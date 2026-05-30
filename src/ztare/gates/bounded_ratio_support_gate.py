"""Bounded-ratio support gate.

General-purpose check for routes where a strict mean surplus of a dimensionless
ratio only lower-bounds support mass after a same-law upper cap is supplied.
If `rho <= R` and `E[rho] >= 1 + delta`, then
`measure({rho >= 1}) >= delta / (R - 1)`. The lower bound is useful only when
it overfills the remaining threshold-space deficit with a companion lower bound.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-BOUNDED-RATIO-SUPPORT"


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    text = str(value).strip()
    if not text:
        raise ValueError("empty numeric value")
    return Fraction(text)


def _fmt(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def run_gate(*, mean_surplus: Any, ratio_upper_bound: Any,
             companion_lower_bound: Any, threshold_space_measure: Any) -> dict[str, Any]:
    """Check whether companion + mean_surplus/(R-1) overfills threshold space."""
    try:
        delta = _fraction(mean_surplus)
        r_upper = _fraction(ratio_upper_bound)
        companion = _fraction(companion_lower_bound)
        theta = _fraction(threshold_space_measure)
    except Exception as exc:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": f"invalid numeric input: {exc}",
        }

    inputs = {
        "mean_surplus": _fmt(delta),
        "ratio_upper_bound": _fmt(r_upper),
        "companion_lower_bound": _fmt(companion),
        "threshold_space_measure": _fmt(theta),
    }
    if delta < 0:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": "mean_surplus must be non-negative",
            "inputs": inputs,
        }
    if r_upper <= 1:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": "ratio_upper_bound must be greater than 1",
            "inputs": inputs,
        }

    support_lower = delta / (r_upper - 1)
    total_lower = companion + support_lower
    margin = total_lower - theta
    passed = theta < total_lower
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "hard_fail": not passed,
        "support_lower_bound": _fmt(support_lower),
        "total_lower_bound": _fmt(total_lower),
        "overfill_margin": _fmt(margin),
        "inputs": inputs,
        "reason": (
            "bounded ratio support lower bound overfills threshold space"
            if passed else
            "bounded ratio support lower bound does not overfill threshold space; mean surplus or cap is insufficient"
        ),
    }
