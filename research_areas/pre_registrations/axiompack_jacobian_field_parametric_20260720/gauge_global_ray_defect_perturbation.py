#!/usr/bin/env python3
"""Exact order-three target-perturbation test for the global Magnus ray.

Adding ``s**3*M(P,Q)`` to the target Hamiltonian changes the cost-four
source Hamiltonian by ``8*M(P_0,Q_0)`` in the translated ``(u,z)`` chart.
The factor eight follows from

    dP_0 wedge dQ_0 = -(z**2/8) du wedge dz.

The Bernoulli-tail defect is a linear coefficient functional of that source
Hamiltonian.  Only nine monomials can enter it.  The seed z-adic orders
``ord_z(P_0)=1`` and ``ord_z(Q_0)=2`` reduce the unrestricted polynomial
target check to finitely many monomials.
"""

from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_controlled_global_magnus_all_order import (  # noqa: E402
    EXPECTED_TRANSLATED_VELOCITY,
)
from gauge_controlled_global_magnus_graded_ray import (  # noqa: E402
    TARGET_GRADE,
    _grade,
    _project,
)
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    SparseHamiltonian,
    _bracket,
    _scale,
)
from gauge_regular_singular_connection import (  # noqa: E402
    source_only_connection,
)


def _defect_slope(
    source_hamiltonian: SparseHamiltonian,
) -> sp.Expr:
    projected = _project(
        source_hamiltonian, 4, TARGET_GRADE
    )
    terminal = {
        exponent: coefficient
        for exponent, coefficient in projected.items()
        if _grade(exponent, 4) == TARGET_GRADE
    }
    nonterminal = {
        exponent: coefficient
        for exponent, coefficient in projected.items()
        if _grade(exponent, 4) != TARGET_GRADE
    }
    l_two = _scale(
        EXPECTED_TRANSLATED_VELOCITY[2],
        Fraction(1, 2),
    )
    core = _project(
        _bracket(
            l_two,
            _scale(nonterminal, Fraction(1, 4)),
            2,
        ),
        6,
        TARGET_GRADE,
    )
    e_one_coefficient = sp.Rational(3, 128)
    direct = terminal.get((7, 8), sp.Integer(0))
    normalized_seed = sp.factor(
        2
        * core.get((13, 12), sp.Integer(0))
        / e_one_coefficient
    )
    return sp.factor(direct + 2 * normalized_seed)


def _to_sparse(
    value: sp.Expr,
    u: sp.Symbol,
    z: sp.Symbol,
) -> SparseHamiltonian:
    return {
        exponent: sp.factor(coefficient)
        for exponent, coefficient in sp.Poly(
            sp.expand(value), u, z
        ).terms()
        if coefficient != 0
    }


def run() -> dict[str, object]:
    data = source_only_connection()
    s, v, t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u, z = sp.symbols("u z")
    seed_substitution = {
        s: 0,
        v: u - 1,
        t: (z - 2 + 3 * (u - 1)) / 2,
    }
    seed_p = sp.factor(family_p.subs(seed_substitution))
    seed_q = sp.factor(family_q.subs(seed_substitution))
    assert seed_p == -z * (3 * u**2 * z - 4 * u - 2) / 4
    assert seed_q == -u * z**2 * (u**2 * z - u - 1) / 4
    seed_jacobian = sp.factor(
        sp.det(
            sp.Matrix([
                [sp.diff(seed_p, u), sp.diff(seed_p, z)],
                [sp.diff(seed_q, u), sp.diff(seed_q, z)],
            ])
        )
    )
    assert seed_jacobian == -z**2 / 8

    # The defect uses z exponents at most eleven.  Since P_0 has z-order
    # one and Q_0 has z-order two, a monomial P^a Q^b with a+2b>11
    # cannot contribute.  The remaining finite set is exhaustive for an
    # arbitrary polynomial target Hamiltonian.
    maximum_defect_z_exponent = 11
    rows = []
    first_nonzero = None
    for first_power in range(maximum_defect_z_exponent + 1):
        for second_power in range(
            maximum_defect_z_exponent // 2 + 1
        ):
            seed_z_order = first_power + 2 * second_power
            if seed_z_order > maximum_defect_z_exponent:
                continue
            perturbation = sp.expand(
                8
                * seed_p**first_power
                * seed_q**second_power
            )
            slope = _defect_slope(
                _to_sparse(perturbation, u, z)
            )
            if first_nonzero is None and slope != 0:
                first_nonzero = (
                    first_power,
                    second_power,
                    slope,
                )
            rows.append({
                "p_power": first_power,
                "q_power": second_power,
                "seed_z_order": seed_z_order,
                "defect_slope": str(slope),
            })
    assert first_nonzero is None

    base_direct = sp.Rational(7, 3072)
    base_normalized_seed = -sp.Rational(1, 1536)
    base_defect = sp.factor(
        base_direct + 2 * base_normalized_seed
    )
    assert base_defect == sp.Rational(1, 1024)

    return {
        "schema": (
            "axiompack.jacobian_global_ray_"
            "defect_perturbation.v1"
        ),
        "seed_chart": {
            "P_0": str(seed_p),
            "Q_0": str(seed_q),
            "jacobian_dP_wedge_dQ": str(seed_jacobian),
            "source_hamiltonian_for_plus_s3_M": "8*M(P_0,Q_0)",
        },
        "defect": {
            "definition": "Delta = H + 2*N",
            "base_direct_H": str(base_direct),
            "base_normalized_seed_N": str(
                base_normalized_seed
            ),
            "base_value": str(base_defect),
        },
        "exhaustion": {
            "maximum_defect_z_exponent": (
                maximum_defect_z_exponent
            ),
            "seed_z_order": "a+2*b for P^a*Q^b",
            "checked_monomial_count": len(rows),
            "first_nonzero_slope": None,
            "all_polynomial_order_three_target_perturbations_annihilated": (
                True
            ),
            "rows": rows,
        },
        "claim_boundary": (
            "The Bernoulli-ray scalar is invariant under an arbitrary "
            "polynomial coefficient added as s^3*M(P,Q) to this fixed "
            "connection. Earlier target coefficients can change L_2 or "
            "L_3, and later coefficients can inject terminal velocity "
            "directly, so this is not an unrestricted gauge-minimax "
            "statement."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
