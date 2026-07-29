from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import ztare.leanmill.construction_artifact_ratification as construction_ratification_module

from test_construction_artifact_ratification import _successful_fake_solver
from test_finite_construction_family import _artifact, _capability, _config, _family
from ztare.leanmill.adapter_forge import (
    ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    adapter_forge_attempt_directory,
    bind_adapter_review_evidence,
)
from ztare.leanmill.construction_artifact_ratification import (
    CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA,
    replay_ratified_construction_artifact_result,
)
from ztare.leanmill.finite_construction_family import (
    FINITE_CONSTRUCTION_FAMILY_SCHEMA,
    construction_witness_interface,
    execute_finite_construction_family,
)
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.frontier_campaign_runner import (
    _persist_reviewed_family_member_ratification_admissions,
    execute_frontier_construction_artifact_ratification,
    next_frontier_campaign_action,
)
from ztare.leanmill.exploration_budget import (
    BudgetLedgerResourceUnavailable,
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierExplorationBrief,
    frontier_objective_contract,
)
from ztare.leanmill.frontier_blueprint_compiler import (
    compile_structure_first_blueprint,
)
from ztare.leanmill.reviewed_family_member_ratification import (
    build_reviewed_family_member_ratification_admission,
    ratify_reviewed_family_member_action,
    validate_reviewed_family_member_ratification_admission,
    validate_reviewed_family_member_ratification_aggregate,
)
from ztare.leanmill.theory_ir import SortDecl, TheorySignature, content_hash
from ztare.leanmill.theory_language import build_theory_language_expansion_request
from ztare.leanmill.theory_lineage_synthesis import (
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.theory_program import TheoryProgram


def _reviewed_family_fixture(
    *artifacts: dict,
    request_id: str | None = None,
    adapter_config: dict | None = None,
) -> tuple[dict, dict, dict, dict]:
    family, interface = _family(*artifacts)
    family_core = {
        key: value for key, value in family.items() if key != "receipt_sha256"
    }
    family_core["gap_id"] = "adapter-gap:" + content_hash(
        {"fixture": "reviewed-family-ratification"}
    )
    if request_id is not None:
        family_core["request_id"] = request_id
    if adapter_config is not None:
        interface = construction_witness_interface(
            "binary_linear_code.v1", adapter_config
        )
        family_core["target_interface_sha256"] = interface["interface_sha256"]
    family = {**family_core, "receipt_sha256": content_hash(family_core)}
    execution = execute_finite_construction_family(
        family,
        witness_interface=interface,
        capability_fn=_capability,
    )
    host_core = {
        "ok": True,
        "interface": FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "gap_id": family["gap_id"],
        "context_hash": family["context_hash"],
        "adapter_id": family["adapter_id"],
        "family_id": family["family_id"],
        "finite_family_receipt_sha256": family["receipt_sha256"],
        "target_interface_sha256": interface["interface_sha256"],
        "outcomes_evaluated": False,
    }
    host = {**host_core, "receipt_sha256": content_hash(host_core)}
    review = {
        "accepted": True,
        "reviewer_ref": "independent-family-reviewer",
        "rationale": "the frozen family and scope are admissible",
        "evidence_refs": [host["receipt_sha256"]],
    }
    binding = bind_adapter_review_evidence(review, host)
    forge_core = {
        "schema": "leanmill.adapter_forge_quarantine_receipt.v1",
        "gap_id": family["gap_id"],
        "proposed_adapter_id": family["adapter_id"],
        "proposal_digest": "2" * 64,
        "host_conformance": host,
        "independent_review": review,
        "review_evidence_binding": binding,
        "status": "quarantined_registry_proposal",
        "live_registry_mutated": False,
        "exactness_authority_granted": False,
        "next_step": "execute_reviewed_finite_construction_family",
    }
    forge = {**forge_core, "receipt_sha256": content_hash(forge_core)}
    return family, interface, execution, forge


def _campaign_adapter_config() -> dict:
    return {
        **_config(),
        "evidence_panel": {
            "schema": "leanmill.binary_linear_code_evidence_panel.v1",
            "field_order": 1,
            "completeness_scope": "declared_control_panel_only",
            "completeness_ref": "fixture:reviewed-family-campaign",
            "objects": [
                {
                    "object_id": "control:one",
                    "stratum_id": "control",
                    "payload": {"label": "one"},
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "property:one",
                    "satisfied_object_ids": ["control:one"],
                    "anonymous_shape": {"kind": "control", "complexity": 1},
                    "payload": {"checker_ref": "fixture:one"},
                }
            ],
        },
    }


def _campaign_blueprint():
    return compile_structure_first_blueprint(
        FrontierExplorationBrief(
            "Exercise the reviewed finite-family terminal transition.",
            source_mode="structure_first",
        ),
        {
            "mode": "evidence_induced",
            "eigenquestion": "Does the reviewed family contain the target witness?",
            "signature": TheorySignature(
                name="Evidence", sorts=(SortDecl("Observation"),)
            ).to_json(),
            "primitive_semantics": {
                "operation_bindings": {},
                "relation_bindings": {},
            },
            "base_axioms": (),
            "base_theory_status": "explicit_empty",
            "adapter_id": "binary_linear_code.v1",
            "adapter_config": _campaign_adapter_config(),
            "formula_grammar": {},
            "model_or_observation_strata": (),
            "pack_arity": 1,
            "collapse_controls": (),
            "visible_evidence_manifest": {"source_refs": ["fixture:panel"]},
            "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
            "deanchoring_policy": {"cold_after_signature_compilation": True},
            "navigator_contract": {"selection_mode": "theory_program"},
            "query_budget": {"max_finalists": 1},
            "stop_rule": {
                "user_instruction": "Construct and ratify the frozen binary code.",
                "executable_condition": {
                    "kind": "late_lineage_objective_review"
                },
            },
            "verification_plan": {},
            "codec_versions": {"evidence": "fixture-v1"},
            "authority_refs": ("fixture:campaign-authority",),
        },
    )


def _persist_family_sources(
    directory: Path, *, family: dict, forge: dict
) -> None:
    if not (directory / "budget.json").exists():
        write_json_atomic(
            directory / "budget.json", budget_preset("smoke_20m").to_json()
        )
    owner = adapter_forge_attempt_directory(
        directory,
        family["gap_id"],
        host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        create=True,
    )
    write_json_atomic(
        owner / "theory_language_finite_family_candidate.json", family
    )
    core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": "reviewed_campaign_local_finite_family_available",
        "attempt_dir": str(directory),
        "gap_id": family["gap_id"],
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "quarantine_receipt": forge,
        "reason": forge["independent_review"]["rationale"],
        "rejection_class": "",
        "recovery_route": "",
        "evidence_refs": [forge["receipt_sha256"]],
        "provider_calls": 0,
    }
    write_json_atomic(
        owner / "adapter_forge_completion.json",
        {**core, "completion_sha256": content_hash(core)},
    )


