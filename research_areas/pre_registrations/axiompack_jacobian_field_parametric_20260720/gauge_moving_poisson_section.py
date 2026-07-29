#!/usr/bin/env python3
"""Exact graded Poisson-section defect at the seed cusp."""
from __future__ import annotations

import json

import sympy as sp


def _minimum_exponents(weight: int) -> tuple[int, int]:
    candidates = [
        (a, b)
        for a in range(weight // 2 + 1)
        for b in range(weight // 3 + 1)
        if 2 * a + 3 * b == weight
    ]
    if not candidates:
        raise ValueError(f"weight {weight} is outside <2,3>")
    return min(candidates, key=lambda pair: (sum(pair), pair[0]))


def _parity_exponents(weight: int) -> tuple[int, int]:
    if weight % 2 == 0:
        return weight // 2, 0
    return (weight - 3) // 2, 1


def _section(
    weight: int,
    exponents,
    x: sp.Symbol,
    y: sp.Symbol,
) -> sp.Expr:
    a, b = exponents(weight)
    return x**a * y**b


def _bracket(
    left: sp.Expr,
    right: sp.Expr,
    x: sp.Symbol,
    y: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        (
            sp.diff(left, x) * sp.diff(right, y)
            - sp.diff(left, y) * sp.diff(right, x)
        )
        / 6
    )


def _target_lift(
    value_xy: sp.Expr,
    x: sp.Symbol,
    y: sp.Symbol,
    p: sp.Symbol,
    q: sp.Symbol,
) -> bool:
    value = sp.expand(value_xy.subs({x: -p / 3, y: -q / 2}))
    first = sp.diff(value, q)
    second = -sp.diff(value, p)
    first_ok = first.subs({p: 0, q: 0}) == 0
    second_q_zero = sp.Poly(second.subs(q, 0), p)
    second_ok = (
        second_q_zero.coeff_monomial(1) == 0
        and second_q_zero.coeff_monomial(p) == 0
    )
    return bool(first_ok and second_ok)


def _degree(value: sp.Expr, *variables: sp.Symbol) -> int:
    if value == 0:
        return -1
    return int(sp.Poly(sp.expand(value), *variables).total_degree())


def _closed_exponent_assignments(maximum_weight: int) -> list[dict[int, tuple[int, int]]]:
    options = {
        weight: [
            (a, b)
            for a in range(weight // 2 + 1)
            for b in range(weight // 3 + 1)
            if 2 * a + 3 * b == weight
        ]
        for weight in range(5, maximum_weight + 1)
    }
    order = sorted(options, key=lambda weight: (len(options[weight]), weight))
    assignment: dict[int, tuple[int, int]] = {}
    solutions: list[dict[int, tuple[int, int]]] = []

    def compatible(weight: int, value: tuple[int, int]) -> bool:
        candidate = assignment | {weight: value}
        for left_weight, (a, b) in candidate.items():
            for right_weight, (c, d) in candidate.items():
                output_weight = left_weight + right_weight - 5
                if output_weight not in candidate:
                    continue
                if a * d - b * c == 0:
                    continue
                if candidate[output_weight] != (a + c - 1, b + d - 1):
                    return False
        return True

    def search(index: int) -> None:
        if index == len(order):
            solutions.append(dict(assignment))
            return
        weight = order[index]
        for value in options[weight]:
            if compatible(weight, value):
                assignment[weight] = value
                search(index + 1)
                del assignment[weight]

    search(0)
    return solutions


def run(maximum_weight: int = 24) -> dict[str, object]:
    x, y, p, q = sp.symbols("X Y P Q")
    d = x**3 - y**2
    c = 4 * p**3 + 27 * q**2
    assert sp.expand(
        d.subs({x: -p / 3, y: -q / 2}) + c / 108
    ) == 0

    defect_rows: list[dict[str, object]] = []
    for left_weight in range(5, maximum_weight + 1):
        left = _section(left_weight, _minimum_exponents, x, y)
        assert _target_lift(left, x, y, p, q)
        for right_weight in range(5, maximum_weight + 1):
            output_weight = left_weight + right_weight - 5
            if output_weight > maximum_weight:
                continue
            right = _section(right_weight, _minimum_exponents, x, y)
            output = _section(output_weight, _minimum_exponents, x, y)
            a, b = _minimum_exponents(left_weight)
            c_exp, d_exp = _minimum_exponents(right_weight)
            structure = sp.Rational(a * d_exp - b * c_exp, 6)
            defect = sp.factor(
                _bracket(left, right, x, y) - structure * output
            )
            expected_nonzero = (
                left_weight % 3 == 1
                and right_weight % 3 == 1
                and left_weight != right_weight
            )
            assert (defect != 0) == expected_nonzero
            if expected_nonzero:
                left_q = (left_weight - 1) // 3
                right_q = (right_weight - 1) // 3
                expected = sp.factor(
                    sp.Rational(right_q - left_q, 3)
                    * d
                    * y ** (left_q + right_q - 3)
                )
                assert sp.factor(defect - expected) == 0
                defect_pq = sp.factor(
                    defect.subs({x: -p / 3, y: -q / 2})
                )
                quotient, remainder = sp.div(
                    defect_pq, c, p, q
                )
                assert remainder == 0
                defect_rows.append({
                    "left_weight": left_weight,
                    "right_weight": right_weight,
                    "output_weight": output_weight,
                    "structure_constant": str(structure),
                    "defect_XY": str(defect),
                    "defect_over_C": str(sp.factor(quotient)),
                })

    correction_rows: list[dict[str, object]] = []
    for weight in range(5, maximum_weight + 1):
        minimum = _section(weight, _minimum_exponents, x, y)
        parity = _section(weight, _parity_exponents, x, y)
        a, b = _minimum_exponents(weight)
        epsilon = b % 2
        k = b // 2
        geometric = sum(
            x ** (3 * (k - 1 - index)) * y ** (2 * index)
            for index in range(k)
        )
        expected_correction = sp.expand(
            d * x**a * y**epsilon * geometric
        )
        assert sp.expand(parity - minimum - expected_correction) == 0
        assert _target_lift(parity, x, y, p, q)
        assert _degree(minimum, x, y) == (weight + 2) // 3
        assert _degree(parity, x, y) == weight // 2
        correction_rows.append({
            "weight": weight,
            "minimum_exponents": [a, b],
            "minimum_degree": _degree(minimum, x, y),
            "parity_exponents": list(_parity_exponents(weight)),
            "closed_degree": _degree(parity, x, y),
            "C_adic_depth": k,
        })

    for left_weight in range(5, maximum_weight + 1):
        left = _section(left_weight, _parity_exponents, x, y)
        a, b = _parity_exponents(left_weight)
        for right_weight in range(5, maximum_weight + 1):
            output_weight = left_weight + right_weight - 5
            if output_weight > maximum_weight:
                continue
            right = _section(right_weight, _parity_exponents, x, y)
            c_exp, d_exp = _parity_exponents(right_weight)
            structure = sp.Rational(a * d_exp - b * c_exp, 6)
            output = _section(output_weight, _parity_exponents, x, y)
            assert sp.expand(
                _bracket(left, right, x, y) - structure * output
            ) == 0

    # Exact contradiction in the alternative weight-six branch.
    cycle = {
        6: y**2,
        7: x**2 * y,
        8: x * y**2,
        9: y**3,
        10: x**2 * y**2,
    }
    forced_from_7_10 = _bracket(cycle[7], cycle[10], x, y)
    forced_from_8_9 = _bracket(cycle[8], cycle[9], x, y)
    assert forced_from_7_10 != 0
    assert forced_from_8_9 != 0
    assert sp.Poly(forced_from_7_10, x, y).monoms() == [(3, 2)]
    assert sp.Poly(forced_from_8_9, x, y).monoms() == [(0, 4)]

    solutions = _closed_exponent_assignments(maximum_weight)
    assert len(solutions) == 1
    unique = solutions[0]
    assert all(
        unique[weight] == _parity_exponents(weight)
        for weight in unique
    )

    return {
        "schema": "axiompack.jacobian_moving_poisson_section.v1",
        "maximum_checked_weight": maximum_weight,
        "normalization": {
            "X": "-P/3",
            "Y": "-Q/2",
            "D": "X^3-Y^2=-C/108",
            "poisson_scale": "1/6",
        },
        "minimum_section": {
            "degree": "ceil(m/3)",
            "nonzero_defect_pair": "(m mod 3,n mod 3)=(1,1), m!=n",
            "defect_formula": (
                "(q-p)/3 * (X^3-Y^2) * Y^(p+q-3)"
            ),
            "nonzero_rows": defect_rows,
        },
        "closed_section": {
            "formula": (
                "X^(m/2) if m even; "
                "X^((m-3)/2)*Y if m odd"
            ),
            "degree": "floor(m/2)",
            "corrections": correction_rows,
            "poisson_closed": True,
        },
        "weight_six_countercycle": {
            "branch": "u6=Y^2",
            "forced_u12_from_7_10": str(forced_from_7_10),
            "forced_u12_from_8_9": str(forced_from_8_9),
            "contradiction": "X^3*Y^2 and Y^4 are independent",
        },
        "uniqueness_control": {
            "graded_rank_one_solutions": len(solutions),
            "unique_section": "parity/C-normal",
        },
        "verdict": (
            "the minimum 1/3-degree section has a stabilizer defect; "
            "the unique graded rank-one Poisson split exists and pays "
            "degree rate 1/2"
        ),
        "claim_boundary": (
            "this does not classify higher-rank or nonhomogeneous filtered "
            "sections, moving transverse contacts, or the symmetric BCH "
            "minimax"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
