"""Capability-aware worker dispatch.

This is a thin resolver, not a new orchestrator. It routes a worker call along
the explicit axes captured in GP-249: capability, state, identity/fungibility,
and transport. The default path remains the caller's existing LLM function.
Agent dispatch is opt-in via ``ZTARE_AGENT_DISPATCH`` and returns raw text for
the call site to parse through its existing typed-contract validator.
"""
from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ztare.common.artifact_refs import (
    collect_artifact_refs_from_text,
    project_ref_requires_resolution,
    visible_workbench_authority_project,
)
from ztare.common.ask_spec import AskSpec, render_ask_spec_markdown
from ztare.common.briefing_pack import (
    BriefingPackRequest,
    ToolSource,
    build_briefing_pack,
    visible_workbench_contract_text,
)
from ztare.common.cegis_membrane import DISCOVERY, EVALUATION, HARNESS_DEBUG
from ztare.common.projection_owner_registry import VISIBLE_WORKBENCH_SOURCE_REFS
from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    CODEX_SANDBOX_VISIBLE_WORKBENCH,
    SEALED_CLAUDE_DISALLOWED_TOOLS,
    redact_prompt_command,
    run_subscription_agent_with_recovery,
)
from ztare.common.subscription_sessions import (
    default_subscription_runtime,
    get_or_create_warm_session,
    persist_warm_session,
    warm_session_recovery_callbacks,
)


AgentRunner = Callable[..., object]
LlmCall = Callable[[str], str]


@dataclass(frozen=True)
class DispatchResult:
    text: str
    capability: str
    transport: str
    worker_archetype: str
    returncode: int
    stderr: str = ""
    command: tuple[str, ...] = ()
    recovery_note: str | None = None
    agent_execution_mode: str = "none"
    run_role: str = EVALUATION


@dataclass(frozen=True)
class DispatchTextResponse:
    """Response-shaped wrapper for call sites that already parse ``response.text``."""

    text: str
    usage: Any = None
    model_id_used: str | None = None
    effective_model_id: str | None = None
    model_name: str | None = None
    dispatch_result: DispatchResult | None = None


def dispatch_result_receipt(call_site: str, result: DispatchResult) -> dict[str, Any]:
    """Return a small, prompt-free receipt for a completed worker dispatch."""

    command_head = result.command[0] if result.command else ""
    return {
        "call_site": call_site,
        "worker_capability": result.capability,
        "transport": result.transport,
        "worker_archetype": result.worker_archetype,
        "returncode": result.returncode,
        "completed": result.returncode == 0,
        "runtime": command_head or result.transport,
        "command_head": command_head,
        "recovery_note": result.recovery_note,
        "agent_execution_mode": result.agent_execution_mode,
    }


