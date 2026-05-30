# SPDX-License-Identifier: MIT
"""Damage-signal stub (GP-129 pull-forward — Matzinger danger model).

Identity-based authorization (src.ztare.roles.authorization) answers
"is this actor allowed here?" It does NOT answer "is this action
damaging the host?" The immune-system frame separates those.

This module provides the minimum channel: any code can `emit()` a
damage signal; the manager-agent (or any supervisor) calls
`list_recent()` before making a decision. No enforcement is baked in
yet — the point is to create the write surface so future invariant
tripwires (evidence-contradiction detectors, cost-spike detectors,
output-quality regression detectors) have somewhere to land.

Design notes:
- Signals are plain JSON files under org/signals/damage/, one per
  emit. Filename is UTC timestamp + a short hash so concurrent emits
  don't collide.
- Emits never raise on filesystem issues (best-effort channel).
- list_recent() is a read-only scan; it does not consume or clear
  signals. Clearing is a separate, explicit call with a reason.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.ztare.common.paths import REPO_ROOT

log = logging.getLogger(__name__)

SIGNALS_DIR = REPO_ROOT / "org" / "signals" / "damage"


@dataclass(frozen=True)
class DamageSignal:
    timestamp_utc: str
    source: str          # e.g. "spend_tracker", "session.member_id", "tool:Bash"
    kind: str            # free-form; canonical catalog at org/signals/SIGNAL_KINDS.md
    detail: str
    session_id: Optional[str] = None
    severity: str = "warn"   # info | warn | critical


def _slug(source: str, kind: str, detail: str) -> str:
    h = hashlib.sha1(f"{source}|{kind}|{detail}".encode("utf-8")).hexdigest()[:8]
    return h


def emit(
    *,
    source: str,
    kind: str,
    detail: str,
    session_id: Optional[str] = None,
    severity: str = "warn",
) -> Optional[Path]:
    """Emit a damage signal. Returns the written file path (or None on failure)."""
    try:
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:                                     # noqa: BLE001
        log.warning("damage-signal dir unavailable: %s", exc)
        return None

    sig = DamageSignal(
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source,
        kind=kind,
        detail=detail,
        session_id=session_id,
        severity=severity,
    )
    fname = f"{sig.timestamp_utc.replace(':', '-')}_{_slug(source, kind, detail)}.json"
    path = SIGNALS_DIR / fname
    try:
        path.write_text(json.dumps(asdict(sig), indent=2), encoding="utf-8")
    except Exception as exc:                                     # noqa: BLE001
        log.warning("damage-signal write failed: %s", exc)
        return None
    return path


def list_recent(*, limit: int = 50) -> list[DamageSignal]:
    """Return most-recent damage signals, newest first."""
    if not SIGNALS_DIR.exists():
        return []
    files = sorted(SIGNALS_DIR.glob("*.json"), reverse=True)[:limit]
    out: list[DamageSignal] = []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append(DamageSignal(**data))
        except Exception:                                        # noqa: BLE001
            continue
    return out


def clear(*, reason: str, session_id: Optional[str] = None) -> int:
    """Move all current signals to org/signals/damage/_cleared/<session>_<ts>/.

    Never deletes — preserves audit trail. Returns number cleared.
    """
    if not SIGNALS_DIR.exists():
        return 0
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"{ts}_{session_id or 'unknown'}"
    archive = SIGNALS_DIR / "_cleared" / archive_name
    archive.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in SIGNALS_DIR.glob("*.json"):
        target = archive / p.name
        try:
            os.replace(p, target)
            count += 1
        except Exception:                                        # noqa: BLE001
            continue
    (archive / "_reason.txt").write_text(reason, encoding="utf-8")
    return count