def _pending_campaign(
    directory: Path, *, include_synthesis: bool = True
) -> dict:
    write_json_atomic(
        directory / "budget.json", budget_preset("smoke_20m").to_json()
    )
    request = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The current chart cannot enumerate the selected finite family.",
        proposed_interface="A reviewed explicit parameter-to-generator relation.",
        evidence_refs=("evidence:test",),
        discriminating_test="Execute every family member and ratify any witness.",
        kill_condition="Return verifier rejection or formal unavailability to search.",
    )
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc"),
        request_id=request.request_id,
        adapter_config=_campaign_adapter_config(),
    )
    admissions = _persist_reviewed_family_member_ratification_admissions(
        directory,
        family=family,
        execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
    )
    _persist_family_sources(directory, family=family, forge=forge)
    blueprint = _campaign_blueprint()
    write_json_atomic(directory / "blueprint.json", blueprint.to_json())
    lineage_id = "lineage:family-author"
    program = TheoryProgram(
        campaign_id="campaign:reviewed-family",
        lineage_id=lineage_id,
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:seed",),
        prediction_formula_ids=("formula:target",),
        selection_receipt_id="selection:reviewed-family",
    )
    wrapper = {
        "lineage_id": lineage_id,
        "request_id": request.request_id,
        "request": request.to_json(),
    }
    navigation = {
        "context_hash": "context:test",
        "context_epoch": 0,
        "language_expansion_request": request.to_json(),
        "theory_language_expansion_requests": [wrapper],
        "finite_construction_family_execution": execution,
        "reviewed_family_member_ratification_admission_sha256s": [
            admissions[0]["receipt_sha256"]
        ],
        "finalists": [
            {
                "theory_program": program.to_json(),
                "theory_program_id": program.program_id,
            }
        ],
        "objective_survivors": [],
    }
    synthesis_input = lineage_synthesis_input(
        navigation, objective_contract=frontier_objective_contract(blueprint)
    )
    synthesis = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "escalate_language",
            "selected_request_ids": [request.request_id],
            "deferred_request_ids": [],
            "rationale": "The reviewed family is the selected discriminator.",
            "next_discriminator": request.discriminating_test,
            "kill_condition": request.kill_condition,
            "program_ids": [],
            "next_discriminator_request_ids": [request.request_id],
        },
    )
    if include_synthesis:
        navigation["lineage_synthesis"] = synthesis
        write_json_atomic(
            directory / "lineage_synthesis_input.epoch-000.json",
            synthesis_input,
        )
    run_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_objective_witness_found_pending_ratification",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": navigation,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return {
        "request": request,
        "family": family,
        "interface": interface,
        "execution": execution,
        "forge": forge,
        "admission": admissions[0],
        "blueprint": blueprint,
        "lineage_id": lineage_id,
        "program": program,
        "synthesis_input": synthesis_input,
        "synthesis": synthesis,
    }


