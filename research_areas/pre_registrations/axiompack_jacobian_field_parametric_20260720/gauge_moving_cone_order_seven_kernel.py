#!/usr/bin/env python3
"""Exact cap-17 affine kernel and complete-affine log-order-eight shell."""

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

import gauge_moving_cone_z_ray_affine_invariance as ZRAY  # noqa: E402
import gauge_moving_section_affine_extension as AFFINE  # noqa: E402
from gauge_controlled_global_magnus import (  # noqa: E402
    _bracket as _source_bracket,
)
from gauge_moving_lie_cone_magnus import (  # noqa: E402
    _degree,
    _equal,
    _formal_ops,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)
from ztare.common.exact_linear_system import (  # noqa: E402
    solve_affine,
)


Pair = tuple[sp.Expr, sp.Expr]
Prefix = tuple[dict[int, sp.Expr], dict[int, Pair]]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _decode_prefix(
    *,
    coordinates: sp.Matrix,
    metadata: list[dict[str, object]],
    lower_directions: list[Prefix],
    family: AFFINE._Family,
) -> Prefix:
    current_count = len(metadata)
    prefix: Prefix = ({}, {})
    for scalar, lower in zip(
        list(coordinates[current_count:, 0]),
        lower_directions,
        strict=True,
    ):
        AFFINE._add_scaled_prefix(prefix, lower, scalar)
    hamiltonian, source = AFFINE._decode(
        sp.Matrix(coordinates[:current_count, :]),
        metadata,
        family.v,
        family.t,
    )
    prefix[0][7] = hamiltonian
    prefix[1][7] = source
    return prefix


def _complete_prefix_data(
    *,
    prime: int,
) -> tuple[
    dict[str, object],
    AFFINE._Family,
    Prefix,
    list[Prefix],
    Prefix,
    list[Prefix],
]:
    family = AFFINE._Family(7)
    lower_base, lower_directions = ZRAY._carry(
        family, (5, 5, 7, 9, 11, 13, 14)
    )
    assert len(lower_directions) == 14
    residual = family.residual(7, lower_base)
    deltas = [
        family.delta_residual(7, direction)
        for direction in lower_directions
    ]
    matrix, rhs, _row_keys, metadata = AFFINE._joint_system(
        family=family,
        category="cone",
        order=7,
        source_cap=17,
        residual=residual,
        lower_deltas=deltas,
    )
    (
        affine_certificate,
        particular,
        kernel,
    ) = solve_affine(
        matrix, rhs, prime=prime
    )
    certificate = affine_certificate.to_dict()
    current_count = len(metadata)
    lower_projection = kernel[current_count:, :]
    lower_projection_rank = lower_projection.rank()
    assert lower_projection_rank == len(lower_directions)
    certificate["lower_projection_rank"] = lower_projection_rank
    certificate["all_lower_affine_freedom_extends"] = True

    selected_adjustment = _decode_prefix(
        coordinates=particular,
        metadata=metadata,
        lower_directions=lower_directions,
        family=family,
    )
    selected: Prefix = (
        dict(lower_base[0]),
        dict(lower_base[1]),
    )
    AFFINE._add_scaled_prefix(
        selected, selected_adjustment, sp.Integer(1)
    )

    outgoing = [
        _decode_prefix(
            coordinates=sp.Matrix(kernel[:, column]),
            metadata=metadata,
            lower_directions=lower_directions,
            family=family,
        )
        for column in range(kernel.shape[1])
    ]
    ZRAY._verify_affine_family(
        family, selected, outgoing, 7
    )
    assert max(
        _degree(direction[1].get(
            7, (sp.Integer(0), sp.Integer(0))
        ), family.v, family.t)
        for direction in outgoing
    ) <= 17
    assert _degree(
        selected[1][7], family.v, family.t
    ) <= 17
    certificate[
        "base_and_all_directions_contact_replayed"
    ] = True
    certificate[
        "all_order_seven_source_directions_degree_at_most_17"
    ] = True
    return (
        certificate,
        family,
        lower_base,
        lower_directions,
        selected,
        outgoing,
    )


def _complete_affine_order_eight_shell(
    family: AFFINE._Family,
    lower_base: Prefix,
    lower_directions: list[Prefix],
) -> dict[str, object]:
    parameters = sp.symbols(
        f"lambda_1:{len(lower_directions) + 1}"
    )
    prefix = ZRAY._symbolic_prefix(
        lower_base, lower_directions, parameters
    )
    source_velocity = [
        tuple(
            sp.expand(component / sp.factorial(order))
            for component in prefix[1][order]
        )
        for order in range(7)
    ]
    source_velocity.append(
        (sp.Integer(0), sp.Integer(0))
    )
    ops = _formal_ops(
        source_velocity[0],
        lambda left, right: _source_bracket(
            left, right, family.v, family.t
        ),
    )
    logarithm = magnus_from_velocity(
        source_velocity,
        8,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        8,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert all(
        _equal(replay[order], source_velocity[order])
        for order in range(8)
    )

    adapted_v, adapted_g = sp.symbols("V G")
    first = sp.expand(logarithm[8][0].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }))
    second = sp.expand(logarithm[8][1].subs({
        family.v: adapted_v,
        family.t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }) - sp.Rational(3, 2) * first)
    shell = ZRAY._degree_shell(
        (first, second), adapted_v, adapted_g, 26
    )
    scalar = sp.expand(
        sp.Poly(shell[0], adapted_v, adapted_g).coeff_monomial(
            adapted_v**19 * adapted_g**7
        )
    )
    expected_z = (
        adapted_v**19 * adapted_g**7,
        -sp.Rational(19, 10)
        * adapted_v**18 * adapted_g**8,
    )
    assert all(
        sp.expand(shell[index] - scalar * expected_z[index]) == 0
        for index in range(2)
    )
    assert not scalar.free_symbols.intersection(set(parameters))
    assert scalar == sp.Rational(5, 14_155_776)
    return {
        "lower_symbolic_parameter_count": len(parameters),
        "newest_velocity_enters_logarithm_linearly": True,
        "newest_velocity_degree_upper_bound": 17,
        "projected_shell_degree": 26,
        "newest_velocity_cannot_enter_projected_shell": True,
        "complete_shell": [
            str(sp.factor(component)) for component in shell
        ],
        "complete_shell_sha256": [
            _sha(component) for component in shell
        ],
        "z_8_scalar": str(scalar),
        "all_affine_parameters_absent": True,
        "projected_right_multiply_dexp_roundtrip": True,
    }


def run(prime: int = 1_000_003) -> dict[str, object]:
    (
        kernel_certificate,
        family,
        lower_base,
        lower_directions,
        _selected,
        outgoing,
    ) = _complete_prefix_data(prime=prime)
    shell = _complete_affine_order_eight_shell(
        family, lower_base, lower_directions
    )
    return {
        "schema": (
            "axiompack.jacobian_moving_cone_order_seven_kernel.v1"
        ),
        "kernel_certificate": kernel_certificate,
        "outgoing_affine_dimension": len(outgoing),
        "log_order_eight_shell": shell,
        "claim_boundary": (
            "Complete affine prefix through instantaneous order seven "
            "and logarithmic order eight only; no all-order recurrence "
            "or tail-minimax conclusion."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
