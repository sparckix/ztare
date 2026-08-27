from fractions import Fraction

import pytest

from ztare.common.formal_power_series import (
    derivative,
    integral,
    iterative_logarithm,
    rational_power_unit,
    time_one_flow,
)


def test_zero_constant_integral_roundtrip() -> None:
    value = (Fraction(3), Fraction(-2), Fraction(5), Fraction(7))
    primitive = integral(value, 4)
    assert primitive[0] == 0
    assert derivative(primitive, 3) == value


def test_rational_power_unit_roundtrip() -> None:
    unit = (Fraction(1), Fraction(3), Fraction(-2), Fraction(5))
    cube_root = rational_power_unit(unit, Fraction(1, 3), 3)
    assert rational_power_unit(cube_root, Fraction(3), 3) == unit


def test_iterative_logarithm_roundtrip() -> None:
    generator = (
        Fraction(0),
        Fraction(0),
        Fraction(2),
        Fraction(-3),
        Fraction(5),
        Fraction(7),
    )
    endpoint = time_one_flow(generator, 5)
    certificate = iterative_logarithm(endpoint, 5)
    assert certificate.generator == generator
    assert certificate.replay == endpoint
    assert certificate.verified


@pytest.mark.parametrize(
    "endpoint",
    [
        (Fraction(1), Fraction(1)),
        (Fraction(0), Fraction(2)),
    ],
)
def test_iterative_logarithm_rejects_non_tangent_endpoint(
    endpoint: tuple[Fraction, ...],
) -> None:
    with pytest.raises(ValueError):
        iterative_logarithm(endpoint, 1)
