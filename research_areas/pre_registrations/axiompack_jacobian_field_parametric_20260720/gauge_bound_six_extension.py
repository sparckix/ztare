#!/usr/bin/env python3
"""Construct and replay a degree-eight compatible prefix through order six."""
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

from gauge_bound_five_extension import build_through_five  # noqa: E402
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _parameter_coefficients,
    _parameter_monomial,
    _source_degree,
    _source_target_image,
    _target_lift_ideals,
)
from gauge_minimized_fourth_jet import _family_jets, _pair_system  # noqa: E402
from gauge_minimized_fourth_obstruction import _quotient_duals  # noqa: E402
from gauge_minimized_recursive_prefix import (  # noqa: E402
    _composed_parameter_series,
    _composed_series,
    _parameter_residual_coefficients,
    _substitute_parameter_coordinates,
)
from gauge_minimized_third_jet import (  # noqa: E402
    _add,
    _hamiltonian_field,
    _particular_solution,
    _scale,
    _substitute,
)


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def _add_scaled_pair(
    base: Pair, direction: Pair, scalar: sp.Expr
) -> Pair:
    return _add(base, _scale(direction, scalar))


def build_through_six(
    bound: int = 8,
    lower_family: dict[str, object] | None = None,
) -> dict[str, object]:
    family = (
        build_through_five(bound)
        if lower_family is None
        else lower_family
    )
    if family["bound"] != bound:
        raise ValueError(
            "the supplied through-five family has a different bound"
        )
    data = _family_jets(6)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    p0, q0 = data["P"][0], data["Q"][0]
    parameters = family["complete_parameters_through_five"]
    target_fields = family["target_fields"]
    source_fields = family["source_fields"]

    predicted = _composed_parameter_series(
        target_fields=target_fields,
        source_fields=source_fields,
        parameters=parameters,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=6,
    )
    residual_monomials, residual_coefficients = (
        _parameter_residual_coefficients(
            predicted=predicted[6],
            actual=(data["P"][6], data["Q"][6]),
            scale=sp.factorial(6),
            parameter_count=len(parameters),
            coefficient_variables=(v, t),
        )
    )
    residual_degrees = [
        max(
            (
                _source_degree(pair[component], v, t)
                for pair in residual_coefficients
            ),
            default=-1,
        )
        for component in range(2)
    ]
    columns, metadata, target_window = _source_target_image(
        source_order=6,
        source_degree_bound=bound,
        first_target_degree=max(bound + 3, residual_degrees[0]),
        second_target_degree=max(bound + 5, residual_degrees[1]),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=family["jacobian"],
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
    duals, _rank, _augmented, _chosen = _quotient_duals(
        image, residual_matrix
    )
    dense = residual_matrix.to_Matrix()
    obstructions = [
        sp.factor(sum(
            sp.cancel((dense[:, index].transpose() * dual)[0])
            * _parameter_monomial(monomial, parameters)
            for index, monomial in enumerate(residual_monomials)
        ))
        for dual in duals
    ]
    solutions = sp.solve(obstructions, parameters, dict=True)
    if len(solutions) != 1:
        raise ValueError(
            f"expected one rational compatibility branch, got {solutions}"
        )
    compatibility_solution = {
        key: sp.expand(value)
        for key, value in solutions[0].items()
    }
    if not all(
        value.is_rational is True
        or value.free_symbols
        for value in compatibility_solution.values()
    ):
        raise ValueError("the sixth compatibility branch is not rational")
    compatible_parameters = tuple(
        parameter
        for parameter in parameters
        if parameter not in compatibility_solution
    )
    target_fields = {
        order: tuple(
            sp.expand(item.subs(compatibility_solution))
            for item in field
        )
        for order, field in target_fields.items()
    }
    source_fields = {
        order: tuple(
            sp.expand(item.subs(compatibility_solution))
            for item in field
        )
        for order, field in source_fields.items()
    }
    residual_monomials, residual_coefficients = (
        _substitute_parameter_coordinates(
            monomials=residual_monomials,
            coefficients=residual_coefficients,
            old_parameters=parameters,
            substitution=compatibility_solution,
            new_parameters=compatible_parameters,
        )
    )
    compatible_combined, _zero, compatible_row_keys = _pair_system(
        columns + residual_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    image = compatible_combined.extract(
        list(range(compatible_combined.shape[0])),
        list(range(image_count)),
    )
    residual_matrix = compatible_combined.extract(
        list(range(compatible_combined.shape[0])),
        list(range(image_count, compatible_combined.shape[1])),
    )
    assert DomainMatrix.hstack(
        image, residual_matrix
    ).rank() == image.rank()
    particulars = [
        _particular_solution(
            image,
            residual_matrix.extract(
                list(range(residual_matrix.shape[0])), [index]
            ),
        )
        for index in range(residual_matrix.shape[1])
    ]
    nullspace = image.to_Matrix().nullspace()
    new_parameters = sp.symbols(f"d0:{len(nullspace)}")
    y6: Pair = (sp.Integer(0), sp.Integer(0))
    k6 = sp.Integer(0)
    for monomial, vector in zip(
        residual_monomials, particulars, strict=True
    ):
        response_y6, response_k6 = _decode_generator(
            vector, metadata, 6, v, t, p, q
        )
        scalar = _parameter_monomial(
            monomial, compatible_parameters
        )
        y6 = _add_scaled_pair(y6, response_y6, scalar)
        k6 += scalar * response_k6
    for parameter, vector in zip(
        new_parameters, nullspace, strict=True
    ):
        response_y6, response_k6 = _decode_generator(
            vector, metadata, 6, v, t, p, q
        )
        y6 = _add_scaled_pair(y6, response_y6, parameter)
        k6 += parameter * response_k6
    y6 = sp.expand(y6[0]), sp.expand(y6[1])
    k6 = sp.expand(k6)
    target_fields[6] = _hamiltonian_field(k6, p, q)
    source_fields[6] = y6
    target_response = _substitute(
        target_fields[6], p, q, p0, q0
    )
    direct_response = (
        sp.expand(
            family["jacobian"][0, 0] * y6[0]
            + family["jacobian"][0, 1] * y6[1]
            + target_response[0]
        ),
        sp.expand(
            family["jacobian"][1, 0] * y6[0]
            + family["jacobian"][1, 1] * y6[1]
            + target_response[1]
        ),
    )
    direct_monomials, direct_coefficients = _parameter_coefficients(
        direct_response, compatible_parameters
    )
    assert direct_monomials == residual_monomials
    assert all(
        sp.expand(left - right) == 0
        for direct_pair, residual_pair in zip(
            direct_coefficients,
            residual_coefficients,
            strict=True,
        )
        for left, right in zip(
            direct_pair, residual_pair, strict=True
        )
    )
    return {
        "bound": bound,
        "lower_family": family,
        "data": data,
        "symbols": family["symbols"],
        "jacobian": family["jacobian"],
        "compatibility_obstructions": obstructions,
        "compatibility_solution": compatibility_solution,
        "compatible_parameters_through_five": compatible_parameters,
        "parameters_at_six": new_parameters,
        "complete_parameters_through_six": (
            *compatible_parameters, *new_parameters
        ),
        "target_fields": target_fields,
        "source_fields": source_fields,
        "K6": k6,
        "Y6": y6,
        "sixth_nullspace": nullspace,
        "sixth_target_window": target_window,
        "sixth_row_keys": compatible_row_keys,
    }


def run(bound: int = 8) -> dict[str, object]:
    family = build_through_six(bound)
    parameters = family["complete_parameters_through_six"]
    substitution = {
        parameter: sp.Integer(0) for parameter in parameters
    }
    target_fields = {
        order: tuple(
            sp.expand(item.subs(substitution))
            for item in field
        )
        for order, field in family["target_fields"].items()
    }
    source_fields = {
        order: tuple(
            sp.expand(item.subs(substitution))
            for item in field
        )
        for order, field in family["source_fields"].items()
    }
    data = family["data"]
    v, t = family["symbols"]["source"]
    p, q = family["symbols"]["target"]
    target_lift_checks = {
        str(order): _target_lift_ideals(field, p, q)
        for order, field in target_fields.items()
    }
    assert all(target_lift_checks.values())
    completed = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
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
                completed[order], actual, strict=True
            )
        )
    return {
        "schema": "axiompack.jacobian_fixed_bound_six_extension.v1",
        "bound": bound,
        "dimension_through_five_before_sixth_constraints": len(
            family["lower_family"][
                "complete_parameters_through_five"
            ]
        ),
        "sixth_compatibility_obstructions": [
            str(item)
            for item in family["compatibility_obstructions"]
        ],
        "sixth_compatibility_parameterization": {
            str(key): str(value)
            for key, value in family[
                "compatibility_solution"
            ].items()
        },
        "compatible_dimension_through_five": len(
            family["compatible_parameters_through_five"]
        ),
        "dimension_at_six": len(family["parameters_at_six"]),
        "dimension_through_six": len(parameters),
        "witness": {
            "target_field_sha256": {
                str(order): [_sha(item) for item in field]
                for order, field in target_fields.items()
            },
            "source_field_sha256": {
                str(order): [_sha(item) for item in field]
                for order, field in source_fields.items()
            },
            "source_field_degrees": {
                str(order): [
                    _source_degree(
                        item, *family["symbols"]["source"]
                    )
                    for item in field
                ]
                for order, field in source_fields.items()
            },
            "target_three_variable_lift_ideals": target_lift_checks,
            "full_prefix_replay": True,
        },
        "sixth_target_window": family["sixth_target_window"],
        "claim": "an explicit source-degree-eight prefix reaches order six",
    }


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(json.dumps(run(selected_bound), indent=2, sort_keys=True))
