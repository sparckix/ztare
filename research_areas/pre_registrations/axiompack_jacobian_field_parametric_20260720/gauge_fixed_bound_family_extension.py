#!/usr/bin/env python3
"""Generic exact transition between complete fixed-bound contact families.

The core operator has no special cases for a jet order.  A caller supplies a
complete compatible lower family and its current parameter coordinates.  The
operator computes the next compatibility locus, retains every rational
polynomial graph returned by the exact solver, and parameterizes the complete
new-order linear fiber on each graph.
"""
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
    _source_degree,
    _source_target_image,
)
from gauge_minimized_fourth_jet import (  # noqa: E402
    _family_jets,
    _pair_system,
)
from gauge_minimized_fourth_obstruction import (  # noqa: E402
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
    _scale,
    _substitute,
)


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _add_scaled_pair(
    base: Pair, direction: Pair, scalar: sp.Expr
) -> Pair:
    return _add(base, _scale(direction, scalar))


def _polynomial_graph(
    solution: dict[sp.Symbol, sp.Expr],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[
    dict[sp.Symbol, sp.Expr],
    tuple[sp.Symbol, ...],
] | None:
    """Normalize one solver branch and require a polynomial affine graph."""
    normalized = {
        parameter: sp.expand(value)
        for parameter, value in solution.items()
    }
    for _ in range(len(normalized) + 1):
        updated = {
            parameter: sp.expand(
                value.subs({
                    other: replacement
                    for other, replacement in normalized.items()
                    if other != parameter
                })
            )
            for parameter, value in normalized.items()
        }
        if updated == normalized:
            break
        normalized = updated
    else:
        return None

    free_parameters = tuple(
        parameter
        for parameter in parameters
        if parameter not in normalized
    )
    free_set = set(free_parameters)
    for parameter, value in normalized.items():
        if parameter in value.free_symbols:
            return None
        if not value.free_symbols <= free_set:
            return None
        try:
            if free_parameters:
                sp.Poly(value, *free_parameters, domain=sp.QQ)
            else:
                sp.Rational(value)
        except (sp.PolynomialError, TypeError, ValueError):
            return None
    return normalized, free_parameters


def _compatibility_graphs(
    obstructions: list[sp.Expr],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[
    str,
    list[
        tuple[
            dict[sp.Symbol, sp.Expr],
            tuple[sp.Symbol, ...],
        ]
    ],
    list[sp.Expr],
    dict[str, object],
]:
    """Return compatibility graphs only when their coverage is certified.

    Affine-linear systems are handled by exact RREF, which proves equivalence
    between the equations and the returned graph.  For nonlinear systems,
    ``solve`` is used only to expose candidate graphs; without a separate
    ideal-decomposition certificate they are typed as partial coverage and
    cannot be consumed as a complete family.
    """
    equations = [
        sp.factor(equation)
        for equation in obstructions
        if sp.factor(equation) != 0
    ]
    if any(
        equation.is_number and equation != 0
        for equation in equations
    ):
        return "incompatible", [], equations, {
            "coverage": "empty_locus_by_nonzero_constant",
            "coverage_certified": True,
        }
    if not equations:
        return "compatible", [({}, parameters)], [], {
            "coverage": "whole_parameter_space",
            "coverage_certified": True,
        }

    polynomial_degrees = [
        sp.Poly(
            equation, *parameters, domain=sp.QQ
        ).total_degree()
        for equation in equations
    ]
    if max(polynomial_degrees) <= 1:
        matrix, rhs = sp.linear_eq_to_matrix(
            equations, parameters
        )
        rank = matrix.rank()
        augmented = matrix.row_join(rhs)
        augmented_rank = augmented.rank()
        linear_receipt = {
            "coverage": "exact_linear_rref",
            "coverage_certified": True,
            "equation_count": len(equations),
            "matrix_shape": list(matrix.shape),
            "rank": rank,
            "augmented_rank": augmented_rank,
        }
        if augmented_rank != rank:
            return "incompatible", [], equations, linear_receipt
        reduced, pivots = augmented.rref()
        if parameters and len(parameters) in pivots:
            raise AssertionError(
                "consistent linear system pivoted in the RHS"
            )
        pivot_columns = tuple(
            pivot for pivot in pivots if pivot < len(parameters)
        )
        free_parameters = tuple(
            parameter
            for index, parameter in enumerate(parameters)
            if index not in pivot_columns
        )
        solution: dict[sp.Symbol, sp.Expr] = {}
        for row, pivot in enumerate(pivot_columns):
            solution[parameters[pivot]] = sp.expand(
                reduced[row, len(parameters)]
                - sum(
                    reduced[row, column] * parameters[column]
                    for column in range(len(parameters))
                    if column not in pivot_columns
                )
            )
        if not all(
            sp.expand(equation.subs(solution)) == 0
            for equation in equations
        ):
            raise AssertionError(
                "RREF graph does not annihilate its linear system"
            )
        linear_receipt["pivot_parameters"] = [
            str(parameters[index]) for index in pivot_columns
        ]
        linear_receipt["free_parameters"] = [
            str(parameter) for parameter in free_parameters
        ]
        return (
            "compatible",
            [(solution, free_parameters)],
            equations,
            linear_receipt,
        )

    raw_solutions = sp.solve(
        equations,
        parameters,
        dict=True,
        simplify=False,
        manual=True,
    )
    graphs: list[
        tuple[
            dict[sp.Symbol, sp.Expr],
            tuple[sp.Symbol, ...],
        ]
    ] = []
    for raw_solution in raw_solutions:
        graph = _polynomial_graph(raw_solution, parameters)
        if graph is None:
            continue
        solution, free_parameters = graph
        if not all(
            sp.expand(equation.subs(solution)) == 0
            for equation in equations
        ):
            continue
        if any(
            solution == previous_solution
            for previous_solution, _free in graphs
        ):
            continue
        graphs.append((solution, free_parameters))
    if not graphs:
        return "unresolved_algebraic_locus", [], equations, {
            "coverage": "no_polynomial_graph_exposed",
            "coverage_certified": False,
            "polynomial_degrees": polynomial_degrees,
        }
    return "partial_graph_cover", graphs, equations, {
        "coverage": "solver_exposed_graphs_without_ideal_decomposition",
        "coverage_certified": False,
        "polynomial_degrees": polynomial_degrees,
        "exposed_graph_count": len(graphs),
    }


def _simultaneous_particular_solutions(
    image: DomainMatrix,
    residual_matrix: DomainMatrix,
) -> list[sp.Matrix]:
    """Solve every compatible residual column using one exact square inverse."""
    if residual_matrix.shape[1] == 0:
        return []
    rank = image.rank()
    pivot_columns = list(image.rref()[1])
    if len(pivot_columns) != rank:
        raise AssertionError("image pivot count does not equal its rank")
    basis = image.extract(
        list(range(image.shape[0])), pivot_columns
    )
    _rref, independent_rows = basis.transpose().rref()
    selected_rows = list(independent_rows)
    if len(selected_rows) != rank:
        raise AssertionError("failed to select an invertible image minor")
    square = basis.extract(
        selected_rows, list(range(rank))
    ).to_Matrix()
    selected_residual = residual_matrix.extract(
        selected_rows,
        list(range(residual_matrix.shape[1])),
    ).to_Matrix()
    coordinates = square.inv() * selected_residual

    solutions: list[sp.Matrix] = []
    for residual_index in range(residual_matrix.shape[1]):
        vector = sp.zeros(image.shape[1], 1)
        for pivot_offset, column_index in enumerate(pivot_columns):
            vector[column_index] = sp.cancel(
                coordinates[pivot_offset, residual_index]
            )
        expected = residual_matrix.to_Matrix()[:, residual_index]
        if image.to_Matrix() * vector != expected:
            raise AssertionError("simultaneous image solve failed")
        solutions.append(vector)
    return solutions


def verify_order_replay(
    *,
    family: dict[str, object],
    order: int,
    parameters: tuple[sp.Symbol, ...],
) -> bool:
    """Replay one completed order as a parameter-polynomial identity."""
    data = _family_jets(order)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    predicted = _composed_parameter_series(
        target_fields=family["target_fields"],
        source_fields=family["source_fields"],
        parameters=parameters,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=order,
    )
    _monomials, coefficients = _parameter_residual_coefficients(
        predicted=predicted[order],
        actual=(data["P"][order], data["Q"][order]),
        scale=sp.factorial(order),
        parameter_count=len(parameters),
        coefficient_variables=(v, t),
    )
    return all(
        component == 0
        for pair in coefficients
        for component in pair
    )


def extend_fixed_bound_family(
    *,
    family: dict[str, object],
    lower_order: int,
    lower_parameters: tuple[sp.Symbol, ...],
    verify_replay: bool = False,
) -> dict[str, object]:
    """Append ``lower_order + 1`` to a complete compatible family.

    The result contains zero or more complete rational polynomial branches.
    ``status=incompatible`` means the compatibility locus is empty.
    ``status=unresolved_algebraic_locus`` preserves a nonempty locus that the
    polynomial-graph carrier cannot represent.
    """
    order = lower_order + 1
    bound = int(family["bound"])
    data = _family_jets(order)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = family["jacobian"]

    predicted = _composed_parameter_series(
        target_fields=family["target_fields"],
        source_fields=family["source_fields"],
        parameters=lower_parameters,
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
            parameter_count=len(lower_parameters),
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
        source_order=order,
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
        list(range(combined.shape[0])),
        list(range(image_count)),
    )
    residual_matrix = combined.extract(
        list(range(combined.shape[0])),
        list(range(image_count, combined.shape[1])),
    )
    duals, image_rank, augmented_rank, chosen = (
        _quotient_duals(image, residual_matrix)
    )
    dense_residual = residual_matrix.to_Matrix()
    obstructions = [
        sp.factor(sum(
            sp.cancel(
                (
                    dense_residual[:, index].transpose()
                    * dual
                )[0]
            )
            * _parameter_monomial(
                monomial, lower_parameters
            )
            for index, monomial in enumerate(
                residual_monomials
            )
        ))
        for dual in duals
    ]
    status, graphs, equations, coverage_receipt = (
        _compatibility_graphs(
            obstructions, lower_parameters
        )
    )
    receipt: dict[str, object] = {
        "schema": (
            "axiompack.jacobian_fixed_bound_family_extension.v1"
        ),
        "status": status,
        "bound": bound,
        "lower_order": lower_order,
        "order": order,
        "lower_parameter_count": len(lower_parameters),
        "residual_component_degrees": residual_degrees,
        "residual_parameter_degree": max(
            (sum(monomial) for monomial in residual_monomials),
            default=0,
        ),
        "residual_parameter_monomial_count": len(
            residual_monomials
        ),
        "image_rank": image_rank,
        "image_column_count": image.shape[1],
        "image_nullity": image.shape[1] - image_rank,
        "image_plus_residual_rank": (
            DomainMatrix.hstack(
                image, residual_matrix
            ).rank()
        ),
        "quotient_dimension": augmented_rank - image_rank,
        "chosen_residual_coefficients": chosen,
        "target_window": target_window,
        "compatibility_obstructions": obstructions,
        "nonzero_compatibility_equations": equations,
        "compatibility_branch_count": len(graphs),
        "compatibility_coverage": coverage_receipt,
        "row_key_sha256": hashlib.sha256(
            json.dumps(
                row_keys, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
        "branches": [],
        "claim_boundary": (
            "the input must be the complete compatible lower family; "
            "non-polynomial algebraic loci remain typed and are not "
            "replaced by a selected witness"
        ),
    }
    if status != "compatible":
        return receipt

    branches: list[dict[str, object]] = []
    for branch_index, (
        compatibility_solution,
        compatible_parameters,
    ) in enumerate(graphs):
        target_fields = {
            field_order: tuple(
                sp.expand(
                    component.subs(compatibility_solution)
                )
                for component in field
            )
            for field_order, field
            in family["target_fields"].items()
        }
        source_fields = {
            field_order: tuple(
                sp.expand(
                    component.subs(compatibility_solution)
                )
                for component in field
            )
            for field_order, field
            in family["source_fields"].items()
        }
        (
            branch_residual_monomials,
            branch_residual_coefficients,
        ) = _substitute_parameter_coordinates(
            monomials=residual_monomials,
            coefficients=residual_coefficients,
            old_parameters=lower_parameters,
            substitution=compatibility_solution,
            new_parameters=compatible_parameters,
        )
        branch_combined, _zero, branch_row_keys = _pair_system(
            columns + branch_residual_coefficients,
            (sp.Integer(0), sp.Integer(0)),
            v,
            t,
        )
        branch_image = branch_combined.extract(
            list(range(branch_combined.shape[0])),
            list(range(image_count)),
        )
        branch_residual_matrix = branch_combined.extract(
            list(range(branch_combined.shape[0])),
            list(range(
                image_count, branch_combined.shape[1]
            )),
        )
        if DomainMatrix.hstack(
            branch_image, branch_residual_matrix
        ).rank() != branch_image.rank():
            raise AssertionError(
                "compatibility graph does not put the residual "
                "inside the next-order image"
            )
        particulars = _simultaneous_particular_solutions(
            branch_image, branch_residual_matrix
        )
        nullspace = branch_image.to_Matrix().nullspace()
        new_parameters = tuple(sp.symbols(
            f"j{order}_0:{len(nullspace)}"
        ))
        y_order: Pair = (sp.Integer(0), sp.Integer(0))
        k_order = sp.Integer(0)
        for monomial, vector in zip(
            branch_residual_monomials,
            particulars,
            strict=True,
        ):
            response_y, response_k = _decode_generator(
                vector, metadata, order, v, t, p, q
            )
            scalar = _parameter_monomial(
                monomial, compatible_parameters
            )
            y_order = _add_scaled_pair(
                y_order, response_y, scalar
            )
            k_order += scalar * response_k
        for parameter, vector in zip(
            new_parameters, nullspace, strict=True
        ):
            response_y, response_k = _decode_generator(
                vector, metadata, order, v, t, p, q
            )
            y_order = _add_scaled_pair(
                y_order, response_y, parameter
            )
            k_order += parameter * response_k
        y_order = (
            sp.expand(y_order[0]),
            sp.expand(y_order[1]),
        )
        k_order = sp.expand(k_order)
        target_fields[order] = _hamiltonian_field(
            k_order, p, q
        )
        source_fields[order] = y_order

        target_at_seed = _substitute(
            target_fields[order], p, q, p0, q0
        )
        direct_response = (
            sp.expand(
                jacobian[0, 0] * y_order[0]
                + jacobian[0, 1] * y_order[1]
                + target_at_seed[0]
            ),
            sp.expand(
                jacobian[1, 0] * y_order[0]
                + jacobian[1, 1] * y_order[1]
                + target_at_seed[1]
            ),
        )
        direct_monomials, direct_coefficients = (
            _parameter_coefficients(
                direct_response, compatible_parameters
            )
        )
        if direct_monomials != branch_residual_monomials:
            raise AssertionError(
                "direct response parameter support changed"
            )
        if not all(
            sp.expand(left - right) == 0
            for direct_pair, residual_pair in zip(
                direct_coefficients,
                branch_residual_coefficients,
                strict=True,
            )
            for left, right in zip(
                direct_pair, residual_pair, strict=True
            )
        ):
            raise AssertionError(
                "constructed order field does not equal the residual"
            )

        complete_parameters = (
            *compatible_parameters, *new_parameters
        )
        branch: dict[str, object] = {
            "bound": bound,
            "completed_order": order,
            "data": data,
            "symbols": family["symbols"],
            "jacobian": jacobian,
            "target_fields": target_fields,
            "source_fields": source_fields,
            "lower_family": family,
            "lower_parameters": lower_parameters,
            "compatibility_solution": (
                compatibility_solution
            ),
            "compatible_lower_parameters": (
                compatible_parameters
            ),
            "parameters_at_order": new_parameters,
            "complete_parameters": complete_parameters,
            "K_order": k_order,
            "Y_order": y_order,
            "image": branch_image,
            "residual_matrix": branch_residual_matrix,
            "row_keys": branch_row_keys,
            "coefficient_replay": True,
            "source_order_degrees": [
                _source_degree(component, v, t)
                for component in y_order
            ],
            "K_order_sha256": _sha(k_order),
            "Y_order_sha256": [
                _sha(component) for component in y_order
            ],
        }
        if verify_replay:
            branch["parameter_polynomial_replay"] = (
                verify_order_replay(
                    family=branch,
                    order=order,
                    parameters=complete_parameters,
                )
            )
            if not branch["parameter_polynomial_replay"]:
                raise AssertionError(
                    "parameter-polynomial replay failed"
                )
        branches.append(branch)
        receipt["branches"].append({
            "branch_index": branch_index,
            "compatibility_solution": {
                str(parameter): str(value)
                for parameter, value
                in compatibility_solution.items()
            },
            "compatible_lower_parameter_count": len(
                compatible_parameters
            ),
            "new_parameter_count": len(new_parameters),
            "complete_parameter_count": len(
                complete_parameters
            ),
            "source_order_degrees": (
                branch["source_order_degrees"]
            ),
            "K_order_sha256": branch["K_order_sha256"],
            "Y_order_sha256": branch["Y_order_sha256"],
            "parameter_polynomial_replay": branch.get(
                "parameter_polynomial_replay"
            ),
        })
    receipt["family_branches"] = branches
    return receipt


def _regression_order_five(bound: int = 7) -> dict[str, object]:
    """Compare the generic transition with the existing order-five module."""
    from gauge_bound_five_extension import (  # noqa: E402
        build_through_five,
    )
    from gauge_bound_four_extension import (  # noqa: E402
        build_through_four,
    )

    lower = build_through_four(bound)
    generic = extend_fixed_bound_family(
        family=lower,
        lower_order=4,
        lower_parameters=lower[
            "complete_parameters_through_four"
        ],
        verify_replay=True,
    )
    reference = build_through_five(
        bound, lower_family=lower
    )
    if generic["status"] != "compatible":
        raise AssertionError("generic order-five transition failed")
    if len(generic["family_branches"]) != 1:
        raise AssertionError(
            "order-five regression expected one branch"
        )
    branch = generic["family_branches"][0]
    same_obstructions = all(
        sp.expand(left - right) == 0
        for left, right in zip(
            generic["compatibility_obstructions"],
            reference["compatibility_obstructions"],
            strict=True,
        )
    )
    same_solution = (
        branch["compatibility_solution"]
        == reference["compatibility_solution"]
    )
    same_compatible_lower_parameters = (
        branch["compatible_lower_parameters"]
        == reference["compatible_parameters_through_four"]
    )
    same_new_dimension = (
        len(branch["parameters_at_order"])
        == len(reference["parameters_at_five"])
    )
    if not all((
        same_obstructions,
        same_solution,
        same_compatible_lower_parameters,
        same_new_dimension,
        branch["parameter_polynomial_replay"],
    )):
        raise AssertionError(
            "generic order-five regression differs from reference"
        )
    return {
        "schema": (
            "axiompack.jacobian_fixed_bound_family_extension_"
            "regression.v1"
        ),
        "bound": bound,
        "order": 5,
        "same_obstructions": same_obstructions,
        "same_compatibility_solution": same_solution,
        "same_compatible_lower_parameters": (
            same_compatible_lower_parameters
        ),
        "same_new_dimension": same_new_dimension,
        "parameter_polynomial_replay": (
            branch["parameter_polynomial_replay"]
        ),
        "image_rank": generic["image_rank"],
        "image_nullity": generic["image_nullity"],
        "complete_parameter_count": len(
            branch["complete_parameters"]
        ),
    }


if __name__ == "__main__":
    selected_bound = (
        int(sys.argv[1]) if len(sys.argv) > 1 else 7
    )
    print(json.dumps(
        _regression_order_five(selected_bound),
        indent=2,
        sort_keys=True,
    ))
