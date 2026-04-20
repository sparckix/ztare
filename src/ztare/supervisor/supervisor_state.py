from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class SupervisorState(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B = "B"
    C = "C"
    D = "D"


class StatusReason(str, Enum):
    AWAITING_EVALUATION = "awaiting_evaluation"
    AWAITING_DRAFT = "awaiting_draft"
    AWAITING_BUILD = "awaiting_build"
    AWAITING_VERIFICATION = "awaiting_verification"
    AWAITING_HUMAN_GATE = "awaiting_human_gate"
    FAILED_CLOSED = "failed_closed"
    PROGRAM_CLOSED = "program_closed"
    PROGRAM_FROZEN = "program_frozen"


class HumanGateReason(str, Enum):
    CONTRACT_PROMOTION = "contract_promotion"
    SCOPE_MISMATCH = "scope_mismatch"
    REOPEN_CLOSED_PROGRAM = "reopen_closed_program"
    IMPLEMENTATION_TRAP = "implementation_trap"
    UNAUTHORIZED_ARTIFACT_WRITE = "unauthorized_artifact_write"
    SPEC_REFINEMENT_CAP_REACHED = "spec_refinement_cap_reached"
    SPEC_REFINEMENT_BUDGET_REACHED = "spec_refinement_budget_reached"
    STALE_REVISION_WRITE = "stale_revision_write"
    SPEC_IMPLEMENTATION_MISMATCH = "spec_implementation_mismatch"
    OUTSIDER_AUDIT_FINDING = "outsider_audit_finding"


class Actor(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    VERIFIER = "verifier"
    HUMAN = "human"
    SYSTEM = "system"


@dataclass(frozen=True)
class ArtifactPaths:
    spec: str | None = None
    implementation: tuple[str, ...] = ()
    verification_report: str | None = None
    error_report: str | None = None


@dataclass(frozen=True)
class ArtifactSnapshot:
    path: str
    sha256: str


@dataclass(frozen=True)
class TurnUsageTelemetry:
    model_name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    thinking_tokens: int = 0
    estimated_cost_usd: float = 0.0
    telemetry_captured: bool = False


@dataclass(frozen=True)
class HandoffStatus:
    run_id: str
    revision: int
    state: SupervisorState
    active_program: str
    active_target: str
    last_actor: Actor
    next_actor: Actor
    status_reason: StatusReason
    pipeline_type: str = "build"
    debate_file: str | None = None
    debate_last_turn: int | None = None
    owner_mode: str | None = None
    genesis_path: str | None = None
    seed_spec_path: str | None = None
    contract_boundary: str | None = None
    success_condition: str | None = None
    out_of_scope: tuple[str, ...] = ()
    artifact_paths: ArtifactPaths = field(default_factory=ArtifactPaths)
    spec_snapshot: tuple[ArtifactSnapshot, ...] = ()
    implementation_snapshot: tuple[ArtifactSnapshot, ...] = ()
    verification_command: str | None = None
    gate_on_verifier_pass: bool = False
    consecutive_build_failures: int = 0
    spec_refinement_rounds: int = 0
    last_turn_usage: TurnUsageTelemetry = field(default_factory=TurnUsageTelemetry)
    program_cost_usd: float = 0.0
    refinement_cost_usd: float = 0.0
    max_refinement_cost_usd: float | None = None
    human_gate_reason: HumanGateReason | None = None
    human_gate_resolved: bool = False
    closed_programs: tuple[str, ...] = ()


@dataclass(frozen=True)
class HandoffEvent:
    revision: int
    actor: Actor
    prior_state: SupervisorState
    new_state: SupervisorState
    reason: str
    timestamp: str
    artifact_paths: ArtifactPaths = field(default_factory=ArtifactPaths)
    human_gate_reason: HumanGateReason | None = None


@dataclass(frozen=True)
class DeclaredScope:
    program_id: str
    target: str


@dataclass(frozen=True)
class TransitionInput:
    actor: Actor
    expected_revision: int
    target_state: SupervisorState
    declared_scope: DeclaredScope | None = None
    touches_closed_program: bool = False
    spec_path: str | None = None
    expected_implementation_paths: tuple[str, ...] = ()
    spec_snapshot: tuple[ArtifactSnapshot, ...] = ()
    implementation_paths: tuple[str, ...] = ()
    implementation_snapshot: tuple[ArtifactSnapshot, ...] = ()
    current_implementation_snapshot: tuple[ArtifactSnapshot, ...] = ()
    spec_refinement_requested: bool = False
    gate_on_verifier_pass: bool = False
    turn_usage: TurnUsageTelemetry | None = None
    write_scope_ok: bool = True
    modified_repo_paths: tuple[str, ...] = ()
    unauthorized_repo_paths: tuple[str, ...] = ()
    verification_command: str | None = None
    verification_passed: bool | None = None
    verification_report: str | None = None
    error_report: str | None = None
    human_gate_reason: HumanGateReason | None = None
    note: str = ""


@dataclass(frozen=True)
class TransitionOutcome:
    status: HandoffStatus
    event: HandoffEvent
    fail_closed: bool = False


def _normalize_artifact_paths(payload: dict[str, Any]) -> ArtifactPaths:
    implementation = payload.get("implementation", ())
    if isinstance(implementation, list):
        implementation = tuple(str(item) for item in implementation)
    return ArtifactPaths(
        spec=payload.get("spec"),
        implementation=tuple(implementation),
        verification_report=payload.get("verification_report"),
        error_report=payload.get("error_report"),
    )


def _normalize_snapshots(items: Any) -> tuple[ArtifactSnapshot, ...]:
    if not items:
        return ()
    return tuple(
        ArtifactSnapshot(path=str(item["path"]), sha256=str(item["sha256"]))
        for item in items
    )


def _normalize_turn_usage(payload: Any) -> TurnUsageTelemetry | None:
    if payload is None:
        return None
    return TurnUsageTelemetry(
        model_name=payload.get("model_name"),
        input_tokens=int(payload.get("input_tokens", 0)),
        output_tokens=int(payload.get("output_tokens", 0)),
        cache_creation_input_tokens=int(payload.get("cache_creation_input_tokens", 0)),
        cache_read_input_tokens=int(payload.get("cache_read_input_tokens", 0)),
        estimated_cost_usd=float(payload.get("estimated_cost_usd", 0.0)),
        telemetry_captured=bool(payload.get("telemetry_captured", False)),
    )


def status_to_dict(status: HandoffStatus) -> dict[str, Any]:
    return asdict(status)


def event_to_dict(event: HandoffEvent) -> dict[str, Any]:
    return asdict(event)


def status_from_dict(payload: dict[str, Any]) -> HandoffStatus:
    return HandoffStatus(
        run_id=str(payload["run_id"]),
        revision=int(payload["revision"]),
        state=SupervisorState(str(payload["state"])),
        active_program=str(payload["active_program"]),
        active_target=str(payload["active_target"]),
        pipeline_type=str(payload.get("pipeline_type", "build")),
        debate_file=payload.get("debate_file"),
        debate_last_turn=(
            int(payload["debate_last_turn"])
            if payload.get("debate_last_turn") is not None
            else None
        ),
        owner_mode=payload.get("owner_mode"),
        genesis_path=payload.get("genesis_path"),
        seed_spec_path=payload.get("seed_spec_path"),
        contract_boundary=payload.get("contract_boundary"),
        success_condition=payload.get("success_condition"),
        out_of_scope=tuple(str(item) for item in payload.get("out_of_scope", ())),
        last_actor=Actor(str(payload["last_actor"])),
        next_actor=Actor(str(payload["next_actor"])),
        status_reason=StatusReason(str(payload["status_reason"])),
        artifact_paths=_normalize_artifact_paths(payload.get("artifact_paths", {})),
        spec_snapshot=_normalize_snapshots(payload.get("spec_snapshot")),
        implementation_snapshot=_normalize_snapshots(payload.get("implementation_snapshot")),
        verification_command=payload.get("verification_command"),
        gate_on_verifier_pass=bool(payload.get("gate_on_verifier_pass", False)),
        consecutive_build_failures=int(payload.get("consecutive_build_failures", 0)),
        spec_refinement_rounds=int(payload.get("spec_refinement_rounds", 0)),
        last_turn_usage=_normalize_turn_usage(payload.get("last_turn_usage")) or TurnUsageTelemetry(),
        program_cost_usd=float(payload.get("program_cost_usd", 0.0)),
        refinement_cost_usd=float(payload.get("refinement_cost_usd", 0.0)),
        max_refinement_cost_usd=(
            float(payload["max_refinement_cost_usd"])
            if payload.get("max_refinement_cost_usd") is not None
            else None
        ),
        human_gate_reason=(
            HumanGateReason(str(payload["human_gate_reason"]))
            if payload.get("human_gate_reason") is not None
            else None
        ),
        human_gate_resolved=bool(payload.get("human_gate_resolved", False)),
        closed_programs=tuple(str(item) for item in payload.get("closed_programs", ())),
    )


def transition_input_from_dict(payload: dict[str, Any]) -> TransitionInput:
    declared_scope_payload = payload.get("declared_scope")
    return TransitionInput(
        actor=Actor(str(payload["actor"])),
        expected_revision=int(payload["expected_revision"]),
        target_state=SupervisorState(str(payload["target_state"])),
        declared_scope=(
            DeclaredScope(
                program_id=str(declared_scope_payload["program_id"]),
                target=str(declared_scope_payload["target"]),
            )
            if declared_scope_payload is not None
            else None
        ),
        touches_closed_program=bool(payload.get("touches_closed_program", False)),
        spec_path=payload.get("spec_path"),
        expected_implementation_paths=tuple(
            str(item) for item in payload.get("expected_implementation_paths", ())
        ),
        spec_snapshot=_normalize_snapshots(payload.get("spec_snapshot")),
        implementation_paths=tuple(
            str(item) for item in payload.get("implementation_paths", ())
        ),
        implementation_snapshot=_normalize_snapshots(payload.get("implementation_snapshot")),
        current_implementation_snapshot=_normalize_snapshots(
            payload.get("current_implementation_snapshot")
        ),
        spec_refinement_requested=bool(payload.get("spec_refinement_requested", False)),
        gate_on_verifier_pass=bool(payload.get("gate_on_verifier_pass", False)),
        turn_usage=_normalize_turn_usage(payload.get("turn_usage")),
        write_scope_ok=bool(payload.get("write_scope_ok", True)),
        modified_repo_paths=tuple(str(item) for item in payload.get("modified_repo_paths", ())),
        unauthorized_repo_paths=tuple(
            str(item) for item in payload.get("unauthorized_repo_paths", ())
        ),
        verification_command=payload.get("verification_command"),
        verification_passed=payload.get("verification_passed"),
        verification_report=payload.get("verification_report"),
        error_report=payload.get("error_report"),
        human_gate_reason=(
            HumanGateReason(str(payload["human_gate_reason"]))
            if payload.get("human_gate_reason") is not None
            else None
        ),
        note=str(payload.get("note", "")),
    )
