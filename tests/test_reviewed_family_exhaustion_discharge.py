from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from test_finite_construction_family import _artifact, _capability
from test_reviewed_family_objective_discharge import (
    _adapter_config,
    _family,
    _forge_receipt,
)
from ztare.leanmill.campaign_closure_gate import (
    assert_campaign_closable,
    lineage_dispositions_from_reviewed_family_exhaustion_discharge,
)
from ztare.leanmill.adapter_forge import AdapterGap
from test_construction_parameterization import (
    _forge_receipt as _parameterization_forge_receipt,
    _limits as _construction_limits,
)
from ztare.leanmill.adapters import binary_linear_code as binary_adapter_module
from ztare.leanmill.adapters.construction_backends import explicit_finite_json
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.construction_parameterization import (
    SAFE_ARTIFACT_TEMPLATE_SCHEMA,
    build_construction_parameterization,
)
from ztare.leanmill.finite_construction_family import (
    admit_construction_origin,
    construction_witness_interface,
    execute_finite_construction_family,
    lower_reviewed_construction_parameterization,
)
from ztare.leanmill.exploration_budget import (
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
from ztare.leanmill.frontier_campaign_runner import (
    _maybe_finalize_reviewed_family_exhaustion,
    advance_frontier_language_expansion,
    next_frontier_campaign_action,
)
from ztare.leanmill.reviewed_family_exhaustion_discharge import (
    build_reviewed_family_exhaustion_discharge,
    build_reviewed_family_exhaustion_observation,
    reviewed_family_exhaustion_stop_permission,
    validate_reviewed_family_exhaustion_discharge,
    validate_reviewed_family_exhaustion_observation,
)
from ztare.leanmill.theory_ir import SortDecl, TheorySignature, content_hash
from ztare.leanmill.theory_language import build_theory_language_expansion_request
from ztare.leanmill.theory_lineage_synthesis import (
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)


STOP_INSTRUCTION = (
    "Stop after one exact witness passes ratification; one campaign-authored "
    "finite construction family is completely enumerated with replayable "
    "member-level rejection receipts and a typed next representation; or the "
    "resource split expires. Never infer global nonexistence from a family result."
)


def _blueprint(instruction: str = STOP_INSTRUCTION):
    brief = FrontierExplorationBrief(
        "Exercise the reviewed family-exhaustion terminal transition.",
        source_mode="structure_first",
    )
    return compile_structure_first_blueprint(
        brief,
        {
            "mode": "evidence_induced",
            "eigenquestion": "What follows when one reviewed family is exhausted?",
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
            "adapter_config": _adapter_config(),
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
                "user_instruction": instruction,
                "executable_condition": {
                    "kind": "late_lineage_objective_review"
                },
            },
            "verification_plan": {},
            "codec_versions": {"evidence": "fixture-v1"},
            "authority_refs": ("fixture:campaign-authority",),
        },
    )


def _workbench_receipt(request) -> dict:
    core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "propose_theory_language_expansion",
        "context_hash": request.source_context_hash,
        "input_hashes": {
            key: "sha256:" + content_hash(value)
            for key, value in sorted(
                {
                    "change_kind": request.change_kind,
                    "blind_spot": request.blind_spot,
                    "proposed_interface": request.proposed_interface,
                    "evidence_refs": list(request.evidence_refs),
                    "discriminating_test": request.discriminating_test,
                    "kill_condition": request.kill_condition,
                }.items()
            )
        },
        "output_summary": {
            "status": "outbound_blueprint_request",
            "request_id": request.request_id,
            "request": request.to_json(),
            "next_route": "frontier_blueprint_compiler_or_adapter_forge",
            "claim_boundary": "proposal only",
        },
        "claim_bindings": ["propose_theory_language_expansion"],
        "authority": "deterministic_host",
    }
    return {**core, "receipt_id": "sha256:" + content_hash(core)}


def _rehash_run(run: dict) -> None:
    core = {key: value for key, value in run.items() if key != "run_digest"}
    run["run_digest"] = content_hash(core)


