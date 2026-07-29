#!/usr/bin/env python3
"""Extend the complete fixed-bound prefix family through order four."""
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

from gauge_bound_prefix_search import build_through_three  # noqa: E402
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _parameter_coefficients,
    _parameter_monomial,
    _source_degree,
    _source_target_image,
)
from gauge_minimized_fourth_jet import _family_jets, _pair_system  # noqa: E402
from gauge_minimized_fourth_obstruction import (  # noqa: E402
    _primitive_dual_support,
    _quotient_duals,
)
from gauge_minimized_recursive_prefix import (  # noqa: E402
    _composed_parameter_series,
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


def build_through_four(bound: int = 7) -> dict[str, object]:
    prefix = build_through_three(bound)
    data = _family_jets(5)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p0, q0 = data["P"][0], data["Q"][0]
    parameters = sp.symbols(f"a0:{prefix['nullity']}")

    particular = prefix["particular"]
    k2 = particular["K2"]
    k3 = particular["K3"]
    y2 = particular["Y2"]
    y3 = particular["Y3"]
    for parameter, direction in zip(
        parameters, prefix["directions"], strict=True
    ):
        k2 += parameter * direction["K2"]
        k3 += parameter * direction["K3"]
        y2 = _add_scaled_pair(y2, direction["Y2"], parameter)
        y3 = _add_scaled_pair(y3, direction["Y3"], parameter)
    k2 = sp.expand(k2)
    k3 = sp.expand(k3)

    target_fields = {
        1: _hamiltonian_field(-q**2 / 4 - p**3 / 36, p, q),
        2: _hamiltonian_field(k2, p, q),
        3: _hamiltonian_field(k3, p, q),
    }
    source_fields = {2: y2, 3: y3}
    through_three = _composed_parameter_series(
        target_fields=target_fields,
        source_fields=source_fields,
        parameters=parameters,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=3,
    )
    for order in range(4):
        _monomials_at_order, coefficients_at_order = (
            _parameter_residual_coefficients(
                predicted=through_three[order],
                actual=(data["P"][order], data["Q"][order]),
                scale=sp.factorial(order),
                parameter_count=len(parameters),
                coefficient_variables=(v, t),
            )
        )
        assert all(
            item == 0
            for pair in coefficients_at_order
            for item in pair
        )

    predicted_four = _composed_parameter_series(
        target_fields=target_fields,
        source_fields=source_fields,
        parameters=parameters,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=4,
    )
    residual_monomials, residual_coefficients = (
        _parameter_residual_coefficients(
            predicted=predicted_four[4],
            actual=(data["P"][4], data["Q"][4]),
            scale=sp.factorial(4),
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

    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    columns, metadata, target_window = _source_target_image(
        source_order=4,
        source_degree_bound=bound,
        first_target_degree=max(bound + 3, residual_degrees[0]),
        second_target_degree=max(bound + 5, residual_degrees[1]),
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
            coefficient * _parameter_monomial(monomial, parameters)
            for coefficient, monomial in zip(
                row, residual_monomials, strict=True
            )
        ))
        for row in pairings
    ]

    result: dict[str, object] = {
        "bound": bound,
        "prefix": prefix,
        "data": data,
        "symbols": {"source": (v, t), "target": (p, q)},
        "jacobian": jacobian,
        "parameters_through_three": parameters,
        "target_fields": target_fields,
        "source_fields": source_fields,
        "residual_four_coefficients": residual_coefficients,
        "residual_four_degrees": residual_degrees,
        "residual_four_monomials": residual_monomials,
        "fourth_columns": columns,
        "fourth_metadata": metadata,
        "fourth_image": image,
        "fourth_residual_matrix": residual_matrix,
        "fourth_row_keys": row_keys,
        "fourth_image_rank": image_rank,
        "fourth_augmented_rank": augmented_rank,
        "fourth_chosen_residuals": chosen,
        "fourth_target_window": target_window,
        "fourth_obstructions": obstructions,
        "fourth_duals": duals,
    }
    compatibility_solution: dict[sp.Symbol, sp.Expr] = {}
    compatible_parameters = parameters
    if obstructions:
        solutions = sp.solve(obstructions, parameters, dict=True)
        if len(solutions) != 1:
            result["compatibility_solutions"] = solutions
            return result
        compatibility_solution = {
            key: sp.expand(value)
            for key, value in solutions[0].items()
        }
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
        compatible_combined, _zero, compatible_row_keys = (
            _pair_system(
                columns + residual_coefficients,
                (sp.Integer(0), sp.Integer(0)),
                v,
                t,
            )
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
        result.update({
            "compatibility_solution": compatibility_solution,
            "compatible_parameters_through_three": (
                compatible_parameters
            ),
            "compatible_residual_four_coefficients": (
                residual_coefficients
            ),
            "compatible_residual_four_monomials": (
                residual_monomials
            ),
            "compatible_fourth_image": image,
            "compatible_fourth_residual_matrix": residual_matrix,
            "compatible_fourth_row_keys": compatible_row_keys,
        })

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
    new_parameters = sp.symbols(f"b0:{len(nullspace)}")
    y4: Pair = (sp.Integer(0), sp.Integer(0))
    k4 = sp.Integer(0)
    for monomial, vector in zip(
        residual_monomials, particulars, strict=True
    ):
        response_y4, response_k4 = _decode_generator(
            vector, metadata, 4, v, t, p, q
        )
        scalar = _parameter_monomial(
            monomial, compatible_parameters
        )
        y4 = _add_scaled_pair(y4, response_y4, scalar)
        k4 += scalar * response_k4
    for parameter, vector in zip(
        new_parameters, nullspace, strict=True
    ):
        response_y4, response_k4 = _decode_generator(
            vector, metadata, 4, v, t, p, q
        )
        y4 = _add_scaled_pair(y4, response_y4, parameter)
        k4 += parameter * response_k4
    y4 = sp.expand(y4[0]), sp.expand(y4[1])
    k4 = sp.expand(k4)
    target_fields[4] = _hamiltonian_field(k4, p, q)
    source_fields[4] = y4
    target_response = _substitute(
        target_fields[4], p, q, p0, q0
    )
    direct_response = (
        sp.expand(
            jacobian[0, 0] * y4[0]
            + jacobian[0, 1] * y4[1]
            + target_response[0]
        ),
        sp.expand(
            jacobian[1, 0] * y4[0]
            + jacobian[1, 1] * y4[1]
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
    result.update({
        "target_fields": target_fields,
        "source_fields": source_fields,
        "compatibility_solution": compatibility_solution,
        "compatible_parameters_through_three": compatible_parameters,
        "compatible_residual_four_coefficients": residual_coefficients,
        "compatible_residual_four_monomials": residual_monomials,
        "compatible_fourth_image": image,
        "compatible_fourth_residual_matrix": residual_matrix,
        "parameters_at_four": new_parameters,
        "fourth_particulars": particulars,
        "fourth_nullspace": nullspace,
        "K4": k4,
        "Y4": y4,
        "complete_parameters_through_four": (
            *compatible_parameters, *new_parameters
        ),
    })
    return result


def run(bound: int = 7) -> dict[str, object]:
    family = build_through_four(bound)
    obstructions = family["fourth_obstructions"]
    result: dict[str, object] = {
        "schema": "axiompack.jacobian_fixed_bound_four_extension.v1",
        "bound": bound,
        "dimension_through_three": family["prefix"]["nullity"],
        "fourth_residual_component_degrees": (
            family["residual_four_degrees"]
        ),
        "fourth_residual_parameter_monomials": [
            list(item) for item in family["residual_four_monomials"]
        ],
        "fourth_image_rank": family["fourth_image_rank"],
        "fourth_image_plus_residual_rank": (
            family["fourth_augmented_rank"]
        ),
        "fourth_quotient_dimension": (
            family["fourth_augmented_rank"]
            - family["fourth_image_rank"]
        ),
        "fourth_target_window": family["fourth_target_window"],
        "compatibility_obstructions": [
            str(item) for item in obstructions
        ],
        "dual_certificates": [
            _primitive_dual_support(
                dual, family["fourth_row_keys"]
            )
            for dual in family["fourth_duals"]
        ],
        "row_key_sha256": hashlib.sha256(
            json.dumps(
                family["fourth_row_keys"], separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
    }
    if "complete_parameters_through_four" in family:
        result.update({
            "compatibility_parameterization": {
                str(key): str(value)
                for key, value in family[
                    "compatibility_solution"
                ].items()
            },
            "compatible_dimension_through_three": len(
                family["compatible_parameters_through_three"]
            ),
            "dimension_at_four": len(family["fourth_nullspace"]),
            "dimension_through_four": len(
                family["complete_parameters_through_four"]
            ),
            "K4_sha256": _sha(family["K4"]),
            "Y4_sha256": [_sha(item) for item in family["Y4"]],
            "Y4_degrees": [
                _source_degree(
                    item, *family["symbols"]["source"]
                )
                for item in family["Y4"]
            ],
            "complete_family_replay": True,
        })
    return result


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(json.dumps(run(selected_bound), indent=2, sort_keys=True))
