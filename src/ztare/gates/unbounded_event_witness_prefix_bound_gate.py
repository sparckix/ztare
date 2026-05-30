"""G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND.

Receipt gate for constructing a bounded natural event enumeration from typed
unbounded natural event witnesses plus a separate final-prefix bound theorem.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-UNBOUNDED-EVENT-WITNESS-PREFIX-BOUND"

REQUIRED_FIELDS = (
    "target_family",
    "ordinary_coverage_packet",
    "selected_bad_node_natural_event_witness",
    "event_to_badnode_target_equality",
    "same_witness_prefix_bound",
    "strict_prefix_bound",
    "witness_refines_cofinal_selected_tree_incidence",
    "prefix_bound_comes_from_final_event_prefix",
    "witness_uses_same_bad_center_event_nodes",
    "witness_uses_event_to_badnode",
    "coverage_packet_forwards_exhaustion",
    "coverage_packet_forwards_prop_appearance",
    "coverage_packet_forwards_beta_domination",
    "coverage_packet_forwards_multiplicity",
    "coverage_packet_forwards_no_shell_only",
    "coverage_packet_forwards_no_adaptive_beta_sum",
    "witness_and_bound_fixed_before_payoff",
    "not_bare_prop_choice",
    "not_endpoint_capacity_only",
    "not_shell_only_enumeration",
    "not_post_payoff_selection",
    "downstream_bounded_natural_event_enumeration_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "existential_event_cover_only",
    "bounded_witness_assumed",
    "bound_on_different_witness",
    "coverage_prop_only",
    "event_to_badnode_label_only",
    "endpoint_capacity_label_only",
    "shell_enumeration_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice",
    "bounded_nat_witness_assumed_without_split",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "missing_prefix_bound",
    "bound_applies_to_different_witness",
    "witness_not_event_to_badnode",
    "endpoint_capacity_as_bound",
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


def run_unbounded_event_witness_prefix_bound_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate an unbounded-witness plus prefix-bound receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "unbounded_event_witness_prefix_bound_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed unbounded-event witness prefix-bound receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "unbounded_event_witness_prefix_bound_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "bounded enumeration needs the typed natural event witness, "
                "a strict bound on that same witness, eventToBadNode equality, "
                "coverage forwarding, timing, and anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "unbounded_event_witness_prefix_bound_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "existential cover, assumed bounded witnesses, a bound on a "
                "different witness, Prop coverage, labels, endpoint capacity, "
                "or shell labels do not construct the bounded event witness"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "unbounded_event_witness_prefix_bound_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the witness is bare-prop chosen, bounded witness is assumed, "
                "posthoc, target-deficit driven, carrier drifting, unbounded, "
                "bounded through a different witness, not eventToBadNode based, "
                "endpoint-only, adaptive, or shell-only"
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
            "complete unbounded-event witness prefix-bound receipt"
            if complete else
            "incomplete unbounded-event witness prefix-bound receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_unbounded_event_witness_prefix_bound_gate({
        "target_family": "selected bad nodes",
        "existential_event_cover_only": "exists event",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["existential_event_cover_only"]

    weak_with_strong = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_different_witness": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "bound_on_different_witness"
    ]

    hard = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_applies_to_different_witness": "wrong witness",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == [
        "bound_applies_to_different_witness"
    ]

    exact_false = run_unbounded_event_witness_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_natural_event_witness":
            "missing because cofinal receipt is pending",
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
        description="Validate an unbounded-event witness prefix-bound receipt."
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
    result = run_unbounded_event_witness_prefix_bound_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
