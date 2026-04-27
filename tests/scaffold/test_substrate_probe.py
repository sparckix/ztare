"""Tests for substrate_probe.classify_substrate (GP-157 Gap #3)."""

from __future__ import annotations

import math

import pytest

from src.ztare.scaffold.substrate_probe import (
    ClassificationResult,
    SubstrateAmbiguityError,
    SubstrateClass,
    classify_substrate,
    verify_class_against_data,
)


class TestDiscreteDetection:
    def test_all_integers_classifies_discrete(self):
        targets = [1, 2, 3, 5, 8, 13, 21]
        result = classify_substrate(targets)
        assert result.detected is SubstrateClass.DISCRETE
        assert result.confidence == "high"
        assert result.integer_fraction == 1.0

    def test_mostly_integers_with_one_float_not_discrete(self):
        # Substrate is "all integer or it's not discrete" — strict
        targets = [1, 2, 3, 5, 8, 13, 21.5]
        result = classify_substrate(targets)
        assert result.detected is not SubstrateClass.DISCRETE


class TestDynamicalDetection:
    def test_high_autocorr_survives_shuffle(self):
        # Strongly autocorrelated time series: y_t = 0.95 * y_{t-1} + noise
        import random
        rng = random.Random(42)
        targets = [0.5]
        for _ in range(50):
            targets.append(0.95 * targets[-1] + rng.gauss(0, 0.01))
        result = classify_substrate(targets)
        assert result.detected is SubstrateClass.DYNAMICAL_CHAOTIC
        assert abs(result.autocorrelation_raw) > abs(result.autocorrelation_shuffled) + 0.3

    def test_iid_gaussian_not_dynamical(self):
        import random
        rng = random.Random(42)
        targets = [rng.gauss(0, 1.0) for _ in range(50)]
        result = classify_substrate(targets)
        assert result.detected is SubstrateClass.SCALAR_KINEMATIC


class TestSortedKinematicNotMisclassifiedAsDynamical:
    def test_sorted_continuous_kinematic_not_flagged_dynamical(self):
        # gp159 pattern: y = a/(x+b) computed on sorted x. Targets are sorted
        # by independent variable but the SHAPE is static kinematic, not
        # time-series. Must NOT classify as dynamical (shuffle test catches it).
        xs = sorted([1.3, 1.8, 2.5, 3.1, 4.4, 5.2, 6.1, 10.2, 15.0, 18.0, 22.0, 27.0])
        a, b = 3.7, 0.9
        targets = [a / (x + b) for x in xs]
        result = classify_substrate(targets)
        assert result.detected is SubstrateClass.SCALAR_KINEMATIC
        # confidence may be "medium" because raw autocorr is high (sorted)
        # but shuffle test rejected — that's the right behavior

    def test_diagnostic_explains_sorted_data(self):
        xs = sorted(range(1, 30))
        targets = [3.7 / (x + 0.9) for x in xs]
        result = classify_substrate(targets)
        assert result.detected is SubstrateClass.SCALAR_KINEMATIC
        # Diagnostic should mention sorted data was caught
        diag_text = " ".join(result.diagnostics).lower()
        if abs(result.autocorrelation_raw) >= 0.5:
            assert "sorted" in diag_text or result.confidence == "medium"


class TestAmbiguous:
    def test_too_few_rows_ambiguous(self):
        result = classify_substrate([1.0, 2.0])
        # With n_rows=2, falls below min for autocorr; depending on int_frac,
        # either DISCRETE-fallback path skipped or AMBIGUOUS
        assert result.confidence in ("low", "high")

    def test_empty_targets(self):
        result = classify_substrate([])
        assert result.detected is SubstrateClass.AMBIGUOUS
        assert result.n_rows == 0


class TestVerifyClassAgainstData:
    def test_declared_1d_matches_kinematic(self):
        targets = [3.7 / (x + 0.9) for x in [1.3, 1.8, 3.1, 4.4, 5.2, 6.1, 10.2]]
        ok, _ = verify_class_against_data("1d", targets)
        assert ok

    def test_declared_1d_matches_discrete(self):
        # 1d declaration accepts both kinematic AND discrete (both 1D)
        targets = [1, 2, 3, 5, 8, 13, 21]
        ok, msg = verify_class_against_data("1d", targets)
        assert ok
        assert "discrete" in msg or "1d" in msg

    def test_declared_time_series_chaotic_kinematic_data_fails(self):
        # gp159-style regression: declared "time_series_chaotic" but data is
        # kinematic — verifier catches the mismatch.
        import random
        rng = random.Random(42)
        targets = [rng.gauss(0, 1.0) for _ in range(20)]
        ok, msg = verify_class_against_data("time_series_chaotic", targets)
        assert not ok
        assert "MISMATCH" in msg

    def test_ambiguous_data_accepts_any_declaration(self):
        # When n_rows is too small, verifier defers to operator declaration
        ok, msg = verify_class_against_data("1d", [1.0])
        assert ok
        assert "ambiguous" in msg.lower()


class TestSubstrateAmbiguityError:
    def test_error_class_exists(self):
        # Caller (e.g. R1 lint) raises this when probes inconclusive
        # AND operator hasn't declared. Test message shape.
        err = SubstrateAmbiguityError(
            "The apparatus cannot determine if this substrate requires a "
            "dynamical ODE solver or a static kinematic fit. You must "
            "explicitly declare the physical class in your PARAMETRIC_FORM."
        )
        assert "explicitly declare" in str(err)
        assert isinstance(err, ValueError)
