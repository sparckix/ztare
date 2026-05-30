"""G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON.

Receipt gate for deriving bounded incident existence from an explicit
target-indexed eventData candidate with a final-slot horizon bound.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-BOUNDED-INCIDENT-EXISTENCE-EVENTDATA-HORIZON"

REQUIRED_FIELDS = (
    "target_family",
    "target_event_candidate",
    "candidate_event_selector",
    "eventdata_binding",
    "horizon_bound",
    "incidence_witness",
    "bounded_existence_derivation",
    "prefix_domination_binding",
    "same_tree_binding",
    "fixed_before_payoff",
    "no_post_payoff_choice",
    "not_target_deficit_selected",
    "not_label_only_eventdata",
    "not_label_only_incidence",
    "downstream_no_reuse_collision_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "eventdata_label_only",
    "prefix_domination_label_only",
    "same_tree_label_only",
    "horizon_label_only",
    "incidence_label_only",
    "opaque_exists_prop",
    "cardinality_bound_as_existence",
)

HARD_VIOLATIONS = (
    "post_payoff_event_choice",
    "target_deficit_event_choice",
    "event_family_drift",
    "unbounded_event_index",
    "incidence_not_displayed",
    "cardinality_as_existence",
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


def run_bounded_incident_existence_eventdata_horizon_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate an eventData/horizon bounded incident existence receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "bounded_incident_eventdata_horizon_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed bounded incident eventData/horizon receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "bounded_incident_eventdata_horizon_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "bounded incident existence needs a concrete target event "
                "candidate, eventData binding, final-slot horizon bound, "
                "displayed incidence witness, prefix/same-tree provenance, "
                "and anti-target/anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "bounded_incident_eventdata_horizon_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "eventData, prefix-domination, horizon, or incidence labels "
                "do not construct a bounded event witness"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "bounded_incident_eventdata_horizon_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the witness is posthoc, target-defined, carrier-drifting, "
                "unbounded, not displayed by incidence, or circular through "
                "cardinality"
            ),
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "summary": (
            "complete bounded incident eventData/horizon receipt"
            if complete else
            "incomplete bounded incident eventData/horizon receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_bounded_incident_existence_eventdata_horizon_gate({
        "target_family": "L3A target prefix",
        "eventdata_label_only": "eventData exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["eventdata_label_only"]

    blocked = run_bounded_incident_existence_eventdata_horizon_gate({
        "target_family": "L3A target prefix",
        "eventdata_label_only": "eventData exists",
    }, enforce_block=True)
    assert blocked["passed"] is False

    falsey = run_bounded_incident_existence_eventdata_horizon_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "post_payoff_event_choice": "not a post payoff choice",
    }, enforce_block=True)
    assert falsey["passed"] is False
    assert falsey["hard_violations_present"] == ["post_payoff_event_choice"]

    strong = run_bounded_incident_existence_eventdata_horizon_gate({
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
        description="Validate a bounded incident eventData/horizon receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_bounded_incident_existence_eventdata_horizon_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
