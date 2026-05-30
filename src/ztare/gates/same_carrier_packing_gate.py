"""G-SAME-CARRIER-PACKING — packing/no-reuse injection receipt gate.

Substrate-neutral gate for arguments that spend a family of local payments as a
single finite prefix/global budget.  It forces the caller to provide the
assignment map, same-carrier binding, overlap/multiplicity bound, budget
inequality, pre-payoff timing, and anti-nested-reuse receipts before a packing
or no-reuse claim can be consumed.
"""
from __future__ import annotations

from typing import Any

GATE_ID = "G-SAME-CARRIER-PACKING"

REQUIRED_FIELDS = (
    "source_carrier",
    "target_payment_family",
    "assignment_or_injection_map",
    "assignment_total_on_prefix",
    "same_carrier_binding",
    "overlap_or_multiplicity_bound",
    "finite_prefix_budget",
    "pre_payoff_timing",
    "no_nested_reuse",
    "no_rebilling_same_atom",
)

WEAK_SUBSTITUTES = (
    "same_label",
    "packing_label",
    "bounded_overlap_label",
    "finite_budget_label",
    "pointwise_payment_only",
    "locality_label",
    "after_the_fact_subcover",
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


def run_same_carrier_packing_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate same-carrier packing/no-reuse receipts.

    The gate does not prove a packing theorem. It rejects the common shortcut
    where local or pointwise payments are summed after declaring a packing label,
    while the source carrier, assignment map, multiplicity, or nested-reuse
    exclusion is missing.
    """
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "same_carrier_packing_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "summary": "malformed same-carrier packing receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "same_carrier_packing_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "packing/no-reuse spend needs source carrier, target payments, "
                "assignment map, same-carrier binding, overlap bound, finite "
                "prefix budget, pre-payoff timing, and anti-nested-reuse receipts"
            ),
        })

    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if weak_present and missing:
        violations.append({
            "type": "same_carrier_packing_replaced_by_weak_substitutes",
            "severity": "blocking" if enforce_block else "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "labels, pointwise payments, or finite-budget language do not "
                "substitute for same-carrier assignment and overlap receipts"
            ),
        })

    if _present(receipt.get("known_nested_reuse_confuser")):
        violations.append({
            "type": "same_carrier_packing_nested_reuse_confuser_declared",
            "severity": "blocking" if enforce_block else "advisory",
            "confuser": receipt.get("known_nested_reuse_confuser"),
            "reason": "caller declared a nested-reuse or carrier-mismatch confuser",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not any(
        v["type"] == "same_carrier_packing_nested_reuse_confuser_declared"
        for v in violations
    )
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "complete same-carrier packing/no-reuse receipt"
            if complete else
            f"incomplete same-carrier packing/no-reuse receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_same_carrier_packing_gate({
        "source_carrier": "metric tents",
        "target_payment_family": "fresh-frequency atoms",
        "packing_label": "Besicovitch",
    })
    assert weak["complete"] is False
    assert any(v["type"] == "same_carrier_packing_receipt_incomplete" for v in weak["violations"])

    strong = run_same_carrier_packing_gate({
        "source_carrier": "metric tents",
        "target_payment_family": "fresh-frequency atoms",
        "assignment_or_injection_map": "selected tent n maps to atom j(n)",
        "assignment_total_on_prefix": "all n<K covered",
        "same_carrier_binding": "same pressure/Duhamel carrier",
        "overlap_or_multiplicity_bound": "multiplicity <= M",
        "finite_prefix_budget": "M * atom_budget <= total_budget",
        "pre_payoff_timing": "map fixed before payoff",
        "no_nested_reuse": "nested chains charged once",
        "no_rebilling_same_atom": "atom j cannot be rebilled beyond M",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


if __name__ == "__main__":
    _self_test()
