from __future__ import annotations

from pathlib import Path

from ztare.reports.autoresearch_trace import build_autoresearch_trace
from ztare.scaffold.source_check import check_source_project
from ztare.scaffold.substrate_queue import load_project_packet, validate_project_packet


REPO = Path(__file__).resolve().parents[2]
PROJECT = "ops_root_cause_diagnosis_demo"
RUBRIC = "ops_root_cause_diagnosis_demo"
PACKET = REPO / "projects" / PROJECT / f"{PROJECT}_intake.json"


def test_ops_root_cause_diagnosis_fixture_is_trace_ready() -> None:
    source_report = check_source_project(project=PROJECT, repo=REPO)
    assert source_report["ok"] is True
    assert source_report["source_count"] == 10
    assert source_report["source_evidence_count"] == 10
    assert source_report["untyped_source_count"] == 0

    packet = load_project_packet(PACKET)
    validation = validate_project_packet(
        packet,
        base_dir=PACKET.parent,
        repo_root=REPO,
        require_source_preflight=True,
    )
    assert validation["ok"] is True
    assert validation["errors"] == []

    trace = build_autoresearch_trace(
        project=PROJECT,
        rubric=RUBRIC,
        packet=str(PACKET),
        repo=REPO,
    )

    assert trace["kernel_entry"]["status"] == "ready"
    assert trace["kernel_entry"]["can_enter_kernel"] is True
    assert trace["project_intake"]["status"] == "valid_packet"
    assert trace["surfaces"]["source_index_freshness"]["status"] == "fresh"
    assert trace["surfaces"]["evidence_compile_freshness"]["status"] == "fresh"
    assert trace["surfaces"]["evidence_output_binding"]["status"] == "fresh"
    assert trace["graph_carriers"]
    assert any(
        graph["graph_kind"] == "source_claim_graph"
        and graph["validation"]["ok"] is True
        for graph in trace["graph_carriers"]
    )
    assert trace["readiness_canonical"] in {
        "ready_for_first_in_loop_run",
        "ready_for_in_loop_candidate",
    }
