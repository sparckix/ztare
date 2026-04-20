from __future__ import annotations

from dataclasses import asdict
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field
from anthropic import Anthropic

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_manifest import (
    derive_packet_read_bundle,
    load_optional_program_manifest,
    next_manifest_packet,
    packet_for_target,
)
from src.ztare.supervisor.supervisor_pipeline import (
    default_research_draft_path,
    default_research_spec_path,
    default_research_verification_command,
)
from src.ztare.supervisor.supervisor_state import (
    Actor,
    HandoffStatus,
    SupervisorState,
    TurnUsageTelemetry,
    status_to_dict,
)
from src.ztare.supervisor.supervisor_usage import estimate_cost_usd
from src.ztare.supervisor.supervisor_usage import extract_usage_telemetry


class WrapperMode(str, Enum):
    EXTERNAL_AGENT = "external_agent"
    LOCAL_VERIFIER = "local_verifier"


class WrapperTransport(str, Enum):
    CLI = "cli"
    OPENAI_API = "openai_api"


@dataclass(frozen=True)
class AgentWrapperConfig:
    actor: Actor
    mode: WrapperMode
    command: tuple[str, ...]
    model_name: str | None = None
    enforce_read_allowlist: bool = False
    research_b_api_model_name: str | None = None
    research_a2_max_output_tokens: int | None = None
    research_a2_api_model_name: str | None = None
    research_a1_prompt_version: str | None = None
    research_a2_prompt_version: str | None = None
    research_b_prompt_version: str | None = None


@dataclass(frozen=True)
class WrapperLaunchResult:
    actor: Actor
    mode: WrapperMode
    executed: bool
    command: tuple[str, ...]
    prompt_path: str | None
    debug_path: str | None
    stdout_path: str | None
    stderr_path: str | None
    report_path: str | None
    usage_path: str | None
    modified_repo_paths: tuple[str, ...] = ()
    unauthorized_repo_paths: tuple[str, ...] = ()
    read_allowlist_paths: tuple[str, ...] = ()
    sandbox_root: str | None = None
    output_envelope_exceeded: bool = False
    output_envelope_limit: int | None = None
    estimated_output_tokens_emitted: int | None = None
    turn_usage: TurnUsageTelemetry | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class AgentInvocationResult:
    executed: bool
    command: tuple[str, ...]
    prompt_path: str
    debug_path: str
    stdout_path: str
    stderr_path: str
    usage_path: str
    modified_repo_paths: tuple[str, ...] = ()
    unauthorized_repo_paths: tuple[str, ...] = ()
    read_allowlist_paths: tuple[str, ...] = ()
    sandbox_root: str | None = None
    output_envelope_exceeded: bool = False
    output_envelope_limit: int | None = None
    estimated_output_tokens_emitted: int | None = None
    turn_usage: TurnUsageTelemetry | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class ProcessExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    output_envelope_exceeded: bool = False
    estimated_output_tokens_emitted: int | None = None


@dataclass(frozen=True)
class APITransportResult:
    request_payload: dict[str, Any]
    artifacts: tuple[tuple[str, str, str], ...]
    turn_usage: TurnUsageTelemetry
    raw_response_text: str


class APIArtifactWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str
    operation: str = "replace"


class APIA1ArtifactWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str
    operation: Literal["append"] = "append"


class APIDeclaredScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    program_id: str
    target: str


class APIA2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    expected_revision: int
    target_state: str
    declared_scope: APIDeclaredScope
    note: str
    spec_path: str
    expected_implementation_paths: list[str] = Field(default_factory=list)
    spec_refinement_requested: bool
    gate_on_verifier_pass: bool = False
    refinement_rounds_used: int = 0
    max_refinement_rounds: int = 2
    max_refinement_cost_usd: float | None = None


class APIA2ArtifactWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str
    operation: Literal["replace"] = "replace"


