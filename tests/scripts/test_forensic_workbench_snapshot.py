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


def load_live_module():
    spec = importlib.util.spec_from_file_location("forensic_workbench_live", LIVE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_display_detail_normalizes_next_step_tokens() -> None:
    module = load_module()

    assert module.display_detail("Report support: next_step; export_blocker") == (
        "Report support: next step; fix report support"
    )
    assert module.display_detail("source_index=fresh; output_binding=fresh") == (
        "file index: fresh; evidence connection: fresh"
    )


def test_project_display_label_uses_visible_project_language() -> None:
    module = load_server_module()

    assert module.project_display_label("riemann_operator_search") == "Riemann system search"
    assert module.project_display_label("ns_defect_packet_certificate") == "Ns defect intake certificate"
    assert module.project_display_label("hbr_case_method_roi_proxy") == "Hbr project method roi proxy"
    assert module.project_display_label("eu_union_load_bearing_pillars") == "Eu union key pillars"


def test_health_payload_adds_plain_evidence_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    assert module.display_action_label("unconsumed_surface") == "work log is missing"
    assert module.display_value("export_blocker") == "fix report support"
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
    assert issue["display_blocking_rule"] == "doc-only evidence-ledger linkage cannot support substantive recommendations"
    assert issue["display_evidence_refs"] == [
        {
            "label": "Evidence ledger file",
            "path": "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md",
        }
    ]
    assert recommendation["display_evidence_refs"] == [
        {"label": "Forecast summary file", "path": "analytics/public/forecast_pool/aggregates/demo.json"}
    ]


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
        "Preflight",
        "Loop admission",
        "Report support",
        "Latest review receipt",
    }.issubset(labels)
    assert module.validate_rows(rows) == []
    assert all(row["provenance"] for row in rows)
    report_row = next(row for row in rows if row["label"] == "Report support")
    assert report_row["status"] == "blocked"
    assert "make synth-contract PROJECT=demo" in report_row["command"]
    assert report_row["evidence"] == "projects/demo/synthesis/report_support_contract.json"
    assert report_row["review_artifact"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    latest_review_row = next(row for row in rows if row["label"] == "Latest review receipt")
    assert latest_review_row["status"] == "no_review_applied"
    assert latest_review_row["warning"] == "no applied review receipt"
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

    receipt_row = next(row for row in rows if row["label"] == "Latest review receipt")
    assert receipt_row["status"] == "applied"
    assert receipt_row["kind"] == "ready"
    assert receipt_row["file"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert receipt_row["review_artifact"] == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert "Report support: hold report" in receipt_row["detail"]
    assert "3 evidence refs" in receipt_row["detail"]


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
    receipt_row = next(row for row in rows if row["label"] == "Latest review receipt")
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
    assert "Project steps" in rendered
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
    assert payload["latest_review"]["row"] == "Report support"
    assert payload["latest_review"]["item_label"] == "Report support"
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
    (tmp_path / "projects/no_intake").mkdir()
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
            "status": "case_ready",
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
    target.write_text("claim source\nline two\n", encoding="utf-8")

    payload = module.file_preview_payload("projects/demo/source.md")

    assert payload["schema"] == "ztare-forensic-workbench-file-preview-v1"
    assert payload["path"] == "projects/demo/source.md"
    assert payload["truncated"] is False
    assert "claim source" in payload["text"]
    with pytest.raises(ValueError):
        module.file_preview_payload("../outside.md")
    with pytest.raises(ValueError):
        module.file_preview_payload("papers/cognitive-camouflage/draft.md")


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
        assert payload["project_check_label"] == "Report support"
        assert payload["item_label"] == "Report support"
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
    assert payload["project_check_label"] == "Report support"
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
    assert payload["write_boundary"]["read_only_actions"] == ["Copy command detail", "Inspect output"]
    assert seen["timeout"] == 120
    command = seen["command"]
    assert isinstance(command, list)
    assert "--preflight-only" in command
    assert command[:5] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "autoresearch", "run"]


def test_preflight_payload_failed_check_has_no_write_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert payload["write_boundary"]["write_paths"] == []
    assert payload["write_boundary"]["browser_writes"] is False


def test_bounded_run_payload_requires_confirmation_and_uses_surfaced_command(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    commands: list[list[str]] = []
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
    assert preview["accepted"] is False
    assert preview["writes"] is False
    assert preview["write_boundary"]["writes_project_files"] is False
    assert preview["write_boundary"]["read_only_actions"] == ["Inspect run plan", "Copy command detail"]
    assert preview["confirmed_write_boundary"]["writes_project_files"] is True
    assert preview["confirmed_write_boundary"]["read_only_actions"] == ["Inspect run plan", "Copy command detail"]
    assert "projects/demo/latest_eval_results.json" in preview["confirmed_write_boundary"]["write_paths"]
    assert commands == [[module.SERVER_PYTHON, "-m", "src.ztare.cli", "autoresearch", "run", "--project", "demo", "--rubric", "demo", "--intake", "projects/demo/demo_intake.json", "--iters", "1"]]
    assert payload["ok"] is True
    assert payload["accepted"] is True
    assert payload["returncode"] == 0
    assert payload["writes"] is True
    assert payload["write_boundary"]["writes_project_files"] is True
    assert "projects/demo/latest_eval_results.json" in payload["write_boundary"]["write_paths"]


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
            "error": "Run plan is not ready for a project run. Run preflight first.",
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

    assert response.status == 400
    assert payload["requires_confirmation"] is False
    assert payload["write_boundary"]["writes_project_files"] is False


def test_live_launcher_reuses_existing_api(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_live_module()
    launched: list[list[str]] = []

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

    def fake_popen(command: list[str], cwd: Path | None = None) -> FakeProcess:
        launched.append(command)
        return FakeProcess(command, cwd=cwd)

    monkeypatch.setattr(module, "api_ready", lambda *_args, **_kwargs: True)
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
        )
    )

    assert rc == 0
    assert len(launched) == 1
    assert launched[0][:4] == ["npm", "--prefix", "forensic-workbench", "run"]


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

    def fake_collect_report_contract(project: str, renderer: str) -> tuple[dict, str]:
        assert project == "demo"
        assert renderer == "decision_brief"
        return (
            {
                "ok": False,
                "status": "blocked",
                "status_reasons": ["synthesis_input_binding_unbound"],
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
            },
            "make synth-contract PROJECT=demo RENDERER=decision_brief",
        )

    monkeypatch.setattr(module.snapshot, "collect_report_contract", fake_collect_report_contract)

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
    assert payload["report_support_contract"] == "projects/demo/synthesis/report_support_contract.json"


def test_source_action_payload_uses_bounded_source_index_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    project_root.mkdir(parents=True)
    intake = project_root / "demo_intake.json"
    intake.write_text(json.dumps({"project": "demo", "bounded_claim": "demo"}), encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
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
        else:
            source_index = workspace / "source_index.json"
            source_index.write_text('{"sources": []}\n', encoding="utf-8")
            payload = {
                "ok": True,
                "status": "fresh",
                "path": str(source_index),
            }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload) + "\n", stderr="")

    monkeypatch.setattr(module.snapshot, "run", fake_run)
    monkeypatch.setattr(module.snapshot, "default_intake_for_project", lambda project: f"projects/{project}/{project}_intake.json")
    monkeypatch.setattr(module, "trace_payload_for_project", lambda **_kwargs: {"readiness": "ready"})
    monkeypatch.setattr(module, "snapshot_payload_for_project", lambda **_kwargs: {"project": "demo", "rows": []})

    payload = module.source_action_payload_for_project(project="demo", action="source_index")
    bind_payload = module.source_action_payload_for_project(project="demo", action="evidence_bind")

    assert payload["schema"] == "ztare-forensic-workbench-source-action-v1"
    assert payload["accepted"] is True
    assert payload["writes"] is True
    assert payload["command"] == "ztare project source-index --project demo --index-only --json"
    assert bind_payload["writes"] is True
    assert bind_payload["command"] == "ztare project evidence-bind --project demo --json"
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
    assert latest["action"] == "evidence_bind"
    assert latest["source_path"] == "projects/demo/evidence.txt"
    assert latest["source_sha256"] == module.hashlib.sha256(b"compiled evidence\n").hexdigest()
    assert len(ledger_rows) == 2
    assert str(tmp_path) not in payload["stdout_tail"]
    assert str(tmp_path) not in json.dumps(payload)
    assert commands == [
        [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "source-index", "--project", "demo", "--index-only", "--json"],
        [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "evidence-bind", "--project", "demo", "--json"],
    ]


