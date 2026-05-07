#!/usr/bin/env python3
"""Summarize the three local inboxes without mutating state."""

from __future__ import annotations

import json
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT
from src.ztare.orchestration.agent_channels import list_agent_messages
from src.ztare.orchestration.goals_inbox import list_pending_goals
from src.ztare.signals.damage import list_recent


def _pending_gate_count() -> int:
    root = REPO_ROOT / "ztare_workspace" / "gates" / "pending"
    return len(list(root.glob("*.json"))) if root.exists() else 0


def _role_ids() -> list[str]:
    root = REPO_ROOT / "org" / "roles"
    return sorted(p.stem for p in root.glob("*.yaml")) if root.exists() else []


def main() -> int:
    agent_messages = {
        role_id: len(list_agent_messages(role_id=role_id, status="open", limit=1000))
        for role_id in _role_ids()
    }
    payload = {
        "ok": True,
        "executive_gate_inbox_pending": _pending_gate_count(),
        "task_inbox_pending": len(list_pending_goals()),
        "agent_channel_open_by_role": {
            k: v for k, v in agent_messages.items() if v
        },
        "unresolved_damage_signals_sample": len(list_recent(limit=100)),
        "semantics": {
            "executive_gate_inbox": "ztare_workspace/gates/pending/ — principal decisions",
            "task_inbox": "org/tasks/pending/ — assignable work",
            "agent_channel_inbox": "org/channels/<role>/inbox/ — role-to-role obligations",
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
