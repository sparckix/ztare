#!/usr/bin/env python3
"""Generic logarithmic-series extension of the gauge-minimized prefix."""
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
    run as run_fourth,
)
from gauge_minimized_third_jet import (  # noqa: E402
    _act,
    _add,
    _hamiltonian_field,
    _monomials,
    _particular_solution,
    _substitute,
    run as run_third,
)


Pair = tuple[sp.Expr, sp.Expr]
Series = list[Pair]
ParameterMonomial = tuple[int, ...]
ParameterPolynomial = dict[ParameterMonomial, sp.Poly]
ParameterPair = tuple[ParameterPolynomial, ParameterPolynomial]
ParameterSeries = list[ParameterPair]


def _zero_pair() -> Pair:
    return sp.Integer(0), sp.Integer(0)


def _operator_series_apply(
    fields: dict[int, Pair],
    series: Series,
    variables: tuple[sp.Symbol, sp.Symbol],
    maximum_order: int,
) -> Series:
    first, second = variables
    result = [_zero_pair() for _ in range(maximum_order + 1)]
    for order in range(maximum_order + 1):
        value = [sp.Integer(0), sp.Integer(0)]
        for field_order, field in fields.items():
            if field_order > order:
                continue
            coefficient = sp.Rational(1, sp.factorial(field_order))
            source = series[order - field_order]
            for component in range(2):
                value[component] += coefficient * (
                    field[0] * sp.diff(source[component], first)
                    + field[1] * sp.diff(source[component], second)
                )
        result[order] = sp.expand(value[0]), sp.expand(value[1])
    return result


def _exp_operator_series(
    fields: dict[int, Pair],
    input_series: Series,
    variables: tuple[sp.Symbol, sp.Symbol],
    maximum_order: int,
) -> Series:
    result = [
        (sp.expand(pair[0]), sp.expand(pair[1]))
        for pair in input_series
    ]
    term = [
        (sp.expand(pair[0]), sp.expand(pair[1]))
        for pair in input_series
    ]
    for power in range(1, maximum_order + 1):
        term = _operator_series_apply(
            fields, term, variables, maximum_order
        )
        if all(pair == _zero_pair() for pair in term):
            break
        coefficient = sp.Rational(1, sp.factorial(power))
        result = [
            _add(result[order], (
                coefficient * term[order][0],
                coefficient * term[order][1],
            ))
            for order in range(maximum_order + 1)
        ]
    return result


def _composed_series(
    *,
    target_fields: dict[int, Pair],
    source_fields: dict[int, Pair],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    maximum_order: int,
) -> Series:
    target_input = [_zero_pair() for _ in range(maximum_order + 1)]
    target_input[0] = p, q
    target_series = _exp_operator_series(
        target_fields, target_input, (p, q), maximum_order
    )
    pulled_back = [
        _substitute(pair, p, q, p0, q0) for pair in target_series
    ]
    return _exp_operator_series(
        source_fields, pulled_back, (v, t), maximum_order
    )


def _parameter_polynomial(
    value: sp.Expr,
    parameters: tuple[sp.Symbol, ...],
    coefficient_variables: tuple[sp.Symbol, ...],
) -> ParameterPolynomial:
    if not parameters:
        coefficient = sp.Poly(
            value, *coefficient_variables, domain=sp.QQ
        )
        return {} if coefficient.is_zero else {(): coefficient}
    polynomial = sp.Poly(
        value, *parameters, domain=sp.EX
    )
    return {
        tuple(int(exponent) for exponent in monomial): sp.Poly(
            coefficient,
            *coefficient_variables,
            domain=sp.QQ,
        )
        for monomial, coefficient in polynomial.terms()
        if coefficient != 0
    }


def _parameter_add(
    *values: ParameterPolynomial,
) -> ParameterPolynomial:
    result: ParameterPolynomial = {}
    for value in values:
        for monomial, coefficient in value.items():
            updated = (
                result[monomial] + coefficient
                if monomial in result
                else coefficient
            )
            if updated.is_zero:
                result.pop(monomial, None)
            else:
                result[monomial] = updated
    return result


