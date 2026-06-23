from __future__ import annotations

import hashlib
import json
from ztare.reports import evidence_trace_health as eth
from ztare.reports.evidence_trace_health import build_evidence_trace_fixture
from ztare.reports.evidence_trace_health import build_project_evidence_trace_health
from ztare.scaffold.substrate_queue import build_project_packet, write_project_packet


def _write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_row(project, raw_name: str = "source.md") -> dict:
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


def _valid_rubric() -> dict:
    return {
        "persona": "Adversarial qualitative judge.",
        "rubric_mode": "kepler",
        "fit_score_mode": "none",
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": "qualitative trace fixture",
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": "qualitative trace fixture",
        "farther_tail_region": None,
        "dimensions": [{"name": "Generative Yield", "weight": 100, "description": "yield"}],
        "criteria": {"Generative_Yield": "yield"},
    }


def test_evidence_trace_fixture_proves_carrier_chain():
    report = build_evidence_trace_fixture()

    assert report["all_passed"] is True
    assert report["num_passed"] == report["num_cases"]
    trace = report["trace"]
    assert trace["source_id"] == "S001"
    assert trace["source_type"] == "source_evidence"
    assert trace["confirmed_constraint_count"] == 1
    assert trace["projection_negative_constraints"] == 1
    assert trace["briefing_record_count"] >= 1
    assert trace["graph_carrier_ok"] is True
    assert trace["graph_carrier_errors"] == []
    assert trace["graph_carrier_effect"] == "strategy_change"


def test_project_evidence_trace_health_proves_real_project_chain(tmp_path):
    repo = tmp_path
    project = repo / "projects" / "trace_project"
    workspace = project / "workspace"
    raw = project / "raw"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (project / "project_charter.md").write_text("# Project Charter\n", encoding="utf-8")
    (project / "thesis.md").write_text("# Thesis\n\nBounded claim.\n", encoding="utf-8")
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    evidence = "Evidence packet\n\n- source_id: S001\n"
    (project / "evidence.txt").write_text(evidence, encoding="utf-8")
    source = _source_row(project)
    _write_json(workspace / "workspace_meta.json", {"merge_status": "success", "source_count": 1})
    _write_json(workspace / "source_index.json", {"sources": [source]})
    _write_json(
        project / "compiled_evidence_provenance.json",
        {
            "source_count": 1,
            "sources": [source],
            "output_path": "projects/trace_project/evidence.txt",
            "output_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
        },
    )
    _write_json(
        project / "compiled_evidence_packet.json",
        {
            "project": "trace_project",
            "immutable_ground_truth": [],
            "numerical_ranges_and_constraints": [],
            "identified_contradictions": [],
            "epistemic_voids": [],
            "provenance": [source],
            "candidate_claims_to_test": [
                {
                    "claim": "The trace has source-bound evidence.",
                    "source_ids": ["S001"],
                }
            ],
        },
    )
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [
            {
                "run_id": 1,
                "iteration": 1,
                "score": 10,
                "weakest_point": "needs source-bound follow-up",
                "timestamp": "2026-06-20T00:00:00Z",
            }
        ],
    )
    _write_json(repo / "rubrics" / "trace_project.json", _valid_rubric())
    intake_path = repo / "trace_project_intake.json"
    write_project_packet(
        intake_path,
        build_project_packet(
            project="trace_project",
            rubric="trace_project",
            task="audit the raw-to-evidence trace",
            bounded_claim="the trace has source-bound evidence",
            source_refs=["projects/trace_project/raw/source.md"],
            evidence_refs=["projects/trace_project/evidence.txt"],
            non_claims=["not a domain benchmark"],
            next_falsifier="remove compile provenance and rerun the audit",
            expected_command=(
                "ztare autoresearch route --task 'audit the raw-to-evidence trace' "
                "--project trace_project --rubric trace_project"
            ),
        ),
    )

    report = build_project_evidence_trace_health(
        project="trace_project",
        rubric="trace_project",
        intake=str(intake_path),
        repo=repo,
    )

    assert report["mode"] == "project"
    assert report["all_passed"] is True
    assert report["num_passed"] == report["num_cases"]
    trace = report["trace"]
    assert trace["status"] == "complete_trace"
    assert trace["readiness"] == "ready_for_in_loop_candidate"
    assert trace["source_index_status"] == "fresh"
    assert trace["compile_provenance_status"] == "fresh"
    assert trace["evidence_output_status"] == "fresh"
    assert trace["evidence_readiness"] == {
        "status": "fresh",
        "source_index_status": "fresh",
        "compile_provenance_status": "fresh",
        "evidence_output_status": "fresh",
        "evidence_replay_status": "not_required",
        "evidence_replay_required": False,
        "raw_evidence_replay_status": "missing_manifest",
    }
    assert trace["claim_support"] == {
        "status": "ready",
        "claim_count": 1,
        "weak_or_unsourced_count": 0,
        "source_context_blocked_count": 0,
        "status_counts": {"direct_source_support": 1},
        "source_context_status_counts": {"verified": 1},
    }
    assert trace["constraint_count"] == 1
    assert trace["projection_available"] is True
    assert trace["kernel_entry_can_enter"] is True
    assert trace["route_can_run_now"] is True
    assert any("ztare autoresearch run" in command for command in trace["next_commands"])
    assert not any("make experiment-loop" in command for command in trace["next_commands"])


