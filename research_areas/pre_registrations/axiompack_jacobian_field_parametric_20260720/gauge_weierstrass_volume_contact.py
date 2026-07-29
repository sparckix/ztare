#!/usr/bin/env python3
"""Exact finite-order test of the Weierstrass volume correction.

The finite cubic gives a liftable target map C_s with nonunit Jacobian.
Conjugating its Jacobian density to the target and integrating in P gives a
canonical triangular correction H_s.  This replay checks

    E_s = H_s o C_s,       det D E_s = 1,
    F_0 o S_s = E_s o F_s

and tests polynomiality, equivariant lift ideals, and filtered degree bounds.
"""
from __future__ import annotations

import hashlib
import json
from math import factorial

import sympy as sp


Series = list[sp.Expr]
MapSeries = tuple[Series, Series]


def _zero(order: int) -> Series:
    return [sp.Integer(0) for _ in range(order + 1)]


def _one(order: int) -> Series:
    result = _zero(order)
    result[0] = sp.Integer(1)
    return result


def _add(*values: Series) -> Series:
    return [
        sp.expand(sum(value[index] for value in values))
        for index in range(len(values[0]))
    ]


def _neg(value: Series) -> Series:
    return [-coefficient for coefficient in value]


def _scale(value: Series, scalar: sp.Expr) -> Series:
    return [sp.expand(scalar * coefficient) for coefficient in value]


def _multiply(left: Series, right: Series) -> Series:
    return [
        sp.expand(sum(
            left[index] * right[order - index]
            for index in range(order + 1)
        ))
        for order in range(len(left))
    ]


def _power(value: Series, exponent: int) -> Series:
    result = _one(len(value) - 1)
    for _ in range(exponent):
        result = _multiply(result, value)
    return result


def _shift(value: Series, amount: int) -> Series:
    return _zero(len(value) - 1)[:amount] + value[:len(value) - amount]


def _evaluate(
    polynomial: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
    first_series: Series,
    second_series: Series,
) -> Series:
    result = _zero(len(first_series) - 1)
    for (i, j), coefficient in sp.Poly(
        polynomial, first, second, domain=sp.QQ
    ).terms():
        result = _add(
            result,
            _scale(
                _multiply(
                    _power(first_series, i),
                    _power(second_series, j),
                ),
                coefficient,
            ),
        )
    return result


def _compose_map(
    outer: MapSeries,
    inner: MapSeries,
    first: sp.Symbol,
    second: sp.Symbol,
) -> MapSeries:
    result = [_zero(len(inner[0]) - 1), _zero(len(inner[0]) - 1)]
    for parameter_order in range(len(outer[0])):
        for component in range(2):
            evaluated = _evaluate(
                outer[component][parameter_order],
                first,
                second,
                inner[0],
                inner[1],
            )
            result[component] = _add(
                result[component],
                _shift(evaluated, parameter_order),
            )
    return result[0], result[1]


def _compose_scalar(
    outer: Series,
    inner: MapSeries,
    first: sp.Symbol,
    second: sp.Symbol,
) -> Series:
    result = _zero(len(outer) - 1)
    for parameter_order, coefficient in enumerate(outer):
        result = _add(
            result,
            _shift(
                _evaluate(
                    coefficient,
                    first,
                    second,
                    inner[0],
                    inner[1],
                ),
                parameter_order,
            ),
        )
    return result


def _jacobian(map_series: MapSeries, p: sp.Symbol, q: sp.Symbol) -> Series:
    return [
        sp.expand(sum(
            sp.diff(map_series[0][index], p)
            * sp.diff(map_series[1][order - index], q)
            - sp.diff(map_series[0][index], q)
            * sp.diff(map_series[1][order - index], p)
            for index in range(order + 1)
        ))
        for order in range(len(map_series[0]))
    ]


