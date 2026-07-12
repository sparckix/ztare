"""Order-independence tests for three ZTARE surfaces.

(a) spec_nogood pruning — JSONL row order doesn't change prune set
(b) derived_constraints — observation delivery order doesn't change confirmed set
(c) dominance rank key — candidate list order doesn't change best candidate
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# (a) spec_nogood: JSONL row order → identical visible_clauses key set
# ---------------------------------------------------------------------------

def _write_nogood_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_spec_nogood_order_independence(tmp_path: Path) -> None:
    from ztare.worldmodel.spec_nogood import SpecNogoodLedger

    row_a = {
        "signature": "aaa111",
        "witness_summary": "visible mismatch A",
        "provenance": {"evidence": "visible", "source": "test", "t": 0, "a": 0, "s": [], "predicted_next": []},
    }
    row_b = {
        "signature": "bbb222",
        "witness_summary": "visible mismatch B",
        "provenance": {"evidence": "visible", "source": "test", "t": 1, "a": 0, "s": [], "predicted_next": []},
    }

    dir_ab = tmp_path / "ab"
    dir_ba = tmp_path / "ba"

    ledger_ab = SpecNogoodLedger(dir_ab)
    ledger_ba = SpecNogoodLedger(dir_ba)

    _write_nogood_rows(ledger_ab.path, [row_a, row_b])
    _write_nogood_rows(ledger_ba.path, [row_b, row_a])

    keys_ab = set(ledger_ab.visible_clauses().keys())
    keys_ba = set(ledger_ba.visible_clauses().keys())

    assert keys_ab == keys_ba, f"prune sets differ: {keys_ab} vs {keys_ba}"

    # blocks() must agree on both signatures regardless of order
    candidate_sigs = ["aaa111", "bbb222", "ccc333"]
    for sig in candidate_sigs:
        assert (ledger_ab.blocks(sig) is not None) == (ledger_ba.blocks(sig) is not None), (
            f"blocks({sig!r}) disagrees between AB and BA ledgers"
        )


# ---------------------------------------------------------------------------
# (b) derived_constraints: observation order → identical confirmed set (by sig)
# ---------------------------------------------------------------------------

def _make_proposal(tag: str) -> dict:
    return {
        "constraint": f"constraint {tag}",
        "applies_to": "test scope",
        "failure_family": "test_family",
        "severity": "blocking",
        "producer": "meta_judge",
        "rationale": f"rationale {tag}",
        "non_applicability_condition": "never",
    }


def test_derived_constraints_order_independence(tmp_path: Path) -> None:
    from ztare.gates.derived_constraints import update_derived_constraints_ledger

    proposal_x = _make_proposal("X")

    # Scenario: two observations of proposal_x, run_id=1 iter=0 then run_id=2 iter=0
    # Delivered in two orders via sequential calls (each call is one observation).

    # Order A: run 1 first, then run 2
    ledger_a = tmp_path / "a" / "dc.json"
    update_derived_constraints_ledger(
        project="test_proj",
        ledger_path=ledger_a,
        proposals=[proposal_x],
        run_id=1,
        iteration_index=0,
        source_score=70,
        weakest_point="wp",
        score_regime_fingerprint="fp1",
        confirmation_threshold_runs=2,
    )
    result_a = update_derived_constraints_ledger(
        project="test_proj",
        ledger_path=ledger_a,
        proposals=[proposal_x],
        run_id=2,
        iteration_index=0,
        source_score=75,
        weakest_point="wp",
        score_regime_fingerprint="fp2",
        confirmation_threshold_runs=2,
    )

    # Order B: run 2 first, then run 1
    ledger_b = tmp_path / "b" / "dc.json"
    update_derived_constraints_ledger(
        project="test_proj",
        ledger_path=ledger_b,
        proposals=[proposal_x],
        run_id=2,
        iteration_index=0,
        source_score=75,
        weakest_point="wp",
        score_regime_fingerprint="fp2",
        confirmation_threshold_runs=2,
    )
    result_b = update_derived_constraints_ledger(
        project="test_proj",
        ledger_path=ledger_b,
        proposals=[proposal_x],
        run_id=1,
        iteration_index=0,
        source_score=70,
        weakest_point="wp",
        score_regime_fingerprint="fp1",
        confirmation_threshold_runs=2,
    )

    sigs_a = {c["signature"] for c in result_a["confirmed_constraints"]}
    sigs_b = {c["signature"] for c in result_b["confirmed_constraints"]}

    assert sigs_a == sigs_b, f"confirmed sets differ: {sigs_a} vs {sigs_b}"
    assert len(sigs_a) == 1, f"expected 1 confirmed constraint, got {len(sigs_a)}"


# ---------------------------------------------------------------------------
# (c) dominance rank key: candidate list order → same best candidate
# ---------------------------------------------------------------------------

def _make_gate_payload(exact_rows: int, wrong_cells: int, holdout_depth: int) -> dict:
    """Build a minimal gate_payload that _rank_key can consume without subprocess."""
    return {
        "harness_ok": True,
        "gates": {
            "visible_replay_exact": {
                "name": "visible_replay_exact",
                "passed": True,
                "tier": "observed",
                "diagnostics": {
                    "exact_rows": exact_rows,
                    "wrong_cell_count": wrong_cells,
                },
            },
            "holdout_rollout_exact": {
                "name": "holdout_rollout_exact",
                "passed": True,
                "tier": "heldout",
                "value": holdout_depth,
            },
        },
    }


def test_rank_key_order_independence() -> None:
    from ztare.validator.core.champion_materialization import _rank_key

    payload_a = _make_gate_payload(exact_rows=5, wrong_cells=2, holdout_depth=3)
    payload_b = _make_gate_payload(exact_rows=3, wrong_cells=0, holdout_depth=7)
    payload_c = _make_gate_payload(exact_rows=5, wrong_cells=1, holdout_depth=1)

    # payload_c should win: tied exact_rows=5 with a, fewer wrong_cells (1 < 2)

    candidates_abc = [payload_a, payload_b, payload_c]
    candidates_cba = [payload_c, payload_b, payload_a]
    candidates_bca = [payload_b, payload_c, payload_a]

    best_abc = max(candidates_abc, key=_rank_key)
    best_cba = max(candidates_cba, key=_rank_key)
    best_bca = max(candidates_bca, key=_rank_key)

    key_abc = _rank_key(best_abc)
    key_cba = _rank_key(best_cba)
    key_bca = _rank_key(best_bca)

    assert key_abc == key_cba == key_bca, (
        f"best rank differs by order: ABC={key_abc}, CBA={key_cba}, BCA={key_bca}"
    )
    # Confirm the expected winner's rank
    expected_key = (5, -1, 1)  # exact=5, wrong_cells=-1 (inverted), holdout=1
    assert key_abc == expected_key, f"expected rank {expected_key}, got {key_abc}"
