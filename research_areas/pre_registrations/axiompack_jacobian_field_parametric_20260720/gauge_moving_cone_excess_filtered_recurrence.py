#!/usr/bin/env python3
"""Exact excess-filtered source Magnus recurrence experiment."""

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
from gauge_controlled_global_magnus import (  # noqa: E402
    _bracket as _source_bracket,
)
from gauge_moving_lie_cone_magnus import (  # noqa: E402
    _equal,
    _formal_ops,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    inverse_dexp_coefficients,
    magnus_from_velocity,
)
from ztare.common.symbolic_witness import (  # noqa: E402
    find_linear_recurrence,
)


Pair = tuple[sp.Expr, sp.Expr]
Prefix = tuple[dict[int, sp.Expr], dict[int, Pair]]
Exponent = tuple[int, int]
SparsePolynomial = dict[Exponent, sp.Expr]
SparsePair = tuple[SparsePolynomial, SparsePolynomial]


def _adapt(
    pair: Pair,
    source_v: sp.Symbol,
    source_t: sp.Symbol,
    adapted_v: sp.Symbol,
    adapted_g: sp.Symbol,
) -> Pair:
    first = sp.expand(pair[0].subs({
        source_v: adapted_v,
        source_t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }))
    second = sp.expand(pair[1].subs({
        source_v: adapted_v,
        source_t: (
            adapted_g + sp.Rational(3, 2) * adapted_v
        ),
    }) - sp.Rational(3, 2) * first)
    return first, second


def _project(
    pair: Pair,
    first: sp.Symbol,
    second: sp.Symbol,
    minimum_degree: int,
) -> Pair:
    return tuple(
        sp.expand(sum(
            coefficient * first**exponent[0] * second**exponent[1]
            for exponent, coefficient in sp.Poly(
                component, first, second
            ).terms()
            if sum(exponent) >= minimum_degree
        ))
        for component in pair
    )  # type: ignore[return-value]


def _add(left: Pair, right: Pair) -> Pair:
    return (
        sp.expand(left[0] + right[0]),
        sp.expand(left[1] + right[1]),
    )


def _scale(value: Pair, scalar: sp.Expr) -> Pair:
    return (
        sp.expand(scalar * value[0]),
        sp.expand(scalar * value[1]),
    )


def _to_sparse(
    pair: Pair,
    first: sp.Symbol,
    second: sp.Symbol,
    minimum_degree: int,
) -> SparsePair:
    return tuple(
        {
            exponent: sp.expand(coefficient)
            for exponent, coefficient in sp.Poly(
                component, first, second
            ).terms()
            if sum(exponent) >= minimum_degree
            and coefficient != 0
        }
        for component in pair
    )  # type: ignore[return-value]


def _from_sparse(
    pair: SparsePair,
    first: sp.Symbol,
    second: sp.Symbol,
) -> Pair:
    return tuple(
        sp.expand(sum(
            coefficient
            * first**exponent[0]
            * second**exponent[1]
            for exponent, coefficient in component.items()
        ))
        for component in pair
    )  # type: ignore[return-value]


def _sparse_add(
    left: SparsePair,
    right: SparsePair,
) -> SparsePair:
    result = []
    for component in range(2):
        values = dict(left[component])
        for exponent, coefficient in right[component].items():
            values[exponent] = (
                values.get(exponent, sp.Integer(0))
                + coefficient
            )
        result.append({
            exponent: sp.expand(coefficient)
            for exponent, coefficient in values.items()
            if sp.expand(coefficient) != 0
        })
    return result[0], result[1]


def _sparse_scale(
    value: SparsePair,
    scalar: sp.Expr,
) -> SparsePair:
    return tuple(
        {
            exponent: sp.expand(scalar * coefficient)
            for exponent, coefficient in component.items()
            if sp.expand(scalar * coefficient) != 0
        }
        for component in value
    )  # type: ignore[return-value]


