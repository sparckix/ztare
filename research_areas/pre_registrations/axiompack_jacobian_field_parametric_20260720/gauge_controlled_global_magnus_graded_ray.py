#!/usr/bin/env python3
"""Exact bigraded Magnus quotient for the global-control source ray.

For a Hamiltonian monomial ``v**a*z**b`` occurring at logarithmic cost
``q``, put

    I = a - 3*q - 1,   J = b - 2*q - 3.

The weighted Hamiltonian bracket adds ``(q, I, J)``.  All velocity grades
are componentwise nonpositive, and the order-two radial monomial is the
unique grade ``(0, 0)``.  A southwest rectangle is therefore an exact Lie
quotient: a discarded monomial cannot bracket back into it.
"""

from __future__ import annotations

from fractions import Fraction
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

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add,
    _bracket,
    _scale,
    _source_velocity,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    inverse_dexp_coefficients,
)


TARGET_GRADE = (-6, -3)
MAXIMUM_A_FREE_CORE_COST = 36


def _grade(exponent: tuple[int, int], cost: int) -> tuple[int, int]:
    return (
        exponent[0] - 3 * cost - 1,
        exponent[1] - 2 * cost - 3,
    )


def _project(
    value: SparseHamiltonian,
    cost: int,
    minimum_grade: tuple[int, int],
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if all(
            actual >= minimum
            for actual, minimum in zip(
                _grade(exponent, cost), minimum_grade
            )
        )
    }


def _series_bracket(
    left: list[SparseHamiltonian],
    right: list[SparseHamiltonian],
    maximum_order: int,
    minimum_grade: tuple[int, int],
) -> list[SparseHamiltonian]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        if not left_value:
            continue
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            if not right_value:
                continue
            order = left_order + right_order
            bracket = _project(
                _bracket(left_value, right_value, 2),
                order + 1,
                minimum_grade,
            )
            result[order] = _add(result[order], bracket)
    return result


def _projected_magnus(
    velocity: list[SparseHamiltonian],
    maximum_order: int,
    minimum_grade: tuple[int, int],
) -> list[SparseHamiltonian]:
    padded_velocity = [
        _project(value, order + 1, minimum_grade)
        for order, value in enumerate(velocity)
    ] + [
        {} for _ in range(maximum_order - len(velocity))
    ]
    logarithm: list[SparseHamiltonian] = [
        {} for _ in range(maximum_order + 1)
    ]
    inverse = inverse_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for derivative_order in range(maximum_order):
        result = padded_velocity[derivative_order]
        nested = padded_velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = _series_bracket(
                prefix,
                nested,
                derivative_order,
                minimum_grade,
            )
            if inverse[depth]:
                result = _add(
                    result,
                    _scale(nested[derivative_order], inverse[depth]),
                )
        logarithm[derivative_order + 1] = _scale(
            result,
            Fraction(1, derivative_order + 1),
        )
    return logarithm


def _ray_exponent(
    logarithmic_order: int,
    grade: tuple[int, int],
) -> tuple[int, int]:
    return (
        3 * logarithmic_order + 1 + grade[0],
        2 * logarithmic_order + 3 + grade[1],
    )


def _ray_formula(adjoint_depth: int) -> sp.Expr:
    """Coefficient at order ``6 + 2*r`` on grade ``(-6,-3)``."""
    base = sp.Rational(1, 2**20)
    adjoint = (
        base
        * (-sp.Rational(3, 128)) ** adjoint_depth
        * sp.prod(
            2 * index + 1 for index in range(adjoint_depth)
        )
    )
    return sp.factor(
        12
        * sp.bernoulli(adjoint_depth + 2)
        / sp.factorial(adjoint_depth + 2)
        * adjoint
    )


