"""G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR.

Validates the source that pays least-selector minimality: a fixed first-hit
bounded search over prefix supportIndex candidates.  This blocks laundering a
least/minimal label, Level465/467/469 existence, or a packing/selection label
as a first-hit success certificate.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-FIRST-HIT-INTERVAL-PREIMAGE-SELECTOR"

REQUIRED_FIELDS = (
    "support_index_map",
    "prefix_domain",
    "same_support_index_same_prefix",
    "owner_or_carrier_binding",
    "base_at_zero",
    "strict_order_on_prefix",
    "first_hit_function",
    "bounded_search_domain",
    "candidate_predicate_exact",
    "bounded_search_provenance",
    "first_hit_success_certificate",
    "success_not_from_interval_image_totality",
    "success_not_from_level467_selector",
    "success_not_from_level469_least_selector",
    "no_classical_choice_or_nat_find_from_existential",
    "first_hit_prefix_membership",
    "first_hit_maps_to_requested_nat",
    "no_prior_candidate_law",
    "least_selector_constructor",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_search",
    "no_first_hit_label_only",
    "no_bounded_search_label_only",
    "no_packing_label_as_first_hit_selector",
    "no_selected_event_as_first_hit_selector",
)

WEAK_SUBSTITUTES = (
    "first_hit_label",
    "first_hit_without_success_certificate",
    "least_label",
    "minimal_label",
    "first_hit_from_least_selector",
    "nat_find_from_interval_image",
    "classical_choice_from_interval_image",
    "classical_choice_from_level467_selector",
    "classical_choice_from_level469_least_selector",
    "well_founded_min_from_existential",
    "bounded_search_label_only",
    "existence_label",
    "interval_image_label",
    "interval_image_totality_label",
    "selector_label",
    "level467_selector_label",
    "level469_least_selector_label",
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


def run_support_index_first_hit_interval_preimage_selector_gate(
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
                "type": "support_index_first_hit_interval_preimage_selector_receipt_malformed",
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
            "type": "support_index_first_hit_interval_preimage_selector_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "first-hit interval-preimage selector evidence needs the same "
                "supportIndex/prefix, bounded search domain, exact candidate "
                "predicate, independent success certificate, membership, image "
                "equality, no-prior-candidate law, constructor, timing, and "
                "anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_first_hit_interval_preimage_selector_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "first-hit/least/minimal labels, Nat.find/Classical.choose from "
                "interval-image, Level467, or Level469 existence, packing, "
                "cardinality, and selected events do not substitute for a "
                "fixed first-hit success certificate"
            ),
        })
    if _present(receipt.get("post_payoff_first_hit_search")):
        violations.append({
            "type": "post_payoff_first_hit_search",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "first-hit bounded search must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_first_hit_selector")):
        violations.append({
            "type": "target_defined_first_hit_selector",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "first-hit selector cannot be defined from the target deficit",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_first_hit_interval_preimage_selector"),
        "passed": not blocking if enforce_block else True,
        "complete": not missing,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index first-hit interval-preimage selector receipt"
            if not violations else
            "support-index first-hit interval-preimage selector rejected with "
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
    weak = run_support_index_first_hit_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "first_hit_label": "first hit",
        "bounded_search_label_only": "bounded search",
        "classical_choice_from_level469_least_selector": "choose least source",
        "packing_label": "owner preimage packing prefix",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False

    blocked = run_support_index_first_hit_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "first_hit_label": "first hit",
    }, enforce_block=True)
    assert blocked["passed"] is False

    exact_false = run_support_index_first_hit_interval_preimage_selector_gate({
        "support_index_map": "missing because not yet formalized",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "prefix_domain"

    strong = run_support_index_first_hit_interval_preimage_selector_gate({
        "support_index_map": "supportIndex",
        "prefix_domain": "i < supportLength",
        "same_support_index_same_prefix": "same supportIndex and prefix as strict source",
        "owner_or_carrier_binding": "same owner binds first hit and supportIndex",
        "base_at_zero": "supportIndex 0 = baseIndex for nonempty prefix",
        "strict_order_on_prefix": "i < j implies supportIndex i < supportIndex j",
        "first_hit_function": "firstHit : Nat -> Nat -> Nat",
        "bounded_search_domain": "Finset.range supportLength",
        "candidate_predicate_exact": "candidate j iff j<prefix and supportIndex j=n",
        "bounded_search_provenance": "bounded scan/source certificate before payoff",
        "first_hit_success_certificate": "first hit succeeds for every skipped slot",
        "success_not_from_interval_image_totality": "not Level465 existential",
        "success_not_from_level467_selector": "not Level467 selector field",
        "success_not_from_level469_least_selector": "not Level469 least selector",
        "no_classical_choice_or_nat_find_from_existential": "no choice over old existential",
        "first_hit_prefix_membership": "first hit index is inside prefix",
        "first_hit_maps_to_requested_nat": "supportIndex firstHit = requested n",
        "no_prior_candidate_law": "no candidate j has j < firstHit",
        "least_selector_constructor": "construct Level469 least selector source",
        "fixed_before_payoff": "first hit fixed before payoff",
        "not_target_defined": "not target-deficit defined",
        "no_post_payoff_search": "no post-payoff bounded search",
        "no_first_hit_label_only": "first-hit label alone is not a selector",
        "no_bounded_search_label_only": "bounded-search name needs success proof",
        "no_packing_label_as_first_hit_selector": "packing is not first-hit law",
        "no_selected_event_as_first_hit_selector": "selected event is not first hit",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index first-hit interval-preimage selector receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_first_hit_interval_preimage_selector_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_first_hit_interval_preimage_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
