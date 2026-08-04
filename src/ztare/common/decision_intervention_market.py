"""Provider-neutral lowering into outcome-priced, sparse prompt intervention.

Briefing providers, skills, episodic memories, retrieved traces, and other
prompt-visible records all propose the same kind of downstream act: perturb
one controller decision.  Their source vocabularies remain outside this
module.  The common kernel owns only exact rendered identity, acquisition
provenance, consumption scope, prompt budget, predicted decision value, and
the existing matched-outcome credit state.

This module is an adapter over :mod:`wake_sleep_credit_router`; it does not
create another credit system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.wake_sleep_credit_router import (
    CreditObservation,
    MemoryAcquisitionProvenance,
    MemoryCandidate,
    MemoryScope,
    RecallConsumptionDecision,
    RecallConsumptionReceipt,
    RecallExperimentStratum,
    RecallReceipt,
    SettlementReceipt,
    WakeSleepCreditState,
    select_sparse_memories,
    settle_recall_credit,
)


SCHEMA = "ztare-decision-intervention-market-v1"


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


def _nonnegative(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _bounded_delta(value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError(
            "predicted_decision_delta must be finite and in [-1, 1]"
        )
    return number


def _canonical(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip()
        for value in values
        if str(value).strip()
    }))


@dataclass(frozen=True)
class DecisionInterventionProposal:
    """One provider's exact rendered bid for bounded decision authority."""

    intervention_kind: str
    provider_id: str
    provider_revision_sha256: str
    rendered_content_sha256: str
    rendered_token_count: int
    tokenizer_sha256: str
    scope: MemoryScope
    acquisition_provenance: MemoryAcquisitionProvenance
    predicted_decision_delta: float
    prompt_cost_per_token: float
    primitive_action_cost: float
    authority_score: float = 0.0
    actionability_score: float = 0.0
    recency_score: float = 0.0
    guard_features: tuple[str, ...] = field(default_factory=tuple)
    semantic_features: tuple[str, ...] = field(default_factory=tuple)
    support_refs: tuple[str, ...] = field(default_factory=tuple)
    boundary_support_refs: tuple[str, ...] = field(default_factory=tuple)
    content_ref: str = ""

    def __post_init__(self) -> None:
        for name in (
            "intervention_kind",
            "provider_id",
            "provider_revision_sha256",
            "rendered_content_sha256",
            "tokenizer_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if (
            isinstance(self.rendered_token_count, bool)
            or not isinstance(self.rendered_token_count, int)
            or self.rendered_token_count < 0
        ):
            raise ValueError(
                "rendered_token_count must be a nonnegative integer"
            )
        object.__setattr__(
            self,
            "predicted_decision_delta",
            _bounded_delta(self.predicted_decision_delta),
        )
        for name in (
            "prompt_cost_per_token",
            "primitive_action_cost",
            "authority_score",
            "actionability_score",
            "recency_score",
        ):
            object.__setattr__(
                self,
                name,
                _nonnegative(getattr(self, name), name),
            )
        for name in (
            "guard_features",
            "semantic_features",
            "support_refs",
            "boundary_support_refs",
        ):
            object.__setattr__(
                self,
                name,
                _canonical(getattr(self, name)),
            )
        missing = (
            set(self.boundary_support_refs) - set(self.support_refs)
        )
        if missing:
            raise ValueError(
                "boundary_support_refs must be a subset of support_refs"
            )

    @property
    def intervention_revision_sha256(self) -> str:
        """Rendered identity; provider/source changes mint a new revision."""

        return _sha({
            "schema": SCHEMA,
            "intervention_kind": self.intervention_kind,
            "provider_id": self.provider_id,
            "provider_revision_sha256": (
                self.provider_revision_sha256
            ),
            "rendered_content_sha256": self.rendered_content_sha256,
            "tokenizer_sha256": self.tokenizer_sha256,
        })

    @property
    def retrieval_cost(self) -> float:
        return self.rendered_token_count * self.prompt_cost_per_token

    def to_memory_candidate(self) -> MemoryCandidate:
        return MemoryCandidate(
            provider_id=(
                f"{self.intervention_kind}:{self.provider_id}"
            ),
            memory_revision_sha256=(
                self.intervention_revision_sha256
            ),
            scope=self.scope,
            predicted_decision_delta=self.predicted_decision_delta,
            retrieval_cost=self.retrieval_cost,
            primitive_action_cost=self.primitive_action_cost,
            prompt_token_cost=self.rendered_token_count,
            authority_score=self.authority_score,
            actionability_score=self.actionability_score,
            recency_score=self.recency_score,
            guard_features=self.guard_features,
            semantic_features=self.semantic_features,
            support_refs=self.support_refs,
            boundary_support_refs=self.boundary_support_refs,
            content_ref=self.content_ref,
            acquisition_provenance=self.acquisition_provenance,
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_intervention_proposal",
            "intervention_kind": self.intervention_kind,
            "provider_id": self.provider_id,
            "provider_revision_sha256": (
                self.provider_revision_sha256
            ),
            "rendered_content_sha256": self.rendered_content_sha256,
            "rendered_token_count": self.rendered_token_count,
            "tokenizer_sha256": self.tokenizer_sha256,
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "acquisition_provenance": (
                self.acquisition_provenance.to_receipt()
            ),
            "predicted_decision_delta": self.predicted_decision_delta,
            "prompt_cost_per_token": self.prompt_cost_per_token,
            "retrieval_cost": self.retrieval_cost,
            "primitive_action_cost": self.primitive_action_cost,
            "authority_score": self.authority_score,
            "actionability_score": self.actionability_score,
            "recency_score": self.recency_score,
            "guard_features": list(self.guard_features),
            "semantic_features": list(self.semantic_features),
            "support_refs": list(self.support_refs),
            "boundary_support_refs": list(
                self.boundary_support_refs
            ),
            "content_ref": self.content_ref,
            "intervention_revision_sha256": (
                self.intervention_revision_sha256
            ),
        }
        return {**payload, "sha256": _sha(payload)}


