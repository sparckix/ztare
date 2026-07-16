from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from argparse import Namespace
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


SCRIPT = Path("scripts/public/control/forensic_workbench_snapshot.py").resolve()
REVIEW_SCRIPT = Path("scripts/public/control/forensic_workbench_review.py").resolve()
SERVER_SCRIPT = Path("scripts/public/control/forensic_workbench_server.py").resolve()
STATE_SCRIPT = Path("scripts/public/control/forensic_workbench_state.py").resolve()
LIVE_SCRIPT = Path("scripts/public/control/forensic_workbench_live.py").resolve()


def load_module():
    spec = importlib.util.spec_from_file_location("forensic_workbench_snapshot", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_review_module():
    spec = importlib.util.spec_from_file_location("forensic_workbench_review", REVIEW_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_server_module():
    script_dir = str(SERVER_SCRIPT.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("forensic_workbench_server", SERVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_state_module():
    script_dir = str(STATE_SCRIPT.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("forensic_workbench_state", STATE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_live_module():
    spec = importlib.util.spec_from_file_location("forensic_workbench_live", LIVE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_display_detail_normalizes_next_step_tokens() -> None:
    module = load_module()

    assert module.display_detail("Report support: next_step; export_blocker") == (
        "Report readiness: next step; fix report readiness"
    )
    assert module.display_detail("source_index=fresh; output_binding=fresh") == (
        "file index: fresh; evidence connection: fresh"
    )


def test_project_display_label_uses_visible_project_language() -> None:
    module = load_server_module()

    assert module.project_display_label("riemann_operator_search") == "Riemann system search"
    assert module.project_display_label("ns_defect_packet_certificate") == "NS defect project brief certificate"
    assert module.project_display_label("hbr_case_method_roi_proxy") == "HBR project method ROI proxy"
    assert module.project_display_label("eu_union_load_bearing_pillars") == "EU union key pillars"
    assert module.project_display_label("ai_capex") == "AI CapEx"


def test_health_payload_adds_plain_evidence_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    assert module.display_action_label("unconsumed_surface") == "work log is missing"
    assert module.display_value("export_blocker") == "fix report readiness"
    assert module.display_text("receipt path") == "saved-history path"
    assert module.display_text("source refs") == "original files"
    assert module.display_surface("launch_preflight") == "readiness check"
    assert module.display_evidence_ref("analytics/public/action_intelligence/surfacing_event_ledger.jsonl") == {
        "label": "Work log",
        "path": "analytics/public/action_intelligence/surfacing_event_ledger.jsonl",
    }

    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(
        module,
        "kernel_health_from_trace",
        lambda **_kwargs: {
            "summary": {
                "overall_status": "attention",
                "component_status": "attention",
                "component_count": 1,
                "component_counts": {"attention": 0, "ok": 1},
                "source": "trace_read_model",
                "recompute_command": "make autoresearch-kernel-health PROJECT=demo JSON=1",
            },
            "attention_components": [],
            "component_count": 1,
        },
    )
    monkeypatch.setattr(
        module,
        "action_intelligence_health_read_model",
        lambda: {
            "counts": {"issues": 1},
            "issues": [
                {
                    "issue_id": "sh_demo",
                    "issue_type": "weak_gp233_linkage",
                    "severity": "warning",
                    "scope": "gp233",
                    "blocking_rule": "markdown-only GP-233 linkage cannot support non-diagnostic recommendations",
                    "evidence_refs": ["analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"],
                    "recommended_action": "repair_source_emitter",
                }
            ],
            "source_paths": {},
        },
    )
    monkeypatch.setattr(
        module,
        "action_intelligence_recommendations",
        lambda: {
            "counts": {"forecast_ops": 1},
            "generated_at": "2026-06-24T00:00:00Z",
            "source_path": "analytics/public/action_intelligence/state/shadow_recommendations.json",
            "recommendations": [
                {
                    "recommendation_id": "sr_demo",
                    "recommended_action": "defer",
                    "evidence_refs": ["analytics/public/forecast_pool/aggregates/demo.json"],
                    "display_evidence_refs": [module.display_evidence_ref("analytics/public/forecast_pool/aggregates/demo.json")],
                }
            ],
        },
    )

    payload = module.health_payload_for_project(project="demo")

    issue = payload["action_guidance"]["issues"][0]
    recommendation = payload["action_guidance"]["recommendations"][0]
    assert issue["display_label"] == "evidence links need repair"
    assert issue["display_blocking_rule"] == "doc-only evidence ledger linkage cannot support stronger suggestions"
    assert issue["what_to_check"].startswith("Open the evidence ledger")
    assert issue["done_when"].startswith("The ledger links the warning")
    assert issue["display_evidence_refs"] == [
        {
            "label": "Evidence ledger file",
            "path": "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        }
    ]
    assert recommendation["display_evidence_refs"] == [
        {"label": "Forecast summary file", "path": "analytics/public/forecast_pool/aggregates/demo.json"}
    ]


def test_source_health_project_action_is_inspect_only_advisory() -> None:
    module = load_server_module()

    action = module.source_health_project_action(
        {
            "issue_type": "weak_gp233_linkage",
            "blocking_rule": "doc-only links cannot support recommendations",
            "evidence_refs": ["analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"],
        },
        index=1,
        source_path="analytics/public/action_intelligence/state/source_health.json",
    )

    assert action["label"] == "Inspect evidence-link warning"
    assert action["action_type"] == "advisory"
    assert action["primary_label"] == "Open backing evidence"
    assert action["area"] == "advisory"
    assert "Guidance only; not a project blocker." in action["detail"]
    assert action["source"] == "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
    assert action["source_label"] == "Evidence ledger file"
    assert action["what_to_check"] == (
        "Open the evidence ledger and look for a concrete decision, run, or project file "
        "linked to the warning, not only a prose note."
    )
    assert action["done_when"] == (
        "The ledger links the warning to inspectable evidence that can support or demote a "
        "recommendation."
    )
    assert action["evidence_refs"] == ["analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"]
    assert action["display_evidence_refs"] == [
        {
            "label": "Evidence ledger file",
            "path": "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        }
    ]
    assert action["receipt_paths"] == []
    assert action["write_boundary"]["writes_project_files"] is False
    assert action["write_boundary"]["writes_repo_files"] is False
    assert action["write_boundary"]["write_paths"] == []
    assert action["write_boundary"]["read_only_actions"] == ["open backing evidence", "copy evidence path"]

    stale_action = module.source_health_project_action(
        {
            "issue_type": "stale_trajectory_output",
            "blocking_rule": "stale run-history outputs force diagnostic guidance",
            "evidence_refs": ["analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl"],
        },
        index=2,
        source_path="analytics/public/action_intelligence/state/source_health.json",
    )
    assert stale_action["label"] == "Inspect stale run-history warning"
    assert stale_action["workspace"] == "run"
    assert stale_action["subsection"] == "Fix warnings"
    assert stale_action["what_to_check"].startswith("Open the run-history archive")
    assert stale_action["done_when"].startswith("The run-history archive has been refreshed")


def test_source_health_state_payload_summarizes_warnings() -> None:
    module = load_server_module()

    payload = module.source_health_state_payload(
        {
            "counts": {"warning": 1, "blocking": 0},
            "source_path": "analytics/public/action_intelligence/state/source_health.json",
            "issues": [
                {
                    "issue_id": "sh_demo",
                    "issue_type": "weak_gp233_linkage",
                    "severity": "warning",
                    "blocking_rule": "markdown-only GP-233 linkage cannot support non-diagnostic recommendations",
                    "evidence_refs": ["analytics/public/ledgers/demo.md"],
                }
            ],
        }
    )

    assert payload["status"] == "needs attention"
    assert payload["issue_count"] == 1
    assert payload["issue_types"] == ["weak_gp233_linkage"]
    assert payload["display_issue_types"] == ["evidence links need repair"]
    assert "evidence links need repair" in payload["summary"]
    assert payload["issues"][0]["display_issue_type"] == "evidence links need repair"
    assert payload["issues"][0]["summary"] == "doc-only evidence ledger linkage cannot support stronger suggestions"
    assert "GP-233" not in payload["issues"][0]["summary"]
    assert payload["issues"][0]["evidence_refs"] == ["analytics/public/ledgers/demo.md"]


def test_admission_trace_uses_configured_evidence_fetch_command() -> None:
    module = load_server_module()
    stale_command = "make evidence-fetch PROJECT=demo SEVERITY=degrading MAX_FETCHES=3 MODEL=gemini"
    configured_command = (
        "make evidence-fetch PROJECT=demo SEVERITY=degrading MAX_FETCHES=3 "
        "MODEL=deepseek EVIDENCE_SEARCH_BACKEND=auto MODEL_FALLBACK=0"
    )

    payload = module.admission_summary_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        trace={
            "kernel_entry": {
                "readiness": "blocked_on_out_of_loop_prep",
                "can_enter_kernel": False,
                "blockers": [
                    {
                        "id": "out_of_loop_evidence_recovery",
                        "next_command": stale_command,
                        "recovery_channel": "out_of_loop_evidence_recovery",
                    }
                ],
            },
            "plan_preview": {"recommended_first_command": stale_command},
            "next_commands": [stale_command],
        },
        evidence_readiness={},
        scoring_guide_readiness={},
        evidence_gap_recovery={"command": configured_command},
        input_ready=False,
        run_can_start=False,
    )

    assert payload["recommended_first_command"] == configured_command
    assert payload["next_commands"] == [configured_command]
    assert payload["blockers"][0]["next_command"] == configured_command


def test_plan_step_display_status_names_blocked_run_sequence() -> None:
    module = load_server_module()

    assert module.plan_step_display_status({"id": "intake_declared_run"}, "blocked_before_kernel_entry") == "ready"
    assert (
        module.plan_step_display_status(
            {"id": "repair_surfaces", "command": "make evidence-fetch PROJECT=demo"},
            "blocked_before_kernel_entry",
        )
        == "needs action"
    )
    assert module.plan_step_display_status({"id": "preflight_only"}, "blocked_before_kernel_entry") == "after recovery"
    assert module.plan_step_display_status({"id": "bounded_loop_run"}, "blocked_before_kernel_entry") == "waits for recovery"
    assert module.plan_step_display_status({"id": "trace_health_review"}, "blocked_before_kernel_entry") == "after run"


def test_admission_trace_uses_configured_evidence_prepare_command(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setenv("ZTARE_WORKBENCH_MODEL", "deepseek")
    stale_command = "make evidence-prepare PROJECT=demo MODEL=gemini"
    expected_command = (
        "make evidence-prepare PROJECT=demo MODEL=deepseek MODEL_FALLBACK=0 "
        "EVIDENCE_LLM_TIMEOUT=300 EVIDENCE_LLM_RETRIES=4"
    )

    payload = module.admission_summary_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        trace={
            "kernel_entry": {
                "readiness": "blocked_on_out_of_loop_prep",
                "can_enter_kernel": False,
                "blockers": [
                    {
                        "id": "evidence_compile_provenance",
                        "next_command": stale_command,
                        "recovery_channel": "evidence_prepare",
                    }
                ],
            },
            "plan_preview": {"recommended_first_command": stale_command},
            "next_commands": [stale_command],
        },
        evidence_readiness={},
        scoring_guide_readiness={},
        evidence_gap_recovery={},
        input_ready=False,
        run_can_start=False,
    )

    assert payload["recommended_first_command"] == expected_command
    assert payload["next_commands"] == [expected_command]
    assert payload["blockers"][0]["next_command"] == expected_command


def fixture_trace() -> dict:
    return {
        "project": "demo",
        "rubric": "demo",
        "project_dir": "projects/demo",
        "readiness_canonical": "ready_for_in_loop_candidate",
        "project_intake": {
            "status": "valid_packet",
            "bounded_claim": "demo bounded claim",
            "next_falsifier": "Find a contrary source.",
            "non_claim_count": 2,
            "intake_path": "examples/project_packets/demo_intake.json",
            "missing_ref_falsifier": {
                "status": "passed",
                "expected_error_fragment": "missing source path is rejected",
            },
        },
        "kernel_entry": {
            "schema": "ztare-kernel-entry-contract-v1",
            "status": "ready",
            "readiness": "ready_for_in_loop_candidate",
            "can_enter_kernel": True,
            "preflight_command": "ztare autoresearch run --project demo --preflight-only",
        },
        "loop_admission": {
            "available": True,
            "receipt_count": 1,
            "intake_hash_verified": True,
        },
        "recent_loop": {
            "available": True,
            "eval_history_rows": 3,
            "latest_run_exit_reason": "preflight_only",
        },
        "surfaces": {
            "raw_file_count": 1,
            "untyped_source_count": 0,
            "source_preflight_status": "ready_for_evidence_prepare",
            "source_index_receipt": {
                "path": "projects/demo/workspace/source_index_receipt.json",
                "schema": "ztare-source-index-receipt-v1",
            },
            "compile_provenance_path": "projects/demo/compiled_evidence_provenance.json",
            "evidence_readiness": {
                "status": "fresh",
                "source_index_status": "fresh",
                "output_binding_status": "fresh",
                "replay_status": "missing_manifest",
            },
        },
    }


def fixture_report_contract() -> dict:
    return {
        "ok": False,
        "status": "blocked",
        "status_reasons": [
            "synthesis_input_binding_unbound",
        ],
        "report_support_contract": "projects/demo/synthesis/report_support_contract.json",
        "synthesis_input_binding": {
            "schema": "ztare-synthesis-input-binding-status-v1",
            "status": "unbound",
        },
    }


def test_snapshot_rows_cover_first_five_minute_path_with_provenance() -> None:
    module = load_module()

    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
    )

    labels = {row["label"] for row in rows}
    assert {
        "Project",
        "Bounded claim",
        "Source readiness",
        "Evidence readiness",
        "Run readiness",
        "Readiness check",
        "Readiness history",
        "Report readiness",
        "Latest saved review",
    }.issubset(labels)
    assert module.validate_rows(rows) == []
    assert all(row["provenance"] for row in rows)
    report_row = next(row for row in rows if row["label"] == "Report readiness")
    assert report_row["status"] == "blocked"
    assert "make synth-contract PROJECT=demo" in report_row["command"]
    assert report_row["evidence"] == "projects/demo/synthesis/report_support_contract.json"
    assert report_row["review_artifact"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    latest_review_row = next(row for row in rows if row["label"] == "Latest saved review")
    assert latest_review_row["status"] == "no_review_applied"
    assert latest_review_row["warning"] == "no saved review record"
    assert "ztare-forensic-workbench-review-receipt-v1" in latest_review_row["provenance"]
    evidence_row = next(row for row in rows if row["label"] == "Evidence readiness")
    assert evidence_row["source"] == "projects/demo/workspace/source_index_receipt.json"
    assert evidence_row["evidence"] == "projects/demo/compiled_evidence_provenance.json"
    falsifier_row = next(row for row in rows if row["label"] == "Next falsifier")
    assert falsifier_row["status"] == "recorded"
    assert falsifier_row["display_status"] == "recorded"
    assert falsifier_row["detail"] == "Find a contrary source."


def test_snapshot_next_falsifier_reads_human_intake_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    intake_path = tmp_path / "projects" / "demo" / "demo_intake.json"
    intake_path.parent.mkdir(parents=True)
    intake_path.write_text(json.dumps({"next_falsifier": "A contrary source would change this."}), encoding="utf-8")
    trace = fixture_trace()
    trace["project_intake"].pop("next_falsifier", None)
    trace["project_intake"]["intake_path"] = "projects/demo/demo_intake.json"

    rows = module.build_rows(
        trace,
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
    )

    falsifier_row = next(row for row in rows if row["label"] == "Next falsifier")
    assert falsifier_row["status"] == "recorded"
    assert falsifier_row["detail"] == "A contrary source would change this."
    assert falsifier_row["warning"] == ""


def test_snapshot_rows_surface_applied_review_receipt() -> None:
    module = load_module()
    latest_review = {
        "schema": "ztare-forensic-workbench-review-receipt-v1",
        "applied_at": "2026-06-22T00:00:00Z",
        "project": "demo",
        "row": "Report support",
        "row_slug": "report_export",
        "decision": "blocked",
        "review_file_sha256": "a" * 64,
        "evidence_ref_count": 3,
    }

    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
        latest_review=latest_review,
        latest_review_artifact_path="projects/demo/workspace/forensic_workbench_latest_review.json",
    )

    receipt_row = next(row for row in rows if row["label"] == "Latest saved review")
    assert receipt_row["status"] == "applied"
    assert receipt_row["kind"] == "ready"
    assert receipt_row["file"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert receipt_row["review_artifact"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert "Report readiness: hold report" in receipt_row["detail"]
    assert "3 evidence files" in receipt_row["detail"]


def test_snapshot_rows_surface_applied_intake_edit_receipt() -> None:
    module = load_module()
    latest_intake_edit = {
        "schema": "ztare-forensic-workbench-intake-edit-receipt-v1",
        "applied_at": "2026-06-22T00:00:00Z",
        "project": "demo",
        "intake_path": "projects/demo/demo_intake.json",
        "updated_fields": ["bounded_claim", "next_falsifier"],
        "after_sha256": "c" * 64,
    }

    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
        latest_intake_edit=latest_intake_edit,
        latest_intake_edit_artifact_path="projects/demo/workspace/forensic_workbench_latest_intake_edit.json",
    )

    receipt_row = next(row for row in rows if row["label"] == "Latest intake edit")
    assert receipt_row["status"] == "applied"
    assert receipt_row["kind"] == "ready"
    assert receipt_row["file"] == "projects/demo/workspace/forensic_workbench_latest_intake_edit.json"
    assert "changed fields: bounded_claim, next_falsifier" in receipt_row["detail"]
    assert "after hash" in receipt_row["detail"]


def test_snapshot_loads_latest_review_from_project_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    latest = tmp_path / "projects/demo/workspace/forensic_workbench_latest_review.json"
    latest.parent.mkdir(parents=True)
    latest.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-receipt-v1",
                "project": "demo",
                "row": "Report support",
                "row_slug": "report_export",
                "decision": "blocked",
                "review_file_sha256": "b" * 64,
                "evidence_ref_count": 2,
            }
        ),
        encoding="utf-8",
    )

    payload, path = module.load_latest_review("demo")

    assert path == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert payload["decision"] == "blocked"
    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
        latest_review=payload,
        latest_review_artifact_path=path,
    )
    receipt_row = next(row for row in rows if row["label"] == "Latest saved review")
    assert receipt_row["status"] == "applied"


def test_snapshot_recovers_latest_review_from_case_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    latest = tmp_path / "projects/demo/workspace/forensic_workbench_latest_review.json"
    latest.parent.mkdir(parents=True)
    latest.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-receipt-v1",
                "project": "demo",
                "intake": "projects/demo/other_intake.json",
                "case_key": "demo::projects/demo/other_intake.json",
                "row": "Report support",
                "row_slug": "report_export",
                "decision": "blocked",
                "review_file_sha256": "b" * 64,
                "evidence_ref_count": 2,
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "projects/demo/workspace/forensic_workbench_reviews.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-receipt-v1",
                "project": "demo",
                "intake": "projects/demo/demo_intake.json",
                "case_key": "demo::projects/demo/demo_intake.json",
                "row": "Source readiness",
                "row_slug": "source_readiness",
                "decision": "approved",
                "review_file_sha256": "a" * 64,
                "evidence_ref_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload, path = module.load_latest_review("demo", "projects/demo/demo_intake.json")

    assert path == "projects/demo/workspace/forensic_workbench_reviews.jsonl"
    assert payload["decision"] == "approved"
    assert payload["case_key"] == "demo::projects/demo/demo_intake.json"


def test_snapshot_keeps_unscoped_legacy_latest_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    latest = tmp_path / "projects/demo/workspace/forensic_workbench_latest_review.json"
    latest.parent.mkdir(parents=True)
    latest.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-receipt-v1",
                "project": "demo",
                "row": "Report support",
                "row_slug": "report_export",
                "decision": "blocked",
                "review_file_sha256": "b" * 64,
                "evidence_ref_count": 2,
            }
        ),
        encoding="utf-8",
    )

    payload, _path = module.load_latest_review("demo", "projects/demo/demo_intake.json")

    assert payload["decision"] == "blocked"


def test_snapshot_html_renders_static_workbench_contract(tmp_path: Path) -> None:
    module = load_module()
    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
    )

    rendered = module.render_html(
        fixture_trace(),
        fixture_report_contract(),
        rows,
        output_path=tmp_path / "snapshot.html",
    )

    assert "Project Workbench" in rendered
    assert "Project path" in rendered
    assert "data-provenance=" in rendered
    assert "The report needs refreshed support before it is safe to use." in rendered
    assert "report input is not connected" in rendered
    assert "project data" in rendered
    assert "project snapshot" not in rendered


def test_snapshot_payload_names_single_project_read_model(tmp_path: Path) -> None:
    module = load_module()
    rows = module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
    )

    payload = module.snapshot_payload(
        fixture_trace(),
        fixture_report_contract(),
        rows,
        output_path=tmp_path / "snapshot.html",
        latest_review={
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "item_label": "Report",
            "item_slug": "report_export",
            "row": "Report/export",
            "row_slug": "report_export",
            "decision": "blocked",
        },
    )

    assert payload["snapshot_scope"] == "single_project_read_model"
    assert payload["project_source"] == "projects/demo"
    assert payload["intake"] == "examples/project_packets/demo_intake.json"
    assert payload["intake_source"] == "public_example_intake"
    assert payload["project"] == "demo"
    assert payload["latest_review"]["row"] == "Report readiness"
    assert payload["latest_review"]["item_label"] == "Report readiness"
    assert payload["latest_review"]["row_slug"] == "report_export"


def test_report_contract_missing_context_becomes_blocked_row(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()

    def fake_run(_cmd: list[str], *, timeout: int = 90):  # noqa: ARG001
        return module.subprocess.CompletedProcess(
            args=_cmd,
            returncode=2,
            stdout="",
            stderr="No synthesis context found.",
        )

    monkeypatch.setattr(module, "run", fake_run)

    payload, command = module.collect_report_contract("demo_claims", "decision_brief")

    assert "make synth-contract PROJECT=demo_claims" in command
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["status_reasons"] == ["report_support_unavailable"]
    assert payload["synthesis_input_binding"]["status"] == "unavailable"
    assert "No synthesis context found" in payload["error"]


def test_project_index_lists_projects_with_intakes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    demo = tmp_path / "projects/demo"
    demo.mkdir(parents=True)
    (demo / "demo_intake.json").write_text("{}", encoding="utf-8")
    workspace = demo / "workspace"
    workspace.mkdir()
    (workspace / "forensic_workbench_latest_source_import.json").write_text("{}", encoding="utf-8")
    (workspace / "forensic_workbench_latest_source_edit.json").write_text("{}", encoding="utf-8")
    (workspace / "forensic_workbench_latest_source_action.json").write_text("{}", encoding="utf-8")
    (workspace / "forensic_workbench_latest_case_file_write.json").write_text("{}", encoding="utf-8")
    no_intake = tmp_path / "projects/no_intake"
    no_intake.mkdir()
    (no_intake / "thesis.md").write_text("Candidate thesis.\n", encoding="utf-8")
    (no_intake / "evidence.txt").write_text("Candidate evidence.\n", encoding="utf-8")
    (tmp_path / "projects/bad/project").mkdir(parents=True)

    entries = module.list_project_entries()
    folders = module.list_project_folders(entries)

    assert entries == [
        {
            "project": "demo",
            "rubric": "demo",
            "project_dir": "projects/demo",
            "intake": "projects/demo/demo_intake.json",
            "intake_source": "project_local_intake",
            "latest_review": "",
            "latest_project_check": "",
            "latest_item_action": "",
            "latest_row_action": "",
            "latest_intake_edit": "",
            "latest_source_import": "projects/demo/workspace/forensic_workbench_latest_source_import.json",
            "latest_source_edit": "projects/demo/workspace/forensic_workbench_latest_source_edit.json",
            "latest_source_action": "projects/demo/workspace/forensic_workbench_latest_source_action.json",
            "latest_project_file_write": "projects/demo/workspace/forensic_workbench_latest_case_file_write.json",
            "latest_case_file_write": "projects/demo/workspace/forensic_workbench_latest_case_file_write.json",
            "report_contract": "",
        }
    ]
    folder_core = [
        {
            key: row[key]
            for key in (
                "project",
                "project_dir",
                "intake_count",
                "raw_exists",
                "workspace_exists",
                "source_type_map_exists",
                "openable",
                "status",
            )
        }
        for row in folders
    ]
    assert folder_core == [
        {
            "project": "bad",
            "project_dir": "projects/bad",
            "intake_count": 0,
            "raw_exists": False,
            "workspace_exists": False,
            "source_type_map_exists": False,
            "openable": False,
            "status": "needs_intake",
        },
        {
            "project": "demo",
            "project_dir": "projects/demo",
            "intake_count": 1,
            "raw_exists": False,
            "workspace_exists": True,
            "source_type_map_exists": False,
            "openable": True,
            "status": "intake_ready",
        },
        {
            "project": "no_intake",
            "project_dir": "projects/no_intake",
            "intake_count": 0,
            "raw_exists": False,
            "workspace_exists": False,
            "source_type_map_exists": False,
            "openable": False,
            "status": "needs_intake",
        },
    ]
    assert all("raw_file_count" in row and "workspace_file_count" in row for row in folders)
    no_intake_row = next(row for row in folders if row["project"] == "no_intake")
    assert no_intake_row["root_source_file_count"] == 2
    assert no_intake_row["source_preview_files"] == [
        "projects/no_intake/thesis.md",
        "projects/no_intake/evidence.txt",
    ]


def test_project_index_filters_latest_paths_to_current_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    demo = tmp_path / "projects/demo"
    demo.mkdir(parents=True)
    (demo / "demo_intake.json").write_text("{}", encoding="utf-8")
    workspace = demo / "workspace"
    workspace.mkdir()
    other_case = {
        "schema": "ztare-forensic-workbench-source-import-v1",
        "project": "demo",
        "intake": "projects/demo/other_intake.json",
        "case_key": "demo::projects/demo/other_intake.json",
    }
    current_case = {
        "schema": "ztare-forensic-workbench-source-edit-v1",
        "project": "demo",
        "intake": "projects/demo/demo_intake.json",
        "case_key": "demo::projects/demo/demo_intake.json",
    }
    (workspace / "forensic_workbench_latest_source_import.json").write_text(json.dumps(other_case), encoding="utf-8")
    (workspace / "forensic_workbench_latest_source_edit.json").write_text(json.dumps(current_case), encoding="utf-8")
    (workspace / "forensic_workbench_latest_review.json").write_text(json.dumps(other_case), encoding="utf-8")
    (workspace / "forensic_workbench_latest_row_action.json").write_text(json.dumps(other_case), encoding="utf-8")
    (workspace / "forensic_workbench_latest_intake_edit.json").write_text(json.dumps(other_case), encoding="utf-8")
    (workspace / "forensic_workbench_reviews.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_row_actions.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_intake_edits.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_source_imports.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_source_actions.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_case_files.jsonl").write_text(json.dumps(current_case) + "\n", encoding="utf-8")
    (workspace / "forensic_workbench_latest_case_file_write.json").write_text(
        json.dumps({**other_case, "schema": "ztare-forensic-workbench-case-file-write-receipt-v1"}),
        encoding="utf-8",
    )

    [entry] = module.list_project_entries()

    assert entry["latest_intake_edit"] == "projects/demo/workspace/forensic_workbench_intake_edits.jsonl"
    assert entry["latest_source_import"] == "projects/demo/workspace/forensic_workbench_source_imports.jsonl"
    assert entry["latest_source_edit"] == "projects/demo/workspace/forensic_workbench_latest_source_edit.json"
    assert entry["latest_source_action"] == "projects/demo/workspace/forensic_workbench_source_actions.jsonl"
    assert entry["latest_review"] == "projects/demo/workspace/forensic_workbench_reviews.jsonl"
    assert entry["latest_project_check"] == "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    assert entry["latest_row_action"] == "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    assert entry["latest_project_file_write"] == "projects/demo/workspace/forensic_workbench_case_files.jsonl"
    assert entry["latest_case_file_write"] == "projects/demo/workspace/forensic_workbench_case_files.jsonl"


def test_project_index_lists_multiple_project_intakes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    demo = tmp_path / "projects/demo"
    demo.mkdir(parents=True)
    (demo / "demo_intake.json").write_text("{}", encoding="utf-8")
    (demo / "second_intake.json").write_text("{}", encoding="utf-8")

    entries = module.list_project_entries()

    assert [entry["intake"] for entry in entries] == [
        "projects/demo/demo_intake.json",
        "projects/demo/second_intake.json",
    ]
    assert {module.case_key(entry["project"], entry["intake"]) for entry in entries} == {
        "demo::projects/demo/demo_intake.json",
        "demo::projects/demo/second_intake.json",
    }


def test_project_index_includes_public_example_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    example = tmp_path / "examples/project_packets/ready_demo_claims_intake.json"
    example.parent.mkdir(parents=True)
    example.write_text("{}", encoding="utf-8")

    entries = module.list_project_entries()

    assert entries == [
        {
            "project": "demo_claims",
            "rubric": "demo_claims",
            "project_dir": "",
            "intake": "examples/project_packets/ready_demo_claims_intake.json",
            "intake_source": "public_example_intake",
            "latest_review": "",
            "latest_project_check": "",
            "latest_item_action": "",
            "latest_row_action": "",
            "latest_intake_edit": "",
            "latest_source_import": "",
            "latest_source_edit": "",
            "latest_source_action": "",
            "latest_project_file_write": "",
            "latest_case_file_write": "",
            "report_contract": "",
        }
    ]
    assert module.default_intake_for_project("demo_claims") == "examples/project_packets/ready_demo_claims_intake.json"


def test_project_index_prefers_project_local_intake_over_public_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    project_dir = tmp_path / "projects/demo_claims"
    project_dir.mkdir(parents=True)
    (project_dir / "demo_claims_intake.json").write_text("{}", encoding="utf-8")
    example = tmp_path / "examples/project_packets/ready_demo_claims_intake.json"
    example.parent.mkdir(parents=True)
    example.write_text("{}", encoding="utf-8")

    entries = module.list_project_entries()

    assert entries == [
        {
            "project": "demo_claims",
            "rubric": "demo_claims",
            "project_dir": "projects/demo_claims",
            "intake": "projects/demo_claims/demo_claims_intake.json",
            "intake_source": "project_local_intake",
            "latest_review": "",
            "latest_project_check": "",
            "latest_item_action": "",
            "latest_row_action": "",
            "latest_intake_edit": "",
            "latest_source_import": "",
            "latest_source_edit": "",
            "latest_source_action": "",
            "latest_project_file_write": "",
            "latest_case_file_write": "",
            "report_contract": "",
        }
    ]


def test_project_index_keeps_example_intake_source_when_project_dir_has_no_intake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    (tmp_path / "projects/demo_claims").mkdir(parents=True)
    example = tmp_path / "examples/project_packets/ready_demo_claims_intake.json"
    example.parent.mkdir(parents=True)
    example.write_text("{}", encoding="utf-8")

    entries = module.list_project_entries()

    assert entries == [
        {
            "project": "demo_claims",
            "rubric": "demo_claims",
            "project_dir": "projects/demo_claims",
            "intake": "examples/project_packets/ready_demo_claims_intake.json",
            "intake_source": "public_example_intake",
            "latest_review": "",
            "latest_project_check": "",
            "latest_item_action": "",
            "latest_row_action": "",
            "latest_intake_edit": "",
            "latest_source_import": "",
            "latest_source_edit": "",
            "latest_source_action": "",
            "latest_project_file_write": "",
            "latest_case_file_write": "",
            "report_contract": "",
        }
    ]


def test_project_slug_rejects_path_traversal() -> None:
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_project_slug("../private")


def test_file_preview_api_reads_repo_relative_text_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    target = tmp_path / "projects/demo/source.md"
    target.parent.mkdir(parents=True)
    target.write_text("claim source\nsee projects/demo/raw/source.md\n", encoding="utf-8")
    referenced = tmp_path / "projects/demo/raw/source.md"
    referenced.parent.mkdir(parents=True)
    referenced.write_text("referenced source\n", encoding="utf-8")

    payload = module.file_preview_payload("projects/demo/source.md")

    assert payload["schema"] == "ztare-forensic-workbench-file-preview-v1"
    assert payload["path"] == "projects/demo/source.md"
    assert payload["display_kind"] == "Project file"
    assert payload["format"] == "Markdown"
    assert payload["line_count"] == 2
    assert payload["non_empty_line_count"] == 2
    assert len(payload["sha256"]) == 64
    assert payload["referenced_paths"] == ["projects/demo/raw/source.md"]
    assert payload["truncated"] is False
    assert "claim source" in payload["text"]
    with pytest.raises(ValueError):
        module.file_preview_payload("../outside.md")
    with pytest.raises(ValueError):
        module.file_preview_payload("papers/cognitive-camouflage/draft.md")


def test_public_scope_rejects_unlisted_project_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module, "PROJECT_SCOPE", "public")
    monkeypatch.setattr(module, "PROJECT_ALLOWLIST", {"shared"})
    for project in ("shared", "private"):
        target = tmp_path / "projects" / project / "note.md"
        target.parent.mkdir(parents=True)
        target.write_text(f"{project} note\n", encoding="utf-8")

    assert module.file_preview_payload("projects/shared/note.md")["text"] == "shared note\n"
    with pytest.raises(FileNotFoundError, match="not available"):
        module.file_preview_payload("projects/private/note.md")


