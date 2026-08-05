#!/usr/bin/env python3
"""Filtered source-Magnus replay after the ``-s*Q**3/56`` cancellation."""

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


MINIMUM_EXCESS = -20
MAXIMUM_INPUT_COST = 5


def _excess(exponent: tuple[int, int], cost: int) -> int:
    return exponent[0] + exponent[1] - 7 * cost - 4


def _project(
    value: SparseHamiltonian,
    cost: int,
    minimum_excess: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if _excess(exponent, cost) >= minimum_excess
    }


def _to_sparse(
    expression: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> SparseHamiltonian:
    expression = sp.cancel(expression)
    numerator, denominator = sp.together(
        expression
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
    minimum_excess: int,
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
                minimum_excess,
            )
            result[order] = _add(result[order], value)
    return result


def _projected_magnus(
    velocity: list[SparseHamiltonian],
    maximum_order: int,
    minimum_excess: int,
) -> list[SparseHamiltonian]:
    padded_velocity = [
        _project(value, order + 1, minimum_excess)
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
                prefix,
                nested,
                derivative_order,
                minimum_excess,
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
    minimum_excess: int,
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
            padded_logarithm,
            nested,
            maximum_order,
            minimum_excess,
        )
        for order in range(maximum_order):
            if forward[depth]:
                result[order] = _add(
                    result[order],
                    _scale(nested[order], forward[depth]),
                )
    return result


def _adjoint_multiplier(depth: int) -> sp.Expr:
    return sp.factor(
        sp.prod(
            sp.Rational(9, 896) * (2 * index + 1)
            for index in range(depth)
        )
    )


def _translated_velocity() -> tuple[
    list[SparseHamiltonian],
    tuple[sp.Symbol, sp.Symbol],
]:
    base_velocity, (_s, v, z), _p3, _pq = _source_velocity(
        MAXIMUM_INPUT_COST
    )
    data = source_only_connection()
    family_s, family_v, family_t, _unused = data["symbols"]
    family_q = data["family"][1]
    u = sp.symbols("u")
    q_translated = sp.factor(
        family_q.subs({
            family_v: u - 1,
            family_t: (z - 2 + 3 * (u - 1)) / 2,
        })
    )
    q_numerator, q_denominator = sp.together(
        q_translated
    ).as_numer_denom()
    assert not ({u, z} & q_denominator.free_symbols)
    q_support = [
        exponent
        for exponent, coefficient in sp.Poly(
            q_numerator, u, z
        ).terms()
        if coefficient != 0
    ]
    assert all(max(exponent) <= 4 for exponent in q_support)

    perturbation = sp.series(
        -sp.Rational(1, 7)
        * family_s
        * q_translated**3,
        family_s,
        0,
        MAXIMUM_INPUT_COST,
    ).removeO()
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
        perturbation_coefficient = sp.cancel(
            sp.expand(perturbation).coeff(family_s, order)
        )
        combined = _to_sparse(
            base_expression + perturbation_coefficient,
            u,
            z,
        )
        velocity.append(
            _project(
                combined, order + 1, MINIMUM_EXCESS
            )
        )
    return velocity, (u, z)


def run(maximum_order: int = 36) -> dict[str, object]:
    if maximum_order < 24:
        raise ValueError("replay needs a held-out tail")
    velocity, (_u, _z) = _translated_velocity()

    # Base Hamiltonians have exponents at most nine; Q_s has exponents at
    # most four, so the perturbation cube has exponents at most twelve.
    # Every instantaneous Hamiltonian therefore has total degree at most
    # 24.  At cost q>=6 its excess is at most 20-7q<-20.
    uniform_hamiltonian_total_degree = 24
    assert (
        uniform_hamiltonian_total_degree
        - 7 * (MAXIMUM_INPUT_COST + 1)
        - 4
        < MINIMUM_EXCESS
    )

    zero_excess = []
    input_rows = []
    for order, value in enumerate(velocity):
        cost = order + 1
        rows = [
            (
                _excess(exponent, cost),
                exponent,
                coefficient,
            )
            for exponent, coefficient in value.items()
        ]
        zero_excess.extend(
            (cost, exponent, coefficient)
            for excess, exponent, coefficient in rows
            if excess == 0
        )
        input_rows.append({
            "parameter_cost": cost,
            "retained_term_count": len(rows),
            "retained_excesses": sorted({
                excess for excess, _exponent, _coefficient in rows
            }, reverse=True),
        })
    assert zero_excess == [
        (2, (9, 9), sp.Rational(1, 448))
    ]

    logarithm = _projected_magnus(
        velocity, maximum_order, MINIMUM_EXCESS
    )

    # The full logarithm outside the distinguished excess -13 orbit stops
    # at cost five.  Replaying that polynomial alone isolates the forcing
    # on E_k = ad_A^k(u^17*z^16).
    polynomial_logarithm = [
        value if order <= 5 else {}
        for order, value in enumerate(logarithm)
    ]
    polynomial_velocity = _projected_velocity_from_magnus(
        polynomial_logarithm,
        maximum_order,
        -13,
    )
    forcing_constant = sp.Rational(27, 12845056)
    forcing_rows = []
    ray_rows = []
    for depth in range((maximum_order - 6) // 2 + 1):
        order = 6 + 2 * depth
        exponent = (
            17 + 8 * depth,
            16 + 6 * depth,
        )
        basis_multiplier = _adjoint_multiplier(depth)
        actual_forcing = sp.factor(
            polynomial_velocity[order - 1].get(exponent, 0)
        )
        expected_forcing = sp.factor(
            -forcing_constant
            * (-1) ** depth
            / sp.factorial(depth + 2)
            * basis_multiplier
        )
        assert actual_forcing == expected_forcing
        actual_ray = sp.factor(
            logarithm[order].get(exponent, 0)
        )
        expected_ray = sp.factor(
            forcing_constant
            * sp.bernoulli(depth + 2)
            / sp.factorial(depth + 2)
            * basis_multiplier
        )
        assert actual_ray == expected_ray
        forcing_rows.append({
            "orbit_depth": depth,
            "velocity_cost": order,
            "coefficient": str(actual_forcing),
            "formula_matches": True,
        })
        ray_rows.append({
            "orbit_depth": depth,
            "logarithmic_order": order,
            "hamiltonian_exponent": list(exponent),
            "coefficient": str(actual_ray),
            "bernoulli_index": depth + 2,
            "formula_matches": True,
        })

    # The exact scalar equation on the terminal module.  Its coefficient
    # diagonal is 2*(k+3), so this solution is unique formally.
    x = sp.symbols("x")
    f = (1 - sp.exp(-x)) / x
    bernoulli = x / (sp.exp(x) - 1)
    response = sp.factor(
        forcing_constant
        * (bernoulli - 1 + x / 2)
        / x**2
    )
    forcing = sp.factor(
        -forcing_constant
        * (x - 1 + sp.exp(-x))
        / x**2
    )
    response_residual = sp.factor(
        sp.together(
            2 * response
            + f * (
                4 * response
                + 2 * x * sp.diff(response, x)
            )
            + forcing
        )
    )
    assert response_residual == 0

    # Beyond the finite polynomial prefix, excess -13 contains only the
    # displayed orbit.  This is checked independently of its coefficient
    # formula in the complete filtered replay.
    for order in range(6, maximum_order + 1):
        expected_exponent = (
            (
                17 + 8 * ((order - 6) // 2),
                16 + 6 * ((order - 6) // 2),
            )
            if order % 2 == 0
            else None
        )
        grade_terms = {
            exponent: coefficient
            for exponent, coefficient in logarithm[order].items()
            if _excess(exponent, order) == -13
        }
        if expected_exponent is None:
            assert grade_terms == {}
        else:
            assert set(grade_terms) <= {expected_exponent}

    output_rows = []
    excess_support: dict[int, list[int]] = {}
    for order in range(1, maximum_order + 1):
        by_excess: dict[int, list[tuple[
            tuple[int, int], sp.Expr
        ]]] = {}
        for exponent, coefficient in logarithm[order].items():
            excess = _excess(exponent, order)
            by_excess.setdefault(excess, []).append(
                (exponent, sp.factor(coefficient))
            )
            excess_support.setdefault(excess, []).append(order)
        if not by_excess:
            continue
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
        "schema": "axiompack.jacobian_q3_source_excess_modules.v1",
        "minimum_excess": MINIMUM_EXCESS,
        "maximum_input_cost": MAXIMUM_INPUT_COST,
        "uniform_hamiltonian_total_degree": (
            uniform_hamiltonian_total_degree
        ),
        "zero_excess_generator": "u^9*z^9/448 at cost 2",
        "excess_minus_thirteen_equation": {
            "basis": (
                "E_0=u^17*z^16; E_(k+1)=[u^9*z^9/896,E_k]"
            ),
            "basis_multiplier": (
                "product_(j=0)^(k-1)(9*(2*j+1)/896)"
            ),
            "forcing_generating_function": str(forcing),
            "response_generating_function": str(response),
            "right_dexp_equation": (
                "2*D + f*(4*D+2*x*D') + forcing = 0, "
                "f=(1-exp(-x))/x"
            ),
            "formal_residual": str(response_residual),
            "uniqueness_diagonal": "2*(k+3)",
            "coefficient": (
                "(27/12845056)*B_(k+2)/(k+2)! "
                "* product_(j=0)^(k-1)(9*(2*j+1)/896)"
            ),
            "nonzero_orders": "n=6+4*m",
            "hamiltonian": (
                "nonzero scalar*u^(17+16*m)*z^(16+12*m)"
            ),
            "source_derivation_degree": "7*n-12",
        },
        "forcing_rows": forcing_rows,
        "ray_rows": ray_rows,
        "input_rows": input_rows,
        "output_rows": output_rows,
        "orders_by_excess": {
            str(excess): sorted(set(orders))
            for excess, orders in sorted(
                excess_support.items(), reverse=True
            )
        },
        "claim_boundary": (
            "All-order source logarithmic escape for the exact Q^3 "
            "cancellation connection. The closed excess quotient and "
            "right-dexp identity give source degree 7*n-12 at every "
            "n=6+4*m. This excludes that connection but does not constrain "
            "a later coefficientwise moving staircase."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
