#!/usr/bin/env python3
"""Exact deformation test around the cubic weighted-lift Keller map.

The calculation is deliberately coefficient-level.  It makes no numerical
rank or approximate-series decisions: SymPy's QQ domain supplies the linear
algebra, and every obstruction is replayed as a polynomial identity.
"""
from __future__ import annotations

import json

import sympy as sp
from sympy.polys.matrices import DomainMatrix


def _chart():
    v, t, w, theta = sp.symbols("v t w theta")
    theta0 = sp.Rational(-2)
    p = (2 + theta / 2) * w + (-3 - 3 * theta / 2) * w**2 + theta * w**3
    q = sp.integrate(w * sp.diff(p, w), w)
    kappa = sp.diff(p, w).subs(w, 1)
    a_theta = sp.factor(-(1 + kappa) / (2 + kappa))
    gamma_theta = 1 + a_theta * v + t
    weighted_theta = (1 + v) * gamma_theta
    beta_family = sp.Poly(
        sp.expand(sp.cancel(1 + p.subs(w, weighted_theta) / gamma_theta)),
        v,
        t,
    )
    alpha_family = sp.Poly(
        sp.expand(
            sp.cancel(1 + v + q.subs(w, weighted_theta) / gamma_theta**2)
        ),
        v,
        t,
    )
    a0 = a_theta.subs(theta, theta0)
    beta0 = sp.Poly(beta_family.as_expr().subs(theta, theta0), v, t)
    alpha0 = sp.Poly(alpha_family.as_expr().subs(theta, theta0), v, t)

    beta_support = beta0.monoms()
    alpha_support = alpha0.monoms()
    beta_variables = sp.symbols(f"b0:{len(beta_support)}")
    alpha_variables = sp.symbols(f"c0:{len(alpha_support)}")
    a = sp.symbols("a")
    beta = sum(
        coefficient * v**i * t**j
        for coefficient, (i, j) in zip(
            beta_variables, beta_support, strict=True
        )
    )
    alpha = sum(
        coefficient * v**i * t**j
        for coefficient, (i, j) in zip(
            alpha_variables, alpha_support, strict=True
        )
    )
    gamma = 1 + a * v + t
    defect = sp.Poly(
        sp.expand(
            sp.diff(beta * gamma, v) * sp.diff(alpha * gamma**2, t)
            - sp.diff(beta * gamma, t) * sp.diff(alpha * gamma**2, v)
            + gamma**2
        ),
        v,
        t,
    )

    full_variables = (a,) + beta_variables + alpha_variables
    full_names = (
        ["a"]
        + [f"b_{i}_{j}" for i, j in beta_support]
        + [f"c_{i}_{j}" for i, j in alpha_support]
    )
    full_point = (
        [a0]
        + [beta0.coeff_monomial(v**i * t**j) for i, j in beta_support]
        + [alpha0.coeff_monomial(v**i * t**j) for i, j in alpha_support]
    )
    beta_v = beta_variables[beta_support.index((1, 0))]
    beta_t = beta_variables[beta_support.index((0, 1))]
    fixed = {
        a: a0,
        beta_v: beta0.coeff_monomial(v),
        beta_t: beta0.coeff_monomial(t),
    }
    variables = [item for item in full_variables if item not in fixed]
    names = [full_names[full_variables.index(item)] for item in variables]
    point = [full_point[full_variables.index(item)] for item in variables]
    equations = [sp.expand(coefficient.subs(fixed)) for _, coefficient in defect.terms()]
    return {
        "v": v,
        "t": t,
        "theta": theta,
        "theta0": theta0,
        "a_theta": a_theta,
        "a0": a0,
        "beta_family": beta_family,
        "alpha_family": alpha_family,
        "beta0": beta0,
        "alpha0": alpha0,
        "beta_support": beta_support,
        "alpha_support": alpha_support,
        "full_variables": full_variables,
        "full_names": full_names,
        "full_point": full_point,
        "variables": variables,
        "names": names,
        "point": point,
        "equations": equations,
    }


def _gauge_transversality(chart) -> sp.Rational:
    beta_support = chart["beta_support"]
    alpha_support = chart["alpha_support"]
    beta_values = chart["full_point"][1 : 1 + len(beta_support)]
    alpha_values = chart["full_point"][1 + len(beta_support) :]
    theta = chart["theta"]
    theta0 = chart["theta0"]
    a_theta = chart["a_theta"]
    a0 = chart["a0"]
    beta_family, alpha_family = (
        chart["beta_family"],
        chart["alpha_family"],
    )
    v, t = chart["v"], chart["t"]

    target_scale = [sp.Integer(0)] + beta_values + [-x for x in alpha_values]
    source_scale = (
        [a0]
        + [(i - 1) * x for x, (i, _j) in zip(beta_values, beta_support)]
        + [i * x for x, (i, _j) in zip(alpha_values, alpha_support)]
    )
    seed_tangent = (
        [sp.diff(a_theta, theta).subs(theta, theta0)]
        + [
            sp.diff(beta_family.coeff_monomial(v**i * t**j), theta).subs(
                theta, theta0
            )
            for i, j in beta_support
        ]
        + [
            sp.diff(alpha_family.coeff_monomial(v**i * t**j), theta).subs(
                theta, theta0
            )
            for i, j in alpha_support
        ]
    )
    rows = [
        chart["full_names"].index("a"),
        chart["full_names"].index("b_1_0"),
        chart["full_names"].index("b_0_1"),
    ]
    return sp.factor(
        sp.Matrix(
            [
                [target_scale[index], source_scale[index], seed_tangent[index]]
                for index in rows
            ]
        ).det()
    )


