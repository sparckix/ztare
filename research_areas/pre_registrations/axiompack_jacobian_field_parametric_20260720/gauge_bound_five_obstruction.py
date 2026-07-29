#!/usr/bin/env python3
"""Fifth-order obstruction over the complete fixed-bound prefix family."""
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

from gauge_bound_four_extension import build_through_four  # noqa: E402
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _parameter_coefficients,
    _parameter_monomial,
    _source_degree,
    _source_target_image,
)
from gauge_minimized_fourth_jet import _pair_system  # noqa: E402
from gauge_minimized_fourth_obstruction import (  # noqa: E402
    _primitive_dual_support,
    _quotient_duals,
)
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402


def run(bound: int = 7) -> dict[str, object]:
    family = build_through_four(bound)
    if "complete_parameters_through_four" not in family:
        raise ValueError(
            "the fourth-order compatibility locus was not parameterized"
        )
    data = family["data"]
    v, t = family["symbols"]["source"]
    p, q = family["symbols"]["target"]
    p0, q0 = data["P"][0], data["Q"][0]
    parameters = family["complete_parameters_through_four"]
    target_fields = family["target_fields"]
    source_fields = family["source_fields"]

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
    residual_monomials, residual_coefficients = _parameter_coefficients(
        residual_five, parameters
    )
    residual_degrees = [
        _source_degree(item, v, t) for item in residual_five
    ]
    columns, _metadata, target_window = _source_target_image(
        source_order=5,
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
    duals, image_rank, augmented_rank, chosen = _quotient_duals(
        image, residual_matrix
    )
    dense = residual_matrix.to_Matrix()
    pairings = [
        [
            sp.cancel((dense[:, index].transpose() * dual)[0])
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
    nonzero_obstructions = [
        obstruction
        for obstruction in obstructions
        if obstruction != 0
    ]
    groebner = (
        sp.groebner(
            nonzero_obstructions,
            *parameters,
            order="grevlex",
            domain=sp.QQ,
        )
        if nonzero_obstructions
        else None
    )
    basis = [] if groebner is None else list(groebner.polys)
    inconsistent = any(
        polynomial.as_expr().is_number
        and polynomial.as_expr() != 0
        for polynomial in basis
    )

    return {
        "schema": "axiompack.jacobian_fixed_bound_five_obstruction.v1",
        "bound": bound,
        "complete_dimension_through_four": len(parameters),
        "parameters": [str(item) for item in parameters],
        "fourth_compatibility_parameterization": {
            str(key): str(value)
            for key, value in family[
                "compatibility_solution"
            ].items()
        },
        "fifth_residual_component_degrees": residual_degrees,
        "fifth_residual_parameter_monomials": [
            list(item) for item in residual_monomials
        ],
        "fifth_residual_parameter_degree": max(
            (sum(item) for item in residual_monomials),
            default=0,
        ),
        "fifth_image_rank": image_rank,
        "fifth_image_plus_residual_rank": (
            DomainMatrix.hstack(image, residual_matrix).rank()
        ),
        "fifth_quotient_dimension": augmented_rank - image_rank,
        "fifth_chosen_residual_coefficients": chosen,
        "fifth_target_window": target_window,
        "compatibility_obstructions": [
            str(item) for item in obstructions
        ],
        "obstruction_total_degrees": [
            sp.Poly(item, *parameters).total_degree()
            for item in nonzero_obstructions
        ],
        "groebner_order": "grevlex",
        "groebner_basis": [
            str(polynomial.as_expr()) for polynomial in basis
        ],
        "compatibility_variety_empty": inconsistent,
        "dual_certificates": [
            _primitive_dual_support(dual, row_keys)
            for dual in duals
        ],
        "row_key_sha256": hashlib.sha256(
            json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "claim_boundary": (
            "the lower family is the complete source-degree-bound prefix "
            "through order four, and each fifth target generator is "
            "represented in the filtered C-normal-form component window"
        ),
    }


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(json.dumps(run(selected_bound), indent=2, sort_keys=True))