def _fixture(
    *,
    next_execution_ref: str | None = None,
    include_feedback_ref: bool = True,
    include_authorship: bool = True,
) -> dict:
    blueprint = _blueprint()
    objective = frontier_objective_contract(blueprint)
    source_request = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The chart cannot execute the selected finite family.",
        proposed_interface="A reviewed explicit parameter-to-artifact relation.",
        evidence_refs=("evidence:source",),
        discriminating_test="Execute every reviewed family member.",
        kill_condition="Return complete rejection or unavailability.",
    )
    source_lineage = "lineage:family-author"
    source_wrapper = {
        "lineage_id": source_lineage,
        "request_id": source_request.request_id,
        "request": source_request.to_json(),
    }
    source_navigation = {
        "context_hash": "context:test",
        "context_epoch": 0,
        "theory_language_expansion_requests": [source_wrapper],
        "objective_survivors": [
            {"theory_program_id": "sibling-program"}
        ],
        "finalists": [],
    }
    source_input = lineage_synthesis_input(
        source_navigation, objective_contract=objective
    )
    source_synthesis = validate_lineage_synthesis_decision(
        source_input,
        {
            "route": "escalate_language",
            "selected_request_ids": [source_request.request_id],
            "deferred_request_ids": [],
            "rationale": "Execute the authored family as the next discriminator.",
            "next_discriminator": source_request.discriminating_test,
            "kill_condition": source_request.kill_condition,
            "program_ids": [],
            "next_discriminator_request_ids": [source_request.request_id],
        },
    )
    source_navigation.update(
        {
            "lineage_synthesis": source_synthesis,
            "language_expansion_request": source_request.to_json(),
        }
    )
    source_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "blocked_adapter_gap",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": source_navigation,
    }
    source_run = {**source_core, "run_digest": content_hash(source_core)}

    interface = construction_witness_interface(
        blueprint.adapter_id, blueprint.adapter_config
    )
    family = _family(source_request.request_id, interface)
    family = deepcopy(family)
    rejected_artifact = _artifact("0x1", "0x2")
    family["members"][0]["artifact"] = rejected_artifact
    family["members"][0]["artifact_sha256"] = content_hash(rejected_artifact)
    family_core = {
        key: value for key, value in family.items() if key != "receipt_sha256"
    }
    family["receipt_sha256"] = content_hash(family_core)
    forge = _forge_receipt(family, interface)
    execution = execute_finite_construction_family(
        family, witness_interface=interface, capability_fn=_capability
    )
    assert execution["status"] == "exhausted"
    observation = build_reviewed_family_exhaustion_observation(
        source_family_run=source_run,
        blueprint=blueprint,
        active_request=source_request,
        synthesis_input=source_input,
        synthesis_decision=source_synthesis,
        family=family,
        forge_quarantine_receipt=forge,
        family_execution=execution,
        frozen_lineage_ids=(source_lineage, "legacy-program:sibling-program"),
    )

    feedback_core = {
        "schema": "leanmill.theory_language_compilation_feedback.v1",
        "context_hash": "context:test",
        "request_id": source_request.request_id,
        "outcome": "rejected",
        "reason": "reviewed_finite_family_exhausted:" + family["family_id"],
        "evidence_refs": [forge["receipt_sha256"], execution["receipt_sha256"]],
        "route": "continue_search",
        "program_ids": [],
        "repeat_requires_new_evidence": True,
        "authority": "host_language_compiler",
    }
    feedback = {**feedback_core, "receipt_sha256": content_hash(feedback_core)}
    wave_core = {
        "schema": "leanmill.theory_language_feedback_wave_binding.v1",
        "context_hash": "context:test",
        "context_epoch": 0,
        "request_id": source_request.request_id,
        "feedback_receipt_sha256": feedback["receipt_sha256"],
        "search_wave": 1,
        "authority": "deterministic_campaign_lifecycle",
    }
    wave = {**wave_core, "receipt_sha256": content_hash(wave_core)}

    refs = [next_execution_ref or execution["receipt_sha256"]]
    if include_feedback_ref:
        refs.append(feedback["receipt_sha256"])
    next_request = build_theory_language_expansion_request(
        source_context_hash="context:test",
        source_epoch=0,
        change_kind="quotient_or_coordinate_change",
        blind_spot="The exhausted family exposes a missing nonlocal construction chart.",
        proposed_interface="A new reviewed construction coordinate over another family.",
        evidence_refs=refs,
        discriminating_test="Execute a family outside the exhausted relation.",
        kill_condition="Reject if it repeats the same family digest.",
    )
    next_lineage = "lineage:next-representation"
    next_wrapper = {
        "lineage_id": next_lineage,
        "request_id": next_request.request_id,
        "request": next_request.to_json(),
    }
    workbench = _workbench_receipt(next_request)
    next_navigation = {
        "context_hash": "context:test",
        "context_epoch": 0,
        "search_wave": 1,
        "theory_language_expansion_requests": [next_wrapper],
        "lineages": [
            {
                "lineage_id": next_lineage,
                "navigation": {
                    "trace": (
                        [
                            {
                                "decision": "request",
                                "capability_id": "propose_theory_language_expansion",
                                "receipt": workbench,
                            }
                        ]
                        if include_authorship
                        else []
                    )
                },
            }
        ],
        "objective_review_history": [feedback],
        "finalists": [],
    }
    next_input = lineage_synthesis_input(
        next_navigation, objective_contract=objective
    )
    next_synthesis = validate_lineage_synthesis_decision(
        next_input,
        {
            "route": "escalate_language",
            "selected_request_ids": [next_request.request_id],
            "deferred_request_ids": [],
            "rationale": "The rejection geometry selects a different chart.",
            "next_discriminator": next_request.discriminating_test,
            "kill_condition": next_request.kill_condition,
            "program_ids": [],
            "next_discriminator_request_ids": [next_request.request_id],
        },
    )
    next_navigation["lineage_synthesis"] = next_synthesis
    next_navigation["language_expansion_request"] = next_request.to_json()
    next_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_language_expansion_requested",
        "context_hash": "context:test",
        "context_summary": {"context_epoch": 0},
        "navigation": next_navigation,
    }
    next_run = {**next_core, "run_digest": content_hash(next_core)}
    return {
        "blueprint": blueprint,
        "observation": observation,
        "feedback": feedback,
        "wave": wave,
        "next_run": next_run,
    }


