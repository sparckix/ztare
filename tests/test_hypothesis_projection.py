from __future__ import annotations

import json
from pathlib import Path

from ztare.validator.hypothesis_projection import build_projection


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_hypothesis_projection_builds_admission_spine(tmp_path: Path):
    project = tmp_path / "projects" / "demo_project"
    history = project / "history"
    history.mkdir(parents=True)
    (history / "100_iter1_score_10_demo_project.md").write_text("first", encoding="utf-8")
    (history / "100_iter3_score_25_demo_project.md").write_text("third", encoding="utf-8")
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 10,
                "weakest_point": "Alpha gate failed because the input boundary was underspecified.",
                "timestamp": "2026-06-11T00:00:01",
            },
            {
                "iteration": 2,
                "score": 8,
                "weakest_point": "Alpha gate failed because the input boundary was underspecified.",
                "timestamp": "2026-06-11T00:00:02",
            },
            {
                "iteration": 3,
                "score": 25,
                "parametric_form": "min(X, Y)",
                "weakest_point": "Beta handoff needs an explicit reviewer receipt.",
                "worker_archetype": "fungible_agent_worker",
                "transport": "subscription_cli",
                "matched_run_id": "pair_demo_project",
                "matched_run_role": "subscription",
                "held_out_admission": {"passed": True},
                "timestamp": "2026-06-11T00:00:03",
            },
        ],
    )
    _append_jsonl(
        project / "workspace" / "dag_steering_log.jsonl",
        [
            {"selected_node_id": "alpha"},
            {"selected_node_id": "alpha"},
            {"selected_node_id": "beta"},
        ],
    )

    projection = build_projection(project)

    assert projection.projection_kind == "ztare_autoresearch_hypothesis_projection_v0"
    assert [node.status for node in projection.nodes] == ["merged", "pruned", "merged"]
    assert projection.nodes[0].parent_id is None
    assert projection.nodes[1].parent_id == "n0001"
    assert projection.nodes[2].parent_id == "n0001"
    assert projection.nodes[2].hypothesis == "min(X, Y)"
    assert projection.nodes[2].worker_archetype == "fungible_agent_worker"
    assert projection.nodes[2].worker_capability == "unrecorded"
    assert projection.nodes[2].worker_state == "unrecorded"
    assert projection.nodes[2].worker_identity == "unrecorded"
    assert projection.nodes[2].transport == "subscription_cli"
    assert projection.nodes[2].worker_dispatch_receipts == []
    assert projection.nodes[2].matched_run_id == "pair_demo_project"
    assert projection.nodes[2].matched_run_role == "subscription"
    assert projection.nodes[0].matched_run_id is None
    assert projection.nodes[0].artifact_refs == [
        "projects/demo_project/history/100_iter1_score_10_demo_project.md"
    ]
    assert projection.summary.admitted_count == 2
    assert projection.summary.rejected_count == 1
    assert projection.summary.score_gain == 15
    assert projection.summary.branch_cue_count == 3
    assert projection.summary.unique_branch_cue_count == 2
    assert projection.summary.repeated_branch_cue_count == 1
    assert projection.summary.held_out_admission_evidence_count == 1
    assert projection.summary.negative_constraint_count == 1
    assert projection.summary.open_frontier_constraint_count == 1
    assert len(projection.negative_constraints) == 1
    constraint = projection.negative_constraints[0]
    assert constraint.failure_signature == (
        "alpha gate failed because the input boundary was underspecified"
    )
    assert constraint.count == 1
    assert constraint.node_ids == ["n0002"]
    assert constraint.branch_cues == ["alpha"]
    assert len(projection.open_frontier_constraints) == 1
    assert projection.open_frontier_constraints[0].node_ids == ["n0003"]
    assert projection.open_frontier_constraints[0].failure_signature == (
        "beta handoff needs an explicit reviewer receipt"
    )


def test_hypothesis_projection_does_not_infer_held_out_evidence(tmp_path: Path):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 40,
                "weakest_point": "Candidate improved the development score only.",
            }
        ],
    )

    projection = build_projection(project)

    assert projection.summary.held_out_admission_evidence_count == 0
    assert projection.nodes[0].held_out_evidence_present is False
    assert projection.nodes[0].worker_archetype == "unrecorded"
    assert projection.nodes[0].worker_capability == "unrecorded"
    assert projection.nodes[0].worker_state == "unrecorded"
    assert projection.nodes[0].worker_identity == "unrecorded"
    assert projection.nodes[0].transport == "unrecorded"
    assert projection.negative_constraints == []
    assert len(projection.open_frontier_constraints) == 1


def test_hypothesis_projection_reads_transport_from_worker_call_site_metadata(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 40,
                "weakest_point": "Candidate used a subscription judge only.",
                "worker_metadata_by_call_site": {
                    "mutator": {"transport": "api", "worker_capability": "llm"},
                    "judge": {"transport": "subscription_cli", "worker_capability": "agent"},
                },
            }
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].transport == "subscription_cli"


