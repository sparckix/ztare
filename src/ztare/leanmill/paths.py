"""Shared LeanMill local paths.

Single source of truth for path constants used by the queue, dashboards,
gates, schedulers, family-spec loader, and the eval-harness runner.

Phase A migration (2026-05-23): canonical home moved here from
``scripts/public/control/leanmill/paths.py``. The original path keeps a
thin shim that re-exports these constants so existing
``from leanmill_paths import ...`` patterns continue to work.
"""
from __future__ import annotations

import os


def _env_path(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATA_DIR = _env_path("LEANMILL_DATA_DIR", "analytics/public/leanmill/dashboard_data")
REPAIR_FAMILY_REGISTRY = f"{DATA_DIR}/repair_family_registry.json"
REPAIR_FAMILY_SPEC_DIR = _env_path("LEANMILL_REPAIR_FAMILY_SPEC_DIR", "analytics/public/leanmill/repair_families")
FACTORY_POLICY = _env_path("LEANMILL_FACTORY_POLICY", f"{DATA_DIR}/leanmill_factory_policy.json")
SCRATCH_DISCOVER_ROOT = _env_path("LEANMILL_SCRATCH_ROOT", "/tmp/rung1")


__all__ = [
    "DATA_DIR",
    "REPAIR_FAMILY_REGISTRY",
    "REPAIR_FAMILY_SPEC_DIR",
    "FACTORY_POLICY",
    "SCRATCH_DISCOVER_ROOT",
]
