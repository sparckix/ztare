#!/usr/bin/env python3
"""Export local A2A-style agent cards for persistent role offices."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.ztare.orchestration.a2a_projection import build_all_agent_cards, write_agent_cards


def main() -> int:
    paths = write_agent_cards()
    print(json.dumps({
        "ok": True,
        "count": len(paths),
        "paths": [str(p) for p in paths],
        "cards": [asdict(c) for c in build_all_agent_cards()],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
