from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.reports import autoresearch_trace
from ztare.scaffold.substrate_queue import (
    build_project_packet,
    project_packet_path_safety_policy,
    write_project_packet,
)
from ztare.workspace.evidence_gaps import LOCAL_VERIFICATION_RECOVERY_KIND
from ztare.workspace.evidence_gap_resolutions import write_gap_resolution
from ztare.workspace.evidence_output_binding import write_evidence_output_binding_receipt
from ztare.workspace.compile_evidence import (
    EVIDENCE_REPLAY_MANIFEST_SCHEMA,
    stable_json_sha256,
)
from ztare.workspace.update_workspace import checkpoint_source_index


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_trace_discovers_project_intake_before_legacy_packet_name(tmp_path: Path) -> None:
    repo = tmp_path
    project_dir = repo / "projects" / "demo"
    project_dir.mkdir(parents=True)
    canonical = project_dir / "demo_intake.json"
    legacy = project_dir / "demo_packet.json"
    canonical.write_text("{}", encoding="utf-8")
    legacy.write_text("{}", encoding="utf-8")

    resolved = autoresearch_trace._resolve_packet_path(
        packet=None,
        repo=repo,
        project_dir=project_dir,
        project="demo",
    )

    assert resolved == canonical.resolve()


def _without_graph_card_provenance(row: dict) -> dict:
    out = dict(row)
    assert out.pop("operator_card_ids") == ["OP-GDC-01"]
    routes = out.pop("operator_card_routes")
    assert len(routes) == 1
    assert routes[0]["card_id"] == "OP-GDC-01"
    assert routes[0]["route_mode"] in {"lexical_fallback", "semantic_atlas"}
    return out


def test_packet_bound_command_renders_intake_boundary_once() -> None:
    command = (
        "ztare autoresearch route --task 'test claim' "
        "--project demo --rubric demo"
    )
    assert autoresearch_trace._packet_bound_command(
        command,
        packet_path="demo_packet.json",
    ) == (
        "ztare autoresearch route --task 'test claim' "
        "--project demo --rubric demo --intake demo_packet.json"
    )
    assert autoresearch_trace._packet_bound_command(
        command + " --intake demo_packet.json",
        packet_path="demo_packet.json",
    ).count("--intake") == 1
    normalized = autoresearch_trace._packet_bound_command(
        command + " --packet demo_packet.json",
        packet_path="demo_packet.json",
    )
    assert "--packet" not in normalized
    assert normalized.count("--intake") == 1


