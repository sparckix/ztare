"""Cross-layer credit projection over existing prospective learning contracts."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256


LEARNING_CREDIT_ASSIGNMENT_SCHEMA = "jaggedthoughts-learning-credit-assignment-v2"


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _row(
    component_id: str,
    unit: str,
    *,
    issued: int,
    settled: int,
    independent_blocks: int,
    isolated: int,
    status: str,
    next_evidence: str,
    source_refs: tuple[str, ...] = (),
    allowed_uses: tuple[str, ...] = (),
) -> dict[str, Any]:
    body = {
        "component_id": component_id,
        "credit_unit": unit,
        "issued_count": issued,
        "settled_outcome_count": settled,
        "independent_block_count": independent_blocks,
        "isolated_credit_count": isolated,
        "credit_earned": isolated > 0,
        "allowed_uses": sorted(set(allowed_uses)) if isolated > 0 else [],
        "status": status,
        "next_evidence": next_evidence,
        "source_refs": sorted({value for value in source_refs if value}),
        "capital_authority": False,
    }
    return {**body, "component_credit_sha256": stable_sha256(body)}


def compile_learning_credit_assignment(
    *,
    research_learning: Mapping[str, Any],
    closed_book: Mapping[str, Any],
    institutional_learning: Mapping[str, Any],
    fund_sleeve_comparison: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any],
    household_policy_tournament: Mapping[str, Any] | None = None,
    activation_matrix_policy_learning: Mapping[str, Any] | None = None,
    underwriting_method_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Tell which frozen component earned an outcome without unbundling wins.

    This is a read projection, not another outcome store. An isolated credit is
    counted only when an existing prospective comparison varied that component.
    """

    question = dict(research_learning.get("research_question_policy_experiment") or {})
    routing = dict(question.get("routing_decision") or {})
    research_body = dict(research_learning)
    research_sha = str(research_body.pop("learning_sha256", ""))
    routing_body = dict(routing)
    routing_sha = str(routing_body.pop("decision_sha256", ""))
    research_valid = bool(
        research_body.get("schema") == "jaggedthoughts-research-acquisition-learning-v1"
        and stable_sha256(research_body) == research_sha
        and routing_body.get("schema")
        == "jaggedthoughts-research-question-routing-decision-v1"
        and stable_sha256(routing_body) == routing_sha
    )
    question_programs = {
        str(row.get("question_program_id") or "")
        for row in research_learning.get("rows") or ()
        if isinstance(row, Mapping) and row.get("question_program_id")
    }
    settled_itt_units = _count(question.get("settled_itt_unit_count"))
    question_credit = int(research_valid and bool(routing.get("routing_change_allowed")))
    matrix_policy = dict(activation_matrix_policy_learning or {})
    matrix_policy_body = dict(matrix_policy)
    matrix_policy_sha = str(matrix_policy_body.pop("policy_learning_sha256", ""))
    matrix_policy_valid = bool(
        matrix_policy_body.get("schema")
        == "jaggedthoughts-activation-matrix-policy-learning-v2"
        and stable_sha256(matrix_policy_body) == matrix_policy_sha
    )
    matrix_pairs = _count(matrix_policy.get("complete_pair_count"))
    matrix_credit = int(
        matrix_policy_valid and bool(matrix_policy.get("routing_change_allowed"))
    )
    method_policy = dict(underwriting_method_policy or {})
    method_policy_body = dict(method_policy)
    method_policy_sha = str(method_policy_body.pop("policy_sha256", ""))
    method_policy_valid = bool(
        method_policy_body.get("schema") == "jaggedthoughts-underwriting-method-policy-v1"
        and stable_sha256(method_policy_body) == method_policy_sha
    )
    ablation = dict(closed_book.get("underwriting_ablation") or {})
    ablation_body = dict(ablation)
    ablation_sha = str(ablation_body.pop("status_sha256", ""))
    ablation_valid = bool(
        ablation_body.get("schema")
        == "jaggedthoughts-underwriting-information-ablation-status-v1"
        and stable_sha256(ablation_body) == ablation_sha
    )
    if method_policy_valid and ablation_valid:
        try:
            from .underwriting_method_policy import compile_underwriting_method_policy

            method_policy_valid = method_policy == compile_underwriting_method_policy(
                ablation,
                compiled_at=str(method_policy.get("compiled_at") or ""),
                exploration_quota=float(method_policy.get("exploration_quota") or 0.20),
            )
        except (KeyError, TypeError, ValueError):
            method_policy_valid = False
    method_blocks = max(
        (_count(row.get("independent_block_count")) for row in method_policy.get("comparisons") or ()
         if isinstance(row, Mapping)),
        default=0,
    )
    method_credit = int(
        method_policy_valid and ablation_valid
        and method_policy.get("source_ablation_status_sha256") == ablation_sha
        and method_policy.get("routing_decision")
        in {"prefer_fingerprint", "prefer_full_research"}
    )

    forecast = dict(closed_book.get("forecast_learning") or {})
    bundles = [row for row in forecast.get("bundles") or () if isinstance(row, Mapping)]
    settled_bundles = [row for row in bundles if _count(row.get("settled_count"))]
    forecast_blocks = max(
        (_count(row.get("inference_block_count")) for row in bundles), default=0,
    )
    mechanism_ids = {
        str(value)
        for row in bundles
        for value in (row.get("bundle") or {}).get("mechanism_ids") or ()
        if value
    }
    forecast_program_ids = {
        str(episode.get("candidate_id") or "")
        for row in bundles
        for episode in row.get("episodes") or ()
        if isinstance(episode, Mapping) and episode.get("candidate_id")
    }

    laws = [
        row for row in institutional_learning.get("candidates") or ()
        if isinstance(row, Mapping)
    ]
    eligible_laws = {
        str(row.get("law_key") or "")
        for row in institutional_learning.get("evaluations") or ()
        if isinstance(row, Mapping) and row.get("promotion_eligible")
    } - {""}
    attribution = dict(portfolio_policy.get("scoreboard") or {})
    law_policy_settlements = [
        row for row in attribution.get("attribution_comparisons") or ()
        if str(row.get("comparison_id") or "").startswith("learned_law_priority__vs__")
    ]
    latest_run = dict(portfolio_policy.get("latest_run") or {})
    policy_rows = list(
        (latest_run.get("attribution_contract") or {}).get("rows") or ()
    )
    varied_law_ids = {
        str(contribution.get("law_key") or "")
        for row in policy_rows
        if isinstance(row, Mapping)
        and str(row.get("comparison_id") or "").startswith("learned_law_priority__vs__")
        for contribution in row.get("law_contributions") or ()
        if isinstance(contribution, Mapping) and contribution.get("law_key")
    }
    law_policy_outcomes = sum(
        _count(row.get("episode_count")) for row in law_policy_settlements
    )
    law_credit = law_policy_outcomes if len(varied_law_ids) == 1 else 0

    fund_programs = [
        row
        for sleeve in fund_sleeve_comparison.get("sleeves") or ()
        if isinstance(sleeve, Mapping)
        for row in sleeve.get("programs") or ()
        if isinstance(row, Mapping)
    ]
    admitted_funds = [row for row in fund_programs if row.get("implementation_review_admitted")]
    linked_fund_programs = {
        str(row.get("implementation_program_id") or "") for row in policy_rows
        if isinstance(row, Mapping) and row.get("implementation_program_id")
    }
    linked_by_comparison: dict[str, set[str]] = {}
    for row in policy_rows:
        if (
            not isinstance(row, Mapping)
            or not row.get("implementation_program_id")
            or not row.get("reference_implementation_program_id")
            or row.get("isolated_component_kind") != "fund_implementation_program"
        ):
            continue
        linked_by_comparison.setdefault(str(row.get("comparison_id") or ""), set()).add(
            str(row["implementation_program_id"])
        )
    settled_by_comparison = {
        str(row.get("comparison_id") or ""): _count(row.get("episode_count"))
        for row in attribution.get("attribution_comparisons") or ()
        if isinstance(row, Mapping)
    }
    fund_outcomes = sum(
        settled_by_comparison.get(comparison, 0) for comparison in linked_by_comparison
    )
    fund_credit = sum(
        settled_by_comparison.get(comparison, 0)
        for comparison, programs in linked_by_comparison.items() if len(programs) == 1
    )

    policy_scoreboard = dict(portfolio_policy.get("scoreboard") or {})
    policy_blocks = _count(policy_scoreboard.get("inference_block_count"))
    policy_review = dict(policy_scoreboard.get("latest_policy_review") or {})
    policy_credit = int(
        policy_review.get("activation_status") == "eligible_for_paper_policy_review"
        and bool(policy_review.get("recommended_policy_id"))
    )
    policy_ids = {
        str(row.get("policy_id") or "")
        for row in latest_run.get("policies") or ()
        if isinstance(row, Mapping) and row.get("policy_id")
    }
    household = dict(household_policy_tournament or {})
    household_reviews = [
        row for row in household.get("reviews") or () if isinstance(row, Mapping)
    ]
    household_blocks = max((
        _count((row.get("survivor_set") or {}).get("inference_block_count"))
        for row in household_reviews
    ), default=0)
    household_reviewable = [
        row for row in household_reviews
        if row.get("statistical_survivor_for_operator_review")
    ]

    components = [
        _row(
            "research_question_policy",
            "candidate-level randomized question-policy assignment",
            issued=_count(question.get("valid_assignment_unit_count")),
            settled=settled_itt_units,
            independent_blocks=settled_itt_units, isolated=question_credit,
            status="earned_for_routing_review" if question_credit else "awaiting_due_itt_outcomes",
            next_evidence=(
                "Settle every due candidate-level ITT assignment; process metrics cannot "
                "substitute for incremental return versus no action."
            ),
            source_refs=(routing_sha, research_sha),
            allowed_uses=("future_research_question_routing",),
        ),
        _row(
            "activation_response_question_policy",
            "matched activation response-question pair",
            issued=_count(matrix_policy.get("valid_pair_count")), settled=matrix_pairs,
            independent_blocks=matrix_pairs, isolated=matrix_credit,
            status=(
                "earned_for_activation_routing_review" if matrix_credit
                else "awaiting_matched_response_question_outcomes"
            ),
            next_evidence=(
                "Settle chronological matched activation-question pairs under the frozen "
                "response-matrix assignment."
            ),
            source_refs=(
                matrix_policy_sha,
                str(matrix_policy.get("eligible_pair_set_sha256") or ""),
            ),
            allowed_uses=("future_activation_question_routing",),
        ),
        _row(
            "underwriting_forecast_bundle",
            "exact forecast mechanism bundle",
            issued=len(bundles), settled=len(settled_bundles),
            independent_blocks=forecast_blocks, isolated=0,
            status="bundle_outcomes_only" if settled_bundles else "awaiting_sealed_return_outcomes",
            next_evidence="Vary one model component against a same-information bundle control before component credit.",
            source_refs=(str(forecast.get("forecast_learning_sha256") or ""),),
        ),
        _row(
            "underwriting_information_method",
            "nested same-process underwriting information ablation",
            issued=len(method_policy.get("comparisons") or ()), settled=method_blocks,
            independent_blocks=method_blocks, isolated=method_credit,
            status=(
                "earned_for_future_method_routing" if method_credit
                else "awaiting_isolated_method_outcomes"
            ),
            next_evidence=(
                "Settle the frozen three-arm same-process information ablation across "
                "eight independent return blocks."
            ),
            source_refs=(ablation_sha,),
            allowed_uses=("future_underwriting_method_routing",),
        ),
        _row(
            "strategy_regularity",
            "exact law identity in a separately varied policy",
            issued=len(laws), settled=law_policy_outcomes,
            independent_blocks=law_policy_outcomes, isolated=law_credit,
            status=(
                "isolated_policy_outcomes" if law_credit else
                "bundled_law_policy_outcomes" if law_policy_outcomes else
                "no_independently_varied_law_policy"
            ),
            next_evidence="Issue a non-equivalent law-adjusted policy, then settle it against the frozen discovery policy.",
            source_refs=(str(institutional_learning.get("state_sha256") or ""),),
            allowed_uses=("recurring_shadow_policy_influence",),
        ),
        _row(
            "fund_implementation_program",
            "exact one-for-one fund implementation program",
            issued=len(admitted_funds), settled=fund_outcomes,
            independent_blocks=fund_outcomes, isolated=fund_credit,
            status=(
                "isolated_policy_outcomes" if fund_credit else
                "bundled_implementation_outcomes" if fund_outcomes else
                "not_carried_into_policy" if fund_programs else "no_fund_programs"
            ),
            next_evidence="Admit two implementations and freeze both program ids in a same-information paper-policy comparison.",
            source_refs=(str(fund_sleeve_comparison.get("fund_sleeve_comparison_sha256") or ""),),
            allowed_uses=("recurring_shadow_policy_influence",),
        ),
        _row(
            "complete_paper_portfolio_policy",
            "complete policy family on one independent return block",
            issued=_count(portfolio_policy.get("run_count")),
            settled=_count(portfolio_policy.get("settled_count")),
            independent_blocks=policy_blocks, isolated=policy_credit,
            status="earned_for_paper_review" if policy_credit else "awaiting_independent_after_cost_blocks",
            next_evidence="Settle eight independent complete-policy blocks and retain one multiplicity-controlled survivor.",
            source_refs=(str(policy_review.get("policy_review_sha256") or ""),),
            allowed_uses=("operator_paper_policy_review",),
        ),
        _row(
            "household_implementation_rule",
            "complete household implementation rule versus its broad-sleeve control",
            issued=_count(household.get("run_count")),
            settled=_count(household.get("settled_count")),
            independent_blocks=household_blocks,
            isolated=int(bool(household_reviewable)),
            status=(
                "earned_for_operator_review" if household_reviewable else
                "awaiting_independent_after_cost_blocks" if household.get("run_count") else
                "awaiting_explicit_household_freeze"
            ),
            next_evidence=(
                "Settle eight independent same-family complete-policy blocks against each "
                "episode's broad-sleeve control."
            ),
            source_refs=(str(household.get("status_sha256") or ""),),
            allowed_uses=("operator_household_policy_review",),
        ),
    ]
    diagnostics = {
        "question_program_id_count": len(question_programs),
        "activation_matrix_complete_pair_count": matrix_pairs,
        "underwriting_method_independent_block_count": method_blocks,
        "underwriting_bundle_count": len(bundles),
        "underwriting_program_id_count": len(forecast_program_ids),
        "underwriting_mechanism_id_count": len(mechanism_ids),
        "underwriting_component_credit_count": 0,
        "eligible_strategy_law_count": len(eligible_laws),
        "policy_varied_strategy_law_count": len(varied_law_ids),
        "fund_comparison_program_count": len(fund_programs),
        "fund_policy_linked_program_count": len(linked_fund_programs),
        "latest_policy_id_count": len(policy_ids),
        "household_policy_trial_family_count": len(household_reviews),
    }
    body = {
        "schema": LEARNING_CREDIT_ASSIGNMENT_SCHEMA,
        "identity": "prospective_component_credit_by_frozen_variation_and_outcome",
        "components": components,
        "diagnostics": diagnostics,
        "earned_component_count": sum(row["credit_earned"] for row in components),
        "transfer_status": (
            "component_transfer_evidence_present"
            if any(row["credit_earned"] for row in components)
            else "no_component_transfer_earned"
        ),
        "boundary": (
            "A bundled win belongs to the exact bundle. Component credit requires a frozen "
            "same-information comparison that varied that component and a later independent outcome."
        ),
        "authority": "paper_learning_projection_only",
        "capital_authority": False,
    }
    return {**body, "learning_credit_sha256": stable_sha256(body)}


