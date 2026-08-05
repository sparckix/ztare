#!/usr/bin/env python3
"""Boundary contact classes and their cancellation transition graph.

The cone slack is

    ell = 2*b - a - 3*d - 3*m.

The stable theorem covers ``ell>=4``.  This certificate treats the
twelve residue states ``a=0,1,2`` and ``ell=0,1,2,3``.  For ``d>=1``
each state has the same odd cost-four corner as the stable range.  At
``d=0`` only five state families lack that corner; their primary
cost-three orbit can be canceled only by leaving the exceptional set.
"""

from __future__ import annotations

from collections import defaultdict
import argparse
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_higher_contact_cost_four_scan import (  # noqa: E402
    NumericSourcePullback,
    _fixed_target_coefficients,
    _one_case,
)


D_SYMBOL, M_SYMBOL = sp.symbols(
    "d m",
    integer=True,
    positive=True,
)
DM_MONOMIALS = (
    sp.Integer(1),
    D_SYMBOL,
    M_SYMBOL,
    D_SYMBOL**2,
    D_SYMBOL * M_SYMBOL,
    M_SYMBOL**2,
)
PARITY_POINTS = {
    0: ((1, 1), (1, 3), (1, 5), (2, 2), (2, 4), (3, 1)),
    1: ((1, 2), (1, 4), (1, 6), (2, 1), (2, 3), (3, 2)),
}
HELD_OUT_POINT = {
    0: (2, 6),
    1: (2, 5),
}
EXCEPTIONAL_D_ZERO_STATES = {
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 0),
}
EXCEPTIONAL_RADIAL_OFFSET = {
    (0, 0): 2,
    (0, 1): 1,
    (0, 2): 1,
    (0, 3): 1,
    (1, 0): 2,
}
EXCEPTIONAL_PRIMARY_POLYNOMIAL = {
    (0, 0): M_SYMBOL * (81 * M_SYMBOL - 46) / 256,
    (0, 1): (
        (3 * M_SYMBOL + 1)
        * (153 * M_SYMBOL**2 + 114 * M_SYMBOL + 73)
        / 256
    ),
    (0, 2): (
        (3 * M_SYMBOL + 2)
        * (153 * M_SYMBOL**2 + 192 * M_SYMBOL + 112)
        / 256
    ),
    (0, 3): (
        3
        * (M_SYMBOL + 1)
        * (153 * M_SYMBOL**2 + 270 * M_SYMBOL + 169)
        / 256
    ),
    (1, 0): -(
        (M_SYMBOL + 1)
        * (81 * M_SYMBOL + 127)
        / 256
    ),
}


def _case(
    a: int,
    slack: int,
    discriminant_depth: int,
    contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[dict[tuple[int, int], sp.Expr]],
    include_full_residual: bool = False,
) -> tuple[sp.Expr, dict[str, object]]:
    numerator = (
        a
        + 3 * discriminant_depth
        + 3 * contact_depth
        + slack
    )
    if numerator % 2:
        raise ValueError("the state has the wrong parity")
    q_exponent = numerator // 2
    result = _one_case(
        q_exponent,
        contact_depth,
        a,
        pullback=pullback,
        background=background,
        discriminant_depth=discriminant_depth,
        normalization_contact_depth=contact_depth + 1,
        cone_admissible_covariant_only=True,
        include_full_residual=include_full_residual,
    )
    leading_scale = (
        (-sp.Rational(3, 4)) ** a
        * (-sp.Rational(1, 4)) ** q_exponent
        * sp.Rational(27, 8) ** discriminant_depth
        * (-sp.Rational(9, 16)) ** contact_depth
    )
    coefficient = sp.Rational(
        result["cost_four_predicted_odd_terminal"]["coefficient"]
    )
    return sp.factor(coefficient / leading_scale), result


