"""Solver lane library — contract + dispatch + validation primitives.

The CLI worker at `scripts/public/control/leanmill/solver_lane_worker.py`
is a thin dispatcher over this library. New code imports from here.

Public API:
    from ztare.leanmill.solver.contract import (
        SOLVER_CONTRACT_SCHEMA,
        DEFAULT_PROVER_CHAIN,
        DEFAULT_ANTI_PATTERNS,
        build_solver_action_contract,
        source_cue_check,
        validate_against_contract,
        verify_matched_negative_control,
    )

The deterministic Layer 2 (FREE, no LLM) is now split from the expensive LLM
Layers 3-4 (task #42):

    from ztare.leanmill.solver.deterministic import run_deterministic_layer
    from ztare.leanmill.solver.llm_provers import run_llm_layers

`run_llm_layers` accepts an optional `gate` — the Agentic Circuit Breaker seam
(F108 / task #74) — that can short-circuit the expensive LLM provers on
low-confidence goals. The CLI worker still owns validation / MNC / ledger / DB
writes; the split modules own only the layer dispatch boundary.
"""
from __future__ import annotations
from ztare.leanmill.solver.contract import (  # noqa: F401
    SOLVER_CONTRACT_SCHEMA,
    DEFAULT_PROVER_CHAIN,
    DEFAULT_ANTI_PATTERNS,
    build_solver_action_contract,
    source_cue_check,
    validate_against_contract,
    verify_matched_negative_control,
)
from ztare.leanmill.solver.deterministic import run_deterministic_layer  # noqa: F401
from ztare.leanmill.solver.llm_provers import run_llm_layers  # noqa: F401
