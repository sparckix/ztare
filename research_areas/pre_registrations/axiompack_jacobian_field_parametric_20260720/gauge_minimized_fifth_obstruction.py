#!/usr/bin/env python3
"""Exact fifth-order obstruction over the complete degree-six prefix family."""
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

from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _matrix_sha,
    _pair_system,
)
from gauge_minimized_fourth_obstruction import (  # noqa: E402
    _primitive_dual_support,
    _quotient_duals,
)
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _add,
    _hamiltonian_field,
    _hamiltonian_field_window,
    _monomials,
    _particular_solution,
    _scale,
    _substitute,
    run as run_third,
)


Pair = tuple[sp.Expr, sp.Expr]


def _parse_pair(
    values: list[str], locals_: dict[str, sp.Symbol]
) -> Pair:
    return tuple(
        sp.sympify(value, locals=locals_) for value in values
    )  # type: ignore[return-value]


def _parameter_coefficients(
    pair: Pair,
    parameters: tuple[sp.Symbol, ...],
) -> tuple[list[tuple[int, ...]], list[Pair]]:
    polynomials = [
        sp.Poly(item, *parameters) for item in pair
    ]
    monomials = sorted({
        monomial
        for polynomial in polynomials
        for monomial in polynomial.monoms()
    })
    coefficients = [
        tuple(
            sp.expand(polynomial.coeff_monomial(monomial))
            for polynomial in polynomials
        )
        for monomial in monomials
    ]
    return monomials, coefficients  # type: ignore[return-value]


def _parameter_monomial(
    powers: tuple[int, ...], parameters: tuple[sp.Symbol, ...]
) -> sp.Expr:
    return sp.prod(
        parameter**power
        for parameter, power in zip(parameters, powers, strict=True)
    )


def _decode_generator(
    vector: sp.Matrix,
    metadata: list[dict[str, object]],
    source_order: int,
    v: sp.Symbol,
    t: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
) -> tuple[Pair, sp.Expr]:
    source = [sp.Integer(0), sp.Integer(0)]
    hamiltonian = sp.Integer(0)
    for coefficient, item in zip(vector, metadata, strict=True):
        if item["kind"] == f"Y{source_order}":
            i, j = item["monomial"]
            source[int(item["component"])] += (
                coefficient * v**int(i) * t**int(j)
            )
        else:
            hamiltonian += coefficient * item["hamiltonian"]
    return (
        (sp.expand(source[0]), sp.expand(source[1])),
        sp.expand(hamiltonian),
    )


def _source_target_image(
    *,
    source_order: int,
    source_degree_bound: int,
    first_target_degree: int,
    second_target_degree: int,
    v: sp.Symbol,
    t: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    jacobian: sp.Matrix,
) -> tuple[list[Pair], list[dict[str, object]], dict[str, object]]:
    columns: list[Pair] = []
    metadata: list[dict[str, object]] = []
    for component in range(2):
        forbidden = (
            {(0, 0)} if component == 0 else {(0, 0), (1, 0)}
        )
        for i, j in _monomials(source_degree_bound):
            if (i, j) in forbidden:
                continue
            monomial = v**i * t**j
            columns.append((
                sp.expand(jacobian[0, component] * monomial),
                sp.expand(jacobian[1, component] * monomial),
            ))
            metadata.append({
                "kind": f"Y{source_order}",
                "component": component,
                "monomial": [i, j],
            })
    target_basis, first_scalar_basis, second_scalar_basis = (
        _hamiltonian_field_window(
            first_target_degree,
            second_target_degree,
            p,
            q,
        )
    )
    for hamiltonian, field in target_basis:
        columns.append(_substitute(field, p, q, p0, q0))
        metadata.append({
            "kind": f"K{source_order}",
            "hamiltonian": hamiltonian,
        })
    return columns, metadata, {
        "target_field_dimension": len(target_basis),
        "first_scalar_basis": [str(item) for item in first_scalar_basis],
        "second_scalar_basis": [str(item) for item in second_scalar_basis],
    }


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def _source_degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t).total_degree())


def _target_lift_ideals(
    field: Pair, p: sp.Symbol, q: sp.Symbol
) -> bool:
    """Whether a quotient target field lifts equivariantly in three variables."""
    first = sp.Poly(sp.expand(field[0]), p, q, domain=sp.QQ)
    second = sp.Poly(sp.expand(field[1]), p, q, domain=sp.QQ)
    first_ok = first.coeff_monomial(1) == 0
    second_ok = (
        second.coeff_monomial(1) == 0
        and second.coeff_monomial(p) == 0
    )
    return first_ok and second_ok


