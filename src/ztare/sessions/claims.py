# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Substrate handoff lock (GP-128 Hole 10 × GP-129 Margulis pull-forward).

When two sessions could both act on the same task (e.g. a Claude
conversational session AND a headless cron manager, or two parallel
agents), we need a membrane that excludes one from the other for the
duration of the task. This is NOT an identity check (that lives in
src.ztare.roles.authorization); it is a claim on a task object.

Semantic: claiming a task is a membrane exclusion. A claim has an
owner (session_id), a task_id, and an expiry. Any other session that
tries to claim the same task_id while the first claim is live MUST
defer, and SHOULD emit a damage signal of kind "handoff_conflict"
so the manager-agent sees it on the next decision.

Claim files live under org/sessions/_claims/<task_id>.json. They are
gitignored because they are runtime coordination artifacts, not
shipped state.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.ztare.common.paths import REPO_ROOT
from src.ztare.signals import damage

log = logging.getLogger(__name__)

CLAIMS_DIR = REPO_ROOT / "org" / "sessions" / "_claims"


@dataclass(frozen=True)
class TaskClaim:
    task_id: str
    session_id: str
    member_id: str
    role_id: str
    claimed_at_utc: str
    expires_at_utc: str

    def is_expired(self, *, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        try:
            expires = datetime.fromisoformat(self.expires_at_utc)
        except ValueError:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now >= expires


def _claim_path(task_id: str) -> Path:
    safe = task_id.replace("/", "_").replace("\\", "_")
    return CLAIMS_DIR / f"{safe}.json"


def read_claim(task_id: str) -> Optional[TaskClaim]:
    path = _claim_path(task_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return TaskClaim(**data)
    except Exception as exc:                                     # noqa: BLE001
        log.warning("malformed claim for %s: %s", task_id, exc)
        return None


def claim_task(
    *,
    task_id: str,
    session_id: str,
    member_id: str,
    role_id: str,
    ttl_seconds: int = 1800,
) -> tuple[bool, Optional[TaskClaim]]:
    """Try to claim a task. Returns (claimed, conflicting_claim).

    - (True, claim): claim acquired (either fresh or because a previous
      claim expired); the returned TaskClaim is ours.
    - (False, conflicting): another live session owns this task; caller
      must defer. A damage signal is emitted on conflict so the manager
      sees it next cycle.
    """
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    existing = read_claim(task_id)
    if existing and existing.session_id != session_id and not existing.is_expired():
        damage.emit(
            source=f"sessions.claims:{session_id}",
            kind="handoff_conflict",
            detail=(
                f"task_id={task_id} already claimed by session "
                f"{existing.session_id} (role {existing.role_id}); "
                f"expires {existing.expires_at_utc}"
            ),
            session_id=session_id,
            severity="warn",
        )
        return False, existing

    now = datetime.now(timezone.utc)
    claim = TaskClaim(
        task_id=task_id,
        session_id=session_id,
        member_id=member_id,
        role_id=role_id,
        claimed_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(seconds=ttl_seconds)).isoformat(),
    )
    _claim_path(task_id).write_text(json.dumps(asdict(claim), indent=2), encoding="utf-8")
    return True, claim


def release_claim(*, task_id: str, session_id: str) -> bool:
    """Release a claim. Only the owning session may release.

    Returns True on successful release, False if the claim wasn't
    owned by this session (stale or stolen).
    """
    existing = read_claim(task_id)
    if not existing:
        return False
    if existing.session_id != session_id:
        damage.emit(
            source=f"sessions.claims:{session_id}",
            kind="claim_release_mismatch",
            detail=(
                f"session {session_id} tried to release task {task_id} "
                f"owned by {existing.session_id}"
            ),
            session_id=session_id,
            severity="warn",
        )
        return False
    try:
        _claim_path(task_id).unlink()
    except FileNotFoundError:
        pass
    return True
