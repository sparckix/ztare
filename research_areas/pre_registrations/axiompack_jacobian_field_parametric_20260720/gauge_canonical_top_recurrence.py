#!/usr/bin/env python3
"""Exact defect-three recurrence for the canonical weighted target normal form.

This replay is deliberately independent of the long recursive normal-form
generator.  It derives the parameter-linear source Hamiltonian from the
public family, reduces it in the inverse cubic, and computes the canonical
defect-three shell in coordinates adapted to the cusp.  It also records a
counterexample to the tempting but false claim that source-coordinate
defect-four corrections cannot feed defect three.
"""
from __future__ import annotations

import json

import sympy as sp


def _coefficient(value: sp.Expr, variable: sp.Symbol, degree: int) -> sp.Expr:
    return sp.factor(sp.expand(value).coeff(variable, degree))


def _family() -> dict[str, object]:
    s, a, g, z = sp.symbols("s A g z")
    v = (a - 3) / 2
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    w = (1 + mu * v) * g
    p = (
        (2 + s / 2) * z
        + (-3 - 3 * s / 2) * z**2
        + s * z**3
    )
    q = (
        (1 + s / 4) * z**2
        - (2 + s) * z**3
        + 3 * s * z**4 / 4
    )
    family = (
        sp.cancel(g * lam / mu * (1 + p.subs(z, w) / g)),
        sp.cancel(
            g**2 * (1 + mu * v + q.subs(z, w) / g**2) / lam
        ),
    )
    jacobian = sp.Matrix([
        [sp.diff(item, variable) for variable in (a, g)]
        for item in family
    ])
    determinant = sp.factor(jacobian.det())
    assert sp.factor(determinant + g**2 / 2) == 0
    return {
        "symbols": (s, a, g),
        "family": family,
        "jacobian": jacobian,
    }


def _linearized_hamiltonian() -> dict[str, object]:
    data = _family()
    s, a, g = data["symbols"]
    family = data["family"]
    jacobian = data["jacobian"]
    p_value, q_value = family

    derivative = (sp.diff(p_value, s), sp.diff(q_value, s))
    source = (
        sp.cancel(
            -2
            * (
                jacobian[1, 1] * derivative[0]
                - jacobian[0, 1] * derivative[1]
            )
            / g**2
        ),
        sp.cancel(
            -2
            * (
                -jacobian[1, 0] * derivative[0]
                + jacobian[0, 0] * derivative[1]
            )
            / g**2
        ),
    )

    seed_target = -p_value**3 / 36 - q_value**2 / 4
    seed_pullback = (
        sp.cancel(-2 * sp.diff(seed_target, g) / g**2),
        sp.cancel(2 * sp.diff(seed_target, a) / g**2),
    )
    normalized = tuple(
        sp.cancel(source[index] - seed_pullback[index])
        for index in range(2)
    )
    assert all(sp.factor(item.subs(s, 0)) == 0 for item in normalized)
    linearized = tuple(
        sp.factor(sp.diff(item, s).subs(s, 0))
        for item in normalized
    )

    expected_tangential_coefficients = (
        (7 * a**3 - 9 * a + 10) / 48,
        -(a - 1) ** 2 * (7 * a**2 - 3) / 16,
        (a - 1) ** 3 * (78 * a**2 - 81 * a - 17) / 192,
        -(a - 1) ** 5 * (7 * a - 10) / 64,
        -3 * (a - 1) ** 7 / 256,
    )
    tangential = sp.factor(sum(
        expected_tangential_coefficients[index] * g**index
        for index in range(len(expected_tangential_coefficients))
    ))
    assert sp.factor(linearized[0] - tangential) == 0
    assert sp.Poly(tangential, g).degree() == 4
    for layer, coefficient in enumerate(expected_tangential_coefficients):
        normal = _coefficient(linearized[1], g, layer + 1)
        assert sp.factor(
            normal + sp.diff(coefficient, a) / (layer + 3)
        ) == 0

    hamiltonian = sp.factor(sp.integrate(-g**2 * tangential / 2, g))
    assert sp.factor(-2 * sp.diff(hamiltonian, g) / g**2 - linearized[0]) == 0
    assert sp.factor(2 * sp.diff(hamiltonian, a) / g**2 - linearized[1]) == 0
    expected_hamiltonian = sp.factor(sum(
        -coefficient * g ** (layer + 3) / (2 * (layer + 3))
        for layer, coefficient in enumerate(expected_tangential_coefficients)
    ))
    assert sp.factor(hamiltonian - expected_hamiltonian) == 0

    seed_family = tuple(sp.factor(item.subs(s, 0)) for item in family)
    expected_seed = (
        g * a - 3 * g**2 * (a - 1) ** 2 / 4,
        g**2 * (a**2 - 1) / 4 - g**3 * (a - 1) ** 3 / 4,
    )
    assert all(
        sp.factor(seed_family[index] - expected_seed[index]) == 0
        for index in range(2)
    )
    return {
        "symbols": (a, g),
        "seed_family": seed_family,
        "linearized": linearized,
        "tangential_coefficients": expected_tangential_coefficients,
        "hamiltonian": hamiltonian,
    }


