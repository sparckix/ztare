"""G-FINITE-COFINAL-EVENT-SELECTOR.

Receipt gate for constructing a cofinal Nat selector from a selector already
valued in the final event-prefix codomain `Fin (supportLength - 1)`.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-FINITE-COFINAL-EVENT-SELECTOR"

REQUIRED_FIELDS = (
    "target_family",
    "ordinary_coverage_packet",
    "cofinal_selected_tree_incidence_receipt",
    "finite_cofinal_event_selector",
    "finite_selector_codomain",
    "finite_selector_event_to_badnode_equality",
    "strict_prefix_bound_from_fin_codomain",
    "finite_selector_refines_cofinal_incidence",
    "finite_selector_codomain_is_final_event_prefix",
    "finite_selector_uses_same_bad_center_event_nodes",
    "finite_selector_uses_event_to_badnode",
    "coverage_packet_forwards_exhaustion",
    "coverage_packet_forwards_prop_appearance",
    "coverage_packet_forwards_beta_domination",
    "coverage_packet_forwards_multiplicity",
    "coverage_packet_forwards_no_shell_only",
    "coverage_packet_forwards_no_adaptive_beta_sum",
    "finite_selector_fixed_before_payoff",
    "not_bare_prop_choice_for_finite_selector",
    "not_endpoint_capacity_only",
    "not_shell_only_enumeration",
    "not_post_payoff_selection",
    "downstream_cofinal_event_selector_final_prefix_bound_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "nat_selector_with_separate_bound_only",
    "explicit_subtype_witness_only",
    "classical_choice_witness_only",
    "event_cover_prop_only",
    "finite_codomain_label_only",
    "selector_without_equality",
    "endpoint_capacity_label_only",
    "shell_enumeration_label_only",
)

HARD_VIOLATIONS = (
    "bare_prop_choice_without_finite_selector",
    "classical_choice_without_finite_selector",
    "nat_selector_not_fin_valued",
    "post_payoff_choice",
    "target_deficit_choice",
    "carrier_drift",
    "missing_fin_codomain",
    "bound_not_from_fin_codomain",
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


def run_finite_cofinal_event_selector_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a finite cofinal event-selector receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "finite_cofinal_event_selector_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed finite cofinal event-selector receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "finite_cofinal_event_selector_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "finite selector construction needs a selector valued in "
                "Fin (supportLength - 1), its eventToBadNode equality, "
                "cofinal incidence, coverage forwarding, timing, and anti-shortcut checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "finite_cofinal_event_selector_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "Nat selectors with separate bounds, subtype witnesses, "
                "Classical-choice wrappers, Prop cover labels, finite-codomain "
                "labels, selectors without equality, endpoint capacity, or shell "
                "labels do not construct the finite selector source"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "finite_cofinal_event_selector_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the selector is bare-choice, Classical-only, not Fin-valued, "
                "posthoc, target-deficit driven, carrier drifting, missing "
                "the final-prefix codomain, bounded outside the codomain, not "
                "eventToBadNode based, endpoint-only, adaptive, or shell-only"
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
            "complete finite cofinal event-selector receipt"
            if complete else
            "incomplete finite cofinal event-selector receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_finite_cofinal_event_selector_gate({
        "target_family": "selected bad nodes",
        "nat_selector_with_separate_bound_only": "Nat selector plus bound",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == [
        "nat_selector_with_separate_bound_only"
    ]

    weak_with_strong = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "explicit_subtype_witness_only": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "explicit_subtype_witness_only"
    ]

    hard = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "nat_selector_not_fin_valued": "Nat only",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == ["nat_selector_not_fin_valued"]

    exact_false = run_finite_cofinal_event_selector_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "finite_cofinal_event_selector":
            "missing because finite selector theorem is pending",
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
        description="Validate a finite cofinal event-selector receipt."
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
    result = run_finite_cofinal_event_selector_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
