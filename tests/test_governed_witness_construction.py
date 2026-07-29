from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import ztare.leanmill.reviewed_construction_campaign as reviewed_campaign_module
import ztare.leanmill.explore_axiom_space as explore_axiom_space_module

from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
)
from ztare.leanmill.formal_task_boundary import (
    GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
)
from ztare.leanmill.frontier_agent_runtime import (
    make_subscription_witness_constructor,
)
from ztare.leanmill.campaign_manifest import load_campaign_manifest
from ztare.leanmill.frontier_campaign_definition import FRONTIER_RUNTIME_ROLES
from ztare.leanmill.adapters.binary_linear_code import build_evidence_context
from ztare.leanmill.axiompack_leaf_workbench import (
    axiompack_leaf_workbench_action_environment,
    navigator_decision_output_schema,
)
from ztare.leanmill.exploration_budget import (
    BudgetStopReceipt,
    ExplorationBudget,
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.explore_axiom_space import finish_frontier_navigation
from ztare.leanmill.frontier_campaign_runner import (
    _campaign_construction_candidate_memory,
    _durable_witness_constructor_for_navigator_segment,
    _replay_navigator_decisions,
    _registered_formal_task_executor_required,
    _registered_task_executor_kinds,
    _registered_witness_task_executor_required,
    next_frontier_campaign_action,
)
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill import prompts
from ztare.leanmill.reviewed_construction_campaign import (
    RECOVERED_BOUNDARY_FEEDBACK_SCHEMA,
    bind_recovered_boundary_artifact_feedback,
    durable_witness_construction_candidates,
    pending_cold_witness_boundary_recovery,
    recover_cold_witness_boundary,
    witness_execution_coordinate_from_contract,
)
from ztare.leanmill.theory_adapter_registry import (
    preflight_theory_adapter,
    theory_task_capability_catalog,
)
from ztare.leanmill.theory_ir import SortDecl, TheorySignature, content_hash
from ztare.leanmill.theory_program import THEORY_PROGRAM_V2, TheoryProgram
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_navigator import _resolve_theory_task_contracts
from ztare.leanmill.theory_task_boundary_registry import (
    DATA_ONLY_WITNESS_EXECUTOR,
    FORMALIZATION_CAMPAIGN_EXECUTOR,
    registered_theory_task_boundary_handler,
    theory_task_journal_projection,
    theory_task_work_reservation,
    validate_registered_theory_task_boundary_result,
)
from ztare.leanmill.witness_construction_boundary import (
    GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
    WITNESS_CONSTRUCTION_CLAIM_SCOPE,
    WitnessConstructionCandidateEnvelope,
    WitnessConstructionCapabilityUnavailable,
    WitnessConstructorUnavailable,
    adjudicate_governed_witness_construction_task,
    build_witness_candidate_outcome_memory,
    build_witness_construction_interface,
    build_witness_constructor_output,
    build_witness_constructor_request,
    compile_governed_witness_construction_task,
    execute_governed_witness_construction_task,
    matching_witness_candidate_outcome,
    validate_witness_construction_boundary_result,
    validate_witness_construction_interface,
    validate_witness_candidate_outcome_memory,
    validate_witness_constructor_output,
    validate_witness_constructor_request,
)


def _interface(*, policy: str = "construction_artifact_ratification_required") -> dict:
    return build_witness_construction_interface(
        predicate_ir={"kind": "field_equals", "field": "value", "expected": 2},
        witness_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {"value": {"type": "integer"}},
        },
        normalizer={
            "capability_id": "normalize_explicit_candidate",
            "contract": {"kind": "identity_v1"},
        },
        verifier={
            "capability_id": "verify_frozen_predicate",
            "contract": {"kind": "exact_replay_v1"},
        },
        discharge_policy=policy,
        target_config_sha256=content_hash({"target": 2}),
    )


def _orientation() -> dict:
    return {
        "eigenquestion": "Can one explicit data object meet the frozen predicate?",
        "representation_choice": "Use the schema's single canonical coordinate.",
        "expected_failure_mode": "The coordinate may miss the required value.",
        "next_revision_if_rejected": "Revise the coordinate and resubmit a new task.",
    }


def _compiled_contract(
    *,
    policy: str = "construction_artifact_ratification_required",
    context_hash: str = "context:frozen",
    formula_id: str = "formula:a",
    artifact_value: int = 2,
) -> tuple[TaskDischargeContract, dict]:
    interface = _interface(policy=policy)
    context = SimpleNamespace(
        context_hash=context_hash,
        formula_ids=(formula_id,),
    )
    original_evidence = ["selection:receipt"]
    constructor_request = build_witness_constructor_request(
        context_hash=context.context_hash,
        adapter_id="test_adapter.v1",
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": [formula_id],
            "goal": "Construct one explicit witness.",
            "observable": "The frozen predicate accepts it.",
            "evidence_refs": original_evidence,
            "kill_condition": "Reject when exact replay fails.",
            "construction_brief": "Search the canonical one-coordinate chart.",
        },
    )
    authored = build_witness_constructor_output(
        constructor_request,
        artifact={"value": artifact_value},
        orientation=_orientation(),
        role="witness_constructor",
        agent_id="axiompack-witness-constructor",
        call_receipt_sha256="c" * 64,
    )
    public_fields = (
        "predicate_ir",
        "witness_schema",
        "normalizer",
        "verifier",
        "discharge_policy",
        "target_config_sha256",
        "interface_sha256",
    )
    core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "presentation_formula_ids": [formula_id],
        "goal": "Construct one explicit witness.",
        "observable": "The frozen predicate accepts it.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": original_evidence
        + [
            "witness-constructor-authorship:"
            + authored["authorship_receipt"]["receipt_sha256"]
        ],
        "kill_condition": "Reject when exact replay fails.",
        "authority": "leaf_request_host_bound",
        "witness_construction": {
            **{field: interface[field] for field in public_fields},
            "constructor_request": constructor_request,
            "artifact": authored["artifact"],
            "orientation": authored["orientation"],
            "authorship_receipt": authored["authorship_receipt"],
        },
    }
    request = {
        **core,
        "request_id": "theory-task-request:" + content_hash(core),
    }
    lowered = compile_governed_witness_construction_task(
        request=request,
        context=context,
        adapter_id="test_adapter.v1",
        construction_interface=interface,
    )
    assert lowered is not None
    contract = TaskDischargeContract(
        contract_id="task:witness",
        adjudicator_id=lowered["adjudicator_id"],
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters=lowered["parameters"],
    )
    return contract, interface


def _outer_boundary(contract: TaskDischargeContract, row: dict) -> dict:
    core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": contract.parameters["context_hash"],
        "query_results": [row],
        "stop_reason": "completed",
        "next_epoch_proposal": None,
    }
    return {**core, "result_sha256": content_hash(core)}


def _accepting_verifier(**kwargs) -> dict:
    return {
        "outcome": "accepted",
        "observed": {
            "predicate": kwargs["predicate_ir"],
            "artifact": kwargs["normalized_artifact"],
        },
        "evidence_refs": ["host-verifier:accepted"],
    }


def test_public_interface_and_candidate_envelope_reject_hidden_or_executable_data() -> None:
    interface = _interface()
    assert validate_witness_construction_interface(interface) == interface

    hidden = copy.deepcopy(interface)
    hidden["predicate_ir"]["sealed_examples"] = [{"value": 2}]
    core = {key: value for key, value in hidden.items() if key != "interface_sha256"}
    hidden["interface_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="forbidden evidence"):
        validate_witness_construction_interface(hidden)

    contract, _ = _compiled_contract()
    candidate_row = copy.deepcopy(contract.parameters["candidate_envelope"])
    candidate_row["artifact"]["opaque"] = (1, 2)
    with pytest.raises(TypeError, match="data-only JSON"):
        WitnessConstructionCandidateEnvelope.from_json(candidate_row)

    candidate_row = copy.deepcopy(contract.parameters["candidate_envelope"])
    candidate_row["extra"] = "crossing"
    with pytest.raises(ValueError, match="fields changed identity"):
        WitnessConstructionCandidateEnvelope.from_json(candidate_row)


def test_constructor_authorship_binds_artifact_orientation_and_task_intent() -> None:
    contract, interface = _compiled_contract()
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    assert candidate.orientation["eigenquestion"]
    assert candidate.authorship_receipt["role"] == "witness_constructor"

    crossed = copy.deepcopy(contract.parameters["candidate_envelope"])
    crossed["artifact"]["value"] = 3
    crossed["artifact_sha256"] = content_hash(crossed["artifact"])
    core = {key: value for key, value in crossed.items() if key != "receipt_sha256"}
    crossed["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="authorship"):
        WitnessConstructionCandidateEnvelope.from_json(crossed)

    request = candidate.constructor_request
    output = build_witness_constructor_output(
        request,
        artifact=candidate.artifact,
        orientation=candidate.orientation,
        role="witness_constructor",
        agent_id="axiompack-witness-constructor",
        call_receipt_sha256="c" * 64,
    )
    assert validate_witness_constructor_output(request, output) == output
    assert interface["claim_boundary"].endswith("no_sealed_evidence")


def test_verification_is_deterministic_and_ratification_policy_stays_open() -> None:
    contract, _ = _compiled_contract()
    row = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=_accepting_verifier,
    )
    assert validate_witness_construction_boundary_result(contract, row) == row
    receipt = adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=_outer_boundary(contract, row),
    )
    assert receipt.status == "open"
    assert receipt.observed["next_obligation"] == (
        "construction_artifact_ratification"
    )
    assert receipt.observed["verifier_observed"]["artifact"] == {"value": 2}

    terminal_contract, _ = _compiled_contract(
        policy="verifier_acceptance_is_terminal"
    )
    terminal_row = execute_governed_witness_construction_task(
        terminal_contract,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=_accepting_verifier,
    )
    terminal_receipt = adjudicate_governed_witness_construction_task(
        contract=terminal_contract,
        boundary_result=_outer_boundary(terminal_contract, terminal_row),
    )
    assert terminal_receipt.status == "discharged"


