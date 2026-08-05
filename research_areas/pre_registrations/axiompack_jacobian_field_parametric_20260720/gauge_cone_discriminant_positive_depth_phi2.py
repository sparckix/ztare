#!/usr/bin/env python3
"""Uniform Magnus tail for discriminant depth at least two.

The symbolic first quotient is supplied by
``gauge_cone_discriminant_depth_symbolic``.  At every depth ``d>=2``
the terminal seed has normal order four, no current one-``C`` column
contains its monomial, and the normalized right-Magnus response is
``phi_2``.
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

from gauge_cone_low_mixed_lower_terminal_recurrence import (  # noqa: E402
    LowMixedCase,
    _c_seed_column,
)


LAMBDA = sp.symbols("lambda")


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


def _leading_scale(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
) -> sp.Expr:
    return sp.factor(
        (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
        * sp.Rational(27, 8) ** discriminant_depth
    )


def _zero_grade_coefficient(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
) -> sp.Expr:
    return sp.factor(
        -sp.Rational(9, 4)
        * _leading_scale(
            p_exponent,
            q_exponent,
            discriminant_depth,
        )
    )


def _terminal_seed(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
) -> sp.Expr:
    if discriminant_depth < 2:
        raise ValueError("this uniform layer starts at depth two")
    return sp.factor(
        _leading_scale(
            p_exponent,
            q_exponent,
            discriminant_depth,
        )
        * sp.Rational(3, 64)
        * sp.binomial(discriminant_depth, 2)
    )


def _adjoint_factor(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    depth: int | sp.Expr,
) -> sp.Expr:
    slope = _slope(
        p_exponent,
        q_exponent,
        discriminant_depth,
    )
    return sp.factor(
        2
        * _zero_grade_coefficient(
            p_exponent,
            q_exponent,
            discriminant_depth,
        )
        * (slope * (depth - 1) - 2)
    )


def _terminal_coefficient(
    p_exponent: int,
    q_exponent: int,
    discriminant_depth: int,
    depth: int,
) -> sp.Expr:
    orbit = sp.prod(
        _adjoint_factor(
            p_exponent,
            q_exponent,
            discriminant_depth,
            index,
        )
        for index in range(depth)
    )
    return sp.factor(
        3
        * _terminal_seed(
            p_exponent,
            q_exponent,
            discriminant_depth,
        )
        * _phi_two_coefficient(depth)
        * orbit
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
    radial = slope * (depth + 1)
    return radial, radial + 4


def _current_column_certificate() -> dict[str, object]:
    """Check the exact support inequalities behind terminal independence."""

    # For cost 2*m+1 and current offset j, a C-column monomial with
    # deficit t and extra normal order h has
    #
    # G_x = -sigma + 2*j + 2 - 2*t,
    # G_y = G_x + 2*h.
    #
    # The terminal grade is (-sigma-2,-sigma+2).  Offsets -4..-1
    # have no admissible (t,h) in the normalized P^p Q^q C support.
    # Offset zero retains its leading normal-two pivot at radial
    # sigma*m+2, but its possible t=2 terms have h<=1 and therefore
    # cannot equal the terminal normal-four monomial.
    symbolic_support_rows = []
    maximum_extra_normal_at_small_deficit = {
        0: 0,
        1: 0,
        2: 1,
    }
    for offset in range(-4, 1):
        maximum_t_degree = 4 + offset
        projected_pairs = []
        for t_degree in range(maximum_t_degree + 1):
            maximum_extra_normal = (
                maximum_extra_normal_at_small_deficit.get(
                    t_degree,
                    t_degree // 2,
                )
            )
            for extra_normal in range(maximum_extra_normal + 1):
                x_margin = 2 * offset + 4 - 2 * t_degree
                y_margin = (
                    2 * offset
                    + 2 * extra_normal
                    - 2 * t_degree
                )
                if x_margin >= 0 and y_margin >= 0:
                    projected_pairs.append((
                        t_degree,
                        extra_normal,
                    ))
        symbolic_support_rows.append({
            "offset": offset,
            "maximum_t_degree": maximum_t_degree,
            "grade_admissible_pairs_before_factor_support": [
                list(pair) for pair in projected_pairs
            ],
        })
    assert all(
        not row["grade_admissible_pairs_before_factor_support"]
        for row in symbolic_support_rows[:4]
    )
    assert (
        symbolic_support_rows[4][
            "grade_admissible_pairs_before_factor_support"
        ]
        == [[0, 0]]
    )

    # Exact finite-support crosscheck over all residue classes of the
    # canonical multiplier and a broad range of slopes/amplitudes.
    checked_slopes = []
    for slope in range(12, 82):
        case = LowMixedCase(
            name=f"slope_{slope}",
            prefix="positive discriminant depth",
            slope=slope,
            terminal_grade=(-slope - 2, -slope + 2),
            cost_two={},
            cost_three={},
            zero_grade_coefficient=sp.Integer(0),
            core_terminal=sp.Integer(0),
            held_out_depth_twelve=sp.Integer(0),
        )
        for amplitude in range(2, 9):
            cost = 2 * amplitude + 1
            terminal = (
                slope * amplitude,
                slope * amplitude + 4,
            )
            columns = []
            for offset in range(-4, 1):
                column = _c_seed_column(
                    case,
                    cost,
                    slope * amplitude + offset,
                )
                assert column is not None
                columns.append((offset, column[1]))
            assert all(
                not column
                for _offset, column in columns[:4]
            )
            assert columns[4][1]
            assert terminal not in columns[4][1]
            pivot = (
                slope * amplitude + 2,
                slope * amplitude + 4,
            )
            assert columns[4][1].get(pivot, 0) != 0
        checked_slopes.append(slope)
    return {
        "symbolic_grade_rows": symbolic_support_rows,
        "support_conclusion": (
            "Offsets -4,-3,-2,-1 lie below the terminal quotient. "
            "Offset 0 has a nonzero higher normal-two pivot and no "
            "terminal monomial, so its coefficient is forced to zero."
        ),
        "affine_current_dimension": 4,
        "terminal_independent": True,
        "finite_support_crosscheck_slopes": [
            min(checked_slopes),
            max(checked_slopes),
        ],
        "finite_support_crosscheck_amplitudes": [2, 8],
    }


def _representative_rows(maximum_depth: int) -> list[dict[str, object]]:
    expected = {
        0: -sp.Rational(2187, 4194304),
        1: sp.Rational(100442349, 1374389534720),
        2: sp.Rational(
            31381059609,
            180143985094819840,
        ),
    }
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = _terminal_coefficient(0, 5, 2, depth)
        if depth in expected:
            assert coefficient == expected[depth]
        rows.append({
            "depth": depth,
            "cost": 3 + 2 * depth,
            "exponent": list(_terminal_exponent(0, 5, 2, depth)),
            "coefficient": str(coefficient),
        })
    return rows


def _full_projection_witness() -> dict[str, object]:
    from gauge_cone_radial_triangular_staircase import run as staircase

    result = staircase(
        maximum_target_order=6,
        cancel_second_normal=True,
        verify_roundtrips=False,
        compute_logarithms=True,
        normalization_objective="logarithm",
        delayed_c_prefix_terms=[
            (6, 5, 16 * LAMBDA),
            (3, 7, 216 * LAMBDA),
            (0, 9, 729 * LAMBDA),
        ],
        project_to_prefix_ray=True,
        prefix_terminal_grade_override=(-28, -24),
        prefix_slope_override=26,
    )
    projection = result["prefix_candidate_ray_projection"]
    expected_logarithm = {
        3: (
            [26, 30],
            "-2187*lambda/4194304",
        ),
        5: (
            [52, 56],
            "100442349*lambda**2/1374389534720",
        ),
        7: (
            [78, 82],
            "31381059609*lambda**3/180143985094819840",
        ),
    }
    rows = {}
    for cost, (exponent, coefficient) in expected_logarithm.items():
        velocity = [
            row
            for row in projection["source_velocity"][cost - 1]
            if row[0] == [-28, -24]
        ]
        logarithm = [
            row
            for row in projection["source_logarithm"][cost - 1]
            if row[0] == [-28, -24]
        ]
        if cost == 3:
            assert velocity == [[
                [-28, -24],
                exponent,
                "-6561*lambda/4194304",
            ]]
        else:
            assert velocity == []
        assert logarithm == [[
            [-28, -24],
            exponent,
            coefficient,
        ]]
        rows[str(cost)] = {
            "source_velocity": velocity,
            "source_logarithm": logarithm,
        }
    return {
        "verified": True,
        "prefix": "D^2*Q^5*C",
        "rows": rows,
    }


def run(
    maximum_depth: int = 10,
    verify_full_projection: bool = False,
) -> dict[str, object]:
    if maximum_depth < 3:
        raise ValueError("at least four response rows are required")
    p_exponent, q_exponent, discriminant_depth = (0, 5, 2)
    slope = _slope(p_exponent, q_exponent, discriminant_depth)
    depth_symbol = sp.symbols("n", integer=True, nonnegative=True)
    root = sp.solve(
        sp.Eq(
            _adjoint_factor(
                p_exponent,
                q_exponent,
                discriminant_depth,
                sp.symbols("x"),
            ),
            0,
        ),
        sp.symbols("x"),
    )
    assert root == [1 + sp.Rational(2, slope)]
    assert 1 < root[0] < 2
    assert sp.solve(
        sp.Eq(
            _adjoint_factor(
                p_exponent,
                q_exponent,
                discriminant_depth,
                depth_symbol,
            ),
            0,
        ),
        depth_symbol,
    ) == []
    assert [
        _phi_two_coefficient(depth) for depth in range(4)
    ] == [
        sp.Rational(1, 3),
        sp.Rational(1, 30),
        -sp.Rational(1, 1260),
        -sp.Rational(1, 1890),
    ]

    current_columns = _current_column_certificate()
    representative = _representative_rows(maximum_depth)
    full_projection = (
        _full_projection_witness()
        if verify_full_projection
        else {
            "verified": False,
            "replay_flag": "--verify-full-projection",
            "maximum_held_out_cost": 7,
        }
    )
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "discriminant_positive_depth_phi2.v1"
        ),
        "depth_range": "d>=2",
        "cone_range": "a+3*d+3<=2*b, a in {0,1,2}",
        "slope": "sigma=2*a+3*b+5*d+1",
        "zero_grade_letter": {
            "exponent": "(sigma+1,sigma+3)",
            "coefficient": (
                "-9/4*(-3/4)^a*(-1/4)^b*(27/8)^d"
            ),
        },
        "cost_three_terminal": {
            "exponent": "(sigma,sigma+4)",
            "coefficient": (
                "(-3/4)^a*(-1/4)^b*(27/8)^d"
                "*3/64*binomial(d,2)"
            ),
        },
        "adjoint_multiplier": (
            "2*A*(sigma*(n-1)-2)"
        ),
        "adjoint_zero": "1+2/sigma, strictly between 1 and 2",
        "current_column_certificate": current_columns,
        "right_magnus_response": {
            "function": (
                "x/(exp(x)-1)*integral_0^1 "
                "t^2*exp(t^2*x) dt"
            ),
            "nonpolynomial_certificate": (
                "At x=2*pi*i, I_2=(1-I_0)/(4*pi*i) "
                "and Re(I_0)<1."
            ),
        },
        "representative_D2_Q5_rows": representative,
        "full_projected_replay": full_projection,
        "all_order_nontermination": True,
        "limiting_source_rate": "sigma/2",
        "claim_boundary": (
            "Every admissible one-C prefix of exact positive "
            "discriminant depth d>=2 has an infinitely supported "
            "normal-four source ray. Depth one is covered by the "
            "separate depth-one theorem. Prefixes involving C^m "
            "with m>=2 are excluded."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-depth", type=int, default=10)
    parser.add_argument(
        "--verify-full-projection",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            maximum_depth=arguments.maximum_depth,
            verify_full_projection=arguments.verify_full_projection,
        ),
        indent=2,
        sort_keys=True,
    ))
