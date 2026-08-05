#!/usr/bin/env python3
"""All-contact-depth normal-three obstruction on the weighted face."""

from __future__ import annotations

from hashlib import sha256
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

from gauge_moving_divisor_normal_transition import (  # noqa: E402
    _leak_preimages,
)
from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredInductionProblem,
    FilteredInductionState,
    FilteredInductionTransition,
    compile_filtered_induction,
)


def _weighted_face() -> tuple[
    tuple[sp.Symbol, sp.Symbol], sp.Expr, sp.Expr, sp.Expr
]:
    """Extract the exact face for wt(r,z,s)=(1,2,-1)."""

    (parameter, u, z), family_p, family_q = _exact_family()
    epsilon, y, x = sp.symbols("epsilon y x")
    substitution = {
        parameter: epsilon * y,
        u: (1 / epsilon) / (x / epsilon**2),
        z: x / epsilon**2,
    }
    face_p = sp.cancel(sp.limit(
        epsilon**2 * family_p.subs(substitution), epsilon, 0
    ))
    face_q = sp.cancel(sp.limit(
        epsilon**3 * family_q.subs(substitution), epsilon, 0
    ))
    # The lower-weight terms -P^2-18PQ+4Q disappear on the weight-six face.
    face_c = sp.expand(4 * face_p**3 + 27 * face_q**2)
    assert sp.factor(face_p.subs(y, 0) - (x / 2 - sp.Rational(3, 4))) == 0
    assert sp.factor(face_q.subs(y, 0) - (x / 4 - sp.Rational(1, 4))) == 0
    return (y, x), face_p, face_q, face_c


def _x_coefficient(value: sp.Expr, x: sp.Symbol, order: int) -> sp.Expr:
    return sp.factor(
        sp.diff(value, x, order).subs(x, 0) / sp.factorial(order)
    )


def _moving_normalized_formula(
    y: sp.Symbol,
    x: sp.Symbol,
    face_p: sp.Expr,
    face_q: sp.Expr,
    face_c: sp.Expr,
) -> tuple[sp.Expr, sp.Expr]:
    """Derive [y^m x^3](P^a Q^b C^m) from first jets at y=0."""

    a, b, m = sp.symbols("a b m", integer=True, nonnegative=True)
    p_zero = face_p.subs(y, 0)
    q_zero = face_q.subs(y, 0)
    f_zero = sp.expand(p_zero**a * q_zero**b)
    f_y = sp.factor(f_zero * (
        a * sp.diff(face_p, y).subs(y, 0) / p_zero
        + b * sp.diff(face_q, y).subs(y, 0) / q_zero
    ))
    f = [_x_coefficient(f_zero, x, order) for order in range(4)]
    f_derivative = [
        _x_coefficient(f_y, x, order) for order in range(4)
    ]

    contact = sp.Poly(face_c, x)
    contact_x = [
        sp.factor(contact.coeff_monomial(x**order))
        for order in range(4)
    ]
    a0 = sp.diff(contact_x[0], y).subs(y, 0)
    a1 = sp.diff(contact_x[0], y, 2).subs(y, 0) / 2
    b0 = sp.diff(contact_x[1], y).subs(y, 0)
    b1 = sp.diff(contact_x[1], y, 2).subs(y, 0) / 2
    d0 = contact_x[2].subs(y, 0)
    d1 = sp.diff(contact_x[2], y).subs(y, 0)
    e0 = contact_x[3].subs(y, 0)
    e1 = sp.diff(contact_x[3], y).subs(y, 0)
    assert (a0, a1, b0, b1, d0, d1, e0, e1) == (
        sp.Rational(27, 128),
        -sp.Rational(333, 4096),
        -sp.Rational(63, 128),
        sp.Rational(111, 512),
        -sp.Rational(9, 16),
        sp.Rational(3, 8),
        sp.Rational(1, 2),
        -sp.Rational(3, 32),
    )

    # Terms already of y-valuation m.
    moving = (
        f[3] * a0**m
        + m * f[2] * b0 * a0 ** (m - 1)
        + sp.binomial(m, 2) * f[1] * b0**2 * a0 ** (m - 2)
        + sp.binomial(m, 3) * f[0] * b0**3 * a0 ** (m - 3)
    )

    def next_coefficient(
        value: sp.Expr,
        derivative: sp.Expr,
        fixed_zero: sp.Expr,
        fixed_one: sp.Expr,
        radial_power: sp.Expr,
    ) -> sp.Expr:
        return (
            derivative * fixed_zero * a0**radial_power
            + value * fixed_one * a0**radial_power
            + value
            * fixed_zero
            * radial_power
            * a0 ** (radial_power - 1)
            * a1
        )

    # Terms of y-valuation m-1 need exactly their next y coefficient.
    moving += m * next_coefficient(
        f[1], f_derivative[1], d0, d1, m - 1
    )
    moving += m * next_coefficient(
        f[0], f_derivative[0], e0, e1, m - 1
    )
    moving += m * (m - 1) * next_coefficient(
        f[0],
        f_derivative[0],
        d0 * b0,
        d1 * b0 + d0 * b1,
        m - 2,
    )

    common = sp.factor(f[0] * a0**m)
    normalized = sp.factor(sp.expand_func(moving / common))
    expected = -(
        16 * a**3
        + 72 * a**2 * b
        + 264 * a**2 * m
        - 48 * a**2
        + 108 * a * b**2
        + 756 * a * b * m
        - 180 * a * b
        + 1146 * a * m**2
        - 754 * a * m
        + 32 * a
        + 54 * b**3
        + 540 * b**2 * m
        - 162 * b**2
        + 1593 * b * m**2
        - 1197 * b * m
        + 108 * b
        + 1463 * m**3
        - 1861 * m**2
        + 542 * m
    ) / 324
    assert sp.factor(normalized - expected) == 0
    return common, sp.factor(expected)