def test_admission_preserves_adapterforge_authorship_and_verified_member() -> None:
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc"),
        _artifact("0x1", "0x2"),
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id="p0",
    )

    assert validate_reviewed_family_member_ratification_admission(admission) == (
        admission
    )
    assert admission["family_authorship"] == {
        "authority": "campaign_local_subscription_leaf",
        "role": "adapter_forge",
    }
    assert admission["kernel_ratification_authority"] is False
    assert "witness_constructor" not in json.dumps(admission, sort_keys=True)

    rejected = deepcopy(execution)
    rejected["member_results"][0]["status"] = "rejected"
    member_core = {
        key: value
        for key, value in rejected["member_results"][0].items()
        if key != "receipt_sha256"
    }
    rejected["member_results"][0]["receipt_sha256"] = content_hash(member_core)
    execution_core = {
        key: value for key, value in rejected.items() if key != "receipt_sha256"
    }
    rejected["receipt_sha256"] = content_hash(execution_core)
    with pytest.raises(ValueError):
        build_reviewed_family_member_ratification_admission(
            family=family,
            family_execution=rejected,
            forge_quarantine_receipt=forge,
            witness_interface=interface,
            parameter_id="p0",
        )


def test_duplicate_normal_forms_have_one_canonical_ratification_admission() -> None:
    artifact = _artifact("0x3", "0xc")
    family, interface, execution, forge = _reviewed_family_fixture(
        artifact, artifact
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id="p0",
    )
    assert admission["parameter_ids"] == ["p0", "p1"]
    with pytest.raises(ValueError, match="first parameter"):
        build_reviewed_family_member_ratification_admission(
            family=family,
            family_execution=execution,
            forge_quarantine_receipt=forge,
            witness_interface=interface,
            parameter_id="p1",
        )


