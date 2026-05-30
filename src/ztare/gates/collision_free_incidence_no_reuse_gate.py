"""G-COLLISION-FREE-INCIDENCE-NO-REUSE.

Receipt gate for deriving collision-free incidence from a displayed no-reuse
primitive, rather than treating fanout/no-reuse labels as injectivity.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-COLLISION-FREE-INCIDENCE-NO-REUSE"

REQUIRED_FIELDS = (
    "incidence_relation",
    "target_family",
    "no_reuse_source",
    "no_reuse_proof",
    "collision_free_theorem",
    "derivation_rule",
    "same_event_family_binding",
    "before_cardinality",
    "fixed_before_payoff",
    "no_post_payoff_choice",
    "not_target_deficit_selected",
    "not_label_only_fanout",
    "downstream_bounded_incidence_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "fanout_label_only",
    "no_reuse_label_only",
    "same_tree_label_only",
    "collision_free_label_only",
    "opaque_injectivity_prop",
    "cardinality_bound_assumed",
)

HARD_VIOLATIONS = (
    "post_payoff_collision_rule",
    "target_deficit_collision_rule",
    "event_family_drift",
    "collision_allowed",
    "injectivity_from_cardinality_bound",
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


def run_collision_free_incidence_no_reuse_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a collision-free incidence from no-reuse receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "collision_free_no_reuse_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed collision-free incidence no-reuse receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "collision_free_no_reuse_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "collision-free incidence needs a displayed no-reuse source, "
                "a no-reuse proof, an explicit theorem/rule to collision "
                "freedom, and anti-label-only checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "collision_free_no_reuse_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "fanout/no-reuse/same-tree labels or opaque injectivity do "
                "not prove that one incident event cannot pay two targets"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "collision_free_no_reuse_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the collision rule is posthoc, target-defined, "
                "carrier-drifting, collision-prone, or circular through "
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
            "complete collision-free incidence no-reuse receipt"
            if complete else
            f"incomplete collision-free incidence no-reuse receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_collision_free_incidence_no_reuse_gate({
        "no_reuse_source": "FreshFrequencyBoundedFanoutNoLogReuse",
        "fanout_label_only": "fanout present",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["fanout_label_only"]

    blocked = run_collision_free_incidence_no_reuse_gate({
        "no_reuse_source": "FreshFrequencyBoundedFanoutNoLogReuse",
        "fanout_label_only": "fanout present",
    }, enforce_block=True)
    assert blocked["passed"] is False

    strong = run_collision_free_incidence_no_reuse_gate({
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
        description="Validate a collision-free incidence no-reuse receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_collision_free_incidence_no_reuse_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
