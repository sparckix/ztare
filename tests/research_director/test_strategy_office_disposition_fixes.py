"""Tests for the 4 disposition fixes in strategy_office + trace_auditor.

1. rejection_class derivation (incomplete vs unsound)
2. supersedes chain linking
3. reconcile_dispositions updates ledger
4. case_law_divergence detector fires on planted divergence
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from ztare.research_director.strategy_office import (
    _derive_rejection_class,
    _link_superseded_prior,
    _render_rejection_line,
    reconcile_dispositions,
    DISPOSITION_RECONCILIATION,
    LEAF_PROPOSAL_LEDGER,
)
from ztare.orchestrator.trace_auditor import check_case_law_divergence


# ── helpers ───────────────────────────────────────────────────────────────────

def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "proj" / "workspace"
    ws.mkdir(parents=True)
    return ws


def _jl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


# ── 1. rejection_class derivation ────────────────────────────────────────────

def test_derive_incomplete_on_missing_keyword():
    assert _derive_rejection_class("lacks a planted synthetic acceptance test") == "incomplete"
    assert _derive_rejection_class("The proposal is malformed and incomplete: missing schema") == "incomplete"
    assert _derive_rejection_class("no evidence provided, no receipt") == "incomplete"


def test_derive_unsound_on_disqualify_keyword():
    assert _derive_rejection_class(
        "explicitly disqualifies it from auto-adoption; certifier_touched is true"
    ) == "unsound"


def test_derive_incomplete_conservative_default():
    # Unknown reason → conservative default
    assert _derive_rejection_class("some other obscure complaint") == "incomplete"


def test_render_rejection_line_incomplete():
    row = {
        "disposition": "rejected",
        "rejection_class": "incomplete",
        "reason": "adjudicator: lacks a planted synthetic acceptance test [Rule 2]",
    }
    line = _render_rejection_line(row)
    assert line.startswith("REJECTED-INCOMPLETE")
    assert "resubmit" in line


def test_render_rejection_line_unsound():
    row = {
        "disposition": "rejected",
        "rejection_class": "unsound",
        "reason": "certifier_touched disqualifies auto-adoption",
    }
    line = _render_rejection_line(row)
    assert line.startswith("REJECTED-UNSOUND")


def test_render_rejection_line_superseded_implemented():
    row = {
        "disposition": "superseded_implemented",
        "implemented_receipt_refs": ["src/foo.py:bar", "workspace/baz.jsonl"],
    }
    line = _render_rejection_line(row)
    assert "SUPERSEDED-IMPLEMENTED" in line
    assert "src/foo.py:bar" in line


# ── 2. supersedes chain ──────────────────────────────────────────────────────

def test_link_superseded_prior_sets_field(tmp_path):
    ws = _ws(tmp_path)
    ledger = ws / LEAF_PROPOSAL_LEDGER
    prior_sig = "aaaa" * 16
    new_sig = "bbbb" * 16
    _jl(ledger, [
        {"proposal_signature": prior_sig, "disposition": "rejected", "reason": "lacks test"},
        {"proposal_signature": "other", "disposition": "open"},
    ])
    _link_superseded_prior(ledger, prior_sig, new_sig)
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    updated = next(r for r in rows if r.get("proposal_signature") == prior_sig)
    assert updated.get("disposition_superseded_by") == new_sig


def test_link_superseded_prior_noop_on_missing(tmp_path):
    ws = _ws(tmp_path)
    ledger = ws / LEAF_PROPOSAL_LEDGER
    _jl(ledger, [{"proposal_signature": "xxxx", "disposition": "rejected"}])
    _link_superseded_prior(ledger, "does_not_exist", "nnnn")  # must not raise
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert rows[0].get("disposition_superseded_by") is None


def test_link_superseded_prior_skips_accepted(tmp_path):
    ws = _ws(tmp_path)
    ledger = ws / LEAF_PROPOSAL_LEDGER
    sig = "cccc" * 16
    _jl(ledger, [{"proposal_signature": sig, "disposition": "accepted"}])
    _link_superseded_prior(ledger, sig, "dddd")
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert rows[0].get("disposition_superseded_by") is None


# ── 3. reconcile_dispositions ─────────────────────────────────────────────────

def test_reconcile_updates_rejected_to_superseded(tmp_path):
    ws = _ws(tmp_path)
    proj = ws.parent
    sig_a = "a" * 64
    sig_b = "b" * 64
    _jl(ws / LEAF_PROPOSAL_LEDGER, [
        {"proposal_signature": sig_a, "disposition": "rejected", "reason": "lacks test"},
        {"proposal_signature": sig_b, "disposition": "rejected", "reason": "other"},
    ])
    _jl(ws / DISPOSITION_RECONCILIATION, [
        {"proposal_sig": sig_a, "implemented_receipt_refs": ["src/foo.py:bar"], "note": "done"},
    ])
    result = reconcile_dispositions(proj)
    assert result["status"] == "ok"
    assert result["updated_count"] == 1
    assert result["no_match"] == 1
    rows = [json.loads(l) for l in (ws / LEAF_PROPOSAL_LEDGER).read_text().splitlines() if l.strip()]
    updated = next(r for r in rows if r.get("proposal_signature") == sig_a)
    assert updated["disposition"] == "superseded_implemented"
    assert "src/foo.py:bar" in updated["implemented_receipt_refs"]


def test_reconcile_already_reconciled_not_double_counted(tmp_path):
    ws = _ws(tmp_path)
    proj = ws.parent
    sig = "c" * 64
    _jl(ws / LEAF_PROPOSAL_LEDGER, [
        {"proposal_signature": sig, "disposition": "superseded_implemented"},
    ])
    _jl(ws / DISPOSITION_RECONCILIATION, [
        {"proposal_sig": sig, "implemented_receipt_refs": ["x"]},
    ])
    result = reconcile_dispositions(proj)
    assert result["updated_count"] == 0
    assert result["already_reconciled"] == 1


def test_reconcile_no_recon_file(tmp_path):
    ws = _ws(tmp_path)
    proj = ws.parent
    _jl(ws / LEAF_PROPOSAL_LEDGER, [{"proposal_signature": "d" * 64, "disposition": "rejected"}])
    result = reconcile_dispositions(proj)
    assert result["status"] == "no_reconciliation_map"
    assert result["updated_count"] == 0


# ── 4. case_law_divergence detector ──────────────────────────────────────────

def test_case_law_divergence_fires_on_unreconciled(tmp_path):
    ws = _ws(tmp_path)
    sig = "e" * 64
    _jl(ws / LEAF_PROPOSAL_LEDGER, [
        {"proposal_signature": sig, "disposition": "rejected", "reason": "lacks test"},
    ])
    _jl(ws / DISPOSITION_RECONCILIATION, [
        {"proposal_sig": sig, "implemented_receipt_refs": ["src/bar.py"]},
    ])
    state: dict = {}
    f = check_case_law_divergence(ws, state)
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "case_law_divergence"
    assert sig[:16] in f["witness"]["divergent_sigs"]


def test_case_law_divergence_ok_after_reconcile(tmp_path):
    ws = _ws(tmp_path)
    sig = "f" * 64
    _jl(ws / LEAF_PROPOSAL_LEDGER, [
        {"proposal_signature": sig, "disposition": "superseded_implemented"},
    ])
    _jl(ws / DISPOSITION_RECONCILIATION, [
        {"proposal_sig": sig, "implemented_receipt_refs": ["src/baz.py"]},
    ])
    state: dict = {}
    f = check_case_law_divergence(ws, state)
    assert f["verdict"] == "ok"


def test_case_law_divergence_ok_no_recon_file(tmp_path):
    ws = _ws(tmp_path)
    state: dict = {}
    f = check_case_law_divergence(ws, state)
    assert f["verdict"] == "ok"
