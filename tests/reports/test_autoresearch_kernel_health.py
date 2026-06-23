from __future__ import annotations

from types import SimpleNamespace

from ztare.reports import autoresearch_kernel_health as health
from ztare.workspace.evidence_gaps import LOCAL_VERIFICATION_RECOVERY_KIND


def test_packet_admission_drift_dedupes_latest_preflight_and_latest_run() -> None:
    packet = {
        "packet_path": "project_packet.json",
        "packet_sha256": "a" * 64,
        "packet_hash_status": "stale_current_packet",
        "packet_hash_verified": False,
        "kernel_entry_sha256": "b" * 64,
        "kernel_entry_hash_status": "current_kernel_entry_changed",
        "kernel_entry_hash_verified": False,
    }

    packet_issues = health._packet_admission_drift_issues(
        latest_run_project_packet=packet,
        latest_preflight_only={"packet": packet},
    )
    kernel_issues = health._kernel_entry_receipt_change_issues(
        latest_run_project_packet=packet,
        latest_preflight_only={"packet": packet},
    )

    assert packet_issues == [
        {
            "source": "latest_preflight_only",
            "packet_path": "project_packet.json",
            "packet_hash_status": "stale_current_packet",
            "packet_hash_verified": False,
        }
    ]
    assert kernel_issues == [
        {
            "source": "latest_preflight_only",
            "packet_path": "project_packet.json",
            "kernel_entry_hash_status": "current_kernel_entry_changed",
            "kernel_entry_hash_verified": False,
        }
    ]


def test_kernel_entry_receipt_change_uses_newer_full_run_lifecycle() -> None:
    latest_run_packet = {
        "packet_path": "project_packet.json",
        "packet_sha256": "a" * 64,
        "packet_hash_status": "fresh",
        "packet_hash_verified": True,
        "kernel_entry_sha256": "b" * 64,
        "kernel_entry_hash_status": "post_run_state_changed",
        "kernel_entry_hash_verified": None,
    }
    preflight_packet = {
        "packet_path": "project_packet.json",
        "packet_sha256": "a" * 64,
        "packet_hash_status": "fresh",
        "packet_hash_verified": True,
        "kernel_entry_sha256": "b" * 64,
        "kernel_entry_hash_status": "current_kernel_entry_changed",
        "kernel_entry_hash_verified": False,
    }

    kernel_issues = health._kernel_entry_receipt_change_issues(
        latest_run_project_packet=latest_run_packet,
        latest_preflight_only={"run_id": 11, "packet": preflight_packet},
        latest_run_id=20,
    )

    assert kernel_issues == []


def test_packet_admission_drift_uses_newest_admission_lifecycle() -> None:
    latest_run_packet = {
        "packet_path": "project_packet.json",
        "packet_sha256": "a" * 64,
        "packet_hash_status": "stale_current_packet",
        "packet_hash_verified": False,
        "kernel_entry_sha256": "b" * 64,
        "kernel_entry_hash_status": "post_run_state_changed",
        "kernel_entry_hash_verified": None,
    }
    preflight_packet = {
        "packet_path": "project_packet.json",
        "packet_sha256": "c" * 64,
        "packet_hash_status": "fresh",
        "packet_hash_verified": True,
        "kernel_entry_sha256": "d" * 64,
        "kernel_entry_hash_status": "fresh",
        "kernel_entry_hash_verified": True,
    }

    packet_issues = health._packet_admission_drift_issues(
        latest_run_project_packet=latest_run_packet,
        latest_preflight_only={"run_id": 30, "packet": preflight_packet},
        latest_run_id=20,
    )

    assert packet_issues == []


