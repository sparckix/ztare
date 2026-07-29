#!/usr/bin/env python3
"""Exact affine-graph coverage for factorable polynomial loci.

This module deliberately does not call a general symbolic equation solver.
It uses only two equivalences over a characteristic-zero field:

* an affine-linear system is equivalent to its exact RREF graph;
* ``V(f * g) = V(f) union V(g)``.

Consequently, every returned affine branch has exhaustive coverage.  If a
branch retains an irreducible nonlinear equation, that branch is returned as
an unresolved algebraic locus instead of being replaced by solver samples.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy as sp


@dataclass(frozen=True)
class AffineBranch:
    """One exact graph in the original parameter coordinates."""

    solution: dict[sp.Symbol, sp.Expr]
    free_parameters: tuple[sp.Symbol, ...]


@dataclass(frozen=True)
class AlgebraicBranch:
    """One exactly covered branch that is not yet an affine graph."""

    solution: dict[sp.Symbol, sp.Expr]
    free_parameters: tuple[sp.Symbol, ...]
    equations: tuple[sp.Expr, ...]


@dataclass(frozen=True)
class LocusDecomposition:
    """Coverage result for a polynomial zero locus."""

    status: str
    affine_branches: tuple[AffineBranch, ...]
    unresolved_branches: tuple[AlgebraicBranch, ...]
    receipt: dict[str, object]


def _normalize_equation(
    equation: sp.Expr,
    parameters: tuple[sp.Symbol, ...],
) -> sp.Expr:
    """Clear rational constants and return a canonical polynomial."""
    expanded = sp.cancel(sp.expand(equation))
    numerator, denominator = sp.fraction(expanded)
    if denominator.free_symbols & set(parameters):
        raise ValueError(
            "parameter-dependent denominators are outside polynomial-locus "
            "semantics"
        )
    if not parameters:
        value = sp.Rational(numerator)
        return sp.Integer(0) if value == 0 else sp.Integer(1)
    polynomial = sp.Poly(
        sp.expand(numerator), *parameters, domain=sp.QQ
    )
    if polynomial.is_zero:
        return sp.Integer(0)
    primitive = polynomial.primitive()[1]
    leading = primitive.LC()
    if leading < 0:
        primitive = -primitive
    return primitive.as_expr()


def _normalize_system(
    equations: tuple[sp.Expr, ...] | list[sp.Expr],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[sp.Expr, ...]:
    normalized: list[sp.Expr] = []
    for equation in equations:
        value = _normalize_equation(equation, parameters)
        if value == 0:
            continue
        if value not in normalized:
            normalized.append(value)
    return tuple(sorted(normalized, key=sp.default_sort_key))


def _compose_solution(
    prior: dict[sp.Symbol, sp.Expr],
    local: dict[sp.Symbol, sp.Expr],
) -> dict[sp.Symbol, sp.Expr]:
    composed = {
        parameter: sp.expand(value.subs(local))
        for parameter, value in prior.items()
    }
    composed.update({
        parameter: sp.expand(value)
        for parameter, value in local.items()
    })
    return composed


def _linear_graph(
    equations: tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
) -> tuple[
    str,
    dict[sp.Symbol, sp.Expr],
    tuple[sp.Symbol, ...],
    dict[str, object],
]:
    matrix, rhs = sp.linear_eq_to_matrix(equations, parameters)
    rank = matrix.rank()
    augmented = matrix.row_join(rhs)
    augmented_rank = augmented.rank()
    receipt: dict[str, object] = {
        "equation_count": len(equations),
        "matrix_shape": list(matrix.shape),
        "rank": rank,
        "augmented_rank": augmented_rank,
    }
    if rank != augmented_rank:
        return "incompatible", {}, (), receipt
    reduced, pivots = augmented.rref()
    if len(parameters) in pivots:
        raise AssertionError("consistent RREF pivoted in the RHS")
    pivot_columns = tuple(
        pivot for pivot in pivots if pivot < len(parameters)
    )
    free_parameters = tuple(
        parameter
        for index, parameter in enumerate(parameters)
        if index not in pivot_columns
    )
    solution = {
        parameters[pivot]: sp.expand(
            reduced[row, len(parameters)]
            - sum(
                reduced[row, column] * parameters[column]
                for column in range(len(parameters))
                if column not in pivot_columns
            )
        )
        for row, pivot in enumerate(pivot_columns)
    }
    if not all(
        sp.expand(equation.subs(solution)) == 0
        for equation in equations
    ):
        raise AssertionError("RREF graph failed its source equations")
    receipt["pivot_parameters"] = [
        str(parameters[index]) for index in pivot_columns
    ]
    receipt["free_parameters"] = [
        str(parameter) for parameter in free_parameters
    ]
    return "compatible", solution, free_parameters, receipt


def _factor_choices(
    equation: sp.Expr,
    parameters: tuple[sp.Symbol, ...],
) -> tuple[sp.Expr, ...]:
    _constant, factors = sp.Poly(
        equation, *parameters, domain=sp.QQ
    ).factor_list()
    return tuple(
        factor.monic().as_expr()
        for factor, _multiplicity in factors
    )


def _branch_key(
    branch: AffineBranch | AlgebraicBranch,
) -> tuple[object, ...]:
    solution = tuple(sorted(
        (
            str(parameter),
            sp.srepr(sp.expand(value)),
        )
        for parameter, value in branch.solution.items()
    ))
    if isinstance(branch, AffineBranch):
        return ("affine", solution)
    return (
        "algebraic",
        solution,
        tuple(sp.srepr(equation) for equation in branch.equations),
    )


def _affine_branch_is_contained(
    candidate: AffineBranch,
    container: AffineBranch,
) -> bool:
    """Whether every point of ``candidate`` lies in ``container``."""
    return all(
        sp.expand(
            (parameter - value).subs(candidate.solution)
        ) == 0
        for parameter, value in container.solution.items()
    )


def _remove_redundant_affine_branches(
    branches: tuple[AffineBranch, ...],
) -> tuple[AffineBranch, ...]:
    return tuple(
        candidate
        for index, candidate in enumerate(branches)
        if not any(
            index != other_index
            and _affine_branch_is_contained(candidate, container)
            for other_index, container in enumerate(branches)
        )
    )


def decompose_factor_affine_locus(
    equations: list[sp.Expr] | tuple[sp.Expr, ...],
    parameters: tuple[sp.Symbol, ...],
) -> LocusDecomposition:
    """Decompose a polynomial locus as far as factors and RREF permit."""
    pending: list[
        tuple[
            dict[sp.Symbol, sp.Expr],
            tuple[sp.Symbol, ...],
            tuple[sp.Expr, ...],
        ]
    ] = [({}, parameters, tuple(equations))]
    affine: list[AffineBranch] = []
    unresolved: list[AlgebraicBranch] = []
    dead_branches = 0
    factor_splits = 0
    linear_receipts: list[dict[str, object]] = []

    while pending:
        prior_solution, free_parameters, raw_equations = pending.pop()
        substituted = tuple(
            sp.expand(equation.subs(prior_solution))
            for equation in raw_equations
        )
        normalized = _normalize_system(substituted, free_parameters)
        if any(
            not equation.free_symbols and equation != 0
            for equation in normalized
        ):
            dead_branches += 1
            continue
        if not normalized:
            affine.append(AffineBranch(
                solution=prior_solution,
                free_parameters=free_parameters,
            ))
            continue

        linear = tuple(
            equation
            for equation in normalized
            if sp.Poly(
                equation, *free_parameters, domain=sp.QQ
            ).total_degree() <= 1
        )
        if linear:
            status, local, new_free, receipt = _linear_graph(
                linear, free_parameters
            )
            linear_receipts.append(receipt)
            if status == "incompatible":
                dead_branches += 1
                continue
            pending.append((
                _compose_solution(prior_solution, local),
                new_free,
                normalized,
            ))
            continue

        split_equation: sp.Expr | None = None
        split_factors: tuple[sp.Expr, ...] = ()
        for equation in normalized:
            factors = _factor_choices(equation, free_parameters)
            if len(factors) > 1 or (
                len(factors) == 1
                and sp.Poly(
                    equation, *free_parameters, domain=sp.QQ
                ).total_degree()
                != sp.Poly(
                    factors[0], *free_parameters, domain=sp.QQ
                ).total_degree()
            ):
                split_equation = equation
                split_factors = factors
                break
        if split_equation is not None:
            factor_splits += 1
            remainder = tuple(
                equation
                for equation in normalized
                if equation != split_equation
            )
            for factor in split_factors:
                pending.append((
                    prior_solution,
                    free_parameters,
                    (*remainder, factor),
                ))
            continue

        unresolved.append(AlgebraicBranch(
            solution=prior_solution,
            free_parameters=free_parameters,
            equations=normalized,
        ))

    unique_affine = _remove_redundant_affine_branches(tuple({
        _branch_key(branch): branch for branch in affine
    }.values()))
    unique_unresolved = tuple({
        _branch_key(branch): branch for branch in unresolved
    }.values())
    if unique_unresolved:
        status = "unresolved_algebraic_locus"
    elif unique_affine:
        status = "compatible"
    else:
        status = "incompatible"
    return LocusDecomposition(
        status=status,
        affine_branches=unique_affine,
        unresolved_branches=unique_unresolved,
        receipt={
            "coverage": (
                "exact_factor_union_with_affine_rref"
                if not unique_unresolved
                else "exact_factor_union_with_unresolved_nonlinear_branches"
            ),
            "decomposition_coverage_certified": True,
            "affine_graph_coverage_certified": not unique_unresolved,
            "affine_branch_count": len(unique_affine),
            "unresolved_branch_count": len(unique_unresolved),
            "dead_branch_count": dead_branches,
            "factor_split_count": factor_splits,
            "linear_rref_receipts": linear_receipts,
        },
    )


if __name__ == "__main__":
    x, y, z = sp.symbols("x y z")
    cases = {
        "affine": ([x + 2 * y - 1], (x, y)),
        "square": ([x**2], (x,)),
        "union": ([x * y], (x, y)),
        "intersecting_union": ([x * y, x * z], (x, y, z)),
        "irreducible": ([x**2 + y**2 + 1], (x, y)),
        "empty": ([sp.Integer(1)], (x,)),
    }
    for name, (case_equations, case_parameters) in cases.items():
        result = decompose_factor_affine_locus(
            case_equations, case_parameters
        )
        print(
            name,
            result.status,
            len(result.affine_branches),
            len(result.unresolved_branches),
        )