def _sparse_bracket(
    left: SparsePair,
    right: SparsePair,
    minimum_degree: int,
) -> SparsePair:
    result: list[dict[Exponent, sp.Expr]] = [{}, {}]

    def add_term(
        component: int,
        left_exponent: Exponent,
        right_exponent: Exponent,
        coefficient: sp.Expr,
        derivative: int,
    ) -> None:
        if right_exponent[derivative] == 0:
            return
        exponent = (
            left_exponent[0]
            + right_exponent[0]
            - (1 if derivative == 0 else 0),
            left_exponent[1]
            + right_exponent[1]
            - (1 if derivative == 1 else 0),
        )
        if sum(exponent) < minimum_degree:
            return
        term = (
            coefficient * right_exponent[derivative]
        )
        result[component][exponent] = (
            result[component].get(exponent, sp.Integer(0))
            + term
        )

    for component in range(2):
        for left_exponent, left_coefficient in left[0].items():
            for right_exponent, right_coefficient in right[
                component
            ].items():
                add_term(
                    component,
                    left_exponent,
                    right_exponent,
                    left_coefficient * right_coefficient,
                    0,
                )
        for left_exponent, left_coefficient in left[1].items():
            for right_exponent, right_coefficient in right[
                component
            ].items():
                add_term(
                    component,
                    left_exponent,
                    right_exponent,
                    left_coefficient * right_coefficient,
                    1,
                )
        for right_exponent, right_coefficient in right[0].items():
            for left_exponent, left_coefficient in left[
                component
            ].items():
                add_term(
                    component,
                    right_exponent,
                    left_exponent,
                    -right_coefficient * left_coefficient,
                    0,
                )
        for right_exponent, right_coefficient in right[1].items():
            for left_exponent, left_coefficient in left[
                component
            ].items():
                add_term(
                    component,
                    right_exponent,
                    left_exponent,
                    -right_coefficient * left_coefficient,
                    1,
                )
    return tuple(
        {
            exponent: sp.expand(coefficient)
            for exponent, coefficient in values.items()
            if sp.expand(coefficient) != 0
        }
        for values in result
    )  # type: ignore[return-value]


def _filtered_series_bracket(
    logarithm: list[SparsePair],
    derivative_series: list[SparsePair],
    maximum_order: int,
) -> list[SparsePair]:
    zero: SparsePair = ({}, {})
    result = [zero for _ in range(maximum_order + 1)]
    for left_order, left in enumerate(
        logarithm[: maximum_order + 1]
    ):
        if left == zero:
            continue
        for right_order, right in enumerate(
            derivative_series[: maximum_order + 1 - left_order]
        ):
            if right == zero:
                continue
            order = left_order + right_order
            bracket = _sparse_bracket(
                left,
                right,
                4 * (order + 1) - 6,
            )
            result[order] = _sparse_add(
                result[order], bracket
            )
    return result


