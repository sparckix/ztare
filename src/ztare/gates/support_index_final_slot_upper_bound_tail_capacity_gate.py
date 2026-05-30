"""G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY.

Validate the smaller positive source beneath the Level478 final-endpoint
capacity receipt: strict prefix order supplies the tail-step count to the
fixed final slot, and a single upper bound at that final slot supplies the
tail-capacity inequality.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-FINAL-SLOT-UPPER-BOUND-TAIL-CAPACITY"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_length",
    "prefix_domain",
    "base_index",
    "final_slot",
    "support_length_eq_succ_final_slot",
    "final_slot_inside_prefix",
    "nonempty_prefix_guard",
    "base_anchor_at_zero",
    "strict_order_on_prefix",
    "same_owner_base_supportIndex_finalSlot",
    "tail_step_count_from_strict_order",
    "tail_step_count_domain_closure",
    "final_slot_upper_bound_tail_capacity",
    "nat_tail_capacity_cancellation",
    "derived_endpoint_upper_bound_on_prefix",
    "level477_lower_bound_feed_declared",
    "level476_endpoint_tight_feed_declared",
    "level475_skipped_slot_rejected_by_final_capacity",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_final_slot",
    "no_post_payoff_capacity_tuning",
    "no_post_payoff_reindexing",
    "nearest_confuser_level476_distinction",
    "nearest_confuser_level477_distinction",
    "nearest_confuser_level475_distinction",
    "nearest_confuser_unit_gap_distinction",
    "nearest_confuser_no_hole_distinction",
    "nearest_confuser_cardinality_distinction",
)

WEAK_SUBSTITUTES = (
    "upper_bound_label_without_final_capacity",
    "final_capacity_without_tail_step_count",
    "strict_order_only_as_upper_bound",
    "lower_bound_only_as_upper_bound",
    "cardinality_as_upper_bound",
    "finite_image_as_range_capacity",
    "packing_as_capacity",
    "carleson_as_capacity",
    "selected_event_as_capacity",
    "unit_gap_as_upper_bound",
    "affine_stride_one_as_upper_bound",
    "no_hole_claim",
    "endpoint_tight_claim",
    "supportLength_minus_one_without_nonempty_guard",
    "finalSlot_chosen_after_payoff",
    "post_payoff_capacity_fit",
    "post_payoff_reindexing",
    "target_defined_final_endpoint",
    "wrong_owner_capacity_bound",
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
        }
        return lowered not in false_exact_matches
    if isinstance(value, bool):
        return value
    return value not in (None, "", [], {})


def run_support_index_final_slot_upper_bound_tail_capacity_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_final_slot_tail_capacity_malformed",
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
            "type": "support_index_final_slot_tail_capacity_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "final-slot tail capacity needs strict-order tail-step count, "
                "domain closure to the fixed final slot, the final-slot upper "
                "bound, Nat cancellation, Level475 rejection, and downstream "
                "endpoint-tight/no-hole feed declarations"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_final_slot_upper_bound_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "strict order, lower bounds, endpoint/no-hole/unit-gap labels, "
                "cardinality, packing, Carleson, or selected events do not "
                "substitute for a fixed final-slot upper bound plus tail-step count"
            ),
        })
    if _present(receipt.get("skipped_slot_witness_survives")):
        violations.append({
            "type": "skipped_slot_witness_survives",
            "reason": "the final-slot upper-bound source must reject Level475/479 upward drift",
        })
    if _present(receipt.get("post_payoff_tail_fit")):
        violations.append({
            "type": "post_payoff_tail_fit",
            "reason": "final-slot capacity must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_capacity_fit")):
        violations.append({
            "type": "target_defined_capacity_fit",
            "reason": "final-slot capacity cannot be fitted from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_final_slot_tail_capacity"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index final-slot upper-bound tail-capacity receipt"
            if not violations else
            "support-index final-slot upper-bound tail capacity rejected with "
            f"{len(violations)} violation(s)"
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
    weak = run_support_index_final_slot_upper_bound_tail_capacity_gate({
        "support_index_map": "supportIndex",
        "strict_order_only_as_upper_bound": "strict supportIndex order",
        "cardinality_as_upper_bound": "image card equals supportLength",
        "skipped_slot_witness_survives": "Level479 [0,2] still allowed",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_final_slot_upper_bound_tail_capacity_gate({
        "label": "final_slot_upper_bound_tail_capacity",
        "support_index_map": "supportIndex",
        "support_length": "supportLength",
        "prefix_domain": "k < supportLength",
        "base_index": "baseIndex",
        "final_slot": "supportLength - 1",
        "support_length_eq_succ_final_slot": "supportLength = finalSlot + 1",
        "final_slot_inside_prefix": "finalSlot < supportLength",
        "nonempty_prefix_guard": "0 < supportLength",
        "base_anchor_at_zero": "supportIndex 0 = baseIndex",
        "strict_order_on_prefix": "strict supportIndex order on prefix",
        "same_owner_base_supportIndex_finalSlot": "same source owns all fields",
        "tail_step_count_from_strict_order": (
            "supportIndex k + (finalSlot-k) <= supportIndex finalSlot"
        ),
        "tail_step_count_domain_closure": "k <= finalSlot from k < supportLength",
        "final_slot_upper_bound_tail_capacity": (
            "supportIndex finalSlot <= baseIndex + finalSlot"
        ),
        "nat_tail_capacity_cancellation": "Nat cancellation gives prefix upper bound",
        "derived_endpoint_upper_bound_on_prefix": "supportIndex k <= baseIndex + k",
        "level477_lower_bound_feed_declared": "Level477 supplies lower endpoint",
        "level476_endpoint_tight_feed_declared": "upper+lower feed Level476",
        "level475_skipped_slot_rejected_by_final_capacity": "[0,2] fails final slot",
        "fixed_before_payoff": "final slot fixed before payoff",
        "not_target_defined": "not fitted from target deficit",
        "no_post_payoff_final_slot": "no post-payoff final slot",
        "no_post_payoff_capacity_tuning": "no post-payoff capacity tuning",
        "no_post_payoff_reindexing": "no post-payoff reindexing",
        "nearest_confuser_level476_distinction": "constructs endpoint tight downstream",
        "nearest_confuser_level477_distinction": "adds upper half beyond lower source",
        "nearest_confuser_level475_distinction": "rejects skipped-slot upward drift",
        "nearest_confuser_unit_gap_distinction": "does not assume unit gap",
        "nearest_confuser_no_hole_distinction": "does not assume no-hole",
        "nearest_confuser_cardinality_distinction": "cardinality is not capacity",
    })
    assert strong["passed"] is True
    assert strong["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description=(
            "Validate a support-index final-slot upper-bound tail-capacity receipt."
        )
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_final_slot_upper_bound_tail_capacity_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_final_slot_upper_bound_tail_capacity_gate(
        _read_json(args.receipt_json)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
