"""Compile the next prospective variation needed for component credit."""

from __future__ import annotations

from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256


LEARNING_EXPERIMENT_DESIGN_SCHEMA = "jaggedthoughts-learning-experiment-design-v1"


def _hashed(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    payload = dict(body)
    return {**payload, field: stable_sha256(payload)}


def _credit_rows(assignment: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("component_id") or ""): row
        for row in assignment.get("components") or ()
        if isinstance(row, Mapping) and row.get("component_id")
    }


def _experiment(
    *,
    family_id: str,
    component_id: str,
    status: str,
    contract_schema: str,
    control_ids: list[str],
    treatment_ids: list[str],
    varied_component_ids: list[str],
    held_constant: list[str],
    identifies: list[str],
    source_refs: list[str],
    remaining_blocks: int | None = None,
    lineage_object_kinds: tuple[str, ...] = (),
) -> dict[str, Any]:
    identity = {
        "family_id": family_id,
        "component_id": component_id,
        "control_ids": control_ids,
        "treatment_ids": treatment_ids,
        "varied_component_ids": varied_component_ids,
    }
    refs = sorted({value for value in source_refs if value})
    body: dict[str, Any] = {
        "experiment_id": f"learning-isolation:{stable_sha256(identity)[:24]}",
        "family_id": family_id,
        "component_id": component_id,
        "status": status,
        "existing_contract_schema": contract_schema,
        "variation": {
            "control_ids": control_ids,
            "treatment_ids": treatment_ids,
            "varied_component_ids": varied_component_ids,
            "variation_count": len(varied_component_ids),
        },
        "same_information_contract": {
            "held_constant": held_constant,
            "one_component_at_a_time": (
                len(control_ids) == len(treatment_ids) == len(varied_component_ids)
            ),
        },
        "can_identify_after_independent_outcome": identifies,
        "remaining_minimum_blocks": remaining_blocks,
        "lineage": {
            "source_refs": refs,
            "expected_golden_object_kinds": list(lineage_object_kinds),
            "append_only_outcome": True,
            "historical_evidence_relabelled": False,
        },
        "authority": "prospective_paper_experiment_design_only",
        "capital_authority": False,
    }
    return _hashed(body, "experiment_sha256")


def _blocker(component_id: str, code: str, **context: Any) -> dict[str, Any]:
    return _hashed({
        "component_id": component_id,
        "code": code,
        **context,
        "capital_authority": False,
    }, "blocker_sha256")


