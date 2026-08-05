#!/usr/bin/env python3
"""Extract pure row-zero top-weight Magnus coefficients at q5 and q6."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_contact_zero_complete_parameter_jet import (  # noqa: E402
    _build_complete_jet_replay,
)


def _pure_row_zero_receipt(weight: int) -> dict[str, object]:
    replay = _build_complete_jet_replay(
        maximum_order=6,
        weights=(weight,),
    )
    row_zero_index = next(
        index
        for index, direction in enumerate(replay.directions)
        if direction.row == 0 and direction.weight == weight
    )
    rows = []
    for order in (5, 6):
        coefficient = replay.source_logarithm[order]
        pure_by_power = {
            len(monomial): spatial
            for monomial, spatial in coefficient.items()
            if monomial and set(monomial) == {row_zero_index}
        }
        nonzero_powers = sorted(
            power
            for power, spatial in pure_by_power.items()
            if any(value != 0 for value in spatial.values())
        )
        maximum_power = max(nonzero_powers)
        top_spatial = pure_by_power[maximum_power]
        competing_coordinates = {
            exponent
            for monomial, spatial in coefficient.items()
            if monomial != (row_zero_index,) * maximum_power
            and (
                not monomial
                or set(monomial) == {row_zero_index}
            )
            for exponent, value in spatial.items()
            if value != 0
        }
        exclusive = [
            exponent
            for exponent, value in top_spatial.items()
            if value != 0 and exponent not in competing_coordinates
        ]
        top_exponent = max(
            exclusive or [
                exponent
                for exponent, value in top_spatial.items()
                if value != 0
            ],
            key=lambda exponent: (sum(exponent), exponent),
        )
        rows.append({
            "logarithmic_order": order,
            "maximum_pure_row_zero_power": maximum_power,
            "exclusive_coordinate_count": len(exclusive),
            "top_coordinate_is_exclusive": bool(exclusive),
            "top_exclusive_exponent": list(top_exponent),
            "top_exclusive_hamiltonian_degree": sum(top_exponent),
            "top_exclusive_coefficient": str(
                sp.factor(top_spatial[top_exponent])
            ),
        })
    return {
        "weight": weight,
        "parity": "even" if weight % 2 == 0 else "odd",
        "orders": rows,
    }


def run() -> dict[str, object]:
    rows = [_pure_row_zero_receipt(weight) for weight in range(5, 15)]
    return {
        "schema": "axiompack.jacobian_contact_zero_top_weight_forcing.v1",
        "weights": rows,
        "claim_boundary": (
            "Pure row-zero coefficients for weights five through fourteen "
            "at logarithmic orders five and six. A symbolic parity formula "
            "and exclusion of mixed lower-weight collisions remain required."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
