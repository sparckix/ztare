import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_valuation_bridge import (
    compile_contingent_policy_payoff_frontier,
    compile_direct_strategy_expectation_residual,
    compile_strategy_valuation_bridge,
    compile_strategy_valuation_bridge_readiness,
)


def _hashed(body, field):
    return {**body, field: stable_sha256(body)}


def test_strategy_ranges_lower_to_prices_without_crossing_candidate_identity(tmp_path) -> None:
    epoch = "2026-08-22T00:00:00Z"
    leaf, option_sha, move_sha, phenotype_sha = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
    def assumption(identity, kind, value, unit, ref):
        return {"assumption_id": identity, "assumption_type": kind, "value": value,
                "unit": unit, "source_refs": [ref]}
    baseline = _hashed({
        "schema": "jaggedthoughts-valuation-envelope-v1", "envelope_id": "base",
        "entity_id": "ACME", "evidence_epoch": epoch,
        "assumptions": [
            assumption("price", "MarketPrice", 50, "currency/share", "filing"),
            assumption("earnings", "OwnerEarnings", 6, "currency/year", "filing"),
            assumption("cash", "ExcessNetCash", 4, "currency", "filing"),
            assumption("shares", "Shares", 2, "shares", "filing"),
            assumption("rf", "RiskFreeRate", .04, "decimal", "market"),
            assumption("discount", "DiscountRate", .10, "decimal", "policy"),
            assumption("growth", "ForecastGrowth", .03, "decimal", "filing"),
            assumption("terminal", "TerminalGrowth", .02, "decimal", "policy"),
            assumption("horizon", "Horizon", 10, "years", "policy"),
        ],
        "scenarios": [{"scenario_id": "base-path", "mechanism_id": "base",
                       "assumption_ids": ["growth", "terminal"], "source_refs": ["filing"]}],
        "summary": {"price_implied_excess_return": .02},
    }, "envelope_sha256")
    (tmp_path / "valuation.json").write_text(json.dumps(baseline))
    quality = _hashed({
        "schema": "jaggedthoughts-company-quality-report-v1", "entity_id": "ACME",
        "as_of": epoch, "metrics": {"median_owner_earnings_margin": .20},
        "scores": {"durable_earnings_power": .8}, "source_refs": ["filing"],
    }, "quality_report_sha256")
    candidate = _hashed({
        "schema": "jaggedthoughts-discovery-candidate-v1", "entity_id": "ACME",
        "as_of": epoch, "quality_report_sha256": quality["quality_report_sha256"],
        "valuation": {
            "artifact_path": "valuation.json",
            "envelope_sha256": baseline["envelope_sha256"],
        },
    }, "candidate_sha256")
    program_id = "program-1"
    frontier = _hashed({
        "schema": "jaggedthoughts-company-strategy-frontier-v1",
        "company": {"id": "ACME", "candidate_leaf": leaf,
                    "candidate_sha256": candidate["candidate_sha256"]},
        "evidence_epoch": epoch,
        "option_catalog": [{"option_id": "move-1", "option_sha256": option_sha}],
        "programs": [{"program_id": program_id, "unique_option_ids": ["move-1"],
                      "evidence_refs": ["strategy-source"]}],
    }, "strategy_frontier_sha256")
    move = {
        "entity_id": "ACME", "candidate_leaf": leaf,
        "candidate_sha256": candidate["candidate_sha256"], "evidence_epoch": epoch,
        "option_id": "move-1", "option_sha256": option_sha, "move_sha256": move_sha,
        "strategy_choice_identity_sha256": "1" * 64,
        "strategy_frontier_sha256": frontier["strategy_frontier_sha256"],
        "mechanism_phenotype_sha256": phenotype_sha, "evidence_refs": ["strategy-source"],
    }
    estimate = {"metric_id": "earnings_durability", "unit": "score",
                "source_refs": ["law-source"]}
    effect = _hashed({"status": "transported_magnitude_available",
                      "metric_id": "earnings_durability", "unit": "score",
                      "estimates": [estimate]},
                     "effect_contract_sha256")
    binding = _hashed({
        "status": "bound_for_model_proposal", "law_identity_sha256": "e" * 64,
        "target": {"move_sha256": move_sha, "metric_id": "earnings_durability",
                   "unit": "score",
                   "environment": {"mechanism_phenotype_sha256": phenotype_sha}},
        "antecedent_assessment": {"target_move_sha256": move_sha, "as_of": epoch},
        "transported_effects": [estimate],
    }, "binding_sha256")
    conditional = {
        "translation_kind": "conditional_conjecture",
        "metric_id": "earnings_durability", "metric_unit": "score",
        "conjecture_id": "durability-to-cash-flow-v1",
        "falsifier": "settled operating outcomes fall outside the frozen range",
    }
    ranges = {
        "revenue_growth_delta": {"low": 0.00, "high": .02, "unit": "decimal",
                                 "source_refs": ["strategy-source"], **conditional},
        "owner_earnings_margin_delta": {"low": 0.00, "high": .10, "unit": "decimal",
                                        "source_refs": ["law-source"], **conditional},
        "durability_terminal_growth_delta": {"low": 0.00, "high": .005, "unit": "decimal",
                                             "source_refs": ["law-source"], **conditional},
    }
    result = compile_strategy_valuation_bridge(
        candidate_leaf=leaf, candidate=candidate, strategy_frontier=frontier,
        strategy_move=move, effect_contract=effect, effect_binding=binding,
        program_id=program_id, baseline_envelope=baseline,
        baseline_scenario_id="base-path", coordinate_ranges=ranges,
        excess_return_hurdle=.06,
    )

    assert result["status"] == "compiled_with_gaps"
    assert result["unsupported_coordinate_gaps"] == [{
        "coordinate": "reinvestment_growth_delta", "reason": "source_bound_range_missing",
    }]
    assert len(result["scenario_coordinates"]) == 2
    assert result["scenario_coordinates"][1]["lowered_owner_earnings"] > result["scenario_coordinates"][0]["lowered_owner_earnings"]
    assert result["hurdle_price_frontier"]["optimistic_maximum_price"] > result["hurdle_price_frontier"]["robust_maximum_price"]
    assert result["causal_translation_earned"] is False
    assert not any(result["authority"].values())

    with pytest.raises(ValueError, match="crossed candidate identity"):
        compile_strategy_valuation_bridge(
            candidate_leaf="f" * 64, candidate=candidate, strategy_frontier=frontier,
            strategy_move=move, effect_contract=effect, effect_binding=binding,
            program_id=program_id, baseline_envelope=baseline,
            baseline_scenario_id="base-path", coordinate_ranges=ranges,
            excess_return_hurdle=.06,
        )

    readiness = compile_strategy_valuation_bridge_readiness({
        "induction_sha256": "1" * 64,
        "candidates": [{"effect_estimate": {"status": "proposal_only",
                                               "estimates": [],
                                               "blockers": ["prospective_holdout"]}}],
    }, generated_at=epoch)
    assert readiness["status"] == "blocked_awaiting_transported_strategy_effect"
    assert readiness["blockers"] == ["prospective_holdout"]

    direct_readiness = compile_strategy_valuation_bridge_readiness({
        "induction_sha256": "2" * 64,
        "candidates": [{"effect_estimate": {
            "status": "transported_magnitude_available", "blockers": [],
            "estimates": [{"metric_id": "revenue_growth", "unit": "decimal"}],
        }}],
    }, generated_at=epoch)
    assert direct_readiness["status"] == "priced_effect_residual_required"
    assert direct_readiness["blockers"] == ["priced_effect_residual_required"]

    dual = _hashed({
        "schema": "jaggedthoughts-strategy-dual-outcome-contract-v1",
        "entity_id": "ACME", "candidate_sha256": candidate["candidate_sha256"],
        "move_sha256": move_sha, "strategy_choice_identity_sha256": "1" * 64,
        "implementation_event_sha256": "2" * 64,
        "operating_outcome": {
            "contract_sha256": "3" * 64, "metric_id": "owner_earnings_margin",
            "unit": "decimal", "direction": "increase", "minimum_effect": .01,
            "comparator": "pre_move_baseline",
        },
        "source_refs": ["strategy-source", "filing"],
    }, "dual_outcome_contract_sha256")
    residual = compile_direct_strategy_expectation_residual(
        tmp_path, candidate=candidate, quality=quality,
        dual_outcome_contract=dual, horizon_days=365,
    )
    assert residual["incremental_horizon_payoff"] > 0
    assert residual["translation"]["causal_effect_earned"] is False

    rich_bridge = dict(result)
    rich_envelope = dict(rich_bridge["valuation_envelope"])
    rich_envelope["results"] = [
        {**row, "value": float(row["value"]) + .05}
        if row["result_type"] == "ImpliedReturn" else row
        for row in rich_envelope["results"]
    ]
    rich_envelope.pop("envelope_sha256")
    rich_envelope["envelope_sha256"] = stable_sha256(rich_envelope)
    rich_bridge.update({
        "strategy_program_id": "program-2", "valuation_envelope": rich_envelope,
    })
    rich_bridge.pop("bridge_sha256")
    rich_bridge["bridge_sha256"] = stable_sha256(rich_bridge)
    region_rows = [
        _hashed({"action_id": "program-1", "conditions": []}, "region_sha256"),
        _hashed({"action_id": "program-2", "conditions": []}, "region_sha256"),
    ]
    regions = _hashed({
        "schema": "jaggedthoughts-policy-action-regions-v1",
        "scope_closed": True, "total_over_condition_space": True,
        "deterministic_over_condition_space": True,
        "reachable_action_ids": ["program-1", "program-2"],
        "regions": region_rows,
    }, "policy_action_regions_sha256")
    policy = _hashed({
        "schema": "jaggedthoughts-company-contingent-policy-v1",
        "company_id": "ACME", "policy_id": "scale-or-protect",
        "frozen_at": epoch,
        "policy_action_regions": regions,
        "final_programs": [
            {"program_id": "program-1"}, {"program_id": "program-2"},
        ],
        "feasibility_receipt": {
            "method": "membership_in_z3_closed_static_choice_space",
            "choice_space_sha256": "6" * 64,
        },
    }, "contingent_policy_sha256")
    policy_frontier = dict(frontier)
    policy_frontier["contingent_policy_catalog"] = [policy]
    policy_frontier["choice_space_certificate"] = {
        "choice_space_sha256": "6" * 64,
    }
    policy_frontier.pop("strategy_frontier_sha256")
    policy_frontier["strategy_frontier_sha256"] = stable_sha256(policy_frontier)
    result = {
        **result,
        "strategy_frontier_sha256": policy_frontier["strategy_frontier_sha256"],
    }
    result.pop("bridge_sha256")
    result["bridge_sha256"] = stable_sha256(result)
    rich_bridge.update({
        "strategy_frontier_sha256": policy_frontier["strategy_frontier_sha256"],
    })
    rich_bridge.pop("bridge_sha256")
    rich_bridge["bridge_sha256"] = stable_sha256(rich_bridge)
    sourced = lambda value: {
        "value": value, "unit": "horizon_active_return_decimal",
        "available_at": epoch, "source_refs": ["filing"],
    }
    branches = {
        "program-1": {"valuation_bridge": result,
                      "implementation_cost": sourced(.01),
                      "downside_active_return": sourced(-.10)},
        "program-2": {"valuation_bridge": rich_bridge,
                      "implementation_cost": sourced(.02),
                      "downside_active_return": sourced(-.15)},
    }
    probability = lambda low, high: {
        "low": low, "high": high, "unit": "probability_decimal",
        "available_at": epoch, "source_refs": ["filing"],
    }
    frontier = compile_contingent_policy_payoff_frontier(
        strategy_frontier=policy_frontier, contingent_policy=policy,
        branch_valuations=branches,
        region_probability_intervals={
            region_rows[0]["region_sha256"]: probability(.2, .6),
            region_rows[1]["region_sha256"]: probability(.4, .8),
        },
        control_horizon_return=sourced(.01), horizon_days=365,
        information_cutoff=epoch,
    )
    assert len(frontier["branch_hurdles"]) == 2
    assert frontier["price_implied_hurdle_mixture_bounds"]["low"] <= (
        frontier["price_implied_hurdle_mixture_bounds"]["high"]
    )
    assert frontier["choice_space_sha256"] == "6" * 64
    assert frontier["expected_realized_return_claim"] is False
    assert frontier["quantity_identity"].endswith("not_expected_realized_return")
    assert not frontier["rank_authority"] and not frontier["capital_authority"]
