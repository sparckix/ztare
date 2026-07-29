"""Typed terminal credit for one exhausted reviewed construction family.

Family review, exact execution, post-outcome navigation, and campaign stopping
authority are separate decisions.  This module joins their immutable receipts
without promoting family exhaustion to ambient nonexistence, kernel credit, or
novelty.  A next representation counts only when a later navigator workbench
request cites the exact execution and its feedback receipt.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from ztare.leanmill.finite_construction_family import (
    AdmittedConstructionOrigin,
    construction_witness_interface,
    validate_finite_construction_family,
    validate_finite_construction_family_execution,
    validate_persisted_parameterized_finite_construction_family,
)
from ztare.leanmill.frontier_blueprint import FrontierTheoryBlueprint
from ztare.leanmill.reviewed_family_member_ratification import (
    validate_reviewed_finite_family_authority,
)
from ztare.leanmill.reviewed_family_objective_discharge import (
    replay_reviewed_family_synthesis,
    reviewed_family_construction_objective,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.data_only_json import strict_json_data
from ztare.leanmill.theory_language import TheoryLanguageExpansionRequest
from ztare.leanmill.theory_lineage_synthesis import (
    compose_selected_language_expansion,
    lineage_synthesis_input,
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.theory_program import TheoryProgram


REVIEWED_FAMILY_EXHAUSTION_OBSERVATION_SCHEMA = (
    "leanmill.reviewed_family_exhaustion_observation.v1"
)
REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA = (
    "leanmill.reviewed_family_exhaustion_discharge.v1"
)
REVIEWED_FAMILY_NEXT_REPRESENTATION_AUTHORSHIP_SCHEMA = (
    "leanmill.reviewed_family_next_representation_authorship.v1"
)
_OBSERVATION_CLAIM_SCOPE = (
    "all members of one exact reviewed finite family were rejected; "
    "no ambient construction-space conclusion"
)
_DISCHARGE_CLAIM_SCOPE = (
    "one exact reviewed finite family is exhausted and a post-outcome "
    "campaign-authored representation is frozen; ambient existence remains open"
)


def _json_data(value: Any, *, context: str) -> Any:
    return strict_json_data(
        value,
        context=context,
        max_wire_bytes=64_000_000,
        max_integer_bits=4_096,
    )


def _blueprint(
    value: FrontierTheoryBlueprint | Mapping[str, Any],
) -> FrontierTheoryBlueprint:
    return (
        value
        if isinstance(value, FrontierTheoryBlueprint)
        else FrontierTheoryBlueprint.from_json(value)
    )


def _run(value: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    row = _json_data(value, context=context)
    if not isinstance(row, dict):
        raise ValueError(f"{context} is malformed")
    core = {key: item for key, item in row.items() if key != "run_digest"}
    if (
        row.get("schema") != "leanmill.frontier_exploration_run.v1"
        or row.get("run_digest") != content_hash(core)
        or not str(row.get("context_hash") or "")
        or not isinstance(row.get("navigation"), Mapping)
    ):
        raise ValueError(f"{context} digest or identity mismatch")
    return row


def reviewed_family_exhaustion_stop_permission(
    blueprint: FrontierTheoryBlueprint | Mapping[str, Any],
) -> dict[str, Any] | None:
    """Recognize the conservative legacy spelling of the family-null stop.

    New blueprints should eventually carry a structured terminal alternative.
    Existing frozen blueprints expose only the reviewed instruction, so this
    recognizer accepts one narrow, substrate-neutral clause and refuses every
    other wording.  Refusal leaves the campaign unresolved.
    """

    frozen = _blueprint(blueprint)
    objective = reviewed_family_construction_objective(frozen)
    instruction = str(objective["frozen_nl_objective"])
    normalized_instruction = re.sub(
        r"[^a-z0-9]+", " ", instruction.lower()
    ).strip()
    if not normalized_instruction.startswith("stop after "):
        return None
    for clause in (part.strip() for part in instruction.split(";")):
        normalized = re.sub(r"[^a-z0-9]+", " ", clause.lower()).strip()
        if normalized.startswith(
            "one campaign authored finite construction family "
        ) and all(
            phrase in normalized
            for phrase in (
                "finite construction family",
                "completely enumerated",
                "replayable member level rejection receipts",
                "typed next representation",
            )
        ) and not re.search(
            r"\b(?:no|not|never|without|cannot|can t|do not|does not|must not|unless|whether|except)\b",
            normalized,
        ):
            core = {
                "schema": "leanmill.family_exhaustion_stop_permission.v1",
                "blueprint_id": frozen.blueprint_id,
                "objective_contract_sha256": str(
                    objective["objective_contract_sha256"]
                ),
                "matched_clause": clause,
                "matched_clause_sha256": content_hash(clause),
                "outcome_kind": (
                    "reviewed_finite_family_exhausted_with_typed_next_representation"
                ),
                "recognition_policy": "conservative_legacy_text_clause_v1",
                "authority": "frozen_stop_instruction_exact_clause",
            }
            return {**core, "receipt_sha256": content_hash(core)}
    return None


def _source_family_run(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _run(value, context="source family run")
    if row.get("status") != "blocked_adapter_gap":
        raise ValueError("family exhaustion requires the exact pre-execution run")
    return row


def _source_frozen_lineage_ids(
    source_run: Mapping[str, Any],
    *,
    source_lineage_ids: Sequence[str],
) -> frozenset[str]:
    """Derive the terminal lineage set from the pre-outcome run."""

    navigation = source_run["navigation"]
    identities = {str(value) for value in source_lineage_ids}
    records: set[tuple[str, str]] = set()
    for field in ("finalists", "objective_survivors"):
        rows = navigation.get(field)
        if not isinstance(rows, (list, tuple)):
            continue
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            raw_program = raw.get("theory_program")
            program = None
            if isinstance(raw_program, Mapping):
                try:
                    program = TheoryProgram.from_json(raw_program)
                except (TypeError, ValueError):
                    continue
            elif raw_program is not None:
                continue
            program_id = str(
                raw.get("theory_program_id")
                or (program.program_id if program is not None else "")
            )
            if not program_id or (
                program is not None and program_id != program.program_id
            ):
                continue
            lineage_id = program.lineage_id if program is not None else ""
            key = (
                ("lineage", lineage_id)
                if lineage_id
                else ("program", program_id)
            )
            if key in records:
                continue
            records.add(key)
            identities.add(
                lineage_id if lineage_id else "legacy-program:" + program_id
            )
    return frozenset(identities)


def validate_reviewed_family_execution_join(
    *,
    family: Mapping[str, Any],
    family_execution: Mapping[str, Any],
    request_id: str,
    context_hash: str,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
    construction_origin: AdmittedConstructionOrigin | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay the exact reviewed-family/member execution join."""

    frozen_family = validate_finite_construction_family(
        family,
        request_id=request_id,
        context_hash=context_hash,
        adapter_id=adapter_id,
        witness_interface=witness_interface,
        construction_origin=construction_origin,
    )
    try:
        execution = validate_finite_construction_family_execution(
            family_execution,
            family=frozen_family,
            witness_interface=witness_interface,
            construction_origin=construction_origin,
        )
    except ValueError as exc:
        raise ValueError(
            "finite family execution does not cover the reviewed family"
        ) from exc
    family_members = list(frozen_family["members"])
    execution_members = list(execution["member_results"])
    if (
        execution.get("family_id") != frozen_family["family_id"]
        or execution.get("family_receipt_sha256")
        != frozen_family["receipt_sha256"]
        or execution.get("request_id") != request_id
        or execution.get("gap_id") != frozen_family["gap_id"]
        or execution.get("context_hash") != context_hash
        or execution.get("adapter_id") != adapter_id
        or execution.get("target_interface_sha256")
        != witness_interface["interface_sha256"]
        or execution.get("expected_parameter_ids")
        != frozen_family["parameter_ids"]
        or len(execution_members) != int(frozen_family["declared_cardinality"])
        or len(execution_members) != len(family_members)
        or any(
            result.get("parameter_id") != member["parameter_id"]
            or result.get("source_artifact_sha256")
            != member["artifact_sha256"]
            for member, result in zip(family_members, execution_members)
        )
    ):
        raise ValueError("finite family execution does not cover the reviewed family")
    return frozen_family, execution


