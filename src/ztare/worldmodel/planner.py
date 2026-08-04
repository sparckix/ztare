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
import hashlib
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ponytail: env knob caps per-call reachability sweep cost (200k default exhausted 26 min/sprint
# at ls20 scale; 5000 gives ~29s/sprint with valid steering paths). Override when FSM is tiny.
_SWEEP_MAX_STATES = int(os.environ.get("ZTARE_SWEEP_MAX_STATES", "5000"))
_SWEEP_ESCALATION_MAX_STATES = int(
    os.environ.get("ZTARE_SWEEP_ESCALATION_MAX_STATES", "50000")
)
_ACQUISITION_ROUTING_SEEN: dict[Path, set[str]] = {}

from ztare.common.equivariance import stable_sha256 as _stable_sha256
from ztare.common.image_set import ImageMaintainingSet
from ztare.worldmodel.frontier_codec import (
    AbstractCarrierInterner, StateInterner, abstract_novelty, batch_novelty,
)
from ztare.worldmodel.gates import as_predictor
from ztare.worldmodel.goal_abduction import goal_edge_matches
from ztare.worldmodel.grid_dsl import Grid, Program, evaluate
from ztare.worldmodel.episode_log import Transition
from ztare.worldmodel.terminal_witness import terminal_witness_fingerprint
from ztare.worldmodel.transition_identity import (
    TransitionIdentity,
    authoritative_boundary,
)

_log = logging.getLogger(__name__)

# ponytail: env flag selects vectorized vs pure-Python novelty; default "1" (on)
_VECTORIZED = os.environ.get("ZTARE_VECTORIZED_FRONTIER", "1") != "0"


@dataclass
class Plan:
    actions: "list[int]"
    reason: str
    simulated_terminal: "Grid | None" = None


def _goal_sources_at(predicate, step: int) -> tuple:
    """Return source presentations that can still fire at ``step``.

    Predicates without a temporal-source interface remain ordinary searchable
    edges.  A predicate that does expose ``nearest_future_sources`` owns an
    exact-time witness identity; an empty result means that identity has
    expired, rather than authorizing an unprioritized search for an impossible
    edge.
    """
    if predicate is None:
        return ()
    nearest_sources = getattr(predicate, "nearest_future_sources", None)
    if callable(nearest_sources):
        return tuple(nearest_sources(step))
    return tuple(getattr(predicate, "goal_source_states", ()) or ())


def _active_goal_edge(predicate, step: int):
    nearest_sources = getattr(predicate, "nearest_future_sources", None)
    if callable(nearest_sources) and not _goal_sources_at(predicate, step):
        return None
    return predicate


def _current_chart_time_translation_certificate(
    carrier,
    *,
    carrier_sha256: str,
    transitions,
):
    """Propose erasing absolute time only on the active evidence chart.

    The common equivariance checker supplies the certificate.  The proposed
    generator is ``t -> t + 1`` with identity maps on every other coordinate;
    factored search still challenges the quotient at runtime and returns a
    non-commutation witness if a newly reached state exposes temporal phase.
    """
    if len(str(carrier_sha256 or "")) != 64:
        return None
    rows = tuple(row for row in transitions if isinstance(row, Transition))
    if not rows:
        return None
    from ztare.common.equivariance import (
        EquivarianceObservation,
        TransformationAction,
        certify_equivariance,
        stable_sha256,
    )
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import env_frame_indices

    boundaries = env_frame_indices(EpisodeLog(list(rows)))
    observations = tuple(
        EquivarianceObservation(
            state=row.s,
            intervention=row.a,
            time=row.t,
            successor=row.s_next,
            observation_ref=f"active_evidence:transition:{index}",
            transition_kind=("reset_boundary" if index in boundaries else "dynamics"),
            classification_authority=("worldmodel_gate" if index in boundaries else ""),
        )
        for index, row in enumerate(rows)
    )
    action = TransformationAction(
        element_id="time_translation:+1",
        implementation_sha256=stable_sha256({
            "source_map": "identity",
            "target_map": "identity",
            "intervention_map": "identity",
            "time_map": "integer_successor",
        }),
        source_map=lambda value: value,
        target_map=lambda value: value,
        intervention_map=lambda value: value,
        time_map=lambda value: value + 1,
        declared_domain="law-scored transitions in one active lifecycle chart",
    )
    return certify_equivariance(
        carrier=carrier,
        carrier_sha256=carrier_sha256,
        action=action,
        observations=observations,
        trusted_boundary_authorities=frozenset({"worldmodel_gate"}),
        min_tested=min(16, max(1, len(rows) - len(boundaries))),
        min_coverage_ratio=1.0,
    )


def _bounded_plan_outcome(
    plan: "Plan | None",
    *,
    policy: str,
    found_status: str,
    missing_status: str = "no_plan_within_bound",
) -> dict:
    return {
        "policy": policy,
        "status": found_status if plan is not None and plan.actions else missing_status,
        "exhaustive": False,
    }


def plan_to_goal(champion: Program, start: Grid, action_arity: int,
                 goal_fn=None, *, goal_edge_fn=None, start_step: int = 0,
                 max_depth: int = 12,
                 abstract_fn=None,
                 max_nodes: int = 20000,
                 _state_interner: "StateInterner | None" = None,
                 ) -> "Plan | None":
    """Bounded search for a simulated goal state or attested goal edge.

    Ordinary predicates use BFS.  A typed environment-edge predicate may expose
    its witnessed source states; then the same node budget is best-first ordered
    by cell distance to those sources.  This changes frontier allocation only:
    the receipt does not enter a prompt, a source state is not treated as a
    general goal law, and exact edge matching still decides success.  Pruning
    keeps ``(state, full_time)`` identity unless a temporal quotient is certified.
    """
    predict = as_predictor(champion)
    goal_edge_fn = _active_goal_edge(goal_edge_fn, start_step)
    if goal_fn is None and goal_edge_fn is None:
        return None
    if goal_fn is not None and goal_fn(start):
        # F5 guard (2026-07-09): a goal that is already satisfied at the start
        # state is a degenerate / null plan. Returning it with empty actions and
        # a distinct reason string ensures pursue_goal's empty-actions filter
        # (which sets plan=None) catches it and it can NEVER propagate as a
        # goal_reached status or be scored as progress. A differs_from_start=False
        # predicate always fires here; a well-formed abduction goal (always True)
        # would produce the same degenerate path. Neither receives credit.
        return Plan(actions=[], reason="goal_satisfied_at_start: null plan, no credit")
    # A target predicate has not certified that it is constant on the caller's
    # abstraction fibers.  Keep concrete state identity for target search;
    # abstraction remains available to acquisition-only planners.
    key_abstraction = None
    # FIX B: interner-aware keying — int IDs are exact surrogates for grid identity.
    if _state_interner is not None:
        _start_key = (_state_interner.intern(start), start_step)
        def _key(g, s): return (_state_interner.intern(g), s)
    else:
        _start_key = _planner_key(start, start_step, key_abstraction)
        def _key(g, s): return _planner_key(g, s, key_abstraction)
    seen = {_start_key}
    goal_sources = _goal_sources_at(goal_edge_fn, start_step)
    prioritized = bool(goal_sources)
    if prioritized:
        import heapq

        def distance(grid: Grid) -> int:
            return min(_hamming(grid, target) for target in goal_sources)

        tie = 0
        frontier = [(distance(start), 0, tie, start, start_step, [])]
    else:
        frontier = deque([(start, start_step, [])])
    nodes = 0
    while frontier and nodes < max_nodes:
        if prioritized:
            _distance, _depth, _tie, grid, step, path = heapq.heappop(frontier)
        else:
            grid, step, path = frontier.popleft()
        if len(path) >= max_depth:
            continue
        for a in range(action_arity):
            if (
                goal_edge_fn is not None
                and goal_edge_matches(goal_edge_fn, grid, a, step)
            ):
                return Plan(
                    actions=path + [a],
                    reason=f"environment goal edge reachable in {len(path) + 1} steps "
                           f"(searched {nodes} nodes; "
                           f"policy={'witness-distance' if prioritized else 'breadth-first'})",
                    simulated_terminal=grid,
                )
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            key = _key(nxt, step + 1)
            if key in seen:
                continue
            seen.add(key)
            nodes += 1
            new_path = path + [a]
            if goal_fn is not None and goal_fn(nxt):
                return Plan(actions=new_path,
                            reason=f"goal reachable in {len(new_path)} steps "
                                   f"(searched {nodes} nodes)",
                            simulated_terminal=nxt)
            if prioritized:
                tie += 1
                heapq.heappush(
                    frontier,
                    (distance(nxt), len(new_path), tie, nxt, step + 1, new_path),
                )
            else:
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
        return (grid, step)
    return (abstract_fn(grid), step)


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
                    _interner.mark_visited(_g)
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
                if abstract_fn is not None:
                    # Abstract novelty is a membership indicator (0/1).  The
                    # first unseen quotient class is therefore already
                    # optimal; continuing to enumerate cannot improve the
                    # acquisition objective.
                    return Plan(
                        actions=best_plan,
                        reason=(
                            "first unseen abstract carrier "
                            f"({len(best_plan)} steps, {nodes} nodes)"
                        ),
                    )
            tie += 1
            heapq.heappush(frontier, (-nov, tie, nxt, step + 1, new_path))
    if not best_plan:
        return Plan(actions=[], reason=f"no novel state reachable ({nodes} nodes)") \
            if nodes else None
    return Plan(actions=best_plan,
                reason=f"most-novel reachable state (novelty {best_novelty}, "
                       f"{len(best_plan)} steps, {nodes} nodes)")


def plan_witness_gap(champion: Program, start: Grid, action_arity: int,
                     witnessed_pairs: "set[tuple]", *, start_step: int = 0,
                     max_depth: int = 12, abstract_fn=None, support_fn=None,
                     max_nodes: int = 20000) -> "Plan | None":
    """Best-first toward the nearest reachable unsupported operation context.

    ``abstract_fn`` owns transition-state equality for search deduplication.
    ``support_fn`` owns acquisition support: its image, paired with an action,
    is looked up in ``witnessed_pairs``.  The identities may coincide, but a
    coarse support identity must not collapse transition-distinct routes.
    When ``support_fn`` is absent it defaults to ``abstract_fn`` for backward
    compatibility.

    Acquisition rationale (substrate-general): novelty is scored on the model's
    PREDICTED successors, so a transition the model predicts wrongly looks
    "already seen" and is never selected — the planner starves itself of the
    counterexamples it needs. Witness support is model-independent: an
    unsupported (context, action) pair is extrapolation by definition, and
    extrapolation is where counterexamples live. Steering only; the terminal
    verifier still owns success, so a wrong steer costs efficiency, never
    correctness. Both projections and the witnessed set come from the caller.
    """
    predict = as_predictor(champion)
    _transition_alpha = abstract_fn if abstract_fn is not None else (
        lambda g: tuple(map(tuple, g)))
    _support_alpha = support_fn if support_fn is not None else _transition_alpha
    from collections import deque
    seen = {(_transition_alpha(start), start_step)}
    q = deque([(start, start_step, [])])
    nodes = 0
    while q and nodes < max_nodes:
        grid, step, path = q.popleft()
        support = _support_alpha(grid)
        for a in range(action_arity):
            if (support, a) not in witnessed_pairs:
                return Plan(actions=path + [a],
                            reason=(f"unsupported operation pair at depth "
                                    f"{len(path) + 1} ({nodes} nodes)"))
            if len(path) + 1 >= max_depth:
                continue
            nxt = predict(grid, a, step)
            if nxt is None:
                continue
            nodes += 1
            key = (_transition_alpha(nxt), step + 1)
            if key in seen:
                continue
            seen.add(key)
            q.append((nxt, step + 1, path + [a]))
    return None


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
        _start_key = (_state_interner.intern(start), start_step)
        def _key(g, s): return (_state_interner.intern(g), s)
    elif _abstract_interner_cache is not None:
        _start_key = (_abstract_interner_cache.intern(abstract_fn(start)), start_step)
        def _key(g, s): return (_abstract_interner_cache.intern(abstract_fn(g)), s)
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
    observed_transitions: "list[Transition]" = field(default_factory=list)
    # Typed terminal outcome of the search policy that selected (or failed to
    # select) the next intervention.  This remains separate from live task and
    # environment outcomes.
    planning_outcome: "dict" = field(default_factory=dict)
    # A task-hypothesis edge reached by the executed plan.  The external task
    # adjudicator still decides discharge; this receipt only identifies the
    # candidate relation that may be refuted when adjudication remains open.
    candidate_goal_edge: "dict | None" = None


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


def _append_acquisition_routing(
    receipts_dir,
    *,
    visited_store,
    plan,
    policy: str,
    search_status: str,
    states_enumerated: int = 0,
    exhaustive: bool = False,
) -> None:
    """Record which substrate-neutral acquisition policy owned a plan."""
    if receipts_dir is None:
        return
    acquisition_path = Path(receipts_dir) / "acquisition_routing.jsonl"
    acquisition_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frontier_scope = json.loads(
            (Path(receipts_dir) / "latest_frontier_scope.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, ValueError):
        frontier_scope = {}
    identity = hashlib.sha256(json.dumps({
        "policy": policy,
        "search_status": search_status,
        "plan_found": bool(plan and plan.actions),
        "exhaustive": bool(exhaustive),
        "source_epoch": frontier_scope.get("source_epoch"),
        "evidence_hash": frontier_scope.get("evidence_hash"),
        "abstraction_version": frontier_scope.get("abstraction_version"),
    }, sort_keys=True).encode()).hexdigest()
    seen = _ACQUISITION_ROUTING_SEEN.setdefault(acquisition_path, set())
    if not seen and acquisition_path.is_file():
        for line in acquisition_path.read_text(encoding="utf-8").splitlines():
            try:
                prior = json.loads(line)
            except (TypeError, ValueError):
                continue
            if prior.get("routing_identity_sha256"):
                seen.add(str(prior["routing_identity_sha256"]))
    if identity in seen:
        return
    seen.add(identity)
    with acquisition_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "schema": "ztare-acquisition-routing-v1",
            "terminal_identity": "undefined_for_active_epoch",
            "objective_identity": "abstraction_shattering",
            "policy": policy,
            "persistent_frontier_size": len(visited_store or ()),
            "plan_found": bool(plan and plan.actions),
            "reason": getattr(plan, "reason", "") if plan else "",
            "search_status": search_status,
            "states_enumerated": int(states_enumerated),
            "exhaustive": bool(exhaustive),
            "routing_identity_sha256": identity,
        }, sort_keys=True) + "\n")


