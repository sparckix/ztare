"""Compile controller-authored residual questions into a pre-outcome assay.

The controller owns question generation.  This module owns the identity and
soundness boundary between one settled failure and the existing residual
fission and sparse-settlement kernels.  It verifies the frozen controller
input/output authority, lowers exact response signatures into H98, and freezes
the H100 Walsh schedule before descendant environment contact.

Question semantics remain in the caller.  This module does not inspect ARC
states, infer a solution, observe descendant outcomes, settle causal effects,
or authorize a compounding claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Sequence

from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    ResidualFissionReceipt,
    ResidualNicheCandidate,
    ResponseFissionAuthority,
    SparseSettlementSchedule,
    compile_residual_fission,
    compile_sparse_settlement_schedule,
    stable_sha256,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-endogenous-residual-discovery-v1"


def _nonempty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _canonical(values: Iterable[object], name: str) -> tuple[str, ...]:
    rows = tuple(sorted({_nonempty(value, name) for value in values}))
    return rows


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _positive_integer(value: object, name: str) -> int:
    result = _nonnegative_integer(value, name)
    if result == 0:
        raise ValueError(f"{name} must be positive")
    return result


def _fraction(value: object, name: str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{name} must be an exact rational, not bool/float")
    try:
        result = value if isinstance(value, Fraction) else Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise TypeError(f"{name} must be an exact rational") from error
    return result


def _probability(value: object, name: str) -> Fraction:
    result = _fraction(value, name)
    if not Fraction(0) <= result <= Fraction(1):
        raise ValueError(f"{name} must be in [0, 1]")
    return result


def _nonnegative_fraction(value: object, name: str) -> Fraction:
    result = _fraction(value, name)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _fraction_receipt(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def measurement_axis_catalog_sha256(
    axes: Sequence[MeasurementAxis],
) -> str:
    """Content identity of one ordered measurement-axis catalog."""

    rows = tuple(axes)
    if not rows:
        raise ValueError("measurement-axis catalog is empty")
    if len({row.axis_id for row in rows}) != len(rows):
        raise ValueError("measurement-axis catalog repeats an identity")
    return stable_sha256({
        "schema": SCHEMA,
        "kind": "measurement_axis_catalog",
        "axes": [row.to_receipt() for row in rows],
    })


@dataclass(frozen=True)
class EndogenousResidualAuthority:
    """Exact owner and chronology of one controller proposal."""

    scope: MemoryScope
    measurement_catalog_sha256: str
    source_response_family_sha256: str
    source_program_sha256: str
    source_derivative_sha256: str
    settled_failure_sha256: str
    intervention_revision_sha256: str
    primitive_cost_unit: str
    parent_child_sha256s: tuple[str, ...]
    generation_index: int
    controller_instance_sha256: str
    stored_parent_response_id: str
    controller_response_id: str
    source_history_prefix_sha256: str
    source_environment_step: int
    controller_prompt_sha256: str
    raw_controller_output_sha256: str
    canonical_controller_output_sha256: str
    allowed_input_evidence_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "measurement_catalog_sha256",
            "source_response_family_sha256",
            "source_program_sha256",
            "source_derivative_sha256",
            "settled_failure_sha256",
            "intervention_revision_sha256",
            "primitive_cost_unit",
            "controller_instance_sha256",
            "stored_parent_response_id",
            "controller_response_id",
            "source_history_prefix_sha256",
            "controller_prompt_sha256",
            "raw_controller_output_sha256",
            "canonical_controller_output_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        parents = _canonical(
            self.parent_child_sha256s,
            "parent_child_sha256s",
        )
        if not parents:
            raise ValueError("parent_child_sha256s are required")
        object.__setattr__(self, "parent_child_sha256s", parents)
        object.__setattr__(
            self,
            "generation_index",
            _positive_integer(self.generation_index, "generation_index"),
        )
        object.__setattr__(
            self,
            "source_environment_step",
            _nonnegative_integer(
                self.source_environment_step,
                "source_environment_step",
            ),
        )
        evidence = _canonical(
            self.allowed_input_evidence_sha256s,
            "allowed_input_evidence_sha256s",
        )
        required = {
            self.source_response_family_sha256,
            self.source_derivative_sha256,
            self.settled_failure_sha256,
            self.source_history_prefix_sha256,
        }
        missing = required - set(evidence)
        if missing:
            raise ValueError(
                "allowed input evidence omitted required source identities: "
                + ", ".join(sorted(missing))
            )
        object.__setattr__(
            self,
            "allowed_input_evidence_sha256s",
            evidence,
        )
        if self.controller_response_id == self.stored_parent_response_id:
            raise ValueError(
                "controller response must descend from, not relabel, its parent"
            )

    @property
    def fission_derivative_sha256(self) -> str:
        """Proposal-bound derivative used by the downstream H98 authority."""

        return stable_sha256({
            "schema": SCHEMA,
            "kind": "proposal_bound_residual_derivative",
            "source_derivative_sha256": self.source_derivative_sha256,
            "proposal_authority_sha256": self.sha256,
        })

    def to_fission_authority(self) -> ResponseFissionAuthority:
        return ResponseFissionAuthority(
            scope=self.scope,
            catalog_sha256=self.measurement_catalog_sha256,
            source_program_sha256=self.source_program_sha256,
            derivative_sha256=self.fission_derivative_sha256,
            intervention_revision_sha256=self.intervention_revision_sha256,
            primitive_cost_unit=self.primitive_cost_unit,
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "endogenous_residual_authority",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "measurement_catalog_sha256": self.measurement_catalog_sha256,
            "source_response_family_sha256": (
                self.source_response_family_sha256
            ),
            "source_program_sha256": self.source_program_sha256,
            "source_derivative_sha256": self.source_derivative_sha256,
            "settled_failure_sha256": self.settled_failure_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "primitive_cost_unit": self.primitive_cost_unit,
            "parent_child_sha256s": list(self.parent_child_sha256s),
            "generation_index": self.generation_index,
            "controller_instance_sha256": self.controller_instance_sha256,
            "stored_parent_response_id": self.stored_parent_response_id,
            "controller_response_id": self.controller_response_id,
            "source_history_prefix_sha256": (
                self.source_history_prefix_sha256
            ),
            "source_environment_step": self.source_environment_step,
            "controller_prompt_sha256": self.controller_prompt_sha256,
            "raw_controller_output_sha256": (
                self.raw_controller_output_sha256
            ),
            "canonical_controller_output_sha256": (
                self.canonical_controller_output_sha256
            ),
            "allowed_input_evidence_sha256s": list(
                self.allowed_input_evidence_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class ControllerResidualQuestion:
    """One structured controller question, prior to descendant outcome."""

    authority_sha256: str
    question_ref: str
    question_payload_sha256: str
    response_signature: tuple[Fraction, ...]
    predicted_information_yield: Fraction
    offline_replay_cost: Fraction
    input_evidence_sha256s: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "authority_sha256",
            "question_ref",
            "question_payload_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        signature = tuple(
            _fraction(value, "response_signature")
            for value in self.response_signature
        )
        if not signature or not any(signature):
            raise ValueError("response_signature must be nonzero")
        object.__setattr__(self, "response_signature", signature)
        object.__setattr__(
            self,
            "predicted_information_yield",
            _probability(
                self.predicted_information_yield,
                "predicted_information_yield",
            ),
        )
        object.__setattr__(
            self,
            "offline_replay_cost",
            _nonnegative_fraction(
                self.offline_replay_cost,
                "offline_replay_cost",
            ),
        )
        evidence = _canonical(
            self.input_evidence_sha256s,
            "input_evidence_sha256s",
        )
        if not evidence:
            raise ValueError("question input evidence is required")
        object.__setattr__(self, "input_evidence_sha256s", evidence)

    def controller_payload(self) -> dict[str, Any]:
        """Canonical parsed content, excluding the separately bound authority."""

        return {
            "question_ref": self.question_ref,
            "question_payload_sha256": self.question_payload_sha256,
            "response_signature": [
                _fraction_receipt(value) for value in self.response_signature
            ],
            "predicted_information_yield": _fraction_receipt(
                self.predicted_information_yield
            ),
            "offline_replay_cost": _fraction_receipt(
                self.offline_replay_cost
            ),
            "input_evidence_sha256s": list(self.input_evidence_sha256s),
        }

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "controller_residual_question",
            "authority_sha256": self.authority_sha256,
            **self.controller_payload(),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def canonical_controller_output_sha256(
    questions: Sequence[ControllerResidualQuestion],
    *,
    modeled_interactions: Sequence[Sequence[str]] = (),
) -> str:
    """Identity of the parsed structured output before authority binding."""

    interactions = tuple(
        tuple(sorted(_nonempty(ref, "interaction question ref") for ref in row))
        for row in modeled_interactions
    )
    return stable_sha256({
        "schema": SCHEMA,
        "kind": "canonical_controller_residual_output",
        "questions": [row.controller_payload() for row in questions],
        "modeled_interactions": [list(row) for row in interactions],
    })


@dataclass(frozen=True)
class EndogenousResidualProposal:
    """Frozen controller output at the same environment step as its prompt."""

    authority: EndogenousResidualAuthority
    proposal_ref: str
    questions: tuple[ControllerResidualQuestion, ...]
    frozen_environment_step: int
    modeled_interactions: tuple[tuple[str, ...], ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proposal_ref",
            _nonempty(self.proposal_ref, "proposal_ref"),
        )
        rows = tuple(self.questions)
        if not rows:
            raise ValueError("endogenous residual proposal needs questions")
        if len({row.question_ref for row in rows}) != len(rows):
            raise ValueError("controller questions repeat a question ref")
        if any(row.authority_sha256 != self.authority.sha256 for row in rows):
            raise ValueError("controller question crossed proposal authority")
        allowed = set(self.authority.allowed_input_evidence_sha256s)
        for row in rows:
            evidence = set(row.input_evidence_sha256s)
            if not evidence.issubset(allowed):
                raise ValueError("question used evidence outside proposal input")
            if self.authority.settled_failure_sha256 not in evidence:
                raise ValueError("question omitted settled-failure evidence")
        object.__setattr__(self, "questions", rows)
        step = _nonnegative_integer(
            self.frozen_environment_step,
            "frozen_environment_step",
        )
        if step != self.authority.source_environment_step:
            raise ValueError(
                "proposal crossed the pre-outcome environment frontier"
            )
        object.__setattr__(self, "frozen_environment_step", step)
        interactions = tuple(tuple(row) for row in self.modeled_interactions)
        object.__setattr__(self, "modeled_interactions", interactions)
        actual_output_sha256 = canonical_controller_output_sha256(
            rows,
            modeled_interactions=interactions,
        )
        if (
            actual_output_sha256
            != self.authority.canonical_controller_output_sha256
        ):
            raise ValueError(
                "parsed questions do not match canonical controller output"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "endogenous_residual_proposal",
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "proposal_ref": self.proposal_ref,
            "questions": [row.to_receipt() for row in self.questions],
            "frozen_environment_step": self.frozen_environment_step,
            "modeled_interactions": [
                list(row) for row in self.modeled_interactions
            ],
            "controller_output_bound": True,
            "preoutcome_frontier_preserved": True,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class EndogenousResidualDiscoveryReceipt:
    """Pre-outcome proposal, rank quotient, and sparse assay identity."""

    proposal: EndogenousResidualProposal
    axes: tuple[MeasurementAxis, ...]
    fission: ResidualFissionReceipt
    schedule: SparseSettlementSchedule

    @property
    def status(self) -> str:
        if self.fission.independent_offspring_capacity > 1:
            return "preoutcome_branching_assay_candidate"
        return "insufficient_independent_residual_rank"

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "endogenous_residual_discovery_receipt",
            "status": self.status,
            "proposal": self.proposal.to_receipt(),
            "proposal_sha256": self.proposal.sha256,
            "measurement_axes": [row.to_receipt() for row in self.axes],
            "measurement_catalog_sha256": (
                measurement_axis_catalog_sha256(self.axes)
            ),
            "fission": self.fission.to_receipt(),
            "fission_sha256": self.fission.sha256,
            "schedule": self.schedule.to_receipt(),
            "schedule_sha256": self.schedule.sha256,
            "raw_question_count": len(self.proposal.questions),
            "direction_quotient_count": len(
                self.fission.direction_quotient_classes
            ),
            "independent_residual_rank": (
                self.fission.independent_offspring_capacity
            ),
            "sparse_trajectory_count": self.schedule.trajectory_count,
            "factorial_trajectory_count": (
                self.schedule.full_factorial_trajectory_count
            ),
            "strict_trajectory_savings": (
                self.schedule.trajectory_count
                < self.schedule.full_factorial_trajectory_count
            ),
            "live_settlement_required": True,
            "compounding_supported": False,
            "takeoff_supported": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_endogenous_residual_discovery(
    proposal: EndogenousResidualProposal,
    *,
    axes: Sequence[MeasurementAxis],
) -> EndogenousResidualDiscoveryReceipt:
    """Lower a frozen controller proposal into H98 fission and H100 assay."""

    axis_rows = tuple(axes)
    actual_catalog_sha256 = measurement_axis_catalog_sha256(axis_rows)
    if actual_catalog_sha256 != proposal.authority.measurement_catalog_sha256:
        raise ValueError("measurement-axis catalog crossed proposal authority")
    width = len(axis_rows)
    if any(len(row.response_signature) != width for row in proposal.questions):
        raise ValueError("controller signature crossed measurement-axis arity")

    fission_authority = proposal.authority.to_fission_authority()
    candidates = tuple(
        ResidualNicheCandidate(
            authority=fission_authority,
            niche_ref=row.question_ref,
            response_signature=row.response_signature,
            predicted_information_yield=float(
                row.predicted_information_yield
            ),
            offline_replay_cost=float(row.offline_replay_cost),
            evidence_refs=(
                *row.input_evidence_sha256s,
                proposal.authority.raw_controller_output_sha256,
                proposal.authority.canonical_controller_output_sha256,
                row.question_payload_sha256,
            ),
            parent_child_sha256s=(
                proposal.authority.parent_child_sha256s
            ),
        )
        for row in proposal.questions
    )
    fission = compile_residual_fission(candidates, axes=axis_rows)
    schedule = compile_sparse_settlement_schedule(
        fission,
        modeled_interactions=proposal.modeled_interactions,
    )
    return EndogenousResidualDiscoveryReceipt(
        proposal=proposal,
        axes=axis_rows,
        fission=fission,
        schedule=schedule,
    )
