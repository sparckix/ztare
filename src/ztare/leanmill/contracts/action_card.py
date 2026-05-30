"""Reusable LeanMill action-card contracts.

The epistemic-generation research log repeatedly found that labels and broad
warnings are weak carriers. The useful worker surface is a compact card with a
failure family, preventive receipt, source-specific confuser, clean proceed
condition, feedback trace, and an executable action program.

This module is LeanMill-local on purpose. RD pattern contracts are broader tick
machinery; LeanMill uses the same contract shape without importing RD state.
"""
from __future__ import annotations

from typing import Any

ACTION_CARD_SCHEMA = "leanmill-action-card-v1"

REQUIRED_ACTION_CARD_FIELDS = (
    "schema",
    "card_type",
    "failure_family",
    "preventive_gate",
    "missing_or_paid_preventive_receipt",
    "source_specific_false_reading_confuser",
    "nearest_confuser_rejection",
    "clean_proceed_condition",
    "intervention_feedback_trace",
    "action_program",
    "current_action_index",
    "required_next_action",
    "program_counter_rule",
)


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _parse_int(value: Any) -> tuple[bool, int]:
    try:
        return True, int(value)
    except (TypeError, ValueError):
        return False, 0


def build_action_card(
    *,
    card_type: str,
    failure_family: str,
    preventive_gate: str,
    missing_or_paid_preventive_receipt: str,
    source_specific_false_reading_confuser: list[str],
    nearest_confuser_rejection: list[str],
    clean_proceed_condition: str,
    action_program: list[str],
    program_counter_rule: str,
    intervention_feedback_trace: list[dict[str, Any]] | None = None,
    evidence_basis: str = "",
) -> dict[str, Any]:
    """Build a compact action card for a LeanMill worker lane."""
    required_next = action_program[0] if action_program else ""
    return {
        "schema": ACTION_CARD_SCHEMA,
        "card_type": str(card_type),
        "failure_family": str(failure_family),
        "preventive_gate": str(preventive_gate),
        "missing_or_paid_preventive_receipt": str(missing_or_paid_preventive_receipt),
        "source_specific_false_reading_confuser": list(source_specific_false_reading_confuser),
        "nearest_confuser_rejection": list(nearest_confuser_rejection),
        "clean_proceed_condition": str(clean_proceed_condition),
        "intervention_feedback_trace": list(intervention_feedback_trace or []),
        "action_program": list(action_program),
        "current_action_index": 0,
        "required_next_action": required_next,
        "program_counter_rule": str(program_counter_rule),
        "evidence_basis": str(evidence_basis),
    }


def validate_action_card(
    card: dict[str, Any],
    *,
    expected_card_type: str | None = None,
    expected_action_program: list[str] | None = None,
) -> dict[str, Any]:
    """Validate action-card shape and program-counter invariants.

    This is a contract/IR gate. It does not decide mathematical truth.
    """
    failures: list[dict[str, Any]] = []
    if not isinstance(card, dict):
        return {
            "schema": "leanmill-action-card-validation-v1",
            "status": "fail",
            "failure_count": 1,
            "failures": [{"failure": "missing_action_card"}],
        }
    if card.get("schema") != ACTION_CARD_SCHEMA:
        failures.append({"failure": "invalid_action_card_schema", "schema": card.get("schema")})
    for field in REQUIRED_ACTION_CARD_FIELDS:
        if field == "intervention_feedback_trace":
            if not isinstance(card.get(field), list):
                failures.append({"failure": "action_card_trace_not_list"})
        elif not _nonempty(card.get(field)):
            failures.append({"failure": f"action_card_missing_{field}"})
    if expected_card_type is not None and str(card.get("card_type") or "") != str(expected_card_type):
        failures.append({
            "failure": "action_card_type_mismatch",
            "expected_card_type": expected_card_type,
            "actual_card_type": card.get("card_type"),
        })
    program = card.get("action_program")
    if expected_action_program is not None and program != expected_action_program:
        failures.append({
            "failure": "action_card_action_program_mismatch",
            "expected_action_program": expected_action_program,
            "actual_action_program": program,
        })
    program_list = program if isinstance(program, list) else []
    required_next = card.get("required_next_action")
    if program_list and required_next != program_list[0]:
        failures.append({
            "failure": "action_card_required_next_action_mismatch",
            "expected_required_next_action": program_list[0],
            "actual_required_next_action": required_next,
        })
    current_ok, current_idx = _parse_int(card.get("current_action_index"))
    if not current_ok or current_idx != 0:
        failures.append({
            "failure": "action_card_current_action_index_mismatch",
            "current_action_index": card.get("current_action_index"),
        })
    return {
        "schema": "leanmill-action-card-validation-v1",
        "status": "pass" if not failures else "fail",
        "failure_count": len(failures),
        "failures": failures,
    }


def _self_test() -> int:
    program = ["inspect", "act"]
    card = build_action_card(
        card_type="test_card",
        failure_family="test_failure",
        preventive_gate="test_gate",
        missing_or_paid_preventive_receipt="test_receipt",
        source_specific_false_reading_confuser=["confuser"],
        nearest_confuser_rejection=["reject"],
        clean_proceed_condition="clean condition",
        action_program=program,
        program_counter_rule="execute in order",
    )
    ok = validate_action_card(card, expected_card_type="test_card", expected_action_program=program)
    assert ok["status"] == "pass", ok
    bad = dict(card)
    bad.pop("clean_proceed_condition")
    failed = validate_action_card(bad, expected_card_type="test_card", expected_action_program=program)
    assert failed["status"] == "fail", failed
    print("leanmill action_card self-test PASS")
    return 0


__all__ = [
    "ACTION_CARD_SCHEMA",
    "REQUIRED_ACTION_CARD_FIELDS",
    "build_action_card",
    "validate_action_card",
]


if __name__ == "__main__":
    raise SystemExit(_self_test())