def test_rejection_unavailability_and_nondeterminism_are_typed_separately() -> None:
    contract, _ = _compiled_contract()

    rejected = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=lambda **_kwargs: {
            "outcome": "rejected",
            "observed": {"reason": "predicate_false"},
            "evidence_refs": ["host-verifier:rejected"],
        },
    )
    rejected_receipt = adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=_outer_boundary(contract, rejected),
    )
    assert rejected_receipt.status == "open"

    def unavailable(**_kwargs):
        raise WitnessConstructionCapabilityUnavailable("verifier_runtime_absent")

    unavailable_row = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=unavailable,
    )
    unavailable_receipt = adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=_outer_boundary(contract, unavailable_row),
    )
    assert unavailable_receipt.status == "unavailable"

    counter = {"value": 0}

    def nondeterministic(**_kwargs):
        counter["value"] += 1
        return {"value": counter["value"]}

    with pytest.raises(ValueError, match="nondeterministic"):
        execute_governed_witness_construction_task(
            contract,
            normalizer_fn=nondeterministic,
            verifier_fn=_accepting_verifier,
        )


def test_handler_registry_keeps_formal_witness_and_unknown_crossings_separate() -> None:
    witness, _ = _compiled_contract()
    formal = TaskDischargeContract(
        contract_id="task:formal",
        adjudicator_id=GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters={"kind": "test-only"},
    )
    unknown = TaskDischargeContract(
        contract_id="task:unknown",
        adjudicator_id="unregistered.task.v1",
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters={},
    )
    program = TheoryProgram(
        schema=THEORY_PROGRAM_V2,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash="context:frozen",
        context_epoch=0,
        presentation_formula_ids=("formula:a",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:receipt",
        task_discharge_contracts=(formal, witness, unknown),
    )
    navigation = {"finalists": [{"theory_program": program.to_json()}]}
    assert _registered_task_executor_kinds(navigation) == frozenset(
        {FORMALIZATION_CAMPAIGN_EXECUTOR, DATA_ONLY_WITNESS_EXECUTOR}
    )
    assert _registered_formal_task_executor_required(navigation) is True
    assert _registered_witness_task_executor_required(navigation) is True
    assert registered_theory_task_boundary_handler(unknown.adjudicator_id) is None

    assert theory_task_work_reservation(witness, {}) == {}
    assert theory_task_work_reservation(formal, {})["lean_attempts"] == 1
    verified = execute_governed_witness_construction_task(
        witness,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=_accepting_verifier,
    )
    assert theory_task_journal_projection(witness, verified) == {
        "evidence_status": "witnessed",
        "authority": "frontier_boundary_witness_construction_join",
    }
    with pytest.raises(ValueError):
        validate_registered_theory_task_boundary_result(formal, verified)


def test_mixed_boundary_dispatches_each_registered_handler_once_and_replays(
    tmp_path, monkeypatch
) -> None:
    from test_theory_navigator import _context_and_blueprint
    import ztare.leanmill.formal_task_boundary as formal_boundary

    context, source_blueprint = _context_and_blueprint()
    presentation = context.formula_ids[0]
    witness, _ = _compiled_contract(
        context_hash=context.context_hash,
        formula_id=presentation,
    )
    formal = TaskDischargeContract(
        contract_id="task:formal-mixed",
        adjudicator_id=GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters={"kind": "test-only"},
    )
    unknown = TaskDischargeContract(
        contract_id="task:unknown-mixed",
        adjudicator_id="unregistered.task.v1",
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters={},
    )
    program = TheoryProgram(
        schema=THEORY_PROGRAM_V2,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=(presentation,),
        prediction_formula_ids=(),
        selection_receipt_id="selection:mixed",
        task_discharge_contracts=(formal, witness, unknown),
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "formula_ids": list(program.presentation_formula_ids),
                "boundary_target_ids": [],
                "residual_prediction_formula_ids": [],
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ]
    }
    blueprint = replace(
        source_blueprint,
        navigator_contract={
            **source_blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
        query_budget={**source_blueprint.query_budget, "boundary_queries": 4},
    )
    witness_row = execute_governed_witness_construction_task(
        witness,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=_accepting_verifier,
    )
    formal_core = {
        "candidate_kind": "theory_task",
        "contract_sha256": formal.sha256,
        "adjudicator_id": formal.adjudicator_id,
        "status": "kernel_verified_test",
    }
    formal_row = {**formal_core, "receipt_sha256": content_hash(formal_core)}

    def validate_formal(contract, row):
        assert contract.sha256 == formal.sha256
        assert dict(row) == formal_row
        return dict(row)

    monkeypatch.setattr(
        formal_boundary, "validate_formal_task_boundary_result", validate_formal
    )
    calls: list[str] = []

    def dispatch(contract, **_kwargs):
        calls.append(contract.adjudicator_id)
        if contract.adjudicator_id == formal.adjudicator_id:
            return formal_row
        if contract.adjudicator_id == witness.adjudicator_id:
            return witness_row
        raise AssertionError("unknown adjudicator reached a boundary executor")

    first = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "first.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "first.budget.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt:first",
        ),
        attempt_id="attempt:first",
        campaign_id="campaign:test",
        theory_task_executor_fn=dispatch,
    ).to_json()
    assert calls == [formal.adjudicator_id, witness.adjudicator_id]
    assert first["query_results"] == [formal_row, witness_row]

    replay = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "replay.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "replay.budget.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt:replay",
        ),
        attempt_id="attempt:replay",
        campaign_id="campaign:test",
        theory_task_executor_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("archived task row reached an executor")
        ),
        prior_query_results=first["query_results"],
    ).to_json()
    assert replay["query_results"] == first["query_results"]


def test_static_first_client_catalog_is_config_bound() -> None:
    config = {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 4,
            "dimension": 2,
            "minimum_distance": 2,
            "max_nonzero_messages": 3,
            "target_snapshot_sha256": "a" * 64,
        }
    }
    rows = theory_task_capability_catalog(
        "binary_linear_code.v1", adapter_config=config
    )
    assert len(rows) == 1
    assert rows[0]["capability_id"] == "governed_witness_construction"
    assert rows[0]["interface"]["target_config_sha256"] == content_hash(config)
    changed = copy.deepcopy(config)
    changed["construction_target"]["minimum_distance"] = 3
    assert theory_task_capability_catalog(
        "binary_linear_code.v1", adapter_config=changed
    )[0]["interface"]["interface_sha256"] != rows[0]["interface"][
        "interface_sha256"
    ]


def test_binary_campaign_manifest_uses_the_canonical_runtime_role_identity() -> None:
    import ztare.leanmill.campaign_manifest as manifest_module

    assert set(manifest_module._AXIOMPACK_ROLES) == set(FRONTIER_RUNTIME_ROLES)
    campaign = load_campaign_manifest(
        Path(__file__).resolve().parents[1]
        / "research_areas/pre_registrations"
        / "axiompack_binary_linear_code_frontier_v1_20260717"
        / "campaign.md"
    )
    overrides = set(campaign.runtime.get("role_overrides") or {})
    assert {"witness_constructor", "external_science_reviewer"} <= overrides


def _binary_campaign_config() -> dict:
    return {
        "construction_target": {
            "schema": "leanmill.binary_linear_code_target_config.v1",
            "field_order": 2,
            "length": 4,
            "dimension": 2,
            "minimum_distance": 2,
            "max_nonzero_messages": 3,
            "target_snapshot_sha256": "a" * 64,
        },
        "evidence_panel": {
            "schema": "leanmill.binary_linear_code_evidence_panel.v1",
            "field_order": 1,
            "completeness_scope": "declared_control_panel_only",
            "completeness_ref": "fixture:declared-panel",
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


def test_static_first_client_registry_preflight_resolves_frozen_campaign_config() -> None:
    config = _binary_campaign_config()
    receipt = preflight_theory_adapter(
        "binary_linear_code.v1",
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config=config,
        formula_grammar={},
        strata=(),
    )
    assert receipt["adapter_id"] == "binary_linear_code.v1"
    assert receipt["complete_census_available"] is True
    assert receipt["target_config_sha256"] == content_hash(config)


def test_workbench_routes_task_brief_to_constructor_and_never_accepts_leaf_artifact() -> None:
    config = _binary_campaign_config()
    context = build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config=config,
        strata=(),
    )
    interface = theory_task_capability_catalog(
        "binary_linear_code.v1", adapter_config=config
    )[0]["interface"]
    public_fields = (
        "predicate_ir",
        "witness_schema",
        "normalizer",
        "verifier",
        "discharge_policy",
        "target_config_sha256",
        "interface_sha256",
    )

    constructor_calls = []

    def constructor(request):
        constructor_calls.append(request["request_sha256"])
        return build_witness_constructor_output(
            request,
            artifact={
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 4,
                "dimension": 2,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": ["0x3", "0xc"],
            },
            orientation=_orientation(),
            role="witness_constructor",
            agent_id="axiompack-witness-constructor",
            call_receipt_sha256="d" * 64,
        )

    environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        witness_constructor_fn=constructor,
    )
    inputs = {
        "formula_ids": ["property:one"],
        "goal": "Construct one explicit target witness.",
        "observable": "Exact target verification accepts it.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": ["selection:receipt"],
        "kill_condition": "Reject after exact replay failure.",
        "witness_construction": {
            **{field: interface[field] for field in public_fields},
            "construction_brief": "Search locally for a canonical generator.",
        },
    }
    receipt = environment["action_handlers"]["propose_theory_task"](
        ".", {"input_refs": inputs}, None, environment["contract"]
    )
    summary = receipt["output_summary"]
    assert summary["status"] == "compiled_theory_task"
    authored = summary["task_request"]["witness_construction"]
    assert authored["artifact"]["rows_hex"] == ["0x3", "0xc"]
    assert authored["authorship_receipt"]["role"] == "witness_constructor"
    assert authored["orientation"]["eigenquestion"]
    resolved = _resolve_theory_task_contracts(
        ({"receipt": receipt},),
        (summary["task_contract_id"],),
        context_hash=context.context_hash,
        adapter_id="binary_linear_code.v1",
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        presentation_formula_ids=("property:one",),
    )
    assert resolved[0].contract_id == summary["task_contract_id"]

    host_carried_inputs = {
        key: value for key, value in inputs.items() if key != "witness_construction"
    }
    host_carried = environment["action_handlers"]["propose_theory_task"](
        ".", {"input_refs": host_carried_inputs}, None, environment["contract"]
    )["output_summary"]
    assert host_carried["status"] == "compiled_theory_task"
    carried_request = host_carried["task_request"]["witness_construction"]
    assert carried_request["constructor_request"]["task_intent"][
        "construction_brief"
    ] == host_carried_inputs["goal"]
    assert carried_request["interface_sha256"] == interface["interface_sha256"]

    crossed_presentation = copy.deepcopy(inputs)
    crossed_presentation["formula_ids"] = ["theory-program:not-a-formula"]
    calls_before_crossing = len(constructor_calls)
    with pytest.raises(ValueError, match="crossed its frozen presentation"):
        environment["action_handlers"]["propose_theory_task"](
            ".",
            {"input_refs": crossed_presentation},
            None,
            environment["contract"],
        )
    assert len(constructor_calls) == calls_before_crossing

    leaf_authored = copy.deepcopy(inputs)
    leaf_authored["witness_construction"]["artifact"] = authored["artifact"]
    with pytest.raises(ValueError, match="public interface"):
        environment["action_handlers"]["propose_theory_task"](
            ".", {"input_refs": leaf_authored}, None, environment["contract"]
        )

    unavailable_environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
    )
    unavailable = unavailable_environment["action_handlers"][
        "propose_theory_task"
    ](".", {"input_refs": inputs}, None, unavailable_environment["contract"])
    assert unavailable["output_summary"]["status"] == (
        "witness_constructor_unavailable"
    )
    assert unavailable["output_summary"]["task_contract"] is None