class APIA2Response(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: APIA2Request
    artifacts: list[APIA2ArtifactWrite] = Field(default_factory=list)


class APIA1Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    expected_revision: int
    target_state: str
    declared_scope: APIDeclaredScope
    note: str


class APIA1Response(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: APIA1Request
    artifacts: list[APIA1ArtifactWrite] = Field(default_factory=list)


class APIBArtifactWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str
    operation: Literal["replace"] = "replace"


class APIBRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    expected_revision: int
    target_state: str
    declared_scope: APIDeclaredScope
    note: str
    implementation_paths: list[str] = Field(default_factory=list)
    verification_command: str


class APIBResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: APIBRequest
    artifacts: list[APIBArtifactWrite] = Field(default_factory=list)


def wrapper_config_path() -> Path:
    return REPO_ROOT / "supervisor" / "agent_wrappers.json"


def load_wrapper_configs(path: Path | None = None) -> dict[Actor, AgentWrapperConfig]:
    target = path or wrapper_config_path()
    payload = json.loads(target.read_text())
    wrappers = payload.get("wrappers", {})
    configs: dict[Actor, AgentWrapperConfig] = {}
    for actor_name, entry in wrappers.items():
        actor = Actor(actor_name)
        configs[actor] = AgentWrapperConfig(
            actor=actor,
            mode=WrapperMode(str(entry["mode"])),
            command=tuple(str(item) for item in entry.get("command", ())),
            model_name=entry.get("model_name"),
            enforce_read_allowlist=bool(entry.get("enforce_read_allowlist", False)),
            research_b_api_model_name=entry.get("research_b_api_model_name"),
            research_a2_max_output_tokens=(
                int(entry["research_a2_max_output_tokens"])
                if entry.get("research_a2_max_output_tokens") is not None
                else None
            ),
            research_a2_api_model_name=entry.get("research_a2_api_model_name"),
            research_a1_prompt_version=entry.get("research_a1_prompt_version"),
            research_a2_prompt_version=entry.get("research_a2_prompt_version"),
            research_b_prompt_version=entry.get("research_b_prompt_version"),
        )
    return configs


def launch_staged_request(
    *,
    status: HandoffStatus,
    staging_dir: Path,
    execute: bool,
    config_path: Path | None = None,
) -> WrapperLaunchResult:
    configs = load_wrapper_configs(config_path)
    if status.next_actor not in configs:
        raise KeyError(f"No wrapper configured for actor `{status.next_actor.value}`.")
    config = configs[status.next_actor]

    if config.mode == WrapperMode.LOCAL_VERIFIER:
        return _run_local_verifier(status=status, staging_dir=staging_dir, execute=execute)

    return _run_external_agent(
        status=status,
        staging_dir=staging_dir,
        config=config,
        execute=execute,
    )


def invoke_agent(
    *,
    command: tuple[str, ...],
    prompt_text: str,
    request_path: Path,
    prompt_path: Path,
    debug_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    usage_path: Path,
    execute: bool,
    allowed_repo_paths: tuple[str, ...] = (),
    read_allowlist_paths: tuple[str, ...] = (),
    max_output_tokens: int | None = None,
    default_model_name: str | None = None,
    cwd: Path = REPO_ROOT,
) -> AgentInvocationResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text)
    rendered_command = render_agent_command(
        command,
        prompt_path=prompt_path,
        debug_path=debug_path,
        usage_path=usage_path,
    )

    if not execute:
        return AgentInvocationResult(
            executed=False,
            command=rendered_command,
            prompt_path=str(prompt_path),
            debug_path=str(debug_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            usage_path=str(usage_path),
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            read_allowlist_paths=read_allowlist_paths,
            sandbox_root=None,
            output_envelope_exceeded=False,
            output_envelope_limit=max_output_tokens,
            estimated_output_tokens_emitted=None,
            turn_usage=None,
            exit_code=None,
        )

    sandbox_root: Path | None = None
    invocation_cwd = cwd
    request_repo_path = _repo_relative_path(request_path)
    sandbox_repo_paths = tuple(
        dict.fromkeys(path for path in (*read_allowlist_paths, *allowed_repo_paths) if path)
    )
    sync_back_repo_paths = tuple(
        dict.fromkeys(path for path in (*allowed_repo_paths, request_repo_path) if path)
    )
    sandbox_writable_paths = tuple(
        dict.fromkeys(path for path in (*allowed_repo_paths, request_repo_path) if path)
    )
    if read_allowlist_paths:
        sandbox_root = _materialize_read_allowlist_workspace(
            repo_paths=sandbox_repo_paths,
            writable_repo_paths=sandbox_writable_paths,
        )
        invocation_cwd = sandbox_root
    execution_command = _prepare_command_for_workspace(
        command=rendered_command,
        cwd=invocation_cwd,
    )

    before_snapshot = _capture_repo_snapshot()
    completed = _execute_agent_process(
        command=execution_command,
        prompt_text=prompt_text,
        cwd=invocation_cwd,
        max_output_tokens=max_output_tokens,
    )
    if sandbox_root is not None and completed.returncode == 0 and not completed.output_envelope_exceeded:
        _sync_sandbox_paths_back(
            sandbox_root=sandbox_root,
            repo_paths=sync_back_repo_paths,
        )
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    modified_repo_paths, unauthorized_repo_paths = _detect_repo_write_scope(
        before_snapshot=before_snapshot,
        after_snapshot=_capture_repo_snapshot(),
        allowed_repo_paths=allowed_repo_paths,
    )
    sidecar_text = debug_path.read_text() if debug_path.exists() else None
    turn_usage = extract_usage_telemetry(
        stdout_text=completed.stdout,
        stderr_text=completed.stderr,
        sidecar_text=sidecar_text,
        default_model_name=default_model_name,
    )
    usage_path.write_text(json.dumps(asdict(turn_usage), indent=2) + "\n")
    return AgentInvocationResult(
        executed=True,
        command=execution_command,
        prompt_path=str(prompt_path),
        debug_path=str(debug_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        usage_path=str(usage_path),
        modified_repo_paths=modified_repo_paths,
        unauthorized_repo_paths=unauthorized_repo_paths,
        read_allowlist_paths=read_allowlist_paths,
        sandbox_root=str(sandbox_root) if sandbox_root is not None else None,
        output_envelope_exceeded=completed.output_envelope_exceeded,
        output_envelope_limit=max_output_tokens,
        estimated_output_tokens_emitted=completed.estimated_output_tokens_emitted,
        turn_usage=turn_usage,
        exit_code=completed.returncode,
    )


def _run_external_agent(
    *,
    status: HandoffStatus,
    staging_dir: Path,
    config: AgentWrapperConfig,
    execute: bool,
) -> WrapperLaunchResult:
    prompt_dir = staging_dir / "launch"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{status.next_actor.value}_{status.state.value.lower()}_prompt.txt"
    debug_path = prompt_dir / f"{status.next_actor.value}_{status.state.value.lower()}_debug.log"
    stdout_path = prompt_dir / f"{status.next_actor.value}_{status.state.value.lower()}_stdout.txt"
    stderr_path = prompt_dir / f"{status.next_actor.value}_{status.state.value.lower()}_stderr.txt"
    usage_path = prompt_dir / f"{status.next_actor.value}_{status.state.value.lower()}_usage.json"
    _reset_launch_sidecars(prompt_path, debug_path, stdout_path, stderr_path, usage_path)

    context_path = staging_dir / f"{status.next_actor.value}_{status.state.value.lower()}_context.json"
    request_path = staging_dir / f"{status.next_actor.value}_{status.state.value.lower()}.json"
    prompt_text = build_wrapper_prompt(
        status=status,
        context_path=context_path,
        request_path=request_path,
    )
    allowed_repo_paths = _allowed_repo_write_paths(status)
    read_allowlist_paths = _allowed_repo_read_paths(
        status=status,
        context_path=context_path,
        request_path=request_path,
    )
    output_envelope_limit = _output_envelope_limit(status=status, config=config)

    if _uses_research_a1_api_transport(status=status):
        invocation = _invoke_research_a1_via_anthropic_api(
            status=status,
            config=config,
            prompt_text=prompt_text,
            request_path=request_path,
            prompt_path=prompt_path,
            debug_path=debug_path,
            usage_path=usage_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            execute=execute,
            allowed_repo_paths=allowed_repo_paths,
            read_allowlist_paths=read_allowlist_paths if config.enforce_read_allowlist else (),
            default_model_name=config.model_name,
        )
    elif _uses_research_b_api_transport(status=status):
        invocation = _invoke_research_b_via_anthropic_api(
            status=status,
            config=config,
            prompt_text=prompt_text,
            request_path=request_path,
            prompt_path=prompt_path,
            debug_path=debug_path,
            usage_path=usage_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            execute=execute,
            allowed_repo_paths=allowed_repo_paths,
            read_allowlist_paths=read_allowlist_paths if config.enforce_read_allowlist else (),
            default_model_name=config.research_b_api_model_name or config.model_name,
        )
    elif _uses_research_a2_api_transport(status=status):
        invocation = _invoke_research_a2_via_openai_api(
            status=status,
            config=config,
            prompt_text=prompt_text,
            request_path=request_path,
            prompt_path=prompt_path,
            debug_path=debug_path,
            usage_path=usage_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            execute=execute,
            allowed_repo_paths=allowed_repo_paths,
            read_allowlist_paths=read_allowlist_paths if config.enforce_read_allowlist else (),
            max_output_tokens=output_envelope_limit,
            default_model_name=config.research_a2_api_model_name or config.model_name,
        )
    else:
        invocation = invoke_agent(
            command=config.command,
            prompt_text=prompt_text,
            request_path=request_path,
            prompt_path=prompt_path,
            debug_path=debug_path,
            usage_path=usage_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            execute=execute,
            allowed_repo_paths=allowed_repo_paths,
            read_allowlist_paths=read_allowlist_paths if config.enforce_read_allowlist else (),
            max_output_tokens=output_envelope_limit,
            default_model_name=config.model_name,
        )

    if not execute:
        return WrapperLaunchResult(
            actor=status.next_actor,
            mode=config.mode,
            executed=False,
            command=invocation.command,
            prompt_path=invocation.prompt_path,
            debug_path=invocation.debug_path,
            stdout_path=invocation.stdout_path,
            stderr_path=invocation.stderr_path,
            report_path=None,
            usage_path=invocation.usage_path,
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            read_allowlist_paths=invocation.read_allowlist_paths,
            sandbox_root=invocation.sandbox_root,
            output_envelope_exceeded=False,
            output_envelope_limit=invocation.output_envelope_limit,
            estimated_output_tokens_emitted=None,
            turn_usage=None,
            exit_code=None,
        )

    payload = json.loads(request_path.read_text())
    payload["turn_usage"] = asdict(invocation.turn_usage)
    payload["write_scope_ok"] = not invocation.unauthorized_repo_paths
    payload["modified_repo_paths"] = list(invocation.modified_repo_paths)
    payload["unauthorized_repo_paths"] = list(invocation.unauthorized_repo_paths)
    payload["read_allowlist_paths"] = list(invocation.read_allowlist_paths)
    if invocation.output_envelope_exceeded:
        payload["write_scope_ok"] = False
        payload["note"] = (
            f"Wrapper killed `{status.next_actor.value}` after exceeding the hard output envelope "
            f"of {invocation.output_envelope_limit} estimated tokens."
        )
        payload["wrapper_abort_reason"] = "output_envelope_exceeded"
        payload["estimated_output_tokens_emitted"] = invocation.estimated_output_tokens_emitted
    request_path.write_text(json.dumps(payload, indent=2) + "\n")
    return WrapperLaunchResult(
        actor=status.next_actor,
        mode=config.mode,
        executed=True,
        command=invocation.command,
        prompt_path=invocation.prompt_path,
        debug_path=invocation.debug_path,
        stdout_path=invocation.stdout_path,
        stderr_path=invocation.stderr_path,
        report_path=None,
        usage_path=invocation.usage_path,
        modified_repo_paths=invocation.modified_repo_paths,
        unauthorized_repo_paths=invocation.unauthorized_repo_paths,
        read_allowlist_paths=invocation.read_allowlist_paths,
        sandbox_root=invocation.sandbox_root,
        output_envelope_exceeded=invocation.output_envelope_exceeded,
        output_envelope_limit=invocation.output_envelope_limit,
        estimated_output_tokens_emitted=invocation.estimated_output_tokens_emitted,
        turn_usage=invocation.turn_usage,
        exit_code=invocation.exit_code,
    )


def _reset_launch_sidecars(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            continue


def _packet_declares_read_bundle(status: HandoffStatus) -> bool:
    manifest = load_optional_program_manifest(status.active_program)
    return bool(derive_packet_read_bundle(manifest, target=status.active_target))


def _uses_research_a1_api_transport(*, status: HandoffStatus) -> bool:
    return (
        status.pipeline_type == "research"
        and status.state == SupervisorState.A1
        and status.next_actor == Actor.CLAUDE
        and _packet_declares_read_bundle(status)
    )


def _uses_research_a2_api_transport(*, status: HandoffStatus) -> bool:
    return (
        status.pipeline_type == "research"
        and status.state == SupervisorState.A2
        and status.next_actor == Actor.CODEX
        and _packet_declares_read_bundle(status)
    )


def _uses_research_b_api_transport(*, status: HandoffStatus) -> bool:
    return (
        status.pipeline_type == "research"
        and status.state == SupervisorState.B
        and status.next_actor == Actor.CLAUDE
        and _packet_declares_read_bundle(status)
    )


def _invoke_research_a1_via_anthropic_api(
    *,
    status: HandoffStatus,
    config: AgentWrapperConfig,
    prompt_text: str,
    request_path: Path,
    prompt_path: Path,
    debug_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    usage_path: Path,
    execute: bool,
    allowed_repo_paths: tuple[str, ...],
    read_allowlist_paths: tuple[str, ...],
    default_model_name: str | None,
) -> AgentInvocationResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    api_read_paths = tuple(
        path for path in read_allowlist_paths if path != status.debate_file
    )
    api_prompt = _build_api_transport_prompt(
        base_prompt=_build_a1_api_base_prompt(status=status, base_prompt=prompt_text),
        read_allowlist_paths=api_read_paths,
    )
    prompt_path.write_text(api_prompt)
    command = _render_anthropic_api_transport_command(model_name=default_model_name)

    if not execute:
        return AgentInvocationResult(
            executed=False,
            command=command,
            prompt_path=str(prompt_path),
            debug_path=str(debug_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            usage_path=str(usage_path),
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            read_allowlist_paths=api_read_paths,
            sandbox_root=None,
            output_envelope_exceeded=False,
            output_envelope_limit=None,
            estimated_output_tokens_emitted=None,
            turn_usage=None,
            exit_code=None,
        )

    before_snapshot = _capture_repo_snapshot()
    result = _call_anthropic_research_a1_api(
        prompt_text=api_prompt,
        model_name=default_model_name,
    )
    valid_artifacts, invalid_artifact_paths = _validate_api_artifacts(
        artifacts=result.artifacts,
        allowed_repo_paths=allowed_repo_paths,
        append_only_repo_paths=tuple(path for path in allowed_repo_paths if path == status.debate_file),
    )
    if not invalid_artifact_paths:
        _write_api_artifacts(valid_artifacts)
    request_path.write_text(json.dumps(result.request_payload, indent=2) + "\n")
    stdout_path.write_text(result.raw_response_text)
    stderr_path.write_text("")
    debug_path.write_text(
        json.dumps(
            {
                "model_name": result.turn_usage.model_name,
                "usage": asdict(result.turn_usage),
                "artifact_paths": [path for path, _, _ in result.artifacts],
                "invalid_artifact_paths": list(invalid_artifact_paths),
            },
            indent=2,
        )
        + "\n"
    )
    modified_repo_paths, unauthorized_repo_paths = _detect_repo_write_scope(
        before_snapshot=before_snapshot,
        after_snapshot=_capture_repo_snapshot(),
        allowed_repo_paths=allowed_repo_paths,
    )
    usage_path.write_text(json.dumps(asdict(result.turn_usage), indent=2) + "\n")
    return AgentInvocationResult(
        executed=True,
        command=command,
        prompt_path=str(prompt_path),
        debug_path=str(debug_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        usage_path=str(usage_path),
        modified_repo_paths=modified_repo_paths,
        unauthorized_repo_paths=tuple(
            dict.fromkeys((*unauthorized_repo_paths, *invalid_artifact_paths))
        ),
        read_allowlist_paths=api_read_paths,
        sandbox_root=None,
        output_envelope_exceeded=False,
        output_envelope_limit=None,
        estimated_output_tokens_emitted=result.turn_usage.output_tokens,
        turn_usage=result.turn_usage,
        exit_code=0,
    )


def _invoke_research_b_via_anthropic_api(
    *,
    status: HandoffStatus,
    config: AgentWrapperConfig,
    prompt_text: str,
    request_path: Path,
    prompt_path: Path,
    debug_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    usage_path: Path,
    execute: bool,
    allowed_repo_paths: tuple[str, ...],
    read_allowlist_paths: tuple[str, ...],
    default_model_name: str | None,
) -> AgentInvocationResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    api_prompt = _build_api_transport_prompt(
        base_prompt=_build_b_api_base_prompt(status=status, base_prompt=prompt_text),
        read_allowlist_paths=read_allowlist_paths,
    )
    prompt_path.write_text(api_prompt)
    command = _render_anthropic_api_transport_command(model_name=default_model_name)

    if not execute:
        return AgentInvocationResult(
            executed=False,
            command=command,
            prompt_path=str(prompt_path),
            debug_path=str(debug_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            usage_path=str(usage_path),
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            read_allowlist_paths=read_allowlist_paths,
            sandbox_root=None,
            output_envelope_exceeded=False,
            output_envelope_limit=None,
            estimated_output_tokens_emitted=None,
            turn_usage=None,
            exit_code=None,
        )

    before_snapshot = _capture_repo_snapshot()
    result = _call_anthropic_research_b_api(
        prompt_text=api_prompt,
        model_name=default_model_name,
    )
    valid_artifacts, invalid_artifact_paths = _validate_api_artifacts(
        artifacts=result.artifacts,
        allowed_repo_paths=allowed_repo_paths,
    )
    if not invalid_artifact_paths:
        _write_api_artifacts(valid_artifacts)
    request_path.write_text(json.dumps(result.request_payload, indent=2) + "\n")
    stdout_path.write_text(result.raw_response_text)
    stderr_path.write_text("")
    debug_path.write_text(
        json.dumps(
            {
                "model_name": result.turn_usage.model_name,
                "usage": asdict(result.turn_usage),
                "artifact_paths": [path for path, _, _ in result.artifacts],
                "invalid_artifact_paths": list(invalid_artifact_paths),
            },
            indent=2,
        )
        + "\n"
    )
    modified_repo_paths, unauthorized_repo_paths = _detect_repo_write_scope(
        before_snapshot=before_snapshot,
        after_snapshot=_capture_repo_snapshot(),
        allowed_repo_paths=allowed_repo_paths,
    )
    usage_path.write_text(json.dumps(asdict(result.turn_usage), indent=2) + "\n")
    return AgentInvocationResult(
        executed=True,
        command=command,
        prompt_path=str(prompt_path),
        debug_path=str(debug_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        usage_path=str(usage_path),
        modified_repo_paths=modified_repo_paths,
        unauthorized_repo_paths=tuple(
            dict.fromkeys((*unauthorized_repo_paths, *invalid_artifact_paths))
        ),
        read_allowlist_paths=read_allowlist_paths,
        sandbox_root=None,
        output_envelope_exceeded=False,
        output_envelope_limit=None,
        estimated_output_tokens_emitted=result.turn_usage.output_tokens,
        turn_usage=result.turn_usage,
        exit_code=0,
    )


def _invoke_research_a2_via_openai_api(
    *,
    status: HandoffStatus,
    config: AgentWrapperConfig,
    prompt_text: str,
    request_path: Path,
    prompt_path: Path,
    debug_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    usage_path: Path,
    execute: bool,
    allowed_repo_paths: tuple[str, ...],
    read_allowlist_paths: tuple[str, ...],
    max_output_tokens: int | None,
    default_model_name: str | None,
) -> AgentInvocationResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    api_prompt = _build_api_transport_prompt(
        base_prompt=prompt_text,
        read_allowlist_paths=read_allowlist_paths,
    )
    prompt_path.write_text(api_prompt)
    command = _render_api_transport_command(
        model_name=config.research_a2_api_model_name or default_model_name
    )

    if not execute:
        return AgentInvocationResult(
            executed=False,
            command=command,
            prompt_path=str(prompt_path),
            debug_path=str(debug_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            usage_path=str(usage_path),
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            read_allowlist_paths=read_allowlist_paths,
            sandbox_root=None,
            output_envelope_exceeded=False,
            output_envelope_limit=max_output_tokens,
            estimated_output_tokens_emitted=None,
            turn_usage=None,
            exit_code=None,
        )

    before_snapshot = _capture_repo_snapshot()
    result = _call_openai_research_a2_api(
        prompt_text=api_prompt,
        model_name=config.research_a2_api_model_name or default_model_name,
        max_output_tokens=max_output_tokens,
    )
    valid_artifacts, invalid_artifact_paths = _validate_api_artifacts(
        artifacts=result.artifacts,
        allowed_repo_paths=allowed_repo_paths,
    )
    if not invalid_artifact_paths:
        _write_api_artifacts(valid_artifacts)
    request_path.write_text(json.dumps(result.request_payload, indent=2) + "\n")
    stdout_path.write_text(result.raw_response_text)
    stderr_path.write_text("")
    debug_path.write_text(
        json.dumps(
            {
                "model_name": result.turn_usage.model_name,
                "usage": asdict(result.turn_usage),
                "artifact_paths": [path for path, _, _ in result.artifacts],
                "invalid_artifact_paths": list(invalid_artifact_paths),
            },
            indent=2,
        )
        + "\n"
    )
    modified_repo_paths, unauthorized_repo_paths = _detect_repo_write_scope(
        before_snapshot=before_snapshot,
        after_snapshot=_capture_repo_snapshot(),
        allowed_repo_paths=allowed_repo_paths,
    )
    usage_path.write_text(json.dumps(asdict(result.turn_usage), indent=2) + "\n")
    return AgentInvocationResult(
        executed=True,
        command=command,
        prompt_path=str(prompt_path),
        debug_path=str(debug_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        usage_path=str(usage_path),
        modified_repo_paths=modified_repo_paths,
        unauthorized_repo_paths=tuple(
            dict.fromkeys((*unauthorized_repo_paths, *invalid_artifact_paths))
        ),
        read_allowlist_paths=read_allowlist_paths,
        sandbox_root=None,
        output_envelope_exceeded=False,
        output_envelope_limit=max_output_tokens,
        estimated_output_tokens_emitted=result.turn_usage.output_tokens,
        turn_usage=result.turn_usage,
        exit_code=0,
    )


def _render_api_transport_command(*, model_name: str | None) -> tuple[str, ...]:
    model = model_name or "o4-mini"
    return ("openai", "responses.parse", "--model", model)


def _render_anthropic_api_transport_command(*, model_name: str | None) -> tuple[str, ...]:
    model = model_name or "claude-sonnet-4-6"
    return ("anthropic", "messages.create", "--model", model)


def _build_api_transport_prompt(
    *,
    base_prompt: str,
    read_allowlist_paths: tuple[str, ...],
) -> str:
    bundle_text = _serialize_read_bundle_for_api(read_allowlist_paths)
    return (
        f"{base_prompt}\n"
        "You do not have shell or filesystem access in this transport.\n"
        "Only the embedded file contents below are available. Treat any path not embedded as unavailable.\n"
        "Return only structured JSON matching the required response schema.\n\n"
        f"{bundle_text}"
    )


def _serialize_read_bundle_for_api(read_allowlist_paths: tuple[str, ...]) -> str:
    sections: list[str] = []
    for repo_path in read_allowlist_paths:
        sections.append(f"=== FILE: {repo_path} ===")
        sections.append(_read_repo_text_for_api(repo_path))
        sections.append("")
    return "\n".join(sections)


def _read_repo_text_for_api(repo_path: str) -> str:
    target = REPO_ROOT / repo_path
    if not target.exists():
        return "[missing file]"
    try:
        return target.read_text()
    except UnicodeDecodeError:
        return "[binary file omitted]"


def _resolve_repo_artifact_path(repo_path: str) -> Path:
    candidate = (REPO_ROOT / repo_path).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError(f"API transport attempted to write outside repo: {repo_path}") from exc
    return candidate


def _validate_api_artifacts(
    *,
    artifacts: tuple[tuple[str, str, str], ...],
    allowed_repo_paths: tuple[str, ...],
    append_only_repo_paths: tuple[str, ...] = (),
) -> tuple[tuple[tuple[str, str, str], ...], tuple[str, ...]]:
    allowed = {path for path in allowed_repo_paths if path}
    append_only = {path for path in append_only_repo_paths if path}
    valid: list[tuple[str, str, str]] = []
    invalid: list[str] = []
    for artifact_path, artifact_content, artifact_operation in artifacts:
        if artifact_path not in allowed:
            invalid.append(artifact_path)
            continue
        if artifact_operation not in {"append", "replace"}:
            invalid.append(artifact_path)
            continue
        if artifact_path in append_only and artifact_operation != "append":
            invalid.append(artifact_path)
            continue
        if artifact_path not in append_only and artifact_operation != "replace":
            invalid.append(artifact_path)
            continue
        valid.append((artifact_path, artifact_content, artifact_operation))
    return tuple(valid), tuple(dict.fromkeys(invalid))


def _write_api_artifacts(artifacts: tuple[tuple[str, str, str], ...]) -> None:
    for artifact_path, artifact_content, artifact_operation in artifacts:
        target_path = _resolve_repo_artifact_path(artifact_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if artifact_operation == "append":
            existing = target_path.read_text() if target_path.exists() else ""
            prefix = "\n\n" if existing and not existing.endswith("\n\n") else ""
            target_path.write_text(existing + prefix + artifact_content)
        else:
            target_path.write_text(artifact_content)


def _build_a1_api_base_prompt(*, status: HandoffStatus, base_prompt: str) -> str:
    prompt_without_full_debate = base_prompt
    if status.debate_file:
        prompt_without_full_debate = prompt_without_full_debate.replace(
            f"- `{status.debate_file}`\n", ""
        )
    next_turn = (status.debate_last_turn or 0) + 1
    return (
        "You are revising a packet-scoped A1 debate/spec update for a specific manuscript fragment.\n"
        "Your output must be structured only.\n"
        "Do not write the paper section.\n"
        "Do not summarize the entire debate.\n"
        "Use the staged context excerpt instead of rereading the full debate log.\n"
        "Return a request object and exactly one append-only debate turn artifact.\n"
        f"The only allowed artifact path is `{status.debate_file}`.\n"
        "That artifact must use operation `append`, never `replace`.\n"
        f"The debate artifact must append a single new turn headed `## Turn {next_turn} — Architect (A1)`.\n"
        "Keep the staged note to at most 3 sentences.\n\n"
        f"{prompt_without_full_debate}"
    )


def _build_b_api_base_prompt(*, status: HandoffStatus, base_prompt: str) -> str:
    implementation_paths = list(status.artifact_paths.implementation)
    allowed_paths = "\n".join(f"- `{path}`" for path in implementation_paths)
    return (
        "You are writing a packet-scoped research B draft against a locked prose spec.\n"
        "Your output must be structured only.\n"
        "Do not use tools.\n"
        "Do not revise the prose spec.\n"
        "Return a request object and draft artifact writes only.\n"
        "Write markdown only to the declared implementation path.\n"
        "Each draft artifact must use operation `replace`, never `append` or `update`.\n"
        "The draft must satisfy required phrases and citations from the prose spec verbatim.\n"
        "Keep the staged note concise.\n"
        "Allowed implementation path(s):\n"
        f"{allowed_paths}\n\n"
        f"{base_prompt}"
    )


def _call_openai_research_a2_api(
    *,
    prompt_text: str,
    model_name: str | None,
    max_output_tokens: int | None,
) -> APITransportResult:
    client = OpenAI()
    response = client.responses.parse(
        model=model_name or "o4-mini",
        input=prompt_text,
        text_format=APIA2Response,
        max_output_tokens=max_output_tokens,
        reasoning={"effort": "low"},
        text={"verbosity": "medium"},
        store=False,
        truncation="disabled",
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI API transport returned no parsed A2 response.")
    usage = response.usage
    cached_tokens = (
        int(getattr(usage.input_tokens_details, "cached_tokens", 0))
        if usage is not None and getattr(usage, "input_tokens_details", None) is not None
        else 0
    )
    input_tokens = int(usage.input_tokens) if usage is not None else 0
    output_tokens = int(usage.output_tokens) if usage is not None else 0
    resolved_model = getattr(response, "model", None) or model_name
    turn_usage = TurnUsageTelemetry(
        model_name=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=cached_tokens,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cached_tokens,
        ),
        telemetry_captured=True,
    )
    return APITransportResult(
        request_payload=parsed.request.model_dump(mode="json"),
        artifacts=tuple((item.path, item.content, item.operation) for item in parsed.artifacts),
        turn_usage=turn_usage,
        raw_response_text=response.output_text,
    )


def _call_anthropic_research_a1_api(
    *,
    prompt_text: str,
    model_name: str | None,
) -> APITransportResult:
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model_name or "claude-sonnet-4-6",
        max_tokens=2000,
        system=(
            "You are the Architect for a packet-scoped research A1 turn. "
            "Use the provided file bundle only. "
            "Return only the tool call with structured data. "
            "Do not draft prose. Do not restate the whole debate."
        ),
        messages=[{"role": "user", "content": prompt_text}],
        tools=[
            {
                "name": "submit_a1_result",
                "description": "Submit the revised A1 request and one append-only debate turn artifact.",
                "input_schema": APIA1Response.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": "submit_a1_result"},
        temperature=0,
    )
    tool_block = next(
        (
            block
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "submit_a1_result"
        ),
        None,
    )
    if tool_block is None:
        raise RuntimeError("Anthropic API transport returned no A1 tool result.")
    parsed = APIA1Response.model_validate(tool_block.input)
    usage = response.usage
    input_tokens = int(getattr(usage, "input_tokens", 0))
    output_tokens = int(getattr(usage, "output_tokens", 0))
    resolved_model = getattr(response, "model", None) or model_name
    turn_usage = TurnUsageTelemetry(
        model_name=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        telemetry_captured=True,
    )
    return APITransportResult(
        request_payload=parsed.request.model_dump(mode="json"),
        artifacts=tuple((item.path, item.content, item.operation) for item in parsed.artifacts),
        turn_usage=turn_usage,
        raw_response_text=json.dumps(tool_block.input),
    )


def _call_anthropic_research_b_api(
    *,
    prompt_text: str,
    model_name: str | None,
) -> APITransportResult:
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model_name or "claude-sonnet-4-6",
        max_tokens=2500,
        system=(
            "You are the Writer for a packet-scoped research B turn. "
            "Use the provided file bundle only. "
            "Return only the tool call with structured data. "
            "Do not produce analysis outside the tool payload."
        ),
        messages=[{"role": "user", "content": prompt_text}],
        tools=[
            {
                "name": "submit_b_result",
                "description": "Submit the B request and replace-only markdown draft artifact.",
                "input_schema": APIBResponse.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": "submit_b_result"},
        temperature=0,
    )
    tool_block = next(
        (
            block
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "submit_b_result"
        ),
        None,
    )
    if tool_block is None:
        raise RuntimeError("Anthropic API transport returned no B tool result.")
    parsed = APIBResponse.model_validate(tool_block.input)
    usage = response.usage
    input_tokens = int(getattr(usage, "input_tokens", 0))
    output_tokens = int(getattr(usage, "output_tokens", 0))
    resolved_model = getattr(response, "model", None) or model_name
    turn_usage = TurnUsageTelemetry(
        model_name=resolved_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        estimated_cost_usd=estimate_cost_usd(
            model_name=resolved_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        telemetry_captured=True,
    )
    return APITransportResult(
        request_payload=parsed.request.model_dump(mode="json"),
        artifacts=tuple((item.path, item.content, item.operation) for item in parsed.artifacts),
        turn_usage=turn_usage,
        raw_response_text=json.dumps(tool_block.input),
    )


def _run_local_verifier(
    *,
    status: HandoffStatus,
    staging_dir: Path,
    execute: bool,
) -> WrapperLaunchResult:
    if not status.verification_command:
        raise ValueError("Verifier wrapper requires a verification_command in supervisor state.")

    request_path = staging_dir / f"{status.next_actor.value}_{status.state.value.lower()}.json"
    report_path = staging_dir.parent / "verification_report.txt"
    stderr_path = staging_dir.parent / "verification_error.txt"

    if not execute:
        return WrapperLaunchResult(
            actor=status.next_actor,
            mode=WrapperMode.LOCAL_VERIFIER,
            executed=False,
            command=(status.verification_command,),
            prompt_path=None,
            debug_path=None,
            stdout_path=None,
            stderr_path=str(stderr_path),
            report_path=str(report_path),
            usage_path=None,
            modified_repo_paths=(),
            unauthorized_repo_paths=(),
            turn_usage=None,
            exit_code=None,
        )

    completed = subprocess.run(
        status.verification_command,
        text=True,
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    report_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)

    payload = json.loads(request_path.read_text())
    payload["turn_usage"] = asdict(TurnUsageTelemetry(model_name="local_verifier"))
    payload["verification_report"] = str(report_path)
    if completed.returncode == 0:
        payload["verification_passed"] = True
        payload["note"] = (
            f"Verifier wrapper ran `{status.verification_command}` successfully. "
            "Implementation matches the recorded artifact set."
        )
    else:
        payload["target_state"] = "B"
        payload["verification_passed"] = False
        payload["error_report"] = str(stderr_path)
        payload["note"] = (
            f"Verifier wrapper ran `{status.verification_command}` and it failed. "
            "Returning to builder with bounded error report."
        )
    request_path.write_text(json.dumps(payload, indent=2) + "\n")

    return WrapperLaunchResult(
        actor=status.next_actor,
        mode=WrapperMode.LOCAL_VERIFIER,
        executed=True,
        command=(status.verification_command,),
        prompt_path=None,
        debug_path=None,
        stdout_path=str(report_path),
        stderr_path=str(stderr_path),
        report_path=str(report_path),
        usage_path=None,
        modified_repo_paths=(),
        unauthorized_repo_paths=(),
        turn_usage=TurnUsageTelemetry(model_name="local_verifier"),
        exit_code=completed.returncode,
    )


def build_wrapper_prompt(
    *,
    status: HandoffStatus,
    context_path: Path,
    request_path: Path,
) -> str:
    if status.state == SupervisorState.A1 and status.pipeline_type == "research":
        role_label = "Architect"
    elif status.state == SupervisorState.A2 and status.pipeline_type == "research":
        role_label = "Skeptic"
    elif status.state == SupervisorState.B and status.next_actor == Actor.CLAUDE:
        role_label = "Writing Agent"
    else:
        role_label = {
            Actor.CLAUDE: "Spec Agent",
            Actor.CODEX: "Implementation Agent",
        }.get(status.next_actor, status.next_actor.value)
    allowed_lines = []
    if status.state == status.state.B:
        allowed_lines.extend(f"- `{path}`" for path in status.artifact_paths.implementation)
    elif status.state in (status.state.A1, status.state.A2):
        if status.debate_file and not (
            status.pipeline_type == "research" and status.state == SupervisorState.A2
        ):
            allowed_lines.append(f"- `{status.debate_file}`")
        if status.state == SupervisorState.A2 and status.pipeline_type == "research":
            allowed_lines.append(
                f"- `{status.artifact_paths.spec or default_research_spec_path(program_id=status.active_program, target=status.active_target)}`"
            )
    allowed_artifacts = "\n".join(allowed_lines) if allowed_lines else "- staged request only"
    manifest = load_optional_program_manifest(status.active_program)
    active_packet = packet_for_target(manifest, target=status.active_target)
    next_packet = next_manifest_packet(manifest)
    packet = active_packet or next_packet
    manifest_guidance = ""
    if packet is not None:
        packet_lines = [
            f"Manifest-selected next packet:",
            f"- packet_id: `{packet.packet_id}`",
            f"- title: `{packet.title}`",
            f"- target: `{packet.target}`",
            f"- summary: {packet.summary}",
        ]
        if packet.allowed_artifacts:
            packet_lines.append("- allowed_artifacts:")
            packet_lines.extend(f"  - `{path}`" for path in packet.allowed_artifacts)
        derived_bundle = derive_packet_read_bundle(manifest, packet=packet)
        if packet.read_bundle:
            packet_lines.append("- read_bundle_overrides:")
            packet_lines.extend(f"  - `{path}`" for path in packet.read_bundle)
        if derived_bundle:
            packet_lines.append("- derived_read_bundle:")
            packet_lines.extend(f"  - `{path}`" for path in derived_bundle)
        if packet.token_budget:
            packet_lines.append(f"- token_budget: {json.dumps(packet.token_budget, sort_keys=True)}")
        if packet.success_condition:
            packet_lines.append(f"- success_condition: {packet.success_condition}")
        packet_lines.append("")
        packet_lines.append(
            "Do not invent a new packet. Use the manifest-selected packet as the default next step."
        )
        manifest_guidance = "\n".join(packet_lines) + "\n\n"
    elif manifest is not None and status.state == SupervisorState.A1:
        manifest_guidance = (
            "The program manifest has no pending packets.\n"
            "If the completed work is promotable, route to `D` with human gate `contract_promotion` "
            "instead of inventing new work.\n\n"
        )
    read_lines = [
        f"- `{context_path}`",
        f"- `{request_path}`",
    ]
    if status.seed_spec_path:
        read_lines.append(f"- `{status.seed_spec_path}`")
    if status.pipeline_type == "research":
        derived_bundle = derive_packet_read_bundle(manifest, packet=packet)
        if packet is not None and derived_bundle:
            read_lines.extend(f"- `{path}`" for path in derived_bundle)
        elif status.state == SupervisorState.A1 and status.debate_file:
            read_lines.append(f"- `{status.debate_file}`")
        if status.state == SupervisorState.B:
            spec_path = status.artifact_paths.spec or default_research_spec_path(
                program_id=status.active_program,
                target=status.active_target,
            )
            read_lines.append(f"- `{spec_path}`")
    elif status.debate_file:
        read_lines.append(f"- `{status.debate_file}`")

    research_context_discipline = ""
    if status.pipeline_type == "research":
        discipline_lines = [
            "Research context discipline:",
            "- the context JSON already contains a capped debate excerpt; use it as the default working set",
            "- a wrapper-level read allowlist is active; only the mirrored files in the working sandbox are available by default",
            "- prefer the packet-declared read bundle over ad hoc file discovery",
            "- do not read the full debate log unless the packet explicitly declares it",
            "- do not run broad repo-wide search commands (`rg`, `grep`, `find`) across `src/`, `supervisor/`, or `research_areas/`",
            "- if you need another file, stop and fail rather than guessing or widening the read set inside the turn",
            "- do not restate the seed, architecture, or prior turns at length",
            "",
        ]
        research_context_discipline = "\n".join(discipline_lines)
    extra_guidance = ""
    if status.state == SupervisorState.A1 and status.pipeline_type == "research":
        a1_guidance_lines = [
            "This is a research debate turn, not a drafting turn.",
            "- propose or revise the outline/claim structure in the debate file",
            "- if a prior skeptic critique exists in the debate file, answer it directly and revise the outline rather than restating the previous draft",
            "- do not lock the prose spec yet and do not write the paper draft in A1",
            "- leave the next turn enough tension to let the skeptic pressure-test the outline",
            "- keep the staged note concise and avoid regurgitating the seed or repo history",
            "",
        ]
        extra_guidance = "\n".join(a1_guidance_lines) + "\n"
    elif status.state == SupervisorState.A2:
        spec_path = (
            status.artifact_paths.spec
            or (
                default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
                if status.pipeline_type == "research"
                else status.debate_file
            )
        )
        a2_guidance_lines = [
            "For A2, the staged request must keep the supervisor schema exactly.",
            "Required top-level fields for a build handoff are:",
            f"- `spec_path`: `{spec_path}`",
        ]
        expected_paths = list(status.artifact_paths.implementation)
        if not expected_paths and next_packet is not None:
            expected_paths = list(next_packet.allowed_artifacts)
        if not expected_paths and status.pipeline_type == "research":
            expected_paths = [
                default_research_draft_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            ]
        if expected_paths:
            a2_guidance_lines.append("- `expected_implementation_paths`:")
            a2_guidance_lines.extend(f"  - `{path}`" for path in expected_paths)
        if status.pipeline_type == "research":
            a2_guidance_lines.extend(
                [
                    "For research A2, act as the skeptic rather than the drafter.",
                    "- aggressively pressure-test the outline, claims, empirical requirements, and section ordering using only the staged context and packet-declared read bundle",
                    "- do not run broad shell exploration or repo-wide searches; if the packet read bundle is insufficient, fail rather than probing the repo",
                    "- if the proposal is not hardened, set `spec_refinement_requested` to true and return to A1 with concrete objections",
                    "- only advance to `B` when the outline is actually hardened enough to lock a prose contract",
                    "- write the deterministic prose spec JSON to `spec_path` using the canonical schema only",
                    "- the spec artifact must use operation `replace`, never `update` or `append`",
                    "- required top-level prose spec keys are exactly: `packet_id`, `required_headers`, `assertions`, `global_word_min`, `global_word_max`",
                    "- each assertion must use one of: `contains_phrase`, `contains_citation`, `has_subsection`, `word_count_range`, `absent_phrase`",
                    "- HARD CONSTRAINT: you are strictly forbidden from creating assertions that test cosmetic properties — word counts, formatting, capitalization, sentence structure, or stylistic phrasing. `word_count_range` may only be used for gross structural bounds (e.g. minimum 200 words to prevent stub sections), never for tight windows. `contains_phrase` and `contains_citation` must test load-bearing theoretical claims or evidence anchors, not stylistic wording.",
                    "- for `contains_phrase` and `contains_citation`, the `target` string must be an exact substring that B can paste verbatim into the draft",
                    "- do not emit legacy prose-spec keys like `required_phrases`, `required_citations`, `banned_phrases`, or `word_count_bounds`",
                    "- do not draft prose in A2",
                    "- a hard output envelope is active for this skeptic turn; stop as soon as the staged request and spec are complete",
                    "- keep the staged note to at most 3 sentences",
                    "- do not restate the seed, the architecture, or prior debate turns at length",
                    "- do not rewrite the full outline in the staged note",
                ]
            )
        if status.pipeline_type == "build":
            a2_guidance_lines.extend(
                [
                    "- HARD CONSTRAINT: build specs must include at least one behavioral verification anchor — a test that exercises runtime behavior, not just formatting, linting, type annotations, or file existence. A spec whose verification command reduces to a linter or formatter without a behavioral assertion is a contract failure. If the packet scope genuinely requires only cosmetic changes, the spec must explicitly declare `verification_class: cosmetic` and justify why no behavioral anchor exists.",
                ]
            )
        a2_guidance_lines.extend(
            [
                "- keep `target_state` as `B` only when the critique is resolved; otherwise return to `A1` with `spec_refinement_requested=true`",
                "- do not replace these with an `artifact_paths` object; `spec_path` and `expected_implementation_paths` must be top-level fields",
                "If this A2 packet should pause on verifier pass instead of auto-looping to the next A1 cycle, set `gate_on_verifier_pass` to true in the staged request.",
                "",
            ]
        )
        extra_guidance = "\n".join(a2_guidance_lines) + "\n"
    elif status.state == SupervisorState.B and status.next_actor in {Actor.CODEX, Actor.CLAUDE}:
        b_guidance_lines = [
            "For B, the staged request must keep the supervisor schema exactly.",
        ]
        implementation_paths = list(status.artifact_paths.implementation)
        if not implementation_paths and next_packet is not None:
            implementation_paths = list(next_packet.allowed_artifacts)
        if not implementation_paths and status.pipeline_type == "research":
            implementation_paths = [
                default_research_draft_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            ]
        if implementation_paths:
            b_guidance_lines.append("- `implementation_paths` must equal:")
            b_guidance_lines.extend(f"  - `{path}`" for path in implementation_paths)
        verification_command = status.verification_command
        if not verification_command and next_packet is not None:
            verification_command = next_packet.verification_command
        if (
            not verification_command
            and status.pipeline_type == "research"
            and implementation_paths
        ):
            verification_command = default_research_verification_command(
                draft_path=implementation_paths[0],
                spec_path=status.artifact_paths.spec
                or default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                ),
            )
        if verification_command:
            b_guidance_lines.extend(
                [
                    f"- `verification_command`: `{verification_command}`",
                    "- do not omit `verification_command`, even if no source edits were required",
                ]
            )
        if status.pipeline_type == "research":
            b_guidance_lines.extend(
                [
                    "- write the research draft markdown to the declared implementation path",
                    "- do not modify the prose spec during B; B writes the draft, C verifies conformance",
                    "- the verifier is an exact deterministic gate; required phrases and citations from the prose spec must appear verbatim in the draft",
                    "- do not paraphrase a required phrase or citation string to make it sound nicer; if the exact string is awkward, that is an A2 contract problem, not a B drafting license",
                    "- keep the staged note concise and focus on what changed in the draft",
                ]
            )
        b_guidance_lines.extend(
            [
                "- keep `target_state` as `C`",
                "- do not replace these with an `artifact_paths` object; `implementation_paths` and `verification_command` must be top-level fields",
                "",
            ]
        )
        extra_guidance = "\n".join(b_guidance_lines) + "\n"

    return (
        f"You are the {role_label} for supervisor state `{status.state.value}`.\n\n"
        f"Read these files first:\n"
        f"{chr(10).join(read_lines)}\n\n"
        f"Rules:\n"
        f"- do not modify supervisor state files directly\n"
        f"- update only the staged request plus these allowed artifacts:\n"
        f"{allowed_artifacts}\n"
        f"- stay within active program `{status.active_program}` / target `{status.active_target}`\n"
        f"- respect out-of-scope constraints from the genesis record already loaded in the context\n\n"
        f"{manifest_guidance}"
        f"{research_context_discipline}"
        f"{extra_guidance}"
        f"After completing the work, update `{request_path}` and stop.\n"
        f"For audit, the current supervisor status is:\n"
        f"{json.dumps(_sanitize_status_for_prompt(status), indent=2)}\n"
    )


def render_agent_command(
    command: tuple[str, ...],
    *,
    prompt_path: Path,
    debug_path: Path,
    usage_path: Path,
) -> tuple[str, ...]:
    replacements = {
        "{prompt_path}": str(prompt_path),
        "{debug_path}": str(debug_path),
        "{usage_path}": str(usage_path),
    }
    rendered: list[str] = []
    for item in command:
        value = item
        for needle, replacement in replacements.items():
            value = value.replace(needle, replacement)
        rendered.append(value)
    return tuple(rendered)


def _sanitize_status_for_prompt(status: HandoffStatus) -> dict[str, object]:
    return _relativize_repo_strings(status_to_dict(status))


def _relativize_repo_strings(value: object) -> object:
    if isinstance(value, str):
        return _relativize_repo_path_string(value)
    if isinstance(value, dict):
        return {key: _relativize_repo_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_relativize_repo_strings(item) for item in value]
    return value


def _relativize_repo_path_string(value: str) -> str:
    repo_prefix = str(REPO_ROOT) + os.sep
    if value.startswith(repo_prefix):
        return value[len(repo_prefix) :].replace(os.sep, "/")
    return value


def _repo_relative_path(path: Path | str) -> str | None:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return None
    return candidate.as_posix().lstrip("./")


def _allowed_repo_read_paths(
    *,
    status: HandoffStatus,
    context_path: Path,
    request_path: Path,
) -> tuple[str, ...]:
    manifest = load_optional_program_manifest(status.active_program)
    packet = packet_for_target(manifest, target=status.active_target) or next_manifest_packet(manifest)
    paths: list[str | None] = [
        _repo_relative_path(context_path),
        _repo_relative_path(request_path),
    ]
    if status.seed_spec_path:
        paths.append(status.seed_spec_path)
    derived_bundle = derive_packet_read_bundle(manifest, packet=packet)
    if status.pipeline_type == "research" and packet is not None and derived_bundle:
        paths.extend(derived_bundle)
        if status.state == SupervisorState.A1 and status.debate_file:
            paths.append(status.debate_file)
        if status.state in {SupervisorState.A2, SupervisorState.B}:
            paths.append(
                status.artifact_paths.spec
                or default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            )
        if status.state == SupervisorState.B:
            implementation_paths = list(status.artifact_paths.implementation)
            if not implementation_paths:
                implementation_paths = list(packet.allowed_artifacts)
            paths.extend(path for path in implementation_paths if path)
    else:
        if status.debate_file:
            paths.append(status.debate_file)
        if status.pipeline_type == "research" and status.state in {SupervisorState.A2, SupervisorState.B}:
            paths.append(
                status.artifact_paths.spec
                or default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            )
        if status.state == SupervisorState.B:
            implementation_paths = list(status.artifact_paths.implementation)
            if not implementation_paths and packet is not None:
                implementation_paths = list(packet.allowed_artifacts)
            paths.extend(path for path in implementation_paths if path)
        paths.extend(_completed_manifest_artifacts(status.active_program))
    return tuple(dict.fromkeys(path for path in paths if path))


def _completed_manifest_artifacts(program_id: str) -> tuple[str, ...]:
    manifest = load_optional_program_manifest(program_id)
    if manifest is None:
        return ()
    completed: list[str] = []
    for packet in manifest.packets:
        if packet.status.value != "complete":
            continue
        completed.extend(str(path) for path in packet.allowed_artifacts if path)
    return tuple(dict.fromkeys(completed))


def _output_envelope_limit(*, status: HandoffStatus, config: AgentWrapperConfig) -> int | None:
    if status.pipeline_type != "research" or status.state != SupervisorState.A2:
        return None
    manifest = load_optional_program_manifest(status.active_program)
    packet = packet_for_target(manifest, target=status.active_target) or next_manifest_packet(manifest)
    packet_limit = None
    if packet is not None and packet.token_budget is not None:
        packet_limit = packet.token_budget.get("a2_max_output")
    if config.research_a2_max_output_tokens is None:
        return packet_limit
    if packet_limit is None:
        return config.research_a2_max_output_tokens
    return min(config.research_a2_max_output_tokens, packet_limit)


def _materialize_read_allowlist_workspace(
    *,
    repo_paths: tuple[str, ...],
    writable_repo_paths: tuple[str, ...],
) -> Path:
    sandbox_root = Path(
        tempfile.mkdtemp(prefix="ztare_agent_fs_", dir=tempfile.gettempdir())
    )
    writable = set(writable_repo_paths)
    for repo_path in repo_paths:
        real_path = REPO_ROOT / repo_path
        sandbox_path = sandbox_root / repo_path
        real_path.parent.mkdir(parents=True, exist_ok=True)
        sandbox_path.parent.mkdir(parents=True, exist_ok=True)
        if repo_path in writable:
            if real_path.exists():
                shutil.copy2(real_path, sandbox_path)
            else:
                sandbox_path.write_text("")
        else:
            if real_path.exists():
                shutil.copy2(real_path, sandbox_path)
    return sandbox_root


def _sync_sandbox_paths_back(*, sandbox_root: Path, repo_paths: tuple[str, ...]) -> None:
    for repo_path in repo_paths:
        sandbox_path = sandbox_root / repo_path
        if not sandbox_path.exists():
            continue
        target_path = REPO_ROOT / repo_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sandbox_path, target_path)


def _execute_agent_process(
    *,
    command: tuple[str, ...],
    prompt_text: str,
    cwd: Path,
    max_output_tokens: int | None,
) -> ProcessExecutionResult:
    if max_output_tokens is not None and _supports_stream_output_envelope(command):
        return _execute_agent_process_with_output_envelope(
            command=command,
            prompt_text=prompt_text,
            cwd=cwd,
            max_output_tokens=max_output_tokens,
        )
    completed = subprocess.run(
        list(command),
        input=prompt_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    return ProcessExecutionResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def _prepare_command_for_workspace(
    *,
    command: tuple[str, ...],
    cwd: Path,
) -> tuple[str, ...]:
    if not command:
        return command
    if Path(command[0]).name != "codex":
        return command
    if "--skip-git-repo-check" in command:
        return command
    return (*command, "--skip-git-repo-check")


def _supports_stream_output_envelope(command: tuple[str, ...]) -> bool:
    return bool(command) and Path(command[0]).name == "codex"


def _execute_agent_process_with_output_envelope(
    *,
    command: tuple[str, ...],
    prompt_text: str,
    cwd: Path,
    max_output_tokens: int,
) -> ProcessExecutionResult:
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        bufsize=1,
    )
    stdout_chunks: list[str] = []
    stderr_text = ""
    estimated_output_tokens = 0
    if process.stdin is not None:
        process.stdin.write(prompt_text)
        process.stdin.close()
        process.stdin = None
    if process.stdout is None:
        stdout_text, stderr_text = process.communicate()
        return ProcessExecutionResult(
            stdout=stdout_text,
            stderr=stderr_text,
            returncode=process.returncode or 1,
        )

    for line in process.stdout:
        stdout_chunks.append(line)
        estimated_output_tokens += _estimated_agent_output_tokens_from_line(line)
        if estimated_output_tokens > max_output_tokens:
            process.kill()
            remaining_stdout, stderr_text = process.communicate()
            stdout_chunks.append(remaining_stdout)
            return ProcessExecutionResult(
                stdout="".join(stdout_chunks),
                stderr=stderr_text,
                returncode=process.returncode or 1,
                output_envelope_exceeded=True,
                estimated_output_tokens_emitted=estimated_output_tokens,
            )

    remaining_stdout, stderr_text = process.communicate()
    stdout_chunks.append(remaining_stdout)
    return ProcessExecutionResult(
        stdout="".join(stdout_chunks),
        stderr=stderr_text,
        returncode=process.returncode or 0,
        estimated_output_tokens_emitted=estimated_output_tokens,
    )


def _estimated_agent_output_tokens_from_line(line: str) -> int:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return 0
    text = ""
    if payload.get("type") == "item.completed":
        item = payload.get("item") or {}
        if item.get("type") == "agent_message":
            text = str(item.get("text", ""))
    if not text:
        return 0
    return max((len(text) + 3) // 4, 1)


def _allowed_repo_write_paths(status: HandoffStatus) -> tuple[str, ...]:
    if status.state == SupervisorState.A1:
        allowed = [status.debate_file] if status.debate_file else []
        return tuple(path for path in allowed if path)
    if status.state == SupervisorState.A2:
        allowed: list[str | None] = []
        if status.debate_file and not status.pipeline_type == "research":
            allowed.append(status.debate_file)
        if status.pipeline_type == "research":
            allowed.append(
                status.artifact_paths.spec
                or default_research_spec_path(
                    program_id=status.active_program,
                    target=status.active_target,
                )
            )
        return tuple(path for path in allowed if path)
    if status.state == SupervisorState.B:
        return tuple(status.artifact_paths.implementation)
    return ()


def _capture_repo_snapshot() -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for root, dirs, files in os.walk(REPO_ROOT):
        rel_root = Path(root).relative_to(REPO_ROOT)
        dirs[:] = [
            name
            for name in dirs
            if name != ".git" and not _is_ignored_repo_path((rel_root / name).as_posix() + "/")
        ]
        for filename in files:
            rel_path = (rel_root / filename).as_posix() if rel_root != Path(".") else filename
            if _is_ignored_repo_path(rel_path):
                continue
            path = Path(root) / filename
            try:
                stat = path.lstat()
            except FileNotFoundError:
                continue
            snapshot[rel_path] = (int(stat.st_size), int(stat.st_mtime_ns))
    return snapshot


def _detect_repo_write_scope(
    *,
    before_snapshot: dict[str, tuple[int, int]],
    after_snapshot: dict[str, tuple[int, int]],
    allowed_repo_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    changed: list[str] = []
    all_paths = set(before_snapshot) | set(after_snapshot)
    for path in sorted(all_paths):
        if before_snapshot.get(path) != after_snapshot.get(path):
            changed.append(path)
    allowed = {path for path in allowed_repo_paths if path}
    unauthorized = tuple(path for path in changed if path not in allowed)
    return tuple(changed), unauthorized


def _is_ignored_repo_path(path: str) -> bool:
    normalized = path.lstrip("./")
    if normalized.endswith("/"):
        normalized = normalized[:-1]
    parts = Path(normalized).parts
    if len(parts) >= 2 and parts[0] == "supervisor" and parts[1] == "active_runs":
        return True
    if "__pycache__" in parts:
        return True
    ignored_suffixes = (".pyc", ".pyo", ".DS_Store")
    ignored_roots = (".pytest_cache", ".mypy_cache", ".ruff_cache")
    return normalized.endswith(ignored_suffixes) or any(part in ignored_roots for part in parts)
