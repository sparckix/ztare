"""Content-bound terminal credit for one reviewed finite-family witness.

The family executor, formal ratifier, language synthesizer, and campaign
blueprint each own a different decision.  This module joins their immutable
outputs without allowing the terminal transition to reconstruct or weaken any
of them.  The resulting receipt carries everything needed for deterministic
replay after the pending run has advanced to its terminal state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.leanmill.finite_construction_family import (
    construction_witness_interface,
    validate_finite_construction_family_execution,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    frontier_objective_contract,
    validate_frontier_blueprint_authority_receipts,
)
from ztare.leanmill.reviewed_family_member_ratification import (
    validate_reviewed_family_member_ratification_admission,
    validate_reviewed_family_member_ratification_aggregate,
)
from ztare.leanmill.protocol_validation import (
    require_sha256_digest as _digest,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.theory_language import TheoryLanguageExpansionRequest
from ztare.leanmill.theory_lineage_synthesis import (
    compose_selected_language_expansion,
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)


REVIEWED_FAMILY_CONSTRUCTION_OBJECTIVE_SCHEMA = (
    "leanmill.reviewed_family_construction_objective.v1"
)
REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA = (
    "leanmill.reviewed_family_objective_discharge.v2"
)


def _json_data(value: Any, *, context: str) -> Any:
    return strict_json_data(
        value,
        context=context,
        max_wire_bytes=64_000_000,
        max_integer_bits=4_096,
    )


def _blueprint(value: FrontierTheoryBlueprint | Mapping[str, Any]) -> FrontierTheoryBlueprint:
    return (
        value
        if isinstance(value, FrontierTheoryBlueprint)
        else FrontierTheoryBlueprint.from_json(value)
    )


def _construction_objective(
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any]:
    authority_replay = validate_frontier_blueprint_authority_receipts(blueprint)
    objective_contract = frontier_objective_contract(blueprint)
    if not isinstance(objective_contract, Mapping):
        raise ValueError("reviewed-family discharge requires a frozen outer objective")
    interface = construction_witness_interface(
        blueprint.adapter_id, dict(blueprint.adapter_config)
    )
    predicate = dict(interface["predicate_ir"])
    witness_schema = dict(interface["witness_schema"])
    adapter_config = dict(blueprint.adapter_config)
    if interface["target_config_sha256"] != content_hash(adapter_config):
        raise ValueError("registered construction interface crossed adapter configuration")
    core = {
        "schema": REVIEWED_FAMILY_CONSTRUCTION_OBJECTIVE_SCHEMA,
        "blueprint_id": blueprint.blueprint_id,
        "blueprint_authority_replay": authority_replay,
        "blueprint_authority_replay_sha256": str(
            authority_replay["receipt_sha256"]
        ),
        "adapter_id": blueprint.adapter_id,
        "adapter_config": adapter_config,
        "adapter_config_sha256": content_hash(adapter_config),
        "construction_witness_interface": interface,
        "interface_sha256": str(interface["interface_sha256"]),
        "target_config_sha256": str(interface["target_config_sha256"]),
        "predicate_ir": predicate,
        "predicate_sha256": content_hash(predicate),
        "witness_schema": witness_schema,
        "witness_schema_sha256": content_hash(witness_schema),
        "discharge_policy": str(interface["discharge_policy"]),
        "objective_contract": dict(objective_contract),
        "objective_contract_sha256": content_hash(dict(objective_contract)),
        "frozen_nl_objective": str(objective_contract["instruction"]),
        "authority": "reviewed_blueprint_registered_construction_objective",
    }
    return {**core, "objective_sha256": content_hash(core)}


def reviewed_family_construction_objective(
    blueprint: FrontierTheoryBlueprint | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the replayed construction objective shared by family outcomes."""

    return _construction_objective(_blueprint(blueprint))