def test_evidence_fetch_severity_uses_strongest_active_public_gap(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "projects" / "demo"
    gaps_path = project_dir / "workspace" / "latest_evidence_gaps.json"
    _write_json(
        gaps_path,
        {
            "evidence_gaps": [
                {
                    "id": "local_blocker",
                    "severity": "blocking",
                    "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
                },
                {"id": "public_degrading", "severity": "degrading"},
            ]
        },
    )

    assert (
        autoresearch_trace._evidence_fetch_severity(
            gaps_path,
            project_dir=project_dir,
        )
        == "degrading"
    )

    _write_json(
        gaps_path,
        {
            "evidence_gaps": [
                {"id": "public_degrading", "severity": "degrading"},
                {"id": "public_blocking", "severity": "blocking"},
            ]
        },
    )

    assert (
        autoresearch_trace._evidence_fetch_severity(
            gaps_path,
            project_dir=project_dir,
        )
        == "blocking"
    )


def test_bool_flag_adds_once_to_packet_run_command() -> None:
    command = (
        "ztare autoresearch run --project demo --rubric demo "
        "--iters 3 --mutator kimi --judge gpt4.1"
    )

    assert autoresearch_trace._with_bool_flag(command, "--preflight-only") == (
        "ztare autoresearch run --project demo --rubric demo "
        "--iters 3 --mutator kimi --judge gpt4.1 --preflight-only"
    )
    assert autoresearch_trace._with_bool_flag(
        command + " --preflight-only",
        "--preflight-only",
    ).count("--preflight-only") == 1


def test_packet_receipt_with_current_kernel_entry_marks_fresh() -> None:
    receipt = {"kernel_entry_sha256": "a" * 64}

    result = autoresearch_trace._packet_receipt_with_current_kernel_entry(
        receipt,
        current_kernel_entry_sha256="a" * 64,
    )

    assert result["kernel_entry_current_sha256"] == "a" * 64
    assert result["kernel_entry_hash_verified"] is True
    assert result["kernel_entry_hash_status"] == "fresh"


def test_packet_receipt_marks_post_run_kernel_change_as_not_replayable() -> None:
    receipt = {"kernel_entry_sha256": "a" * 64}

    result = autoresearch_trace._packet_receipt_with_current_kernel_entry(
        receipt,
        current_kernel_entry_sha256="b" * 64,
        mutable_after_launch=True,
    )

    assert result["kernel_entry_current_sha256"] == "b" * 64
    assert result["kernel_entry_hash_verified"] is None
    assert result["kernel_entry_hash_status"] == "post_run_state_changed"


def test_provider_failure_signature_detects_charged_no_output_mutator() -> None:
    signature = autoresearch_trace._provider_failure_signature(
        {
            "run_id": 303,
            "iteration_index": 1,
            "mutator_usage": {"input_tokens": 8535, "output_tokens": 0},
            "pending_loop_action": "REFRESH_SPECIALISTS",
            "information_yield_rationale": "Latest iteration failed R1 declaration validation.",
            "estimated_cost_usd": 0.008108,
        },
        requested_model_id="kimi-k2.6",
        effective_model_ids=[],
        fallback_events=[],
    )

    assert signature == {
        "failure_class": "mutator_charged_no_output_no_effective_model",
        "model_id": "kimi-k2.6",
        "input_tokens_charged": 8535,
        "output_tokens": 0,
        "fallback_observed": False,
        "pending_loop_action": "REFRESH_SPECIALISTS",
        "information_yield_rationale": "Latest iteration failed R1 declaration validation.",
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


def test_provider_failure_signature_ignores_fallback_or_successful_output() -> None:
    row = {
        "mutator_usage": {"input_tokens": 100, "output_tokens": 0},
        "pending_loop_action": "REFRESH_SPECIALISTS",
    }

    assert (
        autoresearch_trace._provider_failure_signature(
            row,
            requested_model_id="kimi-k2.6",
            effective_model_ids=["gpt-4.1"],
            fallback_events=[{"from": "kimi-k2.6", "to": "gpt-4.1"}],
        )
        is None
    )
    assert (
        autoresearch_trace._provider_failure_signature(
            {"mutator_usage": {"input_tokens": 100, "output_tokens": 20}},
            requested_model_id="kimi-k2.6",
            effective_model_ids=[],
            fallback_events=[],
        )
        is None
    )


def test_plan_preview_treats_provider_failure_as_runtime_risk() -> None:
    plan = autoresearch_trace.build_autoresearch_plan_preview(
        project="provider_gap",
        rubric="provider_gap",
        route_command="ztare autoresearch route --task gap --project provider_gap --rubric provider_gap",
        preflight_command=(
            "ztare autoresearch run --project provider_gap --rubric provider_gap "
            "--preflight-only"
        ),
        run_command=(
            "ztare autoresearch run --project provider_gap --rubric provider_gap "
            "--iters 2"
        ),
        can_run_now=True,
        provider_failure_observed=True,
    )

    assert plan["status"] == "ready_for_preflight"
    assert plan["model_calls_before_confirmation"] is False
    assert (
        plan["largest_quality_drop_risk"]
        == "provider_runtime_failure_misread_as_research_signal"
    )
    assert plan["budget"]["iteration_budget"] == "2"
    assert plan["budget"]["model_fallback_policy"] == "disabled_by_default"


def test_plan_preview_recommends_run_after_current_preflight_admission() -> None:
    run_command = "ztare autoresearch run --project demo --rubric demo --iters 1"
    preflight_command = run_command + " --preflight-only"

    plan = autoresearch_trace.build_autoresearch_plan_preview(
        project="demo",
        rubric="demo",
        preflight_command=preflight_command,
        run_command=run_command,
        can_run_now=True,
        preflight_admitted=True,
    )

    assert plan["status"] == "ready_for_bounded_run"
    assert plan["recommended_first_command"] == run_command
    preflight_step = next(
        step for step in plan["dependency_order"] if step["id"] == "preflight_only"
    )
    assert preflight_step["status"] == "completed"


def test_plan_preview_recommends_repair_before_blocked_run() -> None:
    repair_command = "make evidence-fetch PROJECT=demo SEVERITY=degrading"
    run_command = "ztare autoresearch run --project demo --rubric demo --iters 1"
    preflight_command = run_command + " --preflight-only"

    plan = autoresearch_trace.build_autoresearch_plan_preview(
        project="demo",
        rubric="demo",
        preflight_command=preflight_command,
        run_command=run_command,
        repair_command=repair_command,
        can_run_now=False,
        blocking_missing=["out_of_loop_evidence_recovery"],
    )

    assert plan["status"] == "blocked_before_kernel_entry"
    assert plan["recommended_first_command"] == repair_command
    repair_step = next(
        step for step in plan["dependency_order"] if step["id"] == "repair_surfaces"
    )
    assert repair_step["command"] == repair_command
    assert repair_step["model_calls"] is False


def test_loop_admission_summary_does_not_overstate_mixed_receipts() -> None:
    result = autoresearch_trace._loop_admission_summary(
        {
            "latest_run_project_packet": {
                "packet_path": "full_run_packet.json",
                "packet_sha256": "a" * 64,
                "kernel_entry_sha256": "b" * 64,
                "packet_hash_verified": True,
                "packet_hash_status": "fresh",
                "kernel_entry_hash_verified": True,
                "kernel_entry_hash_status": "fresh",
            },
            "latest_preflight_only": {
                "packet": {
                    "packet_path": "older_packet.json",
                    "packet_sha256": "c" * 64,
                    "kernel_entry_sha256": "d" * 64,
                }
            },
        }
    )

    assert result["available"] is True
    assert result["receipt_count"] == 2
    assert result["packet_hash_verified"] is None
    assert result["packet_hash_statuses"] == ["fresh"]
    assert result["kernel_entry_hash_verified"] is None
    assert result["kernel_entry_hash_statuses"] == ["fresh"]


def test_loop_admission_summary_keeps_full_run_kernel_mutation_neutral() -> None:
    result = autoresearch_trace._loop_admission_summary(
        {
            "latest_run_id": 20,
            "latest_run_project_packet": {
                "packet_path": "packet.json",
                "packet_sha256": "a" * 64,
                "kernel_entry_sha256": "old",
                "packet_hash_verified": True,
                "packet_hash_status": "fresh",
                "kernel_entry_hash_verified": None,
                "kernel_entry_hash_status": "post_run_state_changed",
            },
            "latest_preflight_only": {
                "run_id": 11,
                "packet": {
                    "packet_path": "packet.json",
                    "packet_sha256": "a" * 64,
                    "kernel_entry_sha256": "older",
                    "packet_hash_verified": True,
                    "packet_hash_status": "fresh",
                    "kernel_entry_hash_verified": True,
                    "kernel_entry_hash_status": "fresh",
                },
            },
        }
    )

    assert result["available"] is True
    assert result["receipt_count"] == 1
    assert result["packet_hash_verified"] is True
    assert result["packet_hash_statuses"] == ["fresh"]
    assert result["kernel_entry_hash_verified"] is None
    assert result["kernel_entry_hash_statuses"] == ["post_run_state_changed"]


def test_loop_preflight_admitted_requires_fresh_verified_intake_and_kernel() -> None:
    assert autoresearch_trace._loop_preflight_admitted(
        {
            "available": True,
            "intake_hash_verified": True,
            "kernel_entry_hash_verified": True,
            "intake_hash_statuses": ["fresh"],
            "kernel_entry_hash_statuses": ["fresh"],
        }
    ) is True
    assert autoresearch_trace._loop_preflight_admitted(
        {
            "available": True,
            "intake_hash_verified": True,
            "kernel_entry_hash_verified": False,
            "intake_hash_statuses": ["fresh"],
            "kernel_entry_hash_statuses": ["current_kernel_entry_changed"],
        }
    ) is False


def test_loop_admission_summary_uses_newer_preflight_receipt_for_current_state() -> None:
    result = autoresearch_trace._loop_admission_summary(
        {
            "latest_run_id": 10,
            "latest_run_project_packet": {
                "packet_path": "packet.json",
                "packet_sha256": "a" * 64,
                "kernel_entry_sha256": "old",
                "packet_hash_verified": True,
                "packet_hash_status": "fresh",
                "kernel_entry_hash_verified": False,
                "kernel_entry_hash_status": "current_kernel_entry_changed",
            },
            "latest_preflight_only": {
                "run_id": 11,
                "packet": {
                    "packet_path": "packet.json",
                    "packet_sha256": "a" * 64,
                    "kernel_entry_sha256": "new",
                    "packet_hash_verified": True,
                    "packet_hash_status": "fresh",
                    "kernel_entry_hash_verified": True,
                    "kernel_entry_hash_status": "fresh",
                },
            },
        }
    )

    assert result["available"] is True
    assert result["receipt_count"] == 1
    assert result["packet_hash_verified"] is True
    assert result["packet_hash_statuses"] == ["fresh"]
    assert result["kernel_entry_hash_verified"] is True
    assert result["kernel_entry_hash_statuses"] == ["fresh"]


def test_autoresearch_trace_surfaces_latest_mutator_briefing_records(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "projects" / "demo" / "workspace"
    _write_json(
        workspace / "mutator_briefing_iter_002_records.json",
        {
            "schema_version": 1,
            "iter_index": 2,
            "records": [
                {
                    "provider": "graph_focus_receipt",
                    "record_type": "graph_focus_receipt",
                    "gap_ids": "old-gap",
                    "targets": "old_target",
                }
            ],
        },
    )
    _write_json(
        workspace / "mutator_briefing_iter_004_records.json",
        {
            "schema_version": 1,
            "iter_index": 4,
            "records": [
                {
                    "provider": "graph_focus_receipt",
                    "record_type": "graph_focus_receipt",
                    "gap_ids": "gap-a, gap-b",
                    "targets": "test_model.py, packet_elements",
                },
                {"provider": "contract_rules", "record_type": "contract_rules"},
            ],
        },
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="demo",
        repo=tmp_path,
    )

    briefing = report["surfaces"]["mutator_briefing"]
    assert briefing == {
        "available": True,
        "status": "available",
        "iter_index": 4,
        "path": "projects/demo/workspace/mutator_briefing_iter_004_records.json",
        "record_count": 2,
        "providers": ["contract_rules", "graph_focus_receipt"],
        "graph_focus_record_count": 1,
        "graph_focus_gap_ids": ["gap-a", "gap-b"],
        "graph_focus_targets": ["test_model.py", "packet_elements"],
    }
    carrier_by_surface = {row["surface"]: row for row in report["carrier_chain"]}
    assert carrier_by_surface["mutator_briefing"]["status"] == "available"
    assert carrier_by_surface["mutator_briefing"]["graph_focus_record_count"] == 1
    assert carrier_by_surface["mutator_briefing"]["graph_focus_gap_ids"] == [
        "gap-a",
        "gap-b",
    ]


def _valid_kepler_rubric() -> dict:
    return {
        "persona": "Adversarial qualitative judge.",
        "rubric_mode": "kepler",
        "fit_score_mode": "none",
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": "qualitative trace fixture",
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": "qualitative trace fixture",
        "farther_tail_region": None,
        "dimensions": [
            {"name": "Generative Yield", "weight": 100, "description": "yield"}
        ],
        "criteria": {"Generative_Yield": "yield"},
    }


def _write_launch_files(project: Path) -> None:
    (project / "project_charter.md").write_text(
        "# Project Charter\n\nBounded trace fixture.\n",
        encoding="utf-8",
    )
    (project / "thesis.md").write_text(
        "# Thesis\n\nA bounded claim can be evaluated from typed evidence.\n",
        encoding="utf-8",
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_row(project: Path, raw_name: str = "source.md") -> dict:
    text = (project / "raw" / raw_name).read_text(encoding="utf-8")
    if text.startswith("---\n") and "\n---\n" in text:
        text = text.split("\n---\n", 1)[1]
    text = text.strip()
    digest = _sha256_text(text)
    return {
        "source_id": "S001",
        "path": raw_name,
        "relative_raw_path": raw_name,
        "source_type": "source_evidence",
        "sha256": digest,
        "full_sha256": digest,
    }


def _write_compile_provenance(project: Path, raw_name: str = "source.md") -> dict:
    row = _source_row(project, raw_name)
    payload = {"source_count": 1, "sources": [row]}
    evidence_path = project / "evidence.txt"
    if evidence_path.exists():
        payload["output_path"] = str(evidence_path)
        payload["output_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    _write_json(
        project / "compiled_evidence_provenance.json",
        payload,
    )
    return row


def _write_fresh_source_surfaces(
    project: Path,
    workspace: Path,
    raw_name: str = "source.md",
) -> dict:
    row = _write_compile_provenance(project, raw_name)
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [row]})
    return row


def test_autoresearch_trace_reports_project_surfaces(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    project = repo / "projects" / "demo_trace"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "derived_constraints.json",
        {"confirmed_constraint_count": 1, "provisional_constraint_count": 2},
    )
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [
                {
                    "id": "n1",
                    "label": "Boundary",
                    "probability": 0.5,
                    "watch_signal": "boundary stress",
                },
                {"id": "n2", "label": "Source", "probability": 0.2},
            ],
            "edges": [{"from": "n1", "to": "n2", "weight": 0.8}],
        },
    )
    _write_jsonl(
        workspace / "dag_steering_log.jsonl",
        [
            {
                "selected_node_id": "n1",
                "selected_urgency": 0.4,
                "selected_probability": 0.5,
                "selected_edge_weight": 0.8,
            }
        ],
    )
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-001",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "rd",
                "iteration": 2,
                "event": "iteration score improves",
                "p_success": 0.8,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true if score improves",
                "tier": 2,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "provenance": {
                    "source_surface": "scratch_contract",
                    "mode": "out_of_loop",
                    "producer": "codex:rd",
                },
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
            }
        ],
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [
            {
                "run_id": 101,
                "iteration": 1,
                "score": 10,
                "weakest_point": "Boundary is still underspecified.",
                "timestamp": "2026-06-19T00:00:00",
            },
            {
                "run_id": 101,
                "iteration": 2,
                "score": 0,
                "raw_judge_score": 70,
                "score_cap_reason": "Global Gate Hard Fail: global_extrapolation_gap",
                "score_cap_source": "global_gates.hard_fail",
                "failed_gate_ids": ["global_extrapolation_gap"],
                "gate_failure_count": 1,
                "mutator_requested_model_id": "kimi-k2.6",
                "mutator_effective_model_ids": ["gemini-3.1-pro-preview"],
                "mutator_fallback_events": [
                    {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
                ],
                "weakest_point": "Boundary is still underspecified.",
                "timestamp": "2026-06-19T00:00:01",
            },
        ],
    )
    _write_jsonl(
        workspace / "iteration_telemetry.jsonl",
        [
            {
                "record_type": "run_start",
                "run_id": 101,
                "mutator_model": "kimi-k2.6",
                "judge_model": "grok-4.3",
                "project_packet": {
                    "packet_path": "demo_trace_packet.json",
                    "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                    "packet_status": "valid_packet",
                    "readiness": "ready_for_in_loop_candidate",
                    "kernel_entry_status": "ready",
                },
            },
            {
                "record_type": "iteration",
                "run_id": 101,
                "iteration_index": 2,
                "score": 0,
                "raw_judge_score": 70,
                "score_cap_reason": "Global Gate Hard Fail: global_extrapolation_gap",
                "score_cap_source": "global_gates.hard_fail",
                "failed_gate_ids": ["global_extrapolation_gap"],
                "gate_failure_count": 1,
                "pending_loop_action": "UNDERIDENTIFIED",
                "information_yield_rationale": "bounded discriminator hit repeated gate failures",
                "mutator_model_id": "kimi-k2.6",
                "mutator_effective_model_ids": ["gemini-3.1-pro-preview"],
                "mutator_fallback_events": [
                    {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
                ],
            },
            {
                "record_type": "run_end",
                "run_id": 101,
                "final_iteration": 2,
                "final_score": 35,
                "run_exit_reason": "budget_exhausted",
            },
            {
                "record_type": "run_start",
                "run_id": 202,
                "preflight_only": True,
                "project_packet": {
                    "packet_path": "demo_trace_packet.json",
                    "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                    "packet_status": "valid_packet",
                    "readiness": "ready_for_in_loop_candidate",
                    "kernel_entry_status": "ready",
                },
            },
            {
                "record_type": "run_end",
                "run_id": 202,
                "timestamp_utc": "2026-06-19T00:10:00Z",
                "final_iteration": 0,
                "final_score": None,
                "run_exit_reason": "preflight_only",
                "preflight_only": True,
            },
        ],
    )
    _write_json(repo / "rubrics" / "demo_trace.json", _valid_kepler_rubric())
    packet_path = repo / "demo_trace_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="demo_trace",
            rubric="demo_trace",
            task="test the demo trace boundary",
            bounded_claim="demo trace has source-bound evidence",
            source_refs=["projects/demo_trace/raw/source.md"],
            evidence_refs=["projects/demo_trace/evidence.txt"],
            non_claims=["not a full external replication"],
            next_falsifier="delete compile provenance and re-run trace",
            expected_command=(
                "ztare autoresearch route --task 'test the demo trace boundary' "
                "--project demo_trace --rubric demo_trace"
            ),
        ),
    )

    def _full_health_stub(**kwargs):
        assert kwargs["packet"] == str(packet_path)
        return {
            "summary": {"overall_status": "ok", "component_count": 8},
            "evidence_gaps": [
                {
                    "id": "fixture_gap",
                    "status": "attention",
                    "next_command": "make autoresearch-evidence-trace JSON=1",
                }
            ],
        }

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        _full_health_stub,
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="demo_trace",
        rubric="demo_trace",
        packet=str(packet_path),
        repo=repo,
        full_health=True,
    )

    assert report["status"] == "complete_trace", json.dumps(
        {
            "missing": report["missing"],
            "blocking_missing": report["blocking_missing"],
            "launch_preflight": {
                "status": report["surfaces"].get("launch_preflight_status"),
                "errors": report["surfaces"].get("launch_preflight_errors"),
                "warnings": report["surfaces"].get("launch_preflight_warnings"),
            },
        },
        sort_keys=True,
    )
    assert report["readiness"] == "ready_for_in_loop_candidate"
    assert report["readiness_canonical"] == "ready_for_in_loop_candidate"
    assert report["missing"] == []
    assert report["blocking_missing"] == []
    assert report["history_missing"] == []
    assert report["project_packet"]["status"] == "valid_packet"
    assert report["project_packet"]["ok"] is True
    assert report["project_packet"]["path"] == "demo_trace_packet.json"
    assert report["project_packet"]["source_ref_count"] == 1
    assert report["project_packet"]["evidence_ref_count"] == 1
    assert report["project_packet"]["non_claim_count"] == 1
    assert report["project_packet"]["matches_project"] is True
    assert report["project_packet"]["matches_rubric"] is True
    assert report["project_intake"]["status"] == "valid_packet"
    assert report["project_intake"]["ok"] is True
    assert report["project_intake"]["intake_path"] == "demo_trace_packet.json"
    assert report["project_intake"]["legacy_receipt_surface"] == "project_packet"
    assert report["project_packet"]["missing_ref_falsifier"] == {
        "required": True,
        "ok": True,
        "status": "passed",
        "remove_ref": "evidence_refs[1]",
        "removed_ref": "projects/demo_trace/evidence.txt",
        "expected_error_fragment": "evidence_refs[1] local path does not exist",
        "errors": [],
        "falsified_errors": [
            "evidence_refs[1] local path does not exist: "
            "__ztare_missing_falsifier__/projects/demo_trace/evidence.txt"
        ],
        "path_safety": project_packet_path_safety_policy(),
    }
    assert report["route_preview"] == {
        "available": True,
        "source": "project_intake",
        "source_name": "project_intake",
        "legacy_source": "project_packet",
        "route_command": (
            "ztare autoresearch route --task 'test the demo trace boundary' "
            "--project demo_trace --rubric demo_trace --intake demo_trace_packet.json"
        ),
        "preflight_command": (
            "ztare autoresearch run --project demo_trace --rubric demo_trace "
            "--intake demo_trace_packet.json --preflight-only"
        ),
        "run_command": (
            "ztare autoresearch run --project demo_trace --rubric demo_trace "
            "--intake demo_trace_packet.json --iters 10"
        ),
        "can_run_now": True,
    }
    assert report["plan_preview"]["schema"] == "ztare-autoresearch-plan-preview-v1"
    assert report["plan_preview"]["status"] == "ready_for_preflight"
    assert report["plan_preview"]["model_calls_before_confirmation"] is False
    assert report["plan_preview"]["recommended_first_command"] == (
        "ztare autoresearch run --project demo_trace --rubric demo_trace "
        "--intake demo_trace_packet.json --preflight-only"
    )
    assert report["plan_preview"]["budget"] == {
        "iteration_budget": "10",
        "llm_timeout_seconds": "runtime_default",
        "llm_retries": "runtime_default",
        "model_fallback_policy": "disabled_by_default",
        "provider_spend_starts_at": "bounded_loop_run",
    }
    assert [step["id"] for step in report["plan_preview"]["dependency_order"]] == [
        "route_decision",
        "preflight_only",
        "bounded_loop_run",
        "trace_health_review",
    ]
    assert report["kernel_entry"] == {
        "schema": "ztare-kernel-entry-contract-v1",
        "entry_surface": "in_loop_autoresearch",
        "project": "demo_trace",
        "rubric": "demo_trace",
        "intake_id": report["project_packet"]["packet_id"],
        "intake_path": "demo_trace_packet.json",
        "packet_id": report["project_packet"]["packet_id"],
        "packet_path": "demo_trace_packet.json",
        "status": "ready",
        "can_enter_kernel": True,
        "readiness": "ready_for_in_loop_candidate",
        "readiness_canonical": "ready_for_in_loop_candidate",
        "submission_contract": {
            "schema": "ztare-launch-contract-summary-v1",
            "submission_contract_kind": "numeric_model",
            "expected_submission_surface": "numeric I_model submission",
            "requires_i_model": True,
            "rubric_mode": "kepler",
            "falsification_mode": None,
            "fit_score_mode": "none",
            "enable_fit_primitive": True,
            "enable_fit_primitive_features": False,
            "holdout_hard_gate": False,
            "cage_meta_class": None,
            "registered_substrate_abi": None,
            "registered_signature": None,
            "theorem_required_functions": [],
            "numeric_cross_class_diagnostic_eligible": False,
        },
        "allowed_work_modes": ["inspection_only", "in_loop_autoresearch_gate"],
        "disallowed_work_modes": [
            "rd_out_of_loop_execution",
            "untyped_source_to_kernel_entry",
            "project_prep_queue_as_research_execution",
        ],
        "prerequisites": {
            "project_intake_ok": True,
            "project_intake_matches_project": True,
            "project_intake_matches_rubric": True,
            "project_packet_ok": True,
            "project_packet_matches_project": True,
            "project_packet_matches_rubric": True,
            "missing_ref_falsifier_ok": True,
            "source_preflight_ok": True,
            "source_preflight_status": "ready_for_evidence_prepare",
            "source_evidence_count": 1,
            "launch_preflight_ok": True,
            "launch_preflight_status": "ok",
            "submission_contract_kind": "numeric_model",
            "requires_i_model": True,
            "registered_substrate_abi": None,
        },
        "blockers": [],
        "history_debt": [],
        "in_loop_focus_receipts": report["graph_rd_actions"],
        "withheld_in_loop_focus_receipts": [],
        "entry_command": (
            "ztare autoresearch route --task 'test the demo trace boundary' "
            "--project demo_trace --rubric demo_trace --intake demo_trace_packet.json"
        ),
        "preflight_command": (
            "ztare autoresearch run --project demo_trace --rubric demo_trace "
            "--intake demo_trace_packet.json --preflight-only"
        ),
        "run_command": (
            "ztare autoresearch run --project demo_trace --rubric demo_trace "
            "--intake demo_trace_packet.json --iters 10"
        ),
        "inspection_command": (
            "ztare autoresearch trace --project demo_trace --rubric demo_trace "
            "--intake demo_trace_packet.json --json"
        ),
    }
    assert report["rubric_path"].endswith("rubrics/demo_trace.json")
    assert [row["surface"] for row in report["carrier_chain"]] == [
        "project_dir",
        "raw_sources",
        "source_preflight",
        "source_index",
        "source_index_receipt",
        "compile_provenance",
        "evidence_output",
        "evidence_replay",
        "claim_support",
        "evidence_gaps",
        "project_intake",
        "launch_preflight",
        "mutator_briefing",
        "prediction_contracts",
        "eval_history",
        "loop_admission",
    ]
    carrier_by_surface = {row["surface"]: row for row in report["carrier_chain"]}
    assert carrier_by_surface["source_preflight"]["status"] == "ready_for_evidence_prepare"
    assert carrier_by_surface["source_index"]["status"] == "fresh"
    assert carrier_by_surface["source_index_receipt"]["status"] == "missing"
    assert carrier_by_surface["source_index_receipt"]["blocking"] is False
    assert carrier_by_surface["source_index_receipt"]["next_command"] == (
        "ztare project source-index --project demo_trace"
    )
    assert carrier_by_surface["compile_provenance"]["status"] == "fresh"
    assert carrier_by_surface["evidence_output"]["status"] == "fresh"
    assert carrier_by_surface["evidence_gaps"]["status"] == "no_strategy_change"
    assert carrier_by_surface["project_intake"]["status"] == "valid_packet"
    assert carrier_by_surface["project_intake"]["legacy_surface"] == "project_packet"
    assert carrier_by_surface["launch_preflight"]["status"] == "ok"
    assert carrier_by_surface["mutator_briefing"]["status"] == "missing"
    assert carrier_by_surface["mutator_briefing"]["graph_focus_record_count"] == 0
    assert carrier_by_surface["prediction_contracts"]["status"] == (
        "scoreable_measurement_lane"
    )
    assert carrier_by_surface["prediction_contracts"]["blocking"] is False
    assert carrier_by_surface["prediction_contracts"]["row_count"] == 1
    assert carrier_by_surface["prediction_contracts"]["scoreable_count"] == 1
    assert carrier_by_surface["prediction_contracts"]["measurement_policy"] == (
        "score_only_no_routing"
    )
    assert carrier_by_surface["loop_admission"]["status"] == "available"
    assert not any(row["blocking"] for row in report["carrier_chain"])
    assert report["surfaces"]["raw_file_count"] == 1
    assert report["surfaces"]["evidence_exists"] is True
    assert report["surfaces"]["evidence_sha256"]
    assert report["surfaces"]["compile_provenance_exists"] is True
    assert report["surfaces"]["compile_provenance_path"].endswith(
        "compiled_evidence_provenance.json"
    )
    assert report["surfaces"]["compile_source_count"] == 1
    assert report["surfaces"]["workspace_meta_exists"] is True
    assert report["surfaces"]["workspace_merge_status"] == "success"
    assert report["surfaces"]["workspace_source_count"] == 1
    assert report["surfaces"]["source_index_exists"] is True
    assert report["surfaces"]["source_index_count"] == 1
    assert report["surfaces"]["launch_preflight_ok"] is True
    assert report["surfaces"]["launch_preflight_status"] == "ok"
    assert report["surfaces"]["launch_submission_contract_kind"] == "numeric_model"
    assert report["surfaces"]["launch_requires_i_model"] is True
    assert report["surfaces"]["launch_registered_substrate_abi"] is None
    assert report["surfaces"]["mutator_briefing"]["status"] == "missing"
    assert report["surfaces"]["confirmed_constraint_count"] == 1
    assert report["surfaces"]["provisional_constraint_count"] == 2
    assert report["surfaces"]["eval_history_rows"] == 2
    assert report["recent_loop"] == {
        "available": True,
        "eval_history_rows": 2,
        "telemetry_iteration_rows": 1,
        "latest_run_id": 101,
        "latest_run_project_packet": {
            "packet_path": "demo_trace_packet.json",
            "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
            "packet_status": "valid_packet",
            "readiness": "ready_for_in_loop_candidate",
            "kernel_entry_status": "ready",
        },
        "latest_run_project_intake": {
            "packet_path": "demo_trace_packet.json",
            "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
            "packet_status": "valid_packet",
            "readiness": "ready_for_in_loop_candidate",
            "kernel_entry_status": "ready",
            "intake_id": "demo_trace:packet:2026-06-20T00:00:00Z",
            "intake_path": "demo_trace_packet.json",
            "intake_status": "valid_packet",
            "legacy_receipt_surface": "project_packet",
        },
        "current_project_intake_admission": {
            "source": "latest_preflight_only",
            "run_id": 202,
            "intake": {
                "packet_path": "demo_trace_packet.json",
                "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_in_loop_candidate",
                "kernel_entry_status": "ready",
                "admission_source": "latest_preflight_only",
                "admission_run_id": 202,
                "current_admission": True,
                "intake_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "intake_path": "demo_trace_packet.json",
                "intake_status": "valid_packet",
                "legacy_receipt_surface": "project_packet",
            },
            "legacy_project_packet": {
                "packet_path": "demo_trace_packet.json",
                "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_in_loop_candidate",
                "kernel_entry_status": "ready",
                "admission_source": "latest_preflight_only",
                "admission_run_id": 202,
                "current_admission": True,
            },
        },
        "latest_iteration": 2,
        "latest_score": 0,
        "latest_raw_judge_score": 70,
        "latest_score_delta_from_raw": 70,
        "latest_score_cap_reason": "Global Gate Hard Fail: global_extrapolation_gap",
        "latest_score_cap_source": "global_gates.hard_fail",
        "latest_run_final_score": 35,
        "latest_run_exit_reason": "budget_exhausted",
        "latest_preflight_only": {
            "run_id": 202,
            "run_exit_reason": "preflight_only",
            "timestamp_utc": "2026-06-19T00:10:00Z",
            "packet": {
                "packet_path": "demo_trace_packet.json",
                "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_in_loop_candidate",
                "kernel_entry_status": "ready",
            },
            "intake": {
                "packet_path": "demo_trace_packet.json",
                "packet_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "packet_status": "valid_packet",
                "readiness": "ready_for_in_loop_candidate",
                "kernel_entry_status": "ready",
                "intake_id": "demo_trace:packet:2026-06-20T00:00:00Z",
                "intake_path": "demo_trace_packet.json",
                "intake_status": "valid_packet",
                "legacy_receipt_surface": "project_packet",
            },
        },
        "latest_score_is_gate_zeroed": True,
        "latest_failed_gate_ids": ["global_extrapolation_gap"],
        "latest_pending_loop_action": "UNDERIDENTIFIED",
        "latest_information_yield_rationale": (
            "bounded discriminator hit repeated gate failures"
        ),
        "recent_gate_zeroed_count": 1,
        "latest_mutator_requested_model_id": "kimi-k2.6",
        "latest_mutator_effective_model_ids": ["gemini-3.1-pro-preview"],
        "latest_mutator_fallback_events": [
            {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
        ],
        "latest_provider_fallback_observed": True,
        "latest_provider_failure_signature": None,
        "latest_provider_failure_observed": False,
        "recent_mutator_requested_model_ids": ["kimi-k2.6"],
        "recent_mutator_effective_model_ids": ["gemini-3.1-pro-preview"],
        "recent_mutator_fallback_events": [
            {"from": "kimi-k2.6", "to": "gemini-3.1-pro-preview"}
        ],
        "provider_fallback_observed": True,
        "recent_provider_failure_signatures": [],
        "provider_failure_observed": False,
        "next_command": (
            "ztare autoresearch hillclimb-audit --project demo_trace "
            "--recovery-queue --recovery-limit 10 --json"
        ),
    }
    assert report["projection"]["available"] is True
    assert report["projection"]["node_count"] == 2
    assert report["projection"]["rejected_count"] == 1
    assert report["projection"]["negative_constraint_count"] == 1
    assert report["graph_carriers"] == [
        {
            "graph_id": "demo_trace:latest_probability_dag",
            "graph_kind": "probability_dag",
            "source_artifacts": ["projects/demo_trace/latest_probability_dag.json"],
            "node_count": 2,
            "edge_count": 1,
                "decision_receipt": {
                    "effect": "strategy_change",
                    "selected_next_discriminator": (
                        "DAG steering selected node 'n1' as the next focus"
                    ),
                    "runtime_consumable": True,
                },
            "validation": {"ok": True, "errors": [], "warnings": []},
        },
        {
            "graph_id": "demo_trace:source_claim_graph",
            "graph_kind": "source_claim_graph",
            "source_artifacts": [
                "projects/demo_trace/workspace/source_index.json",
                "projects/demo_trace/evidence.txt",
                "projects/demo_trace/compiled_evidence_provenance.json",
            ],
            "node_count": 2,
            "edge_count": 1,
            "decision_receipt": {
                "effect": "no_strategy_change",
                "reason": "source/evidence chain present with no active evidence gaps",
            },
            "validation": {"ok": True, "errors": [], "warnings": []},
        },
    ]
    assert [_without_graph_card_provenance(row) for row in report["graph_rd_actions"]] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "demo_trace",
            "graph_id": "demo_trace:latest_probability_dag",
            "reason": "DAG steering selected node 'n1' as the next focus",
            "recommended_actor": "autoresearch_loop",
        }
    ]
    assert report["prediction_summary"] == {
        "available": True,
        "status": "scoreable_measurement_lane",
        "source_artifact": "projects/demo_trace/workspace/iteration_predictions.jsonl",
        "row_count": 1,
        "valid_count": 1,
        "invalid_count": 0,
        "sealed_count": 1,
        "unresolved_count": 0,
        "resolved_count": 1,
        "scoreable_count": 1,
        "mean_brier": 0.04,
        "mean_uniform_brier": 0.25,
        "beats_uniform_baseline": True,
        "source_surfaces": {"scratch_contract": 1},
        "provenance_modes": {"out_of_loop": 1},
        "producers": {"codex:rd": 1},
        "certified_count": 0,
        "excluded_from_calibration_count": 0,
        "membrane_eligible_count": 0,
        "authority": {
            "score_authority": "scoreable_binary_brier_rows",
            "calibration_authority": "not_calibration_authority",
            "membrane_authority": "not_membrane_evidence",
            "routing_authority": "none_trace_does_not_route_work",
            "decision_use_required_for_routing": True,
        },
        "measurement_policy": "score_only_no_routing",
        "issues": [],
    }
    assert report["health_summary"] == {"overall_status": "ok", "component_count": 8}
    assert report["health_evidence_gaps"] == [
        {
            "id": "fixture_gap",
            "status": "attention",
            "recovery_kind": None,
            "recovery_channel": None,
            "next_command": "make autoresearch-evidence-trace JSON=1",
        }
    ]
    assert report["recovery_actions"] == []
    assert report["next_commands"][0] == (
        "ztare autoresearch route --task 'test the demo trace boundary' "
        "--project demo_trace --rubric demo_trace --intake demo_trace_packet.json"
    )
    assert report["next_commands"][1] == (
        "ztare autoresearch run --project demo_trace --rubric demo_trace "
        "--intake demo_trace_packet.json --preflight-only"
    )
    assert report["next_commands"][2] == (
        "ztare autoresearch run --project demo_trace --rubric demo_trace "
        "--intake demo_trace_packet.json --iters 10"
    )
    assert report["next_commands"][-1] == (
        "ztare autoresearch health --project demo_trace --rubric demo_trace "
        "--intake demo_trace_packet.json --json"
    )


