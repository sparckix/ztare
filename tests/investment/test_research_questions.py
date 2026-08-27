from ztare.investment.research_questions import compile_research_question_frontier


def test_question_frontier_binds_the_candidate_decision_boundary():
    candidate = {
        "entity_id": "ACME", "entity_kind": "public_equity",
        "candidate_sha256": "a" * 64, "screen_status": "qualified",
        "score_components": {
            "durable_earnings_power": 0.5, "earnings_power_margin": 0.5,
            "low_implied_growth": 0.5, "price_implied_excess_return": 0.5,
        },
        "metrics": {"earnings_power_margin": 0.2, "implied_growth": 0.03},
        "criteria": [
            {"criterion_id": "quality-floor", "path": "quality", "operator": "ge",
             "observed": 0.8, "threshold": 0.45, "passed": True},
            {"criterion_id": "excess-return-floor", "path": "price_implied_excess_return",
             "operator": "ge", "observed": 0.031, "threshold": 0.03, "passed": True},
        ],
    }

    result = compile_research_question_frontier(candidate, arm_id="disagreement_first")

    assert result["decision_context"]["criterion_id"] == "excess-return-floor"
    assert result["decision_context"]["transition_scope"] == "future_candidate_epoch_only"
    assert result["selected_program"]["decision_boundaries"] == [result["decision_context"]]
    assert "decision_boundary:excess-return-floor" in result["selected_program"]["atom_ids"]
    assert result["decision_context"]["information_gain_estimated"] is False
    assert "market_data" in result["selected_program"]["source_plan"]
    assert compile_research_question_frontier(
        {**candidate, "criteria": list(reversed(candidate["criteria"]))},
        arm_id="disagreement_first",
    ) == result
    assert result["capital_authority"] is False
