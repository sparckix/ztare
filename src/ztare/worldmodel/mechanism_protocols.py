"""Lower witnessed partial-action routes into guarded experiment protocols.

This adapter assigns no task value.  It follows a proposed preparation through
the evidence-owned partial action relation, then builds the probe's response
committee from sources that remain predictively compatible with the target and
on which that probe was actually witnessed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolAssignment,
    GuardedProtocolCandidate,
    GuardedProtocolSelection,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    select_guarded_protocol,
)
from ztare.common.guarded_skill_compiler import (
    GuardedSkillLibrary,
    GuardedSkillProgram,
    compile_guarded_execution_plan,
)
from ztare.common.partial_action_system import PartialActionSystem
from ztare.common.predictive_quotient import PredictiveCompatibility


def _stable(values: Iterable[Hashable]) -> tuple[Hashable, ...]:
    return tuple(sorted(values, key=stable_sha256))


def _witnessed_successor(
    system: PartialActionSystem,
    source_key: Hashable,
    operation: Hashable,
) -> Hashable | None:
    relation_key = source_key, operation
    effects = system.relation_effects.get(relation_key, ())
    targets = system.relation_targets.get(relation_key, ())
    if (
        len(effects) != 1
        or len(targets) != 1
        or any(
            (operation, effect) in system.boundary_kinds
            for effect in effects
        )
    ):
        return None
    return next(iter(targets))


def _continuation_signature(
    system: PartialActionSystem,
    source_key: Hashable,
    operations: tuple[Hashable, ...],
) -> tuple[Any, ...]:
    """One evidence-owned readout layer after a proposed probe."""

    rows = []
    for operation in operations:
        effects = system.relation_effects.get((source_key, operation))
        if effects is None:
            rows.append((operation, "unknown"))
            continue
        boundaries = _stable(
            system.boundary_kinds[(operation, effect)]
            for effect in effects
            if (operation, effect) in system.boundary_kinds
        )
        rows.append((
            operation,
            "observed",
            _stable(effects),
            boundaries,
        ))
    return tuple(rows)


def _probe_response(
    system: PartialActionSystem,
    source_key: Hashable,
    probe: Hashable,
    operations: tuple[Hashable, ...],
) -> Hashable:
    relation_key = source_key, probe
    effects = _stable(system.relation_effects[relation_key])
    boundaries = _stable(
        system.boundary_kinds[(probe, effect)]
        for effect in effects
        if (probe, effect) in system.boundary_kinds
    )
    targets = _stable(system.relation_targets.get(relation_key, ()))
    continuations = tuple(sorted(
        (
            _continuation_signature(system, target, operations)
            for target in targets
        ),
        key=stable_sha256,
    ))
    return (
        "typed_boundary_response" if boundaries else "observed_response",
        effects,
        boundaries,
        continuations,
    )


@dataclass(frozen=True)
class WitnessedProtocolLowering:
    candidate: GuardedProtocolCandidate
    preparation_key_sha256s: tuple[str, ...]
    response_readout_operations: tuple[Hashable, ...]
    control_plan_receipt: dict[str, Any] | None
    pricing_control_plan_receipt: dict[str, Any] | None = None
    schema: str = "ztare-witnessed-protocol-lowering-v1"

    def to_receipt(self, *, evidence_cap: int = 8) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "protocol": self.candidate.protocol.identity_receipt(),
            "preparation_key_sha256s": list(
                self.preparation_key_sha256s
            ),
            "response_readout_operation_sha256s": [
                stable_sha256(operation)
                for operation in self.response_readout_operations
            ],
            "committee": [
                {
                    "hypothesis_id": row.hypothesis_id,
                    "response_sha256": stable_sha256(row.response),
                    "description_units": row.description_units,
                    "evidence_ref_count": len(row.evidence_refs),
                    "evidence_refs_sha256": stable_sha256(
                        tuple(sorted(row.evidence_refs))
                    ),
                    "evidence_refs": list(
                        sorted(row.evidence_refs)[:max(
                            0,
                            int(evidence_cap),
                        )]
                    ),
                }
                for row in sorted(
                    self.candidate.committee,
                    key=lambda item: item.hypothesis_id,
                )
            ],
            "control_plan": self.control_plan_receipt,
            "decision_control_plan": self.pricing_control_plan_receipt,
        }


@dataclass(frozen=True)
class WitnessedProtocolPortfolio:
    """One priced family of routes with a single selected protocol identity."""

    lowerings: tuple[WitnessedProtocolLowering, ...]
    selection: GuardedProtocolSelection
    schema: str = "ztare-witnessed-protocol-portfolio-v1"

    @property
    def selected_operations(self) -> tuple[Hashable, ...]:
        selected_id = self.selection.selected_protocol_id
        return next(
            (
                lowering.candidate.protocol.operations
                for lowering in self.lowerings
                if lowering.candidate.protocol.protocol_id == selected_id
            ),
            (),
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "selection": self.selection.to_receipt(),
            "selected_operation_sha256s": [
                stable_sha256(operation)
                for operation in self.selected_operations
            ],
            "lowerings": [
                lowering.to_receipt()
                for lowering in self.lowerings
            ],
        }


@dataclass(frozen=True)
class MechanismAcquisitionFrontiers:
    """The complete producer family for one acquisition decision."""

    observed: Any
    boundary: Any
    predictive_quotient: Any
    predictive_support: Any
    predictive_quotient_is_orbit_completion: bool
    schema: str = "ztare-mechanism-acquisition-frontiers-v1"

    def named_frontiers(self) -> tuple[tuple[str, Any], ...]:
        quotient_id = (
            "predictive_quotient_orbit_completion"
            if self.predictive_quotient_is_orbit_completion
            else "predictive_quotient_frontier"
        )
        proposed = (
            ("observed_partial_action_frontier", self.observed),
            ("boundary_reachability_frontier", self.boundary),
            (quotient_id, self.predictive_quotient),
            ("predictive_compatibility_support", self.predictive_support),
        )
        accepted_statuses = {
            "frontier_pair_found",
            "support_gap_found",
            "boundary_relevant_frontier_found",
        }
        return tuple(
            (protocol_id, frontier)
            for protocol_id, frontier in proposed
            if (
                frontier is not None
                and bool(getattr(frontier, "actions", ()))
                and getattr(frontier, "status", None) in accepted_statuses
            )
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "producer_slots": [
                "observed",
                "boundary",
                "predictive_quotient",
                "predictive_support",
            ],
            "admitted_protocol_ids": [
                protocol_id
                for protocol_id, _frontier in self.named_frontiers()
            ],
            "predictive_quotient_is_orbit_completion": (
                self.predictive_quotient_is_orbit_completion
            ),
        }


@dataclass(frozen=True)
class WitnessedAcquisitionProtocolPortfolio:
    """A complete frontier family and its one evidence-priced decision."""

    frontiers: MechanismAcquisitionFrontiers
    candidates: tuple[tuple[str, Any], ...]
    portfolio: WitnessedProtocolPortfolio
    schema: str = "ztare-witnessed-acquisition-protocol-portfolio-v1"

    @property
    def lowerings(self) -> tuple[WitnessedProtocolLowering, ...]:
        return self.portfolio.lowerings

    @property
    def selection(self) -> GuardedProtocolSelection:
        return self.portfolio.selection

    @property
    def selected_operations(self) -> tuple[Hashable, ...]:
        return self.portfolio.selected_operations

    @property
    def selected_frontier(self) -> Any | None:
        selected_id = self.selection.selected_protocol_id
        return next(
            (
                frontier
                for protocol_id, frontier in self.candidates
                if protocol_id == selected_id
            ),
            None,
        )

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "frontiers": self.frontiers.to_receipt(),
            "portfolio": self.portfolio.to_receipt(),
        }


def lower_witnessed_protocol(
    system: PartialActionSystem,
    compatibility: PredictiveCompatibility,
    *,
    start_key: Hashable,
    actions: Iterable[Hashable],
    protocol_id: str,
    skill_library: GuardedSkillLibrary | None = None,
    allowed_skill_sha256s: frozenset[str] | None = None,
    additional_skill_programs: Iterable[GuardedSkillProgram] = (),
    pricing_allowed_skill_invocations: (
        frozenset[tuple[str, str]] | None
    ) = None,
) -> WitnessedProtocolLowering:
    """Lower one route without borrowing any missing transition.

    All operations except the last are preparation.  The final operation is
    the probe.  Preparation must commute through singly witnessed,
    non-boundary relations.  The response committee consists only of
    compatible sources with an evidence-owned response to the probe.
    """

    operation_word = tuple(actions)
    if not operation_word:
        raise ValueError("a protocol requires at least one probe operation")
    preparation = operation_word[:-1]
    probe = operation_word[-1]
    cursor = start_key
    key_path = [cursor]
    preparation_refs = []
    guard_reason = ""
    for index, operation in enumerate(preparation):
        next_key = _witnessed_successor(system, cursor, operation)
        if next_key is None:
            guard_reason = (
                f"preparation relation undefined or noncommuting at index "
                f"{index}"
            )
            break
        preparation_refs.extend(
            system.relation_evidence_refs.get(
                (cursor, operation),
                (),
            )
        )
        cursor = next_key
        key_path.append(cursor)
    guard_admitted = not guard_reason
    control_plan = None
    pricing_control_plan = None
    control_units = float(len(preparation))
    if guard_admitted and skill_library is not None:
        control_plan = compile_guarded_execution_plan(
            skill_library,
            start_key=start_key,
            operations=preparation,
            transition=lambda source, operation: _witnessed_successor(
                system,
                source,
                operation,
            ),
            allowed_skill_sha256s=allowed_skill_sha256s,
            additional_programs=additional_skill_programs,
        )
        pricing_control_plan = (
            control_plan
            if pricing_allowed_skill_invocations is None
            else compile_guarded_execution_plan(
                skill_library,
                start_key=start_key,
                operations=preparation,
                transition=lambda source, operation: _witnessed_successor(
                    system,
                    source,
                    operation,
                ),
                allowed_skill_sha256s=allowed_skill_sha256s,
                allowed_skill_invocations=(
                    pricing_allowed_skill_invocations
                ),
                additional_programs=additional_skill_programs,
            )
        )
        if (
            pricing_control_plan.exact_expansion
            and pricing_control_plan.status
            in {"compiled_plan", "primitive_plan"}
        ):
            control_units = float(len(pricing_control_plan.tokens))

    committee = []
    if guard_admitted:
        for source in compatibility.sources:
            relation_key = source, probe
            if (
                source == cursor
                or not compatibility.is_compatible(cursor, source)
                or relation_key not in system.relation_effects
            ):
                continue
            refs = system.relation_evidence_refs.get(relation_key, ())
            if not refs:
                continue
            committee.append(ProtocolResponseHypothesis(
                hypothesis_id=stable_sha256(source),
                response=_probe_response(
                    system,
                    source,
                    probe,
                    compatibility.operations,
                ),
                description_units=1,
                evidence_refs=tuple(sorted(refs)),
            ))
    committee.sort(key=lambda row: row.hypothesis_id)
    protocol = GuardedExperimentProtocol(
        protocol_id=protocol_id,
        preparation=preparation,
        probe=probe,
        target_key=cursor,
        cost=ProtocolCost(
            preparation_execution_units=len(preparation),
            probe_execution_units=1,
            control_units=control_units,
        ),
        novel_context=(cursor, probe) not in system.relation_effects,
        guard_admitted=guard_admitted,
        guard_reason=guard_reason,
        evidence_refs=tuple(sorted({
            system.fibers[cursor].evidence_ref,
            *preparation_refs,
        })),
    )
    return WitnessedProtocolLowering(
        candidate=GuardedProtocolCandidate(
            protocol=protocol,
            committee=tuple(committee),
        ),
        preparation_key_sha256s=tuple(
            stable_sha256(key) for key in key_path
        ),
        response_readout_operations=tuple(compatibility.operations),
        control_plan_receipt=(
            control_plan.to_receipt()
            if control_plan is not None
            else None
        ),
        pricing_control_plan_receipt=(
            pricing_control_plan.to_receipt()
            if pricing_control_plan is not None
            else None
        ),
    )


def witnessed_protocol_response(
    system: PartialActionSystem,
    *,
    source_key: Hashable,
    probe: Hashable,
    response_readout_operations: Iterable[Hashable],
) -> Hashable:
    """Read one response from an already compiled witnessed relation."""

    relation_key = source_key, probe
    if relation_key not in system.relation_effects:
        raise ValueError("witnessed protocol response relation is absent")
    return _probe_response(
        system,
        source_key,
        probe,
        tuple(response_readout_operations),
    )


@dataclass(frozen=True)
class WitnessedProtocolResponseReadout:
    """One exact selected-protocol response reconstructed from evidence."""

    protocol_id: str
    source_key_sha256: str
    probe_sha256: str
    response: Hashable
    observation_evidence_ref: str
    boundary_kind: str = ""
    schema: str = "ztare-witnessed-protocol-response-readout-v1"

    @property
    def response_sha256(self) -> str:
        return stable_sha256(self.response)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "protocol_id": self.protocol_id,
            "source_key_sha256": self.source_key_sha256,
            "probe_sha256": self.probe_sha256,
            "response_sha256": self.response_sha256,
            "observation_evidence_ref": self.observation_evidence_ref,
            "boundary_kind": self.boundary_kind,
            "task_credit_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_witnessed_protocol_response_readout(
    system: PartialActionSystem,
    lowering: WitnessedProtocolLowering,
    *,
    observed_source_key: Hashable,
    observed_operation: Hashable,
    observed_successor_key: Hashable | None = None,
    observed_effect: Hashable | None = None,
    boundary_kind: str = "",
    observation_evidence_ref: str,
) -> WitnessedProtocolResponseReadout:
    """Apply one exact abstract observation to the frozen response compiler."""

    evidence_ref = str(observation_evidence_ref).strip()
    if not evidence_ref:
        raise ValueError("protocol response observation requires evidence")
    protocol = lowering.candidate.protocol
    if observed_source_key != protocol.target_key:
        raise ValueError("observed protocol source does not match target")
    if observed_operation != protocol.probe:
        raise ValueError("observed protocol operation does not match probe")
    if observed_source_key not in system.fibers:
        raise ValueError("observed protocol source lacks a witnessed fiber")
    kind = str(boundary_kind or "").strip()
    if kind:
        if observed_successor_key is not None:
            raise ValueError("boundary response cannot carry a successor")
        added_effect: Hashable = ("boundary", kind)
    else:
        if observed_successor_key is None or observed_effect is None:
            raise ValueError(
                "ordinary protocol response requires successor and effect"
            )
        try:
            hash(observed_successor_key)
            hash(observed_effect)
        except TypeError as error:
            raise TypeError(
                "observed successor and effect must be hashable"
            ) from error
        added_effect = observed_effect

    relation_key = observed_source_key, observed_operation
    effects = set(system.relation_effects.get(relation_key, ()))
    effects.add(added_effect)
    targets = set(system.relation_targets.get(relation_key, ()))
    if observed_successor_key is not None:
        targets.add(observed_successor_key)
    boundaries = _stable((
        *(
            system.boundary_kinds[(observed_operation, effect)]
            for effect in effects
            if (observed_operation, effect) in system.boundary_kinds
        ),
        *((kind,) if kind else ()),
    ))
    operations = tuple(lowering.response_readout_operations)
    continuations = tuple(sorted(
        (
            _continuation_signature(system, target, operations)
            for target in targets
        ),
        key=stable_sha256,
    ))
    response = (
        "typed_boundary_response" if boundaries else "observed_response",
        _stable(effects),
        boundaries,
        continuations,
    )
    return WitnessedProtocolResponseReadout(
        protocol_id=protocol.protocol_id,
        source_key_sha256=stable_sha256(observed_source_key),
        probe_sha256=stable_sha256(observed_operation),
        response=response,
        observation_evidence_ref=evidence_ref,
        boundary_kind=kind,
    )


def observe_witnessed_protocol_information_yield(
    system: PartialActionSystem,
    lowering: WitnessedProtocolLowering,
    forecast: Any,
    **observation: Any,
) -> tuple[WitnessedProtocolResponseReadout, Any]:
    """Reconstruct one response and measure it against its frozen forecast."""

    from ztare.common.protocol_information_yield import (
        observe_protocol_information_yield,
    )

    if forecast.protocol_id != lowering.candidate.protocol.protocol_id:
        raise ValueError("yield forecast and protocol lowering mismatch")
    readout = compile_witnessed_protocol_response_readout(
        system,
        lowering,
        **observation,
    )
    measured = observe_protocol_information_yield(
        forecast,
        observed_response=readout.response,
        observation_evidence_ref=readout.sha256,
    )
    return readout, measured


def select_witnessed_protocols(
    system: PartialActionSystem,
    compatibility: PredictiveCompatibility,
    *,
    start_key: Hashable,
    routes: Iterable[tuple[str, Iterable[Hashable]]],
    weights: ProtocolYieldWeights,
    skill_library: GuardedSkillLibrary | None = None,
    allowed_skill_sha256s: frozenset[str] | None = None,
    additional_skill_programs: Iterable[GuardedSkillProgram] = (),
    max_primitive_execution_units: float | None = None,
    pricing_allowed_skill_invocations: (
        frozenset[tuple[str, str]] | None
    ) = None,
    decision_calibration_resolver: (
        Callable[
            [tuple[str, ...]],
            tuple[Mapping[str, int], Mapping[str, int]],
        ] | None
    ) = None,
    decision_assignment_resolver: (
        Callable[
            [tuple[str, ...]],
            GuardedProtocolAssignment | None,
        ] | None
    ) = None,
) -> WitnessedProtocolPortfolio:
    """Lower and price every route through one shared selection door."""

    normalized = tuple(
        (str(protocol_id), tuple(actions))
        for protocol_id, actions in routes
    )
    protocol_ids = [protocol_id for protocol_id, _actions in normalized]
    if len(protocol_ids) != len(set(protocol_ids)):
        raise ValueError("protocol route IDs must be unique")
    additional_program_rows = tuple(additional_skill_programs)
    lowerings = tuple(
        lower_witnessed_protocol(
            system,
            compatibility,
            start_key=start_key,
            actions=actions,
            protocol_id=protocol_id,
            skill_library=skill_library,
            allowed_skill_sha256s=allowed_skill_sha256s,
            additional_skill_programs=additional_program_rows,
            pricing_allowed_skill_invocations=(
                pricing_allowed_skill_invocations
            ),
        )
        for protocol_id, actions in normalized
        if actions
    )
    candidates = tuple(
        lowering.candidate for lowering in lowerings
    )
    selection = select_guarded_protocol(
        candidates,
        weights=weights,
        max_primitive_execution_units=max_primitive_execution_units,
    )
    if selection.canonical_protocol_ids and (
        decision_calibration_resolver is not None
        or decision_assignment_resolver is not None
    ):
        task_values, contrast_priorities = ({}, {})
        if decision_calibration_resolver is not None:
            task_values, contrast_priorities = (
                decision_calibration_resolver(
                    selection.canonical_protocol_ids
                )
            )
        assignment = (
            decision_assignment_resolver(
                selection.canonical_protocol_ids
            )
            if decision_assignment_resolver is not None
            else None
        )
        selection = select_guarded_protocol(
            candidates,
            weights=weights,
            max_primitive_execution_units=max_primitive_execution_units,
            task_value_by_protocol_id=task_values,
            contrast_priority_by_protocol_id=contrast_priorities,
            assignment=assignment,
        )
    return WitnessedProtocolPortfolio(
        lowerings=lowerings,
        selection=selection,
    )


def select_acquisition_protocols(
    system: PartialActionSystem,
    compatibility: PredictiveCompatibility,
    *,
    start_key: Hashable,
    frontiers: MechanismAcquisitionFrontiers,
    weights: ProtocolYieldWeights,
    skill_library: GuardedSkillLibrary | None = None,
    allowed_skill_sha256s: frozenset[str] | None = None,
    additional_skill_programs: Iterable[GuardedSkillProgram] = (),
    max_primitive_execution_units: float | None = None,
    pricing_allowed_skill_invocations: (
        frozenset[tuple[str, str]] | None
    ) = None,
    decision_calibration_resolver: (
        Callable[
            [tuple[str, ...]],
            tuple[Mapping[str, int], Mapping[str, int]],
        ] | None
    ) = None,
    decision_assignment_resolver: (
        Callable[
            [tuple[str, ...]],
            GuardedProtocolAssignment | None,
        ] | None
    ) = None,
) -> WitnessedAcquisitionProtocolPortfolio:
    """Price the complete acquisition-producer family through one door."""

    candidates = frontiers.named_frontiers()
    portfolio = select_witnessed_protocols(
        system,
        compatibility,
        start_key=start_key,
        routes=(
            (protocol_id, frontier.actions)
            for protocol_id, frontier in candidates
        ),
        weights=weights,
        skill_library=skill_library,
        allowed_skill_sha256s=allowed_skill_sha256s,
        additional_skill_programs=additional_skill_programs,
        max_primitive_execution_units=max_primitive_execution_units,
        pricing_allowed_skill_invocations=(
            pricing_allowed_skill_invocations
        ),
        decision_calibration_resolver=(
            decision_calibration_resolver
        ),
        decision_assignment_resolver=(
            decision_assignment_resolver
        ),
    )
    return WitnessedAcquisitionProtocolPortfolio(
        frontiers=frontiers,
        candidates=candidates,
        portfolio=portfolio,
    )


__all__ = [
    "MechanismAcquisitionFrontiers",
    "WitnessedAcquisitionProtocolPortfolio",
    "WitnessedProtocolLowering",
    "WitnessedProtocolPortfolio",
    "WitnessedProtocolResponseReadout",
    "compile_witnessed_protocol_response_readout",
    "lower_witnessed_protocol",
    "observe_witnessed_protocol_information_yield",
    "select_acquisition_protocols",
    "select_witnessed_protocols",
    "witnessed_protocol_response",
]
