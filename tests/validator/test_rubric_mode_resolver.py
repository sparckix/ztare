from __future__ import annotations

from src.ztare.validator.rubric_mode_resolver import (
    apply_rubric_mode_defaults,
    describe_rubric_mode,
    validate_rubric_mode_contract,
)


def test_invariant_search_defaults_preserve_operator_overrides():
    rubric = {
        "rubric_modes": ["invariant_search"],
        "buckingham_strict": True,
    }

    apply_rubric_mode_defaults(rubric)

    assert rubric["enable_lagrangian_derivation"] is True
    assert rubric["enable_buckingham_pi_gate"] is True
    assert rubric["buckingham_strict"] is True
    assert "invariant_search" in describe_rubric_mode(rubric)


def test_describe_primary_and_secondary_modes_distinctly():
    rubric = {
        "rubric_mode": "newton",
        "rubric_modes": ["invariant_search"],
        "enable_lagrangian_derivation": True,
    }

    apply_rubric_mode_defaults(rubric)
    desc = describe_rubric_mode(rubric)

    assert "primary discovery scoring" in desc
    assert "invariant_search" in desc
    assert "no defaults registered" not in desc


def test_unset_primary_mode_is_legacy_ok():
    result = validate_rubric_mode_contract({})

    assert result.ok is True
    assert result.mode == ""
    assert result.message == ""


def test_newton_requires_generative_yield_dimension():
    result = validate_rubric_mode_contract(
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Fit", "weight": 100}],
        }
    )

    assert result.ok is False
    assert "Generative Yield" in result.message


def test_newton_accepts_generative_yield_weight_at_least_15():
    result = validate_rubric_mode_contract(
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": "15"}],
        }
    )

    assert result.ok is True
    assert result.mode == "newton"
    assert "Newton-mode rubric detected" in result.message


def test_kepler_and_calibration_are_accepted_without_generative_yield():
    kepler = validate_rubric_mode_contract({"rubric_mode": "kepler"})
    calibration = validate_rubric_mode_contract({"rubric_mode": "calibration"})

    assert kepler.ok is True
    assert "descriptive-fit-only" in kepler.message
    assert calibration.ok is True
    assert "instrument-characterization" in calibration.message


def test_unknown_primary_mode_fails_closed():
    result = validate_rubric_mode_contract({"rubric_mode": "factory"})

    assert result.ok is False
    assert "not a recognized value" in result.message