def test_autoresearch_trace_blocks_stale_source_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_trace"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\ncurrent source\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    stale_source = {
        "source_id": "S001",
        "path": "source.md",
        "kind": "md",
        "source_type": "source_evidence",
        "sha256": _sha256_text("old source"),
        "chars_used": 10,
        "truncated": False,
    }
    _write_json(
        project / "compiled_evidence_provenance.json",
        {"source_count": 1, "sources": [stale_source]},
    )
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [stale_source]})
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "stale sources"}],
    )
    _write_json(repo / "rubrics" / "stale_trace.json", _valid_kepler_rubric())
    packet_path = repo / "stale_trace_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_trace",
            rubric="stale_trace",
            task="test stale source metadata",
            bounded_claim="loop entry requires fresh source artifacts",
            source_refs=["projects/stale_trace/raw/source.md"],
            evidence_refs=["projects/stale_trace/evidence.txt"],
            non_claims=["not ready while evidence artifacts are stale"],
            next_falsifier="change the raw source body and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale source metadata' "
                "--project stale_trace --rubric stale_trace"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_trace",
        rubric="stale_trace",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_index_stale", "evidence_compile_stale"]
    assert report["blocking_missing"] == ["source_index_stale", "evidence_compile_stale"]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "source_index_stale",
            "recovery_channel": "project_surface",
            "next_command": "ztare project source-index --project stale_trace",
        },
            {
                "id": "evidence_compile_stale",
                "recovery_channel": "evidence_prepare",
                "next_command": "make evidence-prepare PROJECT=stale_trace",
            },
    ]
    assert report["route_preview"]["can_run_now"] is False
    assert report["surfaces"]["source_preflight_ok"] is True
    assert report["surfaces"]["source_index_freshness"]["status"] == "stale"
    assert report["surfaces"]["source_index_freshness"]["hash_mismatches"] == [
        "source.md"
    ]
    assert report["surfaces"]["evidence_compile_freshness"]["status"] == "stale"
    assert report["surfaces"]["evidence_compile_freshness"]["hash_mismatches"] == [
        "source.md"
    ]
    assert report["recovery_actions"] == [
        {
            "id": "source_index",
            "reason": (
                "write deterministic workspace source index and metadata "
                "from typed raw sources"
            ),
            "next_command": "ztare project source-index --project stale_trace",
        },
        {
            "id": "evidence_prepare",
            "reason": "refresh workspace source index and compiled evidence from raw sources",
            "next_command": "make evidence-prepare PROJECT=stale_trace",
        }
    ]
    assert report["next_commands"][0] == (
        "ztare project source-index --project stale_trace"
    )
    assert report["next_commands"][1] == (
        "make evidence-prepare PROJECT=stale_trace"
    )
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_count_only_compile_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "count_only_compile"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source_row = _source_row(project)
    _write_json(project / "compiled_evidence_provenance.json", {"source_count": 1})
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 8, "weakest_point": "count-only compile"}],
    )
    _write_json(repo / "rubrics" / "count_only_compile.json", _valid_kepler_rubric())
    packet_path = repo / "count_only_compile_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="count_only_compile",
            rubric="count_only_compile",
            task="test count-only compile provenance",
            bounded_claim="kernel entry requires source-bound compile provenance",
            source_refs=["projects/count_only_compile/raw/source.md"],
            evidence_refs=["projects/count_only_compile/evidence.txt"],
            non_claims=["not ready on source counts alone"],
            next_falsifier="remove compiled provenance sources and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test count-only compile provenance' "
                "--project count_only_compile --rubric count_only_compile"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="count_only_compile",
        rubric="count_only_compile",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["evidence_compile_unverified"]
    assert report["blocking_missing"] == ["evidence_compile_unverified"]
    assert report["kernel_entry"]["blockers"] == [
            {
                "id": "evidence_compile_unverified",
                "recovery_channel": "evidence_prepare",
                "next_command": "make evidence-prepare PROJECT=count_only_compile",
            }
    ]
    assert report["surfaces"]["evidence_compile_freshness"]["status"] == (
        "unverified_no_artifact_sources"
    )
    assert report["recovery_actions"] == [
        {
            "id": "evidence_prepare",
            "reason": "refresh workspace source index and compiled evidence from raw sources",
            "next_command": "make evidence-prepare PROJECT=count_only_compile",
        }
    ]
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_unhashed_compiled_evidence_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "unhashed_evidence"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source_row = _source_row(project)
    _write_json(
        project / "compiled_evidence_provenance.json",
        {"source_count": 1, "sources": [source_row]},
    )
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 8, "weakest_point": "unhashed output"}],
    )
    _write_json(repo / "rubrics" / "unhashed_evidence.json", _valid_kepler_rubric())
    packet_path = repo / "unhashed_evidence_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="unhashed_evidence",
            rubric="unhashed_evidence",
            task="test unhashed compiled evidence output",
            bounded_claim="kernel entry requires output-bound compile provenance",
            source_refs=["projects/unhashed_evidence/raw/source.md"],
            evidence_refs=["projects/unhashed_evidence/evidence.txt"],
            non_claims=["not ready on source hashes alone"],
            next_falsifier="remove output_sha256 and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test unhashed compiled evidence output' "
                "--project unhashed_evidence --rubric unhashed_evidence"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="unhashed_evidence",
        rubric="unhashed_evidence",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["evidence_output_unverified"]
    assert report["blocking_missing"] == ["evidence_output_unverified"]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "evidence_output_unverified",
            "recovery_channel": "evidence_output_bind",
            "next_command": "ztare project evidence-bind --project unhashed_evidence --json",
        }
    ]
    assert report["surfaces"]["evidence_output_binding"]["status"] == (
        "unverified_missing_output_hash"
    )
    assert report["recovery_actions"] == [
        {
            "id": "evidence_output_bind",
            "reason": (
                "bind current rendered evidence output bytes to fresh compile "
                "provenance without recompiling evidence"
            ),
            "next_command": "ztare project evidence-bind --project unhashed_evidence --json",
        }
    ]


