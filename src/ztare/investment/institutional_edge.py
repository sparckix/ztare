"""Compile the evidence state of JaggedThoughts' economic learning edges."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256


INSTITUTIONAL_EDGE_MAP_SCHEMA = "jaggedthoughts-institutional-edge-map-v2"


def _integer(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _edge(
    edge_id: str,
    label: str,
    question: str,
    *,
    status: str,
    issued: int,
    settled: int,
    independent_blocks: int,
    minimum_blocks: int,
    control_count: int | None,
    next_evidence: str,
    decision_use: str,
    reviewable: bool = False,
    source_refs: Sequence[str] = (),
    issued_unit: str = "issued",
    settled_unit: str = "settled",
) -> dict[str, Any]:
    body = {
        "edge_id": edge_id,
        "label": label,
        "question": question,
        "status": status,
        "issued_count": issued,
        "issued_unit": issued_unit,
        "settled_count": settled,
        "settled_unit": settled_unit,
        "independent_block_count": independent_blocks,
        "minimum_independent_blocks": minimum_blocks,
        "control_count": control_count,
        "reviewable": reviewable,
        "next_evidence": next_evidence,
        "decision_use": decision_use,
        "source_refs": sorted({str(value) for value in source_refs if value}),
        "capital_authority": False,
    }
    return {**body, "edge_sha256": stable_sha256(body)}


def compile_institutional_edge_map(
    *,
    research_learning: Mapping[str, Any],
    strategy_move_learning: Mapping[str, Any],
    institutional_learning: Mapping[str, Any],
    closed_book: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any],
    path_action: Mapping[str, Any] | None = None,
    historical_strategy_bulk_learning: Mapping[str, Any] | None = None,
    historical_strategy_bulk_panel: Mapping[str, Any] | None = None,
    historical_strategy_bulk_effects: Mapping[str, Any] | None = None,
    historical_strategy_outcome_robustness: Mapping[str, Any] | None = None,
    historical_strategy_law_search: Mapping[str, Any] | None = None,
    historical_strategy_security_walk_forward: Mapping[str, Any] | None = None,
    strategy_security_representation_learning: Mapping[str, Any] | None = None,
    research_budget_tournament: Mapping[str, Any] | None = None,
    strategy_program_learning: Mapping[str, Any] | None = None,
    strategy_program_transfer: Mapping[str, Any] | None = None,
    strategy_program_control_acquisition: Mapping[str, Any] | None = None,
    strategy_program_comparison: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe what each economic edge has earned from later evidence.

    The map is a projection over existing contracts. It cannot settle an outcome,
    promote a law, change a paper policy, or authorize capital.
    """

    question_experiment = dict(
        research_learning.get("research_question_policy_experiment") or {}
    )
    routing = dict(question_experiment.get("routing_decision") or {})
    question_units = _integer(question_experiment.get("settled_itt_unit_count"))
    question_floor = 2 * _integer(
        question_experiment.get("minimum_settled_units_per_arm")
    )
    question_reviewable = bool(routing.get("routing_change_allowed"))
    question_status = (
        "research_routing_reviewable"
        if question_reviewable
        else "collecting_candidate_level_itt_outcomes"
        if question_units
        else "awaiting_candidate_level_itt_outcomes"
    )

    panel = dict(institutional_learning.get("strategy_causal_panel") or {})
    treated = _integer(panel.get("treated_unit_count"))
    operating_outcomes = _integer(strategy_move_learning.get("outcome_episode_count"))
    strategy_regularities = [
        row for row in institutional_learning.get("strategy_regularities") or ()
        if isinstance(row, Mapping)
    ]
    strategy_evaluations = [
        row for row in institutional_learning.get("evaluations") or ()
        if isinstance(row, Mapping)
        and isinstance(row.get("strategy_regularity"), Mapping)
    ]
    strategy_observed = [
        dict((row.get("prospective_holdout") or {}).get("observed") or {})
        for row in strategy_regularities
    ]
    strategy_required = [
        dict((row.get("prospective_holdout") or {}).get("required") or {})
        for row in strategy_regularities
    ]
    strategy_blocks = max(
        (_integer(row.get("transfer_environments")) for row in strategy_observed), default=0,
    )
    strategy_floor = max(
        (_integer(row.get("transfer_environments")) for row in strategy_required), default=0,
    )
    controls = max(
        (_integer(row.get("bounded_control_units")) for row in strategy_observed), default=0,
    )
    strategy_reviewable = any(bool(row.get("promotion_eligible")) for row in strategy_evaluations)
    strategy_status = (
        "strategy_law_reviewable"
        if strategy_reviewable
        else str(strategy_regularities[0].get("status") or "")
        if strategy_regularities
        else "awaiting_exact_strategy_events"
    )

    program_learning = dict(strategy_program_learning or {})
    program_transfer = dict(strategy_program_transfer or {})
    program_controls = dict(strategy_program_control_acquisition or {})
    program_comparison = dict(strategy_program_comparison or {})
    program_requests = _integer(program_learning.get("request_count"))
    program_outcomes = _integer(program_comparison.get("treated_episode_count"))
    program_control_count = _integer(program_comparison.get("control_episode_count"))
    composition_rows = [
        comparison for card in program_comparison.get("cards") or ()
        if isinstance(card, Mapping)
        for comparison in card.get("comparisons") or ()
        if isinstance(comparison, Mapping)
        and comparison.get("control_identity") == "same_constituents_without_joint_evidence"
    ]
    program_blocks = max(
        (_integer(row.get("shared_environment_count")) for row in composition_rows),
        default=0,
    )
    program_block_floor = max(
        (_integer(row.get("minimum_shared_environments")) for row in composition_rows),
        default=2,
    )
    program_reviewable = bool(
        program_comparison.get("operating_association_reviewable")
    )
    program_status = (
        "strategy_program_operating_association_reviewable"
        if program_reviewable
        else str(program_comparison.get("status") or "")
        if program_comparison.get("status")
        else "acquiring_program_composition_controls"
        if program_transfer.get("comparison_ready_card_count")
        else "awaiting_program_operating_outcomes"
        if program_transfer.get("card_count")
        else "awaiting_program_source_classification"
        if program_requests
        else "awaiting_integrated_program_question"
    )

    forecast_scoreboard = dict(closed_book.get("scoreboard") or {})
    forecast_blocks = _integer(forecast_scoreboard.get("inference_block_count"))
    forecast_floor = _integer(forecast_scoreboard.get("minimum_inference_blocks"))
    forecast_tournament = dict(closed_book.get("world_model_tournament") or {})
    forecast_reviewable = bool(forecast_tournament.get("engine_evidence_eligible"))
    forecast_status = (
        "model_comparison_reviewable"
        if forecast_reviewable
        else "collecting_independent_return_blocks"
        if _integer(closed_book.get("settled_count"))
        else "awaiting_future_returns"
        if _integer(closed_book.get("run_count"))
        else "awaiting_sealed_forecasts"
    )

    policy_scoreboard = dict(portfolio_policy.get("scoreboard") or {})
    policy_blocks = _integer(policy_scoreboard.get("inference_block_count"))
    policy_floor = _integer(policy_scoreboard.get("minimum_inference_blocks"))
    policy_review = dict(policy_scoreboard.get("latest_policy_review") or {})
    policy_reviewable = (
        policy_review.get("activation_status") == "eligible_for_paper_policy_review"
        and bool(policy_review.get("recommended_policy_id"))
    )
    policy_status = (
        "paper_policy_reviewable"
        if policy_reviewable
        else "collecting_independent_portfolio_blocks"
        if _integer(portfolio_policy.get("settled_count"))
        else "awaiting_after_cost_portfolio_outcomes"
        if _integer(portfolio_policy.get("run_count"))
        else "awaiting_frozen_paper_policies"
    )

    path = dict(path_action or {})
    path_settlement = dict(path.get("settlement_status") or {})
    path_status = str(path_settlement.get("status") or "")
    path_settled = int(path_status in {"settled", "terminal_settled"})
    path_reviewable = bool(path_settlement.get("comparison_ready"))
    path_edge_status = (
        "path_model_reviewable"
        if path_reviewable
        else path_status
        if path_status
        else "awaiting_path_challenger"
    )

    bulk_learning = dict(historical_strategy_bulk_learning or {})
    bulk_panel = dict(historical_strategy_bulk_panel or {})
    bulk_effects = dict(historical_strategy_bulk_effects or {})
    outcome_robustness = dict(historical_strategy_outcome_robustness or {})
    law_search = dict(historical_strategy_law_search or {})
    historical_program_count = len(
        ((law_search.get("enumeration") or {}).get("programs") or ())
    )
    historical_ready_cells = _integer(bulk_panel.get("group_time_ready_cell_count"))
    historical_diagnostics = _integer(bulk_effects.get("ready_cell_count"))
    historical_controls = max(
        (
            _integer(((row.get("joint_design") or {}).get("post_control_count")))
            for row in bulk_panel.get("adoption_cells") or ()
            if isinstance(row, Mapping) and row.get("group_time_ready")
        ),
        default=0,
    )
    historical_reviewable = bool(
        law_search.get("promotion_eligible")
        and outcome_robustness.get("promotion_eligible")
    )
    historical_status = (
        "historical_strategy_law_reviewable"
        if historical_reviewable
        else str(law_search.get("status") or bulk_effects.get("status") or "")
        or "awaiting_historical_strategy_panel"
    )

    strategy_security = dict(historical_strategy_security_walk_forward or {})
    strategy_representation = dict(strategy_security_representation_learning or {})
    strategy_security_blocks = _integer(
        strategy_security.get("inference_block_count")
        if strategy_security.get("inference_block_count") is not None
        else strategy_security.get("independent_block_count")
        if strategy_security.get("independent_block_count") is not None
        else strategy_security.get("fold_count")
    )
    strategy_security_floor = _integer(
        strategy_security.get("minimum_independent_blocks")
    )
    strategy_security_reviewable = bool(
        strategy_security.get("promotion_eligible")
        and strategy_security.get("security_alpha_claim")
    )
    strategy_security_status = str(strategy_security.get("status") or "")
    if strategy_security_reviewable:
        strategy_security_status = "strategy_security_edge_reviewable"
    elif strategy_security_status == "typed_policy_did_not_clear_both_controls":
        strategy_security_status = "strategy_security_challenger_rejected"
    elif strategy_security_blocks:
        strategy_security_status = "collecting_strategy_security_blocks"
    elif not strategy_security_status:
        strategy_security_status = "awaiting_strategy_security_outcomes"

    budget = dict(research_budget_tournament or {})
    budget_blocks = _integer(budget.get("complete_independent_block_count"))
    budget_floor = _integer(budget.get("minimum_independent_blocks"))
    budget_reviewable = bool(
        budget.get("recommended_policy_id")
        and budget.get("queue_mutation_authority")
    )
    budget_status = (
        "research_budget_policy_reviewable"
        if budget_reviewable
        else str(budget.get("status") or "awaiting_research_budget_tournament")
    )

    edges = [
        _edge(
            "question_to_economic_information",
            "Research questions → economic information",
            "Does the way we investigate improve later paper outcomes?",
            status=question_status,
            issued=_integer(question_experiment.get("valid_assignment_unit_count")),
            settled=question_units,
            independent_blocks=question_units,
            minimum_blocks=question_floor,
            control_count=2,
            next_evidence=str(
                research_learning.get("next_activation")
                or "Settle every due randomized coverage-first and disagreement-first assignment."
            ),
            decision_use="research_question_routing_only",
            reviewable=question_reviewable,
            source_refs=(str(routing.get("decision_sha256") or ""),),
        ),
        _edge(
            "strategy_to_operating_consequence",
            "Strategy move → operating consequence",
            "Do exact management moves improve durability in comparable businesses?",
            status=strategy_status,
            issued=treated,
            settled=operating_outcomes,
            independent_blocks=strategy_blocks,
            minimum_blocks=strategy_floor,
            control_count=controls,
            next_evidence=str(
                panel.get("next_activation")
                or strategy_move_learning.get("next_activation")
                or "Acquire exact comparison events and later operating outcomes."
            ),
            decision_use="strategy_law_research_only",
            reviewable=strategy_reviewable,
            source_refs=(
                str(panel.get("readiness_sha256") or ""),
                str(strategy_move_learning.get("library_sha256") or ""),
                *(str(row.get("regularity_evidence_sha256") or "") for row in strategy_regularities),
            ),
        ),
        _edge(
            "strategy_program_composition_to_operating_consequence",
            "Integrated strategy program → operating consequence",
            (
                "Does a coordinated choice system outperform the same constituent "
                "moves executed without joint-program evidence?"
            ),
            status=program_status,
            issued=program_requests,
            settled=program_outcomes,
            independent_blocks=program_blocks,
            minimum_blocks=program_block_floor,
            control_count=program_control_count,
            next_evidence=str(
                (program_controls.get("next_transition") or {}).get("work_id")
                or (program_learning.get("next_transition") or {}).get("work_id")
                or program_comparison.get("next_activation")
                or program_transfer.get("next_activation")
                or "Classify an integrated program, settle its readout, and acquire matched controls."
            ),
            decision_use="strategy_program_research_only",
            reviewable=program_reviewable,
            source_refs=(
                str(program_transfer.get("index_sha256") or ""),
                str(program_controls.get("acquisition_sha256") or ""),
                str(program_comparison.get("comparison_sha256") or ""),
            ),
            issued_unit="program questions",
            settled_unit="program operating outcomes",
        ),
        _edge(
            "historical_strategy_to_candidate_law",
            "Historical strategy evidence → candidate law",
            "Does an outcome-blind strategy program survive support, pretrend, and outcome-scale checks?",
            status=historical_status,
            issued=_integer(bulk_learning.get("classified_event_count")),
            settled=historical_diagnostics,
            independent_blocks=0,
            minimum_blocks=1,
            control_count=historical_controls,
            next_evidence=str(
                law_search.get("next_activation")
                or bulk_panel.get("next_activation")
                or "Acquire the nearest source-bound treated and control histories."
            ),
            decision_use="historical_strategy_evidence_routing_only",
            reviewable=historical_reviewable,
            source_refs=(
                str(bulk_learning.get("learning_queue_sha256") or ""),
                str(bulk_panel.get("readiness_sha256") or ""),
                str(bulk_effects.get("diagnostics_sha256") or ""),
                str(outcome_robustness.get("robustness_sha256") or ""),
                str(law_search.get("law_search_sha256") or ""),
            ),
            issued_unit="typed events",
            settled_unit="admissible diagnostic cells",
        ),
        _edge(
            "strategy_to_security_consequence",
            "Strategy phenotype → factor-controlled security outcome",
            (
                "Do filed strategy-move phenotypes improve return forecasts and paper "
                "selection beyond untyped and factor controls?"
            ),
            status=strategy_security_status,
            issued=_integer(strategy_security.get("eligible_security_outcome_count")),
            settled=_integer(strategy_security.get("scored_episode_count")),
            independent_blocks=strategy_security_blocks,
            minimum_blocks=strategy_security_floor,
            control_count=2,
            next_evidence=str(
                strategy_representation.get("next_activation")
                or strategy_security.get("next_activation")
                or "Freeze a representation challenger and test it on later source-bound events."
            ),
            decision_use="strategy_security_research_only",
            reviewable=strategy_security_reviewable,
            source_refs=(
                str(strategy_security.get("tournament_sha256") or ""),
                str(strategy_representation.get("learning_sha256") or ""),
                str(
                    (strategy_security.get("execution_contract") or {}).get(
                        "factor_basis_sha256"
                    ) or ""
                ),
            ),
            issued_unit="identity-bound isolated events",
            settled_unit="walk-forward predictions",
        ),
        _edge(
            "underwriting_to_security_outcome",
            "Underwriting model → security outcome",
            "Do valuation, durability, factor, and strategy models beat simple controls?",
            status=forecast_status,
            issued=_integer(closed_book.get("run_count")),
            settled=_integer(closed_book.get("settled_count")),
            independent_blocks=forecast_blocks,
            minimum_blocks=forecast_floor,
            control_count=len(forecast_scoreboard.get("candidate_rows") or ()),
            next_evidence=(
                "Settle sealed return windows, then compare exact model bundles on independent blocks."
                if not forecast_reviewable else
                "Review the comparison without decomposing bundle credit into untested components."
            ),
            decision_use="paper_model_review_only",
            reviewable=forecast_reviewable,
            source_refs=(
                str((closed_book.get("forecast_learning") or {}).get("forecast_learning_sha256") or ""),
                str(forecast_tournament.get("result_sha256") or ""),
            ),
        ),
        _edge(
            "allocation_to_after_cost_utility",
            "Paper allocation → after-cost utility",
            "Does the complete allocation policy beat cash and simple portfolios after costs?",
            status=policy_status,
            issued=_integer(portfolio_policy.get("run_count")),
            settled=_integer(portfolio_policy.get("settled_count")),
            independent_blocks=policy_blocks,
            minimum_blocks=policy_floor,
            control_count=len(policy_scoreboard.get("rows") or ()),
            next_evidence=str(
                policy_scoreboard.get("next_activation")
                or "Settle the first complete paper-policy block."
            ),
            decision_use="paper_policy_review_only",
            reviewable=policy_reviewable,
            source_refs=(str(policy_review.get("policy_review_sha256") or ""),),
        ),
        _edge(
            "company_state_path_model",
            "Company state → next-state path",
            "Does a path-dependent company-state model beat reversible and memoryless controls?",
            status=path_edge_status,
            issued=int(bool(path)),
            settled=path_settled,
            independent_blocks=_integer(path_settlement.get("inference_block_count")),
            minimum_blocks=_integer(path_settlement.get("minimum_inference_blocks")),
            control_count=len(path.get("required_control_ids") or ()),
            next_evidence=str(
                path_settlement.get("next_activation")
                or path_settlement.get("next_due_at")
                or "Open a frozen path challenger and wait for its declared horizons."
            ),
            decision_use="world_model_research_only",
            reviewable=path_reviewable,
            source_refs=(
                str(path.get("run_sha256") or ""),
                str(path_settlement.get("settlement_sha256") or ""),
            ),
        ),
        _edge(
            "research_allocation_to_decision_evidence",
            "Research allocation → decision evidence",
            "Which research-routing rule produces the most decision impact per unit of work?",
            status=budget_status,
            issued=_integer(budget.get("eligible_work_count")),
            settled=budget_blocks,
            independent_blocks=budget_blocks,
            minimum_blocks=budget_floor,
            control_count=len(budget.get("arms") or ()),
            next_evidence=str(
                budget.get("exact_blocker")
                or "Settle independently frozen research-budget blocks."
            ),
            decision_use="future_research_scheduler_review_only",
            reviewable=budget_reviewable,
            source_refs=(str(budget.get("source_schedule_sha256") or ""),),
            issued_unit="eligible jobs",
            settled_unit="settled blocks",
        ),
    ]
    reviewable = [row["edge_id"] for row in edges if row["reviewable"]]
    body = {
        "schema": INSTITUTIONAL_EDGE_MAP_SCHEMA,
        "identity": "economic_learning_edge_by_outcome_and_authority",
        "edge_count": len(edges),
        "historical_strategy_program_count": historical_program_count,
        "historical_strategy_ready_cell_count": historical_ready_cells,
        "reviewable_edge_ids": reviewable,
        "economic_edge_established": bool(
            "underwriting_to_security_outcome" in reviewable
            and "allocation_to_after_cost_utility" in reviewable
        ),
        "alpha_evidence_status": (
            "prospective_policy_evidence_reviewable"
            if "allocation_to_after_cost_utility" in reviewable
            else "unestablished"
        ),
        "edges": edges,
        "boundary": (
            "This map projects existing evidence contracts. A reviewable edge may change only "
            "its declared paper or research policy; it never authorizes an order."
        ),
        "capital_authority": False,
    }
    return {**body, "edge_map_sha256": stable_sha256(body)}


__all__ = ["INSTITUTIONAL_EDGE_MAP_SCHEMA", "compile_institutional_edge_map"]
