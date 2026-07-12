"""Dominance-by-evidence-tier promotion (SUBSTRATE-GENERAL).

The champion-freeze bug: promotion required ALL gates to pass, including a
`holdout_rollout_exact` gate scored on a HELD-OUT level whose threshold is full
zero-shot exactness. The reigning champion's own held-out depth is 0, so no
candidate could promote unless it fully solved a level the observed evidence
provably cannot determine. A candidate that strictly improved the observed
surface (6125 vs 5649 visible-exact rows) with held-out 0 == champion's 0 was
killed as `improved_but_gate_failed`.

The fix: gates carry a `tier` ("observed" | "heldout", default "observed").
Observed gates must pass absolutely; heldout gates must merely NOT REGRESS vs
the champion's recorded value. Gated behind ZTARE_DOMINANCE_PROMOTION
(default ON); "0" restores the old all-gates-pass path for A/B.

These fixtures use a synthetic tiered harness (no game-specific logic) plus one
real-artifact assertion against the actual killed arc3_ls20_gov carrier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from ztare.validator.core.pre_judge_gate import detect_patch_base_regression_preflight


def _write_harness(project: Path, gates: dict, *, harness_ok: bool = True, score: float = 0.5) -> None:
    payload = json.dumps({"harness_ok": harness_ok, "score": score, "gates": gates})
    body = (
        "import json\n"
        f"print(json.dumps(json.loads({payload!r})))\n"
    )
    (project / "gate_harness.py").write_text(body, encoding="utf-8")


def _champion(project: Path, *, visible_exact_rows: int, holdout_depth: int, wrong_cells: int = 0) -> None:
    (project / "workspace").mkdir(parents=True, exist_ok=True)
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": "championsha",
                "visible_exact_rows": visible_exact_rows,
                "visible_wrong_cells": wrong_cells,
                "holdout_depth": holdout_depth,
                "gate_score": 0.5,
            }],
        }),
        encoding="utf-8",
    )


def _visible_gate(*, exact_rows: int, ok: bool, tier: str = "observed", wrong_cells: int = 0) -> dict:
    return {
        "name": "visible_replay_exact", "tier": tier,
        "value": 0 if ok else 1, "threshold": 0, "pass": ok,
        "diagnostics": {
            "checked_rows": exact_rows + wrong_cells, "exact_rows": exact_rows,
            "wrong_cell_count": wrong_cells, "first_mismatch": "",
        },
    }


def _holdout_gate(*, depth: int, threshold: int = 10, tier: str = "heldout") -> dict:
    return {
        "name": "holdout_rollout_exact", "tier": tier,
        "value": depth, "threshold": threshold, "pass": depth >= threshold,
    }


def _candidate(project: Path) -> Path:
    candidate = project / "workspace" / "probe.py"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("def step(grid, action, t): return grid\n", encoding="utf-8")
    return candidate


def _preflight(project: Path, candidate: Path):
    return detect_patch_base_regression_preflight(
        enabled=True, project_dir=project, candidate_path=candidate,
        python_executable=sys.executable,
    )


# --- The confirmed-bug case: 6125 vs 5649, holdout 0 == 0 -----------------

def test_improved_visible_tied_holdout_promotes_under_dominance(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=5649, holdout_depth=0)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),
        "holdout_rollout_exact": _holdout_gate(depth=0),
    })
    # None == promotable (no regression receipt blocks the carrier).
    assert _preflight(project, candidate) is None


def test_improved_visible_tied_holdout_killed_when_dominance_off(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "0")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=5649, holdout_depth=0)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),
        "holdout_rollout_exact": _holdout_gate(depth=0),
    })
    # Old all-gates-pass path: holdout gate fails -> blocked. Proves the A/B.
    result = _preflight(project, candidate)
    assert result is not None
    assert result.regression_receipt["candidate_relation"] == "improved_but_gate_failed"


# --- Safety invariant (a): heldout regression is never promoted -----------

def test_heldout_regression_killed_even_with_better_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=5649, holdout_depth=3)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),
        "holdout_rollout_exact": _holdout_gate(depth=1),  # regresses 3 -> 1
    })
    assert _preflight(project, candidate) is not None  # blocked


# --- Safety invariant (b): observed gate failure is never promoted --------

def test_observed_gate_failure_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=5649, holdout_depth=0)
    candidate = _candidate(project)
    _write_harness(project, {
        # visible improved 5649->6125 but the observed gate itself FAILS
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=False),
        "holdout_rollout_exact": _holdout_gate(depth=0),
    })
    assert _preflight(project, candidate) is not None  # blocked


# --- Safety invariant (c): must strictly improve something ----------------

def test_no_strict_improvement_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=6125, holdout_depth=0)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),  # ties champion
        "holdout_rollout_exact": _holdout_gate(depth=0),
    })
    assert _preflight(project, candidate) is not None  # blocked (no strict improve)


# --- Untagged gates default to must-pass (nothing weakens silently) --------

def test_untagged_gate_defaults_to_observed_must_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=5649, holdout_depth=0)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),
        # UNTAGGED failing gate: must behave as observed must-pass -> block.
        "some_other_check": {"name": "some_other_check", "value": 1, "threshold": 0, "pass": False},
        "holdout_rollout_exact": _holdout_gate(depth=0),
    })
    assert _preflight(project, candidate) is not None  # blocked


# --- Real-artifact: the actual killed arc3_ls20_gov 6125 carrier ----------

_REPO = Path(__file__).resolve().parents[2]
_REAL_CARRIER = _REPO / "projects" / "arc3_ls20_gov" / "workspace" / "candidate_boundary_repair.py"
_REAL_HARNESS = _REPO / "projects" / "arc3_ls20_gov" / "gate_harness.py"


@pytest.mark.skipif(not _REAL_CARRIER.exists(), reason="real killed carrier absent")
def test_real_killed_6125_carrier_ab(tmp_path, monkeypatch):
    """Reconstruct the historical block: the real carrier + the real (tagged)
    harness + a 5649/holdout-0 champion. ON -> promotable, OFF -> blocked."""
    project = tmp_path / "arc3_ls20_gov"
    (project / "raw" / "episodes").mkdir(parents=True)
    project.joinpath("gate_harness.py").write_text(_REAL_HARNESS.read_text(), encoding="utf-8")
    # the real harness reads episodes relative to its own dir
    src_ep = _REPO / "projects" / "arc3_ls20_gov" / "raw" / "episodes"
    for name in ("episode_001.jsonl", "episode_002.jsonl"):
        project.joinpath("raw", "episodes", name).write_text(
            (src_ep / name).read_text(), encoding="utf-8")
    candidate = project / "workspace" / "candidate_boundary_repair.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(_REAL_CARRIER.read_text(), encoding="utf-8")
    _champion(project, visible_exact_rows=5649, holdout_depth=0)

    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    assert _preflight(project, candidate) is None, "dominance ON should promote the real 6125 carrier"

    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "0")
    assert _preflight(project, candidate) is not None, "dominance OFF should still block it"
