#!/usr/bin/env python3
"""Finite-width terminal recurrence for the row-one Q^2*C prefix.

In the leading-amplitude scaling ``x = lambda*s**2``, the projected source
logarithm has a fixed cost-two coefficient, a fixed cost-three coefficient,
and one terminal Hamiltonian at every later odd cost.  Current even target
rows contribute at most three C-multiplier seed columns.  This script solves
that finite linear recurrence without rebuilding the full polynomial family.
"""

from __future__ import annotations

from fractions import Fraction
import json
from math import factorial
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_cone_radial_triangular_staircase import (  # noqa: E402
    _canonical_c_multiplier,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _add,
    _bracket,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    forward_dexp_coefficients,
)


Exponent = tuple[int, int]
Sparse = dict[Exponent, sp.Expr]
TruncatedPolynomial = dict[tuple[int, int], sp.Expr]

TERMINAL_GRADE = (-13, -9)

L_TWO: Sparse = {
    (2, 6): -sp.Rational(1, 16),
    (2, 7): sp.Rational(1, 8),
    (3, 6): -sp.Rational(1, 8),
    (3, 7): sp.Rational(7, 16),
    (4, 6): -sp.Rational(1, 16),
    (4, 7): sp.Rational(5, 8),
    (4, 8): -sp.Rational(25, 64),
    (5, 7): sp.Rational(5, 16),
    (5, 8): -sp.Rational(29, 32),
    (6, 8): -sp.Rational(37, 64),
    (6, 9): sp.Rational(13, 32),
    (7, 9): sp.Rational(15, 32),
    (8, 10): -sp.Rational(9, 64),
}

L_THREE: Sparse = {
    (5, 9): sp.Rational(13, 96),
    (6, 9): -sp.Rational(31, 384),
    (7, 9): -sp.Rational(31, 128),
    (7, 10): -sp.Rational(29, 256),
    (9, 11): sp.Rational(9, 256),
}

P_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Rational(4, 3),
    (2, 1): -sp.Rational(2, 3),
}
Q_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Integer(1),
    (2, 1): -sp.Integer(1),
}
C_NORMALIZED: TruncatedPolynomial = {
    (0, 0): sp.Integer(1),
    (1, 0): -sp.Rational(4, 3),
    (2, 0): sp.Rational(4, 9),
    (2, 1): -sp.Rational(8, 9),
}

CORE_INITIAL_T = sp.Rational(13, 96)
CORE_INITIAL_C = -sp.Rational(29, 256)
CORE_INITIAL_E = sp.Rational(9, 256)


def _periodic_delta(index: int) -> int:
    return (0, 12, 6)[index % 3]


def _seed_cokernel_ratio(index: int) -> sp.Rational:
    """Coefficient of the second core state in the terminal cokernel."""

    return sp.Rational(
        147 * index * index
        + 49 * index
        + _periodic_delta(index),
        6 * (21 * index + 8),
    )


def _orbit_multiplier(depth: int) -> sp.Expr:
    """Coefficient in ``ad_A**depth(u**12*z**16)``."""

    result = sp.Integer(1)
    for previous_depth in range(depth):
        result = sp.factor(
            result
            * sp.Rational(
                9 * (4 - 7 * previous_depth),
                32,
            )
        )
    return result


def _advance_core_states(
    index: int,
    transverse: sp.Expr,
    contact: sp.Expr,
    exterior: sp.Expr,
) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    """Apply ``ad_L_TWO`` to the three states at amplitude ``index``."""

    return (
        sp.factor(
            -sp.Rational(9 * (7 * index - 18), 32)
            * transverse
            + sp.Rational(39 * (7 * index - 6), 32)
            * contact
            - sp.Rational(175 * index, 16) * exterior
        ),
        sp.factor(
            -sp.Rational(9 * (7 * index - 12), 32)
            * contact
            + sp.Rational(39 * (7 * index - 2), 32)
            * exterior
        ),
        sp.factor(
            -sp.Rational(9 * (7 * index - 6), 32)
            * exterior
        ),
    )


