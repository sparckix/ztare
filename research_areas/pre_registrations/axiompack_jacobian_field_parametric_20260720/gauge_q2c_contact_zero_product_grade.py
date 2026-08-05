#!/usr/bin/env python3
"""Product-grade symbol of the complete contact-zero Jacobian backbone.

The contact-zero associated grade of the lift algebra

    QQ + (P**3, P*Q, Q**2)

has one canonical cusp symbol in every weight w >= 5.  This adapter pulls
those symbols through the exact seed map, checks their weighted-volume source
Hamiltonians, and compiles every monomial grade in finite windows with the
substrate-neutral Filtered Obstruction Compiler.  The finite compiler replay
is paired with an all-weight support argument; window stabilization is not
used as a completeness claim.
"""

from __future__ import annotations

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

from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    compile_filtered_symbol_cokernel,
)


Exponent = tuple[int, int]
Grade = tuple[int, int]


def _canonical_contact_zero_symbol(
    weight: int,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    if weight < 5:
        raise ValueError("a nonconstant lift-compatible symbol has weight >= 5")
    if weight % 2 == 0:
        return p ** (weight // 2)
    return p ** ((weight - 3) // 2) * q


def _grade(exponent: Exponent, cost: int) -> Grade:
    return (
        2 * exponent[0] - 7 * cost - 2,
        2 * exponent[1] - 7 * cost - 6,
    )


def _source_data() -> dict[str, object]:
    data = _family_jets(0)
    family_v, family_t = data["symbols"]
    u, z = sp.symbols("u z")
    substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p0 = sp.factor(data["P"][0].subs(substitution))
    q0 = sp.factor(data["Q"][0].subs(substitution))
    jacobian = sp.Matrix([
        [sp.diff(p0, u), sp.diff(p0, z)],
        [sp.diff(q0, u), sp.diff(q0, z)],
    ])
    assert sp.factor(jacobian.det() + z**2 / 8) == 0
    return {
        "symbols": (u, z),
        "target_symbols": sp.symbols("P Q"),
        "P0": p0,
        "Q0": q0,
        "jacobian": jacobian,
    }


def _verify_source_hamiltonian(
    target: sp.Expr,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    jacobian: sp.Matrix,
    u: sp.Symbol,
    z: sp.Symbol,
) -> sp.Expr:
    target_field = sp.Matrix([
        sp.diff(target, q),
        -sp.diff(target, p),
    ]).subs({p: p0, q: q0})
    source_field = -jacobian.inv() * target_field
    source_field = sp.Matrix([
        sp.factor(source_field[0]),
        sp.factor(source_field[1]),
    ])
    assert all(
        not component.as_numer_denom()[1].has(u, z)
        for component in source_field
    )
    source_hamiltonian = sp.factor(8 * target.subs({p: p0, q: q0}))
    replay = sp.Matrix([
        sp.diff(source_hamiltonian, z) / z**2,
        -sp.diff(source_hamiltonian, u) / z**2,
    ])
    assert all(
        sp.factor(replay[index] - source_field[index]) == 0
        for index in range(2)
    )
    return source_hamiltonian


def _window_certificate(
    maximum_cost: int,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    domain_rows: list[tuple[str, Grade]] = []
    grade_names: dict[Grade, str] = {(0, 0): "terminal_zero_grade"}
    rows = []
    for cost in range(1, maximum_cost + 1):
        maximum_rate_bounded_weight = (7 * cost + 2) // 2
        for weight in range(5, maximum_rate_bounded_weight + 1):
            target = _canonical_contact_zero_symbol(weight, p, q)
            source = sp.Poly(
                sp.expand(8 * target.subs({p: p0, q: q0})),
                u,
                z,
                domain=sp.QQ,
            )
            top_grade = _grade((weight, weight), cost)
            monomial_grades = []
            for exponent, coefficient in source.terms():
                if coefficient == 0:
                    continue
                grade = _grade(exponent, cost)
                grade_names.setdefault(
                    grade,
                    f"grade_{grade[0]}_{grade[1]}",
                )
                name = (
                    f"cost_{cost}_weight_{weight}_"
                    f"u_{exponent[0]}_z_{exponent[1]}"
                )
                domain_rows.append((name, grade))
                monomial_grades.append(grade)
            assert monomial_grades
            assert all(grade != (0, 0) for grade in monomial_grades)
            assert max(grade[0] for grade in monomial_grades) == top_grade[0]
            assert max(grade[1] for grade in monomial_grades) == top_grade[1]
            assert top_grade[0] <= 0
            assert top_grade[1] <= -4
            rows.append({
                "cost": cost,
                "weight": weight,
                "top_grade": list(top_grade),
                "monomial_count": len(monomial_grades),
                "zero_grade_absent": True,
            })

    domain_basis = tuple(
        FilteredBasisVector(name, grade) for name, grade in domain_rows
    )
    codomain_basis = tuple(
        FilteredBasisVector(name, grade)
        for grade, name in sorted(grade_names.items())
    )
    columns = {
        name: {grade_names[grade]: 1}
        for name, grade in domain_rows
    }
    problem = FilteredSymbolCokernelProblem(
        name=f"q2c_contact_zero_product_grade_cost_{maximum_cost}",
        domain_basis=domain_basis,
        domain_relations=(),
        codomain_basis=codomain_basis,
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "associated_grade_source_support",
                (0, 0),
                columns,
            ),
        ),
        distinguished={"terminal_zero_grade": 1},
    )
    certificate = compile_filtered_symbol_cokernel(problem)
    assert certificate.cokernel_dimension == 1
    assert certificate.distinguished_survives

    # A matched synthetic zero-grade source must kill the distinguished node.
    negative_domain = (
        *domain_basis,
        FilteredBasisVector("synthetic_zero_grade", (0, 0)),
    )
    negative_columns = {
        **columns,
        "synthetic_zero_grade": {"terminal_zero_grade": 1},
    }
    negative = compile_filtered_symbol_cokernel(
        FilteredSymbolCokernelProblem(
            name=f"q2c_contact_zero_zero_grade_control_{maximum_cost}",
            domain_basis=negative_domain,
            domain_relations=(),
            codomain_basis=codomain_basis,
            codomain_relations=(),
            maps=(
                FilteredSymbolMap(
                    "associated_grade_source_support_with_control",
                    (0, 0),
                    negative_columns,
                ),
            ),
            distinguished={"terminal_zero_grade": 1},
        )
    )
    assert not negative.distinguished_survives
    return (
        {
            "maximum_cost": maximum_cost,
            "domain_dimension": certificate.domain_dimension,
            "codomain_dimension": certificate.codomain_dimension,
            "cokernel_dimension": certificate.cokernel_dimension,
            "zero_grade_survives": certificate.distinguished_survives,
            "zero_grade_pairing": certificate.distinguished_pairing,
            "constraint_matrix_sha256": certificate.constraint_matrix_sha256,
            "matched_zero_grade_control_kills": True,
        },
        rows,
    )


def run(
    training_maximum_cost: int = 8,
    heldout_maximum_cost: int = 12,
) -> dict[str, object]:
    if training_maximum_cost < 2:
        raise ValueError("training_maximum_cost must be at least two")
    if heldout_maximum_cost <= training_maximum_cost:
        raise ValueError("heldout window must strictly extend training")

    source_data = _source_data()
    u, z = source_data["symbols"]
    p, q = source_data["target_symbols"]
    p0 = source_data["P0"]
    q0 = source_data["Q0"]
    jacobian = source_data["jacobian"]

    symbol_rows = []
    for weight in range(5, 18):
        target = _canonical_contact_zero_symbol(weight, p, q)
        source = _verify_source_hamiltonian(
            target,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            jacobian=jacobian,
            u=u,
            z=z,
        )
        polynomial = sp.Poly(sp.expand(source), u, z, domain=sp.QQ)
        top_coefficient = polynomial.coeff_monomial(u**weight * z**weight)
        expected_top = (
            8 * (-sp.Rational(3, 4)) ** (weight // 2)
            if weight % 2 == 0
            else 8
            * (-sp.Rational(3, 4)) ** ((weight - 3) // 2)
            * (-sp.Rational(1, 4))
        )
        assert sp.factor(top_coefficient - expected_top) == 0
        assert all(
            exponent[0] <= weight and exponent[1] <= weight
            for exponent, coefficient in polynomial.terms()
            if coefficient != 0
        )
        symbol_rows.append({
            "weight": weight,
            "target_symbol": str(target),
            "source_hamiltonian_degree": int(polynomial.total_degree()),
            "source_excess": 2 * weight - 4,
            "diagonal_leader": [weight, weight],
            "diagonal_coefficient": str(top_coefficient),
            "support_componentwise_at_most_weight": True,
            "weighted_volume_roundtrip": True,
        })

    # Product grades add under the density-z^2 Hamiltonian bracket.
    a, b, c, d, first_cost, second_cost = sp.symbols(
        "a b c d q1 q2", integer=True
    )
    bracket_exponent = (a + c - 1, b + d - 3)
    bracket_grade = (
        2 * bracket_exponent[0] - 7 * (first_cost + second_cost) - 2,
        2 * bracket_exponent[1] - 7 * (first_cost + second_cost) - 6,
    )
    summed_grade = (
        (2 * a - 7 * first_cost - 2)
        + (2 * c - 7 * second_cost - 2),
        (2 * b - 7 * first_cost - 6)
        + (2 * d - 7 * second_cost - 6),
    )
    assert all(
        sp.expand(left - right) == 0
        for left, right in zip(bracket_grade, summed_grade, strict=True)
    )

    training, training_rows = _window_certificate(
        training_maximum_cost,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    heldout, heldout_rows = _window_certificate(
        heldout_maximum_cost,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    assert heldout_rows[: len(training_rows)] == training_rows

    return {
        "schema": "axiompack.jacobian_q2c_contact_zero_product_grade.v1",
        "seed_pullback": {
            "P0": str(p0),
            "Q0": str(q0),
            "jacobian_determinant": str(sp.factor(jacobian.det())),
            "source_hamiltonian_identity": "h_H=8*H(P0,Q0)",
        },
        "complete_contact_zero_associated_grade": {
            "target_lift_algebra": "QQ + (P^3,P*Q,Q^2)",
            "cusp_relation": "4*P^3+27*Q^2=0",
            "canonical_even_symbol": "t_(2*a)=P^a, a>=3",
            "canonical_odd_symbol": "t_(2*a+3)=P^a*Q, a>=1",
            "weights": "every integer w>=5, one-dimensional per weight",
        },
        "terminal_product_filtration": {
            "grade": "G(a,b;q)=(2*a-7*q-2,2*b-7*q-6)",
            "bracket_additive": True,
            "weight_w_leader_grade": "(2*w-7*j-2,2*w-7*j-6)",
            "componentwise_nonpositive_condition": "2*w<=7*j+2",
            "all_other_source_exponents": "a<=w and b<=w",
            "zero_grade_exclusion": (
                "under 2*w<=7*j+2 every source monomial has second "
                "grade <= -4, hence no contact-zero symbol reaches (0,0)"
            ),
        },
        "symbol_rows": symbol_rows,
        "compiler_training": training,
        "compiler_heldout": heldout,
        "all_weight_certificate": {
            "finite_window_stabilization_used": False,
            "reason": (
                "canonical weight-w support is componentwise bounded by "
                "(w,w), and its diagonal coefficient is nonzero"
            ),
            "conclusion": (
                "every componentwise-nonpositive contact-zero backbone "
                "letter is strictly negative in the second terminal grade"
            ),
        },
        "claim_boundary": (
            "This is a complete associated-grade separation theorem for "
            "the contact-zero lift algebra. It proves that rate-bounded "
            "backbone letters cannot act on the Q^2*C terminal quotient. "
            "It does not yet dispose of finite positive-grade backbone "
            "letters or prove the coupled all-order minimax dichotomy."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
