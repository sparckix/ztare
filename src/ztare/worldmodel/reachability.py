"""Bounded-horizon reachability sweep (GP-250): transition laws as level-hunt.

Authority boundary:
  - Kernel-ratified invariants, when present, filter theorem-impossible
    predicted successors through `prediction_is_admissible`.
  - Role-derived quantities such as a monotone-depleting support are search
    coordinates and ranking/bounding hints until a ratified certificate exists.
  - The local mirrored LeanMill scratch I inspected closes the translate/count
    phase. Treat the full timer monotonicity theorem as enforced only when the
    project carries `workspace/invariant_certificates.jsonl`.

The sweep enumerates reachable object states under the champion, ranks
frontier leaves, and hands ordered candidate action paths to live execution.
Coverage payoff: if the sweep exhausts the bounded object space without
reaching the goal, the model must be WRONG somewhere reachable -> a new
falsification channel (return `refuted_or_unreachable`, carrying the deepest
frontier for re-identification). Pure/simulated; the live driver executes and
the sealed reward + gates still judge.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from ztare.worldmodel.gates import as_predictor
from ztare.worldmodel.grid_dsl import Grid
from ztare.worldmodel.invariant_bridge import prediction_is_admissible

# ponytail: degenerate ImageMaintainingSet — the len-keyed memo is sound
# only while this store is append-only; full adoption needs the owner
# (pursue_goal's visited_store / autoresearch._visited_store) to hold an
# ImageMaintainingSet so the 'coverage' image is co-maintained on every append.
# Until then, len-keyed eviction is the correct lazy equivalent: if len matches,
# the append-only invariant guarantees the set is identical — no rebuild needed.
_visited_control_cache: "dict[int, set]" = {}


def _jsonable_key(value):
    if isinstance(value, frozenset):
        items = [_jsonable_key(v) for v in value]
        items.sort(key=lambda v: json.dumps(v, sort_keys=True))
        return {"__ztare_type__": "frozenset", "items": items}
    if isinstance(value, tuple):
        return {"__ztare_type__": "tuple", "items": [_jsonable_key(v) for v in value]}
    if isinstance(value, list):
        return [_jsonable_key(v) for v in value]
    return value


def _key_from_jsonable(value):
    if isinstance(value, dict) and value.get("__ztare_type__") == "frozenset":
        return frozenset(_key_from_jsonable(v) for v in value.get("items", []))
    if isinstance(value, dict) and value.get("__ztare_type__") == "tuple":
        return tuple(_key_from_jsonable(v) for v in value.get("items", []))
    if isinstance(value, list):
        return [_key_from_jsonable(v) for v in value]
    return value


def save_visited(path, keys) -> None:
    """Persist abstract object-state keys as deterministic JSONL — delta-append.

    FIX A: instead of a full O(N) rewrite every 50 steps, append only keys not
    yet on disk. Callers pass a growing *set* (planner's visited_store), whose
    iteration order can change on resize — so a positional cursor is UNSOUND
    (a reordered key could permute into the "already written" prefix and be
    lost). We instead track the written keys per path: membership is
    order-independent, the scan is cheap C-level pointer ops, and only the
    delta pays serialization+IO. First save for a path seeds from the file, so
    legacy full-rewrite files stay compatible (load_visited dedupes anyway).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    written = _WRITTEN_KEYS.get(str(p))
    if written is None:
        written = load_visited(p) if p.exists() else set()
        _WRITTEN_KEYS[str(p)] = written
    new_keys = [k for k in keys if k not in written]
    if not new_keys:
        return
    with p.open("a" if p.exists() else "w") as f:
        for k in new_keys:
            f.write(json.dumps(_jsonable_key(k), sort_keys=True) + "\n")
    written.update(new_keys)


# ponytail: per-path already-written key sets for delta-append (FIX A).
# Cleared on process restart, then reseeded from disk on first save.
_WRITTEN_KEYS: dict[str, set] = {}


def load_visited(path) -> set:
    """Inverse of save_visited; missing/empty file -> empty set (fail-open)."""
    p = Path(path)
    if not p.exists():
        return set()
    out: set = set()
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if isinstance(raw, list):
                # Backward compatibility: old format was [[y, x, color], ...].
                out.add(frozenset(tuple(r) for r in raw))
            else:
                out.add(_key_from_jsonable(raw))
        except Exception:  # noqa: BLE001 — a corrupt line just isn't remembered
            continue
    return out


def _resource_count(grid: Grid, resource_colors) -> int:
    if not resource_colors:
        return 0
    rc = set(resource_colors)
    return sum(1 for row in grid for c in row if c in rc)


@dataclass
class SweepResult:
    status: str                       # goal_paths | refuted_or_unreachable | no_goal_fn
    paths: "list[list[int]]" = field(default_factory=list)   # ranked action seqs
    states_enumerated: int = 0
    deepest: "Grid | None" = None
    deepest_depth: int = 0
    detail: str = ""
    saturated: bool = False           # coverage: every reachable state already visited


def reachability_sweep(champion, start: Grid, action_arity: int, *,
                       goal_fn=None, resource_colors=None, start_step: int = 0,
                       max_states: int = 200000, max_depth: int = 400,
                       rank_fn=None, invariants=None, abstract_fn=None,
                       visited_store=None, coverage_fn=None) -> SweepResult:
    """BFS over reachable states under the champion, resource-bounded. Returns
    ranked goal-reaching paths, or refuted_or_unreachable with the deepest
    frontier if the bounded space is exhausted without the goal."""
    predict = as_predictor(champion)
    # MEMOIZE OVER ABSTRACT OBJECT-STATE when a signature is given — the fix
    # that makes brute-force BFS tractable (finite FSM, not 4^N tree). The
    # invariant filter keeps the monotone axis a DAG, so the closed list is
    # exhausted long before the action budget (external review).
    _key = (lambda g, st: (abstract_fn(g), st % 6)) if abstract_fn \
        else (lambda g, st: (g, st % 6))
    seen = {_key(start, start_step)}
    frontier = deque([(start, start_step, [])])
    goal_paths: "list[tuple[int, list[int]]]" = []
    deepest, deepest_depth = start, 0
    _deepest_path: "list[int]" = []
    # PERSISTENT FRONTIER MEMORY: in coverage mode, steer toward the deepest
    # reachable object-state whose abstract key is NOT already visited live.
    track_novel = goal_fn is None and visited_store is not None and abstract_fn is not None
    coverage_key = coverage_fn or (lambda sig: sig)
    if track_novel:
        _n = len(visited_store)
        if _n not in _visited_control_cache:
            _visited_control_cache.clear()  # only one entry needed; evict stale
            _visited_control_cache[_n] = {coverage_key(k) for k in visited_store}
        # copy so in-sweep .add() calls don't pollute the cache
        visited_control = _visited_control_cache[_n].copy()
    else:
        visited_control = set()
    _novel_path: "list[int]" = []
    novel_depth, found_novel = -1, False
    n = 0
    start_res = _resource_count(start, resource_colors)
    while frontier and n < max_states:
        grid, step, path = frontier.popleft()
        if len(path) > deepest_depth:
            deepest, deepest_depth, _deepest_path = grid, len(path), path
        if track_novel:
            ck = coverage_key(abstract_fn(grid))
            if ck not in visited_control:
                visited_control.add(ck)
                if coverage_fn is not None:
                    # A projected frontier key is already a caller-priced
                    # novelty carrier, so BFS order gives the cheapest new
                    # carrier state. Do not reward inert delay before it.
                    if not found_novel:
                        found_novel = True
                        novel_depth, _novel_path = len(path), path
                elif len(path) > novel_depth:
                    found_novel = True
                    novel_depth, _novel_path = len(path), path
        if goal_fn is not None and goal_fn(grid):
            rank = rank_fn(grid) if rank_fn else -len(path)   # prefer shorter
            goal_paths.append((rank, path))
            if len(goal_paths) >= 8:
                break
            continue
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            # DETERMINISTIC proof bridge: a predicted successor that violates a
            # KERNEL-RATIFIED invariant is a model hallucination -> drop it.
            # This removes theorem-impossible transitions ONLY; a real reachable
            # (hence goal) path is never pruned (external-review soundness fix).
            if invariants and not prediction_is_admissible(invariants, grid, nxt):
                continue
            key = _key(nxt, step + 1)
            if key in seen:
                continue
            seen.add(key)
            n += 1
            frontier.append((nxt, step + 1, path + [a]))
    if goal_paths:
        goal_paths.sort(key=lambda r: -r[0])
        return SweepResult(status="goal_paths",
                           paths=[p for _, p in goal_paths[:8]],
                           states_enumerated=n, deepest=deepest,
                           deepest_depth=deepest_depth,
                           detail=f"{len(goal_paths)} goal paths in {n} states")
    if goal_fn is None:
        # EXPLORATORY COVERAGE (self-review fix): no goal predicate yet, so the
        # sweep drives ABSTRACT-STATE COVERAGE — a path to the deepest reachable
        # object-state. Executed live, this walks the FSM toward unseen object
        # states; the sealed reward fires if coverage reaches a level. This is
        # how the FIRST goal is found (the whole goal apparatus is downstream).
        if track_novel:
            # frontier memory: target the deepest UNVISITED reachable state; if
            # every reachable state is already visited live, SATURATE (fall back
            # to the deepest overall) — the honest CEGAR trigger that exploration
            # has exhausted the reachable space under the current physics.
            path = _novel_path if found_novel else _deepest_path
            saturated = not found_novel
            return SweepResult(
                status="coverage", paths=[path] if path else [],
                states_enumerated=n, deepest=deepest, deepest_depth=deepest_depth,
                saturated=saturated,
                detail=(f"frontier memory: SATURATED — all {n} reachable object-states "
                        f"already visited live (refine physics)" if saturated else
                        f"frontier memory: novel target at depth {len(path)} "
                        f"({n} object-states swept)"))
        return SweepResult(status="coverage", paths=[_deepest_path] if _deepest_path else [],
                           states_enumerated=n, deepest=deepest,
                           deepest_depth=deepest_depth,
                           detail=f"abstract coverage: {n} object-states, deepest "
                                  f"path {len(_deepest_path)}")
    exhausted = n < max_states       # frontier drained within the bound
    return SweepResult(
        status="refuted_or_unreachable", states_enumerated=n,
        deepest=deepest, deepest_depth=deepest_depth,
        detail=("bounded object space exhausted without reaching goal — the "
                "model is likely wrong at a reachable state (re-identify)"
                if exhausted else
                f"state cap {max_states} hit before exhaustion; goal not yet found"))
