"""Layers 3-4 — LLM provers (warm agent + cold-shot fan-out): EXPENSIVE.

This is the LLM half of the solver lane, split out from the monolithic dispatch
in `scripts/public/control/leanmill/solver_lane_worker.py` (task #42). These
layers cost money and hit the network:

  Layer 3 — warm agent (Claude, Bash+Edit+Read enabled, iterates on `lake env
            lean` verdicts in a scratch dir). High P(close), but a full agent run.
  Layer 4 — cold-shot multi-provider fan-out (claude_opus / codex_gpt5 /
            gemini_flash / deepseek_v2), one-shot per provider, kernel-verified.

Splitting these from the deterministic Layer 2 (`deterministic.run_deterministic_layer`)
creates the clean boundary the apparatus needs: run the FREE deterministic layer
first, and only escalate to these EXPENSIVE LLM layers if a gate allows.

============================================================================
THE AGENTIC CIRCUIT BREAKER SEAM (F108, task #74)
============================================================================
`run_llm_layers` accepts an optional `gate: Callable[[dict], bool] | None`.

This is the metacognition insertion point. A caller can pass a gate that
elicits P(close) for the goal (e.g. an LLM judge or a calibrated probe) and
returns True only when `p_mid >= threshold`. When the gate returns False, the
LLM layers SHORT-CIRCUIT: no warm agent is spawned, no provider is invoked, and
the function returns `{closed: False, skipped_by_gate: True, ...}`. This lets a
caller refuse to spend expensive LLM budget on low-confidence goals — the
"Agentic Circuit Breaker" — without touching the deterministic layer or the
credit/validation logic.

When `gate is None` (the DEFAULT), this module behaves EXACTLY as the inline
Layer 3-4 dispatch did before the split: warm agent first, then cold-shot
fan-out, with no skip. The default path is behavior-preserving.

Design note (WRAP, not MOVE): the warm agent (`_agentic_leaf_warm_solve`, the single leaf entry) and the
cold-shot fan-out are deeply interleaved with the worker's credit/validation
machinery — the contract validation gate, the matched-negative-control check,
the carrier-receipt ledger, and the attempts-DB writes. The task constraint is
to leave that machinery untouched and only restructure the *layer dispatch*. So
this module is a thin WRAPPER: the worker injects its layer-runner callables
(warm-agent runner, cold-shot runner) and this module owns only (a) the gate
short-circuit and (b) the Layer 3 → Layer 4 ordering. Validation, MNC, ledger,
and DB writes stay in the worker callables.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

# Gate: given the row, decide whether the expensive LLM layers may run.
# Return True to allow (run the layers), False to short-circuit (skip, no LLM).
Gate = Callable[[dict], bool]

# A layer runner returns a closed-result dict (truthy → a credit-ready closure
# was produced and the caller should stop) or None (no closure → walk on).
# The worker supplies these; they own validation / MNC / ledger / DB writes.
LayerRunner = Callable[[], Optional[dict]]


def run_llm_layers(
    row: dict,
    lean_root: Path,
    timeout_s: int,
    *,
    gate: Optional[Gate] = None,
    warm_agent_layer: LayerRunner,
    cold_shot_layer: LayerRunner,
) -> dict:
    """Run Layers 3-4 (warm agent + cold-shot fan-out) for one row.

    Args:
        row: solver slice row.
        lean_root: Lean project root for verification.
        timeout_s: budget for the LLM layers.
        gate: optional Agentic Circuit Breaker (F108 / task #74). If provided and
            it returns False, SHORT-CIRCUIT before spawning any LLM and return
            `{closed: False, skipped_by_gate: True, ...}`. If None (default),
            behave exactly as the pre-split inline dispatch (no skip).
        warm_agent_layer: zero-arg callable running Layer 3 (warm agent) plus its
            validation/ledger/DB side effects; returns a closed-result dict on a
            credit-ready closure, else None.
        cold_shot_layer: zero-arg callable running Layer 4 (cold-shot fan-out)
            plus its validation/ledger/DB side effects; returns a closed-result
            dict on a credit-ready closure, else None.

    Returns:
        dict with:
            closed:          bool — was a credit-ready closure produced?
            closed_result:   dict | None — the worker's closed-result payload.
            layer:           "warm_agent" | "cold_shot" | "none" — closing layer.
            skipped_by_gate: bool — True iff the gate short-circuited the layers.
    """
    # ── Agentic Circuit Breaker: refuse to spend LLM budget on low-confidence
    # goals. When the gate denies, NO warm agent and NO provider are invoked.
    if gate is not None and not gate(row):
        return {
            "closed": False,
            "closed_result": None,
            "layer": "none",
            "skipped_by_gate": True,
        }

    # ── Layer 3: warm agent (iterative). Higher P(close) than one-shot.
    warm_closed = warm_agent_layer()
    if warm_closed is not None:
        return {
            "closed": True,
            "closed_result": warm_closed,
            "layer": "warm_agent",
            "skipped_by_gate": False,
        }

    # ── Layer 4: cold-shot multi-provider fan-out.
    cold_closed = cold_shot_layer()
    if cold_closed is not None:
        return {
            "closed": True,
            "closed_result": cold_closed,
            "layer": "cold_shot",
            "skipped_by_gate": False,
        }

    return {
        "closed": False,
        "closed_result": None,
        "layer": "none",
        "skipped_by_gate": False,
    }
