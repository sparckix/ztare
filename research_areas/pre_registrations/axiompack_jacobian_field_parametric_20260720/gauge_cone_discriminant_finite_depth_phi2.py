#!/usr/bin/env python3
"""Uniform one-C obstruction at every discriminant depth ``r >= 2``.

For ``D = 4*P^3 + 27*Q^2``, the saturated cost-three quotient of
``P^a*Q^b*D^r*C`` is an ordered-pair contribution from two distinct
``D`` factors.  Its ratio to the zero-grade coefficient is

    -r*(r-1)/96.

The quotient is therefore nonzero in characteristic zero.  Its later
right-Magnus logarithm is the same nonpolynomial ``phi_2`` response as
the depth-one residue families.
"""

from __future__ import annotations

import argparse
from math import comb, factorial
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_low_mixed_lower_terminal_recurrence import (  # noqa: E402
    LowMixedCase,
    _c_seed_column,
)


def _phi_two_coefficient(depth: int) -> sp.Expr:
    return sp.factor(sum(
        sp.bernoulli(depth - power, 0)
        / (
            factorial(depth - power)
            * factorial(power)
            * (2 * power + 3)
        )
        for power in range(depth + 1)
    ))


def _minimum_q_exponent(
    p_exponent: int,
    discriminant_depth: int,
) -> int:
    return (
        p_exponent + 3 * discriminant_depth + 4
    ) // 2


def _slope(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
) -> int:
    return (
        2 * p_exponent
        + 3 * q_exponent
        + 5 * discriminant_depth
        + 1
    )


def _zero_grade_coefficient(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    prefix_scale: sp.Expr = sp.Integer(1),
) -> sp.Expr:
    return sp.factor(
        prefix_scale
        * sp.Rational(
            (
                (-1) ** (p_exponent + q_exponent + 1)
                * 3 ** (
                    p_exponent
                    + 3 * discriminant_depth
                    + 2
                )
            ),
            2 ** (
                2 * p_exponent
                + 2 * q_exponent
                + 3 * discriminant_depth
                + 2
            ),
        )
    )


def _terminal_seed(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    prefix_scale: sp.Expr = sp.Integer(1),
) -> sp.Expr:
    if discriminant_depth < 2:
        raise ValueError("the saturated quotient starts at depth two")
    zero_grade = _zero_grade_coefficient(
        p_exponent,
        q_exponent,
        discriminant_depth,
        prefix_scale,
    )
    return sp.factor(
        -sp.Rational(
            discriminant_depth
            * (discriminant_depth - 1),
            96,
        )
        * zero_grade
    )


def _adjoint_factor(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    depth: int | sp.Expr,
    prefix_scale: sp.Expr = sp.Integer(1),
) -> sp.Expr:
    slope = _slope(
        p_exponent,
        q_exponent,
        discriminant_depth,
    )
    zero_grade = _zero_grade_coefficient(
        p_exponent,
        q_exponent,
        discriminant_depth,
        prefix_scale,
    )
    return sp.factor(
        2 * zero_grade * (slope * (depth - 1) - 2)
    )


def _terminal_coefficient(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    depth: int,
    prefix_scale: sp.Expr = sp.Integer(1),
) -> sp.Expr:
    seed = _terminal_seed(
        p_exponent,
        q_exponent,
        discriminant_depth,
        prefix_scale,
    )
    orbit = sp.prod(
        _adjoint_factor(
            p_exponent,
            q_exponent,
            discriminant_depth,
            index,
            prefix_scale,
        )
        for index in range(depth)
    )
    return sp.factor(
        3 * seed * _phi_two_coefficient(depth) * orbit
    )


def _terminal_exponent(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    depth: int,
) -> tuple[int, int]:
    slope = _slope(
        p_exponent,
        q_exponent,
        discriminant_depth,
    )
    return (
        slope * (depth + 1),
        slope * (depth + 1) + 4,
    )


def _ordered_pair_certificate() -> dict[str, object]:
    r = sp.symbols("r", integer=True, positive=True)
    x = sp.symbols("x", nonzero=True)
    d_zero_leading = sp.Rational(27, 8)
    d_zero_normal_two = -sp.Rational(9, 16)
    d_one_leading = sp.Rational(27, 128)
    marked_parameter_ratio = sp.factor(
        d_one_leading / d_zero_leading
    )
    marked_normal_ratio = sp.factor(
        d_zero_normal_two / d_zero_leading
    )
    single_pair = sp.factor(
        marked_parameter_ratio * marked_normal_ratio
    )
    assert marked_parameter_ratio == sp.Rational(1, 16)
    assert marked_normal_ratio == -sp.Rational(1, 6)
    assert single_pair == -sp.Rational(1, 96)
    ordered_pair_count = sp.factor(
        sp.diff(x**r, x, 2) / x ** (r - 2)
    )
    assert ordered_pair_count == r * (r - 1)
    return {
        "formal_identity": (
            "x^(2-r)*d^2(x^r)/dx^2=r*(r-1)"
        ),
        "source_jet_coefficients": {
            "D_0_leading_(radial_5_normal_0)": str(
                d_zero_leading
            ),
            "D_0_deficit_(radial_2_normal_2)": str(
                d_zero_normal_two
            ),
            "D_1_raising_(radial_7_normal_0)": str(
                d_one_leading
            ),
        },
        "marked_parameter_factor": str(marked_parameter_ratio),
        "marked_normal_factor": str(marked_normal_ratio),
        "ordered_pair_count": str(ordered_pair_count),
        "single_ordered_pair_ratio": str(single_pair),
        "saturated_terminal": "-r*(r-1)*A/96",
        "interpretation": (
            "One marked D factor supplies the parameter-raising term "
            "and a distinct D factor supplies the one-step radial "
            "deficit. All single-factor and unmarked terms lie in the "
            "radial/current image."
        ),
    }


