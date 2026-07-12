"""Tests for src/ztare/worldmodel/challenger_portfolio.py.

Coverage:
  - refresh() picks incomparable candidates; excludes strictly dominated ones
  - refresh() writes portfolio.jsonl with correct schema
  - propose_distinguishing_targets() appends executor-schema rows to
    version_space_disagreements.jsonl
  - propose_distinguishing_targets() deduplicates against existing targets
  - sole-privilege: no promote() API exists on the module
  - champion-identical candidate enters portfolio (equal = nondominated)
  - empty inputs: no crash
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ztare.worldmodel import challenger_portfolio as cp


# ── helpers ───────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _plant_champion_materialization(ws: Path, holdout_depth: int = 8) -> None:
    """Plant a champion_materialization.jsonl with promoted entry."""
    score = holdout_depth / 16 if holdout_depth else 0.5
    row = {
        "result": "promoted",
        "schema": "champion_materialization_v1",
        "promoted_sha": "abc123",
        "dominance_receipt": {
            "rank_after": [100, 0, holdout_depth],
        },
        "gate_summary_after": {"gated_sha256": "abc", "harness_ok": True, "score": score},
    }
    _write_jsonl(ws / "champion_materialization.jsonl", [row])


def _plant_vs_ledger(ws: Path, project_dir: Path, visible: int = 100) -> None:
    """Plant version_space.jsonl with test_model entry."""
    _write_jsonl(
        ws / "version_space.jsonl",
        [{
            "schema": "ztare.version_space.v1",
            "candidate_ref": str(project_dir / "test_model.py"),
            "visible_exact": visible,
            "visible_total": visible,
            "status": "admitted",
            "fingerprint": "champ_fp",
        }],
    )
    (project_dir / "test_model.py").write_text("def f(s, a, t): return s\n")


def _plant_specialist(
    ws: Path,
    lane: str,
    candidate_name: str,
    visible_exact: int,
    visible_total: int,
    holdout_depth: int,
    holdout_total: int = 16,
) -> Path:
    """Plant a specialist candidate file and a residual_specialists.jsonl entry."""
    cand_path = ws / "submissions" / candidate_name
    cand_path.parent.mkdir(parents=True, exist_ok=True)
    cand_path.write_text("def f(s, a, t): return s\n")
    row = {
        "_schema": "ztare.residual_specialists.v1",
        "gate_results": {
            lane: {
                "candidate": str(cand_path),
                "visible_exact": visible_exact,
                "visible_total": visible_total,
                "wrong_rows": [],
                "holdout_depth": holdout_depth,
                "holdout_total": holdout_total,
            }
        },
    }
    rs_path = ws / "residual_specialists.jsonl"
    with rs_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return cand_path


# ── tests ──────────────────────────────────────────────────────────────────────


def test_refresh_incomparable_candidate_enters_portfolio(tmp_path):
    """A candidate with worse visible but better holdout than champion is nondominated."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # Champion: visible=1.0 (100/100), holdout=4
    _plant_champion_materialization(ws, holdout_depth=4)
    _plant_vs_ledger(ws, tmp_path, visible=100)
    # Challenger: visible=0.8 (80/100), holdout=8 → incomparable (better holdout)
    _plant_specialist(ws, "lane_a", "challenger_a.py",
                      visible_exact=80, visible_total=100,
                      holdout_depth=8, holdout_total=16)
    portfolio = cp.refresh(tmp_path)
    refs = [Path(m["candidate_ref"]).name for m in portfolio]
    assert "challenger_a.py" in refs


