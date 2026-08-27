"""Graded external utility for exact matched controller decisions.

Binary terminal settlement can miss externally adjudicated improvements when
both arms attain the task at different efficiency.  This module retains that
graded value in a separate authority channel.  It does not infer terminal task
status, information yield, or transport between choice contexts.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.temporal_decision_credit import DecisionChoiceAuthority


SCHEMA = "ztare-temporal-decision-utility-v1"
_TASK_STATUSES = frozenset({"open", "attained"})


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


def _finite_nonnegative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _canonical_named_values(
    values: Iterable[tuple[str, float]],
    *,
    name: str,
    nonnegative: bool,
) -> tuple[tuple[str, float], ...]:
    rows = tuple(sorted(
        (
            _nonempty(key, f"{name} key"),
            (
                _finite_nonnegative(value, f"{name}[{key}]")
                if nonnegative
                else _finite(value, f"{name}[{key}]")
            ),
        )
        for key, value in values
    ))
    if not rows:
        raise ValueError(f"{name} must be nonempty")
    if len({key for key, _value in rows}) != len(rows):
        raise ValueError(f"{name} keys must be unique")
    return rows


@dataclass(frozen=True)
class ExternalUtilityMeasure:
    """Externally owned weighted value measure for one task contract."""

    task_contract_sha256: str
    measure_id: str
    component_weights: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "task_contract_sha256",
            _nonempty(
                self.task_contract_sha256,
                "task_contract_sha256",
            ),
        )
        object.__setattr__(
            self,
            "measure_id",
            _nonempty(self.measure_id, "measure_id"),
        )
        weights = _canonical_named_values(
            self.component_weights,
            name="component_weights",
            nonnegative=True,
        )
        if not any(weight > 0.0 for _name, weight in weights):
            raise ValueError("utility measure requires a positive weight")
        object.__setattr__(self, "component_weights", weights)

    @property
    def component_names(self) -> tuple[str, ...]:
        return tuple(name for name, _weight in self.component_weights)

    def evaluate(
        self,
        component_values: Iterable[tuple[str, float]],
    ) -> float:
        values = _canonical_named_values(
            component_values,
            name="component_values",
            nonnegative=False,
        )
        if tuple(name for name, _value in values) != self.component_names:
            raise ValueError(
                "utility values crossed the frozen component identity"
            )
        by_name = dict(values)
        return sum(
            weight * by_name[name]
            for name, weight in self.component_weights
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "external_utility_measure",
            "task_contract_sha256": self.task_contract_sha256,
            "measure_id": self.measure_id,
            "component_weights": [
                {"name": name, "weight": weight}
                for name, weight in self.component_weights
            ],
            "direction": "higher_is_better",
            "authority": "external_measure_contract",
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "ExternalUtilityMeasure":
        measure = cls(
            task_contract_sha256=str(payload["task_contract_sha256"]),
            measure_id=str(payload["measure_id"]),
            component_weights=tuple(
                (
                    str(row["name"]),
                    float(row["weight"]),
                )
                for row in payload["component_weights"]
            ),
        )
        if dict(payload) != measure.to_receipt():
            raise ValueError("external utility measure receipt drifted")
        return measure


@dataclass(frozen=True)
class TemporalDecisionUtilityArm:
    """One delayed controller arm with externally measured graded value."""

    matched_pair_ref: str
    arm_id: str
    authority: DecisionChoiceAuthority
    chosen_option_family_sha256: str
    chosen_option_variant_sha256: str
    continuation_policy_sha256: str
    utility_measure: ExternalUtilityMeasure
    component_values: tuple[tuple[str, float], ...]
    primitive_action_cost: float
    immediate_task_status: str
    terminal_task_status: str
    external_value: float
    external_outcome_ref: str

    def __post_init__(self) -> None:
        for name in (
            "matched_pair_ref",
            "arm_id",
            "chosen_option_family_sha256",
            "chosen_option_variant_sha256",
            "continuation_policy_sha256",
            "external_outcome_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if (
            self.utility_measure.task_contract_sha256
            != self.authority.task_contract_sha256
        ):
            raise ValueError("utility measure crossed task authority")
        if (
            self.chosen_option_family_sha256
            not in self.authority.available_option_family_sha256s
        ):
            raise ValueError("chosen option is outside the authority choice set")
        values = _canonical_named_values(
            self.component_values,
            name="component_values",
            nonnegative=False,
        )
        object.__setattr__(self, "component_values", values)
        computed = self.utility_measure.evaluate(values)
        external = _finite(self.external_value, "external_value")
        if not math.isclose(
            computed,
            external,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "external value does not match the frozen utility measure"
            )
        object.__setattr__(self, "external_value", external)
        cost = _finite_nonnegative(
            self.primitive_action_cost,
            "primitive_action_cost",
        )
        if cost <= 0.0:
            raise ValueError("primitive_action_cost must be positive")
        object.__setattr__(self, "primitive_action_cost", cost)
        if self.immediate_task_status != "open":
            raise ValueError("utility arm first decision must be nonterminal")
        if self.terminal_task_status not in _TASK_STATUSES:
            raise ValueError("unknown terminal_task_status")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "temporal_decision_utility_arm",
            "matched_pair_ref": self.matched_pair_ref,
            "arm_id": self.arm_id,
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "chosen_option_family_sha256": (
                self.chosen_option_family_sha256
            ),
            "chosen_option_variant_sha256": (
                self.chosen_option_variant_sha256
            ),
            "continuation_policy_sha256": (
                self.continuation_policy_sha256
            ),
            "utility_measure": self.utility_measure.to_receipt(),
            "utility_measure_sha256": self.utility_measure.sha256,
            "component_values": [
                {"name": name, "value": value}
                for name, value in self.component_values
            ],
            "primitive_action_cost": self.primitive_action_cost,
            "immediate_task_status": self.immediate_task_status,
            "terminal_task_status": self.terminal_task_status,
            "external_value": self.external_value,
            "external_outcome_ref": self.external_outcome_ref,
            "terminal_task_credit_authorized": False,
            "information_yield_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "TemporalDecisionUtilityArm":
        authority = DecisionChoiceAuthority.from_receipt(
            dict(payload["authority"])
        )
        if str(payload["authority_sha256"]) != authority.sha256:
            raise ValueError("utility arm authority identity drifted")
        measure = ExternalUtilityMeasure.from_receipt(
            dict(payload["utility_measure"])
        )
        if str(payload["utility_measure_sha256"]) != measure.sha256:
            raise ValueError("utility arm measure identity drifted")
        arm = cls(
            matched_pair_ref=str(payload["matched_pair_ref"]),
            arm_id=str(payload["arm_id"]),
            authority=authority,
            chosen_option_family_sha256=str(
                payload["chosen_option_family_sha256"]
            ),
            chosen_option_variant_sha256=str(
                payload["chosen_option_variant_sha256"]
            ),
            continuation_policy_sha256=str(
                payload["continuation_policy_sha256"]
            ),
            utility_measure=measure,
            component_values=tuple(
                (
                    str(row["name"]),
                    float(row["value"]),
                )
                for row in payload["component_values"]
            ),
            primitive_action_cost=float(payload["primitive_action_cost"]),
            immediate_task_status=str(payload["immediate_task_status"]),
            terminal_task_status=str(payload["terminal_task_status"]),
            external_value=float(payload["external_value"]),
            external_outcome_ref=str(payload["external_outcome_ref"]),
        )
        if dict(payload) != arm.to_receipt():
            raise ValueError("temporal utility arm receipt drifted")
        return arm


@dataclass(frozen=True)
class MatchedTemporalUtilityReceipt:
    """Settlement of one exact matched pair under one external measure."""

    matched_pair_ref: str
    status: str
    reason: str
    authority_sha256: str
    utility_measure_sha256: str
    preferred_option_family_sha256: str = ""
    hazardous_option_family_sha256: str = ""
    preferred_arm_sha256: str = ""
    contrast_arm_sha256: str = ""
    external_value_delta: float = 0.0
    primitive_action_cost_per_arm: float | None = None
    evidence_refs: tuple[str, ...] = ()

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "matched_temporal_utility_receipt",
            "matched_pair_ref": self.matched_pair_ref,
            "status": self.status,
            "reason": self.reason,
            "authority_sha256": self.authority_sha256,
            "utility_measure_sha256": self.utility_measure_sha256,
            "preferred_option_family_sha256": (
                self.preferred_option_family_sha256
            ),
            "hazardous_option_family_sha256": (
                self.hazardous_option_family_sha256
            ),
            "preferred_arm_sha256": self.preferred_arm_sha256,
            "contrast_arm_sha256": self.contrast_arm_sha256,
            "external_value_delta": self.external_value_delta,
            "primitive_action_cost_per_arm": (
                self.primitive_action_cost_per_arm
            ),
            "evidence_refs": list(self.evidence_refs),
            "authority": "matched_external_utility_adjudication",
            "terminal_task_credit_authorized": False,
            "information_yield_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def settle_matched_temporal_utility_pair(
    left: TemporalDecisionUtilityArm,
    right: TemporalDecisionUtilityArm,
) -> MatchedTemporalUtilityReceipt:
    """Settle a graded pair without changing either arm's evidence."""

    def refuse(reason: str) -> MatchedTemporalUtilityReceipt:
        return MatchedTemporalUtilityReceipt(
            matched_pair_ref=left.matched_pair_ref,
            status="refused",
            reason=reason,
            authority_sha256=left.authority.sha256,
            utility_measure_sha256=left.utility_measure.sha256,
        )

    if right.matched_pair_ref != left.matched_pair_ref:
        return refuse("matched_pair_identity_mismatch")
    if left.arm_id == right.arm_id or left.sha256 == right.sha256:
        return refuse("arm_identity_reused")
    if left.authority != right.authority:
        return refuse("decision_choice_authority_mismatch")
    if (
        left.continuation_policy_sha256
        != right.continuation_policy_sha256
    ):
        return refuse("continuation_policy_mismatch")
    if left.utility_measure != right.utility_measure:
        return refuse("external_utility_measure_mismatch")
    if (
        left.chosen_option_family_sha256
        == right.chosen_option_family_sha256
    ):
        return refuse("option_family_not_contrasted")
    if (
        left.chosen_option_variant_sha256
        == right.chosen_option_variant_sha256
    ):
        return refuse("option_variant_identity_reused")
    if left.external_outcome_ref == right.external_outcome_ref:
        return refuse("external_evidence_identity_reused")
    if left.primitive_action_cost != right.primitive_action_cost:
        return refuse("primitive_action_cost_mismatch")
    delta = left.external_value - right.external_value
    evidence_refs = tuple(sorted({
        left.external_outcome_ref,
        right.external_outcome_ref,
    }))
    if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=1e-12):
        return MatchedTemporalUtilityReceipt(
            matched_pair_ref=left.matched_pair_ref,
            status="uninformative",
            reason="external_utility_tie",
            authority_sha256=left.authority.sha256,
            utility_measure_sha256=left.utility_measure.sha256,
            primitive_action_cost_per_arm=left.primitive_action_cost,
            evidence_refs=evidence_refs,
        )
    preferred, contrast = (
        (left, right) if delta > 0.0 else (right, left)
    )
    return MatchedTemporalUtilityReceipt(
        matched_pair_ref=left.matched_pair_ref,
        status="settled",
        reason="matched_external_utility_contrast",
        authority_sha256=left.authority.sha256,
        utility_measure_sha256=left.utility_measure.sha256,
        preferred_option_family_sha256=(
            preferred.chosen_option_family_sha256
        ),
        hazardous_option_family_sha256=(
            contrast.chosen_option_family_sha256
        ),
        preferred_arm_sha256=preferred.sha256,
        contrast_arm_sha256=contrast.sha256,
        external_value_delta=abs(delta),
        primitive_action_cost_per_arm=left.primitive_action_cost,
        evidence_refs=evidence_refs,
    )


