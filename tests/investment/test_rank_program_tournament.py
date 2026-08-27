import csv
from datetime import datetime, timedelta, timezone
import json

from ztare.common.equivariance import stable_sha256
from ztare.investment.golden_store import GoldenStore
from ztare.investment.rank_program_tournament import (
    DIAGNOSTIC_HORIZON_DAYS,
    PRIMARY_HORIZON_DAYS,
    compile_rank_program_input,
    open_rank_program_tournament,
    rank_program_price_refresh_entity_ids,
    rank_program_tournament_status,
    settle_rank_program_tournaments,
)

BLOCK_STRIDE = PRIMARY_HORIZON_DAYS + 1


def _at(day: int) -> str:
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)).isoformat().replace("+00:00", "Z")


def _candidate(entity_id, components, *, eligible=True, screen_thresholds_pass=True):
    components = {str(name): float(value) for name, value in components.items()}
    body = {
        "candidate_id": entity_id, "entity_id": entity_id,
        "rank_program_eligible": eligible,
        "eligibility_checks": {
            "component_contract_complete": True,
            "evidence_contract_pass": eligible,
            "screen_thresholds_pass": screen_thresholds_pass,
        },
        "components": components,
        "source_refs": [f"source:{entity_id}"],
    }
    return {**body, "candidate_sha256": stable_sha256(body)}


def _discovery(
    block, *, suffix="", compiler_version="test-family-v5",
    policy_id="evidence-and-component-completeness-v2", ineligible=(),
):
    equity = {
        "A": (1, 0, 0, 0), "B": (0, .6, .6, .6), "C": (.35, .35, .35, .35),
    }
    equity_names = (
        "durable_earnings_power", "price_implied_excess_return",
        "earnings_power_margin", "low_implied_growth",
    )
    fund = {
        "F1": (1, 1, 1, 0, 0, 0),
        "F2": (0, 0, 0, .8, .8, 1),
        "F3": (.46,) * 6,
    }
    fund_names = (
        "earnings_yield", "book_to_price",
        "factor_return_after_fee",
        "factor_return_per_volatility", "drawdown_resilience", "fee_efficiency",
    )
    run_id = f"discovery-{block}{suffix}"
    as_of = _at(block * BLOCK_STRIDE)
    rank_input = compile_rank_program_input(
        discovery_run_id=run_id, as_of=as_of, compiler_version=compiler_version,
        eligibility_policy_id=policy_id,
        lanes=(
            {
                "lane_id": "public_equity", "entity_kind": "public_equity",
                "benchmark_id": "SPY",
                "candidates": [
                    _candidate(
                        key, dict(zip(equity_names, values)), eligible=key not in ineligible,
                        screen_thresholds_pass=key != "B",
                    )
                    for key, values in equity.items()
                ],
            },
            {
                "lane_id": "public_fund:us_equity", "entity_kind": "public_fund",
                "benchmark_id": "SPY",
                "candidates": [
                    _candidate(key, dict(zip(fund_names, values)), eligible=key not in ineligible)
                    for key, values in fund.items()
                ],
            },
            {
                "lane_id": "public_fund:thin", "entity_kind": "public_fund",
                "benchmark_id": "SPY",
                "candidates": [_candidate("F4", dict(zip(fund_names, (.5,) * 6)))],
            },
        ),
        enumerated_candidate_count=7, source_refs=(f"source-run:{block}",),
    )
    body = {
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": run_id,
        "as_of": as_of, "completed_at": as_of, "compiler_version": compiler_version,
        "enumeration": {"enumerated_count": 7},
        "rank_program_input": rank_input,
    }
    return {**body, "run_sha256": stable_sha256(body)}


