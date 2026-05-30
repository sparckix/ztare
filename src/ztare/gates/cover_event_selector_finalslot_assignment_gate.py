"""G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT.

Receipt gate for deriving a Nat-valued cover-event selector from a final-slot
indexed eventData assignment with displayed incidence.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-COVER-EVENT-SELECTOR-FINALSLOT-ASSIGNMENT"

REQUIRED_FIELDS = (
    "target_family",
    "final_slot_assignment",
    "assignment_codomain",
    "cover_event_selector_definition",
    "selector_is_assignment_value",
    "selector_below_final_slot",
    "assignment_incidence_law",
    "selector_incidence_transport",
    "eventdata_binding",
    "same_tree_binding",
    "prefix_domination_binding",
    "incidence_geometry_binding",
    "assignment_totality",
    "assignment_fixed_before_payoff",
    "not_target_deficit_selected",
    "no_post_payoff_assignment",
    "not_endpoint_capacity_only",
    "not_label_only_assignment",
    "not_label_only_eventdata",
    "not_label_only_incidence",
    "downstream_eventdata_incidence_cover_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "nat_selector_without_assignment",
    "assignment_label_only",
    "eventdata_label_only",
    "incidence_label_only",
    "prefix_domination_label_only",
    "endpoint_capacity_label_only",
    "opaque_final_slot_map",
)

HARD_VIOLATIONS = (
    "post_payoff_assignment",
    "target_deficit_assignment",
    "carrier_drift",
    "assignment_outside_final_slot_prefix",
    "assignment_not_incident",
    "endpoint_capacity_as_assignment",
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


def run_cover_event_selector_finalslot_assignment_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a final-slot assignment cover-selector receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "cover_event_selector_finalslot_assignment_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed cover-event selector final-slot assignment receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "cover_event_selector_finalslot_assignment_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "selector construction needs a displayed final-slot assignment, "
                "Fin codomain, selector-as-assignment-value law, incidence "
                "law, eventData/same-tree/prefix/incidence bindings, timing, "
                "and anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "cover_event_selector_finalslot_assignment_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "Nat selectors, assignment/eventData/incidence labels, or "
                "endpoint-capacity labels do not construct the final-slot "
                "eventData assignment"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "cover_event_selector_finalslot_assignment_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the assignment is posthoc, target-defined, carrier-drifting, "
                "outside the final-slot prefix, nonincident, or just an "
                "endpoint-capacity restatement"
            ),
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present
    return {
        "gate_id": GATE_ID,
        "passed": not blocking if enforce_block else True,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "summary": (
            "complete cover-event selector final-slot assignment receipt"
            if complete else
            "incomplete cover-event selector final-slot assignment receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_cover_event_selector_finalslot_assignment_gate({
        "target_family": "L3A target prefix",
        "nat_selector_without_assignment": "free selector",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["nat_selector_without_assignment"]

    blocked = run_cover_event_selector_finalslot_assignment_gate({
        "target_family": "L3A target prefix",
        "assignment_label_only": "assignment exists",
    }, enforce_block=True)
    assert blocked["passed"] is False

    hard = run_cover_event_selector_finalslot_assignment_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "endpoint_capacity_as_assignment": "target count <= final slot",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == ["endpoint_capacity_as_assignment"]

    exact_false = run_cover_event_selector_finalslot_assignment_gate({
        "target_family": "missing because provenance is being formalized",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "final_slot_assignment"

    strong = run_cover_event_selector_finalslot_assignment_gate({
        field: "ok" for field in REQUIRED_FIELDS
    }, enforce_block=True)
    assert strong["complete"] is True
    assert strong["passed"] is True


def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a cover-event selector final-slot assignment receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_cover_event_selector_finalslot_assignment_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
