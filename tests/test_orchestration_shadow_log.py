from src.ztare.research_director.orchestration_shadow_log import (
    append_shadow_event,
    new_shadow_event,
    validate_shadow_event,
)


def valid_event(**overrides):
    event = new_shadow_event(
        shadow_event_id="evt-1",
        substrate="ns_millennium_hunt",
        source_trace_ref="repo:payload/source.md",
        decision_context_id="tick-1",
        pre_decision_state_ref="tick-1:pre",
        candidate_action="open_shadow_log",
        proposed_known_residual_class="production_shadow_missing",
        selected_residual_edge="offline benchmark -> production shadow evidence",
        rejected_nearest_confuser_edge="offline benchmark -> production reliability",
        source_cue_check_status="pass",
        accepted_residual_class="production_shadow_missing",
        outside_menu_flag="false",
        specific_outside_residual_class="none",
        action_program=["open_shadow_log", "stop_or_repair"],
        required_next_action="open_shadow_log",
        program_counter_rule="execute action_program[current_action_index]",
        program_invariant_passed="pass",
    )
    event.update(overrides)
    return event


def test_shadow_event_valid_pending():
    result = validate_shadow_event(valid_event())
    assert result["passed"] is True


def test_shadow_event_requires_core_fields():
    event = valid_event(candidate_action="")
    result = validate_shadow_event(event)
    assert result["passed"] is False
    assert {item["type"] for item in result["violations"]} == {"missing_required_field"}


def test_shadow_event_resolved_requires_outcome_fields():
    result = validate_shadow_event(valid_event(later_outcome_status="resolved"))
    assert result["passed"] is False
    assert "resolved_event_missing_outcome_field" in {item["type"] for item in result["violations"]}


def test_shadow_event_valid_resolved():
    event = valid_event(
        later_outcome_status="resolved",
        executed_action="open_shadow_log",
        final_disposition="stopped_pending_shadow_rows",
        later_outcome_ref="repo:outcomes/evt-1.json",
        later_outcome_label="no_policy_change_until_shadow_matures",
        outcome_observed_at="2026-05-24T00:00:00Z",
        cost_or_regret_signal="avoided_premature_rollout_claim",
    )
    assert validate_shadow_event(event)["passed"] is True


def test_append_shadow_event_writes_jsonl(tmp_path):
    out = tmp_path / "shadow.jsonl"
    result = append_shadow_event(valid_event(), out)
    assert result["passed"] is True
    assert out.read_text().count("shadow_event_id") == 1
