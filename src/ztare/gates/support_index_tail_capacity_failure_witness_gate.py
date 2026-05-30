"""G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS.

Validate a finite hostile witness for the Level478 final-endpoint capacity
law.  The receipt demonstrates that base anchor, strict support-index order,
lower endpoint control, cardinality/packing-style labels, or selected-event
labels can be visible while the tail-capacity inequality still fails.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-TAIL-CAPACITY-FAILURE-WITNESS"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_index_values",
    "support_length",
    "prefix_domain",
    "base_index",
    "final_slot",
    "support_length_eq_succ_final_slot",
    "capacity_failure_index",
    "capacity_failure_index_in_prefix",
    "base_anchor_at_zero_holds",
    "strict_order_on_prefix_holds",
    "lower_endpoint_bound_on_prefix_holds",
    "finite_image_cardinality_eq_support_length_holds",
    "weak_boundary_or_packing_evidence_holds",
    "weak_cardinality_evidence_holds",
    "weak_selected_event_or_size_sum_evidence_holds",
    "tail_room_at_failure_index",
    "final_endpoint_capacity_bound_fails",
    "tail_capacity_inequality_fails",
    "derived_upper_endpoint_bound_fails",
    "level477_lower_bound_still_holds",
    "level478_capacity_receipt_missing",
    "level476_endpoint_tight_rejected",
    "level464_no_hole_not_constructed",
    "not_lower_bound_only_as_capacity",
    "not_strict_order_only_as_capacity",
    "not_cardinality_label_as_capacity",
    "not_finite_image_as_range_capacity",
    "not_packing_label_as_capacity",
    "not_carleson_label_as_capacity",
    "not_selected_event_as_capacity",
    "not_no_hole_assumed",
    "not_endpoint_tight_assumed",
    "not_unit_gap_assumed",
    "not_affine_stride_one_assumed",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_final_slot",
    "no_post_payoff_capacity_tuning",
    "no_post_payoff_reindexing",
    "nearest_confuser_level478_distinction",
    "nearest_confuser_level477_distinction",
    "nearest_confuser_level476_distinction",
    "nearest_confuser_level475_distinction",
    "nearest_confuser_cardinality_distinction",
)

FORBIDDEN_SHORTCUTS = (
    "tail_capacity_label",
    "upper_endpoint_label",
    "endpoint_tight_label",
    "no_hole_label",
    "unit_gap_label",
    "affine_stride_one_label",
    "cardinality_label_as_capacity",
    "finite_image_label_as_capacity",
    "packing_label_as_capacity",
    "carleson_label_as_capacity",
    "selected_event_as_capacity",
    "post_payoff_tail_fit",
    "target_defined_capacity_fit",
    "post_payoff_reindexing",
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


def _lower_endpoint_holds(values: list[int], base_index: int) -> bool:
    return all(base_index + i <= value for i, value in enumerate(values))


def run_support_index_tail_capacity_failure_witness_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_tail_capacity_failure_witness_malformed",
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
    base_index = _as_int(receipt.get("base_index"))
    final_slot = _as_int(receipt.get("final_slot"))
    fail_index = _as_int(receipt.get("capacity_failure_index"))
    forbidden = [
        field for field in FORBIDDEN_SHORTCUTS if _present(receipt.get(field))
    ]

    if missing:
        violations.append({
            "type": "support_index_tail_capacity_failure_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "hostile witness must record the support-index values, base "
                "anchor, strict/lower fields that still hold, the failing "
                "tail-capacity inequality, and distinctions from Level478, "
                "endpoint-tight, no-hole, and weak capacity labels"
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
    if base_index is None:
        violations.append({
            "type": "base_index_not_integer",
            "reason": "base_index must be an integer",
        })
    if final_slot is None:
        violations.append({
            "type": "final_slot_not_integer",
            "reason": "final_slot must be an integer",
        })
    if fail_index is None:
        violations.append({
            "type": "capacity_failure_index_not_integer",
            "reason": "capacity_failure_index must be an integer",
        })

    computed: dict[str, Any] = {
        "support_index_values": values,
        "support_length": support_length,
        "base_index": base_index,
        "final_slot": final_slot,
        "capacity_failure_index": fail_index,
    }

    if values is not None and support_length is not None:
        computed["strictly_increasing"] = _strictly_increasing(values)
        computed["image_cardinality"] = len(set(values))
        if len(values) != support_length:
            violations.append({
                "type": "support_index_values_length_mismatch",
                "expected": support_length,
                "actual": len(values),
            })
        if not _strictly_increasing(values):
            violations.append({
                "type": "support_index_values_not_strictly_ordered",
                "reason": "the witness should keep strict order true",
            })
        if len(set(values)) != len(values):
            violations.append({
                "type": "support_index_values_not_injective",
                "reason": "the witness should keep finite-image labels true",
            })
    if (
        support_length is not None
        and final_slot is not None
        and final_slot + 1 != support_length
    ):
        violations.append({
            "type": "final_slot_not_support_length_minus_one",
            "support_length": support_length,
            "final_slot": final_slot,
        })
    if (
        values is not None
        and support_length is not None
        and base_index is not None
    ):
        computed["lower_endpoint_holds"] = _lower_endpoint_holds(values, base_index)
        if values and values[0] != base_index:
            violations.append({
                "type": "base_anchor_at_zero_fails",
                "support_index_zero": values[0],
                "base_index": base_index,
            })
        if not _lower_endpoint_holds(values, base_index):
            violations.append({
                "type": "lower_endpoint_bound_not_preserved",
                "reason": (
                    "Level479 must isolate upper/final-capacity failure while "
                    "preserving the Level477 lower-bound field"
                ),
            })
    if (
        values is not None
        and support_length is not None
        and base_index is not None
        and fail_index is not None
    ):
        if fail_index < 0 or fail_index >= len(values):
            violations.append({
                "type": "capacity_failure_index_out_of_range",
                "capacity_failure_index": fail_index,
                "support_index_values_len": len(values),
            })
        else:
            tail_room = support_length - (fail_index + 1)
            final_endpoint = base_index + (support_length - 1)
            tail_capacity_value = values[fail_index] + tail_room
            upper_endpoint_value = base_index + fail_index
            computed.update({
                "tail_room_at_failure_index": tail_room,
                "final_endpoint": final_endpoint,
                "tail_capacity_value": tail_capacity_value,
                "upper_endpoint_value": upper_endpoint_value,
                "tail_capacity_failure_holds": final_endpoint < tail_capacity_value,
                "upper_endpoint_failure_holds": upper_endpoint_value < values[fail_index],
            })
            if final_endpoint >= tail_capacity_value:
                violations.append({
                    "type": "tail_capacity_inequality_not_failed",
                    "final_endpoint": final_endpoint,
                    "tail_capacity_value": tail_capacity_value,
                })
            if upper_endpoint_value >= values[fail_index]:
                violations.append({
                    "type": "upper_endpoint_bound_not_failed",
                    "upper_endpoint_value": upper_endpoint_value,
                    "support_index_at_failure": values[fail_index],
                })
    if forbidden:
        violations.append({
            "type": "forbidden_capacity_shortcuts_present",
            "forbidden_shortcuts": forbidden,
            "reason": (
                "the witness may expose weak labels, but it cannot route "
                "those labels as tail capacity, endpoint tightness, no-hole, "
                "unit-gap, or affine-stride evidence"
            ),
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_tail_capacity_failure_witness"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "forbidden_shortcuts_present": forbidden,
        "computed": computed,
        "summary": (
            "support-index tail-capacity failure witness"
            if not violations else
            "support-index tail-capacity failure witness rejected with "
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
    weak = run_support_index_tail_capacity_failure_witness_gate({
        "support_index_values": [0, 1],
        "support_length": 2,
        "base_index": 0,
        "final_slot": 1,
        "capacity_failure_index": 1,
        "tail_capacity_label": "tail capacity by cardinality",
    })
    assert weak["passed"] is False

    strong = run_support_index_tail_capacity_failure_witness_gate({
        "label": "two_slot_upward_drift_capacity_failure",
        "support_index_map": "0 -> 0, 1 -> 2",
        "support_index_values": [0, 2],
        "support_length": 2,
        "prefix_domain": "Finset.range 2",
        "base_index": 0,
        "final_slot": 1,
        "support_length_eq_succ_final_slot": "2 = 1 + 1",
        "capacity_failure_index": 1,
        "capacity_failure_index_in_prefix": "1 < 2",
        "base_anchor_at_zero_holds": "supportIndex 0 = 0",
        "strict_order_on_prefix_holds": "0 < 2",
        "lower_endpoint_bound_on_prefix_holds": "0+k <= 2*k for k<2",
        "finite_image_cardinality_eq_support_length_holds": "image {0,2} has card 2",
        "weak_boundary_or_packing_evidence_holds": "packing label can be visible",
        "weak_cardinality_evidence_holds": "cardinality label holds",
        "weak_selected_event_or_size_sum_evidence_holds": "selected event label visible",
        "tail_room_at_failure_index": "2 - (1+1) = 0",
        "final_endpoint_capacity_bound_fails": "base+(2-1)=1 < supportIndex 1=2",
        "tail_capacity_inequality_fails": "1 < 2 + 0",
        "derived_upper_endpoint_bound_fails": "0+1 < supportIndex 1",
        "level477_lower_bound_still_holds": "Level477 lower endpoint survives",
        "level478_capacity_receipt_missing": "tail capacity is exactly missing",
        "level476_endpoint_tight_rejected": "upper endpoint bound fails",
        "level464_no_hole_not_constructed": "slot 1 is skipped",
        "not_lower_bound_only_as_capacity": "lower bound coexists with failure",
        "not_strict_order_only_as_capacity": "strict order coexists with failure",
        "not_cardinality_label_as_capacity": "cardinality coexists with failure",
        "not_finite_image_as_range_capacity": "finite image coexists with failure",
        "not_packing_label_as_capacity": "packing coexists with failure",
        "not_carleson_label_as_capacity": "Carleson label coexists with failure",
        "not_selected_event_as_capacity": "selected event coexists with failure",
        "not_no_hole_assumed": "no-hole is downstream and false here",
        "not_endpoint_tight_assumed": "endpoint tightness is downstream and false here",
        "not_unit_gap_assumed": "unit gap is false here",
        "not_affine_stride_one_assumed": "affine stride one is false here",
        "fixed_before_payoff": "finite map fixed before payoff",
        "not_target_defined": "literal two-slot witness",
        "no_post_payoff_final_slot": "final slot fixed as 1",
        "no_post_payoff_capacity_tuning": "no tuning",
        "no_post_payoff_reindexing": "no reindexing",
        "nearest_confuser_level478_distinction": "opposite of capacity receipt",
        "nearest_confuser_level477_distinction": "lower bound still holds",
        "nearest_confuser_level476_distinction": "endpoint tightness fails",
        "nearest_confuser_level475_distinction": "specializes upward drift to capacity failure",
        "nearest_confuser_cardinality_distinction": "cardinality is not capacity",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True
    assert strong["computed"]["tail_capacity_failure_holds"] is True
    assert strong["computed"]["upper_endpoint_failure_holds"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index tail-capacity failure witness."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_tail_capacity_failure_witness_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_tail_capacity_failure_witness_gate(
        _read_json(args.receipt_json)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
