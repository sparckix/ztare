#!/usr/bin/env python3
"""Exact quadratic contact-zero control closure on coupled source shells."""

from __future__ import annotations

from fractions import Fraction
import itertools
import json
from pathlib import Path
import sys
from typing import Callable, TypeAlias

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _add as _sparse_add,
    _bracket as _sparse_bracket,
    _scale as _sparse_scale,
    _to_sparse,
)
from gauge_moving_pullback_normal_semigroup import _exact_family  # noqa: E402
from gauge_normal_defect_five_causality import (  # noqa: E402
    _source_only_hamiltonian,
)
from gauge_q2c_contact_zero_product_grade import (  # noqa: E402
    _canonical_contact_zero_symbol,
)
from gauge_two_jet_high_rate_shell_quotient import (  # noqa: E402
    _controlled_target,
    _series_coefficients,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredCoupledBlock,
    FilteredCoupledBlockProblem,
    FilteredSymbolMap,
    compile_filtered_coupled_blocks,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    VelocityPlacement,
    magnus_from_velocity,
)


ControlMonomial: TypeAlias = tuple[int, ...]
ControlPolynomial: TypeAlias = dict[ControlMonomial, SparseHamiltonian]


def _control_add(
    left: ControlPolynomial,
    right: ControlPolynomial,
) -> ControlPolynomial:
    result = {key: dict(value) for key, value in left.items()}
    for key, value in right.items():
        combined = _sparse_add(result.get(key, {}), value)
        if combined:
            result[key] = combined
        else:
            result.pop(key, None)
    return result


def _control_scale(
    value: ControlPolynomial,
    scalar: Fraction,
) -> ControlPolynomial:
    return {
        key: scaled
        for key, coefficient in value.items()
        if (scaled := _sparse_scale(coefficient, scalar))
    }


def _control_bracket(
    left: ControlPolynomial,
    right: ControlPolynomial,
    spatial_bracket: Callable[
        [SparseHamiltonian, SparseHamiltonian], SparseHamiltonian
    ],
    retain_monomial: Callable[[ControlMonomial], bool],
) -> ControlPolynomial:
    result: ControlPolynomial = {}
    for left_key, left_value in left.items():
        for right_key, right_value in right.items():
            key = tuple(sorted((*left_key, *right_key)))
            if not retain_monomial(key):
                continue
            bracket = spatial_bracket(left_value, right_value)
            if not bracket:
                continue
            combined = _sparse_add(result.get(key, {}), bracket)
            if combined:
                result[key] = combined
            else:
                result.pop(key, None)
    return result


def _control_ops(
    spatial_bracket: Callable[
        [SparseHamiltonian, SparseHamiltonian], SparseHamiltonian
    ],
    retain_monomial: Callable[[ControlMonomial], bool] = (
        lambda monomial: len(monomial) <= 2
    ),
) -> FormalLieOps[ControlPolynomial]:
    return FormalLieOps(
        zero=dict,
        add=_control_add,
        scale=_control_scale,
        bracket=lambda left, right: _control_bracket(
            left, right, spatial_bracket, retain_monomial
        ),
    )


def _control_monomials(indices: tuple[int, ...]) -> tuple[ControlMonomial, ...]:
    return tuple((index,) for index in indices) + tuple(
        pair for pair in itertools.combinations_with_replacement(indices, 2)
    )


def _monomial_name(
    monomial: ControlMonomial,
    labels: tuple[str, ...],
) -> str:
    return "*".join(labels[index] for index in monomial)


