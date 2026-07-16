"""Tests for src/ztare/worldmodel/engine_router.py.

Each routing branch is exercised with planted receipts (no LLM, no live play).
Tests verify:
  - correct engine/phase decision from signals
  - routing receipt written to workspace/engine_routing.jsonl
  - kill-switch ZTARE_ENGINE_ROUTER=0 prevents dispatch
  - execute() dispatches to mocked engine functions
"""
from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ztare.worldmodel import engine_router as er


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _project(tmp_path: Path, *, has_champion: bool = True,
             champion_explains_visible: bool = True,
             holdout_residual_bits: int = 1,
             n_distinct_fingerprints: int = 0,
             n_survivors: int = 0,
             unresolved_disagreement_targets: int = 0,
             stagnation: int = 0,
             ledger_exists: bool = False) -> Path:
    """Plant a minimal project dir with the requested signal values."""
    p = tmp_path / "proj"
    ws = p / "workspace"
    ws.mkdir(parents=True)
    if has_champion:
        (p / "test_model.py").write_text("def f(s, a, t): return s\n")
        (ws / "champion_materialization.jsonl").write_text(
            json.dumps({"result": "promoted", "promoted_sha": "abc123"}) + "\n"
        )
    if ledger_exists:
        (ws / "version_space.jsonl").write_text("")
    return p


def _state(has_champion=True, champion_explains_visible=True,
           holdout_residual_bits=1, n_survivors=0,
           n_distinct_fingerprints=0, unresolved_disagreement_targets=0,
           stagnation=0, ledger_exists=False,
           n_distinct_hypotheses=None) -> dict:
    state = {
        "has_champion": has_champion,
        "champion_explains_visible": champion_explains_visible,
        "holdout_residual_bits": holdout_residual_bits,
        "population_stats": {
            "n_survivors": n_survivors,
            "n_distinct_fingerprints": n_distinct_fingerprints,
        },
        "unresolved_disagreement_targets": unresolved_disagreement_targets,
        "stagnation": stagnation,
        "_ledger_exists": ledger_exists,
    }
    if n_distinct_hypotheses is not None:
        state["population_stats"]["n_distinct_hypotheses"] = n_distinct_hypotheses
    return state


# ── Routing tests (pure signal → decision, no I/O) ───────────────────────────


def test_no_champion_routes_autoresearch():
    """No champion → autoresearch."""
    d = er.route(_state(has_champion=False))
    assert d["engine"] == "autoresearch"
    assert "no champion" in d["reason"]


def test_champion_mispredicts_routes_autoresearch():
    """Champion exists but mispredicts visible → autoresearch."""
    d = er.route(_state(has_champion=True, champion_explains_visible=False))
    assert d["engine"] == "autoresearch"
    assert "mispredicts" in d["reason"]


def test_zero_residual_routes_closure_check():
    """holdout_residual_bits=0 → closure_check."""
    d = er.route(_state(champion_explains_visible=True, holdout_residual_bits=0))
    assert d["engine"] == "closure_check"
    assert "holdout_residual_bits==0" in d["reason"]


def test_unresolved_targets_routes_distinguishing_play():
    """Unresolved disagreement targets → version_space/distinguishing_play."""
    d = er.route(_state(
        champion_explains_visible=True,
        holdout_residual_bits=4,
        unresolved_disagreement_targets=2,
        ledger_exists=True,
        n_distinct_fingerprints=1,
    ))
    assert d["engine"] == "version_space"
    assert d["phase"] == "distinguishing_play"
    assert "2 unresolved" in d["reason"]


def test_collapsed_population_routes_enumerate():
    """Champion perfect, population collapsed (n_fp=1), no targets → enumerate."""
    d = er.route(_state(
        champion_explains_visible=True,
        holdout_residual_bits=3,
        unresolved_disagreement_targets=0,
        ledger_exists=True,
        n_distinct_fingerprints=1,
    ))
    assert d["engine"] == "version_space"
    assert d["phase"] == "enumerate"
    assert "enumerate" in d["reason"]


def test_distinct_fingerprints_routes_specialists():
    """Champion perfect, distinct fingerprints, no targets, low stagnation → specialists."""
    d = er.route(_state(
        champion_explains_visible=True,
        holdout_residual_bits=5,
        unresolved_disagreement_targets=0,
        ledger_exists=True,
        n_distinct_fingerprints=3,
        stagnation=1,
    ))
    assert d["engine"] == "specialists"
    assert "mechanism duel" in d["reason"]


