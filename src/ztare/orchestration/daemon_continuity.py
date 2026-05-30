"""Daemon continuity primitives: cross-tick session resume + per-task checkpoint.

This module is the implementation for two related but distinct mechanisms used
by `scripts/public/control/agent_daemon.py` to make dockerized agents productive across
ticks:

1. **Cross-tick session resume** — preserves Claude Code's conversation
   memory between ticks so the agent doesn't rebuild context from scratch
   every 5–20 minutes. The daemon keeps a per-role `claude_session_id` and
   passes it via `--session-id` (first use) / `--resume` (subsequent uses)
   to the spawned `claude --print` subprocess. Codex's `codex exec`
   subcommand does not support resume; the codex_exec adapter is unaffected.

2. **Per-task state checkpoint** — on top of resume, writes a small JSON
   file under `org/sessions/<session_id>/state.json` summarizing what the
   tick just did. Read at the start of the next tick so even if the
   process crashes (or the resume target session is missing) the agent
   knows where it left off.

The two compose: resume gives in-conversation memory; checkpoint gives
crash-resilience and is the canonical "I'm a daemon, where was I" surface.

Session-reset policy:
    The Claude session is rotated when it gets stale, to prevent unbounded
    conversation growth. Stale = `tick_count >= max_ticks` or
    `age_hours >= max_age_hours`. On reset, a fresh UUID is generated and
    written to disk; the next tick uses --session-id (first use) again.

Sister mechanisms:
    - `org/sessions/` — org-level session IDs (role + member identity);
      separate concern from Claude Code's conversation IDs.
    - `org/bootstrap_manifest.yaml` — what every spawned agent reads on
      cold start; resume sidesteps the cold-start cost.
    - `analytics/public/queries/rd/decision_history_calibration.md` — empirical case
      for why broader continuity is needed (60% of decisions are
      agent-driven; rebuilding context every tick is wasteful).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSIONS_ROOT = REPO_ROOT / "org" / "sessions"
DAEMON_SESSION_DIRNAME = "daemon"


# Defaults; the daemon may override these via env or --flag.
DEFAULT_MAX_TICKS = 100
DEFAULT_MAX_AGE_HOURS = 24


@dataclass
class DaemonSessionState:
    role_id: str
    claude_session_id: str
    started_at: str
    last_tick_at: str
    tick_count: int
    is_new: bool = False  # True on the tick where the session was created/reset

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("is_new", None)  # is_new is per-call, not persisted
        return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _state_path(role_id: str) -> Path:
    """Path to the persisted daemon session state for this role."""
    out = SESSIONS_ROOT / DAEMON_SESSION_DIRNAME / f"{role_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def _is_stale(state: dict, max_ticks: int, max_age_hours: int) -> bool:
    """Return True if the persisted session should be rotated."""
    if state.get("tick_count", 0) >= max_ticks:
        return True
    started_at = state.get("started_at")
    if not started_at:
        return True
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return True
    age = datetime.now(timezone.utc) - started
    if age >= timedelta(hours=max_age_hours):
        return True
    return False


def get_or_create_claude_session_id(
    role_id: str,
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> DaemonSessionState:
    """Return the active Claude session for this role, creating or rotating
    if missing/stale.

    The daemon should call this once per tick and pass the returned uuid
    to the agent CLI invocation:
        - If `is_new` is True → spawn with `--session-id <uuid>` (Claude
          will create a new conversation with this id).
        - If `is_new` is False → spawn with `--resume <uuid>` (Claude will
          load prior conversation history before processing this tick's
          prompt).
    """
    path = _state_path(role_id)
    if path.exists():
        try:
            state = json.loads(path.read_text())
        except json.JSONDecodeError:
            state = {}
        if state.get("claude_session_id") and not _is_stale(state, max_ticks, max_age_hours):
            # Reuse existing session; not a first-use tick.
            return DaemonSessionState(
                role_id=role_id,
                claude_session_id=state["claude_session_id"],
                started_at=state.get("started_at") or _now_iso(),
                last_tick_at=state.get("last_tick_at") or _now_iso(),
                tick_count=int(state.get("tick_count", 0)),
                is_new=False,
            )

    # Either no state, corrupt state, or stale → mint a fresh session.
    new_id = str(uuid.uuid4())
    now = _now_iso()
    fresh = DaemonSessionState(
        role_id=role_id,
        claude_session_id=new_id,
        started_at=now,
        last_tick_at=now,
        tick_count=0,
        is_new=True,
    )
    path.write_text(json.dumps(fresh.to_dict(), indent=2))
    return fresh


def note_tick(role_id: str, *, success: bool | None = None, summary: str | None = None) -> None:
    """Record that a tick completed. Increments tick_count + updates timestamp.

    Optional `summary` is appended to a per-role tick-log so a human can
    audit what's happening across ticks without diffing the persistent
    state. Bounded to last 50 entries.
    """
    path = _state_path(role_id)
    if not path.exists():
        return  # nothing to update; resume will create on next tick
    try:
        state = json.loads(path.read_text())
    except json.JSONDecodeError:
        return
    state["tick_count"] = int(state.get("tick_count", 0)) + 1
    state["last_tick_at"] = _now_iso()
    if success is not None:
        state["last_tick_success"] = bool(success)
    if summary:
        log = state.get("tick_log") or []
        log.append({"ts": _now_iso(), "summary": summary[:200], "success": success})
        state["tick_log"] = log[-50:]
    path.write_text(json.dumps(state, indent=2))


def reset_session(role_id: str) -> str:
    """Force-rotate the session id for this role. Returns the new uuid."""
    path = _state_path(role_id)
    new_id = str(uuid.uuid4())
    now = _now_iso()
    fresh = {
        "role_id": role_id,
        "claude_session_id": new_id,
        "started_at": now,
        "last_tick_at": now,
        "tick_count": 0,
    }
    path.write_text(json.dumps(fresh, indent=2))
    return new_id


# ── Per-task checkpoint ───────────────────────────────────────────────


def _checkpoint_path(session_id: str) -> Path:
    """Path to the per-org-session checkpoint state."""
    out = SESSIONS_ROOT / session_id / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def write_task_checkpoint(
    session_id: str,
    *,
    claimed_id: str | None,
    task_intent: str | None,
    status: str,
    last_summary: str | None = None,
    extra: dict | None = None,
) -> None:
    """Write the per-tick checkpoint to org/sessions/<session_id>/state.json.

    Status is one of: claimed, executing, completed, failed, no_work.

    First action of each tick should call `read_task_checkpoint(session_id)`
    so the agent has its prior tick's conclusion available. Last action of
    each tick should write a fresh checkpoint reflecting what just happened.
    """
    payload = {
        "ts": _now_iso(),
        "session_id": session_id,
        "claimed_id": claimed_id,
        "task_intent": task_intent[:300] if task_intent else None,
        "status": status,
        "last_summary": last_summary[:1000] if last_summary else None,
    }
    if extra:
        payload["extra"] = extra
    _checkpoint_path(session_id).write_text(json.dumps(payload, indent=2))


def read_task_checkpoint(session_id: str) -> dict | None:
    """Return the prior tick's checkpoint, or None if absent/unreadable."""
    path = _checkpoint_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