def _core_forcing(
    maximum_ray_depth: int,
) -> tuple[list[sp.Expr], list[sp.Expr]]:
    """Return the scalar ODE forcing ``H_n`` and divided forcing ``h_n``.

    At ray depth ``n``, the finite core has amplitude index ``k=n+2``.
    The forward-``dexp`` scalar equation is

    ``e_n = h_n + sum_{j<n} R_(n,j)*e_j``

    and ``H_n=(2*n+5)*h_n``.
    """

    transverse = CORE_INITIAL_T
    contact = CORE_INITIAL_C
    exterior = CORE_INITIAL_E
    transverse, contact, exterior = _advance_core_states(
        1,
        transverse,
        contact,
        exterior,
    )
    ode_forcing = []
    divided_forcing = []
    for depth in range(maximum_ray_depth + 1):
        index = depth + 2
        cokernel_ratio = _seed_cokernel_ratio(index)
        core_quotient = sp.factor(
            sp.Rational((-1) ** (index - 1), factorial(index))
            * (transverse + cokernel_ratio * contact)
        )
        ode_value = sp.factor(
            -core_quotient / _orbit_multiplier(depth)
        )
        ode_forcing.append(ode_value)
        divided_forcing.append(
            sp.factor(ode_value / (2 * depth + 5))
        )
        transverse, contact, exterior = _advance_core_states(
            index,
            transverse,
            contact,
            exterior,
        )
    return ode_forcing, divided_forcing


def _feedback_kernel(depth: int, earlier_depth: int) -> sp.Rational:
    if not 0 <= earlier_depth < depth:
        raise ValueError("feedback indices must satisfy 0 <= j < k")
    return sp.Rational(
        (-1) ** (depth - earlier_depth + 1)
        * (2 * earlier_depth + 3),
        (2 * depth + 5) * factorial(depth - earlier_depth + 1),
    )


def _scalar_response(
    divided_forcing: list[sp.Expr],
) -> list[sp.Expr]:
    response = []
    for depth, forcing in enumerate(divided_forcing):
        response.append(sp.factor(
            forcing
            + sum(
                _feedback_kernel(depth, earlier_depth)
                * response[earlier_depth]
                for earlier_depth in range(depth)
            )
        ))
    return response


def _numerator_coefficients(
    ode_forcing: list[sp.Expr],
) -> list[sp.Expr]:
    """Coefficients of ``J`` in ``E=x*J/(exp(x)-1)``."""

    result = []
    for order in range(len(ode_forcing)):
        exponential_product = sum(
            ode_forcing[forcing_order]
            / factorial(order - forcing_order)
            for forcing_order in range(order + 1)
        )
        result.append(
            sp.factor(exponential_product / (2 * order + 5))
        )
    return result


def _alternating_arctangent_bounds(
    reciprocal: int,
    terms: int,
) -> tuple[Fraction, Fraction]:
    partial = Fraction(0)
    for order in range(terms):
        partial += Fraction(
            (-1) ** order,
            (2 * order + 1)
            * reciprocal ** (2 * order + 1),
        )
    next_term = Fraction(
        (-1) ** terms,
        (2 * terms + 1)
        * reciprocal ** (2 * terms + 1),
    )
    other_endpoint = partial + next_term
    return (
        min(partial, other_endpoint),
        max(partial, other_endpoint),
    )


def _pi_bounds() -> tuple[Fraction, Fraction]:
    """Machin-formula enclosure with an alternating-series remainder."""

    first = _alternating_arctangent_bounds(5, 60)
    second = _alternating_arctangent_bounds(239, 20)
    return (
        16 * first[0] - 4 * second[1],
        16 * first[1] - 4 * second[0],
    )


def _as_fraction(value: sp.Expr) -> Fraction:
    rational = sp.Rational(value)
    return Fraction(int(rational.p), int(rational.q))


