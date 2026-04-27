"""G-SYM-FN — SymmetryScanner False-Negative Gate (v2.0).

Failure mode caught: SymmetryScanner's empirical exponent / separability tests
have a non-zero false-negative rate. A missed symmetry causes the Framer to
enumerate over a restricted Σ that excludes the right (h_in, h_out).

Detection: for a small set of canary substrates with KNOWN symmetries, run
SymmetryScanner against synthetic instances. Measure detection rate.

Pass: detection rate ≥ 0.95 across 60 canaries.

Per spec v2.0 §4.3.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


GATE_ID = "G-SYM-FN"
DEFAULT_DETECTION_THRESHOLD = 0.95
DEFAULT_CANARY_COUNT = 60


def _gen_power_law_canary(seed: int, n: int = 200) -> tuple[np.ndarray, np.ndarray, str]:
    rng = np.random.default_rng(seed)
    alpha = rng.uniform(-3.0, 3.0)
    while abs(alpha) < 0.2:
        alpha = rng.uniform(-3.0, 3.0)
    coeff = rng.uniform(0.5, 5.0)
    x = np.linspace(1.0, 10.0, n)
    y = coeff * x ** alpha
    sigma = 0.01 * float(np.std(y))
    y_noisy = y + rng.normal(0, sigma, size=n)
    return x, y_noisy, "power_law"


def run_symmetry_false_negative_gate(
    canary_count: int = DEFAULT_CANARY_COUNT,
    detection_threshold: float = DEFAULT_DETECTION_THRESHOLD,
    seed_base: int = 1000,
) -> Dict[str, Any]:
    """Run G-SYM-FN by generating canary substrates with known symmetries
    and counting how many SymmetryScanner correctly identifies.
    """
    from src.ztare.framer.symmetry import scan_symmetries

    correct = 0
    total = 0
    misses: List[Dict[str, Any]] = []
    for i in range(canary_count):
        x, y, true_sym = _gen_power_law_canary(seed_base + i)
        report = scan_symmetries(x, y)
        if true_sym == "power_law" and report.is_power_law:
            correct += 1
        else:
            misses.append({"seed": seed_base + i, "true": true_sym, "detected_power_law": report.is_power_law})
        total += 1
    detection_rate = correct / max(total, 1)
    passed = detection_rate >= detection_threshold
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "detection_rate": detection_rate,
        "threshold": detection_threshold,
        "n_canaries": total,
        "n_correct": correct,
        "n_missed": len(misses),
        "first_3_misses": misses[:3],
        "rationale": (
            f"power-law detection rate {detection_rate:.3f} "
            f"{'≥' if passed else '<'} {detection_threshold}"
        ),
    }
