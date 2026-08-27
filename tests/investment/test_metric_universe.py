import yaml

from ztare.investment.contracts import MetricObservation
from ztare.investment.metrics import derive_standard_metrics, metric_universe_surface
from ztare.investment.sources import PUBLIC_SOURCE_MANIFEST_SCHEMA
from ztare.investment.universe import repair_public_equity_quarterly_sources


def test_metric_registry_canonicalizes_alias_and_executes_cross_entity_spreads():
    at = "2026-08-01T00:00:00Z"

    def observation(entity_id, metric_id, value):
        return MetricObservation(
            f"{entity_id}:{metric_id}", entity_id, metric_id, value, "decimal",
            at, at, "source",
        )

    inputs = (
        observation("US-MARKET", "risk_free_rate", 0.04),
        observation("US-MARKET", "implied_equity_risk_premium", 0.05),
        observation("US-MARKET", "sp500_forward_earnings_yield", 0.045),
        observation("US-MARKET", "sp500_trailing_earnings_yield", 0.04),
        observation("US-MARKET", "sp500_trailing_dividend_yield", 0.013),
        observation("US-MACRO", "treasury_10y_real_yield", 0.02),
        observation("US-MACRO", "breakeven_inflation_10y", 0.025),
    )
    rows, receipts, blocks = derive_standard_metrics(inputs, as_of=at)
    values = {row.metric_id: row.value for row in rows if row.entity_id == "US-MARKET"}

    assert blocks == () and len(receipts) == 5
    assert abs(values["treasury_10y_nominal_recomposed"] - 0.0455) < 1e-12
    assert abs(values["forward_earnings_yield_minus_nominal_10y"] + 0.0005) < 1e-12

    universe = metric_universe_surface([
        {"metric_id": "owner_earnings_yield"},
        {"metric_id": "portfolio_holding_hhi"},
        {"metric_id": "open_provider_statistic"},
    ])
    assert universe["observed_aliases"] == [{
        "observed_metric_id": "portfolio_holding_hhi",
        "canonical_metric_id": "portfolio_holdings_hhi",
    }]
    assert universe["unregistered_observed_metric_ids"] == ["open_provider_statistic"]


def test_quarterly_source_repair_feeds_operating_margin(tmp_path):
    manifest = {
        "schema": PUBLIC_SOURCE_MANIFEST_SCHEMA,
        "sources": [{
            "id": "sec_acme_companyfacts", "adapter": "sec_companyfacts",
            "entity_id": "ACME", "cik": "0000000001", "selections": [],
        }],
    }
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    repair = repair_public_equity_quarterly_sources(tmp_path)
    assert {row["metric_id"] for row in repair["additions"]} == {
        "revenue_q", "operating_income_q", "net_income_q",
    }

    at = "2026-08-01T00:00:00Z"
    rows, _, _ = derive_standard_metrics((
        MetricObservation("revenue", "ACME", "revenue_q", 100, "USD/quarter", at, at, "sec"),
        MetricObservation("op-income", "ACME", "operating_income_q", 18, "USD/quarter", at, at, "sec"),
    ), as_of=at)
    margin = next(row for row in rows if row.metric_id == "operating_margin_q")
    assert margin.value == 0.18 and margin.unit == "decimal"
