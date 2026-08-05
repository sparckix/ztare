from fractions import Fraction

import pytest

from ztare.common.formal_lie_series import (
    FormalLieOps,
    VelocityPlacement,
    bch_series,
    factor_magnus_by_projection,
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


def test_bch_series_uses_the_declared_product_order() -> None:
    ops = _ops()
    left: list[Pair] = [
        (Fraction(0), Fraction(0)),
        (Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0)),
    ]
    right: list[Pair] = [
        (Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1)),
        (Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0)),
    ]
    product = bch_series(left, right, 3, ops)
    assert product == [
        (Fraction(0), Fraction(0)),
        (Fraction(1), Fraction(1)),
        (Fraction(0), Fraction(1, 2)),
        (Fraction(0), Fraction(1, 12)),
    ]
    reversed_product = bch_series(right, left, 3, ops)
    assert reversed_product[2] == (Fraction(0), Fraction(-1, 2))


def test_projection_factorization_roundtrip() -> None:
    ops = _ops()
    logarithm: list[Pair] = [
        (Fraction(0), Fraction(0)),
        (Fraction(2), Fraction(3)),
        (Fraction(-1), Fraction(5)),
        (Fraction(4), Fraction(-2)),
        (Fraction(7), Fraction(11)),
    ]
    first, residual = factor_magnus_by_projection(
        logarithm,
        4,
        ops,
        lambda value: (value[0], Fraction(0)),
    )
    assert all(value[1] == 0 for value in first)
    assert all(value[0] == 0 for value in residual)
    assert bch_series(first, residual, 4, ops) == logarithm


def test_projection_factorization_validates_series_lengths() -> None:
    ops = _ops()
    with pytest.raises(ValueError, match="through order n"):
        factor_magnus_by_projection(
            [(Fraction(0), Fraction(0))],
            1,
            ops,
            lambda value: value,
        )
