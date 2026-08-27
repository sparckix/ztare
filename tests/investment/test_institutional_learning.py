import math
from copy import deepcopy

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.institutional_learning import (
    compile_historical_accounting_replay,
    compile_law_candidate,
    compile_law_policy_influence,
    default_law_catalog,
    evaluate_investment_law,
)
from ztare.investment.law_search import search_law_programs


def _episodes(year, blocks, *, reverse=False, industry="transfer"):
    rows = []
    for block in range(blocks):
        for entity in range(12):
            durability = -1 + 2 * entity / 11
            value = -1 + 2 * ((entity * 5 + block * 3) % 12) / 11
            noise = 0.005 * math.sin((entity + 1) * (block + 2))
            metrics = {
                "earnings_durability": durability,
                "price_implied_excess_return": value,
                "implied_growth": noise,
                "active_return": (-1 if reverse else 1) * durability * value + noise,
            }
            opened = f"{year + block // 10:04d}-{block % 10 + 1:02d}-01T00:00:00Z"
            body = {
                "episode_id": f"{year}-{block}-{entity}-{industry}",
                "inference_block_id": f"{year}-{block}",
                "entity_id": f"X{entity}", "entity_kind": "public_equity",
                "horizon_days": 90, "opened_at": opened, "end_at": opened,
                "outcome_available_at": opened, "settlement_status": "settled",
                "metrics": metrics,
                "metric_roles": {
                    "predictor_metric_ids": [
                        "earnings_durability", "price_implied_excess_return", "implied_growth",
                    ],
                    "outcome_metric_ids": ["active_return"],
                },
                "categories": {
                    "horizon_days": "90", "industry_id": industry,
                    "quality_band": "mixed", "expectations_band": "restrained",
                    "momentum_regime": "positive",
                },
            }
            rows.append({**body, "phenotype_episode_sha256": stable_sha256(body)})
    return rows


def test_law_contract_forbids_target_leakage_and_backdating():
    seed = default_law_catalog()["candidates"][0]
    assert compile_law_candidate(seed)["not_before"] == seed["created_at"]

    leaked = deepcopy(seed)
    leaked["predictor_program"]["nodes"][0]["arguments"][0] = {"metric": "active_return"}
    with pytest.raises(ValueError, match="cannot consume or produce"):
        compile_law_candidate(leaked)

    selected_on_target = deepcopy(seed)
    selected_on_target["cohort"]["conditions"] = [
        {"path": "active_return", "operator": "gt", "value": 0},
    ]
    with pytest.raises(ValueError, match="cannot select or partition"):
        compile_law_candidate(selected_on_target)

    backdated = deepcopy(seed)
    backdated["not_before"] = "2026-08-11T03:48:36Z"
    with pytest.raises(ValueError, match="cannot precede"):
        compile_law_candidate(backdated)


def test_historical_accounting_replay_keeps_retrospective_boundary(tmp_path, monkeypatch):
    histories = {}
    for entity_index in range(4):
        entity = f"X{entity_index}"
        reports = []
        for year in range(2010, 2020):
            margin = 0.05 * entity_index + 0.002 * (year - 2010)
            body = {
                "entity_id": entity,
                "available_at": f"{year + 1}-03-01T00:00:00Z",
                "history": [{
                    "observed_at": f"{year}-12-31T00:00:00Z",
                    "owner_earnings_margin": margin,
                }],
                "scores": {"durable_earnings_power": 0.2 * entity_index + 0.01 * year},
                "source_refs": [f"filing:{entity}:{year}"],
            }
            reports.append({**body, "quality_report_sha256": stable_sha256(body)})
        histories[entity] = tuple(reports)
    monkeypatch.setattr(
        "ztare.investment.institutional_learning.compile_company_quality_histories",
        lambda **_kwargs: histories,
    )

    replay = compile_historical_accounting_replay(
        tmp_path, as_of="2021-04-01T00:00:00Z", entity_ids=histories,
    )

    assert replay["episode_count"] == 36
    assert replay["evaluation_integrity"]["evaluation_class"] == (
        "deterministic_point_in_time_mechanical_replay"
    )
    assert replay["durability_model"]["status"] == "retrospective_rank_signal_detected"
    assert replay["durability_model"]["prospective_transfer_eligible"] is False
    assert replay["model_selection_status"] == "current_formula_replayed_over_prior_filings"
    incremental = replay["incremental_out_of_time_comparison"]
    assert incremental["status"] == "no_supported_incremental_rank_information"
    assert all(
        row["training_cutoff_block_id"] < row["inference_block_id"]
        for row in incremental["rows"]
    )
    assert incremental["adverse_transition_follow_up"]["status"] == "not_activated"
    assert replay["return_outcome_included"] is False
    assert replay["promotion_eligible"] is replay["capital_authority"] is False


