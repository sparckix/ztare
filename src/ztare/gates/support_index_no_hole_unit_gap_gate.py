"""G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP - no-hole source for unit spacing.

Validates the finite-prefix arithmetic surface that turns strict adjacent
support-index order plus an explicit no-intermediate-index law into unit
successor spacing.  This blocks using strict order, image cardinality, packing,
or selected-event labels as substitutes for contiguous Nat slots.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP"

REQUIRED_FIELDS = (
    "support_index_map",
    "adjacent_pair_domain",
    "owner_or_carrier_binding",
    "base_at_zero",
    "strict_successor_order",
    "no_between_adjacent_support_index",
    "nat_successor_derivation",
    "unit_gap_constructor",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_pair_selection",
    "no_strict_order_only_as_no_hole",
    "no_cardinality_label_as_no_hole",
    "no_packing_label_as_no_hole",
    "no_selected_event_as_no_hole",
)

WEAK_SUBSTITUTES = (
    "unit_gap_label",
    "adjacent_gap_label",
    "constant_gap_label",
    "fixed_step_law_label",
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


def run_support_index_no_hole_unit_gap_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_no_hole_unit_gap_receipt_malformed",
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
            "type": "support_index_no_hole_unit_gap_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "no-hole unit-gap support order needs a support-index map, "
                "same-owner adjacent domain, base at zero, strict adjacent "
                "order, an explicit no-index-between law, Nat successor "
                "derivation, unit-gap constructor, timing, and anti-laundering "
                "receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_no_hole_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "unit-gap/adjacent-gap/fixed-step/affine/order/injectivity/"
                "cardinality/packing/selected-event labels do not substitute "
                "for a no-intermediate-index contiguity law"
            ),
        })
    if _present(receipt.get("post_payoff_no_hole_pair_selection")):
        violations.append({
            "type": "post_payoff_no_hole_pair_selection",
            "reason": "no-hole adjacent pairs must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_no_hole_gap")):
        violations.append({
            "type": "target_defined_no_hole_gap",
            "reason": "no-hole unit spacing cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_no_hole_unit_gap"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index no-hole unit-gap receipt"
            if not violations else
            f"support-index no-hole unit-gap rejected with {len(violations)} violation(s)"
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
    weak = run_support_index_no_hole_unit_gap_gate({
        "support_index_map": "supportIndex",
        "strict_order_label": "i < j -> supportIndex i < supportIndex j",
        "cardinality_label": "image card equals supportLength",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_no_hole_unit_gap_gate({
        "support_index_map": "supportIndex",
        "adjacent_pair_domain": "k + 1 < supportLength",
        "owner_or_carrier_binding": "same owner binds adjacent atoms",
        "base_at_zero": "supportIndex 0 = baseIndex for nonempty prefix",
        "strict_successor_order": "supportIndex k < supportIndex (k + 1)",
        "no_between_adjacent_support_index": (
            "no n with supportIndex k < n < supportIndex (k + 1)"
        ),
        "nat_successor_derivation": (
            "Nat.succ_le_of_lt plus no-between forces equality to Nat.succ"
        ),
        "unit_gap_constructor": "construct UnitAdjacentGapSupportIndexSource",
        "fixed_before_payoff": "no-hole law fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_pair_selection": "pairs not selected after payoff",
        "no_strict_order_only_as_no_hole": "strict order alone permits holes",
        "no_cardinality_label_as_no_hole": "cardinality alone permits holes",
        "no_packing_label_as_no_hole": "packing is not contiguity",
        "no_selected_event_as_no_hole": "selected event is not contiguous image",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index no-hole unit-gap receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_no_hole_unit_gap_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_no_hole_unit_gap_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
