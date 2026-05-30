"""Unit tests for frontier_state."""
from __future__ import annotations

import pytest


def _force_root(monkeypatch, tmp_path):
    from src.ztare.role_extensions import frontier_state as fs
    monkeypatch.setattr(fs, "STATE_ROOT", tmp_path)


def test_invalid_slug_rejected(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import _validate_slug
    with pytest.raises(ValueError):
        _validate_slug("../etc/passwd")
    with pytest.raises(ValueError):
        _validate_slug("")


def test_load_save_roundtrip(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, save_state, FrontierState,
    )
    s = load_state("test_proj")
    assert s.project_slug == "test_proj"
    assert s.last_iter_observed is None
    s.champion_meaning = "candidate_X"
    save_state(s, history_append={"event": "test_event"})
    s2 = load_state("test_proj")
    assert s2.champion_meaning == "candidate_X"
    assert any(h["event"] == "test_event" for h in s2.history)


def test_increment_obstruction_advances_counter(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, increment_obstruction,
    )
    s = load_state("test_proj")
    n1 = increment_obstruction(s, "route_A", reason="r1")
    s = load_state("test_proj")
    n2 = increment_obstruction(s, "route_A", reason="r2")
    assert n1 == 1
    assert n2 == 2


def test_reset_obstruction_clears_counter(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, increment_obstruction, reset_obstruction,
    )
    s = load_state("test_proj")
    increment_obstruction(s, "route_A")
    s = load_state("test_proj")
    increment_obstruction(s, "route_A")
    s = load_state("test_proj")
    reset_obstruction(s, "route_A")
    s2 = load_state("test_proj")
    assert "route_A" not in s2.obstruction_counters


def test_queue_and_pop_actions(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, queue_action, pop_pending_actions,
    )
    s = load_state("test_proj")
    queue_action(s, {"action_kind": "test_a", "params": {}})
    s = load_state("test_proj")
    queue_action(s, {"action_kind": "test_b", "params": {}})
    s = load_state("test_proj")
    actions = pop_pending_actions(s)
    assert len(actions) == 2
    assert actions[0]["action_kind"] == "test_a"
    s2 = load_state("test_proj")
    assert s2.pending_actions == []


def test_history_capped_at_500(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, save_state,
    )
    s = load_state("test_proj")
    for i in range(550):
        save_state(s, history_append={"event": f"e{i}"})
        s = load_state("test_proj")
    assert len(s.history) == 500
    # Earliest events dropped
    assert s.history[0]["event"] == "e50"


def test_resolve_escape_marks_status(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, add_escape, resolve_escape, EscapeEntry,
    )
    s = load_state("test_proj")
    e = EscapeEntry(escape_id="e1", label="riesz_capacity", proposed_by="cold_shot:gpt5.5", status="open")
    add_escape(s, e)
    s = load_state("test_proj")
    resolve_escape(s, "e1", "refuted", reason="failed discriminator")
    s2 = load_state("test_proj")
    assert s2.active_escapes[0]["status"] == "refuted"
    assert s2.active_escapes[0]["resolved_utc"] is not None


def test_resolve_escape_invalid_verdict_raises(monkeypatch, tmp_path):
    _force_root(monkeypatch, tmp_path)
    from src.ztare.role_extensions.frontier_state import (
        load_state, resolve_escape,
    )
    s = load_state("test_proj")
    with pytest.raises(ValueError):
        resolve_escape(s, "e1", "not_a_real_verdict")
