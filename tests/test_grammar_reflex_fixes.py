"""Tests for current-evidence grammar proposal routing and strategy discharge."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))


# ── FIX 1: non-coupling leaf routes to spec-patch branch ─────────────────────


def test_governed_carrier_owner_routes_bound_cards(tmp_path):
    from ztare.worldmodel import grammar_reflex
    from ztare.worldmodel.episode_log import EpisodeLog

    log = EpisodeLog()
    log.append(((1, 0), (0, 0)), 0, ((0, 1), (0, 0)), t=0)
    ab = SimpleNamespace(spec=None, step_fn=None, replay_ok=False)

    result = grammar_reflex.route_operator_proposals(
        tmp_path,
        log,
        ab,
    )

    assert result["status"] == "proposals_routed"
    assert result["implementation_owner"] == "governed_carrier"
    assert result["route"]["consumer"] == (
        "operator_proposals_briefing_to_governed_candidate_gate"
    )
    assert result["cards"]
    binding = result["cards"][0]["evidence_binding"]
    assert binding["mode"] == "exact_evidence_epoch"
    assert binding["evidence_role"] == "visible"
    assert binding["evidence_content_sha256"] == log.content_hash()
    assert result["cards"][0]["proposal_identity_sha"]


def test_proposal_dedup_separates_family_from_evidence_lifecycle(tmp_path):
    from ztare.common.operator_proposal_contract import (
        operator_proposal_card,
        open_cards,
        write_proposal_cards,
    )

    ledger = tmp_path / "operator_proposals.jsonl"
    base = operator_proposal_card(
        failure_family="same-residual-family",
        evidence_indices=[0],
        spatial_footprint={"count": 1},
        why_existing_ops_fail={"identity": "state changed"},
        proposed_operator_sketch="candidate_operation",
        acceptance_test="strict improvement",
    )
    first = dict(base)
    first["evidence_binding"] = {
        "mode": "exact_evidence_epoch",
        "project_evidence_epoch_sha256": "a" * 64,
    }
    second = dict(base)
    second["evidence_binding"] = {
        "mode": "exact_evidence_epoch",
        "project_evidence_epoch_sha256": "b" * 64,
    }

    assert len(write_proposal_cards(ledger, [first])) == 1
    assert write_proposal_cards(ledger, [first]) == []
    assert len(write_proposal_cards(ledger, [second])) == 1
    [current] = open_cards(ledger)
    assert current["evidence_binding"]["project_evidence_epoch_sha256"] == "b" * 64


def test_governed_route_uses_active_carrier_residual_indices(tmp_path, monkeypatch):
    from ztare.worldmodel import grammar_reflex
    from ztare.worldmodel.episode_log import EpisodeLog

    log = EpisodeLog()
    log.append(((0,),), 0, ((1,),), t=0)
    seen = {}

    def capture(_log, _spec, residual_indices):
        seen["residual_indices"] = residual_indices
        return []

    monkeypatch.setattr(grammar_reflex, "propose_operators", capture)
    grammar_reflex.route_operator_proposals(
        tmp_path,
        log,
        SimpleNamespace(spec=None, step_fn=None, replay_ok=False),
        residual_indices=[0],
    )

    assert seen["residual_indices"] == [0]


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
