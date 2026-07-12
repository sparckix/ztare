"""Tests for live_champion provider, candidate memory schema, and briefing_pack staging."""
from __future__ import annotations

import json
import hashlib
import tempfile
from pathlib import Path

import pytest

from ztare.orchestrator.briefing_providers.live_champion import LiveChampionProvider
from ztare.orchestrator.mutator_briefing import BriefingContext, default_briefing


# ── helpers ────────────────────────────────────────────────────────────────

def _make_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    return tmp_path


def _write_receipt(workspace: Path, rows: list[dict]) -> None:
    ledger = workspace / "champion_materialization.jsonl"
    with ledger.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _promoted_receipt(
    from_ref: str = "workspace/submissions/iter_003.py",
    sha: str = "abc123def456",
    score: float = 0.6667,
    rank_after: list = None,
    rank_before: list = None,
    ts: str = "20260710T041051",
) -> dict:
    return {
        "schema": "champion_materialization_v1",
        "result": "promoted",
        "promoted_sha": sha[:16],
        "from_ref": from_ref,
        "backup_ref": "workspace/backup.py",
        "gate_summary_before": {"harness_ok": True, "score": 0.3333},
        "gate_summary_after": {"harness_ok": True, "score": score},
        "dominance_receipt": {
            "rank_before": rank_before or [6088, -148, 0],
            "rank_after": rank_after or [6125, 0, 0],
        },
        "ts": ts,
    }


def _ctx(project: Path) -> BriefingContext:
    return BriefingContext(project_dir=project, iter_index=0, rubric={})


# ── live_champion: promoted receipt ────────────────────────────────────────

def test_live_champion_renders_from_receipt(tmp_path):
    project = _make_project(tmp_path)
    _write_receipt(project / "workspace", [_promoted_receipt()])
    p = LiveChampionProvider(project)
    ctx = _ctx(project)
    assert p.applies(ctx)
    frag = p.fragment(ctx)
    assert "LIVE CHAMPION" in frag or "Live Champion" in frag
    assert "MANDATORY" in frag
    assert "workspace/submissions/iter_003.py" in frag
    assert "6125" in frag  # rank_after
    assert "Authoring from scratch regresses" in frag


def test_live_champion_newest_promoted_wins(tmp_path):
    """Last promoted row in the file is the active champion."""
    project = _make_project(tmp_path)
    _write_receipt(project / "workspace", [
        _promoted_receipt(from_ref="workspace/submissions/old.py", ts="20260710T010000"),
        {"schema": "champion_materialization_v1", "result": "no_op", "ts": "20260710T020000", "reason": "rank tie"},
        _promoted_receipt(from_ref="workspace/submissions/new.py", ts="20260710T030000"),
    ])
    p = LiveChampionProvider(project)
    frag = p.fragment(_ctx(project))
    assert "new.py" in frag
    assert "old.py" not in frag


def test_live_champion_fallback_when_no_promoted_but_test_model_exists(tmp_path):
    """No promoted receipt but test_model.py exists: one-line note."""
    project = _make_project(tmp_path)
    _write_receipt(project / "workspace", [
        {"schema": "champion_materialization_v1", "result": "no_op", "ts": "20260710T010000", "reason": "rank tie"},
    ])
    (project / "test_model.py").write_text("# placeholder\n", encoding="utf-8")
    p = LiveChampionProvider(project)
    ctx = _ctx(project)
    assert p.applies(ctx)
    frag = p.fragment(ctx)
    assert "test_model.py" in frag
    assert "metrics unavailable" in frag


def test_live_champion_silent_when_neither(tmp_path):
    """No receipt, no test_model.py: applies returns False, fragment returns empty."""
    project = _make_project(tmp_path)
    p = LiveChampionProvider(project)
    ctx = _ctx(project)
    assert not p.applies(ctx)
    frag = p.fragment(ctx)
    assert frag == ""


def test_live_champion_structured_records_from_receipt(tmp_path):
    """structured_records returns one record with champion fields."""
    project = _make_project(tmp_path)
    _write_receipt(project / "workspace", [_promoted_receipt(sha="deadbeef1234")])
    p = LiveChampionProvider(project)
    records = p.structured_records(_ctx(project))
    assert len(records) == 1
    r = records[0]
    assert r["provider"] == "live_champion"
    assert r["source_type"] == "live_champion_receipt"
    assert r["result"] == "promoted"
    assert r["from_ref"] == "workspace/submissions/iter_003.py"


def test_live_champion_silent_when_no_jsonl(tmp_path):
    """No champion_materialization.jsonl and no test_model.py: silent omission."""
    project = _make_project(tmp_path)
    p = LiveChampionProvider(project)
    ctx = _ctx(project)
    assert not p.applies(ctx)
    assert p.fragment(ctx) == ""


# ── candidate memory schema: writer stores canonical fields ────────────────

