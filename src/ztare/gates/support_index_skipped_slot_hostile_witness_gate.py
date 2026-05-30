"""G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS.

Validate a finite hostile witness for the no-hole support-index interface.
The receipt demonstrates that strict order, injectivity/cardinality, packing,
or selected-event labels can be visible while a skipped Nat slot remains
between adjacent support-index values.  It is a discriminator, not a boundary
geometry source.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-SKIPPED-SLOT-HOSTILE-WITNESS"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_index_values",
    "support_length",
    "prefix_domain",
    "adjacent_pair_index",
    "adjacent_pair_domain",
    "owner_or_carrier_binding_for_weak_fields",
    "strict_order_on_prefix_holds",
    "injectivity_on_prefix_holds",
    "finite_image_cardinality_eq_support_length_holds",
    "weak_boundary_or_packing_evidence_holds",
    "weak_cardinality_evidence_holds",
    "weak_selected_event_or_size_sum_evidence_holds",
    "skipped_slot_witness",
    "skipped_slot_between_adjacent_values",
    "no_prefix_preimage_for_skipped_slot",
    "no_between_adjacent_support_index_fails",
    "unit_successor_law_fails",
    "interval_image_totality_fails",
    "first_hit_success_certificate_fails",
    "not_empty_domain_vacuity",
    "not_level473_vacuous_adapter",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_slot_deletion",
    "no_post_payoff_slot_insertion",
    "no_support_index_reindexing_after_target",
    "no_strict_order_only_as_no_hole",
    "no_injectivity_only_as_no_hole",
    "no_cardinality_label_as_no_hole",
    "no_packing_label_as_no_hole",
    "no_selected_event_as_no_hole",
    "nearest_confuser_level474_distinction",
    "nearest_confuser_level465_distinction",
)

FORBIDDEN_SHORTCUTS = (
    "no_hole_label",
    "unit_gap_label",
    "interval_image_label",
    "first_hit_label",
    "packing_label_as_no_hole",
    "carleson_label_as_no_hole",
    "cardinality_label_as_no_hole",
    "selected_event_as_no_hole",
    "post_payoff_patch",
    "target_defined_gap",
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


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _as_int_list(value: Any) -> list[int] | None:
    if not isinstance(value, list):
        return None
    out: list[int] = []
    for item in value:
        parsed = _as_int(item)
        if parsed is None:
            return None
        out.append(parsed)
    return out


def _strictly_increasing(values: list[int]) -> bool:
    return all(values[i] < values[i + 1] for i in range(len(values) - 1))


def run_support_index_skipped_slot_hostile_witness_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_skipped_slot_hostile_witness_malformed",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "forbidden_shortcuts_present": [],
        }

    violations: list[dict[str, Any]] = []
    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    values = _as_int_list(receipt.get("support_index_values"))
    support_length = _as_int(receipt.get("support_length"))
    pair_index = _as_int(receipt.get("adjacent_pair_index"))
    skipped_slot = _as_int(receipt.get("skipped_slot_witness"))
    forbidden = [
        field for field in FORBIDDEN_SHORTCUTS if _present(receipt.get(field))
    ]

    if missing:
        violations.append({
            "type": "support_index_skipped_slot_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "hostile witness must record the support-index values, weak "
                "fields that still hold, the skipped slot, and the anti-"
                "laundering distinctions from no-hole, interval-image, and "
                "vacuous first-hit receipts"
            ),
        })
    if values is None:
        violations.append({
            "type": "support_index_values_not_integer_list",
            "reason": "support_index_values must be a JSON list of integers",
        })
    if support_length is None:
        violations.append({
            "type": "support_length_not_integer",
            "reason": "support_length must be an integer",
        })
    if pair_index is None:
        violations.append({
            "type": "adjacent_pair_index_not_integer",
            "reason": "adjacent_pair_index must be an integer",
        })
    if skipped_slot is None:
        violations.append({
            "type": "skipped_slot_witness_not_integer",
            "reason": "skipped_slot_witness must be an integer",
        })
    if values is not None and support_length is not None:
        if len(values) != support_length:
            violations.append({
                "type": "support_index_values_length_mismatch",
                "expected": support_length,
                "actual": len(values),
            })
        if not _strictly_increasing(values):
            violations.append({
                "type": "support_index_values_not_strictly_ordered",
                "reason": "the hostile witness should keep the weak strict-order field true",
            })
        if len(set(values)) != len(values):
            violations.append({
                "type": "support_index_values_not_injective",
                "reason": (
                    "the hostile witness should keep finite image cardinality "
                    "and injectivity true while no-hole fails"
                ),
            })
    if (
        values is not None
        and pair_index is not None
        and skipped_slot is not None
    ):
        if pair_index < 0 or pair_index + 1 >= len(values):
            violations.append({
                "type": "adjacent_pair_out_of_range",
                "adjacent_pair_index": pair_index,
                "support_index_values_len": len(values),
            })
        else:
            left = values[pair_index]
            right = values[pair_index + 1]
            if not (left < skipped_slot < right):
                violations.append({
                    "type": "skipped_slot_not_between_adjacent_values",
                    "left": left,
                    "skipped_slot": skipped_slot,
                    "right": right,
                })
            if skipped_slot in values:
                violations.append({
                    "type": "skipped_slot_has_prefix_preimage",
                    "skipped_slot": skipped_slot,
                    "reason": "the witness must fail interval-image/no-hole by omitting the slot",
                })
            if right == left + 1:
                violations.append({
                    "type": "unit_successor_law_not_failed",
                    "left": left,
                    "right": right,
                })
    if forbidden:
        violations.append({
            "type": "forbidden_no_hole_shortcuts_present",
            "forbidden_shortcuts": forbidden,
            "reason": (
                "the hostile witness may expose weak labels, but it cannot "
                "route those labels as no-hole, interval-image, unit-gap, or "
                "first-hit evidence"
            ),
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_skipped_slot_hostile_witness"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "forbidden_shortcuts_present": forbidden,
        "computed": {
            "support_index_values": values,
            "support_length": support_length,
            "adjacent_pair_index": pair_index,
            "skipped_slot_witness": skipped_slot,
            "strictly_increasing": (
                _strictly_increasing(values) if values is not None else None
            ),
            "image_cardinality": (
                len(set(values)) if values is not None else None
            ),
        },
        "summary": (
            "support-index skipped-slot hostile witness"
            if not violations else
            "support-index skipped-slot hostile witness rejected with "
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
    weak = run_support_index_skipped_slot_hostile_witness_gate({
        "support_index_values": [0, 1],
        "support_length": 2,
        "adjacent_pair_index": 0,
        "skipped_slot_witness": 1,
        "no_hole_label": "no-hole by strict order",
    })
    assert weak["passed"] is False

    strong = run_support_index_skipped_slot_hostile_witness_gate({
        "label": "two_slot_gap",
        "support_index_map": "0 -> 0, 1 -> 2",
        "support_index_values": [0, 2],
        "support_length": 2,
        "prefix_domain": "Finset.range 2",
        "adjacent_pair_index": 0,
        "adjacent_pair_domain": "0 + 1 < 2",
        "owner_or_carrier_binding_for_weak_fields": "same finite witness",
        "strict_order_on_prefix_holds": "0 < 2",
        "injectivity_on_prefix_holds": "two distinct prefix slots map distinctly",
        "finite_image_cardinality_eq_support_length_holds": "image {0,2} has card 2",
        "weak_boundary_or_packing_evidence_holds": "packing label can be visible",
        "weak_cardinality_evidence_holds": "cardinality label holds",
        "weak_selected_event_or_size_sum_evidence_holds": "selected-event label visible",
        "skipped_slot_witness": 1,
        "skipped_slot_between_adjacent_values": "0 < 1 < 2",
        "no_prefix_preimage_for_skipped_slot": "1 is not in [0,2]",
        "no_between_adjacent_support_index_fails": "n=1 witnesses failure",
        "unit_successor_law_fails": "2 != 0 + 1",
        "interval_image_totality_fails": "slot 1 has no prefix preimage",
        "first_hit_success_certificate_fails": "no candidate exists for slot 1",
        "not_empty_domain_vacuity": "skipped domain contains slot 1",
        "not_level473_vacuous_adapter": "opposite of empty-domain adapter",
        "fixed_before_payoff": "finite map fixed before payoff",
        "not_target_defined": "map is literal two-slot witness",
        "no_post_payoff_slot_deletion": "no deletion",
        "no_post_payoff_slot_insertion": "no insertion",
        "no_support_index_reindexing_after_target": "no reindexing",
        "no_strict_order_only_as_no_hole": "strict order coexists with hole",
        "no_injectivity_only_as_no_hole": "injectivity coexists with hole",
        "no_cardinality_label_as_no_hole": "cardinality coexists with hole",
        "no_packing_label_as_no_hole": "packing label coexists with hole",
        "no_selected_event_as_no_hole": "selected event coexists with hole",
        "nearest_confuser_level474_distinction": "positive witness, not receipt rejection",
        "nearest_confuser_level465_distinction": "interval image fails at slot 1",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index skipped-slot hostile witness."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_skipped_slot_hostile_witness_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_skipped_slot_hostile_witness_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
