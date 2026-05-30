"""G-BOUNDED-NATURAL-EVENT-ENUMERATION.

Receipt gate for converting selected-bad-node natural event indices with an
explicit final-prefix bound into finite event-prefix enumeration witnesses.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-BOUNDED-NATURAL-EVENT-ENUMERATION"

REQUIRED_FIELDS = (
    "target_family",
    "ordinary_coverage_packet",
    "selected_bad_node_natural_event_enumeration",
    "natural_index_codomain",
    "strict_prefix_bound",
    "event_to_badnode_target_equality",
    "natural_enumeration_refines_coverage_appearance",
    "natural_enumeration_uses_same_bad_center_event_nodes",
    "natural_enumeration_uses_event_to_badnode",
    "coverage_packet_forwards_exhaustion",
    "coverage_packet_forwards_prop_appearance",
    "coverage_packet_forwards_beta_domination",
    "coverage_packet_forwards_multiplicity",
    "coverage_packet_forwards_no_shell_only",
    "coverage_packet_forwards_no_adaptive_beta_sum",
    "natural_enumeration_fixed_before_payoff",
    "not_bare_prop_choice",
    "not_endpoint_capacity_only",
    "not_shell_only_enumeration",
    "not_post_payoff_selection",
    "downstream_event_prefix_enumeration_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "fin_enumeration_assumed",
    "coverage_prop_only",
    "unbounded_nat_index",
    "event_to_badnode_label_only",
    "endpoint_capacity_label_only",
    "shell_enumeration_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice",
    "fin_witness_assumed_without_nat_bound",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "missing_strict_prefix_bound",
    "witness_not_event_to_badnode",
    "endpoint_capacity_as_choice",
    "adaptive_stopping_from_beta_sum",
    "shell_only_enumeration",
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


def run_bounded_natural_event_enumeration_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a bounded-natural event enumeration receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "bounded_natural_event_enumeration_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed bounded-natural event enumeration receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "bounded_natural_event_enumeration_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "natural event enumeration needs the selected-bad-node "
                "witness, strict final-prefix bound, eventToBadNode equality, "
                "coverage forwarding, timing, and anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "bounded_natural_event_enumeration_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "assuming Fin enumeration, relying on Prop coverage, using "
                "unbounded Nat indices, labels, endpoint capacity, or shell "
                "labels does not construct the bounded natural enumeration"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "bounded_natural_event_enumeration_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the witness is bare-prop chosen, Fin-assumed, posthoc, target "
                "deficit driven, carrier drifting, unbounded, not eventToBadNode "
                "based, endpoint-only, adaptive, or shell-only"
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
            "complete bounded-natural event enumeration receipt"
            if complete else
            "incomplete bounded-natural event enumeration receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_bounded_natural_event_enumeration_gate({
        "target_family": "selected bad nodes",
        "coverage_prop_only": "coverage exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["coverage_prop_only"]

    weak_with_strong = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "fin_enumeration_assumed": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "fin_enumeration_assumed"
    ]

    hard = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "missing_strict_prefix_bound": "unbounded Nat witness",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == ["missing_strict_prefix_bound"]

    exact_false = run_bounded_natural_event_enumeration_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_natural_event_enumeration":
            "missing because bounded theorem is pending",
    }, enforce_block=True)
    assert exact_false["passed"] is True
    assert exact_false["missing_fields"] == []


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
        description="Validate a bounded-natural event enumeration receipt."
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
    result = run_bounded_natural_event_enumeration_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
