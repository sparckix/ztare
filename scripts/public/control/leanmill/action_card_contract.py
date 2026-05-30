#!/usr/bin/env python3
"""Shim - real implementation at ``ztare.leanmill.contracts.action_card``."""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.contracts.action_card import (  # noqa: E402,F401
    ACTION_CARD_SCHEMA,
    REQUIRED_ACTION_CARD_FIELDS,
    build_action_card,
    validate_action_card,
    __all__,
)


if __name__ == "__main__":
    from ztare.leanmill.contracts.action_card import _self_test
    raise SystemExit(_self_test())