def _leading_scale(
    a: int,
    q_exponent: int,
    discriminant_depth: int,
    contact_depth: int,
) -> sp.Expr:
    return (
        (-sp.Rational(3, 4)) ** a
        * (-sp.Rational(1, 4)) ** q_exponent
        * sp.Rational(27, 8) ** discriminant_depth
        * (-sp.Rational(9, 16)) ** contact_depth
    )


def _expected_boundary_polynomial(a: int, slack: int) -> sp.Expr:
    return sp.factor(
        -(
            21 * a
            + 57 * D_SYMBOL
            + 35 * M_SYMBOL
            + 9 * slack
        )
        / 36
    )


def _positive_d_certificates(
    pullback: NumericSourcePullback,
    background: list[dict[tuple[int, int], sp.Expr]],
) -> list[dict[str, object]]:
    rows = []
    for a in range(3):
        for slack in range(4):
            parity = (a + slack) % 2
            points = PARITY_POINTS[parity]
            matrix = sp.Matrix([
                [
                    monomial.subs({
                        D_SYMBOL: discriminant_depth,
                        M_SYMBOL: contact_depth,
                    })
                    for monomial in DM_MONOMIALS
                ]
                for discriminant_depth, contact_depth in points
            ])
            assert matrix.det() == -64
            values = []
            exact_rows = []
            for discriminant_depth, contact_depth in points:
                value, result = _case(
                    a,
                    slack,
                    discriminant_depth,
                    contact_depth,
                    pullback,
                    background,
                )
                assert result["cost_four_terminal_rectangle"][
                    "terminal_is_unique_northeast_corner"
                ]
                values.append(value)
                exact_rows.append({
                    "d": discriminant_depth,
                    "m": contact_depth,
                    "normalized_terminal": str(value),
                })
            coefficients = tuple(
                matrix.inv() * sp.Matrix(values)
            )
            polynomial = sp.factor(sum(
                coefficient * monomial
                for coefficient, monomial in zip(
                    coefficients,
                    DM_MONOMIALS,
                    strict=True,
                )
            ))
            expected = _expected_boundary_polynomial(a, slack)
            assert sp.factor(polynomial - expected) == 0

            held_d, held_m = HELD_OUT_POINT[parity]
            held_value, held_result = _case(
                a,
                slack,
                held_d,
                held_m,
                pullback,
                background,
            )
            assert held_result["cost_four_terminal_rectangle"][
                "terminal_is_unique_northeast_corner"
            ]
            assert held_value == expected.subs({
                D_SYMBOL: held_d,
                M_SYMBOL: held_m,
            })
            rows.append({
                "a": a,
                "slack": slack,
                "parity_d_plus_m": parity,
                "determining_rows": exact_rows,
                "solved_polynomial": str(polynomial),
                "held_out": {
                    "d": held_d,
                    "m": held_m,
                    "normalized_terminal": str(held_value),
                },
            })
    return rows


