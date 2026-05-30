"""G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX.

Receipt gate for deriving bounded incident existence from an explicit
target-to-same-tree-eventData index cover.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-BOUNDED-INCIDENT-EXISTENCE-SAMETREE-EVENTDATA-INDEX"

REQUIRED_FIELDS = (
    "target_family",
    "same_tree_eventdata_stream",
    "target_eventdata_index",
    "target_eventdata_codomain",
    "eventdata_binding",
    "index_below_final_slot",
    "displayed_incidence_law",
    "bounded_existence_witness_rule",
    "same_tree_binding",
    "prefix_domination_binding",
    "fanout_no_reuse_binding",
    "fixed_before_payoff",
    "no_post_payoff_index_choice",
    "not_target_deficit_selected",
    "not_endpoint_capacity_only",
    "not_label_only_eventdata",
    "not_label_only_incidence",
    "downstream_least_hit_targetslot_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "same_tree_label_only",
    "eventdata_label_only",
    "incidence_label_only",
    "endpoint_capacity_label_only",
    "exists_event_without_eventdata_index",
    "opaque_event_index",
)

HARD_VIOLATIONS = (
    "post_payoff_index_choice",
    "target_deficit_choice",
    "carrier_drift",
    "index_outside_final_slot_prefix",
    "index_not_bound_to_eventdata",
    "index_not_incident",
    "endpoint_capacity_as_existence",
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


def run_bounded_incident_existence_sametree_eventdata_index_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a same-tree eventData index bounded-existence receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "same_tree_eventdata_index_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed same-tree eventData index receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "same_tree_eventdata_index_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "bounded existence needs a target eventData index, binding to "
                "the same-tree eventData stream, a final-slot bound, displayed "
                "incidence, timing, and anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "same_tree_eventdata_index_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "same-tree/eventData/incidence labels or endpoint capacity do "
                "not construct a target-indexed eventData cover"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "same_tree_eventdata_index_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the eventData index is posthoc, target-defined, carrier "
                "drifting, out of prefix, unbound to eventData, nonincident, "
                "or endpoint-capacity-only"
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
            "complete same-tree eventData index bounded-existence receipt"
            if complete else
            "incomplete same-tree eventData index bounded-existence receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_bounded_incident_existence_sametree_eventdata_index_gate({
        "target_family": "L3A target prefix",
        "eventdata_label_only": "sameTreeLock.eventData exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["eventdata_label_only"]

    blocked = run_bounded_incident_existence_sametree_eventdata_index_gate({
        "target_family": "L3A target prefix",
        "opaque_event_index": "some index",
    }, enforce_block=True)
    assert blocked["passed"] is False

    hard = run_bounded_incident_existence_sametree_eventdata_index_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "index_not_incident": "index lacks incidence proof",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == ["index_not_incident"]

    strong = run_bounded_incident_existence_sametree_eventdata_index_gate({
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
        description="Validate a same-tree eventData index bounded-existence receipt."
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
    result = run_bounded_incident_existence_sametree_eventdata_index_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