def _cubic_remainder(
    hamiltonian: sp.Expr,
    a: sp.Symbol,
    g: sp.Symbol,
) -> dict[str, sp.Expr]:
    p, q, w = sp.symbols("P Q W")
    in_w_g = sp.factor(hamiltonian.subs(a, 1 + 2 * w / g))
    in_p_w = sp.factor(in_w_g.subs(g, p - 2 * w + 3 * w**2))
    cubic = sp.Poly(w**3 - w**2 + p * w - q, w)
    remainder = sp.factor(
        sp.rem(sp.Poly(sp.expand(in_p_w), w), cubic).as_expr()
    )
    polynomial = sp.Poly(remainder, w)
    constant = sp.factor(polynomial.coeff_monomial(1))
    linear = sp.factor(polynomial.coeff_monomial(w))
    quadratic = sp.factor(polynomial.coeff_monomial(w**2))

    expected_constant = -(
        70 * p**3
        - 480 * p**2 * q
        - 51 * p * q
        + 1770 * q**2
        - 4 * q
    ) / 2520
    expected_linear = -(
        480 * p**3
        - 159 * p**2
        - 2070 * p * q
        + 4 * p
        - 1215 * q**2
        + 696 * q
    ) / 2520
    expected_quadratic = -(
        135 * p**2
        + 1485 * p * q
        - 12 * p
        - 684 * q
        - 4
    ) / 2520
    assert sp.factor(constant - expected_constant) == 0
    assert sp.factor(linear - expected_linear) == 0
    assert sp.factor(quadratic - expected_quadratic) == 0
    difference_numerator = sp.together(
        in_p_w - remainder
    ).as_numer_denom()[0]
    assert sp.rem(
        sp.Poly(sp.expand(difference_numerator), w),
        cubic,
    ).as_expr() == 0
    return {
        "P": p,
        "Q": q,
        "W": w,
        "remainder": remainder,
        "constant": constant,
        "linear": linear,
        "quadratic": quadratic,
    }