def test_family_action_reuses_provider_free_ratification_core(tmp_path: Path) -> None:
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc")
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id="p0",
    )
    captured: dict = {}

    def rejected(_target, _posed, _goal, **kwargs):
        captured.update(kwargs)
        return {
            "results": [{
                "outcome": "rejected_governance",
                "providers_tried": [{
                    "provider": "construction_artifact_certificate",
                    "agent_kind": "preverified_champion",
                }],
            }],
            "closure_certificate": None,
        }

    aggregate = ratify_reviewed_family_member_action(
        admission,
        substrate=tmp_path,
        governed_solve_fn=rejected,
    )

    assert validate_reviewed_family_member_ratification_aggregate(aggregate) == (
        aggregate
    )
    result = aggregate["ratification_result"]
    assert result["status"] == "open"
    assert result["reason_code"] == "rejected_governance"
    assert result["ratification_contract"]["schema"] == (
        CONSTRUCTION_ARTIFACT_RATIFICATION_CONTRACT_V2_SCHEMA
    )
    assert aggregate["governed_closure_record"] is None
    assert captured["provider"] is None
    assert captured["preverified_only"] is True
    assert captured["preverified_provider"] == "construction_artifact_certificate"
    assert captured["require_positive_axiom_receipt"] is True


def test_ratified_family_aggregate_replays_embedded_record_without_ledger(
    tmp_path: Path,
) -> None:
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc")
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id="p0",
    )
    aggregate = ratify_reviewed_family_member_action(
        admission,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    result = aggregate["ratification_result"]
    embedded = aggregate["governed_closure_record"]
    assert result["status"] == "ratified"
    assert isinstance(embedded, dict)

    ledger = Path(result["closure_record_ref"]["ledger"])
    ledger.unlink()
    assert validate_reviewed_family_member_ratification_aggregate(aggregate) == (
        aggregate
    )
    replayed, selected = replay_ratified_construction_artifact_result(
        result, closure_record=embedded
    )
    assert replayed == result
    assert selected == embedded
    with pytest.raises(ValueError, match="ledger is unavailable"):
        replay_ratified_construction_artifact_result(result)


def test_ratified_family_aggregate_rejects_tampered_embedded_record(
    tmp_path: Path,
) -> None:
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc")
    )
    admission = build_reviewed_family_member_ratification_admission(
        family=family,
        family_execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
        parameter_id="p0",
    )
    aggregate = ratify_reviewed_family_member_action(
        admission,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    tampered = deepcopy(aggregate)
    tampered["governed_closure_record"]["provider"] = "forged-provider"
    core = {
        key: value for key, value in tampered.items() if key != "aggregate_sha256"
    }
    tampered["aggregate_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="closure record digest mismatch"):
        validate_reviewed_family_member_ratification_aggregate(tampered)


def test_campaign_routes_reviewed_family_member_to_objective_discharge(
    tmp_path: Path,
) -> None:
    request = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The current chart cannot enumerate the selected finite family.",
        proposed_interface="A reviewed explicit parameter-to-generator relation.",
        evidence_refs=("evidence:test",),
        discriminating_test="Execute every family member and ratify any witness.",
        kill_condition="Return verifier rejection or formal unavailability to search.",
    )
    family, interface, execution, forge = _reviewed_family_fixture(
        _artifact("0x3", "0xc"),
        request_id=request.request_id,
        adapter_config=_campaign_adapter_config(),
    )
    admissions = _persist_reviewed_family_member_ratification_admissions(
        tmp_path,
        family=family,
        execution=execution,
        forge_quarantine_receipt=forge,
        witness_interface=interface,
    )
    assert len(admissions) == 1
    _persist_family_sources(tmp_path, family=family, forge=forge)

    blueprint = _campaign_blueprint()
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    lineage_id = "lineage:family-author"
    program = TheoryProgram(
        campaign_id="campaign:reviewed-family",
        lineage_id=lineage_id,
        context_hash="context:test",
        context_epoch=0,
        presentation_formula_ids=("formula:seed",),
        prediction_formula_ids=("formula:target",),
        selection_receipt_id="selection:reviewed-family",
    )
    wrapper = {
        "lineage_id": lineage_id,
        "request_id": request.request_id,
        "request": request.to_json(),
    }
    navigation = {
        "context_hash": "context:test",
        "context_epoch": 0,
        "language_expansion_request": request.to_json(),
        "theory_language_expansion_requests": [wrapper],
        "finite_construction_family_execution": execution,
        "reviewed_family_member_ratification_admission_sha256s": [
            admissions[0]["receipt_sha256"]
        ],
        "finalists": [
            {
                "theory_program": program.to_json(),
                "theory_program_id": program.program_id,
            }
        ],
        "objective_survivors": [],
    }
    synthesis_input = lineage_synthesis_input(
        navigation, objective_contract=frontier_objective_contract(blueprint)
    )
    synthesis = validate_lineage_synthesis_decision(
        synthesis_input,
        {
            "route": "escalate_language",
            "selected_request_ids": [request.request_id],
            "deferred_request_ids": [],
            "rationale": "The reviewed family is the selected discriminator.",
            "next_discriminator": request.discriminating_test,
            "kill_condition": request.kill_condition,
            "program_ids": [],
            "next_discriminator_request_ids": [request.request_id],
        },
    )
    navigation["lineage_synthesis"] = synthesis
    write_json_atomic(
        tmp_path / "lineage_synthesis_input.epoch-000.json", synthesis_input
    )
    run_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_objective_witness_found_pending_ratification",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": navigation,
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    assert next_frontier_campaign_action(tmp_path) == (
        "ratify_construction_artifact"
    )

    aggregate = ratify_reviewed_family_member_action(
        admissions[0],
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    calls = {"count": 0}

    def ratifier(admission, **_kwargs):
        calls["count"] += 1
        assert admission == admissions[0]
        return aggregate

    lease = SimpleNamespace(
        binding={"root_context_hash": "context:test"},
        bind_epoch=lambda **_kwargs: None,
    )
    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=ratifier,
        _attempt_lease=lease,
    )
    assert completion["status"] == "objective_discharged"
    assert calls["count"] == 1
    assert not (tmp_path / "boundary_completion.json").exists()
    closed = read_json(tmp_path / "run.json", {})
    assert closed["status"] == "frontier_objective_discharged"
    discharge = closed["navigation"]["reviewed_family_objective_discharge"]
    assert discharge["source_lineage_ids"] == [lineage_id]
    assert discharge["admission"]["normalized_artifact_sha256"] == (
        admissions[0]["normalized_artifact_sha256"]
    )
    assert (
        tmp_path
        / (
            "reviewed_family_member_ratification.by-admission."
            + admissions[0]["receipt_sha256"]
            + ".json"
        )
    ).is_file()
    assert (
        tmp_path
        / (
            "lineage_synthesis_input.by-digest."
            + synthesis_input["input_sha256"]
            + ".json"
        )
    ).is_file()
    assert next_frontier_campaign_action(tmp_path) == "complete"

    second = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("family ratification repeated after discharge")
        ),
        _attempt_lease=lease,
    )
    assert second["status"] == "no_pending_construction_ratification"


