"""Exact normal form for formal weight-3/2 tensor densities.

For a tangent formal diffeomorphism ``phi``, the standard weight-3/2
pullback action is

    T_phi(k) = k(phi) / phi'**(3/2).

The row-indexed split residual used by the obstruction compiler is
``K=x*C``.  Its induced action has an additional ``x/phi`` factor.  Every
such residual ``K=c*x*v(x)`` with ``c != 0`` and ``v(0)=1`` is the pullback
of ``c*x`` by the unique normalized density clock whose derivative is
``v**(-2/3)``.

For a standalone simple-zero standard density, writing ``phi=x*w**3``
reduces its separate nonlinear orbit equation to

    w + 3*x*w' = v**(-2/3).

This module constructs the unique coefficientwise solution over ``Fraction``
and verifies the squared orbit identity

    K**2 * phi'**3 = c**2 * phi**2.

All lists contain ordinary coefficients and are truncated at the declared
maximum power of ``x``.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from ztare.common.formal_power_series import (
    Series,
    compose as _compose,
    derivative as _derivative,
    integral as _integral,
    multiply as _multiply,
    natural_power as _natural_power,
    rational_power_unit,
    truncate as _truncate,
)


def normalized_split_density_clock(
    unit: Iterable[Fraction],
    maximum_order: int,
) -> Series:
    """Return the zero-constant clock with derivative ``unit**(-2/3)``."""

    value = _truncate(unit, maximum_order)
    if value[0] != 1:
        raise ValueError("split-density clock requires a unit with constant one")
    derivative = rational_power_unit(
        value,
        Fraction(-2, 3),
        maximum_order,
    )
    return _integral(derivative, maximum_order)


def act_on_split_density_unit(
    unit: Iterable[Fraction],
    diffeomorphism: Iterable[Fraction],
    maximum_order: int,
) -> Series:
    """Apply the row-indexed weight-3/2 action to ``K/(c*x)``.

    If ``K=c*x*v`` and ``h`` is tangent to the identity, then
    ``T_h(K)/(c*x) = v(h)/(h')**(3/2)``.
    """

    value = _truncate(unit, maximum_order)
    endpoint = _truncate(diffeomorphism, maximum_order)
    if value[0] != 1:
        raise ValueError("split-density action requires a unit")
    if endpoint[0] != 0 or maximum_order < 1 or endpoint[1] != 1:
        raise ValueError("split-density action requires a tangent diffeomorphism")
    endpoint_derivative = _derivative(endpoint, maximum_order)
    derivative_weight = rational_power_unit(
        endpoint_derivative,
        Fraction(-3, 2),
        maximum_order,
    )
    return _multiply(
        _compose(value, endpoint, maximum_order),
        derivative_weight,
        maximum_order,
    )


@dataclass(frozen=True)
class SimpleZeroDensityNormalForm:
    """A content-bearing finite replay of the all-order normal-form formula."""

    maximum_order: int
    leading_coefficient: Fraction
    density: Series
    unit: Series
    negative_two_thirds_power: Series
    euler_solution: Series
    diffeomorphism: Series
    euler_residual: Series
    squared_orbit_residual: Series

    @property
    def verified(self) -> bool:
        return not any(self.euler_residual) and not any(
            self.squared_orbit_residual
        )


@dataclass(frozen=True)
class SplitTensorResidualNormalForm:
    """Normal form for the row-indexed residual ``K = x*C``.

    The standard weight-3/2 density is ``C``.  Consequently the induced
    action on ``K`` contains the extra factor ``x / phi``.
    """

    maximum_order: int
    leading_coefficient: Fraction
    residual: Series
    unit: Series
    negative_two_thirds_power: Series
    diffeomorphism: Series
    derivative_residual: Series
    squared_orbit_residual: Series

    @property
    def verified(self) -> bool:
        return not any(self.derivative_residual) and not any(
            self.squared_orbit_residual
        )


def normalize_simple_zero_density(
    density: Iterable[Fraction],
    maximum_order: int,
) -> SimpleZeroDensityNormalForm:
    """Conjugate a simple-zero weight-3/2 density to its leading monomial.

    The returned ``diffeomorphism`` is ``phi = x*w**3``.  Verification uses
    the polynomial identity ``K**2 * phi'**3 = c**2 * phi**2``, so no
    fractional power is trusted during replay.
    """

    if maximum_order < 1:
        raise ValueError("maximum_order must be at least one")
    coefficients = _truncate(density, maximum_order)
    if coefficients[0] != 0:
        raise ValueError("density must vanish at the origin")
    leading = coefficients[1]
    if not leading:
        raise ValueError("density must have a nonzero simple-zero coefficient")

    unit_order = maximum_order - 1
    unit = tuple(
        coefficients[order + 1] / leading
        for order in range(unit_order + 1)
    )
    negative_two_thirds = rational_power_unit(
        unit,
        Fraction(-2, 3),
        unit_order,
    )
    euler_solution = tuple(
        coefficient / Fraction(1 + 3 * order)
        for order, coefficient in enumerate(negative_two_thirds)
    )

    extended_w = _truncate(euler_solution, maximum_order)
    w_cubed = _natural_power(extended_w, 3, maximum_order)
    diffeomorphism = (Fraction(0),) + w_cubed[:maximum_order]

    derivative_w = _derivative(extended_w, maximum_order)
    euler_left = list(extended_w)
    for order in range(1, maximum_order + 1):
        euler_left[order] += 3 * derivative_w[order - 1]
    euler_right = _truncate(negative_two_thirds, maximum_order)
    euler_residual = tuple(
        euler_left[order] - euler_right[order]
        for order in range(maximum_order + 1)
    )

    phi_derivative = _derivative(diffeomorphism, maximum_order)
    left = _multiply(
        _natural_power(coefficients, 2, maximum_order),
        _natural_power(phi_derivative, 3, maximum_order),
        maximum_order,
    )
    right = tuple(
        leading**2 * coefficient
        for coefficient in _natural_power(
            diffeomorphism, 2, maximum_order
        )
    )
    squared_residual = tuple(
        left[order] - right[order]
        for order in range(maximum_order + 1)
    )
    certificate = SimpleZeroDensityNormalForm(
        maximum_order=maximum_order,
        leading_coefficient=leading,
        density=coefficients,
        unit=unit,
        negative_two_thirds_power=negative_two_thirds,
        euler_solution=euler_solution,
        diffeomorphism=diffeomorphism,
        euler_residual=euler_residual,
        squared_orbit_residual=squared_residual,
    )
    if not certificate.verified:
        raise AssertionError("tensor-density normal-form replay failed")
    return certificate


def normalize_split_tensor_residual(
    residual: Iterable[Fraction],
    maximum_order: int,
) -> SplitTensorResidualNormalForm:
    """Normalize ``K=x*C`` to its leading monomial under the split action.

    If ``K=c*x*v`` then the tangent diffeomorphism is defined by
    ``phi' = v**(-2/3)``.  The returned certificate checks this derivative
    equation and ``K**2 * phi'**3 = c**2 * x**2`` coefficientwise.
    """

    if maximum_order < 1:
        raise ValueError("maximum_order must be at least one")
    coefficients = _truncate(residual, maximum_order)
    if coefficients[0] != 0:
        raise ValueError("residual must vanish at the origin")
    leading = coefficients[1]
    if not leading:
        raise ValueError("residual must have a nonzero simple-zero coefficient")

    unit_order = maximum_order - 1
    unit = tuple(
        coefficients[order + 1] / leading
        for order in range(unit_order + 1)
    )
    negative_two_thirds = rational_power_unit(
        unit,
        Fraction(-2, 3),
        unit_order,
    )
    diffeomorphism = (Fraction(0),) + tuple(
        coefficient / Fraction(order + 1)
        for order, coefficient in enumerate(negative_two_thirds)
    )
    phi_derivative = _derivative(diffeomorphism, maximum_order)
    derivative_target = _truncate(negative_two_thirds, maximum_order)
    derivative_residual = tuple(
        phi_derivative[order] - derivative_target[order]
        for order in range(maximum_order + 1)
    )

    left = _multiply(
        _natural_power(coefficients, 2, maximum_order),
        _natural_power(phi_derivative, 3, maximum_order),
        maximum_order,
    )
    right = [Fraction(0) for _ in range(maximum_order + 1)]
    if maximum_order >= 2:
        right[2] = leading**2
    squared_residual = tuple(
        left[order] - right[order]
        for order in range(maximum_order + 1)
    )
    certificate = SplitTensorResidualNormalForm(
        maximum_order=maximum_order,
        leading_coefficient=leading,
        residual=coefficients,
        unit=unit,
        negative_two_thirds_power=negative_two_thirds,
        diffeomorphism=diffeomorphism,
        derivative_residual=derivative_residual,
        squared_orbit_residual=squared_residual,
    )
    if not certificate.verified:
        raise AssertionError("split tensor-residual normal-form replay failed")
    return certificate
