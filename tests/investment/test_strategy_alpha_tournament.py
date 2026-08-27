from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from ztare.investment.strategy_alpha_tournament import (
    DURABILITY_CONTROL,
    MOMENTUM_CONTROL,
    NULL_CONTROL,
    STRATEGY_MODEL,
    VALUATION_CONTROL,
    StrategyAlphaEpisode,
    evaluate_strategy_alpha_tournament,
)


def _episode(index: int) -> StrategyAlphaEpisode:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=91 * index)
    end = start + timedelta(days=90)
    active_return = 0.08 if index % 2 == 0 else -0.04
    return StrategyAlphaEpisode(
        episode_id=f"episode-{index}",
        inference_block_id=f"quarter-{index}",
        entity_id=f"company-{index}",
        issuer_identity=f"public_equity:company-{index}",
        cohort_family_sha256="d" * 64,
        information_set_sha256=f"{index + 1:064x}",
        information_available_at=(start - timedelta(days=2)).isoformat(),
        phenotype_sha256="a" * 64,
        strategy_expectation_residual_sha256="b" * 64,
        strategy_translation_kind="direct_operating_hurdle_payoff",
        strategy_causal_effect_earned=False,
        strategy_procedure_sha256="c" * 64,
        phenotype_available_at=(start - timedelta(days=3)).isoformat(),
        trained_through=(start - timedelta(days=2)).isoformat(),
        issued_at=(start - timedelta(days=1)).isoformat(),
        start_at=start.isoformat(),
        end_at=end.isoformat(),
        outcome_available_at=(end + timedelta(days=1)).isoformat(),
        valuation_expected_active_return=active_return - 0.06,
        momentum_expected_active_return=0.0,
        durability_return_adjustment=0.02,
        phenotype_return_adjustment=0.04,
        asset_return=0.03 + active_return,
        benchmark_return=0.03,
        information_source_refs=(f"filing-{index}", f"phenotype-event-{index}"),
        phenotype_source_refs=(f"phenotype-event-{index}",),
        outcome_source_refs=(f"later-price-{index}",),
    )


def test_nested_strategy_arm_uses_one_information_set_and_beats_controls() -> None:
    episodes = tuple(_episode(index) for index in range(12))
    result = evaluate_strategy_alpha_tournament(
        tournament_id="strategy-alpha-holdout",
        owner="jaggedthoughts-paper",
        as_of="2027-01-01T00:00:00Z",
        candidate_set_frozen_at="2023-12-01T00:00:00Z",
        episodes=episodes,
        min_inference_blocks=8,
    )

    losses = {
        row["model_id"]: row["prediction_loss"]["mean"]
        for row in result["evaluation"]["model_metrics"]
    }
    assert losses[STRATEGY_MODEL] < losses[DURABILITY_CONTROL] < losses[VALUATION_CONTROL]
    assert losses[STRATEGY_MODEL] < losses[MOMENTUM_CONTROL] == losses[NULL_CONTROL]
    assert result["same_information_control"]["verified"] is True
    assert result["strategy_point_estimate_better_than_controls"] is True
    assert result["strategy_better_than_controls_after_fdr"] is True
    assert {row["phenotype_sha256"] for row in result["phenotype_bindings"]} == {"a" * 64}
    assert result["capital_authority"] is False

    with pytest.raises(ValueError, match="unavailable when the forecast issued"):
        replace(episodes[0], information_available_at="2024-01-02T00:00:00Z")
