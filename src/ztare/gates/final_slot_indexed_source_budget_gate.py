"""G-FINAL-SLOT-INDEXED-SOURCE-BUDGET.

General-purpose receipt gate for the canonical source-budget move where the
source prefix is the first `finalSlot` entries of a fixed event stream and the
source-to-budget map is the identity on that finite prefix.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-FINAL-SLOT-INDEXED-SOURCE-BUDGET"

REQUIRED_FIELDS = (
    "source_prefix_family",
    "source_prefix_definition",
    "event_stream",
    "final_slot_index",
    "source_count",
    "budget_count",
    "source_slot_map",
    "identity_on_final_slot_prefix",
    "map_total_on_indexed_prefix",
    "source_slot_injective",
    "event_data_binding",
    "same_tree_lock_binding",
    "displayed_fanout_or_no_log_reuse",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_slot_truncation",
    "no_rebilling_same_source_atom",
    "no_endpoint_capacity_restatement",
    "remaining_target_assignment_obligation",
    "nearest_confuser",
    "confuser_distinction",
)

WEAK_SUBSTITUTES = (
    "arbitrary_source_prefix_socket",
    "bounded_fanout_label_only",
    "event_stream_label_only",
    "endpoint_capacity_label",
    "target_defined_prefix",
    "post_payoff_prefix_choice",
)

HARD_VIOLATIONS = (
    "source_prefix_chosen_from_target_deficit",
    "posthoc_slot_selection",
    "endpoint_capacity_restatement",
    "same_source_atom_reused",
    "carrier_detached_from_event_data",
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


def run_final_slot_indexed_source_budget_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a final-slot-indexed source-budget receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "final_slot_indexed_source_budget_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "numeric_check": None,
            "summary": "malformed final-slot-indexed source-budget receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "final_slot_indexed_source_budget_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "final-slot-indexed source budgets need the prefix definition, "
                "eventData binding, identity map, injectivity, timing, "
                "single-spend, anti-target-selection, and remaining target "
                "assignment obligation"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "final_slot_indexed_source_budget_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "an arbitrary source-prefix socket, fanout label, or event "
                "stream label does not establish the canonical identity "
                "source-slot map"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "final_slot_indexed_source_budget_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the source prefix is target-defined, posthoc, endpoint "
                "restated, carrier-detached, or rebills a source atom"
            ),
        })

    numeric_check = None
    try:
        source_value = _fraction_or_none(receipt.get("source_count_value"))
        budget_value = _fraction_or_none(receipt.get("budget_count_value"))
    except Exception as exc:
        violations.append({
            "type": "final_slot_indexed_source_budget_numeric_parse_error",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": str(exc),
        })
        source_value = budget_value = None
    if source_value is not None and budget_value is not None:
        equal_to_budget = source_value == budget_value
        source_le_budget = source_value <= budget_value
        numeric_check = {
            "source_count_value": str(source_value),
            "budget_count_value": str(budget_value),
            "source_equals_budget": equal_to_budget,
            "source_le_budget": source_le_budget,
        }
        if not (equal_to_budget and source_le_budget):
            violations.append({
                "type": "final_slot_indexed_source_budget_numeric_check_failed",
                "severity": "blocking" if enforce_block else "advisory",
                "numeric_check": numeric_check,
            })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present and (
        numeric_check is None
        or (
            numeric_check["source_equals_budget"]
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
            "complete final-slot-indexed source-budget receipt"
            if complete else
            "incomplete final-slot-indexed source-budget receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_final_slot_indexed_source_budget_gate({
        "source_prefix_family": "same-tree events",
        "event_stream_label_only": "eventData",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "final_slot_indexed_source_budget_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_final_slot_indexed_source_budget_gate({
        "source_prefix_family": "same-tree eventData events",
        "source_prefix_definition": "sourcePrefixCount n = n",
        "event_stream": "FreshFrequencyEventSameTreeLock.eventData",
        "final_slot_index": "supportLength - 1",
        "source_count": "sourcePrefixCount finalSlot",
        "budget_count": "finalSlot",
        "source_slot_map": "fun j => j",
        "identity_on_final_slot_prefix": "Fin finalSlot identity",
        "map_total_on_indexed_prefix": "domain is the full Fin finalSlot prefix",
        "source_slot_injective": "identity function is injective",
        "event_data_binding": "sourceEventAt j = sameTreeLock.eventData j.val",
        "same_tree_lock_binding": "same sameTreeLock",
        "displayed_fanout_or_no_log_reuse": "displayed bounded fanout guard",
        "fixed_before_payoff": "event stream and final-slot prefix fixed",
        "not_target_defined": "not selected from target deficit",
        "no_post_payoff_slot_truncation": "no posthoc truncation",
        "no_rebilling_same_source_atom": "identity maps each atom once",
        "no_endpoint_capacity_restatement": "constructs identity map",
        "remaining_target_assignment_obligation": "target jumps must inject here",
        "nearest_confuser": "arbitrary source-prefix socket",
        "confuser_distinction": "sourcePrefixCount is fixed to n",
        "source_count_value": 3,
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

    parser = argparse.ArgumentParser(
        description="Validate a final-slot-indexed source-budget receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_final_slot_indexed_source_budget_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
