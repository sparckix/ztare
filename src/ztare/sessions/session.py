# SPDX-License-Identifier: MIT
"""Per-(member, role, substrate, time) session artifact.

A session is opened when a member starts acting in a role and closed
when that activity window ends. Lightweight filesystem structure:

    org/sessions/<role_id>/<member_id>/<timestamp>/
        meta.json       — {start, end, substrate, assignment}
        transcript.md   — human-readable summary (appended by role)
        actions.jsonl   — structured action log (append-only)
        spend.json      — cost rollup (read/written by spend_tracker)
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from ztare.common.paths import REPO_ROOT
from ztare.common.activity_meter import summarize_activity_spend


SESSIONS_ROOT = REPO_ROOT / "org" / "sessions"


@dataclass
class Session:
    session_id: str             # iso timestamp, filesystem-safe
    member_id: str
    role_id: str
    substrate: str
    start_utc: str
    end_utc: Optional[str] = None
    directory: Optional[Path] = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def session_dir(role_id: str, member_id: str, session_id: str) -> Path:
    """Canonical directory for a session artifact."""
    return SESSIONS_ROOT / role_id / member_id / session_id


def _safe_timestamp() -> str:
    """Filesystem-safe ISO timestamp: 2026-04-23T14-30-15Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


def open_session(
    *,
    member_id: str,
    role_id: str,
    substrate: str,
    notes: Optional[Iterable[str]] = None,
) -> Session:
    """Create a new session directory and write meta.json. Returns the
    Session dataclass bound to that directory."""
    session_id = _safe_timestamp()
    directory = session_dir(role_id, member_id, session_id)
    directory.mkdir(parents=True, exist_ok=True)

    session = Session(
        session_id=session_id,
        member_id=member_id,
        role_id=role_id,
        substrate=substrate,
        start_utc=datetime.now(timezone.utc).isoformat(),
        directory=directory,
        notes=tuple(notes or ()),
    )

    meta_payload = {
        "session_id": session.session_id,
        "member_id": session.member_id,
        "role_id": session.role_id,
        "substrate": session.substrate,
        "start_utc": session.start_utc,
        "end_utc": None,
        "notes": list(session.notes),
    }
    (directory / "meta.json").write_text(
        json.dumps(meta_payload, indent=2), encoding="utf-8"
    )
    # Touch append-only logs so callers can blindly append.
    (directory / "actions.jsonl").touch()
    (directory / "transcript.md").write_text(
        f"# Session {session.session_id}\n\n"
        f"- Member: {session.member_id}\n"
        f"- Role: {session.role_id}\n"
        f"- Substrate: {session.substrate}\n"
        f"- Start: {session.start_utc}\n\n"
        "---\n\n",
        encoding="utf-8",
    )
    return session


def close_session(session: Session, summary: str = "") -> None:
    """Mark a session as closed by updating meta.json + appending summary
    to transcript.md."""
    if session.directory is None:
        return
    end_utc = datetime.now(timezone.utc).isoformat()
    session.end_utc = end_utc

    meta_path = session.directory / "meta.json"
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    payload["end_utc"] = end_utc
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if summary:
        transcript = session.directory / "transcript.md"
        with transcript.open("a", encoding="utf-8") as f:
            f.write(f"\n## Session close {end_utc}\n\n{summary}\n")


def append_action(session: Session, action: dict) -> None:
    """Append a structured action record to actions.jsonl."""
    if session.directory is None:
        return
    action = dict(action)
    action.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    with (session.directory / "actions.jsonl").open(
            "a", encoding="utf-8") as f:
        f.write(json.dumps(action) + "\n")


def activity_meter_for_session(session: Session) -> dict:
    if session.directory is None:
        return {"activity_classes": {}, "action_rows": []}
    path = session.directory / "actions.jsonl"
    actions: list[dict] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                actions.append(row)
    return summarize_activity_spend(actions)


def append_transcript(session: Session, text: str) -> None:
    """Append human-readable text to transcript.md."""
    if session.directory is None:
        return
    with (session.directory / "transcript.md").open(
            "a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n\n")


def active_sessions(*, role_id: Optional[str] = None,
                     member_id: Optional[str] = None) -> list[Session]:
    """Sessions on disk with end_utc unset — i.e. currently live.

    Use this before opening a new session to detect overlap: the cron
    manager cycle should DEFER if an interactive manager session is
    already active for the same (role, member)."""
    return [s for s in list_sessions(role_id=role_id, member_id=member_id)
            if s.end_utc is None]


def should_defer_to_existing(*, role_id: str, member_id: str,
                              self_session_id: Optional[str] = None
                              ) -> Optional[Session]:
    """If another session for (role, member) is active and is NOT the
    one calling this function, return that session (caller should
    defer / no-op). Returns None if no conflict.

    self_session_id: the caller's session_id, to exclude from the
    overlap check. Pass None if the caller has not yet opened a session
    (e.g. at the start of a cron invocation — defer BEFORE opening)."""
    active = active_sessions(role_id=role_id, member_id=member_id)
    for s in active:
        if self_session_id and s.session_id == self_session_id:
            continue
        return s
    return None


def list_sessions(*, role_id: Optional[str] = None,
                   member_id: Optional[str] = None) -> list[Session]:
    """Enumerate sessions on disk, optionally filtered."""
    if not SESSIONS_ROOT.exists():
        return []

    results: list[Session] = []
    role_iter = [role_id] if role_id else sorted(
        p.name for p in SESSIONS_ROOT.iterdir() if p.is_dir()
    )
    for r in role_iter:
        r_dir = SESSIONS_ROOT / r
        if not r_dir.exists():
            continue
        member_iter = [member_id] if member_id else sorted(
            p.name for p in r_dir.iterdir() if p.is_dir()
        )
        for m in member_iter:
            m_dir = r_dir / m
            if not m_dir.exists():
                continue
            for session_path in sorted(m_dir.iterdir()):
                if not session_path.is_dir():
                    continue
                meta_path = session_path / "meta.json"
                if not meta_path.exists():
                    continue
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                results.append(Session(
                    session_id=meta.get("session_id", session_path.name),
                    member_id=meta.get("member_id", m),
                    role_id=meta.get("role_id", r),
                    substrate=meta.get("substrate", ""),
                    start_utc=meta.get("start_utc", ""),
                    end_utc=meta.get("end_utc"),
                    directory=session_path,
                    notes=tuple(meta.get("notes", []) or ()),
                ))
    return results
