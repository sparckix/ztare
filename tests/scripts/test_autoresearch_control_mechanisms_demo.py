from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from ztare.scaffold.source_check import check_source_project
from ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences


REPO = Path(__file__).resolve().parents[2]


def _load_demo_module():
    path = REPO / "scripts" / "public" / "demo" / "autoresearch_control_mechanisms_demo.py"
    spec = importlib.util.spec_from_file_location("autoresearch_control_mechanisms_demo", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row_by_id(report: dict, mechanism_id: str) -> dict:
    return next(row for row in report["rows"] if row["mechanism_id"] == mechanism_id)


def test_control_demo_materializes_project_scoped_optional_mechanism_evidence(tmp_path):
    module = _load_demo_module()
    packet = module.materialize_demo(repo=tmp_path, project="demo_controls")

    assert packet["evidence_kind"] == "controlled_local_replay"
    assert packet["live_llm_calls"] is False
    assert packet["observed_optional_mechanisms"] == {
        "control_followup_policy": "observed",
        "eigenquestion_preflight": "observed",
        "parallel_blitz": "observed",
        "primitive_class_rotation": "observed",
    }
    followup = packet["control_followup_policy"]
    assert followup["observed_block"] is True
    assert followup["decision"]["decision"] == "observe_prior_control_followup"
    assert followup["decision"]["prior_control_kind"] == "parallel_blitz"
    assert packet["hill_climb_control_followup_policy_totals"] == {
        "control_followup_allow_count": 0,
        "control_followup_block_count": 1,
        "control_followup_decision_count": 1,
    }
    assert packet["hill_climb_summary"]["post_control_outcome_totals"][
        "active_control_event_count"
    ] == 1
    assert packet["hill_climb_summary"]["post_control_outcome_totals"][
        "post_control_window_count"
    ] == 1
    assert packet["hill_climb_summary"]["post_control_outcome_totals"][
        "post_control_no_followup_count"
    ] == 0
    assert packet["hill_climb_summary"]["post_control_diagnostic_counts"] == {
        "control_observed_no_success": 1,
    }
    source_index = packet["source_index_checkpoint"]
    assert source_index["llm_calls"] is False
    assert source_index["merge_status"] == "index_only"
    assert source_index["source_count"] == 1
    assert source_index["source_index"] == "projects/demo_controls/workspace/source_index.json"
    project_packet = packet["project_packet"]
    assert project_packet["path"] == "projects/demo_controls/control_demo_packet.json"
    assert project_packet["validation"]["ok"] is True
    assert project_packet["validation"]["source_preflight"]["ok"] is True
    assert project_packet["validation"]["source_preflight"]["source_evidence_count"] == 1
    trace = packet["kernel_entry_trace"]
    assert trace["can_enter_kernel"] is False
    assert trace["readiness"] == "blocked_on_project_surfaces"
    assert trace["allowed_work_modes"] == ["inspection_only", "pre_kernel_project_prep"]
    assert {row["id"] for row in trace["blockers"]} == {"evidence_compile_provenance"}
    assert trace["blockers"][0]["next_command"] == (
        "make evidence-prepare PROJECT=demo_controls MODEL=gemini"
    )
    assert trace["next_commands"][0] == "make evidence-prepare PROJECT=demo_controls MODEL=gemini"

    summary_path = (
        tmp_path
        / "projects"
        / "demo_controls"
        / "workspace"
        / "control_mechanisms_demo_summary.json"
    )
    assert json.loads(summary_path.read_text(encoding="utf-8"))["project"] == "demo_controls"
    source_report = check_source_project(project="demo_controls", repo=tmp_path)
    assert source_report["ok"] is True
    assert source_report["source_evidence_count"] == 1

    report = audit_mechanism_consequences(repo=tmp_path, project="demo_controls")
    assert _row_by_id(report, "control_followup_policy")["evidence_status"] == "observed"
    assert _row_by_id(report, "parallel_blitz")["evidence_status"] == "observed"
    assert _row_by_id(report, "primitive_class_rotation")["evidence_status"] == "observed"
    assert _row_by_id(report, "eigenquestion_preflight")["evidence_status"] == "observed"
