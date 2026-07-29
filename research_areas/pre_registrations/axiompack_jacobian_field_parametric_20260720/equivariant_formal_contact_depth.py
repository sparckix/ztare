#!/usr/bin/env python3
"""Exact recursive source/target formal contact for the cubic weighted lift."""
from __future__ import annotations

import hashlib
import json
from math import factorial

import sympy as sp


ORDER = 6


def _zero() -> list[sp.Expr]:
    return [sp.Integer(0) for _ in range(ORDER + 1)]


def _add(left: list[sp.Expr], right: list[sp.Expr]) -> list[sp.Expr]:
    return [sp.expand(a + b) for a, b in zip(left, right, strict=True)]


def _scale(value: sp.Expr, series: list[sp.Expr]) -> list[sp.Expr]:
    return [sp.expand(value * coefficient) for coefficient in series]


def _mul(left: list[sp.Expr], right: list[sp.Expr]) -> list[sp.Expr]:
    result = _zero()
    for i, a in enumerate(left):
        for j, b in enumerate(right[: ORDER + 1 - i]):
            result[i + j] += a * b
    return [sp.expand(value) for value in result]


def _pow(series: list[sp.Expr], exponent: int) -> list[sp.Expr]:
    result = _zero()
    result[0] = sp.Integer(1)
    for _ in range(exponent):
        result = _mul(result, series)
    return result


def _shift(series: list[sp.Expr], amount: int) -> list[sp.Expr]:
    return _zero()[:amount] + series[: ORDER + 1 - amount]


def _evaluate(
    polynomial: sp.Expr,
    first_symbol: sp.Symbol,
    second_symbol: sp.Symbol,
    first_series: list[sp.Expr],
    second_series: list[sp.Expr],
) -> list[sp.Expr]:
    result = _zero()
    for (i, j), coefficient in sp.Poly(
        polynomial, first_symbol, second_symbol
    ).terms():
        term = _scale(
            coefficient,
            _mul(_pow(first_series, i), _pow(second_series, j)),
        )
        result = _add(result, term)
    return result


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode()).hexdigest()


def _family() -> dict[str, object]:
    s, v, t, z = sp.symbols("s v t z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    beta = sp.cancel(lam / mu * (1 + p.subs(z, w) / gamma))
    alpha = sp.cancel((1 + mu * v + q.subs(z, w) / gamma**2) / lam)
    p_series = [
        sp.cancel(gamma * sp.diff(beta, s, order).subs(s, 0) / factorial(order))
        for order in range(ORDER + 1)
    ]
    q_series = [
        sp.cancel(gamma**2 * sp.diff(alpha, s, order).subs(s, 0) / factorial(order))
        for order in range(ORDER + 1)
    ]
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in p_series + q_series
    )
    return {
        "symbols": (v, t),
        "gamma": gamma,
        "P": p_series,
        "Q": q_series,
    }


def _target_removed(data: dict[str, object]) -> tuple[list[sp.Expr], list[sp.Expr]]:
    target_p, target_q = sp.symbols("P Q")

    def derivation(value: sp.Expr) -> sp.Expr:
        return sp.expand(
            -target_q * sp.diff(value, target_p) / 2 +
            target_p**2 * sp.diff(value, target_q) / 12
        )

    powers_p, powers_q = [target_p], [target_q]
    for _ in range(ORDER):
        powers_p.append(derivation(powers_p[-1]))
        powers_q.append(derivation(powers_q[-1]))

    result_p, result_q = _zero(), _zero()
    for order in range(ORDER + 1):
        coefficient = sp.Rational((-1) ** order, factorial(order))
        evaluated_p = _evaluate(
            powers_p[order], target_p, target_q, data["P"], data["Q"]
        )
        evaluated_q = _evaluate(
            powers_q[order], target_p, target_q, data["P"], data["Q"]
        )
        result_p = _add(result_p, _scale(coefficient, _shift(evaluated_p, order)))
        result_q = _add(result_q, _scale(coefficient, _shift(evaluated_q, order)))
    return result_p, result_q


def _infinitesimally_liftable(
    value_u: sp.Expr,
    value_v: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
) -> bool:
    return bool(
        value_u.subs({v: 0, t: 0}) == 0
        and value_v.subs(t, 0).subs(v, 0) == 0
        and sp.diff(value_v.subs(t, 0), v).subs(v, 0) == 0
    )


def run() -> dict[str, object]:
    data = _family()
    v, t = data["symbols"]
    target_p, target_q = _target_removed(data)
    assert sp.cancel(target_p[1]) == 0 and sp.cancel(target_q[1]) == 0

    source_v, source_t = _zero(), _zero()
    source_v[0], source_t[0] = v, t
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    assert sp.cancel(jacobian.det() + data["gamma"]**2) == 0
    rows = []
    for order in range(2, ORDER + 1):
        composed_p = _evaluate(p0, v, t, source_v, source_t)
        composed_q = _evaluate(q0, v, t, source_v, source_t)
        rhs = sp.Matrix([
            sp.expand(target_p[order] - composed_p[order]),
            sp.expand(target_q[order] - composed_q[order]),
        ])
        coefficient = [sp.cancel(value) for value in jacobian.inv() * rhs]
        assert all(sp.denom(value) == 1 for value in coefficient)
        source_v[order], source_t[order] = coefficient
        assert _infinitesimally_liftable(coefficient[0], coefficient[1], v, t)
        recomposed_p = _evaluate(p0, v, t, source_v, source_t)
        recomposed_q = _evaluate(q0, v, t, source_v, source_t)
        assert sp.cancel(recomposed_p[order] - target_p[order]) == 0
        assert sp.cancel(recomposed_q[order] - target_q[order]) == 0
        rows.append({
            "order": order,
            "ordinary_series_not_derivative": True,
            "U_degree": sp.Poly(coefficient[0], v, t).total_degree(),
            "V_degree": sp.Poly(coefficient[1], v, t).total_degree(),
            "U_sha256": _sha(coefficient[0]),
            "V_sha256": _sha(coefficient[1]),
            "polynomial": True,
            "infinitesimal_equivariant_lift_ideals": True,
            "recomposition_zero": True,
        })

    final_p = _evaluate(p0, v, t, source_v, source_t)
    final_q = _evaluate(q0, v, t, source_v, source_t)
    assert all(sp.cancel(final_p[i] - target_p[i]) == 0 for i in range(ORDER + 1))
    assert all(sp.cancel(final_q[i] - target_q[i]) == 0 for i in range(ORDER + 1))
    return {
        "schema": "axiompack.jacobian_quotient_contact_depth.v2",
        "max_order": ORDER,
        "target_flow": "exp(-s*(-Q/2*dP + P^2/12*dQ))",
        "rows": rows,
        "reproduces_independent_derivative_hashes": {
            "order_2_U": _sha(2 * source_v[2]),
            "order_2_V": _sha(2 * source_t[2]),
            "order_3_U": _sha(6 * source_v[3]),
            "order_3_V": _sha(6 * source_t[3]),
        },
        "all_quotient_coefficients_polynomial_and_infinitesimally_liftable": True,
        "full_recomposition_zero_through_order": ORDER,
        "conclusion": "quotient_coordinate_contact_through_order_6",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
