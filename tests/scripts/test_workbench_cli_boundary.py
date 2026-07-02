"""Architectural invariant: workbench UI integrations go through the CLI.

The forensic-workbench local API must never invoke a kernel module directly.
Every command it builds with `python -m <module>` must target the public
`ztare` CLI (`src.ztare.cli`), which in turn calls the kernel. This keeps one
integration contract for terminal users and the workbench, and stops the server
from becoming a second runtime.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "scripts" / "public" / "control" / "forensic_workbench_server.py"

# `"-m", "<module>"`, tolerant of whitespace/newlines between the tokens.
_DASH_M = re.compile(r'"-m"\s*,\s*"([A-Za-z0-9_.]+)"')


def test_workbench_commands_route_through_the_cli() -> None:
    text = SERVER.read_text(encoding="utf-8")
    targets = _DASH_M.findall(text)
    assert targets, "expected the workbench to build at least one `-m` command"
    bypasses = sorted({t for t in targets if t != "src.ztare.cli"})
    assert not bypasses, (
        "workbench builds commands that bypass the ztare CLI to call kernel "
        f"modules directly: {bypasses}. Route them through `src.ztare.cli` "
        "(a `ztare <verb>` subcommand) instead."
    )
