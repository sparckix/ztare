"""Tests for the K-line forward edge: routing_prior (k_line.py) and
the order-bias wiring in engine_router.py.

Coverage:
  1. routing_prior: 4-of-6 threshold (exact match)
  2. routing_prior: 3-of-6 not enough → None
  3. routing_prior: human retrospective rows excluded by default
  4. routing_prior: modal vote when multiple rows match
  5. routing_prior: None when ledger is empty
  6. engine_router: hard rule (branch 1 / no champion) beats prior → overridden_by_rule
  7. engine_router: hard rule (branch 2 / udt>0) beats prior → overridden_by_rule
  8. engine_router: prior biases fallback branch (branch 6) → engine changed
  9. engine_router: prior on specialists branch adds budget_bonus
 10. engine_router: ZTARE_KLINE_PRIOR=0 kill-switch → prior not loaded
 11. engine_router: counterfactual recorded every Nth application
 12. engine_router: prior receipt written to router_prior_receipts.jsonl
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.k_line import (
    LEDGER_SCHEMA,
    ORIGIN_AGENT,
    ORIGIN_HUMAN,
    TRANSFER_PROSPECTIVE,
    TRANSFER_RETROSPECTIVE,
    routing_prior,
)
import ztare.worldmodel.engine_router as er


# ── Helpers ────────────────────────────────────────────────────────────────────


def _full_sig(**overrides) -> dict:
    """Return a full 6-axis signature with known defaults, optionally overridden."""
    base = {
        "warrant_stratum": "holdout",
        "contradiction_topology": "components-1",
        "residual_localization": "coherent_block",
        "input_conditionality": "uniform",
        "regime_position": "interior",
        "epistemic_state": "diverse",
    }
    base.update(overrides)
    return base


def _plant_klines(project_dir: Path, rows: list[dict]) -> None:
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    with (ws / "k_lines.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _make_row(sig: dict, fix_class: str, origin: str = ORIGIN_AGENT,
              transfer: str = TRANSFER_PROSPECTIVE, ts: str = "t1") -> dict:
    return {
        "schema": LEDGER_SCHEMA,
        "ts": ts,
        "signature": sig,
        "configuration": {"fix_class": fix_class},
        "outcome": "success",
        "origin": origin,
        "transfer_status": transfer,
    }


def _state(**overrides) -> dict:
    """Build a minimal router state dict."""
    base = {
        "has_champion": True,
        "champion_explains_visible": True,
        "holdout_residual_bits": 1,
        "population_stats": {"n_survivors": 0, "n_distinct_fingerprints": 0},
        "unresolved_disagreement_targets": 0,
        "stagnation": 0,
        "escape_unreachable": False,
        "enumeration_futile": False,
        "_ledger_exists": False,
        "_routing_prior": None,
        "_current_signature": _full_sig(),
    }
    base.update(overrides)
    return base


# ── Test 1: 4-of-6 match returns a prior ──────────────────────────────────────


def test_routing_prior_4_of_6_match(monkeypatch):
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)
    tmp = Path(tempfile.mkdtemp())
    sig = _full_sig()
    # Ledger row matches on 4 axes; 2 axes differ
    row_sig = _full_sig(
        residual_localization="single_cell",  # differ
        input_conditionality="mixed",          # differ
    )
    rows = [_make_row(row_sig, "residual_scaling_warmstart", ts=f"t{i}") for i in range(3)]
    _plant_klines(tmp, rows)

    result = routing_prior(tmp, sig)
    assert result is not None, "should match at 4-of-6"
    assert result["fix_class"] == "residual_scaling_warmstart"
    assert result["support"] == 3
    assert len(result["kline_refs"]) == 3


# ── Test 2: 3-of-6 match → None ───────────────────────────────────────────────


def test_routing_prior_3_of_6_no_match(monkeypatch):
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)
    tmp = Path(tempfile.mkdtemp())
    sig = _full_sig()
    # Only 3 axes match
    row_sig = _full_sig(
        residual_localization="single_cell",
        input_conditionality="mixed",
        regime_position="boundary",  # 3 diffs → 3 matches
    )
    rows = [_make_row(row_sig, "some_class", ts=f"t{i}") for i in range(3)]
    _plant_klines(tmp, rows)

    result = routing_prior(tmp, sig)
    assert result is None, "3-of-6 should not match threshold"


# ── Test 3: human retrospective rows excluded by default ──────────────────────


def test_routing_prior_excludes_human_retrospective(monkeypatch):
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)
    tmp = Path(tempfile.mkdtemp())
    sig = _full_sig()
    # Human retrospective rows that match on all 6 axes
    rows = [
        _make_row(sig, "contract_surface_routing",
                  origin=ORIGIN_HUMAN, transfer=TRANSFER_RETROSPECTIVE, ts=f"h{i}")
        for i in range(4)
    ]
    _plant_klines(tmp, rows)

    result = routing_prior(tmp, sig)
    assert result is None, "human retrospective rows must be excluded by default"


def test_routing_prior_includes_human_with_env(monkeypatch):
    monkeypatch.setenv("ZTARE_KLINE_HUMAN_PRIOR", "1")
    tmp = Path(tempfile.mkdtemp())
    sig = _full_sig()
    rows = [
        _make_row(sig, "contract_surface_routing",
                  origin=ORIGIN_HUMAN, transfer=TRANSFER_RETROSPECTIVE, ts=f"h{i}")
        for i in range(3)
    ]
    _plant_klines(tmp, rows)

    result = routing_prior(tmp, sig)
    assert result is not None
    assert result["fix_class"] == "contract_surface_routing"


# ── Test 4: modal vote with multiple fix_classes ───────────────────────────────


def test_routing_prior_modal_vote(monkeypatch):
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)
    tmp = Path(tempfile.mkdtemp())
    sig = _full_sig()
    rows = (
        [_make_row(sig, "residual_scaling_warmstart", ts=f"a{i}") for i in range(3)]
        + [_make_row(sig, "clone_and_reuse_real_organ", ts=f"b{i}") for i in range(2)]
    )
    _plant_klines(tmp, rows)

    result = routing_prior(tmp, sig)
    assert result is not None
    assert result["fix_class"] == "residual_scaling_warmstart"  # 3 > 2
    assert result["support"] == 3


# ── Test 5: empty ledger → None ───────────────────────────────────────────────


def test_routing_prior_empty_ledger(monkeypatch):
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()
    result = routing_prior(tmp, _full_sig())
    assert result is None


# ── Test 6: hard rule (no champion) beats prior → overridden_by_rule ──────────


def test_hard_rule_beats_prior_no_champion():
    """Branch 1 (no champion) is a hard rule; prior must not override it."""
    prior = {"fix_class": "residual_scaling_warmstart", "support": 3, "kline_refs": []}
    state = _state(has_champion=False, _routing_prior=prior)
    decision = er.route(state)
    assert decision["engine"] == "autoresearch"
    assert decision.get("_overridden_by_rule") is True


# ── Test 7: hard rule (udt>0) beats prior → overridden_by_rule ────────────────


def test_hard_rule_beats_prior_distinguishing():
    """Branch 2 (unresolved targets) is a hard rule; prior must not redirect it."""
    prior = {"fix_class": "residual_scaling_warmstart", "support": 3, "kline_refs": []}
    state = _state(
        unresolved_disagreement_targets=2,
        _ledger_exists=True,
        _routing_prior=prior,
        population_stats={"n_survivors": 2, "n_distinct_fingerprints": 2},
    )
    decision = er.route(state)
    assert decision["engine"] == "version_space"
    assert decision.get("phase") == "distinguishing_play"
    assert decision.get("_overridden_by_rule") is True


# ── Test 8: prior biases fallback branch (branch 6) ──────────────────────────


def test_prior_biases_fallback_branch():
    """At fallback (stagnation >= threshold), prior can change the engine chosen."""
    import ztare.worldmodel.engine_router as _er
    old = _er._STAGNATION_THRESHOLD
    _er._STAGNATION_THRESHOLD = 2
    try:
        # 'specialists' prior → prior engine is "specialists" (from fix_class map)
        prior = {"fix_class": "residual_scaling_warmstart", "support": 3, "kline_refs": []}
        state = _state(
            stagnation=2,  # at threshold → fallback branch
            _ledger_exists=True,
            _routing_prior=prior,
            population_stats={"n_survivors": 1, "n_distinct_fingerprints": 2},
        )
        decision = er.route(state)
        assert decision["engine"] == "specialists", (
            f"prior (residual_scaling_warmstart → specialists) should bias fallback; got {decision}"
        )
        assert decision.get("_overridden_by_rule") is False
        assert "kline_prior_bias" in decision["reason"]
    finally:
        _er._STAGNATION_THRESHOLD = old


# ── Test 9: prior on specialists branch adds budget_bonus ──────────────────────


def test_prior_adds_budget_bonus_on_specialists_branch():
    """In branch 4 (specialists), if prior agrees → budget_bonus=1."""
    prior = {"fix_class": "residual_scaling_warmstart", "support": 2, "kline_refs": []}
    # specialists branch: hc+cev, hrb>0, udt=0, no ledger, low stagnation
    state = _state(
        _ledger_exists=False,
        _routing_prior=prior,
        stagnation=0,
    )
    decision = er.route(state)
    assert decision["engine"] == "specialists"
    assert decision.get("budget_bonus") == 1


# ── Test 10: ZTARE_KLINE_PRIOR=0 kill-switch ──────────────────────────────────


def test_kline_prior_killswitch(tmp_path, monkeypatch):
    """ZTARE_KLINE_PRIOR=0 → prior not loaded; routing_prior never called."""
    monkeypatch.setenv("ZTARE_KLINE_PRIOR", "0")
    ws = tmp_path / "workspace"
    ws.mkdir()

    # Plant a full k-line ledger that would match
    sig = _full_sig()
    rows = [_make_row(sig, "residual_scaling_warmstart", ts=f"t{i}") for i in range(3)]
    (ws / "k_lines.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    called = []
    original_rp = None
    import ztare.common.k_line as kl
    _orig = kl.routing_prior

    def spy(*a, **kw):
        called.append(1)
        return _orig(*a, **kw)

    with patch.object(er, "knowledge_state") as mock_ks:
        # knowledge_state reads the env var; replicate it
        mock_ks.return_value = {
            "has_champion": False,
            "champion_explains_visible": False,
            "holdout_residual_bits": 1,
            "population_stats": {"n_survivors": 0, "n_distinct_fingerprints": 0},
            "unresolved_disagreement_targets": 0,
            "stagnation": 0,
            "escape_unreachable": False,
            "enumeration_futile": False,
            "_ledger_exists": False,
            "_current_signature": sig,
            "_routing_prior": None,  # kill-switch active → None
        }
        state, decision = er.decide(tmp_path)

    # No prior receipt should exist (prior is None when kill-switch active)
    receipt_path = ws / "router_prior_receipts.jsonl"
    assert not receipt_path.exists(), "no prior receipt should be written when prior is None"


# ── Test 11: counterfactual recorded every Nth application ────────────────────


def test_counterfactual_cadence(tmp_path, monkeypatch):
    """Every Nth application of the prior writes prior_choice + counterfactual_choice."""
    monkeypatch.setenv("ZTARE_KLINE_PRIOR", "1")
    monkeypatch.setenv("ZTARE_KLINE_COUNTERFACTUAL_N", "3")

    # Reset the module-level application counter
    er._kline_prior_application_count = 0

    ws = tmp_path / "workspace"
    ws.mkdir()

    prior = {"fix_class": "residual_scaling_warmstart", "support": 2, "kline_refs": []}
    sig = _full_sig()

    import ztare.worldmodel.engine_router as _er
    old_thresh = _er._STAGNATION_THRESHOLD
    _er._STAGNATION_THRESHOLD = 99  # ensure specialists branch fires, not fallback

    def make_state():
        return {
            "has_champion": True,
            "champion_explains_visible": True,
            "holdout_residual_bits": 1,
            "population_stats": {"n_survivors": 0, "n_distinct_fingerprints": 0},
            "unresolved_disagreement_targets": 0,
            "stagnation": 0,
            "escape_unreachable": False,
            "enumeration_futile": False,
            "_ledger_exists": False,
            "_current_signature": sig,
            "_routing_prior": prior,
        }

    try:
        for _ in range(3):
            with patch.object(er, "knowledge_state", return_value=make_state()):
                er.decide(tmp_path)

        receipts_path = ws / "router_prior_receipts.jsonl"
        assert receipts_path.exists()
        rows = [json.loads(l) for l in receipts_path.read_text().splitlines() if l.strip()]
        assert len(rows) == 3

        # 3rd row (index 2) should have counterfactual fields
        cf_rows = [r for r in rows if "counterfactual_choice" in r]
        assert cf_rows, "at least one counterfactual row should be written at N=3"
        cf = cf_rows[0]
        assert "prior_choice" in cf
        assert "diverged" in cf
    finally:
        _er._STAGNATION_THRESHOLD = old_thresh
        er._kline_prior_application_count = 0


# ── Test 12: prior receipt written to router_prior_receipts.jsonl ─────────────


def test_prior_receipt_written(tmp_path, monkeypatch):
    """When a prior exists, a receipt row is written with correct schema fields."""
    monkeypatch.setenv("ZTARE_KLINE_PRIOR", "1")
    er._kline_prior_application_count = 0

    ws = tmp_path / "workspace"
    ws.mkdir()

    prior = {"fix_class": "residual_scaling_warmstart", "support": 3, "kline_refs": ["t1"]}
    sig = _full_sig()

    state = {
        "has_champion": False,
        "champion_explains_visible": False,
        "holdout_residual_bits": 1,
        "population_stats": {"n_survivors": 0, "n_distinct_fingerprints": 0},
        "unresolved_disagreement_targets": 0,
        "stagnation": 0,
        "escape_unreachable": False,
        "enumeration_futile": False,
        "_ledger_exists": False,
        "_current_signature": sig,
        "_routing_prior": prior,
    }

    with patch.object(er, "knowledge_state", return_value=state):
        er.decide(tmp_path)

    receipt_path = ws / "router_prior_receipts.jsonl"
    assert receipt_path.exists()
    row = json.loads(receipt_path.read_text().strip())
    assert row["schema"] == "ztare.kline_routing_prior.v1"
    assert row["prior"] == prior
    assert "applied" in row
    assert "overridden_by_rule" in row
    assert row["overridden_by_rule"] is True  # branch 1 fired (no champion)
    assert row["chosen_engine"] == "autoresearch"