def test_recursive_law_search_transfers_then_preserves_sign_reversal():
    selection = _episodes(2025, 8, industry="selection")
    seeds = [compile_law_candidate(row) for row in default_law_catalog()["candidates"]]
    search = search_law_programs(
        selection, seeds, "2026-01-15T00:00:00Z", feature_cap=3, max_new_laws=3,
    )
    holdout_ids = set(search["searches"][0]["chronological_partition"]["holdout_block_ids"])
    reversed_holdout = []
    for episode in selection:
        body = {key: value for key, value in episode.items() if key != "phenotype_episode_sha256"}
        if episode["inference_block_id"] in holdout_ids:
            body["metrics"] = {**body["metrics"], "active_return": -body["metrics"]["active_return"]}
        reversed_holdout.append({**body, "phenotype_episode_sha256": stable_sha256(body)})
    challenged_search = search_law_programs(
        reversed_holdout, seeds, "2026-01-15T00:00:00Z", feature_cap=3, max_new_laws=3,
    )
    assert challenged_search["searches"][0]["frozen_selection"] == search["searches"][0]["frozen_selection"]
    assert challenged_search["proposal_count"] == 0
    law = compile_law_candidate(search["proposals"][0])
    assert search["proposal_count"] == 1
    assert "price_implied_excess_return" in law["mechanism"]["antecedent_concepts"]

    transfer = _episodes(2027, 8)
    result = evaluate_investment_law(
        law, selection + transfer, generated_at="2027-11-01T00:00:00Z",
    )
    assert result["cohort"]["episode_count"] == len(transfer)
    assert result["evaluation"]["status"] == "prospective_transfer_candidate"

    reversal = _episodes(2028, 2, reverse=True, industry="reversal")
    challenged = evaluate_investment_law(
        law, selection + transfer + reversal, generated_at="2028-04-01T00:00:00Z",
    )["evaluation"]
    assert challenged["status"] == "challenged_by_counterexample"
    witness = challenged["environment_evaluations"][0]["counterexamples"][0]
    assert (witness["field"], witness["value"]) == ("industry_id", "reversal")

    candidates = [
        {
            "candidate_id": row["episode_id"], "entity_id": row["entity_id"],
            "entity_kind": row["entity_kind"], "metrics": row["metrics"],
        }
        for row in transfer[:12]
    ]
    state = {
        "candidates": [law], "state_sha256": "eligible-state",
        "evaluations": [{"law_key": law["law_key"], "promotion_eligible": True, "status": "prospective_transfer_candidate"}],
    }
    active = compile_law_policy_influence(candidates, state, generated_at="2029-01-01T00:00:00Z")
    assert active["active_law_count"] == 1
    state["evaluations"][0] = {"law_key": law["law_key"], "promotion_eligible": False, "status": "challenged_by_counterexample"}
    withdrawn = compile_law_policy_influence(candidates, state, generated_at="2029-01-02T00:00:00Z")
    assert withdrawn["active_law_count"] == 0
    assert not any(row["adjustment"] for row in withdrawn["candidates"])
