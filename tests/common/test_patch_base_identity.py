from __future__ import annotations

import json
import hashlib

from ztare.common.patch_base_identity import (
    persist_repair_frontier_if_dominant,
    persist_repair_frontier_observation,
    repair_frontier_order,
    repair_frontier_fields,
)


def _payload(
    *,
    exact: int,
    wrong: int,
    relation: str,
    rich: bool,
    candidate_sha: str,
) -> dict:
    quotient = {
        "candidate_top_quotient": {
            "first_row": 9,
            "t": 7,
            "action": 0,
            "bbox": [0, 0, 1, 1],
            "pair_counts": [{"predicted": 1, "real": 2, "count": 1}],
        },
        "best_prior_top_quotient": {
            "first_row": 4 if rich else None,
            "t": 7 if rich else None,
            "action": 0 if rich else None,
            "bbox": [2, 2, 3, 3],
            "pair_counts": [],
        },
    }
    return {
        "schema": "ztare-latest-patch-base-regression-v1",
        "evidence_epoch": {"epoch_sha256": "epoch-a"},
        "candidate_regression_receipt": {
            "candidate_relation": relation,
            "candidate_sha": candidate_sha,
            "candidate_submission": "workspace/submissions/a.py",
            "candidate_exact_rows": exact,
            "candidate_wrong_cells": wrong,
            "candidate_holdout_depth": 16,
            "candidate_gate_score": 0.5,
            "best_prior_sha": candidate_sha,
            "best_prior_submission": "workspace/submissions/a.py",
            "best_prior_exact_rows": exact,
            "best_prior_wrong_cells": wrong,
            "best_prior_holdout_depth": 16,
            "best_prior_gate_score": 0.5,
            "quotient_comparison": quotient,
        },
        "counterexample_trace": {"marker": "rich" if rich else "degenerate"},
    }


def test_repair_frontier_is_monotone_and_preserves_richer_equal_score_witness(
    tmp_path,
) -> None:
    submission = tmp_path / "workspace/submissions/a.py"
    submission.parent.mkdir(parents=True)
    submission.write_text("VALUE = 1\n", encoding="utf-8")
    candidate_sha = hashlib.sha256(submission.read_bytes()).hexdigest()
    rich = _payload(
        exact=10,
        wrong=1,
        relation="improved_but_gate_failed",
        rich=True,
        candidate_sha=candidate_sha,
    )
    assert persist_repair_frontier_if_dominant(tmp_path, rich) is True

    degenerate = _payload(
        exact=10,
        wrong=1,
        relation="no_strict_improvement",
        rich=False,
        candidate_sha=candidate_sha,
    )
    assert persist_repair_frontier_if_dominant(tmp_path, degenerate) is False
    stored = json.loads(
        (tmp_path / "workspace/latest_patch_base_regression.json").read_text()
    )
    assert stored["counterexample_trace"]["marker"] == "rich"

    improved = _payload(
        exact=11,
        wrong=0,
        relation="improved_but_gate_failed",
        rich=True,
        candidate_sha=candidate_sha,
    )
    assert persist_repair_frontier_if_dominant(tmp_path, improved) is True


def test_pareto_incomparable_candidate_retains_prior_carrier_identity(tmp_path) -> None:
    submission = tmp_path / "workspace/submissions/a.py"
    submission.parent.mkdir(parents=True)
    submission.write_text("VALUE = 1\n", encoding="utf-8")
    prior_sha = hashlib.sha256(submission.read_bytes()).hexdigest()
    payload = _payload(
        exact=11,
        wrong=0,
        relation="pareto_incomparable_complexity_regression",
        rich=True,
        candidate_sha=prior_sha,
    )
    regression = payload["candidate_regression_receipt"]
    regression["candidate_sha"] = "c" * 64
    regression["candidate_submission"] = ""
    regression["best_prior_exact_rows"] = 10
    regression["best_prior_wrong_cells"] = 1

    identity = repair_frontier_fields(regression)

    assert identity["role"] == "best_admissible_prior"
    assert identity["source_ref"] == "workspace/submissions/a.py"
    assert identity["sha256"] == prior_sha
    assert persist_repair_frontier_if_dominant(tmp_path, payload) is True


def test_gate_and_retry_producers_share_one_frontier_observation_envelope(
    tmp_path,
) -> None:
    submission = tmp_path / "workspace/submissions/a.py"
    submission.parent.mkdir(parents=True)
    submission.write_text("VALUE = 1\n", encoding="utf-8")
    candidate_sha = hashlib.sha256(submission.read_bytes()).hexdigest()
    payload = _payload(
        exact=10,
        wrong=1,
        relation="improved_but_gate_failed",
        rich=True,
        candidate_sha=candidate_sha,
    )

    assert persist_repair_frontier_observation(
        tmp_path,
        regression_receipt=payload["candidate_regression_receipt"],
        counterexample_trace=payload["counterexample_trace"],
        evidence_epoch=payload["evidence_epoch"],
    ) is True

    stored = json.loads(
        (tmp_path / "workspace/latest_patch_base_regression.json").read_text()
    )
    assert stored == payload


def test_repair_frontier_order_uses_description_only_on_behavioral_tie() -> None:
    compact = repair_frontier_order(
        exact_rows=20,
        holdout_depth=4,
        gate_score=0.5,
        wrong_cells=2,
        description_length=100,
    )
    verbose = repair_frontier_order(
        exact_rows=20,
        holdout_depth=4,
        gate_score=0.5,
        wrong_cells=2,
        description_length=200,
    )
    better_evidence = repair_frontier_order(
        exact_rows=21,
        holdout_depth=4,
        gate_score=0.5,
        wrong_cells=2,
        description_length=10_000,
    )

    assert compact > verbose
    assert better_evidence > compact