def test_save_case_file_payload_writes_workspace_artifact_and_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
    monkeypatch.setattr(module.snapshot, "REPO", tmp_path)
    project_root = tmp_path / "projects" / "demo"
    (project_root / "workspace").mkdir(parents=True)
    case_file = {
        "schema": "ztare-forensic-workbench-case-file-v1",
        "project": "demo",
        "rubric": "demo",
        "intake": "projects/demo/demo_intake.json",
        "rows": [{"label": "Bounded claim"}],
        "audit_commands": [{"command": "ztare project source-check --project demo --json"}],
        "command_queue": [{"command": "ztare project source-check --project demo --json"}],
        "recent_receipts": [{"kind": "review"}],
    }

    payload = module.save_case_file_payload(
        project="demo",
        rubric="demo",
        intake="projects/demo/demo_intake.json",
        case_file=case_file,
    )

    assert payload["schema"] == "ztare-forensic-workbench-case-file-write-receipt-v1"
    expected_name = f"{module.case_file_stem('demo', 'projects/demo/demo_intake.json')}.json"
    assert payload["path"] == f"projects/demo/workspace/{expected_name}"
    assert payload["receipt_path"] == "projects/demo/workspace/forensic_workbench_case_files.jsonl"
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_case_file_write.json"
    saved = json.loads((project_root / "workspace" / expected_name).read_text(encoding="utf-8"))
    latest = json.loads((project_root / "workspace" / "forensic_workbench_latest_case_file_write.json").read_text(encoding="utf-8"))
    ledger_rows = (project_root / "workspace" / "forensic_workbench_case_files.jsonl").read_text(encoding="utf-8").splitlines()
    assert saved == {
        **case_file,
        "project_key": "demo::projects/demo/demo_intake.json",
        "case_key": "demo::projects/demo/demo_intake.json",
    }
    assert saved["audit_commands"] == saved["command_queue"]
    assert latest["row_count"] == 1
    assert latest["command_count"] == 1
    assert latest["receipt_count"] == 1
    assert latest["case_file_path"] == payload["path"]
    assert latest["intake"] == "projects/demo/demo_intake.json"
    assert latest["project_key"] == "demo::projects/demo/demo_intake.json"
    assert latest["case_key"] == "demo::projects/demo/demo_intake.json"
    assert len(ledger_rows) == 1


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
    assert review["project_check_label"] == "Report support"
    assert review["project_check_slug"] == "report_export"
    assert review["check_label"] == "Report support"
    assert review["summary"] == "hold report on Report support"
    assert action["action_file_path"] == "projects/demo/workspace/source_readiness_action.json"
    assert action["project_check_label"] == "Source files"
    assert action["project_check_slug"] == "source_readiness"
    assert action["item_label"] == "Source files"
    assert action["item_slug"] == "source_readiness"
    assert action["row_slug"] == "source_readiness"


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
    assert review["display_label"] == "Report support"
    assert review["summary"] == "hold report on Report support"


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
    assert payload["paths"]["next_step"] == "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    assert payload["paths"]["project_check"] == "projects/demo/workspace/forensic_workbench_row_actions.jsonl"
    assert [row["row_slug"] for row in payload["receipts"]] == ["report_export", "legacy_row"]
    assert all(row.get("intake") != "projects/demo/other_intake.json" for row in payload["receipts"])


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


