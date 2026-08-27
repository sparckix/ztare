#!/usr/bin/env python3
"""All-order polynomial-D-log exclusion for the July density normalizer.

The exact abelian residual ``K`` satisfies a first-order equation over the
quadratic sheet.  Rationalization on the real arc from ``x=0`` to ``x=-2``
certifies ``K(-2)>0``.  Its local recurrence then forces a nonzero
``(x+2)^(3/2)`` term in ``K`` and therefore a nonzero ``(x+2)^(5/2)`` term
in the normalized density clock.  The shared Puiseux-flow compiler turns
that exact germ into the Julia root-multiplicity contradiction.

The conclusion concerns the clock that sends the linear residual to the
July residual.  It does not quantify over every finite polynomial residual.
"""

from __future__ import annotations

from math import comb
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import sympy as sp


HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[2] / "src"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gauge_pure_contact_zero_tensor_density_holonomy import (  # noqa: E402
    run as holonomy_run,
)
from ztare.common.content_bound_evidence import (  # noqa: E402
    EvidenceAuthority,
)
from ztare.common.filtered_obstruction import (  # noqa: E402
    FilteredPuiseuxClaim,
    FilteredPuiseuxEvidenceScope,
    FilteredPuiseuxFlowProblem,
    compile_filtered_puiseux_flow_obstruction,
    make_filtered_puiseux_context,
    make_filtered_puiseux_evidence,
)


def _sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bernstein_coefficients(
    polynomial: sp.Expr,
    variable: sp.Symbol,
) -> tuple[sp.Rational, ...]:
    """Convert a QQ power-basis polynomial to Bernstein coefficients on [0,1]."""

    value = sp.Poly(polynomial, variable, domain=sp.QQ)
    degree = value.degree()
    power = [value.nth(index) for index in range(degree + 1)]
    return tuple(
        sp.factor(sum(
            power[index]
            * sp.Rational(comb(order, index), comb(degree, index))
            for index in range(order + 1)
        ))
        for order in range(degree + 1)
    )


def _evidence(
    *,
    context,
    claim: FilteredPuiseuxClaim,
    digest: str,
    coefficient_claim: bool,
):
    return make_filtered_puiseux_evidence(
        claim=claim,
        context=context,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope=(
            FilteredPuiseuxEvidenceScope.EXACT_FIRST_FRACTIONAL_GERM
            if coefficient_claim
            else FilteredPuiseuxEvidenceScope.EXACT_FORMAL_FLOW_IDENTITY
        ),
        evidence_sha256=digest,
    )