def _filtered_magnus(
    velocity: list[Pair],
    maximum_log_order: int,
    first: sp.Symbol,
    second: sp.Symbol,
) -> list[SparsePair]:
    zero_pair = (sp.Integer(0), sp.Integer(0))
    padded_velocity = list(velocity) + [
        zero_pair
        for _ in range(maximum_log_order - len(velocity))
    ]
    padded_velocity = [
        _to_sparse(
            value,
            first,
            second,
            4 * (order + 1) - 6,
        )
        for order, value in enumerate(padded_velocity)
    ]
    zero: SparsePair = ({}, {})
    logarithm = [zero for _ in range(maximum_log_order + 1)]
    inverse = inverse_dexp_coefficients(
        maximum_log_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for derivative_order in range(maximum_log_order):
        result = padded_velocity[derivative_order]
        nested = padded_velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _filtered_series_bracket(
                prefix,
                nested,
                derivative_order,
            )
            if inverse[depth]:
                result = _sparse_add(
                    result,
                    _sparse_scale(
                        nested[derivative_order],
                        sp.Rational(
                            inverse[depth].numerator,
                            inverse[depth].denominator,
                        ),
                    ),
                )
        logarithm[derivative_order + 1] = _sparse_scale(
            result,
            sp.Rational(1, derivative_order + 1),
        )
    return logarithm


def _full_prefix_crosscheck(
    velocity: list[Pair],
    filtered: list[Pair],
    first: sp.Symbol,
    second: sp.Symbol,
) -> None:
    zero = (sp.Integer(0), sp.Integer(0))
    padded = list(velocity) + [zero] * (8 - len(velocity))
    ops = _formal_ops(
        padded[0],
        lambda left, right: _source_bracket(
            left, right, first, second
        ),
    )
    full = magnus_from_velocity(
        padded,
        8,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for order in range(1, 9):
        projected = _project(
            full[order],
            first,
            second,
            4 * order - 6,
        )
        assert _equal(projected, filtered[order])


def _z_scalar(
    shell: Pair,
    order: int,
    first: sp.Symbol,
    second: sp.Symbol,
) -> sp.Expr:
    first_power = 3 * order - 5
    second_power = order - 1
    scalar = sp.expand(
        sp.Poly(shell[0], first, second).coeff_monomial(
            first**first_power * second**second_power
        )
    )
    expected_second = (
        -sp.Rational(first_power, order + 2)
        * scalar
        * first**(first_power - 1)
        * second**order
    )
    actual_second = sp.expand(
        sp.Poly(shell[1], first, second).coeff_monomial(
            first**(first_power - 1) * second**order
        )
        * first**(first_power - 1)
        * second**order
    )
    assert sp.expand(actual_second - expected_second) == 0
    return scalar


def _guess_rational_ratio(
    values: list[sp.Expr],
    starting_order: int,
    *,
    stride: int,
    maximum_total_degree: int,
) -> dict[str, object] | None:
    ratios = [
        sp.cancel(values[index + stride] / values[index])
        for index in range(len(values) - stride)
    ]
    points = [
        (sp.Integer(starting_order + index), ratio)
        for index, ratio in enumerate(ratios)
    ]
    for total_degree in range(maximum_total_degree + 1):
        for numerator_degree in range(total_degree + 1):
            denominator_degree = total_degree - numerator_degree
            unknown_count = (
                numerator_degree + denominator_degree + 2
            )
            training_count = max(
                2 * unknown_count, unknown_count + 3
            )
            if len(points) - training_count < 8:
                continue
            rows = []
            for order, ratio in points[:training_count]:
                rows.append([
                    *[
                        -order**power
                        for power in range(numerator_degree + 1)
                    ],
                    *[
                        ratio * order**power
                        for power in range(denominator_degree + 1)
                    ],
                ])
            nullspace = sp.Matrix(rows).nullspace()
            if len(nullspace) != 1:
                continue
            vector = nullspace[0]
            symbol = sp.Symbol("m")
            numerator = sp.expand(sum(
                vector[power] * symbol**power
                for power in range(numerator_degree + 1)
            ))
            denominator = sp.expand(sum(
                vector[numerator_degree + 1 + power]
                * symbol**power
                for power in range(denominator_degree + 1)
            ))
            if denominator == 0:
                continue
            candidate = sp.cancel(numerator / denominator)
            if all(
                sp.cancel(
                    ratio - candidate.subs(symbol, order)
                ) == 0
                for order, ratio in points
            ):
                return {
                    "stride": stride,
                    "numerator_degree": numerator_degree,
                    "denominator_degree": denominator_degree,
                    "ratio": str(sp.factor(candidate)),
                    "training_pair_count": training_count,
                    "held_out_pair_count": (
                        len(points) - training_count
                    ),
                    "complete_prefix_replay": True,
                }
    return None


def _guess_polynomial_recurrence(
    values: list[sp.Expr],
    starting_order: int,
    *,
    maximum_order: int,
    maximum_degree: int,
) -> dict[str, object] | None:
    symbol = sp.Symbol("m")
    for recurrence_order in range(1, maximum_order + 1):
        available = len(values) - recurrence_order
        for degree in range(maximum_degree + 1):
            unknown_count = (
                (recurrence_order + 1) * (degree + 1)
            )
            training_count = max(
                unknown_count + 3,
                2 * unknown_count,
            )
            if available - training_count < 8:
                continue
            rows = []
            for index in range(training_count):
                order = sp.Integer(starting_order + index)
                rows.append([
                    values[index + shift] * order**power
                    for shift in range(recurrence_order + 1)
                    for power in range(degree + 1)
                ])
            nullspace = sp.Matrix(rows).nullspace()
            if len(nullspace) != 1:
                continue
            vector = nullspace[0]
            polynomials = []
            offset = 0
            for _shift in range(recurrence_order + 1):
                polynomial = sp.expand(sum(
                    vector[offset + power] * symbol**power
                    for power in range(degree + 1)
                ))
                polynomials.append(polynomial)
                offset += degree + 1
            if all(polynomial == 0 for polynomial in polynomials):
                continue
            if all(
                sp.expand(sum(
                    polynomials[shift].subs(
                        symbol, starting_order + index
                    )
                    * values[index + shift]
                    for shift in range(recurrence_order + 1)
                )) == 0
                for index in range(available)
            ):
                return {
                    "order": recurrence_order,
                    "polynomial_degree": degree,
                    "coefficient_polynomials": [
                        str(sp.factor(polynomial))
                        for polynomial in polynomials
                    ],
                    "training_equation_count": training_count,
                    "held_out_equation_count": (
                        available - training_count
                    ),
                    "complete_prefix_replay": True,
                }
    return None


def run(maximum_log_order: int = 41) -> dict[str, object]:
    family = AFFINE._Family(2)
    base, directions = ZRAY._carry(
        family, (5, 5, 7)
    )
    assert len(directions) == 1
    affine_parameter = sp.Symbol("lambda")
    prefix: Prefix = (dict(base[0]), dict(base[1]))
    AFFINE._add_scaled_prefix(
        prefix, directions[0], affine_parameter
    )
    adapted_v, adapted_g = sp.symbols("V G")
    velocity = [
        _adapt(
            tuple(
                sp.expand(component / sp.factorial(order))
                for component in prefix[1][order]
            ),
            family.v,
            family.t,
            adapted_v,
            adapted_g,
        )
        for order in range(3)
    ]
    sparse_logarithm = _filtered_magnus(
        velocity,
        maximum_log_order,
        adapted_v,
        adapted_g,
    )
    logarithm = [
        _from_sparse(value, adapted_v, adapted_g)
        for value in sparse_logarithm
    ]
    _full_prefix_crosscheck(
        velocity,
        logarithm,
        adapted_v,
        adapted_g,
    )

    rows = []
    scalars = []
    first_parameter_dependent = None
    first_zero = None
    for order in range(5, maximum_log_order + 1):
        shell = ZRAY._degree_shell(
            logarithm[order],
            adapted_v,
            adapted_g,
            4 * order - 6,
        )
        scalar = sp.factor(_z_scalar(
            shell, order, adapted_v, adapted_g
        ))
        if (
            first_parameter_dependent is None
            and affine_parameter in scalar.free_symbols
        ):
            first_parameter_dependent = order
        if first_zero is None and scalar == 0:
            first_zero = order
        scalars.append(scalar)
        rows.append({
            "logarithmic_order": order,
            "z_scalar": str(scalar),
            "parameter_independent": (
                affine_parameter not in scalar.free_symbols
            ),
            "nonzero": scalar != 0,
        })

    expected = {
        5: sp.Rational(7, 276_480),
        6: -sp.Rational(1, 184_320),
        7: -sp.Rational(1, 1_376_256),
        8: sp.Rational(5, 14_155_776),
    }
    assert all(
        scalars[order - 5] == value
        for order, value in expected.items()
    )
    recurrence = find_linear_recurrence(
        [str(value) for value in scalars],
        max_order=min(16, len(scalars) // 2 - 1),
        timeout_s=30,
    )
    ratio = (
        None
        if first_zero is not None
        else {
            str(stride): _guess_rational_ratio(
                scalars,
                5,
                stride=stride,
                maximum_total_degree=12,
            )
            for stride in (1, 2, 4)
        }
    )
    polynomial_recurrence = _guess_polynomial_recurrence(
        scalars,
        5,
        maximum_order=4,
        maximum_degree=5,
    )
    return {
        "schema": (
            "axiompack.jacobian_moving_cone_excess_filtered_recurrence.v1"
        ),
        "maximum_logarithmic_order": maximum_log_order,
        "retained_excess_lower_bound": -6,
        "complete_order_two_affine_parameter": str(
            affine_parameter
        ),
        "full_unfiltered_crosscheck_through_order_eight": True,
        "known_complete_affine_shells_through_order_eight_match": True,
        "first_parameter_dependent_order": first_parameter_dependent,
        "first_zero_order": first_zero,
        "all_checked_z_scalars_parameter_independent": (
            first_parameter_dependent is None
        ),
        "all_checked_z_scalars_nonzero": first_zero is None,
        "constant_coefficient_recurrence": recurrence,
        "rational_stride_ratios": ratio,
        "polynomial_coefficient_recurrence": (
            polynomial_recurrence
        ),
        "rows": rows,
        "claim_boundary": (
            "Exact excess-filtered continuation with projected velocity "
            "inputs zero from derivative order three onward.  It becomes "
            "a moving-connection theorem only after an all-order velocity "
            "filtration or a symmetric cancellation-cost transfer."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