@dataclass(frozen=True)
class TemporalDecisionUtilityJudgment:
    """Exact-scope graded preference for one controller option."""

    authority: DecisionChoiceAuthority
    utility_measure: ExternalUtilityMeasure
    option_family_sha256: str
    status: str
    preferred_support: int
    hazard_support: int
    mean_signed_external_delta: float
    matched_pair_sha256s: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    @property
    def preference(self) -> int:
        if self.status == "utility_preferred":
            return 1
        if self.status == "utility_hazard":
            return -1
        return 0

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "temporal_decision_utility_judgment",
            "authority": self.authority.to_receipt(),
            "authority_sha256": self.authority.sha256,
            "utility_measure": self.utility_measure.to_receipt(),
            "utility_measure_sha256": self.utility_measure.sha256,
            "option_family_sha256": self.option_family_sha256,
            "status": self.status,
            "preference": self.preference,
            "preferred_support": self.preferred_support,
            "hazard_support": self.hazard_support,
            "mean_signed_external_delta": (
                self.mean_signed_external_delta
            ),
            "matched_pair_sha256s": list(self.matched_pair_sha256s),
            "evidence_refs": list(self.evidence_refs),
            "authority_kind": "matched_external_utility_adjudication",
            "terminal_task_credit_authorized": False,
            "information_yield_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class TemporalDecisionUtilityCompilation:
    pair_receipts: tuple[MatchedTemporalUtilityReceipt, ...]
    judgments: tuple[TemporalDecisionUtilityJudgment, ...]
    minimum_support: int

    def to_receipt(self) -> dict[str, Any]:
        settled = tuple(
            row for row in self.pair_receipts if row.status == "settled"
        )
        payload = {
            "schema": SCHEMA,
            "kind": "temporal_decision_utility_compilation",
            "minimum_support": self.minimum_support,
            "pair_receipts": [
                row.to_receipt() for row in self.pair_receipts
            ],
            "judgments": [row.to_receipt() for row in self.judgments],
            "settled_pair_count": len(settled),
            "mean_settled_external_delta": (
                sum(row.external_value_delta for row in settled)
                / len(settled)
                if settled
                else 0.0
            ),
            "authority": "matched_external_utility_adjudication",
            "terminal_task_credit_authorized": False,
            "information_yield_authorized": False,
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def compile_temporal_decision_utility(
    pairs: Sequence[
        tuple[TemporalDecisionUtilityArm, TemporalDecisionUtilityArm]
    ],
    *,
    minimum_support: int = 2,
) -> TemporalDecisionUtilityCompilation:
    """Aggregate graded pair contrasts at exact authority and measure scope."""

    if isinstance(minimum_support, bool) or minimum_support <= 0:
        raise ValueError("minimum_support must be positive")
    pair_refs = [
        left.matched_pair_ref for left, _right in pairs
    ]
    if len(set(pair_refs)) != len(pair_refs):
        raise ValueError("matched utility pair identity was reused")
    receipts = tuple(
        settle_matched_temporal_utility_pair(left, right)
        for left, right in pairs
    )
    authorities: dict[str, DecisionChoiceAuthority] = {}
    measures: dict[str, ExternalUtilityMeasure] = {}
    counts: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (left, _right), receipt in zip(pairs, receipts):
        authority_sha = left.authority.sha256
        measure_sha = left.utility_measure.sha256
        authorities[authority_sha] = left.authority
        measures[measure_sha] = left.utility_measure
        if receipt.status != "settled":
            continue
        for direction, option, signed_delta in (
            (
                "preferred",
                receipt.preferred_option_family_sha256,
                receipt.external_value_delta,
            ),
            (
                "hazard",
                receipt.hazardous_option_family_sha256,
                -receipt.external_value_delta,
            ),
        ):
            row = counts.setdefault(
                (authority_sha, measure_sha, option),
                {
                    "preferred": 0,
                    "hazard": 0,
                    "signed_deltas": [],
                    "pair_sha256s": [],
                    "evidence_refs": set(),
                },
            )
            row[direction] += 1
            row["signed_deltas"].append(signed_delta)
            row["pair_sha256s"].append(receipt.sha256)
            row["evidence_refs"].update(receipt.evidence_refs)
    judgments = []
    for (
        authority_sha,
        measure_sha,
        option,
    ), row in sorted(counts.items()):
        preferred = int(row["preferred"])
        hazard = int(row["hazard"])
        if preferred and hazard:
            status = "utility_conflict"
        elif preferred >= minimum_support:
            status = "utility_preferred"
        elif hazard >= minimum_support:
            status = "utility_hazard"
        else:
            status = "undersampled"
        signed_deltas = tuple(map(float, row["signed_deltas"]))
        judgments.append(TemporalDecisionUtilityJudgment(
            authority=authorities[authority_sha],
            utility_measure=measures[measure_sha],
            option_family_sha256=option,
            status=status,
            preferred_support=preferred,
            hazard_support=hazard,
            mean_signed_external_delta=(
                sum(signed_deltas) / len(signed_deltas)
            ),
            matched_pair_sha256s=tuple(sorted(row["pair_sha256s"])),
            evidence_refs=tuple(sorted(row["evidence_refs"])),
        ))
    return TemporalDecisionUtilityCompilation(
        pair_receipts=receipts,
        judgments=tuple(judgments),
        minimum_support=int(minimum_support),
    )


__all__ = [
    "ExternalUtilityMeasure",
    "MatchedTemporalUtilityReceipt",
    "TemporalDecisionUtilityArm",
    "TemporalDecisionUtilityCompilation",
    "TemporalDecisionUtilityJudgment",
    "compile_temporal_decision_utility",
    "settle_matched_temporal_utility_pair",
]
