# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Autonomous damage-signal emitters (GP-128 post-ship debate output).

The GP-128 post-ship adversarial debate (2026-04-23) found that the
damage-signal channel was a pipe with nothing feeding it — the Matzinger
frame was half-implemented. This module provides the first two auto-emitters
the debate identified as load-bearing:

1. `check_mandate_drift(session, mandate_path)` — at session entry, compares
   the current mandate file hash to the hash stored in the session's
   meta.json. If the mandate changed mid-session, emits a damage signal.
   Catches the "agent reads mandate, mandate changes, agent operates
   under stale rules" case.

2. `check_session_id_authenticity(session_id)` — verifies that a given
   `session_id` corresponds to a live session on disk (a dir exists with
   meta.json whose end_utc is null). Emits a critical-severity damage
   signal if not. Catches forged session_ids in escalations.

Both are cheap (filesystem reads + hash), idempotent, and safe to call
multiple times. Neither raises — on failure they emit a signal and
return a boolean.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from src.ztare.common.paths import REPO_ROOT
from src.ztare.signals import damage

log = logging.getLogger(__name__)

SESSIONS_ROOT = REPO_ROOT / "org" / "sessions"


def _hash_file(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception as exc:                                     # noqa: BLE001
        log.warning("mandate hash failed for %s: %s", path, exc)
        return None


def check_mandate_drift(
    *,
    session_dir: Path,
    mandate_path: Path,
    role_id: str,
) -> bool:
    """Compare current mandate-file hash to hash stored in session meta.json.

    - On first call for a session, stores the current hash in meta.json
      and returns True (no drift to report — baseline established).
    - On subsequent calls, compares. Mismatch emits damage signal
      `mandate_drift` at severity=warn and updates the stored hash
      (so we don't keep re-emitting for the same change).

    Returns True if the mandate appears stable or was just baselined;
    False if drift was detected. Safe to call every session start.
    """
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        damage.emit(
            source=f"autoemit.mandate_drift:{role_id}",
            kind="mandate_drift_unverifiable",
            detail=f"session dir {session_dir} has no meta.json",
            severity="warn",
        )
        return False

    current_hash = _hash_file(mandate_path)
    if current_hash is None:
        damage.emit(
            source=f"autoemit.mandate_drift:{role_id}",
            kind="mandate_missing",
            detail=f"mandate file not found at {mandate_path}",
            severity="critical",
        )
        return False

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:                                     # noqa: BLE001
        log.warning("meta.json read failed: %s", exc)
        return False

    stored_hash = meta.get("mandate_hash")
    if stored_hash is None:
        # First baseline — write it, no drift to report.
        meta["mandate_hash"] = current_hash
        meta["mandate_path"] = str(mandate_path.relative_to(REPO_ROOT)) \
            if mandate_path.is_relative_to(REPO_ROOT) else str(mandate_path)
        try:
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception as exc:                                 # noqa: BLE001
            log.warning("meta.json write failed: %s", exc)
        return True

    if stored_hash == current_hash:
        return True

    # Drift detected. Emit + update stored hash so we don't spam.
    session_id = meta.get("session_id", session_dir.name)
    damage.emit(
        source=f"autoemit.mandate_drift:{role_id}",
        kind="mandate_drift",
        detail=(
            f"mandate file {mandate_path.name} changed during session "
            f"{session_id} (old_hash={stored_hash[:12]}..., "
            f"new_hash={current_hash[:12]}...); "
            f"agent may be operating under stale interpretation"
        ),
        session_id=session_id,
        severity="warn",
    )
    meta["mandate_hash"] = current_hash
    meta["mandate_drift_count"] = int(meta.get("mandate_drift_count", 0)) + 1
    try:
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception as exc:                                     # noqa: BLE001
        log.warning("meta.json write failed: %s", exc)
    return False


def _live_session_ids() -> set[str]:
    """Scan org/sessions/**/meta.json; return session_ids with end_utc=None."""
    live: set[str] = set()
    if not SESSIONS_ROOT.exists():
        return live
    for meta_file in SESSIONS_ROOT.glob("*/*/*/meta.json"):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("end_utc") is None:
            sid = meta.get("session_id")
            if sid:
                live.add(sid)
    return live


def check_goals_not_inspected(
    *,
    session_dir: Path,
    role_id: str,
    min_seconds_before_flag: int = 300,
) -> bool:
    """Detect sessions that act on the repo without ever listing principal goals.

    An honest session calls `goals_inbox.list_pending_goals()` (or the
    CLI, which emits a `goals_inspected` damage signal) at least once.
    Call this helper at session close — if the session ran for more
    than `min_seconds_before_flag` seconds AND no `goals_inspected`
    signal was emitted during the session, fire `goals_not_inspected`
    at warn severity.

    Returns True if inspected (or session too short to care); False if
    the session appears to have ignored the goals inbox.
    """
    import json
    from datetime import datetime, timezone

    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        return False

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    start_utc = meta.get("start_utc")
    if not start_utc:
        return False
    try:
        start = datetime.fromisoformat(start_utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except ValueError:
        return False

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    if duration < min_seconds_before_flag:
        return True  # too short to flag

    session_id = meta.get("session_id", session_dir.name)

    # Scan damage signals (including _cleared/) for any goals_inspected
    # emission carrying this session_id OR within session window.
    signals = damage.list_recent(limit=500)
    for s in signals:
        if s.kind != "goals_inspected":
            continue
        try:
            s_ts = datetime.fromisoformat(s.timestamp_utc)
            if s_ts.tzinfo is None:
                s_ts = s_ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if s_ts >= start:
            return True

    damage.emit(
        source=f"autoemit.goals_not_inspected:{role_id}",
        kind="goals_not_inspected",
        detail=(
            f"session {session_id} ran for {duration:.0f}s without "
            f"ever calling goals_inbox.list_pending_goals() — "
            f"principal goals may have been ignored"
        ),
        session_id=session_id,
        severity="warn",
    )
    return False


def check_session_id_authenticity(
    *,
    session_id: Optional[str],
    context: str,
) -> bool:
    """Verify session_id corresponds to a live session on disk.

    Called by the escalation manager before writing a gate. If the
    claimed session_id does not match any live session, emits a
    critical-severity damage signal (`session_id_forgery`) and
    returns False. None is tolerated (no claim = no forgery).

    `context` is included in the signal detail (e.g. "escalate call,
    title=<title>"). Returns True if valid or None; False on forgery.
    """
    if session_id is None or session_id == "":
        return True  # no claim, no forgery

    live = _live_session_ids()
    if session_id in live:
        return True

    damage.emit(
        source="autoemit.session_id_authenticity",
        kind="session_id_forgery",
        detail=(
            f"escalation claimed session_id={session_id} but no live "
            f"session on disk matches (context: {context}); "
            f"possible forgery or race condition with session close"
        ),
        session_id=session_id,
        severity="critical",
    )
    return False
