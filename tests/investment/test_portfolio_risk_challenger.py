from __future__ import annotations

from datetime import date, timedelta
from math import cos, sin

import pytest

from ztare.investment.portfolio_risk_challenger import (
    PORTFOLIO_RISK_CHALLENGER_SCHEMA,
    compile_walk_forward_ridge_risk_challenger,
)


def test_ridge_risk_challenger_uses_only_past_decision_loss() -> None:
    prices = {entity_id: {} for entity_id in ("A", "B", "C")}
    values = {entity_id: 100.0 for entity_id in prices}
    start = date(2024, 1, 1)
    for offset in range(400):
        day = (start + timedelta(days=offset)).isoformat()
        if offset:
            returns = {
                "A": 0.002 * sin(offset) if offset < 260 else 0.025 * sin(offset * 1.7),
                "B": 0.008 * cos(offset * 0.71),
                "C": 0.010 * sin(offset * 0.43 + 1),
            }
            for entity_id, value in returns.items():
                values[entity_id] *= 1.0 + value
        for entity_id in prices:
            prices[entity_id][day] = values[entity_id]
    as_of = f"{day}T00:00:00Z"

    result = compile_walk_forward_ridge_risk_challenger(
        price_series=prices, as_of=as_of, source_risk_model_sha256="a" * 64,
        gross_weight=0.60, maximum_weight=0.40,
    )
    scores = {row["ridge_penalty_ratio"]: row for row in result["validation_scores"]}

    assert result["schema"] == PORTFOLIO_RISK_CHALLENGER_SCHEMA
    assert result["selected_ridge_penalty_ratio"] > 0
    assert min(row["mean_validation_variance"] for row in scores.values()) < (
        scores[0.0]["mean_validation_variance"]
    )
    assert sum(result["weights"].values()) == pytest.approx(0.60)
    assert max(result["weights"].values()) <= 0.40 + 1e-12
    assert result["promotion_eligible_under_current_score_contract"] is False
    assert result["capital_authority"] is False

    future = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    for entity_id in prices:
        prices[entity_id][future] = prices[entity_id][day] * 10
    replay = compile_walk_forward_ridge_risk_challenger(
        price_series=prices, as_of=as_of, source_risk_model_sha256="a" * 64,
        gross_weight=0.60, maximum_weight=0.40,
    )
    assert replay["risk_challenger_sha256"] == result["risk_challenger_sha256"]

    with pytest.raises(ValueError, match="enough aligned returns"):
        compile_walk_forward_ridge_risk_challenger(
            price_series={
                entity_id: dict(list(rows.items())[:300])
                for entity_id, rows in prices.items()
            },
            as_of=as_of, source_risk_model_sha256="a" * 64,
            gross_weight=0.60, maximum_weight=0.40,
        )
