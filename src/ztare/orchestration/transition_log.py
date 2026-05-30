# SPDX-License-Identifier: MIT
"""Canonical local transition log writer for the org runtime.

This is the solo/local projection of the enterprise event outbox. Every
governance mutation should eventually route through this schema. At scale this
becomes a Postgres outbox/event stream; locally it is JSONL.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT


TRANSITIONS_LOG = REPO_ROOT / "ztare_workspace" / "transitions.jsonl"


def append_transition(
    *,
    event: str,
    actor: str,
    role_id: str | None = None,
    surface: str,
    subject: str,
    payload: dict[str, Any] | None = None,
    causality_id: str | None = None,
    log_path: Path = TRANSITIONS_LOG,
) -> dict[str, Any]:
    """Append one canonical org transition and return the record."""
    record = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "role_id": role_id,
        "surface": surface,
        "subject": subject,
        "causality_id": causality_id,
        "payload": payload or {},
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record