def test_writer_stores_visible_exact_rows_and_holdout_depth(tmp_path):
    """record_candidate_gate_payload writes visible_exact_rows, holdout_depth,
    visible_wrong_cells — the canonical fields _best_prior_candidate_record reads."""
    from ztare.orchestrator.briefing_providers.surviving_candidates import (
        record_candidate_gate_payload,
        _load_records,
    )
    project = _make_project(tmp_path)
    (project / "gate_harness.py").write_text("# stub\n", encoding="utf-8")
    cand = tmp_path / "candidate.py"
    cand.write_text("# candidate\n", encoding="utf-8")
    payload = {
        "score": 0.6667,
        "harness_ok": True,
        "gates": {
            "visible_replay_exact": {
                "pass": False,
                "diagnostics": {
                    "checked_rows": 100,
                    "exact_rows": 80,
                    "wrong_rows": 20,
                    "wrong_cell_count": 5,
                    "first_mismatch": "t=3",
                },
            },
            "holdout_rollout_exact": {
                "pass": False,
                "value": 3,
            },
        },
    }
    record_candidate_gate_payload(
        project_dir=project,
        candidate_path=cand,
        gate_payload=payload,
    )
    records = _load_records(project)
    assert records, "no records written"
    rec = records[0]
    # canonical fields that _best_prior_candidate_record reads:
    assert rec.get("visible_exact_rows") == 80, f"got {rec.get('visible_exact_rows')}"
    assert rec.get("holdout_depth") == 3, f"got {rec.get('holdout_depth')}"
    assert rec.get("visible_wrong_cells") == 5, f"got {rec.get('visible_wrong_cells')}"
    assert rec.get("gate_score") == 0.6667


def test_best_prior_candidate_record_reads_canonical_fields(tmp_path):
    """_best_prior_candidate_record finds the record and returns visible_exact_rows."""
    from ztare.validator.core.pre_judge_gate import _best_prior_candidate_record
    from ztare.orchestrator.briefing_providers.surviving_candidates import (
        record_candidate_gate_payload,
    )
    project = _make_project(tmp_path)
    (project / "gate_harness.py").write_text("# stub\n", encoding="utf-8")
    cand = tmp_path / "workspace" / "submissions" / "iter_001.py"
    cand.parent.mkdir(parents=True)
    # Minimal valid worldmodel carrier source (passes carrier_contract_error check)
    cand.write_text("def step(state, action): return state\n", encoding="utf-8")
    payload = {
        "score": 0.5,
        "harness_ok": True,
        "run_role": "EVALUATION",
        "withheld_refs": [],
        "exposed_refs": [],
        "gates": {
            "visible_replay_exact": {
                "pass": False,
                "diagnostics": {
                    "checked_rows": 50,
                    "exact_rows": 42,
                    "wrong_rows": 8,
                    "wrong_cell_count": 10,
                    "first_mismatch": "t=7",
                },
            },
            "holdout_rollout_exact": {
                "pass": False,
                "value": 0,
            },
        },
    }
    record_candidate_gate_payload(
        project_dir=project,
        candidate_path=cand,
        gate_payload=payload,
    )
    best = _best_prior_candidate_record(project, exclude_sha="000000000000")
    assert best is not None, "no best prior record found"
    assert best.get("visible_exact_rows") == 42


# ── briefing_pack: test_model.py is staged ─────────────────────────────────

def test_briefing_pack_stages_test_model(tmp_path):
    """build_briefing_pack copies test_model.py into the visible workbench."""
    from ztare.common.briefing_pack import build_briefing_pack, BriefingPackRequest
    import os

    repo = tmp_path / "repo"
    project = repo / "projects" / "myproject"
    project.mkdir(parents=True)
    test_model = project / "test_model.py"
    test_model.write_text("# champion\n", encoding="utf-8")

    workbench_root = tmp_path / "wb"
    workbench_root.mkdir()

    prev_root = os.environ.get("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT")
    os.environ["ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT"] = str(workbench_root)
    try:
        pack = build_briefing_pack(BriefingPackRequest(
            repo=repo,
            agent_id="autoresearch_mutator_myproject",
            task="Write a candidate. Return {\"test_model_py\": \"\"}.",
            context="test context",
        ))
    finally:
        if prev_root is None:
            os.environ.pop("ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT", None)
        else:
            os.environ["ZTARE_AGENT_VISIBLE_WORKBENCH_ROOT"] = prev_root

    staged = pack.workbench / "test_model.py"
    assert staged.is_file(), f"test_model.py not staged; workbench contents: {list(pack.workbench.iterdir())}"
    assert staged.read_text(encoding="utf-8") == "# champion\n"


# ── live_champion in default_briefing ──────────────────────────────────────

def test_live_champion_in_default_briefing(tmp_path):
    """default_briefing() includes the live_champion provider."""
    b = default_briefing()
    names = [p.name for p in b.providers]
    assert "live_champion" in names


def test_live_champion_fires_in_full_briefing(tmp_path):
    """live_champion renders in the full briefing when a receipt is present."""
    project = _make_project(tmp_path)
    _write_receipt(project / "workspace", [_promoted_receipt()])
    ctx = BriefingContext(
        project_dir=project,
        iter_index=0,
        rubric={},
        stagnation_count=0,
    )
    b = default_briefing()
    body = b.render(ctx)
    assert "Live Champion" in body or "LIVE CHAMPION" in body or "live_champion" in body.lower()
