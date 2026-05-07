#!/usr/bin/env python3
"""One-command smoke test for the local org runtime.

This does not execute work. It verifies that the durable role contracts,
agent instructions, runtime adapter, and discovery loop can boot.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test ZTARE org runtime without executing work")
    parser.add_argument("--role", default="research_director", choices=["manager", "research_director"])
    parser.add_argument("--member-id", default="codex")
    parser.add_argument("--agent-cli", default="codex")
    parser.add_argument("--agent-adapter", default="auto", choices=["auto", "claude_print", "codex_exec"])
    args = parser.parse_args()

    checks = [
        [
            sys.executable,
            "scripts/org_role_preflight.py",
            "--role",
            args.role,
            "--agent-cli",
            args.agent_cli,
            "--json",
        ],
        [
            sys.executable,
            "scripts/agent_daemon.py",
            "--role",
            args.role,
            "--member-id",
            args.member_id,
            "--agent-cli",
            args.agent_cli,
            "--agent-adapter",
            args.agent_adapter,
            "--tick-once",
            "--dry-run",
        ],
    ]
    for cmd in checks:
        rc = run(cmd)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
