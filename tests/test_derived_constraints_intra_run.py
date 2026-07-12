"""Test derived constraints intra-run confirmation via distinct (run_id, iteration) pairs."""
from __future__ import annotations

import tempfile
from pathlib import Path

from ztare.gates.derived_constraints import update_derived_constraints_ledger


def test_intra_run_same_signature_distinct_iterations_confirms():
    """
    Same signature emitted at (run_id=R, iter=0) and (run_id=R, iter=1)
    should confirm (count 2). Distinct observations within same run count.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "workspace" / "derived_constraints.json"

        # First iteration of run R
        result_iter0 = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "Test constraint A",
                    "applies_to": "test scope",
                    "failure_family": "test_family",
                }
            ],
            run_id=100,
            iteration_index=0,
            source_score=50,
            weakest_point="test point 1",
            score_regime_fingerprint="fp1",
        )

        # Same constraint in second iteration of same run R
        result_iter1 = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "Test constraint A",
                    "applies_to": "test scope",
                    "failure_family": "test_family",
                }
            ],
            run_id=100,
            iteration_index=1,
            source_score=55,
            weakest_point="test point 2",
            score_regime_fingerprint="fp1",
        )

        # After two iterations of same run, constraint should be confirmed
        assert result_iter1["confirmed_constraint_count"] == 1
        assert result_iter1["provisional_constraint_count"] == 0
        confirmed = result_iter1["confirmed_constraints"][0]
        assert confirmed["seen_count_runs"] == 2  # Two distinct (run_id, iteration) pairs
        assert confirmed["status"] == "confirmed"


def test_same_iteration_duplicate_does_not_double_count():
    """
    Same signature emitted twice at (run_id=R, iter=0) should stay provisional
    (count 1, dedup). Duplicates within same observation point don't increase count.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "workspace" / "derived_constraints.json"

        # Two identical proposals in the same iteration
        result = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "Test constraint B",
                    "applies_to": "test scope",
                    "failure_family": "test_family",
                },
                {
                    "constraint": "Test constraint B",
                    "applies_to": "test scope",
                    "failure_family": "test_family",
                },
            ],
            run_id=200,
            iteration_index=0,
            source_score=60,
            weakest_point="test point",
            score_regime_fingerprint="fp2",
        )

        # Should still be provisional (only one distinct observation)
        assert result["confirmed_constraint_count"] == 0
        assert result["provisional_constraint_count"] == 1
        provisional = result["provisional_constraints"][0]
        assert provisional["seen_count_runs"] == 1
        assert provisional["status"] == "provisional"


def test_cross_run_confirmation_still_works():
    """
    Regression test: cross-run confirmation must still work.
    Same signature at (run_id=R1, iter=0) + (run_id=R2, iter=0) should confirm.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "workspace" / "derived_constraints.json"

        # First run
        result_run1 = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "Cross-run constraint",
                    "applies_to": "test scope",
                    "failure_family": "cross_family",
                }
            ],
            run_id=1000,
            iteration_index=0,
            source_score=70,
            weakest_point="test point run1",
            score_regime_fingerprint="fp3",
        )

        # Second run
        result_run2 = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[
                {
                    "constraint": "Cross-run constraint",
                    "applies_to": "test scope",
                    "failure_family": "cross_family",
                }
            ],
            run_id=2000,
            iteration_index=0,
            source_score=75,
            weakest_point="test point run2",
            score_regime_fingerprint="fp3",
        )

        # After two distinct runs, constraint should be confirmed
        assert result_run2["confirmed_constraint_count"] == 1
        assert result_run2["provisional_constraint_count"] == 0
        confirmed = result_run2["confirmed_constraints"][0]
        assert confirmed["seen_count_runs"] == 2
        assert confirmed["status"] == "confirmed"


def test_mixed_intra_and_cross_run_confirmation():
    """
    Multiple iterations in run R1 + different run R2 should confirm.
    Exercises both intra-run and cross-run counting simultaneously.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "workspace" / "derived_constraints.json"

        proposal = {
            "constraint": "Mixed constraint",
            "applies_to": "test scope",
            "failure_family": "mixed_family",
        }

        # Run R1, iteration 0
        update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[proposal],
            run_id=3000,
            iteration_index=0,
            source_score=40,
            weakest_point="mixed run1 iter0",
            score_regime_fingerprint="fp4",
        )

        # Run R1, iteration 1 (still provisional after 1 observation within run)
        result_r1_i1 = update_derived_constraints_ledger(
            project="test_project",
            ledger_path=ledger_path,
            proposals=[proposal],
            run_id=3000,
            iteration_index=1,
            source_score=45,
            weakest_point="mixed run1 iter1",
            score_regime_fingerprint="fp4",
        )
        # At this point: 2 observations (R1,I0) and (R1,I1) -> confirmed
        assert result_r1_i1["confirmed_constraint_count"] == 1
        assert result_r1_i1["provisional_constraint_count"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
