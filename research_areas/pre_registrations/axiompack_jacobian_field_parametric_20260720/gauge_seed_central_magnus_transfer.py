#!/usr/bin/env python3
"""All-order source-ray transfer for the seed-central cancellation.

The target perturbation

    K_s -> K_s - (9/28)*s*H_0**2,
    H_0 = -P**3/36 - Q**2/4,

cancels the earlier grade-zero source monomial.  Its seed pullback creates a
new radial logarithmic generator ``A = -9*u**12*z**12/458752``.  In the
closed bigraded quotient below, the connection has only a cost-two
logarithm and a cost-four velocity.  The terminal response is therefore the
universal function

    phi_3(x) = x/(exp(x)-1) * integral_0^1 t**3 exp(t**2*x) dt.

A finite negative-grade correction changes the first orbit coefficient by
``-12/37``; after that, only the radial generator can act.
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

from gauge_controlled_global_magnus_all_order import (  # noqa: E402
    EXPECTED_TRANSLATED_VELOCITY,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add,
    _bracket,
    _scale,
)
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)


TARGET_GRADE = (-22, -16)


def _grade(
    exponent: tuple[int, int],
    cost: int,
) -> tuple[int, int]:
    return (
        2 * exponent[0] - 11 * cost - 2,
        2 * exponent[1] - 9 * cost - 6,
    )


def _project(
    value: SparseHamiltonian,
    cost: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if all(
            actual >= minimum
            for actual, minimum in zip(
                _grade(exponent, cost), TARGET_GRADE
            )
        )
    }


def _to_sparse(
    value: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> SparseHamiltonian:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in sp.Poly(
            sp.expand(value), u, z
        ).terms()
        if coefficient != 0
    }


def _velocity() -> tuple[
    list[SparseHamiltonian],
    tuple[sp.Symbol, sp.Symbol],
]:
    data = source_only_connection()
    s, v, t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u, z = sp.symbols("u z")
    substitution = {
        v: u - 1,
        t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.cancel(family_p.subs(substitution))
    q = sp.cancel(family_q.subs(substitution))
    p_series = sp.series(p, s, 0, 4).removeO().expand()
    q_series = sp.series(q, s, 0, 4).removeO().expand()
    h_zero = -p_series**3 / 36 - q_series**2 / 4
    perturbation = sp.expand(
        -sp.Rational(18, 7) * s * h_zero**2
    )

    velocity = []
    for order in range(4):
        perturbation_coefficient = _to_sparse(
            perturbation.coeff(s, order), u, z
        )
        base = EXPECTED_TRANSLATED_VELOCITY.get(
            order + 1, {}
        )
        velocity.append(
            _project(
                _add(base, perturbation_coefficient),
                order + 1,
            )
        )
    return velocity, (u, z)


def run(maximum_orbit_depth: int = 20) -> dict[str, object]:
    if maximum_orbit_depth < 8:
        raise ValueError("orbit replay must include held-out depths")

    velocity, (_u, _z) = _velocity()
    assert velocity[0] == {}
    assert velocity[2] == {}
    assert velocity[1]
    assert velocity[3]

    l_two = _scale(velocity[1], Fraction(1, 2))
    zero_grade = {
        exponent: coefficient
        for exponent, coefficient in l_two.items()
        if _grade(exponent, 2) == (0, 0)
    }
    assert zero_grade == {
        (12, 12): -sp.Rational(9, 458752)
    }
    assert all(
        first <= 0 and second <= 0
        for first, second in (
            _grade(exponent, 2)
            for exponent in l_two
        )
    )

    expected_cost_four = {
        (14, 14): sp.Rational(9, 1048576),
        (13, 13): sp.Rational(123, 1835008),
        (12, 13): -sp.Rational(111, 3670016),
    }
    assert velocity[3] == expected_cost_four
    assert {
        exponent: _grade(exponent, 4)
        for exponent in velocity[3]
    } == {
        (14, 14): (-18, -14),
        (13, 13): (-20, -16),
        (12, 13): TARGET_GRADE,
    }

    a_coefficient = next(iter(zero_grade.values()))
    terminal_seed_coefficient = velocity[3][(12, 13)]
    first_iterate = _project(
        _bracket(l_two, velocity[3], 2), 6
    )
    assert {
        exponent: coefficient
        for exponent, coefficient in first_iterate.items()
        if _grade(exponent, 6) == TARGET_GRADE
    } == {
        (23, 22): sp.Rational(
            243, 105226698752
        )
    }
    pure_first = sp.factor(
        terminal_seed_coefficient
        * a_coefficient
        * 12
        * (-1)
    )
    first_coefficient = first_iterate[(23, 22)]
    finite_core_ratio = sp.factor(
        first_coefficient / pure_first
    )
    assert finite_core_ratio == -sp.Rational(12, 37)

    # Once TARGET_GRADE is reached, any strict negative grade leaves the
    # quotient.  Thus every subsequent nonzero outer bracket uses A.
    current = velocity[3]
    orbit_rows = []
    for depth in range(maximum_orbit_depth + 1):
        order = 4 + 2 * depth
        exponent = (
            12 + 11 * depth,
            13 + 9 * depth,
        )
        actual = sp.factor(current.get(exponent, 0))
        if depth == 0:
            expected = terminal_seed_coefficient
        else:
            expected = first_coefficient
            for index in range(1, depth):
                expected *= (
                    a_coefficient
                    * 12
                    * (2 * index - 1)
                )
            expected = sp.factor(expected)
        assert actual == expected
        orbit_rows.append({
            "depth": depth,
            "logarithmic_order": order,
            "exponent": list(exponent),
            "iterated_bracket_coefficient": str(actual),
        })
        current = _project(
            _bracket(l_two, current, 2),
            order + 2,
        )

    x = sp.symbols("x")
    bernoulli = x / (sp.exp(x) - 1)
    response = sp.Rational(1, 2) + (
        bernoulli - 1
    ) / (2 * x)
    integral_form = sp.factor(
        bernoulli
        * (
            sp.exp(x) * (x - 1) + 1
        )
        / (2 * x**2)
    )
    assert sp.simplify(response - integral_form) == 0
    assert sp.limit(response, x, 0) == sp.Rational(1, 4)

    # For depth k>=1, [x^k]phi_3 =
    # B_(k+1)/(2*(k+1)!).  Even Bernoulli nonvanishing therefore gives
    # the subsequence k=2m+1.
    response_prefix = sp.series(
        response, x, 0, maximum_orbit_depth + 1
    ).removeO().expand()
    coefficient_rows = []
    for depth in range(maximum_orbit_depth + 1):
        actual = sp.factor(response_prefix.coeff(x, depth))
        expected = (
            sp.Rational(1, 4)
            if depth == 0
            else sp.factor(
                sp.bernoulli(depth + 1)
                / (
                    2 * sp.factorial(depth + 1)
                )
            )
        )
        assert actual == expected
        coefficient_rows.append({
            "depth": depth,
            "response_coefficient": str(actual),
            "formula_matches": True,
        })

    return {
        "schema": (
            "axiompack.jacobian_seed_central_"
            "magnus_transfer.v1"
        ),
        "target_perturbation": "-(9/28)*s*H_0^2",
        "source_hamiltonian_perturbation": (
            "-(18/7)*s*H_0(P_s,Q_s)^2"
        ),
        "closed_quotient": {
            "grade": (
                "(2*a-11*q-2, 2*b-9*q-6)"
            ),
            "target_grade": list(TARGET_GRADE),
            "velocity_costs": [2, 4],
            "unique_zero_grade": (
                "-9*u^12*z^12/458752 at cost 2"
            ),
            "cost_four_velocity": {
                f"{exponent[0]},{exponent[1]}": str(coefficient)
                for exponent, coefficient in velocity[3].items()
            },
            "finite_core_ratio": str(finite_core_ratio),
        },
        "universal_response": {
            "phi_3": str(response),
            "coefficient_at_zero": "1/4",
            "coefficient_at_k_ge_1": (
                "B_(k+1)/(2*(k+1)!)"
            ),
        },
        "nonzero_subsequence": {
            "orbit_depth": "k=2*m+1",
            "logarithmic_order": "n=6+4*m",
            "hamiltonian": (
                "nonzero scalar * "
                "u^((11*n-20)/2)*z^((9*n-10)/2)"
            ),
            "source_derivation_degree": "10*n-18",
        },
        "orbit_rows": orbit_rows,
        "response_rows": coefficient_rows,
        "claim_boundary": (
            "All-order source logarithmic escape for the seed-central "
            "cancellation candidate. This kills that candidate but does "
            "not constrain a later coefficientwise moving staircase."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
