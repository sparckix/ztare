from copy import deepcopy

from ztare.investment.household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    HOUSEHOLD_MANDATE_SCHEMA,
    compile_capital_market_basis,
    compile_household_allocation_frontier,
    compile_household_mandate,
)
from ztare.investment.household_goal_surface import compile_household_goal_surface


def test_household_frontier_is_goal_and_scenario_monotone() -> None:
    mandate = compile_household_mandate({
        "schema": HOUSEHOLD_MANDATE_SCHEMA,
        "mandate_id": "household", "as_of": "2026-01-01T00:00:00Z",
        "base_currency": "USD", "fx_to_base": {},
        "person": {"age": 35}, "tax_residence": "US",
        "assets": [
            {"asset_id": "brokerage", "kind": "brokerage", "value": 500_000,
             "currency": "USD", "liquid": True, "investable": True, "source_ref": "account"},
            {"asset_id": "home", "kind": "property", "value": 600_000,
             "currency": "USD", "liquid": False, "investable": False, "source_ref": "appraisal"},
        ],
        "liabilities": [{
            "liability_id": "mortgage", "kind": "mortgage", "balance": 200_000,
            "currency": "USD", "annual_rate": 0.02, "rate_kind": "fixed",
            "years_remaining": 20, "secured_by_asset_id": "home", "source_ref": "statement",
        }],
        "accounts": [{"account_id": "brokerage", "tax_class": "taxable"}],
        "tax_policy": {"annual_return_haircuts": {
            "cash": 0.005, "bonds": 0.0075, "equity": 0.01,
        }},
        "goal": {"target_wealth": 1_200_000, "currency": "USD", "horizon_years": 10,
                 "annual_contribution": 30_000, "wealth_basis": "investable_wealth",
                 "minimum_success_probability": 0.7},
        "constraints": {"liquidity_reserve": 50_000, "max_risky_weight": 0.75,
                        "max_one_year_loss": 0.35, "max_effective_equity_exposure": 0.75,
                        "weight_step": 0.25},
        "human_capital": {"annual_net_income": 180_000, "currency": "USD", "years": 10,
                          "annual_growth": 0.01, "discount_rate": 0.04,
                          "market_beta": 0.3, "source_ref": "payroll"},
        "source_refs": ["account", "appraisal", "statement", "payroll"],
    })
    raw_basis = {
        "schema": CAPITAL_MARKET_BASIS_SCHEMA, "basis_id": "basis",
        "as_of": mandate["as_of"],
        "asset_classes": [
            {"asset_id": "cash", "risk_bucket": "cash", "currency": "USD",
             "volatility": 0.0, "minimum_weight": 0, "maximum_weight": 1},
            {"asset_id": "bonds", "risk_bucket": "defensive", "currency": "USD",
             "volatility": 0.07, "minimum_weight": 0, "maximum_weight": 1},
            {"asset_id": "equity", "risk_bucket": "risky", "currency": "USD",
             "volatility": 0.18, "minimum_weight": 0, "maximum_weight": 0.75},
        ],
        "correlations": {
            "cash": {"bonds": 0, "equity": 0},
            "bonds": {"cash": 0, "equity": 0.2},
            "equity": {"cash": 0, "bonds": 0.2},
        },
        "return_scenarios": [{"scenario_id": "cautious",
                              "expected_returns": {"cash": 0.025, "bonds": 0.035, "equity": 0.06},
                              "source_refs": ["public-basis"]}],
        "source_refs": ["public-basis"],
    }
    basis = compile_capital_market_basis(raw_basis)
    first = compile_household_allocation_frontier(
        mandate=mandate, capital_market_basis=basis, simulation_paths=128,
    )

    optimistic = deepcopy(raw_basis)
    optimistic["return_scenarios"].append({
        "scenario_id": "optimistic",
        "expected_returns": {"cash": 0.03, "bonds": 0.06, "equity": 0.12},
        "source_refs": ["public-basis"],
    })
    second = compile_household_allocation_frontier(
        mandate=mandate,
        capital_market_basis=compile_capital_market_basis(optimistic),
        simulation_paths=128,
    )

    assert first["status"] == "paper_policy_ready"
    assert first["selected_policy"]["weights"] == second["selected_policy"]["weights"]
    assert first["selected_policy"]["robust_goal_probability"] == second["selected_policy"]["robust_goal_probability"]
    return_closure = second["return_model_decision_closure"]
    assert return_closure["world_count"] == 2
    assert {
        row["scenario_id"] for row in return_closure["model_worlds"]
    } == {"cautious", "optimistic"}
    assert return_closure["scope_exhausted"] is True
    assert return_closure["probability_interpretation"] is False
    assert return_closure["goal_probability_resolution"] == 1 / 128
    assert return_closure["goal_probability_calibrated"] is False
    assert return_closure["capital_authority"] is False
    assert set(first["anchor_policies"]) == {
        "goal_selected", "minimum_variance", "maximum_robust_sharpe", "risk_budget",
    }
    assert [row["rival_id"] for row in first["policy_rivals"]] == list(
        first["anchor_policies"]
    )
    assert all(
        row["program"]["program_id"] == first["anchor_policies"][row["rival_id"]]
        and set(row["program"]["weights"]) == {"cash", "bonds", "equity"}
        for row in first["policy_rivals"]
    )
    assert sum(row["selected"] for row in first["policy_rivals"]) >= 1
    assert first["capital_authority"] is first["brokerage_authority"] is False
    assert first["simulation"]["goal_probability_calibrated"] is False


def test_partial_household_intake_emits_hurdles_without_inventing_net_worth() -> None:
    surface = compile_household_goal_surface({
        "schema": "jaggedthoughts-household-capital-intake-v1",
        "goal": {"target_net_worth": 10_000_000, "currency": "unresolved"},
        "assets": [
            {"asset_id": "eur", "kind": "liquidity", "value": 240_000, "currency": "EUR"},
            {"asset_id": "usd", "kind": "liquidity", "value": 30_000, "currency": "USD"},
            {"asset_id": "home", "kind": "property", "value": "unresolved", "currency": "EUR"},
        ],
        "liabilities": [
            {"liability_id": "family", "balance": 72_000, "currency": "EUR"},
            {"liability_id": "unknown", "balance": 190_000, "currency": "unresolved"},
        ],
        "known_but_not_yet_bound": ["age", "goal_currency_and_horizon"],
    }, base_currency="USD", fx_to_base={"EUR": 1.1}, fx_source_refs=("ecb-fx",),
       as_of="2026-01-01T00:00:00Z",
       horizon_grid=(20,), contribution_grid=(100_000,))

    assert surface["known_balance_sheet"]["known_investable_liquidity_base"] == 294_000
    assert surface["known_balance_sheet"]["complete"] is False
    assert surface["known_balance_sheet"]["net_worth_base"] is None
    assert surface["known_balance_sheet"]["known_net_position_base"] == 214_800
    assert 0 < surface["hurdle_matrix"][0]["required_constant_nominal_return"] < 1
    assert surface["goal"]["currency_resolved"] is False
    assert surface["goal"]["nonportfolio_terminal_value_included"] is False
    assert surface["fx_source_refs"] == ["ecb-fx"]
