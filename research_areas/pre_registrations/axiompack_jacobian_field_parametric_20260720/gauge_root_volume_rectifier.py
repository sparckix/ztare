#!/usr/bin/env python3
"""Exact replay of the filtered root-cover divergence right inverse."""
from __future__ import annotations

import hashlib
import json

import sympy as sp


def _filtered_degree(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> int:
    if value == 0:
        return -1
    return max(
        4 * i + 6 * j
        for (i, j), coefficient in sp.Poly(
            value, p, q, domain=sp.QQ
        ).terms()
        if coefficient
    )


def _ordinary_degree(
    value: sp.Expr,
    first: sp.Symbol,
    second: sp.Symbol,
) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(
        value, first, second, domain=sp.QQ
    ).total_degree())


def _diagonal_inverse(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    return sp.expand(sum(
        coefficient * p**i * q**j / (5 + 2 * i + 3 * j)
        for (i, j), coefficient in sp.Poly(
            value, p, q, domain=sp.QQ
        ).terms()
    ))


def _lowering(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        -sp.Rational(2, 3) * sp.diff(value, p)
        - p * sp.diff(value, q) / 3
    )


def _operator(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        5 * value
        + (2 * p - sp.Rational(2, 3)) * sp.diff(value, p)
        + (3 * q - p / 3) * sp.diff(value, q)
    )


def _operator_inverse(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    term = _diagonal_inverse(value, p, q)
    result = term
    while term != 0:
        term = sp.expand(
            -_diagonal_inverse(_lowering(term, p, q), p, q)
        )
        result = sp.expand(result + term)
    assert sp.expand(_operator(result, p, q) - value) == 0
    return result


def _root_rectifier(
    density: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    w: sp.Symbol,
) -> dict[str, sp.Expr]:
    inverse = _operator_inverse(density, p, q)
    inverse_at_origin = inverse.subs({p: 0, q: 0})
    b = sp.expand(inverse + 2 * inverse_at_origin)
    c = sp.expand(-3 * inverse_at_origin)
    a = sp.expand(-(b + (1 - 2 * p) * c) / 3)
    root_field = sp.expand(a + b * w + c * w**2)
    target_p = sp.expand(
        (6 * p * b + 7 * p * c - 9 * q * c - 2 * b - 2 * c)
        / 3
    )
    target_q = sp.expand(
        (
            2 * p**2 * c
            - p * b
            - p * c
            + 9 * q * b
            + 3 * q * c
        )
        / 3
    )
    return {
        "q": inverse,
        "q0": inverse_at_origin,
        "a": a,
        "b": b,
        "c": c,
        "f": root_field,
        "ZP": target_p,
        "ZQ": target_q,
    }


def run(*, maximum_order: int = 8) -> dict[str, object]:
    if maximum_order < 1:
        raise ValueError("at least the first determinant defect is needed")

    p, q, w = sp.symbols("P Q W")
    v, t = sp.symbols("v t")
    gamma = 1 - sp.Rational(3, 2) * v + t
    source_w = (1 + v) * gamma
    seed_p = sp.expand(gamma + 2 * source_w - 3 * source_w**2)
    seed_q = sp.expand(
        gamma * source_w + source_w**2 - 2 * source_w**3
    )
    cubic = w**3 - w**2 + p * w - q
    cubic_derivative = sp.diff(cubic, w)

    rows: list[dict[str, object]] = []
    for order in range(1, maximum_order + 1):
        density_monomials = [
            p**i * q**j
            for i in range(order // 2 + 1)
            for j in range(order // 3 + 1)
            if 4 * i + 6 * j <= 2 * order
        ]
        for density in density_monomials:
            data = _root_rectifier(density, p, q, w)
            trace = sp.expand(
                3 * data["a"] + data["b"] + (1 - 2 * p) * data["c"]
            )
            assert trace == 0

            root_remainder = sp.rem(
                sp.Poly(
                    cubic_derivative * data["f"]
                    + data["ZP"] * w
                    - data["ZQ"],
                    w,
                    domain=sp.QQ.frac_field(p, q),
                ),
                sp.Poly(
                    cubic, w, domain=sp.QQ.frac_field(p, q)
                ),
            ).as_expr()
            assert sp.expand(root_remainder) == 0

            target_divergence = sp.expand(
                sp.diff(data["ZP"], p) + sp.diff(data["ZQ"], q)
            )
            assert sp.expand(target_divergence - density) == 0
            assert sp.expand(
                (data["b"] + data["c"]).subs({p: 0, q: 0})
            ) == 0

            substituted = {
                p: seed_p,
                q: seed_q,
                w: source_w,
            }
            source_gamma = sp.expand(
                data["ZP"].subs(substituted)
                + (-2 + 6 * source_w) * data["f"].subs(substituted)
            )
            source_v = sp.cancel(
                (
                    gamma * data["f"].subs(substituted)
                    - source_w * source_gamma
                )
                / gamma**2
            )
            source_t = sp.cancel(
                source_gamma + sp.Rational(3, 2) * source_v
            )
            assert all(
                not ({v, t} & sp.denom(value).free_symbols)
                for value in (source_v, source_t)
            )

            source_p_response = sp.expand(
                source_v * sp.diff(seed_p, v)
                + source_t * sp.diff(seed_p, t)
            )
            source_q_response = sp.expand(
                source_v * sp.diff(seed_q, v)
                + source_t * sp.diff(seed_q, t)
            )
            assert sp.expand(
                source_p_response - data["ZP"].subs({
                    p: seed_p, q: seed_q
                })
            ) == 0
            assert sp.expand(
                source_q_response - data["ZQ"].subs({
                    p: seed_p, q: seed_q
                })
            ) == 0

            assert source_v.subs({v: 0, t: 0}) == 0
            t_axis = sp.Poly(
                source_t.subs(t, 0), v, domain=sp.QQ
            )
            assert t_axis.coeff_monomial(1) == 0
            assert t_axis.coeff_monomial(v) == 0

            source_degrees = [
                _ordinary_degree(value, v, t)
                for value in (source_v, source_t)
            ]
            target_degrees = [
                _filtered_degree(data["ZP"], p, q),
                _filtered_degree(data["ZQ"], p, q),
            ]
            assert max(source_degrees) <= 2 * order + 1
            assert target_degrees[0] <= 2 * order + 4
            assert target_degrees[1] <= 2 * order + 6
            rows.append({
                "order": order,
                "density": str(density),
                "source_degrees": source_degrees,
                "target_filtered_degrees": target_degrees,
            })

    first = _root_rectifier(
        sp.Rational(5, 12), p, q, w
    )
    assert first["a"] == -p / 6
    assert first["b"] == sp.Rational(1, 4)
    assert first["c"] == -sp.Rational(1, 4)
    assert first["ZP"] == -p / 12 + 3 * q / 4
    assert first["ZQ"] == -p**2 / 6 + q / 2

    # The family quartic derivative is the exact exceptional-divisor
    # identity used in the uncorrected source-bound proof.
    s = sp.Symbol("s")
    mu = 3 * (s - 4) / (2 * (s - 6))
    lam = -(s - 4) / 4
    family_p_polynomial = (
        (2 + s / 2) * w
        + (-3 - 3 * s / 2) * w**2
        + s * w**3
    )
    family_p = sp.cancel(
        lam / mu * (gamma + family_p_polynomial)
    )
    quartic_derivative = sp.expand(
        3 * w**2
        - 4 * s * w**3 / (2 * (s + 2))
        - 2 * (s + 4) * w / (2 * (s + 2))
        - 12 * family_p / ((s - 6) * (s + 2))
    )
    assert sp.factor(
        quartic_derivative - 2 * gamma / (s + 2)
    ) == 0

    receipt_text = json.dumps(rows, sort_keys=True)
    return {
        "schema": "axiompack.jacobian_root_volume_rectifier.v1",
        "maximum_parameter_order": maximum_order,
        "complete_filtered_monomial_cases": len(rows),
        "operator": (
            "A=5+(2P-2/3)d/dP+(3Q-P/3)d/dQ"
        ),
        "inverse": (
            "A^-1=sum_k(-A0^-1 N)^k A0^-1; finite because "
            "N strictly lowers weights (4,6)"
        ),
        "root_trace_and_descent_checked": True,
        "divergence_right_inverse_checked": True,
        "source_contact_and_lift_ideals_checked": True,
        "source_slope_two_checked": True,
        "first_rectifier": {
            "a": str(first["a"]),
            "b": str(first["b"]),
            "c": str(first["c"]),
            "ZP": str(first["ZP"]),
            "ZQ": str(first["ZQ"]),
        },
        "quartic_derivative_identity": "R_s'(W)=2*gamma/(s+2)",
        "case_receipt_sha256": hashlib.sha256(
            receipt_text.encode("utf-8")
        ).hexdigest(),
        "claim_boundary": (
            "The replay checks the invariant root/divergence/source "
            "lemmas across complete filtered monomial windows. The "
            "all-order determinant recursion and uncorrected source "
            "bound are proved in the accompanying pencil and remain "
            "to be packaged for kernel ratification."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
