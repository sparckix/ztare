#!/usr/bin/env python3
"""All-order response for one positive discriminant factor.

At fixed target weight, write ``D = 4*P^3 + 27*Q^2``.  The three
depth-one residue families are ``P^a*Q^b*D*C`` with ``a=0,1,2``.
Their cost-three terminal transfer is nonzero and all three have the
same right-Magnus ``phi_2`` response after division by the adjoint
orbit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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


@dataclass(frozen=True)
class DepthOneResidue:
    p_exponent: int
    minimum_q_exponent: int
    factored_terminal: sp.Expr


B = sp.symbols("b", integer=True, positive=True)
DEPTH_ONE_RESIDUES = (
    DepthOneResidue(
        p_exponent=0,
        minimum_q_exponent=3,
        factored_terminal=-sp.Rational(81, 512) * B,
    ),
    DepthOneResidue(
        p_exponent=1,
        minimum_q_exponent=4,
        factored_terminal=(
            sp.Rational(27, 2048) * (9 * B + 20)
        ),
    ),
    DepthOneResidue(
        p_exponent=2,
        minimum_q_exponent=4,
        factored_terminal=(
            -sp.Rational(81, 8192) * (9 * B + 28)
        ),
    ),
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


def _slope(p_exponent: int, q_exponent: int) -> int:
    return 2 * p_exponent + 3 * q_exponent + 6


def _zero_grade_coefficient(
    p_exponent: int,
    q_exponent: int,
) -> sp.Rational:
    return sp.Rational(
        (-1) ** (p_exponent + q_exponent + 1)
        * 3 ** (p_exponent + 5),
        2 ** (2 * p_exponent + 2 * q_exponent + 5),
    )


def _terminal_seed(
    p_exponent: int,
    q_exponent: int,
) -> sp.Rational:
    residue = DEPTH_ONE_RESIDUES[p_exponent]
    return sp.Rational(
        residue.factored_terminal.subs(B, q_exponent)
        * (-sp.Rational(1, 4)) ** q_exponent
    )


def _adjoint_factor(
    p_exponent: int,
    q_exponent: int,
    depth: int | sp.Expr,
) -> sp.Expr:
    slope = _slope(p_exponent, q_exponent)
    return sp.factor(
        _zero_grade_coefficient(
            p_exponent,
            q_exponent,
        )
        * 2
        * (slope * (depth - 1) - 3)
    )


def _terminal_coefficient(
    p_exponent: int,
    q_exponent: int,
    depth: int,
    prefix_scale: sp.Expr = sp.Integer(1),
) -> sp.Expr:
    orbit = sp.prod(
        prefix_scale
        * _adjoint_factor(
            p_exponent,
            q_exponent,
            index,
        )
        for index in range(depth)
    )
    velocity_seed = (
        3
        * prefix_scale
        * _terminal_seed(p_exponent, q_exponent)
    )
    return sp.factor(
        velocity_seed
        * _phi_two_coefficient(depth)
        * orbit
    )


def _terminal_exponent(
    p_exponent: int,
    q_exponent: int,
    depth: int,
) -> tuple[int, int]:
    slope = _slope(p_exponent, q_exponent)
    return (
        slope - 1 + slope * depth,
        slope + 3 + slope * depth,
    )


def _current_column_certificate() -> dict[str, object]:
    checked_slopes = []
    for slope in range(15, 81):
        case = LowMixedCase(
            name=f"slope_{slope}",
            prefix="symbolic depth-one residue",
            slope=slope,
            terminal_grade=(-slope - 4, -slope),
            cost_two={},
            cost_three={},
            zero_grade_coefficient=sp.Integer(0),
            core_terminal=sp.Integer(0),
            held_out_depth_twelve=sp.Integer(0),
        )
        for amplitude in range(2, 9):
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
                for offset in (-4, -3, -2)
            )
            for offset in (-1, 0):
                assert columns[offset] is not None
                pivot = (
                    slope * amplitude + offset + 2,
                    slope * amplitude + offset + 4,
                )
                assert columns[offset][1].get(pivot, 0) != 0
            terminal = (
                slope * amplitude - 1,
                slope * amplitude + 3,
            )
            assert all(
                column is not None
                and terminal not in column[1]
                for column in columns.values()
            )
        checked_slopes.append(slope)
    return {
        "symbolic_support_argument": (
            "Offsets -4,-3,-2 fall below the terminal projection. "
            "Offsets -1,0 have nonzero normal-two leading pivots and "
            "are forced to zero. No current column contains the "
            "normal-four terminal monomial."
        ),
        "finite_support_crosscheck_slopes": [
            min(checked_slopes),
            max(checked_slopes),
        ],
        "finite_support_crosscheck_amplitudes": [2, 8],
        "affine_current_dimension": 3,
        "terminal_independent": True,
    }


def _symbolic_checks() -> list[dict[str, object]]:
    depth = sp.symbols("n", integer=True, nonnegative=True)
    rows = []
    for residue in DEPTH_ONE_RESIDUES:
        p_exponent = residue.p_exponent
        minimum_b = residue.minimum_q_exponent
        assert all(
            residue.factored_terminal.subs(B, integer_b) != 0
            for integer_b in range(minimum_b, 50)
        )
        integer_b = minimum_b
        slope = _slope(p_exponent, integer_b)
        root = sp.solve(
            sp.Eq(
                _adjoint_factor(
                    p_exponent,
                    integer_b,
                    sp.symbols("x"),
                ),
                0,
            ),
            sp.symbols("x"),
        )
        assert root == [1 + sp.Rational(3, slope)]
        assert 1 < root[0] < 2
        assert sp.solve(
            sp.Eq(
                _adjoint_factor(
                    p_exponent,
                    integer_b,
                    depth,
                ),
                0,
            ),
            depth,
        ) == []
        rows.append({
            "p_exponent": p_exponent,
            "minimum_q_exponent": minimum_b,
            "factored_cost_three_terminal": str(
                residue.factored_terminal
            ),
            "restored_cost_three_terminal": (
                f"(-1/4)^b*({residue.factored_terminal})"
            ),
            "slope": f"2*{p_exponent}+3*b+6",
            "adjoint_zero": "1+3/slope",
        })
    return rows


def _representative_rows(
    maximum_depth: int,
) -> list[dict[str, object]]:
    # H_pre = Q^3*D*C/4.
    expected = {
        0: sp.Rational(243, 131072),
        1: -sp.Rational(531441, 2684354560),
        2: -sp.Rational(
            129140163,
            153931627888640,
        ),
        3: -sp.Rational(
            31381059609,
            78812993478983680,
        ),
    }
    rows = []
    for depth in range(maximum_depth + 1):
        coefficient = _terminal_coefficient(
            0,
            3,
            depth,
            prefix_scale=sp.Rational(1, 4),
        )
        if depth in expected:
            assert coefficient == expected[depth]
        rows.append({
            "depth": depth,
            "cost": 3 + 2 * depth,
            "exponent": list(_terminal_exponent(0, 3, depth)),
            "coefficient": str(coefficient),
            "nonzero": coefficient != 0,
        })
    return rows


def _full_projection_witness() -> dict[str, object]:
    from gauge_cone_radial_triangular_staircase import run as staircase

    parameter = sp.symbols("lambda")
    result = staircase(
        maximum_target_order=8,
        cancel_second_normal=True,
        verify_roundtrips=False,
        compute_logarithms=True,
        normalization_objective="logarithm",
        delayed_c_prefix_terms=[
            (3, 3, parameter),
            (0, 5, sp.Rational(27, 4) * parameter),
        ],
        project_to_prefix_ray=True,
        prefix_terminal_grade_override=(-19, -15),
        prefix_slope_override=15,
    )
    projection = result["prefix_candidate_ray_projection"]
    assert projection["weight"] == 15
    assert projection["slope"] == 15
    expected = {
        3: ((14, 18), sp.Rational(243, 131072)),
        5: (
            (29, 33),
            -sp.Rational(531441, 2684354560),
        ),
        7: (
            (44, 48),
            -sp.Rational(
                129140163,
                153931627888640,
            ),
        ),
        9: (
            (59, 63),
            -sp.Rational(
                31381059609,
                78812993478983680,
            ),
        ),
    }
    verified_rows = {}
    for cost, (exponent, coefficient) in expected.items():
        logarithm_rows = [
            row
            for row in projection["source_logarithm"][cost - 1]
            if row[1] == list(exponent)
        ]
        assert logarithm_rows == [[
            [-19, -15],
            list(exponent),
            str(coefficient * parameter ** ((cost - 1) // 2)),
        ]]
        verified_rows[str(cost)] = logarithm_rows
    for cost in (5, 7, 9):
        assert all(
            row[0] != [-19, -15]
            for row in projection["source_velocity"][cost - 1]
        )
    return {
        "verified": True,
        "equal_weight_prefix": (
            "P^3*Q^3*C + 27*Q^5*C/4 = Q^3*D*C/4"
        ),
        "terminal_rows": verified_rows,
        "zero_terminal_velocity_costs": [5, 7, 9],
    }


def run(
    maximum_depth: int = 30,
    verify_full_projection: bool = False,
) -> dict[str, object]:
    if maximum_depth < 3:
        raise ValueError("four response coefficients are required")
    assert [
        _phi_two_coefficient(depth)
        for depth in range(4)
    ] == [
        sp.Rational(1, 3),
        sp.Rational(1, 30),
        -sp.Rational(1, 1260),
        -sp.Rational(1, 1890),
    ]
    symbolic_rows = _symbolic_checks()
    representative = _representative_rows(maximum_depth)
    assert all(row["nonzero"] for row in representative[:4])
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "discriminant_depth_one_phi2.v1"
        ),
        "discriminant": "D=4*P^3+27*Q^2",
        "residue_families": symbolic_rows,
        "current_quotient": _current_column_certificate(),
        "right_magnus_response": {
            "function": (
                "phi_2(x)=x/(exp(x)-1)"
                "*integral_0^1 t^2*exp(t^2*x)dt"
            ),
            "first_coefficients": [
                "1/3",
                "1/30",
                "-1/1260",
                "-1/1890",
            ],
            "nonpolynomial_certificate": (
                "I_2=(exp(x)-I_0)/(2*x); at x=2*pi*i, "
                "Re(I_0)<1, so I_2 is nonzero and phi_2 has "
                "a nonremovable pole."
            ),
        },
        "representative": {
            "prefix": "Q^3*D*C/4",
            "rows": representative,
            "full_projection": (
                _full_projection_witness()
                if verify_full_projection
                else {
                    "verified": False,
                    "replay_flag": "--verify-full-projection",
                    "held_out_cost": 9,
                }
            ),
        },
        "claim_boundary": (
            "All-order terminal nontermination for every admissible "
            "one-C multiplier of exact discriminant depth one. "
            "Depth at least two and powers C^m with m>=2 are outside "
            "the result."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-full-projection",
        action="store_true",
    )
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            verify_full_projection=(
                arguments.verify_full_projection
            )
        ),
        indent=2,
        sort_keys=True,
    ))
