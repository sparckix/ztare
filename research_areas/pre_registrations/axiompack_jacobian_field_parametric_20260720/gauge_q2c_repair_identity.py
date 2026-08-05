#!/usr/bin/env python3
"""Exact identity audit for the proposed ``-Q^2*C/2`` repair.

The delayed ``Q^2*C`` prefix is an order-one target velocity.  Its target
logarithm is therefore ``Q^2*C/2`` at cost two.  The proposed negative
cost-two logarithm has forward-``dexp`` velocity ``-Q^2*C`` at order one.
They cancel as the same target-connection object, so a complete coupled
replay must return to the no-prefix background at every order.  A finite
radial-staircase replay stresses the identity through both side conventions.
"""

from __future__ import annotations

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

from gauge_cone_q2c_terminal_recurrence import L_THREE, L_TWO  # noqa: E402
from gauge_cone_radial_triangular_staircase import run as staircase  # noqa: E402
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _bracket,
    _ops,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_q2c_contact_zero_product_grade import _source_data  # noqa: E402
from gauge_q2c_backbone_resonance import (  # noqa: E402
    _complete_lift_columns,
    _fixed_cost_cokernel,
)
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


Exponent = tuple[int, int]
Sparse = dict[Exponent, sp.Expr]


def _scaled(value: Sparse, scalar: sp.Expr) -> Sparse:
    return {
        exponent: sp.factor(scalar * coefficient)
        for exponent, coefficient in value.items()
        if coefficient != 0
    }


def _row_observables(result: dict[str, object]) -> list[dict[str, object]]:
    fields = (
        "negative_normal_terms",
        "remaining_radial_terms",
        "maximum_hamiltonian_degree",
        "instantaneous_maximum_hamiltonian_degree",
        "maximum_r_degree_by_normal_order",
        "top_terms",
    )
    return [
        {field: row[field] for field in fields}
        for row in result["rows"]
    ]


