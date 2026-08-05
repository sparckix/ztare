#!/usr/bin/env python3
"""Exact complete-affine tests for the next two transverse Z shells."""

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


def _carry(
    family: AFFINE._Family,
    caps: tuple[int, ...],
) -> tuple[Prefix, list[Prefix]]:
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


def _current_image(
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


def _verify_affine_family(
    family: AFFINE._Family,
    base: Prefix,
    directions: list[Prefix],
    maximum_order: int,
) -> None:
    zero_pair = (sp.Integer(0), sp.Integer(0))
    for order in range(maximum_order + 1):
        base_image = _current_image(family, base, order)
        residual = family.residual(order, base)
        assert all(
            sp.expand(base_image[index] - residual[index]) == 0
            for index in range(2)
        )
        source = base[1][order]
        assert sp.expand(
            sp.diff(family.gamma**2 * source[0], family.v)
            + sp.diff(family.gamma**2 * source[1], family.t)
        ) == 0
        for direction in directions:
            direction_image = _current_image(
                family, direction, order
            )
            delta = family.delta_residual(order, direction)
            assert all(
                sp.expand(
                    direction_image[index] - delta[index]
                ) == 0
                for index in range(2)
            )
            direction_source = direction[1].get(order, zero_pair)
            assert sp.expand(
                sp.diff(
                    family.gamma**2 * direction_source[0],
                    family.v,
                )
                + sp.diff(
                    family.gamma**2 * direction_source[1],
                    family.t,
                )
            ) == 0


def _symbolic_prefix(
    base: Prefix,
    directions: list[Prefix],
    parameters: tuple[sp.Symbol, ...],
) -> Prefix:
    prefix: Prefix = (dict(base[0]), dict(base[1]))
    for parameter, direction in zip(
        parameters, directions, strict=True
    ):
        AFFINE._add_scaled_prefix(prefix, direction, parameter)
    return prefix


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


def _case(
    *,
    caps: tuple[int, ...],
    expected_dimension: int,
) -> dict[str, object]:
    maximum_order = len(caps) - 1
    log_order = maximum_order + 1
    shell_degree = 4 * log_order - 6
    family = AFFINE._Family(maximum_order)
    base, directions = _carry(family, caps)
    assert len(directions) == expected_dimension
    _verify_affine_family(
        family, base, directions, maximum_order
    )
    parameters = sp.symbols(
        f"lambda_1:{len(directions) + 1}"
    )
    prefix = _symbolic_prefix(base, directions, parameters)
    source_velocity = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in prefix[1][order]
        )
        for order in range(maximum_order + 1)
    ]
    ops = _formal_ops(
        source_velocity[0],
        lambda left, right: _source_bracket(
            left, right, family.v, family.t
        ),
    )
    logarithm = magnus_from_velocity(
        source_velocity,
        log_order,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        log_order,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert all(
        _equal(replay[order], source_velocity[order])
        for order in range(maximum_order + 1)
    )

    adapted_v, adapted_g = sp.symbols("V G")
    first = sp.expand(logarithm[log_order][0].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }))
    second = sp.expand(logarithm[log_order][1].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }) - sp.Rational(3, 2) * first)
    shell = _degree_shell(
        (first, second),
        adapted_v,
        adapted_g,
        shell_degree,
    )

    first_exponent = (3 * log_order - 5, log_order - 1)
    scalar = sp.expand(
        sp.Poly(shell[0], adapted_v, adapted_g).coeff_monomial(
            adapted_v**first_exponent[0]
            * adapted_g**first_exponent[1]
        )
    )
    z_shell = (
        adapted_v**first_exponent[0]
        * adapted_g**first_exponent[1],
        -sp.Rational(
            first_exponent[0],
            log_order + 2,
        )
        * adapted_v**(first_exponent[0] - 1)
        * adapted_g**log_order,
    )
    z_residual = tuple(
        sp.expand(shell[index] - scalar * z_shell[index])
        for index in range(2)
    )
    parameter_symbols = set(parameters)
    parameter_free = (
        not scalar.free_symbols.intersection(parameter_symbols)
        and all(value == 0 for value in z_residual)
    )
    assert parameter_free
    assert scalar != 0
    return {
        "instantaneous_orders": [0, maximum_order],
        "source_caps": list(caps),
        "complete_affine_dimension": len(directions),
        "logarithmic_order": log_order,
        "shell_degree": shell_degree,
        "complete_shell": [
            str(sp.factor(component)) for component in shell
        ],
        "complete_shell_sha256": [
            _sha(component) for component in shell
        ],
        "z_shell_scalar": str(scalar),
        "all_affine_parameters_absent": True,
        "nonzero": True,
        "contact_base_and_directions_replayed": True,
        "right_multiply_forward_dexp_roundtrip": True,
    }


def run() -> dict[str, object]:
    cases = [
        _case(
            caps=(5, 5, 7, 9, 11, 13),
            expected_dimension=10,
        ),
        _case(
            caps=(5, 5, 7, 9, 11, 13, 14),
            expected_dimension=14,
        ),
    ]
    return {
        "schema": (
            "axiompack.jacobian_moving_cone_z_ray_affine_invariance.v1"
        ),
        "cases": cases,
        "all_successive_shells_complete_affine_invariant": True,
        "claim_boundary": (
            "Exact through logarithmic order seven only; no all-order "
            "coefficient survival or tail-minimax conclusion."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
