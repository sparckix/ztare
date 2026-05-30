from src.ztare.research_director.orchestration_contract_gate import (
    validate_orchestration_contract,
)


def test_orchestration_gate_passes_correct_compact_contract():
    result = validate_orchestration_contract({
        "accepted_residual_class": "missing_source_holdout",
        "required_next_action": "collect_source_evidence",
        "action_program": ["collect_source_evidence", "stop_or_repair"],
        "deterministic_lowering_result": "missing_source_holdout -> collect_source_evidence",
        "source_cue_receipts": ["no held-out sample"],
    }, source_facts="There is no held-out district sample.")

    assert result["passed"] is True


def test_orchestration_gate_catches_wrong_program_order():
    result = validate_orchestration_contract({
        "accepted_residual_class": "production_shadow_missing",
        "required_next_action": "stop_or_repair",
        "action_program": ["stop_or_repair", "open_shadow_log"],
        "deterministic_lowering_result": "production_shadow_missing -> stop_or_repair",
    })

    assert result["passed"] is False
    violation_types = {item["type"] for item in result["violations"]}
    assert "deterministic_lowering_action_mismatch" in violation_types


def test_orchestration_gate_catches_missing_outside_handoff():
    result = validate_orchestration_contract({
        "accepted_residual_class": "outside_menu",
        "required_next_action": "defer_to_new_residual_class",
        "action_program": ["defer_to_new_residual_class", "stop_or_repair"],
        "deterministic_lowering_result": "outside_menu -> defer_to_new_residual_class",
    })

    assert result["passed"] is False
    assert "missing_specific_outside_residual_class" in {
        item["type"] for item in result["violations"]
    }


def test_orchestration_gate_catches_paid_scope_overblock():
    result = validate_orchestration_contract({
        "accepted_residual_class": "paid_narrow_boundary",
        "required_next_action": "proceed",
        "action_program": ["proceed"],
        "deterministic_lowering_result": "paid_narrow_boundary -> proceed",
        "stop_condition": "stop all publication until legal opinion",
    })

    assert result["passed"] is False
    assert "stop_condition_overblocks_paid_scope" in {
        item["type"] for item in result["violations"]
    }


def test_orchestration_gate_catches_wrong_source_cue():
    result = validate_orchestration_contract({
        "accepted_residual_class": "paid_narrow_boundary",
        "required_next_action": "proceed",
        "action_program": ["proceed"],
        "source_cue_receipts": ["outside lab reproduced result"],
    }, source_facts="One in-house lab run exists; no outside lab report exists.")

    assert result["passed"] is False
    assert "source_cue_not_anchored" in {
        item["type"] for item in result["violations"]
    }
