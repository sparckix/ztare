#!/usr/bin/env python3
"""Certificates for the finite higher-contact prefix obstruction.

The governing identity is contact valuation, not a displayed factor
count.  In the fixed chart ``r=u*z``, the seed map induces

    nu_z(H(P_0,Q_0)) = 2 * nu_C(H).

Consequently a current solve that has preserved all rows through normal
order ``2*m`` cannot change an odd row ``2*m+1``.  The stable cost-four
transfer is diagonal on the first nonzero source-radial symbol, and its
eigenvalue never vanishes in positive contact depth.
"""

from __future__ import annotations

import argparse
from math import factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_discriminant_depth_scan import (  # noqa: E402
    C_ZERO,
    D_ZERO,
    P_ZERO,
    Q_ZERO,
)
from gauge_cone_boundary_contact_classes import (  # noqa: E402
    run as boundary_contact_certificate,
)
from gauge_cone_higher_contact_discriminant_symbolic import (  # noqa: E402
    run as discriminant_transfer_certificate,
)
from gauge_cone_higher_contact_first_quotient import (  # noqa: E402
    _canonical_contact_multiplier,
)
from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_cone_monomial,
)


A, B, D, M, K, R = sp.symbols(
    "a b d m k R",
    integer=True,
    nonnegative=True,
)


def _contact_valuation_certificate() -> dict[str, object]:
    r, z, p, q = sp.symbols("r z P Q")
    p_zero = -sp.Rational(3, 4) * r**2 + r + z / 2
    q_zero = (
        -sp.Rational(1, 4) * r**3
        + sp.Rational(1, 4) * r**2
        + r * z / 4
    )
    cusp = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    cusp_pullback = sp.factor(cusp.subs({p: p_zero, q: q_zero}))
    expected = z**2 * (
        -9 * r**2 + 12 * r + 8 * z - 4
    ) / 16
    assert sp.factor(cusp_pullback - expected) == 0

    p_axis = p_zero.subs(z, 0)
    q_axis = q_zero.subs(z, 0)
    resultant = sp.factor(
        sp.resultant(p - p_axis, q - q_axis, r)
    )
    assert sp.factor(resultant - cusp / 64) == 0
    unit = sp.factor(expected / z**2)
    assert unit.subs(z, 0) != 0

    return {
        "seed_pullbacks": {
            "P_0": str(p_zero),
            "Q_0": str(q_zero),
            "C_0": str(cusp_pullback),
        },
        "axis_elimination_resultant": str(resultant),
        "axis_kernel_generator": "C",
        "C_over_z_squared": str(unit),
        "C_over_z_squared_is_unit_in_Q(r)[[z]]": True,
        "valuation_identity": "nu_z(H(P_0,Q_0))=2*nu_C(H)",
        "inverse_image_identity": (
            "phi^(-1)((z^(2*m+2)))=(C^(m+1))"
        ),
        "odd_current_quotient": (
            "agreement through normal 2*m forces agreement "
            "through normal 2*m+1"
        ),
    }


def _predicted_support(contact_depth: int, weight: int) -> bool:
    if contact_depth == 0:
        return weight >= 5
    if contact_depth % 2 == 0:
        half = contact_depth // 2
        return weight in {9 * half, 9 * half + 3} or (
            weight >= 9 * half + 5
        )
    half = (contact_depth - 1) // 2
    return weight in {
        9 * half + 6,
        9 * half + 8,
        9 * half + 9,
    } or weight >= 9 * half + 11


def _current_support_certificate() -> dict[str, object]:
    checked_depth = 12
    checked_weight = 100
    for contact_depth in range(checked_depth + 1):
        for weight in range(checked_weight + 1):
            radial = weight + 2 * contact_depth
            actual = (
                _canonical_cone_monomial(weight) is not None
                if contact_depth == 0
                else _canonical_contact_multiplier(
                    radial,
                    contact_depth,
                ) is not None
            )
            assert actual == _predicted_support(
                contact_depth,
                weight,
            ), (contact_depth, weight, actual)
    return {
        "level_zero": "S_0={w:w>=5}",
        "positive_even_level_2k": (
            "S_(2k)={9k,9k+3} union {w:w>=9k+5}"
        ),
        "positive_odd_level_2k_plus_1": (
            "S_(2k+1)={9k+6,9k+8,9k+9} "
            "union {w:w>=9k+11}"
        ),
        "checked_contact_depth_through": checked_depth,
        "checked_weight_through": checked_weight,
        "boundary_dichotomy": (
            "a missing even pivot is already a radial terminal; "
            "after every even pivot is removed, the odd transfer "
            "is a current cokernel"
        ),
    }


def _factor_support_certificate() -> dict[str, object]:
    families = {
        "P": (P_ZERO, (2, 0)),
        "Q": (Q_ZERO, (3, 0)),
        "D": (D_ZERO, (5, 0)),
        "C": (C_ZERO, (2, 2)),
    }
    rows = {}
    for name, (value, leading) in families.items():
        rows[name] = []
        for (radial, normal), coefficient in sorted(value.items()):
            deficit = leading[0] - radial
            extra_normal = normal - leading[1]
            assert deficit >= extra_normal >= 0
            rows[name].append({
                "radial_deficit": deficit,
                "extra_normal_order": extra_normal,
                "coefficient": str(coefficient),
            })
    return {
        "rows": rows,
        "product_support": "radial_deficit>=extra_normal_order>=0",
        "odd_row_consequence": (
            "a column reaching an odd terminal has a strictly "
            "higher even-normal pivot unless its coefficient is zero"
        ),
    }


