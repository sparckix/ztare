"""Tests for GP-098 Evidence Compressor.

Three synthetic validation substrates per spec:
1. Homoscedastic baseline: Z = a*exp(-b*X) + c, noise ~ N(0, 0.1)
2. Multiplicative noise:   Z = a*exp(-b*X) + c, noise ~ N(0, 0.1*Z)
3. Poisson noise:          Z = a*X^2 + b*X + c, noise ~ N(0, sqrt(Z))

Plus edge cases: empty evidence, negative Z, near-zero Z.
"""

import math
import pytest

from ztare.findings.evidence_compressor import (
    TransformedEvidence,
    enumerate_transforms,
    evaluate_holdout_in_original,
    inverse_transform_predictions,
    Z_FLOOR,
)

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence_1d(
    f, x_range, n=30, noise_fn=None, seed=42,
) -> list[tuple[float, float]]:
    """Generate 1D (X, Z) evidence with optional noise."""
    rng = np.random.default_rng(seed)
    xs = np.linspace(*x_range, n)
    evidence = []
    for x in xs:
        z = f(x)
        if noise_fn is not None:
            z += noise_fn(z, rng)
        evidence.append((float(x), float(z)))
    return evidence


# ---------------------------------------------------------------------------
# Basic enumeration tests
# ---------------------------------------------------------------------------


class TestEnumerateTransforms:
    def test_all_positive_z_returns_three_transforms(self):
        evidence = [(1.0, 4.0), (2.0, 9.0), (3.0, 16.0)]
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert names == ["identity", "log", "sqrt"]

    def test_negative_z_skips_log_and_sqrt(self):
        evidence = [(1.0, -2.0), (2.0, 3.0), (3.0, 5.0)]
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert "identity" in names
        assert "log" not in names
        assert "sqrt" not in names

    def test_zero_z_skips_log_keeps_sqrt(self):
        evidence = [(1.0, 0.0), (2.0, 4.0), (3.0, 9.0)]
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert "identity" in names
        assert "log" not in names
        assert "sqrt" in names

    def test_near_zero_z_skips_log(self):
        """Z values below Z_FLOOR should trigger the domain guard."""
        evidence = [(1.0, Z_FLOOR / 2), (2.0, 4.0)]
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert "log" not in names

    def test_empty_evidence(self):
        result = enumerate_transforms([], verbose=False)
        assert len(result) == 1
        assert result[0].transform_name == "identity"

    def test_identity_is_always_first(self):
        evidence = [(1.0, 4.0), (2.0, 9.0)]
        result = enumerate_transforms(evidence, verbose=False)
        assert result[0].transform_name == "identity"


class TestTransformInverses:
    """Each transform's inverse must be exact."""

    def test_identity_roundtrip(self):
        evidence = [(1.0, 42.5), (2.0, -3.7)]
        result = enumerate_transforms(evidence, verbose=False)
        identity = result[0]
        for e in evidence:
            z = e[-1]
            z_prime = identity.forward_fn(z)
            z_back = identity.inverse_fn(z_prime)
            assert abs(z - z_back) < 1e-12

    def test_log_roundtrip(self):
        evidence = [(1.0, 2.5), (2.0, 100.0)]
        result = enumerate_transforms(evidence, verbose=False)
        log_t = [t for t in result if t.transform_name == "log"][0]
        for e in evidence:
            z = e[-1]
            z_prime = log_t.forward_fn(z)
            z_back = log_t.inverse_fn(z_prime)
            assert abs(z - z_back) < 1e-10

    def test_sqrt_roundtrip(self):
        evidence = [(1.0, 4.0), (2.0, 25.0)]
        result = enumerate_transforms(evidence, verbose=False)
        sqrt_t = [t for t in result if t.transform_name == "sqrt"][0]
        for e in evidence:
            z = e[-1]
            z_prime = sqrt_t.forward_fn(z)
            z_back = sqrt_t.inverse_fn(z_prime)
            assert abs(z - z_back) < 1e-10


class TestTransformedEvidenceValues:
    """Verify that the transformed evidence has correct Z' values."""

    def test_log_transforms_z(self):
        evidence = [(1.0, math.e), (2.0, math.e ** 2)]
        result = enumerate_transforms(evidence, verbose=False)
        log_t = [t for t in result if t.transform_name == "log"][0]
        assert abs(log_t.evidence[0][-1] - 1.0) < 1e-10
        assert abs(log_t.evidence[1][-1] - 2.0) < 1e-10

    def test_sqrt_transforms_z(self):
        evidence = [(1.0, 4.0), (2.0, 9.0)]
        result = enumerate_transforms(evidence, verbose=False)
        sqrt_t = [t for t in result if t.transform_name == "sqrt"][0]
        assert abs(sqrt_t.evidence[0][-1] - 2.0) < 1e-10
        assert abs(sqrt_t.evidence[1][-1] - 3.0) < 1e-10

    def test_x_values_unchanged(self):
        """X values should pass through untouched."""
        evidence = [(1.5, 3.3, 4.0), (2.7, 1.1, 9.0)]
        result = enumerate_transforms(evidence, verbose=False)
        for t in result:
            for orig, trans in zip(evidence, t.evidence):
                # X values (all but last) should be identical
                assert orig[:-1] == trans[:-1]


# ---------------------------------------------------------------------------
# Inverse transform + holdout evaluation
# ---------------------------------------------------------------------------


