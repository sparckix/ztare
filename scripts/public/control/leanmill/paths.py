#!/usr/bin/env python3
"""Shim — the real LeanMill paths module lives at ``ztare.leanmill.paths``.

This file exists so that the existing sibling-import pattern
``from leanmill_paths import FACTORY_POLICY`` used by ~6 worker scripts
continues to work without modification. New code should import from
``ztare.leanmill.paths`` directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.paths import (  # noqa: E402, F401
    DATA_DIR,
    FACTORY_POLICY,
    REPAIR_FAMILY_REGISTRY,
    REPAIR_FAMILY_SPEC_DIR,
    SCRATCH_DISCOVER_ROOT,
    __all__,
)
