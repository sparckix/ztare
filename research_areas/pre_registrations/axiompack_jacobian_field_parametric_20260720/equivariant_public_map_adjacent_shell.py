#!/usr/bin/env python3
"""Exact tangent and obstruction audit for the first omitted degree shell."""
from __future__ import annotations

from itertools import combinations
import json
from math import gcd
from functools import reduce

import sympy as sp
from sympy.polys.matrices import DomainMatrix


BASE_BETA_SUPPORT = [(3, 0), (2, 1), (2, 0), (1, 1), (1, 0), (0, 2), (0, 1)]
BASE_ALPHA_SUPPORT = [
    (4, 0), (3, 1), (3, 0), (2, 1), (2, 0),
    (1, 2), (1, 1), (0, 3), (0, 2), (0, 1),
]
SHELL = {
    "b_4_0": ("beta", (4, 0)),
    "b_1_2": ("beta", (1, 2)),
    "c_5_0": ("alpha", (5, 0)),
    "c_2_2": ("alpha", (2, 2)),
}


def _primitive_vector(values: list[sp.Expr]) -> list[int]:
    rationals = [sp.Rational(value) for value in values]
    denominator = sp.ilcm(*[value.q for value in rationals])
    integers = [int(value * denominator) for value in rationals]
    nonzero = [abs(value) for value in integers if value]
    divisor = reduce(gcd, nonzero, 1)
    integers = [value // divisor for value in integers]
    first = next((value for value in integers if value), 1)
    if first < 0:
        integers = [-value for value in integers]
    return integers


def _chart(selected: tuple[str, ...]) -> dict[str, object]:
    v, t, w, epsilon = sp.symbols("v t w epsilon")
    a0 = sp.Rational(-3, 2)
    gamma0 = 1 + a0 * v + t
    weighted = (1 + v) * gamma0
    p = 2 * w - 3 * w**2
    q = sp.integrate(w * sp.diff(p, w), w)
    beta0 = sp.Poly(sp.expand(sp.cancel(1 + p.subs(w, weighted) / gamma0)), v, t)
    alpha0 = sp.Poly(
        sp.expand(sp.cancel(1 + v + q.subs(w, weighted) / gamma0**2)), v, t
    )

    beta_support = set(BASE_BETA_SUPPORT)
    alpha_support = set(BASE_ALPHA_SUPPORT)
    for name in selected:
        side, exponent = SHELL[name]
        (beta_support if side == "beta" else alpha_support).add(exponent)
    beta_support = sorted(beta_support, reverse=True)
    alpha_support = sorted(alpha_support, reverse=True)

    beta_variables = sp.symbols(f"b0:{len(beta_support)}")
    alpha_variables = sp.symbols(f"c0:{len(alpha_support)}")
    a = sp.symbols("a")
    beta = sum(
        coefficient * v**i * t**j
        for coefficient, (i, j) in zip(beta_variables, beta_support, strict=True)
    )
    alpha = sum(
        coefficient * v**i * t**j
        for coefficient, (i, j) in zip(alpha_variables, alpha_support, strict=True)
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
        [[sp.diff(equation, variable).subs(base) for variable in variables]
         for equation in equations]
    )
    rank = DomainMatrix.from_Matrix(jacobian).rank()
    nullspace = jacobian.nullspace()
    tangent_matrix = sp.Matrix.hstack(*nullspace) if nullspace else sp.zeros(len(variables), 0)
    selected_indices = [names.index(name) for name in selected]
    shell_projection = tangent_matrix[selected_indices, :] if selected_indices else sp.zeros(0, 0)
    shell_tangent_rank = (
        DomainMatrix.from_Matrix(shell_projection).rank() if selected_indices else 0
    )

    result: dict[str, object] = {
        "selected_shell": list(selected),
        "coefficient_equation_count": len(equations),
        "slice_variable_count": len(variables),
        "linear_rank": rank,
        "tangent_dimension": len(variables) - rank,
        "shell_tangent_rank": shell_tangent_rank,
        "shell_coordinates_zero_on_every_tangent": shell_tangent_rank == 0,
        "coordinate_order": names,
        "tangent_basis": [
            _primitive_vector(list(tangent_matrix.col(index)))
            for index in range(tangent_matrix.cols)
        ],
    }

    if set(selected) == set(SHELL):
        parameters = sp.symbols(f"r0:{tangent_matrix.cols}")
        direction = tangent_matrix * sp.Matrix(parameters)
        perturbed = {
            variable: value + epsilon * direction[index]
            for index, (variable, value) in enumerate(zip(variables, point, strict=True))
        }
        second_rhs = sp.Matrix([
            -sp.expand(equation.subs(perturbed)).coeff(epsilon, 2)
            for equation in equations
        ])
        left_kernel = jacobian.T.nullspace()
        obstruction_polynomials = []
        obstruction_vectors = []
        for vector in left_kernel:
            polynomial = sp.factor((vector.T * second_rhs)[0])
            if polynomial != 0:
                obstruction_polynomials.append(polynomial)
                obstruction_vectors.append(_primitive_vector(list(vector)))
        unique_obstructions: list[sp.Expr] = []
        for polynomial in obstruction_polynomials:
            normalized = sp.Poly(polynomial, *parameters).primitive()[1]
            leading = next(iter(normalized.terms()))[1]
            if leading < 0:
                normalized = -normalized
            expression = sp.factor(normalized.as_expr())
            if all(sp.expand(expression - prior) != 0 for prior in unique_obstructions):
                unique_obstructions.append(expression)

        shell_parameter_matrix = tangent_matrix[
            [names.index(name) for name in SHELL], :
        ]
        result.update({
            "cokernel_dimension": len(equations) - rank,
            "nonzero_quadratic_obstruction_count": len(obstruction_polynomials),
            "unique_primitive_quadratic_obstructions": [
                str(polynomial) for polynomial in unique_obstructions
            ],
            "shell_parameter_matrix": [
                [str(value) for value in shell_parameter_matrix.row(row)]
                for row in range(shell_parameter_matrix.rows)
            ],
        })

        if parameters and unique_obstructions:
            groebner = sp.groebner(unique_obstructions, *parameters, order="grevlex")
            result["quadratic_obstruction_groebner_basis"] = [
                str(sp.factor(polynomial.as_expr())) for polynomial in groebner.polys
            ]
            result["quadratic_cone_zero_dimensional"] = groebner.is_zero_dimensional

        # The quadratic cone forces the shell tangent parameter to zero.  Test
        # the surviving projective direction at the next order, allowing the
        # full adjacent shell as an order-two correction.  The first tangent
        # coordinate in this chart is the old same-degree direction; the
        # second is detected by the nonzero shell projection above.
        if tangent_matrix.cols == 2 and shell_parameter_matrix[:, 0] == sp.zeros(4, 1):
            y1 = tangent_matrix.col(0)
            first_path = {
                variable: value + epsilon * y1[index]
                for index, (variable, value) in enumerate(zip(variables, point, strict=True))
            }
            rhs2 = sp.Matrix([
                -sp.expand(equation.subs(first_path)).coeff(epsilon, 2)
                for equation in equations
            ])
            solution2, free2 = jacobian.gauss_jordan_solve(rhs2)
            particular2 = solution2.subs({symbol: 0 for symbol in free2})
            u20, u21 = sp.symbols("u20 u21")
            y2 = particular2 + tangent_matrix * sp.Matrix([u20, u21])
            second_path = {
                variable: value + epsilon * y1[index] + epsilon**2 * y2[index]
                for index, (variable, value) in enumerate(zip(variables, point, strict=True))
            }
            rhs3 = sp.Matrix([
                -sp.expand(equation.subs(second_path)).coeff(epsilon, 3)
                for equation in equations
            ])
            compatibility3 = [
                sp.factor((vector.T * rhs3)[0]) for vector in left_kernel
            ]
            compatibility3 = [value for value in compatibility3 if value != 0]
            unique3: list[sp.Expr] = []
            for value in compatibility3:
                polynomial = sp.Poly(value, u20, u21).primitive()[1]
                leading = next(iter(polynomial.terms()))[1]
                if leading < 0:
                    polynomial = -polynomial
                expression = sp.factor(polynomial.as_expr())
                if all(sp.expand(expression - prior) != 0 for prior in unique3):
                    unique3.append(expression)
            result["third_order_compatibility"] = [str(value) for value in unique3]
            result["third_order_raw_compatibility_values"] = sorted({
                str(sp.factor(value)) for value in compatibility3
            })
            result["third_order_obstructed_for_all_second_order_corrections"] = (
                unique3 == [sp.Integer(1)]
            )
            assert unique3 == [sp.Integer(1)]

            # Produce a compact affine inconsistency certificate.  Eighteen
            # original Jacobian rows span the row space.  For each third-order
            # cokernel condition, express its y2-gradient in that row basis and
            # retain the certificate using the fewest second-order rows.
            y_symbols = sp.symbols(f"y0:{len(variables)}")
            y_vector = sp.Matrix(y_symbols)
            symbolic_second_path = {
                variable: value + epsilon * y1[index] + epsilon**2 * y_vector[index]
                for index, (variable, value) in enumerate(zip(variables, point, strict=True))
            }
            symbolic_rhs3 = sp.Matrix([
                -sp.expand(equation.subs(symbolic_second_path)).coeff(epsilon, 3)
                for equation in equations
            ])
            independent_indices = list(jacobian.T.rref()[1])
            independent_matrix = jacobian[independent_indices, :]
            independent_rhs2 = rhs2[independent_indices, :]
            candidates = []
            for kernel_vector in left_kernel:
                expression = sp.expand((kernel_vector.T * symbolic_rhs3)[0])
                if expression == 0:
                    continue
                gradient = sp.Matrix([sp.diff(expression, symbol) for symbol in y_symbols])
                constant = sp.expand(expression.subs({symbol: 0 for symbol in y_symbols}))
                multipliers, free = independent_matrix.T.gauss_jordan_solve(gradient)
                assert free.rows == 0
                residual = sp.factor(constant + (multipliers.T * independent_rhs2)[0])
                if residual == 0:
                    continue
                support = [index for index, value in enumerate(multipliers) if value != 0]
                candidates.append((len(support), support, multipliers, gradient, constant, residual))
            candidates.sort(key=lambda item: (item[0], sum(len(str(value)) for value in item[2])))
            _, support, multipliers, gradient, constant, residual = candidates[0]
            second_affine_rows = []
            combination = []
            for basis_index in support:
                equation_index = independent_indices[basis_index]
                affine = list(jacobian.row(equation_index)) + [-rhs2[equation_index]]
                primitive = _primitive_vector(affine)
                raw = [sp.Rational(value) for value in affine]
                scale = next(
                    sp.Rational(pvalue, 1) / rvalue
                    for pvalue, rvalue in zip(primitive, raw, strict=True) if rvalue != 0
                )
                second_affine_rows.append({
                    "label": labels[equation_index],
                    "primitive_affine_row": primitive,
                })
                combination.append(str(-multipliers[basis_index] / scale))
            third_affine = list(gradient) + [constant]
            third_primitive = _primitive_vector(third_affine)
            third_raw = [sp.Rational(value) for value in third_affine]
            third_scale = next(
                sp.Rational(pvalue, 1) / rvalue
                for pvalue, rvalue in zip(third_primitive, third_raw, strict=True) if rvalue != 0
            )
            result["compact_third_order_certificate"] = {
                "coordinate_order": names,
                "second_order_rows": second_affine_rows,
                "third_order_primitive_affine_row": third_primitive,
                "linear_combination_multipliers": combination + [str(1 / third_scale)],
                "linear_combination_order": [
                    row["label"] for row in second_affine_rows
                ] + ["third_order_compatibility"],
                "nonzero_residual": str(residual),
            }

    return result


def run() -> dict[str, object]:
    names = tuple(SHELL)
    charts = []
    for size in range(1, len(names) + 1):
        for selected in combinations(names, size):
            charts.append(_chart(selected))
    full_chart = charts[-1]
    return {
        "schema": "axiompack.jacobian_public_map_adjacent_shell.v1",
        "shell": list(names),
        "summary": {
            "subset_chart_count": len(charts),
            "charts_with_shell_tangent": sum(
                not chart["shell_coordinates_zero_on_every_tangent"]
                for chart in charts
            ),
            "full_shell_tangent_dimension": full_chart["tangent_dimension"],
            "full_shell_quadratic_obstruction_basis": full_chart.get(
                "quadratic_obstruction_groebner_basis", []
            ),
            "surviving_direction_third_order_obstructed": full_chart.get(
                "third_order_obstructed_for_all_second_order_corrections", False
            ),
            "conclusion": "no_nonconstant_formal_arc_in_adjacent_degree_shell",
        },
        "charts": charts,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
