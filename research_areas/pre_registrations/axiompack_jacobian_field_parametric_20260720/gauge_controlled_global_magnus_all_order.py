#!/usr/bin/env python3
"""All-order terminal-ray certificate for the global source connection.

The affine translation ``u = 1 + v`` turns the grade-zero Hamiltonian into
the radial monomial ``-3*(u*z)**7/896``.  In the southwest quotient
``I >= -6, J >= -3`` the logarithm outside terminal grade ``(-6, -3)``
has only the three coefficients ``L_2, L_3, L_4``.  Their brackets form
two terminal cores.  Once either core is formed, only the grade-zero
monomial can bracket without leaving the quotient.

That structure sums the complete forward-dexp tail symbolically.  The even
terminal component obeys one scalar formal differential equation whose
unique solution is a Bernoulli divided difference.
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

from gauge_controlled_global_magnus_graded_ray import (  # noqa: E402
    TARGET_GRADE,
    _grade,
    _project,
    _projected_magnus,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _bracket,
    _scale,
    _source_velocity,
)


EXPECTED_TRANSLATED_VELOCITY: dict[
    int, dict[tuple[int, int], sp.Rational]
] = {
    2: {
        (2, 4): -sp.Rational(3, 32),
        (3, 4): -sp.Rational(1, 4),
        (3, 5): -sp.Rational(1, 48),
        (4, 4): -sp.Rational(1, 8),
        (4, 5): sp.Rational(13, 64),
        (5, 5): sp.Rational(37, 160),
        (5, 6): sp.Rational(1, 64),
        (6, 6): -sp.Rational(37, 384),
        (7, 7): -sp.Rational(3, 448),
    },
    3: {
        (4, 6): sp.Rational(5, 768),
        (5, 6): -sp.Rational(3, 32),
        (6, 6): -sp.Rational(13, 96),
        (6, 7): -sp.Rational(7, 768),
        (7, 7): sp.Rational(101, 2688),
        (8, 8): sp.Rational(7, 2048),
    },
    4: {
        (7, 8): sp.Rational(7, 3072),
        (8, 8): -sp.Rational(79, 12288),
        (9, 9): -sp.Rational(1, 2304),
    },
}


def _translated_projected_velocity() -> list[SparseHamiltonian]:
    velocity, (_s, v, z), _coefficient_p3, _coefficient_pq = (
        _source_velocity(5)
    )
    u = sp.symbols("u")
    translated: list[SparseHamiltonian] = []
    for order, value in enumerate(velocity):
        cost = order + 1
        expression = sp.expand(
            sum(
                (
                    coefficient * v**exponent[0] * z**exponent[1]
                    for exponent, coefficient in value.items()
                ),
                sp.Integer(0),
            ).subs(v, u - 1)
        )
        sparse = (
            {
                exponent: sp.cancel(coefficient)
                for exponent, coefficient in sp.Poly(
                    expression, u, z
                ).terms()
                if coefficient != 0
            }
            if expression != 0
            else {}
        )
        translated.append(
            _project(sparse, cost, TARGET_GRADE)
        )
    assert translated == [
        EXPECTED_TRANSLATED_VELOCITY.get(cost, {})
        for cost in range(1, 6)
    ]
    return translated


def _terminal_part(
    value: SparseHamiltonian,
    cost: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if _grade(exponent, cost) == TARGET_GRADE
    }


def _nonterminal_part(
    value: SparseHamiltonian,
    cost: int,
) -> SparseHamiltonian:
    return {
        exponent: coefficient
        for exponent, coefficient in value.items()
        if _grade(exponent, cost) != TARGET_GRADE
    }


def _adjoint_multiplier(depth: int) -> sp.Rational:
    value = sp.Integer(1)
    for index in range(depth):
        value *= -sp.Rational(3, 128) * (2 * index - 1)
    return sp.factor(value)


def _even_orbit_coefficient(depth: int) -> sp.Expr:
    if depth == 0:
        return sp.Rational(7, 12288)
    return sp.factor(
        sp.bernoulli(depth + 1)
        / (
            sp.Integer(2048)
            * sp.factorial(depth + 1)
        )
    )


def run(maximum_replay_order: int = 81) -> dict[str, object]:
    if maximum_replay_order < 18:
        raise ValueError("replay must include four nonzero ray terms")

    velocity = _translated_projected_velocity()
    logarithmic_coefficients = {
        cost: _scale(
            EXPECTED_TRANSLATED_VELOCITY[cost],
            Fraction(1, cost),
        )
        for cost in (2, 3, 4)
    }
    lower = {
        cost: _nonterminal_part(
            logarithmic_coefficients[cost], cost
        )
        for cost in (2, 3, 4)
    }
    terminal = {
        cost: _terminal_part(
            logarithmic_coefficients[cost], cost
        )
        for cost in (2, 3, 4)
    }

    # The only grade-zero logarithmic monomial is A.  Every other retained
    # grade is componentwise nonpositive and has a strict negative entry.
    zero_grade = {
        exponent: coefficient
        for exponent, coefficient in lower[2].items()
        if _grade(exponent, 2) == (0, 0)
    }
    assert zero_grade == {
        (7, 7): -sp.Rational(3, 896)
    }
    assert all(
        _grade(exponent, cost) != (0, 0)
        for cost in (3, 4)
        for exponent in lower[cost]
    )

    # All brackets among the three nonterminal logarithmic coefficients
    # either vanish or enter the terminal grade immediately.
    odd_core = _project(
        _bracket(lower[2], lower[3], 2),
        5,
        TARGET_GRADE,
    )
    even_core = _project(
        _bracket(lower[2], lower[4], 2),
        6,
        TARGET_GRADE,
    )
    mixed_high_core = _project(
        _bracket(lower[3], lower[4], 2),
        7,
        TARGET_GRADE,
    )
    assert odd_core == {
        (10, 10): -sp.Rational(7, 32768)
    }
    assert even_core == {
        (13, 12): -sp.Rational(1, 131072)
    }
    assert mixed_high_core == {}
    assert all(
        _grade(exponent, cost) == TARGET_GRADE
        for cost, core in ((5, odd_core), (6, even_core))
        for exponent in core
    )

    # Once terminal grade is reached, adding any strict negative grade
    # exits the southwest rectangle.  Therefore only A can occur in every
    # subsequent outer bracket.  Its monomial bracket gives the orbit
    # recurrence below.
    a = zero_grade
    e_zero = {(7, 8): sp.Integer(1)}
    orbit = e_zero
    orbit_rows = []
    for depth in range(8):
        expected_exponent = (7 + 6 * depth, 8 + 4 * depth)
        expected_coefficient = _adjoint_multiplier(depth)
        assert orbit == {
            expected_exponent: expected_coefficient
        }
        orbit_rows.append({
            "depth": depth,
            "exponent": list(expected_exponent),
            "coefficient": str(expected_coefficient),
        })
        orbit = _bracket(a, orbit, 2)

    # In [Omega_poly, Omega_poly'], the even terminal seed is twice
    # [L_2,L_4].  Relative to E_1=[A,E_0], its normalized coefficient is
    # -1/1536.  Forward right-dexp contributes (-1)^k/(k+1)! at depth k.
    e_one_coefficient = _adjoint_multiplier(1)
    normalized_even_seed = sp.factor(
        2
        * next(iter(even_core.values()))
        / e_one_coefficient
    )
    assert normalized_even_seed == -sp.Rational(1, 1536)

    x = sp.symbols("x")
    f = (1 - sp.exp(-x)) / x
    forcing = sp.Rational(1, 1536) * (1 - f)
    bernoulli = x / (sp.exp(x) - 1)
    solution = (
        sp.Rational(7, 12288)
        + sp.Rational(1, 2048)
        / x
        * (bernoulli - 1 + x / 2)
    )

    # Exact right-dexp linearization on the terminal module.  If
    # T=s^4*D(x)E_0 and x=s^2*ad_A, then
    #
    #   s V_T = 2 s^4 [D + f(D+xD')].
    #
    # The actual even terminal velocity is 7*E_0/3072 at cost four and
    # zero afterward.
    linear_target_velocity = 2 * (
        solution + f * (solution + x * sp.diff(solution, x))
    )
    formal_residual = sp.factor(
        sp.together(
            linear_target_velocity
            + forcing
            - sp.Rational(7, 3072)
        )
    )
    assert formal_residual == 0

    # The coefficient of d_k in the x^k equation is 2(k+2), so the formal
    # solution is unique over characteristic zero.
    uniqueness_diagonal = "2*(k+2)"

    # Independent exact replay of the closed quotient.  This validates the
    # chart conversion and conventions, while the all-order conclusion
    # comes from the bracket and formal-function identities above.
    replay = _projected_magnus(
        velocity, maximum_replay_order, TARGET_GRADE
    )
    replay_rows = []
    first_replay_failure = None
    for depth in range(
        (maximum_replay_order - 4) // 2 + 1
    ):
        order = 4 + 2 * depth
        exponent = (7 + 6 * depth, 8 + 4 * depth)
        expected = sp.factor(
            _even_orbit_coefficient(depth)
            * _adjoint_multiplier(depth)
        )
        actual = sp.factor(replay[order].get(exponent, 0))
        if first_replay_failure is None and actual != expected:
            first_replay_failure = order
        replay_rows.append({
            "logarithmic_order": order,
            "orbit_depth": depth,
            "hamiltonian_exponent": list(exponent),
            "coefficient": str(actual),
            "formula_matches": actual == expected,
        })
    assert first_replay_failure is None

    assert terminal[2] == {}
    assert terminal[3] == {
        (4, 6): sp.Rational(5, 2304)
    }
    assert terminal[4] == {
        (7, 8): sp.Rational(7, 12288)
    }

    return {
        "schema": (
            "axiompack.jacobian_controlled_global_"
            "magnus_all_order.v1"
        ),
        "translated_chart": {
            "u": "1+v",
            "density": "z^2 du wedge dz",
            "target_grade": list(TARGET_GRADE),
            "instantaneous_monomial_count": sum(
                len(value)
                for value in EXPECTED_TRANSLATED_VELOCITY.values()
            ),
            "instantaneous_costs": [2, 3, 4],
        },
        "finite_nonterminal_logarithm": {
            "costs": [2, 3, 4],
            "bracket_L2_L3": {
                "grade": list(TARGET_GRADE),
                "hamiltonian": "-7*u^10*z^10/32768",
            },
            "bracket_L2_L4": {
                "grade": list(TARGET_GRADE),
                "hamiltonian": "-u^13*z^12/131072",
            },
            "bracket_L3_L4": "zero in the quotient",
            "only_post_terminal_outer_letter": (
                "A=-3*(u*z)^7/896"
            ),
        },
        "even_terminal_equation": {
            "f": "(1-exp(-x))/x",
            "forcing": str(forcing),
            "right_dexp_equation": (
                "2*(D + f*(D+x*D')) + forcing = 7/3072"
            ),
            "solution": str(solution),
            "formal_residual": str(formal_residual),
            "uniqueness_diagonal": uniqueness_diagonal,
        },
        "all_order_coefficient": {
            "basis": (
                "E_0=u^7*z^8; E_(k+1)=[A,E_k]"
            ),
            "basis_multiplier": (
                "(-3/128)^k * product_(j=0)^(k-1)(2*j-1)"
            ),
            "d_0": "7/12288",
            "d_k_for_k_at_least_1": (
                "B_(k+1)/(2048*(k+1)!)"
            ),
            "nonzero_orders": "n=6+4*m, m>=0",
            "hamiltonian": (
                "nonzero scalar * u^(3*n-5)*z^(2*n)"
            ),
            "source_derivation_degree": "5*n-8",
        },
        "maximum_independent_replay_order": maximum_replay_order,
        "first_replay_failure": first_replay_failure,
        "orbit_prefix": orbit_rows,
        "replay_rows": replay_rows,
        "claim_boundary": (
            "All-order unbounded source logarithmic degree for this "
            "explicit cone-compatible global connection. The symbolic "
            "certificate is internal to a closed Hamiltonian quotient and "
            "uses the previously proved nonvanishing of even Bernoulli "
            "coefficients. It does not give a minimax lower bound over "
            "other cone-compatible gauges."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
