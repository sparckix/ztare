#!/usr/bin/env python3
"""Exact Q^2*C audit against the complete contact-zero algebra.

This adapter stress-tests the product-grade separation at the two places
where a contact-zero backbone can still change the finite Q^2*C prefix:

* a row-one symbol enters the cost-five lambda^2 equation; and
* a cost-two symbol is resonant with the zero-grade source letter A.

The canonical one-symbol-per-weight basis describes the contact-zero
associated grade.  The complete lift algebra

    QQ + (P**3, P*Q, Q**2).

also contains positive powers of the cusp equation ``C``.  This adapter runs
both categories without conflating them.  Contact zero leaves a
high-transverse coordinate.  The first positive-contact counterattack cancels
the entire cost-two source Hamiltonian exactly, and the next nonzero quotient
occurs at cost three.  No all-order tail conclusion is made.
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket,
    _ops,
)
from gauge_cone_q2c_terminal_recurrence import (  # noqa: E402
    L_THREE,
    L_TWO,
    _c_seed_column,
    _known_forward_velocity,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_q2c_contact_zero_product_grade import (  # noqa: E402
    _canonical_contact_zero_symbol,
    _grade,
    _source_data,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    compile_filtered_symbol_cokernel,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    velocity_from_magnus,
)


Exponent = tuple[int, int]


def _source_symbol(
    weight: int,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> dict[Exponent, sp.Expr]:
    target = _canonical_contact_zero_symbol(weight, p, q)
    return _to_sparse(
        sp.expand(8 * target.subs({p: p0, q: q0})),
        u,
        z,
    )


def _complete_lift_target_monomials(
    maximum_weight: int,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
) -> dict[str, sp.Expr]:
    """Return every lift-compatible monomial through one cusp weight."""

    result = {}
    for q_exponent in range(maximum_weight // 3 + 1):
        for p_exponent in range(maximum_weight // 2 + 1):
            weight = 2 * p_exponent + 3 * q_exponent
            if weight < 5 or weight > maximum_weight:
                continue
            in_lift_ideal = (
                p_exponent >= 3
                or (p_exponent >= 1 and q_exponent >= 1)
                or q_exponent >= 2
            )
            if not in_lift_ideal:
                continue
            result[f"P{p_exponent}Q{q_exponent}"] = (
                p**p_exponent * q**q_exponent
            )
    return result


def _complete_lift_columns(
    maximum_weight: int,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
    project: Callable[[Exponent], bool] | None = None,
) -> dict[str, dict[Exponent, sp.Expr]]:
    columns = {}
    for name, target in _complete_lift_target_monomials(
        maximum_weight,
        p=p,
        q=q,
    ).items():
        source = _to_sparse(
            sp.expand(8 * target.subs({p: p0, q: q0})),
            u,
            z,
        )
        columns[name] = {
            exponent: coefficient
            for exponent, coefficient in source.items()
            if project is None or project(exponent)
        }
    return columns


def _fixed_cost_cokernel(
    *,
    name: str,
    columns: dict[str, dict[Exponent, sp.Expr]],
    distinguished: dict[Exponent, sp.Expr],
    negative_control: bool = False,
) -> dict[str, object]:
    exponents = sorted(
        set(distinguished)
        | {
            exponent
            for column in columns.values()
            for exponent in column
        }
    )
    names = {
        exponent: f"u{exponent[0]}z{exponent[1]}"
        for exponent in exponents
    }
    domain_columns = {
        column_name: {
            names[exponent]: str(coefficient)
            for exponent, coefficient in column.items()
            if coefficient != 0
        }
        for column_name, column in columns.items()
    }
    if negative_control:
        domain_columns["synthetic_direct_control"] = {
            names[exponent]: str(coefficient)
            for exponent, coefficient in distinguished.items()
            if coefficient != 0
        }
    problem = FilteredSymbolCokernelProblem(
        name=name,
        domain_basis=tuple(
            FilteredBasisVector(column_name, 0)
            for column_name in domain_columns
        ),
        domain_relations=(),
        codomain_basis=tuple(
            FilteredBasisVector(names[exponent], 0)
            for exponent in exponents
        ),
        codomain_relations=(),
        maps=(
            FilteredSymbolMap(
                "fixed_cost_source_image",
                0,
                domain_columns,
            ),
        ),
        distinguished={
            names[exponent]: str(coefficient)
            for exponent, coefficient in distinguished.items()
            if coefficient != 0
        },
    )
    return compile_filtered_symbol_cokernel(problem).to_dict()


def _difference_two_cancellation(
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> tuple[dict[int, sp.Expr], dict[Exponent, sp.Expr]]:
    weights = list(range(5, 13))
    source_rows = [
        {
            exponent: coefficient
            for exponent, coefficient in _source_symbol(
                weight,
                p=p,
                q=q,
                p0=p0,
                q0=q0,
                u=u,
                z=z,
            ).items()
            if exponent[1] - exponent[0] == 2
        }
        for weight in weights
    ]
    exponents = sorted(
        {
            exponent
            for row in source_rows
            for exponent in row
        }
        | {
            exponent
            for exponent in L_TWO
            if exponent[1] - exponent[0] == 2
        }
    )
    matrix = sp.Matrix([
        [row.get(exponent, 0) for row in source_rows]
        for exponent in exponents
    ])
    target = sp.Matrix([
        -L_TWO.get(exponent, 0) for exponent in exponents
    ])
    assert matrix.rank() == matrix.row_join(target).rank() == len(weights)
    solution = tuple(next(iter(sp.linsolve((matrix, target)))))
    expected = (
        sp.Rational(1, 135),
        -sp.Rational(1, 810),
        -sp.Rational(11, 270),
        sp.Rational(13, 1620),
        sp.Rational(13, 135),
        -sp.Rational(1, 54),
        -sp.Rational(1, 12),
        sp.Rational(2, 135),
    )
    assert solution == expected
    coefficients = dict(zip(weights, solution, strict=True))
    modified = dict(L_TWO)
    for weight, scalar in coefficients.items():
        for exponent, coefficient in _source_symbol(
            weight,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        ).items():
            modified[exponent] = sp.factor(
                modified.get(exponent, 0) + scalar * coefficient
            )
    modified = {
        exponent: coefficient
        for exponent, coefficient in modified.items()
        if coefficient != 0
    }
    assert all(
        exponent[1] - exponent[0] != 2
        for exponent in modified
    )
    return coefficients, modified


def _high_transverse_certificate(
    maximum_weight: int,
    *,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> dict[str, object]:
    columns = {}
    for weight in range(5, maximum_weight + 1):
        columns[f"weight_{weight}"] = {
            exponent: coefficient
            for exponent, coefficient in _source_symbol(
                weight,
                p=p,
                q=q,
                p0=p0,
                q0=q0,
                u=u,
                z=z,
            ).items()
            if exponent[1] - exponent[0] >= 3
            and sum(exponent) >= 12
        }
    distinguished = {
        exponent: coefficient
        for exponent, coefficient in L_TWO.items()
        if exponent[1] - exponent[0] >= 3
        and sum(exponent) >= 12
    }
    return _fixed_cost_cokernel(
        name=f"q2c_high_transverse_weight_{maximum_weight}",
        columns=columns,
        distinguished=distinguished,
    )


def _forward_adjoint_checks(
    *,
    leader_coefficient: sp.Expr,
    weight: int,
) -> list[dict[str, object]]:
    beta, lam = sp.symbols("beta lambda")
    a_coefficient = L_TWO[(8, 10)]
    rows = []
    for backbone_cost in (1, 2, 3, 4):
        for depth in range(1, 5):
            cost = backbone_cost + 2 * depth
            logarithm = [{} for _ in range(cost + 1)]
            backbone = {(weight, weight): beta * leader_coefficient}
            zero_grade = {(8, 10): lam * a_coefficient}
            if backbone_cost == 2:
                logarithm[2] = {
                    **backbone,
                    (8, 10): (
                        backbone.get((8, 10), 0)
                        + zero_grade[(8, 10)]
                    ),
                }
            else:
                logarithm[backbone_cost] = backbone
                logarithm[2] = zero_grade
            velocity = velocity_from_magnus(
                logarithm,
                cost,
                _ops(2),
                VelocityPlacement.RIGHT_MULTIPLY,
            )
            exponent = (weight + 7 * depth, weight + 7 * depth)
            actual = sp.factor(
                sp.expand(velocity[cost - 1].get(exponent, 0))
                .coeff(beta, 1)
                .coeff(lam, depth)
            )
            adjoint = sp.factor(
                leader_coefficient
                * a_coefficient**depth
                * 2**depth
                * sp.prod(weight + 7 * index for index in range(depth))
            )
            expected = sp.factor(
                sp.Rational(
                    (-1) ** depth * (backbone_cost - 2),
                    factorial(depth + 1),
                )
                * adjoint
            )
            assert actual == expected
            rows.append({
                "backbone_cost": backbone_cost,
                "adjoint_depth": depth,
                "output_cost": cost,
                "output_exponent": list(exponent),
                "coefficient": str(actual),
                "formula_matches": True,
                "resonant_zero": backbone_cost == 2,
            })
    return rows


def run() -> dict[str, object]:
    data = _source_data()
    u, z = data["symbols"]
    p, q = data["target_symbols"]
    p0 = data["P0"]
    q0 = data["Q0"]
    beta, lam = sp.symbols("beta lambda")

    # The first canonical weight that changes the original cost-five
    # terminal coefficient is weight six.
    weight = 6
    source_weight_six = _source_symbol(
        weight,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    logarithm = [{} for _ in range(6)]
    logarithm[1] = {
        exponent: beta * coefficient
        for exponent, coefficient in source_weight_six.items()
    }
    logarithm[2] = {
        exponent: lam * coefficient
        for exponent, coefficient in L_TWO.items()
    }
    logarithm[3] = {
        exponent: lam * coefficient
        for exponent, coefficient in L_THREE.items()
    }
    known = _known_forward_velocity(logarithm, 5)
    lambda_squared = {
        exponent: sp.factor(sp.expand(coefficient).coeff(lam, 2))
        for exponent, coefficient in known.items()
        if sp.expand(coefficient).coeff(lam, 2) != 0
    }
    terminal_exponent = (12, 16)
    terminal_coefficient = sp.factor(lambda_squared[terminal_exponent])
    assert sp.factor(
        terminal_coefficient
        - sp.Rational(3, 16384) * (563076 * beta + 283)
    ) == 0
    cancellation = -sp.Rational(283, 563076)
    assert terminal_coefficient.subs(beta, cancellation) == 0
    cancelled_residual = {
        exponent: sp.factor(coefficient.subs(beta, cancellation))
        for exponent, coefficient in lambda_squared.items()
        if sp.factor(coefficient.subs(beta, cancellation)) != 0
    }
    surplus_exponent = (20, 20)
    surplus_coefficient = cancelled_residual[surplus_exponent]
    assert surplus_coefficient == -sp.Rational(893997, 512524288)

    current_columns = {}
    for offset in (-2, -1, 0):
        column = _c_seed_column(5, 14 + offset)
        assert column is not None
        current_columns[f"current_offset_{offset}"] = column[1]
    surplus_certificate = _fixed_cost_cokernel(
        name="q2c_weight_six_cancelled_terminal_surplus",
        columns=current_columns,
        distinguished={surplus_exponent: surplus_coefficient},
    )
    assert surplus_certificate["distinguished_survives"]
    surplus_negative = _fixed_cost_cokernel(
        name="q2c_weight_six_surplus_direct_control",
        columns=current_columns,
        distinguished={surplus_exponent: surplus_coefficient},
        negative_control=True,
    )
    assert not surplus_negative["distinguished_survives"]

    difference_two_coefficients, resonant_l_two = (
        _difference_two_cancellation(
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        )
    )
    training = _high_transverse_certificate(
        24,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    heldout = _high_transverse_certificate(
        32,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    assert training["distinguished_survives"]
    assert heldout["distinguished_survives"]
    assert (
        training["witness_by_codomain_basis"]
        == heldout["witness_by_codomain_basis"]
    )
    expected_witness = [
        {"basis": "u0z12", "coefficient": "-72299315200/897"},
        {"basis": "u1z11", "coefficient": "-61931520/299"},
        {"basis": "u1z12", "coefficient": "6326190080/897"},
        {"basis": "u2z10", "coefficient": "2351104/207"},
        {"basis": "u2z11", "coefficient": "-12257280/299"},
        {"basis": "u2z12", "coefficient": "-903741440/2691"},
        {"basis": "u3z10", "coefficient": "-119392/69"},
        {"basis": "u3z11", "coefficient": "16378880/2691"},
        {"basis": "u3z9", "coefficient": "152"},
        {"basis": "u4z10", "coefficient": "192"},
        {"basis": "u4z8", "coefficient": "-16/3"},
        {"basis": "u4z9", "coefficient": "-20"},
        {"basis": "u5z9", "coefficient": "50/9"},
        {"basis": "u6z9", "coefficient": "-8/3"},
    ]
    assert training["witness_by_codomain_basis"] == expected_witness

    complete_weight_twelve = _complete_lift_columns(
        12,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
    )
    complete_l_two = _fixed_cost_cokernel(
        name="q2c_complete_lift_cost_two_weight_12",
        columns=complete_weight_twelve,
        distinguished=L_TWO,
    )
    assert not complete_l_two["distinguished_survives"]
    expected_decomposition = [
        {
            "column": "symbol:fixed_cost_source_image:P2Q2",
            "coefficient": "-1/2",
        },
        {
            "column": "symbol:fixed_cost_source_image:P3Q2",
            "coefficient": "2",
        },
        {
            "column": "symbol:fixed_cost_source_image:P0Q3",
            "coefficient": "2",
        },
        {
            "column": "symbol:fixed_cost_source_image:P1Q3",
            "coefficient": "-9",
        },
        {
            "column": "symbol:fixed_cost_source_image:P0Q4",
            "coefficient": "27/2",
        },
    ]
    assert complete_l_two["decomposition_by_column"] == (
        expected_decomposition
    )
    l_two_target_preimage = sp.factor(
        -sp.Rational(1, 2) * p**2 * q**2
        + 2 * p**3 * q**2
        + 2 * q**3
        - 9 * p * q**3
        + sp.Rational(27, 2) * q**4
    )
    l_two_expression = sum(
        coefficient * u**exponent[0] * z**exponent[1]
        for exponent, coefficient in L_TWO.items()
    )
    assert sp.expand(
        8 * l_two_target_preimage.subs({p: p0, q: q0})
        - l_two_expression
    ) == 0
    cancelling_target = sp.factor(-l_two_target_preimage)

    high_project = lambda exponent: (
        exponent[1] - exponent[0] >= 3
        and sum(exponent) >= 12
    )
    complete_high_columns = _complete_lift_columns(
        12,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        u=u,
        z=z,
        project=high_project,
    )
    complete_high = _fixed_cost_cokernel(
        name="q2c_positive_contact_high_transverse_weight_12",
        columns=complete_high_columns,
        distinguished={
            exponent: coefficient
            for exponent, coefficient in L_TWO.items()
            if high_project(exponent)
        },
    )
    assert not complete_high["distinguished_survives"]

    complete_cost_three_training = _fixed_cost_cokernel(
        name="q2c_complete_lift_cost_three_weight_22",
        columns=_complete_lift_columns(
            22,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        ),
        distinguished=L_THREE,
    )
    complete_cost_three_heldout = _fixed_cost_cokernel(
        name="q2c_complete_lift_cost_three_weight_30",
        columns=_complete_lift_columns(
            30,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        ),
        distinguished=L_THREE,
    )
    assert complete_cost_three_training["distinguished_survives"]
    assert complete_cost_three_heldout["distinguished_survives"]
    assert (
        complete_cost_three_training["witness_by_codomain_basis"]
        == complete_cost_three_heldout["witness_by_codomain_basis"]
    )

    leader_coefficient = source_weight_six[(6, 6)]
    forward_rows = _forward_adjoint_checks(
        leader_coefficient=leader_coefficient,
        weight=weight,
    )

    return {
        "schema": "axiompack.jacobian_q2c_backbone_resonance.v2",
        "row_one_terminal_cancellation": {
            "backbone_symbol": "P^3",
            "backbone_weight": 6,
            "terminal_exponent": list(terminal_exponent),
            "terminal_coefficient": str(terminal_coefficient),
            "cancelling_coefficient": str(cancellation),
            "uniform_terminal_coefficient_survival": False,
            "surplus_exponent": list(surplus_exponent),
            "surplus_grade": list(_grade(surplus_exponent, 5)),
            "surplus_coefficient": str(surplus_coefficient),
            "surplus_current_cokernel": surplus_certificate,
            "matched_direct_control_kills": True,
        },
        "nonresonant_forward_adjoint": {
            "A": "-9*u^8*z^10/64 at cost 2",
            "backbone_leader": "c_w*u^w*z^w at cost j",
            "adjoint_exponent": "(w+7*k,w+7*k)",
            "adjoint_multiplier": (
                "c_w*(-9/64)^k*2^k*product_(i=0)^(k-1)(w+7*i)"
            ),
            "right_forward_dexp_scalar": (
                "(-1)^k*(j-2)/(k+1)!"
            ),
            "resonant_cost": 2,
            "checked_rows": forward_rows,
        },
        "canonical_weight_reduction_audit": {
            "complete_difference_two_cancellation": {
                str(weight): str(coefficient)
                for weight, coefficient
                in difference_two_coefficients.items()
            },
            "modified_L2_has_no_difference_two_monomial": True,
            "modified_L2_term_count": len(resonant_l_two),
            "high_transverse_region": (
                "z_exponent-u_exponent>=3 and total_degree>=12"
            ),
            "training_weight_cap": 24,
            "heldout_weight_cap": 32,
            "training_certificate": training,
            "heldout_witness_matches": True,
            "canonical_associated_grade_completeness": (
                "the witness uses z-exponent at most 12; every canonical "
                "weight w>=25 pullback is divisible by z^13"
            ),
            "conclusion": (
                "the discriminant-reduced one-symbol-per-weight category "
                "leaves a high-transverse coordinate"
            ),
        },
        "positive_contact_cost_two_counterattack": {
            "target_lift_algebra": "QQ + (P^3,PQ,Q^2)",
            "all_monomials_through_weight": 12,
            "source_hamiltonian_certificate": complete_l_two,
            "target_preimage_of_L2": str(l_two_target_preimage),
            "cancelling_target_coefficient": str(cancelling_target),
            "exact_source_roundtrip": True,
            "high_transverse_certificate": complete_high,
            "contact_zero_high_transverse_class_survives": True,
            "positive_contact_direction_kills_it": True,
            "category_boundary": (
                "the additional monomial directions combine to Q^2*C/2, "
                "which has positive C-adic valuation and vanishes in the "
                "contact-zero associated grade"
            ),
        },
        "static_cost_three_quotient_without_lower_row_replay": {
            "training_weight_cap": 22,
            "heldout_weight_cap": 30,
            "training_certificate": complete_cost_three_training,
            "heldout_witness_matches": True,
            "all_weight_completeness": (
                "the witness reads z-exponent at most 9; a target monomial "
                "P^a Q^b pulls back with z-valuation at least a+2*b, and "
                "a+2*b<=9 implies cusp weight 2*a+3*b<=18"
            ),
            "cost_three_class_survives_same_cost_lift_span": True,
            "complete_repair_transport_included": False,
            "interpretation": (
                "This is a static same-cost negative control. It does not "
                "carry the lower cost-two logarithm change through the "
                "coupled source/target connection."
            ),
        },
        "claim_boundary": (
            "The original Q^2*C terminal coefficient is not invariant: "
            "a rational weight-six row-one backbone cancels it. The move "
            "leaves the contact-zero high-transverse class. The exact five-"
            "monomial counterattack is Q^2*C/2, so it belongs to positive "
            "contact and does not alter the contact-zero associated-grade "
            "statement. The preimage Q^2*C/2 is also exactly the target "
            "logarithm generated by the delayed Q^2*C velocity. Its "
            "negative removes that same prefix. The static cost-three "
            "class survives same-cost lift columns only when this lower-"
            "row change is not replayed; it is not a post-repair coupled "
            "quotient."
        ),
        "next_residual": (
            "Classify the least nonzero positive-contact coefficient over "
            "an arbitrary moving contact-zero backbone. The negative of "
            "that coefficient's own target logarithm removes the prefix "
            "and cannot be counted as an independent later cancellation."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