def dispatch_model(
    prompt: str,
    briefing: str | None = None,
    *,
    delta_prompt: str | None = None,
    capability: str = "llm",
    fungible: bool = True,
    stateful: bool = False,
    continuity_key: str | None = None,
    backend: str | None = None,
    llm_call: LlmCall | None = None,
    repo: str | Path = ".",
    agent_id: str = "autoresearch_mutator",
    timeout_seconds: int = 600,
    enabled_env: str = "ZTARE_AGENT_DISPATCH",
    agent_execution_mode: str = "sealed_completion",
    session_dir: str | Path | None = None,
    ask_specs: tuple[AskSpec, ...] = (),
    runner: AgentRunner = run_subscription_agent_with_recovery,
) -> DispatchResult:
    """Dispatch a model worker call.

    ``capability="llm"`` delegates to ``llm_call``. ``capability="agent"``
    requires the opt-in flag and uses the subscription-agent runtime. This
    function does not parse contracts; parsing belongs at the caller boundary.
    """
    capability = capability.strip().lower()
    if capability == "llm":
        if llm_call is None:
            raise ValueError("llm_call is required for capability='llm'")
        prompt = _compose_prompt_with_ask_specs(prompt, ask_specs)
        started = time.monotonic()
        text = llm_call(prompt)
        if _agent_trace_enabled():
            print(
                "agent dispatch end: "
                f"agent_id={agent_id} transport=api mode=api "
                f"elapsed_s={time.monotonic() - started:.1f} "
                f"prompt_chars={len(prompt)} stdout_chars={len(text or '')}",
                flush=True,
            )
        return DispatchResult(
            text=text,
            capability="llm",
            transport="api",
            worker_archetype="fungible_llm_call" if fungible else "persistent_llm_call",
            returncode=0,
            agent_execution_mode="api",
        )

    if capability != "agent":
        raise ValueError(f"unsupported capability: {capability}")
    if not _agent_dispatch_enabled(enabled_env):
        raise RuntimeError(f"agent dispatch disabled; set {enabled_env}=agent to opt in")
    if not fungible and not stateful:
        raise ValueError("non-fungible stateless worker is not a supported dispatch shape")

    runtime = backend or default_subscription_runtime("ZTARE_AUTORESEARCH_AGENT_RUNTIME")
    agent_execution_mode = _normalize_agent_execution_mode(agent_execution_mode)
    run_role = resolve_cegis_run_role(_dispatch_call_site(agent_id=agent_id, capability=capability))
    repo_path = Path(repo)
    dispatch_started = time.monotonic()
    phase_timings: dict[str, float] = {}
    _phase_started = time.monotonic()
    agent_prompt = _compose_agent_prompt(
        prompt,
        briefing,
        execution_mode=agent_execution_mode,
        ask_specs=ask_specs,
    )
    phase_timings["compose_prompt_s"] = round(time.monotonic() - _phase_started, 3)
    runner_repo: str | Path = repo
    visible_workbench_path: Path | None = None
    if agent_execution_mode == "visible_workbench":
        _phase_started = time.monotonic()
        pack = build_briefing_pack(
            BriefingPackRequest(
                repo=repo_path,
                agent_id=agent_id,
                task=prompt,
                briefing=briefing,
                context=agent_prompt,
                sealed_boundary_present=_repo_has_sealed_holdout(repo_path),
                run_role=run_role,
                ask_specs=ask_specs,
                tool_sources=_visible_workbench_tool_sources(repo_path),
            )
        )
        runner_repo = pack.workbench.resolve()
        visible_workbench_path = Path(runner_repo)
        agent_prompt = pack.entry_prompt
        phase_timings["build_visible_workbench_pack_s"] = round(time.monotonic() - _phase_started, 3)
    if runtime == "codex":
        _phase_started = time.monotonic()
        # ponytail: 340k chars is the empirically-proven-safe size for the
        # subscription worker. In visible-workbench mode this cap applies only
        # to the short entry prompt; TASK.md keeps the full staged task.
        _cap = _positive_int(os.environ.get("ZTARE_CODEX_AGENT_MAX_PROMPT_CHARS"), 340000)
        agent_prompt, _elided = _cap_codex_prompt(agent_prompt, _cap)
        if _elided:
            print(
                f"⚠️  codex prompt exceeded {_cap} chars — middle-elided {_elided} to fit "
                f"the model's context window (sealed worker; the deterministic gate still "
                f"sees full evidence). Tune ZTARE_CODEX_AGENT_MAX_PROMPT_CHARS."
            )
        phase_timings["cap_codex_prompt_s"] = round(time.monotonic() - _phase_started, 3)
    _phase_started = time.monotonic()
    prompt_debug_path = _persist_agent_prompt_debug(
        repo=repo,
        agent_id=agent_id,
        runtime=runtime,
        prompt=agent_prompt,
        stage="request",
    )
    phase_timings["persist_request_debug_s"] = round(time.monotonic() - _phase_started, 3)
    state = None
    state_dir: Path | None = None
    _phase_started = time.monotonic()
    if stateful:
        if not continuity_key:
            raise ValueError("continuity_key is required for stateful agent dispatch")
        state_dir = Path(session_dir or Path(repo) / ".ztare_agent_sessions")
        state = get_or_create_warm_session(
            state_dir,
            runtime=runtime,
            agent_id=continuity_key,
            enabled=True,
        )
        invalidate, replacement = warm_session_recovery_callbacks(
            state_dir,
            runtime=runtime,
            agent_id=continuity_key,
        )
    else:
        invalidate = None
        replacement = None
    phase_timings["prepare_session_s"] = round(time.monotonic() - _phase_started, 3)
    if (
        os.environ.get("ZTARE_VISIBLE_WORKBENCH_STRIKE_RESUME", "1") != "0"
        and state is not None
        and not state.get("is_new")
        and delta_prompt is not None
    ):
        agent_prompt = delta_prompt

    # CAPABILITY SEAL (2026-07-02, observed live): an unsealed autoresearch worker grepped
    # the repo, read evidence_holdout.txt (the hidden holdout), and ran the project's frozen
    # gate_harness.py as a local scoring oracle before submitting — voiding the sealed-run
    # premise. Autoresearch workers are bounded text workers: the briefing is their whole
    # world. Sealed is the default; ZTARE_AUTORESEARCH_AGENT_UNSEALED=1 is the explicit
    # escape hatch for externally-sandboxed boxes where repo access is intended.
    seal_kwargs: dict[str, Any] = {}
    if os.environ.get("ZTARE_AUTORESEARCH_AGENT_UNSEALED", "") != "1":
        if agent_execution_mode == "visible_workbench":
            seal_kwargs = {
                "claude_disallowed_tools": SEALED_CLAUDE_DISALLOWED_TOOLS,
                "codex_sandbox": CODEX_SANDBOX_VISIBLE_WORKBENCH,
            }
        else:
            seal_kwargs = {
                "claude_disallowed_tools": SEALED_CLAUDE_DISALLOWED_TOOLS,
                "codex_sandbox": CODEX_SANDBOX_SEALED_COMPLETION,
            }

    if _agent_trace_enabled():
        print(
            "agent dispatch start: "
            f"agent_id={agent_id} runtime={runtime} mode={agent_execution_mode} "
            f"run_role={run_role} "
            f"prompt_chars={len(agent_prompt)} cwd={Path(runner_repo)} "
            f"prompt_debug={prompt_debug_path or ''}",
            flush=True,
        )
    started = time.monotonic()
    run = runner(
        runtime=runtime,
        prompt=agent_prompt,
        agent_id=agent_id,
        repo=runner_repo,
        session_state=state,
        timeout_seconds=timeout_seconds,
        invalidate_session=invalidate,
        create_replacement_session=replacement,
        **seal_kwargs,
    )
    phase_timings["runner_subprocess_s"] = round(time.monotonic() - started, 3)
    result = getattr(run, "result", None)
    if not isinstance(result, subprocess.CompletedProcess):
        raise TypeError("agent runner must return an object with a CompletedProcess result")
    if visible_workbench_path is not None:
        _phase_started = time.monotonic()
        visible_receipt_sync = _sync_visible_workbench_receipts_to_repo(
            workbench=visible_workbench_path,
            repo=repo_path,
            response_text=result.stdout or "",
        )
        phase_timings["sync_visible_workbench_receipts_s"] = round(
            time.monotonic() - _phase_started,
            3,
        )
    else:
        visible_receipt_sync = {}
    elapsed = time.monotonic() - started
    if stateful and state_dir is not None and continuity_key:
        persist_warm_session(
            state_dir,
            runtime=runtime,
            agent_id=continuity_key,
            session_state=getattr(run, "final_session_state", None),
        )
    command = tuple(str(part) for part in getattr(run, "final_command", ()) or ())
    if prompt_debug_path is not None:
        _phase_started = time.monotonic()
        response_debug_phase_started = _phase_started
        phase_timings["persist_response_debug_s"] = 0.0
        phase_timings["dispatch_total_pre_response_debug_s"] = round(
            time.monotonic() - dispatch_started,
            3,
        )
        _persist_agent_response_debug(
            prompt_debug_path,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            returncode=int(result.returncode),
            command=tuple(redact_prompt_command(list(command), "<prompt>")) if command else (),
            elapsed_s=elapsed,
            dispatch_total_elapsed_s=time.monotonic() - dispatch_started,
            phase_timings_s=phase_timings,
            visible_workbench_path=visible_workbench_path,
            agent_execution_mode=agent_execution_mode,
            run_role=run_role,
            visible_receipt_sync=visible_receipt_sync,
        )
        phase_timings["persist_response_debug_s"] = round(
            time.monotonic() - response_debug_phase_started,
            3,
        )
    if _agent_trace_enabled():
        print(
            "agent dispatch end: "
            f"agent_id={agent_id} runtime={runtime} mode={agent_execution_mode} "
            f"run_role={run_role} "
            f"rc={int(result.returncode)} elapsed_s={elapsed:.1f} "
            f"stdout_chars={len(result.stdout or '')} stderr_chars={len(result.stderr or '')} "
            f"workbench_receipts={_visible_workbench_receipt_count(visible_workbench_path)} "
            f"phases={phase_timings}",
            flush=True,
        )
    return DispatchResult(
        text=result.stdout or "",
        capability="agent",
        transport="subscription_cli",
        worker_archetype="fungible_agent_worker" if fungible else "persistent_agent_worker",
        returncode=int(result.returncode),
        stderr=result.stderr or "",
        command=command,
        recovery_note=getattr(run, "recovery_note", None),
        agent_execution_mode=agent_execution_mode,
        run_role=run_role,
    )


