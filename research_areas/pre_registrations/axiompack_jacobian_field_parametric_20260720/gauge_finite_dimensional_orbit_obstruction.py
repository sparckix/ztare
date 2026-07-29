#!/usr/bin/env python3
"""Exact replay for two finite-dimensional-orbit obstructions.

The all-order arguments are recorded in the companion result:

* generic inverse degree excludes rational polynomial source/target orbits;
* the reciprocal-root flattening has an unbounded family of nonzero sharp
  monomials inside the abelian vertical-translation group.

The finite coefficient checks below are regression tests for the closed
forms, not extrapolation from a prefix.
"""
from __future__ import annotations

import hashlib
import json

import sympy as sp


def _truncate(
    value: sp.Expr,
    parameter: sp.Symbol,
    order: int,
) -> sp.Expr:
    return sp.expand(
        sp.series(value, parameter, 0, order + 1).removeO()
    )


def _fixed_point_prefix(
    *,
    parameter: sp.Symbol,
    first: sp.Symbol,
    second: sp.Symbol,
    order: int,
) -> sp.Expr:
    a = parameter / (2 * (parameter + 2))
    b = (parameter + 4) / (2 * (parameter + 2))
    c = 12 / ((parameter - 6) * (parameter + 2))
    d = -(parameter - 4) / (2 * (parameter + 2))
    result = sp.Integer(0)
    for _ in range(order + 2):
        result = _truncate(
            a
            + b * result**2
            + c * first * result**3
            + d * second * result**4,
            parameter,
            order,
        )
    return result


def _sharp_translation_coefficient(k: int) -> sp.Rational:
    """Coefficient of s^(2k-1) P^k in the root translation."""
    if k < 1:
        raise ValueError("k must be positive")
    return sp.Rational(
        (-1) ** k * sp.binomial(3 * k - 1, k - 1),
        2 * 16 ** (k - 1) * (3 * k - 1),
    )


def run(maximum_k: int = 12) -> dict[str, object]:
    if maximum_k < 2:
        raise ValueError("maximum_k must be at least two")

    s, p, q, w = sp.symbols("s P Q W")
    a = s / (2 * (s + 2))
    b = (s + 4) / (2 * (s + 2))
    c = 12 / ((s - 6) * (s + 2))
    d = -(s - 4) / (2 * (s + 2))
    inverse = sp.expand(
        w**3 - a * w**4 - b * w**2 - c * p * w - d * q
    )
    seed_inverse = sp.expand(inverse.subs(s, 0))
    assert sp.Poly(inverse, w).degree() == 4
    assert sp.factor(
        sp.Poly(inverse, w).coeff_monomial(w**4) + a
    ) == 0
    assert sp.Poly(seed_inverse, w).degree() == 3
    assert seed_inverse == w**3 - w**2 + p * w - q

    # The public family is generated from p_s(w), q_s(w) with q_s'=w p_s'.
    p_family = (
        (2 + s / 2) * w
        + (-3 - 3 * s / 2) * w**2
        + s * w**3
    )
    q_family = (
        (1 + s / 4) * w**2
        - (2 + s) * w**3
        + 3 * s * w**4 / 4
    )
    assert sp.expand(
        sp.diff(q_family, w) - w * sp.diff(p_family, w)
    ) == 0

    # Check the first actual translation coefficients in the full
    # coefficientwise fixed-point equation.
    root = _fixed_point_prefix(
        parameter=s,
        first=p,
        second=q,
        order=5,
    )
    scalar_root = s / (s + 4)
    translation = _truncate(
        1 / scalar_root - 1 / root,
        s,
        3,
    )
    assert sp.expand(translation.coeff(s, 1) + p / 4) == 0
    assert sp.expand(
        translation.coeff(s, 2) - (p + 3 * q) / 48
    ) == 0
    assert sp.expand(
        translation.coeff(s, 3)
        - (18 * p**2 - 7 * p - 27 * q) / 576
    ) == 0

    # The all-order sharp family is one-variable.  At y=0, U=4Z obeys
    # U=1-(x/16)U^3 and Phi=-x*U^2/4.
    x = sp.Symbol("x")
    u = sp.Integer(1)
    for _ in range(maximum_k + 1):
        u = sp.series(
            1 - x * u**3 / 16,
            x,
            0,
            maximum_k,
        ).removeO().expand()
    assert sp.expand(
        sp.series(
            u - 1 + x * u**3 / 16,
            x,
            0,
            maximum_k,
        ).removeO()
    ) == 0
    sharp_translation = sp.expand(-x * u**2 / 4)
    rows = []
    for k in range(1, maximum_k + 1):
        order = 2 * k - 1
        coefficient = sp.Poly(
            sharp_translation, x, domain=sp.QQ
        ).coeff_monomial(x**k)
        expected = _sharp_translation_coefficient(k)
        assert coefficient == expected
        assert coefficient != 0
        rows.append({
            "k": k,
            "parameter_order": order,
            "monomial": f"P^{k}",
            "coefficient": str(coefficient),
            "ordinary_target_degree": k,
        })

    # Vertical translations form an abelian Lie algebra:
    # [f(P,Q)d/dW, g(P,Q)d/dW] = 0.
    f, g = sp.Function("f"), sp.Function("g")
    vertical_bracket = sp.expand(
        f(p, q) * sp.diff(g(p, q), w)
        - g(p, q) * sp.diff(f(p, q), w)
    )
    assert vertical_bracket == 0

    receipt = json.dumps(rows, sort_keys=True)
    return {
        "schema": (
            "axiompack.jacobian_finite_dimensional_orbit_obstruction.v1"
        ),
        "inverse_degree": {
            "generic": 4,
            "seed": 3,
            "generic_leading_coefficient": str(sp.factor(-a)),
            "seed_equation": str(seed_inverse),
        },
        "mechanism_identity": "q_s'(W)=W*p_s'(W)",
        "vertical_translation_lie_bracket": str(vertical_bracket),
        "sharp_translation_family": rows,
        "sharp_formula": (
            "(-1)^k*binomial(3*k-1,k-1)"
            "/(2*16^(k-1)*(3*k-1))"
        ),
        "row_receipt_sha256": hashlib.sha256(
            receipt.encode("utf-8")
        ).hexdigest(),
        "claim_boundary": (
            "Generic degree excludes rational-in-parameter polynomial "
            "automorphism orbits. The sharp family excludes a "
            "finite-dimensional subalgebra of vertical generator "
            "translations for the canonical flattening. Non-complete "
            "nonlinear formal flows mixing source and target remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
