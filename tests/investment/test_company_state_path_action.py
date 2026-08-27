import math

from ztare.investment.company_state_path_action import compile_path_distributions
from ztare.investment.company_state_path_action_settlement import (
    compile_model_research_activation,
    score_company_state_path_models,
)
from ztare.investment.company_state_partition_frontier import _next_quarter


def test_path_action_enumerates_normalized_paths_and_survives_current_ablation() -> None:
    assert _next_quarter("2026-09-30") == "2026-12-31"
    states = tuple(
        f"valuation_{value}__durability_{durability}"
        for value in ("expensive", "cheap")
        for durability in ("low", "middle", "high")
    )
    models = compile_path_distributions(
        states, step_cost=1.0, curvature_cost=0.5, circulation_strength=0.125,
        empirical_transition_counts=[
            [8 if source == target else 1 for target in range(len(states))]
            for source in range(len(states))
        ],
    )
    by_id = {model["model_id"]: model for model in models}
    challenger = by_id["path_action_current"]["conditional_path_distributions"]
    ablation = by_id["reversible_action_ablation"]["conditional_path_distributions"]
    for model in models:
        for conditional in model["conditional_path_distributions"]:
            assert len(conditional["paths"]) == len(states) ** 2
            assert math.fsum(row["probability"] for row in conditional["paths"]) == 1.0
    assert any(
        math.fsum(abs(left["probability"] - right["probability"])
                  for left, right in zip(candidate["paths"], control["paths"], strict=True)) > 0
        for candidate, control in zip(challenger, ablation, strict=True)
    )
    empirical = by_id["empirical_markov_path_control"]
    assert empirical["role"] == "required_control"
    run = {
        "state_ids": states,
        "models": models,
        "source_snapshot": {"assignments": [
            {"entity_id": "A", "state_id": states[0]},
            {"entity_id": "B", "state_id": states[-1]},
        ]},
    }
    intermediate = {"A": states[1], "B": states[-1]}
    terminal = {"A": states[2], "B": states[-2]}
    intermediate_scores = score_company_state_path_models(
        run, intermediate_assignments=intermediate,
    )
    terminal_scores = score_company_state_path_models(
        run, intermediate_assignments=intermediate, terminal_assignments=terminal,
    )
    assert len(intermediate_scores["scores"]) == len(terminal_scores["scores"]) == len(models)
    assert all(row["entity_count"] == 2 for row in terminal_scores["scores"])


def test_path_action_survival_pays_the_ordinary_control_debt_before_newton() -> None:
    score = {
        "score_sha256": "score",
        "scores": [
            {"model_id": "path_action_current", "mean_brier": 0.1},
            {"model_id": "persistence_path_control", "mean_brier": 0.2},
        ],
    }
    legacy = compile_model_research_activation({
        "run_sha256": "legacy", "models": [
            {"model_id": "path_action_current"},
            {"model_id": "persistence_path_control"},
        ],
    }, score)
    assert legacy["action"] == "open_nonoverlapping_empirical_markov_comparison"

    controlled = compile_model_research_activation({
        "run_sha256": "controlled", "models": [
            {"model_id": "path_action_current"},
            {"model_id": "persistence_path_control"},
            {"model_id": "empirical_markov_path_control"},
        ],
    }, score)
    assert controlled["action"] == "subscription_newton_successor_project"
    assert controlled["capital_authority"] is False
