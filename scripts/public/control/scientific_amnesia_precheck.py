#!/usr/bin/env python3
"""Run the generic scientific-amnesia history-overlap precheck."""
from __future__ import annotations

import sys
from pathlib import Path

# #49 robustness: crashed `from src.ztare...` when repo root not on
# sys.path, blocking the `scientific_amnesia` pretick leg. Put
# repo/src (for `ztare.*`) AND repo root (for daemon-style
# `src.ztare.*`) on path, try canonical then fallback. Pure import
# robustness; identical module, no logic change.
_REPO = Path(__file__).resolve().parents[3]
for _p in (str(_REPO / "src"), str(_REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from ztare.research_director.scientific_amnesia import main
except Exception:  # noqa: BLE001
    from src.ztare.research_director.scientific_amnesia import main


if __name__ == "__main__":
    raise SystemExit(main())
