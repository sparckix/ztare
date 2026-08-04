"""Behavioral refinement of a consumer-indexed transition quotient.

For a parent key ``q`` and finite labeled operation family, one refinement step
uses the canonical coordinate

    q1(s, t) = (q(s, t), (q(T_a(s, t), t + 1))_a).

This is the immediate right-congruence splitter: if two parent-equivalent
states have different labeled parent images, they cannot remain equal in the
refined consumer.  Goal semantics, feasibility, and adjudication stay owned by
the wrapped problem.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Hashable

from ztare.common.equivariance import stable_sha256


def _prediction_key(
    state: Any,
    operation: Any,
    time_value: Any,
) -> Hashable:
    value = state, operation, time_value
    try:
        hash(value)
    except TypeError:
        return stable_sha256({
            "state": state,
            "operation": operation,
            "time": time_value,
        })
    return value


class LabeledSuccessorRefinementProblem:
    """Finite-depth behavioral refinement of an opaque search problem."""

    def __init__(
        self,
        *,
        parent: Any,
        predict: Callable[[Any, Any, Any], Any],
        operations: tuple[Any, ...],
        carrier_execution_sha256: str,
        refinement_depth: int = 1,
        advance_time: Callable[[Any], Any] = lambda value: value + 1,
    ) -> None:
        if not str(getattr(parent, "problem_id", "")).strip():
            raise ValueError("behavioral refinement requires parent problem identity")
        if not operations or len(operations) != len(set(operations)):
            raise ValueError(
                "behavioral refinement requires unique finite operations"
            )
        if len(str(carrier_execution_sha256)) != 64:
            raise ValueError(
                "behavioral refinement requires carrier execution identity"
            )
        if (
            not isinstance(refinement_depth, int)
            or isinstance(refinement_depth, bool)
            or refinement_depth < 1
        ):
            raise ValueError("behavioral refinement depth must be positive")
        self.parent = parent
        self._predict = predict
        self.operations = tuple(operations)
        self.carrier_execution_sha256 = str(carrier_execution_sha256)
        self.refinement_depth = refinement_depth
        self.advance_time = advance_time
        self.factor_names = (
            *tuple(parent.factor_names),
            f"labeled_successor_signature_depth_{refinement_depth}",
        )
        self.terminal_factor_names = tuple(parent.terminal_factor_names)
        self.feasibility_factor_names = tuple(
            parent.feasibility_factor_names
        )
        self.availability_factor_names = tuple(
            parent.availability_factor_names
        )
        self.evidence_refs = tuple(parent.evidence_refs)
        identity = {
            "schema": "ztare-labeled-successor-refinement-problem-v1",
            "parent_problem_id": parent.problem_id,
            "parent_projection_sha256": parent.projection_sha256,
            "carrier_execution_sha256": self.carrier_execution_sha256,
            "operations": list(map(repr, self.operations)),
            "refinement_depth": self.refinement_depth,
            "factor_names": self.factor_names,
            "terminal_factor_names": self.terminal_factor_names,
            "feasibility_factor_names": self.feasibility_factor_names,
            "availability_factor_names": self.availability_factor_names,
            "evidence_refs": self.evidence_refs,
        }
        self.projection_sha256 = stable_sha256({
            "kind": "consumer_behavioral_refinement",
            **identity,
        })
        self.problem_id = stable_sha256(identity)
        self._predict_cached = lru_cache(maxsize=4_096)(
            self._predict_hashable
        )
        self._refined_key_cached = lru_cache(maxsize=8_192)(
            self._refined_key_hashable
        )
        self.last_projection_counterexample: (
            tuple[Any, Any, Any, Any, Any, dict[str, Any]] | None
        ) = None

    def _predict_hashable(
        self,
        state: Hashable,
        operation: Hashable,
        time_value: Hashable,
    ) -> Any:
        return self._predict(state, operation, time_value)

    def predict(
        self,
        state: Any,
        operation: Any,
        time_value: Any,
    ) -> Any:
        key = _prediction_key(state, operation, time_value)
        if key == (state, operation, time_value):
            return self._predict_cached(state, operation, time_value)
        # Unhashable observations cannot enter the typed lru_cache directly.
        # The caller's predictor still owns their transition semantics.
        return self._predict(state, operation, time_value)

    def _parent_key(self, state: Any, time_value: Any) -> Hashable:
        indexed = getattr(self.parent, "dominance_key_at", None)
        value = (
            indexed(state, time_value)
            if callable(indexed)
            else self.parent.dominance_key(state)
        )
        try:
            hash(value)
        except TypeError as exc:
            raise TypeError("parent dominance key must be hashable") from exc
        return value

    def _refined_key_hashable(
        self,
        state: Hashable,
        time_value: Hashable,
        depth: int,
    ) -> Hashable:
        if depth == 0:
            return self._parent_key(state, time_value)
        next_time = self.advance_time(time_value)
        images = []
        for operation in self.operations:
            successor = self.predict(state, operation, time_value)
            if successor is None or not self.parent.admissible(successor):
                image = ("missing_or_outside_domain",)
            else:
                image = (
                    "image",
                    self._refined_key(successor, next_time, depth - 1),
                )
            images.append((operation, image))
        return (
            "behavior_sha256",
            stable_sha256({
                "depth": depth,
                "source": self._refined_key(
                    state,
                    time_value,
                    depth - 1,
                ),
                "images": images,
            }),
        )

    def _refined_key(
        self,
        state: Any,
        time_value: Any,
        depth: int,
    ) -> Hashable:
        try:
            hash((state, time_value, depth))
        except TypeError:
            return self._refined_key_hashable(state, time_value, depth)
        return self._refined_key_cached(state, time_value, depth)

    def dominance_key_at(
        self,
        state: Any,
        time_value: Any,
    ) -> Hashable:
        return self._refined_key(
            state,
            time_value,
            self.refinement_depth,
        )

    def dominance_key(self, state: Any) -> Hashable:
        return self.dominance_key_at(state, 0)

    def dominance_vector(
        self,
        state: Any,
    ) -> tuple[int | float, ...]:
        return tuple(self.parent.dominance_vector(state))

    def goal_edge(
        self,
        state: Any,
        intervention: Any,
        time_value: Any,
    ) -> bool:
        return bool(self.parent.goal_edge(state, intervention, time_value))

    def state_target(self, state: Any) -> bool:
        target = getattr(self.parent, "state_target", None)
        return bool(target(state)) if callable(target) else False

    def admissible(self, state: Any) -> bool:
        return bool(self.parent.admissible(state))

    def estimate(self, state: Any) -> int | float:
        return self.parent.estimate(state)

    def continuation_admissible(
        self,
        state: Any,
        path: tuple[Any, ...],
    ) -> bool:
        selector = getattr(self.parent, "continuation_admissible", None)
        return bool(selector(state, path)) if callable(selector) else True

    def explain_state_difference(
        self,
        left: Any,
        right: Any,
    ) -> dict[str, Any]:
        explainer = getattr(self.parent, "explain_state_difference", None)
        receipt = (
            explainer(left, right)
            if callable(explainer)
            else {"schema": "ztare-behavioral-refinement-difference-v1"}
        )
        if not isinstance(receipt, dict):
            receipt = {"parent_explanation": repr(receipt)}
        receipt["behavioral_refinement_depth"] = self.refinement_depth
        return receipt

    def capture_projection_counterexample(
        self,
        left: Any,
        right: Any,
        intervention: Any,
        left_time: Any,
        right_time: Any,
        payload: dict[str, Any],
    ) -> None:
        """Retain opaque witnesses in memory for bounded suffix extraction."""
        self.last_projection_counterexample = (
            left,
            right,
            intervention,
            left_time,
            right_time,
            dict(payload),
        )

    def distinguishing_word(
        self,
        left: Any,
        right: Any,
        time_value: Any,
        *,
        max_depth: int | None = None,
    ) -> tuple[Any, ...] | None:
        """Shortest word whose parent quotient separates an observation pair."""
        bound = self.refinement_depth if max_depth is None else max_depth
        if bound < 0:
            raise ValueError("distinguishing-word depth cannot be negative")
        frontier: list[tuple[Any, Any, Any, tuple[Any, ...]]] = [
            (left, right, time_value, ())
        ]
        for depth in range(bound + 1):
            next_frontier = []
            for left_state, right_state, current_time, word in frontier:
                if self._parent_key(
                    left_state,
                    current_time,
                ) != self._parent_key(right_state, current_time):
                    return word
                if depth == bound:
                    continue
                next_time = self.advance_time(current_time)
                for operation in self.operations:
                    left_next = self.predict(
                        left_state,
                        operation,
                        current_time,
                    )
                    right_next = self.predict(
                        right_state,
                        operation,
                        current_time,
                    )
                    left_admissible = (
                        left_next is not None
                        and self.parent.admissible(left_next)
                    )
                    right_admissible = (
                        right_next is not None
                        and self.parent.admissible(right_next)
                    )
                    if left_admissible != right_admissible:
                        return (*word, operation)
                    if left_admissible:
                        next_frontier.append((
                            left_next,
                            right_next,
                            next_time,
                            (*word, operation),
                        ))
            frontier = next_frontier
        return None


__all__ = ["LabeledSuccessorRefinementProblem"]