def run(maximum_order: int = 81) -> dict[str, object]:
    if maximum_order < 18:
        raise ValueError("replay must include the first four nonzero terms")

    # The exact all-parameter support check in _source_velocity proves that
    # every Hamiltonian exponent is at most nine.  Hence parameter cost
    # q >= 6 lies strictly southwest of TARGET_GRADE.  Five coefficients
    # are enough for this quotient at arbitrary output order.
    velocity, (_s, _v, _z), _coefficient_p3, _coefficient_pq = (
        _source_velocity(5)
    )
    input_grade_rows = []
    origins = []
    for order, value in enumerate(velocity):
        cost = order + 1
        grades = {
            _grade(exponent, cost): coefficient
            for exponent, coefficient in value.items()
        }
        assert all(
            first <= 0 and second <= 0
            for first, second in grades
        )
        if (0, 0) in grades:
            origins.append((cost, grades[(0, 0)]))
        input_grade_rows.append({
            "parameter_cost": cost,
            "grade_count": len(grades),
            "projected_grade_count": len(
                _project(value, cost, TARGET_GRADE)
            ),
        })
    assert origins == [(2, -sp.Rational(3, 448))]
    assert _project(velocity[4], 5, TARGET_GRADE) == {}

    # Once the unique zero-grade letter is removed, every remaining input
    # has at least one strictly negative grade coordinate.  At most nine
    # such letters can sum to (-6,-3), and each retained input has cost at
    # most four.  Thus cost 36 exhausts all A-free cores.
    without_zero_grade = []
    for order, value in enumerate(velocity):
        cost = order + 1
        without_zero_grade.append({
            exponent: coefficient
            for exponent, coefficient in value.items()
            if _grade(exponent, cost) != (0, 0)
        })
    core_logarithm = _projected_magnus(
        without_zero_grade,
        MAXIMUM_A_FREE_CORE_COST,
        TARGET_GRADE,
    )
    a_free_core_rows = []
    for order in range(1, MAXIMUM_A_FREE_CORE_COST + 1):
        exponent = _ray_exponent(order, TARGET_GRADE)
        coefficient = sp.factor(
            core_logarithm[order].get(exponent, 0)
        )
        if coefficient != 0:
            a_free_core_rows.append({
                "cost": order,
                "hamiltonian_exponent": list(exponent),
                "coefficient": str(coefficient),
            })

    logarithm = _projected_magnus(
        velocity, maximum_order, TARGET_GRADE
    )
    rows = []
    first_formula_failure = None
    first_even_adjoint_zero = None
    for adjoint_depth in range((maximum_order - 6) // 2 + 1):
        order = 6 + 2 * adjoint_depth
        exponent = _ray_exponent(order, TARGET_GRADE)
        actual = sp.factor(logarithm[order].get(exponent, 0))
        expected = _ray_formula(adjoint_depth)
        if first_formula_failure is None and actual != expected:
            first_formula_failure = order
        if (
            first_even_adjoint_zero is None
            and adjoint_depth % 2 == 0
            and actual == 0
        ):
            first_even_adjoint_zero = order
        rows.append({
            "logarithmic_order": order,
            "adjoint_depth": adjoint_depth,
            "hamiltonian_exponent": list(exponent),
            "coefficient": str(actual),
            "bernoulli_index": adjoint_depth + 2,
            "formula_matches": actual == expected,
            "nonzero_on_even_adjoint_depth": (
                adjoint_depth % 2 != 0 or actual != 0
            ),
        })

    expected_prefix = {
        6: sp.Rational(1, 1_048_576),
        10: -sp.Rational(9, 343_597_383_680),
        14: sp.Rational(27, 2_251_799_813_685_248),
        18: -sp.Rational(
            24_057, 1_475_739_525_896_764_129_280
        ),
    }
    assert all(
        logarithm[order].get(
            _ray_exponent(order, TARGET_GRADE), 0
        ) == coefficient
        for order, coefficient in expected_prefix.items()
    )
    assert first_formula_failure is None
    assert first_even_adjoint_zero is None

    x = sp.symbols("x")
    return {
        "schema": (
            "axiompack.jacobian_controlled_global_"
            "magnus_graded_ray.v1"
        ),
        "grading": {
            "I": "hamiltonian_v_exponent - 3*cost - 1",
            "J": "hamiltonian_z_exponent - 2*cost - 3",
            "target_grade": list(TARGET_GRADE),
            "bracket_additive": True,
            "velocity_grades_componentwise_nonpositive": True,
            "unique_zero_grade": {
                "parameter_cost": 2,
                "hamiltonian": "-3*(v*z)^7/448",
            },
            "uniform_hamiltonian_exponent_upper_bound": 9,
            "input_rows": input_grade_rows,
        },
        "maximum_checked_logarithmic_order": maximum_order,
        "a_free_core_exhaustion": {
            "maximum_possible_cost": MAXIMUM_A_FREE_CORE_COST,
            "nonzero_rows": a_free_core_rows,
            "complete_by_grade_and_cost_bound": True,
        },
        "first_formula_failure": first_formula_failure,
        "first_even_adjoint_zero": first_even_adjoint_zero,
        "coefficient_formula": (
            "c_r = 2^-20*(-3/128)^r*(2r-1)!!"
            "*12*B_(r+2)/(r+2)!"
        ),
        "formal_generating_function": str(
            12
            / x**2
            * (x / (sp.exp(x) - 1) - 1 + x / 2)
        ),
        "nonzero_subsequence": {
            "orders": "n=6+4*m, m>=0",
            "hamiltonian": (
                "c_(2m)*v^(3*n-5)*z^(2*n)"
            ),
            "source_derivation_degree": "5*n-8",
            "reason": "B_(2*m+2) is nonzero over characteristic zero",
        },
        "rows": rows,
        "claim_boundary": (
            "Exact closed bigraded quotient and finite coefficient replay "
            "through the declared order. The Bernoulli generating function "
            "is the all-order candidate extracted from the quotient; a "
            "separate symbolic derivation of the projected Magnus equation "
            "is required before treating the finite replay as an "
            "all-order theorem."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
