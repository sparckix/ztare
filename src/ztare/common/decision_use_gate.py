"""Proposal-conditional gating and verified use of decision interventions.

Recall delivery and decision use are different transitions.  This module binds
one controller proposal to an evidence-backed intervention contract, chooses
whether to inject, challenge, or remain silent, and classifies the resulting
proposal revision without assuming a substrate action vocabulary.

Adapters own feature extraction and the meaning of action/consequence refs.
This kernel owns exact proposal, controller, observation, intervention, and
one-shot consumption identities.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from typing import Any, Iterable, Mapping

from ztare.common.wake_sleep_credit_router import MemoryScope


SCHEMA = "ztare-decision-use-gate-v1"
_GATE_ACTIONS = frozenset({"inject", "challenge", "silence"})
_USE_RELATIONS = frozenset({
    "already_satisfied",
    "accepted_change",
    "rejected",
    "contradicted",
    "unresolved",
})


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


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip()
        for value in values
        if str(value).strip()
    }))


@dataclass(frozen=True)
class ControllerDecisionProposal:
    """One inspectable controller proposal before or after intervention."""

    scope: MemoryScope
    controller_instance_sha256: str
    observation_sha256: str
    proposal_ref: str
    action_ref: str
    predicted_consequence_ref: str
    asserted_features: tuple[str, ...] = field(default_factory=tuple)
    uncertainty_features: tuple[str, ...] = field(default_factory=tuple)
    parent_proposal_sha256: str = ""
    consumed_intervention_revision_sha256: str = ""

    def __post_init__(self) -> None:
        for name in (
            "controller_instance_sha256",
            "observation_sha256",
            "proposal_ref",
            "action_ref",
            "predicted_consequence_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.observation_sha256 != self.scope.context_sha256:
            raise ValueError(
                "proposal observation must equal the consumption context"
            )
        object.__setattr__(
            self,
            "asserted_features",
            _canonical(self.asserted_features),
        )
        object.__setattr__(
            self,
            "uncertainty_features",
            _canonical(self.uncertainty_features),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "controller_decision_proposal",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "observation_sha256": self.observation_sha256,
            "proposal_ref": self.proposal_ref,
            "action_ref": self.action_ref,
            "predicted_consequence_ref": (
                self.predicted_consequence_ref
            ),
            "asserted_features": list(self.asserted_features),
            "uncertainty_features": list(self.uncertainty_features),
            "parent_proposal_sha256": self.parent_proposal_sha256,
            "consumed_intervention_revision_sha256": (
                self.consumed_intervention_revision_sha256
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class DecisionUseContract:
    """Evidence-backed proposal features selected by one intervention."""

    scope: MemoryScope
    intervention_revision_sha256: str
    required_features: tuple[str, ...]
    forbidden_features: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "intervention_revision_sha256",
            _nonempty(
                self.intervention_revision_sha256,
                "intervention_revision_sha256",
            ),
        )
        for name in (
            "required_features",
            "forbidden_features",
            "evidence_refs",
        ):
            object.__setattr__(
                self,
                name,
                _canonical(getattr(self, name)),
            )
        if not self.required_features:
            raise ValueError("required_features must be nonempty")
        if not self.evidence_refs:
            raise ValueError("evidence_refs must be nonempty")
        overlap = (
            set(self.required_features) & set(self.forbidden_features)
        )
        if overlap:
            raise ValueError(
                "required and forbidden features must be disjoint"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_use_contract",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "required_features": list(self.required_features),
            "forbidden_features": list(self.forbidden_features),
            "evidence_refs": list(self.evidence_refs),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class DecisionGateDecision:
    """One gate decision over an exact controller proposal."""

    scope: MemoryScope
    controller_instance_sha256: str
    observation_sha256: str
    pre_proposal_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    gate_action: str
    reason: str
    consumption_receipt_sha256: str = ""

    def __post_init__(self) -> None:
        for name in (
            "controller_instance_sha256",
            "observation_sha256",
            "pre_proposal_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
            "reason",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.gate_action not in _GATE_ACTIONS:
            raise ValueError(f"unknown gate action {self.gate_action!r}")
        if self.observation_sha256 != self.scope.context_sha256:
            raise ValueError(
                "gate observation must equal the consumption context"
            )
        if self.gate_action == "silence":
            if self.consumption_receipt_sha256:
                raise ValueError(
                    "silence cannot carry a consumption receipt"
                )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_gate_decision",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "observation_sha256": self.observation_sha256,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "gate_action": self.gate_action,
            "reason": self.reason,
            "consumption_receipt_sha256": (
                self.consumption_receipt_sha256
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_decision_gate(
    proposal: ControllerDecisionProposal,
    contract: DecisionUseContract,
) -> DecisionGateDecision:
    """Choose silence, injection, or challenge from proposal features."""

    if proposal.scope != contract.scope:
        raise ValueError("proposal and use contract scopes differ")
    asserted = set(proposal.asserted_features)
    required = set(contract.required_features)
    forbidden = set(contract.forbidden_features)
    if asserted & forbidden:
        gate_action = "challenge"
        reason = "proposal_contains_forbidden_feature"
    elif required.issubset(asserted):
        gate_action = "silence"
        reason = "proposal_already_satisfies_contract"
    else:
        gate_action = "inject"
        reason = "proposal_missing_required_feature"
    return DecisionGateDecision(
        scope=proposal.scope,
        controller_instance_sha256=(
            proposal.controller_instance_sha256
        ),
        observation_sha256=proposal.observation_sha256,
        pre_proposal_sha256=proposal.sha256,
        contract_sha256=contract.sha256,
        intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        gate_action=gate_action,
        reason=reason,
    )


def bind_gate_consumption(
    decision: DecisionGateDecision,
    *,
    consumption_receipt_sha256: str,
) -> DecisionGateDecision:
    """Bind an inject/challenge decision to one consumed authorization."""

    if decision.gate_action == "silence":
        raise ValueError("cannot bind recall consumption to silence")
    if decision.consumption_receipt_sha256:
        raise ValueError("gate consumption is already bound")
    return replace(
        decision,
        consumption_receipt_sha256=_nonempty(
            consumption_receipt_sha256,
            "consumption_receipt_sha256",
        ),
    )


@dataclass(frozen=True)
class DecisionUseTransition:
    """Verified relation between proposals around one gate decision."""

    gate_decision_sha256: str
    pre_proposal_sha256: str
    post_proposal_sha256: str
    contract_sha256: str
    intervention_revision_sha256: str
    use_relation: str
    changed_action: bool
    changed_prediction: bool
    added_required_features: tuple[str, ...] = field(default_factory=tuple)
    removed_forbidden_features: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        for name in (
            "gate_decision_sha256",
            "pre_proposal_sha256",
            "contract_sha256",
            "intervention_revision_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.use_relation not in _USE_RELATIONS:
            raise ValueError(
                f"unknown use relation {self.use_relation!r}"
            )
        if (
            self.use_relation != "already_satisfied"
            and not self.post_proposal_sha256
        ):
            raise ValueError(
                "non-silence use relation requires a post proposal"
            )
        object.__setattr__(
            self,
            "added_required_features",
            _canonical(self.added_required_features),
        )
        object.__setattr__(
            self,
            "removed_forbidden_features",
            _canonical(self.removed_forbidden_features),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_use_transition",
            "gate_decision_sha256": self.gate_decision_sha256,
            "pre_proposal_sha256": self.pre_proposal_sha256,
            "post_proposal_sha256": self.post_proposal_sha256,
            "contract_sha256": self.contract_sha256,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
            "use_relation": self.use_relation,
            "changed_action": self.changed_action,
            "changed_prediction": self.changed_prediction,
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


def compile_decision_use_transition(
    *,
    pre_proposal: ControllerDecisionProposal,
    contract: DecisionUseContract,
    gate_decision: DecisionGateDecision,
    post_proposal: ControllerDecisionProposal | None = None,
) -> DecisionUseTransition:
    """Classify the inspectable proposal consequence of one gate decision."""

    if pre_proposal.scope != contract.scope:
        raise ValueError("proposal and use contract scopes differ")
    if gate_decision.scope != pre_proposal.scope:
        raise ValueError("gate and proposal scopes differ")
    if gate_decision.pre_proposal_sha256 != pre_proposal.sha256:
        raise ValueError("gate is bound to a different pre proposal")
    if gate_decision.contract_sha256 != contract.sha256:
        raise ValueError("gate is bound to a different use contract")
    if (
        gate_decision.intervention_revision_sha256
        != contract.intervention_revision_sha256
    ):
        raise ValueError("gate intervention identity drifted")
    if gate_decision.gate_action == "silence":
        if post_proposal is not None:
            raise ValueError("silence does not authorize a revised proposal")
        return DecisionUseTransition(
            gate_decision_sha256=gate_decision.sha256,
            pre_proposal_sha256=pre_proposal.sha256,
            post_proposal_sha256="",
            contract_sha256=contract.sha256,
            intervention_revision_sha256=(
                contract.intervention_revision_sha256
            ),
            use_relation="already_satisfied",
            changed_action=False,
            changed_prediction=False,
        )
    if not gate_decision.consumption_receipt_sha256:
        raise ValueError(
            "inject/challenge gate requires bound recall consumption"
        )
    if post_proposal is None:
        raise ValueError("inject/challenge gate requires a revised proposal")
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
    if (
        post_proposal.consumed_intervention_revision_sha256
        != contract.intervention_revision_sha256
    ):
        raise ValueError("post proposal did not cite the intervention")

    before = set(pre_proposal.asserted_features)
    after = set(post_proposal.asserted_features)
    required = set(contract.required_features)
    forbidden = set(contract.forbidden_features)
    added_required = tuple(sorted((after - before) & required))
    removed_forbidden = tuple(sorted((before - after) & forbidden))
    changed_action = (
        pre_proposal.action_ref != post_proposal.action_ref
    )
    changed_prediction = (
        pre_proposal.predicted_consequence_ref
        != post_proposal.predicted_consequence_ref
    )
    meaningfully_changed = bool(
        changed_action
        or changed_prediction
        or before != after
    )
    if after & forbidden:
        relation = "contradicted"
    elif required.issubset(after) and meaningfully_changed:
        relation = "accepted_change"
    elif not meaningfully_changed:
        relation = "rejected"
    else:
        relation = "unresolved"
    return DecisionUseTransition(
        gate_decision_sha256=gate_decision.sha256,
        pre_proposal_sha256=pre_proposal.sha256,
        post_proposal_sha256=post_proposal.sha256,
        contract_sha256=contract.sha256,
        intervention_revision_sha256=(
            contract.intervention_revision_sha256
        ),
        use_relation=relation,
        changed_action=changed_action,
        changed_prediction=changed_prediction,
        added_required_features=added_required,
        removed_forbidden_features=removed_forbidden,
    )

