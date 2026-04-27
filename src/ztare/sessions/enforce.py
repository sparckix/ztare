# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Holes 2 + 3: session auto-open + multi-session conflict enforcement.

Two helpers that the manager-agent (and any role that wants the same
hygiene) should call at entry:

- `ensure_session(...)`: idempotent — if there is an active session on
  disk for the caller's (role, member, substrate), reuse it; otherwise
  open a new one. Returns the Session.
- `require_no_conflict(...)`: raises SessionConflict (or emits a damage
  signal + returns the conflicting session) if a DIFFERENT live session
  exists for the same (role, member). Call this before `ensure_session`
  in the cron/daemon path to guarantee the live principal session wins.

These are enforcement wrappers on top of the primitives in session.py;
they do not replace open_session / close_session.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from pathlib import Path

from src.ztare.sessions.session import (
    Session,
    active_sessions,
    open_session,
)
from src.ztare.signals import damage

log = logging.getLogger(__name__)


class SessionConflict(RuntimeError):
    """Raised when a caller refuses to proceed due to another live session."""


def ensure_session(
    *,
    member_id: str,
    role_id: str,
    substrate: str,
    notes: Optional[Iterable[str]] = None,
    reuse_existing: bool = True,
    mandate_path: Optional["Path"] = None,
) -> Session:
    """Return a live session for (member, role, substrate).

    If `reuse_existing` is True and a live session already exists for
    the caller's own substrate, reuse it. Otherwise, open a new session.

    If `mandate_path` is provided (GP-128 debate item 3), runs the
    mandate-hash-drift auto-emitter on entry. First call per session
    baselines the hash; later calls detect drift.
    """
    session: Session
    if reuse_existing:
        reused = None
        for s in active_sessions(role_id=role_id, member_id=member_id):
            if s.substrate == substrate:
                reused = s
                break
        session = reused if reused is not None else open_session(
            member_id=member_id, role_id=role_id, substrate=substrate, notes=notes
        )
    else:
        session = open_session(
            member_id=member_id, role_id=role_id, substrate=substrate, notes=notes
        )

    if mandate_path is not None and session.directory is not None:
        # Lazy import avoids circular dep (signals.autoemit is higher in
        # the dependency graph than sessions).
        from src.ztare.signals import autoemit
        autoemit.check_mandate_drift(
            session_dir=session.directory,
            mandate_path=mandate_path,
            role_id=role_id,
        )
    return session


def require_no_conflict(
    *,
    member_id: str,
    role_id: str,
    self_substrate: str,
    action: str = "proceed",
    raise_on_conflict: bool = False,
) -> Optional[Session]:
    """Check for a live session in a DIFFERENT substrate for (member, role).

    Returns the conflicting session (or None if clear). If one is found:
    - Emits a damage signal of kind "session_conflict" so the manager
      sees it next cycle.
    - If `raise_on_conflict=True`, raises SessionConflict.

    `self_substrate` is the caller's substrate; a session on THAT
    substrate is not considered a conflict (it's the caller itself).
    """
    for s in active_sessions(role_id=role_id, member_id=member_id):
        if s.substrate == self_substrate:
            continue
        damage.emit(
            source=f"sessions.enforce:{self_substrate}",
            kind="session_conflict",
            detail=(
                f"another live session {s.session_id} on substrate "
                f"{s.substrate} for role.{role_id}/member.{member_id}; "
                f"refusing to {action}"
            ),
            session_id=s.session_id,
            severity="warn",
        )
        if raise_on_conflict:
            raise SessionConflict(
                f"cannot {action}: session {s.session_id} on {s.substrate} "
                f"is live for role.{role_id}/member.{member_id}"
            )
        return s
    return None
