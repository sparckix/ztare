#!/usr/bin/env python3
"""Exact first replay for a positive-contact row over a moving backbone.

This adapter deliberately separates three objects which a finite normal-form
calculation can otherwise conflate:

* the unpaired canonical row-three residue;
* its affine cancellation problem under contact-zero background columns; and
* the exact inverse-flow boundary of the positive target row itself.

The affine problems are compiled by the substrate-neutral Filtered
Obstruction Compiler.  The target-only inverse pair is checked before any
candidate quotient class is reported.  Consequently an unpaired finite
witness is retained only as a diagnostic and never promoted across the exact
boundary quotient.
"""

from __future__ import annotations

from dataclasses import dataclass
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

from gauge_cone_higher_contact_cost_four_scan import (  # noqa: E402
    CUSP,
    DISCRIMINANT,
    NumericSourcePullback,
    Source,
    Target,
    _add,
    _fixed_target_coefficients,
    _multiply,
    _normalize_prefix,
    _scale,
    _target_power,
    _target_shift,
)
from gauge_controlled_global_magnus_hamiltonian import _ops  # noqa: E402
from gauge_q2c_contact_zero_product_grade import (  # noqa: E402
    _canonical_contact_zero_symbol,
    _source_data,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredGraphQuotientProblem,
    FilteredSurplusProjectionProblem,
    FilteredSymbolCokernelProblem,
    FilteredSymbolMap,
    compile_filtered_graph_quotient,
    compile_filtered_surplus_projection,
    compile_filtered_symbol_cokernel,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


ProfileCoordinate = tuple[int, int]


@dataclass(frozen=True)
class PositiveSeed:
    label: str
    p_exponent: int
    q_exponent: int
    discriminant_depth: int
    contact_depth: int

    def target(self) -> Target:
        return _target_shift(
            _multiply(
                _target_power(DISCRIMINANT, self.discriminant_depth),
                _target_power(CUSP, self.contact_depth),
            ),
            self.p_exponent,
            self.q_exponent,
        )


def _target_sparse(expression: sp.Expr, p: sp.Symbol, q: sp.Symbol) -> Target:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in sp.Poly(
            sp.expand(expression), p, q, domain=sp.QQ
        ).terms()
        if coefficient != 0
    }


def _source_add(left: Source, right: Source) -> Source:
    return _add(left, right)


def _source_difference(left: Source, right: Source) -> Source:
    return _add(left, _scale(right, -1))


def _profile_rows(
    value: Source,
    x: sp.Symbol,
) -> tuple[dict[int, sp.Expr], dict[ProfileCoordinate, sp.Rational]]:
    """Return complete minimum-z profiles and their opposite-parity part."""

    profiles: dict[int, sp.Expr] = {}
    for (radial, normal), coefficient in value.items():
        z_order = radial + normal
        profiles[z_order] = sp.expand(
            profiles.get(z_order, sp.Integer(0))
            + coefficient * (x - sp.Rational(1, 2)) ** radial
        )

    opposite: dict[ProfileCoordinate, sp.Rational] = {}
    for z_order, profile in profiles.items():
        projected = sp.expand(
            (
                profile
                - (-1) ** z_order * profile.subs(x, -x)
            )
            / 2
        )
        polynomial = sp.Poly(projected, x, domain=sp.QQ)
        for (x_degree,), coefficient in polynomial.terms():
            if coefficient != 0:
                opposite[(z_order, x_degree)] = sp.Rational(coefficient)
        target_part = sp.expand(profile - projected)
        assert sp.expand(
            target_part.subs(x, -x)
            - (-1) ** z_order * target_part
        ) == 0
        assert sp.expand(
            projected.subs(x, -x)
            + (-1) ** z_order * projected
        ) == 0
    return profiles, opposite


def _coordinate_name(coordinate: ProfileCoordinate) -> str:
    return f"z{coordinate[0]}x{coordinate[1]}"


def _named_coordinates(
    value: dict[ProfileCoordinate, sp.Rational],
) -> dict[str, str]:
    return {
        _coordinate_name(coordinate): str(coefficient)
        for coordinate, coefficient in sorted(value.items())
        if coefficient != 0
    }


