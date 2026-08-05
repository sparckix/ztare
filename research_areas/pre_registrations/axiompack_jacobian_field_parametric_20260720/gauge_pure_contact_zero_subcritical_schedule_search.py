#!/usr/bin/env python3
"""Exact normal-two/normal-three quotient and ambient schedule diagnostic.

The finite rows are diagnostic only.  The all-index part of this replay is
the compatibility identity for a target correction with zero radial
restriction.  Such a correction is a multiple of the cusp polynomial C;
its source normal-two and normal-three coefficients obey one differential
identity, so they cannot be prescribed independently.

The imported radial staircase selects from the larger cone and is retained
only as an ambient diagnostic.  It is not used as the pure quotient section;
the companion critical recurrence owns that parity-normalized sequence.
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
SRC_ROOT = HERE.parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_cone_radial_triangular_staircase import run as staircase_run  # noqa: E402
from gauge_controlled_global_magnus_hamiltonian import (  # noqa: E402
    _ops,
    _source_velocity,
)
from gauge_p2q_source_newton_modules import _to_sparse  # noqa: E402
from gauge_cone_q3c_finite_terminal_log import run as q3c_prefix_run  # noqa: E402
from gauge_pure_contact_zero_delta_critical_recurrence import (  # noqa: E402
    _critical_recurrence,
)
from gauge_regular_singular_connection import source_only_connection  # noqa: E402
from ztare.common.formal_lie_series import (  # noqa: E402
    VelocityPlacement,
    magnus_from_velocity,
    velocity_from_magnus,
)


def _series_coefficients(
    expression: sp.Expr,
    parameter: sp.Symbol,
    maximum_order: int,
) -> list[sp.Expr]:
    series = sp.series(
        expression, parameter, 0, maximum_order + 1
    ).removeO().expand()
    return [series.coeff(parameter, order) for order in range(maximum_order + 1)]


def _moving_normal_layer(
    sparse: dict[tuple[int, int], sp.Expr],
    normal_order: int,
    radial: sp.Symbol,
) -> sp.Expr:
    """Convert u^a z^b with b-a=j to the moving r^a z^j layer."""

    return sp.expand(sum(
        (
            coefficient * radial**u_exponent
            for (u_exponent, z_exponent), coefficient in sparse.items()
            if z_exponent - u_exponent == normal_order
        ),
        sp.Integer(0),
    ))


def _reconstruct_source_logarithm(
    maximum_target_order: int,
    target_terms: list[dict[str, object]],
) -> tuple[
    list[dict[tuple[int, int], sp.Expr]],
    list[dict[tuple[int, int], sp.Expr]],
]:
    """Rebuild the fixed-chart source velocity and typed right logarithm."""

    maximum_cost = maximum_target_order + 1
    data = source_only_connection()
    base_velocity, (_source_s, v, z), _p3, _pq = _source_velocity(
        maximum_cost, data
    )
    parameter, family_v, family_t, _unused = data["symbols"]
    family_p, family_q = data["family"]
    u = sp.symbols("u")
    fixed_substitution = {
        family_v: u - 1,
        family_t: (z - 2 + 3 * (u - 1)) / 2,
    }
    p = sp.factor(family_p.subs(fixed_substitution))
    q = sp.factor(family_q.subs(fixed_substitution))
    base_expressions = [
        sp.expand(sum(
            (
                coefficient * v**exponent[0] * z**exponent[1]
                for exponent, coefficient in value.items()
            ),
            sp.Integer(0),
        ).subs(v, u - 1))
        for value in base_velocity
    ]
    p_coefficients = _series_coefficients(
        p, parameter, maximum_target_order
    )
    q_coefficients = _series_coefficients(
        q, parameter, maximum_target_order
    )
    monomial_cache: dict[tuple[int, int], list[sp.Expr]] = {
        (0, 0): [
            sp.Integer(1),
            *(sp.Integer(0) for _ in range(maximum_target_order)),
        ]
    }

    def monomial_coefficients(
        p_exponent: int, q_exponent: int
    ) -> list[sp.Expr]:
        key = (p_exponent, q_exponent)
        if key not in monomial_cache:
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
            monomial_cache[key] = [
                sp.expand(sum(
                    (
                        parent[index] * factor[order - index]
                        for index in range(order + 1)
                    ),
                    sp.Integer(0),
                ))
                for order in range(maximum_target_order + 1)
            ]
        return monomial_cache[key]

    velocity = [{}]
    for order in range(1, maximum_target_order + 1):
        value = base_expressions[order]
        for term in target_terms:
            row = int(term["target_order"])
            if row > order:
                continue
            p_exponent = int(term["p_exponent"])
            q_exponent = int(term["q_exponent"])
            coefficient = sp.Rational(str(term["coefficient"]))
            value = sp.expand(
                value
                + 8
                * coefficient
                * monomial_coefficients(p_exponent, q_exponent)[order - row]
            )
        velocity.append(_to_sparse(value, u, z))
    logarithm = magnus_from_velocity(
        velocity,
        maximum_cost,
        _ops(2),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    replay = velocity_from_magnus(
        logarithm,
        maximum_cost,
        _ops(2),
        VelocityPlacement.RIGHT_MULTIPLY,
    )
    assert replay[:maximum_cost] == velocity
    return velocity, logarithm


def _cone_multiplier(weight: int) -> tuple[int, int] | None:
    """A closed-form cone multiplier for every weight at least eleven."""

    if weight < 11:
        return None
    residue = weight % 3
    p_exponent = {0: 0, 1: 2, 2: 1}[residue]
    q_exponent = (weight - 2 * p_exponent) // 3
    assert 2 * p_exponent + 3 * q_exponent == weight
    assert p_exponent + 3 <= 2 * q_exponent
    return p_exponent, q_exponent


def run(maximum_target_order: int = 6) -> dict[str, object]:
    if maximum_target_order < 6:
        raise ValueError("the compatibility probe requires rows through six")

    # Work at s=0 in the moving (r,z) chart.  These identities are exact,
    # not a top-shell truncation.
    r, z = sp.symbols("r z")
    target_p, target_q = sp.symbols("P Q")
    tangent = 2 - 3 * r
    p0 = -sp.Rational(3, 4) * r**2 + r + z / 2
    q0 = -r**3 / 4 + r**2 / 4 + r * z / 4
    cusp = (
        4 * target_p**3
        - target_p**2
        - 18 * target_p * target_q
        + 27 * target_q**2
        + 4 * target_q
    )
    pulled_cusp = sp.factor(cusp.subs({target_p: p0, target_q: q0}))
    expected_cusp = -z**2 * (tangent**2 - 8 * z) / 16
    assert sp.factor(pulled_cusp - expected_cusp) == 0

    # Verify the normal compatibility on a generic finite target polynomial.
    generic_coefficients = sp.symbols("h00:9")
    generic_target = sum(
        generic_coefficients[index] * target_p**p_exponent * target_q**q_exponent
        for index, (p_exponent, q_exponent) in enumerate((
            (0, 0),
            (1, 0),
            (0, 1),
            (2, 0),
            (1, 1),
            (0, 2),
            (3, 0),
            (2, 1),
            (1, 2),
        ))
    )
    pulled_kernel = sp.expand(
        pulled_cusp
        * generic_target.subs({target_p: p0, target_q: q0})
    )
    kernel_normal_two = sp.expand(pulled_kernel.coeff(z, 2))
    kernel_normal_three = sp.expand(pulled_kernel.coeff(z, 3))
    compatibility = sp.factor(
        tangent**2 * kernel_normal_three
        - tangent * sp.diff(kernel_normal_two, r)
        + 2 * kernel_normal_two
    )
    assert compatibility == 0

    checked_radial_symbols = []
    for q_exponent in range(1, 9):
        for p_exponent in range(0, 2 * q_exponent + 1):
            if (p_exponent, q_exponent) == (0, 1):
                continue
            weight = 2 * p_exponent + 3 * q_exponent
            pulled = sp.expand(p0**p_exponent * q0**q_exponent)
            radial = sp.expand(pulled.coeff(z, 0))
            normal_two = sp.expand(pulled.coeff(z, 2))
            normal_three = sp.expand(pulled.coeff(z, 3))
            quotient = sp.expand(
                tangent**2 * normal_three
                - tangent * sp.diff(normal_two, r)
                + 2 * normal_two
            )
            radial_leader = sp.LC(sp.Poly(radial, r))
            quotient_leader = sp.LC(sp.Poly(quotient, r))
            expected_leader = sp.factor(
                radial_leader * weight * (weight - 2) * (weight - 3) / 9
            )
            assert sp.factor(quotient_leader - expected_leader) == 0
            assert sp.degree(quotient, r) == weight - 4
            checked_radial_symbols.append((p_exponent, q_exponent))

    staircase = staircase_run(
        maximum_target_order=maximum_target_order,
        cancel_second_normal=False,
        verify_roundtrips=False,
        compute_logarithms=False,
        normalization_objective="logarithm",
    )
    velocity, logarithm = _reconstruct_source_logarithm(
        maximum_target_order,
        staircase["all_target_terms"],
    )
    finite_rows = []
    for target_order in range(1, maximum_target_order + 1):
        logarithmic_order = target_order + 1
        radial_row = staircase["rows"][target_order - 1]
        highest_control = radial_row["target_terms"][0]
        highest_weight = int(highest_control["weight"])
        highest_p = int(highest_control["p_exponent"])
        highest_q = int(highest_control["q_exponent"])
        highest_coefficient = sp.Rational(str(highest_control["coefficient"]))
        radial_leader = sp.factor(
            sp.Rational(8, logarithmic_order)
            * highest_coefficient
            * (-sp.Rational(3, 4)) ** highest_p
            * (-sp.Rational(1, 4)) ** highest_q
        )
        current_control_quotient_leader = sp.factor(
            radial_leader
            * highest_weight
            * (highest_weight - 2)
            * (highest_weight - 3)
            / 9
        )
        coefficient = logarithm[logarithmic_order]
        normal_two = _moving_normal_layer(coefficient, 2, r)
        normal_three = _moving_normal_layer(coefficient, 3, r)
        obstruction = sp.factor(
            tangent**2 * normal_three
            - tangent * sp.diff(normal_two, r)
            + 2 * normal_two
        )
        obstruction_degree = (
            None if obstruction == 0 else int(sp.degree(obstruction, r))
        )
        obstruction_leader = (
            None
            if obstruction == 0
            else sp.factor(sp.LC(sp.Poly(obstruction, r)))
        )
        finite_rows.append({
            "target_order": target_order,
            "logarithmic_order": logarithmic_order,
            "highest_radial_control_weight": highest_weight,
            "highest_radial_control_coefficient": str(highest_coefficient),
            "current_control_compatibility_leader": str(
                current_control_quotient_leader
            ),
            "normal_two_degree": (
                None if normal_two == 0 else int(sp.degree(normal_two, r))
            ),
            "normal_three_degree": (
                None if normal_three == 0 else int(sp.degree(normal_three, r))
            ),
            "compatibility_obstruction_degree": obstruction_degree,
            "compatibility_obstruction_leader": (
                None if obstruction_leader is None else str(obstruction_leader)
            ),
            "implied_source_vector_degree": (
                None
                if obstruction_degree is None
                else 2 * obstruction_degree - 4
            ),
        })

    pure_parity = _critical_recurrence(
        maximum_target_order,
        guess_rational_generating_function=False,
    )

    conductor_check = {
        str(weight): list(_cone_multiplier(weight) or ())
        for weight in range(11, 32)
    }
    assert all(conductor_check[str(weight)] for weight in range(11, 32))
    prefix = q3c_prefix_run(maximum_cost=15)
    assert prefix["finite_terminal_logarithm"]["higher_terminal_rows"] == "0"
    assert all(
        row["coefficient"] != "0"
        for row in prefix["terminal_velocity_rows"]
    )

    return {
        "schema": "axiompack.jacobian_pure_contact_zero_subcritical_search.v2",
        "moving_base_pullback": {
            "P0": str(p0),
            "Q0": str(q0),
            "C_pullback": str(pulled_cusp),
            "tangent_factor": str(tangent),
        },
        "all_index_kernel_compatibility": {
            "identity": "L^2*N3 - L*d_r(N2) + 2*N2 = 0",
            "scope": "every polynomial correction C(P,Q)*H(P,Q)",
            "symbolic_generic_polynomial_check": True,
            "cusp_ideal_principal": True,
        },
        "radial_to_compatibility_symbol": {
            "formula": (
                "[r^(w-4)] Delta(K(P0,Q0)) = "
                "w*(w-2)*(w-3)/9 times [r^w] K(P0,Q0)"
            ),
            "nonzero_range": "every cone weight w>=5",
            "derivation": (
                "P0_top=(-3/4)r^2*(1-(2/3)z/r^2), "
                "Q0_top=(-1/4)r^3*(1-z/r^2)"
            ),
            "finite_symbol_crosscheck_count": len(checked_radial_symbols),
        },
        "cone_multiplier_conductor": {
            "statement": "every weight w>=11 has p+3<=2q and 2p+3q=w",
            "closed_form": (
                "p=0,2,1 for w mod 3 = 0,1,2; q=(w-2p)/3"
            ),
            "sample": conductor_check,
        },
        "ambient_full_cone_diagnostic_rows": finite_rows,
        "ambient_rows_are_not_pure_parity_after_row_three": True,
        "pure_parity_diagnostic_rows": pure_parity["rows"],
        "finite_supercritical_prefix_audit": {
            "prefix": prefix["prefix"],
            "source_logarithm_nonzero_costs_on_terminal_ray": [2, 3],
            "source_logarithm_higher_terminal_rows": 0,
            "source_velocity_nonzero_costs": [
                row["cost"] for row in prefix["terminal_velocity_rows"]
            ],
            "typed_forward_dexp_replay": True,
            "verdict": (
                "A second noncommuting logarithm coefficient appears at "
                "cost three, but its infinite adjoint response belongs to "
                "the forward-dexp velocity and does not force logarithmic "
                "tail support. A finite-prefix cascade alone cannot exclude "
                "a below-rate-two logarithmic tail."
            ),
            "actual_staircase_scope": (
                "the existing full projection matches this finite "
                "logarithm through held-out cost nine; equality at every "
                "order is not asserted"
            ),
        },
        "source_typed_dexp_roundtrip": True,
        "source_velocity_rows": len(velocity),
        "claim_boundary": (
            "The all-index result is the normal-two/normal-three kernel "
            "compatibility and the cone-multiplier conductor. The ambient "
            "staircase rows are not representatives of the pure parity "
            "quotient after row three. The separately reported parity rows "
            "remain finite diagnostics; proving their nonvanishing on an "
            "unbounded set requires the algebraic connection and a finite-"
            "prefix inverse-dexp theorem."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
