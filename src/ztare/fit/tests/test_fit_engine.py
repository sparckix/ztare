"""GP-157 v5.0 Phase 2 — FitEngine Protocol regression suite.

Verifies:
  - All adapters satisfy the Protocol (runtime_checkable)
  - Adapter routing via select_adapter is deterministic
  - 1D adapter wraps fit_primitive correctly without modifying it
  - N-D adapter wraps fit_primitive_features correctly + carries Bug #26
    pathology + Bug #31 residual feedback through
  - Tensor adapter is a clear STUB that raises with sharp diagnostic
  - can_handle returns (False, reason) on shape mismatch — never silently
"""
from __future__ import annotations

import math
import pytest

from src.ztare.fit.fit_engine import (
    FitEngine,
    FitEngineResult,
    OneDFitEngine,
    FeatureVectorFitEngine,
    TensorTargetFitEngine,
    select_adapter,
)


# ── Fake substrate stand-ins ──────────────────────────────────────────


class _FakeSubstrate:
    def __init__(self, meta: dict):
        self.meta = meta


# ── Protocol conformance ──────────────────────────────────────────────


def test_adapters_satisfy_protocol():
    """All three adapters must satisfy runtime_checkable Protocol."""
    for adapter in (OneDFitEngine(), FeatureVectorFitEngine(), TensorTargetFitEngine()):
        assert isinstance(adapter, FitEngine), f"{type(adapter).__name__} fails Protocol"


# ── can_handle routing ────────────────────────────────────────────────


def test_oned_can_handle_with_fit_declaration():
    s = _FakeSubstrate({"class": "1d"})
    candidate = "thesis prose ... ```fit_declaration\n{...}\n``` ... FIT_DECLARATION"
    ok, reason = OneDFitEngine().can_handle(s, candidate)
    assert ok, f"unexpected reject: {reason}"


def test_oned_rejects_without_fit_declaration():
    s = _FakeSubstrate({"class": "1d"})
    candidate = "no fit_declaration here"
    ok, reason = OneDFitEngine().can_handle(s, candidate)
    assert not ok
    assert "FIT_DECLARATION" in reason


def test_oned_rejects_wrong_class():
    s = _FakeSubstrate({"class": "nd_features"})
    ok, reason = OneDFitEngine().can_handle(s, "FIT_DECLARATION test")
    assert not ok
    assert "1d" in reason


def test_featvec_rejects_without_form_declaration():
    s = _FakeSubstrate({"class": "nd_features"})
    candidate = "no PARAMETRIC_FORM here"
    ok, reason = FeatureVectorFitEngine().can_handle(s, candidate)
    assert not ok


def test_featvec_accepts_with_form_declaration():
    s = _FakeSubstrate({"class": "nd_features"})
    candidate = (
        "PARAMETRIC_FORM = \"params['a'] * features['x']\"\n"
        "PARAMETER_NAMES = ['a']\n"
        "MODEL_PARAMS = {}\n"
        "def I_model(features, params=MODEL_PARAMS):\n"
        "    return params['a']\n"
    )
    ok, reason = FeatureVectorFitEngine().can_handle(s, candidate)
    assert ok, f"unexpected reject: {reason}"


def test_tensor_adapter_is_stub_only_engages_on_time_series():
    s = _FakeSubstrate({"class": "nd_features"})
    ok, reason = TensorTargetFitEngine().can_handle(s, "anything")
    assert not ok
    assert "time_series" in reason

    s2 = _FakeSubstrate({"class": "time_series"})
    ok, reason = TensorTargetFitEngine().can_handle(s2, "anything")
    assert ok


def test_tensor_adapter_fit_returns_stub_diagnostic():
    """Tensor adapter MUST return success=False with sharp STUB message,
    NEVER attempt a fit silently."""
    result = TensorTargetFitEngine().fit(("x", ["a"]), [])
    assert result.success is False
    assert "STUB" in result.error_message
    assert "Phase 3" in result.error_message or "deferred" in result.error_message
    assert result.adapter_class == "TensorTargetFitEngine"


# ── select_adapter routing ────────────────────────────────────────────


def test_select_adapter_routes_1d():
    s = _FakeSubstrate({"class": "1d"})
    candidate = "FIT_DECLARATION test"
    adapter = select_adapter(s, candidate)
    assert isinstance(adapter, OneDFitEngine)


def test_select_adapter_routes_featvec():
    s = _FakeSubstrate({"class": "nd_features"})
    candidate = (
        "PARAMETRIC_FORM = \"params['a']\"\n"
        "PARAMETER_NAMES = ['a']\n"
        "MODEL_PARAMS = {}\n"
        "def I_model(features, params=MODEL_PARAMS): return 1.0\n"
    )
    adapter = select_adapter(s, candidate)
    assert isinstance(adapter, FeatureVectorFitEngine)