def test_server_status_advertises_real_live_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()
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
    assert payload["workflow_label"] == "Project steps"
    assert payload["project_inventory_scope"] == "all_projects_directory"
    assert payload["inventory_includes_all_project_folders"] is True
    assert payload["project_count"] == 2
    assert payload["intake_ready_count"] == 1
    assert payload["pending_folder_count"] == 1
    assert payload["default_project"] == "demo"
    assert payload["projects"]["project_count"] == 2
    assert payload["projects"]["project_inventory_scope"] == "all_projects_directory"
    assert payload["projects"]["inventory_includes_all_project_folders"] is True
    assert payload["projects"]["pending_folder_count"] == 1
    assert payload["projects"]["folder_summary"]["needs_intake_with_files"] == 1
    assert payload["api"]["project_inventory_scope"] == "all_projects_directory"
    assert payload["api"]["inventory_includes_all_project_folders"] is True
    assert payload["api"]["folder_summary"]["needs_intake_with_files"] == 1
    assert payload["checks"]["api_ready"] is True
    assert payload["checks"]["app_built"] is False
    assert payload["checks"]["snapshot_available"] is False
    assert "papers" not in payload["api"]["file_preview"]["allowed_roots"]
    assert "POST /api/source-edit" in endpoints
    assert "POST /api/source-file" not in endpoints
    assert "GET /api/trace" in endpoints
    assert "GET /api/run-history" in endpoints
    assert "GET /api/evidence-support" in endpoints
    assert "POST /api/run" in endpoints
    assert "POST /api/report-contract" not in endpoints
    assert "POST /api/next-step" in endpoints
    assert "POST /api/item-action" not in endpoints
    assert "POST /api/row-action" not in endpoints
    assert "GET /api/claim-support" in compatibility_endpoints
    assert "POST /api/item-action" in compatibility_endpoints
    assert "POST /api/row-action" in compatibility_endpoints
    project_file_contract = payload["api"]["action_contracts"]["project_file"]
    review_contract = payload["api"]["action_contracts"]["review"]
    next_step_contract = payload["api"]["action_contracts"]["next_step"]
    assert payload["api"]["action_summary"]["read_only_count"] == 6
    assert payload["api"]["action_summary"]["write_without_confirmation_count"] == 10
    assert payload["api"]["action_summary"]["confirmation_required_count"] == 1
    assert "Create project or add intake" in payload["api"]["action_summary"]["write_without_confirmation_actions"]
    assert payload["api"]["file_change_summary"]["read_only_count"] == 6
    assert payload["api"]["file_change_summary"]["write_count"] == 10
    assert payload["api"]["file_change_summary"]["ask_first_count"] == 1
    assert payload["api"]["file_change_summary"]["browser_writes"] is False
    assert "Create project or add intake" in payload["api"]["file_change_summary"]["write_steps"]
    assert payload["api"]["action_contracts"]["project_create"]["label"] == "Create project or add intake"
    assert project_file_contract["behavior"] == "writes files or receipts"
    assert payload["api"]["action_contracts"]["run_preview_and_confirm"]["behavior"] == "asks before writing"
    assert project_file_contract["display_write_path_templates"] == [
        {
            "label": "Project file",
            "path_template": "projects/{project}/workspace/forensic_workbench_case_file_{project_file_digest}.json",
        },
        {
            "label": "Project-file ledger",
            "path_template": "projects/{project}/workspace/forensic_workbench_case_files.jsonl",
        },
        {
            "label": "Latest project-file receipt",
            "path_template": "projects/{project}/workspace/forensic_workbench_latest_case_file_write.json",
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

    assert step["local_step"] == "Run preflight"
    assert step["local_action"] == "Run preflight"
    assert summary["next_step_local_step"] == "Run preflight"
    assert summary["next_step_local_action"] == "Run preflight"


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
    monkeypatch.setattr(module, "read_optional_json_object", lambda path: {})
    monkeypatch.setattr(module, "receipt_history_payload", lambda **kwargs: {"receipts": []})

    payload = module.workflow_payload_for_project(project="demo")

    assert payload["next_step"]["id"] == "prepare_files"
    assert payload["summary"]["next_step_label"] == "Prepare files"
    assert payload["next_step_label"] == "Prepare files"
    assert payload["next_step_detail"] == payload["summary"]["next_step_detail"]
    assert payload["next_step_local_step"] == payload["summary"]["next_step_local_step"]
    steps_by_id = {step["id"]: step for step in payload["steps"]}
    assert steps_by_id["open_project"]["ui_destination"] == {"workspace": "projects", "subsection": "All projects"}
    assert steps_by_id["prepare_files"]["ui_destination"]["subsection"] == "File check"
    assert steps_by_id["review_report"]["ui_destination"]["subsection"] == "Support check"
    assert steps_by_id["preflight"]["write_boundary"]["read_only_actions"] == ["Copy command detail", "Inspect output"]
    assert steps_by_id["project_run"]["write_boundary"]["read_only_actions"] == ["Inspect run plan", "Copy command detail"]


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

    assert detail == "Missing architectural documentation detailing how the recorded change affects the report-support worker."


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
        {"project": "demo", "project_dir": "projects/demo", "status": "case_ready"},
        {"project": "pending", "project_dir": "projects/pending", "status": "needs_intake", "raw_exists": True},
        {"project": "_bench_generated", "project_dir": "projects/_bench_generated", "status": "needs_intake"},
    ]
    monkeypatch.setattr(module.snapshot, "list_project_entries", lambda: entries)
    monkeypatch.setattr(module.snapshot, "list_project_folders", lambda _entries: folders)
    monkeypatch.setattr(module, "intake_payload_for_project", lambda *_args, **_kwargs: {"editable": True, "reference_status": {"summary": {"total": 1, "present": 1}}})

    payload = module.project_index_payload()

    assert payload["ok"] is True
    assert payload["ready_count"] == 1
    assert payload["project_inventory_scope"] == "all_projects_directory"
    assert payload["inventory_root"] == "projects/"
    assert payload["inventory_includes_all_project_folders"] is True
    assert payload["folder_count"] == 3
    assert payload["pending_folder_count"] == 2
    assert payload["folder_summary"] == payload["project_folder_summary"]
    assert payload["project_folder_summary"]["needs_intake"] == 2
    assert payload["project_folder_summary"]["needs_intake_with_files"] == 1
    assert payload["project_folder_summary"]["needs_intake_empty"] == 1
    assert payload["project_folder_summary"]["generated_hidden_by_default"] == 1
    assert payload["projects"][0]["intake_editable"] is True
    assert payload["projects"][0]["intake_ref_summary"] == {"total": 1, "present": 1}
    assert payload["projects"][0]["display_label"] == "Demo"
    assert payload["projects"][0]["status"] == "case_ready"
    assert payload["projects"][0]["project_status"] == "intake_ready"
    assert payload["projects"][0]["status_label"] == "intake ready"
    assert payload["projects"][0]["latest_project_check"] == "projects/demo/workspace/forensic_workbench_latest_row_action.json"
    assert payload["intake_ready_projects"] == payload["projects"]
    assert payload["project_folders_compact"] is True
    assert payload["project_folder_detail_field"] == "all_project_folders"
    assert [row["project"] for row in payload["project_folders"]] == [row["project"] for row in payload["all_project_folders"]]
    assert "raw_preview_files" not in payload["project_folders"][0]
    assert payload["all_project_folders"][0]["openable"] is True
    assert payload["all_project_folders"][0]["project_status"] == "intake_ready"
    assert payload["all_project_folders"][0]["latest_project_check"] == "projects/demo/workspace/forensic_workbench_latest_row_action.json"
    assert payload["project_folders"][0]["latest_project_check"] == "projects/demo/workspace/forensic_workbench_latest_row_action.json"
    assert payload["all_project_folders"][1]["display_label"] == "Pending"
    assert payload["all_project_folders"][1]["project_status"] == "needs_intake"
    assert payload["all_project_folders"][1]["status_label"] == "needs intake"
    assert payload["all_project_folders"][1]["openable"] is False
    assert payload["all_project_folders"][1]["has_case_material"] is True
    assert payload["all_project_folders"][1]["hidden_by_default"] is False
    assert payload["all_project_folders"][2]["hidden_by_default"] is True


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
            (tmp_path / "projects" / "fresh").mkdir(parents=True)
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
        "projects/fresh/fresh_intake.json",
    ]
    assert payload["write_boundary"]["writes_project_files"] is True
    assert payload["write_boundary"]["write_paths"] == payload["created_paths"]
    assert commands[0][:6] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "source-init", "--project"]
    assert commands[1][:6] == [module.snapshot.PYTHON, "-m", "src.ztare.cli", "project", "intake", "create"]
    assert "--source-ref" in commands[1]
    assert "--non-claim" in commands[1]


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
    (tmp_path / "projects" / "existing").mkdir(parents=True)

    def fake_run(command: list[str], *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
        if "source-init" in command:
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
    )

    assert payload["accepted"] is True
    assert payload["created_mode"] == "add_intake"
    assert payload["project_existed_before"] is True
    assert payload["created_paths"] == [
        "projects/existing/raw",
        "projects/existing/workspace",
        "projects/existing/raw/source_type_map.json",
        "projects/existing/existing_intake.json",
    ]


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
    assert source_path.read_text(encoding="utf-8") == f"---\nsource_type: source_evidence\n---\n\n{body}\n"
    assert json.loads((raw / "source_type_map.json").read_text(encoding="utf-8")) == {"source_note.md": "source_evidence"}
    receipt = json.loads(receipt_path.read_text(encoding="utf-8").strip())
    assert receipt["schema"] == "ztare-forensic-workbench-source-import-v1"
    assert receipt["source_path"] == "projects/demo/raw/source_note.md"
    assert receipt["intake"] == "projects/demo/demo_intake.json"
    assert receipt["case_key"] == "demo::projects/demo/demo_intake.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest["source_path"] == "projects/demo/raw/source_note.md"


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
    (raw / "source_note.md").write_text("---\nsource_type: source_evidence\n---\n\nOld body.\n", encoding="utf-8")
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
    assert payload["latest"] == "projects/demo/workspace/forensic_workbench_latest_source_edit.json"
    edited = source_path.read_text(encoding="utf-8")
    assert "source_type: research_question" in edited
    assert "New body." in edited
    assert json.loads((raw / "source_type_map.json").read_text(encoding="utf-8")) == {"source_note.md": "research_question"}
    receipt = json.loads(receipt_path.read_text(encoding="utf-8").strip())
    assert receipt["schema"] == "ztare-forensic-workbench-source-edit-v1"
    assert receipt["source_path"] == "projects/demo/raw/source_note.md"
    assert receipt["source_type"] == "research_question"
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

    with pytest.raises(ValueError, match="no changed fields"):
        module.edit_source_payload(
            project="demo",
            relative_path="source_note.md",
            source_type="source_evidence",
            body="Same body.",
        )

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

    receipt_row = next(row for row in rows if row["label"] == "Latest review receipt")
    assert latest_path == "projects/demo/workspace/forensic_workbench_latest_review.json"
    assert receipt_row["status"] == "applied"
    assert receipt_row["file"] == latest_path
    assert "Report support: hold report" in receipt_row["detail"]


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
