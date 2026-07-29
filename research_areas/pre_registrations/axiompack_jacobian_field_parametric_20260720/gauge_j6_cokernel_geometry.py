#!/usr/bin/env python3
"""Exact adapted-chart identity tests for the order-six cokernels."""
from __future__ import annotations

import hashlib
import json

import sympy as sp


V, G, v, t, scale = sp.symbols("V G v t c", nonzero=True)


def _coefficient(
    value: sp.Expr,
    first: sp.Symbol,
    first_power: int,
    second: sp.Symbol,
    second_power: int,
) -> sp.Expr:
    return sp.Poly(
        sp.expand(value), first, second
    ).coeff_monomial(first**first_power * second**second_power)


def _to_original(value: sp.Expr) -> sp.Expr:
    return sp.expand(
        value.subs({V: v, G: t - sp.Rational(3, 2) * v})
    )


def _cone(value: sp.Expr) -> sp.Expr:
    original = _to_original(value)
    return sp.expand(
        25 * _coefficient(original, v, 8, t, 9)
        + 2 * _coefficient(original, v, 9, t, 8)
    )


def _parity(value: sp.Expr) -> sp.Expr:
    return _coefficient(_to_original(value), v, 9, t, 9)


def _apply(
    value: sp.Expr,
    operation,
    count: int,
) -> sp.Expr:
    for _ in range(count):
        value = operation(value)
    return sp.expand(value)


def _source_boundary(
    degree: int,
) -> tuple[list[sp.Symbol], sp.Expr, sp.Expr]:
    coefficients = list(sp.symbols(f"a0:{degree + 1}"))
    first = sum(
        coefficients[index]
        * V**index
        * G ** (degree - index)
        for index in range(degree + 1)
    )
    second_coefficients = [
        -sp.Rational(index + 1, degree - index + 2)
        * coefficients[index + 1]
        for index in range(degree)
    ] + [sp.Integer(0)]
    second = sum(
        second_coefficients[index]
        * V**index
        * G ** (degree - index)
        for index in range(degree + 1)
    )
    assert sp.expand(
        sp.diff(G**2 * first, V)
        + sp.diff(G**2 * second, G)
    ) == 0
    return coefficients, first, second


def _exceptional_jet_kills(
    functional,
    degree: int,
    first_supported_g_power: int,
) -> list[dict[str, object]]:
    """Counterexamples to factorization through jets on G+1=0."""

    rows = []
    for jet_order in range(degree):
        g_power = max(first_supported_g_power, jet_order + 1)
        if g_power > degree:
            break
        witness = (
            (G + 1) ** (jet_order + 1)
            * V ** (degree - g_power)
            * G ** (g_power - jet_order - 1)
        )
        for derivative_order in range(jet_order + 1):
            assert sp.expand(
                sp.diff(witness, G, derivative_order).subs(G, -1)
            ) == 0
        value = sp.expand(functional(witness))
        assert value != 0
        rows.append({
            "jet_order": jet_order,
            "witness": str(witness),
            "functional_value": str(value),
        })
    return rows


def run() -> dict[str, object]:
    cone_coefficients = sp.symbols("c0:18")
    cone_form = sum(
        cone_coefficients[index]
        * V ** (17 - index)
        * G**index
        for index in range(18)
    )
    parity_coefficients = sp.symbols("d0:19")
    parity_form = sum(
        parity_coefficients[index]
        * V ** (18 - index)
        * G**index
        for index in range(19)
    )
    original_v_direction = lambda value: (
        sp.diff(value, V)
        - sp.Rational(3, 2) * sp.diff(value, G)
    )
    normal = lambda value: sp.diff(value, G)
    third = lambda value: (
        sp.diff(value, V) + 11 * sp.diff(value, G)
    )
    cone_factored = (
        sp.Rational(2, sp.factorial(8) * sp.factorial(9))
        * _apply(
            _apply(third(cone_form), normal, 8),
            original_v_direction,
            8,
        )
    )
    parity_factored = (
        _apply(
            _apply(parity_form, normal, 9),
            original_v_direction,
            9,
        )
        / sp.factorial(9) ** 2
    )
    assert sp.expand(_cone(cone_form) - cone_factored) == 0
    assert sp.expand(_parity(parity_form) - parity_factored) == 0

    p_bar = -3 * (V * G) ** 2
    boundary_rows = {}
    for name, degree, functional in (
        ("cone", 14, _cone),
        ("parity", 15, _parity),
    ):
        coefficients, first, second = _source_boundary(degree)
        image = sp.expand(
            sp.diff(p_bar, V) * first
            + sp.diff(p_bar, G) * second
        )
        value = sp.factor(functional(image))
        nonzero = [
            index
            for index, coefficient in enumerate(coefficients)
            if sp.diff(value, coefficient) != 0
        ]
        assert value != 0
        boundary_rows[name] = {
            "source_degree": degree,
            "image_degree": int(
                sp.Poly(image, V, G).total_degree()
            ),
            "nonzero_source_coordinates": nonzero,
            "functional_pullback": str(value),
        }

    cone_jet_kills = _exceptional_jet_kills(_cone, 17, 8)
    parity_jet_kills = _exceptional_jet_kills(_parity, 18, 9)
    slope_ratio = sp.factor(
        (11 / scale**2)
        / (-sp.Rational(3, 2) / scale**2)
    )
    assert slope_ratio == -sp.Rational(22, 3)

    payload = {
        "schema": "axiompack.jacobian_j6_cokernel_geometry.v1",
        "adapted_chart": {"V": "v", "G": "t-3*v/2"},
        "cone_symbol": (
            "2/(8!*9!)*(D_V-3/2 D_G)^8*D_G^8*(D_V+11 D_G)"
        ),
        "parity_symbol": (
            "1/(9!*9!)*(D_V-3/2 D_G)^9*D_G^9"
        ),
        "projective_root_multiplicities": {
            "cone": [8, 8, 1],
            "parity": [9, 9],
        },
        "cusp_axes": ["D_V", "D_G"],
        "cone_third_to_tangent_slope_ratio_under_VG_torus": str(
            slope_ratio
        ),
        "exceptional_line": "G+1=0",
        "exceptional_jet_kills": {
            "cone_orders_0_to_16": cone_jet_kills,
            "parity_orders_0_to_17": parity_jet_kills,
        },
        "weighted_source_boundary": boundary_rows,
        "verdict": (
            "Both rows are exact projective polar symbols of the "
            "normalized chart and are nonzero on the first newly allowed "
            "weighted-divergence-free source boundary. Neither factors "
            "through any proper exceptional-line normal jet. The cone "
            "symbol has a third projective direction, so it is not a pure "
            "cusp tangent/normal quotient; coefficient 11 is chart data, "
            "while the root configuration is the covariant datum."
        ),
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
