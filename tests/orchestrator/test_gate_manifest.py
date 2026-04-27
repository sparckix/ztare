"""Tests for src/ztare/orchestrator/gate_manifest.py — Layer 3 declarative
gate manifest. Validates closed-set GateType enum, strict-typed
validate_gate_spec parameter checking, and the three reference impls
(BOUNDS_CHECK, HOLDOUT_MRE, ANTI_RETRIEVAL).

Per Gemini Pro panel: this module is the iatrogenic-free fix for the
gp160-class intent/mechanism translation gap. Tests must lock the
strict-no-extras / strict-no-missing / strict-types invariants so
operator typos and rubric drift fail at seal time, not at runtime.
"""
from __future__ import annotations

import math

import pytest

from src.ztare.orchestrator.gate_manifest import (
    GATE_REGISTRY,
    PARAMETER_SCHEMAS,
    EvaluativeGateSpec,
    GateContractError,
    GateType,
    evaluate_gate,
    list_gate_types,
    list_registered_gate_types,
    validate_gate_spec,
)


# ── Enum coverage ────────────────────────────────────────────────────────


def test_gate_type_enum_has_ten_unanimous_wire_gates():
    assert {t.name for t in GateType} == {
        "BOUNDS_CHECK",
        "HOLDOUT_MRE",
        "EXTRAPOLATION_MRE",
        "ASYMPTOTIC_DISCIPLINE",
        "MONOTONICITY",
        "POSITIVITY",
        "PARAMETER_COUNT",
        "ANTI_RETRIEVAL",
        "FRAME_INVARIANCE",
        "DIMENSIONAL_CONSISTENCY",
    }


def test_gate_type_numbering_is_monotonic_one_to_ten():
    """Linus-syscall discipline: numbers never renumbered. Lock the order."""
    assert [t.value for t in GateType] == list(range(1, 11))


def test_every_gate_type_has_a_parameter_schema():
    """Every enum value must have a schema entry; otherwise validate_gate_spec
    raises GATE_TYPE_NOT_REGISTERED unexpectedly."""
    for t in GateType:
        assert t in PARAMETER_SCHEMAS, f"missing schema for {t.name}"


def test_list_helpers():
    assert "BOUNDS_CHECK" in list_gate_types()
    assert "HOLDOUT_MRE" in list_registered_gate_types()
    assert "EXTRAPOLATION_MRE" in list_gate_types()
    # spec-only — not registered yet
    assert "EXTRAPOLATION_MRE" not in list_registered_gate_types()


# ── validate_gate_spec — strict typing ───────────────────────────────────


def test_validate_unknown_gate_type_raises():
    with pytest.raises(GateContractError) as exc:
        validate_gate_spec({"type": "NOT_A_REAL_GATE", "parameters": {}})
    assert exc.value.code == "UNKNOWN_GATE_TYPE"


def test_validate_bounds_check_minimal_ok():
    spec = validate_gate_spec({
        "type": "BOUNDS_CHECK",
        "parameters": {"min_val": 0.0, "max_val": 1.0, "probe_points": [100.0, 200.0]},
    })
    assert isinstance(spec, EvaluativeGateSpec)
    assert spec.type == GateType.BOUNDS_CHECK
    assert spec.target_variable == "y"
    assert spec.binding is True
    assert spec.parameters["max_val"] == 1.0


def test_validate_missing_required_parameter_raises():
    with pytest.raises(GateContractError) as exc:
        validate_gate_spec({
            "type": "BOUNDS_CHECK",
            "parameters": {"min_val": 0.0, "probe_points": [100.0]},  # missing max_val
        })
    assert exc.value.code == "MISSING_PARAMETER"
    assert exc.value.gate_type == GateType.BOUNDS_CHECK