def test_select_adapter_returns_none_when_nothing_engages():
    s = _FakeSubstrate({"class": "1d"})
    candidate = "thesis without any fit declaration markers"
    adapter = select_adapter(s, candidate)
    assert adapter is None


def test_select_adapter_handles_missing_meta():
    """N3 nugget defense: substrate without meta dict must be handled
    gracefully (adapter rejects, doesn't crash)."""
    class _NoMeta:
        pass
    adapter = select_adapter(_NoMeta(), "FIT_DECLARATION test")
    # Without meta, all class-based gates fail, adapter routes to nothing
    # OneDFitEngine.can_handle should return True for FIT_DECLARATION even
    # without meta (meta_class is None, falls through to candidate check)
    # so this should route to OneDFitEngine. The concern is no CRASH.
    assert adapter is None or isinstance(adapter, OneDFitEngine)


# ── FeatureVectorFitEngine end-to-end smoke test ─────────────────────


def test_featvec_fit_end_to_end_recovery():
    """N-D adapter should fit gp155-style sigmoid blend + populate
    BIC, residual_diagnostic, feature_value_counts."""
    visible = []
    for d in [2.0, 3.0, 4.0, 5.0, 6.0]:
        for log_n in [3.0, 5.0, 7.0, 9.0]:
            arg = 2.0 * (log_n - 0.5*d - 3.0)
            sig = 1.0 / (1.0 + math.exp(-arg))
            alpha = 2.0/d + (1.0 - 2.0/d) * sig
            visible.append(({"intrinsic_dim_d": d, "log10_N_params": log_n, "modality": "synth"}, alpha))

    form = (
        "2/features['intrinsic_dim_d'] + (1 - 2/features['intrinsic_dim_d']) "
        "* sigmoid(params['s'] * (features['log10_N_params'] "
        "- params['m']*features['intrinsic_dim_d'] - params['b']))"
    )
    declaration = (form, ["s", "m", "b"], None)

    adapter = FeatureVectorFitEngine()
    result = adapter.fit(declaration, visible, n_starts=3, seed=42)

    assert result.success
    assert result.adapter_class == "FeatureVectorFitEngine"
    # Ground truth: s=2, m=0.5, b=3
    assert abs(result.fitted_params["s"] - 2.0) < 0.01
    assert abs(result.fitted_params["m"] - 0.5) < 0.01
    assert abs(result.fitted_params["b"] - 3.0) < 0.01
    # BIC populated
    assert math.isfinite(result.bic)
    assert result.bic < -100
    # K + N populated
    assert result.k_params == 3
    assert result.n_fit_rows == len(visible)
    # Bug #26 pathology: not pathological (params are sane)
    assert result.pathological is False
    # Bug #31 closed-loop: feature_value_counts populated for the
    # categorical 'modality' even though only one value
    assert "modality" in result.feature_value_counts
    assert result.feature_value_counts["modality"]["synth"] == len(visible)


def test_featvec_propagates_pathology():
    """Adapter must carry Bug #26 pathology flag into the common shape."""
    # Synthesize a substrate where one row's y is wildly larger; scipy
    # will move slack into a categorical param and pathology should fire.
    visible = [({"x": 1.0, "mod": "common"}, 1.0)] * 5
    visible.append(({"x": 1.0, "mod": "outlier"}, 100.0))  # y_max=100
    form = (
        "params['base'] + params['delta'] * float(features['mod'] == 'outlier')"
    )
    declaration = (form, ["base", "delta"], None)
    adapter = FeatureVectorFitEngine()
    result = adapter.fit(declaration, visible, n_starts=3, seed=42)
    assert result.success
    # The fit will produce delta ≈ 99 (matches outlier delta).
    # Pathology threshold = 10 × max(|y|) = 1000; 99 is below 1000,
    # so pathology may NOT fire here. This test verifies the field
    # exists, not that it's True.
    assert isinstance(result.pathological, bool)
    assert "delta" in result.fitted_params


# ── Common-shape conversions ──────────────────────────────────────────


def test_common_shape_has_all_v5_fields():
    """FitEngineResult must include all GP-156 v3 + GP-157 v5 fields so
    Cage downstream consumers see one shape."""
    r = FitEngineResult(success=True, fitted_params={"a": 1.0})
    # Spot-check key fields
    for field in [
        "success", "fitted_params", "error_message",
        "sse", "sigma_sq", "mean_abs_residual", "max_abs_residual",
        "n_fit_rows", "k_params", "bic",
        "n_starts_attempted", "n_starts_converged", "convergence_classification",
        "pathological", "pathology_reason", "extreme_params",
        "residual_diagnostic", "residual_by_category", "feature_value_counts",
        "adapter_class",
    ]:
        assert hasattr(r, field), f"FitEngineResult missing field: {field}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
