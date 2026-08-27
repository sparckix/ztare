from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_representation_learning import (
    compile_strategy_security_representation_learning,
)
from ztare.investment.strategy_path_shadow import compile_strategy_path_shadow


def test_only_representation_counterexamples_can_propose_a_grammar_delta():
    def move(episode_sha256: str, entity_id: str, year: int):
        return {
            "episode_sha256": episode_sha256,
            "estimated_effect": (year - 2020) / 100.0,
            "accession_number": f"acc-{episode_sha256}",
            "entity_id": entity_id,
            "occurred_at": f"{year}-01-01T00:00:00Z",
            "implementation_mode": "acquisition",
            "transaction_phenotype": {
                "transaction_form": "asset_purchase",
                "operating_object_scope": "business_unit",
                "issuer_role": "acquirer",
            },
        }

    replay_body = {
        "schema": "jaggedthoughts-historical-strategy-event-replay-v1",
        "evidence_as_of": "2026-08-22T00:00:00Z",
        "episodes": [
            move("old-move", "B", 2017),
            move("move-1", "B", 2020), move("move-2", "B", 2021),
            move("move-3", "C", 2022), move("move-4", "C", 2023),
        ],
    }
    replay = {**replay_body, "replay_sha256": stable_sha256(replay_body)}
    body = {
        "schema": "jaggedthoughts-strategy-security-walk-forward-tournament-v1",
        "evidence_as_of": "2026-08-22T00:00:00Z",
        "replay_sha256": replay["replay_sha256"],
        "status": "typed_policy_did_not_clear_both_controls",
        "minimum_independent_blocks": 6,
        "execution_contract": {
            "return_target": "factor_controlled_log_return", "horizon_days": 400,
        },
        "security_outcomes": [{
            **move("isolated-1", "A", 2019),
            "inference_block_id": "event-year:2019",
            "estimated_effect": 0.04,
        }],
        "coverage_gaps": [
            {
                "reason": "historical_security_identity_unresolved",
                "entity_id": "A",
                "episode_sha256": "identity-gap",
            },
            {
                "reason": "overlapping_strategy_events_require_bundle_representation",
                "entity_id": "B",
                "episode_sha256s": ["move-1", "move-2"],
                "entry_start": "2024-01-01T00:00:00Z",
                "exit_end": "2025-01-01T00:00:00Z",
            },
            {
                "reason": "overlapping_strategy_events_require_bundle_representation",
                "entity_id": "C",
                "episode_sha256s": ["move-3", "move-4"],
                "entry_start": "2022-01-01T00:00:00Z",
                "exit_end": "2024-01-01T00:00:00Z",
            },
        ],
        "capital_authority": False,
    }
    tournament = {**body, "tournament_sha256": stable_sha256(body)}

    learning = compile_strategy_security_representation_learning(tournament, replay=replay)

    assert learning["conjecture_count"] == 1
    assert {
        row["operator_id"]
        for row in learning["conjectures"][0]["grammar_delta"]["full_typed_delta"][
            "added_operators"
        ]
    } == {
        "append_strategy_move", "compose_strategy_moves", "project_strategy_move_path",
    }
    assert learning["acquisition_gaps"] == [{
        "reason": "historical_security_identity_unresolved",
        "entity_id": "A",
        "episode_sha256s": ["identity-gap"],
    }]
    conjecture = learning["conjectures"][0]
    assert conjecture["trial_state"] == "same_epoch_behavior_qualified"
    assert conjecture["same_epoch_behavior_qualification"]["qualified_behavior_count"] > 0
    assert conjecture["future_evaluation_contract"]["activation_status"] == "eligible_to_freeze"
    assert learning["security_ranking_use"] is False

    def event(accession: str, occurred_at: str):
        event_body = {
            "schema": "jaggedthoughts-bulk-sec-item-2.01-event-v1",
            "cik": "0000000001", "accession_number": accession,
            "item": "2.01", "primary_document": f"{accession}.htm",
            "occurred_at": occurred_at, "available_at": occurred_at,
            "filing_date": occurred_at[:10], "company_name": "Path Corp",
            "sic": "3600",
            "current_common_equity_member": True,
            "current_common_equity_symbols": ["PATH"],
        }
        return {**event_body, "event_sha256": stable_sha256(event_body)}

    events = [
        event("future-1", "2026-09-01T12:00:00Z"),
        event("future-2", "2027-01-01T12:00:00Z"),
        event("future-3", "2027-03-01T12:00:00Z"),
    ]
    classifications = {
        row["accession_number"]: {
            "classification": "acquisition_completion",
            "implementation_mode": "acquisition",
            "transaction_form": "asset_purchase",
            "operating_object_scope": "business_unit",
            "issuer_role": "acquirer", "completion_state": "completed",
            "strategy_event_eligibility": "operating_strategy_event",
            "classification_receipt_sha256": stable_sha256(row["accession_number"]),
            "filing_document_sha256": stable_sha256(row),
            "filing_trading_symbols": ["PATH"],
        }
        for row in events
    }
    corpus_body = {
        "schema": "jaggedthoughts-historical-strategy-bulk-event-corpus-v2",
        "event_lake_path": "unused.jsonl", "event_lake_sha256": "unused",
        "market_catalog_sha256": stable_sha256("catalog"),
        "bulk_source_receipt_sha256": stable_sha256("source"),
    }
    corpus = {**corpus_body, "corpus_sha256": stable_sha256(corpus_body)}
    operating_history = [{
        "observed_at": "2025-12-31T23:59:59Z",
        "available_at": "2026-02-20T23:59:59Z",
        "owner_earnings_margin": 0.12,
        "observation_ids": ["baseline"],
        "observation_row_sha256s": [stable_sha256("baseline")],
    }]
    evaluation = {
        "diagnostic_status": "inconclusive_effect",
        "details": {"aggregate_att": 0.025},
    }
    evaluation["evaluation_sha256"] = stable_sha256(evaluation)
    diagnostics_body = {
        "schema": "jaggedthoughts-historical-strategy-bulk-effect-diagnostics-v1",
        "diagnostics": [{
            "cell": {
                "sic2": "36", "implementation_mode": "acquisition",
                "adoption_year": 2020, "group_time_ready": True,
            },
            "evaluation": evaluation,
        }],
    }
    diagnostics = {
        **diagnostics_body,
        "diagnostics_sha256": stable_sha256(diagnostics_body),
    }
    shadow = compile_strategy_path_shadow(
        learning, replay, tournament, corpus, events, classifications,
        operating_histories={"0000000001": operating_history},
        bulk_effect_diagnostics=diagnostics,
        as_of="2027-03-02T00:00:00Z",
    )

    assert sorted(row["path_length"] for row in shadow["forecasts"]) == [1, 1, 1, 2, 2, 3]
    assert shadow["single_move_forecast_count"] == 3
    assert shadow["operating_forecast_count"] == 3
    assert all(
        row["predicted_deltas"]["group_time_strategy_family"] == 0.025
        and row["group_time_prediction_basis"] == "sic2_implementation_mode_family"
        for row in shadow["operating_forecasts"]
    )
    assert shadow["event_research_queue_count"] == 3
    assert all(
        row["selection_use"] == "evidence_acquisition_only"
        and row["capital_authority"] is False
        for row in shadow["event_research_queue"]
    )
    assert all(
        row["ordered_move_observation_sha256s"][-1]
        == row["target_move_observation_sha256"] for row in shadow["forecasts"]
    )
    assert {row["settlement_contract"]["diagnostic_horizon_days"] for row in shadow["forecasts"]} == {90}
    assert shadow["diagnostic_promotion_authority"] is False
    assert shadow["automatic_model_refit"] is False
    assert shadow["capital_authority"] is False

    settled = compile_strategy_path_shadow(
        learning, replay, tournament, corpus, events, classifications,
        prior=shadow,
        operating_histories={"0000000001": [
            *operating_history,
            {"observed_at": "2030-01-01T00:00:00Z", "available_at": "2030-02-01T00:00:00Z", "owner_earnings_margin": 0.15, "observation_ids": ["outcome"], "observation_row_sha256s": [stable_sha256("outcome")]},
        ]},
        bulk_effect_diagnostics=diagnostics,
        as_of="2030-03-02T00:00:00Z",
    )
    assert settled["operating_settled_forecast_count"] == 3
    assert settled["operating_tournament"]["independent_block_count"] == 1