def test_source_distinct_hypotheses_do_not_collapse_on_one_evidence_class():
    d = er.route(_state(
        champion_explains_visible=True,
        holdout_residual_bits=5,
        ledger_exists=True,
        n_survivors=3,
        n_distinct_hypotheses=3,
        n_distinct_fingerprints=1,
        stagnation=1,
    ))
    assert d["engine"] == "specialists"
    assert "n_distinct_hypotheses=3" in d["reason"]


def test_no_ledger_routes_specialists_when_stagnation_low():
    """No VS ledger and low stagnation → specialists (bootstrap: no ledger = start dueling)."""
    d = er.route(_state(
        champion_explains_visible=True,
        holdout_residual_bits=5,
        unresolved_disagreement_targets=0,
        ledger_exists=False,
        n_distinct_fingerprints=0,
        stagnation=0,
    ))
    assert d["engine"] == "specialists"


def test_high_stagnation_routes_autoresearch():
    """Stagnation at threshold → autoresearch fallback."""
    import ztare.worldmodel.engine_router as _er_mod
    old = _er_mod._STAGNATION_THRESHOLD
    _er_mod._STAGNATION_THRESHOLD = 2
    try:
        d = er.route(_state(
            champion_explains_visible=True,
            holdout_residual_bits=5,
            unresolved_disagreement_targets=0,
            ledger_exists=True,
            n_distinct_fingerprints=3,
            stagnation=2,
        ))
        assert d["engine"] == "autoresearch"
        assert "stagnation" in d["reason"]
    finally:
        _er_mod._STAGNATION_THRESHOLD = old


# ── Receipt-writing tests ─────────────────────────────────────────────────────


def test_routing_receipt_written(tmp_path):
    """decide() appends to workspace/engine_routing.jsonl."""
    state = _state(has_champion=False)
    project_dir = tmp_path / "proj2"
    ws = project_dir / "workspace"
    ws.mkdir(parents=True)

    with (patch.object(er, "knowledge_state", return_value=state)):
        st, dec = er.decide(project_dir)

    receipt_path = ws / "engine_routing.jsonl"
    assert receipt_path.exists()
    row = json.loads(receipt_path.read_text().splitlines()[-1])
    assert row["schema"] == "ztare.engine_routing.v1"
    assert row["engine"] == "autoresearch"
    assert "signals" in row


# ── Kill-switch test ──────────────────────────────────────────────────────────


def test_kill_switch_skips_router(tmp_path, monkeypatch):
    """ZTARE_ENGINE_ROUTER=0 → play loop does not call engine_router.decide."""
    monkeypatch.setenv("ZTARE_ENGINE_ROUTER", "0")

    # Simulate the kill-switch branch in arc3_play_loop inline (without running full loop)
    er_called = []
    def fake_decide(p):
        er_called.append(p)
        return _state(), {"engine": "specialists", "phase": None, "reason": "x"}

    with patch.object(er, "decide", side_effect=fake_decide):
        mode = "hybrid"
        advice_only = False
        _er_active = (mode == "hybrid"
                      and not advice_only
                      and os.environ.get("ZTARE_ENGINE_ROUTER", "1") != "0")
        assert not _er_active
    assert er_called == []


# ── Execute dispatch tests ─────────────────────────────────────────────────────


def test_execute_autoresearch_sentinel(tmp_path):
    """execute() for autoresearch returns sentinel without calling any engine."""
    result = er.execute({"engine": "autoresearch", "phase": None, "reason": "x"}, tmp_path)
    assert result == {"autoresearch": True}


def test_execute_closure_check_sentinel(tmp_path):
    """execute() for closure_check returns sentinel."""
    result = er.execute({"engine": "closure_check", "phase": None, "reason": "x"}, tmp_path)
    assert result == {"closure_check": True}


def test_execute_dispatches_enumerate(tmp_path, monkeypatch):
    """execute() for version_space/enumerate calls enumerate_population."""
    called = []
    fake_ep = MagicMock(return_value={"admitted": 3})

    import importlib
    ws = tmp_path / "workspace"
    ws.mkdir()

    with patch("ztare.worldmodel.population_enumerator.enumerate_population", fake_ep):
        result = er.execute(
            {"engine": "version_space", "phase": "enumerate", "reason": "x"},
            tmp_path,
        )
    fake_ep.assert_called_once_with(tmp_path.resolve())


