import json
from pathlib import Path

from ztare.orchestrator.control_followup_policy import (
    CONTROL_FOLLOWUP_SCHEMA,
    evaluate_control_followup,
    latest_prior_control,
    read_control_events,
    record_control_followup_decision,
)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def test_followup_blocks_repeated_non_emergency_pivot(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _append_jsonl(
        workspace / "loop_events.jsonl",
        {
            "event_type": "topological_pivot_profile_injected",
            "iteration_index": 4,
        },
    )

    decision = evaluate_control_followup(
        workspace,
        current_iteration=5,
        rubric_data={},
        candidate_control_kind="stagnation_pivot",
    )

    assert decision.schema_version == CONTROL_FOLLOWUP_SCHEMA
    assert decision.allowed is False
    assert decision.decision == "observe_prior_control_followup"
    assert decision.prior_control_kind == "topological_pivot_profile_injected"
    assert decision.prior_control_iteration == 4
    assert decision.remaining_followup_iterations == 3
    assert "observe 3 more" in decision.reason


def test_followup_allows_after_window_is_observed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _append_jsonl(
        workspace / "loop_events.jsonl",
        {
            "event_type": "topological_pivot_profile_injected",
            "iteration_index": 4,
        },
    )

    decision = evaluate_control_followup(
        workspace,
        current_iteration=8,
        rubric_data={},
        candidate_control_kind="stagnation_pivot",
    )

    assert decision.allowed is True
    assert decision.decision == "allow_followup_window_observed"
    assert "4 iterations elapsed" in decision.reason


def test_followup_reads_blitz_events_as_controls(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _append_jsonl(
        workspace / "parallel_blitz_log.jsonl",
        {
            "iter": 2,
            "k": 3,
            "decision_reason": "stagnation_count=2 >= 1",
        },
    )

    prior = latest_prior_control(workspace, current_iteration=3)
    decision = evaluate_control_followup(
        workspace,
        current_iteration=3,
        rubric_data={"control_followup_window": 2},
        candidate_control_kind="parallel_blitz",
    )

    assert prior is not None
    assert prior.control_kind == "parallel_blitz"
    assert decision.allowed is False
    assert decision.prior_control_kind == "parallel_blitz"
    assert decision.remaining_followup_iterations == 2


def test_followup_emergency_and_disabled_modes_allow(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _append_jsonl(
        workspace / "loop_events.jsonl",
        {"event_type": "topological_pivot_profile_injected", "iteration_index": 7},
    )

    emergency = evaluate_control_followup(
        workspace,
        current_iteration=8,
        rubric_data={},
        candidate_control_kind="emergency_pivot",
        emergency=True,
    )
    disabled = evaluate_control_followup(
        workspace,
        current_iteration=8,
        rubric_data={"control_followup_window": 0},
        candidate_control_kind="stagnation_pivot",
    )

    assert emergency.allowed is True
    assert emergency.decision == "allow_emergency_or_bounded_override"
    assert disabled.allowed is True
    assert disabled.decision == "allow_disabled"


def test_record_control_followup_decision_writes_jsonl(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    decision = evaluate_control_followup(
        workspace,
        current_iteration=1,
        rubric_data={},
        candidate_control_kind="parallel_blitz",
    )

    record_control_followup_decision(
        workspace,
        decision,
        run_id="run-1",
        project="demo",
        iteration_index=1,
    )

    rows = read_control_events(workspace)
    payload = json.loads((workspace / "control_followup_policy.jsonl").read_text())
    assert rows == []
    assert payload["record_type"] == "control_followup_policy_decision"
    assert payload["run_id"] == "run-1"
    assert payload["project"] == "demo"
    assert payload["iteration_index"] == 1
    assert payload["candidate_control_kind"] == "parallel_blitz"
