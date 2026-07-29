#!/usr/bin/env python3
"""Replay the completed inverse factor and its weighted Rees boundary.

The replay checks four exact mechanisms:

* the reciprocal escaping factor is a unit in the coefficientwise s-adic
  ring, so the inverse algebra is presented by a monic cubic;
* an identity-normalized generator translation makes the reciprocal root
  target-scalar;
* the diagonal Rees boundary of the deformed map has a node, while the seed
  boundary is a cusp;
* a tail-limsup statement cannot be transferred from logarithms to
  instantaneous velocities without controlling the finite prefix.
"""
from __future__ import annotations

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
    a: sp.Expr,
    b: sp.Expr,
    c: sp.Expr,
    d: sp.Expr,
    order: int,
) -> sp.Expr:
    result = sp.Integer(0)
    for _ in range(order + 1):
        result = _truncate(
            a
            + b * result**2
            + c * first * result**3
            + d * second * result**4,
            parameter,
            order,
        )
    return result


def _filtered_degree(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> int:
    if value == 0:
        return -1
    return max(
        4 * powers[0] + 6 * powers[1]
        for powers, _ in sp.Poly(
            sp.expand(value), first, second
        ).terms()
    )


def _ordinary_degree(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> int:
    if value == 0:
        return -1
    return sp.Poly(sp.expand(value), first, second).total_degree()


def _poisson(
    left: sp.Expr,
    right: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        sp.diff(left, first) * sp.diff(right, second)
        - sp.diff(left, second) * sp.diff(right, first)
    )


def run() -> dict[str, object]:
    s, p, q, w, z = sp.symbols("s P Q W z")

    a = s / (2 * (s + 2))
    b = (s + 4) / (2 * (s + 2))
    c = 12 / ((s - 6) * (s + 2))
    d = -(s - 4) / (2 * (s + 2))

    inverse_quartic = (
        w**3 - a * w**4 - b * w**2 - c * p * w - d * q
    )
    fixed_residual = (
        z - a - b * z**2 - c * p * z**3 - d * q * z**4
    )
    root_ratio = z / a
    cubic_a = -root_ratio * (
        b + c * p * z + d * q * z**2
    )
    cubic_b = -root_ratio * (c * p + d * q * z)
    cubic_c = -root_ratio * d * q
    finite_cubic = (
        w**3 + cubic_a * w**2 + cubic_b * w + cubic_c
    )

    factor_residual = sp.factor(
        root_ratio * inverse_quartic
        - (1 - z * w) * finite_cubic
    )
    factor_multiplier = sp.factor(
        factor_residual / fixed_residual
    )
    assert sp.factor(
        factor_residual - factor_multiplier * fixed_residual
    ) == 0
    assert factor_multiplier == 2 * w**3 * (s + 2) / s

    unit_depth = 7
    unit_partial_inverse = sum(
        (z * w) ** power for power in range(unit_depth)
    )
    assert sp.expand(
        (1 - z * w) * unit_partial_inverse
        - (1 - (z * w) ** unit_depth)
    ) == 0

    scalar_root = s / (s + 4)
    assert sp.factor(
        scalar_root - a - b * scalar_root**2
    ) == 0
    root_difference_identity = sp.factor(
        (z - scalar_root) * (1 - b * (z + scalar_root))
        - c * p * z**3
        - d * q * z**4
        - fixed_residual
    )
    assert root_difference_identity == 0

    generator_translation = 1 / scalar_root - 1 / z
    translated_w = w + generator_translation
    flattening_identity = sp.factor(
        (1 - z * w)
        - (z / scalar_root) * (1 - scalar_root * translated_w)
    )
    assert flattening_identity == 0

    prefix_order = 6
    root_prefix = _fixed_point_prefix(
        parameter=s,
        first=p,
        second=q,
        a=a,
        b=b,
        c=c,
        d=d,
        order=prefix_order,
    )
    translation_prefix = sp.expand(
        sp.series(
            1 / scalar_root - 1 / root_prefix,
            s,
            0,
            prefix_order - 2,
        ).removeO()
    )
    assert translation_prefix.subs(s, 0) == 0
    assert translation_prefix.subs({p: 0, q: 0}) == 0

    translation_shells: list[dict[str, object]] = []
    for parameter_order in range(1, prefix_order - 2):
        coefficient = sp.expand(
            translation_prefix.coeff(s, parameter_order)
        )
        filtered_degree = _filtered_degree(coefficient, p, q)
        ordinary_degree = _ordinary_degree(coefficient, p, q)
        assert filtered_degree <= 2 * parameter_order + 2
        assert ordinary_degree <= (parameter_order + 1) // 2
        translation_shells.append({
            "parameter_order": parameter_order,
            "coefficient": str(sp.factor(coefficient)),
            "filtered_degree": filtered_degree,
            "ordinary_target_degree": ordinary_degree,
            "critical_filtered_bound": 2 * parameter_order + 2,
        })

    x, y, capital_z = sp.symbols("x y Z")
    top_equation = capital_z - sp.Rational(1, 4)
    top_equation += x * capital_z**3 - y * capital_z**4
    top_translation = 4 - 1 / capital_z
    top_translation_polynomial = (
        -4 * x * capital_z**2 + 4 * y * capital_z**3
    )
    assert sp.factor(
        capital_z
        * (top_translation - top_translation_polynomial)
        - 4 * top_equation
    ) == 0

    epsilon, tau = sp.symbols(
        "epsilon tau", nonzero=True
    )
    v, t, capital_v, capital_t = sp.symbols("v t V T")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    family_w = (1 + mu * v) * gamma
    polynomial_variable = sp.symbols("polynomial_variable")
    family_polynomial_p = (
        (2 + s / 2) * polynomial_variable
        + (-3 - 3 * s / 2) * polynomial_variable**2
        + s * polynomial_variable**3
    )
    family_polynomial_q = (
        (1 + s / 4) * polynomial_variable**2
        - (2 + s) * polynomial_variable**3
        + 3 * s * polynomial_variable**4 / 4
    )
    family_p = sp.cancel(
        lam / mu
        * (
            gamma
            + family_polynomial_p.subs(
                polynomial_variable, family_w
            )
        )
    )
    family_q = sp.cancel(
        (
            gamma**2 * (1 + mu * v)
            + family_polynomial_q.subs(
                polynomial_variable, family_w
            )
        )
        / lam
    )

    rees_substitution = {
        s: tau * epsilon**2,
        v: capital_v / epsilon,
        t: capital_t / epsilon,
    }
    boundary_p = sp.factor(sp.limit(
        sp.cancel(
            epsilon**4 * family_p.subs(rees_substitution)
        ),
        epsilon,
        0,
    ))
    boundary_q = sp.factor(sp.limit(
        sp.cancel(
            epsilon**6 * family_q.subs(rees_substitution)
        ),
        epsilon,
        0,
    ))
    boundary_linear = capital_t - sp.Rational(3, 2) * capital_v
    boundary_root = capital_v * boundary_linear
    expected_boundary_p = (
        tau * boundary_root**3 - 3 * boundary_root**2
    )
    expected_boundary_q = (
        sp.Rational(3, 4) * tau * boundary_root**4
        - 2 * boundary_root**3
    )
    assert sp.factor(boundary_p - expected_boundary_p) == 0
    assert sp.factor(boundary_q - expected_boundary_q) == 0

    seed_p = sp.cancel(family_p.subs(s, 0))
    seed_q = sp.cancel(family_q.subs(s, 0))
    seed_substitution = {
        v: capital_v / epsilon,
        t: capital_t / epsilon,
    }
    boundary_seed_p = sp.factor(sp.limit(
        sp.cancel(
            epsilon**4 * seed_p.subs(seed_substitution)
        ),
        epsilon,
        0,
    ))
    boundary_seed_q = sp.factor(sp.limit(
        sp.cancel(
            epsilon**6 * seed_q.subs(seed_substitution)
        ),
        epsilon,
        0,
    ))
    assert sp.factor(
        boundary_seed_p + 3 * boundary_root**2
    ) == 0
    assert sp.factor(
        boundary_seed_q + 2 * boundary_root**3
    ) == 0

    normalization_parameter = sp.symbols("r")
    curve_p = (
        tau * normalization_parameter**3
        - 3 * normalization_parameter**2
    )
    curve_q = (
        sp.Rational(3, 4)
        * tau
        * normalization_parameter**4
        - 2 * normalization_parameter**3
    )
    square_root_three = sp.sqrt(3)
    node_plus = (1 + square_root_three) / tau
    node_minus = (1 - square_root_three) / tau
    node_image_plus = (
        sp.factor(curve_p.subs(normalization_parameter, node_plus)),
        sp.factor(curve_q.subs(normalization_parameter, node_plus)),
    )
    node_image_minus = (
        sp.factor(curve_p.subs(normalization_parameter, node_minus)),
        sp.factor(curve_q.subs(normalization_parameter, node_minus)),
    )
    expected_node = (-2 / tau**2, 1 / tau**3)
    assert all(
        sp.factor(left - right) == 0
        for left, right in zip(node_image_plus, expected_node)
    )
    assert all(
        sp.factor(left - right) == 0
        for left, right in zip(node_image_minus, expected_node)
    )

    curve_tangent = sp.Matrix([
        sp.diff(curve_p, normalization_parameter),
        sp.diff(curve_q, normalization_parameter),
    ])
    tangent_plus = curve_tangent.subs(
        normalization_parameter, node_plus
    )
    tangent_minus = curve_tangent.subs(
        normalization_parameter, node_minus
    )
    tangent_determinant = sp.factor(sp.det(
        sp.Matrix.hstack(tangent_plus, tangent_minus)
    ))
    assert tangent_determinant == (
        -72 * square_root_three / tau**3
    )

    jacobian_entries = sp.symbols("j11 j12 j21 j22")
    jacobian = sp.Matrix(2, 2, jacobian_entries)
    transported_tangent_determinant = sp.factor(sp.det(
        sp.Matrix.hstack(
            jacobian * tangent_plus,
            jacobian * tangent_minus,
        )
    ))
    assert sp.factor(
        transported_tangent_determinant
        - jacobian.det() * tangent_determinant
    ) == 0

    seed_curve_relation = 4 * x**3 + 27 * y**2
    seed_parameter = sp.symbols("seed_parameter")
    assert sp.expand(seed_curve_relation.subs({
        x: -3 * seed_parameter**2,
        y: -2 * seed_parameter**3,
    })) == 0
    assert sp.solve(
        [
            sp.diff(seed_curve_relation, x),
            sp.diff(seed_curve_relation, y),
        ],
        [x, y],
        dict=True,
    ) == [{x: 0, y: 0}]

    hamiltonian_a = q * p**4
    hamiltonian_b = q * p**2
    iterated_hamiltonian = hamiltonian_b
    witt_growth: list[dict[str, object]] = []
    for bracket_depth in range(7):
        polynomial_degree = sp.Poly(
            iterated_hamiltonian, p, q
        ).total_degree()
        field_degree = polynomial_degree - 1
        assert field_degree == 2 + 3 * bracket_depth
        witt_growth.append({
            "bracket_depth": bracket_depth,
            "hamiltonian": str(sp.factor(iterated_hamiltonian)),
            "hamiltonian_field_degree": field_degree,
            "dexp_parameter_order": bracket_depth + 1,
        })
        iterated_hamiltonian = _poisson(
            hamiltonian_a,
            iterated_hamiltonian,
            p,
            q,
        )
        assert iterated_hamiltonian != 0

    return {
        "schema": (
            "axiompack.jacobian_inverse_factor_rees_boundary.v1"
        ),
        "completed_inverse_algebra": {
            "factorization": (
                "(z/a)*R_s(W)=(1-z*W)"
                "*(W^3+A*W^2+B*W+C)"
            ),
            "factor_residual_multiplier": str(
                factor_multiplier
            ),
            "unit_partial_inverse_depth": unit_depth,
            "completed_rank": 3,
            "fitting_boundary": (
                "free rank three; no nonzero rank-one summand"
            ),
        },
        "reciprocal_root_flattening": {
            "scalar_root": str(scalar_root),
            "generator_translation": "1/z0-1/z",
            "translation_prefix": str(
                sp.collect(translation_prefix, s)
            ),
            "shells": translation_shells,
            "top_translation": "4-1/Z=-4*x*Z^2+4*y*Z^3",
            "boundary": (
                "presentation change only; Hamiltonian/liftable "
                "implementation is not asserted"
            ),
        },
        "rees_boundary": {
            "deformed_curve": (
                "(tau*r^3-3*r^2,"
                "3*tau*r^4/4-2*r^3)"
            ),
            "seed_curve": "(-3*r^2,-2*r^3)",
            "node_parameters": [
                "(1+sqrt(3))/tau",
                "(1-sqrt(3))/tau",
            ],
            "node_image": [
                "-2/tau^2",
                "1/tau^3",
            ],
            "node_tangent_determinant": str(
                tangent_determinant
            ),
            "seed_implicit_curve": "4*P^3+27*Q^2=0",
            "uniform_rees_consequence": (
                "globally Rees-admissible contacts cannot have "
                "deficit 2*n-D_n tending to infinity"
            ),
            "unrestricted_dichotomy": (
                "one finite supercritical coefficient, or infinitely "
                "many coefficients within O(1) of the critical shell"
            ),
        },
        "logarithmic_limsup_boundary": {
            "example_logarithm": (
                "B_s=s*X_(Q*P^4)+s^2*X_(Q*P^2)"
            ),
            "witt_growth": witt_growth,
            "conclusion": (
                "finite logarithmic prefix can create an infinite "
                "high-slope instantaneous-velocity tail"
            ),
            "tail_limsup_closed": False,
        },
        "claim_boundary": {
            "weighted_uniform_rees_class": "proved by exact identities",
            "weighted_unrestricted_tail_limsup": "open",
            "ordinary_symmetric_logarithmic_limsup": "open",
            "historical_priority": "unassessed",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
