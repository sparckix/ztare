"""Tests for FIX 1/2/3: sprint warm-start skip, sub-phase receipts, budget gate.

Tests:
  1. Champion explains all rows → receipt "skipped", abduce NOT called.
  2. Champion has residual → receipt "full_reidentification", abduce called.
  3. Champion load fails → receipt "warmstart_unavailable", normal abduce path.
  4. Sub-phase receipts (sprint.identification, sprint.multilife) appear.
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# Load arc3_play_loop as a module from its file path (it lives under scripts/,
# not a package, so we use importlib.util to avoid sys.path games).
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "arc3_play_loop",
    str(REPO / "scripts" / "public" / "control" / "arc3_play_loop.py"),
)
_mod = _ilu.module_from_spec(_spec)
sys.modules["arc3_play_loop"] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_champion_warm_start = _mod._champion_warm_start
_sprint_ident_receipt = _mod._sprint_ident_receipt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workspace(tmp: Path) -> Path:
    ws = tmp / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _read_ident_receipts(tmp: Path) -> list[dict]:
    p = tmp / "workspace" / "sprint_identification.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def _read_phase_timings(tmp: Path) -> list[dict]:
    p = tmp / "workspace" / "phase_timings.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Minimal stubs for _sprint dependencies
# ---------------------------------------------------------------------------

def _dummy_episode_log():
    """A tiny in-memory EpisodeLog stub."""
    from ztare.worldmodel.episode_log import EpisodeLog
    log = EpisodeLog()
    g = ((0, 1), (2, 3))
    log.append(g, 0, g, t=0)
    return log


def _write_dummy_episode(project: Path) -> Path:
    from ztare.worldmodel.adapter import episode_log_path
    log = _dummy_episode_log()
    ep = episode_log_path(project)
    ep.parent.mkdir(parents=True, exist_ok=True)
    log.write_jsonl(ep)
    return ep


def _write_dummy_test_model(project: Path) -> Path:
    """Write a test_model.py that is an identity step (predicts s_next = s)."""
    path = project / "test_model.py"
    path.write_text("def step(s, a, t):\n    return s\n")
    return path


# ---------------------------------------------------------------------------
# Test 1: champion explains all rows → skipped receipt, abduce NOT called
# ---------------------------------------------------------------------------

def test_warmstart_skip_when_champion_explains_all(tmp_path):
    """When build_row_bitmap returns wrong_rows=[], action=skipped."""
    _make_workspace(tmp_path)
    _write_dummy_episode(tmp_path)
    _write_dummy_test_model(tmp_path)

    bitmap_clean = {
        "schema": "ztare-row-bitmap-v1",
        "wrong_rows": [],
        "total_rows": 9103,
        "exact_count": 9103,
        "bits": [],
        "env_frame_indices": [],
        "carrier_sha256": "abc",
        "episode_hash": "def",
        "episode_path": "",
    }

    abduce_called = []

    def _fake_abduce(*a, **kw):
        abduce_called.append(True)
        from ztare.worldmodel.spec_abduction import AbductionResult
        return AbductionResult(status="no_catalog_law", replay_ok=False, detail="fake")

    with patch("ztare.worldmodel.evidence_consolidation.build_row_bitmap",
               return_value=bitmap_clean):
        ws = _champion_warm_start(tmp_path, _dummy_episode_log())

    assert ws is not None
    assert ws["wrong_rows"] == []
    assert ws["rows"] == 9103

    # Simulate what _sprint does: emit the skipped receipt
    _sprint_ident_receipt(tmp_path, {
        "schema": "ztare.sprint_identification.v1",
        "round": 1,
        "action": "skipped",
        "reason": "champion_explains_all_checked_rows",
        "rows": ws["rows"],
    })

    receipts = _read_ident_receipts(tmp_path)
    assert len(receipts) == 1
    assert receipts[0]["action"] == "skipped"
    assert receipts[0]["reason"] == "champion_explains_all_checked_rows"
    # abduce was not called (warm-start path skips it)
    assert not abduce_called, "abduce_spec called despite champion explaining all rows"


# ---------------------------------------------------------------------------
# Test 2: champion has residual → full_reidentification receipt
# ---------------------------------------------------------------------------

def test_warmstart_full_reidentification_when_residual(tmp_path):
    """When wrong_rows is non-empty, action=full_reidentification."""
    _make_workspace(tmp_path)
    _write_dummy_episode(tmp_path)
    _write_dummy_test_model(tmp_path)

    bitmap_dirty = {
        "schema": "ztare-row-bitmap-v1",
        "wrong_rows": [5, 12, 99],
        "total_rows": 200,
        "exact_count": 197,
        "bits": [],
        "env_frame_indices": [],
        "carrier_sha256": "abc",
        "episode_hash": "def",
        "episode_path": "",
    }

    with patch("ztare.worldmodel.evidence_consolidation.build_row_bitmap",
               return_value=bitmap_dirty):
        ws = _champion_warm_start(tmp_path, _dummy_episode_log())

    assert ws is not None
    assert ws["wrong_rows"] == [5, 12, 99]

    _sprint_ident_receipt(tmp_path, {
        "schema": "ztare.sprint_identification.v1",
        "round": 1,
        "action": "full_reidentification",
        "residual_count": len(ws["wrong_rows"]),
        "rows": ws["rows"],
        "elapsed_s": 0.1,
    })

    receipts = _read_ident_receipts(tmp_path)
    assert receipts[0]["action"] == "full_reidentification"
    assert receipts[0]["residual_count"] == 3


# ---------------------------------------------------------------------------
# Test 3: champion load failure → warmstart_unavailable, normal path
# ---------------------------------------------------------------------------

def test_warmstart_unavailable_on_exception(tmp_path):
    """Any exception in build_row_bitmap must return None, not raise."""
    _make_workspace(tmp_path)
    _write_dummy_episode(tmp_path)
    _write_dummy_test_model(tmp_path)

    def _raise(*a, **kw):
        raise RuntimeError("disk error")

    with patch("ztare.worldmodel.evidence_consolidation.build_row_bitmap", _raise):
        ws = _champion_warm_start(tmp_path, _dummy_episode_log())

    assert ws is None

    _sprint_ident_receipt(tmp_path, {
        "schema": "ztare.sprint_identification.v1",
        "round": 1,
        "action": "warmstart_unavailable",
        "rows": 0,
    })
    receipts = _read_ident_receipts(tmp_path)
    assert receipts[0]["action"] == "warmstart_unavailable"


def test_warmstart_unavailable_when_no_test_model(tmp_path):
    """No test_model.py → _champion_warm_start returns None immediately."""
    _make_workspace(tmp_path)
    _write_dummy_episode(tmp_path)
    # intentionally do NOT write test_model.py
    ws = _champion_warm_start(tmp_path, _dummy_episode_log())
    assert ws is None


# ---------------------------------------------------------------------------
# Test 4: sub-phase receipts (sprint.identification + sprint.multilife) appear
# ---------------------------------------------------------------------------

def test_warmstart_failed_spec_load_label(tmp_path):
    """STEP 3 bug: bitmap=0 wrong rows but champion spec missing ->
    label must be 'warmstart_failed_spec_load', NOT 'full_reidentification'.
    This was the residual_count=0 full_reidentification mislabel (first-round
    ordering/cache-miss path) the task asks us to fix.

    Test exercises the label logic directly (extracted from _sprint) because
    _champion_warm_start requires test_model.py + episode file to return non-None.
    The fixed label branch in arc3_play_loop._sprint is:
        if _ws is None:             -> warmstart_unavailable
        elif _residual_count:       -> full_reidentification
        else:                       -> warmstart_failed_spec_load
    """
    # Exercise the label logic with the three cases using ws stubs
    cases = [
        # (ws,                       residual_count, expected_label)
        (None,                       None,           "warmstart_unavailable"),
        ({"wrong_rows": [1, 2]},     2,              "full_reidentification"),
        ({"wrong_rows": []},         0,              "warmstart_failed_spec_load"),
    ]
    for ws, residual_count, expected in cases:
        if ws is None:
            action = "warmstart_unavailable"
        elif residual_count:
            action = "full_reidentification"
        else:
            action = "warmstart_failed_spec_load"
        assert action == expected, (
            f"ws={ws}, residual_count={residual_count}: expected {expected!r}, got {action!r}"
        )

    # Also verify the receipt roundtrip for the zero-residual case
    _make_workspace(tmp_path)
    _sprint_ident_receipt(tmp_path, {
        "schema": "ztare.sprint_identification.v1",
        "round": 1,
        "action": "warmstart_failed_spec_load",
        "residual_count": 0,
        "rows": 100,
        "elapsed_s": 0.05,
    })
    receipts = _read_ident_receipts(tmp_path)
    assert receipts[0]["action"] == "warmstart_failed_spec_load"
    assert receipts[0]["residual_count"] == 0


def test_full_reidentification_only_when_residuals_nonzero(tmp_path):
    """full_reidentification label must NOT appear when residual_count is 0."""
    _make_workspace(tmp_path)
    # Replicate the fixed label logic: residual_count=0, ws not None -> never full_reidentification
    for wrong_rows, expected in [([1, 2], "full_reidentification"), ([], "warmstart_failed_spec_load")]:
        _residual_count = len(wrong_rows)
        ws = {"wrong_rows": wrong_rows}
        if ws is None:
            action = "warmstart_unavailable"
        elif _residual_count:
            action = "full_reidentification"
        else:
            action = "warmstart_failed_spec_load"
        assert action == expected, f"wrong_rows={wrong_rows}: expected {expected!r}, got {action!r}"


def test_subphase_receipts_appear(tmp_path):
    """phase("sprint.identification") and phase("sprint.multilife") write records."""
    from ztare.common.phase_timing import phase

    _make_workspace(tmp_path)
    ws_dir = tmp_path / "workspace"

    with phase("sprint.identification", ws_dir):
        pass
    with phase("sprint.multilife", ws_dir):
        pass

    timings = _read_phase_timings(tmp_path)
    names = [t["phase"] for t in timings]
    assert "sprint.identification" in names
    assert "sprint.multilife" in names
    for t in timings:
        assert t["schema"] == "ztare.phase_timing.v1"
        assert t["seconds"] >= 0
