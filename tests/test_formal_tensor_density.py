from fractions import Fraction

import pytest

from ztare.common.formal_tensor_density import (
    act_on_split_density_unit,
    normalize_simple_zero_density,
    normalize_split_tensor_residual,
    normalized_split_density_clock,
    rational_power_unit,
)
from ztare.common.formal_power_series import compose


def test_rational_power_unit_cubes_back_for_one_third() -> None:
    unit = (Fraction(1), Fraction(3), Fraction(-2), Fraction(5))
    root = rational_power_unit(unit, Fraction(1, 3), 3)
    certificate = normalize_simple_zero_density(
        (Fraction(0), Fraction(2), Fraction(6), Fraction(-4), Fraction(10)),
        4,
    )
    assert root[0] == 1
    assert certificate.verified


def test_july_critical_split_residual_normalizes_to_linear_monomial() -> None:
    density = (
        Fraction(0),
        Fraction(-1, 144),
        Fraction(-1, 576),
        Fraction(-1, 4608),
        Fraction(-5, 193536),
        Fraction(-109, 83607552),
        Fraction(3065, 2731180032),
    )
    certificate = normalize_split_tensor_residual(density, 6)
    assert certificate.leading_coefficient == Fraction(-1, 144)
    assert certificate.diffeomorphism[0:2] == (Fraction(0), Fraction(1))
    assert certificate.verified


def test_split_residual_alien_unit_replays() -> None:
    certificate = normalize_split_tensor_residual(
        (Fraction(0), Fraction(5), Fraction(-7), Fraction(11), Fraction(3)),
        4,
    )
    assert certificate.diffeomorphism[1] == 1
    assert certificate.verified


def test_split_density_clock_converts_action_to_composition() -> None:
    maximum_order = 6
    unit = (
        Fraction(1),
        Fraction(2),
        Fraction(-3),
        Fraction(5),
        Fraction(7),
        Fraction(-11),
        Fraction(13),
    )
    endpoint = (
        Fraction(0),
        Fraction(1),
        Fraction(3),
        Fraction(-2),
        Fraction(1),
        Fraction(4),
        Fraction(-5),
    )
    transformed = act_on_split_density_unit(
        unit, endpoint, maximum_order
    )
    transformed_clock = normalized_split_density_clock(
        transformed, maximum_order
    )
    original_clock = normalized_split_density_clock(unit, maximum_order)
    assert transformed_clock == compose(
        original_clock, endpoint, maximum_order
    )


@pytest.mark.parametrize(
    "density",
    [
        (Fraction(1), Fraction(1)),
        (Fraction(0), Fraction(0), Fraction(1)),
    ],
)
def test_normalizer_rejects_non_simple_zero(density: tuple[Fraction, ...]) -> None:
    with pytest.raises(ValueError):
        normalize_simple_zero_density(density, len(density) - 1)


def test_normalizer_requires_positive_truncation_order() -> None:
    with pytest.raises(ValueError):
        normalize_simple_zero_density((Fraction(0), Fraction(1)), 0)
