#!/usr/bin/env python3
"""Complete finite-row contact-zero parameter jet through order six."""

from __future__ import annotations

from dataclasses import dataclass
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

from gauge_contact_zero_quadratic_coupled_shell import (  # noqa: E402
    ControlPolynomial,
    _control_ops,
    _monomial_name,
    _velocity_polynomial,
)
from gauge_contact_zero_weighted_complete_coupled_shell import (  # noqa: E402
    _control_cost,
    _weighted_monomials,
)
from gauge_contact_zero_weighted_parameter_fiber import (  # noqa: E402
    _filtered_blocks,
    _monomial_exponents,
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
    _series_coefficients,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredCoupledBlockProblem,
    FilteredPolynomialFiberProblem,
    compile_filtered_polynomial_fiber,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
)


@dataclass(frozen=True)
class Direction:
    label: str
    row: int
    weight: int
    cost: int


@dataclass(frozen=True)
class CompleteJetReplay:
    directions: tuple[Direction, ...]
    labels: tuple[str, ...]
    costs: tuple[int, ...]
    source_logarithm: list[ControlPolynomial]
    target_logarithm: list[ControlPolynomial]


def _build_complete_jet_replay(
    *,
    maximum_order: int,
    maximum_weight: int | None = None,
    weights: tuple[int, ...] | None = None,
) -> CompleteJetReplay:
    if (maximum_weight is None) == (weights is None):
        raise ValueError("declare exactly one of maximum_weight or weights")
    selected_weights = (
        tuple(range(5, maximum_weight + 1))
        if maximum_weight is not None
        else tuple(weights or ())
    )
    if (
        not selected_weights
        or any(weight < 5 for weight in selected_weights)
        or len(selected_weights) != len(set(selected_weights))
    ):
        raise ValueError("contact-zero weights must be distinct integers >=5")
    (parameter, u, z), family_p, family_q = _exact_family()
    (_symbols, source_only, _support) = _source_only_hamiltonian()
    target_p, target_q = sp.symbols("P Q")
    directions = tuple(
        Direction(
            label=f"row_{row}_weight_{weight}",
            row=row,
            weight=weight,
            cost=row + 1,
        )
        for row in range(maximum_order)
        for weight in selected_weights
    )
    labels = tuple(direction.label for direction in directions)
    costs = tuple(direction.cost for direction in directions)

    source_baseline = _series_coefficients(
        source_only, parameter, maximum_order
    )
    source_directions = []
    target_directions = []
    for direction in directions:
        target_symbol = sp.expand(_canonical_contact_zero_symbol(
            direction.weight, target_p, target_q
        ))
        moving_symbol = target_symbol.subs({
            target_p: family_p,
            target_q: family_q,
        })
        source_directions.append(_series_coefficients(
            8 * parameter**direction.row * moving_symbol,
            parameter,
            maximum_order,
        ))
        target_directions.append(_series_coefficients(
            parameter**direction.row * target_symbol,
            parameter,
            maximum_order,
        ))

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
    return CompleteJetReplay(
        directions=directions,
        labels=labels,
        costs=costs,
        source_logarithm=source_logarithm,
        target_logarithm=target_logarithm,
    )


def _compile_jet_window(
    *,
    replay: CompleteJetReplay,
    order: int,
    maximum_weight: int,
):
    included_indices = tuple(
        index
        for index, direction in enumerate(replay.directions)
        if direction.weight <= maximum_weight and direction.cost <= order
    )
    domain_monomials = _weighted_monomials(
        included_indices, replay.costs, order
    )
    domain_names = tuple(
        _monomial_name(monomial, replay.labels)
        for monomial in domain_monomials
    )
    source_blocks = _filtered_blocks(
        side="source",
        coefficient=replay.source_logarithm[order],
        domain_monomials=domain_monomials,
        labels=replay.labels,
        minimum_hamiltonian_degree=2 * order + 3,
    )
    target_blocks = _filtered_blocks(
        side="target",
        coefficient=replay.target_logarithm[order],
        domain_monomials=domain_monomials,
        labels=replay.labels,
        minimum_hamiltonian_degree=2 * order + 1,
    )
    linearization = FilteredCoupledBlockProblem(
        name=f"complete_parameter_jet_linearization_q{order}_w{maximum_weight}",
        domain_basis=tuple(
            FilteredBasisVector(name, 0) for name in domain_names
        ),
        domain_relations=(),
        blocks=source_blocks + target_blocks,
    )
    parameter_labels = tuple(
        f"c_{replay.labels[index]}" for index in included_indices
    )
    certificate = compile_filtered_polynomial_fiber(
        FilteredPolynomialFiberProblem(
            name=f"complete_parameter_jet_fiber_q{order}_w{maximum_weight}",
            linearization=linearization,
            parameters=parameter_labels,
            monomial_exponents={
                name: _monomial_exponents(monomial, included_indices)
                for name, monomial in zip(
                    domain_names, domain_monomials, strict=True
                )
            },
        )
    )
    return certificate, {
        "control_count": len(included_indices),
        "weighted_monomial_count": len(domain_monomials),
        "source_rate_face_block_count": len(source_blocks),
        "target_rate_face_block_count": len(target_blocks),
    }


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("the complete jet replay requires order six")
    replay = _build_complete_jet_replay(
        maximum_order=maximum_order,
        maximum_weight=7,
    )
    rows = []
    for order in (5, 6):
        for window, maximum_weight in (
            ("training", 6),
            ("heldout", 7),
        ):
            certificate, counts = _compile_jet_window(
                replay=replay,
                order=order,
                maximum_weight=maximum_weight,
            )
            rows.append({
                "logarithmic_order": order,
                "window": window,
                "maximum_cusp_weight": maximum_weight,
                **counts,
                "certificate": certificate.to_dict(),
            })
    return {
        "schema": "axiompack.jacobian_complete_parameter_jet.v1",
        "parameter_rows": list(range(maximum_order)),
        "control_cost": "row+1",
        "orders": rows,
        "claim_boundary": (
            "Complete coefficient rows below logarithmic order six in the "
            "canonical contact-zero weight-seven window. Unbounded weight "
            "and all-order propagation remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