def _velocity_polynomial(
    *,
    baseline: list[sp.Expr],
    directions: list[list[sp.Expr]],
    first: sp.Symbol,
    second: sp.Symbol,
) -> list[ControlPolynomial]:
    velocity: list[ControlPolynomial] = []
    for order, baseline_coefficient in enumerate(baseline):
        coefficient: ControlPolynomial = {}
        baseline_coefficient = sp.cancel(baseline_coefficient)
        baseline_denominator = baseline_coefficient.as_numer_denom()[1]
        assert baseline_denominator.free_symbols.isdisjoint({first, second})
        baseline_sparse = _to_sparse(baseline_coefficient, first, second)
        if baseline_sparse:
            coefficient[()] = baseline_sparse
        for index, direction in enumerate(directions):
            direction_coefficient = sp.cancel(direction[order])
            direction_denominator = direction_coefficient.as_numer_denom()[1]
            assert direction_denominator.free_symbols.isdisjoint(
                {first, second}
            )
            direction_sparse = _to_sparse(
                direction_coefficient, first, second
            )
            if direction_sparse:
                coefficient[(index,)] = direction_sparse
        velocity.append(coefficient)
    return velocity


def _compile_order(
    *,
    logarithm: ControlPolynomial,
    order: int,
    labels: tuple[str, ...],
    included_indices: tuple[int, ...],
    all_indices: tuple[int, ...],
    reverse: bool,
):
    minimum_degree = 2 * order + 3
    coordinates_by_degree: dict[int, set[tuple[int, int]]] = {}
    for coefficient in logarithm.values():
        for exponent, value in coefficient.items():
            degree = sum(exponent)
            if value != 0 and degree >= minimum_degree:
                coordinates_by_degree.setdefault(degree, set()).add(exponent)

    domain_monomials = _control_monomials(included_indices)
    if reverse:
        domain_monomials = tuple(reversed(domain_monomials))
    degrees = sorted(coordinates_by_degree, reverse=True)
    if reverse:
        degrees = list(reversed(degrees))
    blocks = []
    for degree in degrees:
        coordinates = tuple(sorted(coordinates_by_degree[degree]))
        if reverse:
            coordinates = tuple(reversed(coordinates))
        coordinate_names = {
            coordinate: f"u{coordinate[0]}z{coordinate[1]}"
            for coordinate in coordinates
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
                    f"degree_{degree}_quadratic_control",
                    degree,
                    {
                        _monomial_name(monomial, labels): {
                            coordinate_names[coordinate]: value
                            for coordinate in coordinates
                            if (
                                value := logarithm.get(monomial, {}).get(
                                    coordinate, sp.Integer(0)
                                )
                            ) != 0
                        }
                        for monomial in domain_monomials
                    },
                ),
                distinguished={
                    coordinate_names[coordinate]: value
                    for coordinate in coordinates
                    if (
                        value := logarithm.get((), {}).get(
                            coordinate, sp.Integer(0)
                        )
                    ) != 0
                },
            )
        )
    certificate = compile_filtered_coupled_blocks(
        FilteredCoupledBlockProblem(
            name=(
                f"quadratic_contact_zero_order_{order}_"
                f"{'reversed' if reverse else 'canonical'}"
            ),
            domain_basis=tuple(
                FilteredBasisVector(
                    _monomial_name(monomial, labels), 0
                )
                for monomial in domain_monomials
            ),
            domain_relations=(),
            blocks=tuple(blocks),
        )
    )
    # The held-out computation owns the common ambient basis.  Training maps
    # are a typed subset of that domain rather than a smaller spatial window.
    assert set(included_indices).issubset(all_indices)
    return certificate


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("quadratic closure requires logarithmic order six")

    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    target_p, target_q = sp.symbols("P Q")
    labels = (
        "controlled",
        "weight_5",
        "weight_6",
        "weight_7",
        "weight_8",
        "weight_9",
        "weight_10",
        "weight_11",
        "weight_12",
        "weight_13",
    )

    source_baseline = _series_coefficients(
        source_only, parameter, maximum_order
    )
    controlled_source = _series_coefficients(
        8 * _controlled_target(parameter, family_p, family_q),
        parameter,
        maximum_order,
    )
    source_directions = [controlled_source]
    target_directions = [
        _series_coefficients(
            _controlled_target(parameter, target_p, target_q),
            parameter,
            maximum_order,
        )
    ]
    for weight in range(5, 14):
        target_symbol = sp.expand(
            _canonical_contact_zero_symbol(weight, target_p, target_q)
        )
        moving_symbol = target_symbol.subs({
            target_p: family_p,
            target_q: family_q,
        })
        source_directions.append(
            _series_coefficients(
                8 * parameter * moving_symbol,
                parameter,
                maximum_order,
            )
        )
        target_directions.append(
            _series_coefficients(
                parameter * target_symbol,
                parameter,
                maximum_order,
            )
        )

    source_velocity = _velocity_polynomial(
        baseline=source_baseline,
        directions=source_directions,
        first=u,
        second=z,
    )
    source_logarithm = magnus_from_velocity(
        source_velocity,
        maximum_order,
        _control_ops(
            lambda left, right: _sparse_bracket(left, right, 2)
        ),
        VelocityPlacement.RIGHT_MULTIPLY,
    )

    target_zero = [sp.Integer(0) for _ in range(maximum_order)]
    target_velocity = _velocity_polynomial(
        baseline=target_zero,
        directions=target_directions,
        first=target_p,
        second=target_q,
    )
    target_logarithm = magnus_from_velocity(
        target_velocity,
        maximum_order,
        _control_ops(
            lambda left, right: _sparse_scale(
                _sparse_bracket(left, right, 0), Fraction(-1)
            )
        ),
        VelocityPlacement.LEFT_MULTIPLY,
    )

    training_indices = tuple(range(8))
    heldout_indices = tuple(range(10))
    rows = []
    for order in (5, 6):
        training = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            included_indices=training_indices,
            all_indices=heldout_indices,
            reverse=False,
        )
        training_reversed = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            included_indices=training_indices,
            all_indices=heldout_indices,
            reverse=True,
        )
        heldout = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            included_indices=heldout_indices,
            all_indices=heldout_indices,
            reverse=False,
        )
        assert training.distinguished_survives
        assert training_reversed.distinguished_survives
        assert heldout.distinguished_survives
        assert (
            training.common_control_rank
            == training_reversed.common_control_rank
        )

        maximum_target_derivation_degree = max(
            (
                sum(exponent) - 1
                for monomial, coefficient
                in target_logarithm[order].items()
                if monomial
                for exponent, value in coefficient.items()
                if value != 0
            ),
            default=-1,
        )
        assert maximum_target_derivation_degree < 2 * order
        rows.append({
            "logarithmic_order": order,
            "ambient_dimension": heldout.ambient_dimension,
            "training_control_monomial_count": len(
                _control_monomials(training_indices)
            ),
            "training_control_rank": training.common_control_rank,
            "training_augmented_rank": training.constraint_rank + 1,
            "heldout_control_monomial_count": len(
                _control_monomials(heldout_indices)
            ),
            "heldout_control_rank": heldout.common_control_rank,
            "heldout_augmented_rank": heldout.constraint_rank + 1,
            "source_only_bundle_survives_training": True,
            "source_only_bundle_survives_heldout": True,
            "basis_and_block_permutation_unchanged": True,
            "maximum_target_derivation_degree": (
                maximum_target_derivation_degree
            ),
            "all_quadratic_columns_below_rate_two_on_target": True,
            "training_witness_coordinate_count": len(
                training.witness_by_block_basis
            ),
            "heldout_witness_coordinate_count": len(
                heldout.witness_by_block_basis
            ),
            "training_constraint_sha256": (
                training.constraint_matrix_sha256
            ),
            "heldout_constraint_sha256": heldout.constraint_matrix_sha256,
        })

    return {
        "schema": (
            "axiompack.jacobian_contact_zero_quadratic_"
            "coupled_shell.v1"
        ),
        "control_labels": list(labels),
        "control_degree_cutoff": 2,
        "quadratic_columns_treated_as_independent_relaxation": True,
        "orders": rows,
        "quadratic_relaxation_reaches_source_bundle": False,
        "new_information": (
            "The coupled high-rate bundle survives the complete independent "
            "span of every linear and quadratic Taylor coefficient in the "
            "controlled direction and canonical row-one contact-zero "
            "directions through held-out weight 13."
        ),
        "claim_boundary": (
            "Exact control-degree-two Taylor closure at logarithmic orders "
            "five and six. Cubic coefficients, independent higher parameter "
            "rows, all cusp weights, and all-order propagation remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
