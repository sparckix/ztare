"""Tests for champion_materialization.materialize_champion_from_memory.

All gate harness calls and dominance functions are patched so tests run
without a real project or episode logs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ztare.validator.core.champion_materialization import (
    materialize_champion_from_memory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path, test_model_src: str = "PROGRAM = None") -> Path:
    """Minimal project layout: test_model.py + workspace/ + submissions/ + gate_harness.py stub."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "test_model.py").write_text(test_model_src)
    (proj / "workspace").mkdir()
    (proj / "workspace" / "submissions").mkdir()
    (proj / "gate_harness.py").write_text("# stub")
    return proj


def _cand(project_dir: Path, name: str, src: str = "PROGRAM = None") -> Path:
    p = project_dir / "workspace" / name
    p.write_text(src)
    return p


def _gate_ok(exact: int = 10, wrong: int = 0, holdout: int = 5) -> dict:
    return {
        "harness_ok": True,
        "score": 80,
        "gated_sha256": "abc",
        "gates": [
            {"name": "visible_replay_exact", "tier": "observed", "value": 0, "passed": True},
            {"name": "holdout_rollout_exact", "tier": "heldout", "value": holdout, "threshold": 0, "passed": holdout >= 0},
        ],
        "gates_dict_visible_replay_exact_diagnostics": {},
        # visible_replay_exact diagnostics embedded
        "_diag_exact": exact,
        "_diag_wrong": wrong,
    }


def _live_gate_fail() -> dict:
    """Live gate where visible_replay_exact fails."""
    return {
        "harness_ok": True,
        "score": 0,
        "gated_sha256": "000",
        "gates": [
            {"name": "visible_replay_exact", "tier": "observed", "value": 1, "passed": False},
            {"name": "holdout_rollout_exact", "tier": "heldout", "value": 0, "threshold": 0, "passed": True},
        ],
    }


# Because _rank_key and _dominance_check reach into pre_judge_gate internals,
# we patch them at the champion_materialization module level.

_MODULE = "ztare.validator.core.champion_materialization"


# ---------------------------------------------------------------------------
# Test 1: dominating candidate → promoted
# ---------------------------------------------------------------------------

