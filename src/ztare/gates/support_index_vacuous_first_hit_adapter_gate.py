"""G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER.

Validates a narrow adapter: no-hole contiguous supportIndex geometry makes the
first-hit skipped-slot domain empty.  This prevents recording vacuity as an
independent bounded-search certificate.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-VACUOUS-FIRST-HIT-ADAPTER"

REQUIRED_FIELDS = (
    "support_index_map",
    "prefix_domain",
    "source_no_hole_receipt",
    "skipped_slot_domain_empty_by_no_hole",
    "no_hole_source_field",
    "dummy_first_hit_function",
    "first_hit_membership_from_false",
    "first_hit_image_equality_from_false",
    "no_prior_candidate_from_false",
    "strict_source_constructor_chain",
    "not_independent_bounded_search_certificate",
    "not_new_source_mechanism",
    "next_lever_returns_to_no_hole_geometry",
    "no_level465_interval_image_import",
    "no_level467_selector_import",
    "no_level469_least_selector_import",
    "no_classical_choice_or_nat_find",
    "fixed_before_payoff",
    "not_target_defined",
    "no_packing_label_as_vacuity",
    "no_selected_event_as_vacuity",
)

WEAK_SUBSTITUTES = (
    "first_hit_label",
    "bounded_search_label_only",
    "hidden_bounded_search",
    "least_label",
    "minimal_label",
    "interval_image_totality_label",
    "level467_selector_label",
    "level469_least_selector_label",
    "nat_find_from_interval_image",
    "classical_choice_from_level467_selector",
    "classical_choice_from_level469_least_selector",
    "packing_label",
    "carleson_label",
    "selected_event_witness",
    "counts_as_new_source",
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


def run_support_index_vacuous_first_hit_adapter_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_vacuous_first_hit_adapter_receipt_malformed",
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
            "type": "support_index_vacuous_first_hit_adapter_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "vacuous first-hit adapter evidence needs a no-hole source, "
                "explicit skipped-slot empty-domain certificate, dummy firstHit, "
                "False-elim membership/image/no-prior laws, strict-source "
                "constructor chain, and an explicit non-new-source classification"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_vacuous_first_hit_adapter_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "first-hit/bounded-search/least labels, old interval-image or "
                "selector existence, choice/find, packing, and selected events "
                "do not substitute for a no-hole empty-domain certificate"
            ),
        })
    if _present(receipt.get("post_payoff_vacuity_selection")):
        violations.append({
            "type": "post_payoff_vacuity_selection",
            "reason": "the no-skipped-slot source and dummy firstHit must be fixed before payoff",
        })
    if _present(receipt.get("target_defined_vacuity_adapter")):
        violations.append({
            "type": "target_defined_vacuity_adapter",
            "reason": "vacuity cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_vacuous_first_hit_adapter"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index vacuous first-hit adapter receipt"
            if not violations else
            "support-index vacuous first-hit adapter rejected with "
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
    weak = run_support_index_vacuous_first_hit_adapter_gate({
        "support_index_map": "supportIndex",
        "first_hit_label": "first hit exists",
        "bounded_search_label_only": "bounded search",
        "counts_as_new_source": "new first-hit source",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong = run_support_index_vacuous_first_hit_adapter_gate({
        "support_index_map": "supportIndex",
        "prefix_domain": "k + 1 < supportLength",
        "source_no_hole_receipt": "G-SUPPORT-INDEX-NO-HOLE-UNIT-GAP passed",
        "skipped_slot_domain_empty_by_no_hole": (
            "no n with supportIndex k < n < supportIndex (k+1)"
        ),
        "no_hole_source_field": "no_supportIndex_between_adjacent_on_prefix",
        "dummy_first_hit_function": "firstHit k n := 0",
        "first_hit_membership_from_false": "False.elim no-hole contradiction",
        "first_hit_image_equality_from_false": "False.elim no-hole contradiction",
        "no_prior_candidate_from_false": "False.elim no-hole contradiction",
        "strict_source_constructor_chain": "NoHole -> Unit -> Adjacent -> Fixed -> Affine -> Strict",
        "not_independent_bounded_search_certificate": "adapter is empty-domain vacuity",
        "not_new_source_mechanism": "derived adapter only",
        "next_lever_returns_to_no_hole_geometry": "derive no-hole from boundary geometry",
        "no_level465_interval_image_import": "does not import Level465",
        "no_level467_selector_import": "does not import Level467",
        "no_level469_least_selector_import": "does not import Level469",
        "no_classical_choice_or_nat_find": "no choice/find",
        "fixed_before_payoff": "fixed before payoff",
        "not_target_defined": "not target-defined",
        "no_packing_label_as_vacuity": "packing is not empty-domain proof",
        "no_selected_event_as_vacuity": "selected event is not empty-domain proof",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index vacuous first-hit adapter receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_vacuous_first_hit_adapter_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_vacuous_first_hit_adapter_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