def test_autoresearch_trace_accepts_unhashed_compiled_evidence_with_binding_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "bound_unhashed_evidence"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source_row = _source_row(project)
    _write_json(
        project / "compiled_evidence_provenance.json",
        {"source_count": 1, "sources": [source_row], "output_path": "evidence.txt"},
    )
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 8, "weakest_point": "legacy output hash"}],
    )
    _write_json(
        repo / "rubrics" / "bound_unhashed_evidence.json",
        _valid_kepler_rubric(),
    )
    write_evidence_output_binding_receipt(project_dir=project, repo=repo)
    packet_path = repo / "bound_unhashed_evidence_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="bound_unhashed_evidence",
            rubric="bound_unhashed_evidence",
            task="test output binding receipt",
            bounded_claim="kernel entry accepts receipt-bound legacy compiled evidence",
            source_refs=["projects/bound_unhashed_evidence/raw/source.md"],
            evidence_refs=["projects/bound_unhashed_evidence/evidence.txt"],
            non_claims=["not evidence that compilation was rerun"],
            next_falsifier="edit evidence.txt after receipt and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test output binding receipt' "
                "--project bound_unhashed_evidence --rubric bound_unhashed_evidence"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="bound_unhashed_evidence",
        rubric="bound_unhashed_evidence",
        packet=str(packet_path),
        repo=repo,
    )

    assert "evidence_output_unverified" not in report["missing"]
    assert "evidence_output_stale" not in report["missing"]
    binding = report["surfaces"]["evidence_output_binding"]
    assert binding["status"] == "fresh"
    assert binding["verified"] is True
    assert binding["binding_source"] == "evidence_output_binding_receipt"
    assert binding["legacy_output_hash_binding"] is True
    assert binding["receipt"]["verified"] is True


def test_autoresearch_trace_blocks_stale_output_binding_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_bound_unhashed_evidence"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source_row = _source_row(project)
    _write_json(
        project / "compiled_evidence_provenance.json",
        {"source_count": 1, "sources": [source_row], "output_path": "evidence.txt"},
    )
    _write_json(
        workspace / "workspace_meta.json",
        {"merge_status": "success", "source_count": 1},
    )
    _write_json(workspace / "source_index.json", {"sources": [source_row]})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 8, "weakest_point": "legacy output hash"}],
    )
    _write_json(
        repo / "rubrics" / "stale_bound_unhashed_evidence.json",
        _valid_kepler_rubric(),
    )
    write_evidence_output_binding_receipt(project_dir=project, repo=repo)
    (project / "evidence.txt").write_text("Edited evidence packet\n", encoding="utf-8")
    packet_path = repo / "stale_bound_unhashed_evidence_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_bound_unhashed_evidence",
            rubric="stale_bound_unhashed_evidence",
            task="test stale output binding receipt",
            bounded_claim="kernel entry rejects stale receipt-bound legacy evidence",
            source_refs=["projects/stale_bound_unhashed_evidence/raw/source.md"],
            evidence_refs=["projects/stale_bound_unhashed_evidence/evidence.txt"],
            non_claims=["not ready after evidence mutation"],
            next_falsifier="refresh receipt or rerun compile",
            expected_command=(
                "ztare autoresearch route --task 'test stale output binding receipt' "
                "--project stale_bound_unhashed_evidence "
                "--rubric stale_bound_unhashed_evidence"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_bound_unhashed_evidence",
        rubric="stale_bound_unhashed_evidence",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["missing"] == ["evidence_output_stale"]
    assert report["blocking_missing"] == ["evidence_output_stale"]
    binding = report["surfaces"]["evidence_output_binding"]
    assert binding["status"] == "stale"
    assert binding["verified"] is False
    assert binding["binding_source"] == "evidence_output_binding_receipt"
    assert binding["receipt"]["status"] == "stale_artifact_hash"
    assert binding["stale_artifacts"] == ["evidence_output"]


def test_autoresearch_trace_recommends_source_index_for_missing_index_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "missing_index_trace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_compile_provenance(project)
    _write_jsonl(
        project / "workspace" / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "missing index"}],
    )
    _write_json(repo / "rubrics" / "missing_index_trace.json", _valid_kepler_rubric())
    packet_path = repo / "missing_index_trace_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="missing_index_trace",
            rubric="missing_index_trace",
            task="test missing source index recovery",
            bounded_claim="source-index recovery is separate from evidence compilation",
            source_refs=["projects/missing_index_trace/raw/source.md"],
            evidence_refs=["projects/missing_index_trace/evidence.txt"],
            non_claims=["not a full evidence compiler run"],
            next_falsifier="delete source_index.json and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test missing source index recovery' "
                "--project missing_index_trace --rubric missing_index_trace"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="missing_index_trace",
        rubric="missing_index_trace",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_index", "workspace_meta"]
    assert report["blocking_missing"] == ["source_index", "workspace_meta"]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "source_index",
            "recovery_channel": "project_surface",
            "next_command": "ztare project source-index --project missing_index_trace",
        },
        {
            "id": "workspace_meta",
            "recovery_channel": "project_surface",
            "next_command": "ztare project source-index --project missing_index_trace",
        },
    ]
    assert report["recovery_actions"] == [
        {
            "id": "source_index",
            "reason": (
                "write deterministic workspace source index and metadata "
                "from typed raw sources"
            ),
            "next_command": "ztare project source-index --project missing_index_trace",
        }
    ]
    assert report["next_commands"][0] == (
        "ztare project source-index --project missing_index_trace"
    )
    assert not any("make evidence-prepare" in command for command in report["next_commands"])
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_stale_source_index_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_source_receipt"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    checkpoint_source_index(
        project_dir=project,
        raw_dir=project / "raw",
        workspace_dir=workspace,
        model_family="gemini",
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )
    receipt = json.loads((workspace / "source_index_receipt.json").read_text(encoding="utf-8"))
    receipt["source_index_sha256"] = "0" * 64
    _write_json(workspace / "source_index_receipt.json", receipt)
    _write_compile_provenance(project)
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "receipt drift"}],
    )
    _write_json(repo / "rubrics" / "stale_source_receipt.json", _valid_kepler_rubric())
    packet_path = repo / "stale_source_receipt_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_source_receipt",
            rubric="stale_source_receipt",
            task="test stale source-index receipt",
            bounded_claim="kernel entry requires current source-index receipt when present",
            source_refs=["projects/stale_source_receipt/raw/source.md"],
            evidence_refs=["projects/stale_source_receipt/evidence.txt"],
            non_claims=["not a full evidence compiler run"],
            next_falsifier="corrupt source-index receipt hash and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale source-index receipt' "
                "--project stale_source_receipt --rubric stale_source_receipt"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_source_receipt",
        rubric="stale_source_receipt",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_index_receipt_stale"]
    assert report["blocking_missing"] == ["source_index_receipt_stale"]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "source_index_receipt_stale",
            "recovery_channel": "project_surface",
            "next_command": "ztare project source-index --project stale_source_receipt",
        }
    ]
    assert report["surfaces"]["source_index_freshness"]["status"] == "fresh"
    assert report["surfaces"]["source_index_receipt"]["status"] == "stale"
    assert report["surfaces"]["source_index_receipt"]["hash_mismatches"] == [
        "source_index"
    ]
    assert report["next_commands"][0] == (
        "ztare project source-index --project stale_source_receipt"
    )
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_source_index_receipt_with_missing_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "missing_source_receipt_artifacts"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    checkpoint_source_index(
        project_dir=project,
        raw_dir=project / "raw",
        workspace_dir=workspace,
        model_family="gemini",
        max_files=10,
        max_chars_per_file=1000,
        max_total_chars=5000,
    )
    _write_compile_provenance(project)
    (workspace / "source_index.json").unlink()
    (workspace / "workspace_meta.json").unlink()
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "missing source receipt artifacts"}],
    )
    _write_json(
        repo / "rubrics" / "missing_source_receipt_artifacts.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "missing_source_receipt_artifacts_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="missing_source_receipt_artifacts",
            rubric="missing_source_receipt_artifacts",
            task="test missing source-index receipt artifacts",
            bounded_claim="kernel entry requires receipt-bound source-index artifacts to exist",
            source_refs=["projects/missing_source_receipt_artifacts/raw/source.md"],
            evidence_refs=["projects/missing_source_receipt_artifacts/evidence.txt"],
            non_claims=["not ready on receipt file alone"],
            next_falsifier="delete source_index.json after source-index and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test missing source-index receipt artifacts' "
                "--project missing_source_receipt_artifacts "
                "--rubric missing_source_receipt_artifacts"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="missing_source_receipt_artifacts",
        rubric="missing_source_receipt_artifacts",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == [
        "source_index",
        "source_index_receipt_stale",
        "workspace_meta",
    ]
    assert report["blocking_missing"] == [
        "source_index",
        "source_index_receipt_stale",
        "workspace_meta",
    ]
    receipt = report["surfaces"]["source_index_receipt"]
    assert receipt["verified"] is False
    assert receipt["status"] == "stale_missing_artifact"
    assert receipt["missing_artifacts"] == ["source_index"]
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_stale_compiled_evidence_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_evidence_output"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    original_evidence = "Evidence packet\n"
    (project / "evidence.txt").write_text(original_evidence, encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    provenance_path = project / "compiled_evidence_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["output_path"] = str(project / "evidence.txt")
    provenance["output_sha256"] = _sha256_text(original_evidence)
    _write_json(provenance_path, provenance)
    (project / "evidence.txt").write_text("Edited evidence packet\n", encoding="utf-8")
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "evidence drift"}],
    )
    _write_json(repo / "rubrics" / "stale_evidence_output.json", _valid_kepler_rubric())
    packet_path = repo / "stale_evidence_output_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_evidence_output",
            rubric="stale_evidence_output",
            task="test stale compiled evidence output",
            bounded_claim="kernel entry requires evidence bytes to match compile provenance",
            source_refs=["projects/stale_evidence_output/raw/source.md"],
            evidence_refs=["projects/stale_evidence_output/evidence.txt"],
            non_claims=["not a proof of claim truth"],
            next_falsifier="edit evidence.txt after compile and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale compiled evidence output' "
                "--project stale_evidence_output --rubric stale_evidence_output"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_evidence_output",
        rubric="stale_evidence_output",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["evidence_output_stale"]
    assert report["blocking_missing"] == ["evidence_output_stale"]
    assert report["kernel_entry"]["blockers"] == [
            {
                "id": "evidence_output_stale",
                "recovery_channel": "evidence_prepare",
                "next_command": "make evidence-prepare PROJECT=stale_evidence_output",
            }
    ]
    assert report["surfaces"]["source_index_freshness"]["status"] == "fresh"
    assert report["surfaces"]["evidence_compile_freshness"]["status"] == "fresh"
    assert report["surfaces"]["evidence_output_binding"]["status"] == "stale"
    assert report["surfaces"]["evidence_output_binding"]["hash_mismatch"] is True
    assert report["next_commands"][0] == (
        "make evidence-prepare PROJECT=stale_evidence_output"
    )
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_stale_compiled_evidence_replay_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_evidence_replay"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    original_evidence = "Evidence packet\n"
    (project / "evidence.txt").write_text(original_evidence, encoding="utf-8")
    (project / "compiled_evidence.txt").write_text(original_evidence, encoding="utf-8")
    _write_json(project / "compiled_evidence_packet.json", {"project": "stale_evidence_replay"})
    _write_json(
        workspace / "evidence_gap_action.json",
        {"schema": "ztare-evidence-gap-action-v1", "active_evidence_gap_count": 0},
    )
    _write_json(workspace / "workspace_snapshot.json", {"project": "stale_evidence_replay"})

    row = _write_fresh_source_surfaces(project, workspace)
    source_binding = {"source_count": 1, "sources": [row]}
    input_projection = {
        "source_binding": source_binding,
        "workspace_snapshot_sha256": hashlib.sha256(
            (workspace / "workspace_snapshot.json").read_bytes()
        ).hexdigest(),
    }
    support_counts = {
        "immutable_ground_truth": 0,
        "numerical_ranges_and_constraints": 0,
        "identified_contradictions": 0,
        "epistemic_voids": 0,
        "provenance": 0,
        "candidate_claims_to_test": 0,
    }
    replay_manifest_path = project / "compiled_evidence_replay_manifest.json"
    replay_manifest = {
        "schema": EVIDENCE_REPLAY_MANIFEST_SCHEMA,
        "mode": "workspace",
        "replay_mode": "workspace_snapshot_replay",
        "input_projection": input_projection,
        "input_binding_sha256": stable_json_sha256(input_projection),
        "source_binding_sha256": stable_json_sha256(source_binding),
        "support_projection_counts": support_counts,
        "support_binding_sha256": stable_json_sha256(support_counts),
        "artifact_hashes": {
            "evidence_txt": hashlib.sha256((project / "evidence.txt").read_bytes()).hexdigest(),
            "audit_copy": hashlib.sha256((project / "compiled_evidence.txt").read_bytes()).hexdigest(),
            "packet_json": hashlib.sha256(
                (project / "compiled_evidence_packet.json").read_bytes()
            ).hexdigest(),
            "evidence_gap_action": hashlib.sha256(
                (workspace / "evidence_gap_action.json").read_bytes()
            ).hexdigest(),
        },
    }
    _write_json(replay_manifest_path, replay_manifest)

    edited_evidence = "Edited evidence packet with a fresh legacy output hash\n"
    (project / "evidence.txt").write_text(edited_evidence, encoding="utf-8")
    provenance_path = project / "compiled_evidence_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["output_path"] = str(project / "evidence.txt")
    provenance["output_sha256"] = _sha256_text(edited_evidence)
    provenance["evidence_replay_manifest_path"] = str(replay_manifest_path)
    provenance["evidence_replay_manifest_sha256"] = hashlib.sha256(
        replay_manifest_path.read_bytes()
    ).hexdigest()
    provenance["support_binding_sha256"] = replay_manifest["support_binding_sha256"]
    provenance["input_binding_sha256"] = replay_manifest["input_binding_sha256"]
    _write_json(provenance_path, provenance)

    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "replay drift"}],
    )
    _write_json(repo / "rubrics" / "stale_evidence_replay.json", _valid_kepler_rubric())
    packet_path = repo / "stale_evidence_replay_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_evidence_replay",
            rubric="stale_evidence_replay",
            task="test stale compiled evidence replay",
            bounded_claim="kernel entry requires replay manifest freshness",
            source_refs=["projects/stale_evidence_replay/raw/source.md"],
            evidence_refs=["projects/stale_evidence_replay/evidence.txt"],
            non_claims=["not a proof of claim truth"],
            next_falsifier="edit evidence.txt after replay manifest and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale compiled evidence replay' "
                "--project stale_evidence_replay --rubric stale_evidence_replay"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_evidence_replay",
        rubric="stale_evidence_replay",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["missing"] == ["evidence_replay_stale"]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "evidence_replay_stale",
            "recovery_channel": "evidence_replay",
            "next_command": "ztare project evidence-replay --project stale_evidence_replay --json",
        }
    ]
    assert report["surfaces"]["evidence_output_binding"]["status"] == "fresh"
    assert report["surfaces"]["evidence_replay"]["required"] is True
    assert report["surfaces"]["evidence_replay"]["status"] == "stale_or_invalid"
    carrier_by_surface = {row["surface"]: row for row in report["carrier_chain"]}
    assert carrier_by_surface["evidence_replay"]["blocking"] is True
    assert report["next_commands"][0] == (
        "ztare project evidence-replay --project stale_evidence_replay --json"
    )
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_stale_compiled_evidence_audit_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_evidence_audit_copy"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    evidence_text = "Evidence packet\n"
    audit_text = "Audit copy\n"
    packet_text = '{"project": "stale_evidence_audit_copy"}\n'
    (project / "evidence.txt").write_text(evidence_text, encoding="utf-8")
    (project / "compiled_evidence.txt").write_text(audit_text, encoding="utf-8")
    (project / "compiled_evidence_packet.json").write_text(packet_text, encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    provenance_path = project / "compiled_evidence_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.update(
        {
            "output_path": str(project / "evidence.txt"),
            "output_sha256": _sha256_text(evidence_text),
            "audit_copy_path": str(project / "compiled_evidence.txt"),
            "audit_copy_sha256": _sha256_text(audit_text),
            "packet_output_path": str(project / "compiled_evidence_packet.json"),
            "packet_output_sha256": _sha256_text(packet_text),
        }
    )
    _write_json(provenance_path, provenance)
    (project / "compiled_evidence.txt").write_text("Edited audit copy\n", encoding="utf-8")
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "evidence audit drift"}],
    )
    _write_json(
        repo / "rubrics" / "stale_evidence_audit_copy.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "stale_evidence_audit_copy_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_evidence_audit_copy",
            rubric="stale_evidence_audit_copy",
            task="test stale compiled evidence audit copy",
            bounded_claim="kernel entry binds compiled evidence audit copy bytes",
            source_refs=["projects/stale_evidence_audit_copy/raw/source.md"],
            evidence_refs=["projects/stale_evidence_audit_copy/evidence.txt"],
            non_claims=["not a proof of claim truth"],
            next_falsifier="edit compiled_evidence.txt after compile and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale compiled evidence audit copy' "
                "--project stale_evidence_audit_copy --rubric stale_evidence_audit_copy"
            ),
        ),
    )
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_evidence_audit_copy",
        rubric="stale_evidence_audit_copy",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["blocking_missing"] == ["evidence_output_stale"]
    binding = report["surfaces"]["evidence_output_binding"]
    assert binding["status"] == "stale"
    assert binding["stale_artifacts"] == ["audit_copy"]
    by_artifact = {row["artifact_id"]: row for row in binding["artifact_bindings"]}
    assert by_artifact["evidence_output"]["verified"] is True
    assert by_artifact["audit_copy"]["hash_mismatch"] is True
    assert by_artifact["packet_output"]["verified"] is True
    assert report["kernel_entry"]["can_enter_kernel"] is False


