"""G-OWNER-PREIMAGE-PREFIX — advisory gate for GP-219 proto-op pec_k.

Checks whether a phase-space packet ownership receipt contains the numerical
selected-prefix owner-preimage inequality, rather than only pointwise owner
payment, finite atom budget, or qualitative no-reuse language.
"""
from __future__ import annotations

from typing import Any


REQUIRED_RECEIPT_FIELDS = (
    "owner_map",
    "pre_payoff_timing",
    "full_output_scale_owner",
    "pointwise_payment",
    "finite_atom_budget",
    "multiplicity_bound",
    "owner_preimage_prefix_inequality",
)


WEAK_SUBSTITUTE_FIELDS = (
    "pointwise_payment",
    "finite_atom_budget",
    "owner_map_nonconstant",
    "finite_owner_palette",
    "bounded_local_fanout",
    "per_lineage_uniqueness",
    "same_carrier_no_reuse",
)


def _present(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if not text:
            return False
        false_exact_matches = {
            "missing",
            "absent",
            "unknown",
            "todo",
            "owed",
            "unpaid",
            "not supplied",
            "not provided",
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_owner_preimage_prefix_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
    expect_receipt: bool = False,
) -> dict[str, Any]:
    """Verify pec_k owner-preimage prefix receipts.

    Args:
        rubric_data: metadata containing `owner_preimage_receipts`, a list of
          receipt dicts. Each complete receipt needs the fields in
          REQUIRED_RECEIPT_FIELDS.
        enforce_block: if true, missing fields produce passed=False.
        expect_receipt: if true, zero receipts is an advisory violation.
    """

    rubric_data = rubric_data or {}
    receipts = rubric_data.get("owner_preimage_receipts") or []
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(receipts, list):
        violations.append({
            "type": "owner_preimage_receipts_malformed",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "owner_preimage_receipts must be a list of receipt dicts",
        })
        receipts = []

    if expect_receipt and not receipts:
        violations.append({
            "type": "owner_preimage_receipt_missing",
            "severity": "advisory",
            "reason": (
                "pec_k was selected but no owner_preimage_receipts were declared. "
                "Declare the owner map, timing, output-scale owner eligibility, "
                "pointwise payment, finite atom budget, multiplicity bound, and "
                "selected-prefix owner-preimage inequality."
            ),
        })
        warnings.append("pec_k selected with no owner_preimage_receipts")

    n_complete = 0
    for i, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            violations.append({
                "type": "owner_preimage_receipt_malformed",
                "receipt_index": i,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "owner_preimage_receipts entries must be dicts",
            })
            continue

        missing = [
            field for field in REQUIRED_RECEIPT_FIELDS
            if not _present(receipt.get(field))
        ]
        if missing:
            violations.append({
                "type": "owner_preimage_receipt_incomplete",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "missing_fields": missing,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": (
                    "phase-space ownership must include the numerical "
                    "selected-prefix owner-preimage inequality; pointwise "
                    "payment, finite atom budget, finite owner palette, and "
                    "bounded fanout are weak substitutes"
                ),
            })
            warnings.append(
                f"owner_preimage_receipts[{i}] missing: {', '.join(missing)}"
            )
            continue

        weak_present = [
            field for field in WEAK_SUBSTITUTE_FIELDS
            if _present(receipt.get(field))
        ]
        if weak_present and not _present(receipt.get("owner_preimage_prefix_inequality")):
            violations.append({
                "type": "owner_preimage_prefix_replaced_by_weak_substitutes",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "weak_substitutes": weak_present,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": (
                    "weak owner/no-reuse fields were declared without the "
                    "selected-prefix owner-preimage inequality"
                ),
            })
            continue

        n_complete += 1

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = not blocking if enforce_block else True

    summary_parts = [
        f"{len(receipts)} owner-preimage receipt(s) declared",
        f"{n_complete} complete",
    ]
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "n_receipts_declared": len(receipts),
        "n_complete_receipts": n_complete,
        "required_fields": list(REQUIRED_RECEIPT_FIELDS),
        "summary": "; ".join(summary_parts),
    }


def _self_test() -> None:
    weak = run_owner_preimage_prefix_gate({
        "owner_preimage_receipts": [{
            "name": "pointwise_only",
            "owner_map": "ownerOfEvent",
            "pointwise_payment": "eventPay e <= atomCharge (owner e)",
            "finite_atom_budget": "prefix atomCharge <= B",
        }],
    })
    assert weak["passed"] is True
    assert any(
        v["type"] == "owner_preimage_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_owner_preimage_prefix_gate({
        "owner_preimage_receipts": [{
            "name": "scaled_prefix",
            "owner_map": "ownerOfEvent",
            "pre_payoff_timing": "owner fixed before payoff",
            "full_output_scale_owner": "owner is output-scale packet",
            "pointwise_payment": "eventPay e <= atomCharge (owner e)",
            "finite_atom_budget": "prefix atomCharge <= B",
            "multiplicity_bound": "M",
            "owner_preimage_prefix_inequality": (
                "prefix eventPay N <= M * prefix atomCharge (A N)"
            ),
        }],
    })
    assert strong["n_complete_receipts"] == 1
    assert not strong["violations"]


if __name__ == "__main__":
    _self_test()