def test_resumed_constructor_sees_outcome_memory_and_duplicate_cannot_compile() -> None:
    config = _binary_campaign_config()
    context = build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config=config,
        strata=(),
    )
    interface = theory_task_capability_catalog(
        "binary_linear_code.v1", adapter_config=config
    )[0]["interface"]
    first_artifact = {
        "schema": "leanmill.binary_linear_generator_matrix.v1",
        "field_order": 2,
        "length": 4,
        "dimension": 2,
        "coordinate_convention": "bit_i_is_coordinate_i",
        "rows_hex": ["0x3", "0xc"],
    }
    second_artifact = {**first_artifact, "rows_hex": ["0x5", "0xa"]}
    inputs = {
        "formula_ids": ["property:one"],
        "goal": "Construct one explicit target witness.",
        "observable": "Exact target verification accepts it.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": ["selection:receipt"],
        "kill_condition": "Reject after exact replay failure.",
    }

    def author(artifact):
        def constructor(request):
            return build_witness_constructor_output(
                request,
                artifact=artifact,
                orientation=_orientation(),
                role="witness_constructor",
                agent_id="axiompack-witness-constructor",
                call_receipt_sha256="d" * 64,
            )

        return constructor

    first_environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        witness_constructor_fn=author(first_artifact),
    )
    first = first_environment["action_handlers"]["propose_theory_task"](
        ".", {"input_refs": inputs}, None, first_environment["contract"]
    )["output_summary"]
    contract = TaskDischargeContract.from_dict(first["task_contract"])
    envelope = contract.parameters["candidate_envelope"]
    normalized_sha = content_hash(first_artifact)
    boundary_receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="leanmill.frontier_boundary",
        observed={
            "candidate_envelope_sha256": envelope["receipt_sha256"],
            "boundary_status": "witness_rejected",
            "normalized_artifact_sha256": normalized_sha,
            "verifier_observed": {
                "status": "low_weight_counterexample",
                "observed_rank": 2,
                "distance_replay": {"minimum_distance": 1},
            },
        },
        evidence_refs=("boundary-row:" + "a" * 64,),
    )
    candidate_outcome = {
        "source_artifact_sha256": envelope["artifact_sha256"],
        "normalized_artifact_sha256": normalized_sha,
        "boundary_status": "witness_rejected",
        "verifier_status": "low_weight_counterexample",
        "observed": boundary_receipt.observed["verifier_observed"],
        "evidence_refs": [
            contract.sha256,
            boundary_receipt.sha256,
            *boundary_receipt.evidence_refs,
        ],
    }
    memory = build_witness_candidate_outcome_memory(
        adapter_id="binary_linear_code.v1",
        construction_interface=interface,
        outcomes=(candidate_outcome,),
    )
    assert validate_witness_candidate_outcome_memory(memory) == memory
    assert matching_witness_candidate_outcome(
        memory, content_hash(first_artifact)
    )

    duplicate_environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        witness_constructor_fn=author(first_artifact),
        candidate_outcome_memory=memory,
    )
    duplicate = duplicate_environment["action_handlers"][
        "propose_theory_task"
    ](".", {"input_refs": inputs}, None, duplicate_environment["contract"])[
        "output_summary"
    ]
    assert duplicate["status"] == "candidate_duplicate"
    assert duplicate["task_contract"] is None

    fresh_environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        witness_constructor_fn=author(second_artifact),
        candidate_outcome_memory=memory,
    )
    fresh = fresh_environment["action_handlers"]["propose_theory_task"](
        ".", {"input_refs": inputs}, None, fresh_environment["contract"]
    )["output_summary"]
    assert fresh["status"] == "compiled_theory_task"
    request = fresh["task_request"]["witness_construction"][
        "constructor_request"
    ]
    assert request["schema"] == "leanmill.witness_constructor_request.v2"
    assert request["candidate_outcome_memory"] == memory


def test_candidate_memory_rejects_rehashed_outer_candidate_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract, interface = _compiled_contract(context_hash="context:memory")
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    monkeypatch.setattr(
        "ztare.leanmill.theory_adapter_registry.theory_task_capability_catalog",
        lambda *_args, **_kwargs: ({
            "capability_id": "governed_witness_construction",
            "interface": interface,
        },),
    )
    observed = {
        "request_id": contract.parameters["request_id"],
        "candidate_envelope_sha256": candidate.receipt_sha256,
        "boundary_status": "witness_rejected",
        "normalized_artifact_sha256": candidate.to_json()["artifact_sha256"],
        "verifier_observed": {
            "status": "rejected",
            "reason": "fixture_miss",
        },
        "claim_scope": contract.parameters["claim_scope"],
        "discharge_policy": candidate.discharge_policy,
        "next_obligation": None,
    }

    def persist_bundle(
        frozen_contract: TaskDischargeContract,
        frozen_receipt: TaskDischargeReceipt,
    ) -> None:
        row_core = {
            "source": "explicit_task",
            "contract_sha256": frozen_contract.sha256,
            "contract": frozen_contract.to_dict(),
            "receipt": frozen_receipt.to_dict(),
        }
        row = {**row_core, "receipt_sha256": content_hash(row_core)}
        bundle_core = {
            "schema": "leanmill.theory_task_discharge.v1",
            "rows": [row],
            "authority": "registered_adapter_receipts_host_aggregation",
        }
        _write_json(
            tmp_path / "theory_task_discharge.json",
            {**bundle_core, "receipt_sha256": content_hash(bundle_core)},
        )

    valid_receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="leanmill.frontier_boundary",
        observed=observed,
        evidence_refs=("boundary-row:" + "a" * 64,),
    )
    persist_bundle(contract, valid_receipt)
    blueprint = SimpleNamespace(
        adapter_id="test_adapter.v1",
        adapter_config={},
    )
    memory = _campaign_construction_candidate_memory(tmp_path, blueprint)
    assert memory is not None
    assert memory["outcomes"][0]["source_artifact_sha256"] == candidate.to_json()[
        "artifact_sha256"
    ]

    crossed_parameters = copy.deepcopy(dict(contract.parameters))
    crossed_parameters["candidate_envelope_sha256"] = "0" * 64
    crossed_contract = TaskDischargeContract(
        contract_id=contract.contract_id,
        adjudicator_id=contract.adjudicator_id,
        lifecycle_scope=contract.lifecycle_scope,
        owner=contract.owner,
        parameters=crossed_parameters,
    )
    receipt = TaskDischargeReceipt(
        contract_sha256=crossed_contract.sha256,
        adjudicator_id=crossed_contract.adjudicator_id,
        status="open",
        authority="leanmill.frontier_boundary",
        observed=observed,
        evidence_refs=("boundary-row:" + "a" * 64,),
    )
    persist_bundle(crossed_contract, receipt)

    with pytest.raises(
        ValueError,
        match="witness candidate crossed its frozen task",
    ):
        _campaign_construction_candidate_memory(tmp_path, blueprint)

    untrusted_receipt = TaskDischargeReceipt(
        contract_sha256=contract.sha256,
        adjudicator_id=contract.adjudicator_id,
        status="open",
        authority="untrusted.fixture",
        observed=observed,
        evidence_refs=("boundary-row:" + "a" * 64,),
    )
    persist_bundle(contract, untrusted_receipt)
    with pytest.raises(
        ValueError,
        match="witness task receipt has unsupported authority",
    ):
        _campaign_construction_candidate_memory(tmp_path, blueprint)


def test_resolver_ignores_unrequested_historical_task_presentations() -> None:
    config = _binary_campaign_config()
    config["evidence_panel"]["hypotheses"].append(
        {
            "hypothesis_id": "property:other",
            "satisfied_object_ids": ["control:one"],
            "anonymous_shape": {"kind": "control", "complexity": 1},
            "payload": {"checker_ref": "fixture:other"},
        }
    )
    context = build_evidence_context(
        TheorySignature(name="Evidence", sorts=(SortDecl("Observation"),)),
        adapter_config=config,
        strata=(),
    )

    def constructor(request):
        return build_witness_constructor_output(
            request,
            artifact={
                "schema": "leanmill.binary_linear_generator_matrix.v1",
                "field_order": 2,
                "length": 4,
                "dimension": 2,
                "coordinate_convention": "bit_i_is_coordinate_i",
                "rows_hex": ["0x3", "0xc"],
            },
            orientation=_orientation(),
            role="witness_constructor",
            agent_id="axiompack-witness-constructor",
            call_receipt_sha256="d" * 64,
        )

    environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="binary_linear_code.v1",
        theory_adapter_config=config,
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        witness_constructor_fn=constructor,
    )

    def compile_task(formula_ids):
        return environment["action_handlers"]["propose_theory_task"](
            ".",
            {
                "input_refs": {
                    "formula_ids": list(formula_ids),
                    "goal": "Construct one explicit target witness.",
                    "observable": "Exact target verification accepts it.",
                    "adjudicator_capability": "governed_witness_construction",
                    "evidence_refs": ["selection:receipt"],
                    "kill_condition": "Reject after exact replay failure.",
                }
            },
            None,
            environment["contract"],
        )

    historical = compile_task(("property:other",))
    selected_presentation = ("property:one",)
    selected = compile_task(selected_presentation)
    selected_id = selected["output_summary"]["task_contract_id"]

    resolved = _resolve_theory_task_contracts(
        ({"receipt": historical}, {"receipt": selected}),
        (selected_id,),
        context_hash=context.context_hash,
        adapter_id="binary_linear_code.v1",
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        presentation_formula_ids=selected_presentation,
    )

    assert tuple(row.contract_id for row in resolved) == (selected_id,)


