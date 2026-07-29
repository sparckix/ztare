"""Layer 2 — deterministic native-hammer attack (FREE, no LLM, no network).

This is the deterministic half of the solver lane, split out from the
monolithic dispatch in `scripts/public/control/leanmill/solver_lane_worker.py`
(task #42). It is the cheap, free, kernel-only first attack: the Mathlib tactic
cascade (aesop / simp_all / omega / polyrith / ...) run against the enriched
context. No LLM cost, no provider calls.

Splitting Layer 2 from Layers 3-4 creates a clean boundary so a caller can run
the free deterministic layer FIRST, and only escalate to the expensive LLM
provers (see `llm_provers.run_llm_layers`) when a gate allows. This module is
the deterministic side of that seam.

Design note (WRAP, not MOVE): `_native_hammer_probe` in the worker depends on
several module-level worker helpers (`_build_solver_context`, `_verify_compile`,
`_NATIVE_HAMMER_TACTICS`, `_strip_proof_text`) that themselves close over the
worker's `REPO` constant and the semantic-premise-shelf import. Moving the pure
function here would drag those module-level deps along and risk breaking the
worker's many existing references. So this is a thin wrapper: the caller passes
the worker's `_native_hammer_probe` callable in and receives the typed outcome
without duplicating the cascade implementation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal


NativeHammerDisposition = Literal["closed", "exhausted", "unavailable"]


@dataclass(frozen=True)
class NativeHammerProbeResult:
    """Typed outcome of one deterministic tactic-cascade invocation.

    ``exhausted`` is the only admissible miss: every tactic ran and returned a
    normal non-close.  A cap, timeout, checker fault, or assembly fault is
    ``unavailable`` and must not enter move calibration as mathematical
    counterevidence.
    """

    disposition: NativeHammerDisposition
    proof: str = ""
    transcript: str = ""

    @property
    def closed(self) -> bool:
        return self.disposition == "closed"

    @property
    def admissible_negative(self) -> bool:
        return self.disposition == "exhausted"

    @property
    def available(self) -> bool:
        return self.disposition != "unavailable"


# The native-hammer probe signature: (row, lean_root, timeout_s) -> typed result.
NativeHammerProbe = Callable[[dict, Path, int], NativeHammerProbeResult]


def run_deterministic_layer(
    row: dict,
    lean_root: Path,
    timeout_s: int,
    *,
    native_hammer_probe: NativeHammerProbe,
) -> dict:
    """Run Layer 2 (the deterministic native-hammer tactic cascade) for one row.

    Args:
        row: solver slice row (row_id, goal, source_file, target_theorem_name).
        lean_root: Lean project root for `lake env lean` verification.
        timeout_s: total budget for the cascade (per-tactic budget is derived
            inside the probe).
        native_hammer_probe: the worker's `_native_hammer_probe` callable. Passed
            in (rather than imported) to avoid a heavy worker-module import and
            its `REPO`/semantic-shelf side effects at import time. Returns
            a :class:`NativeHammerProbeResult`.

    Returns:
        dict with:
            closed:      bool — did a tactic close the goal under the kernel?
            proof:       str  — the winning tactic text (empty if none closed).
            tail:        str  — transcript tail from the cascade.
            layer:       "native_hammer"
            wallclock_s: float — wall-clock seconds spent in the cascade.

    This does NOT run validation / MNC / ledger / attempts-DB writes — those stay
    in the worker (the contract requires the credit/validation logic to be
    unchanged). This function only owns the deterministic attack itself.
    """
    start = time.time()
    result = native_hammer_probe(row, lean_root, timeout_s)
    # Compatibility for injected third-party/test probes while the production
    # owner uses the typed result above.  A legacy false cannot prove that the
    # full cascade was available and exhausted, so it is unavailable.
    if not isinstance(result, NativeHammerProbeResult):
        compile_ok, proof, tail = result
        result = NativeHammerProbeResult(
            "closed" if compile_ok else "unavailable",
            proof or "",
            tail or "",
        )
    return {
        "closed": result.closed,
        "proof": result.proof,
        "tail": result.transcript,
        "disposition": result.disposition,
        "available": result.available,
        "admissible_negative": result.admissible_negative,
        "layer": "native_hammer",
        "wallclock_s": round(time.time() - start, 2),
    }
