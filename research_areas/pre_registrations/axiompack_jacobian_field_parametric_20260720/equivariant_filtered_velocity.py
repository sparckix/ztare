#!/usr/bin/env python3
"""Exact target-relative source velocity for the normalized Keller line."""
from __future__ import annotations

import hashlib
import json

import sympy as sp


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode()).hexdigest()


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    return int(sp.Poly(value, v, t).total_degree())


def _top_part(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> sp.Expr:
    polynomial = sp.Poly(sp.expand(value), v, t)
    degree = polynomial.total_degree()
    return sp.expand(sum(
        coefficient * v**monomial[0] * t**monomial[1]
        for monomial, coefficient in polynomial.terms()
        if sum(monomial) == degree
    ))


def run() -> dict[str, object]:
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    P = sp.cancel(lam / mu * (gamma + p.subs(z, w)))
    Q = sp.cancel((gamma * w + q.subs(z, w)) / lam)

    jacobian = sp.Matrix([
        [sp.diff(P, v), sp.diff(P, t)],
        [sp.diff(Q, v), sp.diff(Q, t)],
    ])
    assert sp.cancel(jacobian.det() + gamma**2) == 0

    # For F_s = exp(s X_H) o F_0 o psi_s, freeze the convention by the
    # displayed identity: this equals (D psi_s)^(-1) partial_s psi_s.
    residual = sp.Matrix([
        sp.diff(P, s) + Q / 2,
        sp.diff(Q, s) - P**2 / 12,
    ])
    velocity = [sp.factor(sp.cancel(value)) for value in jacobian.inv() * residual]

    rows = []
    for name, value in zip(("v", "t"), velocity, strict=True):
        numerator, denominator = map(sp.factor, sp.fraction(value))
        assert not ({v, t} & denominator.free_symbols)
        assert denominator.subs(s, 0) != 0
        rows.append({
            "component": name,
            "numerator_total_degree": _degree(numerator, v, t),
            "denominator_depends_only_on_parameter": True,
            "numerator_s_degree": int(sp.Poly(numerator, s).degree()),
            "denominator_s_degree": int(sp.Poly(denominator, s).degree()),
            "denominator_factor": str(denominator),
            "denominator_nonzero_at_s_zero": True,
            "numerator_sha256": _sha(numerator),
            "denominator_sha256": _sha(denominator),
            "vanishes_at_s_zero": sp.cancel(value.subs(s, 0)) == 0,
        })

    # The first two Taylor coefficients orient the prospective filtration
    # proof; no finite-order extrapolation is used as an all-order argument.
    coefficient_rows = []
    initial_coefficients = []
    for order in (1, 2):
        coefficients = [
            sp.cancel(sp.diff(value, s, order).subs(s, 0) / sp.factorial(order))
            for value in velocity
        ]
        initial_coefficients.append(coefficients)
        coefficient_rows.append({
            "s_order": order,
            "degrees": [_degree(value, v, t) for value in coefficients],
            "sha256": [_sha(value) for value in coefficients],
        })

    velocity_one_top = [
        _top_part(value, v, t) for value in initial_coefficients[0]
    ]
    velocity_two_top = [
        _top_part(value, v, t) for value in initial_coefficients[1]
    ]
    L = 2 * t - 3 * v
    r = v * L
    expected_one_top = [
        -sp.Rational(3, 64) * v**7 * L**4,
        sp.Rational(3, 64) * v**6 * (t - 3 * v) * L**4,
    ]
    assert all(
        sp.expand(actual - expected) == 0
        for actual, expected in zip(
            velocity_one_top, expected_one_top, strict=True
        )
    )
    assert all(
        sp.expand(actual + sp.Rational(7, 12) * r * first) == 0
        for actual, first in zip(
            velocity_two_top, velocity_one_top, strict=True
        )
    )
    assert sp.expand(
        velocity_one_top[0] * sp.diff(r, v) +
        velocity_one_top[1] * sp.diff(r, t)
    ) == 0
    velocity_degree_fifteen = [_top_part(value, v, t) for value in velocity]
    degree_fifteen_scalar = sp.factor(
        -sp.Rational(243, 8192) * s**3 * (s - 4)**9 / (s - 6)**6
    )
    assert all(
        sp.cancel(actual - degree_fifteen_scalar * r**2 * first / 2) == 0
        for actual, first in zip(
            velocity_degree_fifteen, velocity_one_top, strict=True
        )
    )

    return {
        "schema": "axiompack.jacobian_filtered_velocity.v1",
        "identity": "F_s=exp(s*X_H)*F_0*psi_s",
        "velocity_convention": "(Dpsi_s)^(-1)*partial_s(psi_s)",
        "quotient_jacobian": "-gamma^2",
        "uniform_velocity_coefficient_degree_bound": 15,
        "components": rows,
        "initial_coefficients": coefficient_rows,
        "leading_flow": {
            "invariant": "r=v*(2*t-3*v)",
            "W1_top": [str(value) for value in velocity_one_top],
            "W2_top_relation": "W2_top=-(7/12)*r*W1_top",
            "W1_top_annihilates_r": True,
            "degree_15_velocity_relation": "W_s^[15]=C(s)*r^2*W1_top/2",
            "degree_15_scalar": str(degree_fifteen_scalar),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