class _FakeConstructorRole:
    role = "witness_constructor"
    agent_id = "axiompack-witness-constructor"

    def __init__(self, *, visible: bool) -> None:
        self.config = SimpleNamespace(visible_workbench=visible)
        self.budget_ledger = None
        self.calls: list[dict] = []

    @property
    def provider_call_count(self) -> int:
        return len([row for row in self.calls if not row.get("replayed")])

    def __call__(self, prompt: str) -> dict:
        self.calls.append(
            {
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": self.role,
                "agent_id": self.agent_id,
                "runtime": "codex",
                "model": "gpt-5.4-mini",
                "prompt_digest": content_hash({"prompt": prompt}),
                "returncode": 0,
                "provider_call_charge": 1,
                "wallclock_s": 1.0,
                "stdout_digest": "stdout:test",
                "stderr_digest": "stderr:test",
                "result_digest": "result:test",
                "output_schema_digest": "",
            }
        )
        return {"artifact": {"value": 2}, "orientation": _orientation()}


def test_distinct_constructor_role_requires_visible_workbench_and_binds_call() -> None:
    interface = _interface()
    request = build_witness_constructor_request(
        context_hash="context:frozen",
        adapter_id="test_adapter.v1",
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": ["formula:a"],
            "goal": "Construct one explicit witness.",
            "observable": "The predicate accepts.",
            "evidence_refs": ["selection:receipt"],
            "kill_condition": "Reject on replay failure.",
            "construction_brief": "Search the canonical coordinate.",
        },
    )
    hidden = make_subscription_witness_constructor(
        _FakeConstructorRole(visible=False)
    )
    with pytest.raises(WitnessConstructorUnavailable, match="visible"):
        hidden(request)

    visible = make_subscription_witness_constructor(
        _FakeConstructorRole(visible=True)
    )
    output = visible(request)
    assert validate_witness_constructor_output(request, output) == output
    assert output["authorship_receipt"]["role"] == "witness_constructor"
    assert output["claim_boundary"].startswith("orientation_is_non_authoritative")


def test_constructor_does_not_dispatch_without_its_leaf_continuation(tmp_path) -> None:
    interface = _interface()
    request = build_witness_constructor_request(
        context_hash="context:frozen",
        adapter_id="test_adapter.v1",
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": ["formula:a"],
            "goal": "Construct one explicit witness.",
            "observable": "The predicate accepts.",
            "evidence_refs": ["selection:receipt"],
            "kill_condition": "Reject on replay failure.",
            "construction_brief": "Search the canonical coordinate.",
        },
    )
    role = _FakeConstructorRole(visible=True)
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "constructor-budget.events.jsonl",
        budget,
        attempt_id="attempt-constructor-causal-budget",
    )
    role.budget_ledger = ledger
    constructor = make_subscription_witness_constructor(role)
    constructor.continuation_turn_available = False

    with pytest.raises(
        WitnessConstructorUnavailable,
        match="causal_continuation_unavailable",
    ):
        constructor(request)

    assert role.calls == []
    assert ledger.state()["usage"]["provider_calls"] == 0

    constructor.continuation_turn_available = True
    capacity = {
        resource: ledger.remaining_capacity("navigation", resource)
        for resource in ("provider_calls", "agent_turns")
    }
    prior = ledger.reserve(
        "fixture:leave-one-causal-unit",
        "navigation",
        {resource: value - 1 for resource, value in capacity.items()},
    )
    ledger.commit(prior)
    with pytest.raises(
        WitnessConstructorUnavailable,
        match="causal_continuation_unavailable",
    ):
        constructor(request)
    assert role.calls == []


def test_recovery_rebinds_exact_completed_sibling_constructor_without_dispatch(
    tmp_path: Path,
) -> None:
    definition = FrontierCampaignDefinition(
        direction="Recover a completed data-only construction.",
        source_mode="structure_first",
        budget=budget_preset("smoke_20m"),
    )
    interface = _interface()
    request = build_witness_constructor_request(
        context_hash="context:frozen",
        adapter_id="test_adapter.v1",
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": ["formula:a"],
            "goal": "Construct one explicit witness.",
            "observable": "The predicate accepts.",
            "evidence_refs": ["selection:receipt"],
            "kill_condition": "Reject on replay failure.",
            "construction_brief": "Search the canonical coordinate.",
        },
    )
    instance = "lineage-000.wave-001"
    navigator_dir = tmp_path / "agent_calls" / f"navigator.{instance}"
    navigator_dir.mkdir(parents=True)
    sibling = tmp_path / "agent_calls" / f"witness_constructor.{instance}"
    sibling.mkdir(parents=True)
    prompt = prompts.AXIOMPACK_WITNESS_CONSTRUCTOR_PROMPT.format(
        construction_request_json=json.dumps(
            request, sort_keys=True, separators=(",", ":")
        )
    )
    raw = {"artifact": {"value": 2}, "orientation": _orientation()}
    result_text = json.dumps(raw, sort_keys=True, separators=(",", ":"))

    def write_call(index: int, frozen_prompt: str) -> None:
        prefix = sibling / f"{index:03d}"
        prefix.with_suffix(".prompt.txt").write_text(
            frozen_prompt, encoding="utf-8"
        )
        prefix.with_suffix(".stdout.txt").write_text(
            result_text, encoding="utf-8"
        )
        prefix.with_suffix(".result.json").write_text(
            result_text, encoding="utf-8"
        )
        prefix.with_suffix(".call.json").write_text(json.dumps({
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": "witness_constructor",
                "agent_id": f"axiompack-witness_constructor-{instance}",
                "runtime": "codex",
                "model": "gpt-5.4-mini",
                "prompt_digest": content_hash({"prompt": frozen_prompt}),
                "returncode": 0,
                "provider_call_charge": 1,
                "wallclock_s": 1.0,
                "stdout_digest": content_hash({"stdout": result_text}),
                "stderr_digest": content_hash({"stderr": ""}),
                "result_digest": content_hash({"result": result_text}),
                "output_schema_digest": "",
            }, sort_keys=True), encoding="utf-8")

    write_call(0, "a prior constructor prompt skipped by changed host semantics")
    write_call(1, prompt)

    constructor = _durable_witness_constructor_for_navigator_segment(
        definition, tmp_path, navigator_dir
    )

    assert constructor is not None
    output = constructor(request)
    assert validate_witness_constructor_output(request, output) == output
    assert output["artifact"] == {"value": 2}
    assert constructor.call_role.provider_call_count == 0
    assert constructor.call_role.calls[0]["skipped_by_prompt_indexed_recovery"]


def test_durable_navigation_replay_preserves_authoritative_candidate_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = {"schema": "fixture.authoritative_candidate_memory.v1"}
    captured: dict[str, object] = {}

    def replay_stub(*_args, **kwargs):
        captured["candidate_outcome_memory"] = kwargs.get(
            "candidate_outcome_memory"
        )
        return {"status": "replayed"}

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.run_interactive_theory_navigator",
        replay_stub,
    )
    result = _replay_navigator_decisions(
        SimpleNamespace(),
        SimpleNamespace(query_budget={"max_finalists": 1}),
        [{"decision": "finish", "rationale": "Replay frozen bytes."}],
        SimpleNamespace(),
        attempt_id="attempt:memory-replay",
        campaign_id="campaign:memory-replay",
        epoch=0,
        candidate_outcome_memory=memory,
    )

    assert result == {"status": "replayed"}
    assert captured["candidate_outcome_memory"] is memory


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _boundary_completion(path: Path, contract: TaskDischargeContract, row: dict) -> dict:
    boundary = _outer_boundary(contract, row)
    core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_completed",
        "attempt_dir": str(path),
        "context_hash": contract.parameters["context_hash"],
        "boundary_result": boundary,
        "theory_task_discharge": {},
        "budget_stop_receipt": None,
        "provider_calls": 0,
    }
    completion = {**core, "completion_sha256": content_hash(core)}
    _write_json(path / "boundary_completion.json", completion)
    _write_json(path / "boundary_result.json", boundary)
    return completion


def _rejecting_verifier(**kwargs) -> dict:
    return {
        "outcome": "rejected",
        "observed": {
            "predicate": kwargs["predicate_ir"],
            "reason": "fixture_miss",
        },
        "evidence_refs": ["host-verifier:rejected"],
    }