def test_parameterized_exhaustion_build_and_cold_round_trip_are_backend_free(
    monkeypatch,
) -> None:
    fixture = _fixture()
    prior = fixture["observation"]
    blueprint = fixture["blueprint"]
    interface = construction_witness_interface(
        blueprint.adapter_id, blueprint.adapter_config
    )
    capability_id = explicit_finite_json.CAPABILITY_ID
    original = binary_adapter_module.CAPABILITIES[capability_id]
    calls = {"validate_problem": 0, "enumerate_assignments": 0, "execute_problem": 0}

    def counted_capability(**kwargs):
        operation = str(kwargs.get("operation") or "")
        if operation in calls:
            calls[operation] += 1
        return original(**kwargs)

    monkeypatch.setitem(
        binary_adapter_module.CAPABILITIES,
        capability_id,
        counted_capability,
    )
    parameterization = build_construction_parameterization(
        campaign_id="campaign:parameterized-exhaustion",
        request_id=prior["language_request_id"],
        gap_id="gap:parameterized-exhaustion",
        context_hash=prior["source_family_run"]["context_hash"],
        context_epoch=0,
        adapter_id=blueprint.adapter_id,
        target_interface_sha256=interface["interface_sha256"],
        source_refs=["fixture:parameterized-exhaustion"],
        parameter_space={
            "schema": "leanmill.explicit_finite_parameter_space.v1",
            "variables": [
                {"parameter_id": "row0", "sort": "json_atom", "domain": ["0x1"]},
                {"parameter_id": "row1", "sort": "json_atom", "domain": ["0x2"]},
            ],
        },
        backend_problem=explicit_finite_json.build_problem(
            parameter_ids=["row0", "row1"]
        ),
        materializer={
            "schema": SAFE_ARTIFACT_TEMPLATE_SCHEMA,
            "template": {
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 4,
                "dimension": 2,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": [
                    {"$parameter": "row0"},
                    {"$parameter": "row1"},
                ],
            },
        },
        backend={
            "adapter_id": blueprint.adapter_id,
            "capability_id": capability_id,
            "contract_sha256": content_hash(explicit_finite_json.CONTRACT),
        },
        resource_limits=_construction_limits(),
        search_order={
            "kind": "lexicographic",
            "parameter_ids": ["row0", "row1"],
            "domain_order": "declared_canonical",
        },
    )
    forge = _parameterization_forge_receipt(parameterization, interface)
    family, parameterization_execution = (
        lower_reviewed_construction_parameterization(
            parameterization,
            forge_quarantine_receipt=forge,
            witness_interface=interface,
        )
    )
    assert family is not None
    origin = admit_construction_origin(
        parameterization=parameterization,
        forge_quarantine_receipt=forge,
        parameterization_execution=parameterization_execution,
        witness_interface=interface,
    )
    execution = execute_finite_construction_family(
        family,
        witness_interface=interface,
        capability_fn=_capability,
        construction_origin=origin,
    )
    assert execution["status"] == "exhausted"
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }

    observation = build_reviewed_family_exhaustion_observation(
        source_family_run=prior["source_family_run"],
        blueprint=blueprint,
        active_request=prior["active_language_request"],
        synthesis_input=prior["lineage_synthesis_input"],
        synthesis_decision=prior["lineage_synthesis_decision"],
        family=family,
        forge_quarantine_receipt=forge,
        family_execution=execution,
        frozen_lineage_ids=prior["frozen_lineage_ids"],
        construction_origin=origin,
    )
    assert observation["construction_parameterization"] == dict(
        origin.parameterization
    )
    assert observation["construction_parameterization_execution"] == dict(
        origin.execution
    )
    cold = deepcopy(observation)
    assert validate_reviewed_family_exhaustion_observation(cold) == cold
    assert calls == {
        "validate_problem": 1,
        "enumerate_assignments": 1,
        "execute_problem": 1,
    }


