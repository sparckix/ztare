from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from ztare.orchestrator.trace_auditor import (
    check_recurrence,
    check_schema_route_ledger,
    run_audit,
)


REPO = Path(__file__).resolve().parents[1]


def _finding(verdict: str) -> dict:
    return {
        "check_id": "schema_route_ledger",
        "verdict": verdict,
        "witness": {"halt_required": verdict == "anomaly"},
        "note": "fixture",
        "routing_scope": "active_apparatus",
    }


def _append_candidate_event(project: Path, *, event: str, candidate: str) -> None:
    ledger = project / "workspace" / "deterministic_candidate_producer_receipts.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "ztare-deterministic-candidate-producer-receipt-v1",
        "event": event,
        "candidate_sha256": candidate,
        "phase": "checkpoint_identification",
        "producer_id": "fixture",
    }
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def test_schema_route_finding_preserves_blocking_authority(tmp_path):
    project = tmp_path / "project"
    _append_candidate_event(project, event="materialized", candidate="candidate-a")
    finding = check_schema_route_ledger(project)
    assert finding["verdict"] == "anomaly"
    assert finding["witness"]["halt_required"] is True
    assert any(
        row["kind"] == "operational_write_without_downstream_consume"
        for row in finding["witness"]["errors"]
    )


def test_schema_route_finding_clears_after_registered_consume(tmp_path):
    project = tmp_path / "project"
    _append_candidate_event(project, event="materialized", candidate="candidate-a")
    _append_candidate_event(
        project,
        event="consumed_by_project_gate",
        candidate="candidate-a",
    )
    finding = check_schema_route_ledger(project)
    assert finding["verdict"] == "ok"
    assert finding["witness"]["halt_required"] is False


def test_audit_failure_itself_blocks(monkeypatch, tmp_path):
    module = importlib.import_module("ztare.common.schema_routes")

    def fail(_project):
        raise RuntimeError("planted")

    monkeypatch.setattr(module, "audit_project_schema_routes", fail)
    finding = check_schema_route_ledger(tmp_path)
    assert finding["verdict"] == "anomaly"
    assert finding["witness"]["halt_required"] is True


def test_initial_ok_then_anomaly_is_not_recurrence():
    state: dict = {}
    check_recurrence([_finding("ok")], state)
    assert check_recurrence([_finding("anomaly")], state)[0]["recurrence"] is False


def test_anomaly_recovery_anomaly_is_recurrence():
    state: dict = {}
    assert check_recurrence([_finding("anomaly")], state)[0]["recurrence"] is False
    check_recurrence([_finding("ok")], state)
    assert check_recurrence([_finding("anomaly")], state)[0]["recurrence"] is True


def test_legacy_fixed_property_cannot_fabricate_recurrence():
    state = {"fixed_checks": {"schema_route_ledger": True}}
    result = check_recurrence([_finding("anomaly")], state)
    assert result[0]["recurrence"] is False
    assert "fixed_checks" not in state


def test_run_audit_persists_the_route_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("ZTARE_CONJECTURE_RUNG", "0")
    project = tmp_path / "project"
    _append_candidate_event(project, event="materialized", candidate="candidate-a")
    first = run_audit(project)
    assert first["findings"][0]["recurrence"] is False

    _append_candidate_event(
        project,
        event="consumed_by_project_gate",
        candidate="candidate-a",
    )
    assert run_audit(project)["findings"][0]["verdict"] == "ok"

    _append_candidate_event(project, event="materialized", candidate="candidate-b")
    third = run_audit(project)
    assert third["findings"][0]["recurrence"] is True
    state = json.loads(
        (project / "workspace" / "trace_auditor_state.json").read_text()
    )
    assert state["audit_count"] == 3


def test_play_report_result_is_fenced_by_halt_required():
    scripts = REPO / "scripts" / "public" / "control"
    sys.path.insert(0, str(scripts))
    try:
        play_loop = importlib.import_module("arc3_play_loop")
    finally:
        sys.path.remove(str(scripts))
    report = {"result": "task_discharged"}
    active, advisory = play_loop._apply_trace_audit_consequence(
        report,
        {
            "findings": [
                {
                    "check_id": "schema_route_ledger",
                    "verdict": "anomaly",
                    "routing_scope": "active_apparatus",
                    "witness": {"halt_required": True},
                }
            ]
        },
    )
    assert report["result"] == "operational_route_obstruction"
    assert active == ["schema_route_ledger"]
    assert advisory == []
