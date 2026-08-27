from datetime import datetime, timedelta, timezone

from ztare.common.equivariance import stable_sha256
from ztare.investment.historical_strategy_event_replay import (
    HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA,
)
from ztare.investment.factor_analysis import (
    FactorDefinition,
    PricePoint,
    compile_historical_factor_control,
)
from ztare.investment.strategy_walk_forward import (
    _security_independence_receipt,
    compile_strategy_security_walk_forward,
    compile_strategy_walk_forward,
    extract_filing_trading_symbols,
)


def _replay(years):
    episodes = []
    for year in years:
        for index in range(4):
            effect = float((year - 2020) * 10 + index)
            body = {
                "inference_block_id": f"fiscal-year:{year}",
                "entity_id": f"entity-{index}",
                "available_at": f"{year}-01-01T20:00:00Z",
                "implementation_mode": "acquisition" if index % 2 else "disposition",
                "transaction_phenotype": {
                    "transaction_form": "asset_purchase" if index % 2 else "asset_sale",
                    "operating_object_scope": "business_unit",
                    "issuer_role": "buyer" if index % 2 else "seller",
                },
                "baseline": {"value": 100.0},
                "outcome": {"value": 100.0 + effect},
                "estimated_effect": effect,
            }
            episodes.append({**body, "episode_sha256": stable_sha256(body)})
    body = {
        "schema": HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA,
        "evidence_as_of": f"{max(years)}-12-31T00:00:00Z",
        "episodes": episodes,
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def test_future_block_cannot_rewrite_prior_strategy_forecasts():
    original = compile_strategy_walk_forward(_replay(range(2019, 2023)))
    extended = compile_strategy_walk_forward(_replay(range(2019, 2024)))

    assert [row["fold_sha256"] for row in original["folds"]] == [
        row["fold_sha256"] for row in extended["folds"][: len(original["folds"])]
    ]


def _prices(years):
    rows = []
    for year in years:
        for entity_index, entity_id in enumerate(["SPY", *(f"entity-{i}" for i in range(4))]):
            for day, value in (
                ("01-02", 100.0), ("01-03", 100.0),
                ("02-03", 101.0 + entity_index + (year % 3)),
            ):
                observed_at = f"{year}-{day}T21:00:00Z"
                rows.append(PricePoint(
                    entity_id=entity_id, observed_at=observed_at,
                    available_at="2030-01-01T00:00:00Z", value=value,
                    observation_id=f"{entity_id}:{observed_at}", source_ref=f"price:{entity_id}",
                ))
    return rows


def test_future_security_block_cannot_rewrite_prior_strategy_return_folds():
    def compile(years):
        return compile_strategy_security_walk_forward(
            _replay(years), _prices(years), price_source_run_sha256="a" * 64,
            evidence_as_of="2030-01-01T00:00:00Z", horizon_days=30,
            entry_lag_sessions=1,
        )

    original = compile(range(2017, 2023))
    extended = compile(range(2017, 2024))

    assert original["fold_count"] > 0
    assert original["inference_sufficient"] is False
    inference = original["dependence_adjusted_inference"]
    assert inference["calendar_cohort_count"] == original["fold_count"]
    assert inference["newey_west_lag_calendar_cohorts"] == 1
    assert inference["training_purge_rule"] == (
        "training_return_exit_strictly_precedes_test_issue_cutoff"
    )
    assert all(row["training_purge_rule_satisfied"] for row in original["folds"])
    assert [row["fold_sha256"] for row in original["folds"]] == [
        row["fold_sha256"] for row in extended["folds"][: len(original["folds"])]
    ]


def test_overlapping_security_windows_count_as_one_inference_block():
    outcomes = [{
        "episode_sha256": f"episode-{index}",
        "security_outcome_sha256": f"outcome-{index}",
        "entry": {"observed_at": start}, "exit": {"observed_at": end},
    } for index, (start, end) in enumerate((
        ("2023-01-02T21:00:00Z", "2024-01-02T21:00:00Z"),
        ("2023-08-01T21:00:00Z", "2024-08-01T21:00:00Z"),
        ("2025-01-02T21:00:00Z", "2026-01-02T21:00:00Z"),
    ))]

    receipt = _security_independence_receipt(
        outcomes, {row["episode_sha256"] for row in outcomes},
    )

    assert receipt["independent_block_count"] == 2
    assert receipt["count_is_inference_sample_size"] is False


def test_future_prices_cannot_rewrite_a_settled_factor_control():
    start = datetime(2020, 1, 1, 21, tzinfo=timezone.utc)

    def points(days):
        return [
            PricePoint(entity, (start + timedelta(days=day)).isoformat(),
                       "2030-01-01T00:00:00Z", 100 + day * scale,
                       f"{entity}:{day}", f"price:{entity}")
            for day in range(days) for entity, scale in (("ACME", 2), ("SPY", 1))
        ]

    def compile(rows):
        return compile_historical_factor_control(
            analysis_id="fixed-event", candidate_entity_id="ACME",
            factors=(FactorDefinition("market", "SPY"),), price_points=rows,
            evidence_as_of="2030-01-01T00:00:00Z",
            calibration_end=(start + timedelta(days=24)).isoformat(),
            settlement_start=(start + timedelta(days=25)).isoformat(),
            settlement_end=(start + timedelta(days=35)).isoformat(),
            min_observations=10, lookback_observations=20,
        )

    assert compile(points(36))["factor_control_sha256"] == compile(points(45))["factor_control_sha256"]


def test_filing_symbol_requires_an_issuer_statement():
    filing = b"""<table><tr><td>Title of each class</td><td>Trading symbol(s)</td>
        <td>Name of exchange</td></tr><tr><td>Common Stock</td><td>PD</td>
        <td>NYSE</td></tr></table><table><tr><td>A</td><td>EXHIBITS</td>
        <td>B</td></tr></table><p>The Company's shares of common stock are
        trading on the NYSE under the new ticker symbol &quot;ESI.&quot;</p>"""
    annual = b"""<p>Our Class A common stock trades on the New York Stock
        Exchange under the symbol LAD.</p><p>The Company Common Stock is quoted
        on Nasdaq under the symbol INOD.</p><p>Our common stock was listed under
        TWP. Effective November 23, 2009, the symbol changed to TREX.</p>"""
    third_party = b'<p>Target shares trade under the ticker symbol "NOPE".</p>'

    assert extract_filing_trading_symbols(filing) == ["ESI", "PD"]
    assert extract_filing_trading_symbols(annual) == ["INOD", "LAD", "TREX"]
    assert extract_filing_trading_symbols(third_party) == []