def test_recovered_boundary_requires_equal_complete_execution_coordinate(
    tmp_path: Path,
) -> None:
    contract, _interface_row = _compiled_contract(context_hash="context:a")
    row = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=lambda **kwargs: kwargs["artifact"],
        verifier_fn=_rejecting_verifier,
    )
    coordinate = row["execution_coordinate"]
    assert set(coordinate) == {
        "schema",
        "context_hash",
        "adapter_id",
        "interface_sha256",
        "target_config_sha256",
        "artifact_sha256",
        "predicate_sha256",
        "witness_schema_sha256",
        "normalizer_sha256",
        "verifier_sha256",
        "coordinate_sha256",
    }
    _boundary_completion(tmp_path, contract, row)
    program = TheoryProgram(
        campaign_id="campaign:a",
        lineage_id="lineage:a",
        context_hash="context:a",
        context_epoch=0,
        presentation_formula_ids=("formula:a",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:a",
        task_discharge_contracts=(contract,),
        schema=THEORY_PROGRAM_V2,
    )
    navigation = {
        "context_hash": "context:a",
        "context_epoch": 0,
        "finalists": [{
            "theory_program_id": program.program_id,
            "theory_program": program.to_json(),
        }],
    }
    rebound = bind_recovered_boundary_artifact_feedback(tmp_path, navigation)
    feedback = rebound["finalists"][0]["objective_feedback"]
    assert feedback["execution_coordinate"] == coordinate
    assert feedback["route"] == "revise_construction"

    crossed_contract, _ = _compiled_contract(context_hash="context:b")
    crossed_program = TheoryProgram(
        campaign_id="campaign:a",
        lineage_id="lineage:a",
        context_hash="context:b",
        context_epoch=0,
        presentation_formula_ids=("formula:a",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:b",
        task_discharge_contracts=(crossed_contract,),
        schema=THEORY_PROGRAM_V2,
    )
    crossed = copy.deepcopy(navigation)
    crossed["finalists"][0]["theory_program_id"] = crossed_program.program_id
    crossed["finalists"][0]["theory_program"] = crossed_program.to_json()
    assert "objective_feedback" not in bind_recovered_boundary_artifact_feedback(
        tmp_path, crossed
    )["finalists"][0]

    legacy = copy.deepcopy(row)
    legacy.pop("execution_coordinate")
    legacy.pop("execution_coordinate_sha256")
    legacy_core = {
        key: value for key, value in legacy.items() if key != "receipt_sha256"
    }
    legacy["receipt_sha256"] = content_hash(legacy_core)
    _boundary_completion(tmp_path, contract, legacy)
    legacy_rebound = bind_recovered_boundary_artifact_feedback(tmp_path, navigation)
    assert "objective_feedback" not in legacy_rebound["finalists"][0]


@pytest.mark.parametrize(
    "navigation",
    (
        [
            {"schema": {"nested": ["not", "a", "tag"]}},
            {"schema": ["also", "not", "a", "tag"]},
        ],
        "navigation-scalar",
        17,
        {"objective_review_history": "history-scalar"},
        {"objective_review_history": 23},
        {
            "noise": [{"schema": "leanmill.witness_constructor_request.v2"}],
        },
        {
            "noise": [{
                "schema": "ztare-task-discharge-contract-v1",
                "contract_id": "task:shape-noise",
                "adjudicator_id": GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
                "lifecycle_scope": "campaign:shape-noise",
                "owner": "lineage:shape-noise",
                "parameters": {
                    "kind": "governed_witness_construction",
                    "candidate_envelope": {
                        "schema": {"nested": ["container", "shape"]},
                    },
                },
            }],
        },
    ),
)
def test_cold_recovery_scanner_ignores_container_protocol_tags_and_bad_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    navigation: object,
) -> None:
    candidate = SimpleNamespace(
        constructor_request={"request_sha256": "request:fixture"},
        execution_coordinate={"coordinate_sha256": "coordinate:fixture"},
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    run = {
        "status": "budget_stopped",
        "context_hash": "context:fixture",
        "navigation": navigation,
    }

    assert pending_cold_witness_boundary_recovery(tmp_path, run) is True


def test_witness_coordinate_recognizer_is_type_total_before_contract_parsing(
) -> None:
    contract, _ = _compiled_contract(context_hash="context:recognizer")
    legacy = contract.to_dict()
    legacy.pop("schema")
    assert witness_execution_coordinate_from_contract(legacy) is not None

    for schema in (
        {"nested": ["not", "a", "tag"]},
        ["not", "a", "tag"],
    ):
        malformed = contract.to_dict()
        malformed["schema"] = schema
        assert witness_execution_coordinate_from_contract(malformed) is None

    fake_envelope = contract.to_dict()
    fake_envelope["parameters"] = {
        "kind": "governed_witness_construction",
        "candidate_envelope": {
            "schema": {"nested": ["container", "shape"]},
        },
    }
    assert witness_execution_coordinate_from_contract(fake_envelope) is None

    crossed_wrapper = contract.to_dict()
    crossed_wrapper["parameters"] = dict(crossed_wrapper["parameters"])
    crossed_wrapper["parameters"]["request_id"] = "request:other"
    assert witness_execution_coordinate_from_contract(crossed_wrapper) is None


def test_cold_recovery_reads_control_refs_only_from_validated_owner_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_contract, _ = _compiled_contract(
        context_hash="context:owner-path",
        formula_id="formula:a",
    )
    second_contract, _ = _compiled_contract(
        context_hash="context:owner-path",
        formula_id="formula:b",
        artifact_value=3,
    )
    first = WitnessConstructionCandidateEnvelope.from_json(
        first_contract.parameters["candidate_envelope"]
    )
    second = WitnessConstructionCandidateEnvelope.from_json(
        second_contract.parameters["candidate_envelope"]
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (first, second),
    )
    source = {
        "status": "budget_stopped",
        "context_hash": "context:owner-path",
        "navigation": {
            "artifact": {
                "embedded_valid_request": first.constructor_request,
            },
            "witness_schema": {
                "const": second.constructor_request,
            },
        },
    }
    assert reviewed_campaign_module._pending_cold_witness_candidates(
        tmp_path, source
    ) == (first, second)

    task_request_core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": "context:owner-path",
        "context_epoch": 0,
        "presentation_formula_ids": ["formula:a"],
        "goal": "Construct the first candidate.",
        "observable": "The frozen predicate accepts it.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": ["selection:receipt"],
        "kill_condition": "Reject after exact replay failure.",
        "authority": "leaf_request_host_bound",
        "witness_construction": {
            "constructor_request": first.constructor_request,
            "artifact": {
                "embedded_valid_request": second.constructor_request,
            },
        },
    }
    task_request = {
        **task_request_core,
        "request_id": "theory-task-request:" + content_hash(task_request_core),
    }
    receipt_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "propose_theory_task",
        "context_hash": "context:owner-path",
        "input_hashes": {},
        "output_summary": {
            "status": "compiled_theory_task",
            "task_request": task_request,
        },
        "claim_bindings": ["propose_theory_task"],
        "authority": "deterministic_host",
    }
    receipt = {
        **receipt_core,
        "receipt_id": "sha256:" + content_hash(receipt_core),
    }
    source["navigation"] = {"trace": [{"receipt": receipt}]}
    assert reviewed_campaign_module._pending_cold_witness_candidates(
        tmp_path, source
    ) == (first,)

    compatibility_core = copy.deepcopy(receipt_core)
    compatibility_core["output_summary"]["status"] = (
        "adapter_capability_unavailable"
    )
    compatibility_receipt = {
        **compatibility_core,
        "receipt_id": "sha256:" + content_hash(compatibility_core),
    }
    source["navigation"] = {
        "trace": [{"receipt": compatibility_receipt}],
    }
    assert reviewed_campaign_module._pending_cold_witness_candidates(
        tmp_path, source
    ) == (first,)

    near_shape = copy.deepcopy(receipt)
    near_shape["unexpected"] = "rehashed-near-shape"
    near_shape_core = {
        key: value for key, value in near_shape.items() if key != "receipt_id"
    }
    near_shape["receipt_id"] = "sha256:" + content_hash(near_shape_core)
    source["navigation"] = {"trace": [{"receipt": near_shape}]}
    with pytest.raises(ValueError, match="receipt fields changed identity"):
        reviewed_campaign_module._pending_cold_witness_candidates(
            tmp_path, source
        )


@pytest.mark.parametrize(
    "owner_slot",
    (
        "finalists",
        "objective_survivors",
        "deferred_finalists",
        "lineage_finalists",
    ),
)
def test_cold_recovery_program_refs_cover_canonical_candidate_owner_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    owner_slot: str,
) -> None:
    first_contract, _ = _compiled_contract(
        context_hash="context:program-owner",
        formula_id="formula:a",
        artifact_value=2,
    )
    second_contract, _ = _compiled_contract(
        context_hash="context:program-owner",
        formula_id="formula:b",
        artifact_value=3,
    )
    first = WitnessConstructionCandidateEnvelope.from_json(
        first_contract.parameters["candidate_envelope"]
    )
    second = WitnessConstructionCandidateEnvelope.from_json(
        second_contract.parameters["candidate_envelope"]
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (first, second),
    )
    program = TheoryProgram(
        campaign_id="campaign:program-owner",
        lineage_id="lineage:program-owner",
        context_hash="context:program-owner",
        context_epoch=0,
        presentation_formula_ids=("formula:a",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:program-owner",
        task_discharge_contracts=(first_contract,),
        schema=THEORY_PROGRAM_V2,
    )
    row = {
        "theory_program_id": program.program_id,
        "theory_program": program.to_json(),
    }
    navigation = (
        {"lineages": [{"navigation": {"finalists": [row]}}]}
        if owner_slot == "lineage_finalists"
        else {owner_slot: [row]}
    )
    assert reviewed_campaign_module._pending_cold_witness_candidates(
        tmp_path,
        {
            "status": "budget_stopped",
            "context_hash": "context:program-owner",
            "navigation": navigation,
        },
    ) == (first,)


def test_cold_recovery_control_scan_has_a_deterministic_node_ceiling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract, _ = _compiled_contract(context_hash="context:bounded")
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_MAX_RECOVERY_CONTROL_NODES",
        2,
    )
    with pytest.raises(ValueError, match="control-node ceiling exhausted"):
        reviewed_campaign_module._pending_cold_witness_candidates(
            tmp_path,
            {
                "status": "budget_stopped",
                "context_hash": "context:bounded",
                "navigation": {"trace": [{}, {}]},
            },
        )


@pytest.mark.parametrize(
    "navigation",
    (
        ["malformed-navigation"],
        {"objective_review_history": "malformed-history"},
    ),
)
def test_router_rejects_malformed_control_without_durable_cold_candidate(
    tmp_path: Path,
    navigation: object,
) -> None:
    core = {
        "status": "budget_stopped",
        "context_hash": "context:no-candidate",
        "navigation": navigation,
    }
    _write_json(tmp_path / "run.json", {**core, "run_digest": content_hash(core)})
    with pytest.raises(ValueError, match="navigation control fields are malformed"):
        next_frontier_campaign_action(tmp_path)


