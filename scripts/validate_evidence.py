#!/usr/bin/env python3
"""Compatibility wrapper for `scripts/public/validators/validate_evidence.py`."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_REAL = (
    Path(__file__).resolve().parent
    / "public"
    / "validators"
    / "validate_evidence.py"
)
_SPEC = importlib.util.spec_from_file_location("_ztare_validate_evidence_public", _REAL)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"cannot load validator wrapper target: {_REAL}")

_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

globals().update(
    {
        name: getattr(_MOD, name)
        for name in dir(_MOD)
        if not (name.startswith("__") and name not in {"__doc__", "__all__"})
    }
)


if __name__ == "__main__":
    raise SystemExit(_MOD.main())
