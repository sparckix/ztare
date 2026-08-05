#!/usr/bin/env python3
"""Exact polynomial-fiber test for the weighted contact-zero controls."""

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

from gauge_contact_zero_quadratic_coupled_shell import (  # noqa: E402
    ControlMonomial,
    ControlPolynomial,
    _monomial_name,
)
from gauge_contact_zero_weighted_complete_coupled_shell import (  # noqa: E402
    _build_weighted_control_replay,
    _weighted_monomials,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredCoupledBlock,
    FilteredCoupledBlockProblem,
    FilteredPolynomialFiberProblem,
    FilteredSymbolMap,
    compile_filtered_polynomial_fiber,
)


def _monomial_exponents(
    monomial: ControlMonomial,
    included_indices: tuple[int, ...],
) -> tuple[int, ...]:
    return tuple(monomial.count(index) for index in included_indices)


def _filtered_blocks(
    *,
    side: str,
    coefficient: ControlPolynomial,
    domain_monomials: tuple[ControlMonomial, ...],
    labels: tuple[str, ...],
    minimum_hamiltonian_degree: int,
) -> tuple[FilteredCoupledBlock, ...]:
    coordinates_by_degree: dict[int, set[tuple[int, int]]] = {}
    for spatial_coefficient in coefficient.values():
        for exponent, value in spatial_coefficient.items():
            degree = sum(exponent)
            if value != 0 and degree >= minimum_hamiltonian_degree:
                coordinates_by_degree.setdefault(degree, set()).add(exponent)

    blocks = []
    for degree in sorted(coordinates_by_degree):
        coordinates = tuple(sorted(coordinates_by_degree[degree]))
        coordinate_names = {
            exponent: f"x{exponent[0]}y{exponent[1]}"
            for exponent in coordinates
        }
        block_name = f"{side}_degree_{degree}"
        blocks.append(FilteredCoupledBlock(
            name=block_name,
            codomain_basis=tuple(
                FilteredBasisVector(coordinate_names[exponent], degree)
                for exponent in coordinates
            ),
            codomain_relations=(),
            symbol_map=FilteredSymbolMap(
                f"{block_name}_polynomial_control",
                degree,
                {
                    _monomial_name(monomial, labels): {
                        coordinate_names[exponent]: value
                        for exponent in coordinates
                        if (
                            value := coefficient.get(monomial, {}).get(
                                exponent, sp.Integer(0)
                            )
                        ) != 0
                    }
                    for monomial in domain_monomials
                },
            ),
            distinguished={
                coordinate_names[exponent]: value
                for exponent in coordinates
                if (
                    value := coefficient.get((), {}).get(
                        exponent, sp.Integer(0)
                    )
                ) != 0
            },
        ))
    return tuple(blocks)


def _compile_window(
    *,
    order: int,
    included_indices: tuple[int, ...],
    labels: tuple[str, ...],
    costs: tuple[int, ...],
    source_logarithm: list[ControlPolynomial],
    target_logarithm: list[ControlPolynomial],
):
    domain_monomials = _weighted_monomials(
        included_indices, costs, order
    )
    domain_names = tuple(
        _monomial_name(monomial, labels) for monomial in domain_monomials
    )
    source_blocks = _filtered_blocks(
        side="source",
        coefficient=source_logarithm[order],
        domain_monomials=domain_monomials,
        labels=labels,
        minimum_hamiltonian_degree=2 * order + 3,
    )
    target_blocks = _filtered_blocks(
        side="target",
        coefficient=target_logarithm[order],
        domain_monomials=domain_monomials,
        labels=labels,
        minimum_hamiltonian_degree=2 * order + 1,
    )
    window_name = "_".join(labels[index] for index in included_indices)
    linearization = FilteredCoupledBlockProblem(
        name=f"weighted_parameter_linearization_q{order}_{window_name}",
        domain_basis=tuple(
            FilteredBasisVector(name, 0) for name in domain_names
        ),
        domain_relations=(),
        blocks=source_blocks + target_blocks,
    )
    parameters = tuple(f"c_{labels[index]}" for index in included_indices)
    return compile_filtered_polynomial_fiber(
        FilteredPolynomialFiberProblem(
            name=f"weighted_parameter_fiber_q{order}_{window_name}",
            linearization=linearization,
            parameters=parameters,
            monomial_exponents={
                name: _monomial_exponents(monomial, included_indices)
                for name, monomial in zip(
                    domain_names, domain_monomials, strict=True
                )
            },
        )
    ), len(source_blocks), len(target_blocks)


def run(maximum_order: int = 6) -> dict[str, object]:
    if maximum_order < 6:
        raise ValueError("the parameter-fiber replay requires order six")
    replay = _build_weighted_control_replay(maximum_order)
    windows = {
        "training": tuple(range(8)),
        "heldout": tuple(range(10)),
    }
    rows = []
    for order in (5, 6):
        for window, included_indices in windows.items():
            certificate, source_block_count, target_block_count = (
                _compile_window(
                    order=order,
                    included_indices=included_indices,
                    labels=replay.labels,
                    costs=replay.costs,
                    source_logarithm=replay.source_logarithm,
                    target_logarithm=replay.target_logarithm,
                )
            )
            rows.append({
                "logarithmic_order": order,
                "window": window,
                "included_control_labels": [
                    replay.labels[index] for index in included_indices
                ],
                "source_rate_face_block_count": source_block_count,
                "target_rate_face_block_count": target_block_count,
                "certificate": certificate.to_dict(),
            })
    return {
        "schema": "axiompack.jacobian_weighted_parameter_fiber.v1",
        "control_costs": {
            label: cost
            for label, cost in zip(replay.labels, replay.costs, strict=True)
        },
        "orders": rows,
        "claim_boundary": (
            "Exact polynomial fiber through logarithmic order six for the "
            "declared row-one weight-thirteen control window. Higher "
            "parameter rows, unbounded cusp weight, and all-order "
            "propagation remain open."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
