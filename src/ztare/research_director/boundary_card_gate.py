"""Deterministic validation for claim-boundary / anti-pattern cards.

Boundary cards are compiler IR for paid/unpaid research updates: they separate
what evidence pays from what remains blocked, then lower that state into an
action program. This gate checks the card shape and action-program invariants;
it does not decide whether the underlying domain claim is true.
"""
from __future__ import annotations

from typing import Any

BOUNDARY_FIRST_ACTION = {
    "unpaid_receipt": "request_missing_receipt",
    "paid_narrow_boundary": "mark_paid_narrow_boundary",
    "paid_narrow_boundary_with_unpaid_mechanism": "mark_paid_narrow_boundary",
    "paid_negative_boundary": "downgrade_or_block_claim",
}

BOUNDARY_TERMINAL_ACTION = {
    "unpaid_receipt": "stop_or_repair",
    "paid_narrow_boundary": "proceed_narrow",
    "paid_narrow_boundary_with_unpaid_mechanism": "proceed_narrow",
    "paid_negative_boundary": "mark_paid_negative_boundary",
}

REQUIRED_FIELDS = (
    "boundary_state",
    "paid_receipt",
    "unpaid_receipt",
    "permitted_update",
    "blocked_update",
    "false_reading_confuser",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _words(value: Any) -> set[str]:
    return {
        word
        for word in str(value or "").lower().replace("_", " ").replace("-", " ").split()
        if len(word) > 3
    }


def _program(card: dict[str, Any]) -> list[str]:
    program = card.get("action_program") or card.get("boundary_card_action_program") or []
    if isinstance(program, str):
        return [_norm(part) for part in program.split(",") if part.strip()]
    if isinstance(program, list):
        return [_norm(item) for item in program]
    return []


def validate_boundary_card(
    card: dict[str, Any],
    *,
    source_facts: str | None = None,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected = expected or {}
    state = _norm(card.get("boundary_state"))
    program = _program(card)
    required_next = _norm(card.get("required_next_action") or card.get("boundary_card_required_next_action") or (program[0] if program else ""))
    violations: list[dict[str, Any]] = []

    for field in REQUIRED_FIELDS:
        if not str(card.get(field) or "").strip():
            violations.append({"type": "missing_boundary_card_field", "field": field})

    first = BOUNDARY_FIRST_ACTION.get(state)
    terminal = BOUNDARY_TERMINAL_ACTION.get(state)
    if state not in BOUNDARY_FIRST_ACTION:
        violations.append({"type": "unknown_boundary_state", "value": state})
    if first and required_next and required_next != first:
        violations.append({
            "type": "boundary_first_action_mismatch",
            "boundary_state": state,
            "expected_first_action": first,
            "required_next_action": required_next,
        })
    if program:
        if first and program[0] != first:
            violations.append({
                "type": "boundary_program_first_action_mismatch",
                "expected_first_action": first,
                "program_first_action": program[0],
            })
        if terminal and len(program) > 1 and program[-1] != terminal:
            violations.append({
                "type": "boundary_terminal_action_mismatch",
                "expected_terminal_action": terminal,
                "program_terminal_action": program[-1],
            })

    paid = str(card.get("paid_receipt") or "").strip()
    unpaid = str(card.get("unpaid_receipt") or "").strip()
    permitted = str(card.get("permitted_update") or "").strip()
    blocked = str(card.get("blocked_update") or "").strip()
    if state == "unpaid_receipt" and (not unpaid or not blocked):
        violations.append({"type": "unpaid_boundary_missing_unpaid_or_blocked_receipt"})
    if state.startswith("paid_") and (not paid or not permitted):
        violations.append({"type": "paid_boundary_missing_paid_or_permitted_receipt"})
    if state in {"paid_narrow_boundary", "paid_narrow_boundary_with_unpaid_mechanism"} and not blocked:
        violations.append({"type": "paid_boundary_missing_blocked_broad_claim"})

    if source_facts:
        source_words = _words(source_facts)
        for field in ("paid_receipt", "unpaid_receipt"):
            value_words = _words(card.get(field))
            if value_words and not value_words.intersection(source_words):
                violations.append({
                    "type": "boundary_field_not_source_anchored",
                    "field": field,
                })

    expected_state = _norm(expected.get("boundary_state"))
    expected_first = _norm(expected.get("required_next_action") or expected.get("first_action"))
    expected_terminal = _norm(expected.get("terminal_action"))
    if expected_state and state != expected_state:
        violations.append({
            "type": "expected_boundary_state_mismatch",
            "expected": expected_state,
            "actual": state,
        })
    if expected_first and required_next != expected_first:
        violations.append({
            "type": "expected_first_action_mismatch",
            "expected": expected_first,
            "actual": required_next,
        })
    if expected_terminal and program and program[-1] != expected_terminal:
        violations.append({
            "type": "expected_terminal_action_mismatch",
            "expected": expected_terminal,
            "actual": program[-1],
        })

    return {
        "passed": not violations,
        "boundary_state": state,
        "required_next_action": required_next,
        "action_program": program,
        "violations": violations,
    }


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

    parser = argparse.ArgumentParser(description="Validate a boundary-card contract.")
    parser.add_argument("card_json", help="Path to card JSON, or - for stdin")
    parser.add_argument("--source-facts", default="")
    parser.add_argument("--source-facts-file")
    parser.add_argument("--expected-json")
    args = parser.parse_args(argv)

    source_facts = args.source_facts
    if args.source_facts_file:
        with open(args.source_facts_file, encoding="utf-8") as f:
            source_facts = f.read()
    expected = _read_json(args.expected_json) if args.expected_json else None
    result = validate_boundary_card(
        _read_json(args.card_json),
        source_facts=source_facts or None,
        expected=expected,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
