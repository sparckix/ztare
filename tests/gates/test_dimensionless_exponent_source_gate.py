from ztare.gates.dimensionless_exponent_source_gate import run_gate


def test_dimensionless_square_requires_analytic_source_receipt():
    result = run_gate(
        expression="mu * r^2 / T",
        dimensionless_variables={"r": 2},
        receipts={
            "analytic_source": "Cauchy-Schwarz/Jensen stretch-rate identity",
            "source_identity_type": "cauchy_schwarz",
            "source_derives_exponent": True,
            "fixed_before_payoff": True,
            "same_carrier_or_scope": True,
            "not_dimensional_analysis_only": True,
            "consumed_by": "stretchRateDissipationBridgeTarget",
        },
    )

    assert result["passed"] is True
    assert result["nontrivial_dimensionless_exponents"] == [{"name": "r", "exponent": "2"}]


def test_dimensionless_square_rejects_pi_only_laundering():
    result = run_gate(
        expression="mu * r^2 / T",
        dimensionless_variables={"r": 2},
        receipts={
            "analytic_source": "Buckingham/Pi dimensional fit",
            "source_identity_type": "other",
            "source_derives_exponent": False,
            "fixed_before_payoff": True,
            "same_carrier_or_scope": True,
            "not_dimensional_analysis_only": False,
            "consumed_by": "stretchRateDissipationBridgeTarget",
        },
    )

    assert result["passed"] is False
    assert result["hard_fail"] is True
    assert "dimensional analysis alone" in result["reason"]


def test_linear_dimensionless_factor_does_not_require_exponent_receipt():
    result = run_gate(
        expression="mu * r / T",
        dimensionless_variables={"r": 1},
        receipts={},
    )

    assert result["passed"] is True
    assert result["nontrivial_dimensionless_exponents"] == []
