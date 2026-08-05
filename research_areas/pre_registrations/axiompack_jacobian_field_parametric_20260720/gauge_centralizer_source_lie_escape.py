#!/usr/bin/env python3
"""Exact centralizer-profile classification and source graded Lie escape."""

from __future__ import annotations

import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_regular_singular_connection import (  # noqa: E402
    _inverse_action,
    source_only_connection,
)


def _graded_bracket(
    first_layer: int,
    second_layer: int,
    first: sp.Expr,
    second: sp.Expr,
    variable: sp.Symbol,
) -> sp.Expr:
    return sp.factor(
        (first_layer + second_layer + 3)
        * (
            first * sp.diff(second, variable) / (second_layer + 3)
            - second * sp.diff(first, variable) / (first_layer + 3)
        )
    )


def _spectral_project(
    value: sp.Expr,
    target_degree: int,
    operator,
) -> sp.Expr:
    eigenvalues = {
        degree: sp.Rational(4 - 3 * degree, 16)
        for degree in range(5)
    }
    result = value
    denominator = sp.Integer(1)
    target = eigenvalues[target_degree]
    for degree, eigenvalue in eigenvalues.items():
        if degree == target_degree:
            continue
        result = sp.expand(operator(result) - eigenvalue * result)
        denominator *= target - eigenvalue
    return sp.factor(result / denominator)