def _imaginary_numerator_certificate(
    numerator: list[sp.Expr],
    truncation_order: int = 100,
) -> dict[str, object]:
    """Certify ``Im J(2*pi*i) > 1/200`` by rational intervals.

    The all-order majorant used for the omitted tail is

    ``|H_n| <= 2*(n+2)^4/(n+2)!``.

    It follows from the positive three-state recurrence, the symbolic
    bound ``T_k/E_k <= 10*k^2``, and the explicit Pochhammer products for
    the exterior state and terminal orbit.
    """

    if len(numerator) < truncation_order:
        raise ValueError("the numerator prefix is too short")
    pi_lower, pi_upper = _pi_bounds()
    radius_lower = 2 * pi_lower
    radius_upper = 2 * pi_upper
    partial_lower = Fraction(0)
    partial_upper = Fraction(0)
    for order in range(1, truncation_order, 2):
        coefficient = (
            _as_fraction(numerator[order])
            * (-1) ** ((order - 1) // 2)
        )
        lower_power = radius_lower**order
        upper_power = radius_upper**order
        if coefficient >= 0:
            partial_lower += coefficient * lower_power
            partial_upper += coefficient * upper_power
        else:
            partial_lower += coefficient * upper_power
            partial_upper += coefficient * lower_power

    # Since 2*pi < 7, the coefficient majorant gives
    # M_n = 8*14^n*(n+2)^4 / ((2*n+5)*(n+2)!).
    majorant_at_cut = Fraction(
        8 * 14**truncation_order
        * (truncation_order + 2) ** 4,
        (2 * truncation_order + 5)
        * factorial(truncation_order + 2),
    )
    ratio_bound = Fraction(
        14 * (truncation_order + 3) ** 3,
        (truncation_order + 2) ** 4,
    )
    assert ratio_bound < Fraction(1, 6)
    tail_bound = majorant_at_cut / (1 - ratio_bound)
    assert partial_lower - tail_bound > Fraction(1, 200)
    return {
        "evaluation_point": "2*pi*i",
        "truncation_order": truncation_order,
        "pi_enclosure": (
            "Machin: pi=16*atan(1/5)-4*atan(1/239), "
            "alternating remainders"
        ),
        "forcing_majorant": (
            "|H_n| <= 2*(n+2)^4/(n+2)!"
        ),
        "tail_majorant": (
            "8*14^N*(N+2)^4/((2*N+5)*(N+2)!) "
            "with geometric ratio < 1/6"
        ),
        "certified_imaginary_part_lower_bound": "1/200",
        "numerator_nonzero": True,
        "nonremovable_response_pole": True,
    }


def _symbolic_all_order_checks() -> dict[str, object]:
    """Verify the residue-class formulas that drive the proof."""

    index = sp.symbols("k", integer=True, positive=True)
    next_index = index + 1
    normalized_contact_ratio = (21 * index + 8) / 9
    exterior_update = (
        9 * (7 * index - 6) / (32 * (index + 1))
    )
    contact_update = (
        9 * (7 * index - 12) / (32 * (index + 1))
    )
    exterior_to_contact = (
        39 * (7 * index - 2) / (32 * (index + 1))
    )
    assert sp.factor(
        (
            contact_update * normalized_contact_ratio
            + exterior_to_contact
        )
        / exterior_update
        - (21 * next_index + 8) / 9
    ) == 0

    symbolic_rows = []
    for residue, p_exponent in ((0, 0), (1, 2), (2, 1)):
        q_exponent = (7 * index - 2 * p_exponent) / 3
        contact_coefficient = (
            -sp.Rational(2, 3) * p_exponent
            - q_exponent
            - sp.Rational(8, 9)
        )
        square_sum = (
            sp.Rational(4, 9) * p_exponent
            + q_exponent
            + sp.Rational(64, 81)
        )
        transverse_coefficient = sp.factor(
            (
                contact_coefficient**2
                - square_sum
            )
            / 2
        )
        delta = (0, 12, 6)[residue]
        cokernel_ratio = sp.factor(
            -transverse_coefficient / contact_coefficient
        )
        expected_ratio = (
            147 * index**2 + 49 * index + delta
        ) / (6 * (21 * index + 8))
        assert sp.factor(
            cokernel_ratio - expected_ratio
        ) == 0

        current_ratio = expected_ratio
        next_delta = (0, 12, 6)[(residue + 1) % 3]
        next_ratio = (
            147 * next_index**2
            + 49 * next_index
            + next_delta
        ) / (6 * (21 * next_index + 8))
        transverse_diagonal = (
            9 * (7 * index - 18)
            / (32 * (index + 1))
        )
        contact_to_transverse = (
            39 * (7 * index - 6)
            / (32 * (index + 1))
        )
        exterior_to_transverse = (
            175 * index / (16 * (index + 1))
        )
        gamma = sp.factor(
            transverse_diagonal * current_ratio
            + contact_to_transverse
            + exterior_to_transverse
            / normalized_contact_ratio
            - next_ratio
            * (
                contact_update
                + exterior_to_contact
                / normalized_contact_ratio
            )
        )
        expected_gamma = (
            sp.Integer(0)
            if residue == 0
            else (
                189 * (index - 2)
                / (
                    32 * (index + 1)
                    * (21 * index + 8)
                )
                if residue == 1
                else
                27 * (7 * index - 10)
                / (
                    32 * (index + 1)
                    * (21 * index + 8)
                )
            )
        )
        assert sp.factor(gamma - expected_gamma) == 0
        symbolic_rows.append({
            "residue": residue,
            "canonical_p_exponent": p_exponent,
            "canonical_q_exponent": str(q_exponent),
            "cokernel_ratio": str(sp.factor(expected_ratio)),
            "gamma": str(sp.factor(expected_gamma)),
        })

    shifted_index = sp.symbols(
        "m",
        integer=True,
        nonnegative=True,
    )
    induction_margin_numerator = sp.expand(
        (
            5109 * index**2
            - 1490 * index
            - 996
        ).subs(index, shifted_index + 3)
    )
    assert sp.Poly(
        induction_margin_numerator,
        shifted_index,
    ).all_coeffs() == [5109, 29164, 40515]
    return {
        "seed_cokernel_residue_rows": symbolic_rows,
        "rotated_contact_identity": (
            "C_k/E_k=(21*k+8)/9"
        ),
        "positive_core_recurrence": (
            "D_(k+1)=a_k*D_k+gamma_k*C_k; "
            "D_3=81/16384"
        ),
        "core_growth_induction": (
            "0<D_k<=T_k<=10*k^2*E_k for k>=3"
        ),
        "feedback_kernel": (
            "R_(k,j)=(-1)^(k-j+1)*(2*j+3)"
            "/((2*k+5)*(k-j+1)!)"
        ),
        "response_ode": (
            "2*x*f(x)*E'(x)+(2+3*f(x))*E(x)=H(x), "
            "f(x)=(1-exp(-x))/x"
        ),
        "response_solution": (
            "E(x)=x*J(x)/(exp(x)-1), "
            "J(x)=integral_0^x exp(t)*t^(3/2)*H(t)dt"
            "/(2*x^(5/2))"
        ),
    }


def _grade(exponent: Exponent, cost: int) -> tuple[int, int]:
    return (
        2 * exponent[0] - 7 * cost - 2,
        2 * exponent[1] - 7 * cost - 6,
    )


def _project(value: Sparse, cost: int) -> Sparse:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in value.items()
        if all(
            component >= terminal
            for component, terminal in zip(
                _grade(exponent, cost),
                TERMINAL_GRADE,
                strict=True,
            )
        )
        and coefficient != 0
    }


