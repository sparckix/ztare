#!/usr/bin/env python3
"""Exact order-seven extension of the moving cone affine carry.

Finite-field elimination selects pivot rows and columns only.  Every
consistency or inconsistency conclusion is replayed over the rationals
against the complete original system.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import sympy as sp
from sympy.polys.matrices import DomainMatrix


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
    _degree,
    _equal,
    _formal_ops,
    _sha,
    _target_bracket,
    _top_shell,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)
from ztare.common.exact_linear_system import (  # noqa: E402
    certify_inconsistent,
    solve_particular,
)


Pair = tuple[sp.Expr, sp.Expr]
Prefix = tuple[dict[int, sp.Expr], dict[int, Pair]]


def _inconsistency_certificate(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    *,
    prime: int,
) -> dict[str, object]:
    return certify_inconsistent(
        matrix, rhs, prime=prime
    ).to_dict()


def _consistency_certificate(
    matrix: DomainMatrix,
    rhs: DomainMatrix,
    *,
    prime: int,
) -> tuple[dict[str, object], sp.Matrix]:
    certificate, solution = solve_particular(
        matrix, rhs, prime=prime
    )
    return certificate.to_dict(), solution


def _carry_through_order_six(
    family: AFFINE._Family,
) -> tuple[Prefix, list[Prefix]]:
    caps = (5, 5, 7, 9, 11, 13, 14)
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


def _decode_order_seven_solution(
    *,
    solution: sp.Matrix,
    metadata: list[dict[str, object]],
    directions: list[Prefix],
    base: Prefix,
    family: AFFINE._Family,
) -> tuple[sp.Expr, Pair]:
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
    base[0][7] = hamiltonian
    base[1][7] = source
    return hamiltonian, source


def _magnus_extension(
    hamiltonians: dict[int, sp.Expr],
    sources: dict[int, Pair],
    family: AFFINE._Family,
) -> dict[str, object]:
    p, q = family.p, family.q
    v, t = family.v, family.t
    maximum_velocity_order = 7
    maximum_log_order = 8
    source_velocity = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in sources[order]
        )
        for order in range(maximum_velocity_order + 1)
    ]
    target_velocity = [
        sp.expand(hamiltonians[order] / sp.factorial(order))
        for order in range(maximum_velocity_order + 1)
    ]
    source_ops = _formal_ops(
        source_velocity[0],
        lambda left, right: _source_bracket(left, right, v, t),
    )
    target_ops = _formal_ops(
        target_velocity[0],
        lambda left, right: _target_bracket(
            left, right, p, q
        ),
    )
    source_log = magnus_from_velocity(
        source_velocity,
        maximum_log_order,
        source_ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    target_log = magnus_from_velocity(
        target_velocity,
        maximum_log_order,
        target_ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    source_replay = velocity_from_magnus(
        source_log,
        maximum_log_order,
        source_ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    target_replay = velocity_from_magnus(
        target_log,
        maximum_log_order,
        target_ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert all(
        _equal(source_replay[order], source_velocity[order])
        for order in range(maximum_velocity_order + 1)
    )
    assert all(
        _equal(target_replay[order], target_velocity[order])
        for order in range(maximum_velocity_order + 1)
    )
    source_top_degree = _degree(source_log[8], v, t)
    source_top = tuple(
        sp.expand(sum(
            coefficient * v**exponent[0] * t**exponent[1]
            for exponent, coefficient in sp.Poly(
                component, v, t
            ).terms()
            if sum(exponent) == source_top_degree
        ))
        for component in source_log[8]
    )
    adapted_v, adapted_g = sp.symbols("V G")
    adapted_first = sp.factor(
        source_top[0].subs({
            v: adapted_v,
            t: adapted_g + sp.Rational(3, 2) * adapted_v,
        })
    )
    adapted_second = sp.factor(
        source_top[1].subs({
            v: adapted_v,
            t: adapted_g + sp.Rational(3, 2) * adapted_v,
        })
        - sp.Rational(3, 2) * adapted_first
    )
    cusp_derivative = sp.factor(
        adapted_g * adapted_first
        + adapted_v * adapted_second
    )
    assert cusp_derivative == (
        -adapted_v**19 * adapted_g**8 / sp.Integer(3_145_728)
    )
    return {
        "source_degrees_orders_1_to_8": [
            _degree(source_log[order], v, t)
            for order in range(1, maximum_log_order + 1)
        ],
        "target_hamiltonian_degrees_orders_1_to_8": [
            _degree(target_log[order], p, q)
            for order in range(1, maximum_log_order + 1)
        ],
        "source_order_eight_top_shell": [
            str(component) for component in source_top
        ],
        "source_order_eight_sha256": _sha(source_log[8]),
        "source_order_eight_adapted_top_shell": [
            str(adapted_first),
            str(adapted_second),
        ],
        "source_order_eight_cusp_derivative": str(
            cusp_derivative
        ),
        "source_order_eight_top_shell_is_transverse": True,
        "target_order_eight_top_shell": _top_shell(
            target_log[8], p, q
        ),
        "mixed_orientation_forward_dexp_roundtrip": True,
    }


def run(prime: int = 1_000_003) -> dict[str, object]:
    family = AFFINE._Family(7)
    base, directions = _carry_through_order_six(family)
    residual = family.residual(7, base)
    deltas = [
        family.delta_residual(7, direction)
        for direction in directions
    ]

    failed_caps = {}
    for source_cap in (14, 15, 16):
        previous, previous_rhs, _keys, _metadata = AFFINE._joint_system(
            family=family,
            category="cone",
            order=7,
            source_cap=source_cap,
            residual=residual,
            lower_deltas=deltas,
        )
        failed_caps[str(source_cap)] = _inconsistency_certificate(
            previous,
            previous_rhs,
            prime=prime,
        )

    selected_cap = 17
    selected, selected_rhs, _keys, metadata = AFFINE._joint_system(
        family=family,
        category="cone",
        order=7,
        source_cap=selected_cap,
        residual=residual,
        lower_deltas=deltas,
    )
    selected_certificate, solution = _consistency_certificate(
        selected,
        selected_rhs,
        prime=prime,
    )
    hamiltonian, source = _decode_order_seven_solution(
        solution=solution,
        metadata=metadata,
        directions=directions,
        base=base,
        family=family,
    )
    return {
        "schema": (
            "axiompack.jacobian_moving_cone_order_seven_extension.v1"
        ),
        "instantaneous_order": 7,
        "natural_target_weight": 13,
        "lower_affine_dimension_in": len(directions),
        "failed_caps": failed_caps,
        "selected_cap_certificate": selected_certificate,
        "minimum_source_cap": selected_cap,
        "selected_target_hamiltonian": str(hamiltonian),
        "selected_target_hamiltonian_degree": _degree(
            hamiltonian, family.p, family.q
        ),
        "selected_source_degrees": [
            _degree(component, family.v, family.t)
            for component in source
        ],
        "magnus_extension": _magnus_extension(
            base[0],
            base[1],
            family,
        ),
        "claim_boundary": (
            "Exact order-seven minimum and one rational selected extension; "
            "the order-seven outgoing affine kernel is not classified."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=1_000_003)
    arguments = parser.parse_args()
    print(json.dumps(
        run(prime=arguments.prime),
        indent=2,
        sort_keys=True,
    ))
