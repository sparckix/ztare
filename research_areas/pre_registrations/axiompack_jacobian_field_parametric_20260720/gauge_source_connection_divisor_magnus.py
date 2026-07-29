#!/usr/bin/env python3
"""Exceptional-divisor Magnus law for the regular source-only connection."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    inverse_dexp_coefficients,
)


def _degree(value: sp.Expr, variable: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, variable).degree())


def _leading_coefficient(
    value: sp.Expr,
    variable: sp.Symbol,
) -> sp.Rational:
    return sp.Poly(
        value, variable, domain=sp.QQ
    ).LC()


def _bracket(
    left: sp.Expr,
    right: sp.Expr,
    variable: sp.Symbol,
) -> sp.Expr:
    """Coefficient of [left*d/dv, right*d/dv]."""
    return sp.expand(
        left * sp.diff(right, variable)
        - right * sp.diff(left, variable)
    )


def _series_bracket(
    left: list[sp.Expr],
    right: list[sp.Expr],
    maximum_order: int,
    variable: sp.Symbol,
) -> list[sp.Expr]:
    result = [
        sp.Integer(0) for _ in range(maximum_order + 1)
    ]
    for first_order, first in enumerate(
        left[: maximum_order + 1]
    ):
        if first == 0:
            continue
        for second_order, second in enumerate(
            right[: maximum_order + 1 - first_order]
        ):
            if second != 0:
                result[first_order + second_order] += (
                    _bracket(first, second, variable)
                )
    return [sp.expand(value) for value in result]


def _dexp_coefficients(
    maximum_order: int,
    orientation: str,
) -> dict[int, sp.Rational]:
    """Compatibility adapter onto the equation-typed shared primitive."""

    placements = {
        "left": VelocityPlacement.LEFT_MULTIPLY,
        "right": VelocityPlacement.RIGHT_MULTIPLY,
    }
    if orientation not in placements:
        raise ValueError("orientation must be left or right")
    return {
        order: sp.Rational(value.numerator, value.denominator)
        for order, value in enumerate(inverse_dexp_coefficients(
            maximum_order, placements[orientation]
        ))
        if value
    }


def _magnus_coefficients(
    velocity: list[sp.Expr],
    maximum_order: int,
    variable: sp.Symbol,
    orientation: str,
) -> list[sp.Expr]:
    """Solve the dexp recursion coefficient by coefficient."""
    dexp = _dexp_coefficients(
        maximum_order, orientation
    )
    logarithm = [
        sp.Integer(0) for _ in range(maximum_order + 1)
    ]
    for derivative_order in range(maximum_order):
        truncated_logarithm = logarithm[
            : derivative_order + 1
        ]
        truncated_velocity = velocity[
            : derivative_order + 1
        ]
        result = truncated_velocity[derivative_order]
        nested = truncated_velocity
        for bracket_depth in range(
            1, derivative_order + 1
        ):
            nested = _series_bracket(
                truncated_logarithm,
                nested,
                derivative_order,
                variable,
            )
            if bracket_depth in dexp:
                result += (
                    dexp[bracket_depth]
                    * nested[derivative_order]
                )
        logarithm[derivative_order + 1] = sp.expand(
            result / (derivative_order + 1)
        )
    return logarithm


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def run(maximum_order: int = 11) -> dict[str, object]:
    if maximum_order < 5:
        raise ValueError("maximum_order must be at least five")
    data = source_only_connection()
    s, v, t, _ = data["symbols"]
    gamma = data["gamma"]
    source_only = data["source_only"]

    restricted = sp.factor(
        source_only[0].subs(
            t, -1 + sp.Rational(3, 2) * v
        )
    )
    normal_component = sp.factor(
        source_only[1]
        - sp.Rational(3, 2) * source_only[0]
    )
    assert sp.factor(
        normal_component.subs(
            t, -1 + sp.Rational(3, 2) * v
        )
    ) == 0
    assert sp.factor(
        gamma.subs(
            t, -1 + sp.Rational(3, 2) * v
        )
    ) == 0

    denominator = sp.factor(sp.denom(restricted))
    assert denominator.subs(s, 0) != 0
    assert not ({v} & denominator.free_symbols)
    assert _degree(sp.numer(restricted), v) == 3

    velocity_series = sp.series(
        restricted, s, 0, maximum_order
    ).removeO().expand()
    velocity = [
        sp.Poly(
            velocity_series, s
        ).coeff_monomial(s**order)
        for order in range(maximum_order)
    ]
    assert all(
        _degree(value, v) == 3 for value in velocity
    )

    seed = velocity[0]
    first = velocity[1]
    second = velocity[2]
    iterated = _bracket(seed, first, v)
    assert _degree(iterated, v) == 3
    seed_lead = _leading_coefficient(seed, v)
    iterated_rows = []
    for depth in range(1, maximum_order - 1):
        expected_degree = (
            3 if depth == 1 else 2 * depth
        )
        assert _degree(iterated, v) == expected_degree
        leading = _leading_coefficient(iterated, v)
        iterated_rows.append({
            "depth": depth,
            "degree": expected_degree,
            "leading_coefficient": str(leading),
            "sha256": _sha(iterated),
        })
        if depth < maximum_order - 2:
            next_iterated = _bracket(
                seed, iterated, v
            )
            next_leading = _leading_coefficient(
                next_iterated, v
            )
            if depth >= 2:
                assert sp.factor(
                    next_leading
                    - seed_lead
                    * (2 * depth - 3)
                    * leading
                ) == 0
            iterated = next_iterated

    y = sp.symbols("y")
    to_y = lambda value: sp.expand(  # noqa: E731
        2 * value.subs(v, (y - 3) / 2)
    )
    seed_y = to_y(seed)
    first_y = to_y(first)
    second_y = to_y(second)
    assert sp.expand(seed_y - y**3 / 6) == 0
    assert sp.expand(
        first_y
        - (7 * y**3 - 9 * y + 10) / 48
    ) == 0
    assert sp.expand(
        second_y - y**2 * (8 * y + 15) / 288
    ) == 0

    # The source-only cascade is not invariant under the admissible target
    # gauge.  The Hamiltonian P^3 has field (0,-3P^2), belongs to the full
    # target lift ideals, and has a polynomial source pullback.  Its exact
    # regular coefficient below cancels the cubic divisor term for every s.
    family = data["family"]
    jacobian = data["jacobian"]
    determinant = data["determinant"]
    p_cubed_pullback = (
        sp.cancel(
            3 * jacobian[0, 1] * family[0] ** 2
            / determinant
        ),
        sp.cancel(
            -3 * jacobian[0, 0] * family[0] ** 2
            / determinant
        ),
    )
    p_cubed_restricted_y = sp.factor(
        2
        * p_cubed_pullback[0].subs(
            t, -1 + sp.Rational(3, 2) * v
        ).subs(v, (y - 3) / 2)
    )
    source_restricted_y = sp.factor(
        2 * restricted.subs(v, (y - 3) / 2)
    )
    source_cubic = sp.Poly(
        source_restricted_y, y
    ).coeff_monomial(y**3)
    control_cubic = sp.Poly(
        p_cubed_restricted_y, y
    ).coeff_monomial(y**3)
    target_coefficient = sp.factor(
        source_cubic / control_cubic
    )
    expected_target_coefficient = sp.factor(
        -192
        * (s**2 - 3 * s - 8)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    assert sp.factor(
        target_coefficient - expected_target_coefficient
    ) == 0
    assert target_coefficient.subs(s, 0) == -sp.Rational(
        1, 36
    )

    controlled_source = tuple(
        sp.cancel(
            source_only[index]
            - target_coefficient * p_cubed_pullback[index]
        )
        for index in range(2)
    )
    controlled_restricted_y = sp.factor(
        2
        * controlled_source[0].subs(
            t, -1 + sp.Rational(3, 2) * v
        ).subs(v, (y - 3) / 2)
    )
    expected_controlled_restriction = sp.factor(
        s
        * (
            9 * s**2 * y
            - 15 * s**2
            - 144 * y
            + 160
        )
        / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    assert sp.factor(
        controlled_restricted_y
        - expected_controlled_restriction
    ) == 0
    assert _degree(controlled_restricted_y, y) == 1
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in controlled_source
    )
    assert controlled_source[0].subs({v: 0, t: 0}) == 0
    controlled_second_axis = sp.factor(
        controlled_source[1].subs(t, 0)
    )
    assert controlled_second_axis.subs(v, 0) == 0
    assert sp.diff(
        controlled_second_axis, v
    ).subs(v, 0) == 0
    controlled_normal = sp.cancel(
        (
            controlled_source[1]
            - sp.Rational(3, 2) * controlled_source[0]
        )
        / gamma
    )
    assert not ({v, t} & sp.denom(controlled_normal).free_symbols)
    controlled_gamma = sp.factor(
        controlled_source[1]
        - sp.Rational(3, 2) * controlled_source[0]
    )
    weighted_divergence = sp.factor(
        (
            sp.diff(
                gamma**2 * controlled_source[0], v
            )
            + sp.Rational(3, 2)
            * sp.diff(
                gamma**2 * controlled_source[0], t
            )
            + sp.diff(
                gamma**2 * controlled_gamma, t
            )
        )
        / gamma**2
    )
    assert weighted_divergence == 0

    controlled_series = sp.series(
        controlled_restricted_y, s, 0, maximum_order
    ).removeO().expand()
    controlled_velocity = [
        sp.Poly(
            controlled_series, s
        ).coeff_monomial(s**order)
        for order in range(maximum_order)
    ]
    controlled_magnus_degrees: dict[str, list[int]] = {}
    for orientation in ("left", "right"):
        controlled_logarithm = _magnus_coefficients(
            controlled_velocity,
            maximum_order,
            y,
            orientation,
        )
        controlled_degrees = [
            _degree(
                controlled_logarithm[order], y
            )
            for order in range(1, maximum_order + 1)
        ]
        assert all(
            degree <= 1 for degree in controlled_degrees
        )
        controlled_magnus_degrees[orientation] = (
            controlled_degrees
        )

    # The complete lowest-weight target image is generated by P^3 and P*Q.
    # Using both controls removes the linear term as well and leaves a
    # translation connection on the divisor.
    scaling_pullback = data["scaling_pullback"]
    constant_p_cubed_coefficient = sp.factor(
        96
        * (s**2 - 12 * s + 16)
        / (
            (s - 6) ** 3
            * (s - 4) ** 2
            * (s + 4) ** 2
        )
    )
    constant_scaling_coefficient = sp.factor(
        2 * s / ((s - 4) * (s + 4))
    )
    constant_source = tuple(
        sp.cancel(
            source_only[index]
            - constant_p_cubed_coefficient
            * p_cubed_pullback[index]
            - constant_scaling_coefficient
            * scaling_pullback[index]
        )
        for index in range(2)
    )
    constant_restricted_y = sp.factor(
        2
        * constant_source[0].subs(
            t, -1 + sp.Rational(3, 2) * v
        ).subs(v, (y - 3) / 2)
    )
    expected_constant_restriction = sp.factor(
        160
        * s
        / (3 * (s - 4) ** 2 * (s + 4) ** 2)
    )
    assert sp.factor(
        constant_restricted_y
        - expected_constant_restriction
    ) == 0
    assert _degree(constant_restricted_y, y) == 0
    assert constant_p_cubed_coefficient.subs(
        s, 0
    ) == -sp.Rational(1, 36)
    assert constant_scaling_coefficient.subs(s, 0) == 0
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in constant_source
    )
    assert constant_source[0].subs({v: 0, t: 0}) == 0
    constant_second_axis = sp.factor(
        constant_source[1].subs(t, 0)
    )
    assert constant_second_axis.subs(v, 0) == 0
    assert sp.diff(
        constant_second_axis, v
    ).subs(v, 0) == 0
    constant_gamma = sp.factor(
        constant_source[1]
        - sp.Rational(3, 2) * constant_source[0]
    )
    constant_weighted_divergence = sp.factor(
        (
            sp.diff(gamma**2 * constant_source[0], v)
            + sp.Rational(3, 2)
            * sp.diff(gamma**2 * constant_source[0], t)
            + sp.diff(gamma**2 * constant_gamma, t)
        )
        / gamma**2
    )
    assert constant_weighted_divergence == 0

    # Q^2 has zero divisor action but restores the campaign's normalized
    # first target Hamiltonian K_1=-Q^2/4-P^3/36.  The resulting source
    # connection begins at positive parameter order globally.
    q_squared_pullback = (
        sp.cancel(
            2
            * jacobian[1, 1]
            * family[1]
            / determinant
        ),
        sp.cancel(
            -2
            * jacobian[1, 0]
            * family[1]
            / determinant
        ),
    )
    normalized_source = tuple(
        sp.cancel(
            constant_source[index]
            + sp.Rational(1, 4)
            * q_squared_pullback[index]
        )
        for index in range(2)
    )
    assert all(
        sp.factor(value.subs(s, 0)) == 0
        for value in normalized_source
    )
    normalized_restricted_y = sp.factor(
        2
        * normalized_source[0].subs(
            t, -1 + sp.Rational(3, 2) * v
        ).subs(v, (y - 3) / 2)
    )
    assert sp.factor(
        normalized_restricted_y
        - expected_constant_restriction
    ) == 0
    assert all(
        not ({v, t} & sp.denom(value).free_symbols)
        for value in normalized_source
    )
    assert normalized_source[0].subs({v: 0, t: 0}) == 0
    normalized_second_axis = sp.factor(
        normalized_source[1].subs(t, 0)
    )
    assert normalized_second_axis.subs(v, 0) == 0
    assert sp.diff(
        normalized_second_axis, v
    ).subs(v, 0) == 0

    first_chain = first
    second_chain = second
    chain_ratio_rows = []
    for depth in range(1, maximum_order - 2):
        first_chain = _bracket(
            seed, first_chain, v
        )
        if depth > 1:
            second_chain = _bracket(
                seed, second_chain, v
            )
        if depth >= 2:
            assert _degree(first_chain, v) == 2 * depth
            assert _degree(second_chain, v) == 2 * depth
            ratio = sp.factor(
                _leading_coefficient(second_chain, v)
                / _leading_coefficient(first_chain, v)
            )
            assert ratio == -sp.Rational(1, 2)
            chain_ratio_rows.append({
                "bracket_depth": depth,
                "second_chain_over_first_chain": str(
                    ratio
                ),
            })

    orientation_rows: dict[str, object] = {}
    for orientation in ("left", "right"):
        logarithm = _magnus_coefficients(
            velocity,
            maximum_order,
            v,
            orientation,
        )
        degrees = {
            str(order): _degree(logarithm[order], v)
            for order in range(1, maximum_order + 1)
        }
        for order in range(4, maximum_order + 1, 2):
            assert degrees[str(order)] == 2 * order - 4
        orientation_rows[orientation] = {
            "degrees": degrees,
            "even_order_top_law_replayed": True,
            "sha256": {
                str(order): _sha(logarithm[order])
                for order in range(
                    1, maximum_order + 1
                )
            },
        }

    bernoulli_rows = []
    for even_depth in range(
        2, maximum_order - 1, 2
    ):
        coefficient = sp.Rational(
            sp.bernoulli(even_depth),
            2 * sp.factorial(even_depth),
        )
        assert coefficient != 0
        bernoulli_rows.append({
            "bracket_depth": even_depth,
            "logarithm_order": even_depth + 2,
            "combined_first_second_coefficient": str(
                coefficient
            ),
        })

    return {
        "schema": (
            "axiompack."
            "jacobian_source_connection_divisor_magnus.v1"
        ),
        "maximum_replayed_order": maximum_order,
        "exceptional_divisor": "gamma=0",
        "restricted_connection_degree": 3,
        "restricted_connection_regular_at_s_zero": True,
        "velocity_coefficient_degrees": [
            _degree(value, v) for value in velocity
        ],
        "witt_coordinate": "y=2*v+3",
        "first_three_witt_fields": {
            "A": str(seed_y),
            "B": str(first_y),
            "C": str(second_y),
        },
        "first_bracket_degree": 3,
        "iterated_brackets": iterated_rows,
        "top_chain_ratio": chain_ratio_rows,
        "bernoulli_linear_terms": bernoulli_rows,
        "all_order_coefficient_recurrence": {
            "initial_positive_coefficient": "a_1=1/12",
            "recurrence": (
                "a_m=(sum_{i=1}^{m-1} "
                "a_i*a_(m-i))/(2*m+1)"
            ),
            "sign_relation": "c_m=(-1)^(m-1)*a_m",
            "origin": (
                "x*h'=h-h^2+x^2/4 for "
                "h=(x/2)*coth(x/2)"
            ),
        },
        "magnus_orientations": orientation_rows,
        "admissible_target_control": {
            "hamiltonian": "a(s)*P^3",
            "coefficient": str(target_coefficient),
            "coefficient_at_s_zero": str(
                target_coefficient.subs(s, 0)
            ),
            "regular_at_s_zero": (
                sp.denom(target_coefficient).subs(s, 0) != 0
            ),
            "target_lift_ideals": (
                "dotP=0; dotQ=-3*a(s)*P^2"
            ),
            "source_pullback_polynomial": True,
            "source_lift_ideals": True,
            "weighted_divergence_zero": True,
            "gamma_tangent": True,
            "controlled_divisor_connection": str(
                controlled_restricted_y
            ),
            "controlled_divisor_degree": _degree(
                controlled_restricted_y, y
            ),
            "controlled_lie_algebra": (
                "span{d/dy,y*d/dy}"
            ),
            "controlled_magnus_degrees": (
                controlled_magnus_degrees
            ),
            "consequence": (
                "Every divisor Magnus coefficient remains affine; "
                "the source-only Bernoulli-Witt escape is removable "
                "by a regular admissible target gauge."
            ),
        },
        "complete_lowest_weight_target_normal_form": {
            "hamiltonian": "a(s)*P^3+b(s)*P*Q",
            "p_cubed_coefficient": str(
                constant_p_cubed_coefficient
            ),
            "scaling_coefficient": str(
                constant_scaling_coefficient
            ),
            "coefficients_at_s_zero": [
                str(constant_p_cubed_coefficient.subs(s, 0)),
                str(constant_scaling_coefficient.subs(s, 0)),
            ],
            "regular_at_s_zero": True,
            "target_lift_ideals": (
                "dotP=b(s)*P; "
                "dotQ=-3*a(s)*P^2-b(s)*Q"
            ),
            "source_pullback_polynomial": True,
            "source_lift_ideals": True,
            "weighted_divergence_zero": True,
            "controlled_divisor_connection": str(
                constant_restricted_y
            ),
            "controlled_divisor_degree": _degree(
                constant_restricted_y, y
            ),
            "controlled_lie_algebra": "span{d/dy}",
            "consequence": (
                "The complete lowest-weight target controls put "
                "the divisor connection in the abelian translation "
                "algebra for every parameter value."
            ),
        },
        "normalized_first_order_target_control": {
            "hamiltonian": (
                "a(s)*P^3+b(s)*P*Q-Q^2/4"
            ),
            "first_hamiltonian": "-P^3/36-Q^2/4",
            "source_connection_vanishes_at_s_zero": True,
            "q_squared_divisor_action": 0,
            "controlled_divisor_connection": str(
                normalized_restricted_y
            ),
            "source_pullback_polynomial": True,
            "source_lift_ideals": True,
            "consequence": (
                "The translation normal form is compatible with "
                "the campaign's fixed first-order target slice."
            ),
        },
        "all_order_candidate": (
            "For every even n>=4, the exceptional-divisor "
            "restriction of the source-only logarithm has "
            "degree exactly 2*n-4."
        ),
        "claim_boundary": (
            "The replay checks finite orders and the exact "
            "leading-coefficient recurrence. The all-order "
            "step uses the positive convolution recurrence "
            "for the even generating-function coefficients "
            "and the Witt-index word bound. The exact P^3 "
            "control proves that the same divisor connection "
            "has an affine representative in the full "
            "admissible target gauge. Hence the source-only "
            "theorem cannot supply a gauge-minimized lower "
            "bound."
        ),
    }


if __name__ == "__main__":
    selected_order = (
        int(sys.argv[1]) if len(sys.argv) > 1 else 11
    )
    print(json.dumps(
        run(selected_order),
        indent=2,
        sort_keys=True,
    ))