def test_file_preview_promotes_saved_project_recent_change_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    target = tmp_path / "projects/demo/workspace/forensic_workbench_case_file_abcdef123456.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-case-file-v1",
                "project": "demo",
                "project_summary": {
                    "schema": "ztare-saved-project-summary-v1",
                    "project": "demo",
                    "recent_changes": {
                        "latest_source_or_evidence_change": {
                            "artifact_path": "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json",
                            "receipt_path": "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
                        },
                        "substantive_inspection": {
                            "preview_path": "projects/demo/workspace/latest_eval_results.json",
                            "reason": "Open the run file to see the latest score, weakest point, and evidence gaps.",
                        }
                    },
                    "proof_paths": [
                        "projects/demo/workspace/evidence_fetch_manifest_<timestamp>.json",
                        "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json",
                        "projects/demo/demo_intake.json",
                    ],
                    "file_inventory": {
                        "previewable_files": [
                            {"path": "projects/demo/thesis.md"},
                        ]
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/workspace/forensic_workbench_case_file_abcdef123456.json")

    assert payload["display_kind"] == "Project file"
    assert payload["referenced_paths"][:4] == [
        "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json",
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        "projects/demo/workspace/latest_eval_results.json",
        "projects/demo/demo_intake.json",
    ]
    assert payload["referenced_paths"][:5] == [
        "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json",
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        "projects/demo/workspace/latest_eval_results.json",
        "projects/demo/demo_intake.json",
        "projects/demo/thesis.md",
    ]
    assert "projects/demo/thesis.md" in payload["referenced_paths"]
    assert "projects/demo/workspace/evidence_fetch_manifest_<timestamp>.json" not in payload["referenced_paths"]


def test_file_preview_expands_project_relative_json_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "raw").mkdir(parents=True)
    (project_root / "workspace" / "source_notes").mkdir(parents=True)
    (project_root / "raw" / "source.md").write_text("source\n", encoding="utf-8")
    (project_root / "workspace" / "source_notes" / "S001.json").write_text("{}\n", encoding="utf-8")
    source_index = project_root / "workspace" / "source_index.json"
    source_index.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "path": "source.md",
                        "note_path": "source_notes/S001.json",
                        "source_id": "S001",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/workspace/source_index.json")

    assert payload["display_kind"] == "Source index"
    assert payload["referenced_paths"][:2] == [
        "projects/demo/raw/source.md",
        "projects/demo/workspace/source_notes/S001.json",
    ]
    assert payload["referenced_items"][:2] == [
        {
            "path": "projects/demo/raw/source.md",
            "kind": "source",
            "display_kind": "Source",
            "format": "Markdown",
            "exists": True,
            "label": "Source: source.md",
        },
        {
            "path": "projects/demo/workspace/source_notes/S001.json",
            "kind": "source_note",
            "display_kind": "Source note",
            "format": "JSON",
            "exists": True,
            "label": "Source note: S001.json",
        },
    ]


def test_file_preview_classifies_source_note_and_links_raw_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "raw").mkdir(parents=True)
    (project_root / "workspace" / "source_notes").mkdir(parents=True)
    (project_root / "raw" / "source.md").write_text("source body\n", encoding="utf-8")
    note_path = project_root / "workspace" / "source_notes" / "S001.json"
    note_path.write_text(
        json.dumps(
            {
                "source_id": "S001",
                "source_path": "source.md",
                "source_summary": "The source supports the bounded thesis.",
                "source_type": "source_evidence",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/workspace/source_notes/S001.json")

    assert payload["display_kind"] == "Source note"
    assert payload["referenced_paths"][:1] == ["projects/demo/raw/source.md"]


def test_file_preview_links_evidence_gap_required_surface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "raw").mkdir(parents=True)
    (project_root / "workspace").mkdir(parents=True)
    (project_root / "raw" / "source.md").write_text("source body\n", encoding="utf-8")
    gap_path = project_root / "workspace" / "latest_evidence_gaps.json"
    gap_path.write_text(
        json.dumps(
            {
                "project": "demo",
                "weakest_point": "The thesis needs one more source.",
                "evidence_gaps": [
                    {
                        "target": "missing source",
                        "description": "Need a backing source.",
                        "required_surface": "source.md",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/workspace/latest_evidence_gaps.json")

    assert payload["display_kind"] == "Evidence gap"
    assert payload["referenced_paths"][:1] == ["projects/demo/raw/source.md"]


def test_file_preview_classifies_evidence_gap_resolution_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "raw").mkdir(parents=True)
    (project_root / "workspace").mkdir(parents=True)
    (project_root / "raw" / "source.md").write_text("source body\n", encoding="utf-8")
    (project_root / "workspace" / "latest_evidence_gaps.json").write_text("{}\n", encoding="utf-8")
    receipt_path = project_root / "workspace" / "evidence_gap_resolutions.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema": "ztare-evidence-gap-resolutions-v1",
                "project": "demo",
                "resolution_count": 1,
                "resolutions": [
                    {
                        "resolution_id": "egr_demo",
                        "target": "missing source",
                        "status": "justified",
                        "reason": "The local source now supports the gap.",
                        "gap_source_path": "projects/demo/workspace/latest_evidence_gaps.json",
                        "evidence_refs": [{"path": "raw/source.md"}],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/workspace/evidence_gap_resolutions.json")

    assert payload["display_kind"] == "Evidence-gap history"
    assert payload["referenced_paths"][:2] == [
        "projects/demo/workspace/latest_evidence_gaps.json",
        "projects/demo/raw/source.md",
    ]


def test_file_preview_classifies_workbench_docs_as_guides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    target = tmp_path / "docs/concepts/forensic_workbench_interface.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Project workbench interface\n\nReport support docs.\n", encoding="utf-8")

    payload = module.file_preview_payload("docs/concepts/forensic_workbench_interface.md")

    assert payload["kind"] == "guide"
    assert payload["display_kind"] == "Guide"


def test_file_preview_classifies_iteration_telemetry_as_run_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    target = tmp_path / "projects/demo/workspace/iteration_telemetry.jsonl"
    target.parent.mkdir(parents=True)
    target.write_text('{"record_type":"run_start","run_id":1}\n', encoding="utf-8")

    payload = module.file_preview_payload("projects/demo/workspace/iteration_telemetry.jsonl")

    assert payload["kind"] == "run_results"
    assert payload["display_kind"] == "Run results"


def test_file_preview_classifies_run_setup_and_synthesis_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    workspace = tmp_path / "projects/demo/workspace"
    workspace.mkdir(parents=True)
    (workspace / "cold_shot_runs.jsonl").write_text('{"event":"policy_decision","families":[]}\n', encoding="utf-8")
    (workspace / "post_run_synthesis_attempts.jsonl").write_text('{"attempts_count":0,"attempts":[]}\n', encoding="utf-8")

    setup = module.file_preview_payload("projects/demo/workspace/cold_shot_runs.jsonl")
    synthesis = module.file_preview_payload("projects/demo/workspace/post_run_synthesis_attempts.jsonl")

    assert setup["kind"] == "run_policy_decisions"
    assert setup["display_kind"] == "Run setup choices"
    assert synthesis["kind"] == "report_synthesis_attempts"
    assert synthesis["display_kind"] == "Report synthesis attempts"


def test_file_preview_classifies_probability_dag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    target = tmp_path / "projects/demo/latest_probability_dag.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"outcome": {"label": "thesis", "probability": 0.7}, "nodes": [], "edges": []}),
        encoding="utf-8",
    )

    payload = module.file_preview_payload("projects/demo/latest_probability_dag.json")

    assert payload["kind"] == "probability_model"
    assert payload["display_kind"] == "Probability model"


def test_file_preview_classifies_current_draft_and_project_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects/demo"
    project_root.mkdir(parents=True)
    (project_root / "current_iteration.md").write_text("# Current draft\n", encoding="utf-8")
    (project_root / "test_model.py").write_text("assert True\n", encoding="utf-8")

    draft = module.file_preview_payload("projects/demo/current_iteration.md")
    test_file = module.file_preview_payload("projects/demo/test_model.py")

    assert draft["kind"] == "current_draft"
    assert draft["display_kind"] == "Current draft"
    assert test_file["kind"] == "project_test"
    assert test_file["display_kind"] == "Project test"


def test_file_preview_classifies_project_launch_bundle_without_renaming_evidence_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects/demo"
    project_root.mkdir(parents=True)
    (project_root / "demo_packet.json").write_text(
        json.dumps(
            {
                "project": "demo",
                "bounded_claim": "The project thesis has enough support to run.",
                "expected_command": "make autoresearch-run PROJECT=demo",
                "source_refs": ["projects/demo/raw/source.md"],
                "evidence_refs": ["projects/demo/evidence.txt"],
            }
        ),
        encoding="utf-8",
    )
    (project_root / "compiled_evidence_packet.json").write_text("{}\n", encoding="utf-8")

    launch_bundle = module.file_preview_payload("projects/demo/demo_packet.json")
    evidence_bundle = module.file_preview_payload("projects/demo/compiled_evidence_packet.json")

    assert launch_bundle["kind"] == "project_launch_bundle"
    assert launch_bundle["display_kind"] == "Project launch bundle"
    assert evidence_bundle["kind"] == "evidence"
    assert evidence_bundle["display_kind"] == "Evidence"


def test_project_file_inventory_collects_previewable_project_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    for path, text in {
        project_root / "demo_intake.json": "{}\n",
        project_root / "project_charter.md": "# Demo Project Charter\n",
        project_root / "raw" / "source.md": "source\n",
        project_root / "compiled_evidence_packet.json": "{}\n",
        project_root / "workspace" / "latest_evidence_gaps.json": "{}\n",
        project_root / "workspace" / "derived_constraints.json": "{}\n",
        project_root / "latest_eval_results.json": "{}\n",
        project_root / "synthesis" / "report_support_contract.json": "{}\n",
        project_root / "workspace" / "forensic_workbench_reviews.jsonl": "{}\n",
        project_root / "workspace" / "forensic_workbench_project_file_123456789abc.json": "{}\n",
        project_root / "workspace" / "forensic_workbench_latest_project_file_write.json": json.dumps(
            {
                "kind": "project_file",
                "project_file_path": "projects/demo/workspace/forensic_workbench_project_file_123456789abc.json",
                "applied_at": "2026-06-27T14:22:42Z",
            }
        )
        + "\n",
    }.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    payload = module.project_file_inventory_payload(
        project="demo",
        intake="projects/demo/demo_intake.json",
        source_list={},
        evidence_readiness={"compiled_packet": "projects/demo/compiled_evidence_packet.json"},
        evidence_gap_recovery={
            "file": "projects/demo/workspace/latest_evidence_gaps.json",
            "gaps": [{"target": "causal direction", "required_surface": "S009_generation_rules.md"}],
        },
        report={
            "report_support_contract": "projects/demo/synthesis/report_support_contract.json",
            "backing_files": [{"label": "Report contract", "path": "projects/demo/synthesis/report_support_contract.json"}],
        },
        run_history={
            "paths": {"latest_eval": "projects/demo/latest_eval_results.json"},
            "recent_runs": [{"artifact_refs": ["projects/demo/workspace/derived_constraints.json"]}],
        },
        receipts={
            "paths": {
                "review": "projects/demo/workspace/forensic_workbench_reviews.jsonl",
                "project_file": "projects/demo/workspace/forensic_workbench_project_files.jsonl",
            },
            "receipts": [],
        },
        axiom_state={"backing_files": []},
        thesis_support={"evidence_support_file_path": "projects/demo/compiled_evidence_packet.json"},
    )

    items_by_path = {item["path"]: item for item in payload["items"]}
    assert payload["schema"] == "ztare-project-file-inventory-v1"
    assert payload["previewable_count"] >= 6
    file_groups = {group["id"]: group for group in payload["file_groups"]}
    assert file_groups["overview"]["label"] == "Charter, thesis & brief"
    assert file_groups["overview"]["count"] == 3
    assert file_groups["overview"]["action"]["subsection"] == "Charter"
    assert file_groups["evidence"]["count"] >= 3
    assert items_by_path["projects/demo/project_charter.md"]["role"] == "charter"
    assert items_by_path["projects/demo/project_charter.md"]["label"] == "Project charter"
    assert items_by_path["projects/demo/project_charter.md"]["role_order"] < items_by_path[
        "projects/demo/demo_intake.json"
    ]["role_order"]
    assert items_by_path["projects/demo/demo_intake.json"]["label"] == "Project brief"
    assert items_by_path["projects/demo/demo_intake.json"]["display_kind"] == "Project brief"
    assert items_by_path["projects/demo/demo_intake.json"]["role_order"] < items_by_path[
        "projects/demo/compiled_evidence_packet.json"
    ]["role_order"]
    assert items_by_path["projects/demo/raw/source.md"]["role"] == "source"
    assert items_by_path["projects/demo/compiled_evidence_packet.json"]["role"] == "evidence"
    assert items_by_path["projects/demo/compiled_evidence_packet.json"]["priority"] < items_by_path[
        "projects/demo/raw/S009_generation_rules.md"
    ]["priority"]
    assert items_by_path["projects/demo/workspace/latest_evidence_gaps.json"]["role"] == "evidence_gap"
    assert items_by_path["projects/demo/raw/S009_generation_rules.md"]["role"] == "evidence_gap"
    assert items_by_path["projects/demo/raw/S009_generation_rules.md"]["label"] == "Needed evidence"
    assert items_by_path["projects/demo/raw/S009_generation_rules.md"]["display_kind"] == "Needed evidence"
    assert items_by_path["projects/demo/raw/S009_generation_rules.md"]["exists"] is False
    assert items_by_path["projects/demo/raw/S009_generation_rules.md"]["previewable"] is False
    assert items_by_path["projects/demo/latest_eval_results.json"]["role"] == "run"
    assert items_by_path["projects/demo/workspace/derived_constraints.json"]["role"] == "axiom"
    assert items_by_path["projects/demo/workspace/derived_constraints.json"]["label"] == "Run-learned assumptions"
    assert items_by_path["projects/demo/synthesis/report_support_contract.json"]["role"] == "report"
    assert payload["latest_project_file"] == "projects/demo/workspace/forensic_workbench_project_file_123456789abc.json"
    assert payload["latest_project_file_write"] == "projects/demo/workspace/forensic_workbench_latest_project_file_write.json"
    assert items_by_path["projects/demo/workspace/forensic_workbench_project_file_123456789abc.json"]["role"] == "project_file"
    assert items_by_path["projects/demo/workspace/forensic_workbench_latest_project_file_write.json"]["label"] == "Latest project file"
    assert items_by_path["projects/demo/workspace/forensic_workbench_reviews.jsonl"]["role"] == "receipt"


def test_validate_rows_rejects_missing_provenance() -> None:
    module = load_module()

    errors = module.validate_rows([{"label": "Project", "provenance": ""}])

    assert "row lacks provenance: Project" in errors
    assert any("missing rows" in error for error in errors)


def test_apply_review_file_writes_file_backed_receipt(tmp_path: Path) -> None:
    module = load_review_module()
    review_file = {
        "schema": "ztare-forensic-workbench-review-v1",
        "project": "demo",
        "rubric": "demo",
        "row": "Report support",
        "row_status": "blocked",
        "decision": "blocked",
        "note": "Need source binding before export.",
        "evidence_refs": [
            {"type": "evidence", "value": "projects/demo/synthesis/report_support_contract.json"},
            {"type": "command", "value": "make synth-contract PROJECT=demo"},
            {"type": "review", "value": "projects/demo/workspace/forensic_workbench_latest_review.json"},
        ],
    }
    review_file_path = tmp_path / "report_export_review.json"
    ledger = tmp_path / "reviews.jsonl"
    latest = tmp_path / "latest.json"
    review_file_path.write_text(json.dumps(review_file), encoding="utf-8")

    result = module.apply_review(
        Namespace(
            project="demo",
            row="report_export",
            review_file_path=str(review_file_path),
            intake="projects/demo/demo_intake.json",
            ledger=str(ledger),
            latest=str(latest),
        )
    )

    assert result["ok"] is True
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["decision"] == "blocked"
    assert rows[0]["row_slug"] == "report_export"
    assert rows[0]["intake"] == "projects/demo/demo_intake.json"
    assert rows[0]["case_key"] == "demo::projects/demo/demo_intake.json"
    assert json.loads(latest.read_text(encoding="utf-8"))["review_file_sha256"] == rows[0]["review_file_sha256"]


def test_apply_review_payload_writes_same_receipt_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_review_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    review_file = {
        "schema": "ztare-forensic-workbench-review-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "case_key": "demo::projects/demo/demo_intake.json",
        "row": "Report support",
        "row_status": "blocked",
        "decision": "blocked",
        "note": "Need source binding before export.",
        "evidence_refs": [
            {"type": "evidence", "value": "projects/demo/synthesis/report_support_contract.json"},
        ],
    }

    result = module.apply_review_payload(
        review_file,
        project="demo",
        row="report_export",
        review_file_path="local-api:demo/report_export",
    )

    latest = tmp_path / "projects/demo/workspace/forensic_workbench_latest_review.json"
    ledger = tmp_path / "projects/demo/workspace/forensic_workbench_reviews.jsonl"
    receipt = json.loads(latest.read_text(encoding="utf-8"))
    ledger_row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert result["ok"] is True
    assert receipt == ledger_row
    assert receipt["review_file_path"] == "local-api:demo/report_export"
    assert receipt["evidence_ref_count"] == 1
    assert receipt["intake"] == "projects/demo/demo_intake.json"
    assert receipt["case_key"] == "demo::projects/demo/demo_intake.json"


def test_review_validation_rejects_other_case_when_intake_is_supplied() -> None:
    module = load_review_module()
    review_file = {
        "schema": "ztare-forensic-workbench-review-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/other_intake.json",
        "project_key": "demo::projects/demo/other_intake.json",
        "case_key": "demo::projects/demo/other_intake.json",
        "row": "Report support",
        "row_status": "blocked",
        "decision": "blocked",
        "note": "Need source binding before export.",
        "evidence_refs": [
            {"type": "evidence", "value": "projects/demo/synthesis/report_support_contract.json"},
        ],
    }
    legacy_review_file = {
        key: value
        for key, value in review_file.items()
        if key not in {"intake", "project_key", "case_key"}
    }

    errors = module.validate_review_file(
        review_file,
        project="demo",
        row="report_export",
        intake="projects/demo/demo_intake.json",
    )
    legacy_errors = module.validate_review_file(
        legacy_review_file,
        project="demo",
        row="report_export",
        intake="projects/demo/demo_intake.json",
    )

    assert any("project_key mismatch" in error for error in errors)
    assert any("case_key mismatch" in error for error in errors)
    assert any("intake mismatch" in error for error in errors)
    assert legacy_errors == []

    alias_errors = module.validate_review_file(
        {**legacy_review_file, "project_check_slug": "source_readiness"},
        project="demo",
        row="report_export",
        intake="projects/demo/demo_intake.json",
    )
    assert any("project_check_slug mismatch" in error for error in alias_errors)


def test_live_item_file_context_rejects_stale_rubric_and_case() -> None:
    module = load_server_module()
    payload = {
        "schema": "ztare-forensic-workbench-review-v1",
        "project": "demo",
        "rubric": "other",
        "intake": "projects/demo/other_intake.json",
        "project_key": "demo::projects/demo/other_intake.json",
        "case_key": "demo::projects/demo/other_intake.json",
        "row": "Report support",
        "decision": "blocked",
        "evidence_refs": [{"type": "evidence", "value": "projects/demo/synthesis/report_support_contract.json"}],
    }

    with pytest.raises(ValueError, match="rubric"):
        module.live_row_payload_with_case(
            payload,
            project="demo",
            rubric="demo",
            intake="projects/demo/demo_intake.json",
        )
    with pytest.raises(ValueError, match="project key"):
        module.live_row_payload_with_case(
            {**payload, "rubric": "demo", "intake": "projects/demo/demo_intake.json", "case_key": "demo::projects/demo/demo_intake.json"},
            project="demo",
            rubric="demo",
            intake="projects/demo/demo_intake.json",
        )


def test_review_api_preserves_receipt_when_snapshot_refresh_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)

    def fake_apply_review_payload(
        payload: dict,
        *,
        project: str,
        row: str,
        review_file_path: str,
        intake: str | None = None,
    ) -> dict:
        assert payload["schema"] == "ztare-forensic-workbench-review-v1"
        assert payload["intake"] == "projects/demo/demo_intake.json"
        assert payload["case_key"] == "demo::projects/demo/demo_intake.json"
        assert payload["project_check_slug"] == "report_export"
        assert payload["item_slug"] == "report_export"
        assert payload["row_slug"] == "report_export"
        assert payload["project_check_label"] == "Report readiness"
        assert payload["item_label"] == "Report readiness"
        assert intake == "projects/demo/demo_intake.json"
        assert project == "demo"
        assert row == "report_export"
        assert review_file_path.startswith("projects/demo/workspace/forensic_workbench_applied/")
        assert "_report_export_review_" in review_file_path
        persisted = tmp_path / review_file_path
        assert persisted.exists()
        assert json.loads(persisted.read_text(encoding="utf-8")) == payload
        return {"ok": True, "receipt": {"project": project, "row_slug": row}}

    def fake_snapshot_payload_for_project(*, project: str, intake: str | None = None, **_kwargs: object) -> dict:
        assert project == "demo"
        assert intake == "projects/demo/demo_intake.json"
        raise SystemExit("trace refresh failed")

    monkeypatch.setattr(module.review, "apply_review_payload", fake_apply_review_payload)
    monkeypatch.setattr(module, "snapshot_payload_for_project", fake_snapshot_payload_for_project)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps(
            {
                "project": "demo",
                "rubric": "demo",
                "intake": "projects/demo/demo_intake.json",
                "project_check_slug": "report_export",
                "review_file": {
                    "schema": "ztare-forensic-workbench-review-v1",
                    "project": "demo",
                    "rubric": "demo",
                    "row": "Report support",
                    "decision": "blocked",
                    "evidence_refs": [{"type": "evidence", "value": "x"}],
                },
            }
        )
        conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        conn.request("POST", "/api/review", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert response.status == 200
    assert payload["ok"] is True
    assert payload["review"]["ok"] is True
    assert payload["project_check_label"] == "Report readiness"
    assert payload["project_check_slug"] == "report_export"
    assert payload["snapshot"] is None
    assert payload["snapshot_error"] == "trace refresh failed"


def test_preflight_payload_runs_only_preflight_command(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    seen: dict[str, object] = {}

    def fake_project_intake_path(project: str, intake: str | None = None, *, allow_examples: bool = False) -> Path:
        assert project == "demo"
        assert intake == "projects/demo/demo_intake.json"
        assert allow_examples is True
        return Path("projects/demo/demo_intake.json")

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        seen["command"] = command
        seen["timeout"] = timeout
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="checks ok\nautoresearch preflight-only: launch inputs and intake boundary accepted\n",
            stderr="",
        )

    monkeypatch.setattr(module, "project_intake_path", fake_project_intake_path)
    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(
        module,
        "trace_payload_for_project",
        lambda **_kwargs: {"schema": "ztare-forensic-workbench-trace-v1", "project": "demo", "loop_admission": {"receipt_count": 1}},
    )
    monkeypatch.setattr(
        module,
        "snapshot_payload_for_project",
        lambda **_kwargs: {"schema": "ztare-forensic-workbench-snapshot-v1", "project": "demo"},
    )

    payload = module.preflight_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
    )

    assert payload["schema"] == "ztare-forensic-workbench-preflight-v1"
    assert payload["accepted"] is True
    assert payload["returncode"] == 0
    assert payload["trace"]["loop_admission"]["receipt_count"] == 1
    assert payload["snapshot"]["project"] == "demo"
    assert payload["write_boundary"]["write_paths"] == ["projects/demo/workspace/iteration_telemetry.jsonl"]
    assert payload["write_boundary"]["read_only_actions"] == ["Copy command", "Inspect output"]
    assert seen["timeout"] == 120
    command = seen["command"]
    assert isinstance(command, list)
    assert "--preflight-only" in command
    assert command[:5] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "autoresearch", "run"]


def test_preflight_payload_failed_check_keeps_target_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()

    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(
        module.snapshot,
        "run",
        lambda command, *, timeout=90: subprocess.CompletedProcess(
            args=command,
            returncode=2,
            stdout="",
            stderr="source index missing",
        ),
    )
    monkeypatch.setattr(
        module,
        "trace_payload_for_project",
        lambda **_kwargs: {"schema": "ztare-forensic-workbench-trace-v1", "project": "demo", "loop_admission": {"receipt_count": 0}},
    )
    monkeypatch.setattr(
        module,
        "snapshot_payload_for_project",
        lambda **_kwargs: {"schema": "ztare-forensic-workbench-snapshot-v1", "project": "demo"},
    )

    payload = module.preflight_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
    )

    assert payload["accepted"] is False
    assert payload["ok"] is False
    assert payload["write_boundary"]["writes_project_files"] is False
    assert payload["write_boundary"]["write_paths"] == ["projects/demo/workspace/iteration_telemetry.jsonl"]
    assert payload["write_boundary"]["receipt_path"] == "projects/demo/workspace/iteration_telemetry.jsonl"
    assert "No files changed" in payload["write_boundary"]["no_change_boundary"]
    assert payload["write_boundary"]["browser_writes"] is False


def test_bounded_run_payload_requires_confirmation_and_uses_surfaced_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    commands: list[list[str]] = []
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    trace = {
        "schema": "ztare-forensic-workbench-trace-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "kernel_entry": {
            "can_enter_kernel": True,
            "run_command": "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json --iters 1",
        },
        "plan_preview": {"status": "ready_for_bounded_run"},
    }

    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "trace_payload_for_project", lambda **_kwargs: trace)
    monkeypatch.setattr(module, "run_history_payload_for_project", lambda **_kwargs: {"schema": "ztare-forensic-workbench-run-history-v1", "summary": {"run_rows": 1}})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "demo", "rows": []})

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="run finished", stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)

    preview = module.bounded_run_payload_for_project(project="demo", confirmed=False)
    payload = module.bounded_run_payload_for_project(project="demo", confirmed=True)

    assert preview["ok"] is True
    assert preview["label"] == "Project run"
    assert preview["status"] == "needs_confirmation"
    assert preview["display_status"] == "needs confirmation"
    assert preview["requires_confirmation"] is True
    assert preview["can_run"] is True
    assert preview["accepted"] is False
    assert preview["writes"] is False
    assert preview["model_spend_starts_at"] == "confirmed_project_run"
    assert preview["write_boundary"]["writes_project_files"] is False
    assert preview["write_boundary"]["read_only_actions"] == ["Inspect readiness", "Copy command"]
    assert preview["confirmed_write_boundary"]["writes_project_files"] is True
    assert preview["confirmed_write_boundary"]["receipt_path"] == "projects/demo/workspace/iteration_telemetry.jsonl"
    assert preview["confirmed_write_boundary"]["latest_path"] == "projects/demo/latest_eval_results.json"
    assert preview["confirmed_write_boundary"]["read_only_actions"] == ["Inspect readiness", "Copy command"]
    assert "projects/demo/latest_eval_results.json" in preview["confirmed_write_boundary"]["write_paths"]
    assert "projects/demo/workspace/eval_history.jsonl" in preview["confirmed_write_boundary"]["write_paths"]
    assert "projects/demo/eval_results.jsonl" not in preview["confirmed_write_boundary"]["write_paths"]
    assert preview["command"] == (
        "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json --iters 1 "
        "--llm-timeout-seconds 600 --llm-retries 3"
    )
    assert preview["effective_settings"] == {
        "mutator": "",
        "judge": "",
        "inverter": "",
        "llm_timeout_seconds": "600",
        "llm_retries": "3",
        "model_fallback": "0",
        "transport": "api",
        "judging": "single",
        "rubric_mode": "fixed",
        "cross_family": "0",
    }
    assert commands == [[
        module.SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "autoresearch",
        "run",
        "--project",
        "demo",
        "--rubric",
        "demo",
        "--intake",
        "projects/demo/demo_intake.json",
        "--iters",
        "1",
        "--llm-timeout-seconds",
        "600",
        "--llm-retries",
        "3",
    ]]
    assert payload["ok"] is True
    assert payload["accepted"] is True
    assert payload["returncode"] == 0
    assert payload["writes"] is True
    assert payload["write_boundary"]["writes_project_files"] is True
    assert payload["write_boundary"]["receipt_path"] == "projects/demo/workspace/iteration_telemetry.jsonl"
    assert payload["write_boundary"]["latest_path"] == "projects/demo/latest_eval_results.json"
    assert "projects/demo/latest_eval_results.json" in payload["write_boundary"]["write_paths"]
    assert "projects/demo/workspace/eval_history.jsonl" in payload["write_boundary"]["write_paths"]
    assert "projects/demo/eval_results.jsonl" not in payload["write_boundary"]["write_paths"]


