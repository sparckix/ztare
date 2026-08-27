import json

import pytest

from ztare.investment.state_pricing import (
    STATE_PRICE_CONTRACT_SCHEMA,
    audit_workspace_state_price_readiness,
    solve_state_prices,
)


def _contract():
    price = lambda identity, value: {
        "observation_id": identity, "value": value, "unit": "USD",
        "observed_at": "2026-01-01T00:00:00Z", "available_at": "2026-01-02T00:00:00Z",
        "source_ref": f"public:{identity}",
    }
    return {
        "schema": STATE_PRICE_CONTRACT_SCHEMA, "contract_id": "two-state-public-market",
        "as_of": "2026-01-02T00:00:00Z", "horizon_at": "2027-01-02T00:00:00Z",
        "states": [
            {"state_id": "down", "description": "Declared down-state payoff"},
            {"state_id": "up", "description": "Declared up-state payoff"},
        ],
        "probability_contract": {
            "kind": "declared_scenario_weights", "source_kind": "authored_scenario_weights",
            "weights": {"down": 0.5, "up": 0.5}, "source_refs": ["scenario:base-case"],
        },
        "assets": [
            {
                "asset_id": "treasury", "price_observation": price("treasury-price", 0.95),
                "payoffs": {"down": 1.0, "up": 1.0}, "payoff_source_refs": ["treasury:terms"],
            },
            {
                "asset_id": "equity", "price_observation": price("equity-price", 95.0),
                "payoffs": {"down": 80.0, "up": 120.0}, "payoff_source_refs": ["scenario:equity-payoffs"],
            },
        ],
        "numeraire_asset_id": "treasury", "minimum_state_price": 1e-9,
        "residual_tolerance": 1e-8,
    }


def test_state_price_kernel_solves_positive_prices_and_rejects_frequency_laundering():
    result = solve_state_prices(_contract())

    assert result["no_arbitrage_certificate"] is True
    assert result["market_complete"] is True
    assert result["representative_state_prices"] == pytest.approx({"down": 0.475, "up": 0.475})
    assert result["risk_neutral_probabilities"]["values"] == pytest.approx({"down": 0.5, "up": 0.5})
    assert result["stochastic_discount_kernel"]["values"] == pytest.approx({"down": 0.95, "up": 0.95})
    assert result["residuals"]["max_abs_price_residual"] < 1e-8
    assert result["capital_authority"] is False

    invalid = _contract()
    invalid["probability_contract"]["source_kind"] = "historical_frequency"
    with pytest.raises(ValueError, match="historical frequencies"):
        solve_state_prices(invalid)


def test_state_price_readiness_reuses_latest_observation_projection(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "discovery").mkdir()
    (tmp_path / "state_pricing" / "contracts").mkdir(parents=True)
    (tmp_path / "data" / "latest_source_run.json").write_text(json.dumps({
        "as_of": "2026-01-02T00:00:00Z",
    }))
    (tmp_path / "discovery" / "latest.json").write_text(json.dumps({"candidates": []}))

    result = audit_workspace_state_price_readiness(tmp_path, latest_observations=(
        {"entity_id": "AAA", "metric_id": "price"},
        {"entity_id": "AAA", "metric_id": "adjusted_price"},
        {"entity_id": "BBB", "metric_id": "price"},
    ))

    assert result["public_price_entity_count"] == 2