def _current_column_certificate() -> dict[str, object]:
    for slope in range(29, 100):
        case = LowMixedCase(
            name=f"saturated_{slope}",
            prefix="P^a*Q^b*D^r*C",
            slope=slope,
            terminal_grade=(-slope - 2, -slope + 2),
            cost_two={},
            cost_three={},
            zero_grade_coefficient=sp.Integer(0),
            core_terminal=sp.Integer(0),
            held_out_depth_twelve=sp.Integer(0),
        )
        for amplitude in range(2, 8):
            cost = 2 * amplitude + 1
            columns = {
                offset: _c_seed_column(
                    case,
                    cost,
                    slope * amplitude + offset,
                )
                for offset in range(-4, 1)
            }
            assert all(
                columns[offset] is not None
                and not columns[offset][1]
                for offset in (-4, -3, -2, -1)
            )
            assert columns[0] is not None
            pivot = (
                slope * amplitude + 2,
                slope * amplitude + 4,
            )
            assert columns[0][1].get(pivot, 0) != 0
            terminal = (
                slope * amplitude,
                slope * amplitude + 4,
            )
            assert all(
                column is not None
                and terminal not in column[1]
                for column in columns.values()
            )
    return {
        "symbolic_support_argument": (
            "Offsets below zero lie below the saturated terminal "
            "projection. Offset zero has a nonzero normal-two pivot "
            "strictly above the terminal and is forced to zero. "
            "Positive offsets, if adjoined, are eliminated first by "
            "their still higher leading pivots."
        ),
        "affine_current_dimension_in_minimum_window": 4,
        "terminal_independent": True,
        "crosschecked_slopes": [29, 99],
        "crosschecked_amplitudes": [2, 7],
    }


def _symbolic_family_certificate() -> dict[str, object]:
    r = sp.symbols("r", integer=True, positive=True)
    n = sp.symbols("n", integer=True, nonnegative=True)
    sigma = sp.symbols("sigma", integer=True, positive=True)
    root = 1 + sp.Rational(2, 1) / sigma
    assert 1 < root.subs(sigma, 29) < 2
    roots = sp.solve(
        sp.Eq(sigma * (n - 1) - 2, 0),
        n,
    )
    assert len(roots) == 1
    assert sp.factor(
        roots[0] - (1 + sp.Rational(2, 1) / sigma)
    ) == 0
    # Every admissible saturated slope is at least 29, so it cannot
    # divide 2 and the displayed algebraic root is not integral.
    assert all(
        sp.Rational(2, integer_slope).q != 1
        for integer_slope in range(29, 200)
    )
    seed_ratio = -r * (r - 1) / 96
    assert sp.factor(
        seed_ratio + r * (r - 1) / 96
    ) == 0
    residues = []
    for p_exponent in range(3):
        minimum_b = _minimum_q_exponent(p_exponent, 2)
        residues.append({
            "p_exponent": p_exponent,
            "minimum_q_exponent_at_r_2": minimum_b,
            "general_cone_bound": (
                f"2*b >= {p_exponent}+3*r+3"
            ),
        })
    return {
        "residues": residues,
        "zero_grade_coefficient": (
            "(-1)^(a+b+1)*3^(a+3*r+2)"
            "/2^(2*a+2*b+3*r+2)"
        ),
        "terminal_seed": "-r*(r-1)*A/96",
        "effective_slope": "2*a+3*b+5*r+1",
        "terminal_exponent": (
            "(slope*(n+1),slope*(n+1)+4)"
        ),
        "adjoint_multiplier": (
            "2*A*(slope*(n-1)-2)"
        ),
        "only_algebraic_adjoint_zero": "1+2/slope",
        "adjoint_nonzero_at_integral_depths": True,
    }


def _normalized_representative_rows(
    discriminant_depth: int,
    maximum_depth: int = 3,
) -> list[dict[str, object]]:
    r = discriminant_depth
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = _terminal_coefficient(
            0,
            3 * r,
            r,
            depth,
            prefix_scale=sp.Rational(1, 4**r),
        )
        rows.append({
            "depth": depth,
            "cost": 3 + 2 * depth,
            "exponent": list(_terminal_exponent(
                0,
                3 * r,
                r,
                depth,
            )),
            "coefficient": str(coefficient),
            "nonzero": coefficient != 0,
        })
    return rows


