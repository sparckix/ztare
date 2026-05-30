#!/usr/bin/env python3
"""Shim - real implementation at ``ztare.leanmill.contracts.learning_feedback``."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ztare.leanmill.contracts.learning_feedback import (  # noqa: E402,F401
    FAILURE_EVIDENCE_KEYS,
    NEGATIVE_CONTROL_INVALID_FAILURE_MARKERS,
    NONUSEFUL_PROBE_EXITS,
    PROOF_VALUE_EXIT_KINDS,
    SCHEMA,
    TERMINAL_DECISION_EXIT_KINDS,
    TESTED_LEARNING_EXIT_KINDS,
    compact_failure_evidence,
    compact_feedback_entries,
    feedback_entry,
    int_count,
    learning_exit_from_counts,
    negative_control_invalid_failure,
)


if __name__ == "__main__":
    from ztare.leanmill.contracts.learning_feedback import _self_test

    raise SystemExit(_self_test())