def run(maximum_target_order: int = 5) -> dict[str, object]:
    if maximum_target_order < 3:
        raise ValueError("the full-replay stress requires three rows")

    data = _source_data()
    u, z = data["symbols"]
    p, q = data["target_symbols"]
    p0 = data["P0"]
    q0 = data["Q0"]
    cusp = 4 * p**3 - p**2 - 18 * p * q + 27 * q**2 + 4 * q
    q2c = sp.expand(q**2 * cusp)
    q2c_sparse = _to_sparse(q2c, p, q)

    prefix_velocity = [{} for _ in range(4)]
    prefix_velocity[1] = q2c_sparse
    prefix_logarithm = magnus_from_velocity(
        prefix_velocity,
        4,
        _ops(0),
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert prefix_logarithm[1] == {}
    assert prefix_logarithm[2] == _scaled(q2c_sparse, sp.Rational(1, 2))
    assert prefix_logarithm[3] == {}

    repair_logarithm = [{} for _ in range(5)]
    repair_logarithm[2] = _scaled(q2c_sparse, -sp.Rational(1, 2))
    repair_velocity = velocity_from_magnus(
        repair_logarithm,
        4,
        _ops(0),
        VelocityPlacement.LEFT_MULTIPLY,
    )
    assert repair_velocity[0] == {}
    assert repair_velocity[1] == _scaled(q2c_sparse, -1)
    assert repair_velocity[2] == {}
    assert repair_velocity[3] == {}
    assert {
        exponent: sp.factor(
            prefix_velocity[1].get(exponent, 0)
            + repair_velocity[1].get(exponent, 0)
        )
        for exponent in set(prefix_velocity[1]) | set(repair_velocity[1])
        if sp.factor(
            prefix_velocity[1].get(exponent, 0)
            + repair_velocity[1].get(exponent, 0)
        ) != 0
    } == {}

    l_two_expression = sum(
        coefficient * u**exponent[0] * z**exponent[1]
        for exponent, coefficient in L_TWO.items()
    )
    assert sp.expand(
        l_two_expression
        - 8 * sp.Rational(1, 2) * q2c.subs({p: p0, q: q0})
    ) == 0

    common = {
        "maximum_target_order": maximum_target_order,
        "cancel_second_normal": True,
        "verify_roundtrips": True,
        "compute_logarithms": True,
        "normalization_objective": "logarithm",
    }
    baseline = staircase(**common)
    amplitude = sp.symbols("lambda")
    cancelled = staircase(
        **common,
        # Put both members of the inverse pair through the same
        # pre-normalization interface.  The dedicated delayed-prefix hook
        # intentionally runs after row normalization and therefore cannot
        # represent a simultaneous prefix/inverse-prefix comparison.
        prescribed_target_terms=[
            (1, 3, 2, 4 * amplitude),
            (1, 2, 2, -amplitude),
            (1, 1, 3, -18 * amplitude),
            (1, 0, 4, 27 * amplitude),
            (1, 0, 3, 4 * amplitude),
            # Twice the repair logarithm is its order-one velocity:
            # -lambda*Q^2*C.
            (1, 2, 2, amplitude),
            (1, 3, 2, -4 * amplitude),
            (1, 0, 3, -4 * amplitude),
            (1, 1, 3, 18 * amplitude),
            (1, 0, 4, -27 * amplitude),
        ],
    )
    compared_fields = (
        "source_logarithmic_hamiltonian_degrees",
        "source_logarithmic_top_terms",
        "source_logarithmic_normal_leading_terms",
        "target_logarithmic_hamiltonian_degrees",
        "target_logarithmic_top_terms",
        "target_logarithmic_rate_bound",
    )
    assert all(cancelled[field] == baseline[field] for field in compared_fields)
    assert _row_observables(cancelled) == _row_observables(baseline)
    assert cancelled["source_forward_dexp_roundtrip"]
    assert cancelled["target_forward_dexp_roundtrip"]

    # Negative-control regression: freezing L3 after changing only L2
    # manufactures a strong quotient, even though L3 vanishes in the
    # complete coupled replay above.
    frozen_l3_response = _bracket(_scaled(L_TWO, -1), L_THREE, 2)
    assert len(frozen_l3_response) == 26
    frozen_training = _fixed_cost_cokernel(
        name="q2c_invalid_frozen_l3_response_weight_24",
        columns=_complete_lift_columns(
            24,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        ),
        distinguished=frozen_l3_response,
    )
    frozen_heldout = _fixed_cost_cokernel(
        name="q2c_invalid_frozen_l3_response_weight_30",
        columns=_complete_lift_columns(
            30,
            p=p,
            q=q,
            p0=p0,
            q0=q0,
            u=u,
            z=z,
        ),
        distinguished=frozen_l3_response,
    )
    assert frozen_training["distinguished_survives"]
    assert frozen_training["witness_by_codomain_basis"] == (
        frozen_heldout["witness_by_codomain_basis"]
    )
    frozen_witness = {
        row["basis"]: row["coefficient"]
        for row in frozen_training["witness_by_codomain_basis"]
    }
    assert frozen_witness["u6z12"] == "6144/665"
    assert frozen_witness["u7z12"] == "-1024/665"
    assert max(
        int(name.split("z", 1)[1]) for name in frozen_witness
    ) <= 12

    return {
        "schema": "axiompack.jacobian_q2c_repair_identity.v1",
        "target_identity": {
            "delayed_prefix_velocity": "lambda*s*Q^2*C",
            "delayed_prefix_logarithm": "lambda*s^2*Q^2*C/2",
            "proposed_repair_logarithm": "-lambda*s^2*Q^2*C/2",
            "repair_forward_dexp_velocity": "-lambda*s*Q^2*C",
            "combined_target_velocity_zero": True,
            "combined_target_group_is_identity_relative_to_background": True,
        },
        "source_identity": {
            "L2_equals_8_pullback_of_Q2C_over_2": True,
            "complete_coupled_repair_returns_no_prefix_background": True,
            "cost_three_residual_after_complete_repair": False,
        },
        "finite_full_replay_stress": {
            "maximum_target_order": maximum_target_order,
            "source_right_forward_dexp_roundtrip": True,
            "target_left_forward_dexp_roundtrip": True,
            "source_rows_equal_no_prefix_background": True,
            "target_rows_equal_no_prefix_background": True,
        },
        "invalid_frozen_lower_row_negative_control": {
            "formal_response": "[-L2,L3]",
            "term_count": len(frozen_l3_response),
            "survives_complete_same_cost_pullback_span": True,
            "training_weight_cap": 24,
            "heldout_weight_cap": 30,
            "heldout_witness_matches": True,
            "witness_maximum_z_exponent": 12,
            "top_pairing": (
                "(6144/665)*[u^6*z^12] - "
                "(1024/665)*[u^7*z^12]"
            ),
            "interpretation": (
                "A strong exact quotient can be manufactured by freezing "
                "L3 after changing L2. It is a regression fixture for "
                "lower-row transport, not a coupled obstruction."
            ),
        },
        "claim_boundary": (
            "The exact -Q^2*C/2 term is the negative logarithm of the "
            "same delayed Q^2*C connection coefficient. It removes that "
            "least positive-contact prefix rather than transporting a "
            "surviving cost-three quotient. This identity does not decide "
            "the arbitrary contact-zero backbone or the next nonzero "
            "positive-contact coefficient."
        ),
        "next_residual": (
            "Classify the least nonzero positive-contact coefficient over "
            "an arbitrary contact-zero moving backbone, without treating "
            "its own negative logarithm as an independent later control."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
