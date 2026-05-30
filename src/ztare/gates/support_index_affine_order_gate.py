"""G-SUPPORT-INDEX-AFFINE-ORDER - affine source for strict support order.

Validates that a support-index stream is ordered by an explicit affine formula
with positive stride on a fixed finite domain. This prevents reusing a bare
order, packing, or cardinality label as the arithmetic source of strict order.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-AFFINE-ORDER"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_domain",
    "affine_base",
    "affine_stride",
    "positive_stride",
    "affine_formula_on_domain",
    "strict_order_derivation",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_reindexing",
    "no_cardinality_label_as_order",
    "no_packing_label_as_order",
)

WEAK_SUBSTITUTES = (
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


def run_support_index_affine_order_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_affine_order_receipt_malformed",
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
            "type": "support_index_affine_order_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "affine support order needs a fixed domain, base, positive "
                "stride, formula on the domain, strict-order derivation, "
                "timing, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_affine_order_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "order, injectivity, cardinality, packing, or selected-event "
                "labels do not substitute for a positive-stride affine formula"
            ),
        })
    if _present(receipt.get("post_payoff_affine_formula")):
        violations.append({
            "type": "post_payoff_affine_formula",
            "reason": "affine support-index formula must be fixed before payoff",
        })
    if _present(receipt.get("target_deficit_stride")):
        violations.append({
            "type": "target_deficit_stride",
            "reason": "base/stride cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_affine_order"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index affine-order receipt"
            if not violations else
            f"support-index affine order rejected with {len(violations)} violation(s)"
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
    weak = run_support_index_affine_order_gate({
        "support_index_map": "supportIndex",
        "strict_order_label": "ordered",
        "cardinality_label": "same length",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_affine_order_gate({
        "support_index_map": "supportIndex",
        "support_domain": "k < supportLength",
        "affine_base": "baseIndex",
        "affine_stride": "stride",
        "positive_stride": "0 < stride",
        "affine_formula_on_domain": "supportIndex k = baseIndex + stride * k",
        "strict_order_derivation": (
            "i < j and 0 < stride imply baseIndex + stride*i < "
            "baseIndex + stride*j"
        ),
        "fixed_before_payoff": "base and stride fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_reindexing": "domain not pruned after payoff",
        "no_cardinality_label_as_order": "cardinality follows downstream",
        "no_packing_label_as_order": "packing is not an affine formula",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index affine-order receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_affine_order_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_affine_order_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
