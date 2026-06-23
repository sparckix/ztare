#!/usr/bin/env python3
"""Compatibility entrypoint for the public Lean batched candidate generator."""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_IMPL_PATH = REPO / "scripts" / "public" / "lean" / "batched_candidate_generator.py"
_SPEC = importlib.util.spec_from_file_location("_ztare_batched_candidate_generator_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load batched candidate generator from {_IMPL_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)


if __name__ == "__main__":
    raise SystemExit(main())
