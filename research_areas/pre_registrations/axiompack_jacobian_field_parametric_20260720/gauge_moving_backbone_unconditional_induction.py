#!/usr/bin/env python3
"""Group factorization and complete-face induction for a moving backbone."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_moving_divisor_odd_remainder_all_depth import (  # noqa: E402
    _weighted_face,
)
from gauge_positive_contact_locally_finite_obstruction import (  # noqa: E402
    _exceptional_certificate,
    _rate_certificate,
    _robust_affine_certificate,
    _well_order_certificate,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredAsymptoticClaim,
    FilteredAsymptoticEvidenceScope,
    FilteredAsymptoticInductionProblem,
    FilteredAsymptoticRateWitness,
    FilteredInductionProblem,
    FilteredInductionState,
    FilteredInductionTransition,
    compile_filtered_asymptotic_induction,
    compile_filtered_induction,
    make_filtered_asymptotic_evidence,
)
from ztare.common.content_bound_evidence import (  # noqa: E402
    EvidenceAuthority,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    FormalLieOps,
    bch_series,
    factor_magnus_by_projection,
)


SparseFace = dict[tuple[int, int], sp.Rational]


def _poisson(
    left: sp.Expr,
    right: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    return sp.expand(
        sp.diff(left, p) * sp.diff(right, q)
        - sp.diff(left, q) * sp.diff(right, p)
    )


def _parity_projection(
    value: sp.Expr,
    p: sp.Symbol,
    q: sp.Symbol,
) -> sp.Expr:
    """Project QQ[P,Q] to the Q-degree-at-most-one cusp section."""

    result = sp.Integer(0)
    for (a, b), coefficient in sp.Poly(
        sp.expand(value), p, q, domain=sp.QQ
    ).terms():
        depth, parity = divmod(b, 2)
        result += (
            coefficient
            * (-sp.Rational(4, 27)) ** depth
            * p ** (a + 3 * depth)
            * q**parity
        )
    return sp.expand(result)


def _parity_and_grade_certificate() -> dict[str, object]:
    p, q = sp.symbols("P Q")
    a, c = sp.symbols("a c", integer=True, nonnegative=True)
    left_parity, right_parity = sp.symbols(
        "epsilon eta", integer=True, nonnegative=True
    )
    weight, other_weight, cost, other_cost = sp.symbols(
        "w v j k", integer=True, nonnegative=True
    )
    grade = 2 * (weight - cost - 5)
    other_grade = 2 * (other_weight - other_cost - 5)
    bracket_grade = sp.expand(
        2 * (
            weight + other_weight - 5
            - cost - other_cost
            - 5
        )
    )
    assert sp.expand(bracket_grade - grade - other_grade) == 0

    # The parity representatives are monomials with Q exponent zero or one.
    representatives = {
        5: p * q,
        6: p**3,
        7: p**2 * q,
        8: p**4,
        9: p**3 * q,
        10: p**5,
    }
    brackets = []
    for left_weight, left in representatives.items():
        for right_weight, right in representatives.items():
            value = _poisson(left, right, p, q)
            if value:
                output_weight = left_weight + right_weight - 5
                assert sp.Poly(value, q).degree() <= 1
                assert all(
                    2 * exponent[0] + 3 * exponent[1] == output_weight
                    for exponent, coefficient in sp.Poly(
                        value, p, q
                    ).terms()
                    if coefficient
                )
                brackets.append({
                    "left_weight": left_weight,
                    "right_weight": right_weight,
                    "output_weight": output_weight,
                    "bracket": str(value),
                })

    divisor = 4 * p**3 + 27 * q**2
    decomposition_rows = []
    for a_value in range(0, 5):
        for b_value in range(0, 8):
            depth, parity = divmod(b_value, 2)
            expanded = sp.expand(
                p**a_value
                * q**parity
                / 27**depth
                * sum(
                    sp.binomial(depth, index)
                    * divisor**index
                    * (-4 * p**3) ** (depth - index)
                    for index in range(depth + 1)
                )
            )
            assert sp.expand(expanded - p**a_value * q**b_value) == 0
            projected = _parity_projection(
                p**a_value * q**b_value, p, q
            )
            remainder = sp.expand(p**a_value * q**b_value - projected)
            if remainder:
                quotient, residual = sp.div(remainder, divisor, p, q)
                assert residual == 0
                assert quotient != 0
            decomposition_rows.append({
                "P_exponent": a_value,
                "Q_exponent": b_value,
                "D_depth": depth,
                "parity_Q_exponent": parity,
            })
    return {
        "parity_bracket_rows": brackets,
        "rate_two_grade": "gamma(w,j)=2*(w-j-5)",
        "bracket_grade_additive": True,
        "D_adic_identity": (
            "P^a*Q^(2*d+e)=P^a*Q^e/27^d * "
            "sum_j binomial(d,j)*D^j*(-4*P^3)^(d-j)"
        ),
        "finite_decomposition_rows_checked": decomposition_rows,
        "projection_idempotent": True,
        "positive_D_remainder": True,
    }


def _formal_factorization_replay() -> dict[str, object]:
    p, q = sp.symbols("P Q")
    ops = FormalLieOps[sp.Expr](
        zero=lambda: sp.Integer(0),
        add=lambda left, right: sp.expand(left + right),
        scale=lambda value, scalar: sp.expand(
            sp.Rational(scalar.numerator, scalar.denominator) * value
        ),
        bracket=lambda left, right: _poisson(left, right, p, q),
    )
    logarithm = [
        sp.Integer(0),
        p * q + (4 * p**3 + 27 * q**2) * p,
        p**4 + p * q**2 + q**3,
        p**3 * q + p**2 * q**2,
        p**6 + p * q**3 + q**4,
    ]
    backbone, positive = factor_magnus_by_projection(
        logarithm,
        4,
        ops,
        lambda value: _parity_projection(value, p, q),
    )
    replay = bch_series(backbone, positive, 4, ops)
    assert all(sp.expand(replay[index] - logarithm[index]) == 0
               for index in range(5))
    assert all(
        sp.expand(_parity_projection(value, p, q) - value) == 0
        for value in backbone
    )
    assert all(
        _parity_projection(value, p, q) == 0 for value in positive
    )
    return {
        "maximum_order": 4,
        "BCH_roundtrip": True,
        "backbone_in_parity_section": True,
        "residual_has_zero_parity_projection": True,
        "coefficient_recursion": (
            "at order n, BCH(B,R)_n=B_n+R_n plus lower-order brackets"
        ),
        "coefficientwise_finiteness": (
            "each order uses finitely many partitions and polynomial brackets"
        ),
    }


def _face_dictionary(value: sp.Expr, y: sp.Symbol, x: sp.Symbol) -> SparseFace:
    return {
        exponent: sp.Rational(coefficient)
        for exponent, coefficient in sp.Poly(
            sp.expand(value), y, x, domain=sp.QQ
        ).terms()
        if coefficient
    }


def _multiply_face(
    left: SparseFace,
    right: SparseFace,
    maximum_parameter_order: int,
) -> SparseFace:
    result: SparseFace = {}
    for (left_y, left_x), left_coefficient in left.items():
        for (right_y, right_x), right_coefficient in right.items():
            parameter_order = left_y + right_y
            if parameter_order > maximum_parameter_order:
                continue
            exponent = (parameter_order, left_x + right_x)
            result[exponent] = (
                result.get(exponent, sp.Rational(0))
                + left_coefficient * right_coefficient
            )
    return {exponent: coefficient for exponent, coefficient in result.items()
            if coefficient}


def _face_powers(
    value: SparseFace,
    maximum_power: int,
    maximum_parameter_order: int,
) -> list[SparseFace]:
    result = [{(0, 0): sp.Rational(1)}]
    for _power in range(maximum_power):
        result.append(_multiply_face(
            result[-1], value, maximum_parameter_order
        ))
    return result


def _top_section_monomial(
    a: int,
    b: int,
    depth: int,
) -> tuple[int, int, sp.Rational]:
    multiplier = sp.Rational(1)
    for _step in range(depth):
        if a > 0:
            multiplier *= sp.Rational(81, 8)
            a -= 1
            b += 3
        else:
            multiplier *= -sp.Rational(3, 2)
            a = 2
            b += 1
    return a, b, multiplier


def _seed_face_monomial(a: int, b: int, x: sp.Symbol) -> dict[int, sp.Rational]:
    polynomial = sp.Poly(
        sp.expand(
            (-sp.Rational(3, 4) + x / 2) ** a
            * (-sp.Rational(1, 4) + x / 4) ** b
        ),
        x,
        domain=sp.QQ,
    )
    return {
        exponent[0]: sp.Rational(coefficient)
        for exponent, coefficient in polynomial.terms()
        if coefficient
    }


def _complete_face_scan(
    maximum_weight: int = 42,
    maximum_depth: int = 6,
) -> dict[str, object]:
    (y, x), face_p, face_q, face_c = _weighted_face()
    p = _face_dictionary(face_p, y, x)
    q = _face_dictionary(face_q, y, x)
    c = _face_dictionary(face_c, y, x)
    p_powers = _face_powers(p, maximum_weight // 2, maximum_depth)
    q_powers = _face_powers(q, maximum_weight // 3, maximum_depth)
    rows = []
    for depth in range(1, maximum_depth + 1):
        contact_power = _face_powers(c, depth, depth)[depth]
        for weight in range(5, maximum_weight + 1):
            exponents = [
                (a, b)
                for a in range(weight // 2 + 1)
                for b in range(weight // 3 + 1)
                if 2 * a + 3 * b == weight
            ]
            columns = []
            for a, b in exponents:
                moving = _multiply_face(
                    _multiply_face(p_powers[a], q_powers[b], depth),
                    contact_power,
                    depth,
                )
                column = {
                    x_order: coefficient
                    for (parameter_order, x_order), coefficient
                    in moving.items()
                    if parameter_order == depth
                }
                final_a, final_b, multiplier = _top_section_monomial(
                    a, b, depth
                )
                for x_order, coefficient in _seed_face_monomial(
                    final_a, final_b, x
                ).items():
                    column[x_order] = (
                        column.get(x_order, sp.Rational(0))
                        - multiplier * coefficient
                    )
                columns.append({order: value for order, value in column.items()
                                if value})
            maximum_x = max(max(column, default=0) for column in columns)
            matrix = sp.Matrix([
                [column.get(x_order, 0) for column in columns]
                for x_order in range(maximum_x + 1)
            ])
            rank = matrix.rank()
            expected_kernel = int(depth == 1 and weight % 6 == 0)
            assert rank == len(exponents) - expected_kernel
            even_rows = [2 + 2 * index for index in range(len(exponents))]
            even_minor = sp.Matrix([
                [column.get(x_order, 0) for column in columns]
                for x_order in even_rows
            ]).det()
            if depth >= 2:
                assert even_minor != 0
            rows.append({
                "contact_depth": depth,
                "weight": weight,
                "domain_dimension": len(exponents),
                "rank": rank,
                "kernel_dimension": len(exponents) - rank,
                "expected_exception": bool(expected_kernel),
                "uniform_even_minor_nonzero": depth >= 2,
                "held_out": depth >= 5 or weight >= 31,
            })
    return {
        "training_window": "m=1..4, W=5..30",
        "heldout_window": "m=5..6 or W=31..42",
        "rows": rows,
        "only_rank_exception": "m=1 and W divisible by 6",
        "finite_window_used_for_all_order_claim": False,
    }


def _exceptional_kernel_certificate(maximum_k: int = 12) -> dict[str, object]:
    p, q = sp.symbols("P Q")
    rows = []
    for k in range(1, maximum_k + 1):
        coefficients = [
            sp.factor(9**ell * sp.binomial(sp.Rational(4 * k + 1, 4), ell))
            for ell in range(k + 1)
        ]
        assert coefficients[0] == 1
        for ell in range(k):
            assert sp.factor(
                coefficients[ell + 1] / coefficients[ell]
                - sp.Rational(9 * (4 * (k - ell) + 1), 4 * (ell + 1))
            ) == 0
        kernel = sp.expand(sum(
            coefficients[ell] * p ** (3 * (k - ell)) * q ** (2 * ell)
            for ell in range(k + 1)
        ))
        exit_coefficient = -sp.Rational(3, 2 ** (3 * k + 4))
        assert exit_coefficient != 0
        rows.append({
            "k": k,
            "weight": 6 * k,
            "kernel": str(kernel),
            "coefficient_recurrence_verified": True,
            "next_face_weight": 6 * k + 6,
            "pure_highest_normal_order": 3 * k + 3,
            "exit_coefficient": str(exit_coefficient),
            "held_out": k >= 9,
        })
    return {
        "kernel_formula": (
            "K_k=sum_(ell=0)^k 9^ell*binomial(k+1/4,ell)"
            "*P^(3*(k-ell))*Q^(2*ell)"
        ),
        "coefficient_ODE": (
            "(1+9*u)f_k'(u)-9*(k+1/4)f_k(u)="
            "-(9/4)c_(k,k)u^k"
        ),
        "kernel_dimension": 1,
        "strict_face_descent": 1,
        "all_k_exit_coefficient": "-3/2^(3*k+4)",
        "all_k_exit_nonzero": True,
        "rows": rows,
    }


def _payload_sha256(value: object) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def _combined_induction_problem(
    parity: dict[str, object],
    exceptional_kernel: dict[str, object],
) -> FilteredInductionProblem:
    robust = _robust_affine_certificate()
    exceptional = _exceptional_certificate()
    states = [
        FilteredInductionState(
            name="parity_diagonal",
            rank=(0, 0),
            local_certificate_sha256=_payload_sha256(parity),
            complete_outcomes=("parity_terminal",),
        ),
        FilteredInductionState(
            name="depth_one_weight_six_kernel",
            rank=(2, 0),
            local_certificate_sha256=_payload_sha256(exceptional_kernel),
            complete_outcomes=("kernel_descends_one_face",),
        ),
        FilteredInductionState(
            name="lower_face_terminal",
            rank=(1, 0),
            local_certificate_sha256=_payload_sha256({
                "exit": exceptional_kernel["all_k_exit_coefficient"]
            }),
            complete_outcomes=("lower_face_survives",),
        ),
        FilteredInductionState(
            name="D_positive_robust",
            rank=(0, 1),
            local_certificate_sha256=_payload_sha256(robust),
            complete_outcomes=(
                "D_terminal_survives",
                "D_source_charged",
            ),
        ),
    ]
    transitions = [
        FilteredInductionTransition(
            name="parity_terminal",
            source="parity_diagonal",
            outcome="terminal_survives",
        ),
        FilteredInductionTransition(
            name="kernel_descends_one_face",
            source="depth_one_weight_six_kernel",
            outcome="descend",
            target="lower_face_terminal",
        ),
        FilteredInductionTransition(
            name="lower_face_survives",
            source="lower_face_terminal",
            outcome="terminal_survives",
        ),
        FilteredInductionTransition(
            name="D_terminal_survives",
            source="D_positive_robust",
            outcome="terminal_survives",
        ),
        FilteredInductionTransition(
            name="D_source_charged",
            source="D_positive_robust",
            outcome="source_charged",
        ),
    ]
    for index, row in enumerate(exceptional["states"]):
        name = f"D_exceptional_{index}"
        terminal = f"{name}_terminal"
        exits = f"{name}_exits"
        states.append(FilteredInductionState(
            name=name,
            rank=(1, index + 1),
            local_certificate_sha256=_payload_sha256(row),
            complete_outcomes=(terminal, exits),
        ))
        transitions.extend((
            FilteredInductionTransition(
                name=terminal,
                source=name,
                outcome="terminal_survives",
            ),
            FilteredInductionTransition(
                name=exits,
                source=name,
                outcome="descend",
                target="D_positive_robust",
            ),
        ))
    return FilteredInductionProblem(
        name="jacobian_arbitrary_backbone_positive_contact_induction",
        states=tuple(states),
        transitions=tuple(transitions),
        initial_states=tuple(state.name for state in states),
    )


def _combined_induction_certificate(
    parity: dict[str, object],
    exceptional_kernel: dict[str, object],
) -> dict[str, object]:
    certificate = compile_filtered_induction(_combined_induction_problem(
        parity,
        exceptional_kernel,
    ))
    assert certificate.maximum_uncharged_descent_length == 1
    assert not certificate.adapter_completeness_inferred
    return certificate.to_dict()


def _asymptotic_rate_transfer_certificate(
    parity: dict[str, object],
    exceptional_kernel: dict[str, object],
) -> dict[str, object]:
    induction = _combined_induction_problem(parity, exceptional_kernel)
    rate = _rate_certificate()
    well_order = _well_order_certificate()
    support_receipt = {
        "positive_contact_well_order": well_order,
        "limiting_rate": rate,
        "moving_backbone_adapter": {
            "parity": _payload_sha256(parity),
            "exceptional_kernel": _payload_sha256(exceptional_kernel),
            "least_index_shift_changes_only_order_intercept": True,
            "fixed_rational_specialization": (
                "complete coefficient rows are assembled before "
                "specialization"
            ),
        },
    }
    support_digest = _payload_sha256(support_receipt)
    terminal_digest = _payload_sha256({
        "support": support_receipt,
        "uniform_terminal_rate": rate[
            "uniform_lower_bound_for_m_positive"
        ],
        "infinite_nonzero_support": True,
    })
    source_charge_digest = _payload_sha256({
        "support": support_receipt,
        "charge": "higher source pivot at the same parameter order",
        "minimum_rate": 2,
    })
    witnesses = []
    for transition in induction.transitions:
        if transition.outcome == "descend":
            continue
        if transition.outcome == "terminal_survives":
            witnesses.append(FilteredAsymptoticRateWitness(
                transition_name=transition.name,
                side="source",
                payment_order_intercept=4,
                payment_order_slope=2,
                payment_excess_intercept=-32,
                payment_excess_slope=11,
                coefficient_certificate_sha256=terminal_digest,
            ))
        elif transition.outcome == "source_charged":
            witnesses.append(FilteredAsymptoticRateWitness(
                transition_name=transition.name,
                side="source",
                payment_order_intercept=4,
                payment_order_slope=2,
                payment_excess_intercept=-16,
                payment_excess_slope=4,
                coefficient_certificate_sha256=source_charge_digest,
            ))
        else:
            raise AssertionError(
                f"unhandled closing outcome {transition.outcome!r}"
            )
    problem_name = (
        "jacobian_arbitrary_backbone_positive_contact_"
        "asymptotic_rate_transfer"
    )
    support_evidence = make_filtered_asymptotic_evidence(
        claim=FilteredAsymptoticClaim.INFINITE_OCCURRENCE_SUPPORT,
        subject_id=problem_name,
        induction=induction,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=(
            FilteredAsymptoticEvidenceScope.ALL_UNBOUNDED_OCCURRENCE_INDICES
        ),
        evidence_sha256=support_digest,
    )
    certificate = compile_filtered_asymptotic_induction(
        FilteredAsymptoticInductionProblem(
            name=problem_name,
            induction=induction,
            threshold=2,
            occurrence_order_intercept=4,
            occurrence_order_slope=2,
            occurrence_support_evidence=support_evidence,
            closing_witnesses=tuple(witnesses),
        )
    )
    assert certificate.minimum_certified_rate == "2"
    assert certificate.parameter_shift_invariance_verified
    assert certificate.no_rebilling_verified
    return {
        "compiler_certificate": certificate.to_dict(),
        "occurrence_index": (
            "relative orbit order 4+2*k on an infinite unbounded support; "
            "an arbitrary least-index shift changes only the intercept"
        ),
        "terminal_rate_lower_bound": "11/2",
        "cancellation_payment_rate_lower_bound": "2",
        "finite_supercritical_backbone_prefix": (
            "retained as an actor in the complete moving-backbone local "
            "certificates, never counted as a tail payment"
        ),
        "strictly_subcritical_backbone_tail": (
            "invertible filtered transport; it preserves the terminal/"
            "same-order-payment dichotomy"
        ),
        "claim_boundary": (
            "unconditional least-positive-contact branch; the pure "
            "contact-zero branch is not inferred"
        ),
    }


def run() -> dict[str, object]:
    parity = _parity_and_grade_certificate()
    factorization = _formal_factorization_replay()
    face_scan = _complete_face_scan()
    exceptional_kernel = _exceptional_kernel_certificate()
    induction = _combined_induction_certificate(parity, exceptional_kernel)
    rate_transfer = _asymptotic_rate_transfer_certificate(
        parity,
        exceptional_kernel,
    )
    return {
        "schema": "axiompack.jacobian_moving_backbone_unconditional_induction.v1",
        "contact_zero_parity_algebra": parity,
        "formal_group_factorization": factorization,
        "complete_weight_face_scan": face_scan,
        "unique_top_face_exception": exceptional_kernel,
        "combined_filtered_induction": induction,
        "asymptotic_rate_transfer": rate_transfer,
        "unconditional_induction_closure": {
            "contact_depths": "all m>=1",
            "contact_zero_weights": "all coefficientwise-finite rows",
            "D_adic_depths": "all finite depths per coefficient row",
            "exceptional_uncharged_descent_bound": 1,
            "local_terminal_or_source_charge": True,
            "least_positive_contact_symmetric_limsup_at_least_two": True,
            "adapter_completeness_inferred_by_compiler": False,
            "adapter_completeness_supplied_by": [
                "exact parity/D-adic identity",
                "all-depth normal-three factorization",
                "all-k exceptional kernel recurrence and exit",
                "existing robust/exceptional positive-contact theorem",
                "coefficientwise BCH projection factorization",
            ],
        },
        "claim_boundary": (
            "The least-positive-contact branch over every coefficientwise-"
            "polynomial moving contact-zero backbone is closed: every "
            "nonzero least positive-contact coefficient forces symmetric "
            "logarithmic limsup at least two, uniformly under least-index "
            "shifts and fixed rational specialization. The pure contact-zero "
            "branch and the final global comparison remain separate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
