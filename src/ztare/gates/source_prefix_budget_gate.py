"""G-SOURCE-PREFIX-BUDGET.

General-purpose receipt gate for proving that a selected source prefix fits
inside a fixed budget prefix.  This is narrower than G-PREFIX-COUNT-BRIDGE: it
does not pay a target prefix, only the source-budget leg.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-SOURCE-PREFIX-BUDGET"

REQUIRED_FIELDS = (
    "source_prefix_family",
    "budget_family",
    "source_count",
    "budget_count",
    "budget_index",
    "prefix_to_budget_map",
    "map_total_on_source_prefix",
    "pointwise_budget_assignment",
    "source_count_le_budget",
    "fixed_before_payoff",
    "same_owner_or_source",
    "bounded_fanout_or_multiplicity",
    "no_logarithmic_reuse",
    "no_rebilling_same_source_atom",
    "not_target_defined",
    "no_post_payoff_selection",
    "no_endpoint_restatement",
    "nearest_confuser",
    "confuser_distinction",
)

WEAK_SUBSTITUTES = (
    "bounded_fanout_label",
    "no_log_reuse_label",
    "same_carrier_label",
    "finite_budget_label",
    "cardinality_label",
    "endpoint_bound_label",
    "target_count_bridge_label",
    "source_count_defined_as_budget",
    "prop_only_source_budget",
)

HARD_VIOLATIONS = (
    "posthoc_budget_selection",
    "target_deficit_selection",
    "same_source_atom_reused",
    "endpoint_restatement",
    "unbounded_multiplicity",
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


def _fraction_or_none(value: Any) -> Fraction | None:
    if value in (None, ""):
        return None
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(str(value).strip())


def run_source_prefix_budget_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a source-prefix budget receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "source_prefix_budget_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "numeric_check": None,
            "summary": "malformed source-prefix budget receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "source_prefix_budget_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "source-prefix budget needs source/budget families, a fixed "
                "prefix-to-budget map, bounded multiplicity, no-log-reuse, "
                "single-spend, timing, anti-target-selection, and confuser "
                "distinction"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "source_prefix_budget_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "bounded-fanout/no-log labels do not substitute for a "
                "prefix-level source budget map and single-spend receipt"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "source_prefix_budget_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the budget is selected after payoff, selected from the "
                "target deficit, reuses a source atom, restates the endpoint, "
                "or allows unbounded multiplicity"
            ),
        })

    numeric_check = None
    try:
        source_value = _fraction_or_none(receipt.get("source_count_value"))
        budget_value = _fraction_or_none(receipt.get("budget_count_value"))
    except Exception as exc:
        violations.append({
            "type": "source_prefix_budget_numeric_parse_error",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": str(exc),
        })
        source_value = budget_value = None
    if source_value is not None and budget_value is not None:
        source_le_budget = source_value <= budget_value
        numeric_check = {
            "source_count_value": str(source_value),
            "budget_count_value": str(budget_value),
            "source_le_budget": source_le_budget,
        }
        if not source_le_budget:
            violations.append({
                "type": "source_prefix_budget_numeric_check_failed",
                "severity": "blocking" if enforce_block else "advisory",
                "numeric_check": numeric_check,
            })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present and (
        numeric_check is None or numeric_check["source_le_budget"]
    )
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "numeric_check": numeric_check,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "complete source-prefix budget receipt"
            if complete else
            f"incomplete source-prefix budget receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_source_prefix_budget_gate({
        "source_prefix_family": "fresh events",
        "budget_family": "final slot",
        "bounded_fanout_label": "bounded fanout",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "source_prefix_budget_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_source_prefix_budget_gate({
        "source_prefix_family": "same-tree fresh events",
        "budget_family": "final slot index budget",
        "source_count": "sourcePrefixCount finalSlot",
        "budget_count": "finalSlot",
        "budget_index": "supportLength - 1",
        "prefix_to_budget_map": "source event j maps to budget slot j",
        "map_total_on_source_prefix": "all j < sourcePrefixCount finalSlot mapped",
        "pointwise_budget_assignment": "j.val witnesses the budget slot",
        "source_count_le_budget": "bounded fanout/no-log source budget",
        "fixed_before_payoff": "source prefix fixed before endpoint query",
        "same_owner_or_source": "same same-tree event source",
        "bounded_fanout_or_multiplicity": "bounded comparable-scale tent fanout",
        "no_logarithmic_reuse": "no same-scale logarithmic multiplicity",
        "no_rebilling_same_source_atom": "one event pays once",
        "not_target_defined": "not selected from target deficit",
        "no_post_payoff_selection": "no posthoc pruning",
        "no_endpoint_restatement": "does not assume final-slot upper bound",
        "nearest_confuser": "bounded-fanout label only",
        "confuser_distinction": "requires prefix map and numeric budget field",
        "source_count_value": 2,
        "budget_count_value": 3,
    })
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

    parser = argparse.ArgumentParser(description="Validate a source-prefix budget receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_source_prefix_budget_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