@pytest.mark.parametrize(
    ("mode", "expected_outcome"),
    (("open", "rejected"), ("unavailable", "unavailable")),
)
def test_campaign_returns_open_or_unavailable_family_ratification_to_navigation(
    tmp_path: Path,
    mode: str,
    expected_outcome: str,
) -> None:
    state = _pending_campaign(tmp_path)
    admission = state["admission"]

    if mode == "open":
        def rejected(_target, _posed, _goal, **_kwargs):
            return {
                "results": [{
                    "outcome": "rejected_governance",
                    "providers_tried": [{
                        "provider": "construction_artifact_certificate",
                        "agent_kind": "preverified_champion",
                    }],
                }],
                "closure_certificate": None,
            }

        aggregate = ratify_reviewed_family_member_action(
            admission,
            substrate=tmp_path,
            governed_solve_fn=rejected,
        )
    else:
        from ztare.leanmill.construction_artifact_ratification import (
            ConstructionArtifactRatificationCapabilityUnavailable,
        )

        def unavailable(**_kwargs):
            raise ConstructionArtifactRatificationCapabilityUnavailable(
                "fixture_formal_bridge_unavailable"
            )

        aggregate = ratify_reviewed_family_member_action(
            admission,
            substrate=tmp_path,
            formal_interface_fn=unavailable,
        )

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: aggregate,
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    run = read_json(tmp_path / "run.json", {})
    assert run["status"] == "frontier_objective_unmet"
    feedback = read_json(tmp_path / "theory_language_compilation_feedback.json", {})
    assert feedback["outcome"] == expected_outcome
    assert run["navigation"]["carried_evidence_receipts"]
    assert "reviewed_family_objective_discharge" not in run["navigation"]