def test_bounded_run_payload_uses_workbench_run_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "ZTARE_WORKBENCH_RUN_MUTATOR_MODEL=claude",
                "ZTARE_WORKBENCH_RUN_JUDGE_MODEL=gpt4.1",
                "ZTARE_WORKBENCH_RUN_INVERTER_MODEL=deepseek",
                "ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT=120",
                "ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES=1",
                "ZTARE_WORKBENCH_MODEL_FALLBACK=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    trace = {
        "schema": "ztare-forensic-workbench-trace-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "kernel_entry": {
            "can_enter_kernel": True,
            "run_command": "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json --iters 1 --mutator old --judge old",
        },
        "plan_preview": {"status": "ready_for_bounded_run"},
    }
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "trace_payload_for_project", lambda **_kwargs: trace)

    preview = module.bounded_run_payload_for_project(project="demo", confirmed=False)

    assert preview["command"] == (
        "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json --iters 1 "
        "--mutator claude --judge gpt4.1 --inverter deepseek --llm-timeout-seconds 120 --llm-retries 1 "
        "--allow-model-fallback"
    )
    assert preview["effective_settings"] == {
        "mutator": "claude",
        "judge": "gpt4.1",
        "inverter": "deepseek",
        "llm_timeout_seconds": "120",
        "llm_retries": "1",
        "model_fallback": "1",
        "transport": "api",
        "judging": "single",
        "rubric_mode": "fixed",
        "cross_family": "0",
    }


def test_bounded_run_blank_settings_strip_trace_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    trace = {
        "schema": "ztare-forensic-workbench-trace-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "kernel_entry": {
            "can_enter_kernel": True,
            "run_command": (
                "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json "
                "--iters 1 --mutator kimi --judge grok --inverter deepseek --llm-timeout-seconds 240 --llm-retries 1"
            ),
        },
        "plan_preview": {"status": "ready_for_bounded_run"},
    }
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "trace_payload_for_project", lambda **_kwargs: trace)

    preview = module.bounded_run_payload_for_project(project="demo", confirmed=False)

    assert preview["command"] == (
        "ztare autoresearch run --project demo --rubric demo --intake projects/demo/demo_intake.json "
        "--iters 1 --llm-timeout-seconds 240 --llm-retries 1"
    )
    assert preview["effective_settings"]["mutator"] == ""
    assert preview["effective_settings"]["judge"] == ""
    assert preview["effective_settings"]["inverter"] == ""