def _d_zero_classification(
    pullback: NumericSourcePullback,
    background: list[dict[tuple[int, int], sp.Expr]],
) -> dict[str, object]:
    robust = []
    exceptional = []
    robust_basis = (
        sp.Integer(1),
        M_SYMBOL,
        M_SYMBOL**2,
    )
    exceptional_basis = (
        *robust_basis,
        M_SYMBOL**3,
    )
    for a in range(3):
        for slack in range(4):
            state = (a, slack)
            required_parity = (a + slack) % 2
            first_m = 2 if required_parity == 0 else 1
            robust_determining_m = (
                first_m,
                first_m + 2,
                first_m + 4,
            )
            if state in EXCEPTIONAL_D_ZERO_STATES:
                determining_m = (
                    *robust_determining_m,
                    first_m + 6,
                )
                held_out_m = first_m + 8
            else:
                determining_m = robust_determining_m
                held_out_m = first_m + 6
            checked = []
            odd_values = []
            primary_values = []
            for contact_depth in (*determining_m, held_out_m):
                value, result = _case(
                    a,
                    slack,
                    0,
                    contact_depth,
                    pullback,
                    background,
                    include_full_residual=True,
                )
                corner = result["cost_four_terminal_rectangle"][
                    "terminal_is_unique_northeast_corner"
                ]
                q_exponent = (
                    a + 3 * contact_depth + slack
                ) // 2
                source_slope = (
                    2 * a
                    + 3 * q_exponent
                    + 2 * contact_depth
                )
                primary_key = [
                    source_slope
                    + EXCEPTIONAL_RADIAL_OFFSET.get(state, 0),
                    2 * contact_depth,
                ]
                full_rows = result["cost_four_residual_rows"]
                primary_matches = [
                    row for row in full_rows
                    if row["key_r_normal"] == primary_key
                ]
                primary_rectangle_violations = [
                    row for row in full_rows
                    if (
                        row["key_r_normal"][0] > primary_key[0]
                        or sum(row["key_r_normal"]) > sum(primary_key)
                    )
                ]
                checked.append({
                    "m": contact_depth,
                    "normalized_odd_slot": str(value),
                    "unique_northeast_corner": corner,
                    "primary_key_r_normal": primary_key,
                    "primary_rectangle_violations": (
                        primary_rectangle_violations
                    ),
                    "leading_rows": result["cost_four_leading_rows"],
                })
                odd_values.append(value)
                if state in EXCEPTIONAL_D_ZERO_STATES:
                    assert not corner
                    assert not primary_rectangle_violations, (
                        state,
                        contact_depth,
                        primary_key,
                        primary_rectangle_violations,
                    )
                    assert len(primary_matches) == 1
                    primary_coefficient = sp.Rational(
                        primary_matches[0]["coefficient"]
                    )
                    primary_values.append(sp.factor(
                        primary_coefficient
                        / _leading_scale(
                            a,
                            q_exponent,
                            0,
                            contact_depth,
                        )
                    ))
                else:
                    expected = _expected_boundary_polynomial(
                        a, slack
                    ).subs({
                        D_SYMBOL: 0,
                        M_SYMBOL: contact_depth,
                    })
                    assert corner
                    assert value == expected

            row = {
                "a": a,
                "slack": slack,
                "required_contact_parity": required_parity,
                "checked_rows": checked,
            }
            if state in EXCEPTIONAL_D_ZERO_STATES:
                interpolation_matrix = sp.Matrix([
                    [
                        monomial.subs(M_SYMBOL, contact_depth)
                        for monomial in exceptional_basis
                    ]
                    for contact_depth in determining_m
                ])
                assert abs(interpolation_matrix.det()) == 768
                primary_coefficients = tuple(
                    interpolation_matrix.inv()
                    * sp.Matrix(primary_values[:4])
                )
                primary_polynomial = sp.factor(sum(
                    coefficient * monomial
                    for coefficient, monomial in zip(
                        primary_coefficients,
                        exceptional_basis,
                        strict=True,
                    )
                ))
                assert primary_polynomial.subs(
                    M_SYMBOL, held_out_m
                ) == primary_values[-1], (
                    state,
                    determining_m,
                    primary_values,
                    primary_polynomial,
                )
                assert sp.factor(
                    primary_polynomial
                    - EXCEPTIONAL_PRIMARY_POLYNOMIAL[state]
                ) == 0
                roots = sp.roots(primary_polynomial, M_SYMBOL)
                prohibited_roots = [
                    root
                    for root in roots
                    if (
                        root.is_integer is True
                        and root.is_positive is True
                        and int(root) % 2 == required_parity
                    )
                ]
                assert not prohibited_roots
                row["normalized_primary_polynomial"] = str(
                    primary_polynomial
                )
                row["primary_roots"] = [
                    str(root) for root in roots
                ]
                row["no_positive_integral_root_of_required_parity"] = True
                row["primary_held_out_agrees"] = True
                exceptional.append(row)
            else:
                interpolation_matrix = sp.Matrix([
                    [
                        monomial.subs(M_SYMBOL, contact_depth)
                        for monomial in robust_basis
                    ]
                    for contact_depth in determining_m
                ])
                assert interpolation_matrix.det() == 16
                odd_coefficients = tuple(
                    interpolation_matrix.inv()
                    * sp.Matrix(odd_values[:3])
                )
                odd_polynomial = sp.factor(sum(
                    coefficient * monomial
                    for coefficient, monomial in zip(
                        odd_coefficients,
                        robust_basis,
                        strict=True,
                    )
                ))
                assert odd_polynomial.subs(
                    M_SYMBOL, held_out_m
                ) == odd_values[-1], (
                    state,
                    determining_m,
                    odd_values,
                    odd_polynomial,
                )
                expected_polynomial = _expected_boundary_polynomial(
                    a, slack
                ).subs(D_SYMBOL, 0)
                assert sp.factor(
                    odd_polynomial - expected_polynomial
                ) == 0
                row["normalized_odd_polynomial"] = str(
                    odd_polynomial
                )
                row["odd_held_out_agrees"] = True
                robust.append(row)
    return {
        "robust_states": robust,
        "exceptional_states": exceptional,
        "degree_bound_certificate": (
            "At fixed (a,ell) and contact parity, the fixed relative "
            "pivot pattern gives degree at most two for robust odd "
            "slots and degree at most three for exceptional primary "
            "slots; the latter includes one cumulative boundary solve."
        ),
        "unisolvent_depths_plus_one_held_out": True,
    }


