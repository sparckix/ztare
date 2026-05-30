from src.ztare.research_director.boundary_card_gate import validate_boundary_card


def _paid_card():
    return {
        "boundary_state": "paid_narrow_boundary",
        "paid_receipt": "control mapping evidence",
        "unpaid_receipt": "deployment compliance proof",
        "permitted_update": "control mapping claim",
        "blocked_update": "compliance proof",
        "false_reading_confuser": "mapping treated as compliance proof",
        "action_program": ["mark_paid_narrow_boundary", "proceed_narrow"],
        "required_next_action": "mark_paid_narrow_boundary",
    }


def test_boundary_card_gate_passes_correct_paid_card():
    result = validate_boundary_card(
        _paid_card(),
        source_facts="The source gives control mapping evidence but no deployment compliance proof.",
    )

    assert result["passed"] is True


def test_boundary_card_gate_catches_wrong_first_action():
    card = _paid_card()
    card["action_program"] = ["proceed_narrow", "mark_paid_narrow_boundary"]
    card["required_next_action"] = "proceed_narrow"

    result = validate_boundary_card(card)

    assert result["passed"] is False
    assert "boundary_first_action_mismatch" in {
        item["type"] for item in result["violations"]
    }


def test_boundary_card_gate_catches_paid_card_missing_blocked_broad_claim():
    card = _paid_card()
    card["blocked_update"] = ""

    result = validate_boundary_card(card)

    assert result["passed"] is False
    violation_types = {item["type"] for item in result["violations"]}
    assert "missing_boundary_card_field" in violation_types
    assert "paid_boundary_missing_blocked_broad_claim" in violation_types


def test_boundary_card_gate_catches_expected_state_mismatch():
    card = _paid_card()
    card["boundary_state"] = "unpaid_receipt"

    result = validate_boundary_card(card, expected={"boundary_state": "paid_narrow_boundary"})

    assert result["passed"] is False
    assert "expected_boundary_state_mismatch" in {
        item["type"] for item in result["violations"]
    }
