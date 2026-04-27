"""GP-157 v5.0 Phase 1 — substrate_evaluation regression suite."""
from __future__ import annotations

import math
import pytest

from src.ztare.gates.substrate_evaluation import (
    EvalResult,
    evaluate_set,
    assert_or_propagate_defect,
    to_canonical_schema,
)


# Stub features module
class _FeatsModule:
    def __init__(self, table: dict[int, dict]):
        self._t = table

    def get_features(self, row_id: int) -> dict:
        if row_id not in self._t:
            raise KeyError(row_id)
        return self._t[row_id]


# ── evaluate_set basic correctness ────────────────────────────────────


def test_evaluate_set_pass():
    """All predictions exact → mean_re=0 → passed=True."""
    feats = _FeatsModule({0: {"x": 1.0}, 1: {"x": 2.0}, 2: {"x": 3.0}})
    rows = [(0, 1.0), (1, 2.0), (2, 3.0)]
    i_model = lambda f: f["x"]
    result = evaluate_set(rows, i_model, feats, threshold=0.1)
    assert result.passed is True
    assert result.near_miss is False
    assert result.mean_relative_error == 0.0
    assert result.crash_count == 0


def test_evaluate_set_near_miss():
    """Model off by ~30% → fails 0.25 threshold but inside 1.5×=0.375 band."""
    feats = _FeatsModule({i: {"x": float(i)} for i in range(5)})
    rows = [(i, float(i)) for i in range(1, 5)]  # skip 0 (zero division)
    i_model = lambda f: f["x"] * 1.30  # 30% over
    result = evaluate_set(rows, i_model, feats, threshold=0.25, near_miss_factor=1.5)
    assert result.passed is False
    assert result.near_miss is True
    assert 0.25 <= result.mean_relative_error < 0.375


def test_evaluate_set_hard_miss():
    """Model off by 200% → mean_re ≫ 1.5×threshold → near_miss=False."""
    feats = _FeatsModule({i: {"x": float(i)} for i in range(5)})
    rows = [(i, float(i)) for i in range(1, 5)]
    i_model = lambda f: f["x"] * 3.0  # 200% over
    result = evaluate_set(rows, i_model, feats, threshold=0.25)
    assert result.passed is False
    assert result.near_miss is False


def test_evaluate_set_crash_detection():
    """Model raises on every row → crash_rate=1.0; per_row records exception class."""
    feats = _FeatsModule({0: {"x": 1.0}, 1: {"x": 2.0}})
    rows = [(0, 1.0), (1, 2.0)]
    i_model = lambda f: 1 / 0  # ZeroDivisionError on every row
    result = evaluate_set(rows, i_model, feats, threshold=0.25)
    assert result.crash_rate == 1.0
    assert result.crash_count == 2
    assert "ZeroDivisionError" in result.crash_classes
    assert result.crash_classes["ZeroDivisionError"] == 2


def test_evaluate_set_partial_crash():
    """Model raises on half rows; crash_rate=0.5, but mean_re computed over all (with rel_err=1 for crashed)."""
    feats = _FeatsModule({i: {"x": float(i + 1)} for i in range(4)})
    rows = [(i, float(i + 1)) for i in range(4)]
    def i_model(f):
        if f["x"] > 2:
            raise ValueError("synthetic crash")
        return f["x"]
    result = evaluate_set(rows, i_model, feats, threshold=0.25)
    assert result.crash_count == 2
    assert result.crash_rate == 0.5


def test_evaluate_set_nan_handling():
    """NaN/Inf predictions counted as nonfinite, rel_err=1.0."""
    feats = _FeatsModule({0: {"x": 1.0}, 1: {"x": 2.0}})
    rows = [(0, 1.0), (1, 2.0)]
    i_model = lambda f: float("nan")
    result = evaluate_set(rows, i_model, feats, threshold=0.25)
    assert result.nonfinite_count == 2
    assert result.crash_rate == 1.0  # nonfinite counts toward crash_rate


# ── residual breakdown by category (Bug #31 closed-loop) ──────────────


def test_residual_breakdown_identifies_failing_category():
    """Inject one categorical group with bad fit; breakdown surfaces it."""
    feats = _FeatsModule({
        0: {"mod": "good", "x": 1.0},
        1: {"mod": "good", "x": 2.0},
        2: {"mod": "good", "x": 3.0},
        3: {"mod": "bad", "x": 100.0},  # outlier
    })
    rows = [(0, 1.0), (1, 2.0), (2, 3.0), (3, 4.0)]
    i_model = lambda f: f["x"]  # off only on row 3
    result = evaluate_set(rows, i_model, feats, threshold=0.25)
    assert "mod" in result.residual_by_category
    bad = result.residual_by_category["mod"]["bad"]
    good = result.residual_by_category["mod"]["good"]
    assert bad["mean_abs_res"] > good["mean_abs_res"]
    assert bad["n"] == 1
    assert good["n"] == 3


