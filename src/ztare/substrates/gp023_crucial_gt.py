"""Ground truth substrate — GP-083 Crucial Experiment (Division A only).

Variable key (Division A internal):
  x1 = norm_freq   (normalised first input variable)
  x2 = norm_temp   (normalised second input variable)
  z  = normalised output (continuous scalar)

Division A/B isolation: the public API uses only generic names (x1, x2, z).
No domain-identifying terms appear in the exported symbols or docstrings.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Core law (Division A only — do not expose to mutator or judge prompts)
# f_true(x1, x2) = x1**3 / (exp(x1 / x2) - 1)
# Guard: if x1/x2 > 500 the exponential overflows — return 0.0.
# ---------------------------------------------------------------------------


def f_true(x1: float, x2: float) -> float:
    """Return the exact ground-truth output for normalised inputs x1 and x2."""
    ratio = x1 / x2
    if ratio > 500.0:
        return 0.0
    denom = math.exp(ratio) - 1.0
    if denom == 0.0:
        return 0.0
    return x1 ** 3 / denom


# Alias for residual-diagnostics compatibility (f_dominant is the same as f_true for
# single-regime substrates — added post-run 2026-04-18).
f_dominant = f_true


# ---------------------------------------------------------------------------
# Evidence grids
# ---------------------------------------------------------------------------

_X1_VALS = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
_X2_VISIBLE = [0.5, 1.0, 2.0]
_X2_HOLDOUT = [0.75, 1.5]


def evidence_grid() -> list[tuple[float, float, float]]:
    """Return 24 clean (x1, x2, z) triples for the visible set."""
    pts: list[tuple[float, float, float]] = []
    for x2 in _X2_VISIBLE:
        for x1 in _X1_VALS:
            pts.append((x1, x2, f_true(x1, x2)))
    return pts


def holdout_grid() -> list[tuple[float, float, float]]:
    """Return 16 clean (x1, x2, z) triples for the holdout set (unseen x2 values)."""
    pts: list[tuple[float, float, float]] = []
    for x2 in _X2_HOLDOUT:
        for x1 in _X1_VALS:
            pts.append((x1, x2, f_true(x1, x2)))
    return pts
