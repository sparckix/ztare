"""G-EVENT-PREFIX-ENUMERATION-PACKET.

Receipt gate for constructing a typed bad-center coverage packet from an
explicit finite event-prefix enumeration theorem.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-EVENT-PREFIX-ENUMERATION-PACKET"

REQUIRED_FIELDS = (
    "target_family",
    "ordinary_coverage_packet",
    "selected_bad_node_event_prefix_enumeration",
    "enumeration_codomain",
    "enumeration_refines_coverage_appearance",
    "enumeration_bounded_by_final_event_prefix",
    "enumeration_uses_same_bad_center_event_nodes",
    "enumeration_uses_event_to_badnode",
    "event_to_badnode_target_equality",
    "coverage_packet_forwards_exhaustion",
    "coverage_packet_forwards_prop_appearance",
    "coverage_packet_forwards_beta_domination",
    "coverage_packet_forwards_multiplicity",
    "coverage_packet_forwards_no_shell_only",
    "coverage_packet_forwards_no_adaptive_beta_sum",
    "enumeration_fixed_before_payoff",
    "not_bare_prop_choice",
    "not_endpoint_capacity_only",
    "not_shell_only_enumeration",
    "not_post_payoff_selection",
    "downstream_typed_coverage_packet",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "ordinary_coverage_only",
    "typed_packet_assumed",
    "appearance_prop_only",
    "event_to_badnode_label_only",
    "endpoint_capacity_label_only",
    "shell_enumeration_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice",
    "typed_packet_assumed_without_enumeration",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "enumeration_outside_final_prefix",
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


def run_event_prefix_enumeration_packet_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate an event-prefix enumeration packet receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "event_prefix_enumeration_packet_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed event-prefix enumeration packet receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "event_prefix_enumeration_packet_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "packet construction needs finite selected-bad-node event "
                "enumeration, final-prefix bound, eventToBadNode equality, "
                "ordinary coverage forwarding, timing, and anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "event_prefix_enumeration_packet_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "ordinary coverage, assumed typed packets, Prop appearance, "
                "labels, endpoint capacity, or shell labels do not construct "
                "the finite enumeration theorem"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "event_prefix_enumeration_packet_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the packet is assumed, bare-prop chosen, posthoc, target "
                "deficit driven, carrier drifting, outside the final prefix, "
                "not eventToBadNode-based, endpoint-only, adaptive, or shell-only"
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
            "complete event-prefix enumeration packet receipt"
            if complete else
            "incomplete event-prefix enumeration packet receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_event_prefix_enumeration_packet_gate({
        "target_family": "L3A target prefix",
        "ordinary_coverage_only": "coverage exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["ordinary_coverage_only"]

    weak_with_strong = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_packet_assumed": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["typed_packet_assumed"]

    hard = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "typed_packet_assumed_without_enumeration": "packet supplied directly",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == [
        "typed_packet_assumed_without_enumeration"
    ]

    exact_false = run_event_prefix_enumeration_packet_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "selected_bad_node_event_prefix_enumeration":
            "missing because enumeration theorem is pending",
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
        description="Validate an event-prefix enumeration packet receipt."
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
    result = run_event_prefix_enumeration_packet_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
