"""G-TARGET-COVER-EVENTDATA-INCIDENCE.

Receipt gate for deriving a target-cover relation from explicit same-tree
eventData incidence laws, rather than naming ``targetCover`` as an opaque
relation before selecting a witness.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-TARGET-COVER-EVENTDATA-INCIDENCE"

REQUIRED_FIELDS = (
    "target_family",
    "eventdata_source",
    "target_node_source",
    "cover_event_selector",
    "cover_relation_definition",
    "selector_totality",
    "cover_relation_is_selector_graph",
    "selector_below_final_slot",
    "selector_incident_to_target",
    "cover_to_horizon_law",
    "cover_to_incidence_law",
    "same_tree_binding",
    "prefix_domination_binding",
    "incidence_geometry_binding",
    "fixed_before_payoff",
    "no_post_payoff_cover_choice",
    "not_target_deficit_selected",
    "not_label_only_eventdata",
    "not_label_only_incidence",
    "not_label_only_cover",
    "downstream_cover_selection_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "target_cover_label_only",
    "eventdata_label_only",
    "incidence_label_only",
    "prefix_domination_label_only",
    "same_tree_label_only",
    "opaque_cover_prop",
    "classical_choice_from_existence",
)

HARD_VIOLATIONS = (
    "post_payoff_cover_choice",
    "target_deficit_cover_choice",
    "event_family_drift",
    "selector_not_below_final_slot",
    "selector_not_incident",
    "cover_defined_by_cardinality_deficit",
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


def run_target_cover_eventdata_incidence_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate an eventData/incidence target-cover receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "target_cover_eventdata_incidence_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed target-cover eventData/incidence receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "target_cover_eventdata_incidence_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "cover construction needs a displayed eventData source, target "
                "node source, cover-event selector, selector graph definition, "
                "horizon and incidence laws, same-tree/prefix/incidence "
                "bindings, and anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "target_cover_eventdata_incidence_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "cover/eventData/incidence labels or opaque existence choices "
                "do not construct a same-tree cover-event selector"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "target_cover_eventdata_incidence_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the cover choice is posthoc, target-defined, carrier-drifting, "
                "outside the final slot, nonincident, or circular through "
                "cardinality"
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
            "complete target-cover eventData/incidence receipt"
            if complete else
            "incomplete target-cover eventData/incidence receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_target_cover_eventdata_incidence_gate({
        "target_family": "L3A target prefix",
        "target_cover_label_only": "targetCover exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["target_cover_label_only"]

    blocked = run_target_cover_eventdata_incidence_gate({
        "target_family": "L3A target prefix",
        "target_cover_label_only": "targetCover exists",
    }, enforce_block=True)
    assert blocked["passed"] is False

    hard = run_target_cover_eventdata_incidence_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selector_not_incident": "selected cover event is not incident",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == ["selector_not_incident"]

    exact_false = run_target_cover_eventdata_incidence_gate({
        "target_family": "missing because target-family proof is pending",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "eventdata_source"

    strong = run_target_cover_eventdata_incidence_gate({
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
        description="Validate a target-cover eventData/incidence receipt."
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
    result = run_target_cover_eventdata_incidence_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
