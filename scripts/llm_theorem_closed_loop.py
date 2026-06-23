#!/usr/bin/env python3
"""Compatibility entrypoint for the theorem closed-loop script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_IMPL_PATH = REPO / "scripts" / "public" / "analytics_shared" / "llm_theorem_closed_loop.py"
_SPEC = importlib.util.spec_from_file_location("_ztare_llm_theorem_closed_loop_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load theorem closed-loop script from {_IMPL_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)


if __name__ == "__main__":
    raise SystemExit(main())