def run(regression_depth: int = 9) -> dict[str, object]:
    if regression_depth < 1:
        raise ValueError("regression_depth must be positive")

    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    family_p, family_q = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    source_only = data["source_only"]

    pullback_p3 = _inverse_action(
        jacobian,
        determinant,
        (sp.Integer(0), -3 * family_p**2),
    )
    pullback_q2 = _inverse_action(
        jacobian,
        determinant,
        (2 * family_q, sp.Integer(0)),
    )
    y = sp.symbols("y")
    affine_profile = sp.factor(
        6912
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    assert affine_profile.subs(s, 0) == 1

    # Extract only the lower normal jets needed by the source quotient.
    response_v = pullback_p3[0] / 36 + pullback_q2[0] / 4
    maximum_parameter_order = 2
    scalar_coefficients = [
        sp.diff(affine_profile, s, order).subs(s, 0)
        / factorial(order)
        for order in range(maximum_parameter_order + 1)
    ]
    source_coefficients = [
        sp.diff(source_only[0], s, order).subs(s, 0)
        / factorial(order)
        for order in range(maximum_parameter_order + 1)
    ]
    response_coefficients = [
        sp.diff(response_v, s, order).subs(s, 0)
        / factorial(order)
        for order in range(maximum_parameter_order + 1)
    ]

    g = sp.symbols("g")
    exceptional_substitution = {
        v: (y - 3) / 2,
        t: g - 1 + sp.Rational(3, 4) * (y - 3),
    }
    tangential_layers: dict[int, list[sp.Expr]] = {}
    for parameter_order in (1, 2):
        v_coefficient = source_coefficients[parameter_order] + sum(
            scalar_coefficients[index]
            * response_coefficients[parameter_order - index]
            for index in range(parameter_order + 1)
        )
        tangential = sp.expand(
            2 * v_coefficient.subs(exceptional_substitution)
        )
        tangential_layers[parameter_order] = [
            sp.factor(
                sp.diff(tangential, g, layer).subs(g, 0)
                / factorial(layer)
            )
            for layer in range(3)
        ]

    a0 = tangential_layers[1][0]
    b0 = tangential_layers[2][0]
    b1 = tangential_layers[2][1]
    assert sp.factor(a0 + (9 * y - 10) / 48) == 0
    assert b0 == 0
    expected_b1 = sp.factor(
        -(y - 1)
        * (21 * y**3 + 21 * y**2 + 5 * y - 31)
        / 192
    )
    assert sp.factor(b1 - expected_b1) == 0

    # H_0(F_0) has normal valuation three, so every H_0^k, k>=2,
    # changes tangential fields first at layer 3*k-3 >= 3.
    seed_h0 = sp.factor(
        (
            -family_p**3 / 36 - family_q**2 / 4
        )
        .subs(s, 0)
        .subs(exceptional_substitution)
    )
    seed_h0_polynomial = sp.Poly(seed_h0, g)
    seed_h0_valuation = min(
        monomial[0]
        for monomial, coefficient in seed_h0_polynomial.terms()
        if coefficient != 0
    )
    assert seed_h0_valuation == 3
    for power in (2, 3, 4):
        tangential_power = sp.cancel(
            sp.diff(seed_h0**power, g) / g**2
        )
        valuation = min(
            monomial[0]
            for monomial, coefficient in sp.Poly(
                tangential_power, g
            ).terms()
            if coefficient != 0
        )
        assert valuation == 3 * power - 3

    z = sp.symbols("z")
    a0_shifted = sp.factor(a0.subs(y, z + sp.Rational(10, 9)))
    b1_shifted = sp.expand(b1.subs(y, z + sp.Rational(10, 9)))
    assert a0_shifted == -sp.Rational(3, 16) * z
    b1_coefficients = {
        degree: sp.factor(b1_shifted.coeff(z, degree))
        for degree in range(5)
    }
    assert all(coefficient != 0 for coefficient in b1_coefficients.values())

    layer_one_operator = lambda value: _graded_bracket(  # noqa: E731
        0, 1, a0_shifted, value, z
    )
    eigenvalues = {
        degree: sp.Rational(4 - 3 * degree, 16)
        for degree in range(5)
    }
    for degree, eigenvalue in eigenvalues.items():
        assert sp.factor(
            layer_one_operator(z**degree) - eigenvalue * z**degree
        ) == 0

    e4 = _spectral_project(b1_shifted, 4, layer_one_operator)
    e3 = _spectral_project(b1_shifted, 3, layer_one_operator)
    assert sp.factor(e4 - b1_coefficients[4] * z**4) == 0
    assert sp.factor(e3 - b1_coefficients[3] * z**3) == 0

    seed = _graded_bracket(1, 1, e4, e3, z)
    seed_coefficient = sp.factor(seed.coeff(z, 6))
    assert seed_coefficient != 0
    assert sp.factor(seed - seed_coefficient * z**6) == 0

    ray_rows: list[dict[str, object]] = []
    current = seed
    current_coefficient = seed_coefficient
    for index in range(regression_depth):
        layer = 2 + index
        exponent = 6 + 3 * index
        assert sp.factor(
            current - current_coefficient * z**exponent
        ) == 0
        ray_rows.append(
            {
                "adjoint_depth": index,
                "normal_layer": layer,
                "z_degree": exponent,
                "source_degree": layer + exponent,
                "coefficient": str(current_coefficient),
            }
        )
        current = _graded_bracket(1, layer, e4, current, z)
        multiplier = sp.factor(
            b1_coefficients[4]
            * (index + 6)
            * sp.Rational(2 * index + 1, index + 5)
        )
        current_coefficient = sp.factor(
            current_coefficient * multiplier
        )

    j = sp.symbols("j", integer=True, nonnegative=True)
    recurrence_multiplier = sp.factor(
        b1_coefficients[4]
        * (j + 6)
        * (2 * j + 1)
        / (j + 5)
    )
    assert recurrence_multiplier != 0

    return {
        "schema": (
            "axiompack.jacobian_centralizer_source_lie_escape.v1"
        ),
        "divisor_profile_replay": "gauge_centralizer_divisor_profile.py",
        "unique_affine_profile": str(affine_profile),
        "higher_centralizer_controls": {
            "target_form": "sum_k u_k(s)*H_0^k",
            "H_0_seed_normal_valuation": seed_h0_valuation,
            "power_k_tangential_layer": "3*k-3",
            "lower_layers_immune_through": 2,
        },
        "source_graded_generators": {
            "gr_0_A": str(a0),
            "gr_1_B": str(b1),
            "shift": "z=y-10/9",
            "layer_one_eigenvalues": {
                str(degree): str(value)
                for degree, value in eigenvalues.items()
            },
            "projected_E4": str(e4),
            "projected_E3": str(e3),
            "seed_bracket": str(seed),
        },
        "all_order_source_ray": {
            "formula": (
                "gr(ad_E4^j([E4,E3]))="
                "c_j*D_(z^(6+3*j))^(2+j)"
            ),
            "coefficient_initial": str(seed_coefficient),
            "coefficient_recurrence_multiplier": str(
                recurrence_multiplier
            ),
            "source_degree": "8+4*j",
            "nonzero_for_every_j": True,
            "regression_rows": ray_rows,
        },
        "conclusion": (
            "every finite-dimensional polynomial target Hamiltonian algebra "
            "compatible with the normalized cusp seed has an "
            "infinite-dimensional full-source projection"
        ),
        "tail_minimax_decided": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