def _parameter_scale(
    value: ParameterPolynomial,
    scalar: sp.Expr,
) -> ParameterPolynomial:
    if scalar == 0:
        return {}
    return {
        monomial: coefficient * scalar
        for monomial, coefficient in value.items()
        if not coefficient.is_zero
    }


def _parameter_multiply(
    left: ParameterPolynomial,
    right: ParameterPolynomial,
) -> ParameterPolynomial:
    result: ParameterPolynomial = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            monomial = tuple(
                left_exponent + right_exponent
                for left_exponent, right_exponent in zip(
                    left_monomial, right_monomial, strict=True
                )
            )
            product = left_coefficient * right_coefficient
            updated = (
                result[monomial] + product
                if monomial in result
                else product
            )
            if updated.is_zero:
                result.pop(monomial, None)
            else:
                result[monomial] = updated
    return result


def _parameter_diff(
    value: ParameterPolynomial,
    variable: sp.Symbol,
) -> ParameterPolynomial:
    return {
        monomial: derivative
        for monomial, coefficient in value.items()
        if not (derivative := coefficient.diff(variable)).is_zero
    }


def _parameter_pair_add(
    *values: ParameterPair,
) -> ParameterPair:
    return (
        _parameter_add(*(value[0] for value in values)),
        _parameter_add(*(value[1] for value in values)),
    )


def _parameter_pair_scale(
    value: ParameterPair,
    scalar: sp.Expr,
) -> ParameterPair:
    return (
        _parameter_scale(value[0], scalar),
        _parameter_scale(value[1], scalar),
    )


def _parameter_operator_series_apply(
    fields: dict[int, ParameterPair],
    series: ParameterSeries,
    variables: tuple[sp.Symbol, sp.Symbol],
    maximum_order: int,
) -> ParameterSeries:
    first, second = variables
    result: ParameterSeries = [
        ({}, {}) for _ in range(maximum_order + 1)
    ]
    for order in range(maximum_order + 1):
        terms: list[ParameterPair] = []
        for field_order, field in fields.items():
            if field_order > order:
                continue
            source = series[order - field_order]
            components: list[ParameterPolynomial] = []
            for component in range(2):
                components.append(_parameter_add(
                    _parameter_multiply(
                        field[0],
                        _parameter_diff(source[component], first),
                    ),
                    _parameter_multiply(
                        field[1],
                        _parameter_diff(source[component], second),
                    ),
                ))
            terms.append(_parameter_pair_scale(
                (components[0], components[1]),
                sp.Rational(1, sp.factorial(field_order)),
            ))
        result[order] = (
            _parameter_pair_add(*terms) if terms else ({}, {})
        )
    return result


def _parameter_exp_operator_series(
    fields: dict[int, ParameterPair],
    input_series: ParameterSeries,
    variables: tuple[sp.Symbol, sp.Symbol],
    maximum_order: int,
) -> ParameterSeries:
    result = [
        (dict(pair[0]), dict(pair[1])) for pair in input_series
    ]
    term = [
        (dict(pair[0]), dict(pair[1])) for pair in input_series
    ]
    for power in range(1, maximum_order + 1):
        term = _parameter_operator_series_apply(
            fields, term, variables, maximum_order
        )
        if all(not pair[0] and not pair[1] for pair in term):
            break
        coefficient = sp.Rational(1, sp.factorial(power))
        result = [
            _parameter_pair_add(
                result[order],
                _parameter_pair_scale(term[order], coefficient),
            )
            for order in range(maximum_order + 1)
        ]
    return result


