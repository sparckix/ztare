"""GP-131 Work-Discovery Loop — two-source prototype.

The Level 2 daemon (GP-128 § Future Work) needs to identify work
worth doing without being told. This module implements the two
cheapest + highest-signal-density discovery sources from GP-131:

1. TODO-scan   — open TODO boxes in seam files (self-authored, pre-filtered)
2. Damage-scan — unresolved signals from src.ztare.signals.damage

Each source produces Candidate objects with a scarcity signal and an
"intent" field (not "procedure" — GP-129 Godfrey-Smith pull-forward).
Candidates are NOT executed; they are returned to a ranker that picks
one for inbox escalation, human-in-loop.

This is the prototype. The full ranker + proposal-envelope writer
live in a separate module once the first 30 proposals have calibrated
the source weights.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.ztare.common.paths import REPO_ROOT
from src.ztare.signals import damage


SEAMS_ROOT = REPO_ROOT / "research_areas" / "private" / "seams" / "mission"
TODO_PATTERN = re.compile(r"^\s*-\s*\[\s*\]\s+(.+)$", re.MULTILINE)


@dataclass
class Candidate:
    """A discovered work item, not yet proposed to the principal."""
    source: str                     # TODO-scan | damage-scan | closure-map | ...
    intent: str                     # one-sentence, what-for (not how)
    origin_path: Optional[Path]     # seam file, signal file, etc.
    scarcity_signal: str            # why this surfaced now
    raw_text: str                   # verbatim excerpt for triage
    age_days: Optional[float] = None
    severity: str = "info"          # info | warn | critical
    metadata: dict = field(default_factory=dict)


def discover_open_todos(
    *,
    root: Path = SEAMS_ROOT,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Scan seam files for open `- [ ]` TODO boxes.

    Returns candidates ranked by file-mtime-desc then position-in-file.
    Stale seams (mtime > 60 days) are skipped — the GP-131 trail-lock-in
    defense says stale TODOs are a separate signal class and should not
    crowd out fresh items.
    """
    if not root.exists():
        return []

    now = time.time()
    stale_cutoff = now - 60 * 24 * 3600  # 60 days

    candidates: list[Candidate] = []
    seam_files = sorted(
        (p for p in root.glob("*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for seam in seam_files:
        mtime = seam.stat().st_mtime
        if mtime < stale_cutoff:
            continue
        age_days = (now - mtime) / 86400.0
        try:
            text = seam.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in TODO_PATTERN.finditer(text):
            todo = match.group(1).strip()
            if not todo or len(todo) < 10:
                continue
            candidates.append(Candidate(
                source="TODO-scan",
                intent=todo[:200],
                origin_path=seam,
                scarcity_signal=(
                    f"open TODO in seam last touched {age_days:.1f} days ago; "
                    "self-authored commitment not yet closed"
                ),
                raw_text=todo,
                age_days=age_days,
                severity="info",
                metadata={"seam": seam.name},
            ))

    # Cap + stable ordering: freshest seams first, then order of TODOs
    # within file preserved.
    return candidates[:max_per_source]


def discover_damage_signals(
    *,
    max_per_source: int = 10,
) -> list[Candidate]:
    """Scan unresolved damage signals.

    Every damage signal is already a scarcity-filtered event — someone
    or something wrote it because an invariant was violated. Critical
    signals jump to the top regardless of age.
    """
    signals = damage.list_recent(limit=max_per_source * 3)
    now = datetime.now(timezone.utc)

    candidates: list[Candidate] = []
    for s in signals:
        try:
            ts = datetime.fromisoformat(s.timestamp_utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (now - ts).total_seconds() / 86400.0
        except ValueError:
            age = None

        intent = (
            f"resolve {s.kind} signal from {s.source}"
            if s.severity != "critical"
            else f"HARD STOP: critical {s.kind} signal from {s.source}"
        )
        candidates.append(Candidate(
            source="damage-scan",
            intent=intent,
            origin_path=None,
            scarcity_signal=(
                f"{s.severity}-severity signal, age {age:.2f} days"
                if age is not None else f"{s.severity}-severity signal"
            ),
            raw_text=s.detail,
            age_days=age,
            severity=s.severity,
            metadata={
                "source": s.source,
                "kind": s.kind,
                "timestamp_utc": s.timestamp_utc,
                "session_id": s.session_id,
            },
        ))

    # Critical first, then by age ascending (newer first).
    def sort_key(c: Candidate) -> tuple:
        sev_rank = {"critical": 0, "warn": 1, "info": 2}.get(c.severity, 3)
        return (sev_rank, c.age_days if c.age_days is not None else 1e9)

    candidates.sort(key=sort_key)
    return candidates[:max_per_source]


def discover_principal_goals(
    *,
    assigned_to: Optional[str] = None,
    max_per_source: int = 10,
) -> list[Candidate]:
    """GP-132 source: pending goals the principal wrote to org/goals/pending/.

    These are the HIGHEST-priority discovery source because they carry
    explicit principal intent — not inferred from artifacts, but stated.
    """
    from src.ztare.orchestration.goals_inbox import list_pending_goals
    goals = list_pending_goals(assigned_to=assigned_to)
    out: list[Candidate] = []
    for g in goals[:max_per_source]:
        severity = (
            "critical" if g.priority.lower() == "urgent" else
            "warn" if g.priority.lower() == "high" else
            "info"
        )
        out.append(Candidate(
            source="principal-goal",
            intent=(
                f"[{g.priority}] execute principal goal: {g.goal_id}"
                + (f" (deadline {g.deadline})" if g.deadline else "")
            ),
            origin_path=g.path,
            scarcity_signal=(
                "explicit principal directive in org/goals/pending/ — "
                f"autonomous_scope_ok={g.autonomous_scope_ok}, "
                f"estimated_cost=${g.estimated_cost_usd:.2f}"
            ),
            raw_text=g.body[:500],
            age_days=None,
            severity=severity,
            metadata={
                "goal_id": g.goal_id,
                "priority": g.priority,
                "deadline": g.deadline,
                "estimated_cost_usd": g.estimated_cost_usd,
                "assigned_to": g.assigned_to,
                "autonomous_scope_ok": g.autonomous_scope_ok,
            },
        ))
    return out


def discover_all(
    *,
    max_per_source: int = 10,
    assigned_to: Optional[str] = None,
) -> list[Candidate]:
    """Run all implemented discovery sources and return combined list.

    Ordering: principal goals first (explicit directive), then critical
    damage signals, then TODO-scan. The ranker downstream decides which
    to propose; this function just aggregates.
    """
    out: list[Candidate] = []
    out.extend(discover_principal_goals(
        assigned_to=assigned_to, max_per_source=max_per_source))
    out.extend(discover_damage_signals(max_per_source=max_per_source))
    out.extend(discover_open_todos(max_per_source=max_per_source))
    return out


def format_candidate_for_inbox(c: Candidate) -> str:
    """Render a candidate as the GP-131 proposal envelope."""
    origin = str(c.origin_path.relative_to(REPO_ROOT)) if c.origin_path else "n/a"
    meta_str = ", ".join(f"{k}={v}" for k, v in c.metadata.items() if v)
    return (
        f"Source:           {c.source}\n"
        f"Intent:           {c.intent}\n"
        f"Candidate action: <propose a bounded next move to the principal>\n"
        f"Origin:           {origin}\n"
        f"Scarcity signal:  {c.scarcity_signal}\n"
        f"Age:              {c.age_days:.2f} days" if c.age_days is not None
        else f"Age:              unknown"
    ) + (f"\nSeverity:         {c.severity}\n"
         f"Metadata:         {meta_str}\n"
         f"Raw excerpt:      {c.raw_text[:300]}")