def _parity_certificate() -> dict[str, object]:
    data = _source_data()
    u, z = data["symbols"]
    p, q = data["target_symbols"]
    p0 = data["P0"]
    q0 = data["Q0"]
    x = sp.symbols("x")
    p_in_x = sp.expand(p0.subs(u, x - sp.Rational(1, 2)))
    q_in_x = sp.expand(q0.subs(u, x - sp.Rational(1, 2)))
    cusp = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    cusp_in_x = sp.expand(cusp.subs({p: p_in_x, q: q_in_x}))

    assert sp.expand(p_in_x.coeff(z, 1) - x) == 0
    assert sp.expand(
        q_in_x.coeff(z, 2) - (x**2 - sp.Rational(1, 4)) / 4
    ) == 0
    assert sp.expand(cusp_in_x.coeff(z, 2) + sp.Rational(1, 4)) == 0

    def leading_bracket(
        first_order: int,
        first: sp.Expr,
        second_order: int,
        second: sp.Expr,
    ) -> sp.Expr:
        return sp.expand(
            first_order * first * sp.diff(second, x)
            - second_order * sp.diff(first, x) * second
        )

    routing_rows = []
    for first_kind, first_offset in (("target", 0), ("opposite", 1)):
        for second_kind, second_offset in (("target", 0), ("opposite", 1)):
            first_order, second_order = 7, 10
            first_degree = first_order % 2 + first_offset
            second_degree = second_order % 2 + second_offset
            first = x**first_degree * (1 + x**2)
            second = x**second_degree * (1 + 2 * x**2)
            output_order = first_order + second_order - 3
            output = leading_bracket(
                first_order, first, second_order, second
            )
            output_is_target = (
                (first_kind == "target")
                == (second_kind == "target")
            )
            expected_sign = (
                (-1) ** output_order
                if output_is_target
                else -(-1) ** output_order
            )
            assert sp.expand(output.subs(x, -x) - expected_sign * output) == 0
            routing_rows.append({
                "left": first_kind,
                "right": second_kind,
                "output": "target" if output_is_target else "opposite",
            })

    return {
        "P0_minimum_z_profile": "x",
        "Q0_minimum_z_profile": "(x^2-1/4)/4",
        "C0_minimum_z_profile": "-1/4",
        "density_z2_bracket": "B*f*g'-D*f'*g",
        "routing_rows": routing_rows,
        "exact": True,
    }


