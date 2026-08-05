#!/usr/bin/env python3
"""Complete low-weight contact-zero tangent against coupled source shells.

One canonical lift-compatible contact-zero symbol exists at every cusp
weight at least five.  This replay inserts the full moving pullback of the
row-one symbols at weights five through thirteen, adds the bounded controlled
connection, and compiles all source-Hamiltonian grades on or above the
rate-two face with one shared column per connection.

The result is an exact finite-difference tangent statement.  Mixed
multivariate terms, arbitrary weights, and all-order propagation are outside
its claim boundary.
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
    _source_ops,
    _target_ops,
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


def _source_logarithm(
    connection: sp.Expr,
    *,
    source_only: sp.Expr,
    parameter: sp.Symbol,
    u: sp.Symbol,
    z: sp.Symbol,
    maximum_order: int,
) -> list[sp.Expr]:
    velocity = _series_coefficients(
        sp.cancel(source_only + 8 * connection),
        parameter,
        maximum_order,
    )
    return magnus_from_velocity(
        velocity,
        maximum_order,
        _source_ops(u, z),
        VelocityPlacement.RIGHT_MULTIPLY,
    )


def _coefficient_dictionary(
    expression: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> dict[tuple[int, int], sp.Rational]:
    return {
        exponent: sp.Rational(coefficient)
        for exponent, coefficient in sp.Poly(
            expression, u, z, domain=sp.QQ
        ).terms()
        if coefficient != 0
    }


def _compile_bundle(
    *,
    name: str,
    baseline: sp.Expr,
    samples: dict[str, sp.Expr],
    all_expressions: tuple[sp.Expr, ...],
    order: int,
    u: sp.Symbol,
    z: sp.Symbol,
    reverse: bool,
):
    minimum_degree = 2 * order + 3
    coordinates_by_degree: dict[int, set[tuple[int, int]]] = {}
    for expression in all_expressions:
        for exponent, coefficient in sp.Poly(expression, u, z).terms():
            degree = sum(exponent)
            if coefficient != 0 and degree >= minimum_degree:
                coordinates_by_degree.setdefault(degree, set()).add(exponent)

    baseline_coefficients = _coefficient_dictionary(baseline, u, z)
    sample_differences = {
        label: _coefficient_dictionary(
            sp.expand(expression - baseline), u, z
        )
        for label, expression in samples.items()
    }
    labels = tuple(samples)
    degrees = sorted(coordinates_by_degree, reverse=True)
    if reverse:
        labels = tuple(reversed(labels))
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
                    f"degree_{degree}_contact_zero_tangent",
                    degree,
                    {
                        label: {
                            coordinate_names[coordinate]: coefficient
                            for coordinate in coordinates
                            if (
                                coefficient := sample_differences[
                                    label
                                ].get(coordinate, sp.Integer(0))
                            ) != 0
                        }
                        for label in labels
                    },
                ),
                distinguished={
                    coordinate_names[coordinate]: coefficient
                    for coordinate in coordinates
                    if (
                        coefficient := baseline_coefficients.get(
                            coordinate, sp.Integer(0)
                        )
                    ) != 0
                },
            )
        )
    return compile_filtered_coupled_blocks(
        FilteredCoupledBlockProblem(
            name=f"{name}_{'reversed' if reverse else 'canonical'}",
            domain_basis=tuple(
                FilteredBasisVector(label, 0) for label in labels
            ),
            domain_relations=(),
            blocks=tuple(blocks),
        )
    )


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("the held-out tangent requires order six")

    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    baseline = _source_logarithm(
        sp.Integer(0),
        source_only=source_only,
        parameter=parameter,
        u=u,
        z=z,
        maximum_order=maximum_order,
    )
    target_p, target_q = sp.symbols("P Q")
    controlled_connection = _controlled_target(
        parameter, family_p, family_q
    )
    controlled_logarithm = _source_logarithm(
        controlled_connection,
        source_only=source_only,
        parameter=parameter,
        u=u,
        z=z,
        maximum_order=maximum_order,
    )

    contact_zero_logarithms: dict[int, list[sp.Expr]] = {}
    target_symbols: dict[int, sp.Expr] = {}
    for weight in range(5, 14):
        symbol = sp.expand(
            _canonical_contact_zero_symbol(weight, target_p, target_q)
        )
        target_symbols[weight] = symbol
        moving_symbol = symbol.subs({target_p: family_p, target_q: family_q})
        contact_zero_logarithms[weight] = _source_logarithm(
            parameter * moving_symbol,
            source_only=source_only,
            parameter=parameter,
            u=u,
            z=z,
            maximum_order=maximum_order,
        )

    # A row-one velocity s*H has target logarithm s^2*H/2 exactly.  It has
    # no target coefficient at orders five or six.  Check the nonautonomous
    # controlled column separately.
    controlled_target_velocity = _series_coefficients(
        _controlled_target(parameter, target_p, target_q),
        parameter,
        maximum_order,
    )
    controlled_target_logarithm = magnus_from_velocity(
        controlled_target_velocity,
        maximum_order,
        _target_ops(target_p, target_q),
        VelocityPlacement.LEFT_MULTIPLY,
    )

    rows = []
    for order in (5, 6):
        all_samples = {
            "controlled": controlled_logarithm[order],
            **{
                f"weight_{weight}": logarithm[order]
                for weight, logarithm in contact_zero_logarithms.items()
            },
        }
        training_samples = {
            label: expression
            for label, expression in all_samples.items()
            if label == "controlled" or int(label.rsplit("_", 1)[1]) <= 11
        }
        all_expressions = (
            baseline[order], *all_samples.values()
        )
        training = _compile_bundle(
            name=f"contact_zero_training_order_{order}",
            baseline=baseline[order],
            samples=training_samples,
            all_expressions=all_expressions,
            order=order,
            u=u,
            z=z,
            reverse=False,
        )
        training_reversed = _compile_bundle(
            name=f"contact_zero_training_order_{order}",
            baseline=baseline[order],
            samples=training_samples,
            all_expressions=all_expressions,
            order=order,
            u=u,
            z=z,
            reverse=True,
        )
        heldout = _compile_bundle(
            name=f"contact_zero_heldout_order_{order}",
            baseline=baseline[order],
            samples=all_samples,
            all_expressions=all_expressions,
            order=order,
            u=u,
            z=z,
            reverse=False,
        )
        assert training.distinguished_survives
        assert training_reversed.distinguished_survives
        assert heldout.distinguished_survives
        assert (
            training.common_control_rank
            == training_reversed.common_control_rank
        )
        assert heldout.common_control_rank >= training.common_control_rank

        controlled_target_degree = max(
            (
                sum(exponent)
                for exponent, coefficient in sp.Poly(
                    controlled_target_logarithm[order],
                    target_p,
                    target_q,
                ).terms()
                if coefficient != 0
            ),
            default=-1,
        )
        controlled_target_derivation_degree = (
            controlled_target_degree - 1
            if controlled_target_degree >= 0
            else -1
        )
        assert controlled_target_derivation_degree < 2 * order

        rows.append({
            "logarithmic_order": order,
            "ambient_dimension": heldout.ambient_dimension,
            "training_columns": list(training_samples),
            "training_control_rank": training.common_control_rank,
            "training_augmented_rank": training.constraint_rank + 1,
            "heldout_columns": ["weight_12", "weight_13"],
            "heldout_control_rank": heldout.common_control_rank,
            "heldout_augmented_rank": heldout.constraint_rank + 1,
            "source_only_bundle_survives_training": True,
            "source_only_bundle_survives_heldout": True,
            "basis_and_block_permutation_unchanged": True,
            "controlled_target_derivation_degree": (
                controlled_target_derivation_degree
            ),
            "row_one_symbol_target_orders_five_and_six_zero": True,
            "all_columns_uncharged_on_checked_target_orders": True,
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
            "axiompack.jacobian_contact_zero_low_weight_"
            "coupled_shell.v1"
        ),
        "training_weights": [5, 6, 7, 8, 9, 10, 11],
        "heldout_weights": [12, 13],
        "canonical_symbol_count": len(target_symbols),
        "orders": rows,
        "low_weight_finite_difference_tangent_reaches_bundle": False,
        "new_information": (
            "The source-only high-rate bundle remains outside the common "
            "span of the controlled column and every canonical row-one "
            "contact-zero finite difference through held-out weight 13 at "
            "orders five and six."
        ),
        "claim_boundary": (
            "Exact single-direction finite differences through cusp weight "
            "13 and logarithmic orders five and six. Mixed multivariate "
            "terms, higher parameter rows, all weights, and all-order "
            "propagation are not classified."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
