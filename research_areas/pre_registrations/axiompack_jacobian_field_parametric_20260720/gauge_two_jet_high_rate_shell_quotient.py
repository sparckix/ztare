#!/usr/bin/env python3
"""Quotient complete high-rate shells along an exact controlled interpolation.

The defect-five comparison rejects one named ``Z`` coordinate.  This replay
asks the coordinate-free finite question: after scaling the complete
controlled target connection by ``lambda``, does any linear functional on a
fixed total-degree source shell remain constant?  Enough exact rational
specializations are included to span the polynomial dependence, and one
additional value is held out.

This is a one-parameter carrier-discovery test.  It does not represent the
complete finite contact fiber and makes no all-order minimax claim.
"""

from __future__ import annotations

from fractions import Fraction
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

from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from gauge_normal_defect_five_causality import (  # noqa: E402
    _source_only_hamiltonian,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredCoupledBlock,
    FilteredCoupledBlockProblem,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    compile_filtered_coupled_blocks,
    compile_filtered_symbol_cokernel,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


def _scale_expression(value: sp.Expr, scalar: Fraction) -> sp.Expr:
    return sp.expand(
        sp.Rational(scalar.numerator, scalar.denominator) * value
    )


def _source_ops(u: sp.Symbol, z: sp.Symbol) -> FormalLieOps[sp.Expr]:
    return FormalLieOps(
        zero=lambda: sp.Integer(0),
        add=lambda left, right: sp.expand(left + right),
        scale=_scale_expression,
        bracket=lambda left, right: sp.cancel(
            (
                sp.diff(left, z) * sp.diff(right, u)
                - sp.diff(left, u) * sp.diff(right, z)
            )
            / z**2
        ),
    )


def _target_ops(p: sp.Symbol, q: sp.Symbol) -> FormalLieOps[sp.Expr]:
    return FormalLieOps(
        zero=lambda: sp.Integer(0),
        add=lambda left, right: sp.expand(left + right),
        scale=_scale_expression,
        bracket=lambda left, right: sp.expand(
            sp.diff(left, p) * sp.diff(right, q)
            - sp.diff(left, q) * sp.diff(right, p)
        ),
    )


def _controlled_target(
    parameter: sp.Symbol,
    family_p: sp.Expr,
    family_q: sp.Expr,
) -> sp.Expr:
    coefficient_p3 = sp.factor(
        96
        * (parameter**2 - 12 * parameter + 16)
        / (
            (parameter - 6) ** 3
            * (parameter - 4) ** 2
            * (parameter + 4) ** 2
        )
    )
    coefficient_pq = sp.factor(
        2
        * parameter
        / ((parameter - 4) * (parameter + 4))
    )
    return sp.cancel(
        coefficient_p3 * family_p**3
        + coefficient_pq * family_p * family_q
        - family_q**2 / 4
    )


def _series_coefficients(
    expression: sp.Expr,
    parameter: sp.Symbol,
    maximum_order: int,
) -> list[sp.Expr]:
    expansion = sp.series(
        expression, parameter, 0, maximum_order
    ).removeO().expand()
    return [
        sp.expand(expansion.coeff(parameter, order))
        for order in range(maximum_order)
    ]


def _coordinates_at_degree(
    polynomial: sp.Poly,
    degree: int,
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({
        (u_exponent, z_exponent)
        for (u_exponent, z_exponent, _lambda_exponent), coefficient
        in polynomial.terms()
        if coefficient != 0 and u_exponent + z_exponent == degree
    }))


def _specialized_coordinates(
    polynomial: sp.Poly,
    coordinates: tuple[tuple[int, int], ...],
    value: int,
) -> dict[tuple[int, int], sp.Rational]:
    u, z, interpolation = polynomial.gens
    specialized_polynomial = sp.Poly(
        polynomial.as_expr().subs(interpolation, value),
        u,
        z,
        domain=sp.QQ,
    )
    result: dict[tuple[int, int], sp.Rational] = {}
    for coordinate in coordinates:
        specialized = sp.Rational(
            specialized_polynomial.coeff_monomial(
                u ** coordinate[0] * z ** coordinate[1]
            )
        )
        if specialized:
            result[coordinate] = specialized
    return result


def _compile_degree(
    *,
    logarithm: sp.Expr,
    order: int,
    degree: int,
    u: sp.Symbol,
    z: sp.Symbol,
    interpolation: sp.Symbol,
) -> dict[str, object]:
    polynomial = sp.Poly(logarithm, u, z, interpolation, domain=sp.QQ)
    coordinates = _coordinates_at_degree(polynomial, degree)
    coordinate_names = {
        coordinate: f"u{coordinate[0]}z{coordinate[1]}"
        for coordinate in coordinates
    }
    baseline = _specialized_coordinates(polynomial, coordinates, 0)
    sample_values = tuple(range(1, order + 2))
    heldout_value = order + 2

    def variation(value: int) -> dict[str, sp.Rational]:
        specialized = _specialized_coordinates(
            polynomial, coordinates, value
        )
        return {
            coordinate_names[coordinate]: (
                specialized.get(coordinate, sp.Integer(0))
                - baseline.get(coordinate, sp.Integer(0))
            )
            for coordinate in coordinates
            if (
                specialized.get(coordinate, sp.Integer(0))
                - baseline.get(coordinate, sp.Integer(0))
            ) != 0
        }

    def compile_values(
        values: tuple[int, ...],
        *,
        reverse_basis: bool,
    ):
        ordered_coordinates = (
            tuple(reversed(coordinates)) if reverse_basis else coordinates
        )
        return compile_filtered_symbol_cokernel(
            FilteredSymbolCokernelProblem(
                name=(
                    f"two_jet_interpolation_order_{order}_degree_{degree}"
                    f"_{'reversed' if reverse_basis else 'canonical'}"
                ),
                domain_basis=tuple(
                    FilteredBasisVector(f"lambda_{value}", degree)
                    for value in values
                ),
                domain_relations=(),
                codomain_basis=tuple(
                    FilteredBasisVector(
                        coordinate_names[coordinate], degree
                    )
                    for coordinate in ordered_coordinates
                ),
                codomain_relations=(),
                maps=(
                    FilteredSymbolMap(
                        "controlled_interpolation_variation",
                        0,
                        {
                            f"lambda_{value}": variation(value)
                            for value in values
                        },
                    ),
                ),
                distinguished={
                    coordinate_names[coordinate]: coefficient
                    for coordinate, coefficient in baseline.items()
                },
            )
        )

    training = compile_values(sample_values, reverse_basis=False)
    permuted = compile_values(sample_values, reverse_basis=True)
    extended = compile_values(
        (*sample_values, heldout_value), reverse_basis=False
    )
    assert training.cokernel_dimension == permuted.cokernel_dimension
    assert training.distinguished_survives == permuted.distinguished_survives
    assert extended.cokernel_dimension == training.cokernel_dimension
    assert extended.symbol_image_rank == training.symbol_image_rank

    return {
        "hamiltonian_degree": degree,
        "source_derivation_degree": degree - 3,
        "coordinate_count": len(coordinates),
        "sample_values": list(sample_values),
        "heldout_value": heldout_value,
        "variation_rank": training.symbol_image_rank,
        "cokernel_dimension": training.cokernel_dimension,
        "source_only_shell_survives": training.distinguished_survives,
        "heldout_rank_unchanged": True,
        "basis_permutation_unchanged": True,
        "constraint_sha256": training.constraint_matrix_sha256,
        "decomposition_column_count": len(
            training.decomposition_by_column
        ),
    }


def _compile_coupled_order(
    *,
    logarithm: sp.Expr,
    order: int,
    degrees: list[int],
    u: sp.Symbol,
    z: sp.Symbol,
    interpolation: sp.Symbol,
) -> dict[str, object]:
    polynomial = sp.Poly(logarithm, u, z, interpolation, domain=sp.QQ)
    sample_values = tuple(range(1, order + 2))
    heldout_value = order + 2
    retained_coordinates = {
        (u_exponent, z_exponent)
        for (u_exponent, z_exponent, _lambda_exponent), coefficient
        in polynomial.terms()
        if coefficient != 0
        and u_exponent + z_exponent in degrees
    }
    interpolation_degree = max(
        lambda_exponent
        for (u_exponent, z_exponent, lambda_exponent), coefficient
        in polynomial.terms()
        if coefficient != 0
        and (u_exponent, z_exponent) in retained_coordinates
    )
    vandermonde = sp.Matrix([
        [value**power for power in range(1, interpolation_degree + 1)]
        for value in sample_values
    ])
    assert vandermonde.rank() == interpolation_degree

    def compile_values(
        values: tuple[int, ...],
        *,
        reverse_blocks: bool,
    ):
        ordered_degrees = (
            list(reversed(degrees)) if reverse_blocks else degrees
        )
        blocks = []
        for degree in ordered_degrees:
            coordinates = _coordinates_at_degree(polynomial, degree)
            if reverse_blocks:
                coordinates = tuple(reversed(coordinates))
            coordinate_names = {
                coordinate: f"u{coordinate[0]}z{coordinate[1]}"
                for coordinate in coordinates
            }
            baseline = _specialized_coordinates(
                polynomial, coordinates, 0
            )
            columns = {}
            for value in values:
                specialized = _specialized_coordinates(
                    polynomial, coordinates, value
                )
                columns[f"lambda_{value}"] = {
                    coordinate_names[coordinate]: difference
                    for coordinate in coordinates
                    if (
                        difference := (
                            specialized.get(coordinate, sp.Integer(0))
                            - baseline.get(coordinate, sp.Integer(0))
                        )
                    ) != 0
                }
            blocks.append(
                FilteredCoupledBlock(
                    name=f"degree_{degree}",
                    codomain_basis=tuple(
                        FilteredBasisVector(
                            coordinate_names[coordinate], degree
                        )
                        for coordinate in coordinates
                    ),
                    codomain_relations=(),
                    symbol_map=FilteredSymbolMap(
                        f"degree_{degree}_variation",
                        degree,
                        columns,
                    ),
                    distinguished={
                        coordinate_names[coordinate]: coefficient
                        for coordinate, coefficient in baseline.items()
                    },
                )
            )
        return compile_filtered_coupled_blocks(
            FilteredCoupledBlockProblem(
                name=(
                    f"two_jet_coupled_order_{order}_"
                    f"{'reversed' if reverse_blocks else 'canonical'}"
                ),
                domain_basis=tuple(
                    FilteredBasisVector(f"lambda_{value}", 0)
                    for value in values
                ),
                domain_relations=(),
                blocks=tuple(blocks),
            )
        )

    training = compile_values(sample_values, reverse_blocks=False)
    permuted = compile_values(sample_values, reverse_blocks=True)
    extended = compile_values(
        (*sample_values, heldout_value), reverse_blocks=False
    )
    assert training.distinguished_survives
    assert permuted.distinguished_survives
    assert extended.distinguished_survives
    assert training.common_control_rank == permuted.common_control_rank
    assert extended.common_control_rank == training.common_control_rank
    assert training.common_control_rank == 4
    return {
        "sample_values": list(sample_values),
        "heldout_value": heldout_value,
        "ambient_dimension": training.ambient_dimension,
        "interpolation_polynomial_degree": interpolation_degree,
        "vandermonde_rank": vandermonde.rank(),
        "all_rational_specializations_spanned": True,
        "common_control_rank": training.common_control_rank,
        "augmented_rank": training.constraint_rank + 1,
        "coupled_cokernel_dimension": (
            training.coupled_cokernel_dimension
        ),
        "source_only_bundle_survives": True,
        "distinguished_pairing": training.distinguished_pairing,
        "witness_coordinate_count": len(
            training.witness_by_block_basis
        ),
        "witness": training.to_dict()["witness_by_block_basis"],
        "heldout_rank_unchanged": True,
        "block_and_basis_permutation_unchanged": True,
        "constraint_sha256": training.constraint_matrix_sha256,
    }


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("the held-out shell comparison requires order six")

    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    interpolation = sp.Symbol("lambda")
    controlled_target = _controlled_target(parameter, family_p, family_q)
    source_velocity = _series_coefficients(
        sp.cancel(source_only + 8 * interpolation * controlled_target),
        parameter,
        maximum_order,
    )
    source_logarithm = magnus_from_velocity(
        source_velocity,
        maximum_order,
        _source_ops(u, z),
        VelocityPlacement.RIGHT_MULTIPLY,
    )

    target_p, target_q = sp.symbols("P Q")
    target_connection = _controlled_target(
        parameter, target_p, target_q
    )
    target_velocity = [
        interpolation * coefficient
        for coefficient in _series_coefficients(
            target_connection, parameter, maximum_order
        )
    ]
    target_logarithm = magnus_from_velocity(
        target_velocity,
        maximum_order,
        _target_ops(target_p, target_q),
        VelocityPlacement.LEFT_MULTIPLY,
    )

    orders = []
    for order in (5, 6):
        polynomial = sp.Poly(
            source_logarithm[order], u, z, interpolation, domain=sp.QQ
        )
        degrees = sorted({
            u_exponent + z_exponent
            for (u_exponent, z_exponent, _lambda_exponent), coefficient
            in polynomial.terms()
            if coefficient != 0
            and u_exponent + z_exponent - 3 >= 2 * order
        }, reverse=True)
        compiled = [
            _compile_degree(
                logarithm=source_logarithm[order],
                order=order,
                degree=degree,
                u=u,
                z=z,
                interpolation=interpolation,
            )
            for degree in degrees
        ]
        assert compiled
        assert all(row["cokernel_dimension"] == 0 for row in compiled)
        assert all(
            not row["source_only_shell_survives"] for row in compiled
        )
        coupled = _compile_coupled_order(
            logarithm=source_logarithm[order],
            order=order,
            degrees=degrees,
            u=u,
            z=z,
            interpolation=interpolation,
        )
        target_degree = max(
            (
                sum(exponents[:2])
                for exponents, coefficient in sp.Poly(
                    target_logarithm[order],
                    target_p,
                    target_q,
                    interpolation,
                ).terms()
                if coefficient != 0
            ),
            default=-1,
        )
        target_derivation_degree = (
            target_degree - 1 if target_degree >= 0 else -1
        )
        assert target_derivation_degree < 2 * order
        orders.append({
            "logarithmic_order": order,
            "retained_degree_range": [min(degrees), max(degrees)],
            "retained_grade_count": len(degrees),
            "all_high_rate_grade_cokernels_zero": True,
            "target_hamiltonian_degree": target_degree,
            "target_derivation_degree": target_derivation_degree,
            "target_below_rate_two_at_this_order": True,
            "coupled_cross_grade": coupled,
            "grades": compiled,
        })

    return {
        "schema": (
            "axiompack.jacobian_two_jet_high_rate_shell_quotient.v1"
        ),
        "interpolation": (
            "L_source_only + 8*lambda*K_controlled(P_s,Q_s)"
        ),
        "orders": orders,
        "fixed_grade_linear_carrier_survives": False,
        "coupled_cross_grade_carrier_survives": True,
        "new_information": (
            "Every fixed grade is spanned by exact interpolation "
            "variations, but a normalized functional survives when all "
            "grades share one common variation vector. Cross-grade "
            "compatibility, rather than a named terminal, is the first "
            "surviving carrier on this controlled subfamily."
        ),
        "claim_boundary": (
            "Exact one-parameter interpolation and logarithmic orders five "
            "and six only. The coupled certificate is linear in the affine "
            "span of sampled connections; the complete finite contact "
            "fiber, nonlinear parameter compatibility, charged-surplus "
            "recurrence, and all-order tail remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
