"""Task-conditioned reachability over evidence-owned partial actions.

The governing object is a predicate transformer, not a presentation of state.
An edge-valued task relation seeds two backward fixed points:

* ``may`` admits a source when some witnessed image can reach the task edge;
* ``must`` admits a source when one operation has witnessed images, no typed
  boundary alternative, and every witnessed image can reach the task edge.

The interval keeps partiality visible.  It does not infer task success, invent
missing images, or claim that witnessed outcomes exhaust an environment.
Callers own task authority and any model used to propose images for a missing
source-operation pair.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Hashable, Iterable, Literal

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import PartialActionSystem


Modality = Literal["may", "must"]
PredictedTargets = Callable[
    [Hashable, Hashable],
    Iterable[Hashable],
]


def _stable(values: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(
        values,
        key=lambda value: (stable_sha256(value), repr(value)),
    ))


@dataclass(frozen=True)
class TaskRelationEdge:
    """One evidence-scoped candidate task morphism."""

    source: Hashable
    operation: Hashable
    hypothesis_id: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not str(self.hypothesis_id).strip():
            raise ValueError("task relation edges require hypothesis_id")
        if not self.evidence_refs:
            raise ValueError("task relation edges require evidence lineage")

    def to_receipt(self) -> dict:
        return {
            "source_sha256": stable_sha256(self.source),
            "operation": repr(self.operation),
            "hypothesis_id": self.hypothesis_id,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class PredicateTransformerStep:
    """One selected predecessor witness whose targets have lower rank."""

    source: Hashable
    operation: Hashable
    targets: tuple[Hashable, ...]
    depth: int
    modality: Modality


@dataclass(frozen=True)
class TaskConditionedRoute:
    """A preparation followed by one candidate task edge."""

    status: str
    modality: Modality
    preparation: tuple[Hashable, ...] = ()
    probe_operation: Hashable | None = None
    source_path: tuple[Hashable, ...] = ()
    feedback_required: bool = False
    task_hypothesis_id: str = ""

    @property
    def actions(self) -> tuple[Hashable, ...]:
        if self.probe_operation is None:
            return self.preparation
        return (*self.preparation, self.probe_operation)

    def to_receipt(self) -> dict:
        return {
            "status": self.status,
            "modality": self.modality,
            "preparation": [repr(value) for value in self.preparation],
            "probe_operation": (
                repr(self.probe_operation)
                if self.probe_operation is not None
                else None
            ),
            "action_count": len(self.actions),
            "source_path_sha256s": [
                stable_sha256(value) for value in self.source_path
            ],
            "feedback_required": self.feedback_required,
            "task_hypothesis_id": self.task_hypothesis_id,
        }


@dataclass(frozen=True)
class TaskChangingFrontier:
    """A reachable missing relation with a model-proposed basin image."""

    source: Hashable
    operation: Hashable
    preparation: tuple[Hashable, ...]
    predicted_targets: tuple[Hashable, ...]
    gain_kind: str
    target_depth: int

    @property
    def actions(self) -> tuple[Hashable, ...]:
        return (*self.preparation, self.operation)

    def to_receipt(self) -> dict:
        return {
            "source_sha256": stable_sha256(self.source),
            "operation": repr(self.operation),
            "preparation": [repr(value) for value in self.preparation],
            "action_count": len(self.actions),
            "predicted_target_sha256s": [
                stable_sha256(value) for value in self.predicted_targets
            ],
            "gain_kind": self.gain_kind,
            "target_depth": self.target_depth,
        }


@dataclass(frozen=True)
class TaskConditionedAcquisitionPlan:
    """One task route or a finite task-changing acquisition cut."""

    status: str
    route: TaskConditionedRoute | None = None
    selected_frontier: TaskChangingFrontier | None = None
    task_changing_frontier: tuple[TaskChangingFrontier, ...] = ()
    reachable_source_count: int = 0
    missing_pair_count: int = 0
    schema: str = "ztare-task-conditioned-acquisition-plan-v1"

    def to_receipt(self) -> dict:
        return {
            "schema": self.schema,
            "status": self.status,
            "route": self.route.to_receipt() if self.route else None,
            "selected_frontier": (
                self.selected_frontier.to_receipt()
                if self.selected_frontier else None
            ),
            "task_changing_frontier": [
                row.to_receipt() for row in self.task_changing_frontier
            ],
            "reachable_source_count": self.reachable_source_count,
            "missing_pair_count": self.missing_pair_count,
        }


@dataclass(frozen=True)
class TaskReachabilityBasin:
    """The fixed-point interval induced by one task relation."""

    source_system: PartialActionSystem = field(compare=False, repr=False)
    task_relation_sha256: str
    operations: tuple[Hashable, ...]
    task_edges: tuple[TaskRelationEdge, ...]
    may_sources: frozenset[Hashable]
    must_sources: frozenset[Hashable]
    may_depth: dict[Hashable, int] = field(compare=False, repr=False)
    must_depth: dict[Hashable, int] = field(compare=False, repr=False)
    may_policy: dict[Hashable, PredicateTransformerStep] = field(
        compare=False,
        repr=False,
    )
    must_policy: dict[Hashable, PredicateTransformerStep] = field(
        compare=False,
        repr=False,
    )
    decision_class_by_source: dict[Hashable, str] = field(
        compare=False,
        repr=False,
    )
    iteration_count: int = 0
    schema: str = "ztare-task-reachability-basin-v1"

    @property
    def source_system_sha256(self) -> str:
        return self.source_system.sha256

    @property
    def interval_sources(self) -> frozenset[Hashable]:
        return self.may_sources - self.must_sources

    @property
    def decision_class_count(self) -> int:
        return len(set(self.decision_class_by_source.values()))

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_receipt())

    def route_from(
        self,
        source: Hashable,
        *,
        modality: Modality = "must",
    ) -> TaskConditionedRoute:
        admitted = (
            self.must_sources if modality == "must" else self.may_sources
        )
        policy = self.must_policy if modality == "must" else self.may_policy
        depth = self.must_depth if modality == "must" else self.may_depth
        if source not in admitted:
            return TaskConditionedRoute(
                status="outside_basin",
                modality=modality,
            )
        task_by_source: dict[Hashable, list[TaskRelationEdge]] = defaultdict(list)
        for edge in self.task_edges:
            task_by_source[edge.source].append(edge)
        cursor = source
        preparation: list[Hashable] = []
        path = [cursor]
        feedback_required = False
        while cursor not in task_by_source:
            step = policy.get(cursor)
            if step is None:
                return TaskConditionedRoute(
                    status="policy_incomplete",
                    modality=modality,
                    preparation=tuple(preparation),
                    source_path=tuple(path),
                )
            candidates = tuple(
                target
                for target in step.targets
                if target in admitted and depth[target] < depth[cursor]
            )
            if not candidates:
                return TaskConditionedRoute(
                    status="policy_non_decreasing",
                    modality=modality,
                    preparation=tuple(preparation),
                    source_path=tuple(path),
                )
            feedback_required = feedback_required or len(candidates) > 1
            cursor = min(
                candidates,
                key=lambda value: (
                    depth[value],
                    stable_sha256(value),
                    repr(value),
                ),
            )
            preparation.append(step.operation)
            path.append(cursor)
        edge = min(
            task_by_source[cursor],
            key=lambda row: (
                repr(row.operation),
                row.hypothesis_id,
                stable_sha256(row.source),
            ),
        )
        return TaskConditionedRoute(
            status="route_found",
            modality=modality,
            preparation=tuple(preparation),
            probe_operation=edge.operation,
            source_path=tuple(path),
            feedback_required=feedback_required,
            task_hypothesis_id=edge.hypothesis_id,
        )

    def to_receipt(self, *, source_cap: int = 200) -> dict:
        classes: dict[str, list[str]] = defaultdict(list)
        for source, class_id in self.decision_class_by_source.items():
            classes[class_id].append(stable_sha256(source))
        class_rows = [
            {
                "class_id": class_id,
                "member_count": len(members),
                "member_sha256s": sorted(members)[:source_cap],
            }
            for class_id, members in sorted(classes.items())
        ]
        return {
            "schema": self.schema,
            "source_system_sha256": self.source_system_sha256,
            "task_relation_sha256": self.task_relation_sha256,
            "operations": [repr(value) for value in self.operations],
            "task_edges": [edge.to_receipt() for edge in self.task_edges],
            "source_count": len(self.source_system.fibers),
            "may_source_count": len(self.may_sources),
            "must_source_count": len(self.must_sources),
            "interval_source_count": len(self.interval_sources),
            "may_source_sha256s": sorted(
                stable_sha256(value) for value in self.may_sources
            )[:source_cap],
            "must_source_sha256s": sorted(
                stable_sha256(value) for value in self.must_sources
            )[:source_cap],
            "interval_source_sha256s": sorted(
                stable_sha256(value) for value in self.interval_sources
            )[:source_cap],
            "iteration_count": self.iteration_count,
            "decision_class_count": self.decision_class_count,
            "decision_classes": class_rows,
        }


def _has_boundary(
    system: PartialActionSystem,
    operation: Hashable,
    effects: Iterable[Hashable],
) -> bool:
    return any(
        (operation, effect) in system.boundary_kinds
        for effect in effects
    )


def _action_signature(
    system: PartialActionSystem,
    *,
    source: Hashable,
    operation: Hashable,
    may_sources: frozenset[Hashable],
    must_sources: frozenset[Hashable],
) -> tuple[str, bool, bool]:
    key = source, operation
    effects = system.relation_effects.get(key)
    targets = system.relation_targets.get(key, frozenset())
    if effects is None:
        return "unknown", False, False
    may = any(target in may_sources for target in targets)
    must = bool(targets) and not _has_boundary(
        system,
        operation,
        effects,
    ) and all(target in must_sources for target in targets)
    return "observed", may, must


def compile_task_reachability_basin(
    system: PartialActionSystem,
    *,
    task_edges: Iterable[TaskRelationEdge],
    task_relation_sha256: str,
    operations: Iterable[Hashable],
) -> TaskReachabilityBasin:
    """Compile the least may/must predecessor fixed points."""

    if not str(task_relation_sha256).strip():
        raise ValueError("task_relation_sha256 is required")
    operation_set = tuple(dict.fromkeys(operations))
    edges = tuple(sorted(
        task_edges,
        key=lambda row: (
            stable_sha256(row.source),
            repr(row.operation),
            row.hypothesis_id,
        ),
    ))
    if not edges:
        raise ValueError("at least one task relation edge is required")
    unknown_sources = {
        edge.source for edge in edges if edge.source not in system.fibers
    }
    if unknown_sources:
        raise ValueError("task relation edge source lacks an evidence fiber")

    terminal_sources = frozenset(edge.source for edge in edges)
    may = set(terminal_sources)
    must = set(terminal_sources)
    may_depth = {source: 0 for source in terminal_sources}
    must_depth = {source: 0 for source in terminal_sources}
    may_policy: dict[Hashable, PredicateTransformerStep] = {}
    must_policy: dict[Hashable, PredicateTransformerStep] = {}
    iteration_count = 0

    while True:
        iteration_count += 1
        new_may: dict[Hashable, PredicateTransformerStep] = {}
        new_must: dict[Hashable, PredicateTransformerStep] = {}
        for source in _stable(system.fibers):
            if source not in may:
                candidates = []
                for operation in operation_set:
                    targets = system.relation_targets.get(
                        (source, operation),
                        frozenset(),
                    )
                    admitted = tuple(target for target in targets if target in may)
                    if admitted:
                        candidates.append((operation, targets, admitted))
                if candidates:
                    operation, targets, admitted = min(
                        candidates,
                        key=lambda row: (
                            min(may_depth[target] for target in row[2]),
                            repr(row[0]),
                            stable_sha256(source),
                        ),
                    )
                    new_may[source] = PredicateTransformerStep(
                        source=source,
                        operation=operation,
                        targets=_stable(targets),
                        depth=1 + min(
                            may_depth[target] for target in admitted
                        ),
                        modality="may",
                    )
            if source not in must:
                candidates = []
                for operation in operation_set:
                    key = source, operation
                    effects = system.relation_effects.get(key)
                    targets = system.relation_targets.get(key, frozenset())
                    if (
                        effects
                        and targets
                        and not _has_boundary(system, operation, effects)
                        and all(target in must for target in targets)
                    ):
                        candidates.append((operation, targets))
                if candidates:
                    operation, targets = min(
                        candidates,
                        key=lambda row: (
                            max(must_depth[target] for target in row[1]),
                            repr(row[0]),
                            stable_sha256(source),
                        ),
                    )
                    new_must[source] = PredicateTransformerStep(
                        source=source,
                        operation=operation,
                        targets=_stable(targets),
                        depth=1 + max(
                            must_depth[target] for target in targets
                        ),
                        modality="must",
                    )
        if not new_may and not new_must:
            break
        for source, step in new_may.items():
            may.add(source)
            may_depth[source] = step.depth
            may_policy[source] = step
        for source, step in new_must.items():
            must.add(source)
            must_depth[source] = step.depth
            must_policy[source] = step
        if iteration_count > len(system.fibers) + 1:
            raise RuntimeError("task predecessor fixed point did not stabilize")

    frozen_may = frozenset(may)
    frozen_must = frozenset(must)
    if not frozen_must <= frozen_may:
        raise RuntimeError("must predecessor escaped the may predecessor")
    task_operations: dict[Hashable, set[Hashable]] = defaultdict(set)
    for edge in edges:
        task_operations[edge.source].add(edge.operation)
    class_by_source = {}
    for source in _stable(system.fibers):
        signature = (
            _stable(task_operations.get(source, ())),
            tuple(
                (
                    operation,
                    _action_signature(
                        system,
                        source=source,
                        operation=operation,
                        may_sources=frozen_may,
                        must_sources=frozen_must,
                    ),
                )
                for operation in operation_set
            ),
        )
        class_by_source[source] = stable_sha256({
            "task_relation_sha256": task_relation_sha256,
            "decision_signature": signature,
        })
    return TaskReachabilityBasin(
        source_system=system,
        task_relation_sha256=task_relation_sha256,
        operations=operation_set,
        task_edges=edges,
        may_sources=frozen_may,
        must_sources=frozen_must,
        may_depth=may_depth,
        must_depth=must_depth,
        may_policy=may_policy,
        must_policy=must_policy,
        decision_class_by_source=class_by_source,
        iteration_count=iteration_count,
    )


def plan_task_conditioned_acquisition(
    basin: TaskReachabilityBasin,
    *,
    start_source: Hashable,
    predict_targets: PredictedTargets | None = None,
) -> TaskConditionedAcquisitionPlan:
    """Join forward witnessed control with the backward task basin."""

    system = basin.source_system
    if start_source not in system.fibers:
        return TaskConditionedAcquisitionPlan(status="start_source_unknown")
    for modality in ("must", "may"):
        route = basin.route_from(start_source, modality=modality)
        if route.status == "route_found":
            return TaskConditionedAcquisitionPlan(
                status=f"{modality}_task_route",
                route=route,
                reachable_source_count=1,
            )

    predecessor: dict[
        Hashable,
        tuple[Hashable, Hashable] | None,
    ] = {start_source: None}
    queue = deque((start_source,))
    while queue:
        source = queue.popleft()
        for operation in basin.operations:
            key = source, operation
            effects = system.relation_effects.get(key)
            targets = system.relation_targets.get(key, frozenset())
            if (
                not effects
                or len(targets) != 1
                or _has_boundary(system, operation, effects)
            ):
                continue
            target = next(iter(targets))
            if target not in predecessor:
                predecessor[target] = source, operation
                queue.append(target)

    def path_to(source: Hashable) -> tuple[Hashable, ...]:
        actions = []
        cursor = source
        while predecessor[cursor] is not None:
            parent, operation = predecessor[cursor]  # type: ignore[misc]
            actions.append(operation)
            cursor = parent
        actions.reverse()
        return tuple(actions)

    missing_pairs = [
        (source, operation)
        for source in _stable(predecessor)
        for operation in basin.operations
        if (source, operation) not in system.relation_effects
    ]
    candidates = []
    if predict_targets is not None:
        for source, operation in missing_pairs:
            predicted = _stable(
                target
                for target in predict_targets(source, operation)
                if target in system.fibers
            )
            if not predicted:
                continue
            must_images = tuple(
                target for target in predicted
                if target in basin.must_sources
            )
            may_images = tuple(
                target for target in predicted
                if target in basin.may_sources
            )
            if predicted and len(must_images) == len(predicted):
                kind = "must_basin_bridge"
                depth = max(basin.must_depth[target] for target in must_images)
            elif may_images:
                kind = "may_basin_bridge"
                depth = min(basin.may_depth[target] for target in may_images)
            else:
                continue
            candidates.append(TaskChangingFrontier(
                source=source,
                operation=operation,
                preparation=path_to(source),
                predicted_targets=predicted,
                gain_kind=kind,
                target_depth=depth,
            ))
    candidates.sort(key=lambda row: (
        0 if row.gain_kind == "must_basin_bridge" else 1,
        len(row.preparation),
        row.target_depth,
        stable_sha256(row.source),
        repr(row.operation),
    ))
    return TaskConditionedAcquisitionPlan(
        status=(
            "task_changing_frontier_found"
            if candidates
            else "outside_observed_task_basin"
        ),
        selected_frontier=candidates[0] if candidates else None,
        task_changing_frontier=tuple(candidates),
        reachable_source_count=len(predecessor),
        missing_pair_count=len(missing_pairs),
    )


__all__ = [
    "PredicateTransformerStep",
    "TaskChangingFrontier",
    "TaskConditionedAcquisitionPlan",
    "TaskConditionedRoute",
    "TaskReachabilityBasin",
    "TaskRelationEdge",
    "compile_task_reachability_basin",
    "plan_task_conditioned_acquisition",
]