def test_exhaustion_discharge_projects_source_and_unresolved_sibling() -> None:
    fixture = _fixture()
    discharge = build_reviewed_family_exhaustion_discharge(
        observation=fixture["observation"],
        feedback=fixture["feedback"],
        feedback_wave_binding=fixture["wave"],
        next_representation_run=fixture["next_run"],
    )
    assert validate_reviewed_family_exhaustion_discharge(
        discharge, current_blueprint=fixture["blueprint"]
    ) == discharge
    assert discharge["ambient_nonexistence_authority"] is False
    assert discharge["kernel_ratification_authority"] is False
    assert discharge["novelty_authority"] is False

    dispositions = lineage_dispositions_from_reviewed_family_exhaustion_discharge(
        discharge, current_blueprint=fixture["blueprint"]
    )
    by_lineage = {row["lineage_id"]: row for row in dispositions}
    assert by_lineage["lineage:family-author"]["terminal_state"] == (
        "objective_discharged"
    )
    assert by_lineage["legacy-program:sibling-program"]["terminal_state"] == (
        "retired_unresolved"
    )
    assert assert_campaign_closable(
        context_hash="context:test",
        frozen_lineage_ids=(
            "lineage:family-author",
            "legacy-program:sibling-program",
        ),
        lineage_dispositions=dispositions,
    )["ready"] is True


def test_exhaustion_discharge_rejects_stale_and_preoutcome_next_requests() -> None:
    stale = _fixture(next_execution_ref="f" * 64)
    with pytest.raises(ValueError, match="not bound to family exhaustion"):
        build_reviewed_family_exhaustion_discharge(
            observation=stale["observation"],
            feedback=stale["feedback"],
            feedback_wave_binding=stale["wave"],
            next_representation_run=stale["next_run"],
        )


