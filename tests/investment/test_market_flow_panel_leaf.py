import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.golden_store import GoldenStore, record_market_flow_experiment
from ztare.investment.market_flow_shadow import (
    MARKET_FLOW_SHADOW_RUN_SCHEMA,
    _source_date_information_set,
    compile_market_flow_research_activation,
    run_market_flow_shadow_cycle,
)


def test_cross_sectional_flow_evidence_is_an_immutable_experiment_leaf(tmp_path):
    body = {
        "schema": "jaggedthoughts-cross-sectional-market-flow-evidence-v2",
        "experiment_id": "panel-current",
        "as_of": "2026-08-14T00:00:00Z",
        "authority": "experiment_only",
        "capital_authority": False,
        "source_refs": ["public-price-receipt"],
    }
    result = {**body, "evidence_sha256": stable_sha256(body)}
    store = GoldenStore(tmp_path / "golden.sqlite3")

    leaf_sha = record_market_flow_experiment(store, owner="paper", result=result)
    leaf = store.get_leaf(leaf_sha)

    assert leaf["object_kind"] == "market_flow_experiment"
    assert leaf["epoch"] == result["evidence_sha256"]
    assert leaf["payload"] == result
    assert leaf["source_refs"] == ["public-price-receipt"]
    assert store.verify()["ok"] is True


def test_market_flow_result_selects_a_bounded_research_consequence():
    run_body = {
        "schema": MARKET_FLOW_SHADOW_RUN_SCHEMA,
        "project_id": "flow-project",
        "model_bundle_sha256": "bundle-1",
        "candidate_sha256": "candidate-1",
        "prospective_promotion_eligible": False,
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}

    def activation(survivors):
        tournament_body = {
            "schema": "synthetic-tournament",
            "inference_sufficient": True,
            "survivor_model_ids": survivors,
            "source_refs": [f"run:{run['run_sha256']}"],
        }
        return compile_market_flow_research_activation(
            {**tournament_body, "tournament_sha256": stable_sha256(tournament_body)},
            run,
        )

    successor = activation(["lagrangian_probability_current_rejected_shadow"])
    retirement = activation(["empirical_markov"])

    assert successor["action"] == "successor_research_due"
    assert successor["source_run_sha256"] == run["run_sha256"]
    assert retirement["action"] == "retire_research_due"
    assert successor["automatic_model_mutation"] is False
    assert successor["capital_authority"] is False


def test_market_flow_source_date_identity_ignores_same_date_refetches():
    first = {
        "experiment_id": "panel-current",
        "state_date": "2026-08-21",
        "feature_observation_ids_sha256": "first-fetch",
    }
    refetch = {
        **first,
        "feature_observation_ids_sha256": "second-fetch",
        "feature_available_at": "2026-08-23T02:00:00Z",
    }

    assert _source_date_information_set(first) == _source_date_information_set(refetch)
    assert _source_date_information_set(first) != _source_date_information_set({
        **first, "state_date": "2026-08-22",
    })


def test_market_flow_settlement_refreshes_latest_before_later_failure(
    tmp_path, monkeypatch,
):
    output = tmp_path / "shadow"
    run = {
        "snapshot_sha256": "snapshot-1",
        "snapshot": {"snapshot_sha256": "snapshot-1"},
    }
    (output / "runs").mkdir(parents=True)
    (output / "runs" / "run-1.json").write_text(json.dumps(run), encoding="utf-8")

    settlement_body = {
        "schema": "jaggedthoughts-cross-sectional-market-flow-settlement-v1",
        "snapshot_sha256": "snapshot-1",
        "status": "settled",
    }
    settlement = {
        **settlement_body,
        "settlement_sha256": stable_sha256(settlement_body),
    }
    monkeypatch.setattr(
        "ztare.investment.market_flow_shadow.settle_cross_sectional_flow_snapshot",
        lambda *_args, **_kwargs: settlement,
    )
    monkeypatch.setattr(
        "ztare.investment.market_flow_shadow.compile_cross_sectional_flow_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("later stage failed")),
    )

    with pytest.raises(ValueError, match="later stage failed"):
        run_market_flow_shadow_cycle(
            profile_path=tmp_path / "profile.yaml",
            workspace=tmp_path,
            project_dir=tmp_path / "project",
            output_dir=output,
            as_of="2026-08-23T03:00:00Z",
            owner="paper",
        )

    latest = json.loads((output / "latest.json").read_text(encoding="utf-8"))
    assert latest["settlement_checkpoint"] == {
        "as_of": "2026-08-23T03:00:00Z",
        "run_count": 1,
        "settled_count": 1,
        "pending_count": 0,
    }
    assert latest["paper_policy_authority"] is False
    assert latest["capital_authority"] is False
