"""Late, agent-chosen synthesis over frozen host-isolated lineage requests."""
from __future__ import annotations

from typing import Any, Mapping

from ztare.leanmill.theory_ir import content_hash


LINEAGE_SYNTHESIS_ROUTES = frozenset(
    {
        "admit_formulas",
        "escalate_language",
        "defer_all",
        "proceed_boundary",
        "continue_search",
    }
)


def lineage_synthesis_output_schema() -> dict[str, Any]:
    string_array = {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "route",
            "selected_request_ids",
            "deferred_request_ids",
            "rationale",
            "next_discriminator",
            "kill_condition",
            "program_ids",
            "next_discriminator_request_ids",
        ],
        "properties": {
            "route": {"enum": sorted(LINEAGE_SYNTHESIS_ROUTES)},
            "selected_request_ids": string_array,
            "deferred_request_ids": string_array,
            "rationale": {"type": "string", "minLength": 1},
            "next_discriminator": {"type": "string", "minLength": 1},
            "kill_condition": {"type": "string", "minLength": 1},
            "program_ids": string_array,
            "next_discriminator_request_ids": string_array,
        },
    }


def formula_lineage_request_id(row: Mapping[str, Any]) -> str:
    return "lineage-formula-request:" + content_hash(
        {
            "lineage_id": str(row.get("lineage_id") or ""),
            "proposal": dict(row.get("proposal") or {}),
        }
    )