def _exact_boundary_certificate(prefix: Target) -> dict[str, object]:
    """Check the target prefix and its logarithmic inverse as one object."""

    velocity = [{}, prefix, {}, {}]
    logarithm = magnus_from_velocity(
        velocity,
        4,
        _ops(0),
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert logarithm[2] == _scale(prefix, sp.Rational(1, 2))
    inverse_logarithm = [{}, {}, _scale(prefix, -sp.Rational(1, 2)), {}, {}]
    inverse_velocity = velocity_from_magnus(
        inverse_logarithm,
        4,
        _ops(0),
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert inverse_velocity[1] == _scale(prefix, -1)
    assert all(
        _add(velocity[order], inverse_velocity[order]) == {}
        for order in range(4)
    )
    return {
        "prefix_logarithm_order_two_is_half_prefix": True,
        "inverse_forward_dexp_is_negative_prefix": True,
        "combined_target_velocity_zero": True,
        "quotient_class": "exact_boundary",
    }


def _coupled_graph_certificate(
    prefix: Target,
    pullback: NumericSourcePullback,
) -> dict[str, object]:
    """Compile ``(8*H(P0,Q0), H)`` modulo the pullback graph."""

    target_coordinates = sorted(prefix)
    target_labels = {
        exponent: f"P{exponent[0]}Q{exponent[1]}"
        for exponent in target_coordinates
    }
    pullback_columns = {
        exponent: _scale(
            pullback.expression({exponent: sp.Integer(1)}, 0),
            8,
        )
        for exponent in target_coordinates
    }
    source_coordinates = sorted({
        coordinate
        for column in pullback_columns.values()
        for coordinate in column
    })
    source_labels = {
        coordinate: f"r{coordinate[0]}n{coordinate[1]}"
        for coordinate in source_coordinates
    }
    boundary_columns = {
        target_labels[exponent]: {
            source_labels[coordinate]: coefficient
            for coordinate, coefficient in pullback_columns[exponent].items()
        }
        for exponent in target_coordinates
    }
    source_pair = _scale(pullback.expression(prefix, 0), 8)
    certificate = compile_filtered_graph_quotient(
        FilteredGraphQuotientProblem(
            name="jacobian_seed_pullback_graph",
            source_basis=tuple(
                FilteredBasisVector(source_labels[coordinate], 0)
                for coordinate in source_coordinates
            ),
            source_relations=(),
            target_basis=tuple(
                FilteredBasisVector(target_labels[exponent], 0)
                for exponent in target_coordinates
            ),
            target_relations=(),
            boundary_map=FilteredSymbolMap(
                "eight_times_seed_pullback",
                0,
                boundary_columns,
            ),
            distinguished_source={
                source_labels[coordinate]: coefficient
                for coordinate, coefficient in source_pair.items()
            },
            distinguished_target={
                target_labels[exponent]: coefficient
                for exponent, coefficient in prefix.items()
            },
        )
    )
    assert not certificate.distinguished_survives
    assert not certificate.compressed_source_survives
    assert certificate.compressed_source_by_basis == ()
    return {
        "schema": certificate.schema,
        "graph_quotient_dimension": certificate.graph_quotient_dimension,
        "compressed_source_zero": True,
        "distinguished_survives": False,
        "graph_constraint_sha256": certificate.graph_constraint_sha256,
    }


def _backbone_column(
    prefix: Target,
    background_symbol: Target,
    *,
    pullback: NumericSourcePullback,
    base_background: list[Target],
    base_residual: Source,
    normalization_contact_depth: int,
) -> Source:
    moved_background = [
        base_background[0],
        _add(base_background[1], background_symbol),
    ]
    moved = _normalize_prefix(
        prefix,
        normalization_contact_depth,
        pullback,
        moved_background,
    )
    return _source_difference(moved.row_three_residual, base_residual)


def _compile_window(
    name: str,
    seed: dict[ProfileCoordinate, sp.Rational],
    columns: dict[str, dict[ProfileCoordinate, sp.Rational]],
) -> dict[str, object]:
    coordinates = sorted({
        *seed,
        *(coordinate for column in columns.values() for coordinate in column),
    })
    if not seed:
        return {
            "opposite_seed_zero": True,
            "full_pair_cancellable": True,
            "reason": "no distinguished opposite-parity coordinate",
        }
    coordinate_names = {
        coordinate: _coordinate_name(coordinate)
        for coordinate in coordinates
    }
    domain_basis = tuple(
        FilteredBasisVector(column, 0) for column in columns
    )
    codomain_basis = tuple(
        FilteredBasisVector(coordinate_names[coordinate], 0)
        for coordinate in coordinates
    )
    named_columns = {
        column_name: {
            coordinate_names[coordinate]: coefficient
            for coordinate, coefficient in column.items()
            if coefficient != 0
        }
        for column_name, column in columns.items()
    }
    named_seed = {
        coordinate_names[coordinate]: coefficient
        for coordinate, coefficient in seed.items()
        if coefficient != 0
    }
    full = compile_filtered_symbol_cokernel(
        FilteredSymbolCokernelProblem(
            name=f"{name}_full_opposite_parity",
            domain_basis=domain_basis,
            domain_relations=(),
            codomain_basis=codomain_basis,
            codomain_relations=(),
            maps=(FilteredSymbolMap("moving_backbone", 0, named_columns),),
            distinguished=named_seed,
        )
    )

    terminal_coordinate = max(
        seed,
        key=lambda coordinate: (
            coordinate[0] + coordinate[1],
            coordinate[1],
            coordinate[0],
        ),
    )
    surplus_coordinates = [
        coordinate for coordinate in coordinates
        if coordinate != terminal_coordinate
    ]
    if not surplus_coordinates:
        return {
            "opposite_seed_zero": False,
            "coordinate_count": 1,
            "full_distinguished_survives": full.distinguished_survives,
            "full_decomposition": full.to_dict()["decomposition_by_column"],
            "affine_split_degenerate": True,
        }
    terminal_name = coordinate_names[terminal_coordinate]
    surplus_names = {
        coordinate: coordinate_names[coordinate]
        for coordinate in surplus_coordinates
    }
    surplus_columns = {
        column_name: {
            surplus_names[coordinate]: coefficient
            for coordinate, coefficient in column.items()
            if coordinate in surplus_names and coefficient != 0
        }
        for column_name, column in columns.items()
    }
    terminal_columns = {
        column_name: (
            {terminal_name: column[terminal_coordinate]}
            if column.get(terminal_coordinate, 0) != 0
            else {}
        )
        for column_name, column in columns.items()
    }
    affine = compile_filtered_surplus_projection(
        FilteredSurplusProjectionProblem(
            name=f"{name}_affine_terminal_split",
            domain_basis=domain_basis,
            domain_relations=(),
            surplus_basis=tuple(
                FilteredBasisVector(surplus_names[coordinate], 0)
                for coordinate in surplus_coordinates
            ),
            surplus_relations=(),
            terminal_basis=(FilteredBasisVector(terminal_name, 0),),
            terminal_relations=(),
            surplus_map=FilteredSymbolMap(
                "moving_backbone_surplus", 0, surplus_columns
            ),
            terminal_map=FilteredSymbolMap(
                "moving_backbone_terminal", 0, terminal_columns
            ),
            distinguished_surplus={
                surplus_names[coordinate]: -seed.get(coordinate, 0)
                for coordinate in surplus_coordinates
                if seed.get(coordinate, 0) != 0
            },
            distinguished_terminal={terminal_name: -seed[terminal_coordinate]},
        )
    )
    assert affine.distinguished_pair_cancellable == (
        not full.distinguished_survives
    )
    return {
        "opposite_seed_zero": False,
        "coordinate_count": len(coordinates),
        "terminal_coordinate": list(terminal_coordinate),
        "terminal_source_hamiltonian_degree": sum(terminal_coordinate),
        "full_distinguished_survives": full.distinguished_survives,
        "full_pair_cancellable": affine.distinguished_pair_cancellable,
        "surplus_demand_reachable": affine.distinguished_surplus_reachable,
        "surplus_pairing": affine.distinguished_surplus_pairing,
        "terminal_pairing": affine.distinguished_pairing,
        "full_witness": full.to_dict()["witness_by_codomain_basis"],
        "full_decomposition": full.to_dict()["decomposition_by_column"],
        "affine_cancellation": affine.to_dict()[
            "cancellation_by_domain_basis"
        ],
        "surplus_constraint_sha256": affine.surplus_constraint_sha256,
        "terminal_constraint_sha256": affine.terminal_constraint_sha256,
    }


def _case(
    seed: PositiveSeed,
    *,
    training_weight: int,
    heldout_weight: int,
) -> dict[str, object]:
    p, q = sp.symbols("P Q")
    x = sp.symbols("x")
    prefix = seed.target()
    pullback = NumericSourcePullback()
    background = _fixed_target_coefficients(1)
    base = _normalize_prefix(
        prefix,
        seed.contact_depth,
        pullback,
        background,
    )
    _profiles, base_opposite = _profile_rows(base.row_three_residual, x)

    target_symbols = {
        weight: _target_sparse(
            _canonical_contact_zero_symbol(weight, p, q), p, q
        )
        for weight in range(5, heldout_weight + 1)
    }
    source_columns: dict[str, Source] = {}
    opposite_columns: dict[str, dict[ProfileCoordinate, sp.Rational]] = {}
    for weight, target_symbol in target_symbols.items():
        label = f"backbone_weight_{weight}"
        source_column = _backbone_column(
            prefix,
            target_symbol,
            pullback=pullback,
            base_background=background,
            base_residual=base.row_three_residual,
            normalization_contact_depth=seed.contact_depth,
        )
        source_columns[label] = source_column
        _column_profiles, opposite_columns[label] = _profile_rows(
            source_column, x
        )

    # The moving-background dependence must be a single fixed linear map.
    first_label = "backbone_weight_5"
    last_training_label = f"backbone_weight_{training_weight}"
    direct_background = [
        background[0],
        _add(
            background[1],
            _add(
                _scale(target_symbols[5], 2),
                _scale(target_symbols[training_weight], -3),
            ),
        ),
    ]
    direct = _normalize_prefix(
        prefix,
        seed.contact_depth,
        pullback,
        direct_background,
    )
    predicted = _source_add(
        base.row_three_residual,
        _source_add(
            _scale(source_columns[first_label], 2),
            _scale(source_columns[last_training_label], -3),
        ),
    )
    assert _source_difference(direct.row_three_residual, predicted) == {}

    training_columns = {
        name: column
        for name, column in opposite_columns.items()
        if int(name.rsplit("_", 1)[1]) <= training_weight
    }
    return {
        "seed": {
            "label": seed.label,
            "P_exponent": seed.p_exponent,
            "Q_exponent": seed.q_exponent,
            "discriminant_depth": seed.discriminant_depth,
            "contact_depth": seed.contact_depth,
        },
        "exact_boundary": _exact_boundary_certificate(prefix),
        "coupled_graph_boundary": _coupled_graph_certificate(
            prefix, pullback
        ),
        "unpaired_row_three": {
            "sparse_term_count": len(base.row_three_residual),
            "opposite_coordinate_count": len(base_opposite),
            "opposite_coordinates": _named_coordinates(base_opposite),
        },
        "moving_backbone_linearity": {
            "direct_combination": "2*weight_5-3*training_top_weight",
            "exact": True,
        },
        "training": _compile_window(
            f"{seed.label}_weight_{training_weight}",
            base_opposite,
            training_columns,
        ),
        "heldout": _compile_window(
            f"{seed.label}_weight_{heldout_weight}",
            base_opposite,
            opposite_columns,
        ),
        "quotient_verdict": (
            "unpaired_certificate_rejected_exact_target_boundary"
        ),
    }


def run(
    training_weight: int = 7,
    heldout_weight: int = 9,
) -> dict[str, object]:
    if training_weight < 6:
        raise ValueError("training weight must be at least six")
    if heldout_weight <= training_weight:
        raise ValueError("heldout weight must extend training")

    seeds = (
        PositiveSeed("Q2C_boundary", 0, 2, 0, 1),
        PositiveSeed("Q6C_robust", 0, 6, 0, 1),
        PositiveSeed("Q3C2_heldout_contact", 0, 3, 0, 2),
    )
    rows = [
        _case(
            seed,
            training_weight=training_weight,
            heldout_weight=heldout_weight,
        )
        for seed in seeds
    ]
    assert all(
        row["exact_boundary"]["quotient_class"] == "exact_boundary"
        for row in rows
    )
    assert all(
        row["quotient_verdict"]
        == "unpaired_certificate_rejected_exact_target_boundary"
        for row in rows
    )
    return {
        "schema": (
            "axiompack.jacobian_least_positive_contact_moving_backbone.v1"
        ),
        "claim_boundary": (
            "finite target-controlled row-one background windows; the "
            "unpaired residues are diagnostics and vanish in the exact "
            "inverse-flow quotient; no arbitrary source-backbone or "
            "all-index conclusion"
        ),
        "parity": _parity_certificate(),
        "training_weight": training_weight,
        "heldout_weight": heldout_weight,
        "cases": rows,
        "new_information": {
            "target_only_lane_survives_exact_boundary_quotient": False,
            "unpaired_affine_cokernels_are_claims": False,
            "next_object": (
                "source residue modulo the graph of exact coupled "
                "target-flow/source-pullback boundaries"
            ),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
    compile_filtered_graph_quotient,
