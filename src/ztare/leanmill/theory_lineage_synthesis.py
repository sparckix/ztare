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

CONTINUATION_MODES = frozenset(
    {"current_context", "formula_coordinate", "theory_language", "none"}
)


def lineage_request_matches_context(
    row: Mapping[str, Any],
    *,
    context_hash: str,
    context_epoch: int,
) -> bool:
    """Whether a frozen formula/language request belongs to this context."""

    payload = row.get("request")
    if not isinstance(payload, Mapping):
        payload = row.get("proposal")
    if not isinstance(payload, Mapping):
        payload = row
    return bool(
        str(payload.get("source_context_hash") or "") == context_hash
        and type(payload.get("source_epoch")) is int
        and int(payload["source_epoch"]) == context_epoch
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
            "continuation_mode",
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
            "continuation_mode": {"enum": sorted(CONTINUATION_MODES)},
            "selected_request_ids": string_array,
            "deferred_request_ids": string_array,
            "rationale": {"type": "string", "minLength": 1},
            "next_discriminator": {"type": "string", "minLength": 1},
            "kill_condition": {"type": "string", "minLength": 1},
            "program_ids": string_array,
            "next_discriminator_request_ids": string_array,
        },
    }


def build_theory_move_portfolio(
    navigation: Mapping[str, Any],
    *,
    objective_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Quote the next lawful move families without choosing one for the leaf.

    The portfolio composes two measurements already owned elsewhere: residual
    information coordinates on frozen programs and semantic-image growth across
    search waves.  It deliberately emits no scalar winner.  Unknown future
    representations have option value but no defensible point estimate.
    """

    context_hash = str(navigation.get("context_hash") or "")
    epoch = int(navigation.get("context_epoch", 0))
    wave = navigation.get("search_wave_image_receipt")
    if isinstance(wave, Mapping):
        wave_core = {key: value for key, value in wave.items() if key != "receipt_sha256"}
        if (
            wave.get("receipt_sha256") != content_hash(wave_core)
            or str(wave.get("context_hash") or "") != context_hash
            or int(wave.get("context_epoch", -1)) != epoch
        ):
            raise ValueError("search-wave image does not bind the synthesis context")
        growth_kind = str(wave.get("growth_kind") or "unknown")
        new_raw_count = int(wave.get("new_raw_count", 0))
        new_image_count = int(wave.get("new_image_count", 0))
    else:
        growth_kind = "unknown"
        new_raw_count = new_image_count = 0

    programs = [
        row for row in navigation.get("finalists") or ()
        if isinstance(row, Mapping) and isinstance(row.get("theory_program"), Mapping)
    ]
    reviewed_targets = {
        str(outcome.get("target_formula_id") or "")
        for row in programs
        for outcome in (row.get("objective_feedback") or {}).get(
            "prediction_outcomes", ()
        )
        if isinstance(outcome, Mapping)
    }
    predictions = [
        prediction
        for row in programs
        for prediction in (row.get("prediction_profile") or {}).get("predictions") or ()
        if isinstance(prediction, Mapping)
    ]
    unresolved = sum(
        str(row.get("chart_status") or "")
        in {"holds_on_complete_context", "holds_on_observed_context"}
        and str(row.get("formula_id") or "") not in reviewed_targets
        for row in predictions
    )
    residual_prices = [
        float((row.get("residual_information_yield") or {}).get("information_per_cost", 0.0))
        for row in programs
        if isinstance(row.get("residual_information_yield"), Mapping)
    ]
    formula_requests = len(navigation.get("expansion_proposals") or ())
    language_requests = len(navigation.get("theory_language_expansion_requests") or ())
    objective_available = isinstance(objective_contract, Mapping)

    def option(
        route: str,
        continuation_mode: str,
        *,
        available: bool,
        evidence_relation: str,
        phases: tuple[str, ...],
        owed_consequence: str,
        reversibility: str,
    ) -> dict[str, Any]:
        return {
            "route": route,
            "continuation_mode": continuation_mode,
            "availability": "available" if available else "blocked_precondition",
            "evidence_relation": evidence_relation,
            "cost_quote": {
                "required_phases": list(phases),
                "exact_units": "campaign_ledger_at_admission",
            },
            "owed_consequence": owed_consequence,
            "reversibility": reversibility,
        }

    options = [
        option(
            "continue_search",
            "current_context",
            available=objective_available,
            evidence_relation=(
                f"wave_growth={growth_kind};new_raw={new_raw_count};"
                f"new_semantic_images={new_image_count}"
            ),
            phases=("navigation",),
            owed_consequence="leanmill.theory_search_wave_image.v1",
            reversibility="new_wave_same_context",
        ),
        option(
            "continue_search",
            "formula_coordinate",
            available=objective_available,
            evidence_relation=(
                f"wave_growth={growth_kind};frozen_formula_requests={formula_requests}"
            ),
            phases=("navigation", "context"),
            owed_consequence="leanmill.frontier_formula_admission.v1_or_rejection",
            reversibility="immutable_successor_context",
        ),
        option(
            "continue_search",
            "theory_language",
            available=objective_available,
            evidence_relation=(
                f"wave_growth={growth_kind};frozen_language_requests={language_requests}"
            ),
            phases=("navigation", "expansion"),
            owed_consequence="typed_language_request_or_adapter_gap",
            reversibility="proposal_only_until_reviewed_successor",
        ),
        option(
            "admit_formulas",
            "none",
            available=formula_requests > 0,
            evidence_relation=f"frozen_formula_requests={formula_requests}",
            phases=("context",),
            owed_consequence="leanmill.frontier_formula_admission.v1_or_rejection",
            reversibility="immutable_successor_context",
        ),
        option(
            "escalate_language",
            "none",
            available=language_requests > 0,
            evidence_relation=f"frozen_language_requests={language_requests}",
            phases=("expansion",),
            owed_consequence="typed_adapter_gap_or_reviewed_successor",
            reversibility="proposal_only_until_reviewed_successor",
        ),
        option(
            "proceed_boundary",
            "none",
            available=objective_available and unresolved > 0,
            evidence_relation=(
                f"unresolved_predictions={unresolved};"
                f"max_residual_information_per_cost={max(residual_prices, default=0.0):.8f}"
            ),
            phases=("boundary",),
            owed_consequence="countermodel_proof_or_unresolved_boundary_receipt",
            reversibility="evidence_append_only",
        ),
        option(
            "defer_all",
            "none",
            available=True,
            evidence_relation=(
                f"wave_growth={growth_kind};unresolved_predictions={unresolved}"
            ),
            phases=(),
            owed_consequence="terminal_unresolved_disposition",
            reversibility="resumable_with_explicit_budget_or_new_evidence",
        ),
    ]
    core = {
        "schema": "leanmill.adaptive_theory_move_portfolio.v1",
        "context_hash": context_hash,
        "context_epoch": epoch,
        "quality_diversity_state": {
            "growth_kind": growth_kind,
            "new_raw_count": new_raw_count,
            "new_semantic_image_count": new_image_count,
        },
        "residual_state": {
            "frozen_program_count": len(programs),
            "unresolved_prediction_count": unresolved,
            "max_information_per_cost": max(residual_prices, default=0.0),
        },
        "options": options,
        "authority": "diagnostic_affordance_only",
        "claim_boundary": (
            "the host quotes measured coordinates, resource classes, and owed receipts; "
            "the synthesis leaf chooses the move and may value unpriced option creation"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


def theory_move_consequence_receipt(
    navigation: Mapping[str, Any],
    source_synthesis: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a prior continuation choice to the first resulting search wave."""

    source_core = {
        key: value for key, value in source_synthesis.items() if key != "receipt_sha256"
    }
    if (
        source_synthesis.get("schema") != "leanmill.lineage_synthesis_decision.v1"
        or source_synthesis.get("receipt_sha256") != content_hash(source_core)
        or source_synthesis.get("route") != "continue_search"
    ):
        raise ValueError("adaptive move consequence requires a valid continuation receipt")
    planned = str(source_synthesis.get("continuation_mode") or "")
    if planned not in CONTINUATION_MODES - {"none"}:
        raise ValueError("adaptive move consequence lacks a typed continuation mode")

    observed: set[str] = set()
    evidence_refs: list[str] = []
    formula_requests = navigation.get("expansion_proposals") or ()
    language_requests = navigation.get("theory_language_expansion_requests") or ()
    if formula_requests:
        observed.add("formula_coordinate")
        evidence_refs.extend(
            str(row.get("request_id") or "")
            for row in formula_requests
            if isinstance(row, Mapping)
        )
    if language_requests:
        observed.add("theory_language")
        evidence_refs.extend(
            str(row.get("request_id") or "")
            for row in language_requests
            if isinstance(row, Mapping)
        )
    for lineage in navigation.get("lineages") or ():
        lineage_navigation = (
            lineage.get("navigation") if isinstance(lineage, Mapping) else None
        )
        if not isinstance(lineage_navigation, Mapping):
            continue
        for turn in lineage_navigation.get("trace") or ():
            if not isinstance(turn, Mapping):
                continue
            receipt = turn.get("receipt")
            if isinstance(receipt, Mapping):
                receipt_ref = str(
                    receipt.get("receipt_id")
                    or receipt.get("receipt_sha256")
                    or ""
                )
                if receipt_ref:
                    evidence_refs.append(receipt_ref)
            if turn.get("decision") == "request":
                capability = str(turn.get("capability_id") or "")
                if capability == "propose_frontier_formula":
                    observed.add("formula_coordinate")
                elif capability == "propose_theory_language_expansion":
                    observed.add("theory_language")
                else:
                    observed.add("current_context")
    if navigation.get("finalists") or (
        not observed
        and int(
            navigation.get("wave_provider_calls", navigation.get("provider_calls", 0))
        )
        > 0
    ):
        observed.add("current_context")
    wave = navigation.get("search_wave_image_receipt")
    if isinstance(wave, Mapping) and wave.get("receipt_sha256"):
        evidence_refs.append(str(wave["receipt_sha256"]))

    status = (
        "no_consuming_action"
        if not observed
        else "diversified"
        if len(observed) > 1
        else "executed_as_planned"
        if planned in observed
        else "leaf_revised_move"
    )
    core = {
        "schema": "leanmill.adaptive_theory_move_consequence.v1",
        "context_hash": str(navigation.get("context_hash") or ""),
        "context_epoch": int(navigation.get("context_epoch", 0)),
        "search_wave": int(navigation.get("search_wave", 0)),
        "source_synthesis_receipt_sha256": str(
            source_synthesis.get("receipt_sha256") or ""
        ),
        "move_portfolio_receipt_sha256": str(
            source_synthesis.get("move_portfolio_receipt_sha256") or ""
        ),
        "planned_continuation_mode": planned,
        "observed_move_modes": sorted(observed),
        "status": status,
        "evidence_refs": [row for row in dict.fromkeys(evidence_refs) if row],
        "authority": "host_observation_only",
        "claim_boundary": (
            "records first-fire or leaf revision; it does not judge the mathematical choice"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


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
    context_hash = str(navigation.get("context_hash") or "")
    context_epoch = int(navigation.get("context_epoch", 0))
    archived_stale_request_ids: list[str] = []
    formulas = []
    for raw in navigation.get("expansion_proposals") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("lineage formula request is malformed")
        row = dict(raw)
        expected = formula_lineage_request_id(row)
        supplied = row.get("request_id")
        if supplied is not None and supplied != expected:
            raise ValueError("lineage formula request identity changed")
        if not lineage_request_matches_context(
            row, context_hash=context_hash, context_epoch=context_epoch
        ):
            archived_stale_request_ids.append(expected)
            continue
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
        request_id = str(request["request_id"])
        if not lineage_request_matches_context(
            row, context_hash=context_hash, context_epoch=context_epoch
        ):
            archived_stale_request_ids.append(request_id)
            continue
        languages.append({**row, "request_id": request_id})
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
                "objective_feedback": dict(row.get("objective_feedback") or {}),
            }
        )
    review_history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    boundary_feedback = [
        dict(row["objective_feedback"])
        for row in navigation.get("finalists") or ()
        if isinstance(row, Mapping)
        and isinstance(row.get("objective_feedback"), Mapping)
        and row.get("objective_feedback")
    ]
    boundary_feedback.extend(
        row
        for row in review_history
        if row.get("schema") == "leanmill.boundary_search_feedback.v1"
    )
    boundary_feedback = list({
        str(row.get("receipt_sha256") or content_hash(row)): row
        for row in boundary_feedback
    }.values())
    core = {
        "schema": "leanmill.lineage_synthesis_input.v1",
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "formula_requests": formulas,
        "theory_language_requests": languages,
        "archived_stale_request_ids": sorted(set(archived_stale_request_ids)),
        "frozen_programs": programs,
        "objective_review_history": review_history,
        "objective_contract": (
            dict(objective_contract) if objective_contract is not None else None
        ),
        "boundary_stage": {
            "status": (
                "completed_evidence_attached"
                if boundary_feedback
                else "not_yet_run"
            ),
            "admission_semantics": "authorizes_discriminating_tests_not_outer_success",
            "capabilities": [
                "larger_carrier_countermodel_search",
                "formal_verification",
                "post_freeze_literature_review",
            ],
            "feedback_receipt_sha256s": [
                str(row.get("receipt_sha256") or "")
                for row in boundary_feedback
                if row.get("receipt_sha256")
            ],
        },
        "host_isolated_program_comparisons": list(
            navigation.get("host_isolated_program_comparisons")
            or navigation.get("independent_program_comparisons")
            or ()
        ),
        "isolation_receipt": dict(navigation.get("isolation_receipt") or {}),
        "search_wave_image_receipt": dict(
            navigation.get("search_wave_image_receipt") or {}
        ),
        "visibility": "post_lineage_freeze_anonymous_only",
    }
    post_freeze_disposition = navigation.get("post_freeze_research_disposition")
    if isinstance(post_freeze_disposition, Mapping):
        disposition_core = {
            key: value
            for key, value in post_freeze_disposition.items()
            if key != "receipt_sha256"
        }
        if (
            post_freeze_disposition.get("schema")
            != "leanmill.post_freeze_research_disposition.v1"
            or post_freeze_disposition.get("receipt_sha256")
            != content_hash(disposition_core)
            or str(post_freeze_disposition.get("context_hash") or "")
            != core["context_hash"]
        ):
            raise ValueError(
                "post-freeze research disposition does not bind the synthesis input"
            )
        core["post_freeze_research_disposition"] = dict(
            post_freeze_disposition
        )
    portfolio = navigation.get("adaptive_move_portfolio")
    if isinstance(portfolio, Mapping):
        portfolio_core = {
            key: value for key, value in portfolio.items() if key != "receipt_sha256"
        }
        if (
            portfolio.get("receipt_sha256") != content_hash(portfolio_core)
            or str(portfolio.get("context_hash") or "") != core["context_hash"]
            or int(portfolio.get("context_epoch", -1)) != core["context_epoch"]
        ):
            raise ValueError("adaptive move portfolio does not bind the synthesis input")
        core["adaptive_move_portfolio"] = dict(portfolio)
    return {**core, "input_sha256": content_hash(core)}


def validate_lineage_synthesis_decision(
    synthesis_input: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    legacy_fields = {
        "route",
        "selected_request_ids",
        "deferred_request_ids",
        "rationale",
        "next_discriminator",
        "kill_condition",
        "program_ids",
        "next_discriminator_request_ids",
    }
    expected_fields = legacy_fields | {"continuation_mode"}
    portfolio = synthesis_input.get("adaptive_move_portfolio")
    has_portfolio = isinstance(portfolio, Mapping)
    if set(decision) not in (legacy_fields, expected_fields):
        raise ValueError("lineage synthesis fields do not match the contract")
    if has_portfolio and set(decision) != expected_fields:
        raise ValueError("adaptive synthesis requires continuation_mode")
    route = str(decision.get("route") or "")
    if route not in LINEAGE_SYNTHESIS_ROUTES:
        raise ValueError("unsupported lineage synthesis route")
    continuation_supplied = "continuation_mode" in decision
    continuation_mode = str(decision.get("continuation_mode") or "none")
    if continuation_supplied and continuation_mode not in CONTINUATION_MODES:
        raise ValueError("unsupported continuation mode")
    if continuation_supplied and (
        (route == "continue_search" and continuation_mode == "none")
        or (route != "continue_search" and continuation_mode != "none")
    ):
        raise ValueError("continuation mode does not match the synthesis route")
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
    if continuation_supplied and isinstance(portfolio, Mapping):
        matching = [
            dict(row)
            for row in portfolio.get("options") or ()
            if isinstance(row, Mapping)
            and row.get("route") == route
            and row.get("continuation_mode") == continuation_mode
        ]
        if len(matching) != 1 or matching[0].get("availability") != "available":
            raise ValueError("selected adaptive move is not an available affordance")
        core.update(
            {
                "continuation_mode": continuation_mode,
                "selected_move_affordance": matching[0],
                "move_portfolio_receipt_sha256": str(
                    portfolio.get("receipt_sha256") or ""
                ),
            }
        )
    elif continuation_supplied:
        # Compatibility for direct/in-process navigators that do not use the
        # adaptive portfolio producer. Subscription synthesis always receives
        # the portfolio and therefore takes the validated branch above.
        core["continuation_mode"] = continuation_mode
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "LINEAGE_SYNTHESIS_ROUTES",
    "CONTINUATION_MODES",
    "build_theory_move_portfolio",
    "theory_move_consequence_receipt",
    "formula_lineage_request_id",
    "lineage_synthesis_input",
    "lineage_synthesis_output_schema",
    "validate_lineage_synthesis_decision",
]