def test_dominating_candidate_is_promoted(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    cand = _cand(proj, "candidate_good.py", src="PROGRAM = 1")

    monkeypatch.setenv("ZTARE_CHAMPION_MATERIALIZATION", "1")

    dummy_payload = {"harness_ok": True, "score": 80, "gated_sha256": "ff"}

    live_payload = {"harness_ok": True, "score": 0, "gated_sha256": "00"}
    after_payload = {"harness_ok": True, "score": 80, "gated_sha256": "ff"}

    def rank_key_smart(payload):
        # candidate payload has score=80, live has score=0
        return (10, 0, 5) if payload.get("score") == 80 else (5, 0, 3)

    with (
        patch(f"{_MODULE}._collect_candidates", return_value=[cand]),
        patch(f"{_MODULE}._run_harness", return_value=dummy_payload),
        patch(f"{_MODULE}._observed_tier_passes", return_value=True),
        patch(f"{_MODULE}._dominance_check", return_value=True),
        patch(f"{_MODULE}._rank_key", side_effect=rank_key_smart),
        patch(f"{_MODULE}._live_gate_result", side_effect=[live_payload, after_payload]),
    ):
        receipt = materialize_champion_from_memory(proj)

    assert receipt["result"] == "promoted", receipt
    assert (proj / "test_model.py").read_text() == "PROGRAM = 1"
    # backup exists
    backups = list((proj / "workspace").glob("test_model_pre_materialization_*.py"))
    assert backups, "expected backup file"
    # receipt written to jsonl
    ledger = proj / "workspace" / "champion_materialization.jsonl"
    assert ledger.exists()
    rows = [json.loads(l) for l in ledger.read_text().splitlines()]
    assert rows[-1]["result"] == "promoted"


# ---------------------------------------------------------------------------
# Test 2: candidate fails observed gate → NOT promoted
# ---------------------------------------------------------------------------

def test_observed_gate_failure_blocks_promotion(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    cand = _cand(proj, "candidate_bad.py", src="PROGRAM = None")

    monkeypatch.setenv("ZTARE_CHAMPION_MATERIALIZATION", "1")

    with (
        patch(f"{_MODULE}._collect_candidates", return_value=[cand]),
        patch(f"{_MODULE}._run_harness", return_value={"harness_ok": True, "score": 0, "gated_sha256": "aa"}),
        patch(f"{_MODULE}._observed_tier_passes", return_value=False),  # <-- fails
    ):
        receipt = materialize_champion_from_memory(proj)

    assert receipt["result"] == "no_op"
    # test_model unchanged
    assert (proj / "test_model.py").read_text().startswith("PROGRAM")


# ---------------------------------------------------------------------------
# Test 3: heldout-regressing candidate → NOT promoted
# ---------------------------------------------------------------------------

def test_heldout_regression_blocks_promotion(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    cand = _cand(proj, "candidate_regress.py", src="PROGRAM = 2")

    monkeypatch.setenv("ZTARE_CHAMPION_MATERIALIZATION", "1")

    with (
        patch(f"{_MODULE}._collect_candidates", return_value=[cand]),
        patch(f"{_MODULE}._run_harness", return_value={"harness_ok": True, "score": 50, "gated_sha256": "bb"}),
        patch(f"{_MODULE}._observed_tier_passes", return_value=True),
        patch(f"{_MODULE}._dominance_check", return_value=False),  # dominance rejects heldout regression
    ):
        receipt = materialize_champion_from_memory(proj)

    assert receipt["result"] == "no_op"


# ---------------------------------------------------------------------------
# Test 4: nothing better in memory → no-op receipt written
# ---------------------------------------------------------------------------

def test_no_better_candidate_writes_noop_receipt(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    cand = _cand(proj, "candidate_worse.py", src="PROGRAM = 3")

    monkeypatch.setenv("ZTARE_CHAMPION_MATERIALIZATION", "1")

    live_rank = (10, 0, 5)
    cand_rank = (5, 0, 5)  # strictly worse

    with (
        patch(f"{_MODULE}._collect_candidates", return_value=[cand]),
        patch(f"{_MODULE}._run_harness", return_value={"harness_ok": True, "score": 40, "gated_sha256": "cc"}),
        patch(f"{_MODULE}._observed_tier_passes", return_value=True),
        patch(f"{_MODULE}._dominance_check", return_value=True),
        patch(f"{_MODULE}._rank_key", side_effect=lambda p: cand_rank),
        patch(f"{_MODULE}._live_gate_result", return_value={"harness_ok": True, "score": 80, "gated_sha256": "dd"}),
    ):
        # We also need live_rank from _rank_key when called on live_payload
        # The side_effect above returns cand_rank for any call, so we need to distinguish.
        # Easier: patch rank_key to return cand_rank for payload with score=40, live_rank otherwise.
        def rank_key_smart(payload):
            return cand_rank if payload.get("score") == 40 else live_rank

        with patch(f"{_MODULE}._rank_key", side_effect=rank_key_smart):
            receipt = materialize_champion_from_memory(proj)

    assert receipt["result"] == "no_op"
    ledger = proj / "workspace" / "champion_materialization.jsonl"
    assert ledger.exists()
    rows = [json.loads(l) for l in ledger.read_text().splitlines()]
    assert rows[-1]["result"] == "no_op"
    assert "does not strictly dominate" in rows[-1].get("reason", "")


# ---------------------------------------------------------------------------
# Test 5: ZTARE_CHAMPION_MATERIALIZATION=0 → untouched
# ---------------------------------------------------------------------------

def test_env_gate_disables_materialization(tmp_path, monkeypatch):
    proj = _make_project(tmp_path, test_model_src="PROGRAM = 'original'")
    monkeypatch.setenv("ZTARE_CHAMPION_MATERIALIZATION", "0")

    receipt = materialize_champion_from_memory(proj)

    assert receipt["result"] == "disabled"
    # test_model.py not touched
    assert (proj / "test_model.py").read_text() == "PROGRAM = 'original'"
    # no jsonl written
    assert not (proj / "workspace" / "champion_materialization.jsonl").exists()
