from __future__ import annotations

import json
from pathlib import Path

from src.ztare.reports.hill_climb_behavior_audit import (
    audit_workspace,
    build_hill_climb_behavior_audit,
    render_text,
)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def test_flags_stagnant_workspace_without_escape_evidence(tmp_path):
    workspace = tmp_path / "projects" / "stuck_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 3,
            "stagnation_count": 3,
            "loop_control_action": "normal",
            "pending_loop_action": "REFRESH_SPECIALISTS",
            "information_yield_rationale": "Information yield is low.",
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "control_due_without_breadth_evidence"
    assert row.max_stagnation_count == 3
    assert row.effective_pivot_threshold == 2
    assert row.escape_signal_count == 0
    assert row.active_control_signal_count == 0
    assert row.mechanism_status_counts == {"active": 0, "advisory": 0, "diagnostic": 0}
    assert row.latest_information_yield_rationale == "Information yield is low."


def test_reaching_threshold_at_final_row_is_not_a_missed_control_boundary(tmp_path):
    workspace = tmp_path / "projects" / "boundary_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 2,
            "stagnation_count": 2,
            "loop_control_action": "normal",
            "pending_loop_action": "REFRESH_SPECIALISTS",
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "stagnation_reached_no_next_control_boundary"
    assert row.pending_refresh_count == 1
    assert row.escape_signal_count == 0


def test_rubric_threshold_prevents_false_positive(tmp_path):
    rubric_dir = tmp_path / "rubrics"
    rubric_dir.mkdir(parents=True)
    (rubric_dir / "slow_project.json").write_text(
        json.dumps({
            "rubric_mode": "newton",
            "composition_stagnation_threshold": 5,
        }),
        encoding="utf-8",
    )
    workspace = tmp_path / "projects" / "slow_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "run_start",
            "rubric": "slow_project",
            "project": "slow_project",
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 5,
            "stagnation_count": 4,
            "loop_control_action": "normal",
            "pending_loop_action": "CONTINUE",
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "stagnation_reached_no_next_control_boundary"
    assert row.effective_pivot_threshold == 5
    assert row.threshold_source == "rubric"


def test_counts_pivot_blitz_and_primitive_class_as_escape_evidence(tmp_path):
    workspace = tmp_path / "projects" / "escape_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 4,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
            "pending_loop_action": "CONTINUE",
        },
    )
    _append_jsonl(
        workspace / "loop_events.jsonl",
        {"event_type": "topological_pivot_profile_injected"},
    )
    _append_jsonl(
        workspace / "parallel_blitz_log.jsonl",
        {"iter": 4, "k": 3, "decision_reason": "stagnation_count=3 >= 2"},
    )
    _append_jsonl(
        workspace / "explored_primitive_classes.jsonl",
        {"class_name": "residual boundary detector"},
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "escape_evidence_observed"
    assert row.pivot_event_count == 1
    assert row.pivot_action_count == 1
    assert row.blitz_iteration_count == 1
    assert row.primitive_class_count == 1
    assert row.escape_signal_count == 4
    assert row.active_control_signal_count == 4
    assert row.mechanism_status_counts["active"] == 4
    assert row.active_mechanisms == (
        "pivot_events",
        "pivot_actions",
        "parallel_blitz",
        "primitive_class_rotation",
    )


def test_post_control_outcomes_dedupe_same_iteration_mechanisms(tmp_path):
    workspace = tmp_path / "projects" / "dedup_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 4,
            "score": 10,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )
    _append_jsonl(
        workspace / "loop_events.jsonl",
        {
            "event_type": "topological_pivot_profile_injected",
            "run_id": "run-a",
            "iteration": 4,
        },
    )
    _append_jsonl(
        workspace / "parallel_blitz_log.jsonl",
        {"run_id": "run-a", "iter": 4, "k": 3},
    )
    _append_jsonl(
        workspace / "explored_primitive_classes.jsonl",
        {"run_id": "run-a", "iteration": 4, "class_name": "boundary detector"},
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 5,
            "score": 15,
            "stagnation_count": 0,
            "loop_control_action": "normal",
            "score_improved": True,
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.active_control_signal_count == 4
    assert row.active_control_event_count == 1
    assert row.post_control_window_count == 1
    assert row.post_control_success_count == 1


def test_active_control_outcomes_count_followup_success(tmp_path):
    workspace = tmp_path / "projects" / "recovered_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 1,
            "score": 50,
            "stagnation_count": 2,
            "loop_control_action": "normal",
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "score": 45,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
            "score_improved": False,
            "champion_promoted": False,
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 3,
            "score": 60,
            "stagnation_count": 0,
            "loop_control_action": "normal",
            "score_improved": True,
            "champion_promoted": True,
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.active_control_event_count == 1
    assert row.post_control_window_count == 1
    assert row.post_control_no_followup_count == 0
    assert row.post_control_success_count == 1
    assert row.post_control_improvement_count == 1
    assert row.post_control_champion_count == 1
    assert row.post_control_stagnation_drop_count == 1
    assert row.post_control_success_rate == 1.0


def test_advisory_and_diagnostic_signals_do_not_mask_missing_active_control(tmp_path):
    project = tmp_path / "projects" / "advisory_only"
    workspace = project / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 4,
            "stagnation_count": 4,
            "loop_control_action": "normal",
            "pending_loop_action": "CONTINUE",
        },
    )
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "blitz_survival_report.json").write_text("{}", encoding="utf-8")
    charter = project / "project_charter.md"
    proposal = project / "proposed_eigenquestion_20260612_010203.md"
    charter.write_text("old charter\n", encoding="utf-8")
    proposal.write_text("new proposal\n", encoding="utf-8")
    # Make the proposal newer than the charter.
    import os

    os.utime(charter, (1000, 1000))
    os.utime(proposal, (2000, 2000))

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "control_due_without_breadth_evidence"
    assert row.active_control_signal_count == 0
    assert row.advisory_signal_count == 1
    assert row.diagnostic_signal_count == 1
    assert row.advisory_mechanisms == ("pending_eigenquestion_review",)
    assert row.diagnostic_mechanisms == ("blitz_survival_report",)
    assert row.mechanism_status_counts == {"active": 0, "advisory": 1, "diagnostic": 1}


def test_project_report_orders_uncovered_stagnation_first(tmp_path):
    stuck = tmp_path / "projects" / "demo" / "workspace"
    escaped = tmp_path / "projects" / "demo" / "archive" / "workspace"
    _append_jsonl(
        stuck / "iteration_telemetry.jsonl",
        {"record_type": "iteration", "iteration_index": 3, "stagnation_count": 3},
    )
    _append_jsonl(
        escaped / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "iteration_index": 2,
            "stagnation_count": 2,
            "loop_control_action": "stagnation_pivot",
        },
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    text = render_text(report)

    assert report["workspace_count"] == 2
    assert report["status_counts"]["control_due_without_breadth_evidence"] == 1
    assert report["mechanism_status_totals"]["active"] == 1
    assert report["post_control_outcome_totals"]["active_control_event_count"] == 1
    assert report["post_control_outcome_totals"]["post_control_window_count"] == 0
    assert report["rows"][0]["workspace"] == "projects/demo/workspace"
    assert "Autoresearch hill-climb behavior audit" in text
    assert "mechanism_status_totals=" in text
    assert "post_control_outcomes=" in text
    assert "latest_yield=" in text
