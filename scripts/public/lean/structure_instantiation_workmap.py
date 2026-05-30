#!/usr/bin/env python3
"""CLI wrapper for the NS Track B structure-instantiation workmap.

The implementation lives with the NS workspace.  This wrapper keeps the
documented `scripts/public/lean/structure_instantiation_workmap.py` command stable without
duplicating extractor logic.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IMPL = (
    REPO
    / "projects"
    / "ns_millennium_hunt"
    / "workspace"
    / "structure_instantiation_workmap.py"
)


def _load_impl():
    spec = importlib.util.spec_from_file_location(
        "ns_structure_instantiation_workmap_impl",
        IMPL,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load workmap implementation: {IMPL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    return _load_impl().main()


if __name__ == "__main__":
    raise SystemExit(main())