def test_malformed_family_ratification_conservatively_closes_reservation(
    tmp_path: Path,
) -> None:
    _pending_campaign(tmp_path)

    with pytest.raises(ValueError):
        execute_frontier_construction_artifact_ratification(
            tmp_path,
            lean_root=tmp_path,
            family_ratify_fn=lambda *_args, **_kwargs: {},
            _attempt_lease=SimpleNamespace(
                binding={"root_context_hash": "context:test"},
                bind_epoch=lambda **_kwargs: None,
            ),
        )

    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id=tmp_path.name,
    )
    state = ledger.state()
    assert state["reservations"] == {}
    assert state["usage"]["lean_attempts"] == 1
    assert ledger._strict_rows()[-1]["event_type"] == "wall_clock_frozen"


def test_formal_resource_ceiling_releases_pre_kernel_reservation(
    tmp_path: Path, monkeypatch
) -> None:
    state = _pending_campaign(tmp_path)
    monkeypatch.setattr(
        construction_ratification_module,
        "_MAX_FORMAL_SOURCE_COMPONENT_BYTES",
        1,
    )

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    owner = tmp_path / (
        "reviewed_family_member_ratification.by-admission."
        + state["admission"]["receipt_sha256"]
        + ".json"
    )
    aggregate = validate_reviewed_family_member_ratification_aggregate(
        read_json(owner, {})
    )
    result = aggregate["ratification_result"]
    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_interface"
    assert result["resource_unavailable"]["resource"] == (
        "construction_formal_source_prefix_bytes"
    )
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id=tmp_path.name,
    )
    assert ledger.state()["usage"]["lean_attempts"] == 0
    assert ledger.state()["usage"]["lean_millis"] == 0
    releases = [
        row
        for row in ledger._strict_rows()
        if row.get("event_type") == "reservation_released"
    ]
    assert len(releases) == 1
    assert releases[0]["reason"] == (
        "family_construction_ratification_pre_kernel_unavailable"
    )


def test_ratified_family_without_synthesis_provenance_cannot_discharge_objective(
    tmp_path: Path,
) -> None:
    state = _pending_campaign(tmp_path, include_synthesis=False)
    aggregate = ratify_reviewed_family_member_action(
        state["admission"],
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: aggregate,
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    run = read_json(tmp_path / "run.json", {})
    assert run["status"] == "frontier_objective_unmet"
    feedback = read_json(tmp_path / "theory_language_compilation_feedback.json", {})
    assert feedback["outcome"] == "unavailable"
    assert feedback["reason"] == (
        "reviewed_family_objective_discharge_provenance_unavailable"
    )
    assert not list(tmp_path.glob("reviewed_family_objective_discharge.*.json"))
    assert list(tmp_path.glob("reviewed_family_member_ratification.*.json"))


def test_family_ratification_budget_exhaustion_is_typed_navigation_feedback(
    tmp_path: Path,
) -> None:
    from ztare.leanmill.exploration_budget import budget_preset

    _pending_campaign(tmp_path)
    write_json_atomic(tmp_path / "budget.json", budget_preset("local_only").to_json())

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("budget exhaustion must precede ratification")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    assert completion["aggregate_sha256s"] == []
    feedback = read_json(tmp_path / "theory_language_compilation_feedback.json", {})
    assert feedback["outcome"] == "unavailable"
    assert feedback["reason"].startswith(
        "reviewed_family_member_ratification_budget_unavailable:"
    )


def test_family_admission_recovery_rebuilds_from_forge_and_family_bytes(
    tmp_path: Path,
) -> None:
    state = _pending_campaign(tmp_path)
    mutated = deepcopy(state["admission"])
    mutated["forge_proposal_digest"] = "3" * 64
    core = {
        key: value for key, value in mutated.items() if key != "receipt_sha256"
    }
    mutated["receipt_sha256"] = content_hash(core)
    assert validate_reviewed_family_member_ratification_admission(mutated) == mutated
    write_json_atomic(
        tmp_path
        / (
            "reviewed_family_member_ratification_admission."
            + mutated["receipt_sha256"][:16]
            + ".json"
        ),
        mutated,
    )
    run = read_json(tmp_path / "run.json", {})
    run_core = {key: value for key, value in run.items() if key != "run_digest"}
    navigation = dict(run_core["navigation"])
    navigation["reviewed_family_member_ratification_admission_sha256s"] = [
        mutated["receipt_sha256"]
    ]
    run_core["navigation"] = navigation
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )

    assert next_frontier_campaign_action(tmp_path) == (
        "ratify_construction_artifact"
    )
    with pytest.raises(ValueError, match="admission does not rebuild"):
        execute_frontier_construction_artifact_ratification(
            tmp_path,
            lean_root=tmp_path,
            family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("invalid admission must fail before ratification")
            ),
            _attempt_lease=SimpleNamespace(
                binding={"root_context_hash": "context:test"},
                bind_epoch=lambda **_kwargs: None,
            ),
        )


