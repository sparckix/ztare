#!/usr/bin/env python3
"""Compare the defect-five ray across three exact finite two-jets."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import gauge_moving_cone_z_ray_affine_invariance as ZRAY  # noqa: E402
import gauge_moving_section_affine_extension as AFFINE  # noqa: E402
from gauge_moving_cone_excess_filtered_recurrence import (  # noqa: E402
    _filtered_magnus,
    _from_sparse,
    _z_scalar,
)
from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from gauge_normal_defect_five_causality import (  # noqa: E402
    _source_only_hamiltonian,
)


Pair = tuple[sp.Expr, sp.Expr]


def _hamiltonian_velocity_coefficients(
    hamiltonian: sp.Expr,
    *,
    parameter: sp.Symbol,
    u: sp.Symbol,
    z: sp.Symbol,
) -> list[Pair]:
    expansion = sp.series(hamiltonian, parameter, 0, 3).removeO().expand()
    result = []
    for order in range(3):
        coefficient = sp.expand(expansion.coeff(parameter, order))
        first = sp.cancel(sp.diff(coefficient, z) / z**2)
        second = sp.cancel(-sp.diff(coefficient, u) / z**2)
        assert first.as_numer_denom()[1].free_symbols.isdisjoint({u, z})
        assert second.as_numer_denom()[1].free_symbols.isdisjoint({u, z})
        result.append((sp.expand(first), sp.expand(second)))
    return result


def _minimum_cap_velocity(u: sp.Symbol, z: sp.Symbol) -> list[Pair]:
    family = AFFINE._Family(2)
    base, directions = ZRAY._carry(family, (5, 5, 7))
    assert len(directions) == 1
    # The existing complete-affine theorem proves the selected Z coefficients
    # are independent of this direction.  Use the rational base point here.
    result = []
    substitution = {
        family.v: u - 1,
        family.t: (z - 2 + 3 * (u - 1)) / 2,
    }
    for order in range(3):
        source = base[1][order]
        first = sp.expand(
            source[0].subs(substitution) / sp.factorial(order)
        )
        second = sp.expand(
            (2 * source[1] - 3 * source[0]).subs(substitution)
            / sp.factorial(order)
        )
        result.append((first, second))
    return result


def _scalars(
    name: str,
    velocity: list[Pair],
    *,
    u: sp.Symbol,
    z: sp.Symbol,
    maximum_order: int,
) -> dict[str, object]:
    sparse = _filtered_magnus(velocity, maximum_order, u, z)
    logarithm = [_from_sparse(value, u, z) for value in sparse]
    rows = []
    first_zero = None
    for order in range(5, maximum_order + 1):
        shell = ZRAY._degree_shell(
            logarithm[order], u, z, 4 * order - 6
        )
        scalar = sp.factor(_z_scalar(shell, order, u, z))
        if first_zero is None and scalar == 0:
            first_zero = order
        rows.append({
            "logarithmic_order": order,
            "Z_scalar": str(scalar),
            "nonzero": scalar != 0,
        })
    return {
        "representative": name,
        "velocity_component_degrees": [
            [
                (
                    -1
                    if component == 0
                    else sp.Poly(component, u, z).total_degree()
                )
                for component in row
            ]
            for row in velocity
        ],
        "first_zero_order": first_zero,
        "rows": rows,
    }


def run(maximum_order: int = 10) -> dict[str, object]:
    if maximum_order < 9:
        raise ValueError("held-out comparison requires order at least nine")
    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    p_coefficient = sp.factor(
        96
        * (parameter**2 - 12 * parameter + 16)
        / (
            (parameter - 6) ** 3
            * (parameter - 4) ** 2
            * (parameter + 4) ** 2
        )
    )
    pq_coefficient = sp.factor(
        2 * parameter / ((parameter - 4) * (parameter + 4))
    )
    controlled_target = (
        p_coefficient * family_p**3
        + pq_coefficient * family_p * family_q
        - family_q**2 / 4
    )
    controlled_source = sp.cancel(source_only + 8 * controlled_target)
    controlled_at_zero = sp.cancel(controlled_source.subs(parameter, 0))
    assert sp.diff(controlled_at_zero, u) == 0
    assert sp.diff(controlled_at_zero, z) == 0

    velocities = {
        "source_only": _hamiltonian_velocity_coefficients(
            source_only, parameter=parameter, u=u, z=z
        ),
        "controlled_source_zero_at_s0": (
            _hamiltonian_velocity_coefficients(
                controlled_source, parameter=parameter, u=u, z=z
            )
        ),
        "minimum_cap_affine_base": _minimum_cap_velocity(u, z),
    }
    rows = [
        _scalars(
            name,
            velocity,
            u=u,
            z=z,
            maximum_order=maximum_order,
        )
        for name, velocity in velocities.items()
    ]
    sequences = [
        tuple(item["Z_scalar"] for item in row["rows"])
        for row in rows
    ]
    return {
        "schema": "axiompack.jacobian_defect_five_two_jet_comparison.v1",
        "maximum_logarithmic_order": maximum_order,
        "later_velocity_rows_irrelevant_to_Z_ray_by_defect_causality": True,
        "representatives": rows,
        "all_sequences_equal": len(set(sequences)) == 1,
        "all_checked_sequences_nonzero": all(
            row["first_zero_order"] is None for row in rows
        ),
        "claim_boundary": (
            "Three exact finite two-jets and Z-ray coefficients through the "
            "declared maximum logarithmic order only. Defect causality makes "
            "the first three velocity rows sufficient for this ray, but no "
            "all-order coefficient formula or unrestricted radial-profile "
            "classification is claimed."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
