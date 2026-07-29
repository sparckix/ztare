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


def _registered_boundary_task_sha256s(
    program: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return unconsumed task identities with an executable frontier consumer."""

    from ztare.common.task_discharge import TaskDischargeContract
    from ztare.leanmill.theory_task_boundary_registry import (
        registered_theory_task_boundary_handler,
    )

    program_row = program.get("theory_program")
    frozen_program = (
        program_row if isinstance(program_row, Mapping) else program
    )
    program_id = str(frozen_program.get("program_id") or "")
    feedback = program.get("objective_feedback")
    disposed_contract_sha256s: set[str] = set()
    disposed_contract_ids: set[str] = set()
    if isinstance(feedback, Mapping):
        if feedback.get("schema") == "leanmill.boundary_search_feedback.v1":
            discharge = feedback.get("theory_task_discharge")
            for row in (
                discharge.get("rows")
                if isinstance(discharge, Mapping)
                else ()
            ) or ():
                receipt = row.get("receipt") if isinstance(row, Mapping) else None
                observed = (
                    receipt.get("observed")
                    if isinstance(receipt, Mapping)
                    else None
                )
                if (
                    isinstance(row, Mapping)
                    and str(row.get("program_id") or "") == program_id
                    and isinstance(observed, Mapping)
                    and observed.get("boundary_status")
                    in {"witness_rejected", "witness_verified"}
                ):
                    disposed_contract_sha256s.add(
                        str(row.get("contract_sha256") or "")
                    )
        elif (
            feedback.get("schema")
            == "leanmill.recovered_boundary_artifact_feedback.v1"
            and feedback.get("status")
            in {"witness_rejected", "witness_verified"}
        ):
            disposed_contract_ids.add(str(feedback.get("contract_id") or ""))

    raw_tasks = frozen_program.get("task_discharge_contracts") or ()
    if not isinstance(raw_tasks, (list, tuple)):
        raise ValueError("frozen theory-program tasks must be an array")
    task_sha256s: list[str] = []
    for raw in raw_tasks:
        if not isinstance(raw, Mapping):
            raise ValueError("frozen theory-program task is malformed")
        contract = TaskDischargeContract.from_dict(raw)
        if (
            contract.sha256 not in disposed_contract_sha256s
            and contract.contract_id not in disposed_contract_ids
            and registered_theory_task_boundary_handler(contract.adjudicator_id)
            is not None
        ):
            task_sha256s.append(contract.sha256)
    return tuple(task_sha256s)


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
        and str(row.get("prediction_formula_id") or "") not in reviewed_targets
        for row in predictions
    )
    registered_boundary_tasks = {
        task_sha256
        for row in programs
        for task_sha256 in _registered_boundary_task_sha256s(
            row
        )
    }
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
            available=objective_available and growth_kind != "alpha_blind",
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
            available=objective_available and growth_kind != "alpha_blind",
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
            available=formula_requests > 0 and growth_kind != "alpha_blind",
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
            available=objective_available
            and (unresolved > 0 or bool(registered_boundary_tasks)),
            evidence_relation=(
                f"unresolved_predictions={unresolved};"
                f"registered_boundary_tasks={len(registered_boundary_tasks)};"
                f"max_residual_information_per_cost={max(residual_prices, default=0.0):.8f}"
            ),
            phases=("boundary",),
            owed_consequence=(
                "countermodel_proof_or_task_discharge_or_unresolved_boundary_receipt"
            ),
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
            "registered_boundary_task_count": len(registered_boundary_tasks),
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


def compose_selected_language_expansion(
    synthesis: Mapping[str, Any],
) -> tuple[Any, dict[str, Any] | None]:
    """Project one successor request from an agent-selected compatible set.

    A context epoch admits one language-transition identity. The synthesizer
    may still select several independently authored requests when their
    conjunction is the experiment. This projection adds no mathematical
    choice: it retains source blind spots and interfaces in selection order,
    unions evidence, and uses the agent-authored discriminator and kill
    condition.
    """

    from ztare.leanmill.theory_language import (
        TheoryLanguageExpansionRequest,
        build_theory_language_expansion_request,
    )

    synthesis_core = {
        key: value for key, value in synthesis.items() if key != "receipt_sha256"
    }
    if (
        synthesis.get("schema") != "leanmill.lineage_synthesis_decision.v1"
        or synthesis.get("route") != "escalate_language"
        or synthesis.get("receipt_sha256") != content_hash(synthesis_core)
    ):
        raise ValueError("language composition requires a verified synthesis")
    selected_rows = list(synthesis.get("selected_requests") or ())
    if not selected_rows:
        raise ValueError("language synthesis selected no typed request")
    requests: list[TheoryLanguageExpansionRequest] = []
    request_ids: list[str] = []
    for row in selected_rows:
        if not isinstance(row, Mapping) or not isinstance(
            row.get("request"), Mapping
        ):
            raise ValueError("language synthesis selected a malformed request")
        request = TheoryLanguageExpansionRequest.from_json(row["request"])
        if str(row.get("request_id") or "") != request.request_id:
            raise ValueError("language synthesis request wrapper changed identity")
        requests.append(request)
        request_ids.append(request.request_id)
    if len(requests) == 1:
        return requests[0], None

    identity = {
        (request.source_context_hash, request.source_epoch, request.change_kind)
        for request in requests
    }
    if len(identity) != 1:
        raise ValueError(
            "multi-request language synthesis crosses successor identity"
        )
    context_hash, source_epoch, change_kind = next(iter(identity))
    composite = build_theory_language_expansion_request(
        source_context_hash=context_hash,
        source_epoch=source_epoch,
        change_kind=change_kind,
        blind_spot="\n\n".join(
            f"[{request.request_id}] {request.blind_spot}"
            for request in requests
        ),
        proposed_interface="\n\n".join(
            f"[{request.request_id}] {request.proposed_interface}"
            for request in requests
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                evidence
                for request in requests
                for evidence in request.evidence_refs
            )
        ),
        discriminating_test=str(synthesis.get("next_discriminator") or ""),
        kill_condition=str(synthesis.get("kill_condition") or ""),
    )
    receipt_core = {
        "schema": "leanmill.theory_language_request_composition.v1",
        "context_hash": context_hash,
        "context_epoch": source_epoch,
        "change_kind": change_kind,
        "source_synthesis_receipt_sha256": str(
            synthesis.get("receipt_sha256") or ""
        ),
        "source_request_ids": request_ids,
        "composite_request_id": composite.request_id,
        "composition_rule": "conjunctive_same_identity_v1",
        "authority": "deterministic_projection_of_agent_selection",
        "claim_boundary": (
            "composes selected requests without admitting the successor language"
        ),
    }
    receipt = {
        **receipt_core,
        "receipt_sha256": content_hash(receipt_core),
    }
    return composite, receipt


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


def _request_trace_evidence(
    navigation: Mapping[str, Any], evidence_refs: set[str]
) -> list[dict[str, Any]]:
    """Carry only content-verified trace receipts cited by frozen requests."""

    found: dict[str, dict[str, Any]] = {}
    traces = [navigation.get("trace") or ()]
    traces.extend(
        (lineage.get("navigation") or {}).get("trace") or ()
        for lineage in navigation.get("lineages") or ()
        if isinstance(lineage, Mapping)
    )
    for trace in traces:
        for event in trace:
            receipt = event.get("receipt") if isinstance(event, Mapping) else None
            if not isinstance(receipt, Mapping):
                continue
            receipt_id = str(receipt.get("receipt_id") or "")
            if receipt_id:
                core = {
                    key: value for key, value in receipt.items() if key != "receipt_id"
                }
                if receipt_id == "sha256:" + content_hash(core):
                    found[receipt_id] = dict(receipt)
            receipt_sha = str(receipt.get("receipt_sha256") or "")
            if receipt_sha:
                core = {
                    key: value
                    for key, value in receipt.items()
                    if key != "receipt_sha256"
                }
                if receipt_sha == content_hash(core):
                    found[receipt_sha] = dict(receipt)
    return [
        {"evidence_ref": ref, "receipt": found[ref]}
        for ref in sorted(evidence_refs & set(found))
    ]


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
    requested_evidence_refs = {
        str(evidence_ref)
        for row in (*formulas, *languages)
        for payload in (row.get("proposal"), row.get("request"))
        if isinstance(payload, Mapping)
        for evidence_ref in payload.get("evidence_refs") or ()
    }
    core = {
        "schema": "leanmill.lineage_synthesis_input.v1",
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "formula_requests": formulas,
        "theory_language_requests": languages,
        "archived_stale_request_ids": sorted(set(archived_stale_request_ids)),
        "frozen_programs": programs,
        "objective_review_history": review_history,
        "carried_evidence_receipts": _request_trace_evidence(
            navigation, requested_evidence_refs
        ),
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
    selected_registered_task_sha256s: tuple[str, ...] = ()
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
            selected_registered_task_sha256s = tuple(
                dict.fromkeys(
                    task_sha256
                    for row in bound_programs
                    for task_sha256 in _registered_boundary_task_sha256s(row)
                )
            )
            has_unresolved_prediction = bool(predictions) and any(
                row.get("chart_status") != "refuted_in_context"
                for row in predictions
            )
            if not has_unresolved_prediction and not selected_registered_task_sha256s:
                raise ValueError(
                    "boundary route requires a prediction unresolved by the seed "
                    "context or a registered task consumer"
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
        if len(matching) != 1:
            raise ValueError("selected adaptive move is not an available affordance")
        selected_affordance = matching[0]
        if selected_affordance.get("availability") != "available":
            if route != "proceed_boundary" or not selected_registered_task_sha256s:
                raise ValueError("selected adaptive move is not an available affordance")
            correction_core = {
                "schema": "leanmill.theory_move_affordance_correction.v1",
                "input_sha256": str(synthesis_input.get("input_sha256") or ""),
                "move_portfolio_receipt_sha256": str(
                    portfolio.get("receipt_sha256") or ""
                ),
                "program_ids": list(program_ids),
                "registered_task_sha256s": list(
                    selected_registered_task_sha256s
                ),
                "prior_availability": str(
                    selected_affordance.get("availability") or ""
                ),
                "corrected_availability": "available",
                "authority": "registered_task_consumer_replay",
            }
            correction = {
                **correction_core,
                "receipt_sha256": content_hash(correction_core),
            }
            selected_affordance = {
                **selected_affordance,
                "availability": "available",
                "evidence_relation": (
                    str(selected_affordance.get("evidence_relation") or "")
                    + ";registered_boundary_tasks="
                    + str(len(selected_registered_task_sha256s))
                ).lstrip(";"),
                "owed_consequence": (
                    "countermodel_proof_or_task_discharge_or_unresolved_boundary_receipt"
                ),
            }
            core["move_affordance_correction"] = correction
        core.update(
            {
                "continuation_mode": continuation_mode,
                "selected_move_affordance": selected_affordance,
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
    "compose_selected_language_expansion",
    "theory_move_consequence_receipt",
    "formula_lineage_request_id",
    "lineage_synthesis_input",
    "lineage_synthesis_output_schema",
    "validate_lineage_synthesis_decision",
]
