"""Shared residual normalization for gate harnesses.

Normalizes absolute residuals by max observable magnitude, making gate
thresholds scale-invariant. Extracted from global_gates.py (lines 171-179)
per panel verdict 2026-04-21: absolute thresholds conflate structural failure
with calibration imprecision on large-scale observables.

Usage in gate_harness.py:
    from ztare.gates.residual_norm import normalized_max_residual
    mx = normalized_max_residual(predictions, observations)
    results["gates"]["holdout"] = {"value": mx, "threshold": 0.005, "pass": mx < 0.005}

Thresholds guide (relative, scale-invariant):
    0.005 (0.5%) — holdout global (GP-088 equivalent: 0.05/12 ≈ 0.004)
    0.004 (0.4%) — holdout upper
    0.010 (1.0%) — farther-tail global
    0.008 (0.8%) — farther-tail upper
"""

from __future__ import annotations


def normalized_max_residual(
    predictions: list[float],
    observations: list[float],
) -> float:
    """Max |pred - obs| / max(|obs|). Scale-invariant residual metric."""
    if not observations or not predictions:
        return float("inf")
    max_obs = max(abs(o) for o in observations)
    denom = max_obs if max_obs >= 1e-12 else 1.0
    residuals = [abs(o - p) / denom for o, p in zip(observations, predictions)]
    return max(residuals)