def _patch_common(
    monkeypatch,
    *,
    rubric_attention: int = 0,
    dispatch_findings: int = 0,
    subscription_ok: bool = True,
    subscription_status: str = "comparable",
    mechanism_summary: dict | None = None,
    route_rows_needed: int = 0,
    source_health_blockers: int = 0,
    source_health_warnings: int = 0,
    unexplained_bypasses: int = 0,
    parent_utility_ok: bool = True,
    primitive_open_misses: int = 0,
    primitive_malformed_misses: int = 0,
    project_trace_ready: bool = True,
    project_trace_blockers: list[dict] | None = None,
    project_trace_blocking_missing: list[str] | None = None,
    project_trace_prediction_issues: list[dict] | None = None,
    project_trace_source_freshness_status: str = "fresh",
    project_trace_compile_freshness_status: str = "fresh",
    project_trace_evidence_binding: dict | None = None,
    project_trace_evidence_replay: dict | None = None,
    project_trace_focus_receipts: list[dict] | None = None,
    project_trace_withheld_focus_receipts: list[dict] | None = None,
    project_trace_latest_run_packet: dict | None = None,
    project_trace_latest_preflight_only: dict | None = None,
    project_trace_provider_failures: list[dict] | None = None,
    project_trace_latest_provider_failure: dict | None = None,
    hill_post_control: dict | None = None,
    hill_post_control_episode: dict | None = None,
    hill_diagnostic_counts: dict | None = None,
    hill_diagnostic_samples: list[dict] | None = None,
    hill_recovery_counts: dict | None = None,
    hill_recovery_queue: list[dict] | None = None,
    hill_followup_policy: dict | None = None,
    source_preflight_blocking: list[str] | None = None,
    source_preflight_warnings: list[str] | None = None,
    graph_missing_rows: list[str] | None = None,
    forecast_missing_rows: list[str] | None = None,
):
    monkeypatch.setattr(
        health,
        "_dispatch_validate",
        lambda repo: {
            "summary": {
                "findings": dispatch_findings,
                "dispatch_sites": 20,
                "wrapped_sites": 16,
                "direct_allowed_sites": 4,
            },
            "direct_allowed": [
                {
                    "path": "src/ztare/validator/autoresearch_loop.py",
                    "line": 1357,
                    "function": "safe_mutate",
                    "reason": "dispatch-covered mutator fallback",
                }
            ],
        },
    )
    monkeypatch.setattr(
        health,
        "_catalog_health",
        lambda repo: SimpleNamespace(
            ok=True,
            row_count=781,
            warnings=(),
            stale_outputs=(),
        ),
    )
    monkeypatch.setattr(
        health,
        "_primitive_parent_utility",
        lambda: {
            "ok": parent_utility_ok,
            "case_count": 6,
            "passed": 6 if parent_utility_ok else 5,
            "catalog_rank_recall": 1.0,
            "worker_rank_recall": 1.0 if parent_utility_ok else 0.5,
            "child_recall": 1.0,
        },
    )
    monkeypatch.setattr(
        health,
        "_primitive_miss_queue",
        lambda repo: {
            "path": "analytics/public/queries/primitive_amnesia_miss_queue.jsonl",
            "row_count": primitive_open_misses + primitive_malformed_misses,
            "open_count": primitive_open_misses,
            "malformed_count": primitive_malformed_misses,
            "status_counts": {"open": primitive_open_misses}
            if primitive_open_misses
            else {},
            "promotion_review_counts": {
                "close_as_catalog_retrieval_repair": primitive_open_misses
            }
            if primitive_open_misses
            else {},
            "latest_open": [
                {
                    "miss_id": "miss1",
                    "case_id": "case1",
                    "query": "find overlap primitive",
                    "targets": ["jaccard"],
                    "promotion_review": {
                        "promotion_decision": "close_as_catalog_retrieval_repair",
                        "validation": {"ok": True, "missing": []},
                    },
                }
            ][:primitive_open_misses],
        },
    )
    monkeypatch.setattr(
        health,
        "_mechanism_consequences",
        lambda **kwargs: {
            "summary": mechanism_summary or {
                "mechanism_count": 13,
                "evidence_status_counts": {"observed": 13},
                "evidence_quality_counts": {"usable": 13},
                "intrinsic_decorative_count": 0,
                "placeholder_only_count": 0,
            }
        },
    )
    monkeypatch.setattr(
        health,
        "_fixtures",
        lambda: {
            "passed": True,
            "num_passed": 12,
            "num_fixtures": 12,
            "mechanism_status": {"by_status": {"active": {"passed": 8, "total": 8}}},
        },
    )
    monkeypatch.setattr(
        health,
        "_evidence_trace",
        lambda: {
            "all_passed": True,
            "num_passed": 5,
            "num_cases": 5,
            "trace": {
                "source_id": "S001",
                "confirmed_constraint_count": 1,
                "projection_negative_constraints": 1,
                "briefing_record_count": 3,
            },
        },
    )
    monkeypatch.setattr(
        health,
        "_graph_capability",
        lambda repo: {
            "summary": {
                "row_count": 17,
                "present_count": 17 - len(graph_missing_rows or []),
                "missing_count": len(graph_missing_rows or []),
                "status_counts": {
                    "ready_receipt_path": 6,
                    "ztare_recombination_layer": 7,
                    "standard_algorithm_with_ztare_adapter": 3,
                    "research_candidate_needs_benchmark": 1,
                },
                "ready_receipt_paths": [
                    "probability_dag_trace_carrier",
                    "source_claim_graph_trace_carrier",
                ],
                "missing_rows": graph_missing_rows or [],
            },
            "verdict": {
                "strongest_supported_claim": (
                    "ZTARE has a graph diagnostic carrier and recombination layer."
                ),
                "release_boundary": "Do not claim graph framework replacement.",
            },
        },
    )
    monkeypatch.setattr(
        health,
        "_forecast_capability",
        lambda repo: {
            "summary": {
                "row_count": 9,
                "present_count": 9 - len(forecast_missing_rows or []),
                "missing_count": len(forecast_missing_rows or []),
                "status_counts": {"ready_receipt_path": 9},
                "ready_receipt_paths": [
                    "gp230_contract_schema_gate",
                    "prediction_contract_read_model",
                    "operations_intelligence_consumer",
                ],
                "missing_rows": forecast_missing_rows or [],
            },
            "verdict": {
                "strongest_supported_claim": (
                    "ZTARE has a sealed forecast-pool lifecycle."
                ),
                "release_boundary": (
                    "Do not claim forecasts steer work without resolved lift."
                ),
                "needs_before_stronger_claim": (
                    "increase decision-use coverage and publish calibration lift"
                ),
            },
        },
    )
    monkeypatch.setattr(
        health,
        "_rubric_modes",
        lambda **kwargs: {
            "summary": {
                "attention_count": rubric_attention,
                "status_counts": {"ok": 10},
                "mode_counts": {"newton": 10},
                "legacy_unset": {
                    "count": 0,
                    "with_project_count": 0,
                    "without_project_count": 0,
                    "charter_status_counts": {},
                },
            }
        },
    )
    def _hill_report(**kwargs):
        report = {
            "workspace_count": 4,
            "stagnant_workspace_count": 2,
            "status_counts": {"escape_evidence_observed": 2},
            "post_control_outcome_totals": hill_post_control or {
                "active_control_event_count": 3,
                "post_control_window_count": 2,
                "post_control_no_followup_count": 0,
                "post_control_success_count": 1,
                "post_control_success_rate": 0.5,
            },
            "control_followup_policy_totals": hill_followup_policy or {
                "control_followup_decision_count": 0,
                "control_followup_block_count": 0,
                "control_followup_allow_count": 0,
            },
            "post_control_diagnostic_counts": hill_diagnostic_counts or {},
            "post_control_diagnostic_samples": hill_diagnostic_samples or [],
            "control_episode_recovery_counts": hill_recovery_counts or {},
            "control_episode_recovery_queue": hill_recovery_queue or [],
        }
        if hill_post_control_episode is not None:
            report["post_control_episode_totals"] = hill_post_control_episode
        return report

    monkeypatch.setattr(health, "_hill_climb", _hill_report)
    monkeypatch.setattr(
        health,
        "_subscription_outcomes",
        lambda **kwargs: {
            "ok": subscription_ok,
            "status": subscription_status,
            "summary": {
                "node_count": 8,
                "transport_counts": {"api": 4, "subscription_cli": 4}
                if subscription_ok
                else {"unrecorded": 8},
                "api_rows": 4 if subscription_ok else 0,
                "subscription_rows": 4 if subscription_ok else 0,
            },
            "matched_run_plan": []
            if subscription_ok
            else [
                {
                    "project": "gp_example",
                    "rubric": "gp_example",
                    "suitability_score": 88,
                    "matched_pair_command": (
                        "make autoresearch-matched-transport-pair PROJECT=gp_example "
                        "RUBRIC=gp_example ITERS=1 MATCHED_RUN_ID=pair_gp_example_001"
                    ),
                }
            ],
            "action": "inspect deltas"
            if subscription_ok
            else "run fresh API and subscription-backed rows with worker metadata",
        },
    )
    monkeypatch.setattr(
        health,
        "_operations_intelligence",
        lambda repo: {
            "agentic_workbench": {
                "rows": 5,
                "ready_workbench_bypasses": 0,
                "missing_surface_preparations": 2,
                "route_row_coverage": {
                    "status": "route_rows_present"
                    if route_rows_needed == 0
                    else "sparse_route_logging",
                    "route_rows": 5 - route_rows_needed,
                    "recommended_min_route_rows": 5,
                    "additional_route_rows_needed": route_rows_needed,
                    "needs_logging_attention": route_rows_needed > 0,
                },
                "subscription_outcomes": {"status": subscription_status},
                "ready_workbench_bypasses_without_reason": unexplained_bypasses,
            },
            "source_health_summary": {
                "blocking_count": source_health_blockers,
                "warning_count": source_health_warnings,
                "issue_count": source_health_blockers + source_health_warnings,
                "issue_type_counts": (
                    {"fixture_warning": source_health_warnings}
                    if source_health_warnings
                    else {}
                ),
                "issue_sample": [
                    {
                        "severity": "warning",
                        "scope": "fixture",
                        "issue_type": "fixture_warning",
                        "blocking_rule": None,
                        "recommended_action": "repair_source_emitter",
                        "evidence_refs": ["analytics/public/action_intelligence/state/source_health.json"],
                    }
                ]
                if source_health_warnings
                else [],
            },
        },
    )
    monkeypatch.setattr(
        health,
        "_source_preflight",
        lambda **kwargs: {
            "ok": not bool(source_preflight_blocking),
            "status": "blocked"
            if source_preflight_blocking
            else "ready_for_evidence_prepare",
            "source_count": 1,
            "source_evidence_count": 1,
            "untyped_source_count": 0,
            "unsupported_file_count": 0,
            "empty_file_count": 0,
            "blocking": source_preflight_blocking or [],
            "warnings": source_preflight_warnings or [],
            "next_steps": ["fix source typing"] if source_preflight_blocking else [
                "Compile the source/evidence chain before routing into the loop."
            ],
            "next_commands": []
            if source_preflight_blocking
            else ["make evidence-prepare PROJECT=gp_example MODEL=gemini"],
            "raw_dir": "projects/gp_example/raw",
            "source_type_map": "projects/gp_example/raw/source_type_map.json",
        },
    )
    monkeypatch.setattr(
        health,
        "_project_trace",
        lambda **kwargs: {
            "status": "complete_trace" if project_trace_ready else "partial_trace",
            "readiness": (
                "ready_for_in_loop_candidate"
                if project_trace_ready
                else "blocked_on_project_surfaces"
            ),
            "blocking_missing": project_trace_blocking_missing or [],
            "history_missing": [],
            "kernel_entry": {
                "status": "ready" if project_trace_ready else "blocked",
                "can_enter_kernel": project_trace_ready,
                "blockers": project_trace_blockers or [],
                "in_loop_focus_receipts": project_trace_focus_receipts or [],
                "withheld_in_loop_focus_receipts": (
                    project_trace_withheld_focus_receipts or []
                ),
            },
            "graph_carriers": [
                {
                    "graph_id": "gp_example:source_claim_graph",
                    "graph_kind": "source_claim_graph",
                }
            ],
            "graph_rd_actions": [],
            "prediction_summary": {
                "available": True,
                "status": (
                    "scoreable_measurement_lane"
                    if not project_trace_prediction_issues
                    else "needs_attention"
                ),
                "issues": project_trace_prediction_issues or [],
            },
            "surfaces": {
                "source_index_freshness": {
                    "status": project_trace_source_freshness_status
                },
                "evidence_compile_freshness": {
                    "status": project_trace_compile_freshness_status
                },
                "evidence_output_binding": (
                    project_trace_evidence_binding
                    or {"status": "fresh", "stale_artifacts": []}
                ),
                "evidence_replay": (
                    project_trace_evidence_replay
                    or {"status": "missing_manifest", "required": False, "ok": False}
                ),
            },
            "recent_loop": {
                "latest_run_project_packet": project_trace_latest_run_packet or {},
                "latest_preflight_only": project_trace_latest_preflight_only or {},
                "recent_provider_failure_signatures": (
                    project_trace_provider_failures or []
                ),
                "latest_provider_failure_signature": (
                    project_trace_latest_provider_failure
                ),
            },
        },
    )


