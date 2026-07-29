#!/usr/bin/env python3
"""Exact finite-branch Weierstrass factor for the inverse quartic.

The generic inverse equation has a fourth root escaping to infinity as the
deformation parameter tends to zero.  In the s-adic completion its reciprocal
is contractive, so the escaping factor is a unit and the three finite sheets
are governed by a monic cubic.
"""
from __future__ import annotations

import json

import sympy as sp


Series = list[sp.Expr]


def _scalar_series(
    value: sp.Expr,
    parameter: sp.Symbol,
    length: int,
) -> Series:
    return [
        sp.cancel(
            sp.diff(value, parameter, order).subs(parameter, 0)
            / sp.factorial(order)
        )
        for order in range(length)
    ]


def _add(*values: Series) -> Series:
    return [
        sp.expand(sum(value[order] for value in values))
        for order in range(len(values[0]))
    ]


def _neg(value: Series) -> Series:
    return [-coefficient for coefficient in value]


def _scale(value: Series, scalar: sp.Expr) -> Series:
    return [
        sp.expand(scalar * coefficient)
        for coefficient in value
    ]


def _multiply(left: Series, right: Series) -> Series:
    return [
        sp.expand(sum(
            left[index] * right[order - index]
            for index in range(order + 1)
        ))
        for order in range(len(left))
    ]


def _power(value: Series, exponent: int) -> Series:
    result = [sp.Integer(1)] + [
        sp.Integer(0) for _ in range(len(value) - 1)
    ]
    for _ in range(exponent):
        result = _multiply(result, value)
    return result


def _reciprocal(value: Series) -> Series:
    if value[0] == 0:
        raise ValueError("a unit series is required")
    result = [sp.cancel(1 / value[0])] + [
        sp.Integer(0) for _ in range(len(value) - 1)
    ]
    for order in range(1, len(value)):
        result[order] = sp.cancel(
            -sum(
                value[index] * result[order - index]
                for index in range(1, order + 1)
            )
            / value[0]
        )
    return result


def _compose_polynomial(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
    first_series: Series,
    second_series: Series,
) -> Series:
    result = [
        sp.Integer(0) for _ in range(len(first_series))
    ]
    for (first_power, second_power), coefficient in sp.Poly(
        value, first, second, domain=sp.QQ
    ).terms():
        term = _scale(
            _multiply(
                _power(first_series, first_power),
                _power(second_series, second_power),
            ),
            coefficient,
        )
        result = _add(result, term)
    return result


def _compose_map(
    value: Series,
    first: sp.Symbol,
    second: sp.Symbol,
    first_series: Series,
    second_series: Series,
) -> Series:
    result = [
        sp.Integer(0) for _ in range(len(first_series))
    ]
    for parameter_order, coefficient in enumerate(value):
        if parameter_order >= len(result):
            break
        composed = _compose_polynomial(
            coefficient,
            first,
            second,
            first_series,
            second_series,
        )
        result = _add(
            result,
            [sp.Integer(0)] * parameter_order
            + composed[:len(result) - parameter_order],
        )
    return result


