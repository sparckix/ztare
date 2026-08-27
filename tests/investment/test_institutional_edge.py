from ztare.investment.institutional_edge import compile_institutional_edge_map


def test_counts_cannot_substitute_for_the_owning_review_gate():
    result = compile_institutional_edge_map(
        research_learning={
            "research_question_policy_experiment": {
                "valid_assignment_unit_count": 40,
                "settled_itt_unit_count": 40,
                "minimum_settled_units_per_arm": 20,
                "routing_decision": {"routing_change_allowed": False},
            }
        },
        strategy_move_learning={"outcome_episode_count": 20},
        institutional_learning={
            "strategy_causal_panel": {"treated_unit_count": 5, "control_unit_count": 5},
            "inference_block_count": 20,
            "evaluations": [{"law_key": "other@1", "promotion_eligible": True}],
        },
        closed_book={
            "run_count": 20, "settled_count": 20,
            "scoreboard": {"inference_block_count": 20, "minimum_inference_blocks": 8},
            "world_model_tournament": {"engine_evidence_eligible": False},
        },
        portfolio_policy={
            "run_count": 20, "settled_count": 20,
            "scoreboard": {
                "inference_block_count": 20, "minimum_inference_blocks": 8,
                "latest_policy_review": {
                    "activation_status": "no_unique_statistical_survivor",
                    "recommended_policy_id": None,
                },
            },
        },
        strategy_program_learning={"request_count": 1},
        strategy_program_transfer={"card_count": 0, "settled_episode_count": 0},
        strategy_program_control_acquisition={"admitted_source_control_count": 0},
    )
    assert result["reviewable_edge_ids"] == []
    assert result["economic_edge_established"] is False
    assert result["alpha_evidence_status"] == "unestablished"
    assert all(row["capital_authority"] is False for row in result["edges"])
    program_edge = next(
        row for row in result["edges"]
        if row["edge_id"] == "strategy_program_composition_to_operating_consequence"
    )
    assert program_edge["status"] == "awaiting_program_source_classification"
    assert program_edge["reviewable"] is False
