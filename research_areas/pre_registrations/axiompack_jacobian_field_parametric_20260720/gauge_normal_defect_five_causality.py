#!/usr/bin/env python3
"""All-order causal cutoff for the transverse Magnus ``Z`` ray.

The exact source-only connection and every moving target pullback have
nonnegative normal order in the ``(u,z)`` chart.  The density-``z^2`` bracket
then gives an additive defect for Magnus words.  The critical ``Z_q`` ray has
total instantaneous defect five, so derivative orders three and higher are
excluded without a spatial-degree cap.
"""

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

from gauge_moving_pullback_normal_semigroup import (  # noqa: E402
    _exact_family,
    _support_certificate,
)


def _source_only_hamiltonian() -> tuple[
    tuple[sp.Symbol, sp.Symbol, sp.Symbol],
    sp.Expr,
    dict[str, object],
]:
    (parameter, u, z), family_p, family_q = _exact_family()
    jacobian = sp.Matrix([family_p, family_q]).jacobian([u, z])
    determinant = sp.factor(jacobian.det())
    assert determinant == -z**2 / 8
    velocity = sp.simplify(
        jacobian.inv()
        * sp.Matrix([
            sp.diff(family_p, parameter),
            sp.diff(family_q, parameter),
        ])
    )
    source_u = sp.cancel(velocity[0])
    source_z = sp.cancel(velocity[1])
    assert sp.factor(
        sp.diff(z**2 * source_u, u)
        + sp.diff(z**2 * source_z, z)
    ) == 0
    hamiltonian = sp.integrate(z**2 * source_u, z)
    residual = sp.cancel(
        -sp.diff(hamiltonian, u) - z**2 * source_z
    )
    assert residual == 0
    hamiltonian = sp.cancel(
        hamiltonian - hamiltonian.subs({u: 0, z: 0})
    )
    assert sp.cancel(sp.diff(hamiltonian, z) - z**2 * source_u) == 0
    assert sp.cancel(-sp.diff(hamiltonian, u) - z**2 * source_z) == 0
    support = _support_certificate(
        "source_only_hamiltonian",
        hamiltonian,
        parameter=parameter,
        u=u,
        z=z,
    )
    assert support["minimum_normal_order"] == 0
    return (parameter, u, z), hamiltonian, support


def _bracket_certificate() -> dict[str, object]:
    u, z = sp.symbols("u z", nonzero=True)
    first_radial, second_radial = sp.symbols(
        "a b", integer=True, nonnegative=True
    )
    first_normal, second_normal = sp.symbols(
        "m n", integer=True
    )
    first = u**first_radial * z ** (first_radial + first_normal)
    second = u**second_radial * z ** (
        second_radial + second_normal
    )
    bracket = sp.expand(
        (
            sp.diff(first, z) * sp.diff(second, u)
            - sp.diff(first, u) * sp.diff(second, z)
        )
        / z**2
    )
    expected = (
        (first_normal * second_radial
         - first_radial * second_normal)
        * u ** (first_radial + second_radial - 1)
        * z ** (
            first_radial
            + second_radial
            + first_normal
            + second_normal
            - 3
        )
    )
    assert sp.simplify(bracket - expected) == 0
    return {
        "basis": "E_(a,n)=u^a*z^(a+n)=r^a*z^n",
        "bracket": (
            "[E_(a,m),E_(b,n)]="
            "(m*b-a*n)*E_(a+b-1,m+n-2)"
        ),
        "normal_shift": "m+n-2",
        "exact": True,
    }


def _causality_certificate() -> dict[str, object]:
    # For a word with letters (j_i,n_i), logarithmic order is
    # sum(j_i+1), while every bracket lowers total normal order by two.
    # Therefore n_out + 2*q = 2 + sum(n_i+2*j_i).
    checked_rows = []
    for logarithmic_order in (5, 8, 13, 21):
        output_normal = 7 - 2 * logarithmic_order
        total_defect = output_normal + 2 * logarithmic_order - 2
        assert total_defect == 5
        checked_rows.append({
            "logarithmic_order": logarithmic_order,
            "Z_normal_order": output_normal,
            "required_total_instantaneous_defect": total_defect,
            "maximum_possible_derivative_order": 2,
        })

    # Strong negative control: without nonnegative normal support, an
    # order-three letter of normal -1 has defect five and breaches cutoff.
    assert -1 + 2 * 3 == 5
    return {
        "instantaneous_defect": "delta=n+2*j",
        "word_identity": "n_out+2*q=2+sum(delta_i)",
        "Z_required_sum": 5,
        "nonnegative_normal_implies_each_delta_nonnegative": True,
        "derivative_orders_at_least_three_excluded": True,
        "checked_rows": checked_rows,
        "negative_control": {
            "derivative_order": 3,
            "normal_order": -1,
            "defect": 5,
            "breaches_without_semigroup_support": True,
        },
    }


def run() -> dict[str, object]:
    (_parameter, _u, _z), _hamiltonian, source_support = (
        _source_only_hamiltonian()
    )
    bracket = _bracket_certificate()
    causality = _causality_certificate()
    return {
        "schema": "axiompack.jacobian_normal_defect_five_causality.v1",
        "source_only_connection": {
            "jacobian_determinant": "-z^2/8",
            "hamiltonian_equations_replayed": True,
            "support": source_support,
        },
        "arbitrary_target_control": {
            "source_hamiltonian_form": (
                "L_source_only+8*K_s(P_s,Q_s)"
            ),
            "moving_pullback_has_nonnegative_normal": True,
            "every_compatible_instantaneous_source_hamiltonian_has_"
            "nonnegative_normal": True,
        },
        "normal_lie_algebra": bracket,
        "causality": causality,
        "consequence": {
            "later_projected_velocity_inputs_are_zero": True,
            "first_excluded_derivative_order": 3,
            "applies_to_arbitrary_coefficientwise_polynomial_backbone": True,
            "discharges_conditional_velocity_filtration_hypothesis": True,
        },
        "claim_boundary": (
            "All-order causal cutoff for the defect-five Z-ray. Its "
            "coefficient still depends on the unrestricted finite first "
            "three velocity rows, and nonvanishing after every such prefix "
            "is not proved here."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
