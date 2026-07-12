"""Async pending-file IO: write a finding this cycle, take-and-apply the next.

Extracted from GP-105 ``mform_alignment_audit`` so both arms of the General
Office share one implementation instead of copying it: the M-Form audit queues
a pending rubric criterion, the Strategy Office (research_director) queues a
pending commissioning receipt. A "pending" artifact is a single JSON dict at a
fixed filename; ``take_pending`` reads it once and deletes it (the async
boundary — produced after this cycle, consumed at the start of the next).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_pending(directory: "Path | str", filename: str, obj: dict[str, Any]) -> Path:
    """Write ``obj`` as pretty JSON to ``directory/filename`` (overwrite)."""
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


def take_pending(directory: "Path | str", filename: str) -> "dict | None":
    """Load-and-delete the pending dict. None if absent or unreadable
    (fail-silent: a corrupt handoff never blocks the consuming cycle)."""
    path = Path(directory) / filename
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt handoff is treated as absent
        return None
    try:
        path.unlink()
    except OSError:
        pass
    return obj if isinstance(obj, dict) else None