def pursue_goal(adapter, champion: Program, *, goal_fn=None, goal_edge_fn=None,
                acquisition_obligation=None,
                excluded_edge_fn=None,
                progress_fn=None,
                resource_colors=None, invariants=None, abstract_fn=None,
                coverage_fn=None, visited_store=None, visited_path=None,
                evidence_states=None, evidence_transitions=None,
                control_boundary_edges=None,
                control_history_prefix=None,
                control_operation_effect_history_prefix=None,
                control_history_trajectories=None,
                carrier_execution_sha256: str = "",
                control_task_contract_sha256: str = "",
                max_steps: int = 400, max_replans: int = 8,
                plan_depth: int = 12, receipts_dir=None) -> PursuitReceipt:
    """Plan under `champion`, execute against the live adapter, stop on the
    terminal verifier event. Steering is NOVELTY search by default (drive toward the
    most-novel state the model predicts) — general and game-agnostic, with no
    model-authored success criterion. ``goal_fn(grid)`` targets a state;
    ``goal_edge_fn(grid, action[, time])`` targets an environment-attested success edge
    without asking the within-epoch carrier to simulate through the boundary.
    ``acquisition_obligation`` is a separately typed experiment obligation: it
    may seek a new context for a witnessed operation trigger but cannot define
    success, promote a carrier, or discharge the task.
    ``excluded_edge_fn`` carries environment-adjudicated non-discharge edges.
    It constrains simulated control only; the transition carrier is unchanged.

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

    def planning_predict(source, intervention, time_value):
        """One search door for evidence-owned control exclusions.

        A respawn edge is outside the within-epoch transition carrier.  Letting
        search simulate through it turns the carrier's counterfactual image
        into a reachable novelty target.  The live adapter may exclude that
        edge after adjudicating it as a non-discharge boundary; prediction used
        for execution comparison remains the original carrier above.
        """
        if excluded_edge_fn is not None and excluded_edge_fn(
            source, intervention, time_value
        ):
            return None
        return predict(source, intervention, time_value)

    planning_model = planning_predict if excluded_edge_fn is not None else champion
    factored_projection = getattr(champion, "_ztare_factored_projection", None)
    clear_projection_caches = getattr(
        factored_projection, "clear_runtime_caches", None
    )
    if callable(clear_projection_caches):
        clear_projection_caches()
    factored_projection_compiled_emitted = False
    pursuit_start_step = int(adapter.t)
    control_operation_namespace = (
        f"{type(adapter).__module__}.{type(adapter).__qualname__}:"
        f"arity={int(adapter.action_arity)}"
    )
    baseline = _levels(adapter)
    state = adapter.state
    if goal_fn is not None and goal_fn(state):
        return PursuitReceipt(
            status="candidate_goal_reached",
            steps_executed=0,
            levels_gained=0,
            detail="candidate task predicate already holds at leg entry",
            replans=0,
            trace=[],
            saturated=False,
            observed_transitions=[],
            planning_outcome={
                "policy": "candidate_goal_adjudication",
                "status": "candidate_predicate_satisfied",
                "exhaustive": False,
            },
        )
    evidence_states = tuple(evidence_states or ())
    # Witness-support index for terminal acquisition. Transition equality and
    # acquisition support are consumer-distinct identities: search retains the
    # former while support membership uses coverage_fn(abstract_fn(state)).
    # Model-independent by construction (observations only). None when the
    # caller supplied no transitions or the support projection is not total.
    _transition_alpha = abstract_fn if abstract_fn is not None else (
        lambda g: tuple(map(tuple, g)))
    _support_alpha = (
        (lambda g: coverage_fn(_transition_alpha(g)))
        if coverage_fn is not None
        else _transition_alpha
    )
    _witnessed_pairs: "set[tuple] | None" = None
    if evidence_transitions:
        try:
            _witnessed_pairs = {
                (_support_alpha(tr.s), tr.a) for tr in evidence_transitions
            }
        except Exception:
            _witnessed_pairs = None
    time_translation_certificate = _current_chart_time_translation_certificate(
        predict,
        carrier_sha256=carrier_execution_sha256,
        transitions=tuple(evidence_transitions or ()),
    )
    trace: "list[int]" = []
    observed: "list[Transition]" = []
    # ponytail: one ImageMaintainingSet replaces the visited/visited_abstract pair;
    # 'abstract' image is co-maintained pointwise on every add — O(1) vs O(|visited|)
    # per BFS node in plan_novelty. Functoriality holds: abstract_fn is grid→carrier
    # with no set-level dependence.
    _functors = {"abstract": abstract_fn} if abstract_fn is not None else {}
    _vset = ImageMaintainingSet(functors=_functors, receipts_dir=receipts_dir)
    _vset.add(state)
    persistent_abstract = set(visited_store or ()) if abstract_fn is not None else set()
    replans = 0
    replan_limit = max_replans

    # Persistent interners share simulated-state identity across planners while
    # only live observations enter their visited membership.
    _pg_interner: "StateInterner | None" = None
    _pg_abs_interner: "AbstractCarrierInterner | None" = None
    if _VECTORIZED and abstract_fn is None:
        _pg_interner = StateInterner()
        _pg_interner.mark_visited(state)
    elif _VECTORIZED and abstract_fn is not None:
        _pg_abs_interner = AbstractCarrierInterner()
        for carrier in persistent_abstract:
            _pg_abs_interner.mark_visited(carrier)
        _pg_abs_interner.mark_visited(abstract_fn(state))

    def _visited_abstract():
        if abstract_fn is None:
            return None
        return persistent_abstract | set(_vset._images.get("abstract") or ())

    def _novelty_view(*, projected: bool):
        carriers = _visited_abstract()
        if not projected or abstract_fn is None or coverage_fn is None:
            return abstract_fn, carriers, _pg_abs_interner
        return (
            lambda grid: coverage_fn(abstract_fn(grid)),
            {coverage_fn(carrier) for carrier in carriers or ()},
            None,
        )

    # Prediction memo identity includes full adapter time.  A finite period is a
    # carrier theorem/certificate, not a property inferred from 20 visible rows.
    _predict_memo: dict = {}
    acquisition_policy = "projected_reachability_coverage"
    last_planning_outcome: dict = {}
    factored_planning_outcome: dict = {}
    active_skill_windows: list[dict] = []
    planned_skill_windows: list[dict] = []
    continual_skill_runtime: dict = {}

    def _skill_window_receipts() -> tuple[list[dict], list[dict], list[dict]]:
        """Separate selected, completed, and partially executed skill windows."""

        selected: dict[tuple, dict] = {}
        for window in planned_skill_windows:
            identity = (
                window["family_sha256"],
                window["revision_sha256"],
                window["context_sha256"],
                int(window["start_step"]),
                int(window["end_step"]),
            )
            selected[identity] = {
                **window,
                "memory_ref": "continual_skill_memory.json",
            }
        planned = [
            selected[identity]
            for identity in sorted(selected)
        ]
        completed = []
        partial = []
        current_step = int(adapter.t)
        for window in planned:
            start_step = int(window["start_step"])
            end_step = int(window["end_step"])
            operation_count = max(0, end_step - start_step)
            executed = max(
                0,
                min(operation_count, current_step - start_step),
            )
            if executed == operation_count and operation_count:
                completed.append({
                    **window,
                    "status": "completed",
                    "executed_operation_count": executed,
                })
            elif executed:
                partial.append({
                    **window,
                    "status": "partial",
                    "executed_operation_count": executed,
                })
        return planned, completed, partial

    def _planning_receipt() -> dict:
        """Preserve a consumer projection result across generic fallbacks."""
        current = dict(last_planning_outcome)
        completed = []
        if planned_skill_windows:
            planned, completed, partial = _skill_window_receipts()
            current["continual_skill_planned_windows"] = planned
            current["continual_skill_execution_windows"] = completed
            current["continual_skill_partial_execution_windows"] = partial
        if trace and control_task_contract_sha256:
            option_markers_by_end: dict[int, list[str]] = {}
            for window in completed:
                effect_family = str(
                    window.get("effect_option_family_sha256") or ""
                )
                if effect_family:
                    option_markers_by_end.setdefault(
                        int(window["end_step"]),
                        [],
                    ).append("effect_option:" + effect_family)
            process_tokens = []
            for offset, operation in enumerate(trace):
                process_tokens.append(
                    "primitive:" + _stable_sha256({
                        "operation_namespace": (
                            control_operation_namespace
                        ),
                        "operation": operation,
                    })
                )
                process_tokens.extend(sorted(
                    option_markers_by_end.get(
                        pursuit_start_step + offset + 1,
                        (),
                    )
                ))
            current["continual_control_process_tokens"] = process_tokens
        if factored_planning_outcome and current != factored_planning_outcome:
            current["factored_predecessor"] = dict(factored_planning_outcome)
        return current

    def _record_skill_cegar_counterexample(
        *,
        step_now: int,
        divergence: dict,
    ) -> dict | None:
        """Feed a path-local prediction failure back to its skill revision."""

        window = next(
            (
                row for row in active_skill_windows
                if row["start_step"] <= step_now < row["end_step"]
            ),
            None,
        )
        if window is None or not continual_skill_runtime:
            return None
        try:
            from ztare.common.continual_skill_memory import (
                IntrinsicLearningSignal,
                load_continual_skill_memory,
                record_intrinsic_signal,
                save_continual_skill_memory,
            )
            from ztare.common.equivariance import stable_sha256

            memory_path = continual_skill_runtime["memory_path"]
            memory = load_continual_skill_memory(memory_path)
            failed_step = int(step_now - window["start_step"])
            signal = IntrinsicLearningSignal(
                family_sha256=window["family_sha256"],
                revision_sha256=window["revision_sha256"],
                context_sha256=continual_skill_runtime["context_sha256"],
                evidence_epoch_sha256=stable_sha256({
                    "memory_before": memory.memory_sha256,
                    "divergence": divergence,
                }),
                kind="cegar_counterexample",
                disposition="requires_refinement",
                failed_step=failed_step,
                evidence_refs=(
                    "runtime_divergence:"
                    + stable_sha256(divergence),
                ),
            )
            updated = record_intrinsic_signal(memory, signal)
            save_continual_skill_memory(memory_path, updated)
            receipt = {
                "schema": "ztare-runtime-skill-cegar-feedback-v1",
                "status": "revision_revoked",
                "family_sha256": window["family_sha256"],
                "revision_sha256": window["revision_sha256"],
                "failed_step": failed_step,
                "signal_sha256": signal.signal_sha256,
                "memory_sha256": updated.memory_sha256,
            }
            last_planning_outcome[
                "continual_skill_cegar_feedback"
            ] = receipt
            return receipt
        except Exception as error:  # noqa: BLE001
            receipt = {
                "schema": "ztare-runtime-skill-cegar-feedback-v1",
                "status": "feedback_failed",
                "error_type": type(error).__name__,
            }
            last_planning_outcome[
                "continual_skill_cegar_feedback"
            ] = receipt
            return receipt

    # Task 5: accumulating sub-phase timing counters (float seconds, no per-step I/O)
    _t_plan: float = 0.0
    _t_env: float = 0.0
    _t_predict: float = 0.0
    _pursuit_started: str = datetime.utcnow().isoformat()

    def _factored_attempt(
        problem,
        policy: str,
        *,
        widen: bool = False,
        initial_cap: int | None = None,
        max_cap: int | None = None,
    ):
        """Run one typed search route and emit its complete consequence chain."""
        nonlocal _t_plan, factored_projection_compiled_emitted
        from ztare.common.factored_search import search_factored
        from ztare.common.schema_routes import append_consequence_event
        from ztare.worldmodel.compiled_fiber_planning import (
            append_projection_receipt,
        )

        if receipts_dir is not None and not factored_projection_compiled_emitted:
            append_projection_receipt(
                receipts_dir,
                projection=factored_projection,
                event="compiled",
                problem=problem,
            )
            factored_projection_compiled_emitted = True
        base_cap = min(
            _SWEEP_MAX_STATES,
            max(1, int(initial_cap or _SWEEP_MAX_STATES)),
        )
        cap = base_cap
        cap_limit = max(base_cap, int(max_cap or _SWEEP_ESCALATION_MAX_STATES))
        started = time.perf_counter()
        while True:
            result = search_factored(
                predict=getattr(problem, "predict", planning_predict),
                start=state,
                interventions=tuple(range(adapter.action_arity)),
                problem=problem,
                start_time=adapter.t,
                max_depth=plan_depth * 6,
                max_states=cap,
            )
            if (
                result.status != "search_budget_exhausted"
                or not widen
                or cap >= cap_limit
            ):
                break
            cap = min(cap_limit, max(cap + 1, cap * 5))
        _t_plan += time.perf_counter() - started
        outcome = {
            "policy": policy,
            "status": result.status,
            "states_generated": result.generated,
            "states_expanded": result.expanded,
            "problem_id": problem.problem_id,
            "exhaustive": result.status == "projected_frontier_exhausted",
        }
        temporal_certificate = getattr(
            problem, "time_translation_certificate", None
        )
        if temporal_certificate is not None:
            from ztare.common.equivariance import stable_sha256

            outcome["time_translation_certificate"] = {
                "status": temporal_certificate.status,
                "certificate_sha256": stable_sha256(
                    temporal_certificate.to_dict()
                ),
                "tested": temporal_certificate.tested,
                "coverage_ratio": temporal_certificate.coverage_ratio,
                "boundary_excluded": temporal_certificate.boundary_excluded,
            }
        if result.continuation_actions:
            outcome["continuation_length"] = len(result.continuation_actions)
        if base_cap != _SWEEP_MAX_STATES:
            outcome["allocation"] = {
                "trigger": "terminal_identity_undefined",
                "from_cap": _SWEEP_MAX_STATES,
                "to_cap": base_cap,
                "consumer_action": "prefer_information_yield",
            }
        if cap != base_cap:
            outcome["allocation"] = {
                "trigger": "search_budget_exhausted",
                "from_cap": base_cap,
                "to_cap": cap,
                "consumer_action": "widen_factored_search",
            }
        if result.projection_counterexample:
            outcome["projection_counterexample"] = dict(
                result.projection_counterexample
            )
        if receipts_dir is not None:
            route = {
                "contract_id": "factored_search_outcome_totality.v1",
                "subject_id": problem.problem_id,
                "outcome": result.status,
                "evidence_refs": problem.evidence_refs,
            }
            append_consequence_event(receipts_dir, event="produced", **route)
            append_projection_receipt(
                receipts_dir,
                projection=factored_projection,
                event="first_fire",
                problem=problem,
                search_result=result,
            )
            append_consequence_event(receipts_dir, event="consumed", **route)
        return result, outcome

    try:
        while len(trace) < max_steps and replans <= replan_limit:
            plan = None
            active_skill_windows = []
            planned_acquisition_transaction = False
            factored_planning_outcome = {}
            planned_undefined_terminal = False
            incremental_attempted = False
            active_goal_edge_fn = _active_goal_edge(goal_edge_fn, adapter.t)
            goal_target_kind = str(
                getattr(goal_fn, "target_kind", "defined_terminal")
            )
            terminal_identity_defined = (
                (
                    goal_fn is not None
                    and goal_target_kind != "hypothesis_version_space"
                )
                or active_goal_edge_fn is not None
            )
            # An accepted carrier may expose a substrate lowering into the
            # common factored-search protocol.  With a witnessed edge it serves
            # target steering; without one it serves current-lifecycle factor
            # acquisition.  Both paths retain the adapter adjudicator and the
            # runtime non-commutation guard.
            if factored_projection is not None:
                factored_policy = ""
                factored_problem = None
                try:
                    if acquisition_obligation is not None:
                        factored_policy = "factored_operation_discrimination"
                        factored_problem = (
                            factored_projection.operation_discrimination_problem(
                                acquisition_obligation,
                                state,
                                planning_predict,
                            )
                        )
                    elif active_goal_edge_fn is not None:
                        factored_policy = "factored_terminal_edge_search"
                        factored_problem = factored_projection.problem_for(
                            active_goal_edge_fn, state
                        )
                    elif goal_fn is not None:
                        if goal_target_kind == "hypothesis_version_space":
                            factored_policy = "factored_goal_experiment"
                            factored_problem = (
                                factored_projection.goal_experiment_problem(
                                    start=state,
                                    target=goal_fn,
                                    predict=planning_predict,
                                    evidence_states=(
                                        *evidence_states,
                                        *_vset._raw,
                                    ),
                                    time_translation_certificate=(
                                        time_translation_certificate
                                    ),
                                )
                            )
                        else:
                            factored_policy = "factored_goal_search"
                            factored_problem = factored_projection.goal_problem(
                                start=state,
                                target=goal_fn,
                            )
                    elif goal_fn is None:
                        partial_factory = getattr(
                            factored_projection,
                            "partial_operation_problem",
                            None,
                        )
                        factored_problem = (
                            partial_factory(start=state, predict=planning_predict)
                            if callable(partial_factory)
                            else None
                        )
                        if factored_problem is not None:
                            factored_policy = "factored_partial_operation_completion"
                    if (
                        factored_problem is None
                        and evidence_states
                        and (
                            goal_fn is None
                            or goal_target_kind == "hypothesis_version_space"
                        )
                    ):
                        if goal_target_kind == "hypothesis_version_space":
                            factored_policy = (
                                "factored_goal_information_acquisition"
                            )
                            factored_problem = (
                                factored_projection.goal_discrimination_problem(
                                    start=state,
                                    target=goal_fn,
                                    evidence_states=(
                                        *evidence_states,
                                        *_vset._raw,
                                    ),
                                )
                            )
                        else:
                            factored_policy = "factored_operation_acquisition"
                            factored_problem = factored_projection.acquisition_problem(
                                start=state,
                                evidence_states=(
                                    *evidence_states,
                                    *_vset._raw,
                                ),
                                evidence_ref="active_lifecycle_observations",
                            )
                except Exception as _projection_error:  # noqa: BLE001
                    return PursuitReceipt(
                        status="apparatus_obstructed",
                        steps_executed=len(trace),
                        levels_gained=_levels(adapter) - baseline,
                        detail=(
                            "factored projection failed before search; repair or "
                            "retire that projection before scientific fallback"
                        ),
                        replans=replans,
                        trace=trace,
                        saturated=saturated,
                        observed_transitions=observed,
                        planning_outcome={
                            "policy": factored_policy or "factored_projection",
                            "status": "projection_instrument_error",
                            "error_type": type(_projection_error).__name__,
                        },
                    )
                if factored_problem is not None:
                    factored_result, last_planning_outcome = _factored_attempt(
                        factored_problem,
                        factored_policy,
                        widen=(
                            terminal_identity_defined
                            or goal_target_kind == "hypothesis_version_space"
                        ),
                        initial_cap=(
                            max(128, _SWEEP_MAX_STATES // 20)
                            if goal_target_kind == "hypothesis_version_space"
                            and factored_policy in {
                                "factored_goal_experiment",
                                "factored_goal_information_acquisition",
                            }
                            else None
                        ),
                        max_cap=(
                            _SWEEP_MAX_STATES
                            if goal_target_kind == "hypothesis_version_space"
                            else None
                        ),
                    )
                    if (
                        factored_policy == "factored_operation_acquisition"
                        and factored_result.status
                        == "projected_frontier_exhausted"
                    ):
                        factor_novelty_outcome = dict(last_planning_outcome)
                        try:
                            mechanism_problem = (
                                factored_projection.mechanism_acquisition_problem(
                                    start=state,
                                    evidence_transitions=tuple(
                                        (
                                            *tuple(evidence_transitions or ()),
                                            *observed,
                                        )
                                    ),
                                    predict=planning_predict,
                                    evidence_ref=(
                                        "active_lifecycle_transition_evidence"
                                    ),
                                    boundary_edges=tuple(
                                        control_boundary_edges or ()
                                    ),
                                    history_trajectories=tuple(
                                        control_history_trajectories or ()
                                    ),
                                )
                            )
                        except Exception as _mechanism_error:  # noqa: BLE001
                            return PursuitReceipt(
                                status="apparatus_obstructed",
                                steps_executed=len(trace),
                                levels_gained=_levels(adapter) - baseline,
                                detail=(
                                    "partial-action transport failed after the "
                                    "factor-novelty consumer exhausted"
                                ),
                                replans=replans,
                                trace=trace,
                                saturated=saturated,
                                observed_transitions=observed,
                                planning_outcome={
                                    "policy": "factored_mechanism_acquisition",
                                    "status": "projection_instrument_error",
                                    "error_type": type(
                                        _mechanism_error
                                    ).__name__,
                                    "factor_novelty_predecessor": (
                                        factor_novelty_outcome
                                    ),
                                },
                            )
                        if mechanism_problem is None:
                            return PursuitReceipt(
                                status="mechanism_projection_unavailable",
                                steps_executed=len(trace),
                                levels_gained=_levels(adapter) - baseline,
                                detail=(
                                    "factor novelty exhausted and no "
                                    "evidence-backed mechanism effect remained"
                                ),
                                replans=replans,
                                trace=trace,
                                saturated=True,
                                observed_transitions=observed,
                                planning_outcome={
                                    "policy": "factored_mechanism_acquisition",
                                    "status": "no_transportable_effect",
                                    "exhaustive": True,
                                    "factor_novelty_predecessor": (
                                        factor_novelty_outcome
                                    ),
                                },
                            )
                        factored_policy = "factored_mechanism_acquisition"
                        factored_problem = mechanism_problem
                        from ztare.common.partial_action_system import (
                            plan_observed_action_frontier,
                        )
                        history_lift_kind = str(
                            getattr(
                                mechanism_problem.history_lift,
                                "history_kind",
                                "",
                            )
                            or ""
                        )
                        observed_start_key = (
                            mechanism_problem.observed_start_key(
                                state,
                                tuple(control_history_prefix or ()),
                                tuple(
                                    control_operation_effect_history_prefix
                                    or ()
                                ),
                            )
                            if history_lift_kind == "operation_effect"
                            else mechanism_problem.observed_start_key(
                                state,
                                tuple(control_history_prefix or ()),
                            )
                        )
                        observed_frontier = plan_observed_action_frontier(
                            mechanism_problem.action_system,
                            start_key=observed_start_key,
                            operations=tuple(range(adapter.action_arity)),
                            max_depth=plan_depth * 12,
                        )
                        boundary_reachability_fibers = None
                        boundary_reachability_frontier = None
                        if callable(
                            getattr(
                                mechanism_problem,
                                "acquisition_context_key",
                                None,
                            )
                        ):
                            from ztare.common.boundary_reachability import (
                                compile_boundary_reachability_fibers,
                                plan_boundary_reachability_frontier,
                            )

                            boundary_reachability_fibers = (
                                compile_boundary_reachability_fibers(
                                    mechanism_problem.action_system,
                                    operations=tuple(
                                        range(adapter.action_arity)
                                    ),
                                    context_key=(
                                        mechanism_problem
                                        .acquisition_context_key
                                    ),
                                    support_key=(
                                        mechanism_problem
                                        .acquisition_support_key
                                    ),
                                )
                            )
                            boundary_reachability_frontier = (
                                plan_boundary_reachability_frontier(
                                    boundary_reachability_fibers,
                                    start_key=observed_start_key,
                                    max_depth=plan_depth * 12,
                                )
                            )
                        from ztare.common.predictive_quotient import (
                            compile_predictive_compatibility,
                            compile_predictive_quotient,
                            plan_predictive_support_frontier,
                            plan_predictive_quotient_frontier,
                        )

                        predictive_quotient = compile_predictive_quotient(
                            mechanism_problem.action_system,
                            operations=tuple(
                                range(adapter.action_arity)
                            ),
                        )
                        predictive_frontier = (
                            plan_predictive_quotient_frontier(
                                predictive_quotient,
                                source_system=(
                                    mechanism_problem.action_system
                                ),
                                start_source_key=observed_start_key,
                                operations=tuple(
                                    range(adapter.action_arity)
                                ),
                                max_depth=plan_depth * 12,
                            )
                            if (
                                predictive_quotient.passed_section
                                and predictive_quotient.passed_transport
                                and predictive_quotient.compressed
                            )
                            else None
                        )
                        predictive_compatibility = (
                            compile_predictive_compatibility(
                                mechanism_problem.action_system,
                                operations=tuple(
                                    range(adapter.action_arity)
                                ),
                            )
                        )
                        predictive_support_frontier = (
                            plan_predictive_support_frontier(
                                predictive_compatibility,
                                source_system=(
                                    mechanism_problem.action_system
                                ),
                                start_source_key=observed_start_key,
                                operations=tuple(
                                    range(adapter.action_arity)
                                ),
                                max_depth=plan_depth * 12,
                            )
                        )
                        orbit_completion = (
                            next(
                                (
                                    experiment
                                    for experiment
                                    in predictive_quotient.orbit_completions
                                    if (
                                        experiment.source_class
                                        == predictive_frontier.target_source_sha256
                                        and predictive_frontier.target_operation
                                        in experiment.query_operations
                                    )
                                ),
                                None,
                            )
                            if predictive_frontier is not None
                            else None
                        )
                        guarded_skill_library = None
                        guarded_skill_traces = ()
                        continual_skill_memory = None
                        guarded_skill_compiler = {
                            "status": "no_history_trajectories",
                        }
                        continual_skill_state = {
                            "status": "no_compiled_skill_library",
                        }
                        consumable_skill_revisions = frozenset()
                        transported_skill_programs = ()
                        if control_history_trajectories:
                            try:
                                from ztare.worldmodel.mechanism_effects import (
                                    compile_history_guarded_skill_library,
                                    guarded_skill_traces_from_history_evidence,
                                )

                                guarded_skill_traces = (
                                    guarded_skill_traces_from_history_evidence(
                                        tuple(control_history_trajectories),
                                        projection=factored_projection,
                                        history_lift=(
                                            mechanism_problem.history_lift
                                        ),
                                    )
                                )
                                guarded_skill_library = (
                                    compile_history_guarded_skill_library(
                                        tuple(control_history_trajectories),
                                        projection=factored_projection,
                                        history_lift=(
                                            mechanism_problem.history_lift
                                        ),
                                        guarded_traces=guarded_skill_traces,
                                        min_word_length=2,
                                        max_word_length=8,
                                        min_variant_support=2,
                                    )
                                )
                                guarded_skill_compiler = {
                                    "status": "compiled",
                                    "receipt": (
                                        guarded_skill_library.to_receipt()
                                    ),
                                }
                            except Exception as skill_error:  # noqa: BLE001
                                guarded_skill_compiler = {
                                    "status": "primitive_fallback",
                                    "error_type": type(skill_error).__name__,
                                }
                        if guarded_skill_library is not None:
                            if receipts_dir is None:
                                continual_skill_state = {
                                    "status": "persistence_path_unavailable",
                                }
                            else:
                                try:
                                    from ztare.common.continual_skill_memory import (
                                        load_continual_skill_memory,
                                        merge_guarded_skill_library,
                                        consumable_skill_revision_sha256s,
                                        rehydrate_validated_skill_programs,
                                        record_library_quotient_transport,
                                        save_continual_skill_memory,
                                    )
                                    from ztare.common.equivariance import (
                                        stable_sha256,
                                    )

                                    memory_path = (
                                        Path(receipts_dir)
                                        / "continual_skill_memory.json"
                                    )
                                    operation_namespace = (
                                        f"{type(adapter).__module__}."
                                        f"{type(adapter).__qualname__}:"
                                        f"arity={int(adapter.action_arity)}"
                                    )
                                    skill_context = (
                                        "compiled_fiber_skill_context",
                                        mechanism_problem.projection_sha256,
                                        str(carrier_execution_sha256 or ""),
                                    )
                                    prior_memory = (
                                        load_continual_skill_memory(memory_path)
                                    )
                                    updated_memory = (
                                        merge_guarded_skill_library(
                                            prior_memory,
                                            guarded_skill_library,
                                            operation_namespace=(
                                                operation_namespace
                                            ),
                                            context_key=skill_context,
                                        )
                                    )
                                    continual_skill_memory = updated_memory
                                    (
                                        updated_memory,
                                        quotient_transport,
                                    ) = record_library_quotient_transport(
                                        updated_memory,
                                        guarded_skill_library,
                                        operation_namespace=(
                                            operation_namespace
                                        ),
                                        context_key=skill_context,
                                        predictive_quotient=(
                                            predictive_quotient
                                        ),
                                    )
                                    continual_skill_memory = updated_memory
                                    transported_skill_programs = (
                                        rehydrate_validated_skill_programs(
                                            updated_memory,
                                            guarded_skill_traces,
                                            operation_namespace=(
                                                operation_namespace
                                            ),
                                            context_key=skill_context,
                                        )
                                    )
                                    (
                                        consumable_skill_revisions,
                                        consumption_receipt,
                                    ) = consumable_skill_revision_sha256s(
                                        updated_memory,
                                        guarded_skill_library,
                                        operation_namespace=(
                                            operation_namespace
                                        ),
                                        context_key=skill_context,
                                        additional_programs=(
                                            transported_skill_programs
                                        ),
                                    )
                                    save_continual_skill_memory(
                                        memory_path,
                                        updated_memory,
                                    )
                                    continual_skill_runtime = {
                                        "memory_path": memory_path,
                                        "context_sha256": stable_sha256(
                                            skill_context
                                        ),
                                        "family_by_revision": {
                                            program.skill_sha256: (
                                                program.structural_sha256(
                                                    operation_namespace
                                                )
                                            )
                                            for program in (
                                                *guarded_skill_library.programs,
                                                *transported_skill_programs,
                                            )
                                        },
                                        "authority_by_revision": {
                                            program.skill_sha256: (
                                                program.admission_authority
                                            )
                                            for program in (
                                                *guarded_skill_library.programs,
                                                *transported_skill_programs,
                                            )
                                        },
                                    }
                                    continual_skill_state = {
                                        "status": "persisted_and_consumable",
                                        "memory_ref": (
                                            "continual_skill_memory.json"
                                        ),
                                        "prior_memory_sha256": (
                                            prior_memory.memory_sha256
                                        ),
                                        "memory": (
                                            updated_memory.to_receipt()
                                        ),
                                        "quotient_transport": (
                                            quotient_transport
                                        ),
                                        "consumption": (
                                            consumption_receipt
                                        ),
                                        "rehydrated_transport_count": len(
                                            transported_skill_programs
                                        ),
                                    }
                                except Exception as memory_error:  # noqa: BLE001
                                    continual_skill_memory = None
                                    continual_skill_state = {
                                        "status": "persistence_fallback",
                                        "error_type": (
                                            type(memory_error).__name__
                                        ),
                                    }

                        decision_pricing_skill_invocations = frozenset()
                        effect_option_family_by_invocation = {}
                        effect_option_variant_by_invocation = {}
                        effect_option_families_by_source = {}
                        effect_option_namespace = ""
                        motor_option_programs = ()
                        effect_option_families = ()
                        effect_option_task_judgments = ()
                        effect_option_state = {
                            "status": "option_surface_unavailable",
                            "decision_pricing_authority": (
                                "matched_effect_option_outcome_credit_only"
                            ),
                            "decision_pricing_invocation_count": 0,
                        }
                        if (
                            guarded_skill_library is not None
                            and boundary_reachability_fibers is not None
                        ):
                            try:
                                from ztare.common.boundary_reachability import (
                                    compile_effect_option_families,
                                    reindex_option_programs,
                                )
                                from ztare.common.continual_skill_memory import (
                                    judge_effect_option_task_credit,
                                )
                                from ztare.worldmodel.mechanism_effects import (
                                    guarded_skill_option_specs,
                                )

                                operation_namespace = (
                                    f"{type(adapter).__module__}."
                                    f"{type(adapter).__qualname__}:"
                                    f"arity={int(adapter.action_arity)}"
                                )
                                option_specs = guarded_skill_option_specs(
                                    guarded_skill_library,
                                    operation_namespace=operation_namespace,
                                    additional_programs=(
                                        transported_skill_programs
                                    ),
                                )
                                motor_option_programs = (
                                    reindex_option_programs(
                                        option_specs,
                                        fibers=(
                                            boundary_reachability_fibers
                                        ),
                                    )
                                )
                                effect_namespace = (
                                    "compiled-fiber-effects-v1:"
                                    + mechanism_problem.projection_sha256
                                )
                                effect_option_namespace = effect_namespace
                                effect_option_families = (
                                    compile_effect_option_families(
                                        motor_option_programs,
                                        effect_namespace=effect_namespace,
                                    )
                                )
                                option_candidates_by_invocation = {}
                                family_candidates_by_source = {}
                                for family in effect_option_families:
                                    for context_variant in (
                                        family.context_variants
                                    ):
                                        for implementation in (
                                            context_variant.implementations
                                        ):
                                            for source_sha, _target_sha in (
                                                implementation
                                                .source_target_sha256_pairs
                                            ):
                                                invocation = (
                                                    implementation
                                                    .source_revision_sha256,
                                                    source_sha,
                                                )
                                                (
                                                    option_candidates_by_invocation
                                                    .setdefault(
                                                        invocation,
                                                        set(),
                                                    )
                                                    .add((
                                                        family.family_sha256,
                                                        context_variant
                                                        .variant_sha256,
                                                    ))
                                                )
                                                (
                                                    family_candidates_by_source
                                                    .setdefault(
                                                        source_sha,
                                                        set(),
                                                    )
                                                    .add(
                                                        family.family_sha256
                                                    )
                                                )
                                option_identity_by_invocation = {
                                    invocation: next(iter(option_ids))
                                    for invocation, option_ids in (
                                        option_candidates_by_invocation.items()
                                    )
                                    if len(option_ids) == 1
                                }
                                effect_option_family_by_invocation = {
                                    invocation: option_identity[0]
                                    for invocation, option_identity in (
                                        option_identity_by_invocation.items()
                                    )
                                }
                                effect_option_variant_by_invocation = {
                                    invocation: option_identity[1]
                                    for invocation, option_identity in (
                                        option_identity_by_invocation.items()
                                    )
                                }
                                effect_option_families_by_source = {
                                    source_sha: tuple(sorted(family_ids))
                                    for source_sha, family_ids in (
                                        family_candidates_by_source.items()
                                    )
                                }
                                judgments = []
                                credited_invocations = set()
                                for family in effect_option_families:
                                    source_families = tuple(sorted({
                                        implementation.source_family_sha256
                                        for implementation
                                        in family.implementations
                                        if (
                                            implementation
                                            .source_family_sha256
                                        )
                                    }))
                                    if not control_task_contract_sha256:
                                        judgment_receipt = {
                                            "schema": (
                                                "ztare-effect-option-task-"
                                                "judgment-v1"
                                            ),
                                            "effect_option_family_sha256": (
                                                family.family_sha256
                                            ),
                                            "task_contract_sha256": "",
                                            "status": (
                                                "task_contract_unavailable"
                                            ),
                                            "source_family_sha256s": list(
                                                source_families
                                            ),
                                            "enable_support": 0,
                                            "hazard_support": 0,
                                            "evidence_refs": [],
                                            "authority": (
                                                "matched_external_outcome_"
                                                "contrasts_only"
                                            ),
                                        }
                                    elif continual_skill_memory is None:
                                        judgment_receipt = {
                                            "schema": (
                                                "ztare-effect-option-task-"
                                                "judgment-v1"
                                            ),
                                            "effect_option_family_sha256": (
                                                family.family_sha256
                                            ),
                                            "task_contract_sha256": (
                                                control_task_contract_sha256
                                            ),
                                            "status": "memory_unavailable",
                                            "source_family_sha256s": list(
                                                source_families
                                            ),
                                            "enable_support": 0,
                                            "hazard_support": 0,
                                            "evidence_refs": [],
                                            "authority": (
                                                "matched_external_outcome_"
                                                "contrasts_only"
                                            ),
                                        }
                                    else:
                                        judgment = (
                                            judge_effect_option_task_credit(
                                                continual_skill_memory,
                                                effect_option_family_sha256=(
                                                    family.family_sha256
                                                ),
                                                task_contract_sha256=(
                                                    control_task_contract_sha256
                                                ),
                                                source_family_sha256s=(
                                                    source_families
                                                ),
                                            )
                                        )
                                        judgment_receipt = (
                                            judgment.to_receipt()
                                        )
                                        if judgment.status == "task_credited":
                                            for implementation in (
                                                family.implementations
                                            ):
                                                if (
                                                    implementation
                                                    .source_revision_sha256
                                                    not in
                                                    consumable_skill_revisions
                                                ):
                                                    continue
                                                for source_sha, _target_sha in (
                                                    implementation
                                                    .source_target_sha256_pairs
                                                ):
                                                    credited_invocations.add((
                                                        implementation
                                                        .source_revision_sha256,
                                                        source_sha,
                                                    ))
                                    judgments.append(judgment_receipt)
                                effect_option_task_judgments = tuple(
                                    judgments
                                )
                                decision_pricing_skill_invocations = (
                                    frozenset(credited_invocations)
                                )
                                effect_option_state = {
                                    "status": "compiled",
                                    "effect_namespace": effect_namespace,
                                    "motor_option_program_count": len(
                                        motor_option_programs
                                    ),
                                    "effect_option_family_count": len(
                                        effect_option_families
                                    ),
                                    "effect_option_context_variant_count": sum(
                                        len(family.context_variants)
                                        for family in effect_option_families
                                    ),
                                    "task_credited_family_count": sum(
                                        row["status"] == "task_credited"
                                        for row in
                                        effect_option_task_judgments
                                    ),
                                    "decision_pricing_authority": (
                                        "matched_effect_option_outcome_"
                                        "credit_only"
                                    ),
                                    "decision_pricing_invocation_count": len(
                                        decision_pricing_skill_invocations
                                    ),
                                }
                            except Exception as option_error:  # noqa: BLE001
                                decision_pricing_skill_invocations = (
                                    frozenset()
                                )
                                effect_option_family_by_invocation = {}
                                effect_option_variant_by_invocation = {}
                                effect_option_families_by_source = {}
                                effect_option_namespace = ""
                                effect_option_state = {
                                    "status": "primitive_pricing_fallback",
                                    "error_type": type(
                                        option_error
                                    ).__name__,
                                    "decision_pricing_authority": (
                                        "matched_effect_option_outcome_"
                                        "credit_only"
                                    ),
                                    "decision_pricing_invocation_count": 0,
                                }

                        from ztare.common.guarded_experiment_protocol import (
                            ProtocolYieldWeights,
                        )
                        from ztare.worldmodel.mechanism_protocols import (
                            MechanismAcquisitionFrontiers,
                            select_acquisition_protocols,
                        )
                        from ztare.worldmodel.policy import (
                            W_COMPRESSION,
                            W_COVERAGE,
                            W_EIG,
                        )

                        decision_namespace = (
                            "ztare-acquisition-protocol-choice-v1"
                        )
                        decision_choice_context_sha256 = _stable_sha256({
                            "schema": (
                                "ztare-controller-choice-context-v1"
                            ),
                            "decision_namespace": decision_namespace,
                            "task_contract_sha256": (
                                control_task_contract_sha256
                            ),
                            "observed_start_key_sha256": (
                                _stable_sha256(observed_start_key)
                            ),
                        })
                        decision_continuation_context_sha256 = (
                            _stable_sha256({
                                "schema": (
                                    "ztare-controller-continuation-context-v1"
                                ),
                                "controller": (
                                    "guarded-protocol-information-yield-v1"
                                ),
                                "projection_sha256": (
                                    mechanism_problem.projection_sha256
                                ),
                                "operation_namespace": (
                                    control_operation_namespace
                                ),
                            })
                        )
                        decision_option_judgments = []

                        def resolve_protocol_decision_calibration(
                            protocol_ids,
                        ):
                            if (
                                continual_skill_memory is None
                                or not control_task_contract_sha256
                            ):
                                return {}, {}
                            from ztare.common.continual_skill_memory import (
                                decision_option_family_sha256,
                                judge_decision_option_task_credit,
                            )

                            family_by_protocol = {
                                protocol_id: (
                                    decision_option_family_sha256(
                                        decision_namespace,
                                        protocol_id,
                                    )
                                )
                                for protocol_id in protocol_ids
                            }
                            available_families = tuple(sorted(
                                family_by_protocol.values()
                            ))
                            task_values = {}
                            contrast_priorities = {}
                            for protocol_id in protocol_ids:
                                judgment = (
                                    judge_decision_option_task_credit(
                                        continual_skill_memory,
                                        decision_namespace=(
                                            decision_namespace
                                        ),
                                        option_family_sha256=(
                                            family_by_protocol[
                                                protocol_id
                                            ]
                                        ),
                                        task_contract_sha256=(
                                            control_task_contract_sha256
                                        ),
                                        choice_context_sha256=(
                                            decision_choice_context_sha256
                                        ),
                                        continuation_context_sha256=(
                                            decision_continuation_context_sha256
                                        ),
                                        available_option_family_sha256s=(
                                            available_families
                                        ),
                                    )
                                )
                                decision_option_judgments.append(
                                    judgment.to_receipt()
                                )
                                task_values[protocol_id] = (
                                    judgment.preference
                                )
                                contrast_priorities[protocol_id] = (
                                    judgment.contrast_priority
                                )
                            return task_values, contrast_priorities

                        protocol_portfolio = select_acquisition_protocols(
                            mechanism_problem.action_system,
                            predictive_compatibility,
                            start_key=observed_start_key,
                            frontiers=MechanismAcquisitionFrontiers(
                                observed=observed_frontier,
                                boundary=boundary_reachability_frontier,
                                predictive_quotient=predictive_frontier,
                                predictive_support=(
                                    predictive_support_frontier
                                ),
                                predictive_quotient_is_orbit_completion=(
                                    orbit_completion is not None
                                ),
                            ),
                            weights=ProtocolYieldWeights(
                                identification=W_EIG,
                                compression=W_COMPRESSION,
                                novelty=W_COVERAGE,
                            ),
                            skill_library=guarded_skill_library,
                            allowed_skill_sha256s=(
                                consumable_skill_revisions
                            ),
                            additional_skill_programs=(
                                transported_skill_programs
                            ),
                            max_primitive_execution_units=max(
                                0,
                                int(max_steps - len(trace)),
                            ),
                            pricing_allowed_skill_invocations=(
                                decision_pricing_skill_invocations
                            ),
                            decision_calibration_resolver=(
                                resolve_protocol_decision_calibration
                            ),
                        )
                        protocol_lowerings = (
                            protocol_portfolio.lowerings
                        )
                        protocol_selection = (
                            protocol_portfolio.selection
                        )
                        selected_policy = (
                            protocol_selection.selected_protocol_id
                        )
                        selected_frontier = (
                            protocol_portfolio.selected_frontier
                            or observed_frontier
                        )
                        task_decision_choice = None
                        if (
                            protocol_selection.selected is not None
                            and control_task_contract_sha256
                        ):
                            from ztare.common.continual_skill_memory import (
                                decision_option_family_sha256,
                            )

                            family_by_protocol = {
                                protocol_id: (
                                    decision_option_family_sha256(
                                        decision_namespace,
                                        protocol_id,
                                    )
                                )
                                for protocol_id in (
                                    protocol_selection
                                    .canonical_protocol_ids
                                )
                            }
                            selected_price = protocol_selection.selected
                            selected_family = family_by_protocol[
                                selected_price.protocol_id
                            ]
                            task_decision_choice = {
                                "schema": (
                                    "ztare-task-decision-choice-window-v1"
                                ),
                                "decision_namespace": decision_namespace,
                                "choice_context_sha256": (
                                    decision_choice_context_sha256
                                ),
                                "continuation_context_sha256": (
                                    decision_continuation_context_sha256
                                ),
                                "chosen_option_family_sha256": (
                                    selected_family
                                ),
                                "chosen_option_variant_sha256": (
                                    _stable_sha256({
                                        "schema": (
                                            "ztare-acquisition-protocol-"
                                            "variant-v1"
                                        ),
                                        "protocol_id": (
                                            selected_price.protocol_id
                                        ),
                                        "committee_sha256": (
                                            selected_price
                                            .committee_sha256
                                        ),
                                        "partition_sha256": (
                                            selected_price
                                            .partition_sha256
                                        ),
                                        "protocol": (
                                            selected_price.protocol
                                            .identity_receipt()
                                        ),
                                    })
                                ),
                                "available_option_family_sha256s": (
                                    sorted(
                                        family_by_protocol.values()
                                    )
                                ),
                                "chosen_protocol_id": (
                                    selected_price.protocol_id
                                ),
                                "available_protocol_ids": list(
                                    protocol_selection
                                    .canonical_protocol_ids
                                ),
                            }
                        protocol_diagnostics = {
                            "factor_novelty_predecessor": (
                                factor_novelty_outcome
                            ),
                            "observed_partial_action_frontier": (
                                observed_frontier.to_receipt()
                            ),
                            "predictive_quotient": (
                                predictive_quotient.to_receipt(
                                    option_cap=10,
                                    class_cap=0,
                                )
                            ),
                            "predictive_quotient_frontier": (
                                predictive_frontier.to_receipt()
                                if predictive_frontier is not None
                                else None
                            ),
                            "predictive_compatibility": (
                                predictive_compatibility.to_receipt(
                                    incompatibility_cap=20,
                                    support_gap_cap=20,
                                )
                            ),
                            "predictive_support_frontier": (
                                predictive_support_frontier.to_receipt()
                            ),
                            "boundary_reachability_fibers": (
                                boundary_reachability_fibers.to_receipt(
                                    edge_cap=0,
                                )
                                if boundary_reachability_fibers is not None
                                else None
                            ),
                            "boundary_reachability_frontier": (
                                boundary_reachability_frontier.to_receipt()
                                if boundary_reachability_frontier is not None
                                else None
                            ),
                            "orbit_completion": (
                                orbit_completion.to_receipt()
                                if orbit_completion is not None
                                else None
                            ),
                            "history_lift": (
                                mechanism_problem.history_lift.to_receipt()
                                if mechanism_problem.history_lift is not None
                                else None
                            ),
                            "guarded_skill_compiler": (
                                guarded_skill_compiler
                            ),
                            "continual_skill_state": continual_skill_state,
                            "effect_option_state": effect_option_state,
                            "motor_option_programs": [
                                {
                                    "option_sha256": option.option_sha256,
                                    "source_family_sha256": (
                                        option.source_family_sha256
                                    ),
                                    "source_revision_sha256": (
                                        option.source_revision_sha256
                                    ),
                                    "status": option.status,
                                    "requested_initiation_count": (
                                        option.requested_initiation_count
                                    ),
                                    "resolved_initiation_count": (
                                        option.resolved_initiation_count
                                    ),
                                    "effect_variant_count": len(
                                        option.variants
                                    ),
                                    "failure_kinds": list(
                                        option.failure_kinds
                                    ),
                                }
                                for option in motor_option_programs
                            ],
                            "effect_option_families": [
                                {
                                    "family_sha256": family.family_sha256,
                                    "effect_namespace": (
                                        family.effect_namespace
                                    ),
                                    "effect_trace_sha256": (
                                        _stable_sha256(
                                            family.effect_trace
                                        )
                                    ),
                                    "context_variant_count": len(
                                        family.context_variants
                                    ),
                                    "terminal_context_sha256s": sorted({
                                        _stable_sha256(
                                            variant.terminal_context
                                        )
                                        for variant in (
                                            family.context_variants
                                        )
                                    }),
                                    "implementation_count": len(
                                        family.implementations
                                    ),
                                    "initiation_count": len({
                                        source_sha256
                                        for implementation in (
                                            family.implementations
                                        )
                                        for source_sha256, _target_sha256
                                        in (
                                            implementation
                                            .source_target_sha256_pairs
                                        )
                                    }),
                                    "source_revision_sha256s": sorted({
                                        implementation
                                        .source_revision_sha256
                                        for implementation in (
                                            family.implementations
                                        )
                                    }),
                                }
                                for family in effect_option_families
                            ],
                            "effect_option_task_judgments": list(
                                effect_option_task_judgments
                            ),
                            "decision_option_task_judgments": list(
                                decision_option_judgments
                            ),
                            "task_decision_choice": (
                                task_decision_choice
                            ),
                            "guarded_protocol_lowerings": [
                                lowering.to_receipt()
                                for lowering in protocol_lowerings
                            ],
                            "guarded_protocol_selection": (
                                protocol_selection.to_receipt()
                            ),
                        }
                        if protocol_selection.selected is not None:
                            if (
                                tuple(selected_frontier.actions)
                                != protocol_portfolio.selected_operations
                            ):
                                return PursuitReceipt(
                                    status="apparatus_obstructed",
                                    steps_executed=len(trace),
                                    levels_gained=(
                                        _levels(adapter) - baseline
                                    ),
                                    detail=(
                                        "selected protocol identity does not "
                                        "match the frontier operation word"
                                    ),
                                    replans=replans,
                                    trace=trace,
                                    saturated=saturated,
                                    observed_transitions=observed,
                                    planning_outcome={
                                        "policy": (
                                            "guarded_protocol_information_yield"
                                        ),
                                        "status": (
                                            "selected_protocol_identity_mismatch"
                                        ),
                                        **protocol_diagnostics,
                                    },
                                )
                            plan = Plan(
                                actions=list(selected_frontier.actions),
                                reason=(
                                    "guarded protocol information yield: "
                                    f"{selected_policy} density="
                                    f"{protocol_selection.selected.yield_density:.8f}"
                                ),
                            )
                            selected_lowering = next(
                                (
                                    lowering
                                    for lowering in protocol_lowerings
                                    if (
                                        lowering.candidate.protocol.protocol_id
                                        == selected_policy
                                    )
                                ),
                                None,
                            )
                            control_plan_receipt = (
                                selected_lowering.control_plan_receipt
                                if selected_lowering is not None
                                else None
                            )
                            cursor_step = int(adapter.t)
                            cursor_operation_index = 0
                            if (
                                isinstance(control_plan_receipt, dict)
                                and continual_skill_runtime
                            ):
                                family_by_revision = (
                                    continual_skill_runtime[
                                        "family_by_revision"
                                    ]
                                )
                                for token in (
                                    control_plan_receipt.get("tokens") or ()
                                ):
                                    operation_count = int(
                                        token.get("operation_count") or 0
                                    )
                                    revision_sha = str(
                                        token.get("skill_sha256") or ""
                                    )
                                    if (
                                        token.get("kind") == "skill"
                                        and revision_sha
                                        in family_by_revision
                                    ):
                                        skill_window = {
                                            "start_step": cursor_step,
                                            "end_step": (
                                                cursor_step
                                                + operation_count
                                            ),
                                            "revision_sha256": (
                                                revision_sha
                                            ),
                                            "family_sha256": (
                                                family_by_revision[
                                                    revision_sha
                                                ]
                                            ),
                                            "context_sha256": (
                                                continual_skill_runtime[
                                                    "context_sha256"
                                                ]
                                            ),
                                            "admission_authority": (
                                                continual_skill_runtime[
                                                    "authority_by_revision"
                                                ][revision_sha]
                                            ),
                                        }
                                        source_sha256 = (
                                            selected_lowering
                                            .preparation_key_sha256s[
                                                cursor_operation_index
                                            ]
                                        )
                                        target_sha256 = (
                                            selected_lowering
                                            .preparation_key_sha256s[
                                                cursor_operation_index
                                                + operation_count
                                            ]
                                        )
                                        effect_family_sha256 = (
                                            effect_option_family_by_invocation
                                            .get((
                                                revision_sha,
                                                source_sha256,
                                            ))
                                        )
                                        if effect_family_sha256:
                                            skill_window[
                                                "effect_option_family_sha256"
                                            ] = effect_family_sha256
                                            skill_window[
                                                "effect_option_variant_sha256"
                                            ] = (
                                                effect_option_variant_by_invocation[
                                                    (
                                                        revision_sha,
                                                        source_sha256,
                                                    )
                                                ]
                                            )
                                            skill_window[
                                                "choice_source_sha256"
                                            ] = source_sha256
                                            skill_window[
                                                "choice_target_sha256"
                                            ] = target_sha256
                                            skill_window[
                                                "available_effect_option_"
                                                "family_sha256s"
                                            ] = list(
                                                effect_option_families_by_source
                                                .get(
                                                    source_sha256,
                                                    (),
                                                )
                                            )
                                            skill_window[
                                                "choice_context_sha256"
                                            ] = _stable_sha256({
                                                "schema": (
                                                    "ztare-effect-option-"
                                                    "choice-context-v1"
                                                ),
                                                "effect_namespace": (
                                                    effect_option_namespace
                                                ),
                                                "source_sha256": (
                                                    source_sha256
                                                ),
                                            })
                                            skill_window[
                                                "continuation_context_sha256"
                                            ] = _stable_sha256({
                                                "schema": (
                                                    "ztare-effect-option-"
                                                    "continuation-context-v1"
                                                ),
                                                "task_contract_sha256": (
                                                    control_task_contract_sha256
                                                ),
                                                "effect_namespace": (
                                                    effect_option_namespace
                                                ),
                                                "operation_namespace": (
                                                    control_operation_namespace
                                                ),
                                                "controller": (
                                                    "guarded-protocol-"
                                                    "information-yield-v1"
                                                ),
                                            })
                                        active_skill_windows.append(
                                            skill_window
                                        )
                                        planned_skill_windows.append(
                                            skill_window
                                        )
                                    cursor_step += operation_count
                                    cursor_operation_index += (
                                        operation_count
                                    )
                            (
                                planned_windows,
                                completed_windows,
                                partial_windows,
                            ) = _skill_window_receipts()
                            protocol_diagnostics[
                                "continual_skill_planned_windows"
                            ] = planned_windows
                            protocol_diagnostics[
                                "continual_skill_execution_windows"
                            ] = completed_windows
                            protocol_diagnostics[
                                "continual_skill_partial_execution_windows"
                            ] = partial_windows
                            last_planning_outcome = {
                                "policy": (
                                    "guarded_protocol_information_yield"
                                ),
                                "selected_protocol_policy": (
                                    selected_policy
                                ),
                                "status": "protocol_selected",
                                "states_generated": (
                                    selected_frontier.reachable_nodes
                                ),
                                "states_expanded": (
                                    selected_frontier.reachable_nodes
                                ),
                                "problem_id": mechanism_problem.problem_id,
                                "exhaustive": False,
                                "consumer_action": (
                                    "execute_selected_guarded_protocol"
                                ),
                                **protocol_diagnostics,
                            }
                            planned_acquisition_transaction = True
                            _append_acquisition_routing(
                                receipts_dir,
                                visited_store=visited_store,
                                plan=plan,
                                policy=(
                                    "guarded_protocol_information_yield"
                                ),
                                search_status=last_planning_outcome[
                                    "status"
                                ],
                                states_enumerated=(
                                    selected_frontier.reachable_nodes
                                ),
                                exhaustive=False,
                            )
                        elif (
                            protocol_selection.status
                            == "no_affordable_protocol"
                        ):
                            last_planning_outcome = {
                                "policy": (
                                    "guarded_protocol_information_yield"
                                ),
                                "status": "no_affordable_protocol",
                                "states_generated": (
                                    selected_frontier.reachable_nodes
                                ),
                                "states_expanded": (
                                    selected_frontier.reachable_nodes
                                ),
                                "problem_id": mechanism_problem.problem_id,
                                "exhaustive": False,
                                "consumer_action": (
                                    "return_for_intervention_budget"
                                ),
                                **protocol_diagnostics,
                            }
                            return PursuitReceipt(
                                status=(
                                    "mechanism_protocol_budget_exhausted"
                                ),
                                steps_executed=len(trace),
                                levels_gained=(
                                    _levels(adapter) - baseline
                                ),
                                detail=(
                                    "no admitted mechanism protocol fits the "
                                    "remaining primitive intervention budget"
                                ),
                                replans=replans,
                                trace=trace,
                                saturated=False,
                                observed_transitions=observed,
                                planning_outcome=_planning_receipt(),
                            )
                        elif mechanism_problem.history_suffix_length:
                            last_planning_outcome = {
                                "policy": (
                                    "guarded_protocol_information_yield"
                                ),
                                "status": protocol_selection.status,
                                "states_generated": (
                                    selected_frontier.reachable_nodes
                                ),
                                "states_expanded": (
                                    selected_frontier.reachable_nodes
                                ),
                                "problem_id": mechanism_problem.problem_id,
                                "exhaustive": True,
                                "consumer_action": (
                                    "return_for_protocol_refinement"
                                ),
                                **protocol_diagnostics,
                            }
                        else:
                            factored_result, last_planning_outcome = (
                                _factored_attempt(
                                    factored_problem,
                                    factored_policy,
                                )
                            )
                            last_planning_outcome[
                                "factor_novelty_predecessor"
                            ] = factor_novelty_outcome
                            last_planning_outcome[
                                "observed_partial_action_frontier"
                            ] = observed_frontier.to_receipt()
                    if (
                        factored_result.status == "search_budget_exhausted"
                        and goal_target_kind == "hypothesis_version_space"
                    ):
                        acquisition_policy = (
                            "incremental_novelty_after_bounded_capitulation"
                        )
                        last_planning_outcome["consumer_action"] = (
                            "switch_to_information_yield_acquisition"
                        )
                    if (
                        factored_result.status in {"edge_found", "state_found"}
                        and factored_result.actions
                    ):
                        plan = Plan(
                            actions=list(factored_result.actions),
                            reason=(
                                f"{factored_policy}: "
                                f"{factored_result.generated} generated / "
                                f"{factored_result.expanded} expanded"
                            ),
                        )
                        planned_undefined_terminal = (
                            factored_policy
                            == "factored_partial_operation_completion"
                        )
                        planned_acquisition_transaction = factored_policy in {
                            "factored_goal_experiment",
                            "factored_goal_information_acquisition",
                            "factored_mechanism_acquisition",
                            "factored_operation_discrimination",
                        }
                        if (
                            (
                                factored_result.status == "state_found"
                                and factored_policy != "factored_goal_search"
                            )
                            or factored_policy == "factored_operation_discrimination"
                        ):
                            _append_acquisition_routing(
                                receipts_dir,
                                visited_store=visited_store,
                                plan=plan,
                                policy=factored_policy,
                                search_status=(
                                    "distinct_operation_trigger_context"
                                    if factored_policy
                                    == "factored_operation_discrimination"
                                    else "goal_hypothesis_experiment_edge"
                                    if factored_policy
                                    == "factored_goal_experiment"
                                    else "novel_goal_observation_identity"
                                    if factored_policy
                                    == "factored_goal_information_acquisition"
                                    else "exceptional_mechanism_transport"
                                    if factored_policy
                                    == "factored_mechanism_acquisition"
                                    else "novel_operation_affordance_identity"
                                ),
                                states_enumerated=factored_result.generated,
                            )
                    elif (
                        factored_result.status == "search_budget_exhausted"
                        and goal_target_kind == "hypothesis_version_space"
                        and factored_result.continuation_actions
                    ):
                        plan = Plan(
                            actions=list(factored_result.continuation_actions),
                            reason=(
                                f"{factored_policy}: bounded informative frontier "
                                f"after {factored_result.generated} generated states"
                            ),
                        )
                        last_planning_outcome["consumer_action"] = (
                            "execute_bounded_informative_continuation"
                        )
                        planned_acquisition_transaction = True
                        _append_acquisition_routing(
                            receipts_dir,
                            visited_store=visited_store,
                            plan=plan,
                            policy=factored_policy,
                            search_status="bounded_informative_continuation",
                            states_enumerated=factored_result.generated,
                            exhaustive=False,
                        )
                    elif (
                        factored_policy == "factored_mechanism_acquisition"
                        and plan is None
                        and factored_result.status == "search_budget_exhausted"
                        and factored_result.continuation_actions
                    ):
                        plan = Plan(
                            actions=list(factored_result.continuation_actions),
                            reason=(
                                "factored_mechanism_acquisition: bounded "
                                "exceptional-effect frontier after "
                                f"{factored_result.generated} generated states"
                            ),
                        )
                        last_planning_outcome["consumer_action"] = (
                            "execute_bounded_mechanism_continuation"
                        )
                        planned_acquisition_transaction = True
                        _append_acquisition_routing(
                            receipts_dir,
                            visited_store=visited_store,
                            plan=plan,
                            policy=factored_policy,
                            search_status=(
                                "bounded_exceptional_mechanism_continuation"
                            ),
                            states_enumerated=factored_result.generated,
                            exhaustive=False,
                        )
                    factored_planning_outcome = dict(last_planning_outcome)
                    if factored_result.status == "projection_noncommuting":
                        return PursuitReceipt(
                            status="projection_noncommuting",
                            steps_executed=len(trace),
                            levels_gained=_levels(adapter) - baseline,
                            detail=(
                                "consumer projection merged states with different "
                                "intervention consequences; refine that projection "
                                "before allocating another live intervention"
                            ),
                            replans=replans,
                            trace=trace,
                            saturated=saturated,
                            observed_transitions=observed,
                            planning_outcome=_planning_receipt(),
                        )
                    if (
                        plan is None
                        and factored_policy
                        == "factored_mechanism_acquisition"
                    ):
                        return PursuitReceipt(
                            status="mechanism_frontier_exhausted",
                            steps_executed=len(trace),
                            levels_gained=_levels(adapter) - baseline,
                            detail=(
                                "the feasibility-aware partial-action consumer "
                                "found no admissible mechanism experiment; a "
                                "lower-fidelity fallback is not authorized"
                            ),
                            replans=replans,
                            trace=trace,
                            saturated=(
                                factored_result.status
                                == "projected_frontier_exhausted"
                            ),
                            observed_transitions=observed,
                            planning_outcome=_planning_receipt(),
                        )
            # With no admitted task identity, acquisition lives on the
            # consumer's state-action support graph. A reachable unsupported
            # operation is a stricter information target than a merely unseen
            # state: its final intervention directly fills or refutes one
            # support edge. State novelty remains the fallback when this graph
            # has no reachable gap.
            if (
                plan is None
                and goal_fn is None
                and active_goal_edge_fn is None
                and acquisition_obligation is None
                and _witnessed_pairs is not None
            ):
                _t0 = time.perf_counter()
                plan = plan_witness_gap(
                    planning_model,
                    state,
                    adapter.action_arity,
                    _witnessed_pairs,
                    start_step=adapter.t,
                    max_depth=plan_depth,
                    abstract_fn=abstract_fn,
                    support_fn=_support_alpha,
                )
                _t_plan += time.perf_counter() - _t0
                if plan is not None and plan.actions:
                    last_planning_outcome = _bounded_plan_outcome(
                        plan,
                        policy="witness_gap_acquisition",
                        found_status="unsupported_operation_pair",
                    )
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=plan,
                        policy="witness_gap_acquisition",
                        search_status="unsupported_operation_pair",
                    )
            bounded_edge_fn = active_goal_edge_fn
            bounded_goal_fn = goal_fn
            bounded_edge_policy = "terminal_edge"
            if bounded_edge_fn is None and acquisition_obligation is not None:
                def bounded_edge_fn(
                    source: Any,
                    intervention: Any,
                    time_value: Any,
                ) -> bool:
                    successor = predict(source, intervention, time_value)
                    return successor is not None and acquisition_obligation.accepts_edge(
                        source,
                        intervention,
                        time_value,
                        successor,
                    )

                bounded_edge_fn.goal_source_states = (
                    acquisition_obligation.goal_source_states
                )
                bounded_edge_fn.time_aware = True
                bounded_goal_fn = None
                bounded_edge_policy = "raw_operation_discrimination"
            goal_edge_has_witness_sources = bool(
                _goal_sources_at(bounded_edge_fn, adapter.t)
            )
            # An adapter-attested edge carries finite source witnesses. Reorder
            # the bounded search toward those witnesses before paying for an
            # exhaustive sweep; this is allocator state, never prompt content.
            if plan is None and goal_edge_has_witness_sources:
                _t0 = time.perf_counter()
                plan = plan_to_goal(
                    planning_model,
                    state,
                    adapter.action_arity,
                    bounded_goal_fn,
                    goal_edge_fn=bounded_edge_fn,
                    start_step=adapter.t,
                    max_depth=plan_depth * 6,
                    max_nodes=_SWEEP_MAX_STATES,
                    abstract_fn=abstract_fn,
                    _state_interner=_pg_interner,
                )
                _t_plan += time.perf_counter() - _t0
                last_planning_outcome = _bounded_plan_outcome(
                    plan,
                    policy=bounded_edge_policy,
                    found_status="edge_found",
                    missing_status="witness_source_unreachable_within_bound",
                )
                if plan is None or not plan.actions:
                    plan = None
                elif bounded_edge_policy == "raw_operation_discrimination":
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=plan,
                        policy=bounded_edge_policy,
                        search_status="distinct_operation_trigger_context",
                    )
            # With no terminal identity and no consumer projection, the first
            # unseen abstract carrier is already the optimal acquisition target.
            # Ask the incremental novelty planner first; pay for an exhaustive
            # sweep only when it cannot find one and saturation must be decided.
            if (
                plan is None
                and not terminal_identity_defined
                and abstract_fn is not None
                and (
                    coverage_fn is None
                    or acquisition_policy
                    == "incremental_novelty_after_bounded_capitulation"
                )
            ):
                incremental_attempted = True
                novelty_abstract_fn, novelty_visited, novelty_interner = _novelty_view(
                    projected=(
                        acquisition_policy
                        == "incremental_novelty_after_bounded_capitulation"
                    )
                )
                _t0 = time.perf_counter()
                plan = plan_novelty(
                    planning_model,
                    state,
                    adapter.action_arity,
                    _vset._raw,
                    visited_abstract=novelty_visited,
                    start_step=adapter.t,
                    max_depth=plan_depth,
                    abstract_fn=novelty_abstract_fn,
                    _state_interner=_pg_interner,
                    _abstract_interner_cache=novelty_interner,
                )
                _t_plan += time.perf_counter() - _t0
                if plan is not None and plan.actions:
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=plan,
                        policy=(
                            "incremental_abstract_novelty"
                            if coverage_fn is None
                            else acquisition_policy
                        ),
                        search_status="first_unseen_abstract_carrier",
                    )
                    last_planning_outcome = {
                        "policy": (
                            "incremental_abstract_novelty"
                            if coverage_fn is None
                            else acquisition_policy
                        ),
                        "status": "first_unseen_abstract_carrier",
                        "exhaustive": False,
                    }
                else:
                    plan = None
                    last_planning_outcome = {
                        "policy": (
                            "incremental_abstract_novelty"
                            if coverage_fn is None
                            else acquisition_policy
                        ),
                        "status": "no_unseen_within_incremental_bound",
                        "exhaustive": False,
                    }
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=None,
                        policy=last_planning_outcome["policy"],
                        search_status="no_unseen_within_incremental_bound",
                        exhaustive=False,
                    )
            # ABSTRACT REACHABILITY is the single acquisition door.  It keeps
            # transition-state equality in ``abstract_fn`` while pricing novelty
            # through the consumer-indexed ``coverage_fn`` projection.  Running
            # raw abstract novelty first would let predictable clocks or other
            # feasibility coordinates preempt changes in controllable factors.
            # object-state memoization makes exhaustive FSM coverage tractable, and
            # coverage is how the FIRST level is found before any goal predicate.
            if (
                plan is None
                and abstract_fn is not None
                and acquisition_policy == "projected_reachability_coverage"
            ):
                sweep_cap = _SWEEP_MAX_STATES
                budget_allocations: list[dict[str, Any]] = []
                while True:
                    _t0 = time.perf_counter()
                    sw = reachability_sweep(
                        planning_model,
                        state,
                        adapter.action_arity,
                        goal_fn=goal_fn,
                        goal_edge_fn=active_goal_edge_fn,
                        resource_colors=resource_colors,
                        start_step=adapter.t,
                        max_depth=plan_depth * 6,
                        max_states=sweep_cap,
                        invariants=invariants,
                        abstract_fn=abstract_fn,
                        visited_store=visited_store,
                        coverage_fn=coverage_fn,
                        admissible_fn=(
                            (
                                lambda candidate_state: (
                                    factored_projection.in_domain(candidate_state)
                                    and factored_projection.factor(
                                        candidate_state
                                    ).ordered_budget > 0
                                )
                            )
                            if factored_projection is not None
                            else None
                        ),
                    )
                    _t_plan += time.perf_counter() - _t0
                    if (
                        sw.status != "search_budget_exhausted"
                        or not terminal_identity_defined
                        or sweep_cap >= _SWEEP_ESCALATION_MAX_STATES
                    ):
                        break
                    next_cap = min(
                        _SWEEP_ESCALATION_MAX_STATES,
                        max(sweep_cap + 1, sweep_cap * 5),
                    )
                    allocation = {
                        "from_cap": sweep_cap,
                        "to_cap": next_cap,
                        "trigger": "search_budget_exhausted",
                        "target_identity": "defined",
                    }
                    budget_allocations.append(allocation)
                    if receipts_dir is not None:
                        _budget_p = Path(receipts_dir) / "reachability_budget.jsonl"
                        _budget_p.parent.mkdir(parents=True, exist_ok=True)
                        with _budget_p.open("a") as _bf:
                            _bf.write(json.dumps({
                                "schema": "ztare-reachability-budget-v1",
                                "states_enumerated": int(
                                    getattr(sw, "states_enumerated", 0) or 0
                                ),
                                "cap": sweep_cap,
                                "status": sw.status,
                                "replans": replans,
                                "consumer_action": allocation,
                                "ts": datetime.utcnow().isoformat(),
                            }) + "\n")
                    sweep_cap = next_cap
                sw_states_enumerated = int(
                    getattr(sw, "states_enumerated", 0) or 0
                )
                sw_exhaustive = bool(getattr(sw, "exhaustive", False))
                last_planning_outcome = {
                    "policy": "projected_reachability_coverage",
                    "status": sw.status,
                    "states_enumerated": sw_states_enumerated,
                    "exhaustive": sw_exhaustive,
                    "budget_allocations": budget_allocations,
                    "final_state_cap": sweep_cap,
                }
                if (
                    sw.status == "search_budget_exhausted"
                    and not terminal_identity_defined
                ):
                    # The bounded search has paid for a capitulation receipt.
                    # Repeating the same full allocation on the next replan
                    # discards that consequence.  Shift only allocation; the
                    # model, prompt, task identity, and verifier remain fixed.
                    acquisition_policy = (
                        "incremental_novelty_after_bounded_capitulation"
                    )
                if sw_states_enumerated >= sweep_cap:
                    _budget_p = (Path(receipts_dir) if receipts_dir else Path("workspace")) / "reachability_budget.jsonl"
                    _budget_p.parent.mkdir(parents=True, exist_ok=True)
                    with _budget_p.open("a") as _bf:
                        _bf.write(json.dumps({
                            "schema": "ztare-reachability-budget-v1",
                            "states_enumerated": sw_states_enumerated,
                            "cap": sweep_cap,
                            "status": sw.status,
                            "replans": replans,
                            "consumer_action": "bounded_stop",
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
                if saturated and sw.status == "coverage" and _witnessed_pairs is not None:
                    # A saturated coverage plan revisits states already seen —
                    # known-uninformative by the sweep's own verdict. Prefer the
                    # nearest reachable (alpha, action) pair the evidence bank
                    # has never witnessed: support is model-independent, so this
                    # targets exactly the transitions saturation cannot see.
                    _t0 = time.perf_counter()
                    _wg = plan_witness_gap(
                        planning_model, state, adapter.action_arity,
                        _witnessed_pairs, start_step=adapter.t,
                        max_depth=plan_depth, abstract_fn=abstract_fn,
                        support_fn=_support_alpha)
                    _t_plan += time.perf_counter() - _t0
                    if _wg is not None and _wg.actions:
                        plan = _wg
                        last_planning_outcome = _bounded_plan_outcome(
                            plan,
                            policy="witness_gap_acquisition",
                            found_status="unsupported_operation_pair",
                        )
                        if receipts_dir is not None:
                            _append_acquisition_routing(
                                receipts_dir,
                                visited_store=visited_store,
                                plan=plan,
                                policy="witness_gap_acquisition",
                                search_status="unsupported_operation_pair",
                            )
                if (
                    receipts_dir is not None
                    and not terminal_identity_defined
                    and progress_fn is None
                ):
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=plan,
                        policy="projected_reachability_coverage",
                        search_status=sw.status,
                        states_enumerated=sw_states_enumerated,
                        exhaustive=sw_exhaustive,
                    )
            if (
                plan is None
                and (goal_fn is not None or active_goal_edge_fn is not None)
                and not goal_edge_has_witness_sources
            ):
                _t0 = time.perf_counter()
                plan = plan_to_goal(planning_model, state, adapter.action_arity, goal_fn,
                                    goal_edge_fn=active_goal_edge_fn,
                                    start_step=adapter.t, max_depth=plan_depth,
                                    abstract_fn=abstract_fn,
                                    _state_interner=_pg_interner)
                _t_plan += time.perf_counter() - _t0
                last_planning_outcome = _bounded_plan_outcome(
                    plan,
                    policy="bounded_terminal_search",
                    found_status="target_path_found",
                )
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
                    _t0 = time.perf_counter()
                    plan = plan_novelty(planning_model, state, adapter.action_arity, _vset._raw,
                                        visited_abstract=_visited_abstract(),
                                        start_step=adapter.t, max_depth=plan_depth,
                                        abstract_fn=abstract_fn,
                                        _state_interner=_pg_interner,
                                        _abstract_interner_cache=_pg_abs_interner)
                    _t_plan += time.perf_counter() - _t0
                    last_planning_outcome = _bounded_plan_outcome(
                        plan,
                        policy="periodic_novelty_steering",
                        found_status="novelty_path_found",
                    )
                else:
                    _t0 = time.perf_counter()
                    plan = plan_progress(planning_model, state, adapter.action_arity, progress_fn,
                                         start_step=adapter.t, max_depth=plan_depth,
                                         abstract_fn=abstract_fn,
                                         _state_interner=_pg_interner,
                                         _abstract_interner_cache=_pg_abs_interner)
                    _t_plan += time.perf_counter() - _t0
                    last_planning_outcome = _bounded_plan_outcome(
                        plan,
                        policy="progress_steering",
                        found_status="progress_path_found",
                    )
            elif plan is None and not incremental_attempted:
                # only when reachability/goal produced nothing — DON'T overwrite a
                # coverage/goal plan (that made the whole sweep apparatus inert)
                novelty_abstract_fn, novelty_visited, novelty_interner = _novelty_view(
                    projected=(
                        acquisition_policy
                        == "incremental_novelty_after_bounded_capitulation"
                    )
                )
                _t0 = time.perf_counter()
                plan = plan_novelty(planning_model, state, adapter.action_arity, _vset._raw,
                                    visited_abstract=novelty_visited,
                                    start_step=adapter.t, max_depth=plan_depth,
                                    abstract_fn=novelty_abstract_fn,
                                    _state_interner=_pg_interner,
                                    _abstract_interner_cache=novelty_interner)
                _t_plan += time.perf_counter() - _t0
                last_planning_outcome = _bounded_plan_outcome(
                    plan,
                    policy=(
                        acquisition_policy
                        if acquisition_policy
                        == "incremental_novelty_after_bounded_capitulation"
                        else "novelty_fallback"
                    ),
                    found_status="first_unseen_abstract_carrier",
                )
                if (
                    plan is not None
                    and plan.actions
                    and acquisition_policy
                    == "incremental_novelty_after_bounded_capitulation"
                ):
                    _append_acquisition_routing(
                        receipts_dir,
                        visited_store=visited_store,
                        plan=plan,
                        policy=acquisition_policy,
                        search_status="first_unseen_abstract_carrier",
                    )
            if plan is None or not plan.actions:
                # Terminal acquisition fallback: novelty saturated over PREDICTED
                # successors, but witness support is model-independent — seek the
                # nearest reachable (alpha, action) pair the evidence bank has
                # never witnessed. This is where a wrong model hides: it predicts
                # something old there, so novelty can never select it.
                if _witnessed_pairs is not None:
                    _t0 = time.perf_counter()
                    plan = plan_witness_gap(
                        planning_model, state, adapter.action_arity,
                        _witnessed_pairs, start_step=adapter.t,
                        max_depth=plan_depth, abstract_fn=abstract_fn,
                        support_fn=_support_alpha)
                    _t_plan += time.perf_counter() - _t0
                    if plan is not None and plan.actions:
                        last_planning_outcome = _bounded_plan_outcome(
                            plan,
                            policy="witness_gap_acquisition",
                            found_status="unsupported_operation_pair",
                        )
            if plan is None or not plan.actions:
                return PursuitReceipt(status="plan_exhausted", steps_executed=len(trace),
                                      levels_gained=_levels(adapter) - baseline,
                                      detail=(plan.reason if plan else "planner returned nothing"),
                                      replans=replans, trace=trace, saturated=saturated,
                                      observed_transitions=observed,
                                      planning_outcome=_planning_receipt())
            for action_index, a in enumerate(plan.actions):
                step_now = adapter.t
                candidate_goal_edge = None
                if (
                    action_index == len(plan.actions) - 1
                    and active_goal_edge_fn is not None
                    and callable(
                        getattr(active_goal_edge_fn, "refute_satisfied", None)
                    )
                    and goal_edge_matches(
                        active_goal_edge_fn,
                        state,
                        a,
                        step_now,
                    )
                ):
                    candidate_goal_edge = {
                        "source": state,
                        "operation": a,
                        "time": step_now,
                        "hypothesis_ids": list(
                            active_goal_edge_fn.satisfied_ids(
                                state,
                                a,
                                step_now,
                            )
                        ),
                        "goal_edge_identity_sha256": str(
                            getattr(
                                active_goal_edge_fn,
                                "identity_sha256",
                                "",
                            )
                        ),
                    }
                _sid = _pg_interner.get_id(state) if _pg_interner is not None else None
                _memo_key = (_sid if _sid is not None else state, a, step_now)
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
                transition_identity = getattr(adapter, "last_transition_identity", None)
                if not isinstance(transition_identity, TransitionIdentity):
                    transition_identity = None
                observed.append(
                    Transition(
                        t=step_now,
                        s=state,
                        a=a,
                        s_next=real,
                        identity=transition_identity,
                    )
                )
                if _witnessed_pairs is not None:
                    try:
                        _witnessed_pairs.add((_support_alpha(state), a))
                    except Exception:
                        pass
                environment_boundary = authoritative_boundary(transition_identity)
                # frontier memory: the observed live state is now visited
                if (
                    not environment_boundary
                    and abstract_fn is not None
                    and visited_store is not None
                ):
                    carrier = abstract_fn(real)
                    visited_store.add(carrier)
                    persistent_abstract.add(carrier)
                    steps_since_save += 1
                    if visited_path is not None and steps_since_save >= 50:
                        save_visited(visited_path, visited_store)
                        steps_since_save = 0
                # A None prediction is a fail-closed error from the champion, not
                # agreement: pursuing blind under an erroring model is a divergence
                # event (terminal_witness_fingerprint emits its prediction_none kind).
                mismatch = predicted is None or real != predicted
                acquisition_observed = bool(
                    acquisition_obligation is not None
                    and transition_identity is not None
                    and transition_identity.is_authoritative
                    and not transition_identity.is_boundary
                    and acquisition_obligation.accepts_edge(
                        state,
                        a,
                        step_now,
                        real,
                    )
                )
                planned_unknown_observation = (
                    predicted is None
                    and planned_undefined_terminal
                    and action_index == len(plan.actions) - 1
                )
                runtime_divergence = None
                if (
                    mismatch
                    and not environment_boundary
                    and not planned_unknown_observation
                ):
                    runtime_divergence = _divergence_payload(
                        a,
                        step_now,
                        state,
                        predicted,
                        real,
                    )
                    _record_skill_cegar_counterexample(
                        step_now=step_now,
                        divergence=runtime_divergence,
                    )
                if _levels(adapter) > baseline:
                    detail = "terminal verifier event occurred after model steering"
                    divergence = None
                    if planned_unknown_observation:
                        detail += "; terminal event supplied an undefined operation image"
                    elif mismatch and not environment_boundary:
                        detail += "; terminal edge also refuted the transition law"
                        divergence = runtime_divergence
                    elif mismatch:
                        detail += "; adapter-owned boundary lies outside the within-epoch carrier"
                    return PursuitReceipt(status="goal_reached", steps_executed=len(trace),
                                          levels_gained=_levels(adapter) - baseline,
                                          detail=detail, divergence=divergence,
                                          replans=replans, trace=trace, saturated=saturated,
                                          observed_transitions=observed,
                                          planning_outcome=_planning_receipt())
                if mismatch:
                    if environment_boundary:
                        return PursuitReceipt(
                            status="environment_boundary",
                            steps_executed=len(trace),
                            levels_gained=0,
                            detail=(
                                "adapter-owned epoch boundary encountered; resume from "
                                "the adapter's new epoch without refining the within-epoch law"
                            ),
                            divergence=None,
                            replans=replans,
                            trace=trace,
                            saturated=saturated,
                            observed_transitions=observed,
                            planning_outcome=_planning_receipt(),
                            candidate_goal_edge=candidate_goal_edge,
                        )
                    if (
                        planned_unknown_observation
                    ):
                        return PursuitReceipt(
                            status="acquisition_observed",
                            steps_executed=len(trace),
                            levels_gained=0,
                            detail=(
                                "live execution supplied the consequence of an "
                                "admitted partial operation"
                            ),
                            divergence=None,
                            replans=replans,
                            trace=trace,
                            saturated=saturated,
                            observed_transitions=observed,
                            planning_outcome=_planning_receipt(),
                            candidate_goal_edge=candidate_goal_edge,
                        )
                    if acquisition_observed:
                        return PursuitReceipt(
                            status="acquisition_observed",
                            steps_executed=len(trace),
                            levels_gained=0,
                            detail=(
                                "live execution supplied a new law-owned observation "
                                "of the operation; the transition law was also refuted"
                            ),
                            divergence=_divergence_payload(
                                a, step_now, state, predicted, real
                            ) if runtime_divergence is None else runtime_divergence,
                            replans=replans,
                            trace=trace,
                            saturated=saturated,
                            observed_transitions=observed,
                            planning_outcome=_planning_receipt(),
                            candidate_goal_edge=candidate_goal_edge,
                        )
                    return PursuitReceipt(
                        status="model_diverged", steps_executed=len(trace),
                        levels_gained=_levels(adapter) - baseline,
                        detail="ratified law mispredicted a live transition off the witnessed basin; "
                               "re-identify before planning further",
                        divergence=(
                            runtime_divergence
                            or _divergence_payload(
                                a, step_now, state, predicted, real
                            )
                        ),
                        replans=replans, trace=trace, saturated=saturated,
                        observed_transitions=observed,
                        planning_outcome=_planning_receipt(),
                        candidate_goal_edge=candidate_goal_edge)
                if candidate_goal_edge is not None:
                    state = real
                    _vset.add(state)
                    return PursuitReceipt(
                        status="candidate_goal_edge_reached",
                        steps_executed=len(trace),
                        levels_gained=0,
                        detail=(
                            "candidate task relation reached; adapter "
                            "adjudication retains discharge authority"
                        ),
                        replans=replans,
                        trace=trace,
                        saturated=saturated,
                        observed_transitions=observed,
                        planning_outcome=_planning_receipt(),
                        candidate_goal_edge=candidate_goal_edge,
                    )
                if acquisition_observed:
                    return PursuitReceipt(
                        status="acquisition_observed",
                        steps_executed=len(trace),
                        levels_gained=0,
                        detail=(
                            "live execution supplied a new law-owned observation "
                            "of the operation"
                        ),
                        divergence=None,
                        replans=replans,
                        trace=trace,
                        saturated=saturated,
                        observed_transitions=observed,
                        planning_outcome=_planning_receipt(),
                    )
                state = real
                _vset.add(state)
                if _pg_interner is not None:
                    try:
                        _pg_interner.mark_visited(state)
                    except ValueError:
                        # A shape-changing epoch cannot share this fixed-width arena.
                        _pg_interner = None
                elif _pg_abs_interner is not None:
                    _pg_abs_interner.mark_visited(abstract_fn(state))
                if goal_fn is not None and goal_fn(state):
                    return PursuitReceipt(
                        status="candidate_goal_reached",
                        steps_executed=len(trace),
                        levels_gained=0,
                        detail=(
                            "candidate task predicate reached; adapter adjudication "
                            "retains discharge authority"
                        ),
                        replans=replans,
                        trace=trace,
                        saturated=saturated,
                        observed_transitions=observed,
                        planning_outcome=_planning_receipt(),
                    )
                if len(trace) >= max_steps:
                    break
            if planned_acquisition_transaction and observed:
                return PursuitReceipt(
                    status="acquisition_observed",
                    steps_executed=len(trace),
                    levels_gained=0,
                    detail=(
                        "one bounded acquisition transaction completed; return "
                        "observations to identification before replanning"
                    ),
                    replans=replans,
                    trace=trace,
                    saturated=saturated,
                    observed_transitions=observed,
                    planning_outcome=_planning_receipt(),
                )
            replans += 1  # plan consumed without reaching goal → replan from the new state

        detail = f"budget exhausted ({len(trace)} steps, {replans} replans)"
        if saturated:
            detail += " — coverage SATURATED: all reachable object-states already visited (CEGAR trigger)"
        return PursuitReceipt(status="plan_exhausted", steps_executed=len(trace),
                              levels_gained=_levels(adapter) - baseline,
                              detail=detail, replans=replans, trace=trace,
                              saturated=saturated, observed_transitions=observed,
                              planning_outcome=_planning_receipt())
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
        for transition in pr.observed_transitions:
            log.append_transition(transition)
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
    seen = {(start, start_step)}
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
            key = (nxt, step + 1)
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
