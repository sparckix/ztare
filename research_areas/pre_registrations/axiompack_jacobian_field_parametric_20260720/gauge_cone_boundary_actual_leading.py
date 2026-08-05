#!/usr/bin/env python3
"""Discover and hold out the actual exceptional d=0 leading module.

The earlier boundary argument prescribed the even key ``(S+1-2*a, 2*m)``.
The full residual falsified that prescription.  This replay instead extracts
the maximum-radial cost-four row first, fits its key and normalized amplitude
at three contact depths of the required parity, and reserves the fourth depth
as an exact held-out check.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_boundary_contact_classes import (  # noqa: E402
    EXCEPTIONAL_D_ZERO_STATES,
    M_SYMBOL,
    NumericSourcePullback,
    _case,
    _fixed_target_coefficients,
    _leading_scale,
)


def _quadratic_fit(
    depths: tuple[int, int, int],
    values: tuple[sp.Expr, sp.Expr, sp.Expr],
) -> sp.Expr:
    basis = (sp.Integer(1), M_SYMBOL, M_SYMBOL**2)
    matrix = sp.Matrix([
        [term.subs(M_SYMBOL, depth) for term in basis]
        for depth in depths
    ])
    assert matrix.det() != 0
    coefficients = tuple(matrix.inv() * sp.Matrix(values))
    return sp.factor(sum(
        coefficient * term
        for coefficient, term in zip(coefficients, basis, strict=True)
    ))


def run() -> dict[str, object]:
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    rows = []
    for a, slack in sorted(EXCEPTIONAL_D_ZERO_STATES):
        required_parity = (a + slack) % 2
        first_depth = 2 if required_parity == 0 else 1
        depths = tuple(first_depth + 2 * index for index in range(4))
        observations = []
        for contact_depth in depths:
            numerator = a + 3 * contact_depth + slack
            assert numerator % 2 == 0
            q_exponent = numerator // 2
            source_slope = (
                2 * a + 3 * q_exponent + 2 * contact_depth
            )
            _, result = _case(
                a,
                slack,
                0,
                contact_depth,
                pullback,
                background,
                include_full_residual=True,
            )
            leading = result["cost_four_leading_rows"]
            assert len(leading) == 1, (
                "leading boundary module is not rank one",
                a,
                slack,
                contact_depth,
                leading,
            )
            radial, normal = leading[0]["key_r_normal"]
            coefficient = sp.Rational(leading[0]["coefficient"])
            normalized = sp.factor(
                coefficient
                / _leading_scale(
                    a,
                    q_exponent,
                    0,
                    contact_depth,
                )
            )
            observations.append({
                "m": contact_depth,
                "q_exponent": q_exponent,
                "source_slope": source_slope,
                "leading_key_r_normal": [radial, normal],
                "radial_offset_from_S": radial - source_slope,
                "normal_offset_from_2m": normal - 2 * contact_depth,
                "coefficient": str(coefficient),
                "normalized_coefficient": str(normalized),
                "_normalized": normalized,
            })

        determining = observations[:3]
        held_out = observations[3]
        fit_depths = tuple(row["m"] for row in determining)
        radial_fit = _quadratic_fit(
            fit_depths,
            tuple(sp.Integer(row["radial_offset_from_S"])
                  for row in determining),
        )
        normal_fit = _quadratic_fit(
            fit_depths,
            tuple(sp.Integer(row["normal_offset_from_2m"])
                  for row in determining),
        )
        amplitude_fit = _quadratic_fit(
            fit_depths,
            tuple(row["_normalized"] for row in determining),
        )
        held_depth = held_out["m"]
        radial_heldout_agrees = (
            radial_fit.subs(M_SYMBOL, held_depth)
            == held_out["radial_offset_from_S"]
        )
        normal_heldout_agrees = (
            normal_fit.subs(M_SYMBOL, held_depth)
            == held_out["normal_offset_from_2m"]
        )
        amplitude_prediction = sp.factor(
            amplitude_fit.subs(M_SYMBOL, held_depth)
        )
        amplitude_heldout_agrees = (
            amplitude_prediction == held_out["_normalized"]
        )
        for observation in observations:
            observation.pop("_normalized")
        rows.append({
            "a": a,
            "slack": slack,
            "required_contact_parity": required_parity,
            "determining_depths": list(fit_depths),
            "held_out_depth": held_depth,
            "radial_offset_polynomial": str(radial_fit),
            "normal_offset_polynomial": str(normal_fit),
            "normalized_amplitude_polynomial": str(amplitude_fit),
            "radial_held_out_agrees": radial_heldout_agrees,
            "normal_held_out_agrees": normal_heldout_agrees,
            "amplitude_held_out_prediction": str(amplitude_prediction),
            "amplitude_held_out_agrees": amplitude_heldout_agrees,
            "observations": observations,
        })
    return {
        "schema": (
            "axiompack.jacobian_cone_boundary_"
            "actual_leading.v1"
        ),
        "rows": rows,
        "all_key_heldouts_agree": all(
            row["radial_held_out_agrees"]
            and row["normal_held_out_agrees"]
            for row in rows
        ),
        "all_amplitude_heldouts_agree": all(
            row["amplitude_held_out_agrees"] for row in rows
        ),
        "claim_boundary": (
            "Exact four-depth classification of the maximum-radial "
            "cost-four row in the five exceptional d=0 states. "
            "A successful quadratic heldout does not by itself prove "
            "the degree bound or the all-order Magnus obstruction."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