def test_kernel_health_ready_when_components_ok(tmp_path, monkeypatch):
    _patch_common(monkeypatch)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["component_counts"] == {
        "ok": 10,
        "attention": 0,
        "needs_attention": 0,
    }
    assert report["summary"]["evidence_gap_count"] == 0
    rendered = health.render_text(report)
    assert "Autoresearch kernel health" in rendered
    assert "next=make autoresearch-dispatch-validate JSON=1" in rendered
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["summary"]["route_row_coverage_status"] == "route_rows_present"
    assert operations["next_command"] == "make operations-intelligence"
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    assert rubric["summary"]["legacy_unset_count"] == 0
    dispatch = next(row for row in report["components"] if row["component"] == "dispatch")
    assert dispatch["summary"]["direct_allowed"][0]["reason"] == (
        "dispatch-covered mutator fallback"
    )
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["summary"]["parent_utility"]["ok"] is True
    evidence_trace = next(
        row for row in report["components"] if row["component"] == "evidence_trace"
    )
    assert evidence_trace["status"] == "ok"
    assert evidence_trace["next_command"] == "make autoresearch-evidence-trace JSON=1"
    graph = next(row for row in report["components"] if row["component"] == "graph_capability")
    assert graph["status"] == "ok"
    assert graph["summary"]["missing_count"] == 0
    assert graph["next_command"] == "make graph-capability-audit JSON=1"
    forecast = next(
        row for row in report["components"] if row["component"] == "forecast_capability"
    )
    assert forecast["status"] == "ok"
    assert forecast["summary"]["missing_count"] == 0
    assert "forecast-pool lifecycle" in forecast["summary"]["strongest_supported_claim"]
    assert forecast["next_command"] == "make forecast-capability-audit JSON=1"
    hill = next(row for row in report["components"] if row["component"] == "hill_climb_controls")
    assert hill["summary"]["control_followup_policy_totals"] == {
        "control_followup_decision_count": 0,
        "control_followup_block_count": 0,
        "control_followup_allow_count": 0,
    }


