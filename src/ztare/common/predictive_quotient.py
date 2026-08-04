"""Boundary-aware predictive quotients of witnessed partial action systems.

The source object is an evidence-backed partial Mealy system. Two witnessed
source fibers are identified only when partition refinement cannot distinguish
them by any admitted operation/effect/boundary test. Unknown operations remain
observable outcomes, so compression never turns missing evidence into a law.

The quotient retains a concrete source-fiber section and can surface reusable
options as deterministic paths shared by more than one witnessed source.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Hashable, Iterable

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    ObservedFrontierPlan,
    PartialActionSystem,
)


def _stable(values: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(values, key=stable_sha256))


def _relation_signature(
    system: PartialActionSystem,
    source_key: Hashable,
    operation: Hashable,
    colors: dict[Hashable, int],
) -> tuple[Hashable, ...]:
    relation_key = source_key, operation
    effects = system.relation_effects.get(relation_key)
    targets = system.relation_targets.get(relation_key)
    if effects is None and targets is None:
        return ("unknown",)
    effect_rows = _stable(effects or ())
    target_colors = tuple(sorted({
        colors[target]
        for target in (targets or ())
    }))
    return (
        "observed",
        effect_rows,
        target_colors,
    )


def _partition(colors: dict[Hashable, int]) -> frozenset[frozenset[Hashable]]:
    groups: dict[int, set[Hashable]] = defaultdict(set)
    for source, color in colors.items():
        groups[color].add(source)
    return frozenset(frozenset(group) for group in groups.values())


@dataclass(frozen=True)
class PredictiveOption:
    """One deterministic quotient path reusable across source witnesses."""

    initiation_class: str
    operations: tuple[Hashable, ...]
    termination_class: str
    initiation_support: int
    evidence_refs: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        return {
            "initiation_class": self.initiation_class,
            "operations": [repr(operation) for operation in self.operations],
            "termination_class": self.termination_class,
            "initiation_support": self.initiation_support,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class OperationOrbitCompletion:
    """An unknown operation beside a repeated local consequence signature."""

    orbit_kind: str
    source_class: str
    witnessed_operations: tuple[Hashable, ...]
    query_operations: tuple[Hashable, ...]
    effect_sha256s: tuple[str, ...]
    target_classes: tuple[str, ...]
    source_support: int
    evidence_refs: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        return {
            "orbit_kind": self.orbit_kind,
            "source_class": self.source_class,
            "witnessed_operations": [
                repr(operation) for operation in self.witnessed_operations
            ],
            "query_operations": [
                repr(operation) for operation in self.query_operations
            ],
            "effect_sha256s": list(self.effect_sha256s),
            "target_classes": list(self.target_classes),
            "source_support": self.source_support,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class PredictiveIncompatibility:
    """One concrete refutation of predictive compatibility."""

    left_source: Hashable
    right_source: Hashable
    operation: Hashable
    kind: str
    left_effects: tuple[Hashable, ...] = ()
    right_effects: tuple[Hashable, ...] = ()
    left_targets: tuple[Hashable, ...] = ()
    right_targets: tuple[Hashable, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        return {
            "left_source_sha256": stable_sha256(self.left_source),
            "right_source_sha256": stable_sha256(self.right_source),
            "operation": repr(self.operation),
            "kind": self.kind,
            "left_effect_sha256s": [
                stable_sha256(effect) for effect in self.left_effects
            ],
            "right_effect_sha256s": [
                stable_sha256(effect) for effect in self.right_effects
            ],
            "left_target_sha256s": [
                stable_sha256(target) for target in self.left_targets
            ],
            "right_target_sha256s": [
                stable_sha256(target) for target in self.right_targets
            ],
        }


@dataclass(frozen=True)
class PredictiveSupportGap:
    """A test witnessed on one compatible source and absent on another."""

    tested_source: Hashable
    untested_source: Hashable
    operation: Hashable
    effects: tuple[Hashable, ...]
    targets: tuple[Hashable, ...]
    joint_operations: tuple[Hashable, ...]
    tested_evidence_ref: str
    untested_evidence_ref: str

    def to_receipt(self) -> dict[str, Any]:
        return {
            "tested_source_sha256": stable_sha256(self.tested_source),
            "untested_source_sha256": stable_sha256(self.untested_source),
            "operation": repr(self.operation),
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effects
            ],
            "target_sha256s": [
                stable_sha256(target) for target in self.targets
            ],
            "joint_test_count": len(self.joint_operations),
            "joint_operations": [
                repr(operation) for operation in self.joint_operations
            ],
            "tested_evidence_ref": self.tested_evidence_ref,
            "untested_evidence_ref": self.untested_evidence_ref,
        }


@dataclass(frozen=True)
class PredictiveSupportPlan:
    """A concrete route to one supported, consumer-indexed test gap."""

    status: str
    actions: tuple[Hashable, ...] = ()
    target_operation: Hashable | None = None
    tested_source_sha256: str = ""
    untested_source_sha256: str = ""
    joint_operations: tuple[Hashable, ...] = ()
    effect_sha256s: tuple[str, ...] = ()
    tested_evidence_ref: str = ""
    untested_evidence_ref: str = ""
    depth: int = 0
    exceptional_score: float = 0.0
    reachable_nodes: int = 0
    support_gap_count: int = 0
    schema: str = "ztare-predictive-support-frontier-plan-v1"

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "action_count": len(self.actions),
            "actions": [repr(action) for action in self.actions],
            "target_operation": repr(self.target_operation),
            "tested_source_sha256": self.tested_source_sha256,
            "untested_source_sha256": self.untested_source_sha256,
            "joint_test_count": len(self.joint_operations),
            "joint_operations": [
                repr(operation) for operation in self.joint_operations
            ],
            "effect_sha256s": list(self.effect_sha256s),
            "tested_evidence_ref": self.tested_evidence_ref,
            "untested_evidence_ref": self.untested_evidence_ref,
            "depth": self.depth,
            "exceptional_score": self.exceptional_score,
            "reachable_nodes": self.reachable_nodes,
            "support_gap_count": self.support_gap_count,
        }


def _source_pair(
    left: Hashable,
    right: Hashable,
) -> tuple[Hashable, Hashable]:
    left_order = stable_sha256(left), repr(left)
    right_order = stable_sha256(right), repr(right)
    return (left, right) if left_order <= right_order else (right, left)


@dataclass
class PredictiveCompatibility:
    """Partial behavioral compatibility with evidence support kept separate.

    Compatibility is the greatest fixed point surviving every jointly
    witnessed operation/effect/boundary test. An operation missing on either
    member supplies no behavioral result; it becomes a support gap.
    """

    source_system_sha256: str
    operations: tuple[Hashable, ...]
    sources: tuple[Hashable, ...]
    compatible_pairs: frozenset[tuple[Hashable, Hashable]]
    incompatibilities: tuple[PredictiveIncompatibility, ...]
    support_gaps: tuple[PredictiveSupportGap, ...]
    refinement_rounds: int
    schema: str = "ztare-predictive-compatibility-v1"

    def is_compatible(self, left: Hashable, right: Hashable) -> bool:
        return _source_pair(left, right) in self.compatible_pairs

    def pair_receipt(
        self,
        left: Hashable,
        right: Hashable,
    ) -> dict[str, Any]:
        pair = _source_pair(left, right)
        refutation = next(
            (
                row for row in self.incompatibilities
                if _source_pair(
                    row.left_source,
                    row.right_source,
                ) == pair
            ),
            None,
        )
        gaps = [
            row.to_receipt()
            for row in self.support_gaps
            if _source_pair(
                row.tested_source,
                row.untested_source,
            ) == pair
        ]
        return {
            "left_source_sha256": stable_sha256(left),
            "right_source_sha256": stable_sha256(right),
            "compatible": pair in self.compatible_pairs,
            "refutation": (
                refutation.to_receipt()
                if refutation is not None
                else None
            ),
            "support_gap_count": len(gaps),
            "support_gaps": gaps,
        }

    def to_receipt(
        self,
        *,
        incompatibility_cap: int = 80,
        support_gap_cap: int = 80,
    ) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_system_sha256": self.source_system_sha256,
            "operations": [
                repr(operation) for operation in self.operations
            ],
            "source_count": len(self.sources),
            "compatible_pair_count": len(self.compatible_pairs),
            "distinct_compatible_pair_count": sum(
                1 for left, right in self.compatible_pairs
                if left != right
            ),
            "incompatibility_count": len(self.incompatibilities),
            "support_gap_count": len(self.support_gaps),
            "refinement_rounds": self.refinement_rounds,
            "incompatibilities": [
                row.to_receipt()
                for row in self.incompatibilities[:incompatibility_cap]
            ],
            "support_gaps": [
                row.to_receipt()
                for row in self.support_gaps[:support_gap_cap]
            ],
        }


@dataclass
class PredictiveQuotient:
    """Stable partition, transported relation, section, and option surface."""

    source_system_sha256: str
    operations: tuple[Hashable, ...]
    class_by_source: dict[Hashable, str]
    members_by_class: dict[str, tuple[Hashable, ...]]
    section_by_class: dict[str, Hashable]
    relation_effects: dict[
        tuple[str, Hashable],
        frozenset[Hashable],
    ]
    relation_targets: dict[
        tuple[str, Hashable],
        frozenset[str],
    ]
    boundary_classes: frozenset[tuple[Hashable, Hashable]]
    options: tuple[PredictiveOption, ...]
    orbit_completions: tuple[OperationOrbitCompletion, ...]
    refinement_rounds: int
    section_failures: tuple[dict[str, Any], ...] = ()
    transport_failures: tuple[dict[str, Any], ...] = ()
    schema: str = "ztare-boundary-predictive-quotient-v1"

    @property
    def passed_section(self) -> bool:
        return not self.section_failures

    @property
    def passed_transport(self) -> bool:
        return not self.transport_failures

    @property
    def class_count(self) -> int:
        return len(self.members_by_class)

    @property
    def source_fiber_count(self) -> int:
        return len(self.class_by_source)

    @property
    def compressed(self) -> bool:
        return self.class_count < self.source_fiber_count

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_receipt())

    def class_for_source(self, source_key: Hashable) -> str:
        try:
            return self.class_by_source[source_key]
        except KeyError as exc:
            raise KeyError(
                "source fiber has no witnessed predictive class"
            ) from exc

    def to_receipt(
        self,
        *,
        option_cap: int = 30,
        class_cap: int | None = None,
    ) -> dict[str, Any]:
        classes = []
        for class_id, members in sorted(self.members_by_class.items()):
            classes.append({
                "class_id": class_id,
                "member_count": len(members),
                "member_sha256s": sorted(
                    stable_sha256(member) for member in members
                ),
                "section_source_sha256": stable_sha256(
                    self.section_by_class[class_id]
                ),
            })
        return {
            "schema": self.schema,
            "source_system_sha256": self.source_system_sha256,
            "operations": [repr(operation) for operation in self.operations],
            "source_fiber_count": self.source_fiber_count,
            "class_count": self.class_count,
            "compressed": self.compressed,
            "compression_ratio": (
                self.class_count / max(1, self.source_fiber_count)
            ),
            "refinement_rounds": self.refinement_rounds,
            "relation_count": len(self.relation_effects),
            "noncommuting_relation_count": sum(
                1
                for effects in self.relation_effects.values()
                if len(effects) > 1
            ),
            "boundary_relation_count": sum(
                1
                for (class_id, operation), effects
                in self.relation_effects.items()
                if any(
                    (operation, effect) in self.boundary_classes
                    for effect in effects
                )
            ),
            "section": {
                "status": "pass" if self.passed_section else "fail",
                "failures": list(self.section_failures),
            },
            "transport": {
                "status": "pass" if self.passed_transport else "fail",
                "failures": list(self.transport_failures),
            },
            "classes": (
                classes
                if class_cap is None
                else classes[:max(0, int(class_cap))]
            ),
            "option_count": len(self.options),
            "options": [
                option.to_receipt() for option in self.options[:option_cap]
            ],
            "orbit_completion_count": len(self.orbit_completions),
            "orbit_completions": [
                experiment.to_receipt()
                for experiment in self.orbit_completions[:option_cap]
            ],
        }


def _discover_options(
    *,
    system: PartialActionSystem,
    operations: tuple[Hashable, ...],
    members_by_class: dict[str, tuple[Hashable, ...]],
    relation_effects: dict[
        tuple[str, Hashable],
        frozenset[Hashable],
    ],
    relation_targets: dict[
        tuple[str, Hashable],
        frozenset[str],
    ],
    boundary_classes: frozenset[tuple[Hashable, Hashable]],
    max_length: int,
) -> tuple[PredictiveOption, ...]:
    options: list[PredictiveOption] = []
    seen: set[tuple[str, tuple[Hashable, ...], str]] = set()
    for initiation_class, members in members_by_class.items():
        if len(members) < 2:
            continue
        evidence_refs = tuple(sorted({
            system.fibers[member].evidence_ref
            for member in members
        }))
        stack = [(initiation_class, (), frozenset({initiation_class}))]
        while stack:
            class_id, path, visited = stack.pop()
            if len(path) >= max_length:
                continue
            for operation in operations:
                relation_key = class_id, operation
                effects = relation_effects.get(relation_key, ())
                targets = relation_targets.get(relation_key, ())
                if (
                    len(effects) != 1
                    or len(targets) != 1
                    or any(
                        (operation, effect) in boundary_classes
                        for effect in effects
                    )
                ):
                    continue
                target = next(iter(targets))
                next_path = (*path, operation)
                if len(next_path) >= 2:
                    identity = initiation_class, next_path, target
                    if identity not in seen:
                        seen.add(identity)
                        options.append(PredictiveOption(
                            initiation_class=initiation_class,
                            operations=next_path,
                            termination_class=target,
                            initiation_support=len(members),
                            evidence_refs=evidence_refs,
                        ))
                if target not in visited:
                    stack.append((
                        target,
                        next_path,
                        visited | {target},
                    ))
    options.sort(key=lambda option: (
        -option.initiation_support,
        -len(option.operations),
        option.initiation_class,
        tuple(map(repr, option.operations)),
        option.termination_class,
    ))
    return tuple(options)


def _discover_orbit_completions(
    *,
    system: PartialActionSystem,
    operations: tuple[Hashable, ...],
    members_by_class: dict[str, tuple[Hashable, ...]],
    relation_effects: dict[
        tuple[str, Hashable],
        frozenset[Hashable],
    ],
    relation_targets: dict[
        tuple[str, Hashable],
        frozenset[str],
    ],
    boundary_classes: frozenset[tuple[Hashable, Hashable]],
) -> tuple[OperationOrbitCompletion, ...]:
    experiments = []
    for class_id, members in members_by_class.items():
        signatures: dict[
            tuple[str, ...],
            list[tuple[Hashable, Hashable]],
        ] = defaultdict(list)
        unknown = []
        for operation in operations:
            relation_key = class_id, operation
            effects = relation_effects.get(relation_key)
            if effects is None:
                unknown.append(operation)
                continue
            targets = relation_targets.get(relation_key, ())
            if (
                len(effects) != 1
                or len(targets) != 1
                or any(
                    (operation, effect) in boundary_classes
                    for effect in effects
                )
            ):
                continue
            signatures[tuple(sorted(targets))].append((
                operation,
                next(iter(effects)),
            ))
        if not unknown:
            continue
        for targets, witnessed_rows in signatures.items():
            if len(witnessed_rows) < 2:
                continue
            witnessed = [row[0] for row in witnessed_rows]
            effects = [row[1] for row in witnessed_rows]
            refs = set()
            for operation, effect in witnessed_rows:
                refs.update(
                    system.effect_evidence_refs.get(
                        (operation, effect),
                        (),
                    )
                )
            experiments.append(OperationOrbitCompletion(
                orbit_kind="shared_predictive_target",
                source_class=class_id,
                witnessed_operations=_stable(witnessed),
                query_operations=_stable(unknown),
                effect_sha256s=tuple(sorted(
                    stable_sha256(effect) for effect in effects
                )),
                target_classes=targets,
                source_support=len(members),
                evidence_refs=tuple(sorted(refs)),
            ))
    experiments.sort(key=lambda experiment: (
        -len(experiment.witnessed_operations),
        -experiment.source_support,
        experiment.source_class,
        tuple(map(repr, experiment.query_operations)),
    ))
    return tuple(experiments)


def compile_predictive_compatibility(
    system: PartialActionSystem,
    *,
    operations: Iterable[Hashable],
) -> PredictiveCompatibility:
    """Compile definite behavioral conflicts and asymmetric support.

    This is intentionally a relation, not a partition: compatibility under
    partial tests need not be transitive. A source with an untested operation
    can remain compatible with multiple mutually incompatible completions.
    """
    operation_set = tuple(dict.fromkeys(operations))
    sources = _stable(system.fibers)
    compatible = {
        _source_pair(left, right)
        for left_index, left in enumerate(sources)
        for right in sources[left_index:]
    }
    refutations: dict[
        tuple[Hashable, Hashable],
        PredictiveIncompatibility,
    ] = {}
    refinement_rounds = 0

    for round_index in range(max(1, len(sources) + 1)):
        removed: dict[
            tuple[Hashable, Hashable],
            PredictiveIncompatibility,
        ] = {}
        for left, right in tuple(compatible):
            if left == right:
                continue
            for operation in operation_set:
                left_key = left, operation
                right_key = right, operation
                left_effects = system.relation_effects.get(left_key)
                right_effects = system.relation_effects.get(right_key)
                if left_effects is None or right_effects is None:
                    continue
                ordered_left_effects = _stable(left_effects)
                ordered_right_effects = _stable(right_effects)
                if left_effects.isdisjoint(right_effects):
                    removed[(left, right)] = PredictiveIncompatibility(
                        left_source=left,
                        right_source=right,
                        operation=operation,
                        kind="disjoint_jointly_witnessed_effects",
                        left_effects=ordered_left_effects,
                        right_effects=ordered_right_effects,
                    )
                    break
                left_targets = system.relation_targets.get(left_key, ())
                right_targets = system.relation_targets.get(right_key, ())
                if not left_targets or not right_targets:
                    continue
                if not any(
                    _source_pair(left_target, right_target) in compatible
                    for left_target in left_targets
                    for right_target in right_targets
                ):
                    removed[(left, right)] = PredictiveIncompatibility(
                        left_source=left,
                        right_source=right,
                        operation=operation,
                        kind="joint_effect_successors_incompatible",
                        left_effects=ordered_left_effects,
                        right_effects=ordered_right_effects,
                        left_targets=_stable(left_targets),
                        right_targets=_stable(right_targets),
                    )
                    break
        refinement_rounds = round_index + 1
        if not removed:
            break
        for pair, witness in removed.items():
            compatible.discard(pair)
            refutations[pair] = witness

    support_gaps = []
    for left, right in compatible:
        if left == right:
            continue
        joint_operations = tuple(
            operation for operation in operation_set
            if (left, operation) in system.relation_effects
            and (right, operation) in system.relation_effects
        )
        for operation in operation_set:
            left_key = left, operation
            right_key = right, operation
            left_observed = left_key in system.relation_effects
            right_observed = right_key in system.relation_effects
            if left_observed == right_observed:
                continue
            tested = left if left_observed else right
            untested = right if left_observed else left
            tested_key = tested, operation
            support_gaps.append(PredictiveSupportGap(
                tested_source=tested,
                untested_source=untested,
                operation=operation,
                effects=_stable(system.relation_effects[tested_key]),
                targets=_stable(
                    system.relation_targets.get(tested_key, ())
                ),
                joint_operations=joint_operations,
                tested_evidence_ref=system.fibers[tested].evidence_ref,
                untested_evidence_ref=system.fibers[untested].evidence_ref,
            ))
    support_gaps.sort(key=lambda row: (
        -len(row.joint_operations),
        stable_sha256(row.untested_source),
        repr(row.operation),
        stable_sha256(row.tested_source),
    ))
    incompatibilities = tuple(sorted(
        refutations.values(),
        key=lambda row: (
            stable_sha256(row.left_source),
            stable_sha256(row.right_source),
            repr(row.operation),
        ),
    ))
    return PredictiveCompatibility(
        source_system_sha256=system.sha256,
        operations=operation_set,
        sources=sources,
        compatible_pairs=frozenset(compatible),
        incompatibilities=incompatibilities,
        support_gaps=tuple(support_gaps),
        refinement_rounds=refinement_rounds,
    )


def plan_predictive_support_frontier(
    compatibility: PredictiveCompatibility,
    *,
    source_system: PartialActionSystem,
    start_source_key: Hashable,
    operations: Iterable[Hashable],
    max_depth: int = 128,
) -> PredictiveSupportPlan:
    """Route to a reachable consumer-indexed support gap.

    The tested peer supplies experiment value, never a borrowed transition.
    Execution targets only the compatible source whose operation is absent.
    """
    if start_source_key not in source_system.fibers:
        return PredictiveSupportPlan(status="start_fiber_unwitnessed")
    operation_set = tuple(dict.fromkeys(operations))
    allowed_operations = frozenset(operation_set)
    class_scores = {
        row.class_key: row.score
        for row in source_system.ranked
        if not row.boundary_kind
    }
    boundary_classes = frozenset(source_system.boundary_kinds)
    gaps_by_source: dict[
        Hashable,
        list[PredictiveSupportGap],
    ] = defaultdict(list)
    for gap in compatibility.support_gaps:
        if gap.operation in allowed_operations:
            gaps_by_source[gap.untested_source].append(gap)

    queue = [start_source_key]
    predecessor: dict[
        Hashable,
        tuple[Hashable, Hashable] | None,
    ] = {start_source_key: None}
    depth_by_source = {start_source_key: 0}
    candidates: list[
        tuple[int, float, int, str, str, str, PredictiveSupportGap]
    ] = []
    cursor = 0
    while cursor < len(queue):
        source = queue[cursor]
        cursor += 1
        depth = depth_by_source[source]
        for gap in gaps_by_source.get(source, ()):
            score = max(
                (
                    class_scores.get((gap.operation, effect), 0.0)
                    for effect in gap.effects
                ),
                default=0.0,
            )
            candidates.append((
                -len(gap.joint_operations),
                -score,
                depth,
                stable_sha256(source),
                repr(gap.operation),
                stable_sha256(gap.tested_source),
                gap,
            ))
        if depth >= max_depth:
            continue
        for operation in operation_set:
            relation_key = source, operation
            effects = source_system.relation_effects.get(
                relation_key, ()
            )
            targets = source_system.relation_targets.get(
                relation_key, ()
            )
            if (
                len(effects) != 1
                or len(targets) != 1
                or any(
                    (operation, effect) in boundary_classes
                    for effect in effects
                )
            ):
                continue
            target = next(iter(targets))
            if target in predecessor:
                continue
            predecessor[target] = source, operation
            depth_by_source[target] = depth + 1
            queue.append(target)

    if not candidates:
        return PredictiveSupportPlan(
            status="support_frontier_unreachable",
            reachable_nodes=len(predecessor),
            support_gap_count=len(compatibility.support_gaps),
        )
    supported_candidates = [
        row for row in candidates
        if row[0] < 0
    ]
    if not supported_candidates:
        return PredictiveSupportPlan(
            status="support_frontier_unsubstantiated",
            reachable_nodes=len(predecessor),
            support_gap_count=len(compatibility.support_gaps),
        )
    (
        _negative_joint_tests,
        negative_score,
        depth,
        _source_order,
        _operation_order,
        _tested_source_order,
        selected,
    ) = min(supported_candidates)
    path = []
    cursor_source = selected.untested_source
    while predecessor[cursor_source] is not None:
        prior, operation = predecessor[cursor_source]
        path.append(operation)
        cursor_source = prior
    path.reverse()
    path.append(selected.operation)
    return PredictiveSupportPlan(
        status="support_gap_found",
        actions=tuple(path),
        target_operation=selected.operation,
        tested_source_sha256=stable_sha256(selected.tested_source),
        untested_source_sha256=stable_sha256(selected.untested_source),
        joint_operations=selected.joint_operations,
        effect_sha256s=tuple(
            stable_sha256(effect) for effect in selected.effects
        ),
        tested_evidence_ref=selected.tested_evidence_ref,
        untested_evidence_ref=selected.untested_evidence_ref,
        depth=depth + 1,
        exceptional_score=-negative_score,
        reachable_nodes=len(predecessor),
        support_gap_count=len(compatibility.support_gaps),
    )


def compile_predictive_quotient(
    system: PartialActionSystem,
    *,
    operations: Iterable[Hashable],
    max_option_length: int = 4,
) -> PredictiveQuotient:
    """Compute the coarsest stable observed-test partition.

    Refinement starts with one class and repeatedly colors each source by the
    tuple of operation outcomes and successor colors. Because unknown is an
    explicit signature, two sources merge only when their admitted test
    surfaces agree.
    """
    operation_set = tuple(dict.fromkeys(operations))
    sources = _stable(system.fibers)
    colors = {source: 0 for source in sources}
    refinement_rounds = 0
    for round_index in range(max(1, len(sources) + 1)):
        signatures = {
            source: tuple(
                _relation_signature(
                    system,
                    source,
                    operation,
                    colors,
                )
                for operation in operation_set
            )
            for source in sources
        }
        unique = _stable(set(signatures.values()))
        color_for_signature = {
            signature: index
            for index, signature in enumerate(unique)
        }
        next_colors = {
            source: color_for_signature[signatures[source]]
            for source in sources
        }
        refinement_rounds = round_index + 1
        stable_partition = _partition(next_colors) == _partition(colors)
        colors = next_colors
        if stable_partition:
            break

    grouped: dict[int, list[Hashable]] = defaultdict(list)
    for source, color in colors.items():
        grouped[color].append(source)
    members_by_class: dict[str, tuple[Hashable, ...]] = {}
    class_by_source: dict[Hashable, str] = {}
    for members in grouped.values():
        stable_members = _stable(members)
        class_id = stable_sha256({
            "source_system_sha256": system.sha256,
            "members": sorted(
                stable_sha256(member) for member in stable_members
            ),
        })
        members_by_class[class_id] = stable_members
        for member in stable_members:
            class_by_source[member] = class_id

    section_by_class = {
        class_id: members[0]
        for class_id, members in members_by_class.items()
    }
    section_failures = tuple(
        {
            "class_id": class_id,
            "kind": "section_noncommuting",
        }
        for class_id, representative in section_by_class.items()
        if class_by_source.get(representative) != class_id
    )

    relation_effects: dict[
        tuple[str, Hashable],
        set[Hashable],
    ] = defaultdict(set)
    relation_targets: dict[
        tuple[str, Hashable],
        set[str],
    ] = defaultdict(set)
    for (source, operation), effects in system.relation_effects.items():
        class_id = class_by_source[source]
        relation_effects[(class_id, operation)].update(effects)
    for (source, operation), targets in system.relation_targets.items():
        class_id = class_by_source[source]
        relation_targets[(class_id, operation)].update(
            class_by_source[target] for target in targets
        )

    final_signatures = {
        source: tuple(
            _relation_signature(
                system,
                source,
                operation,
                colors,
            )
            for operation in operation_set
        )
        for source in sources
    }
    transport_failures = []
    for class_id, members in members_by_class.items():
        expected = final_signatures[members[0]]
        for member in members[1:]:
            if final_signatures[member] != expected:
                transport_failures.append({
                    "class_id": class_id,
                    "source_sha256": stable_sha256(member),
                    "kind": "operation_transport_noncommuting",
                })

    frozen_effects = {
        key: frozenset(value)
        for key, value in relation_effects.items()
    }
    frozen_targets = {
        key: frozenset(value)
        for key, value in relation_targets.items()
    }
    boundary_classes = frozenset(system.boundary_kinds)
    options = _discover_options(
        system=system,
        operations=operation_set,
        members_by_class=members_by_class,
        relation_effects=frozen_effects,
        relation_targets=frozen_targets,
        boundary_classes=boundary_classes,
        max_length=max(0, int(max_option_length)),
    )
    orbit_completions = _discover_orbit_completions(
        system=system,
        operations=operation_set,
        members_by_class=members_by_class,
        relation_effects=frozen_effects,
        relation_targets=frozen_targets,
        boundary_classes=boundary_classes,
    )
    return PredictiveQuotient(
        source_system_sha256=system.sha256,
        operations=operation_set,
        class_by_source=class_by_source,
        members_by_class=members_by_class,
        section_by_class=section_by_class,
        relation_effects=frozen_effects,
        relation_targets=frozen_targets,
        boundary_classes=boundary_classes,
        options=options,
        orbit_completions=orbit_completions,
        refinement_rounds=refinement_rounds,
        section_failures=section_failures,
        transport_failures=tuple(transport_failures),
    )


def plan_predictive_quotient_frontier(
    quotient: PredictiveQuotient,
    *,
    source_system: PartialActionSystem,
    start_source_key: Hashable,
    operations: Iterable[Hashable],
    max_depth: int = 128,
) -> ObservedFrontierPlan:
    """Route to an unknown intervention through commuting quotient edges."""
    if not quotient.passed_section or not quotient.passed_transport:
        return ObservedFrontierPlan(status="predictive_quotient_invalid")
    try:
        start_class = quotient.class_for_source(start_source_key)
    except KeyError:
        return ObservedFrontierPlan(status="start_fiber_unwitnessed")
    operation_set = tuple(dict.fromkeys(operations))
    class_scores = {
        row.class_key: row.score
        for row in source_system.ranked
        if not row.boundary_kind
    }
    incoming_score: dict[str, float] = defaultdict(float)
    for (class_id, operation), targets in quotient.relation_targets.items():
        effects = quotient.relation_effects.get((class_id, operation), ())
        score = max(
            (
                class_scores.get((operation, effect), 0.0)
                for effect in effects
            ),
            default=0.0,
        )
        for target in targets:
            incoming_score[target] = max(incoming_score[target], score)

    queue = [start_class]
    predecessor: dict[str, tuple[str, Hashable] | None] = {
        start_class: None,
    }
    depth_by_class = {start_class: 0}
    candidates: list[
        tuple[float, int, str, str, str, Hashable]
    ] = []
    frontier_pairs = 0
    cursor = 0
    while cursor < len(queue):
        class_id = queue[cursor]
        cursor += 1
        depth = depth_by_class[class_id]
        for operation in operation_set:
            relation_key = class_id, operation
            if relation_key in quotient.relation_effects:
                continue
            frontier_pairs += 1
            candidates.append((
                -incoming_score.get(class_id, 0.0),
                depth,
                class_id,
                repr(operation),
                class_id,
                operation,
            ))
        if depth >= max_depth:
            continue
        for operation in operation_set:
            relation_key = class_id, operation
            effects = quotient.relation_effects.get(relation_key, ())
            targets = quotient.relation_targets.get(relation_key, ())
            if (
                len(effects) != 1
                or len(targets) != 1
                or any(
                    (operation, effect) in quotient.boundary_classes
                    for effect in effects
                )
            ):
                continue
            target = next(iter(targets))
            if target in predecessor:
                continue
            predecessor[target] = class_id, operation
            depth_by_class[target] = depth + 1
            queue.append(target)
    if not candidates:
        return ObservedFrontierPlan(
            status="observed_frontier_exhausted",
            reachable_nodes=len(predecessor),
        )
    (
        negative_score,
        depth,
        _class_order,
        _operation_order,
        target_class,
        target_operation,
    ) = min(candidates)
    path: list[Hashable] = []
    cursor_class = target_class
    while predecessor[cursor_class] is not None:
        prior, operation = predecessor[cursor_class]
        path.append(operation)
        cursor_class = prior
    path.reverse()
    path.append(target_operation)
    return ObservedFrontierPlan(
        status="frontier_pair_found",
        actions=tuple(path),
        target_operation=target_operation,
        target_source_sha256=target_class,
        depth=depth + 1,
        exceptional_score=-negative_score,
        reachable_nodes=len(predecessor),
        frontier_pairs=frontier_pairs,
    )


__all__ = [
    "OperationOrbitCompletion",
    "PredictiveCompatibility",
    "PredictiveIncompatibility",
    "PredictiveOption",
    "PredictiveQuotient",
    "PredictiveSupportGap",
    "PredictiveSupportPlan",
    "compile_predictive_compatibility",
    "compile_predictive_quotient",
    "plan_predictive_quotient_frontier",
    "plan_predictive_support_frontier",
]
