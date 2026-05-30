"""G-SUPPORT-INDEX-FIXED-STEP - local recurrence source for affine support order.

Validates that a support-index stream has a fixed base value and a uniform
positive successor step on the finite prefix. This is the local arithmetic
source that can imply a global affine formula; it blocks reusing cardinality,
packing, selected-event, or already-affine labels as the recurrence evidence.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-FIXED-STEP"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_domain",
    "base_at_zero",
    "step_stride",
    "positive_stride",
    "successor_step_law",
    "induction_derivation",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_reindexing",
    "no_cardinality_label_as_step",
    "no_packing_label_as_step",
    "no_selected_event_as_step",
)

WEAK_SUBSTITUTES = (
    "affine_formula_label",
    "strict_order_label",
    "injectivity_label",
    "cardinality_label",
    "packing_label",
    "carleson_label",
    "selected_event_witness",
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
            "no",
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_support_index_fixed_step_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_fixed_step_receipt_malformed",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
        }

    violations: list[dict[str, Any]] = []
    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "support_index_fixed_step_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "fixed-step support order needs a map, prefix domain, base at "
                "zero, positive step stride, successor-step law, induction "
                "derivation, timing, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_fixed_step_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "affine/order/injectivity/cardinality/packing/selected-event "
                "labels do not substitute for a local fixed-step recurrence"
            ),
        })
    if _present(receipt.get("post_payoff_step_law")):
        violations.append({
            "type": "post_payoff_step_law",
            "reason": "fixed-step support-index law must be fixed before payoff",
        })
    if _present(receipt.get("target_deficit_step")):
        violations.append({
            "type": "target_deficit_step",
            "reason": "step stride cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_fixed_step"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index fixed-step receipt"
            if not violations else
            f"support-index fixed-step rejected with {len(violations)} violation(s)"
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
    weak = run_support_index_fixed_step_gate({
        "support_index_map": "supportIndex",
        "affine_formula_label": "supportIndex k = base + stride*k",
        "cardinality_label": "same length",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_fixed_step_gate({
        "support_index_map": "supportIndex",
        "support_domain": "k + 1 < supportLength",
        "base_at_zero": "supportIndex 0 = baseIndex",
        "step_stride": "stride",
        "positive_stride": "0 < stride",
        "successor_step_law": "supportIndex (k + 1) = supportIndex k + stride",
        "induction_derivation": (
            "base case at zero plus successor step proves "
            "supportIndex k = baseIndex + stride*k"
        ),
        "fixed_before_payoff": "base and step fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_reindexing": "prefix not pruned after payoff",
        "no_cardinality_label_as_step": "cardinality follows downstream",
        "no_packing_label_as_step": "packing is not a successor-step law",
        "no_selected_event_as_step": "selected event is not a step recurrence",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index fixed-step receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_fixed_step_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_fixed_step_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
