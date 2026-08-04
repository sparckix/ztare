"""Interactive-world lowering into partial action mechanism effects.

The common partial-action kernel sees opaque keys.  This adapter projects the
accepted carrier's factor surface into presentation-invariant operation
effects.  Array coordinates remain confined here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    PartialActionSystem,
    build_partial_action_system,
)
from ztare.worldmodel.compiled_fiber_planning import FiberFactors


def fiber_transition_key(factors: FiberFactors) -> tuple[Hashable, ...]:
    """Coordinates needed to preserve operation consequences.

    Presentation labels are excluded; their equality partition already lives
    in ``finite_configuration``.  Ordered feasibility configuration and scalar
    remain because either can change which operation is available.
    """
    return (
        factors.controlled_base,
        factors.finite_configuration,
        factors.operation_domain_assignment,
        factors.ordered_feasibility_configuration,
        factors.ordered_budget,
        factors.one_shot_availability,
    )


@dataclass(frozen=True)
class HistoryAnnotatedState:
    """One observation paired with its pre-action history coordinate."""

    observation: Any = field(compare=False, repr=False)
    action_history: tuple[Hashable, ...] = ()


@dataclass(frozen=True)
class HistoryTrajectoryEvidence:
    """One ordered evidence trajectory with its predictive-state prefixes."""

    transitions: tuple[Any, ...]
    action_prefix: tuple[Hashable, ...] = ()
    operation_effect_prefix: tuple[Hashable, ...] = ()
    boundary_indices: frozenset[int] = frozenset()
    evidence_ref: str = ""

    def __post_init__(self) -> None:
        if not str(self.evidence_ref).strip():
            raise ValueError("history trajectories require evidence_ref")
        if any(
            index < 0 or index >= len(self.transitions)
            for index in self.boundary_indices
        ):
            raise ValueError("history trajectory boundary index is outside trace")


@dataclass(frozen=True)
class HistoryLiftSelection:
    """Evidence-selected bounded history projection."""

    action_system: PartialActionSystem
    history_kind: str
    suffix_length: int
    candidates: tuple[dict[str, Any], ...]
    boundary_noncommuting_relations: int
    observation_count: int
    predictive_context: Any = field(default=None, compare=False, repr=False)
    candidate_cap: int = 0
    pruned_candidate_count: int = 0
    schema: str = "ztare-history-lift-selection-v1"

    def start_key(
        self,
        factors: FiberFactors,
        *,
        observation: Any | None = None,
        action_history: Iterable[Hashable] = (),
        operation_effect_history: Iterable[Hashable] = (),
    ) -> tuple[Hashable, ...]:
        history = tuple(
            operation_effect_history
            if self.history_kind == "operation_effect"
            else action_history
        )
        suffix = (
            history[-self.suffix_length:]
            if self.suffix_length > 0
            else ()
        )
        key: tuple[Hashable, ...] = (
            *fiber_transition_key(factors),
            (f"{self.history_kind}_history_suffix", suffix),
        )
        if self.predictive_context is not None:
            if observation is None:
                raise ValueError(
                    "predictive context requires the concrete observation"
                )
            key = (
                *key,
                (
                    "predictive_context",
                    self.predictive_context.project(observation),
                ),
            )
        return key

    def predictive_context_key(self, observation: Any) -> Hashable:
        if self.predictive_context is None:
            return ()
        return (
            self.predictive_context.structural_sha256,
            self.predictive_context.project(observation),
        )

    def source_lineage_keys(
        self,
        source_key: Hashable,
    ) -> tuple[Hashable, ...]:
        """Return current identity and its pre-refinement parent, if present."""
        if (
            self.predictive_context is not None
            and isinstance(source_key, tuple)
            and source_key
            and isinstance(source_key[-1], tuple)
            and source_key[-1][:1] == ("predictive_context",)
        ):
            return source_key, source_key[:-1]
        return (source_key,)

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "history_kind": self.history_kind,
            "suffix_length": self.suffix_length,
            "boundary_noncommuting_relations": (
                self.boundary_noncommuting_relations
            ),
            "observation_count": self.observation_count,
            "candidate_cap": self.candidate_cap,
            "evaluated_candidate_count": len(self.candidates),
            "pruned_candidate_count": self.pruned_candidate_count,
            "candidates": list(self.candidates),
            "action_system_sha256": self.action_system.sha256,
            "predictive_context": (
                self.predictive_context.to_receipt()
                if self.predictive_context is not None
                else None
            ),
        }


def _boundary_noncommuting_count(system: PartialActionSystem) -> int:
    boundary_classes = frozenset(system.boundary_kinds)
    return sum(
        1
        for (source_key, operation), effects
        in system.noncommuting_relations.items()
        if any(
            (operation, effect_key) in boundary_classes
            for effect_key in effects
        )
    )


def _transition_histories(
    transitions: tuple[Any, ...],
) -> tuple[tuple[Hashable, ...], ...]:
    """Reconstruct pre-action histories on continuous evidence segments."""
    histories: list[tuple[Hashable, ...]] = []
    history: tuple[Hashable, ...] = ()
    prior = None
    for transition in transitions:
        continuous = _transition_pair_is_continuous(prior, transition)
        if not continuous:
            history = ()
        histories.append(history)
        history = (*history, transition.a)
        prior = transition
    return tuple(histories)


def _transition_pair_is_continuous(prior: Any, current: Any) -> bool:
    if prior is None or transition_boundary_kind(prior):
        return False
    if getattr(prior, "s_next", None) != getattr(current, "s", None):
        return False
    prior_time = getattr(prior, "t", None)
    current_time = getattr(current, "t", None)
    if prior_time is not None and current_time is not None:
        try:
            if int(current_time) != int(prior_time) + 1:
                return False
        except (TypeError, ValueError):
            return False
    prior_epoch = getattr(
        getattr(prior, "identity", None),
        "target_epoch",
        None,
    )
    current_epoch = getattr(
        getattr(current, "identity", None),
        "source_epoch",
        None,
    )
    if (
        prior_epoch is not None
        and current_epoch is not None
        and prior_epoch != current_epoch
    ):
        return False
    return True


def _normalize_boundary_edges(
    edges: Iterable[tuple[Any, ...]],
) -> tuple[
    tuple[
        Any,
        Hashable,
        str,
        tuple[Hashable, ...],
        tuple[Hashable, ...],
        str,
    ],
    ...,
]:
    normalized = []
    for item in edges:
        if len(item) == 3:
            source, operation, evidence_ref = item
            action_history = ()
            operation_effect_history = ()
            boundary_kind = "control_exclusion"
        elif len(item) == 4:
            source, operation, evidence_ref, action_history = item
            operation_effect_history = ()
            boundary_kind = "control_exclusion"
        elif len(item) == 5:
            (
                source,
                operation,
                evidence_ref,
                action_history,
                operation_effect_history,
            ) = item
            boundary_kind = "control_exclusion"
        elif len(item) == 6:
            (
                source,
                operation,
                evidence_ref,
                action_history,
                operation_effect_history,
                boundary_kind,
            ) = item
        else:
            raise ValueError(
                "explicit boundary edges require source, operation, "
                "evidence_ref, optional predictive histories, and optional "
                "boundary kind"
            )
        ref = str(evidence_ref).strip()
        if not ref:
            raise ValueError("explicit boundary edges require evidence refs")
        kind = str(boundary_kind).strip()
        if not kind:
            raise ValueError("explicit boundary edges require boundary kind")
        normalized.append((
            source,
            operation,
            ref,
            tuple(action_history),
            tuple(operation_effect_history),
            kind,
        ))
    return tuple(normalized)


def operation_effect_token(
    projection: Any,
    transition: Any,
) -> tuple[Hashable, ...]:
    """Return one recursively consumable Mealy observation token.

    The digest preserves the equality partition of the mechanism effect while
    keeping archived prefixes compact. The transition witness remains the
    backward section from the token to its represented observation.
    """
    effect = fiber_mechanism_effect(
        projection.factor(transition.s),
        projection.factor(transition.s_next),
    )
    return (
        "operation_effect",
        transition.a,
        stable_sha256(effect),
    )


def predictive_prefixes_from_transitions(
    transitions: Iterable[Any],
    *,
    projection: Any,
    action_prefix: Iterable[Hashable] = (),
    operation_effect_prefix: Iterable[Hashable] = (),
    explicit_boundary_indices: frozenset[int] = frozenset(),
) -> tuple[tuple[Hashable, ...], tuple[Hashable, ...]]:
    """Advance both predictive histories with one shared boundary lifecycle."""
    actions = tuple(action_prefix)
    operation_effects = tuple(operation_effect_prefix)
    for index, transition in enumerate(transitions):
        boundary = (
            index in explicit_boundary_indices
            or bool(transition_boundary_kind(transition))
        )
        if boundary:
            actions = ()
            operation_effects = ()
            continue
        actions = (*actions, transition.a)
        operation_effects = (
            *operation_effects,
            operation_effect_token(projection, transition),
        )
    return actions, operation_effects


def select_fiber_history_action_system(
    transitions: Iterable[Any],
    *,
    projection: Any,
    evidence_ref: str,
    explicit_boundary_edges: Iterable[tuple[Any, ...]] = (),
    history_trajectories: Iterable[HistoryTrajectoryEvidence] = (),
    max_suffix_length: int = 32,
    exhaustive_candidates: bool = False,
) -> HistoryLiftSelection:
    """Select the shortest suffix eliminating known boundary ambiguity.

    Candidate length zero is the frame-only relation.  Longer histories are
    admitted only through recursive action suffixes.  Selection first
    minimizes boundary-contaminated non-commutation, then chooses the shortest
    candidate that attains that minimum while retaining at least one repeated
    fiber whenever the evidence permits it.
    """
    transition_rows = tuple(transitions)
    trajectory_evidence = tuple(history_trajectories)
    factor_cache: dict[int, FiberFactors] = {}

    def factors(state: Any) -> FiberFactors:
        observation = (
            state.observation
            if isinstance(state, HistoryAnnotatedState)
            else state
        )
        key = id(observation)
        if key not in factor_cache:
            factor_cache[key] = projection.factor(observation)
        return factor_cache[key]

    def token(transition: Any) -> tuple[Hashable, ...]:
        effect_value = fiber_mechanism_effect(
            factors(transition.s),
            factors(transition.s_next),
        )
        return (
            "operation_effect",
            transition.a,
            stable_sha256(effect_value),
        )

    law_specs: list[
        tuple[
            Any,
            tuple[Hashable, ...],
            tuple[Hashable, ...],
            str,
        ]
    ] = []
    sequence_position_by_ref: dict[str, tuple[str, int]] = {}
    trajectory_boundary_edges: list[tuple[Any, ...]] = []
    if trajectory_evidence:
        for trajectory in trajectory_evidence:
            action_history = tuple(trajectory.action_prefix)
            operation_effect_history = tuple(
                trajectory.operation_effect_prefix
            )
            for index, transition in enumerate(trajectory.transitions):
                row_ref = f"{trajectory.evidence_ref}#{index}"
                sequence_position_by_ref[row_ref] = (
                    trajectory.evidence_ref,
                    index,
                )
                adapter_boundary_kind = transition_boundary_kind(transition)
                if (
                    index in trajectory.boundary_indices
                    or adapter_boundary_kind
                ):
                    trajectory_boundary_edges.append((
                        transition.s,
                        transition.a,
                        row_ref,
                        action_history,
                        operation_effect_history,
                        (
                            adapter_boundary_kind
                            or "control_exclusion"
                        ),
                    ))
                    action_history = ()
                    operation_effect_history = ()
                    continue
                law_specs.append((
                    transition,
                    action_history,
                    operation_effect_history,
                    row_ref,
                ))
                action_history = (*action_history, transition.a)
                operation_effect_history = (
                    *operation_effect_history,
                    token(transition),
                )
    else:
        action_histories = _transition_histories(transition_rows)
        operation_effect_history: tuple[Hashable, ...] = ()
        prior = None
        for index, (transition, action_history) in enumerate(
            zip(transition_rows, action_histories)
        ):
            row_ref = f"{evidence_ref}#{index}"
            sequence_position_by_ref[row_ref] = (evidence_ref, index)
            continuous = bool(
                prior is not None
                and prior.s_next == transition.s
                and getattr(prior, "t", None) is not None
                and getattr(transition, "t", None) is not None
                and int(transition.t) == int(prior.t) + 1
            )
            if not continuous:
                operation_effect_history = ()
            law_specs.append((
                transition,
                action_history,
                operation_effect_history,
                row_ref,
            ))
            operation_effect_history = (
                *operation_effect_history,
                token(transition),
            )
            prior = transition

    trajectory_boundary_refs = frozenset(
        str(item[2]) for item in trajectory_boundary_edges
    )
    boundary_edges = _normalize_boundary_edges((
        *(
            item
            for item in tuple(explicit_boundary_edges)
            if len(item) < 3 or str(item[2]) not in trajectory_boundary_refs
        ),
        *trajectory_boundary_edges,
    ))

    def effect(
        source: HistoryAnnotatedState,
        _operation: Hashable,
        successor: HistoryAnnotatedState,
        _source_key: Hashable,
        _target_key: Hashable,
    ) -> Hashable:
        return fiber_mechanism_effect(
            factors(source),
            factors(successor),
        )

    def project_history_state(
        state: HistoryAnnotatedState,
        *,
        history_kind: str,
        suffix_length: int,
        predictive_context: Any = None,
    ) -> Hashable:
        key: tuple[Hashable, ...] = (
            *fiber_transition_key(factors(state)),
            (
                f"{history_kind}_history_suffix",
                (
                    state.action_history[-suffix_length:]
                    if suffix_length
                    else ()
                ),
            ),
        )
        if predictive_context is not None:
            key = (
                *key,
                (
                    "predictive_context",
                    predictive_context.project(state.observation),
                ),
            )
        return key

    def compile_candidate(
        history_kind: str,
        suffix_length: int,
        *,
        predictive_context: Any = None,
    ) -> PartialActionSystem:
        observations = []
        history_index = 1 if history_kind == "action" else 2
        for row in law_specs:
            transition = row[0]
            history = row[history_index]
            next_token = (
                transition.a
                if history_kind == "action"
                else token(transition)
            )
            source_history = (
                history[-suffix_length:] if suffix_length else ()
            )
            target_history = (
                (*history, next_token)[-suffix_length:]
                if suffix_length
                else ()
            )
            observations.append(PartialActionObservation(
                source=HistoryAnnotatedState(
                    transition.s,
                    source_history,
                ),
                operation=transition.a,
                successor=HistoryAnnotatedState(
                    transition.s_next,
                    target_history,
                ),
                evidence_ref=row[3],
                context={
                    "time": getattr(transition, "t", None),
                    "history_kind": history_kind,
                    "history_suffix_length": suffix_length,
                },
            ))
        for boundary_row in boundary_edges:
            source, operation, boundary_ref = boundary_row[:3]
            history = boundary_row[
                3 if history_kind == "action" else 4
            ]
            observations.append(PartialActionObservation(
                source=HistoryAnnotatedState(
                    source,
                    history[-suffix_length:] if suffix_length else (),
                ),
                operation=operation,
                successor=None,
                evidence_ref=boundary_ref,
                boundary_kind=boundary_row[5],
                context={
                    "source": "explicit_boundary_edge",
                    "history_kind": history_kind,
                    "history_suffix_length": suffix_length,
                },
            ))

        def project(state: HistoryAnnotatedState) -> Hashable:
            return project_history_state(
                state,
                history_kind=history_kind,
                suffix_length=suffix_length,
                predictive_context=predictive_context,
            )

        return build_partial_action_system(
            observations,
            project=project,
            effect=effect,
            projection_id=stable_sha256({
                "projection_sha256": projection.projection_sha256,
                "history": f"bounded_{history_kind}_suffix",
                "suffix_length": suffix_length,
                "predictive_context": (
                    predictive_context.structural_sha256
                    if predictive_context is not None
                    else None
                ),
            }),
            exceptional_weight=fiber_exception_weight,
        )

    max_observed_history = max(
        (
            len(history)
            for history in (
                *(row[1] for row in law_specs),
                *(row[2] for row in law_specs),
                *(row[3] for row in boundary_edges),
                *(row[4] for row in boundary_edges),
            )
        ),
        default=0,
    )
    cap = max(0, min(int(max_suffix_length), max_observed_history))
    background_observations = (
        *(row[0].s for row in law_specs),
        *(row[0] for row in boundary_edges),
    )
    coordinate_cache: dict[str, Any | None] = {}

    def refine_candidate(
        history_kind: str,
        suffix_length: int,
        system: PartialActionSystem,
        boundary_noncommuting: int,
    ) -> tuple[
        PartialActionSystem,
        int,
        Any | None,
        dict[str, Any] | None,
    ]:
        """Refine one counterexample fiber before ranking history length."""
        if boundary_noncommuting == 0:
            return system, boundary_noncommuting, None, None

        from ztare.worldmodel.persistent_component_reservoir import (
            ReservoirWitness,
            discover_component_reservoir_coordinate,
        )

        conflict_keys = frozenset(system.noncommuting_relations)
        witnesses_by_relation: dict[
            tuple[Hashable, Hashable],
            list[ReservoirWitness],
        ] = {}
        history_index = 1 if history_kind == "action" else 2
        for row in law_specs:
            transition = row[0]
            state = HistoryAnnotatedState(
                transition.s,
                (
                    row[history_index][-suffix_length:]
                    if suffix_length
                    else ()
                ),
            )
            relation_key = (
                project_history_state(
                    state,
                    history_kind=history_kind,
                    suffix_length=suffix_length,
                ),
                transition.a,
            )
            if relation_key not in conflict_keys:
                continue
            outcome = (
                "effect",
                stable_sha256(fiber_mechanism_effect(
                    factors(transition.s),
                    factors(transition.s_next),
                )),
            )
            witnesses_by_relation.setdefault(relation_key, []).append(
                ReservoirWitness(
                    observation=transition.s,
                    outcome=outcome,
                    evidence_ref=row[3],
                    sequence_id=sequence_position_by_ref.get(
                        row[3],
                        ("", 0),
                    )[0],
                    sequence_index=(
                        sequence_position_by_ref[row[3]][1]
                        if row[3] in sequence_position_by_ref
                        else None
                    ),
                )
            )
        for boundary_row in boundary_edges:
            source, operation, boundary_ref = boundary_row[:3]
            history = boundary_row[
                3 if history_kind == "action" else 4
            ]
            state = HistoryAnnotatedState(
                source,
                (
                    history[-suffix_length:]
                    if suffix_length
                    else ()
                ),
            )
            relation_key = (
                project_history_state(
                    state,
                    history_kind=history_kind,
                    suffix_length=suffix_length,
                ),
                operation,
            )
            if relation_key not in conflict_keys:
                continue
            witnesses_by_relation.setdefault(relation_key, []).append(
                ReservoirWitness(
                    observation=source,
                    outcome=("boundary", boundary_row[5]),
                    evidence_ref=boundary_ref,
                    sequence_id=sequence_position_by_ref.get(
                        boundary_ref,
                        ("", 0),
                    )[0],
                    sequence_index=(
                        sequence_position_by_ref[boundary_ref][1]
                        if boundary_ref in sequence_position_by_ref
                        else None
                    ),
                )
            )

        refinements = []
        for relation_witnesses in witnesses_by_relation.values():
            exceptional_outcome = next(
                (
                    witness.outcome
                    for witness in relation_witnesses
                    if (
                        isinstance(witness.outcome, tuple)
                        and witness.outcome[:1] == ("boundary",)
                    )
                ),
                None,
            )
            if exceptional_outcome is None:
                continue
            cache_key = stable_sha256({
                "exceptional_outcome": exceptional_outcome,
                "witnesses": sorted(
                    (
                        witness.evidence_ref,
                        stable_sha256(witness.outcome),
                    )
                    for witness in relation_witnesses
                ),
            })
            if cache_key not in coordinate_cache:
                try:
                    coordinate_cache[cache_key] = (
                        discover_component_reservoir_coordinate(
                            relation_witnesses,
                            exceptional_outcome=exceptional_outcome,
                            background_observations=background_observations,
                            max_area=32,
                        )
                    )
                except (TypeError, ValueError):
                    coordinate_cache[cache_key] = None
            coordinate = coordinate_cache[cache_key]
            if coordinate is None:
                continue
            refined_system = compile_candidate(
                history_kind,
                suffix_length,
                predictive_context=coordinate,
            )
            refined_boundary_count = _boundary_noncommuting_count(
                refined_system
            )
            if refined_boundary_count >= boundary_noncommuting:
                continue
            refinements.append((
                refined_boundary_count,
                len(refined_system.noncommuting_relations),
                len(coordinate.normalized_shape),
                coordinate.structural_sha256,
                coordinate,
                refined_system,
            ))
        if not refinements:
            return system, boundary_noncommuting, None, None

        (
            refined_boundary_count,
            _noncommuting_count,
            _area,
            _coordinate_sha,
            coordinate,
            refined_system,
        ) = min(refinements, key=lambda row: row[:4])
        return (
            refined_system,
            refined_boundary_count,
            coordinate,
            {
                "kind": "component_reservoir",
                "sha256": coordinate.structural_sha256,
                "fiber_count": len(refined_system.fibers),
                "relation_count": len(refined_system.relation_effects),
                "noncommuting_relation_count": len(
                    refined_system.noncommuting_relations
                ),
                "boundary_noncommuting_relation_count": (
                    refined_boundary_count
                ),
            },
        )

    compiled: list[
        tuple[str, int, PartialActionSystem, int, Any | None]
    ] = []
    candidate_receipts: list[dict[str, Any]] = []
    shortest_zero_length: int | None = None
    for history_kind in ("action", "operation_effect"):
        family_cap = (
            cap
            if exhaustive_candidates or shortest_zero_length is None
            else min(cap, shortest_zero_length)
        )
        for suffix_length in range(family_cap + 1):
            system = compile_candidate(
                history_kind,
                suffix_length,
            )
            raw_boundary_noncommuting = _boundary_noncommuting_count(system)
            (
                selected_candidate_system,
                boundary_noncommuting,
                predictive_context,
                refinement_receipt,
            ) = refine_candidate(
                history_kind,
                suffix_length,
                system,
                raw_boundary_noncommuting,
            )
            compiled.append((
                history_kind,
                suffix_length,
                selected_candidate_system,
                boundary_noncommuting,
                predictive_context,
            ))
            candidate_receipt = {
                "history_kind": history_kind,
                "suffix_length": suffix_length,
                "fiber_count": len(system.fibers),
                "relation_count": len(system.relation_effects),
                "noncommuting_relation_count": len(
                    system.noncommuting_relations
                ),
                "boundary_noncommuting_relation_count": (
                    raw_boundary_noncommuting
                ),
            }
            if suffix_length == 0 and system.noncommuting_relations:
                candidate_receipt["noncommuting_relations"] = (
                    system.to_receipt(rank_cap=8)[
                        "noncommuting_relations"
                    ]
                )
            if refinement_receipt is not None:
                candidate_receipt["predictive_context_refinement"] = (
                    refinement_receipt
                )
            candidate_receipts.append(candidate_receipt)
            if (
                boundary_noncommuting == 0
                and not exhaustive_candidates
            ):
                shortest_zero_length = (
                    suffix_length
                    if shortest_zero_length is None
                    else min(shortest_zero_length, suffix_length)
                )
                # Later suffixes in this family lose on suffix length. The
                # other family is still evaluated through this length.
                break

    minimum_boundary_noncommuting = min(
        (row[3] for row in compiled),
        default=0,
    )
    observation_count = len(law_specs) + len(boundary_edges)
    compressed = [
        row for row in compiled
        if row[3] == minimum_boundary_noncommuting
        and len(row[2].fibers) < max(1, observation_count)
    ]
    eligible = compressed or [
        row for row in compiled
        if row[3] == minimum_boundary_noncommuting
    ]
    (
        selected_kind,
        selected_length,
        selected_system,
        selected_boundary_count,
        predictive_context,
    ) = min(
        eligible,
        key=lambda row: (
            row[1],
            len(row[2].noncommuting_relations),
            len(row[2].fibers),
            0 if row[0] == "action" else 1,
        ),
    )
    return HistoryLiftSelection(
        action_system=selected_system,
        history_kind=selected_kind,
        suffix_length=selected_length,
        candidates=tuple(candidate_receipts),
        boundary_noncommuting_relations=selected_boundary_count,
        observation_count=observation_count,
        predictive_context=predictive_context,
        candidate_cap=cap,
        pruned_candidate_count=(
            2 * (cap + 1) - len(candidate_receipts)
        ),
    )


def _controlled_effect(
    source: tuple[tuple[int, int], ...],
    target: tuple[tuple[int, int], ...],
) -> tuple[Hashable, ...]:
    if source == target:
        return ("fixed",)
    if len(source) == len(target) and source:
        for source_row, source_col in source:
            for target_row, target_col in target:
                delta = target_row - source_row, target_col - source_col
                shifted = tuple(sorted(
                    (row + delta[0], col + delta[1])
                    for row, col in source
                ))
                if shifted == tuple(sorted(target)):
                    return ("translate", delta[0], delta[1])
    return (
        "support_change",
        len(source),
        len(target),
    )


def fiber_mechanism_effect(
    source: FiberFactors,
    target: FiberFactors,
) -> tuple[Hashable, ...]:
    """Return the factor mechanism, excluding render-label changes."""
    changes: list[Hashable] = []
    controlled = _controlled_effect(
        source.controlled_base,
        target.controlled_base,
    )
    if controlled != ("fixed",):
        changes.append(("controlled_base", controlled))
    if source.finite_configuration != target.finite_configuration:
        changes.append((
            "finite_configuration",
            source.finite_configuration,
            target.finite_configuration,
        ))
    if source.operation_domain_assignment != target.operation_domain_assignment:
        changes.append((
            "operation_domain_assignment",
            source.operation_domain_assignment,
            target.operation_domain_assignment,
        ))
    if (
        source.ordered_feasibility_configuration
        != target.ordered_feasibility_configuration
    ):
        before = sum(source.ordered_feasibility_configuration)
        after = sum(target.ordered_feasibility_configuration)
        changes.append((
            "ordered_feasibility_configuration",
            after - before,
        ))
    budget_delta = target.ordered_budget - source.ordered_budget
    if budget_delta:
        changes.append(("ordered_budget", budget_delta))
    if source.one_shot_availability != target.one_shot_availability:
        before = dict(source.one_shot_availability)
        after = dict(target.one_shot_availability)
        changed = tuple(sorted(
            (identity, before.get(identity), after.get(identity))
            for identity in set(before) | set(after)
            if before.get(identity) != after.get(identity)
        ))
        changes.append(("one_shot_availability", changed))
    return tuple(changes) if changes else (("identity",),)


def fiber_exception_weight(
    _row: PartialActionObservation,
    effect: Hashable,
) -> float:
    """Structural exception weight, independent of substrate values."""
    if isinstance(effect, tuple) and effect[:1] == ("boundary",):
        return 8.0
    rows = effect if isinstance(effect, tuple) else ()
    weight = 0.0
    for item in rows:
        if not isinstance(item, tuple) or not item:
            continue
        factor = item[0]
        if factor == "ordered_budget" and len(item) > 1 and item[1] > 0:
            weight += 7.0
        elif factor == "ordered_feasibility_configuration":
            weight += 5.0
        elif factor == "finite_configuration":
            weight += 5.0
        elif factor == "one_shot_availability":
            weight += 4.0
        elif factor == "operation_domain_assignment":
            weight += 3.0
        elif (
            factor == "controlled_base"
            and len(item) > 1
            and isinstance(item[1], tuple)
            and item[1][:1] == ("support_change",)
        ):
            weight += 3.0
    return weight


def transition_boundary_kind(transition: Any) -> str:
    identity = getattr(transition, "identity", None)
    kind = str(getattr(identity, "kind", "") or "")
    source_epoch = getattr(identity, "source_epoch", None)
    target_epoch = getattr(identity, "target_epoch", None)
    if kind in {"epoch_boundary", "reset_boundary"}:
        return kind
    if (
        source_epoch is not None
        and target_epoch is not None
        and source_epoch != target_epoch
    ):
        return "epoch_boundary"
    return ""


def guarded_skill_traces_from_history_evidence(
    history_trajectories: Iterable[HistoryTrajectoryEvidence],
    *,
    projection: Any,
    history_lift: Any = None,
) -> tuple[Any, ...]:
    """Lower ordered worldmodel evidence into opaque common skill traces.

    Discontinuous rows start a new trace and reset history. Adapter or declared
    lifecycle boundaries remain typed transition tokens with no successor.
    The lowering does not infer missing operations or task valence.
    """
    from ztare.common.guarded_skill_compiler import (
        GuardedActionTrace,
        GuardedTraceTransition,
    )

    traces = []

    def source_key(
        state: Any,
        action_history: tuple[Hashable, ...],
        operation_effect_history: tuple[Hashable, ...],
    ) -> Hashable:
        factors = projection.factor(state)
        if history_lift is None:
            return fiber_transition_key(factors)
        return history_lift.start_key(
            factors,
            observation=state,
            action_history=action_history,
            operation_effect_history=operation_effect_history,
        )

    for trajectory in history_trajectories:
        actions = tuple(trajectory.action_prefix)
        operation_effects = tuple(trajectory.operation_effect_prefix)
        rows = []
        segment_index = 0
        prior = None

        def flush() -> None:
            nonlocal rows, segment_index
            if not rows:
                return
            traces.append(GuardedActionTrace(
                trace_ref=(
                    f"{trajectory.evidence_ref}::segment:{segment_index}"
                ),
                transitions=tuple(rows),
            ))
            rows = []
            segment_index += 1

        for index, transition in enumerate(trajectory.transitions):
            if prior is not None and not _transition_pair_is_continuous(
                prior,
                transition,
            ):
                flush()
                actions = ()
                operation_effects = ()
            boundary_kind = (
                transition_boundary_kind(transition)
                or (
                    "observed_degeneration"
                    if index in trajectory.boundary_indices
                    else ""
                )
            )
            current_key = source_key(
                transition.s,
                actions,
                operation_effects,
            )
            evidence_ref = f"{trajectory.evidence_ref}#{index}"
            if boundary_kind:
                rows.append(GuardedTraceTransition(
                    source=current_key,
                    operation=transition.a,
                    successor=None,
                    effect=None,
                    evidence_ref=evidence_ref,
                    boundary_kind=boundary_kind,
                ))
                actions = ()
                operation_effects = ()
                prior = transition
                continue
            effect_value = fiber_mechanism_effect(
                projection.factor(transition.s),
                projection.factor(transition.s_next),
            )
            next_actions = (*actions, transition.a)
            next_effects = (
                *operation_effects,
                (
                    "operation_effect",
                    transition.a,
                    stable_sha256(effect_value),
                ),
            )
            next_key = source_key(
                transition.s_next,
                next_actions,
                next_effects,
            )
            rows.append(GuardedTraceTransition(
                source=current_key,
                operation=transition.a,
                successor=next_key,
                effect=effect_value,
                evidence_ref=evidence_ref,
            ))
            actions = next_actions
            operation_effects = next_effects
            prior = transition
        flush()
    return tuple(traces)


def compile_history_guarded_skill_library(
    history_trajectories: Iterable[HistoryTrajectoryEvidence],
    *,
    projection: Any,
    history_lift: Any = None,
    guarded_traces: Iterable[Any] | None = None,
    min_word_length: int = 2,
    max_word_length: int = 8,
    min_variant_support: int = 2,
) -> Any:
    """Compile the common guarded library from worldmodel trajectories."""
    from ztare.common.guarded_skill_compiler import (
        compile_guarded_skill_library,
    )

    traces = (
        tuple(guarded_traces)
        if guarded_traces is not None
        else guarded_skill_traces_from_history_evidence(
            history_trajectories,
            projection=projection,
            history_lift=history_lift,
        )
    )
    if not traces:
        return None
    return compile_guarded_skill_library(
        traces,
        min_word_length=min_word_length,
        max_word_length=max_word_length,
        min_variant_support=min_variant_support,
    )


def build_fiber_action_system(
    transitions: Iterable[Any],
    *,
    projection: Any,
    evidence_ref: str,
    explicit_boundary_indices: frozenset[int] = frozenset(),
    explicit_boundary_edges: Iterable[tuple[Any, ...]] = (),
    boundary_predicate: Callable[[Any, Any, Any], bool] | None = None,
) -> PartialActionSystem:
    """Compile transition evidence through one accepted factor projection."""
    observations: list[PartialActionObservation] = []
    factor_cache: dict[int, FiberFactors] = {}

    def factors(state: Any) -> FiberFactors:
        key = id(state)
        if key not in factor_cache:
            factor_cache[key] = projection.factor(state)
        return factor_cache[key]

    def project(state: Any) -> Hashable:
        return fiber_transition_key(factors(state))

    def effect(
        source: Any,
        _operation: Hashable,
        successor: Any,
        _source_key: Hashable,
        _target_key: Hashable,
    ) -> Hashable:
        return fiber_mechanism_effect(factors(source), factors(successor))

    for index, transition in enumerate(transitions):
        declared_boundary = (
            "observed_degeneration"
            if index in explicit_boundary_indices
            else transition_boundary_kind(transition)
        )
        control_boundary = bool(
            not declared_boundary
            and boundary_predicate is not None
            and boundary_predicate(
                transition.s,
                transition.a,
                getattr(transition, "t", None),
            )
        )
        boundary = (
            declared_boundary
            or ("control_exclusion" if control_boundary else "")
        )
        observations.append(PartialActionObservation(
            source=transition.s,
            operation=transition.a,
            successor=None if boundary else transition.s_next,
            evidence_ref=f"{evidence_ref}#{index}",
            boundary_kind=boundary,
            context={
                "time": getattr(transition, "t", None),
                "index": index,
            },
        ))
    for index, (
        source,
        operation,
        boundary_ref,
        _action_history,
        _operation_effect_history,
        boundary_kind,
    ) in enumerate(
        _normalize_boundary_edges(explicit_boundary_edges)
    ):
        observations.append(PartialActionObservation(
            source=source,
            operation=operation,
            successor=None,
            evidence_ref=boundary_ref,
            boundary_kind=boundary_kind,
            context={
                "source": "explicit_boundary_edge",
                "index": index,
            },
        ))
    return build_partial_action_system(
        observations,
        project=project,
        effect=effect,
        projection_id=projection.projection_sha256,
        exceptional_weight=fiber_exception_weight,
    )


def guarded_skill_option_specs(
    library: Any,
    *,
    operation_namespace: str,
    additional_programs: Iterable[Any] = (),
) -> tuple[Any, ...]:
    """Bind compiled motor chunks to the persistent option reindexer."""

    from ztare.common.boundary_reachability import OptionProgramSpec

    namespace = str(operation_namespace).strip()
    if not namespace:
        raise ValueError(
            "guarded skill option binding requires operation_namespace"
        )
    programs_by_revision = {}
    for program in (*library.programs, *tuple(additional_programs)):
        prior = programs_by_revision.get(program.skill_sha256)
        if prior is not None and prior != program:
            raise ValueError("skill revision identity collision")
        programs_by_revision[program.skill_sha256] = program
    specs = []
    for program in sorted(
        programs_by_revision.values(),
        key=lambda row: row.skill_sha256,
    ):
        initiation_digests = tuple(sorted({
            stable_sha256(occurrence.initiation_key)
            for occurrence in program.occurrences
        }))
        lineage_refs = tuple(sorted({
            evidence_ref
            for occurrence in program.occurrences
            for evidence_ref in occurrence.evidence_refs
        }))
        if not initiation_digests or not lineage_refs:
            continue
        family_sha = program.structural_sha256(namespace)
        specs.append(OptionProgramSpec(
            operations=program.operations,
            initiation_source_sha256s=initiation_digests,
            lineage_refs=lineage_refs,
            imported_ref=(
                "guarded_motor_chunk:" + program.skill_sha256
            ),
            source_family_sha256=family_sha,
            source_revision_sha256=program.skill_sha256,
        ))
    return tuple(sorted(
        specs,
        key=lambda spec: spec.option_sha256,
    ))


__all__ = [
    "HistoryAnnotatedState",
    "HistoryLiftSelection",
    "HistoryTrajectoryEvidence",
    "build_fiber_action_system",
    "fiber_exception_weight",
    "fiber_mechanism_effect",
    "fiber_transition_key",
    "guarded_skill_option_specs",
    "operation_effect_token",
    "predictive_prefixes_from_transitions",
    "select_fiber_history_action_system",
    "transition_boundary_kind",
]
