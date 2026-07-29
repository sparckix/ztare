#!/usr/bin/env python3
"""Probe a canonical order-one stabilizer gauge through four contact jets."""
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

from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_fourth_jet import _pair_system  # noqa: E402
from gauge_minimized_fourth_obstruction import (  # noqa: E402
    _quotient_duals,
)
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _decode_generator,
    _parameter_coefficients,
    _parameter_monomial,
    _source_target_image,
)
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import (  # noqa: E402
    _hamiltonian_field,
    _particular_solution,
)


Pair = tuple[sp.Expr, sp.Expr]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def _source_degree(
    value: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t).total_degree())


def _solve_source(
    jacobian: sp.Matrix, residual: Pair
) -> tuple[Pair, tuple[sp.Expr, sp.Expr]]:
    solution = tuple(
        sp.factor(sp.cancel(value))
        for value in jacobian.inv() * sp.Matrix(residual)
    )
    denominators = tuple(sp.factor(sp.denom(value)) for value in solution)
    if any(
        sp.expand(value) != 0
        for value in (
            jacobian * sp.Matrix(solution) - sp.Matrix(residual)
        )
    ):
        raise ValueError("source recursion failed exact replay")
    return (
        solution,  # type: ignore[arg-type]
        denominators,  # type: ignore[arg-type]
    )


