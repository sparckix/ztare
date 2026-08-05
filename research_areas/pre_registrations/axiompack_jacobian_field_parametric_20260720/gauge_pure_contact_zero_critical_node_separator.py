#!/usr/bin/env python3
"""Finite critical-velocity obstruction from normalization-node separation.

At slope two, a target monomial of cusp weight w placed in parameter row
j=w-6 restricts radially as

    x**j Pcrit(x,0)**a Qcrit(x,0)**b
      = x**(-6) Phat(x)**a Qhat(x)**b.

Thus every finite critical target velocity has x**6 times its restriction
in QQ[Phat,Qhat].  The normalization map x -> (Phat,Qhat) identifies two
points, while the required source radial primitive separates them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredBasisVector,
    FilteredObstructionProblem,
    FilteredRelation,
    compile_fixed_grade_obstruction,
)


def run() -> dict[str, object]:
    x = sp.symbols("x")
    root = sp.sqrt(3)
    node_plus = 2 + 2 * root
    node_minus = 2 - 2 * root
    p_hat = sp.factor(x**2 * (x - 6) / 8)
    q_hat = sp.factor(x**3 * (3 * x - 16) / 64)
    assert sp.simplify(p_hat.subs(x, node_plus)) == -2
    assert sp.simplify(p_hat.subs(x, node_minus)) == -2
    assert sp.simplify(q_hat.subs(x, node_plus)) == 1
    assert sp.simplify(q_hat.subs(x, node_minus)) == 1

    required = sp.factor(
        x**7 * (56 * x**2 - 441 * x + 864) / sp.Integer(1032192)
    )
    value_plus = sp.simplify(required.subs(x, node_plus))
    value_minus = sp.simplify(required.subs(x, node_minus))
    separation = sp.factor(value_plus - value_minus)
    assert value_plus == sp.Rational(2239, 252) + sp.Rational(36, 7) * root
    assert value_minus == sp.Rational(2239, 252) - sp.Rational(36, 7) * root
    assert separation == sp.Rational(72, 7) * root

    # Coordinates are node average and the coefficient of sqrt(3) in the
    # antisymmetric node value.  Every target restriction lies on the
    # average axis; the source demand has a nonzero separator coordinate.
    problem = FilteredObstructionProblem(
        name="jacobian_critical_normalization_node_separator",
        basis=(
            FilteredBasisVector("node_average", 0),
            FilteredBasisVector("node_separator", 0),
        ),
        relations=(
            FilteredRelation(
                "finite_target_restriction",
                0,
                {"node_average": 1},
            ),
        ),
        actions=(),
        distinguished={
            "node_average": sp.Rational(2239, 252),
            "node_separator": sp.Rational(36, 7),
        },
    )
    certificate = compile_fixed_grade_obstruction(problem)
    assert certificate.distinguished_survives
    assert certificate.distinguished_pairing == "1"
    assert certificate.witness_by_basis == (("node_separator", "7/36"),)

    payload = {
        "p_hat": str(p_hat),
        "q_hat": str(q_hat),
        "node_plus": str(node_plus),
        "node_minus": str(node_minus),
        "required": str(required),
        "separation": str(separation),
        "compiler": certificate.to_dict(),
    }
    payload_digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "critical_node_separator.v1"
        ),
        "critical_normalization": {
            "P_hat": str(p_hat),
            "Q_hat": str(q_hat),
            "node_points": [str(node_plus), str(node_minus)],
            "common_node_image": ["-2", "1"],
        },
        "required_radial_primitive": {
            "x6_times_demand": str(required),
            "node_values": [str(value_plus), str(value_minus)],
            "node_separation": str(separation),
        },
        "filtered_obstruction_compiler": certificate.to_dict(),
        "certificate_sha256": payload_digest,
        "claim_boundary": (
            "No finite slope-two critical target velocity can cancel the "
            "required radial primitive, even allowing every polynomial "
            "target Hamiltonian, because finite restrictions descend to the "
            "node while the demand separates its normalization points. This "
            "is a velocity theorem. A finite target logarithm can still "
            "produce an infinite critical velocity through forward dexp."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
