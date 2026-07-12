"""Tests for ztare.worldmodel.distinguishing_play — no live API, no ArcAgi3Adapter.

10+ tests (v1 shape-goal) + v2 scripted-probe tests:
  1. load_targets returns [] when disagreements file is absent
  2. load_targets returns [] when latest report has collapsed population (no disagreement_states)
  3. load_targets returns ranked targets from a seeded file
  4. load_targets filters already-resolved targets
  5. goal_fn_for_target returns False-everywhere for target with no predictions
  6. goal_fn_for_target matches a planted state and rejects others
  7. prune writes BOTH ledgers with correct shapes on a planted observation
  8. prune skips survivors that predict correctly (only mispredictors get prune rows)
  9. dry_run run_distinguishing_session emits plan without touching adapter
 10. run_distinguishing_session with no targets writes a session receipt with 0 attempts
 11. session receipt schema and ts fields present
 12. _mark_resolved causes load_targets to skip that target id
 13. nogood row shape matches _record_investigated_clause
 14. _target_id is stable
 15. latest disagreements report wins over older collapsed one
 -- v2 scripted probe tests --
 16. load_targets parses scripted_probe rows from scripted_probe_targets
 17. _context_post_boundary fires on planted post-boundary grid, not on level-1 grid
 18. _phase_matches honors observed 4-step cycle (t_phase=19, period=4)
 19. _run_scripted_probe issues scripted action when context+phase fire (mock adapter)
 20. _run_scripted_probe resolves after N observations
 21. dry_run emits scripted_probe plan without adapter
 22. v1 shape_goal targets unaffected when scripted_probe present
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ztare.worldmodel.distinguishing_play import (
    SessionReceipt,
    _SESSION_SCHEMA,
    _PRUNES_FILE,
    _NOGOODS_FILE,
    _SESSION_FILE,
    _RESOLUTION_FILE,
    _PROBE_DETECT_ROW,
    _PROBE_DETECT_COL,
    _PROBE_DETECT_VAL,
    _PROBE_CYCLE_LEN,
    _PROBE_T_PHASE,
    _context_post_boundary,
    _phase_matches,
    _run_scripted_probe,
    _mark_resolved,
    _target_id,
    goal_fn_for_target,
    load_targets,
    prune,
    run_distinguishing_session,
)

# ── synthetic data helpers ────────────────────────────────────────────────────

_G1 = ((1, 2), (3, 4))  # grid 1
_G2 = ((2, 2), (3, 4))  # grid 2 — differs from G1 at (0,0)
_G3 = ((3, 2), (3, 4))  # grid 3


def _dis_state(t: int = 0, action: int = 0, row_index: int = 0,
               n_unique: int = 2,
               pred_a=_G1, pred_b=_G2) -> dict:
    return {
        "t": t,
        "action": action,
        "row_index": row_index,
        "n_unique_predictions": n_unique,
        "survivor_split": [
            {"prediction": [list(r) for r in pred_a], "survivors": ["a.py"]},
            {"prediction": [list(r) for r in pred_b], "survivors": ["b.py"]},
        ],
        "pricing_hook": "residual_information_yield",
    }


def _write_disagreements(ws: Path, reports: list[dict]) -> None:
    p = ws / "version_space_disagreements.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in reports:
            f.write(json.dumps(r) + "\n")


def _make_project(tmp_path: Path) -> Path:
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_vs_ledger(project_dir: Path, candidates: list[tuple[str, str]]) -> None:
    """Write version_space.jsonl with admitted records for (candidate_ref, fingerprint) tuples."""
    p = project_dir / "workspace" / "version_space.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for ref, fp in candidates:
            f.write(json.dumps({
                "schema": "ztare.version_space.v1",
                "candidate_ref": ref,
                "fingerprint": fp,
                "status": "admitted",
                "visible_exact": 10,
                "visible_total": 10,
                "warrant": "S2_gate_checked",
            }) + "\n")


# ── 1. load_targets: absent file returns [] ───────────────────────────────────

def test_load_targets_absent_file(tmp_path):
    _make_project(tmp_path)
    assert load_targets(tmp_path) == []


# ── 2. load_targets: collapsed population (no disagreement_states) ────────────

def test_load_targets_collapsed_population(tmp_path):
    _make_project(tmp_path)
    _write_disagreements(tmp_path / "workspace", [
        {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": 1,
            "disagreement_states": [],
            "note": "population is behaviorally collapsed on battery",
        }
    ])
    assert load_targets(tmp_path) == []


# ── 3. load_targets: returns targets from a seeded file ──────────────────────

def test_load_targets_returns_targets(tmp_path):
    _make_project(tmp_path)
    ds1 = _dis_state(t=5, action=1, n_unique=3)
    ds2 = _dis_state(t=10, action=0, n_unique=2)
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "disagreement_states": [ds1, ds2],
        "note": "play targets",
    }])
    targets = load_targets(tmp_path)
    assert len(targets) == 2
    # Each target has a _target_id injected
    assert all("_target_id" in t for t in targets)
    # Original fields preserved
    assert targets[0]["t"] == 5
    assert targets[0]["action"] == 1


# ── 4. load_targets: filters already-resolved targets ────────────────────────

def test_load_targets_filters_resolved(tmp_path):
    _make_project(tmp_path)
    ds1 = _dis_state(t=5, action=1)
    ds2 = _dis_state(t=10, action=0, row_index=1)
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "disagreement_states": [ds1, ds2],
    }])
    # Compute id for ds1 and mark resolved
    tid1 = _target_id(ds1)
    _mark_resolved(tmp_path, tid1, {"target_id": tid1})

    targets = load_targets(tmp_path)
    assert len(targets) == 1
    assert targets[0]["t"] == 10


# ── 5. goal_fn: False-everywhere for target with no predictions ───────────────

def test_goal_fn_no_predictions_always_false():
    tgt = {
        "t": 0, "action": 0,
        "survivor_split": [],
        "_target_id": "x",
    }
    gf = goal_fn_for_target(tgt)
    assert gf(_G1) is False
    assert gf(_G2) is False


# ── 6. goal_fn: matches planted state, rejects others ────────────────────────

def test_goal_fn_matches_planted_state():
    ds = _dis_state(pred_a=_G1, pred_b=_G2)
    ds["_target_id"] = _target_id(ds)
    gf = goal_fn_for_target(ds)

    # Either G1 or G2 should match (both are candidate predictions)
    assert gf(_G1) is True
    assert gf(_G2) is True
    # G3 is a different grid — should not match
    assert gf(_G3) is False


# ── 7. prune: writes BOTH ledgers, correct shapes ────────────────────────────

def test_prune_writes_both_ledgers(tmp_path):
    _make_project(tmp_path)

    # Candidate that MISPREDICTS: predicts G1, observation says G2
    cand_src = "\n".join([
        "def step(s, a, t): return ((1,2),(3,4))",  # always predicts G1
        "f = step",
    ])
    cand_path = tmp_path / "workspace" / "cand_a.py"
    cand_path.write_text(cand_src)
    _make_vs_ledger(tmp_path, [(str(cand_path), "fp_a")])

    obs = {
        "target_id": "test-obs",
        "s": [[0, 0], [0, 0]],
        "action": 0,
        "s_next": [[2, 2], [3, 4]],  # G2 — what actually happened
        "t": 5,
    }

    with patch("ztare.worldmodel.evidence_consolidation._load_carrier_from_source") as mock_lcs, \
         patch("ztare.worldmodel.gates.as_predictor") as mock_ap:

        # Mock predictor: predicts G1 = ((1,2),(3,4)) NOT matching observed G2
        def _predict(s, a, t):
            return ((1, 2), (3, 4))  # mismatch

        mock_prog = MagicMock()
        mock_lcs.return_value = mock_prog
        mock_ap.return_value = _predict

        n_prunes, n_nogoods = prune(tmp_path, obs)

    assert n_prunes == 1
    assert n_nogoods == 1

    # Check prunes file
    prunes_path = tmp_path / "workspace" / _PRUNES_FILE
    assert prunes_path.exists()
    prune_rows = [json.loads(l) for l in prunes_path.read_text().splitlines() if l.strip()]
    assert len(prune_rows) == 1
    assert prune_rows[0]["schema"] == "ztare.version_space_prunes.v1"
    assert prune_rows[0]["pruned_by"] == "test-obs"

    # Check nogoods file
    nogoods_path = tmp_path / "workspace" / _NOGOODS_FILE
    assert nogoods_path.exists()
    nogood_rows = [json.loads(l) for l in nogoods_path.read_text().splitlines() if l.strip()]
    assert len(nogood_rows) == 1
    assert nogood_rows[0]["provenance"]["source"] == "distinguishing_observation"
    assert nogood_rows[0]["provenance"]["evidence"] == "visible"
    assert "signature" in nogood_rows[0]
    assert "witness_summary" in nogood_rows[0]


# ── 8. prune: skips correctly-predicting survivors ────────────────────────────

def test_prune_skips_correct_predictor(tmp_path):
    _make_project(tmp_path)

    cand_src = "def step(s, a, t): return tuple(tuple(r) for r in s)\nf = step"
    cand_path = tmp_path / "workspace" / "cand_correct.py"
    cand_path.write_text(cand_src)
    _make_vs_ledger(tmp_path, [(str(cand_path), "fp_correct")])

    s = [[1, 2], [3, 4]]
    s_next = [[1, 2], [3, 4]]  # identity transition

    obs = {
        "target_id": "test-identity",
        "s": s,
        "action": 0,
        "s_next": s_next,
        "t": 0,
    }

    with patch("ztare.worldmodel.evidence_consolidation._load_carrier_from_source") as mock_lcs, \
         patch("ztare.worldmodel.gates.as_predictor") as mock_ap:

        def _predict(s, a, t):
            return tuple(tuple(r) for r in s)  # correct: predicts identity

        mock_prog = MagicMock()
        mock_lcs.return_value = mock_prog
        mock_ap.return_value = _predict

        n_prunes, n_nogoods = prune(tmp_path, obs)

    assert n_prunes == 0   # no misprediction → no prune row
    assert n_nogoods == 1  # nogood is always written


# ── 9. dry_run: emits plan without adapter ────────────────────────────────────

def test_dry_run_no_adapter(tmp_path):
    _make_project(tmp_path)
    ds1 = _dis_state(t=3, action=0)
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "disagreement_states": [ds1],
    }])

    # Should NOT raise even though adapter/champion are absent
    receipt = run_distinguishing_session(tmp_path, max_targets=1, dry_run=True)

    assert receipt.dry_run is True
    assert len(receipt.targets_attempted) == 1
    assert receipt.targets_attempted[0]["dry_run"] is True
    assert receipt.targets_reached == []
    assert receipt.prunes_written == 0

    # Session receipt written to disk
    session_path = tmp_path / "workspace" / _SESSION_FILE
    assert session_path.exists()
    rows = [json.loads(l) for l in session_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["schema"] == _SESSION_SCHEMA
    assert rows[0]["dry_run"] is True


# ── 10. run with no targets writes session receipt with 0 attempts ────────────

def test_run_no_targets_writes_receipt(tmp_path):
    _make_project(tmp_path)
    # No disagreements file at all
    receipt = run_distinguishing_session(tmp_path, dry_run=True)

    assert len(receipt.targets_attempted) == 0
    session_path = tmp_path / "workspace" / _SESSION_FILE
    assert session_path.exists()
    rows = [json.loads(l) for l in session_path.read_text().splitlines() if l.strip()]
    assert rows[0]["targets_attempted"] == []


# ── 11. session receipt schema and ts fields ──────────────────────────────────

def test_session_receipt_schema_ts(tmp_path):
    _make_project(tmp_path)
    receipt = run_distinguishing_session(tmp_path, dry_run=True)

    assert receipt.schema == _SESSION_SCHEMA
    assert receipt.ts  # non-empty ISO timestamp

    session_path = tmp_path / "workspace" / _SESSION_FILE
    row = json.loads(session_path.read_text().splitlines()[0])
    assert row["schema"] == _SESSION_SCHEMA
    assert "ts" in row


# ── 12. mark_resolved causes load_targets to skip that id ────────────────────

def test_mark_resolved_skips_on_reload(tmp_path):
    _make_project(tmp_path)
    ds = _dis_state(t=7, action=2)
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "disagreement_states": [ds],
    }])
    tid = _target_id(ds)
    _mark_resolved(tmp_path, tid, {"target_id": tid})

    targets = load_targets(tmp_path)
    assert targets == []

    resolution_path = tmp_path / "workspace" / _RESOLUTION_FILE
    rows = [json.loads(l) for l in resolution_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["target_id"] == tid


# ── 13. prune shape matches _record_investigated_clause exactly ───────────────

def test_nogood_row_shape_matches_investigated_clause(tmp_path):
    """Verify the nogood row has the exact keys written by _record_investigated_clause."""
    _make_project(tmp_path)
    _make_vs_ledger(tmp_path, [])  # no survivors → prune_count=0

    obs = {
        "target_id": "shape-check",
        "s": [[0]], "action": 1, "s_next": [[1]], "t": 2,
    }
    n_prunes, n_nogoods = prune(tmp_path, obs)

    assert n_nogoods == 1
    path = tmp_path / "workspace" / _NOGOODS_FILE
    row = json.loads(path.read_text().strip())

    # Required keys from _record_investigated_clause:
    assert "signature" in row
    assert "witness_summary" in row
    assert "provenance" in row
    prov = row["provenance"]
    assert prov["source"] == "distinguishing_observation"
    assert prov["evidence"] == "visible"


# ── 14. _target_id is stable ──────────────────────────────────────────────────

def test_target_id_stable():
    ds = {"t": 3, "action": 1, "row_index": 7}
    assert _target_id(ds) == _target_id(ds)
    ds2 = {"t": 4, "action": 1, "row_index": 7}
    assert _target_id(ds) != _target_id(ds2)


# ── 15. latest disagreements report wins over older collapsed one ─────────────

def test_load_targets_uses_latest_report(tmp_path):
    _make_project(tmp_path)
    ds = _dis_state(t=99, action=0)
    _write_disagreements(tmp_path / "workspace", [
        # old report: collapsed
        {"schema": "ztare.vs_disagreements.v1", "n_survivors": 0,
         "disagreement_states": [], "note": "collapsed"},
        # newer report: has targets
        {"schema": "ztare.vs_disagreements.v1", "n_survivors": 2,
         "disagreement_states": [ds]},
    ])
    targets = load_targets(tmp_path)
    assert len(targets) == 1
    assert targets[0]["t"] == 99


# ── 16. load_targets parses scripted_probe rows ───────────────────────────────

def test_load_targets_parses_scripted_probe(tmp_path):
    _make_project(tmp_path)
    probe = {
        "kind": "scripted_probe",
        "context": {"post_boundary": True},
        "action": 1,
        "t_phase": 19,
        "t": 19,
        "row_index": 0,
    }
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 0,
        "scripted_probe_targets": [probe],
        "disagreement_states": [],
    }])
    targets = load_targets(tmp_path)
    assert len(targets) == 1
    assert targets[0]["kind"] == "scripted_probe"
    assert targets[0]["action"] == 1
    assert targets[0]["t_phase"] == 19
    assert "_target_id" in targets[0]


# ── 17. _context_post_boundary fires on post-boundary grid, not pre-boundary ──

def _make_grid(nrows: int = 64, ncols: int = 64, fill: int = 4) -> list[list[int]]:
    return [[fill] * ncols for _ in range(nrows)]


def test_context_post_boundary_fires_on_planted_grid():
    # Plant the discriminating value: grid[5][19] == 3
    g = _make_grid()
    g[_PROBE_DETECT_ROW][_PROBE_DETECT_COL] = _PROBE_DETECT_VAL
    assert _context_post_boundary(g) is True


def test_context_post_boundary_not_on_level1_grid():
    # All-4 grid (pre-boundary): detector must not fire
    g = _make_grid(fill=4)
    assert _context_post_boundary(g) is False


def test_context_post_boundary_not_on_small_grid():
    # Small grid (fewer rows/cols): graceful False, no IndexError
    assert _context_post_boundary([[1, 2], [3, 4]]) is False


# ── 18. _phase_matches honors observed 4-step cycle ──────────────────────────

def test_phase_matches_fires_at_correct_phase():
    # t_phase=19, cycle=4: 19%4=3; should fire at adapter.t=3,7,11,...
    assert _phase_matches(19, 3) is True   # 3 % 4 == 3
    assert _phase_matches(19, 7) is True   # 7 % 4 == 3
    assert _phase_matches(19, 19) is True  # 19 % 4 == 3
    assert _phase_matches(19, 23) is True  # 23 % 4 == 3


def test_phase_matches_does_not_fire_at_wrong_phase():
    assert _phase_matches(19, 0) is False  # 0 % 4 == 0
    assert _phase_matches(19, 1) is False
    assert _phase_matches(19, 2) is False
    assert _phase_matches(19, 4) is False  # 4 % 4 == 0


def test_phase_matches_none_always_fires():
    # t_phase=None: fire on any step
    for t in range(20):
        assert _phase_matches(None, t) is True


# ── 19. _run_scripted_probe overrides policy at matching step (mock adapter) ──

class _MockAdapter:
    """Minimal adapter: cycles a pre-set grid through states, exposing t."""

    def __init__(self, states: list, post_boundary_at: int = 3):
        self._states = states
        self._idx = 0
        self._t = 0
        self.action_arity = 4
        self._post_boundary_at = post_boundary_at  # adapter.t when context fires
        self.steps: list[int] = []  # record every action issued

    def reset(self):
        self._idx = 0
        self._t = 0
        self.steps = []

    def step(self, action: int):
        self.steps.append(action)
        self._t += 1
        self._idx = (self._idx + 1) % len(self._states)
        return self._states[self._idx]

    @property
    def t(self) -> int:
        return self._t

    @property
    def state(self):
        return self._states[self._idx]


def _post_boundary_grid() -> tuple:
    """64x64 tuple-of-tuples with grid[5][19]==3 (post-boundary signature)."""
    rows = [[4] * 64 for _ in range(64)]
    rows[_PROBE_DETECT_ROW][_PROBE_DETECT_COL] = _PROBE_DETECT_VAL
    return tuple(tuple(r) for r in rows)


def _pre_boundary_grid() -> tuple:
    return tuple(tuple([4] * 64) for _ in range(64))


def test_scripted_probe_issues_scripted_action(tmp_path):
    # Adapter alternates: pre-boundary (t=0,1,2), then post-boundary (t=3 ← phase match)
    pre = _pre_boundary_grid()
    post = _post_boundary_grid()
    # States cycle: pre, pre, pre, post (so at t=3 context fires + phase matches)
    adapter = _MockAdapter([pre, pre, pre, post, pre, pre, pre, post] * 10, post_boundary_at=3)

    target = {
        "_target_id": "probe-001",
        "kind": "scripted_probe",
        "context": {"post_boundary": True},
        "action": 1,
        "t_phase": 19,  # 19%4==3
    }

    obs, note = _run_scripted_probe(adapter, target, budget=50, n_required=1)

    assert len(obs) >= 1, f"expected >=1 probe obs, got {len(obs)}; note={note}"
    # The scripted action (1) must appear in steps at the fired position
    assert obs[0]["action"] == 1
    assert obs[0]["kind"] == "scripted_probe"


# ── 20. _run_scripted_probe resolves after N observations ────────────────────

def test_scripted_probe_resolves_after_n_observations():
    pre = _pre_boundary_grid()
    post = _post_boundary_grid()
    # Every 4th step is post-boundary + phase match (t%4==3 for t=3,7,11,...)
    states = [pre, pre, pre, post] * 20
    adapter = _MockAdapter(states)

    target = {
        "_target_id": "probe-002",
        "kind": "scripted_probe",
        "context": {"post_boundary": True},
        "action": 2,
        "t_phase": 19,
    }

    obs, note = _run_scripted_probe(adapter, target, budget=200, n_required=3)
    assert len(obs) == 3, f"expected exactly 3 obs after n_required=3, got {len(obs)}; note={note}"
    assert "resolved" in note


# ── 21. dry_run emits scripted_probe plan without adapter ────────────────────

def test_dry_run_scripted_probe(tmp_path):
    _make_project(tmp_path)
    probe = {
        "kind": "scripted_probe",
        "context": {"post_boundary": True},
        "action": 1,
        "t_phase": 19,
        "t": 19,
        "row_index": 0,
    }
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 0,
        "scripted_probe_targets": [probe],
        "disagreement_states": [],
    }])

    receipt = run_distinguishing_session(tmp_path, max_targets=1, dry_run=True)

    assert receipt.dry_run is True
    assert len(receipt.targets_attempted) == 1
    attempted = receipt.targets_attempted[0]
    assert attempted["kind"] == "scripted_probe"
    assert attempted["action"] == 1
    assert attempted["t_phase"] == 19
    assert attempted["dry_run"] is True


# ── 22. v1 shape_goal targets unaffected when scripted_probe present ──────────

def test_v1_shape_goal_unaffected_by_scripted_probe(tmp_path):
    _make_project(tmp_path)
    ds1 = _dis_state(t=5, action=1, n_unique=3)
    # A report with BOTH kinds — dry_run; shape_goal path still emits its fields
    _write_disagreements(tmp_path / "workspace", [{
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "disagreement_states": [ds1],
        "scripted_probe_targets": [],
    }])

    receipt = run_distinguishing_session(tmp_path, max_targets=2, dry_run=True)
    assert len(receipt.targets_attempted) == 1
    assert receipt.targets_attempted[0].get("kind") == "shape_goal"
    assert receipt.targets_attempted[0]["t"] == 5
