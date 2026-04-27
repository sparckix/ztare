"""Inbox-velocity ratchet (GP-128 post-ship debate item 5).

The manager-agent's escalation scope is a ratchet: adding a new case is
cheap, removing one is political. Without a velocity check, the inbox
accumulates until the principal becomes the bottleneck the manager was
supposed to protect from being the bottleneck.

This module provides the simplest possible counter-measure:

- `record_weekly_snapshot()` — writes a single line to
  `ztare_workspace/daemon/inbox_velocity.jsonl` capturing the current
  count of pending gates + ISO week tag. Idempotent per week (later
  calls in the same ISO week update the existing entry).

- `check_velocity_trend()` — reads the last ≥3 weekly snapshots; if the
  most recent 3 are strictly monotone-increasing, writes a
  SCOPE_CONTRACTION_REQUIRED gate asking the principal to retire
  escalation categories. Idempotent: the gate is fingerprinted on the
  (latest_week, trend_hash) so re-invocations don't spam.

Call both at the end of each manager cron cycle.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.ztare.common.paths import REPO_ROOT

log = logging.getLogger(__name__)

GATES_DIR = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
LEDGER_PATH = REPO_ROOT / "ztare_workspace" / "daemon" / "inbox_velocity.jsonl"
FINGERPRINT_PATH = REPO_ROOT / "ztare_workspace" / "daemon" / "inbox_velocity_last_gate.txt"


def _iso_week_tag(when: Optional[datetime] = None) -> str:
    """Return ISO-8601 year-week tag like `2026-W17`."""
    when = when or datetime.now(timezone.utc)
    y, w, _ = when.isocalendar()
    return f"{y}-W{w:02d}"


def _count_pending_gates() -> int:
    if not GATES_DIR.exists():
        return 0
    return sum(1 for _ in GATES_DIR.glob("*.json"))


def _read_ledger() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    entries: list[dict] = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _write_ledger(entries: list[dict]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(e) for e in entries) + "\n"
    tmp = LEDGER_PATH.with_suffix(".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(LEDGER_PATH)


def record_weekly_snapshot(*, when: Optional[datetime] = None) -> dict:
    """Write/update this week's pending-gate count in the ledger.

    Returns the snapshot dict written. Idempotent within a week.
    """
    tag = _iso_week_tag(when)
    count = _count_pending_gates()
    now = (when or datetime.now(timezone.utc)).isoformat()

    entries = _read_ledger()
    found = False
    for e in entries:
        if e.get("iso_week") == tag:
            e["count"] = count
            e["last_updated_utc"] = now
            found = True
            break
    if not found:
        entries.append({
            "iso_week": tag,
            "count": count,
            "first_recorded_utc": now,
            "last_updated_utc": now,
        })

    _write_ledger(entries)
    return {"iso_week": tag, "count": count}


def check_velocity_trend(*, gate_dir: Optional[Path] = None) -> Optional[Path]:
    """Inspect last 3 weekly snapshots; if strictly increasing, write a
    SCOPE_CONTRACTION_REQUIRED gate.

    Returns the path of the written gate or None if no trend.
    Idempotent: same trend doesn't produce duplicate gates.
    """
    entries = _read_ledger()
    if len(entries) < 3:
        return None

    last3 = entries[-3:]
    counts = [int(e.get("count", 0)) for e in last3]
    if not (counts[0] < counts[1] < counts[2]):
        return None

    # Fingerprint: week tag of latest + the three counts.
    fingerprint_key = f"{last3[-1]['iso_week']}|{counts[0]}|{counts[1]}|{counts[2]}"
    fingerprint = hashlib.sha256(fingerprint_key.encode("utf-8")).hexdigest()[:16]

    if FINGERPRINT_PATH.exists():
        try:
            prev = FINGERPRINT_PATH.read_text(encoding="utf-8").strip()
            if prev == fingerprint:
                return None  # already fired for this exact trend
        except Exception:
            pass

    # Fire the gate via escalation_manager so it lands in the inbox.
    from src.ztare.supervisor.escalation_manager import escalate
    result = escalate(
        title="Inbox scope contraction required",
        reason=(
            f"Pending-gate count rose for 3 consecutive weeks: "
            f"{counts[0]} ({last3[0]['iso_week']}) → "
            f"{counts[1]} ({last3[1]['iso_week']}) → "
            f"{counts[2]} ({last3[2]['iso_week']}). "
            "Per GP-128 Seat C ratchet defense, principal should review "
            "the mandate's Escalation Scope section and retire categories "
            "that are generating net-noise."
        ),
        urgent=False,
        advisory=False,
        notes=[
            f"Trend fingerprint: {fingerprint}",
            "To silence: close enough gates to stop the trend, OR edit manager_mandate.md § 'Scope of Escalation' and remove categories, then record new weekly snapshots.",
            "This gate will not re-fire for the same trend.",
        ],
        cost_usd=0.0,
        equivalent_gate_reason="SCOPE_CONTRACTION_REQUIRED",
        gate_dir=gate_dir,
        from_role="manager",
        to_role="principal",
    )

    # Persist fingerprint so we don't re-fire.
    FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINGERPRINT_PATH.write_text(fingerprint, encoding="utf-8")
    return Path(result["path"])