def test_exhaustion_discharge_rejects_rehashed_noncompiler_feedback() -> None:
    fixture = _fixture()
    feedback = fixture["feedback"]
    feedback["authority"] = "post_outcome_host_override"
    feedback["reason"] = "manual_stop"
    feedback["receipt_sha256"] = content_hash(
        {
            key: value
            for key, value in feedback.items()
            if key != "receipt_sha256"
        }
    )
    fixture["wave"]["feedback_receipt_sha256"] = feedback["receipt_sha256"]
    fixture["wave"]["receipt_sha256"] = content_hash(
        {
            key: value
            for key, value in fixture["wave"].items()
            if key != "receipt_sha256"
        }
    )
    fixture["next_run"]["navigation"]["objective_review_history"] = [feedback]
    _rehash_run(fixture["next_run"])
    with pytest.raises(ValueError, match="crossed its execution"):
        build_reviewed_family_exhaustion_discharge(
            observation=fixture["observation"],
            feedback=feedback,
            feedback_wave_binding=fixture["wave"],
            next_representation_run=fixture["next_run"],
        )


def test_exhaustion_discharge_rejects_cross_request_wave_binding() -> None:
    fixture = _fixture()
    fixture["wave"]["request_id"] = "theory-language-request:unrelated"
    fixture["wave"]["receipt_sha256"] = content_hash(
        {
            key: value
            for key, value in fixture["wave"].items()
            if key != "receipt_sha256"
        }
    )
    with pytest.raises(ValueError, match="feedback wave changed identity"):
        build_reviewed_family_exhaustion_discharge(
            observation=fixture["observation"],
            feedback=fixture["feedback"],
            feedback_wave_binding=fixture["wave"],
            next_representation_run=fixture["next_run"],
        )

    preoutcome = _fixture(include_feedback_ref=False)
    with pytest.raises(ValueError, match="not bound to family exhaustion"):
        build_reviewed_family_exhaustion_discharge(
            observation=preoutcome["observation"],
            feedback=preoutcome["feedback"],
            feedback_wave_binding=preoutcome["wave"],
            next_representation_run=preoutcome["next_run"],
        )


def test_exhaustion_discharge_rejects_missing_campaign_authorship() -> None:
    fixture = _fixture(include_authorship=False)
    with pytest.raises(ValueError, match="workbench authorship"):
        build_reviewed_family_exhaustion_discharge(
            observation=fixture["observation"],
            feedback=fixture["feedback"],
            feedback_wave_binding=fixture["wave"],
            next_representation_run=fixture["next_run"],
        )


def test_exhaustion_discharge_rejects_receipt_under_unrelated_trace_event() -> None:
    fixture = _fixture()
    trace = fixture["next_run"]["navigation"]["lineages"][0]["navigation"][
        "trace"
    ][0]
    trace["decision"] = "host_injected"
    trace["capability_id"] = "unrelated_capability"
    _rehash_run(fixture["next_run"])
    with pytest.raises(ValueError, match="workbench authorship"):
        build_reviewed_family_exhaustion_discharge(
            observation=fixture["observation"],
            feedback=fixture["feedback"],
            feedback_wave_binding=fixture["wave"],
            next_representation_run=fixture["next_run"],
        )


def test_exhaustion_discharge_rejects_rehashed_host_authorship_receipt() -> None:
    fixture = _fixture()
    receipt = fixture["next_run"]["navigation"]["lineages"][0]["navigation"][
        "trace"
    ][0]["receipt"]
    receipt["authority"] = "post_outcome_host_override"
    receipt["input_hashes"] = {
        "evidence_refs": receipt["input_hashes"]["evidence_refs"]
    }
    receipt["receipt_id"] = "sha256:" + content_hash(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )
    _rehash_run(fixture["next_run"])
    with pytest.raises(ValueError, match="workbench authorship"):
        build_reviewed_family_exhaustion_discharge(
            observation=fixture["observation"],
            feedback=fixture["feedback"],
            feedback_wave_binding=fixture["wave"],
            next_representation_run=fixture["next_run"],
        )