def test_kernel_health_attention_for_rubric_debt(tmp_path, monkeypatch):
    _patch_common(monkeypatch, rubric_attention=3)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    assert rubric["status"] == "attention"
    assert rubric["summary"]["attention_count"] == 3
    assert rubric["next_command"] == "make autoresearch-rubric-mode-audit LIMIT=20"


def test_kernel_health_next_commands_preserve_scope(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        rubric_attention=1,
        project_trace_focus_receipts=[
            {
                "action_type": "in_loop_focus_receipt",
                "work_mode": "in_loop",
                "graph_id": "gp_example:source_claim_graph",
                "reason": "resolve local verification gap",
            }
        ],
        project_trace_latest_run_packet={
            "packet_path": "gp_example_packet.json",
            "packet_sha256": "a" * 64,
            "packet_current_sha256": "a" * 64,
            "packet_hash_status": "fresh",
            "packet_hash_verified": True,
            "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
            "packet_status": "valid_packet",
            "readiness": "ready_for_in_loop_candidate",
            "kernel_entry_status": "ready",
            "kernel_entry_sha256": "b" * 64,
        },
        project_trace_latest_preflight_only={
            "run_id": 202,
            "run_exit_reason": "preflight_only",
            "timestamp_utc": "2026-06-20T00:10:00Z",
            "packet": {
                "packet_path": "gp_example_packet.json",
                "packet_sha256": "a" * 64,
                "packet_current_sha256": "a" * 64,
                "packet_hash_status": "fresh",
                "packet_hash_verified": True,
                "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_in_loop_candidate",
                "kernel_entry_status": "ready",
                "kernel_entry_sha256": "b" * 64,
            },
        },
    )

    report = health.build_autoresearch_kernel_health(
        repo=tmp_path,
        project="gp_example",
        workspace="projects/gp_example/workspace",
        rubric="rubrics/gp_example.json",
        packet="gp_example_packet.json",
        stagnation_threshold=3,
    )

    assert report["scope"]["packet"] == "gp_example_packet.json"

    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    rubric = next(row for row in report["components"] if row["component"] == "rubric_modes")
    hill = next(row for row in report["components"] if row["component"] == "hill_climb_controls")

    assert mechanism["next_command"] == (
        "make autoresearch-consequence-audit PROJECT=gp_example "
        "WORKSPACE=projects/gp_example/workspace JSON=1"
    )
    assert rubric["next_command"] == (
        "make autoresearch-rubric-mode-audit RUBRIC=rubrics/gp_example.json LIMIT=20"
    )
    assert hill["next_command"] == (
        "make autoresearch-hillclimb-audit PROJECT=gp_example STAGNATION_THRESHOLD=3 "
        "RECOVERY_QUEUE=1 RECOVERY_LIMIT=20 JSON=1"
    )
    source = next(row for row in report["components"] if row["component"] == "source_preflight")
    assert source["status"] == "ok"
    assert source["summary"]["next_steps"] == []
    assert source["summary"]["next_commands"] == []
    assert source["next_command"] == (
        "ztare autoresearch trace --project gp_example "
        "--rubric rubrics/gp_example.json --intake gp_example_packet.json --json"
    )
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "ok"
    assert trace["summary"]["can_enter_kernel"] is True
    assert trace["summary"]["graph_carrier_count"] == 1
    assert trace["summary"]["in_loop_focus_receipt_count"] == 1
    assert trace["summary"]["withheld_in_loop_focus_receipt_count"] == 0
    assert trace["summary"]["evidence_readiness"] == {
        "status": "fresh",
        "source_index_status": "fresh",
        "compile_provenance_status": "fresh",
        "output_binding_status": "fresh",
        "output_stale_artifacts": [],
        "replay_required": False,
        "replay_status": "not_required",
        "raw_replay_status": "missing_manifest",
        "replay_ok": True,
    }
    assert trace["summary"]["source_index_freshness_status"] == "fresh"
    assert trace["summary"]["evidence_output_binding_status"] == "fresh"
    assert trace["summary"]["evidence_output_stale_artifacts"] == []
    assert trace["summary"]["packet_admission_drift_count"] == 0
    assert trace["summary"]["packet_admission_drift"] == []
    assert trace["summary"]["kernel_entry_receipt_change_count"] == 0
    assert trace["summary"]["kernel_entry_receipt_changes"] == []
    assert trace["summary"]["latest_run_project_packet"] == {
        "packet_path": "gp_example_packet.json",
        "packet_sha256": "a" * 64,
        "packet_current_sha256": "a" * 64,
        "packet_hash_status": "fresh",
        "packet_hash_verified": True,
        "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
        "packet_status": "valid_packet",
        "readiness": "ready_for_in_loop_candidate",
        "kernel_entry_status": "ready",
        "kernel_entry_sha256": "b" * 64,
    }
    assert trace["summary"]["latest_preflight_only"] == {
        "run_id": 202,
        "run_exit_reason": "preflight_only",
        "timestamp_utc": "2026-06-20T00:10:00Z",
        "packet": {
            "packet_path": "gp_example_packet.json",
            "packet_sha256": "a" * 64,
            "packet_current_sha256": "a" * 64,
            "packet_hash_status": "fresh",
            "packet_hash_verified": True,
            "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
            "packet_status": "valid_packet",
            "readiness": "ready_for_in_loop_candidate",
            "kernel_entry_status": "ready",
            "kernel_entry_sha256": "b" * 64,
        },
    }
    assert trace["next_command"] == (
        "ztare autoresearch trace --project gp_example "
        "--rubric rubrics/gp_example.json --intake gp_example_packet.json --json"
    )