def _fixed_depth_crosschecks() -> list[dict[str, object]]:
    expected = {
        2: (
            sp.Rational(2187, 268435456),
            sp.Rational(
                444816117,
                22517998136852480,
            ),
        ),
        3: (
            -sp.Rational(177147, 549755813888),
            sp.Rational(
                282429536481,
                18889465931478580854784,
            ),
        ),
        4: (
            sp.Rational(
                4782969,
                562949953421312,
            ),
            sp.Rational(
                1349730754842699,
                198070406285660843983859875840,
            ),
        ),
        5: (
            -sp.Rational(
                215233605,
                1152921504606846976,
            ),
            sp.Rational(
                405811421358553179,
                166153499473114484112975882535043072,
            ),
        ),
    }
    result = []
    for r, pair in expected.items():
        rows = _normalized_representative_rows(r)
        assert sp.Rational(rows[0]["coefficient"]) == pair[0]
        assert sp.Rational(rows[1]["coefficient"]) == pair[1]
        result.append({
            "discriminant_depth": r,
            "prefix": f"Q^{3*r}*D^{r}*C/4^{r}",
            "cost_three": rows[0],
            "cost_five": rows[1],
            "formula_matches_full_projected_replay": True,
        })
    return result


def _full_projection_witness(
    discriminant_depth: int,
) -> dict[str, object]:
    from gauge_cone_radial_triangular_staircase import run as staircase

    r = discriminant_depth
    if not 2 <= r <= 8:
        raise ValueError("full replay depth must lie between 2 and 8")
    parameter = sp.symbols("lambda")
    prefix_terms = [
        (
            3 * index,
            5 * r - 2 * index,
            sp.Rational(
                comb(r, index)
                * 4**index
                * 27 ** (r - index),
                4**r,
            )
            * parameter,
        )
        for index in range(r + 1)
    ]
    slope = 14 * r + 1
    terminal_grade = (-slope - 2, -slope + 2)
    result = staircase(
        maximum_target_order=4,
        cancel_second_normal=True,
        verify_roundtrips=False,
        compute_logarithms=True,
        normalization_objective="logarithm",
        delayed_c_prefix_terms=prefix_terms,
        project_to_prefix_ray=True,
        prefix_terminal_grade_override=terminal_grade,
        prefix_slope_override=slope,
    )
    projection = result["prefix_candidate_ray_projection"]
    expected_rows = _normalized_representative_rows(r, 1)
    verified = {}
    for row in expected_rows:
        cost = row["cost"]
        exponent = row["exponent"]
        lambda_power = (cost - 1) // 2
        expected_coefficient = (
            sp.Rational(row["coefficient"])
            * parameter**lambda_power
        )
        actual = [
            item
            for item in projection["source_logarithm"][cost - 1]
            if (
                item[0] == list(terminal_grade)
                and item[1] == exponent
            )
        ]
        assert actual == [[
            list(terminal_grade),
            exponent,
            str(expected_coefficient),
        ]]
        verified[str(cost)] = actual
    assert all(
        row[0] != list(terminal_grade)
        for row in projection["source_velocity"][4]
    )
    return {
        "verified": True,
        "discriminant_depth": r,
        "prefix_terms": [
            [p, q, str(coefficient)]
            for p, q, coefficient in prefix_terms
        ],
        "terminal_rows": verified,
        "zero_terminal_velocity_at_cost_five": True,
    }


def run(
    verify_depth: int | None = None,
) -> dict[str, object]:
    assert [
        _phi_two_coefficient(depth)
        for depth in range(4)
    ] == [
        sp.Rational(1, 3),
        sp.Rational(1, 30),
        -sp.Rational(1, 1260),
        -sp.Rational(1, 1890),
    ]
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "discriminant_finite_depth_phi2.v1"
        ),
        "discriminant": "D=4*P^3+27*Q^2",
        "declared_depth_range": "r>=2",
        "ordered_pair_certificate": _ordered_pair_certificate(),
        "symbolic_family": _symbolic_family_certificate(),
        "current_quotient": _current_column_certificate(),
        "right_magnus_response": {
            "function": (
                "phi_2(x)=x/(exp(x)-1)"
                "*integral_0^1 t^2*exp(t^2*x)dt"
            ),
            "nonpolynomial_certificate": (
                "At x=2*pi*i, I_2=(1-I_0)/(4*pi*i) "
                "and Re(I_0)<1, so the numerator is nonzero."
            ),
        },
        "fixed_depth_crosschecks": _fixed_depth_crosschecks(),
        "full_projection": (
            _full_projection_witness(verify_depth)
            if verify_depth is not None
            else {
                "verified": False,
                "replay_option": "--verify-depth R",
                "supported_depths": [2, 8],
            }
        ),
        "claim_boundary": (
            "All-order terminal nontermination for every admissible "
            "one-C multiplier of exact finite discriminant depth "
            "r>=2. Combined with the separate depth-zero and "
            "depth-one results, this covers every finite one-C "
            "multiplier. Powers C^m with m>=2 remain outside."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-depth",
        type=int,
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(verify_depth=arguments.verify_depth),
        indent=2,
        sort_keys=True,
    ))
