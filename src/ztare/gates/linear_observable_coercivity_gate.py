"""G-LINEAR-OBS-COERCIVITY -- rank/coercivity gate for linear observables.

Dimensional and Buckingham-pi checks can say that an observable has the
right physical units while missing the algebraic information needed to
recover or dominate the target structure.  This gate checks that separate
contract: a linear observation map must have enough rank on the declared
target, or the caller must explicitly supply a quotient/kernel receipt.

The gate is substrate-agnostic.  A caller supplies only dimensions/ranks and
receipt flags; NS-specific tensors, carriers, or packets belong in the
project-level consumer.
"""
from __future__ import annotations

from typing import Any, Mapping

GATE_ID = "G-LINEAR-OBS-COERCIVITY"
GATE_NAME = "linear_observable_coercivity"


def _nonnegative_int(value: Any, name: str) -> tuple[int | None, dict[str, Any] | None]:
    try:
        out = int(value)
    except Exception:
        return None, {"kind": "invalid_integer", "field": name, "value": value}
    if out < 0:
        return None, {"kind": "negative_integer", "field": name, "value": value}
    return out, None


def run_gate(
    *,
    target_dimension: int,
    observable_rank: int,
    full_reconstruction_receipt: bool = False,
    coercivity_receipt: bool = False,
    kernel_quotient_dimension: int | None = None,
    kernel_quotient_receipt: bool = False,
    kernel_witness_present: bool = False,
    dimensionally_compatible: bool | None = None,
    labels: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Check whether a linear observable can pay a target-structure claim.

    Parameters are finite-dimensional metadata, not substrate objects.
    ``target_dimension`` is the dimension of the declared structure to recover
    or dominate; ``observable_rank`` is the rank of the actual observation map
    restricted to that structure.  Adequate rank still needs a receipt naming
    the reconstruction/coercivity argument.  Rank-deficient maps may pass only
    when the claim is explicitly downgraded to a quotient and that quotient is
    also receipted.
    """
    labels = dict(labels or {})
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    target, err = _nonnegative_int(target_dimension, "target_dimension")
    if err:
        violations.append(err)
        target = 0
    rank, err = _nonnegative_int(observable_rank, "observable_rank")
    if err:
        violations.append(err)
        rank = 0
    if target == 0 and not violations:
        violations.append({"kind": "zero_target_dimension", "field": "target_dimension"})

    quotient = None
    if kernel_quotient_dimension is not None:
        quotient, err = _nonnegative_int(
            kernel_quotient_dimension, "kernel_quotient_dimension"
        )
        if err:
            violations.append(err)

    if dimensionally_compatible is False:
        warnings.append({
            "kind": "dimensionally_incompatible",
            "detail": "Rank/coercivity analysis is secondary to a failed dimensional check.",
        })

    rank_deficient = rank < target
    receipt_present = bool(full_reconstruction_receipt or coercivity_receipt)

    if rank_deficient:
        if coercivity_receipt or full_reconstruction_receipt:
            violations.append({
                "kind": "contradictory_rank_receipt",
                "target_dimension": target,
                "observable_rank": rank,
                "detail": "A full-target reconstruction/coercivity receipt contradicts rank < target dimension.",
            })
        quotient_ok = (
            quotient is not None
            and quotient <= rank
            and kernel_quotient_receipt
        )
        if not quotient_ok:
            violations.append({
                "kind": "observable_rank_defect",
                "target_dimension": target,
                "observable_rank": rank,
                "kernel_witness_present": bool(kernel_witness_present),
                "missing": "full-rank reconstruction/coercivity receipt or receipted quotient target",
            })
    elif not receipt_present:
        violations.append({
            "kind": "missing_reconstruction_or_coercivity_receipt",
            "target_dimension": target,
            "observable_rank": rank,
            "missing": "full_reconstruction_receipt or coercivity_receipt",
        })

    passed = not violations
    if passed and quotient is not None and quotient < target:
        warnings.append({
            "kind": "quotient_target_only",
            "target_dimension": target,
            "kernel_quotient_dimension": quotient,
            "detail": "The receipt supports only the declared quotient target, not the full target.",
        })

    if passed:
        reason = "observable rank/coercivity contract discharged"
    elif rank_deficient:
        reason = "observable rank is too small for the declared target without a receipted quotient"
    else:
        reason = "observable has enough rank numerically but lacks a reconstruction/coercivity receipt"

    return {
        "gate_id": GATE_ID,
        "gate_name": GATE_NAME,
        "passed": passed,
        "hard_fail": not passed,
        "target_dimension": target,
        "observable_rank": rank,
        "rank_deficient": rank_deficient,
        "dimensionally_compatible": dimensionally_compatible,
        "receipts": {
            "full_reconstruction_receipt": bool(full_reconstruction_receipt),
            "coercivity_receipt": bool(coercivity_receipt),
            "kernel_quotient_receipt": bool(kernel_quotient_receipt),
        },
        "kernel_quotient_dimension": quotient,
        "kernel_witness_present": bool(kernel_witness_present),
        "labels": labels,
        "violations": violations,
        "warnings": warnings,
        "reason": reason,
    }


def format_report(result: Mapping[str, Any]) -> str:
    """One-line report for workbench packs and RD receipts."""
    if result.get("passed"):
        return (
            "PASS rank/coercivity: observable rank "
            f"{result.get("observable_rank")} supports target dimension "
            f"{result.get("target_dimension")} with receipts {result.get("receipts")}."
        )
    kinds = [v.get("kind") for v in result.get("violations", [])]
    return (
        "FAIL rank/coercivity: "
        f"observable rank {result.get("observable_rank")} vs target dimension "
        f"{result.get("target_dimension")}; violations={kinds}."
    )
