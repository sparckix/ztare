import json

import pytest

from ztare.investment.search_trial_census import (
    compile_closed_book_trial_count_selection_gate,
    compile_institutional_law_selection_gate,
    compile_portfolio_policy_trial_count_selection_gate,
    compile_search_trial_family,
    compile_trial_count_selection_gate,
    compile_workspace_search_trial_census,
    register_prospective_search_surface,
    register_search_trial_family,
)


def test_institutional_law_gate_counts_unfinished_frozen_trials():
    ids = [character * 64 for character in "abc"]
    family = compile_search_trial_family(
        owner="paper-owner", trial_family_id="laws:fixed",
        research_question="Which laws transfer?", purpose="causal_law_evaluation",
        model_family="institutional_strategy_laws", selection_unit="law_candidate",
        candidate_ids=ids, declared_at="2026-01-01T00:00:00Z",
        outcome_access_after="2026-02-01T00:00:00Z",
        generator_receipts=("generator:fixed",), source_refs=("learning.json",),
    )
    learning = {
        "generated_at": "2026-03-01T00:00:00Z",
        "candidates": [{"law_sha256": value} for value in ids],
        "evaluations": [{
            "law_sha256": ids[0], "law_key": "law-a@1",
            "status": "prospective_transfer_candidate", "promotion_eligible": True,
            "environment_evaluations": [{"pooled_two_sided_p_value": 0.01}],
        }],
    }

    gate = compile_institutional_law_selection_gate(family=family, learning=learning)

    assert gate["status"] == "passes_familywise_screen"
    assert gate["eligible_law_ids"] == [ids[0]]
    assert gate["unresolved_law_count"] == 2


def test_trial_family_is_permutation_invariant_and_covers_exact_law_search(tmp_path):
    (tmp_path / "workspace.yaml").write_text(
        "golden_store: state/golden_store.sqlite3\n", encoding="utf-8",
    )
    learning_dir = tmp_path / "institutional_learning"
    learning_dir.mkdir()
    candidates = [
        {"law_key": "law-a@1", "law_sha256": "a" * 64},
        {"law_key": "law-b@1", "law_sha256": "b" * 64},
    ]
    (learning_dir / "latest.json").write_text(json.dumps({
        "input_sha256": "c" * 64,
        "state_sha256": "d" * 64,
        "candidates": candidates,
    }), encoding="utf-8")

    def family(ids):
        return compile_search_trial_family(
            owner="paper-owner", trial_family_id="laws:census-1",
            research_question="Do either of these laws transfer?",
            purpose="causal_law_evaluation", model_family="institutional_strategy_laws",
            selection_unit="law_candidate", candidate_ids=ids,
            declared_at="2026-01-01T00:00:00Z",
            outcome_access_after="2026-02-01T00:00:00Z",
            generator_receipts=("generator:census-1",),
            source_refs=("institutional_learning/latest.json",),
        )

    forward = family(("a" * 64, "b" * 64))
    assert forward == family(("b" * 64, "a" * 64))
    assert register_search_trial_family(tmp_path, forward)["status"] == "registered"
    assert register_search_trial_family(tmp_path, forward)["status"] == "already_registered"
    census = compile_workspace_search_trial_census(tmp_path)
    law_surface = census["search_surfaces"][0]
    assert law_surface["registry_covered"] is True
    assert law_surface["evidence_use"] == "multiplicity_eligible_after_settlement"
    assert census["registered_trial_count"] == 2

    changed = {**forward, "research_question": "Changed after registration"}
    changed.pop("trial_family_sha256")
    from ztare.common.equivariance import stable_sha256
    changed["trial_family_sha256"] = stable_sha256(changed)
    with pytest.raises(ValueError, match="already committed"):
        register_search_trial_family(tmp_path, changed)

    prospective = dict(
        owner="paper-owner", trial_family_id="closed-book:90d:models",
        research_question="Which model predicts the prospective block?",
        model_family="closed_book_world_models", selection_unit="forecast_model",
        candidate_ids=("model-a", "model-b"),
        outcome_access_after="2026-03-01T00:00:00Z",
        generator_receipts=("closed-book:first",), source_refs=("runs/first.json",),
    )
    assert register_prospective_search_surface(
        tmp_path, declared_at="2026-01-01T00:00:00Z", **prospective,
    )["status"] == "registered"
    assert register_prospective_search_surface(
        tmp_path, declared_at="2026-01-02T00:00:00Z", **prospective,
    )["status"] == "already_registered"


