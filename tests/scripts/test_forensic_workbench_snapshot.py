from __future__ import annotations

import importlib.util
import json
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


def fixture_trace() -> dict:
    return {
        "project": "demo",
        "rubric": "demo",
        "project_dir": "projects/demo",
        "readiness_canonical": "ready_for_in_loop_candidate",
        "project_intake": {
            "status": "valid_packet",
            "bounded_claim": "demo bounded claim",
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
        "Report/export",
        "Latest review receipt",
    }.issubset(labels)
    assert module.validate_rows(rows) == []
    assert all(row["provenance"] for row in rows)
    report_row = next(row for row in rows if row["label"] == "Report/export")
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


def test_snapshot_rows_surface_applied_review_receipt() -> None:
    module = load_module()
    latest_review = {
        "schema": "ztare-forensic-workbench-review-receipt-v1",
        "applied_at": "2026-06-22T00:00:00Z",
        "project": "demo",
        "row": "Report/export",
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
    assert "Report/export: blocked" in receipt_row["detail"]
    assert "evidence_refs=3" in receipt_row["detail"]


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
                "row": "Report/export",
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

    assert "Forensic Workbench Prototype" in rendered
    assert "First Five-Minute Path" in rendered
    assert "data-provenance=" in rendered
    assert "support contract blocks stale reports" in rendered
    assert "synthesis_input_binding_unbound" in rendered


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
    )

    assert payload["snapshot_scope"] == "single_project_read_model"
    assert payload["project_source"] == "projects/demo"
    assert payload["intake"] == "examples/project_packets/demo_intake.json"
    assert payload["intake_source"] == "public_example_intake"
    assert payload["project"] == "demo"


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
    (tmp_path / "projects/no_intake").mkdir()
    (tmp_path / "projects/bad/project").mkdir(parents=True)

    entries = module.list_project_entries()

    assert entries == [
        {
            "project": "demo",
            "rubric": "demo",
            "project_dir": "projects/demo",
            "intake": "projects/demo/demo_intake.json",
            "intake_source": "project_local_intake",
            "latest_review": "",
            "report_contract": "",
        }
    ]


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
            "report_contract": "",
        }
    ]


def test_project_slug_rejects_path_traversal() -> None:
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_project_slug("../private")


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
        "row": "Report/export",
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
            ledger=str(ledger),
            latest=str(latest),
        )
    )

    assert result["ok"] is True
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["decision"] == "blocked"
    assert rows[0]["row_slug"] == "report_export"
    assert json.loads(latest.read_text(encoding="utf-8"))["review_file_sha256"] == rows[0]["review_file_sha256"]


def test_apply_review_payload_writes_same_receipt_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_review_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    review_file = {
        "schema": "ztare-forensic-workbench-review-v1",
        "project": "demo",
        "rubric": "demo",
        "row": "Report/export",
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


def test_review_api_preserves_receipt_when_snapshot_refresh_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_server_module()

    def fake_apply_review_payload(
        payload: dict,
        *,
        project: str,
        row: str,
        review_file_path: str,
    ) -> dict:
        assert payload["schema"] == "ztare-forensic-workbench-review-v1"
        assert project == "demo"
        assert row == "report_export"
        assert review_file_path == "local-api:demo/report_export"
        return {"ok": True, "receipt": {"project": project, "row_slug": row}}

    def fake_snapshot_payload_for_project(*, project: str, **_kwargs: object) -> dict:
        assert project == "demo"
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
                "row_slug": "report_export",
                "review_file": {
                    "schema": "ztare-forensic-workbench-review-v1",
                    "project": "demo",
                    "row": "Report/export",
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
    assert payload["snapshot"] is None
    assert payload["snapshot_error"] == "trace refresh failed"


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
                "row": "Report/export",
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
    assert "Report/export: blocked" in receipt_row["detail"]


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