def _top_section_rules() -> dict[str, object]:
    p, q = sp.symbols("P Q")
    preimages = _leak_preimages(p, q)

    def top(value: sp.Expr) -> sp.Expr:
        polynomial = sp.Poly(sp.expand(value), p, q, domain=sp.QQ)
        maximum = max(
            2 * exponent[0] + 3 * exponent[1]
            for exponent, coefficient in polynomial.terms()
            if coefficient
        )
        return sp.factor(sum(
            coefficient * p ** exponent[0] * q ** exponent[1]
            for exponent, coefficient in polynomial.terms()
            if coefficient and 2 * exponent[0] + 3 * exponent[1] == maximum
        ))

    leaders = {name: top(value) for name, value in preimages.items()}
    assert leaders == {
        "P3": sp.Rational(81, 8) * p**2 * q**3,
        "PQ": sp.Rational(81, 8) * q**4,
        "Q2": -sp.Rational(3, 2) * p**2 * q**3,
    }
    return {
        "generator_leaders": {name: str(value) for name, value in leaders.items()},
        "positive_P_exponent_rule": (
            "(a,b)->(a-1,b+3), multiplier 81/8"
        ),
        "zero_P_exponent_rule": (
            "(0,b)->(2,b+1), multiplier -3/2"
        ),
        "state_dynamics": (
            "strict descent a->a-1 until zero, followed by the cycle 0->2->1->0"
        ),
    }


def _factored_residual() -> dict[str, object]:
    a, b, m, alpha = sp.symbols(
        "a b m alpha", integer=True, nonnegative=True
    )
    _variables, face_p, face_q, face_c = _weighted_face()
    y, x = _variables
    common, moving = _moving_normalized_formula(
        y, x, face_p, face_q, face_c
    )
    final_b = sp.factor((2 * a + 3 * b + 7 * m - 2 * alpha) / 3)
    correction = -(
        sp.binomial(alpha, 3) * sp.Rational(8, 27)
        + sp.binomial(alpha, 2) * sp.Rational(4, 9) * final_b
        + alpha * sp.Rational(2, 3) * sp.binomial(final_b, 2)
        + sp.binomial(final_b, 3)
    )
    correction = sp.factor(sp.expand_func(correction))
    difference = sp.factor(sp.expand_func(moving - correction))
    expected = -(
        6 * a + 9 * b + 21 * m - 10
    ) * (
        16 * a * m
        + 4 * a
        + 18 * b * m
        + 37 * m**2
        - 29 * m
        - 4 * alpha
    ) / 324
    assert sp.factor(difference - expected) == 0
    return {
        "common_nonzero_factor": str(common),
        "final_P_exponent": (
            "alpha=a-m when m<=a; otherwise alpha is the representative "
            "of a-m modulo 3 in {0,1,2}"
        ),
        "final_Q_exponent": str(final_b),
        "normalized_residual": str(sp.factor(expected)),
        "first_factor_positive": (
            "for lift-ideal monomials, a>=1 or (a=0 and b>=2); "
            "therefore 6*a+9*b+21*m-10 >=17 when m>=1"
        ),
        "second_factor_positive": (
            "0<=alpha<=2 and 37*m^2-29*m>=8*m. If a>=1, "
            "16*a*m+8*m-8>0; if a=0, lift-ideal admissibility "
            "gives b>=2 and 18*b*m+8*m-8>0"
        ),
        "nonzero_for_canonical_symbols": True,
    }