# ── assert_or_propagate_defect ────────────────────────────────────────


def test_assert_or_propagate_passes_clean():
    """Clean pass → no exception."""
    result = EvalResult(n=4, mean_relative_error=0.05, max_relative_error=0.1,
                         passed=True, threshold=0.25)
    assert_or_propagate_defect(result, "HOLDOUT")  # no raise


def test_assert_or_propagate_runtime_error_on_crash():
    """High crash_rate → RuntimeError with sharp diagnostic."""
    result = EvalResult(n=10, mean_relative_error=1.0, max_relative_error=1.0,
                         crash_count=10, crash_rate=1.0,
                         crash_classes={"KeyError": 10},
                         passed=False, threshold=0.25)
    with pytest.raises(RuntimeError, match="harness defect|crashed"):
        assert_or_propagate_defect(result, "HOLDOUT")


def test_assert_or_propagate_assertion_error_on_failure():
    """Low crash_rate + miss → AssertionError with [hard_miss] tag."""
    result = EvalResult(n=10, mean_relative_error=1.5, max_relative_error=2.0,
                         passed=False, near_miss=False, threshold=0.25,
                         near_miss_factor=1.5)
    with pytest.raises(AssertionError, match="hard_miss|FAILED"):
        assert_or_propagate_defect(result, "HOLDOUT")


def test_assert_or_propagate_near_miss_tag():
    """Near miss should produce REFINE-not-redesign tag."""
    result = EvalResult(n=10, mean_relative_error=0.30, max_relative_error=0.5,
                         passed=False, near_miss=True, threshold=0.25,
                         near_miss_factor=1.5)
    with pytest.raises(AssertionError, match="near_miss|REFINE"):
        assert_or_propagate_defect(result, "FARTHER_TAIL")


def test_assert_or_propagate_preflight_skip():
    """Pre-flight skips both defect and falsification raises."""
    # Crash-rate path
    r1 = EvalResult(n=10, mean_relative_error=1.0, max_relative_error=1.0,
                    crash_count=10, crash_rate=1.0, passed=False, threshold=0.25)
    assert_or_propagate_defect(r1, "HOLDOUT", is_preflight=True)
    # Hard-miss path
    r2 = EvalResult(n=10, mean_relative_error=1.0, max_relative_error=1.0,
                    passed=False, threshold=0.25)
    assert_or_propagate_defect(r2, "HOLDOUT", is_preflight=True)


# ── canonical schema (Bug #21 unification) ────────────────────────────


def test_canonical_schema_includes_legacy_keys():
    """Schema must include BOTH legacy `harness_ok`/`gates` AND v5 keys."""
    r = EvalResult(n=10, mean_relative_error=0.05, max_relative_error=0.1,
                    passed=True, threshold=0.25)
    out = to_canonical_schema({"holdout": r})
    # Legacy keys
    assert out["harness_ok"] is True
    assert isinstance(out["gates"], list)
    assert out["gates"][0]["name"] == "HOLDOUT"
    assert out["gates"][0]["passed"] is True
    # v5 keys
    assert "holdout" in out
    assert out["holdout"]["passed"] is True
    assert out["all_gates_pass"] is True
    assert out["any_near_miss"] is False


def test_canonical_schema_two_gates_one_near_miss():
    r1 = EvalResult(n=10, mean_relative_error=0.05, max_relative_error=0.1,
                     passed=True, near_miss=False, threshold=0.25)
    r2 = EvalResult(n=10, mean_relative_error=0.30, max_relative_error=0.4,
                     passed=False, near_miss=True, threshold=0.25)
    out = to_canonical_schema({"holdout": r1, "farther_tail": r2})
    assert out["all_gates_pass"] is False
    assert out["any_near_miss"] is True


def test_canonical_schema_extra_fields_merged():
    r = EvalResult(n=10, mean_relative_error=0.05, max_relative_error=0.1,
                    passed=True, threshold=0.25)
    out = to_canonical_schema({"holdout": r}, extra_fields={"asymptotic_bound": {"passed": True}})
    assert "asymptotic_bound" in out
    assert out["asymptotic_bound"]["passed"] is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
