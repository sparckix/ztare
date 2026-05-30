"""G-SUPPORT-INDEX-LAW — typed finite-support selector law receipt.

General-purpose gate for arguments that spend a selected support index as more
than a label.  It checks for actual membership, restricted-prefix, injectivity,
totality, timing, and transfer laws before a support selector can be consumed
as a finite-support source.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-LAW"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_domain",
    "membership_law",
    "restricted_prefix_law",
    "injectivity_law",
    "totality_law",
    "pointwise_lower_transfer_law",
    "boundary_payment_transfer_law",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_pruning",
)

WEAK_SUBSTITUTES = (
    "support_label",
    "injective_prop_label",
    "totality_prop_label",
    "finite_budget_label",
    "carleson_packing_label",
    "selected_event_witness",
    "size_sum_overfill",
    "same_name",
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
            "no",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_support_index_law_gate(receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_law_receipt_malformed",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "support_index_law_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "support-index consumption needs typed membership, restricted-prefix, "
                "injectivity, totality, timing, and payment-transfer laws"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_law_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "labels, selected witnesses, size sums, or Prop-label receipts "
                "do not substitute for typed support-index laws"
            ),
        })
    if _present(receipt.get("post_payoff_selector")):
        violations.append({
            "type": "post_payoff_selector",
            "reason": "support index must be fixed before payoff",
        })
    if _present(receipt.get("target_deficit_selection")):
        violations.append({
            "type": "target_deficit_selection",
            "reason": "support index cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_law"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "typed support-index law receipt"
            if not violations else
            f"support-index law receipt rejected with {len(violations)} violation(s)"
        ),
    }


def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _self_test() -> None:
    weak = run_support_index_law_gate({
        "support_index_map": "k -> supportIndex k",
        "support_label": "ordered support",
        "injective_prop_label": "injective",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False
    assert any(v["type"] == "support_index_law_receipt_incomplete"
               for v in weak["violations"])

    strong = run_support_index_law_gate({
        "support_index_map": "k -> supportIndex k",
        "support_domain": "k < supportLength",
        "membership_law": "supportIndex k is in paid support",
        "restricted_prefix_law": "supportIndex k < restrictedPrefix",
        "injectivity_law": "supportIndex i = supportIndex j -> i = j",
        "totality_law": "paid support n -> exists k, supportIndex k = n",
        "pointwise_lower_transfer_law": "paid support n -> delta <= payment n",
        "boundary_payment_transfer_law": "paid support n -> payment n <= boundary n",
        "fixed_before_payoff": "selector fixed before payoff",
        "not_target_defined": "not defined from target deficit",
        "no_post_payoff_pruning": "no post-payoff pruning",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate a support-index law receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_law_gate self-test PASS")
        return 0
    result = run_support_index_law_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
