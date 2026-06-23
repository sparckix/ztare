"""Shared subscription-agent selection and warm-session persistence.

This module intentionally contains no CLI command policy. It is safe for
generic dispatch code to depend on it without pulling in runtime-specific
Codex or Claude command changes.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from ztare.common.subscription_agent_runtime import SUPPORTED_SUBSCRIPTION_RUNTIMES


SUBSCRIPTION_SESSION_SCHEMA = "ztare-subscription-agent-session-v1"
DEFAULT_WARM_MAX_TASKS = 20
DEFAULT_WARM_MAX_AGE_S = 6 * 60 * 60


def default_subscription_runtime(env_var: str = "ZTARE_AGENT_RUNTIME") -> str:
    """Resolve a subscription runtime from scoped env, global env, then codex."""

    runtime = (os.environ.get(env_var) or "").strip().lower()
    if runtime in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        return runtime
    global_runtime = (os.environ.get("ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME") or "").strip().lower()
    if global_runtime in SUPPORTED_SUBSCRIPTION_RUNTIMES:
        return global_runtime
    return "codex"


def session_slug(value: str) -> str:
    """Return a filesystem-safe slug for a runtime or continuity key."""

    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "agent"


def warm_session_path(session_dir: str | Path, *, runtime: str, agent_id: str) -> Path:
    return Path(session_dir) / f"{session_slug(runtime)}_{session_slug(agent_id)}.json"


def _read_session_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return {}
    return obj if isinstance(obj, dict) else {}


def get_or_create_warm_session(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    enabled: bool = True,
    warm_max_tasks: int = DEFAULT_WARM_MAX_TASKS,
    warm_max_age_s: int = DEFAULT_WARM_MAX_AGE_S,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Load or create a durable warm session for a subscription-backed worker."""

    if not enabled:
        return None
    path = warm_session_path(session_dir, runtime=runtime, agent_id=agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _read_session_json(path)
    now_epoch = int(time.time() if now is None else now)
    stale = True
    if state.get("session_id") and state.get("started_at_epoch"):
        age_s = now_epoch - int(state.get("started_at_epoch") or now_epoch)
        stale = int(state.get("tick_count") or 0) >= warm_max_tasks or age_s >= warm_max_age_s
    if stale:
        state = {
            "schema": SUBSCRIPTION_SESSION_SCHEMA,
            "runtime": runtime,
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()) if runtime == "claude" else None,
            "started_at_epoch": now_epoch,
            "last_used_at_epoch": None,
            "tick_count": 0,
            "is_new": True,
            "policy": "session_warm_resume_if_supported",
        }
        path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    else:
        state["is_new"] = False
    state["session_state_path"] = str(path)
    return state


def persist_warm_session(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    session_state: dict[str, Any] | None,
    now: int | None = None,
) -> None:
    """Persist final session metadata so the next worker can resume."""

    if not session_state:
        return
    path = warm_session_path(session_dir, runtime=runtime, agent_id=agent_id)
    state = {k: v for k, v in dict(session_state).items() if k != "session_state_path"}
    state.setdefault("schema", SUBSCRIPTION_SESSION_SCHEMA)
    state["runtime"] = runtime
    state["agent_id"] = agent_id
    state["is_new"] = False
    state["last_used_at_epoch"] = int(time.time() if now is None else now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def warm_session_recovery_callbacks(
    session_dir: str | Path,
    *,
    runtime: str,
    agent_id: str,
    warm_max_tasks: int = DEFAULT_WARM_MAX_TASKS,
    warm_max_age_s: int = DEFAULT_WARM_MAX_AGE_S,
) -> tuple[Callable[[str], None], Callable[[], dict[str, Any]]]:
    """Return invalidation and replacement callbacks for runner recovery."""

    def _invalidate(reason: str) -> None:
        persist_warm_session(
            session_dir,
            runtime=runtime,
            agent_id=agent_id,
            session_state={
                "schema": SUBSCRIPTION_SESSION_SCHEMA,
                "runtime": runtime,
                "agent_id": agent_id,
                "session_id": None,
                "is_new": True,
                "invalidated_reason": reason,
                "started_at_epoch": int(time.time()),
                "tick_count": 0,
            },
        )

    def _replacement() -> dict[str, Any]:
        return get_or_create_warm_session(
            session_dir,
            runtime=runtime,
            agent_id=agent_id,
            enabled=True,
            warm_max_tasks=warm_max_tasks,
            warm_max_age_s=warm_max_age_s,
        ) or {}

    return _invalidate, _replacement
