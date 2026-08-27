"""Executable strategic mechanism programs and evidence-pruned version spaces."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Literal, Mapping

from ztare.common.equivariance import stable_sha256

from .transitions import StrategicState, StrategicTraceSet, StrategicTransition


ConditionOperator = Literal["eq", "ne", "gt", "ge", "lt", "le"]
RulePhase = Literal["primary", "actor_response"]


def _text(value: str, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be nonempty")
    return result


@dataclass(frozen=True, slots=True)
class StateCondition:
    path: str
    operator: ConditionOperator
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _text(self.path, "condition path"))
        if self.operator not in {"eq", "ne", "gt", "ge", "lt", "le"}:
            raise ValueError(f"unsupported condition operator: {self.operator}")
        number = float(self.value)
        if not math.isfinite(number):
            raise ValueError("condition value must be finite")
        object.__setattr__(self, "value", number)

    def matches(self, state: StrategicState) -> bool:
        observed = state.value(self.path)
        return {
            "eq": observed == self.value,
            "ne": observed != self.value,
            "gt": observed > self.value,
            "ge": observed >= self.value,
            "lt": observed < self.value,
            "le": observed <= self.value,
        }[self.operator]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class MechanismEffect:
    path: str
    delta: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _text(self.path, "effect path"))
        value = float(self.delta)
        if not math.isfinite(value):
            raise ValueError("mechanism effect delta must be finite")
        object.__setattr__(self, "delta", value)

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "delta": self.delta}


@dataclass(frozen=True, slots=True)
class MechanismRule:
    rule_id: str
    phase: RulePhase
    action_ids: tuple[str, ...]
    conditions: tuple[StateCondition, ...]
    effects: tuple[MechanismEffect, ...]
    evidence_refs: tuple[str, ...]
    actor_id: str = ""
    priority: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _text(self.rule_id, "rule_id"))
        if self.phase not in {"primary", "actor_response"}:
            raise ValueError(f"unsupported rule phase: {self.phase}")
        actions = tuple(sorted({_text(value, "rule action") for value in self.action_ids}))
        if not actions:
            raise ValueError("mechanism rules require action identities")
        object.__setattr__(self, "action_ids", actions)
        if not self.effects:
            raise ValueError("mechanism rules require effects")
        paths = [effect.path for effect in self.effects]
        if len(paths) != len(set(paths)):
            raise ValueError("one mechanism rule cannot repeat an effect path")
        refs = tuple(sorted({_text(value, "rule evidence ref") for value in self.evidence_refs}))
        if not refs:
            raise ValueError("mechanism rules require evidence refs")
        object.__setattr__(self, "evidence_refs", refs)
        actor = str(self.actor_id or "").strip()
        if self.phase == "actor_response" and not actor:
            raise ValueError("actor-response rules require actor_id")
        if self.phase == "primary" and actor:
            raise ValueError("primary rules cannot claim actor ownership")
        object.__setattr__(self, "actor_id", actor)
        if isinstance(self.priority, bool):
            raise ValueError("mechanism rule priority must be an integer")

    def matches(self, state: StrategicState, action_id: str) -> bool:
        return action_id in self.action_ids and all(
            condition.matches(state) for condition in self.conditions
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "phase": self.phase,
            "action_ids": list(self.action_ids),
            "actor_id": self.actor_id,
            "priority": self.priority,
            "conditions": [condition.to_dict() for condition in self.conditions],
            "effects": [effect.to_dict() for effect in self.effects],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class StrategicMechanism:
    mechanism_id: str
    description: str
    description_units: int
    rules: tuple[MechanismRule, ...]
    evidence_refs: tuple[str, ...]
    mechanism_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mechanism_id",
            _text(self.mechanism_id, "mechanism_id"),
        )
        object.__setattr__(
            self,
            "description",
            _text(self.description, "mechanism description"),
        )
        if isinstance(self.description_units, bool) or self.description_units <= 0:
            raise ValueError("mechanism description_units must be positive")
        if not self.rules:
            raise ValueError("strategic mechanisms require rules")
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("mechanism rule identities must be unique")
        refs = tuple(sorted({
            _text(value, "mechanism evidence ref")
            for value in self.evidence_refs
        }))
        if not refs:
            raise ValueError("strategic mechanisms require evidence refs")
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "mechanism_sha256", stable_sha256(self._payload()))

    @property
    def has_endogenous_response(self) -> bool:
        return any(rule.phase == "actor_response" for rule in self.rules)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-strategic-mechanism-v1",
            "mechanism_id": self.mechanism_id,
            "description": self.description,
            "description_units": self.description_units,
            "rules": [rule.to_dict() for rule in self.rules],
            "evidence_refs": list(self.evidence_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "mechanism_sha256": self.mechanism_sha256}


def _effect_sum(rules: Iterable[MechanismRule]) -> dict[str, float]:
    result: dict[str, float] = {}
    for rule in rules:
        for effect in rule.effects:
            result[effect.path] = result.get(effect.path, 0.0) + effect.delta
    return result


def predict_transition(
    mechanism: StrategicMechanism,
    state: StrategicState,
    action_id: str,
) -> StrategicState:
    """Execute primary effects, then actor responses against the intermediate state."""
    primary = tuple(sorted(
        (
            rule
            for rule in mechanism.rules
            if rule.phase == "primary" and rule.matches(state, action_id)
        ),
        key=lambda rule: (rule.priority, rule.rule_id),
    ))
    intermediate = state.advance(_effect_sum(primary))
    responses = tuple(sorted(
        (
            rule
            for rule in mechanism.rules
            if rule.phase == "actor_response"
            and rule.matches(intermediate, action_id)
        ),
        key=lambda rule: (rule.priority, rule.actor_id, rule.rule_id),
    ))
    if not responses:
        return intermediate
    response_effects = _effect_sum(responses)
    final = intermediate.advance(response_effects)
    return StrategicState(
        decision_id=final.decision_id,
        epoch=state.epoch + 1,
        firm=final.firm,
        actors=final.actors,
        context=final.context,
    )


@dataclass(frozen=True, slots=True)
class TransitionReplay:
    transition_id: str
    predicted_state_sha256: str
    target_state_sha256: str
    absolute_errors: tuple[tuple[str, float], ...]
    within_tolerance: bool

    @property
    def mean_absolute_error(self) -> float:
        return (
            sum(value for _path, value in self.absolute_errors)
            / len(self.absolute_errors)
            if self.absolute_errors
            else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "predicted_state_sha256": self.predicted_state_sha256,
            "target_state_sha256": self.target_state_sha256,
            "absolute_errors": dict(self.absolute_errors),
            "mean_absolute_error": self.mean_absolute_error,
            "within_tolerance": self.within_tolerance,
        }


@dataclass(frozen=True, slots=True)
class MechanismVerdict:
    mechanism_id: str
    mechanism_sha256: str
    status: str
    replay_mean_absolute_error: float
    replay_max_absolute_error: float
    replays: tuple[TransitionReplay, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "mechanism_sha256": self.mechanism_sha256,
            "status": self.status,
            "replay_mean_absolute_error": self.replay_mean_absolute_error,
            "replay_max_absolute_error": self.replay_max_absolute_error,
            "replays": [row.to_dict() for row in self.replays],
        }


@dataclass(frozen=True, slots=True)
class MechanismVersionSpace:
    trace_sha256: str
    tolerance_by_path: tuple[tuple[str, float], ...]
    mechanisms: tuple[StrategicMechanism, ...]
    verdicts: tuple[MechanismVerdict, ...]
    survivor_ids: tuple[str, ...]
    version_space_sha256: str

    @property
    def survivors(self) -> tuple[StrategicMechanism, ...]:
        survivor_set = set(self.survivor_ids)
        return tuple(
            model for model in self.mechanisms if model.mechanism_id in survivor_set
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-mechanism-version-space-v1",
            "trace_sha256": self.trace_sha256,
            "tolerance_by_path": dict(self.tolerance_by_path),
            "mechanisms": [model.to_dict() for model in self.mechanisms],
            "verdicts": [verdict.to_dict() for verdict in self.verdicts],
            "survivor_ids": list(self.survivor_ids),
            "version_space_sha256": self.version_space_sha256,
        }


def _replay_transition(
    mechanism: StrategicMechanism,
    transition: StrategicTransition,
    tolerances: Mapping[str, float],
) -> TransitionReplay | None:
    if transition.target is None:
        return None
    predicted = predict_transition(
        mechanism,
        transition.source,
        transition.action_id,
    )
    errors = tuple(
        (
            path,
            abs(predicted.value(path) - transition.target.value(path)),
        )
        for path in transition.source.paths
    )
    return TransitionReplay(
        transition_id=transition.transition_id,
        predicted_state_sha256=predicted.state_sha256,
        target_state_sha256=transition.target.state_sha256,
        absolute_errors=errors,
        within_tolerance=all(
            error <= float(tolerances.get(path, 0.0))
            for path, error in errors
        ),
    )


def compile_mechanism_version_space(
    mechanisms: Iterable[StrategicMechanism],
    traces: StrategicTraceSet,
    *,
    tolerance_by_path: Mapping[str, float] | None = None,
) -> MechanismVersionSpace:
    """Replay every mechanism and retain all models consistent with evidence."""
    models = tuple(sorted(mechanisms, key=lambda model: model.mechanism_id))
    if not models:
        raise ValueError("mechanism version space requires candidates")
    if len({model.mechanism_id for model in models}) != len(models):
        raise ValueError("mechanism candidate identities must be unique")
    tolerances = {
        str(path): float(value)
        for path, value in (tolerance_by_path or {}).items()
    }
    if any(
        not math.isfinite(value) or value < 0
        for value in tolerances.values()
    ):
        raise ValueError("mechanism replay tolerances must be finite and nonnegative")
    verdicts: list[MechanismVerdict] = []
    for mechanism in models:
        replays = tuple(
            replay
            for transition in traces.transitions
            if (
                replay := _replay_transition(
                    mechanism,
                    transition,
                    tolerances,
                )
            )
            is not None
        )
        errors = tuple(
            error
            for replay in replays
            for _path, error in replay.absolute_errors
        )
        verdicts.append(MechanismVerdict(
            mechanism_id=mechanism.mechanism_id,
            mechanism_sha256=mechanism.mechanism_sha256,
            status=(
                "survives"
                if replays and all(replay.within_tolerance for replay in replays)
                else "unscored"
                if not replays
                else "refuted"
            ),
            replay_mean_absolute_error=(sum(errors) / len(errors) if errors else 0.0),
            replay_max_absolute_error=max(errors, default=0.0),
            replays=replays,
        ))
    survivor_ids = tuple(
        verdict.mechanism_id
        for verdict in verdicts
        if verdict.status in {"survives", "unscored"}
    )
    payload = {
        "schema": "jaggedthoughts-mechanism-version-space-v1",
        "trace_sha256": traces.trace_sha256,
        "tolerance_by_path": dict(sorted(tolerances.items())),
        "mechanism_sha256s": [model.mechanism_sha256 for model in models],
        "verdicts": [verdict.to_dict() for verdict in verdicts],
        "survivor_ids": list(survivor_ids),
    }
    return MechanismVersionSpace(
        trace_sha256=traces.trace_sha256,
        tolerance_by_path=tuple(sorted(tolerances.items())),
        mechanisms=models,
        verdicts=tuple(verdicts),
        survivor_ids=survivor_ids,
        version_space_sha256=stable_sha256(payload),
    )


__all__ = [
    "MechanismEffect",
    "MechanismRule",
    "MechanismVerdict",
    "MechanismVersionSpace",
    "StateCondition",
    "StrategicMechanism",
    "TransitionReplay",
    "compile_mechanism_version_space",
    "predict_transition",
]
