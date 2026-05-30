"""G-SUPPORT-INDEX-UNIT-GAP - unit adjacent source for support order.

Validates that a support-index stream pays the stronger contiguous-slot source:
same-owner adjacent pairs advance by exactly one Nat successor. This source can
construct the adjacent-gap source with ``adjacentGap := fun _ => 1`` and
``stride := 1``. It blocks arbitrary adjacent-gap labels, fixed-step labels,
order, cardinality, packing, and selected-event evidence as substitutes.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-UNIT-GAP"

REQUIRED_FIELDS = (
    "support_index_map",
    "adjacent_pair_domain",
    "owner_or_carrier_binding",
    "base_at_zero",
    "unit_gap_law",
    "unit_gap_positive",
    "support_index_succ_eq_succ",
    "adjacent_gap_constructor",
    "stride_one_derivation",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_pair_selection",
    "no_strict_order_label_as_unit_gap",
    "no_cardinality_label_as_unit_gap",
    "no_packing_label_as_unit_gap",
    "no_selected_event_as_unit_gap",
)

WEAK_SUBSTITUTES = (
    "adjacent_gap_label",
    "constant_gap_label",
    "fixed_step_law_label",
    "successor_step_law",
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


def run_support_index_unit_gap_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_unit_gap_receipt_malformed",
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
            "type": "support_index_unit_gap_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "unit-gap support order needs a support-index map, same-owner "
                "adjacent-pair domain, base at zero, unit gap law, Nat.succ "
                "successor law, construction of adjacentGap := 1 and stride := "
                "1, timing, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_unit_gap_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "adjacent-gap/fixed-step/affine/order/injectivity/cardinality/"
                "packing/selected-event labels do not substitute for unit "
                "same-owner successor spacing"
            ),
        })
    if _present(receipt.get("post_payoff_unit_pair_selection")):
        violations.append({
            "type": "post_payoff_unit_pair_selection",
            "reason": "unit adjacent pairs must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_unit_gap")):
        violations.append({
            "type": "target_defined_unit_gap",
            "reason": "unit gap cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_unit_gap"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index unit-gap receipt"
            if not violations else
            f"support-index unit-gap rejected with {len(violations)} violation(s)"
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
    weak = run_support_index_unit_gap_gate({
        "support_index_map": "supportIndex",
        "adjacent_gap_label": "adjacentGap k = stride",
        "strict_order_label": "i < j -> supportIndex i < supportIndex j",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_unit_gap_gate({
        "support_index_map": "supportIndex",
        "adjacent_pair_domain": "k + 1 < supportLength",
        "owner_or_carrier_binding": "same owner binds adjacent atoms",
        "base_at_zero": "supportIndex 0 = baseIndex for nonempty prefix",
        "unit_gap_law": "adjacent gap equals 1",
        "unit_gap_positive": "0 < 1",
        "support_index_succ_eq_succ": (
            "supportIndex (k + 1) = Nat.succ (supportIndex k)"
        ),
        "adjacent_gap_constructor": "adjacentGap := fun _ => 1",
        "stride_one_derivation": "stride := 1 and Nat.succ_eq_add_one",
        "fixed_before_payoff": "unit pair law fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_pair_selection": "pairs not selected after payoff",
        "no_strict_order_label_as_unit_gap": "strict order allows larger gaps",
        "no_cardinality_label_as_unit_gap": "cardinality does not force contiguity",
        "no_packing_label_as_unit_gap": "packing is not unit spacing",
        "no_selected_event_as_unit_gap": "selected event is not unit adjacency",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index unit-gap receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_unit_gap_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_unit_gap_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
