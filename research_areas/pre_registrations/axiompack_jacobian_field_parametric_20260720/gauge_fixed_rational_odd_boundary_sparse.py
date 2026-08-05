#!/usr/bin/env python3
"""Sparse exact symbolic shell replay for the odd-boundary positivity test."""

from __future__ import annotations

from fractions import Fraction
import json
from math import factorial
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    inverse_dexp_coefficients,
    magnus_from_velocity,
)


Power = tuple[int, int]
Polynomial = dict[Power, Fraction]
Shell = tuple[int, int]
Element = dict[Shell, Polynomial]


def _polynomial_add(
    left: Polynomial,
    right: Polynomial,
) -> Polynomial:
    result = dict(left)
    for power, coefficient in right.items():
        value = result.get(power, Fraction(0)) + coefficient
        if value:
            result[power] = value
        else:
            result.pop(power, None)
    return result


def _polynomial_scale(
    value: Polynomial,
    scalar: Fraction,
) -> Polynomial:
    if scalar == 0:
        return {}
    return {
        power: scalar * coefficient
        for power, coefficient in value.items()
        if scalar * coefficient
    }


def _polynomial_multiply(
    left: Polynomial,
    right: Polynomial,
) -> Polynomial:
    result: Polynomial = {}
    for (left_e, left_ell), left_coefficient in left.items():
        for (right_e, right_ell), right_coefficient in right.items():
            power = (left_e + right_e, left_ell + right_ell)
            value = (
                result.get(power, Fraction(0))
                + left_coefficient * right_coefficient
            )
            if value:
                result[power] = value
            else:
                result.pop(power, None)
    return result


def _element_add(left: Element, right: Element) -> Element:
    result = dict(left)
    for shell, polynomial in right.items():
        value = _polynomial_add(result.get(shell, {}), polynomial)
        if value:
            result[shell] = value
        else:
            result.pop(shell, None)
    return result


def _element_scale(value: Element, scalar: Fraction) -> Element:
    if scalar == 0:
        return {}
    return {
        shell: scaled
        for shell, polynomial in value.items()
        if (scaled := _polynomial_scale(polynomial, scalar))
    }


def _shell_bracket_coefficient(
    first: Shell,
    second: Shell,
) -> int:
    r, s = first
    u, w = second
    return (
        u * s
        + 3 * u
        - w * r
        - 2 * w
        - 3 * r
        + 2 * s
    )


def _element_bracket(left: Element, right: Element) -> Element:
    result: Element = {}
    for first, first_polynomial in left.items():
        for second, second_polynomial in right.items():
            scalar = _shell_bracket_coefficient(first, second)
            if scalar == 0:
                continue
            shell = (first[0] + second[0], first[1] + second[1])
            contribution = _polynomial_scale(
                _polynomial_multiply(
                    first_polynomial,
                    second_polynomial,
                ),
                Fraction(scalar),
            )
            value = _polynomial_add(result.get(shell, {}), contribution)
            if value:
                result[shell] = value
            else:
                result.pop(shell, None)
    return result


def _truncate_element(value: Element, maximum_order: int) -> Element:
    return {
        shell: polynomial
        for shell, polynomial in value.items()
        if shell[0] + shell[1] <= maximum_order
    }


def _evaluate(
    value: Polynomial,
    e_value: int,
    ell_value: int,
) -> Fraction:
    return sum(
        coefficient
        * Fraction(e_value) ** e_power
        * Fraction(ell_value) ** ell_power
        for (e_power, ell_power), coefficient in value.items()
    )


def _polynomial_row(value: Polynomial) -> list[dict[str, object]]:
    return [
        {
            "e_power": power[0],
            "ell_power": power[1],
            "coefficient": str(coefficient),
        }
        for power, coefficient in sorted(
            value.items(),
            key=lambda item: (-item[0][0], item[0][1]),
        )
    ]


def _series_bracket(
    left: list[Element],
    right: list[Element],
    maximum_order: int,
) -> list[Element]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(left[: maximum_order + 1]):
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            order = left_order + right_order
            result[order] = _element_add(
                result[order],
                _element_bracket(left_value, right_value),
            )
    return result


