"""Goal pursuit: the exploit half of the interactive substrate (GP-250 P1).

The autoresearch kernel identifies a transition law; this module CONSUMES a
ratified law to reach a goal. It adds no epistemic surface: the model is an
executable program (`evaluate`), the goal signal is environment-provided and
sealed (a `levels_completed` / score increase — never named in the charter,
per the Oracle Trap rule), and every planned sequence is executed against the
live adapter and re-checked. The kernel stays an identifier; this is a thin
downstream planner over its output.

Design (deliberately minimal):
  - `plan_to_goal(champion, start, arity, goal_fn, ...)` — bounded BFS over
    action sequences, simulating with `evaluate`; returns the first sequence
    whose SIMULATED terminal state satisfies goal_fn, or None.
  - `pursue_goal(adapter, champion, ...)` — plan under the model, execute the
    plan against the live environment, and STOP the moment the real
    `levels_completed` increases (the terminal verifier event). A divergence
    between the model's prediction and the real frame ends the plan (the model
    is wrong off the witnessed basin) and is reported for re-identification.

Honest boundary: this plans through ONE ratified champion. A committee that
has not collapsed to a singleton has no ratified model to plan through — plan
only after `acquire_evidence` returns `identified`.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ponytail: env knob caps per-call reachability sweep cost (200k default exhausted 26 min/sprint
# at ls20 scale; 5000 gives ~29s/sprint with valid steering paths). Override when FSM is tiny.
_SWEEP_MAX_STATES = int(os.environ.get("ZTARE_SWEEP_MAX_STATES", "5000"))

from ztare.common.image_set import ImageMaintainingSet
from ztare.worldmodel.frontier_codec import (
    AbstractCarrierInterner, StateInterner, abstract_novelty, batch_novelty,
)
from ztare.worldmodel.gates import as_predictor
from ztare.worldmodel.grid_dsl import Grid, Program, evaluate
from ztare.worldmodel.terminal_witness import terminal_witness_fingerprint

_log = logging.getLogger(__name__)

# ponytail: env flag selects vectorized vs pure-Python novelty; default "1" (on)
_VECTORIZED = os.environ.get("ZTARE_VECTORIZED_FRONTIER", "1") != "0"


@dataclass
class Plan:
    actions: "list[int]"
    reason: str
    simulated_terminal: "Grid | None" = None


def plan_to_goal(champion: Program, start: Grid, action_arity: int,
                 goal_fn, *, start_step: int = 0, max_depth: int = 12,
                 abstract_fn=None,
                 max_nodes: int = 20000,
                 _state_interner: "StateInterner | None" = None,
                 _abstract_interner_cache: "AbstractCarrierInterner | None" = None,
                 ) -> "Plan | None":
    """Bounded BFS for the shortest action sequence whose SIMULATED terminal
    state satisfies `goal_fn(grid)`. Pure — touches no environment. Prunes by
    visited (grid, step%6) so cyclic worlds terminate; step is tracked mod 6
    because seed-grammar guards only read t via %2/%3 (same soundness argument
    as the Lean probe set)."""
    predict = as_predictor(champion)
    if goal_fn(start):
        # F5 guard (2026-07-09): a goal that is already satisfied at the start
        # state is a degenerate / null plan. Returning it with empty actions and
        # a distinct reason string ensures pursue_goal's empty-actions filter
        # (which sets plan=None) catches it and it can NEVER propagate as a
        # goal_reached status or be scored as progress. A differs_from_start=False
        # predicate always fires here; a well-formed abduction goal (always True)
        # would produce the same degenerate path. Neither receives credit.
        return Plan(actions=[], reason="goal_satisfied_at_start: null plan, no credit")
    # FIX B: interner-aware keying — int IDs are exact surrogates for grid identity.
    if _state_interner is not None and abstract_fn is None:
        _start_key = (_state_interner.intern(start), start_step % 6)
        def _key(g, s): return (_state_interner.intern(g), s % 6)
    elif _abstract_interner_cache is not None:
        _start_key = (_abstract_interner_cache.intern(abstract_fn(start)), start_step % 6)
        def _key(g, s): return (_abstract_interner_cache.intern(abstract_fn(g)), s % 6)
    else:
        _start_key = _planner_key(start, start_step, abstract_fn)
        def _key(g, s): return _planner_key(g, s, abstract_fn)
    seen = {_start_key}
    frontier: "deque[tuple[Grid, int, list[int]]]" = deque([(start, start_step, [])])
    nodes = 0
    while frontier and nodes < max_nodes:
        grid, step, path = frontier.popleft()
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            key = _key(nxt, step + 1)
            if key in seen:
                continue
            seen.add(key)
            nodes += 1
            new_path = path + [a]
            if goal_fn(nxt):
                return Plan(actions=new_path,
                            reason=f"goal reachable in {len(new_path)} steps "
                                   f"(searched {nodes} nodes)",
                            simulated_terminal=nxt)
            frontier.append((nxt, step + 1, new_path))
    return Plan(actions=[], reason=f"no plan within depth {max_depth} / {nodes} nodes") \
        if nodes else None


def _hamming(a: Grid, b: Grid, limit: int = 0) -> int:
    """Cell-difference distance between two same-shape grids.

    When `limit > 0`, early-exits as soon as the running count reaches
    `limit` — semantics unchanged (returns exact value when < limit,
    returns limit when >= limit).
    """
    dist = 0
    for ra, rb in zip(a, b):
        for ca, cb in zip(ra, rb):
            if ca != cb:
                dist += 1
                if limit and dist >= limit:
                    return dist
    return dist


def _novelty(grid: Grid, visited: "set[Grid]") -> int:
    """Min distance from `grid` to any visited state — high = unexplored."""
    if not visited or grid in visited:
        return 0
    best = None
    for v in visited:
        # ponytail: pass best as limit so _hamming short-circuits the moment
        # it would exceed the current minimum — O(cells) exit, not O(|visited|×cells)
        d = _hamming(grid, v, limit=best if best is not None else 0)
        if best is None or d < best:
            best = d
            if best == 1:
                break  # can't do better (0 excluded by `grid in visited`)
    return best if best is not None else 0


def _abstract_novelty(grid: Grid, visited: "set[Grid]", abstract_fn=None,
                      visited_abstract: "set | None" = None) -> int:
    if abstract_fn is None:
        return _novelty(grid, visited)
    carrier = abstract_fn(grid)
    if visited_abstract is not None:
        # O(1): the caller maintains the abstract image of `visited`
        # incrementally. Rebuilding it here was O(|visited|) PER BFS NODE
        # per replan — quadratic in progress; it wedged the sprint the first
        # time evidence grew enough to saturate reachability.
        return 0 if carrier in visited_abstract else 1
    visited_carriers = {abstract_fn(v) for v in visited}
    return 0 if carrier in visited_carriers else 1


def _planner_key(grid: Grid, step: int, abstract_fn=None):
    """State identity for planner pruning.

    Default is byte-level transition-state identity. Callers with a valid
    abstraction map can pass ``abstract_fn`` so search runs over quotient
    classes instead of action-prefix strings.
    """
    if abstract_fn is None:
        return (grid, step % 6)
    return (abstract_fn(grid), step % 6)


def plan_novelty(champion: Program, start: Grid, action_arity: int,
                 visited: "set[Grid]", *, visited_abstract: "set | None" = None,
                 start_step: int = 0, max_depth: int = 10,
                 abstract_fn=None,
                 max_nodes: int = 20000,
                 _state_interner: "StateInterner | None" = None,
                 _abstract_interner_cache: "AbstractCarrierInterner | None" = None,
                 ) -> "Plan | None":
    """Best-first search for the action sequence reaching the MOST NOVEL state
    the model predicts (max min-distance to `visited`). General and
    game-agnostic: no goal predicate, no model-authored success criterion — it
    only STEERS exploration. Success is judged elsewhere by the terminal
    verifier, so a wrong steer costs efficiency, never correctness. Doubles as
    the evidence-diversity driver for re-identification — novel states are the
    off-basin transitions the act-learn loop absorbs.

    FIX B: callers that call plan_novelty repeatedly on a growing `visited` can
    pass a pre-seeded `_state_interner` (raw-grid path) or `_abstract_interner_cache`
    (abstract path) so we skip re-interning all visited entries from scratch every
    replan.  Callers are responsible for growing the interner incrementally before
    each call.  When None, the old full-seed path is used (correct, just slower).
    """
    predict = as_predictor(champion)
    seen = {_planner_key(start, start_step, abstract_fn)}
    # frontier entries: (neg_novelty, tiebreak, grid, step, path) — heapq is a
    # min-heap so we negate novelty to pop the most-novel first
    import heapq

    # ponytail: vectorized novelty via StateInterner (raw grids) or
    # AbstractCarrierInterner (abstract carriers) when ZTARE_VECTORIZED_FRONTIER=1.
    # Both replace frozenset/tuple-set membership with O(1) int-id set lookup.
    # ZTARE_VECTORIZED_FRONTIER=0 selects the old pure-Python path for both.
    _interner: "StateInterner | None" = _state_interner
    _abstract_interner: "AbstractCarrierInterner | None" = _abstract_interner_cache
    if _interner is None and _abstract_interner is None:
        # Cold-start path: seed from scratch (original behaviour).
        if _VECTORIZED and abstract_fn is None and visited:
            _interner = StateInterner()
            for _g in visited:
                try:
                    _interner.intern(_g)
                except ValueError:
                    # mixed grid sizes (shouldn't happen in a single BFS but be safe)
                    _interner = None
                    break
        elif _VECTORIZED and abstract_fn is not None:
            # Abstract path: intern the visited_abstract carriers (from ImageMaintainingSet)
            # into int IDs so membership checks are O(1) int comparisons rather than
            # O(K) frozenset hash + equality. Carriers are frozensets or nested tuples;
            # abstract_novelty is BINARY (0 visited / 1 new) — no hamming needed.
            if visited_abstract is not None:
                _abstract_interner = AbstractCarrierInterner()
                for _c in visited_abstract:
                    _abstract_interner.mark_visited(_c)

    def _novelty_fn(g: Grid) -> int:
        if _interner is not None:
            return batch_novelty(g, _interner)
        if _abstract_interner is not None:
            _carrier = abstract_fn(g)
            # ponytail: read-only — plan_novelty doesn't grow visited;
            # _abstract_interner was seeded once from visited_abstract at start
            return abstract_novelty(_carrier, _abstract_interner)
        return _abstract_novelty(g, visited, abstract_fn,
                                 visited_abstract=visited_abstract)

    best_plan: "list[int]" = []
    best_novelty = 0
    frontier = [(0, 0, start, start_step, [])]
    nodes = 0
    tie = 0
    while frontier and nodes < max_nodes:
        _, _, grid, step, path = heapq.heappop(frontier)
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            key = _planner_key(nxt, step + 1, abstract_fn)
            if key in seen:
                continue
            seen.add(key)
            nodes += 1
            new_path = path + [a]
            nov = _novelty_fn(nxt)
            if nov > best_novelty:
                best_novelty, best_plan = nov, new_path
            tie += 1
            heapq.heappush(frontier, (-nov, tie, nxt, step + 1, new_path))
    if not best_plan:
        return Plan(actions=[], reason=f"no novel state reachable ({nodes} nodes)") \
            if nodes else None
    return Plan(actions=best_plan,
                reason=f"most-novel reachable state (novelty {best_novelty}, "
                       f"{len(best_plan)} steps, {nodes} nodes)")


def plan_progress(champion: Program, start: Grid, action_arity: int,
                  progress_fn, *, start_step: int = 0, max_depth: int = 12,
                  abstract_fn=None,
                  max_nodes: int = 20000,
                  _state_interner: "StateInterner | None" = None,
                  _abstract_interner_cache: "AbstractCarrierInterner | None" = None,
                  ) -> "Plan | None":
    """Best-first search maximizing a PROGRESS heuristic `progress_fn(grid)->
    float` (a goal-shaped cue the mutator inferred from OBSERVED frames — frames
    are unsealed; only game docs are). STEERING ONLY: the terminal verifier,
    not this heuristic, judges success, so a wrong progress guess costs search
    efficiency, never correctness. Falls back to returning the best-progress
    plan found within the node budget."""
    predict = as_predictor(champion)
    import heapq

    def _score(g):
        try:
            v = float(progress_fn(g))
        except Exception:
            return float("-inf")
        return v

    # FIX B: interner-aware keying — int IDs are exact surrogates for grid identity.
    if _state_interner is not None and abstract_fn is None:
        _start_key = (_state_interner.intern(start), start_step % 6)
        def _key(g, s): return (_state_interner.intern(g), s % 6)
    elif _abstract_interner_cache is not None:
        _start_key = (_abstract_interner_cache.intern(abstract_fn(start)), start_step % 6)
        def _key(g, s): return (_abstract_interner_cache.intern(abstract_fn(g)), s % 6)
    else:
        _start_key = _planner_key(start, start_step, abstract_fn)
        def _key(g, s): return _planner_key(g, s, abstract_fn)
    start_score = _score(start)
    best_plan, best_score = [], start_score
    seen = {_start_key}
    frontier = [(-start_score, 0, start, start_step, [])]
    nodes, tie = 0, 0
    while frontier and nodes < max_nodes:
        _, _, grid, step, path = heapq.heappop(frontier)
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            key = _key(nxt, step + 1)
            if key in seen:
                continue
            seen.add(key)
            nodes += 1
            tie += 1
            new_path = path + [a]
            sc = _score(nxt)
            if sc > best_score:
                best_score, best_plan = sc, new_path
            heapq.heappush(frontier, (-sc, tie, nxt, step + 1, new_path))
    if not best_plan:
        return Plan(actions=[], reason=f"no progress improvement reachable ({nodes} nodes)") \
            if nodes else None
    return Plan(actions=best_plan,
                reason=f"max-progress plan (progress {best_score:.3g}, "
                       f"{len(best_plan)} steps, {nodes} nodes)")


def compile_progress_heuristic(code: str):
    """Sandbox-compile a mutator-proposed `progress(grid)->float`. Reuses the
    grammar-extension sandbox (script_is_safe + minimal builtins). Returns
    (fn, error). Steering-only, so the sandbox is defense-in-depth, not a trust
    boundary; success is still the terminal verifier event."""
    from ztare.worldmodel.grammar_extension import _SAFE_BUILTINS
    from ztare.common.sandboxed_python import script_is_safe
    if not script_is_safe(code):
        return None, "rejected by sandbox safety scan"
    ns: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, ns)  # noqa: S102 — gated by script_is_safe + minimal builtins
    except Exception as exc:
        return None, f"exec failed: {exc}"
    fn = ns.get("progress")
    if not callable(fn):
        return None, "no `progress` function defined"
    try:
        float(fn(((0, 1), (2, 0))))
    except Exception as exc:
        return None, f"probe call failed: {exc}"
    return fn, ""


@dataclass
class PursuitReceipt:
    status: str                    # goal_reached | model_diverged | plan_exhausted | no_model
    steps_executed: int = 0
    levels_gained: int = 0
    detail: str = ""
    divergence: "dict | None" = None
    replans: int = 0
    trace: "list[int]" = field(default_factory=list)
    # coverage saturated during pursuit: every reachable object-state was already
    # visited live — the honest CEGAR trigger (exploration exhausted the space)
    saturated: bool = False
    # the exact transitions the live env produced during pursuit — the model
    # was NEVER fit on these (they are off-basin by construction once it
    # diverges), so they are pure re-identification evidence
    observed_transitions: "list[tuple]" = field(default_factory=list)


def _levels(adapter) -> int:
    return int(getattr(adapter, "levels_completed", 0) or 0)


def _divergence_payload(action: int, step: int, state: Grid,
                        predicted: "Grid | None", real_next: Grid) -> dict:
    return {
        "action": action,
        "step": step,
        "state": state,
        "real_next": real_next,
        "kernel_role_bindings": [
            {
                "term": "terminal_verifier_event",
                "roles": ["verification", "selection"],
                "evidence": (
                    "environment terminal event decides outcome; transition "
                    "mismatch remains separate law-refinement evidence"
                ),
            }
        ],
        "terminal_witness": terminal_witness_fingerprint(
            action=action, step=step, state=state,
            predicted=predicted, observed=real_next),
    }


def _emit_saturation_receipt(adapter, visited_store, abstract_growth_rate=None, *, receipts_dir=None) -> None:
    """Append a one-line typed saturation receipt to abstraction_saturation.jsonl.
    Called at most once per pursuit (guarded by caller's flag).
    receipts_dir: explicit directory; falls back to CWD-relative workspace/ when None.
    """
    game_id = getattr(adapter, "env_id", None)
    receipt = {
        "schema": "ztare-abstraction-saturation-v1",
        "game": game_id,
        "visited_store_size": len(visited_store) if visited_store is not None else 0,
        "ts": datetime.utcnow().isoformat(),
    }
    if abstract_growth_rate is not None:
        receipt["abstract_growth_rate"] = abstract_growth_rate
    # FIX 3: stamp saturation_kind when the visited structure exposes it
    if hasattr(visited_store, "saturation_kind"):
        # ImageMaintainingSet: disambiguate exhaustion vs alpha-blindness
        for _fname_sk in list(getattr(visited_store, "_functors", {}).keys())[:1]:
            try:
                receipt["saturation_kind"] = visited_store.saturation_kind(_fname_sk)
            except Exception:  # noqa: BLE001
                pass
    _fname = "abstraction_saturation.jsonl"
    out = (Path(receipts_dir) / _fname) if receipts_dir is not None else Path("workspace") / _fname
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write(json.dumps(receipt) + "\n")
    _log.info("abstraction saturation: game=%s visited_store=%d",
              game_id, receipt["visited_store_size"])


def pursue_goal(adapter, champion: Program, *, goal_fn=None, progress_fn=None,
                resource_colors=None, invariants=None, abstract_fn=None,
                coverage_fn=None, visited_store=None, visited_path=None,
                max_steps: int = 400, max_replans: int = 8,
                plan_depth: int = 12, receipts_dir=None) -> PursuitReceipt:
    """Plan under `champion`, execute against the live adapter, stop on the
    terminal verifier event. Steering is NOVELTY search by default (drive toward the
    most-novel state the model predicts) — general and game-agnostic, with no
    model-authored success criterion. `goal_fn(grid)->bool` overrides with an
    explicit target frame when a caller has one.

    The non-iatrogenic split: the model only STEERS exploration; SUCCESS is
    judged solely by the environment's sealed `levels_completed`, which the
    model cannot author. A wrong steer costs efficiency, never correctness.

    Every executed step is compared to the model's prediction; a mismatch
    means the ratified law does not hold off the witnessed basin — the pursuit
    ends with `model_diverged` and the divergence is reported for
    re-identification, rather than a silent wrong plan."""
    if champion is None:
        return PursuitReceipt(status="no_model", detail="no ratified champion to plan through")

    from ztare.worldmodel.reachability import (
        load_visited, reachability_sweep, save_visited)
    # PERSISTENT CROSS-EPISODE FRONTIER MEMORY: the set of abstract object-state
    # keys already visited LIVE. Loaded from visited_path when not passed in, it
    # accumulates across replans, rounds, and process restarts. The coverage
    # sweep steers away from these; when every reachable state is already in the
    # store the sweep SATURATES — the honest CEGAR trigger, carried into the
    # receipt so the caller sees exploration has exhausted the reachable space.
    if visited_store is None and visited_path is not None:
        visited_store = load_visited(visited_path)
    saturated = False
    steps_since_save = 0
    _saturation_receipt_emitted = False

    predict = as_predictor(champion)
    baseline = _levels(adapter)
    state = adapter.state
    trace: "list[int]" = []
    observed: "list[tuple]" = []   # (state, action, real_next, step) — re-id evidence
    # ponytail: one ImageMaintainingSet replaces the visited/visited_abstract pair;
    # 'abstract' image is co-maintained pointwise on every add — O(1) vs O(|visited|)
    # per BFS node in plan_novelty. Functoriality holds: abstract_fn is grid→carrier
    # with no set-level dependence.
    _functors = {"abstract": abstract_fn} if abstract_fn is not None else {}
    _vset = ImageMaintainingSet(functors=_functors, receipts_dir=receipts_dir)
    _vset.add(state)
    replans = 0
    replan_limit = max_replans
    if coverage_fn is not None and goal_fn is None and progress_fn is None:
        # Projected coverage may intentionally return the cheapest path to the
        # next new carrier state, often one action. In that regime the action
        # budget, not a small fixed replan count, is the proportional stop.
        replan_limit = max(max_replans, max_steps)

    # FIX B: persistent interners so each replan only interns NEW entries.
    # _pg_interner is the raw-grid StateInterner; _pg_abs_interner is the
    # AbstractCarrierInterner for the abstract path.  Both are grown incrementally
    # alongside _vset inside the loop, so plan_novelty never re-seeds from scratch.
    # _pg_interner_seeded tracks how many raw grids the interner has seen; any
    # grids added to _vset._raw since then are interned before the next plan call.
    _pg_interner: "StateInterner | None" = None
    _pg_interner_seeded: int = 0
    _pg_abs_interner: "AbstractCarrierInterner | None" = None
    _pg_abs_interner_seeded: int = 0
    if _VECTORIZED and abstract_fn is None:
        _pg_interner = StateInterner()
    elif _VECTORIZED and abstract_fn is not None:
        _pg_abs_interner = AbstractCarrierInterner()

    def _ensure_interners_synced():
        """Intern any grids/carriers added to _vset since the last plan call."""
        nonlocal _pg_interner_seeded, _pg_abs_interner_seeded
        if _pg_interner is not None:
            raw_list = list(_vset._raw)
            new_entries = raw_list[_pg_interner_seeded:]
            for _g in new_entries:
                try:
                    _pg_interner.intern(_g)
                    _pg_interner_seeded += 1
                except ValueError:
                    # mixed grid sizes — fall back to cold-start by nulling interner
                    break
        if _pg_abs_interner is not None:
            abs_img = _vset._images.get("abstract")
            if abs_img is not None:
                abs_list = list(abs_img)
                new_abs = abs_list[_pg_abs_interner_seeded:]
                for _c in new_abs:
                    _pg_abs_interner.mark_visited(_c)
                    _pg_abs_interner_seeded += 1

    # Task 3: predict memo.
    # Real-data test (20 rows of episode_001.jsonl) confirmed predict(s, a, t) == predict(s, a, t+4)
    # for ALL 20 rows → keying by (state_id, action, step%4) is safe and correct.
    # ponytail: step%4 key — verified period-4 on real champion; use full step if ever broken
    _predict_memo: dict = {}

    # Task 5: accumulating sub-phase timing counters (float seconds, no per-step I/O)
    _t_plan: float = 0.0
    _t_env: float = 0.0
    _t_predict: float = 0.0
    _pursuit_started: str = datetime.utcnow().isoformat()

    try:
        while len(trace) < max_steps and replans <= replan_limit:
            plan = None
            # ABSTRACT REACHABILITY first (goal-directed OR exploratory coverage):
            # object-state memoization makes exhaustive FSM coverage tractable, and
            # coverage is how the FIRST level is found before any goal predicate.
            if abstract_fn is not None:
                _t0 = time.perf_counter()
                sw = reachability_sweep(champion, state, adapter.action_arity,
                                        goal_fn=goal_fn, resource_colors=resource_colors,
                                        start_step=adapter.t, max_depth=plan_depth * 6,
                                        max_states=_SWEEP_MAX_STATES,
                                        invariants=invariants, abstract_fn=abstract_fn,
                                        visited_store=visited_store,
                                        coverage_fn=coverage_fn)
                _t_plan += time.perf_counter() - _t0
                if getattr(sw, "states_enumerated", 0) >= _SWEEP_MAX_STATES:
                    _budget_p = (Path(receipts_dir) if receipts_dir else Path("workspace")) / "reachability_budget.jsonl"
                    _budget_p.parent.mkdir(parents=True, exist_ok=True)
                    with _budget_p.open("a") as _bf:
                        _bf.write(json.dumps({
                            "schema": "ztare-reachability-budget-v1",
                            "states_enumerated": sw.states_enumerated,
                            "cap": _SWEEP_MAX_STATES,
                            "status": sw.status,
                            "replans": replans,
                            "ts": datetime.utcnow().isoformat(),
                        }) + "\n")
                if sw.status == "coverage" and sw.saturated:
                    saturated = True
                    if not _saturation_receipt_emitted:
                        _saturation_receipt_emitted = True
                        _gr = _vset.growth_rate("abstract") if abstract_fn is not None else None
                        _emit_saturation_receipt(adapter, _vset, abstract_growth_rate=_gr, receipts_dir=receipts_dir)
                if sw.status in ("goal_paths", "coverage") and sw.paths and sw.paths[0]:
                    plan = Plan(actions=sw.paths[0], reason=f"sweep({sw.status}): {sw.detail}")
            if plan is None and goal_fn is not None:
                _ensure_interners_synced()
                _t0 = time.perf_counter()
                plan = plan_to_goal(champion, state, adapter.action_arity, goal_fn,
                                    start_step=adapter.t, max_depth=plan_depth,
                                    abstract_fn=abstract_fn,
                                    _state_interner=_pg_interner,
                                    _abstract_interner_cache=_pg_abs_interner)
                _t_plan += time.perf_counter() - _t0
                # F5 guard: plan_to_goal returns an empty-actions Plan for both
                # "goal_satisfied_at_start" and "no plan within depth N". Neither
                # should propagate as a real plan — the start-satisfied case is a
                # null/degenerate plan (no credit, no goal_reached, no progress);
                # the exhausted case falls through to novelty steering below.
                if plan is None or not plan.actions:
                    plan = None
            if plan is None and progress_fn is not None:
                # goal-cue steering: bias toward higher inferred progress, but every
                # few replans inject a novelty plan so a flat/wrong heuristic can't
                # trap the search (terminal verifier is still the only success signal)
                if replans % 3 == 2:
                    _ensure_interners_synced()
                    _t0 = time.perf_counter()
                    plan = plan_novelty(champion, state, adapter.action_arity, _vset._raw,
                                        visited_abstract=_vset._images.get("abstract"),
                                        start_step=adapter.t, max_depth=plan_depth,
                                        abstract_fn=abstract_fn,
                                        _state_interner=_pg_interner,
                                        _abstract_interner_cache=_pg_abs_interner)
                    _t_plan += time.perf_counter() - _t0
                else:
                    _ensure_interners_synced()
                    _t0 = time.perf_counter()
                    plan = plan_progress(champion, state, adapter.action_arity, progress_fn,
                                         start_step=adapter.t, max_depth=plan_depth,
                                         abstract_fn=abstract_fn,
                                         _state_interner=_pg_interner,
                                         _abstract_interner_cache=_pg_abs_interner)
                    _t_plan += time.perf_counter() - _t0
            elif plan is None:
                # only when reachability/goal produced nothing — DON'T overwrite a
                # coverage/goal plan (that made the whole sweep apparatus inert)
                _ensure_interners_synced()
                _t0 = time.perf_counter()
                plan = plan_novelty(champion, state, adapter.action_arity, _vset._raw,
                                    visited_abstract=_vset._images.get("abstract"),
                                    start_step=adapter.t, max_depth=plan_depth,
                                    abstract_fn=abstract_fn,
                                    _state_interner=_pg_interner,
                                    _abstract_interner_cache=_pg_abs_interner)
                _t_plan += time.perf_counter() - _t0
            if plan is None or not plan.actions:
                return PursuitReceipt(status="plan_exhausted", steps_executed=len(trace),
                                      levels_gained=_levels(adapter) - baseline,
                                      detail=(plan.reason if plan else "planner returned nothing"),
                                      replans=replans, trace=trace, saturated=saturated,
                                      observed_transitions=observed)
            for a in plan.actions:
                step_now = adapter.t
                # predict memo: period-4 verified on real data → key by (state_id, action, step%4)
                _sid = _pg_interner.get_id(state) if _pg_interner is not None else None
                _memo_key = (_sid if _sid is not None else state, a, step_now % 4)
                if _memo_key in _predict_memo:
                    predicted = _predict_memo[_memo_key]
                else:
                    _t0 = time.perf_counter()
                    predicted = predict(state, a, step_now)
                    _t_predict += time.perf_counter() - _t0
                    _predict_memo[_memo_key] = predicted
                _t0 = time.perf_counter()
                real = adapter.step(a)
                _t_env += time.perf_counter() - _t0
                trace.append(a)
                observed.append((state, a, real, step_now))
                # frontier memory: the observed live state is now visited
                if abstract_fn is not None and visited_store is not None:
                    visited_store.add(abstract_fn(real))
                    steps_since_save += 1
                    if visited_path is not None and steps_since_save >= 50:
                        save_visited(visited_path, visited_store)
                        steps_since_save = 0
                # A None prediction is a fail-closed error from the champion, not
                # agreement: pursuing blind under an erroring model is a divergence
                # event (terminal_witness_fingerprint emits its prediction_none kind).
                mismatch = predicted is None or real != predicted
                if _levels(adapter) > baseline:
                    detail = "terminal verifier event occurred after model steering"
                    divergence = None
                    if mismatch:
                        detail += "; terminal edge also refuted the transition law"
                        divergence = _divergence_payload(a, step_now, state, predicted, real)
                    return PursuitReceipt(status="goal_reached", steps_executed=len(trace),
                                          levels_gained=_levels(adapter) - baseline,
                                          detail=detail, divergence=divergence,
                                          replans=replans, trace=trace, saturated=saturated,
                                          observed_transitions=observed)
                if mismatch:
                    return PursuitReceipt(
                        status="model_diverged", steps_executed=len(trace),
                        levels_gained=_levels(adapter) - baseline,
                        detail="ratified law mispredicted a live transition off the witnessed basin; "
                               "re-identify before planning further",
                        divergence=_divergence_payload(a, step_now, state, predicted, real),
                        replans=replans, trace=trace, saturated=saturated,
                        observed_transitions=observed)
                state = real
                _vset.add(state)
                if len(trace) >= max_steps:
                    break
            replans += 1  # plan consumed without reaching goal → replan from the new state

        detail = f"budget exhausted ({len(trace)} steps, {replans} replans)"
        if saturated:
            detail += " — coverage SATURATED: all reachable object-states already visited (CEGAR trigger)"
        return PursuitReceipt(status="plan_exhausted", steps_executed=len(trace),
                              levels_gained=_levels(adapter) - baseline,
                              detail=detail, replans=replans, trace=trace,
                              saturated=saturated, observed_transitions=observed)
    finally:
        # persist on EVERY exit path (return, break, or exception)
        if visited_path is not None and visited_store is not None:
            save_visited(visited_path, visited_store)
        # Task 5: write 3 sub-phase timing rows (one shot, no per-step I/O)
        if receipts_dir is not None:
            _timing_path = Path(receipts_dir) / "phase_timings.jsonl"
            _timing_path.parent.mkdir(parents=True, exist_ok=True)
            with _timing_path.open("a") as _tf:
                for _phase, _secs in (
                    ("pursuit.plan", _t_plan),
                    ("pursuit.env_step", _t_env),
                    ("pursuit.predict", _t_predict),
                ):
                    _tf.write(json.dumps({
                        "schema": "ztare.phase_timing.v1",
                        "phase": _phase,
                        "seconds": _secs,
                        "depth": 2,
                        "started": _pursuit_started,
                    }) + "\n")


@dataclass
class ActLearnReceipt:
    status: str                    # goal_reached | converged_no_goal | ceiling | budget
    rounds: int = 0
    levels_gained: int = 0
    log_growth: "list[int]" = field(default_factory=list)   # log size after each round
    champions: "list[str]" = field(default_factory=list)
    detail: str = ""


def act_and_learn(adapter, log, action_arity, *, resynthesize, extend_at_ceiling=None,
                  progress_fn=None, max_rounds: int = 8, pursue_steps: int = 150,
                  plan_depth: int = 10):
    """Close the identify->act->learn cycle: identify a champion from `log`,
    pursue the goal, ABSORB the off-basin transitions the live env produced
    (they were never fit), re-identify on the grown log, repeat.

    This is the direct answer to the basin-coverage finding: a model that
    diverges hands back the exact transitions that expand its witnessing basin,
    so each round strictly grows the evidence and the model converges toward the
    reachable-state law instead of the single-episode-basin law.

    `resynthesize(log)` -> object with `.status` and `.champion` (the kernel's
    `synthesize`). `extend_at_ceiling(log)` optional -> a champion callable when
    synthesis hits grammar_ceiling (the earned-grammar hook); if None, ceiling
    ends the loop. Returns an ActLearnReceipt. `log` is mutated in place
    (append-only), so the caller keeps the grown evidence."""
    growth, champions = [], []
    for rnd in range(1, max_rounds + 1):
        result = resynthesize(log)
        champion = getattr(result, "champion", None)
        if getattr(result, "status", None) == "grammar_ceiling" and extend_at_ceiling is not None:
            champion = extend_at_ceiling(log)
        if champion is None:
            return ActLearnReceipt(status="ceiling", rounds=rnd, log_growth=growth,
                                   champions=champions,
                                   detail="synthesis cannot express the grown log; grammar ceiling")
        champions.append(str(champion)[:80])
        pr = pursue_goal(adapter, champion, progress_fn=progress_fn,
                         max_steps=pursue_steps, plan_depth=plan_depth)
        if pr.status == "goal_reached":
            return ActLearnReceipt(status="goal_reached", rounds=rnd,
                                   levels_gained=pr.levels_gained, log_growth=growth,
                                   champions=champions,
                                   detail="ratified-then-refined model completed a level")
        before = len(log)
        for (s, a, s_next, t) in pr.observed_transitions:
            log.append(s, a, s_next, t=t)
        growth.append(len(log))
        if len(log) == before:
            # nothing new to learn from this pursuit; the model is basin-complete
            # for what the current goal drives it toward
            return ActLearnReceipt(status="converged_no_goal", rounds=rnd,
                                   log_growth=growth, champions=champions,
                                   detail="pursuit produced no new transitions; basin-complete "
                                          "for the current (sealed) goal drive")
    return ActLearnReceipt(status="budget", rounds=max_rounds, log_growth=growth,
                           champions=champions, detail="round budget exhausted")


def _disagreement(candidates, grid: Grid, action_arity: int, step: int) -> int:
    """Number of behaviorally-distinct predictions the candidate set makes at
    this state — the multi-step generalization of the identification policy's
    1-step EIG (the seam's 'disagreement frontier' promise, completed)."""
    preds = set()
    for c in candidates:
        p = as_predictor(c)
        outs = tuple(p(grid, a, step) for a in range(action_arity))
        preds.add(outs)
    return len(preds)


def plan_disagreement(candidates, start: Grid, action_arity: int, *,
                      start_step: int = 0, max_depth: int = 10,
                      max_nodes: int = 20000) -> "Plan | None":
    """Plan toward the state where the surviving candidate committee DISAGREES
    most — the cheapest experiment that kills the most hypotheses. Simulation
    uses the FIRST candidate (they agree along the path until the frontier by
    construction of survivorship); execution against the live environment then
    settles the argument via the ordinary gates/divergence machinery."""
    if len(candidates) < 2:
        return None
    predict = as_predictor(candidates[0])
    import heapq
    best_plan, best_dis = [], 1
    seen = {(start, start_step % 6)}
    frontier = [(0, 0, start, start_step, [])]
    nodes, tie = 0, 0
    while frontier and nodes < max_nodes:
        _, _, grid, step, path = heapq.heappop(frontier)
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            key = (nxt, (step + 1) % 6)
            if key in seen:
                continue
            seen.add(key)
            nodes += 1
            tie += 1
            new_path = path + [a]
            dis = _disagreement(candidates, nxt, action_arity, step + 1)
            if dis > best_dis:
                best_dis, best_plan = dis, new_path
            heapq.heappush(frontier, (-dis, tie, nxt, step + 1, new_path))
    if not best_plan:
        return Plan(actions=[], reason=f"committee agrees everywhere reachable ({nodes} nodes)") \
            if nodes else None
    return Plan(actions=best_plan,
                reason=f"max-disagreement frontier ({best_dis} distinct predictions, "
                       f"{len(best_plan)} steps, {nodes} nodes)")
