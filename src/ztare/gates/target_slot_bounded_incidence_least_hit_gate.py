"""G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT.

Receipt gate for deriving a final-slot target assignment by least-hit
selection from a bounded displayed-incidence existence theorem.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-TARGET-SLOT-BOUNDED-INCIDENCE-LEAST-HIT"

REQUIRED_FIELDS = (
    "target_family",
    "incidence_relation",
    "bounded_incident_existence_theorem",
    "least_hit_target_slot_rule",
    "target_slot_codomain",
    "target_slot_bound_derivation",
    "target_slot_incidence_law",
    "same_tree_eventdata_binding",
    "prefix_domination_binding",
    "fanout_no_reuse_binding",
    "assignment_totality",
    "assignment_fixed_before_payoff",
    "no_post_payoff_least_hit_choice",
    "no_post_payoff_existence_choice",
    "not_target_deficit_selected",
    "not_endpoint_capacity_only",
    "not_cardinality_as_injectivity",
    "not_label_only_assignment",
    "not_label_only_eventdata",
    "not_label_only_incidence",
    "downstream_finalslot_assignment_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "endpoint_capacity_label_only",
    "bounded_incidence_label_only",
    "least_hit_label_only",
    "opaque_final_slot_assignment",
    "exists_event_without_bound",
    "assignment_without_incidence",
    "prefix_domination_label_only",
)

HARD_VIOLATIONS = (
    "post_payoff_least_hit_choice",
    "post_payoff_existence_choice",
    "target_deficit_choice",
    "carrier_drift",
    "unbounded_target_slot",
    "target_slot_not_incident",
    "endpoint_capacity_as_assignment",
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


def run_target_slot_bounded_incidence_least_hit_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a bounded-incidence least-hit target-slot receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "target_slot_bounded_incidence_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed target-slot bounded-incidence receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "target_slot_bounded_incidence_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "least-hit target-slot assignment needs bounded incident "
                "existence, a Fin codomain, bound and incidence laws, "
                "same-tree/prefix/fanout bindings, timing, and anti-label "
                "checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "target_slot_bounded_incidence_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "endpoint-capacity labels, incidence labels, or opaque "
                "assignments do not derive the target slot by least-hit "
                "bounded incidence"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "target_slot_bounded_incidence_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the target slot is posthoc, target-defined, unbounded, "
                "carrier-drifting, nonincident, or an endpoint-capacity "
                "substitution"
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
            "complete target-slot bounded-incidence least-hit receipt"
            if complete else
            "incomplete target-slot bounded-incidence least-hit receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_target_slot_bounded_incidence_least_hit_gate({
        "target_family": "L3A target prefix",
        "endpoint_capacity_label_only": "target count <= final-slot count",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["endpoint_capacity_label_only"]

    blocked = run_target_slot_bounded_incidence_least_hit_gate({
        "target_family": "L3A target prefix",
        "least_hit_label_only": "least hit exists",
    }, enforce_block=True)
    assert blocked["passed"] is False

    hard = run_target_slot_bounded_incidence_least_hit_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "target_slot_not_incident": "slot chosen without incidence proof",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == ["target_slot_not_incident"]

    exact_false = run_target_slot_bounded_incidence_least_hit_gate({
        "target_family": "missing because provenance is being formalized",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "incidence_relation"

    strong = run_target_slot_bounded_incidence_least_hit_gate({
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
        description="Validate a target-slot bounded-incidence least-hit receipt."
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
    result = run_target_slot_bounded_incidence_least_hit_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