def test_validate_wrong_parameter_type_raises():
    with pytest.raises(GateContractError) as exc:
        validate_gate_spec({
            "type": "HOLDOUT_MRE",
            "parameters": {"threshold": "not_a_float"},
        })
    assert exc.value.code == "WRONG_PARAMETER_TYPE"
    assert exc.value.gate_type == GateType.HOLDOUT_MRE


def test_validate_extra_parameter_raises():
    """Strict — operator drift via stale keys must fail at seal."""
    with pytest.raises(GateContractError) as exc:
        validate_gate_spec({
            "type": "HOLDOUT_MRE",
            "parameters": {"threshold": 0.1, "stale_old_key": 999},
        })
    assert exc.value.code == "EXTRA_PARAMETER"


def test_validate_binding_default_true_explicit_false():
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.1},
        "binding": False,
    })
    assert spec.binding is False


def test_validate_target_variable_override():
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.1},
        "target_variable": "alpha",
    })
    assert spec.target_variable == "alpha"


def test_validate_probe_range_accepts_list_or_tuple():
    """MONOTONICITY / POSITIVITY use tuple-or-list union schema."""
    spec_list = validate_gate_spec({
        "type": "POSITIVITY",
        "parameters": {"strict": True, "probe_range": [0.0, 100.0]},
    })
    assert spec_list.parameters["probe_range"] == [0.0, 100.0]
    spec_tuple = validate_gate_spec({
        "type": "POSITIVITY",
        "parameters": {"strict": True, "probe_range": (0.0, 100.0)},
    })
    assert spec_tuple.parameters["probe_range"] == (0.0, 100.0)


def test_validate_anti_retrieval_full_schema():
    spec = validate_gate_spec({
        "type": "ANTI_RETRIEVAL",
        "parameters": {
            "probe_points": [5.0, 10.0],
            "forbidden_values": [0.4, 0.2, 0.1],  # 2/d, 4/(2d), 1/d
            "tolerance": 0.01,
        },
    })
    assert spec.type == GateType.ANTI_RETRIEVAL


def test_validate_spec_only_gate_validates_but_evaluate_raises():
    """A spec-only gate type (EXTRAPOLATION_MRE etc.) should validate fine
    but raise GATE_TYPE_NOT_REGISTERED when invoked."""
    spec = validate_gate_spec({
        "type": "EXTRAPOLATION_MRE",
        "parameters": {"threshold": 0.15, "far_tail_min_d": 50.0},
    })
    assert spec.type == GateType.EXTRAPOLATION_MRE

    class _Ctx:
        I_model = staticmethod(lambda d: 0.0)
        visible_rows = []
        holdout_rows = []

    with pytest.raises(GateContractError) as exc:
        evaluate_gate(_Ctx(), spec)
    assert exc.value.code == "GATE_TYPE_NOT_REGISTERED"


# ── BOUNDS_CHECK impl ────────────────────────────────────────────────────


class _Ctx:
    """Minimal GateContext mock."""

    def __init__(self, model_fn, visible=(), holdout=()):
        self.I_model = model_fn
        self.visible_rows = visible
        self.holdout_rows = holdout


def test_bounds_check_passes_when_in_range():
    spec = validate_gate_spec({
        "type": "BOUNDS_CHECK",
        "parameters": {"min_val": 0.0, "max_val": 1.0, "probe_points": [100.0, 150.0, 200.0]},
    })
    ctx = _Ctx(lambda d: 0.001 * (200.0 / d))  # ~0 < y < 1
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is True
    assert result["violations"] == []


def test_bounds_check_catches_negative_extrapolation():
    """gp160-class fix: model that goes negative at large d FAILS."""
    spec = validate_gate_spec({
        "type": "BOUNDS_CHECK",
        "parameters": {"min_val": 0.0, "max_val": 1.0, "probe_points": [100.0, 150.0, 200.0]},
    })
    ctx = _Ctx(lambda d: -0.5 if d > 120 else 0.5)
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is False
    assert len(result["violations"]) == 2  # d=150 and d=200


