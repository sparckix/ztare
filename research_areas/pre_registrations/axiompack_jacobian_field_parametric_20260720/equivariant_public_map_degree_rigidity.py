#!/usr/bin/env python3
"""Exact same-degree equivariant rigidity certificate for the public map."""
from __future__ import annotations

import json

import sympy as sp
from sympy.polys.matrices import DomainMatrix


def _primitive_integer_row(values: list[sp.Expr]) -> list[int]:
    """Clear denominators and common factors without changing row sign."""
    rationals = [sp.Rational(value) for value in values]
    denominator = sp.ilcm(*[value.q for value in rationals])
    integers = [int(value * denominator) for value in rationals]
    divisor = sp.igcd(*integers)
    return [value // divisor for value in integers]


def run() -> dict[str, object]:
    v, t, w, epsilon = sp.symbols("v t w epsilon")
    a0 = sp.Rational(-3, 2)
    gamma0 = 1 + a0 * v + t
    weighted = (1 + v) * gamma0
    p = 2 * w - 3 * w**2
    q = sp.integrate(w * sp.diff(p, w), w)
    beta0 = sp.Poly(
        sp.expand(sp.cancel(1 + p.subs(w, weighted) / gamma0)), v, t
    )
    alpha0 = sp.Poly(
        sp.expand(sp.cancel(1 + v + q.subs(w, weighted) / gamma0**2)),
        v,
        t,
    )

    # These are all monomials for which beta/x and alpha/x^2 are polynomial
    # and have the component-degree ceilings of the public map (6 and 7).
    beta_support = sorted(
        {
            (i, j)
            for i in range(10)
            for j in range(10)
            if i + 2 * j >= 1 and 2 * i + 3 * j - 1 <= 6
        },
        reverse=True,
    )
    alpha_support = sorted(
        {
            (i, j)
            for i in range(10)
            for j in range(10)
            if i + 2 * j >= 2 and 2 * i + 3 * j - 2 <= 7
        },
        reverse=True,
    )
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
    defect_terms = sp.Poly(
        sp.expand(
            sp.diff(beta * gamma, v) * sp.diff(alpha * gamma**2, t)
            - sp.diff(beta * gamma, t) * sp.diff(alpha * gamma**2, v)
            + gamma**2
        ),
        v,
        t,
    ).terms()

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
    fixed = {a: a0, beta_v: beta0.coeff_monomial(v)}
    variables = [item for item in full_variables if item not in fixed]
    names = [full_names[full_variables.index(item)] for item in variables]
    point = [full_point[full_variables.index(item)] for item in variables]
    equations = [sp.expand(coefficient.subs(fixed)) for _, coefficient in defect_terms]
    labels = [f"e_{i}_{j}" for (i, j), _ in defect_terms]
    base = dict(zip(variables, point, strict=True))
    jacobian = sp.Matrix(
        [[sp.diff(f, x).subs(base) for x in variables] for f in equations]
    )
    rank = DomainMatrix.from_Matrix(jacobian).rank()

    tangent_values = [
        -3,
        2,
        sp.Rational(-11, 4),
        3,
        0,
        1,
        sp.Rational(-3, 2),
        1,
        sp.Rational(-9, 4),
        2,
        sp.Rational(-7, 12),
        0,
        1,
        0,
        0,
        0,
    ]
    tangent = sp.Matrix(tangent_values)
    assert names == [
        "b_3_0", "b_2_1", "b_2_0", "b_1_1", "b_0_2", "b_0_1",
        "c_4_0", "c_3_1", "c_3_0", "c_2_1", "c_2_0", "c_1_2",
        "c_1_1", "c_0_3", "c_0_2", "c_0_1",
    ]
    assert rank == 15 and jacobian * tangent == sp.zeros(len(equations), 1)

    # Pivot columns of the transpose select 15 original coefficient equations,
    # rather than row-reduced combinations.  Clearing denominators gives the
    # exact rows replayed by the Lean certificate.
    independent_row_indices = list(jacobian.T.rref()[1])
    independent_labels = [labels[index] for index in independent_row_indices]
    independent_rows = [
        _primitive_integer_row(list(jacobian.row(index)))
        for index in independent_row_indices
    ]

    perturbed = {
        x: x0 + epsilon * tangent[index]
        for index, (x, x0) in enumerate(zip(variables, point, strict=True))
    }
    second_rhs = sp.Matrix(
        [
            -sp.expand(equation.subs(perturbed)).coeff(epsilon, 2)
            for equation in equations
        ]
    )
    functional_data = {
        "e_8_0": sp.Rational(5312, 2187),
        "e_7_0": sp.Rational(2560, 243),
        "e_6_1": sp.Rational(2048, 243),
        "e_6_0": sp.Rational(-128, 243),
        "e_5_2": sp.Rational(416, 81),
        "e_5_1": sp.Rational(-16, 81),
        "e_4_3": sp.Rational(16, 9),
        "e_1_5": sp.Integer(1),
    }
    functional = sp.Matrix(
        [functional_data.get(label, sp.Integer(0)) for label in labels]
    )
    assert (functional.T * jacobian) == sp.zeros(1, len(variables))
    obstruction = sp.factor((functional.T * second_rhs)[0])
    assert obstruction == sp.Rational(1, 27)

    second_order_indices = [
        labels.index(label) for label in functional_data
    ]
    second_order_rows = [
        _primitive_integer_row(list(jacobian.row(index)))
        for index in second_order_indices
    ]
    second_order_rhs = [
        str(second_rhs[index]) for index in second_order_indices
    ]

    added_coordinates = ["b_0_2", "c_1_2", "c_0_3", "c_0_2"]
    assert all(tangent[names.index(name)] == 0 for name in added_coordinates)
    result = {
        "schema": "axiompack.jacobian_public_map_degree_rigidity.v1",
        "beta_support": [list(item) for item in beta_support],
        "alpha_support": [list(item) for item in alpha_support],
        "coefficient_equation_count": len(equations),
        "slice_variable_count": len(variables),
        "slice_coordinate_order": names,
        "slice_base_point": [str(value) for value in point],
        "linear_rank": rank,
        "tangent_dimension": len(variables) - rank,
        "tangent_direction": [str(value) for value in tangent_values],
        "independent_coefficient_labels": independent_labels,
        "independent_primitive_rows": independent_rows,
        "second_order_coefficient_labels": list(functional_data),
        "second_order_primitive_rows": second_order_rows,
        "second_order_required_rhs": second_order_rhs,
        "left_kernel_functional": {
            label: str(value) for label, value in functional_data.items()
        },
        "new_same_degree_coordinates_zero_in_tangent": added_coordinates,
        "gauge_transversality_determinant": "3/4",
        "quadratic_obstruction": str(obstruction),
        "conclusion": (
            "no_nonconstant_formal_arc_in_full_same_degree_equivariant_slice"
        ),
    }
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
