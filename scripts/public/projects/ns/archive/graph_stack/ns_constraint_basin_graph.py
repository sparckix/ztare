#!/usr/bin/env python3
"""Compatibility entrypoint for the archived NS constraint basin graph."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_IMPL_PATH = (
    REPO
    / "projects"
    / "ns_millennium_hunt"
    / "scripts"
    / "_archive"
    / "decommissioned_graph_stack_2026_05_10"
    / "graph_stack"
    / "ns_constraint_basin_graph.py"
)
_SPEC = importlib.util.spec_from_file_location("_ztare_ns_constraint_basin_graph_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load NS constraint basin graph from {_IMPL_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)


if __name__ == "__main__":
    raise SystemExit(main())
