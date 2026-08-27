"""Matched distal credit for finite chains of controller decisions.

Immediate controller-choice credit cannot value an experiment whose task
receipt remains open but whose successor decision state later enables task
discharge.  This module keeps that delayed task authority separate from
predicted-versus-observed information-yield calibration.

Credit is admitted only from matched chains that share the complete first
choice authority, differ in the first selected option, retain one downstream
controller policy, pay equal primitive cost, and end in attained/open external
outcomes.  Information gain never substitutes for task discharge.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256


SCHEMA = "ztare-temporal-decision-credit-v1"
_TASK_STATUSES = frozenset({"open", "attained"})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _canonical(values: Iterable[str], name: str) -> tuple[str, ...]:
    rows = tuple(sorted({
        _nonempty(value, name) for value in values
    }))
    if not rows:
        raise ValueError(f"{name} must be nonempty")
    return rows


def _finite_nonnegative(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


@dataclass(frozen=True)
class DecisionChoiceAuthority:
    """Complete authority of one reproducible controller choice surface."""

    task_contract_sha256: str
    decision_namespace: str
    choice_context_sha256: str
    continuation_context_sha256: str
    available_option_family_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "task_contract_sha256",
            "decision_namespace",
            "choice_context_sha256",
            "continuation_context_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "available_option_family_sha256s",
            _canonical(
                self.available_option_family_sha256s,
                "available_option_family_sha256s",
            ),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_choice_authority",
            "task_contract_sha256": self.task_contract_sha256,
            "decision_namespace": self.decision_namespace,
            "choice_context_sha256": self.choice_context_sha256,
            "continuation_context_sha256": (
                self.continuation_context_sha256
            ),
            "available_option_family_sha256s": list(
                self.available_option_family_sha256s
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "DecisionChoiceAuthority":
        authority = cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            decision_namespace=str(payload["decision_namespace"]),
            choice_context_sha256=str(payload["choice_context_sha256"]),
            continuation_context_sha256=str(
                payload["continuation_context_sha256"]
            ),
            available_option_family_sha256s=tuple(map(
                str,
                payload["available_option_family_sha256s"],
            )),
        )
        if dict(payload) != authority.to_receipt():
            raise ValueError("decision choice authority receipt drifted")
        return authority


@dataclass(frozen=True)
class DecisionEligibilityEdge:
    """One finite-lived decision eligibility trace and its local readout."""

    chain_ref: str
    edge_index: int
    authority: DecisionChoiceAuthority
    chosen_option_family_sha256: str
    chosen_option_variant_sha256: str
    successor_decision_state_sha256: str
    predicted_information_yield: float
    observed_information_yield: float
    information_yield_measure_sha256: str
    primitive_action_cost: float
    immediate_task_status: str
    evidence_ref: str

    def __post_init__(self) -> None:
        for name in (
            "chain_ref",
            "chosen_option_family_sha256",
            "chosen_option_variant_sha256",
            "successor_decision_state_sha256",
            "information_yield_measure_sha256",
            "evidence_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if isinstance(self.edge_index, bool) or self.edge_index < 0:
            raise ValueError("edge_index must be a nonnegative integer")
        if (
            self.chosen_option_family_sha256
            not in self.authority.available_option_family_sha256s
        ):
            raise ValueError("chosen option is outside the authority choice set")
        object.__setattr__(
            self,
            "predicted_information_yield",
            _finite_nonnegative(
                self.predicted_information_yield,
                "predicted_information_yield",
            ),
        )
        object.__setattr__(
            self,
            "observed_information_yield",
            _finite_nonnegative(
                self.observed_information_yield,
                "observed_information_yield",
            ),
        )
        cost = _finite_nonnegative(
            self.primitive_action_cost,
            "primitive_action_cost",
        )
        if cost <= 0.0:
            raise ValueError("primitive_action_cost must be positive")
        object.__setattr__(self, "primitive_action_cost", cost)
        if self.immediate_task_status not in _TASK_STATUSES:
            raise ValueError("unknown immediate_task_status")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_eligibility_edge",
            "chain_ref": self.chain_ref,
            "edge_index": self.edge_index,
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "chosen_option_family_sha256": (
                self.chosen_option_family_sha256
            ),
            "chosen_option_variant_sha256": (
                self.chosen_option_variant_sha256
            ),
            "successor_decision_state_sha256": (
                self.successor_decision_state_sha256
            ),
            "predicted_information_yield": (
                self.predicted_information_yield
            ),
            "observed_information_yield": (
                self.observed_information_yield
            ),
            "information_yield_measure_sha256": (
                self.information_yield_measure_sha256
            ),
            "primitive_action_cost": self.primitive_action_cost,
            "immediate_task_status": self.immediate_task_status,
            "evidence_ref": self.evidence_ref,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "DecisionEligibilityEdge":
        authority = DecisionChoiceAuthority.from_receipt(
            dict(payload["authority"])
        )
        if str(payload["authority_sha256"]) != authority.sha256:
            raise ValueError("decision edge authority identity drifted")
        edge = cls(
            chain_ref=str(payload["chain_ref"]),
            edge_index=int(payload["edge_index"]),
            authority=authority,
            chosen_option_family_sha256=str(
                payload["chosen_option_family_sha256"]
            ),
            chosen_option_variant_sha256=str(
                payload["chosen_option_variant_sha256"]
            ),
            successor_decision_state_sha256=str(
                payload["successor_decision_state_sha256"]
            ),
            predicted_information_yield=float(
                payload["predicted_information_yield"]
            ),
            observed_information_yield=float(
                payload["observed_information_yield"]
            ),
            information_yield_measure_sha256=str(
                payload["information_yield_measure_sha256"]
            ),
            primitive_action_cost=float(payload["primitive_action_cost"]),
            immediate_task_status=str(payload["immediate_task_status"]),
            evidence_ref=str(payload["evidence_ref"]),
        )
        if dict(payload) != edge.to_receipt():
            raise ValueError("decision eligibility edge receipt drifted")
        return edge


@dataclass(frozen=True)
class DecisionEligibilityChain:
    """One controller trajectory ending in external task adjudication."""

    chain_ref: str
    matched_pair_ref: str
    arm_id: str
    continuation_policy_sha256: str
    edges: tuple[DecisionEligibilityEdge, ...]
    terminal_task_status: str
    terminal_adjudication_ref: str

    def __post_init__(self) -> None:
        for name in (
            "chain_ref",
            "matched_pair_ref",
            "arm_id",
            "continuation_policy_sha256",
            "terminal_adjudication_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if not self.edges:
            raise ValueError("decision eligibility chain must contain edges")
        for index, edge in enumerate(self.edges):
            if edge.chain_ref != self.chain_ref:
                raise ValueError("edge crossed chain identity")
            if edge.edge_index != index:
                raise ValueError("chain edge indices must be contiguous")
        first = self.edges[0].authority
        for edge in self.edges:
            authority = edge.authority
            if (
                authority.task_contract_sha256
                != first.task_contract_sha256
                or authority.decision_namespace
                != first.decision_namespace
                or authority.continuation_context_sha256
                != first.continuation_context_sha256
            ):
                raise ValueError("chain crossed task or controller authority")
        for left, right in zip(self.edges, self.edges[1:]):
            if (
                left.successor_decision_state_sha256
                != right.authority.choice_context_sha256
            ):
                raise ValueError("chain successor does not bind the next choice")
        if self.terminal_task_status not in _TASK_STATUSES:
            raise ValueError("unknown terminal_task_status")

    @property
    def primitive_action_cost(self) -> float:
        return sum(edge.primitive_action_cost for edge in self.edges)

    @property
    def eligibility_delay_steps(self) -> int:
        return len(self.edges) - 1

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_eligibility_chain",
            "chain_ref": self.chain_ref,
            "matched_pair_ref": self.matched_pair_ref,
            "arm_id": self.arm_id,
            "continuation_policy_sha256": (
                self.continuation_policy_sha256
            ),
            "edges": [edge.to_receipt() for edge in self.edges],
            "edge_count": len(self.edges),
            "eligibility_delay_steps": self.eligibility_delay_steps,
            "primitive_action_cost": self.primitive_action_cost,
            "terminal_task_status": self.terminal_task_status,
            "terminal_adjudication_ref": self.terminal_adjudication_ref,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "DecisionEligibilityChain":
        chain = cls(
            chain_ref=str(payload["chain_ref"]),
            matched_pair_ref=str(payload["matched_pair_ref"]),
            arm_id=str(payload["arm_id"]),
            continuation_policy_sha256=str(
                payload["continuation_policy_sha256"]
            ),
            edges=tuple(
                DecisionEligibilityEdge.from_receipt(dict(row))
                for row in payload["edges"]
            ),
            terminal_task_status=str(payload["terminal_task_status"]),
            terminal_adjudication_ref=str(
                payload["terminal_adjudication_ref"]
            ),
        )
        if dict(payload) != chain.to_receipt():
            raise ValueError("decision eligibility chain receipt drifted")
        return chain


@dataclass(frozen=True)
class MatchedTemporalCreditReceipt:
    """Adjudication of one exact-source pair of delayed decision chains."""

    matched_pair_ref: str
    status: str
    reason: str
    first_authority_sha256: str
    enabling_option_family_sha256: str = ""
    hazardous_option_family_sha256: str = ""
    eligibility_delay_steps: int | None = None
    positive_chain_sha256: str = ""
    contrast_chain_sha256: str = ""
    evidence_refs: tuple[str, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "matched_temporal_credit_receipt",
            "matched_pair_ref": self.matched_pair_ref,
            "status": self.status,
            "reason": self.reason,
            "first_authority_sha256": self.first_authority_sha256,
            "enabling_option_family_sha256": (
                self.enabling_option_family_sha256
            ),
            "hazardous_option_family_sha256": (
                self.hazardous_option_family_sha256
            ),
            "eligibility_delay_steps": self.eligibility_delay_steps,
            "positive_chain_sha256": self.positive_chain_sha256,
            "contrast_chain_sha256": self.contrast_chain_sha256,
            "evidence_refs": list(self.evidence_refs),
            "authority": "matched_external_terminal_adjudication",
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def settle_matched_temporal_pair(
    left: DecisionEligibilityChain,
    right: DecisionEligibilityChain,
    *,
    max_eligibility_delay_steps: int,
) -> MatchedTemporalCreditReceipt:
    """Settle one delayed chain pair without treating information as reward."""

    if (
        isinstance(max_eligibility_delay_steps, bool)
        or max_eligibility_delay_steps < 0
    ):
        raise ValueError("max_eligibility_delay_steps must be nonnegative")
    pair_ref = left.matched_pair_ref
    first_authority = left.edges[0].authority

    def refuse(reason: str) -> MatchedTemporalCreditReceipt:
        return MatchedTemporalCreditReceipt(
            matched_pair_ref=pair_ref,
            status="refused",
            reason=reason,
            first_authority_sha256=first_authority.sha256,
        )

    if right.matched_pair_ref != pair_ref:
        return refuse("matched_pair_identity_mismatch")
    if left.chain_ref == right.chain_ref or left.arm_id == right.arm_id:
        return refuse("chain_or_arm_identity_reused")
    if left.edges[0].authority != right.edges[0].authority:
        return refuse("first_choice_authority_mismatch")
    if left.continuation_policy_sha256 != right.continuation_policy_sha256:
        return refuse("continuation_policy_mismatch")
    if (
        left.edges[0].chosen_option_family_sha256
        == right.edges[0].chosen_option_family_sha256
    ):
        return refuse("first_option_not_contrasted")
    if (
        left.edges[0].immediate_task_status != "open"
        or right.edges[0].immediate_task_status != "open"
    ):
        return refuse("first_decision_not_nonterminal")
    if (
        left.primitive_action_cost != right.primitive_action_cost
    ):
        return refuse("primitive_action_cost_mismatch")
    delay = max(
        left.eligibility_delay_steps,
        right.eligibility_delay_steps,
    )
    if delay > max_eligibility_delay_steps:
        return refuse("eligibility_trace_expired")
    outcomes = {
        left.terminal_task_status,
        right.terminal_task_status,
    }
    if outcomes != {"attained", "open"}:
        return MatchedTemporalCreditReceipt(
            matched_pair_ref=pair_ref,
            status="uninformative",
            reason="terminal_task_outcomes_not_contrasted",
            first_authority_sha256=first_authority.sha256,
            eligibility_delay_steps=delay,
            positive_chain_sha256="",
            contrast_chain_sha256="",
            evidence_refs=tuple(sorted({
                left.terminal_adjudication_ref,
                right.terminal_adjudication_ref,
            })),
        )
    positive, contrast = (
        (left, right)
        if left.terminal_task_status == "attained"
        else (right, left)
    )
    return MatchedTemporalCreditReceipt(
        matched_pair_ref=pair_ref,
        status="settled",
        reason="matched_delayed_terminal_contrast",
        first_authority_sha256=first_authority.sha256,
        enabling_option_family_sha256=(
            positive.edges[0].chosen_option_family_sha256
        ),
        hazardous_option_family_sha256=(
            contrast.edges[0].chosen_option_family_sha256
        ),
        eligibility_delay_steps=delay,
        positive_chain_sha256=positive.sha256,
        contrast_chain_sha256=contrast.sha256,
        evidence_refs=tuple(sorted({
            positive.terminal_adjudication_ref,
            contrast.terminal_adjudication_ref,
        })),
    )


@dataclass(frozen=True)
class TemporalDecisionTaskJudgment:
    """Distal task value for one option at one exact choice authority."""

    authority: DecisionChoiceAuthority
    option_family_sha256: str
    status: str
    enable_support: int
    hazard_support: int
    maximum_delay_steps: int
    matched_pair_sha256s: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    @property
    def preference(self) -> int:
        if self.status == "task_credited":
            return 1
        if self.status == "task_hazard":
            return -1
        return 0

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "temporal_decision_task_judgment",
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "option_family_sha256": self.option_family_sha256,
            "status": self.status,
            "preference": self.preference,
            "enable_support": self.enable_support,
            "hazard_support": self.hazard_support,
            "maximum_delay_steps": self.maximum_delay_steps,
            "matched_pair_sha256s": list(self.matched_pair_sha256s),
            "evidence_refs": list(self.evidence_refs),
            "authority_kind": "matched_external_terminal_adjudication",
        }
        return {**payload, "sha256": stable_sha256(payload)}


@dataclass(frozen=True)
class TemporalDecisionCreditCompilation:
    pair_receipts: tuple[MatchedTemporalCreditReceipt, ...]
    judgments: tuple[TemporalDecisionTaskJudgment, ...]
    minimum_support: int
    max_eligibility_delay_steps: int

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "temporal_decision_credit_compilation",
            "minimum_support": self.minimum_support,
            "max_eligibility_delay_steps": (
                self.max_eligibility_delay_steps
            ),
            "pair_receipts": [
                receipt.to_receipt() for receipt in self.pair_receipts
            ],
            "judgments": [
                judgment.to_receipt() for judgment in self.judgments
            ],
            "settled_pair_count": sum(
                receipt.status == "settled"
                for receipt in self.pair_receipts
            ),
            "task_credit_authority": (
                "matched_external_terminal_adjudication"
            ),
        }
        return {**payload, "sha256": stable_sha256(payload)}


def compile_temporal_decision_credit(
    pairs: Sequence[
        tuple[DecisionEligibilityChain, DecisionEligibilityChain]
    ],
    *,
    minimum_support: int = 2,
    max_eligibility_delay_steps: int = 4,
) -> TemporalDecisionCreditCompilation:
    """Aggregate exact-scope delayed contrasts into controller preferences."""

    if isinstance(minimum_support, bool) or minimum_support <= 0:
        raise ValueError("minimum_support must be positive")
    receipts = tuple(
        settle_matched_temporal_pair(
            left,
            right,
            max_eligibility_delay_steps=max_eligibility_delay_steps,
        )
        for left, right in pairs
    )
    authorities: dict[str, DecisionChoiceAuthority] = {}
    counts: dict[tuple[str, str], dict[str, Any]] = {}
    for (left, _right), receipt in zip(pairs, receipts):
        authority = left.edges[0].authority
        authorities[authority.sha256] = authority
        if receipt.status != "settled":
            continue
        for direction, option in (
            ("enable", receipt.enabling_option_family_sha256),
            ("hazard", receipt.hazardous_option_family_sha256),
        ):
            row = counts.setdefault(
                (authority.sha256, option),
                {
                    "enable": 0,
                    "hazard": 0,
                    "delays": [],
                    "pair_sha256s": [],
                    "evidence_refs": set(),
                },
            )
            row[direction] += 1
            row["delays"].append(int(receipt.eligibility_delay_steps or 0))
            row["pair_sha256s"].append(receipt.sha256)
            row["evidence_refs"].update(receipt.evidence_refs)
    judgments = []
    for (authority_sha, option), row in sorted(counts.items()):
        enable = int(row["enable"])
        hazard = int(row["hazard"])
        if enable >= minimum_support and hazard:
            status = "credit_conflict"
        elif hazard >= minimum_support and enable:
            status = "credit_conflict"
        elif enable >= minimum_support:
            status = "task_credited"
        elif hazard >= minimum_support:
            status = "task_hazard"
        else:
            status = "undersampled"
        judgments.append(TemporalDecisionTaskJudgment(
            authority=authorities[authority_sha],
            option_family_sha256=option,
            status=status,
            enable_support=enable,
            hazard_support=hazard,
            maximum_delay_steps=max(row["delays"], default=0),
            matched_pair_sha256s=tuple(sorted(row["pair_sha256s"])),
            evidence_refs=tuple(sorted(row["evidence_refs"])),
        ))
    return TemporalDecisionCreditCompilation(
        pair_receipts=receipts,
        judgments=tuple(judgments),
        minimum_support=int(minimum_support),
        max_eligibility_delay_steps=int(max_eligibility_delay_steps),
    )


@dataclass(frozen=True)
class DecisionYieldCalibration:
    """Prediction error for one exact decision variant and yield measure."""

    authority: DecisionChoiceAuthority
    option_family_sha256: str
    option_variant_sha256: str
    information_yield_measure_sha256: str
    status: str
    observation_count: int
    mean_predicted_yield: float
    mean_observed_yield: float
    mean_error: float
    mean_absolute_error: float
    evidence_refs: tuple[str, ...]

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_yield_calibration",
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "option_family_sha256": self.option_family_sha256,
            "option_variant_sha256": self.option_variant_sha256,
            "information_yield_measure_sha256": (
                self.information_yield_measure_sha256
            ),
            "status": self.status,
            "observation_count": self.observation_count,
            "mean_predicted_yield": self.mean_predicted_yield,
            "mean_observed_yield": self.mean_observed_yield,
            "mean_error": self.mean_error,
            "mean_absolute_error": self.mean_absolute_error,
            "evidence_refs": list(self.evidence_refs),
            "authority_kind": "observed_information_yield_only",
            "task_credit_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "DecisionYieldCalibration":
        authority = DecisionChoiceAuthority.from_receipt(
            dict(payload["authority"])
        )
        if str(payload["authority_sha256"]) != authority.sha256:
            raise ValueError("yield calibration authority identity drifted")
        calibration = cls(
            authority=authority,
            option_family_sha256=str(
                payload["option_family_sha256"]
            ),
            option_variant_sha256=str(
                payload["option_variant_sha256"]
            ),
            information_yield_measure_sha256=str(
                payload["information_yield_measure_sha256"]
            ),
            status=str(payload["status"]),
            observation_count=int(payload["observation_count"]),
            mean_predicted_yield=float(
                payload["mean_predicted_yield"]
            ),
            mean_observed_yield=float(
                payload["mean_observed_yield"]
            ),
            mean_error=float(payload["mean_error"]),
            mean_absolute_error=float(payload["mean_absolute_error"]),
            evidence_refs=tuple(map(str, payload["evidence_refs"])),
        )
        if dict(payload) != calibration.to_receipt():
            raise ValueError("decision yield calibration receipt drifted")
        return calibration


def compile_decision_yield_calibration(
    chains: Iterable[DecisionEligibilityChain],
    *,
    minimum_observations: int = 2,
) -> tuple[DecisionYieldCalibration, ...]:
    """Calibrate information predictions without minting task value."""

    if (
        isinstance(minimum_observations, bool)
        or minimum_observations <= 0
    ):
        raise ValueError("minimum_observations must be positive")
    grouped: dict[
        tuple[str, str, str, str],
        list[DecisionEligibilityEdge],
    ] = {}
    authorities: dict[str, DecisionChoiceAuthority] = {}
    for chain in chains:
        for edge in chain.edges:
            authority_sha = edge.authority.sha256
            authorities[authority_sha] = edge.authority
            grouped.setdefault((
                authority_sha,
                edge.chosen_option_family_sha256,
                edge.chosen_option_variant_sha256,
                edge.information_yield_measure_sha256,
            ), []).append(edge)
    rows = []
    for key, edges in sorted(grouped.items()):
        authority_sha, family, variant, measure = key
        predicted = [
            edge.predicted_information_yield for edge in edges
        ]
        observed = [
            edge.observed_information_yield for edge in edges
        ]
        errors = [
            actual - forecast
            for forecast, actual in zip(predicted, observed)
        ]
        count = len(edges)
        rows.append(DecisionYieldCalibration(
            authority=authorities[authority_sha],
            option_family_sha256=family,
            option_variant_sha256=variant,
            information_yield_measure_sha256=measure,
            status=(
                "calibrated"
                if count >= minimum_observations
                else "provisional"
            ),
            observation_count=count,
            mean_predicted_yield=sum(predicted) / count,
            mean_observed_yield=sum(observed) / count,
            mean_error=sum(errors) / count,
            mean_absolute_error=(
                sum(abs(error) for error in errors) / count
            ),
            evidence_refs=tuple(sorted({
                edge.evidence_ref for edge in edges
            })),
        ))
    return tuple(rows)


def task_values_for_authority(
    compilation: TemporalDecisionCreditCompilation,
    authority: DecisionChoiceAuthority,
) -> Mapping[str, int]:
    """Expose only exact-authority distal preferences to a selector."""

    return {
        judgment.option_family_sha256: judgment.preference
        for judgment in compilation.judgments
        if judgment.authority == authority
    }


__all__ = [
    "DecisionChoiceAuthority",
    "DecisionEligibilityChain",
    "DecisionEligibilityEdge",
    "DecisionYieldCalibration",
    "MatchedTemporalCreditReceipt",
    "TemporalDecisionCreditCompilation",
    "TemporalDecisionTaskJudgment",
    "compile_decision_yield_calibration",
    "compile_temporal_decision_credit",
    "settle_matched_temporal_pair",
    "task_values_for_authority",
]
