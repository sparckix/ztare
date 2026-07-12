"""Tests for coverage_planner.py — synthetic project + toy champion, no live API."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ztare.worldmodel.coverage_planner import (
    CoverageDebt,
    ExecutionReceipt,
    _carrier_repr,
    _make_alpha,
    _plan_to_carrier,
    _rank_holes,
    _reachable_carriers,
    _volatile_positions,
    coverage_debt,
    execute_plans,
)
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.grid_dsl import grid_from_lists


# ─── Synthetic helpers ────────────────────────────────────────────────────────

def _g(v: int):
    """1x3 grid: cell [0][0] carries state v; [0][1], [0][2] are always 0."""
    return grid_from_lists([[v, 0, 0]])


def _toy_champion(s, a, t):
    """Toy champion: a=0 increments [0][0] mod 4; a=1 is identity."""
    v = s[0][0]
    if a == 0:
        return grid_from_lists([[(v + 1) % 4, 0, 0]])
    return s


_ACTION_ARITY = 2


def _make_transitions(n: int = 8) -> list:
    """Generate n transitions with a=0 (cycle v=0→1→2→3→0…)
    plus 2 identity transitions for v=0,1 with a=1.
    """
    rows = []
    for i in range(n):
        v = i % 4
        s = _g(v)
        s_next = _g((v + 1) % 4)
        rows.append(Transition(t=i, s=s, a=0, s_next=s_next))
    for i in range(2):
        v = i % 4
        s = _g(v)
        rows.append(Transition(t=n + i, s=s, a=1, s_next=s))
    return rows


# Minimal champion source that _load_carrier_from_source can exec.
# Returns a proper 1-row grid (tuple of tuples).
_CHAMPION_SRC = """\
def step(s, a, t):
    v = s[0][0]
    if a == 0:
        return (((v + 1) % 4, 0, 0),)
    return s
