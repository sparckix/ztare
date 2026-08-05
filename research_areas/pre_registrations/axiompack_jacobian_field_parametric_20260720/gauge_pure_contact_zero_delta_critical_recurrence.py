#!/usr/bin/env python3
"""Critical one-variable recurrence for the pure contact-zero Delta class.

This adapter takes the slope-two initial form before doing any finite-window
linear algebra.  With ``x=s*r`` and ``eta=z/r**2``, the normalized family
coordinates have finite critical polynomials ``Pcrit(x,eta)`` and
``Qcrit(x,eta)``.  The pure contact-zero quotient is represented by its
unique parity section: ``P**(w/2)`` in even cusp weight and
``P**((w-3)/2)*Q`` in odd cusp weight.  The resulting radial normalization
is a scalar triangular recurrence in ``x``.

After the radial and first-normal blocks vanish, normal orders two and three
form the semidirect Lie algebra

    [r^a z^2, r^b z^2] = 2(b-a) r^(a+b-1) z^2,
    [r^a z^2, r^b z^3] = (2b-3a) r^(a+b-1) z^3.

Normal order at least four is an ideal and is quotiented.  Typed right-Magnus
integration in this exact quotient produces the scalar compatibility leaders

    delta_n = (3*n+8) A_n + 9 B_n,

where ``A_n`` and ``B_n`` are the normal-two and normal-three logarithmic
leaders at order ``n+1``.  The replay discovers no all-index nonvanishing
theorem; it provides the finite-state recurrence that such a theorem must
analyze and rejects mixing it with the much larger spatial calculation.
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys
from typing import TypeAlias

import sympy as sp
from sympy.concrete.guess import guess_generating_function_rational


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_moving_pullback_normal_semigroup import (  # noqa: E402
    _exact_family,
)
from gauge_q2c_contact_zero_product_grade import (  # noqa: E402
    _canonical_contact_zero_symbol,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


CriticalPolynomial: TypeAlias = dict[tuple[int, int], Fraction]
CriticalVector: TypeAlias = dict[tuple[int, int], Fraction]


def _fraction(value: sp.Expr) -> Fraction:
    rational = sp.Rational(value)
    return Fraction(int(rational.p), int(rational.q))


def _critical_polynomial(
    expression: sp.Expr,
    seed_weight: int,
    *,
    parameter: sp.Symbol,
    u: sp.Symbol,
    z: sp.Symbol,
) -> CriticalPolynomial:
    """Extract s^n r^(seed+n-2j) z^j as x^n eta^j."""

    radial = sp.symbols("r")
    radial_normal = sp.cancel(expression.subs(u, radial / z))
    numerator, denominator = radial_normal.as_numer_denom()
    if {radial, z} & denominator.free_symbols:
        raise AssertionError("critical extraction needs a spatial scalar denominator")
    result: CriticalPolynomial = {}
    for (radial_degree, normal_order), raw in sp.Poly(
        sp.expand(numerator), radial, z
    ).terms():
        parameter_order = radial_degree - seed_weight + 2 * normal_order
        if parameter_order < 0:
            continue
        coefficient = sp.cancel(raw / denominator)
        critical_coefficient = sp.factor(
            sp.series(
                coefficient,
                parameter,
                0,
                parameter_order + 1,
            )
            .removeO()
            .expand()
            .coeff(parameter, parameter_order)
        )
        if critical_coefficient:
            key = (parameter_order, normal_order)
            result[key] = result.get(key, Fraction(0)) + _fraction(
                critical_coefficient
            )
    return {key: value for key, value in result.items() if value}


def _polynomial_dictionary(
    expression: sp.Expr,
    x: sp.Symbol,
    eta: sp.Symbol,
) -> CriticalPolynomial:
    """Convert an exact polynomial in the critical variables to QQ data."""

    return {
        (x_order, normal): _fraction(coefficient)
        for (x_order, normal), coefficient in sp.Poly(
            sp.expand(expression), x, eta
        ).terms()
        if coefficient
    }


def _critical_source_from_family(
    p_critical: CriticalPolynomial,
    q_critical: CriticalPolynomial,
) -> CriticalPolynomial:
    """Recover the normalized critical source connection intrinsically.

    Under ``s=x/r`` and ``z=eta*r**2`` the family coordinates are
    ``r**2*Pcrit`` and ``r**3*Qcrit``.  Solving their exact Hamiltonian
    velocity equations is far smaller than expanding the full spatial
    source connection and proves that the critical extractor uses the same
    geometric owner rather than a fitted coefficient table.
    """

    x, eta = sp.symbols("x eta")
    p = sum(
        sp.Rational(value.numerator, value.denominator)
        * x**x_order
        * eta**normal
        for (x_order, normal), value in p_critical.items()
    )
    q = sum(
        sp.Rational(value.numerator, value.denominator)
        * x**x_order
        * eta**normal
        for (x_order, normal), value in q_critical.items()
    )

    # If dr/ds=r^2*A and dz/ds=r^3*Z, differentiating the self-similar
    # coordinates at fixed source (r,z) gives this two-by-two system.
    p_radial = 2 * p + x * sp.diff(p, x) - 2 * eta * sp.diff(p, eta)
    q_radial = 3 * q + x * sp.diff(q, x) - 2 * eta * sp.diff(q, eta)
    p_normal = sp.diff(p, eta)
    q_normal = sp.diff(q, eta)
    determinant = sp.factor(p_radial * q_normal - p_normal * q_radial)
    assert determinant == -eta / 8
    radial_velocity = sp.cancel(
        (sp.diff(p, x) * q_normal - p_normal * sp.diff(q, x))
        / determinant
    )
    normal_velocity = sp.cancel(
        (p_radial * sp.diff(q, x) - sp.diff(p, x) * q_radial)
        / determinant
    )

    # For a critical Hamiltonian r^6*B(x,eta), Hamilton's equations are
    # A=B_eta/eta and
    # Z=-(6B+x*B_x-2eta*B_eta)/eta.  The second equation fixes the radial
    # integration constant; polynomiality excludes the x^-6 solution.
    source_without_radial = sp.integrate(
        sp.cancel(eta * radial_velocity), eta
    )
    second_residual = sp.cancel(
        normal_velocity
        + (
            6 * source_without_radial
            + x * sp.diff(source_without_radial, x)
            - 2 * eta * sp.diff(source_without_radial, eta)
        )
        / eta
    )
    radial_equation = sp.factor(-eta * second_residual)
    radial_correction = sp.cancel(
        sp.integrate(x**5 * radial_equation, x) / x**6
    )
    assert not eta in radial_correction.free_symbols
    source = sp.cancel(source_without_radial + radial_correction)
    assert sp.cancel(sp.diff(source, eta) / eta - radial_velocity) == 0
    assert sp.cancel(
        -(
            6 * source
            + x * sp.diff(source, x)
            - 2 * eta * sp.diff(source, eta)
        )
        / eta
        - normal_velocity
    ) == 0

    normalized = sp.expand(source - sp.Rational(2, 9) * p**3 - 2 * q**2)
    assert sp.factor(normalized.subs(x, 0)) == 0
    return _polynomial_dictionary(normalized, x, eta)


def _poly_add(
    left: CriticalPolynomial,
    right: CriticalPolynomial,
) -> CriticalPolynomial:
    result = dict(left)
    for key, value in right.items():
        result[key] = result.get(key, Fraction(0)) + value
    return {key: value for key, value in result.items() if value}


def _poly_scale(
    value: CriticalPolynomial,
    scalar: Fraction,
) -> CriticalPolynomial:
    return {
        key: scalar * coefficient
        for key, coefficient in value.items()
        if scalar * coefficient
    }


def _poly_multiply(
    left: CriticalPolynomial,
    right: CriticalPolynomial,
    *,
    maximum_x_order: int,
    maximum_normal: int,
) -> CriticalPolynomial:
    result: CriticalPolynomial = {}
    for (left_x, left_normal), left_value in left.items():
        for (right_x, right_normal), right_value in right.items():
            key = (left_x + right_x, left_normal + right_normal)
            if key[0] > maximum_x_order or key[1] > maximum_normal:
                continue
            result[key] = (
                result.get(key, Fraction(0)) + left_value * right_value
            )
    return {key: value for key, value in result.items() if value}


def _poly_power(
    value: CriticalPolynomial,
    exponent: int,
    *,
    maximum_x_order: int,
    maximum_normal: int,
) -> CriticalPolynomial:
    result: CriticalPolynomial = {(0, 0): Fraction(1)}
    for _index in range(exponent):
        result = _poly_multiply(
            result,
            value,
            maximum_x_order=maximum_x_order,
            maximum_normal=maximum_normal,
        )
    return result


def _critical_ops() -> FormalLieOps[CriticalVector]:
    def add(left: CriticalVector, right: CriticalVector) -> CriticalVector:
        result = dict(left)
        for key, value in right.items():
            result[key] = result.get(key, Fraction(0)) + value
        return {key: value for key, value in result.items() if value}

    def scale(value: CriticalVector, scalar: Fraction) -> CriticalVector:
        return {
            key: scalar * coefficient
            for key, coefficient in value.items()
            if scalar * coefficient
        }

    def bracket(left: CriticalVector, right: CriticalVector) -> CriticalVector:
        result: CriticalVector = {}
        for (left_normal, left_radial), left_value in left.items():
            for (right_normal, right_radial), right_value in right.items():
                output_normal = left_normal + right_normal - 2
                if output_normal not in {2, 3}:
                    continue
                multiplier = (
                    left_normal * right_radial
                    - left_radial * right_normal
                )
                if not multiplier:
                    continue
                key = (
                    output_normal,
                    left_radial + right_radial - 1,
                )
                result[key] = (
                    result.get(key, Fraction(0))
                    + multiplier * left_value * right_value
                )
        return {key: value for key, value in result.items() if value}

    return FormalLieOps(zero=dict, add=add, scale=scale, bracket=bracket)


def _split_semidirect_certificate() -> dict[str, object]:
    """Check the intrinsic function algebra behind the Delta quotient."""

    x = sp.symbols("x")
    first = sp.Function("A")(x)
    second = sp.Function("C")(x)
    module = sp.Function("B")(x)

    def witt(left: sp.Expr, right: sp.Expr) -> sp.Expr:
        return sp.expand(
            2 * x * (left * sp.diff(right, x) - sp.diff(left, x) * right)
        )

    def action(actor: sp.Expr, value: sp.Expr) -> sp.Expr:
        return sp.expand(
            2 * x * actor * sp.diff(value, x)
            - 3 * x * sp.diff(actor, x) * value
            - 5 * actor * value
        )

    representation_residual = sp.expand(
        action(first, action(second, module))
        - action(second, action(first, module))
        - action(witt(first, second), module)
    )
    assert representation_residual == 0
    basepoint = sp.Rational(1, 9)
    assert sp.expand(
        action(first, basepoint)
        + (3 * x * sp.diff(first, x) + 5 * first) / 9
    ) == 0
    return {
        "logarithm_normal_form": (
            "Omega_crit=r*z^2*A(x)+z^3/r*B(x), x=s*r"
        ),
        "witt_bracket": "[A,C]=2*x*(A*C'-A'*C)",
        "module_action": "rho(A)B=2*x*A*B'-3*x*A'*B-5*A*B",
        "representation_identity_verified": True,
        "coboundary_basepoint": "h=1/9",
        "split_module_coordinate": (
            "J=B-rho(A)(1/9)=B+(3*x*A'+5*A)/9"
        ),
        "delta_generating_series": "Delta(Omega_crit)=9*J",
        "kernel_is_split_witt_subalgebra": True,
        "prefix_problem": (
            "A finite critical kernel logarithm is a finite Witt element; "
            "unconditional closure requires proving that its semidirect "
            "action cannot polynomialize the nonkernel module tail."
        ),
    }


def _critical_recurrence(
    maximum_row: int,
    *,
    guess_rational_generating_function: bool = True,
) -> dict[str, object]:
    (parameter, u, z), family_p, family_q = _exact_family()
    p_critical = _critical_polynomial(
        family_p,
        2,
        parameter=parameter,
        u=u,
        z=z,
    )
    q_critical = _critical_polynomial(
        family_q,
        3,
        parameter=parameter,
        u=u,
        z=z,
    )
    base_critical = _critical_source_from_family(p_critical, q_critical)
    assert p_critical == {
        (0, 0): Fraction(-3, 4),
        (1, 0): Fraction(1, 8),
        (0, 1): Fraction(1, 2),
        (1, 1): Fraction(-1, 8),
        (2, 1): Fraction(1, 32),
        (2, 2): Fraction(-1, 192),
        (3, 2): Fraction(1, 384),
        (4, 3): Fraction(1, 13824),
    }
    assert q_critical[(0, 0)] == Fraction(-1, 4)
    assert q_critical[(1, 0)] == Fraction(3, 64)
    assert len(base_critical) == 37
    assert max(x_order for x_order, _normal in base_critical) == 12

    radial_residual = [Fraction(0) for _ in range(maximum_row + 1)]
    for (x_order, normal), coefficient in base_critical.items():
        if normal == 0 and x_order <= maximum_row:
            radial_residual[x_order] += coefficient

    controls: dict[int, Fraction] = {}
    control_symbols: dict[int, CriticalPolynomial] = {}
    target_p, target_q = sp.symbols("P Q")
    for row in range(1, maximum_row + 1):
        weight = row + 6
        canonical = _canonical_contact_zero_symbol(
            weight, target_p, target_q
        )
        polynomial = sp.Poly(canonical, target_p, target_q)
        terms = polynomial.terms()
        assert len(terms) == 1 and terms[0][1] == 1
        p_exponent, q_exponent = terms[0][0]
        symbol = _poly_multiply(
            _poly_power(
                p_critical,
                p_exponent,
                maximum_x_order=maximum_row,
                maximum_normal=3,
            ),
            _poly_power(
                q_critical,
                q_exponent,
                maximum_x_order=maximum_row,
                maximum_normal=3,
            ),
            maximum_x_order=maximum_row,
            maximum_normal=3,
        )
        control_symbols[row] = symbol
        diagonal = symbol[(0, 0)]
        controls[row] = -radial_residual[row] / (8 * diagonal)
        for (delay, normal), coefficient in symbol.items():
            if normal or row + delay > maximum_row:
                continue
            radial_residual[row + delay] += 8 * controls[row] * coefficient
        assert radial_residual[row] == 0

    velocity: list[CriticalVector] = []
    velocity_layers: list[dict[int, Fraction]] = []
    for row in range(maximum_row + 1):
        layers: dict[int, Fraction] = {}
        for (base_row, normal), coefficient in base_critical.items():
            if base_row == row:
                layers[normal] = layers.get(normal, Fraction(0)) + coefficient
        for control_row in range(1, row + 1):
            for (delay, normal), coefficient in control_symbols[
                control_row
            ].items():
                if control_row + delay == row:
                    layers[normal] = (
                        layers.get(normal, Fraction(0))
                        + 8 * controls[control_row] * coefficient
                    )
        layers = {normal: value for normal, value in layers.items() if value}
        assert layers.get(0, Fraction(0)) == 0
        assert layers.get(1, Fraction(0)) == 0
        velocity_layers.append(layers)
        critical_row: CriticalVector = {}
        for normal in (2, 3):
            radial_degree = row + 6 - 2 * normal
            coefficient = layers.get(normal, Fraction(0))
            if coefficient and radial_degree >= 0:
                critical_row[(normal, radial_degree)] = coefficient
        velocity.append(critical_row)

    ops = _critical_ops()
    logarithm = magnus_from_velocity(
        velocity,
        maximum_row + 1,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        maximum_row + 1,
        ops,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert replay[: maximum_row + 1] == velocity

    rows = []
    deltas: list[sp.Rational] = []
    for row in range(1, maximum_row + 1):
        logarithmic_order = row + 1
        normal_two = logarithm[logarithmic_order].get(
            (2, row + 2), Fraction(0)
        )
        normal_three = logarithm[logarithmic_order].get(
            (3, row), Fraction(0)
        )
        delta = (3 * row + 8) * normal_two + 9 * normal_three
        deltas.append(sp.Rational(delta.numerator, delta.denominator))
        rows.append({
            "target_row": row,
            "logarithmic_order": logarithmic_order,
            "radial_control": str(controls[row]),
            "velocity_normal_two": str(
                velocity_layers[row].get(2, Fraction(0))
            ),
            "velocity_normal_three": str(
                velocity_layers[row].get(3, Fraction(0))
            ),
            "logarithm_normal_two": str(normal_two),
            "logarithm_normal_three": str(normal_three),
            "delta": str(delta),
            "delta_nonzero": bool(delta),
        })

    positive_contact_staircase_values = (
        sp.Rational(-1, 16),
        sp.Rational(-1, 64),
        sp.Rational(-3, 1024),
        sp.Rational(-137, 229376),
        sp.Rational(-5359, 44040192),
        sp.Rational(-920333, 43159388160),
    )
    assert tuple(deltas[:6]) != positive_contact_staircase_values
    rational_guess = (
        guess_generating_function_rational(deltas, sp.Symbol("x"))
        if guess_rational_generating_function
        else None
    )
    return {
        "critical_family": {
            "Pcrit": {
                f"x^{x_order}*eta^{normal}": str(coefficient)
                for (x_order, normal), coefficient in sorted(
                    p_critical.items()
                )
            },
            "Qcrit": {
                f"x^{x_order}*eta^{normal}": str(coefficient)
                for (x_order, normal), coefficient in sorted(
                    q_critical.items()
                )
            },
            "base_support_size": len(base_critical),
            "base_maximum_x_order": max(
                x_order for x_order, _normal in base_critical
            ),
        },
        "scalar_radial_recurrence": {
            "diagonal_nonzero_every_row": all(controls.values()),
            "canonical_weight": "row+6 in the pure parity section",
            "radial_rows_cancelled": True,
            "positive_contact_staircase_values_rejected": True,
        },
        "normal_two_three_lie_quotient": {
            "normal_at_least_four_is_an_ideal": True,
            "bracket_22": "2*(b-a)*E_(a+b-1,2)",
            "bracket_23": "(2*b-3*a)*E_(a+b-1,3)",
            "typed_forward_dexp_roundtrip": True,
        },
        "split_semidirect_quotient": _split_semidirect_certificate(),
        "rows": rows,
        "all_computed_delta_nonzero": all(delta != 0 for delta in deltas),
        "rational_generating_function_guess": (
            None if rational_guess is None else str(rational_guess)
        ),
        "rational_generating_function_guess_attempted": (
            guess_rational_generating_function
        ),
    }


def run(maximum_row: int = 14) -> dict[str, object]:
    if maximum_row < 6:
        raise ValueError("the critical recurrence needs the six held rows")
    recurrence = _critical_recurrence(maximum_row)
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "delta_critical_recurrence.v2"
        ),
        **recurrence,
        "claim_boundary": (
            "The exact slope-two critical quotient and its pure-parity "
            "radial normalization are compiled through the declared "
            "recurrence depth, with a projected typed Magnus round trip. "
            "The older full-cone staircase is explicitly rejected after "
            "the rows where it ceases to represent this quotient. "
            "Nonvanishing of every computed delta is diagnostic. An "
            "all-index theorem still requires a closed recurrence, a "
            "generating-function singularity, or a sign/valuation invariant "
            "stable under every finite rational prefix."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