def _scale(value: Sparse, scalar: sp.Expr) -> Sparse:
    return {
        exponent: sp.factor(scalar * coefficient)
        for exponent, coefficient in value.items()
        if coefficient != 0
    }


def _series_bracket(
    left: list[Sparse],
    right: list[Sparse],
    maximum_order: int,
) -> list[Sparse]:
    result = [{} for _ in range(maximum_order + 1)]
    for left_order, left_value in enumerate(
        left[: maximum_order + 1]
    ):
        for right_order, right_value in enumerate(
            right[: maximum_order + 1 - left_order]
        ):
            order = left_order + right_order
            result[order] = _project(
                _add(
                    result[order],
                    _bracket(left_value, right_value, 2),
                ),
                order + 1,
            )
    return result


def _known_forward_velocity(
    logarithm: list[Sparse],
    cost: int,
) -> Sparse:
    """Velocity at ``cost`` with the still-unknown log row set to zero."""

    maximum_velocity_order = cost - 1
    derivative = [
        _scale(logarithm[order + 1], order + 1)
        for order in range(maximum_velocity_order)
    ]
    derivative.append({})
    result = dict(derivative[maximum_velocity_order])
    nested = derivative
    forward = forward_dexp_coefficients(
        maximum_velocity_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    for depth in range(1, maximum_velocity_order + 1):
        nested = _series_bracket(
            logarithm,
            nested,
            maximum_velocity_order,
        )
        coefficient = forward[depth]
        if coefficient:
            scalar = sp.Rational(
                coefficient.numerator,
                coefficient.denominator,
            )
            result = _project(
                _add(
                    result,
                    _scale(
                        nested[maximum_velocity_order],
                        scalar,
                    ),
                ),
                cost,
            )
    return result


def _truncated_product(
    left: TruncatedPolynomial,
    right: TruncatedPolynomial,
    maximum_t_degree: int,
) -> TruncatedPolynomial:
    result: TruncatedPolynomial = {}
    for (left_t, left_z), left_coefficient in left.items():
        for (right_t, right_z), right_coefficient in right.items():
            t_degree = left_t + right_t
            if t_degree > maximum_t_degree:
                continue
            exponent = (t_degree, left_z + right_z)
            result[exponent] = sp.factor(
                result.get(exponent, 0)
                + left_coefficient * right_coefficient
            )
    return {
        exponent: coefficient
        for exponent, coefficient in result.items()
        if coefficient != 0
    }


def _truncated_power(
    value: TruncatedPolynomial,
    exponent: int,
    maximum_t_degree: int,
) -> TruncatedPolynomial:
    result: TruncatedPolynomial = {(0, 0): sp.Integer(1)}
    factor = value
    remaining = exponent
    while remaining:
        if remaining % 2:
            result = _truncated_product(
                result, factor, maximum_t_degree
            )
        remaining //= 2
        if remaining:
            factor = _truncated_product(
                factor, factor, maximum_t_degree
            )
    return result


def _c_seed_column(
    cost: int,
    multiplier_weight: int,
) -> tuple[tuple[int, int], Sparse] | None:
    multiplier = _canonical_c_multiplier(
        multiplier_weight + 2
    )
    if multiplier is None:
        return None
    p_exponent, q_exponent = multiplier
    weight_offset = multiplier_weight - 7 * ((cost - 1) // 2)
    maximum_t_degree = 4 + weight_offset
    normalized = _truncated_product(
        _truncated_power(
            P_NORMALIZED,
            p_exponent,
            maximum_t_degree,
        ),
        _truncated_power(
            Q_NORMALIZED,
            q_exponent,
            maximum_t_degree,
        ),
        maximum_t_degree,
    )
    normalized = _truncated_product(
        normalized,
        C_NORMALIZED,
        maximum_t_degree,
    )
    leading = sp.factor(
        8
        * (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
        * (-sp.Rational(9, 16))
    )
    value: Sparse = {}
    for (
        t_degree,
        extra_normal_order,
    ), coefficient in normalized.items():
        radial_degree = multiplier_weight + 2 - t_degree
        normal_order = 2 + extra_normal_order
        exponent = (
            radial_degree,
            radial_degree + normal_order,
        )
        value[exponent] = sp.factor(
            value.get(exponent, 0)
            + leading * coefficient
        )
    return multiplier, _project(value, cost)


def _solve_row(
    known_velocity: Sparse,
    cost: int,
    allow_symbolic_solution: bool = False,
) -> tuple[sp.Expr, list[dict[str, object]]]:
    amplitude_degree = (cost - 1) // 2
    terminal_exponent = (
        7 * amplitude_degree - 2,
        7 * amplitude_degree + 2,
    )
    terminal = {terminal_exponent: sp.Integer(1)}
    columns = []
    for offset in (-2, -1, 0):
        multiplier_weight = 7 * amplitude_degree + offset
        column = _c_seed_column(cost, multiplier_weight)
        if column is not None:
            columns.append((
                multiplier_weight,
                column[0],
                column[1],
            ))

    control_symbols = sp.symbols(f"c0:{len(columns)}")
    terminal_symbol = sp.symbols("d")
    exponents = sorted(
        set(known_velocity)
        | {terminal_exponent}
        | {
            exponent
            for _weight, _multiplier, column in columns
            for exponent in column
        }
    )
    equations = []
    for exponent in exponents:
        equations.append(
            known_velocity.get(exponent, 0)
            + cost
            * terminal_symbol
            * terminal.get(exponent, 0)
            - sum(
                symbol * column.get(exponent, 0)
                for symbol, (
                    _weight,
                    _multiplier,
                    column,
                ) in zip(
                    control_symbols,
                    columns,
                    strict=True,
                )
            )
        )
    solution_set = sp.linsolve(
        equations,
        (*control_symbols, terminal_symbol),
    )
    if solution_set is sp.EmptySet or len(solution_set) != 1:
        raise AssertionError(
            f"terminal row {cost} does not have a unique solve"
        )
    solution = tuple(next(iter(solution_set)))
    if (
        not allow_symbolic_solution
        and any(value.free_symbols for value in solution)
    ):
        raise AssertionError(
            f"terminal row {cost} solve has residual freedom"
        )
    control_values = solution[:-1]
    terminal_value = sp.factor(solution[-1])
    controls = [
        {
            "multiplier_weight": weight,
            "multiplier_p_exponent": multiplier[0],
            "multiplier_q_exponent": multiplier[1],
            "coefficient": str(sp.factor(coefficient)),
        }
        for (
            weight,
            multiplier,
            _column,
        ), coefficient in zip(
            columns,
            control_values,
            strict=True,
        )
    ]
    return terminal_value, controls


def _valuation(value: sp.Expr, prime: int) -> int:
    rational = sp.Rational(value)

    def integer_valuation(integer: int) -> int:
        remaining = abs(integer)
        result = 0
        while remaining and remaining % prime == 0:
            remaining //= prime
            result += 1
        return result

    return (
        integer_valuation(int(rational.p))
        - integer_valuation(int(rational.q))
    )


def run(maximum_ray_depth: int = 40) -> dict[str, object]:
    if maximum_ray_depth < 3:
        raise ValueError("at least four terminal rows are required")
    maximum_cost = 5 + 2 * maximum_ray_depth
    logarithm = [{} for _ in range(maximum_cost + 1)]
    logarithm[2] = L_TWO
    logarithm[3] = L_THREE
    rows = []
    for depth in range(maximum_ray_depth + 1):
        cost = 5 + 2 * depth
        known_velocity = _known_forward_velocity(
            logarithm,
            cost,
        )
        terminal_value, controls = _solve_row(
            known_velocity,
            cost,
        )
        exponent = (12 + 7 * depth, 16 + 7 * depth)
        logarithm[cost] = {exponent: terminal_value}
        rows.append({
            "depth": depth,
            "cost": cost,
            "exponent": list(exponent),
            "coefficient": str(terminal_value),
            "coefficient_nonzero": terminal_value != 0,
            "valuation_at_2": _valuation(terminal_value, 2),
            "valuation_at_3": _valuation(terminal_value, 3),
            "current_c_controls": controls,
        })

    expected_prefix = [
        sp.Rational(189, 81920),
        -sp.Rational(1377, 9175040),
        sp.Rational(24057, 587202560),
        -sp.Rational(111537, 1291845632),
        -sp.Rational(1644101307, 24567212933120),
        sp.Rational(43844413941, 171970490531840),
        -sp.Rational(
            6314193478629, 19439365579079680
        ),
        -sp.Rational(
            79703784304860483,
            490039490203950776320,
        ),
        sp.Rational(
            28509067563827533659,
            18532402538622138449920,
        ),
    ]
    assert [
        sp.Rational(row["coefficient"])
        for row in rows[: len(expected_prefix)]
    ] == expected_prefix

    certificate_depth = max(maximum_ray_depth, 99)
    ode_forcing, divided_forcing = _core_forcing(
        certificate_depth
    )
    scalar_response = _scalar_response(divided_forcing)
    normalized_full_response = []
    for depth, row in enumerate(rows):
        normalized_full_response.append(sp.factor(
            sp.Rational(row["coefficient"])
            / _orbit_multiplier(depth)
        ))
    assert (
        normalized_full_response
        == scalar_response[: maximum_ray_depth + 1]
    )
    numerator = _numerator_coefficients(ode_forcing)
    pole_certificate = _imaginary_numerator_certificate(
        numerator
    )
    symbolic_certificate = _symbolic_all_order_checks()

    first_zero_depth = next(
        (
            row["depth"]
            for row in rows
            if not row["coefficient_nonzero"]
        ),
        None,
    )
    return {
        "schema": (
            "axiompack.jacobian_cone_q2c_"
            "terminal_recurrence.v2"
        ),
        "grading": "(2*a-7*cost-2,2*b-7*cost-6)",
        "terminal_grade": list(TERMINAL_GRADE),
        "fixed_logarithmic_costs": [2, 3],
        "maximum_ray_depth": maximum_ray_depth,
        "maximum_cost": maximum_cost,
        "first_zero_depth": first_zero_depth,
        "all_checked_coefficients_nonzero": first_zero_depth is None,
        "scalar_response_matches_full_replay": True,
        "all_order_terminal_ray_certificate": {
            **symbolic_certificate,
            **pole_certificate,
            "conclusion": (
                "J(2*pi*i) is nonzero, so E has a "
                "nonremovable pole and cannot be a polynomial. "
                "Infinitely many terminal coefficients are nonzero."
            ),
        },
        "rows": rows,
        "claim_boundary": (
            "All-order nontermination of the leading-amplitude "
            "terminal ray for the row-one Q^2*C prefix. This does "
            "not quantify over arbitrary finite C-adic prefixes."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