def _trace_shell_check(
    cubic_data: dict[str, sp.Expr],
) -> dict[str, sp.Expr]:
    p = cubic_data["P"]
    q = cubic_data["Q"]
    linear = cubic_data["linear"]
    quadratic = cubic_data["quadratic"]
    u, g = sp.symbols("u g")

    # Under A=u/g, W=(u-g)/2.  The other small cubic root is
    # W'=(1-W-sqrt((1-3W)^2-4g))/2.  We solve only the two square-root
    # coefficients needed below.
    alpha = 1 - 3 * u / 2
    square_root_1 = sp.factor((3 * alpha - 4) / (2 * alpha))
    square_root_2 = sp.factor(
        (sp.Rational(9, 4) - square_root_1**2) / (2 * alpha)
    )
    branch_difference_1 = sp.factor(
        (square_root_1 - sp.Rational(3, 2)) / 2
    )
    branch_difference_2 = sp.factor(square_root_2 / 2)
    assert sp.factor(branch_difference_1 - 2 / (3 * u - 2)) == 0

    p0 = u - 3 * u**2 / 4
    p1 = 3 * u / 2
    p2 = -sp.Rational(3, 4)
    q0 = u**2 / 4 - u**3 / 4
    q1 = 3 * u**2 / 4
    q2 = -sp.Rational(1, 4) - 3 * u / 4
    substitution = {p: p0, q: q0}

    # U=W+W' equals u+u1*g+u2*g^2+... in the defect scaling.
    branch_sum_1 = sp.factor(-1 - branch_difference_1)
    branch_sum_2 = sp.factor(-branch_difference_2)

    def first_variation(value: sp.Expr) -> sp.Expr:
        return sp.factor(
            sp.diff(value, p).subs(substitution) * p1
            + sp.diff(value, q).subs(substitution) * q1
        )

    def second_variation(value: sp.Expr) -> sp.Expr:
        return sp.factor(
            sp.diff(value, p).subs(substitution) * p2
            + sp.diff(value, q).subs(substitution) * q2
            + sp.diff(value, p, 2).subs(substitution) * p1**2 / 2
            + sp.diff(sp.diff(value, p), q).subs(substitution) * p1 * q1
            + sp.diff(value, q, 2).subs(substitution) * q1**2 / 2
        )

    linear_0 = sp.factor(linear.subs(substitution))
    quadratic_0 = sp.factor(quadratic.subs(substitution))
    sum_factor_0 = sp.factor(linear_0 + quadratic_0 * u)
    sum_factor_1 = sp.factor(
        first_variation(linear)
        + first_variation(quadratic) * u
        + quadratic_0 * branch_sum_1
    )
    sum_factor_2 = sp.factor(
        second_variation(linear)
        + second_variation(quadratic) * u
        + first_variation(quadratic) * branch_sum_1
        + quadratic_0 * branch_sum_2
    )
    assert sum_factor_0 == 0
    assert sum_factor_1 == 0
    expected_sum_factor_2 = (
        9 * u**3 - 36 * u**2 + 39 * u - 10
    ) / (72 * (3 * u - 2))
    assert sp.factor(sum_factor_2 - expected_sum_factor_2) == 0

    # For phi=a+bW+cW^2, the anti-trace over the two small roots is
    # (W-W')*(b+c*(W+W'))/2.
    trace_shell = sp.factor(branch_difference_1 * sum_factor_2 / 2)
    expected_shell = (
        9 * u**3 - 36 * u**2 + 39 * u - 10
    ) / (72 * (3 * u - 2) ** 2)
    assert sp.factor(trace_shell - expected_shell) == 0
    return {
        "u": u,
        "branch_difference_linear": branch_difference_1,
        "branch_sum_linear": branch_sum_1,
        "branch_sum_quadratic": branch_sum_2,
        "sum_factor_quadratic": sum_factor_2,
        "trace_shell": trace_shell,
    }


