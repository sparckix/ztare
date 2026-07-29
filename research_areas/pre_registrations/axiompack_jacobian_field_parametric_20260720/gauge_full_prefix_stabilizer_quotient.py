#!/usr/bin/env python3
"""Exact full-prefix quotient at the seed cusp.

The replay uses a generic finite polynomial prefix, constructs its target
normal lift, reduces the paired tangent remainder by the C-stabilizer, and
builds the weighted-volume source completion.
"""
from __future__ import annotations

import json

import sympy as sp


def _degree(value: sp.Expr, *variables: sp.Symbol) -> int:
    value = sp.expand(value)
    if value == 0:
        return -1
    return int(sp.Poly(value, *variables).total_degree())


def _restriction(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    r: sp.Symbol,
) -> sp.Expr:
    return sp.expand(value.subs({p: -3 * r**2, q: -2 * r**3}))


def _minimal_seed_monomial(
    exponent: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Minimal ordinary-degree target representative of r^exponent."""
    if exponent == 0:
        return sp.Integer(1)
    candidates: list[tuple[int, int]] = []
    for q_power in range(exponent // 3 + 1):
        remainder = exponent - 3 * q_power
        if remainder >= 0 and remainder % 2 == 0:
            candidates.append((remainder // 2, q_power))
    if not candidates:
        raise ValueError(f"{exponent} is outside <2,3>")
    p_power, q_power = min(
        candidates,
        key=lambda powers: (sum(powers), powers[0]),
    )
    coefficient = (-3) ** p_power * (-2) ** q_power
    return sp.Rational(1, coefficient) * p**p_power * q**q_power


def _lift_seed_polynomial(
    value: sp.Expr,
    r: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
    minimum_exponent: int,
) -> sp.Expr:
    polynomial = sp.Poly(sp.expand(value), r)
    result = sp.Integer(0)
    for (exponent,), coefficient in polynomial.terms():
        if exponent < minimum_exponent:
            raise ValueError(
                f"term r^{exponent} is below {minimum_exponent}"
            )
        result += coefficient * _minimal_seed_monomial(
            exponent, p, q
        )
    return sp.expand(result)


def _target_lift(
    hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> bool:
    first = sp.diff(hamiltonian, q)
    second = -sp.diff(hamiltonian, p)
    first_ok = sp.expand(first).subs({p: 0, q: 0}) == 0
    second_on_q_zero = sp.Poly(
        sp.expand(second.subs(q, 0)), p
    )
    second_ok = (
        second_on_q_zero.coeff_monomial(1) == 0
        and second_on_q_zero.coeff_monomial(p) == 0
    )
    return bool(first_ok and second_ok)


def _normal_lift(
    normal: sp.Expr,
    r: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[sp.Expr, sp.Expr]:
    """Return K and k=K(f) with k'/(6r)=normal."""
    k = sp.integrate(6 * r * normal, r)
    hamiltonian = _lift_seed_polynomial(k, r, p, q, 5)
    return sp.expand(hamiltonian), sp.expand(k)


def _weighted_source_lift(
    tangent: sp.Expr,
    r: sp.Symbol,
    v: sp.Symbol,
    g: sp.Symbol,
) -> tuple[sp.Expr, tuple[sp.Expr, sp.Expr]]:
    """Lift tangent u(r), assumed divisible by r, via a source potential."""
    if sp.expand(tangent) == 0:
        return sp.Integer(0), (sp.Integer(0), sp.Integer(0))
    polynomial = sp.Poly(sp.expand(tangent), r)
    potential = sp.Integer(0)
    for (exponent,), coefficient in polynomial.terms():
        if exponent < 1:
            raise ValueError("a constant tangent has no polynomial lift")
        potential += (
            coefficient
            * sp.Rational(1, 2)
            * v**exponent
            * g ** (exponent + 2)
        )
    field = (
        sp.cancel(sp.diff(potential, g) / g**2),
        sp.cancel(-sp.diff(potential, v) / g**2),
    )
    assert all(
        not ({v, g} & sp.denom(item).free_symbols)
        for item in field
    )
    return sp.expand(potential), tuple(sp.expand(item) for item in field)


def _strict_source_lift(
    field: tuple[sp.Expr, sp.Expr],
    v: sp.Symbol,
    g: sp.Symbol,
) -> bool:
    """Check U_V∈(V,T), U_T∈(T,V²), with G=T-3V/2."""
    t = sp.Symbol("T")
    first_vt = sp.expand(
        field[0].subs(g, t - sp.Rational(3, 2) * v)
    )
    second_vt = sp.expand(
        (field[1] + sp.Rational(3, 2) * field[0]).subs(
            g, t - sp.Rational(3, 2) * v
        )
    )
    first_ok = first_vt.subs({v: 0, t: 0}) == 0
    second_on_t_zero = sp.Poly(second_vt.subs(t, 0), v)
    second_ok = (
        second_on_t_zero.coeff_monomial(1) == 0
        and second_on_t_zero.coeff_monomial(v) == 0
    )
    return bool(first_ok and second_ok)


def _bracket(
    left: tuple[sp.Expr, sp.Expr],
    right: tuple[sp.Expr, sp.Expr],
    variables: tuple[sp.Symbol, sp.Symbol],
) -> tuple[sp.Expr, sp.Expr]:
    return tuple(
        sp.expand(
            sum(
                left[index] * sp.diff(right[component], variables[index])
                - right[index] * sp.diff(left[component], variables[index])
                for index in range(2)
            )
        )
        for component in range(2)
    )


def _decompose(
    first: sp.Expr,
    second: sp.Expr,
    r: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    g: sp.Symbol,
) -> dict[str, sp.Expr | tuple[sp.Expr, sp.Expr]]:
    normal = sp.expand(second - r * first)
    hamiltonian, potential_restriction = _normal_lift(
        normal, r, p, q
    )
    c = 4 * p**3 + 27 * q**2

    target_first = _restriction(
        sp.diff(hamiltonian, q), p, q, r
    )
    raw_tangent = sp.expand(first - target_first)
    assert sp.rem(raw_tangent, r**2, domain=sp.QQ.frac_field(
        *sorted(raw_tangent.free_symbols - {r}, key=str)
    )) == 0

    # X_(C L)(f) has first component -108 r^3 L(f).  Choose L(f)
    # to cancel all tangent terms except the r^2 and r^4 quotient basis.
    stabilizer_restriction = sp.Integer(0)
    for (exponent,), coefficient in sp.Poly(raw_tangent, r).terms():
        if exponent == 3 or exponent >= 5:
            stabilizer_restriction += (
                -coefficient / 108 * r ** (exponent - 3)
            )
    stabilizer_lift = _lift_seed_polynomial(
        stabilizer_restriction, r, p, q, 0
    )
    reduced_hamiltonian = sp.expand(
        hamiltonian + c * stabilizer_lift
    )
    reduced_target_first = _restriction(
        sp.diff(reduced_hamiltonian, q), p, q, r
    )
    reduced_tangent = sp.expand(first - reduced_target_first)
    assert all(
        exponent in {2, 4}
        for (exponent,), coefficient
        in sp.Poly(reduced_tangent, r).terms()
        if coefficient != 0
    )

    tangent = sp.cancel(-reduced_tangent / (6 * r))
    assert r not in sp.denom(tangent).free_symbols
    source_potential, source_field = _weighted_source_lift(
        tangent, r, v, g
    )
    return {
        "normal": normal,
        "potential_restriction": potential_restriction,
        "raw_hamiltonian": hamiltonian,
        "stabilizer_restriction": stabilizer_restriction,
        "stabilizer_lift": stabilizer_lift,
        "hamiltonian": reduced_hamiltonian,
        "reduced_tangent": reduced_tangent,
        "tangent": tangent,
        "source_potential": source_potential,
        "source_field": source_field,
    }


def run() -> dict[str, object]:
    r, p, q, v, g = sp.symbols("r P Q V G")
    a2, a3, a4, a5, a6, a7 = sp.symbols(
        "a2 a3 a4 a5 a6 a7"
    )
    b3, b4, b5, b6, b7, b8 = sp.symbols(
        "b3 b4 b5 b6 b7 b8"
    )
    unrestricted_first = (
        a2 * r**2
        + a3 * r**3
        + a4 * r**4
        + a5 * r**5
        + a6 * r**6
        + a7 * r**7
    )
    unrestricted_second = (
        b3 * r**3
        + b4 * r**4
        + b5 * r**5
        + b6 * r**6
        + b7 * r**7
        + b8 * r**8
    )
    unrestricted_normal = sp.expand(
        unrestricted_second - r * unrestricted_first
    )
    strict_obstruction = sp.expand(
        5 * a2
        + 3 * sp.Poly(unrestricted_normal, r).coeff_monomial(r**3)
    )
    assert strict_obstruction == 2 * a2 + 3 * b3

    # A generic prefix in the strict paired category satisfies omega=0.
    first = unrestricted_first
    second = sp.expand(
        unrestricted_second.subs(b3, -sp.Rational(2, 3) * a2)
    )
    data = _decompose(first, second, r, p, q, v, g)
    hamiltonian = data["hamiltonian"]
    source_field = data["source_field"]
    tangent = data["tangent"]
    assert isinstance(hamiltonian, sp.Expr)
    assert isinstance(source_field, tuple)
    assert isinstance(tangent, sp.Expr)
    c = 4 * p**3 + 27 * q**2

    assert _restriction(c, p, q, r) == 0
    assert _target_lift(hamiltonian, p, q)
    target = (
        _restriction(sp.diff(hamiltonian, q), p, q, r),
        _restriction(-sp.diff(hamiltonian, p), p, q, r),
    )
    f_prime = (-6 * r, -6 * r**2)
    assert sp.expand(
        target[1] - r * target[0] - data["normal"]
    ) == 0
    assert sp.expand(
        target[0] + f_prime[0] * tangent - first
    ) == 0
    assert sp.expand(
        target[1] + f_prime[1] * tangent - second
    ) == 0

    weighted_divergence = sp.expand(
        sp.diff(g**2 * source_field[0], v)
        + sp.diff(g**2 * source_field[1], g)
    )
    source_r = sp.expand(
        g * source_field[0] + v * source_field[1]
    )
    assert weighted_divergence == 0
    assert sp.expand(
        source_r - tangent.subs(r, v * g)
    ) == 0
    assert max(_degree(item, v, g) for item in source_field) <= 5
    assert _strict_source_lift(source_field, v, g)

    # The omitted scalar is a strict source-lift obstruction.
    obstructed = _decompose(r**2, 0, r, p, q, v, g)
    obstructed_field = obstructed["source_field"]
    assert isinstance(obstructed_field, tuple)
    assert not _strict_source_lift(obstructed_field, v, g)
    obstructed_normal = -r**3
    obstructed_value = sp.expand(
        5 + 3 * sp.Poly(obstructed_normal, r).coeff_monomial(r**3)
    )
    assert obstructed_value == 2

    # The polar source counterexample is recovered exactly.
    polar = _decompose(
        r**3,
        sp.Rational(3, 4) * r**4,
        r,
        p,
        q,
        v,
        g,
    )
    expected_b = -(p**3 + 9 * q**2) / 36
    assert sp.expand(polar["hamiltonian"] - expected_b) == 0
    assert polar["reduced_tangent"] == 0
    assert polar["source_field"] == (0, 0)

    # The relaxed U_1,U_3 remainder is an affine Lie algebra.  Only U_3
    # survives the strict source lift ideals.
    _, u1 = _weighted_source_lift(r, r, v, g)
    _, u3 = _weighted_source_lift(r**3, r, v, g)
    assert not _strict_source_lift(u1, v, g)
    assert _strict_source_lift(u3, v, g)
    assert _bracket(u1, u3, (v, g)) == tuple(
        sp.expand(2 * item) for item in u3
    )

    # The monomial image proves the potential and normal filtration.
    monomial_rows = []
    for exponent in range(5, 16):
        representative = _minimal_seed_monomial(exponent, p, q)
        restriction = _restriction(representative, p, q, r)
        normal = sp.cancel(sp.diff(restriction, r) / (6 * r))
        assert restriction == r**exponent
        assert sp.Poly(normal, r).monoms() == [(exponent - 2,)]
        assert _target_lift(representative, p, q)
        monomial_rows.append({
            "potential_exponent": exponent,
            "normal_exponent": exponent - 2,
            "representative": str(representative),
            "target_degree": _degree(representative, p, q),
            "optimal_degree": (exponent + 2) // 3,
        })
        assert (
            monomial_rows[-1]["target_degree"]
            == monomial_rows[-1]["optimal_degree"]
        )

    return {
        "schema": "axiompack.jacobian_full_prefix_stabilizer_quotient.v1",
        "seed_cusp": {
            "f": ["-3*r^2", "-2*r^3"],
            "C": "4*P^3+27*Q^2",
            "target_lift_space": "Q + (P^3,P*Q,Q^2)",
            "potential_image": "Q + r^5*Q[r]",
            "normal_image": "r^3*Q[r]",
            "stabilizer": "Q + C*Q[P,Q]",
        },
        "paired_obstruction": {
            "relaxed_boundary_coordinates": [
                "a mod r^2",
                "(b-r*a) mod r^3",
            ],
            "relaxed_boundary_quotient": (
                "Q[r]/(r^2) + Q[r]/(r^3)"
            ),
            "strict_source_scalar": (
                "5*[r^2]a + 3*[r^3](b-r*a) "
                "= 2*[r^2]a + 3*[r^3]b"
            ),
            "generic_value": str(strict_obstruction),
            "strict_generic_prefix_substitution": "b3=-2*a2/3",
            "obstructed_example": ["r^2", "0"],
            "obstructed_value": int(obstructed_value),
            "U1_fails_source_lift": True,
            "U3_passes_source_lift": True,
            "relaxed_affine_bracket": "[U1,U3]=2*U3",
        },
        "normal_transfer": {
            "coordinate": "(b-r*a) mod r^3",
            "vanishes_under_target_lift_ideals": True,
            "image": "r^3*Q[r]",
        },
        "generic_prefix": {
            "normal": str(data["normal"]),
            "raw_hamiltonian": str(data["raw_hamiltonian"]),
            "stabilizer_lift": str(data["stabilizer_lift"]),
            "reduced_tangent": str(data["reduced_tangent"]),
            "source_tangent": str(tangent),
            "source_field": [str(item) for item in source_field],
            "source_degree_bound": 5,
            "strict_source_lift": True,
            "contact_identity": True,
        },
        "polar_witness": {
            "motion": ["r^3", "3*r^4/4"],
            "normal": "-r^4/4",
            "hamiltonian": str(polar["hamiltonian"]),
            "source_remainder": [str(item) for item in polar["source_field"]],
            "recovers_campaign_B": True,
        },
        "minimal_target_sections": monomial_rows,
        "verdict": (
            "every finite target-lift-compatible seed-cusp normal class "
            "transfers; full strict paired completion has one scalar low "
            "tangent obstruction, and when it vanishes the stabilizer-"
            "reduced source remainder has degree at most five"
        ),
        "claim_boundary": (
            "the seed quotient does not control moving transverse layers or "
            "the BCH/logarithmic cost of coefficientwise normalization"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