def test_trial_count_gate_tightens_when_search_family_grows():
    def evaluate(candidate_count):
        model_ids = ["baseline", *[f"candidate-{index}" for index in range(candidate_count - 1)]]
        hashes = {model_id: model_id * 8 for model_id in model_ids}
        family = compile_search_trial_family(
            owner="paper-owner", trial_family_id=f"models:{candidate_count}",
            research_question="Does the selected model beat the baseline?",
            purpose="alpha_evidence", model_family="world_model_tournament",
            selection_unit="world_model", candidate_ids=reversed(tuple(hashes.values())),
            declared_at="2026-01-01T00:00:00Z",
            outcome_access_after="2026-02-01T00:00:00Z",
            generator_receipts=("generator:selection-gate",),
            source_refs=("tournament-profile.json",),
        )
        tournament = {
            "as_of": "2026-03-01T00:00:00Z", "alpha": 0.05,
            "baseline_model_id": "baseline", "inference_sufficient": True,
            "inference_block_count": 12, "min_inference_blocks": 8,
            "transaction_cost_bps": 10.0,
            "evaluation_integrity": {"alpha_evidence_eligible": True},
            "model_tracks": [
                {"model": {"model_id": model_id, "model_sha256": hashes[model_id]}}
                for model_id in reversed(model_ids)
            ],
            "evaluation_matrix": {
                "complete_matrix": True, "model_ids": model_ids,
                "episode_ids": [f"episode-{index}" for index in range(12)],
                "forecast_sha256s": [
                    f"{model_id}:{index}" for model_id in model_ids for index in range(12)
                ],
                "matrix_sha256": "matrix",
            },
            "model_metrics": [
                {"model_id": model_id, "net_excess_return": {"mean": (
                    0.02 if model_id == "candidate-0" else 0.0
                )}} for model_id in model_ids
            ],
            "paired_comparisons": [{
                "left_model_id": "baseline", "right_model_id": "candidate-0",
                "dimension": "economic_loss", "observed_delta": 0.02,
                "p_value": 0.02, "n_paired": 12,
            }],
        }
        return compile_trial_count_selection_gate(family=family, tournament=tournament)

    two_trials = evaluate(2)
    three_trials = evaluate(3)
    assert two_trials["status"] == "passes_familywise_screen"
    assert three_trials["status"] == "fails_familywise_screen"
    assert two_trials["familywise_adjusted_p_value"] == 0.04
    assert three_trials["familywise_adjusted_p_value"] == 0.06
    assert three_trials["uncomputed_methods"]["deflated_sharpe_ratio"]["status"] == "not_computed"