def test_autoresearch_trace_blocks_stale_compiled_evidence_packet_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_evidence_packet_output"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    evidence_text = "Evidence packet\n"
    audit_text = "Evidence packet\n"
    packet_text = '{"project": "stale_evidence_packet_output"}\n'
    (project / "evidence.txt").write_text(evidence_text, encoding="utf-8")
    (project / "compiled_evidence.txt").write_text(audit_text, encoding="utf-8")
    (project / "compiled_evidence_packet.json").write_text(packet_text, encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    provenance_path = project / "compiled_evidence_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.update(
        {
            "output_path": str(project / "evidence.txt"),
            "output_sha256": _sha256_text(evidence_text),
            "audit_copy_path": str(project / "compiled_evidence.txt"),
            "audit_copy_sha256": _sha256_text(audit_text),
            "packet_output_path": str(project / "compiled_evidence_packet.json"),
            "packet_output_sha256": _sha256_text(packet_text),
        }
    )
    _write_json(provenance_path, provenance)
    (project / "compiled_evidence_packet.json").write_text(
        '{"project": "edited"}\n',
        encoding="utf-8",
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 7, "weakest_point": "evidence packet drift"}],
    )
    _write_json(
        repo / "rubrics" / "stale_evidence_packet_output.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "stale_evidence_packet_output_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_evidence_packet_output",
            rubric="stale_evidence_packet_output",
            task="test stale compiled evidence packet output",
            bounded_claim="kernel entry binds compiled evidence packet bytes",
            source_refs=["projects/stale_evidence_packet_output/raw/source.md"],
            evidence_refs=["projects/stale_evidence_packet_output/evidence.txt"],
            non_claims=["not a proof of claim truth"],
            next_falsifier="edit compiled_evidence_packet.json after compile and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test stale compiled evidence packet output' "
                "--project stale_evidence_packet_output --rubric stale_evidence_packet_output"
            ),
        ),
    )
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_evidence_packet_output",
        rubric="stale_evidence_packet_output",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["blocking_missing"] == ["evidence_output_stale"]
    binding = report["surfaces"]["evidence_output_binding"]
    assert binding["status"] == "stale"
    assert binding["stale_artifacts"] == ["packet_output"]
    by_artifact = {row["artifact_id"]: row for row in binding["artifact_bindings"]}
    assert by_artifact["evidence_output"]["verified"] is True
    assert by_artifact["audit_copy"]["verified"] is True
    assert by_artifact["packet_output"]["hash_mismatch"] is True
    assert report["kernel_entry"]["can_enter_kernel"] is False


def test_autoresearch_trace_default_health_is_bounded(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    project = repo / "projects" / "bounded_trace"
    raw = project / "raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )

    def fail_full_health(**_kwargs):
        raise AssertionError("aggregate health should require full_health=True")

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        fail_full_health,
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="bounded_trace",
        repo=repo,
    )

    assert report["health_summary"]["mode"] == "trace_local"
    assert report["health_summary"]["component_count"] == 1


def test_autoresearch_trace_keeps_predictions_measurement_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "prediction_only"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 7,
                "weakest_point": "source boundary",
                "timestamp": "2026-06-19T00:00:00",
            }
        ],
    )
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-strong",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "codex:rd",
                "event": "next iteration closes evidence gap",
                "p_success": 0.95,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true iff evidence gaps are empty",
                "tier": 1,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
            }
        ],
    )
    _write_json(repo / "rubrics" / "prediction_only.json", _valid_kepler_rubric())
    packet_path = repo / "prediction_only_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="prediction_only",
            rubric="prediction_only",
            task="test the prediction-only trace boundary",
            bounded_claim="prediction-only trace has source-bound evidence",
            source_refs=["projects/prediction_only/raw/source.md"],
            evidence_refs=["projects/prediction_only/evidence.txt"],
            non_claims=["not a forecast-driven scheduler"],
            next_falsifier="delete the source index and re-run trace",
            expected_command=(
                "ztare autoresearch route --task 'test the prediction-only trace boundary' "
                "--project prediction_only --rubric prediction_only"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {
            "summary": {"overall_status": "ok", "component_count": 8},
            "evidence_gaps": [],
        },
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="prediction_only",
        rubric="prediction_only",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["prediction_summary"]["available"] is True
    assert report["prediction_summary"]["status"] == "scoreable_measurement_lane"
    assert report["prediction_summary"]["measurement_policy"] == "score_only_no_routing"
    assert report["graph_carriers"] == [
        {
            "graph_id": "prediction_only:source_claim_graph",
            "graph_kind": "source_claim_graph",
            "source_artifacts": [
                "projects/prediction_only/workspace/source_index.json",
                "projects/prediction_only/evidence.txt",
                "projects/prediction_only/compiled_evidence_provenance.json",
            ],
            "node_count": 2,
            "edge_count": 1,
            "decision_receipt": {
                "effect": "no_strategy_change",
                "reason": "source/evidence chain present with no active evidence gaps",
            },
            "validation": {"ok": True, "errors": [], "warnings": []},
        }
    ]
    assert report["graph_rd_actions"] == []
    assert report["recovery_actions"] == []
    assert report["next_commands"][:3] == [
        (
            "ztare autoresearch route --task 'test the prediction-only trace boundary' "
            "--project prediction_only --rubric prediction_only --intake prediction_only_packet.json"
        ),
        (
            "ztare autoresearch run --project prediction_only --rubric prediction_only "
            "--intake prediction_only_packet.json --preflight-only"
        ),
        (
            "ztare autoresearch run --project prediction_only --rubric prediction_only "
            "--intake prediction_only_packet.json --iters 10"
        ),
    ]
    assert all("forecast" not in command.lower() for command in report["next_commands"])
    assert all("brier" not in command.lower() for command in report["next_commands"])
    assert any("ztare autoresearch projection" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_invalid_prediction_authority_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "prediction_spoof"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 7,
                "weakest_point": "source boundary",
                "timestamp": "2026-06-19T00:00:00",
            }
        ],
    )
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-spoof",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "codex:rd",
                "event": "next iteration closes evidence gap",
                "p_success": 0.95,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true iff evidence gaps are empty",
                "tier": 1,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
                "provenance": {
                    "source_surface": "forecast_pool",
                    "mode": "forecast_pool",
                    "producer": "codex:rd",
                    "certified": True,
                    "can_satisfy_membrane": True,
                },
            }
        ],
    )
    _write_json(repo / "rubrics" / "prediction_spoof.json", _valid_kepler_rubric())
    packet_path = repo / "prediction_spoof_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="prediction_spoof",
            rubric="prediction_spoof",
            task="test the prediction authority boundary",
            bounded_claim="prediction authority trace has source-bound evidence",
            source_refs=["projects/prediction_spoof/raw/source.md"],
            evidence_refs=["projects/prediction_spoof/evidence.txt"],
            non_claims=["not a forecast-driven scheduler"],
            next_falsifier="delete the source index and re-run trace",
            expected_command=(
                "ztare autoresearch route --task 'test the prediction authority boundary' "
                "--project prediction_spoof --rubric prediction_spoof"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {
            "summary": {"overall_status": "ok", "component_count": 8},
            "evidence_gaps": [],
        },
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="prediction_spoof",
        rubric="prediction_spoof",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert report["missing"] == ["prediction_authority_claim_invalid"]
    assert report["blocking_missing"] == ["prediction_authority_claim_invalid"]
    carrier_by_surface = {row["surface"]: row for row in report["carrier_chain"]}
    assert carrier_by_surface["prediction_contracts"] == {
        "surface": "prediction_contracts",
        "status": "needs_attention",
        "blocking": True,
        "row_count": 1,
        "scoreable_count": 0,
        "measurement_policy": "score_only_no_routing",
        "next_command": "ztare audit forecast-capability --json",
    }
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "prediction_authority_claim_invalid",
            "recovery_channel": "prediction_contracts",
            "next_command": "ztare audit forecast-capability --json",
        }
    ]
    assert {issue["code"] for issue in report["prediction_summary"]["issues"]} == {
        "missing_forecast_pool_authority_anchor",
        "invalid_certification_claim",
        "invalid_membrane_claim",
    }
    assert report["recovery_actions"] == [
        {
            "id": "prediction_authority_claim_invalid",
            "reason": (
                "prediction rows claim forecast-pool, membrane, or routing "
                "authority but fail authority checks: "
                "missing_forecast_pool_authority_anchor, invalid_certification_claim, "
                "invalid_membrane_claim"
            ),
            "next_command": "ztare audit forecast-capability --json",
        }
    ]


