"""Causal response learning for interventions on controller proposals.

Memory relevance and memory value are insufficient when a controller may
ignore an offered memory or reach the same policy without it.  This module
treats an intervention as a contextual perturbation of an inspectable
proposal.  It records:

* a blind pre-proposal;
* a randomized ``offer`` or ``withhold`` assignment;
* a same-controller post-proposal;
* contract-relative proposal displacement; and
* an externally settled outcome.

The offer assignment is an instrument.  Supported proposal transport is the
endogenous uptake variable.  The reduced-form outcome effect and first-stage
transport effect remain separate; a complier effect is emitted only when the
instrument is strong enough.  This prevents successful trajectories from
being credited to interventions that were merely present.

Adapters own proposal feature extraction and external utility.  The kernel
owns task/context/controller/choice-set identity, proposal lineage, exact
intervention identity, offer cost, and the response-signature quotient.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.decision_use_gate import (
    ControllerDecisionProposal,
    DecisionUseContract,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-instrumented-proposal-plasticity-v1"
_ASSIGNMENTS = frozenset({"offer", "withhold"})
_RELATIONS = frozenset({
    "offered_supported_transport",
    "offered_contradiction",
    "offered_other_transport",
    "offered_no_uptake",
    "withheld_spontaneous_supported",
    "withheld_spontaneous_contradiction",
    "withheld_spontaneous_other",
    "withheld_stable",
})
_ADMISSION_ACTIONS = frozenset({"offer", "withhold", "explore"})


def _sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _status_counts(values: Iterable[str]) -> dict[str, int]:
    rows = tuple(str(value) for value in values)
    return {
        value: sum(row == value for row in rows)
        for value in sorted(set(rows))
    }


@dataclass(frozen=True)
class InstrumentedProposalTransition:
    """One proposal response under a randomized intervention assignment."""

    scope: MemoryScope
    trial_ref: str
    stratum_sha256: str
    controller_instance_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    assignment: str
    pre_proposal_sha256: str
    post_proposal_sha256: str
    pre_basin_sha256: str
    relation: str
    changed_action: bool
    changed_prediction: bool
    changed_features: bool
    supported_transport: bool
    added_required_features: tuple[str, ...]
    removed_forbidden_features: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "trial_ref",
            "stratum_sha256",
            "controller_instance_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "pre_proposal_sha256",
            "post_proposal_sha256",
            "pre_basin_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.assignment not in _ASSIGNMENTS:
            raise ValueError(f"unknown assignment {self.assignment!r}")
        if self.relation not in _RELATIONS:
            raise ValueError(f"unknown relation {self.relation!r}")
        object.__setattr__(
            self,
            "added_required_features",
            tuple(sorted(set(self.added_required_features))),
        )
        object.__setattr__(
            self,
            "removed_forbidden_features",
            tuple(sorted(set(self.removed_forbidden_features))),
        )

    @property
    def action_relevant_displacement(self) -> bool:
        return bool(
            self.changed_action
            or self.changed_prediction
            or self.changed_features
        )

    @property
    def response_signature_sha256(self) -> str:
        return _sha({
            "scope_sha256": self.scope.sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "pre_basin_sha256": self.pre_basin_sha256,
            "assignment": self.assignment,
            "relation": self.relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
            "changed_features": self.changed_features,
            "supported_transport": self.supported_transport,
            "added_required_features": list(
                self.added_required_features
            ),
            "removed_forbidden_features": list(
                self.removed_forbidden_features
            ),
        })

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "instrumented_proposal_transition",
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
            "assignment": self.assignment,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "post_proposal_sha256": self.post_proposal_sha256,
            "pre_basin_sha256": self.pre_basin_sha256,
            "response_signature_sha256": (
                self.response_signature_sha256
            ),
            "relation": self.relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
            "changed_features": self.changed_features,
            "action_relevant_displacement": (
                self.action_relevant_displacement
            ),
            "supported_transport": self.supported_transport,
            "added_required_features": list(
                self.added_required_features
            ),
            "removed_forbidden_features": list(
                self.removed_forbidden_features
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def proposal_basin_sha256(
    proposal: ControllerDecisionProposal,
    contract: DecisionUseContract,
) -> str:
    """Quotient a raw proposal to its contract-relative decision basin."""

    if proposal.scope != contract.scope:
        raise ValueError("proposal and contract scopes differ")
    required = set(contract.required_features)
    forbidden = set(contract.forbidden_features)
    asserted = set(proposal.asserted_features)
    return _sha({
        "scope_sha256": proposal.scope.sha256,
        "contract_sha256": contract.sha256,
        "action_ref": proposal.action_ref,
        "required_present": sorted(asserted & required),
        "required_missing": sorted(required - asserted),
        "forbidden_present": sorted(asserted & forbidden),
        "uncertainty_features": list(proposal.uncertainty_features),
    })


def compile_instrumented_transition(
    *,
    trial_ref: str,
    stratum_sha256: str,
    assignment: str,
    pre_proposal: ControllerDecisionProposal,
    post_proposal: ControllerDecisionProposal,
    contract: DecisionUseContract,
) -> InstrumentedProposalTransition:
    """Compile a proposal pair into a causal response-signature event."""

    if assignment not in _ASSIGNMENTS:
        raise ValueError(f"unknown assignment {assignment!r}")
    if pre_proposal.scope != contract.scope:
        raise ValueError("pre proposal and contract scopes differ")
    if post_proposal.scope != pre_proposal.scope:
        raise ValueError("post proposal scope drifted")
    if (
        post_proposal.controller_instance_sha256
        != pre_proposal.controller_instance_sha256
    ):
        raise ValueError("post proposal controller instance drifted")
    if (
        post_proposal.observation_sha256
        != pre_proposal.observation_sha256
    ):
        raise ValueError("post proposal observation drifted")
    if post_proposal.parent_proposal_sha256 != pre_proposal.sha256:
        raise ValueError("post proposal has the wrong parent")
    consumed = post_proposal.consumed_intervention_revision_sha256
    if assignment == "offer":
        if consumed != contract.intervention_revision_sha256:
            raise ValueError(
                "offered post proposal did not cite the intervention"
            )
    elif consumed:
        raise ValueError(
            "withheld post proposal cannot cite an intervention"
        )

    before = set(pre_proposal.asserted_features)
    after = set(post_proposal.asserted_features)
    required = set(contract.required_features)
    forbidden = set(contract.forbidden_features)
    before_satisfies = required.issubset(before) and not (
        before & forbidden
    )
    after_satisfies = required.issubset(after) and not (
        after & forbidden
    )
    added_required = tuple(sorted((after - before) & required))
    removed_forbidden = tuple(sorted((before - after) & forbidden))
    changed_action = (
        pre_proposal.action_ref != post_proposal.action_ref
    )
    changed_prediction = (
        pre_proposal.predicted_consequence_ref
        != post_proposal.predicted_consequence_ref
    )
    changed_features = before != after
    meaningful = bool(
        changed_action or changed_prediction or changed_features
    )
    supported = bool(
        meaningful and after_satisfies and not before_satisfies
    )
    if assignment == "offer":
        if supported:
            relation = "offered_supported_transport"
        elif after & forbidden:
            relation = "offered_contradiction"
        elif meaningful:
            relation = "offered_other_transport"
        else:
            relation = "offered_no_uptake"
    else:
        if supported:
            relation = "withheld_spontaneous_supported"
        elif after & forbidden:
            relation = "withheld_spontaneous_contradiction"
        elif meaningful:
            relation = "withheld_spontaneous_other"
        else:
            relation = "withheld_stable"
    return InstrumentedProposalTransition(
        scope=pre_proposal.scope,
        trial_ref=_nonempty(trial_ref, "trial_ref"),
        stratum_sha256=_nonempty(
            stratum_sha256,
            "stratum_sha256",
        ),
        controller_instance_sha256=(
            pre_proposal.controller_instance_sha256
        ),
        contract_sha256=contract.sha256,
        intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        assignment=assignment,
        pre_proposal_sha256=pre_proposal.sha256,
        post_proposal_sha256=post_proposal.sha256,
        pre_basin_sha256=proposal_basin_sha256(
            pre_proposal,
            contract,
        ),
        relation=relation,
        changed_action=changed_action,
        changed_prediction=changed_prediction,
        changed_features=changed_features,
        supported_transport=supported,
        added_required_features=added_required,
        removed_forbidden_features=removed_forbidden,
    )


@dataclass(frozen=True)
class InstrumentedProposalOutcome:
    """External settlement for one proposal-perturbation transition."""

    transition: InstrumentedProposalTransition
    external_outcome_ref: str
    external_value: float
    offer_cost: float
    primitive_action_cost: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "external_outcome_ref",
            _nonempty(
                self.external_outcome_ref,
                "external_outcome_ref",
            ),
        )
        object.__setattr__(
            self,
            "external_value",
            _finite(self.external_value, "external_value"),
        )
        object.__setattr__(
            self,
            "offer_cost",
            _nonnegative(self.offer_cost, "offer_cost"),
        )
        object.__setattr__(
            self,
            "primitive_action_cost",
            _nonnegative(
                self.primitive_action_cost,
                "primitive_action_cost",
            ),
        )
        if (
            self.transition.assignment == "withhold"
            and self.offer_cost != 0.0
        ):
            raise ValueError("withheld transition cannot pay offer cost")

    @property
    def net_external_value(self) -> float:
        return self.external_value - self.offer_cost

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "instrumented_proposal_outcome",
            "transition_sha256": self.transition.sha256,
            "assignment": self.transition.assignment,
            "external_outcome_ref": self.external_outcome_ref,
            "external_value": self.external_value,
            "offer_cost": self.offer_cost,
            "net_external_value": self.net_external_value,
            "primitive_action_cost": self.primitive_action_cost,
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class InstrumentedPlasticityEstimate:
    """Intent-to-treat and uptake-conditioned response estimate."""

    scope_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    status: str
    offer_count: int
    withhold_count: int
    proposal_basin_count: int
    offer_supported_transport_rate: float
    withhold_supported_transport_rate: float
    first_stage_transport_delta: float
    offer_mean_net_value: float
    withhold_mean_net_value: float
    intent_to_treat_net_delta: float
    complier_net_effect: float | None
    relation_status_counts: Mapping[str, int]
    outcome_sha256s: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "instrumented_plasticity_estimate",
            "scope_sha256": self.scope_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "status": self.status,
            "offer_count": self.offer_count,
            "withhold_count": self.withhold_count,
            "proposal_basin_count": self.proposal_basin_count,
            "offer_supported_transport_rate": (
                self.offer_supported_transport_rate
            ),
            "withhold_supported_transport_rate": (
                self.withhold_supported_transport_rate
            ),
            "first_stage_transport_delta": (
                self.first_stage_transport_delta
            ),
            "offer_mean_net_value": self.offer_mean_net_value,
            "withhold_mean_net_value": self.withhold_mean_net_value,
            "intent_to_treat_net_delta": (
                self.intent_to_treat_net_delta
            ),
            "complier_net_effect": self.complier_net_effect,
            "relation_status_counts": dict(
                self.relation_status_counts
            ),
            "outcome_sha256s": list(self.outcome_sha256s),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def estimate_instrumented_plasticity(
    outcomes: Sequence[InstrumentedProposalOutcome],
    *,
    minimum_first_stage: float = 0.10,
) -> InstrumentedPlasticityEstimate:
    """Estimate intervention value without equating offer with uptake."""

    rows = tuple(outcomes)
    if not rows:
        raise ValueError("at least one outcome is required")
    threshold = _nonnegative(
        minimum_first_stage,
        "minimum_first_stage",
    )
    transitions = tuple(row.transition for row in rows)
    scopes = {row.scope.sha256 for row in transitions}
    contracts = {row.contract_sha256 for row in transitions}
    interventions = {
        row.intervention_revision_sha256 for row in transitions
    }
    if len(scopes) != 1:
        raise ValueError("outcomes cross proposal scopes")
    if len(contracts) != 1:
        raise ValueError("outcomes cross decision-use contracts")
    if len(interventions) != 1:
        raise ValueError("outcomes cross intervention revisions")
    offers = tuple(
        row for row in rows
        if row.transition.assignment == "offer"
    )
    withholds = tuple(
        row for row in rows
        if row.transition.assignment == "withhold"
    )
    if not offers or not withholds:
        raise ValueError(
            "both offer and withhold outcomes are required"
        )
    offer_transport = _mean([
        float(row.transition.supported_transport)
        for row in offers
    ])
    withhold_transport = _mean([
        float(row.transition.supported_transport)
        for row in withholds
    ])
    first_stage = offer_transport - withhold_transport
    offer_value = _mean([
        row.net_external_value for row in offers
    ])
    withhold_value = _mean([
        row.net_external_value for row in withholds
    ])
    intent_to_treat = offer_value - withhold_value
    if first_stage >= threshold and first_stage > 0.0:
        status = "identified"
        complier = intent_to_treat / first_stage
    else:
        status = "weak_instrument"
        complier = None
    return InstrumentedPlasticityEstimate(
        scope_sha256=next(iter(scopes)),
        contract_sha256=next(iter(contracts)),
        intervention_revision_sha256=next(iter(interventions)),
        status=status,
        offer_count=len(offers),
        withhold_count=len(withholds),
        proposal_basin_count=len({
            row.pre_basin_sha256 for row in transitions
        }),
        offer_supported_transport_rate=offer_transport,
        withhold_supported_transport_rate=withhold_transport,
        first_stage_transport_delta=first_stage,
        offer_mean_net_value=offer_value,
        withhold_mean_net_value=withhold_value,
        intent_to_treat_net_delta=intent_to_treat,
        complier_net_effect=complier,
        relation_status_counts=_status_counts(
            row.relation for row in transitions
        ),
        outcome_sha256s=tuple(sorted(row.sha256 for row in rows)),
    )


@dataclass(frozen=True)
class CompiledAdmissionDecision:
    """Sparse admission action compiled from an identified response estimate."""

    estimate_sha256: str
    action: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "estimate_sha256",
            _nonempty(self.estimate_sha256, "estimate_sha256"),
        )
        if self.action not in _ADMISSION_ACTIONS:
            raise ValueError(f"unknown admission action {self.action!r}")
        object.__setattr__(
            self,
            "reason",
            _nonempty(self.reason, "reason"),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "compiled_admission_decision",
            "estimate_sha256": self.estimate_sha256,
            "action": self.action,
            "reason": self.reason,
        }
        return {**payload, "sha256": _sha(payload)}


def compile_admission_decision(
    estimate: InstrumentedPlasticityEstimate,
    *,
    minimum_net_gain: float = 0.0,
) -> CompiledAdmissionDecision:
    """Admit only from an identified, cost-adjusted offer effect."""

    margin = _nonnegative(minimum_net_gain, "minimum_net_gain")
    if estimate.status != "identified":
        action = "explore"
        reason = "proposal_transport_instrument_is_weak"
    elif estimate.intent_to_treat_net_delta > margin:
        action = "offer"
        reason = "identified_offer_has_positive_net_effect"
    elif estimate.intent_to_treat_net_delta < -margin:
        action = "withhold"
        reason = "identified_offer_has_negative_net_effect"
    else:
        action = "explore"
        reason = "identified_effect_inside_decision_margin"
    return CompiledAdmissionDecision(
        estimate_sha256=estimate.sha256,
        action=action,
        reason=reason,
    )
