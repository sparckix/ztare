"""GP-128 Session model: per-(member, role, substrate, time-window) audit.

A session is the runtime instance of an assignment. When a Claude
conversation opens, a cron fires, or a daemon starts a work window, the
session tracks WHAT HAPPENED for that specific member filling that
specific role on that specific substrate within that time window.

Sessions are gitignored (personal activity log). Structure:

    org/sessions/<role_id>/<member_id>/<iso_timestamp>/
        transcript.md       ← principal-readable summary
        actions.jsonl       ← append-only log of significant actions
        spend.json          ← cost rollup matching spend_tracker schema
        meta.json           ← start/end, substrate, assignment ref
"""

from .session import (
    Session, session_dir, open_session, close_session, list_sessions,
    active_sessions, should_defer_to_existing, append_action, append_transcript,
)
from .claims import TaskClaim, claim_task, release_claim, read_claim
from .enforce import ensure_session, require_no_conflict

__all__ = [
    "Session", "session_dir", "open_session", "close_session",
    "list_sessions", "active_sessions", "should_defer_to_existing",
    "append_action", "append_transcript",
    "TaskClaim", "claim_task", "release_claim", "read_claim",
    "ensure_session", "require_no_conflict",
]