def _inverse_map(
    value: MapSeries, p: sp.Symbol, q: sp.Symbol
) -> MapSeries:
    order = len(value[0]) - 1
    inverse: MapSeries = (_zero(order), _zero(order))
    inverse[0][0], inverse[1][0] = p, q
    for parameter_order in range(1, order + 1):
        residual = _compose_map(value, inverse, p, q)
        inverse[0][parameter_order] = -residual[0][parameter_order]
        inverse[1][parameter_order] = -residual[1][parameter_order]
    identity = _compose_map(value, inverse, p, q)
    assert identity[0][0] == p and identity[1][0] == q
    assert all(
        identity[component][index] == 0
        for component in range(2)
        for index in range(1, order + 1)
    )
    return inverse


def _inverse_scalar(value: Series) -> Series:
    assert value[0] == 1
    result = _one(len(value) - 1)
    for order in range(1, len(value)):
        result[order] = sp.expand(-sum(
            value[index] * result[order - index]
            for index in range(1, order + 1)
        ))
    assert _multiply(value, result) == _one(len(value) - 1)
    return result


def _scalar_series(
    value: sp.Expr, parameter: sp.Symbol, order: int
) -> Series:
    return [
        sp.cancel(
            sp.diff(value, parameter, index).subs(parameter, 0)
            / factorial(index)
        )
        for index in range(order + 1)
    ]


def _weierstrass_map(order: int, p: sp.Symbol, q: sp.Symbol) -> MapSeries:
    s = sp.Symbol("s")
    # One extra coefficient is needed because z/a=4z/s+2z.
    a_full = _scalar_series(s / (2 * (s + 2)), s, order + 1)
    b_full = _scalar_series((s + 4) / (2 * (s + 2)), s, order + 1)
    c_full = _scalar_series(12 / ((s - 6) * (s + 2)), s, order + 1)
    d_full = _scalar_series(-(s - 4) / (2 * (s + 2)), s, order + 1)

    z = _zero(order + 1)
    for _ in range(order + 3):
        z = _add(
            a_full,
            _multiply(b_full, _power(z, 2)),
            _scale(
                _multiply(c_full, _power(z, 3)),
                p,
            ),
            _scale(
                _multiply(d_full, _power(z, 4)),
                q,
            ),
        )
    ratio = [
        sp.expand(4 * z[index + 1] + 2 * z[index])
        for index in range(order + 1)
    ]
    b = b_full[:order + 1]
    c = c_full[:order + 1]
    d = d_full[:order + 1]
    z = z[:order + 1]
    a_cubic = _neg(_multiply(
        ratio,
        _add(
            b,
            _scale(_multiply(c, z[:order + 1]), p),
            _scale(_multiply(d, _power(z, 2)[:order + 1]), q),
        ),
    ))
    b_cubic = _neg(_multiply(
        ratio,
        _add(
            _scale(c, p),
            _scale(_multiply(d, z[:order + 1]), q),
        ),
    ))
    c_cubic = _neg(_scale(_multiply(ratio, d), q))
    one = _one(order)
    shift = _scale(_add(a_cubic, one), sp.Rational(1, 3))
    normalized_p = _add(
        b_cubic,
        _scale(
            _add(one, _neg(_power(a_cubic, 2))),
            sp.Rational(1, 3),
        ),
    )
    normalized_q = _add(
        _neg(c_cubic),
        _multiply(shift, b_cubic),
        _neg(_scale(
            _multiply(
                _power(shift, 2),
                _add(_scale(a_cubic, 2), _neg(one)),
            ),
            sp.Rational(1, 3),
        )),
    )
    assert normalized_p[0] == p and normalized_q[0] == q
    return normalized_p, normalized_q


def _family(
    order: int, v: sp.Symbol, t: sp.Symbol
) -> tuple[MapSeries, sp.Expr]:
    s, z = sp.symbols("s z")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * gamma
    p_poly = (2 + s / 2) * z + (-3 - 3 * s / 2) * z**2 + s * z**3
    q_poly = (1 + s / 4) * z**2 - (2 + s) * z**3 + 3 * s * z**4 / 4
    p_exact = sp.cancel(lam / mu * (gamma + p_poly.subs(z, w)))
    q_exact = sp.cancel(
        (gamma**2 * (1 + mu * v) + q_poly.subs(z, w)) / lam
    )
    family = (
        _scalar_series(p_exact, s, order),
        _scalar_series(q_exact, s, order),
    )
    assert all(
        not ({v, t} & sp.denom(coefficient).free_symbols)
        for component in family
        for coefficient in component
    )
    return family, gamma


