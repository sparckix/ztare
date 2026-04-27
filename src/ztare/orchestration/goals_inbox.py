"""GP-132 — Principal-Goals Inbox.

Markdown-first goal artifacts under `org/goals/{pending,active,done}/`.
The principal writes a goal file; any agent session picks it up on
next wake. No Python invocation required from the principal.

This module is the agent-side reader + lifecycle manager. See
`org/goals/README.md` for the file schema and agent contract.

Lifecycle: pending → active (claimed by session) → done.
On block, a goal stays in active/ with a ## Blocked section appended.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from src.ztare.common.paths import REPO_ROOT

log = logging.getLogger(__name__)

GOALS_ROOT = REPO_ROOT / "org" / "goals"
PENDING_DIR = GOALS_ROOT / "pending"
ACTIVE_DIR = GOALS_ROOT / "active"
DONE_DIR = GOALS_ROOT / "done"


PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class Goal:
    """Parsed goal file."""
    goal_id: str
    path: Path
    priority: str
    deadline: Optional[str]
    estimated_cost_usd: float
    assigned_to: str
    autonomous_scope_ok: bool
    created_by: str
    created_utc: str
    body: str
    raw_frontmatter: dict = field(default_factory=dict)

    @property
    def priority_rank(self) -> int:
        return PRIORITY_RANK.get(self.priority.lower(), 99)

    @property
    def deadline_sort_key(self) -> str:
        """Sort-friendly deadline; empty string sorts last (no deadline)."""
        return self.deadline or "9999-99-99"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter + body."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    try:
        data = yaml.safe_load(block) or {}
        if not isinstance(data, dict):
            data = {}
    except yaml.YAMLError as exc:
        log.warning("goal frontmatter parse failed: %s", exc)
        data = {}
    body = text[end + 4:].lstrip("\n")
    return data, body


def _parse_goal(path: Path) -> Optional[Goal]:
    """Parse a goal markdown file. Returns None on unrecoverable error."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:                                     # noqa: BLE001
        log.warning("goal read failed %s: %s", path, exc)
        return None

    fm, body = _split_frontmatter(text)
    goal_id = fm.get("goal_id")
    if not goal_id:
        # Fall back to filename stem if frontmatter missing goal_id
        goal_id = path.stem
        if goal_id.startswith(".") or goal_id == "":
            return None

    return Goal(
        goal_id=goal_id,
        path=path,
        priority=str(fm.get("priority", "medium")),
        deadline=fm.get("deadline"),
        estimated_cost_usd=float(fm.get("estimated_cost_usd", 0.0) or 0.0),
        assigned_to=str(fm.get("assigned_to", "role.manager")),
        autonomous_scope_ok=bool(fm.get("autonomous_scope_ok", False)),
        created_by=str(fm.get("created_by", "unknown")),
        created_utc=str(fm.get("created_utc", "")),
        body=body,
        raw_frontmatter=fm,
    )


def list_pending_goals(
    *,
    assigned_to: Optional[str] = None,
    goals_root: Optional[Path] = None,
) -> list[Goal]:
    """Return pending goals, sorted by (priority, deadline).

    assigned_to: filter to goals assigned to this role (e.g. 'role.manager').
    goals_root: override for tests.
    """
    root = goals_root if goals_root is not None else GOALS_ROOT
    pending = root / "pending"
    if not pending.exists():
        return []
    out: list[Goal] = []
    for path in sorted(pending.glob("*.md")):
        if path.name.startswith("."):
            continue
        goal = _parse_goal(path)
        if goal is None:
            continue
        if assigned_to is not None and goal.assigned_to != assigned_to:
            continue
        out.append(goal)
    out.sort(key=lambda g: (g.priority_rank, g.deadline_sort_key, g.goal_id))
    return out


def list_active_goals(
    *,
    goals_root: Optional[Path] = None,
) -> list[Goal]:
    """Return currently-claimed goals (in active/ folder)."""
    root = goals_root if goals_root is not None else GOALS_ROOT
    active = root / "active"
    if not active.exists():
        return []
    out: list[Goal] = []
    for path in sorted(active.glob("*.md")):
        if path.name.startswith("."):
            continue
        goal = _parse_goal(path)
        if goal is None:
            continue
        out.append(goal)
    return out


