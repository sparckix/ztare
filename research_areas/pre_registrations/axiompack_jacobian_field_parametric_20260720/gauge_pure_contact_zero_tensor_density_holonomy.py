#!/usr/bin/env python3
"""Algebraic (A,J) connection for the pure contact-zero critical quotient.

This replay extends the existing parity algebraic connection by one normal
layer.  It computes the exact normal-two and normal-three instantaneous
series in the same quadratic function field and forms the split
tensor-density forcing

    j = b + (3*x*a' + 8*a)/9.

Here ``a,b,j`` are the row-indexed generating functions.  The intrinsic
tensor-density coordinates are shifted by one radial power,
``Ahat=x*a`` and ``Jhat=x*j``; equivalently
``Jhat=Bhat+(3*x*Ahat'+5*Ahat)/9``.  Keeping this shift explicit prevents
the row index from being confused with the intrinsic ``x`` exponent.

The first purpose is categorical: the target-kernel graph is ``J=0``, so
polar-prefix induction must use this pair rather than the plain Witt
coordinate A.  The second purpose is to expose an all-index singularity or
differential relation for the logarithmic J-series.  Finite recurrence rows
are used only as an orientation check.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from gauge_pure_contact_zero_delta_critical_recurrence import (  # noqa: E402
    _critical_polynomial,
    _critical_recurrence,
    _critical_source_from_family,
    _critical_ops,
)
from gauge_pure_contact_zero_parity_algebraic_connection import (  # noqa: E402
    QuadraticElement,
    _add,
    _algebraic_normal_two,
    _derivative,
    _divide,
    _evaluate_polynomial,
    _multiply,
    _power,
    _scale,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredQuadraticDifferentialProblem,
    compile_filtered_quadratic_differential_obstruction,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    bch_series,
    factor_magnus_by_projection,
)


def _critical_expression(
    coefficients: dict[tuple[int, int], object],
    x: sp.Symbol,
    eta: sp.Symbol,
) -> sp.Expr:
    return sp.expand(sum(
        sp.Rational(value.numerator, value.denominator)
        * x**x_order
        * eta**normal
        for (x_order, normal), value in coefficients.items()
    ))


def _series_multiply(
    left: list[QuadraticElement],
    right: list[QuadraticElement],
    discriminant: sp.Expr,
    maximum_order: int,
) -> list[QuadraticElement]:
    result = [
        QuadraticElement(sp.Integer(0), sp.Integer(0))
        for _ in range(maximum_order + 1)
    ]
    for left_order, left_value in enumerate(left):
        for right_order, right_value in enumerate(right):
            if left_order + right_order > maximum_order:
                continue
            result[left_order + right_order] = _add(
                result[left_order + right_order],
                _multiply(left_value, right_value, discriminant),
            )
    return result


def _compose_through_three(
    value: QuadraticElement,
    y: sp.Expr,
    y_coefficients: list[sp.Expr],
    x: sp.Symbol,
    discriminant: sp.Expr,
) -> list[QuadraticElement]:
    derivatives = [value]
    for _order in range(3):
        derivatives.append(
            _scale(
                _derivative(derivatives[-1], x, discriminant),
                1 / sp.diff(y, x),
            )
        )
    y1, y2, y3 = y_coefficients[1:4]
    return [
        derivatives[0],
        _scale(derivatives[1], y1),
        _add(
            _scale(derivatives[1], y2),
            _scale(derivatives[2], y1**2 / 2),
        ),
        _add(
            _add(
                _scale(derivatives[1], y3),
                _scale(derivatives[2], y1 * y2),
            ),
            _scale(derivatives[3], y1**3 / 6),
        ),
    ]


def _polynomial_coefficients(
    value: sp.Expr,
    eta: sp.Symbol,
    maximum_order: int = 3,
) -> list[QuadraticElement]:
    return [
        QuadraticElement(sp.expand(value).coeff(eta, order), sp.Integer(0))
        for order in range(maximum_order + 1)
    ]


def _algebraic_normal_two_three() -> tuple[
    sp.Symbol,
    sp.Expr,
    QuadraticElement,
    QuadraticElement,
]:
    x, eta = sp.symbols("x eta")
    discriminant = sp.factor(36 + 12 * x - 3 * x**2)
    radical = QuadraticElement(sp.Integer(0), sp.Integer(1))
    involution = _add(
        QuadraticElement((6 - x) / 2, sp.Integer(0)),
        _scale(radical, -sp.Rational(1, 2)),
    )

    (parameter, u, z), family_p, family_q = _exact_family()
    p_data = _critical_polynomial(
        family_p, 2, parameter=parameter, u=u, z=z
    )
    q_data = _critical_polynomial(
        family_q, 3, parameter=parameter, u=u, z=z
    )
    base_data = _critical_source_from_family(p_data, q_data)
    p_critical = _critical_expression(p_data, x, eta)
    q_critical = _critical_expression(q_data, x, eta)
    base = _critical_expression(base_data, x, eta)
    p = sp.factor(p_critical.subs(eta, 0))
    q = sp.factor(q_critical.subs(eta, 0))
    y = sp.factor(x**2 * p)
    demand = sp.factor(-base.subs(eta, 0) / 8)

    fixed = QuadraticElement(x, sp.Integer(0))
    p_fixed = QuadraticElement(p, sp.Integer(0))
    q_fixed = QuadraticElement(q, sp.Integer(0))
    demand_fixed = QuadraticElement(demand, sp.Integer(0))
    p_other = _evaluate_polynomial(p, involution, x, discriminant)
    q_other = _evaluate_polynomial(q, involution, x, discriminant)
    demand_other = _evaluate_polynomial(
        demand, involution, x, discriminant
    )
    first_value = _divide(
        demand_fixed, _power(p_fixed, 2, discriminant), discriminant
    )
    other_value = _divide(
        demand_other, _power(p_other, 2, discriminant), discriminant
    )
    parity_even = _divide(
        _add(
            _multiply(
                first_value,
                _multiply(involution, q_other, discriminant),
                discriminant,
            ),
            _scale(
                _multiply(
                    other_value,
                    _multiply(fixed, q_fixed, discriminant),
                    discriminant,
                ),
                -1,
            ),
        ),
        _add(
            _multiply(
                p_fixed,
                _multiply(involution, q_other, discriminant),
                discriminant,
            ),
            _scale(
                _multiply(
                    p_other,
                    _multiply(fixed, q_fixed, discriminant),
                    discriminant,
                ),
                -1,
            ),
        ),
        discriminant,
    )
    parity_odd = _divide(
        _add(
            _multiply(first_value, p_other, discriminant),
            _scale(_multiply(other_value, p_fixed, discriminant), -1),
        ),
        _add(
            _multiply(
                fixed,
                _multiply(q_fixed, p_other, discriminant),
                discriminant,
            ),
            _scale(
                _multiply(
                    involution,
                    _multiply(q_other, p_fixed, discriminant),
                    discriminant,
                ),
                -1,
            ),
        ),
        discriminant,
    )

    y_critical = sp.expand(x**2 * p_critical)
    y_coefficients = [
        y_critical.coeff(eta, order) for order in range(4)
    ]
    even_series = _compose_through_three(
        parity_even,
        y,
        y_coefficients,
        x,
        discriminant,
    )
    odd_series = _compose_through_three(
        parity_odd,
        y,
        y_coefficients,
        x,
        discriminant,
    )
    even_prefactor = _polynomial_coefficients(p_critical**3, eta)
    odd_prefactor = _polynomial_coefficients(
        x * p_critical**2 * q_critical,
        eta,
    )
    even_product = _series_multiply(
        even_prefactor,
        even_series,
        discriminant,
        3,
    )
    odd_product = _series_multiply(
        odd_prefactor,
        odd_series,
        discriminant,
        3,
    )
    layers = []
    for normal in range(4):
        layers.append(_add(
            QuadraticElement(base.coeff(eta, normal), sp.Integer(0)),
            _scale(_add(even_product[normal], odd_product[normal]), 8),
        ))
    assert layers[0] == QuadraticElement(0, 0)
    assert layers[1] == QuadraticElement(0, 0)

    _, _, existing_normal_two = _algebraic_normal_two()
    assert sp.cancel(
        layers[2].rational - existing_normal_two.rational
    ) == 0
    assert sp.cancel(
        layers[2].radical_coefficient
        - existing_normal_two.radical_coefficient
    ) == 0
    return x, discriminant, layers[2], layers[3]


def run(verification_rows: int = 14) -> dict[str, object]:
    if verification_rows < 8:
        raise ValueError("the tensor-density audit needs eight rows")
    x, discriminant, normal_two, normal_three = (
        _algebraic_normal_two_three()
    )
    # The intrinsic split coordinate is
    #
    #   Jhat=Bhat+(3*x*Ahat'+5*Ahat)/9,
    #   Ahat=x*a, Bhat=x*b, Jhat=x*j.
    #
    # Hence the row-indexed coefficient function uses +8, not +5.
    tensor_density = _add(
        normal_three,
        _scale(
            _add(
                _scale(_derivative(normal_two, x, discriminant), 3 * x),
                _scale(normal_two, 8),
            ),
            sp.Rational(1, 9),
        ),
    )

    recurrence = _critical_recurrence(
        verification_rows,
        guess_rational_generating_function=False,
    )
    normal_three_series = sp.series(
        normal_three.rational
        + normal_three.radical_coefficient * sp.sqrt(discriminant),
        x,
        0,
        verification_rows + 3,
    ).removeO().expand()
    tensor_series = sp.series(
        tensor_density.rational
        + tensor_density.radical_coefficient * sp.sqrt(discriminant),
        x,
        0,
        verification_rows + 3,
    ).removeO().expand()

    # Freeze the coefficient orientation against the exact recurrence.
    # Both reduced coefficient series use the target-row index as their
    # generating exponent; the different radial powers are already in the
    # definitions of the A and B basis vectors.
    for row in recurrence["rows"]:
        index = int(row["target_row"])
        assert normal_three_series.coeff(x, index) == sp.Rational(
            row["velocity_normal_three"]
        )

    t = sp.symbols("t")
    local_substitution = {x: t**2 - 2}
    local_radical = t * sp.sqrt(24 - 3 * t**2)
    tensor_local = sp.series(
        tensor_density.rational.subs(local_substitution)
        + tensor_density.radical_coefficient.subs(local_substitution)
        * local_radical,
        t,
        0,
        9,
    ).removeO().expand()
    fractional_terms = {
        exponent: sp.factor(tensor_local.coeff(t, exponent))
        for exponent in (1, 3, 5, 7)
        if tensor_local.coeff(t, exponent) != 0
    }

    # Move the complete Witt logarithm to the target-kernel factor.  The
    # residual subgroup is the abelian J-module, so its group coordinate is
    # already its logarithm.  For a right velocity it obeys
    #
    #   K' = J_vel-rho(A_vel)K.
    #
    # On the critical diagonal, with reduced coefficient functions a,j,k,
    # this becomes the displayed scalar ODE.
    a = normal_two
    j = tensor_density
    a_radical_derivative = sp.cancel(
        sp.diff(a.radical_coefficient, x)
        + a.radical_coefficient * sp.diff(discriminant, x)
        / (2 * discriminant)
    )
    rational_row = (
        sp.cancel(x * (1 + 2 * x * a.rational)),
        sp.cancel(
            -(6 * x * a.rational
              + 3 * x**2 * sp.diff(a.rational, x) - 1)
        ),
        sp.cancel(j.rational),
    )
    radical_row = (
        sp.cancel(2 * x**2 * a.radical_coefficient),
        sp.cancel(
            -(6 * x * a.radical_coefficient
              + 3 * x**2 * a_radical_derivative)
        ),
        sp.cancel(j.radical_coefficient),
    )

    logarithm = [dict() for _ in range(verification_rows + 2)]
    for row in recurrence["rows"]:
        index = int(row["target_row"])
        logarithm[index + 1] = {
            (2, index + 2): Fraction(row["logarithm_normal_two"]),
            (3, index): Fraction(row["logarithm_normal_three"]),
        }

    def project_target_graph(
        value: dict[tuple[int, int], Fraction],
    ) -> dict[tuple[int, int], Fraction]:
        result: dict[tuple[int, int], Fraction] = {}
        for (normal, radial), coefficient in value.items():
            if normal != 2:
                continue
            result[(2, radial)] = (
                result.get((2, radial), Fraction(0)) + coefficient
            )
            row = radial - 2
            result[(3, row)] = (
                result.get((3, row), Fraction(0))
                - Fraction(3 * row + 8, 9) * coefficient
            )
        return {key: value for key, value in result.items() if value}

    target_factor, source_residual = factor_magnus_by_projection(
        logarithm,
        verification_rows + 1,
        _critical_ops(),
        project_target_graph,
    )
    assert bch_series(
        target_factor,
        source_residual,
        verification_rows + 1,
        _critical_ops(),
    ) == logarithm
    residual_series = sp.expand(sum(
        sp.Rational(
            source_residual[index + 1].get(
                (3, index), Fraction(0)
            ).numerator,
            source_residual[index + 1].get(
                (3, index), Fraction(0)
            ).denominator,
        )
        * x**index
        for index in range(1, verification_rows + 1)
    ))
    a_series = sp.series(
        a.rational + a.radical_coefficient * sp.sqrt(discriminant),
        x,
        0,
        verification_rows + 1,
    ).removeO().expand()
    j_series = sp.series(
        j.rational + j.radical_coefficient * sp.sqrt(discriminant),
        x,
        0,
        verification_rows + 1,
    ).removeO().expand()
    ode_residual = sp.series(
        x * (1 + 2 * x * a_series) * sp.diff(residual_series, x)
        - j_series
        - (6 * x * a_series + 3 * x**2 * sp.diff(a_series, x) - 1)
        * residual_series,
        x,
        0,
        verification_rows + 1,
    ).removeO().expand()
    assert ode_residual == 0, sp.factor(ode_residual)

    adapter_payload = {
        "discriminant": str(discriminant),
        "normal_two": [
            str(sp.factor(a.rational)),
            str(sp.factor(a.radical_coefficient)),
        ],
        "tensor_density": [
            str(sp.factor(j.rational)),
            str(sp.factor(j.radical_coefficient)),
        ],
        "rational_row": [str(sp.factor(value)) for value in rational_row],
        "radical_row": [str(sp.factor(value)) for value in radical_row],
        "factorization_roundtrip": True,
        "ode_roundtrip_rows": verification_rows,
    }
    adapter_digest = hashlib.sha256(
        json.dumps(
            adapter_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    differential_certificate = (
        compile_filtered_quadratic_differential_obstruction(
            FilteredQuadraticDifferentialProblem(
                name=(
                    "jacobian_pure_contact_zero_"
                    "critical_abelian_source_residual"
                ),
                variable="x",
                rational_row=tuple(str(value) for value in rational_row),
                radical_row=tuple(str(value) for value in radical_row),
                adapter_certificate_sha256=adapter_digest,
            )
        )
    )
    assert differential_certificate.rational_solution_excluded
    assert differential_certificate.polynomial_solution_excluded
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "tensor_density_holonomy.v1"
        ),
        "normal_three_velocity": {
            "rational_part": str(sp.factor(normal_three.rational)),
            "radical_coefficient": str(
                sp.factor(normal_three.radical_coefficient)
            ),
            "recurrence_shift": "[x^row]B_vel",
            "recurrence_rows_verified": verification_rows,
        },
        "tensor_density_velocity": {
            "definition": "j_vel=b_vel+(3*x*a_vel'+8*a_vel)/9",
            "intrinsic_definition": (
                "Jhat_vel=Bhat_vel+"
                "(3*x*Ahat_vel'+5*Ahat_vel)/9; "
                "Ahat=x*a, Bhat=x*b, Jhat=x*j"
            ),
            "rational_part": str(sp.factor(tensor_density.rational)),
            "radical_coefficient": str(
                sp.factor(tensor_density.radical_coefficient)
            ),
            "series_prefix": str(tensor_series),
            "branch_point": -2,
            "local_odd_t_coefficients": {
                str(exponent): str(value)
                for exponent, value in fractional_terms.items()
            },
        },
        "abelian_source_residual": {
            "factorization": "exp(A,J)=exp(A,0)*exp(0,K)",
            "right_velocity_equation": "K'=J_vel-rho(A_vel)K",
            "critical_scalar_ode": (
                "x*(1+2*x*a)*k'=j+(6*x*a+3*x^2*a'-1)*k"
            ),
            "typed_factorization_roundtrip": True,
            "ode_roundtrip_rows": verification_rows,
            "series_prefix": str(residual_series),
            "adapter_certificate_sha256": adapter_digest,
            "quadratic_differential_compiler": (
                differential_certificate.to_dict()
            ),
            "polynomial_residual_excluded": True,
            "critical_source_residual_has_infinite_support": True,
            "critical_source_rate": "2",
        },
        "claim_boundary": (
            "After moving the complete Witt factor to the target-kernel "
            "side, the remaining abelian source logarithm satisfies an "
            "exact quadratic-field ODE. Its separated rational rows are "
            "differentially incompatible, so the residual is not a "
            "polynomial and has infinitely many critical source "
            "coefficients. Finite positive-Rees prefixes still require "
            "the tensor-density maximal-face induction."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