def test_hypothesis_projection_prefers_completed_dispatch_receipts_over_policy_metadata(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 40,
                "weakest_point": "Policy requested a subscription judge, but only API calls completed.",
                "worker_metadata_by_call_site": {
                    "mutator": {"transport": "subscription_cli", "worker_capability": "agent"},
                    "judge": {"transport": "subscription_cli", "worker_capability": "agent"},
                },
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "api",
                        "worker_capability": "llm",
                        "completed": True,
                    },
                    {
                        "call_site": "judge",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": False,
                    },
                ],
            }
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].transport == "api"
    assert len(projection.nodes[0].worker_dispatch_receipts) == 2


def test_hypothesis_projection_uses_completed_subscription_receipt(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 40,
                "weakest_point": "A bounded subscription mutator completed.",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "mutator",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            }
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].transport == "subscription_cli"


def test_hypothesis_projection_recovers_gate_failures_from_iteration_telemetry(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 0,
                "weakest_point": "Candidate was zeroed by a hard gate.",
                "timestamp": "2026-06-14T00:24:57.240889",
                "matched_run_id": "pair_demo_project",
                "matched_run_role": "subscription",
                "worker_dispatch_receipts": [
                    {
                        "call_site": "judge",
                        "transport": "subscription_cli",
                        "worker_capability": "agent",
                        "completed": True,
                    }
                ],
            }
        ],
    )
    _append_jsonl(
        project / "workspace" / "iteration_telemetry.jsonl",
        [
            {
                "record_type": "iteration",
                "iteration_index": 1,
                "iteration_end_utc": "2026-06-14T00:24:57.243820+00:00",
                "gate_failure_count": 1,
                "failed_gate_ids": ["global_project_sweep_definitional_tautology"],
            }
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].gate_failure_count == 1
    assert projection.nodes[0].failed_gate_ids == [
        "global_project_sweep_definitional_tautology"
    ]


def test_hypothesis_projection_links_action_intelligence_rows(tmp_path: Path):
    project = tmp_path / "projects" / "demo_project"
    history = project / "history"
    history.mkdir(parents=True)
    artifact = "projects/demo_project/history/100_iter1_score_40_demo_project.md"
    (tmp_path / artifact).write_text("candidate", encoding="utf-8")
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 40,
                "weakest_point": "Route needs a recorded downstream decision.",
                "artifact_refs": [artifact],
            }
        ],
    )
    _append_jsonl(
        tmp_path / "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        [
            {
                "action_impact_id": "ai_projection_demo",
                "selected_action": "invoke_autoresearch",
                "decision_point": {
                    "decision_id": "decision_projection_demo",
                    "project_id": "demo_project",
                },
                "context_features": {
                    "project_family": "demo_project",
                    "workbench_router_decision": "invoke_autoresearch",
                },
                "source_refs": {"source_refs": [artifact]},
            }
        ],
    )

    projection = build_projection(project)

    assert projection.summary.action_intelligence_link_count == 1
    assert projection.nodes[0].action_intelligence_refs == [
        {
            "action_impact_id": "ai_projection_demo",
            "decision_id": "decision_projection_demo",
            "selected_action": "invoke_autoresearch",
            "workbench_router_decision": "invoke_autoresearch",
            "match_kind": "artifact_ref",
            "matched_refs": [artifact],
        }
    ]


def test_hypothesis_projection_prefers_eval_history_gate_failures(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 0,
                "weakest_point": "Candidate was zeroed by a hard gate.",
                "gate_failure_count": 2,
                "failed_gate_ids": ["gate_a", "gate_b"],
            }
        ],
    )
    _append_jsonl(
        project / "workspace" / "iteration_telemetry.jsonl",
        [
            {
                "record_type": "iteration",
                "iteration_index": 1,
                "gate_failure_count": 1,
                "failed_gate_ids": ["old_gate"],
            }
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].gate_failure_count == 2
    assert projection.nodes[0].failed_gate_ids == ["gate_a", "gate_b"]


def test_hypothesis_projection_matches_same_iteration_telemetry_by_timestamp(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "demo_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 35,
                "weakest_point": "API row without gate failure.",
                "timestamp": "2026-06-13T20:14:39.824253",
                "matched_run_id": "pair_demo_project",
                "matched_run_role": "api",
                "transport": "api",
            },
            {
                "iteration": 1,
                "score": 0,
                "weakest_point": "Subscription row with gate failure.",
                "timestamp": "2026-06-13T20:24:57.240889",
                "matched_run_id": "pair_demo_project",
                "matched_run_role": "subscription",
                "transport": "subscription_cli",
            },
        ],
    )
    _append_jsonl(
        project / "workspace" / "iteration_telemetry.jsonl",
        [
            {
                "record_type": "iteration",
                "iteration_index": 1,
                "iteration_end_utc": "2026-06-14T00:14:39.827120+00:00",
                "gate_failure_count": 0,
                "failed_gate_ids": [],
            },
            {
                "record_type": "iteration",
                "iteration_index": 1,
                "iteration_end_utc": "2026-06-14T00:24:57.243820+00:00",
                "gate_failure_count": 1,
                "failed_gate_ids": ["global_project_sweep_definitional_tautology"],
            },
        ],
    )

    projection = build_projection(project)

    assert projection.nodes[0].gate_failure_count == 0
    assert projection.nodes[0].failed_gate_ids == []
    assert projection.nodes[1].gate_failure_count == 1
    assert projection.nodes[1].failed_gate_ids == [
        "global_project_sweep_definitional_tautology"
    ]