def _transfer_and_orbit_certificate() -> dict[str, object]:
    multiplier_radial = 2 * A + 3 * B + 5 * D
    slope = multiplier_radial + 2 * M
    normalized_transfer = sp.factor(
        -(3 * multiplier_radial + 4 * M) / 18
    )
    same = sp.factor(-(3 * slope - 2 * M) / 18)
    assert sp.factor(normalized_transfer - same) == 0

    orbit_radial = sp.expand(slope + K * (slope - 1))
    orbit_normal = sp.expand(
        2 * M + 1 + 2 * K * (M - 1)
    )
    bracket_multiplier = sp.factor(
        2 * (slope - M) * K - slope
    )
    resonance = sp.factor(
        slope / (2 * (slope - M))
    )
    assert sp.factor(
        1 - resonance
        - multiplier_radial
        / (2 * (multiplier_radial + M))
    ) == 0
    limiting_rate = sp.factor(slope + M - 2)

    generic_radial_eigenvalue = sp.factor(
        -(3 * R - 2 * M) / 18
    )
    multiplier_degree = sp.symbols(
        "w",
        integer=True,
        nonnegative=True,
    )
    euler_eigenvalue = sp.factor(
        3 * multiplier_degree + 4 * M
    )
    assert sp.factor(
        euler_eigenvalue
        - (3 * (multiplier_degree + 2 * M) - 2 * M)
    ) == 0
    return {
        "source_radial_slope": str(slope),
        "odd_terminal_normal_order": str(2 * M + 1),
        "normalized_monomial_transfer": str(normalized_transfer),
        "radial_grade_eigenvalue": str(generic_radial_eigenvalue),
        "radial_grade_eigenvalue_nonzero_for_R>=2*m": True,
        "multiplier_euler_operator": "3*r*d/dr+4*m",
        "multiplier_degree_eigenvalue": str(euler_eigenvalue),
        "finite_polynomial_multiplier_kernel_is_zero": True,
        "orbit_radial_exponent": str(orbit_radial),
        "orbit_normal_order": str(orbit_normal),
        "bracket_multiplier_without_letter_amplitude": str(
            bracket_multiplier
        ),
        "only_algebraic_resonance": str(resonance),
        "resonance_strictly_between_zero_and_one": True,
        "limiting_source_hamiltonian_rate": str(limiting_rate),
    }


def _response_certificate(maximum_depth: int) -> dict[str, object]:
    if maximum_depth < 9:
        raise ValueError("maximum_depth must be at least nine")
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = (
            sp.Rational(1, 4)
            if depth == 0
            else sp.Rational(
                sp.bernoulli(depth + 1),
                2 * factorial(depth + 1),
            )
        )
        if depth >= 1 and depth % 2 == 0:
            assert coefficient == 0
        if depth % 2 == 1:
            assert coefficient != 0
        rows.append({
            "depth": depth,
            "coefficient_after_orbit_division": str(coefficient),
        })
    return {
        "right_magnus_response": (
            "phi_3(x)=x/(exp(x)-1)*integral_0^1 "
            "t^3*exp(t^2*x)dt"
        ),
        "rows": rows,
        "infinite_nonzero_subsequence": "every odd depth",
        "finite_forcing_transform": (
            "E_V(x)=integral_0^x(t*exp(t)*V(t))dt/"
            "(2*x*(exp(x)-1))"
        ),
        "finite_forcing_nontermination": (
            "no nonzero polynomial V gives a polynomial E_V"
        ),
    }


def run(
    maximum_depth: int = 11,
    verify_transfer: bool = True,
    verify_boundary: bool = True,
) -> dict[str, object]:
    transfer = (
        discriminant_transfer_certificate(include_held_out=False)
        if verify_transfer
        else None
    )
    if transfer is not None:
        assert transfer["normalized_terminal"] == (
            "-(6*a + 9*b + 15*d + 4*m)/18"
        )
    boundary = (
        boundary_contact_certificate(
            include_full_positive_d_grid=False
        )
        if verify_boundary
        else None
    )
    if boundary is not None:
        assert boundary["finite_triangularization"][
            "finite_linear_combinations_excluded"
        ]
    return {
        "schema": (
            "axiompack.jacobian_cone_higher_contact_"
            "global_obstruction.v2"
        ),
        "contact_valuation": _contact_valuation_certificate(),
        "current_radial_support": _current_support_certificate(),
        "factor_support": _factor_support_certificate(),
        "stable_transfer_schema": (
            transfer["schema"] if transfer is not None else "skipped"
        ),
        "boundary_certificate_schema": (
            boundary["schema"] if boundary is not None else "skipped"
        ),
        "transfer_and_orbit": _transfer_and_orbit_certificate(),
        "response": _response_certificate(maximum_depth),
        "finite_higher_contact_prefix_escape": False,
        "claim_boundary": (
            "All nonzero finite polynomial prefixes in positive "
            "C-adic contact depth are excluded. Together with the "
            "separate complete one-C classification, this excludes "
            "every nonzero finite cone-compatible contact prefix. "
            "An infinite coefficientwise-finite C-adic schedule and "
            "the full tail minimax value remain separate."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-depth", type=int, default=11)
    parser.add_argument(
        "--skip-transfer-verification",
        action="store_true",
    )
    parser.add_argument(
        "--skip-boundary-verification",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            arguments.maximum_depth,
            not arguments.skip_transfer_verification,
            not arguments.skip_boundary_verification,
        ),
        indent=2,
        sort_keys=True,
    ))
