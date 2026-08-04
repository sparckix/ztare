"""Temporal derivatives of externally settled object-response programs.

An object response learned at one observation is a program over future
object-role events, not an immutable list that can be copied through time.
This module:

* induces the common ordered program of multiple supported offer witnesses;
* consumes completed waypoints only under exact, pre-outcome lineage events;
* compiles proposal transitions against the residual program; and
* exposes the observed response offspring number.

It does not use task labels, proposal prose, embeddings, target outcomes, or
post-outcome event selection.  Ambiguous program induction, event binding, or
lineage refuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
    estimate_instrumented_plasticity,
)
from ztare.common.object_basin_response import (
    ObjectBasinResponse,
    ObjectResponseFamily,
)
from ztare.common.object_lineage_transport import (
    CausalObjectLineageTransport,
    ObjectLineageEvent,
    ObjectLineageTrace,
)
from ztare.common.object_linked_judgment import (
    ObjectLinkedControllerProposal,
    ObjectLinkedProposalTransition,
    ObjectReferenceAuthority,
    ObjectRolePathContract,
)
from ztare.common.wake_sleep_credit_router import MemoryScope
from ztare.gates.event_family_binding_gate import (
    run_event_family_binding_gate,
)


SCHEMA = "ztare-causal-response-derivative-v1"
_PROGRAM_STATUSES = frozenset({"compiled", "refused"})
_DERIVATIVE_STATUSES = frozenset({"derived", "refused"})
_ASSIGNMENTS = frozenset({"offer", "withhold"})
_RESPONSE_STATUSES = frozenset({
    "identified_positive",
    "identified_nonpositive",
    "weak_instrument",
    "undersampled",
})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip() for value in values if str(value).strip()
    }))


def _ordered(values: Iterable[str], name: str) -> tuple[str, ...]:
    rows = tuple(_nonempty(value, name) for value in values)
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not repeat values")
    return rows


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or int(value) != value or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _contains_subsequence(
    observed: Sequence[str],
    required: Sequence[str],
) -> bool:
    if not required:
        return True
    index = 0
    for value in observed:
        if value == required[index]:
            index += 1
            if index == len(required):
                return True
    return False


def _unique_longest_common_subsequence(
    rows: Sequence[Sequence[str]],
) -> tuple[str, ...] | None:
    if not rows:
        return None
    shortest = min((tuple(row) for row in rows), key=len)
    if len(shortest) > 16:
        raise ValueError("response witness path exceeds bounded LCS surface")
    candidates: set[tuple[str, ...]] = set()
    for length in range(len(shortest), 0, -1):
        for indices in combinations(range(len(shortest)), length):
            candidate = tuple(shortest[index] for index in indices)
            if all(_contains_subsequence(row, candidate) for row in rows):
                candidates.add(candidate)
        if candidates:
            return next(iter(candidates)) if len(candidates) == 1 else None
    return None


@dataclass(frozen=True)
class CausalResponseProgram:
    """Common object-role program induced from supported response witnesses."""

    source_family_sha256: str
    source_response_sha256: str
    source_contract_sha256: str
    source_scope_sha256: str
    source_observation_sha256: str
    source_catalog_sha256: str
    source_intervention_revision_sha256: str
    controlled_object_ref: str
    ordered_waypoint_refs: tuple[str, ...]
    support_transition_sha256s: tuple[str, ...]
    support_post_proposal_sha256s: tuple[str, ...]
    status: str
    reason: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "source_family_sha256",
            "source_response_sha256",
            "source_contract_sha256",
            "source_scope_sha256",
            "source_observation_sha256",
            "source_catalog_sha256",
            "source_intervention_revision_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _PROGRAM_STATUSES:
            raise ValueError(f"unknown response program status {self.status!r}")
        controlled = str(self.controlled_object_ref or "").strip()
        waypoints = tuple(self.ordered_waypoint_refs)
        if self.status == "compiled":
            _nonempty(controlled, "controlled_object_ref")
            waypoints = _ordered(waypoints, "ordered_waypoint_refs")
            if not waypoints:
                raise ValueError("compiled response program needs waypoints")
        elif controlled or waypoints:
            raise ValueError("refused response program cannot expose a program")
        object.__setattr__(self, "controlled_object_ref", controlled)
        object.__setattr__(self, "ordered_waypoint_refs", waypoints)
        transitions = _canonical(self.support_transition_sha256s)
        posts = _canonical(self.support_post_proposal_sha256s)
        if self.status == "compiled" and (
            len(transitions) < 2 or len(posts) < 2
        ):
            raise ValueError("compiled response program needs two supports")
        object.__setattr__(
            self,
            "support_transition_sha256s",
            transitions,
        )
        object.__setattr__(
            self,
            "support_post_proposal_sha256s",
            posts,
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("response program requires evidence refs")
        object.__setattr__(self, "evidence_refs", evidence)

    @property
    def support_count(self) -> int:
        return len(self.support_transition_sha256s)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "causal_response_program",
            "source_family_sha256": self.source_family_sha256,
            "source_response_sha256": self.source_response_sha256,
            "source_contract_sha256": self.source_contract_sha256,
            "source_scope_sha256": self.source_scope_sha256,
            "source_observation_sha256": (
                self.source_observation_sha256
            ),
            "source_catalog_sha256": self.source_catalog_sha256,
            "source_intervention_revision_sha256": (
                self.source_intervention_revision_sha256
            ),
            "controlled_object_ref": self.controlled_object_ref,
            "ordered_waypoint_refs": list(self.ordered_waypoint_refs),
            "support_count": self.support_count,
            "support_transition_sha256s": list(
                self.support_transition_sha256s
            ),
            "support_post_proposal_sha256s": list(
                self.support_post_proposal_sha256s
            ),
            "status": self.status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _refused_program(
    *,
    family: ObjectResponseFamily,
    response: ObjectBasinResponse,
    contract: ObjectRolePathContract,
    reason: str,
    evidence_refs: Iterable[str],
) -> CausalResponseProgram:
    return CausalResponseProgram(
        source_family_sha256=family.sha256,
        source_response_sha256=response.sha256,
        source_contract_sha256=contract.sha256,
        source_scope_sha256=contract.scope.sha256,
        source_observation_sha256=contract.scope.context_sha256,
        source_catalog_sha256=contract.catalog_sha256,
        source_intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        controlled_object_ref="",
        ordered_waypoint_refs=(),
        support_transition_sha256s=(),
        support_post_proposal_sha256s=(),
        status="refused",
        reason=reason,
        evidence_refs=tuple(evidence_refs),
    )


def compile_causal_response_program(
    family: ObjectResponseFamily,
    response: ObjectBasinResponse,
    contract: ObjectRolePathContract,
    witnesses: Sequence[
        tuple[
            ObjectLinkedProposalTransition,
            ObjectLinkedControllerProposal,
            ObjectLinkedControllerProposal,
        ]
    ],
    *,
    evidence_refs: Iterable[str],
) -> CausalResponseProgram:
    """Induce the unique shared program of settled supported offer witnesses."""

    evidence = tuple(evidence_refs)
    family_matches = [
        row for row in family.responses if row.sha256 == response.sha256
    ]
    if (
        len(family_matches) != 1
        or not response.admissible
        or response.contract_sha256 != contract.sha256
        or response.scope_sha256 != contract.scope.sha256
        or response.catalog_sha256 != contract.catalog_sha256
        or response.intervention_revision_sha256
        != contract.intervention_revision_sha256
    ):
        return _refused_program(
            family=family,
            response=response,
            contract=contract,
            reason="response_family_or_contract_authority_mismatch",
            evidence_refs=evidence,
        )
    if len(witnesses) < 2:
        return _refused_program(
            family=family,
            response=response,
            contract=contract,
            reason="insufficient_supported_offer_witnesses",
            evidence_refs=evidence,
        )
    controls = set()
    waypoint_rows: list[tuple[str, ...]] = []
    transition_shas = []
    post_shas = []
    for transition, pre, post in witnesses:
        valid = bool(
            transition.assignment == "offer"
            and transition.supported_transport
            and transition.relation == "offered_supported_transport"
            and transition.contract_sha256 == contract.sha256
            and transition.intervention_revision_sha256
            == contract.intervention_revision_sha256
            and transition.pre_basin_sha256
            == response.pre_basin_sha256
            and transition.pre_proposal_sha256 == pre.sha256
            and transition.post_proposal_sha256 == post.sha256
            and pre.scope == contract.scope
            and post.scope == contract.scope
            and pre.catalog_sha256 == contract.catalog_sha256
            and post.catalog_sha256 == contract.catalog_sha256
            and post.consumed_intervention_revision_sha256
            == contract.intervention_revision_sha256
        )
        if not valid:
            return _refused_program(
                family=family,
                response=response,
                contract=contract,
                reason="support_witness_authority_mismatch",
                evidence_refs=evidence,
            )
        controls.add(post.controlled_object_ref)
        waypoint_rows.append(post.ordered_waypoint_refs)
        transition_shas.append(transition.sha256)
        post_shas.append(post.sha256)
    if len(controls) != 1:
        return _refused_program(
            family=family,
            response=response,
            contract=contract,
            reason="supported_witnesses_have_no_unique_common_control",
            evidence_refs=evidence,
        )
    common = _unique_longest_common_subsequence(waypoint_rows)
    if not common:
        return _refused_program(
            family=family,
            response=response,
            contract=contract,
            reason="supported_witnesses_have_no_unique_common_waypoints",
            evidence_refs=evidence,
        )
    return CausalResponseProgram(
        source_family_sha256=family.sha256,
        source_response_sha256=response.sha256,
        source_contract_sha256=contract.sha256,
        source_scope_sha256=contract.scope.sha256,
        source_observation_sha256=contract.scope.context_sha256,
        source_catalog_sha256=contract.catalog_sha256,
        source_intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        controlled_object_ref=next(iter(controls)),
        ordered_waypoint_refs=common,
        support_transition_sha256s=tuple(transition_shas),
        support_post_proposal_sha256s=tuple(post_shas),
        status="compiled",
        reason="unique_common_control_and_ordered_program",
        evidence_refs=evidence,
    )


@dataclass(frozen=True)
class ResponseDerivativeDischarge:
    """One source waypoint consumed by a pre-outcome joint event."""

    source_waypoint_ref: str
    target_waypoint_ref: str
    hop_index: int
    transition_sha256: str
    occlusion_event_sha256: str
    reappearance_event_sha256: str
    coevent_source_object_ref: str
    coevent_revision_event_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "source_waypoint_ref",
            "target_waypoint_ref",
            "transition_sha256",
            "occlusion_event_sha256",
            "reappearance_event_sha256",
            "coevent_source_object_ref",
            "coevent_revision_event_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.hop_index <= 0:
            raise ValueError("discharge hop must be positive")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "response_derivative_discharge",
            "source_waypoint_ref": self.source_waypoint_ref,
            "target_waypoint_ref": self.target_waypoint_ref,
            "hop_index": self.hop_index,
            "transition_sha256": self.transition_sha256,
            "occlusion_event_sha256": self.occlusion_event_sha256,
            "reappearance_event_sha256": (
                self.reappearance_event_sha256
            ),
            "coevent_source_object_ref": (
                self.coevent_source_object_ref
            ),
            "coevent_revision_event_sha256": (
                self.coevent_revision_event_sha256
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ResidualResponseContract:
    """Future obligations remaining after a certified event prefix."""

    scope: MemoryScope
    catalog_sha256: str
    intervention_revision_sha256: str
    source_program_sha256: str
    lineage_transport_sha256: str
    required_controlled_object_ref: str
    pending_waypoint_refs: tuple[str, ...]
    discharged_waypoint_refs: tuple[str, ...]
    forbidden_controlled_object_refs: tuple[str, ...]
    discharge_receipt_sha256s: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "catalog_sha256",
            "intervention_revision_sha256",
            "source_program_sha256",
            "lineage_transport_sha256",
            "required_controlled_object_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        pending = _ordered(
            self.pending_waypoint_refs,
            "pending_waypoint_refs",
        )
        discharged = _ordered(
            self.discharged_waypoint_refs,
            "discharged_waypoint_refs",
        )
        if set(pending) & set(discharged):
            raise ValueError("waypoint cannot be pending and discharged")
        object.__setattr__(self, "pending_waypoint_refs", pending)
        object.__setattr__(
            self,
            "discharged_waypoint_refs",
            discharged,
        )
        forbidden = _canonical(self.forbidden_controlled_object_refs)
        if self.required_controlled_object_ref in forbidden:
            raise ValueError("required control cannot also be forbidden")
        object.__setattr__(
            self,
            "forbidden_controlled_object_refs",
            forbidden,
        )
        receipts = _canonical(self.discharge_receipt_sha256s)
        if len(receipts) != len(discharged):
            raise ValueError("each discharged waypoint needs one receipt")
        object.__setattr__(
            self,
            "discharge_receipt_sha256s",
            receipts,
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("residual contract requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_response_contract",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "catalog_sha256": self.catalog_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "source_program_sha256": self.source_program_sha256,
            "lineage_transport_sha256": (
                self.lineage_transport_sha256
            ),
            "required_controlled_object_ref": (
                self.required_controlled_object_ref
            ),
            "pending_waypoint_refs": list(self.pending_waypoint_refs),
            "discharged_waypoint_refs": list(
                self.discharged_waypoint_refs
            ),
            "forbidden_controlled_object_refs": list(
                self.forbidden_controlled_object_refs
            ),
            "discharge_receipt_sha256s": list(
                self.discharge_receipt_sha256s
            ),
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class CausalResponseDerivative:
    source_program_sha256: str
    lineage_transport_sha256: str
    source_observation_sha256: str
    target_observation_sha256: str
    event_family_binding_sha256: str
    event_selection_phase: str
    discharges: tuple[ResponseDerivativeDischarge, ...]
    residual_contract: ResidualResponseContract | None
    status: str
    reason: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "source_program_sha256",
            "lineage_transport_sha256",
            "source_observation_sha256",
            "target_observation_sha256",
            "event_family_binding_sha256",
            "event_selection_phase",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _DERIVATIVE_STATUSES:
            raise ValueError(f"unknown derivative status {self.status!r}")
        if self.status == "derived" and self.residual_contract is None:
            raise ValueError("derived response needs a residual contract")
        if self.status == "refused" and self.residual_contract is not None:
            raise ValueError("refused derivative cannot expose a contract")
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("response derivative requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "causal_response_derivative",
            "source_program_sha256": self.source_program_sha256,
            "lineage_transport_sha256": (
                self.lineage_transport_sha256
            ),
            "source_observation_sha256": (
                self.source_observation_sha256
            ),
            "target_observation_sha256": (
                self.target_observation_sha256
            ),
            "event_family_binding_sha256": (
                self.event_family_binding_sha256
            ),
            "event_selection_phase": self.event_selection_phase,
            "discharges": [
                row.to_receipt() for row in self.discharges
            ],
            "residual_contract": (
                self.residual_contract.to_receipt()
                if self.residual_contract is not None
                else None
            ),
            "status": self.status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def response_derivative_event_family_binding_receipt(
    program: CausalResponseProgram,
    lineage: CausalObjectLineageTransport,
) -> dict[str, Any]:
    """Build the exact pre-payoff event-family identity receipt."""

    return {
        "relation_type": "identity",
        "target_event_family": (
            f"response_program_waypoints:{program.sha256}"
        ),
        "source_event_family": (
            f"causal_object_lineage_events:{lineage.sha256}"
        ),
        "event_identity": stable_sha256({
            "program_waypoints": list(program.ordered_waypoint_refs),
            "lineage_roots": list(lineage.required_source_object_refs),
            "lineage_transport_sha256": lineage.sha256,
        }),
        "pre_payoff_timing": "frozen_before_target_proposal_and_outcome",
        "same_carrier": (
            f"source_observation:{lineage.source_observation_sha256}"
        ),
        "same_owner_or_source": (
            f"source_program:{program.sha256}"
        ),
        "index_map": "program_waypoint_ref_to_unique_lineage_root",
        "index_map_total_on_prefix": all(
            waypoint in set(lineage.required_source_object_refs)
            for waypoint in program.ordered_waypoint_refs
        ),
        "no_proxy_family": "exact_lineage_roots_only",
        "no_post_payoff_selection": "event_selection_phase_pre_outcome",
    }


def _refused_derivative(
    *,
    program: CausalResponseProgram,
    lineage: CausalObjectLineageTransport,
    binding_sha256: str,
    event_selection_phase: str,
    reason: str,
    evidence_refs: Iterable[str],
) -> CausalResponseDerivative:
    return CausalResponseDerivative(
        source_program_sha256=program.sha256,
        lineage_transport_sha256=lineage.sha256,
        source_observation_sha256=(
            lineage.source_observation_sha256
        ),
        target_observation_sha256=(
            lineage.target_observation_sha256
        ),
        event_family_binding_sha256=binding_sha256,
        event_selection_phase=event_selection_phase,
        discharges=(),
        residual_contract=None,
        status="refused",
        reason=reason,
        evidence_refs=tuple(evidence_refs),
    )


def _trace_by_root(
    lineage: CausalObjectLineageTransport,
) -> dict[str, ObjectLineageTrace]:
    return {row.source_object_ref: row for row in lineage.traces}


def _next_event(
    trace: ObjectLineageTrace,
    event: ObjectLineageEvent,
) -> ObjectLineageEvent | None:
    rows = [
        row for row in trace.events
        if row.hop_index == event.hop_index + 1
    ]
    return rows[0] if len(rows) == 1 else None


def compile_causal_response_derivative(
    program: CausalResponseProgram,
    lineage: CausalObjectLineageTransport,
    *,
    target_scope: MemoryScope,
    target_intervention_revision_sha256: str,
    source_forbidden_controlled_object_refs: Iterable[str],
    event_family_binding_receipt: Mapping[str, Any],
    event_selection_phase: str,
    evidence_refs: Iterable[str],
) -> CausalResponseDerivative:
    """Compute the residual response program before target outcome."""

    evidence = tuple(evidence_refs)
    binding = dict(event_family_binding_receipt)
    binding_sha = stable_sha256(binding)
    gate = run_event_family_binding_gate(binding, enforce_block=True)
    if program.status != "compiled":
        return _refused_derivative(
            program=program,
            lineage=lineage,
            binding_sha256=binding_sha,
            event_selection_phase=event_selection_phase,
            reason="source_response_program_refused",
            evidence_refs=evidence,
        )
    if event_selection_phase != "pre_outcome":
        return _refused_derivative(
            program=program,
            lineage=lineage,
            binding_sha256=binding_sha,
            event_selection_phase=event_selection_phase,
            reason="event_selection_not_pre_outcome",
            evidence_refs=evidence,
        )
    if not gate["passed"] or not gate["complete"]:
        return _refused_derivative(
            program=program,
            lineage=lineage,
            binding_sha256=binding_sha,
            event_selection_phase=event_selection_phase,
            reason="event_family_binding_refused",
            evidence_refs=evidence,
        )
    if (
        lineage.status != "transportable"
        or program.source_observation_sha256
        != lineage.source_observation_sha256
        or program.source_catalog_sha256
        != lineage.source_catalog_sha256
        or target_scope.context_sha256
        != lineage.target_observation_sha256
    ):
        return _refused_derivative(
            program=program,
            lineage=lineage,
            binding_sha256=binding_sha,
            event_selection_phase=event_selection_phase,
            reason="program_lineage_or_target_authority_mismatch",
            evidence_refs=evidence,
        )
    roots = set(lineage.required_source_object_refs)
    required_roots = {
        program.controlled_object_ref,
        *program.ordered_waypoint_refs,
        *tuple(source_forbidden_controlled_object_refs),
    }
    if not required_roots.issubset(roots):
        return _refused_derivative(
            program=program,
            lineage=lineage,
            binding_sha256=binding_sha,
            event_selection_phase=event_selection_phase,
            reason="lineage_not_total_on_program",
            evidence_refs=evidence,
        )

    traces = _trace_by_root(lineage)
    all_events = tuple(
        event for trace in lineage.traces for event in trace.events
    )
    discharges: list[ResponseDerivativeDischarge] = []
    pending_source: list[str] = []
    for waypoint in program.ordered_waypoint_refs:
        trace = traces[waypoint]
        occlusions = [
            row for row in trace.events
            if row.relation == "bracketed_occlusion_enter"
        ]
        if not occlusions:
            pending_source.append(waypoint)
            continue
        if len(occlusions) != 1:
            return _refused_derivative(
                program=program,
                lineage=lineage,
                binding_sha256=binding_sha,
                event_selection_phase=event_selection_phase,
                reason="ambiguous_waypoint_occlusion_event",
                evidence_refs=evidence,
            )
        occlusion = occlusions[0]
        reappearance = _next_event(trace, occlusion)
        if (
            reappearance is None
            or reappearance.relation != "unique_reappearance_exit"
        ):
            return _refused_derivative(
                program=program,
                lineage=lineage,
                binding_sha256=binding_sha,
                event_selection_phase=event_selection_phase,
                reason="waypoint_occlusion_not_uniquely_bracketed",
                evidence_refs=evidence,
            )
        coevents = [
            row for row in all_events
            if row.lineage_sha256 != occlusion.lineage_sha256
            and row.hop_index == occlusion.hop_index
            and row.transition_sha256 == occlusion.transition_sha256
            and row.relation
            == "unique_fixed_support_appearance_revision"
        ]
        if len(coevents) != 1:
            return _refused_derivative(
                program=program,
                lineage=lineage,
                binding_sha256=binding_sha,
                event_selection_phase=event_selection_phase,
                reason=(
                    "joint_discharge_coevent_missing"
                    if not coevents
                    else "joint_discharge_coevent_ambiguous"
                ),
                evidence_refs=evidence,
            )
        coevent = coevents[0]
        coevent_trace = next(
            row for row in lineage.traces
            if row.lineage_sha256 == coevent.lineage_sha256
        )
        discharges.append(ResponseDerivativeDischarge(
            source_waypoint_ref=waypoint,
            target_waypoint_ref=lineage.map_ref(waypoint),
            hop_index=occlusion.hop_index,
            transition_sha256=occlusion.transition_sha256,
            occlusion_event_sha256=occlusion.sha256,
            reappearance_event_sha256=reappearance.sha256,
            coevent_source_object_ref=(
                coevent_trace.source_object_ref
            ),
            coevent_revision_event_sha256=coevent.sha256,
        ))

    residual = ResidualResponseContract(
        scope=target_scope,
        catalog_sha256=lineage.target_catalog_sha256,
        intervention_revision_sha256=_nonempty(
            target_intervention_revision_sha256,
            "target_intervention_revision_sha256",
        ),
        source_program_sha256=program.sha256,
        lineage_transport_sha256=lineage.sha256,
        required_controlled_object_ref=lineage.map_ref(
            program.controlled_object_ref
        ),
        pending_waypoint_refs=lineage.map_path(pending_source),
        discharged_waypoint_refs=tuple(
            row.target_waypoint_ref for row in discharges
        ),
        forbidden_controlled_object_refs=lineage.map_path(
            source_forbidden_controlled_object_refs
        ),
        discharge_receipt_sha256s=tuple(
            row.sha256 for row in discharges
        ),
        evidence_refs=(
            *evidence,
            f"program:{program.sha256}",
            f"lineage:{lineage.sha256}",
            f"event_family_binding:{binding_sha}",
        ),
    )
    return CausalResponseDerivative(
        source_program_sha256=program.sha256,
        lineage_transport_sha256=lineage.sha256,
        source_observation_sha256=lineage.source_observation_sha256,
        target_observation_sha256=lineage.target_observation_sha256,
        event_family_binding_sha256=binding_sha,
        event_selection_phase=event_selection_phase,
        discharges=tuple(discharges),
        residual_contract=residual,
        status="derived",
        reason="joint_event_prefix_consumed_response_waypoints",
        evidence_refs=evidence,
    )


def proposal_satisfies_residual_response(
    proposal: ObjectLinkedControllerProposal,
    contract: ResidualResponseContract,
) -> bool:
    if proposal.scope != contract.scope:
        raise ValueError("proposal and residual scopes differ")
    if proposal.catalog_sha256 != contract.catalog_sha256:
        raise ValueError("proposal and residual catalogs differ")
    return bool(
        proposal.controlled_object_ref
        == contract.required_controlled_object_ref
        and proposal.controlled_object_ref
        not in set(contract.forbidden_controlled_object_refs)
        and _contains_subsequence(
            proposal.ordered_waypoint_refs,
            contract.pending_waypoint_refs,
        )
    )


def residual_plan_basin_signature(
    proposal: ObjectLinkedControllerProposal,
    contract: ResidualResponseContract,
) -> dict[str, Any]:
    if proposal.scope != contract.scope:
        raise ValueError("proposal and residual scopes differ")
    if proposal.catalog_sha256 != contract.catalog_sha256:
        raise ValueError("proposal and residual catalogs differ")
    if (
        proposal.controlled_object_ref
        == contract.required_controlled_object_ref
    ):
        control = "required"
    elif proposal.controlled_object_ref in set(
        contract.forbidden_controlled_object_refs
    ):
        control = "forbidden"
    else:
        control = "other"
    prefix = 0
    for observed, required in zip(
        proposal.ordered_waypoint_refs,
        contract.pending_waypoint_refs,
    ):
        if observed != required:
            break
        prefix += 1
    return {
        "control_relation": control,
        "pending_waypoint_prefix_length": prefix,
        "pending_waypoint_order_satisfied": _contains_subsequence(
            proposal.ordered_waypoint_refs,
            contract.pending_waypoint_refs,
        ),
    }


def residual_plan_basin_sha256(
    proposal: ObjectLinkedControllerProposal,
    contract: ResidualResponseContract,
) -> str:
    return stable_sha256({
        "scope_sha256": contract.scope.sha256,
        "contract_sha256": contract.sha256,
        "catalog_sha256": contract.catalog_sha256,
        **residual_plan_basin_signature(proposal, contract),
    })


@dataclass(frozen=True)
class ResidualProposalTransition:
    """One offer/withhold displacement scored against a residual program."""

    scope: MemoryScope
    trial_ref: str
    stratum_sha256: str
    controller_instance_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    source_program_sha256: str
    derivative_sha256: str
    assignment: str
    pre_proposal_sha256: str
    post_proposal_sha256: str
    pre_basin_sha256: str
    relation: str
    changed_action: bool
    changed_prediction: bool
    changed_path: bool
    supported_transport: bool

    def __post_init__(self) -> None:
        for name in (
            "trial_ref",
            "stratum_sha256",
            "controller_instance_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "source_program_sha256",
            "derivative_sha256",
            "pre_proposal_sha256",
            "post_proposal_sha256",
            "pre_basin_sha256",
            "relation",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.assignment not in _ASSIGNMENTS:
            raise ValueError(f"unknown derivative assignment {self.assignment!r}")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_proposal_transition",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "trial_ref": self.trial_ref,
            "stratum_sha256": self.stratum_sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "source_program_sha256": self.source_program_sha256,
            "derivative_sha256": self.derivative_sha256,
            "assignment": self.assignment,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "post_proposal_sha256": self.post_proposal_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "relation": self.relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
            "changed_path": self.changed_path,
            "supported_transport": self.supported_transport,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_residual_proposal_transition(
    *,
    trial_ref: str,
    stratum_sha256: str,
    assignment: str,
    pre_proposal: ObjectLinkedControllerProposal,
    post_proposal: ObjectLinkedControllerProposal,
    derivative: CausalResponseDerivative,
    authority: ObjectReferenceAuthority,
) -> ResidualProposalTransition:
    if derivative.status != "derived" or derivative.residual_contract is None:
        raise ValueError("refused derivative cannot score a proposal")
    contract = derivative.residual_contract
    allowed = set(authority.object_refs)
    for proposal in (pre_proposal, post_proposal):
        if (
            proposal.scope != contract.scope
            or proposal.observation_sha256
            != authority.observation_sha256
            or proposal.catalog_sha256 != authority.catalog_sha256
            or not set(proposal.path).issubset(allowed)
        ):
            raise ValueError("proposal crossed residual authority")
    if post_proposal.parent_proposal_sha256 != pre_proposal.sha256:
        raise ValueError("post proposal has wrong residual parent")
    if (
        post_proposal.controller_instance_sha256
        != pre_proposal.controller_instance_sha256
    ):
        raise ValueError("proposal controller instance drifted")
    consumed = post_proposal.consumed_intervention_revision_sha256
    if assignment == "offer":
        if consumed != contract.intervention_revision_sha256:
            raise ValueError("offered derivative revision was not consumed")
    elif assignment == "withhold":
        if consumed:
            raise ValueError("withheld derivative cannot consume revision")
    else:
        raise ValueError(f"unknown assignment {assignment!r}")

    before = proposal_satisfies_residual_response(pre_proposal, contract)
    after = proposal_satisfies_residual_response(post_proposal, contract)
    changed_action = pre_proposal.action_ref != post_proposal.action_ref
    changed_prediction = (
        pre_proposal.predicted_consequence_ref
        != post_proposal.predicted_consequence_ref
    )
    changed_path = pre_proposal.path != post_proposal.path
    meaningful = changed_action or changed_prediction or changed_path
    supported = bool(changed_path and after and not before)
    contradicted = (
        post_proposal.controlled_object_ref
        in set(contract.forbidden_controlled_object_refs)
    )
    if assignment == "offer":
        if supported:
            relation = "offered_supported_derivative"
        elif before and after:
            relation = "offered_already_satisfied"
        elif contradicted:
            relation = "offered_contradiction"
        elif meaningful:
            relation = "offered_other_derivative"
        else:
            relation = "offered_no_uptake"
    else:
        if supported:
            relation = "withheld_spontaneous_derivative"
        elif before and after:
            relation = "withheld_already_satisfied"
        elif contradicted:
            relation = "withheld_spontaneous_contradiction"
        elif meaningful:
            relation = "withheld_spontaneous_other"
        else:
            relation = "withheld_stable"
    return ResidualProposalTransition(
        scope=contract.scope,
        trial_ref=trial_ref,
        stratum_sha256=stratum_sha256,
        controller_instance_sha256=(
            pre_proposal.controller_instance_sha256
        ),
        contract_sha256=contract.sha256,
        intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        catalog_sha256=contract.catalog_sha256,
        source_program_sha256=contract.source_program_sha256,
        derivative_sha256=derivative.sha256,
        assignment=assignment,
        pre_proposal_sha256=pre_proposal.sha256,
        post_proposal_sha256=post_proposal.sha256,
        pre_basin_sha256=residual_plan_basin_sha256(
            pre_proposal,
            contract,
        ),
        relation=relation,
        changed_action=changed_action,
        changed_prediction=changed_prediction,
        changed_path=changed_path,
        supported_transport=supported,
    )


@dataclass(frozen=True)
class ResidualBasinResponse:
    """Externally settled response for one derivative-relative proposal basin."""

    scope_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    source_program_sha256: str
    derivative_sha256: str
    pre_basin_sha256: str
    status: str
    offer_count: int
    withhold_count: int
    offer_supported_transport_rate: float
    withhold_supported_transport_rate: float
    first_stage_transport_delta: float
    intent_to_treat_net_delta: float
    complier_net_effect: float | None
    primitive_action_cost: float
    outcome_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "scope_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "source_program_sha256",
            "derivative_sha256",
            "pre_basin_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.status not in _RESPONSE_STATUSES:
            raise ValueError(
                f"unknown residual response status {self.status!r}"
            )
        if self.offer_count < 0 or self.withhold_count < 0:
            raise ValueError("residual response counts must be nonnegative")
        for name in (
            "offer_supported_transport_rate",
            "withhold_supported_transport_rate",
            "first_stage_transport_delta",
            "intent_to_treat_net_delta",
        ):
            object.__setattr__(
                self,
                name,
                _finite(getattr(self, name), name),
            )
        if self.complier_net_effect is not None:
            object.__setattr__(
                self,
                "complier_net_effect",
                _finite(
                    self.complier_net_effect,
                    "complier_net_effect",
                ),
            )
        object.__setattr__(
            self,
            "primitive_action_cost",
            _nonnegative(
                self.primitive_action_cost,
                "primitive_action_cost",
            ),
        )
        outcomes = _canonical(self.outcome_sha256s)
        if len(outcomes) != self.offer_count + self.withhold_count:
            raise ValueError(
                "residual outcome identities do not match sample count"
            )
        object.__setattr__(self, "outcome_sha256s", outcomes)

    @property
    def admissible(self) -> bool:
        return self.status == "identified_positive"

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_basin_response",
            "scope_sha256": self.scope_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "source_program_sha256": self.source_program_sha256,
            "derivative_sha256": self.derivative_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "status": self.status,
            "admissible": self.admissible,
            "offer_count": self.offer_count,
            "withhold_count": self.withhold_count,
            "offer_supported_transport_rate": (
                self.offer_supported_transport_rate
            ),
            "withhold_supported_transport_rate": (
                self.withhold_supported_transport_rate
            ),
            "first_stage_transport_delta": (
                self.first_stage_transport_delta
            ),
            "intent_to_treat_net_delta": (
                self.intent_to_treat_net_delta
            ),
            "complier_net_effect": self.complier_net_effect,
            "primitive_action_cost": self.primitive_action_cost,
            "outcome_sha256s": list(self.outcome_sha256s),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ResidualResponseFamily:
    """Settled descendant family owned by one response derivative."""

    scope_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    catalog_sha256: str
    source_program_sha256: str
    derivative_sha256: str
    source_settlement_ref: str
    source_settlement_sha256: str
    minimum_offer_count: int
    minimum_withhold_count: int
    minimum_first_stage_transport_delta: float
    minimum_intent_to_treat_net_delta: float
    responses: tuple[ResidualBasinResponse, ...]

    def __post_init__(self) -> None:
        for name in (
            "scope_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "catalog_sha256",
            "source_program_sha256",
            "derivative_sha256",
            "source_settlement_ref",
            "source_settlement_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "minimum_offer_count",
            _positive_int(self.minimum_offer_count, "minimum_offer_count"),
        )
        object.__setattr__(
            self,
            "minimum_withhold_count",
            _positive_int(
                self.minimum_withhold_count,
                "minimum_withhold_count",
            ),
        )
        object.__setattr__(
            self,
            "minimum_first_stage_transport_delta",
            _nonnegative(
                self.minimum_first_stage_transport_delta,
                "minimum_first_stage_transport_delta",
            ),
        )
        object.__setattr__(
            self,
            "minimum_intent_to_treat_net_delta",
            _finite(
                self.minimum_intent_to_treat_net_delta,
                "minimum_intent_to_treat_net_delta",
            ),
        )
        responses = tuple(
            sorted(self.responses, key=lambda row: row.pre_basin_sha256)
        )
        if not responses:
            raise ValueError("residual response family needs responses")
        if len({row.pre_basin_sha256 for row in responses}) != len(
            responses
        ):
            raise ValueError("residual family repeats a pre-basin")
        identity = (
            self.scope_sha256,
            self.contract_sha256,
            self.intervention_revision_sha256,
            self.catalog_sha256,
            self.source_program_sha256,
            self.derivative_sha256,
        )
        if any(
            (
                row.scope_sha256,
                row.contract_sha256,
                row.intervention_revision_sha256,
                row.catalog_sha256,
                row.source_program_sha256,
                row.derivative_sha256,
            )
            != identity
            for row in responses
        ):
            raise ValueError("response crossed residual-family authority")
        object.__setattr__(self, "responses", responses)

    @property
    def admissible_response_count(self) -> int:
        return sum(row.admissible for row in self.responses)

    @property
    def promoted(self) -> bool:
        return self.admissible_response_count > 0

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "residual_response_family",
            "scope_sha256": self.scope_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "catalog_sha256": self.catalog_sha256,
            "source_program_sha256": self.source_program_sha256,
            "derivative_sha256": self.derivative_sha256,
            "source_settlement_ref": self.source_settlement_ref,
            "source_settlement_sha256": self.source_settlement_sha256,
            "minimum_offer_count": self.minimum_offer_count,
            "minimum_withhold_count": self.minimum_withhold_count,
            "minimum_first_stage_transport_delta": (
                self.minimum_first_stage_transport_delta
            ),
            "minimum_intent_to_treat_net_delta": (
                self.minimum_intent_to_treat_net_delta
            ),
            "admissible_response_count": self.admissible_response_count,
            "promoted": self.promoted,
            "responses": [row.to_receipt() for row in self.responses],
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_residual_response_family(
    outcomes: Sequence[InstrumentedProposalOutcome],
    *,
    derivative: CausalResponseDerivative,
    source_settlement_ref: str,
    source_settlement_sha256: str,
    minimum_offer_count: int = 2,
    minimum_withhold_count: int = 2,
    minimum_first_stage_transport_delta: float = 1.0,
    minimum_intent_to_treat_net_delta: float = 0.0,
) -> ResidualResponseFamily:
    """Promote only derivative-owned randomized settlements."""

    if derivative.status != "derived" or derivative.residual_contract is None:
        raise ValueError("response family requires a derived contract")
    rows = tuple(outcomes)
    if not rows:
        raise ValueError("residual response family requires outcomes")
    transitions = tuple(row.transition for row in rows)
    if not all(
        isinstance(row, ResidualProposalTransition)
        for row in transitions
    ):
        raise ValueError(
            "residual family requires residual proposal transitions"
        )
    contract = derivative.residual_contract
    expected_identity = (
        contract.scope.sha256,
        contract.sha256,
        contract.intervention_revision_sha256,
        contract.catalog_sha256,
        contract.source_program_sha256,
        derivative.sha256,
    )
    identities = {
        (
            row.scope.sha256,
            row.contract_sha256,
            row.intervention_revision_sha256,
            row.catalog_sha256,
            row.source_program_sha256,
            row.derivative_sha256,
        )
        for row in transitions
    }
    if identities != {expected_identity}:
        raise ValueError("outcomes crossed residual derivative authority")
    primitive_costs = {row.primitive_action_cost for row in rows}
    if len(primitive_costs) != 1:
        raise ValueError("outcomes crossed primitive action cost")
    minimum_offers = _positive_int(
        minimum_offer_count,
        "minimum_offer_count",
    )
    minimum_withholds = _positive_int(
        minimum_withhold_count,
        "minimum_withhold_count",
    )
    minimum_first_stage = _nonnegative(
        minimum_first_stage_transport_delta,
        "minimum_first_stage_transport_delta",
    )
    minimum_itt = _finite(
        minimum_intent_to_treat_net_delta,
        "minimum_intent_to_treat_net_delta",
    )
    grouped: dict[str, list[InstrumentedProposalOutcome]] = {}
    for outcome in rows:
        grouped.setdefault(
            outcome.transition.pre_basin_sha256,
            [],
        ).append(outcome)
    responses = []
    for pre_basin, group in sorted(grouped.items()):
        group_rows = tuple(group)
        offer_count = sum(
            row.transition.assignment == "offer"
            for row in group_rows
        )
        withhold_count = len(group_rows) - offer_count
        estimate = estimate_instrumented_plasticity(
            group_rows,
            minimum_first_stage=minimum_first_stage,
        )
        if (
            offer_count < minimum_offers
            or withhold_count < minimum_withholds
        ):
            status = "undersampled"
        elif estimate.status != "identified":
            status = "weak_instrument"
        elif estimate.intent_to_treat_net_delta > minimum_itt:
            status = "identified_positive"
        else:
            status = "identified_nonpositive"
        responses.append(ResidualBasinResponse(
            scope_sha256=expected_identity[0],
            contract_sha256=expected_identity[1],
            intervention_revision_sha256=expected_identity[2],
            catalog_sha256=expected_identity[3],
            source_program_sha256=expected_identity[4],
            derivative_sha256=expected_identity[5],
            pre_basin_sha256=pre_basin,
            status=status,
            offer_count=estimate.offer_count,
            withhold_count=estimate.withhold_count,
            offer_supported_transport_rate=(
                estimate.offer_supported_transport_rate
            ),
            withhold_supported_transport_rate=(
                estimate.withhold_supported_transport_rate
            ),
            first_stage_transport_delta=(
                estimate.first_stage_transport_delta
            ),
            intent_to_treat_net_delta=(
                estimate.intent_to_treat_net_delta
            ),
            complier_net_effect=estimate.complier_net_effect,
            primitive_action_cost=next(iter(primitive_costs)),
            outcome_sha256s=estimate.outcome_sha256s,
        ))
    return ResidualResponseFamily(
        scope_sha256=expected_identity[0],
        contract_sha256=expected_identity[1],
        intervention_revision_sha256=expected_identity[2],
        catalog_sha256=expected_identity[3],
        source_program_sha256=expected_identity[4],
        derivative_sha256=expected_identity[5],
        source_settlement_ref=source_settlement_ref,
        source_settlement_sha256=source_settlement_sha256,
        minimum_offer_count=minimum_offers,
        minimum_withhold_count=minimum_withholds,
        minimum_first_stage_transport_delta=minimum_first_stage,
        minimum_intent_to_treat_net_delta=minimum_itt,
        responses=tuple(responses),
    )


@dataclass(frozen=True)
class ResponseReproductionEstimate:
    """Observed offspring operator for one response-schema population."""

    response_schema_sha256: str
    parent_family_sha256s: tuple[str, ...]
    promoted_child_family_sha256s: tuple[str, ...]
    false_edge_count: int
    primitive_action_cost: float
    response_reproduction_number: float
    spectral_radius_lower_bound: float
    regime: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("response_schema_sha256", "regime"):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        parents = _canonical(self.parent_family_sha256s)
        children = _canonical(self.promoted_child_family_sha256s)
        if not parents:
            raise ValueError("reproduction estimate requires parents")
        if self.false_edge_count < 0:
            raise ValueError("false edge count must be nonnegative")
        if not math.isfinite(self.primitive_action_cost) or (
            self.primitive_action_cost < 0
        ):
            raise ValueError("primitive action cost must be nonnegative")
        expected = len(children) / len(parents)
        if not math.isclose(
            self.response_reproduction_number,
            expected,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("response reproduction number drifted")
        if not math.isclose(
            self.spectral_radius_lower_bound,
            expected,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("spectral radius lower bound drifted")
        expected_regime = (
            "subcritical"
            if expected < 1.0
            else "critical"
            if expected == 1.0
            else "supercritical"
        )
        if self.regime != expected_regime:
            raise ValueError("response reproduction regime drifted")
        object.__setattr__(self, "parent_family_sha256s", parents)
        object.__setattr__(
            self,
            "promoted_child_family_sha256s",
            children,
        )
        evidence = _canonical(self.evidence_refs)
        if not evidence:
            raise ValueError("reproduction estimate requires evidence")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "response_reproduction_estimate",
            "response_schema_sha256": self.response_schema_sha256,
            "parent_family_sha256s": list(
                self.parent_family_sha256s
            ),
            "promoted_child_family_sha256s": list(
                self.promoted_child_family_sha256s
            ),
            "parent_count": len(self.parent_family_sha256s),
            "promoted_child_count": len(
                self.promoted_child_family_sha256s
            ),
            "false_edge_count": self.false_edge_count,
            "primitive_action_cost": self.primitive_action_cost,
            "response_reproduction_number": (
                self.response_reproduction_number
            ),
            "spectral_radius_lower_bound": (
                self.spectral_radius_lower_bound
            ),
            "regime": self.regime,
            "critical_boundary": 1.0,
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_response_reproduction_estimate(
    *,
    response_schema_sha256: str,
    parent_family_sha256s: Iterable[str],
    promoted_child_family_sha256s: Iterable[str],
    false_edge_count: int,
    primitive_action_cost: float,
    evidence_refs: Iterable[str],
) -> ResponseReproductionEstimate:
    parents = _canonical(parent_family_sha256s)
    children = _canonical(promoted_child_family_sha256s)
    if not parents:
        raise ValueError("reproduction estimate requires a parent")
    number = len(children) / len(parents)
    regime = (
        "subcritical"
        if number < 1.0
        else "critical"
        if number == 1.0
        else "supercritical"
    )
    return ResponseReproductionEstimate(
        response_schema_sha256=response_schema_sha256,
        parent_family_sha256s=parents,
        promoted_child_family_sha256s=children,
        false_edge_count=int(false_edge_count),
        primitive_action_cost=float(primitive_action_cost),
        response_reproduction_number=number,
        spectral_radius_lower_bound=number,
        regime=regime,
        evidence_refs=tuple(evidence_refs),
    )


__all__ = [
    "CausalResponseDerivative",
    "CausalResponseProgram",
    "ResidualProposalTransition",
    "ResidualBasinResponse",
    "ResidualResponseFamily",
    "ResidualResponseContract",
    "ResponseDerivativeDischarge",
    "ResponseReproductionEstimate",
    "compile_causal_response_derivative",
    "compile_causal_response_program",
    "compile_residual_proposal_transition",
    "compile_residual_response_family",
    "compile_response_reproduction_estimate",
    "proposal_satisfies_residual_response",
    "residual_plan_basin_sha256",
    "residual_plan_basin_signature",
    "response_derivative_event_family_binding_receipt",
]
