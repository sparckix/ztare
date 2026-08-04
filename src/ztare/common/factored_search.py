"""Consumer-indexed search over a certified state projection.

The common kernel does not know what a state contains.  A substrate lowering
supplies a ``FactoredSearchProblem`` whose coordinates have one job in one
consumer lifecycle:

* ``dominance_key`` is equality for transition-relevant coordinates;
* ``dominance_vector`` is an ordered feasibility coordinate where larger is
  declared no worse;
* ``goal_edge`` is a steering hypothesis over an intervention-bearing edge;
* ``estimate`` changes frontier allocation only; and
* ``admissible`` excludes states outside the declared feasibility domain.

The terminal authority remains outside this module.  A returned action list is
only a proposal for execution against the substrate adjudicator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any, Callable, Hashable, Protocol, runtime_checkable


@runtime_checkable
class FactoredSearchProblem(Protocol):
    """Opaque, target-specific projection supplied by a substrate lowering."""

    problem_id: str
    projection_sha256: str
    factor_names: tuple[str, ...]
    terminal_factor_names: tuple[str, ...]
    feasibility_factor_names: tuple[str, ...]
    availability_factor_names: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def dominance_key(self, state: Any) -> Hashable: ...
    def dominance_vector(self, state: Any) -> tuple[int | float, ...]: ...
    def goal_edge(self, state: Any, intervention: Any, time: Any) -> bool: ...
    def admissible(self, state: Any) -> bool: ...
    def estimate(self, state: Any) -> int | float: ...


@runtime_checkable
class FactoredStateTarget(Protocol):
    """Optional state-target obligation for acquisition-style searches."""

    def state_target(self, state: Any) -> bool: ...


@runtime_checkable
class FactoredContinuationSelector(Protocol):
    """Optional information criterion for a bounded frontier proposal."""

    def continuation_admissible(
        self,
        state: Any,
        path: tuple[Any, ...],
    ) -> bool: ...


@dataclass(frozen=True)
class FactoredSearchResult:
    status: str
    actions: tuple[Any, ...] = ()
    continuation_actions: tuple[Any, ...] = ()
    generated: int = 0
    expanded: int = 0
    frontier_remaining: int = 0
    deepest_depth: int = 0
    projection_counterexample: dict[str, Any] = field(default_factory=dict)


def _hashable(value: Any, label: str) -> Hashable:
    try:
        hash(value)
    except TypeError as exc:
        raise TypeError(f"{label} must return a hashable carrier") from exc
    return value


def _vector(problem: FactoredSearchProblem, state: Any) -> tuple[float, ...]:
    raw = tuple(problem.dominance_vector(state))
    try:
        return tuple(float(item) for item in raw)
    except (TypeError, ValueError) as exc:
        raise TypeError("dominance_vector must contain ordered numeric values") from exc


def _estimate(problem: FactoredSearchProblem, state: Any) -> float:
    value = float(problem.estimate(state))
    if value < 0:
        raise ValueError("factored-search estimate must be non-negative")
    return value


def _dominance_key(
    problem: FactoredSearchProblem,
    state: Any,
    time_value: Any,
) -> Hashable:
    """Use a time-indexed key when the lowering has not quotiented the clock."""
    indexed = getattr(problem, "dominance_key_at", None)
    raw = (
        indexed(state, time_value)
        if callable(indexed)
        else problem.dominance_key(state)
    )
    return _hashable(raw, "dominance_key")


def search_factored(
    *,
    predict: Callable[[Any, Any, Any], Any],
    start: Any,
    interventions: tuple[Any, ...],
    problem: FactoredSearchProblem,
    start_time: Any = 0,
    advance_time: Callable[[Any], Any] = lambda value: value + 1,
    max_depth: int = 72,
    max_states: int = 5000,
) -> FactoredSearchResult:
    """Best-first search with product-order feasibility dominance.

    For one ``dominance_key``, a node is discarded only when an earlier node
    has no greater path cost and is coordinatewise no worse on the declared
    feasibility vector.  During expansion, states merged by the key must map
    to the same successor key under each intervention.  A disagreement returns
    ``projection_noncommuting`` with the two witnessed images instead of
    silently continuing on an invalid quotient.
    """
    if not isinstance(problem, FactoredSearchProblem):
        raise TypeError("problem does not implement FactoredSearchProblem")
    if not problem.problem_id or not problem.projection_sha256:
        raise ValueError("factored search requires problem and projection identity")
    if max_depth < 1 or max_states < 1:
        raise ValueError("factored search bounds must be positive")
    if not problem.admissible(start):
        return FactoredSearchResult(status="start_outside_feasibility_domain")

    start_key = _dominance_key(problem, start, start_time)
    start_vector = _vector(problem, start)
    state_target = (
        problem.state_target
        if isinstance(problem, FactoredStateTarget)
        else None
    )
    if state_target is not None and state_target(start):
        return FactoredSearchResult(status="state_found")
    pareto: dict[
        Hashable,
        list[tuple[int, tuple[float, ...], Any, Any]],
    ] = {
        start_key: [(0, start_vector, start, start_time)]
    }
    # A quotient key claims that its transition image is well-defined.  Keep a
    # witness per (key, intervention); a second image refutes that claim.
    transition_images: dict[tuple[Hashable, Any], Hashable] = {}

    def counterexample_receipt(
        payload: dict[str, Any],
        left: Any,
        right: Any,
        intervention: Any,
        left_time: Any,
        right_time: Any,
    ) -> dict[str, Any]:
        """Attach a bounded substrate explanation at the erasure boundary."""
        explainer = getattr(problem, "explain_state_difference", None)
        if not callable(explainer):
            explainer = getattr(
                getattr(problem, "projection", None),
                "explain_state_difference",
                None,
            )
        if callable(explainer):
            try:
                explanation = explainer(left, right)
            except Exception as exc:  # noqa: BLE001
                explanation = {"diagnostic_error": type(exc).__name__}
            if isinstance(explanation, dict):
                payload["consumer_difference"] = explanation
        capture = getattr(problem, "capture_projection_counterexample", None)
        if callable(capture):
            capture(
                left,
                right,
                intervention,
                left_time,
                right_time,
                payload,
            )
        return payload

    def dominance_counterexample(
        *,
        key: Hashable,
        dominator_state: Any,
        dominator_time: Any,
        dominated_state: Any,
        dominated_time: Any,
    ) -> dict[str, Any] | None:
        """Check the forward-simulation claim paid for by dominance pruning.

        Equality of the projected key is insufficient: a discarded concrete
        presentation may still expose an intervention or image that its
        purported dominator cannot reproduce.  Check that implication at the
        merge boundary, before the only distinguishing witness is erased.
        """
        for intervention in interventions:
            dominator_goal = bool(
                problem.goal_edge(dominator_state, intervention, dominator_time)
            )
            dominated_goal = bool(
                problem.goal_edge(dominated_state, intervention, dominated_time)
            )
            if dominated_goal and not dominator_goal:
                return counterexample_receipt({
                    "kind": "dominance_simulation_failed",
                    "merged_key": repr(key),
                    "intervention": repr(intervention),
                    "dominator_time": repr(dominator_time),
                    "dominated_time": repr(dominated_time),
                    "dominator_image": "nonterminal",
                    "dominated_image": "goal_edge",
                }, dominator_state, dominated_state, intervention,
                   dominator_time, dominated_time)
            if dominated_goal:
                continue
            dominated_successor = predict(
                dominated_state, intervention, dominated_time
            )
            if dominated_successor is None or not problem.admissible(
                dominated_successor
            ):
                # A dominator may possess transitions the dominated state
                # lacks.  Only the reverse would invalidate forward simulation.
                continue
            dominator_successor = predict(
                dominator_state, intervention, dominator_time
            )
            if dominator_successor is None or not problem.admissible(
                dominator_successor
            ):
                return counterexample_receipt({
                    "kind": "dominance_simulation_failed",
                    "merged_key": repr(key),
                    "intervention": repr(intervention),
                    "dominator_time": repr(dominator_time),
                    "dominated_time": repr(dominated_time),
                    "dominator_image": "missing_or_outside_domain",
                    "dominated_image": repr(
                        _dominance_key(
                            problem,
                            dominated_successor,
                            advance_time(dominated_time),
                        )
                    ),
                }, dominator_state, dominated_state, intervention,
                   dominator_time, dominated_time)
            dominator_key = _hashable(
                _dominance_key(
                    problem,
                    dominator_successor,
                    advance_time(dominator_time),
                ),
                "dominance_key",
            )
            dominated_key = _hashable(
                _dominance_key(
                    problem,
                    dominated_successor,
                    advance_time(dominated_time),
                ),
                "dominance_key",
            )
            dominator_vector = _vector(problem, dominator_successor)
            dominated_vector = _vector(problem, dominated_successor)
            simulates = (
                dominator_key == dominated_key
                and len(dominator_vector) == len(dominated_vector)
                and all(
                    upper >= lower
                    for upper, lower in zip(dominator_vector, dominated_vector)
                )
            )
            if not simulates:
                return counterexample_receipt({
                    "kind": "dominance_simulation_failed",
                    "merged_key": repr(key),
                    "intervention": repr(intervention),
                    "dominator_time": repr(dominator_time),
                    "dominated_time": repr(dominated_time),
                    "dominator_image": repr(
                        (dominator_key, dominator_vector)
                    ),
                    "dominated_image": repr(
                        (dominated_key, dominated_vector)
                    ),
                }, dominator_state, dominated_state, intervention,
                   dominator_time, dominated_time)
        return None

    def admitted(
        key: Hashable,
        depth: int,
        vector: tuple[float, ...],
        state: Any,
        time_value: Any,
    ) -> tuple[bool, dict[str, Any] | None]:
        rows = pareto.setdefault(key, [])
        exact_transition_identity = bool(
            getattr(problem, "exact_transition_identity", False)
        )
        dominators = [
            row
            for row in rows
            if row[0] <= depth
            and len(row[1]) == len(vector)
            and all(old >= new for old, new in zip(row[1], vector))
        ]
        if dominators:
            # Exact (state, time) identity makes deterministic transition
            # compatibility definitional. Re-running every labeled successor
            # check at a duplicate node changes no scientific claim and can
            # dominate the cost of a conservative fallback search.
            if exact_transition_identity:
                return False, None
            for _old_depth, _old_vector, old_state, old_time in dominators:
                counterexample = dominance_counterexample(
                    key=key,
                    dominator_state=old_state,
                    dominator_time=old_time,
                    dominated_state=state,
                    dominated_time=time_value,
                )
                if counterexample is not None:
                    return False, counterexample
            return False, None
        dominated_rows = [
            row
            for row in rows
            if depth <= row[0]
            and len(row[1]) == len(vector)
            and all(new >= old for new, old in zip(vector, row[1]))
        ]
        if not exact_transition_identity:
            for _old_depth, _old_vector, old_state, old_time in dominated_rows:
                counterexample = dominance_counterexample(
                    key=key,
                    dominator_state=state,
                    dominator_time=time_value,
                    dominated_state=old_state,
                    dominated_time=old_time,
                )
                if counterexample is not None:
                    return False, counterexample
        rows[:] = [
            row
            for row in rows
            if not (
                depth <= row[0]
                and len(row[1]) == len(vector)
                and all(new >= old for new, old in zip(vector, row[1]))
            )
        ]
        rows.append((depth, vector, state, time_value))
        return True, None

    tie = generated = expanded = deepest = 0
    depth_truncated = False
    frontier: list[tuple[float, int, int, Any, Any, tuple[Any, ...]]] = [
        (_estimate(problem, start), 0, tie, start, start_time, ())
    ]
    while frontier and generated < max_states:
        _priority, depth, _tie, state, time_value, path = heapq.heappop(frontier)
        expanded += 1
        deepest = max(deepest, depth)
        if depth >= max_depth:
            depth_truncated = True
            continue
        source_key = _dominance_key(problem, state, time_value)
        for intervention in interventions:
            if problem.goal_edge(state, intervention, time_value):
                return FactoredSearchResult(
                    status="edge_found",
                    actions=path + (intervention,),
                    generated=generated,
                    expanded=expanded,
                    frontier_remaining=len(frontier),
                    deepest_depth=max(deepest, depth + 1),
                )
            successor = predict(state, intervention, time_value)
            if successor is None or not problem.admissible(successor):
                continue
            successor_time = advance_time(time_value)
            successor_key = _dominance_key(problem, successor, successor_time)
            image_key = (source_key, intervention)
            prior_image = transition_images.get(image_key)
            if prior_image is not None and prior_image != successor_key:
                return FactoredSearchResult(
                    status="projection_noncommuting",
                    generated=generated,
                    expanded=expanded,
                    frontier_remaining=len(frontier),
                    deepest_depth=deepest,
                    projection_counterexample={
                        "source_key": repr(source_key),
                        "intervention": repr(intervention),
                        "prior_successor_key": repr(prior_image),
                        "successor_key": repr(successor_key),
                    },
                )
            transition_images[image_key] = successor_key
            if state_target is not None and state_target(successor):
                return FactoredSearchResult(
                    status="state_found",
                    actions=path + (intervention,),
                    generated=generated,
                    expanded=expanded,
                    frontier_remaining=len(frontier),
                    deepest_depth=max(deepest, depth + 1),
                )
            successor_vector = _vector(problem, successor)
            next_depth = depth + 1
            is_admitted, merge_counterexample = admitted(
                successor_key,
                next_depth,
                successor_vector,
                successor,
                successor_time,
            )
            if merge_counterexample is not None:
                return FactoredSearchResult(
                    status="projection_noncommuting",
                    generated=generated,
                    expanded=expanded,
                    frontier_remaining=len(frontier),
                    deepest_depth=deepest,
                    projection_counterexample=merge_counterexample,
                )
            if not is_admitted:
                continue
            generated += 1
            tie += 1
            next_path = path + (intervention,)
            heapq.heappush(
                frontier,
                (
                    next_depth + _estimate(problem, successor),
                    next_depth,
                    tie,
                    successor,
                    successor_time,
                    next_path,
                ),
            )
            if generated >= max_states:
                break
    continuation: tuple[Any, ...] = ()
    if frontier:
        selector = (
            problem.continuation_admissible
            if isinstance(problem, FactoredContinuationSelector)
            else None
        )
        selected = next(
            (
                row
                for row in sorted(frontier)
                if selector is None or selector(row[3], row[5])
            ),
            None,
        )
        if selected is not None:
            continuation = selected[5]
    status = (
        "search_budget_exhausted"
        if frontier
        else "depth_bound_exhausted"
        if depth_truncated
        else "projected_frontier_exhausted"
    )
    return FactoredSearchResult(
        status=status,
        # A bounded continuation is a control proposal, not a terminal witness.
        # Keep it in a separate field so consumers cannot obtain terminal
        # authority by treating search truncation as success.
        continuation_actions=continuation,
        generated=generated,
        expanded=expanded,
        frontier_remaining=len(frontier),
        deepest_depth=deepest,
    )


__all__ = [
    "FactoredSearchProblem",
    "FactoredSearchResult",
    "FactoredStateTarget",
    "FactoredContinuationSelector",
    "search_factored",
]
