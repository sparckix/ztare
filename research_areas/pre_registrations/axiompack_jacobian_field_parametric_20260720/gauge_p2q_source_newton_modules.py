#!/usr/bin/env python3
"""Filtered source Magnus replay after the minimum-weight ``P^2 Q`` repair."""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add,
    _bracket,
    _scale,
    _source_velocity,
)
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    forward_dexp_coefficients,
    inverse_dexp_coefficients,
)


MINIMUM_EXCESS = -8
MAXIMUM_INPUT_COST = 6


def _excess(exponent: tuple[int, int], cost: int) -> int:
    return exponent[0] + exponent[1] - 4 * cost - 4


def _project(
    value: SparseHamiltonian,
    cost: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if _excess(exponent, cost) >= MINIMUM_EXCESS
    }


def _to_sparse(
    expression: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> SparseHamiltonian:
    numerator, denominator = sp.together(
        sp.cancel(expression)
    ).as_numer_denom()
    assert not ({u, z} & denominator.free_symbols)
    return {
        exponent: sp.cancel(coefficient / denominator)
        for exponent, coefficient in sp.Poly(
            sp.expand(numerator), u, z
        ).terms()
        if coefficient != 0
    }


def _series_bracket(
    left: list[SparseHamiltonian],
    right: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        if not left_value:
            continue
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            if not right_value:
                continue
            order = left_order + right_order
            value = _project(
                _bracket(left_value, right_value, 2),
                order + 1,
            )
            result[order] = _add(result[order], value)
    return result


def _projected_magnus(
    velocity: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    padded_velocity = [
        _project(value, order + 1)
        for order, value in enumerate(velocity)
    ] + [
        {} for _ in range(maximum_order - len(velocity))
    ]
    logarithm: list[SparseHamiltonian] = [
        {} for _ in range(maximum_order + 1)
    ]
    inverse = inverse_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for derivative_order in range(maximum_order):
        result = padded_velocity[derivative_order]
        nested = padded_velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _series_bracket(
                prefix, nested, derivative_order
            )
            if inverse[depth]:
                result = _add(
                    result,
                    _scale(
                        nested[derivative_order],
                        inverse[depth],
                    ),
                )
        logarithm[derivative_order + 1] = _scale(
            result,
            Fraction(1, derivative_order + 1),
        )
    return logarithm


def _projected_velocity_from_magnus(
    logarithm: list[SparseHamiltonian],
    maximum_order: int,
) -> list[SparseHamiltonian]:
    padded_logarithm = logarithm[: maximum_order + 1] + [
        {} for _ in range(
            maximum_order + 1 - len(logarithm)
        )
    ]
    derivative = [
        _scale(
            padded_logarithm[order + 1],
            Fraction(order + 1),
        )
        for order in range(maximum_order)
    ] + [{}]
    result = list(derivative)
    nested = derivative
    forward = forward_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for depth in range(1, maximum_order + 1):
        nested = _series_bracket(
            padded_logarithm, nested, maximum_order
        )
        for order in range(maximum_order):
            if forward[depth]:
                result[order] = _add(
                    result[order],
                    _scale(nested[order], forward[depth]),
                )
    return result


def _translated_velocity(
    connection_data: dict[str, object] | None = None,
) -> list[SparseHamiltonian]:
    base_velocity, (_s, v, z), _p3, _pq = _source_velocity(
        MAXIMUM_INPUT_COST,
        connection_data,
    )
    data = (
        source_only_connection()
        if connection_data is None
        else connection_data
    )
    family_s, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u = sp.symbols("u")
    substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p_translated = sp.factor(family_p.subs(substitution))
    q_translated = sp.factor(family_q.subs(substitution))
    for value, maximum_exponent in (
        (p_translated, 3),
        (q_translated, 4),
    ):
        numerator, denominator = sp.together(
            value
        ).as_numer_denom()
        assert not ({u, z} & denominator.free_symbols)
        assert all(
            max(exponent) <= maximum_exponent
            for exponent, coefficient in sp.Poly(
                numerator, u, z
            ).terms()
            if coefficient != 0
        )
    perturbation = sp.series(
        -sp.Rational(1, 21)
        * family_s
        * p_translated**2
        * q_translated,
        family_s,
        0,
        MAXIMUM_INPUT_COST,
    ).removeO()
    perturbation = sp.expand(perturbation)

    velocity = []
    for order, base in enumerate(base_velocity):
        base_expression = sp.expand(
            sum(
                (
                    coefficient
                    * v**exponent[0]
                    * z**exponent[1]
                    for exponent, coefficient in base.items()
                ),
                sp.Integer(0),
            ).subs(v, u - 1)
        )
        combined = _to_sparse(
            base_expression
            + sp.cancel(
                perturbation.coeff(family_s, order)
            ),
            u,
            z,
        )
        velocity.append(_project(combined, order + 1))
    return velocity


def run(maximum_order: int = 36) -> dict[str, object]:
    if maximum_order < 24:
        raise ValueError("replay needs a held-out tail")
    velocity = _translated_velocity()
    assert 20 - 4 * (MAXIMUM_INPUT_COST + 1) - 4 < MINIMUM_EXCESS

    input_rows = []
    zero_excess = []
    for order, value in enumerate(velocity):
        cost = order + 1
        zero_excess.extend(
            (cost, exponent, coefficient)
            for exponent, coefficient in value.items()
            if _excess(exponent, cost) == 0
        )
        input_rows.append({
            "parameter_cost": cost,
            "retained_term_count": len(value),
            "retained_excesses": sorted({
                _excess(exponent, cost)
                for exponent in value
            }, reverse=True),
        })
    assert zero_excess == [
        (2, (6, 6), -sp.Rational(325, 2688)),
        (3, (8, 8), -sp.Rational(1, 14336)),
    ]

    logarithm = _projected_magnus(velocity, maximum_order)
    excess_minus_seven_terms = []
    for order in range(1, maximum_order + 1):
        for exponent, coefficient in logarithm[order].items():
            if _excess(exponent, order) != -7:
                continue
            difference = exponent[0] - exponent[1]
            excess_minus_seven_terms.append(
                (
                    order - difference,
                    order,
                    exponent,
                    sp.factor(coefficient),
                )
            )
    minimum_h = min(
        h_value
        for h_value, _order, _exponent, _coefficient
        in excess_minus_seven_terms
    )
    minimum_h_rows = [
        {
            "logarithmic_order": order,
            "hamiltonian_exponent": list(exponent),
            "coefficient": str(coefficient),
        }
        for h_value, order, exponent, coefficient
        in excess_minus_seven_terms
        if h_value == minimum_h
    ]

    # The next lattice layer h=5 is closed under the cost-two radial
    # adjoint.  The cost-three radial adjoint raises h and therefore cannot
    # act on this layer.  Removing h=5 from the logarithm isolates the
    # complete forcing from the terminating h=4 boundary.
    h_five_logarithm = []
    logarithm_without_h_five = []
    for order, value in enumerate(logarithm):
        h_five_terms = {
            exponent: coefficient
            for exponent, coefficient in value.items()
            if (
                _excess(exponent, order) == -7
                and order - (exponent[0] - exponent[1]) == 5
            )
        }
        h_five_logarithm.append(h_five_terms)
        logarithm_without_h_five.append({
            exponent: coefficient
            for exponent, coefficient in value.items()
            if exponent not in h_five_terms
        })
    h_five_external_velocity = _projected_velocity_from_magnus(
        logarithm_without_h_five, maximum_order
    )
    h_five_rows = []
    h_five_basis_multiplier = sp.Integer(1)
    h_five_log_values = []
    h_five_external_values = []
    h_five_velocity_values = []
    h_five_basis_multipliers = []
    for depth in range((maximum_order - 2) // 2 + 1):
        order = 2 + 2 * depth
        exponent = (
            1 + 5 * depth,
            4 + 3 * depth,
        )
        h_five_basis_multipliers.append(
            h_five_basis_multiplier
        )
        log_coefficient = sp.factor(
            h_five_logarithm[order].get(exponent, 0)
        )
        external_coefficient = sp.factor(
            h_five_external_velocity[order - 1].get(
                exponent, 0
            )
        )
        velocity_coefficient = sp.factor(
            (
                velocity[order - 1].get(exponent, 0)
                if order <= len(velocity)
                else 0
            )
        )
        normalized_log = sp.factor(
            log_coefficient / h_five_basis_multiplier
        )
        normalized_external = sp.factor(
            external_coefficient / h_five_basis_multiplier
        )
        normalized_velocity = sp.factor(
            velocity_coefficient / h_five_basis_multiplier
        )
        h_five_log_values.append(normalized_log)
        h_five_external_values.append(normalized_external)
        h_five_velocity_values.append(normalized_velocity)
        h_five_rows.append({
            "orbit_depth": depth,
            "logarithmic_order": order,
            "hamiltonian_exponent": list(exponent),
            "normalized_logarithm": str(normalized_log),
            "normalized_external_velocity": str(normalized_external),
            "normalized_actual_velocity": str(normalized_velocity),
        })
        h_five_basis_multiplier = sp.factor(
            h_five_basis_multiplier
            * (-sp.Rational(325, 5376))
            * 6
            * (2 * depth - 3)
        )

    h_five_x = sp.symbols("h_five_x")
    h_five_log_prefix = sum(
        (
            coefficient * h_five_x**depth
            for depth, coefficient in enumerate(
                h_five_log_values
            )
        ),
        sp.Integer(0),
    )
    h_five_external_prefix = sum(
        (
            coefficient * h_five_x**depth
            for depth, coefficient in enumerate(
                h_five_external_values
            )
        ),
        sp.Integer(0),
    )
    h_five_velocity_prefix = sum(
        (
            coefficient * h_five_x**depth
            for depth, coefficient in enumerate(
                h_five_velocity_values
            )
        ),
        sp.Integer(0),
    )
    h_five_f = (
        1 - sp.exp(-h_five_x)
    ) / h_five_x
    h_five_residual = sp.series(
        2 * h_five_log_prefix
        + 2
        * h_five_f
        * h_five_x
        * sp.diff(h_five_log_prefix, h_five_x)
        + h_five_external_prefix
        - h_five_velocity_prefix,
        h_five_x,
        0,
        len(h_five_log_values),
    ).removeO().expand()
    assert h_five_residual == 0

    # The finite-core elimination has one normalized cost-(2,4) seed:
    #
    #   [Z_2,Z_4] = -(227/46800) E_2.
    #
    # After that seed, the support grading and h=q-(a-b) boundary permit
    # only insertions of the cost-two radial logarithm A.  The complete
    # external velocity and actual velocity on the h=5 orbit are therefore
    # the following scalar series.  Solving the closed right-dexp equation
    # gives the Bernoulli response displayed below.
    cost_two_cost_four = _bracket(
        logarithm_without_h_five[2],
        logarithm_without_h_five[4],
        2,
    )
    normalized_cost_two_cost_four_seed = sp.factor(
        cost_two_cost_four[(11, 10)]
        / h_five_basis_multipliers[2]
    )
    assert (
        normalized_cost_two_cost_four_seed
        == -sp.Rational(227, 46800)
    )
    h_five_external_closed_form = (
        sp.Rational(227, 23400)
        * (
            sp.exp(-h_five_x)
            - 1
            + h_five_x
        )
    )
    h_five_velocity_closed_form = (
        -sp.Rational(1, 336)
        + sp.Rational(779, 23400) * h_five_x
    )
    h_five_response_closed_form = (
        -sp.Rational(221, 26208)
        + sp.Rational(23, 1950) * h_five_x
        + sp.Rational(13, 1872)
        * h_five_x
        / (sp.exp(h_five_x) - 1)
    )
    assert sp.simplify(
        2 * h_five_response_closed_form
        + 2
        * h_five_f
        * h_five_x
        * sp.diff(
            h_five_response_closed_form, h_five_x
        )
        + h_five_external_closed_form
        - h_five_velocity_closed_form
    ) == 0
    h_five_external_closed_prefix = sp.series(
        h_five_external_closed_form,
        h_five_x,
        0,
        len(h_five_external_values),
    ).removeO().expand()
    h_five_velocity_closed_prefix = sp.series(
        h_five_velocity_closed_form,
        h_five_x,
        0,
        len(h_five_velocity_values),
    ).removeO().expand()
    h_five_response_closed_prefix = sp.series(
        h_five_response_closed_form,
        h_five_x,
        0,
        len(h_five_log_values),
    ).removeO().expand()
    for depth in range(len(h_five_log_values)):
        assert sp.factor(
            h_five_external_closed_prefix.coeff(
                h_five_x, depth
            )
            - h_five_external_values[depth]
        ) == 0
        assert sp.factor(
            h_five_velocity_closed_prefix.coeff(
                h_five_x, depth
            )
            - h_five_velocity_values[depth]
        ) == 0
        assert sp.factor(
            h_five_response_closed_prefix.coeff(
                h_five_x, depth
            )
            - h_five_log_values[depth]
        ) == 0
        if depth >= 2:
            assert h_five_external_values[depth] == sp.factor(
                sp.Rational(227, 23400)
                * (-1) ** depth
                / sp.factorial(depth)
            )
            assert h_five_log_values[depth] == sp.factor(
                sp.Rational(13, 1872)
                * sp.bernoulli(depth)
                / sp.factorial(depth)
            )
    velocity_without_radial_origins = []
    for order, value in enumerate(velocity):
        cost = order + 1
        velocity_without_radial_origins.append({
            exponent: coefficient
            for exponent, coefficient in value.items()
            if not (
                (cost == 2 and exponent == (6, 6))
                or (cost == 3 and exponent == (8, 8))
            )
        })
    a_b_free_logarithm = _projected_magnus(
        velocity_without_radial_origins, 24
    )
    a_b_free_cores = []
    for order in range(1, 25):
        terms = {
            exponent: sp.factor(coefficient)
            for exponent, coefficient in (
                a_b_free_logarithm[order].items()
            )
            if _excess(exponent, order) == -7
        }
        if terms:
            a_b_free_cores.append({
                "logarithmic_order": order,
                "terms": {
                    f"{exponent[0]},{exponent[1]}": str(coefficient)
                    for exponent, coefficient in sorted(terms.items())
                },
            })
    polynomial_logarithm = [
        value if order <= 6 else {}
        for order, value in enumerate(logarithm)
    ]
    polynomial_velocity = _projected_velocity_from_magnus(
        polynomial_logarithm, maximum_order
    )

    a_coefficient = -sp.Rational(325, 5376)
    boundary_rows = []
    normalized_forcing_values = []
    normalized_response_values = []
    basis_multiplier = sp.Integer(1)
    for depth in range((maximum_order - 7) // 2 + 1):
        order = 7 + 2 * depth
        exponent = (
            13 + 5 * depth,
            12 + 3 * depth,
        )
        forcing = sp.factor(
            polynomial_velocity[order - 1].get(exponent, 0)
        )
        response = sp.factor(
            logarithm[order].get(exponent, 0)
        )
        normalized_forcing = sp.factor(
            forcing / basis_multiplier
        )
        normalized_response = sp.factor(
            response / basis_multiplier
        )
        expected_normalized_forcing = (
            -sp.Rational(1105, 693633024)
            if depth == 0
            else sp.factor(
                (-1) ** depth
                * sp.Rational(65, 2774532096)
                * (
                    20 * depth**3
                    + 35 * depth**2
                    - 241 * depth
                    - 438
                )
                / sp.factorial(depth + 3)
            )
        )
        assert normalized_forcing == expected_normalized_forcing
        normalized_forcing_values.append(normalized_forcing)
        normalized_response_values.append(normalized_response)
        boundary_rows.append({
            "orbit_depth": depth,
            "logarithmic_order": order,
            "hamiltonian_exponent": list(exponent),
            "basis_multiplier": str(basis_multiplier),
            "normalized_forcing": str(normalized_forcing),
            "normalized_response": str(normalized_response),
        })
        basis_multiplier = sp.factor(
            basis_multiplier
            * a_coefficient
            * 6
            * (2 * depth + 1)
        )

    x = sp.symbols("x")
    theta = lambda value: sp.expand(  # noqa: E731
        x * sp.diff(value, x)
    )
    divided_exponential = (
        1 - x + x**2 / 2 - sp.exp(-x)
    ) / x**3
    forcing = sp.factor(
        sp.Rational(65, 2774532096)
        * (
            20 * theta(theta(theta(divided_exponential)))
            + 35 * theta(theta(divided_exponential))
            - 241 * theta(divided_exponential)
            - 438 * divided_exponential
        )
        + sp.Rational(325, 2774532096)
    )
    forcing_closed_form = sp.factor(
        sp.Rational(65, 2774532096)
        * sp.exp(-x)
        / x**3
        * (
            5 * x**3 * sp.exp(x)
            + 20 * x**3
            - 91 * x**2 * sp.exp(x)
            + 85 * x**2
            - 24 * x * sp.exp(x)
            - 36 * x
            + 60 * sp.exp(x)
            - 60
        )
    )
    assert sp.factor(forcing - forcing_closed_form) == 0
    forcing_prefix = sp.series(
        forcing, x, 0, len(normalized_forcing_values)
    ).removeO().expand()
    assert all(
        sp.factor(
            forcing_prefix.coeff(x, depth) - coefficient
        ) == 0
        for depth, coefficient in enumerate(
            normalized_forcing_values
        )
    )

    response_prefix = sum(
        (
            coefficient * x**depth
            for depth, coefficient in enumerate(
                normalized_response_values
            )
        ),
        sp.Integer(0),
    )
    f = (1 - sp.exp(-x)) / x
    response_residual = sp.series(
        2 * response_prefix
        + f * (
            5 * response_prefix
            + 2 * x * sp.diff(response_prefix, x)
        )
        + forcing,
        x,
        0,
        len(normalized_response_values),
    ).removeO().expand()
    first_boundary_coupling_depth = next(
        (
            depth
            for depth in range(len(normalized_response_values))
            if sp.factor(response_residual.coeff(x, depth)) != 0
        ),
        None,
    )
    assert first_boundary_coupling_depth == 3
    output_rows = []
    orders_by_excess: dict[int, list[int]] = {}
    for order in range(1, maximum_order + 1):
        by_excess: dict[int, list[tuple[
            tuple[int, int], sp.Expr
        ]]] = {}
        for exponent, coefficient in logarithm[order].items():
            excess = _excess(exponent, order)
            by_excess.setdefault(excess, []).append(
                (exponent, sp.factor(coefficient))
            )
            orders_by_excess.setdefault(excess, []).append(order)
        if by_excess:
            maximum = max(by_excess)
            output_rows.append({
                "logarithmic_order": order,
                "maximum_excess": maximum,
                "maximum_excess_terms": {
                    f"{exponent[0]},{exponent[1]}": str(coefficient)
                    for exponent, coefficient in sorted(by_excess[maximum])
                },
                "retained_term_count": len(logarithm[order]),
            })

    return {
        "schema": "axiompack.jacobian_p2q_source_newton_modules.v1",
        "minimum_excess": MINIMUM_EXCESS,
        "uniform_hamiltonian_total_degree": 20,
        "maximum_input_cost": MAXIMUM_INPUT_COST,
        "zero_excess_generators": [
            "-325*u^6*z^6/5376 at logarithmic cost 2",
            "-u^8*z^8/43008 at logarithmic cost 3",
        ],
        "a_boundary": {
            "basis": (
                "E_0=u^13*z^12; "
                "E_(k+1)=[-325*u^6*z^6/5376,E_k]"
            ),
            "right_dexp_operator": (
                "2*D + f*(5*D+2*x*D'), "
                "f=(1-exp(-x))/x"
            ),
            "forcing_generating_function": str(forcing),
            "forcing_tail_coefficient": (
                "(-1)^k*(65/2774532096)"
                "*(20*k^3+35*k^2-241*k-438)/(k+3)!, k>=1"
            ),
            "response_prefix_residual": str(response_residual),
            "first_neighbor_orbit_coupling_depth": (
                first_boundary_coupling_depth
            ),
            "uncoupled_diagonal": "2*(k+7/2)",
            "all_order_boundary_equation_closed": False,
            "rows": boundary_rows,
        },
        "radial_free_excess_minus_seven_cores": a_b_free_cores,
        "minimum_h_boundary": {
            "h_definition": "q-(a-b)",
            "h_value": minimum_h,
            "cost_two_adjoint_shift": 0,
            "cost_three_adjoint_shift": 1,
            "rows": minimum_h_rows,
        },
        "h_five_boundary": {
            "h_value": 5,
            "basis": (
                "E_0=u*z^4; "
                "E_(k+1)=[-325*u^6*z^6/5376,E_k]"
            ),
            "right_dexp_operator": "2*D+2*f*x*D'",
            "normalized_cost_two_cost_four_seed": str(
                normalized_cost_two_cost_four_seed
            ),
            "external_velocity_generating_function": str(
                h_five_external_closed_form
            ),
            "actual_velocity_generating_function": str(
                h_five_velocity_closed_form
            ),
            "logarithm_generating_function": str(
                h_five_response_closed_form
            ),
            "tail_coefficient": (
                "(13/1872)*B_k/k! for k>=2"
            ),
            "nonzero_subsequence": (
                "k=2m, m>=1; logarithmic order n=2+4m; "
                "source derivation degree 4*n-6"
            ),
            "response_prefix_residual": str(h_five_residual),
            "rows": h_five_rows,
        },
        "input_rows": input_rows,
        "output_rows": output_rows,
        "orders_by_excess": {
            str(excess): sorted(set(orders))
            for excess, orders in sorted(
                orders_by_excess.items(), reverse=True
            )
        },
        "claim_boundary": (
            "Exact source logarithmic rate four for the P^2*Q "
            "cancellation. The all-order upper bound is sharp on the "
            "h=5, G_4=-7 Bernoulli ray at orders n=2+4m. This "
            "classifies one exact connection, not the full affine "
            "order-one cancellation hyperplane or the symmetric minimax."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
