#!/usr/bin/env python3
"""Exact rank-two differential equation for the critical holonomy germ.

The critical logarithmic derivative belongs to the quadratic field
``QQ(x, sqrt(-3 (x-6) (x+2)))``.  Differentiation preserves that field, so
``F''/F = L' + L**2`` is an exact rational-linear combination of ``1`` and
``L = F'/F``.  This replay performs that reduction, emits the resulting
second-order polynomial ODE, and checks its coefficient recurrence against
the independently constructed critical holonomy prefix.

The ODE is an exact all-order identity.  It does not classify products of
polynomial time-one maps and therefore does not prove the two-flow
nonfactorization theorem.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_pure_contact_zero_parity_algebraic_connection import (  # noqa: E402
    _algebraic_normal_two,
)
from gauge_two_polynomial_flow_direct_factorization import (  # noqa: E402
    _critical_holonomy_coefficients,
)


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _quadratic_logarithmic_derivative() -> tuple[
    sp.Symbol,
    sp.Expr,
    sp.Expr,
    sp.Expr,
]:
    """Return ``x, D, l0, l1`` with ``F'/F = l0 + l1*sqrt(D)``."""

    x, discriminant, velocity = _algebraic_normal_two()
    denominator_rational = sp.cancel(1 + 2 * x * velocity.rational)
    denominator_radical = sp.cancel(
        2 * x * velocity.radical_coefficient
    )
    norm = sp.cancel(
        denominator_rational**2
        - denominator_radical**2 * discriminant
    )
    rational = sp.cancel(denominator_rational / (x * norm))
    radical = sp.cancel(-denominator_radical / (x * norm))
    return x, discriminant, rational, radical


def _polynomial_ode() -> tuple[
    sp.Symbol,
    sp.Expr,
    sp.Expr,
    sp.Expr,
    dict[str, sp.Expr],
]:
    """Return polynomial coefficients ``P2,P1,P0`` for the scalar ODE."""

    x, discriminant, l0, l1 = _quadratic_logarithmic_derivative()
    derivative_l0 = sp.diff(l0, x)
    derivative_l1 = sp.cancel(
        sp.diff(l1, x)
        + l1 * sp.diff(discriminant, x) / (2 * discriminant)
    )
    square_l0 = sp.cancel(l0**2 + l1**2 * discriminant)
    square_l1 = sp.cancel(2 * l0 * l1)
    k0 = sp.cancel(derivative_l0 + square_l0)
    k1 = sp.cancel(derivative_l1 + square_l1)

    beta = sp.factor(sp.cancel(k1 / l1))
    alpha = sp.factor(sp.cancel(k0 - beta * l0))
    assert sp.cancel(k0 - alpha - beta * l0) == 0
    assert sp.cancel(k1 - beta * l1) == 0

    beta_numerator, beta_denominator = sp.fraction(beta)
    alpha_numerator, alpha_denominator = sp.fraction(alpha)
    common_denominator = sp.lcm(
        sp.Poly(beta_denominator, x),
        sp.Poly(alpha_denominator, x),
    ).as_expr()
    p2 = sp.factor(common_denominator)
    p1 = sp.factor(-common_denominator * beta)
    p0 = sp.factor(-common_denominator * alpha)
    for coefficient in (p2, p1, p0):
        polynomial = sp.Poly(coefficient, x, domain=sp.QQ).as_expr()
        assert sp.cancel(polynomial - coefficient) == 0

    audit = {
        "discriminant": sp.factor(discriminant),
        "logarithmic_derivative_rational": sp.factor(l0),
        "logarithmic_derivative_radical": sp.factor(l1),
        "alpha": alpha,
        "beta": beta,
        "beta_numerator": sp.factor(beta_numerator),
        "alpha_numerator": sp.factor(alpha_numerator),
    }
    return x, p2, p1, p0, audit


def _recurrence_coefficients(
    maximum_order: int,
    x: sp.Symbol,
    p2: sp.Expr,
    p1: sp.Expr,
    p0: sp.Expr,
) -> list[sp.Expr]:
    """Solve the polynomial-ODE recurrence from ``c0=0,c1=1``."""

    if maximum_order < 1:
        raise ValueError("maximum_order must be positive")
    p2_coefficients = sp.Poly(p2, x).as_dict()
    p1_coefficients = sp.Poly(p1, x).as_dict()
    p0_coefficients = sp.Poly(p0, x).as_dict()
    leading = p2_coefficients.get((0,), sp.S.Zero)
    assert leading != 0

    coefficients = [sp.S.Zero, sp.S.One]
    for row in range(maximum_order - 1):
        unknown_order = row + 2
        residual = sp.S.Zero
        for (degree,), value in p2_coefficients.items():
            series_order = row - degree + 2
            if 0 <= series_order < unknown_order:
                residual += (
                    value
                    * series_order
                    * (series_order - 1)
                    * coefficients[series_order]
                )
        for (degree,), value in p1_coefficients.items():
            series_order = row - degree + 1
            if 0 <= series_order < unknown_order:
                residual += value * series_order * coefficients[series_order]
        for (degree,), value in p0_coefficients.items():
            series_order = row - degree
            if 0 <= series_order < unknown_order:
                residual += value * coefficients[series_order]
        divisor = leading * unknown_order * (unknown_order - 1)
        coefficients.append(sp.factor(-residual / divisor))
    return coefficients


def build_certificate(verification_order: int = 10) -> dict[str, object]:
    if verification_order < 6:
        raise ValueError("verification_order must be at least six")
    x, p2, p1, p0, audit = _polynomial_ode()
    recurrence = _recurrence_coefficients(
        verification_order, x, p2, p1, p0
    )
    independently_constructed = _critical_holonomy_coefficients(
        verification_order
    )
    assert recurrence == independently_constructed

    core: dict[str, object] = {
        "schema": "axiompack.critical_holonomy_rank_two_differential.v1",
        "coefficient_field": "QQ",
        "quadratic_discriminant": str(audit["discriminant"]),
        "quadratic_discriminant_is_squarefree": (
            sp.gcd(
                sp.Poly(audit["discriminant"], x),
                sp.Poly(sp.diff(audit["discriminant"], x), x),
            ).degree()
            == 0
        ),
        "logarithmic_derivative": {
            "rational_part": str(
                audit["logarithmic_derivative_rational"]
            ),
            "radical_coefficient": str(
                audit["logarithmic_derivative_radical"]
            ),
            "radical_coefficient_nonzero": (
                audit["logarithmic_derivative_radical"] != 0
            ),
        },
        "polynomial_ode": {
            "equation": "P2*F'' + P1*F' + P0*F = 0",
            "P2": str(p2),
            "P1": str(p1),
            "P0": str(p0),
            "degrees": {
                "P2": int(sp.degree(p2, x)),
                "P1": int(sp.degree(p1, x)),
                "P0": int(sp.degree(p0, x)),
            },
        },
        "recurrence_initial_values": ["0", "1"],
        "verification_order": verification_order,
        "recurrence_coefficients": [str(value) for value in recurrence],
        "independent_prefix_matches_recurrence": True,
        "recurrence_sha256": _sha256(
            [str(value) for value in recurrence]
        ),
        "claim_boundary": (
            "The critical holonomy satisfies the displayed all-order "
            "rank-two linear differential equation and its induced "
            "P-recursive coefficient law. No classification of products "
            "of two polynomial autonomous flows is inferred."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(build_certificate(), indent=2, sort_keys=True))