def claim_goal(
    *,
    goal_id: str,
    session_id: str,
    member_id: str,
    role_id: str,
    goals_root: Optional[Path] = None,
) -> Optional[Goal]:
    """Move a pending goal to active/, stamp it with the claiming session.

    Returns the claimed Goal (now pointing to the active/ path), or None
    if the goal does not exist in pending/ (already claimed or done).

    Also calls sessions.claim_task() so the task-claim membrane covers
    it (other agents will defer if they try to claim the same goal_id).
    """
    root = goals_root if goals_root is not None else GOALS_ROOT
    src = root / "pending" / f"{goal_id}.md"
    if not src.exists():
        return None

    # Try to claim via the sessions membrane first; if a conflict exists
    # we refuse rather than silently override.
    from src.ztare.sessions.claims import claim_task
    claimed, conflict = claim_task(
        task_id=f"goal:{goal_id}",
        session_id=session_id,
        member_id=member_id,
        role_id=role_id,
        ttl_seconds=6 * 3600,  # 6-hour working window
    )
    if not claimed:
        log.info("goal %s already claimed by session %s",
                 goal_id, conflict.session_id if conflict else "?")
        return None

    dst_dir = root / "active"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{goal_id}.md"

    # Append a claim block to the body, then atomically move.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    original = src.read_text(encoding="utf-8")
    annotated = original.rstrip() + (
        f"\n\n---\n\n## Claim\n\n"
        f"- session_id: {session_id}\n"
        f"- member_id: {member_id}\n"
        f"- role_id: {role_id}\n"
        f"- claimed_utc: {now}\n"
    )
    dst.write_text(annotated, encoding="utf-8")
    src.unlink()

    return _parse_goal(dst)


def mark_goal_done(
    *,
    goal_id: str,
    session_id: str,
    result_summary: str,
    artifacts: Optional[list[str]] = None,
    cost_incurred_usd: float = 0.0,
    goals_root: Optional[Path] = None,
) -> Optional[Path]:
    """Move an active goal to done/, append a ## Result section.

    Also releases the task-claim. Returns the done/ path, or None on error.
    """
    root = goals_root if goals_root is not None else GOALS_ROOT
    src = root / "active" / f"{goal_id}.md"
    if not src.exists():
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    art_lines = "\n".join(f"- {a}" for a in (artifacts or []))
    result_block = (
        f"\n\n---\n\n## Result\n\n"
        f"- completed_utc: {now}\n"
        f"- session_id: {session_id}\n"
        f"- cost_incurred_usd: {cost_incurred_usd}\n"
        f"- summary: {result_summary}\n"
        + (f"- artifacts:\n{art_lines}\n" if art_lines else "")
    )
    text = src.read_text(encoding="utf-8").rstrip() + result_block

    dst_dir = root / "done"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{goal_id}.md"
    dst.write_text(text, encoding="utf-8")
    src.unlink()

    # Release the claim membrane.
    from src.ztare.sessions.claims import release_claim
    release_claim(task_id=f"goal:{goal_id}", session_id=session_id)

    return dst


def mark_goal_blocked(
    *,
    goal_id: str,
    session_id: str,
    blocker: str,
    escalation_path: Optional[str] = None,
    goals_root: Optional[Path] = None,
) -> Optional[Path]:
    """Append ## Blocked section to an active goal (does NOT move it)."""
    root = goals_root if goals_root is not None else GOALS_ROOT
    src = root / "active" / f"{goal_id}.md"
    if not src.exists():
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    block = (
        f"\n\n---\n\n## Blocked\n\n"
        f"- blocked_utc: {now}\n"
        f"- session_id: {session_id}\n"
        f"- blocker: {blocker}\n"
        + (f"- escalation: {escalation_path}\n" if escalation_path else "")
    )
    text = src.read_text(encoding="utf-8").rstrip() + block
    src.write_text(text, encoding="utf-8")
    return src
