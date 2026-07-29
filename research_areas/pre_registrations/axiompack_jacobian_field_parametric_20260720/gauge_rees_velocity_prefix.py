#!/usr/bin/env python3
"""Exact slope-two Rees-velocity contact for the normalized family."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp
from sympy.polys.matrices import DomainMatrix


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_fixed_bound_family_extension import (  # noqa: E402
    _simultaneous_particular_solutions,
)
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _source_degree,
    _source_target_image,
    _target_lift_ideals,
)
from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _pair_system,
)
from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
)


Pair = tuple[sp.Expr, sp.Expr]
ScalarSeries = list[sp.Expr]
PairSeries = list[Pair]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _zero_series(maximum_order: int) -> ScalarSeries:
    return [
        sp.Integer(0) for _ in range(maximum_order + 1)
    ]


def _multiply_series(
    left: ScalarSeries,
    right: ScalarSeries,
    maximum_order: int,
) -> ScalarSeries:
    result = _zero_series(maximum_order)
    for first_order, first in enumerate(left):
        if first == 0:
            continue
        for second_order, second in enumerate(right):
            order = first_order + second_order
            if order > maximum_order:
                break
            if second != 0:
                result[order] += first * second
    return [sp.expand(item) for item in result]


def _power_series(
    value: ScalarSeries,
    exponent: int,
    maximum_order: int,
) -> ScalarSeries:
    result = _zero_series(maximum_order)
    result[0] = sp.Integer(1)
    for _ in range(exponent):
        result = _multiply_series(
            result, value, maximum_order
        )
    return result


def _evaluate_series(
    value: sp.Expr,
    first_symbol: sp.Symbol,
    second_symbol: sp.Symbol,
    first_series: ScalarSeries,
    second_series: ScalarSeries,
    maximum_order: int,
) -> ScalarSeries:
    result = _zero_series(maximum_order)
    for (first_power, second_power), coefficient in sp.Poly(
        value, first_symbol, second_symbol, domain=sp.QQ
    ).terms():
        term = _multiply_series(
            _power_series(
                first_series, first_power, maximum_order
            ),
            _power_series(
                second_series, second_power, maximum_order
            ),
            maximum_order,
        )
        for order in range(maximum_order + 1):
            result[order] += coefficient * term[order]
    return [sp.expand(item) for item in result]


def _field_at_family_series(
    field: Pair,
    p: sp.Symbol,
    q: sp.Symbol,
    p_series: ScalarSeries,
    q_series: ScalarSeries,
    maximum_order: int,
) -> PairSeries:
    components = [
        _evaluate_series(
            component,
            p,
            q,
            p_series,
            q_series,
            maximum_order,
        )
        for component in field
    ]
    return [
        (
            components[0][order],
            components[1][order],
        )
        for order in range(maximum_order + 1)
    ]


def _source_response_series(
    field: Pair,
    jacobian_series: list[list[ScalarSeries]],
    maximum_order: int,
) -> PairSeries:
    return [
        (
            sp.expand(
                jacobian_series[0][0][order] * field[0]
                + jacobian_series[0][1][order] * field[1]
            ),
            sp.expand(
                jacobian_series[1][0][order] * field[0]
                + jacobian_series[1][1][order] * field[1]
            ),
        )
        for order in range(maximum_order + 1)
    ]


def _solve_velocity_order(
    *,
    logarithm_order: int,
    bound: int,
    residual: Pair,
    family: dict[str, object],
    data: dict[str, object],
    v: sp.Symbol,
    t: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[Pair, sp.Expr, dict[str, object]]:
    residual_degrees = [
        _source_degree(item, v, t) for item in residual
    ]
    columns, metadata, target_window = _source_target_image(
        source_order=logarithm_order,
        source_degree_bound=bound,
        first_target_degree=max(
            bound + 3, residual_degrees[0]
        ),
        second_target_degree=max(
            bound + 5, residual_degrees[1]
        ),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=data["P"][0],
        q0=data["Q"][0],
        jacobian=family["jacobian"],
    )
    matrix, rhs, row_keys = _pair_system(
        columns, residual, v, t
    )
    rank = matrix.rank()
    augmented_rank = DomainMatrix.hstack(
        matrix, rhs
    ).rank()
    if rank != augmented_rank:
        raise ValueError(
            f"degree {bound} is incompatible at logarithm "
            f"order {logarithm_order}"
        )
    vector = _simultaneous_particular_solutions(
        matrix, rhs
    )[0]
    source, hamiltonian = _decode_generator(
        vector,
        metadata,
        logarithm_order,
        v,
        t,
        p,
        q,
    )
    return source, hamiltonian, {
        "rank": rank,
        "column_count": matrix.shape[1],
        "nullity": matrix.shape[1] - rank,
        "residual_component_degrees": residual_degrees,
        "target_window": target_window,
        "row_key_sha256": hashlib.sha256(
            json.dumps(
                row_keys, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
    }


def run(maximum_log_order: int = 8) -> dict[str, object]:
    if maximum_log_order < 2:
        raise ValueError("the based source logarithm begins at order two")
    maximum_velocity_order = maximum_log_order - 1
    data = _family_jets(maximum_log_order)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p_series = [
        sp.cancel(
            data["P"][order] / sp.factorial(order)
        )
        for order in range(maximum_log_order + 1)
    ]
    q_series = [
        sp.cancel(
            data["Q"][order] / sp.factorial(order)
        )
        for order in range(maximum_log_order + 1)
    ]
    jacobian_series = [
        [
            [
                sp.diff(
                    (p_series, q_series)[component][order],
                    variable,
                )
                for order in range(maximum_log_order + 1)
            ]
            for variable in (v, t)
        ]
        for component in range(2)
    ]
    seed_jacobian = sp.Matrix([
        [jacobian_series[row][column][0] for column in range(2)]
        for row in range(2)
    ])
    family = {
        "bound": 0,
        "jacobian": seed_jacobian,
        "symbols": {"target": (p, q), "source": (v, t)},
    }

    base_hamiltonian = -q**2 / 4 - p**3 / 36
    base_target = _hamiltonian_field(
        base_hamiltonian, p, q
    )
    target_velocities: dict[int, Pair] = {0: base_target}
    source_velocities: dict[int, Pair] = {}
    target_series: dict[int, PairSeries] = {
        0: _field_at_family_series(
            base_target,
            p,
            q,
            p_series,
            q_series,
            maximum_velocity_order,
        )
    }
    source_series: dict[int, PairSeries] = {}
    solve_receipts: dict[str, object] = {}

    tangent = (
        p_series[1],
        q_series[1],
    )
    assert tangent == target_series[0][0]

    for velocity_order in range(1, maximum_velocity_order + 1):
        derivative_coefficient = (
            (velocity_order + 1)
            * p_series[velocity_order + 1],
            (velocity_order + 1)
            * q_series[velocity_order + 1],
        )
        known = [sp.Integer(0), sp.Integer(0)]
        for field_order, series in target_series.items():
            if field_order >= velocity_order:
                continue
            relative_order = velocity_order - field_order
            known[0] += series[relative_order][0]
            known[1] += series[relative_order][1]
        for field_order, series in source_series.items():
            if field_order >= velocity_order:
                continue
            relative_order = velocity_order - field_order
            known[0] += series[relative_order][0]
            known[1] += series[relative_order][1]
        residual: Pair = (
            sp.expand(derivative_coefficient[0] - known[0]),
            sp.expand(derivative_coefficient[1] - known[1]),
        )
        allowed_source_bound = 2 * velocity_order + 3
        selected_source_bound: int | None = None
        for candidate_bound in range(5, allowed_source_bound + 1):
            family["bound"] = candidate_bound
            try:
                source, hamiltonian, receipt = (
                    _solve_velocity_order(
                        logarithm_order=velocity_order + 1,
                        bound=candidate_bound,
                        residual=residual,
                        family=family,
                        data=data,
                        v=v,
                        t=t,
                        p=p,
                        q=q,
                    )
                )
            except ValueError:
                continue
            selected_source_bound = candidate_bound
            break
        if selected_source_bound is None:
            raise ValueError(
                "no source field exists inside the shifted "
                f"Rees bound {allowed_source_bound} at velocity "
                f"order {velocity_order}"
            )
        target = _hamiltonian_field(hamiltonian, p, q)
        assert _target_lift_ideals(target, p, q)
        source_velocities[velocity_order] = source
        target_velocities[velocity_order] = target
        target_series[velocity_order] = (
            _field_at_family_series(
                target,
                p,
                q,
                p_series,
                q_series,
                maximum_velocity_order - velocity_order,
            )
        )
        source_series[velocity_order] = (
            _source_response_series(
                source,
                jacobian_series,
                maximum_velocity_order - velocity_order,
            )
        )
        actual_degrees = [
            _source_degree(item, v, t) for item in source
        ]
        assert max(actual_degrees) <= selected_source_bound
        solve_receipts[str(velocity_order)] = {
            **receipt,
            "selected_source_degree_bound": (
                selected_source_bound
            ),
            "allowed_source_degree_bound": (
                allowed_source_bound
            ),
            "source_degrees": actual_degrees,
        }

    # Replay the infinitesimal contact equation coefficient by coefficient.
    for order in range(maximum_velocity_order + 1):
        predicted = [sp.Integer(0), sp.Integer(0)]
        for field_order, series in target_series.items():
            if field_order <= order:
                relative_order = order - field_order
                predicted[0] += series[relative_order][0]
                predicted[1] += series[relative_order][1]
        for field_order, series in source_series.items():
            if field_order <= order:
                relative_order = order - field_order
                predicted[0] += series[relative_order][0]
                predicted[1] += series[relative_order][1]
        actual = (
            (order + 1) * p_series[order + 1],
            (order + 1) * q_series[order + 1],
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                predicted, actual, strict=True
            )
        )

    return {
        "schema": "axiompack.jacobian_rees_velocity_prefix.v1",
        "maximum_log_order": maximum_log_order,
        "maximum_velocity_order": maximum_velocity_order,
        "fixed_target_hamiltonian_at_order_zero": str(
            base_hamiltonian
        ),
        "solve_receipts": solve_receipts,
        "source_velocity_degrees": {
            str(order): [
                _source_degree(item, v, t) for item in field
            ]
            for order, field in source_velocities.items()
        },
        "source_velocity_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in source_velocities.items()
        },
        "target_velocity_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in target_velocities.items()
        },
        "all_target_velocities_liftable": all(
            _target_lift_ideals(field, p, q)
            for field in target_velocities.values()
        ),
        "shifted_slope_two_bounds": {
            str(order): 2 * order + 3
            for order in source_velocities
        },
        "full_velocity_equation_replay": True,
        "claim_boundary": (
            "This is one exact particular Rees-velocity prefix. "
            "The filtered Lie integration lemma transfers it to a "
            "slope-two logarithmic prefix; no finite prefix proves "
            "all-order continuation."
        ),
    }


if __name__ == "__main__":
    selected_order = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(json.dumps(
        run(selected_order),
        indent=2,
        sort_keys=True,
    ))