def _filtered_degree(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> int:
    if value == 0:
        return -1
    return max(
        4 * p_power + 6 * q_power
        for (p_power, q_power), coefficient
        in sp.Poly(value, p, q, domain=sp.QQ).terms()
        if coefficient
    )


def _odd_sharp_coefficient(k: int) -> sp.Rational:
    """Coefficient of ``P^k`` in ``[s^(2k+1)] z``."""

    return sp.Rational(
        (-1) ** k * sp.binomial(3 * k, k),
        4 * 16**k * (2 * k + 1),
    )


def _even_sharp_coefficient(k: int) -> sp.Rational:
    """Coefficient of ``P^k*Q`` in ``[s^(2k+4)] z``."""

    return sp.Rational(
        (-1) ** k
        * (2 * k + 5)
        * sp.binomial(3 * k + 5, k),
        (3 * k + 5) * 4 ** (2 * k + 4),
    )


def run(*, precision: int = 10) -> dict[str, object]:
    if precision < 3:
        raise ValueError("precision must expose the first volume defect")

    s, p, q, w, u = sp.symbols("s P Q W U")
    length = precision + 2
    zero = [sp.Integer(0) for _ in range(length)]
    one = [sp.Integer(1)] + zero[1:]

    a_exact = s / (2 * (s + 2))
    b_exact = (s + 4) / (2 * (s + 2))
    c_exact = 12 / ((s - 6) * (s + 2))
    d_exact = -(s - 4) / (2 * (s + 2))
    a = _scalar_series(a_exact, s, length)
    b = _scalar_series(b_exact, s, length)
    c = _scalar_series(c_exact, s, length)
    d = _scalar_series(d_exact, s, length)

    # The fixed-point map is s-adically contractive on s*QQ[P,Q][[s]].
    z = zero
    for _ in range(length + 2):
        z = _add(
            a,
            _multiply(b, _power(z, 2)),
            _scale(_multiply(c, _power(z, 3)), p),
            _scale(_multiply(d, _power(z, 4)), q),
        )
    fixed_point_residual = _add(
        z,
        _neg(a),
        _neg(_multiply(b, _power(z, 2))),
        _neg(_scale(_multiply(c, _power(z, 3)), p)),
        _neg(_scale(_multiply(d, _power(z, 4)), q)),
    )
    assert all(item == 0 for item in fixed_point_residual[:precision])

    sharp_shell: list[dict[str, object]] = []
    for order in range(3, precision):
        polynomial = sp.Poly(z[order], p, q, domain=sp.QQ)
        if order % 2 == 1:
            k = (order - 1) // 2
            exponent = (k, 0)
            expected = _odd_sharp_coefficient(k)
        else:
            k = (order - 4) // 2
            exponent = (k, 1)
            expected = _even_sharp_coefficient(k)
        actual = polynomial.coeff_monomial(
            p ** exponent[0] * q ** exponent[1]
        )
        assert actual == expected
        assert actual != 0
        assert 4 * exponent[0] + 6 * exponent[1] == 2 * order - 2
        sharp_shell.append({
            "order": order,
            "P_exponent": exponent[0],
            "Q_exponent": exponent[1],
            "coefficient": str(actual),
            "filtered_degree": 2 * order - 2,
        })

    # Since a=s/(2(s+2)), z/a=4*z/s+2*z coefficientwise.
    ratio = [
        sp.expand(4 * z[order + 1] + 2 * z[order])
        for order in range(length - 1)
    ] + [sp.Integer(0)]
    assert ratio[0] == 1

    cubic_a = _neg(_multiply(
        ratio,
        _add(
            b,
            _scale(_multiply(c, z), p),
            _scale(_multiply(d, _power(z, 2)), q),
        ),
    ))
    cubic_b = _neg(_multiply(
        ratio,
        _add(
            _scale(c, p),
            _scale(_multiply(d, z), q),
        ),
    ))
    cubic_c = _neg(_scale(_multiply(ratio, d), q))

    inverse_quartic = _add(
        _scale(one, w**3),
        _scale(a, -w**4),
        _scale(b, -w**2),
        _scale(c, -p * w),
        _scale(d, -q),
    )
    finite_cubic = _add(
        _scale(one, w**3),
        _scale(cubic_a, w**2),
        _scale(cubic_b, w),
        cubic_c,
    )
    unit_factor = _add(one, _scale(z, -w))
    factorization_residual = _add(
        _multiply(ratio, inverse_quartic),
        _neg(_multiply(unit_factor, finite_cubic)),
    )
    assert all(
        item == 0 for item in factorization_residual[:precision]
    )

    # Translate the finite cubic back to the seed coefficient convention.
    root_shift = _scale(_add(cubic_a, one), sp.Rational(1, 3))
    normalized_p = _add(
        cubic_b,
        _scale(
            _add(one, _neg(_power(cubic_a, 2))),
            sp.Rational(1, 3),
        ),
    )
    normalized_q = _add(
        _neg(cubic_c),
        _multiply(root_shift, cubic_b),
        _neg(_scale(
            _multiply(
                _power(root_shift, 2),
                _add(_scale(cubic_a, 2), _neg(one)),
            ),
            sp.Rational(1, 3),
        )),
    )
    translated_cubic = _add(
        _power(_add(_scale(one, u), _neg(root_shift)), 3),
        _multiply(
            cubic_a,
            _power(
                _add(_scale(one, u), _neg(root_shift)),
                2,
            ),
        ),
        _multiply(
            cubic_b,
            _add(_scale(one, u), _neg(root_shift)),
        ),
        cubic_c,
    )
    normalized_seed_cubic = _add(
        _scale(one, u**3 - u**2),
        _scale(normalized_p, u),
        _neg(normalized_q),
    )
    normalization_residual = _add(
        translated_cubic,
        _neg(normalized_seed_cubic),
    )
    assert all(
        item == 0 for item in normalization_residual[:precision]
    )

    # The coefficient map respects the equivariant target ideals, but its
    # determinant is not one.  This is the remaining contact correction.
    target_jacobian = [
        sp.expand(sum(
            sp.diff(normalized_p[index], p)
            * sp.diff(normalized_q[order - index], q)
            - sp.diff(normalized_p[index], q)
            * sp.diff(normalized_q[order - index], p)
            for index in range(order + 1)
        ))
        for order in range(length)
    ]
    assert target_jacobian[0] == 1
    assert target_jacobian[1] == -sp.Rational(5, 12)

    for order in range(1, precision):
        assert normalized_p[order].subs({p: 0, q: 0}) == 0
        q_axis = sp.Poly(
            normalized_q[order].subs(q, 0),
            p,
            domain=sp.QQ,
        )
        assert q_axis.coeff_monomial(1) == 0
        assert q_axis.coeff_monomial(p) == 0

        assert _filtered_degree(z[order], p, q) <= 2 * order - 2
        assert (
            _filtered_degree(ratio[order], p, q)
            <= 2 * order
        )
        assert (
            _filtered_degree(cubic_a[order], p, q)
            <= 2 * order + 2
        )
        assert (
            _filtered_degree(cubic_b[order], p, q)
            <= 2 * order + 4
        )
        assert (
            _filtered_degree(cubic_c[order], p, q)
            <= 2 * order + 6
        )
        assert (
            _filtered_degree(root_shift[order], p, q)
            <= 2 * order + 2
        )
        assert (
            _filtered_degree(normalized_p[order], p, q)
            <= 2 * order + 4
        )
        assert (
            _filtered_degree(normalized_q[order], p, q)
            <= 2 * order + 6
        )

    # Correct the coefficient map to determinant one.  If T=(P',Q') and
    # J=det(DT), put rho=1/(J o T^-1) and
    # R(Y1,Y2)=(integral_0^Y1 rho(u,Y2)du,Y2).  Then H=R o T has
    # determinant one.  The construction is formal and all-order; a shorter
    # exact prefix keeps this replay inexpensive.
    volume_length = min(precision, 7)
    identity_p = [p] + [
        sp.Integer(0) for _ in range(volume_length - 1)
    ]
    identity_q = [q] + [
        sp.Integer(0) for _ in range(volume_length - 1)
    ]
    target_p = normalized_p[:volume_length]
    target_q = normalized_q[:volume_length]
    inverse_p = identity_p
    inverse_q = identity_q
    target_delta_p = _add(target_p, _neg(identity_p))
    target_delta_q = _add(target_q, _neg(identity_q))
    for _ in range(volume_length + 1):
        inverse_p = _add(
            identity_p,
            _neg(_compose_map(
                target_delta_p,
                p,
                q,
                inverse_p,
                inverse_q,
            )),
        )
        inverse_q = _add(
            identity_q,
            _neg(_compose_map(
                target_delta_q,
                p,
                q,
                inverse_p,
                inverse_q,
            )),
        )
    inverse_check_p = _compose_map(
        target_p, p, q, inverse_p, inverse_q
    )
    inverse_check_q = _compose_map(
        target_q, p, q, inverse_p, inverse_q
    )
    assert inverse_check_p == identity_p
    assert inverse_check_q == identity_q

    density = _reciprocal(_compose_map(
        target_jacobian[:volume_length],
        p,
        q,
        inverse_p,
        inverse_q,
    ))
    integration_variable = sp.Symbol("_integration_P")
    correction_p = [
        sp.expand(sp.integrate(
            coefficient.subs(p, integration_variable),
            (integration_variable, 0, p),
        ))
        for coefficient in density
    ]
    corrected_p = _compose_map(
        correction_p, p, q, target_p, target_q
    )
    corrected_q = target_q
    corrected_jacobian = [
        sp.expand(sum(
            sp.diff(corrected_p[index], p)
            * sp.diff(corrected_q[order - index], q)
            - sp.diff(corrected_p[index], q)
            * sp.diff(corrected_q[order - index], p)
            for index in range(order + 1)
        ))
        for order in range(volume_length)
    ]
    assert corrected_jacobian == [
        sp.Integer(1)
    ] + [sp.Integer(0) for _ in range(volume_length - 1)]
    for order in range(1, volume_length):
        assert corrected_p[order].subs({p: 0, q: 0}) == 0
        corrected_q_axis = sp.Poly(
            corrected_q[order].subs(q, 0),
            p,
            domain=sp.QQ,
        )
        assert corrected_q_axis.coeff_monomial(1) == 0
        assert corrected_q_axis.coeff_monomial(p) == 0
        assert (
            _filtered_degree(density[order], p, q)
            <= 2 * order
        )
        assert (
            _filtered_degree(corrected_p[order], p, q)
            <= 2 * order + 4
        )
        assert (
            _filtered_degree(corrected_q[order], p, q)
            <= 2 * order + 6
        )

    # Pull the determinant-one target normalization back through the seed.
    # This computes the source-side discriminator without choosing source
    # coefficients independently at each order.
    v, t, polynomial_variable = sp.symbols("v t polynomial_variable")
    gamma = 1 - sp.Rational(3, 2) * v + t
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    family_w = (1 + mu * v) * gamma
    family_polynomial_p = (
        (2 + s / 2) * polynomial_variable
        + (-3 - 3 * s / 2) * polynomial_variable**2
        + s * polynomial_variable**3
    )
    family_polynomial_q = (
        (1 + s / 4) * polynomial_variable**2
        - (2 + s) * polynomial_variable**3
        + 3 * s * polynomial_variable**4 / 4
    )
    family_p_exact = sp.cancel(
        lam / mu
        * (
            gamma
            + family_polynomial_p.subs(
                polynomial_variable, family_w
            )
        )
    )
    family_q_exact = sp.cancel(
        (
            gamma**2 * (1 + mu * v)
            + family_polynomial_q.subs(
                polynomial_variable, family_w
            )
        )
        / lam
    )
    source_length = min(volume_length, 5)
    family_p = _scalar_series(
        family_p_exact, s, source_length
    )
    family_q = _scalar_series(
        family_q_exact, s, source_length
    )
    seed_p, seed_q = family_p[0], family_q[0]
    seed_jacobian = sp.Matrix([
        [sp.diff(seed_p, variable) for variable in (v, t)],
        [sp.diff(seed_q, variable) for variable in (v, t)],
    ])

    def source_probe(
        target_map_p: Series,
        target_map_q: Series,
    ) -> dict[str, object]:
        normalized_family_p = _compose_map(
            target_map_p[:source_length],
            p,
            q,
            family_p,
            family_q,
        )
        normalized_family_q = _compose_map(
            target_map_q[:source_length],
            p,
            q,
            family_p,
            family_q,
        )
        source_v = [v] + [
            sp.Integer(0) for _ in range(source_length - 1)
        ]
        source_t = [t] + [
            sp.Integer(0) for _ in range(source_length - 1)
        ]
        source_degrees: list[tuple[int, int]] = []
        source_within_slope_two = True
        for order in range(1, source_length):
            composed_seed_p = _compose_polynomial(
                seed_p, v, t, source_v, source_t
            )
            composed_seed_q = _compose_polynomial(
                seed_q, v, t, source_v, source_t
            )
            residual = sp.Matrix([
                sp.expand(
                    normalized_family_p[order]
                    - composed_seed_p[order]
                ),
                sp.expand(
                    normalized_family_q[order]
                    - composed_seed_q[order]
                ),
            ])
            source_coefficient = [
                sp.cancel(value)
                for value in seed_jacobian.inv() * residual
            ]
            assert all(
                not ({v, t} & sp.denom(value).free_symbols)
                for value in source_coefficient
            )
            source_v[order], source_t[order] = source_coefficient
            degrees = tuple(
                int(sp.Poly(
                    value, v, t, domain=sp.QQ
                ).total_degree())
                if value != 0 else -1
                for value in source_coefficient
            )
            source_degrees.append(degrees)
            source_within_slope_two = (
                source_within_slope_two
                and max(degrees) <= 2 * order + 1
            )
        assert _compose_polynomial(
            seed_p, v, t, source_v, source_t
        ) == normalized_family_p
        assert _compose_polynomial(
            seed_q, v, t, source_v, source_t
        ) == normalized_family_q
        return {
            "checked_through_s_order": source_length - 1,
            "component_degrees": {
                str(order): list(source_degrees[order - 1])
                for order in range(1, source_length)
            },
            "slope_two_bound": "max degree <= 2*n+1",
            "within_slope_two_through_checked_range": (
                source_within_slope_two
            ),
            "coefficientwise_polynomial": True,
            "full_recomposition_checked": True,
        }

    coefficient_source_probe = source_probe(target_p, target_q)
    volume_corrected_source_probe = source_probe(
        corrected_p, corrected_q
    )

    return {
        "schema": "axiompack.jacobian_weierstrass_finite_branch.v1",
        "inverse_quartic": (
            "W^3-a(s)W^4-b(s)W^2-c(s)P*W-d(s)Q"
        ),
        "scalars": {
            "a": str(a_exact),
            "b": str(b_exact),
            "c": str(c_exact),
            "d": str(d_exact),
        },
        "reciprocal_infinity_root": {
            "equation": "z=a+b*z^2+c*P*z^3+d*Q*z^4",
            "coefficients": [
                str(sp.factor(z[order]))
                for order in range(1, precision)
            ],
            "filtered_bound": "deg_f([s^n]z)<=2*n-2",
            "sharp_from_order_three": True,
            "sharp_shell_equation": "Z=1/4-x*Z^3+y*Z^4",
            "sharp_shell_coefficients": sharp_shell,
            "odd_closed_form": (
                "[P^k s^(2k+1)]z="
                "(-1)^k*binomial(3k,k)/(4*16^k*(2k+1))"
            ),
            "even_closed_form": (
                "[P^k Q s^(2k+4)]z="
                "(-1)^k*(2k+5)*binomial(3k+5,k)"
                "/((3k+5)*4^(2k+4))"
            ),
        },
        "factorization": {
            "identity": (
                "(z/a)*R_s(W)=(1-z*W)"
                "*(W^3+A*W^2+B*W+C)"
            ),
            "unit_factor": "1-z*W",
            "checked_through_s_order": precision - 1,
            "finite_cubic_special_fiber": (
                "W^3-W^2+P*W-Q"
            ),
        },
        "seed_coefficient_normalization": {
            "root_shift": "(A+1)/3",
            "P_prime": "B+(1-A^2)/3",
            "Q_prime": (
                "-C+(A+1)*B/3"
                "-(A+1)^2*(2*A-1)/27"
            ),
            "target_lift_ideals_checked": True,
            "filtered_bounds": {
                "root_shift_n": "2*n+2",
                "P_prime_n": "2*n+4",
                "Q_prime_n": "2*n+6",
            },
        },
        "filtered_volume_normalization": {
            "construction": (
                "rho=1/(det(DT) o T^-1); "
                "R(Y1,Y2)=(integral_0^Y1 rho(u,Y2)du,Y2); "
                "H=R o T"
            ),
            "checked_through_s_order": volume_length - 1,
            "target_jacobian_coefficients": [
                str(coefficient)
                for coefficient in corrected_jacobian
            ],
            "target_lift_ideals_checked": True,
            "density_filtered_bound": "deg_f(rho_n)<=2*n",
            "corrected_target_bounds": {
                "H_P_n": "2*n+4",
                "H_Q_n": "2*n+6",
            },
            "first_coefficients": {
                "H_P_1": str(sp.factor(corrected_p[1])),
                "H_Q_1": str(sp.factor(corrected_q[1])),
            },
        },
        "induced_source_lift_probes": {
            "coefficient_normalization": coefficient_source_probe,
            "volume_corrected_normalization": (
                volume_corrected_source_probe
            ),
        },
        "contact_boundary": {
            "target_jacobian_s_coefficient_0": str(
                target_jacobian[0]
            ),
            "target_jacobian_s_coefficient_1": str(
                target_jacobian[1]
            ),
            "hamiltonian_already": False,
            "remaining_task": (
                "bound the source lift induced by the filtered "
                "determinant-one target normalization"
            ),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