def _canonical_shell(
    hamiltonian: sp.Expr,
    a: sp.Symbol,
    g: sp.Symbol,
) -> dict[str, sp.Expr]:
    u = sp.symbols("u")
    defect_expansion = sp.expand(hamiltonian.subs(a, u / g))
    phi0 = _coefficient(defect_expansion, g, 0)
    phi2 = _coefficient(defect_expansion, g, 2)
    phi3 = _coefficient(defect_expansion, g, 3)
    expected_phi0 = (
        u**3
        * (
            135 * u**4
            + 1470 * u**3
            - 6552 * u**2
            + 8820 * u
            - 3920
        )
        / 161280
    )
    expected_phi2 = (
        u
        * (
            27 * u**4
            + 240 * u**3
            - 368 * u**2
            + 48 * u
            + 48
        )
        / 1536
    )
    expected_phi3 = -(
        135 * u**4
        + 1020 * u**3
        - 648 * u**2
        - 216 * u
        + 160
    ) / 4608
    assert sp.factor(phi0 - expected_phi0) == 0
    assert sp.factor(phi2 - expected_phi2) == 0
    assert sp.factor(phi3 - expected_phi3) == 0

    # The defect-scale seed map is x(u)+g*v1+g^2*v2+g^3*v3.
    p = u - 3 * u**2 / 4
    q = u**2 / 4 - u**3 / 4
    p1 = 3 * u / 2
    q1 = 3 * u**2 / 4
    p2 = -sp.Rational(3, 4)
    q2 = -sp.Rational(1, 4) - 3 * u / 4
    q3 = sp.Rational(1, 4)

    # Choose xi so p(xi) is the exact first target coordinate through g^3.
    p_prime = sp.diff(p, u)
    xi1 = sp.factor(p1 / p_prime)
    xi2 = sp.factor((p2 + 3 * xi1**2 / 4) / p_prime)
    xi3 = sp.factor(3 * xi1 * xi2 / (2 * p_prime))
    expected_xi = (
        -3 * u / (3 * u - 2),
        -6 * (3 * u - 1) / (3 * u - 2) ** 3,
        -54 * u * (3 * u - 1) / (3 * u - 2) ** 5,
    )
    assert all(
        sp.factor(value - expected_xi[index]) == 0
        for index, value in enumerate((xi1, xi2, xi3))
    )

    # N=Q-q(xi) is transverse to the cusp and starts in defect two.
    normal2 = sp.factor(
        q2
        - (
            sp.diff(q, u) * xi2
            + sp.diff(q, u, 2) * xi1**2 / 2
        )
    )
    normal3 = sp.factor(
        q3
        - (
            sp.diff(q, u) * xi3
            + sp.diff(q, u, 2) * xi1 * xi2
            + sp.diff(q, u, 3) * xi1**3 / 6
        )
    )
    assert sp.factor(q1 - sp.diff(q, u) * xi1) == 0
    assert sp.factor(normal2 - 1 / (2 * (3 * u - 2))) == 0
    assert sp.factor(
        normal3 - (9 * u - 4) / (2 * (3 * u - 2) ** 3)
    ) == 0

    # In the adapted chart H=H0(xi)+N*H1(xi)+O(N^2).
    # Canonical opposite parity makes the residual Hamiltonian odd in
    # defect, so matching defects zero and two fixes H0 and H1.
    target_normal_1 = sp.factor(
        (
            phi2
            - (
                sp.diff(phi0, u) * xi2
                + sp.diff(phi0, u, 2) * xi1**2 / 2
            )
        )
        / normal2
    )
    expected_target_normal_1 = (
        u * (9 * u**3 - 64 * u**2 + 108 * u - 48) / 384
    )
    assert sp.factor(target_normal_1 - expected_target_normal_1) == 0

    target_defect3 = sp.factor(
        sp.diff(phi0, u) * xi3
        + sp.diff(phi0, u, 2) * xi1 * xi2
        + sp.diff(phi0, u, 3) * xi1**3 / 6
        + normal3 * target_normal_1
        + normal2 * xi1 * sp.diff(target_normal_1, u)
    )
    canonical_shell = sp.factor(phi3 - target_defect3)
    expected_shell = (
        9 * u**3 - 36 * u**2 + 39 * u - 10
    ) / (72 * (3 * u - 2) ** 2)
    assert sp.factor(canonical_shell - expected_shell) == 0

    # Since N starts at g^2, all N^2 and higher target terms start at g^4.
    # This is the correct completeness statement for the defect-three jet.
    assert sp.factor(normal2) != 0
    return {
        "u": u,
        "phi0": phi0,
        "phi2": phi2,
        "phi3": phi3,
        "xi1": xi1,
        "xi2": xi2,
        "xi3": xi3,
        "normal2": normal2,
        "normal3": normal3,
        "target_normal_1": target_normal_1,
        "target_defect3": target_defect3,
        "canonical_shell": canonical_shell,
        "higher_normal_terms_minimum_defect": sp.Integer(4),
    }