def test_router_prioritizes_authenticated_cold_recovery_over_malformed_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = SimpleNamespace(
        constructor_request={"request_sha256": "request:fixture"},
        execution_coordinate={"coordinate_sha256": "coordinate:fixture"},
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    core = {
        "status": "budget_stopped",
        "context_hash": "context:durable-candidate",
        "navigation": ["malformed-navigation"],
    }
    _write_json(tmp_path / "run.json", {**core, "run_digest": content_hash(core)})
    assert next_frontier_campaign_action(tmp_path) == (
        "recover_construction_boundary"
    )


def test_failed_cold_recovery_restores_provider_free_source_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = budget_preset("smoke_20m")
    _write_json(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:expansion:provider_calls",
        context_hash="context:recovery-transaction",
    ).to_json()
    _write_json(tmp_path / "budget_stop_receipt.json", stop)
    source_core = {
        "status": "budget_stopped",
        "context_hash": "context:recovery-transaction",
        "budget_digest": budget.digest,
        "provider_calls": 0,
        "budget_stop_receipt": stop,
        "navigation": {
            "context_hash": "context:recovery-transaction",
            "context_epoch": 0,
        },
    }
    source_run = {
        **source_core,
        "run_digest": content_hash(source_core),
    }
    _write_json(tmp_path / "run.json", source_run)
    candidate = SimpleNamespace(
        execution_coordinate={"coordinate_sha256": "coordinate:durable"}
    )

    def source_recovery_pending(_directory: Path, run: object) -> bool:
        return isinstance(run, dict) and run.get("run_digest") == source_run[
            "run_digest"
        ]

    monkeypatch.setattr(
        reviewed_campaign_module,
        "pending_cold_witness_boundary_recovery",
        source_recovery_pending,
    )
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.pending_cold_witness_boundary_recovery",
        source_recovery_pending,
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_pending_cold_witness_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_role_output_inventory",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_completed_witness_coordinate_statuses",
        lambda *_args, **_kwargs: {},
    )
    immutable_receipt = {
        "schema": "fixture.immutable_boundary_receipt.v1",
        "receipt_sha256": "receipt:preserved",
    }

    def materialize_invalid_projection(path: Path, reason: str) -> None:
        assert reason == "blocked_before_action:expansion:provider_calls"
        _write_json(path / "boundary_receipt.fixture.json", immutable_receipt)
        partial_core = {
            "status": "budget_stopped",
            "context_hash": "context:recovery-transaction",
            "budget_digest": budget.digest,
            "provider_calls": 0,
            "budget_stop_receipt": stop,
            "navigation": {
                "context_hash": "context:recovery-transaction",
                "context_epoch": 0,
                "finalists": [],
            },
        }
        _write_json(
            path / "run.json",
            {**partial_core, "run_digest": content_hash(partial_core)},
        )

    with pytest.raises(
        ValueError,
        match="durable constructor coordinates were lost during materialization",
    ):
        recover_cold_witness_boundary(
            tmp_path,
            materialize_fn=materialize_invalid_projection,
            verify_fn=lambda _path: pytest.fail("coordinate check must fail first"),
        )

    assert json.loads((tmp_path / "run.json").read_text()) == source_run
    assert json.loads(
        (tmp_path / "boundary_receipt.fixture.json").read_text()
    ) == immutable_receipt
    assert next_frontier_campaign_action(tmp_path) == (
        "recover_construction_boundary"
    )


