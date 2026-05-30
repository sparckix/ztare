"""G-COVERAGE-CHOICE-FINITE-SELECTOR.

Receipt gate for turning event-prefix coverage into a finite selected-index
selector via an explicit sigma witness, rather than carrying an opaque selected
index through the source ladder.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-COVERAGE-CHOICE-FINITE-SELECTOR"

REQUIRED_FIELDS = (
    "target_family",
    "coverage_packet",
    "coverage_choice_witness",
    "selected_index_definition",
    "selected_index_codomain",
    "target_node_selected_bad_membership",
    "choice_from_appearance_field",
    "choice_uses_target_membership",
    "event_to_badnode_target_equality",
    "displayed_incidence_refinement",
    "selected_index_incidence_transport",
    "same_tree_binding",
    "event_node_identification_binding",
    "event_prefixes_exhaust_selected_bad_nodes",
    "every_selected_bad_node_appears_in_some_prefix",
    "prefix_dominates_finite_selected_bad_tree_beta_sum",
    "duplicate_events_charge_multiplicity",
    "no_shell_only_enumeration_shortcut",
    "no_adaptive_stopping_from_beta_sum",
    "coverage_choice_fixed_before_payoff",
    "not_classical_choice_from_bare_appearance",
    "not_endpoint_capacity_only",
    "not_post_payoff_selection",
    "downstream_event_prefix_coverage_selected_index_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "coverage_label_only",
    "appearance_label_only",
    "target_membership_label_only",
    "opaque_selected_index",
    "classical_choice_from_bare_appearance_label",
    "endpoint_capacity_label_only",
)

HARD_VIOLATIONS = (
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "choice_outside_final_slot",
    "target_node_not_selected_bad",
    "witness_not_event_to_badnode",
    "selected_index_not_incident",
    "endpoint_capacity_as_choice",
    "classical_choice_from_bare_appearance",
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


def run_coverage_choice_finite_selector_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a coverage-choice finite-selector receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "coverage_choice_finite_selector_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed coverage-choice finite-selector receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "coverage_choice_finite_selector_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "finite selector construction needs an explicit coverage-choice "
                "witness, target selected-bad membership, event-to-badnode "
                "equality, incidence transport, coverage anti-shortcut fields, "
                "and timing/anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "coverage_choice_finite_selector_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "labels for coverage, appearance, target membership, endpoint "
                "capacity, or opaque selected indices do not supply the finite "
                "sigma witness"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "coverage_choice_finite_selector_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the selector is posthoc, target-deficit driven, carrier "
                "drifting, outside the final slot, disconnected from "
                "eventToBadNode, nonincident, endpoint-only, bare-choice, "
                "adaptively stopped, or shell-only"
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
            "complete coverage-choice finite-selector receipt"
            if complete else
            "incomplete coverage-choice finite-selector receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_coverage_choice_finite_selector_gate({
        "target_family": "L3A target prefix",
        "coverage_label_only": "coverage packet exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["coverage_label_only"]

    weak_with_strong = run_coverage_choice_finite_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "target_membership_label_only": "recorded as confuser, not proof",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "target_membership_label_only"
    ]

    hard = run_coverage_choice_finite_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "witness_not_event_to_badnode": "choice witness is not the displayed map",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == ["witness_not_event_to_badnode"]

    exact_false = run_coverage_choice_finite_selector_gate({
        "target_family": "missing because target-family proof is pending",
    }, enforce_block=True)
    assert exact_false["passed"] is False
    assert "coverage_packet" in exact_false["missing_fields"]

    strong = run_coverage_choice_finite_selector_gate({
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
        description="Validate a coverage-choice finite-selector receipt."
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
    result = run_coverage_choice_finite_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
