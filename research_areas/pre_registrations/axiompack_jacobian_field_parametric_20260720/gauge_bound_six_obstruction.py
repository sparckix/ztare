#!/usr/bin/env python3
"""Sixth-order obstruction over a complete fixed-bound prefix family."""
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
)


def fixed_bound_obstruction(
    *,
    family: dict[str, object],
    order: int,
    bound: int,
    parameter_key: str,
    compute_groebner: bool = True,
) -> dict[str, object]:
    data = _family_jets(order)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    p0, q0 = data["P"][0], data["Q"][0]
    parameters = family[parameter_key]
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
        maximum_order=order,
    )
    residual_monomials, residual_coefficients = (
        _parameter_residual_coefficients(
            predicted=predicted[order],
            actual=(data["P"][order], data["Q"][order]),
            scale=sp.factorial(order),
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
    columns, _metadata, target_window = _source_target_image(
        source_order=order,
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
    dense = residual_matrix.to_Matrix()
    obstructions = [
        sp.factor(sum(
            sp.cancel((dense[:, index].transpose() * dual)[0])
            * _parameter_monomial(monomial, parameters)
            for index, monomial in enumerate(residual_monomials)
        ))
        for dual in duals
    ]
    nonzero = [item for item in obstructions if item != 0]
    groebner = (
        sp.groebner(
            nonzero,
            *parameters,
            order="grevlex",
            domain=sp.QQ,
        )
        if nonzero and compute_groebner
        else None
    )
    basis = [] if groebner is None else list(groebner.polys)
    inconsistent = any(
        polynomial.as_expr().is_number
        and polynomial.as_expr() != 0
        for polynomial in basis
    )
    return {
        "bound": bound,
        "order": order,
        "complete_lower_dimension": len(parameters),
        "parameters": [str(item) for item in parameters],
        "residual_component_degrees": residual_degrees,
        "residual_parameter_degree": max(
            (sum(item) for item in residual_monomials),
            default=0,
        ),
        "residual_parameter_monomial_count": len(
            residual_monomials
        ),
        "image_rank": image_rank,
        "image_plus_residual_rank": (
            DomainMatrix.hstack(image, residual_matrix).rank()
        ),
        "quotient_dimension": augmented_rank - image_rank,
        "chosen_residual_coefficients": chosen,
        "target_window": target_window,
        "compatibility_obstructions": [
            str(item) for item in obstructions
        ],
        "obstruction_total_degrees": [
            sp.Poly(item, *parameters).total_degree()
            for item in nonzero
        ],
        "groebner_order": "grevlex",
        "groebner_computed": compute_groebner,
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
            "the lower family is the complete fixed-bound prefix through "
            f"order {order - 1}; the order-{order} target image uses the "
            "exhaustive "
            "filtered C-normal-form component window"
        ),
    }


def run(bound: int = 7) -> dict[str, object]:
    result = fixed_bound_obstruction(
        family=build_through_five(bound),
        order=6,
        bound=bound,
        parameter_key="complete_parameters_through_five",
    )
    return {
        "schema": "axiompack.jacobian_fixed_bound_six_obstruction.v1",
        **result,
        "complete_dimension_through_five": result[
            "complete_lower_dimension"
        ],
        "sixth_residual_component_degrees": result[
            "residual_component_degrees"
        ],
        "sixth_residual_parameter_degree": result[
            "residual_parameter_degree"
        ],
        "sixth_residual_parameter_monomial_count": result[
            "residual_parameter_monomial_count"
        ],
        "sixth_image_rank": result["image_rank"],
        "sixth_image_plus_residual_rank": result[
            "image_plus_residual_rank"
        ],
        "sixth_quotient_dimension": result["quotient_dimension"],
        "sixth_chosen_residual_coefficients": result[
            "chosen_residual_coefficients"
        ],
        "sixth_target_window": result["target_window"],
    }


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(json.dumps(run(selected_bound), indent=2, sort_keys=True))
