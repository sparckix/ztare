from ztare.investment.household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    compile_capital_market_basis,
)
from ztare.investment.household_allocation_scenario import (
    HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA,
    compile_household_allocation_scenario,
)
from ztare.investment.household_goal_surface import compile_household_goal_surface
from ztare.investment.household_mandate_frontier import (
    compile_household_mandate_frontier,
)
from ztare.investment.public_capital_market_basis import PUBLIC_BASIS_ACQUISITION_SCHEMA


def test_planning_scenario_enumerates_without_becoming_operator_policy() -> None:
    surface = compile_household_goal_surface({
        "schema": "jaggedthoughts-household-capital-intake-v1",
        "goal": {"target_net_worth": 2_000_000, "currency": "USD"},
        "assets": [
            {"asset_id": "cash", "kind": "liquidity", "value": 300_000, "currency": "USD"},
            {"asset_id": "home", "kind": "property", "value": 500_000, "currency": "USD"},
        ],
        "liabilities": [{
            "liability_id": "mortgage", "kind": "mortgage", "balance": 200_000,
            "currency": "USD", "annual_rate": 0.02,
        }],
        "known_but_not_yet_bound": ["age", "account_inventory"],
    }, base_currency="USD", fx_to_base={}, fx_source_refs=("fx",),
       as_of="2026-01-01T00:00:00Z")
    ids = ("cash", "us_equity", "international_equity", "usd_bonds", "us_tips")
    basis = compile_capital_market_basis({
        "schema": CAPITAL_MARKET_BASIS_SCHEMA, "basis_id": "public",
        "as_of": "2026-01-01T00:00:00Z",
        "asset_classes": [
            {"asset_id": asset_id, "risk_bucket": "cash" if asset_id == "cash" else
             "risky" if "equity" in asset_id else "defensive", "currency": "USD",
             "volatility": 0.01 if asset_id == "cash" else 0.16 if "equity" in asset_id else 0.06,
             "minimum_weight": 0, "maximum_weight": 1}
            for asset_id in ids
        ],
        "correlations": {left: {right: 0 for right in ids if right != left} for left in ids},
        "return_scenarios": [{
            "scenario_id": "source", "source_refs": ["public"],
            "expected_returns": {asset_id: 0.03 if asset_id == "cash" else
                                 0.08 if "equity" in asset_id else 0.04 for asset_id in ids},
        }],
        "source_refs": ["public"],
    })
    result = compile_household_allocation_scenario({
        "schema": HOUSEHOLD_ALLOCATION_SCENARIO_INPUT_SCHEMA,
        "annual_contribution": 50_000, "horizon_years": 20, "target_wealth": 2_000_000,
        "liquidity_reserve": 50_000, "max_risky_weight": 0.7,
        "max_one_year_loss": 0.4, "max_effective_equity_exposure": 0.7,
        "minimum_success_probability": 0.8,
        "annual_return_haircuts": {asset_id: 0 for asset_id in ids}, "weight_step": 0.1,
    }, goal_surface=surface, public_basis_acquisition={
        "schema": PUBLIC_BASIS_ACQUISITION_SCHEMA, "capital_market_basis": basis,
    }, simulation_paths=128)

    assert result["status"] == "planning_scenario_ready"
    assert sum(result["selected_policy"]["weights"].values()) == 1
    assert result["policy_authority"] is result["capital_authority"] is False
    assert result["operator_policy_blockers"] == ["account_inventory", "age"]
    selected_outcome = result["selected_policy"]["scenario_outcomes"][0]
    selected_path = result["selected_wealth_paths"][0]["annual_wealth_path"]
    assert selected_path[-1]["median_base"] == selected_outcome["terminal_median_base"]

    domains = {
        "annual_contribution": {
            "values": [150_000, 50_000], "question": "Annual contribution?",
            "source_blocker_ids": ["annual_after_tax_savings_capacity"],
        },
        "horizon_years": {
            "values": [30, 15], "question": "Investment horizon?",
            "source_blocker_ids": ["goal_horizon"],
        },
    }
    frontier = compile_household_mandate_frontier(
        base_inputs=result["inputs"], goal_surface=surface,
        public_basis_acquisition={
            "schema": PUBLIC_BASIS_ACQUISITION_SCHEMA, "capital_market_basis": basis,
        },
        input_domains=domains, simulation_paths=128,
    )
    reordered = compile_household_mandate_frontier(
        base_inputs=result["inputs"], goal_surface=surface,
        public_basis_acquisition={
            "schema": PUBLIC_BASIS_ACQUISITION_SCHEMA, "capital_market_basis": basis,
        },
        input_domains={key: {**value, "values": list(reversed(value["values"]))}
                       for key, value in reversed(domains.items())},
        simulation_paths=128,
    )
    assert frontier["mandate_frontier_sha256"] == reordered["mandate_frontier_sha256"]
    assert frontier["design_world_count"] == 6  # base values are retained in both domains
    assert frontier["decision_class_count"] >= 1
    if frontier["decision_class_count"] > 1:
        assert frontier["highest_voi_unresolved_input"]["decision_information_bits"] > 0
    assert frontier["information_method"]["probability_interpretation"] is False
    assert frontier["policy_authority"] is frontier["capital_authority"] is False