def test_run_api_requires_boolean_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    seen: dict[str, object] = {}

    def fake_bounded_run_payload_for_project(**kwargs: object) -> dict:
        seen.update(kwargs)
        return {
            "schema": "ztare-forensic-workbench-bounded-run-v1",
            "ok": True,
            "status": "needs_confirmation",
            "requires_confirmation": True,
            "accepted": False,
            "write_boundary": {"writes_project_files": False, "write_paths": []},
        }

    monkeypatch.setattr(module, "bounded_run_payload_for_project", fake_bounded_run_payload_for_project)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps(
            {
                "project": "demo",
                "rubric": "demo",
                "intake": "projects/demo/demo_intake.json",
                "confirmed": "false",
            }
        )
        conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        conn.request("POST", "/api/run", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert response.status == 200
    assert payload["requires_confirmation"] is True
    assert seen["confirmed"] is False


def test_run_api_not_ready_is_not_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()

    def fake_bounded_run_payload_for_project(**_kwargs: object) -> dict:
        return {
            "schema": "ztare-forensic-workbench-bounded-run-v1",
            "ok": False,
            "error": "Project is not ready for a run. Run preflight first.",
            "requires_confirmation": False,
            "accepted": False,
            "write_boundary": {"writes_project_files": False, "write_paths": []},
        }

    monkeypatch.setattr(module, "bounded_run_payload_for_project", fake_bounded_run_payload_for_project)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps(
            {
                "project": "demo",
                "rubric": "demo",
                "intake": "projects/demo/demo_intake.json",
                "confirmed": False,
            }
        )
        conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        conn.request("POST", "/api/run", body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert response.status == 200
    assert payload["requires_confirmation"] is False
    assert payload["write_boundary"]["writes_project_files"] is False


def test_bounded_run_preview_names_first_recovery_step(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(
        module,
        "trace_payload_for_project",
        lambda **_kwargs: {
            "plan_preview": {
                "status": "blocked_before_kernel_entry",
                "recommended_first_command": "make evidence-fetch PROJECT=demo SEVERITY=degrading",
            },
            "kernel_entry": {
                "can_enter_kernel": False,
                "blockers": [
                    {
                        "id": "out_of_loop_evidence_recovery",
                        "next_command": "make evidence-fetch PROJECT=demo SEVERITY=degrading",
                        "recovery_channel": "out_of_loop_evidence_recovery",
                    }
                ],
            },
            "blocking_missing": ["out_of_loop_evidence_recovery"],
        },
    )
    monkeypatch.setattr(
        module,
        "evidence_gap_list_payload_for_project",
        lambda **_kwargs: {
            "summary": "1 active evidence gap needs fetch or justification (1 degrading).",
            "active_gaps": [
                {
                    "target": "causal_direction",
                    "required_surface": "S009_generation_rules.md",
                    "fetch_query": "Does the fixture include the isolation rows?",
                    "description": "Missing fixture-generation proof.",
                }
            ],
            "receipt_paths": [
                "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
                "projects/demo/workspace/evidence_gap_resolutions.json",
            ],
            "write_paths": ["projects/demo/evidence.txt"],
        },
    )

    payload = module.bounded_run_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        confirmed=False,
    )

    assert payload["ok"] is False
    assert payload["requires_confirmation"] is False
    assert payload["status"] == "blocked_before_run"
    assert payload["next_action"] == {
        "id": "out_of_loop_evidence_recovery",
        "label": "Fetch or justify evidence gaps",
        "detail": "Project is not ready for a run. First: Fetch or justify evidence gaps.",
        "command": "make evidence-fetch PROJECT=demo SEVERITY=degrading",
        "workspace": "sources",
        "subsection": "Prepare files",
        "local_step": "Open evidence gaps",
    }
    assert payload["error"] == payload["next_action"]["detail"]
    assert "Run preflight first" not in payload["error"]
    assert payload["blocker_explanation"]["summary"] == "1 active evidence gap needs fetch or justification (1 degrading)."
    assert payload["blocker_explanation"]["target"] == "causal_direction"
    assert payload["blocker_explanation"]["missing_surface"] == "S009_generation_rules.md"
    assert payload["blocker_explanation"]["question_to_answer"] == "Does the fixture include the isolation rows?"
    assert "missing support" in payload["blocker_explanation"]["why_it_blocks"]
    assert "hash-bound justification" in payload["blocker_explanation"]["closes_when"]
    assert payload["blocker_explanation"]["receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        "projects/demo/workspace/evidence_gap_resolutions.json",
    ]
    assert payload["write_boundary"]["writes_project_files"] is False


def test_live_launcher_reuses_existing_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_live_module()
    launched: list[list[str]] = []
    launched_envs: list[dict[str, str] | None] = []

    class FakeProcess:
        returncode = 0

        def __init__(self, command: list[str], cwd: Path | None = None) -> None:
            self.command = command
            self.cwd = cwd
            self.terminated = False

        def poll(self) -> int | None:
            return None if not self.terminated else self.returncode

        def wait(self, timeout: float | None = None) -> int:
            if timeout is None:
                return self.returncode
            self.terminated = True
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.terminated = True

    def fake_popen(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> FakeProcess:
        launched.append(command)
        launched_envs.append(env)
        return FakeProcess(command, cwd=cwd)

    monkeypatch.setattr(module, "api_status", lambda *_args, **_kwargs: {"project_inventory_scope": "local"})
    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)

    rc = module.run_live(
        Namespace(
            api_host="127.0.0.1",
            api_port=8765,
            api_url="http://127.0.0.1:8765",
            app_url="http://127.0.0.1:5174",
            host="",
            port=0,
            api_startup_timeout=1.0,
            api_poll_interval=0.1,
            project_scope="local",
            projects="",
        )
    )

    assert rc == 0
    assert len(launched) == 1
    assert launched[0][:4] == ["npm", "--prefix", "forensic-workbench", "run"]
    assert launched_envs[0]
    assert launched_envs[0]["ZTARE_WORKBENCH_API_TARGET"] == "http://127.0.0.1:8765"


def test_live_launcher_checks_lightweight_status_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_live_module()
    seen_urls: list[str] = []

    class FakeResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"project_inventory_scope":"local"}'

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        seen_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    assert module.api_ready("http://127.0.0.1:8765", timeout=0.1)
    assert seen_urls == ["http://127.0.0.1:8765/api/status"]


def test_live_launcher_refuses_to_reuse_a_different_project_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_live_module()
    monkeypatch.setattr(module, "ensure_web_deps", lambda: True)
    monkeypatch.setattr(module, "api_status", lambda *_args, **_kwargs: {"project_inventory_scope": "local"})
    monkeypatch.setattr(
        module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("a mismatched API must not launch or reuse the frontend"),
    )

    rc = module.run_live(
        Namespace(
            api_host="127.0.0.1",
            api_port=8765,
            api_url="http://127.0.0.1:8765",
            app_url="http://127.0.0.1:5174",
            host="",
            port=0,
            api_startup_timeout=1.0,
            api_poll_interval=0.1,
            project_scope="public",
            projects="",
        )
    )

    assert rc == 2


def test_live_launcher_waits_long_enough_for_project_status(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_live_module()
    seen_timeouts: list[float] = []

    class FakeProcess:
        def poll(self) -> None:
            return None

    def fake_api_ready(_api_url: str, *, timeout: float) -> bool:
        seen_timeouts.append(timeout)
        return True

    monkeypatch.setattr(module, "api_ready", fake_api_ready)

    assert module.wait_for_api("http://127.0.0.1:8765", FakeProcess(), startup_timeout=1.0, poll_interval=0.1)
    assert seen_timeouts == [1.0]


def test_run_history_payload_surfaces_latest_verdict_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    synthesis = project_root / "synthesis"
    workspace.mkdir(parents=True)
    synthesis.mkdir()
    (project_root / "demo_intake.json").write_text(json.dumps({"project": "demo"}), encoding="utf-8")
    (workspace / "eval_history.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"run_id": 1, "iteration": 0, "score": 40, "weakest_point": "too broad"}),
                json.dumps(
                    {
                        "run_id": 2,
                        "iteration": 1,
                        "score": 82,
                        "weakest_point": "missing direct rival test",
                        "artifact_refs": ["projects/demo/latest_eval_results.json"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "iteration_telemetry.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "run_start",
                        "run_id": 7,
                        "timestamp_utc": "2026-06-26T00:00:00Z",
                        "preflight_only": True,
                        "mutator_model": "kimi",
                        "judge_model": "grok",
                        "project_packet": {
                            "packet_status": "valid_packet",
                            "kernel_entry_status": "ready",
                        },
                    }
                ),
                json.dumps(
                    {
                        "record_type": "run_end",
                        "run_id": 7,
                        "timestamp_utc": "2026-06-26T00:00:01Z",
                        "preflight_only": True,
                        "run_exit_reason": "preflight_only",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 8,
                        "iteration_index": 1,
                        "score": 40,
                        "score_improved": True,
                        "wall_clock_seconds": 10.0,
                        "estimated_cost_usd": 0.01,
                        "pending_loop_action": "CONTINUE",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 8,
                        "iteration_index": 2,
                        "score": 41,
                        "score_improved": False,
                        "wall_clock_seconds": 15.0,
                        "estimated_cost_usd": 0.02,
                        "pending_loop_action": "CONTINUE",
                        "compression_progress_advice": {
                            "status": "available",
                            "recommendation": "narrow_or_pivot",
                            "rationale": "No compression improvement for 3 iterations.",
                            "usable_observations": 2,
                            "stagnation_length": 3,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_001.json").write_text(
        json.dumps({"rmse": 0.25, "n_fit_rows": 100, "k_params": 3}),
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_002.json").write_text(
        json.dumps({"rmse": 0.30, "n_fit_rows": 100, "k_params": 3}),
        encoding="utf-8",
    )
    (project_root / "latest_eval_results.json").write_text(
        json.dumps(
            {
                "score": 82,
                "weakest_point": "missing direct rival test",
                "evidence_gaps": [{"target": "rival", "severity": "degrading", "description": "Need direct test."}],
                "probability_dag": {"outcome": {"label": "bounded verdict", "probability": 0.72}},
            }
        ),
        encoding="utf-8",
    )
    (project_root / "champion_eval_results.json").write_text(json.dumps({"score": 88, "weakest_point": "champion gap"}), encoding="utf-8")
    (synthesis / "history_summary.json").write_text(
        json.dumps({"recurring_failures": ["correlation bridge"], "major_pivots": ["bounded scope"]}),
        encoding="utf-8",
    )

    payload = module.run_history_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
    )

    assert payload["schema"] == "ztare-forensic-workbench-run-history-v1"
    assert payload["ok"] is True
    assert payload["intake"] == "projects/demo/demo_intake.json"
    assert payload["case_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["run_scope"] == "project_run_history"
    assert payload["intake_scoped_files"] is False
    assert payload["summary"]["run_rows"] == 2
    assert payload["summary"]["latest_score"] == 82
    assert payload["summary"]["best_score"] == 88
    assert payload["latest_eval"]["evidence_gap_count"] == 1
    assert payload["champion_eval"]["score"] == 88
    assert payload["recent_runs"][-1]["artifact_refs"] == ["projects/demo/latest_eval_results.json"]
    assert payload["synthesis_history"]["recurring_failures"] == ["correlation bridge"]
    assert payload["summary"]["latest_preflight_status"] == "accepted"
    assert payload["latest_preflight"]["run_id"] == 7
    assert payload["latest_preflight"]["file"] == "projects/demo/workspace/iteration_telemetry.jsonl"
    assert payload["compression_progress"]["schema"] == "ztare-forensic-workbench-compression-progress-v1"
    assert payload["compression_progress"]["usable_observations"] == 2
    assert payload["compression_progress"]["latest_effort"] == 25.0
    assert payload["compression_progress"]["total_cost_usd"] == 0.03
    assert payload["compression_progress"]["latest_iteration_advice"]["recommendation"] == "narrow_or_pivot"
    assert payload["compression_progress"]["controller_alignment"]["status"] == "compression_warns_first"
    assert payload["compression_progress"]["complexity_runtime_profile"][-1]["loop_action"] == "CONTINUE"
    assert payload["compression_progress"]["complexity_runtime_profile"][-1]["recorded_advice"]["recommendation"] == "narrow_or_pivot"
    assert payload["compression_progress"]["complexity_runtime_profile"][-1]["source"] == "projects/demo/workspace/fit_result_iter_002.json"


def test_run_history_counts_latest_eval_when_eval_history_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (project_root / "demo_intake.json").write_text(json.dumps({"project": "demo"}), encoding="utf-8")
    (project_root / "latest_eval_results.json").write_text(
        json.dumps({"score": 74, "weakest_point": "needs direct rival test"}),
        encoding="utf-8",
    )

    payload = module.run_history_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
    )

    assert payload["summary"]["run_rows"] == 1
    assert payload["summary"]["eval_history_rows"] == 0
    assert payload["summary"]["latest_score"] == 74
    assert payload["summary"]["best_score"] == 74
    assert payload["recent_runs"] == []


def test_report_contract_payload_surfaces_project_scope_with_selected_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    (project_root / "demo_intake.json").write_text(json.dumps({"project": "demo"}), encoding="utf-8")
    contract_path = project_root / "synthesis" / "report_support_contract.json"
    contract_path.parent.mkdir()
    contract_path.write_text(
        json.dumps(
            {
                "ok": False,
                "status": "blocked",
                "status_reasons": [
                    "synthesis_input_binding_unbound",
                    "out_of_loop_evidence_recovery",
                    "out_of_loop_evidence_recovery",
                ],
                "report_support_contract": str(contract_path),
                "synthesis_input_binding": {
                    "schema": "ztare-synthesis-input-binding-v1",
                    "ok": False,
                    "status": "unbound",
                    "reason": "no bound inputs",
                    "artifact_count": 0,
                    "current_digest": "abc",
                    "ledger_digest": "def",
                },
                "report_action_authority": {
                    "allowed_now": [
                        {
                            "action_id": "allowed_now:test",
                            "label": (
                                "Inspect autoresearch health.: ztare autoresearch health "
                                "--project stale --rubric stale --intake projects/stale/stale_intake.json --json"
                            ),
                            "source": "support_contract.next_actions",
                        },
                        {
                            "action_id": "allowed_now:preflight_label",
                            "label": "Run the model-free launch preflight to verify local setup.",
                            "source": "support_contract.next_actions",
                        }
                    ],
                    "conditional": [
                        {
                            "action_id": "conditional_action:test",
                            "condition": "if_negative",
                            "label": "If no cache counterexample appears, keep the export-cause thesis.",
                            "source": "ledger.decision_rule",
                        }
                    ],
                    "deferred": [
                        {
                            "action_id": "deferred_action:test",
                            "label": "Generalizing to production is out of scope.",
                            "source": "planning_brief.what_to_defer",
                        }
                    ],
                    "forbidden_upgrades": [
                        {
                            "action_id": "forbidden_upgrade:test",
                            "label": "Cache is an independent root cause.",
                            "source": "support_contract.unsupported_or_unresolved",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    payload = module.report_contract_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        renderer="decision_brief",
    )

    assert payload["schema"] == "ztare-forensic-workbench-report-contract-v1"
    assert payload["intake"] == "projects/demo/demo_intake.json"
    assert payload["project_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["case_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["report_scope"] == "project_report_support"
    assert payload["intake_scoped_command"] is False
    assert payload["status"] == "blocked"
    assert "evidence gap needs fetch or justification" in payload["display_status_reasons"]
    issues_by_reason = {row["reason"]: row for row in payload["support_issues"]}
    assert issues_by_reason["out_of_loop_evidence_recovery"]["display_reason"] == (
        "evidence gap needs fetch or justification"
    )
    assert [row["reason"] for row in payload["support_issues"]].count("out_of_loop_evidence_recovery") == 1
    assert payload["report_support_contract"] == "projects/demo/synthesis/report_support_contract.json"
    assert len(payload["allowed_actions"]) == 2
    allowed_action = payload["allowed_actions"][0]
    assert allowed_action["id"] == "allowed_now:test"
    assert allowed_action["label"] == "Inspect autoresearch health"
    assert allowed_action["source"] == "support_contract.next_actions"
    assert allowed_action["command"] == (
        "ztare autoresearch health --project demo --rubric demo "
        "--intake projects/demo/demo_intake.json --json"
    )
    assert allowed_action["workspace"] == "run"
    assert allowed_action["subsection"] == "Fix warnings"
    assert allowed_action["primary_label"] == "Open warnings"
    assert allowed_action["write_boundary"]["writes_project_files"] is False
    assert allowed_action["write_boundary"]["write_paths"] == []
    label_action = payload["allowed_actions"][1]
    assert label_action["command"] == ""
    assert label_action["workspace"] == "run"
    assert label_action["subsection"] == "Check readiness"
    assert label_action["primary_label"] == "Open readiness check"
    assert label_action["write_boundary"]["writes_project_files"] is False
    assert payload["conditional_actions"] == [
        {
            "condition": "if_negative",
            "id": "conditional_action:test",
            "label": "If no cache counterexample appears, keep the export-cause thesis.",
            "source": "ledger.decision_rule",
        }
    ]
    assert payload["deferred_actions"] == [
        {
            "condition": "",
            "id": "deferred_action:test",
            "label": "Generalizing to production is out of scope.",
            "source": "planning_brief.what_to_defer",
        }
    ]
    assert payload["forbidden_upgrades"] == [
        {
            "condition": "",
            "id": "forbidden_upgrade:test",
            "label": "Cache is an independent root cause.",
            "source": "support_contract.unsupported_or_unresolved",
        }
    ]
    assert [row["id"] for row in payload["repair_actions"]] == [
        "follow_report_next_action",
        "refresh_report_inputs",
        "rerun_report_support",
        "save_report_review",
    ]
    assert payload["repair_actions"][0]["detail"] == "Inspect autoresearch health"
    assert payload["repair_actions"][0]["command"] == (
        "ztare autoresearch health --project demo --rubric demo "
        "--intake projects/demo/demo_intake.json --json"
    )
    assert payload["repair_actions"][0]["workspace"] == "run"
    assert payload["repair_actions"][0]["subsection"] == "Fix warnings"
    assert payload["repair_actions"][0]["primary_label"] == "Open warnings"
    assert payload["repair_actions"][0]["command"] == (
        "ztare autoresearch health --project demo --rubric demo "
        "--intake projects/demo/demo_intake.json --json"
    )
    assert payload["repair_actions"][1]["requires_confirmation"] is True
    assert payload["repair_actions"][1]["command"] == (
        "ztare forensic-workbench report-action --project demo --action refresh_inputs "
        "--renderer decision_brief --confirmed --json"
    )
    assert payload["repair_actions"][2]["command"] == (
        "ztare forensic-workbench report-action --project demo --action check_readiness "
        "--renderer decision_brief --confirmed --json"
    )
    assert payload["repair_actions"][2]["requires_confirmation"] is True
    assert payload["repair_actions"][3]["receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_reviews.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_review.json",
    ]


def test_report_contract_refresh_preview_and_confirm_write_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    synthesis = project_root / "synthesis"
    workspace.mkdir(parents=True)
    synthesis.mkdir()
    (project_root / "demo_intake.json").write_text(json.dumps({"project": "demo"}), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, root, env, timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        contract = {
            "ok": True,
            "status": "ready",
            "status_reasons": [],
            "report_support_contract": str(synthesis / "report_support_contract.json"),
            "synthesis_input_binding": {"schema": "binding", "ok": True, "status": "bound", "reason": "ok"},
        }
        (synthesis / "report_support_contract.json").write_text(json.dumps(contract), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(contract), stderr="")

    monkeypatch.setattr(module.report_actions_core, "run_command", fake_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    preview = module.report_contract_refresh_payload_for_project(project="demo")
    confirmed = module.report_contract_refresh_payload_for_project(project="demo", confirmed=True)

    assert preview["status"] == "needs_confirmation"
    assert preview["write_boundary"]["writes_project_files"] is False
    assert preview["confirmed_write_boundary"]["writes_project_files"] is True
    assert confirmed["accepted"] is True
    assert confirmed["status"] == "ready"
    assert confirmed["receipt_path"] == "projects/demo/workspace/forensic_workbench_report_support_checks.jsonl"
    assert confirmed["receipt"]["report_support_contract"] == "projects/demo/synthesis/report_support_contract.json"
    assert commands == [["make", "synth-contract", "PROJECT=demo", "RENDERER=decision_brief", f"PYTHON={module.snapshot.PYTHON}"]]


def test_source_action_payload_uses_bounded_source_index_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, root=None, env=None, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        workspace = project_root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        if "evidence-bind" in command:
            artifact = project_root / "evidence.txt"
            artifact.write_text("compiled evidence\n", encoding="utf-8")
            payload = {
                "path": str(workspace / "evidence_output_binding_receipt.json"),
                "receipt": {
                    "schema": "ztare-evidence-output-binding-receipt-v1",
                    "status": "bound",
                    "provenance_path": "projects/demo/compiled_evidence_provenance.json",
                    "artifacts": [
                        {
                            "artifact_id": "evidence_output",
                            "path": "projects/demo/evidence.txt",
                            "sha256": module.hashlib.sha256(b"compiled evidence\n").hexdigest(),
                        }
                    ],
                },
            }
        elif command[:2] == ["make", "evidence-prepare"]:
            artifact = project_root / "evidence.txt"
            provenance = project_root / "compiled_evidence_provenance.json"
            artifact.write_text("prepared evidence\n", encoding="utf-8")
            provenance.write_text('{"schema": "compiled-evidence-provenance"}\n', encoding="utf-8")
            payload = {"ok": True, "status": "prepared"}
        else:
            source_index = workspace / "source_index.json"
            source_index.write_text('{"sources": []}\n', encoding="utf-8")
            payload = {
                "ok": True,
                "status": "fresh",
                "path": "projects/demo/workspace/source_index.json",
            }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload) + "\n", stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module.source_actions_core, "run_command", fake_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "trace_payload_for_project", lambda **_kwargs: {"readiness": "ready"})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "demo", "rows": []})

    payload = module.source_action_payload_for_project(project="demo", action="source_index")
    bind_payload = module.source_action_payload_for_project(project="demo", action="evidence_bind")
    prepare_payload = module.source_action_payload_for_project(project="demo", action="evidence_prepare")
    confirmed_prepare_payload = module.source_action_payload_for_project(project="demo", action="evidence_prepare", confirmed=True)

    assert payload["schema"] == "ztare-forensic-workbench-source-action-v1"
    assert payload["accepted"] is True
    assert payload["writes"] is True
    assert payload["command"] == "ztare project source-index --project demo --index-only --json"
    assert bind_payload["writes"] is True
    assert bind_payload["command"] == "ztare project evidence-bind --project demo --json"
    assert prepare_payload["writes"] is True
    assert prepare_payload["requires_confirmation"] is True
    assert prepare_payload["status"] == "needs_confirmation"
    expected_prepare_command = (
        "make evidence-prepare PROJECT=demo MODEL_FALLBACK=0 "
        "EVIDENCE_LLM_TIMEOUT=300 EVIDENCE_LLM_RETRIES=4"
    )
    assert prepare_payload["command"] == expected_prepare_command
    assert prepare_payload["write_boundary"]["writes_project_files"] is False
    assert prepare_payload["confirmed_write_boundary"]["writes_project_files"] is True
    assert "projects/demo/evidence.txt" in prepare_payload["confirmed_write_boundary"]["write_paths"]
    assert "receipt" not in prepare_payload
    assert confirmed_prepare_payload["writes"] is True
    assert confirmed_prepare_payload["requires_confirmation"] is True
    assert confirmed_prepare_payload["command"] == expected_prepare_command
    assert confirmed_prepare_payload["receipt"]["source_path"] == "projects/demo/evidence.txt"
    assert confirmed_prepare_payload["receipt"]["source_receipt_path"] == "projects/demo/compiled_evidence_provenance.json"
    assert confirmed_prepare_payload["write_boundary"]["receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_source_actions.jsonl"
    )
    assert confirmed_prepare_payload["write_boundary"]["latest_path"] == (
        "projects/demo/workspace/forensic_workbench_latest_source_action.json"
    )
    assert "projects/demo/compiled_evidence_packet.json" in confirmed_prepare_payload["write_boundary"]["write_paths"]
    assert "projects/demo/compiled_evidence_replay_manifest.json" in confirmed_prepare_payload["write_boundary"]["write_paths"]
    assert payload["parsed_output"]["path"] == "projects/demo/workspace/source_index.json"
    assert payload["receipt_path"] == "projects/demo/workspace/forensic_workbench_source_actions.jsonl"
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_source_action.json"
    assert payload["receipt"]["schema"] == "ztare-forensic-workbench-source-action-receipt-v1"
    assert payload["receipt"]["action"] == "source_index"
    assert payload["receipt"]["intake"] == "projects/demo/demo_intake.json"
    assert payload["receipt"]["case_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["receipt"]["source_path"] == "projects/demo/workspace/source_index.json"
    assert payload["receipt"]["source_sha256"] == module.hashlib.sha256(b'{"sources": []}\n').hexdigest()
    latest = json.loads((project_root / "workspace" / "forensic_workbench_latest_source_action.json").read_text(encoding="utf-8"))
    ledger_rows = (project_root / "workspace" / "forensic_workbench_source_actions.jsonl").read_text(encoding="utf-8").splitlines()
    assert latest["action"] == "evidence_prepare"
    assert latest["source_path"] == "projects/demo/evidence.txt"
    assert latest["source_sha256"] == module.hashlib.sha256(b"prepared evidence\n").hexdigest()
    assert len(ledger_rows) == 3
    assert str(tmp_path) not in payload["stdout_tail"]
    assert str(tmp_path) not in json.dumps(payload)
    assert str(tmp_path) not in json.dumps(prepare_payload)
    assert commands == [
        [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "source-index", "--project", "demo", "--index-only", "--json"],
        [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "evidence-bind", "--project", "demo", "--json"],
        [
            "make",
            "evidence-prepare",
            "PROJECT=demo",
            "MODEL_FALLBACK=0",
            "EVIDENCE_LLM_TIMEOUT=300",
            "EVIDENCE_LLM_RETRIES=4",
        ],
    ]


def test_workbench_settings_save_feed_source_action_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    (project_root / "demo_intake.json").write_text('{"project": "demo"}\n', encoding="utf-8")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret\nZTARE_WORKBENCH_MODEL=model_a\n", encoding="utf-8")
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    saved = module.save_settings_payload(
        {
            "ZTARE_WORKBENCH_MODEL": "claude",
            "ZTARE_EVIDENCE_SEARCH_BACKEND": "anthropic",
            "ZTARE_WORKBENCH_FETCH_SEVERITY": "blocking",
            "ZTARE_WORKBENCH_MAX_FETCHES": "2",
            "ZTARE_WORKBENCH_AUTO_COMPILE": "0",
            "ZTARE_WORKBENCH_EVIDENCE_LLM_TIMEOUT": "120",
            "ZTARE_WORKBENCH_EVIDENCE_LLM_RETRIES": "1",
            "ZTARE_WORKBENCH_MODEL_FALLBACK": "1",
            "OPENAI_API_KEY": "new-secret",
            "DEEPSEEK_API_KEY": "deepseek-secret",
        }
    )
    preview = module.source_action_payload_for_project(project="demo", action="evidence_prepare")

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert saved["saved"] is True
    assert saved["values"]["ZTARE_WORKBENCH_MODEL"] == "claude"
    assert "OPENAI_API_KEY" not in saved["values"]
    assert saved["updated_provider_keys"] == ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]
    assert saved["write_boundary"]["writes_project_files"] is False
    assert saved["write_boundary"]["writes_repo_files"] is True
    assert saved["write_boundary"]["write_paths"] == [".env"]
    assert "Accepted settings saves can change only the local .env settings file" in saved["write_boundary"]["no_change_boundary"]
    assert "OPENAI_API_KEY=new-secret" in env_text
    assert "DEEPSEEK_API_KEY=deepseek-secret" in env_text
    openai_key = next(row for row in saved["provider_keys"] if row["key"] == "OPENAI_API_KEY")
    deepseek_key = next(row for row in saved["provider_keys"] if row["key"] == "DEEPSEEK_API_KEY")
    assert openai_key["present"] is True
    assert deepseek_key["present"] is True
    assert openai_key["value_hidden"] is True
    assert "new-secret" not in json.dumps(saved)
    assert preview["command"] == (
        "make evidence-prepare PROJECT=demo MODEL=claude MODEL_FALLBACK=1 "
        "EVIDENCE_LLM_TIMEOUT=120 EVIDENCE_LLM_RETRIES=1"
    )


def test_project_run_settings_save_crosses_cli_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    (tmp_path / "projects" / "demo").mkdir(parents=True)

    payload = module.save_run_config_payload({
        "project": "demo",
        "values": {
            "ZTARE_WORKBENCH_RUN_ITERS": "5",
            "ZTARE_WORKBENCH_RUN_TRANSPORT": "subscription",
        },
    })

    saved = json.loads((tmp_path / payload["config_path"]).read_text(encoding="utf-8"))
    assert payload["saved"] is True
    assert payload["updated_keys"] == ["ZTARE_WORKBENCH_RUN_ITERS", "ZTARE_WORKBENCH_RUN_TRANSPORT"]
    assert saved["values"] == {
        "ZTARE_WORKBENCH_RUN_ITERS": "5",
        "ZTARE_WORKBENCH_RUN_TRANSPORT": "subscription",
    }


def test_claim_card_build_and_receipt_cross_cli_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    synthesis = tmp_path / "projects" / "demo" / "synthesis"
    synthesis.mkdir(parents=True)
    (synthesis / "report_support_contract.json").write_text(
        json.dumps({
            "status": "supported",
            "hardest_conclusion": {"claim": "Bounded conclusion"},
            "claim_strength": {"epistemic_note": "Bounded to the checked sources."},
            "supported_claims": [{"claim": "Bounded conclusion"}],
            "source_artifact_paths": [],
        }),
        encoding="utf-8",
    )

    payload = module.build_claim_card_payload({
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
    })

    assert payload["accepted"] is True
    assert payload["preview_path"] == "projects/demo/synthesis/claim_card.html"
    assert (tmp_path / payload["json_path"]).exists()
    assert (tmp_path / payload["receipt_path"]).exists()
    assert payload["write_boundary"]["write_paths"] == payload["write_paths"]


def test_evidence_fetch_preview_and_confirm_write_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    command_context = module.workbench_command_context
    monkeypatch.setattr(
        module,
        "workbench_command_context",
        lambda project, rubric=None: {
            **command_context(project, rubric),
            "evidence_search_backend": "auto",
        },
    )
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (project_root / "raw").mkdir()
    (project_root / "demo_intake.json").write_text('{"project": "demo"}\n', encoding="utf-8")
    commands: list[list[str]] = []

    def fake_workbench_run(command: list[str], *, timeout: int = 90, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "record-evidence-fetch" in command:
            receipt = json.loads(Path(command[command.index("--from") + 1]).read_text(encoding="utf-8"))
            ledger = workspace / "forensic_workbench_evidence_fetches.jsonl"
            latest = workspace / "forensic_workbench_latest_evidence_fetch.json"
            ledger.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            latest.write_text(json.dumps(receipt), encoding="utf-8")
            result = {
                "ok": True,
                "receipt_path": "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
                "latest": "projects/demo/workspace/forensic_workbench_latest_evidence_fetch.json",
                "receipt": receipt,
            }
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(result), stderr="")
        manifest = {
            "fetched_at": "2026-06-22T00:00:00Z",
            "project": "demo",
            "severity_filter": "degrading",
            "search_backend": "anthropic",
            "total_attempted": 1,
            "total_accepted": 1,
            "skipped_duplicates": 0,
            "fetches": [{"gap_index": 0, "status": "accepted"}],
        }
        (workspace / "evidence_fetch_manifest_20260622T000000Z.json").write_text(json.dumps(manifest), encoding="utf-8")
        (project_root / "evidence.txt").write_text("evidence\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="Manifest: evidence_fetch_manifest_20260622T000000Z.json\n", stderr="")

    monkeypatch.setattr(module, "run_workbench_command", fake_workbench_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(
        module,
        "evidence_gap_list_payload_for_project",
        lambda **_kwargs: {
            "active_evidence_gap_count": 1,
            "active_gap_count": 1,
            "gap_count": 1,
            "summary": "One active evidence gap.",
            "active_gaps": [{"claim": "missing source"}],
        },
    )
    monkeypatch.setattr(module, "claim_support_payload_for_project", lambda **_kwargs: {"status": "usable"})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "demo", "rows": []})

    preview = module.evidence_fetch_payload_for_project(project="demo")
    confirmed = module.evidence_fetch_payload_for_project(project="demo", confirmed=True)

    assert preview["status"] == "needs_confirmation"
    assert preview["accepted"] is False
    assert preview["write_boundary"]["writes_project_files"] is False
    assert preview["confirmed_write_boundary"]["writes_project_files"] is True
    assert preview["gap_count"] == 1
    assert preview["active_gap_count"] == 1
    assert preview["gap_summary"] == "One active evidence gap."
    assert preview["active_gaps"] == [{"claim": "missing source"}]
    assert preview["command"] == (
        f"{module.SERVER_PYTHON} -m src.ztare.cli project evidence-fetch --project demo "
        "--severity degrading --max-fetches 3 --search-backend auto"
    )
    assert confirmed["accepted"] is True
    assert confirmed["manifest_path"] == "projects/demo/workspace/evidence_fetch_manifest_20260622T000000Z.json"
    assert confirmed["receipt_path"] == "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl"
    assert confirmed["receipt"]["total_accepted"] == 1
    assert confirmed["receipt"]["search_backend"] == "anthropic"
    assert confirmed["receipt"]["failure_counts"] == {}
    assert confirmed["receipt"]["recovery_hints"] == []
    quota_manifest = {
        "fetched_at": "2026-06-22T01:00:00Z",
        "project": "demo",
        "search_backend": "anthropic",
        "total_attempted": 2,
        "total_accepted": 0,
        "failure_counts": {"provider_quota": 2},
        "fetches": [
            {"gap_index": 0, "status": "provider_quota", "recovery_hint": "change billing state or choose another search backend"},
            {"gap_index": 1, "status": "provider_quota", "recovery_hint": "change billing state or choose another search backend"},
        ],
    }
    (workspace / "evidence_fetch_manifest_quota.json").write_text(json.dumps(quota_manifest), encoding="utf-8")
    quota_receipt = module.normalize_receipt_row(
        {
            "schema": "ztare-forensic-workbench-evidence-fetch-receipt-v1",
            "project": "demo",
            "returncode": 0,
            "accepted": False,
            "status": "no_new_evidence",
            "manifest_path": "projects/demo/workspace/evidence_fetch_manifest_quota.json",
            "total_attempted": 2,
            "total_accepted": 0,
            "search_backend": "anthropic",
        },
        kind="evidence_fetch",
        path="projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        line=2,
    )
    assert "provider quota=2" in quota_receipt["summary"]
    assert "change billing state or choose another search backend" in quota_receipt["summary"]
    recent = module.project_recent_changes_payload(
        {
            "receipts": [quota_receipt],
            "summary": module.receipt_history_summary([quota_receipt]),
        }
    )
    assert recent["latest_source_or_evidence_change"]["artifact_path"] == (
        "projects/demo/workspace/evidence_fetch_manifest_quota.json"
    )
    assert recent["next_inspection"]["preview_path"] == "projects/demo/workspace/evidence_fetch_manifest_quota.json"
    assert recent["next_inspection"]["preview_kind"] == "artifact"
    assert recent["next_inspection"]["reason"] == "Open the source or evidence file to see what changed."
    assert recent["substantive_inspection"]["preview_path"] == "projects/demo/workspace/evidence_fetch_manifest_quota.json"
    assert recent["substantive_inspection"]["preview_kind"] == "artifact"
    assert commands[0] == [
        module.SERVER_PYTHON,
        "-m",
        "src.ztare.cli",
        "project",
        "evidence-fetch",
        "--project",
        "demo",
        "--severity",
        "degrading",
        "--max-fetches",
        "3",
        "--search-backend",
        "auto",
    ]
    assert commands[1][3:5] == ["forensic-workbench", "record-evidence-fetch"]
    assert commands[1][commands[1].index("--repo") + 1] == str(tmp_path)


def test_evidence_gap_list_and_justify_use_cli_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (project_root / "raw").mkdir()
    (project_root / "demo_intake.json").write_text('{"task": "demo"}\n', encoding="utf-8")
    (project_root / "raw" / "source.md").write_text("source\n", encoding="utf-8")
    receipt_path = workspace / "evidence_gap_resolutions.json"
    commands: list[list[str]] = []

    def fake_run(command: list[str], timeout: int = 0) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "list" in command:
            payload = {
                "schema": "ztare-evidence-gap-list-result-v1",
                "project": "demo",
                "source_path": "projects/demo/workspace/champion_evidence_gaps.json",
                "active_evidence_gap_count": 1,
                "evidence_gaps": [
                    {
                        "target": "Enterprise win/loss data",
                        "severity": "degrading",
                        "description": "Needs explicit source support.",
                    }
                ],
                "warnings": [],
                "next_action": {
                    "next_action": {
                        "action_type": "fetch_evidence",
                        "command": "make evidence-fetch PROJECT=demo",
                    }
                },
            }
        else:
            assert command[:6] == [
                module.SERVER_PYTHON,
                "-m",
                "src.ztare.cli",
                "project",
                "evidence-gap",
                "justify",
            ]
            assert "--source" in command and command[command.index("--source") + 1] == "active"
            assert "--index" in command and command[command.index("--index") + 1] == "0"
            assert "--evidence-ref" in command and command[command.index("--evidence-ref") + 1] == "raw/source.md"
            receipt_path.write_text('{"schema": "ztare-evidence-gap-resolutions-v1"}\n', encoding="utf-8")
            payload = {
                "path": "projects/demo/workspace/evidence_gap_resolutions.json",
                "resolution": {
                    "resolution_id": "egr_abc",
                    "target": "Enterprise win/loss data",
                    "gap_sha256": "abc",
                    "reason": "Covered by the cited project source file.",
                },
                "resolution_count": 1,
            }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload) + "\n", stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "demo", "rows": []})

    list_payload = module.evidence_gap_list_payload_for_project(project="demo")
    write_payload = module.evidence_gap_justify_payload_for_project(
        project="demo",
        selector={"index": 0},
        reason="Covered by the cited project source file.",
        evidence_refs=["raw/source.md"],
    )

    assert list_payload["schema"] == "ztare-forensic-workbench-evidence-gap-list-v1"
    assert list_payload["write_boundary"]["writes_project_files"] is False
    assert write_payload["schema"] == "ztare-forensic-workbench-evidence-gap-justify-v1"
    assert write_payload["accepted"] is True
    assert write_payload["receipt_path"] == "projects/demo/workspace/evidence_gap_resolutions.json"
    assert write_payload["write_boundary"]["write_paths"] == ["projects/demo/workspace/evidence_gap_resolutions.json"]
    assert write_payload["resolution"]["resolution_id"] == "egr_abc"
    assert write_payload["evidence_gaps"]["active_evidence_gap_count"] == 1
    assert len(commands) == 3


def test_evidence_gap_justify_failure_keeps_receipt_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    (project_root / "demo_intake.json").write_text('{"task": "demo"}\n', encoding="utf-8")

    def fake_run(command: list[str], timeout: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="gap selector not found")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.evidence_gap_justify_payload_for_project(
        project="demo",
        selector={"index": 0},
        reason="Covered by the cited project source file.",
    )

    assert payload["accepted"] is False
    assert payload["ok"] is False
    assert payload["receipt_path"] == "projects/demo/workspace/evidence_gap_resolutions.json"
    assert payload["write_boundary"]["writes_project_files"] is False
    assert payload["write_boundary"]["write_paths"] == ["projects/demo/workspace/evidence_gap_resolutions.json"]
    assert "No files changed" in payload["write_boundary"]["no_change_boundary"]


def test_save_case_file_payload_writes_workspace_artifact_and_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "workspace").mkdir(parents=True)
    monkeypatch.setattr(
        module,
        "workflow_payload_for_project",
        lambda **_kwargs: {
            "schema": "ztare-forensic-workbench-workflow-v1",
            "mode": "fast",
            "summary": {"next_step_label": "Review report"},
            "next_step": {"id": "review_report", "label": "Review report"},
            "steps": [{"id": "review_report", "label": "Review report"}],
            "errors": [],
            "project_state": {
                "schema": "ztare-project-workbench-state-v1",
                "project": "demo",
                "charter": {
                    "status": "recorded",
                    "summary": "Project charter is present and can be inspected with the project files.",
                    "file": "projects/demo/project_charter.md",
                    "exists": True,
                },
                "next_action": {"id": "review_report", "label": "Review report"},
                "assumptions": {"non_claims": ["not a full product claim"]},
                "axioms": {
                    "status": "recorded",
                    "summary": "2 verified axioms; 1 retired; 3 derived constraints.",
                    "file": "projects/demo/latest_eval_results.json",
                    "backing_files": [
                        "projects/demo/latest_eval_results.json",
                        "projects/demo/workspace/derived_constraints.json",
                    ],
                    "verified_count": 2,
                    "retired_count": 1,
                    "derived_constraint_count": 3,
                },
                "action_summary": {
                    "total_count": 2,
                    "project_repair_count": 0,
                    "project_inspect_count": 1,
                    "advisory_count": 1,
                    "area_counts": {"report": 1, "advisory": 1},
                    "action_type_counts": {"project_inspect": 1, "advisory": 1},
                },
                "actions": [
                    {
                        "id": "repair_report_support",
                        "label": "Inspect report-support issue",
                        "action_type": "project_inspect",
                        "source": "projects/demo/synthesis/report_support_contract.json",
                        "receipt_paths": [],
                    },
                    {
                        "id": "source_health_1",
                        "label": "Inspect evidence-link warning",
                        "area": "advisory",
                        "action_type": "advisory",
                        "evidence_refs": ["analytics/public/ledgers/demo_source_health.jsonl"],
                    },
                ],
                "files": {
                    "schema": "ztare-project-file-inventory-v1",
                    "item_count": 3,
                    "previewable_count": 2,
                    "missing_count": 1,
                    "role_counts": {"intake": 1, "evidence": 1, "report": 1},
                    "items": [
                        {
                            "label": "Project brief",
                            "role": "intake",
                            "path": "projects/demo/demo_intake.json",
                            "display_kind": "Project brief",
                            "format": "JSON",
                            "previewable": True,
                        },
                        {
                            "label": "Compiled evidence",
                            "role": "evidence",
                            "path": "projects/demo/compiled_evidence_packet.json",
                            "display_kind": "Evidence",
                            "format": "JSON",
                            "previewable": True,
                        },
                        {
                            "label": "Report support",
                            "role": "report",
                            "path": "projects/demo/synthesis/report_support_contract.json",
                            "display_kind": "Report",
                            "format": "JSON",
                            "previewable": False,
                        },
                    ],
                },
                "recent_changes": {
                    "schema": "ztare-project-recent-changes-v1",
                    "status": "recorded",
                    "recorded_count": 2,
                    "receipt_count": 2,
                    "summary": "next step saved: Refresh report support",
                    "latest_receipt_path": "projects/demo/workspace/forensic_workbench_row_actions.jsonl",
                    "latest_review": {
                        "label": "Latest review",
                        "status": "recorded",
                        "summary": "review saved: Report support deferred",
                        "receipt_path": "projects/demo/workspace/forensic_workbench_reviews.jsonl",
                    },
                    "latest_next_step": {
                        "label": "Latest next step",
                        "status": "recorded",
                        "summary": "next step saved: Refresh report support",
                        "receipt_path": "projects/demo/workspace/forensic_workbench_row_actions.jsonl",
                    },
                    "latest_source_or_evidence_change": {
                        "label": "Latest source or evidence change",
                        "status": "recorded",
                        "summary": "Evidence fetch attention; accepted 0 of 2 attempted",
                        "receipt_path": "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
                        "artifact_path": "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json",
                    },
                },
            },
            "project_object_contract": {
                "schema": "ztare-project-object-contract-v1",
                "ok": True,
                "failed_count": 0,
            },
        },
    )
    monkeypatch.setattr(
        module,
        "report_contract_payload_for_project",
        lambda **_kwargs: {
            "schema": "ztare-forensic-workbench-report-contract-v1",
            "status": "attention",
            "display_status": "needs review",
            "report_support_contract": "projects/demo/synthesis/report_support_contract.json",
            "allowed_actions": [
                {
                    "id": "allowed_now:test",
                    "label": "Run the cache isolation test.",
                    "source": "support_contract.next_actions",
                }
            ],
            "conditional_actions": [
                {
                    "id": "conditional_action:test",
                    "condition": "if_negative",
                    "label": "If no cache counterexample appears, keep the export-cause thesis.",
                    "source": "ledger.decision_rule",
                }
            ],
            "deferred_actions": [
                {
                    "id": "deferred_action:test",
                    "label": "Production generalization is out of scope.",
                    "source": "planning_brief.what_to_defer",
                }
            ],
            "forbidden_upgrades": [
                {
                    "id": "forbidden_upgrade:test",
                    "label": "Do not claim cache is an independent root cause.",
                    "source": "support_contract.unsupported_or_unresolved",
                }
            ],
        },
    )
    case_file = {
        "schema": "ztare-forensic-workbench-case-file-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "project_checks": [{"label": "Bounded claim"}],
        "audit_commands": [{"command": "ztare project source-check --project demo --json"}],
        "command_queue": [{"command": "ztare project source-check --project demo --json"}],
        "recent_receipts": [
            {
                "kind": "review",
                "display_summary": "review saved: Report support deferred",
                "display_decision": "deferred",
                "project_check_label": "Report support",
                "applied_at": "2026-06-26T00:00:00Z",
                "path": "projects/demo/workspace/forensic_workbench_reviews.jsonl",
            },
            {
                "kind": "row_action",
                "display_summary": "next step saved: Refresh report support",
                "display_action": "fix report support",
                "project_check_label": "Report support",
                "applied_at": "2026-06-26T00:01:00Z",
                "path": "projects/demo/workspace/forensic_workbench_row_actions.jsonl",
            },
        ],
        "live_context": {
            "project_state": {"schema": "stale-client-state"},
            "pending_intake_edit": {
                "status": "pending_unsaved",
                "changed_fields": ["evidence_refs"],
            },
            "pending_source_import": {
                "status": "pending_unsaved",
                "filename": "S009_generation_rules.md",
                "source_type": "source_evidence",
                "evidence_gap": {
                    "target": "causal_direction",
                    "required_surface": "S009_generation_rules.md",
                },
            },
            "pending_evidence_gap_justification": {
                "status": "pending_unsaved",
                "index": "0",
                "evidence_refs": ["projects/demo/raw/S009_generation_rules.md"],
            },
        },
    }

    payload = module.save_case_file_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        case_file=case_file,
    )

    assert payload["schema"] == "ztare-forensic-workbench-project-file-write-receipt-v1"
    expected_name = f"{module.case_file_stem('demo', 'projects/demo/demo_intake.json')}.json"
    assert payload["path"] == f"projects/demo/workspace/{expected_name}"
    assert payload["receipt_path"] == "projects/demo/workspace/forensic_workbench_project_files.jsonl"
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_project_file_write.json"
    assert payload["item_count"] == 1
    assert payload["receipt_count"] == 2
    assert payload["project_state_schema"] == "ztare-project-workbench-state-v1"
    assert payload["project_state_next_action"] == "Review report"
    assert payload["project_state_action_count"] == 2
    assert payload["project_state_project_repair_count"] == 0
    assert payload["project_state_project_inspect_count"] == 1
    assert payload["project_state_advisory_count"] == 1
    assert payload["project_file_inventory_count"] == 3
    assert payload["project_file_previewable_count"] == 2
    assert payload["project_file_missing_count"] == 1
    assert payload["project_object_contract_ok"] is True
    assert payload["project_object_contract_failed_count"] == 0
    assert payload["project_object_contract_failed_checks"] == []
    assert payload["project_file_previous_sha256"] == ""
    assert payload["project_file_content_changed"] is True
    assert payload["content_changed"] is True
    assert payload["project_file_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["write_boundary"]["primary_path"] == payload["path"]
    assert payload["write_boundary"]["previous_sha256"] == ""
    assert payload["write_boundary"]["new_sha256"] == payload["project_file_sha256"]
    assert payload["write_boundary"]["content_changed"] is True
    assert payload["write_boundary"]["no_change"] is False
    assert "Accepted actions can change only the listed paths" in payload["write_boundary"]["no_change_boundary"]
    saved = json.loads((project_root / "workspace" / expected_name).read_text(encoding="utf-8"))
    latest = json.loads((project_root / "workspace" / "forensic_workbench_latest_project_file_write.json").read_text(encoding="utf-8"))
    ledger_rows = (project_root / "workspace" / "forensic_workbench_project_files.jsonl").read_text(encoding="utf-8").splitlines()
    assert saved["schema"] == "ztare-forensic-workbench-project-file-v1"
    assert saved["project_key"] == "demo::projects/demo/demo_intake.json"
    assert saved["project_file_key"] == "demo::projects/demo/demo_intake.json"
    assert saved["case_key"] == "demo::projects/demo/demo_intake.json"
    assert saved["project_summary"]["schema"] == "ztare-saved-project-summary-v1"
    assert saved["project_summary"]["charter"] == {
        "status": "recorded",
        "summary": "Project charter is present and can be inspected with the project files.",
        "file": "projects/demo/project_charter.md",
        "exists": True,
    }
    assert saved["project_summary"]["next_action"]["label"] == "Review report"
    assert saved["project_summary"]["open_action_count"] == 2
    assert saved["project_summary"]["open_project_repair_count"] == 0
    assert saved["project_summary"]["open_project_inspect_count"] == 1
    assert saved["project_summary"]["open_advisory_count"] == 1
    assert saved["project_summary"]["recent_receipt_count"] == 2
    assert saved["project_summary"]["recent_changes"]["status"] == "recorded"
    assert saved["project_summary"]["recent_changes"]["recorded_count"] == 4
    assert saved["project_summary"]["recent_changes"]["latest_receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_project_files.jsonl"
    )
    assert saved["project_summary"]["recent_changes"]["latest_review"]["summary"] == (
        "review saved: Report support deferred"
    )
    assert saved["project_summary"]["recent_changes"]["latest_next_step"]["summary"] == (
        "next step saved: Refresh report support"
    )
    assert saved["project_summary"]["recent_changes"]["latest_source_or_evidence_change"]["artifact_path"] == (
        "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json"
    )
    assert saved["project_summary"]["recent_changes"]["substantive_inspection"]["preview_path"] == (
        "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json"
    )
    assert saved["project_summary"]["recent_changes"]["substantive_inspection"]["reason"] == (
        "Open the source or evidence file to see what changed."
    )
    assert saved["project_summary"]["recent_changes"]["latest_project_file"] == {
        "label": "Latest project file",
        "status": "recorded",
        "summary": (
            "Project file saved; next action Review report; 2 open actions, 0 repairs, "
            "1 guidance items, 3 files (2 previewable, 1 missing)"
        ),
        "receipt_path": "projects/demo/workspace/forensic_workbench_project_files.jsonl",
        "artifact_path": f"projects/demo/workspace/{expected_name}",
        "latest_path": "projects/demo/workspace/forensic_workbench_latest_project_file_write.json",
        "applied_at": "",
        "kind": "project_file",
        "target": "",
    }
    assert saved["project_summary"]["recent_changes"]["receipt_count"] == 4
    assert saved["project_summary"]["non_claims"] == ["not a full product claim"]
    assert saved["project_summary"]["axioms"]["verified_count"] == 2
    assert saved["project_summary"]["axioms"]["retired_count"] == 1
    assert saved["project_summary"]["axioms"]["derived_constraint_count"] == 3
    assert saved["project_summary"]["axioms"]["backing_files"] == [
        "projects/demo/latest_eval_results.json",
        "projects/demo/workspace/derived_constraints.json",
    ]
    assert saved["project_summary"]["file_inventory"]["schema"] == "ztare-project-file-inventory-v1"
    assert saved["project_summary"]["file_inventory"]["item_count"] == 3
    assert saved["project_summary"]["file_inventory"]["previewable_count"] == 2
    assert saved["project_summary"]["file_inventory"]["missing_count"] == 1
    assert saved["project_summary"]["file_inventory"]["role_counts"] == {"intake": 1, "evidence": 1, "report": 1}
    assert saved["project_summary"]["file_inventory"]["previewable_files"] == [
        {
            "label": "Project brief",
            "role": "intake",
            "path": "projects/demo/demo_intake.json",
            "display_kind": "Project brief",
            "format": "JSON",
        },
        {
            "label": "Compiled evidence",
            "role": "evidence",
            "path": "projects/demo/compiled_evidence_packet.json",
            "display_kind": "Evidence",
            "format": "JSON",
        },
    ]
    assert saved["project_summary"]["report_authority"] == {
        "status": "needs review",
        "allowed_count": 1,
        "conditional_count": 1,
        "deferred_count": 1,
        "forbidden_count": 1,
        "first_allowed_action": "Run the cache isolation test.",
        "first_conditional_rule": "If no cache counterexample appears, keep the export-cause thesis.",
        "first_forbidden_upgrade": "Do not claim cache is an independent root cause.",
        "contract": "projects/demo/synthesis/report_support_contract.json",
    }
    assert saved["project_summary"]["pending_work"] == {
        "status": "pending",
        "items": ["intake", "file draft", "evidence-gap justification"],
        "count": 3,
        "intake_changed_fields": ["evidence_refs"],
        "pending_source_filename": "S009_generation_rules.md",
        "pending_source_type": "source_evidence",
        "pending_source_gap": {
            "target": "causal_direction",
            "required_surface": "S009_generation_rules.md",
        },
        "pending_gap_index": "0",
        "pending_gap_evidence_refs": ["projects/demo/raw/S009_generation_rules.md"],
    }
    assert saved["project_summary"]["latest_review"] == {
        "kind": "review",
        "label": "Report readiness",
        "summary": "review saved: Report readiness deferred",
        "decision": "deferred",
        "action": "",
        "applied_at": "2026-06-26T00:00:00Z",
        "path": "projects/demo/workspace/forensic_workbench_reviews.jsonl",
    }
    assert saved["project_summary"]["latest_next_step"] == {
        "kind": "row_action",
        "label": "Report readiness",
        "summary": "next step saved: Refresh report readiness",
        "decision": "",
        "action": "fix report readiness",
        "applied_at": "2026-06-26T00:01:00Z",
        "path": "projects/demo/workspace/forensic_workbench_row_actions.jsonl",
    }
    assert saved["project_summary"]["project_object_ok"] is True
    assert saved["project_summary"]["project_object_failed_count"] == 0
    assert saved["project_summary"]["project_object_failed_checks"] == []
    assert saved["project_summary"]["proof_path_count"] >= len(saved["project_summary"]["proof_paths"])
    assert "analytics/public/ledgers/demo_source_health.jsonl" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/project_charter.md" in saved["project_summary"]["proof_paths"]
    assert f"projects/demo/workspace/{expected_name}" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/workspace/forensic_workbench_project_files.jsonl" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/workspace/forensic_workbench_latest_project_file_write.json" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/workspace/forensic_workbench_row_actions.jsonl" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/workspace/evidence_fetch_manifest_20260627T101123Z.json" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/demo_intake.json" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/compiled_evidence_packet.json" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/latest_eval_results.json" in saved["project_summary"]["proof_paths"]
    assert "projects/demo/workspace/derived_constraints.json" in saved["project_summary"]["proof_paths"]
    assert saved["live_context"]["project_state"]["schema"] == "ztare-project-workbench-state-v1"
    assert saved["live_context"]["project_state"]["next_action"]["label"] == "Review report"
    assert saved["live_context"]["project_object_contract"]["schema"] == "ztare-project-object-contract-v1"
    assert saved["live_context"]["project_object_contract"]["ok"] is True
    assert saved["live_context"]["report_contract"]["conditional_actions"][0]["label"] == (
        "If no cache counterexample appears, keep the export-cause thesis."
    )
    assert saved["live_context"]["report_contract"]["forbidden_upgrades"][0]["label"] == (
        "Do not claim cache is an independent root cause."
    )
    assert saved["live_context"]["workflow"]["next_step"]["label"] == "Review report"
    assert saved["audit_commands"] == saved["command_queue"]
    assert latest["row_count"] == 1
    assert latest["command_count"] == 1
    assert latest["receipt_count"] == 2
    assert latest["project_state_schema"] == "ztare-project-workbench-state-v1"
    assert latest["project_state_next_action"] == "Review report"
    assert latest["project_state_action_count"] == 2
    assert latest["project_state_project_repair_count"] == 0
    assert latest["project_state_project_inspect_count"] == 1
    assert latest["project_state_advisory_count"] == 1
    assert latest["project_file_inventory_count"] == 3
    assert latest["project_file_previewable_count"] == 2
    assert latest["project_file_missing_count"] == 1
    assert latest["project_object_contract_ok"] is True
    assert latest["project_object_contract_failed_count"] == 0
    assert latest["project_object_contract_failed_checks"] == []
    assert latest["case_file_path"] == payload["path"]
    assert latest["intake"] == "projects/demo/demo_intake.json"
    assert latest["project_key"] == "demo::projects/demo/demo_intake.json"
    assert latest["project_file_key"] == "demo::projects/demo/demo_intake.json"
    assert latest["case_key"] == "demo::projects/demo/demo_intake.json"
    normalized_latest = module.normalize_receipt_row(
        latest,
        kind="project_file",
        path="projects/demo/workspace/forensic_workbench_project_files.jsonl",
        line=1,
    )
    assert normalized_latest["project_file_inventory_count"] == 3
    assert normalized_latest["project_file_previewable_count"] == 2
    assert normalized_latest["project_file_missing_count"] == 1
    assert "3 files (2 previewable, 1 missing)" in normalized_latest["display_summary"]
    assert len(ledger_rows) == 1

    second_payload = module.save_case_file_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        case_file=case_file,
    )
    second_ledger_rows = (project_root / "workspace" / "forensic_workbench_project_files.jsonl").read_text(encoding="utf-8").splitlines()
    assert second_payload["project_file_sha256"] == payload["project_file_sha256"]
    assert second_payload["project_file_previous_sha256"] == payload["project_file_sha256"]
    assert second_payload["project_file_content_changed"] is False
    assert second_payload["content_changed"] is False
    assert second_payload["write_boundary"]["content_changed"] is False
    assert second_payload["write_boundary"]["no_change"] is True
    assert len(second_ledger_rows) == 2


def test_save_case_file_payload_rejects_other_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    (tmp_path / "projects" / "demo" / "workspace").mkdir(parents=True)
    case_file = {
        "schema": "ztare-forensic-workbench-case-file-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/other_intake.json",
        "case_key": "demo::projects/demo/other_intake.json",
    }

    with pytest.raises(ValueError, match="project_file intake must match request intake"):
        module.save_case_file_payload(
            project="demo",
            rubric="demo",
            intake="projects/demo/demo_intake.json",
            case_file=case_file,
        )
    with pytest.raises(ValueError, match="project key"):
        module.save_case_file_payload(
            project="demo",
            rubric="demo",
            intake="projects/demo/demo_intake.json",
            case_file={
                **case_file,
                "intake": "projects/demo/demo_intake.json",
                "project_key": "demo::projects/demo/other_intake.json",
                "case_key": "demo::projects/demo/demo_intake.json",
            },
        )


def test_save_project_file_accepts_legacy_schema_and_rewrites_project_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(
        module,
        "workflow_payload_for_project",
        lambda **_kwargs: {"project_state": {}, "project_object_contract": {}},
    )
    monkeypatch.setattr(
        module,
        "report_contract_payload_for_project",
        lambda **_kwargs: {"schema": "ztare-forensic-workbench-report-contract-v1"},
    )
    project_root = tmp_path / "projects" / "demo"
    (project_root / "workspace").mkdir(parents=True)

    payload = module.save_case_file_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        case_file={
            "schema": "ztare-forensic-workbench-case-file-v1",
            "project": "demo",
            "rubric": "demo",
            "intake": "projects/demo/demo_intake.json",
            "case_key": "demo::projects/demo/demo_intake.json",
        },
    )

    saved = json.loads((tmp_path / payload["path"]).read_text(encoding="utf-8"))
    latest = json.loads((project_root / "workspace" / "forensic_workbench_latest_project_file_write.json").read_text(encoding="utf-8"))

    assert payload["schema"] == "ztare-forensic-workbench-project-file-write-receipt-v1"
    assert saved["schema"] == "ztare-forensic-workbench-project-file-v1"
    assert latest["schema"] == "ztare-forensic-workbench-project-file-write-receipt-v1"
    assert latest["kind"] == "project_file"


def test_receipt_history_preserves_review_and_action_artifact_paths() -> None:
    module = load_server_module()

    review = module.normalize_receipt_row(
        {
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "project": "demo",
            "rubric": "demo",
            "intake": "projects/demo/demo_intake.json",
            "case_key": "demo::projects/demo/demo_intake.json",
            "row": "Report support",
            "row_slug": "report_export",
            "decision": "blocked",
            "note": "hold until the report support file is refreshed",
            "review_file_path": "local-api:demo/report_export",
            "review_file_sha256": "abc",
            "evidence_ref_count": 2,
        },
        kind="review",
        path="projects/demo/workspace/forensic_workbench_reviews.jsonl",
        line=1,
    )
    action = module.normalize_receipt_row(
        {
            "schema": "ztare-forensic-workbench-row-action-receipt-v1",
            "project": "demo",
            "project_check_label": "Source files",
            "project_check_slug": "source_readiness",
            "action": "needs_source",
            "note": "add the missing source file before running preflight",
            "action_file_path": "projects/demo/workspace/source_readiness_action.json",
            "action_file_sha256": "def",
            "evidence_ref_count": 1,
        },
        kind="row_action",
        path="projects/demo/workspace/forensic_workbench_row_actions.jsonl",
        line=2,
    )

    assert review["review_file_path"] == "local-api:demo/report_export"
    assert review["intake"] == "projects/demo/demo_intake.json"
    assert review["project_key"] == "demo::projects/demo/demo_intake.json"
    assert review["case_key"] == "demo::projects/demo/demo_intake.json"
    assert review["project_check_label"] == "Report readiness"
    assert review["project_check_slug"] == "report_export"
    assert review["check_label"] == "Report readiness"
    assert review["summary"] == "hold report on Report readiness: hold until the report support file is refreshed"
    assert action["action_file_path"] == "projects/demo/workspace/source_readiness_action.json"
    assert action["project_check_label"] == "Source files"
    assert action["project_check_slug"] == "source_readiness"
    assert action["item_label"] == "Source files"
    assert action["item_slug"] == "source_readiness"
    assert action["row_slug"] == "source_readiness"
    assert action["summary"] == "needs source on Source files: add the missing source file before running preflight"


def test_receipt_history_normalizes_legacy_report_label() -> None:
    module = load_server_module()

    review = module.normalize_receipt_row(
        {
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "project": "demo",
            "item_label": "Report",
            "row": "Report/export",
            "row_slug": "report_export",
            "decision": "blocked",
        },
        kind="review",
        path="projects/demo/workspace/forensic_workbench_reviews.jsonl",
        line=1,
    )

    assert review["item_label"] == "Report"
    assert review["row"] == "Report/export"
    assert review["display_label"] == "Report readiness"
    assert review["summary"] == "hold report on Report readiness"


def test_receipt_history_filters_case_scoped_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    workspace = tmp_path / "projects" / "demo" / "workspace"
    workspace.mkdir(parents=True)
    rows = [
        {
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "applied_at": "2026-06-23T00:00:03Z",
            "project": "demo",
            "intake": "projects/demo/other_intake.json",
            "case_key": "demo::projects/demo/other_intake.json",
            "row": "Report support",
            "row_slug": "report_export",
            "decision": "blocked",
            "evidence_ref_count": 1,
        },
        {
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "applied_at": "2026-06-23T00:00:02Z",
            "project": "demo",
            "intake": "projects/demo/demo_intake.json",
            "case_key": "demo::projects/demo/demo_intake.json",
            "row": "Report support",
            "row_slug": "report_export",
            "decision": "reviewed",
            "evidence_ref_count": 1,
        },
        {
            "schema": "ztare-forensic-workbench-review-receipt-v1",
            "applied_at": "2026-06-23T00:00:01Z",
            "project": "demo",
            "row": "Legacy row",
            "row_slug": "legacy_row",
            "decision": "deferred",
            "evidence_ref_count": 1,
        },
    ]
    ledger = workspace / "forensic_workbench_reviews.jsonl"
    ledger.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")

    payload = module.receipt_history_payload(project="demo", intake="projects/demo/demo_intake.json", limit=10)

    assert payload["ok"] is True
    assert payload["receipt_count"] == 2
    assert payload["total_receipt_count"] == 3
    assert payload["paths"]["project_file"] == "projects/demo/workspace/forensic_workbench_project_files.jsonl"
    assert payload["paths"]["case_file"] == "projects/demo/workspace/forensic_workbench_project_files.jsonl"
    assert payload["paths"]["case_file_compatibility"] == "projects/demo/workspace/forensic_workbench_case_files.jsonl"
    assert payload["paths"]["next_step"] == "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    assert payload["paths"]["project_check"] == "projects/demo/workspace/forensic_workbench_project_tests.jsonl"
    assert [row["row_slug"] for row in payload["receipts"]] == ["report_export", "legacy_row"]
    assert all(row.get("intake") != "projects/demo/other_intake.json" for row in payload["receipts"])
    assert payload["summary"]["schema"] == "ztare-forensic-workbench-receipt-history-summary-v1"
    assert payload["summary"]["recorded_count"] == 1
    assert payload["summary"]["rows"][0]["label"] == "Latest review"
    assert payload["summary"]["rows"][0]["status"] == "recorded"
    assert payload["summary"]["rows"][0]["summary"] == "reviewed on Report readiness"
    assert payload["summary"]["rows"][1]["label"] == "Latest next step"
    assert payload["summary"]["rows"][1]["status"] == "missing"


def test_receipt_history_includes_evidence_gap_resolutions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    workspace = tmp_path / "projects" / "demo" / "workspace"
    workspace.mkdir(parents=True)
    receipt = {
        "schema": "ztare-evidence-gap-resolutions-v1",
        "project": "demo",
        "resolution_count": 1,
        "resolutions": [
            {
                "resolution_id": "egr_123",
                "project": "demo",
                "target": "Enterprise win/loss data",
                "gap_id": "gap1",
                "gap_sha256": "abc123",
                "gap_source_path": "projects/demo/workspace/champion_evidence_gaps.json",
                "status": "justified",
                "reason": "Covered by the cited local source for this bounded project.",
                "resolved_at": "2026-06-23T00:00:04Z",
                "evidence_refs": [{"path": "raw/source.md", "sha256": "def456"}],
            }
        ],
    }
    (workspace / "evidence_gap_resolutions.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    payload = module.receipt_history_payload(project="demo", intake="projects/demo/demo_intake.json", limit=10)

    assert payload["ok"] is True
    assert payload["paths"]["evidence_gap_resolution"] == "projects/demo/workspace/evidence_gap_resolutions.json"
    assert payload["receipt_count"] == 1
    row = payload["receipts"][0]
    assert row["kind"] == "evidence_gap_resolution"
    assert row["display_kind"] == "evidence gap"
    assert row["display_label"] == "Enterprise win/loss data"
    assert row["status"] == "justified"
    assert row["reason"] == "Covered by the cited local source for this bounded project."
    assert row["receipt_file_path"] == "projects/demo/workspace/evidence_gap_resolutions.json"
    assert row["summary"] == "justified evidence gap: Enterprise win/loss data"


def test_claim_support_payload_uses_bounded_command_and_repo_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw_path = project_root / "raw" / "source.md"
    packet_path = project_root / "compiled_evidence_packet.json"
    index_path = project_root / "workspace" / "source_index.json"
    intake_path = project_root / "demo_intake.json"
    raw_path.parent.mkdir(parents=True)
    index_path.parent.mkdir(parents=True)
    intake_path.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        payload = {
            "ok": False,
            "status": "missing_packet",
            "project": "demo",
            "claim_count": 0,
            "weak_or_unsourced_count": 0,
            "source_context_blocked_count": 0,
            "packet_path": str(packet_path),
            "source_index_path": str(index_path),
            "errors": [f"missing compiled evidence packet: {packet_path}"],
            "source_context": {
                "demo_source": {
                    "source_id": "demo_source",
                    "status": "verified",
                    "source_type": "source_evidence",
                    "path": str(raw_path),
                    "relative_raw_path": "source.md",
                    "line_count": 3,
                    "hash_matches_index": True,
                    "preview": {"line_start": 1, "line_end": 2, "text": "source text", "truncated": False},
                }
            },
        }
        return subprocess.CompletedProcess(command, 1, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)

    payload = module.claim_support_payload_for_project(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
    )

    assert payload["schema"] == "ztare-forensic-workbench-claim-support-v1"
    assert payload["intake"] == "projects/demo/demo_intake.json"
    assert payload["project_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["case_key"] == "demo::projects/demo/demo_intake.json"
    assert payload["support_scope"] == "project_compiled_evidence"
    assert payload["intake_scoped_command"] is False
    assert payload["accepted"] is False
    assert payload["status"] == "missing_packet"
    assert payload["display_status"] == "missing evidence file"
    assert payload["packet_path"] == "projects/demo/compiled_evidence_packet.json"
    assert payload["evidence_support_file_path"] == "projects/demo/compiled_evidence_packet.json"
    assert payload["evidence_file_path"] == "projects/demo/compiled_evidence_packet.json"
    assert payload["source_index_path"] == "projects/demo/workspace/source_index.json"
    assert payload["source_context"][0]["path"] == "projects/demo/raw/source.md"
    assert payload["errors"] == ["missing compiled evidence packet: projects/demo/compiled_evidence_packet.json"]
    assert str(tmp_path) not in payload["stdout_tail"]
    assert str(tmp_path) not in json.dumps(payload)
    assert commands == [[module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "claim-support", "--project", "demo", "--json"]]

    default_payload = module.claim_support_payload_for_project(project="demo", rubric="demo")
    assert default_payload["intake"] == "projects/demo/demo_intake.json"
    assert default_payload["project_key"] == "demo::projects/demo/demo_intake.json"
    assert default_payload["case_key"] == "demo::projects/demo/demo_intake.json"


def test_server_status_advertises_real_live_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module, "WORKBENCH_ENV_PATH", str(tmp_path / ".env.workbench"))
    monkeypatch.setattr(
        module,
        "project_index_payload",
        lambda: {
            "default_project": "demo",
            "projects": [{"project": "demo"}],
            "project_folders": [{"project": "demo"}, {"project": "pending"}],
            "project_inventory_scope": "all_projects_directory",
            "inventory_root": "projects/",
            "inventory_includes_all_project_folders": True,
            "pending_folder_count": 1,
            "project_folder_summary": {"needs_intake_with_files": 1, "needs_intake_empty": 0},
        },
    )
    monkeypatch.setattr(module, "WORKBENCH_DIST", Path("/tmp/ztare_missing_workbench_dist"))
    monkeypatch.setattr(module, "WORKBENCH_PUBLIC", Path("/tmp/ztare_missing_workbench_public"))

    payload = module.server_status_payload()
    endpoints = set(payload["api"]["endpoints"])
    compatibility_endpoints = set(payload["api"]["compatibility_endpoints"])

    assert payload["ok"] is True
    assert payload["api_ready"] is True
    assert payload["app_built"] is False
    assert payload["snapshot_available"] is False
    assert payload["projects_available"] is True
    assert payload["app_name"] == "Project Workbench"
    assert payload["workflow_label"] == "Project path"
    assert payload["project_inventory_scope"] == "local"
    assert payload["inventory_includes_all_project_folders"] is True
    assert payload["project_count"] == 2
    assert payload["intake_ready_count"] == 1
    assert payload["pending_folder_count"] == 1
    assert payload["default_project"] == "demo"
    assert payload["projects"]["project_count"] == 2
    assert payload["projects"]["project_inventory_scope"] == "local"
    assert payload["projects"]["inventory_includes_all_project_folders"] is True
    assert payload["projects"]["pending_folder_count"] == 1
    assert payload["projects"]["folder_summary"]["needs_intake_with_files"] == 1
    assert payload["api"]["project_inventory_scope"] == "local"
    assert payload["api"]["inventory_includes_all_project_folders"] is True
    assert payload["api"]["folder_summary"]["needs_intake_with_files"] == 1
    assert payload["checks"]["api_ready"] is True
    assert payload["checks"]["app_built"] is False
    assert payload["checks"]["snapshot_available"] is False
    assert payload["checks"]["storage_ready"] is True
    assert payload["storage"]["schema"] == "ztare-forensic-workbench-storage-v1"
    assert payload["storage"]["backend"] == "file"
    assert payload["storage"]["detachable"] is True
    assert "papers" not in payload["api"]["file_preview"]["allowed_roots"]
    assert "POST /api/source-edit" in endpoints
    assert "POST /api/source-file" not in endpoints
    assert "GET /api/trace" in endpoints
    assert "GET /api/project-recovery-draft" in endpoints
    assert "GET /api/capabilities" in endpoints
    assert "GET /api/run-history" in endpoints
    assert "GET /api/evidence-support" in endpoints
    assert "GET /api/evidence-gaps" in endpoints
    assert "GET /api/leanmill" in endpoints
    assert "POST /api/leanmill/target" in endpoints
    assert "POST /api/leanmill/blueprint" in endpoints
    assert "POST /api/leanmill/autoformalize-notes" in endpoints
    assert "POST /api/leanmill/solve-adhoc" in endpoints
    assert "POST /api/run" in endpoints
    assert "POST /api/evidence-fetch" in endpoints
    assert "POST /api/evidence-gap-justify" in endpoints
    assert "POST /api/report-contract" in endpoints
    assert "POST /api/next-step" in endpoints
    assert "POST /api/item-action" not in endpoints
    assert "POST /api/row-action" not in endpoints
    assert "GET /api/claim-support" in compatibility_endpoints
    assert "POST /api/item-action" in compatibility_endpoints
    assert "POST /api/row-action" in compatibility_endpoints
    project_file_contract = payload["api"]["action_contracts"]["project_file"]
    review_contract = payload["api"]["action_contracts"]["review"]
    next_step_contract = payload["api"]["action_contracts"]["next_step"]
    evidence_prepare_contract = payload["api"]["action_contracts"]["evidence_prepare"]
    evidence_fetch_contract = payload["api"]["action_contracts"]["evidence_fetch"]
    evidence_gap_contract = payload["api"]["action_contracts"]["evidence_gap_justify"]
    leanmill_contract = payload["api"]["action_contracts"]["leanmill"]
    leanmill_target_contract = payload["api"]["action_contracts"]["leanmill_target"]
    leanmill_blueprint_contract = payload["api"]["action_contracts"]["leanmill_blueprint"]
    leanmill_autoformalize_contract = payload["api"]["action_contracts"]["leanmill_autoformalize_notes"]
    leanmill_solve_contract = payload["api"]["action_contracts"]["leanmill_solve_adhoc"]
    report_support_contract = payload["api"]["action_contracts"]["report_support_refresh"]
    report_synthesis_contract = payload["api"]["action_contracts"]["report_synthesis"]
    capabilities_contract = payload["api"]["action_contracts"]["capabilities"]
    assert payload["api"]["action_summary"]["read_only_count"] == 11
    assert payload["api"]["action_summary"]["write_without_confirmation_count"] == 15
    assert payload["api"]["action_summary"]["confirmation_required_count"] == 8
    assert payload["api"]["action_contracts"]["settings"]["route"] == "GET /api/settings -> POST /api/settings"
    assert payload["api"]["action_contracts"]["settings"]["writes_repo_files"] is True
    assert capabilities_contract["route"] == "GET /api/capabilities"
    assert capabilities_contract["mode"] == "read-only"
    assert capabilities_contract["writes_project_files"] is False
    assert capabilities_contract["requires_confirmation"] is False
    settings_write_template = payload["api"]["action_contracts"]["settings"]["display_write_path_templates"][0]
    assert settings_write_template["label"] == "Settings file"
    assert settings_write_template["path_template"] == str(tmp_path / ".env.workbench")
    assert payload["api"]["action_contracts"]["project_recovery_draft"]["route"] == "GET /api/project-recovery-draft"
    assert "Create or connect project" in payload["api"]["action_summary"]["write_without_confirmation_actions"]
    assert "Prepare evidence" not in payload["api"]["action_summary"]["write_without_confirmation_actions"]
    assert "Prepare evidence" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Fetch evidence" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Refresh report inputs" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Check report readiness" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Save LeanMill target and notes" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Autoformalize from notes" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Solve ad hoc target" in payload["api"]["action_summary"]["confirmation_required_actions"]
    assert "Justify evidence gap" in payload["api"]["action_summary"]["write_without_confirmation_actions"]
    assert payload["api"]["file_change_summary"]["read_only_count"] == 11
    assert payload["api"]["file_change_summary"]["write_count"] == 15
    assert payload["api"]["file_change_summary"]["ask_first_count"] == 8
    assert payload["api"]["file_change_summary"]["browser_writes"] is False
    assert "Create or connect project" in payload["api"]["file_change_summary"]["write_steps"]
    assert "Prepare evidence" not in payload["api"]["file_change_summary"]["write_steps"]
    assert "Prepare evidence" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Fetch evidence" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Refresh report inputs" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Check report readiness" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Save LeanMill target and notes" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Autoformalize from notes" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Solve ad hoc target" in payload["api"]["file_change_summary"]["ask_first_steps"]
    assert "Justify evidence gap" in payload["api"]["file_change_summary"]["write_steps"]
    write_contracts = [
        contract
        for contract in payload["api"]["action_contracts"].values()
        if contract.get("writes_project_files") or contract.get("writes_repo_files")
    ]
    assert write_contracts
    saved_record_write_contracts = [
        contract for contract in write_contracts if contract.get("writes_saved_record") is not False
    ]
    assert saved_record_write_contracts
    assert all(contract.get("receipt_path_template") for contract in saved_record_write_contracts)
    assert all(contract.get("latest_path_template") for contract in saved_record_write_contracts)
    assert all(contract.get("no_change_boundary") for contract in write_contracts)
    assert all((contract.get("write_boundary_template") or {}).get("write_paths") for contract in write_contracts)
    assert all((contract.get("write_boundary") or {}).get("write_paths") for contract in write_contracts)
    assert all(
        (contract.get("write_boundary_template") or {}).get("receipt_path")
        for contract in saved_record_write_contracts
    )
    assert payload["api"]["action_contracts"]["project_create"]["label"] == "Create or connect project"
    assert payload["api"]["action_contracts"]["project_create"]["receipt_path_template"] == (
        "projects/{project}/{project}_intake.json"
    )
    assert evidence_prepare_contract["route"] == "POST /api/source-action"
    assert evidence_prepare_contract["command_template"] == (
        "make evidence-prepare 'PROJECT={project}' 'MODEL=<settings_evidence_model>' MODEL_FALLBACK=0 "
        "EVIDENCE_LLM_TIMEOUT=300 EVIDENCE_LLM_RETRIES=4"
    )
    assert evidence_prepare_contract["writes_project_files"] is True
    assert evidence_prepare_contract["requires_confirmation"] is True
    assert {
        row["label"] for row in evidence_prepare_contract["display_write_path_templates"]
    } >= {"Evidence provenance", "Compiled evidence file", "Evidence replay manifest"}
    assert evidence_fetch_contract["route"] == "POST /api/evidence-fetch"
    assert evidence_fetch_contract["requires_confirmation"] is True
    assert "MODEL=" not in evidence_fetch_contract["command_template"]
    assert report_support_contract["route"] == "POST /api/report-contract"
    assert report_support_contract["requires_confirmation"] is True
    assert report_synthesis_contract["route"] == "POST /api/report-synthesis"
    assert report_synthesis_contract["requires_confirmation"] is True
    assert [
        row["label"] for row in report_support_contract["display_write_path_templates"]
    ] == ["Report readiness file", "Report readiness history", "Latest report readiness record"]
    assert evidence_gap_contract["route"] == "POST /api/evidence-gap-justify"
    assert evidence_gap_contract["write_path_templates"] == ["projects/{project}/workspace/evidence_gap_resolutions.json"]
    assert evidence_gap_contract["receipt_path_template"] == "projects/{project}/workspace/evidence_gap_resolutions.json"
    assert evidence_gap_contract["writes_project_files"] is True
    assert leanmill_contract["route"] == "GET /api/leanmill"
    assert leanmill_contract["writes_project_files"] is False
    assert leanmill_contract["behavior"] == "read-only"
    assert leanmill_target_contract["route"] == "POST /api/leanmill/target"
    assert leanmill_target_contract["writes_project_files"] is False
    assert leanmill_target_contract["writes_repo_files"] is True
    assert leanmill_target_contract["requires_confirmation"] is True
    assert leanmill_target_contract["behavior"] == "asks before writing"
    assert leanmill_target_contract["display_write_path_templates"] == [
        {
            "label": "LeanMill target and notes",
            "path_template": "ztare_proofs/leanmill-formalizations/blueprints/{slug}_blueprint.md",
        },
        {
            "label": "LeanMill target-save history",
            "path_template": "analytics/public/leanmill/workbench/leanmill_blueprint_receipts.jsonl",
        },
        {
            "label": "Latest LeanMill target",
            "path_template": "analytics/public/leanmill/workbench/latest_leanmill_blueprint.json",
        },
    ]
    assert leanmill_blueprint_contract["route"] == "POST /api/leanmill/blueprint"
    assert leanmill_blueprint_contract["compatibility_only"] is True
    assert leanmill_blueprint_contract["requires_confirmation"] is True
    assert leanmill_autoformalize_contract["route"] == "POST /api/leanmill/autoformalize-notes"
    assert leanmill_autoformalize_contract["requires_confirmation"] is True
    assert leanmill_solve_contract["route"] == "POST /api/leanmill/solve-adhoc"
    assert leanmill_solve_contract["requires_confirmation"] is True
    assert project_file_contract["behavior"] == "writes files or saved history"
    assert project_file_contract["receipt_path_template"] == (
        "projects/{project}/workspace/forensic_workbench_project_files.jsonl"
    )
    assert payload["api"]["action_contracts"]["run_preview_and_confirm"]["behavior"] == "asks before writing"
    assert project_file_contract["display_write_path_templates"] == [
        {
            "label": "Project file",
            "path_template": "projects/{project}/workspace/forensic_workbench_project_file_{project_file_digest}.json",
        },
        {
            "label": "Project-file ledger",
            "path_template": "projects/{project}/workspace/forensic_workbench_project_files.jsonl",
        },
        {
            "label": "Latest project file",
            "path_template": "projects/{project}/workspace/forensic_workbench_latest_project_file_write.json",
        },
    ]
    assert "{project_check_slug}" in review_contract["write_path_templates"][0]
    assert "{item_slug}" not in review_contract["write_path_templates"][0]
    assert "{project_check_slug}" in next_step_contract["write_path_templates"][0]
    assert "{item_slug}" not in next_step_contract["write_path_templates"][0]
    assert next_step_contract["display_write_path_templates"][1] == {
        "label": "Next-step ledger",
        "path_template": "projects/{project}/workspace/forensic_workbench_row_actions.jsonl",
    }
    assert next_step_contract["route"] == "POST /api/next-step"


def test_leanmill_state_payload_is_file_backed_and_write_bounded() -> None:
    module = load_server_module()

    payload = module.leanmill_payloads.state_payload(repo=module.snapshot.REPO, storage=module.WORKBENCH_STORE)

    assert payload["schema"] == module.leanmill_payloads.LEANMILL_STATE_SCHEMA
    assert payload["mode"] == "inspect_and_write_targets"
    assert payload["boundary"]["launch_enabled"] is False
    assert payload["boundary"]["background_launch_enabled"] is True
    assert payload["boundary"]["blueprint_write_enabled"] is True
    assert payload["boundary"]["writes_project_files"] is False
    assert payload["blueprint_writes"]["route"] == "POST /api/leanmill/target"
    assert payload["blueprint_writes"]["compatibility_route"] == "POST /api/leanmill/blueprint"
    assert payload["target_writes"]["route"] == "POST /api/leanmill/target"
    assert payload["formalizations"]["lean_file_count"] >= 1
    assert payload["formalizations"]["blueprint_count"] >= 1
    assert payload["claim_boundary"]["source"] == "docs/public_claim_register.md"
    assert payload["solver_lane"]["path"] == "analytics/public/queries/leanmill_solver_lane_results.json"
    assert payload["typed_exits"]["path"] == "analytics/public/queries/leanmill_solver_lane_typed_exits.json"
    actions = {action["id"]: action for action in payload["launch_actions"]}
    assert actions["write_target"]["status"] == "enabled"
    assert actions["autoformalize_from_notes"]["status"] == "enabled"
    assert actions["autoformalize_from_notes"]["route"] == "POST /api/leanmill/autoformalize-notes"
    assert actions["solve_ad_hoc"]["status"] == "enabled"
    assert actions["solve_ad_hoc"]["route"] == "POST /api/leanmill/solve-adhoc"
    assert payload["jobs"]["job_root"] == "analytics/public/leanmill/workbench/jobs"


def test_leanmill_blueprint_preview_then_confirm_writes_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)

    request = {
        "slug": "mathd_algebra_182",
        "title": "Algebra Target Blueprint",
        "target_statement": "Formalize the target statement from the algebra note.",
        "notes": "Use the smallest useful statement before launching a proof job.",
        "non_claims": ["Not a solved proof.", "Not credit-ready until receipts pass."],
        "confirmed": False,
    }

    preview = module.leanmill_payloads.target_request_payload(
        request,
        repo=module.snapshot.REPO,
        storage=module.WORKBENCH_STORE,
    )

    blueprint_path = tmp_path / "ztare_proofs/leanmill-formalizations/blueprints/mathd_algebra_182_blueprint.md"
    ledger_path = tmp_path / "analytics/public/leanmill/workbench/leanmill_blueprint_receipts.jsonl"
    latest_path = tmp_path / "analytics/public/leanmill/workbench/latest_leanmill_blueprint.json"
    assert preview["status"] == "needs_confirmation"
    assert preview["requires_confirmation"] is True
    assert preview["accepted"] is False
    assert preview["write_boundary"]["writes_repo_files"] is True
    assert preview["write_boundary"]["write_paths"] == [
        "ztare_proofs/leanmill-formalizations/blueprints/mathd_algebra_182_blueprint.md",
        "analytics/public/leanmill/workbench/leanmill_blueprint_receipts.jsonl",
        "analytics/public/leanmill/workbench/latest_leanmill_blueprint.json",
    ]
    assert not blueprint_path.exists()
    assert not ledger_path.exists()
    assert not latest_path.exists()

    with pytest.raises(ValueError, match="preview_sha256"):
        module.leanmill_payloads.target_request_payload(
            {**request, "confirmed": True},
            repo=module.snapshot.REPO,
            storage=module.WORKBENCH_STORE,
        )
    assert not blueprint_path.exists()

    saved = module.leanmill_payloads.target_request_payload(
        {**request, "confirmed": True, "preview_sha256": preview["preview_sha256"]},
        repo=module.snapshot.REPO,
        storage=module.WORKBENCH_STORE,
    )

    assert saved["accepted"] is True
    assert saved["status"] == "saved"
    assert saved["content_changed"] is True
    assert blueprint_path.exists()
    assert ledger_path.exists()
    assert latest_path.exists()
    assert "# Algebra Target Blueprint" in blueprint_path.read_text(encoding="utf-8")
    receipt = json.loads(latest_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == module.leanmill_payloads.TARGET_HISTORY_SCHEMA
    assert receipt["blueprint_path"] == saved["blueprint_path"]

    repeated = module.leanmill_payloads.target_request_payload(
        {**request, "confirmed": True, "preview_sha256": preview["preview_sha256"]},
        repo=module.snapshot.REPO,
        storage=module.WORKBENCH_STORE,
    )

    assert repeated["accepted"] is True
    assert repeated["content_changed"] is False
    assert repeated["no_change"] is True


def test_workflow_step_exposes_local_step_alias() -> None:
    module = load_server_module()

    step = module.workflow_step(
        step_id="preflight",
        label="Preflight",
        status="not_run",
        route="POST /api/preflight",
        detail="Run the cheap local check before heavier work.",
    )
    summary = module.workflow_summary_payload([step])

    assert step["local_step"] == "Check readiness"
    assert step["local_action"] == "Check readiness"
    assert summary["next_step_local_step"] == "Check readiness"
    assert summary["next_step_local_action"] == "Check readiness"


def test_project_state_surfaces_accepted_preflight_before_scored_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module, "read_optional_json_object", lambda path: {"bounded_claim": "demo claim"})
    monkeypatch.setattr(module, "compact_project_axioms", lambda project: {"status": "not loaded", "summary": ""})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    payload = module.project_state_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        rows=[],
        steps=[
            module.workflow_step(
                step_id="project_run",
                label="Run project",
                status="not_run",
                route="POST /api/run",
                detail="Start a bounded run.",
            )
        ],
        report={},
        run_history={
            "summary": {"run_rows": 0},
            "latest_preflight": {
                "status": "accepted",
                "run_id": 7,
                "file": "projects/demo/workspace/iteration_telemetry.jsonl",
            },
        },
        source_list={"sources": []},
        receipts={"receipts": []},
        source_count=0,
        scoring_guide_readiness={"status": "usable", "summary": "Scoring guide is ready.", "blocking": []},
    )

    assert payload["run"]["status"] == "readiness accepted"
    assert payload["run"]["summary"] == "Latest readiness check accepted; project run has not started yet."
    assert payload["run"]["latest_preflight"]["file"] == "projects/demo/workspace/iteration_telemetry.jsonl"


def test_project_state_keeps_scored_run_ahead_of_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module, "read_optional_json_object", lambda path: {"bounded_claim": "demo claim"})
    monkeypatch.setattr(module, "compact_project_axioms", lambda project: {"status": "not loaded", "summary": ""})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    payload = module.project_state_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        rows=[],
        steps=[],
        report={},
        run_history={
            "summary": {"run_rows": 3, "latest_score": 74},
            "latest_preflight": {"status": "accepted", "run_id": 9},
            "compression_progress": {
                "status": "needs_narrowing",
                "label": "Simplify or narrow before continuing",
                "summary": "No compression improvement for 3 iterations.",
                "recommendation": "narrow_or_pivot",
                "controller_alignment": {
                    "status": "compression_warns_first",
                    "summary": "The run controller allowed continuation, but compression progress says the route may be stale.",
                },
            },
        },
        source_list={"sources": []},
        receipts={"receipts": []},
        source_count=0,
    )

    assert payload["run"]["status"] == "run recorded"
    assert payload["run"]["summary"] == "latest score 74; 3 runs found."
    assert payload["run"]["compression_progress_status"] == "needs_narrowing"
    assert payload["run"]["compression_progress_recommendation"] == "narrow_or_pivot"
    assert payload["run"]["compression_controller_alignment"]["status"] == "compression_warns_first"


