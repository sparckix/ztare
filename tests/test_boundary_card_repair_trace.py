from src.ztare.research_director.boundary_card_repair_trace import (
    append_repair_trace,
    new_repair_trace,
    validate_repair_trace,
)


def base_trace(**overrides):
    trace = new_repair_trace(
        trace_id="trace-1",
        substrate="epistemic_generation",
        source_ref="repo:source.md",
        source_observation="The source pays a narrow use but blocks the broad claim.",
        rejected_card={"boundary_state": "unpaid_receipt"},
        pre_repair_gate_result={"passed": False, "violations": [{"type": "boundary_first_action_mismatch"}]},
        rejection_basis="non_oracle_gate_rejection",
        repair_prompt="Repair using only source and gate violations.",
        raw_repair_output='{"boundary_state":"paid_narrow_boundary"}',
        repaired_card={"boundary_state": "paid_narrow_boundary"},
        post_repair_gate_result={"passed": True, "violations": []},
    )
    trace.update(overrides)
    return trace


def test_pending_repair_trace_valid():
    assert validate_repair_trace(base_trace())["passed"] is True


def test_rejects_pre_gate_passed_when_basis_is_non_oracle_gate():
    result = validate_repair_trace(base_trace(pre_repair_gate_result={"passed": True}))
    assert result["passed"] is False
    assert "non_oracle_rejection_basis_but_pre_gate_passed" in {v["type"] for v in result["violations"]}


def test_allows_scoring_rejection_with_visible_gate_pass():
    result = validate_repair_trace(base_trace(
        rejection_basis="scoring_rejection",
        pre_repair_gate_result={"passed": True, "violations": []},
    ))
    assert result["passed"] is True


def test_rejects_post_gate_failure():
    result = validate_repair_trace(base_trace(post_repair_gate_result={"passed": False}))
    assert result["passed"] is False
    assert "post_repair_gate_did_not_pass" in {v["type"] for v in result["violations"]}


def test_scored_trace_requires_downstream_fields():
    result = validate_repair_trace(base_trace(downstream_status="scored"))
    assert result["passed"] is False
    assert "scored_trace_missing_downstream_field" in {v["type"] for v in result["violations"]}


def test_scored_trace_valid():
    trace = base_trace(
        downstream_status="scored",
        executed_action="mark_paid_narrow_boundary",
        terminal_action="proceed_narrow",
        false_proceed=False,
        false_stop=False,
        paid_boundary_overwork=False,
        episode_cost=1,
        downstream_score_ref="repo:score.json",
    )
    assert validate_repair_trace(trace)["passed"] is True


def test_append_repair_trace_writes_jsonl(tmp_path):
    out = tmp_path / "repair_trace.jsonl"
    result = append_repair_trace(base_trace(), out)
    assert result["passed"] is True
    assert out.read_text().count("trace_id") == 1
