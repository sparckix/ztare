"""Formal Magnus/dexp recursions with an equation-typed velocity side.

The words "left" and "right" are easy to reverse when a group action is
composed on different sides.  ``VelocityPlacement`` therefore names the
matrix equation itself:

* ``LEFT_MULTIPLY``:  ``g' = velocity * g``;
* ``RIGHT_MULTIPLY``: ``g' = g * velocity``.

The implementation is substrate-neutral.  Callers supply the zero, addition,
rational scaling, and Lie-bracket operations for their coefficient type.
Series use ordinary coefficients: entry ``j`` multiplies ``s**j``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from math import comb, factorial
from typing import Callable, Generic, TypeVar


Coefficient = TypeVar("Coefficient")


class VelocityPlacement(str, Enum):
    """The side on which the instantaneous velocity multiplies the flow."""

    LEFT_MULTIPLY = "g_prime_eq_velocity_times_g"
    RIGHT_MULTIPLY = "g_prime_eq_g_times_velocity"


@dataclass(frozen=True)
class FormalLieOps(Generic[Coefficient]):
    """Operations required by the formal Lie-series recursion."""

    zero: Callable[[], Coefficient]
    add: Callable[[Coefficient, Coefficient], Coefficient]
    scale: Callable[[Coefficient, Fraction], Coefficient]
    bracket: Callable[[Coefficient, Coefficient], Coefficient]


def _bernoulli_numbers(maximum_order: int) -> list[Fraction]:
    """Return B_0..B_n with the convention B_1 = -1/2."""

    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    values = [Fraction(1)]
    for order in range(1, maximum_order + 1):
        numerator = sum(
            Fraction(comb(order + 1, index)) * values[index]
            for index in range(order)
        )
        values.append(-numerator / Fraction(order + 1))
    return values


def inverse_dexp_coefficients(
    maximum_depth: int,
    placement: VelocityPlacement,
) -> tuple[Fraction, ...]:
    """Coefficients of ``dexp^{-1}`` for the declared flow equation."""

    bernoulli = _bernoulli_numbers(maximum_depth)
    coefficients = []
    for depth, value in enumerate(bernoulli):
        coefficient = value / Fraction(factorial(depth))
        if (
            placement is VelocityPlacement.RIGHT_MULTIPLY
            and depth % 2 == 1
        ):
            coefficient = -coefficient
        coefficients.append(coefficient)
    return tuple(coefficients)


def forward_dexp_coefficients(
    maximum_depth: int,
    placement: VelocityPlacement,
) -> tuple[Fraction, ...]:
    """Coefficients of ``dexp`` for the declared flow equation."""

    if maximum_depth < 0:
        raise ValueError("maximum_depth must be nonnegative")
    return tuple(
        Fraction(
            -1
            if (
                placement is VelocityPlacement.RIGHT_MULTIPLY
                and depth % 2 == 1
            )
            else 1,
            factorial(depth + 1),
        )
        for depth in range(maximum_depth + 1)
    )


def _series_bracket(
    left: list[Coefficient],
    right: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
) -> list[Coefficient]:
    result = [ops.zero() for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            order = left_order + right_order
            result[order] = ops.add(
                result[order],
                ops.bracket(left_value, right_value),
            )
    return result


def magnus_from_velocity(
    velocity: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
    placement: VelocityPlacement,
) -> list[Coefficient]:
    """Recover ``log(g)`` from the velocity in the declared equation."""

    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    if len(velocity) < maximum_order:
        raise ValueError("velocity needs coefficients through order n-1")
    inverse = inverse_dexp_coefficients(maximum_order, placement)
    logarithm = [ops.zero() for _ in range(maximum_order + 1)]
    for derivative_order in range(maximum_order):
        result = velocity[derivative_order]
        nested = velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _series_bracket(
                prefix,
                nested,
                derivative_order,
                ops,
            )
            if inverse[depth]:
                result = ops.add(
                    result,
                    ops.scale(nested[derivative_order], inverse[depth]),
                )
        logarithm[derivative_order + 1] = ops.scale(
            result,
            Fraction(1, derivative_order + 1),
        )
    return logarithm


def velocity_from_magnus(
    logarithm: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
    placement: VelocityPlacement,
) -> list[Coefficient]:
    """Apply ``dexp`` to ``log(g)`` and recover the velocity series."""

    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    if len(logarithm) <= maximum_order:
        raise ValueError("logarithm needs coefficients through order n")
    derivative = [
        ops.scale(logarithm[order + 1], Fraction(order + 1))
        for order in range(maximum_order)
    ]
    derivative.append(ops.zero())
    result = list(derivative)
    nested = derivative
    forward = forward_dexp_coefficients(maximum_order, placement)
    for depth in range(1, maximum_order + 1):
        nested = _series_bracket(
            logarithm,
            nested,
            maximum_order,
            ops,
        )
        for order in range(maximum_order):
            result[order] = ops.add(
                result[order],
                ops.scale(nested[order], forward[depth]),
            )
    return result
