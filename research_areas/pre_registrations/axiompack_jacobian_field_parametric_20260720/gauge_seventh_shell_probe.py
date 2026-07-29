#!/usr/bin/env python3
"""Probe the first compactified obstruction in the seventh contact jet.

This is deliberately a branchwise certificate.  It freezes the sparse
degree-eight prefix from ``gauge_bound_six_witness.py`` and computes the
order-seven residual with the same logarithmic/BCH convention.  It does not
parameterize every compatible lower prefix.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_bound_four_extension import build_through_four  # noqa: E402
from gauge_bound_six_witness import _solve_new_order  # noqa: E402
from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import _hamiltonian_field  # noqa: E402


Pair = tuple[sp.Expr, sp.Expr]


FROZEN_COORDINATES = {
    "a0": sp.Rational(11341, 80640),
    "a1": sp.Rational(1229, 20736),
    "a2": -sp.Rational(4729, 40320),
    "a3": sp.Integer(0),
    "a4": sp.Rational(2291, 36288),
    "a5": sp.Rational(733, 145152),
    "b0": sp.Integer(0),
    "b1": sp.Integer(0),
    "b2": sp.Integer(0),
}


EXPECTED_SHELL = (
    (sp.Symbol("u") + 1)
    * (
        4262519160 * sp.Symbol("u") ** 5
        - 17280177044 * sp.Symbol("u") ** 4
        + 6421252276 * sp.Symbol("u") ** 3
        + 16271460891 * sp.Symbol("u") ** 2
        - 5570127407 * sp.Symbol("u")
        - 1640381738
    )
    / 67722117120
)


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _combinatorial_degree_receipt() -> dict[str, object]:
    """Check the Laurent coefficient count behind the affine-degree bound."""
    checked_through = 32
    for degree_bound in range(checked_through + 1):
        for z_power in range(-degree_bound, degree_bound + 1):
            possible_u_degrees = [
                positive_choices
                for positive_choices in range(degree_bound + 1)
                for negative_choices in range(degree_bound + 1)
                if (
                    positive_choices - negative_choices == z_power
                    and positive_choices + negative_choices <= degree_bound
                )
            ]
            assert possible_u_degrees
            assert max(possible_u_degrees) == (
                degree_bound + z_power
            ) // 2
    return {
        "balance_variables": {
            "k": "number of positive-z t choices, each carrying at most one u",
            "ell": "number of negative-z choices",
        },
        "constraints": [
            "m = k - ell",
            "k + ell <= D",
            "deg_u <= k",
        ],
        "scalar_laurent_bound": (
            "deg_u [z^m] A(v,t) <= floor((D+m)/2) "
            "for every affine polynomial A of total degree <= D"
        ),
        "compact_source_formulas": {
            "dz": "-z^2 U",
            "du": "3*(V-(3/2)*U)/z + (u+1)*z*U",
        },
        "simple_pole_bounds_for_D_ge_3": {
            "deg_u_[z^-1]_dz": "floor((D-3)/2)",
            "deg_u_[z^-1]_du": "floor(D/2)",
            "deg_u_joint_shell": "floor(D/2)+1",
        },
        "integer_balance_check_D_through": checked_through,
    }


def _target_joint_residue_identity() -> dict[str, object]:
    """Verify the joint residue killed by every target Hamiltonian."""
    u, z, k_x, k_y = sp.symbols("u z K_X K_Y")
    x = u**2 - (u + 1) * z
    y = u**3 - sp.Rational(3, 2) * u * (u + 1) * z
    x_z, x_u = sp.diff(x, z), sp.diff(x, u)
    y_z, y_u = sp.diff(y, z), sp.diff(y, u)
    determinant = sp.factor(x_z * y_u - x_u * y_z)
    assert determinant == sp.Rational(3, 2) * z * (u + 1) ** 2

    # The Hamiltonian target field in (X,Y) coordinates is (K_Y,-K_X).
    local_z = sp.cancel((y_u * k_y + x_u * k_x) / determinant)
    local_u = sp.cancel((-y_z * k_y - x_z * k_x) / determinant)
    z_residue = sp.factor(sp.cancel(z * local_z).subs(z, 0))
    u_residue = sp.factor(sp.cancel(z * local_u).subs(z, 0))
    joint = sp.factor((u + 1) * z_residue - 2 * u * u_residue)
    assert joint == 0
    return {
        "seed_chart": {
            "X": str(x),
            "Y": str(y),
            "jacobian": str(determinant),
        },
        "target_field_convention": "(K_Y,-K_X)",
        "z_residue": str(z_residue),
        "u_residue": str(u_residue),
        "annihilator": "(u+1)*[z^-1]dz - 2*u*[z^-1]du",
        "symbolic_value": str(joint),
    }


def _frozen_prefix_through_six() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[int, Pair],
    dict[int, Pair],
]:
    bound = 8
    family = build_through_four(bound)
    data = _family_jets(7)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    parameters = family["complete_parameters_through_four"]
    assert {str(item) for item in parameters} == set(FROZEN_COORDINATES)
    substitution = {
        parameter: FROZEN_COORDINATES[str(parameter)]
        for parameter in parameters
    }
    target_fields = {
        order: tuple(
            sp.expand(item.subs(substitution)) for item in field
        )
        for order, field in family["target_fields"].items()
    }
    source_fields = {
        order: tuple(
            sp.expand(item.subs(substitution)) for item in field
        )
        for order, field in family["source_fields"].items()
    }
    for order in (5, 6):
        predicted = _composed_series(
            target_fields=target_fields,
            source_fields=source_fields,
            p=p,
            q=q,
            v=v,
            t=t,
            p0=data["P"][0],
            q0=data["Q"][0],
            maximum_order=order,
        )
        residual = (
            sp.expand(
                data["P"][order]
                - sp.factorial(order) * predicted[order][0]
            ),
            sp.expand(
                data["Q"][order]
                - sp.factorial(order) * predicted[order][1]
            ),
        )
        source, hamiltonian, _receipt = _solve_new_order(
            order=order,
            bound=bound,
            residual=residual,
            family=family,
            data=data,
            v=v,
            t=t,
            p=p,
            q=q,
        )
        source_fields[order] = source
        target_fields[order] = _hamiltonian_field(
            hamiltonian, p, q
        )

    replay = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=6,
    )
    for order in range(7):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                replay[order], actual, strict=True
            )
        )
    return family, data, target_fields, source_fields


def _seventh_joint_shell() -> dict[str, object]:
    family, data, target_fields, source_fields = (
        _frozen_prefix_through_six()
    )
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    predicted = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=7,
    )
    residual_p = sp.expand(
        data["P"][7] - sp.factorial(7) * predicted[7][0]
    )
    residual_q = sp.expand(
        data["Q"][7] - sp.factorial(7) * predicted[7][1]
    )

    u, z = sp.symbols("u z")
    compactification = {
        v: 1 / z - 1,
        t: (
            sp.Rational(3, 2) / z
            + (u + 1) * z / 3
            - sp.Rational(5, 2)
        ),
    }
    residual_x = sp.cancel((-3 * residual_p).subs(compactification))
    residual_y = sp.cancel(
        ((9 * residual_p - 27 * residual_q) / 2).subs(
            compactification
        )
    )
    x_z = -(u + 1)
    x_u = 2 * u - z
    y_z = -sp.Rational(3, 2) * u * (u + 1)
    y_u = 3 * u**2 - sp.Rational(3, 2) * (2 * u + 1) * z
    determinant = sp.Rational(3, 2) * z * (u + 1) ** 2
    required_z = sp.cancel(
        (y_u * residual_x - x_u * residual_y) / determinant
    )
    required_u = sp.cancel(
        (-y_z * residual_x + x_z * residual_y) / determinant
    )
    z_residue = sp.factor(sp.cancel(z * required_z).subs(z, 0))
    u_residue = sp.factor(sp.cancel(z * required_u).subs(z, 0))
    joint = sp.factor((u + 1) * z_residue - 2 * u * u_residue)
    assert sp.expand(joint - EXPECTED_SHELL) == 0
    polynomial = sp.Poly(joint, u, domain=sp.QQ)
    degree_nine_ceiling = 9 // 2 + 1
    assert polynomial.degree() == 6
    assert polynomial.LC() == sp.Rational(3946777, 62705664)
    assert polynomial.degree() > degree_nine_ceiling
    return {
        "parameter_order": 7,
        "frozen_prefix_source_degree": 8,
        "full_logarithmic_BCH_replay_through_order": 6,
        "joint_shell_polynomial": str(joint),
        "joint_shell_degree": polynomial.degree(),
        "joint_shell_leading_coefficient": str(polynomial.LC()),
        "degree_nine_shell_ceiling": degree_nine_ceiling,
        "branchwise_consequence": (
            "no order-seven target Hamiltonian and no affine source "
            "field of degree at most nine extends this frozen prefix"
        ),
        "degree_ten_status": (
            "the first joint-residue bound permits degree ten; this "
            "probe does not claim that later z-shells are compatible"
        ),
        "prefix_source_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in source_fields.items()
        },
        "order_seven_residual_sha256": [
            _sha(residual_p),
            _sha(residual_q),
        ],
    }


def run() -> dict[str, object]:
    return {
        "schema": "axiompack.jacobian_seventh_shell_probe.v1",
        "target_joint_residue_identity": (
            _target_joint_residue_identity()
        ),
        "affine_degree_bound": _combinatorial_degree_receipt(),
        "order_seven_frozen_prefix_shell": _seventh_joint_shell(),
        "claim_boundary": (
            "This is an exact obstruction for one frozen compatible "
            "degree-eight prefix. Invariance of the leading u^6 "
            "coefficient over every compatible degree-nine lower prefix "
            "is unproved, so this artifact does not determine the minimax "
            "value c_7 or an all-order degree law."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
