"""Planted-defect tests: validator core must raise or leave a receipt.

Each test targets a previously-silent fallback in src/ztare/validator/core/:
an error or absence that used to be coerced into an ordinary verdict must now
either raise or persist a receipt row that names its instance.
"""
from __future__ import annotations

import json

import pytest

from ztare.validator.core import pre_judge_gate, strategy_card_gate
from ztare.validator.core.pre_judge_gate import (
    _best_prior_candidate_record,
    _candidate_prior_comparison_receipt,
    _failed_gate_labels,
    detect_patch_base_regression_preflight,
)
from ztare.validator.core.strategy_card_gate import evaluate_strategy_card_gate


def _receipt_rows(project_dir):
    ledger = project_dir / "workspace" / "pre_judge_gate_receipts.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]


def test_zero_stdout_harness_raises(tmp_path):
    # gate_harness.py exits 0 but emits nothing: must raise, not become "{}".
    (tmp_path / "gate_harness.py").write_text("", encoding="utf-8")
    candidate = tmp_path / "cand.py"
    candidate.write_text("pass\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty stdout"):
        detect_patch_base_regression_preflight(
            enabled=True,
            project_dir=tmp_path,
            candidate_path=candidate,
        )


def test_corrupt_candidate_memory_writes_receipt(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "candidate_memory.json").write_text("{not json", encoding="utf-8")
    assert _best_prior_candidate_record(tmp_path, exclude_sha="x") is None
    rows = _receipt_rows(tmp_path)
    assert any(row.get("fallback_taken") == "corrupt_candidate_memory" for row in rows)
    assert any("JSONDecodeError" in str(row.get("cause")) for row in rows)


def test_missing_candidate_memory_is_silent_absence(tmp_path):
    # No file is legitimate absence, not corruption: no receipt spam.
    assert _best_prior_candidate_record(tmp_path, exclude_sha="x") is None
    assert _receipt_rows(tmp_path) == []


_BEST_PRIOR = {
    "sha": "priorsha",
    "submission": "prior.py",
    "visible_exact_rows": 3,
    "visible_wrong_cells": 1,
    "holdout_depth": 2,
    "gate_score": 0.5,
}


def _gate_entries():
    return [
        {
            "name": "visible_replay_exact",
            "passed": True,
            "diagnostics": {"exact_rows": 5, "checked_rows": 5, "wrong_cell_count": 0},
        },
        {"name": "holdout_rollout_exact", "passed": True, "value": 7},
    ]


def test_list_form_gates_holdout_not_zeroed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pre_judge_gate, "_best_prior_candidate_record", lambda *a, **k: dict(_BEST_PRIOR)
    )
    entries = _gate_entries()
    dict_payload = {"gates": {g["name"]: g for g in entries}, "gated_sha256": "abc"}
    list_payload = {"gates": entries, "gated_sha256": "abc"}
    receipts = [
        _candidate_prior_comparison_receipt(
            project_dir=tmp_path, candidate_path=None, gate_payload=payload
        )
        for payload in (dict_payload, list_payload)
    ]
    assert all(r is not None for r in receipts)
    dict_receipt, list_receipt = receipts
    assert dict_receipt["candidate_holdout_depth"] == 7
    assert list_receipt["candidate_holdout_depth"] == 7
    assert list_receipt["_candidate_rank"] == dict_receipt["_candidate_rank"]


def test_missing_exact_rows_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pre_judge_gate, "_best_prior_candidate_record", lambda *a, **k: dict(_BEST_PRIOR)
    )
    payload = {
        "gates": {
            "visible_replay_exact": {
                "name": "visible_replay_exact",
                "passed": True,
                "diagnostics": {"checked_rows": 5},
            }
        },
        "gated_sha256": "abc",
    }
    assert (
        _candidate_prior_comparison_receipt(
            project_dir=tmp_path, candidate_path=None, gate_payload=payload
        )
        is None
    )


def test_failed_gate_labels_name_harness_ok_and_schema_mismatch():
    passing = [{"name": "g1", "passed": True}]
    assert _failed_gate_labels(passing, harness_ok=False) == ["harness_ok: false"]
    assert _failed_gate_labels([], harness_ok=True) == ["?: no gates emitted"]
    labels = _failed_gate_labels([{"name": "g2", "value": 3}], harness_ok=True)
    assert labels == ["g2: missing 'passed' field"]


def test_unparseable_discharge_lands_in_invalid(monkeypatch, tmp_path):
    card = {"failure_family_sha": "fam123", "kind": "repair"}
    monkeypatch.setattr(strategy_card_gate, "_load_open_strategy_cards", lambda p: [card])
    monkeypatch.setattr(
        strategy_card_gate, "_blocking_strategy_cards", lambda cards, context=None: cards
    )
    result = evaluate_strategy_card_gate(
        project_dir=tmp_path,
        thesis_text='STRATEGY_CARD_DISCHARGE: {"outcome": nope}',
    )
    assert not result.passed
    invalid = result.payload["invalid"]
    unparseable = [row for row in invalid if row.get("reason") == "unparseable_receipt"]
    assert unparseable, invalid
    assert '"outcome"' in unparseable[0]["raw_prefix"]
    assert len(unparseable[0]["raw_prefix"]) <= 120
