"""Evidence-backed partial action systems for skill acquisition.

The common object is a relation between an abstract source, an operation, and
either an abstract successor effect or a declared boundary.  Substrates supply
the projection and effect functions.  The kernel retains witnessed concrete
fiber members as a constrained section; it never synthesizes a representative.

This module does not assume grids, geometry, fixed action arity, scalar scores,
or deterministic dynamics.  Its jobs are:

* keep state, operation, effect, and boundary identities separate;
* check the witnessed section ``alpha(gamma(z)) == z``;
* surface source-operation classes with multiple effects;
* expose support rank and exceptional-effect rank independently.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256


@dataclass(frozen=True)
class PartialActionObservation:
    """One evidence-owned operation witness.

    ``successor`` may be absent only when ``boundary_kind`` names the observed
    partiality.  Boundary authority remains with the caller.
    """

    source: Any = field(compare=False, repr=False)
    operation: Hashable
    successor: Any | None = field(default=None, compare=False, repr=False)
    evidence_ref: str = ""
    boundary_kind: str = ""
    context: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not str(self.evidence_ref).strip():
            raise ValueError("partial-action observations require evidence_ref")
        if self.successor is None and not str(self.boundary_kind).strip():
            raise ValueError("missing successor requires boundary_kind")
        try:
            hash(self.operation)
        except TypeError as exc:
            raise TypeError("operation identity must be hashable") from exc


@dataclass(frozen=True)
class WitnessedFiber:
    """A concrete evidence member selected as a partial section witness."""

    abstract_key: Hashable
    representative: Any = field(compare=False, repr=False)
    evidence_ref: str


@dataclass(frozen=True)
class RankedEffect:
    """One operation/effect class under the opposing exceptional-set rank."""

    operation: Hashable
    effect: Hashable
    support: int
    score: float
    boundary_kind: str = ""
    evidence_refs: tuple[str, ...] = ()
    source_key_digests: tuple[str, ...] = ()

    @property
    def class_key(self) -> tuple[Hashable, Hashable]:
        return self.operation, self.effect

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": repr(self.operation),
            "effect_sha256": stable_sha256(self.effect),
            "effect": repr(self.effect),
            "support": self.support,
            "score": self.score,
            "boundary_kind": self.boundary_kind,
            "evidence_refs": list(self.evidence_refs),
            "source_key_digests": list(self.source_key_digests),
        }


@dataclass
class PartialActionSystem:
    """Compiled evidence relation plus its section and rank diagnostics."""

    projection_id: str
    observation_count: int
    fibers: dict[Hashable, WitnessedFiber]
    relation_effects: dict[tuple[Hashable, Hashable], frozenset[Hashable]]
    relation_targets: dict[
        tuple[Hashable, Hashable],
        frozenset[Hashable],
    ]
    effect_support: Counter[tuple[Hashable, Hashable]]
    effect_sources: dict[tuple[Hashable, Hashable], frozenset[Hashable]]
    effect_evidence_refs: dict[tuple[Hashable, Hashable], tuple[str, ...]]
    relation_evidence_refs: dict[
        tuple[Hashable, Hashable],
        tuple[str, ...],
    ]
    relation_effect_evidence_refs: dict[
        tuple[Hashable, Hashable, Hashable],
        tuple[str, ...],
    ]
    boundary_kinds: dict[tuple[Hashable, Hashable], str]
    ranked: tuple[RankedEffect, ...]
    section_failures: tuple[dict[str, Any], ...] = ()
    schema: str = "ztare-partial-action-system-v1"

    @property
    def noncommuting_relations(
        self,
    ) -> dict[tuple[Hashable, Hashable], frozenset[Hashable]]:
        return {
            key: effects
            for key, effects in self.relation_effects.items()
            if len(effects) > 1
        }

    @property
    def passed_section(self) -> bool:
        return not self.section_failures

    def representative(self, abstract_key: Hashable) -> Any:
        """Return an evidence member; no representative is generated."""
        try:
            return self.fibers[abstract_key].representative
        except KeyError as exc:
            raise KeyError("no witnessed member for abstract fiber") from exc

    def ranked_effects(
        self,
        *,
        include_boundaries: bool = True,
    ) -> tuple[RankedEffect, ...]:
        if include_boundaries:
            return self.ranked
        return tuple(row for row in self.ranked if not row.boundary_kind)

    @property
    def sha256(self) -> str:
        return stable_sha256(self.to_receipt())

    def to_receipt(self, *, rank_cap: int = 40) -> dict[str, Any]:
        noncommuting = []
        for (source_key, operation), effects in sorted(
            self.noncommuting_relations.items(),
            key=lambda item: (
                stable_sha256(item[0][0]),
                repr(item[0][1]),
            ),
        ):
            representative = self.fibers[source_key].representative
            concrete_source = getattr(
                representative,
                "observation",
                representative,
            )
            noncommuting.append({
                "source_key_sha256": stable_sha256(source_key),
                "source_representative_sha256": stable_sha256(
                    concrete_source
                ),
                "source_representative_evidence_ref": (
                    self.fibers[source_key].evidence_ref
                ),
                "operation": repr(operation),
                "effect_sha256s": sorted(stable_sha256(effect) for effect in effects),
                "relation_evidence_refs": list(
                    self.relation_evidence_refs.get(
                        (source_key, operation),
                        (),
                    )
                ),
                "effect_witnesses": [
                    {
                        "effect_sha256": stable_sha256(effect),
                        "evidence_refs": list(
                            self.relation_effect_evidence_refs.get(
                                (source_key, operation, effect),
                                (),
                            )
                        ),
                    }
                    for effect in sorted(effects, key=stable_sha256)
                ],
            })
        return {
            "schema": self.schema,
            "projection_id": self.projection_id,
            "observation_count": self.observation_count,
            "fiber_count": len(self.fibers),
            "relation_count": len(self.relation_effects),
            "target_relation_count": len(self.relation_targets),
            "relation_evidence_count": sum(
                len(refs) for refs in self.relation_evidence_refs.values()
            ),
            "effect_class_count": len(self.effect_support),
            "boundary_class_count": len(self.boundary_kinds),
            "section": {
                "checked": len(self.fibers),
                "status": "pass" if self.passed_section else "fail",
                "failures": list(self.section_failures),
            },
            "noncommuting_relation_count": len(noncommuting),
            "noncommuting_relations": noncommuting[:rank_cap],
            "exceptional_rank": [
                row.to_dict() for row in self.ranked[:rank_cap]
            ],
        }


ProjectFn = Callable[[Any], Hashable]
EffectFn = Callable[
    [Any, Hashable, Any, Hashable, Hashable],
    Hashable,
]
ExceptionalWeightFn = Callable[
    [PartialActionObservation, Hashable],
    float,
]


def _hashable(value: Any, label: str) -> Hashable:
    try:
        hash(value)
    except TypeError as exc:
        raise TypeError(f"{label} must return a hashable identity") from exc
    return value


def build_partial_action_system(
    observations: Iterable[PartialActionObservation],
    *,
    project: ProjectFn,
    effect: EffectFn,
    projection_id: str,
    exceptional_weight: ExceptionalWeightFn | None = None,
) -> PartialActionSystem:
    """Compile an evidence-backed partial action relation.

    Multiple effects for one projected source-operation pair are retained as a
    non-commutation witness.  They are never silently resolved by majority
    vote.  Exceptional rank is separate from support: caller-supplied
    structural weight, modal deviation, and inverse support all contribute.
    """
    if not str(projection_id).strip():
        raise ValueError("projection_id is required")
    rows = tuple(observations)
    fibers: dict[Hashable, WitnessedFiber] = {}
    section_failures: list[dict[str, Any]] = []
    relation: dict[
        tuple[Hashable, Hashable],
        set[Hashable],
    ] = defaultdict(set)
    targets: dict[
        tuple[Hashable, Hashable],
        set[Hashable],
    ] = defaultdict(set)
    supports: Counter[tuple[Hashable, Hashable]] = Counter()
    sources: dict[
        tuple[Hashable, Hashable],
        set[Hashable],
    ] = defaultdict(set)
    refs: dict[
        tuple[Hashable, Hashable],
        list[str],
    ] = defaultdict(list)
    relation_refs: dict[
        tuple[Hashable, Hashable],
        list[str],
    ] = defaultdict(list)
    relation_effect_refs: dict[
        tuple[Hashable, Hashable, Hashable],
        list[str],
    ] = defaultdict(list)
    boundary_kinds: dict[tuple[Hashable, Hashable], str] = {}
    weights: dict[tuple[Hashable, Hashable], float] = defaultdict(float)

    def retain_fiber(raw: Any, key: Hashable, evidence_ref: str) -> None:
        if key in fibers:
            return
        fiber = WitnessedFiber(
            abstract_key=key,
            representative=raw,
            evidence_ref=evidence_ref,
        )
        fibers[key] = fiber
        try:
            roundtrip = _hashable(project(raw), "project")
        except Exception as exc:  # noqa: BLE001 - becomes a section witness
            section_failures.append({
                "abstract_key_sha256": stable_sha256(key),
                "evidence_ref": evidence_ref,
                "kind": "projection_error",
                "error_type": type(exc).__name__,
            })
            return
        if roundtrip != key:
            section_failures.append({
                "abstract_key_sha256": stable_sha256(key),
                "roundtrip_key_sha256": stable_sha256(roundtrip),
                "evidence_ref": evidence_ref,
                "kind": "section_noncommuting",
            })

    for row in rows:
        source_key = _hashable(project(row.source), "project")
        retain_fiber(row.source, source_key, row.evidence_ref)
        if row.boundary_kind:
            effect_key: Hashable = (
                "boundary",
                str(row.boundary_kind),
            )
            target_key = None
        else:
            target_key = _hashable(project(row.successor), "project")
            retain_fiber(row.successor, target_key, row.evidence_ref)
            effect_key = _hashable(
                effect(
                    row.source,
                    row.operation,
                    row.successor,
                    source_key,
                    target_key,
                ),
                "effect",
            )
        relation_key = (source_key, row.operation)
        effect_class = (row.operation, effect_key)
        relation[relation_key].add(effect_key)
        if target_key is not None:
            targets[relation_key].add(target_key)
        supports[effect_class] += 1
        sources[effect_class].add(source_key)
        if row.evidence_ref not in refs[effect_class]:
            refs[effect_class].append(row.evidence_ref)
        if row.evidence_ref not in relation_refs[relation_key]:
            relation_refs[relation_key].append(row.evidence_ref)
        relation_effect_key = (
            source_key,
            row.operation,
            effect_key,
        )
        if row.evidence_ref not in relation_effect_refs[relation_effect_key]:
            relation_effect_refs[relation_effect_key].append(row.evidence_ref)
        if row.boundary_kind:
            boundary_kinds[effect_class] = str(row.boundary_kind)
        if exceptional_weight is not None:
            weights[effect_class] = max(
                weights[effect_class],
                float(exceptional_weight(row, effect_key)),
            )

    operation_effect_support: dict[Hashable, Counter[Hashable]] = defaultdict(Counter)
    for (operation, effect_key), count in supports.items():
        operation_effect_support[operation][effect_key] += count
    modal: dict[Hashable, frozenset[Hashable]] = {}
    for operation, counts in operation_effect_support.items():
        maximum = max(counts.values(), default=0)
        modal[operation] = frozenset(
            effect_key for effect_key, count in counts.items()
            if count == maximum
        )

    ranked: list[RankedEffect] = []
    for (operation, effect_key), support in supports.items():
        boundary_kind = boundary_kinds.get((operation, effect_key), "")
        modal_deviation = 0.0 if effect_key in modal[operation] else 1.0
        boundary_weight = 4.0 if boundary_kind else 0.0
        score = (
            weights[(operation, effect_key)]
            + modal_deviation
            + boundary_weight
            + (1.0 / max(1, support))
        )
        ranked.append(RankedEffect(
            operation=operation,
            effect=effect_key,
            support=support,
            score=score,
            boundary_kind=boundary_kind,
            evidence_refs=tuple(refs[(operation, effect_key)]),
            source_key_digests=tuple(sorted(
                stable_sha256(key)
                for key in sources[(operation, effect_key)]
            )),
        ))
    ranked.sort(
        key=lambda row: (
            -row.score,
            row.support,
            repr(row.operation),
            stable_sha256(row.effect),
        )
    )
    return PartialActionSystem(
        projection_id=str(projection_id),
        observation_count=len(rows),
        fibers=fibers,
        relation_effects={
            key: frozenset(value) for key, value in relation.items()
        },
        relation_targets={
            key: frozenset(value) for key, value in targets.items()
        },
        effect_support=supports,
        effect_sources={
            key: frozenset(value) for key, value in sources.items()
        },
        effect_evidence_refs={
            key: tuple(value) for key, value in refs.items()
        },
        relation_evidence_refs={
            key: tuple(value) for key, value in relation_refs.items()
        },
        relation_effect_evidence_refs={
            key: tuple(value) for key, value in relation_effect_refs.items()
        },
        boundary_kinds=boundary_kinds,
        ranked=tuple(ranked),
        section_failures=tuple(section_failures),
    )


@dataclass(frozen=True)
class ObservedFrontierPlan:
    """A route through witnessed operations to one unwitnessed operation."""

    status: str
    actions: tuple[Hashable, ...] = ()
    target_operation: Hashable | None = None
    target_source_sha256: str = ""
    depth: int = 0
    exceptional_score: float = 0.0
    reachable_nodes: int = 0
    frontier_pairs: int = 0
    ambiguous_edges_on_path: int = 0
    schema: str = "ztare-observed-partial-action-frontier-plan-v1"

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "action_count": len(self.actions),
            "actions": [repr(action) for action in self.actions],
            "target_operation": repr(self.target_operation),
            "target_source_sha256": self.target_source_sha256,
            "depth": self.depth,
            "exceptional_score": self.exceptional_score,
            "reachable_nodes": self.reachable_nodes,
            "frontier_pairs": self.frontier_pairs,
            "ambiguous_edges_on_path": self.ambiguous_edges_on_path,
        }


def plan_observed_action_frontier(
    system: PartialActionSystem,
    *,
    start_key: Hashable,
    operations: Iterable[Hashable],
    max_depth: int = 128,
) -> ObservedFrontierPlan:
    """Plan on the witnessed partial relation, never a rendered simulation.

    Adapter-attested boundary classes have no target and are therefore absent
    from traversal.  A relation with multiple targets remains branched.  The
    selected frontier is the reachable unwitnessed operation whose source has
    the highest incoming exceptional-effect score, with path length as the
    tiebreak.  This opposing rank prevents common transitions from hiding the
    small mechanism frontier.
    """
    _hashable(start_key, "start_key")
    operation_set = tuple(dict.fromkeys(operations))
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if start_key not in system.fibers:
        return ObservedFrontierPlan(
            status="start_fiber_unwitnessed",
        )
    class_scores = {
        row.class_key: row.score
        for row in system.ranked
        if not row.boundary_kind
    }
    boundary_classes = frozenset(system.boundary_kinds)
    witnessed_by_source: dict[Hashable, set[Hashable]] = defaultdict(set)
    for source_key, operation in system.relation_effects:
        witnessed_by_source[source_key].add(operation)
    incoming_score: dict[Hashable, float] = defaultdict(float)
    for relation_key, target_keys in system.relation_targets.items():
        operation = relation_key[1]
        effects = system.relation_effects.get(relation_key, ())
        score = max(
            (
                class_scores.get((operation, effect_key), 0.0)
                for effect_key in effects
            ),
            default=0.0,
        )
        for target_key in target_keys:
            incoming_score[target_key] = max(
                incoming_score[target_key],
                score,
            )

    queue: list[Hashable] = [start_key]
    predecessor: dict[
        Hashable,
        tuple[Hashable, Hashable, bool] | None,
    ] = {start_key: None}
    depth_by_key = {start_key: 0}
    candidates: list[
        tuple[float, int, str, str, Hashable, Hashable]
    ] = []
    frontier_pairs = 0
    cursor = 0
    while cursor < len(queue):
        source_key = queue[cursor]
        cursor += 1
        depth = depth_by_key[source_key]
        witnessed = witnessed_by_source.get(source_key, set())
        for operation in operation_set:
            if operation in witnessed:
                continue
            frontier_pairs += 1
            candidates.append((
                -incoming_score.get(source_key, 0.0),
                depth,
                stable_sha256(source_key),
                repr(operation),
                source_key,
                operation,
            ))
        if depth >= max_depth:
            continue
        for operation in operation_set:
            relation_key = (source_key, operation)
            targets = system.relation_targets.get(relation_key, ())
            effects = system.relation_effects.get(relation_key, ())
            # An open-loop action sequence can transport only through a
            # single-valued witnessed relation.  Multiple targets, multiple
            # effects, or a boundary alternative require feedback/replanning;
            # selecting one branch would silently invent an inverse map.
            if (
                len(targets) != 1
                or len(effects) != 1
                or any(
                    (operation, effect_key) in boundary_classes
                    for effect_key in effects
                )
            ):
                continue
            for target_key in sorted(targets, key=stable_sha256):
                if target_key in predecessor:
                    continue
                predecessor[target_key] = (
                    source_key,
                    operation,
                    False,
                )
                depth_by_key[target_key] = depth + 1
                queue.append(target_key)

    if not candidates:
        return ObservedFrontierPlan(
            status="observed_frontier_exhausted",
            reachable_nodes=len(predecessor),
            frontier_pairs=0,
        )
    (
        negative_score,
        depth,
        _source_digest,
        _operation_repr,
        target_source,
        target_operation,
    ) = min(candidates)
    path: list[Hashable] = []
    ambiguous_edges = 0
    cursor_key = target_source
    while predecessor[cursor_key] is not None:
        prior, operation, ambiguous = predecessor[cursor_key]
        path.append(operation)
        ambiguous_edges += int(ambiguous)
        cursor_key = prior
    path.reverse()
    path.append(target_operation)
    return ObservedFrontierPlan(
        status="frontier_pair_found",
        actions=tuple(path),
        target_operation=target_operation,
        target_source_sha256=stable_sha256(target_source),
        depth=depth + 1,
        exceptional_score=-negative_score,
        reachable_nodes=len(predecessor),
        frontier_pairs=frontier_pairs,
        ambiguous_edges_on_path=ambiguous_edges,
    )


__all__ = [
    "PartialActionObservation",
    "PartialActionSystem",
    "ObservedFrontierPlan",
    "RankedEffect",
    "WitnessedFiber",
    "build_partial_action_system",
    "plan_observed_action_frontier",
]
