"""G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR - explicit interval preimage source.

Validates the stronger support-index surface that pays interval-image totality
by naming a fixed prefix selector for every Nat value strictly between adjacent
support-index values.  This blocks replacing the selector with existence,
interval-image, no-hole, strict-order, cardinality, packing, or selected-event
labels.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-INTERVAL-PREIMAGE-SELECTOR"

REQUIRED_FIELDS = (
    "support_index_map",
    "prefix_domain",
    "owner_or_carrier_binding",
    "base_at_zero",
    "strict_order_on_prefix",
    "interval_preimage_selector",
    "selector_domain_totality",
    "selector_prefix_membership",
    "selector_maps_to_requested_nat",
    "selector_not_skolemized_from_interval_image_totality",
    "interval_image_constructor",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_selector_filling",
    "no_exists_label_only_as_selector",
    "no_strict_order_only_as_selector",
    "no_cardinality_label_as_selector",
    "no_packing_label_as_selector",
    "no_selected_event_as_selector",
)

WEAK_SUBSTITUTES = (
    "existence_label",
    "interval_image_label",
    "interval_image_totality_label",
    "classical_choice_from_interval_image",
    "no_hole_label",
    "unit_gap_label",
    "strict_order_label",
    "injectivity_label",
    "cardinality_label",
    "finite_image_label",
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
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_support_index_interval_preimage_selector_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "support_index_interval_preimage_selector_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
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
            "type": "support_index_interval_preimage_selector_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "interval-preimage selector evidence needs a support-index map, "
                "prefix domain, same-owner binding, base at zero, strict prefix "
                "order, an explicit selector for skipped Nat values, selector "
                "domain totality, prefix membership, maps-to-requested-Nat law, "
                "non-Skolemization from interval-image totality, constructor, "
                "timing, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_interval_preimage_selector_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "existence/interval-image/no-hole/unit-gap/order/injectivity/"
                "cardinality/finite-image/packing/selected-event labels do not "
                "substitute for an explicit selector with membership and image laws"
            ),
        })
    if _present(receipt.get("post_payoff_selector_filling")):
        violations.append({
            "type": "post_payoff_selector_filling",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "interval preimage selectors must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_selector")):
        violations.append({
            "type": "target_defined_selector",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "the selector cannot be defined from the target deficit",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_interval_preimage_selector"),
        "passed": not blocking if enforce_block else True,
        "complete": not missing,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index interval-preimage selector receipt"
            if not violations else
            "support-index interval-preimage selector rejected with "
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
    weak = run_support_index_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "existence_label": "there exists a preimage",
        "strict_order_label": "i < j -> supportIndex i < supportIndex j",
        "packing_label": "owner preimage packing prefix",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False

    blocked = run_support_index_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "existence_label": "there exists a preimage",
    }, enforce_block=True)
    assert blocked["passed"] is False

    exact_false = run_support_index_interval_preimage_selector_gate({
        "support_index_map": "missing because not yet formalized",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "prefix_domain"

    strong = run_support_index_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "prefix_domain": "i < supportLength",
        "owner_or_carrier_binding": "same owner binds the selector and supportIndex",
        "base_at_zero": "supportIndex 0 = baseIndex for nonempty prefix",
        "strict_order_on_prefix": "i < j implies supportIndex i < supportIndex j",
        "interval_preimage_selector": (
            "for k,n with supportIndex k < n < supportIndex (k+1), choose i"
        ),
        "selector_domain_totality": "selector is defined for every adjacent skipped Nat",
        "selector_prefix_membership": "chosen i satisfies i < supportLength",
        "selector_maps_to_requested_nat": "supportIndex i = n",
        "selector_not_skolemized_from_interval_image_totality": (
            "selector is an upstream source, not Classical.choose from Level465"
        ),
        "interval_image_constructor": "construct IntervalImageSupportIndexSource",
        "fixed_before_payoff": "selector fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_selector_filling": "no post-payoff selector insertion",
        "no_exists_label_only_as_selector": "existence label lacks a selector law",
        "no_strict_order_only_as_selector": "strict order alone permits holes",
        "no_cardinality_label_as_selector": "cardinality alone permits holes",
        "no_packing_label_as_selector": "packing prefix is not a selector law",
        "no_selected_event_as_selector": "selected event is not a selector",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index interval-preimage selector receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_interval_preimage_selector_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_interval_preimage_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