def test_bounds_check_catches_nan_inf():
    spec = validate_gate_spec({
        "type": "BOUNDS_CHECK",
        "parameters": {"min_val": 0.0, "max_val": 1.0, "probe_points": [100.0]},
    })
    ctx = _Ctx(lambda d: float("nan"))
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is False
    assert result["violations"][0]["violation"] == "NaN/Inf"


def test_bounds_check_catches_exception_in_model():
    spec = validate_gate_spec({
        "type": "BOUNDS_CHECK",
        "parameters": {"min_val": 0.0, "max_val": 1.0, "probe_points": [100.0]},
    })

    def _raises(d):
        raise RuntimeError("model exploded")

    ctx = _Ctx(_raises)
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is False
    assert "RuntimeError" in result["violations"][0]["violation"]


# ── HOLDOUT_MRE impl ─────────────────────────────────────────────────────


def test_holdout_mre_passes_within_threshold():
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.10},
    })
    holdout = [(0, 1.0, 1.0), (1, 2.0, 0.5), (2, 4.0, 0.25)]  # y_true = 1/d
    ctx = _Ctx(lambda d: 1.0 / d, holdout=holdout)
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is True
    assert result["mean_relative_error"] < 1e-9


def test_holdout_mre_fails_above_threshold():
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.05},
    })
    holdout = [(0, 1.0, 1.0), (1, 2.0, 0.5)]
    ctx = _Ctx(lambda d: 2.0 / d, holdout=holdout)  # 2x off
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is False
    assert result["mean_relative_error"] > 0.5


def test_holdout_mre_handles_two_tuple_rows():
    """Some substrates emit (d, y) directly without an id."""
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.10},
    })
    holdout = [(1.0, 1.0), (2.0, 0.5)]
    ctx = _Ctx(lambda d: 1.0 / d, holdout=holdout)
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is True


def test_holdout_mre_treats_nan_as_full_error():
    spec = validate_gate_spec({
        "type": "HOLDOUT_MRE",
        "parameters": {"threshold": 0.5},
    })
    holdout = [(0, 1.0, 1.0)]
    ctx = _Ctx(lambda d: float("nan"), holdout=holdout)
    result = evaluate_gate(ctx, spec)
    assert result["mean_relative_error"] == 1.0


# ── ANTI_RETRIEVAL impl ──────────────────────────────────────────────────


def test_anti_retrieval_catches_known_law_match():
    """gp159-class: mutator 'discovers' 2/d via retrieval, not fitting."""
    spec = validate_gate_spec({
        "type": "ANTI_RETRIEVAL",
        "parameters": {
            "probe_points": [5.0, 10.0],
            "forbidden_values": [0.4, 0.2],  # 2/5, 2/10
            "tolerance": 0.005,
        },
    })
    ctx = _Ctx(lambda d: 2.0 / d)  # the retrieval form
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is False
    assert len(result["breaches"]) == 2


def test_anti_retrieval_passes_when_form_diverges():
    spec = validate_gate_spec({
        "type": "ANTI_RETRIEVAL",
        "parameters": {
            "probe_points": [5.0, 10.0],
            "forbidden_values": [0.4, 0.2],
            "tolerance": 0.001,
        },
    })
    ctx = _Ctx(lambda d: 3.7142 / (d + 0.001))  # gp159's actual fitted form
    result = evaluate_gate(ctx, spec)
    assert result["passed"] is True


def test_anti_retrieval_tolerance_band():
    spec = validate_gate_spec({
        "type": "ANTI_RETRIEVAL",
        "parameters": {
            "probe_points": [10.0],
            "forbidden_values": [0.20],
            "tolerance": 0.025,
        },
    })
    ctx_close = _Ctx(lambda d: 0.218)  # within 0.025 of 0.20
    ctx_far = _Ctx(lambda d: 0.30)  # outside band
    assert evaluate_gate(ctx_close, spec)["passed"] is False
    assert evaluate_gate(ctx_far, spec)["passed"] is True
