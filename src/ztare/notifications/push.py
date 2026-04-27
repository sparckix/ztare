"""Push notification layer for GP-128 persistent-manager-agent escalations.

As of 2026-04-25 (GP-128b unification), this module is a thin compat
shim over ``telegram.py``. The original ntfy.sh transport was retired
because Telegram is bidirectional (the principal can also send commands
to the manager via the same bot — see GP-128b seam).

All existing call sites (``push_notification``, ``push_gate_escalation``,
``push_from_gate_json``) keep working without code changes; only the
underlying transport changed.

Usage (unchanged):

    from src.ztare.notifications import push_notification

    push_notification(
        title="Patent #4 gate pending",
        message="TDO-LR filing window opens tomorrow; principal signature needed.",
        priority="high",
        tags=["patent", "decision"],
    )

Setup:
    python scripts/telegram_setup.py        # one-time creds capture
    python scripts/poll_telegram.py --consume   # ad-hoc inbound poll

Deprecation notes:
    * ``ZTARE_NTFY_TOPIC`` env var is ignored (kept here for grep
      discoverability — the topic file ``org/mandates/.ntfy_topic`` is
      no longer consulted).
    * The ntfy.sh broker is no longer contacted by this module.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from src.ztare.notifications.telegram import (
    push_notification as _telegram_push_notification,
)


# Legacy constants retained for any caller that imports them. They are
# no longer functional after the GP-128b transport swap.
NTFY_TOPIC_ENV = "ZTARE_NTFY_TOPIC"
NTFY_TOPIC_FILE = Path("org/mandates/.ntfy_topic")
NTFY_TOPIC: Optional[str] = None  # always None after retirement
NTFY_URL: Optional[str] = None     # always None after retirement


log = logging.getLogger(__name__)


def push_notification(
    title: str,
    message: str,
    priority: str = "default",
    tags: Optional[Iterable[str]] = None,
    click_url: Optional[str] = None,
    timeout_seconds: float = 5.0,
) -> bool:
    """Send a push notification to the principal.

    API-compatible with the historical ntfy.sh implementation. The
    transport is now Telegram (GP-128b). See ``telegram.py`` for
    priority-prefix conventions. All failures are logged, never
    raised — the filesystem inbox remains the authoritative channel.
    """
    return _telegram_push_notification(
        title=title,
        message=message,
        priority=priority,
        tags=tags,
        click_url=click_url,
        timeout_seconds=timeout_seconds,
    )


def push_gate_escalation(
    goal_slug: str,
    stage: str,
    gate_description: str,
    gate_reason: str,
    inbox_url: str = "http://localhost:8501",
    extra_context: Optional[str] = None,
) -> bool:
    """Convenience wrapper that formats a GP-070 gate escalation
    for push delivery.

    Intended to be called from `gate_escalation.py` immediately after
    the filesystem gate JSON is written. Failure to push does NOT
    fail the gate; the filesystem entry remains authoritative.
    """
    title = f"[gate] {goal_slug}: {stage}"
    body_parts = [gate_description.strip()]
    if gate_reason:
        body_parts.append(f"Reason: {gate_reason}")
    if extra_context:
        body_parts.append(extra_context.strip())
    body_parts.append(f"Inbox: {inbox_url}")
    message = "\n".join(body_parts)

    urgent_reasons = {
        "CONTRACT_PROMOTION",
        "SCOPE_MISMATCH",
        "UNAUTHORIZED_ARTIFACT_WRITE",
        "COST_OVERRUN",
    }
    priority = "high" if gate_reason in urgent_reasons else "default"

    return push_notification(
        title=title,
        message=message,
        priority=priority,
        tags=["gate", goal_slug],
        click_url=inbox_url,
    )


def push_from_gate_json(
    gate_json_path: Path,
    inbox_url: str = "http://localhost:8501",
) -> bool:
    """Read a gate JSON written by write_gate_escalation() and push it."""
    try:
        with open(gate_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read gate json %s: %s", gate_json_path, exc)
        return False

    return push_gate_escalation(
        goal_slug=payload.get("goal_slug", "<unknown>"),
        stage=payload.get("stage", "<unknown>"),
        gate_description=payload.get("gate_description", ""),
        gate_reason=payload.get("gate_reason", ""),
        inbox_url=inbox_url,
        extra_context=payload.get("notes"),
    )
