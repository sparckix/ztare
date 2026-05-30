"""G-PREFIX-COUNT-BRIDGE.

General-purpose receipt gate for converting a source-side finite prefix into a
target-side count bound.  It forces the caller to provide the prefix map,
assignment/injection, source budget, timing, no-rebilling, and anti-restatement
receipts before a count comparison can be consumed.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-PREFIX-COUNT-BRIDGE"

REQUIRED_FIELDS = (
    "target_prefix_family",
    "source_prefix_family",
    "target_count",
    "source_count",
    "source_budget",
    "prefix_index_map",
    "map_total_on_target_prefix",
    "pointwise_assignment_or_injection",
    "target_count_le_source_count",
    "source_count_le_budget",
    "target_count_le_budget_conclusion",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_selection",
    "no_rebilling_same_source_atom",
    "no_endpoint_restatement",
    "nearest_confuser",
    "confuser_distinction",
)

WEAK_SUBSTITUTES = (
    "same_label",
    "cardinality_label",
    "packing_label",
    "bounded_overlap_label",
    "carleson_label",
    "selected_event_label",
    "endpoint_bound_label",
    "same_tree_label_only",
    "source_count_defined_as_target_count",
)

HARD_VIOLATIONS = (
    "posthoc_mapping",
    "target_deficit_selection",
    "same_atom_reused_across_targets",
    "endpoint_restatement",
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


def run_prefix_count_bridge_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a finite-prefix count-bridge receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "prefix_count_bridge_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "numeric_check": None,
            "summary": "malformed prefix-count bridge receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "prefix_count_bridge_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "prefix-count bridge needs target/source families, counts, "
                "prefix map, assignment/injection, source budget, timing, "
                "no-rebilling, anti-restatement, and confuser distinction"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "prefix_count_bridge_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "labels, endpoint bounds, or same-tree vocabulary do not "
                "substitute for a target-to-source prefix assignment"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "prefix_count_bridge_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the bridge maps after payoff, selects by the target deficit, "
                "reuses source atoms, or restates the endpoint"
            ),
        })

    numeric_check = None
    try:
        target_value = _fraction_or_none(receipt.get("target_count_value"))
        source_value = _fraction_or_none(receipt.get("source_count_value"))
        budget_value = _fraction_or_none(receipt.get("source_budget_value"))
    except Exception as exc:
        violations.append({
            "type": "prefix_count_bridge_numeric_parse_error",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": str(exc),
        })
        target_value = source_value = budget_value = None
    if target_value is not None and source_value is not None and budget_value is not None:
        target_le_source = target_value <= source_value
        source_le_budget = source_value <= budget_value
        numeric_check = {
            "target_count_value": str(target_value),
            "source_count_value": str(source_value),
            "source_budget_value": str(budget_value),
            "target_le_source": target_le_source,
            "source_le_budget": source_le_budget,
            "target_le_budget": target_value <= budget_value,
        }
        if not (target_le_source and source_le_budget):
            violations.append({
                "type": "prefix_count_bridge_numeric_check_failed",
                "severity": "blocking" if enforce_block else "advisory",
                "numeric_check": numeric_check,
            })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present and (
        numeric_check is None
        or (
            numeric_check["target_le_source"]
            and numeric_check["source_le_budget"]
        )
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
            "complete prefix-count bridge receipt"
            if complete else
            f"incomplete prefix-count bridge receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_prefix_count_bridge_gate({
        "target_prefix_family": "supportIndex jumps",
        "source_prefix_family": "fresh events",
        "same_tree_label_only": "same tree",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "prefix_count_bridge_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_prefix_count_bridge_gate({
        "target_prefix_family": "supportIndex jumps",
        "source_prefix_family": "fresh events",
        "target_count": "supportIndex finalSlot - baseIndex",
        "source_count": "freshPrefixCount finalSlot",
        "source_budget": "finalSlot",
        "prefix_index_map": "jump n maps to event n",
        "map_total_on_target_prefix": "all jumps n < finalSlot mapped",
        "pointwise_assignment_or_injection": "injective up to paid fanout M",
        "target_count_le_source_count": "prefix domination",
        "source_count_le_budget": "bounded fanout/no-reuse",
        "target_count_le_budget_conclusion": "target jumps <= finalSlot",
        "fixed_before_payoff": "map fixed before endpoint query",
        "not_target_defined": "source events not selected from deficit",
        "no_post_payoff_selection": "no posthoc pruning",
        "no_rebilling_same_source_atom": "one event pays once",
        "no_endpoint_restatement": "does not assume final-slot bound",
        "nearest_confuser": "same-tree label only",
        "confuser_distinction": "requires assignment and no-rebilling",
        "target_count_value": 2,
        "source_count_value": 2,
        "source_budget_value": 3,
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

    parser = argparse.ArgumentParser(description="Validate a prefix-count bridge receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    args = parser.parse_args(argv)
    result = run_prefix_count_bridge_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
