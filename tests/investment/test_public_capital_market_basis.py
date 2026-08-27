from datetime import datetime, timedelta, timezone

import numpy as np

from ztare.investment.household_allocation import compile_capital_market_basis
from ztare.investment.public_capital_market_basis import (
    PUBLIC_BASIS_SOURCE_IDS,
    compile_public_capital_market_basis_input,
)


def test_public_basis_uses_prices_for_risk_but_not_return_forecasts() -> None:
    as_of = "2026-01-01T00:00:00Z"
    receipts = [{
        "source_id": source_id, "receipt_sha256": f"{index + 1:064x}",
        "retrieved_at": as_of,
    } for index, source_id in enumerate(PUBLIC_BASIS_SOURCE_IDS)]
    proxies = {
        "yahoo_bil_adjusted_daily": "BIL",
        "yahoo_spy_adjusted_daily": "SPY",
        "yahoo_vxus_adjusted_daily": "VXUS",
        "yahoo_bnd_adjusted_daily": "BND",
        "yahoo_tip_adjusted_daily": "TIP",
    }
    observations = []
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for source_index, (source_id, symbol) in enumerate(proxies.items()):
        price = 100.0
        for day in range(320):
            price *= 1.0 + 0.0002 + 0.001 * np.sin(day / 11 + source_index)
            observations.append({
                "observation_id": f"{source_id}:{day}", "entity_id": symbol,
                "metric_id": "adjusted_price", "value": price, "unit": "USD",
                "observed_at": (start + timedelta(days=day)).isoformat().replace("+00:00", "Z"),
                "available_at": as_of, "source_ref": source_id,
            })
    for metric_id, value in (
        ("treasury_3m_yield", 0.03),
        ("treasury_10y_real_yield", 0.02),
        ("breakeven_inflation_10y", 0.025),
    ):
        observations.append({
            "observation_id": metric_id, "entity_id": "US-MACRO", "metric_id": metric_id,
            "value": value, "unit": "decimal", "observed_at": as_of,
            "available_at": as_of, "source_ref": "fred_public_market_state",
        })
    for metric_id, value in (
        ("risk_free_rate", 0.04),
        ("implied_equity_risk_premium", 0.05),
        ("implied_erp_ttm_cash_yield", 0.04),
        ("implied_erp_10y_average_cash_flow_yield", 0.07),
        ("implied_erp_net_cash_yield", 0.03),
        ("implied_erp_normalized_earnings_payout", 0.02),
    ):
        observations.append({
            "observation_id": metric_id, "entity_id": "US-MARKET", "metric_id": metric_id,
            "value": value, "unit": "decimal", "observed_at": as_of,
            "available_at": as_of, "source_ref": "nyu_us_implied_erp",
        })

    raw = compile_public_capital_market_basis_input(
        as_of=as_of, observations=observations, source_receipts=receipts,
        lookback_returns=252, diagonal_shrinkage=0.5,
    )
    basis = compile_capital_market_basis(raw)

    scenario = basis["return_scenarios"][0]["expected_returns"]
    assert scenario == {
        "cash": 0.03, "us_equity": 0.09, "international_equity": 0.09,
        "usd_bonds": 0.04, "us_tips": (1.02 * 1.025) - 1,
    }
    assert raw["risk_evidence"]["historical_mean_used_as_forecast"] is False
    assert raw["risk_evidence"]["return_count"] == 252
    uncertainty = raw["return_scenario_inputs"]["uncertainty_set"]
    assert uncertainty["mode"] == "source_bound_erp_method_worlds"
    assert uncertainty["scenario_count"] == 5
    assert uncertainty["probability_interpretation"] is False
    assert uncertainty["shared_method_epoch"]["observed_at"] == as_of
    assert {
        round(row["expected_returns"]["us_equity"], 12)
        for row in raw["return_scenarios"]
    } == {0.06, 0.07, 0.08, 0.09, 0.11}
    assert {
        row["expected_returns"]["cash"] for row in raw["return_scenarios"]
    } == {0.03}
    assert basis["covariance_min_eigenvalue"] >= -1e-12
    assert set(row["asset_id"] for row in basis["asset_classes"]) == {
        "cash", "us_equity", "international_equity", "usd_bonds", "us_tips",
    }