def test_autoresearch_trace_blocks_prediction_routing_spoof(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "prediction_route_spoof"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [
            {
                "iteration": 1,
                "score": 7,
                "weakest_point": "source boundary",
                "timestamp": "2026-06-19T00:00:00",
            }
        ],
    )
    _write_jsonl(
        workspace / "iteration_predictions.jsonl",
        [
            {
                "prediction_id": "P-route-spoof",
                "predicted_at": "2026-06-19T00:00:00Z",
                "predictor": "codex:rd",
                "event": "next iteration closes evidence gap",
                "p_success": 0.95,
                "horizon": "next iteration",
                "resolution_rule": "actual_success is true iff evidence gaps are empty",
                "tier": 1,
                "sealed_at": "2026-06-19T00:00:01Z",
                "sealed_inputs_sha256": "a" * 64,
                "resolved_at": "2026-06-19T00:05:00Z",
                "actual_success": True,
                "routing_authority": "invoke_autoresearch",
                "route_autoresearch": True,
                "decision_use_required_for_routing": False,
            }
        ],
    )
    _write_json(repo / "rubrics" / "prediction_route_spoof.json", _valid_kepler_rubric())
    packet_path = repo / "prediction_route_spoof_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="prediction_route_spoof",
            rubric="prediction_route_spoof",
            task="test the prediction routing boundary",
            bounded_claim="prediction routing trace has source-bound evidence",
            source_refs=["projects/prediction_route_spoof/raw/source.md"],
            evidence_refs=["projects/prediction_route_spoof/evidence.txt"],
            non_claims=["not a forecast-driven scheduler"],
            next_falsifier="delete the source index and re-run trace",
            expected_command=(
                "ztare autoresearch route --task 'test the prediction routing boundary' "
                "--project prediction_route_spoof --rubric prediction_route_spoof"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {
            "summary": {"overall_status": "ok", "component_count": 8},
            "evidence_gaps": [],
        },
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="prediction_route_spoof",
        rubric="prediction_route_spoof",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert report["missing"] == ["prediction_authority_claim_invalid"]
    assert report["blocking_missing"] == ["prediction_authority_claim_invalid"]
    carrier_by_surface = {row["surface"]: row for row in report["carrier_chain"]}
    assert carrier_by_surface["prediction_contracts"]["blocking"] is True
    assert carrier_by_surface["prediction_contracts"]["next_command"] == (
        "ztare audit forecast-capability --json"
    )
    assert {issue["code"] for issue in report["prediction_summary"]["issues"]} == {
        "invalid_routing_authority_claim",
        "invalid_decision_use_bypass_claim",
    }
    assert report["recovery_actions"] == [
        {
            "id": "prediction_authority_claim_invalid",
            "reason": (
                "prediction rows claim forecast-pool, membrane, or routing "
                "authority but fail authority checks: "
                "invalid_routing_authority_claim, invalid_decision_use_bypass_claim"
            ),
            "next_command": "ztare audit forecast-capability --json",
        }
    ]
    assert not any("ztare autoresearch run" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_missing_source_evidence_type(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "missing_source_evidence"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "source claim without source_evidence type\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: S001\n",
        encoding="utf-8",
    )
    _write_json(project / "compiled_evidence_provenance.json", {"source_count": 1})
    _write_json(workspace / "workspace_meta.json", {"merge_status": "success", "source_count": 1})
    _write_json(
        workspace / "source_index.json",
        {"sources": [{"source_id": "S001", "path": "source.md"}]},
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "source typing"}],
    )
    _write_json(
        repo / "rubrics" / "missing_source_evidence.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "missing_source_evidence_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="missing_source_evidence",
            rubric="missing_source_evidence",
            task="test missing source evidence typing",
            bounded_claim="kernel entry requires typed source evidence",
            source_refs=["projects/missing_source_evidence/raw/source.md"],
            evidence_refs=["projects/missing_source_evidence/evidence.txt"],
            non_claims=["not a successful evidence compile"],
            next_falsifier="type the source and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test missing source evidence typing' "
                "--project missing_source_evidence --rubric missing_source_evidence"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="missing_source_evidence",
        rubric="missing_source_evidence",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_preflight"]
    assert report["blocking_missing"] == ["source_preflight"]
    assert report["route_preview"]["can_run_now"] is False
    assert report["kernel_entry"]["status"] == "blocked"
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert report["kernel_entry"]["allowed_work_modes"] == [
        "inspection_only",
        "pre_kernel_project_prep",
    ]
    assert report["kernel_entry"]["prerequisites"]["source_preflight_ok"] is False
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "source_preflight",
            "recovery_channel": "source_preflight",
            "next_command": (
                "ztare project source-check --project missing_source_evidence --json"
            ),
        }
    ]
    assert report["kernel_entry"]["entry_command"] is None
    assert report["kernel_entry"]["run_command"] is None
    assert report["surfaces"]["source_preflight_ok"] is False
    assert report["surfaces"]["source_preflight_blocking"] == [
        "no source_evidence file is present"
    ]
    assert report["health_evidence_gaps"] == [
        {
            "id": "source_preflight",
            "status": "needs_attention",
            "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
            "recovery_channel": "source_preflight",
            "next_command": (
                "ztare project source-check --project missing_source_evidence --json"
            ),
        }
    ]
    assert report["recovery_actions"] == [
        {
            "id": "source_preflight",
            "reason": "fix raw source typing before workspace update or evidence compilation",
            "next_command": (
                "ztare project source-check --project missing_source_evidence --json"
            ),
        }
    ]
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_when_source_preflight_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "source_preflight_crash"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: S001\n",
        encoding="utf-8",
    )
    _write_json(project / "compiled_evidence_provenance.json", {"source_count": 1})
    _write_json(workspace / "workspace_meta.json", {"merge_status": "success", "source_count": 1})
    _write_json(
        workspace / "source_index.json",
        {"sources": [{"source_id": "S001", "path": "source.md"}]},
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "source checker unavailable"}],
    )
    _write_json(
        repo / "rubrics" / "source_preflight_crash.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "source_preflight_crash_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="source_preflight_crash",
            rubric="source_preflight_crash",
            task="test source preflight crash handling",
            bounded_claim="kernel entry requires executable source preflight",
            source_refs=["projects/source_preflight_crash/raw/source.md"],
            evidence_refs=["projects/source_preflight_crash/evidence.txt"],
            non_claims=["not a source-check bypass"],
            next_falsifier="break source-check and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test source preflight crash handling' "
                "--project source_preflight_crash --rubric source_preflight_crash"
            ),
        ),
    )

    def _raise_source_preflight(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(autoresearch_trace, "check_source_project", _raise_source_preflight)
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="source_preflight_crash",
        rubric="source_preflight_crash",
        packet=str(packet_path),
        repo=repo,
    )

    blocker = "source preflight unavailable for trace path: RuntimeError: boom"
    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_preflight"]
    assert report["blocking_missing"] == ["source_preflight"]
    assert report["route_preview"]["can_run_now"] is False
    assert report["kernel_entry"]["status"] == "blocked"
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert report["kernel_entry"]["prerequisites"]["source_preflight_ok"] is False
    assert report["kernel_entry"]["prerequisites"]["source_preflight_status"] == (
        "unavailable_for_trace_path"
    )
    assert report["surfaces"]["source_preflight_ok"] is False
    assert report["surfaces"]["source_preflight_blocking"] == [blocker]
    assert report["kernel_entry"]["blockers"] == [
        {
            "id": "source_preflight",
            "recovery_channel": "source_preflight",
            "next_command": "ztare project source-check --project source_preflight_crash --json",
        }
    ]
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_on_source_claim_graph_recovery(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "needs_graph_recovery"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {"id": "gap1", "severity": "degrading"},
                {"id": "gap2", "severity": "blocking"},
            ]
        },
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "active evidence gaps"}],
    )
    _write_json(
        repo / "rubrics" / "needs_graph_recovery.json",
        _valid_kepler_rubric(),
    )
    packet_path = repo / "needs_graph_recovery_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="needs_graph_recovery",
            rubric="needs_graph_recovery",
            task="test source-claim graph recovery boundary",
            bounded_claim="active evidence gaps should block kernel entry",
            source_refs=["projects/needs_graph_recovery/raw/source.md"],
            evidence_refs=["projects/needs_graph_recovery/evidence.txt"],
            non_claims=["not ready while evidence gaps are active"],
            next_falsifier="clear the evidence gaps and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test source-claim graph recovery boundary' "
                "--project needs_graph_recovery --rubric needs_graph_recovery"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="needs_graph_recovery",
        rubric="needs_graph_recovery",
        packet=str(packet_path),
        repo=repo,
        model="kimi",
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_out_of_loop_prep"
    assert report["missing"] == ["out_of_loop_evidence_recovery"]
    assert report["blocking_missing"] == ["out_of_loop_evidence_recovery"]
    assert report["route_preview"]["can_run_now"] is False
    assert [_without_graph_card_provenance(row) for row in report["graph_rd_actions"]] == [
        {
            "action_type": "out_of_loop_evidence_recovery",
            "work_mode": "out_of_loop_prep",
            "project": "needs_graph_recovery",
            "graph_id": "needs_graph_recovery:source_claim_graph",
            "reason": "fetch or justify 2 active evidence gap(s)",
            "recommended_actor": "research_director_or_prep_agent",
        }
    ]
    assert report["recovery_actions"] == [
        {
            "id": "out_of_loop_evidence_recovery",
            "reason": "fetch or justify 2 active evidence gap(s)",
            "next_command": (
                "make evidence-fetch PROJECT=needs_graph_recovery SEVERITY=blocking "
                "MAX_FETCHES=3 MODEL=kimi EVIDENCE_SEARCH_BACKEND=auto"
            ),
        }
    ]
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_accepts_hash_bound_evidence_gap_resolution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "resolved_graph_gap"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "gap1",
                    "severity": "degrading",
                    "target": "external comparator",
                    "description": "Need another public comparator.",
                }
            ]
        },
    )
    write_gap_resolution(
        project_dir=project,
        gap_id="gap1",
        reason="Comparator is outside this bounded packet and named as a non-claim.",
        repo=repo,
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "resolved evidence gap"}],
    )
    _write_json(repo / "rubrics" / "resolved_graph_gap.json", _valid_kepler_rubric())
    packet_path = repo / "resolved_graph_gap_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="resolved_graph_gap",
            rubric="resolved_graph_gap",
            task="test source-claim graph gap receipt",
            bounded_claim="hash-bound evidence-gap resolutions should unblock graph recovery",
            source_refs=["projects/resolved_graph_gap/raw/source.md"],
            evidence_refs=["projects/resolved_graph_gap/evidence.txt"],
            non_claims=["not a claim about the external comparator"],
            next_falsifier="change the evidence gap text and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test source-claim graph gap receipt' "
                "--project resolved_graph_gap --rubric resolved_graph_gap"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="resolved_graph_gap",
        rubric="resolved_graph_gap",
        packet=str(packet_path),
        repo=repo,
        model="kimi",
    )

    assert report["status"] == "complete_trace"
    assert report["readiness"] == "ready_for_in_loop_candidate"
    assert "out_of_loop_evidence_recovery" not in report["missing"]
    assert report["route_preview"]["can_run_now"] is True
    source_graph = [
        graph
        for graph in report["graph_carriers"]
        if graph["graph_kind"] == "source_claim_graph"
    ][0]
    assert source_graph["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert report["graph_rd_actions"] == []


def test_autoresearch_trace_does_not_block_on_repaired_local_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "repaired_graph_gap"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "test_model.py").write_text(
        "def I_model():\n    return 1.0\n",
        encoding="utf-8",
    )
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "missing-suite",
                    "severity": "degrading",
                    "target": "test_model.py",
                    "description": "The falsification suite is missing.",
                }
            ]
        },
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 25, "weakest_point": "old missing suite gap"}],
    )
    _write_json(repo / "rubrics" / "repaired_graph_gap.json", _valid_kepler_rubric())
    packet_path = repo / "repaired_graph_gap_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="repaired_graph_gap",
            rubric="repaired_graph_gap",
            task="test repaired local gap boundary",
            bounded_claim="repaired local artifact gaps should not block kernel entry",
            source_refs=["projects/repaired_graph_gap/raw/source.md"],
            evidence_refs=["projects/repaired_graph_gap/evidence.txt"],
            non_claims=["semantic evidence gaps still need recovery"],
            next_falsifier="delete test_model.py and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test repaired local gap boundary' "
                "--project repaired_graph_gap --rubric repaired_graph_gap"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="repaired_graph_gap",
        rubric="repaired_graph_gap",
        packet=str(packet_path),
        repo=repo,
        model="kimi",
    )

    assert report["status"] == "complete_trace"
    assert report["readiness"] == "ready_for_in_loop_candidate"
    assert "out_of_loop_evidence_recovery" not in report["missing"]
    assert report["route_preview"]["can_run_now"] is True
    source_graph = [
        graph
        for graph in report["graph_carriers"]
        if graph["graph_kind"] == "source_claim_graph"
    ][0]
    assert source_graph["decision_receipt"] == {
        "effect": "no_strategy_change",
        "reason": "source/evidence chain present with no active evidence gaps",
    }
    assert report["graph_rd_actions"] == []