def _magnus_contribution_audit(
    velocity: list[Element],
    maximum_order: int,
) -> tuple[list[Element], dict[str, object] | None]:
    inverse = inverse_dexp_coefficients(
        maximum_order,
        VelocityPlacement.LEFT_MULTIPLY,
    )
    logarithm = [{} for _ in range(maximum_order + 1)]
    first_nonpositive: dict[str, object] | None = None
    for derivative_order in range(maximum_order):
        result = velocity[derivative_order]
        contribution_rows = [(0, result)]
        nested = velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _series_bracket(
                prefix,
                nested,
                derivative_order,
            )
            if inverse[depth]:
                contribution = _element_scale(
                    nested[derivative_order],
                    inverse[depth],
                )
                contribution_rows.append((depth, contribution))
                result = _element_add(result, contribution)
        logarithm[derivative_order + 1] = _element_scale(
            result,
            Fraction(1, derivative_order + 1),
        )

        logarithmic_order = derivative_order + 1
        if logarithmic_order < 3 or logarithmic_order % 2 == 0:
            continue
        for depth, contribution in contribution_rows:
            for (r, shell_s), coefficient in contribution.items():
                q_degree = shell_s - r + 1
                if q_degree < 0 or q_degree % 2:
                    continue
                wick = _polynomial_scale(
                    coefficient,
                    Fraction(-((-1) ** (q_degree // 2))),
                )
                if any(value < 0 for value in wick.values()):
                    if first_nonpositive is None:
                        first_nonpositive = {
                            "logarithmic_order": logarithmic_order,
                            "inverse_dexp_depth": depth,
                            "shell": [r, shell_s],
                            "q_degree": q_degree,
                            "polynomial": _polynomial_row(wick),
                        }
    return logarithm, first_nonpositive


def run(depth: int = 31) -> dict[str, object]:
    if depth < 7 or depth % 2 == 0:
        raise ValueError("depth must be odd and at least seven")

    one: Polynomial = {(0, 0): Fraction(1)}
    e: Polynomial = {(1, 0): Fraction(1)}
    ell: Polynomial = {(0, 1): Fraction(1)}
    outer: Element = {(0, 1): _polynomial_scale(e, Fraction(-1, 2))}
    middle: Element = {
        (1, 0): _polynomial_scale(one, Fraction(-1)),
        (0, 1): _polynomial_scale(ell, Fraction(-1)),
    }

    ad_outer_middle: list[Element] = [middle]
    for _ in range(1, depth):
        ad_outer_middle.append(
            _element_bracket(outer, ad_outer_middle[-1])
        )

    ad_middle_outer: list[Element] = [outer]
    for _ in range(1, depth):
        ad_middle_outer.append(
            _element_bracket(middle, ad_middle_outer[-1])
        )

    transported_outer: dict[tuple[int, int], Element] = {}
    for middle_depth in range(depth):
        value = ad_middle_outer[middle_depth]
        transported_outer[(0, middle_depth)] = value
        for outer_depth in range(1, depth - middle_depth):
            value = _element_bracket(outer, value)
            transported_outer[(outer_depth, middle_depth)] = value

    velocity: list[Element] = []
    for order in range(depth):
        value: Element = {}
        if order == 0:
            value = _element_add(value, outer)
        value = _element_add(
            value,
            _element_scale(
                ad_outer_middle[order],
                Fraction(1, factorial(order)),
            ),
        )
        for outer_depth in range(order + 1):
            middle_depth = order - outer_depth
            value = _element_add(
                value,
                _element_scale(
                    transported_outer[(outer_depth, middle_depth)],
                    Fraction(
                        1,
                        factorial(outer_depth)
                        * factorial(middle_depth),
                    ),
                ),
            )
        velocity.append(value)

    operations = FormalLieOps[Element](
        zero=dict,
        add=_element_add,
        scale=_element_scale,
        bracket=_element_bracket,
    )
    logarithm = magnus_from_velocity(
        velocity=velocity,
        maximum_order=depth,
        ops=operations,
        placement=VelocityPlacement.LEFT_MULTIPLY,
    )
    first_nonpositive_magnus_contribution: dict[str, object] | None = None
    first_nonpositive_even_wick_adjoint: dict[str, object] | None = None
    structural_audit_depth = min(depth, 15)
    audited_logarithm, first_nonpositive_magnus_contribution = (
        _magnus_contribution_audit(
            velocity[:structural_audit_depth],
            structural_audit_depth,
        )
    )
    assert audited_logarithm == logarithm[: structural_audit_depth + 1]

    wick_logarithm: Element = {}
    for order in range(1, structural_audit_depth + 1, 2):
        for (r, shell_s), coefficient in logarithm[order].items():
            q_degree = shell_s - r + 1
            transformed = _polynomial_scale(
                coefficient,
                Fraction(-((-1) ** (q_degree // 2))),
            )
            wick_logarithm[(r, shell_s)] = transformed
    nested_wick: Element = {(0, 1): {(0, 0): Fraction(1)}}
    for adjoint_depth in range(1, structural_audit_depth):
        nested_wick = _truncate_element(
            _element_bracket(wick_logarithm, nested_wick),
            structural_audit_depth,
        )
        if adjoint_depth % 2:
            continue
        for shell, polynomial in nested_wick.items():
            if any(value < 0 for value in polynomial.values()):
                first_nonpositive_even_wick_adjoint = {
                    "adjoint_depth": adjoint_depth,
                    "shell": list(shell),
                    "polynomial": _polynomial_row(polynomial),
                }
                break
        if first_nonpositive_even_wick_adjoint is not None:
            break

    boundary_rows: list[dict[str, object]] = []
    first_negative_boundary: dict[str, object] | None = None
    first_mixed_wick_shell: dict[str, object] | None = None
    all_wick_shells_nonnegative_after_linear = True

    for order in range(1, depth + 1, 2):
        k = (order + 1) // 2
        boundary = _polynomial_scale(
            logarithm[order].get((k, k - 1), {}),
            Fraction(-1),
        )
        boundary_nonnegative = bool(boundary) and all(
            coefficient >= 0 for coefficient in boundary.values()
        )
        if not boundary_nonnegative and first_negative_boundary is None:
            first_negative_boundary = {
                "order": order,
                "k": k,
                "polynomial": _polynomial_row(boundary),
            }
        boundary_rows.append(
            {
                "order": order,
                "k": k,
                "term_count": len(boundary),
                "coefficientwise_nonnegative": boundary_nonnegative,
                "evaluation_e1_ell3": str(_evaluate(boundary, 1, 3)),
                "coefficients": _polynomial_row(boundary),
            }
        )

        for (r, shell_s), coefficient in logarithm[order].items():
            q_degree = shell_s - r + 1
            assert q_degree >= 0 and q_degree % 2 == 0
            wick = _polynomial_scale(
                coefficient,
                Fraction(-((-1) ** (q_degree // 2))),
            )
            nonnegative = all(value >= 0 for value in wick.values())
            expected_exception = order == 1 and q_degree == 2
            if not nonnegative and not expected_exception:
                all_wick_shells_nonnegative_after_linear = False
                if first_mixed_wick_shell is None:
                    first_mixed_wick_shell = {
                        "order": order,
                        "shell": [r, shell_s],
                        "q_degree": q_degree,
                        "polynomial": _polynomial_row(wick),
                    }

    return {
        "schema": (
            "axiompack.jacobian_fixed_rational_odd_boundary_sparse.v1"
        ),
        "checked_through_order": depth,
        "checked_through_boundary_index": (depth + 1) // 2,
        "first_negative_boundary": first_negative_boundary,
        "first_nonpositive_wick_shell_after_linear": (
            first_mixed_wick_shell
        ),
        "first_nonpositive_wick_magnus_contribution": (
            first_nonpositive_magnus_contribution
        ),
        "first_nonpositive_even_wick_adjoint": (
            first_nonpositive_even_wick_adjoint
        ),
        "structural_audit_through_order": structural_audit_depth,
        "all_checked_boundaries_coefficientwise_nonnegative": (
            first_negative_boundary is None
        ),
        "all_checked_wick_shells_nonnegative_after_linear": (
            all_wick_shells_nonnegative_after_linear
        ),
        "boundary_rows": boundary_rows,
        "claim_boundary": (
            "Sparse exact finite discriminator. Positivity beyond the "
            "declared order still requires an all-order proof."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
