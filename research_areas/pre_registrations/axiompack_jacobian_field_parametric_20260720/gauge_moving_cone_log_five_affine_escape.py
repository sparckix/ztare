#!/usr/bin/env python3
"""Complete-affine cancellation test for the degree-14 source log shell."""

from __future__ import annotations

import hashlib
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

import gauge_moving_section_affine_extension as AFFINE  # noqa: E402
from gauge_controlled_global_magnus import (  # noqa: E402
    _bracket as _source_bracket,
)
from gauge_moving_lie_cone_magnus import (  # noqa: E402
    _equal,
    _formal_ops,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


Pair = tuple[sp.Expr, sp.Expr]
Prefix = tuple[dict[int, sp.Expr], dict[int, Pair]]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _carry_through_order_four(
    family: AFFINE._Family,
) -> tuple[Prefix, list[Prefix]]:
    caps = (5, 5, 7, 9, 11)
    base: Prefix = ({}, {})
    directions: list[Prefix] = []
    for order, selected_cap in enumerate(caps):
        residual = family.residual(order, base)
        deltas = [
            family.delta_residual(order, direction)
            for direction in directions
        ]
        matrix, rhs, _row_keys, metadata = AFFINE._joint_system(
            family=family,
            category="cone",
            order=order,
            source_cap=selected_cap,
            residual=residual,
            lower_deltas=deltas,
        )
        solution = AFFINE._particular_solution(matrix, rhs)
        current_count = len(metadata)
        hamiltonian, source = AFFINE._decode(
            sp.Matrix(solution[:current_count, :]),
            metadata,
            family.v,
            family.t,
        )
        for scalar, direction in zip(
            list(solution[current_count:, 0]),
            directions,
            strict=True,
        ):
            AFFINE._add_scaled_prefix(base, direction, scalar)
        base[0][order] = hamiltonian
        base[1][order] = source

        next_directions: list[Prefix] = []
        for vector in matrix.to_Matrix().nullspace():
            direction: Prefix = ({}, {})
            for scalar, lower in zip(
                list(vector[current_count:, 0]),
                directions,
                strict=True,
            ):
                AFFINE._add_scaled_prefix(direction, lower, scalar)
            direction_hamiltonian, direction_source = AFFINE._decode(
                sp.Matrix(vector[:current_count, :]),
                metadata,
                family.v,
                family.t,
            )
            direction[0][order] = direction_hamiltonian
            direction[1][order] = direction_source
            next_directions.append(direction)
        directions = next_directions
    return base, directions


def _symbolic_prefix(
    base: Prefix,
    directions: list[Prefix],
    parameters: tuple[sp.Symbol, ...],
) -> Prefix:
    result: Prefix = (
        dict(base[0]),
        dict(base[1]),
    )
    for parameter, direction in zip(
        parameters, directions, strict=True
    ):
        AFFINE._add_scaled_prefix(result, direction, parameter)
    return result


def _current_contact_image(
    family: AFFINE._Family,
    prefix: Prefix,
    order: int,
) -> Pair:
    source = prefix[1].get(
        order, (sp.Integer(0), sp.Integer(0))
    )
    hamiltonian = prefix[0].get(order, sp.Integer(0))
    source_image = family.jacobian * sp.Matrix(source)
    target_field = AFFINE._hamiltonian_field(
        hamiltonian, family.p, family.q
    )
    target_image = AFFINE._substitute(
        target_field,
        family.p,
        family.q,
        family.p0,
        family.q0,
    )
    return (
        sp.expand(source_image[0] + target_image[0]),
        sp.expand(source_image[1] + target_image[1]),
    )


def _verify_contact_affine_family(
    family: AFFINE._Family,
    base: Prefix,
    directions: list[Prefix],
) -> None:
    for order in range(5):
        base_image = _current_contact_image(
            family, base, order
        )
        residual = family.residual(order, base)
        assert all(
            sp.expand(base_image[component] - residual[component]) == 0
            for component in range(2)
        )
        assert sp.expand(
            sp.diff(
                family.gamma**2 * base[1][order][0],
                family.v,
            )
            + sp.diff(
                family.gamma**2 * base[1][order][1],
                family.t,
            )
        ) == 0
        for direction in directions:
            direction_image = _current_contact_image(
                family, direction, order
            )
            delta_residual = family.delta_residual(
                order, direction
            )
            assert all(
                sp.expand(
                    direction_image[component]
                    - delta_residual[component]
                ) == 0
                for component in range(2)
            )
            assert sp.expand(
                sp.diff(
                    family.gamma**2
                    * direction[1].get(
                        order,
                        (sp.Integer(0), sp.Integer(0)),
                    )[0],
                    family.v,
                )
                + sp.diff(
                    family.gamma**2
                    * direction[1].get(
                        order,
                        (sp.Integer(0), sp.Integer(0)),
                    )[1],
                    family.t,
                )
            ) == 0


def _degree_shell(
    value: Pair,
    first: sp.Symbol,
    second: sp.Symbol,
    degree: int,
) -> Pair:
    return tuple(
        sp.expand(sum(
            coefficient * first**exponent[0] * second**exponent[1]
            for exponent, coefficient in sp.Poly(
                component, first, second
            ).terms()
            if sum(exponent) == degree
        ))
        for component in value
    )  # type: ignore[return-value]


def _shell_equations(
    shell: Pair,
    first: sp.Symbol,
    second: sp.Symbol,
) -> list[sp.Expr]:
    coefficients = []
    for component in shell:
        coefficients.extend(
            sp.expand(coefficient)
            for _exponent, coefficient in sp.Poly(
                component, first, second
            ).terms()
        )
    return sorted(
        {coefficient for coefficient in coefficients if coefficient != 0},
        key=str,
    )


def _bracket_algebra_receipt() -> dict[str, object]:
    a, b, c, d = sp.symbols("a b c d")
    coefficient = sp.factor(
        c
        - a * d / (b + 3)
        - a
        + c * b / (d + 3)
    )
    second_coefficient = sp.factor(
        -c * (c - 1) / (d + 3)
        + a * c * (d + 1) / ((b + 3) * (d + 3))
        + a * (a - 1) / (b + 3)
        - a * c * (b + 1) / ((b + 3) * (d + 3))
    )
    assert sp.factor(
        second_coefficient
        + coefficient * (a + c - 1) / (b + d + 3)
    ) == 0
    w_action = sp.factor(coefficient.subs({
        a: 4,
        b: 1,
    }))
    assert w_action == (
        (d + 4) * (c - d - 3) / (d + 3)
    )
    rows = []
    accumulated = sp.Integer(1)
    for depth in range(9):
        if depth:
            index = depth - 1
            accumulated *= sp.Rational(
                (index + 8) * (2 * index + 3),
                index + 7,
            )
        expected = (
            sp.Rational(depth + 7, 7)
            * sp.factorial2(2 * depth + 1)
        )
        assert sp.factor(accumulated - expected) == 0
        rows.append({
            "depth": depth,
            "coefficient": str(accumulated),
            "target_shell": f"Z_{5 + depth}",
        })
    return {
        "general_divergence_free_monomial_bracket_verified": True,
        "w4_action_coefficient": (
            "(b+4)*(a-b-3)/(b+3)"
        ),
        "iterated_z5_rows": rows,
        "all_checked_iterates_nonzero": True,
    }


def run() -> dict[str, object]:
    family = AFFINE._Family(4)
    base, directions = _carry_through_order_four(family)
    assert len(directions) == 6
    parameters = sp.symbols("lambda_1:7")
    _verify_contact_affine_family(family, base, directions)
    prefix = _symbolic_prefix(base, directions, parameters)

    source_velocity = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in prefix[1][order]
        )
        for order in range(5)
    ]
    ops = _formal_ops(
        source_velocity[0],
        lambda left, right: _source_bracket(
            left, right, family.v, family.t
        ),
    )
    logarithm = magnus_from_velocity(
        source_velocity,
        5,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        5,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert all(
        _equal(replay[order], source_velocity[order])
        for order in range(5)
    )

    adapted_v, adapted_g = sp.symbols("V G")
    substituted_first = sp.expand(logarithm[5][0].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }))
    substituted_second = sp.expand(logarithm[5][1].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }) - sp.Rational(3, 2) * substituted_first)
    shell = _degree_shell(
        (substituted_first, substituted_second),
        adapted_v,
        adapted_g,
        14,
    )
    equations = _shell_equations(
        shell, adapted_v, adapted_g
    )
    constant_equations = [
        equation
        for equation in equations
        if not equation.free_symbols.intersection(parameters)
    ]
    if constant_equations:
        outcome = {
            "kind": "affine_invariant_nonzero_shell",
            "nonzero_constant_coefficients": [
                str(value) for value in constant_equations
            ],
            "cancellation_impossible_over_every_field_of_characteristic_zero": (
                True
            ),
        }
    else:
        basis = sp.groebner(
            equations, *parameters, order="grevlex"
        )
        contains_one = any(
            polynomial.as_expr() == 1
            for polynomial in basis.polys
        )
        outcome = {
            "kind": (
                "groebner_inconsistent"
                if contains_one
                else "algebraic_residual"
            ),
            "groebner_contains_one": contains_one,
            "groebner_basis": [
                str(polynomial.as_expr())
                for polynomial in basis.polys
            ],
        }

    return {
        "schema": (
            "axiompack.jacobian_moving_cone_log_five_affine_escape.v1"
        ),
        "source_caps_orders_zero_to_four": [5, 5, 7, 9, 11],
        "complete_affine_dimension": len(directions),
        "symbolic_contact_replay": True,
        "right_multiply_forward_dexp_roundtrip": True,
        "degree_fourteen_shell": [
            str(sp.factor(component)) for component in shell
        ],
        "degree_fourteen_shell_sha256": [
            _sha(component) for component in shell
        ],
        "coefficient_equations": [
            str(sp.factor(equation)) for equation in equations
        ],
        "cancellation_outcome": outcome,
        "shell_lie_algebra": _bracket_algebra_receipt(),
        "claim_boundary": (
            "Complete affine minimum-cap prefix through log order five; "
            "no later-order or tail-minimax conclusion."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