def test_cold_recovery_rejects_crossed_and_stale_source_budget_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = budget_preset("smoke_20m")
    _write_json(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stale = ledger.stop_receipt(
        "blocked_before_action:expansion:provider_calls",
        context_hash="context:stale-stop",
    ).to_json()
    ledger.freeze_wall_clock(reason="fixture_between_budget_stops")
    current = ledger.stop_receipt(
        "blocked_before_action:boundary:provider_calls",
        context_hash="context:stale-stop",
    ).to_json()
    assert current["receipt_sha256"] != stale["receipt_sha256"]
    _write_json(tmp_path / "budget_stop_receipt.json", current)
    source_core = {
        "status": "budget_stopped",
        "context_hash": "context:stale-stop",
        "budget_digest": budget.digest,
        "provider_calls": 0,
        "budget_stop_receipt": stale,
        "navigation": {
            "context_hash": "context:stale-stop",
            "context_epoch": 0,
        },
    }
    source_run = {**source_core, "run_digest": content_hash(source_core)}
    _write_json(tmp_path / "run.json", source_run)
    candidate = SimpleNamespace(
        execution_coordinate={"coordinate_sha256": "coordinate:stale-stop"}
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "pending_cold_witness_boundary_recovery",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_pending_cold_witness_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_role_output_inventory",
        lambda *_args, **_kwargs: (),
    )
    materialized: list[bool] = []

    with pytest.raises(
        ValueError,
        match="cold witness recovery lost its source budget stop",
    ):
        recover_cold_witness_boundary(
            tmp_path,
            materialize_fn=lambda *_args: materialized.append(True),
            verify_fn=lambda _path: pytest.fail("crossed stop reached verification"),
        )

    _write_json(tmp_path / "budget_stop_receipt.json", stale)
    with pytest.raises(
        ValueError,
        match="cold witness recovery budget stop changed identity",
    ):
        recover_cold_witness_boundary(
            tmp_path,
            materialize_fn=lambda *_args: materialized.append(True),
            verify_fn=lambda _path: pytest.fail("stale stop reached verification"),
        )

    assert materialized == []


def _write_recovery_activation_authority_fixture(
    directory: Path,
) -> dict[str, Path]:
    context_hash = "context:bounded-recovery-authority"
    contract, _ = _compiled_contract(context_hash=context_hash)
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    program = TheoryProgram(
        campaign_id="campaign:bounded-recovery-authority",
        lineage_id="lineage:bounded-recovery-authority",
        context_hash=context_hash,
        context_epoch=0,
        presentation_formula_ids=("formula:target",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:bounded-recovery-authority",
        task_discharge_contracts=(contract,),
        schema=THEORY_PROGRAM_V2,
    )
    budget = budget_preset("smoke_20m")
    _write_json(directory / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:expansion:provider_calls",
        context_hash=context_hash,
    ).to_json()
    source_core = {
        "status": "budget_stopped",
        "context_hash": context_hash,
        "budget_digest": budget.digest,
        "provider_calls": 0,
        "budget_stop_receipt": stop,
        "navigation": {"context_hash": context_hash, "context_epoch": 0},
    }
    source = {**source_core, "run_digest": content_hash(source_core)}
    source_path = directory / (
        "construction_recovery_source_run."
        f"{source['run_digest'][:16]}.json"
    )
    source_stop_path = directory / (
        "construction_recovery_source_budget_stop."
        f"{stop['receipt_sha256'][:16]}.json"
    )
    _write_json(source_path, source)
    _write_json(source_stop_path, stop)
    navigation = {
        "context_hash": context_hash,
        "context_epoch": 0,
        "finalists": [
            {
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ],
    }
    rebuilt_core = {
        **source_core,
        "navigation": navigation,
    }
    rebuilt = {**rebuilt_core, "run_digest": content_hash(rebuilt_core)}
    activation_core = {
        "schema": "leanmill.construction_boundary_recovery_activation.v1",
        "source_run_sha256": source["run_digest"],
        "rebuilt_run_sha256": rebuilt["run_digest"],
        "source_budget_stop_receipt_sha256": stop["receipt_sha256"],
        "latest_budget_stop_receipt_sha256": stop["receipt_sha256"],
        "execution_coordinate_sha256s": [
            candidate.execution_coordinate["coordinate_sha256"]
        ],
        "executor_kind": "data_only_witness_construction",
        "authority": "reviewed_construction_campaign_transition",
    }
    activation = {
        **activation_core,
        "receipt_sha256": content_hash(activation_core),
    }
    activation_path = directory / (
        "construction_boundary_recovery_activation."
        f"{activation['receipt_sha256'][:16]}.json"
    )
    _write_json(activation_path, activation)
    active_navigation = {
        **navigation,
        "construction_boundary_recovery_activation": activation,
    }
    active_core = {**rebuilt_core, "navigation": active_navigation}
    _write_json(
        directory / "run.json",
        {**active_core, "run_digest": content_hash(active_core)},
    )
    return {
        "activation": activation_path,
        "source_run": source_path,
        "source_stop": source_stop_path,
    }


@pytest.mark.parametrize(
    "slot_name,context",
    (
        ("activation", "construction boundary recovery activation"),
        ("source_run", "construction recovery source run"),
        ("source_stop", "construction recovery source budget stop"),
    ),
)
@pytest.mark.parametrize("failure_mode", ("symlink", "oversized"))
def test_recovery_activation_authority_slots_are_bounded_and_link_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    slot_name: str,
    context: str,
    failure_mode: str,
) -> None:
    paths = _write_recovery_activation_authority_fixture(tmp_path)
    target = paths[slot_name]
    if failure_mode == "symlink":
        backing = target.with_suffix(".backing.json")
        target.replace(backing)
        target.symlink_to(backing)
        expected = context + " authority slot is unavailable"
    else:
        other_sizes = [
            path.stat().st_size
            for name, path in paths.items()
            if name != slot_name
        ]
        ceiling = max(other_sizes) + 32
        monkeypatch.setattr(
            explore_axiom_space_module,
            "_MAX_CONSTRUCTION_RECOVERY_AUTHORITY_SLOT_BYTES",
            ceiling,
        )
        target.write_text(
            json.dumps({"padding": "x" * (ceiling + 1)}),
            encoding="utf-8",
        )
        expected = context + " authority slot exceeds its byte ceiling"
    run = json.loads((tmp_path / "run.json").read_text())
    with pytest.raises(ValueError, match=expected):
        explore_axiom_space_module._validated_construction_boundary_recovery_activation(
            tmp_path,
            run,
            lean_executor_fn=None,
            isabelle_executor_fn=None,
            raw_boundary_fn=None,
            countermodel_fn=None,
            single_premise_audit_fn=None,
            theory_task_executor_fn=lambda *_args, **_kwargs: {},
        )


def test_recovery_rejects_provider_usage_carried_by_crash_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_recovery_activation_authority_fixture(tmp_path)
    source = json.loads(paths["source_run"].read_text())
    source_stop = BudgetStopReceipt.from_json(
        source["budget_stop_receipt"]
    )
    budget = ExplorationBudget.from_json(
        json.loads((tmp_path / "budget.json").read_text())
    )
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    reservation = ledger.reserve(
        "fixture:forbidden-provider-call",
        "expansion",
        {"provider_calls": 1},
    )
    ledger.commit(reservation, {"provider_calls": 1})
    ledger.stop_receipt(
        source_stop.reason,
        context_hash=source_stop.context_hash,
    )
    reviewed_campaign_module._restore_recovery_read_model_after_failure(
        tmp_path,
        source_run=source,
        source_stop=source_stop,
        ledger=ledger,
        budget=budget,
        recovery_activation=None,
    )
    candidate = SimpleNamespace(
        execution_coordinate={"coordinate_sha256": "coordinate:provider-violation"}
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "pending_cold_witness_boundary_recovery",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_pending_cold_witness_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_role_output_inventory",
        lambda *_args, **_kwargs: (),
    )
    with pytest.raises(
        ValueError, match="rollback consumed provider calls"
    ):
        recover_cold_witness_boundary(
            tmp_path,
            materialize_fn=lambda *_args: pytest.fail(
                "provider-tainted retry reached materialization"
            ),
            verify_fn=lambda _path: pytest.fail(
                "provider-tainted retry reached verification"
            ),
        )


@pytest.mark.parametrize("crash_once", (False, True), ids=("direct", "crash_retry"))
def test_budget_stopped_cold_recovery_finishes_finalist_without_synthesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_once: bool,
) -> None:
    from test_theory_navigator import _context_and_blueprint
    from ztare.leanmill.finite_theory_context import save_formal_theory_context
    from ztare.leanmill.formal_verification_provider import generate_keypair
    from ztare.leanmill.frontier_campaign import sign_frontier_campaign
    from ztare.leanmill.frontier_campaign_runner import (
        execute_frontier_campaign_verification,
        packet_for_frontier_context,
    )
    import ztare.leanmill.theory_adapter_registry as adapter_registry

    context, source_blueprint = _context_and_blueprint()
    blueprint = replace(
        source_blueprint,
        adapter_id="test_adapter.v1",
        adapter_config={},
        stop_rule={
            **source_blueprint.stop_rule,
            "user_instruction": "Require a late objective review.",
            "executable_condition": {"kind": "late_lineage_objective_review"},
        },
    )
    contract, _interface_row = _compiled_contract(
        context_hash=context.context_hash,
        formula_id=context.formula_ids[0],
    )
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    program = TheoryProgram(
        campaign_id="campaign:cold-budget-stop",
        lineage_id="lineage:cold-budget-stop",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=(context.formula_ids[0],),
        prediction_formula_ids=(),
        selection_receipt_id="selection:cold-budget-stop",
        task_discharge_contracts=(contract,),
        schema=THEORY_PROGRAM_V2,
    )
    budget = budget_preset("smoke_20m")
    definition = FrontierCampaignDefinition(
        direction="Recover one rejected construction provider-free.",
        source_mode="structure_first",
        budget=budget,
    )
    (tmp_path / "campaign_definition.yaml").write_text(
        definition.to_yaml(), encoding="utf-8"
    )
    _write_json(tmp_path / "blueprint.json", blueprint.to_json())
    _write_json(tmp_path / "budget.json", budget.to_json())
    save_formal_theory_context(context, tmp_path / "formal_context.json")
    private_key, public_key = generate_keypair()
    campaign = sign_frontier_campaign(
        packet_for_frontier_context(
            blueprint,
            context,
            campaign_id="campaign:cold-budget-stop",
        ),
        private_key_pem=private_key,
        signer_ref="test-authority",
    ).to_json()
    _write_json(tmp_path / "campaign.json", campaign)
    (tmp_path / "campaign_signer_public.pem").write_text(
        public_key, encoding="utf-8"
    )
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    reason = "blocked_before_action:expansion:provider_calls"
    stop = ledger.stop_receipt(
        reason,
        context_hash=context.context_hash,
    ).to_json()
    _write_json(tmp_path / "budget_stop_receipt.json", stop)
    source_core = {
        "status": "budget_stopped",
        "context_hash": context.context_hash,
        "budget_digest": budget.digest,
        "provider_calls": 0,
        "budget_stop_receipt": stop,
        "navigation": {
            "context_hash": context.context_hash,
            "context_epoch": 0,
        },
    }
    source_run = {
        **source_core,
        "run_digest": content_hash(source_core),
    }
    _write_json(tmp_path / "run.json", source_run)
    monkeypatch.setattr(
        reviewed_campaign_module,
        "pending_cold_witness_boundary_recovery",
        lambda _directory, run: run.get("status") == "budget_stopped",
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_pending_cold_witness_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_role_output_inventory",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(
        adapter_registry,
        "theory_adapter_capabilities",
        lambda adapter_id: (
            "normalize_explicit_candidate",
            "verify_frozen_predicate",
        )
        if adapter_id == "test_adapter.v1"
        else (),
    )

    def materialize_capability(
        adapter_id: str,
        capability_id: str,
        **kwargs,
    ) -> dict:
        assert adapter_id == "test_adapter.v1"
        if capability_id == "normalize_explicit_candidate":
            return dict(kwargs["artifact"])
        assert capability_id == "verify_frozen_predicate"
        return {
            "outcome": "rejected",
            "observed": {"reason": "fixture_miss"},
            "evidence_refs": ["host-verifier:rejected"],
        }

    monkeypatch.setattr(
        adapter_registry,
        "materialize_theory_adapter_capability",
        materialize_capability,
    )

    materialized_reasons: list[str] = []

    def materialize(path: Path, recovered_reason: str) -> None:
        materialized_reasons.append(recovered_reason)
        recovered_stop = ledger.stop_receipt(
            recovered_reason,
            context_hash=context.context_hash,
        ).to_json()
        finish_frontier_navigation(
            path,
            brief_id=blueprint.brief_digest,
            blueprint=blueprint,
            context=context,
            context_epoch=0,
            campaign_id="campaign:cold-budget-stop",
            packet_digest=str(campaign["packet_digest"]),
            navigation={
                "context_hash": context.context_hash,
                "context_epoch": 0,
                "finalists": [{
                    "candidate_kind": "theory_program",
                    "context_hash": context.context_hash,
                    "context_epoch": 0,
                    "formula_ids": [context.formula_ids[0]],
                    "boundary_target_ids": [],
                    "residual_prediction_formula_ids": [],
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }],
            },
            provider_calls=0,
            preparation_provider_calls=0,
            budget_digest=budget.digest,
            formula_proposal_count=0,
            semantically_new_formula_count=0,
            labeled_object_count=len(context.object_ids),
            budget_stop_receipt=recovered_stop,
        )

    crashed_activation_sha256 = ""

    def verify(path: Path) -> dict:
        nonlocal crashed_activation_sha256
        completion = execute_frontier_campaign_verification(
            path,
            with_lean=False,
            with_isabelle=False,
            resume_search=False,
        )
        if crash_once and not crashed_activation_sha256:
            active = json.loads((path / "run.json").read_text())[
                "navigation"
            ]["construction_boundary_recovery_activation"]
            crashed_activation_sha256 = active["receipt_sha256"]
            raise RuntimeError("fixture crash after boundary stop append")
        return completion

    if crash_once:
        with pytest.raises(
            RuntimeError, match="fixture crash after boundary stop append"
        ):
            recover_cold_witness_boundary(
                tmp_path,
                materialize_fn=materialize,
                verify_fn=verify,
            )
        rollback = json.loads((tmp_path / "run.json").read_text())
        latest_after_crash = ledger.latest_stop_receipt()
        assert latest_after_crash is not None
        assert rollback["budget_stop_receipt"] == latest_after_crash.to_json()
        assert rollback["provider_calls"] == latest_after_crash.usage[
            "provider_calls"
        ]
        assert json.loads(
            (tmp_path / "budget_stop_receipt.json").read_text()
        ) == latest_after_crash.to_json()
        reconciliation = rollback["navigation"][
            "construction_recovery_rollback_reconciliation"
        ]
        assert reconciliation["source_run_sha256"] == source_run["run_digest"]
        assert reconciliation[
            "source_budget_stop_receipt_sha256"
        ] == stop["receipt_sha256"]
        assert reconciliation[
            "latest_budget_stop_receipt_sha256"
        ] == latest_after_crash.to_json()["receipt_sha256"]
        assert reconciliation[
            "orphaned_activation_receipt_sha256s"
        ] == [crashed_activation_sha256]

    transition = recover_cold_witness_boundary(
        tmp_path,
        materialize_fn=materialize,
        verify_fn=verify,
    )

    recovered = json.loads((tmp_path / "run.json").read_text())
    latest = ledger.latest_stop_receipt()
    assert latest is not None
    assert transition["provider_calls_before"] == 0
    assert transition["provider_calls_after"] == 0
    assert recovered["status"] == "budget_stopped"
    assert recovered["budget_stop_receipt"] == latest.to_json()
    assert json.loads(
        (tmp_path / "budget_stop_receipt.json").read_text()
    ) == latest.to_json()
    assert recovered["navigation"]["finalists"][0][
        "theory_program_id"
    ] == program.program_id
    assert "lineage_synthesis" not in recovered["navigation"]
    assert "construction_boundary_recovery_activation" not in recovered[
        "navigation"
    ]
    consumed = recovered["navigation"][
        "construction_boundary_recovery_activation_consumed"
    ]
    assert consumed["schema"] == (
        "leanmill.construction_boundary_recovery_activation_consumed.v1"
    )
    if crash_once:
        assert materialized_reasons == [reason, "campaign_finished"]
        assert consumed["active_activation_receipt_sha256"] == ""
        assert consumed[
            "orphaned_activation_receipt_sha256s"
        ] == [crashed_activation_sha256]
        assert crashed_activation_sha256 in consumed[
            "audited_activation_receipt_sha256s"
        ]
    else:
        assert materialized_reasons == [reason]
        assert consumed["active_activation_receipt_sha256"]
        assert consumed["orphaned_activation_receipt_sha256s"] == []
    completion = json.loads(
        (tmp_path / "boundary_completion.json").read_text()
    )
    assert consumed["boundary_completion_sha256"] == completion[
        "completion_sha256"
    ]
    query_results = completion["boundary_result"]["query_results"]
    assert len(query_results) == 1
    assert query_results[0]["candidate_kind"] == "theory_task"
    assert "target_formula_id" not in query_results[0]


def test_invalid_json_schema_is_normalized_at_witness_artifact_boundary() -> None:
    contract, _ = _compiled_contract(context_hash="context:schema-error")
    candidate = copy.deepcopy(contract.parameters["candidate_envelope"])
    candidate["witness_schema"] = {"type": 7}
    candidate["witness_schema_sha256"] = content_hash(
        candidate["witness_schema"]
    )
    candidate_core = {
        key: value for key, value in candidate.items() if key != "receipt_sha256"
    }
    candidate["receipt_sha256"] = content_hash(candidate_core)
    with pytest.raises(
        ValueError,
        match="witness artifact does not satisfy its frozen schema",
    ):
        WitnessConstructionCandidateEnvelope.from_json(candidate)


def test_rehashed_invalid_interface_schema_is_normalized_in_control_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract, _ = _compiled_contract(context_hash="context:invalid-interface")
    candidate = WitnessConstructionCandidateEnvelope.from_json(
        contract.parameters["candidate_envelope"]
    )
    malformed_request = copy.deepcopy(candidate.constructor_request)
    malformed_interface = malformed_request["construction_interface"]
    malformed_interface["witness_schema"] = {"type": 7}
    interface_core = {
        key: value
        for key, value in malformed_interface.items()
        if key != "interface_sha256"
    }
    malformed_interface["interface_sha256"] = content_hash(interface_core)
    malformed_request["interface_sha256"] = malformed_interface[
        "interface_sha256"
    ]
    request_core = {
        key: value
        for key, value in malformed_request.items()
        if key != "request_sha256"
    }
    malformed_request["request_sha256"] = content_hash(request_core)
    with pytest.raises(
        ValueError,
        match="construction interface witness schema is invalid",
    ):
        validate_witness_constructor_request(malformed_request)

    task_core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": "context:invalid-interface",
        "context_epoch": 0,
        "presentation_formula_ids": ["formula:a"],
        "goal": "Construct one candidate.",
        "observable": "The predicate accepts it.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": ["selection:receipt"],
        "kill_condition": "Reject after exact replay failure.",
        "authority": "leaf_request_host_bound",
        "witness_construction": {
            "constructor_request": malformed_request,
        },
    }
    task_request = {
        **task_core,
        "request_id": "theory-task-request:" + content_hash(task_core),
    }
    receipt_core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": "propose_theory_task",
        "context_hash": "context:invalid-interface",
        "input_hashes": {},
        "output_summary": {
            "status": "compiled_theory_task",
            "task_request": task_request,
        },
        "claim_bindings": ["propose_theory_task"],
        "authority": "deterministic_host",
    }
    receipt = {
        **receipt_core,
        "receipt_id": "sha256:" + content_hash(receipt_core),
    }
    monkeypatch.setattr(
        reviewed_campaign_module,
        "_durable_current_constructor_candidates",
        lambda *_args, **_kwargs: (candidate,),
    )
    with pytest.raises(ValueError, match="constructor request is malformed"):
        reviewed_campaign_module._pending_cold_witness_candidates(
            tmp_path,
            {
                "status": "budget_stopped",
                "context_hash": "context:invalid-interface",
                "navigation": {"trace": [{"receipt": receipt}]},
            },
        )


