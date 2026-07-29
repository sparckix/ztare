#!/usr/bin/env python3
"""Exact finite-point obstruction to lowering the second source jet.

The target class is deliberately enlarged to arbitrary pairs in Q(P,Q).
At safe rational specializations of (P,Q), a global base-field-valued
residual must have zero w and w^2 coordinates in
Q[w]/(w^3-w^2+P*w-Q).  Inconsistency at finitely many exact specializations
therefore excludes a global lower-degree source correction.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import sympy as sp
from sympy.matrices.exceptions import NonInvertibleMatrixError
from sympy.polys.matrices import DomainMatrix

from equivariant_full_gauge_third_jet import _family_jets, _solve_source


Element = tuple[sp.Rational, sp.Rational, sp.Rational]


def _add(left: Element, right: Element) -> Element:
    return tuple(a + b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def _scale(value: Element, scalar: sp.Rational) -> Element:
    return tuple(scalar * item for item in value)  # type: ignore[return-value]


def _mul(left: Element, right: Element, p: sp.Rational, q: sp.Rational) -> Element:
    raw = [sp.Rational(0) for _ in range(5)]
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            raw[i + j] += a * b
    # w^d = w^(d-1) - p*w^(d-2) + q*w^(d-3), d >= 3.
    for degree in range(4, 2, -1):
        coefficient = raw[degree]
        raw[degree] = 0
        raw[degree - 1] += coefficient
        raw[degree - 2] -= p * coefficient
        raw[degree - 3] += q * coefficient
    return raw[0], raw[1], raw[2]


def _inverse(value: Element, p: sp.Rational, q: sp.Rational) -> Element:
    basis: tuple[Element, ...] = (
        (sp.Rational(1), sp.Rational(0), sp.Rational(0)),
        (sp.Rational(0), sp.Rational(1), sp.Rational(0)),
        (sp.Rational(0), sp.Rational(0), sp.Rational(1)),
    )
    matrix = sp.Matrix.hstack(
        *(sp.Matrix(_mul(value, item, p, q)) for item in basis)
    )
    solution = matrix.inv() * sp.Matrix([1, 0, 0])
    return tuple(sp.Rational(item) for item in solution)  # type: ignore[return-value]


def _powers(
    value: Element, maximum: int, p: sp.Rational, q: sp.Rational
) -> list[Element]:
    result: list[Element] = [(sp.Rational(1), sp.Rational(0), sp.Rational(0))]
    for _ in range(maximum):
        result.append(_mul(result[-1], value, p, q))
    return result


def _evaluate_poly(
    expression: sp.Expr,
    v: sp.Symbol,
    t: sp.Symbol,
    v_powers: list[Element],
    t_powers: list[Element],
    p: sp.Rational,
    q: sp.Rational,
) -> Element:
    value: Element = (sp.Rational(0), sp.Rational(0), sp.Rational(0))
    for (i, j), coefficient in sp.Poly(expression, v, t, domain=sp.QQ).terms():
        monomial = _mul(v_powers[i], t_powers[j], p, q)
        value = _add(value, _scale(monomial, sp.Rational(coefficient)))
    return value


def _monomials(maximum_degree: int) -> list[tuple[int, int]]:
    return [
        (i, total - i)
        for total in range(maximum_degree + 1)
        for i in range(total + 1)
    ]


def _safe_point_rows(
    p_value: int,
    q_value: int,
    *,
    maximum_degree: int,
    v: sp.Symbol,
    t: sp.Symbol,
    jacobian: sp.Matrix,
    residual: tuple[sp.Expr, sp.Expr],
    monomials: list[tuple[int, int]],
) -> tuple[list[list[sp.Rational]], list[sp.Rational]] | None:
    p = sp.Rational(p_value)
    q = sp.Rational(q_value)
    w: Element = (sp.Rational(0), sp.Rational(1), sp.Rational(0))
    gamma: Element = (p, sp.Rational(-2), sp.Rational(3))
    try:
        gamma_inverse = _inverse(gamma, p, q)
    except (ValueError, ZeroDivisionError, NonInvertibleMatrixError):
        return None
    v_value = _add(
        _mul(w, gamma_inverse, p, q),
        (sp.Rational(-1), sp.Rational(0), sp.Rational(0)),
    )
    t_value = _add(
        _add(gamma, (sp.Rational(-1), sp.Rational(0), sp.Rational(0))),
        _scale(v_value, sp.Rational(3, 2)),
    )
    v_powers = _powers(v_value, maximum_degree + 6, p, q)
    t_powers = _powers(t_value, maximum_degree + 6, p, q)
    jacobian_values = [
        [
            _evaluate_poly(
                jacobian[row, column], v, t, v_powers, t_powers, p, q
            )
            for column in range(2)
        ]
        for row in range(2)
    ]
    residual_values = [
        _evaluate_poly(item, v, t, v_powers, t_powers, p, q)
        for item in residual
    ]
    monomial_values = [
        _mul(v_powers[i], t_powers[j], p, q) for i, j in monomials
    ]

    rows: list[list[sp.Rational]] = [[] for _ in range(4)]
    rhs = [
        residual_values[0][1],
        residual_values[0][2],
        residual_values[1][1],
        residual_values[1][2],
    ]
    for source_component in range(2):
        for monomial in monomial_values:
            image = [
                _mul(jacobian_values[target][source_component], monomial, p, q)
                for target in range(2)
            ]
            rows[0].append(image[0][1])
            rows[1].append(image[0][2])
            rows[2].append(image[1][1])
            rows[3].append(image[1][2])
    return rows, rhs


def _candidate_points() -> Iterable[tuple[int, int]]:
    for radius in range(1, 10):
        for p in range(-radius, radius + 1):
            for q in range(-radius, radius + 1):
                if max(abs(p), abs(q)) == radius:
                    yield p, q


def _coefficient_vector(
    source: tuple[sp.Expr, sp.Expr],
    v: sp.Symbol,
    t: sp.Symbol,
    monomials: list[tuple[int, int]],
) -> sp.Matrix:
    rows: list[sp.Rational] = []
    for component in source:
        polynomial = sp.Poly(component, v, t, domain=sp.QQ)
        rows.extend(sp.Rational(polynomial.coeff_monomial(v**i * t**j))
                    for i, j in monomials)
    return sp.Matrix(rows)


def _degree_indices(
    degree: int, *, full_monomial_count: int
) -> list[int]:
    count = len(_monomials(degree))
    return list(range(count)) + list(range(full_monomial_count, full_monomial_count + count))


def _rank_status(
    matrix: sp.Matrix, rhs: sp.Matrix, indices: list[int]
) -> tuple[int, int]:
    selected = matrix[:, indices]
    rank = DomainMatrix.from_Matrix(selected).rank()
    augmented_rank = DomainMatrix.from_Matrix(selected.row_join(rhs)).rank()
    return rank, augmented_rank


def _general_solution(
    matrix: sp.Matrix, rhs: sp.Matrix
) -> tuple[sp.Matrix, tuple[sp.Symbol, ...]]:
    solution_set = sp.linsolve((matrix, rhs))
    if solution_set is sp.EmptySet:
        raise ValueError("linear system is inconsistent")
    solution = next(iter(solution_set))
    parameters = tuple(sorted(
        set().union(*(item.free_symbols for item in solution)),
        key=str,
    ))
    return sp.Matrix(solution), parameters


def _particular_solution(matrix: sp.Matrix, rhs: sp.Matrix) -> sp.Matrix:
    solution, parameters = _general_solution(matrix, rhs)
    substitution = {parameter: sp.Rational(0) for parameter in parameters}
    return sp.Matrix([sp.cancel(item.subs(substitution)) for item in solution])


def _source_from_vector(
    vector: sp.Matrix,
    v: sp.Symbol,
    t: sp.Symbol,
    monomials: list[tuple[int, int]],
) -> tuple[sp.Expr, sp.Expr]:
    count = len(monomials)
    components = []
    for offset in (0, count):
        components.append(sp.expand(sum(
            vector[offset + index] * v**i * t**j
            for index, (i, j) in enumerate(monomials)
        )))
    return components[0], components[1]


def _generic_field_coordinates(
    expression: sp.Expr, v: sp.Symbol, t: sp.Symbol
) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    p, q, w = sp.symbols("P Q w")
    gamma = p - 2 * w + 3 * w**2
    v_inverse = w / gamma - 1
    t_inverse = gamma - 1 + sp.Rational(3, 2) * v_inverse
    substituted = sp.cancel(expression.subs({v: v_inverse, t: t_inverse}))
    numerator, denominator = sp.fraction(substituted)
    parameters = sorted(
        expression.free_symbols - {v, t, p, q, w},
        key=str,
    )
    field = sp.QQ.frac_field(p, q, *parameters)
    cubic = sp.Poly(w**3 - w**2 + p * w - q, w, domain=field)
    numerator_poly = sp.Poly(numerator, w, domain=field).rem(cubic)
    denominator_poly = sp.Poly(denominator, w, domain=field).rem(cubic)
    inverse = sp.invert(denominator_poly, cubic)
    remainder = (numerator_poly * inverse).rem(cubic)
    return tuple(sp.cancel(remainder.nth(index).as_expr()) for index in range(3))  # type: ignore[return-value]


def _polynomial_linear_system(
    columns: list[tuple[sp.Expr, sp.Expr]],
    rhs: tuple[sp.Expr, sp.Expr],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[sp.Matrix, sp.Matrix, list[tuple[int, int, int]]]:
    polynomials = [
        [sp.Poly(component, v, t, domain=sp.QQ) for component in pair]
        for pair in columns
    ]
    rhs_polynomials = [
        sp.Poly(component, v, t, domain=sp.QQ) for component in rhs
    ]
    row_keys = sorted({
        (component, i, j)
        for component in range(2)
        for polynomial in (
            [pair[component] for pair in polynomials]
            + [rhs_polynomials[component]]
        )
        for (i, j) in polynomial.monoms()
    })
    matrix_rows = []
    rhs_rows = []
    for component, i, j in row_keys:
        monomial = v**i * t**j
        matrix_rows.append([
            polynomial_pair[component].coeff_monomial(monomial)
            for polynomial_pair in polynomials
        ])
        rhs_rows.append(rhs_polynomials[component].coeff_monomial(monomial))
    return sp.Matrix(matrix_rows), sp.Matrix(rhs_rows), row_keys


def _direct_hamiltonian_minimum(
    *,
    v: sp.Symbol,
    t: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    jacobian: sp.Matrix,
    residual: tuple[sp.Expr, sp.Expr],
    maximum_source_degree: int = 11,
    maximum_hamiltonian_degree: int = 4,
) -> dict[str, object]:
    source_monomials = _monomials(maximum_source_degree)
    u_monomials = [
        monomial for monomial in source_monomials if monomial != (0, 0)
    ]
    v_monomials = [
        monomial
        for monomial in source_monomials
        if monomial not in {(0, 0), (1, 0)}
    ]
    hamiltonian_monomials = [
        (i, total - i)
        for total in range(1, maximum_hamiltonian_degree + 1)
        for i in range(total + 1)
    ]
    columns: list[tuple[sp.Expr, sp.Expr]] = []
    metadata: list[tuple[str, int, tuple[int, int]]] = []
    for monomial in u_monomials:
        value = v**monomial[0] * t**monomial[1]
        columns.append((
            sp.expand(jacobian[0, 0] * value),
            sp.expand(jacobian[1, 0] * value),
        ))
        metadata.append(("U", sum(monomial), monomial))
    for monomial in v_monomials:
        value = v**monomial[0] * t**monomial[1]
        columns.append((
            sp.expand(jacobian[0, 1] * value),
            sp.expand(jacobian[1, 1] * value),
        ))
        metadata.append(("V", sum(monomial), monomial))
    p, q = sp.symbols("P Q")
    for monomial in hamiltonian_monomials:
        i, j = monomial
        first = (
            j * p**i * q ** (j - 1) if j else sp.Rational(0)
        )
        second = (
            -i * p ** (i - 1) * q**j if i else sp.Rational(0)
        )
        columns.append((
            sp.expand(first.subs({p: p0, q: q0})),
            sp.expand(second.subs({p: p0, q: q0})),
        ))
        metadata.append(("K", sum(monomial), monomial))

    matrix, rhs, _row_keys = _polynomial_linear_system(columns, residual, v, t)
    checks: dict[str, dict[str, object]] = {}
    best: tuple[int, int, list[int], sp.Matrix] | None = None
    for hamiltonian_degree in range(1, maximum_hamiltonian_degree + 1):
        low = -1
        high = maximum_source_degree
        local_checks: dict[int, tuple[int, int]] = {}
        while high - low > 1:
            source_degree = (low + high) // 2
            indices = [
                index
                for index, (kind, degree, _monomial) in enumerate(metadata)
                if (
                    (kind in {"U", "V"} and degree <= source_degree)
                    or (kind == "K" and degree <= hamiltonian_degree)
                )
            ]
            selected = matrix[:, indices]
            rank = DomainMatrix.from_Matrix(selected).rank()
            augmented_rank = DomainMatrix.from_Matrix(
                selected.row_join(rhs)
            ).rank()
            local_checks[source_degree] = (rank, augmented_rank)
            if rank == augmented_rank:
                high = source_degree
            else:
                low = source_degree
        final_indices = [
            index
            for index, (kind, degree, _monomial) in enumerate(metadata)
            if (
                (kind in {"U", "V"} and degree <= high)
                or (kind == "K" and degree <= hamiltonian_degree)
            )
        ]
        final_matrix = matrix[:, final_indices]
        solution = _particular_solution(final_matrix, rhs)
        checks[str(hamiltonian_degree)] = {
            "minimum_source_degree": high,
            "rank_checks": {
                str(degree): {
                    "rank": rank,
                    "augmented_rank": augmented,
                    "consistent": rank == augmented,
                }
                for degree, (rank, augmented) in sorted(local_checks.items())
            },
        }
        if best is None or high < best[0]:
            best = (
                high,
                hamiltonian_degree,
                final_indices,
                solution,
            )
    if best is None:
        raise RuntimeError("Hamiltonian search produced no bounded system")

    source_degree, hamiltonian_degree, indices, solution = best
    source_u = sp.Rational(0)
    source_v = sp.Rational(0)
    hamiltonian = sp.Rational(0)
    for coefficient, index in zip(solution, indices, strict=True):
        kind, _degree, (i, j) = metadata[index]
        if kind == "U":
            source_u += coefficient * v**i * t**j
        elif kind == "V":
            source_v += coefficient * v**i * t**j
        else:
            hamiltonian += coefficient * p**i * q**j
    source = (sp.expand(source_u), sp.expand(source_v))
    hamiltonian = sp.expand(hamiltonian)
    target = (
        sp.diff(hamiltonian, q),
        -sp.diff(hamiltonian, p),
    )
    target_at_seed = (
        sp.expand(target[0].subs({p: p0, q: q0})),
        sp.expand(target[1].subs({p: p0, q: q0})),
    )
    assert all(
        sp.cancel(item) == 0
        for item in (
            jacobian * sp.Matrix(source)
            + sp.Matrix(target_at_seed)
            - sp.Matrix(residual)
        )
    )
    assert (
        source[0].subs({v: 0, t: 0}) == 0
        and source[1].subs({v: 0, t: 0}) == 0
        and sp.diff(source[1].subs(t, 0), v).subs(v, 0) == 0
        and sp.cancel(sp.diff(target[0], p) + sp.diff(target[1], q)) == 0
    )
    return {
        "maximum_hamiltonian_degree_tested": maximum_hamiltonian_degree,
        "minimum_source_degree": source_degree,
        "witness_hamiltonian_degree": hamiltonian_degree,
        "checks": checks,
        "source_component_degrees": [
            sp.Poly(item, v, t).total_degree() for item in source
        ],
        "source_component_sha256": [
            hashlib.sha256(str(item).encode("utf-8")).hexdigest()
            for item in source
        ],
        "source_components": [str(item) for item in source],
        "hamiltonian": str(hamiltonian),
        "hamiltonian_sha256": hashlib.sha256(
            str(hamiltonian).encode("utf-8")
        ).hexdigest(),
        "target_pair": [str(item) for item in target],
        "source_lift_ideals": True,
        "target_pair_polynomial": True,
        "target_pair_divergence_free": True,
        "matrix_sha256": _matrix_sha(matrix),
        "rhs_sha256": _matrix_sha(rhs),
    }


def _poly_pair_terms(
    pair: tuple[sp.Expr | sp.Poly, sp.Expr | sp.Poly],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[sp.Poly, sp.Poly]:
    return tuple(
        item if isinstance(item, sp.Poly) else sp.Poly(item, v, t, domain=sp.QQ)
        for item in pair
    )  # type: ignore[return-value]


def _sparse_polynomial_system(
    columns: list[tuple[sp.Expr | sp.Poly, sp.Expr | sp.Poly]],
    rhs: tuple[sp.Expr, sp.Expr],
    v: sp.Symbol,
    t: sp.Symbol,
) -> tuple[DomainMatrix, DomainMatrix, list[tuple[int, int, int]]]:
    """Build the coefficient system without materializing a dense Matrix."""

    polynomial_columns = [
        _poly_pair_terms(pair, v, t) for pair in columns
    ]
    rhs_polynomials = _poly_pair_terms(rhs, v, t)
    row_keys = sorted({
        (component, i, j)
        for component in range(2)
        for polynomial in (
            [pair[component] for pair in polynomial_columns]
            + [rhs_polynomials[component]]
        )
        for i, j in polynomial.monoms()
    })
    row_index = {key: index for index, key in enumerate(row_keys)}
    matrix_entries: dict[int, dict[int, sp.Rational]] = {}
    for column_index, pair in enumerate(polynomial_columns):
        for component, polynomial in enumerate(pair):
            for (i, j), coefficient in polynomial.terms():
                if coefficient == 0:
                    continue
                row = row_index[(component, i, j)]
                matrix_entries.setdefault(row, {})[
                    column_index
                ] = sp.Rational(coefficient)
    rhs_entries: dict[int, dict[int, sp.Rational]] = {}
    for component, polynomial in enumerate(rhs_polynomials):
        for (i, j), coefficient in polynomial.terms():
            if coefficient == 0:
                continue
            rhs_entries.setdefault(row_index[(component, i, j)], {})[
                0
            ] = sp.Rational(coefficient)
    matrix = DomainMatrix.from_dict_sympy(
        len(row_keys), len(columns), matrix_entries
    ).to_field()
    rhs_matrix = DomainMatrix.from_dict_sympy(
        len(row_keys), 1, rhs_entries
    ).to_field()
    return matrix, rhs_matrix, row_keys


def _polynomial_columns_sha256(
    columns: list[tuple[sp.Expr | sp.Poly, sp.Expr | sp.Poly]],
    v: sp.Symbol,
    t: sp.Symbol,
) -> str:
    payload = []
    for pair in columns:
        polynomial_pair = _poly_pair_terms(pair, v, t)
        payload.append([
            [
                [i, j, str(coefficient)]
                for (i, j), coefficient in polynomial.terms()
            ]
            for polynomial in polynomial_pair
        ])
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_hamiltonian_stabilization(
    maximum_hamiltonian_degree: int = 12,
) -> dict[str, object]:
    """Test the bounded pullback image for higher Hamiltonian degrees."""

    data = _family_jets()
    v, t = data["symbols"]
    p0, p2 = data["P"][0], data["P"][2]
    q0, q2 = data["Q"][0], data["Q"][2]
    residual = (
        sp.cancel(p2 + p0**2 / 24),
        sp.cancel(q2 + p0 * q0 / 12),
    )
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    source_monomials = _monomials(4)
    source_columns: list[tuple[sp.Expr, sp.Expr]] = []
    for i, j in source_monomials:
        if (i, j) != (0, 0):
            monomial = v**i * t**j
            source_columns.append((
                sp.expand(jacobian[0, 0] * monomial),
                sp.expand(jacobian[1, 0] * monomial),
            ))
    for i, j in source_monomials:
        if (i, j) not in {(0, 0), (1, 0)}:
            monomial = v**i * t**j
            source_columns.append((
                sp.expand(jacobian[0, 1] * monomial),
                sp.expand(jacobian[1, 1] * monomial),
            ))

    p0_poly = sp.Poly(p0, v, t, domain=sp.QQ)
    q0_poly = sp.Poly(q0, v, t, domain=sp.QQ)
    p_powers = [sp.Poly(1, v, t, domain=sp.QQ)]
    q_powers = [sp.Poly(1, v, t, domain=sp.QQ)]
    for _ in range(maximum_hamiltonian_degree):
        p_powers.append(p_powers[-1] * p0_poly)
        q_powers.append(q_powers[-1] * q0_poly)

    target_columns: list[tuple[sp.Poly, sp.Poly]] = []
    target_degrees: list[int] = []
    for total in range(1, maximum_hamiltonian_degree + 1):
        for i in range(total + 1):
            j = total - i
            first = (
                j * p_powers[i] * q_powers[j - 1]
                if j
                else sp.Poly(0, v, t, domain=sp.QQ)
            )
            second = (
                -i * p_powers[i - 1] * q_powers[j]
                if i
                else sp.Poly(0, v, t, domain=sp.QQ)
            )
            target_columns.append((
                first,
                second,
            ))
            target_degrees.append(total)

    source_count = len(source_columns)
    all_columns: list[tuple[sp.Expr | sp.Poly, sp.Expr | sp.Poly]] = (
        source_columns + target_columns
    )
    matrix, rhs, row_keys = _sparse_polynomial_system(
        all_columns, residual, v, t
    )
    high_rows = [
        index
        for index, (component, i, j) in enumerate(row_keys)
        if (component == 0 and i + j > 8)
        or (component == 1 and i + j > 10)
    ]
    records: dict[int, dict[str, object]] = {}
    for degree in range(3, maximum_hamiltonian_degree + 1):
        target_local_indices = [
            index
            for index, target_degree in enumerate(target_degrees)
            if target_degree <= degree
        ]
        target_indices = [
            source_count + index for index in target_local_indices
        ]
        target_matrix = matrix.extract(
            list(range(matrix.shape[0])), target_indices
        )
        target_high = target_matrix.extract(
            high_rows, list(range(target_matrix.shape[1]))
        )
        target_rank = target_matrix.rank()
        target_high_rank = target_high.rank()
        combined_indices = list(range(source_count)) + target_indices
        combined = matrix.extract(
            list(range(matrix.shape[0])), combined_indices
        )
        rank = combined.rank()
        augmented_rank = DomainMatrix.hstack(combined, rhs).rank()
        records[degree] = {
            "target_column_count": len(target_indices),
            "target_rank": target_rank,
            "target_high_rank": target_high_rank,
            "bounded_target_image_rank": target_rank - target_high_rank,
            "source_plus_target_rank": rank,
            "augmented_rank": augmented_rank,
            "source_degree_at_most_4_excluded": augmented_rank > rank,
        }
    final_image_rank = int(
        records[maximum_hamiltonian_degree]["bounded_target_image_rank"]
    )
    stable_from = next(
        degree
        for degree in records
        if all(
            int(records[later]["bounded_target_image_rank"]) == final_image_rank
            for later in records
            if later >= degree
        )
    )
    return {
        "schema": "axiompack.jacobian_second_jet_hamiltonian_stabilization.v1",
        "source_degree_bound": 4,
        "target_component_degree_window": [8, 10],
        "maximum_hamiltonian_degree": maximum_hamiltonian_degree,
        "records": {
            str(degree): record for degree, record in records.items()
        },
        "bounded_target_image_stable_from": stable_from,
        "bounded_target_image_rank": final_image_rank,
        "residual_excluded_at_every_bound": all(
            bool(record["source_degree_at_most_4_excluded"])
            for record in records.values()
        ),
        "matrix_sha256": _polynomial_columns_sha256(all_columns, v, t),
        "rhs_sha256": _polynomial_columns_sha256(
            [(residual[0], residual[1])], v, t
        ),
        "claim_boundary": (
            "exact finite Hamiltonian-degree stabilization through the declared "
            "bound; an all-degree subduction argument remains required"
        ),
    }


def run_filtered_coordinate_certificate() -> dict[str, object]:
    """Certify the all-degree target chart and a finite dual obstruction."""

    data = _family_jets()
    v, t = data["symbols"]
    p0, p2 = data["P"][0], data["P"][2]
    q0, q2 = data["Q"][0], data["Q"][2]
    residual = (
        sp.cancel(p2 + p0**2 / 24),
        sp.cancel(q2 + p0 * q0 / 12),
    )
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])

    gamma, w = sp.symbols("gamma w")
    p, q = sp.symbols("P Q")
    p_gamma_w = gamma + 2 * w - 3 * w**2
    q_gamma_w = w * gamma + w**2 - 2 * w**3
    filtered_coordinate = (
        4 * p**3 - 18 * p * q + 27 * q**2 - p**2 + 4 * q
    )
    filtered_at_gamma_w = sp.expand(
        filtered_coordinate.subs({p: p_gamma_w, q: q_gamma_w})
    )
    filtered_factor = sp.expand(
        gamma**2 * (3 * p_gamma_w + gamma - 1)
    )
    assert sp.cancel(filtered_at_gamma_w - filtered_factor) == 0
    quadratic_relation = sp.expand(
        27 * q**2
        - (
            filtered_coordinate
            + (18 * p - 4) * q
            - 4 * p**3
            + p**2
        )
    )
    assert quadratic_relation == 0

    scalar_degree_8_basis = [
        sp.Integer(1), p, p**2, q, filtered_coordinate
    ]
    scalar_degree_10_basis = scalar_degree_8_basis + [
        p * q, p * filtered_coordinate
    ]
    hamiltonian_basis = [
        p, q, p**2, p * q, q**2, p**3, p**2 * q
    ]

    source_monomials = _monomials(4)
    source_columns: list[tuple[sp.Expr, sp.Expr]] = []
    source_metadata: list[tuple[str, tuple[int, int]]] = []
    for i, j in source_monomials:
        if (i, j) == (0, 0):
            continue
        monomial = v**i * t**j
        source_columns.append((
            sp.expand(jacobian[0, 0] * monomial),
            sp.expand(jacobian[1, 0] * monomial),
        ))
        source_metadata.append(("U", (i, j)))
    for i, j in source_monomials:
        if (i, j) in {(0, 0), (1, 0)}:
            continue
        monomial = v**i * t**j
        source_columns.append((
            sp.expand(jacobian[0, 1] * monomial),
            sp.expand(jacobian[1, 1] * monomial),
        ))
        source_metadata.append(("V", (i, j)))

    target_columns: list[tuple[sp.Expr, sp.Expr]] = []
    for hamiltonian in hamiltonian_basis:
        target_columns.append((
            sp.expand(sp.diff(hamiltonian, q).subs({p: p0, q: q0})),
            sp.expand(-sp.diff(hamiltonian, p).subs({p: p0, q: q0})),
        ))
    all_columns = source_columns + target_columns
    matrix, rhs_matrix, row_keys = _sparse_polynomial_system(
        all_columns, residual, v, t
    )
    augmented = DomainMatrix.hstack(matrix, rhs_matrix)
    matrix_rank = matrix.rank()
    augmented_rank = augmented.rank()
    assert augmented_rank == matrix_rank + 1

    _rref, independent_rows = augmented.transpose().rref()
    selected_rows = list(independent_rows)
    assert len(selected_rows) == augmented_rank
    selected = augmented.extract(
        selected_rows, list(range(augmented.shape[1]))
    ).to_Matrix()
    dual_selected = selected.transpose().inv() * sp.eye(
        augmented_rank
    )[:, -1]
    dual = sp.zeros(matrix.shape[0], 1)
    for row, value in zip(selected_rows, dual_selected, strict=True):
        dual[row] = sp.Rational(value)
    matrix_sympy = matrix.to_Matrix()
    rhs_sympy = rhs_matrix.to_Matrix()
    assert matrix_sympy.transpose() * dual == sp.zeros(matrix.shape[1], 1)
    assert (rhs_sympy.transpose() * dual)[0] == 1

    denominators = [
        sp.denom(value) for value in dual if value != 0
    ]
    common_denominator = sp.ilcm(*[int(value) for value in denominators])
    integer_dual = [
        int(value * common_denominator) for value in dual
    ]
    common_factor = int(sp.gcd_list([
        sp.Integer(abs(value)) for value in integer_dual if value
    ]))
    integer_dual = [value // common_factor for value in integer_dual]
    residual_pairing = int(
        (rhs_sympy.transpose() * sp.Matrix(integer_dual))[0]
    )
    if residual_pairing < 0:
        integer_dual = [-value for value in integer_dual]
        residual_pairing = -residual_pairing
    assert matrix_sympy.transpose() * sp.Matrix(integer_dual) == sp.zeros(
        matrix.shape[1], 1
    )
    assert residual_pairing > 0
    dual_support = [
        {
            "component": row_keys[index][0],
            "v_degree": row_keys[index][1],
            "t_degree": row_keys[index][2],
            "coefficient": coefficient,
        }
        for index, coefficient in enumerate(integer_dual)
        if coefficient
    ]

    return {
        "schema": "axiompack.jacobian_filtered_target_coordinate.v1",
        "filtered_coordinate": str(filtered_coordinate),
        "filtered_coordinate_pullback": str(filtered_factor),
        "filtered_coordinate_pullback_sha256": hashlib.sha256(
            str(filtered_factor).encode("utf-8")
        ).hexdigest(),
        "quadratic_normal_form_relation": (
            "27*Q^2=C+(18*P-4)*Q-4*P^3+P^2"
        ),
        "normal_form": "A(P,C)+Q*B(P,C)",
        "normal_monomial_degrees": {
            "without_Q": "4*a+6*c",
            "with_Q": "6+4*a+6*c",
        },
        "scalar_degree_8_basis": [
            str(item) for item in scalar_degree_8_basis
        ],
        "scalar_degree_10_basis": [
            str(item) for item in scalar_degree_10_basis
        ],
        "hamiltonian_basis_mod_constants": [
            str(item) for item in hamiltonian_basis
        ],
        "source_column_count": len(source_columns),
        "source_column_metadata": [
            {"component": kind, "monomial": list(monomial)}
            for kind, monomial in source_metadata
        ],
        "target_column_count": len(target_columns),
        "coefficient_row_count": matrix.shape[0],
        "matrix_rank": matrix_rank,
        "augmented_rank": augmented_rank,
        "dual_support": dual_support,
        "dual_support_size": len(dual_support),
        "dual_residual_pairing": residual_pairing,
        "dual_annihilates_every_column": True,
        "matrix_sha256": _polynomial_columns_sha256(all_columns, v, t),
        "rhs_sha256": _polynomial_columns_sha256(
            [(residual[0], residual[1])], v, t
        ),
        "claim_boundary": (
            "all polynomial Hamiltonians in the component window reduce to "
            "the declared seven-dimensional basis; the dual certificate "
            "excludes source degree at most four for this second jet"
        ),
    }


def _matrix_sha(matrix: sp.Matrix) -> str:
    payload = json.dumps(
        [[str(item) for item in row] for row in matrix.tolist()],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run() -> dict[str, object]:
    data = _family_jets()
    v, t = data["symbols"]
    p0, p2 = data["P"][0], data["P"][2]
    q0, q2 = data["Q"][0], data["Q"][2]
    residual = (
        sp.cancel(p2 + p0**2 / 24),
        sp.cancel(q2 + p0 * q0 / 12),
    )
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])
    source11 = _solve_source(data, residual)
    assert max(sp.Poly(item, v, t).total_degree() for item in source11) == 11
    assert all(
        sp.cancel(value) == 0
        for value in jacobian * sp.Matrix(source11) - sp.Matrix(residual)
    )

    maximum_degree = 11
    monomials = _monomials(maximum_degree)
    rows: list[list[sp.Rational]] = []
    rhs: list[sp.Rational] = []
    points: list[tuple[int, int]] = []
    degree11_monomial_count = len(monomials)

    for point in _candidate_points():
        evaluated = _safe_point_rows(
            *point,
            maximum_degree=maximum_degree,
            v=v,
            t=t,
            jacobian=jacobian,
            residual=residual,
            monomials=monomials,
        )
        if evaluated is None:
            continue
        point_rows, point_rhs = evaluated
        rows.extend(point_rows)
        rhs.extend(point_rhs)
        points.append(point)
        if len(points) >= 70:
            break

    matrix11 = sp.Matrix(rows)
    rhs_matrix = sp.Matrix(rhs)

    source_vector = _coefficient_vector(source11, v, t, monomials)
    assert matrix11 * source_vector == rhs_matrix

    degree_checks: dict[int, tuple[int, int]] = {}
    low = -1
    high = 10
    rank_high, augmented_high = _rank_status(
        matrix11,
        rhs_matrix,
        _degree_indices(high, full_monomial_count=degree11_monomial_count),
    )
    degree_checks[high] = (rank_high, augmented_high)
    if augmented_high > rank_high:
        raise RuntimeError("degree ten remains inconsistent on the enlarged stack")
    while high - low > 1:
        middle = (low + high) // 2
        rank, augmented_rank = _rank_status(
            matrix11,
            rhs_matrix,
            _degree_indices(
                middle, full_monomial_count=degree11_monomial_count
            ),
        )
        degree_checks[middle] = (rank, augmented_rank)
        if rank == augmented_rank:
            high = middle
        else:
            low = middle

    candidate_degree = high
    candidate_monomials = _monomials(candidate_degree)
    candidate_indices = _degree_indices(
        candidate_degree, full_monomial_count=degree11_monomial_count
    )
    candidate_matrix = matrix11[:, candidate_indices]
    candidate_vector = _particular_solution(candidate_matrix, rhs_matrix)
    candidate_source = _source_from_vector(
        candidate_vector, v, t, candidate_monomials
    )
    target_remainder = tuple(
        sp.cancel(item)
        for item in (
            sp.Matrix(residual) - jacobian * sp.Matrix(candidate_source)
        )
    )
    field_coordinates = [
        _generic_field_coordinates(item, v, t) for item in target_remainder
    ]
    globally_base_valued = all(
        sp.cancel(coordinates[index]) == 0
        for coordinates in field_coordinates
        for index in (1, 2)
    )
    if not globally_base_valued:
        raise RuntimeError("finite-point candidate failed the generic cubic remainder")

    p, q = sp.symbols("P Q")
    target_pair = [coordinates[0] for coordinates in field_coordinates]
    target_pair_polynomial = all(sp.denom(item) == 1 for item in target_pair)
    target_pair_divergence_free = (
        sp.cancel(sp.diff(target_pair[0], p) + sp.diff(target_pair[1], q)) == 0
    )

    admissible_gauge = _direct_hamiltonian_minimum(
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        jacobian=jacobian,
        residual=residual,
    )
    admissible_degree = int(admissible_gauge["minimum_source_degree"])

    return {
        "schema": "axiompack.jacobian_gauge_minimal_second_jet.v1",
        "target_relaxation": "arbitrary_pair_in_Q(P,Q)",
        "inverse_cubic": "w^3-w^2+P*w-Q",
        "points": [[p, q] for p, q in points],
        "point_count": len(points),
        "degree_checks": {
            str(degree): {
                "rank": rank,
                "augmented_rank": augmented,
                "consistent": rank == augmented,
            }
            for degree, (rank, augmented) in sorted(degree_checks.items())
        },
        "lowering_candidate": {
            "degree": candidate_degree,
            "source_monomial_count_per_component": len(candidate_monomials),
            "unknown_count": candidate_matrix.cols,
            "row_count": candidate_matrix.rows,
            "matrix_sha256": _matrix_sha(candidate_matrix),
            "rhs_sha256": _matrix_sha(rhs_matrix),
            "source_component_degrees": [
                sp.Poly(item, v, t).total_degree() for item in candidate_source
            ],
            "source_component_sha256": [
                hashlib.sha256(str(sp.expand(item)).encode("utf-8")).hexdigest()
                for item in candidate_source
            ],
            "globally_base_valued": globally_base_valued,
            "target_pair": [str(item) for item in target_pair],
            "target_pair_polynomial": target_pair_polynomial,
            "target_pair_divergence_free": target_pair_divergence_free,
        },
        "admissible_gauge": admissible_gauge,
        "degree_11": {
            "source_monomial_count_per_component": len(monomials),
            "unknown_count": matrix11.cols,
            "known_witness_solves": True,
            "source_component_degrees": [
                sp.Poly(item, v, t).total_degree() for item in source11
            ],
            "source_component_sha256": [
                hashlib.sha256(str(sp.expand(item)).encode("utf-8")).hexdigest()
                for item in source11
            ],
        },
        "conclusion": (
            "hamiltonian_gauge_lowers_second_source_jet"
            if admissible_degree < 11
            else "second_source_jet_hamiltonian_minimum_degree_is_11"
        ),
        "claim_boundary": (
            "generic cubic reduction certifies rational base-field target "
            "membership; polynomial and Hamiltonian target admissibility are "
            "reported separately; no all-order degree claim"
        ),
        "script_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
