import csv
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.golden_store import GoldenStore
from ztare.investment.portfolio_policy import (
    PORTFOLIO_POLICY_RUN_SCHEMA,
    PRIMARY_HORIZON_DAYS,
    _paper_policy_incumbent_routing,
    _policy,
    open_portfolio_policy_tournament,
    portfolio_policy_status,
    settle_portfolio_policy_tournaments,
)


def _write_prices(path: Path, rows: list[tuple[str, str, float, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "observation_id", "entity_id", "metric_id", "value",
            "observed_at", "available_at", "source_ref",
        ])
        writer.writeheader()
        for observation_id, entity_id, value, observed_at, available_at in rows:
            writer.writerow({
                "observation_id": observation_id,
                "entity_id": entity_id,
                "metric_id": "adjusted_price",
                "value": value,
                "observed_at": observed_at,
                "available_at": available_at,
                "source_ref": f"cached:{observation_id}",
            })


def test_settled_incumbent_routing_is_exact_family_and_order_invariant() -> None:
    policies = [
        _policy("cash", "cash", {}, ("book",)),
        _policy("candidate", "ranked", {"AAA": 0.2}, ("book",)),
    ]
    family_body = {
        "schema": "jaggedthoughts-portfolio-policy-trial-family-v1",
        "policy_versions": {"candidate": "8", "cash": "8"},
        "horizon_days": 365, "estimand_role": "primary_patient_capital_policy_evidence",
        "benchmark_id": "SPY", "score_contract_version": "4",
        "return_price_identity": "adjusted_close_total_return_proxy",
        "cost_application": "round_trip_once_in_prospective_return_window",
        "transaction_cost_bps": 10.0, "risk_evaluation_contract_sha256": "r" * 64,
    }
    family = {**family_body, "trial_family_id": stable_sha256(family_body)}
    review_body = {
        "schema": "jaggedthoughts-portfolio-policy-review-v1", "trial_family": family,
        "recommended_policy_id": "candidate",
        "activation_status": "eligible_for_paper_policy_review",
        "settlement_sha256s": [f"{index:064x}" for index in range(8)],
        "automatic_policy_change": False, "capital_authority": False,
    }
    review = {**review_body, "policy_review_sha256": stable_sha256(review_body)}

    left = _paper_policy_incumbent_routing(
        trial_family=family, policies=policies, equivalent_policies=(), reviews=(review,),
    )
    right = _paper_policy_incumbent_routing(
        trial_family=family, policies=reversed(policies), equivalent_policies=(), reviews=(review,),
    )
    changed_body = {**family_body, "benchmark_id": "QQQ"}
    blocked = _paper_policy_incumbent_routing(
        trial_family={**changed_body, "trial_family_id": stable_sha256(changed_body)},
        policies=policies, equivalent_policies=(), reviews=(review,),
    )

    assert left["routing_sha256"] == right["routing_sha256"]
    assert left["status"] == "settled_survivor_incumbent"
    assert left["weights"] == {"AAA": 0.2} and left["capital_authority"] is False
    assert blocked["status"] == "no_eligible_exact_family_survivor"
    assert blocked["weights"] == {}


def test_rank_tickets_are_point_in_time_scored_and_immutably_settled(tmp_path: Path) -> None:
    prices = tmp_path / "data" / "observations.csv"
    history = []
    values = []
    price_a = price_b = 100.0
    for offset in range(380):
        day = date(2024, 12, 18) + timedelta(days=offset)
        price_a *= 1.008 if offset % 2 else 0.994
        price_b *= 1.001 if offset % 5 else 0.9995
        values.append((day.isoformat(), price_a, price_b))
    scale_a, scale_b = 100 / values[-1][1], 50 / values[-1][2]
    for day, value_a, value_b in values:
        for entity_id, value in (("AAA", value_a * scale_a), ("BBB", value_b * scale_b)):
            history.append((
                f"{entity_id.lower()}-{day}", entity_id, value,
                f"{day}T00:00:00Z", f"{day}T01:00:00Z",
            ))
    outcome_path = []
    value_a, value_b = 100.0, 50.0
    for offset in range(1, 365):
        day = date(2026, 1, 2) + timedelta(days=offset)
        value_a *= 1.0015 if offset % 7 else 0.995
        value_b *= 1.0002 if offset % 11 else 0.999
        for entity_id, value in (("AAA", value_a), ("BBB", value_b)):
            outcome_path.append((
                f"{entity_id.lower()}-path-{day}", entity_id, value,
                f"{day}T00:00:00Z", f"{day}T01:00:00Z",
            ))
    _write_prices(prices, history + [
        ("a-open", "AAA", 100, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ("b-open", "BBB", 50, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ("c-open", "CCC", 80, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ("d-open", "DDD", 40, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ("spy-open", "SPY", 400, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ("a-entry", "AAA", 100, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
        ("b-entry", "BBB", 50, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
        ("c-entry", "CCC", 80, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
        ("d-entry", "DDD", 40, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
        ("spy-entry", "SPY", 400, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
        # Observed before issue but unavailable until afterward: it must not leak into the ticket.
        ("a-late", "AAA", 1_000, "2026-01-01T12:00:00Z", "2026-01-03T00:00:00Z"),
    ] + outcome_path + [
        ("a-end", "AAA", 120, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
        ("b-end", "BBB", 52.5, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
        ("c-end", "CCC", 88, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
        ("d-end", "DDD", 41, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
        ("spy-end", "SPY", 440, "2027-01-02T00:00:00Z", "2027-01-03T00:00:00Z"),
    ])
    candidates = [
        {
            "candidate_id": "equity:AAA", "candidate_sha256": "a" * 64,
            "entity_id": "AAA", "entity_kind": "public_equity", "screen_status": "qualified",
            "research_priority_score": 3.0, "learned_research_priority_score": 3.5,
            "economic_coordinates": {"factor_implied_return": 0.04},
            "law_policy_influence": {
                "contributions": [{"law_key": "strategy_durability_v1"}],
            },
            "research": {"research_prompt": "Test the strategy durability mechanism."},
            "source_refs": ["filing:AAA"],
        },
        {
            "candidate_id": "fund:BBB", "candidate_sha256": "b" * 64,
            "entity_id": "BBB", "entity_kind": "public_equity", "screen_status": "qualified",
            "research_priority_score": 2.0, "learned_research_priority_score": 1.5,
            "economic_coordinates": {"factor_implied_return": 0.09},
            "law_policy_influence": {"contributions": []},
            "research": {"research_prompt": "Test factor capture after fees."},
            "source_refs": ["issuer:BBB"],
        },
        {
            "candidate_id": "fund:CCC", "candidate_sha256": "e" * 64,
            "entity_id": "CCC", "entity_kind": "public_fund", "screen_status": "qualified",
            "research_priority_score": 1.0, "learned_research_priority_score": 1.0,
            "economic_coordinates": {"factor_implied_return": 0.03},
            "law_policy_influence": {"contributions": []},
            "research": {"research_prompt": "Test the fund sleeve against cash."},
            "source_refs": ["issuer:CCC"],
        },
    ]
    book_body = {
        "schema": "jaggedthoughts-opportunity-book-v1",
        "book_id": "book-1",
        "generated_at": "2026-01-02T00:00:00Z",
        "candidates": candidates,
        "law_policy_influence": {"influence_sha256": "c" * 64},
        "source_refs": ["discovery:1"],
        "authority": "paper_shadow",
        "capital_authority": False,
    }
    book = {**book_body, "book_sha256": stable_sha256(book_body)}
    fund_input_body = {
        "schema": "jaggedthoughts-fund-program-tournament-input-v1",
        "as_of": "2026-01-02T00:00:00Z",
        "sleeves": [{
            "sleeve_id": "us_equity",
            "programs": [{
                "program_id": f"fund-sleeve:us:{entity}",
                "program_sha256": digest * 64,
                "entity_id": entity,
                "same_information_core_ready": True,
                "ranking_coordinates": {
                    "factor_implied_return_less_expense": factor,
                    "aggregate_earnings_power_margin": earnings,
                },
            } for entity, digest, factor, earnings in (
                ("CCC", "e", 0.03, 0.10), ("DDD", "f", 0.01, 0.20),
            )],
        }],
        "selection_claims": [
            {
                "claim_id": "factor_net_expense",
                "coordinate": "factor_implied_return_less_expense",
                "semantics": "factor_assumption_control_not_expected_alpha",
            },
            {
                "claim_id": "aggregate_earnings_power",
                "coordinate": "aggregate_earnings_power_margin",
                "semantics": "aggregate_expectations_proxy_not_holdings_underwriting",
            },
        ],
    }
    fund_input = {
        **fund_input_body,
        "tournament_input_sha256": stable_sha256(fund_input_body),
    }
    admission_rows = []
    for entity, expected, downside in (("AAA", 0.08, 0.20), ("BBB", 0.04, 0.10)):
        claim_body = {
            "schema": "jaggedthoughts-prospective-active-return-claim-v1",
            "estimand": "annualized_active_return",
            "subject_entity_id": entity,
            "benchmark_entity_id": "SPY",
            "value": expected,
            "horizon_days": PRIMARY_HORIZON_DAYS,
            "underperformance_probability": 0.35,
            "sealed_at": "2026-01-01T00:00:00Z",
            "forecast_sha256": "1" * 64,
            "run_sha256": "2" * 64,
            "packet_sha256": "3" * 64,
            "paper_decision_sha256": "4" * 64,
            "candidate_sha256": "5" * 64,
            "dossier_sha256": "6" * 64,
            "authority": "prospective_shadow",
            "capital_authority": False,
        }
        admission_body = {
            "schema": "jaggedthoughts-instrument-portfolio-admission-v1",
            "subject": {"subject_id": entity, "entity_kind": "public_equity"},
            "portfolio_projection": {
                "expected_active_return_claims": [{
                    **claim_body, "claim_sha256": stable_sha256(claim_body),
                }],
                "downside_risk": downside,
            },
            "eligibility": {"research_paper_portfolio_candidate": True},
        }
        admission_rows.append({
            **admission_body, "admission_sha256": stable_sha256(admission_body),
        })
    fund_claim_body = {
        "schema": "jaggedthoughts-prospective-active-return-claim-v1",
        "estimand": "annualized_active_return",
        "subject_entity_id": "CCC",
        "benchmark_entity_id": "SPY",
        "value": 0.03,
        "horizon_days": PRIMARY_HORIZON_DAYS,
        "underperformance_probability": 0.40,
        "sealed_at": "2026-01-01T00:00:00Z",
        "forecast_sha256": "7" * 64,
        "run_sha256": "8" * 64,
        "packet_sha256": "9" * 64,
        "paper_decision_sha256": "a" * 64,
        "candidate_sha256": "b" * 64,
        "dossier_sha256": "c" * 64,
        "authority": "prospective_shadow",
        "capital_authority": False,
    }
    fund_admission_body = {
        "schema": "jaggedthoughts-instrument-portfolio-admission-v1",
        "subject": {
            "subject_id": "CCC", "entity_kind": "public_fund",
            "implementation_sleeve_id": "us_equity",
        },
        "portfolio_projection": {
            "expected_active_return_claims": [{
                **fund_claim_body, "claim_sha256": stable_sha256(fund_claim_body),
            }],
            "downside_risk": 0.18,
            "target_weight_cap": 0.10,
        },
        "eligibility": {"research_paper_portfolio_candidate": True},
    }
    admission_rows.append({
        **fund_admission_body,
        "admission_sha256": stable_sha256(fund_admission_body),
    })
    admissions_body = {
        "schema": "jaggedthoughts-workspace-instrument-portfolio-admissions-v1",
        "compiled_at": "2026-01-02T00:00:00Z",
        "admissions": admission_rows,
    }
    admissions = {
        **admissions_body,
        "workspace_admissions_sha256": stable_sha256(admissions_body),
    }
    store_path = tmp_path / "state" / "golden.sqlite3"
    legacy_body = {
        "schema": PORTFOLIO_POLICY_RUN_SCHEMA,
        "run_id": "portfolio-policy-legacy",
        "opened_at": "2026-01-01T00:00:00Z",
        "end_at": "2026-04-01T00:00:00Z",
        "horizon_days": 90,
        "settlement_contract": {
            "score_contract_version": "2",
            "prospective_return_window": {
                "price_identity": "source_bound_cached_total_price_observation",
            },
        },
    }
    legacy = {**legacy_body, "run_sha256": stable_sha256(legacy_body)}
    legacy_path = tmp_path / "portfolio_policy" / "runs" / "portfolio-policy-legacy.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
    bound_body = {**legacy_body, "run_id": "portfolio-policy-bound-legacy"}
    bound = {**bound_body, "run_sha256": stable_sha256(bound_body)}
    bound_path = legacy_path.with_name("portfolio-policy-bound-legacy.json")
    bound_path.write_text(json.dumps(bound), encoding="utf-8")
    bound_window = tmp_path / "portfolio_policy/return_windows/portfolio-policy-bound-legacy.json"
    bound_window.parent.mkdir(parents=True)
    bound_window.write_text(json.dumps({"binding": {"status": "bound"}}), encoding="utf-8")

    run = open_portfolio_policy_tournament(
        tmp_path, owner="paper", store_path=store_path, opportunity_book=book,
        generated_at="2026-01-02T00:00:00Z", sealed_at="2026-01-02T00:00:00Z",
        horizon_days=PRIMARY_HORIZON_DAYS,
        max_position_weight=0.30,
        fund_program_tournament_input=fund_input,
        instrument_portfolio_admissions=admissions,
    )

    assert run["status"] == "pending_outcome"
    assert run["run_id"] != "portfolio-policy-bound-legacy"
    assert run["estimand_role"] == "primary_patient_capital_policy_evidence"
    assert set(run["trial_family"]["policy_versions"].values()) == {"8"}
    assert run["settlement_contract"]["score_contract_version"] == "4"
    assert run["settlement_contract"]["cost_application"] == (
        "round_trip_once_in_prospective_return_window"
    )
    assert run["settlement_contract"]["prospective_return_window"]["price_identity"] == (
        "adjusted_close_total_return_proxy"
    )
    assert run["superseded_run_ids"] == ["portfolio-policy-legacy"]
    bound_path.unlink()
    bound_window.unlink()
    assert run["allocation_universe"] == {
        "identity": "public_equity_satellite",
        "entity_ids": ["AAA", "BBB"],
        "fund_boundary": (
            "one_fund_at_a_time_capped_shadow_sleeve_challengers;"
            "no_cross_fund_or_equity_fund_mixing"
        ),
        "fund_shadow_policy_ids": ["fund_admission:us_equity:CCC"],
        "household_boundary": "broad_sleeve_allocation_owned_by_household_mandate",
    }
    equity_equal = next(
        row for row in run["policies"] if row["policy_id"] == "equity_equal_weight"
    )
    assert equity_equal["weights"] == {"AAA": 0.25, "BBB": 0.25}
    admission_policy = next(
        row for row in run["policies"]
        if row["policy_id"] == "equity_admission_prospective_active_return"
    )
    assert admission_policy["weights"] == pytest.approx({"AAA": 0.30, "BBB": 1 / 6})
    minimum_variance = next(
        row for row in run["policies"] if row["policy_id"] == "equity_minimum_variance"
    )
    assert minimum_variance["expected_return_claim"] is False
    assert minimum_variance["evaluation_role"] == "diagnostic_risk_comparator"
    assert minimum_variance["promotion_eligible_under_current_score_contract"] is False
    assert sum(minimum_variance["weights"].values()) == pytest.approx(0.50)
    assert max(minimum_variance["weights"].values()) <= 0.30 + 1e-12
    covariance = run["risk_model"]["return_covariance"]
    assert covariance["expected_return_claim"] is False
    assert covariance["historical_mean_used_as_forecast"] is False
    evidence = run["risk_model"]["source_evidence"]
    assert evidence["return_covariance_sha256"] == covariance["return_covariance_sha256"]
    assert len(evidence["point_in_time_observation_tuples_sha256"]) == 64
    assert run["settlement_contract"]["risk_comparator_promotion_contract"] == {
        "policy_id": "equity_minimum_variance",
        "current_status": "diagnostic_only",
        "required_unscored_outcomes": [
            "realized_volatility", "maximum_drawdown", "turnover",
        ],
    }
    assert run["risk_challenger"]["method"] == (
        "chronological_validation_selected_ridge_minimum_variance"
    )
    risk_contract = run["settlement_contract"]["risk_challenger_evaluation"]
    assert (
        risk_contract["status"] == "enabled"
        and risk_contract["after_cost_utility"]["risk_aversion"] == 3.0
        and risk_contract["minimum_independent_blocks"] == 8
        and len(risk_contract["risk_evaluation_contract_sha256"]) == 64
        and risk_contract["capital_authority"] is False
    )
    assert "equity_walk_forward_ridge_minimum_variance" in {
        *(row["policy_id"] for row in run["policies"]),
        *(row["policy_id"] for row in run["equivalent_policies"]),
    }
    matrix = covariance["covariance_matrix"]
    entity_ids = covariance["entity_ids"]

    def variance(policy: dict) -> float:
        weights = [policy["weights"].get(entity_id, 0.0) for entity_id in entity_ids]
        return sum(
            weights[left] * matrix[left][right] * weights[right]
            for left in range(len(weights)) for right in range(len(weights))
        )

    assert variance(minimum_variance) <= variance(equity_equal) + 1e-12
    fund_policy = next(
        row for row in run["policies"]
        if row["policy_id"] == "fund_admission:us_equity:CCC"
    )
    assert fund_policy["weights"] == {"CCC": 0.10}
    assert fund_policy["evaluation_role"] == "fund_sleeve_vs_cash_and_policy_challenger"
    assert fund_policy["promotion_eligible_under_current_score_contract"] is False
    fund_attribution = next(
        row for row in run["attribution_contract"]["comparisons"]
        if row["policy_id"] == fund_policy["policy_id"]
    )
    assert fund_attribution["reference_policy_id"] == "cash_control"
    assert all("DDD" not in row["weights"] for row in run["policies"])
    assert all(
        {candidate["entity_kind"] for candidate in ticket["ranked_candidates"]}
        == ({"public_fund"} if ticket["claim_id"].startswith("fund::") else {"public_equity"})
        for ticket in run["ranking_tickets"]
    )
    assert run["settlement_contract"]["prospective_return_window"]["sealed_at"] == run["sealed_at"]
    assert run["universe"][0]["start"]["price"] == 100
    assert {row["claim_id"] for row in run["ranking_tickets"]} == {
        "discovery_priority", "learned_law_priority", "factor_implied_return_control",
        "fund::us_equity::factor_net_expense",
        "fund::us_equity::aggregate_earnings_power",
    }
    assert len(run["fund_program_universe"]) == 2
    assert all("weight" not in row for row in run["fund_program_universe"])
    assert all(row["status"] == "unresolved" for row in run["ranking_tickets"])
    assert not (tmp_path / "portfolio_policy" / "settlements").exists()

    early = settle_portfolio_policy_tournaments(
        tmp_path, owner="paper", store_path=store_path, as_of="2026-06-01T00:00:00Z",
    )
    assert early["settled"] == [] and early["pending"][0]["reason"] == "horizon_not_reached"

    settlement_result = settle_portfolio_policy_tournaments(
        tmp_path, owner="paper", store_path=store_path, as_of="2027-01-03T00:00:00Z",
    )
    settled = settlement_result["settled"][0]
    assert settled["actual_returns"]["AAA"] == pytest.approx(0.1976012)
    sensitivity = settled["transaction_cost_sensitivity"]
    sensitivity_by_policy = {row["policy_id"]: row for row in sensitivity["policies"]}
    settled_scores = {row["policy_id"]: row for row in settled["policy_scores"]}
    assert (
        sensitivity["transaction_cost_bps_grid"] == [0.0, 5.0, 10.0, 25.0, 50.0]
        and sensitivity["ordering"]["comparable_policy_count"] == len(run["policies"])
        and all(len(row["points"]) == 5 for row in sensitivity_by_policy.values())
        and all("break_even_bps_vs_benchmark" in row for row in sensitivity_by_policy.values())
        and all(
            sensitivity_by_policy[policy["policy_id"]]["turnover_basis"]["round_trip_weight"] == pytest.approx(
                2.0 * sum(policy["weights"].values())
            )
            for policy in run["policies"]
        )
        and all(
            next(point for point in row["points"] if point["transaction_cost_bps"] == 10.0)["net_return"]
            == pytest.approx(settled_scores[policy_id]["portfolio_return_after_cost"])
            for policy_id, row in sensitivity_by_policy.items()
        )
    )
    risk_evaluation = settled["risk_challenger_evaluation"]
    risk_metrics = {
        row["policy_id"]: row for row in risk_evaluation["policy_metrics"]
    }
    assert (
        risk_evaluation["status"] == "settled"
        and risk_evaluation["path_evidence"]["synchronized_observation_count"] == 366
        and set(risk_metrics) == {
            "equity_minimum_variance",
            "equity_walk_forward_ridge_minimum_variance",
        }
        and all(row["realized_volatility"] >= 0 for row in risk_metrics.values())
        and all(row["maximum_drawdown"] <= 0 for row in risk_metrics.values())
        and all(row["round_trip_turnover"] == pytest.approx(1.0) for row in risk_metrics.values())
        and all(
            row["terminal_wealth"]
            == pytest.approx(1.0 + settled_scores[policy_id]["portfolio_return_after_cost"])
            for policy_id, row in risk_metrics.items()
        )
        and risk_evaluation["capital_authority"] is False
    )
    risk_review = settlement_result["policy_reviews"][0]["risk_challenger_evaluation"]
    assert (
        risk_review["status"] == "collecting_independent_blocks"
        and risk_review["settled_independent_block_count"] == 1
        and risk_review["minimum_independent_blocks"] == 8
        and risk_review["automatic_policy_change"] is False
        and risk_review["capital_authority"] is False
    )
    scores = {row["claim_id"]: row for row in settled["ranking_scores"]}
    assert scores["discovery_priority"]["rank_calibration"]["value"] == 0
    assert scores["discovery_priority"]["regret"]["value"] == 0
    assert scores["factor_implied_return_control"]["rank_calibration"]["value"] == 1
    assert scores["factor_implied_return_control"]["regret"]["value"] == pytest.approx(
        0.14970015
    )
    assert scores["discovery_priority"]["comparison_to_factor_control"]["top_1_regret_delta"] == pytest.approx(
        -0.14970015
    )
    assert scores["fund::us_equity::factor_net_expense"]["regret"]["value"] == 0
    assert "comparison_to_factor_control" not in scores[
        "fund::us_equity::factor_net_expense"
    ]

    # A later observation cannot rewrite the first settlement.
    original_hash = settled["settlement_sha256"]
    with prices.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow([
            "a-revision", "AAA", "adjusted_price", 10, "2027-01-05T00:00:00Z",
            "2027-01-05T01:00:00Z", "cached:a-revision",
        ])
    replay = settle_portfolio_policy_tournaments(
        tmp_path, owner="paper", store_path=store_path, as_of="2027-01-06T00:00:00Z",
    )["settled"][0]
    assert replay["settlement_sha256"] == original_hash
    status = portfolio_policy_status(tmp_path)
    assert status["primary_horizon_days"] == PRIMARY_HORIZON_DAYS
    assert status["eligible_run_count"] == 1
    assert status["superseded_run_count"] == 1
    assert status["latest_run"]["run_id"] == run["run_id"]
    assert status["scoreboard"]["ranking_claims"]
    assert GoldenStore(store_path).verify()["ok"] is True