@pytest.mark.parametrize("mutation", ["family_identity", "member_identity"])
def test_exhaustion_observation_rejects_rehashed_cross_family_execution(
    mutation: str,
) -> None:
    observation = deepcopy(_fixture()["observation"])
    execution = observation["finite_family_execution"]
    if mutation == "family_identity":
        execution["family_id"] = "family:substitute"
        execution["gap_id"] = "gap:substitute"
    else:
        member = execution["member_results"][0]
        member["parameter_id"] = "parameter:substitute"
        member["source_artifact_sha256"] = "f" * 64
        member_core = {
            key: value
            for key, value in member.items()
            if key != "receipt_sha256"
        }
        member["receipt_sha256"] = content_hash(member_core)
        execution["expected_parameter_ids"] = ["parameter:substitute"]
        execution["observed_parameter_ids"] = ["parameter:substitute"]
        observation["member_rejection_receipt_sha256s"] = [
            member["receipt_sha256"]
        ]
    execution_core = {
        key: value
        for key, value in execution.items()
        if key != "receipt_sha256"
    }
    execution["receipt_sha256"] = content_hash(execution_core)
    observation["finite_family_execution_sha256"] = execution["receipt_sha256"]
    observation_core = {
        key: value
        for key, value in observation.items()
        if key != "receipt_sha256"
    }
    observation["receipt_sha256"] = content_hash(observation_core)
    with pytest.raises(ValueError, match="does not cover the reviewed family"):
        validate_reviewed_family_exhaustion_observation(observation)