def test_matured_prospective_adapters_require_complete_after_cost_blocks():
    declared = dict(
        owner="paper-owner", research_question="Which frozen candidate wins after costs?",
        purpose="alpha_evidence", selection_unit="candidate",
        declared_at="2026-01-01T00:00:00Z",
        outcome_access_after="2026-02-01T00:00:00Z",
        generator_receipts=("generator:prospective",), source_refs=("runs/",),
    )
    closed_family = compile_search_trial_family(
        trial_family_id="closed:2", model_family="closed_book_world_models",
        candidate_ids=("baseline-v1", "candidate-v1"), **declared,
    )
    closed_tournament = {
        "as_of": "2026-03-01T00:00:00Z", "mode": "prospective_shadow",
        "alpha": 0.05, "baseline_model_id": "baseline",
        "inference_sufficient": True, "inference_block_count": 8,
        "min_inference_blocks": 8, "transaction_cost_bps": 10.0,
        "evaluation_integrity": {
            "alpha_evidence_eligible": True,
            "evidence_authority": "matured_prospective_evidence",
        },
        "model_tracks": [
            {"model": {"model_id": "baseline", "model_sha256": "b", "trial_family_id": "baseline-v1"}},
            {"model": {"model_id": "candidate", "model_sha256": "c", "trial_family_id": "candidate-v1"}},
        ],
        "evaluation_matrix": {
            "complete_matrix": True, "model_ids": ["baseline", "candidate"],
            "episode_ids": [f"e{index}" for index in range(8)],
            "forecast_sha256s": [f"{model}:{index}" for model in ("baseline", "candidate") for index in range(8)],
        },
        "model_metrics": [
            {"model_id": "baseline", "net_excess_return": {"mean": 0.0}},
            {"model_id": "candidate", "net_excess_return": {"mean": 0.02}},
        ],
        "paired_comparisons": [{
            "left_model_id": "baseline", "right_model_id": "candidate",
            "dimension": "economic_loss", "observed_delta": 0.02,
            "p_value": 0.01, "n_paired": 8,
        }],
    }
    assert compile_closed_book_trial_count_selection_gate(
        family=closed_family, tournament=closed_tournament,
    )["status"] == "passes_familywise_screen"

    policy_family = compile_search_trial_family(
        trial_family_id="policy:2", model_family="portfolio_policy",
        candidate_ids=("equal_weight_qualified@1", "value_weighted@1"), **declared,
    )
    runs, settlements = [], []
    for index in range(8):
        run_id = f"run-{index}"
        runs.append({
            "run_id": run_id, "opened_at": f"2026-01-{index + 1:02d}T00:00:00Z",
            "end_at": "2026-02-01T00:00:00Z",
            "policies": [
                {"policy_id": "equal_weight_qualified", "version": "1"},
                {"policy_id": "value_weighted", "version": "1"},
            ],
            "trial_family": {"trial_family_id": "policy:2"},
            "settlement_contract": {"transaction_cost_bps": 10.0},
        })
        settlements.append({
            "run_id": run_id, "inference_block_id": f"block-{index}",
            "trial_family_id": "policy:2",
            "evaluated_at": "2026-03-01T00:00:00Z",
            "end_prices": {"SPY": {"available_at": "2026-02-02T00:00:00Z"}},
            "policy_scores": [
                {"policy_id": "equal_weight_qualified", "portfolio_excess_return_after_cost": 0.0, "transaction_cost": 0.001},
                {"policy_id": "value_weighted", "portfolio_excess_return_after_cost": 0.02, "transaction_cost": 0.001},
            ],
        })
    review = {
        "trial_family": {"trial_family_id": "policy:2"},
        "run_ids": [row["run_id"] for row in runs],
        "survivor_set": {
            "alpha": 0.05, "min_inference_blocks": 8,
            "inference_block_count": 8, "inference_sufficient": True,
            "paired_comparisons": [{
                "left_model_id": "equal_weight_qualified",
                "right_model_id": "value_weighted",
                "dimension": "negative_portfolio_excess_return_after_cost",
                "observed_delta": 0.02, "p_value": 0.01, "n_paired": 8,
            }],
        },
    }
    gate = compile_portfolio_policy_trial_count_selection_gate(
        family=policy_family, review=review, runs=runs, settlements=settlements,
    )
    assert gate["status"] == "passes_familywise_screen"
    settlements[0]["policy_scores"].pop()
    assert "complete_exact_policy_by_episode_matrix" in compile_portfolio_policy_trial_count_selection_gate(
        family=policy_family, review=review, runs=runs, settlements=settlements,
    )["missing_inputs"]
