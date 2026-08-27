"""Typed strategic states, actions, transition traces, and observed relations."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.partial_action_system import (
    PartialActionObservation,
    PartialActionSystem,
    build_partial_action_system,
)


def _identity(value: str, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be nonempty")
    return text


def _coordinates(
    values: Mapping[str, float] | Iterable[tuple[str, float]],
    label: str,
) -> tuple[tuple[str, float], ...]:
    rows = values.items() if isinstance(values, Mapping) else values
    normalized: dict[str, float] = {}
    for raw_name, raw_value in rows:
        name = _identity(raw_name, f"{label} coordinate")
        if isinstance(raw_value, bool):
            raise ValueError(f"{label}.{name} must be numeric")
        value = float(raw_value)
        if not math.isfinite(value):
            raise ValueError(f"{label}.{name} must be finite")
        if name in normalized:
            raise ValueError(f"duplicate {label} coordinate: {name}")
        normalized[name] = value
    return tuple(sorted(normalized.items()))


@dataclass(frozen=True, slots=True)
class StrategicActorState:
    actor_id: str
    variables: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", _identity(self.actor_id, "actor_id"))
        object.__setattr__(
            self,
            "variables",
            _coordinates(self.variables, f"actor.{self.actor_id}"),
        )

    @classmethod
    def from_mapping(
        cls,
        actor_id: str,
        values: Mapping[str, float],
    ) -> "StrategicActorState":
        return cls(actor_id, tuple(values.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "variables": dict(self.variables),
        }


@dataclass(frozen=True, slots=True)
class StrategicState:
    decision_id: str
    epoch: int
    firm: tuple[tuple[str, float], ...]
    actors: tuple[StrategicActorState, ...] = ()
    context: tuple[tuple[str, str], ...] = ()
    state_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_id",
            _identity(self.decision_id, "decision_id"),
        )
        if isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("strategic state epoch must be nonnegative")
        object.__setattr__(self, "firm", _coordinates(self.firm, "firm"))
        actors = tuple(sorted(self.actors, key=lambda actor: actor.actor_id))
        if len({actor.actor_id for actor in actors}) != len(actors):
            raise ValueError("strategic actor identities must be unique")
        object.__setattr__(self, "actors", actors)
        context = tuple(sorted(
            (
                _identity(name, "context name"),
                _identity(value, f"context.{name}"),
            )
            for name, value in self.context
        ))
        if len({name for name, _value in context}) != len(context):
            raise ValueError("strategic context coordinates must be unique")
        object.__setattr__(self, "context", context)
        payload = self._identity_payload()
        object.__setattr__(self, "state_sha256", stable_sha256(payload))

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-strategic-state-v1",
            "decision_id": self.decision_id,
            "epoch": self.epoch,
            "firm": dict(self.firm),
            "actors": [actor.to_dict() for actor in self.actors],
            "context": dict(self.context),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "state_sha256": self.state_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "StrategicState":
        actors = tuple(
            StrategicActorState.from_mapping(
                str(row.get("id") or row.get("actor_id") or ""),
                dict(row.get("variables") or {}),
            )
            for row in payload.get("actors", [])
        )
        return cls(
            decision_id=str(payload["decision_id"]),
            epoch=int(payload["epoch"]),
            firm=tuple(dict(payload.get("firm") or {}).items()),
            actors=actors,
            context=tuple(
                (str(name), str(value))
                for name, value in dict(payload.get("context") or {}).items()
            ),
        )

    @property
    def paths(self) -> tuple[str, ...]:
        actor_paths = tuple(
            f"actor.{actor.actor_id}.{name}"
            for actor in self.actors
            for name, _value in actor.variables
        )
        return tuple(f"firm.{name}" for name, _value in self.firm) + actor_paths

    def value(self, path: str) -> float:
        parts = path.split(".")
        if len(parts) == 2 and parts[0] == "firm":
            values = dict(self.firm)
            if parts[1] not in values:
                raise KeyError(f"unknown state path: {path}")
            return values[parts[1]]
        if len(parts) == 3 and parts[0] == "actor":
            actor = next(
                (row for row in self.actors if row.actor_id == parts[1]),
                None,
            )
            if actor is None or parts[2] not in dict(actor.variables):
                raise KeyError(f"unknown state path: {path}")
            return dict(actor.variables)[parts[2]]
        raise KeyError(f"invalid state path: {path}")

    def advance(
        self,
        deltas: Mapping[str, float],
        *,
        context_updates: Mapping[str, str] | None = None,
    ) -> "StrategicState":
        firm = dict(self.firm)
        actors = {
            actor.actor_id: dict(actor.variables) for actor in self.actors
        }
        for path, raw_delta in deltas.items():
            delta = float(raw_delta)
            if not math.isfinite(delta):
                raise ValueError(f"state delta must be finite: {path}")
            parts = path.split(".")
            if len(parts) == 2 and parts[0] == "firm" and parts[1] in firm:
                firm[parts[1]] += delta
                continue
            if (
                len(parts) == 3
                and parts[0] == "actor"
                and parts[1] in actors
                and parts[2] in actors[parts[1]]
            ):
                actors[parts[1]][parts[2]] += delta
                continue
            raise KeyError(f"effect references unknown state path: {path}")
        context = dict(self.context)
        context.update(context_updates or {})
        return StrategicState(
            decision_id=self.decision_id,
            epoch=self.epoch + 1,
            firm=tuple(firm.items()),
            actors=tuple(
                StrategicActorState.from_mapping(actor_id, values)
                for actor_id, values in actors.items()
            ),
            context=tuple(context.items()),
        )


@dataclass(frozen=True, slots=True)
class StrategicAction:
    action_id: str
    description: str
    primitive_cost: float
    irreversibility: float
    authority_tier: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", _identity(self.action_id, "action_id"))
        object.__setattr__(
            self,
            "description",
            _identity(self.description, "action description"),
        )
        for label, value in (
            ("primitive_cost", self.primitive_cost),
            ("irreversibility", self.irreversibility),
        ):
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"action {label} must be finite and nonnegative")
            object.__setattr__(self, label, number)
        object.__setattr__(
            self,
            "authority_tier",
            _identity(self.authority_tier, "authority_tier"),
        )
        refs = tuple(sorted({
            _identity(ref, "action evidence ref")
            for ref in self.evidence_refs
        }))
        if not refs:
            raise ValueError("strategic actions require evidence refs")
        object.__setattr__(self, "evidence_refs", refs)

    @property
    def action_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "description": self.description,
            "primitive_cost": self.primitive_cost,
            "irreversibility": self.irreversibility,
            "authority_tier": self.authority_tier,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class StrategicTransition:
    transition_id: str
    source: StrategicState
    action_id: str
    target: StrategicState | None
    occurred_at: str
    evidence_refs: tuple[str, ...]
    boundary_kind: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_id",
            _identity(self.transition_id, "transition_id"),
        )
        object.__setattr__(self, "action_id", _identity(self.action_id, "action_id"))
        object.__setattr__(
            self,
            "occurred_at",
            _identity(self.occurred_at, "occurred_at"),
        )
        refs = tuple(sorted({
            _identity(ref, "transition evidence ref")
            for ref in self.evidence_refs
        }))
        if not refs:
            raise ValueError("strategic transitions require evidence refs")
        object.__setattr__(self, "evidence_refs", refs)
        boundary = str(self.boundary_kind or "").strip()
        if self.target is None and not boundary:
            raise ValueError("a missing transition target requires boundary_kind")
        if self.target is not None:
            if self.target.decision_id != self.source.decision_id:
                raise ValueError("strategic transition crossed decision identity")
            if self.target.epoch <= self.source.epoch:
                raise ValueError("strategic transition target must advance epoch")
            if self.target.paths != self.source.paths:
                raise ValueError("strategic transition changed state coordinate schema")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "source": self.source.to_dict(),
            "action_id": self.action_id,
            "target": self.target.to_dict() if self.target is not None else None,
            "occurred_at": self.occurred_at,
            "evidence_refs": list(self.evidence_refs),
            "boundary_kind": self.boundary_kind,
        }


@dataclass(frozen=True, slots=True)
class StrategicTraceSet:
    trace_set_id: str
    transitions: tuple[StrategicTransition, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "trace_set_id",
            _identity(self.trace_set_id, "trace_set_id"),
        )
        if len({row.transition_id for row in self.transitions}) != len(self.transitions):
            raise ValueError("strategic transition identities must be unique")

    @property
    def trace_sha256(self) -> str:
        return stable_sha256({
            "schema": "jaggedthoughts-strategic-trace-set-v1",
            "trace_set_id": self.trace_set_id,
            "transitions": [row.to_dict() for row in self.transitions],
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-strategic-trace-set-v1",
            "trace_set_id": self.trace_set_id,
            "trace_sha256": self.trace_sha256,
            "transitions": [row.to_dict() for row in self.transitions],
        }


def _state_key(state: StrategicState) -> tuple[Any, ...]:
    return (
        state.decision_id,
        state.epoch,
        state.firm,
        tuple((actor.actor_id, actor.variables) for actor in state.actors),
        state.context,
    )


def _transition_effect(
    source: StrategicState,
    _action: str,
    target: StrategicState,
    _source_key: Any,
    _target_key: Any,
) -> tuple[tuple[str, float], ...]:
    return tuple(
        (path, target.value(path) - source.value(path))
        for path in source.paths
    )


def compile_observed_action_system(
    traces: StrategicTraceSet,
) -> PartialActionSystem:
    """Lower strategic traces into the shared witnessed partial-action kernel."""
    observations = tuple(
        PartialActionObservation(
            source=row.source,
            operation=row.action_id,
            successor=row.target,
            evidence_ref=row.evidence_refs[0],
            boundary_kind=row.boundary_kind,
            context={"transition_id": row.transition_id},
        )
        for row in traces.transitions
    )
    return build_partial_action_system(
        observations,
        project=_state_key,
        effect=_transition_effect,
        projection_id=f"{traces.trace_set_id}@{traces.trace_sha256}",
    )


__all__ = [
    "StrategicAction",
    "StrategicActorState",
    "StrategicState",
    "StrategicTraceSet",
    "StrategicTransition",
    "compile_observed_action_system",
]