def test_exhaustion_observation_rejects_omitted_frozen_sibling() -> None:
    observation = deepcopy(_fixture()["observation"])
    observation["frozen_lineage_ids"] = ["lineage:family-author"]
    core = {
        key: value
        for key, value in observation.items()
        if key != "receipt_sha256"
    }
    observation["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="source identity changed"):
        validate_reviewed_family_exhaustion_observation(observation)


def test_exhaustion_discharge_rejects_rehashed_global_overclaim() -> None:
    fixture = _fixture()
    discharge = build_reviewed_family_exhaustion_discharge(
        observation=fixture["observation"],
        feedback=fixture["feedback"],
        feedback_wave_binding=fixture["wave"],
        next_representation_run=fixture["next_run"],
    )
    planted = deepcopy(discharge)
    planted["ambient_nonexistence_authority"] = True
    planted["claim_scope"] = "all target objects in the ambient space fail"
    planted_core = {
        key: value for key, value in planted.items() if key != "receipt_sha256"
    }
    planted["receipt_sha256"] = content_hash(planted_core)
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_reviewed_family_exhaustion_discharge(planted)

    scope_only = deepcopy(discharge)
    scope_only["claim_scope"] = "all target objects in the ambient space fail"
    scope_only["receipt_sha256"] = content_hash(
        {
            key: value
            for key, value in scope_only.items()
            if key != "receipt_sha256"
        }
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_reviewed_family_exhaustion_discharge(scope_only)


def test_unpermitted_stop_contract_preserves_unresolved() -> None:
    blueprint = _blueprint("Stop only after one governed witness is ratified.")
    assert reviewed_family_exhaustion_stop_permission(blueprint) is None


def test_negated_family_stop_clause_preserves_unresolved() -> None:
    blueprint = _blueprint(
        "Stop after one governed witness is ratified; do not stop when one "
        "finite construction family is completely enumerated with replayable "
        "member-level rejection receipts and a typed next representation."
    )
    assert reviewed_family_exhaustion_stop_permission(blueprint) is None


def test_family_clause_mentioned_without_terminal_alternative_is_rejected() -> None:
    blueprint = _blueprint(
        "Stop after one governed witness is ratified; document when one "
        "campaign-authored finite construction family is completely enumerated "
        "with replayable member-level rejection receipts and a typed next "
        "representation."
    )
    assert reviewed_family_exhaustion_stop_permission(blueprint) is None


def test_runner_finalizes_persisted_observation_after_authored_wave(
    tmp_path: Path,
) -> None:
    fixture = _fixture()
    blueprint = fixture["blueprint"]
    observation = fixture["observation"]
    feedback = fixture["feedback"]
    wave = fixture["wave"]
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    write_json_atomic(
        tmp_path
        / (
            "reviewed_family_exhaustion_observation."
            + observation["receipt_sha256"][:16]
            + ".json"
        ),
        observation,
    )
    write_json_atomic(tmp_path / "run.json", fixture["next_run"])
    write_json_atomic(
        tmp_path
        / (
            "theory_language_feedback_wave_binding."
            + feedback["receipt_sha256"][:16]
            + ".wave-001.json"
        ),
        wave,
    )

    updated = _maybe_finalize_reviewed_family_exhaustion(
        tmp_path, blueprint=blueprint
    )

    assert updated is not None
    assert updated["status"] == "frontier_objective_discharged"
    persisted = read_json(tmp_path / "run.json", {})
    assert persisted == updated
    assert persisted["navigation"]["reviewed_family_exhaustion_discharge"][
        "objective_status"
    ] == "discharged_by_reviewed_family_exhaustion_with_typed_successor"
    assert len(list(tmp_path.glob("lineage_disposition.*.json"))) == 2
    assert next_frontier_campaign_action(tmp_path) == "complete"


@pytest.mark.parametrize("prior_state", ["committed", "outstanding", "absent"])
def test_language_advancement_executes_or_replays_exact_family_once(
    tmp_path: Path,
    monkeypatch,
    prior_state: str,
) -> None:
    import ztare.leanmill.frontier_campaign_runner as campaign_runner

    fixture = _fixture()
    observation = fixture["observation"]
    blueprint = fixture["blueprint"]
    family = observation["finite_family"]
    execution = observation["finite_family_execution"]
    forge_receipt = observation["forge_quarantine_receipt"]
    request = observation["active_language_request"]
    gap = AdapterGap(
        brief_digest="brief:family-replay",
        proposed_adapter_id=blueprint.adapter_id,
        primitive_semantics_contract={"theory_language_request": request},
        raw_fixture_refs=(),
        required_context_kind="exact",
        required_operations=(),
        required_receipts=(),
        forbidden_authorities=(),
        acceptance_tests=(),
    )
    run = deepcopy(observation["source_family_run"])
    run["adapter_gap"] = gap.to_json()
    _rehash_run(run)
    write_json_atomic(tmp_path / "run.json", run)
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    if prior_state != "absent":
        write_json_atomic(
            tmp_path / "finite_construction_family_execution.json", execution
        )
        reservation = ledger.reserve(
            "finite-family:" + family["receipt_sha256"],
            "boundary",
            {"boundary_queries": int(family["declared_cardinality"])},
        )
        if prior_state == "committed":
            ledger.commit(reservation)

    monkeypatch.setattr(
        campaign_runner,
        "_load_campaign_attempt",
        lambda _directory: (None, blueprint, None, None, None),
    )
    monkeypatch.setattr(
        campaign_runner,
        "_read_adapter_forge_lifecycle_completion",
        lambda *_args, **_kwargs: {
            "status": "reviewed_campaign_local_finite_family_available"
        },
    )
    monkeypatch.setattr(
        campaign_runner,
        "_approved_finite_family_candidate",
        lambda *_args, **_kwargs: (family, forge_receipt),
    )

    result = advance_frontier_language_expansion(
        tmp_path,
        resume_fn=lambda *_args, **_kwargs: None,
        _attempt_lease=object(),
    )

    assert result["status"] == "finite_family_exhausted"
    assert result["execution_receipt_sha256"] == execution["receipt_sha256"]
    recovered_ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    assert recovered_ledger.state()["usage"]["boundary_queries"] == 1
    assert recovered_ledger.state()["reservations"] == {}
    assert read_json(
        tmp_path / "finite_construction_family_execution.json", {}
    ) == execution
