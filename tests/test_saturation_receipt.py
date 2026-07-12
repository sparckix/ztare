"""Verify saturation receipt is written exactly once per pursuit (FIX 3)."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


# Minimal stubs for pursue_goal
class _AlwaysSaturatedSweep:
    status = "coverage"
    paths = [[0]]   # non-empty so plan proceeds
    saturated = True
    detail = "stub saturated"


class _FakeAdapter:
    env_id = "test-game-42"
    action_arity = 1
    t = 0
    levels_completed = 0

    def __init__(self):
        self._step = 0

    @property
    def state(self):
        return ((0, 0), (0, 0))

    def step(self, action):
        self._step += 1
        return ((0, 0), (0, 0))


class _FakeChampion:
    pass


def _fake_predict(grid, action, step):
    # predict same state — mismatch will fire after 1 step (real != predicted on next)
    return ((1, 1), (1, 1))  # always mismatch


def test_receipt_written_exactly_once(tmp_path, monkeypatch):
    """Double-saturation: even when sweep saturates on every replan, receipt appears once."""
    # Redirect workspace/ to tmp_path
    monkeypatch.chdir(tmp_path)

    from ztare.worldmodel import planner
    from ztare.worldmodel.gates import as_predictor

    # Patch reachability_sweep to always return saturated coverage
    def fake_sweep(*a, **kw):
        return _AlwaysSaturatedSweep()

    # Patch as_predictor to return our fake predict
    def fake_as_predictor(champ):
        return _fake_predict

    # Patch save_visited / load_visited to no-ops
    def fake_save(path, store):
        pass

    def fake_load(path):
        return set()

    # pursue_goal imports these locally from the reachability module; patch there
    import ztare.worldmodel.reachability as reach_mod
    monkeypatch.setattr(reach_mod, "reachability_sweep", fake_sweep)
    monkeypatch.setattr(reach_mod, "save_visited", fake_save)
    monkeypatch.setattr(reach_mod, "load_visited", fake_load)
    monkeypatch.setattr("ztare.worldmodel.gates.as_predictor", fake_as_predictor)

    adapter = _FakeAdapter()
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))
    visited_store: set = set()

    from ztare.worldmodel.planner import pursue_goal
    result = pursue_goal(
        adapter, _FakeChampion(),
        abstract_fn=abstract_fn,
        visited_store=visited_store,
        max_steps=20,
        max_replans=5,
    )

    receipt_file = tmp_path / "workspace" / "abstraction_saturation.jsonl"
    assert receipt_file.exists(), "receipt file not created"
    lines = [l for l in receipt_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 1, f"expected exactly 1 receipt line, got {len(lines)}: {lines}"

    receipt = json.loads(lines[0])
    assert receipt["schema"] == "ztare-abstraction-saturation-v1"
    assert receipt["game"] == "test-game-42"
    assert isinstance(receipt["visited_store_size"], int)
    assert "ts" in receipt


def test_receipt_not_emitted_without_saturation(tmp_path, monkeypatch):
    """When sweep is not saturated, no receipt file is written."""
    monkeypatch.chdir(tmp_path)

    class _NotSaturatedSweep:
        status = "coverage"
        paths = []
        saturated = False
        detail = "not saturated"

    def fake_sweep(*a, **kw):
        return _NotSaturatedSweep()

    def fake_as_predictor(champ):
        return lambda grid, action, step: ((1, 1), (1, 1))

    monkeypatch.setattr("ztare.worldmodel.planner.reachability_sweep", fake_sweep, raising=False)
    monkeypatch.setattr("ztare.worldmodel.gates.as_predictor", fake_as_predictor)

    adapter = _FakeAdapter()
    abstract_fn = lambda g: frozenset((r, c, v) for r, row in enumerate(g) for c, v in enumerate(row))

    from ztare.worldmodel.planner import pursue_goal
    pursue_goal(adapter, _FakeChampion(), abstract_fn=abstract_fn,
                visited_store=set(), max_steps=5, max_replans=2)

    receipt_file = tmp_path / "workspace" / "abstraction_saturation.jsonl"
    if receipt_file.exists():
        lines = [l for l in receipt_file.read_text().splitlines() if l.strip()]
        assert lines == [], f"unexpected receipt lines: {lines}"
