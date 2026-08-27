from ztare.common.equivariance import stable_sha256
from ztare.investment.state_price_authoring import (
    DECLARATION_SCHEMA,
    compile_modeled_payoff_grid,
    compile_state_price_proposal,
)


def _inputs():
    assumptions = [
        {"assumption_id": "price", "assumption_type": "MarketPrice", "value": 95.0,
         "unit": "currency/share", "source_refs": ["public:equity"]},
        {"assumption_id": "growth-low", "assumption_type": "ForecastGrowth", "value": 0.0,
         "unit": "decimal", "source_refs": ["scenario:low"]},
        {"assumption_id": "growth-high", "assumption_type": "ForecastGrowth", "value": 0.1,
         "unit": "decimal", "source_refs": ["scenario:high"]},
    ]
    scenarios = [
        {"scenario_id": "low", "mechanism_id": "growth", "assumption_ids": ["growth-low"],
         "source_refs": ["scenario:low"]},
        {"scenario_id": "high", "mechanism_id": "growth", "assumption_ids": ["growth-high"],
         "source_refs": ["scenario:high"]},
    ]
    results = [
        {"program_id": state, "result_sha256": f"result:{state}", "result_type": "IntrinsicValue",
         "value": value, "unit": "currency/share", "assumption_ids": [f"growth-{state}"],
         "scenario_ids": [state]} for state, value in (("low", 80.0), ("high", 120.0))
    ]
    valuation_body = {
        "schema": "jaggedthoughts-valuation-envelope-v1", "entity_id": "ACME",
        "evidence_epoch": "2026-01-02T00:00:00Z", "assumptions": assumptions,
        "scenarios": scenarios, "results": results,
    }
    valuation = {**valuation_body, "envelope_sha256": stable_sha256(valuation_body)}
    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1", "entity_id": "ACME",
        "entity_kind": "public_equity", "as_of": "2026-01-02T00:00:00Z",
        "valuation": {"envelope_sha256": valuation["envelope_sha256"]},
    }
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}
    spot = {
        "observation_id": "spot", "value": 95.0, "unit": "USD",
        "observed_at": "2026-01-01T00:00:00Z", "available_at": "2026-01-02T00:00:00Z",
        "source_ref": "public:equity",
    }
    return candidate, valuation, spot


def test_proposal_keeps_present_values_out_of_payoffs_until_declared():
    candidate, valuation, spot = _inputs()
    draft = compile_state_price_proposal(
        candidate=candidate, valuation=valuation, spot_price_observation=spot,
    )
    assert draft["status"] == "awaiting_payoff_state_declaration"
    assert all(not row["eligible_as_horizon_payoff"] for row in draft["scenario_templates"])

    declaration = {
        "schema": DECLARATION_SCHEMA, "entity_id": "ACME",
        "candidate_sha256": candidate["candidate_sha256"],
        "valuation_envelope_sha256": valuation["envelope_sha256"],
        "horizon_at": "2027-01-02T00:00:00Z", "exhaustive_within_declared_scope": True,
        "exhaustiveness_scope": "two authored business states",
        "exhaustiveness_source_refs": ["operator:scenario-scope"],
        "states": [
            {"state_id": "down", "valuation_scenario_id": "low", "description": "low case",
             "equity_payoff_at_horizon": 80.0, "payoff_source_refs": ["operator:low-payoff"]},
            {"state_id": "up", "valuation_scenario_id": "high", "description": "high case",
             "equity_payoff_at_horizon": 120.0, "payoff_source_refs": ["operator:high-payoff"]},
        ],
        "numeraire_asset": {
            "asset_id": "treasury", "payoff_source_refs": ["treasury:terms"],
            "price_observation": {"observation_id": "treasury-price", "value": 0.95, "unit": "USD",
                "observed_at": "2026-01-01T00:00:00Z", "available_at": "2026-01-02T00:00:00Z",
                "source_ref": "treasury:price"},
        },
    }
    compiled = compile_state_price_proposal(
        candidate=candidate, valuation=valuation, spot_price_observation=spot, declaration=declaration,
    )
    assert compiled["state_price_result"]["no_arbitrage_certificate"] is True
    assert compiled["state_price_result"]["stochastic_discount_kernel"] is None
    assert compiled["capital_authority"] is False


def test_modeled_grid_derives_future_payoffs_but_not_physical_probabilities():
    candidate, valuation, spot = _inputs()
    valuation_body = {key: value for key, value in valuation.items() if key != "envelope_sha256"}
    valuation_body["assumptions"] = [dict(row) for row in valuation_body["assumptions"]]
    valuation_body["assumptions"][0]["value"] = 120.0
    spot = {**spot, "value": 120.0}
    valuation_body["assumptions"] += [
        {"assumption_id": "earnings", "assumption_type": "OwnerEarnings", "value": 10.0,
         "unit": "currency/year", "source_refs": ["filing:earnings"]},
        {"assumption_id": "beta", "assumption_type": "EquityBeta", "value": 1.0,
         "unit": "multiple", "source_refs": ["prices:beta"]},
        {"assumption_id": "erp", "assumption_type": "EquityRiskPremium", "value": 0.04,
         "unit": "decimal", "source_refs": ["market:erp"]},
        {"assumption_id": "rf", "assumption_type": "RiskFreeRate", "value": 0.04,
         "unit": "decimal", "source_refs": ["treasury:yield"]},
        {"assumption_id": "cash", "assumption_type": "ExcessNetCash", "value": 0.0,
         "unit": "currency", "source_refs": ["filing:cash"]},
        {"assumption_id": "shares", "assumption_type": "Shares", "value": 1.0,
         "unit": "shares", "source_refs": ["filing:shares"]},
        {"assumption_id": "horizon", "assumption_type": "Horizon", "value": 10.0,
         "unit": "years", "source_refs": ["policy:horizon"]},
        {"assumption_id": "terminal-low", "assumption_type": "TerminalGrowth", "value": 0.01,
         "unit": "decimal", "source_refs": ["scenario:low"]},
        {"assumption_id": "terminal-high", "assumption_type": "TerminalGrowth", "value": 0.02,
         "unit": "decimal", "source_refs": ["scenario:high"]},
    ]
    valuation_body["scenarios"] = [
        {"scenario_id": "low", "mechanism_id": "growth", "assumption_ids": ["growth-low", "terminal-low"],
         "source_refs": ["scenario:low"]},
        {"scenario_id": "high", "mechanism_id": "growth", "assumption_ids": ["growth-high", "terminal-high"],
         "source_refs": ["scenario:high"]},
    ]
    valuation = {**valuation_body, "envelope_sha256": stable_sha256(valuation_body)}
    candidate_body = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    candidate_body["valuation"] = {"envelope_sha256": valuation["envelope_sha256"]}
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}

    grid = compile_modeled_payoff_grid(
        candidate=candidate, valuation=valuation, spot_price_observation=spot,
    )
    result = grid["compiled_proposal"]["state_price_result"]
    assert result["no_arbitrage_certificate"] is True
    assert result["market_complete"] is True
    assert grid["diagnostics"]["physical_probability_claim"] is False
    assert grid["diagnostics"]["expected_return_claim"] is False
    assert grid["scope_boundary"] == "conditional_model_grid_not_physical_world_distribution"