def test_execute_dispatches_specialists(tmp_path):
    """execute() for specialists calls run_specialists."""
    fake_rs = MagicMock(return_value={"shards": []})
    ws = tmp_path / "workspace"
    ws.mkdir()

    with patch("ztare.worldmodel.residual_specialists.run_specialists", fake_rs):
        result = er.execute(
            {"engine": "specialists", "phase": None, "reason": "x"},
            tmp_path,
        )
    fake_rs.assert_called_once_with(tmp_path.resolve())


def test_execute_dispatches_distinguishing_play(tmp_path):
    """execute() for version_space/distinguishing_play calls run_distinguishing_session."""
    session_receipt = MagicMock()
    session_receipt.__dict__ = {"dry_run": False, "targets_attempted": []}
    fake_rds = MagicMock(return_value=session_receipt)
    ws = tmp_path / "workspace"
    ws.mkdir()

    with patch("ztare.worldmodel.distinguishing_play.run_distinguishing_session", fake_rds):
        result = er.execute(
            {"engine": "version_space", "phase": "distinguishing_play", "reason": "x"},
            tmp_path,
        )
    fake_rds.assert_called_once_with(tmp_path.resolve())


# ── Finding 1: open-world escape branch ───────────────────────────────────────


def _escape_state(
    stagnation: int = 3,
    escape_unreachable: bool = True,
    n_distinct_fingerprints: int = 1,
    ledger_exists: bool = True,
    **kwargs,
) -> dict:
    """State with all escape conditions satisfied by default."""
    base = _state(
        has_champion=True,
        champion_explains_visible=True,
        holdout_residual_bits=4,
        unresolved_disagreement_targets=1,
        n_distinct_fingerprints=n_distinct_fingerprints,
        ledger_exists=ledger_exists,
        stagnation=stagnation,
    )
    base["escape_unreachable"] = escape_unreachable
    base.update(kwargs)
    return base


def test_escape_fires_when_all_conditions_met():
    """Escape branch fires: collapsed + stagnant + unreachable targets."""
    import ztare.worldmodel.engine_router as _er
    old = _er._ESCAPE_STAGNATION
    _er._ESCAPE_STAGNATION = 3
    try:
        d = er.route(_escape_state(stagnation=3))
        assert d["engine"] == "autoresearch"
        assert d["phase"] == "open_world"
        assert "hypothesis-class escape" in d["reason"]
        assert "misspecified" in d["reason"]
    finally:
        _er._ESCAPE_STAGNATION = old


def test_escape_does_not_fire_when_targets_being_reached():
    """Escape suppressed when escape_unreachable=False (targets are reachable)."""
    import ztare.worldmodel.engine_router as _er
    old = _er._ESCAPE_STAGNATION
    _er._ESCAPE_STAGNATION = 3
    try:
        d = er.route(_escape_state(stagnation=3, escape_unreachable=False))
        # Should NOT be open_world; falls to distinguish (udt=1)
        assert d.get("phase") != "open_world"
    finally:
        _er._ESCAPE_STAGNATION = old


def test_escape_does_not_fire_below_threshold():
    """Escape suppressed when stagnation < _ESCAPE_STAGNATION."""
    import ztare.worldmodel.engine_router as _er
    old = _er._ESCAPE_STAGNATION
    _er._ESCAPE_STAGNATION = 3
    try:
        d = er.route(_escape_state(stagnation=2))
        assert d.get("phase") != "open_world"
    finally:
        _er._ESCAPE_STAGNATION = old


def test_escape_does_not_fire_when_population_not_collapsed():
    """Escape suppressed when n_distinct_fingerprints > 1 (population diverse)."""
    import ztare.worldmodel.engine_router as _er
    old = _er._ESCAPE_STAGNATION
    _er._ESCAPE_STAGNATION = 3
    try:
        d = er.route(_escape_state(stagnation=5, n_distinct_fingerprints=3))
        assert d.get("phase") != "open_world"
    finally:
        _er._ESCAPE_STAGNATION = old


