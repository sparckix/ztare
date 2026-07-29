#!/usr/bin/env python3
"""Exact support-filtration audit for the normalized cubic Keller family."""
from __future__ import annotations

from functools import reduce
from math import gcd
import json

import sympy as sp
from sympy.polys.matrices import DomainMatrix


BASE_BETA_SUPPORT = {
    (3, 0), (2, 1), (2, 0), (1, 1), (1, 0), (0, 2), (0, 1),
}
BASE_ALPHA_SUPPORT = {
    (4, 0), (3, 1), (3, 0), (2, 1), (2, 0),
    (1, 2), (1, 1), (0, 3), (0, 2), (0, 1),
}
SHELLS = {
    1: {
        "beta": {(4, 0), (1, 2)},
        "alpha": {(5, 0), (2, 2)},
    },
    2: {
        "beta": {(3, 1), (0, 3)},
        "alpha": {(4, 1), (1, 3)},
    },
    3: {
        "beta": {(5, 0), (2, 2)},
        "alpha": {(6, 0), (3, 2), (0, 4)},
    },
    4: {
        "beta": {(4, 1), (1, 3)},
        "alpha": {(5, 1), (2, 3)},
    },
    5: {
        "beta": {(6, 0), (3, 2), (0, 4)},
        "alpha": {(7, 0), (4, 2), (1, 4)},
    },
}
EXPECTED_NEW_DERIVATIVE = {
    "b_4_0": sp.Rational(15, 4),
    "b_1_2": sp.Integer(3),
    "c_5_0": sp.Rational(9, 2),
    "c_2_2": sp.Rational(9, 2),
    "b_3_1": sp.Integer(-7),
    "c_4_1": sp.Rational(-15, 2),
    "b_5_0": sp.Rational(9, 4),
    "b_2_2": sp.Integer(3),
    "c_6_0": sp.Rational(27, 16),
    "c_3_2": sp.Integer(3),
    "b_4_1": sp.Integer(-3),
    "c_5_1": sp.Rational(-9, 4),
    "b_3_2": sp.Integer(1),
    "c_4_2": sp.Rational(3, 4),
}


