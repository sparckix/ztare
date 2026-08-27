from ztare.common.equivariance import stable_sha256
from ztare.investment.recursive_strategy_benchmark import (
    AGENT_SELECTION_SCHEMA,
    SEALED_PROFILE_SHA256,
    compile_agent_only_baseline,
    run_recursive_strategy_benchmark,
)


def test_exhaustive_search_escapes_the_sealed_local_peak() -> None:
    result = run_recursive_strategy_benchmark()
    body = {key: value for key, value in result.items() if key != "benchmark_sha256"}
    assert result["benchmark_sha256"] == stable_sha256(body)
    assert result["one_edit_hill_climb"]["selected_option_ids"] == ["incumbent_bundle"]
    assert result["one_edit_hill_climb"]["stopped_at_local_peak"] is True
    assert result["exhaustive_search"]["selected_option_ids"] == [
        "adaptive_product", "distribution_platform",
    ]
    flat = result["flat_single_option_ablation"]
    assert [row["option_ids"] for row in flat["selected_programs"]] == [["incumbent_bundle"]]
    assert flat["selected_programs"][0]["option_ids"] == result["one_edit_hill_climb"][
        "selected_option_ids"
    ]
    assert flat["choice_space_sha256"] == result["choice_space_sha256"]
    ablation = result["solver_only_ablation"]
    assert [row["option_ids"] for row in ablation["selected_programs"]] == [
        ["adaptive_product", "incumbent_bundle"],
        ["distribution_platform", "incumbent_bundle"],
    ]
    assert {tuple(row["additive_objective_values"][:4]) for row in ablation["selected_programs"]} == {
        (7.0, 7.0, 7.0, 7.0),
    }
    assert ablation["missed_known_optimum"] is True
    assert ablation["exhaustive_dominates_every_selected_on_full_landscape"] is True
    assert all(
        row["additive_objective_values"][0] > row["full_landscape_objective_values"][0]
        for row in ablation["selected_programs"]
    )
    assert result["agent_only_baseline"]["status"] == "pending_recorded_agent_output"
    assert result["agent_only_baseline"]["included_in_comparison"] is False
    scored = compile_agent_only_baseline({
        "schema": AGENT_SELECTION_SCHEMA,
        "sealed_profile_sha256": SEALED_PROFILE_SHA256,
        "selected_option_ids": ["adaptive_product", "distribution_platform"],
        "rationale": "The positive interaction dominates the standalone incumbent.",
    }, {("adaptive_product", "distribution_platform"): {
        "objective_values": {"earnings_durability": 12.0},
    }})
    assert scored["selected_known_optimum"] is True
    assert result["local_peak_escape"]["requires_initial_decline"] is True
    assert result["local_peak_escape"]["exhaustive_beats_hill_climb"] is True