def _source_run(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _json_data(value, context="source pending run")
    if not isinstance(row, dict):
        raise ValueError("source pending run is malformed")
    core = {key: item for key, item in row.items() if key != "run_digest"}
    if (
        row.get("schema") != "leanmill.frontier_exploration_run.v1"
        or row.get("status")
        != "frontier_objective_witness_found_pending_ratification"
        or row.get("run_digest") != content_hash(core)
        or not str(row.get("context_hash") or "")
        or not isinstance(row.get("navigation"), Mapping)
    ):
        raise ValueError("reviewed-family discharge requires the exact pending run")
    return row


def _replay_synthesis(
    *,
    source_run: Mapping[str, Any],
    objective_contract: Mapping[str, Any],
    synthesis_input: Mapping[str, Any],
    synthesis_decision: Mapping[str, Any],
    active_request: TheoryLanguageExpansionRequest,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    navigation = source_run["navigation"]
    expected_input = lineage_synthesis_input(
        navigation, objective_contract=objective_contract
    )
    frozen_input = _json_data(
        synthesis_input, context="lineage synthesis input"
    )
    if frozen_input != expected_input:
        raise ValueError("lineage synthesis input does not replay from the pending run")

    frozen_decision = _json_data(
        synthesis_decision, context="lineage synthesis decision"
    )
    if not isinstance(frozen_decision, dict):
        raise ValueError("lineage synthesis decision is malformed")
    decision_fields = {
        key: frozen_decision[key]
        for key in (
            "route",
            "selected_request_ids",
            "deferred_request_ids",
            "rationale",
            "next_discriminator",
            "kill_condition",
            "program_ids",
            "next_discriminator_request_ids",
        )
        if key in frozen_decision
    }
    if "continuation_mode" in frozen_decision:
        decision_fields["continuation_mode"] = frozen_decision["continuation_mode"]
    expected_decision = validate_lineage_synthesis_decision(
        expected_input, decision_fields
    )
    if frozen_decision != expected_decision:
        raise ValueError("lineage synthesis decision does not replay")
    if (
        expected_decision.get("route") != "escalate_language"
        or expected_decision.get("objective_contract") != objective_contract
        or navigation.get("lineage_synthesis") != expected_decision
    ):
        raise ValueError("pending run lacks the exact language-escalation decision")

    composed, _composition_receipt = compose_selected_language_expansion(
        expected_decision
    )
    if composed.to_json() != active_request.to_json():
        raise ValueError("active language request differs from synthesized request")
    if navigation.get("language_expansion_request") != active_request.to_json():
        raise ValueError("pending run carries a different active language request")

    source_request_ids: list[str] = []
    source_lineage_ids: list[str] = []
    for wrapper in expected_decision.get("selected_requests") or ():
        if not isinstance(wrapper, Mapping):
            raise ValueError("selected language request wrapper is malformed")
        request_row = wrapper.get("request")
        lineage_id = str(wrapper.get("lineage_id") or "").strip()
        if not isinstance(request_row, Mapping) or not lineage_id:
            raise ValueError("selected language request lacks source lineage identity")
        source = TheoryLanguageExpansionRequest.from_json(request_row)
        if wrapper.get("request_id") != source.request_id:
            raise ValueError("selected language wrapper crossed request identity")
        source_request_ids.append(source.request_id)
        source_lineage_ids.append(lineage_id)
    source_requests = tuple(dict.fromkeys(source_request_ids))
    source_lineages = tuple(dict.fromkeys(source_lineage_ids))
    if not source_requests or not source_lineages:
        raise ValueError("language escalation lacks nonempty source lineage identities")
    return expected_input, expected_decision, source_requests, source_lineages


def replay_reviewed_family_synthesis(
    *,
    source_run: Mapping[str, Any],
    objective_contract: Mapping[str, Any],
    synthesis_input: Mapping[str, Any],
    synthesis_decision: Mapping[str, Any],
    active_request: TheoryLanguageExpansionRequest,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    """Replay the language-selection provenance common to family outcomes."""

    return _replay_synthesis(
        source_run=source_run,
        objective_contract=objective_contract,
        synthesis_input=synthesis_input,
        synthesis_decision=synthesis_decision,
        active_request=active_request,
    )


def build_reviewed_family_objective_discharge(
    *,
    source_pending_run: Mapping[str, Any],
    blueprint: FrontierTheoryBlueprint | Mapping[str, Any],
    active_request: TheoryLanguageExpansionRequest | Mapping[str, Any],
    synthesis_input: Mapping[str, Any],
    synthesis_decision: Mapping[str, Any],
    family_execution: Mapping[str, Any],
    admission: Mapping[str, Any],
    ratification_aggregate: Mapping[str, Any],
    attempted_ratification_aggregate_sha256s: Sequence[str],
    frozen_lineage_ids: Sequence[str],
) -> dict[str, Any]:
    """Build and immediately replay one family-origin terminal transition."""

    frozen_blueprint = _blueprint(blueprint)
    request = (
        active_request
        if isinstance(active_request, TheoryLanguageExpansionRequest)
        else TheoryLanguageExpansionRequest.from_json(active_request)
    )
    construction_objective = _construction_objective(frozen_blueprint)
    run = _source_run(source_pending_run)
    objective_contract = construction_objective["objective_contract"]
    replayed_input, replayed_decision, source_requests, source_lineages = (
        _replay_synthesis(
            source_run=run,
            objective_contract=objective_contract,
            synthesis_input=synthesis_input,
            synthesis_decision=synthesis_decision,
            active_request=request,
        )
    )
    lineages = tuple(str(value).strip() for value in frozen_lineage_ids)
    if (
        not lineages
        or any(not value for value in lineages)
        or len(set(lineages)) != len(lineages)
        or not set(source_lineages) <= set(lineages)
    ):
        raise ValueError("frozen lineage identities do not cover request sources")
    execution = validate_finite_construction_family_execution(family_execution)
    frozen_admission = validate_reviewed_family_member_ratification_admission(
        admission
    )
    aggregate = validate_reviewed_family_member_ratification_aggregate(
        ratification_aggregate
    )
    attempts = [str(value) for value in attempted_ratification_aggregate_sha256s]
    for value in attempts:
        _digest(value, context="attempted ratification aggregate")
    if len(set(attempts)) != len(attempts):
        raise ValueError("attempted ratification aggregate refs must be unique")
    closure_ref = aggregate["ratification_result"].get("closure_record_ref")
    if not isinstance(closure_ref, Mapping):
        raise ValueError("ratified family aggregate lacks governed closure identity")

    core = {
        "schema": REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA,
        "blueprint": frozen_blueprint.to_json(),
        "blueprint_id": frozen_blueprint.blueprint_id,
        "construction_objective": construction_objective,
        "construction_objective_sha256": str(
            construction_objective["objective_sha256"]
        ),
        "source_pending_run": run,
        "source_run_digest": str(run["run_digest"]),
        "source_pending_run_sha256": content_hash(run),
        "active_language_request": request.to_json(),
        "language_request_id": request.request_id,
        "lineage_synthesis_input": replayed_input,
        "lineage_synthesis_input_sha256": str(replayed_input["input_sha256"]),
        "lineage_synthesis_decision": replayed_decision,
        "lineage_synthesis_decision_sha256": str(
            replayed_decision["receipt_sha256"]
        ),
        "source_request_ids": list(source_requests),
        "source_lineage_ids": list(source_lineages),
        "frozen_lineage_ids": list(lineages),
        "finite_family_execution": execution,
        "finite_family_execution_sha256": str(execution["receipt_sha256"]),
        "admission": frozen_admission,
        "admission_sha256": str(frozen_admission["receipt_sha256"]),
        "ratification_aggregate": aggregate,
        "ratification_aggregate_sha256": str(aggregate["aggregate_sha256"]),
        "attempted_ratification_aggregate_sha256s": attempts,
        "governed_closure_record_sha256": str(closure_ref["record_sha256"]),
        "objective_status": "discharged_by_exact_constructed_witness",
        "claim_scope": (
            "one reviewed family member satisfies the frozen construction "
            "objective and passed provider-free kernel governance"
        ),
        "ambient_nonexistence_authority": False,
        "authority": "reviewed_family_content_bound_terminal_transition",
    }
    return validate_reviewed_family_objective_discharge(
        {**core, "receipt_sha256": content_hash(core)}
    )


def validate_reviewed_family_objective_discharge(
    value: Mapping[str, Any],
    *,
    current_blueprint: FrontierTheoryBlueprint | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay every authority edge embedded in a family-origin discharge."""

    row = _json_data(value, context="reviewed-family objective discharge")
    required = {
        "schema",
        "blueprint",
        "blueprint_id",
        "construction_objective",
        "construction_objective_sha256",
        "source_pending_run",
        "source_run_digest",
        "source_pending_run_sha256",
        "active_language_request",
        "language_request_id",
        "lineage_synthesis_input",
        "lineage_synthesis_input_sha256",
        "lineage_synthesis_decision",
        "lineage_synthesis_decision_sha256",
        "source_request_ids",
        "source_lineage_ids",
        "frozen_lineage_ids",
        "finite_family_execution",
        "finite_family_execution_sha256",
        "admission",
        "admission_sha256",
        "ratification_aggregate",
        "ratification_aggregate_sha256",
        "attempted_ratification_aggregate_sha256s",
        "governed_closure_record_sha256",
        "objective_status",
        "claim_scope",
        "ambient_nonexistence_authority",
        "authority",
    }
    if not isinstance(row, dict) or set(row) != required | {"receipt_sha256"}:
        raise ValueError("reviewed-family objective discharge fields changed identity")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("objective_status")
        != "discharged_by_exact_constructed_witness"
        or row.get("ambient_nonexistence_authority") is not False
        or row.get("authority")
        != "reviewed_family_content_bound_terminal_transition"
    ):
        raise ValueError("reviewed-family objective discharge digest mismatch")

    blueprint = FrontierTheoryBlueprint.from_json(row["blueprint"])
    if current_blueprint is not None and _blueprint(current_blueprint).to_json() != (
        blueprint.to_json()
    ):
        raise ValueError("reviewed-family discharge crossed the current blueprint")
    objective = _construction_objective(blueprint)
    if (
        row["blueprint_id"] != blueprint.blueprint_id
        or row["construction_objective"] != objective
        or row["construction_objective_sha256"] != objective["objective_sha256"]
    ):
        raise ValueError("reviewed-family construction objective changed identity")

    run = _source_run(row["source_pending_run"])
    request = TheoryLanguageExpansionRequest.from_json(
        row["active_language_request"]
    )
    synthesis_input, synthesis_decision, source_requests, source_lineages = (
        _replay_synthesis(
            source_run=run,
            objective_contract=objective["objective_contract"],
            synthesis_input=row["lineage_synthesis_input"],
            synthesis_decision=row["lineage_synthesis_decision"],
            active_request=request,
        )
    )
    frozen_lineages = row.get("frozen_lineage_ids")
    if (
        row["source_run_digest"] != run["run_digest"]
        or row["source_pending_run_sha256"] != content_hash(run)
        or row["language_request_id"] != request.request_id
        or row["lineage_synthesis_input_sha256"] != synthesis_input["input_sha256"]
        or row["lineage_synthesis_decision_sha256"]
        != synthesis_decision["receipt_sha256"]
        or row["source_request_ids"] != list(source_requests)
        or row["source_lineage_ids"] != list(source_lineages)
        or not isinstance(frozen_lineages, list)
        or not frozen_lineages
        or any(not isinstance(value, str) or not value for value in frozen_lineages)
        or len(set(frozen_lineages)) != len(frozen_lineages)
        or not set(source_lineages) <= set(frozen_lineages)
    ):
        raise ValueError("reviewed-family source or lineage binding changed identity")

    execution = validate_finite_construction_family_execution(
        row["finite_family_execution"]
    )
    admission = validate_reviewed_family_member_ratification_admission(
        row["admission"]
    )
    aggregate = validate_reviewed_family_member_ratification_aggregate(
        row["ratification_aggregate"]
    )
    interface = objective["construction_witness_interface"]
    attempts = row.get("attempted_ratification_aggregate_sha256s")
    closure_ref = aggregate["ratification_result"].get("closure_record_ref")
    if not isinstance(attempts, list):
        raise ValueError("reviewed-family discharge lacks attempted aggregate refs")
    for attempt in attempts:
        _digest(attempt, context="attempted ratification aggregate")
    if (
        len(set(attempts)) != len(attempts)
        or aggregate["aggregate_sha256"] not in attempts
        or execution.get("status") != "witness_found"
        or aggregate.get("status") != "ratified"
        or aggregate.get("admission") != admission
        or aggregate.get("admission_sha256") != admission["receipt_sha256"]
        or execution.get("receipt_sha256")
        != admission["family_execution_receipt_sha256"]
        or execution.get("family_receipt_sha256")
        != admission["family_receipt_sha256"]
        or execution.get("family_id") != admission["family_id"]
        or execution.get("request_id") != request.request_id
        or admission.get("request_id") != request.request_id
        or execution.get("context_hash") != run.get("context_hash")
        or admission.get("context_hash") != run.get("context_hash")
        or execution.get("adapter_id") != objective["adapter_id"]
        or admission.get("adapter_id") != objective["adapter_id"]
        or execution.get("target_interface_sha256") != interface["interface_sha256"]
        or admission.get("interface_sha256") != interface["interface_sha256"]
        or admission.get("target_config_sha256")
        != objective["target_config_sha256"]
        or admission.get("predicate_sha256") != objective["predicate_sha256"]
        or admission.get("witness_schema_sha256")
        != objective["witness_schema_sha256"]
        or row["finite_family_execution_sha256"] != execution["receipt_sha256"]
        or row["admission_sha256"] != admission["receipt_sha256"]
        or row["ratification_aggregate_sha256"]
        != aggregate["aggregate_sha256"]
        or not isinstance(closure_ref, Mapping)
        or row["governed_closure_record_sha256"]
        != closure_ref.get("record_sha256")
    ):
        raise ValueError("reviewed-family terminal transition no longer replays")
    return row


__all__ = [
    "REVIEWED_FAMILY_CONSTRUCTION_OBJECTIVE_SCHEMA",
    "REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA",
    "build_reviewed_family_objective_discharge",
    "replay_reviewed_family_synthesis",
    "reviewed_family_construction_objective",
    "validate_reviewed_family_objective_discharge",
]