def test_family_ratification_action_poll_is_read_only_and_semantics_free(
    tmp_path: Path, monkeypatch
) -> None:
    import ztare.leanmill.theory_adapter_registry as registry

    _pending_campaign(tmp_path)
    calls = {"count": 0}

    def forbidden_capability(*_args, **_kwargs):
        calls["count"] += 1
        raise AssertionError("action polling invoked adapter semantics")

    monkeypatch.setattr(
        registry,
        "materialize_theory_adapter_capability",
        forbidden_capability,
    )
    before = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    assert next_frontier_campaign_action(tmp_path) == (
        "ratify_construction_artifact"
    )
    assert next_frontier_campaign_action(tmp_path) == (
        "ratify_construction_artifact"
    )

    after = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert calls == {"count": 0}
    assert after == before


def test_family_cold_replay_budget_unavailability_is_typed_and_frozen(
    tmp_path: Path,
) -> None:
    _pending_campaign(tmp_path)
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    consume = ledger.reserve(
        "fixture:consume-cold-family-boundary",
        "boundary",
        {"boundary_queries": budget.hard_caps["boundary_queries"]},
    )
    ledger.commit(consume)
    ledger.freeze_wall_clock(reason="fixture_before_cold_replay")
    provider_calls_before = ledger.state()["usage"]["provider_calls"]

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("cold replay budget failure reached ratification")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    feedback = read_json(
        tmp_path / "theory_language_compilation_feedback.json", {}
    )
    assert feedback["outcome"] == "unavailable"
    assert feedback["reason"].startswith(
        "reviewed_family_cold_replay_unavailable:"
    )
    receipts = list(
        tmp_path.glob("reviewed_family_cold_replay_unavailable.*.json")
    )
    assert len(receipts) == 1
    assert ledger.state()["usage"]["provider_calls"] == provider_calls_before
    events = [
        json.loads(line)
        for line in (tmp_path / "budget.events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert events[-1]["event_type"] == "wall_clock_frozen"


def test_family_formal_ledger_failure_is_not_misclassified_as_cold_replay(
    tmp_path: Path, monkeypatch
) -> None:
    _pending_campaign(tmp_path)
    original_reserve = ExplorationBudgetLedger.reserve

    def fail_formal_reservation(self, action_id, phase, resources):
        if str(action_id).startswith(
            "boundary:family-construction-ratification:"
        ):
            raise BudgetLedgerResourceUnavailable(
                "fixture_formal_ledger_unavailable",
                observed=1,
                ceiling=1,
            )
        return original_reserve(self, action_id, phase, resources)

    monkeypatch.setattr(
        ExplorationBudgetLedger,
        "reserve",
        fail_formal_reservation,
    )
    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("formal ledger failure reached ratifier")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    feedback = read_json(
        tmp_path / "theory_language_compilation_feedback.json", {}
    )
    assert feedback["reason"] == (
        "reviewed_family_formal_stage_unavailable:"
        "fixture_formal_ledger_unavailable"
    )
    assert not list(
        tmp_path.glob("reviewed_family_cold_replay_unavailable.*.json")
    )
    formal_receipts = list(
        tmp_path.glob("reviewed_family_formal_stage_unavailable.*.json")
    )
    assert len(formal_receipts) == 1
    formal_receipt = read_json(formal_receipts[0], {})
    assert formal_receipt["stage"] == "formal_ratification"
    assert formal_receipt["resource"] == "exploration_budget_ledger_bytes"
    assert formal_receipt["observed"] == 1
    assert formal_receipt["ceiling"] == 1
    assert formal_receipt["counters"] == {}


def test_family_cold_replay_projects_oversized_ledger_to_typed_feedback(
    tmp_path: Path, monkeypatch
) -> None:
    import ztare.leanmill.exploration_budget as budget_module

    _pending_campaign(tmp_path)
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    ledger.freeze_wall_clock(reason="fixture_before_oversized_replay")
    ledger_bytes = (tmp_path / "budget.events.jsonl").read_bytes()
    monkeypatch.setattr(
        budget_module,
        "_MAX_AUTHORITY_LEDGER_BYTES",
        len(ledger_bytes) - 1,
    )

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("oversized ledger reached ratification")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    feedback = read_json(
        tmp_path / "theory_language_compilation_feedback.json", {}
    )
    assert feedback["reason"] == (
        "reviewed_family_cold_replay_unavailable:"
        "budget_ledger_byte_limit_exhausted"
    )
    assert (tmp_path / "budget.events.jsonl").read_bytes() == ledger_bytes
    receipt_paths = list(
        tmp_path.glob("reviewed_family_cold_replay_unavailable.*.json")
    )
    assert len(receipt_paths) == 1
    receipt = read_json(receipt_paths[0], {})
    assert receipt["error_type"] == "BudgetLedgerResourceUnavailable"
    assert receipt["resource"] == "exploration_budget_ledger_bytes"
    assert receipt["observed"] > receipt["ceiling"]
    assert receipt["counters"] == {}


def test_family_cold_replay_projects_write_headroom_before_semantics(
    tmp_path: Path, monkeypatch
) -> None:
    import ztare.leanmill.exploration_budget as budget_module

    _pending_campaign(tmp_path)
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    ledger.freeze_wall_clock(reason="fixture_before_headroom_replay")
    ledger_bytes = (tmp_path / "budget.events.jsonl").read_bytes()
    provider_calls_before = ledger.state()["usage"]["provider_calls"]
    monkeypatch.setattr(
        budget_module,
        "_MAX_AUTHORITY_LEDGER_BYTES",
        len(ledger_bytes)
        + budget_module._AUTHORITY_LEDGER_TERMINAL_HEADROOM_BYTES,
    )

    completion = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        family_ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("write-headroom failure reached ratification")
        ),
        _attempt_lease=SimpleNamespace(
            binding={"root_context_hash": "context:test"},
            bind_epoch=lambda **_kwargs: None,
        ),
    )

    assert completion["status"] == "returned_to_navigation"
    feedback = read_json(
        tmp_path / "theory_language_compilation_feedback.json", {}
    )
    assert feedback["reason"] == (
        "reviewed_family_cold_replay_unavailable:"
        "budget_ledger_write_byte_headroom_exhausted"
    )
    assert (tmp_path / "budget.events.jsonl").read_bytes() == ledger_bytes
    receipt_paths = list(
        tmp_path.glob("reviewed_family_cold_replay_unavailable.*.json")
    )
    assert len(receipt_paths) == 1
    receipt = read_json(receipt_paths[0], {})
    assert receipt["error_type"] == "BudgetLedgerResourceUnavailable"
    assert receipt["resource"] == "exploration_budget_ledger_bytes"
    assert receipt["observed"] > receipt["ceiling"]
    assert receipt["counters"] == {}
    assert receipt["provider_calls_before"] == provider_calls_before
    assert receipt["provider_calls_after"] == provider_calls_before
