from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from src.ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences


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
        "eigenquestion_preflight": "observed",
        "parallel_blitz": "observed",
        "primitive_class_rotation": "observed",
    }

    summary_path = (
        tmp_path
        / "projects"
        / "demo_controls"
        / "workspace"
        / "control_mechanisms_demo_summary.json"
    )
    assert json.loads(summary_path.read_text(encoding="utf-8"))["project"] == "demo_controls"

    report = audit_mechanism_consequences(repo=tmp_path, project="demo_controls")
    assert _row_by_id(report, "parallel_blitz")["evidence_status"] == "observed"
    assert _row_by_id(report, "primitive_class_rotation")["evidence_status"] == "observed"
    assert _row_by_id(report, "eigenquestion_preflight")["evidence_status"] == "observed"
