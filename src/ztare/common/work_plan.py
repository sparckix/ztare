"""Division-of-labor work-plan algebra.

Three node constructors express common parallel/sequential patterns found
in the blitz/parallel-mutator pipeline; `run` executes them uniformly with
ThreadPoolExecutor, optional receipts, and an optional confluence check.

Node constructors
-----------------
fanout(task_fn, K, ...)   — best-of-K independent lanes
partition(shards, ...)    — one lane per independent data shard
sequential(*steps)        — chain of callables/nodes

Merge contract
--------------
Every parallel node requires a `merge` dict:
  {"kind": "reduce", "fn": assoc_commutative_fn}
  {"kind": "select", "rank_fn": fn}   # highest rank wins
  {"kind": "collect"}                  # return all good results as a list,
                                       # order-canonicalized by lane index
Constructing without merge raises WorkPlanContractError.

Attestation
-----------
If receipts_path is given, one JSONL row per parallel node is appended
with schema "ztare.work_plan_attestation.v1".

Confluence check
----------------
With confluence_check=True, reduce merges are verified by re-running on
a deterministically shuffled copy (seed = len(results)). Mismatch raises
WorkPlanConfluenceError — this intentionally catches non-associative reducers.

Deferred third parallel node: blackboard
----------------------------------------
fanout covers redundancy (best-of-K, log returns); partition covers
division of labor (independent shards, linear returns). Cooperative
parallelism — lanes pruning against siblings' intermediate discoveries
(proof search sharing lemmas; proposer waves seeing occupancy claims;
residual-class specialists avoiding overlapping patches) — needs a
blackboard node: workers over a MONOTONE shared store (append-only,
commutative updates). Monotonicity is the law that keeps it confluent
(same reason semi-naive datalog evaluation is order-independent).
Build it when residual-class specialists need cross-lane claim
coordination; proposer_pool.py's wave pattern is the existing consumer
that could not be expressed without it.
"""
from __future__ import annotations

import concurrent.futures
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# ── Errors ─────────────────────────────────────────────────────────────────


class WorkPlanContractError(ValueError):
    """Raised when a parallel node is constructed without a valid merge."""


class WorkPlanConfluenceError(RuntimeError):
    """Raised when a reduce merge produces different results on shuffled input."""


# ── Internal node types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class _FanoutNode:
    task_fn: Callable[[Any], Any]     # task_fn(context) -> result
    K: int
    diversify: Optional[Callable[[int], Any]]  # lane_idx -> context
    merge: dict
    verifier: Optional[Callable[[Any], bool]]


@dataclass(frozen=True)
class _PartitionNode:
    shards: list
    worker_fn: Callable[[Any], Any]   # worker_fn(shard) -> result
    merge: dict
    verifier: Optional[Callable[[Any], bool]]


@dataclass(frozen=True)
class _SequentialNode:
    steps: tuple  # each element is a callable or a _*Node


# ── Merge helpers ───────────────────────────────────────────────────────────


def _validate_merge(merge: dict, node_kind: str) -> None:
    if not isinstance(merge, dict) or merge.get("kind") not in ("reduce", "select", "collect"):
        raise WorkPlanContractError(
            f"{node_kind}: merge must be {{'kind':'reduce','fn':...}}, "
            f"{{'kind':'select','rank_fn':...}}, or {{'kind':'collect'}}; got {merge!r}"
        )
    if merge["kind"] == "reduce" and "fn" not in merge:
        raise WorkPlanContractError(f"{node_kind}: reduce merge missing 'fn'")
    if merge["kind"] == "select" and "rank_fn" not in merge:
        raise WorkPlanContractError(f"{node_kind}: select merge missing 'rank_fn'")


def _apply_merge(results: list, merge: dict) -> tuple[Any, Optional[int]]:
    """Return (merged_value, winner_index_or_None).

    For 'collect': merged_value is the list of good results in lane-index order
    (already guaranteed by the caller's sort before verifier pass).
    winner_index is None (all lanes included).
    """
    if merge["kind"] == "select":
        ranked = [(merge["rank_fn"](r), i, r) for i, r in enumerate(results)]
        ranked.sort(key=lambda x: x[0], reverse=True)
        _, winner_idx, winner = ranked[0]
        return winner, winner_idx
    if merge["kind"] == "collect":
        # ponytail: already lane-index ordered by caller; return the list as-is
        return list(results), None
    # reduce
    from functools import reduce
    fn = merge["fn"]
    return reduce(fn, results), None


def _apply_reduce_only(results: list, fn: Callable) -> Any:
    from functools import reduce
    return reduce(fn, results)


# ── Public constructors ─────────────────────────────────────────────────────


def fanout(
    task_fn: Callable[[Any], Any],
    K: int,
    *,
    diversify: Optional[Callable[[int], Any]] = None,
    merge: dict,  # REQUIRED — enforced at call time via keyword-only
    verifier: Optional[Callable[[Any], bool]] = None,
) -> _FanoutNode:
    """K independent lanes; diversify(lane_idx) builds per-lane context."""
    _validate_merge(merge, "fanout")
    return _FanoutNode(task_fn=task_fn, K=K, diversify=diversify,
                       merge=merge, verifier=verifier)


