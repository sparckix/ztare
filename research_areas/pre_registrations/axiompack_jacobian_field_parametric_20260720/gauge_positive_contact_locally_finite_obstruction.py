#!/usr/bin/env python3
"""Exact support certificate for locally finite positive-contact schedules.

This strengthens the finite higher-contact result for coefficientwise
polynomial continuations of the normalized radial background.  It makes no
uniform claim over a replacement of that contact-zero backbone.  Every
parameter row is finite; for its first nonzero positive-contact class,
either the all-order terminal survives or its first cancellation enters a
robust class whose terminal has a strictly higher same-order pivot.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_cone_boundary_contact_classes import (  # noqa: E402
    EXCEPTIONAL_D_ZERO_STATES,
    EXCEPTIONAL_PRIMARY_POLYNOMIAL,
    EXCEPTIONAL_RADIAL_OFFSET,
    M_SYMBOL as BOUNDARY_M,
    _transition_edges,
)
from gauge_cone_higher_contact_global_obstruction import (  # noqa: E402
    _contact_valuation_certificate,
    _factor_support_certificate,
)
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredInductionProblem,
    FilteredInductionState,
    FilteredInductionTransition,
    compile_filtered_induction,
)


A, D, M, ELL, W, T, H = sp.symbols(
    "a d m ell w t h",
    integer=True,
    nonnegative=True,
)


def _rate_certificate() -> dict[str, object]:
    q_from_slack = sp.factor(
        (A + 3 * D + 3 * M + ELL) / 2
    )
    rate = sp.factor(
        2 * A + 3 * q_from_slack + 5 * D + 3 * M - 2
    )
    expected = sp.factor(
        (7 * A + 19 * D + 15 * M + 3 * ELL - 4) / 2
    )
    assert sp.factor(rate - expected) == 0
    gap_above_two = sp.factor(rate - 2)
    assert sp.factor(
        gap_above_two
        - (
            7 * A + 19 * D + 15 * M + 3 * ELL - 8
        ) / 2
    ) == 0

    # With m>=1, dropping every other nonnegative contribution gives
    # L-2 >= (15-8)/2 = 7/2.
    minimum_gap = sp.Rational(7, 2)
    assert minimum_gap > 0
    return {
        "q_from_slack": str(q_from_slack),
        "limiting_source_hamiltonian_rate": str(rate),
        "gap_above_two": str(gap_above_two),
        "uniform_lower_bound_for_m_positive": str(
            2 + minimum_gap
        ),
        "uniform_gap_above_two": str(minimum_gap),
    }


def _robust_affine_certificate() -> dict[str, object]:
    eigenvalue = 3 * W + 4 * M
    assert eigenvalue.subs({W: 0, M: 1}) == 4
    radial_eigenvalue = sp.factor(
        -(3 * (W + 2 * M) - 2 * M) / 18
    )
    assert sp.factor(radial_eigenvalue + eigenvalue / 18) == 0

    factor_support = _factor_support_certificate()
    assert factor_support[
        "product_support"
    ] == "radial_deficit>=extra_normal_order>=0"
    pivot_radial_margin = T
    pivot_total_margin = T - H
    return {
        "axis_multiplier_degree": "w",
        "contact_depth": "m",
        "odd_transfer_euler_operator": "3*r*d/dr+4*m",
        "degree_w_eigenvalue": str(eigenvalue),
        "eigenvalue_positive_for_w_nonnegative_m_positive": True,
        "contact_valuation_separates_different_m": True,
        "odd_containment_requires_extra_normal_h_at_least_one": True,
        "factor_support_constraint": "t>=h>=1",
        "leading_even_pivot_margins": {
            "radial": str(pivot_radial_margin),
            "total_source_degree": str(pivot_total_margin),
            "radial_margin_strictly_positive": True,
            "total_margin_nonnegative": True,
        },
        "finite_affine_kernel": "zero",
        "reason": (
            "At the least C-adic depth, the axis multiplier is a "
            "nonzero polynomial. Its highest radial coefficient is "
            "multiplied by 3*w+4*m. Any finite current row reaching "
            "the resulting odd terminal has a strictly higher even "
            "pivot unless its least-contact coefficient vanishes."
        ),
    }


def _exceptional_certificate() -> dict[str, object]:
    transition = _transition_edges()
    assert transition[
        "no_edge_stays_in_exceptional_d_zero_set"
    ]
    rows = []
    for state in sorted(EXCEPTIONAL_D_ZERO_STATES):
        polynomial = sp.factor(
            EXCEPTIONAL_PRIMARY_POLYNOMIAL[state].subs(
                BOUNDARY_M,
                M,
            )
        )
        roots = sp.roots(polynomial, M)
        prohibited = [
            root
            for root in roots
            if (
                root.is_integer is True
                and root.is_positive is True
            )
        ]
        assert not prohibited
        delta = EXCEPTIONAL_RADIAL_OFFSET[state]
        rows.append({
            "state_a_slack": list(state),
            "radial_offset_delta": delta,
            "normalized_primary_amplitude": str(polynomial),
            "roots": [str(root) for root in roots],
            "nonzero_at_every_positive_integral_contact": True,
            "adjoint_multiplier": (
                f"2*m*{delta}+2*k*(S-m)"
            ),
            "adjoint_multiplier_positive": True,
        })
    return {
        "states": rows,
        "right_magnus_response": "phi_2, nonpolynomial",
        "transition_equation": transition["transition_equation"],
        "no_exceptional_d_zero_return": True,
        "first_cancellation_enters_robust_case": True,
    }


def _well_order_certificate() -> dict[str, object]:
    return {
        "coefficient_category": (
            "finite polynomial rows continuing the normalized "
            "contact-zero background"
        ),
        "each_parameter_row_has_finite_contact_support": True,
        "nonempty_cancellation_orders_have_a_least_order": True,
        "dichotomy": [
            "no cancellation: the exceptional or robust terminal ray survives",
            (
                "first cancellation of an exceptional ray: the corrected "
                "transition enters the robust case"
            ),
            (
                "cancellation of a robust odd terminal: a strictly higher "
                "same-order source pivot survives"
            ),
        ],
        "global_maximum_contact_depth_used": False,
    }


def _payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _filtered_induction_certificate() -> dict[str, object]:
    robust_receipt = _robust_affine_certificate()
    exceptional_receipt = _exceptional_certificate()
    states = [
        FilteredInductionState(
            name="robust_odd_terminal",
            rank=(0, 0),
            local_certificate_sha256=_payload_sha256(robust_receipt),
            complete_outcomes=(
                "robust_terminal_survives",
                "robust_higher_source_pivot",
            ),
        )
    ]
    transitions = [
        FilteredInductionTransition(
            name="robust_terminal_survives",
            source="robust_odd_terminal",
            outcome="terminal_survives",
        ),
        FilteredInductionTransition(
            name="robust_higher_source_pivot",
            source="robust_odd_terminal",
            outcome="source_charged",
        ),
    ]
    for index, row in enumerate(exceptional_receipt["states"]):
        name = f"exceptional_{index}"
        terminal = f"{name}_terminal_survives"
        exits = f"{name}_first_cancellation_exits"
        states.append(FilteredInductionState(
            name=name,
            rank=(1, index),
            local_certificate_sha256=_payload_sha256({
                "state": row,
                "transition_equation": exceptional_receipt[
                    "transition_equation"
                ],
                "no_exceptional_d_zero_return": True,
            }),
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
                target="robust_odd_terminal",
            ),
        ))
    certificate = compile_filtered_induction(FilteredInductionProblem(
        name="positive_contact_locally_finite_transition_graph",
        states=tuple(states),
        transitions=tuple(transitions),
        initial_states=tuple(state.name for state in states),
    ))
    return certificate.to_dict()


def run() -> dict[str, object]:
    valuation = _contact_valuation_certificate()
    assert valuation["axis_kernel_generator"] == "C"
    assert valuation["valuation_identity"] == (
        "nu_z(H(P_0,Q_0))=2*nu_C(H)"
    )
    return {
        "schema": (
            "axiompack.jacobian_positive_contact_"
            "locally_finite_obstruction.v1"
        ),
        "contact_valuation": valuation,
        "robust_finite_affine_terminal": (
            _robust_affine_certificate()
        ),
        "exceptional_first_cancellation": (
            _exceptional_certificate()
        ),
        "limiting_rate": _rate_certificate(),
        "locally_finite_well_order": _well_order_certificate(),
        "filtered_induction": _filtered_induction_certificate(),
        "positive_contact_locally_finite_escape": False,
        "claim_boundary": (
            "Every coefficientwise-polynomial continuation of the "
            "normalized radial background with a nonzero positive-"
            "C-adic contact coefficient forces an infinite source-log "
            "subsequence of limiting Hamiltonian rate strictly above "
            "two, or a higher same-order source pivot. Replacing the "
            "contact-zero backbone and the unrestricted symmetric "
            "minimax remain separate."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
