from ztare.gates.pde_analytic_substance_gate import run_pde_analytic_substance_gate


def test_pde_analytic_substance_gate_rejects_bridge_only_receipt() -> None:
    result = run_pde_analytic_substance_gate({
        "label": "bridge_only",
        "lean_constructor": "C7DisplayedInvoiceTelescopingFieldIdentityReceipt.foo",
        "bridge_receipt": "same-carrier source timing receipt",
        "timing_receipt": "matching fixed before radius sum",
        "gate_pass_only": "same-carrier/no-rebilling/nonadaptive gates passed",
        "declared_non_estimate": True,
    })

    assert result["passed"] is False
    assert result["classification"] == "source_contract_or_plumbing"
    assert "pde_analytic_substance_missing" in [
        violation["type"] for violation in result["violations"]
    ]
    assert "lean_constructor" in result["weak_substitutes"]


def test_pde_analytic_substance_gate_accepts_quantitative_pressure_receipt() -> None:
    result = run_pde_analytic_substance_gate({
        "label": "pressure_tail_localization",
        "analytic_object": "localized pressure tail after Calderon-Zygmund split",
        "target_estimate": "annular pressure reserve bounded by residual fresh energy",
        "quantitative_inequality": "||p_tail||_{L^{3/2}(Q_r)} <= C r^alpha E_res",
        "norm_or_quantity": "L^{3/2} pressure norm and residual energy",
        "scale_or_localization": "parabolic cylinder Q_r with annular cutoff",
        "derivation_mechanism": "Riesz transform kernel split plus heat-kernel cutoff localization",
        "constants_or_exponents": "C independent of r, alpha > 0",
        "endpoint_or_limit_handling": "finite prefix bound stable under r_k -> 0",
        "hostile_packet_or_sharpness": "fails for nonlocalized harmonic pressure packet",
    })

    assert result["passed"] is True
    assert result["classification"] == "analytic_pde_estimate"
    assert result["missing_fields"] == []
