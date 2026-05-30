"""Finite-prefix selection gate.

General-purpose arithmetic check for arguments of the form:

    if sum(interface[0:N]) <= sum(boundary[0:N]),
    then some prefix event has boundary[i] >= interface[i].

The arithmetic is elementary; the gate exists to force the non-arithmetic
source contracts that make the prefix comparison meaningful.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-FINITE-PREFIX-SELECTION"


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


def _series(values: Any) -> list[Fraction]:
    if values is None:
        raise ValueError("missing series")
    if not isinstance(values, list):
        raise ValueError("series must be a list")
    if not values:
        raise ValueError("series must be nonempty")
    return [_fraction(value) for value in values]


def run_gate(
    *,
    boundary: Any,
    interface: Any,
    prefix_length: Any | None = None,
    same_source_family: bool = False,
    prefix_fixed_before_payoff: bool = False,
    boundary_interface_units_aligned: bool = False,
    no_post_payoff_selection: bool = False,
    interface_floor: Any | None = None,
) -> dict[str, Any]:
    """Check finite-prefix selection arithmetic and source-contract receipts."""
    try:
        boundary_values = _series(boundary)
        interface_values = _series(interface)
        if len(boundary_values) != len(interface_values):
            raise ValueError("boundary and interface series must have same length")
        n = len(boundary_values) if prefix_length is None else int(prefix_length)
        if n <= 0:
            raise ValueError("prefix_length must be positive")
        if n > len(boundary_values):
            raise ValueError("prefix_length exceeds supplied series")
        floor = None if interface_floor is None else _fraction(interface_floor)
    except Exception as exc:
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "hard_fail": True,
            "reason": f"invalid input: {exc}",
        }

    receipts = {
        "same_source_family": bool(same_source_family),
        "prefix_fixed_before_payoff": bool(prefix_fixed_before_payoff),
        "boundary_interface_units_aligned": bool(boundary_interface_units_aligned),
        "no_post_payoff_selection": bool(no_post_payoff_selection),
    }
    missing = [name for name, ok in receipts.items() if not ok]

    boundary_prefix = sum(boundary_values[:n], Fraction(0, 1))
    interface_prefix = sum(interface_values[:n], Fraction(0, 1))
    prefix_comparison_holds = interface_prefix <= boundary_prefix
    witnesses = [
        i for i in range(n) if boundary_values[i] >= interface_values[i]
    ]
    payment_floor_witnesses = (
        witnesses
        if floor is None
        else [i for i in witnesses if interface_values[i] >= floor]
    )
    all_boundary_below_interface = not witnesses
    floor_requested = floor is not None

    passed = (
        not missing
        and prefix_comparison_holds
        and bool(payment_floor_witnesses)
    )
    reason_parts: list[str] = []
    if missing:
        reason_parts.append("missing source-contract receipts: " + ", ".join(missing))
    if not prefix_comparison_holds:
        reason_parts.append("prefix interface sum exceeds prefix boundary sum")
    if all_boundary_below_interface:
        reason_parts.append("all boundary entries are below interface entries")
    if floor_requested and not payment_floor_witnesses:
        reason_parts.append("no boundary>=interface witness also pays the interface floor")
    if not reason_parts:
        reason_parts.append("finite prefix comparison forces a boundary>=interface event")

    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "hard_fail": not passed,
        "prefix_length": n,
        "boundary_prefix_sum": _fmt(boundary_prefix),
        "interface_prefix_sum": _fmt(interface_prefix),
        "prefix_comparison_holds": prefix_comparison_holds,
        "witness_indices": witnesses,
        "payment_floor_witness_indices": payment_floor_witnesses,
        "interface_floor": None if floor is None else _fmt(floor),
        "conclusion_strength": (
            "boundary_pays_interface_floor"
            if floor_requested and payment_floor_witnesses else
            "boundary_not_below_interface"
            if witnesses else
            "no_witness"
        ),
        "receipts": receipts,
        "missing_receipts": missing,
        "reason": "; ".join(reason_parts),
    }
