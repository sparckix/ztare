#!/usr/bin/env python3
"""Shim — real implementation at ``ztare.leanmill.contracts.source_query``.

Existing ``from leanmill_source_query_contract import ...`` patterns used
by 6 worker scripts continue to work. New code should import from the
kernel directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.contracts.source_query import (  # noqa: E402, F401
    DECL_IN_STATEMENT_RE,
    DECL_RE,
    GENERIC_TOKENS,
    LEAN_IDENT_RE,
    LEAN_SHAPE_TOKENS,
    LEAN_SYMBOLS,
    PROCESS_FRAGMENTS,
    accepted_queries,
    compact_query_item,
    normalize_query_contract,
    queries_pass_gate,
    query_identity,
    query_quality,
    source_queries_from_proposal,
    __all__,
)


if __name__ == "__main__":
    from ztare.leanmill.contracts.source_query import _self_test
    raise SystemExit(_self_test())