def test_project_evidence_trace_health_blocks_missing_compile_provenance(tmp_path):
    repo = tmp_path
    project = repo / "projects" / "blocked_trace"
    raw = project / "raw"
    workspace = project / "workspace"
    raw.mkdir(parents=True)
    workspace.mkdir(parents=True)
    (project / "project_charter.md").write_text("# Project Charter\n", encoding="utf-8")
    (project / "thesis.md").write_text("# Thesis\n\nBounded claim.\n", encoding="utf-8")
    (raw / "source.md").write_text(
        "---\nsource_type: source_evidence\n---\nsource claim\n",
        encoding="utf-8",
    )
    (project / "evidence.txt").write_text("Evidence packet\n", encoding="utf-8")
    source = _source_row(project)
    _write_json(workspace / "workspace_meta.json", {"merge_status": "success", "source_count": 1})
    _write_json(workspace / "source_index.json", {"sources": [source]})
    _write_json(workspace / "derived_constraints.json", {"confirmed_constraint_count": 1})
    _write_jsonl(
        workspace / "eval_history.jsonl",
        [{"run_id": 1, "iteration": 1, "score": 5, "weakest_point": "blocked"}],
    )
    _write_json(repo / "rubrics" / "blocked_trace.json", _valid_rubric())

    report = build_project_evidence_trace_health(
        project="blocked_trace",
        rubric="blocked_trace",
        repo=repo,
    )

    assert report["all_passed"] is False
    failed = {row["id"] for row in report["checks"] if not row["passed"]}
    assert "project_trace_complete" in failed
    assert "compile_provenance_fresh" in failed
    assert "kernel_entry_ready" in failed
    assert report["trace"]["status"] == "partial_trace"
    assert "evidence_compile_provenance" in report["trace"]["blocking_missing"]
    assert any(
        row["id"] == "evidence_prepare"
        for row in report["trace"]["recovery_actions"]
    )


def test_project_evidence_trace_health_blocks_stale_evidence_replay(monkeypatch):
    monkeypatch.setattr(
        eth,
        "build_autoresearch_trace",
        lambda **kwargs: {
            "status": "partial_trace",
            "readiness": "blocked_on_project_surfaces",
            "readiness_canonical": "blocked_on_project_surfaces",
            "missing": ["evidence_replay_stale"],
            "blocking_missing": ["evidence_replay_stale"],
            "surfaces": {
                "raw_file_count": 1,
                "source_preflight_ok": True,
                "source_preflight_blocking": [],
                "source_preflight_status": "ready_for_evidence_prepare",
                "confirmed_constraint_count": 1,
                "provisional_constraint_count": 0,
            },
            "carrier_chain": [
                {"surface": "source_index", "status": "fresh"},
                {"surface": "compile_provenance", "status": "fresh"},
                {"surface": "evidence_output", "status": "fresh"},
                {"surface": "evidence_replay", "status": "stale_or_invalid"},
            ],
            "kernel_entry": {"can_enter_kernel": False, "status": "blocked"},
            "route_preview": {"available": True, "can_run_now": False, "source": "intake"},
            "projection": {"available": True, "node_count": 1},
            "next_commands": ["ztare project evidence-replay --project demo --json"],
            "recovery_actions": [],
        },
    )

    report = eth.build_project_evidence_trace_health(project="demo")

    assert report["all_passed"] is False
    failed = {row["id"] for row in report["checks"] if not row["passed"]}
    assert "evidence_readiness_replay_verified_or_not_required" in failed
    assert report["trace"]["evidence_readiness"]["status"] == "blocked"
    assert report["trace"]["evidence_readiness"]["evidence_replay_status"] == (
        "stale_or_invalid"
    )
