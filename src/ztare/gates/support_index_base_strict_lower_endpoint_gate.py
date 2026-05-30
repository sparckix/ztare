"""G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND.

Validate the finite arithmetic source that pays the lower half of endpoint
tightness: a fixed base anchor and strict prefix order force
`baseIndex + k <= supportIndex k` for every prefix slot.  This gate keeps the
upper endpoint/range-capacity bound separate; it rejects receipts that smuggle
in no-hole, unit-gap, affine stride-one, or full endpoint-tight conclusions.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-BASE-ANCHORED-STRICT-LOWER-BOUND"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_length",
    "prefix_domain",
    "base_index",
    "base_anchor_at_zero",
    "strict_order_on_prefix",
    "same_owner_base_and_support_index",
    "nonempty_zero_domain_guard",
    "predecessor_prefix_closure",
    "nat_strict_step_implies_successor_le",
    "lower_bound_induction_base",
    "lower_bound_induction_step",
    "derived_endpoint_lower_bound_on_prefix",
    "upper_endpoint_bound_live_debt",
    "level475_skipped_slot_still_admitted",
    "not_no_hole_constructor",
    "not_endpoint_tight_constructor",
    "not_unit_gap_assumed",
    "not_affine_stride_one_assumed",
    "not_cardinality_label_as_lower_bound",
    "not_packing_label_as_lower_bound",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_base_anchor",
    "no_post_payoff_reindexing",
    "nearest_confuser_endpoint_tight_distinction",
    "nearest_confuser_level475_distinction",
    "nearest_confuser_fixed_step_distinction",
    "nearest_confuser_no_hole_distinction",
    "nearest_confuser_upper_bound_distinction",
)

WEAK_SUBSTITUTES = (
    "lower_bound_label_without_base_anchor",
    "strict_order_only_as_lower_bound",
    "injectivity_label",
    "cardinality_as_lower_bound",
    "finite_image_label",
    "packing_as_lower_bound",
    "carleson_label",
    "selected_event_witness",
    "unit_gap_as_lower_bound",
    "affine_stride_one_as_lower_bound",
    "no_hole_claim",
    "endpoint_tight_claim",
    "post_payoff_base_fit",
    "post_payoff_reindexing",
    "target_defined_anchor",
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


def run_support_index_base_strict_lower_endpoint_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_base_strict_lower_endpoint_receipt_malformed",
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
            "type": "support_index_base_strict_lower_endpoint_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "base-anchored strict lower bound needs a same-owner "
                "supportIndex/base anchor, strict prefix order, zero-domain "
                "and predecessor-prefix guards, the Nat induction step, and "
                "explicit admission that upper endpoint capacity remains owed"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_lower_endpoint_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "labels for cardinality, packing, no-hole, unit gap, affine "
                "stride one, or full endpoint tightness do not "
                "substitute for the base-anchored strict-order induction"
            ),
        })
    if _present(receipt.get("upper_endpoint_bound_assumed")):
        violations.append({
            "type": "upper_endpoint_bound_assumed",
            "reason": "Level477 only pays the lower bound; upper capacity stays open",
        })
    if _present(receipt.get("endpoint_tightness_claimed")):
        violations.append({
            "type": "endpoint_tightness_claimed",
            "reason": "lower endpoint control alone is not Level476 endpoint tightness",
        })
    if _present(receipt.get("post_payoff_base_fit")):
        violations.append({
            "type": "post_payoff_base_fit",
            "reason": "the base anchor must be fixed before payoff",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_base_anchored_strict_lower_bound"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index base-anchored strict lower-bound receipt"
            if not violations else
            "support-index base-anchored strict lower bound rejected with "
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
    weak = run_support_index_base_strict_lower_endpoint_gate({
        "support_index_map": "supportIndex",
        "strict_order_only_as_lower_bound": "strict order on prefix",
        "endpoint_tight_claim": "endpoint tight",
        "upper_endpoint_bound_assumed": "supportIndex k <= base+k",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_base_strict_lower_endpoint_gate({
        "label": "base_strict_lower_endpoint",
        "support_index_map": "supportIndex",
        "support_length": "supportLength",
        "prefix_domain": "k < supportLength",
        "base_index": "baseIndex",
        "base_anchor_at_zero": "supportIndex 0 = baseIndex",
        "strict_order_on_prefix": "i < j implies supportIndex i < supportIndex j",
        "same_owner_base_and_support_index": "same source fixes base and supportIndex",
        "nonempty_zero_domain_guard": "0 < supportLength for the zero anchor",
        "predecessor_prefix_closure": "k+1 < supportLength implies k < supportLength",
        "nat_strict_step_implies_successor_le": "Nat.succ_le_of_lt transfers the step",
        "lower_bound_induction_base": "k=0 follows by supportIndex_zero_eq_base",
        "lower_bound_induction_step": (
            "IH plus supportIndex k < supportIndex(k+1)"
        ),
        "derived_endpoint_lower_bound_on_prefix": "baseIndex + k <= supportIndex k",
        "upper_endpoint_bound_live_debt": "supportIndex k <= baseIndex+k remains open",
        "level475_skipped_slot_still_admitted": "[0,2] still satisfies lower bound",
        "not_no_hole_constructor": "no-hole not constructed",
        "not_endpoint_tight_constructor": "endpoint tightness not constructed",
        "not_unit_gap_assumed": "unit gap not assumed",
        "not_affine_stride_one_assumed": "affine stride one not assumed",
        "not_cardinality_label_as_lower_bound": "cardinality label rejected",
        "not_packing_label_as_lower_bound": "packing label rejected",
        "fixed_before_payoff": "base anchor and order fixed before payoff",
        "not_target_defined": "not fitted from target deficit",
        "no_post_payoff_base_anchor": "no post-payoff base anchor",
        "no_post_payoff_reindexing": "no post-payoff reindexing",
        "nearest_confuser_endpoint_tight_distinction": "only lower half of Level476",
        "nearest_confuser_level475_distinction": "Level475 survives lower-bound-only",
        "nearest_confuser_fixed_step_distinction": "does not assume fixed step",
        "nearest_confuser_no_hole_distinction": "does not construct no-hole",
        "nearest_confuser_upper_bound_distinction": "upper bound remains live debt",
    })
    assert strong["passed"] is True
    assert strong["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description=(
            "Validate a support-index base-anchored strict lower-bound receipt."
        )
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_base_strict_lower_endpoint_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_base_strict_lower_endpoint_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