def _composed_parameter_series(
    *,
    target_fields: dict[int, Pair],
    source_fields: dict[int, Pair],
    parameters: tuple[sp.Symbol, ...],
    p: sp.Symbol,
    q: sp.Symbol,
    v: sp.Symbol,
    t: sp.Symbol,
    p0: sp.Expr,
    q0: sp.Expr,
    maximum_order: int,
) -> ParameterSeries:
    target_parameter_fields = {
        order: (
            _parameter_polynomial(
                field[0], parameters, (p, q)
            ),
            _parameter_polynomial(
                field[1], parameters, (p, q)
            ),
        )
        for order, field in target_fields.items()
    }
    target_input: ParameterSeries = [
        ({}, {}) for _ in range(maximum_order + 1)
    ]
    zero_monomial = (0,) * len(parameters)
    target_input[0] = (
        {zero_monomial: sp.Poly(p, p, q, domain=sp.QQ)},
        {zero_monomial: sp.Poly(q, p, q, domain=sp.QQ)},
    )
    target_series = _parameter_exp_operator_series(
        target_parameter_fields,
        target_input,
        (p, q),
        maximum_order,
    )
    p0_polynomial = sp.Poly(p0, v, t, domain=sp.QQ)
    q0_polynomial = sp.Poly(q0, v, t, domain=sp.QQ)
    one = sp.Poly(1, v, t, domain=sp.QQ)
    p0_powers = {0: one, 1: p0_polynomial}
    q0_powers = {0: one, 1: q0_polynomial}

    def cached_power(
        cache: dict[int, sp.Poly],
        base: sp.Poly,
        exponent: int,
    ) -> sp.Poly:
        if exponent not in cache:
            for index in range(max(cache) + 1, exponent + 1):
                cache[index] = cache[index - 1] * base
        return cache[exponent]

    def pull_back(coefficient: sp.Poly) -> sp.Poly:
        result = sp.Poly(0, v, t, domain=sp.QQ)
        for (p_power, q_power), scalar in coefficient.terms():
            result += (
                cached_power(p0_powers, p0_polynomial, p_power)
                * cached_power(q0_powers, q0_polynomial, q_power)
                * scalar
            )
        return result

    pulled_back: ParameterSeries = [
        (
            {
                monomial: pull_back(coefficient)
                for monomial, coefficient in pair[0].items()
            },
            {
                monomial: pull_back(coefficient)
                for monomial, coefficient in pair[1].items()
            },
        )
        for pair in target_series
    ]
    source_parameter_fields = {
        order: (
            _parameter_polynomial(
                field[0], parameters, (v, t)
            ),
            _parameter_polynomial(
                field[1], parameters, (v, t)
            ),
        )
        for order, field in source_fields.items()
    }
    return _parameter_exp_operator_series(
        source_parameter_fields,
        pulled_back,
        (v, t),
        maximum_order,
    )


def _parameter_residual_coefficients(
    *,
    predicted: ParameterPair,
    actual: Pair,
    scale: sp.Expr,
    parameter_count: int,
    coefficient_variables: tuple[sp.Symbol, ...],
) -> tuple[list[ParameterMonomial], list[Pair]]:
    zero_monomial = (0,) * parameter_count
    residual = (
        _parameter_add(
            {
                zero_monomial: sp.Poly(
                    actual[0],
                    *coefficient_variables,
                    domain=sp.QQ,
                )
            },
            _parameter_scale(predicted[0], -scale),
        ),
        _parameter_add(
            {
                zero_monomial: sp.Poly(
                    actual[1],
                    *coefficient_variables,
                    domain=sp.QQ,
                )
            },
            _parameter_scale(predicted[1], -scale),
        ),
    )
    monomials = sorted(set(residual[0]) | set(residual[1]))
    return monomials, [
        (
            (
                residual[0][monomial].as_expr()
                if monomial in residual[0]
                else sp.Integer(0)
            ),
            (
                residual[1][monomial].as_expr()
                if monomial in residual[1]
                else sp.Integer(0)
            ),
        )
        for monomial in monomials
    ]