def _direct_face_replay() -> list[dict[str, object]]:
    (y, x), face_p, face_q, face_c = _weighted_face()
    rows = []
    # Depth four and weights nine/ten are the preregistered held-out cells.
    cells = [
        *((depth, weight) for depth in range(1, 4) for weight in range(5, 9)),
        (4, 9),
        (4, 10),
    ]
    for depth, weight in cells:
        if weight % 2:
            a, b = (weight - 3) // 2, 1
        else:
            a, b = weight // 2, 0
        multiplier = sp.Integer(1)
        final_a = a
        for _step in range(depth):
            if final_a > 0:
                multiplier *= sp.Rational(81, 8)
                final_a -= 1
            else:
                multiplier *= -sp.Rational(3, 2)
                final_a = 2
        final_b = (
            2 * a + 3 * b + 7 * depth - 2 * final_a
        ) // 3
        # Weight conservation already determines the final Q exponent.
        p_zero = face_p.subs(y, 0)
        q_zero = face_q.subs(y, 0)
        moving = sp.Poly(
            sp.expand(face_p**a * face_q**b * face_c**depth),
            y,
            x,
            domain=sp.QQ,
        ).coeff_monomial(y**depth * x**3)
        correction = sp.Poly(
            sp.expand(multiplier * p_zero**final_a * q_zero**final_b),
            x,
            domain=sp.QQ,
        ).coeff_monomial(x**3)
        direct = sp.factor(moving - correction)
        predicted = sp.factor(
            (-sp.Rational(3, 4)) ** a
            * (-sp.Rational(1, 4)) ** b
            * sp.Rational(27, 128) ** depth
            * (-(6 * a + 9 * b + 21 * depth - 10))
            * (
                16 * a * depth
                + 4 * a
                + 18 * b * depth
                + 37 * depth**2
                - 29 * depth
                - 4 * final_a
            )
            / 324
        )
        assert sp.factor(direct - predicted) == 0
        assert direct != 0
        rows.append({
            "contact_depth": depth,
            "weight": weight,
            "final_P_exponent": final_a,
            "held_out": depth == 4,
            "normal_three_radial_degree": weight + 7 * depth - 6,
            "top_coefficient": str(direct),
            "matches_factored_formula": True,
        })
    return rows


def _induction_certificate(formula: str) -> dict[str, object]:
    states = []
    transitions = []
    state_classes = (
        "transient",
        "periodic_0",
        "periodic_1",
        "periodic_2",
    )
    for parity in ("even", "odd"):
        for state_class in state_classes:
            name = f"{parity}_{state_class}"
            transition_name = f"{name}_normal_three_survives"
            receipt = sha256(
                f"{formula}|{parity}|{state_class}|m>=1".encode()
            ).hexdigest()
            states.append(FilteredInductionState(
                name=name,
                rank=(0,),
                local_certificate_sha256=receipt,
                complete_outcomes=(transition_name,),
            ))
            transitions.append(FilteredInductionTransition(
                name=transition_name,
                source=name,
                outcome="terminal_survives",
            ))
    certificate = compile_filtered_induction(FilteredInductionProblem(
        name="jacobian_moving_divisor_all_depth_normal_three",
        states=tuple(states),
        transitions=tuple(transitions),
        initial_states=tuple(state.name for state in states),
    ))
    assert certificate.all_states_reachable
    assert certificate.maximum_uncharged_descent_length == 0
    assert not certificate.adapter_completeness_inferred
    return certificate.to_dict()


def run() -> dict[str, object]:
    section = _top_section_rules()
    factorization = _factored_residual()
    replay = _direct_face_replay()
    induction = _induction_certificate(factorization["normalized_residual"])
    return {
        "schema": "axiompack.jacobian_moving_divisor_odd_remainder_all_depth.v1",
        "weighted_face": {
            "grading": "wt(r,z,s)=(1,2,-1)",
            "P_weight": 2,
            "Q_weight": 3,
            "C_weight": 6,
            "parameter_depth_m_top_weight": "w+7*m",
        },
        "top_radial_section": section,
        "normal_three_factorization": factorization,
        "exact_face_replay": replay,
        "filtered_induction_certificate": induction,
        "all_depth_conclusion": {
            "contact_depth": "every m>=1",
            "canonical_weight": "every w>=5",
            "first_odd_normal_order": 3,
            "top_radial_degree": "w+7*m-6",
            "top_coefficient_nonzero": True,
            "lower_weight_collision": False,
        },
        "claim_boundary": (
            "This proves the local arbitrary-contact-depth moving-divisor "
            "odd transition on the exact weighted associated face. The "
            "complete coefficient complex still needs the group-level "
            "factorization of an arbitrary moving contact-zero backbone and "
            "a proof that conjugation preserves the charged rate filtration."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
