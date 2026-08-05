#!/usr/bin/env python3
"""Exact first nonlinear Magnus shells of a finite C-normal prefix.

For a row-one target prefix

    sum lambda[a,b] * P**a * Q**b * C(P,Q),

only the first three parameter coefficients A, B, C of its pulled-back
source velocity are needed for the first quadratic and cubic terms:

    nonlinear(Omega_6) = [A,C] / 48,
    cubic(Omega_7)     = -[A,[A,B]] / 5040.

Computing these sparse brackets directly avoids expanding the unused
linear part of the full order-seven Magnus logarithm.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Iterable

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket,
    _ops,
)
from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_c_multiplier,
    _canonical_cone_monomial,
    _seed_c_diagonal,
    _seed_diagonal,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
)


PrefixTerm = tuple[int, int, sp.Expr]
SparseHamiltonian = dict[tuple[int, int], sp.Expr]


def _add_scaled(
    destination: SparseHamiltonian,
    source: SparseHamiltonian,
    scalar: sp.Expr,
) -> None:
    for exponent, coefficient in source.items():
        destination[exponent] = sp.factor(
            destination.get(exponent, 0) + scalar * coefficient
        )
        if destination[exponent] == 0:
            del destination[exponent]


def _scale(
    source: SparseHamiltonian,
    scalar: sp.Expr,
) -> SparseHamiltonian:
    return {
        exponent: sp.factor(scalar * coefficient)
        for exponent, coefficient in source.items()
        if coefficient != 0
    }


def _top_shell(value: SparseHamiltonian) -> dict[str, object]:
    degree = max(
        (sum(exponent) for exponent in value),
        default=None,
    )
    return {
        "degree": degree,
        "terms": [
            [list(exponent), str(coefficient)]
            for exponent, coefficient in sorted(value.items())
            if degree is not None and sum(exponent) == degree
        ],
    }


def _to_expression(
    value: SparseHamiltonian,
    first: sp.Symbol,
    second: sp.Symbol,
) -> sp.Expr:
    return sp.expand(sum(
        (
            coefficient
            * first**exponent[0]
            * second**exponent[1]
            for exponent, coefficient in value.items()
        ),
        sp.Integer(0),
    ))


def _logarithm_first_second_row(
    raw_logarithm: SparseHamiltonian,
    seed_p: sp.Expr,
    seed_q: sp.Expr,
    seed_c: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> tuple[SparseHamiltonian, list[dict[str, object]]]:
    """Apply the exact current radial and one-C solves at cost three."""

    objective = _to_expression(
        raw_logarithm,
        first,
        second,
    )
    controls = []
    current_row_log_scale = sp.Rational(1, 3)
    while True:
        sparse = _to_sparse(objective, first, second)
        cancellable = [
            exponent[0]
            for exponent in sparse
            if (
                exponent[0] == exponent[1]
                and _canonical_cone_monomial(
                    exponent[0]
                ) is not None
            )
        ]
        if not cancellable:
            break
        weight = max(cancellable)
        multiplier = _canonical_cone_monomial(weight)
        assert multiplier is not None
        coefficient = sp.factor(
            -sparse[(weight, weight)]
            / (
                current_row_log_scale
                * _seed_diagonal(*multiplier)
            )
        )
        objective = sp.expand(
            objective
            + current_row_log_scale
            * 8
            * coefficient
            * seed_p**multiplier[0]
            * seed_q**multiplier[1]
        )
        controls.append({
            "kind": "radial",
            "p_exponent": multiplier[0],
            "q_exponent": multiplier[1],
            "coefficient": str(coefficient),
        })

    while True:
        sparse = _to_sparse(objective, first, second)
        cancellable = [
            exponent[0]
            for exponent in sparse
            if (
                exponent[1] - exponent[0] == 2
                and _canonical_c_multiplier(
                    exponent[0]
                ) is not None
            )
        ]
        if not cancellable:
            break
        radial_degree = max(cancellable)
        multiplier = _canonical_c_multiplier(radial_degree)
        assert multiplier is not None
        coefficient = sp.factor(
            -sparse[(
                radial_degree,
                radial_degree + 2,
            )]
            / (
                current_row_log_scale
                * _seed_c_diagonal(*multiplier)
            )
        )
        objective = sp.expand(
            objective
            + current_row_log_scale
            * 8
            * coefficient
            * seed_p**multiplier[0]
            * seed_q**multiplier[1]
            * seed_c
        )
        controls.append({
            "kind": "one_c",
            "p_exponent": multiplier[0],
            "q_exponent": multiplier[1],
            "coefficient": str(coefficient),
        })
    return _to_sparse(objective, first, second), controls


def _series_product(
    left: list[sp.Expr],
    right: list[sp.Expr],
    maximum_order: int,
) -> list[sp.Expr]:
    return [
        sp.expand(sum(
            (
                left[index] * right[order - index]
                for index in range(order + 1)
            ),
            sp.Integer(0),
        ))
        for order in range(maximum_order + 1)
    ]


def run(
    prefix_terms: Iterable[PrefixTerm] = ((0, 2, sp.Integer(1)),),
) -> dict[str, object]:
    configured_terms = [
        (p_exponent, q_exponent, sp.factor(coefficient))
        for p_exponent, q_exponent, coefficient in prefix_terms
        if coefficient != 0
    ]
    if not configured_terms:
        raise ValueError("the finite C-prefix must be nonzero")
    for p_exponent, q_exponent, _coefficient in configured_terms:
        if min(p_exponent, q_exponent) < 0:
            raise ValueError("prefix exponents must be nonnegative")
        if p_exponent + 3 > 2 * q_exponent:
            raise ValueError("the C-multiple is outside the cone")

    data = source_only_connection()
    s, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u, z = sp.symbols("u z")
    fixed_substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.cancel(family_p.subs(fixed_substitution))
    q = sp.cancel(family_q.subs(fixed_substitution))
    # H_pre(s) is inserted in velocity order one, so its coefficients
    # through s**5 supply velocity orders one through six.
    maximum_parameter_order = 5
    p_coefficients = [
        sp.expand(
            sp.diff(p, s, order).subs(s, 0) / sp.factorial(order)
        )
        for order in range(maximum_parameter_order + 1)
    ]
    q_coefficients = [
        sp.expand(
            sp.diff(q, s, order).subs(s, 0) / sp.factorial(order)
        )
        for order in range(maximum_parameter_order + 1)
    ]
    monomial_cache: dict[tuple[int, int], list[sp.Expr]] = {
        (0, 0): [
            sp.Integer(1),
            *(
                sp.Integer(0)
                for _ in range(maximum_parameter_order)
            ),
        ]
    }

    def monomial_coefficients(
        p_exponent: int,
        q_exponent: int,
    ) -> list[sp.Expr]:
        key = (p_exponent, q_exponent)
        if key in monomial_cache:
            return monomial_cache[key]
        if p_exponent:
            parent = monomial_coefficients(
                p_exponent - 1, q_exponent
            )
            factor = p_coefficients
        else:
            parent = monomial_coefficients(
                p_exponent, q_exponent - 1
            )
            factor = q_coefficients
        result = _series_product(
            parent, factor, maximum_parameter_order
        )
        monomial_cache[key] = result
        return result

    target_c_terms = {
        (3, 0): sp.Integer(4),
        (2, 0): -sp.Integer(1),
        (1, 1): -sp.Integer(18),
        (0, 2): sp.Integer(27),
        (0, 1): sp.Integer(4),
    }
    seed_p = sp.expand(p.subs(s, 0))
    seed_q = sp.expand(q.subs(s, 0))
    seed_c = sp.expand(
        4 * seed_p**3
        - seed_p**2
        - 18 * seed_p * seed_q
        + 27 * seed_q**2
        + 4 * seed_q
    )
    velocity_coefficients: list[SparseHamiltonian] = [
        {} for _ in range(maximum_parameter_order + 1)
    ]
    for p_exponent, q_exponent, prefix_coefficient in configured_terms:
        for (
            c_p_exponent,
            c_q_exponent,
        ), c_coefficient in target_c_terms.items():
            coefficients = monomial_coefficients(
                p_exponent + c_p_exponent,
                q_exponent + c_q_exponent,
            )
            for order, expression in enumerate(coefficients):
                _add_scaled(
                    velocity_coefficients[order],
                    _to_sparse(expression, u, z),
                    8 * prefix_coefficient * c_coefficient,
                )

    first, second, third = velocity_coefficients[:3]
    quadratic = _scale(
        _bracket(first, third, density_power=2),
        sp.Rational(1, 48),
    )
    cubic = _scale(
        _bracket(
            first,
            _bracket(first, second, density_power=2),
            density_power=2,
        ),
        -sp.Rational(1, 5040),
    )
    source_velocity = [{}, *velocity_coefficients]
    source_logarithm = magnus_from_velocity(
        source_velocity,
        7,
        _ops(2),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    coupled_cost_three, cost_three_controls = (
        _logarithm_first_second_row(
            _scale(
                velocity_coefficients[1],
                sp.Rational(1, 3),
            ),
            seed_p,
            seed_q,
            seed_c,
            u,
            z,
        )
    )
    return {
        "schema": (
            "axiompack.jacobian_cone_finite_c_prefix_"
            "top_cascade.v1"
        ),
        "prefix_terms": [
            {
                "p_exponent": p_exponent,
                "q_exponent": q_exponent,
                "cusp_weight": 2 * p_exponent + 3 * q_exponent,
                "coefficient": str(coefficient),
            }
            for p_exponent, q_exponent, coefficient
            in configured_terms
        ],
        "source_velocity_coefficient_top_shells": [
            _top_shell(value) for value in velocity_coefficients
        ],
        "isolated_omega_6_quadratic_shell": _top_shell(quadratic),
        "isolated_omega_7_cubic_shell": _top_shell(cubic),
        "complete_omega_6_shell": _top_shell(source_logarithm[6]),
        "complete_omega_7_shell": _top_shell(source_logarithm[7]),
        "coupled_logarithm_first_cost_three": {
            "coefficient": {
                f"{exponent[0]},{exponent[1]}": str(coefficient)
                for exponent, coefficient
                in sorted(coupled_cost_three.items())
            },
            "top_shell": _top_shell(coupled_cost_three),
            "identically_zero": not coupled_cost_three,
            "current_controls": cost_three_controls,
        },
        "magnus_identities": {
            "omega_6_quadratic": "[A,C]/48",
            "omega_7_cubic": "-[A,[A,B]]/5040",
        },
        "claim_boundary": (
            "Exact first quadratic and cubic source-Magnus shells for "
            "one finite row-one C-normal prefix, plus the exact coupled "
            "cost-three normalization; no general all-order recurrence."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