def _agent_prompt_debug_enabled() -> bool:
    return os.environ.get("ZTARE_AGENT_PROMPT_DEBUG", "1") not in {"0", "false", "False"}


def _agent_trace_enabled() -> bool:
    return os.environ.get("ZTARE_AGENT_TRACE", "1") not in {"0", "false", "False"}


def _persist_agent_prompt_debug(
    *,
    repo: str | Path,
    agent_id: str,
    runtime: str,
    prompt: str,
    stage: str,
) -> Path | None:
    if not _agent_prompt_debug_enabled():
        return None
    try:
        root = Path(os.environ.get("ZTARE_AGENT_PROMPT_DEBUG_DIR") or Path(repo) / "workspace" / "agent_prompt_debug")
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        safe_agent = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in agent_id)[:80]
        digest = hashlib.sha256(prompt.encode("utf-8", errors="ignore")).hexdigest()[:12]
        path = root / f"{stamp}_{safe_agent}_{runtime}_{digest}.{stage}.txt"
        path.write_text(prompt, encoding="utf-8")
        meta = {
            "schema": "ztare-agent-prompt-debug-v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "runtime": runtime,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8", errors="ignore")).hexdigest(),
            "prompt_chars": len(prompt),
            "prompt_path": str(path),
        }
        path.with_suffix(".meta.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
    except Exception:
        return None


def _persist_agent_response_debug(
    prompt_path: Path,
    *,
    stdout: str,
    stderr: str,
    returncode: int,
    command: tuple[str, ...],
    elapsed_s: float | None = None,
    dispatch_total_elapsed_s: float | None = None,
    phase_timings_s: dict[str, float] | None = None,
    visible_workbench_path: Path | None = None,
    agent_execution_mode: str = "none",
    run_role: str = EVALUATION,
    visible_receipt_sync: dict[str, Any] | None = None,
) -> None:
    try:
        debug_started = time.monotonic()
        response_path = prompt_path.with_suffix(".response.txt")
        response_path.write_text(stdout, encoding="utf-8")
        stderr_path = prompt_path.with_suffix(".stderr.txt")
        if stderr:
            stderr_path.write_text(stderr, encoding="utf-8")
        meta_path = prompt_path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        meta.update({
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "returncode": returncode,
            "response_path": str(response_path),
            "response_chars": len(stdout),
            "stderr_path": str(stderr_path) if stderr else "",
            "stderr_chars": len(stderr),
            "command": list(command),
            "agent_execution_mode": agent_execution_mode,
            "run_role": run_role,
        })
        if elapsed_s is not None:
            meta["elapsed_s"] = round(float(elapsed_s), 3)
        if dispatch_total_elapsed_s is not None:
            meta["dispatch_total_elapsed_s"] = round(float(dispatch_total_elapsed_s), 3)
        phase_payload: dict[str, float] = {}
        if phase_timings_s:
            phase_payload = {
                str(key): round(float(value), 3)
                for key, value in phase_timings_s.items()
            }
        workbench = _visible_workbench_telemetry(visible_workbench_path)
        if workbench:
            meta["visible_workbench"] = workbench
        if visible_receipt_sync:
            meta["visible_receipt_sync"] = visible_receipt_sync
        if phase_payload:
            phase_payload["persist_response_debug_s"] = round(time.monotonic() - debug_started, 3)
            meta["phase_timings_s"] = phase_payload
            meta["phase_timings"] = phase_payload
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        return


def _visible_workbench_receipt_count(workbench: Path | None) -> int:
    if workbench is None:
        return 0
    receipts_dir = workbench / "workspace" / "visible_cli_receipts"
    try:
        return sum(1 for path in receipts_dir.glob("*.json") if path.is_file())
    except OSError:
        return 0


def _sync_visible_workbench_receipts_to_repo(
    *,
    workbench: Path,
    repo: Path,
    response_text: str = "",
) -> dict[str, Any]:
    """Make staged visible-workbench artifact refs durable in the authority project."""

    src_root = workbench / "workspace" / "visible_cli_receipts"
    authority_project = visible_workbench_authority_project(workbench, fallback=repo)
    dst_root = authority_project / "workspace" / "visible_cli_receipts"
    artifact_copied = 0
    artifact_skipped = 0
    artifact_errors: list[str] = []
    if not src_root.is_dir():
        receipt_result = {"copied": 0, "skipped": 0, "errors": []}
    else:
        receipt_result = _copy_tree_files(src_root, dst_root)
    artifact_refs = tuple(
        dict.fromkeys(
            (
                *collect_artifact_refs_from_text(response_text),
                *_artifact_refs_from_receipts(src_root),
            )
        )
    )
    for ref in artifact_refs:
        if not project_ref_requires_resolution(ref) or ref.startswith("workspace/visible_cli_receipts/"):
            continue
        src = (workbench / ref).resolve()
        dst = (authority_project / ref).resolve()
        try:
            src.relative_to(workbench.resolve())
            dst.relative_to(authority_project.resolve())
        except ValueError:
            continue
        if not src.is_file():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src_bytes = src.read_bytes()
            if dst.exists() and dst.read_bytes() == src_bytes:
                artifact_skipped += 1
                continue
            shutil.copy2(src, dst)
            artifact_copied += 1
        except OSError as exc:
            artifact_errors.append(f"{ref}: {exc}")
    return {
        "project": str(authority_project),
        "copied": receipt_result["copied"],
        "skipped": receipt_result["skipped"],
        "errors": receipt_result["errors"],
        "artifact_copied": artifact_copied,
        "artifact_skipped": artifact_skipped,
        "artifact_errors": artifact_errors[:8],
    }


def _artifact_refs_from_receipts(src_root: Path) -> tuple[str, ...]:
    refs: list[str] = []
    if not src_root.is_dir():
        return ()
    for path in sorted(src_root.glob("*.json")):
        if not path.is_file():
            continue
        try:
            refs.extend(collect_artifact_refs_from_text(path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return tuple(dict.fromkeys(refs))


def _copy_tree_files(src_root: Path, dst_root: Path) -> dict[str, Any]:
    copied = 0
    skipped = 0
    errors: list[str] = []
    try:
        dst_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"copied": 0, "skipped": 0, "errors": [str(exc)]}
    for src in sorted(src_root.glob("*.json")):
        if not src.is_file():
            continue
        dst = dst_root / src.name
        try:
            src_bytes = src.read_bytes()
            if dst.exists() and dst.read_bytes() == src_bytes:
                skipped += 1
                continue
            shutil.copy2(src, dst)
            copied += 1
        except OSError as exc:
            errors.append(f"{src.name}: {exc}")
    return {"copied": copied, "skipped": skipped, "errors": errors[:8]}

def _visible_workbench_telemetry(workbench: Path | None) -> dict[str, Any]:
    if workbench is None:
        return {}
    telemetry: dict[str, Any] = {
        "path": str(workbench),
    }
    try:
        manifest_path = workbench / "MANIFEST.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            telemetry["manifest_bytes"] = manifest_path.stat().st_size
            files = manifest.get("pack_files") if isinstance(manifest, dict) else None
            if isinstance(files, list):
                telemetry["pack_files"] = len(files)
                telemetry["pack_bytes"] = sum(
                    int(row.get("bytes") or 0)
                    for row in files
                    if isinstance(row, dict)
                )
        for rel in ("TASK.md", "ATTENTION.md", "RECORDS.json", "CONTEXT.md", "WORKBENCH_TOOLS.md"):
            path = workbench / rel
            if path.is_file():
                telemetry[f"{rel.lower().replace('.', '_')}_bytes"] = path.stat().st_size
        receipts_dir = workbench / "workspace" / "visible_cli_receipts"
        receipts: list[dict[str, Any]] = []
        for path in sorted(receipts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            receipts.append(
                {
                    "ref": str(path.relative_to(workbench)),
                    "command": str(payload.get("command") or payload.get("capability_id") or ""),
                    "status": str(payload.get("status") or ""),
                    "duration_ms": payload.get("duration_ms"),
                    "bytes": path.stat().st_size,
                    "mtime": path.stat().st_mtime,
                }
            )
        telemetry["visible_receipt_count"] = len(receipts)
        telemetry["visible_receipt_bytes"] = sum(int(row["bytes"]) for row in receipts)
        telemetry["visible_receipt_commands"] = _count_by_key(receipts, "command")
        durations = [
            float(row["duration_ms"])
            for row in receipts
            if isinstance(row.get("duration_ms"), (int, float))
        ]
        if durations:
            telemetry["visible_receipt_duration_ms_total"] = round(sum(durations), 3)
            telemetry["visible_receipt_duration_ms_max"] = round(max(durations), 3)
        if receipts:
            telemetry["visible_receipt_mtime_span_s"] = round(
                max(float(row["mtime"]) for row in receipts)
                - min(float(row["mtime"]) for row in receipts),
                3,
            )
            telemetry["latest_visible_receipts"] = [
                {key: row[key] for key in ("ref", "command", "status", "duration_ms", "bytes")}
                for row in receipts[-8:]
            ]
    except OSError:
        telemetry["status"] = "unavailable"
    return telemetry


def _count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def resolve_dispatch_capability(
    call_site: str,
    *,
    default: str = "llm",
    env_var: str = "ZTARE_AGENT_DISPATCH",
) -> str:
    """Resolve the capability for a call site from environment policy.

    Supported values:
    - ``ZTARE_AGENT_DISPATCH=off`` or unset: default capability.
    - ``ZTARE_AGENT_DISPATCH=agent``: generic opt-in.
    - ``ZTARE_AGENT_DISPATCH_MUTATOR=agent``: per-call-site opt-in.

    Per-call-site env vars win over the generic env var. This helper only
    resolves policy; the downstream call still validates typed contracts.
    """
    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    scoped_value = os.environ.get(f"{env_var}_{site_key}")
    if scoped_value is not None:
        return _capability_from_env(scoped_value, default=default)
    return _capability_from_env(os.environ.get(env_var), default=default)


def dispatch_env_for_call_site(call_site: str, *, env_var: str = "ZTARE_AGENT_DISPATCH") -> str:
    """Return the env var that should authorize this call site's dispatch.

    When a scoped env var is set, use it. Otherwise the generic env var controls
    dispatch. This mirrors ``resolve_dispatch_capability`` so callers do not
    accidentally resolve from one env var and authorize against another.
    """
    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    scoped = f"{env_var}_{site_key}"
    if os.environ.get(scoped) is not None:
        return scoped
    return env_var


def resolve_agent_timeout_seconds(call_site: str, *, default: int) -> int:
    """Resolve an agent timeout for one autoresearch call site.

    Scoped env vars let a slow committee or mutator get its own budget without
    weakening every other subscription-backed worker.
    """

    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    candidates = (
        f"ZTARE_AUTORESEARCH_{site_key}_AGENT_TIMEOUT_SECONDS",
        "ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS",
    )
    for name in candidates:
        raw = os.environ.get(name)
        if raw is None or not raw.strip():
            continue
        try:
            parsed = int(raw)
        except ValueError:
            continue
        if parsed > 0:
            return parsed
    return max(1, _positive_int(default, 1))


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return max(1, int(default))
    return parsed if parsed > 0 else max(1, int(default))


def resolve_agent_execution_mode(call_site: str, *, default: str | None = None) -> str:
    """Resolve whether a subscription worker is a sealed completion or visible workbench."""

    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    candidates = (
        f"ZTARE_AUTORESEARCH_{site_key}_AGENT_EXECUTION_MODE",
        "ZTARE_AUTORESEARCH_AGENT_EXECUTION_MODE",
    )
    for name in candidates:
        raw = os.environ.get(name)
        if raw is None or not raw.strip():
            continue
        return _normalize_agent_execution_mode(raw)
    if default is None:
        default = _default_agent_execution_mode_for_call_site(call_site)
    return _normalize_agent_execution_mode(default)


def resolve_cegis_run_role(call_site: str, *, default: str | None = None) -> str:
    site_key = "".join(ch if ch.isalnum() else "_" for ch in str(call_site).upper()).strip("_")
    candidates = (
        f"ZTARE_AUTORESEARCH_{site_key}_CEGIS_RUN_ROLE",
        "ZTARE_AUTORESEARCH_CEGIS_RUN_ROLE",
        "ZTARE_CEGIS_RUN_ROLE",
    )
    for name in candidates:
        raw = os.environ.get(name)
        if raw is not None and raw.strip():
            return _normalize_cegis_run_role(raw)
    if default is None:
        default = DISCOVERY if call_site == "mutator" else EVALUATION
    return _normalize_cegis_run_role(default)


def _dispatch_call_site(*, agent_id: str, capability: str) -> str:
    lowered = str(agent_id or "").lower()
    if lowered.startswith("autoresearch_mutator_") or lowered.startswith("mutator"):
        return "mutator"
    if lowered.startswith("autoresearch_judge_") or lowered.startswith("judge"):
        return "judge"
    return capability


def _default_agent_execution_mode_for_call_site(call_site: str) -> str:
    site = "".join(ch if ch.isalnum() else "_" for ch in str(call_site).lower()).strip("_")
    if site == "mutator":
        return "visible_workbench"
    return "sealed_completion"


def _normalize_cegis_run_role(value: str | None) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "SCIENCE": DISCOVERY,
        "DISCOVERY": DISCOVERY,
        "CEGIS": DISCOVERY,
        "HARNESS_DEBUG": HARNESS_DEBUG,
        "DEBUG": HARNESS_DEBUG,
        "EVAL": EVALUATION,
        "EVALUATION": EVALUATION,
    }
    if text not in aliases:
        raise ValueError(f"unsupported CEGIS run role: {value!r}")
    return aliases[text]


def _capability_from_env(value: str | None, *, default: str) -> str:
    normalized = (value or "off").strip().lower()
    if normalized in {"1", "true", "on", "agent"}:
        return "agent"
    if normalized in {"llm", "api", "off", "0", "false", ""}:
        return default
    raise ValueError(f"unsupported dispatch capability env value: {value!r}")


def _agent_dispatch_enabled(env_var: str) -> bool:
    return os.environ.get(env_var, "off").strip().lower() in {"1", "true", "on", "agent"}


def _normalize_agent_execution_mode(value: str | None) -> str:
    normalized = (value or "sealed_completion").strip().lower().replace("-", "_")
    aliases = {
        "sealed": "sealed_completion",
        "completion": "sealed_completion",
        "sealed_completion": "sealed_completion",
        "typed": "sealed_completion",
        "typed_workbench": "sealed_completion",
        "visible": "visible_workbench",
        "visible_workbench": "visible_workbench",
        "read_only_shell": "visible_workbench",
        "readonly_shell": "visible_workbench",
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported agent execution mode: {value!r}")
    return aliases[normalized]


def _repo_has_sealed_holdout(repo: Path) -> bool:
    """Return True when a command-enabled worker would see sealed evaluator data."""

    try:
        if not repo.exists():
            return False
        if (repo / "evidence_holdout.txt").exists() or (repo / "sealed_holdout.json").exists():
            return True
        # Guard repo-root dispatches without scanning the whole tree. ARC/prose projects keep
        # sealed holdouts one project level down; a staged visible workspace should not.
        for child in repo.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            if (child / "evidence_holdout.txt").exists() or (child / "sealed_holdout.json").exists():
                return True
        projects_dir = repo / "projects"
        if projects_dir.is_dir():
            for child in projects_dir.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if (child / "evidence_holdout.txt").exists() or (child / "sealed_holdout.json").exists():
                    return True
    except OSError:
        return False
    return False


def _visible_workbench_tool_sources(repo: Path) -> tuple[ToolSource, ...]:
    root = Path(__file__).resolve().parents[3]
    sources: list[ToolSource] = []
    seen: set[str] = set()
    for ref in VISIBLE_WORKBENCH_SOURCE_REFS:
        if ref in seen:
            continue
        seen.add(ref)
        source = root / ref
        if source.is_file():
            sources.append(ToolSource(ref, source))
    return tuple(sources)


def _compose_agent_prompt(
    prompt: str,
    briefing: str | None,
    *,
    execution_mode: str = "sealed_completion",
    ask_specs: tuple[AskSpec, ...] = (),
) -> str:
    mode = _normalize_agent_execution_mode(execution_mode)
    if mode == "visible_workbench":
        workbench_text = visible_workbench_contract_text() + "\n\n"
    else:
        workbench_text = (
            "You are running in a sealed completion workbench. Direct local tools "
            "may be unavailable; do not claim you inspected files or ran commands "
            "unless a receipt is present. If you need a visible probe or an "
            "authority-bearing observation, request it via the typed workbench "
            "action contract so the kernel can execute it and return a receipt.\n\n"
        )
    preamble = (
        "You are a bounded worker called by an automated parser. Return the typed "
        "contract requested by the caller in your final answer. Do not replace the "
        "contract with a summary, file list, status note, or description of edits. "
        "Do not write or modify repository files unless the task explicitly asks "
        "for file edits; most dispatch calls are stdout-only.\n\n"
        f"{workbench_text}"
    )
    task = _compose_prompt_with_ask_specs(prompt, ask_specs)
    if not briefing:
        return preamble + "=== TASK ===\n" + task
    return (
        preamble
        + "Use the briefing as externalized state.\n\n"
        "=== EXTERNALIZED BRIEFING ===\n"
        f"{briefing.rstrip()}\n\n"
        "=== TASK ===\n"
        f"{task}"
    )


def _compose_prompt_with_ask_specs(prompt: str, ask_specs: tuple[AskSpec, ...]) -> str:
    if not ask_specs:
        return prompt
    section = "\n\n".join(render_ask_spec_markdown(spec).rstrip() for spec in ask_specs)
    return f"=== ASK CONTRACTS ===\n{section}\n\n=== TASK BODY ===\n{prompt}"


def _cap_codex_prompt(prompt: str, max_chars: int, *, tail_keep: int = 6000) -> tuple[str, int]:
    """Middle-elide an oversized codex prompt so it fits the model's context window.

    `codex exec` wraps the prompt in its own agent harness (~17k tokens of
    overhead even for a one-word prompt) and reserves output/compaction room, so a
    large single-shot briefing overflows the window and codex aborts the turn with
    0 tokens and returncode=1. We keep the HEAD (persona/axioms/thesis) and the
    TAIL (the appended JSON response contract) and drop the middle of the evidence.
    Returns (possibly-trimmed prompt, chars elided). Caller prints on elision — the
    trim is loud, not silent.
    """
    if len(prompt) <= max_chars:
        return prompt, 0
    elided = len(prompt) - max_chars
    tail_keep = min(tail_keep, max(0, max_chars // 2))  # never let the tail slice exceed the budget
    head = prompt[: max_chars - tail_keep]
    tail = prompt[-tail_keep:] if tail_keep else ""
    return (
        head
        + f"\n\n… [{elided} chars elided to fit the sealed codex worker's context window] …\n\n"
        + tail
    ), elided


def dispatch_call_text(
    call_site: str,
    prompt: str,
    *,
    llm_response_call: Callable[[str], Any],
    briefing: str | None = None,
    fungible: bool = True,
    stateful: bool = False,
    continuity_key: str | None = None,
    backend: str | None = None,
    repo: str | Path = ".",
    agent_id: str | None = None,
    timeout_seconds: int = 600,
    enabled_env: str | None = None,
    runner: AgentRunner = run_subscription_agent_with_recovery,
) -> DispatchTextResponse:
    """Run an existing ``LLMRuntime.call_text`` site through optional dispatch.

    The API path calls ``llm_response_call`` and preserves common response
    metadata. The agent path returns a response-shaped wrapper with stdout as
    ``text`` so existing JSON/text parsers keep owning validation.
    """
    capability = resolve_dispatch_capability(call_site)
    if capability == "llm":
        response = llm_response_call(prompt)
        return DispatchTextResponse(
            text=str(getattr(response, "text", "") or getattr(response, "content", "") or response or ""),
            usage=getattr(response, "usage", None),
            model_id_used=getattr(response, "model_id_used", None),
            effective_model_id=getattr(response, "effective_model_id", None),
            model_name=getattr(response, "model_name", None),
            dispatch_result=DispatchResult(
                text=str(getattr(response, "text", "") or getattr(response, "content", "") or response or ""),
                capability="llm",
                transport="api",
                worker_archetype="fungible_llm_call" if fungible else "persistent_llm_call",
                returncode=0,
            ),
        )

    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    runtime = (
        backend
        or os.environ.get(f"ZTARE_AUTORESEARCH_{site_key}_AGENT_RUNTIME")
        or default_subscription_runtime("ZTARE_AUTORESEARCH_AGENT_RUNTIME")
    )
    result = dispatch_model(
        prompt,
        briefing,
        capability=capability,
        fungible=fungible,
        stateful=stateful,
        continuity_key=continuity_key,
        backend=runtime,
        llm_call=None,
        repo=repo,
        agent_id=agent_id or f"autoresearch_{site_key.lower()}",
        timeout_seconds=resolve_agent_timeout_seconds(call_site, default=timeout_seconds),
        enabled_env=enabled_env or dispatch_env_for_call_site(call_site),
        agent_execution_mode=resolve_agent_execution_mode(call_site),
        runner=runner,
    )
    return DispatchTextResponse(
        text=result.text,
        usage=None,
        model_id_used=runtime,
        effective_model_id=runtime,
        model_name=runtime,
        dispatch_result=result,
    )