def lineage_synthesis_input(
    navigation: Mapping[str, Any],
    *,
    objective_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    formulas = []
    for raw in navigation.get("expansion_proposals") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("lineage formula request is malformed")
        row = dict(raw)
        expected = formula_lineage_request_id(row)
        supplied = row.get("request_id")
        if supplied is not None and supplied != expected:
            raise ValueError("lineage formula request identity changed")
        formulas.append({**row, "request_id": expected})
    languages = []
    for raw in navigation.get("theory_language_expansion_requests") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("lineage language request is malformed")
        row = dict(raw)
        request = row.get("request")
        if not isinstance(request, Mapping) or not request.get("request_id"):
            raise ValueError("lineage language request lacks frozen identity")
        supplied = row.get("request_id")
        if supplied is not None and supplied != request["request_id"]:
            raise ValueError("lineage language request identity changed")
        languages.append({**row, "request_id": str(request["request_id"])})
    if not formulas and not languages and objective_contract is None:
        raise ValueError("lineage synthesis requires at least one frozen request")
    programs = []
    for row in navigation.get("finalists") or ():
        if not isinstance(row, Mapping) or not isinstance(
            row.get("theory_program"), Mapping
        ):
            continue
        program = dict(row["theory_program"])
        programs.append(
            {
                **program,
                "prediction_profile": dict(row.get("prediction_profile") or {}),
                "residual_information_yield": dict(
                    row.get("residual_information_yield") or {}
                ),
                "structural_baseline": row.get("structural_baseline"),
                "navigator_rationale": str(row.get("navigator_rationale") or ""),
            }
        )
    core = {
        "schema": "leanmill.lineage_synthesis_input.v1",
        "context_hash": str(navigation.get("context_hash") or ""),
        "context_epoch": int(navigation.get("context_epoch", 0)),
        "formula_requests": formulas,
        "theory_language_requests": languages,
        "frozen_programs": programs,
        "objective_contract": (
            dict(objective_contract) if objective_contract is not None else None
        ),
        "host_isolated_program_comparisons": list(
            navigation.get("host_isolated_program_comparisons")
            or navigation.get("independent_program_comparisons")
            or ()
        ),
        "isolation_receipt": dict(navigation.get("isolation_receipt") or {}),
        "visibility": "post_lineage_freeze_anonymous_only",
    }
    return {**core, "input_sha256": content_hash(core)}


def validate_lineage_synthesis_decision(
    synthesis_input: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "route",
        "selected_request_ids",
        "deferred_request_ids",
        "rationale",
        "next_discriminator",
        "kill_condition",
        "program_ids",
        "next_discriminator_request_ids",
    }
    if set(decision) != expected_fields:
        raise ValueError("lineage synthesis fields do not match the contract")
    route = str(decision.get("route") or "")
    if route not in LINEAGE_SYNTHESIS_ROUTES:
        raise ValueError("unsupported lineage synthesis route")
    selected = tuple(str(row) for row in decision.get("selected_request_ids") or ())
    deferred = tuple(str(row) for row in decision.get("deferred_request_ids") or ())
    program_ids = tuple(str(row) for row in decision.get("program_ids") or ())
    discriminator_request_ids = tuple(
        str(row) for row in decision.get("next_discriminator_request_ids") or ()
    )
    if len(set(selected)) != len(selected) or len(set(deferred)) != len(deferred):
        raise ValueError("lineage synthesis request IDs must be unique")
    formula_ids = {
        str(row["request_id"])
        for row in synthesis_input.get("formula_requests") or ()
        if isinstance(row, Mapping)
    }
    language_ids = {
        str(row["request_id"])
        for row in synthesis_input.get("theory_language_requests") or ()
        if isinstance(row, Mapping)
    }
    available = formula_ids | language_ids
    if (
        len(set(discriminator_request_ids)) != len(discriminator_request_ids)
        or not set(discriminator_request_ids) <= available
    ):
        raise ValueError("next discriminator references unknown frozen requests")
    if set(selected) & set(deferred) or set(selected) | set(deferred) != available:
        raise ValueError("lineage synthesis must partition every frozen request")
    if route == "admit_formulas" and (not selected or not set(selected) <= formula_ids):
        raise ValueError("formula synthesis may select only formula requests")
    if route == "escalate_language" and (
        not selected or not set(selected) <= language_ids
    ):
        raise ValueError("language synthesis may select only language requests")
    if route == "defer_all" and selected:
        raise ValueError("defer_all cannot select a request")
    if route in {"admit_formulas", "escalate_language"}:
        if set(discriminator_request_ids) != set(selected):
            raise ValueError(
                "request-consuming discriminator must bind every selected request"
            )
    elif discriminator_request_ids:
        raise ValueError(
            "unchanged-context or boundary routes cannot consume deferred requests"
        )
    objective = synthesis_input.get("objective_contract")
    available_program_ids = {
        str(row.get("program_id") or "")
        for row in synthesis_input.get("frozen_programs") or ()
        if isinstance(row, Mapping) and row.get("program_id")
    }
    if len(set(program_ids)) != len(program_ids) or not set(program_ids) <= available_program_ids:
        raise ValueError("lineage synthesis references unknown theory programs")
    if route in {"proceed_boundary", "continue_search"}:
        if not isinstance(objective, Mapping):
            raise ValueError("objective routes require a frozen objective contract")
        if selected or set(deferred) != available:
            raise ValueError("objective review must defer every language request")
        if route == "proceed_boundary" and not program_ids:
            raise ValueError("objective review must bind at least one frozen program")
        if route == "proceed_boundary":
            bound_programs = [
                row
                for row in synthesis_input.get("frozen_programs") or ()
                if isinstance(row, Mapping)
                and str(row.get("program_id") or "") in set(program_ids)
            ]
            predictions = [
                prediction
                for row in bound_programs
                for prediction in (
                    (row.get("prediction_profile") or {}).get("predictions") or ()
                )
                if isinstance(prediction, Mapping)
            ]
            if not predictions or all(
                row.get("chart_status") == "refuted_in_context"
                for row in predictions
            ):
                raise ValueError(
                    "boundary route requires a prediction unresolved by the seed context"
                )
        if route == "continue_search" and available_program_ids and not program_ids:
            raise ValueError("objective review must bind the programs it rejects")
    elif program_ids:
        raise ValueError("request synthesis cannot claim objective program evidence")
    for name in ("rationale", "next_discriminator", "kill_condition"):
        if not str(decision.get(name) or "").strip():
            raise ValueError(f"lineage synthesis requires {name}")
    selected_rows = [
        dict(row)
        for group in (
            synthesis_input.get("formula_requests") or (),
            synthesis_input.get("theory_language_requests") or (),
        )
        for row in group
        if isinstance(row, Mapping) and row.get("request_id") in set(selected)
    ]
    core = {
        "schema": "leanmill.lineage_synthesis_decision.v1",
        "input_sha256": str(synthesis_input.get("input_sha256") or ""),
        "context_hash": str(synthesis_input.get("context_hash") or ""),
        "context_epoch": int(synthesis_input.get("context_epoch", 0)),
        "route": route,
        "selected_request_ids": list(selected),
        "deferred_request_ids": list(deferred),
        "selected_requests": selected_rows,
        "program_ids": list(program_ids),
        "next_discriminator_request_ids": list(discriminator_request_ids),
        "objective_contract": dict(objective) if isinstance(objective, Mapping) else None,
        "rationale": str(decision["rationale"]),
        "next_discriminator": str(decision["next_discriminator"]),
        "kill_condition": str(decision["kill_condition"]),
        "authority": "agent_choice_host_validated",
        "claim_boundary": (
            "selection among frozen anonymous requests only; admission and "
            "successor-language review remain host-owned"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "LINEAGE_SYNTHESIS_ROUTES",
    "formula_lineage_request_id",
    "lineage_synthesis_input",
    "lineage_synthesis_output_schema",
    "validate_lineage_synthesis_decision",
]