def run(source_degree_bound_at_five: int = 6) -> dict[str, object]:
    third = run_third(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=1,
        all_degree_target_window=True,
    )
    assert third["solution_affine_dimension"] == 2
    witness = third["witness"]
    directions = third["homogeneous_directions"]

    data = _family_jets(5)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    a, b, c = sp.symbols("a b c")
    p0, q0 = data["P"][0], data["Q"][0]
    target_locals = {"P": p, "Q": q}
    source_locals = {"v": v, "t": t}

    k2 = sp.sympify(witness["K2"], locals=target_locals)
    k3 = sp.sympify(witness["K3"], locals=target_locals)
    y2 = _parse_pair(witness["Y2"], source_locals)
    y3 = _parse_pair(witness["Y3"], source_locals)
    for parameter, direction in zip((a, b), directions, strict=True):
        k2 += parameter * sp.sympify(
            direction["K2"], locals=target_locals
        )
        k3 += parameter * sp.sympify(
            direction["K3"], locals=target_locals
        )
        y2 = _add(
            y2,
            _scale(
                _parse_pair(direction["Y2"], source_locals),
                parameter,
            ),
        )
        y3 = _add(
            y3,
            _scale(
                _parse_pair(direction["Y3"], source_locals),
                parameter,
            ),
        )

    target_fields = {
        1: _hamiltonian_field(
            -q**2 / 4 - p**3 / 36, p, q
        ),
        2: _hamiltonian_field(k2, p, q),
        3: _hamiltonian_field(k3, p, q),
    }
    source_fields = {2: y2, 3: y3}
    predicted_four = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=4,
    )
    residual_four = (
        sp.expand(data["P"][4] - 24 * predicted_four[4][0]),
        sp.expand(data["Q"][4] - 24 * predicted_four[4][1]),
    )
    lower_parameters = (a, b)
    lower_monomials, residual_four_coefficients = _parameter_coefficients(
        residual_four, lower_parameters
    )
    assert lower_monomials == [(0, 0), (0, 1), (1, 0)]

    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    fourth_columns, fourth_metadata, fourth_window = (
        _source_target_image(
            source_order=4,
            source_degree_bound=6,
            first_target_degree=12,
            second_target_degree=14,
            v=v,
            t=t,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            jacobian=jacobian,
        )
    )
    combined_four, _zero, _rows_four = _pair_system(
        fourth_columns + residual_four_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    fourth_count = len(fourth_columns)
    fourth_matrix = combined_four.extract(
        list(range(combined_four.shape[0])),
        list(range(fourth_count)),
    )
    fourth_rhs_columns = combined_four.extract(
        list(range(combined_four.shape[0])),
        list(range(fourth_count, combined_four.shape[1])),
    )
    assert DomainMatrix.hstack(
        fourth_matrix, fourth_rhs_columns
    ).rank() == fourth_matrix.rank()
    fourth_particulars = [
        _particular_solution(
            fourth_matrix,
            fourth_rhs_columns.extract(
                list(range(fourth_rhs_columns.shape[0])), [index]
            ),
        )
        for index in range(fourth_rhs_columns.shape[1])
    ]
    fourth_nullspace = fourth_matrix.to_Matrix().nullspace()
    assert len(fourth_nullspace) == 1

    y4 = (sp.Integer(0), sp.Integer(0))
    k4 = sp.Integer(0)
    for monomial, vector in zip(
        lower_monomials, fourth_particulars, strict=True
    ):
        direction_y4, direction_k4 = _decode_generator(
            vector, fourth_metadata, 4, v, t, p, q
        )
        scalar = _parameter_monomial(monomial, lower_parameters)
        y4 = _add(y4, _scale(direction_y4, scalar))
        k4 += scalar * direction_k4
    null_y4, null_k4 = _decode_generator(
        fourth_nullspace[0], fourth_metadata, 4, v, t, p, q
    )
    y4 = _add(y4, _scale(null_y4, c))
    k4 = sp.expand(k4 + c * null_k4)
    target_fields[4] = _hamiltonian_field(k4, p, q)
    source_fields[4] = y4

    completed_four = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=4,
    )
    assert all(
        sp.expand(
            completed_four[4][component]
            - data[("P", "Q")[component]][4] / 24
        ) == 0
        for component in range(2)
    )

    predicted_five = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=5,
    )
    residual_five = (
        sp.expand(data["P"][5] - 120 * predicted_five[5][0]),
        sp.expand(data["Q"][5] - 120 * predicted_five[5][1]),
    )
    prefix_parameters = (a, b, c)
    residual_monomials, residual_coefficients = _parameter_coefficients(
        residual_five, prefix_parameters
    )
    residual_degrees = [
        _source_degree(item, v, t) for item in residual_five
    ]
    fifth_columns, fifth_metadata, fifth_window = _source_target_image(
        source_order=5,
        source_degree_bound=source_degree_bound_at_five,
        first_target_degree=max(
            source_degree_bound_at_five + 3, residual_degrees[0]
        ),
        second_target_degree=max(
            source_degree_bound_at_five + 5, residual_degrees[1]
        ),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
    )
    combined_five, _zero, row_keys = _pair_system(
        fifth_columns + residual_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    fifth_count = len(fifth_columns)
    fifth_matrix = combined_five.extract(
        list(range(combined_five.shape[0])), list(range(fifth_count))
    )
    residual_matrix = combined_five.extract(
        list(range(combined_five.shape[0])),
        list(range(fifth_count, combined_five.shape[1])),
    )
    duals, image_rank, augmented_rank, chosen_residuals = (
        _quotient_duals(fifth_matrix, residual_matrix)
    )
    residual_dense = residual_matrix.to_Matrix()
    pairings = [
        [
            sp.cancel(
                (residual_dense[:, index].transpose() * dual)[0]
            )
            for index in range(residual_matrix.shape[1])
        ]
        for dual in duals
    ]
    obstructions = [
        sp.factor(sum(
            coefficient
            * _parameter_monomial(monomial, prefix_parameters)
            for coefficient, monomial in zip(
                row, residual_monomials, strict=True
            )
        ))
        for row in pairings
    ]
    solutions = sp.solve(obstructions, prefix_parameters, dict=True)

    result: dict[str, object] = {
        "schema": "axiompack.jacobian_gauge_minimized_fifth_obstruction.v1",
        "source_degree_bound_at_five": source_degree_bound_at_five,
        "complete_degree_six_prefix_dimension_through_four": 3,
        "prefix_parameters": ["a", "b", "c"],
        "fourth_image_rank": fourth_matrix.rank(),
        "fourth_image_nullity": len(fourth_nullspace),
        "fourth_target_window": fourth_window,
        "fifth_residual_component_degrees": residual_degrees,
        "fifth_residual_parameter_monomials": [
            list(item) for item in residual_monomials
        ],
        "fifth_image_column_count": fifth_matrix.shape[1],
        "fifth_image_rank": image_rank,
        "fifth_image_plus_residual_rank": DomainMatrix.hstack(
            fifth_matrix, residual_matrix
        ).rank(),
        "fifth_quotient_dimension": augmented_rank - image_rank,
        "fifth_chosen_residual_coefficients": chosen_residuals,
        "fifth_target_window": fifth_window,
        "compatibility_obstructions": [
            str(item) for item in obstructions
        ],
        "obstruction_factorizations": [
            str(sp.factor(item)) for item in obstructions
        ],
        "dual_certificates": [
            _primitive_dual_support(dual, row_keys) for dual in duals
        ],
        "solutions": [
            {str(key): str(value) for key, value in solution.items()}
            for solution in solutions
        ],
        "row_key_sha256": hashlib.sha256(
            json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "claim_boundary": (
            "all polynomial Hamiltonian fifth generators are included by "
            "the C-normal-form component window; the lower prefix family is "
            "the complete degree-six family through order four"
        ),
    }

    if not obstructions:
        fifth_particulars = [
            _particular_solution(
                fifth_matrix,
                residual_matrix.extract(
                    list(range(residual_matrix.shape[0])), [index]
                ),
            )
            for index in range(residual_matrix.shape[1])
        ]
        fifth_nullspace = fifth_matrix.to_Matrix().nullspace()

        def encoded_generator(
            vector: sp.Matrix,
            metadata: list[dict[str, object]],
            order: int,
        ) -> dict[str, object]:
            source, hamiltonian = _decode_generator(
                vector, metadata, order, v, t, p, q
            )
            return {
                "hamiltonian": str(hamiltonian),
                "source": [str(item) for item in source],
                "hamiltonian_sha256": _sha(hamiltonian),
                "source_sha256": [_sha(item) for item in source],
            }

        result["complete_prefix_family"] = {
            "parameters_through_three": ["a", "b"],
            "through_three_base": {
                "K2": witness["K2"],
                "K3": witness["K3"],
                "Y2": witness["Y2"],
                "Y3": witness["Y3"],
            },
            "through_three_directions": directions,
            "fourth_response_monomials": [
                list(item) for item in lower_monomials
            ],
            "fourth_particular_responses": [
                encoded_generator(vector, fourth_metadata, 4)
                for vector in fourth_particulars
            ],
            "fourth_homogeneous_directions": [
                encoded_generator(vector, fourth_metadata, 4)
                for vector in fourth_nullspace
            ],
            "fifth_response_monomials": [
                list(item) for item in residual_monomials
            ],
            "fifth_particular_responses": [
                encoded_generator(vector, fifth_metadata, 5)
                for vector in fifth_particulars
            ],
            "fifth_homogeneous_directions": [
                encoded_generator(vector, fifth_metadata, 5)
                for vector in fifth_nullspace
            ],
            "dimension_through_five": (
                2 + len(fourth_nullspace) + len(fifth_nullspace)
            ),
        }

    rational_solution = (
        {}
        if not obstructions
        else next(
            (
                solution
                for solution in solutions
                if all(
                    value.is_rational is True
                    and not (
                        value.free_symbols & set(prefix_parameters)
                    )
                    for value in solution.values()
                )
            ),
            None,
        )
    )
    if rational_solution is not None:
        full_substitution = {
            parameter: rational_solution.get(parameter, sp.Integer(0))
            for parameter in prefix_parameters
        }
        residual_at_solution = tuple(
            sp.expand(item.subs(full_substitution))
            for item in residual_five
        )
        fifth_system, fifth_rhs, _rows = _pair_system(
            fifth_columns,
            residual_at_solution,
            v,
            t,
        )
        vector = _particular_solution(fifth_system, fifth_rhs)
        y5, k5 = _decode_generator(
            vector, fifth_metadata, 5, v, t, p, q
        )
        target_fields_at_solution = {
            order: tuple(
                sp.expand(item.subs(full_substitution))
                for item in field
            )
            for order, field in target_fields.items()
        }
        source_fields_at_solution = {
            order: tuple(
                sp.expand(item.subs(full_substitution))
                for item in field
            )
            for order, field in source_fields.items()
        }
        target_fields_at_solution[5] = _hamiltonian_field(k5, p, q)
        source_fields_at_solution[5] = y5
        completed_five = _composed_series(
            target_fields=target_fields_at_solution,
            source_fields=source_fields_at_solution,
            p=p,
            q=q,
            v=v,
            t=t,
            p0=p0,
            q0=q0,
            maximum_order=5,
        )
        for order in range(6):
            actual = (
                data["P"][order] / sp.factorial(order),
                data["Q"][order] / sp.factorial(order),
            )
            assert all(
                sp.expand(left - right) == 0
                for left, right in zip(
                    completed_five[order], actual, strict=True
                )
            )
        result["rational_witness"] = {
            "parameters": {
                str(key): str(value)
                for key, value in full_substitution.items()
            },
            "K5": str(k5),
            "Y5": [str(item) for item in y5],
            "K5_sha256": _sha(k5),
            "Y5_sha256": [_sha(item) for item in y5],
            "Y5_degrees": [
                _source_degree(item, v, t) for item in y5
            ],
            "full_prefix_replay": True,
            "matrix_sha256": _matrix_sha(fifth_system),
            "rhs_sha256": _matrix_sha(fifth_rhs),
        }
        carried_hamiltonians = {
            2: sp.expand(k2.subs(full_substitution)),
            3: sp.expand(k3.subs(full_substitution)),
            4: sp.expand(k4.subs(full_substitution)),
            5: sp.expand(k5),
        }
        carried_sources = {
            2: tuple(
                sp.expand(item.subs(full_substitution)) for item in y2
            ),
            3: tuple(
                sp.expand(item.subs(full_substitution)) for item in y3
            ),
            4: tuple(
                sp.expand(item.subs(full_substitution)) for item in y4
            ),
            5: y5,
        }
        result["carried_prefix"] = {
            "hamiltonians": {
                str(order): str(value)
                for order, value in carried_hamiltonians.items()
            },
            "source_fields": {
                str(order): [str(item) for item in value]
                for order, value in carried_sources.items()
            },
            "hamiltonian_sha256": {
                str(order): _sha(value)
                for order, value in carried_hamiltonians.items()
            },
            "source_field_sha256": {
                str(order): [_sha(item) for item in value]
                for order, value in carried_sources.items()
            },
        }
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