def _validate_persisted_parameterized_exhaustion_join(
    *,
    family: Mapping[str, Any],
    family_execution: Mapping[str, Any],
    parameterization: Mapping[str, Any],
    parameterization_execution: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    request_id: str,
    context_hash: str,
    adapter_id: str,
    witness_interface: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Replay a cold exhaustion projection without restoring admission."""

    frozen_family = validate_persisted_parameterized_finite_construction_family(
        family,
        request_id=request_id,
        gap_id=str(family.get("gap_id") or ""),
        context_hash=context_hash,
        adapter_id=adapter_id,
        witness_interface=witness_interface,
        parameterization=parameterization,
        parameterization_execution=parameterization_execution,
        forge_quarantine_receipt=forge_quarantine_receipt,
    )
    execution = validate_finite_construction_family_execution(family_execution)
    members = list(frozen_family["members"])
    results = list(execution["member_results"])
    expected_origin_hashes = {
        "parameterization_sha256": str(parameterization["receipt_sha256"]),
        "adapter_forge_quarantine_receipt_sha256": str(
            forge_quarantine_receipt["receipt_sha256"]
        ),
        "parameterization_execution_sha256": str(
            parameterization_execution["receipt_sha256"]
        ),
    }
    if (
        execution.get("family_id") != frozen_family["family_id"]
        or execution.get("family_receipt_sha256")
        != frozen_family["receipt_sha256"]
        or execution.get("request_id") != request_id
        or execution.get("gap_id") != frozen_family["gap_id"]
        or execution.get("context_hash") != context_hash
        or execution.get("adapter_id") != adapter_id
        or execution.get("target_interface_sha256")
        != witness_interface["interface_sha256"]
        or execution.get("expected_parameter_ids")
        != frozen_family["parameter_ids"]
        or execution.get("construction_origin_sha256s")
        != expected_origin_hashes
        or len(results) != len(members)
        or any(
            result.get("parameter_id") != member["parameter_id"]
            or result.get("source_artifact_sha256")
            != member["artifact_sha256"]
            for member, result in zip(members, results, strict=True)
        )
    ):
        raise ValueError(
            "persisted finite family execution changed its signed projection"
        )
    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_bytes_authority,
    )

    _parameterization, forge = (
        validate_reviewed_construction_parameterization_bytes_authority(
            parameterization,
            forge_quarantine_receipt,
            witness_interface=witness_interface,
        )
    )
    return frozen_family, execution, forge


def build_reviewed_family_exhaustion_observation(
    *,
    source_family_run: Mapping[str, Any],
    blueprint: FrontierTheoryBlueprint | Mapping[str, Any],
    active_request: TheoryLanguageExpansionRequest | Mapping[str, Any],
    synthesis_input: Mapping[str, Any],
    synthesis_decision: Mapping[str, Any],
    family: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    family_execution: Mapping[str, Any],
    frozen_lineage_ids: Sequence[str],
    construction_origin: AdmittedConstructionOrigin | None = None,
) -> dict[str, Any]:
    """Freeze the reviewed all-rejected result before navigation observes it."""

    frozen_blueprint = _blueprint(blueprint)
    objective = reviewed_family_construction_objective(frozen_blueprint)
    permission = reviewed_family_exhaustion_stop_permission(frozen_blueprint)
    if permission is None:
        raise ValueError(
            "frozen objective does not authorize family-exhaustion discharge"
        )
    run = _source_family_run(source_family_run)
    request = (
        active_request
        if isinstance(active_request, TheoryLanguageExpansionRequest)
        else TheoryLanguageExpansionRequest.from_json(active_request)
    )
    replayed_input, replayed_decision, source_requests, source_lineages = (
        replay_reviewed_family_synthesis(
            source_run=run,
            objective_contract=objective["objective_contract"],
            synthesis_input=synthesis_input,
            synthesis_decision=synthesis_decision,
            active_request=request,
        )
    )
    lineages = tuple(str(value).strip() for value in frozen_lineage_ids)
    expected_lineages = _source_frozen_lineage_ids(
        run, source_lineage_ids=source_lineages
    )
    if (
        not lineages
        or any(not value for value in lineages)
        or len(set(lineages)) != len(lineages)
        or set(lineages) != expected_lineages
    ):
        raise ValueError("frozen lineages do not cover the family request sources")

    interface = construction_witness_interface(
        frozen_blueprint.adapter_id, dict(frozen_blueprint.adapter_config)
    )
    parameterized = (family.get("family_spec") or {}).get("kind") == (
        "typed_construction_parameterization.v1"
    )
    if parameterized != isinstance(
        construction_origin, AdmittedConstructionOrigin
    ):
        raise ValueError(
            "family exhaustion requires exactly one admitted parameterized origin"
        )
    frozen_family, execution = validate_reviewed_family_execution_join(
        family=family,
        family_execution=family_execution,
        request_id=request.request_id,
        context_hash=str(run["context_hash"]),
        adapter_id=frozen_blueprint.adapter_id,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    forge, host, review_binding = validate_reviewed_finite_family_authority(
        frozen_family,
        forge_quarantine_receipt,
        witness_interface=interface,
        construction_origin=construction_origin,
    )
    member_refs = [
        str(member["receipt_sha256"]) for member in execution["member_results"]
    ]
    if (
        execution.get("status") != "exhausted"
        or len(member_refs) != int(frozen_family["declared_cardinality"])
    ):
        raise ValueError("reviewed family exhaustion does not replay its family")

    origin_json = (
        construction_origin.to_json()
        if construction_origin is not None
        else None
    )
    core = {
        "schema": REVIEWED_FAMILY_EXHAUSTION_OBSERVATION_SCHEMA,
        "blueprint": frozen_blueprint.to_json(),
        "blueprint_id": frozen_blueprint.blueprint_id,
        "construction_objective": objective,
        "construction_objective_sha256": str(objective["objective_sha256"]),
        "stop_permission": permission,
        "stop_permission_sha256": str(permission["receipt_sha256"]),
        "source_family_run": run,
        "source_run_digest": str(run["run_digest"]),
        "source_run_sha256": content_hash(run),
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
        "finite_family": frozen_family,
        "finite_family_sha256": str(frozen_family["receipt_sha256"]),
        "forge_quarantine_receipt": forge,
        "forge_quarantine_receipt_sha256": str(forge["receipt_sha256"]),
        "forge_host_conformance_receipt_sha256": str(host["receipt_sha256"]),
        "forge_review_binding_receipt_sha256": str(
            review_binding["receipt_sha256"]
        ),
        "finite_family_execution": execution,
        "finite_family_execution_sha256": str(execution["receipt_sha256"]),
        "construction_parameterization": (
            origin_json["parameterization"]
            if origin_json is not None
            else None
        ),
        "construction_parameterization_execution": (
            origin_json["parameterization_execution"]
            if origin_json is not None
            else None
        ),
        "member_rejection_receipt_sha256s": member_refs,
        "objective_status": "family_exhausted_awaiting_typed_next_representation",
        "claim_scope": _OBSERVATION_CLAIM_SCOPE,
        "ambient_nonexistence_authority": False,
        "kernel_ratification_authority": False,
        "novelty_authority": False,
        "authority": "reviewed_family_exhaustion_pre_navigation_observation",
    }
    return validate_reviewed_family_exhaustion_observation(
        {**core, "receipt_sha256": content_hash(core)}
    )


def validate_reviewed_family_exhaustion_observation(
    value: Mapping[str, Any],
    *,
    current_blueprint: FrontierTheoryBlueprint | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = _json_data(value, context="reviewed family exhaustion observation")
    required = {
        "schema", "blueprint", "blueprint_id", "construction_objective",
        "construction_objective_sha256", "stop_permission",
        "stop_permission_sha256", "source_family_run", "source_run_digest",
        "source_run_sha256", "active_language_request", "language_request_id",
        "lineage_synthesis_input", "lineage_synthesis_input_sha256",
        "lineage_synthesis_decision", "lineage_synthesis_decision_sha256",
        "source_request_ids", "source_lineage_ids", "frozen_lineage_ids",
        "finite_family", "finite_family_sha256", "forge_quarantine_receipt",
        "forge_quarantine_receipt_sha256",
        "forge_host_conformance_receipt_sha256",
        "forge_review_binding_receipt_sha256", "finite_family_execution",
        "finite_family_execution_sha256", "construction_parameterization",
        "construction_parameterization_execution",
        "member_rejection_receipt_sha256s",
        "objective_status", "claim_scope", "ambient_nonexistence_authority",
        "kernel_ratification_authority", "novelty_authority", "authority",
    }
    if not isinstance(row, dict) or set(row) != required | {"receipt_sha256"}:
        raise ValueError("reviewed family exhaustion observation fields changed")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != REVIEWED_FAMILY_EXHAUSTION_OBSERVATION_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("objective_status")
        != "family_exhausted_awaiting_typed_next_representation"
        or row.get("claim_scope") != _OBSERVATION_CLAIM_SCOPE
        or row.get("ambient_nonexistence_authority") is not False
        or row.get("kernel_ratification_authority") is not False
        or row.get("novelty_authority") is not False
        or row.get("authority")
        != "reviewed_family_exhaustion_pre_navigation_observation"
    ):
        raise ValueError("reviewed family exhaustion observation digest mismatch")

    blueprint = FrontierTheoryBlueprint.from_json(row["blueprint"])
    if current_blueprint is not None and _blueprint(current_blueprint).to_json() != (
        blueprint.to_json()
    ):
        raise ValueError("family exhaustion crossed the current blueprint")
    objective = reviewed_family_construction_objective(blueprint)
    permission = reviewed_family_exhaustion_stop_permission(blueprint)
    if permission is None:
        raise ValueError("family exhaustion stop permission is unavailable")
    run = _source_family_run(row["source_family_run"])
    request = TheoryLanguageExpansionRequest.from_json(
        row["active_language_request"]
    )
    replayed_input, replayed_decision, source_requests, source_lineages = (
        replay_reviewed_family_synthesis(
            source_run=run,
            objective_contract=objective["objective_contract"],
            synthesis_input=row["lineage_synthesis_input"],
            synthesis_decision=row["lineage_synthesis_decision"],
            active_request=request,
        )
    )
    lineages = row.get("frozen_lineage_ids")
    expected_lineages = _source_frozen_lineage_ids(
        run, source_lineage_ids=source_lineages
    )
    if (
        row["blueprint_id"] != blueprint.blueprint_id
        or row["construction_objective"] != objective
        or row["construction_objective_sha256"] != objective["objective_sha256"]
        or row["stop_permission"] != permission
        or row["stop_permission_sha256"] != permission["receipt_sha256"]
        or row["source_run_digest"] != run["run_digest"]
        or row["source_run_sha256"] != content_hash(run)
        or row["language_request_id"] != request.request_id
        or row["lineage_synthesis_input_sha256"] != replayed_input["input_sha256"]
        or row["lineage_synthesis_decision_sha256"]
        != replayed_decision["receipt_sha256"]
        or row["source_request_ids"] != list(source_requests)
        or row["source_lineage_ids"] != list(source_lineages)
        or not isinstance(lineages, list)
        or not lineages
        or len(set(lineages)) != len(lineages)
        or set(lineages) != expected_lineages
    ):
        raise ValueError("family exhaustion source identity changed")

    interface = construction_witness_interface(
        blueprint.adapter_id, dict(blueprint.adapter_config)
    )
    parameterization = row.get("construction_parameterization")
    parameterization_execution = row.get(
        "construction_parameterization_execution"
    )
    if (parameterization is None) != (parameterization_execution is None):
        raise ValueError("family exhaustion construction origin is incomplete")
    if parameterization is not None:
        family, execution, forge = (
            _validate_persisted_parameterized_exhaustion_join(
                family=row["finite_family"],
                family_execution=row["finite_family_execution"],
                parameterization=parameterization,
                parameterization_execution=parameterization_execution,
                forge_quarantine_receipt=row["forge_quarantine_receipt"],
                request_id=request.request_id,
                context_hash=str(run["context_hash"]),
                adapter_id=blueprint.adapter_id,
                witness_interface=interface,
            )
        )
        host = dict(forge["host_conformance"])
        review_binding = dict(forge["review_evidence_binding"])
    else:
        family, execution = validate_reviewed_family_execution_join(
            family=row["finite_family"],
            family_execution=row["finite_family_execution"],
            request_id=request.request_id,
            context_hash=str(run["context_hash"]),
            adapter_id=blueprint.adapter_id,
            witness_interface=interface,
            construction_origin=None,
        )
        forge, host, review_binding = validate_reviewed_finite_family_authority(
            family,
            row["forge_quarantine_receipt"],
            witness_interface=interface,
            construction_origin=None,
        )
    member_refs = [
        str(member["receipt_sha256"]) for member in execution["member_results"]
    ]
    if (
        row["finite_family_sha256"] != family["receipt_sha256"]
        or row["forge_quarantine_receipt_sha256"] != forge["receipt_sha256"]
        or row["forge_host_conformance_receipt_sha256"] != host["receipt_sha256"]
        or row["forge_review_binding_receipt_sha256"]
        != review_binding["receipt_sha256"]
        or row["finite_family_execution_sha256"] != execution["receipt_sha256"]
        or row["member_rejection_receipt_sha256s"] != member_refs
        or execution.get("status") != "exhausted"
    ):
        raise ValueError("family exhaustion review or execution changed identity")
    return row


def _feedback(
    value: Mapping[str, Any], observation: Mapping[str, Any]
) -> dict[str, Any]:
    row = _json_data(value, context="family exhaustion feedback")
    required = {
        "schema", "context_hash", "request_id", "outcome", "reason",
        "evidence_refs", "route", "program_ids",
        "repeat_requires_new_evidence", "authority", "receipt_sha256",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("family exhaustion feedback is malformed")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    expected_evidence = [
        str(observation["forge_quarantine_receipt_sha256"]),
        str(observation["finite_family_execution_sha256"]),
    ]
    if (
        row.get("schema") != "leanmill.theory_language_compilation_feedback.v1"
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("context_hash")
        != observation["source_family_run"]["context_hash"]
        or row.get("request_id") != observation["language_request_id"]
        or row.get("outcome") != "rejected"
        or row.get("reason")
        != "reviewed_finite_family_exhausted:"
        + str(observation["finite_family"]["family_id"])
        or row.get("evidence_refs") != expected_evidence
        or row.get("route") != "continue_search"
        or row.get("program_ids") != []
        or row.get("repeat_requires_new_evidence") is not True
        or row.get("authority") != "host_language_compiler"
    ):
        raise ValueError("family exhaustion feedback crossed its execution")
    return row


def _feedback_wave_binding(
    value: Mapping[str, Any],
    *,
    feedback: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    row = _json_data(value, context="family exhaustion feedback wave")
    required = {
        "schema", "context_hash", "context_epoch", "request_id",
        "feedback_receipt_sha256", "search_wave", "authority",
        "receipt_sha256",
    }
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("family exhaustion feedback wave is malformed")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    source_navigation = observation["source_family_run"]["navigation"]
    source_epoch = int(
        source_navigation.get(
            "context_epoch",
            observation["source_family_run"].get("context_summary", {}).get(
                "context_epoch", 0
            ),
        )
    )
    if (
        row.get("schema")
        != "leanmill.theory_language_feedback_wave_binding.v1"
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("feedback_receipt_sha256") != feedback["receipt_sha256"]
        or row.get("request_id") != observation["language_request_id"]
        or row.get("context_hash")
        != observation["source_family_run"]["context_hash"]
        or int(row.get("context_epoch", -1)) != source_epoch
        or int(row.get("search_wave", 0)) < 1
        or row.get("authority") != "deterministic_campaign_lifecycle"
    ):
        raise ValueError("family exhaustion feedback wave changed identity")
    return row


def _workbench_receipt_for_request(
    navigation: Mapping[str, Any],
    *,
    lineage_id: str,
    request: TheoryLanguageExpansionRequest,
) -> dict[str, Any]:
    matching_lineages = [
        lineage
        for lineage in navigation.get("lineages") or ()
        if isinstance(lineage, Mapping)
        and str(lineage.get("lineage_id") or "") == lineage_id
    ]
    if len(matching_lineages) != 1 or not isinstance(
        matching_lineages[0].get("navigation"), Mapping
    ):
        raise ValueError("next representation lacks unique lineage authorship")
    traces = [
        row
        for row in matching_lineages[0]["navigation"].get("trace") or ()
        if isinstance(row, Mapping)
    ]
    matches: dict[str, dict[str, Any]] = {}
    for trace in traces:
        receipt = trace.get("receipt")
        if not isinstance(receipt, Mapping):
            continue
        row = dict(receipt)
        required_fields = {
            "schema", "capability_id", "context_hash", "input_hashes",
            "output_summary", "claim_bindings", "authority", "receipt_id",
        }
        core = {key: item for key, item in row.items() if key != "receipt_id"}
        summary = row.get("output_summary")
        expected_input_hashes = {
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
        }
        if (
            trace.get("decision") != "request"
            or trace.get("capability_id")
            != "propose_theory_language_expansion"
            or set(row) != required_fields
            or row.get("schema") != "leanmill.axiompack_workbench_receipt.v1"
            or row.get("receipt_id") != "sha256:" + content_hash(core)
            or row.get("capability_id") != "propose_theory_language_expansion"
            or row.get("context_hash") != request.source_context_hash
            or row.get("input_hashes") != expected_input_hashes
            or row.get("claim_bindings")
            != ["propose_theory_language_expansion"]
            or row.get("authority") != "deterministic_host"
            or not isinstance(summary, Mapping)
            or summary.get("status") != "outbound_blueprint_request"
            or summary.get("request_id") != request.request_id
            or summary.get("request") != request.to_json()
        ):
            continue
        matches[str(row["receipt_id"])] = row
    if len(matches) != 1:
        raise ValueError("next representation lacks unique workbench authorship")
    return next(iter(matches.values()))


def _next_representation_authorship(
    *,
    observation: Mapping[str, Any],
    feedback: Mapping[str, Any],
    feedback_wave_binding: Mapping[str, Any],
    next_run: Mapping[str, Any],
) -> tuple[dict[str, Any], TheoryLanguageExpansionRequest, dict[str, Any]]:
    navigation = next_run["navigation"]
    raw_decision = navigation.get("lineage_synthesis")
    if not isinstance(raw_decision, Mapping):
        raise ValueError("next representation lacks lineage synthesis")
    objective = observation["construction_objective"]["objective_contract"]
    synthesis_input = lineage_synthesis_input(
        navigation, objective_contract=objective
    )
    decision = dict(raw_decision)
    fields = {
        key: decision[key]
        for key in (
            "route", "selected_request_ids", "deferred_request_ids",
            "rationale", "next_discriminator", "kill_condition", "program_ids",
            "next_discriminator_request_ids",
        )
        if key in decision
    }
    if "continuation_mode" in decision:
        fields["continuation_mode"] = decision["continuation_mode"]
    replayed = validate_lineage_synthesis_decision(synthesis_input, fields)
    if replayed != decision or decision.get("route") != "escalate_language":
        raise ValueError("next representation synthesis does not replay")
    active_request, _composition = compose_selected_language_expansion(replayed)
    if navigation.get("language_expansion_request") != active_request.to_json():
        raise ValueError("next representation differs from the active request")
    required_refs = {
        str(observation["finite_family_execution_sha256"]),
        str(feedback["receipt_sha256"]),
    }
    if not required_refs <= set(active_request.evidence_refs):
        raise ValueError("next representation is not bound to family exhaustion")
    prior_request_ids = {
        str(observation["language_request_id"]),
        *(
            str(value) for value in observation.get("source_request_ids") or ()
        ),
    }
    if active_request.request_id in prior_request_ids:
        raise ValueError("next representation was authored before family execution")

    selected = replayed.get("selected_requests") or ()
    workbench_refs: list[str] = []
    selected_request_ids: list[str] = []
    selected_lineage_ids: list[str] = []
    for wrapper in selected:
        if not isinstance(wrapper, Mapping) or not isinstance(
            wrapper.get("request"), Mapping
        ):
            raise ValueError("next representation wrapper is malformed")
        request = TheoryLanguageExpansionRequest.from_json(wrapper["request"])
        lineage_id = str(wrapper.get("lineage_id") or "")
        if (
            not lineage_id
            or wrapper.get("request_id") != request.request_id
            or not required_refs <= set(request.evidence_refs)
        ):
            raise ValueError("next representation wrapper lacks causal binding")
        workbench = _workbench_receipt_for_request(
            navigation, lineage_id=lineage_id, request=request
        )
        selected_request_ids.append(request.request_id)
        selected_lineage_ids.append(lineage_id)
        workbench_refs.append(str(workbench["receipt_id"]))
    if not selected_request_ids:
        raise ValueError("next representation has no campaign-authored request")

    core = {
        "schema": REVIEWED_FAMILY_NEXT_REPRESENTATION_AUTHORSHIP_SCHEMA,
        "source_observation_sha256": str(observation["receipt_sha256"]),
        "family_execution_sha256": str(
            observation["finite_family_execution_sha256"]
        ),
        "feedback_receipt_sha256": str(feedback["receipt_sha256"]),
        "feedback_wave_binding_sha256": str(
            feedback_wave_binding["receipt_sha256"]
        ),
        "next_run_digest": str(next_run["run_digest"]),
        "next_lineage_synthesis_input_sha256": str(
            synthesis_input["input_sha256"]
        ),
        "next_lineage_synthesis_decision_sha256": str(
            replayed["receipt_sha256"]
        ),
        "selected_request_ids": selected_request_ids,
        "selected_lineage_ids": selected_lineage_ids,
        "workbench_receipt_ids": workbench_refs,
        "active_next_representation": active_request.to_json(),
        "active_next_representation_request_id": active_request.request_id,
        "authority": "campaign_navigation_leaf_post_outcome_workbench_request",
    }
    return (
        {**core, "receipt_sha256": content_hash(core)},
        active_request,
        replayed,
    )


def build_reviewed_family_exhaustion_discharge(
    *,
    observation: Mapping[str, Any],
    feedback: Mapping[str, Any],
    feedback_wave_binding: Mapping[str, Any],
    next_representation_run: Mapping[str, Any],
) -> dict[str, Any]:
    """Join one family-scoped null to its post-outcome typed successor."""

    observed = validate_reviewed_family_exhaustion_observation(observation)
    frozen_feedback = _feedback(feedback, observed)
    wave = _feedback_wave_binding(
        feedback_wave_binding, feedback=frozen_feedback, observation=observed
    )
    next_run = _run(
        next_representation_run, context="next representation run"
    )
    if (
        next_run.get("status") != "frontier_language_expansion_requested"
        or next_run.get("context_hash")
        != observed["source_family_run"]["context_hash"]
        or frozen_feedback
        not in list(next_run["navigation"].get("objective_review_history") or ())
        or int(next_run["navigation"].get("search_wave", 0))
        < int(wave["search_wave"])
    ):
        raise ValueError("post-outcome navigation does not consume family feedback")
    authorship, active_next, next_synthesis = _next_representation_authorship(
        observation=observed,
        feedback=frozen_feedback,
        feedback_wave_binding=wave,
        next_run=next_run,
    )
    core = {
        "schema": REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA,
        "observation": observed,
        "observation_sha256": str(observed["receipt_sha256"]),
        "feedback": frozen_feedback,
        "feedback_sha256": str(frozen_feedback["receipt_sha256"]),
        "feedback_wave_binding": wave,
        "feedback_wave_binding_sha256": str(wave["receipt_sha256"]),
        "next_representation_run": next_run,
        "next_representation_run_digest": str(next_run["run_digest"]),
        "next_representation_authorship": authorship,
        "next_representation_authorship_sha256": str(authorship["receipt_sha256"]),
        "next_representation_request": active_next.to_json(),
        "next_representation_request_id": active_next.request_id,
        "next_lineage_synthesis_decision_sha256": str(
            next_synthesis["receipt_sha256"]
        ),
        "objective_status": (
            "discharged_by_reviewed_family_exhaustion_with_typed_successor"
        ),
        "claim_scope": _DISCHARGE_CLAIM_SCOPE,
        "ambient_nonexistence_authority": False,
        "kernel_ratification_authority": False,
        "novelty_authority": False,
        "authority": "reviewed_family_exhaustion_content_bound_terminal_transition",
    }
    return validate_reviewed_family_exhaustion_discharge(
        {**core, "receipt_sha256": content_hash(core)}
    )


def validate_reviewed_family_exhaustion_discharge(
    value: Mapping[str, Any],
    *,
    current_blueprint: FrontierTheoryBlueprint | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = _json_data(value, context="reviewed family exhaustion discharge")
    required = {
        "schema", "observation", "observation_sha256", "feedback",
        "feedback_sha256", "feedback_wave_binding",
        "feedback_wave_binding_sha256", "next_representation_run",
        "next_representation_run_digest", "next_representation_authorship",
        "next_representation_authorship_sha256", "next_representation_request",
        "next_representation_request_id",
        "next_lineage_synthesis_decision_sha256", "objective_status",
        "claim_scope", "ambient_nonexistence_authority",
        "kernel_ratification_authority", "novelty_authority", "authority",
    }
    if not isinstance(row, dict) or set(row) != required | {"receipt_sha256"}:
        raise ValueError("reviewed family exhaustion discharge fields changed")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("objective_status")
        != "discharged_by_reviewed_family_exhaustion_with_typed_successor"
        or row.get("claim_scope") != _DISCHARGE_CLAIM_SCOPE
        or row.get("ambient_nonexistence_authority") is not False
        or row.get("kernel_ratification_authority") is not False
        or row.get("novelty_authority") is not False
        or row.get("authority")
        != "reviewed_family_exhaustion_content_bound_terminal_transition"
    ):
        raise ValueError("reviewed family exhaustion discharge digest mismatch")
    observation = validate_reviewed_family_exhaustion_observation(
        row["observation"], current_blueprint=current_blueprint
    )
    feedback = _feedback(row["feedback"], observation)
    wave = _feedback_wave_binding(
        row["feedback_wave_binding"],
        feedback=feedback,
        observation=observation,
    )
    next_run = _run(
        row["next_representation_run"], context="next representation run"
    )
    authorship, active_next, next_synthesis = _next_representation_authorship(
        observation=observation,
        feedback=feedback,
        feedback_wave_binding=wave,
        next_run=next_run,
    )
    if (
        row["observation_sha256"] != observation["receipt_sha256"]
        or row["feedback_sha256"] != feedback["receipt_sha256"]
        or row["feedback_wave_binding_sha256"] != wave["receipt_sha256"]
        or row["next_representation_run_digest"] != next_run["run_digest"]
        or row["next_representation_authorship"] != authorship
        or row["next_representation_authorship_sha256"]
        != authorship["receipt_sha256"]
        or row["next_representation_request"] != active_next.to_json()
        or row["next_representation_request_id"] != active_next.request_id
        or row["next_lineage_synthesis_decision_sha256"]
        != next_synthesis["receipt_sha256"]
        or next_run.get("status") != "frontier_language_expansion_requested"
        or next_run.get("context_hash")
        != observation["source_family_run"]["context_hash"]
        or feedback
        not in list(next_run["navigation"].get("objective_review_history") or ())
        or int(next_run["navigation"].get("search_wave", 0))
        < int(wave["search_wave"])
    ):
        raise ValueError("reviewed family exhaustion transition no longer replays")
    return row


__all__ = [
    "REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA",
    "REVIEWED_FAMILY_EXHAUSTION_OBSERVATION_SCHEMA",
    "REVIEWED_FAMILY_NEXT_REPRESENTATION_AUTHORSHIP_SCHEMA",
    "build_reviewed_family_exhaustion_discharge",
    "build_reviewed_family_exhaustion_observation",
    "reviewed_family_exhaustion_stop_permission",
    "validate_reviewed_family_execution_join",
    "validate_reviewed_family_exhaustion_discharge",
    "validate_reviewed_family_exhaustion_observation",
]
