#!/usr/bin/env python3
"""Shim — real implementation at ``ztare.leanmill.policy``.

Existing ``from leanmill_factory_config import read_policy`` patterns used
by ~5 worker scripts continue to work. New code should import from
``ztare.leanmill.policy``.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.policy import (  # noqa: E402, F401
    FACTORY_POLICY,
    apply_profile_section,
    c_supply_breadth_policy,
    c_supply_breadth_policy_from_policy,
    lane_budget_plan,
    multi_node_routing_plan,
    priority_policy_from_policy,
    priority_value,
    priority_value_from_policy,
    read_policy,
    __all__,
)


if __name__ == "__main__":
    # Preserve CLI behavior of the original script.
    from ztare.leanmill.policy import main as _kernel_main
    raise SystemExit(_kernel_main())