def test_kernel_health_blocks_project_with_source_preflight_debt(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        source_preflight_blocking=["one or more sources declare an invalid source_type"],
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path, project="gp_example")

    assert report["summary"]["overall_status"] == "needs_attention"
    source = next(row for row in report["components"] if row["component"] == "source_preflight")
    assert source["status"] == "needs_attention"
    assert source["summary"]["blocking"] == [
        "one or more sources declare an invalid source_type"
    ]
    assert source["summary"]["next_steps"] == ["fix source typing"]
    assert source["summary"]["next_commands"] == []
    assert source["summary"]["source_count"] == 1
    assert source["next_command"] == "ztare project source-check --project gp_example --json"


def test_kernel_health_blocks_project_with_trace_debt(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        project_trace_ready=False,
        project_trace_blocking_missing=["prediction_authority_claim_invalid"],
        project_trace_blockers=[
            {
                "id": "prediction_authority_claim_invalid",
                "recovery_channel": "prediction_contracts",
                "next_command": "ztare audit forecast-capability --json",
            }
        ],
        project_trace_prediction_issues=[
            {
                "code": "missing_forecast_pool_authority_anchor",
                "message": "certified forecast-pool rows need an authority anchor",
            },
            {
                "code": "invalid_membrane_claim",
                "message": "scratch and in-loop rows are measurement-only",
            },
        ],
        project_trace_evidence_binding={
            "status": "stale",
            "stale_artifacts": ["audit_copy"],
        },
        project_trace_withheld_focus_receipts=[
            {
                "action_type": "in_loop_focus_receipt",
                "work_mode": "in_loop",
                "graph_id": "gp_example:source_claim_graph",
                "reason": "resolve local verification gap",
            }
        ],
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path, project="gp_example")

    assert report["summary"]["overall_status"] == "needs_attention"
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "needs_attention"
    assert trace["summary"]["can_enter_kernel"] is False
    assert trace["summary"]["blocking_missing"] == ["prediction_authority_claim_invalid"]
    assert trace["summary"]["blockers"] == [
        {
            "id": "prediction_authority_claim_invalid",
            "recovery_channel": "prediction_contracts",
            "next_command": "ztare audit forecast-capability --json",
        }
    ]
    assert trace["summary"]["prediction_issue_codes"] == [
        "missing_forecast_pool_authority_anchor",
        "invalid_membrane_claim",
    ]
    assert trace["summary"]["in_loop_focus_receipt_count"] == 0
    assert trace["summary"]["withheld_in_loop_focus_receipt_count"] == 1
    assert trace["summary"]["evidence_readiness"]["status"] == "blocked"
    assert trace["summary"]["evidence_readiness"]["output_binding_status"] == "stale"
    assert trace["summary"]["evidence_output_binding_status"] == "stale"
    assert trace["summary"]["evidence_output_stale_artifacts"] == ["audit_copy"]
    assert trace["action"] == "resolve project trace blockers before run readiness"
    assert trace["next_command"] == "ztare autoresearch trace --project gp_example --json"


