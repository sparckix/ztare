from fractions import Fraction

import pytest

from ztare.common.formal_lie_series import (
    FormalLieOps,
    VelocityPlacement,
    forward_dexp_coefficients,
    inverse_dexp_coefficients,
    magnus_from_velocity,
    velocity_from_magnus,
)


Pair = tuple[Fraction, Fraction]


def _ops() -> FormalLieOps[Pair]:
    # Upper-triangular matrices [[a,b],[0,0]].
    return FormalLieOps(
        zero=lambda: (Fraction(0), Fraction(0)),
        add=lambda left, right: (
            left[0] + right[0],
            left[1] + right[1],
        ),
        scale=lambda value, scalar: (
            scalar * value[0],
            scalar * value[1],
        ),
        bracket=lambda left, right: (
            Fraction(0),
            left[0] * right[1] - right[0] * left[1],
        ),
    )


def test_dexp_orientation_is_bound_to_the_flow_equation() -> None:
    left_inverse = inverse_dexp_coefficients(
        4, VelocityPlacement.LEFT_MULTIPLY
    )
    right_inverse = inverse_dexp_coefficients(
        4, VelocityPlacement.RIGHT_MULTIPLY
    )
    assert left_inverse[:3] == (
        Fraction(1),
        Fraction(-1, 2),
        Fraction(1, 12),
    )
    assert right_inverse[:3] == (
        Fraction(1),
        Fraction(1, 2),
        Fraction(1, 12),
    )
    assert forward_dexp_coefficients(
        2, VelocityPlacement.LEFT_MULTIPLY
    ) == (Fraction(1), Fraction(1, 2), Fraction(1, 6))
    assert forward_dexp_coefficients(
        2, VelocityPlacement.RIGHT_MULTIPLY
    ) == (Fraction(1), Fraction(-1, 2), Fraction(1, 6))


@pytest.mark.parametrize("placement", list(VelocityPlacement))
def test_magnus_dexp_roundtrip(placement: VelocityPlacement) -> None:
    ops = _ops()
    velocity: list[Pair] = [
        (Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(1)),
        (Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0)),
    ]
    logarithm = magnus_from_velocity(
        velocity, 4, ops, placement
    )
    replay = velocity_from_magnus(logarithm, 4, ops, placement)
    assert replay[:4] == velocity


def test_opposite_flow_equations_flip_the_first_bracket_shell() -> None:
    ops = _ops()
    velocity: list[Pair] = [
        (Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(1)),
        (Fraction(0), Fraction(0)),
    ]
    left = magnus_from_velocity(
        velocity, 3, ops, VelocityPlacement.LEFT_MULTIPLY
    )
    right = magnus_from_velocity(
        velocity, 3, ops, VelocityPlacement.RIGHT_MULTIPLY
    )
    assert left[1:3] == right[1:3]
    assert left[3] == (Fraction(0), Fraction(-1, 12))
    assert right[3] == (Fraction(0), Fraction(1, 12))