def _false_defect_shortcut_counterexample(
    a: sp.Symbol,
    g: sp.Symbol,
) -> dict[str, sp.Expr]:
    p, q = sp.symbols("P Q")
    trace_weight_four = -(4 * p**4 - 29 * p**2 * q + 40 * q**2) / 48
    canonical_weight_four = -p**2 * (p**2 - 6 * q) / 32
    weight_four_difference = sp.factor(
        canonical_weight_four - trace_weight_four
    )
    expected_difference = sp.Rational(5, 6) * (q - p**2 / 4) ** 2
    assert sp.factor(weight_four_difference - expected_difference) == 0

    c3 = sp.factor((a - 1) ** 2 * (a + 2) / 8)
    c4 = sp.factor(-9 * (a - 1) ** 4 / 64)
    g_bar = -sp.Rational(1, 4) + g * c3 + g**2 * c4
    correction = sp.expand(sp.Rational(5, 6) * g_bar**2)
    exported = _coefficient(correction, g, 2)
    defect_three_coefficient = sp.factor(
        sp.Poly(exported, a).coeff_monomial(a**3)
    )
    assert sp.factor(defect_three_coefficient + sp.Rational(35, 192)) == 0
    return {
        "C3": c3,
        "C4": c4,
        "trace_weight_four": trace_weight_four,
        "canonical_weight_four": canonical_weight_four,
        "weight_four_difference": weight_four_difference,
        "weight_four_correction": sp.Rational(5, 6),
        "g2_export": exported,
        "weight_six_A3_coefficient": defect_three_coefficient,
    }


def _coefficient_law(shell: sp.Expr, u: sp.Symbol) -> dict[str, object]:
    residual = sp.factor(-2 * (3 * shell + u * sp.diff(shell, u)))
    expected_residual = (
        18 * u**4
        - 72 * u**3
        + 99 * u**2
        - 57 * u
        + 10
    ) / (6 * (2 - 3 * u) ** 3)
    assert sp.factor(residual - expected_residual) == 0
    assert sp.factor(
        6 * (2 - 3 * u) ** 3 * residual
        - (
            18 * u**4
            - 72 * u**3
            + 99 * u**2
            - 57 * u
            + 10
        )
    ) == 0

    partial_fraction = (
        -u / 9
        + sp.Rational(2, 9)
        + 1 / (18 * (2 - 3 * u))
        - 1 / (54 * (2 - 3 * u) ** 2)
        - 8 / (27 * (2 - 3 * u) ** 3)
    )
    assert sp.factor(residual - partial_fraction) == 0

    m = sp.symbols("m", integer=True, nonnegative=True)
    closed_coefficient = sp.factor(
        -sp.Rational(1, 216)
        * sp.Rational(3, 2) ** m
        * (m + 3)
        * (4 * m + 1)
    )
    extracted_tail = sp.factor(
        sp.Rational(1, 36) * sp.Rational(3, 2) ** m
        - (m + 1) * sp.Rational(3, 2) ** m / 216
        - (m + 1) * (m + 2) * sp.Rational(3, 2) ** m / 54
    )
    assert sp.factor(extracted_tail - closed_coefficient) == 0
    recurrence = sp.factor(
        8 * closed_coefficient.subs(m, m + 3)
        - 36 * closed_coefficient.subs(m, m + 2)
        + 54 * closed_coefficient.subs(m, m + 1)
        - 27 * closed_coefficient
    )
    assert recurrence == 0

    prefix = [
        sp.factor(sp.series(residual, u, 0, 12).removeO().coeff(u, index))
        for index in range(12)
    ]
    assert prefix[:6] == [
        sp.Rational(5, 24),
        -sp.Rational(1, 4),
        -sp.Rational(15, 32),
        -sp.Rational(39, 32),
        -sp.Rational(357, 128),
        -sp.Rational(189, 32),
    ]
    for index in range(2, len(prefix)):
        assert sp.factor(
            prefix[index] - closed_coefficient.subs(m, index)
        ) == 0
    return {
        "residual_generating_function": residual,
        "partial_fraction": partial_fraction,
        "closed_coefficient_m_ge_2": closed_coefficient,
        "recurrence": "8*r[m+3]-36*r[m+2]+54*r[m+1]-27*r[m]=0",
        "prefix": prefix,
    }