def _substitute_parameter_coordinates(
    *,
    monomials: list[ParameterMonomial],
    coefficients: list[Pair],
    old_parameters: tuple[sp.Symbol, ...],
    substitution: dict[sp.Symbol, sp.Expr],
    new_parameters: tuple[sp.Symbol, ...],
) -> tuple[list[ParameterMonomial], list[Pair]]:
    result: list[dict[ParameterMonomial, sp.Expr]] = [{}, {}]
    for monomial, coefficient_pair in zip(
        monomials, coefficients, strict=True
    ):
        parameter_value = sp.Integer(1)
        for parameter, exponent in zip(
            old_parameters, monomial, strict=True
        ):
            parameter_value *= parameter**exponent
        parameter_value = sp.expand(
            parameter_value.subs(substitution)
        )
        if new_parameters:
            scalar_polynomial = sp.Poly(
                parameter_value, *new_parameters, domain=sp.QQ
            )
            parameter_polynomial = {
                tuple(int(exponent) for exponent in monomial):
                coefficient
                for monomial, coefficient
                in scalar_polynomial.terms()
            }
        else:
            parameter_polynomial = {
                (): sp.Rational(parameter_value)
            }
        for component in range(2):
            contribution = {
                new_monomial: sp.expand(
                    scalar * coefficient_pair[component]
                )
                for new_monomial, scalar
                in parameter_polynomial.items()
            }
            result[component] = _parameter_add(
                result[component], contribution
            )
    result_monomials = sorted(set(result[0]) | set(result[1]))
    return result_monomials, [
        (
            result[0].get(monomial, sp.Integer(0)),
            result[1].get(monomial, sp.Integer(0)),
        )
        for monomial in result_monomials
    ]


def _parse_pair(
    values: list[str], locals_: dict[str, sp.Symbol]
) -> Pair:
    return tuple(
        sp.sympify(value, locals=locals_) for value in values
    )  # type: ignore[return-value]


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(str(sp.expand(value)).encode("utf-8")).hexdigest()


def _degree(value: sp.Expr, v: sp.Symbol, t: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(value, v, t, domain=sp.QQ).total_degree())


