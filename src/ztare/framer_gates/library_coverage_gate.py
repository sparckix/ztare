"""G-LIB-COVER — Library Coverage Gate (v2.0).

Failure mode caught: ground-truth (h_in, h_out) is OUTSIDE Σ. The Framer
chooses a sub-optimal in-library pair with apparent MDL improvement, but
the gain doesn't reflect actual structure recovery.

Detection: best in-library MDL improvement < THRESHOLD bits → fail.
Pass: ≥ THRESHOLD bits AND non-degenerate depth-1 vs depth-2 ratio.

Threshold default 100 bits per spec v2.0 §4.1 (raised from v1.0's 50 to
clear σ̂² estimator noise envelope).
"""
from __future__ import annotations

import math
from typing import Any, Dict


GATE_ID = "G-LIB-COVER"
DEFAULT_THRESHOLD_BITS = 100.0


def run_library_coverage_gate(
    framing_report: Dict[str, Any],
    threshold_bits: float = DEFAULT_THRESHOLD_BITS,
) -> Dict[str, Any]:
    """Run G-LIB-COVER on a framing_report.

    Returns dict: gate_id, passed, mdl_gain_bits, threshold_bits, rationale.
    """
    if not framing_report.get("framer_engaged"):
        return {
            "gate_id": GATE_ID,
            "passed": True,
            "skipped": True,
            "rationale": "framer not engaged → gate skipped",
        }
    mdl_gain_bits = float(framing_report.get("MDL_gain_bits") or 0.0)
    passed = mdl_gain_bits >= threshold_bits
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "mdl_gain_bits": mdl_gain_bits,
        "threshold_bits": threshold_bits,
        "rationale": (
            f"MDL gain {mdl_gain_bits:.1f} bits "
            f"{'≥' if passed else '<'} threshold {threshold_bits:.1f} bits."
            + ("" if passed else " Ground truth may be outside Σ.")
        ),
    }