def _high_degree_conditions(
    source_fields: dict[int, Pair],
    *,
    bound: int,
    parameter: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> list[sp.Poly]:
    conditions: list[sp.Poly] = []
    for field in source_fields.values():
        for component in field:
            polynomial = sp.Poly(
                component, v, t, domain=sp.QQ[parameter]
            )
            for monomial, coefficient in polynomial.terms():
                if sum(monomial) > bound and coefficient != 0:
                    conditions.append(
                        sp.Poly(coefficient, parameter, domain=sp.QQ)
                    )
    return conditions


def _proportional_pair(
    left: Pair,
    right: Pair,
    variables: tuple[sp.Symbol, sp.Symbol],
) -> sp.Expr | None:
    left_polynomials = [
        sp.Poly(component, *variables, domain=sp.QQ)
        for component in left
    ]
    right_polynomials = [
        sp.Poly(component, *variables, domain=sp.QQ)
        for component in right
    ]
    ratio: sp.Expr | None = None
    monomials = sorted({
        (component, *monomial)
        for component, polynomial in enumerate(right_polynomials)
        for monomial in polynomial.monoms()
    })
    for component, *monomial in monomials:
        right_coefficient = right_polynomials[
            component
        ].coeff_monomial(tuple(monomial))
        left_coefficient = left_polynomials[
            component
        ].coeff_monomial(tuple(monomial))
        if right_coefficient == 0:
            if left_coefficient != 0:
                return None
            continue
        candidate = sp.cancel(left_coefficient / right_coefficient)
        ratio = candidate if ratio is None else ratio
        if candidate != ratio:
            return None
    if ratio is None:
        return None
    return (
        ratio
        if all(
            sp.expand(
                left_component - ratio * right_component
            ) == 0
            for left_component, right_component in zip(
                left, right, strict=True
            )
        )
        else None
    )


def _complete_order_one_family(
    *,
    bound: int,
    data: dict[str, object],
    jacobian: sp.Matrix,
    base_hamiltonian: sp.Expr,
    stabilizer_hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> dict[str, object]:
    p0, q0 = data["P"][0], data["Q"][0]
    residual = data["P"][1], data["Q"][1]
    residual_degrees = [
        _source_degree(component, v, t) for component in residual
    ]
    columns, metadata, target_window = _source_target_image(
        source_order=1,
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
    matrix, rhs, _row_keys = _pair_system(
        columns, residual, v, t
    )
    rank = matrix.rank()
    augmented_rank = DomainMatrix.hstack(matrix, rhs).rank()
    nullspace = matrix.to_Matrix().nullspace()
    known_base_field = _hamiltonian_field(
        base_hamiltonian, p, q
    )
    known_base_replay = (
        sp.expand(
            known_base_field[0].subs({p: p0, q: q0})
            - residual[0]
        ) == 0
        and sp.expand(
            known_base_field[1].subs({p: p0, q: q0})
            - residual[1]
        ) == 0
    )
    result: dict[str, object] = {
        "bound": bound,
        "rank": rank,
        "augmented_rank": augmented_rank,
        "nullity": len(nullspace),
        "target_window": target_window,
        "known_base_replay": known_base_replay,
    }
    if len(nullspace) == 1:
        source_direction, hamiltonian_direction = _decode_generator(
            nullspace[0], metadata, 1, v, t, p, q
        )
        target_ratio = _proportional_pair(
            _hamiltonian_field(hamiltonian_direction, p, q),
            _hamiltonian_field(stabilizer_hamiltonian, p, q),
            (p, q),
        )
        expected_source = _solve_source(
            jacobian,
            tuple(
                -component.subs({p: p0, q: q0})
                for component in _hamiltonian_field(
                    stabilizer_hamiltonian, p, q
                )
            ),  # type: ignore[arg-type]
        )[0]
        source_ratio = _proportional_pair(
            source_direction, expected_source, (v, t)
        )
        result.update({
            "direction_target_ratio_to_K_star": str(target_ratio),
            "direction_source_ratio_to_Z_star": str(source_ratio),
            "direction_matches_seed_stabilizer": (
                target_ratio is not None
                and target_ratio == source_ratio
            ),
            "direction_source_degrees": [
                _source_degree(component, v, t)
                for component in source_direction
            ],
        })
    return result


def _build_complete_order_one_fields(
    *,
    bound: int,
    data: dict[str, object],
    jacobian: sp.Matrix,
    base_hamiltonian: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[
    dict[int, Pair],
    dict[int, Pair],
    tuple[sp.Symbol, ...],
    dict[str, object],
]:
    p0, q0 = data["P"][0], data["Q"][0]
    residual = data["P"][1], data["Q"][1]
    residual_degrees = [
        _source_degree(component, v, t) for component in residual
    ]
    columns, metadata, target_window = _source_target_image(
        source_order=1,
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
    matrix, rhs, _row_keys = _pair_system(
        columns, residual, v, t
    )
    if matrix.rank() != DomainMatrix.hstack(matrix, rhs).rank():
        raise ValueError("known first-order contact is absent")
    directions = [
        _decode_generator(
            vector, metadata, 1, v, t, p, q
        )
        for vector in matrix.to_Matrix().nullspace()
    ]
    parameters = sp.symbols(f"l0:{len(directions)}")
    source: Pair = (sp.Integer(0), sp.Integer(0))
    hamiltonian = base_hamiltonian
    for parameter, (
        source_direction,
        hamiltonian_direction,
    ) in zip(parameters, directions, strict=True):
        source = (
            sp.expand(
                source[0] + parameter * source_direction[0]
            ),
            sp.expand(
                source[1] + parameter * source_direction[1]
            ),
        )
        hamiltonian += parameter * hamiltonian_direction
    target_fields = {
        1: _hamiltonian_field(
            sp.expand(hamiltonian), p, q
        )
    }
    source_fields = {1: source}
    predicted = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=1,
    )
    actual = data["P"][1], data["Q"][1]
    if any(
        sp.expand(left - right) != 0
        for left, right in zip(
            predicted[1], actual, strict=True
        )
    ):
        raise ValueError("complete order-one family failed replay")
    return target_fields, source_fields, parameters, {
        "bound": bound,
        "rank": matrix.rank(),
        "nullity": len(directions),
        "target_window": target_window,
        "direction_source_degrees": [
            [
                _source_degree(component, v, t)
                for component in direction[0]
            ]
            for direction in directions
        ],
        "complete_order_one_replay": True,
    }


def _order_two_full_image_obstructions(
    *,
    target_fields: dict[int, Pair],
    source_one: Pair,
    parameter: sp.Symbol,
    source_degree_bound: int,
    data: dict[str, object],
    jacobian: sp.Matrix,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> dict[str, object]:
    p0, q0 = data["P"][0], data["Q"][0]
    predicted = _composed_series(
        target_fields=target_fields,
        source_fields={1: source_one},
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=2,
    )
    residual = (
        sp.expand(data["P"][2] - 2 * predicted[2][0]),
        sp.expand(data["Q"][2] - 2 * predicted[2][1]),
    )
    parameter_monomials, residual_coefficients = (
        _parameter_coefficients(residual, (parameter,))
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
    columns, _metadata, target_window = _source_target_image(
        source_order=2,
        source_degree_bound=source_degree_bound,
        first_target_degree=max(
            source_degree_bound + 3, residual_degrees[0]
        ),
        second_target_degree=max(
            source_degree_bound + 5, residual_degrees[1]
        ),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
    )
    combined, _zero, _row_keys = _pair_system(
        columns + residual_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    image_count = len(columns)
    rows = list(range(combined.shape[0]))
    image = combined.extract(rows, list(range(image_count)))
    residual_matrix = combined.extract(
        rows, list(range(image_count, combined.shape[1]))
    )
    duals, image_rank, augmented_rank, _chosen = _quotient_duals(
        image, residual_matrix
    )
    residual_dense = residual_matrix.to_Matrix()
    obstructions = [
        sp.factor(sum(
            (
                residual_dense[:, index].transpose() * dual
            )[0]
            * _parameter_monomial(
                monomial, (parameter,)
            )
            for index, monomial in enumerate(
                parameter_monomials
            )
        ))
        for dual in duals
    ]
    nonzero = [item for item in obstructions if item != 0]
    ideal_gcd = sp.Poly(0, parameter, domain=sp.QQ)
    for item in nonzero:
        polynomial = sp.Poly(item, parameter, domain=sp.QQ)
        ideal_gcd = (
            polynomial
            if ideal_gcd.is_zero
            else sp.gcd(ideal_gcd, polynomial)
        )
    roots = (
        sp.solve(ideal_gcd.as_expr(), parameter)
        if nonzero and ideal_gcd.degree() > 0
        else []
    )
    return {
        "residual_parameter_degree": max(
            sum(monomial) for monomial in parameter_monomials
        ),
        "residual_component_degrees": residual_degrees,
        "target_window": target_window,
        "image_rank": image_rank,
        "image_plus_residual_rank": augmented_rank,
        "obstructions": [str(item) for item in nonzero],
        "obstruction_gcd": str(sp.factor(ideal_gcd.as_expr())),
        "compatible_parameter_roots": [
            str(root) for root in roots
        ],
    }


def _extend_canonical_branch(
    *,
    order: int,
    target_fields: dict[int, Pair],
    source_fields: dict[int, Pair],
    parameters: tuple[sp.Symbol, ...],
    source_degree_bound: int,
    data: dict[str, object],
    jacobian: sp.Matrix,
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[
    dict[str, object],
    Pair | None,
    sp.Expr | None,
    list[tuple[Pair, sp.Expr]],
]:
    p0, q0 = data["P"][0], data["Q"][0]
    predicted = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=order,
    )
    residual = (
        sp.expand(
            data["P"][order]
            - sp.factorial(order) * predicted[order][0]
        ),
        sp.expand(
            data["Q"][order]
            - sp.factorial(order) * predicted[order][1]
        ),
    )
    parameter_monomials, residual_coefficients = (
        _parameter_coefficients(residual, parameters)
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
        source_degree_bound=source_degree_bound,
        first_target_degree=max(
            source_degree_bound + 3, residual_degrees[0]
        ),
        second_target_degree=max(
            source_degree_bound + 5, residual_degrees[1]
        ),
        v=v,
        t=t,
        p=p,
        q=q,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
    )
    combined, _zero, _row_keys = _pair_system(
        columns + residual_coefficients,
        (sp.Integer(0), sp.Integer(0)),
        v,
        t,
    )
    rows = list(range(combined.shape[0]))
    image_count = len(columns)
    image = combined.extract(rows, list(range(image_count)))
    residual_matrix = combined.extract(
        rows, list(range(image_count, combined.shape[1]))
    )
    duals, image_rank, augmented_rank, _chosen = _quotient_duals(
        image, residual_matrix
    )
    residual_dense = residual_matrix.to_Matrix()
    obstructions = [
        sp.factor(sum(
            (
                residual_dense[:, index].transpose() * dual
            )[0]
            * _parameter_monomial(
                monomial, parameters
            )
            for index, monomial in enumerate(
                parameter_monomials
            )
        ))
        for dual in duals
    ]
    nonzero = [item for item in obstructions if item != 0]
    receipt: dict[str, object] = {
        "order": order,
        "residual_parameter_degree": max(
            sum(monomial) for monomial in parameter_monomials
        ),
        "residual_component_degrees": residual_degrees,
        "image_rank": image_rank,
        "image_plus_residual_rank": augmented_rank,
        "target_window": target_window,
        "obstructions": [str(item) for item in nonzero],
    }
    if nonzero:
        compatibility_solutions = sp.solve(
            nonzero, parameters, dict=True
        )
        receipt.update({
            "compatibility_solutions": [
                {
                    str(key): str(sp.factor(value))
                    for key, value in solution.items()
                }
                for solution in compatibility_solutions
            ],
            "extended": False,
        })
        return receipt, None, None, []

    particulars = [
        _particular_solution(
            image,
            residual_matrix.extract(rows, [index]),
        )
        for index in range(residual_matrix.shape[1])
    ]
    source: Pair = (sp.Integer(0), sp.Integer(0))
    hamiltonian = sp.Integer(0)
    for monomial, vector in zip(
        parameter_monomials, particulars, strict=True
    ):
        response_source, response_hamiltonian = _decode_generator(
            vector, metadata, order, v, t, p, q
        )
        scalar = _parameter_monomial(monomial, parameters)
        source = (
            sp.expand(source[0] + scalar * response_source[0]),
            sp.expand(source[1] + scalar * response_source[1]),
        )
        hamiltonian += scalar * response_hamiltonian
    hamiltonian = sp.expand(hamiltonian)
    directions = [
        _decode_generator(
            vector, metadata, order, v, t, p, q
        )
        for vector in image.to_Matrix().nullspace()
    ]
    receipt.update({
        "extended": True,
        "source_degrees": [
            _source_degree(component, v, t)
            for component in source
        ],
        "source_sha256": [_sha(component) for component in source],
        "hamiltonian_sha256": _sha(hamiltonian),
        "new_direction_count": len(directions),
    })
    return receipt, source, hamiltonian, directions


def run(
    maximum_order: int = 4, source_degree_bound: int = 5
) -> dict[str, object]:
    parameter = sp.Symbol("lambda")
    p, q = sp.symbols("P Q")
    data = _family_jets(maximum_order)
    v, t = data["symbols"]
    p0, q0 = data["P"][0], data["Q"][0]
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])

    base_hamiltonian = -q**2 / 4 - p**3 / 36
    stabilizer_hamiltonian = -(
        4 * p**3 - 18 * p * q + 27 * q**2
    ) / 12
    target_fields = {
        1: _hamiltonian_field(
            base_hamiltonian
            + parameter * stabilizer_hamiltonian,
            p,
            q,
        )
    }
    source_fields: dict[int, Pair] = {}
    order_one_completeness = {
        str(bound): _complete_order_one_family(
            bound=bound,
            data=data,
            jacobian=jacobian,
            base_hamiltonian=base_hamiltonian,
            stabilizer_hamiltonian=stabilizer_hamiltonian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        for bound in sorted({4, 5, source_degree_bound})
    }

    for order in range(1, maximum_order + 1):
        predicted = _composed_series(
            target_fields=target_fields,
            source_fields=source_fields,
            p=p,
            q=q,
            v=v,
            t=t,
            p0=p0,
            q0=q0,
            maximum_order=order,
        )
        residual = (
            sp.expand(
                data["P"][order]
                - sp.factorial(order) * predicted[order][0]
            ),
            sp.expand(
                data["Q"][order]
                - sp.factorial(order) * predicted[order][1]
            ),
        )
        source, denominators = _solve_source(jacobian, residual)
        if any(denominator.free_symbols for denominator in denominators):
            return {
                "schema": (
                    "axiompack.jacobian_order_one_stabilizer_probe.v1"
                ),
                "maximum_order": maximum_order,
                "source_degree_bound": source_degree_bound,
                "base_hamiltonian": str(base_hamiltonian),
                "stabilizer_hamiltonian": str(
                    stabilizer_hamiltonian
                ),
                "polynomial_recursion": False,
                "first_nonpolynomial_order": order,
                "denominators": [
                    str(denominator)
                    for denominator in denominators
                ],
                "claim_boundary": (
                    "the autonomous combined target flow fails the "
                    "polynomial quotient-source recursion; composition "
                    "with separate stabilizer flow remains untested"
                ),
            }
        source_fields[order] = source

    completed = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=maximum_order,
    )
    for order in range(maximum_order + 1):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        if any(
            sp.expand(left - right) != 0
            for left, right in zip(
                completed[order], actual, strict=True
            )
        ):
            raise ValueError(f"prefix replay failed at order {order}")

    conditions = _high_degree_conditions(
        source_fields,
        bound=source_degree_bound,
        parameter=parameter,
        v=v,
        t=t,
    )
    gcd = sp.Poly(0, parameter, domain=sp.QQ)
    for condition in conditions:
        gcd = condition if gcd.is_zero else sp.gcd(gcd, condition)
    common_roots = (
        sp.solve(gcd.as_expr(), parameter)
        if conditions and gcd.degree() > 0
        else []
    )
    rational_roots = [
        root for root in common_roots if root.is_Rational
    ]
    bounded_roots = [
        root
        for root in rational_roots
        if all(
            _source_degree(
                sp.expand(component.subs(parameter, root)), v, t
            )
            <= source_degree_bound
            for field in source_fields.values()
            for component in field
        )
    ]
    order_two_full_image = _order_two_full_image_obstructions(
        target_fields=target_fields,
        source_one=source_fields[1],
        parameter=parameter,
        source_degree_bound=source_degree_bound,
        data=data,
        jacobian=jacobian,
        p=p,
        q=q,
        v=v,
        t=t,
    )
    canonical_target_fields = dict(target_fields)
    canonical_source_fields = {1: source_fields[1]}
    canonical_parameters = (parameter,)
    canonical_extensions: list[dict[str, object]] = []
    for order in range(2, maximum_order + 1):
        receipt, source, hamiltonian, directions = (
            _extend_canonical_branch(
            order=order,
            target_fields=canonical_target_fields,
            source_fields=canonical_source_fields,
            parameters=canonical_parameters,
            source_degree_bound=source_degree_bound,
            data=data,
            jacobian=jacobian,
            p=p,
            q=q,
            v=v,
            t=t,
            )
        )
        canonical_extensions.append(receipt)
        if source is None or hamiltonian is None:
            break
        new_parameters = sp.symbols(
            f"g{order}_0:{len(directions)}"
        )
        for new_parameter, (
            source_direction,
            hamiltonian_direction,
        ) in zip(new_parameters, directions, strict=True):
            source = (
                sp.expand(
                    source[0]
                    + new_parameter * source_direction[0]
                ),
                sp.expand(
                    source[1]
                    + new_parameter * source_direction[1]
                ),
            )
            hamiltonian += (
                new_parameter * hamiltonian_direction
            )
        hamiltonian = sp.expand(hamiltonian)
        canonical_source_fields[order] = source
        canonical_target_fields[order] = _hamiltonian_field(
            hamiltonian, p, q
        )
        canonical_parameters = (
            *canonical_parameters, *new_parameters
        )
    complete_family_branch: dict[str, object] | None = None
    if source_degree_bound >= 7:
        (
            complete_target_fields,
            complete_source_fields,
            complete_parameters,
            complete_order_one,
        ) = _build_complete_order_one_fields(
            bound=source_degree_bound,
            data=data,
            jacobian=jacobian,
            base_hamiltonian=base_hamiltonian,
            p=p,
            q=q,
            v=v,
            t=t,
        )
        complete_extensions: list[dict[str, object]] = []
        order = 2
        while order <= maximum_order:
            receipt, source, hamiltonian, directions = (
                _extend_canonical_branch(
                    order=order,
                    target_fields=complete_target_fields,
                    source_fields=complete_source_fields,
                    parameters=complete_parameters,
                    source_degree_bound=source_degree_bound,
                    data=data,
                    jacobian=jacobian,
                    p=p,
                    q=q,
                    v=v,
                    t=t,
                )
            )
            complete_extensions.append(receipt)
            if source is None or hamiltonian is None:
                serialized_solutions = receipt.get(
                    "compatibility_solutions"
                )
                if (
                    not isinstance(serialized_solutions, list)
                    or len(serialized_solutions) != 1
                    or not isinstance(serialized_solutions[0], dict)
                ):
                    break
                by_name = {
                    str(parameter): parameter
                    for parameter in complete_parameters
                }
                substitution = {
                    by_name[str(key)]: sp.sympify(
                        value, locals=by_name
                    )
                    for key, value in serialized_solutions[0].items()
                }
                complete_target_fields = {
                    field_order: tuple(
                        sp.expand(component.subs(substitution))
                        for component in field
                    )
                    for field_order, field
                    in complete_target_fields.items()
                }
                complete_source_fields = {
                    field_order: tuple(
                        sp.expand(component.subs(substitution))
                        for component in field
                    )
                    for field_order, field
                    in complete_source_fields.items()
                }
                complete_parameters = tuple(
                    parameter
                    for parameter in complete_parameters
                    if parameter not in substitution
                )
                continue
            new_parameters = sp.symbols(
                f"h{order}_0:{len(directions)}"
            )
            for new_parameter, (
                source_direction,
                hamiltonian_direction,
            ) in zip(new_parameters, directions, strict=True):
                source = (
                    sp.expand(
                        source[0]
                        + new_parameter * source_direction[0]
                    ),
                    sp.expand(
                        source[1]
                        + new_parameter * source_direction[1]
                    ),
                )
                hamiltonian += (
                    new_parameter * hamiltonian_direction
                )
            complete_source_fields[order] = source
            complete_target_fields[order] = _hamiltonian_field(
                sp.expand(hamiltonian), p, q
            )
            complete_parameters = (
                *complete_parameters, *new_parameters
            )
            order += 1
        complete_family_branch = {
            "order_one": complete_order_one,
            "extensions": complete_extensions,
        }

    return {
        "schema": (
            "axiompack.jacobian_order_one_stabilizer_probe.v1"
        ),
        "maximum_order": maximum_order,
        "source_degree_bound": source_degree_bound,
        "order_one_completeness": order_one_completeness,
        "base_hamiltonian": str(base_hamiltonian),
        "stabilizer_hamiltonian": str(stabilizer_hamiltonian),
        "polynomial_recursion": True,
        "source_degrees_over_Q_lambda": {
            str(order): [
                _source_degree(component, v, t)
                for component in field
            ]
            for order, field in source_fields.items()
        },
        "source_sha256": {
            str(order): [_sha(component) for component in field]
            for order, field in source_fields.items()
        },
        "high_degree_condition_count": len(conditions),
        "high_degree_condition_gcd": str(sp.factor(gcd.as_expr())),
        "common_rational_roots": [str(root) for root in rational_roots],
        "bounded_rational_roots": [str(root) for root in bounded_roots],
        "order_two_full_image": order_two_full_image,
        "canonical_full_image_branch": canonical_extensions,
        "complete_order_one_family_branch": complete_family_branch,
        "full_prefix_replay": True,
        "claim_boundary": (
            "tests one autonomous first-order Hamiltonian family; "
            "independent higher target jets are not included"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
