#!/usr/bin/env python3
"""Exact count-algebra replay of the alternating-cubic target quotient.

The target cancellation ``K_s - s*Q**3/56`` has zero-grade velocity

    alpha * P**3 + beta * s * Q**3.

Every Lie word with ``x`` copies of ``P**3`` and ``y`` copies of ``Q**3``
is a scalar multiple of

    E_(x,y) = P**(2*x-y+1) * Q**(2*y-x+1).

This script computes the universal coefficients with ``alpha=beta=1``.
The physical coefficient on the distinguished ray is then
``alpha**(2*m) * beta**(m+1)`` times the reported value.
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


Count: TypeAlias = tuple[int, int]
CountSeries: TypeAlias = dict[Count, Fraction]


def _exponent(count: Count) -> tuple[int, int]:
    x_count, y_count = count
    return (
        2 * x_count - y_count + 1,
        2 * y_count - x_count + 1,
    )


def _add(left: CountSeries, right: CountSeries) -> CountSeries:
    result = dict(left)
    for count, coefficient in right.items():
        result[count] = result.get(count, Fraction(0)) + coefficient
        if not result[count]:
            del result[count]
    return result


def _scale(value: CountSeries, scalar: Fraction) -> CountSeries:
    return {
        count: scalar * coefficient
        for count, coefficient in value.items()
        if scalar * coefficient
    }


def _bracket(left: CountSeries, right: CountSeries) -> CountSeries:
    result: CountSeries = {}
    for (x_count, y_count), left_coefficient in left.items():
        for (w_count, u_count), right_coefficient in right.items():
            multiplier = 3 * (
                y_count * w_count
                - x_count * u_count
                + y_count
                - x_count
                + w_count
                - u_count
            )
            if not multiplier:
                continue
            count = (
                x_count + w_count,
                y_count + u_count,
            )
            assert min(_exponent(count)) >= 0
            result[count] = (
                result.get(count, Fraction(0))
                + multiplier * left_coefficient * right_coefficient
            )
    return {
        count: coefficient
        for count, coefficient in result.items()
        if coefficient
    }


def _small_holonomic_candidates(
    sequence: list[Fraction],
    discovery_terms: int,
) -> list[dict[str, object]]:
    """Find and held-out check small polynomial-coefficient recurrences."""

    if not 8 <= discovery_terms < len(sequence):
        raise ValueError("need both a discovery range and a held-out suffix")
    candidates = []
    for order in range(1, 5):
        for degree in range(4):
            column_count = (order + 1) * (degree + 1)
            row_count = discovery_terms - order
            if row_count < column_count - 1:
                continue
            rows = []
            for index in range(row_count):
                rows.append([
                    sp.Rational(
                        sequence[index + shift].numerator,
                        sequence[index + shift].denominator,
                    )
                    * index**power
                    for shift in range(order + 1)
                    for power in range(degree + 1)
                ])
            kernel = sp.Matrix(rows).nullspace()
            if len(kernel) != 1:
                continue
            vector = kernel[0]
            held_out_matches = True
            for index in range(
                discovery_terms - order,
                len(sequence) - order,
            ):
                residual = sum(
                    vector[
                        shift * (degree + 1) + power
                    ]
                    * index**power
                    * sp.Rational(
                        sequence[index + shift].numerator,
                        sequence[index + shift].denominator,
                    )
                    for shift in range(order + 1)
                    for power in range(degree + 1)
                )
                if sp.factor(residual) != 0:
                    held_out_matches = False
                    break
            if held_out_matches:
                candidates.append({
                    "order": order,
                    "polynomial_degree": degree,
                    "coefficients_by_shift_then_power": [
                        str(sp.factor(entry))
                        for entry in vector
                    ],
                })
    return candidates


def run(
    maximum_m: int = 16,
    discovery_terms: int = 12,
) -> dict[str, object]:
    if maximum_m < 12:
        raise ValueError("replay needs a held-out suffix beyond m=11")
    maximum_order = 4 * maximum_m + 2
    velocity: list[CountSeries] = [
        {} for _ in range(maximum_order)
    ]
    velocity[0] = {(1, 0): Fraction(1)}
    velocity[1] = {(0, 1): Fraction(1)}
    ops = FormalLieOps[CountSeries](
        zero=dict,
        add=_add,
        scale=_scale,
        bracket=_bracket,
    )
    logarithm = magnus_from_velocity(
        velocity,
        maximum_order,
        ops,
        VelocityPlacement.LEFT_MULTIPLY,
    )

    rows = []
    sequence = []
    for m_value in range(maximum_m + 1):
        order = 4 * m_value + 2
        count = (2 * m_value, m_value + 1)
        exponent = _exponent(count)
        assert exponent == (3 * m_value, 3)
        coefficient = logarithm[order].get(
            count, Fraction(0)
        )
        sequence.append(coefficient)
        rows.append({
            "m": m_value,
            "logarithmic_order": order,
            "count": list(count),
            "hamiltonian_exponent": list(exponent),
            "universal_coefficient": str(coefficient),
            "nonzero": coefficient != 0,
        })

    candidates = _small_holonomic_candidates(
        sequence, discovery_terms
    )
    return {
        "schema": "axiompack.jacobian_q3_target_top_quotient.v1",
        "flow_equation": "A_prime = velocity * A",
        "velocity_placement": (
            VelocityPlacement.LEFT_MULTIPLY.value
        ),
        "zero_grade_velocity": "alpha*P^3 + beta*s*Q^3",
        "physical_amplitudes": {
            "alpha": "-1/36",
            "beta": "-1/56",
        },
        "distinguished_ray": {
            "hamiltonian": "W_m=P^(3*m)*Q^3",
            "logarithmic_order": "4*m+2",
            "target_derivation_degree": "3*m+2",
            "amplitude_factor": "alpha^(2*m)*beta^(m+1)",
        },
        "rows": rows,
        "all_checked_nonzero": all(sequence),
        "discovery_terms": discovery_terms,
        "held_out_terms": len(sequence) - discovery_terms,
        "small_holonomic_candidates": candidates,
        "claim_boundary": (
            "Exact finite replay in the complete zero-grade target "
            "quotient. A nonzero prefix and failure of the declared small "
            "recurrence search do not prove all-order nonvanishing."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
