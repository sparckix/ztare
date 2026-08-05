#!/usr/bin/env python3
"""Exact combined-prefix rank audit for the higher-contact quotient.

The single-monomial calculations do not by themselves exclude affine
cancellation between exceptional and robust classes.  This replay builds
finite canonical ``D``-adic rectangles, removes polynomial identities in
the target first, and compares that target-space rank with the rank of the
complete cost-three/four source normal form.

All current rows start from zero.  Thus every column is evaluated by the
same fixed linear cone normalizer, including one adversarial contact level
beyond the largest contact depth in the input rectangle.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Hashable

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_higher_contact_cost_four_scan import (  # noqa: E402
    CUSP,
    DISCRIMINANT,
    NumericSourcePullback,
    Source,
    Target,
    _add,
    _fixed_target_coefficients,
    _multiply,
    _normalize_prefix,
    _scale,
    _target_is_cone_compatible,
    _target_power,
    _target_shift,
)


Coordinate = tuple[int, int, int]


@dataclass(frozen=True)
class Candidate:
    p_exponent: int
    q_exponent: int
    discriminant_depth: int
    contact_depth: int
    radial_slope: int
    cone_slack: int
    prefix: Target

    @property
    def label(self) -> str:
        return (
            f"P^{self.p_exponent}*Q^{self.q_exponent}"
            f"*D^{self.discriminant_depth}*C^{self.contact_depth}"
        )

    @property
    def exceptional(self) -> bool:
        return (
            self.discriminant_depth == 0
            and (self.p_exponent, self.cone_slack)
            in {(0, 0), (0, 1), (0, 2), (0, 3), (1, 0)}
        )


def _candidates(
    maximum_contact_depth: int,
    maximum_radial_slope: int,
) -> list[Candidate]:
    result = []
    for contact_depth in range(1, maximum_contact_depth + 1):
        for discriminant_depth in range(maximum_radial_slope // 5 + 1):
            for p_exponent in range(3):
                minimum_q = (
                    p_exponent
                    + 3 * discriminant_depth
                    + 3 * contact_depth
                    + 1
                ) // 2
                q_exponent = minimum_q
                while True:
                    radial_slope = (
                        2 * p_exponent
                        + 3 * q_exponent
                        + 5 * discriminant_depth
                        + 2 * contact_depth
                    )
                    if radial_slope > maximum_radial_slope:
                        break
                    cone_slack = (
                        2 * q_exponent
                        - p_exponent
                        - 3 * discriminant_depth
                        - 3 * contact_depth
                    )
                    prefix = _target_shift(
                        _multiply(
                            _target_power(
                                DISCRIMINANT,
                                discriminant_depth,
                            ),
                            _target_power(CUSP, contact_depth),
                        ),
                        p_exponent,
                        q_exponent,
                    )
                    assert _target_is_cone_compatible(prefix)
                    result.append(Candidate(
                        p_exponent=p_exponent,
                        q_exponent=q_exponent,
                        discriminant_depth=discriminant_depth,
                        contact_depth=contact_depth,
                        radial_slope=radial_slope,
                        cone_slack=cone_slack,
                        prefix=prefix,
                    ))
                    q_exponent += 1
    return sorted(
        result,
        key=lambda row: (
            row.radial_slope,
            row.contact_depth,
            row.discriminant_depth,
            row.p_exponent,
            row.q_exponent,
        ),
    )


def _matrix(
    columns: list[dict[Hashable, sp.Expr]],
) -> tuple[sp.Matrix, list[Hashable]]:
    coordinates = sorted({
        coordinate
        for column in columns
        for coordinate in column
    })
    return (
        sp.Matrix([
            [
                column.get(coordinate, sp.Integer(0))
                for column in columns
            ]
            for coordinate in coordinates
        ]),
        coordinates,
    )


def _target_pivots(
    candidates: list[Candidate],
) -> tuple[list[int], int]:
    matrix, _ = _matrix([row.prefix for row in candidates])
    _, pivots = matrix.rref()
    return list(pivots), len(pivots)


def _source_column(
    candidate: Candidate,
    normalization_contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[Target],
) -> dict[Coordinate, sp.Expr]:
    normal_form = _normalize_prefix(
        candidate.prefix,
        normalization_contact_depth,
        pullback,
        background,
        start_covariant_rows_from_zero=True,
    )
    return {
        **{
            (3, radial, normal): coefficient
            for (radial, normal), coefficient
            in normal_form.row_two_residual.items()
        },
        **{
            (4, radial, normal): coefficient
            for (radial, normal), coefficient
            in normal_form.row_three_residual.items()
        },
    }


def _combine_targets(
    candidates: list[Candidate],
    coefficients: list[sp.Rational],
) -> Target:
    result: Target = {}
    for candidate, coefficient in zip(
        candidates,
        coefficients,
        strict=True,
    ):
        result = _add(
            result,
            _scale(candidate.prefix, coefficient),
        )
    return result


def _combine_sources(
    columns: list[dict[Coordinate, sp.Expr]],
    coefficients: list[sp.Rational],
) -> dict[Coordinate, sp.Expr]:
    result: dict[Coordinate, sp.Expr] = {}
    for column, coefficient in zip(columns, coefficients, strict=True):
        for coordinate, value in column.items():
            result[coordinate] = (
                result.get(coordinate, sp.Integer(0))
                + coefficient * value
            )
    return {
        coordinate: sp.factor(value)
        for coordinate, value in result.items()
        if sp.factor(value) != 0
    }


def _direct_source(
    prefix: Target,
    normalization_contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[Target],
) -> dict[Coordinate, sp.Expr]:
    normal_form = _normalize_prefix(
        prefix,
        normalization_contact_depth,
        pullback,
        background,
        start_covariant_rows_from_zero=True,
    )
    return {
        **{
            (3, radial, normal): coefficient
            for (radial, normal), coefficient
            in normal_form.row_two_residual.items()
        },
        **{
            (4, radial, normal): coefficient
            for (radial, normal), coefficient
            in normal_form.row_three_residual.items()
        },
    }


def _linearity_checks(
    basis: list[Candidate],
    columns: list[dict[Coordinate, sp.Expr]],
    normalization_contact_depth: int,
    pullback: NumericSourcePullback,
    background: list[Target],
) -> list[dict[str, object]]:
    selections: list[list[int]] = []
    if len(basis) >= 3:
        selections.append([0, len(basis) // 2, len(basis) - 1])

    fibers: dict[tuple[int, int], list[int]] = {}
    for index, candidate in enumerate(basis):
        fibers.setdefault(
            (candidate.contact_depth, candidate.radial_slope),
            [],
        ).append(index)
    mixed_fibers = [
        indices
        for indices in fibers.values()
        if (
            any(basis[index].exceptional for index in indices)
            and any(not basis[index].exceptional for index in indices)
        )
    ]
    selections.extend(indices[:4] for indices in mixed_fibers[:3])

    rows = []
    seen = set()
    for indices in selections:
        key = tuple(indices)
        if len(indices) < 2 or key in seen:
            continue
        seen.add(key)
        coefficients = [
            sp.Rational((-1) ** index * (index + 1))
            for index in range(len(indices))
        ]
        selected_candidates = [basis[index] for index in indices]
        selected_columns = [columns[index] for index in indices]
        direct = _direct_source(
            _combine_targets(selected_candidates, coefficients),
            normalization_contact_depth,
            pullback,
            background,
        )
        assembled = _combine_sources(selected_columns, coefficients)
        assert direct == assembled
        rows.append({
            "labels": [
                candidate.label
                for candidate in selected_candidates
            ],
            "coefficients": [str(value) for value in coefficients],
            "direct_equals_column_sum": True,
            "nonzero_residual_row_count": len(direct),
        })
    return rows


def run(
    maximum_contact_depth: int = 2,
    maximum_radial_slope: int = 24,
) -> dict[str, object]:
    if maximum_contact_depth < 1:
        raise ValueError("maximum contact depth must be positive")
    if maximum_radial_slope < 8:
        raise ValueError("maximum radial slope must be at least eight")

    candidates = _candidates(
        maximum_contact_depth,
        maximum_radial_slope,
    )
    pivot_indices, target_rank = _target_pivots(candidates)
    basis = [candidates[index] for index in pivot_indices]
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    normalization_contact_depth = maximum_contact_depth + 1
    columns = [
        _source_column(
            candidate,
            normalization_contact_depth,
            pullback,
            background,
        )
        for candidate in basis
    ]
    source_matrix, source_coordinates = _matrix(columns)
    source_rank = source_matrix.rank()
    kernel_dimension = target_rank - source_rank
    assert kernel_dimension >= 0

    mixed_fibers = []
    grouped: dict[tuple[int, int], list[int]] = {}
    for index, candidate in enumerate(basis):
        grouped.setdefault(
            (candidate.contact_depth, candidate.radial_slope),
            [],
        ).append(index)
    for (contact_depth, radial_slope), indices in sorted(grouped.items()):
        if not (
            any(basis[index].exceptional for index in indices)
            and any(not basis[index].exceptional for index in indices)
        ):
            continue
        fiber_columns = [columns[index] for index in indices]
        fiber_matrix, _ = _matrix(fiber_columns)
        fiber_rank = fiber_matrix.rank()
        mixed_fibers.append({
            "contact_depth": contact_depth,
            "radial_slope": radial_slope,
            "labels": [basis[index].label for index in indices],
            "exceptional_flags": [
                basis[index].exceptional for index in indices
            ],
            "column_count": len(indices),
            "rank": fiber_rank,
            "full_column_rank": fiber_rank == len(indices),
        })

    linearity = _linearity_checks(
        basis,
        columns,
        normalization_contact_depth,
        pullback,
        background,
    )
    assert source_rank == target_rank
    assert all(row["full_column_rank"] for row in mixed_fibers)
    assert linearity
    return {
        "schema": (
            "axiompack.jacobian_cone_higher_contact_"
            "combined_rank.v1"
        ),
        "maximum_contact_depth": maximum_contact_depth,
        "maximum_radial_slope": maximum_radial_slope,
        "normalization_contact_depth": normalization_contact_depth,
        "candidate_column_count_before_target_identities": len(
            candidates
        ),
        "target_polynomial_rank": target_rank,
        "canonical_basis_labels": [row.label for row in basis],
        "source_quotient_coordinate_count": len(source_coordinates),
        "source_quotient_rank": source_rank,
        "nonidentity_kernel_dimension": kernel_dimension,
        "injective_on_target_span": source_rank == target_rank,
        "mixed_exceptional_robust_fibers": mixed_fibers,
        "linearity_checks": linearity,
        "claim_boundary": (
            "Exact finite-rectangle rank and direct-sum audit. "
            "Target polynomial identities are removed before the "
            "source rank comparison. This does not by itself prove "
            "injectivity in every finite rectangle."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-contact-depth", type=int, default=2)
    parser.add_argument("--maximum-radial-slope", type=int, default=24)
    arguments = parser.parse_args()
    print(json.dumps(
        run(
            arguments.maximum_contact_depth,
            arguments.maximum_radial_slope,
        ),
        indent=2,
        sort_keys=True,
    ))