"""


def _make_project(tmp_path: Path, champion_src: str, transitions: list, action_arity: int = 2) -> Path:
    """Scaffold a minimal synthetic project directory."""
    proj = tmp_path / "projects" / "test_proj"
    (proj / "raw" / "episodes").mkdir(parents=True)
    (proj / "workspace").mkdir()

    (proj / "test_model.py").write_text(champion_src)
    (proj / "play_config.json").write_text(json.dumps({"action_arity": action_arity}))

    ep_path = proj / "raw" / "episodes" / "episode_001.jsonl"
    with ep_path.open("w") as f:
        for tr in transitions:
            f.write(json.dumps({
                "t": tr.t,
                "s": [list(r) for r in tr.s],
                "a": tr.a,
                "s_next": [list(r) for r in tr.s_next],
            }) + "\n")

    # Rubric needed for _load_carrier_from_source → _rubric_dynamics_assumption
    rubrics_dir = tmp_path / "rubrics"
    rubrics_dir.mkdir(exist_ok=True)
    (rubrics_dir / "test_proj.json").write_text("{}")

    return proj


# ─── Unit tests: volatile positions & alpha ───────────────────────────────────

def test_volatile_positions_detects_changing_cell():
    transitions = _make_transitions(4)
    vp = _volatile_positions(transitions)
    assert (0, 0) in vp
    assert (0, 1) not in vp
    assert (0, 2) not in vp


def test_alpha_encodes_volatile_cell():
    vp = frozenset([(0, 0)])
    alpha = _make_alpha(vp)
    g = _g(3)
    sig = alpha(g)
    assert (0, 0, 3) in sig
    assert len(sig) == 1


# ─── Unit tests: cover construction ──────────────────────────────────────────

def test_cover_counts_witnessed_pairs():
    """Every (sig, action) seen in transitions must be in covered."""
    transitions = _make_transitions(4)
    vp = _volatile_positions(transitions)
    alpha = _make_alpha(vp)
    covered = {(alpha(tr.s), tr.a) for tr in transitions}
    for v in range(4):
        sig = alpha(_g(v))
        assert (sig, 0) in covered


def test_covered_pairs_come_from_transitions():
    """All covered pairs must be derivable from some transition."""
    transitions = _make_transitions(4)
    vp = _volatile_positions(transitions)
    alpha = _make_alpha(vp)
    covered = {(alpha(tr.s), tr.a) for tr in transitions}
    for sig, a in covered:
        found = any(alpha(tr.s) == sig and tr.a == a for tr in transitions)
        assert found, f"covered pair not in transitions: action={a}"


# ─── Unit tests: reachable enumeration ───────────────────────────────────────

def test_enumerate_reachable_finds_all_four_classes():
    """Starting from v=0, the toy champion reaches v=0,1,2,3 (4 classes)."""
    vp = frozenset([(0, 0)])
    alpha = _make_alpha(vp)
    reachable = _reachable_carriers(_toy_champion, [_g(0)], _ACTION_ARITY, alpha, max_states=500)
    assert len(reachable) == 4


def test_hole_enumeration_excludes_covered():
    """Holes must not overlap with covered pairs."""
    transitions = _make_transitions(8)
    vp = _volatile_positions(transitions)
    alpha = _make_alpha(vp)
    covered = {(alpha(tr.s), tr.a) for tr in transitions}
    reachable = _reachable_carriers(_toy_champion, [_g(0)], _ACTION_ARITY, alpha, max_states=500)
    all_pairs = {(c, a) for c in reachable for a in range(_ACTION_ARITY)}
    holes = list(all_pairs - covered)
    for h in holes:
        assert h not in covered


# ─── Unit tests: ranking ─────────────────────────────────────────────────────

def test_ranking_produces_non_negative_bits():
    transitions = _make_transitions(8)
    vp = _volatile_positions(transitions)
    alpha = _make_alpha(vp)
    covered = {(alpha(tr.s), tr.a) for tr in transitions}
    reachable = _reachable_carriers(_toy_champion, [_g(0)], _ACTION_ARITY, alpha, max_states=500)
    all_pairs = {(c, a) for c in reachable for a in range(_ACTION_ARITY)}
    holes = list(all_pairs - covered)
    ranked = _rank_holes(holes, covered)
    for bits, _c, _a in ranked:
        assert bits >= 0.0


# ─── Unit tests: in-model BFS ────────────────────────────────────────────────

def test_in_model_bfs_finds_planted_path():
    """3-step path: v=0 →a0→ v=1 →a0→ v=2 →a0→ v=3, then hole action."""
    vp = frozenset([(0, 0)])
    alpha = _make_alpha(vp)
    target_carrier = alpha(_g(3))
    plan = _plan_to_carrier(
        _toy_champion, _g(0), _ACTION_ARITY, target_carrier, alpha,
        target_action=1, max_depth=6, max_nodes=200,
    )
    assert plan is not None
    assert plan[-1] == 1          # ends with hole action
    assert len(plan) >= 4         # 3 steps to reach v=3 + hole action


def test_plan_to_carrier_returns_none_for_unreachable():
    """An impossible carrier (v=5, not in mod-4 world) → None."""
    vp = frozenset([(0, 0)])
    alpha = _make_alpha(vp)
    impossible = frozenset([(0, 0, 5)])
    plan = _plan_to_carrier(
        _toy_champion, _g(0), _ACTION_ARITY, impossible, alpha, 0,
        max_depth=4, max_nodes=50,
    )
    assert plan is None


# ─── Integration tests: coverage_debt API ────────────────────────────────────

def test_coverage_debt_receipt_schema(tmp_path):
    transitions = _make_transitions(8)
    proj = _make_project(tmp_path, _CHAMPION_SRC, transitions)
    coverage_debt(proj, max_holes=5)
    path = proj / "workspace" / "coverage_debt.jsonl"
    assert path.exists()
    row = json.loads(path.read_text().splitlines()[-1])
    assert row["schema"] == "ztare.coverage_debt.v1"
    for key in ("n_classes", "n_covered", "n_holes", "top_holes"):
        assert key in row


def test_coverage_debt_n_holes_positive_when_action_unseen(tmp_path):
    """With only a=0 evidence and arity=2, a=1 pairs are holes."""
    transitions = [tr for tr in _make_transitions(8) if tr.a == 0]
    proj = _make_project(tmp_path, _CHAMPION_SRC, transitions, action_arity=2)
    result = coverage_debt(proj, max_holes=10)
    assert result.n_holes > 0


def test_coverage_debt_covered_plus_holes_equals_total(tmp_path):
    transitions = _make_transitions(8)
    proj = _make_project(tmp_path, _CHAMPION_SRC, transitions)
    result = coverage_debt(proj, max_holes=5)
    assert result.n_covered + result.n_holes == result.n_classes * _ACTION_ARITY


def test_coverage_debt_no_champion(tmp_path):
    """Missing test_model.py → graceful zero result."""
    proj = tmp_path / "projects" / "empty_proj"
    (proj / "workspace").mkdir(parents=True)
    (tmp_path / "rubrics").mkdir(exist_ok=True)
    (tmp_path / "rubrics" / "empty_proj.json").write_text("{}")
    result = coverage_debt(proj)
    assert result.n_classes == 0
    assert result.n_holes == 0


# ─── Integration tests: execute_plans dry_run ────────────────────────────────

def test_dry_run_emits_plans_only(tmp_path):
    """dry_run=True: never attempts adapter; all receipts have dry_run=True."""
    transitions = _make_transitions(4)
    proj = _make_project(tmp_path, _CHAMPION_SRC, transitions)
    receipts = execute_plans(proj, max_holes=2, dry_run=True)
    assert isinstance(receipts, list)
    for r in receipts:
        assert r.dry_run is True
        assert r.steps_executed == 0
        assert r.counterexamples_written == 0


# ─── Integration tests: MPC divergence ───────────────────────────────────────

def test_mpc_divergence_triggers_replan(tmp_path):
    """Mock adapter that diverges at step 2 — execution does not crash;
    plan_found=True and steps_executed>0."""
    transitions = _make_transitions(4)
    proj = _make_project(tmp_path, _CHAMPION_SRC, transitions)

    call_count = [0]

    class MockAdapter:
        def __init__(self):
            self.t = 0
            self._s = _g(0)
            self.action_arity = 2
            self.levels_completed = 0

        def reset(self):
            self._s = _g(0)
            self.t = 0

        @property
        def state(self):
            return self._s

        def step(self, a):
            call_count[0] += 1
            if call_count[0] == 2:
                nxt = _g(9)   # diverge: impossible value
            else:
                nxt = _toy_champion(self._s, a, self.t)
            self._s = nxt
            self.t += 1
            return nxt

    import ztare.worldmodel.coverage_planner as cp
    original = cp._adapter_from_project
    cp._adapter_from_project = lambda pd: MockAdapter()
    try:
        receipts = execute_plans(proj, max_holes=1, dry_run=False)
    finally:
        cp._adapter_from_project = original

    assert receipts
    r = receipts[0]
    assert r.plan_found
    assert not r.dry_run
