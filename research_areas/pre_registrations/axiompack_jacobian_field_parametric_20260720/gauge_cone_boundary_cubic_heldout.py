#!/usr/bin/env python3
"""Fifth-depth heldouts for the corrected exceptional d=0 amplitudes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_boundary_contact_classes import (  # noqa: E402
    M_SYMBOL,
    NumericSourcePullback,
    _case,
    _fixed_target_coefficients,
    _leading_scale,
)


CANDIDATES = {
    (0, 1): (9, (3 * M_SYMBOL + 1)
             * (153 * M_SYMBOL**2 + 114 * M_SYMBOL + 73) / 256),
    (0, 2): (10, (3 * M_SYMBOL + 2)
              * (153 * M_SYMBOL**2 + 192 * M_SYMBOL + 112) / 256),
    (0, 3): (9, 3 * (M_SYMBOL + 1)
             * (153 * M_SYMBOL**2 + 270 * M_SYMBOL + 169) / 256),
}


def run() -> dict[str, object]:
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    rows = []
    for (a, slack), (contact_depth, candidate) in CANDIDATES.items():
        q_exponent = (a + 3 * contact_depth + slack) // 2
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
            include_full_residual=False,
        )
        leading = result["cost_four_leading_rows"]
        assert len(leading) == 1
        radial, normal = leading[0]["key_r_normal"]
        assert radial == source_slope + 1
        assert normal == 2 * contact_depth
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
        predicted = sp.factor(candidate.subs(
            M_SYMBOL, contact_depth
        ))
        assert normalized == predicted
        rows.append({
            "a": a,
            "slack": slack,
            "held_out_contact_depth": contact_depth,
            "leading_key_r_normal": [radial, normal],
            "normalized_coefficient": str(normalized),
            "predicted_coefficient": str(predicted),
            "candidate_polynomial": str(sp.factor(candidate)),
            "held_out_agrees": True,
        })
    return {
        "schema": (
            "axiompack.jacobian_cone_boundary_"
            "cubic_heldout.v1"
        ),
        "rows": rows,
        "all_heldouts_agree": True,
        "coefficient_nonvanishing": (
            "Every displayed factor has positive coefficients for m>0."
        ),
        "claim_boundary": (
            "Three fifth-depth exact heldouts for preregistered cubic "
            "amplitudes. The all-depth identity additionally uses the "
            "fixed-parity degree-at-most-three pivot certificate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