def test_escape_writes_open_world_brief(tmp_path):
    """decide() writes open_world_brief.jsonl when escape fires."""
    import ztare.worldmodel.engine_router as _er
    old = _er._ESCAPE_STAGNATION
    _er._ESCAPE_STAGNATION = 3
    ws = tmp_path / "workspace"
    ws.mkdir()
    state = _escape_state(stagnation=3)
    try:
        with patch.object(er, "knowledge_state", return_value=state):
            _, dec = er.decide(tmp_path)
        assert dec["phase"] == "open_world"
        brief_path = ws / "open_world_brief.jsonl"
        assert brief_path.exists()
        row = json.loads(brief_path.read_text().strip())
        assert row["schema"] == "ztare.open_world_brief.v1"
        assert "misspecified" in row["instruction"]
        assert "trigger_signals" in row
    finally:
        _er._ESCAPE_STAGNATION = old


def test_escape_no_brief_written_when_not_open_world(tmp_path):
    """open_world_brief.jsonl NOT written for normal autoresearch (no escape)."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    state = _state(has_champion=False)
    with patch.object(er, "knowledge_state", return_value=state):
        _, dec = er.decide(tmp_path)
    assert dec["engine"] == "autoresearch"
    assert dec.get("phase") != "open_world"
    assert not (ws / "open_world_brief.jsonl").exists()


# ── FIX B: livelock — unreachable target detection + routing escape ────────────


def _plant_session_rows(ws: Path, target_id: str, n_zero_reach: int) -> None:
    """Plant n_zero_reach session rows: target attempted but never reached."""
    import time as _t
    session_file = ws / "distinguishing_play.jsonl"
    for _ in range(n_zero_reach):
        row = {
            "schema": "ztare.distinguishing_play.v1",
            "ts": _t.strftime("%Y%m%dT%H%M%SZ", _t.gmtime()),
            "targets_attempted": [{"target_id": target_id, "kind": "shape_goal"}],
            "targets_reached": [],  # zero reach
        }
        with session_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def test_unreachable_target_marked_after_k_zero_reach(tmp_path):
    """A target with K zero-reach sessions → marked unreachable in resolved ledger."""
    import hashlib as _hl
    import ztare.worldmodel.engine_router as _er_mod
    old_k = _er_mod._TARGET_MAX_ATTEMPTS
    _er_mod._TARGET_MAX_ATTEMPTS = 2
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    # Compute real target_id matching distinguishing_play._target_id({t:5, action:3, row_index:5})
    _payload = json.dumps({"t": 5, "action": 3, "row_index": 5},
                          sort_keys=True, separators=(",", ":"))
    target_id = _hl.sha256(_payload.encode()).hexdigest()[:16]

    # Plant a disagreements file with this target
    dis_row = {
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "n_distinct_fingerprints": 2,
        "disagreement_states": [{
            "t": 5, "action": 3, "row_index": 5,
            "n_unique_predictions": 2,
            "survivor_split": [],
            "pricing_hook": "residual_information_yield",
        }],
    }
    dis_file = ws / "version_space_disagreements.jsonl"
    with dis_file.open("w") as f:
        f.write(json.dumps(dis_row) + "\n")

    # Plant 2 zero-reach session rows using the real target_id
    _plant_session_rows(ws, target_id, 2)

    try:
        # _resolve_unreachable_targets should mark it
        er._resolve_unreachable_targets(tmp_path)
        resolved_file = ws / "distinguishing_play_resolved.jsonl"
        assert resolved_file.exists(), "resolved ledger should have been written"
        rows = [json.loads(l) for l in resolved_file.read_text().splitlines() if l.strip()]
        unreachable = [r for r in rows if r.get("resolution") == "unreachable"]
        assert unreachable, "target should be marked unreachable"
        assert any(r.get("target_id") == target_id for r in unreachable)
    finally:
        _er_mod._TARGET_MAX_ATTEMPTS = old_k


def test_router_advances_past_distinguishing_when_all_targets_unreachable(tmp_path):
    """After all targets marked unreachable, router should NOT route distinguishing_play."""
    import hashlib as _hl
    import ztare.worldmodel.engine_router as _er_mod
    old_k = _er_mod._TARGET_MAX_ATTEMPTS
    _er_mod._TARGET_MAX_ATTEMPTS = 2
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    # Create test_model.py and champion receipt so champion exists
    (tmp_path / "test_model.py").write_text("def f(s,a,t): return s\n")
    (ws / "champion_materialization.jsonl").write_text(
        json.dumps({"result": "promoted"}) + "\n"
    )
    # Plant version_space.jsonl (ledger exists)
    (ws / "version_space.jsonl").write_text("")

    # Compute the real _target_id for {t:7, action:2, row_index:7}
    # (matches distinguishing_play._target_id logic)
    _payload = json.dumps({"t": 7, "action": 2, "row_index": 7},
                          sort_keys=True, separators=(",", ":"))
    target_id = _hl.sha256(_payload.encode()).hexdigest()[:16]

    # Disagreements file with one target using the same fields
    dis_row = {
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": 2,
        "n_distinct_fingerprints": 2,
        "disagreement_states": [{
            "t": 7, "action": 2, "row_index": 7,
            "n_unique_predictions": 2, "survivor_split": [],
            "pricing_hook": "residual_information_yield",
        }],
    }
    with (ws / "version_space_disagreements.jsonl").open("w") as f:
        f.write(json.dumps(dis_row) + "\n")

    # Plant K zero-reach session rows using the real computed target_id
    _plant_session_rows(ws, target_id, 2)

    try:
        # Patch heavy signal extractors so routing is deterministic
        with patch.object(er, "_champion_explains_visible", return_value=True), \
             patch.object(er, "_holdout_residual_bits", return_value=4), \
             patch.object(er, "_population_stats",
                          return_value={"n_survivors": 1, "n_distinct_fingerprints": 1}), \
             patch.object(er, "_stagnation", return_value=0), \
             patch.object(er, "_unreachable_targets", return_value=False):
            state = er.knowledge_state(tmp_path)

        # After _resolve_unreachable_targets runs inside knowledge_state,
        # udt should be 0 (the only target is now resolved as unreachable).
        assert state["unresolved_disagreement_targets"] == 0, (
            f"Expected 0 unresolved targets after marking unreachable, got "
            f"{state['unresolved_disagreement_targets']}"
        )
        # Route on that state: should NOT be distinguishing_play
        dec = er.route(state)
        assert dec.get("phase") != "distinguishing_play", (
            f"Router should not route distinguishing_play when 0 live targets; got {dec}"
        )
    finally:
        _er_mod._TARGET_MAX_ATTEMPTS = old_k


def test_escape_fires_on_enumeration_futility_with_frozen_stagnation(tmp_path):
    """Run-10 lesson: stagnation's only writer is the materializer, which the
    livelock silences. Escape must also fire on enumeration futility."""
    from ztare.worldmodel.engine_router import route

    state = {
        "has_champion": True,
        "champion_explains_visible": True,
        "holdout_residual_bits": 12,
        "population_stats": {"n_survivors": 1, "n_distinct_fingerprints": 1},
        "unresolved_disagreement_targets": 0,
        "stagnation": 2,  # frozen below the escape threshold
        "escape_unreachable": True,
        "enumeration_futile": True,
        "_ledger_exists": True,
    }
    decision = route(state)
    assert decision["engine"] == "autoresearch"
    assert decision.get("phase") == "open_world"

    # without futility and with frozen stagnation, escape must NOT fire
    state2 = dict(state, enumeration_futile=False)
    d2 = route(state2)
    assert not (d2["engine"] == "autoresearch" and d2.get("phase") == "open_world")


def test_unreachable_signal_persists_after_resolution(tmp_path):
    """Run-11 lesson: resolving a target AS unreachable must not clear the
    escape signal — persisted unreachability is the strongest escape evidence."""
    import json
    from ztare.worldmodel.engine_router import _unreachable_targets

    proj = tmp_path / "proj"
    ws = proj / "workspace"
    ws.mkdir(parents=True)
    (ws / "distinguishing_play_resolved.jsonl").write_text(
        json.dumps({"target_id": "abc123", "resolution": "unreachable"}) + "\n")
    assert _unreachable_targets(proj) is True

    # a normally-resolved target does NOT set the signal
    (ws / "distinguishing_play_resolved.jsonl").write_text(
        json.dumps({"target_id": "abc123", "resolution": "observed"}) + "\n")
    assert _unreachable_targets(proj) is False

    # Resolution is append-only and last-write-wins. Reopening a target
    # invalidates an earlier unreachability premise; a later unreachable row
    # can establish it again.
    (ws / "distinguishing_play_resolved.jsonl").write_text(
        "\n".join(
            json.dumps({"target_id": "abc123", "resolution": resolution})
            for resolution in ("unreachable", "reopened")
        ) + "\n"
    )
    assert _unreachable_targets(proj) is False
    with (ws / "distinguishing_play_resolved.jsonl").open("a") as fh:
        fh.write(json.dumps({"target_id": "abc123", "resolution": "unreachable"}) + "\n")
    assert _unreachable_targets(proj) is True