def run(verification_rows: int = 8) -> dict[str, object]:
    if verification_rows < 8:
        raise ValueError("the density D-log audit needs eight exact rows")

    holonomy = holonomy_run(verification_rows)
    x, t = sp.symbols("x t")
    discriminant = 36 + 12 * x - 3 * x**2
    normal_two = holonomy["normal_two_velocity"]
    density_velocity = holonomy["tensor_density_velocity"]
    a_rational = sp.sympify(normal_two["rational_part"])
    a_radical = sp.sympify(normal_two["radical_coefficient"])
    j_rational = sp.sympify(density_velocity["rational_part"])
    j_radical = sp.sympify(density_velocity["radical_coefficient"])

    # This rational parameter follows the selected positive radical sheet
    # from t=1 (x=0) to t=0 (x=-2).
    x_of_t = 6 * (t**2 - 1) / (t**2 + 3)
    radical_of_t = 24 * t / (t**2 + 3)
    assert sp.cancel(
        discriminant.subs(x, x_of_t) - radical_of_t**2
    ) == 0
    a_of_t = sp.factor(
        a_rational.subs(x, x_of_t)
        + a_radical.subs(x, x_of_t) * radical_of_t
    )
    j_of_t = sp.factor(
        j_rational.subs(x, x_of_t)
        + j_radical.subs(x, x_of_t) * radical_of_t
    )
    regular_denominator = sp.factor(1 + 2 * x_of_t * a_of_t)

    j_positive_polynomial = (
        121 * t**9
        - 1597 * t**8
        + 8914 * t**7
        - 20910 * t**6
        + 9828 * t**5
        - 7128 * t**4
        + 34686 * t**3
        + 53838 * t**2
        + 28755 * t
        + 8181
    )
    denominator_positive_polynomial = (
        199 * t**7
        - 1393 * t**6
        + 67 * t**5
        + 219 * t**4
        + 5973 * t**3
        + 10125 * t**2
        + 10593 * t
        + 2889
    )
    expected_j = (
        (t - 1) * j_positive_polynomial
        / (
            672
            * (t - 3) ** 3
            * (t + 1)
            * (t**2 + 3)
            * (t**2 - 6 * t - 3) ** 2
        )
    )
    expected_regular_denominator = (
        denominator_positive_polynomial
        / (
            112
            * (t - 3)
            * (t + 1) ** 2
            * (t**2 + 3)
            * (t**2 - 6 * t - 3)
        )
    )
    assert sp.cancel(j_of_t - expected_j) == 0
    assert sp.cancel(
        regular_denominator - expected_regular_denominator
    ) == 0

    j_bernstein = _bernstein_coefficients(j_positive_polynomial, t)
    denominator_bernstein = _bernstein_coefficients(
        denominator_positive_polynomial, t
    )
    assert all(value > 0 for value in j_bernstein)
    assert all(value > 0 for value in denominator_bernstein)

    # On 0<t<1 the displayed factorizations give j>0 and
    # 1+2*x*a>0, while x<0.  Hence the inhomogeneous coefficient
    # alpha=j/(x*(1+2*x*a)) is negative.  Variation of constants with
    # K(0)=0 then gives K(x)>0 for -2<x<0 and K(-2)=k0>0.
    k0 = sp.symbols("k0", positive=True)
    local_x = t**2 - 2
    local_radical = t * sp.sqrt(24 - 3 * t**2)
    local_a = sp.series(
        a_rational.subs(x, local_x)
        + a_radical.subs(x, local_x) * local_radical,
        t,
        0,
        6,
    ).removeO().expand()
    local_j = sp.series(
        j_rational.subs(x, local_x)
        + j_radical.subs(x, local_x) * local_radical,
        t,
        0,
        6,
    ).removeO().expand()
    k1, k2, k3, k4 = sp.symbols("k1 k2 k3 k4")
    local_k = k0 + k1 * t + k2 * t**2 + k3 * t**3 + k4 * t**4
    ode_residual = sp.series(
        local_x
        * (1 + 2 * local_x * local_a)
        * sp.diff(local_k, t)
        / (2 * t)
        - local_j
        - (
            6 * local_x * local_a
            + 3 * local_x**2 * sp.diff(local_a, t) / (2 * t)
            - 1
        )
        * local_k,
        t,
        0,
        3,
    ).removeO().expand()
    solved: dict[sp.Symbol, sp.Expr] = {}
    for power, coefficient in ((-1, k1), (0, k2), (1, k3), (2, k4)):
        equation = sp.expand(ode_residual.subs(solved)).coeff(t, power)
        values = sp.solve(equation, coefficient, dict=False)
        assert len(values) == 1
        solved[coefficient] = sp.factor(values[0])
    assert solved[k1] == 0
    assert sp.factor(
        solved[k2] - (5400 * k0 - 101) / sp.Integer(11556)
    ) == 0
    expected_k3 = 25 * sp.sqrt(6) * (108 * k0 + 1) / 11556
    assert sp.factor(solved[k3] - expected_k3) == 0
    assert sp.ask(sp.Q.positive(expected_k3)) is True
    critical_square_t3 = sp.factor(2 * k0 * expected_k3)
    assert sp.ask(sp.Q.positive(critical_square_t3)) is True

    derivative_relative_branch = sp.factor(
        -sp.Rational(2, 3) * expected_k3 / k0
    )
    endpoint_relative_branch = sp.factor(
        sp.Rational(2, 5) * derivative_relative_branch
    )
    assert derivative_relative_branch != 0
    assert endpoint_relative_branch != 0

    expansion_payload = {
        "germ": "normalized_density_clock_of_July_critical_residual",
        "branch_point": -2,
        "local_coordinate": "u=x+2=t^2",
        "k0_sign": "positive",
        "local_k_t1": str(solved[k1]),
        "local_k_t2": str(solved[k2]),
        "local_k_t3": str(solved[k3]),
        "local_k_square_t3": str(critical_square_t3),
        "critical_square_base_field_status": (
            "not_in_C(x): nonzero odd t^3 coefficient"
        ),
        "normalizer_linear_coefficient": "(72*k0)^(-2/3), nonzero",
        "normalizer_first_fractional_exponent": "5/2",
        "normalizer_relative_fractional_coefficient": str(
            endpoint_relative_branch
        ),
        "j_positive_bernstein": [str(value) for value in j_bernstein],
        "regular_denominator_positive_bernstein": [
            str(value) for value in denominator_bernstein
        ],
    }
    expansion_digest = _sha256(expansion_payload)
    context = make_filtered_puiseux_context(
        germ_id="jacobian_pure_contact_zero_density_normalizer_germ",
        local_coordinate_id="u=x+2_on_selected_quadratic_sheet",
        first_fractional_exponent=Fraction(5, 2),
        local_expansion_evidence_sha256=expansion_digest,
    )
    certificate = compile_filtered_puiseux_flow_obstruction(
        FilteredPuiseuxFlowProblem(
            name=(
                "jacobian_pure_contact_zero_"
                "linear_density_representative_dlog"
            ),
            context=context,
            evidence=(
                _evidence(
                    context=context,
                    claim=(
                        FilteredPuiseuxClaim.REGULAR_LINEAR_COEFFICIENT_NONZERO
                    ),
                    digest=expansion_digest,
                    coefficient_claim=True,
                ),
                _evidence(
                    context=context,
                    claim=(
                        FilteredPuiseuxClaim.FIRST_FRACTIONAL_COEFFICIENT_NONZERO
                    ),
                    digest=expansion_digest,
                    coefficient_claim=True,
                ),
                _evidence(
                    context=context,
                    claim=FilteredPuiseuxClaim.JULIA_FLOW_IDENTITY,
                    digest=expansion_digest,
                    coefficient_claim=False,
                ),
            ),
        )
    )
    assert certificate.polynomial_generator_excluded

    core: dict[str, object] = {
        "schema": (
            "axiompack.jacobian_pure_contact_zero_"
            "tensor_density_dlog_puiseux.v1"
        ),
        "quadratic_arc_sign_certificate": {
            "parameter_interval": "0<=t<=1",
            "x_parameterization": str(x_of_t),
            "radical_parameterization": str(radical_of_t),
            "j_positive_bernstein": [str(value) for value in j_bernstein],
            "regular_denominator_positive_bernstein": [
                str(value) for value in denominator_bernstein
            ],
            "variation_of_constants_conclusion": "K(-2)=k0>0",
        },
        "local_density_clock": expansion_payload,
        "puiseux_flow_compiler": certificate.to_dict(),
        "consequence": {
            "linear_representative_polynomial_dlog_excluded": True,
            "arbitrary_polynomial_representative_excluded": False,
            "minimax_lower_bound_closed": False,
        },
        "claim_boundary": (
            "The unique normalized density clock from the linear residual "
            "to the July critical residual is not the time-one endpoint of "
            "a finite polynomial vector field. Other finite polynomial "
            "module representatives and the full contact filtration remain "
            "outside this certificate."
        ),
    }
    return {**core, "certificate_sha256": _sha256(core)}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