def decision_intervention_proposal_from_receipt(
    receipt: Mapping[str, Any],
) -> DecisionInterventionProposal:
    """Rehydrate one proposal while preserving every identity boundary."""

    if receipt.get("schema") != SCHEMA:
        raise ValueError("unknown decision intervention receipt schema")
    if receipt.get("kind") != "decision_intervention_proposal":
        raise ValueError("receipt is not a decision intervention proposal")
    scope_receipt = dict(receipt["scope"])
    provenance_receipt = dict(receipt["acquisition_provenance"])
    proposal = DecisionInterventionProposal(
        intervention_kind=str(receipt["intervention_kind"]),
        provider_id=str(receipt["provider_id"]),
        provider_revision_sha256=str(
            receipt["provider_revision_sha256"]
        ),
        rendered_content_sha256=str(
            receipt["rendered_content_sha256"]
        ),
        rendered_token_count=int(receipt["rendered_token_count"]),
        tokenizer_sha256=str(receipt["tokenizer_sha256"]),
        scope=MemoryScope(
            task_sha256=str(scope_receipt["task_sha256"]),
            controller_sha256=str(
                scope_receipt["controller_sha256"]
            ),
            context_sha256=str(scope_receipt["context_sha256"]),
            choice_set_sha256=str(
                scope_receipt["choice_set_sha256"]
            ),
            action_vocabulary_sha256=str(
                scope_receipt["action_vocabulary_sha256"]
            ),
        ),
        acquisition_provenance=MemoryAcquisitionProvenance(
            episode_sha256=str(
                provenance_receipt["episode_sha256"]
            ),
            observation_sha256=str(
                provenance_receipt["observation_sha256"]
            ),
            controller_instance_sha256=str(
                provenance_receipt["controller_instance_sha256"]
            ),
            support_sha256s=tuple(
                provenance_receipt["support_sha256s"]
            ),
            boundary_support_sha256s=tuple(
                provenance_receipt["boundary_support_sha256s"]
            ),
        ),
        predicted_decision_delta=float(
            receipt["predicted_decision_delta"]
        ),
        prompt_cost_per_token=float(receipt["prompt_cost_per_token"]),
        primitive_action_cost=float(receipt["primitive_action_cost"]),
        authority_score=float(receipt["authority_score"]),
        actionability_score=float(receipt["actionability_score"]),
        recency_score=float(receipt["recency_score"]),
        guard_features=tuple(receipt["guard_features"]),
        semantic_features=tuple(receipt["semantic_features"]),
        support_refs=tuple(receipt["support_refs"]),
        boundary_support_refs=tuple(
            receipt["boundary_support_refs"]
        ),
        content_ref=str(receipt["content_ref"]),
    )
    if proposal.intervention_revision_sha256 != str(
        receipt["intervention_revision_sha256"]
    ):
        raise ValueError("decision intervention revision hash drifted")
    if proposal.to_receipt()["sha256"] != str(receipt["sha256"]):
        raise ValueError("decision intervention receipt hash drifted")
    return proposal


