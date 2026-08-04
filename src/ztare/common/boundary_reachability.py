"""Consumer-indexed reachability fibers for sparse skill acquisition.

The compiler keeps four identities separate:

* the witnessed control node needed by a transition consumer;
* the operation support observed over that node;
* an option program and its concrete evidence lineage;
* an external boundary or task-acceptance event.

It does not infer missing effects, synthesize representatives, or interpret a
boundary as task completion.  Substrates supply only opaque context keys.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import PartialActionSystem


ContextKeyFn = Callable[[Hashable], Hashable]
SupportKeyFn = Callable[[Hashable], Hashable]
SourceLineageKeysFn = Callable[[Hashable], Iterable[Hashable]]


def _stable(values: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(values, key=lambda value: (stable_sha256(value), repr(value))))


@dataclass(frozen=True)
class ReachabilityEdge:
    """One witnessed source-operation relation in the control graph."""

    source: Hashable
    operation: Hashable
    effects: tuple[Hashable, ...]
    targets: tuple[Hashable, ...]
    evidence_refs: tuple[str, ...]
    boundary_kinds: tuple[str, ...] = ()
    exceptional_score: float = 0.0
    context_transition: bool = False

    @property
    def deterministic(self) -> bool:
        return (
            len(self.effects) == 1
            and len(self.targets) == 1
            and not self.boundary_kinds
        )

    def to_receipt(self) -> dict:
        return {
            "source_sha256": stable_sha256(self.source),
            "operation": repr(self.operation),
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effects
            ],
            "target_sha256s": [
                stable_sha256(target) for target in self.targets
            ],
            "evidence_refs": list(self.evidence_refs),
            "boundary_kinds": list(self.boundary_kinds),
            "exceptional_score": self.exceptional_score,
            "context_transition": self.context_transition,
            "deterministic": self.deterministic,
        }


@dataclass(frozen=True)
class OptionProgramSpec:
    """An action chunk whose identity does not contain quotient-class IDs."""

    operations: tuple[Hashable, ...]
    initiation_source_sha256s: tuple[str, ...]
    lineage_refs: tuple[str, ...]
    imported_ref: str = ""
    source_family_sha256: str = ""
    source_revision_sha256: str = ""

    def __post_init__(self) -> None:
        if not self.operations:
            raise ValueError("option programs require at least one operation")
        if not self.initiation_source_sha256s and not self.lineage_refs:
            raise ValueError("option programs require concrete initiation lineage")
        if bool(self.source_family_sha256) != bool(
            self.source_revision_sha256
        ):
            raise ValueError(
                "source option family and revision identities must be paired"
            )

    @property
    def option_sha256(self) -> str:
        lineage = (
            ("evidence_refs", tuple(sorted(set(self.lineage_refs))))
            if self.lineage_refs
            else (
                "source_witnesses",
                tuple(sorted(set(self.initiation_source_sha256s))),
            )
        )
        return stable_sha256({
            "schema": "ztare-persistent-option-program-v1",
            "operations": self.operations,
            "concrete_lineage": lineage,
        })


@dataclass(frozen=True)
class OptionVariant:
    """One witnessed context-gated image of an option program."""

    effect_trace: tuple[Hashable, ...]
    context_transitions: tuple[int, ...]
    terminal_context: Hashable
    initiation_source_sha256s: tuple[str, ...]
    termination_source_sha256s: tuple[str, ...]
    source_target_sha256_pairs: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        canonical_pairs = tuple(sorted(set(
            self.source_target_sha256_pairs
        )))
        if self.source_target_sha256_pairs != canonical_pairs:
            raise ValueError(
                "option source/target pairs must be unique and canonical"
            )
        if canonical_pairs:
            if self.initiation_source_sha256s != tuple(sorted({
                source for source, _target in canonical_pairs
            })):
                raise ValueError(
                    "option initiation identities drifted from source/target "
                    "pairs"
                )
            if self.termination_source_sha256s != tuple(sorted({
                target for _source, target in canonical_pairs
            })):
                raise ValueError(
                    "option termination identities drifted from source/target "
                    "pairs"
                )

    @property
    def variant_sha256(self) -> str:
        return stable_sha256({
            "effect_trace": self.effect_trace,
            "context_transitions": self.context_transitions,
            "terminal_context": self.terminal_context,
        })

    def to_receipt(self) -> dict:
        return {
            "variant_sha256": self.variant_sha256,
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effect_trace
            ],
            "context_transition_steps": list(self.context_transitions),
            "terminal_context_sha256": stable_sha256(
                self.terminal_context
            ),
            "initiation_source_sha256s": list(
                self.initiation_source_sha256s
            ),
            "termination_source_sha256s": list(
                self.termination_source_sha256s
            ),
            "source_target_sha256_pairs": [
                {
                    "source_sha256": source,
                    "target_sha256": target,
                }
                for source, target in self.source_target_sha256_pairs
            ],
        }


@dataclass(frozen=True)
class ReindexedOptionProgram:
    """Current graph disposition of one persistent option program."""

    option_sha256: str
    operations: tuple[Hashable, ...]
    status: str
    requested_initiation_count: int
    resolved_initiation_count: int
    variants: tuple[OptionVariant, ...]
    unresolved_source_sha256s: tuple[str, ...] = ()
    failure_kinds: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    imported_ref: str = ""
    source_family_sha256: str = ""
    source_revision_sha256: str = ""

    def to_receipt(self) -> dict:
        return {
            "option_sha256": self.option_sha256,
            "operations": [repr(operation) for operation in self.operations],
            "status": self.status,
            "requested_initiation_count": self.requested_initiation_count,
            "resolved_initiation_count": self.resolved_initiation_count,
            "variant_count": len(self.variants),
            "variants": [variant.to_receipt() for variant in self.variants],
            "unresolved_source_sha256s": list(
                self.unresolved_source_sha256s
            ),
            "failure_kinds": list(self.failure_kinds),
            "lineage_refs": list(self.lineage_refs),
            "imported_ref": self.imported_ref,
            "source_family_sha256": self.source_family_sha256,
            "source_revision_sha256": self.source_revision_sha256,
        }


@dataclass(frozen=True)
class EffectOptionImplementation:
    """One motor program witnessing a guarded effect-schema variant."""

    source_option_sha256: str
    source_option_status: str
    source_family_sha256: str
    source_revision_sha256: str
    context_variant_sha256: str
    operations: tuple[Hashable, ...]
    source_target_sha256_pairs: tuple[tuple[str, str], ...]
    lineage_refs: tuple[str, ...]
    imported_ref: str = ""

    @property
    def implementation_sha256(self) -> str:
        return stable_sha256({
            "schema": "ztare-effect-option-implementation-v1",
            "source_option_sha256": self.source_option_sha256,
            "context_variant_sha256": self.context_variant_sha256,
            "operations": self.operations,
            "source_target_sha256_pairs": (
                self.source_target_sha256_pairs
            ),
        })

    def to_receipt(self) -> dict:
        return {
            "implementation_sha256": self.implementation_sha256,
            "source_option_sha256": self.source_option_sha256,
            "source_option_status": self.source_option_status,
            "source_family_sha256": self.source_family_sha256,
            "source_revision_sha256": self.source_revision_sha256,
            "context_variant_sha256": self.context_variant_sha256,
            "operations": [
                repr(operation) for operation in self.operations
            ],
            "primitive_operation_count": len(self.operations),
            "initiation_count": len({
                source
                for source, _target in self.source_target_sha256_pairs
            }),
            "source_target_sha256_pairs": [
                {
                    "source_sha256": source,
                    "target_sha256": target,
                }
                for source, target in self.source_target_sha256_pairs
            ],
            "lineage_refs": list(self.lineage_refs),
            "imported_ref": self.imported_ref,
        }


@dataclass(frozen=True)
class EffectOptionContextVariant:
    """One terminal-context guard under a shared effect-schema identity."""

    variant_sha256: str
    context_transitions: tuple[int, ...]
    terminal_context: Hashable
    implementations: tuple[EffectOptionImplementation, ...]

    def to_receipt(self) -> dict:
        return {
            "schema": "ztare-effect-option-context-variant-v1",
            "variant_sha256": self.variant_sha256,
            "context_transition_steps": list(self.context_transitions),
            "terminal_context_sha256": stable_sha256(
                self.terminal_context
            ),
            "implementation_count": len(self.implementations),
            "initiation_count": len({
                source
                for implementation in self.implementations
                for source, _target
                in implementation.source_target_sha256_pairs
            }),
            "implementations": [
                implementation.to_receipt()
                for implementation in self.implementations
            ],
        }


@dataclass(frozen=True)
class EffectOptionFamily:
    """A shared effect schema with guarded variants and motor implementations."""

    family_sha256: str
    effect_namespace: str
    effect_trace: tuple[Hashable, ...]
    context_variants: tuple[EffectOptionContextVariant, ...]

    @property
    def implementations(self) -> tuple[EffectOptionImplementation, ...]:
        """Return the implementation set without erasing variant lineage."""

        by_identity = {
            implementation.implementation_sha256: implementation
            for variant in self.context_variants
            for implementation in variant.implementations
        }
        return tuple(sorted(
            by_identity.values(),
            key=lambda row: row.implementation_sha256,
        ))

    def to_receipt(self) -> dict:
        return {
            "schema": "ztare-effect-option-family-v2",
            "family_sha256": self.family_sha256,
            "effect_namespace": self.effect_namespace,
            "effect_sha256s": [
                stable_sha256(effect) for effect in self.effect_trace
            ],
            "context_variant_count": len(self.context_variants),
            "implementation_count": len(self.implementations),
            "initiation_count": len({
                source
                for implementation in self.implementations
                for source, _target
                in implementation.source_target_sha256_pairs
            }),
            "context_variants": [
                variant.to_receipt()
                for variant in self.context_variants
            ],
            "evidence_status": "effect_supported",
            "task_credit_transferred": False,
        }


@dataclass(frozen=True)
class BoundaryReachabilityPlan:
    """A witnessed route to one boundary-relevant unsupported operation."""

    status: str
    actions: tuple[Hashable, ...] = ()
    target_operation: Hashable | None = None
    target_source_sha256: str = ""
    route_crosses_context: bool = False
    source_has_boundary: bool = False
    source_has_context_transition: bool = False
    distance_to_boundary: int | None = None
    exceptional_score: float = 0.0
    reachable_nodes: int = 0
    reachable_frontier_pairs: int = 0
    boundary_relevant_frontier_pairs: int = 0
    schema: str = "ztare-boundary-reachability-plan-v1"

    def to_receipt(self) -> dict:
        return {
            "schema": self.schema,
            "status": self.status,
            "actions": [repr(action) for action in self.actions],
            "action_count": len(self.actions),
            "target_operation": repr(self.target_operation),
            "target_source_sha256": self.target_source_sha256,
            "route_crosses_context": self.route_crosses_context,
            "source_has_boundary": self.source_has_boundary,
            "source_has_context_transition": (
                self.source_has_context_transition
            ),
            "distance_to_boundary": self.distance_to_boundary,
            "exceptional_score": self.exceptional_score,
            "reachable_nodes": self.reachable_nodes,
            "reachable_frontier_pairs": self.reachable_frontier_pairs,
            "boundary_relevant_frontier_pairs": (
                self.boundary_relevant_frontier_pairs
            ),
        }


@dataclass
class BoundaryReachabilityFiberSystem:
    """Witnessed control graph with support and context kept as fibers."""

    source_system_sha256: str
    operations: tuple[Hashable, ...]
    nodes: tuple[Hashable, ...]
    context_by_node: Mapping[Hashable, Hashable]
    support_identity_by_node: Mapping[Hashable, Hashable]
    lineage_sha256s_by_node: Mapping[Hashable, frozenset[str]]
    support_by_node: Mapping[Hashable, frozenset[Hashable]]
    edges: Mapping[tuple[Hashable, Hashable], ReachabilityEdge]
    section_failures: tuple[dict, ...] = ()
    schema: str = "ztare-boundary-reachability-fiber-system-v1"

    @property
    def passed_section(self) -> bool:
        return not self.section_failures

    @property
    def context_transition_edges(self) -> tuple[ReachabilityEdge, ...]:
        return tuple(
            edge for edge in self.edges.values()
            if edge.context_transition
        )

    @property
    def boundary_edges(self) -> tuple[ReachabilityEdge, ...]:
        return tuple(
            edge for edge in self.edges.values()
            if edge.boundary_kinds
        )

    @property
    def source_operation_frontier_count(self) -> int:
        return sum(
            1
            for source in self.nodes
            for operation in self.operations
            if operation not in self.support_by_node[source]
        )

    def to_receipt(
        self,
        *,
        edge_cap: int = 80,
        option_programs: Iterable[ReindexedOptionProgram] = (),
    ) -> dict:
        edges = sorted(
            self.edges.values(),
            key=lambda edge: (
                stable_sha256(edge.source),
                repr(edge.operation),
            ),
        )
        options = tuple(option_programs)
        return {
            "schema": self.schema,
            "source_system_sha256": self.source_system_sha256,
            "operations": [repr(operation) for operation in self.operations],
            "node_count": len(self.nodes),
            "relation_count": len(self.edges),
            "source_operation_frontier_count": (
                self.source_operation_frontier_count
            ),
            "context_count": len(set(self.context_by_node.values())),
            "support_identity_count": len(set(
                self.support_identity_by_node.values()
            )),
            "lineage_identity_count": len({
                digest
                for digests in self.lineage_sha256s_by_node.values()
                for digest in digests
            }),
            "context_transition_edge_count": len(
                self.context_transition_edges
            ),
            "boundary_edge_count": len(self.boundary_edges),
            "deterministic_edge_count": sum(
                edge.deterministic for edge in edges
            ),
            "ambiguous_edge_count": sum(
                not edge.deterministic and not edge.boundary_kinds
                for edge in edges
            ),
            "section": {
                "status": "pass" if self.passed_section else "fail",
                "failures": list(self.section_failures),
            },
            "edges": [
                edge.to_receipt() for edge in edges[:max(0, edge_cap)]
            ],
            "option_program_count": len(options),
            "option_programs": [
                option.to_receipt() for option in options
            ],
        }


def compile_boundary_reachability_fibers(
    system: PartialActionSystem,
    *,
    operations: Iterable[Hashable],
    context_key: ContextKeyFn,
    support_key: SupportKeyFn | None = None,
    source_lineage_keys: SourceLineageKeysFn | None = None,
) -> BoundaryReachabilityFiberSystem:
    """Compile the witnessed partial relation into reachability fibers."""
    operation_set = tuple(dict.fromkeys(operations))
    nodes = _stable(system.fibers)
    contexts: dict[Hashable, Hashable] = {}
    support_identities: dict[Hashable, Hashable] = {}
    lineage_sha256s: dict[Hashable, frozenset[str]] = {}
    section_failures = list(system.section_failures)
    for source in nodes:
        try:
            context = context_key(source)
            hash(context)
        except Exception as exc:  # noqa: BLE001 - receipt localizes adapter fault
            section_failures.append({
                "kind": "context_projection_failed",
                "source_sha256": stable_sha256(source),
                "error_type": type(exc).__name__,
            })
            context = ("context_projection_failed", stable_sha256(source))
        contexts[source] = context
        try:
            support_identity = (
                support_key(source)
                if support_key is not None
                else source
            )
            hash(support_identity)
        except Exception as exc:  # noqa: BLE001 - receipt localizes adapter fault
            section_failures.append({
                "kind": "support_projection_failed",
                "source_sha256": stable_sha256(source),
                "error_type": type(exc).__name__,
            })
            support_identity = (
                "support_projection_failed",
                stable_sha256(source),
            )
        support_identities[source] = support_identity
        try:
            lineage_keys = tuple(
                source_lineage_keys(source)
                if source_lineage_keys is not None
                else (source,)
            )
            if not lineage_keys:
                raise ValueError("source lineage cannot be empty")
            lineage_sha256s[source] = frozenset(
                stable_sha256(key) for key in lineage_keys
            )
        except Exception as exc:  # noqa: BLE001 - receipt localizes adapter fault
            section_failures.append({
                "kind": "source_lineage_projection_failed",
                "source_sha256": stable_sha256(source),
                "error_type": type(exc).__name__,
            })
            lineage_sha256s[source] = frozenset({
                stable_sha256(source),
            })

    ranked_scores = {
        row.class_key: row.score for row in system.ranked
    }
    edges = {}
    support_by_identity: dict[Hashable, set[Hashable]] = defaultdict(set)
    for relation_key in sorted(
        system.relation_effects,
        key=lambda item: (stable_sha256(item[0]), repr(item[1])),
    ):
        source, operation = relation_key
        effects = _stable(system.relation_effects[relation_key])
        targets = _stable(system.relation_targets.get(relation_key, ()))
        support_by_identity[support_identities[source]].add(operation)
        boundary_kinds = tuple(sorted({
            system.boundary_kinds[(operation, effect)]
            for effect in effects
            if (operation, effect) in system.boundary_kinds
        }))
        # Effect support is intentionally shared across sources. Evidence
        # lineage is not: a concrete reachability edge may cite only rows
        # compiled for that exact source-operation relation.
        evidence_refs = tuple(sorted(
            system.relation_evidence_refs.get(relation_key, ())
        ))
        context_transition = any(
            contexts.get(target) != contexts[source]
            for target in targets
            if target in contexts
        )
        exceptional_score = max(
            (
                ranked_scores.get((operation, effect), 0.0)
                for effect in effects
            ),
            default=0.0,
        )
        edges[relation_key] = ReachabilityEdge(
            source=source,
            operation=operation,
            effects=effects,
            targets=targets,
            evidence_refs=evidence_refs,
            boundary_kinds=boundary_kinds,
            exceptional_score=exceptional_score,
            context_transition=context_transition,
        )
    return BoundaryReachabilityFiberSystem(
        source_system_sha256=system.sha256,
        operations=operation_set,
        nodes=nodes,
        context_by_node=contexts,
        support_identity_by_node=support_identities,
        lineage_sha256s_by_node=lineage_sha256s,
        support_by_node={
            node: frozenset(
                support_by_identity.get(support_identities[node], ())
            )
            for node in nodes
        },
        edges=edges,
        section_failures=tuple(section_failures),
    )


def reindex_option_program(
    spec: OptionProgramSpec,
    *,
    fibers: BoundaryReachabilityFiberSystem,
) -> ReindexedOptionProgram:
    """Transport one option program through current witnessed graph fibers."""
    by_digest: dict[str, list[Hashable]] = defaultdict(list)
    for source in fibers.nodes:
        for digest in fibers.lineage_sha256s_by_node[source]:
            by_digest[digest].append(source)
    requested = tuple(dict.fromkeys(spec.initiation_source_sha256s))
    unresolved = []
    failures = []
    resolved_rows = []
    for source_digest in requested:
        sources = _stable(by_digest.get(source_digest, ()))
        if not sources:
            unresolved.append(source_digest)
            failures.append("initiation_source_absent")
            continue
        resolved_this_lineage = False
        for source in sources:
            current = source
            effect_trace = []
            context_transitions = []
            failure = ""
            for step, operation in enumerate(spec.operations):
                edge = fibers.edges.get((current, operation))
                if edge is None:
                    failure = "operation_unsupported"
                    break
                if edge.boundary_kinds:
                    failure = "typed_boundary_before_option_termination"
                    break
                if not edge.deterministic:
                    failure = "ambiguous_operation_image"
                    break
                effect_trace.append(edge.effects[0])
                if edge.context_transition:
                    context_transitions.append(step)
                current = edge.targets[0]
            if failure:
                unresolved.append(stable_sha256(source))
                failures.append(failure)
                continue
            resolved_this_lineage = True
            resolved_rows.append((
                stable_sha256(source),
                stable_sha256(current),
                tuple(effect_trace),
                tuple(context_transitions),
                fibers.context_by_node[current],
                source_digest,
            ))
        if not resolved_this_lineage:
            unresolved.append(source_digest)

    grouped: dict[
        tuple[tuple[Hashable, ...], tuple[int, ...], Hashable],
        list[tuple[str, str]],
    ] = defaultdict(list)
    for (
        source_digest,
        target_digest,
        effects,
        transitions,
        context,
        _parent_digest,
    ) in resolved_rows:
        grouped[(effects, transitions, context)].append(
            (source_digest, target_digest)
        )
    variants = tuple(sorted(
        (
            OptionVariant(
                effect_trace=signature[0],
                context_transitions=signature[1],
                terminal_context=signature[2],
                initiation_source_sha256s=tuple(sorted({
                    source for source, _target in rows
                })),
                termination_source_sha256s=tuple(sorted({
                    target for _source, target in rows
                })),
                source_target_sha256_pairs=tuple(sorted(set(rows))),
            )
            for signature, rows in grouped.items()
        ),
        key=lambda variant: variant.variant_sha256,
    ))
    resolved_parent_count = len({
        parent_digest for *_rest, parent_digest in resolved_rows
    })
    requested_count = len(requested)
    failed_current_source = any(
        digest not in requested for digest in unresolved
    )
    if resolved_parent_count == 0:
        status = "unsupported"
    elif (
        resolved_parent_count < requested_count
        or failed_current_source
    ):
        status = "partially_supported"
    elif len(variants) == 1:
        status = "stable"
    else:
        status = "context_gated"
    return ReindexedOptionProgram(
        option_sha256=spec.option_sha256,
        operations=spec.operations,
        status=status,
        requested_initiation_count=requested_count,
        resolved_initiation_count=resolved_parent_count,
        variants=variants,
        unresolved_source_sha256s=tuple(sorted(set(unresolved))),
        failure_kinds=tuple(sorted(set(failures))),
        lineage_refs=tuple(sorted(set(spec.lineage_refs))),
        imported_ref=spec.imported_ref,
        source_family_sha256=spec.source_family_sha256,
        source_revision_sha256=spec.source_revision_sha256,
    )


def reindex_option_programs(
    specs: Iterable[OptionProgramSpec],
    *,
    fibers: BoundaryReachabilityFiberSystem,
) -> tuple[ReindexedOptionProgram, ...]:
    """Reindex a stable set of option programs without quotient identifiers."""
    return tuple(sorted(
        (
            reindex_option_program(spec, fibers=fibers)
            for spec in specs
        ),
        key=lambda option: option.option_sha256,
    ))


def compile_effect_option_families(
    options: Iterable[ReindexedOptionProgram],
    *,
    effect_namespace: str,
) -> tuple[EffectOptionFamily, ...]:
    """Group motor words under effect schemas and retain context as variants."""

    namespace = str(effect_namespace).strip()
    if not namespace:
        raise ValueError("effect option families require effect_namespace")
    grouped: dict[
        tuple[Hashable, ...],
        dict[
            tuple[tuple[int, ...], Hashable],
            dict[str, EffectOptionImplementation],
        ],
    ] = defaultdict(dict)
    for option in options:
        for variant in option.variants:
            if not variant.source_target_sha256_pairs:
                continue
            family_sha = stable_sha256({
                "schema": "ztare-effect-option-family-v2",
                "effect_namespace": namespace,
                "effect_trace": variant.effect_trace,
            })
            context_variant_sha = stable_sha256({
                "schema": "ztare-effect-option-context-variant-v1",
                "effect_option_family_sha256": family_sha,
                "context_transitions": variant.context_transitions,
                "terminal_context": variant.terminal_context,
            })
            implementation = EffectOptionImplementation(
                source_option_sha256=option.option_sha256,
                source_option_status=option.status,
                source_family_sha256=option.source_family_sha256,
                source_revision_sha256=option.source_revision_sha256,
                context_variant_sha256=context_variant_sha,
                operations=option.operations,
                source_target_sha256_pairs=(
                    variant.source_target_sha256_pairs
                ),
                lineage_refs=option.lineage_refs,
                imported_ref=option.imported_ref,
            )
            variant_key = (
                variant.context_transitions,
                variant.terminal_context,
            )
            grouped.setdefault(variant.effect_trace, {}).setdefault(
                variant_key,
                {},
            )[implementation.implementation_sha256] = implementation
    families = []
    for effect_trace, variants in grouped.items():
        family_sha = stable_sha256({
            "schema": "ztare-effect-option-family-v2",
            "effect_namespace": namespace,
            "effect_trace": effect_trace,
        })
        context_variants = []
        for (
            context_transitions,
            terminal_context,
        ), implementations in variants.items():
            variant_sha = stable_sha256({
                "schema": "ztare-effect-option-context-variant-v1",
                "effect_option_family_sha256": family_sha,
                "context_transitions": context_transitions,
                "terminal_context": terminal_context,
            })
            context_variants.append(EffectOptionContextVariant(
                variant_sha256=variant_sha,
                context_transitions=context_transitions,
                terminal_context=terminal_context,
                implementations=tuple(sorted(
                    implementations.values(),
                    key=lambda row: row.implementation_sha256,
                )),
            ))
        families.append(EffectOptionFamily(
            family_sha256=family_sha,
            effect_namespace=namespace,
            effect_trace=effect_trace,
            context_variants=tuple(sorted(
                context_variants,
                key=lambda row: row.variant_sha256,
            )),
        ))
    return tuple(sorted(
        families,
        key=lambda family: family.family_sha256,
    ))


def _distance_to_boundary(
    fibers: BoundaryReachabilityFiberSystem,
    start: Hashable,
    *,
    max_depth: int,
) -> int | None:
    boundary_sources = {
        edge.source for edge in fibers.boundary_edges
    }
    if start in boundary_sources:
        return 0
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        source, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for operation in fibers.operations:
            edge = fibers.edges.get((source, operation))
            if edge is None or not edge.deterministic:
                continue
            target = edge.targets[0]
            if target in boundary_sources:
                return depth + 1
            if target not in seen:
                seen.add(target)
                queue.append((target, depth + 1))
    return None


def plan_boundary_reachability_frontier(
    fibers: BoundaryReachabilityFiberSystem,
    *,
    start_key: Hashable,
    max_depth: int = 128,
    boundary_distance: int = 2,
) -> BoundaryReachabilityPlan:
    """Rank unsupported operations only on a boundary-relevant reachable graph."""
    if start_key not in fibers.context_by_node:
        return BoundaryReachabilityPlan(status="start_fiber_unwitnessed")
    if max_depth < 0 or boundary_distance < 0:
        raise ValueError("reachability depths must be non-negative")

    # A node can be reached before and after a context transition. Preserve
    # that bit because it changes experiment rank but not control-state identity.
    start_state = (start_key, False)
    queue = deque([start_state])
    predecessor: dict[
        tuple[Hashable, bool],
        tuple[tuple[Hashable, bool], Hashable] | None,
    ] = {start_state: None}
    depth = {start_state: 0}
    while queue:
        state = queue.popleft()
        source, crossed_context = state
        if depth[state] >= max_depth:
            continue
        for operation in fibers.operations:
            edge = fibers.edges.get((source, operation))
            if edge is None or not edge.deterministic:
                continue
            target_state = (
                edge.targets[0],
                crossed_context or edge.context_transition,
            )
            if target_state in predecessor:
                continue
            predecessor[target_state] = state, operation
            depth[target_state] = depth[state] + 1
            queue.append(target_state)

    boundary_sources = {
        edge.source for edge in fibers.boundary_edges
    }
    context_sources = {
        edge.source for edge in fibers.context_transition_edges
    }
    all_frontier_count = 0
    candidates = []
    distance_cache: dict[Hashable, int | None] = {}
    for state in predecessor:
        source, crossed_context = state
        missing = [
            operation for operation in fibers.operations
            if operation not in fibers.support_by_node[source]
        ]
        all_frontier_count += len(missing)
        if source not in distance_cache:
            distance_cache[source] = _distance_to_boundary(
                fibers,
                source,
                max_depth=max_depth,
            )
        distance = distance_cache[source]
        source_boundary = source in boundary_sources
        source_context = source in context_sources
        relevant = (
            source_boundary
            or crossed_context
            or source_context
            or (
                distance is not None
                and distance <= boundary_distance
            )
        )
        if not relevant:
            continue
        incoming_score = max(
            (
                edge.exceptional_score
                for edge in fibers.edges.values()
                if source in edge.targets
            ),
            default=0.0,
        )
        priority = (
            4 if source_boundary
            else 3 if crossed_context
            else 2 if source_context
            else 1
        )
        for operation in missing:
            candidates.append((
                -priority,
                -incoming_score,
                distance if distance is not None else max_depth + 1,
                depth[state],
                stable_sha256(source),
                repr(operation),
                state,
                operation,
                source_boundary,
                source_context,
                distance,
            ))

    reachable_nodes = len({
        source for source, _crossed in predecessor
    })
    if not candidates:
        return BoundaryReachabilityPlan(
            status="boundary_relevant_frontier_unavailable",
            reachable_nodes=reachable_nodes,
            reachable_frontier_pairs=all_frontier_count,
            boundary_relevant_frontier_pairs=0,
        )
    (
        _priority,
        negative_exceptional,
        _distance_order,
        _depth_order,
        _source_order,
        _operation_order,
        selected_state,
        selected_operation,
        source_boundary,
        source_context,
        distance,
    ) = min(candidates)
    path = []
    cursor = selected_state
    while predecessor[cursor] is not None:
        prior, operation = predecessor[cursor]
        path.append(operation)
        cursor = prior
    path.reverse()
    path.append(selected_operation)
    return BoundaryReachabilityPlan(
        status="boundary_relevant_frontier_found",
        actions=tuple(path),
        target_operation=selected_operation,
        target_source_sha256=stable_sha256(selected_state[0]),
        route_crosses_context=selected_state[1],
        source_has_boundary=source_boundary,
        source_has_context_transition=source_context,
        distance_to_boundary=distance,
        exceptional_score=-negative_exceptional,
        reachable_nodes=reachable_nodes,
        reachable_frontier_pairs=all_frontier_count,
        boundary_relevant_frontier_pairs=len(candidates),
    )