def _primitive_vector(values: list[sp.Expr]) -> list[int]:
    rationals = [sp.Rational(value) for value in values]
    denominator = sp.ilcm(*[value.q for value in rationals])
    integers = [int(value * denominator) for value in rationals]
    nonzero = [abs(value) for value in integers if value]
    divisor = reduce(gcd, nonzero, 1)
    result = [value // divisor for value in integers]
    first = next((value for value in result if value), 1)
    return [-value for value in result] if first < 0 else result


def _normalized_family() -> dict[str, object]:
    s, v, t, w, target_p, target_q = sp.symbols("s v t w P Q")
    p = (2 + s / 2) * w + (-3 - 3 * s / 2) * w**2 + s * w**3
    q = (1 + s / 4) * w**2 - (2 + s) * w**3 + 3 * s * w**4 / 4
    a = -(s - 6) / (s - 4)
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    source_v = mu * v
    gamma = sp.cancel(1 + a * source_v + t)
    assert sp.cancel(gamma - (1 - 3 * v / 2 + t)) == 0
    weighted = (1 + source_v) * gamma
    beta = sp.cancel(lam / mu * (1 + p.subs(w, weighted) / gamma))
    alpha = sp.cancel((1 + source_v + q.subs(w, weighted) / gamma**2) / lam)
    if any(symbol in sp.denom(expr).free_symbols for expr in (beta, alpha)
           for symbol in (v, t)):
        raise AssertionError("normalization did not produce polynomial components")
    beta_poly = sp.Poly(sp.expand(beta), v, t)
    alpha_poly = sp.Poly(sp.expand(alpha), v, t)
    beta_derivative = sp.Poly(
        sp.expand(sp.diff(beta, s).subs(s, 0)), v, t
    )
    alpha_derivative = sp.Poly(
        sp.expand(sp.diff(alpha, s).subs(s, 0)), v, t
    )
    fixed_gamma = 1 - 3 * v / 2 + t
    defect = sp.cancel(
        sp.diff(beta * fixed_gamma, v) * sp.diff(alpha * fixed_gamma**2, t)
        - sp.diff(beta * fixed_gamma, t) * sp.diff(alpha * fixed_gamma**2, v)
        + fixed_gamma**2
    )
    inverse_polynomial = sp.expand(w * p - q - w * target_p + target_q)
    source_v0, source_t0 = sp.symbols("source_v source_t")
    source_gamma = 1 + a * source_v0 + source_t0
    source_w = (1 + source_v0) * source_gamma
    source_p = source_gamma + p.subs(w, source_w)
    source_q = source_w * source_gamma + q.subs(w, source_w)
    assert sp.cancel(inverse_polynomial.subs({
        w: source_w, target_p: source_p, target_q: source_q
    })) == 0
    recovered_gamma = target_p - p
    recovered_v = sp.cancel(w / recovered_gamma - 1)
    recovered_t = sp.cancel(recovered_gamma - 1 - a * recovered_v)
    assert sp.cancel(recovered_v.subs({
        w: source_w, target_p: source_p
    }) - source_v0) == 0
    assert sp.cancel(recovered_t.subs({
        w: source_w, target_p: source_p
    }) - source_t0) == 0
    inverse_generic = sp.Poly(inverse_polynomial, w)
    inverse_seed = sp.Poly(inverse_polynomial.subs(s, 0), w)
    return {
        "symbols": (s, v, t),
        "beta": beta_poly,
        "alpha": alpha_poly,
        "beta_derivative": beta_derivative,
        "alpha_derivative": alpha_derivative,
        "defect_zero": sp.factor(defect) == 0,
        "inverse_fiber_certificate": {
            "polynomial": str(inverse_polynomial),
            "generic_w_degree": inverse_generic.degree(),
            "seed_w_degree": inverse_seed.degree(),
            "generic_w_leading_coefficient": str(inverse_generic.LC()),
            "seed_w_leading_coefficient": str(inverse_seed.LC()),
            "degree_in_independent_Q": sp.Poly(
                inverse_polynomial, target_q
            ).degree(),
            "coefficient_of_independent_Q": str(
                sp.Poly(inverse_polynomial, target_q).coeff_monomial(target_q)
            ),
            "source_recovery_verified": True,
            "normalization_exceptional_parameters": ["4", "6"],
            "irreducibility_mechanism": (
                "Gauss plus degree-one-in-independent-Q unit-factor argument"
            ),
        },
    }


def _supports(level: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    beta = set(BASE_BETA_SUPPORT)
    alpha = set(BASE_ALPHA_SUPPORT)
    for shell in range(1, level + 1):
        beta.update(SHELLS[shell]["beta"])
        alpha.update(SHELLS[shell]["alpha"])
    return sorted(beta, reverse=True), sorted(alpha, reverse=True)


def _polynomial(expr: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> sp.Poly | None:
    value = sp.cancel(expr)
    if {v, t} & sp.denom(value).free_symbols:
        return None
    return sp.Poly(sp.expand(value), v, t)


def _gauge_variations(
    *,
    beta0: sp.Poly,
    alpha0: sp.Poly,
    gamma0: sp.Expr,
    beta_support: list[tuple[int, int]],
    alpha_support: list[tuple[int, int]],
    variables: list[sp.Symbol],
    beta_variables: tuple[sp.Symbol, ...],
    alpha_variables: tuple[sp.Symbol, ...],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[list[str], sp.Matrix, sp.Matrix, list[dict[str, object]]]:
    """Return monomial-local generators plus expanded constrained filtrations."""

    raw: list[tuple[str, int, sp.Poly, sp.Poly]] = []
    direction = lambda expr: sp.diff(expr, v) + sp.Rational(3, 2) * sp.diff(expr, t)
    gamma_poly = sp.Poly(gamma0, v, t)
    beta_direction = sp.Poly(direction(beta0.as_expr()), v, t)
    alpha_direction = sp.Poly(direction(alpha0.as_expr()), v, t)
    for power in range(9):
        factor = gamma_poly**power
        delta_beta = factor * beta_direction
        delta_alpha = factor * alpha_direction
        raw.append((f"source_gamma_{power}", 0, delta_beta, delta_alpha))
    for i in range(7):
        for j in range(4):
            weight = i + 2 * j
            if i + j == 0 or not 3 <= weight <= 6:
                continue
            gamma_power = weight - 3
            factor = gamma_poly**gamma_power
            delta_beta = (
                j * factor * beta0**i * alpha0**(j - 1)
                if j else sp.Poly(0, v, t)
            )
            delta_alpha = (
                -i * factor * beta0**(i - 1) * alpha0**j
                if i else sp.Poly(0, v, t)
            )
            raw.append((f"target_H_P{i}_Q{j}", weight, delta_beta, delta_alpha))

    labels: list[str] = []
    columns: list[sp.Matrix] = []
    frozen_values: list[sp.Expr] = []
    seen: set[tuple[sp.Expr, ...]] = set()
    beta_set, alpha_set = set(beta_support), set(alpha_support)
    beta_lookup = dict(zip(beta_variables, beta_support, strict=True))
    alpha_lookup = dict(zip(alpha_variables, alpha_support, strict=True))
    for label, _weight, delta_beta, delta_alpha in raw:
        if not set(delta_beta.monoms()) <= beta_set:
            continue
        if not set(delta_alpha.monoms()) <= alpha_set:
            continue
        coefficient_by_variable = {
            **{
                variable: delta_beta.coeff_monomial(v**i * t**j)
                for variable, (i, j) in beta_lookup.items()
            },
            **{
                variable: delta_alpha.coeff_monomial(v**i * t**j)
                for variable, (i, j) in alpha_lookup.items()
            },
        }
        column = sp.Matrix([
            coefficient_by_variable.get(variable, sp.Integer(0))
            for variable in variables
        ])
        frozen = delta_beta.coeff_monomial(v)
        identity = tuple(column) + (frozen,)
        if not any(identity) or identity in seen:
            continue
        seen.add(identity)
        labels.append(label)
        columns.append(column)
        frozen_values.append(frozen)
    matrix = (
        sp.Matrix.hstack(*columns) if columns else sp.zeros(len(variables), 0)
    )
    beta_lookup = {exponent: variable for variable, exponent in beta_lookup.items()}
    alpha_lookup = {exponent: variable for variable, exponent in alpha_lookup.items()}
    expanded: list[dict[str, object]] = []
    for bound in range(3, 7):
        selected = [row for row in raw if row[1] == 0 or row[1] <= bound]
        coordinate_union = sorted({
            (side, exponent)
            for _label, _weight, delta_beta, delta_alpha in selected
            for side, polynomial in (("beta", delta_beta), ("alpha", delta_alpha))
            for exponent in polynomial.monoms()
        })
        selected_labels = [row[0] for row in selected]
        coefficient_columns = []
        for _label, _weight, delta_beta, delta_alpha in selected:
            coefficient_columns.append(sp.Matrix([
                (
                    delta_beta.coeff_monomial(v**i * t**j)
                    if side == "beta"
                    else delta_alpha.coeff_monomial(v**i * t**j)
                )
                for side, (i, j) in coordinate_union
            ]))
        coefficient_matrix = (
            sp.Matrix.hstack(*coefficient_columns)
            if coefficient_columns else sp.zeros(len(coordinate_union), 0)
        )
        allowed_coordinates = {
            *(('beta', exponent) for exponent in beta_support if exponent != (1, 0)),
            *(('alpha', exponent) for exponent in alpha_support),
        }
        forbidden_indices = [
            index for index, coordinate in enumerate(coordinate_union)
            if coordinate not in allowed_coordinates
        ]
        constraint_matrix = coefficient_matrix[forbidden_indices, :]
        constraint_kernel = constraint_matrix.nullspace()
        constraint_basis = (
            sp.Matrix.hstack(*constraint_kernel)
            if constraint_kernel else sp.zeros(coefficient_matrix.cols, 0)
        )
        allowed_rows: list[sp.Matrix] = []
        for variable in variables:
            if variable in beta_lookup.values():
                exponent = next(
                    key for key, value in beta_lookup.items() if value == variable
                )
                coordinate = ("beta", exponent)
            else:
                exponent = next(
                    key for key, value in alpha_lookup.items() if value == variable
                )
                coordinate = ("alpha", exponent)
            if coordinate in coordinate_union:
                index = coordinate_union.index(coordinate)
                allowed_rows.append(coefficient_matrix.row(index))
            else:
                allowed_rows.append(sp.zeros(1, coefficient_matrix.cols))
        allowed_matrix = (
            sp.Matrix.vstack(*allowed_rows)
            if allowed_rows else sp.zeros(0, coefficient_matrix.cols)
        )
        constrained_image = allowed_matrix * constraint_basis
        expanded.append({
            "hamiltonian_weight_bound": bound,
            "raw_generator_count": len(selected_labels),
            "raw_generator_labels": selected_labels,
            "forbidden_coordinate_count": len(forbidden_indices),
            "constraint_rank": DomainMatrix.from_Matrix(constraint_matrix).rank(),
            "constraint_kernel_dimension": constraint_basis.cols,
            "normalized_coordinate_gauge_rank": (
                DomainMatrix.from_Matrix(constrained_image).rank()
            ),
            "_matrix": constrained_image,
            "_constraint_basis": constraint_basis,
            "_selected_labels": selected_labels,
        })
    return labels, matrix, sp.Matrix([frozen_values]), expanded


def _chart(level: int, family: dict[str, object]) -> dict[str, object]:
    _s, v, t = family["symbols"]
    a0 = sp.Rational(-3, 2)
    gamma0 = 1 + a0 * v + t
    beta0 = sp.Poly(family["beta"].as_expr().subs(_s, 0), v, t)
    alpha0 = sp.Poly(family["alpha"].as_expr().subs(_s, 0), v, t)
    beta_derivative = family["beta_derivative"]
    alpha_derivative = family["alpha_derivative"]
    beta_support, alpha_support = _supports(level)
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
    terms = sp.Poly(
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
    full_derivative = (
        [sp.Integer(0)]
        + [beta_derivative.coeff_monomial(v**i * t**j) for i, j in beta_support]
        + [alpha_derivative.coeff_monomial(v**i * t**j) for i, j in alpha_support]
    )
    beta_v = beta_variables[beta_support.index((1, 0))]
    fixed = {a: a0, beta_v: beta0.coeff_monomial(v)}
    variables = [value for value in full_variables if value not in fixed]
    names = [full_names[full_variables.index(value)] for value in variables]
    point = [full_point[full_variables.index(value)] for value in variables]
    derivative = sp.Matrix([
        full_derivative[full_variables.index(value)] for value in variables
    ])
    equations = [sp.expand(coefficient.subs(fixed)) for _, coefficient in terms]
    labels = [f"e_{i}_{j}" for (i, j), _ in terms]
    base = dict(zip(variables, point, strict=True))
    jacobian = sp.Matrix([
        [sp.diff(equation, variable).subs(base) for variable in variables]
        for equation in equations
    ])
    rank = DomainMatrix.from_Matrix(jacobian).rank()
    tangent_vectors = jacobian.nullspace()
    tangent_matrix = (
        sp.Matrix.hstack(*tangent_vectors)
        if tangent_vectors else sp.zeros(len(variables), 0)
    )
    residual = jacobian * derivative
    nonzero_residual = [
        {"equation": labels[index], "value": str(sp.factor(value))}
        for index, value in enumerate(residual) if value != 0
    ]
    (
        gauge_labels,
        gauge_candidates,
        frozen_gauge_row,
        expanded_gauge_filtration,
    ) = _gauge_variations(
        beta0=beta0,
        alpha0=alpha0,
        gamma0=gamma0,
        beta_support=beta_support,
        alpha_support=alpha_support,
        variables=variables,
        beta_variables=beta_variables,
        alpha_variables=alpha_variables,
        v=v,
        t=t,
    )
    gauge_constraint_kernel = frozen_gauge_row.nullspace()
    gauge_constraint_matrix = (
        sp.Matrix.hstack(*gauge_constraint_kernel)
        if gauge_constraint_kernel else sp.zeros(gauge_candidates.cols, 0)
    )
    gauge_matrix = gauge_candidates * gauge_constraint_matrix
    gauge_rank = DomainMatrix.from_Matrix(gauge_matrix).rank()
    assert jacobian * gauge_matrix == sp.zeros(jacobian.rows, gauge_matrix.cols)
    family_in_gauge_span = None
    if not nonzero_residual:
        family_in_gauge_span = (
            DomainMatrix.from_Matrix(gauge_matrix.row_join(derivative)).rank()
            == gauge_rank
        )
    expanded_gauge_rows: list[dict[str, object]] = []
    for filtration_row in expanded_gauge_filtration:
        expanded_matrix = filtration_row["_matrix"]
        assert isinstance(expanded_matrix, sp.MatrixBase)
        assert jacobian * expanded_matrix == sp.zeros(
            jacobian.rows, expanded_matrix.cols
        )
        expanded_rank = int(filtration_row["normalized_coordinate_gauge_rank"])
        expanded_family_member = None
        family_gauge_decomposition: dict[str, str] = {}
        if not nonzero_residual:
            expanded_family_member = (
                DomainMatrix.from_Matrix(
                    expanded_matrix.row_join(derivative)
                ).rank() == expanded_rank
            )
            if expanded_family_member:
                image_coordinates, free = expanded_matrix.gauss_jordan_solve(
                    derivative
                )
                image_coordinates = image_coordinates.subs({
                    symbol: 0 for symbol in free
                })
                raw_coordinates = (
                    filtration_row["_constraint_basis"] * image_coordinates
                )
                family_gauge_decomposition = {
                    label: str(sp.factor(value))
                    for label, value in zip(
                        filtration_row["_selected_labels"],
                        raw_coordinates,
                        strict=True,
                    )
                    if value != 0
                }
        expanded_gauge_rows.append({
            key: value for key, value in filtration_row.items()
            if not key.startswith("_")
        } | {
            "tangent_quotient_dimension": tangent_matrix.cols - expanded_rank,
            "known_family_tangent_in_coordinate_gauge_span": (
                expanded_family_member
            ),
            "known_family_gauge_decomposition": family_gauge_decomposition,
        })
    parameters = sp.symbols(f"r0:{tangent_matrix.cols}")
    direction = tangent_matrix * sp.Matrix(parameters)
    epsilon = sp.symbols("epsilon")
    perturbed = {
        variable: value + epsilon * direction[index]
        for index, (variable, value) in enumerate(
            zip(variables, point, strict=True)
        )
    }
    second_rhs = sp.Matrix([
        -sp.expand(equation.subs(perturbed)).coeff(epsilon, 2)
        for equation in equations
    ])
    obstruction_polynomials: list[sp.Expr] = []
    for vector in jacobian.T.nullspace():
        expression = sp.factor((vector.T * second_rhs)[0])
        if expression == 0:
            continue
        polynomial = sp.Poly(expression, *parameters).primitive()[1]
        leading = next(iter(polynomial.terms()))[1]
        if leading < 0:
            polynomial = -polynomial
        normalized = sp.factor(polynomial.as_expr())
        if all(
            sp.expand(normalized - prior) != 0
            for prior in obstruction_polynomials
        ):
            obstruction_polynomials.append(normalized)
    if obstruction_polynomials:
        groebner = sp.groebner(
            obstruction_polynomials, *parameters, order="grevlex"
        )
        obstruction_basis = [
            sp.factor(polynomial.as_expr()) for polynomial in groebner.polys
        ]
        cone_zero_dimensional = bool(groebner.is_zero_dimensional)
    else:
        obstruction_basis = []
        cone_zero_dimensional = False
    family_coordinates: list[sp.Expr] = []
    if not nonzero_residual:
        solution, free = tangent_matrix.gauss_jordan_solve(derivative)
        assert free.rows == 0
        family_coordinates = list(solution)
        assert all(
            sp.expand(polynomial.subs(dict(zip(
                parameters, family_coordinates, strict=True
            )))) == 0
            for polynomial in obstruction_polynomials
        )
    return {
        "cumulative_shell": level,
        "coefficient_equation_count": len(equations),
        "variable_count": len(variables),
        "linear_rank": rank,
        "tangent_dimension": len(variables) - rank,
        "known_family_projection_is_tangent": not nonzero_residual,
        "known_family_projection_nonzero_residual_count": len(nonzero_residual),
        "known_family_projection_first_residuals": nonzero_residual[:5],
        "known_family_tangent_coordinates": [
            str(value) for value in family_coordinates
        ],
        "coordinate_gauge_generator_count": len(gauge_labels),
        "coordinate_gauge_generator_labels": gauge_labels,
        "normalized_coordinate_gauge_rank": gauge_rank,
        "tangent_quotient_dimension": tangent_matrix.cols - gauge_rank,
        "known_family_tangent_in_coordinate_gauge_span": family_in_gauge_span,
        "expanded_coordinate_gauge_filtration": expanded_gauge_rows,
        "quadratic_obstruction_groebner_basis": [
            str(value) for value in obstruction_basis
        ],
        "quadratic_cone_zero_dimensional": cone_zero_dimensional,
        "known_family_projected_derivative": {
            name: str(value)
            for name, value in zip(names, derivative, strict=True) if value != 0
        },
        "tangent_basis": [
            _primitive_vector(list(vector)) for vector in tangent_vectors
        ],
    }


def main() -> None:
    family = _normalized_family()
    _s, v, t = family["symbols"]
    beta_support = set(family["beta"].monoms())
    alpha_support = set(family["alpha"].monoms())
    shell5_beta, shell5_alpha = map(set, _supports(5))
    derivative_entries = {
        **{
            f"b_{i}_{j}": family["beta_derivative"].coeff_monomial(v**i * t**j)
            for i, j in shell5_beta - BASE_BETA_SUPPORT
        },
        **{
            f"c_{i}_{j}": family["alpha_derivative"].coeff_monomial(v**i * t**j)
            for i, j in shell5_alpha - BASE_ALPHA_SUPPORT
        },
    }
    nonzero_new = {key: value for key, value in derivative_entries.items() if value != 0}
    assert nonzero_new == EXPECTED_NEW_DERIVATIVE
    assert beta_support <= shell5_beta and alpha_support <= shell5_alpha
    charts = [_chart(level, family) for level in range(6)]
    assert charts[-1]["known_family_projection_is_tangent"] is True
    assert all(
        chart["known_family_projection_is_tangent"] is False
        for chart in charts[:-1]
    )
    print(json.dumps({
        "schema": "axiompack.jacobian_public_map_cumulative_shells.v1",
        "normalized_family_exact_keller_identity": family["defect_zero"],
        "inverse_fiber_certificate": family["inverse_fiber_certificate"],
        "family_support_contained_first_at_shell": 5,
        "predicted_new_derivative_entries_verified": True,
        "charts": charts,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
