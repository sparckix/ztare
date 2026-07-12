"""Tests for the 4 catalog-promotion kill-point fixes (GP-250).

FIX 1 — non-coupling leaf reaches spec-patch branch and gets a real verdict
FIX 2 — accepted card produces a promotion-contract row counted by p0_metrics
         (covered in test_worldmodel_p0_metrics.py::test_path_a_promotion_counted)
FIX 3 — empty-evidence card gets backfilled or receipted no_evidence_yet
FIX 4 — persist_strategy_card_discharges called on gate pass (mock);
         zero-caller list includes the organ
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))


# ── FIX 1: non-coupling leaf routes to spec-patch branch ─────────────────────

def test_non_coupling_leaf_reaches_spec_patch_branch(tmp_path):
    """worldmodel_harness must route a non-coupling artifact to the spec-patch
    evaluator and return a branch-labelled verdict (not a silent hard-reject)."""
    from ztare.worldmodel.operator_implement import worldmodel_harness
    from ztare.worldmodel.episode_log import EpisodeLog

    # Minimal EpisodeLog with one trivial transition (grid stays same).
    log = EpisodeLog()
    g = ((0, 1), (2, 0))
    log.append(g, 0, g, t=0)

    # Artifact that is NOT a coupling (no when_effect / rule-coupling language).
    # Has a spec_patch key so the branch can attempt evaluation.
    artifact = {
        "name": "some_non_coupling_op",
        "semantics": "a plain spec patch that does something else entirely",
        "catalog_encoding": "recolor_map or similar",
        "planted_synthetic": "non-coupling scenario",
        "spec_patch": {"actions": {"0": []}, "always": []},
    }

    result = worldmodel_harness(artifact, real_log=log)

    # Must name the branch in the result, not just say "leaf shape does not name coupling".
    assert result.get("branch") == "spec_patch", (
        "Non-coupling artifact must be evaluated by spec_patch branch, "
        f"got counterexample={result.get('counterexample')!r}"
    )
    # Verdict must be present and boolean (accepted True or False, not missing).
    assert "accepted" in result


def test_coupling_leaf_still_uses_coupling_branch(tmp_path):
    """Coupling-named artifacts must still hit the coupling branch (regression guard)."""
    from ztare.worldmodel.operator_implement import worldmodel_harness

    coupling_artifact = {
        "name": "when_effect_rule_coupling",
        "semantics": "rule-coupling: timer ticks only when mover fired this step",
        "catalog_encoding": "when_effect [id, true]",
        "planted_synthetic": "two-colour mover on corridor",
        "mover_colors": [9, 12],
        "timer_color": 11,
        "ticks_when_moved": True,
    }
    # No real_log → should hit the coupling branch (not spec_patch) and fail
    # with "no real log" counterexample, not a "branch=spec_patch" error.
    result = worldmodel_harness(coupling_artifact, real_log=None)
    assert result.get("branch") != "spec_patch", (
        "A coupling artifact must not be rerouted to spec_patch branch"
    )
    assert not result["accepted"]


# ── FIX 3: empty-evidence card backfill ──────────────────────────────────────

def test_empty_evidence_card_backfilled_with_indices(tmp_path):
    """_backfill_empty_evidence_cards must compute mismatch indices for a card
    that has evidence_indices=[] and update the ledger row."""
    from ztare.worldmodel.grammar_reflex import _backfill_empty_evidence_cards
    from ztare.common.operator_proposal_contract import open_cards
    from ztare.worldmodel.episode_log import EpisodeLog

    ledger = tmp_path / "workspace" / "operator_proposals.jsonl"
    ledger.parent.mkdir(parents=True)

    # Write one open card with empty evidence_indices.
    card = {
        "schema": "operator-proposal-v1",
        "failure_family": "closure:test:backfill",
        "failure_family_sha": "aabbccdd",
        "evidence_indices": [],
        "disposition": "open",
        "proposed_operator_sketch": "test sketch",
        "why_existing_ops_fail": {},
        "spatial_footprint": {},
        "acceptance_test": "n/a",
    }
    with ledger.open("w") as f:
        f.write(json.dumps(card) + "\n")

    # Log with one transition that NO spec can predict (spec=None → all mismatches).
    log = EpisodeLog()
    g = ((0, 1), (2, 0))
    g2 = ((1, 0), (0, 2))
    log.append(g, 0, g2, t=0)

    _backfill_empty_evidence_cards(ledger, log, None)

    # After backfill, the card's evidence_indices must be non-empty OR have a note.
    remaining = open_cards(ledger)
    assert remaining, "card should still be open after backfill"
    updated = remaining[0]
    # With spec=None, _infer_mismatches returns all indices (the one row).
    assert updated.get("evidence_indices") == [0], (
        f"expected backfilled indices=[0], got {updated.get('evidence_indices')}"
    )


def test_empty_evidence_card_receipted_no_evidence_yet(tmp_path):
    """When _infer_mismatches finds nothing, card stays open with no_evidence_yet note."""
    from ztare.worldmodel.grammar_reflex import _backfill_empty_evidence_cards
    from ztare.common.operator_proposal_contract import open_cards
    from ztare.worldmodel.episode_log import EpisodeLog

    ledger = tmp_path / "workspace" / "operator_proposals.jsonl"
    ledger.parent.mkdir(parents=True)

    card = {
        "schema": "operator-proposal-v1",
        "failure_family": "closure:test:noevidence",
        "failure_family_sha": "deadbeef01",
        "evidence_indices": [],
        "disposition": "open",
        "proposed_operator_sketch": "hidden-state guard",
        "why_existing_ops_fail": {},
        "spatial_footprint": {},
        "acceptance_test": "n/a",
    }
    with ledger.open("w") as f:
        f.write(json.dumps(card) + "\n")

    # Empty log → _infer_mismatches returns [] → no_evidence_yet.
    log = EpisodeLog()
    _backfill_empty_evidence_cards(ledger, log, None)

    remaining = open_cards(ledger)
    assert remaining, "card must stay open"
    assert remaining[0].get("backfill_note") == "no_evidence_yet"


# ── FIX 4: persist_strategy_card_discharges called on gate pass ──────────────

def test_persist_strategy_card_discharges_called_on_gate_pass(tmp_path):
    """strategy_card_retry_message must call persist_strategy_card_discharges
    when the gate passes (result.passed=True)."""
    from ztare.validator.core import repair_preflight

    (tmp_path / "workspace").mkdir(parents=True)

    # Patch evaluate_strategy_card_gate to return passed=True.
    mock_result = MagicMock()
    mock_result.passed = True

    with patch.object(repair_preflight, "evaluate_strategy_card_gate",
                      return_value=mock_result) as _mock_eval, \
         patch.object(repair_preflight, "persist_strategy_card_discharges") as mock_persist, \
         patch.object(repair_preflight, "_looks_like_executable_worldmodel_carrier",
                      return_value=False):
        ret = repair_preflight.strategy_card_retry_message(
            project_dir=tmp_path,
            thesis_text="some thesis",
            candidate_source="",
        )

    assert ret is None, "gate pass must return None (no retry message)"
    mock_persist.assert_called_once(), (
        "persist_strategy_card_discharges must be called when gate passes"
    )


# ── FIX 4: zero-caller list includes persist_strategy_card_discharges ────────

def test_zero_caller_list_includes_persist_strategy_card_discharges():
    """_MUST_HAVE_CALLERS in test_contract_coherence must include
    persist_strategy_card_discharges so it can never silently lose its caller."""
    import importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "test_contract_coherence",
        str(REPO / "tests" / "test_contract_coherence.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    names = [fn for _, fn in mod._MUST_HAVE_CALLERS]
    assert "persist_strategy_card_discharges" in names, (
        "persist_strategy_card_discharges must be in _MUST_HAVE_CALLERS "
        "in test_contract_coherence.py"
    )


def test_persist_strategy_card_discharges_has_caller_in_src():
    """Structural: persist_strategy_card_discharges must have ≥1 caller in
    src/ztare/ outside its own definition file."""
    result = subprocess.run(
        ["grep", "-rn", "persist_strategy_card_discharges", str(SRC / "ztare")],
        capture_output=True, text=True,
    )
    def_file = "ztare/validator/core/strategy_card_gate.py"
    callers = [
        line for line in result.stdout.splitlines()
        if def_file not in line and ".pyc" not in line and ".py:" in line
    ]
    assert callers, (
        "persist_strategy_card_discharges has no callers in src/ztare/ "
        "outside its own definition — wire it in before shipping"
    )
