#!/usr/bin/env python3
"""Exact cost-three/four scan for covariant ``Q^b*C^m`` prefixes.

The target prefix is completed by the first two covariant rows against
the fixed normalized background.  At each row, source residuals are
normalized successively by every current cone level
``1,C,...,C^m``.  The calculation is exact and finite for each supplied
pair ``(b,m)``; it does not extrapolate a formula in ``m``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_higher_contact_first_quotient import (  # noqa: E402
    _canonical_contact_multiplier,
)
from gauge_cone_qbc_uniform_cost_four import (  # noqa: E402
    _fixed_coefficients,
    _fixed_target_coefficients,
)
from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_cone_monomial,
)


Exponent = tuple[int, int]
Source = dict[Exponent, sp.Expr]
Target = dict[Exponent, sp.Expr]


CUSP: Target = {
    (3, 0): sp.Integer(4),
    (2, 0): -sp.Integer(1),
    (1, 1): -sp.Integer(18),
    (0, 2): sp.Integer(27),
    (0, 1): sp.Integer(4),
}
DISCRIMINANT: Target = {
    (3, 0): sp.Integer(4),
    (0, 2): sp.Integer(27),
}


def _clean(value: dict[Exponent, sp.Expr]) -> dict[Exponent, sp.Expr]:
    result = {}
    for exponent, raw in value.items():
        coefficient = (
            sp.factor(raw)
            if raw.free_symbols
            else raw
        )
        if coefficient != 0:
            result[exponent] = coefficient
    return result


def _add(
    left: dict[Exponent, sp.Expr],
    right: dict[Exponent, sp.Expr],
) -> dict[Exponent, sp.Expr]:
    result = dict(left)
    for exponent, coefficient in right.items():
        result[exponent] = (
            result.get(exponent, sp.Integer(0)) + coefficient
        )
    return _clean(result)


def _scale(
    value: dict[Exponent, sp.Expr],
    scalar: sp.Expr,
) -> dict[Exponent, sp.Expr]:
    return _clean({
        exponent: scalar * coefficient
        for exponent, coefficient in value.items()
    })


def _multiply(
    left: dict[Exponent, sp.Expr],
    right: dict[Exponent, sp.Expr],
) -> dict[Exponent, sp.Expr]:
    result: dict[Exponent, sp.Expr] = {}
    for left_exponent, left_coefficient in left.items():
        for right_exponent, right_coefficient in right.items():
            exponent = (
                left_exponent[0] + right_exponent[0],
                left_exponent[1] + right_exponent[1],
            )
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + left_coefficient * right_coefficient
            )
    return _clean(result)


def _target_power(value: Target, exponent: int) -> Target:
    if exponent < 0:
        raise ValueError("target powers must be nonnegative")
    result: Target = {(0, 0): sp.Integer(1)}
    factor = value
    remaining = exponent
    while remaining:
        if remaining % 2:
            result = _multiply(result, factor)
        remaining //= 2
        if remaining:
            factor = _multiply(factor, factor)
    return result


def _target_shift(
    value: Target,
    p_exponent: int,
    q_exponent: int,
) -> Target:
    return {
        (
            exponent[0] + p_exponent,
            exponent[1] + q_exponent,
        ): coefficient
        for exponent, coefficient in value.items()
    }


def _target_bracket(left: Target, right: Target) -> Target:
    result: Target = {}
    for (left_p, left_q), left_coefficient in left.items():
        for (right_p, right_q), right_coefficient in right.items():
            multiplier = left_q * right_p - left_p * right_q
            if multiplier == 0:
                continue
            exponent = (
                left_p + right_p - 1,
                left_q + right_q - 1,
            )
            result[exponent] = (
                result.get(exponent, sp.Integer(0))
                + multiplier * left_coefficient * right_coefficient
            )
    return _clean(result)


def _target_is_cone_compatible(value: Target) -> bool:
    return all(
        p_exponent <= 2 * q_exponent
        and (p_exponent, q_exponent) != (0, 1)
        for (p_exponent, q_exponent), coefficient in value.items()
        if coefficient != 0
    )


class NumericSourcePullback:
    """Source pullbacks through ordinary parameter order two."""

    def __init__(self) -> None:
        self.p_coefficients, self.q_coefficients = _fixed_coefficients()

    @lru_cache(maxsize=None)
    def factor_power(
        self,
        family: str,
        exponent: int,
    ) -> tuple[Source, Source, Source]:
        if exponent < 0:
            raise ValueError("source powers must be nonnegative")
        if exponent == 0:
            return ({(0, 0): sp.Integer(1)}, {}, {})
        parent = self.factor_power(family, exponent - 1)
        coefficients = {
            "P": self.p_coefficients,
            "Q": self.q_coefficients,
        }[family]
        result = []
        for order in range(3):
            value: Source = {}
            for index in range(order + 1):
                value = _add(
                    value,
                    _multiply(
                        parent[index],
                        coefficients[order - index],
                    ),
                )
            result.append(value)
        return result[0], result[1], result[2]

    @lru_cache(maxsize=None)
    def monomial(
        self,
        p_exponent: int,
        q_exponent: int,
        order: int,
    ) -> Source:
        p_series = self.factor_power("P", p_exponent)
        q_series = self.factor_power("Q", q_exponent)
        result: Source = {}
        for index in range(order + 1):
            result = _add(
                result,
                _multiply(
                    p_series[index],
                    q_series[order - index],
                ),
            )
        return result

    def expression(self, value: Target, order: int) -> Source:
        result: Source = {}
        for (
            p_exponent,
            q_exponent,
        ), coefficient in value.items():
            result = _add(
                result,
                _scale(
                    self.monomial(
                        p_exponent,
                        q_exponent,
                        order,
                    ),
                    coefficient,
                ),
            )
        return result


def _contact_seed(
    p_exponent: int,
    q_exponent: int,
    contact_depth: int,
) -> Target:
    return _target_shift(
        _target_power(CUSP, contact_depth),
        p_exponent,
        q_exponent,
    )


def _canonical_control(
    radial_degree: int,
    contact_depth: int,
) -> tuple[int, int] | None:
    if contact_depth == 0:
        return _canonical_cone_monomial(radial_degree)
    return _canonical_contact_multiplier(
        radial_degree,
        contact_depth,
    )


def _normalize_row(
    residual: Source,
    target_terms: Target,
    maximum_contact_depth: int,
    pullback: NumericSourcePullback,
) -> tuple[
    Source,
    Target,
    list[dict[str, object]],
    dict[int, Source],
]:
    result = dict(residual)
    controls = dict(target_terms)
    control_rows = []
    depth_snapshots = {}
    for contact_depth in range(maximum_contact_depth + 1):
        normal_order = 2 * contact_depth
        while True:
            radial_degrees = [
                radial
                for (radial, normal), coefficient in result.items()
                if (
                    normal == normal_order
                    and coefficient != 0
                    and _canonical_control(
                        radial,
                        contact_depth,
                    )
                    is not None
                )
            ]
            if not radial_degrees:
                break
            radial = max(radial_degrees)
            multiplier = _canonical_control(
                radial,
                contact_depth,
            )
            assert multiplier is not None
            target_seed = _contact_seed(
                multiplier[0],
                multiplier[1],
                contact_depth,
            )
            source_seed = _scale(
                pullback.expression(target_seed, 0),
                8,
            )
            pivot = source_seed[(radial, normal_order)]
            coefficient = sp.factor(
                -result[(radial, normal_order)] / pivot
            )
            term = _scale(target_seed, coefficient)
            controls = _add(controls, term)
            result = _add(
                result,
                _scale(source_seed, coefficient),
            )
            control_rows.append({
                "contact_depth": contact_depth,
                "radial_degree": radial,
                "multiplier": list(multiplier),
                "coefficient": str(coefficient),
            })
        depth_snapshots[contact_depth] = _clean(result)
    return (
        _clean(result),
        _clean(controls),
        control_rows,
        depth_snapshots,
    )


def _row_residual(
    target_rows: list[Target],
    current_row: int,
    pullback: NumericSourcePullback,
) -> Source:
    result: Source = {}
    for target_row, terms in enumerate(target_rows, 1):
        if target_row > current_row:
            break
        result = _add(
            result,
            _scale(
                pullback.expression(
                    terms,
                    current_row - target_row,
                ),
                8,
            ),
        )
    return result


def _leading_rows(value: Source) -> list[dict[str, object]]:
    maximum_radial = max(
        (exponent[0] for exponent in value),
        default=None,
    )
    return [
        {
            "key_r_normal": list(exponent),
            "exponent_u_z": [
                exponent[0],
                exponent[0] + exponent[1],
            ],
            "coefficient": str(coefficient),
        }
        for exponent, coefficient in sorted(value.items())
        if exponent[0] == maximum_radial
    ]


def _sparse_rows(value: Source) -> list[dict[str, object]]:
    return [
        {
            "key_r_normal": list(exponent),
            "coefficient": str(coefficient),
        }
        for exponent, coefficient in sorted(value.items())
    ]


def _terminal_rectangle_certificate(
    value: Source,
    terminal_radial: int,
    terminal_normal: int,
) -> dict[str, object]:
    violations = [
        {
            "key_r_normal": list(exponent),
            "coefficient": str(coefficient),
        }
        for exponent, coefficient in sorted(value.items())
        if (
            exponent[0] > terminal_radial
            or exponent[0] + exponent[1]
            > terminal_radial + terminal_normal
        )
    ]
    corner_rows = [
        {
            "key_r_normal": list(exponent),
            "coefficient": str(coefficient),
        }
        for exponent, coefficient in sorted(value.items())
        if (
            exponent[0] == terminal_radial
            and exponent[0] + exponent[1]
            == terminal_radial + terminal_normal
        )
    ]
    return {
        "terminal_key_r_normal": [
            terminal_radial,
            terminal_normal,
        ],
        "componentwise_violations": violations,
        "terminal_is_unique_northeast_corner": (
            not violations and len(corner_rows) == 1
        ),
        "corner_rows": corner_rows,
    }


def _control_histogram(
    rows: list[dict[str, object]],
) -> dict[str, int]:
    depths = sorted({
        int(row["contact_depth"])
        for row in rows
    })
    return {
        str(depth): sum(
            int(row["contact_depth"]) == depth
            for row in rows
        )
        for depth in depths
    }


def _control_radial_offsets(
    rows: list[dict[str, object]],
    baseline: int,
) -> dict[str, list[int]]:
    return {
        str(depth): sorted(
            int(row["radial_degree"]) - baseline
            for row in rows
            if int(row["contact_depth"]) == depth
        )
        for depth in sorted({
            int(row["contact_depth"])
            for row in rows
        })
    }


@dataclass(frozen=True)
class PrefixNormalForm:
    row_two_residual: Source
    row_three_residual: Source
    target_rows: list[Target]
    row_two_controls: list[dict[str, object]]
    row_three_controls: list[dict[str, object]]
    row_two_snapshots: dict[int, Source]
    row_three_snapshots: dict[int, Source]


def _normalize_prefix(
    prefix: Target,
    normalization_contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[Target],
    cone_admissible_covariant_only: bool = False,
    start_covariant_rows_from_zero: bool = False,
) -> PrefixNormalForm:
    """Return the canonical cost-three/four normal form of a prefix.

    With ``start_covariant_rows_from_zero=True`` this is a fixed linear
    quotient map on arbitrary finite target prefixes.  The entry point is
    deliberately separate from ``_one_case`` so combined-prefix checks can
    compare direct normalization with sums of monomial columns.
    """

    formal_first_covariant = _scale(
        _target_bracket(background[0], prefix),
        -1,
    )
    first_covariant = (
        {}
        if start_covariant_rows_from_zero
        else formal_first_covariant
        if (
            not cone_admissible_covariant_only
            or _target_is_cone_compatible(formal_first_covariant)
        )
        else {}
    )

    target_rows = [prefix]
    row_two_residual = _row_residual(
        [*target_rows, first_covariant],
        2,
        pullback,
    )
    (
        row_two_residual,
        first_covariant,
        row_two_controls,
        row_two_snapshots,
    ) = _normalize_row(
        row_two_residual,
        first_covariant,
        normalization_contact_depth,
        pullback,
    )
    target_rows.append(first_covariant)

    formal_second_covariant = _scale(
        _add(
            _target_bracket(background[0], first_covariant),
            _target_bracket(background[1], prefix),
        ),
        -sp.Rational(1, 2),
    )
    second_covariant = (
        {}
        if start_covariant_rows_from_zero
        else formal_second_covariant
        if (
            not cone_admissible_covariant_only
            or _target_is_cone_compatible(formal_second_covariant)
        )
        else {}
    )
    row_three_residual = _row_residual(
        [*target_rows, second_covariant],
        3,
        pullback,
    )
    (
        row_three_residual,
        second_covariant,
        row_three_controls,
        row_three_snapshots,
    ) = _normalize_row(
        row_three_residual,
        second_covariant,
        normalization_contact_depth,
        pullback,
    )
    target_rows.append(second_covariant)
    return PrefixNormalForm(
        row_two_residual=row_two_residual,
        row_three_residual=row_three_residual,
        target_rows=target_rows,
        row_two_controls=row_two_controls,
        row_three_controls=row_three_controls,
        row_two_snapshots=row_two_snapshots,
        row_three_snapshots=row_three_snapshots,
    )


def _one_case(
    q_exponent: int,
    contact_depth: int,
    p_exponent: int = 0,
    pullback: NumericSourcePullback | None = None,
    background: list[Target] | None = None,
    discriminant_depth: int = 0,
    normalization_contact_depth: int | None = None,
    cone_admissible_covariant_only: bool = False,
    start_covariant_rows_from_zero: bool = False,
    include_full_residual: bool = False,
) -> dict[str, object]:
    if contact_depth < 1:
        raise ValueError("contact depth must be positive")
    if p_exponent < 0:
        raise ValueError("the P exponent must be nonnegative")
    if discriminant_depth < 0:
        raise ValueError("the discriminant depth must be nonnegative")
    if normalization_contact_depth is None:
        normalization_contact_depth = contact_depth
    if normalization_contact_depth < contact_depth:
        raise ValueError(
            "normalization contact depth cannot be below the prefix"
        )
    if (
        p_exponent
        + 3 * discriminant_depth
        + 3 * contact_depth
        > 2 * q_exponent
    ):
        raise ValueError("the prefix is outside the cone")
    if pullback is None:
        pullback = NumericSourcePullback()
    if background is None:
        background = _fixed_target_coefficients(1)
    prefix = _target_shift(
        _multiply(
            _target_power(DISCRIMINANT, discriminant_depth),
            _target_power(CUSP, contact_depth),
        ),
        p_exponent,
        q_exponent,
    )
    normal_form = _normalize_prefix(
        prefix,
        normalization_contact_depth,
        pullback,
        background,
        cone_admissible_covariant_only,
        start_covariant_rows_from_zero,
    )
    row_two_residual = normal_form.row_two_residual
    row_three_residual = normal_form.row_three_residual
    target_rows = normal_form.target_rows
    row_two_controls = normal_form.row_two_controls
    row_three_controls = normal_form.row_three_controls
    row_two_snapshots = normal_form.row_two_snapshots
    row_three_snapshots = normal_form.row_three_snapshots
    baseline = (
        2 * p_exponent
        + 3 * q_exponent
        + 5 * discriminant_depth
        + 2 * contact_depth
    )
    terminal_rectangle = _terminal_rectangle_certificate(
        row_three_residual,
        baseline,
        2 * contact_depth + 1,
    )
    prefix_contact_residual = row_three_snapshots[contact_depth]
    predicted_odd_terminal = sp.factor(
        row_three_residual.get(
            (baseline, 2 * contact_depth + 1),
            0,
        )
    )
    row_cone_compatibility = [
        _target_is_cone_compatible(row)
        for row in target_rows
    ]

    output = {
        "p_exponent": p_exponent,
        "q_exponent": q_exponent,
        "discriminant_depth": discriminant_depth,
        "contact_depth": contact_depth,
        "normalization_contact_depth": normalization_contact_depth,
        "cone_admissible_covariant_only": (
            cone_admissible_covariant_only
        ),
        "start_covariant_rows_from_zero": (
            start_covariant_rows_from_zero
        ),
        "cost_three_residual_vanished": not row_two_residual,
        "cost_three_leading_rows": _leading_rows(row_two_residual),
        "cost_four_residual_vanished": not row_three_residual,
        "cost_four_leading_rows": _leading_rows(row_three_residual),
        "cost_four_predicted_odd_terminal": {
            "key_r_normal": [
                baseline,
                2 * contact_depth + 1,
            ],
            "coefficient": str(predicted_odd_terminal),
        },
        "cost_four_after_prefix_contact_leading_rows": _leading_rows(
            prefix_contact_residual
        ),
        "cost_four_terminal_rectangle": terminal_rectangle,
        "row_two_current_control_count": len(row_two_controls),
        "row_two_snapshot_depths": sorted(row_two_snapshots),
        "row_two_current_control_histogram": _control_histogram(
            row_two_controls
        ),
        "row_two_current_control_radial_offsets": (
            _control_radial_offsets(row_two_controls, baseline)
        ),
        "row_three_current_control_count": len(row_three_controls),
        "row_three_current_control_histogram": _control_histogram(
            row_three_controls
        ),
        "row_three_current_control_radial_offsets": (
            _control_radial_offsets(row_three_controls, baseline)
        ),
        "target_row_cone_compatibility": row_cone_compatibility,
        "target_rows_are_cone_compatible": all(
            row_cone_compatibility
        ),
    }
    if include_full_residual:
        output["cost_three_residual_rows"] = _sparse_rows(
            row_two_residual
        )
        output["cost_four_residual_rows"] = _sparse_rows(
            row_three_residual
        )
        output["cost_four_after_prefix_contact_rows"] = _sparse_rows(
            prefix_contact_residual
        )
    return output


def run() -> dict[str, object]:
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    one_c_controls = [
        _one_case(
            q_exponent,
            1,
            pullback=pullback,
            background=background,
        )
        for q_exponent in (6, 7)
    ]
    for row in one_c_controls:
        q_exponent = row["q_exponent"]
        leading = row["cost_four_leading_rows"]
        assert leading == [{
            "key_r_normal": [3 * q_exponent + 2, 3],
            "exponent_u_z": [
                3 * q_exponent + 2,
                3 * q_exponent + 5,
            ],
            "coefficient": str(sp.Rational(
                (-1) ** q_exponent * (9 * q_exponent + 4),
                2 ** (2 * q_exponent + 5),
            )),
        }]
        assert row["target_rows_are_cone_compatible"]

    higher_rows = [
        _one_case(
            q_exponent,
            contact_depth,
            pullback=pullback,
            background=background,
        )
        for contact_depth, q_values in (
            (2, (5, 6, 7)),
            (3, (7, 8)),
        )
        for q_exponent in q_values
    ]
    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "higher_contact_cost_four_scan.v1"
        ),
        "one_c_controls": one_c_controls,
        "higher_contact_rows": higher_rows,
        "all_current_levels_through_prefix_contact_depth_enabled": True,
        "claim_boundary": (
            "Exact finite cost-three/four scan for the listed "
            "covariantly completed Q^b*C^m prefixes. No symbolic "
            "identity in b or m and no all-order Magnus conclusion "
            "is inferred."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