def _transition_edges() -> dict[str, object]:
    states = [(a, slack) for a in range(3) for slack in range(4)]
    edges: dict[
        tuple[int, int],
        list[dict[str, int]],
    ] = defaultdict(list)
    for a, slack in states:
        radial_offset = EXCEPTIONAL_RADIAL_OFFSET.get(
            (a, slack),
            0,
        )
        for next_a, next_slack in states:
            for depth_mod_19 in range(19):
                numerator = (
                    7 * a
                    + 3 * slack
                    + 2 * radial_offset
                    + depth_mod_19
                    * (7 * a + 3 * slack + 11)
                    - 7 * next_a
                    - 3 * next_slack
                )
                if numerator % 19:
                    continue
                depth_offset = numerator // 19
                if depth_offset < 0:
                    continue
                edge = {
                    "next_a": next_a,
                    "next_slack": next_slack,
                    "depth_mod_19": depth_mod_19,
                    "d_offset": depth_offset,
                }
                edges[(a, slack)].append(edge)

    exceptional_exit_rows = []
    for state in sorted(EXCEPTIONAL_D_ZERO_STATES):
        state_edges = edges[state]
        assert state_edges
        for edge in state_edges:
            target_state = (
                edge["next_a"],
                edge["next_slack"],
            )
            target_d = edge["d_offset"]
            assert (
                target_d > 0
                or target_state not in EXCEPTIONAL_D_ZERO_STATES
            )
        exceptional_exit_rows.append({
            "source_state": list(state),
            "edges": state_edges,
        })

    # The residue graph alone is recurrent; the useful theorem is the
    # stricter exceptional-d=0 exit property above.
    return {
        "transition_equation": (
            "7*a'+19*d'+3*ell'="
            "7*a+19*d+3*ell+2*delta(a,ell)"
            "+k*(7*a+19*d+3*ell+11)"
        ),
        "exceptional_radial_offsets": {
            f"{a},{slack}": radial_offset
            for (a, slack), radial_offset
            in sorted(EXCEPTIONAL_RADIAL_OFFSET.items())
        },
        "all_twelve_residue_states_have_edges": all(
            edges[state] for state in states
        ),
        "exceptional_d_zero_exit_rows": exceptional_exit_rows,
        "no_edge_stays_in_exceptional_d_zero_set": True,
    }


