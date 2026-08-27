from ztare.common.equivariance import stable_sha256
from ztare.investment.discovery import DISCOVERY_CANDIDATE_SCHEMA, DISCOVERY_RUN_SCHEMA
from ztare.investment.factor_analysis import FACTOR_ANALYSIS_SCHEMA
from ztare.investment.underwriting_adapter import compile_underwriting_opportunity_index


def test_underwriting_adapter_keeps_erp_spreads_and_security_return_distinct():
    as_of = "2026-01-02T00:00:00Z"
    factor = {
        "schema": FACTOR_ANALYSIS_SCHEMA, "analysis_sha256": "f" * 64,
        "candidate_entity_id": "ABC", "factors": [{"expected_annual_premium": 0.0}],
        "coefficients": {"betas": {"market": 0.8}}, "fit": {"leave_one_out_r2": 0.5},
        "historical": {"residual_alpha_annualized": 0.01},
        "assumption_implied": {"return_without_residual_alpha": 0.0},
        "source_observation_ids": ["price-abc", "price-spy"], "source_refs": ["prices"],
    }
    candidate_body = {
        "schema": DISCOVERY_CANDIDATE_SCHEMA, "candidate_id": "equity:ABC",
        "entity_id": "ABC", "entity_kind": "public_equity", "as_of": as_of,
        "rank": 1, "rank_score": 0.8, "metrics": {}, "source_refs": ["filing", "prices"],
        "valuation": {"envelope_sha256": "v" * 64},
        "beta_receipt": {"status": "estimated", "analysis": factor},
    }
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}
    rank_input_body = {
        "schema": "jaggedthoughts-rank-program-input-v1",
        "discovery_run_id": "discovery-test",
        "lanes": [{"candidates": [{
            "candidate_id": "equity:ABC", "rank_program_eligible": True,
        }]}],
    }
    run_body = {
        "schema": DISCOVERY_RUN_SCHEMA, "run_id": "discovery-test",
        "completed_at": as_of, "candidates": [candidate],
        "rank_program_input": {
            **rank_input_body,
            "rank_program_input_sha256": stable_sha256(rank_input_body),
        },
    }
    discovery = {**run_body, "run_sha256": stable_sha256(run_body)}
    valuation = {
        "schema": "jaggedthoughts-valuation-envelope-v1", "envelope_sha256": "v" * 64,
        "entity_id": "ABC", "evidence_epoch": as_of,
        "summary": {
            "implied_growth_median": 0.01, "earnings_power_margin_of_safety": 0.2,
            "implied_required_return_median": 0.11, "price_implied_excess_return": 0.07,
        },
        "assumptions": [
            {"assumption_type": "RiskFreeRate", "value": 0.04, "source_refs": ["treasury"]},
            {"assumption_type": "EquityRiskPremium", "value": 0.05, "source_refs": ["erp"]},
        ],
    }
    market = {
        "schema": "jaggedthoughts-market-state-snapshot-artifact-v2", "snapshot_artifact_sha256": "m" * 64,
        "point_in_time_snapshot": {
            "as_of": "2026-01-01T00:00:00Z",
            "observations": [
                {"metric_id": "implied_equity_risk_premium", "value": 0.05, "observation_id": "erp-1", "source_ref": "erp"},
                {"metric_id": "risk_free_rate", "value": 0.04, "observation_id": "rf-1", "source_ref": "treasury"},
                {"metric_id": "sp500_forward_earnings_yield", "value": 0.045, "observation_id": "ey-1", "source_ref": "index"},
                {"metric_id": "treasury_10y_real_yield", "value": 0.02, "observation_id": "tips-1", "source_ref": "tips"},
                {"metric_id": "breakeven_inflation_10y", "value": 0.02, "observation_id": "bei-1", "source_ref": "breakeven"},
            ],
        },
        "state": {
            "implied_nominal_equity_return": 0.09,
            "valuation_spreads": {"forward_earnings_yield_minus_nominal_10y": 0.005},
        },
    }
    index = compile_underwriting_opportunity_index(
        discovery, market, valuation_artifacts={"equity:ABC": valuation},
        conditional_payoff_artifacts={"equity:ABC": _conditional_grid(candidate)},
        payoff_forecast_results={"equity:ABC": _payoff_forecast(candidate)},
    )
    row = index["candidates"][0]

    assert row["ranking"]["eligible"] is True
    assert row["ranking"]["underwriting_coordinates_complete"] is True
    assert row["ranking"]["research_priority_is_expected_return"] is False
    assert row["factor"]["source_observation_count"] == 2
    assert row["factor"]["source_observation_ids_sha256"] == stable_sha256([
        "price-abc", "price-spy",
    ])
    assert "source_observation_ids" not in row["factor"]
    assert row["valuation"]["return_coordinates"][1]["value"] == 0.07
    assert index["market_context"]["primary_cash_flow_implied_erp"]["value"] == 0.05
    assert index["market_context"]["yield_spread_diagnostics"][0]["value"] == 0.005
    assert index["market_context"]["yield_spread_diagnostics"][0]["input_observation_ids"] == [
        "ey-1", "tips-1", "bei-1",
    ]
    assert row["conditional_payoff_analysis"]["identity"] == "conditional_scenario_price_consistency"
    assert row["conditional_payoff_analysis"]["market_state_prices_identified"] is False
    assert index["conditional_payoff_aware_count"] == 1
    assert index["forecast_return_aware_count"] == 1
    assert row["payoff_forecast"]["expected_active_return_interval"] == {
        "low": -0.2, "high": 0.3,
    }
    assert row["state_price_aware"] is False


def _conditional_grid(candidate):
    body = {
        "schema": "jaggedthoughts-modeled-payoff-grid-v1",
        "entity_id": candidate["entity_id"],
        "scope_boundary": "conditional_model_grid_not_physical_world_distribution",
        "compiled_proposal": {
            "candidate_sha256": candidate["candidate_sha256"],
            "state_price_result": {
                "no_arbitrage_certificate": True,
                "market_complete": False,
                "result_sha256": "r" * 64,
            },
        },
    }
    return {**body, "modeled_grid_sha256": stable_sha256(body)}


def _payoff_forecast(candidate):
    body = {
        "schema": "jaggedthoughts-candidate-payoff-forecast-result-v1",
        "contract_sha256": "c" * 64, "entity_id": candidate["entity_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "information_cutoff": candidate["as_of"], "horizon_at": "2027-01-02T00:00:00Z",
        "horizon_days": 365, "comparator_entity_id": "SPY",
        "expected_active_return_interval": {"low": -0.2, "high": 0.3},
        "underperformance_probability_interval": {"low": 0.1, "high": 0.6},
        "worst_case_active_return": -0.5,
        "expected_return_identity": "forecast_interval_conditional_on_authored_worlds",
        "market_state_prices_identified": False, "capital_authority": False,
    }
    return {**body, "forecast_result_sha256": stable_sha256(body)}
