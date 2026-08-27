"""Exact truncated one-variable formal power-series operations over ``QQ``.

This module owns the small coefficient engine shared by formal-density and
formal-diffeomorphism replays.  A series is a tuple of ordinary coefficients;
every operation is truncated at an explicit maximum order.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import factorial
from typing import Iterable


Series = tuple[Fraction, ...]


def truncate(values: Iterable[Fraction], maximum_order: int) -> Series:
    if maximum_order < 0:
        raise ValueError("maximum_order must be nonnegative")
    result = tuple(Fraction(value) for value in values)
    if len(result) < maximum_order + 1:
        result += (Fraction(0),) * (maximum_order + 1 - len(result))
    return result[: maximum_order + 1]


def add(left: Series, right: Series, maximum_order: int) -> Series:
    left_value = truncate(left, maximum_order)
    right_value = truncate(right, maximum_order)
    return tuple(
        left_value[order] + right_value[order]
        for order in range(maximum_order + 1)
    )


def scale(value: Series, scalar: Fraction, maximum_order: int) -> Series:
    return tuple(
        Fraction(scalar) * coefficient
        for coefficient in truncate(value, maximum_order)
    )


def multiply(left: Series, right: Series, maximum_order: int) -> Series:
    result = [Fraction(0) for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(left[: maximum_order + 1]):
        if not left_value:
            continue
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            if right_value:
                result[left_order + right_order] += left_value * right_value
    return tuple(result)


def natural_power(value: Series, exponent: int, maximum_order: int) -> Series:
    if exponent < 0:
        raise ValueError("natural_power requires a nonnegative exponent")
    result = (Fraction(1),) + (Fraction(0),) * maximum_order
    for _ in range(exponent):
        result = multiply(result, value, maximum_order)
    return result


def derivative(value: Series, maximum_order: int) -> Series:
    return tuple(
        Fraction(order + 1) * (
            value[order + 1] if order + 1 < len(value) else Fraction(0)
        )
        for order in range(maximum_order + 1)
    )


def integral(value: Series, maximum_order: int) -> Series:
    """Return the zero-constant formal antiderivative."""

    coefficients = truncate(value, maximum_order)
    return (Fraction(0),) + tuple(
        coefficients[order] / Fraction(order + 1)
        for order in range(maximum_order)
    )


def compose(outer: Series, inner: Series, maximum_order: int) -> Series:
    """Return ``outer(inner(x))`` through ``maximum_order``."""

    result = (Fraction(0),) * (maximum_order + 1)
    power = (Fraction(1),) + (Fraction(0),) * maximum_order
    for coefficient in truncate(outer, maximum_order):
        result = add(result, scale(power, coefficient, maximum_order), maximum_order)
        power = multiply(power, inner, maximum_order)
    return result


def rational_power_unit(
    unit: Iterable[Fraction],
    exponent: Fraction,
    maximum_order: int,
) -> Series:
    """Return a rational power of a unit series through ``maximum_order``.

    The recurrence comes from
    ``unit * result' = exponent * unit' * result``.
    """

    value = truncate(unit, maximum_order)
    if value[0] != 1:
        raise ValueError("rational power requires constant coefficient one")
    result = [Fraction(0) for _ in range(maximum_order + 1)]
    result[0] = Fraction(1)
    for order in range(1, maximum_order + 1):
        right = sum(
            Fraction(exponent)
            * Fraction(index)
            * value[index]
            * result[order - index]
            for index in range(1, order + 1)
        )
        left_known = sum(
            value[index]
            * Fraction(order - index)
            * result[order - index]
            for index in range(1, order)
        )
        result[order] = (right - left_known) / Fraction(order)
    return tuple(result)


def time_one_flow(vector_field: Series, maximum_order: int) -> Series:
    """Return ``exp(vector_field*d/dx)(x)`` through one spatial order."""

    field = truncate(vector_field, maximum_order)
    if field[0] != 0 or (maximum_order >= 1 and field[1] != 0):
        raise ValueError("vector field must vanish to order at least two")
    coordinate = [Fraction(0) for _ in range(maximum_order + 1)]
    if maximum_order >= 1:
        coordinate[1] = Fraction(1)
    result = tuple(coordinate)
    iterated = tuple(coordinate)
    for depth in range(1, maximum_order):
        iterated = multiply(
            field,
            derivative(iterated, maximum_order),
            maximum_order,
        )
        result = add(
            result,
            scale(iterated, Fraction(1, factorial(depth)), maximum_order),
            maximum_order,
        )
    return result


@dataclass(frozen=True)
class IterativeLogarithmCertificate:
    maximum_order: int
    endpoint: Series
    generator: Series
    replay: Series
    residual: Series

    @property
    def verified(self) -> bool:
        return not any(self.residual)

    @property
    def last_nonzero_generator_order(self) -> int | None:
        support = [
            order for order, coefficient in enumerate(self.generator)
            if coefficient
        ]
        return max(support) if support else None


def iterative_logarithm(
    endpoint: Iterable[Fraction],
    maximum_order: int,
) -> IterativeLogarithmCertificate:
    """Recover the unique tangent vector field whose time-one map is given.

    At spatial order ``n``, the time-one coefficient is the new generator
    coefficient plus a polynomial in lower generator coefficients.  The
    recursion therefore solves one exact rational coefficient at a time.
    """

    value = truncate(endpoint, maximum_order)
    if value[0] != 0:
        raise ValueError("endpoint must fix the origin")
    if maximum_order < 1 or value[1] != 1:
        raise ValueError("endpoint must be tangent to the identity")
    generator = [Fraction(0) for _ in range(maximum_order + 1)]
    for order in range(2, maximum_order + 1):
        lower_flow = time_one_flow(tuple(generator), maximum_order)
        generator[order] = value[order] - lower_flow[order]
    replay = time_one_flow(tuple(generator), maximum_order)
    residual = tuple(
        replay[order] - value[order]
        for order in range(maximum_order + 1)
    )
    certificate = IterativeLogarithmCertificate(
        maximum_order=maximum_order,
        endpoint=value,
        generator=tuple(generator),
        replay=replay,
        residual=residual,
    )
    if not certificate.verified:
        raise AssertionError("iterative-logarithm round trip failed")
    return certificate
