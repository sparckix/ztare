"""G-TARGET-EVENT-CANDIDATE-COVER-SELECTION.

Receipt gate for deriving target event candidates from an explicit target-cover
selection relation before using them as bounded incident witnesses.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-TARGET-EVENT-CANDIDATE-COVER-SELECTION"

REQUIRED_FIELDS = (
    "target_family",
    "cover_relation",
    "cover_selector",
    "selector_totality",
    "horizon_from_cover",
    "incidence_from_cover",
    "eventdata_binding",
    "prefix_domination_binding",
    "same_tree_binding",
    "fixed_before_payoff",
    "no_post_payoff_selection",
    "not_target_deficit_selected",
    "not_label_only_cover",
    "not_label_only_eventdata",
    "downstream_eventdata_horizon_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "cover_label_only",
    "eventdata_label_only",
    "prefix_domination_label_only",
    "same_tree_label_only",
    "opaque_selector",
    "horizon_label_only",
    "incidence_label_only",
)

HARD_VIOLATIONS = (
    "post_payoff_selector",
    "target_deficit_selector",
    "event_family_drift",
    "unbounded_selected_event",
    "selected_event_not_incident",
    "cardinality_as_cover_totality",
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


def run_target_event_candidate_cover_selection_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a target-event-candidate cover-selection receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "target_event_candidate_cover_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed target-event-candidate cover receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "target_event_candidate_cover_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "candidate production needs a concrete cover relation, "
                "selector totality, cover-to-horizon and cover-to-incidence "
                "rules, same-tree/eventData provenance, and anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "target_event_candidate_cover_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "cover/eventData/prefix labels or opaque selector fields do "
                "not produce a bounded incident event candidate"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "target_event_candidate_cover_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the selected event is posthoc, target-defined, "
                "carrier-drifting, unbounded, nonincident, or circular "
                "through cardinality"
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
            "complete target-event-candidate cover-selection receipt"
            if complete else
            "incomplete target-event-candidate cover-selection receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_target_event_candidate_cover_selection_gate({
        "target_family": "L3A target prefix",
        "cover_label_only": "cover exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["cover_label_only"]

    blocked = run_target_event_candidate_cover_selection_gate({
        "target_family": "L3A target prefix",
        "cover_label_only": "cover exists",
    }, enforce_block=True)
    assert blocked["passed"] is False

    hard = run_target_event_candidate_cover_selection_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "target_deficit_selector": "selected from target deficit",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == ["target_deficit_selector"]

    strong = run_target_event_candidate_cover_selection_gate({
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
        description="Validate a target-event-candidate cover-selection receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_target_event_candidate_cover_selection_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