class TestInverseTransformPredictions:
    def test_identity(self):
        t = TransformedEvidence(
            transform_name="identity",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z: z,
            forward_fn=lambda z: z,
        )
        preds = [1.0, 2.0, 3.0]
        result = inverse_transform_predictions(preds, t)
        assert result == preds

    def test_log_inverse(self):
        t = TransformedEvidence(
            transform_name="log",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z_prime: math.exp(z_prime),
            forward_fn=lambda z: math.log(z),
        )
        # log inverse: exp(0) = 1, exp(1) ≈ 2.718
        result = inverse_transform_predictions([0.0, 1.0], t)
        assert abs(result[0] - 1.0) < 1e-10
        assert abs(result[1] - math.e) < 1e-10


class TestEvaluateHoldoutInOriginal:
    def test_perfect_predictions(self):
        t = TransformedEvidence(
            transform_name="identity",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z: z,
            forward_fn=lambda z: z,
        )
        res = evaluate_holdout_in_original([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], t)
        assert res < 1e-10

    def test_imperfect_predictions(self):
        t = TransformedEvidence(
            transform_name="identity",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z: z,
            forward_fn=lambda z: z,
        )
        res = evaluate_holdout_in_original([1.1, 2.0, 3.0], [1.0, 2.0, 3.0], t)
        assert abs(res - 0.1) < 1e-10

    def test_mismatched_lengths(self):
        t = TransformedEvidence(
            transform_name="identity",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z: z,
            forward_fn=lambda z: z,
        )
        res = evaluate_holdout_in_original([1.0], [1.0, 2.0], t)
        assert res == float("inf")

    def test_log_transform_holdout(self):
        """Holdout evaluation through log inverse."""
        t = TransformedEvidence(
            transform_name="log",
            evidence=[],
            original_evidence=[],
            inverse_fn=lambda z_prime: math.exp(z_prime),
            forward_fn=lambda z: math.log(z),
        )
        # Predict Z'=0.0 (meaning Z=1.0), holdout Z_obs=1.0
        res = evaluate_holdout_in_original([0.0], [1.0], t)
        assert res < 1e-10


# ---------------------------------------------------------------------------
# Substrate tests (require numpy)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestSubstrate1Homoscedastic:
    """Substrate 1: Z = 3*exp(-0.5*X) + 1, noise ~ N(0, 0.1)."""

    @pytest.fixture
    def evidence(self):
        def f(x):
            return 3.0 * math.exp(-0.5 * x) + 1.0

        return _make_evidence_1d(
            f, (0.1, 8.0), n=30,
            noise_fn=lambda z, rng: rng.normal(0, 0.1),
        )

    def test_all_transforms_available(self, evidence):
        """All Z > 0 for this substrate, so all three should be available."""
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert "identity" in names
        assert "log" in names
        assert "sqrt" in names

    def test_identity_evidence_unchanged(self, evidence):
        result = enumerate_transforms(evidence, verbose=False)
        identity = result[0]
        for orig, trans in zip(evidence, identity.evidence):
            assert orig == trans


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestSubstrate2MultiplicativeNoise:
    """Substrate 2: Z = 3*exp(-0.5*X) + 1, noise ~ N(0, 0.1*Z)."""

    @pytest.fixture
    def evidence(self):
        def f(x):
            return 3.0 * math.exp(-0.5 * x) + 1.0

        return _make_evidence_1d(
            f, (0.1, 8.0), n=30,
            noise_fn=lambda z, rng: rng.normal(0, 0.1 * abs(z)),
        )

    def test_log_transform_stabilizes_variance(self, evidence):
        """Log transform should reduce variance spread across the domain."""
        result = enumerate_transforms(evidence, verbose=False)
        log_t = [t for t in result if t.transform_name == "log"]
        assert len(log_t) == 1

        # Check that Z' range is compressed relative to Z range
        z_range = max(e[-1] for e in evidence) - min(e[-1] for e in evidence)
        z_prime_range = (
            max(e[-1] for e in log_t[0].evidence)
            - min(e[-1] for e in log_t[0].evidence)
        )
        # Log compression: z_prime_range should be smaller
        assert z_prime_range < z_range


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy required")
class TestSubstrate3PoissonNoise:
    """Substrate 3: Z = 0.5*X^2 + 2*X + 5, noise ~ N(0, sqrt(Z))."""

    @pytest.fixture
    def evidence(self):
        def f(x):
            return 0.5 * x ** 2 + 2.0 * x + 5.0

        return _make_evidence_1d(
            f, (0.1, 10.0), n=30,
            noise_fn=lambda z, rng: rng.normal(0, math.sqrt(abs(z))),
        )

    def test_sqrt_transform_available(self, evidence):
        result = enumerate_transforms(evidence, verbose=False)
        names = [t.transform_name for t in result]
        assert "sqrt" in names

    def test_sqrt_roundtrip_on_evidence(self, evidence):
        """Forward + inverse should reproduce original Z."""
        result = enumerate_transforms(evidence, verbose=False)
        sqrt_t = [t for t in result if t.transform_name == "sqrt"][0]
        for orig in evidence:
            z = orig[-1]
            if z >= 0:
                z_prime = sqrt_t.forward_fn(z)
                z_back = sqrt_t.inverse_fn(z_prime)
                assert abs(z - z_back) < 1e-10
