"""G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND.

Receipt gate for constructing an explicit cofinal event witness from a named
event selector plus its eventToBadNode equality and same-selector prefix bound.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-COFINAL-EVENT-SELECTOR-FINAL-PREFIX-BOUND"

REQUIRED_FIELDS = (
    "target_family",
    "ordinary_coverage_packet",
    "cofinal_selected_tree_incidence_receipt",
    "cofinal_event_selector",
    "selector_event_to_badnode_equality",
    "same_selector_final_prefix_bound",
    "strict_prefix_bound",
    "selector_refines_cofinal_incidence",
    "selector_bound_comes_from_final_event_prefix",
    "selector_uses_same_bad_center_event_nodes",
    "selector_uses_event_to_badnode",
    "coverage_packet_forwards_exhaustion",
    "coverage_packet_forwards_prop_appearance",
    "coverage_packet_forwards_beta_domination",
    "coverage_packet_forwards_multiplicity",
    "coverage_packet_forwards_no_shell_only",
    "coverage_packet_forwards_no_adaptive_beta_sum",
    "selector_and_bound_fixed_before_payoff",
    "not_bare_prop_choice_for_selector",
    "not_endpoint_capacity_only",
    "not_shell_only_enumeration",
    "not_post_payoff_selection",
    "downstream_explicit_cofinal_event_witness_bound_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "explicit_subtype_witness_only",
    "classical_choice_witness_only",
    "event_cover_prop_only",
    "selector_without_equality",
    "bound_on_nonselector_witness",
    "cofinal_label_only",
    "event_to_badnode_label_only",
    "endpoint_capacity_label_only",
    "shell_enumeration_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice_without_selector",
    "classical_choice_without_selector",
    "subtype_witness_without_selector_rule",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "missing_prefix_bound",
    "bound_applies_to_nonselector",
    "selector_not_event_to_badnode",
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


def run_cofinal_event_selector_final_prefix_bound_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a cofinal event-selector final-prefix-bound receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "cofinal_event_selector_final_prefix_bound_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed cofinal event-selector final-prefix-bound receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "cofinal_event_selector_final_prefix_bound_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "selector construction needs a named event selector, its "
                "eventToBadNode equality, a strict final-prefix bound on that "
                "same selector, coverage forwarding, timing, and anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "cofinal_event_selector_final_prefix_bound_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "subtype witnesses, Classical-choice wrappers, Prop cover labels, "
                "selectors without equality, nonselector bounds, endpoint capacity, "
                "or shell labels do not construct the selector-bound source"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "cofinal_event_selector_final_prefix_bound_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the selector is bare-choice, Classical-only, subtype-only, posthoc, "
                "target-deficit driven, carrier drifting, unbounded, bounded through "
                "another witness, not eventToBadNode based, endpoint-only, adaptive, "
                "or shell-only"
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
            "complete cofinal event-selector final-prefix-bound receipt"
            if complete else
            "incomplete cofinal event-selector final-prefix-bound receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_cofinal_event_selector_final_prefix_bound_gate({
        "target_family": "selected bad nodes",
        "explicit_subtype_witness_only": "subtype exists but no selector rule",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["explicit_subtype_witness_only"]

    weak_with_strong = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_nonselector_witness": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "bound_on_nonselector_witness"
    ]

    hard = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "subtype_witness_without_selector_rule": "implicit projection only",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == [
        "subtype_witness_without_selector_rule"
    ]

    exact_false = run_cofinal_event_selector_final_prefix_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cofinal_event_selector":
            "missing because selector theorem is pending",
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
        description="Validate a cofinal event-selector final-prefix-bound receipt."
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
    result = run_cofinal_event_selector_final_prefix_bound_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
