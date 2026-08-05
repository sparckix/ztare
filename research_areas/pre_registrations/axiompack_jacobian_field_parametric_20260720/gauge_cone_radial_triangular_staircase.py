#!/usr/bin/env python3
"""Exact finite rows of the radial triangular cone normalization."""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _add,
    _ops,
    _source_velocity,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    inverse_dexp_coefficients,
    magnus_from_velocity,
    velocity_from_magnus,
)


def _canonical_cone_monomial(
    weight: int,
) -> tuple[int, int] | None:
    candidates = []
    for q_exponent in range(1, weight // 3 + 1):
        remainder = weight - 3 * q_exponent
        if remainder < 0 or remainder % 2:
            continue
        p_exponent = remainder // 2
        if (p_exponent, q_exponent) == (0, 1):
            continue
        if p_exponent <= 2 * q_exponent:
            candidates.append((p_exponent, q_exponent))
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda pair: (sum(pair), pair[1], pair[0]),
    )


def _seed_diagonal(p_exponent: int, q_exponent: int) -> sp.Expr:
    return sp.factor(
        8
        * (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
    )


def _canonical_c_multiplier(
    normal_radial_degree: int,
) -> tuple[int, int] | None:
    multiplier_weight = normal_radial_degree - 2
    candidates = []
    for q_exponent in range(0, multiplier_weight // 3 + 1):
        remainder = multiplier_weight - 3 * q_exponent
        if remainder < 0 or remainder % 2:
            continue
        p_exponent = remainder // 2
        if p_exponent + 3 <= 2 * q_exponent:
            candidates.append((p_exponent, q_exponent))
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda pair: (sum(pair), pair[1], pair[0]),
    )


def _seed_c_diagonal(
    p_exponent: int,
    q_exponent: int,
) -> sp.Expr:
    return sp.factor(
        -sp.Rational(9, 2)
        * (-sp.Rational(3, 4)) ** p_exponent
        * (-sp.Rational(1, 4)) ** q_exponent
    )


def _series_coefficient(
    expression: sp.Expr,
    parameter: sp.Symbol,
    order: int,
) -> sp.Expr:
    return sp.series(
        expression,
        parameter,
        0,
        order + 1,
    ).removeO().expand().coeff(parameter, order)


def _projected_source_magnus(
    velocity: list[dict[tuple[int, int], sp.Expr]],
    maximum_order: int,
    project: Callable[
        [dict[tuple[int, int], sp.Expr], int],
        dict[tuple[int, int], sp.Expr],
    ],
) -> list[dict[tuple[int, int], sp.Expr]]:
    """Right-Magnus recursion with a cost-aware additive projection."""

    inverse = inverse_dexp_coefficients(
        maximum_order,
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    logarithm = [{} for _ in range(maximum_order + 1)]
    source_ops = _ops(2)

    def series_bracket(
        left: list[dict[tuple[int, int], sp.Expr]],
        right: list[dict[tuple[int, int], sp.Expr]],
        maximum_series_order: int,
    ) -> list[dict[tuple[int, int], sp.Expr]]:
        result = [{} for _ in range(maximum_series_order + 1)]
        for left_order, left_value in enumerate(
            left[: maximum_series_order + 1]
        ):
            for right_order, right_value in enumerate(
                right[: maximum_series_order + 1 - left_order]
            ):
                order = left_order + right_order
                result[order] = project(
                    _add(
                        result[order],
                        source_ops.bracket(left_value, right_value),
                    ),
                    order + 1,
                )
        return result

    for derivative_order in range(maximum_order):
        result = velocity[derivative_order]
        nested = velocity[: derivative_order + 1]
        prefix = logarithm[: derivative_order + 1]
        for depth in range(1, derivative_order + 1):
            nested = series_bracket(
                prefix,
                nested,
                derivative_order,
            )
            if inverse[depth]:
                scalar = sp.Rational(
                    inverse[depth].numerator,
                    inverse[depth].denominator,
                )
                result = _add(
                    result,
                    {
                        exponent: sp.factor(scalar * coefficient)
                        for exponent, coefficient
                        in nested[derivative_order].items()
                    },
                )
                result = project(result, derivative_order + 1)
        logarithm[derivative_order + 1] = {
            exponent: sp.factor(
                coefficient / (derivative_order + 1)
            )
            for exponent, coefficient in result.items()
        }
    return logarithm


def run(
    maximum_target_order: int = 5,
    cancel_second_normal: bool = False,
    verify_roundtrips: bool = True,
    compute_logarithms: bool | None = None,
    normalization_objective: str = "velocity",
    delayed_c_prefix_coefficient: sp.Expr | None = None,
    delayed_c_prefix_multiplier: tuple[int, int] = (0, 2),
    delayed_c_prefix_terms: list[
        tuple[int, int, sp.Expr]
    ] | None = None,
    prescribed_target_terms: list[
        tuple[int, int, int, sp.Expr]
    ] | None = None,
    project_to_prefix_ray: bool = False,
    prefix_terminal_grade_override: tuple[int, int] | None = None,
    prefix_slope_override: int | None = None,
    prefix_weight_override: int | None = None,
    prefix_source_slopes_override: tuple[int, int] | None = None,
) -> dict[str, object]:
    if maximum_target_order < 3:
        raise ValueError("at least three triangular rows are required")
    if normalization_objective not in {"velocity", "logarithm"}:
        raise ValueError(
            "normalization_objective must be velocity or logarithm"
        )
    if (
        delayed_c_prefix_terms is not None
        and delayed_c_prefix_coefficient not in {None, 0}
    ):
        raise ValueError(
            "use either one delayed C-prefix coefficient or a term list"
        )
    if delayed_c_prefix_terms is None:
        configured_delayed_prefix = (
            []
            if delayed_c_prefix_coefficient in {None, 0}
            else [(
                delayed_c_prefix_multiplier[0],
                delayed_c_prefix_multiplier[1],
                sp.factor(delayed_c_prefix_coefficient),
            )]
        )
    else:
        configured_delayed_prefix = [
            (p_exponent, q_exponent, sp.factor(coefficient))
            for p_exponent, q_exponent, coefficient
            in delayed_c_prefix_terms
            if coefficient != 0
        ]
    for delayed_prefix_p, delayed_prefix_q, _coefficient in (
        configured_delayed_prefix
    ):
        if min(delayed_prefix_p, delayed_prefix_q) < 0:
            raise ValueError(
                "delayed C-prefix exponents must be nonnegative"
            )
        if delayed_prefix_p + 3 > 2 * delayed_prefix_q:
            raise ValueError(
                "delayed C-prefix multiplier does not put C in the cone"
            )
    configured_prescribed_coefficients: dict[
        tuple[int, int, int], sp.Expr
    ] = {}
    for (
        target_order,
        p_exponent,
        q_exponent,
        coefficient,
    ) in prescribed_target_terms or []:
        key = (target_order, p_exponent, q_exponent)
        combined_coefficient = sp.cancel(
            configured_prescribed_coefficients.get(
                key, sp.Integer(0)
            )
            + coefficient
        )
        if combined_coefficient == 0:
            configured_prescribed_coefficients.pop(key, None)
        else:
            configured_prescribed_coefficients[key] = (
                combined_coefficient
            )
    configured_prescribed_terms = [
        (*key, coefficient)
        for key, coefficient in sorted(
            configured_prescribed_coefficients.items()
        )
    ]
    for (
        target_order,
        p_exponent,
        q_exponent,
        _coefficient,
    ) in configured_prescribed_terms:
        if not 1 <= target_order <= maximum_target_order:
            raise ValueError(
                "prescribed target order is outside the replay"
            )
        if min(p_exponent, q_exponent) < 0:
            raise ValueError(
                "prescribed target exponents must be nonnegative"
            )
        if (
            p_exponent > 2 * q_exponent
            or (p_exponent, q_exponent) == (0, 1)
        ):
            raise ValueError(
                "prescribed target monomial is outside the cone"
            )
        if p_exponent + 2 * q_exponent < 3:
            raise ValueError(
                "prescribed target monomial has no polynomial source lift"
            )
    projection_weights = {
        2 * p_exponent + 3 * q_exponent
        for p_exponent, q_exponent, _coefficient
        in configured_delayed_prefix
    }
    if (
        project_to_prefix_ray
        and (
            not configured_delayed_prefix
            or (
                len(projection_weights) != 1
                and prefix_weight_override is None
            )
        )
    ):
        raise ValueError(
            "prefix-ray projection requires a nonempty "
            "equal-weight prefix or an explicit effective weight"
        )
    if (
        prefix_terminal_grade_override is not None
        and not project_to_prefix_ray
    ):
        raise ValueError(
            "a prefix terminal-grade override requires projection"
        )
    if prefix_slope_override is not None:
        if not project_to_prefix_ray:
            raise ValueError(
                "a prefix slope override requires projection"
            )
        if prefix_slope_override <= 0:
            raise ValueError(
                "a prefix slope override must be positive"
            )
    if prefix_weight_override is not None:
        if not project_to_prefix_ray:
            raise ValueError(
                "a prefix weight override requires projection"
            )
        if prefix_weight_override <= 0:
            raise ValueError(
                "a prefix weight override must be positive"
            )
    if prefix_source_slopes_override is not None:
        if not project_to_prefix_ray:
            raise ValueError(
                "source slope overrides require projection"
            )
        if min(prefix_source_slopes_override) <= 0:
            raise ValueError(
                "source slope overrides must be positive"
            )
    if compute_logarithms is None:
        compute_logarithms = verify_roundtrips
    if verify_roundtrips and not compute_logarithms:
        raise ValueError(
            "round-trip verification requires logarithm computation"
        )
    if project_to_prefix_ray and verify_roundtrips:
        raise ValueError(
            "prefix-ray projection is a quotient replay, not a full "
            "round-trip computation"
        )
    maximum_cost = maximum_target_order + 1
    data = source_only_connection()
    base_velocity, (_s, v, z), _p3, _pq = _source_velocity(
        maximum_cost,
        data,
    )
    s, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u = sp.symbols("u")
    projection_weight = (
        prefix_weight_override
        if prefix_weight_override is not None
        else (
            next(iter(projection_weights))
            if project_to_prefix_ray
            else None
        )
    )
    projection_source_slopes = (
        prefix_source_slopes_override
        if prefix_source_slopes_override is not None
        else None
    )
    projection_slope = (
        prefix_slope_override
        if prefix_slope_override is not None
        else (
            projection_weight + 1
            if projection_weight is not None
            else None
        )
    )
    projection_terminal_grade = (
        prefix_terminal_grade_override
        if prefix_terminal_grade_override is not None
        else (
            (
                -projection_weight - 7,
                -projection_weight - 3,
            )
            if projection_weight is not None
            else None
        )
    )

    def prefix_grade(
        exponent: tuple[int, int],
        cost: int,
    ) -> tuple[int, int]:
        if projection_weight is None:
            raise AssertionError("prefix-ray projection is disabled")
        assert projection_slope is not None
        source_slopes = (
            projection_source_slopes
            if projection_source_slopes is not None
            else (projection_slope, projection_slope)
        )
        return (
            2 * exponent[0]
            - source_slopes[0] * cost
            - 2,
            2 * exponent[1]
            - source_slopes[1] * cost
            - 6,
        )

    def project_sparse(
        value: dict[tuple[int, int], sp.Expr],
        cost: int,
    ) -> dict[tuple[int, int], sp.Expr]:
        if projection_terminal_grade is None:
            return value
        return {
            exponent: coefficient
            for exponent, coefficient in value.items()
            if all(
                grade_component >= terminal_component
                for grade_component, terminal_component in zip(
                    prefix_grade(exponent, cost),
                    projection_terminal_grade,
                    strict=True,
                )
            )
        }

    def project_expression(
        value: sp.Expr,
        cost: int,
    ) -> sp.Expr:
        if projection_terminal_grade is None:
            return sp.expand(value)
        return sp.expand(sum(
            (
                coefficient * u**exponent[0] * z**exponent[1]
                for exponent, coefficient in project_sparse(
                    _to_sparse(value, u, z),
                    cost,
                ).items()
            ),
            sp.Integer(0),
        ))

    fixed_substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.factor(family_p.subs(fixed_substitution))
    q = sp.factor(family_q.subs(fixed_substitution))
    p0 = sp.factor(p.subs(s, 0))
    q0 = sp.factor(q.subs(s, 0))
    assert sp.Poly(p0, u, z).terms()[0] == (
        (2, 2), -sp.Rational(3, 4)
    )
    assert sp.Poly(q0, u, z).terms()[0] == (
        (3, 3), -sp.Rational(1, 4)
    )
    # The finite coefficient replay uses the fixed chart u = v + 1.
    # The all-order normal-layer identity instead belongs to the moving
    # affine chart U_s = 1 + mu_s*v.  These charts agree at s = 0, and
    # their transition is affine in space, so it preserves spatial degree
    # coefficientwise while contributing only a degree-one frame velocity.
    moving_u, r = sp.symbols("U r")
    mu = sp.factor(3 * (s - 4) / (2 * (s - 6)))
    moving_v = sp.factor((moving_u - 1) / mu)
    moving_substitution = {
        family_v: moving_v,
        family_t: (z - 2 + 3 * moving_v) / 2,
    }
    moving_p = sp.factor(family_p.subs(moving_substitution))
    moving_q = sp.factor(family_q.subs(moving_substitution))
    p_rz = sp.expand(sum(
        coefficient
        * r**exponent[0]
        * z ** (exponent[1] - exponent[0])
        for exponent, coefficient in sp.Poly(
            sp.cancel(moving_p), moving_u, z
        ).terms()
    ))
    q_rz = sp.expand(sum(
        coefficient
        * r**exponent[0]
        * z ** (exponent[1] - exponent[0])
        for exponent, coefficient in sp.Poly(
            sp.cancel(moving_q), moving_u, z
        ).terms()
    ))
    assert sp.degree(p_rz, z) == 1
    assert sp.degree(q_rz, z) == 1
    p_radial = sp.factor(p_rz.coeff(z, 0))
    q_radial = sp.factor(q_rz.coeff(z, 0))
    p_normal = sp.factor(p_rz.coeff(z, 1))
    q_normal = sp.factor(q_rz.coeff(z, 1))
    assert sp.factor(
        p_radial
        - (
            -s * (s - 6) * r**3 / 48
            + (s - 6) * (s + 2) * r**2 / 16
            - (s - 6) * (s + 4) * r / 24
        )
    ) == 0
    assert sp.factor(p_normal + (s - 6) / 12) == 0
    assert sp.factor(
        q_radial
        - (
            -3 * s * r**4 / (16 * (s - 4))
            + (s + 2) * r**3 / (2 * (s - 4))
            - (s + 4) * r**2 / (4 * (s - 4))
        )
    ) == 0
    assert sp.factor(q_normal + r / (s - 4)) == 0
    tangent_factor = sp.factor(
        (
            3 * s * r**2
            - 6 * s * r
            - 12 * r
            + 2 * s
            + 8
        )
        / 4
    )
    assert sp.factor(
        sp.diff(p_radial, r)
        - tangent_factor * p_normal
    ) == 0
    assert sp.factor(
        sp.diff(q_radial, r)
        - tangent_factor * q_normal
    ) == 0
    assert [
        weight
        for weight in range(1, maximum_target_order + 7)
        if _canonical_cone_monomial(weight) is not None
    ] == list(range(5, maximum_target_order + 7))

    base_expressions = []
    for order, base in enumerate(base_velocity):
        base_expressions.append(sp.expand(sum(
            (
                coefficient
                * v**exponent[0]
                * z**exponent[1]
                for exponent, coefficient in base.items()
            ),
            sp.Integer(0),
        ).subs(v, u - 1)))
        if project_to_prefix_ray:
            base_expressions[-1] = project_expression(
                base_expressions[-1],
                order + 1,
            )

    target_terms: list[tuple[int, int, int, sp.Expr]] = []
    velocity = []
    normalized_rows = []
    row_records = []
    p_series = sp.series(
        p, s, 0, maximum_target_order + 1
    ).removeO().expand()
    q_series = sp.series(
        q, s, 0, maximum_target_order + 1
    ).removeO().expand()
    p_coefficients = [
        p_series.coeff(s, order)
        for order in range(maximum_target_order + 1)
    ]
    q_coefficients = [
        q_series.coeff(s, order)
        for order in range(maximum_target_order + 1)
    ]
    p_sparse_coefficients = [
        _to_sparse(value, u, z) for value in p_coefficients
    ]
    q_sparse_coefficients = [
        _to_sparse(value, u, z) for value in q_coefficients
    ]
    monomial_series: dict[
        tuple[int, int], list[sp.Expr]
    ] = {
        (0, 0): [
            sp.Integer(1),
            *(
                sp.Integer(0)
                for _ in range(maximum_target_order)
            ),
        ]
    }

    def monomial_coefficients(
        p_exponent: int,
        q_exponent: int,
    ) -> list[sp.Expr]:
        key = (p_exponent, q_exponent)
        if key in monomial_series:
            return monomial_series[key]
        if p_exponent:
            parent = monomial_coefficients(
                p_exponent - 1, q_exponent
            )
            factor = p_coefficients
        else:
            parent = monomial_coefficients(
                p_exponent, q_exponent - 1
            )
            factor = q_coefficients
        coefficients = [
            sp.expand(sum(
                (
                    parent[index]
                    * factor[order - index]
                    for index in range(order + 1)
                ),
                sp.Integer(0),
            ))
            for order in range(maximum_target_order + 1)
        ]
        monomial_series[key] = coefficients
        return coefficients

    monomial_sparse_series: dict[
        tuple[int, int, int],
        dict[tuple[int, int], sp.Expr],
    ] = {}

    def sparse_product(
        left: dict[tuple[int, int], sp.Expr],
        right: dict[tuple[int, int], sp.Expr],
    ) -> dict[tuple[int, int], sp.Expr]:
        result: dict[tuple[int, int], sp.Expr] = {}
        for left_exponent, left_coefficient in left.items():
            for right_exponent, right_coefficient in right.items():
                exponent = (
                    left_exponent[0] + right_exponent[0],
                    left_exponent[1] + right_exponent[1],
                )
                result[exponent] = (
                    result.get(exponent, sp.Integer(0))
                    + left_coefficient * right_coefficient
                )
        return {
            exponent: coefficient
            for exponent, coefficient in result.items()
            if coefficient != 0
        }

    def monomial_sparse_coefficient(
        p_exponent: int,
        q_exponent: int,
        order: int,
    ) -> dict[tuple[int, int], sp.Expr]:
        key = (p_exponent, q_exponent, order)
        if key in monomial_sparse_series:
            return monomial_sparse_series[key]
        if p_exponent == 0 and q_exponent == 0:
            result = (
                {(0, 0): sp.Integer(1)}
                if order == 0
                else {}
            )
            monomial_sparse_series[key] = result
            return result
        if p_exponent:
            parent_key = (p_exponent - 1, q_exponent)
            factor = p_sparse_coefficients
        else:
            parent_key = (p_exponent, q_exponent - 1)
            factor = q_sparse_coefficients
        result: dict[tuple[int, int], sp.Expr] = {}
        for index in range(order + 1):
            result = _add(
                result,
                sparse_product(
                    monomial_sparse_coefficient(
                        parent_key[0],
                        parent_key[1],
                        index,
                    ),
                    factor[order - index],
                ),
            )
        monomial_sparse_series[key] = result
        return result

    def sparse_expression(
        value: dict[tuple[int, int], sp.Expr],
    ) -> sp.Expr:
        return sp.expand(sum(
            (
                coefficient * u**exponent[0] * z**exponent[1]
                for exponent, coefficient in value.items()
            ),
            sp.Integer(0),
        ))

    target_c_terms = {
        (3, 0): sp.Integer(4),
        (2, 0): -sp.Integer(1),
        (1, 1): -sp.Integer(18),
        (0, 2): sp.Integer(27),
        (0, 1): sp.Integer(4),
    }
    seed_c = sp.expand(
        4 * p0**3
        - p0**2
        - 18 * p0 * q0
        + 27 * q0**2
        + 4 * q0
    )
    seed_c_sparse = _to_sparse(seed_c, u, z)
    assert all(
        exponent[1] - exponent[0] >= 2
        for exponent in seed_c_sparse
    )
    assert seed_c_sparse[(2, 4)] == -sp.Rational(9, 16)

    for target_order in range(1, maximum_target_order + 1):
        velocity_order = target_order
        residual = base_expressions[velocity_order]
        for (
            earlier_order,
            p_exponent,
            q_exponent,
            coefficient,
        ) in target_terms:
            if project_to_prefix_ray:
                delayed_source = project_sparse(
                    monomial_sparse_coefficient(
                        p_exponent,
                        q_exponent,
                        target_order - earlier_order,
                    ),
                    target_order + 1,
                )
                residual = sp.expand(
                    residual
                    + sparse_expression({
                        exponent: sp.factor(
                            8 * coefficient * source_coefficient
                        )
                        for exponent, source_coefficient
                        in delayed_source.items()
                    })
                )
            else:
                residual = sp.expand(
                    residual
                    + 8
                    * coefficient
                    * monomial_coefficients(
                        p_exponent, q_exponent
                    )[target_order - earlier_order]
                )
        residual = project_expression(
            residual,
            target_order + 1,
        )
        applied_prescribed_target_terms = []
        for (
            prescribed_order,
            prescribed_p,
            prescribed_q,
            prescribed_coefficient,
        ) in configured_prescribed_terms:
            if prescribed_order != target_order:
                continue
            applied_prescribed_target_terms.append((
                prescribed_p,
                prescribed_q,
                prescribed_coefficient,
            ))
            target_terms.append((
                target_order,
                prescribed_p,
                prescribed_q,
                prescribed_coefficient,
            ))
            residual = project_expression(
                sp.expand(
                    residual
                    + 8
                    * prescribed_coefficient
                    * p0**prescribed_p
                    * q0**prescribed_q
                ),
                target_order + 1,
            )

        current_row_log_scale = sp.Integer(1)
        if normalization_objective == "logarithm":
            current_velocity = [
                {},
                *velocity,
                _to_sparse(residual, u, z),
            ]
            if project_to_prefix_ray:
                current_logarithm = _projected_source_magnus(
                    current_velocity,
                    target_order + 1,
                    project_sparse,
                )[target_order + 1]
            else:
                current_logarithm = magnus_from_velocity(
                    current_velocity,
                    target_order + 1,
                    _ops(2),
                    VelocityPlacement.RIGHT_MULTIPLY,
                )[target_order + 1]
            objective_residual = sp.expand(sum(
                (
                    coefficient
                    * u**exponent[0]
                    * z**exponent[1]
                    for exponent, coefficient
                    in current_logarithm.items()
                ),
                sp.Integer(0),
            ))
            current_row_log_scale = sp.Rational(
                1, target_order + 1
            )
        else:
            objective_residual = residual

        row_terms = []
        while True:
            sparse = _to_sparse(objective_residual, u, z)
            cancellable = [
                exponent[0]
                for exponent, coefficient in sparse.items()
                if (
                    exponent[0] == exponent[1]
                    and _canonical_cone_monomial(exponent[0])
                    is not None
                )
            ]
            if not cancellable:
                break
            weight = max(cancellable)
            p_exponent, q_exponent = (
                _canonical_cone_monomial(weight)
            )
            coefficient = sp.factor(
                -sparse[(weight, weight)]
                / (
                    current_row_log_scale
                    * _seed_diagonal(p_exponent, q_exponent)
                )
            )
            assert coefficient != 0
            row_terms.append((
                p_exponent,
                q_exponent,
                coefficient,
            ))
            target_terms.append((
                target_order,
                p_exponent,
                q_exponent,
                coefficient,
            ))
            residual = sp.expand(
                residual
                + 8
                * coefficient
                * p0**p_exponent
                * q0**q_exponent
            )
            residual = project_expression(
                residual,
                target_order + 1,
            )
            objective_residual = sp.expand(
                objective_residual
                + current_row_log_scale
                * 8
                * coefficient
                * p0**p_exponent
                * q0**q_exponent
            )
            objective_residual = project_expression(
                objective_residual,
                target_order + 1,
            )

        second_normal_terms = []
        if cancel_second_normal:
            while True:
                sparse = _to_sparse(objective_residual, u, z)
                cancellable = [
                    exponent[0]
                    for exponent, coefficient in sparse.items()
                    if (
                        exponent[1] - exponent[0] == 2
                        and _canonical_c_multiplier(
                            exponent[0]
                        ) is not None
                    )
                ]
                if not cancellable:
                    break
                radial_degree = max(cancellable)
                p_exponent, q_exponent = (
                    _canonical_c_multiplier(radial_degree)
                )
                coefficient = sp.factor(
                    -sparse[(radial_degree, radial_degree + 2)]
                    / (
                        current_row_log_scale
                        * _seed_c_diagonal(
                            p_exponent, q_exponent
                        )
                    )
                )
                assert coefficient != 0
                second_normal_terms.append((
                    p_exponent,
                    q_exponent,
                    coefficient,
                ))
                for (
                    c_p_exponent,
                    c_q_exponent,
                ), c_coefficient in target_c_terms.items():
                    target_terms.append((
                        target_order,
                        p_exponent + c_p_exponent,
                        q_exponent + c_q_exponent,
                        sp.factor(
                            coefficient * c_coefficient
                        ),
                    ))
                residual = sp.expand(
                    residual
                    + 8
                    * coefficient
                    * p0**p_exponent
                    * q0**q_exponent
                    * seed_c
                )
                residual = project_expression(
                    residual,
                    target_order + 1,
                )
                objective_residual = sp.expand(
                    objective_residual
                    + current_row_log_scale
                    * 8
                    * coefficient
                    * p0**p_exponent
                    * q0**q_exponent
                    * seed_c
                )
                objective_residual = project_expression(
                    objective_residual,
                    target_order + 1,
                )

        applied_delayed_prefix_terms = []
        if target_order == 1:
            for (
                delayed_prefix_p,
                delayed_prefix_q,
                prefix_coefficient,
            ) in configured_delayed_prefix:
                applied_delayed_prefix_terms.append((
                    delayed_prefix_p,
                    delayed_prefix_q,
                    prefix_coefficient,
                ))
                for (
                    c_p_exponent,
                    c_q_exponent,
                ), c_coefficient in target_c_terms.items():
                    target_terms.append((
                        target_order,
                        delayed_prefix_p + c_p_exponent,
                        delayed_prefix_q + c_q_exponent,
                        sp.factor(
                            prefix_coefficient * c_coefficient
                        ),
                    ))
                prefix_pullback = sp.expand(
                    8
                    * prefix_coefficient
                    * p0**delayed_prefix_p
                    * q0**delayed_prefix_q
                    * seed_c
                )
                residual = sp.expand(
                    residual + prefix_pullback
                )
                residual = project_expression(
                    residual,
                    target_order + 1,
                )
                objective_residual = sp.expand(
                    objective_residual
                    + current_row_log_scale
                    * prefix_pullback
                )
                objective_residual = project_expression(
                    objective_residual,
                    target_order + 1,
                )

        final_sparse = _to_sparse(residual, u, z)
        inadmissible_source_terms = {
            exponent: coefficient
            for exponent, coefficient in final_sparse.items()
            if exponent != (0, 0) and exponent[1] < 3
        }
        if inadmissible_source_terms:
            raise AssertionError(
                "source Hamiltonian does not define a polynomial "
                f"density-z^2 field at target order {target_order}: "
                f"{inadmissible_source_terms}"
            )
        objective_final_sparse = _to_sparse(
            objective_residual, u, z
        )
        negative_normal_terms = {
            exponent: coefficient
            for exponent, coefficient
            in objective_final_sparse.items()
            if exponent[1] < exponent[0]
        }
        assert all(
            _canonical_cone_monomial(exponent[0]) is None
            for exponent, coefficient
            in objective_final_sparse.items()
            if exponent[0] == exponent[1]
        )
        velocity.append(final_sparse)
        normalized_rows.append(objective_final_sparse)
        maximum_degree = max(
            (
                sum(exponent)
                for exponent in objective_final_sparse
            ),
            default=None,
        )
        instantaneous_maximum_degree = max(
            (sum(exponent) for exponent in final_sparse),
            default=None,
        )
        normal_layers = {
            normal_order: max(
                exponent[0]
                for exponent in objective_final_sparse
                if exponent[1] - exponent[0] == normal_order
            )
            for normal_order in sorted({
                exponent[1] - exponent[0]
                for exponent in objective_final_sparse
            })
        }
        row_records.append({
            "target_order": target_order,
            "velocity_cost": target_order + 1,
            "target_terms": [
                {
                    "p_exponent": p_exponent,
                    "q_exponent": q_exponent,
                    "weight": (
                        2 * p_exponent + 3 * q_exponent
                    ),
                    "coefficient": str(coefficient),
                }
                for p_exponent, q_exponent, coefficient
                in row_terms
            ],
            "row_dimension": len(row_terms),
            "second_normal_kernel_terms": [
                {
                    "multiplier_p_exponent": p_exponent,
                    "multiplier_q_exponent": q_exponent,
                    "normal_radial_degree": (
                        2
                        + 2 * p_exponent
                        + 3 * q_exponent
                    ),
                    "coefficient": str(coefficient),
                }
                for p_exponent, q_exponent, coefficient
                in second_normal_terms
            ],
            "second_normal_dimension": len(second_normal_terms),
            "delayed_c_prefix_terms": [
                {
                    "multiplier_p_exponent": p_exponent,
                    "multiplier_q_exponent": q_exponent,
                    "coefficient": str(coefficient),
                }
                for p_exponent, q_exponent, coefficient
                in applied_delayed_prefix_terms
            ],
            "prescribed_target_terms": [
                {
                    "p_exponent": p_exponent,
                    "q_exponent": q_exponent,
                    "coefficient": str(coefficient),
                }
                for p_exponent, q_exponent, coefficient
                in applied_prescribed_target_terms
            ],
            "polynomial_source_hamiltonian": True,
            "negative_normal_terms": [
                [list(exponent), str(coefficient)]
                for exponent, coefficient
                in negative_normal_terms.items()
            ],
            "remaining_radial_terms": [
                [exponent[0], str(coefficient)]
                for exponent, coefficient
                in objective_final_sparse.items()
                if exponent[0] == exponent[1]
            ],
            "maximum_hamiltonian_degree": maximum_degree,
            "instantaneous_maximum_hamiltonian_degree": (
                instantaneous_maximum_degree
            ),
            "maximum_r_degree_by_normal_order": {
                str(normal_order): radial_degree
                for normal_order, radial_degree
                in normal_layers.items()
            },
            "normal_order_one_absent": 1 not in normal_layers,
            "top_terms": [
                [list(exponent), str(coefficient)]
                for exponent, coefficient
                in objective_final_sparse.items()
                if (
                    maximum_degree is not None
                    and sum(exponent) == maximum_degree
                )
            ],
        })
        if normalization_objective == "velocity":
            assert len(row_terms) == target_order + 2

    maximum_source_degree = max(
        max((sum(exponent) for exponent in value), default=-1)
        for value in velocity
    )
    source_slopes = [
        Fraction(
            max(sum(exponent) for exponent in value) - 4,
            cost,
        )
        for cost, value in enumerate(normalized_rows, 2)
        if value
    ]
    source_newton_slope = max(source_slopes)

    combined_target_coefficients: dict[
        tuple[int, int, int], sp.Expr
    ] = {}
    for order, p_exponent, q_exponent, coefficient in target_terms:
        key = (order, p_exponent, q_exponent)
        combined_coefficient = sp.cancel(
            combined_target_coefficients.get(key, sp.Integer(0))
            + coefficient
        )
        if combined_coefficient == 0:
            combined_target_coefficients.pop(key, None)
        else:
            combined_target_coefficients[key] = combined_coefficient
    effective_target_terms = [
        (*key, coefficient)
        for key, coefficient in sorted(
            combined_target_coefficients.items()
        )
    ]

    uniform_degrees = [
        6 * p_exponent + 8 * q_exponent
        for p_exponent, q_exponent in {
        (p_exponent, q_exponent)
        for _, p_exponent, q_exponent, _ in effective_target_terms
        }
    ]
    uniform_source_degree = max(
        [18] + uniform_degrees
    )
    tail_first_cost = maximum_target_order + 2
    tail_slope_bound = Fraction(
        uniform_source_degree - 4,
        tail_first_cost,
    )

    target_slopes = [
        Fraction(p_exponent + q_exponent - 2, order + 1)
        for order, p_exponent, q_exponent, coefficient
        in effective_target_terms
    ]
    target_rate_bound = max([Fraction(1)] + target_slopes)
    source_logarithmic_degrees = None
    source_logarithmic_top_terms = None
    source_logarithmic_normal_leading_terms = None
    prefix_ray_projection = None
    target_logarithmic_degrees = None
    target_logarithmic_top_terms = None
    source_roundtrip = False
    target_roundtrip = False
    if compute_logarithms:
        source_velocity = [{}] + velocity
        if project_to_prefix_ray:
            source_logarithm = _projected_source_magnus(
                source_velocity,
                maximum_cost,
                project_sparse,
            )
        else:
            source_logarithm = magnus_from_velocity(
                source_velocity,
                maximum_cost,
                _ops(2),
                VelocityPlacement.RIGHT_MULTIPLY,
            )
        source_logarithmic_degrees = [
            max(
                (sum(exponent) for exponent in value),
                default=None,
            )
            for value in source_logarithm[1:]
        ]
        if not configured_delayed_prefix:
            assert all(
                degree is None or degree <= 2 * order + 4
                for order, degree in enumerate(
                    source_logarithmic_degrees, 1
                )
            )
        if normalization_objective == "logarithm":
            row_mismatches = []
            for order in range(maximum_target_order):
                delta = _add(
                    source_logarithm[order + 2],
                    {
                        exponent: -coefficient
                        for exponent, coefficient
                        in normalized_rows[order].items()
                    },
                )
                if delta:
                    row_mismatches.append((order + 1, delta))
            if row_mismatches:
                raise AssertionError(
                    "incremental/global source Magnus mismatch: "
                    f"{row_mismatches}"
                )
        source_logarithmic_top_terms = [
            [
                [list(exponent), str(coefficient)]
                for exponent, coefficient in value.items()
                if (
                    degree is not None
                    and sum(exponent) == degree
                )
            ]
            for value, degree in zip(
                source_logarithm[1:],
                source_logarithmic_degrees,
                strict=True,
            )
        ]
        source_logarithmic_normal_leading_terms = [
            [
                [
                    normal_order,
                    [maximum_r_degree, maximum_r_degree + normal_order],
                    str(value[(
                        maximum_r_degree,
                        maximum_r_degree + normal_order,
                    )]),
                ]
                for normal_order in sorted({
                    exponent[1] - exponent[0]
                    for exponent in value
                })
                for maximum_r_degree in [max(
                    exponent[0]
                    for exponent in value
                    if exponent[1] - exponent[0] == normal_order
                )]
            ]
            for value in source_logarithm[1:]
        ]
        if project_to_prefix_ray:
            prefix_weight = projection_weight
            assert prefix_weight is not None
            prefix_slope = projection_slope
            assert prefix_slope is not None
            prefix_source_slopes = (
                projection_source_slopes
                if projection_source_slopes is not None
                else (prefix_slope, prefix_slope)
            )
            terminal_grade = projection_terminal_grade
            assert terminal_grade is not None

            def prefix_grade(
                exponent: tuple[int, int],
                cost: int,
            ) -> tuple[int, int]:
                return (
                    2 * exponent[0]
                    - prefix_source_slopes[0] * cost
                    - 2,
                    2 * exponent[1]
                    - prefix_source_slopes[1] * cost
                    - 6,
                )

            def projected_rows(
                rows: list[dict[tuple[int, int], sp.Expr]],
            ) -> list[list[list[object]]]:
                return [
                    [
                        [
                            list(prefix_grade(exponent, cost)),
                            list(exponent),
                            str(coefficient),
                        ]
                        for exponent, coefficient in sorted(value.items())
                        if all(
                            grade_component >= terminal_component
                            for grade_component, terminal_component
                            in zip(
                                prefix_grade(exponent, cost),
                                terminal_grade,
                                strict=True,
                            )
                        )
                    ]
                    for cost, value in enumerate(rows, 1)
                ]

            prefix_ray_projection = {
                "grading": (
                    "(2*a-source_slope_u*cost-2, "
                    "2*b-source_slope_z*cost-6)"
                ),
                "weight": prefix_weight,
                "slope": prefix_slope,
                "source_slopes": list(prefix_source_slopes),
                "terminal_grade": list(terminal_grade),
                "source_velocity": projected_rows(source_velocity),
                "source_logarithm": projected_rows(
                    source_logarithm[1:]
                ),
            }
        if verify_roundtrips:
            source_replay = velocity_from_magnus(
                source_logarithm,
                maximum_cost,
                _ops(2),
                VelocityPlacement.RIGHT_MULTIPLY,
            )
            assert source_replay[:maximum_cost] == source_velocity
            source_roundtrip = True
    target_velocity = [
        {} for _ in range(maximum_cost)
    ]
    for order, p_exponent, q_exponent, coefficient in effective_target_terms:
        exponent = (p_exponent, q_exponent)
        target_velocity[order][exponent] = coefficient
    if compute_logarithms and not project_to_prefix_ray:
        target_logarithm = magnus_from_velocity(
            target_velocity,
            maximum_cost,
            _ops(0),
            VelocityPlacement.LEFT_MULTIPLY,
        )
        target_logarithmic_degrees = [
            max(
                (sum(exponent) for exponent in value),
                default=None,
            )
            for value in target_logarithm[1:]
        ]
        target_logarithmic_top_terms = [
            [
                [list(exponent), str(coefficient)]
                for exponent, coefficient in value.items()
                if (
                    degree is not None
                    and sum(exponent) == degree
                )
            ]
            for value, degree in zip(
                target_logarithm[1:],
                target_logarithmic_degrees,
                strict=True,
            )
        ]
        if verify_roundtrips:
            target_replay = velocity_from_magnus(
                target_logarithm,
                maximum_cost,
                _ops(0),
                VelocityPlacement.LEFT_MULTIPLY,
            )
            target_roundtrip_deltas = [
                _add(
                    replay_row,
                    {
                        exponent: -coefficient
                        for exponent, coefficient in velocity_row.items()
                    },
                )
                for replay_row, velocity_row in zip(
                    target_replay[:maximum_cost],
                    target_velocity,
                    strict=True,
                )
            ]
            if any(target_roundtrip_deltas):
                raise AssertionError(
                    "target Magnus/dexp round-trip mismatch: "
                    f"{target_roundtrip_deltas}"
                )
            target_roundtrip = True

    return {
        "schema": (
            "axiompack.jacobian_cone_radial_"
            "triangular_staircase.v2"
        ),
        "maximum_target_order": maximum_target_order,
        "cancel_second_normal": cancel_second_normal,
        "verify_roundtrips": verify_roundtrips,
        "compute_logarithms": compute_logarithms,
        "normalization_objective": normalization_objective,
        "project_to_prefix_ray": project_to_prefix_ray,
        "prefix_slope_override": prefix_slope_override,
        "prefix_weight_override": prefix_weight_override,
        "prefix_source_slopes_override": (
            None
            if prefix_source_slopes_override is None
            else list(prefix_source_slopes_override)
        ),
        "prefix_terminal_grade_override": (
            None
            if prefix_terminal_grade_override is None
            else list(prefix_terminal_grade_override)
        ),
        "delayed_c_prefix_coefficient": (
            None
            if delayed_c_prefix_coefficient is None
            else str(delayed_c_prefix_coefficient)
        ),
        "delayed_c_prefix_multiplier": [
            delayed_c_prefix_multiplier[0],
            delayed_c_prefix_multiplier[1],
        ],
        "configured_delayed_c_prefix_terms": [
            {
                "multiplier_p_exponent": p_exponent,
                "multiplier_q_exponent": q_exponent,
                "coefficient": str(coefficient),
            }
            for p_exponent, q_exponent, coefficient
            in configured_delayed_prefix
        ],
        "configured_prescribed_target_terms": [
            {
                "target_order": target_order,
                "p_exponent": p_exponent,
                "q_exponent": q_exponent,
                "coefficient": str(coefficient),
            }
            for (
                target_order,
                p_exponent,
                q_exponent,
                coefficient,
            ) in configured_prescribed_terms
        ],
        "rows": row_records,
        "moving_tangency_identity": (
            "in U_s=1+3(s-4)v/(2(s-6)), "
            "d_r(P_rad,Q_rad)=L_s(r)*(P_z,Q_z), "
            "L_s=(3*s*r^2-6*s*r-12*r+2*s+8)/4"
        ),
        "seed_cone_target_lift_radial_semigroup": "{w:w>=5}",
        "all_target_terms": [
            {
                "target_order": order,
                "p_exponent": p_exponent,
                "q_exponent": q_exponent,
                "weight": 2 * p_exponent + 3 * q_exponent,
                "coefficient": str(coefficient),
            }
            for order, p_exponent, q_exponent, coefficient
            in target_terms
        ],
        "source_newton_slope_over_computed_rows": str(
            source_newton_slope
        ),
        "maximum_computed_source_hamiltonian_degree": (
            maximum_source_degree
        ),
        "uniform_source_hamiltonian_degree": (
            uniform_source_degree
        ),
        "tail_first_cost": tail_first_cost,
        "tail_slope_bound": str(tail_slope_bound),
        "target_logarithmic_rate_bound": str(target_rate_bound),
        "source_forward_dexp_roundtrip": source_roundtrip,
        "source_logarithmic_hamiltonian_degrees": (
            source_logarithmic_degrees
        ),
        "source_logarithmic_top_terms": (
            source_logarithmic_top_terms
        ),
        "source_logarithmic_normal_leading_terms": (
            source_logarithmic_normal_leading_terms
        ),
        "prefix_candidate_ray_projection": prefix_ray_projection,
        "target_forward_dexp_roundtrip": target_roundtrip,
        "target_logarithmic_hamiltonian_degrees": (
            target_logarithmic_degrees
        ),
        "target_logarithmic_top_terms": (
            target_logarithmic_top_terms
        ),
        "claim_boundary": (
            "Exact finite target-lift-compatible triangular replay. "
            "The all-order rate bound additionally uses the moving-chart "
            "coefficient filtration and radial induction."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
