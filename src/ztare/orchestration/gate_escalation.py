"""GP-070 Goal Orchestrator — Gate escalation (C-5, C-8).

Writes gate escalation JSON to the executive inbox directory,
reusing the GP-036 D4 adapter pattern.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

INBOX_DIR = Path("ztare_workspace/gates/pending")


def write_gate_escalation(
    *,
    goal_slug: str,
    goal_name: str,
    stage: str,
    gate_description: str,
    gate_reason: str = "",
    artifact_hashes: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a gate escalation to the executive inbox."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now(datetime.timezone.utc)
    filename = f"goal_{goal_slug}_{stage}_{int(ts.timestamp() * 1_000_000)}.json"
    escalation = {
        "type": "goal_gate_escalation",
        "goal_slug": goal_slug,
        "goal_name": goal_name,
        "stage": stage,
        "gate_description": gate_description,
        "gate_reason": gate_reason,
        "artifact_hashes": artifact_hashes or {},
        "timestamp_utc": ts.isoformat(),
        "metadata": metadata or {},
    }

    path = INBOX_DIR / filename
    path.write_text(json.dumps(escalation, indent=2) + "\n")
    return path