def test_cold_budget_stop_replays_durable_constructor_before_terminal_handling(
    tmp_path: Path,
) -> None:
    interface = _interface(policy="verifier_acceptance_is_terminal")
    request = build_witness_constructor_request(
        context_hash="context:cold",
        adapter_id="test_adapter.v1",
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": ["formula:a"],
            "goal": "Construct one explicit witness.",
            "observable": "The predicate accepts.",
            "evidence_refs": ["selection:receipt"],
            "kill_condition": "Reject on exact replay failure.",
            "construction_brief": "Search one canonical coordinate.",
        },
    )
    prompt = prompts.AXIOMPACK_WITNESS_CONSTRUCTOR_PROMPT.format(
        construction_request_json=json.dumps(
            request, sort_keys=True, separators=(",", ":")
        )
    )
    raw = {"artifact": {"value": 1}, "orientation": _orientation()}
    result_text = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    budget = budget_preset("smoke_20m")
    definition = FrontierCampaignDefinition(
        direction="Recover one completed witness construction.",
        source_mode="structure_first",
        budget=budget,
    )
    (tmp_path / "campaign_definition.yaml").write_text(
        definition.to_yaml(), encoding="utf-8"
    )
    call = {
        "schema": "leanmill.frontier_subscription_role_call.v1",
        "role": "witness_constructor",
        "agent_id": "axiompack-witness_constructor-lineage-000.wave-003",
        "runtime": "codex",
        "model": "gpt-5.4-mini",
        "prompt_digest": content_hash({"prompt": prompt}),
        "returncode": 0,
        "provider_call_charge": 1,
        "wallclock_s": 1.0,
        "stdout_digest": content_hash({"stdout": result_text}),
        "stderr_digest": content_hash({"stderr": ""}),
        "result_digest": content_hash({"result": result_text}),
        "output_schema_digest": "",
    }
    call_dir = (
        tmp_path
        / "agent_calls"
        / "witness_constructor.lineage-000.wave-003"
    )
    call_dir.mkdir(parents=True)
    _write_json(call_dir / "000.call.json", call)
    (call_dir / "000.prompt.txt").write_text(prompt, encoding="utf-8")
    (call_dir / "000.result.json").write_text(result_text, encoding="utf-8")
    (call_dir / "000.stdout.txt").write_text(result_text, encoding="utf-8")
    navigator_dir = (
        tmp_path / "agent_calls" / "navigator.lineage-000.wave-003"
    )
    navigator_dir.mkdir(parents=True)
    navigator_prompt = "durable navigator request"
    navigator_decision = {
        "decision": "request",
        "rationale": "Author the explicit frozen witness.",
        "capability_id": "propose_theory_task",
        "input_refs": {
            "formula_ids": ["formula:a"],
            "goal": "Construct one explicit witness.",
            "observable": "The predicate accepts.",
            "adjudicator_capability": "governed_witness_construction",
            "evidence_refs": ["selection:receipt"],
            "kill_condition": "Reject on exact replay failure.",
        },
        "formula_ids": None,
        "boundary_target_ids": None,
        "task_contract_ids": None,
    }
    navigator_result = json.dumps(
        navigator_decision, sort_keys=True, separators=(",", ":")
    )
    navigator_call = {
        **call,
        "role": "navigator",
        "agent_id": "axiompack-navigator-lineage-000.wave-003",
        "prompt_digest": content_hash({"prompt": navigator_prompt}),
        "stdout_digest": content_hash({"stdout": navigator_result}),
        "result_digest": content_hash({"result": navigator_result}),
        "output_schema_digest": content_hash(navigator_decision_output_schema()),
    }
    _write_json(navigator_dir / "000.call.json", navigator_call)
    (navigator_dir / "000.prompt.txt").write_text(
        navigator_prompt, encoding="utf-8"
    )
    (navigator_dir / "000.result.json").write_text(
        navigator_result, encoding="utf-8"
    )
    (navigator_dir / "000.stdout.txt").write_text(
        navigator_result, encoding="utf-8"
    )
    _write_json(
        navigator_dir / "000.schema.json", navigator_decision_output_schema()
    )

    _write_json(tmp_path / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl", budget, attempt_id=tmp_path.name
    )
    for phase in ("compilation", "navigation", "expansion", "boundary"):
        reservation = ledger.reserve(
            f"fixture:{phase}",
            phase,
            {"provider_calls": 2, "agent_turns": 2},
        )
        ledger.commit(reservation)
    stop = ledger.stop_receipt(
        "blocked_before_action:expansion:provider_calls",
        context_hash="context:cold",
    ).to_json()
    _write_json(tmp_path / "budget_stop_receipt.json", stop)
    ledger.freeze_wall_clock(reason="fixture_stale_budget_stop")
    source_core = {
        "status": "budget_stopped",
        "context_hash": "context:cold",
        "budget_digest": budget.digest,
        "provider_calls": 8,
        "budget_stop_receipt": stop,
        "navigation": {"context_hash": "context:cold", "context_epoch": 0},
    }
    _write_json(
        tmp_path / "run.json",
        {**source_core, "run_digest": content_hash(source_core)},
    )
    assert pending_cold_witness_boundary_recovery(
        tmp_path, json.loads((tmp_path / "run.json").read_text())
    )
    assert next_frontier_campaign_action(tmp_path) == (
        "recover_construction_boundary"
    )
    candidate = durable_witness_construction_candidates(tmp_path)[0]
    task_specification = {
        "goal": "Construct one explicit witness.",
        "observable": "The predicate accepts.",
        "kill_condition": "Reject on exact replay failure.",
    }
    contract = TaskDischargeContract(
        contract_id="task:cold-wave-3",
        adjudicator_id=GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        lifecycle_scope="campaign:cold",
        owner="lineage:cold",
        parameters={
            "kind": "governed_witness_construction",
            "request_id": candidate.request_id,
            "context_hash": candidate.context_hash,
            "context_epoch": 0,
            "presentation_formula_ids": ["formula:a"],
            "task_specification": task_specification,
            "task_specification_sha256": content_hash(task_specification),
            "input_evidence_refs": ["selection:receipt"],
            "candidate_envelope": candidate.to_json(),
            "candidate_envelope_sha256": candidate.receipt_sha256,
            "claim_scope": WITNESS_CONSTRUCTION_CLAIM_SCOPE,
        },
    )
    program = TheoryProgram(
        campaign_id="campaign:cold",
        lineage_id="lineage:cold",
        context_hash="context:cold",
        context_epoch=0,
        presentation_formula_ids=("formula:a",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:cold",
        task_discharge_contracts=(contract,),
        schema=THEORY_PROGRAM_V2,
    )

    def materialize(path: Path, reason: str) -> None:
        assert reason == "blocked_before_action:expansion:provider_calls"
        core = {
            "status": "budget_stopped",
            "context_hash": "context:cold",
            "budget_digest": budget.digest,
            "provider_calls": 8,
            "budget_stop_receipt": stop,
            "navigation": {
                "context_hash": "context:cold",
                "context_epoch": 0,
                "finalists": [{
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }],
            },
        }
        _write_json(path / "run.json", {**core, "run_digest": content_hash(core)})

    def verify(path: Path) -> dict:
        row = execute_governed_witness_construction_task(
            contract,
            normalizer_fn=lambda **kwargs: kwargs["artifact"],
            verifier_fn=_rejecting_verifier,
        )
        return _boundary_completion(path, contract, row)

    before_files = sorted(path.name for path in call_dir.iterdir())
    transition = recover_cold_witness_boundary(
        tmp_path, materialize_fn=materialize, verify_fn=verify
    )
    after_files = sorted(path.name for path in call_dir.iterdir())
    assert before_files == after_files
    assert transition["provider_calls_before"] == 8
    assert transition["provider_calls_after"] == 8
    assert transition["navigator_constructor_outputs_unchanged"] is True
    assert transition["frozen_budget_state_sha256"]
    recovered = json.loads((tmp_path / "run.json").read_text())
    assert recovered["status"] == "budget_stopped"
    feedback = recovered["navigation"]["objective_review_history"][-1]
    assert feedback["schema"] == RECOVERED_BOUNDARY_FEEDBACK_SCHEMA
    assert feedback["route"] == "revise_construction"