def _fund_pair(programs: list[Mapping[str, Any]]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Choose the least-correlated admitted pair; identity breaks ties."""

    pairs = []
    ordered = sorted(programs, key=lambda row: str(row.get("program_id") or ""))
    for index, left in enumerate(ordered):
        left_id = str((left.get("identity") or {}).get("subject_id") or "")
        for right in ordered[index + 1:]:
            right_id = str((right.get("identity") or {}).get("subject_id") or "")
            correlation = (left.get("correlations_to_compared_funds") or {}).get(right_id)
            pairs.append((
                float(correlation) if correlation is not None else 1.0,
                str(left.get("program_id") or ""),
                str(right.get("program_id") or ""),
                left,
                right,
            ))
    _, _, _, left, right = min(pairs, key=lambda row: row[:3])
    return left, right


def compile_learning_experiment_design(
    *,
    learning_credit_assignment: Mapping[str, Any],
    research_learning: Mapping[str, Any],
    strategy_alpha_tournament: Mapping[str, Any],
    institutional_learning: Mapping[str, Any],
    fund_sleeve_comparison: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any],
    household_policy_tournament: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reuse active trials and propose only the missing isolated variation."""

    credit = _credit_rows(learning_credit_assignment)
    active: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    question = dict(research_learning.get("research_question_policy_experiment") or {})
    question_family = str(question.get("experiment_id") or "")
    if question_family and not credit.get("research_question_policy", {}).get("credit_earned"):
        settled = int(question.get("settled_itt_unit_count") or 0)
        routing = dict(question.get("routing_decision") or {})
        row = _experiment(
            family_id=question_family,
            component_id="research_question_policy",
            status="continue_existing_family",
            contract_schema="jaggedthoughts-research-question-policy-assignment-v2",
            control_ids=["coverage_first"], treatment_ids=["disagreement_first"],
            varied_component_ids=["research_question_policy"],
            held_constant=[
                "entity_kind", "frozen_assignment_batch", "common_dossier_schema",
                "economic_outcome_horizon",
            ],
            identifies=[
                "intent_to_treat_incremental_return_vs_no_action_of_disagreement_first_routing"
            ],
            source_refs=[
                str(routing.get("decision_sha256") or ""),
                str(routing.get("unit_set_sha256") or ""),
            ],
            remaining_blocks=max(
                0,
                2 * int(question.get("minimum_settled_units_per_arm") or 20)
                - settled,
            ),
            lineage_object_kinds=("agent_research_request", "paper_decision"),
        )
        active.append(row)
        proposals.append(row)

    alpha = dict(strategy_alpha_tournament)
    model_ids = list(map(str, alpha.get("nested_model_ids") or ()))
    required_models = [
        "valuation_only_control",
        "durability_valuation_control",
        "strategy_phenotype_durability_valuation",
    ]
    if alpha.get("same_information_control") and model_ids == required_models:
        activation = dict(alpha.get("binding_activation") or {})
        activated = [
            row for row in activation.get("activation_statuses") or ()
            if isinstance(row, Mapping) and row.get("status") == "activated"
        ]
        evidence = dict(alpha.get("evidence") or {})
        row = _experiment(
            family_id="strategy-alpha-nested-ablation-v1",
            component_id="underwriting_forecast_bundle",
            status="continue_existing_family" if activated else "ready_on_next_eligible_episode",
            contract_schema="jaggedthoughts-strategy-alpha-binding-v1",
            control_ids=required_models[:-1], treatment_ids=required_models[1:],
            varied_component_ids=[
                "durable_earnings_expectation",
                "source_bound_strategy_phenotype",
            ],
            held_constant=[
                "entity", "information_set_sha256", "issue_time", "return_window",
                "security_control", "forecast_output_contract",
            ],
            identifies=[
                "durability_increment_beyond_valuation",
                "strategy_phenotype_increment_beyond_durability_and_valuation",
            ],
            source_refs=[
                str(evidence.get("evidence_sha256") or ""),
                *(str(item.get("binding_sha256") or "") for item in activated),
            ],
            remaining_blocks=max(0, 8 - int(alpha.get("eligible_episode_count") or 0)),
            lineage_object_kinds=(
                "strategy_alpha_issuance_action", "closed_book_forecast_run",
                "backtest_episode",
            ),
        )
        active.append(row)
        proposals.append(row)
    else:
        blockers.append(_blocker(
            "underwriting_forecast_bundle", "nested_same_information_contract_missing",
            observed_model_ids=model_ids,
        ))

    latest_run = dict(portfolio_policy.get("latest_run") or {})
    policy_rows = list((latest_run.get("attribution_contract") or {}).get("rows") or ())
    varied_laws = sorted({
        str(contribution.get("law_key") or "")
        for row in policy_rows if isinstance(row, Mapping)
        and str(row.get("comparison_id") or "").startswith("learned_law_priority__vs__")
        for contribution in row.get("law_contributions") or ()
        if isinstance(contribution, Mapping) and contribution.get("law_key")
    })
    eligible_laws = sorted(
        (dict(row) for row in institutional_learning.get("evaluations") or ()
         if isinstance(row, Mapping) and row.get("promotion_eligible")),
        key=lambda row: (str(row.get("law_key") or ""), str(row.get("law_sha256") or "")),
    )
    if len(varied_laws) == 1:
        row = _experiment(
            family_id=f"law-policy-isolation:{latest_run.get('run_id')}",
            component_id="strategy_regularity", status="active_frozen_comparison",
            contract_schema="jaggedthoughts-portfolio-policy-run-v1",
            control_ids=["discovery_priority"], treatment_ids=["learned_law_priority"],
            varied_component_ids=varied_laws,
            held_constant=[
                "opportunity_book_sha256", "eligible_universe", "start_prices",
                "gross_weight", "position_cap", "return_window", "transaction_cost_bps",
            ],
            identifies=["incremental_after_cost_return_of_exact_strategy_regularity"],
            source_refs=[str(latest_run.get("run_sha256") or "")],
            remaining_blocks=max(0, 8 - int((portfolio_policy.get("scoreboard") or {}).get("inference_block_count") or 0)),
            lineage_object_kinds=("investment_law_evaluation", "portfolio_policy_run"),
        )
        active.append(row)
    elif eligible_laws:
        law = eligible_laws[0]
        proposals.append(_experiment(
            family_id=f"law-policy-isolation:{law.get('law_sha256')}",
            component_id="strategy_regularity", status="ready_to_freeze",
            contract_schema="jaggedthoughts-portfolio-policy-run-v1",
            control_ids=["discovery_priority"],
            treatment_ids=[f"discovery_plus_law:{law.get('law_key')}"],
            varied_component_ids=[str(law.get("law_key") or "")],
            held_constant=[
                "opportunity_book_sha256", "eligible_universe", "start_prices",
                "gross_weight", "position_cap", "return_window", "transaction_cost_bps",
            ],
            identifies=["incremental_after_cost_return_of_exact_strategy_regularity"],
            source_refs=[
                str(law.get("law_sha256") or ""), str(law.get("evaluation_sha256") or ""),
            ],
            remaining_blocks=8,
            lineage_object_kinds=("investment_law_evaluation", "portfolio_policy_run"),
        ))
    else:
        blockers.append(_blocker(
            "strategy_regularity", "promotion_eligible_law_missing",
            candidate_law_sha256s=sorted(
                str(row.get("law_sha256") or "")
                for row in institutional_learning.get("candidates") or ()
                if isinstance(row, Mapping) and row.get("law_sha256")
            ),
        ))

    admitted_sleeves = []
    eligible_program_ids = []
    for sleeve in fund_sleeve_comparison.get("sleeves") or ():
        if not isinstance(sleeve, Mapping):
            continue
        eligible_program_ids.extend(
            str(row.get("program_id") or "") for row in sleeve.get("programs") or ()
            if isinstance(row, Mapping) and row.get("comparison_eligible")
        )
        admitted = [
            row for row in sleeve.get("programs") or ()
            if isinstance(row, Mapping) and row.get("comparison_eligible")
            and row.get("implementation_review_admitted")
        ]
        if len(admitted) >= 2:
            admitted_sleeves.append((str(sleeve.get("sleeve_id") or ""), admitted))
    if admitted_sleeves:
        sleeve_id, programs = sorted(admitted_sleeves, key=lambda row: row[0])[0]
        control, treatment = _fund_pair(programs)
        proposals.append(_experiment(
            family_id=f"fund-program-isolation:{sleeve_id}",
            component_id="fund_implementation_program", status="ready_to_freeze",
            contract_schema="jaggedthoughts-fund-sleeve-comparison-v1",
            control_ids=[str(control.get("program_id") or "")],
            treatment_ids=[str(treatment.get("program_id") or "")],
            varied_component_ids=["fund_implementation_program"],
            held_constant=[
                "sleeve_id", "normalized_implementation_fraction", "portfolio_weight",
                "issue_time", "return_window", "transaction_cost_basis",
            ],
            identifies=["incremental_after_cost_return_of_exact_fund_implementation"],
            source_refs=[
                str(control.get("program_sha256") or ""),
                str(treatment.get("program_sha256") or ""),
            ],
            remaining_blocks=8,
            lineage_object_kinds=("portfolio_policy_run",),
        ))
    else:
        blockers.append(_blocker(
            "fund_implementation_program", "two_same_sleeve_admissions_missing",
            comparison_eligible_program_ids=sorted(filter(None, eligible_program_ids)),
        ))

    comparisons = list((latest_run.get("attribution_contract") or {}).get("comparisons") or ())
    if latest_run.get("run_id") and comparisons:
        active.append(_experiment(
            family_id=str(latest_run["run_id"]),
            component_id="complete_paper_portfolio_policy",
            status="active_frozen_comparison",
            contract_schema="jaggedthoughts-portfolio-policy-run-v1",
            control_ids=sorted({str(row.get("reference_policy_id") or "") for row in comparisons}),
            treatment_ids=sorted({str(row.get("policy_id") or "") for row in comparisons}),
            varied_component_ids=["complete_paper_portfolio_policy"],
            held_constant=[
                "opportunity_book_sha256", "eligible_universe", "start_prices",
                "return_window", "transaction_cost_bps",
            ],
            identifies=["complete_policy_family_after_cost_return_only"],
            source_refs=[
                str(latest_run.get("run_sha256") or ""),
                str(latest_run.get("opportunity_book_sha256") or ""),
            ],
            remaining_blocks=max(0, 8 - int((portfolio_policy.get("scoreboard") or {}).get("inference_block_count") or 0)),
            lineage_object_kinds=("opportunity_book", "portfolio_policy_run"),
        ))

    household = dict(household_policy_tournament or {})
    household_run = dict(household.get("latest_run") or {})
    if household_run.get("run_id"):
        family_id = str((household_run.get("trial_family") or {}).get("trial_family_id") or "")
        review = next((
            row for row in household.get("reviews") or ()
            if isinstance(row, Mapping) and row.get("trial_family_id") == family_id
        ), {})
        blocks = int((review.get("survivor_set") or {}).get("inference_block_count") or 0)
        policies = [
            str(row.get("policy_id") or "") for row in household_run.get("policies") or ()
            if isinstance(row, Mapping) and row.get("policy_id")
        ]
        control = str(household_run.get("control_policy_id") or "broad_sleeve_control")
        active.append(_experiment(
            family_id=family_id or str(household_run["run_id"]),
            component_id="household_implementation_rule",
            status=(
                "settled_collecting_family_blocks"
                if household_run.get("lifecycle_status") == "settled"
                else "active_frozen_comparison"
            ),
            contract_schema="jaggedthoughts-household-policy-tournament-run-v1",
            control_ids=[control],
            treatment_ids=sorted(policy_id for policy_id in policies if policy_id != control),
            varied_component_ids=["household_implementation_rule"],
            held_constant=[
                "scenario_sha256", "household_sleeve_weights", "priced_identity_set",
                "return_window", "transaction_cost_bps",
            ],
            identifies=["incremental_after_cost_return_of_household_implementation_rule"],
            source_refs=[
                str(household_run.get("scenario_sha256") or ""),
                str(household_run.get("run_sha256") or ""),
            ],
            remaining_blocks=max(0, 8 - blocks),
            lineage_object_kinds=(
                "household_allocation_scenario", "household_policy_tournament_run",
            ),
        ))
    else:
        proposals.append(_experiment(
            family_id="household-implementation-rule-primary-v1",
            component_id="household_implementation_rule",
            status="requires_operator_scenario_freeze",
            contract_schema="jaggedthoughts-household-policy-tournament-run-v1",
            control_ids=["broad_sleeve_control"],
            treatment_ids=["current_admitted_implementation_rivals"],
            varied_component_ids=["household_implementation_rule"],
            held_constant=[
                "operator_reviewed_scenario", "household_sleeve_weights",
                "priced_identity_set", "return_window", "transaction_cost_bps",
            ],
            identifies=["incremental_after_cost_return_of_household_implementation_rule"],
            source_refs=[str(household.get("status_sha256") or "")],
            remaining_blocks=8,
            lineage_object_kinds=(
                "household_allocation_scenario", "household_policy_tournament_run",
            ),
        ))

    proposals.sort(key=lambda row: (
        -len(row["can_identify_after_independent_outcome"]), row["experiment_id"],
    ))
    active.sort(key=lambda row: (row["component_id"], row["experiment_id"]))
    blockers.sort(key=lambda row: (row["component_id"], row["code"]))
    body = {
        "schema": LEARNING_EXPERIMENT_DESIGN_SCHEMA,
        "identity": "next_prospective_isolated_variation_from_unearned_component_credit",
        "source_learning_credit_sha256": learning_credit_assignment.get("learning_credit_sha256"),
        "active_experiments": active,
        "proposals": proposals,
        "blockers": blockers,
        "next_experiment": proposals[0] if proposals else None,
        "scheduler": {
            "method": "distinct_identifiable_contrast_count_desc_then_experiment_identity",
            "expected_information_gain_estimated": False,
        },
        "counts": {
            "active": len(active), "proposed": len(proposals), "blocked": len(blockers),
        },
        "boundary": (
            "The design compiler reuses frozen experiment families and changes one credited unit "
            "at a time. It neither settles outcomes nor activates paper or funded capital."
        ),
        "authority": "prospective_paper_experiment_design_only",
        "capital_authority": False,
    }
    return _hashed(body, "design_sha256")


__all__ = ["LEARNING_EXPERIMENT_DESIGN_SCHEMA", "compile_learning_experiment_design"]