def test_project_state_distinguishes_eval_artifact_from_run_history(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module, "read_optional_json_object", lambda path: {"bounded_claim": "demo claim"})
    monkeypatch.setattr(module, "compact_project_axioms", lambda project: {"status": "not loaded", "summary": ""})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    payload = module.project_state_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        rows=[],
        steps=[],
        report={},
        run_history={
            "summary": {"run_rows": 0, "latest_score": 74},
            "latest_preflight": {},
        },
        source_list={"sources": []},
        receipts={"receipts": []},
        source_count=0,
    )

    assert payload["run"]["status"] == "run file recorded"
    assert payload["run"]["summary"] == "Latest eval file reports latest score 74; no run-history rows found."


def test_project_state_uses_report_allowed_action_as_repair_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    for path in [
        tmp_path / "projects" / "demo" / "synthesis" / "report_support_contract.json",
        tmp_path / "projects" / "demo" / "test_model.py",
        tmp_path / "projects" / "demo" / "raw" / "cache_isolation_check.md",
        tmp_path / "projects" / "demo" / "raw" / "S009_generation_rules.md",
        tmp_path / "projects" / "demo" / "workspace" / "champion_evidence_gaps.json",
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(module, "project_intake_path", lambda *_args, **_kwargs: Path("projects/demo/demo_intake.json"))
    monkeypatch.setattr(module, "read_optional_json_object", lambda path: {"bounded_claim": "demo claim"})
    monkeypatch.setattr(module, "compact_project_axioms", lambda project: {"status": "not loaded", "summary": ""})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})
    monkeypatch.setattr(
        module,
        "read_env_file_values",
        lambda: {
            "ZTARE_WORKBENCH_RUN_MUTATOR_MODEL": "",
            "ZTARE_WORKBENCH_RUN_JUDGE_MODEL": "",
            "ZTARE_WORKBENCH_RUN_INVERTER_MODEL": "",
        },
    )

    payload = module.project_state_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        rows=[],
        steps=[],
        report={
            "status": "blocked",
            "report_support_contract": "projects/demo/synthesis/report_support_contract.json",
            "support_issues": [{"reason": "Report support is blocked."}],
            "allowed_actions": [
                {
                    "id": "allowed_now:test",
                    "label": "Run an exhaustive parameter-space cache test before relying on the report.",
                    "source": "support_contract.next_actions",
                    "command": "ztare project intake validate --path projects/stale/stale_intake.json",
                },
                {
                    "id": "allowed_now:preflight",
                    "label": "Run the model-free launch preflight",
                    "source": "support_contract.next_actions",
                    "command": (
                        "ztare autoresearch run --project stale --rubric stale "
                        "--intake projects/stale/stale_intake.json --iters 1 "
                        "--mutator stale --judge stale --inverter stale --preflight-only"
                    ),
                }
            ],
        },
        run_history={"summary": {}},
        source_list={"sources": []},
        receipts={"receipts": []},
        source_count=0,
        trace={
            "kernel_entry": {
                "can_enter_kernel": True,
                "run_command": (
                    "ztare autoresearch run --project demo --rubric demo "
                    "--intake projects/demo/demo_intake.json --iters 1 "
                    "--mutator stale --judge stale --inverter stale"
                ),
            },
            "plan_preview": {
                "status": "ready_for_bounded_run",
                "recommended_first_command": (
                    "ztare autoresearch run --project demo --rubric demo "
                    "--intake projects/demo/demo_intake.json --iters 1 "
                    "--mutator stale --judge stale --inverter stale --preflight-only"
                ),
            },
            "next_commands": [
                (
                    "ztare autoresearch run --project demo --rubric demo "
                    "--intake projects/demo/demo_intake.json --iters 1 "
                    "--mutator stale --judge stale --inverter stale --preflight-only"
                )
            ],
        },
    )

    follow = next(row for row in payload["actions"] if row["id"] == "follow_report_next_action")
    assert follow["label"] == "Do next report action"
    assert follow["action_type"] == "project_inspect"
    assert follow["detail"] == "Run an exhaustive parameter-space cache test before relying on the report."
    assert follow["workspace"] == "save"
    assert follow["subsection"] == "Report readiness"
    assert follow["primary_label"] == "Open report readiness"
    assert follow["command"] == "ztare project intake validate --path projects/demo/demo_intake.json"
    assert follow["source"] == "projects/demo/synthesis/report_support_contract.json"
    assert follow["evidence_refs"] == [
        "projects/demo/synthesis/report_support_contract.json",
        "projects/demo/test_model.py",
        "projects/demo/raw/cache_isolation_check.md",
        "projects/demo/raw/S009_generation_rules.md",
        "projects/demo/workspace/champion_evidence_gaps.json",
    ]
    assert follow["display_evidence_refs"] == [
        {"label": "Report readiness file", "path": "projects/demo/synthesis/report_support_contract.json"},
        {"label": "Fixture discriminator", "path": "projects/demo/test_model.py"},
        {"label": "Cache isolation source", "path": "projects/demo/raw/cache_isolation_check.md"},
        {"label": "Generation-rule audit", "path": "projects/demo/raw/S009_generation_rules.md"},
        {"label": "Evidence-gap state", "path": "projects/demo/workspace/champion_evidence_gaps.json"},
    ]
    assert follow["write_boundary"]["writes_project_files"] is False
    assert follow["write_boundary"]["write_paths"] == []
    assert "save review after doing it" in follow["write_boundary"]["read_only_actions"]
    assert follow["receipt_paths"] == []
    assert follow["outcome_receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_reviews.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_review.json",
    ]
    run_allowed = next(row for row in payload["actions"] if row["id"] == "run_report_allowed_check")
    assert run_allowed["label"] == "Check readiness"
    assert run_allowed["action_type"] == "project_repair"
    assert run_allowed["detail"] == "Run the local readiness check"
    assert run_allowed["workspace"] == "run"
    assert run_allowed["subsection"] == "Check readiness"
    assert run_allowed["primary_label"] == "Check readiness"
    assert run_allowed["command"] == (
        "ztare autoresearch run --project demo --rubric demo "
        "--intake projects/demo/demo_intake.json --iters 1 --preflight-only "
        "--llm-timeout-seconds 600 --llm-retries 3"
    )
    assert run_allowed["source"] == "projects/demo/synthesis/report_support_contract.json"
    assert run_allowed["evidence_refs"] == ["projects/demo/synthesis/report_support_contract.json"]
    assert run_allowed["display_evidence_refs"] == [
        {"label": "Report readiness file", "path": "projects/demo/synthesis/report_support_contract.json"}
    ]
    assert run_allowed["write_boundary"]["writes_project_files"] is True
    assert run_allowed["write_boundary"]["write_paths"] == ["projects/demo/workspace/iteration_telemetry.jsonl"]
    assert run_allowed["write_boundary"]["receipt_path"] == "projects/demo/workspace/iteration_telemetry.jsonl"
    assert run_allowed["receipt_paths"] == []
    assert run_allowed["outcome_receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_reviews.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_review.json",
    ]
    action = next(row for row in payload["actions"] if row["id"] == "repair_report_support")
    assert action["label"] == "Inspect report readiness issue"
    assert action["action_type"] == "project_inspect"
    assert action["detail"] == "Next report action: Run an exhaustive parameter-space cache test before relying on the report."
    assert action["evidence_refs"] == [
        "projects/demo/synthesis/report_support_contract.json",
        "projects/demo/test_model.py",
        "projects/demo/raw/cache_isolation_check.md",
        "projects/demo/raw/S009_generation_rules.md",
        "projects/demo/workspace/champion_evidence_gaps.json",
    ]
    assert action["display_evidence_refs"] == follow["display_evidence_refs"]
    assert action["source"] == "projects/demo/synthesis/report_support_contract.json"
    assert action["receipt_paths"] == []
    assert action["write_boundary"]["writes_project_files"] is False
    assert action["write_boundary"]["write_paths"] == []
    assert payload["report"]["allowed_action_count"] == 2
    assert payload["report"]["first_allowed_action"] == "Run an exhaustive parameter-space cache test before relying on the report."
    assert payload["admission"]["recommended_first_command"] == (
        "ztare autoresearch run --project demo --rubric demo "
        "--intake projects/demo/demo_intake.json --iters 1 --preflight-only "
        "--llm-timeout-seconds 600 --llm-retries 3"
    )
    assert payload["admission"]["next_commands"] == [
        (
            "ztare autoresearch run --project demo --rubric demo "
            "--intake projects/demo/demo_intake.json --iters 1 --preflight-only "
            "--llm-timeout-seconds 600 --llm-retries 3"
        )
    ]
    rerun = next(row for row in payload["actions"] if row["id"] == "rerun_report_support")
    assert rerun["label"] == "Check report readiness"
    assert rerun["action_type"] == "project_repair"
    assert rerun["workspace"] == "save"
    assert rerun["subsection"] == "Report inputs"
    assert rerun["command"] == (
        "ztare forensic-workbench report-action --project demo "
        "--action check_readiness --renderer decision_brief --confirmed --json"
    )
    assert rerun["receipt_paths"] == [
        "projects/demo/synthesis/report_support_contract.json",
        "projects/demo/workspace/forensic_workbench_report_support_checks.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_report_support_check.json",
    ]
    assert rerun["write_boundary"]["receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_report_support_checks.jsonl"
    )
    assert rerun["write_boundary"]["latest_path"] == (
        "projects/demo/workspace/forensic_workbench_latest_report_support_check.json"
    )


