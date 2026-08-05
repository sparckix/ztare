#!/usr/bin/env python3
"""Complete weighted control dependence through logarithmic order six."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import itertools
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

from gauge_contact_zero_quadratic_coupled_shell import (  # noqa: E402
    ControlMonomial,
    ControlPolynomial,
    _control_ops,
    _monomial_name,
    _velocity_polynomial,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket as _sparse_bracket,
    _scale as _sparse_scale,
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
    VelocityPlacement,
    magnus_from_velocity,
)


@dataclass(frozen=True)
class WeightedControlReplay:
    source_symbols: tuple[sp.Symbol, sp.Symbol]
    target_symbols: tuple[sp.Symbol, sp.Symbol]
    labels: tuple[str, ...]
    costs: tuple[int, ...]
    source_logarithm: list[ControlPolynomial]
    target_logarithm: list[ControlPolynomial]


def _control_cost(
    monomial: ControlMonomial,
    costs: tuple[int, ...],
) -> int:
    return sum(costs[index] for index in monomial)


def _weighted_monomials(
    indices: tuple[int, ...],
    costs: tuple[int, ...],
    maximum_cost: int,
) -> tuple[ControlMonomial, ...]:
    maximum_degree = maximum_cost // min(costs[index] for index in indices)
    result = []
    for degree in range(1, maximum_degree + 1):
        for monomial in itertools.combinations_with_replacement(
            indices, degree
        ):
            if _control_cost(monomial, costs) <= maximum_cost:
                result.append(monomial)
    return tuple(result)


def _compile_order(
    *,
    logarithm: ControlPolynomial,
    order: int,
    labels: tuple[str, ...],
    costs: tuple[int, ...],
    included_indices: tuple[int, ...],
    reverse: bool,
):
    minimum_degree = 2 * order + 3
    coordinates_by_degree: dict[int, set[tuple[int, int]]] = {}
    for coefficient in logarithm.values():
        for exponent, value in coefficient.items():
            degree = sum(exponent)
            if value != 0 and degree >= minimum_degree:
                coordinates_by_degree.setdefault(degree, set()).add(exponent)

    domain_monomials = _weighted_monomials(
        included_indices, costs, order
    )
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
        names = {
            exponent: f"u{exponent[0]}z{exponent[1]}"
            for exponent in coordinates
        }
        blocks.append(
            FilteredCoupledBlock(
                name=f"degree_{degree}",
                codomain_basis=tuple(
                    FilteredBasisVector(names[exponent], degree)
                    for exponent in coordinates
                ),
                codomain_relations=(),
                symbol_map=FilteredSymbolMap(
                    f"degree_{degree}_weighted_complete_control",
                    degree,
                    {
                        _monomial_name(monomial, labels): {
                            names[exponent]: value
                            for exponent in coordinates
                            if (
                                value := logarithm.get(monomial, {}).get(
                                    exponent, sp.Integer(0)
                                )
                            ) != 0
                        }
                        for monomial in domain_monomials
                    },
                ),
                distinguished={
                    names[exponent]: value
                    for exponent in coordinates
                    if (
                        value := logarithm.get((), {}).get(
                            exponent, sp.Integer(0)
                        )
                    ) != 0
                },
            )
        )
    return compile_filtered_coupled_blocks(
        FilteredCoupledBlockProblem(
            name=(
                f"weighted_complete_order_{order}_"
                f"{'reversed' if reverse else 'canonical'}"
            ),
            domain_basis=tuple(
                FilteredBasisVector(_monomial_name(monomial, labels), 0)
                for monomial in domain_monomials
            ),
            domain_relations=(),
            blocks=tuple(blocks),
        )
    )


def _build_weighted_control_replay(
    maximum_order: int,
) -> WeightedControlReplay:
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
    costs = (1, 2, 2, 2, 2, 2, 2, 2, 2, 2)

    source_baseline = _series_coefficients(
        source_only, parameter, maximum_order
    )
    source_directions = [
        _series_coefficients(
            8 * _controlled_target(parameter, family_p, family_q),
            parameter,
            maximum_order,
        )
    ]
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

    retain = lambda monomial: _control_cost(monomial, costs) <= maximum_order
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
            lambda left, right: _sparse_bracket(left, right, 2),
            retain,
        ),
        VelocityPlacement.RIGHT_MULTIPLY,
    )

    target_velocity = _velocity_polynomial(
        baseline=[sp.Integer(0) for _ in range(maximum_order)],
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
            ),
            retain,
        ),
        VelocityPlacement.LEFT_MULTIPLY,
    )

    return WeightedControlReplay(
        source_symbols=(u, z),
        target_symbols=(target_p, target_q),
        labels=labels,
        costs=costs,
        source_logarithm=source_logarithm,
        target_logarithm=target_logarithm,
    )


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("weighted closure requires order six")

    replay = _build_weighted_control_replay(maximum_order)
    labels = replay.labels
    costs = replay.costs
    source_logarithm = replay.source_logarithm
    target_logarithm = replay.target_logarithm

    training_indices = tuple(range(8))
    heldout_indices = tuple(range(10))
    rows = []
    for order in (5, 6):
        training = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            costs=costs,
            included_indices=training_indices,
            reverse=False,
        )
        training_reversed = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            costs=costs,
            included_indices=training_indices,
            reverse=True,
        )
        heldout = _compile_order(
            logarithm=source_logarithm[order],
            order=order,
            labels=labels,
            costs=costs,
            included_indices=heldout_indices,
            reverse=False,
        )
        assert (
            training.common_control_rank
            == training_reversed.common_control_rank
        )
        assert (
            training.distinguished_survives
            == training_reversed.distinguished_survives
        )

        maximum_target_derivation_degree = max(
            (
                sum(exponent) - 1
                for monomial, coefficient
                in target_logarithm[order].items()
                if monomial and _control_cost(monomial, costs) <= order
                for exponent, value in coefficient.items()
                if value != 0
            ),
            default=-1,
        )
        uncharged = maximum_target_derivation_degree < 2 * order
        rows.append({
            "logarithmic_order": order,
            "ambient_dimension": heldout.ambient_dimension,
            "training_control_monomial_count": len(
                _weighted_monomials(training_indices, costs, order)
            ),
            "training_control_rank": training.common_control_rank,
            "training_augmented_rank": (
                training.constraint_rank
                + (1 if training.distinguished_survives else 0)
            ),
            "heldout_control_monomial_count": len(
                _weighted_monomials(heldout_indices, costs, order)
            ),
            "heldout_control_rank": heldout.common_control_rank,
            "heldout_augmented_rank": (
                heldout.constraint_rank
                + (1 if heldout.distinguished_survives else 0)
            ),
            "source_only_bundle_survives_training": (
                training.distinguished_survives
            ),
            "source_only_bundle_survives_heldout": (
                heldout.distinguished_survives
            ),
            "basis_and_block_permutation_unchanged": True,
            "maximum_target_derivation_degree": (
                maximum_target_derivation_degree
            ),
            "all_weighted_columns_below_rate_two_on_target": uncharged,
            "training_witness_coordinate_count": len(
                training.witness_by_block_basis
            ),
            "heldout_witness_coordinate_count": len(
                heldout.witness_by_block_basis
            ),
            "training_decomposition": training.to_dict()[
                "decomposition_by_column"
            ],
            "heldout_decomposition": heldout.to_dict()[
                "decomposition_by_column"
            ],
            "training_constraint_sha256": (
                training.constraint_matrix_sha256
            ),
            "heldout_constraint_sha256": heldout.constraint_matrix_sha256,
        })

    return {
        "schema": (
            "axiompack.jacobian_contact_zero_weighted_complete_"
            "coupled_shell.v1"
        ),
        "control_labels": list(labels),
        "control_costs": list(costs),
        "weighted_cutoff": maximum_order,
        "weighted_control_monomials_treated_as_independent_relaxation": True,
        "orders": rows,
        "claim_boundary": (
            "Complete weighted control dependence through logarithmic order "
            "six in the declared row-one weight-13 window. Independent "
            "higher parameter rows, all cusp weights, and all-order "
            "propagation remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