def _degree(value: sp.Expr, first: sp.Symbol, second: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, first, second, domain=sp.QQ).total_degree())


def _filtered_degree(value: sp.Expr, p: sp.Symbol, q: sp.Symbol) -> int:
    if value == 0:
        return -1
    return max(
        4 * i + 6 * j
        for (i, j), coefficient in sp.Poly(
            value, p, q, domain=sp.QQ
        ).terms()
        if coefficient
    )


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode()).hexdigest()


def _top_part(
    value: sp.Expr, first: sp.Symbol, second: sp.Symbol
) -> sp.Expr:
    degree = _degree(value, first, second)
    if degree < 0:
        return sp.Integer(0)
    return sp.factor(sum(
        coefficient * first**i * second**j
        for (i, j), coefficient in sp.Poly(
            value, first, second, domain=sp.QQ
        ).terms()
        if i + j == degree
    ))


def _lift_source(
    target: MapSeries,
    target_jacobian: Series,
    family: MapSeries,
    gamma: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    *,
    include_first_factor: bool,
) -> tuple[MapSeries, list[dict[str, object]], str]:
    order = len(target[0]) - 1
    target_at_family = _compose_map(target, family, p, q)
    p0, q0 = family[0][0], family[1][0]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    assert sp.cancel(jacobian.det() + gamma**2) == 0

    source: MapSeries = (_zero(order), _zero(order))
    source[0][0], source[1][0] = v, t
    rows = []
    for parameter_order in range(1, order + 1):
        composed = (
            _evaluate(p0, v, t, source[0], source[1]),
            _evaluate(q0, v, t, source[0], source[1]),
        )
        residual = sp.Matrix([
            target_at_family[0][parameter_order]
            - composed[0][parameter_order],
            target_at_family[1][parameter_order]
            - composed[1][parameter_order],
        ])
        coefficient = [
            sp.cancel(item) for item in jacobian.inv() * residual
        ]
        assert all(sp.denom(item) == 1 for item in coefficient)
        source[0][parameter_order] = coefficient[0]
        source[1][parameter_order] = coefficient[1]
        assert coefficient[0].subs({v: 0, t: 0}) == 0
        assert coefficient[1].subs({v: 0, t: 0}) == 0
        assert sp.diff(coefficient[1], v).subs({v: 0, t: 0}) == 0
        rows.append({
            "order": parameter_order,
            "V_degree": _degree(coefficient[0], v, t),
            "T_degree": _degree(coefficient[1], v, t),
            "V_top": str(_top_part(coefficient[0], v, t)),
            "T_top": str(_top_part(coefficient[1], v, t)),
            "lift_ideals": True,
            "V_sha256": _sha(coefficient[0]),
            "T_sha256": _sha(coefficient[1]),
            **({
                "V_factor": str(sp.factor(coefficient[0])),
                "T_factor": str(sp.factor(coefficient[1])),
            } if include_first_factor and parameter_order == 1 else {}),
        })

    recomposed = (
        _evaluate(p0, v, t, source[0], source[1]),
        _evaluate(q0, v, t, source[0], source[1]),
    )
    assert recomposed == target_at_family

    source_gamma = _add(
        _one(order),
        _scale(source[0], -sp.Rational(3, 2)),
        source[1],
    )
    source_w = _multiply(
        _add(_one(order), source[0]),
        source_gamma,
    )
    source_l = _add(
        _scale(source[1], 2),
        _scale(source[0], -3),
    )
    source_r = _multiply(source[0], source_l)
    for parameter_order, row in enumerate(rows, start=1):
        row["gamma_degree"] = _degree(
            source_gamma[parameter_order], v, t
        )
        row["W_degree"] = _degree(
            source_w[parameter_order], v, t
        )
        row["vL_degree"] = _degree(
            source_r[parameter_order], v, t
        )

    weighted_source_jacobian = _multiply(
        _power(source_gamma, 2),
        _jacobian(source, v, t),
    )
    target_multiplier = _compose_scalar(
        target_jacobian, family, p, q
    )
    expected = _scale(target_multiplier, gamma**2)
    assert weighted_source_jacobian == expected
    multiplier_description = (
        "1" if target_multiplier == _one(order)
        else "Jac(target)(F_s)"
    )
    return source, rows, multiplier_description