def test_workflow_payload_exposes_top_level_next_step(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "project_intake_path", lambda project, intake, allow_examples=False: module.snapshot.REPO / intake)
    monkeypatch.setattr(
        module,
        "intake_payload_for_project",
        lambda *args, **kwargs: {
            "editable_fields": {"source_refs": [], "evidence_refs": []},
            "reference_status": {"summary": {"missing": 0, "unsafe": 0}},
        },
    )
    def fake_read_optional_json_object(path: Path | str) -> dict[str, str]:
        if str(path).endswith("_intake.json"):
            return {"bounded_claim": "demo claim", "non_claims": ["not a broad claim"]}
        if str(path).endswith("latest_eval_results.json"):
            return {
                "verified_axioms": ["source files are local"],
                "retired_axioms_approved": [],
                "derived_constraints": [{"constraint": "Review cache timing before causal attribution."}],
            }
        return {}

    monkeypatch.setattr(module, "read_optional_json_object", fake_read_optional_json_object)
    monkeypatch.setattr(module, "read_optional_json_value", lambda path: None)
    monkeypatch.setattr(
        module,
        "receipt_history_payload",
        lambda **kwargs: {
            "receipts": [
                {
                    "kind": "row_action",
                    "display_summary": "next step saved: Run source check",
                    "display_action": "needs source",
                    "project_check_label": "Source readiness",
                    "applied_at": "2026-06-26T00:01:00Z",
                    "path": "projects/demo/workspace/forensic_workbench_row_actions.jsonl",
                },
                {
                    "kind": "review",
                    "display_summary": "review saved: Source readiness deferred",
                    "display_decision": "deferred",
                    "project_check_label": "Source readiness",
                    "applied_at": "2026-06-26T00:00:00Z",
                    "path": "projects/demo/workspace/forensic_workbench_reviews.jsonl",
                },
            ]
        },
    )
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})
    monkeypatch.setattr(
        module,
        "claim_support_payload_for_project",
        lambda **_kwargs: {
            "status": "usable",
            "display_status": "usable",
            "claim_count": 2,
            "evidence_support_file_path": "projects/demo/compiled_evidence_packet.json",
            "source_index_path": "projects/demo/workspace/source_index.json",
            "rows": [
                {
                    "claim_id": "c1",
                    "claim": "Demo claim has direct support.",
                    "support_status": "direct_source_support",
                    "source_paths": ["projects/demo/raw/source.md"],
                },
                {
                    "claim_id": "c2",
                    "claim": "Demo claim still has a gap.",
                    "support_status": "weak_support",
                    "issue": "needs a second source",
                },
            ],
            "source_context": [{"source_id": "s1", "path": "projects/demo/raw/source.md"}],
        },
    )
    monkeypatch.setattr(
        module,
        "local_scoring_guide_readiness_payload",
        lambda **_kwargs: {"status": "usable", "summary": "Scoring guide is ready.", "blocking": []},
    )

    payload = module.workflow_payload_for_project(project="demo")

    assert payload["next_step"]["id"] == "prepare_files"
    assert payload["project_state"]["schema"] == "ztare-project-workbench-state-v1"
    assert payload["project_state"]["next_action"]["label"] == "Prepare files"
    assert payload["project_state"]["sources"]["source_count"] == 0
    assert payload["project_state"]["source_health"]["status"] == "ready"
    assert payload["project_state"]["source_health"]["issue_count"] == 0
    assert payload["project_state"]["assumptions"]["status"] == "recorded"
    assert payload["project_state"]["assumptions"]["file"] == "projects/demo/demo_intake.json"
    assert payload["project_state"]["assumptions"]["non_claims"] == ["not a broad claim"]
    assert "not a broad claim" in payload["project_state"]["assumptions"]["summary"]
    assert payload["project_state"]["axioms"]["status"] == "recorded"
    assert payload["project_state"]["axioms"]["verified_count"] == 1
    assert payload["project_state"]["axioms"]["derived_constraint_count"] == 1
    assert payload["project_state"]["axioms"]["backing_files"] == ["projects/demo/latest_eval_results.json"]
    assert payload["project_state"]["thesis_support"]["schema"] == "ztare-project-thesis-support-v1"
    assert payload["project_state"]["thesis_support"]["claim_count"] == 2
    assert payload["project_state"]["thesis_support"]["supported_count"] == 1
    assert payload["project_state"]["thesis_support"]["weak_or_open_count"] == 1
    assert [row["kind"] for row in payload["project_state"]["thesis_support"]["claim_cards"]] == [
        "supported",
        "weak_or_open",
    ]
    assert payload["project_state"]["thesis_support"]["claim_cards"][0]["display_status"] == "Supported"
    assert payload["project_state"]["thesis_support"]["evidence_support_file_path"] == (
        "projects/demo/compiled_evidence_packet.json"
    )
    assert payload["project_state"]["review"]["latest_receipt"] == (
        "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    )
    assert payload["project_state"]["review"]["latest_review"]["summary"] == (
        "review saved: Source readiness deferred"
    )
    assert payload["project_state"]["review"]["latest_next_step"]["summary"] == (
        "next step saved: Run source check"
    )
    assert payload["project_state"]["recent_changes"]["schema"] == "ztare-project-recent-changes-v1"
    assert payload["project_state"]["recent_changes"]["status"] == "recorded"
    assert payload["project_state"]["recent_changes"]["receipt_count"] == 2
    assert payload["project_state"]["recent_changes"]["latest_receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    )
    assert payload["project_state"]["recent_changes"]["latest_review"]["summary"] == (
        "review saved: Source readiness deferred"
    )
    assert payload["project_state"]["recent_changes"]["latest_next_step"]["summary"] == (
        "next step saved: Run source check"
    )
    assert payload["project_state"]["recent_changes"]["latest_source_or_evidence_change"]["status"] == "missing"
    actions_by_id = {row["id"]: row for row in payload["project_state"]["actions"]}
    assert {"repair_project_files", "bind_evidence"}.issubset(actions_by_id)
    assert "Project files must be inspectable" in actions_by_id["repair_project_files"]["rule"]
    assert "Compiled evidence must be bound" in actions_by_id["bind_evidence"]["rule"]
    assert payload["project_object_contract"]["schema"] == "ztare-project-object-contract-v1"
    assert payload["project_object_contract"]["ok"] is True
    assert payload["project_object_contract"]["next_action_label"] == "Prepare files"
    contract_checks = {row["id"]: row for row in payload["project_object_contract"]["checks"]}
    assert contract_checks["workflow_destinations"]["ok"] is True
    assert contract_checks["action_destinations"]["ok"] is True
    assert contract_checks["claim_cards"]["ok"] is True
    assert contract_checks["file_inventory"]["ok"] is True
    assert contract_checks["file_group_routes"]["ok"] is True
    substantive_check = next(
        row for row in payload["project_object_contract"]["checks"] if row["id"] == "substantive_inspection"
    )
    assert substantive_check["ok"] is True
    assert payload["project_state"]["project_object_contract"] == payload["project_object_contract"]
    assert payload["summary"]["next_step_label"] == "Prepare files"
    assert payload["next_step_label"] == "Prepare files"
    assert payload["next_step_detail"] == payload["summary"]["next_step_detail"]
    assert payload["next_step_local_step"] == payload["summary"]["next_step_local_step"]
    steps_by_id = {step["id"]: step for step in payload["steps"]}
    assert steps_by_id["open_project"]["ui_destination"] == {"workspace": "projects", "subsection": "Projects"}
    assert steps_by_id["prepare_files"]["ui_destination"]["subsection"] == "Prepare files"
    assert steps_by_id["review_report"]["ui_destination"]["subsection"] == "Save review"
    assert steps_by_id["preflight"]["write_boundary"]["read_only_actions"] == ["Copy command", "Inspect output"]
    assert steps_by_id["project_run"]["write_boundary"]["read_only_actions"] == ["Inspect readiness", "Copy command"]


def test_workflow_payload_recovers_project_without_intake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})
    project_root = tmp_path / "projects" / "pending"
    workspace = project_root / "workspace"
    raw = project_root / "raw"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (project_root / "thesis.md").write_text("The recovered thesis has a useful signal.\n", encoding="utf-8")
    (raw / "source.md").write_text("local source\n", encoding="utf-8")
    (project_root / "latest_eval_results.json").write_text(
        json.dumps({"score": 97, "weakest_point": "needs narrower evidence boundary"}),
        encoding="utf-8",
    )
    (workspace / "iteration_telemetry.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 1,
                        "iteration_index": 1,
                        "score": 50,
                        "score_improved": True,
                        "pending_loop_action": "CONTINUE",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 1,
                        "iteration_index": 2,
                        "score": 50,
                        "score_improved": False,
                        "pending_loop_action": "CONTINUE",
                        "compression_progress_advice": {
                            "status": "available",
                            "recommendation": "narrow_or_pivot",
                            "rationale": "No compression improvement.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 1,
                        "iteration_index": 3,
                        "score": 50,
                        "score_improved": False,
                        "pending_loop_action": "CONTINUE",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "iteration",
                        "run_id": 1,
                        "iteration_index": 4,
                        "score": 50,
                        "score_improved": False,
                        "pending_loop_action": "CONTINUE",
                        "compression_progress_advice": {
                            "status": "available",
                            "recommendation": "narrow_or_pivot",
                            "rationale": "No compression improvement.",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_001.json").write_text(
        json.dumps({"rmse": 0.4, "n_fit_rows": 30, "k_params": 2}),
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_002.json").write_text(
        json.dumps({"rmse": 0.5, "n_fit_rows": 30, "k_params": 2}),
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_003.json").write_text(
        json.dumps({"rmse": 0.6, "n_fit_rows": 30, "k_params": 2}),
        encoding="utf-8",
    )
    (workspace / "fit_result_iter_004.json").write_text(
        json.dumps({"rmse": 0.7, "n_fit_rows": 30, "k_params": 2}),
        encoding="utf-8",
    )

    payload = module.workflow_payload_for_project(project="pending", rubric="pending")

    assert payload["ok"] is True
    assert payload["recovery_required"] is True
    assert payload["next_step"]["id"] == "connect_project"
    assert payload["next_step"]["ui_destination"] == {"workspace": "projects", "subsection": "Connect project"}
    assert payload["recovery"]["can_add_intake"] is True
    assert payload["recovery"]["add_intake_action"]["write_boundary"]["receipt_path"] == (
        "projects/pending/pending_intake.json"
    )
    assert payload["project_state"]["thesis"]["text"] == "The recovered thesis has a useful signal."
    assert payload["project_state"]["run"]["run_count"] == 1
    assert payload["project_state"]["run"]["latest_score"] == 97
    assert "latest score 97" in payload["project_state"]["run"]["summary"]
    assert payload["project_state"]["run"]["compression_progress_recommendation"] == "narrow_or_pivot"
    assert payload["project_state"]["run"]["compression_controller_alignment"]["status"] == "compression_warns_first"
    assert payload["project_state"]["actions"][0]["id"] == "add_intake"
    assert [action["id"] for action in payload["project_state"]["actions"]] == ["add_intake"]
    assert payload["project_state"]["action_summary"]["total_count"] == 1
    assert payload["project_state"]["files"]["schema"] == "ztare-project-file-inventory-v1"
    assert payload["project_object_contract"]["ok"] is True
    steps_by_id = {step["id"]: step for step in payload["steps"]}
    assert steps_by_id["save_project"]["write_boundary"]["receipt_path"] == (
        "projects/pending/workspace/forensic_workbench_project_files.jsonl"
    )


def test_project_state_sources_are_ready_after_evidence_is_prepared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "demo"
    (project_root / "raw").mkdir(parents=True)
    (project_root / "workspace").mkdir()
    (project_root / "demo_intake.json").write_text('{"bounded_claim": "Demo claim"}\n', encoding="utf-8")
    (project_root / "raw" / "source.md").write_text("source\n", encoding="utf-8")
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})
    monkeypatch.setattr(module, "compact_project_axioms", lambda project: {"status": "not loaded", "summary": ""})

    payload = module.project_state_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        rows=[
            {
                "label": "Source readiness",
                "status": "ready_for_evidence_prepare",
                "detail": "1 source file; 0 untyped",
            }
        ],
        steps=[],
        report={},
        run_history={"summary": {}},
        source_list={
            "accepted": True,
            "sources": [{"path": "projects/demo/raw/source.md", "relative_raw_path": "source.md"}],
            "untyped_source_count": 0,
            "invalid_source_type_count": 0,
        },
        receipts={"receipts": []},
        source_count=1,
        evidence_readiness={
            "status": "usable",
            "source_index": "projects/demo/workspace/source_index.json",
            "source_receipt": "projects/demo/workspace/source_index_receipt.json",
            "compile_provenance": "projects/demo/compiled_evidence_provenance.json",
            "compiled_packet": "projects/demo/compiled_evidence_packet.json",
            "replay_manifest": "projects/demo/compiled_evidence_replay_manifest.json",
            "blocking": [],
        },
        scoring_guide_readiness={"status": "usable", "blocking": []},
        evidence_gap_recovery={"gap_count": 0, "summary": ""},
        thesis_support={"status": "usable"},
    )

    assert payload["sources"]["status"] == "ready"
    assert payload["evidence"]["status"] == "usable"


def test_project_object_contract_rejects_dead_project_action_route() -> None:
    module = load_server_module()
    intake = "projects/demo/demo_intake.json"
    save_boundary = module.write_boundary_payload(
        writes_project_files=True,
        write_paths=[
            "projects/demo/workspace/forensic_workbench_project_file_abc.json",
            "projects/demo/workspace/forensic_workbench_project_files.jsonl",
        ],
        receipt_path="projects/demo/workspace/forensic_workbench_project_files.jsonl",
    )
    project_state = {
        "schema": "ztare-project-workbench-state-v1",
        "project": "demo",
        "intake": intake,
        "project_key": module.case_key("demo", intake),
        "charter": {"status": "recorded", "file": "projects/demo/project_charter.md", "exists": True},
        "thesis": {"status": "recorded"},
        "change_test": {"status": "recorded"},
        "assumptions": {"status": "recorded"},
        "axioms": {"status": "recorded"},
        "thesis_support": {"status": "usable"},
        "sources": {"status": "usable"},
        "source_health": {"status": "ready"},
        "evidence": {"status": "usable", "blocking": []},
        "admission": {"status": "ready_for_bounded_run"},
        "run": {"status": "not run"},
        "report": {"status": "ready", "support_issue_count": 0, "allowed_action_count": 0},
        "review": {"receipt_count": 0},
        "research_map": {
            "schema": "ztare-forensic-workbench-research-map-v1",
            "section_count": 5,
            "project_meaning": {"status": "ready"},
            "next_action": {"status": "ready"},
        },
        "recent_changes": {"status": "missing"},
        "files": {
            "schema": "ztare-project-file-inventory-v1",
            "item_count": 1,
            "previewable_count": 1,
            "missing_count": 0,
            "file_groups": [
                {
                    "id": group["id"],
                    "count": 1 if group["id"] == "all" else 0,
                    "previewable_count": 1 if group["id"] == "all" else 0,
                    "missing_count": 0,
                    "action": {
                        "workspace": group["action_workspace"],
                        "subsection": group["action_subsection"],
                    },
                }
                for group in module.PROJECT_FILE_GROUP_DEFINITIONS
            ],
        },
        "next_action": {
            "id": "prepare_files",
            "label": "Prepare sources",
            "workspace": "sources",
            "subsection": "Prepare sources",
        },
        "actions": [
            {
                "id": "dead_route",
                "label": "Dead route",
                "workspace": "overview",
                "subsection": "Missing panel",
            }
        ],
    }
    contract = module.project_object_contract_payload(
        project="demo",
        intake=intake,
        project_key=module.case_key("demo", intake),
        summary={},
        project_state=project_state,
        steps=[
            {
                "id": "prepare_files",
                "label": "Prepare sources",
                "status": "needs_attention",
                "ui_destination": {"workspace": "sources", "subsection": "Prepare sources"},
            },
            {
                "id": "save_project",
                "label": "Save project file",
                "status": "waiting",
                "ui_destination": {"workspace": "save", "subsection": "Project file"},
                "write_boundary": save_boundary,
            },
        ],
    )

    checks = {row["id"]: row for row in contract["checks"]}
    assert contract["ok"] is False
    assert contract["failed_checks"] == [
        {
            "id": "action_destinations",
            "label": "Project action routes",
            "detail": "Project actions point to missing sections: dead_route.",
        }
    ]
    assert checks["action_destinations"]["ok"] is False
    assert "dead_route" in checks["action_destinations"]["detail"]


def test_project_object_contract_requires_source_health_warning_actions() -> None:
    module = load_server_module()
    state_module = load_state_module()
    intake = "projects/demo/demo_intake.json"
    project_key = module.case_key("demo", intake)
    save_boundary = module.write_boundary_payload(
        writes_project_files=True,
        write_paths=[
            "projects/demo/workspace/forensic_workbench_project_file_abc.json",
            "projects/demo/workspace/forensic_workbench_project_files.jsonl",
        ],
        receipt_path="projects/demo/workspace/forensic_workbench_project_files.jsonl",
    )
    project_state = {
        "schema": "ztare-project-workbench-state-v1",
        "project": "demo",
        "intake": intake,
        "project_key": project_key,
        "charter": {"status": "recorded", "file": "projects/demo/project_charter.md", "exists": True},
        "thesis": {"status": "recorded", "text": "Demo thesis"},
        "change_test": {"status": "recorded"},
        "assumptions": {"status": "recorded"},
        "axioms": {"status": "recorded"},
        "thesis_support": {"status": "usable"},
        "sources": {"status": "usable"},
        "source_health": {
            "status": "needs attention",
            "issue_count": 1,
            "summary": "1 file/evidence warning.",
            "issues": [
                {
                    "issue_type": "weak_gp233_linkage",
                    "evidence_refs": ["analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"],
                }
            ],
        },
        "evidence": {"status": "usable", "blocking": []},
        "admission": {"status": "ready_for_bounded_run"},
        "run": {"status": "ready", "run_count": 1},
        "report": {"status": "ready", "support_issue_count": 0, "allowed_action_count": 0},
        "review": {"receipt_count": 0},
        "research_map": {
            "schema": module.RESEARCH_MAP_SCHEMA,
            "section_count": 1,
            "project_meaning": {"thesis": "Demo thesis"},
            "next_action": {
                "label": "Save project file",
                "workspace": "save",
                "subsection": "Project file",
            },
        },
        "recent_changes": {"status": "recorded", "summary": "review saved"},
        "files": {
            "schema": "ztare-project-file-inventory-v1",
            "item_count": 1,
            "previewable_count": 1,
            "missing_count": 0,
            "file_groups": [
                {
                    "id": group["id"],
                    "count": 1 if group["id"] == "all" else 0,
                    "previewable_count": 1 if group["id"] == "all" else 0,
                    "missing_count": 0,
                    "action": {
                        "workspace": group["action_workspace"],
                        "subsection": group["action_subsection"],
                    },
                }
                for group in module.PROJECT_FILE_GROUP_DEFINITIONS
            ],
        },
        "next_action": {
            "id": "save_project",
            "label": "Save project file",
            "workspace": "save",
            "subsection": "Project file",
        },
        "actions": [
            {
                "id": "repair_project_files",
                "label": "Fix project files",
                "action_type": "project_repair",
                "workspace": "sources",
                "subsection": "Prepare files",
                "write_boundary": module.write_boundary_payload(
                    writes_project_files=True,
                    write_paths=["projects/demo/raw/source.md"],
                    receipt_path="projects/demo/workspace/source_index_receipt.json",
                ),
            }
        ],
    }
    steps = [
        {
            "id": "save_project",
            "label": "Save project file",
            "status": "waiting",
            "ui_destination": {"workspace": "save", "subsection": "Project file"},
            "write_boundary": save_boundary,
        }
    ]

    contract = module.project_object_contract_payload(
        project="demo",
        intake=intake,
        project_key=project_key,
        summary={},
        project_state=project_state,
        steps=steps,
    )
    audit = state_module.project_to_thesis_audit(
        project_state,
        {"ok": True, "summary": "Project object is coherent across workflow and project state."},
    )

    assert contract["ok"] is False
    assert any(row["id"] == "source_health_actions" for row in contract["failed_checks"])
    assert audit["ok"] is False
    assert any(row["id"] == "source_health_actions" for row in audit["failed_checks"])

    recovery_state = json.loads(json.dumps(project_state))
    recovery_state["recovery"] = {
        "intake_target": "projects/demo/demo_intake.json",
        "summary": "needs project brief",
    }
    recovery_state["next_action"] = {
        "id": "connect_project",
        "label": "Create project brief",
        "workspace": "projects",
        "subsection": "Connect project",
    }
    recovery_state["actions"] = [
        {
            "id": "add_intake",
            "label": "Create project brief",
            "action_type": "project_repair",
            "workspace": "projects",
            "subsection": "Connect project",
            "write_boundary": module.write_boundary_payload(
                writes_project_files=True,
                write_paths=["projects/demo/demo_intake.json"],
                receipt_path="projects/demo/demo_intake.json",
            ),
        }
    ]
    recovery_audit = state_module.project_to_thesis_audit(
        recovery_state,
        {"ok": True, "summary": "Project object is coherent across workflow and project state."},
    )

    assert recovery_audit["ok"] is True
    assert next(row for row in recovery_audit["checks"] if row["id"] == "source_health_actions")["detail"] == (
        "File and evidence warnings wait until the project brief is saved."
    )

    project_state["actions"].append(
        {
            "id": "source_health_1",
            "label": "Inspect evidence-link warning",
            "action_type": "advisory",
            "workspace": "run",
            "subsection": "Fix warnings",
            "source": "analytics/public/action_intelligence/state/source_health.json",
            "evidence_refs": ["analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"],
        }
    )

    repaired_contract = module.project_object_contract_payload(
        project="demo",
        intake=intake,
        project_key=project_key,
        summary={},
        project_state=project_state,
        steps=steps,
    )
    repaired_audit = state_module.project_to_thesis_audit(
        project_state,
        {"ok": True, "summary": "Project object is coherent across workflow and project state."},
    )

    assert repaired_contract["ok"] is True
    assert repaired_audit["ok"] is True