def test_autoresearch_trace_keeps_local_verification_gap_in_loop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "local_verification_gap"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "test_model.py").write_text(
        "def I_model():\n    return 1.0\n",
        encoding="utf-8",
    )
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "next-falsifier",
                    "severity": "degrading",
                    "target": "next_falsifier_execution",
                    "description": "No evidence that preflight executes the falsifier.",
                    "producer_rationale": "contract_enforcement",
                }
            ]
        },
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 55, "weakest_point": "local verifier gap"}],
    )
    _write_json(repo / "rubrics" / "local_verification_gap.json", _valid_kepler_rubric())
    packet_path = repo / "local_verification_gap_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="local_verification_gap",
            rubric="local_verification_gap",
            task="test local verification gap routing",
            bounded_claim="local verification gaps should remain in-loop focus",
            source_refs=["projects/local_verification_gap/raw/source.md"],
            evidence_refs=["projects/local_verification_gap/evidence.txt"],
            non_claims=["public evidence gaps still block for prep"],
            next_falsifier="remove evidence ref and rerun route",
            expected_command=(
                "ztare autoresearch route --task 'test local verification gap routing' "
                "--project local_verification_gap --rubric local_verification_gap"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="local_verification_gap",
        rubric="local_verification_gap",
        packet=str(packet_path),
        repo=repo,
        model="kimi",
    )

    assert report["status"] == "complete_trace"
    assert report["readiness"] == "ready_for_in_loop_candidate"
    assert report["blocking_missing"] == []
    assert report["route_preview"]["can_run_now"] is True
    assert [_without_graph_card_provenance(row) for row in report["graph_rd_actions"]] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "local_verification_gap",
            "graph_id": "local_verification_gap:source_claim_graph",
            "reason": (
                "resolve 1 local verification gap(s) inside the autoresearch loop: "
                "next_falsifier_execution"
            ),
            "recommended_actor": "autoresearch_loop",
            "gap_ids": "next-falsifier",
            "targets": "next_falsifier_execution",
        }
    ]
    assert report["kernel_entry"]["in_loop_focus_receipts"] == report["graph_rd_actions"]
    assert report["kernel_entry"]["withheld_in_loop_focus_receipts"] == []
    assert not any("evidence-fetch" in command for command in report["next_commands"])


def test_autoresearch_trace_withholds_graph_focus_when_kernel_entry_is_blocked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "blocked_focus"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "test_model.py").write_text(
        "def I_model():\n    return 1.0\n",
        encoding="utf-8",
    )
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(
        workspace / "latest_evidence_gaps.json",
        {
            "evidence_gaps": [
                {
                    "id": "local-check",
                    "severity": "degrading",
                    "target": "next_falsifier_execution",
                    "description": "No evidence that preflight executes the falsifier.",
                    "producer_rationale": "contract_enforcement",
                }
            ]
        },
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 55, "weakest_point": "local verifier gap"}],
    )
    _write_json(repo / "rubrics" / "blocked_focus.json", _valid_kepler_rubric())
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="blocked_focus",
        rubric="blocked_focus",
        repo=repo,
        model="kimi",
    )

    assert [_without_graph_card_provenance(row) for row in report["graph_rd_actions"]] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "blocked_focus",
            "graph_id": "blocked_focus:source_claim_graph",
            "reason": (
                "resolve 1 local verification gap(s) inside the autoresearch loop: "
                "next_falsifier_execution"
            ),
            "recommended_actor": "autoresearch_loop",
            "gap_ids": "local-check",
            "targets": "next_falsifier_execution",
        }
    ]
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert report["kernel_entry"]["in_loop_focus_receipts"] == []
    assert report["kernel_entry"]["withheld_in_loop_focus_receipts"] == report["graph_rd_actions"]


def test_autoresearch_trace_gates_probability_dag_actions_by_effective_rubric(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "dag_runtime_boundary"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    _write_fresh_source_surfaces(project, workspace)
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": []})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 55, "weakest_point": "DAG focus"}],
    )
    _write_json(
        project / "latest_probability_dag.json",
        {
            "nodes": [
                {
                    "id": "n1",
                    "label": "Boundary",
                    "probability": 0.7,
                    "watch_signal": "boundary stress",
                }
            ],
            "edges": [{"from": "n1", "to": "outcome", "weight": 0.9}],
        },
    )
    packet_path = repo / "dag_runtime_boundary_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="dag_runtime_boundary",
            rubric="dag_runtime_boundary",
            task="test probability DAG runtime boundary",
            bounded_claim="DAG trace action depends on effective rubric steering",
            source_refs=["projects/dag_runtime_boundary/raw/source.md"],
            evidence_refs=["projects/dag_runtime_boundary/evidence.txt"],
            non_claims=["read-only trace does not write steering logs"],
            next_falsifier="disable DAG steering and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test probability DAG runtime boundary' "
                "--project dag_runtime_boundary --rubric dag_runtime_boundary"
            ),
        ),
    )
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    disabled_rubric = _valid_kepler_rubric()
    _write_json(repo / "rubrics" / "dag_runtime_boundary.json", disabled_rubric)
    disabled_report = autoresearch_trace.build_autoresearch_trace(
        project="dag_runtime_boundary",
        rubric="dag_runtime_boundary",
        packet=str(packet_path),
        repo=repo,
    )

    dag_receipt = disabled_report["graph_carriers"][0]["decision_receipt"]
    assert dag_receipt == {
        "effect": "no_strategy_change",
        "reason": (
            "DAG has a scorable pending focus, but the effective rubric does "
            "not enable DAG steering"
        ),
        "pending_next_discriminator": (
            "DAG scoring selects node 'n1' as the pending in-loop focus; "
            "watch signal: boundary stress"
        ),
        "runtime_consumable": False,
    }
    assert disabled_report["graph_rd_actions"] == []

    enabled_rubric = _valid_kepler_rubric()
    enabled_rubric["rubric_modes"] = ["invariant_search"]
    _write_json(repo / "rubrics" / "dag_runtime_boundary.json", enabled_rubric)
    enabled_report = autoresearch_trace.build_autoresearch_trace(
        project="dag_runtime_boundary",
        rubric="dag_runtime_boundary",
        packet=str(packet_path),
        repo=repo,
    )

    assert enabled_report["graph_carriers"][0]["decision_receipt"] == {
        "effect": "strategy_change",
        "selected_next_discriminator": (
            "DAG scoring selects node 'n1' as the pending in-loop focus; "
            "watch signal: boundary stress"
        ),
        "runtime_consumable": True,
    }
    assert [
        _without_graph_card_provenance(row)
        for row in enabled_report["graph_rd_actions"]
    ] == [
        {
            "action_type": "in_loop_focus_receipt",
            "work_mode": "in_loop",
            "project": "dag_runtime_boundary",
            "graph_id": "dag_runtime_boundary:latest_probability_dag",
            "reason": (
                "DAG scoring selects node 'n1' as the pending in-loop focus; "
                "watch signal: boundary stress"
            ),
            "recommended_actor": "autoresearch_loop",
        }
    ]


def test_autoresearch_trace_blocks_invalid_source_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "bad_source_type"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: invented_type\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: S001\n",
        encoding="utf-8",
    )
    _write_json(project / "compiled_evidence_provenance.json", {"source_count": 1})
    _write_json(workspace / "workspace_meta.json", {"merge_status": "success", "source_count": 1})
    _write_json(
        workspace / "source_index.json",
        {"sources": [{"source_id": "S001", "path": "source.md"}]},
    )
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 9, "weakest_point": "source typing"}],
    )
    _write_json(repo / "rubrics" / "bad_source_type.json", _valid_kepler_rubric())
    packet_path = repo / "bad_source_type_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="bad_source_type",
            rubric="bad_source_type",
            task="test source preflight readiness",
            bounded_claim="source typing must be valid before loop entry",
            source_refs=["projects/bad_source_type/raw/source.md"],
            evidence_refs=["projects/bad_source_type/evidence.txt"],
            non_claims=["not a successful evidence compile"],
            next_falsifier="fix the source type and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test source preflight readiness' "
                "--project bad_source_type --rubric bad_source_type"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="bad_source_type",
        rubric="bad_source_type",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["source_preflight"]
    assert report["blocking_missing"] == ["source_preflight"]
    assert report["route_preview"]["can_run_now"] is False
    assert report["surfaces"]["source_preflight_ok"] is False
    assert report["surfaces"]["source_preflight_status"] == "blocked"
    assert report["surfaces"]["source_preflight_blocking"] == [
        "one or more sources declare an invalid source_type",
        "no source_evidence file is present",
    ]
    assert report["recovery_actions"] == [
        {
            "id": "source_preflight",
            "reason": "fix raw source typing before workspace update or evidence compilation",
            "next_command": "ztare project source-check --project bad_source_type --json",
        }
    ]
    assert report["next_commands"][0] == (
        "ztare project source-check --project bad_source_type --json"
    )
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_reports_partial_source_chain_with_recovery(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "partial_trace"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (project / "evidence.txt").write_text("legacy evidence\n", encoding="utf-8")
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"iteration": 1, "score": 5, "weakest_point": "Missing source chain."}],
    )
    _write_json(workspace / "latest_evidence_gaps.json", {"evidence_gaps": []})

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "needs_attention"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="partial_trace",
        rubric=None,
        model="deepseek",
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "blocked_on_project_surfaces"
    assert report["missing"] == ["raw_sources", "evidence_compile_provenance"]
    assert report["blocking_missing"] == ["raw_sources", "evidence_compile_provenance"]
    assert report["history_missing"] == []
    assert report["project_packet"]["status"] == "not_found"
    assert report["project_packet"]["available"] is False
    assert report["route_preview"] == {
        "available": False,
        "source": None,
        "source_name": None,
        "route_command": None,
        "preflight_command": None,
        "run_command": None,
        "can_run_now": False,
    }
    assert report["plan_preview"]["status"] == "unavailable"
    assert report["plan_preview"]["model_calls_before_confirmation"] is False
    assert report["plan_preview"]["largest_quality_drop_risk"] == "blocked_kernel_entry"
    assert report["surfaces"]["raw_file_count"] == 0
    assert report["surfaces"]["compile_provenance_exists"] is False
    assert report["surfaces"]["workspace_meta_exists"] is False
    assert report["surfaces"]["source_index_exists"] is False
    assert report["graph_carriers"] == [
        {
            "graph_id": "partial_trace:source_claim_graph",
            "graph_kind": "source_claim_graph",
            "source_artifacts": [
                "projects/partial_trace/evidence.txt",
                "projects/partial_trace/workspace/latest_evidence_gaps.json",
            ],
            "node_count": 1,
            "edge_count": 0,
            "decision_receipt": {
                "effect": "misleading_or_noise",
                "reason": (
                    "source-claim graph source preflight is not satisfied (blocked); "
                    "graph routing is blocked until source-check passes: raw source "
                    "directory is missing"
                ),
            },
            "validation": {"ok": True, "errors": [], "warnings": []},
        }
    ]
    assert [_without_graph_card_provenance(row) for row in report["graph_rd_actions"]] == [
        {
            "action_type": "demote_graph_signal",
            "work_mode": "out_of_loop_review",
            "project": "partial_trace",
            "graph_id": "partial_trace:source_claim_graph",
            "reason": (
                "source-claim graph source preflight is not satisfied (blocked); "
                "graph routing is blocked until source-check passes: raw source "
                "directory is missing"
            ),
            "recommended_actor": "research_director",
        }
    ]
    assert report["prediction_summary"]["status"] == "no_prediction_contracts"
    assert report["prediction_summary"]["row_count"] == 0
    assert report["recovery_actions"] == [
        {
            "id": "raw_sources",
            "reason": "fetch public sources for recorded evidence gaps",
            "next_command": (
                "make evidence-fetch PROJECT=partial_trace SEVERITY=degrading "
                "MAX_FETCHES=3 MODEL=deepseek EVIDENCE_SEARCH_BACKEND=auto"
            ),
        }
    ]
    assert report["next_commands"][0] == (
        "make evidence-fetch PROJECT=partial_trace SEVERITY=degrading "
        "MAX_FETCHES=3 MODEL=deepseek EVIDENCE_SEARCH_BACKEND=auto"
    )
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_recommends_source_init_instead_of_shell_mkdir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "needs_sources"
    project.mkdir(parents=True)
    _write_json(repo / "rubrics" / "needs_sources.json", _valid_kepler_rubric())

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "needs_attention"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="needs_sources",
        rubric="needs_sources",
        model="deepseek",
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_project_surfaces"
    assert "raw_or_evidence" in report["blocking_missing"]
    raw_action = next(
        action for action in report["recovery_actions"] if action["id"] == "raw_sources"
    )
    assert raw_action == {
        "id": "raw_sources",
        "reason": (
            "initialize the source-ingest surface, then add typed source "
            "documents under the project raw directory"
        ),
        "next_command": (
            "ztare project source-init --project needs_sources --rubric needs_sources"
        ),
    }
    assert raw_action["next_command"] in report["next_commands"]
    assert all("mkdir -p" not in command for command in report["next_commands"])
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_when_launch_preflight_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "missing_launch_files"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nfresh source claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_json(repo / "rubrics" / "missing_launch_files.json", _valid_kepler_rubric())
    packet_path = repo / "missing_launch_files_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="missing_launch_files",
            rubric="missing_launch_files",
            task="test launch preflight parity",
            bounded_claim="trace readiness must match make experiment-loop preflight",
            source_refs=["projects/missing_launch_files/raw/source.md"],
            evidence_refs=["projects/missing_launch_files/evidence.txt"],
            non_claims=["not a completed autoresearch run"],
            next_falsifier="add project_charter.md and thesis.md and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test launch preflight parity' "
                "--project missing_launch_files --rubric missing_launch_files"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="missing_launch_files",
        rubric="missing_launch_files",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_launch_preflight"
    assert report["missing"] == ["launch_preflight", "eval_history"]
    assert report["blocking_missing"] == ["launch_preflight"]
    assert report["history_missing"] == ["eval_history"]
    assert report["route_preview"]["can_run_now"] is False
    assert report["surfaces"]["launch_preflight_ok"] is False
    assert report["surfaces"]["launch_preflight_status"] == "blocked"
    assert any(
        "missing required file: projects/missing_launch_files/project_charter.md"
        in item
        for item in report["surfaces"]["launch_preflight_errors"]
    )
    assert any(
        "missing required file: projects/missing_launch_files/thesis.md" in item
        for item in report["surfaces"]["launch_preflight_errors"]
    )
    assert report["recovery_actions"] == [
        {
            "id": "launch_preflight",
            "reason": "fix the same rubric/project preflight that make experiment-loop enforces",
            "next_command": (
                "make validate-rubric PROJECT=missing_launch_files "
                "RUBRIC=rubrics/missing_launch_files.json"
            ),
        }
    ]
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_blocks_when_launch_preflight_unavailable_for_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    project = tmp_path / "external_projects" / "external_launch"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nfresh source claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_jsonl(workspace / "eval_history.jsonl", [{"iter": 0, "score": 0.1}])
    _write_json(repo / "rubrics" / "external_launch.json", _valid_kepler_rubric())
    packet_path = repo / "external_launch_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="external_launch",
            rubric="external_launch",
            task="test launch preflight trace path contract",
            bounded_claim="trace readiness must not bypass launch preflight",
            source_refs=["https://example.invalid/external_launch/source.md"],
            evidence_refs=["https://example.invalid/external_launch/evidence.txt"],
            non_claims=["not a completed autoresearch run"],
            next_falsifier="move the project under projects/ and rerun launch preflight",
            expected_command=(
                "ztare autoresearch route --task 'test launch preflight trace path contract' "
                "--project external_launch --rubric external_launch"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "check_source_project",
        lambda **_kwargs: {
            "schema": "ztare-source-check-v1",
            "ok": True,
            "status": "ok",
            "blocking": [],
            "warnings": [],
            "source_evidence_count": 1,
            "untyped_source_count": 0,
        },
    )
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project=str(project),
        rubric="external_launch",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["readiness"] == "blocked_on_launch_preflight"
    assert report["missing"] == ["launch_preflight"]
    assert report["blocking_missing"] == ["launch_preflight"]
    assert report["history_missing"] == []
    assert report["route_preview"]["can_run_now"] is False
    assert report["surfaces"]["launch_preflight_ok"] is False
    assert report["surfaces"]["launch_preflight_status"] == "unavailable_for_trace_path"
    assert any(
        "projects directory" in item
        for item in report["surfaces"]["launch_preflight_errors"]
    )
    assert report["kernel_entry"]["status"] == "blocked"
    assert report["kernel_entry"]["can_enter_kernel"] is False
    assert {
        "id": "launch_preflight",
        "reason": "fix the same rubric/project preflight that make experiment-loop enforces",
        "next_command": (
            "make validate-rubric PROJECT=external_launch "
            "RUBRIC=rubrics/external_launch.json"
        ),
    } in report["recovery_actions"]
    assert not any("make experiment-loop" in command for command in report["next_commands"])