def run() -> dict[str, object]:
    linearized = _linearized_hamiltonian()
    a, g = linearized["symbols"]
    cubic = _cubic_remainder(linearized["hamiltonian"], a, g)
    trace = _trace_shell_check(cubic)
    canonical = _canonical_shell(linearized["hamiltonian"], a, g)
    assert sp.factor(trace["trace_shell"] - canonical["canonical_shell"]) == 0
    counterexample = _false_defect_shortcut_counterexample(a, g)
    coefficient_law = _coefficient_law(
        canonical["canonical_shell"],
        canonical["u"],
    )

    return {
        "schema": "axiompack.jacobian_canonical_top_recurrence.v1",
        "seed_family": [str(item) for item in linearized["seed_family"]],
        "linearized_source_hamiltonian": str(linearized["hamiltonian"]),
        "linearized_tangential_coefficients": [
            str(item) for item in linearized["tangential_coefficients"]
        ],
        "inverse_cubic": "W^3-W^2+P*W-Q",
        "cubic_remainder": {
            "constant": str(cubic["constant"]),
            "linear": str(cubic["linear"]),
            "quadratic": str(cubic["quadratic"]),
        },
        "branch_shell_check": {
            "involution": "exchange the two small roots W and W'",
            "branch_difference_linear": str(trace["branch_difference_linear"]),
            "branch_sum_linear": str(trace["branch_sum_linear"]),
            "branch_sum_quadratic": str(trace["branch_sum_quadratic"]),
            "shell": str(trace["trace_shell"]),
        },
        "canonical_cusp_coordinates": {
            "sign_involution": "(A,g)->(-A,-g), fixing u=g*A",
            "xi_coefficients": [
                str(canonical["xi1"]),
                str(canonical["xi2"]),
                str(canonical["xi3"]),
            ],
            "normal_coefficients": [
                str(canonical["normal2"]),
                str(canonical["normal3"]),
            ],
            "target_normal_1": str(canonical["target_normal_1"]),
            "shell": str(canonical["canonical_shell"]),
            "higher_normal_terms_minimum_defect": int(
                canonical["higher_normal_terms_minimum_defect"]
            ),
        },
        "false_termwise_defect_shortcut": {
            "verdict": "counterexample",
            "trace_weight_four": str(counterexample["trace_weight_four"]),
            "canonical_weight_four": str(
                counterexample["canonical_weight_four"]
            ),
            "weight_four_difference": str(
                counterexample["weight_four_difference"]
            ),
            "C3": str(counterexample["C3"]),
            "C4": str(counterexample["C4"]),
            "weight_six_A3_coefficient": str(
                counterexample["weight_six_A3_coefficient"]
            ),
        },
        "coefficient_law": {
            "generating_function": str(
                coefficient_law["residual_generating_function"]
            ),
            "closed_coefficient_m_ge_2": str(
                coefficient_law["closed_coefficient_m_ge_2"]
            ),
            "recurrence": coefficient_law["recurrence"],
            "prefix": [str(item) for item in coefficient_law["prefix"]],
        },
        "local_finiteness_consequence": (
            "the s-linear source connection and each polynomial target "
            "pullback have finite gamma support; the nonzero infinite "
            "canonical residual tail therefore requires infinitely many "
            "s-linear target weights and is not in Q[P,Q][[s]]"
        ),
        "claim_boundary": (
            "the recurrence belongs to the completed canonical weighted "
            "normal form; it does not establish the symmetric source-target "
            "minimax obstruction"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
