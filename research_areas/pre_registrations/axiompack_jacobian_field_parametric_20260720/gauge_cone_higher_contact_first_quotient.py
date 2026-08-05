#!/usr/bin/env python3
"""First coupled quotient for prefixes ``P^a*Q^b*C^m``.

The replay uses the exact fixed-chart coefficients through parameter
order one.  At contact depth ``m`` it applies every current triangular
level ``1,C,...,C^m`` before reporting the highest surviving radial
source term.  It is a finite scan in ``m``; no all-depth contact
identity is inferred from the scan alone.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gauge_cone_discriminant_depth_scan as local  # noqa: E402


def _canonical_contact_multiplier(
    normal_radial_degree: int,
    contact_depth: int,
) -> tuple[int, int] | None:
    multiplier_weight = normal_radial_degree - 2 * contact_depth
    if multiplier_weight < 0:
        return None
    candidates = []
    for q_exponent in range(multiplier_weight // 3 + 1):
        remainder = multiplier_weight - 3 * q_exponent
        if remainder < 0 or remainder % 2:
            continue
        p_exponent = remainder // 2
        if (
            q_exponent >= 1
            and p_exponent + 3 * contact_depth
            <= 2 * q_exponent
        ):
            candidates.append((p_exponent, q_exponent))
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda pair: (sum(pair), pair[1], pair[0]),
    )


def _contact_seed(
    p_exponent: int,
    q_exponent: int,
    contact_depth: int,
    minimum_radial_degree: int,
) -> local.Sparse:
    return local._product([
        local._power(local.P_ZERO, p_exponent, 2),
        local._power(local.Q_ZERO, q_exponent, 3),
        local._power(local.C_ZERO, contact_depth, 2),
    ], minimum_radial_degree)


def _prefix_first_coefficient(
    p_exponent: int,
    q_exponent: int,
    contact_depth: int,
    minimum_radial_degree: int,
) -> local.Sparse:
    p_power = local._power(local.P_ZERO, p_exponent, 2)
    q_power = local._power(local.Q_ZERO, q_exponent, 3)
    c_power = local._power(local.C_ZERO, contact_depth, 2)
    result: local.Sparse = {}
    if p_exponent:
        result = local._add(
            result,
            local._scale(local._product([
                local._power(
                    local.P_ZERO,
                    p_exponent - 1,
                    2,
                ),
                local.P_ONE,
                q_power,
                c_power,
            ], minimum_radial_degree), p_exponent),
        )
    if q_exponent:
        result = local._add(
            result,
            local._scale(local._product([
                p_power,
                local._power(
                    local.Q_ZERO,
                    q_exponent - 1,
                    3,
                ),
                local.Q_ONE,
                c_power,
            ], minimum_radial_degree), q_exponent),
        )
    result = local._add(
        result,
        local._scale(local._product([
            p_power,
            q_power,
            local._power(
                local.C_ZERO,
                contact_depth - 1,
                2,
            ),
            local.C_ONE,
        ], minimum_radial_degree), contact_depth),
    )
    return local._scale(result, 8)


def _normalize(
    residual: local.Sparse,
    contact_depth: int,
    minimum_radial_degree: int,
) -> tuple[local.Sparse, list[dict[str, object]]]:
    result = dict(residual)
    controls = []
    for current_depth in range(contact_depth + 1):
        normal_order = 2 * current_depth
        while True:
            radial_degrees = [
                radial
                for (radial, normal), coefficient in result.items()
                if (
                    normal == normal_order
                    and coefficient != 0
                    and _canonical_contact_multiplier(
                        radial,
                        current_depth,
                    )
                    is not None
                )
            ]
            if not radial_degrees:
                break
            radial = max(radial_degrees)
            multiplier = _canonical_contact_multiplier(
                radial,
                current_depth,
            )
            assert multiplier is not None
            seed = local._scale(
                _contact_seed(
                    multiplier[0],
                    multiplier[1],
                    current_depth,
                    minimum_radial_degree,
                ),
                8,
            )
            coefficient = sp.factor(
                -result[(radial, normal_order)]
                / seed[(radial, normal_order)]
            )
            result = local._add(
                result,
                local._scale(seed, coefficient),
            )
            controls.append({
                "contact_depth": current_depth,
                "normal_radial_degree": radial,
                "multiplier_p_exponent": multiplier[0],
                "multiplier_q_exponent": multiplier[1],
                "coefficient": str(coefficient),
            })
    return local._clean(result), controls


def _one_case(
    p_exponent: int,
    q_exponent: int,
    contact_depth: int,
) -> dict[str, object]:
    if contact_depth < 1:
        raise ValueError("contact depth must be positive")
    if p_exponent + 3 * contact_depth > 2 * q_exponent:
        raise ValueError("the prefix is outside the cone")
    previous_normal_order = local.MAXIMUM_NORMAL_ORDER
    local.MAXIMUM_NORMAL_ORDER = 2 * contact_depth + 4
    try:
        baseline = (
            2 * p_exponent
            + 3 * q_exponent
            + 2 * contact_depth
        )
        minimum = max(
            0,
            baseline - local.MAXIMUM_RADIAL_DEFICIT,
        )
        residual, controls = _normalize(
            _prefix_first_coefficient(
                p_exponent,
                q_exponent,
                contact_depth,
                minimum,
            ),
            contact_depth,
            minimum,
        )
    finally:
        local.MAXIMUM_NORMAL_ORDER = previous_normal_order
    logarithm = {
        exponent: sp.factor(coefficient / 3)
        for exponent, coefficient in residual.items()
        if coefficient != 0
    }
    maximum_radial = max(
        (exponent[0] for exponent in logarithm),
        default=None,
    )
    leading_rows = [
        {
            "key_r_normal": list(exponent),
            "exponent_u_z": [
                exponent[0],
                exponent[0] + exponent[1],
            ],
            "coefficient": str(coefficient),
        }
        for exponent, coefficient in sorted(logarithm.items())
        if exponent[0] == maximum_radial
    ]
    return {
        "p_exponent": p_exponent,
        "q_exponent": q_exponent,
        "contact_depth": contact_depth,
        "quotient_vanished": not logarithm,
        "maximum_surviving_radial_degree": maximum_radial,
        "leading_rows": leading_rows,
        "current_control_count": len(controls),
        "current_controls": controls,
    }


def run(maximum_contact_depth: int = 6) -> dict[str, object]:
    if maximum_contact_depth < 2:
        raise ValueError("the scan must include C^2")
    rows = []
    for contact_depth in range(1, maximum_contact_depth + 1):
        for p_exponent in range(3):
            q_exponent = max(
                1,
                (p_exponent + 3 * contact_depth + 1) // 2,
            )
            rows.append(_one_case(
                p_exponent,
                q_exponent,
                contact_depth,
            ))

    # Known one-C and newly held-out C^2 controls.
    expected = {
        (1, 1, 4): ([13, 17], "-9/8192"),
        (2, 0, 3): ([14, 18], "243/32768"),
        (2, 0, 4): ([17, 21], "-81/32768"),
        (2, 1, 4): ([17, 21], "-81/131072"),
    }
    indexed = {
        (
            row["contact_depth"],
            row["p_exponent"],
            row["q_exponent"],
        ): row
        for row in rows
    }
    # The one-C validation uses a non-minimal stable representative.
    stable_one_c = _one_case(1, 4, 1)
    assert (
        stable_one_c["leading_rows"][0]["exponent_u_z"],
        stable_one_c["leading_rows"][0]["coefficient"],
    ) == expected[(1, 1, 4)]
    for key in ((2, 0, 3), (2, 1, 4)):
        row = indexed[key]
        assert (
            row["leading_rows"][0]["exponent_u_z"],
            row["leading_rows"][0]["coefficient"],
        ) == expected[key]
    nonminimal_c2_control = _one_case(0, 4, 2)
    assert (
        nonminimal_c2_control["leading_rows"][0]["exponent_u_z"],
        nonminimal_c2_control["leading_rows"][0]["coefficient"],
    ) == expected[(2, 0, 4)]

    return {
        "schema": (
            "axiompack.jacobian_cone_"
            "higher_contact_first_quotient.v1"
        ),
        "maximum_contact_depth": maximum_contact_depth,
        "stable_one_c_control": stable_one_c,
        "nonminimal_c2_control": nonminimal_c2_control,
        "all_current_contact_levels_enabled": True,
        "rows": rows,
        "claim_boundary": (
            "Finite exact scan of the first coupled quotient for "
            "P^a*Q^b*C^m after current normalization through C^m. "
            "No all-m transfer or Magnus nontermination is claimed."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