def validate_learning_credit_assignment(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the aggregate and every component before an earned use is consumed."""

    body = dict(value)
    declared = str(body.pop("learning_credit_sha256", ""))
    if body.get("schema") != LEARNING_CREDIT_ASSIGNMENT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("learning credit assignment identity is invalid")
    for row in body.get("components") or ():
        if not isinstance(row, Mapping):
            raise ValueError("learning credit component must be an object")
        component = dict(row)
        component_sha = str(component.pop("component_credit_sha256", ""))
        if stable_sha256(component) != component_sha:
            raise ValueError("learning credit component identity is invalid")
    return {**body, "learning_credit_sha256": declared}


def learning_credit_allows(
    value: Mapping[str, Any], *, component_id: str, use: str,
    source_ref: str | None = None,
) -> bool:
    """Return whether one exact settled component credit admits a downstream use."""

    assignment = validate_learning_credit_assignment(value)
    matches = [
        row for row in assignment.get("components") or ()
        if isinstance(row, Mapping) and row.get("component_id") == component_id
    ]
    if len(matches) != 1:
        return False
    row = matches[0]
    return bool(
        row.get("credit_earned")
        and use in set(map(str, row.get("allowed_uses") or ()))
        and (not source_ref or source_ref in set(map(str, row.get("source_refs") or ())))
    )


__all__ = [
    "LEARNING_CREDIT_ASSIGNMENT_SCHEMA", "compile_learning_credit_assignment",
    "learning_credit_allows", "validate_learning_credit_assignment",
]
