#!/usr/bin/env python3
"""Compatibility entry point for the current P1 autonomous-n=1 RUNG A campaign.

The former launcher read an untracked scratch theorem and assembled its own
runtime/budget.  P1 now goes through the normal LeanMill campaign door, whose
frontmatter freezes the target, Terra runtime, budget, run identity, and
completion receipts.
"""
from __future__ import annotations

import os
from pathlib import Path

from ztare.leanmill.cli import main as leanmill_main


REPO = Path(__file__).resolve().parents[4]
BLUEPRINT = REPO / "projects" / "leanmill_experiments" / "p1_rungA_campaign.md"


def main() -> int:
    if not BLUEPRINT.is_file():
        raise FileNotFoundError(f"missing P1 campaign blueprint: {BLUEPRINT}")
    os.chdir(REPO)
    return leanmill_main(["campaign", str(BLUEPRINT)])


if __name__ == "__main__":
    raise SystemExit(main())
