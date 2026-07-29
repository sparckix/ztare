#!/usr/bin/env python3
"""Exact sixth-order quotient over the complete c5=8 prefix family."""
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

from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _parameter_coefficients,
    _parameter_monomial,
    _parse_pair,
    _sha,
    _source_degree,
    _source_target_image,
    run as run_fifth,
)
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
    _particular_solution,
    _scale,
)


Pair = tuple[sp.Expr, sp.Expr]


def _top_part(
    value: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> sp.Expr:
    polynomial = sp.Poly(value, v, t, domain=sp.QQ)
    degree = polynomial.total_degree()
    return sp.factor(sum(
        coefficient * v**i * t**j
        for (i, j), coefficient in polynomial.terms()
        if i + j == degree
    ))


def _parse_generator(
    record: dict[str, object],
    target_locals: dict[str, sp.Symbol],
    source_locals: dict[str, sp.Symbol],
) -> tuple[Pair, sp.Expr]:
    return (
        _parse_pair(record["source"], source_locals),
        sp.sympify(record["hamiltonian"], locals=target_locals),
    )


def run(source_degree_bound_at_six: int = 8) -> dict[str, object]:
    fifth = run_fifth(8)
    family = fifth["complete_prefix_family"]
    assert family["dimension_through_five"] == 6

    data = _family_jets(6)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    a, b, c, d, e, f = sp.symbols("a b c d e f")
    parameters = (a, b, c, d, e, f)
    p0, q0 = data["P"][0], data["Q"][0]
    target_locals = {"P": p, "Q": q}
    source_locals = {"v": v, "t": t}

    base = family["through_three_base"]
    k2 = sp.sympify(base["K2"], locals=target_locals)
    k3 = sp.sympify(base["K3"], locals=target_locals)
    y2 = _parse_pair(base["Y2"], source_locals)
    y3 = _parse_pair(base["Y3"], source_locals)
    for parameter, direction in zip(
        (a, b), family["through_three_directions"], strict=True
    ):
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

    k4 = sp.Integer(0)
    y4: Pair = (sp.Integer(0), sp.Integer(0))
    for powers, record in zip(
        family["fourth_response_monomials"],
        family["fourth_particular_responses"],
        strict=True,
    ):
        source, hamiltonian = _parse_generator(
            record, target_locals, source_locals
        )
        scalar = _parameter_monomial(tuple(powers), (a, b))
        k4 += scalar * hamiltonian
        y4 = _add(y4, _scale(source, scalar))
    fourth_null = family["fourth_homogeneous_directions"]
    assert len(fourth_null) == 1
    null_source, null_hamiltonian = _parse_generator(
        fourth_null[0], target_locals, source_locals
    )
    k4 = sp.expand(k4 + c * null_hamiltonian)
    y4 = _add(y4, _scale(null_source, c))

    k5 = sp.Integer(0)
    y5: Pair = (sp.Integer(0), sp.Integer(0))
    for powers, record in zip(
        family["fifth_response_monomials"],
        family["fifth_particular_responses"],
        strict=True,
    ):
        source, hamiltonian = _parse_generator(
            record, target_locals, source_locals
        )
        scalar = _parameter_monomial(tuple(powers), (a, b, c))
        k5 += scalar * hamiltonian
        y5 = _add(y5, _scale(source, scalar))
    fifth_null = family["fifth_homogeneous_directions"]
    assert len(fifth_null) == 3
    for parameter, record in zip((d, e, f), fifth_null, strict=True):
        source, hamiltonian = _parse_generator(
            record, target_locals, source_locals
        )
        k5 += parameter * hamiltonian
        y5 = _add(y5, _scale(source, parameter))
    k5 = sp.expand(k5)

    target_fields = {
        1: _hamiltonian_field(
            -q**2 / 4 - p**3 / 36, p, q
        ),
        2: _hamiltonian_field(k2, p, q),
        3: _hamiltonian_field(k3, p, q),
        4: _hamiltonian_field(k4, p, q),
        5: _hamiltonian_field(k5, p, q),
    }
    source_fields = {2: y2, 3: y3, 4: y4, 5: y5}
    completed_five = _composed_series(
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

    predicted_six = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=6,
    )
    residual = (
        sp.expand(data["P"][6] - 720 * predicted_six[6][0]),
        sp.expand(data["Q"][6] - 720 * predicted_six[6][1]),
    )
    residual_monomials, residual_coefficients = _parameter_coefficients(
        residual, parameters
    )
    residual_degrees = [
        _source_degree(item, v, t) for item in residual
    ]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    columns, metadata, target_window = _source_target_image(
        source_order=6,
        source_degree_bound=source_degree_bound_at_six,
        first_target_degree=max(
            source_degree_bound_at_six + 3, residual_degrees[0]
        ),
        second_target_degree=max(
            source_degree_bound_at_six + 5, residual_degrees[1]
        ),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
    )
    combined, _zero, row_keys = _pair_system(
        columns + residual_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    image_count = len(columns)
    image = combined.extract(
        list(range(combined.shape[0])), list(range(image_count))
    )
    residual_matrix = combined.extract(
        list(range(combined.shape[0])),
        list(range(image_count, combined.shape[1])),
    )
    duals, image_rank, augmented_rank, chosen = _quotient_duals(
        image, residual_matrix
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
            coefficient * _parameter_monomial(
                monomial, parameters
            )
            for coefficient, monomial in zip(
                row, residual_monomials, strict=True
            )
        ))
        for row in pairings
    ]
    solutions = sp.solve(obstructions, parameters, dict=True)
    result: dict[str, object] = {
        "schema": "axiompack.jacobian_gauge_minimized_sixth_obstruction.v1",
        "source_degree_bound_at_six": source_degree_bound_at_six,
        "complete_degree_eight_prefix_dimension_through_five": 6,
        "parameters": [str(item) for item in parameters],
        "residual_component_degrees": residual_degrees,
        "residual_parameter_monomial_count": len(residual_monomials),
        "residual_parameter_monomials": [
            list(item) for item in residual_monomials
        ],
        "image_column_count": image.shape[1],
        "image_rank": image_rank,
        "image_plus_residual_rank": DomainMatrix.hstack(
            image, residual_matrix
        ).rank(),
        "quotient_dimension": augmented_rank - image_rank,
        "chosen_residual_coefficients": chosen,
        "target_window": target_window,
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
            "the lower family is the complete degree-eight prefix through "
            "five and the sixth target window is all-degree via C"
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
                    and not (value.free_symbols & set(parameters))
                    for value in solution.values()
                )
            ),
            None,
        )
    )
    if rational_solution is not None:
        substitution = {
            parameter: rational_solution.get(parameter, sp.Integer(0))
            for parameter in parameters
        }
        residual_at_solution = tuple(
            sp.expand(item.subs(substitution)) for item in residual
        )
        system, rhs, _rows = _pair_system(
            columns, residual_at_solution, v, t
        )
        vector = _particular_solution(system, rhs)
        y6, k6 = _decode_generator(
            vector, metadata, 6, v, t, p, q
        )
        target_at_solution = {
            order: tuple(
                sp.expand(item.subs(substitution)) for item in field
            )
            for order, field in target_fields.items()
        }
        source_at_solution = {
            order: tuple(
                sp.expand(item.subs(substitution)) for item in field
            )
            for order, field in source_fields.items()
        }
        target_at_solution[6] = _hamiltonian_field(k6, p, q)
        source_at_solution[6] = y6
        completed_six = _composed_series(
            target_fields=target_at_solution,
            source_fields=source_at_solution,
            p=p,
            q=q,
            v=v,
            t=t,
            p0=p0,
            q0=q0,
            maximum_order=6,
        )
        for order in range(7):
            actual = (
                data["P"][order] / sp.factorial(order),
                data["Q"][order] / sp.factorial(order),
            )
            assert all(
                sp.expand(left - right) == 0
                for left, right in zip(
                    completed_six[order], actual, strict=True
                )
            )
        result["rational_witness"] = {
            "parameters": {
                str(key): str(value)
                for key, value in substitution.items()
            },
            "K6": str(k6),
            "Y6": [str(item) for item in y6],
            "K6_sha256": _sha(k6),
            "Y6_sha256": [_sha(item) for item in y6],
            "Y6_degrees": [
                _source_degree(item, v, t) for item in y6
            ],
            "Y6_top": [
                str(_top_part(item, v, t)) for item in y6
            ],
            "full_prefix_replay": True,
            "matrix_sha256": _matrix_sha(system),
            "rhs_sha256": _matrix_sha(rhs),
        }
        exceptional_shell = v * (2 * t - 3 * v)
        result["source_top_shells"] = {
            str(order): {
                "degree": [
                    _source_degree(item, v, t)
                    for item in source_at_solution[order]
                ],
                "top": [
                    str(_top_part(item, v, t))
                    for item in source_at_solution[order]
                ],
                "after_dividing_r_power": [
                    str(sp.factor(
                        _top_part(item, v, t)
                        / exceptional_shell ** max(order - 2, 0)
                    ))
                    for item in source_at_solution[order]
                ],
            }
            for order in range(2, 7)
        }
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
