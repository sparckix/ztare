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
import hashlib
import sys
from pathlib import Path
import pytest

from ztare.validator.core.pre_judge_gate import (
    _dominance_inputs,
    detect_patch_base_regression_preflight,
)
from ztare.validator.core.repair_preflight import (
    patch_base_regression_retry_message,
)


def _write_harness(
    project: Path,
    gates: dict,
    *,
    harness_ok: bool = True,
    score: float = 0.5,
    description_length: int | None = None,
) -> None:
    payload = {
        "harness_ok": harness_ok,
        "score": score,
        "gates": gates,
    }
    if description_length is not None:
        payload.update({
            "description_length": description_length,
            "description_length_unit": "source_token_closure_v1",
        })
    payload = json.dumps(payload)
    body = (
        "import json\n"
        f"print(json.dumps(json.loads({payload!r})))\n"
    )
    (project / "gate_harness.py").write_text(body, encoding="utf-8")


def _champion(
    project: Path,
    *,
    visible_exact_rows: int,
    holdout_depth: int,
    wrong_cells: int = 0,
    description_length: int | None = None,
) -> None:
    (project / "workspace").mkdir(parents=True, exist_ok=True)
    prior = project / "workspace" / "submissions" / "iter_001.py"
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior_source = "def step(grid, action, t):\n    return list(grid)\n"
    prior.write_text(prior_source, encoding="utf-8")
    (project / "workspace" / "candidate_memory.json").write_text(
        json.dumps({
            "schema": "ztare-candidate-memory-v1",
            "records": [{
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/iter_001.py",
                "sha": hashlib.sha256(prior_source.encode("utf-8")).hexdigest(),
                "visible_exact_rows": visible_exact_rows,
                "visible_wrong_cells": wrong_cells,
                "holdout_depth": holdout_depth,
                "gate_score": 0.5,
                "description_length": description_length,
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


def _preflight(
    project: Path,
    candidate: Path,
    *,
    require_strict_improvement: bool = True,
):
    return detect_patch_base_regression_preflight(
        enabled=True, project_dir=project, candidate_path=candidate,
        python_executable=sys.executable,
        require_strict_improvement=require_strict_improvement,
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


def test_companion_artifact_may_tie_behavior_but_not_cross_failed_gate(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(project, visible_exact_rows=6125, holdout_depth=10)
    candidate = _candidate(project)
    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6125, ok=True),
        "holdout_rollout_exact": _holdout_gate(depth=10),
    })

    assert _preflight(
        project,
        candidate,
        require_strict_improvement=False,
    ) is None

    _write_harness(project, {
        "visible_replay_exact": _visible_gate(
            exact_rows=6124,
            wrong_cells=1,
            ok=False,
        ),
        "holdout_rollout_exact": _holdout_gate(depth=10),
    })
    assert _preflight(
        project,
        candidate,
        require_strict_improvement=False,
    ) is not None

    _write_harness(project, {
        "visible_replay_exact": _visible_gate(exact_rows=6126, ok=True),
        "holdout_rollout_exact": _holdout_gate(depth=10),
    })
    assert _preflight(
        project,
        candidate,
        require_strict_improvement=False,
    ) is not None


def test_description_length_breaks_ties_without_blocking_evidence_gain() -> None:
    _, anchor_growth = _dominance_inputs({
        "best_prior_holdout_depth": 4,
        "exact_rows_delta": 1,
        "wrong_cells_delta": -1,
        "holdout_depth_delta": 0,
        "description_length_delta": 8,
    })
    _, compressed_equal_behavior = _dominance_inputs({
        "best_prior_holdout_depth": 4,
        "exact_rows_delta": 0,
        "wrong_cells_delta": 0,
        "holdout_depth_delta": 0,
        "description_length_delta": -8,
    })

    assert anchor_growth is True
    assert compressed_equal_behavior is True


def test_evidence_gain_can_acquire_a_larger_first_expression(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ZTARE_DOMINANCE_PROMOTION", "1")
    project = tmp_path / "p"
    project.mkdir()
    _champion(
        project,
        visible_exact_rows=10,
        holdout_depth=2,
        wrong_cells=1,
        description_length=100,
    )
    candidate = _candidate(project)
    _write_harness(
        project,
        {
            "visible_replay_exact": _visible_gate(exact_rows=11, ok=True),
            "holdout_rollout_exact": _holdout_gate(depth=2, threshold=2),
        },
        description_length=108,
    )

    assert _preflight(project, candidate) is None


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


def test_task_hypothesis_is_kernel_bound_to_current_carrier(tmp_path, monkeypatch):
    from ztare.common import candidate_memory
    from ztare.validator.core.candidate_preflight import (
        task_hypothesis_companion_source,
    )

    project = tmp_path / "p"
    carrier = project / "workspace" / "submissions" / "carrier.py"
    carrier.parent.mkdir(parents=True)
    carrier.write_text(
        "def step(state, action, t):\n    return state\n",
        encoding="utf-8",
    )
    record = {"source_type": "full_survivor"}
    monkeypatch.setattr(
        candidate_memory,
        "best_admissible_candidate_memory_record",
        lambda *_args, **_kwargs: record,
    )
    monkeypatch.setattr(
        candidate_memory,
        "candidate_memory_submission_path",
        lambda *_args, **_kwargs: carrier,
    )

    source = task_hypothesis_companion_source(
        project_dir=project,
        task_source=(
            "def GOAL_PREDICATE(state):\n"
            "    return bool(state)\n"
        ),
    )

    assert "PATCH_BASE" in source
    assert hashlib.sha256(carrier.read_bytes()).hexdigest() in source
    assert "return base_next" in source
    assert "def GOAL_PREDICATE(state)" in source
    from ztare.worldmodel.carrier_loader import load_carrier_from_source

    companion = load_carrier_from_source(
        source,
        project / "companion.py",
        project,
        dynamics_assumption="lawful_time",
    )
    assert companion(((1,),), 0, 3) == ((1,),)

    with pytest.raises(ValueError, match="standalone"):
        task_hypothesis_companion_source(
            project_dir=project,
            task_source=(
                "from test_model import *\n"
                "def GOAL_PREDICATE(state):\n"
                "    return True\n"
            ),
        )
