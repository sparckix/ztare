from __future__ import annotations

import pytest

from ztare.common.guarded_experiment_protocol import (
    ProtocolYieldWeights,
    price_guarded_protocol,
)
from ztare.common.partial_action_system import (
    PartialActionObservation,
    build_partial_action_system,
)
from ztare.common.protocol_information_yield import (
    compile_protocol_information_yield_forecast,
)
from ztare.worldmodel.mechanism_protocols import (
    compile_witnessed_protocol_response_readout,
    lower_witnessed_protocol,
    observe_witnessed_protocol_information_yield,
    witnessed_protocol_response,
)


PREPARE = 0
PROBE = 1


def _state(key: str, incoming_effect: str = "identity"):
    return key, incoming_effect


def _system(*, include_target_probe: bool = False):
    rows = [
        PartialActionObservation(
            source=_state("start"),
            operation=PREPARE,
            successor=_state("target", "prepare-effect"),
            evidence_ref="start:prepare",
        ),
        PartialActionObservation(
            source=_state("analog-a"),
            operation=PROBE,
            successor=_state("successor-a", "common-effect"),
            evidence_ref="analog-a:probe",
        ),
        PartialActionObservation(
            source=_state("analog-b"),
            operation=PROBE,
            successor=_state("successor-b", "common-effect"),
            evidence_ref="analog-b:probe",
        ),
        PartialActionObservation(
            source=_state("analog-c"),
            operation=PROBE,
            successor=_state("successor-c", "rare-effect"),
            evidence_ref="analog-c:probe",
        ),
    ]
    if include_target_probe:
        rows.append(PartialActionObservation(
            source=_state("target"),
            operation=PROBE,
            successor=_state("target-successor", "common-effect"),
            evidence_ref="target:probe",
        ))
    return build_partial_action_system(
        rows,
        project=lambda state: state[0],
        effect=lambda _source, _operation, successor, *_keys: (
            successor[1]
        ),
        projection_id="readout-fixture",
    ), rows


class _Compatibility:
    sources = ("analog-a", "analog-b", "analog-c", "target")
    operations = (PREPARE, PROBE)

    @staticmethod
    def is_compatible(_left, _right):
        return True


def _lowering_and_forecast():
    system, rows = _system()
    lowering = lower_witnessed_protocol(
        system,
        _Compatibility(),
        start_key="start",
        actions=(PREPARE, PROBE),
        protocol_id="novel-target-probe",
    )
    price = price_guarded_protocol(
        lowering.candidate,
        weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
    )
    forecast = compile_protocol_information_yield_forecast(
        lowering.candidate,
        price,
    )
    return system, rows, lowering, forecast


def test_direct_readout_equals_augmented_partial_system_response():
    system, rows, lowering, forecast = _lowering_and_forecast()
    readout, observed = observe_witnessed_protocol_information_yield(
        system,
        lowering,
        forecast,
        observed_source_key="target",
        observed_operation=PROBE,
        observed_successor_key="target-successor",
        observed_effect="common-effect",
        observation_evidence_ref="live:target:probe",
    )
    augmented_rows = [
        *rows,
        PartialActionObservation(
            source=_state("target"),
            operation=PROBE,
            successor=_state("target-successor", "common-effect"),
            evidence_ref="live:target:probe",
        ),
    ]
    augmented = build_partial_action_system(
        augmented_rows,
        project=lambda state: state[0],
        effect=lambda _source, _operation, successor, *_keys: (
            successor[1]
        ),
        projection_id="readout-fixture",
    )
    recompiled = witnessed_protocol_response(
        augmented,
        source_key="target",
        probe=PROBE,
        response_readout_operations=(
            lowering.response_readout_operations
        ),
    )
    assert readout.response == recompiled
    assert observed.status == "witnessed_partition_cell"
    assert observed.posterior_cell_size == 2
    assert not readout.to_receipt()["task_credit_authorized"]
    assert not observed.to_receipt()["task_credit_authorized"]


def test_new_effect_refutes_committee_and_boundary_stays_typed():
    system, _rows, lowering, forecast = _lowering_and_forecast()
    readout, observed = observe_witnessed_protocol_information_yield(
        system,
        lowering,
        forecast,
        observed_source_key="target",
        observed_operation=PROBE,
        observed_successor_key="new-successor",
        observed_effect="unforecast-effect",
        observation_evidence_ref="live:new-effect",
    )
    assert readout.response[0] == "observed_response"
    assert observed.status == "committee_refuted"
    assert observed.posterior_cell_size == 0

    boundary, boundary_yield = (
        observe_witnessed_protocol_information_yield(
            system,
            lowering,
            forecast,
            observed_source_key="target",
            observed_operation=PROBE,
            boundary_kind="environment_reset",
            observation_evidence_ref="live:boundary",
        )
    )
    assert boundary.response[0] == "typed_boundary_response"
    assert boundary.response[2] == ("environment_reset",)
    assert boundary.response[3] == ()
    assert boundary_yield.status == "committee_refuted"


def test_readout_refuses_source_probe_or_evidence_mismatch():
    system, _rows, lowering, _forecast = _lowering_and_forecast()
    common = {
        "system": system,
        "lowering": lowering,
        "observed_successor_key": "successor",
        "observed_effect": "common-effect",
        "observation_evidence_ref": "live:evidence",
    }
    with pytest.raises(ValueError, match="source does not match target"):
        compile_witnessed_protocol_response_readout(
            **common,
            observed_source_key="analog-a",
            observed_operation=PROBE,
        )
    with pytest.raises(ValueError, match="operation does not match probe"):
        compile_witnessed_protocol_response_readout(
            **common,
            observed_source_key="target",
            observed_operation=PREPARE,
        )
    with pytest.raises(ValueError, match="requires evidence"):
        compile_witnessed_protocol_response_readout(
            **{
                **common,
                "observation_evidence_ref": "",
            },
            observed_source_key="target",
            observed_operation=PROBE,
        )


def test_existing_relation_is_unioned_not_overwritten():
    system, rows = _system(include_target_probe=True)
    lowering = lower_witnessed_protocol(
        system,
        _Compatibility(),
        start_key="start",
        actions=(PREPARE, PROBE),
        protocol_id="existing-target-probe",
    )
    readout = compile_witnessed_protocol_response_readout(
        system,
        lowering,
        observed_source_key="target",
        observed_operation=PROBE,
        observed_successor_key="second-target-successor",
        observed_effect="second-effect",
        observation_evidence_ref="live:second-effect",
    )
    augmented = build_partial_action_system(
        [
            *rows,
            PartialActionObservation(
                source=_state("target"),
                operation=PROBE,
                successor=_state(
                    "second-target-successor",
                    "second-effect",
                ),
                evidence_ref="live:second-effect",
            ),
        ],
        project=lambda state: state[0],
        effect=lambda _source, _operation, successor, *_keys: (
            successor[1]
        ),
        projection_id="readout-fixture",
    )
    assert readout.response == witnessed_protocol_response(
        augmented,
        source_key="target",
        probe=PROBE,
        response_readout_operations=(
            lowering.response_readout_operations
        ),
    )
    assert set(readout.response[1]) == {
        "common-effect",
        "second-effect",
    }
