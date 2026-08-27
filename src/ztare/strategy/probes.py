"""Guarded strategic probes and scoped, registered evidence adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    GuardedProtocolSelection,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    select_guarded_protocol,
)

from .mechanisms import MechanismVersionSpace, predict_transition
from .transitions import StrategicAction, StrategicState, StrategicTransition


@dataclass(frozen=True, slots=True)
class ProbeAuthority:
    authority_id: str
    allowed_adapters: tuple[str, ...]
    allowed_action_tiers: tuple[str, ...]
    max_primitive_execution_units: float
    max_irreversibility_units: float

    def __post_init__(self) -> None:
        if not self.authority_id.strip():
            raise ValueError("probe authority requires identity")
        if not self.allowed_adapters or not self.allowed_action_tiers:
            raise ValueError("probe authority requires adapter and tier allowlists")
        for value in (
            self.max_primitive_execution_units,
            self.max_irreversibility_units,
        ):
            if not math.isfinite(float(value)) or value < 0:
                raise ValueError("probe authority bounds must be nonnegative")

    @property
    def authority_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "allowed_adapters": list(self.allowed_adapters),
            "allowed_action_tiers": list(self.allowed_action_tiers),
            "max_primitive_execution_units": self.max_primitive_execution_units,
            "max_irreversibility_units": self.max_irreversibility_units,
        }


@dataclass(frozen=True, slots=True)
class StrategicProbe:
    probe_id: str
    start_state: StrategicState
    action: StrategicAction
    response_paths: tuple[str, ...]
    adapter_id: str
    adapter_config: tuple[tuple[str, str], ...]
    cost: ProtocolCost
    evidence_refs: tuple[str, ...]
    novel_context: bool = False

    def __post_init__(self) -> None:
        if not self.probe_id.strip() or not self.adapter_id.strip():
            raise ValueError("strategic probes require probe and adapter identity")
        if not self.response_paths:
            raise ValueError("strategic probes require response paths")
        for path in self.response_paths:
            self.start_state.value(path)
        if not self.evidence_refs:
            raise ValueError("strategic probes require evidence refs")
        if self.cost.probe_execution_units < self.action.primitive_cost:
            raise ValueError("probe cost understates its strategic action cost")
        if self.cost.irreversibility_units < self.action.irreversibility:
            raise ValueError("probe cost understates action irreversibility")

    @property
    def probe_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "start_state_sha256": self.start_state.state_sha256,
            "action_id": self.action.action_id,
            "response_paths": list(self.response_paths),
            "adapter_id": self.adapter_id,
            "adapter_config": dict(self.adapter_config),
            "cost": self.cost.to_receipt(),
            "evidence_refs": list(self.evidence_refs),
            "novel_context": self.novel_context,
        }


@dataclass(frozen=True, slots=True)
class StrategicProbeAgenda:
    selection: GuardedProtocolSelection
    probes: tuple[StrategicProbe, ...]
    authority: ProbeAuthority

    @property
    def selected_probe(self) -> StrategicProbe | None:
        selected_id = self.selection.selected_protocol_id
        return next(
            (probe for probe in self.probes if probe.probe_id == selected_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-strategic-probe-agenda-v1",
            "authority": {
                **self.authority.to_dict(),
                "authority_sha256": self.authority.authority_sha256,
            },
            "probes": [probe.to_dict() for probe in self.probes],
            "selection": self.selection.to_receipt(),
        }


def _response(
    probe: StrategicProbe,
    state: StrategicState,
) -> tuple[tuple[str, float], ...]:
    return tuple((path, state.value(path)) for path in probe.response_paths)


def compile_probe_agenda(
    probes: Iterable[StrategicProbe],
    *,
    version_space: MechanismVersionSpace,
    authority: ProbeAuthority,
    weights: ProtocolYieldWeights | None = None,
) -> StrategicProbeAgenda:
    """Price admitted probes against predictions of every surviving model."""
    rows = tuple(sorted(probes, key=lambda row: row.probe_id))
    candidates = []
    for probe in rows:
        admitted = True
        reasons = []
        if probe.adapter_id not in authority.allowed_adapters:
            admitted = False
            reasons.append("adapter_not_authorized")
        if probe.action.authority_tier not in authority.allowed_action_tiers:
            admitted = False
            reasons.append("action_tier_not_authorized")
        if probe.cost.irreversibility_units > authority.max_irreversibility_units:
            admitted = False
            reasons.append("irreversibility_bound_exceeded")
        committee = tuple(
            ProtocolResponseHypothesis(
                hypothesis_id=model.mechanism_id,
                response=_response(
                    probe,
                    predict_transition(
                        model,
                        probe.start_state,
                        probe.action.action_id,
                    ),
                ),
                description_units=model.description_units,
                evidence_refs=model.evidence_refs,
            )
            for model in version_space.survivors
        )
        if len({member.response for member in committee}) <= 1:
            admitted = False
            reasons.append("no_model_disagreement")
        protocol = GuardedExperimentProtocol(
            protocol_id=probe.probe_id,
            preparation=(probe.start_state.state_sha256,),
            probe=(probe.action.action_id, probe.response_paths),
            target_key=probe.start_state.decision_id,
            cost=probe.cost,
            novel_context=probe.novel_context,
            guard_admitted=admitted,
            guard_reason=",".join(reasons),
            evidence_refs=probe.evidence_refs,
        )
        candidates.append(GuardedProtocolCandidate(protocol, committee))
    selection = select_guarded_protocol(
        candidates,
        weights=weights or ProtocolYieldWeights(1.0, 0.25, 0.1),
        max_primitive_execution_units=(
            authority.max_primitive_execution_units
        ),
    )
    return StrategicProbeAgenda(selection, rows, authority)


@dataclass(frozen=True, slots=True)
class ProbeExecutionReceipt:
    probe_id: str
    adapter_id: str
    authority_sha256: str
    status: str
    observed_transition: StrategicTransition | None
    observation_sha256: str
    executed_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "jaggedthoughts-probe-execution-v1",
            "probe_id": self.probe_id,
            "adapter_id": self.adapter_id,
            "authority_sha256": self.authority_sha256,
            "status": self.status,
            "observed_transition": (
                self.observed_transition.to_dict()
                if self.observed_transition is not None
                else None
            ),
            "observation_sha256": self.observation_sha256,
            "executed_at": self.executed_at,
        }
        return {**payload, "receipt_sha256": stable_sha256(payload)}


ProbeAdapter = Callable[
    [StrategicProbe, ProbeAuthority, Path],
    ProbeExecutionReceipt,
]


class ProbeAdapterRegistry:
    """Explicit adapter allowlist; no profile can inject executable code."""

    def __init__(self) -> None:
        self._adapters: dict[str, ProbeAdapter] = {}

    def register(self, adapter_id: str, adapter: ProbeAdapter) -> None:
        if not adapter_id.strip() or adapter_id in self._adapters:
            raise ValueError(f"invalid or duplicate probe adapter: {adapter_id}")
        self._adapters[adapter_id] = adapter

    def execute(
        self,
        probe: StrategicProbe,
        *,
        authority: ProbeAuthority,
        adapter_root: Path,
    ) -> ProbeExecutionReceipt:
        if probe.adapter_id not in authority.allowed_adapters:
            raise PermissionError("probe adapter is outside execution authority")
        if probe.action.authority_tier not in authority.allowed_action_tiers:
            raise PermissionError("probe action tier is outside execution authority")
        if (
            probe.cost.primitive_execution_units
            > authority.max_primitive_execution_units
        ):
            raise PermissionError("probe cost exceeds execution authority")
        if (
            probe.cost.irreversibility_units
            > authority.max_irreversibility_units
        ):
            raise PermissionError("probe irreversibility exceeds execution authority")
        adapter = self._adapters.get(probe.adapter_id)
        if adapter is None:
            raise ValueError(f"unregistered probe adapter: {probe.adapter_id}")
        return adapter(probe, authority, adapter_root)


def _scoped_file(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ValueError("probe observation paths must be relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("probe observation path escapes adapter root") from error
    return resolved


def execute_file_transition_probe(
    probe: StrategicProbe,
    authority: ProbeAuthority,
    adapter_root: Path,
) -> ProbeExecutionReceipt:
    """Read a bounded transition observation produced outside this process."""
    config = dict(probe.adapter_config)
    path = _scoped_file(adapter_root, config.get("observation_path", ""))
    now = datetime.now(timezone.utc).isoformat()
    if not path.is_file():
        return ProbeExecutionReceipt(
            probe_id=probe.probe_id,
            adapter_id=probe.adapter_id,
            authority_sha256=authority.authority_sha256,
            status="observation_pending",
            observed_transition=None,
            observation_sha256="",
            executed_at=now,
        )
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if str(payload.get("probe_id")) != probe.probe_id:
        raise ValueError("probe observation crossed probe identity")
    if str(payload.get("action_id")) != probe.action.action_id:
        raise ValueError("probe observation crossed action identity")
    if str(payload.get("source_state_sha256")) != probe.start_state.state_sha256:
        raise ValueError("probe observation crossed source-state identity")
    target = StrategicState.from_mapping(dict(payload["target"]))
    transition = StrategicTransition(
        transition_id=f"probe::{probe.probe_id}::{stable_sha256(raw)}",
        source=probe.start_state,
        action_id=probe.action.action_id,
        target=target,
        occurred_at=str(payload["observed_at"]),
        evidence_refs=(f"observation:{path.name}@sha256:{stable_sha256(raw)}",),
    )
    return ProbeExecutionReceipt(
        probe_id=probe.probe_id,
        adapter_id=probe.adapter_id,
        authority_sha256=authority.authority_sha256,
        status="observed",
        observed_transition=transition,
        observation_sha256=stable_sha256(raw),
        executed_at=now,
    )


def default_probe_adapter_registry() -> ProbeAdapterRegistry:
    registry = ProbeAdapterRegistry()
    registry.register("file_transition", execute_file_transition_probe)
    return registry


__all__ = [
    "ProbeAdapterRegistry",
    "ProbeAuthority",
    "ProbeExecutionReceipt",
    "StrategicProbe",
    "StrategicProbeAgenda",
    "compile_probe_agenda",
    "default_probe_adapter_registry",
    "execute_file_transition_probe",
]
