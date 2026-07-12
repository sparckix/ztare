"""Tests for ztare.common.work_plan — 12+ behavioral tests + benchmark."""
import json
import tempfile
import time
from pathlib import Path

import pytest

from ztare.common.work_plan import (
    WorkPlanConfluenceError,
    WorkPlanContractError,
    fanout,
    partition,
    run,
    sequential,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _add(a, b):
    return a + b


def _sub(a, b):
    """Non-associative: (a-b)-c != a-(b-c)."""
    return a - b


def _identity(x):
    return x


# ── 1. Missing merge raises WorkPlanContractError ───────────────────────────


def test_fanout_missing_merge_raises():
    with pytest.raises(WorkPlanContractError, match="fanout"):
        fanout(_identity, K=2, merge={})


def test_partition_missing_merge_raises():
    with pytest.raises(WorkPlanContractError, match="partition"):
        partition([1, 2], _identity, merge={"kind": "unknown"})


def test_fanout_bad_merge_kind_raises():
    with pytest.raises(WorkPlanContractError):
        fanout(_identity, K=2, merge={"kind": "bogus"})


# ── 2. Select picks rank-max ─────────────────────────────────────────────────


def test_select_picks_rank_max():
    # Lane i returns i; rank_fn is identity; expect 4 for K=5
    plan = fanout(
        lambda ctx: ctx,
        K=5,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
    )
    assert run(plan) == 4


# ── 3. Partition + reduce merges shard results ───────────────────────────────


def test_partition_reduce_sums_shards():
    plan = partition(
        [1, 2, 3, 4, 5],
        worker_fn=_identity,
        merge={"kind": "reduce", "fn": _add},
    )
    assert run(plan) == 15


# ── 4. Shuffled-order reduce equality (associative fn) ───────────────────────


def test_confluence_check_passes_for_associative():
    plan = fanout(
        lambda ctx: ctx,
        K=6,
        diversify=lambda i: i + 1,
        merge={"kind": "reduce", "fn": _add},
    )
    # sum(1..6)=21; should pass confluence
    result = run(plan, confluence_check=True)
    assert result == 21


# ── 5. Non-associative reducer caught by confluence_check ────────────────────


def test_confluence_check_catches_non_associative():
    # subtraction is non-associative; 4 values -> likely diverges
    plan = fanout(
        lambda ctx: ctx,
        K=4,
        diversify=lambda i: i + 1,   # [1,2,3,4]
        merge={"kind": "reduce", "fn": _sub},
    )
    # In-order: ((1-2)-3)-4 = -8
    # Shuffled (seed=4): shuffle of [1,2,3,4] with Random(4) -> [2,3,1,4] or similar
    # Result differs → should raise
    with pytest.raises(WorkPlanConfluenceError):
        run(plan, confluence_check=True)


# ── 6. Lane exception excluded, siblings not aborted ─────────────────────────


def test_lane_exception_excluded_not_fatal():
    call_log: list[int] = []

    def sometimes_raises(ctx):
        call_log.append(ctx)
        if ctx == 2:
            raise ValueError("boom")
        return ctx * 10

    plan = fanout(
        sometimes_raises,
        K=4,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
    )
    result = run(plan)
    # Lane 2 excluded; remaining [0,10,30]; select picks 30
    assert result == 30
    assert len(call_log) == 4   # all siblings still ran


# ── 7. Verifier excludes failing lanes; excluded_count reflects it ───────────


def test_verifier_excludes_lanes():
    plan = fanout(
        lambda ctx: ctx,
        K=5,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
        verifier=lambda v: v % 2 == 0,   # only even values pass
    )
    # Values: 0,1,2,3,4 -> 1,3 excluded -> good: 0,2,4
    result = run(plan)
    assert result == 4   # max of evens


def test_verifier_excluded_count_in_receipt():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    plan = fanout(
        lambda ctx: ctx,
        K=4,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
        verifier=lambda v: v >= 2,   # excludes 0,1 -> excluded_count=2
    )
    run(plan, receipts_path=path)
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    assert rows[0]["excluded_count"] == 2


# ── 8. Attestation rows well-formed ─────────────────────────────────────────


def test_attestation_rows_well_formed():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    plan = partition(
        [10, 20, 30],
        worker_fn=_identity,
        merge={"kind": "reduce", "fn": _add},
    )
    run(plan, receipts_path=path)

    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "ztare.work_plan_attestation.v1"
    assert row["node_kind"] == "partition"
    assert row["lanes"] == 3
    assert row["merge_kind"] == "reduce"
    assert row["merged"] is True
    assert "wall_seconds" in row
    assert row["excluded_count"] == 0


def test_attestation_select_has_winner_index():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    plan = fanout(
        lambda ctx: ctx,
        K=3,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
    )
    run(plan, receipts_path=path)
    row = json.loads(Path(path).read_text().splitlines()[0])
    assert "winner_index" in row


# ── 9. Sequential chains outputs ────────────────────────────────────────────


def test_sequential_chains_outputs():
    # step1 produces 5; step2 doubles it -> 10
    plan = sequential(
        lambda _: 5,
        lambda x: x * 2,
    )
    assert run(plan) == 10


def test_sequential_with_parallel_node():
    inner = fanout(
        lambda ctx: ctx,
        K=3,
        diversify=lambda i: i + 1,  # [1,2,3]
        merge={"kind": "reduce", "fn": _add},
    )
    # sequential: run fanout (sum=6), then multiply by 2
    plan = sequential(inner, lambda x: x * 2)
    assert run(plan) == 12


# ── 10. max_workers honored ─────────────────────────────────────────────────


def test_max_workers_limits_parallelism():
    def slow(_):
        time.sleep(0.2)
        return 1

    plan4 = fanout(slow, K=4, diversify=lambda i: i,
                   merge={"kind": "reduce", "fn": _add})

    t0 = time.perf_counter()
    result = run(plan4, max_workers=1)
    t_serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    result = run(plan4, max_workers=4)
    t_parallel = time.perf_counter() - t0

    assert result == 4  # both produce 4
    # serial >= 4x sleep; parallel < 2x sleep
    assert t_serial >= 0.7
    assert t_parallel < 0.6


# ── 11. Fanout diversify receives distinct lane indices ──────────────────────


def test_fanout_diversify_receives_distinct_indices():
    seen: list[int] = []

    def capture(ctx):
        seen.append(ctx)
        return ctx

    plan = fanout(
        capture,
        K=5,
        diversify=lambda i: i,
        merge={"kind": "select", "rank_fn": lambda x: x},
    )
    run(plan)
    assert sorted(seen) == [0, 1, 2, 3, 4]


# ── 12. Empty shards edge case ───────────────────────────────────────────────


def test_partition_empty_shards_raises():
    plan = partition([], _identity, merge={"kind": "reduce", "fn": _add})
    with pytest.raises(WorkPlanContractError, match="all .* lanes excluded"):
        run(plan)


# ── 13. collect merge kind ───────────────────────────────────────────────────


def test_collect_returns_all_good_lanes_in_lane_index_order():
    """collect returns a list of all passing lane results, order-canonicalized by lane index."""
    plan = fanout(
        lambda ctx: ctx * 10,
        K=4,
        diversify=lambda i: i,
        merge={"kind": "collect"},
    )
    result = run(plan)
    assert result == [0, 10, 20, 30]


def test_collect_attestation_has_collected_count():
    """Attestation row for collect reports collected_count, not winner_index or merged."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    plan = fanout(
        lambda ctx: ctx,
        K=3,
        diversify=lambda i: i,
        merge={"kind": "collect"},
    )
    result = run(plan, receipts_path=path)
    assert result == [0, 1, 2]
    row = json.loads(Path(path).read_text().splitlines()[0])
    assert row["schema"] == "ztare.work_plan_attestation.v1"
    assert row["merge_kind"] == "collect"
    assert row["collected_count"] == 3
    assert "winner_index" not in row
    assert "merged" not in row


# ── Benchmark (under __main__; not collected by pytest unless slow marker) ───


def _benchmark():
    import sys

    K = 8
    SLEEP = 0.5
    SHARDS = 16
    SHARD_SLEEP = 0.2
    SHARD_WORKERS = 8

    print("\n── work_plan benchmark ──────────────────────────────────")

    # fanout parallel vs sequential
    plan_parallel = fanout(
        lambda ctx: (time.sleep(SLEEP), SLEEP)[1],
        K=K,
        diversify=lambda i: i,
        merge={"kind": "reduce", "fn": _add},
    )
    t0 = time.perf_counter()
    run(plan_parallel, max_workers=K)
    t_par = time.perf_counter() - t0

    t0 = time.perf_counter()
    total = 0.0
    for _ in range(K):
        time.sleep(SLEEP)
        total += SLEEP
    t_seq = time.perf_counter() - t0

    speedup = t_seq / t_par
    print(f"fanout K={K} sleep={SLEEP}s: parallel={t_par:.2f}s  sequential={t_seq:.2f}s  speedup={speedup:.1f}x")

    # partition 16 shards at max_workers=8
    plan_part = partition(
        list(range(SHARDS)),
        worker_fn=lambda s: (time.sleep(SHARD_SLEEP), SHARD_SLEEP)[1],
        merge={"kind": "reduce", "fn": _add},
    )
    t0 = time.perf_counter()
    run(plan_part, max_workers=SHARD_WORKERS)
    t_part = time.perf_counter() - t0
    print(f"partition {SHARDS} shards sleep={SHARD_SLEEP}s max_workers={SHARD_WORKERS}: wall={t_part:.2f}s  (ideal={SHARDS*SHARD_SLEEP/SHARD_WORKERS:.2f}s)")
    print("── done ─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    _benchmark()
