"""G-BOUNDED-INCIDENCE-LEAST-HIT-SELECTOR.

Receipt gate for deriving a finite event-index selector from a bounded
incidence existence theorem by least-hit selection.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-BOUNDED-INCIDENCE-LEAST-HIT-SELECTOR"

REQUIRED_FIELDS = (
    "incidence_relation",
    "target_family",
    "bounded_existence_theorem",
    "least_hit_selector_rule",
    "bound_derivation",
    "collision_free_incidence_theorem",
    "injectivity_derivation",
    "same_event_family_binding",
    "fixed_before_payoff",
    "no_post_payoff_choice",
    "not_target_deficit_selected",
    "not_cardinality_as_injectivity",
    "not_label_only_incidence",
    "downstream_bounded_event_index_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "incidence_label_only",
    "bounded_fanout_label_only",
    "prefix_domination_label_only",
    "exists_event_without_bound",
    "collision_free_label_only",
    "opaque_injective_map",
)

HARD_VIOLATIONS = (
    "post_payoff_least_hit_choice",
    "target_deficit_choice",
    "event_family_drift",
    "collision_allowed",
    "injectivity_from_cardinality_bound",
    "unbounded_event_index",
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


def run_bounded_incidence_least_hit_selector_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a bounded least-hit incidence selector receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "bounded_incidence_least_hit_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed bounded incidence least-hit selector receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "bounded_incidence_least_hit_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "least-hit selection needs bounded existence, an explicit "
                "selector rule, a bound proof, collision-free incidence, "
                "injectivity derivation, and anti-label-only checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "bounded_incidence_least_hit_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "incidence/fanout/prefix labels or opaque injectivity do not "
                "construct a bounded least-hit event-index selector"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "bounded_incidence_least_hit_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the selector is posthoc, target-defined, unbounded, "
                "carrier-drifting, collision-prone, or derives injectivity "
                "from the cardinality conclusion"
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
            "complete bounded incidence least-hit selector receipt"
            if complete else
            f"incomplete bounded incidence least-hit selector receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_bounded_incidence_least_hit_selector_gate({
        "incidence_relation": "BadCenterEventIncidenceGeometry.incidence",
        "incidence_label_only": "incidence present",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["incidence_label_only"]

    blocked = run_bounded_incidence_least_hit_selector_gate({
        "incidence_relation": "BadCenterEventIncidenceGeometry.incidence",
        "incidence_label_only": "incidence present",
    }, enforce_block=True)
    assert blocked["passed"] is False

    strong = run_bounded_incidence_least_hit_selector_gate({
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
        description="Validate a bounded incidence least-hit selector receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_bounded_incidence_least_hit_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
