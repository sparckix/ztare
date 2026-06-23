from __future__ import annotations

import json
from pathlib import Path

from ztare.reports.hill_climb_behavior_audit import (
    audit_workspace,
    build_control_episode_recovery_report,
    build_hill_climb_behavior_audit,
    record_control_episode_recovery_resolution,
    render_recovery_text,
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
    _append_jsonl(
        workspace / "control_followup_policy.jsonl",
        {
            "record_type": "control_followup_policy_decision",
            "iteration_index": 5,
            "candidate_control_kind": "stagnation_pivot",
            "allowed": False,
            "decision": "observe_prior_control_followup",
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.status == "escape_evidence_observed"
    assert row.pivot_event_count == 1
    assert row.pivot_action_count == 1
    assert row.blitz_iteration_count == 1
    assert row.primitive_class_count == 1
    assert row.control_followup_decision_count == 1
    assert row.control_followup_block_count == 1
    assert row.control_followup_allow_count == 0
    assert row.escape_signal_count == 5
    assert row.active_control_signal_count == 5
    assert row.mechanism_status_counts["active"] == 5
    assert row.active_mechanisms == (
        "pivot_events",
        "pivot_actions",
        "parallel_blitz",
        "primitive_class_rotation",
        "control_followup_policy",
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
    assert row.post_control_observed_no_success_count == 0
    assert row.post_control_success_count == 1
    assert row.post_control_improvement_count == 1
    assert row.post_control_champion_count == 1
    assert row.post_control_stagnation_drop_count == 1
    assert row.post_control_success_rate == 1.0
    diagnostic = row.post_control_diagnostics[0]
    assert diagnostic["outcome_status"] == "control_success"
    assert diagnostic["routing_hint"] == "preserve_or_replay_control"
    assert diagnostic["score_delta"] == 15.0
    assert diagnostic["stagnation_dropped"] is True
    assert diagnostic["followup_iterations"] == [3]


def test_active_control_outcomes_count_observed_no_success(tmp_path):
    workspace = tmp_path / "projects" / "continued_no_lift_project" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "score": 50,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 3,
            "score": 45,
            "stagnation_count": 4,
            "loop_control_action": "normal",
            "score_improved": False,
            "champion_promoted": False,
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.active_control_event_count == 1
    assert row.post_control_window_count == 1
    assert row.post_control_no_followup_count == 0
    assert row.post_control_observed_no_success_count == 1
    assert row.post_control_success_count == 0
    assert row.post_control_success_rate == 0.0
    diagnostic = row.post_control_diagnostics[0]
    assert diagnostic["outcome_status"] == "control_observed_no_success"
    assert diagnostic["routing_hint"] == "review_control_selection_or_measurement"
    assert diagnostic["score_delta"] == -5.0
    assert diagnostic["stagnation_dropped"] is False


def test_repeated_controls_are_grouped_into_one_followup_episode(tmp_path):
    workspace = tmp_path / "projects" / "repeated_control_project" / "workspace"
    for iteration in (2, 3, 4):
        _append_jsonl(
            workspace / "iteration_telemetry.jsonl",
            {
                "record_type": "iteration",
                "run_id": "run-a",
                "iteration_index": iteration,
                "score": 50,
                "stagnation_count": iteration,
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
            "iteration_index": 5,
            "score": 45,
            "stagnation_count": 5,
            "loop_control_action": "normal",
            "score_improved": False,
            "champion_promoted": False,
        },
    )

    row = audit_workspace(workspace, repo=tmp_path, stagnation_threshold=2)

    assert row.active_control_event_count == 3
    assert row.control_episode_count == 1
    assert row.post_control_window_count == 3
    assert row.post_control_observed_no_success_count == 3
    assert row.post_control_episode_window_count == 1
    assert row.post_control_episode_observed_no_success_count == 1
    assert row.post_control_episode_success_count == 0
    assert row.post_control_episode_success_rate == 0.0
    diagnostic = row.post_control_episode_diagnostics[0]
    assert diagnostic["event_iterations"] == [2, 3, 4]
    assert diagnostic["event_count"] == 3
    assert diagnostic["outcome_status"] == "control_observed_no_success"


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
    _append_jsonl(
        escaped / "control_followup_policy.jsonl",
        {
            "record_type": "control_followup_policy_decision",
            "iteration_index": 3,
            "candidate_control_kind": "parallel_blitz",
            "allowed": False,
            "decision": "observe_prior_control_followup",
        },
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    text = render_text(report)

    assert report["workspace_count"] == 2
    assert report["status_counts"]["control_due_without_breadth_evidence"] == 1
    assert report["mechanism_status_totals"]["active"] == 2
    assert report["control_followup_policy_totals"] == {
        "control_followup_decision_count": 1,
        "control_followup_block_count": 1,
        "control_followup_allow_count": 0,
    }
    assert report["post_control_outcome_totals"]["active_control_event_count"] == 1
    assert report["post_control_episode_totals"]["control_episode_count"] == 1
    assert report["post_control_outcome_totals"]["post_control_window_count"] == 0
    assert report["post_control_episode_totals"]["post_control_episode_window_count"] == 0
    assert report["post_control_outcome_totals"]["post_control_observed_no_success_count"] == 0
    assert report["post_control_diagnostic_counts"] == {
        "control_fired_without_followup": 1
    }
    assert report["control_episode_recovery_counts"] == {
        "control_fired_without_followup": 1
    }
    assert report["control_episode_recovery_admission_packet_counts"] == {
        "missing_admission_packet": 1
    }
    assert report["control_episode_recovery_queue"] == [
        {
            "priority": 0,
            "workspace": "projects/demo/archive/workspace",
            "project": "demo",
            "fixture_like_project": False,
            "rubric": "demo",
            "run_id": "",
            "iteration": 2,
            "last_control_iteration": 2,
            "event_iterations": [2],
            "event_count": 1,
            "mechanisms": ["pivot_action"],
            "outcome_status": "control_fired_without_followup",
            "routing_hint": "run_followup_or_record_no_followup_reason",
            "action": "run_followup_or_record_no_followup_reason",
            "reason": "control episode fired but no follow-up iteration was observed",
            "followup_window": 3,
            "constituent_outcome_counts": {"control_fired_without_followup": 1},
            "project_intake": None,
            "packet": None,
            "compiled_evidence_packet": None,
            "intake_status": "missing_project_intake",
            "admission_packet_status": "missing_admission_packet",
            "intake_draft_command": None,
            "packet_draft_command": None,
            "trace_command": (
                "ztare autoresearch trace --project demo --rubric demo --json"
            ),
            "preflight_command": None,
            "kernel_entry_status": None,
            "kernel_entry_trace_status": None,
            "kernel_entry_readiness": None,
            "kernel_entry_can_enter": None,
            "kernel_entry_blockers": [],
            "kernel_entry_blocking_missing": [],
            "kernel_entry_trace_error": None,
            "next_command": (
                "ztare autoresearch trace --project demo --rubric demo --json"
            ),
        }
    ]
    assert report["post_control_diagnostic_samples"] == [
        {
            "workspace": "projects/demo/archive/workspace",
            "run_id": "",
            "iteration": 2,
            "mechanisms": ["pivot_action"],
            "outcome_status": "control_fired_without_followup",
            "routing_hint": "run_followup_or_record_no_followup_reason",
            "followup_window": 3,
            "followup_iteration_count": 0,
            "followup_iterations": [],
            "current_score": None,
            "best_followup_score": None,
            "score_delta": None,
            "current_stagnation_count": 2,
            "min_followup_stagnation_count": None,
            "score_improved": False,
            "champion_promoted": False,
            "stagnation_dropped": False,
        }
    ]
    assert report["rows"][0]["workspace"] == "projects/demo/workspace"
    assert "Autoresearch hill-climb behavior audit" in text
    assert "mechanism_status_totals=" in text
    assert "post_control_outcomes=" in text
    assert "post_control_episodes=" in text
    assert "post_control_diagnostics=" in text
    assert "control_episode_recovery_counts=" in text
    assert "control_followup_policy=" in text
    assert "latest_yield=" in text


def test_control_episode_recovery_report_is_bounded_queue_view(tmp_path):
    first = tmp_path / "projects" / "demo" / "workspace"
    second = tmp_path / "projects" / "demo" / "archive" / "workspace"
    for workspace, run_id, iteration in (
        (first, "run-a", 2),
        (second, "run-b", 5),
    ):
        _append_jsonl(
            workspace / "iteration_telemetry.jsonl",
            {
                "record_type": "iteration",
                "run_id": run_id,
                "iteration_index": iteration,
                "stagnation_count": 3,
                "loop_control_action": "stagnation_pivot",
            },
        )

    full = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    recovery = build_control_episode_recovery_report(full, limit=1)
    text = render_recovery_text(recovery)

    assert recovery["schema"] == "ztare-hill-climb-control-recovery-v1"
    assert recovery["project"] == "demo"
    assert recovery["queue_count"] == 2
    assert recovery["queue_limit"] == 1
    assert len(recovery["queue"]) == 1
    assert recovery["control_episode_recovery_counts"] == {
        "control_fired_without_followup": 2
    }
    assert "Autoresearch loop-control recovery queue" in text
    assert "next=ztare autoresearch trace --project demo --rubric demo --json" in text
    assert "... 1 additional recovery rows omitted" in text


def test_control_episode_recovery_queue_is_packet_aware(tmp_path):
    workspace = tmp_path / "projects" / "demo" / "workspace"
    packet_path = tmp_path / "projects" / "demo" / "project_packet.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        "{}\n",
        encoding="utf-8",
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "run_start",
            "run_id": "run-a",
            "rubric": "demo",
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    row = report["control_episode_recovery_queue"][0]

    assert row["project_intake"] == "projects/demo/project_packet.json"
    assert row["packet"] == "projects/demo/project_packet.json"
    assert row["compiled_evidence_packet"] is None
    assert row["intake_status"] == "ready"
    assert row["admission_packet_status"] == "ready"
    assert row["intake_draft_command"] is None
    assert row["packet_draft_command"] is None
    assert row["trace_command"] == (
        "ztare autoresearch trace --project demo --rubric demo "
        "--intake projects/demo/project_packet.json --json"
    )
    assert row["preflight_command"] == (
        "ztare autoresearch run --project demo --rubric demo "
        "--intake projects/demo/project_packet.json --preflight-only"
    )
    assert row["kernel_entry_status"] == "blocked"
    assert row["kernel_entry_trace_status"] == "partial_trace"
    assert row["kernel_entry_can_enter"] is False
    assert row["kernel_entry_readiness"] == "blocked_on_project_surfaces"
    assert row["kernel_entry_blockers"] == [
        "raw_or_evidence",
        "rubric",
        "project_packet",
        "source_preflight",
    ]
    assert row["next_command"] == (
        "ztare project intake validate --path projects/demo/project_packet.json"
    )


def test_control_episode_recovery_prefers_project_intake_over_legacy_packet(tmp_path):
    workspace = tmp_path / "projects" / "demo" / "workspace"
    intake_path = tmp_path / "projects" / "demo" / "project_intake.json"
    packet_path = tmp_path / "projects" / "demo" / "project_packet.json"
    intake_path.parent.mkdir(parents=True, exist_ok=True)
    intake_path.write_text("{}\n", encoding="utf-8")
    packet_path.write_text("{}\n", encoding="utf-8")
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "run_start",
            "run_id": "run-a",
            "rubric": "demo",
        },
    )
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    row = report["control_episode_recovery_queue"][0]

    assert row["project_intake"] == "projects/demo/project_intake.json"
    assert row["packet"] == "projects/demo/project_intake.json"
    assert row["intake_status"] == "ready"
    assert row["trace_command"] == (
        "ztare autoresearch trace --project demo --rubric demo "
        "--intake projects/demo/project_intake.json --json"
    )
    assert row["preflight_command"] == (
        "ztare autoresearch run --project demo --rubric demo "
        "--intake projects/demo/project_intake.json --preflight-only"
    )


def test_control_episode_recovery_report_filters_by_packet_status(tmp_path):
    ready_workspace = tmp_path / "projects" / "ready_demo" / "workspace"
    missing_workspace = tmp_path / "projects" / "missing_demo" / "workspace"
    packet_path = tmp_path / "projects" / "ready_demo" / "project_packet.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text("{}\n", encoding="utf-8")
    for workspace, run_id in (
        (ready_workspace, "run-ready"),
        (missing_workspace, "run-missing"),
    ):
        _append_jsonl(
            workspace / "iteration_telemetry.jsonl",
            {
                "record_type": "iteration",
                "run_id": run_id,
                "iteration_index": 2,
                "stagnation_count": 3,
                "loop_control_action": "stagnation_pivot",
            },
        )

    full = build_hill_climb_behavior_audit(repo=tmp_path)
    ready = build_control_episode_recovery_report(
        full,
        intake_status="ready",
    )

    assert ready["intake_status_filter"] == "ready"
    assert ready["packet_status_filter"] == "ready"
    assert ready["legacy_packet_status_filter"] == "ready"
    assert ready["queue_count"] == 1
    assert ready["queue"][0]["project"] == "ready_demo"
    assert ready["queue"][0]["intake_status"] == "ready"
    assert ready["queue"][0]["admission_packet_status"] == "ready"


def test_control_episode_recovery_marks_compiled_evidence_without_project_intake(
    tmp_path,
):
    workspace = tmp_path / "projects" / "demo" / "workspace"
    compiled = tmp_path / "projects" / "demo" / "compiled_evidence_packet.json"
    compiled.parent.mkdir(parents=True, exist_ok=True)
    compiled.write_text("{}\n", encoding="utf-8")
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    row = report["control_episode_recovery_queue"][0]

    assert report["control_episode_recovery_intake_counts"] == {
        "compiled_evidence_without_project_intake": 1
    }
    assert report["control_episode_recovery_admission_packet_counts"] == {
        "compiled_evidence_without_admission_packet": 1
    }
    assert row["project_intake"] is None
    assert row["packet"] is None
    assert row["compiled_evidence_packet"] == "projects/demo/compiled_evidence_packet.json"
    assert row["intake_status"] == "compiled_evidence_without_project_intake"
    assert row["admission_packet_status"] == (
        "compiled_evidence_without_admission_packet"
    )
    assert row["preflight_command"] is None
    assert row["intake_draft_command"] == (
        "ztare project intake draft-from-compiled --project demo "
        "--path projects/demo/demo_intake.json"
    )
    assert row["packet_draft_command"] == (
        "ztare project intake draft-from-compiled --project demo "
        "--path projects/demo/demo_intake.json"
    )
    assert row["next_command"] == row["packet_draft_command"]


def test_control_episode_recovery_resolution_removes_active_queue_only(tmp_path):
    workspace = tmp_path / "projects" / "demo" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )

    before = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    assert before["control_episode_recovery_queue"][0]["outcome_status"] == (
        "control_fired_without_followup"
    )

    receipt = record_control_episode_recovery_resolution(
        workspace=workspace,
        repo=tmp_path,
        run_id="run-a",
        iteration=2,
        last_control_iteration=2,
        outcome_status="control_fired_without_followup",
        resolution_status="reason_recorded",
        reason="end-of-run control; next launch must use the packet preflight path",
        recorded_by="test",
    )
    assert receipt["counts_as_control_success"] is False

    after = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    assert after["control_episode_recovery_counts"] == {
        "control_fired_without_followup": 1
    }
    assert after["control_episode_recovery_unresolved_counts"] == {}
    assert after["control_episode_recovery_resolution_counts"] == {
        "reason_recorded": 1
    }
    assert after["control_episode_recovery_queue"] == []
    assert after["post_control_episode_totals"][
        "post_control_episode_no_followup_count"
    ] == 1
    assert after["post_control_episode_totals"]["post_control_episode_success_count"] == 0


def test_deferred_control_episode_resolution_stays_in_queue(tmp_path):
    workspace = tmp_path / "projects" / "demo" / "workspace"
    _append_jsonl(
        workspace / "iteration_telemetry.jsonl",
        {
            "record_type": "iteration",
            "run_id": "run-a",
            "iteration_index": 2,
            "stagnation_count": 3,
            "loop_control_action": "stagnation_pivot",
        },
    )
    record_control_episode_recovery_resolution(
        workspace=workspace,
        repo=tmp_path,
        run_id="run-a",
        iteration=2,
        last_control_iteration=2,
        outcome_status="control_fired_without_followup",
        resolution_status="deferred",
        reason="needs a follow-up run after source refresh",
        recorded_by="test",
    )

    report = build_hill_climb_behavior_audit(repo=tmp_path, project="demo")
    row = report["control_episode_recovery_queue"][0]

    assert report["control_episode_recovery_unresolved_counts"] == {
        "control_fired_without_followup": 1
    }
    assert report["control_episode_recovery_resolution_counts"] == {"deferred": 1}
    assert row["resolution_status"] == "deferred"
    assert row["resolution_closes_queue_item"] is False
