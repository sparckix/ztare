import pytest

import ztare.investment.operator_paper_policy as operator_policy
from ztare.common.equivariance import stable_sha256
from ztare.investment.household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    HOUSEHOLD_MANDATE_SCHEMA,
    compile_capital_market_basis,
    compile_household_allocation_frontier,
    compile_household_mandate,
)
from ztare.investment.golden_store import GoldenStore
from ztare.investment.operator_paper_policy import freeze_operator_paper_policy


def _signed(body, field):
    return {**body, field: stable_sha256(body)}


def test_operator_policy_requires_complete_explicit_choice_and_replays(
    tmp_path, monkeypatch,
) -> None:
    mandate = {
        "schema": HOUSEHOLD_MANDATE_SCHEMA, "mandate_id": "household-1",
        "mandate_purpose": "operator_policy", "as_of": "2026-01-01T00:00:00Z",
        "base_currency": "USD", "fx_to_base": {}, "person": {"age": 35},
        "tax_residence": "US", "accounts": [{"account_id": "taxable"}],
        "assets": [{"asset_id": "cash", "kind": "liquidity", "value": 100_000,
                    "currency": "USD", "liquid": True, "investable": True,
                    "source_ref": "operator:balance-sheet"}],
        "liabilities": [],
        "tax_policy": {"annual_return_haircuts": {"cash": 0, "us_equity": 0}},
        "currency_policy": {"minimum_asset_weights": {}},
        "goal": {"target_wealth": 150_000, "currency": "USD", "horizon_years": 10,
                 "annual_contribution": 5_000, "wealth_basis": "investable_wealth",
                 "minimum_success_probability": 0.5},
        "constraints": {"liquidity_reserve": 10_000, "max_risky_weight": 1,
                        "max_one_year_loss": 1, "max_effective_equity_exposure": 1,
                        "weight_step": 0.5},
        "human_capital": {"annual_net_income": 60_000, "currency": "USD", "years": 10,
                          "annual_growth": 0, "discount_rate": 0.05, "market_beta": 0,
                          "source_ref": "operator:income"},
        "source_refs": ["operator:balance-sheet", "operator:income"],
    }
    basis = compile_capital_market_basis({
        "schema": CAPITAL_MARKET_BASIS_SCHEMA, "basis_id": "basis-1",
        "as_of": mandate["as_of"],
        "asset_classes": [
            {"asset_id": "cash", "risk_bucket": "cash", "currency": "USD",
             "volatility": 0.01, "minimum_weight": 0, "maximum_weight": 1},
            {"asset_id": "us_equity", "risk_bucket": "risky", "currency": "USD",
             "volatility": 0.15, "minimum_weight": 0, "maximum_weight": 1},
        ],
        "correlations": {"cash": {"us_equity": 0}, "us_equity": {"cash": 0}},
        "return_scenarios": [{"scenario_id": "public", "source_refs": ["public:basis"],
                              "expected_returns": {"cash": 0.03, "us_equity": 0.07}}],
        "source_refs": ["public:basis"],
    })
    compiled = compile_household_mandate(mandate)
    allocation = compile_household_allocation_frontier(
        mandate=compiled, capital_market_basis=basis,
        simulation_seed_identity="planning-scenario", simulation_paths=512,
    )

    def proposal(proposal_id, entity_id):
        weights = {entity_id: 1.0}
        body = {
            "proposal_id": proposal_id, "method": proposal_id,
            "policy_rule_version": "same-sleeve-signal-v1",
            "starting_investable_wealth_base": 90_000,
            "positions": [{"entity_id": entity_id, "entity_kind": "broad_sleeve_proxy",
                           "target_weight": 1.0}],
            "decision_equivalence_id": stable_sha256(weights), "total_weight": 1.0,
            "source_refs": ["public:basis"], "selection_signal": None,
            "expected_return_claim": False, "selection_status": "unselected_paper_rival",
            "order_routing_allowed": False,
        }
        return _signed(body, "proposal_sha256")

    implementation = _signed({
        "schema": "jaggedthoughts-household-paper-implementation-rivals-v1",
        "proposals": [proposal("broad_sleeve_control", "SPY"),
                      proposal("cash_challenger", "BIL")],
        "capital_authority": False, "order_routing_allowed": False,
    }, "implementation_sha256")
    scenario = _signed({
        "schema": "jaggedthoughts-household-allocation-scenario-v1",
        "as_of": mandate["as_of"], "base_currency": "USD",
        "basis_sha256": basis["basis_sha256"], "mandate_sha256": "planning",
        "selected_policy": allocation["selected_policy"],
        "simulation": {"paths": 512},
        "paper_implementation": implementation,
        "policy_authority": False, "capital_authority": False,
    }, "scenario_sha256")
    arguments = dict(
        root=tmp_path, owner="operator", store_path=tmp_path / "golden.sqlite3",
        mandate=mandate, capital_market_basis=basis, scenario=scenario,
        selected_proposal_id="cash_challenger", operator_id="operator",
        attestation="paper_only_reviewed", reviewed_at="2026-01-02T00:00:00Z",
    )
    first = freeze_operator_paper_policy(**arguments)
    second = freeze_operator_paper_policy(**arguments)
    assert first["activation_status"] == "operator_paper_policy_frozen"
    assert second["activation_status"] == "already_frozen"
    assert second["policy_sha256"] == first["policy_sha256"]
    changed = freeze_operator_paper_policy(**{
        **arguments, "selected_proposal_id": "broad_sleeve_control",
        "reviewed_at": "2026-01-03T00:00:00Z",
    })
    assert changed["policy_sha256"] != first["policy_sha256"]
    assert len(GoldenStore(arguments["store_path"]).list_leaves(
        owner="operator", object_kind="household_capital_mandate",
    )) == 1
    with pytest.raises(ValueError, match="later review timestamp"):
        freeze_operator_paper_policy(**{
            **arguments, "selected_proposal_id": "broad_sleeve_control",
            "transaction_cost_bps": 20, "reviewed_at": "2026-01-03T00:00:00Z",
        })
    cost_changed = freeze_operator_paper_policy(**{
        **arguments, "selected_proposal_id": "broad_sleeve_control",
        "transaction_cost_bps": 20, "reviewed_at": "2026-01-04T00:00:00Z",
    })
    assert cost_changed["policy_sha256"] != changed["policy_sha256"]
    assert cost_changed["transaction_cost_bps"] == 20
    monkeypatch.setattr(
        operator_policy, "open_household_policy_tournament",
        lambda *args, **kwargs: {"activation_status": "blocked_overlap"},
    )
    with pytest.raises(ValueError, match="no compatible prospective tournament"):
        freeze_operator_paper_policy(**{
            **arguments, "selected_proposal_id": "cash_challenger",
            "transaction_cost_bps": 20, "reviewed_at": "2026-01-05T00:00:00Z",
        })
    with pytest.raises(ValueError, match="never inferred"):
        freeze_operator_paper_policy(**{**arguments, "selected_proposal_id": ""})
    with pytest.raises(ValueError, match="incomplete"):
        freeze_operator_paper_policy(**{
            **arguments, "mandate": {**mandate, "person": {}},
        })
