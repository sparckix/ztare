"""Capability-aware worker dispatch.

This is a thin resolver, not a new orchestrator. It routes a worker call along
the explicit axes captured in GP-249: capability, state, identity/fungibility,
and transport. The default path remains the caller's existing LLM function.
Agent dispatch is opt-in via ``ZTARE_AGENT_DISPATCH`` and returns raw text for
the call site to parse through its existing typed-contract validator.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery
from src.ztare.common.subscription_sessions import (
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
    }


def dispatch_model(
    prompt: str,
    briefing: str | None = None,
    *,
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
    session_dir: str | Path | None = None,
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
        text = llm_call(prompt)
        return DispatchResult(
            text=text,
            capability="llm",
            transport="api",
            worker_archetype="fungible_llm_call" if fungible else "persistent_llm_call",
            returncode=0,
        )

    if capability != "agent":
        raise ValueError(f"unsupported capability: {capability}")
    if not _agent_dispatch_enabled(enabled_env):
        raise RuntimeError(f"agent dispatch disabled; set {enabled_env}=agent to opt in")
    if not fungible and not stateful:
        raise ValueError("non-fungible stateless worker is not a supported dispatch shape")

    runtime = backend or default_subscription_runtime("ZTARE_AUTORESEARCH_AGENT_RUNTIME")
    agent_prompt = _compose_agent_prompt(prompt, briefing)
    state = None
    state_dir: Path | None = None
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

    run = runner(
        runtime=runtime,
        prompt=agent_prompt,
        agent_id=agent_id,
        repo=repo,
        session_state=state,
        timeout_seconds=timeout_seconds,
        invalidate_session=invalidate,
        create_replacement_session=replacement,
    )
    result = getattr(run, "result", None)
    if not isinstance(result, subprocess.CompletedProcess):
        raise TypeError("agent runner must return an object with a CompletedProcess result")
    if stateful and state_dir is not None and continuity_key:
        persist_warm_session(
            state_dir,
            runtime=runtime,
            agent_id=continuity_key,
            session_state=getattr(run, "final_session_state", None),
        )
    command = tuple(str(part) for part in getattr(run, "final_command", ()) or ())
    return DispatchResult(
        text=result.stdout or "",
        capability="agent",
        transport="subscription_cli",
        worker_archetype="fungible_agent_worker" if fungible else "persistent_agent_worker",
        returncode=int(result.returncode),
        stderr=result.stderr or "",
        command=command,
        recovery_note=getattr(run, "recovery_note", None),
    )


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
    return max(1, int(default))


def _capability_from_env(value: str | None, *, default: str) -> str:
    normalized = (value or "off").strip().lower()
    if normalized in {"1", "true", "on", "agent"}:
        return "agent"
    if normalized in {"llm", "api", "off", "0", "false", ""}:
        return default
    raise ValueError(f"unsupported dispatch capability env value: {value!r}")


def _agent_dispatch_enabled(env_var: str) -> bool:
    return os.environ.get(env_var, "off").strip().lower() in {"1", "true", "on", "agent"}


def _compose_agent_prompt(prompt: str, briefing: str | None) -> str:
    if not briefing:
        return prompt
    return (
        "You are a bounded tool-using worker. Use the briefing as externalized state; "
        "return only the typed contract requested by the caller.\n\n"
        "=== EXTERNALIZED BRIEFING ===\n"
        f"{briefing.rstrip()}\n\n"
        "=== TASK ===\n"
        f"{prompt}"
    )


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