def run(order: int = 3) -> dict[str, object]:
    if order < 2:
        raise ValueError("order must expose the nonlinear correction")
    p, q, v, t = sp.symbols("P Q v t")
    c_map = _weierstrass_map(order, p, q)
    c_inverse = _inverse_map(c_map, p, q)
    c_jacobian = _jacobian(c_map, p, q)
    transported_jacobian = _compose_scalar(
        c_jacobian, c_inverse, p, q
    )
    density = _inverse_scalar(transported_jacobian)

    h_map: MapSeries = (_zero(order), _zero(order))
    h_map[0][0], h_map[1][0] = p, q
    for parameter_order in range(1, order + 1):
        h_map[0][parameter_order] = sp.integrate(
            density[parameter_order], (p, 0, p)
        )
    corrected = _compose_map(h_map, c_map, p, q)
    corrected_jacobian = _jacobian(corrected, p, q)
    assert corrected_jacobian == _one(order)

    target_rows = []
    for parameter_order in range(1, order + 1):
        first, second = (
            corrected[0][parameter_order],
            corrected[1][parameter_order],
        )
        assert first.subs({p: 0, q: 0}) == 0
        assert second.subs({p: 0, q: 0}) == 0
        assert sp.diff(second, p).subs({p: 0, q: 0}) == 0
        assert _filtered_degree(first, p, q) <= 2 * parameter_order + 4
        assert _filtered_degree(second, p, q) <= 2 * parameter_order + 6
        target_rows.append({
            "order": parameter_order,
            "P_filtered_degree": _filtered_degree(first, p, q),
            "Q_filtered_degree": _filtered_degree(second, p, q),
            "lift_ideals": True,
            "P_sha256": _sha(first),
            "Q_sha256": _sha(second),
        })

    family, gamma = _family(order, v, t)
    _, uncorrected_rows, uncorrected_multiplier = _lift_source(
        c_map,
        c_jacobian,
        family,
        gamma,
        p,
        q,
        v,
        t,
        include_first_factor=False,
    )
    _, source_rows, corrected_multiplier = _lift_source(
        corrected,
        corrected_jacobian,
        family,
        gamma,
        p,
        q,
        v,
        t,
        include_first_factor=True,
    )

    return {
        "schema": "axiompack.jacobian_weierstrass_volume_contact.v1",
        "checked_through_s_order": order,
        "target_volume_correction": {
            "construction": (
                "H(P,Q)=(integral_0^P "
                "1/(Jac(C) o C^-1)(u,Q) du,Q)"
            ),
            "corrected_jacobian": "1",
            "target_rows": target_rows,
        },
        "source_lift": {
            "polynomial": True,
            "equivariant_lift_ideals": True,
            "weighted_jacobian_identity": (
                f"gamma(S)^2*Jac(S)={corrected_multiplier}*gamma^2"
            ),
            "rows": source_rows,
        },
        "uncorrected_weierstrass_source_lift": {
            "polynomial": True,
            "equivariant_lift_ideals": True,
            "weighted_jacobian_identity": (
                f"gamma(S)^2*Jac(S)={uncorrected_multiplier}*gamma^2"
            ),
            "rows": uncorrected_rows,
        },
        "claim_boundary": (
            "the uncorrected cubic source has slope two through the replay; "
            "the canonical triangular volume correction is liftable and "
            "volume-preserving but fails source slope two at order one; "
            "its sharp all-order 6*n+1 prediction remains to be proved"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
