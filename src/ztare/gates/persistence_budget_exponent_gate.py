"""Persistence-budget exponent/thickness prefilter.

This gate is a cheap anti-laundering check for topological persistence
payment arguments. In dimension d, unweighted or low-exponent persistence
counts are not paid by an L2/energy-style budget unless an independent
thickness/reach/Morse-complexity receipt is supplied. Exponent p>d is treated
as the standard safe side for total-persistence style arguments; p<=d requires
extra geometry. This is a prefilter, not a theorem prover.
"""
from __future__ import annotations

from typing import Any


def run_persistence_budget_exponent_gate(
    *,
    dimension: float,
    persistence_exponent: float,
    thickness_or_reach_receipt: bool = False,
    uniform_complexity_receipt: bool = False,
    same_carrier_receipt: bool = False,
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    if dimension <= 0:
        violations.append({"kind": "invalid_dimension"})
    if persistence_exponent <= 0:
        violations.append({"kind": "invalid_exponent"})

    super_dimension = persistence_exponent > dimension
    geometric_receipt = thickness_or_reach_receipt or uniform_complexity_receipt
    if not super_dimension and not geometric_receipt:
        violations.append({
            "kind": "subcritical_persistence_exponent",
            "message": (
                "persistence exponent is not above ambient dimension; "
                "a thickness/reach or uniform complexity receipt is required"
            ),
        })
    if not same_carrier_receipt:
        violations.append({
            "kind": "same_carrier_receipt_missing",
            "message": "persistence debit must be bound to the payment carrier",
        })

    return {
        "gate_id": "G-PERSISTENCE-BUDGET-EXPONENT",
        "passed": not violations,
        "dimension": dimension,
        "persistence_exponent": persistence_exponent,
        "super_dimension": super_dimension,
        "thickness_or_reach_receipt": thickness_or_reach_receipt,
        "uniform_complexity_receipt": uniform_complexity_receipt,
        "same_carrier_receipt": same_carrier_receipt,
        "violations": violations,
    }


def format_persistence_budget_exponent_report(result: dict[str, Any]) -> str:
    status = "PASS" if result.get("passed") else "FAIL"
    exponent = result.get("persistence_exponent")
    dimension = result.get("dimension")
    super_dimension = result.get("super_dimension")
    return (
        f"{status}: p={exponent} in "
        f"dimension d={dimension} "
        f"(super_dimension={super_dimension})"
    )