def test_refresh_dominated_candidate_excluded(tmp_path):
    """A strictly dominated candidate (worse visible AND worse holdout) is excluded."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # Champion: visible=1.0, holdout=8
    _plant_champion_materialization(ws, holdout_depth=8)
    _plant_vs_ledger(ws, tmp_path, visible=100)
    # Dominated: visible=0.5, holdout=2 — champion strictly better on BOTH
    _plant_specialist(ws, "lane_b", "dominated.py",
                      visible_exact=50, visible_total=100,
                      holdout_depth=2, holdout_total=16)
    portfolio = cp.refresh(tmp_path)
    refs = [Path(m["candidate_ref"]).name for m in portfolio]
    assert "dominated.py" not in refs


def test_refresh_equal_candidate_enters_portfolio(tmp_path):
    """Equal (same visible fraction, same holdout) is nondominated → enters portfolio."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # Champion: visible=1.0, holdout=4
    _plant_champion_materialization(ws, holdout_depth=4)
    _plant_vs_ledger(ws, tmp_path, visible=100)
    # Equal: same fractions (100/100, holdout=4)
    _plant_specialist(ws, "lane_c", "equal.py",
                      visible_exact=100, visible_total=100,
                      holdout_depth=4, holdout_total=16)
    portfolio = cp.refresh(tmp_path)
    refs = [Path(m["candidate_ref"]).name for m in portfolio]
    assert "equal.py" in refs


def test_refresh_writes_portfolio_jsonl(tmp_path):
    """refresh() writes workspace/challenger_portfolio.jsonl with correct schema."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    _plant_champion_materialization(ws, holdout_depth=4)
    _plant_vs_ledger(ws, tmp_path, visible=100)
    _plant_specialist(ws, "lane_a", "chal.py",
                      visible_exact=80, visible_total=100,
                      holdout_depth=8, holdout_total=16)
    cp.refresh(tmp_path)
    portfolio_path = ws / "challenger_portfolio.jsonl"
    assert portfolio_path.exists()
    rows = [json.loads(l) for l in portfolio_path.read_text().splitlines() if l.strip()]
    assert any(r.get("schema") == "ztare.challenger_portfolio.v1" for r in rows)
    assert any(Path(r.get("candidate_ref", "")).name == "chal.py" for r in rows)


def test_refresh_empty_inputs_no_crash(tmp_path):
    """refresh() returns empty list gracefully when no receipts exist."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = cp.refresh(tmp_path)
    assert result == []
    # portfolio file written but empty
    assert (ws / "challenger_portfolio.jsonl").exists()


def test_sole_privilege_no_promote_api():
    """There is no promote() function on challenger_portfolio (sole-privilege rule)."""
    assert not hasattr(cp, "promote"), (
        "challenger_portfolio must NOT export promote(); "
        "portfolio members never promote — sole privilege is propose_distinguishing_targets"
    )


