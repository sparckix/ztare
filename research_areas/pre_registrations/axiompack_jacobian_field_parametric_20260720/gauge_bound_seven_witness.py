#!/usr/bin/env python3
"""Rational normalized contact prefix with slope-two continuations."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import sympy as sp


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_bound_six_extension import build_through_six  # noqa: E402
from gauge_bound_six_witness import _solve_new_order  # noqa: E402
from gauge_minimized_fifth_obstruction import (  # noqa: E402
    _source_degree,
    _target_lift_ideals,
)
from gauge_minimized_fourth_jet import _family_jets  # noqa: E402
from gauge_minimized_recursive_prefix import _composed_series  # noqa: E402
from gauge_minimized_third_jet import _hamiltonian_field  # noqa: E402


def _sha(value: sp.Expr) -> str:
    return hashlib.sha256(
        str(sp.expand(value)).encode("utf-8")
    ).hexdigest()


def run(
    *,
    maximum_order: int = 7,
    include_internal: bool = False,
) -> dict[str, object]:
    if maximum_order < 7:
        raise ValueError("the carried prefix begins at order seven")
    bound = 9
    family = build_through_six(bound)
    data = _family_jets(maximum_order)
    v, t = data["symbols"]
    p, q = family["symbols"]["target"]
    parameters = family["complete_parameters_through_six"]
    by_name = {str(parameter): parameter for parameter in parameters}
    required_names = {"b3", "b4", "c3", "c4", "c5"}
    if not required_names <= set(by_name):
        raise ValueError(
            f"unexpected through-six coordinates: {tuple(by_name)}"
        )

    b3_value = -sp.Rational(102613, 1841940)
    parameter_values = {
        parameter: sp.Integer(0) for parameter in parameters
    }
    parameter_values[by_name["b3"]] = b3_value
    parameter_values[by_name["b4"]] = sp.Integer(0)
    parameter_values[by_name["c3"]] = sp.factor(
        sp.Rational(12368730247899, 677698939008) * b3_value
    )
    parameter_values[by_name["c4"]] = sp.factor(
        sp.Rational(401490813861, 677698939008) * b3_value
    )
    parameter_values[by_name["c5"]] = sp.Integer(0)

    # The four exact quotient conditions returned by the complete
    # degree-nine obstruction family.
    a5 = parameter_values.get(by_name.get("a5"), sp.Integer(0))
    b0 = parameter_values.get(by_name.get("b0"), sp.Integer(0))
    b1 = parameter_values.get(by_name.get("b1"), sp.Integer(0))
    b2 = parameter_values.get(by_name.get("b2"), sp.Integer(0))
    b3 = parameter_values[by_name["b3"]]
    b4 = parameter_values[by_name["b4"]]
    c0 = parameter_values.get(by_name.get("c0"), sp.Integer(0))
    c2 = parameter_values.get(by_name.get("c2"), sp.Integer(0))
    c3 = parameter_values[by_name["c3"]]
    c4 = parameter_values[by_name["c4"]]
    c5 = parameter_values[by_name["c5"]]
    obstruction_numerators = [
        1841940 * b3 - 22103280 * b4 + 102613,
        c5,
        (
            1372654101000 * a5
            - 218130610880 * b0
            + 70593639480 * b1
            - 275651354160 * b2
            + 401490813861 * b3
            - 6665219291772 * b4
            - 75299882112 * c0
            - 338849469504 * c2
            - 677698939008 * c4
        ),
        (
            16529369955280 * a5
            - 2617567330560 * b0
            + 847123673760 * b1
            - 3307816249920 * b2
            + 12368730247899 * b3
            - 159037081525188 * b4
            - 903598585344 * c0
            - 4066193634048 * c2
            - 677698939008 * c3
        ),
    ]
    assert all(sp.factor(item) == 0 for item in obstruction_numerators)

    target_fields = {
        order: tuple(
            sp.expand(item.subs(parameter_values))
            for item in field
        )
        for order, field in family["target_fields"].items()
    }
    source_fields = {
        order: tuple(
            sp.expand(item.subs(parameter_values))
            for item in field
        )
        for order, field in family["source_fields"].items()
    }
    through_six = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=7,
    )
    for order in range(7):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                through_six[order], actual, strict=True
            )
        )
    residual = (
        sp.expand(
            data["P"][7]
            - sp.factorial(7) * through_six[7][0]
        ),
        sp.expand(
            data["Q"][7]
            - sp.factorial(7) * through_six[7][1]
        ),
    )
    y7, k7, solve_receipt = _solve_new_order(
        order=7,
        bound=bound,
        residual=residual,
        family=family,
        data=data,
        v=v,
        t=t,
        p=p,
        q=q,
    )
    target_fields[7] = _hamiltonian_field(k7, p, q)
    source_fields[7] = y7
    continuation_receipts: dict[str, object] = {}
    for order in range(8, maximum_order + 1):
        predicted = _composed_series(
            target_fields=target_fields,
            source_fields=source_fields,
            p=p,
            q=q,
            v=v,
            t=t,
            p0=data["P"][0],
            q0=data["Q"][0],
            maximum_order=order,
        )
        residual = (
            sp.expand(
                data["P"][order]
                - sp.factorial(order) * predicted[order][0]
            ),
            sp.expand(
                data["Q"][order]
                - sp.factorial(order) * predicted[order][1]
            ),
        )
        source, hamiltonian, receipt = _solve_new_order(
            order=order,
            bound=2 * order + 1,
            residual=residual,
            family=family,
            data=data,
            v=v,
            t=t,
            p=p,
            q=q,
        )
        source_fields[order] = source
        target_fields[order] = _hamiltonian_field(
            hamiltonian, p, q
        )
        continuation_receipts[str(order)] = receipt

    completed = _composed_series(
        target_fields=target_fields,
        source_fields=source_fields,
        p=p,
        q=q,
        v=v,
        t=t,
        p0=data["P"][0],
        q0=data["Q"][0],
        maximum_order=maximum_order,
    )
    for order in range(maximum_order + 1):
        actual = (
            data["P"][order] / sp.factorial(order),
            data["Q"][order] / sp.factorial(order),
        )
        assert all(
            sp.expand(left - right) == 0
            for left, right in zip(
                completed[order], actual, strict=True
            )
        )

    target_lift_checks = {
        str(order): _target_lift_ideals(field, p, q)
        for order, field in target_fields.items()
    }
    assert all(target_lift_checks.values())
    if include_internal:
        return {
            "family": family,
            "data": data,
            "target_fields": target_fields,
            "source_fields": source_fields,
            "seventh_solve": solve_receipt,
            "continuation_receipts": continuation_receipts,
        }
    return {
        "schema": "axiompack.jacobian_fixed_bound_seven_witness.v1",
        "maximum_order": maximum_order,
        "bound": bound,
        "nonzero_lower_coordinate_values": {
            str(parameter): str(value)
            for parameter, value in parameter_values.items()
            if value != 0
        },
        "seventh_solve": solve_receipt,
        "slope_two_continuation_receipts": continuation_receipts,
        "source_field_degrees": {
            str(order): [
                _source_degree(item, v, t) for item in field
            ]
            for order, field in source_fields.items()
        },
        "source_field_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in source_fields.items()
        },
        "target_field_sha256": {
            str(order): [_sha(item) for item in field]
            for order, field in target_fields.items()
        },
        "target_field_degrees": {
            str(order): [
                _source_degree(item, p, q) for item in field
            ]
            for order, field in target_fields.items()
        },
        "target_three_variable_lift_ideals": target_lift_checks,
        "all_target_fields_liftable": all(
            target_lift_checks.values()
        ),
        "full_prefix_replay": True,
        "claim": (
            "a rational source prefix reaches order "
            f"{maximum_order} in the fixed first-order quotient slice; "
            "orders at least eight use source bound 2*n+1"
        ),
    }


if __name__ == "__main__":
    selected_order = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(json.dumps(
        run(maximum_order=selected_order),
        indent=2,
        sort_keys=True,
    ))