def partition(
    shards: list,
    worker_fn: Callable[[Any], Any],
    *,
    merge: dict,  # REQUIRED
    verifier: Optional[Callable[[Any], bool]] = None,
) -> _PartitionNode:
    """One worker per independent shard."""
    _validate_merge(merge, "partition")
    return _PartitionNode(shards=list(shards), worker_fn=worker_fn,
                          merge=merge, verifier=verifier)


def sequential(*steps) -> _SequentialNode:
    """Chain; each step is a callable(input)->output or a node."""
    return _SequentialNode(steps=steps)


# ── Runner ──────────────────────────────────────────────────────────────────


def run(
    plan,
    *,
    max_workers: Optional[int] = None,
    receipts_path: Optional[str | Path] = None,
    confluence_check: bool = False,
    _input: Any = None,   # used for sequential chaining; external callers rarely set this
) -> Any:
    """Execute a work-plan node; return the merged result."""
    if isinstance(plan, _SequentialNode):
        return _run_sequential(plan, max_workers=max_workers,
                               receipts_path=receipts_path,
                               confluence_check=confluence_check)
    if isinstance(plan, _FanoutNode):
        return _run_parallel(plan, max_workers=max_workers,
                              receipts_path=receipts_path,
                              confluence_check=confluence_check)
    if isinstance(plan, _PartitionNode):
        return _run_parallel(plan, max_workers=max_workers,
                              receipts_path=receipts_path,
                              confluence_check=confluence_check)
    # bare callable
    if callable(plan):
        return plan(_input)
    raise TypeError(f"run: unrecognised plan type {type(plan)!r}")


# ── Internal runners ────────────────────────────────────────────────────────


def _run_sequential(node: _SequentialNode, **kwargs) -> Any:
    value = None
    for step in node.steps:
        if isinstance(step, (_FanoutNode, _PartitionNode, _SequentialNode)):
            # ponytail: pass previous value as _input for future chaining if needed
            value = run(step, **kwargs)
        elif callable(step):
            value = step(value)
        else:
            raise TypeError(f"sequential step must be callable or node; got {type(step)!r}")
    return value


def _run_parallel(
    node: _FanoutNode | _PartitionNode,
    *,
    max_workers: Optional[int],
    receipts_path: Optional[str | Path],
    confluence_check: bool,
) -> Any:
    # Build (lane_label, task_callable) pairs
    if isinstance(node, _FanoutNode):
        node_kind = "fanout"
        lanes = []
        for i in range(node.K):
            ctx = node.diversify(i) if node.diversify else i
            lanes.append((i, lambda c=ctx: node.task_fn(c)))
    else:
        node_kind = "partition"
        lanes = [(i, lambda s=shard: node.worker_fn(s))
                 for i, shard in enumerate(node.shards)]

    n_lanes = len(lanes)
    _max = max_workers if max_workers is not None else max(1, n_lanes)

    t0 = time.perf_counter()
    raw_results: list[tuple[int, Any, Optional[str]]] = []  # (idx, value, error)

    with concurrent.futures.ThreadPoolExecutor(max_workers=_max) as ex:
        futures = {ex.submit(fn): idx for idx, fn in lanes}
        for fut in concurrent.futures.as_completed(futures):
            idx = futures[fut]
            try:
                raw_results.append((idx, fut.result(), None))
            except Exception as exc:  # noqa: BLE001
                raw_results.append((idx, None, f"{type(exc).__name__}: {exc}"))

    wall_seconds = time.perf_counter() - t0

    # Sort by lane index for determinism
    raw_results.sort(key=lambda x: x[0])

    # Verifier pass + exclusion count
    excluded_count = 0
    good_results: list[Any] = []
    for _idx, val, err in raw_results:
        if err is not None:
            excluded_count += 1
            continue
        if node.verifier is not None and not node.verifier(val):
            excluded_count += 1
            continue
        good_results.append(val)

    if not good_results:
        raise WorkPlanContractError(
            f"{node_kind}: all {n_lanes} lanes excluded (errors or verifier rejection)"
        )

    merged, winner_idx = _apply_merge(good_results, node.merge)

    # Confluence check (reduce only)
    if confluence_check and node.merge["kind"] == "reduce":
        import random as _random
        seed = len(good_results)
        shuffled = list(good_results)
        _random.Random(seed).shuffle(shuffled)
        merged_shuffled = _apply_reduce_only(shuffled, node.merge["fn"])
        if merged_shuffled != merged:
            raise WorkPlanConfluenceError(
                f"{node_kind}: reduce merge not confluent — "
                f"in-order={merged!r} shuffled={merged_shuffled!r}"
            )

    # Attestation
    if receipts_path is not None:
        row = {
            "schema": "ztare.work_plan_attestation.v1",
            "node_kind": node_kind,
            "lanes": n_lanes,
            "merge_kind": node.merge["kind"],
            "verifier_present": node.verifier is not None,
            "excluded_count": excluded_count,
            "wall_seconds": round(wall_seconds, 4),
        }
        if node.merge["kind"] == "select":
            row["winner_index"] = winner_idx
        elif node.merge["kind"] == "collect":
            row["collected_count"] = len(merged)
        else:
            row["merged"] = True
        with open(receipts_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    return merged
