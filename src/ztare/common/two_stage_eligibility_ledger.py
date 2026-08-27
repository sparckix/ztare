"""Two-stage collection and replay binding for delayed decision credit.

Episode collection preserves exact controller windows and information-yield
readouts but grants no task value. A separate replay contract owns
counterfactual pair identity and may bind a draft into a temporal decision
chain only when every frozen source and authority component matches.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.temporal_decision_credit import (
    DecisionChoiceAuthority,
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
)
from ztare.common.temporal_decision_utility import (
    ExternalUtilityMeasure,
    TemporalDecisionUtilityArm,
)


SCHEMA = "ztare-two-stage-eligibility-ledger-v1"
_TASK_STATUSES = frozenset({"open", "attained"})


def _nonempty(value: str, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be nonempty")
    return text


def _finite_nonnegative(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


@dataclass(frozen=True)
class DecisionWindowEvidence:
    """One collected decision window before any replay-pair authority."""

    authority: DecisionChoiceAuthority
    chosen_option_family_sha256: str
    chosen_option_variant_sha256: str
    successor_decision_state_sha256: str
    predicted_information_yield: float
    observed_information_yield: float
    information_yield_measure_sha256: str
    primitive_action_cost: float
    immediate_task_status: str
    decision_evidence_ref: str
    observed_yield_evidence_ref: str

    def __post_init__(self) -> None:
        for name in (
            "chosen_option_family_sha256",
            "chosen_option_variant_sha256",
            "successor_decision_state_sha256",
            "information_yield_measure_sha256",
            "decision_evidence_ref",
            "observed_yield_evidence_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
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
            "kind": "decision_window_evidence",
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
            "decision_evidence_ref": self.decision_evidence_ref,
            "observed_yield_evidence_ref": (
                self.observed_yield_evidence_ref
            ),
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
    ) -> "DecisionWindowEvidence":
        authority = DecisionChoiceAuthority.from_receipt(
            dict(payload["authority"])
        )
        if str(payload["authority_sha256"]) != authority.sha256:
            raise ValueError("decision window authority identity drifted")
        window = cls(
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
            decision_evidence_ref=str(payload["decision_evidence_ref"]),
            observed_yield_evidence_ref=str(
                payload["observed_yield_evidence_ref"]
            ),
        )
        if dict(payload) != window.to_receipt():
            raise ValueError("decision window evidence receipt drifted")
        return window


@dataclass(frozen=True)
class DecisionEpisodeDraft:
    """An exact finite episode admitted to replay, without pair authority."""

    episode_ref: str
    environment_source_sha256: str
    replay_prefix_sha256: str
    continuation_policy_sha256: str
    windows: tuple[DecisionWindowEvidence, ...]
    terminal_task_status: str
    terminal_adjudication_ref: str

    def __post_init__(self) -> None:
        for name in (
            "episode_ref",
            "environment_source_sha256",
            "replay_prefix_sha256",
            "continuation_policy_sha256",
            "terminal_adjudication_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if not self.windows:
            raise ValueError("decision episode draft requires windows")
        first = self.windows[0]
        if first.immediate_task_status != "open":
            raise ValueError("episode first decision must be nonterminal")
        for window in self.windows:
            if (
                window.authority.task_contract_sha256
                != first.authority.task_contract_sha256
                or window.authority.decision_namespace
                != first.authority.decision_namespace
                or window.authority.continuation_context_sha256
                != first.authority.continuation_context_sha256
            ):
                raise ValueError(
                    "episode crossed task or continuation authority"
                )
            if (
                window.information_yield_measure_sha256
                != first.information_yield_measure_sha256
            ):
                raise ValueError(
                    "episode crossed information-yield measure identity"
                )
        for left, right in zip(self.windows, self.windows[1:]):
            if (
                left.successor_decision_state_sha256
                != right.authority.choice_context_sha256
            ):
                raise ValueError(
                    "episode successor does not bind the next decision"
                )
        if self.terminal_task_status not in _TASK_STATUSES:
            raise ValueError("unknown terminal_task_status")
        if (
            self.windows[-1].immediate_task_status
            != self.terminal_task_status
        ):
            raise ValueError(
                "terminal adjudication does not match the final window"
            )

    @property
    def first_authority(self) -> DecisionChoiceAuthority:
        return self.windows[0].authority

    @property
    def eligibility_delay_steps(self) -> int:
        return len(self.windows) - 1

    @property
    def primitive_action_cost(self) -> float:
        return sum(window.primitive_action_cost for window in self.windows)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_episode_draft",
            "episode_ref": self.episode_ref,
            "environment_source_sha256": self.environment_source_sha256,
            "replay_prefix_sha256": self.replay_prefix_sha256,
            "continuation_policy_sha256": (
                self.continuation_policy_sha256
            ),
            "windows": [
                window.to_receipt() for window in self.windows
            ],
            "window_count": len(self.windows),
            "first_authority_sha256": self.first_authority.sha256,
            "information_yield_measure_sha256": (
                self.windows[0].information_yield_measure_sha256
            ),
            "eligibility_delay_steps": self.eligibility_delay_steps,
            "primitive_action_cost": self.primitive_action_cost,
            "terminal_task_status": self.terminal_task_status,
            "terminal_adjudication_ref": self.terminal_adjudication_ref,
            "pair_authority": "absent_until_sealed_replay_binding",
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
    ) -> "DecisionEpisodeDraft":
        draft = cls(
            episode_ref=str(payload["episode_ref"]),
            environment_source_sha256=str(
                payload["environment_source_sha256"]
            ),
            replay_prefix_sha256=str(payload["replay_prefix_sha256"]),
            continuation_policy_sha256=str(
                payload["continuation_policy_sha256"]
            ),
            windows=tuple(
                DecisionWindowEvidence.from_receipt(dict(row))
                for row in payload["windows"]
            ),
            terminal_task_status=str(payload["terminal_task_status"]),
            terminal_adjudication_ref=str(
                payload["terminal_adjudication_ref"]
            ),
        )
        if dict(payload) != draft.to_receipt():
            raise ValueError("decision episode draft receipt drifted")
        return draft


@dataclass(frozen=True)
class SealedDecisionReplayContract:
    """Frozen two-arm source authority for counterfactual episode replay."""

    contract_ref: str
    first_authority: DecisionChoiceAuthority
    continuation_policy_sha256: str
    environment_source_sha256: str
    replay_prefix_sha256: str
    information_yield_measure_sha256: str
    arm_option_family_sha256s: tuple[tuple[str, str], ...]
    max_eligibility_delay_steps: int

    def __post_init__(self) -> None:
        for name in (
            "contract_ref",
            "continuation_policy_sha256",
            "environment_source_sha256",
            "replay_prefix_sha256",
            "information_yield_measure_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        arms = tuple(sorted(
            (
                _nonempty(arm, "arm_id"),
                _nonempty(option, "option_family_sha256"),
            )
            for arm, option in self.arm_option_family_sha256s
        ))
        object.__setattr__(self, "arm_option_family_sha256s", arms)
        if len(arms) != 2:
            raise ValueError("sealed replay contracts require exactly two arms")
        if len({arm for arm, _option in arms}) != 2:
            raise ValueError("sealed replay arm identities must be distinct")
        if len({option for _arm, option in arms}) != 2:
            raise ValueError("sealed replay first options must be distinct")
        if any(
            option
            not in self.first_authority.available_option_family_sha256s
            for _arm, option in arms
        ):
            raise ValueError(
                "sealed replay arm option is outside the frozen choice set"
            )
        if (
            isinstance(self.max_eligibility_delay_steps, bool)
            or self.max_eligibility_delay_steps < 0
        ):
            raise ValueError(
                "max_eligibility_delay_steps must be nonnegative"
            )

    def option_for_arm(self, arm_id: str) -> str:
        arm = _nonempty(arm_id, "arm_id")
        return next(
            (
                option for candidate, option
                in self.arm_option_family_sha256s
                if candidate == arm
            ),
            "",
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "sealed_decision_replay_contract",
            "contract_ref": self.contract_ref,
            "first_authority": self.first_authority.to_receipt(),
            "first_authority_sha256": self.first_authority.sha256,
            "continuation_policy_sha256": (
                self.continuation_policy_sha256
            ),
            "environment_source_sha256": self.environment_source_sha256,
            "replay_prefix_sha256": self.replay_prefix_sha256,
            "information_yield_measure_sha256": (
                self.information_yield_measure_sha256
            ),
            "arm_option_family_sha256s": [
                {"arm_id": arm, "option_family_sha256": option}
                for arm, option in self.arm_option_family_sha256s
            ],
            "max_eligibility_delay_steps": (
                self.max_eligibility_delay_steps
            ),
            "pairing_authority": "sealed_exact_source_replay_contract",
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "SealedDecisionReplayContract":
        authority = DecisionChoiceAuthority.from_receipt(
            dict(payload["first_authority"])
        )
        if str(payload["first_authority_sha256"]) != authority.sha256:
            raise ValueError("replay contract authority identity drifted")
        contract = cls(
            contract_ref=str(payload["contract_ref"]),
            first_authority=authority,
            continuation_policy_sha256=str(
                payload["continuation_policy_sha256"]
            ),
            environment_source_sha256=str(
                payload["environment_source_sha256"]
            ),
            replay_prefix_sha256=str(payload["replay_prefix_sha256"]),
            information_yield_measure_sha256=str(
                payload["information_yield_measure_sha256"]
            ),
            arm_option_family_sha256s=tuple(
                (
                    str(row["arm_id"]),
                    str(row["option_family_sha256"]),
                )
                for row in payload["arm_option_family_sha256s"]
            ),
            max_eligibility_delay_steps=int(
                payload["max_eligibility_delay_steps"]
            ),
        )
        if dict(payload) != contract.to_receipt():
            raise ValueError("sealed replay contract receipt drifted")
        return contract


@dataclass(frozen=True)
class SealedDecisionReplayAssignment:
    """Prospective arm assignment distinct from every value channel."""

    assignment_ref: str
    contract: SealedDecisionReplayContract
    arm_id: str
    randomization_evidence_ref: str

    def __post_init__(self) -> None:
        for name in (
            "assignment_ref",
            "arm_id",
            "randomization_evidence_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        if not self.contract.option_for_arm(self.arm_id):
            raise ValueError("assignment names an undeclared replay arm")

    @property
    def option_family_sha256(self) -> str:
        return self.contract.option_for_arm(self.arm_id)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "sealed_decision_replay_assignment",
            "assignment_ref": self.assignment_ref,
            "contract": self.contract.to_receipt(),
            "contract_sha256": self.contract.sha256,
            "arm_id": self.arm_id,
            "option_family_sha256": self.option_family_sha256,
            "randomization_evidence_ref": self.randomization_evidence_ref,
            "authority": "sealed_randomized_experiment_assignment",
            "task_credit_authorized": False,
            "external_utility_authorized": False,
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
    ) -> "SealedDecisionReplayAssignment":
        contract = SealedDecisionReplayContract.from_receipt(
            dict(payload["contract"])
        )
        if str(payload["contract_sha256"]) != contract.sha256:
            raise ValueError("replay assignment contract identity drifted")
        assignment = cls(
            assignment_ref=str(payload["assignment_ref"]),
            contract=contract,
            arm_id=str(payload["arm_id"]),
            randomization_evidence_ref=str(
                payload["randomization_evidence_ref"]
            ),
        )
        if dict(payload) != assignment.to_receipt():
            raise ValueError("sealed replay assignment receipt drifted")
        return assignment


@dataclass(frozen=True)
class SealedDecisionUtilityContract:
    """Utility measure and adjudicator frozen before episode settlement."""

    contract_ref: str
    replay_contract: SealedDecisionReplayContract
    utility_measure: ExternalUtilityMeasure
    external_adjudicator_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "contract_ref",
            _nonempty(self.contract_ref, "contract_ref"),
        )
        object.__setattr__(
            self,
            "external_adjudicator_id",
            _nonempty(
                self.external_adjudicator_id,
                "external_adjudicator_id",
            ),
        )
        if (
            self.utility_measure.task_contract_sha256
            != self.replay_contract.first_authority.task_contract_sha256
        ):
            raise ValueError("utility contract crossed task authority")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "sealed_decision_utility_contract",
            "contract_ref": self.contract_ref,
            "replay_contract": self.replay_contract.to_receipt(),
            "replay_contract_sha256": self.replay_contract.sha256,
            "utility_measure": self.utility_measure.to_receipt(),
            "utility_measure_sha256": self.utility_measure.sha256,
            "external_adjudicator_id": self.external_adjudicator_id,
            "authority": "pre_episode_external_utility_contract",
        }
        return {**payload, "sha256": stable_sha256(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    @classmethod
    def from_receipt(
        cls,
        payload: Mapping[str, Any],
    ) -> "SealedDecisionUtilityContract":
        replay_contract = SealedDecisionReplayContract.from_receipt(
            dict(payload["replay_contract"])
        )
        if (
            str(payload["replay_contract_sha256"])
            != replay_contract.sha256
        ):
            raise ValueError("utility contract replay identity drifted")
        utility_measure = ExternalUtilityMeasure.from_receipt(
            dict(payload["utility_measure"])
        )
        if (
            str(payload["utility_measure_sha256"])
            != utility_measure.sha256
        ):
            raise ValueError("utility contract measure identity drifted")
        contract = cls(
            contract_ref=str(payload["contract_ref"]),
            replay_contract=replay_contract,
            utility_measure=utility_measure,
            external_adjudicator_id=str(
                payload["external_adjudicator_id"]
            ),
        )
        if dict(payload) != contract.to_receipt():
            raise ValueError("sealed utility contract receipt drifted")
        return contract


def _canonical_component_values(
    values: Iterable[tuple[str, float]],
) -> tuple[tuple[str, float], ...]:
    rows = tuple(sorted(
        (
            _nonempty(name, "component name"),
            float(value),
        )
        for name, value in values
    ))
    if not rows:
        raise ValueError("component_values must be nonempty")
    if len({name for name, _value in rows}) != len(rows):
        raise ValueError("component value names must be unique")
    if any(not math.isfinite(value) for _name, value in rows):
        raise ValueError("component values must be finite")
    return rows


@dataclass(frozen=True)
class DecisionEpisodeUtilityAdjudication:
    """Externally authored components bound to one completed episode."""

    utility_contract_sha256: str
    replay_assignment_sha256: str
    episode_sha256: str
    external_adjudicator_id: str
    component_values: tuple[tuple[str, float], ...]
    external_outcome_ref: str

    def __post_init__(self) -> None:
        for name in (
            "utility_contract_sha256",
            "replay_assignment_sha256",
            "episode_sha256",
            "external_adjudicator_id",
            "external_outcome_ref",
        ):
            object.__setattr__(
                self,
                name,
                _nonempty(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "component_values",
            _canonical_component_values(self.component_values),
        )

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "decision_episode_utility_adjudication",
            "utility_contract_sha256": self.utility_contract_sha256,
            "replay_assignment_sha256": self.replay_assignment_sha256,
            "episode_sha256": self.episode_sha256,
            "external_adjudicator_id": self.external_adjudicator_id,
            "component_values": [
                {"name": name, "value": value}
                for name, value in self.component_values
            ],
            "external_outcome_ref": self.external_outcome_ref,
            "authority": "external_episode_adjudicator",
            "task_credit_authorized": False,
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
    ) -> "DecisionEpisodeUtilityAdjudication":
        adjudication = cls(
            utility_contract_sha256=str(
                payload["utility_contract_sha256"]
            ),
            replay_assignment_sha256=str(
                payload["replay_assignment_sha256"]
            ),
            episode_sha256=str(payload["episode_sha256"]),
            external_adjudicator_id=str(
                payload["external_adjudicator_id"]
            ),
            component_values=tuple(
                (
                    str(row["name"]),
                    float(row["value"]),
                )
                for row in payload["component_values"]
            ),
            external_outcome_ref=str(payload["external_outcome_ref"]),
        )
        if dict(payload) != adjudication.to_receipt():
            raise ValueError("episode utility adjudication receipt drifted")
        return adjudication


def assemble_decision_episode_draft(
    windows: Iterable[Mapping[str, Any]],
    *,
    episode_ref: str,
    task_contract_sha256: str,
    environment_source_sha256: str,
    replay_prefix_sha256: str,
    continuation_policy_sha256: str,
    terminal_task_status: str,
    terminal_adjudication_ref: str,
    terminal_decision_state_sha256: str,
) -> DecisionEpisodeDraft:
    """Lower chronological H101-complete controller windows into one draft."""

    rows = tuple(dict(row) for row in windows)
    if not rows:
        raise ValueError("episode assembly requires decision windows")
    task = _nonempty(task_contract_sha256, "task_contract_sha256")
    terminal_state = _nonempty(
        terminal_decision_state_sha256,
        "terminal_decision_state_sha256",
    )
    lowered = []
    for index, row in enumerate(rows):
        forecast = row.get("information_yield_forecast")
        observation = row.get("information_yield_observation")
        if not isinstance(forecast, dict):
            raise ValueError("decision window lacks H101 yield forecast")
        if not isinstance(observation, dict):
            raise ValueError("decision window lacks H101 yield observation")
        if (
            forecast.get("schema")
            != "ztare-realized-protocol-information-yield-v1"
            or forecast.get("kind")
            != "protocol_information_yield_forecast"
            or forecast.get("task_credit_authorized") is not False
        ):
            raise ValueError("decision window yield forecast is not H101")
        if (
            observation.get("schema")
            != "ztare-realized-protocol-information-yield-v1"
            or observation.get("kind")
            != "protocol_information_yield_observation"
            or observation.get("status")
            not in {"witnessed_partition_cell", "committee_refuted"}
            or observation.get("task_credit_authorized") is not False
        ):
            raise ValueError("decision window yield observation is unavailable")
        if (
            str(observation.get("forecast_sha256") or "")
            != str(forecast.get("sha256") or "")
        ):
            raise ValueError("decision window crossed yield forecast identity")
        measure = str(forecast.get("measure_sha256") or "")
        if not measure or measure != str(
            observation.get("measure_sha256") or ""
        ):
            raise ValueError("decision window crossed yield measure identity")
        evidence_ref = str(
            observation.get("observation_evidence_ref") or ""
        ).strip()
        observation_sha = str(observation.get("sha256") or "").strip()
        if not evidence_ref or not observation_sha:
            raise ValueError(
                "decision window yield observation lacks evidence identity"
            )
        cost = forecast.get("cost")
        if not isinstance(cost, dict):
            raise ValueError("decision window yield forecast lacks cost")
        authority = DecisionChoiceAuthority(
            task_contract_sha256=task,
            decision_namespace=str(row["decision_namespace"]),
            choice_context_sha256=str(row["choice_context_sha256"]),
            continuation_context_sha256=str(
                row["continuation_context_sha256"]
            ),
            available_option_family_sha256s=tuple(map(
                str,
                row["available_option_family_sha256s"],
            )),
        )
        successor = (
            str(rows[index + 1]["choice_context_sha256"])
            if index + 1 < len(rows)
            else terminal_state
        )
        lowered.append(DecisionWindowEvidence(
            authority=authority,
            chosen_option_family_sha256=str(
                row["chosen_option_family_sha256"]
            ),
            chosen_option_variant_sha256=str(
                row["chosen_option_variant_sha256"]
            ),
            successor_decision_state_sha256=successor,
            predicted_information_yield=float(
                forecast["predicted_information_yield"]
            ),
            observed_information_yield=float(
                observation["observed_information_yield"]
            ),
            information_yield_measure_sha256=measure,
            primitive_action_cost=float(
                cost["primitive_execution_units"]
            ),
            immediate_task_status=str(row["outcome"]),
            decision_evidence_ref=str(row["evidence_ref"]),
            observed_yield_evidence_ref=observation_sha,
        ))
    return DecisionEpisodeDraft(
        episode_ref=episode_ref,
        environment_source_sha256=environment_source_sha256,
        replay_prefix_sha256=replay_prefix_sha256,
        continuation_policy_sha256=continuation_policy_sha256,
        windows=tuple(lowered),
        terminal_task_status=terminal_task_status,
        terminal_adjudication_ref=terminal_adjudication_ref,
    )


def record_decision_episode_draft(
    drafts: Iterable[DecisionEpisodeDraft],
    draft: DecisionEpisodeDraft,
) -> tuple[DecisionEpisodeDraft, ...]:
    """Idempotently append one episode while rejecting identity conflicts."""

    rows = tuple(drafts)
    conflicting = [
        row for row in rows
        if row.episode_ref == draft.episode_ref and row.sha256 != draft.sha256
    ]
    if conflicting:
        raise ValueError(
            "one episode identity cannot carry conflicting draft evidence"
        )
    by_sha = {row.sha256: row for row in rows}
    by_sha[draft.sha256] = draft
    return tuple(sorted(
        by_sha.values(),
        key=lambda row: row.sha256,
    ))


def save_decision_episode_drafts(
    path: str | Path,
    drafts: Iterable[DecisionEpisodeDraft],
) -> Path:
    """Atomically persist the unbound episode ledger."""

    target = Path(path)
    rows = tuple(sorted(drafts, key=lambda row: row.sha256))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps({
            "schema": "ztare-decision-episode-draft-ledger-v1",
            "drafts": [row.to_receipt() for row in rows],
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return target


def load_decision_episode_drafts(
    path: str | Path,
) -> tuple[DecisionEpisodeDraft, ...]:
    target = Path(path)
    if not target.exists():
        return ()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema")
        != "ztare-decision-episode-draft-ledger-v1"
    ):
        raise ValueError("unsupported decision episode draft ledger")
    rows = tuple(sorted(
        (
            DecisionEpisodeDraft.from_receipt(dict(row))
            for row in payload.get("drafts", ())
        ),
        key=lambda row: row.sha256,
    ))
    if len({row.sha256 for row in rows}) != len(rows):
        raise ValueError("decision episode draft ledger contains duplicates")
    if len({row.episode_ref for row in rows}) != len(rows):
        raise ValueError(
            "decision episode draft ledger contains identity conflicts"
        )
    return rows


def bind_episode_draft(
    draft: DecisionEpisodeDraft,
    contract: SealedDecisionReplayContract,
    *,
    arm_id: str,
) -> DecisionEligibilityChain:
    """Bind one episode only through its exact frozen replay arm."""

    arm = _nonempty(arm_id, "arm_id")
    expected_option = contract.option_for_arm(arm)
    if not expected_option:
        raise ValueError("episode names an undeclared replay arm")
    if draft.first_authority != contract.first_authority:
        raise ValueError("episode first-choice authority mismatch")
    if (
        draft.continuation_policy_sha256
        != contract.continuation_policy_sha256
    ):
        raise ValueError("episode continuation policy mismatch")
    if (
        draft.environment_source_sha256
        != contract.environment_source_sha256
    ):
        raise ValueError("episode environment source mismatch")
    if draft.replay_prefix_sha256 != contract.replay_prefix_sha256:
        raise ValueError("episode replay prefix mismatch")
    if (
        draft.windows[0].information_yield_measure_sha256
        != contract.information_yield_measure_sha256
    ):
        raise ValueError("episode information-yield measure mismatch")
    if (
        draft.windows[0].chosen_option_family_sha256
        != expected_option
    ):
        raise ValueError("episode first option does not match replay arm")
    if (
        draft.eligibility_delay_steps
        > contract.max_eligibility_delay_steps
    ):
        raise ValueError("episode eligibility trace expired")
    chain_ref = (
        "sealed-episode:"
        + stable_sha256({
            "contract_sha256": contract.sha256,
            "arm_id": arm,
            "episode_sha256": draft.sha256,
        })
    )
    edges = tuple(
        DecisionEligibilityEdge(
            chain_ref=chain_ref,
            edge_index=index,
            authority=window.authority,
            chosen_option_family_sha256=(
                window.chosen_option_family_sha256
            ),
            chosen_option_variant_sha256=(
                window.chosen_option_variant_sha256
            ),
            successor_decision_state_sha256=(
                window.successor_decision_state_sha256
            ),
            predicted_information_yield=(
                window.predicted_information_yield
            ),
            observed_information_yield=(
                window.observed_information_yield
            ),
            information_yield_measure_sha256=(
                window.information_yield_measure_sha256
            ),
            primitive_action_cost=window.primitive_action_cost,
            immediate_task_status=window.immediate_task_status,
            evidence_ref=(
                "episode-window:"
                + stable_sha256({
                    "window_sha256": window.sha256,
                    "decision_evidence_ref": (
                        window.decision_evidence_ref
                    ),
                    "observed_yield_evidence_ref": (
                        window.observed_yield_evidence_ref
                    ),
                })
            ),
        )
        for index, window in enumerate(draft.windows)
    )
    return DecisionEligibilityChain(
        chain_ref=chain_ref,
        matched_pair_ref="sealed-replay:" + contract.sha256,
        arm_id=arm,
        continuation_policy_sha256=(
            draft.continuation_policy_sha256
        ),
        edges=edges,
        terminal_task_status=draft.terminal_task_status,
        terminal_adjudication_ref=draft.terminal_adjudication_ref,
    )


def materialize_episode_utility_arm(
    draft: DecisionEpisodeDraft,
    assignment: SealedDecisionReplayAssignment,
    utility_contract: SealedDecisionUtilityContract,
    adjudication: DecisionEpisodeUtilityAdjudication,
) -> TemporalDecisionUtilityArm:
    """Lower one exactly bound episode into externally measured utility."""

    if (
        utility_contract.replay_contract.sha256
        != assignment.contract.sha256
    ):
        raise ValueError("utility contract crossed replay authority")
    if adjudication.utility_contract_sha256 != utility_contract.sha256:
        raise ValueError("utility adjudication contract mismatch")
    if adjudication.replay_assignment_sha256 != assignment.sha256:
        raise ValueError("utility adjudication assignment mismatch")
    if adjudication.episode_sha256 != draft.sha256:
        raise ValueError("utility adjudication episode mismatch")
    if (
        adjudication.external_adjudicator_id
        != utility_contract.external_adjudicator_id
    ):
        raise ValueError("utility adjudicator identity mismatch")
    chain = bind_episode_draft(
        draft,
        assignment.contract,
        arm_id=assignment.arm_id,
    )
    first = draft.windows[0]
    external_value = utility_contract.utility_measure.evaluate(
        adjudication.component_values
    )
    return TemporalDecisionUtilityArm(
        matched_pair_ref=chain.matched_pair_ref,
        arm_id=assignment.arm_id,
        authority=first.authority,
        chosen_option_family_sha256=(
            first.chosen_option_family_sha256
        ),
        chosen_option_variant_sha256=(
            first.chosen_option_variant_sha256
        ),
        continuation_policy_sha256=(
            draft.continuation_policy_sha256
        ),
        utility_measure=utility_contract.utility_measure,
        component_values=adjudication.component_values,
        primitive_action_cost=draft.primitive_action_cost,
        immediate_task_status=first.immediate_task_status,
        terminal_task_status=draft.terminal_task_status,
        external_value=external_value,
        external_outcome_ref=(
            "external-episode-adjudication:" + adjudication.sha256
        ),
    )


def total_primitive_cost(
    drafts_or_chains: Iterable[
        DecisionEpisodeDraft | DecisionEligibilityChain
    ],
) -> float:
    """Read primitive effort without consulting task value."""

    return sum(row.primitive_action_cost for row in drafts_or_chains)


__all__ = [
    "DecisionEpisodeUtilityAdjudication",
    "DecisionEpisodeDraft",
    "DecisionWindowEvidence",
    "SealedDecisionReplayContract",
    "SealedDecisionReplayAssignment",
    "SealedDecisionUtilityContract",
    "assemble_decision_episode_draft",
    "bind_episode_draft",
    "load_decision_episode_drafts",
    "materialize_episode_utility_arm",
    "record_decision_episode_draft",
    "save_decision_episode_drafts",
    "total_primitive_cost",
]
