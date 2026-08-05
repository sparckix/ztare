#!/usr/bin/env python3
"""All-order support law for current target pullbacks.

The exact rational family is inspected before its parameter expansion.  In
the adapted ``(u,z)`` chart both family coordinates are supported in the
semigroup ``z_exponent >= u_exponent``.  Hence every coefficientwise-
polynomial target Hamiltonian has a current source pullback in the same
semigroup.  The negative-normal transverse ``Z_m`` Hamiltonian is therefore
absent from the current boundary graph at every degree.

Finite graph compilations stress the coordinate implementation.  The
all-order statement is the exact support argument, not stabilization of
those windows.  Lower-row BCH transport is outside this adapter.
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

from gauge_q2c_contact_zero_product_grade import _source_data  # noqa: E402
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredGraphQuotientProblem,
    FilteredSymbolMap,
    compile_filtered_graph_quotient,
)


def _exact_family() -> tuple[
    tuple[sp.Symbol, sp.Symbol, sp.Symbol], sp.Expr, sp.Expr
]:
    parameter, u, z = sp.symbols("s u z")
    gamma = z / 2
    mu = 3 * (parameter - 4) / (2 * (parameter - 6))
    lam = -(parameter - 4) / 4
    w = (1 + mu * (u - 1)) * gamma
    p_auxiliary = (
        (2 + parameter / 2) * w
        + (-3 - 3 * parameter / 2) * w**2
        + parameter * w**3
    )
    q_auxiliary = (
        (1 + parameter / 4) * w**2
        - (2 + parameter) * w**3
        + 3 * parameter * w**4 / 4
    )
    family_p = sp.cancel(lam / mu * (gamma + p_auxiliary))
    family_q = sp.cancel(
        (gamma**2 * (1 + mu * (u - 1)) + q_auxiliary) / lam
    )
    return (parameter, u, z), family_p, family_q


def _support_certificate(
    name: str,
    value: sp.Expr,
    *,
    parameter: sp.Symbol,
    u: sp.Symbol,
    z: sp.Symbol,
) -> dict[str, object]:
    numerator, denominator = sp.cancel(value).as_numer_denom()
    assert not ({u, z} & denominator.free_symbols)
    polynomial = sp.Poly(sp.expand(numerator), u, z)
    rows = [
        (u_power, z_power, coefficient)
        for (u_power, z_power), coefficient in polynomial.terms()
        if coefficient != 0
    ]
    assert rows
    assert all(z_power >= u_power for u_power, z_power, _ in rows)
    assert denominator.subs(parameter, 0) != 0
    radial = sp.symbols("r")
    normal_zero = sp.factor(sum(
        coefficient * radial**u_power
        for u_power, z_power, coefficient in rows
        if u_power == z_power
    ) / denominator)
    return {
        "family_coordinate": name,
        "spatial_denominator_free": True,
        "regular_at_parameter_zero": True,
        "support": [
            [u_power, z_power]
            for u_power, z_power, _coefficient in rows
        ],
        "minimum_normal_order": min(
            z_power - u_power for u_power, z_power, _ in rows
        ),
        "maximum_spatial_degree": max(
            u_power + z_power for u_power, z_power, _ in rows
        ),
        "normal_zero_radial_polynomial": str(normal_zero),
    }


def _graph_window(
    logarithmic_order: int,
    maximum_target_degree: int,
) -> dict[str, object]:
    data = _source_data()
    u, z = data["symbols"]

    def sparse(value: sp.Expr) -> dict[tuple[int, int], sp.Rational]:
        return {
            exponent: sp.Rational(coefficient)
            for exponent, coefficient in sp.Poly(
                sp.expand(value), u, z, domain=sp.QQ
            ).terms()
            if coefficient != 0
        }

    def multiply(
        left: dict[tuple[int, int], sp.Rational],
        right: dict[tuple[int, int], sp.Rational],
    ) -> dict[tuple[int, int], sp.Rational]:
        result: dict[tuple[int, int], sp.Rational] = {}
        for left_exponent, left_coefficient in left.items():
            for right_exponent, right_coefficient in right.items():
                exponent = (
                    left_exponent[0] + right_exponent[0],
                    left_exponent[1] + right_exponent[1],
                )
                result[exponent] = (
                    result.get(exponent, sp.Rational(0))
                    + left_coefficient * right_coefficient
                )
        return {
            exponent: coefficient
            for exponent, coefficient in result.items()
            if coefficient != 0
        }

    def powers(
        value: dict[tuple[int, int], sp.Rational],
    ) -> list[dict[tuple[int, int], sp.Rational]]:
        result = [{(0, 0): sp.Rational(1)}]
        for _exponent in range(maximum_target_degree):
            result.append(multiply(result[-1], value))
        return result

    p_powers = powers(sparse(data["P0"]))
    q_powers = powers(sparse(data["Q0"]))
    target_exponents = [
        (p_power, total_degree - p_power)
        for total_degree in range(1, maximum_target_degree + 1)
        for p_power in range(total_degree + 1)
    ]
    target_labels = {
        exponent: f"P{exponent[0]}Q{exponent[1]}"
        for exponent in target_exponents
    }
    pullback_columns = {
        exponent: {
            coordinate: 8 * coefficient
            for coordinate, coefficient in multiply(
                p_powers[exponent[0]], q_powers[exponent[1]]
            ).items()
        }
        for exponent in target_exponents
    }
    source_exponents = {
        exponent
        for column in pullback_columns.values()
        for exponent in column
    }
    assert all(
        z_power >= u_power for u_power, z_power in source_exponents
    )
    terminal = (3 * logarithmic_order - 5, logarithmic_order + 2)
    assert terminal[1] - terminal[0] == 7 - 2 * logarithmic_order
    assert terminal[1] < terminal[0]
    assert terminal not in source_exponents
    all_source_exponents = sorted({*source_exponents, terminal})
    source_labels = {
        exponent: f"u{exponent[0]}z{exponent[1]}"
        for exponent in all_source_exponents
    }
    boundary_columns = {
        target_labels[target_exponent]: {
            source_labels[exponent]: coefficient
            for exponent, coefficient
            in pullback_columns[target_exponent].items()
        }
        for target_exponent in target_exponents
    }
    certificate = compile_filtered_graph_quotient(
        FilteredGraphQuotientProblem(
            name=(
                f"jacobian_current_pullback_Z{logarithmic_order}_"
                f"target_degree_{maximum_target_degree}"
            ),
            source_basis=tuple(
                FilteredBasisVector(source_labels[exponent], 0)
                for exponent in all_source_exponents
            ),
            source_relations=(),
            target_basis=tuple(
                FilteredBasisVector(target_labels[exponent], 0)
                for exponent in target_exponents
            ),
            target_relations=(),
            boundary_map=FilteredSymbolMap(
                "seed_pullback_graph",
                0,
                boundary_columns,
            ),
            distinguished_source={source_labels[terminal]: 1},
            distinguished_target={},
        )
    )
    assert certificate.distinguished_survives
    assert certificate.compressed_source_survives
    assert certificate.compressed_witness_by_source_basis == (
        (source_labels[terminal], "1"),
    )
    return {
        "logarithmic_order": logarithmic_order,
        "maximum_target_degree": maximum_target_degree,
        "target_dimension": len(target_exponents),
        "source_dimension": len(all_source_exponents),
        "terminal_exponent_u_z": list(terminal),
        "terminal_normal_order": terminal[1] - terminal[0],
        "distinguished_survives": True,
        "witness": certificate.to_dict()[
            "compressed_witness_by_source_basis"
        ],
        "graph_constraint_sha256": certificate.graph_constraint_sha256,
    }


def run() -> dict[str, object]:
    (parameter, u, z), family_p, family_q = _exact_family()
    data = _source_data()
    seed_u, seed_z = data["symbols"]
    assert sp.expand(
        family_p.subs(parameter, 0).subs({u: seed_u, z: seed_z})
        - data["P0"]
    ) == 0
    assert sp.expand(
        family_q.subs(parameter, 0).subs({u: seed_u, z: seed_z})
        - data["Q0"]
    ) == 0
    support = [
        _support_certificate(
            "P_s", family_p, parameter=parameter, u=u, z=z
        ),
        _support_certificate(
            "Q_s", family_q, parameter=parameter, u=u, z=z
        ),
    ]
    windows = [
        _graph_window(5, 9),
        _graph_window(7, 13),
    ]
    return {
        "schema": "axiompack.jacobian_moving_pullback_normal_semigroup.v1",
        "adapted_coordinates": {
            "u": "v+1",
            "z": "2+2*t-3*v",
            "gamma": "z/2",
        },
        "exact_family_support": support,
        "coefficientwise_support_theorem": {
            "semigroup": "z_exponent >= u_exponent",
            "closed_under_addition": True,
            "closed_under_multiplication": True,
            "polynomial_target_substitution_preserves_semigroup": True,
            "parameter_coefficient_extraction_preserves_support": True,
        },
        "finite_graph_stress": windows,
        "all_order_current_row_theorem": {
            "Z_m_hamiltonian_exponent": ["3*m-5", "m+2"],
            "Z_m_normal_order": "7-2*m",
            "excluded_for_every_m_at_least_four": True,
            "independent_of_target_degree": True,
        },
        "claim_boundary": (
            "All-order exclusion of current polynomial target columns from "
            "the negative-normal Z_m coordinate. Lower target rows can "
            "still reach negative normal through BCH transport; no "
            "unrestricted tail-minimax conclusion."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