def test_autoresearch_trace_ready_first_run_without_eval_history(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "fresh_trace"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nfresh source claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_json(repo / "rubrics" / "fresh_trace.json", _valid_kepler_rubric())
    packet_path = repo / "fresh_trace_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="fresh_trace",
            rubric="fresh_trace",
            task="test a fresh project boundary",
            bounded_claim="fresh trace has source-bound evidence",
            source_refs=["projects/fresh_trace/raw/source.md"],
            evidence_refs=["projects/fresh_trace/evidence.txt"],
            non_claims=["not a completed autoresearch run"],
            next_falsifier="run the first loop and inspect eval history",
            expected_command=(
                "ztare autoresearch route --task 'test a fresh project boundary' "
                "--project fresh_trace --rubric fresh_trace"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="fresh_trace",
        rubric="fresh_trace",
        packet=str(packet_path),
        repo=repo,
    )

    assert report["status"] == "partial_trace"
    assert report["readiness"] == "ready_for_first_in_loop_run"
    assert report["missing"] == ["eval_history"]
    assert report["blocking_missing"] == []
    assert report["history_missing"] == ["eval_history"]
    assert report["project_packet"]["ok"] is True
    assert report["project_packet"]["missing_ref_falsifier"]["ok"] is True
    assert report["project_packet"]["missing_ref_falsifier"]["remove_ref"] == "evidence_refs[1]"
    assert report["route_preview"] == {
        "available": True,
        "source": "project_intake",
        "source_name": "project_intake",
        "legacy_source": "project_packet",
        "route_command": (
            "ztare autoresearch route --task 'test a fresh project boundary' "
            "--project fresh_trace --rubric fresh_trace --intake fresh_trace_packet.json"
        ),
        "preflight_command": (
            "ztare autoresearch run --project fresh_trace --rubric fresh_trace "
            "--intake fresh_trace_packet.json --preflight-only"
        ),
        "run_command": (
            "ztare autoresearch run --project fresh_trace --rubric fresh_trace "
            "--intake fresh_trace_packet.json --iters 10"
        ),
        "can_run_now": True,
    }
    assert report["projection"]["available"] is False
    assert report["recovery_actions"] == []
    assert report["next_commands"][0] == (
        "ztare autoresearch route --task 'test a fresh project boundary' "
        "--project fresh_trace --rubric fresh_trace --intake fresh_trace_packet.json"
    )
    assert report["next_commands"][1] == (
        "ztare autoresearch run --project fresh_trace --rubric fresh_trace "
        "--intake fresh_trace_packet.json --preflight-only"
    )
    assert report["next_commands"][2] == (
        "ztare autoresearch run --project fresh_trace --rubric fresh_trace "
        "--intake fresh_trace_packet.json --iters 10"
    )
    assert not any("ztare autoresearch projection" in command for command in report["next_commands"])


def test_autoresearch_trace_uses_packet_run_command_for_launch_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "packet_run_trace"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nfresh source claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_json(repo / "rubrics" / "packet_run_trace.json", _valid_kepler_rubric())
    packet_path = repo / "packet_run_trace_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="packet_run_trace",
            rubric="packet_run_trace",
            task="test packet run command preview",
            bounded_claim="fresh trace has source-bound evidence",
            source_refs=["projects/packet_run_trace/raw/source.md"],
            evidence_refs=["projects/packet_run_trace/evidence.txt"],
            non_claims=["not a completed autoresearch run"],
            next_falsifier="run the first loop and inspect eval history",
            expected_command=(
                "ztare autoresearch run --project packet_run_trace "
                "--rubric packet_run_trace --iters 3 --mutator kimi --judge gpt4.1"
            ),
        ),
    )

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="packet_run_trace",
        rubric="packet_run_trace",
        packet=str(packet_path),
        repo=repo,
    )

    run_command = (
        "ztare autoresearch run --project packet_run_trace "
        "--rubric packet_run_trace --iters 3 --mutator kimi --judge gpt4.1 "
        "--intake packet_run_trace_packet.json"
    )
    preflight_command = run_command + " --preflight-only"
    assert report["route_preview"]["route_command"] == run_command
    assert report["route_preview"]["run_command"] == run_command
    assert report["route_preview"]["preflight_command"] == preflight_command
    assert report["kernel_entry"]["entry_command"] == run_command
    assert report["kernel_entry"]["run_command"] == run_command
    assert report["next_commands"].count(run_command) == 1
    assert report["next_commands"][0] == preflight_command
    assert report["next_commands"][1] == run_command
    assert report["plan_preview"]["recommended_first_command"] == preflight_command
    assert report["plan_preview"]["dependency_order"][0]["id"] == "intake_declared_run"
    assert report["plan_preview"]["dependency_order"][0]["command"] is None


def test_autoresearch_trace_flags_stale_preflight_packet_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path
    project = repo / "projects" / "stale_preflight_packet"
    workspace = project / "workspace"
    (project / "raw").mkdir(parents=True)
    _write_launch_files(project)
    (project / "raw" / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nfresh source claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text(
        "Evidence packet\n\n- source_id: source.md\n",
        encoding="utf-8",
    )
    _write_fresh_source_surfaces(project, workspace)
    _write_json(repo / "rubrics" / "stale_preflight_packet.json", _valid_kepler_rubric())
    packet_path = repo / "stale_preflight_packet.json"
    write_project_packet(
        packet_path,
        build_project_packet(
            project="stale_preflight_packet",
            rubric="stale_preflight_packet",
            task="test packet preflight drift",
            bounded_claim="preflight packet receipt should bind exact bytes",
            source_refs=["projects/stale_preflight_packet/raw/source.md"],
            evidence_refs=["projects/stale_preflight_packet/evidence.txt"],
            non_claims=["not a completed autoresearch run"],
            next_falsifier="edit the packet after preflight and rerun trace",
            expected_command=(
                "ztare autoresearch route --task 'test packet preflight drift' "
                "--project stale_preflight_packet --rubric stale_preflight_packet"
            ),
        ),
    )
    admitted_packet_sha = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    _write_jsonl(
        workspace / "iteration_telemetry.jsonl",
        [
            {
                "record_type": "run_start",
                "run_id": 303,
                "preflight_only": True,
                "project_packet": {
                    "packet_path": "stale_preflight_packet.json",
                    "packet_sha256": admitted_packet_sha,
                    "packet_id": "stale_preflight_packet:packet:2026-06-20T00:00:00Z",
                    "packet_status": "valid_packet",
                    "readiness": "ready_for_first_in_loop_run",
                    "kernel_entry_status": "ready",
                    "kernel_entry_sha256": "b" * 64,
                },
            },
            {
                "record_type": "run_end",
                "run_id": 303,
                "timestamp_utc": "2026-06-20T00:10:00Z",
                "final_iteration": 0,
                "final_score": None,
                "run_exit_reason": "preflight_only",
                "preflight_only": True,
            },
        ],
    )
    packet_path.write_text(packet_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_kernel_health",
        lambda **_kwargs: {"summary": {"overall_status": "ok"}, "evidence_gaps": []},
    )

    report = autoresearch_trace.build_autoresearch_trace(
        project="stale_preflight_packet",
        rubric="stale_preflight_packet",
        packet=str(packet_path),
        repo=repo,
    )

    preflight = report["recent_loop"]["latest_preflight_only"]
    packet = preflight["packet"]
    assert report["recent_loop"]["available"] is True
    assert report["recent_loop"]["eval_history_rows"] == 0
    assert report["recent_loop"]["telemetry_iteration_rows"] == 0
    assert preflight["run_id"] == 303
    assert packet["packet_sha256"] == admitted_packet_sha
    assert packet["packet_current_sha256"] != admitted_packet_sha
    assert packet["packet_hash_status"] == "stale_current_packet"
    assert packet["packet_hash_verified"] is False
    assert packet["kernel_entry_current_sha256"] != "b" * 64
    assert packet["kernel_entry_hash_status"] == "current_kernel_entry_changed"
    assert packet["kernel_entry_hash_verified"] is False
    assert report["loop_admission"] == {
        "available": True,
        "receipt_count": 1,
        "intake_hash_verified": False,
        "intake_hash_statuses": ["stale_current_packet"],
        "packet_hash_verified": False,
        "packet_hash_statuses": ["stale_current_packet"],
        "kernel_entry_hash_verified": False,
        "kernel_entry_hash_statuses": ["current_kernel_entry_changed"],
    }
    assert report["readiness"] == "ready_for_first_in_loop_run"


def test_autoresearch_trace_text_output_includes_graph_carriers(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        autoresearch_trace,
        "build_autoresearch_trace",
        lambda **_kwargs: {
            "project": "demo",
            "status": "complete_trace",
            "readiness": "ready_for_in_loop_candidate",
            "missing": [],
            "blocking_missing": [],
            "history_missing": [],
            "project_packet": {
                "available": True,
                "status": "valid_packet",
                "ok": True,
                "path": "demo_packet.json",
            },
            "project_intake": {
                "available": True,
                "status": "valid_packet",
                "ok": True,
                "path": "demo_packet.json",
                "intake_path": "demo_packet.json",
                "legacy_receipt_surface": "project_packet",
            },
            "route_preview": {
                "available": True,
                "source": "project_intake",
                "source_name": "project_intake",
                "legacy_source": "project_packet",
                "route_command": "ztare autoresearch route --task demo --project demo --rubric demo",
                "run_command": (
                    "ztare autoresearch run --project demo --rubric demo "
                    "--intake demo_packet.json --iters 10"
                ),
                "can_run_now": True,
            },
            "kernel_entry": {
                "schema": "ztare-kernel-entry-contract-v1",
                "status": "ready",
                "can_enter_kernel": True,
            },
            "loop_admission": {
                "available": True,
                "receipt_count": 1,
                "packet_hash_verified": True,
                "intake_hash_verified": True,
                "packet_hash_statuses": ["fresh"],
                "intake_hash_statuses": ["fresh"],
                "kernel_entry_hash_verified": True,
                "kernel_entry_hash_statuses": ["fresh"],
            },
            "carrier_chain": [
                {
                    "surface": "project_intake",
                    "legacy_surface": "project_packet",
                    "status": "valid_packet",
                    "blocking": False,
                    "next_command": "ztare project intake validate demo_packet.json",
                }
            ],
            "surfaces": {"evidence_exists": True},
            "projection": {"available": False},
            "recent_loop": {
                "available": True,
                "latest_preflight_only": {
                    "run_id": 7,
                    "run_exit_reason": "preflight_only",
                    "packet": {
                        "packet_path": "demo_packet.json",
                        "packet_hash_status": "fresh",
                        "kernel_entry_hash_status": "fresh",
                    },
                },
            },
            "graph_carriers": [
                {
                    "graph_id": "demo:source_claim_graph",
                    "graph_kind": "source_claim_graph",
                    "validation": {"ok": True, "errors": [], "warnings": []},
                }
            ],
            "graph_rd_actions": [
                {
                    "action_type": "out_of_loop_evidence_recovery",
                    "work_mode": "out_of_loop_prep",
                    "project": "demo",
                    "graph_id": "demo:source_claim_graph",
                    "reason": "fetch or justify 1 active evidence gap(s)",
                    "recommended_actor": "research_director_or_prep_agent",
                }
            ],
            "prediction_summary": {
                "available": False,
                "status": "no_prediction_contracts",
                "row_count": 0,
            },
            "health_summary": {"overall_status": "ok"},
            "next_commands": ["ztare autoresearch health --project demo --json"],
        },
    )

    rc = autoresearch_trace.main(["--project", "demo"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "readiness=" in out
    assert "blocking_missing=" in out
    assert "history_missing=" in out
    assert "project_intake=" in out
    assert "legacy_project_packet=" in out
    assert "route_preview=" in out
    assert "loop_admission=" in out
    assert "carrier_chain_table:" in out
    assert "surface" in out
    assert "block" in out
    assert "valid_packet" in out
    assert "ztare project intake validate demo_packet.json" in out
    assert "carrier_chain=" in out
    assert "recent_loop=" in out
    assert "project_intake" in out
    assert "project_packet" in out
    assert "packet_hash_status" in out
    assert "kernel_entry_hash_status" in out
    assert "graph_carriers=" in out
    assert "graph_rd_actions=" in out
    assert "prediction_summary=" in out
    assert "source_claim_graph" in out
