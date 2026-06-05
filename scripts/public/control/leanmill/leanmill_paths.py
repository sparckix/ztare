#!/usr/bin/env python3
"""Compat shim — re-exports the LeanMill paths from ``ztare.leanmill.paths``.

~46 leanmill scripts (workers, governance_worker, proof_audit) import via the
sibling pattern ``from leanmill_paths import …``. The sibling `paths.py` is the
same shim but under a different name; this file restores the name the importers
expect (it was missing on the cleanup branch, which broke the whole suite incl.
governance). New code should import ``ztare.leanmill.paths`` directly.
"""
from __future__ import annotations
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.paths import (  # noqa: E402,F401
    DATA_DIR,
    FACTORY_POLICY,
    REPAIR_FAMILY_REGISTRY,
    REPAIR_FAMILY_SPEC_DIR,
    SCRATCH_DISCOVER_ROOT,
    __all__,
)
