"""Evidence-scoped task hypotheses over states and partial-action edges.

A task condition may be unary, but intervention-bearing evidence often
distinguishes ``(source, operation, outcome)`` relations that no state
predicate can express.  This module keeps both hypothesis kinds in one version
space and supplies the finite relational preimage used to compose an edge
condition backward through a guarded operation word.

The kernel is substrate-neutral.  Callers own state, operation, outcome,
evidence, lifecycle, and task-adjudication authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Literal, Mapping

from ztare.common.equivariance import stable_sha256


StatePredicate = Callable[[Any], bool]
EdgePredicate = Callable[[Any, Hashable, Any], bool]
PullbackModality = Literal["may", "must"]


@dataclass(frozen=True)
class StateTaskHypothesis:
    """One unary task candidate retained for compatibility."""

    hypothesis_id: str
    predicate: StatePredicate = field(compare=False, repr=False)
    kind: str = "state"
    spec: Any = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not str(self.hypothesis_id).strip():
            raise ValueError("state task hypothesis requires hypothesis_id")


@dataclass(frozen=True)
class EdgeTaskHypothesis:
    """One candidate property of an intervention-bearing edge."""

    hypothesis_id: str
    predicate: EdgePredicate = field(compare=False, repr=False)
    kind: str = "edge"
    spec: Any = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not str(self.hypothesis_id).strip():
            raise ValueError("edge task hypothesis requires hypothesis_id")


@dataclass
class TaskHypothesisVersionSpace:
    """Falsifiable unary and relational task candidates.

    Reaching one task-open state refutes only unary candidates true there.
    Observing one task-open edge refutes only edge candidates true on that
    exact relation.  Siblings remain active.
    """

    state_hypotheses: tuple[StateTaskHypothesis, ...] = ()
    edge_hypotheses: tuple[EdgeTaskHypothesis, ...] = ()
    source_epoch: Hashable | None = None
    task_contract_sha256: str = ""
    refuted_ids: set[str] = field(default_factory=set)
    schema: str = "ztare-task-hypothesis-version-space-v1"

    def __post_init__(self) -> None:
        identities = [
            row.hypothesis_id
            for row in (*self.state_hypotheses, *self.edge_hypotheses)
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("task hypothesis identities must be unique")

    @property
    def active_ids(self) -> tuple[str, ...]:
        return tuple(
            row.hypothesis_id
            for row in (*self.state_hypotheses, *self.edge_hypotheses)
            if row.hypothesis_id not in self.refuted_ids
        )

    @property
    def active_count(self) -> int:
        return len(self.active_ids)

    @property
    def identity_sha256(self) -> str:
        return stable_sha256({
            "active_hypotheses": sorted(self.active_ids),
            "source_epoch": self.source_epoch,
            "task_contract_sha256": self.task_contract_sha256,
        })

    def __call__(self, state: Any) -> bool:
        return bool(self.state_satisfied_ids(state))

    def state_satisfied_ids(self, state: Any) -> tuple[str, ...]:
        return tuple(
            row.hypothesis_id
            for row in self.state_hypotheses
            if row.hypothesis_id not in self.refuted_ids
            and bool(row.predicate(state))
        )

    def edge_satisfied_ids(
        self,
        source: Any,
        operation: Hashable,
        outcome: Any,
    ) -> tuple[str, ...]:
        return tuple(
            row.hypothesis_id
            for row in self.edge_hypotheses
            if row.hypothesis_id not in self.refuted_ids
            and bool(row.predicate(source, operation, outcome))
        )

    def refute_state_satisfied(self, state: Any) -> tuple[str, ...]:
        refuted = self.state_satisfied_ids(state)
        self.refuted_ids.update(refuted)
        return refuted

    def refute_edge_satisfied(
        self,
        source: Any,
        operation: Hashable,
        outcome: Any,
    ) -> tuple[str, ...]:
        refuted = self.edge_satisfied_ids(source, operation, outcome)
        self.refuted_ids.update(refuted)
        return refuted

    def refute_ids(self, hypothesis_ids: Iterable[str]) -> tuple[str, ...]:
        known = {
            row.hypothesis_id
            for row in (*self.state_hypotheses, *self.edge_hypotheses)
        }
        admitted = tuple(dict.fromkeys(
            str(hypothesis_id)
            for hypothesis_id in hypothesis_ids
            if str(hypothesis_id) in known
        ))
        self.refuted_ids.update(admitted)
        return admitted

    def state_projection_key(self, state: Any) -> tuple[tuple[str, bool], ...]:
        return tuple(
            (
                row.hypothesis_id,
                bool(row.predicate(state)),
            )
            for row in self.state_hypotheses
            if row.hypothesis_id not in self.refuted_ids
        )

    def edge_projection_key(
        self,
        source: Any,
        operation: Hashable,
        outcome: Any,
    ) -> tuple[tuple[str, bool], ...]:
        return tuple(
            (
                row.hypothesis_id,
                bool(row.predicate(source, operation, outcome)),
            )
            for row in self.edge_hypotheses
            if row.hypothesis_id not in self.refuted_ids
        )


@dataclass(frozen=True)
class RelationalTaskPullback:
    """Finite receipt for a terminal edge condition pulled through a word."""

    hypothesis_id: str
    preparation: tuple[Hashable, ...]
    probe_operation: Hashable
    modality: PullbackModality
    initial_sources: tuple[Hashable, ...]
    layers: tuple[dict[str, Any], ...]
    schema: str = "ztare-relational-task-pullback-v1"

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_receipt())

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "hypothesis_id": self.hypothesis_id,
            "preparation": list(map(repr, self.preparation)),
            "probe_operation": repr(self.probe_operation),
            "modality": self.modality,
            "initial_source_sha256s": [
                stable_sha256(source) for source in self.initial_sources
            ],
            "layers": list(self.layers),
        }


def pullback_edge_hypothesis(
    hypothesis: EdgeTaskHypothesis,
    *,
    relation_targets: Mapping[
        tuple[Hashable, Hashable],
        Iterable[Hashable],
    ],
    preparation: Iterable[Hashable],
    probe_operation: Hashable,
    candidate_sources: Iterable[Hashable] = (),
    modality: PullbackModality = "must",
) -> RelationalTaskPullback:
    """Pull one edge predicate backward through a finite action relation.

    For ``must``, ``Pre_a(X)`` contains a source exactly when it has at least
    one witnessed ``a`` successor and every such successor lies in ``X``.
    For ``may``, one successor in ``X`` is sufficient.  The terminal layer
    applies the same modality to outcomes of ``probe_operation`` that satisfy
    the edge predicate.
    """
    if modality not in {"may", "must"}:
        raise ValueError("pullback modality must be 'may' or 'must'")

    word = tuple(preparation)
    normalized = {
        key: frozenset(values)
        for key, values in relation_targets.items()
    }
    universe = {
        source for source, _operation in normalized
    }
    universe.update(
        target
        for targets in normalized.values()
        for target in targets
    )
    requested = tuple(dict.fromkeys(candidate_sources))
    universe.update(requested)

    def admitted(flags: Iterable[bool]) -> bool:
        values = tuple(flags)
        return bool(values) and (
            any(values) if modality == "may" else all(values)
        )

    terminal = {
        source
        for source in universe
        if admitted(
            hypothesis.predicate(source, probe_operation, outcome)
            for outcome in normalized.get(
                (source, probe_operation),
                frozenset(),
            )
        )
    }
    layers: list[dict[str, Any]] = [{
        "kind": "terminal_edge",
        "operation": repr(probe_operation),
        "accepted_source_sha256s": sorted(
            stable_sha256(source) for source in terminal
        ),
    }]
    accepted = terminal
    for operation in reversed(word):
        accepted = {
            source
            for source in universe
            if admitted(
                target in accepted
                for target in normalized.get(
                    (source, operation),
                    frozenset(),
                )
            )
        }
        layers.append({
            "kind": "relational_preimage",
            "operation": repr(operation),
            "accepted_source_sha256s": sorted(
                stable_sha256(source) for source in accepted
            ),
        })

    selected = (
        tuple(source for source in requested if source in accepted)
        if requested
        else tuple(sorted(accepted, key=stable_sha256))
    )
    return RelationalTaskPullback(
        hypothesis_id=hypothesis.hypothesis_id,
        preparation=word,
        probe_operation=probe_operation,
        modality=modality,
        initial_sources=selected,
        layers=tuple(layers),
    )


__all__ = [
    "EdgeTaskHypothesis",
    "RelationalTaskPullback",
    "StateTaskHypothesis",
    "TaskHypothesisVersionSpace",
    "pullback_edge_hypothesis",
]