@dataclass(frozen=True)
class DecisionInterventionAllocation:
    """Sparse allocation receipt across heterogeneous provider proposals."""

    scope: MemoryScope
    recall: RecallReceipt
    proposal_revision_sha256s: tuple[str, ...]
    selected_proposal_revision_sha256s: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_intervention_allocation",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "proposal_revision_sha256s": list(
                self.proposal_revision_sha256s
            ),
            "selected_proposal_revision_sha256s": list(
                self.selected_proposal_revision_sha256s
            ),
            "recall": self.recall.to_receipt(),
        }
        return {**payload, "sha256": _sha(payload)}


def allocate_decision_interventions(
    state: WakeSleepCreditState,
    proposals: Sequence[DecisionInterventionProposal],
    *,
    scope: MemoryScope,
    max_items: int,
    max_prompt_tokens: int,
    prior_strength: float = 2.0,
    calibration_penalty_weight: float = 0.25,
    guard_overlap_weight: float = 0.25,
    exploration_weight: float = 0.0,
    minimum_score: float = 0.0,
) -> DecisionInterventionAllocation:
    """Allocate one prompt budget without privileging provider vocabulary."""

    candidates = tuple(
        proposal.to_memory_candidate() for proposal in proposals
    )
    recall = select_sparse_memories(
        state,
        candidates,
        scope=scope,
        max_items=max_items,
        prior_strength=prior_strength,
        calibration_penalty_weight=calibration_penalty_weight,
        guard_overlap_weight=guard_overlap_weight,
        exploration_weight=exploration_weight,
        minimum_score=minimum_score,
        max_prompt_tokens=max_prompt_tokens,
    )
    selected = {
        row.memory_revision_sha256 for row in recall.selections
    }
    return DecisionInterventionAllocation(
        scope=scope,
        recall=recall,
        proposal_revision_sha256s=tuple(sorted(
            proposal.intervention_revision_sha256
            for proposal in proposals
            if proposal.scope == scope
        )),
        selected_proposal_revision_sha256s=tuple(sorted(selected)),
    )


@dataclass(frozen=True)
class DecisionInterventionArmOutcome:
    """Externally measured outcome for one active intervention arm."""

    stratum_sha256: str
    proposal_revision_sha256: str
    arm_id: str
    controller_instance_sha256: str
    runtime_controller_instance_ref: str
    trajectory_sha256: str
    external_outcome_ref: str
    primitive_action_cost: float
    task_score: float
    efficiency_score: float
    information_yield: float
    consumption_receipt_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "stratum_sha256",
            "proposal_revision_sha256",
            "arm_id",
            "controller_instance_sha256",
            "runtime_controller_instance_ref",
            "trajectory_sha256",
            "external_outcome_ref",
            "consumption_receipt_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "primitive_action_cost",
            _nonnegative(
                self.primitive_action_cost,
                "primitive_action_cost",
            ),
        )
        for name in (
            "task_score",
            "efficiency_score",
            "information_yield",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
            object.__setattr__(self, name, value)

    def decision_score(
        self,
        stratum: RecallExperimentStratum,
    ) -> float:
        return (
            stratum.task_score_weight * self.task_score
            + stratum.efficiency_score_weight * self.efficiency_score
        )

    def to_receipt(
        self,
        *,
        stratum: RecallExperimentStratum | None = None,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_intervention_arm_outcome",
            "stratum_sha256": self.stratum_sha256,
            "proposal_revision_sha256": (
                self.proposal_revision_sha256
            ),
            "arm_id": self.arm_id,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "runtime_controller_instance_ref": (
                self.runtime_controller_instance_ref
            ),
            "trajectory_sha256": self.trajectory_sha256,
            "external_outcome_ref": self.external_outcome_ref,
            "primitive_action_cost": self.primitive_action_cost,
            "task_score": self.task_score,
            "efficiency_score": self.efficiency_score,
            "information_yield": self.information_yield,
            "consumption_receipt_sha256": (
                self.consumption_receipt_sha256
            ),
            "decision_score": (
                self.decision_score(stratum)
                if stratum is not None
                else None
            ),
        }
        return {**payload, "sha256": _sha(payload)}


@dataclass(frozen=True)
class PairwiseInterventionTrialReceipt:
    """Atomic duel receipt for two active prompt interventions."""

    status: str
    reason: str
    stratum_sha256: str
    left_arm_sha256: str
    right_arm_sha256: str
    observed_decision_delta: float | None
    observed_task_delta: float | None
    observed_efficiency_delta: float | None
    observed_information_yield_delta: float | None
    left_settlement: SettlementReceipt | None
    right_settlement: SettlementReceipt | None

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "pairwise_intervention_trial",
            "status": self.status,
            "reason": self.reason,
            "stratum_sha256": self.stratum_sha256,
            "left_arm_sha256": self.left_arm_sha256,
            "right_arm_sha256": self.right_arm_sha256,
            "observed_decision_delta": self.observed_decision_delta,
            "observed_task_delta": self.observed_task_delta,
            "observed_efficiency_delta": (
                self.observed_efficiency_delta
            ),
            "observed_information_yield_delta": (
                self.observed_information_yield_delta
            ),
            "left_settlement": (
                self.left_settlement.to_receipt()
                if self.left_settlement is not None
                else None
            ),
            "right_settlement": (
                self.right_settlement.to_receipt()
                if self.right_settlement is not None
                else None
            ),
        }
        return {**payload, "sha256": _sha(payload)}


