"""G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR - canonical selector source.

Validates a stronger support-index selector surface: the skipped-slot preimage
selector must be a fixed least-prefix selector with bounded-search provenance.
This blocks laundering a Level465 existential, Level467 selector, Nat.find, or
packing/selection label as a new canonical selector.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-LEAST-INTERVAL-PREIMAGE-SELECTOR"

REQUIRED_FIELDS = (
    "support_index_map",
    "prefix_domain",
    "same_support_index_same_prefix",
    "owner_or_carrier_binding",
    "base_at_zero",
    "strict_order_on_prefix",
    "least_selector_function",
    "bounded_search_domain",
    "candidate_predicate_exact",
    "bounded_search_provenance",
    "search_success_certificate",
    "search_success_not_from_interval_image_totality",
    "search_success_not_from_level467_selector",
    "no_classical_choice_or_nat_find_from_existential",
    "least_prefix_membership",
    "least_maps_to_requested_nat",
    "least_minimality_law",
    "interval_preimage_selector_constructor",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_search",
    "no_least_label_only",
    "no_minimal_label_only",
    "no_bounded_search_label_only",
    "no_packing_label_as_least_selector",
    "no_selected_event_as_least_selector",
)

WEAK_SUBSTITUTES = (
    "least_label",
    "minimal_label",
    "nat_find_from_interval_image",
    "classical_choice_from_interval_image",
    "classical_choice_from_level467_selector",
    "well_founded_min_from_existential",
    "bounded_search_label_only",
    "first_hit_without_success_certificate",
    "existence_label",
    "interval_image_label",
    "interval_image_totality_label",
    "selector_label",
    "level467_selector_label",
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


def run_support_index_least_interval_preimage_selector_gate(
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
                "type": "support_index_least_interval_preimage_selector_receipt_malformed",
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
            "type": "support_index_least_interval_preimage_selector_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "least interval-preimage selector evidence needs the same "
                "supportIndex/prefix, bounded search domain, exact candidate "
                "predicate, independent success certificate, membership, image "
                "equality, minimality, constructor, timing, and anti-laundering "
                "receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_least_interval_preimage_selector_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "least/minimal labels, Nat.find/Classical.choose from "
                "interval-image or Level467 existence, bounded-search labels, "
                "packing, cardinality, and selected events do not substitute "
                "for a bounded-search least selector certificate"
            ),
        })
    if _present(receipt.get("post_payoff_least_search")):
        violations.append({
            "type": "post_payoff_least_search",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "least-selector bounded search must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_least_selector")):
        violations.append({
            "type": "target_defined_least_selector",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "least selector cannot be defined from the target deficit",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_least_interval_preimage_selector"),
        "passed": not blocking if enforce_block else True,
        "complete": not missing,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index least interval-preimage selector receipt"
            if not violations else
            "support-index least interval-preimage selector rejected with "
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
    weak = run_support_index_least_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "least_label": "least witness",
        "nat_find_from_interval_image": "Nat.find over Level465 totality",
        "packing_label": "owner preimage packing prefix",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False

    blocked = run_support_index_least_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "least_label": "least witness",
    }, enforce_block=True)
    assert blocked["passed"] is False

    exact_false = run_support_index_least_interval_preimage_selector_gate({
        "support_index_map": "missing because not yet formalized",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "prefix_domain"

    strong = run_support_index_least_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "prefix_domain": "i < supportLength",
        "same_support_index_same_prefix": "same supportIndex and prefix as strict source",
        "owner_or_carrier_binding": "same owner binds least selector and supportIndex",
        "base_at_zero": "supportIndex 0 = baseIndex for nonempty prefix",
        "strict_order_on_prefix": "i < j implies supportIndex i < supportIndex j",
        "least_selector_function": "leastIntervalPreimage : Nat -> Nat -> Nat",
        "bounded_search_domain": "Finset.range supportLength",
        "candidate_predicate_exact": "candidate j iff j<prefix and supportIndex j=n",
        "bounded_search_provenance": "bounded scan/source certificate before payoff",
        "search_success_certificate": "success certificate independent of Level465/467",
        "search_success_not_from_interval_image_totality": "not Level465 existential",
        "search_success_not_from_level467_selector": "not Level467 selector field",
        "no_classical_choice_or_nat_find_from_existential": "no choice over old existential",
        "least_prefix_membership": "least index is inside prefix",
        "least_maps_to_requested_nat": "supportIndex least = requested n",
        "least_minimality_law": "least index <= every prefix candidate for n",
        "interval_preimage_selector_constructor": "construct Level467 selector source",
        "fixed_before_payoff": "least selector fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_search": "no post-payoff bounded search",
        "no_least_label_only": "least label alone is not a selector",
        "no_minimal_label_only": "minimal label alone is not a proof",
        "no_bounded_search_label_only": "bounded-search name needs success proof",
        "no_packing_label_as_least_selector": "packing is not least selector law",
        "no_selected_event_as_least_selector": "selected event is not selector",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index least interval-preimage selector receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_least_interval_preimage_selector_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_least_interval_preimage_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
