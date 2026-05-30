"""G-TYPED-APPEARANCE-COVERAGE-CHOICE.

Receipt gate for deriving a target-indexed coverage-choice witness by
specializing a typed selected-bad-node appearance theorem.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-TYPED-APPEARANCE-COVERAGE-CHOICE"

REQUIRED_FIELDS = (
    "target_family",
    "typed_selected_bad_node_appearance",
    "target_node_selected_bad_membership",
    "coverage_choice_specialization",
    "selected_index_codomain",
    "event_to_badnode_target_equality",
    "coverage_packet",
    "appearance_refines_coverage",
    "appearance_uses_target_membership",
    "displayed_incidence_refinement",
    "same_tree_binding",
    "event_node_identification_binding",
    "event_prefixes_exhaust_selected_bad_nodes",
    "every_selected_bad_node_appears_in_some_prefix",
    "prefix_dominates_finite_selected_bad_tree_beta_sum",
    "duplicate_events_charge_multiplicity",
    "no_shell_only_enumeration_shortcut",
    "no_adaptive_stopping_from_beta_sum",
    "typed_appearance_fixed_before_payoff",
    "not_classical_choice_from_bare_appearance",
    "not_endpoint_capacity_only",
    "not_post_payoff_selection",
    "downstream_coverage_choice_finite_selector_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "appearance_prop_only",
    "target_membership_label_only",
    "coverage_label_only",
    "classical_choice_from_bare_prop_label",
    "opaque_coverage_choice",
    "endpoint_capacity_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "target_node_not_selected_bad",
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


def run_typed_appearance_coverage_choice_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a typed-appearance-to-coverage-choice receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "typed_appearance_coverage_choice_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed typed-appearance coverage-choice receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "typed_appearance_coverage_choice_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "typed appearance must provide a finite witness theorem over "
                "selected bad nodes, specialize it at target-node membership, "
                "and preserve event-to-badnode, same-tree, timing, and "
                "anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "typed_appearance_coverage_choice_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "bare appearance props, labels, endpoint capacity, and opaque "
                "coverageChoice fields do not derive the finite witness"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "typed_appearance_coverage_choice_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the witness is bare-prop chosen, posthoc, target-deficit "
                "driven, carrier drifting, disconnected from selected-bad "
                "membership or eventToBadNode, endpoint-only, adaptive, or "
                "shell-only"
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
            "complete typed-appearance coverage-choice receipt"
            if complete else
            "incomplete typed-appearance coverage-choice receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_typed_appearance_coverage_choice_gate({
        "target_family": "L3A target prefix",
        "appearance_prop_only": "appearance exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["appearance_prop_only"]

    weak_with_strong = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "opaque_coverage_choice": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["opaque_coverage_choice"]

    hard = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bare_prop_choice": "Classical.choose from a Prop-only field",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == ["bare_prop_choice"]

    exact_false = run_typed_appearance_coverage_choice_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "coverage_packet": "missing because stronger packet is pending",
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
        description="Validate a typed-appearance coverage-choice receipt."
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
    result = run_typed_appearance_coverage_choice_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