def test_hypothesis_projection_falls_back_to_legacy_history_meta(tmp_path: Path):
    project = tmp_path / "projects" / "legacy_project"
    history = project / "history"
    history.mkdir(parents=True)
    (history / "200_iter0_score_30_legacy_project.md").write_text("first", encoding="utf-8")
    (history / "200_iter1_score_44_legacy_project.md").write_text("second", encoding="utf-8")
    (history / "200_iter2_score_43_other_rubric.md").write_text("other", encoding="utf-8")
    (history / "200_iter0_score_30_legacy_project_meta.json").write_text(
        json.dumps(
            {
                "run_id": 200,
                "iteration": 0,
                "score": 30,
                "rubric": "legacy_project",
                "weakest_point": "Scenario frame is too broad.",
                "timestamp": "2026-04-13T00:00:01",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (history / "200_iter1_score_44_legacy_project_meta.json").write_text(
        json.dumps(
            {
                "run_id": 200,
                "iteration": 1,
                "score": 44,
                "rubric": "legacy_project",
                "weakest_point": "Scenario frame is still too broad.",
                "timestamp": "2026-04-13T00:00:02",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (history / "200_iter2_score_43_other_rubric_meta.json").write_text(
        json.dumps(
            {
                "run_id": 200,
                "iteration": 2,
                "score": 43,
                "rubric": "other_rubric",
                "weakest_point": "This should not enter the project projection.",
                "timestamp": "2026-04-13T00:00:03",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    projection = build_projection(project)

    assert [node.iteration for node in projection.nodes] == [0, 1]
    assert [node.score for node in projection.nodes] == [30.0, 44.0]
    assert projection.summary.node_count == 2
    assert projection.summary.best_score == 44.0
    assert projection.summary.open_frontier_constraint_count == 1
    assert projection.nodes[0].artifact_refs == [
        "projects/legacy_project/history/200_iter0_score_30_legacy_project.md"
    ]


def test_hypothesis_projection_reports_latest_eval_without_history(tmp_path: Path):
    project = tmp_path / "projects" / "latest_only_project"
    (project).mkdir(parents=True)
    (project / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "iteration": 0,
                "score": 41,
                "weakest_point": "Baseline claim lacks a source-bound falsifier.",
                "gate_failure_count": 1,
                "failed_gate_ids": ["source_bound_falsifier_missing"],
                "timestamp": "2026-06-20T00:00:00Z",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    projection = build_projection(project)

    assert projection.summary.node_count == 0
    assert projection.latest_eval_overlay["available"] is True
    assert projection.latest_eval_overlay["status"] == "latest_eval_without_eval_history"
    assert projection.latest_eval_overlay["matches_history"] is False
    assert projection.latest_eval_overlay["score"] == 41.0
    assert projection.latest_eval_overlay["gate_failure_count"] == 1
    assert projection.latest_eval_overlay["failed_gate_ids"] == [
        "source_bound_falsifier_missing"
    ]
    assert "projection nodes are empty" in projection.latest_eval_overlay["warnings"][0]


def test_hypothesis_projection_warns_when_latest_eval_is_not_in_history(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "stale_history_project"
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 20,
                "weakest_point": "Earlier source gap.",
                "timestamp": "2026-06-20T00:00:00Z",
            }
        ],
    )
    (project / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "iteration": 2,
                "score": 55,
                "weakest_point": "New claim survived source preflight but failed holdout.",
                "timestamp": "2026-06-20T00:10:00Z",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    projection = build_projection(project)

    assert projection.summary.node_count == 1
    assert projection.summary.best_score == 20.0
    assert projection.latest_eval_overlay["status"] == "latest_eval_not_in_eval_history"
    assert projection.latest_eval_overlay["matches_history"] is False
    assert projection.latest_eval_overlay["iteration"] == 2
    assert projection.latest_eval_overlay["score"] == 55.0
    assert "nodes as stale" in projection.latest_eval_overlay["warnings"][0]


def test_hypothesis_projection_matches_latest_eval_against_truncated_history_weakest_point(
    tmp_path: Path,
):
    project = tmp_path / "projects" / "truncated_history_project"
    full_weakest = (
        "The thesis depends on deterministic filesystem path resolution for a "
        "missing reference and therefore needs source-code evidence that the "
        "preflight fails closed instead of logging and continuing."
    )
    _append_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 72,
                "weakest_point": full_weakest[:120],
                "timestamp": "2026-06-20T00:00:00Z",
            }
        ],
    )
    (project / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "score": 72,
                "weakest_point": full_weakest,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    projection = build_projection(project)

    assert projection.latest_eval_overlay["status"] == "covered_by_eval_history"
    assert projection.latest_eval_overlay["matches_history"] is True
    assert projection.latest_eval_overlay["warnings"] == []