def test_fixed_rank_programs_need_eight_prospective_blocks(tmp_path):
    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True)
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "observation_id", "entity_id", "metric_id", "value", "observed_at",
            "available_at", "source_ref",
        ))
        writer.writeheader()
        for block in range(8):
            for offset, prices in ((0, {}), (PRIMARY_HORIZON_DAYS, {"A": 120, "C": 110, "F1": 120, "F3": 110})):
                observed = _at(block * BLOCK_STRIDE + offset)
                for entity_id in ("A", "B", "C", "F1", "F2", "F3", "F4", "SPY"):
                    writer.writerow({
                        "observation_id": f"{block}-{offset}-{entity_id}",
                            "entity_id": entity_id, "metric_id": "adjusted_price",
                        "value": prices.get(entity_id, 100), "observed_at": observed,
                        "available_at": observed, "source_ref": f"price:{block}:{offset}:{entity_id}",
                    })

    store_path = tmp_path / "state" / "golden.sqlite3"
    for block in range(8):
        opened = open_rank_program_tournament(
            tmp_path, owner="paper", store_path=store_path, discovery_run=_discovery(block),
            horizon_days=PRIMARY_HORIZON_DAYS,
            opened_at=_at(block * BLOCK_STRIDE), sealed_at=_at(block * BLOCK_STRIDE),
        )
        assert all(
            len({ticket["candidate_set_sha256"] for ticket in lane["ranking_tickets"]}) == 1
            for lane in opened["lanes"]
        )
        assert opened["deferred_lanes"][0]["reason"] == (
            "fewer_than_two_score_independent_eligible_candidates"
        )
        settle_rank_program_tournaments(
            tmp_path, owner="paper", store_path=store_path,
            as_of=_at(block * BLOCK_STRIDE + PRIMARY_HORIZON_DAYS),
        )

    status = rank_program_tournament_status(tmp_path)
    assert status["settled_count"] == 8
    assert status["review"]["survivor_set"]["inference_block_count"] == 8
    equity_review = status["review"]["reviews_by_entity_kind"]["public_equity"]
    assert set(equity_review["program_ids"]) == {
        "coordinate_equal_v4", "family_weighted_v5",
        "quality_expectations_balanced_v1", "quality_only_v1", "expectations_only_v1",
    }
    assert set(status["review"]["reviews_by_entity_kind"]["public_fund"]["program_ids"]) == {
        "coordinate_equal_v5", "factor_return_after_fee_v1", "family_weighted_v6",
    }
    assert status["review"]["automatic_policy_change"] is False
    store = GoldenStore(store_path)
    assert len(store.list_leaves(owner="paper", object_kind="rank_program_tournament_run")) == 8
    assert len(store.list_leaves(owner="paper", object_kind="rank_program_tournament_settlement")) == 8


def test_corrected_eligibility_supersedes_only_before_entry(tmp_path):
    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True)
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "observation_id", "entity_id", "metric_id", "value", "observed_at",
            "available_at", "source_ref",
        ))
        writer.writeheader()
        for entity_id in ("A", "B", "C", "F1", "F2", "F3", "F4", "SPY"):
            writer.writerow({
                "observation_id": entity_id, "entity_id": entity_id,
                "metric_id": "adjusted_price", "value": 100,
                "observed_at": _at(0), "available_at": _at(0),
                "source_ref": f"price:{entity_id}",
            })

    store_path = tmp_path / "state" / "golden.sqlite3"
    prior = open_rank_program_tournament(
        tmp_path, owner="paper", store_path=store_path, discovery_run=_discovery(0),
        opened_at=_at(0), sealed_at=_at(0),
    )
    successor = open_rank_program_tournament(
        tmp_path, owner="paper", store_path=store_path,
        discovery_run=_discovery(
            0, suffix="-v7-contracted", compiler_version="test-family-v7",
            policy_id="evidence-and-component-completeness-v3", ineligible={"C", "F3"},
        ),
        opened_at=_at(0), sealed_at=_at(0),
    )
    supersession = json.loads((
        tmp_path / "rank_program_tournament" / "supersessions" / f"{prior['run_id']}.json"
    ).read_text())
    assert successor["replayed"] is False
    assert sum(row["candidate_count"] for row in successor["lanes"]) < sum(
        row["candidate_count"] for row in prior["lanes"]
    )
    assert supersession["reason"] == "eligibility_policy_change_before_entry_binding"
    assert rank_program_tournament_status(tmp_path)["next_activation"] == (
        "bind_next_postseal_common_price"
    )
    assert rank_program_price_refresh_entity_ids(tmp_path, as_of=_at(0)) == [
        "A", "B", "F1", "F2", "SPY",
    ]

    settle_rank_program_tournaments(
        tmp_path, owner="paper", store_path=store_path, as_of=_at(0),
    )
    assert rank_program_tournament_status(tmp_path)["next_activation"] == (
        "await_first_rank_outcome_maturity"
    )
    assert rank_program_price_refresh_entity_ids(tmp_path, as_of=_at(1)) == []
    replay = open_rank_program_tournament(
        tmp_path, owner="paper", store_path=store_path,
        discovery_run=_discovery(
            0, suffix="-v7-expanded", compiler_version="test-family-v7",
            policy_id="evidence-and-component-completeness-v3",
        ),
        opened_at=_at(0), sealed_at=_at(0),
    )
    assert replay["run_id"] == successor["run_id"]
    assert replay["replayed"] is True
    assert not (
        tmp_path / "rank_program_tournament" / "supersessions" / f"{successor['run_id']}.json"
    ).exists()

    diagnostic = open_rank_program_tournament(
        tmp_path, owner="paper", store_path=store_path,
        discovery_run=_discovery(0, suffix="-diagnostic"),
        horizon_days=DIAGNOSTIC_HORIZON_DAYS,
        opened_at=_at(0), sealed_at=_at(0),
    )
    status = rank_program_tournament_status(tmp_path)
    assert status["latest_run"]["run_id"] == successor["run_id"]
    assert status["latest_diagnostic_run"]["run_id"] == diagnostic["run_id"]