def run(
    *,
    extension_order: int = 5,
    source_degree_bound: int = 6,
    maximum_hamiltonian_degree: int = 6,
) -> dict[str, object]:
    if extension_order != 5:
        raise ValueError("the current carried prefix is certified through four")

    third = run_third(
        maximum_source_degree=5,
        maximum_third_hamiltonian_degree=4,
    )
    fourth = run_fourth(
        source_degree_bound=6,
        maximum_fourth_hamiltonian_degree=4,
    )
    third_witness = third["witness"]
    fourth_witness = fourth["witness"]
    assert third_witness["K2"] == fourth["prefix"]["K2"]
    assert third_witness["K3"] == fourth["prefix"]["K3"]

    data = _family_jets(extension_order)
    v, t = data["symbols"]
    p, q = sp.symbols("P Q")
    p0, q0 = data["P"][0], data["Q"][0]
    target_locals = {"P": p, "Q": q}
    source_locals = {"v": v, "t": t}
    target_hamiltonians = {
        1: -q**2 / 4 - p**3 / 36,
        2: sp.sympify(third_witness["K2"], locals=target_locals),
        3: sp.sympify(third_witness["K3"], locals=target_locals),
        4: sp.sympify(fourth_witness["K4"], locals=target_locals),
    }
    target_fields = {
        order: _hamiltonian_field(hamiltonian, p, q)
        for order, hamiltonian in target_hamiltonians.items()
    }
    source_fields = {
        2: _parse_pair(third_witness["Y2"], source_locals),
        3: _parse_pair(third_witness["Y3"], source_locals),
        4: _parse_pair(fourth_witness["Y4"], source_locals),
    }

    through_four = _composed_series(
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
    for order in range(5):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                through_four[order], actual, strict=True
            )
        )

    predicted = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=extension_order,
    )
    residual = (
        sp.expand(
            data["P"][extension_order]
            - sp.factorial(extension_order)
            * predicted[extension_order][0]
        ),
        sp.expand(
            data["Q"][extension_order]
            - sp.factorial(extension_order)
            * predicted[extension_order][1]
        ),
    )
    jacobian = sp.Matrix([
        [sp.diff(p0, v), sp.diff(p0, t)],
        [sp.diff(q0, v), sp.diff(q0, t)],
    ])

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
                "kind": f"Y{extension_order}",
                "component": component,
                "monomial": [i, j],
            })
    for total in range(1, maximum_hamiltonian_degree + 1):
        for i in range(total + 1):
            hamiltonian = p**i * q ** (total - i)
            columns.append(_substitute(
                _hamiltonian_field(hamiltonian, p, q),
                p,
                q,
                p0,
                q0,
            ))
            metadata.append({
                "kind": f"K{extension_order}",
                "hamiltonian": str(hamiltonian),
                "target_degree": total,
            })

    matrix, rhs, row_keys = _pair_system(columns, residual, v, t)
    cap_checks: dict[str, dict[str, object]] = {}
    first_consistent: tuple[int, list[int], DomainMatrix] | None = None
    for cap in range(1, maximum_hamiltonian_degree + 1):
        indices = [
            index
            for index, item in enumerate(metadata)
            if (
                item["kind"] == f"Y{extension_order}"
                or int(item["target_degree"]) <= cap
            )
        ]
        selected = matrix.extract(list(range(matrix.shape[0])), indices)
        rank = selected.rank()
        augmented_rank = DomainMatrix.hstack(selected, rhs).rank()
        consistent = rank == augmented_rank
        cap_checks[str(cap)] = {
            "column_count": len(indices),
            "rank": rank,
            "augmented_rank": augmented_rank,
            "consistent": consistent,
        }
        if consistent and first_consistent is None:
            first_consistent = cap, indices, selected
    if first_consistent is None:
        return {
            "schema": "axiompack.jacobian_recursive_gauge_prefix.v1",
            "extension_order": extension_order,
            "source_degree_bound": source_degree_bound,
            "extended": False,
            "cap_checks": cap_checks,
            "residual_component_degrees": [
                _degree(item, v, t) for item in residual
            ],
        }

    cap, indices, selected = first_consistent
    solution = _particular_solution(selected, rhs)
    source = [sp.Integer(0), sp.Integer(0)]
    hamiltonian = sp.Integer(0)
    for coefficient, index in zip(solution, indices, strict=True):
        item = metadata[index]
        if item["kind"] == f"Y{extension_order}":
            i, j = item["monomial"]
            source[int(item["component"])] += (
                coefficient * v**int(i) * t**int(j)
            )
        else:
            hamiltonian += coefficient * sp.sympify(
                item["hamiltonian"], locals=target_locals
            )
    source_pair = sp.expand(source[0]), sp.expand(source[1])
    hamiltonian = sp.expand(hamiltonian)
    target_fields[extension_order] = _hamiltonian_field(
        hamiltonian, p, q
    )
    source_fields[extension_order] = source_pair
    completed = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=p0,
        q0=q0,
        maximum_order=extension_order,
    )
    for order in range(extension_order + 1):
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
        "schema": "axiompack.jacobian_recursive_gauge_prefix.v1",
        "series_engine": (
            "ordinary-power truncation of exp(B_s) exp(A_s) with "
            "factorial-scaled logarithmic generators"
        ),
        "independent_replay_through_order_four": True,
        "extension_order": extension_order,
        "source_degree_bound": source_degree_bound,
        "extended": True,
        "first_consistent_hamiltonian_degree": cap,
        "cap_checks": cap_checks,
        "residual_component_degrees": [
            _degree(item, v, t) for item in residual
        ],
        "witness": {
            f"K{extension_order}": str(hamiltonian),
            f"Y{extension_order}": [
                str(item) for item in source_pair
            ],
            f"K{extension_order}_sha256": _sha(hamiltonian),
            f"Y{extension_order}_sha256": [
                _sha(item) for item in source_pair
            ],
            f"Y{extension_order}_degrees": [
                _degree(item, v, t) for item in source_pair
            ],
            "full_prefix_replay": True,
        },
        "coefficient_system": {
            "row_count": matrix.shape[0],
            "selected_column_count": selected.shape[1],
            "selected_matrix_sha256": _matrix_sha(selected),
            "rhs_sha256": _matrix_sha(rhs),
            "row_key_sha256": hashlib.sha256(
                json.dumps(row_keys, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "one explicit compatible prefix through order five; the exact "
            "order-four minimum supplies only the lower bound c5>=6 unless "
            "this extension also has source degree six"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
