"""Outcome-calibrated sparse recall over consolidated memory candidates.

The compiler proposes memories.  This module does not grant those proposals
decision authority.  It admits candidates under an exact consumption scope,
allocates a bounded number of recall slots, and settles value only from a
matched external outcome or ablation.

The router is deliberately substrate-neutral.  A caller owns episode
semantics, guard construction, external outcomes, and the meaning of decision
delta.  This kernel owns:

* separate acquisition, consumption, and experimental-stratum identities;
* exact task/controller/context/choice-set/action-vocabulary compatibility;
* one-shot direct recall injection;
* calibrated decision delta net of retrieval and guard-overlap costs;
* immutable recall and settlement receipts;
* candidate -> active -> probation -> demoted lifecycle;
* boundary-provenance reopening before repeated contradiction demotes a
  memory revision.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "ztare-wake-sleep-credit-router-v1"
IDENTITY_SCHEMA = "ztare-wake-sleep-recall-identities-v1"
_LIFECYCLES = frozenset({"candidate", "active", "probation", "demoted"})
_TRIAL_ASSIGNMENTS = frozenset({"inject", "ablate"})


def _sha(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _bounded_delta(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and in [-1, 1]")
    return number


def _nonnegative(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _unit_interval(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return number


def _nonnegative_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _canonical_strings(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip()
        for value in values
        if str(value).strip()
    }))


@dataclass(frozen=True)
class MemoryScope:
    """Exact compatibility surface for one recall decision.

    ``controller_sha256`` identifies the controller class/configuration, not
    a stochastic runtime instance.  Instance identity belongs to
    :class:`RecallConsumptionDecision` and to each experimental arm.
    """

    task_sha256: str
    controller_sha256: str
    context_sha256: str
    choice_set_sha256: str
    action_vocabulary_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "task_sha256",
            "controller_sha256",
            "context_sha256",
            "choice_set_sha256",
            "action_vocabulary_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )

    def to_receipt(self) -> dict[str, str]:
        return {
            "task_sha256": self.task_sha256,
            "controller_sha256": self.controller_sha256,
            "context_sha256": self.context_sha256,
            "choice_set_sha256": self.choice_set_sha256,
            "action_vocabulary_sha256": self.action_vocabulary_sha256,
        }

    @property
    def sha256(self) -> str:
        return _sha(self.to_receipt())


@dataclass(frozen=True)
class MemoryAcquisitionProvenance:
    """Immutable evidence origin of one compiled memory revision.

    Acquisition provenance is never a recall-generalization key.  A separate
    consumption scope and, when those contexts differ, an explicit transport
    certificate authorize use.
    """

    episode_sha256: str
    observation_sha256: str
    controller_instance_sha256: str
    support_sha256s: tuple[str, ...]
    boundary_support_sha256s: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "episode_sha256",
            "observation_sha256",
            "controller_instance_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "support_sha256s",
            _canonical_strings(self.support_sha256s),
        )
        object.__setattr__(
            self,
            "boundary_support_sha256s",
            _canonical_strings(self.boundary_support_sha256s),
        )
        if not self.support_sha256s:
            raise ValueError("support_sha256s must be nonempty")
        missing = (
            set(self.boundary_support_sha256s)
            - set(self.support_sha256s)
        )
        if missing:
            raise ValueError(
                "boundary_support_sha256s must be a subset of "
                "support_sha256s"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": IDENTITY_SCHEMA,
            "kind": "memory_acquisition_provenance",
            "episode_sha256": self.episode_sha256,
            "observation_sha256": self.observation_sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "support_sha256s": list(self.support_sha256s),
            "boundary_support_sha256s": list(
                self.boundary_support_sha256s
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class MemoryCandidate:
    """One compiler-proposed memory revision competing for recall."""

    provider_id: str
    memory_revision_sha256: str
    scope: MemoryScope
    predicted_decision_delta: float
    retrieval_cost: float
    primitive_action_cost: float
    prompt_token_cost: int = 0
    authority_score: float = 0.0
    actionability_score: float = 0.0
    recency_score: float = 0.0
    guard_features: tuple[str, ...] = field(default_factory=tuple)
    semantic_features: tuple[str, ...] = field(default_factory=tuple)
    support_refs: tuple[str, ...] = field(default_factory=tuple)
    boundary_support_refs: tuple[str, ...] = field(default_factory=tuple)
    content_ref: str = ""
    acquisition_provenance: MemoryAcquisitionProvenance | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_id",
            _nonempty(self.provider_id, "provider_id"),
        )
        object.__setattr__(
            self,
            "memory_revision_sha256",
            _nonempty(
                self.memory_revision_sha256,
                "memory_revision_sha256",
            ),
        )
        object.__setattr__(
            self,
            "predicted_decision_delta",
            _bounded_delta(
                self.predicted_decision_delta,
                "predicted_decision_delta",
            ),
        )
        for name in (
            "retrieval_cost",
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
        object.__setattr__(
            self,
            "prompt_token_cost",
            _nonnegative_int(
                self.prompt_token_cost,
                "prompt_token_cost",
            ),
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
                _canonical_strings(getattr(self, name)),
            )
        missing = set(self.boundary_support_refs) - set(self.support_refs)
        if missing:
            raise ValueError(
                "boundary_support_refs must be a subset of support_refs"
            )

    @property
    def key(self) -> str:
        return f"{self.scope.sha256}:{self.memory_revision_sha256}"

    def to_receipt(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "memory_revision_sha256": self.memory_revision_sha256,
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "predicted_decision_delta": self.predicted_decision_delta,
            "retrieval_cost": self.retrieval_cost,
            "primitive_action_cost": self.primitive_action_cost,
            "prompt_token_cost": self.prompt_token_cost,
            "authority_score": self.authority_score,
            "actionability_score": self.actionability_score,
            "recency_score": self.recency_score,
            "guard_features": list(self.guard_features),
            "semantic_features": list(self.semantic_features),
            "support_refs": list(self.support_refs),
            "boundary_support_refs": list(self.boundary_support_refs),
            "content_ref": self.content_ref,
            "acquisition_provenance": (
                self.acquisition_provenance.to_receipt()
                if self.acquisition_provenance is not None
                else None
            ),
        }


@dataclass(frozen=True)
class MemoryCredit:
    """Outcome evidence for one memory revision under one exact scope."""

    memory_key: str
    settlement_count: int = 0
    sum_observed_delta: float = 0.0
    sum_squared_prediction_error: float = 0.0
    compatible_contradictions: int = 0
    lifecycle: str = "candidate"
    reopened_support_refs: tuple[str, ...] = field(default_factory=tuple)
    last_external_outcome_ref: str = ""

    def __post_init__(self) -> None:
        _nonempty(self.memory_key, "memory_key")
        if self.settlement_count < 0:
            raise ValueError("settlement_count must be nonnegative")
        if self.compatible_contradictions < 0:
            raise ValueError(
                "compatible_contradictions must be nonnegative"
            )
        if self.lifecycle not in _LIFECYCLES:
            raise ValueError(f"unknown memory lifecycle {self.lifecycle!r}")
        object.__setattr__(
            self,
            "reopened_support_refs",
            _canonical_strings(self.reopened_support_refs),
        )

    @property
    def mean_observed_delta(self) -> float | None:
        if self.settlement_count == 0:
            return None
        return self.sum_observed_delta / self.settlement_count

    @property
    def mean_squared_prediction_error(self) -> float | None:
        if self.settlement_count == 0:
            return None
        return self.sum_squared_prediction_error / self.settlement_count

    def calibrated_delta(
        self,
        candidate: MemoryCandidate,
        *,
        prior_strength: float,
    ) -> float:
        strength = _nonnegative(prior_strength, "prior_strength")
        denominator = strength + self.settlement_count
        if denominator == 0:
            return candidate.predicted_decision_delta
        numerator = (
            strength * candidate.predicted_decision_delta
            + self.sum_observed_delta
        )
        return numerator / denominator

    def to_receipt(self) -> dict[str, Any]:
        return {
            "memory_key": self.memory_key,
            "settlement_count": self.settlement_count,
            "sum_observed_delta": self.sum_observed_delta,
            "mean_observed_delta": self.mean_observed_delta,
            "sum_squared_prediction_error": (
                self.sum_squared_prediction_error
            ),
            "mean_squared_prediction_error": (
                self.mean_squared_prediction_error
            ),
            "compatible_contradictions": self.compatible_contradictions,
            "lifecycle": self.lifecycle,
            "reopened_support_refs": list(self.reopened_support_refs),
            "last_external_outcome_ref": self.last_external_outcome_ref,
        }


@dataclass(frozen=True)
class WakeSleepCreditState:
    credits: tuple[MemoryCredit, ...] = field(default_factory=tuple)

    def credit_for(self, candidate: MemoryCandidate) -> MemoryCredit:
        for credit in self.credits:
            if credit.memory_key == candidate.key:
                return credit
        return MemoryCredit(memory_key=candidate.key)

    def with_credit(self, updated: MemoryCredit) -> "WakeSleepCreditState":
        rows = [
            credit
            for credit in self.credits
            if credit.memory_key != updated.memory_key
        ]
        rows.append(updated)
        rows.sort(key=lambda row: row.memory_key)
        return WakeSleepCreditState(credits=tuple(rows))

    def to_receipt(self) -> dict[str, Any]:
        rows = [credit.to_receipt() for credit in self.credits]
        payload = {
            "schema": SCHEMA,
            "credits": rows,
        }
        return {
            **payload,
            "sha256": _sha(payload),
        }


def wake_sleep_credit_state_from_receipt(
    receipt: Mapping[str, Any],
) -> WakeSleepCreditState:
    """Rehydrate one hash-bound credit state without weakening its identity."""

    source = dict(receipt)
    claimed_sha256 = _nonempty(
        str(source.pop("sha256", "")),
        "credit_state_sha256",
    )
    if _sha(source) != claimed_sha256:
        raise ValueError("credit-state receipt hash mismatch")
    if source.get("schema") != SCHEMA:
        raise ValueError("unsupported credit-state receipt schema")
    raw_credits = source.get("credits")
    if not isinstance(raw_credits, list):
        raise ValueError("credit-state credits must be a list")
    credits: list[MemoryCredit] = []
    for raw in raw_credits:
        if not isinstance(raw, Mapping):
            raise ValueError("credit-state row must be an object")
        row = MemoryCredit(
            memory_key=str(raw.get("memory_key") or ""),
            settlement_count=int(raw.get("settlement_count", 0)),
            sum_observed_delta=float(
                raw.get("sum_observed_delta", 0.0)
            ),
            sum_squared_prediction_error=float(
                raw.get("sum_squared_prediction_error", 0.0)
            ),
            compatible_contradictions=int(
                raw.get("compatible_contradictions", 0)
            ),
            lifecycle=str(raw.get("lifecycle") or ""),
            reopened_support_refs=tuple(
                raw.get("reopened_support_refs") or ()
            ),
            last_external_outcome_ref=str(
                raw.get("last_external_outcome_ref") or ""
            ),
        )
        if row.to_receipt() != dict(raw):
            raise ValueError(
                "credit-state row contains inconsistent derived fields"
            )
        credits.append(row)
    state = WakeSleepCreditState(credits=tuple(credits))
    if state.to_receipt()["sha256"] != claimed_sha256:
        raise ValueError("credit-state canonicalization drifted")
    return state


@dataclass(frozen=True)
class RecallSelection:
    provider_id: str
    memory_revision_sha256: str
    memory_key: str
    lifecycle: str
    predicted_decision_delta: float
    calibrated_decision_delta: float
    calibration_penalty: float
    retrieval_cost: float
    guard_overlap: float
    guard_overlap_cost: float
    score: float
    primitive_action_cost: float
    prompt_token_cost: int

    def to_receipt(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "memory_revision_sha256": self.memory_revision_sha256,
            "memory_key": self.memory_key,
            "lifecycle": self.lifecycle,
            "predicted_decision_delta": self.predicted_decision_delta,
            "calibrated_decision_delta": (
                self.calibrated_decision_delta
            ),
            "calibration_penalty": self.calibration_penalty,
            "retrieval_cost": self.retrieval_cost,
            "guard_overlap": self.guard_overlap,
            "guard_overlap_cost": self.guard_overlap_cost,
            "score": self.score,
            "primitive_action_cost": self.primitive_action_cost,
            "prompt_token_cost": self.prompt_token_cost,
        }


@dataclass(frozen=True)
class RecallReceipt:
    scope: MemoryScope
    max_items: int
    candidate_memory_keys: tuple[str, ...]
    selections: tuple[RecallSelection, ...]
    prior_strength: float
    calibration_penalty_weight: float
    guard_overlap_weight: float
    exploration_weight: float
    max_prompt_tokens: int | None = None

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "recall",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "max_items": self.max_items,
            "candidate_memory_keys": list(self.candidate_memory_keys),
            "selections": [
                selection.to_receipt()
                for selection in self.selections
            ],
            "prior_strength": self.prior_strength,
            "calibration_penalty_weight": (
                self.calibration_penalty_weight
            ),
            "guard_overlap_weight": self.guard_overlap_weight,
            "exploration_weight": self.exploration_weight,
            "max_prompt_tokens": self.max_prompt_tokens,
            "selected_prompt_tokens": sum(
                selection.prompt_token_cost
                for selection in self.selections
            ),
        }
        return {
            **payload,
            "sha256": _sha(payload),
        }

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class RecallConsumptionDecision:
    """One exact, one-shot authorization to inject selected memories.

    The runtime controller instance is deliberately distinct from the
    controller class in ``scope``.  ``remaining_direct_injections`` is part of
    the identity transition, so a digest cannot silently persist as the
    observation changes.
    """

    scope: MemoryScope
    recall_sha256: str
    controller_instance_sha256: str
    observation_sha256: str
    decision_ref: str
    selected_memory_keys: tuple[str, ...]
    acquisition_provenance_sha256s: tuple[str, ...]
    compatibility_transport_sha256: str
    remaining_direct_injections: int = 1

    def __post_init__(self) -> None:
        for name in (
            "recall_sha256",
            "controller_instance_sha256",
            "observation_sha256",
            "decision_ref",
            "compatibility_transport_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if (
            len(self.selected_memory_keys)
            != len(self.acquisition_provenance_sha256s)
        ):
            raise ValueError(
                "every selected memory needs one acquisition provenance"
            )
        pairs = tuple(sorted({
            (
                _nonempty(memory_key, "selected_memory_key"),
                _nonempty(provenance, "acquisition_provenance_sha256"),
            )
            for memory_key, provenance in zip(
                self.selected_memory_keys,
                self.acquisition_provenance_sha256s,
            )
        }))
        object.__setattr__(
            self,
            "selected_memory_keys",
            tuple(memory_key for memory_key, _ in pairs),
        )
        object.__setattr__(
            self,
            "acquisition_provenance_sha256s",
            tuple(provenance for _, provenance in pairs),
        )
        if not pairs:
            raise ValueError("selected_memory_keys must be nonempty")
        if self.observation_sha256 != self.scope.context_sha256:
            raise ValueError(
                "observation_sha256 must equal the exact consumption context"
            )
        if self.remaining_direct_injections not in (0, 1):
            raise ValueError(
                "remaining_direct_injections must be zero or one"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": IDENTITY_SCHEMA,
            "kind": "recall_consumption_decision",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "recall_sha256": self.recall_sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "observation_sha256": self.observation_sha256,
            "decision_ref": self.decision_ref,
            "selected_memory_keys": list(self.selected_memory_keys),
            "acquisition_provenance_sha256s": list(
                self.acquisition_provenance_sha256s
            ),
            "compatibility_transport_sha256": (
                self.compatibility_transport_sha256
            ),
            "remaining_direct_injections": (
                self.remaining_direct_injections
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class RecallConsumptionReceipt:
    status: str
    reason: str
    decision_sha256: str
    next_decision_sha256: str
    scope_sha256: str
    controller_instance_sha256: str
    observation_sha256: str
    selected_memory_keys: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": IDENTITY_SCHEMA,
            "kind": "recall_consumption",
            "status": self.status,
            "reason": self.reason,
            "decision_sha256": self.decision_sha256,
            "next_decision_sha256": self.next_decision_sha256,
            "scope_sha256": self.scope_sha256,
            "controller_instance_sha256": (
                self.controller_instance_sha256
            ),
            "observation_sha256": self.observation_sha256,
            "selected_memory_keys": list(self.selected_memory_keys),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def authorize_recall_consumption(
    recall: RecallReceipt,
    candidates: Sequence[MemoryCandidate],
    *,
    controller_instance_sha256: str,
    observation_sha256: str,
    decision_ref: str,
    compatibility_transport_sha256: str,
) -> RecallConsumptionDecision:
    """Bind a sparse recall result to one controller instance and decision."""

    selected_candidates: list[MemoryCandidate] = []
    for selection in recall.selections:
        candidate = next(
            (
                row
                for row in candidates
                if row.key == selection.memory_key
            ),
            None,
        )
        if candidate is None:
            raise ValueError(
                "recall selection has no matching memory candidate"
            )
        if candidate.acquisition_provenance is None:
            raise ValueError(
                "recall consumption requires acquisition provenance"
            )
        selected_candidates.append(candidate)
    if not selected_candidates:
        raise ValueError("cannot authorize an empty recall")
    return RecallConsumptionDecision(
        scope=recall.scope,
        recall_sha256=recall.sha256,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=observation_sha256,
        decision_ref=decision_ref,
        selected_memory_keys=tuple(
            row.key for row in selected_candidates
        ),
        acquisition_provenance_sha256s=tuple(
            row.acquisition_provenance.sha256
            for row in selected_candidates
            if row.acquisition_provenance is not None
        ),
        compatibility_transport_sha256=(
            compatibility_transport_sha256
        ),
    )


def consume_recall_once(
    decision: RecallConsumptionDecision,
    *,
    controller_instance_sha256: str,
    observation_sha256: str,
) -> tuple[RecallConsumptionDecision, RecallConsumptionReceipt]:
    """Consume one direct-injection authorization, rejecting any replay."""

    prior_sha = decision.sha256

    def reject(reason: str) -> tuple[
        RecallConsumptionDecision,
        RecallConsumptionReceipt,
    ]:
        return decision, RecallConsumptionReceipt(
            status="rejected",
            reason=reason,
            decision_sha256=prior_sha,
            next_decision_sha256=prior_sha,
            scope_sha256=decision.scope.sha256,
            controller_instance_sha256=controller_instance_sha256,
            observation_sha256=observation_sha256,
            selected_memory_keys=decision.selected_memory_keys,
        )

    if controller_instance_sha256 != decision.controller_instance_sha256:
        return reject("controller_instance_mismatch")
    if observation_sha256 != decision.observation_sha256:
        return reject("observation_mismatch")
    if decision.remaining_direct_injections == 0:
        return reject("direct_injection_already_consumed")
    next_decision = replace(
        decision,
        remaining_direct_injections=0,
    )
    return next_decision, RecallConsumptionReceipt(
        status="consumed",
        reason="one_shot_direct_injection",
        decision_sha256=prior_sha,
        next_decision_sha256=next_decision.sha256,
        scope_sha256=decision.scope.sha256,
        controller_instance_sha256=controller_instance_sha256,
        observation_sha256=observation_sha256,
        selected_memory_keys=decision.selected_memory_keys,
    )


@dataclass(frozen=True)
class RecallExperimentStratum:
    """The equivalence claim under which distinct trial arms are compared."""

    scope: MemoryScope
    restored_prefix_sha256: str
    restored_observation_sha256: str
    action_budget: int
    primitive_action_cost: float
    randomization_seed_sha256: str
    task_score_weight: float = 0.8
    efficiency_score_weight: float = 0.2

    def __post_init__(self) -> None:
        for name in (
            "restored_prefix_sha256",
            "restored_observation_sha256",
            "randomization_seed_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.action_budget <= 0:
            raise ValueError("action_budget must be positive")
        object.__setattr__(
            self,
            "primitive_action_cost",
            _nonnegative(
                self.primitive_action_cost,
                "primitive_action_cost",
            ),
        )
        task_weight = _unit_interval(
            self.task_score_weight,
            "task_score_weight",
        )
        efficiency_weight = _unit_interval(
            self.efficiency_score_weight,
            "efficiency_score_weight",
        )
        if not math.isclose(
            task_weight + efficiency_weight,
            1.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "task and efficiency score weights must sum to one"
            )
        object.__setattr__(
            self,
            "task_score_weight",
            task_weight,
        )
        object.__setattr__(
            self,
            "efficiency_score_weight",
            efficiency_weight,
        )
        if self.restored_observation_sha256 != self.scope.context_sha256:
            raise ValueError(
                "restored observation must equal the consumption context"
            )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": IDENTITY_SCHEMA,
            "kind": "recall_experiment_stratum",
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "restored_prefix_sha256": self.restored_prefix_sha256,
            "restored_observation_sha256": (
                self.restored_observation_sha256
            ),
            "action_budget": self.action_budget,
            "primitive_action_cost": self.primitive_action_cost,
            "randomization_seed_sha256": (
                self.randomization_seed_sha256
            ),
            "task_score_weight": self.task_score_weight,
            "efficiency_score_weight": (
                self.efficiency_score_weight
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class RecallTrialArmOutcome:
    """Externally measured outcome of one distinct stochastic controller."""

    stratum_sha256: str
    arm_id: str
    assignment: str
    controller_instance_sha256: str
    runtime_controller_instance_ref: str
    trajectory_sha256: str
    external_outcome_ref: str
    primitive_action_cost: float
    task_score: float
    efficiency_score: float
    information_yield: float
    recall_consumption_sha256: str = ""

    def __post_init__(self) -> None:
        for name in (
            "stratum_sha256",
            "arm_id",
            "controller_instance_sha256",
            "runtime_controller_instance_ref",
            "trajectory_sha256",
            "external_outcome_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if self.assignment not in _TRIAL_ASSIGNMENTS:
            raise ValueError(
                f"unknown recall trial assignment {self.assignment!r}"
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
            object.__setattr__(
                self,
                name,
                _unit_interval(getattr(self, name), name),
            )
        consumption = str(self.recall_consumption_sha256 or "").strip()
        if self.assignment == "inject" and not consumption:
            raise ValueError(
                "inject arm requires a recall consumption receipt"
            )
        if self.assignment == "ablate" and consumption:
            raise ValueError(
                "ablate arm cannot carry a recall consumption receipt"
            )
        object.__setattr__(
            self,
            "recall_consumption_sha256",
            consumption,
        )

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
            "schema": IDENTITY_SCHEMA,
            "kind": "recall_trial_arm_outcome",
            "stratum_sha256": self.stratum_sha256,
            "arm_id": self.arm_id,
            "assignment": self.assignment,
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
            "recall_consumption_sha256": (
                self.recall_consumption_sha256
            ),
            "decision_score": (
                self.decision_score(stratum)
                if stratum is not None
                else None
            ),
        }
        return {**payload, "sha256": _sha(payload)}


@dataclass(frozen=True)
class MatchedRecallTrialReceipt:
    status: str
    reason: str
    stratum_sha256: str
    recall_sha256: str
    consumption_decision_sha256: str
    inject_arm_sha256: str
    ablate_arm_sha256: str
    observed_decision_delta: float | None
    observed_task_delta: float | None
    observed_efficiency_delta: float | None
    observed_information_yield_delta: float | None
    settlement: SettlementReceipt | None

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": IDENTITY_SCHEMA,
            "kind": "matched_recall_trial",
            "status": self.status,
            "reason": self.reason,
            "stratum_sha256": self.stratum_sha256,
            "recall_sha256": self.recall_sha256,
            "consumption_decision_sha256": (
                self.consumption_decision_sha256
            ),
            "inject_arm_sha256": self.inject_arm_sha256,
            "ablate_arm_sha256": self.ablate_arm_sha256,
            "observed_decision_delta": self.observed_decision_delta,
            "observed_task_delta": self.observed_task_delta,
            "observed_efficiency_delta": (
                self.observed_efficiency_delta
            ),
            "observed_information_yield_delta": (
                self.observed_information_yield_delta
            ),
            "settlement": (
                self.settlement.to_receipt()
                if self.settlement is not None
                else None
            ),
        }
        return {**payload, "sha256": _sha(payload)}


@dataclass(frozen=True)
class CreditObservation:
    scope: MemoryScope
    memory_revision_sha256: str
    observed_decision_delta: float
    external_outcome_ref: str
    matched_control_ref: str
    primitive_action_cost_before: float
    primitive_action_cost_after: float
    guard_compatible: bool = True
    authoritative_contradiction: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "memory_revision_sha256",
            _nonempty(
                self.memory_revision_sha256,
                "memory_revision_sha256",
            ),
        )
        object.__setattr__(
            self,
            "observed_decision_delta",
            _bounded_delta(
                self.observed_decision_delta,
                "observed_decision_delta",
            ),
        )
        object.__setattr__(
            self,
            "external_outcome_ref",
            _nonempty(self.external_outcome_ref, "external_outcome_ref"),
        )
        object.__setattr__(
            self,
            "matched_control_ref",
            _nonempty(self.matched_control_ref, "matched_control_ref"),
        )
        object.__setattr__(
            self,
            "primitive_action_cost_before",
            _nonnegative(
                self.primitive_action_cost_before,
                "primitive_action_cost_before",
            ),
        )
        object.__setattr__(
            self,
            "primitive_action_cost_after",
            _nonnegative(
                self.primitive_action_cost_after,
                "primitive_action_cost_after",
            ),
        )


@dataclass(frozen=True)
class SettlementReceipt:
    status: str
    reason: str
    recall_sha256: str
    memory_key: str
    scope_sha256: str
    prior_state_sha256: str
    next_state_sha256: str
    observed_decision_delta: float | None
    external_outcome_ref: str
    matched_control_ref: str
    lifecycle_before: str | None
    lifecycle_after: str | None
    reopened_support_refs: tuple[str, ...]
    primitive_action_cost_before: float | None
    primitive_action_cost_after: float | None

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "settlement",
            "status": self.status,
            "reason": self.reason,
            "recall_sha256": self.recall_sha256,
            "memory_key": self.memory_key,
            "scope_sha256": self.scope_sha256,
            "prior_state_sha256": self.prior_state_sha256,
            "next_state_sha256": self.next_state_sha256,
            "observed_decision_delta": self.observed_decision_delta,
            "external_outcome_ref": self.external_outcome_ref,
            "matched_control_ref": self.matched_control_ref,
            "lifecycle_before": self.lifecycle_before,
            "lifecycle_after": self.lifecycle_after,
            "reopened_support_refs": list(self.reopened_support_refs),
            "primitive_action_cost_before": (
                self.primitive_action_cost_before
            ),
            "primitive_action_cost_after": (
                self.primitive_action_cost_after
            ),
        }
        return {
            **payload,
            "sha256": _sha(payload),
        }


def feature_overlap(
    left: Sequence[str],
    right: Sequence[str],
) -> float:
    """Jaccard overlap, with two empty feature sets treated as disjoint."""

    a = set(left)
    b = set(right)
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def select_static_authority_baseline(
    candidates: Sequence[MemoryCandidate],
    *,
    scope: MemoryScope,
    max_items: int,
) -> tuple[MemoryCandidate, ...]:
    """Approximate the current authority/actionability/recency agenda."""

    if max_items < 0:
        raise ValueError("max_items must be nonnegative")
    eligible = [
        candidate
        for candidate in candidates
        if candidate.scope == scope
    ]
    eligible.sort(
        key=lambda candidate: (
            candidate.authority_score,
            candidate.actionability_score,
            candidate.recency_score,
            candidate.memory_revision_sha256,
        ),
        reverse=True,
    )
    return tuple(eligible[:max_items])


def select_sparse_memories(
    state: WakeSleepCreditState,
    candidates: Sequence[MemoryCandidate],
    *,
    scope: MemoryScope,
    max_items: int,
    prior_strength: float = 2.0,
    calibration_penalty_weight: float = 0.25,
    guard_overlap_weight: float = 0.25,
    exploration_weight: float = 0.0,
    minimum_score: float = 0.0,
    max_prompt_tokens: int | None = None,
) -> RecallReceipt:
    """Greedily allocate recall slots by calibrated net decision value."""

    if max_items < 0:
        raise ValueError("max_items must be nonnegative")
    if max_prompt_tokens is not None:
        max_prompt_tokens = _nonnegative_int(
            max_prompt_tokens,
            "max_prompt_tokens",
        )
    prior_strength = _nonnegative(prior_strength, "prior_strength")
    calibration_penalty_weight = _nonnegative(
        calibration_penalty_weight,
        "calibration_penalty_weight",
    )
    guard_overlap_weight = _nonnegative(
        guard_overlap_weight,
        "guard_overlap_weight",
    )
    exploration_weight = _nonnegative(
        exploration_weight,
        "exploration_weight",
    )
    pool = []
    for candidate in candidates:
        if candidate.scope != scope:
            continue
        credit = state.credit_for(candidate)
        if credit.lifecycle == "demoted":
            continue
        calibrated = credit.calibrated_delta(
            candidate,
            prior_strength=prior_strength,
        )
        mse = credit.mean_squared_prediction_error or 0.0
        calibration_penalty = calibration_penalty_weight * mse
        exploration = (
            exploration_weight
            / math.sqrt(1.0 + credit.settlement_count)
        )
        pool.append({
            "candidate": candidate,
            "credit": credit,
            "calibrated": calibrated,
            "calibration_penalty": calibration_penalty,
            "exploration": exploration,
        })

    selected_rows: list[RecallSelection] = []
    selected_candidates: list[MemoryCandidate] = []
    while pool and len(selected_rows) < max_items:
        scored = []
        for row in pool:
            candidate = row["candidate"]
            selected_prompt_tokens = sum(
                chosen.prompt_token_cost
                for chosen in selected_candidates
            )
            if (
                max_prompt_tokens is not None
                and selected_prompt_tokens + candidate.prompt_token_cost
                > max_prompt_tokens
            ):
                continue
            overlap = max(
                (
                    feature_overlap(
                        candidate.guard_features,
                        chosen.guard_features,
                    )
                    for chosen in selected_candidates
                ),
                default=0.0,
            )
            overlap_cost = guard_overlap_weight * overlap
            score = (
                row["calibrated"]
                - row["calibration_penalty"]
                - candidate.retrieval_cost
                - overlap_cost
                + row["exploration"]
            )
            scored.append((score, candidate.memory_revision_sha256, row, overlap, overlap_cost))
        if not scored:
            break
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        score, _, winner, overlap, overlap_cost = scored[0]
        if score <= minimum_score:
            break
        candidate = winner["candidate"]
        credit = winner["credit"]
        selected_rows.append(RecallSelection(
            provider_id=candidate.provider_id,
            memory_revision_sha256=candidate.memory_revision_sha256,
            memory_key=candidate.key,
            lifecycle=credit.lifecycle,
            predicted_decision_delta=candidate.predicted_decision_delta,
            calibrated_decision_delta=winner["calibrated"],
            calibration_penalty=winner["calibration_penalty"],
            retrieval_cost=candidate.retrieval_cost,
            guard_overlap=overlap,
            guard_overlap_cost=overlap_cost,
            score=score,
            primitive_action_cost=candidate.primitive_action_cost,
            prompt_token_cost=candidate.prompt_token_cost,
        ))
        selected_candidates.append(candidate)
        pool = [
            row
            for row in pool
            if row["candidate"].key != candidate.key
        ]

    return RecallReceipt(
        scope=scope,
        max_items=max_items,
        candidate_memory_keys=tuple(sorted(
            candidate.key
            for candidate in candidates
            if candidate.scope == scope
        )),
        selections=tuple(selected_rows),
        prior_strength=prior_strength,
        calibration_penalty_weight=calibration_penalty_weight,
        guard_overlap_weight=guard_overlap_weight,
        exploration_weight=exploration_weight,
        max_prompt_tokens=max_prompt_tokens,
    )


def settle_recall_credit(
    state: WakeSleepCreditState,
    candidates: Sequence[MemoryCandidate],
    *,
    recall: RecallReceipt,
    observation: CreditObservation,
    contradiction_demote_at: int = 3,
) -> tuple[WakeSleepCreditState, SettlementReceipt]:
    """Settle one selected memory against a matched external outcome."""

    if contradiction_demote_at < 2:
        raise ValueError("contradiction_demote_at must be at least 2")
    prior_sha = state.to_receipt()["sha256"]
    selected = next(
        (
            row
            for row in recall.selections
            if row.memory_revision_sha256
            == observation.memory_revision_sha256
        ),
        None,
    )
    candidate = next(
        (
            item
            for item in candidates
            if item.memory_revision_sha256
            == observation.memory_revision_sha256
            and item.scope == recall.scope
        ),
        None,
    )

    def reject(reason: str) -> tuple[WakeSleepCreditState, SettlementReceipt]:
        return state, SettlementReceipt(
            status="rejected",
            reason=reason,
            recall_sha256=recall.sha256,
            memory_key=selected.memory_key if selected else "",
            scope_sha256=observation.scope.sha256,
            prior_state_sha256=prior_sha,
            next_state_sha256=prior_sha,
            observed_decision_delta=None,
            external_outcome_ref=observation.external_outcome_ref,
            matched_control_ref=observation.matched_control_ref,
            lifecycle_before=selected.lifecycle if selected else None,
            lifecycle_after=selected.lifecycle if selected else None,
            reopened_support_refs=(),
            primitive_action_cost_before=(
                observation.primitive_action_cost_before
            ),
            primitive_action_cost_after=(
                observation.primitive_action_cost_after
            ),
        )

    if observation.scope != recall.scope:
        return reject("scope_mismatch")
    if not observation.guard_compatible:
        return reject("guard_mismatch")
    if selected is None or candidate is None:
        return reject("memory_not_selected")
    if (
        observation.primitive_action_cost_before
        != observation.primitive_action_cost_after
        or observation.primitive_action_cost_before
        != selected.primitive_action_cost
    ):
        return reject("primitive_action_cost_drift")

    credit = state.credit_for(candidate)
    error = (
        selected.predicted_decision_delta
        - observation.observed_decision_delta
    )
    contradictions = credit.compatible_contradictions
    lifecycle = credit.lifecycle
    reopened = credit.reopened_support_refs
    if observation.authoritative_contradiction:
        contradictions += 1
        if contradictions >= contradiction_demote_at:
            lifecycle = "demoted"
            reopened = ()
        else:
            lifecycle = "probation"
            reopened = candidate.boundary_support_refs
    elif observation.observed_decision_delta > 0:
        lifecycle = "active"
        contradictions = 0
        reopened = ()
    elif lifecycle == "candidate":
        lifecycle = "active"

    updated = replace(
        credit,
        settlement_count=credit.settlement_count + 1,
        sum_observed_delta=(
            credit.sum_observed_delta
            + observation.observed_decision_delta
        ),
        sum_squared_prediction_error=(
            credit.sum_squared_prediction_error + error * error
        ),
        compatible_contradictions=contradictions,
        lifecycle=lifecycle,
        reopened_support_refs=reopened,
        last_external_outcome_ref=observation.external_outcome_ref,
    )
    next_state = state.with_credit(updated)
    next_sha = next_state.to_receipt()["sha256"]
    receipt = SettlementReceipt(
        status="settled",
        reason="compatible_matched_outcome",
        recall_sha256=recall.sha256,
        memory_key=candidate.key,
        scope_sha256=observation.scope.sha256,
        prior_state_sha256=prior_sha,
        next_state_sha256=next_sha,
        observed_decision_delta=observation.observed_decision_delta,
        external_outcome_ref=observation.external_outcome_ref,
        matched_control_ref=observation.matched_control_ref,
        lifecycle_before=credit.lifecycle,
        lifecycle_after=updated.lifecycle,
        reopened_support_refs=updated.reopened_support_refs,
        primitive_action_cost_before=(
            observation.primitive_action_cost_before
        ),
        primitive_action_cost_after=(
            observation.primitive_action_cost_after
        ),
    )
    return next_state, receipt


def settle_matched_recall_trial(
    state: WakeSleepCreditState,
    candidates: Sequence[MemoryCandidate],
    *,
    recall: RecallReceipt,
    consumption_decision: RecallConsumptionDecision,
    consumption_receipt: RecallConsumptionReceipt,
    stratum: RecallExperimentStratum,
    inject: RecallTrialArmOutcome,
    ablate: RecallTrialArmOutcome,
    memory_revision_sha256: str,
    contradiction_demote_at: int = 3,
) -> tuple[WakeSleepCreditState, MatchedRecallTrialReceipt]:
    """Settle one inject/ablate pair without equating its controller instances."""

    inject_sha = inject.to_receipt(stratum=stratum)["sha256"]
    ablate_sha = ablate.to_receipt(stratum=stratum)["sha256"]

    def reject(
        reason: str,
    ) -> tuple[WakeSleepCreditState, MatchedRecallTrialReceipt]:
        return state, MatchedRecallTrialReceipt(
            status="rejected",
            reason=reason,
            stratum_sha256=stratum.sha256,
            recall_sha256=recall.sha256,
            consumption_decision_sha256=(
                consumption_decision.sha256
            ),
            inject_arm_sha256=str(inject_sha),
            ablate_arm_sha256=str(ablate_sha),
            observed_decision_delta=None,
            observed_task_delta=None,
            observed_efficiency_delta=None,
            observed_information_yield_delta=None,
            settlement=None,
        )

    if recall.scope != stratum.scope:
        return reject("recall_stratum_scope_mismatch")
    if consumption_decision.scope != stratum.scope:
        return reject("consumption_stratum_scope_mismatch")
    if consumption_decision.recall_sha256 != recall.sha256:
        return reject("consumption_recall_mismatch")
    if consumption_receipt.status != "consumed":
        return reject("recall_not_consumed")
    if (
        consumption_receipt.decision_sha256
        != consumption_decision.sha256
    ):
        return reject("consumption_receipt_decision_mismatch")
    if inject.assignment != "inject" or ablate.assignment != "ablate":
        return reject("assignment_mismatch")
    if (
        inject.stratum_sha256 != stratum.sha256
        or ablate.stratum_sha256 != stratum.sha256
    ):
        return reject("stratum_mismatch")
    if inject.arm_id == ablate.arm_id:
        return reject("arm_identity_reused")
    if (
        inject.controller_instance_sha256
        == ablate.controller_instance_sha256
    ):
        return reject("controller_instance_reused")
    if (
        inject.runtime_controller_instance_ref
        == ablate.runtime_controller_instance_ref
    ):
        return reject("runtime_controller_instance_reused")
    if inject.trajectory_sha256 == ablate.trajectory_sha256:
        return reject("trajectory_identity_reused")
    if (
        inject.controller_instance_sha256
        != consumption_decision.controller_instance_sha256
    ):
        return reject("inject_controller_consumption_mismatch")
    if (
        inject.recall_consumption_sha256
        != consumption_receipt.sha256
    ):
        return reject("inject_consumption_receipt_mismatch")
    if (
        inject.primitive_action_cost
        != ablate.primitive_action_cost
        or inject.primitive_action_cost
        != stratum.primitive_action_cost
    ):
        return reject("primitive_action_cost_drift")

    selected = next(
        (
            row
            for row in recall.selections
            if row.memory_revision_sha256
            == memory_revision_sha256
        ),
        None,
    )
    if selected is None:
        return reject("memory_not_selected")
    task_delta = inject.task_score - ablate.task_score
    efficiency_delta = (
        inject.efficiency_score - ablate.efficiency_score
    )
    information_delta = (
        inject.information_yield - ablate.information_yield
    )
    decision_delta = (
        inject.decision_score(stratum)
        - ablate.decision_score(stratum)
    )
    next_state, settlement = settle_recall_credit(
        state,
        candidates,
        recall=recall,
        observation=CreditObservation(
            scope=stratum.scope,
            memory_revision_sha256=memory_revision_sha256,
            observed_decision_delta=decision_delta,
            external_outcome_ref=inject.external_outcome_ref,
            matched_control_ref=ablate.external_outcome_ref,
            primitive_action_cost_before=inject.primitive_action_cost,
            primitive_action_cost_after=ablate.primitive_action_cost,
            authoritative_contradiction=(
                decision_delta < 0.0 and task_delta < 0.0
            ),
        ),
        contradiction_demote_at=contradiction_demote_at,
    )
    if settlement.status != "settled":
        return state, MatchedRecallTrialReceipt(
            status="rejected",
            reason=f"credit_{settlement.reason}",
            stratum_sha256=stratum.sha256,
            recall_sha256=recall.sha256,
            consumption_decision_sha256=(
                consumption_decision.sha256
            ),
            inject_arm_sha256=str(inject_sha),
            ablate_arm_sha256=str(ablate_sha),
            observed_decision_delta=None,
            observed_task_delta=None,
            observed_efficiency_delta=None,
            observed_information_yield_delta=None,
            settlement=settlement,
        )
    return next_state, MatchedRecallTrialReceipt(
        status="settled",
        reason="matched_exchangeable_arms",
        stratum_sha256=stratum.sha256,
        recall_sha256=recall.sha256,
        consumption_decision_sha256=consumption_decision.sha256,
        inject_arm_sha256=str(inject_sha),
        ablate_arm_sha256=str(ablate_sha),
        observed_decision_delta=decision_delta,
        observed_task_delta=task_delta,
        observed_efficiency_delta=efficiency_delta,
        observed_information_yield_delta=information_delta,
        settlement=settlement,
    )
