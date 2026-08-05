"""Formal Magnus, dexp, BCH, and split-factorization recursions.

The words "left" and "right" are easy to reverse when a group action is
composed on different sides.  ``VelocityPlacement`` therefore names the
matrix equation itself:

* ``LEFT_MULTIPLY``:  ``g' = velocity * g``;
* ``RIGHT_MULTIPLY``: ``g' = g * velocity``.

The implementation is substrate-neutral.  Callers supply the zero, addition,
rational scaling, and Lie-bracket operations for their coefficient type.
Series use ordinary coefficients: entry ``j`` multiplies ``s**j``.
The BCH and factorization functions require identity-tangent inputs: their
order-zero coefficients must vanish.  This makes every coefficient depend
on finitely many lower-order brackets.
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


def _series_add(
    left: list[Coefficient],
    right: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
) -> list[Coefficient]:
    return [
        ops.add(left[order], right[order])
        for order in range(maximum_order + 1)
    ]


def _adjoint_exponential(
    actor: list[Coefficient],
    value: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
    *,
    sign: int = 1,
) -> list[Coefficient]:
    """Return ``exp(sign * ad_actor)(value)`` through one series order."""

    if sign not in {-1, 1}:
        raise ValueError("adjoint sign must be -1 or 1")
    result = list(value[: maximum_order + 1])
    nested = list(value[: maximum_order + 1])
    for depth in range(1, maximum_order + 1):
        nested = _series_bracket(actor, nested, maximum_order, ops)
        result = _series_add(
            result,
            [
                ops.scale(
                    coefficient,
                    Fraction(sign**depth, factorial(depth)),
                )
                for coefficient in nested
            ],
            maximum_order,
            ops,
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


def bch_series(
    left: list[Coefficient],
    right: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
) -> list[Coefficient]:
    """Return ``log(exp(left) * exp(right))`` through ``s**n``.

    Both inputs must have zero order-zero coefficient.  The implementation
    uses left-multiplication velocities:

    ``V_product = V_left + exp(ad_left)(V_right)``.

    Reusing the typed dexp recursion keeps BCH orientation coupled to the
    displayed product equation.
    """

    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    if len(left) <= maximum_order or len(right) <= maximum_order:
        raise ValueError("both logarithms need coefficients through order n")
    left_velocity = velocity_from_magnus(
        left,
        maximum_order,
        ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    right_velocity = velocity_from_magnus(
        right,
        maximum_order,
        ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    transported_right = _adjoint_exponential(
        left,
        right_velocity,
        maximum_order,
        ops,
    )
    product_velocity = _series_add(
        left_velocity,
        transported_right,
        maximum_order,
        ops,
    )
    return magnus_from_velocity(
        product_velocity,
        maximum_order,
        ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )


def factor_magnus_by_projection(
    logarithm: list[Coefficient],
    maximum_order: int,
    ops: FormalLieOps[Coefficient],
    project_first_factor: Callable[[Coefficient], Coefficient],
) -> tuple[list[Coefficient], list[Coefficient]]:
    """Factor one logarithm as ``BCH(first, residual)`` recursively.

    ``project_first_factor`` declares a coefficient-space splitting.  At
    order ``n``, the BCH coefficient is ``first[n] + residual[n]`` plus a
    known expression in lower orders.  Projection therefore determines a
    unique pair coefficient by coefficient.  If the projection image is a
    Lie subalgebra, ``first`` is the logarithm of the corresponding formal
    subgroup factor.  No subalgebra or asymptotic-completeness claim is
    inferred by this substrate-neutral routine.
    """

    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    if len(logarithm) <= maximum_order:
        raise ValueError("logarithm needs coefficients through order n")
    first = [ops.zero() for _ in range(maximum_order + 1)]
    residual = [ops.zero() for _ in range(maximum_order + 1)]
    for order in range(1, maximum_order + 1):
        approximation = bch_series(first, residual, order, ops)
        missing = ops.add(
            logarithm[order],
            ops.scale(approximation[order], Fraction(-1)),
        )
        first[order] = project_first_factor(missing)
        residual[order] = ops.add(
            missing,
            ops.scale(first[order], Fraction(-1)),
        )
    return first, residual
