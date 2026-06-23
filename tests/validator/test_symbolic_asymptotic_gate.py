from __future__ import annotations

from ztare.validator.core.symbolic_asymptotic_gate import (
    TextRejector,
    evaluate_asymptotic_terms,
)


def test_prefers_scale_over_amplitude() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "C1*N*A**2",
            "self_tax_polynomial_or_bound": "C2*N**2*A**2",
        }
    )
    assert result["passed"] is True
    assert result["variable"] == "N"
    assert result["gain_over_self_tax_limit"] == "0"


def test_binds_beta_as_symbol() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "alpha*K*n",
            "self_tax_polynomial_or_bound": "beta*K**2*n**2",
        }
    )
    assert result["passed"] is True
    assert result["variable"] == "K"


def test_rejects_lhs_or_prose_expression() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "gamma(V;A)=C1*A**2",
            "self_tax_polynomial_or_bound": "C2*A**4",
        }
    )
    assert result["passed"] is False
    assert "without_lhs_or_prose" in result["reason"]


def test_configurable_rejector() -> None:
    rejector = TextRejector(
        name="known_nullspace",
        reason="single-mode class needs a nullspace split",
        required_any_groups=(("single mode",), ("self-tax dominates",)),
        unless_any=("case split",),
    )
    result = evaluate_asymptotic_terms(
        {
            "independent_parametric_class": "single mode Fourier class",
            "gain_polynomial_or_bound": "C1*N",
            "self_tax_polynomial_or_bound": "C2*N**2",
            "degree_comparison": "self-tax dominates",
        },
        rejectors=(rejector,),
    )
    assert result["passed"] is False
    assert result["reason"].startswith("known_nullspace")


def test_sqrt_tax_limit_is_optional_by_default() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "alpha*A",
            "self_tax_polynomial_or_bound": "beta*A**2",
        }
    )
    assert result["passed"] is True
    assert result["gain_over_sqrt_self_tax_limit"] == "alpha/sqrt(beta)"


def test_sqrt_tax_limit_rejects_unpaid_symbolic_constant() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "alpha*A",
            "self_tax_polynomial_or_bound": "beta*A**2",
        },
        require_sqrt_tax_limit=True,
        sqrt_tax_limit_threshold=2 / 3,
    )
    assert result["passed"] is False
    assert result["reason"].startswith("sqrt_tax_limit_not_numeric")


def test_sqrt_tax_limit_accepts_paid_numeric_margin() -> None:
    result = evaluate_asymptotic_terms(
        {
            "gain_polynomial_or_bound": "A/2",
            "self_tax_polynomial_or_bound": "A**2",
        },
        require_sqrt_tax_limit=True,
        sqrt_tax_limit_threshold=2 / 3,
    )
    assert result["passed"] is True
    assert result["gain_over_sqrt_self_tax_limit"] == "1/2"


if __name__ == "__main__":
    test_prefers_scale_over_amplitude()
    test_binds_beta_as_symbol()
    test_rejects_lhs_or_prose_expression()
    test_configurable_rejector()
    test_sqrt_tax_limit_is_optional_by_default()
    test_sqrt_tax_limit_rejects_unpaid_symbolic_constant()
    test_sqrt_tax_limit_accepts_paid_numeric_margin()
