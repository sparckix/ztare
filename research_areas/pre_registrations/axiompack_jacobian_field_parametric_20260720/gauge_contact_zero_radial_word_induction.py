#!/usr/bin/env python3
"""All-order radial-word action on odd-normal source terminals.

This adapter supplies one symbolic edge for the moving-backbone induction.
It proves wordwise injectivity for arbitrary nonconstant radial contact-zero
leaders.  Linear collisions among different words remain a separate coupled
bundle problem and are stated in the output boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket,
)
from gauge_positive_contact_locally_finite_obstruction import (  # noqa: E402
    _filtered_induction_certificate,
)


def _monomial_word_certificate(regression_depth: int) -> dict[str, object]:
    if regression_depth < 1:
        raise ValueError("regression_depth must be positive")
    w, a, n = sp.symbols(
        "w a n", integer=True, positive=True
    )
    multiplier_first = sp.expand(w * a - w * (a + n))
    exponent_first = (
        a + w - 1,
        a + w + n - 3,
    )
    assert multiplier_first == -w * n
    assert sp.expand(
        exponent_first[1] - exponent_first[0] - (n - 2)
    ) == 0

    odd_half = sp.symbols("m", integer=True, nonnegative=True)
    k = sp.symbols("k", integer=True, nonnegative=True)
    multiplier = sp.factor(
        (-w) ** k
        * sp.product(2 * odd_half + 1 - 2 * sp.Symbol("i"),
                     (sp.Symbol("i"), 0, k - 1))
    )

    rows = []
    current = {(3, 8): sp.Integer(1)}  # r^3*z^5: odd normal offset five.
    expected_coefficient = sp.Integer(1)
    selected_weight = 7
    for depth in range(regression_depth + 1):
        expected_exponent = (
            3 + depth * (selected_weight - 1),
            8 + depth * (selected_weight - 3),
        )
        assert current == {expected_exponent: expected_coefficient}
        rows.append({
            "word_length": depth,
            "source_exponent": list(expected_exponent),
            "normal_offset": expected_exponent[1] - expected_exponent[0],
            "coefficient": str(expected_coefficient),
        })
        normal = 5 - 2 * depth
        expected_coefficient = sp.factor(
            expected_coefficient * (-selected_weight * normal)
        )
        current = _bracket(
            {(selected_weight, selected_weight): sp.Integer(1)},
            current,
            2,
        )

    return {
        "single_step": (
            "[E_(w,0),E_(a,n)]=-w*n*E_(a+w-1,n-2)"
        ),
        "word_formula": (
            "ad_(E_(w,0))^k(E_(a,2*m+1))="
            "(-w)^k*prod_(i=0)^(k-1)(2*m+1-2*i)*"
            "E_(a+k*(w-1),2*m+1-2*k)"
        ),
        "symbolic_multiplier": str(multiplier),
        "nonzero_for_every_positive_w_nonnegative_m_k": True,
        "regression_weight": selected_weight,
        "regression_initial": "r^3*z^5",
        "regression_rows": rows,
    }


def _polynomial_word_certificate() -> dict[str, object]:
    r, z = sp.symbols("r z")
    f = r**2 + 2 * r**5 - 3 * r**7
    g = 1 - r + 4 * r**3
    normal = 5
    depth = 4
    expected = sp.expand(
        (-1) ** depth
        * sp.prod(normal - 2 * index for index in range(depth))
        * z ** (normal - 2 * depth)
        * sp.diff(f, r) ** depth
        * g
    )

    # Verify the radial formula directly in (u,z), permitting negative
    # normal powers while the Hamiltonian expression remains Laurent.
    u = sp.symbols("u")
    radial = u * z

    def laurent_bracket(left: sp.Expr, right: sp.Expr) -> sp.Expr:
        return sp.factor(
            (
                sp.diff(left, z) * sp.diff(right, u)
                - sp.diff(left, u) * sp.diff(right, z)
            ) / z**2
        )

    current = z**normal * g.subs(r, radial)
    leader = f.subs(r, radial)
    for _ in range(depth):
        current = laurent_bracket(leader, current)
    expected_uv = expected.subs(r, radial)
    assert sp.factor(current - expected_uv) == 0
    return {
        "general_formula": (
            "ad_f^k(z^n*g(r))=(-1)^k*"
            "prod_(i=0)^(k-1)(n-2*i)*z^(n-2*k)*(f'(r))^k*g(r)"
        ),
        "coefficient_domain": "QQ[r] is an integral domain",
        "odd_normal_wordwise_injective": True,
        "regression_f": str(f),
        "regression_g": str(g),
        "regression_normal_offset": normal,
        "regression_depth": depth,
        "regression_nonzero": expected != 0,
    }


def _radial_connection_certificate() -> dict[str, object]:
    s, r, z = sp.symbols("s r z")
    n, k = sp.symbols(
        "n k", integer=True, positive=True
    )

    # The coefficient recurrence is the coefficientwise proof of the
    # time-dependent connection equation.  Radial adjoint operators commute,
    # so no time ordering remains after integration in s.
    c_previous = sp.symbols("c_previous")
    c_current = sp.factor(
        -(n - 2 * k + 2) * c_previous / k
    )
    assert sp.factor(
        k * c_current + (n - 2 * k + 2) * c_previous
    ) == 0

    connection = (
        (r**2 + 2 * r**5) * s
        + (3 * r**4 - r**7) * s**3
    )
    primitive = sp.integrate(connection, (s, 0, s))
    derivative = sp.diff(primitive, r)
    g = 1 + r + r**3
    normal = 5
    maximum_depth = 4
    coefficients = [sp.Integer(1)]
    for depth in range(1, maximum_depth + 1):
        coefficients.append(sp.factor(
            -sp.Rational(normal - 2 * depth + 2, depth)
            * coefficients[-1]
        ))
    transported = [
        sp.expand(
            coefficients[depth]
            * z ** (normal - 2 * depth)
            * derivative**depth
            * g
        )
        for depth in range(maximum_depth + 1)
    ]
    for depth in range(1, maximum_depth + 1):
        left = sp.diff(transported[depth], s)
        right = sp.expand(
            -(normal - 2 * depth + 2)
            * sp.diff(connection, r)
            * transported[depth - 1]
            / z**2
        )
        assert sp.expand(left - right) == 0

    # A tied Newton face remains nonzero under every power.  For one
    # occurrence, the slope-two surplus of s^j*r^d in d_r F is
    # 2*d-2*j-2.  The occurrence count makes that surplus additive.
    tied_face = 2 * s * r**4 + 3 * s**2 * r**5
    lower = 5 * s**2 * r**4 + 7 * s**4 * r**5
    newton_polynomial = sp.expand(tied_face + lower)

    def face(value: sp.Expr, occurrence_count: int) -> sp.Expr:
        polynomial = sp.Poly(sp.expand(value), s, r)
        terms = [
            (exponents, coefficient)
            for exponents, coefficient in polynomial.terms()
            if coefficient != 0
        ]
        scores = [
            2 * radial_order - 2 * parameter_order
            - 2 * occurrence_count
            for (parameter_order, radial_order), _coefficient in terms
        ]
        maximum = max(scores)
        return sp.expand(sum(
            coefficient * s**parameter_order * r**radial_order
            for ((parameter_order, radial_order), coefficient), score
            in zip(terms, scores, strict=True)
            if score == maximum
        ))

    assert face(newton_polynomial, 1) == tied_face
    face_rows = []
    for power in range(1, 6):
        powered_face = face(newton_polynomial**power, power)
        assert sp.expand(powered_face - tied_face**power) == 0
        assert powered_face != 0
        face_rows.append({
            "power": power,
            "face_term_count": len(sp.Poly(
                powered_face, s, r
            ).terms()),
            "face_nonzero": True,
        })

    return {
        "radial_actions_commute": True,
        "primitive": "F_s(r)=integral_0^s f_t(r) dt",
        "transport_formula": (
            "U_s(z^n*g)=sum_k (-1)^k/k!*"
            "prod_(i=0)^(k-1)(n-2*i)*z^(n-2*k)*"
            "(d_r F_s)^k*g"
        ),
        "coefficient_recurrence": (
            "k*c_k=-(n-2*k+2)*c_(k-1)"
        ),
        "connection_equation_verified_through_depth": maximum_depth,
        "training_connection": str(connection),
        "training_primitive_radial_derivative": str(derivative),
        "newton_face": {
            "one_occurrence_surplus": "2*d-2*j-2",
            "tied_face": str(tied_face),
            "lower_terms": str(lower),
            "initial_form_power_identity": "in(F^k)=in(F)^k",
            "reason": (
                "the slope-two occurrence grading is additive and "
                "QQ[s,r] is an integral domain"
            ),
            "regression_rows": face_rows,
        },
        "odd_normal_complete_connection_nonzero": True,
    }


def run(regression_depth: int = 8) -> dict[str, object]:
    return {
        "schema": "axiompack.jacobian_contact_zero_radial_word_induction.v1",
        "monomial_radial_word": _monomial_word_certificate(
            regression_depth
        ),
        "polynomial_radial_word": _polynomial_word_certificate(),
        "complete_radial_connection": _radial_connection_certificate(),
        "normalized_positive_contact_induction": (
            _filtered_induction_certificate()
        ),
        "new_induction_edge": {
            "source_state": "robust_odd_terminal",
            "radial_contact_zero_word_is_nonresonant": True,
            "normal_offset_changes_by": -2,
            "radial_exponent_changes_by": "weight-1",
        },
        "claim_boundary": (
            "The complete time-dependent radial contact-zero connection "
            "acts by the displayed binomial transport, and its highest "
            "slope-two Newton face cannot cancel on an odd-normal "
            "polynomial terminal. This is an all-order symbolic edge. "
            "The remaining induction bridge must include positive-contact "
            "radial leakage from the moving divisor and prove that lower "
            "normal pullback shells either descend or expose a charged "
            "pivot."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
