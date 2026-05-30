"""G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE.

Validate the positive finite arithmetic surface that turns a strict
support-index order into no-hole contiguity: every prefix slot must be pinned
between the same endpoint law, `baseIndex + k <= supportIndex k` and
`supportIndex k <= baseIndex + k`.  This rejects the Level475 skipped-slot
witness class, where strict order/cardinality hold but the upper endpoint
bound fails.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-ENDPOINT-TIGHT-NO-HOLE"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_length",
    "prefix_domain",
    "base_index",
    "base_anchor_at_zero",
    "endpoint_lower_bound_on_prefix",
    "endpoint_upper_bound_on_prefix",
    "pointwise_eq_base_plus_k_derived_from_bounds",
    "strict_order_on_prefix_holds_or_derived",
    "adjacent_endpoint_eq_left",
    "adjacent_endpoint_eq_right",
    "nat_no_between_successive_endpoints",
    "no_hole_constructor",
    "unit_gap_constructor_or_downstream_unit_gap_check",
    "level475_skipped_slot_rejected_by_upper_bound",
    "not_level475_strict_cardinality_only",
    "not_level464_no_hole_assumed",
    "not_unit_gap_assumed",
    "not_affine_stride_one_assumed_without_bounds",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_reindexing",
    "no_post_payoff_endpoint_tuning",
    "no_strict_order_label_as_endpoint_tight",
    "no_cardinality_label_as_endpoint_tight",
    "no_packing_label_as_endpoint_tight",
    "no_selected_event_as_endpoint_tight",
    "nearest_confuser_unit_gap_distinction",
    "nearest_confuser_affine_stride_one_distinction",
    "nearest_confuser_level475_distinction",
    "nearest_confuser_level464_distinction",
)

WEAK_SUBSTITUTES = (
    "strict_order_label",
    "injectivity_label",
    "cardinality_label",
    "finite_image_label",
    "packing_label",
    "carleson_label",
    "selected_event_witness",
    "no_hole_label",
    "unit_gap_label",
    "affine_stride_one_label",
    "endpoint_label_without_bounds",
    "post_payoff_patch",
    "target_defined_endpoint",
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


def run_support_index_endpoint_tight_no_hole_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_endpoint_tight_no_hole_receipt_malformed",
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
            "type": "support_index_endpoint_tight_no_hole_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "endpoint-tight no-hole needs the support-index map, base, "
                "strict order, both pointwise lower and upper base+k bounds, "
                "derivations of equality/strict successor/no-between, and "
                "anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_endpoint_tight_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "strict order, injectivity, cardinality, packing, selected "
                "events, unit-gap labels, or affine labels do not substitute "
                "for pointwise endpoint upper and lower bounds"
            ),
        })
    if _present(receipt.get("skipped_slot_witness_present")):
        violations.append({
            "type": "skipped_slot_witness_still_present",
            "reason": (
                "endpoint tightness must reject the skipped-slot witness, not "
                "coexist with it"
            ),
        })
    if _present(receipt.get("post_payoff_endpoint_fit")):
        violations.append({
            "type": "post_payoff_endpoint_fit",
            "reason": "endpoint tightness must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_endpoint_fit")):
        violations.append({
            "type": "target_defined_endpoint_fit",
            "reason": "endpoint tightness cannot be fitted from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_endpoint_tight_no_hole"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index endpoint-tight no-hole receipt"
            if not violations else
            "support-index endpoint-tight no-hole rejected with "
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
    weak = run_support_index_endpoint_tight_no_hole_gate({
        "support_index_map": "supportIndex",
        "strict_order_label": "strict order on prefix",
        "cardinality_label": "image card equals supportLength",
        "skipped_slot_witness_present": "Level475 [0,2] still has slot 1",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_endpoint_tight_no_hole_gate({
        "label": "endpoint_tight_base_plus_index",
        "support_index_map": "supportIndex",
        "prefix_domain": "k < supportLength",
        "base_index": "baseIndex",
        "support_length": "supportLength",
        "base_anchor_at_zero": "supportIndex 0 = baseIndex",
        "endpoint_lower_bound_on_prefix": "baseIndex + k <= supportIndex k",
        "endpoint_upper_bound_on_prefix": "supportIndex k <= baseIndex + k",
        "pointwise_eq_base_plus_k_derived_from_bounds": "le_antisymm gives equality",
        "strict_order_on_prefix_holds_or_derived": "strict order on prefix",
        "adjacent_endpoint_eq_left": "supportIndex k = baseIndex + k",
        "adjacent_endpoint_eq_right": "supportIndex (k+1) = baseIndex + (k+1)",
        "nat_no_between_successive_endpoints": "no Nat lies between m and Nat.succ m",
        "no_hole_constructor": "construct NoHoleContiguousSupportIndexSource",
        "unit_gap_constructor_or_downstream_unit_gap_check": "downstream unit gap follows",
        "level475_skipped_slot_rejected_by_upper_bound": (
            "[0,2] fails supportIndex 1 <= base+1"
        ),
        "not_level475_strict_cardinality_only": "requires endpoint upper/lower bounds",
        "not_level464_no_hole_assumed": "no-hole is derived",
        "not_unit_gap_assumed": "unit gap is derived downstream",
        "not_affine_stride_one_assumed_without_bounds": "affine equality comes from bounds",
        "fixed_before_payoff": "endpoint bounds fixed before payoff",
        "not_target_defined": "not fitted from target deficit",
        "no_post_payoff_reindexing": "no post-payoff reindexing",
        "no_post_payoff_endpoint_tuning": "no post-payoff endpoint tuning",
        "no_strict_order_label_as_endpoint_tight": "Level475 refutes strict-only",
        "no_cardinality_label_as_endpoint_tight": "Level475 refutes card-only",
        "no_packing_label_as_endpoint_tight": "packing is not endpoint tightness",
        "no_selected_event_as_endpoint_tight": "selected event is not endpoint tightness",
        "nearest_confuser_unit_gap_distinction": "endpoint bounds derive unit gap",
        "nearest_confuser_affine_stride_one_distinction": "bounds derive affine stride one",
        "nearest_confuser_level475_distinction": "Level475 fails upper endpoint bound",
        "nearest_confuser_level464_distinction": "Level464 no-hole is derived, not assumed",
    })
    assert strong["passed"] is True
    assert strong["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index endpoint-tight no-hole receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_endpoint_tight_no_hole_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_endpoint_tight_no_hole_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
