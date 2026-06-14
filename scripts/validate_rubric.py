#!/usr/bin/env python3
"""Compatibility wrapper for the public rubric validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parent / "public" / "validators" / "validate_rubric.py"
    spec = importlib.util.spec_from_file_location("_ztare_public_validate_rubric", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PUBLIC_VALIDATOR = _load_module()
for _name, _value in vars(_PUBLIC_VALIDATOR).items():
    if _name not in {"__name__", "__file__", "__package__", "__spec__", "__loader__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(main())
