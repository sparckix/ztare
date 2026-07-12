"""Planted invariant: residual pricing demotes baseline-explained probes.

A probe whose only distinguishing atoms are already in the champion baseline
must rank below a probe with fewer raw bits but fully residual information.
"""

from ztare.worldmodel.probe_selection import rank_probes


def _rec(mention: str, visible_wrong: int = 0) -> dict:
    """Minimal record that build_witness_hypergraph and _champion_baseline_atoms can read."""
    return {
        "claim_class": mention,
        "visible_wrong_cells": visible_wrong,
        "counterexample_trace": {"holdout_witness": {"divergent_cells": []}},
    }


def _rec_with_holdout(holdout_row: int, holdout_col: int) -> dict:
    return {
        "claim_class": "candidate_evaluation",
        "visible_wrong_cells": 0,
        "counterexample_trace": {
            "holdout_witness": {
                "divergent_cells": [{"row": holdout_row, "col": holdout_col, "actual": 3, "predicted": 11}]
            }
        },
    }


def test_residual_ranks_above_baseline_explained():
    """Probe A: fully in champion baseline (high raw bits, 0 residual).
    Probe B: tiny raw bits but fully residual (not in baseline).
    B must rank above A after residual pricing.
    """
    # Build a committee where:
    #   atom "candidate_evaluation" appears in ALL records (claim_class) → baseline atom
    #   atom "cell_row_99_col_99" appears only in holdout divergent_cells → residual atom
    committee = [
        _rec("candidate_evaluation"),
        _rec("candidate_evaluation"),
        _rec("candidate_evaluation"),
        _rec("candidate_evaluation"),
        _rec_with_holdout(99, 99),  # only this record has cell_row_99_col_99
    ]
    # Transversal covering both atoms
    transversals = [frozenset(["candidate_evaluation"]), frozenset(["cell_row_99_col_99"])]

    ranked = rank_probes(
        transversals,
        committee,
        max_probes=10,
        baseline_probe_ids=frozenset({"candidate_evaluation"}),
        baseline_ref="arc_agi.test_champion_visible_replay.v1",
    )

    by_probe = {r["probe"]: r for r in ranked}

    # candidate_evaluation: appears in all 5 records → raw bits ≈ 0 (no partition)
    # cell_row_99_col_99: appears in 1/5 records → raw bits > 0; fully residual
    assert "cell_row_99_col_99" in by_probe, "residual probe must appear in ranked output"
    assert "candidate_evaluation" in by_probe, "baseline probe must appear in ranked output"

    residual_probe = by_probe["cell_row_99_col_99"]
    baseline_probe = by_probe["candidate_evaluation"]

    # Residual probe scores positively, baseline probe scores 0 (in baseline → subtracted)
    assert residual_probe["residual_identification_bits"] > 0, (
        "fully residual probe must have positive residual bits"
    )
    assert baseline_probe["residual_identification_bits"] == 0.0, (
        "baseline-explained probe must have 0 residual bits"
    )

    # Ranking: residual probe is first
    assert ranked[0]["probe"] == "cell_row_99_col_99", (
        f"residual probe must rank above baseline probe; got {ranked[0]['probe']}"
    )
    # Both raw and residual bits are present in output
    for r in ranked:
        assert "raw_identification_bits" in r
        assert "residual_identification_bits" in r
        assert r["baseline_ref"] == "arc_agi.test_champion_visible_replay.v1"
