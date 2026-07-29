#!/usr/bin/env python3
"""Exact third-jet test under the full polynomial equivariant source gauge."""
from __future__ import annotations

import hashlib
import json

import sympy as sp


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode()).hexdigest()


def _family_jets() -> dict[str, object]:
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    beta = sp.cancel(lam / mu * (1 + p.subs(z, w) / gamma))
    alpha = sp.cancel((1 + mu * v + q.subs(z, w) / gamma**2) / lam)
    p_jets = [
        sp.cancel(gamma * sp.diff(beta, s, order).subs(s, 0))
        for order in range(4)
    ]
    q_jets = [
        sp.cancel(gamma**2 * sp.diff(alpha, s, order).subs(s, 0))
        for order in range(4)
    ]
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in p_jets + q_jets
    )
    return {
        "symbols": (v, t),
        "gamma": gamma,
        "P": p_jets,
        "Q": q_jets,
    }


def _solve_source(
    data: dict[str, object], residual: tuple[sp.Expr, sp.Expr]
) -> tuple[sp.Expr, sp.Expr]:
    v, t = data["symbols"]
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    assert sp.cancel(jacobian.det() + data["gamma"]**2) == 0
    source = [sp.cancel(value) for value in jacobian.inv() * sp.Matrix(residual)]
    assert all(sp.denom(value) == 1 for value in source)
    assert all(sp.cancel(value) == 0 for value in jacobian * sp.Matrix(source) - sp.Matrix(residual))
    return source[0], source[1]


def _lift_certificate(
    source: tuple[sp.Expr, sp.Expr], v: sp.Symbol, t: sp.Symbol
) -> dict[str, object]:
    u, z = source
    assert u.subs({v: 0, t: 0}) == 0
    assert z.subs(t, 0).subs(v, 0) == 0
    assert sp.diff(z.subs(t, 0), v).subs(v, 0) == 0

    a = sp.cancel((sp.diff(u, v) + sp.diff(z, t)) / 2)
    b = sp.cancel((u - v * a).subs(t, 0) / v)
    c = sp.cancel((u - v * (a + b)) / t)
    e = sp.cancel((z - 2 * t * a).subs(t, 0) / v**2)
    d = sp.cancel((z - 2 * t * a - v**2 * e) / t)
    assert all(sp.denom(value) == 1 for value in (a, b, c, d, e))
    assert sp.cancel(v * (a + b) + t * c - u) == 0
    assert sp.cancel(t * (2 * a + d) + v**2 * e - z) == 0
    divergence = (
        a + b + d + v * (sp.diff(a, v) + sp.diff(b, v)) +
        2 * t * sp.diff(a, t) + t * sp.diff(c, v) +
        t * sp.diff(d, t) + v**2 * sp.diff(e, t)
    )
    assert sp.cancel(divergence) == 0
    return {
        "U_degree": sp.Poly(u, v, t).total_degree(),
        "V_degree": sp.Poly(z, v, t).total_degree(),
        "U_sha256": _sha(u),
        "V_sha256": _sha(z),
        "U_in_v_t_ideal": True,
        "V_in_t_v2_ideal": True,
        "polynomial_divergence_free_equivariant_lift": True,
    }


def _weighted_coordinates(
    source: tuple[sp.Expr, sp.Expr], v: sp.Symbol, t: sp.Symbol
) -> tuple[sp.Expr, sp.Expr]:
    w, gamma = sp.symbols("w gamma")
    substitution = {
        v: w / gamma - 1,
        t: gamma - 1 + sp.Rational(3, 2) * (w / gamma - 1),
    }
    u, z = source
    delta_gamma = sp.cancel((-sp.Rational(3, 2) * u + z).subs(substitution))
    delta_w = sp.cancel(
        ((1 - sp.Rational(3, 2) * v + t) * u +
         (1 + v) * (-sp.Rational(3, 2) * u + z)).subs(substitution)
    )
    assert sp.cancel(
        sp.diff(gamma * delta_w, w) + sp.diff(gamma * delta_gamma, gamma)
    ) == 0
    return sp.factor(delta_w), sp.factor(delta_gamma)


def run() -> dict[str, object]:
    data = _family_jets()
    v, t = data["symbols"]
    p0, p2, p3 = data["P"][0], data["P"][2], data["P"][3]
    q0, q2, q3 = data["Q"][0], data["Q"][2], data["Q"][3]

    second = (
        sp.cancel(p2 + p0**2 / 24),
        sp.cancel(q2 + p0 * q0 / 12),
    )
    source2 = _solve_source(data, second)

    third = (
        sp.cancel(p3 - p0 * q0 / 24 + sp.Rational(3, 2) * second[1]),
        sp.cancel(q3 - q0**2 / 24 + p0**3 / 144 - p0 * second[0] / 2),
    )
    source3 = _solve_source(data, third)
    weighted2 = _weighted_coordinates(source2, v, t)
    weighted3 = _weighted_coordinates(source3, v, t)
    return {
        "schema": "axiompack.jacobian_full_gauge_third_jet.v1",
        "composition_convention": "exp(s*X_H) o F0 o psi_s",
        "X_H": ["-Q/2", "P^2/12"],
        "X_H_cubed": ["P*Q/24", "Q^2/24-P^3/144"],
        "second_residual_degrees": [
            sp.Poly(value, v, t).total_degree() for value in second
        ],
        "third_residual_degrees": [
            sp.Poly(value, v, t).total_degree() for value in third
        ],
        "second_source": _lift_certificate(source2, v, t) | {
            "weighted_coordinates": [str(value) for value in weighted2]
        },
        "third_source": _lift_certificate(source3, v, t) | {
            "weighted_coordinates": [str(value) for value in weighted3]
        },
        "conclusion": "full_equivariant_coordinate_contact_through_third_jet",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
