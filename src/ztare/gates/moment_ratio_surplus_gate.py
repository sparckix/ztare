"""Moment-ratio surplus gate.

General-purpose check for Paley-Zygmund/Cauchy-style routes where a first
moment lower bound `m` and second-moment cap `Q` only help if `m^2 / Q`
actually pays the remaining size-sum deficit.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-MOMENT-RATIO-SURPLUS"


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


def run_gate(*, first_moment_sq: Any, second_moment_cap: Any,
             cheap_boundary_lower_bound: Any, threshold_space_measure: Any) -> dict[str, Any]:
    """Check whether cheap + first_moment_sq / second_moment_cap overfills threshold space."""
    try:
        m2 = _fraction(first_moment_sq)
        q = _fraction(second_moment_cap)
        cheap = _fraction(cheap_boundary_lower_bound)
        theta = _fraction(threshold_space_measure)
    except Exception as exc:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": f"invalid numeric input: {exc}",
        }

    if q <= 0:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": "second_moment_cap must be positive",
            "inputs": {
                "first_moment_sq": _fmt(m2),
                "second_moment_cap": _fmt(q),
                "cheap_boundary_lower_bound": _fmt(cheap),
                "threshold_space_measure": _fmt(theta),
            },
        }

    ratio = m2 / q
    total_lower = cheap + ratio
    margin = total_lower - theta
    passed = theta < total_lower
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "hard_fail": not passed,
        "ratio_lower_bound": _fmt(ratio),
        "total_lower_bound": _fmt(total_lower),
        "overfill_margin": _fmt(margin),
        "inputs": {
            "first_moment_sq": _fmt(m2),
            "second_moment_cap": _fmt(q),
            "cheap_boundary_lower_bound": _fmt(cheap),
            "threshold_space_measure": _fmt(theta),
        },
        "reason": (
            "moment ratio overfills threshold space"
            if passed else
            "moment ratio does not overfill threshold space; finite second moment cap is insufficient"
        ),
    }