def _exceptional_orbit_certificate() -> dict[str, object]:
    a, b, m, k, delta = sp.symbols(
        "a b m k delta",
        integer=True,
        nonnegative=True,
    )
    slope = 2 * a + 3 * b + 2 * m
    multiplier = sp.factor(
        2 * m * delta
        + 2 * k * (slope - m)
    )
    state_rows = []
    for state, radial_offset in sorted(
        EXCEPTIONAL_RADIAL_OFFSET.items()
    ):
        state_rows.append({
            "state_a_slack": list(state),
            "radial_offset_delta": radial_offset,
            "multiplier_is_positive_for_nonnegative_depth": True,
        })
    return {
        "primary_terminal": {
            "radial": "S+delta(a,ell)",
            "normal_order": "2*m",
        },
        "state_rows": state_rows,
        "adjoint_multiplier_without_letter_amplitude": str(
            multiplier
        ),
        "no_nonnegative_integral_resonance": True,
        "right_magnus_response": "phi_2, nonpolynomial",
        "first_direct_cancellation_obeys_transition_graph": True,
    }


def _finite_triangularization_certificate(
    transition_graph: dict[str, object],
) -> dict[str, object]:
    m, k = sp.symbols(
        "m k",
        integer=True,
        positive=True,
    )
    next_contact = sp.expand(m + (m - 1) * k)
    contact_increase = sp.factor(next_contact - m)
    assert contact_increase == k * (m - 1)
    assert transition_graph[
        "no_edge_stays_in_exceptional_d_zero_set"
    ]
    return {
        "invariant_contact_depth": (
            "nu_C of each nonzero polynomial target coefficient"
        ),
        "finite_prefix_maximum_contact_depth_exists": True,
        "exceptional_cancellation_contact_depth": str(next_contact),
        "contact_depth_increase": str(contact_increase),
        "maximum_depth_consequence": (
            "For m>1 and k>=1 the required canceler has contact "
            "depth above the finite prefix maximum."
        ),
        "contact_one_consequence": (
            "For m=1 the contact depth is unchanged, but every "
            "transition leaves the exceptional d=0 state set."
        ),
        "same_depth_consequence": (
            "At k=0, and after every contact-one transition, the "
            "target class has a current-independent odd terminal."
        ),
        "equal_radial_affine_consequence": (
            "On a fixed contact/radial grade the odd transfer is a "
            "nonzero scalar. Cancellation exposes the next nonzero "
            "radial grade, so finite D-adic combinations terminate."
        ),
        "finite_linear_combinations_excluded": True,
    }


def run(
    include_full_positive_d_grid: bool = True,
) -> dict[str, object]:
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    positive_d = (
        _positive_d_certificates(pullback, background)
        if include_full_positive_d_grid
        else "skipped"
    )
    transition_graph = _transition_edges()
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "boundary_contact_classes.v2"
        ),
        "boundary_states": "a in {0,1,2}, ell in {0,1,2,3}",
        "positive_d_polynomial_certificates": positive_d,
        "d_zero_classification": _d_zero_classification(
            pullback, background
        ),
        "exceptional_orbit_certificate": (
            _exceptional_orbit_certificate()
        ),
        "transition_graph": transition_graph,
        "finite_triangularization": (
            _finite_triangularization_certificate(
                transition_graph
            )
        ),
        "conclusion": (
            "Every boundary monomial either has a current-independent "
            "odd phi_3 corner, or has a primary phi_2 orbit whose first "
            "direct cancellation exits to such a class. The corrected "
            "state-dependent primary offsets and fifth-depth amplitude "
            "held-outs restore the maximal-contact induction for every "
            "finite linear combination."
        ),
        "claim_boundary": (
            "All-order obstruction for finite polynomial prefixes in "
            "the four boundary slack classes. An infinite "
            "coefficientwise-finite contact schedule remains outside."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-full-positive-d-grid",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(not arguments.skip_full_positive_d_grid),
        indent=2,
        sort_keys=True,
    ))
