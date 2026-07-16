from __future__ import annotations

import json

import pytest

from ztare.common.observation_chart import (
    CounterexampleObservationTriple,
    ChartTransportMorphism,
    CoordinateOperation,
    EvidenceEpochChangedError,
    FiberReachabilityReceipt,
    ObservationChart,
    TransportWitness,
    WitnessedFiberMember,
    assert_project_evidence_epoch,
    capture_project_evidence_epoch,
    certify_pointwise_transport,
    register_pointwise_operation,
    select_witnessed_fiber,
)


def _charts():
    common = {
        "packet_schema_id": "transition-v1",
        "coordinate_axes": ("state", "action", "time", "successor"),
        "authority": "episode_collector",
    }
    return (
        ObservationChart("replay", "v1", parameters={"clock": "local"}, **common),
        ObservationChart("bank", "v1", parameters={"clock": "run"}, **common),
    )


def test_counterexample_observation_triple_identity_is_chart_bound():
    source, _target = _charts()
    triple = CounterexampleObservationTriple(
        chart=source,
        evidence_epoch_sha256="epoch-a",
        evidence_ref="visible/evidence.jsonl",
        observation_ref="visible/evidence.jsonl#row:7",
        proposal_identity={"carrier_sha": "candidate-a"},
        intervention={"kind": "action", "value": 2},
        source_observation={"tokens": ["a", "b"]},
        proposed_consequence={"tokens": ["a", "c"]},
        observed_consequence={"tokens": ["a", "d"]},
    )

    payload = triple.to_dict()
    assert payload["objects"]["source_observation"] == {"tokens": ["a", "b"]}
    assert payload["observation_chart"]["coordinate_axes"] == [
        "state", "action", "time", "successor"
    ]
    changed_chart = ObservationChart(
        "replay-window", "v1", "transition-v1", ("token",), "text_adapter"
    )
    changed = CounterexampleObservationTriple(
        chart=changed_chart,
        evidence_epoch_sha256="epoch-a",
        evidence_ref="visible/evidence.jsonl",
        observation_ref="visible/evidence.jsonl#row:7",
        proposal_identity={"carrier_sha": "candidate-a"},
        intervention={"kind": "action", "value": 2},
        source_observation={"tokens": ["a", "b"]},
        proposed_consequence={"tokens": ["a", "c"]},
        observed_consequence={"tokens": ["a", "d"]},
    )
    assert changed.sha256 != triple.sha256


def test_counterexample_observation_identity_ignores_storage_provenance():
    source, _target = _charts()
    common = {
        "chart": source,
        "evidence_epoch_sha256": "epoch-a",
        "proposal_identity": {"carrier_sha": "candidate-a"},
        "intervention": {"kind": "action", "value": 2},
        "source_observation": {"tokens": ["a", "b"]},
        "proposed_consequence": {"tokens": ["a", "c"]},
        "observed_consequence": {"tokens": ["a", "d"]},
    }
    first = CounterexampleObservationTriple(
        evidence_ref="visible/evidence.jsonl",
        observation_ref="visible/evidence.jsonl#row:7",
        **common,
    )
    copied = CounterexampleObservationTriple(
        evidence_ref="workspace/copied_bank.jsonl",
        observation_ref="workspace/copied_bank.jsonl#row:91",
        **common,
    )

    assert first.to_dict()["observation_ref"] != copied.to_dict()["observation_ref"]
    assert first.sha256 == copied.sha256


def test_pointwise_clock_transport_runs_order_metamorphisms_and_rejects_stateful_ops():
    source, target = _charts()
    operation = CoordinateOperation.bind(
        path=("time",),
        operation_id="integer_affine.v1",
        parameters={"scale": 1, "offset": 25},
    )
    witnesses = [
        TransportWitness(
            {"state": n, "action": 2, "time": 65 + n, "successor": n + 1},
            {"state": n, "action": 2, "time": 90 + n, "successor": n + 1},
            f"row:{n}",
        )
        for n in range(2)
    ]
    from ztare.common.equivariance import stable_sha256
    morphism = ChartTransportMorphism(
        transport_id="clock+25.v1",
        source_chart_sha256=source.sha256,
        target_chart_sha256=target.sha256,
        operations=(operation,),
        domain_witness_bank_sha256=stable_sha256(
            [witness.receipt_payload() for witness in witnesses]
        ),
        declared_domain="attested two-row reset window",
    )
    certificate = certify_pointwise_transport(
        source_chart=source,
        target_chart=target,
        morphism=morphism,
        witnesses=witnesses,
    )
    assert certificate.passed
    assert certificate.repetition_checks == 2
    assert certificate.order_checks == 4

    rolling: list[int] = []

    def history_dependent(value, _parameters):
        rolling.append(value)
        return value + len(rolling)

    with pytest.raises(ValueError, match="mutable/contextual state"):
        register_pointwise_operation(
            "history-dependent-test.v1",
            history_dependent,
            authority="episode_collector",
        )


def test_evidence_epoch_pin_and_constrained_fiber_are_partial(tmp_path):
    project = tmp_path / "projects" / "demo"
    episodes = project / "raw" / "episodes"
    episodes.mkdir(parents=True)
    (episodes / "episode_001.jsonl").write_text(
        json.dumps({"t": 0, "s": [[0]], "a": 0, "s_next": [[1]]}) + "\n"
    )
    sidecar = episodes / "episode_001.identity.json"
    sidecar.write_text("{}\n")
    pinned = capture_project_evidence_epoch(project)
    sidecar.write_text('{"migrated":true}\n')
    with pytest.raises(EvidenceEpochChangedError, match="active governed round"):
        assert_project_evidence_epoch(project, pinned)

    presentation = {"pose": 1}
    from ztare.common.equivariance import stable_sha256
    reachability = FiberReachabilityReceipt(
        canonical_identity_sha256="orbit-a",
        chart_sha256="chart-a",
        presentation_sha256=stable_sha256(presentation),
        status="reachable",
        authority="environment_adapter",
        evidence_refs=("episode:7",),
    )
    member = WitnessedFiberMember(
        canonical_identity_sha256="orbit-a",
        chart_sha256="chart-a",
        presentation=presentation,
        reachability_receipt=reachability,
    )
    assert select_witnessed_fiber(
        canonical_identity_sha256="orbit-a",
        target_chart_sha256="chart-a",
        members=[member],
    ).status == "selected"
    assert select_witnessed_fiber(
        canonical_identity_sha256="orbit-a",
        target_chart_sha256="chart-b",
        members=[member],
    ).status == "unreachable"
    assert select_witnessed_fiber(
        canonical_identity_sha256="orbit-a",
        target_chart_sha256="chart-a",
        members=[member, member],
    ).status == "ambiguous"