def test_propose_distinguishing_targets_appends_to_disagreements(tmp_path):
    """propose_distinguishing_targets() appends executor-schema rows to disagreements file."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    # Plant portfolio with one member
    s0 = [[1, 2], [3, 4]]
    s_champ = [[5, 6], [7, 8]]  # champion predicts this
    s_member = [[9, 10], [11, 12]]  # member predicts differently

    # Mock portfolio
    member_ref = str(tmp_path / "workspace" / "submissions" / "chal.py")
    (tmp_path / "workspace" / "submissions").mkdir(exist_ok=True)
    Path(member_ref).write_text("def f(s, a, t): return s\n")

    portfolio_rows = [{
        "schema": "ztare.challenger_portfolio.v1",
        "candidate_ref": member_ref,
        "visible_exact": 80, "visible_total": 100,
        "holdout_depth": 8, "holdout_total": 16,
        "source": "residual_specialists/lane_a",
        "fingerprint": "fp_member",
        "champion_metrics": {"visible_exact": 100, "visible_total": 100,
                             "holdout_depth": 4, "holdout_total": 16},
    }]
    _write_jsonl(ws / "challenger_portfolio.jsonl", portfolio_rows)

    # Plant mock holdout episode
    from ztare.worldmodel.episode_log import EpisodeLog
    ep_dir = tmp_path / "raw" / "episodes"
    ep_dir.mkdir(parents=True)
    holdout_path = ep_dir / "episode_002.jsonl"
    tr_row = {
        "s": s0, "a": 1, "s_next": s_champ, "t": 5,
        "schema": "ztare.episode_log.v1",
    }
    holdout_path.write_text(json.dumps(tr_row) + "\n")

    def fake_resolve(project_dir):
        return {"visible": None, "holdout": holdout_path}

    # Mock predictors: champion returns s_champ, member returns s_member
    def make_champ_predict(s, a, t):
        return tuple(tuple(r) for r in s_champ)

    def make_member_predict(s, a, t):
        return tuple(tuple(r) for r in s_member)

    with (
        patch("ztare.worldmodel.challenger_portfolio.resolve_episode_paths",
              side_effect=fake_resolve),
        patch("ztare.worldmodel.challenger_portfolio._champion_predictor",
              return_value=(make_champ_predict, None)),
        patch("ztare.worldmodel.challenger_portfolio._member_predictor",
              return_value=(make_member_predict, None)),
    ):
        count = cp.propose_distinguishing_targets(tmp_path)

    assert count >= 1
    dis_path = ws / "version_space_disagreements.jsonl"
    assert dis_path.exists()
    rows = [json.loads(l) for l in dis_path.read_text().splitlines() if l.strip()]
    assert any(r.get("schema") == "ztare.vs_disagreements.v1" for r in rows)
    # Check executor schema: disagreement_states with survivor_split
    found = False
    for r in rows:
        for ds in r.get("disagreement_states") or []:
            if ds.get("source") == "challenger_portfolio":
                assert "survivor_split" in ds
                assert len(ds["survivor_split"]) == 2
                found = True
    assert found


def test_propose_distinguishing_targets_dedup(tmp_path):
    """propose_distinguishing_targets() does not append duplicate targets."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    member_ref = str(tmp_path / "workspace" / "submissions" / "chal.py")
    (tmp_path / "workspace" / "submissions").mkdir(exist_ok=True)
    Path(member_ref).write_text("def f(s, a, t): return s\n")

    portfolio_rows = [{
        "schema": "ztare.challenger_portfolio.v1",
        "candidate_ref": member_ref,
        "visible_exact": 80, "visible_total": 100,
        "holdout_depth": 8, "holdout_total": 16,
        "source": "lane_a", "fingerprint": "fp_m",
        "champion_metrics": {"visible_exact": 100, "visible_total": 100,
                             "holdout_depth": 4, "holdout_total": 16},
    }]
    _write_jsonl(ws / "challenger_portfolio.jsonl", portfolio_rows)

    ep_dir = tmp_path / "raw" / "episodes"
    ep_dir.mkdir(parents=True)
    holdout_path = ep_dir / "episode_002.jsonl"
    tr_row = {"s": [[1]], "a": 1, "s_next": [[2]], "t": 0,
               "schema": "ztare.episode_log.v1"}
    holdout_path.write_text(json.dumps(tr_row) + "\n")

    s_champ = ((2,),)
    s_member = ((9,),)

    def fake_resolve(project_dir):
        return {"visible": None, "holdout": holdout_path}

    with (
        patch("ztare.worldmodel.challenger_portfolio.resolve_episode_paths",
              side_effect=fake_resolve),
        patch("ztare.worldmodel.challenger_portfolio._champion_predictor",
              return_value=(lambda s, a, t: s_champ, None)),
        patch("ztare.worldmodel.challenger_portfolio._member_predictor",
              return_value=(lambda s, a, t: s_member, None)),
    ):
        count1 = cp.propose_distinguishing_targets(tmp_path)
        count2 = cp.propose_distinguishing_targets(tmp_path)  # second call should dedup

    assert count1 >= 1
    assert count2 == 0  # all already present


def test_propose_no_crash_empty_portfolio(tmp_path):
    """propose_distinguishing_targets() returns 0 without crashing on empty portfolio."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "challenger_portfolio.jsonl").write_text("")
    result = cp.propose_distinguishing_targets(tmp_path)
    assert result == 0


def test_propose_no_crash_no_holdout(tmp_path):
    """propose_distinguishing_targets() returns 0 when holdout episode is missing."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    member_ref = str(tmp_path / "chal.py")
    Path(member_ref).write_text("def f(s, a, t): return s\n")
    _write_jsonl(ws / "challenger_portfolio.jsonl", [{
        "schema": "ztare.challenger_portfolio.v1",
        "candidate_ref": member_ref,
    }])

    def fake_resolve(project_dir):
        return {"visible": None, "holdout": None}

    with patch("ztare.worldmodel.challenger_portfolio.resolve_episode_paths",
               side_effect=fake_resolve):
        result = cp.propose_distinguishing_targets(tmp_path)
    assert result == 0