def settle_pairwise_intervention_trial(
    state: WakeSleepCreditState,
    *,
    stratum: RecallExperimentStratum,
    left_proposal: DecisionInterventionProposal,
    right_proposal: DecisionInterventionProposal,
    left_recall: RecallReceipt,
    right_recall: RecallReceipt,
    left_decision: RecallConsumptionDecision,
    right_decision: RecallConsumptionDecision,
    left_consumption: RecallConsumptionReceipt,
    right_consumption: RecallConsumptionReceipt,
    left_outcome: DecisionInterventionArmOutcome,
    right_outcome: DecisionInterventionArmOutcome,
    contradiction_demote_at: int = 3,
) -> tuple[WakeSleepCreditState, PairwiseInterventionTrialReceipt]:
    """Price two active interventions symmetrically from one matched duel."""

    left_arm_sha = str(
        left_outcome.to_receipt(stratum=stratum)["sha256"]
    )
    right_arm_sha = str(
        right_outcome.to_receipt(stratum=stratum)["sha256"]
    )

    def reject(
        reason: str,
        *,
        left_settlement: SettlementReceipt | None = None,
        right_settlement: SettlementReceipt | None = None,
    ) -> tuple[WakeSleepCreditState, PairwiseInterventionTrialReceipt]:
        return state, PairwiseInterventionTrialReceipt(
            status="rejected",
            reason=reason,
            stratum_sha256=stratum.sha256,
            left_arm_sha256=left_arm_sha,
            right_arm_sha256=right_arm_sha,
            observed_decision_delta=None,
            observed_task_delta=None,
            observed_efficiency_delta=None,
            observed_information_yield_delta=None,
            left_settlement=left_settlement,
            right_settlement=right_settlement,
        )

    left_candidate = left_proposal.to_memory_candidate()
    right_candidate = right_proposal.to_memory_candidate()
    if left_candidate.scope != stratum.scope:
        return reject("left_scope_mismatch")
    if right_candidate.scope != stratum.scope:
        return reject("right_scope_mismatch")
    if (
        left_outcome.stratum_sha256 != stratum.sha256
        or right_outcome.stratum_sha256 != stratum.sha256
    ):
        return reject("stratum_mismatch")
    if (
        left_outcome.proposal_revision_sha256
        != left_proposal.intervention_revision_sha256
        or right_outcome.proposal_revision_sha256
        != right_proposal.intervention_revision_sha256
    ):
        return reject("proposal_revision_mismatch")
    if left_outcome.arm_id == right_outcome.arm_id:
        return reject("arm_identity_reused")
    if (
        left_outcome.controller_instance_sha256
        == right_outcome.controller_instance_sha256
    ):
        return reject("controller_instance_reused")
    if (
        left_outcome.runtime_controller_instance_ref
        == right_outcome.runtime_controller_instance_ref
    ):
        return reject("runtime_controller_instance_reused")
    if left_outcome.trajectory_sha256 == right_outcome.trajectory_sha256:
        return reject("trajectory_identity_reused")
    if (
        left_outcome.primitive_action_cost
        != right_outcome.primitive_action_cost
        or left_outcome.primitive_action_cost
        != stratum.primitive_action_cost
    ):
        return reject("primitive_action_cost_drift")
    for side, proposal, recall, decision, consumption, outcome in (
        (
            "left",
            left_proposal,
            left_recall,
            left_decision,
            left_consumption,
            left_outcome,
        ),
        (
            "right",
            right_proposal,
            right_recall,
            right_decision,
            right_consumption,
            right_outcome,
        ),
    ):
        revision = proposal.intervention_revision_sha256
        if recall.scope != stratum.scope:
            return reject(f"{side}_recall_scope_mismatch")
        if tuple(
            row.memory_revision_sha256 for row in recall.selections
        ) != (revision,):
            return reject(f"{side}_recall_not_single_proposal")
        if (
            decision.recall_sha256 != recall.sha256
            or decision.controller_instance_sha256
            != outcome.controller_instance_sha256
        ):
            return reject(f"{side}_consumption_decision_mismatch")
        if (
            consumption.status != "consumed"
            or consumption.decision_sha256 != decision.sha256
            or consumption.sha256
            != outcome.consumption_receipt_sha256
        ):
            return reject(f"{side}_consumption_receipt_mismatch")

    task_delta = left_outcome.task_score - right_outcome.task_score
    efficiency_delta = (
        left_outcome.efficiency_score
        - right_outcome.efficiency_score
    )
    information_delta = (
        left_outcome.information_yield
        - right_outcome.information_yield
    )
    decision_delta = (
        left_outcome.decision_score(stratum)
        - right_outcome.decision_score(stratum)
    )
    candidates = (left_candidate, right_candidate)
    left_state, left_settlement = settle_recall_credit(
        state,
        candidates,
        recall=left_recall,
        observation=CreditObservation(
            scope=stratum.scope,
            memory_revision_sha256=(
                left_proposal.intervention_revision_sha256
            ),
            observed_decision_delta=decision_delta,
            external_outcome_ref=left_outcome.external_outcome_ref,
            matched_control_ref=right_outcome.external_outcome_ref,
            primitive_action_cost_before=(
                left_outcome.primitive_action_cost
            ),
            primitive_action_cost_after=(
                right_outcome.primitive_action_cost
            ),
            authoritative_contradiction=(
                decision_delta < 0.0 and task_delta < 0.0
            ),
        ),
        contradiction_demote_at=contradiction_demote_at,
    )
    if left_settlement.status != "settled":
        return reject(
            f"left_credit_{left_settlement.reason}",
            left_settlement=left_settlement,
        )
    next_state, right_settlement = settle_recall_credit(
        left_state,
        candidates,
        recall=right_recall,
        observation=CreditObservation(
            scope=stratum.scope,
            memory_revision_sha256=(
                right_proposal.intervention_revision_sha256
            ),
            observed_decision_delta=-decision_delta,
            external_outcome_ref=right_outcome.external_outcome_ref,
            matched_control_ref=left_outcome.external_outcome_ref,
            primitive_action_cost_before=(
                right_outcome.primitive_action_cost
            ),
            primitive_action_cost_after=(
                left_outcome.primitive_action_cost
            ),
            authoritative_contradiction=(
                decision_delta > 0.0 and task_delta > 0.0
            ),
        ),
        contradiction_demote_at=contradiction_demote_at,
    )
    if right_settlement.status != "settled":
        return reject(
            f"right_credit_{right_settlement.reason}",
            left_settlement=left_settlement,
            right_settlement=right_settlement,
        )
    return next_state, PairwiseInterventionTrialReceipt(
        status="settled",
        reason="matched_active_intervention_duel",
        stratum_sha256=stratum.sha256,
        left_arm_sha256=left_arm_sha,
        right_arm_sha256=right_arm_sha,
        observed_decision_delta=decision_delta,
        observed_task_delta=task_delta,
        observed_efficiency_delta=efficiency_delta,
        observed_information_yield_delta=information_delta,
        left_settlement=left_settlement,
        right_settlement=right_settlement,
    )