def _linear_data(chart):
    variables, point, equations = (
        chart["variables"],
        chart["point"],
        chart["equations"],
    )
    base = dict(zip(variables, point, strict=True))
    jacobian = sp.Matrix(
        [[sp.diff(f, x).subs(base) for x in variables] for f in equations]
    )
    domain = DomainMatrix.from_Matrix(jacobian)
    tangent = domain.nullspace().to_Matrix()
    pivot_columns = domain.rref()[1]
    independent_rows = DomainMatrix.from_Matrix(jacobian.T).rref()[1]
    free_columns = [
        index for index in range(len(variables)) if index not in pivot_columns
    ]
    inverse = jacobian.extract(independent_rows, pivot_columns).inv()
    return {
        "jacobian": jacobian,
        "rank": domain.rank(),
        "tangent": tangent,
        "pivot_columns": pivot_columns,
        "independent_rows": independent_rows,
        "free_columns": free_columns,
        "inverse": inverse,
    }


def _coefficient_rhs(chart, known, order: int) -> sp.Matrix:
    epsilon = sp.symbols("epsilon")
    substitution = {
        x: x0
        + sum(epsilon**k * vector[index] for k, vector in enumerate(known, 1))
        for index, (x, x0) in enumerate(
            zip(chart["variables"], chart["point"], strict=True)
        )
    }
    return sp.Matrix(
        [
            -sp.expand(equation.subs(substitution)).coeff(epsilon, order)
            for equation in chart["equations"]
        ]
    )


def _solve_linear(chart, linear, rhs, prefix: str):
    jacobian = linear["jacobian"]
    independent = linear["independent_rows"]
    pivots = linear["pivot_columns"]
    free = linear["free_columns"]
    parameters = sp.symbols(f"{prefix}_0 {prefix}_1")
    vector = [None] * len(chart["variables"])
    for column, value in zip(free, parameters, strict=True):
        vector[column] = value
    selected_rhs = sp.Matrix([rhs[index] for index in independent])
    selected_free = jacobian.extract(independent, free) * sp.Matrix(parameters)
    solved = linear["inverse"] * (selected_rhs - selected_free)
    for column, value in zip(pivots, solved, strict=True):
        vector[column] = sp.factor(value)
    residual = jacobian * sp.Matrix(vector) - rhs
    compatibility = []
    for value in residual:
        value = sp.factor(value)
        if value and value not in compatibility and -value not in compatibility:
            compatibility.append(value)
    return sp.Matrix(vector), parameters, compatibility


def run() -> dict[str, object]:
    chart = _chart()
    linear = _linear_data(chart)
    tangent = linear["tangent"]
    assert tangent.shape == (2, 28)

    S, R = sp.symbols("S R")
    general_tangent = S * tangent.row(0).T + R * tangent.row(1).T
    quadratic_rhs = _coefficient_rhs(chart, [general_tangent], 2)
    left_kernel = DomainMatrix.from_Matrix(
        linear["jacobian"].T
    ).nullspace().to_Matrix()
    quadratic_obstructions = [
        sp.factor((left_kernel.row(i) * quadratic_rhs)[0])
        for i in range(left_kernel.rows)
    ]
    quadratic_obstructions = [item for item in quadratic_obstructions if item]
    common = quadratic_obstructions[0]
    for item in quadratic_obstructions[1:]:
        common = sp.gcd(common, item)
    common = sp.factor(common)
    expected_cone = (2 * R + S) * (5 * R + 3 * S)
    cone_scale = sp.factor(common / expected_cone)
    assert cone_scale.is_Rational and cone_scale != 0

    lines = {
        "S=-2R": -2 * tangent.row(0).T + tangent.row(1).T,
        "S=-5R/3": -sp.Rational(5, 3) * tangent.row(0).T
        + tangent.row(1).T,
    }
    cubic: dict[str, object] = {}
    for index, (label, direction) in enumerate(lines.items()):
        second, free, compatibility = _solve_linear(
            chart,
            linear,
            _coefficient_rhs(chart, [direction], 2),
            f"u{index}",
        )
        assert not compatibility
        _, _, third = _solve_linear(
            chart,
            linear,
            _coefficient_rhs(chart, [direction, second], 3),
            f"z{index}",
        )
        if label == "S=-2R":
            constant = next(item for item in third if not item.free_symbols)
            assert constant == sp.Rational(16, 81)
            cubic[label] = {"constant_obstruction": str(constant)}
        else:
            u0, u1 = free
            first = 12 * u0 + 20 * u1 - 7
            second_condition = 33 * u0 + 55 * u1 - 19
            assert any(sp.factor(item / first).is_Rational for item in third)
            assert any(
                sp.factor(item / second_condition).is_Rational for item in third
            )
            contradiction = sp.factor(
                sp.Rational(11, 4) * first - second_condition
            )
            assert contradiction == sp.Rational(-1, 4)
            cubic[label] = {
                "conditions": [str(first), str(second_condition)],
                "constant_contradiction": str(contradiction),
            }

    result = {
        "schema": "axiompack.jacobian_equivariant_local_rigidity.v1",
        "coefficient_equation_count": len(chart["equations"]),
        "slice_variable_count": len(chart["variables"]),
        "linear_rank": linear["rank"],
        "tangent_dimension": tangent.rows,
        "gauge_seed_transversality_determinant": str(
            _gauge_transversality(chart)
        ),
        "quadratic_obstruction_cone": str(expected_cone),
        "cubic_obstructions": cubic,
        "conclusion": (
            "no_nonconstant_formal_arc_in_normalized_fixed_support_slice"
        ),
    }
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