def test_workflow_next_step_skips_ready_upstream_steps_after_run_done() -> None:
    module = load_server_module()
    steps = [
        module.workflow_step(step_id="open_project", label="Open project", status="ready", route="", detail=""),
        module.workflow_step(
            step_id="prepare_files",
            label="Prepare sources",
            status="ready",
            route="",
            detail="Sources are ready.",
            source_status="ready",
        ),
        module.workflow_step(step_id="preflight", label="Preflight", status="ready", route="", detail=""),
        module.workflow_step(step_id="project_run", label="Project run", status="done", route="", detail=""),
        module.workflow_step(step_id="review_report", label="Review report", status="ready", route="", detail=""),
        module.workflow_step(step_id="save_project", label="Save project", status="done", route="", detail=""),
    ]

    next_step = module.workflow_next_step(steps)

    assert next_step["id"] == "review_report"
    assert module.workflow_summary_payload(steps)["next_step_label"] == "Review report"


def test_workflow_blocked_report_review_advertises_review_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "demo"
    report_path = project_root / "synthesis" / "report_support_contract.json"
    report_path.parent.mkdir(parents=True)
    raw_path = project_root / "raw" / "source.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("source", encoding="utf-8")
    (project_root / "raw" / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}),
        encoding="utf-8",
    )
    (project_root / "demo_intake.json").write_text(
        json.dumps(
            {
                "bounded_claim": "Demo report claim.",
                "next_falsifier": "Change the claim if report evidence fails.",
                "source_refs": ["projects/demo/raw/source.md"],
                "evidence_refs": ["projects/demo/evidence.txt"],
            }
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "status": "blocked",
                "support_issues": [{"reason": "Report support is blocked."}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "project_intake_path", lambda project, intake, allow_examples=False: tmp_path / intake)
    monkeypatch.setattr(
        module,
        "intake_payload_for_project",
        lambda *args, **kwargs: {
            "editable_fields": {"source_refs": ["projects/demo/raw/source.md"], "evidence_refs": ["projects/demo/evidence.txt"]},
            "reference_status": {"summary": {"missing": 0, "unsafe": 0}},
        },
    )
    monkeypatch.setattr(
        module,
        "source_list_payload",
        lambda **_kwargs: {
            "accepted": True,
            "summary": {"source_count": 1, "untyped_count": 0, "invalid_count": 0},
            "sources": [{"path": "projects/demo/raw/source.md", "source_type": "source_evidence"}],
        },
    )
    monkeypatch.setattr(
        module,
        "local_evidence_readiness_payload",
        lambda _project_root: {
            "status": "usable",
            "summary": "Evidence is usable.",
            "blocking": [],
            "source_index": "projects/demo/workspace/source_index.json",
            "source_receipt": "projects/demo/workspace/source_index_receipt.json",
            "compile_provenance": "projects/demo/compiled_evidence_provenance.json",
            "compiled_packet": "projects/demo/compiled_evidence_packet.json",
            "replay_manifest": "projects/demo/compiled_evidence_replay_manifest.json",
        },
    )
    monkeypatch.setattr(
        module,
        "local_scoring_guide_readiness_payload",
        lambda **_kwargs: {"status": "usable", "summary": "Scoring guide is ready.", "blocking": []},
    )
    monkeypatch.setattr(module, "receipt_history_payload", lambda **_kwargs: {"receipts": []})
    monkeypatch.setattr(module, "run_history_payload_for_project", lambda **_kwargs: {"summary": {}})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    payload = module.workflow_payload_for_project(project="demo")

    review_step = {step["id"]: step for step in payload["steps"]}["review_report"]
    write_boundary = review_step["write_boundary"]
    assert review_step["status"] == "needs_attention"
    assert write_boundary["writes_project_files"] is True
    assert write_boundary["receipt_path"] == "projects/demo/workspace/forensic_workbench_reviews.jsonl"
    assert write_boundary["latest_path"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert any(action["id"] == "save_report_review" for action in payload["project_state"]["actions"])
    assert len(write_boundary["write_paths"]) == 3
    actions_by_id = {row["id"]: row for row in payload["project_state"]["actions"]}
    assert "report readiness issue" in actions_by_id["repair_report_support"]["rule"]
    assert "review is saved" in actions_by_id["save_report_review"]["rule"]


def test_workflow_promotes_active_evidence_gap_before_report_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "demo"
    report_path = project_root / "synthesis" / "report_support_contract.json"
    report_path.parent.mkdir(parents=True)
    raw_path = project_root / "raw" / "source.md"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("source", encoding="utf-8")
    report_path.write_text(
        json.dumps(
            {
                "status": "blocked",
                "support_issues": [{"reason": "Report support is blocked."}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "project_intake_path", lambda project, intake, allow_examples=False: tmp_path / intake)
    monkeypatch.setattr(
        module,
        "intake_payload_for_project",
        lambda *args, **kwargs: {
            "editable_fields": {"source_refs": ["projects/demo/raw/source.md"], "evidence_refs": ["projects/demo/evidence.txt"]},
            "reference_status": {"summary": {"missing": 0, "unsafe": 0}},
        },
    )
    monkeypatch.setattr(
        module,
        "local_evidence_readiness_payload",
        lambda _project_root: {"status": "usable", "summary": "Evidence is usable.", "blocking": []},
    )
    monkeypatch.setattr(
        module,
        "local_evidence_gap_recovery_payload",
        lambda **_kwargs: {
            "status": "needs evidence recovery",
            "summary": "1 active evidence gap needs fetch or justification (1 degrading).",
            "gap_count": 1,
            "file": "projects/demo/workspace/latest_evidence_gaps.json",
            "command": "make evidence-fetch PROJECT=demo SEVERITY=degrading MAX_FETCHES=3 MODEL_FALLBACK=0",
            "receipt_paths": ["projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl"],
            "write_paths": ["projects/demo/raw/evidence_fetch_<timestamp>.md"],
            "gaps": [{"target": "Missing source", "severity": "degrading", "fetch_query": "missing source"}],
        },
    )
    monkeypatch.setattr(
        module,
        "local_scoring_guide_readiness_payload",
        lambda **_kwargs: {"status": "usable", "summary": "Scoring guide is ready.", "blocking": []},
    )
    monkeypatch.setattr(module, "receipt_history_payload", lambda **_kwargs: {"receipts": []})
    monkeypatch.setattr(module, "run_history_payload_for_project", lambda **_kwargs: {"summary": {}})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    payload = module.workflow_payload_for_project(project="demo")

    steps_by_id = {step["id"]: step for step in payload["steps"]}
    assert payload["next_step"]["id"] == "prepare_files"
    assert payload["next_step"]["label"] == "Fetch or justify evidence gaps"
    assert payload["project_state"]["next_action"]["label"] == "Fetch or justify evidence gaps"
    assert payload["summary"]["next_step_local_step"] == "Fetch or justify evidence gaps"
    assert steps_by_id["prepare_files"]["ui_destination"] == {
        "workspace": "sources",
        "subsection": "Prepare files",
    }
    action_ids = {row["id"] for row in payload["project_state"]["actions"]}
    assert "prepare_evidence" not in action_ids
    assert "recover_evidence_gaps" in action_ids
    actions_by_id = {row["id"]: row for row in payload["project_state"]["actions"]}
    assert actions_by_id["recover_evidence_gaps"]["workspace"] == "sources"
    assert actions_by_id["recover_evidence_gaps"]["subsection"] == "Prepare files"
    assert steps_by_id["review_report"]["status"] == "needs_attention"
    assert payload["project_object_contract"]["ok"] is True


def test_workflow_payload_holds_recovered_project_on_evidence_prep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    command_context = module.workbench_command_context
    monkeypatch.setattr(
        module,
        "workbench_command_context",
        lambda project, rubric=None: {
            **command_context(project, rubric),
            "evidence_search_backend": "auto",
        },
    )
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "intake_payload_for_project", lambda *_args, **_kwargs: {
        "editable_fields": {
            "source_refs": ["projects/demo/raw/thesis.md"],
            "evidence_refs": ["projects/demo/raw/evidence.txt"],
        },
        "reference_status": {"summary": {"missing": 0, "unsafe": 0}},
    })
    monkeypatch.setattr(
        module,
        "source_list_payload",
        lambda **_kwargs: {
            "accepted": True,
            "summary": {"source_count": 2, "untyped_count": 0, "invalid_count": 0},
            "sources": [
                {"path": "projects/demo/raw/thesis.md", "source_type": "source_evidence"},
                {"path": "projects/demo/raw/evidence.txt", "source_type": "source_evidence"},
            ],
        },
    )
    monkeypatch.setattr(module, "receipt_history_payload", lambda **_kwargs: {"receipts": []})
    monkeypatch.setattr(module, "action_intelligence_health_read_model", lambda: {"issues": [], "source_path": ""})

    project_root = tmp_path / "projects" / "demo"
    rubrics_root = tmp_path / "rubrics"
    raw_dir = project_root / "raw"
    workspace = project_root / "workspace"
    raw_dir.mkdir(parents=True)
    rubrics_root.mkdir()
    workspace.mkdir()
    (project_root / "demo_intake.json").write_text(
        json.dumps(
            {
                "bounded_claim": "Recovered project thesis.",
                "next_falsifier": "Change the thesis if recovered evidence points elsewhere.",
                "source_refs": ["projects/demo/raw/thesis.md"],
                "evidence_refs": ["projects/demo/raw/evidence.txt"],
            }
        ),
        encoding="utf-8",
    )
    (raw_dir / "thesis.md").write_text("thesis", encoding="utf-8")
    (raw_dir / "evidence.txt").write_text("evidence", encoding="utf-8")
    (raw_dir / "source_type_map.json").write_text(
        json.dumps({"thesis.md": "source_evidence", "evidence.txt": "source_evidence"}),
        encoding="utf-8",
    )
    (rubrics_root / "demo.json").write_text('{"criteria": {"A": "legacy scoring text"}}\n', encoding="utf-8")
    (workspace / "source_index.json").write_text('{"sources": []}\n', encoding="utf-8")
    (workspace / "source_index_receipt.json").write_text('{"ok": true}\n', encoding="utf-8")
    (workspace / "iteration_telemetry.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "run_start",
                        "run_id": 9,
                        "timestamp_utc": "2026-06-26T00:00:00Z",
                        "preflight_only": True,
                        "project_packet": {
                            "packet_status": "valid_packet",
                            "kernel_entry_status": "ready",
                        },
                    }
                ),
                json.dumps(
                    {
                        "record_type": "run_end",
                        "run_id": 9,
                        "timestamp_utc": "2026-06-26T00:00:01Z",
                        "preflight_only": True,
                        "run_exit_reason": "preflight_only",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workspace / "latest_evidence_gaps.json").write_text(
        json.dumps(
            {
                "evidence_gaps": [
                    {
                        "target": "Missing enterprise source",
                        "severity": "degrading",
                        "fetch_query": "enterprise source query",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = module.workflow_payload_for_project(project="demo")

    assert payload["next_step"]["id"] == "prepare_files"
    assert payload["next_step"]["label"] == "Prepare evidence summary"
    assert payload["project_state"]["next_action"]["label"] == "Prepare evidence summary"
    assert payload["project_state"]["sources"]["source_count"] == 2
    assert payload["project_state"]["evidence"]["status"] == "needs support"
    assert payload["project_state"]["run"]["status"] == "needs support"
    assert payload["project_state"]["run"]["latest_preflight"]["run_id"] == 9
    assert payload["project_state"]["evidence"]["blocking"] == [
        "evidence compile provenance",
        "compiled evidence file",
        "evidence replay manifest",
    ]
    actions_by_id = {row["id"]: row for row in payload["project_state"]["actions"]}
    expected_prepare_command = (
        "make evidence-prepare PROJECT=demo MODEL_FALLBACK=0 "
        "EVIDENCE_LLM_TIMEOUT=300 EVIDENCE_LLM_RETRIES=4"
    )
    assert actions_by_id["prepare_evidence"]["command"] == expected_prepare_command
    assert "Source files listed in the project brief are not enough by themselves" in (
        actions_by_id["prepare_evidence"]["rule"]
    )
    assert actions_by_id["prepare_evidence"]["receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_source_actions.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_source_action.json",
        "projects/demo/compiled_evidence_provenance.json",
        "projects/demo/compiled_evidence_packet.json",
        "projects/demo/compiled_evidence_replay_manifest.json",
    ]
    assert actions_by_id["prepare_evidence"]["write_boundary"]["receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_source_actions.jsonl"
    )
    assert actions_by_id["prepare_evidence"]["write_boundary"]["latest_path"] == (
        "projects/demo/workspace/forensic_workbench_latest_source_action.json"
    )
    assert "projects/demo/workspace/source_index.json" in actions_by_id["prepare_evidence"]["write_boundary"]["write_paths"]
    assert "Accepted actions can change only the listed paths" in (
        actions_by_id["prepare_evidence"]["write_boundary"]["no_change_boundary"]
    )
    assert actions_by_id["recover_evidence_gaps"]["detail"] == (
        "1 active evidence gap needs fetch or justification (1 degrading)."
    )
    assert "Active evidence gaps must be fetched or hash-justified" in actions_by_id["recover_evidence_gaps"]["rule"]
    assert actions_by_id["recover_evidence_gaps"]["source"] == "projects/demo/workspace/latest_evidence_gaps.json"
    assert actions_by_id["recover_evidence_gaps"]["command"] == (
        f"{module.SERVER_PYTHON} -m src.ztare.cli project evidence-fetch --project demo "
        "--severity degrading --max-fetches 3 --search-backend auto"
    )
    assert actions_by_id["recover_evidence_gaps"]["receipt_paths"] == [
        "projects/demo/workspace/evidence_fetch_manifest_<timestamp>.json",
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_evidence_fetch.json",
        "projects/demo/workspace/evidence_gap_resolutions.json",
        "projects/demo/workspace/evidence_gap_action.json",
        "projects/demo/workspace/evidence_gap_brief.md",
    ]
    assert actions_by_id["recover_evidence_gaps"]["write_boundary"]["receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl"
    )
    assert actions_by_id["recover_evidence_gaps"]["write_boundary"]["latest_path"] == (
        "projects/demo/workspace/forensic_workbench_latest_evidence_fetch.json"
    )
    assert "projects/demo/evidence.txt" in actions_by_id["recover_evidence_gaps"]["write_boundary"]["write_paths"]
    assert "projects/demo/raw/evidence_fetch_<timestamp>.md" in (
        actions_by_id["recover_evidence_gaps"]["write_boundary"]["write_paths"]
    )
    assert "projects/demo/workspace/evidence_gap_resolutions.json" in (
        actions_by_id["recover_evidence_gaps"]["write_boundary"]["write_paths"]
    )
    assert actions_by_id["fix_scoring_guide"]["detail"] == (
        "Scoring guide needs a non-empty dimensions list before a run."
    )
    assert "current scoring guide" in actions_by_id["fix_scoring_guide"]["rule"]
    assert payload["project_state"]["evidence"]["gap_count"] == 1
    assert payload["project_state"]["evidence"]["gap_file"] == "projects/demo/workspace/latest_evidence_gaps.json"
    assert payload["project_state"]["admission"]["status"] == "blocked_on_project_surfaces"
    assert payload["project_state"]["admission"]["can_enter_kernel"] is False
    assert payload["project_state"]["admission"]["model_calls_before_confirmation"] is False
    assert payload["project_state"]["admission"]["model_spend_starts_at"] == "bounded_loop_run"
    assert payload["project_state"]["admission"]["recommended_first_command"] == expected_prepare_command
    assert payload["project_state"]["admission"]["blockers"]
    assert actions_by_id["fix_scoring_guide"]["source"] == "rubrics/demo.json"
    assert actions_by_id["fix_scoring_guide"]["command"] == "GET /api/scoring-guide -> POST /api/scoring-guide"
    assert actions_by_id["fix_scoring_guide"]["receipt_paths"] == [
        "projects/demo/workspace/forensic_workbench_scoring_guides.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_scoring_guide.json",
        "rubrics/demo.json",
    ]
    assert actions_by_id["fix_scoring_guide"]["write_boundary"]["write_paths"] == [
        "rubrics/demo.json",
        "projects/demo/workspace/forensic_workbench_scoring_guides.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_scoring_guide.json",
    ]
    assert actions_by_id["fix_scoring_guide"]["write_boundary"]["receipt_path"] == (
        "projects/demo/workspace/forensic_workbench_scoring_guides.jsonl"
    )
    assert "JSON parse failure" in actions_by_id["fix_scoring_guide"]["write_boundary"]["no_change_boundary"]
    assert payload["project_state"]["run"]["blocking"] == ["scoring guide dimensions"]
    evidence_action_check = next(
        row for row in payload["project_object_contract"]["checks"] if row["id"] == "evidence_repair_action"
    )
    assert evidence_action_check["ok"] is True
    action_boundary_check = next(
        row for row in payload["project_object_contract"]["checks"] if row["id"] == "action_write_boundaries"
    )
    assert action_boundary_check["ok"] is True
    workflow_boundary_check = next(
        row for row in payload["project_object_contract"]["checks"] if row["id"] == "workflow_write_boundaries"
    )
    assert workflow_boundary_check["ok"] is True
    assert payload["project_object_contract"]["ok"] is True


def test_workbench_evidence_gap_recovery_respects_hash_bound_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ztare.workspace.evidence_gap_resolutions import write_gap_resolution

    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "latest_evidence_gaps.json").write_text(
        json.dumps(
            {
                "evidence_gaps": [
                    {
                        "id": "public-gap",
                        "target": "Missing enterprise source",
                        "severity": "degrading",
                        "fetch_query": "enterprise source query",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    before = module.local_evidence_gap_recovery_payload(project="demo", project_root=project_root)
    write_gap_resolution(
        project_dir=project_root,
        gap_id="public-gap",
        reason="Comparator is out of scope for this bounded project.",
        repo=tmp_path,
    )
    after = module.local_evidence_gap_recovery_payload(project="demo", project_root=project_root)

    assert before["gap_count"] == 1
    assert before["file"] == "projects/demo/workspace/latest_evidence_gaps.json"
    assert after["gap_count"] == 0
    assert after["status"] == "none"
    assert "contains no active evidence gaps" in after["summary"]
    assert after["receipt_paths"] == ["projects/demo/workspace/evidence_gap_resolutions.json"]


def test_evidence_gap_endpoint_exposes_active_gap_aliases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    project_root = tmp_path / "projects" / "demo"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (project_root / "demo_intake.json").write_text("{}", encoding="utf-8")
    gap_payload = {
        "active_evidence_gap_count": 1,
        "evidence_gaps": [
            {
                "target": "causal_direction",
                "severity": "degrading",
                "fetch_query": "find fixture generation rules",
            }
        ],
        "source_path": "projects/demo/workspace/latest_evidence_gaps.json",
    }
    (workspace / "latest_evidence_gaps.json").write_text(json.dumps(gap_payload), encoding="utf-8")
    monkeypatch.setattr(
        module.snapshot,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(gap_payload),
            stderr="",
        ),
    )

    payload = module.evidence_gap_list_payload_for_project(project="demo")

    assert payload["status"] == "needs evidence recovery"
    assert payload["gap_count"] == 1
    assert payload["active_gap_count"] == 1
    assert payload["active_evidence_gap_count"] == 1
    assert payload["active_gaps"][0]["target"] == "causal_direction"
    assert payload["source_path"] == "projects/demo/workspace/latest_evidence_gaps.json"
    assert payload["receipt_paths"] == [
        "projects/demo/workspace/evidence_fetch_manifest_<timestamp>.json",
        "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl",
        "projects/demo/workspace/forensic_workbench_latest_evidence_fetch.json",
        "projects/demo/workspace/evidence_gap_resolutions.json",
        "projects/demo/workspace/evidence_gap_action.json",
        "projects/demo/workspace/evidence_gap_brief.md",
    ]
    assert "projects/demo/evidence.txt" in payload["write_paths"]
    assert "projects/demo/workspace/evidence_gap_resolutions.json" in payload["justify_write_paths"]
    assert "projects/demo/workspace/forensic_workbench_evidence_fetches.jsonl" in payload["fetch_receipt_paths"]


def test_project_state_cli_uses_workflow_project_state(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_state_module()
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(
        module.server,
        "workflow_payload_for_project",
        lambda **kwargs: {
            "schema": "ztare-forensic-workbench-workflow-v1",
            "project_state": {
                    "schema": "ztare-project-workbench-state-v1",
                    "project": kwargs["project"],
                    "charter": {
                        "exists": True,
                        "file": "projects/demo/project_charter.md",
                        "status": "usable",
                        "summary": "Project charter is present and can be inspected.",
                    },
                    "thesis": {"text": "Demo thesis", "status": "recorded"},
                "sources": {"status": "usable"},
                "evidence": {"status": "usable"},
                "source_health": {"status": "ready", "issue_count": 0, "summary": "No file warnings."},
                "run": {"status": "ready", "run_count": 0},
                "report": {
                    "status": "attention",
                    "summary": "Report needs review.",
                    "contract": "projects/demo/synthesis/report_support_contract.json",
                },
                "research_map": {
                    "schema": module.server.RESEARCH_MAP_SCHEMA,
                    "status": "ready",
                    "summary": "Project map connects the thesis, support, limits, and next action.",
                    "section_count": 4,
                    "project_meaning": {
                        "claim": "Demo thesis",
                        "support": "usable",
                        "limits": "Report needs review.",
                        "next": "Review report",
                    },
                    "next_action": {
                        "label": "Review report",
                        "workspace": "review",
                        "subsection": "Save review",
                    },
                },
                "files": {
                    "schema": "ztare-project-file-inventory-v1",
                    "item_count": 4,
                    "previewable_count": 3,
                    "missing_count": 1,
                    "file_groups": [
                        {
                            "id": "overview",
                            "label": "Charter, thesis & brief",
                            "count": 2,
                            "previewable_count": 2,
                            "missing_count": 0,
                            "action": {"workspace": "overview", "subsection": "Thesis"},
                        }
                    ],
                },
                "next_action": {
                    "id": "review_report",
                    "label": "Review report",
                    "workspace": "review",
                    "subsection": "Save review",
                },
                "recent_changes": {"status": "recorded", "summary": "review saved: Report support deferred"},
                "actions": [
                    {
                        "id": "repair_project_files",
                        "label": "Fix project files",
                        "action_type": "project_repair",
                    }
                ],
            },
            "project_object_contract": {
                "schema": "ztare-project-object-contract-v1",
                "ok": True,
                "summary": "Project object is coherent across workflow and project state.",
            },
        },
    )

    payload = module.project_state_for_args(
        Namespace(project="demo", rubric=None, intake=None, renderer=None, mode="fast", json=True)
    )

    assert payload["schema"] == "ztare-forensic-workbench-project-state-cli-v1"
    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["failed_check_count"] == 0
    assert payload["project"] == "demo"
    assert payload["intake"] == "projects/demo/demo_intake.json"
    assert payload["workflow_schema"] == "ztare-forensic-workbench-workflow-v1"
    assert payload["next_action"]["label"] == "Review report"
    assert payload["report"]["status"] == "attention"
    assert payload["recent_changes"]["summary"] == "review saved: Report support deferred"
    assert payload["files"]["item_count"] == 4
    assert payload["files"]["previewable_count"] == 3
    assert payload["files"]["missing_count"] == 1
    assert payload["files"]["file_groups"][0]["label"] == "Charter, thesis & brief"
    assert payload["summary"] == {
        "thesis": "Demo thesis",
        "sources": "usable",
        "evidence": "usable",
        "run": "ready",
        "report": "attention",
        "formalization": "",
        "research_map": "Project map connects the thesis, support, limits, and next action.",
        "files": "4 files; 3 previewable; 1 missing",
        "next_action": "Review report",
        "latest_change": "review saved: Report support deferred",
    }
    assert payload["project_state"]["schema"] == "ztare-project-workbench-state-v1"
    assert payload["project_state"]["actions"][0]["label"] == "Fix project files"
    assert payload["project_object_contract"]["schema"] == "ztare-project-object-contract-v1"
    assert payload["project_object_contract"]["ok"] is True


def test_project_state_cli_defaults_to_full_workflow() -> None:
    module = load_state_module()

    args = module.build_parser().parse_args(["--project", "demo", "--json"])

    assert args.mode == "full"


def test_project_state_cli_surfaces_contract_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_state_module()
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(
        module.server,
        "workflow_payload_for_project",
        lambda **kwargs: {
            "schema": "ztare-forensic-workbench-workflow-v1",
            "project_state": {
                "schema": "ztare-project-workbench-state-v1",
                "project": kwargs["project"],
            },
            "project_object_contract": {
                "schema": "ztare-project-object-contract-v1",
                "ok": False,
                "failed_count": 1,
                "failed_checks": [
                    {
                        "id": "action_destinations",
                        "label": "Project action routes",
                        "detail": "Project actions point to missing sections: dead_route.",
                    }
                ],
                "summary": "Project object has a missing next action.",
            },
        },
    )

    payload = module.project_state_for_args(
        Namespace(project="demo", rubric=None, intake=None, renderer=None, mode="fast", json=True, strict=False)
    )

    assert payload["ok"] is False
    assert payload["status"] == "attention"
    assert payload["failed_check_count"] == 1
    assert payload["first_failed_check"]["label"] == "Project action routes"
    assert payload["failed_checks"][0]["id"] == "action_destinations"
    assert payload["project_object_contract"]["summary"] == "Project object has a missing next action."


def test_report_workflow_detail_uses_product_language() -> None:
    module = load_server_module()
    report = {
        "support_issues": [
            {
                "reason": "Missing architectural documentation detailing how the CHG-142 change affects the export worker.",
                "display_reason": "Missing architectural documentation detailing how the CHG-142 change affects the export worker.",
            }
        ]
    }

    detail = module.report_workflow_detail(report)

    assert detail == "Missing architectural documentation detailing how the recorded change affects the export worker."


def test_project_index_payload_reports_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    entries = [
        {
            "project": "demo",
            "intake": "projects/demo/demo_intake.json",
            "latest_project_check": "projects/demo/workspace/forensic_workbench_latest_row_action.json",
        }
    ]
    folders = [
        {"project": "demo", "project_dir": "projects/demo", "status": "intake_ready"},
        {
            "project": "pending",
            "project_dir": "projects/pending",
            "status": "needs_intake",
            "raw_exists": True,
            "source_preview_files": ["projects/pending/thesis.md"],
        },
        {"project": "_bench_generated", "project_dir": "projects/_bench_generated", "status": "needs_intake"},
    ]
    monkeypatch.setattr(module.snapshot, "list_project_entries", lambda: entries)
    monkeypatch.setattr(module.snapshot, "list_project_folders", lambda _entries: folders)
    monkeypatch.setattr(module, "intake_payload_for_project", lambda *_args, **_kwargs: {"editable": True, "reference_status": {"summary": {"total": 1, "present": 1}}})

    payload = module.project_index_payload()

    assert payload["ok"] is True
    assert payload["ready_count"] == 1
    assert payload["project_inventory_scope"] == "local"
    assert payload["inventory_root"] == "projects/"
    assert payload["inventory_includes_all_project_folders"] is True
    assert payload["folder_count"] == 3
    assert payload["pending_folder_count"] == 2
    assert payload["folder_summary"] == payload["project_folder_summary"]
    assert payload["project_folders_compact"] is True
    pending = next(row for row in payload["project_folders"] if row["project"] == "pending")
    assert pending["source_preview"] == "projects/pending/thesis.md"
    assert "recovery_actions" not in pending
    assert payload["project_folder_summary"]["needs_intake"] == 2
    assert payload["project_folder_summary"]["needs_intake_with_files"] == 1
    assert payload["project_folder_summary"]["needs_intake_empty"] == 1
    assert payload["project_folder_summary"]["generated_hidden_by_default"] == 1
    assert payload["projects"][0]["intake_editable"] is True
    assert payload["projects"][0]["intake_ref_summary"] == {"total": 1, "present": 1}
    assert payload["projects"][0]["display_label"] == "Demo"
    assert payload["projects"][0]["status"] == "intake_ready"
    assert payload["projects"][0]["project_status"] == "intake_ready"
    assert payload["projects"][0]["status_label"] == "project brief ready"
    assert payload["projects"][0]["next_action"]["label"] == "Open project"
    assert payload["projects"][0]["latest_project_check"] == "projects/demo/workspace/forensic_workbench_latest_row_action.json"
    assert payload["project_folders_compact"] is True
    assert payload["project_folder_detail_field"] == "project_folders"
    assert "raw_preview_files" not in payload["project_folders"][0]
    assert payload["project_folders"][0]["latest_project_check"] == "projects/demo/workspace/forensic_workbench_latest_row_action.json"
    assert pending["display_label"] == "Pending"
    assert pending["project_status"] == "needs_intake"
    assert pending["status_label"] == "needs project brief"
    assert pending["openable"] is False
    assert pending["next_action"]["label"] == "Create project brief"
    assert pending["has_project_material"] is True
    assert pending["hidden_by_default"] is False
    assert not any(row["project"] == "_bench_generated" for row in payload["project_folders"])


def test_existing_project_recovery_draft_uses_folder_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "pending"
    project_root.mkdir(parents=True)
    (project_root / "thesis.md").write_text("# Thesis\n\nThe project thesis comes from existing notes.\n", encoding="utf-8")
    (project_root / "evidence.txt").write_text("Evidence file supports part of the thesis.\n", encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.existing_project_recovery_draft("pending")

    assert payload["ok"] is True
    assert payload["status"] == "needs project brief"
    assert payload["display_label"] == "Pending"
    assert payload["can_add_intake"] is True
    assert payload["summary"] == "needs project brief; found 2 useful files, suggested 2 source files and 1 evidence file."
    assert payload["bounded_claim"] == "The project thesis comes from existing notes."
    assert payload["next_falsifier"] == ""
    assert "Review these files before saving the project brief" in payload["notes"]
    assert "projects/pending/thesis.md" in payload["notes"]
    assert "Evidence file supports part of the thesis" not in payload["notes"]
    assert payload["source_refs"] == ["projects/pending/thesis.md", "projects/pending/evidence.txt"]
    assert payload["evidence_refs"] == ["projects/pending/evidence.txt"]
    assert payload["source_ref_count"] == 2
    assert payload["evidence_ref_count"] == 1
    assert payload["candidate_file_count"] == 2
    assert payload["candidate_files"] == [
        {
            "path": "projects/pending/thesis.md",
            "role": "thesis",
            "previewable": True,
            "binds_as_source": True,
            "binds_as_evidence": False,
        },
        {
            "path": "projects/pending/evidence.txt",
            "role": "evidence",
            "previewable": True,
            "binds_as_source": True,
            "binds_as_evidence": True,
        },
    ]
    assert payload["recovery_summary"]["folder"] == "projects/pending"
    assert payload["recovery_summary"]["intake_target"] == "projects/pending/pending_intake.json"
    assert payload["recovery_summary"]["drafted_from_file_count"] == 2
    assert payload["recovery_summary"]["bounded_claim_drafted"] is True
    assert payload["recovery_summary"]["summary"] == payload["summary"]
    assert [step["label"] for step in payload["after_connect_steps"]] == [
        "Review draft",
        "Inspect source files",
        "Prepare files",
    ]
    assert payload["write_boundary"]["writes_project_files"] is False
    assert payload["add_intake_action"]["id"] == "add_intake"
    assert "Runs stay blocked until the project brief names the thesis" in payload["add_intake_action"]["rule"]
    assert payload["add_intake_action"]["write_boundary"] == payload["add_intake_write_boundary"]
    assert payload["add_intake_write_boundary"]["writes_project_files"] is True
    assert payload["add_intake_write_boundary"]["write_paths"] == [
        "projects/pending",
        "projects/pending/raw",
        "projects/pending/workspace",
        "projects/pending/raw/source_type_map.json",
        "projects/pending/project_charter.md",
        "projects/pending/pending_intake.json",
    ]
    assert payload["add_intake_write_boundary"]["receipt_path"] == "projects/pending/pending_intake.json"


def test_existing_project_recovery_draft_rejects_stub_thesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "pending"
    project_root.mkdir(parents=True)
    (project_root / "thesis.md").write_text("# t\n", encoding="utf-8")
    (project_root / "evidence.txt").write_text("Evidence file supports a real review.\n", encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.existing_project_recovery_draft("pending")

    assert payload["ok"] is True
    assert payload["bounded_claim"] == ""
    assert payload["recovery_summary"]["bounded_claim_drafted"] is False
    assert payload["source_refs"] == ["projects/pending/thesis.md", "projects/pending/evidence.txt"]
    assert payload["evidence_refs"] == ["projects/pending/evidence.txt"]


def test_existing_project_recovery_draft_ignores_metadata_and_uses_charter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "pending"
    raw_dir = project_root / "raw"
    raw_dir.mkdir(parents=True)
    (project_root / "project_charter.md").write_text(
        "# Charter\n\nRecover this charter claim from the historical folder.\n",
        encoding="utf-8",
    )
    (raw_dir / "source.md").write_text("A real raw source.\n", encoding="utf-8")
    (raw_dir / "source_type_map.json").write_text('{"source.md": "source_evidence"}\n', encoding="utf-8")
    (project_root / "workspace").mkdir()
    (project_root / "workspace" / "source_index_receipt.json").write_text('{"ok": true}\n', encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.existing_project_recovery_draft("pending")

    all_refs = payload["source_refs"] + payload["evidence_refs"] + [
        row["path"] for row in payload["candidate_files"]
    ]
    assert payload["bounded_claim"] == "Recover this charter claim from the historical folder."
    assert "projects/pending/raw/source.md" in payload["source_refs"]
    assert "projects/pending/raw/source.md" in payload["evidence_refs"]
    assert "projects/pending/raw/source_type_map.json" not in all_refs
    assert "projects/pending/workspace/source_index_receipt.json" not in all_refs


def test_existing_project_recovery_draft_surfaces_historical_run_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "pending"
    workspace = project_root / "workspace"
    workspace.mkdir(parents=True)
    (project_root / "thesis.md").write_text("Historical thesis.\n", encoding="utf-8")
    (project_root / "latest_eval_results.json").write_text('{"score": 82}\n', encoding="utf-8")
    (project_root / "champion_probability_dag.json").write_text('{"outcome": "bounded"}\n', encoding="utf-8")
    (workspace / "fit_result_iter_001.json").write_text('{"rmse": 0.2, "n_fit_rows": 50, "k_params": 2}\n', encoding="utf-8")
    (workspace / "fit_result_iter_002.json").write_text('{"rmse": 0.3, "n_fit_rows": 50, "k_params": 2}\n', encoding="utf-8")
    (workspace / "iteration_telemetry.jsonl").write_text('{"record_type":"iteration","iteration_index":1}\n', encoding="utf-8")
    (workspace / "structural_memory.json").write_text('{"patterns":[]}\n', encoding="utf-8")
    (workspace / "source_index_receipt.json").write_text('{"ok": true}\n', encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.existing_project_recovery_draft("pending")
    files_by_path = {row["path"]: row for row in payload["candidate_files"]}
    all_refs = payload["source_refs"] + payload["evidence_refs"] + list(files_by_path)

    assert files_by_path["projects/pending/latest_eval_results.json"]["role"] == "run result"
    assert files_by_path["projects/pending/champion_probability_dag.json"]["role"] == "probability model"
    assert files_by_path["projects/pending/workspace/fit_result_iter_001.json"]["role"] == "fit history"
    assert files_by_path["projects/pending/workspace/iteration_telemetry.jsonl"]["role"] == "run history"
    assert files_by_path["projects/pending/workspace/structural_memory.json"]["role"] == "assumption"
    assert "projects/pending/workspace/fit_result_iter_002.json" in payload["evidence_refs"]
    assert "projects/pending/workspace/source_index_receipt.json" not in all_refs
    assert payload["candidate_file_count"] >= 6


def test_existing_project_recovery_draft_does_not_offer_add_intake_when_intake_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    project_root = tmp_path / "projects" / "ready"
    project_root.mkdir(parents=True)
    (project_root / "thesis.md").write_text("Recovered thesis.\n", encoding="utf-8")
    (project_root / "ready_intake.json").write_text('{"ok": true}\n', encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    monkeypatch.setattr(module.snapshot, "validate_project_slug", lambda project: project)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.existing_project_recovery_draft("ready")

    assert payload["status"] == "project brief already exists"
    assert payload["can_add_intake"] is False
    assert payload["add_intake_action"] is None
    assert payload["add_intake_write_boundary"] is None


def test_failed_write_responses_have_no_write_boundary() -> None:
    module = load_server_module()

    for endpoint in module.WRITE_POST_ENDPOINTS:
        payload = module.post_error_payload(endpoint, ValueError("invalid write request"))

        assert payload["ok"] is False
        assert payload["error"] == "invalid write request"
        assert payload["write_boundary"]["writes_project_files"] is False
        assert payload["write_boundary"]["browser_writes"] is False
        assert payload["write_boundary"]["write_paths"] == []


def test_create_project_payload_runs_source_init_then_intake_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "source-init" in command:
            raw_dir = tmp_path / "projects" / "fresh" / "raw"
            raw_dir.mkdir(parents=True)
            (tmp_path / "projects" / "fresh" / "workspace").mkdir()
            (raw_dir / "source_type_map.json").write_text("{}\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module, "project_index_payload", lambda: {"projects": [{"project": "fresh"}]})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "fresh", "rows": []})

    payload = module.create_project_payload(
        project="fresh",
        task="Check a bounded claim",
        bounded_claim="A narrow claim.",
        next_falsifier="Find a contrary source.",
        source_refs=["raw/source.md"],
        non_claims=["not a broad claim"],
    )

    assert payload["schema"] == "ztare-forensic-workbench-project-create-v1"
    assert payload["ok"] is True
    assert payload["accepted"] is True
    assert payload["creation_complete"] is True
    assert payload["created_mode"] == "create_project"
    assert payload["project_existed_before"] is False
    assert payload["source_init_accepted"] is True
    assert payload["intake_create_accepted"] is True
    assert payload["intake_file_exists"] is False
    assert payload["intake"] == "projects/fresh/fresh_intake.json"
    assert payload["created_paths"] == [
        "projects/fresh",
        "projects/fresh/raw",
        "projects/fresh/workspace",
        "projects/fresh/project_charter.md",
        "projects/fresh/fresh_intake.json",
    ]
    assert (tmp_path / "projects/fresh/project_charter.md").read_text(encoding="utf-8").startswith(
        "# Fresh Project Charter\n"
    )
    assert payload["write_boundary"]["writes_project_files"] is True
    assert payload["write_boundary"]["write_paths"] == payload["created_paths"]
    assert payload["write_boundary"]["receipt_path"] == "projects/fresh/fresh_intake.json"
    assert payload["write_boundary"]["latest_path"] == "projects/fresh/fresh_intake.json"
    assert commands[0][:6] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "source-init", "--project"]
    assert commands[1][:6] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "intake", "create"]
    assert "--source-ref" in commands[1]
    assert "--non-claim" in commands[1]


def test_create_project_payload_writes_uploaded_raw_files_into_intake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "source-init" in command:
            raw_dir = tmp_path / "projects" / "fresh" / "raw"
            raw_dir.mkdir(parents=True)
            (tmp_path / "projects" / "fresh" / "workspace").mkdir()
            (raw_dir / "source_type_map.json").write_text("{}\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module, "project_index_payload", lambda: {"projects": [{"project": "fresh"}]})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "fresh", "rows": []})

    payload = module.create_project_payload(
        project="fresh",
        task="Check a bounded claim",
        bounded_claim="A narrow claim.",
        next_falsifier="Find a contrary source.",
        uploaded_sources=[
            {
                "filename": "evidence.md",
                "source_type": "source_evidence",
                "body": "Evidence text.",
            },
            {
                "filename": "context.md",
                "source_type": "research_question",
                "body": "Context text.",
            },
        ],
    )

    raw_dir = tmp_path / "projects" / "fresh" / "raw"
    assert (raw_dir / "evidence.md").read_text(encoding="utf-8") == (
        "---\nsource_type: source_evidence\nartifact_kind: raw_evidence\n---\n\nEvidence text.\n"
    )
    assert (raw_dir / "context.md").read_text(encoding="utf-8") == (
        "---\nsource_type: research_question\nartifact_kind: raw_evidence\n---\n\nContext text.\n"
    )
    assert json.loads((raw_dir / "source_type_map.json").read_text(encoding="utf-8")) == {
        "context.md": "research_question",
        "evidence.md": "source_evidence",
    }
    assert payload["uploaded_evidence_refs"] == ["projects/fresh/raw/evidence.md"]
    assert payload["uploaded_source_refs"] == ["projects/fresh/raw/context.md"]
    assert "projects/fresh/raw/evidence.md" in payload["created_paths"]
    assert "projects/fresh/raw/context.md" in payload["created_paths"]
    assert "--evidence-ref" in commands[1]
    assert "projects/fresh/raw/evidence.md" in commands[1]
    assert "--source-ref" in commands[1]
    assert "projects/fresh/raw/context.md" in commands[1]


def test_create_project_payload_reports_partial_source_init_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        if "source-init" in command:
            (tmp_path / "projects" / "partial" / "raw").mkdir(parents=True)
            (tmp_path / "projects" / "partial" / "workspace").mkdir()
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="intake failed")

    monkeypatch.setattr(module.snapshot, "run", fake_run)

    payload = module.create_project_payload(
        project="partial",
        task="Check a bounded claim",
        bounded_claim="A narrow claim.",
        next_falsifier="Find a contrary source.",
    )

    assert payload["accepted"] is False
    assert payload["creation_complete"] is False
    assert payload["intake_file_exists"] is False
    assert payload["created_paths"] == [
        "projects/partial",
        "projects/partial/raw",
        "projects/partial/workspace",
    ]
    assert payload["write_boundary"]["writes_project_files"] is True
    assert payload["write_boundary"]["write_paths"] == payload["created_paths"]


def test_create_project_payload_can_add_intake_to_existing_folder_without_intake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    existing = tmp_path / "projects" / "existing"
    existing.mkdir(parents=True)
    (existing / "thesis.md").write_text("Recovered thesis.\n", encoding="utf-8")

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        if "source-init" in command:
            raw_dir = tmp_path / "projects" / "existing" / "raw"
            raw_dir.mkdir(parents=True)
            (tmp_path / "projects" / "existing" / "workspace").mkdir()
            (raw_dir / "source_type_map.json").write_text("{}\n", encoding="utf-8")
            payload = {
                "ok": True,
                "created_dirs": ["projects/existing/raw", "projects/existing/workspace"],
                "created_files": ["projects/existing/raw/source_type_map.json"],
            }
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module, "project_index_payload", lambda: {"projects": [{"project": "existing"}]})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "existing", "rows": []})

    payload = module.create_project_payload(
        project="existing",
        task="Check a bounded claim",
        bounded_claim="A narrow claim.",
        next_falsifier="Find a contrary source.",
        source_refs=["projects/existing/thesis.md"],
    )

    assert payload["accepted"] is True
    assert payload["created_mode"] == "add_intake"
    assert payload["project_existed_before"] is True
    assert payload["created_paths"] == [
        "projects/existing/raw",
        "projects/existing/workspace",
        "projects/existing/raw/source_type_map.json",
        "projects/existing/raw/thesis.md",
        "projects/existing/workspace/forensic_workbench_source_imports.jsonl",
        "projects/existing/workspace/forensic_workbench_latest_source_import.json",
        "projects/existing/project_charter.md",
        "projects/existing/existing_intake.json",
    ]
    assert payload["recovered_source_refs"] == ["projects/existing/raw/thesis.md"]
    assert (tmp_path / "projects/existing/raw/thesis.md").read_text(encoding="utf-8") == (
        "---\nsource_type: source_evidence\nartifact_kind: raw_evidence\n---\n\nRecovered thesis.\n"
    )


def test_create_project_payload_accepts_existing_intake_after_command_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        if "source-init" in command:
            (tmp_path / "projects" / "warned" / "raw").mkdir(parents=True)
            (tmp_path / "projects" / "warned" / "workspace").mkdir()
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")
        intake_path = tmp_path / "projects" / "warned" / "warned_intake.json"
        intake_path.write_text('{"project": "warned"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="created intake but returned warning")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module, "project_index_payload", lambda: {"projects": [{"project": "warned"}]})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "warned", "rows": []})

    payload = module.create_project_payload(
        project="warned",
        task="Check a bounded claim",
        bounded_claim="A narrow claim.",
        next_falsifier="Find a contrary source.",
    )

    assert payload["accepted"] is True
    assert payload["creation_complete"] is True
    assert payload["intake_create_accepted"] is False
    assert payload["intake_file_exists"] is True
    assert "projects/warned/warned_intake.json" in payload["created_paths"]


def test_import_source_payload_writes_raw_source_and_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw = project_root / "raw"
    workspace = project_root / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (raw / "source_type_map.json").write_text("{}\n", encoding="utf-8")
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "source_action_payload_for_project", lambda **_kwargs: {"accepted": True, "snapshot": {"project": "demo"}, "trace": {"readiness": "ready"}})

    body = "  Observed failure mode.\n\nTrailing note  "
    payload = module.import_source_payload(
        project="demo",
        filename="source_note.md",
        source_type="source_evidence",
        body=body,
    )

    source_path = raw / "source_note.md"
    receipt_path = workspace / "forensic_workbench_source_imports.jsonl"
    latest_path = workspace / "forensic_workbench_latest_source_import.json"
    assert payload["schema"] == "ztare-forensic-workbench-source-import-v1"
    assert payload["source_path"] == "projects/demo/raw/source_note.md"
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_source_import.json"
    assert source_path.read_text(encoding="utf-8") == (
        f"---\nsource_type: source_evidence\nartifact_kind: project_note\n---\n\n{body}\n"
    )
    assert json.loads((raw / "source_type_map.json").read_text(encoding="utf-8")) == {"source_note.md": "source_evidence"}
    receipt = json.loads(receipt_path.read_text(encoding="utf-8").strip())
    assert receipt["schema"] == "ztare-forensic-workbench-source-import-v1"
    assert receipt["source_path"] == "projects/demo/raw/source_note.md"
    assert receipt["intake"] == "projects/demo/demo_intake.json"
    assert receipt["case_key"] == "demo::projects/demo/demo_intake.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest["source_path"] == "projects/demo/raw/source_note.md"


def test_project_brief_and_charter_writes_cross_the_cli_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "workspace").mkdir(parents=True)
    intake_path = project_root / "demo_intake.json"
    intake_path.write_text(
        json.dumps({
            "project": "demo",
            "bounded_claim": "Original claim",
            "next_falsifier": "Original test",
            "notes": "",
            "non_claims": [],
            "source_refs": [],
            "evidence_refs": [],
        }),
        encoding="utf-8",
    )
    charter_path = project_root / "project_charter.md"
    charter_path.write_text("# Demo\n\nOriginal mandate.\n", encoding="utf-8")

    brief = module.apply_intake_edit(
        project="demo",
        intake="projects/demo/demo_intake.json",
        raw_patch={"bounded_claim": "Updated claim"},
    )
    charter = module.apply_charter_edit(
        project="demo",
        intake="projects/demo/demo_intake.json",
        text="# Demo\n\nUpdated mandate.\n",
    )

    assert brief["ok"] is True
    assert brief["receipt"]["updated_fields"] == ["bounded_claim"]
    assert json.loads(intake_path.read_text(encoding="utf-8"))["bounded_claim"] == "Updated claim"
    assert charter["ok"] is True
    assert charter["receipt"]["charter_path"] == "projects/demo/project_charter.md"
    assert "Updated mandate" in charter_path.read_text(encoding="utf-8")


def test_scoring_guide_and_research_map_writes_cross_the_cli_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "workspace").mkdir(parents=True)
    (tmp_path / "rubrics").mkdir()
    (project_root / "demo_intake.json").write_text(
        json.dumps({"project": "demo", "bounded_claim": "Claim", "next_falsifier": "Test"}),
        encoding="utf-8",
    )
    research_map = {
        "schema": module.RESEARCH_MAP_SCHEMA,
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "summary": "One claim and its next test.",
        "markdown": "# Research map\n",
        "sections": [],
    }
    monkeypatch.setattr(
        module,
        "workflow_payload_for_project",
        lambda **_kwargs: {"project_state": {"research_map": research_map}},
    )

    guide = module.save_scoring_guide_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        text=json.dumps({
            "persona": "Reviewer",
            "criteria": "Check the claim.",
            "dimensions": [{"name": "Backing", "weight": 100, "description": "Evidence is traceable."}],
        }),
    )
    saved_map = module.save_research_map_payload({
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
    })

    assert guide["saved"] is True
    assert (tmp_path / "rubrics" / "demo.json").exists()
    assert saved_map["accepted"] is True
    assert (project_root / "workspace" / "research_map.json").exists()


def test_import_source_payload_preserves_write_when_source_check_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw = project_root / "raw"
    workspace = project_root / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (raw / "source_type_map.json").write_text("{}\n", encoding="utf-8")
    (project_root / "demo_intake.json").write_text(
        json.dumps({"project": "demo", "bounded_claim": "demo"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    def failing_source_check(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("source check unavailable")

    monkeypatch.setattr(module, "source_action_payload_for_project", failing_source_check)

    payload = module.import_source_payload(
        project="demo",
        filename="source_note.md",
        source_type="source_evidence",
        body="Observed failure mode.",
    )

    assert payload["ok"] is True
    assert payload["source_path"] == "projects/demo/raw/source_note.md"
    assert payload["source_check"]["accepted"] is False
    assert payload["source_check"]["error"] == "source check unavailable"
    assert (raw / "source_note.md").exists()
    assert (workspace / "forensic_workbench_source_imports.jsonl").exists()
    assert (workspace / "forensic_workbench_latest_source_import.json").exists()


def test_edit_source_payload_updates_raw_source_and_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw = project_root / "raw"
    workspace = project_root / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (raw / "source_type_map.json").write_text(json.dumps({"source_note.md": "source_evidence"}) + "\n", encoding="utf-8")
    (raw / "source_note.md").write_text(
        "---\nsource_type: source_evidence\nartifact_kind: computation_output\ncreated_by: notebook\n---\n\nOld body.\n",
        encoding="utf-8",
    )
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "source_action_payload_for_project", lambda **_kwargs: {"accepted": True, "snapshot": {"project": "demo"}, "trace": {"readiness": "ready"}})

    payload = module.edit_source_payload(
        project="demo",
        relative_path="source_note.md",
        source_type="research_question",
        body="New body.",
    )

    source_path = raw / "source_note.md"
    receipt_path = workspace / "forensic_workbench_source_edits.jsonl"
    latest_path = workspace / "forensic_workbench_latest_source_edit.json"
    assert payload["schema"] == "ztare-forensic-workbench-source-edit-v1"
    assert payload["source_path"] == "projects/demo/raw/source_note.md"
    assert payload["relative_raw_path"] == "source_note.md"
    assert payload["artifact_kind"] == "computation_output"
    assert payload["created_by"] == "notebook"
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_source_edit.json"
    edited = source_path.read_text(encoding="utf-8")
    assert "source_type: research_question" in edited
    assert "artifact_kind: computation_output" in edited
    assert "created_by: notebook" in edited
    assert "New body." in edited
    assert json.loads((raw / "source_type_map.json").read_text(encoding="utf-8")) == {"source_note.md": "research_question"}
    receipt = json.loads(receipt_path.read_text(encoding="utf-8").strip())
    assert receipt["schema"] == "ztare-forensic-workbench-source-edit-v1"
    assert receipt["source_path"] == "projects/demo/raw/source_note.md"
    assert receipt["source_type"] == "research_question"
    assert receipt["artifact_kind"] == "computation_output"
    assert receipt["created_by"] == "notebook"
    assert receipt["intake"] == "projects/demo/demo_intake.json"
    assert receipt["case_key"] == "demo::projects/demo/demo_intake.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest["source_path"] == "projects/demo/raw/source_note.md"
    assert latest["source_type"] == "research_question"


def test_edit_source_payload_preserves_source_body_whitespace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw = project_root / "raw"
    workspace = project_root / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (raw / "source_type_map.json").write_text(json.dumps({"source_note.md": "source_evidence"}) + "\n", encoding="utf-8")
    (raw / "source_note.md").write_text("---\nsource_type: source_evidence\n---\n\nOld body.\n", encoding="utf-8")
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "source_action_payload_for_project", lambda **_kwargs: {"accepted": True, "snapshot": {"project": "demo"}, "trace": {"readiness": "ready"}})

    body = "  Leading space\n\nTrailing space  "
    module.edit_source_payload(
        project="demo",
        relative_path="source_note.md",
        source_type="source_evidence",
        body=body,
    )

    source_text = (raw / "source_note.md").read_text(encoding="utf-8")
    assert source_text == f"---\nsource_type: source_evidence\n---\n\n{body}\n"
    assert module.split_source_frontmatter(source_text, fallback_source_type="source_evidence") == ("source_evidence", body)


def test_edit_source_payload_rejects_noop_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    raw = project_root / "raw"
    workspace = project_root / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir()
    (raw / "source_type_map.json").write_text(json.dumps({"source_note.md": "source_evidence"}) + "\n", encoding="utf-8")
    (raw / "source_note.md").write_text("---\nsource_type: source_evidence\n---\n\nSame body.\n", encoding="utf-8")
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")

    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")

    payload = module.edit_source_payload(
        project="demo",
        relative_path="source_note.md",
        source_type="source_evidence",
        body="Same body.",
    )

    assert payload["ok"] is False
    assert "no changed fields" in payload["error"]
    assert not (workspace / "forensic_workbench_source_edits.jsonl").exists()


def test_review_file_handoff_surfaces_in_refreshed_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_module = load_module()
    review_module = load_review_module()
    monkeypatch.setattr(snapshot_module, "REPO", tmp_path)
    monkeypatch.setattr(review_module, "REPO", tmp_path)
    review_file_path = tmp_path / "demo_report_export_review.json"
    review_file_path.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-v1",
                "project": "demo",
                "rubric": "demo",
                "row": "Report support",
                "row_status": "blocked",
                "decision": "blocked",
                "note": "Need current source binding before export.",
                "evidence_refs": [
                    {"type": "evidence", "value": "projects/demo/synthesis/report_support_contract.json"},
                    {"type": "command", "value": "make synth-contract PROJECT=demo"},
                ],
            }
        ),
        encoding="utf-8",
    )

    review_module.apply_review(
        Namespace(
            project="demo",
            row="report_export",
            review_file_path=str(review_file_path),
            ledger=None,
            latest=None,
        )
    )
    latest_review, latest_path = snapshot_module.load_latest_review("demo")
    rows = snapshot_module.build_rows(
        fixture_trace(),
        fixture_report_contract(),
        trace_command="ztare autoresearch trace --project demo --json",
        report_command="make synth-contract PROJECT=demo RENDERER=decision_brief",
        latest_review=latest_review,
        latest_review_artifact_path=latest_path,
    )

    receipt_row = next(row for row in rows if row["label"] == "Latest saved review")
    assert latest_path == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert receipt_row["status"] == "applied"
    assert receipt_row["file"] == latest_path
    assert "Report readiness: hold report" in receipt_row["detail"]


def test_apply_review_file_rejects_row_mismatch(tmp_path: Path) -> None:
    module = load_review_module()
    review_file_path = tmp_path / "source_readiness_review.json"
    review_file_path.write_text(
        json.dumps(
            {
                "schema": "ztare-forensic-workbench-review-v1",
                "project": "demo",
                "row": "Source readiness",
                "decision": "reviewed",
                "evidence_refs": [{"type": "file", "value": "source_index.json"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        module.apply_review(
            Namespace(
                project="demo",
                row="report_export",
                review_file_path=str(review_file_path),
                ledger=str(tmp_path / "reviews.jsonl"),
                latest=str(tmp_path / "latest.json"),
            )
        )


def test_citation_binding_uses_indexed_source_and_demotes_when_source_changes(
    tmp_path: Path
) -> None:
    from ztare.scenarios.evidence_admission import admit_source_passage

    project_dir = tmp_path / "projects" / "demo"
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True)
    source_path = raw_dir / "interviews.md"
    source_body = "Customers will adopt it. Nine customers asked for the workflow."
    source_path.write_text(source_body, encoding="utf-8")
    (raw_dir / "source_type_map.json").write_text(
        json.dumps({"interviews.md": "source_evidence"}), encoding="utf-8"
    )
    (project_dir / "latest_eval_results.json").write_text(json.dumps({
        "probability_dag": {
            "outcome": {"label": "Launch the product", "probability": 0.8},
            "nodes": [{"id": "demand", "label": "Customers will adopt it", "probability": 0.7}],
        }
    }), encoding="utf-8")

    exact = admit_source_passage({
        "project": "demo",
        "source_path": "interviews.md",
        "excerpt": "Customers will adopt it.",
        "target": "claim:demand",
    }, tmp_path)
    assert exact["ok"] is True, exact
    assert exact["bound"]["source_tier"] == "cited"
    assert exact["bound"]["inference_tier"] == "cited"
    assert exact["decision_before"]["schema"] == "ztare-decision-state-v1"
    assert exact["decision_after"]["schema"] == "ztare-decision-state-v1"
    assert exact["decision_delta"]["schema"] == "ztare-decision-delta-v1"
    assert exact["decision_history"]["graph"]["hash"]

    relevant = admit_source_passage({
        "project": "demo",
        "source_path": "interviews.md",
        "excerpt": "Nine customers asked for the workflow.",
        "target": "claim:demand",
    }, tmp_path)
    assert relevant["ok"] is True
    assert relevant["bound"]["source_tier"] == "cited"
    assert relevant["bound"]["inference_tier"] == "unchecked"
    assert isinstance(relevant["decision_delta"]["decision_changed"], bool)

    overlay = json.loads((project_dir / "workspace" / "governed_overlay.json").read_text(encoding="utf-8"))
    assert len(overlay["elements"]) == 2 and len(overlay["edges"]) == 2
    assert {edge["warrant"] for edge in overlay["edges"]} == {"W2", "W3"}

    from ztare.reports.research_graph import build_research_graph
    current = build_research_graph("demo", tmp_path)
    exact_edge = next(edge for edge in current["edges"] if edge.get("admission") == "exact_claim_quote")
    assert exact_edge["warrant"] == "W2" and exact_edge["admission_status"] == "current"

    source_path.write_text(source_body + " Changed.", encoding="utf-8")
    stale = build_research_graph("demo", tmp_path)
    exact_edge = next(edge for edge in stale["edges"] if edge.get("admission") == "exact_claim_quote")
    assert exact_edge["warrant"] == "W3" and exact_edge["admission_status"] == "stale_source"


def test_document_upload_extracts_and_stages_original_with_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import io
    import zipfile

    module = load_server_module()
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Approve the launch.</w:t>'
            '</w:r></w:p></w:body></w:document>',
        )
    encoded = base64.b64encode(raw.getvalue()).decode("ascii")
    preview = module.document_extract_payload({"filename": "launch.docx", "content_base64": encoded})
    assert preview["ok"] and preview["text"] == "Approve the launch."

    rows = module.uploaded_source_rows_for_project([{
        "filename": preview["extracted_filename"],
        "original_filename": "launch.docx",
        "original_base64": encoded,
        "source_type": "source_evidence",
        "body": preview["text"],
    }])
    assert rows[0]["filename"] == "launch.extracted.md"
    assert rows[0]["original_sha256"] == preview["sha256"]

    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    (tmp_path / "projects" / "demo" / "raw").mkdir(parents=True)
    (tmp_path / "projects" / "demo" / "workspace").mkdir()
    (tmp_path / "projects" / "demo" / "raw" / "source_type_map.json").write_text("{}\n", encoding="utf-8")
    source_refs, evidence_refs, writes = module.stage_uploaded_source_rows("demo", rows)
    assert source_refs == []
    assert evidence_refs == ["projects/demo/raw/launch.extracted.md"]
    assert "projects/demo/attachments/launch.docx" in writes
    extracted = (tmp_path / "projects/demo/raw/launch.extracted.md").read_text(encoding="utf-8")
    assert "original_sha256:" in extracted and "extraction_method: docx-xml" in extracted
    assert "Approve the launch." in extracted