def test_kernel_health_summarizes_stale_evidence_replay(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        project_trace_ready=False,
        project_trace_blocking_missing=["evidence_replay_stale"],
        project_trace_blockers=[
            {
                "id": "evidence_replay_stale",
                "recovery_channel": "evidence_replay",
                "next_command": "ztare project evidence-replay --project gp_example --json",
            }
        ],
        project_trace_evidence_replay={
            "status": "stale_or_invalid",
            "required": True,
            "ok": False,
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path, project="gp_example")

    assert report["summary"]["overall_status"] == "needs_attention"
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "needs_attention"
    assert trace["summary"]["blocking_missing"] == ["evidence_replay_stale"]
    assert trace["summary"]["evidence_readiness"] == {
        "status": "blocked",
        "source_index_status": "fresh",
        "compile_provenance_status": "fresh",
        "output_binding_status": "fresh",
        "output_stale_artifacts": [],
        "replay_required": True,
        "replay_status": "stale_or_invalid",
        "raw_replay_status": "stale_or_invalid",
        "replay_ok": False,
    }


def test_kernel_health_attention_for_packet_admission_drift(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        project_trace_latest_preflight_only={
            "run_id": 303,
            "run_exit_reason": "preflight_only",
            "timestamp_utc": "2026-06-20T00:10:00Z",
            "packet": {
                "packet_path": "gp_example_packet.json",
                "packet_sha256": "a" * 64,
                "packet_current_sha256": "c" * 64,
                "packet_hash_status": "stale_current_packet",
                "packet_hash_verified": False,
                "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_first_in_loop_run",
                "kernel_entry_status": "ready",
                "kernel_entry_sha256": "b" * 64,
                "kernel_entry_current_sha256": "d" * 64,
                "kernel_entry_hash_status": "current_kernel_entry_changed",
                "kernel_entry_hash_verified": False,
            },
        },
    )

    report = health.build_autoresearch_kernel_health(
        repo=tmp_path,
        project="gp_example",
        rubric="rubrics/gp_example.json",
        packet="gp_example_packet.json",
    )

    assert report["summary"]["overall_status"] == "attention"
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "attention"
    assert trace["action"] == (
        "inspect packet admission drift before reusing prior run evidence"
    )
    assert trace["summary"]["can_enter_kernel"] is True
    assert trace["summary"]["packet_admission_drift_count"] == 1
    assert trace["summary"]["packet_admission_drift"] == [
        {
            "source": "latest_preflight_only",
            "packet_path": "gp_example_packet.json",
            "packet_hash_status": "stale_current_packet",
            "packet_hash_verified": False,
        }
    ]
    assert trace["summary"]["kernel_entry_receipt_change_count"] == 1
    assert trace["summary"]["kernel_entry_receipt_changes"] == [
        {
            "source": "latest_preflight_only",
            "packet_path": "gp_example_packet.json",
            "kernel_entry_hash_status": "current_kernel_entry_changed",
            "kernel_entry_hash_verified": False,
        }
    ]


def test_kernel_health_attention_for_kernel_entry_receipt_change(tmp_path, monkeypatch):
    _patch_common(
        monkeypatch,
        project_trace_latest_preflight_only={
            "run_id": 303,
            "run_exit_reason": "preflight_only",
            "timestamp_utc": "2026-06-20T00:10:00Z",
            "packet": {
                "packet_path": "gp_example_packet.json",
                "packet_sha256": "a" * 64,
                "packet_current_sha256": "a" * 64,
                "packet_hash_status": "fresh",
                "packet_hash_verified": True,
                "packet_id": "gp_example:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_first_in_loop_run",
                "kernel_entry_status": "ready",
                "kernel_entry_sha256": "b" * 64,
                "kernel_entry_current_sha256": "d" * 64,
                "kernel_entry_hash_status": "current_kernel_entry_changed",
                "kernel_entry_hash_verified": False,
            },
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path, project="gp_example")

    assert report["summary"]["overall_status"] == "attention"
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "attention"
    assert trace["action"] == (
        "refresh run-readiness receipt before reusing prior admission evidence"
    )
    assert trace["summary"]["packet_admission_drift_count"] == 0
    assert trace["summary"]["kernel_entry_receipt_change_count"] == 1


def test_kernel_health_attention_for_provider_failure_signature(tmp_path, monkeypatch):
    signature = {
        "failure_class": "mutator_charged_no_output_no_effective_model",
        "model_id": "kimi-k2.6",
        "input_tokens_charged": 8535,
        "output_tokens": 0,
        "fallback_observed": False,
        "pending_loop_action": "REFRESH_SPECIALISTS",
        "information_yield_rationale": (
            "Latest iteration failed R1 declaration validation."
        ),
        "estimated_cost_usd": 0.008108,
        "interpretation": "provider_runtime_failure_not_research_signal",
        "recovery_kind": "provider_timeout_retry_budget",
        "retry_scope": "same_model_before_cross_model_fallback",
        "recommended_retry_budget": {
            "same_model_retries": 1,
            "allow_cross_model_fallback": False,
        },
        "run_id": 303,
        "iteration": 1,
    }
    _patch_common(
        monkeypatch,
        project_trace_provider_failures=[signature],
        project_trace_latest_provider_failure=signature,
    )

    report = health.build_autoresearch_kernel_health(
        repo=tmp_path,
        project="gp_example",
        rubric="rubrics/gp_example.json",
        packet="gp_example_packet.json",
    )

    assert report["summary"]["overall_status"] == "attention"
    trace = next(row for row in report["components"] if row["component"] == "project_trace")
    assert trace["status"] == "attention"
    assert trace["action"] == (
        "inspect provider timeout/retry failure before treating loop failure as research signal"
    )
    assert trace["summary"]["provider_failure_signature_count"] == 1
    assert trace["summary"]["recent_provider_failure_signatures"] == [signature]
    assert trace["summary"]["latest_provider_failure_signature"] == signature


def test_kernel_health_needs_attention_when_parent_utility_fails(tmp_path, monkeypatch):
    _patch_common(monkeypatch, parent_utility_ok=False)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "needs_attention"
    assert catalog["summary"]["parent_utility"]["ok"] is False
    assert catalog["next_command"] == "make primitive-parent-utility JSON=1"


def test_kernel_health_attention_for_open_primitive_miss_queue(tmp_path, monkeypatch):
    _patch_common(monkeypatch, primitive_open_misses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "attention"
    assert catalog["summary"]["miss_queue"]["open_count"] == 1
    assert catalog["summary"]["miss_queue"]["promotion_review_counts"] == {
        "close_as_catalog_retrieval_repair": 1
    }
    assert catalog["next_command"] == "make primitive-amnesia-eval RECORD_MISSES=1"


def test_kernel_health_needs_attention_for_malformed_primitive_miss_queue(tmp_path, monkeypatch):
    _patch_common(monkeypatch, primitive_malformed_misses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    catalog = next(row for row in report["components"] if row["component"] == "primitive_catalog")
    assert catalog["status"] == "needs_attention"
    assert catalog["summary"]["miss_queue"]["malformed_count"] == 1


def test_kernel_health_needs_attention_for_placeholder_only_mechanisms(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        mechanism_summary={
            "mechanism_count": 13,
            "evidence_status_counts": {"observed": 12, "placeholder_only": 1},
            "evidence_quality_counts": {"usable": 12, "placeholder_only": 1},
            "intrinsic_decorative_count": 0,
            "placeholder_only_count": 1,
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    assert mechanism["status"] == "needs_attention"
    assert mechanism["summary"]["placeholder_only_count"] == 1
    assert "placeholder-only" in mechanism["action"]


def test_kernel_health_surfaces_not_triggered_mechanisms_as_coverage_opportunity(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        mechanism_summary={
            "mechanism_count": 13,
            "evidence_status_counts": {"observed": 10, "not_triggered": 3},
            "evidence_quality_counts": {"usable": 10, "not_triggered": 3},
            "intrinsic_decorative_count": 0,
            "placeholder_only_count": 0,
        },
    )
    monkeypatch.setattr(
        health,
        "_mechanism_consequences",
        lambda **kwargs: {
            "summary": {
                "mechanism_count": 13,
                "evidence_status_counts": {"observed": 10, "not_triggered": 3},
                "evidence_quality_counts": {"usable": 10, "not_triggered": 3},
                "intrinsic_decorative_count": 0,
                "placeholder_only_count": 0,
            },
            "rows": [
                {
                    "mechanism_id": "parallel_blitz",
                    "label": "Parallel mutator / blitz selection",
                    "trigger": "Rubric force flag or stagnation threshold enables K-way mutation.",
                    "evidence_status": "not_triggered",
                    "activation_hint": "not triggered because parallel_mutator_k=1",
                }
            ],
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["evidence_gap_count"] == 0
    assert report["summary"]["coverage_opportunity_count"] == 1
    mechanism = next(
        row for row in report["components"] if row["component"] == "mechanism_consequences"
    )
    assert mechanism["status"] == "ok"
    assert mechanism["summary"]["not_triggered_count"] == 3
    opportunity = report["coverage_opportunities"][0]
    assert opportunity["id"] == "not_triggered_mechanisms"
    assert opportunity["status"] == "not_triggered"
    assert opportunity["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert opportunity["recovery_channel"] == "kernel_health"
    assert opportunity["summary"]["count"] == 3
    assert opportunity["summary"]["examples"][0]["mechanism_id"] == "parallel_blitz"
    assert "parallel_mutator_k=1" in opportunity["summary"]["examples"][0]["activation_hint"]
    rendered = health.render_text(report)
    assert "evidence_gaps=0" in rendered
    assert "coverage_opportunities=1" in rendered
    assert "coverage_opportunity:not_triggered_mechanisms" in rendered


def test_kernel_health_surfaces_subscription_outcome_gap_without_blocking(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        subscription_ok=False,
        subscription_status="transport_metadata_missing",
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    assert report["summary"]["component_status"] == "ok"
    assert report["summary"]["component_counts"] == {
        "ok": 10,
        "attention": 0,
        "needs_attention": 0,
    }
    assert report["summary"]["evidence_gap_count"] == 1
    gap = report["evidence_gaps"][0]
    assert gap["id"] == "subscription_outcomes"
    assert gap["status"] == "transport_metadata_missing"
    assert gap["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert gap["recovery_channel"] == "kernel_health"
    assert gap["next_command"] == "make autoresearch-subscription-outcome-audit JSON=1"
    assert gap["summary"]["suggested_matched_pair_project"] == "gp_example"
    assert gap["summary"]["suggested_matched_pair_rubric"] == "gp_example"
    assert gap["summary"]["suggested_matched_pair_suitability"] == 88
    assert gap["summary"]["suggested_matched_pair_command"].startswith(
        "make autoresearch-matched-transport-pair PROJECT=gp_example"
    )
    rendered = health.render_text(report)
    assert "evidence_gaps=1" in rendered
    assert "evidence_gap:subscription_outcomes" in rendered


def test_kernel_health_surfaces_weak_hill_climb_outcomes_as_evidence_gap(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        hill_post_control={
            "active_control_event_count": 40,
            "post_control_window_count": 25,
            "post_control_no_followup_count": 15,
            "post_control_observed_no_success_count": 19,
            "post_control_success_count": 6,
            "post_control_success_rate": 0.24,
        },
        hill_followup_policy={
            "control_followup_decision_count": 7,
            "control_followup_block_count": 5,
            "control_followup_allow_count": 2,
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    assert report["summary"]["component_status"] == "ok"
    hill = next(row for row in report["components"] if row["component"] == "hill_climb_controls")
    assert hill["status"] == "ok"
    assert hill["summary"]["post_control_no_followup_rate"] == 0.375
    assert hill["summary"]["post_control_observed_no_success_count"] == 19
    assert hill["summary"]["post_control_observed_no_success_rate"] == 0.76
    assert hill["summary"]["control_followup_policy_totals"] == {
        "control_followup_decision_count": 7,
        "control_followup_block_count": 5,
        "control_followup_allow_count": 2,
    }
    assert hill["summary"]["post_control_diagnostic_counts"] == {}
    gap = report["evidence_gaps"][0]
    assert gap["id"] == "hill_climb_control_outcomes"
    assert gap["status"] == "weak_post_control_evidence"
    assert gap["recovery_kind"] == LOCAL_VERIFICATION_RECOVERY_KIND
    assert gap["recovery_channel"] == "kernel_health"
    assert gap["summary"]["post_control_success_rate"] == 0.24
    assert gap["summary"]["post_control_observed_no_success_count"] == 19
    assert gap["summary"]["control_followup_policy_totals"] == {
        "control_followup_decision_count": 7,
        "control_followup_block_count": 5,
        "control_followup_allow_count": 2,
    }
    assert gap["next_command"] == (
        "make autoresearch-hillclimb-audit RECOVERY_QUEUE=1 "
        "RECOVERY_LIMIT=20 JSON=1"
    )


def test_kernel_health_surfaces_high_hill_climb_no_followup_as_evidence_gap(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        hill_post_control={
            "active_control_event_count": 20,
            "post_control_window_count": 8,
            "post_control_no_followup_count": 12,
            "post_control_observed_no_success_count": 2,
            "post_control_success_count": 6,
            "post_control_success_rate": 0.75,
        },
        hill_diagnostic_counts={
            "control_fired_without_followup": 12,
            "control_success": 6,
            "control_observed_no_success": 2,
        },
        hill_diagnostic_samples=[
            {
                "workspace": "projects/demo/workspace",
                "run_id": "r1",
                "iteration": 4,
                "mechanisms": ["pivot_action"],
                "outcome_status": "control_fired_without_followup",
                "routing_hint": "run_followup_or_record_no_followup_reason",
            }
        ],
        hill_recovery_counts={"control_fired_without_followup": 12},
        hill_recovery_queue=[
            {
                "workspace": "projects/demo/workspace",
                "project": "demo",
                "rubric": "demo",
                "run_id": "r1",
                "iteration": 4,
                "outcome_status": "control_fired_without_followup",
                "action": "run_followup_or_record_no_followup_reason",
                "reason": "control episode fired but no follow-up iteration was observed",
                "next_command": (
                    "ztare autoresearch trace --project demo --rubric demo --json"
                ),
            }
        ],
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "attention"
    gap = report["evidence_gaps"][0]
    assert gap["id"] == "hill_climb_control_outcomes"
    assert gap["summary"]["post_control_no_followup_rate"] == 0.6
    assert gap["summary"]["post_control_observed_no_success_rate"] == 0.25
    assert gap["summary"]["post_control_diagnostic_counts"] == {
        "control_fired_without_followup": 12,
        "control_success": 6,
        "control_observed_no_success": 2,
    }
    assert gap["summary"]["post_control_diagnostic_samples"][0]["routing_hint"] == (
        "run_followup_or_record_no_followup_reason"
    )
    assert gap["summary"]["control_episode_recovery_counts"] == {
        "control_fired_without_followup": 12
    }
    assert gap["summary"]["control_episode_recovery_queue"][0]["next_command"] == (
        "ztare autoresearch trace --project demo --rubric demo --json"
    )


def test_kernel_health_uses_episode_metrics_for_hill_climb_evidence_gap(
    tmp_path, monkeypatch
):
    _patch_common(
        monkeypatch,
        hill_post_control={
            "active_control_event_count": 40,
            "post_control_window_count": 25,
            "post_control_no_followup_count": 15,
            "post_control_observed_no_success_count": 19,
            "post_control_success_count": 6,
            "post_control_success_rate": 0.24,
        },
        hill_post_control_episode={
            "control_episode_count": 4,
            "post_control_episode_window_count": 4,
            "post_control_episode_no_followup_count": 0,
            "post_control_episode_observed_no_success_count": 1,
            "post_control_episode_success_count": 3,
            "post_control_episode_success_rate": 0.75,
        },
    )

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    hill = next(row for row in report["components"] if row["component"] == "hill_climb_controls")
    assert hill["summary"]["active_control_event_count"] == 40
    assert hill["summary"]["control_episode_count"] == 4
    assert hill["summary"]["post_control_episode_success_rate"] == 0.75
    assert not [
        gap for gap in report["evidence_gaps"]
        if gap["id"] == "hill_climb_control_outcomes"
    ]


def test_kernel_health_needs_attention_for_graph_capability_drift(tmp_path, monkeypatch):
    _patch_common(monkeypatch, graph_missing_rows=["probability_dag_trace_carrier"])

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    graph = next(row for row in report["components"] if row["component"] == "graph_capability")
    assert graph["status"] == "needs_attention"
    assert graph["summary"]["missing_rows"] == ["probability_dag_trace_carrier"]
    assert graph["next_command"] == "make graph-capability-audit JSON=1"


def test_kernel_health_needs_attention_for_forecast_capability_drift(tmp_path, monkeypatch):
    _patch_common(monkeypatch, forecast_missing_rows=["decision_use_logging"])

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    forecast = next(
        row for row in report["components"] if row["component"] == "forecast_capability"
    )
    assert forecast["status"] == "needs_attention"
    assert forecast["summary"]["missing_rows"] == ["decision_use_logging"]
    assert forecast["next_command"] == "make forecast-capability-audit JSON=1"


def test_kernel_health_needs_attention_for_sparse_route_logging(tmp_path, monkeypatch):
    _patch_common(monkeypatch, route_rows_needed=2)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["additional_route_rows_needed"] == 2
    assert operations["next_command"] == "make operations-intelligence"


def test_kernel_health_needs_attention_for_blocking_action_sources(tmp_path, monkeypatch):
    _patch_common(monkeypatch, source_health_blockers=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["source_health_blockers"] == 1


def test_kernel_health_surfaces_source_health_warnings_without_blocking(
    tmp_path, monkeypatch
):
    _patch_common(monkeypatch, source_health_warnings=2)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "ok"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "ok"
    assert operations["summary"]["source_health_issues"] == 2
    assert operations["summary"]["source_health_warnings"] == 2
    assert operations["summary"]["source_health_blockers"] == 0
    assert operations["summary"]["source_health_issue_type_counts"] == {
        "fixture_warning": 2
    }
    assert operations["summary"]["source_health_issue_sample"][0]["issue_type"] == (
        "fixture_warning"
    )


def test_kernel_health_needs_attention_for_unexplained_workbench_bypass(
    tmp_path, monkeypatch
):
    _patch_common(monkeypatch, unexplained_bypasses=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    operations = next(
        row for row in report["components"] if row["component"] == "operations_intelligence"
    )
    assert operations["status"] == "needs_attention"
    assert operations["summary"]["ready_workbench_bypasses_without_reason"] == 1


def test_main_strict_fails_on_subscription_outcome_evidence_gap(
    tmp_path, monkeypatch, capsys
):
    _patch_common(
        monkeypatch,
        subscription_ok=False,
        subscription_status="transport_metadata_missing",
    )
    monkeypatch.setattr(health, "REPO", tmp_path)

    rc = health.main(["--strict"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "status=attention" in out
    assert "evidence_gaps=1" in out


def test_kernel_health_needs_attention_for_dispatch_findings(tmp_path, monkeypatch):
    _patch_common(monkeypatch, rubric_attention=3, dispatch_findings=1)

    report = health.build_autoresearch_kernel_health(repo=tmp_path)

    assert report["summary"]["overall_status"] == "needs_attention"
    dispatch = next(row for row in report["components"] if row["component"] == "dispatch")
    assert dispatch["status"] == "needs_attention"


def test_main_strict_fails_on_attention(tmp_path, monkeypatch, capsys):
    _patch_common(monkeypatch, rubric_attention=1)
    monkeypatch.setattr(health, "REPO", tmp_path)

    rc = health.main(["--strict"])

    assert rc == 1
    assert "status=attention" in capsys.readouterr().out
