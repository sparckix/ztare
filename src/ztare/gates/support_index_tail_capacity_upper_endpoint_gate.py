"""G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND.

Validate the finite range-capacity source that pays the upper half of endpoint
tightness.  The active receipt is not a bare upper-bound label: strict order
must supply the finite tail-step count up to a fixed final slot, then a final
endpoint capacity bound and Nat cancellation yield `supportIndex k <= baseIndex + k`.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-FINAL-ENDPOINT-CAPACITY-UPPER-BOUND"

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
    "final_endpoint_capacity_bound",
    "nat_tail_capacity_cancellation",
    "derived_endpoint_upper_bound_on_prefix",
    "level477_lower_bound_feed_declared",
    "level476_endpoint_tight_feed_declared",
    "level475_skipped_slot_rejected_by_final_capacity",
    "not_lower_bound_only",
    "not_no_hole_assumed",
    "not_endpoint_tight_assumed",
    "not_unit_gap_assumed",
    "not_affine_stride_one_assumed",
    "not_cardinality_label_as_capacity",
    "not_packing_label_as_capacity",
    "not_carleson_label_as_capacity",
    "not_selected_event_as_capacity",
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


def run_support_index_tail_capacity_upper_endpoint_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_tail_capacity_upper_endpoint_receipt_malformed",
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
            "type": "support_index_tail_capacity_upper_endpoint_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "tail-capacity upper endpoint needs same-prefix supportIndex, "
                "final-slot capacity, strict-order tail-step count, Nat "
                "tail cancellation, Level475 rejection, and downstream "
                "endpoint-tight/no-hole constructors"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_upper_endpoint_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "upper-bound labels, endpoint-tight/no-hole/unit-gap labels, "
                "cardinality, packing, Carleson, or selected events do not "
                "substitute for final-slot capacity plus tail-step count"
            ),
        })
    if _present(receipt.get("skipped_slot_witness_survives")):
        violations.append({
            "type": "skipped_slot_witness_survives",
            "reason": "tail capacity must reject Level475 upward drift",
        })
    if _present(receipt.get("post_payoff_tail_fit")):
        violations.append({
            "type": "post_payoff_tail_fit",
            "reason": "tail capacity must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_capacity_fit")):
        violations.append({
            "type": "target_defined_capacity_fit",
            "reason": "tail capacity cannot be fitted from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_final_endpoint_capacity_upper"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index final-endpoint capacity upper-bound receipt"
            if not violations else
            "support-index final-endpoint capacity upper bound rejected with "
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
    weak = run_support_index_tail_capacity_upper_endpoint_gate({
        "support_index_map": "supportIndex",
        "upper_bound_label_without_final_capacity": "supportIndex k <= base+k",
        "cardinality_as_upper_bound": "image card equals supportLength",
        "skipped_slot_witness_survives": "Level475 [0,2] still allowed",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_tail_capacity_upper_endpoint_gate({
        "label": "tail_capacity_upper_endpoint",
        "support_index_map": "supportIndex",
        "support_length": "supportLength",
        "prefix_domain": "k < supportLength",
        "base_index": "baseIndex",
        "final_slot": "finalSlot",
        "support_length_eq_succ_final_slot": "supportLength = finalSlot + 1",
        "final_slot_inside_prefix": "finalSlot < supportLength",
        "nonempty_prefix_guard": "supportLength = succ finalSlot",
        "base_anchor_at_zero": "supportIndex 0 = baseIndex",
        "strict_order_on_prefix": "strict supportIndex order on prefix",
        "same_owner_base_supportIndex_finalSlot": "same source owns base/support/finalSlot",
        "tail_step_count_from_strict_order": (
            "supportIndex k + (finalSlot-k) <= supportIndex finalSlot"
        ),
        "tail_step_count_domain_closure": "k <= finalSlot from k < supportLength",
        "final_endpoint_capacity_bound": "supportIndex finalSlot <= baseIndex + finalSlot",
        "nat_tail_capacity_cancellation": "Nat.add_le_add_iff_right cancels tail",
        "derived_endpoint_upper_bound_on_prefix": "supportIndex k <= baseIndex + k",
        "level477_lower_bound_feed_declared": "Level477 supplies lower endpoint bound",
        "level476_endpoint_tight_feed_declared": "upper+lower feed Level476",
        "level475_skipped_slot_rejected_by_final_capacity": "[0,2] fails final capacity",
        "not_lower_bound_only": "adds upper capacity beyond Level477",
        "not_no_hole_assumed": "no-hole is downstream",
        "not_endpoint_tight_assumed": "endpoint tightness is constructed",
        "not_unit_gap_assumed": "unit gap is downstream",
        "not_affine_stride_one_assumed": "affine equality follows downstream",
        "not_cardinality_label_as_capacity": "cardinality rejected",
        "not_packing_label_as_capacity": "packing rejected",
        "not_carleson_label_as_capacity": "Carleson rejected",
        "not_selected_event_as_capacity": "selected event rejected",
        "fixed_before_payoff": "tail capacity fixed before payoff",
        "not_target_defined": "not fitted from target deficit",
        "no_post_payoff_final_slot": "no post-payoff final slot",
        "no_post_payoff_capacity_tuning": "no post-payoff capacity tuning",
        "no_post_payoff_reindexing": "no post-payoff reindexing",
        "nearest_confuser_level476_distinction": "does not assume endpoint tight",
        "nearest_confuser_level477_distinction": "adds upper half",
        "nearest_confuser_level475_distinction": "rejects upward drift",
        "nearest_confuser_unit_gap_distinction": "does not assume unit gap",
        "nearest_confuser_no_hole_distinction": "no-hole is downstream",
        "nearest_confuser_cardinality_distinction": "cardinality is not capacity",
    })
    assert strong["passed"] is True
    assert strong["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description=(
            "Validate a support-index final-endpoint capacity upper-bound receipt."
        )
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_tail_capacity_upper_endpoint_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_tail_capacity_upper_endpoint_gate(
        _read_json(args.receipt_json)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
