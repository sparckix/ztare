"""Unit tests for BRIDGE-2 retirement detector decision rule.

Three tests per spec §9 acceptance:
  (a) substrate flagged when all three rules fire
  (b) plateau guard correctly blocks retirement when a pivot succeeded
  (c) paper_critical correctly blocks retirement
"""

from __future__ import annotations

from ztare.research_director.retirement_detector import (
    ProjectMetrics,
    evaluate,
)


def make_metrics(**kw):
    defaults = dict(
        project="test_proj",
        iter_count=20,
        last_iter_ts=1_700_000_000,
        stagnation_count=8,
        last_5_score_variance=2.0,
        cost_per_finding_30d=20.0,
        iters_in_30d=20,
        promotions_in_30d=1,
        pivots_in_30d=0,
        paper_critical=False,
        substrate_class=None,
        last_5_scores=[40, 41, 40, 41, 40],
    )
    defaults.update(kw)
    return ProjectMetrics(**defaults)


def test_all_three_rules_fire_recommends_retirement():
    m = make_metrics(
        stagnation_count=8,
        last_5_score_variance=2.0,
        cost_per_finding_30d=20.0,
    )
    median_cost = 5.0  # 20.0 > 5.0 * 2.0 = 10.0
    d = evaluate(m, median_cost, stagnation_threshold=5, variance_threshold=5.0, cost_multiplier=2.0)
    assert d.recommend_retirement is True
    assert all(d.rule_firings.values())
    assert d.plateau_guards == []


def test_plateau_guard_blocks_retirement_after_pivot():
    m = make_metrics(
        stagnation_count=8,
        last_5_score_variance=2.0,
        cost_per_finding_30d=20.0,
        pivots_in_30d=1,
    )
    median_cost = 5.0
    d = evaluate(m, median_cost, stagnation_threshold=5, variance_threshold=5.0, cost_multiplier=2.0)
    assert d.recommend_retirement is False
    assert any("pivots_in_30d" in g for g in d.plateau_guards)
    assert all(d.rule_firings.values())  # rules still fire; the guard blocks the recommendation


def test_paper_critical_blocks_retirement():
    m = make_metrics(
        stagnation_count=99,
        last_5_score_variance=0.0,
        cost_per_finding_30d=999.0,
        paper_critical=True,
    )
    d = evaluate(m, median_cost=5.0, stagnation_threshold=5, variance_threshold=5.0, cost_multiplier=2.0)
    assert d.recommend_retirement is False
    assert "paper_critical" in d.plateau_guards


def test_cold_start_excluded():
    m = make_metrics(iter_count=5, stagnation_count=99, last_5_score_variance=0.0, cost_per_finding_30d=999.0)
    d = evaluate(m, median_cost=5.0, stagnation_threshold=5, variance_threshold=5.0, cost_multiplier=2.0)
    assert d.recommend_retirement is False
    assert "cold_start_under_10_iters" in d.plateau_guards


def test_one_rule_unfired_skips_retirement():
    m = make_metrics(stagnation_count=2)  # below threshold
    d = evaluate(m, median_cost=5.0, stagnation_threshold=5, variance_threshold=5.0, cost_multiplier=2.0)
    assert d.recommend_retirement is False
    assert d.rule_firings["stagnation>=5"] is False


def test_no_plateau_guard_flag_overrides():
    m = make_metrics(
        stagnation_count=8,
        last_5_score_variance=2.0,
        cost_per_finding_30d=20.0,
        pivots_in_30d=1,
        substrate_class="tail_generalization",
    )
    d = evaluate(
        m,
        median_cost=5.0,
        stagnation_threshold=5,
        variance_threshold=5.0,
        cost_multiplier=2.0,
        no_plateau_guard=True,
    )
    assert d.recommend_retirement is True
    assert d.plateau_guards == []
