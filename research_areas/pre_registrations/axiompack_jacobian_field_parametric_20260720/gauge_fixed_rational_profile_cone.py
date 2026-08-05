#!/usr/bin/env python3
"""Exact weighted-profile discriminator for the symmetric cusp BCH."""

from __future__ import annotations

from fractions import Fraction
from importlib.util import module_from_spec, spec_from_file_location
import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

SPARSE_PATH = HERE / "gauge_fixed_rational_odd_boundary_sparse.py"
SPARSE_SPEC = spec_from_file_location("gauge_odd_sparse", SPARSE_PATH)
if SPARSE_SPEC is None or SPARSE_SPEC.loader is None:
    raise RuntimeError("could not load the sparse odd-boundary replay")
SPARSE = module_from_spec(SPARSE_SPEC)
SPARSE_SPEC.loader.exec_module(SPARSE)

from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


Polynomial = dict[tuple[int, int], Fraction]
Shell = tuple[int, int]
Element = dict[Shell, Polynomial]


def _compute_logarithm(depth: int) -> list[Element]:
    one: Polynomial = {(0, 0): Fraction(1)}
    e: Polynomial = {(1, 0): Fraction(1)}
    ell: Polynomial = {(0, 1): Fraction(1)}
    outer: Element = {
        (0, 1): SPARSE._polynomial_scale(e, Fraction(-1, 2))
    }
    middle: Element = {
        (1, 0): SPARSE._polynomial_scale(one, Fraction(-1)),
        (0, 1): SPARSE._polynomial_scale(ell, Fraction(-1)),
    }

    ad_outer_middle = [middle]
    for _ in range(1, depth):
        ad_outer_middle.append(
            SPARSE._element_bracket(outer, ad_outer_middle[-1])
        )

    ad_middle_outer = [outer]
    for _ in range(1, depth):
        ad_middle_outer.append(
            SPARSE._element_bracket(middle, ad_middle_outer[-1])
        )

    transported_outer: dict[tuple[int, int], Element] = {}
    for middle_depth in range(depth):
        value = ad_middle_outer[middle_depth]
        transported_outer[(0, middle_depth)] = value
        for outer_depth in range(1, depth - middle_depth):
            value = SPARSE._element_bracket(outer, value)
            transported_outer[(outer_depth, middle_depth)] = value

    velocity: list[Element] = []
    for order in range(depth):
        value: Element = {}
        if order == 0:
            value = SPARSE._element_add(value, outer)
        value = SPARSE._element_add(
            value,
            SPARSE._element_scale(
                ad_outer_middle[order],
                Fraction(1, factorial(order)),
            ),
        )
        for outer_depth in range(order + 1):
            middle_depth = order - outer_depth
            value = SPARSE._element_add(
                value,
                SPARSE._element_scale(
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
        add=SPARSE._element_add,
        scale=SPARSE._element_scale,
        bracket=SPARSE._element_bracket,
    )
    return magnus_from_velocity(
        velocity=velocity,
        maximum_order=depth,
        ops=operations,
        placement=VelocityPlacement.LEFT_MULTIPLY,
    )


def _wick_polynomial(shell: Shell, value: Polynomial) -> Polynomial:
    q_degree = shell[1] - shell[0] + 1
    assert q_degree >= 0 and q_degree % 2 == 0
    return SPARSE._polynomial_scale(
        value,
        Fraction(-((-1) ** (q_degree // 2))),
    )


def _profile_rows(
    logarithm: list[Element],
    depth: int,
) -> tuple[list[dict[str, object]], sp.Expr, sp.Expr]:
    p, tau = sp.symbols("p tau")
    source_zero_jet = sp.Integer(0)
    source_two_jet = sp.Integer(0)
    rows: list[dict[str, object]] = []
    previous_root_intervals: list[
        tuple[sp.Rational, sp.Rational]
    ] | None = None
    for order in range(1, depth + 1, 2):
        k = (order + 1) // 2
        coefficients: dict[int, Fraction] = {}
        for shell, polynomial in logarithm[order].items():
            q_degree = shell[1] - shell[0] + 1
            wick = _wick_polynomial(shell, polynomial)
            evaluated = SPARSE._evaluate(wick, 1, 3)
            u_power = q_degree // 2
            coefficients[u_power] = (
                coefficients.get(u_power, Fraction(0)) + evaluated
            )
            p_degree = 2 * shell[0] - shell[1] + 1
            term = (
                sp.Rational(evaluated.numerator, evaluated.denominator)
                * tau**order
                * p**p_degree
            )
            if q_degree == 0:
                source_zero_jet += term
            elif q_degree == 2:
                source_two_jet += term

        expected_negative_seed = order == 1
        higher_nonnegative = all(
            value >= 0 for value in coefficients.values()
        )
        if expected_negative_seed:
            assert coefficients == {
                0: Fraction(1),
                1: Fraction(-4),
            }
        else:
            assert higher_nonnegative
        u = sp.symbols("u")
        profile = sum(
            sp.Rational(value.numerator, value.denominator) * u**power
            for power, value in coefficients.items()
        )
        roots = []
        root_intervals: list[tuple[sp.Rational, sp.Rational]] = []
        if sp.degree(profile, u) > 0:
            roots = [complex(root) for root in sp.nroots(profile)]
            isolated = sp.Poly(profile, u).intervals(
                eps=sp.Rational(1, 10**12),
            )
            assert all(multiplicity == 1 for _, multiplicity in isolated)
            root_intervals = [
                (
                    sp.Rational(interval[0]),
                    sp.Rational(interval[1]),
                )
                for interval, _ in isolated
            ]
        exact_real_negative = (
            len(root_intervals) == sp.degree(profile, u)
            and all(upper < 0 for _, upper in root_intervals)
        )
        interlaces_previous = None
        if order > 3 and previous_root_intervals is not None:
            previous_degree = len(previous_root_intervals)
            current_degree = len(root_intervals)
            if current_degree == previous_degree:
                interlaces_previous = all(
                    previous_root_intervals[index][1]
                    < root_intervals[index][0]
                    and (
                        index == previous_degree - 1
                        or root_intervals[index][1]
                        < previous_root_intervals[index + 1][0]
                    )
                    for index in range(current_degree)
                )
            elif current_degree == previous_degree + 1:
                interlaces_previous = all(
                    root_intervals[index][1]
                    < previous_root_intervals[index][0]
                    and previous_root_intervals[index][1]
                    < root_intervals[index + 1][0]
                    for index in range(previous_degree)
                )
            else:
                interlaces_previous = False
        rows.append(
            {
                "order": order,
                "k": k,
                "profile": str(sp.factor(profile)),
                "coefficientwise_nonnegative": higher_nonnegative,
                "expected_negative_linear_seed": expected_negative_seed,
                "coefficients_ascending": [
                    str(coefficients[power])
                    for power in range(max(coefficients) + 1)
                ],
                "degree": int(sp.degree(profile, u)),
                "all_roots_in_open_left_half_plane": exact_real_negative,
                "all_roots_real": (
                    len(root_intervals) == sp.degree(profile, u)
                ),
                "strictly_interlaces_previous_higher_profile": (
                    interlaces_previous
                ),
                "exact_root_isolating_intervals": [
                    [str(lower), str(upper)]
                    for lower, upper in root_intervals
                ],
                "roots": [
                    {
                        "real": float(root.real),
                        "imaginary": float(root.imag),
                    }
                    for root in roots
                ],
            }
        )
        if order > 1:
            previous_root_intervals = root_intervals
    return rows, sp.expand(source_zero_jet), sp.expand(source_two_jet)


def _adjacent_coefficient_minor_audit(
    profile_rows: list[dict[str, object]],
) -> dict[str, object]:
    higher_rows = [
        row for row in profile_rows if int(row["order"]) > 1
    ]
    checked_minor_count = 0
    first_nonpositive = None
    for previous, current in zip(higher_rows, higher_rows[1:]):
        previous_coefficients = [
            Fraction(value)
            for value in previous["coefficients_ascending"]
        ]
        current_coefficients = [
            Fraction(value)
            for value in current["coefficients_ascending"]
        ]
        common_length = min(
            len(previous_coefficients),
            len(current_coefficients),
        )
        for first_index in range(common_length):
            for second_index in range(
                first_index + 1,
                common_length,
            ):
                determinant = (
                    previous_coefficients[first_index]
                    * current_coefficients[second_index]
                    - previous_coefficients[second_index]
                    * current_coefficients[first_index]
                )
                checked_minor_count += 1
                if determinant <= 0 and first_nonpositive is None:
                    first_nonpositive = {
                        "previous_order": previous["order"],
                        "current_order": current["order"],
                        "columns": [first_index, second_index],
                        "determinant": str(determinant),
                    }
    return {
        "checked_minor_count": checked_minor_count,
        "all_adjacent_two_by_two_minors_strictly_positive": (
            first_nonpositive is None
        ),
        "first_nonpositive": first_nonpositive,
    }


def _symbolic_profile_stability_audit(
    logarithm: list[Element],
    depth: int,
    maximum_k: int,
    profile_rows: list[dict[str, object]],
) -> dict[str, object]:
    t, u = sp.symbols("t u")
    profiles: dict[int, sp.Expr] = {}
    discriminant_rows: list[dict[str, object]] = []
    all_amplitude_homogeneous = True
    for order in range(3, depth + 1, 2):
        k = (order + 1) // 2
        if k > maximum_k:
            break
        profile = sp.Integer(0)
        for shell, polynomial in logarithm[order].items():
            q_degree = shell[1] - shell[0] + 1
            u_power = q_degree // 2
            wick = _wick_polynomial(shell, polynomial)
            amplitude_degrees = {
                e_power + ell_power
                for e_power, ell_power in wick
            }
            expected_amplitude_degree = k - 1 + u_power
            if amplitude_degrees != {expected_amplitude_degree}:
                all_amplitude_homogeneous = False
            coefficient = sum(
                sp.Rational(value.numerator, value.denominator)
                * t**e_power
                for (e_power, _), value in wick.items()
            )
            profile += coefficient * u**u_power
        profile = sp.expand(profile)
        profiles[k] = profile
        degree = int(sp.degree(profile, u))
        if degree <= 1:
            discriminant = sp.Integer(1)
        else:
            discriminant = sp.expand(sp.discriminant(profile, u))
        discriminant_polynomial = sp.Poly(discriminant, t)
        positive = all(
            coefficient > 0
            for coefficient in discriminant_polynomial.coeffs()
        )
        discriminant_rows.append(
            {
                "k": k,
                "order": order,
                "profile_degree": degree,
                "discriminant_term_count_after_ell_one": len(
                    discriminant_polynomial.terms()
                ),
                "discriminant_coefficients_strictly_positive": positive,
            }
        )

    resultant_rows: list[dict[str, object]] = []
    for k in range(2, max(profiles)):
        resultant = sp.Poly(
            sp.expand(
                sp.resultant(profiles[k], profiles[k + 1], u)
            ),
            t,
        )
        signs = {
            sp.sign(coefficient)
            for coefficient in resultant.coeffs()
        }
        fixed_nonzero_sign = (
            len(signs) == 1 and signs != {sp.Integer(0)}
        )
        resultant_rows.append(
            {
                "previous_k": k,
                "current_k": k + 1,
                "resultant_term_count_after_ell_one": len(
                    resultant.terms()
                ),
                "all_coefficients_have_one_nonzero_sign": (
                    fixed_nonzero_sign
                ),
                "coefficient_sign": (
                    str(next(iter(signs)))
                    if fixed_nonzero_sign
                    else None
                ),
            }
        )

    all_discriminants_positive = all(
        row["discriminant_coefficients_strictly_positive"]
        for row in discriminant_rows
    )
    all_resultants_fixed_sign = all(
        row["all_coefficients_have_one_nonzero_sign"]
        for row in resultant_rows
    )
    basepoint_rows = [
        row
        for row in profile_rows
        if 1 < int(row["k"]) <= maximum_k
    ]
    basepoint_negative_roots = all(
        row["all_roots_real"]
        and row["all_roots_in_open_left_half_plane"]
        for row in basepoint_rows
    )
    basepoint_interlacing = all(
        row["strictly_interlaces_previous_higher_profile"]
        for row in basepoint_rows
        if int(row["k"]) > 2
    )
    return {
        "checked_through_k": max(profiles),
        "amplitude_homogeneity_verified": all_amplitude_homogeneous,
        "all_discriminants_coefficientwise_positive_after_ell_one": (
            all_discriminants_positive
        ),
        "all_adjacent_resultants_have_one_nonzero_coefficient_sign": (
            all_resultants_fixed_sign
        ),
        "basepoint_e1_ell3_has_negative_roots": (
            basepoint_negative_roots
        ),
        "basepoint_e1_ell3_strictly_interlaces": (
            basepoint_interlacing
        ),
        "parameter_uniform_negative_roots_and_interlacing": (
            all_amplitude_homogeneous
            and all_discriminants_positive
            and all_resultants_fixed_sign
            and basepoint_negative_roots
            and basepoint_interlacing
        ),
        "discriminant_rows": discriminant_rows,
        "resultant_rows": resultant_rows,
    }


def _truncate_tau(value: sp.Expr, tau: sp.Symbol, depth: int) -> sp.Expr:
    return sp.expand(
        sum(
            coefficient * tau**power
            for (power,), coefficient in sp.Poly(
                sp.expand(value), tau
            ).terms()
            if power <= depth
        )
    )


def _wronskian_audit(
    source_zero_jet: sp.Expr,
    source_two_jet: sp.Expr,
    depth: int,
) -> dict[str, object]:
    p, tau = sp.symbols("p tau")
    wronskian = _truncate_tau(
        sp.diff(source_zero_jet, p) * sp.diff(source_two_jet, p)
        - source_two_jet * sp.diff(source_zero_jet, p, 2),
        tau,
        depth,
    )
    polynomial = sp.Poly(wronskian, tau, p)
    negative = [
        {
            "tau_power": powers[0],
            "p_power": powers[1],
            "coefficient": str(coefficient),
        }
        for powers, coefficient in polynomial.terms()
        if coefficient < 0
    ]
    return {
        "checked_through_parameter_order": depth,
        "coefficientwise_nonnegative": not negative,
        "first_negative": negative[0] if negative else None,
        "term_count": len(polynomial.terms()),
    }


def _even_adjoint_boundary_audit(
    logarithm: list[Element],
    depth: int,
    maximum_adjoint_depth: int,
) -> list[dict[str, object]]:
    wick_logarithm: Element = {}
    for order in range(1, depth + 1, 2):
        for shell, polynomial in logarithm[order].items():
            wick_logarithm[shell] = _wick_polynomial(shell, polynomial)

    nested: Element = {(0, 1): {(0, 0): Fraction(1)}}
    rows: list[dict[str, object]] = []
    for adjoint_depth in range(1, maximum_adjoint_depth + 1):
        nested = SPARSE._truncate_element(
            SPARSE._element_bracket(wick_logarithm, nested),
            depth + 1,
        )
        if adjoint_depth % 2:
            continue
        boundary = {
            shell: polynomial
            for shell, polynomial in nested.items()
            if shell[1] - shell[0] + 1 == 0
        }
        first_negative = None
        for shell, polynomial in sorted(boundary.items()):
            for power, coefficient in sorted(polynomial.items()):
                if coefficient < 0:
                    first_negative = {
                        "shell": list(shell),
                        "e_power": power[0],
                        "ell_power": power[1],
                        "coefficient": str(coefficient),
                    }
                    break
            if first_negative is not None:
                break
        rows.append(
            {
                "adjoint_depth": adjoint_depth,
                "boundary_shell_count": len(boundary),
                "boundary_coefficientwise_nonnegative": (
                    first_negative is None
                ),
                "first_negative": first_negative,
            }
        )
    return rows


def _verify_serre_relations() -> dict[str, object]:
    one: Polynomial = {(0, 0): Fraction(1)}
    x: Element = {(1, 0): one}
    y: Element = {(0, 1): one}

    ad_x_y = y
    x_rows = []
    for depth in range(1, 4):
        ad_x_y = SPARSE._element_bracket(x, ad_x_y)
        x_rows.append(bool(ad_x_y))

    ad_y_x = x
    y_rows = []
    for depth in range(1, 5):
        ad_y_x = SPARSE._element_bracket(y, ad_y_x)
        y_rows.append(bool(ad_y_x))

    assert x_rows == [True, True, False]
    assert y_rows == [True, True, True, False]
    return {
        "ad_X_powers_on_Y_nonzero": x_rows,
        "ad_Y_powers_on_X_nonzero": y_rows,
        "generalized_cartan_matrix": [[2, -2], [-3, 2]],
    }


def _verify_profile_bracket() -> bool:
    p, q = sp.symbols("p q")
    for first_q_degree in range(5):
        for second_q_degree in range(5):
            first_p_degree = 9 - 3 * first_q_degree // 2
            second_p_degree = 8 - 3 * second_q_degree // 2
            if (
                2 * first_p_degree + 3 * first_q_degree != 18
                or 2 * second_p_degree + 3 * second_q_degree != 16
            ):
                continue
            first = p**first_p_degree * q**first_q_degree
            second = p**second_p_degree * q**second_q_degree
            direct = sp.expand(
                sp.diff(first, q) * sp.diff(second, p)
                - sp.diff(first, p) * sp.diff(second, q)
            )
            a = sp.Rational(9)
            b = sp.Rational(8)
            x = sp.symbols("x")
            f = x**first_q_degree
            g = x**second_q_degree
            profile = sp.expand(
                b * sp.diff(f, x) * g
                - a * f * sp.diff(g, x)
            )
            expected = sp.expand(
                p ** (a + b - sp.Rational(5, 2))
                * profile.subs(x, q / p ** sp.Rational(3, 2))
            )
            assert sp.expand(direct - expected) == 0
    return True


def _perturbation_witness() -> dict[str, str]:
    p, c, d, m = sp.symbols("p c d m", positive=True)
    a = p**3 + c * p**4
    b = -m + d * p
    wronskian = sp.factor(
        sp.diff(a, p) * sp.diff(b, p)
        - b * sp.diff(a, p, 2)
    )
    assert sp.expand(wronskian).coeff(p, 3) == -8 * c * d
    return {
        "A": str(a),
        "B": str(b),
        "A_prime_B_prime_minus_B_A_double_prime": str(wronskian),
        "negative_high_coefficient": "-8*c*d at p^3",
    }


def run(
    depth: int = 21,
    maximum_adjoint_depth: int = 8,
    symbolic_maximum_k: int = 11,
) -> dict[str, object]:
    if depth < 7 or depth % 2 == 0:
        raise ValueError("depth must be odd and at least seven")
    logarithm = _compute_logarithm(depth)
    profile_rows, source_zero_jet, source_two_jet = _profile_rows(
        logarithm,
        depth,
    )
    even_adjoint_rows = _even_adjoint_boundary_audit(
        logarithm,
        depth,
        maximum_adjoint_depth,
    )
    return {
        "schema": "axiompack.jacobian_fixed_rational_profile_cone.v1",
        "checked_through_logarithmic_order": depth,
        "profile_bracket_verified": _verify_profile_bracket(),
        "serre_relations": _verify_serre_relations(),
        "profile_rows_at_e1_ell3": profile_rows,
        "all_higher_profiles_coefficientwise_nonnegative": all(
            row["coefficientwise_nonnegative"]
            for row in profile_rows
            if row["order"] > 1
        ),
        "all_profiles_hurwitz_stable": all(
            row["all_roots_in_open_left_half_plane"]
            for row in profile_rows
            if row["order"] > 1 and row["degree"] > 0
        ),
        "all_profiles_real_rooted": all(
            row["all_roots_real"]
            for row in profile_rows
            if row["order"] > 1 and row["degree"] > 0
        ),
        "all_consecutive_higher_profiles_strictly_interlace": all(
            row["strictly_interlaces_previous_higher_profile"]
            for row in profile_rows
            if row["order"] > 3
        ),
        "adjacent_profile_coefficient_minors": (
            _adjacent_coefficient_minor_audit(profile_rows)
        ),
        "symbolic_profile_stability": (
            _symbolic_profile_stability_audit(
                logarithm,
                depth,
                min(symbolic_maximum_k, (depth + 1) // 2),
                profile_rows,
            )
        ),
        "first_boundary_wronskian": _wronskian_audit(
            source_zero_jet,
            source_two_jet,
            depth,
        ),
        "even_adjoint_boundary_rows": even_adjoint_rows,
        "all_checked_even_adjoint_boundaries_nonnegative": all(
            row["boundary_coefficientwise_nonnegative"]
            for row in even_adjoint_rows
        ),
        "positive_profile_cone_counterexample": _perturbation_witness(),
        "claim_boundary": (
            "Finite exact discriminator for the correlated profile cone; "
            "an invariant inequality family is still required."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
