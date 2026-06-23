from ztare.gates.pde_inequality_dimensional_gate import run_gate


def test_physical_vector_mode_accepts_balanced_phase_alignment_bound():
    result = run_gate(
        "viscosity * shellN^2 * phaseGap^2 <= "
        "gramianConstant * survivalBudget * controlEnergy",
        dimensional_features={
            "viscosity": "L^2 T^-1",
            "shellN": "L^-1",
            "phaseGap": "1",
            "gramianConstant": "1",
            "survivalBudget": "T^-1",
            "controlEnergy": "1",
        },
        allowed_endpoints={
            "viscosity",
            "shellN",
            "phaseGap",
            "gramianConstant",
            "survivalBudget",
            "controlEnergy",
        },
    )

    assert result["passed"] is True
    assert result["dim_check"]["mode"] == "physical_vector"


def test_physical_vector_mode_rejects_missing_survival_budget_dimension():
    result = run_gate(
        "viscosity * shellN^2 * phaseGap^2 <= "
        "gramianConstant * survivalBudget * controlEnergy",
        dimensional_features={
            "viscosity": "L^2 T^-1",
            "shellN": "L^-1",
            "phaseGap": "1",
            "gramianConstant": "1",
            "survivalBudget": "1",
            "controlEnergy": "1",
        },
        allowed_endpoints={
            "viscosity",
            "shellN",
            "phaseGap",
            "gramianConstant",
            "survivalBudget",
            "controlEnergy",
        },
    )

    assert result["passed"] is False
    assert result["violations"][0]["kind"] == "dimensional_mismatch"
    assert result["violations"][0]["lhs_dim"] == {"T": -1.0}
    assert result["violations"][0]["rhs_dim"] == {}


def test_default_physical_vector_mode_rejects_parabolic_latency_mismatch():
    result = run_gate(
        "N^4 * dt^3 * grad_u^2 <= nu * N^2 * dt",
        dimensional_features={},
        allowed_endpoints={"N", "dt", "grad_u", "nu"},
    )

    assert result["passed"] is False
    assert result["violations"][0]["kind"] == "dimensional_mismatch"
    assert result["violations"][0]["lhs_dim"] == {"L": -4.0, "T": 1.0}
    assert result["violations"][0]["rhs_dim"] == {}


def test_unknown_abstract_endpoint_names_do_not_trigger_physical_defaults():
    result = run_gate(
        "survivalProfit <= gamma * rootSq",
        dimensional_features={},
        allowed_endpoints={"survivalProfit", "gamma", "rootSq"},
    )

    assert result["passed"] is True
    assert "lhs_cats" in result["dim_check"]


def test_legacy_category_mode_still_handles_constant_labels():
    result = run_gate(
        "gamma * ampSq <= sharpTarget",
        dimensional_features={
            "gamma": "energy",
            "ampSq": "constant",
            "sharpTarget": "energy",
        },
        allowed_endpoints={"gamma", "ampSq", "sharpTarget"},
    )

    assert result["passed"] is True
    assert "lhs_cats" in result["dim_check"]


def test_double_equals_parses_as_single_equality():
    result = run_gate(
        "beta == 2/3 - 5/(3*q)",
        dimensional_features={
            "beta": "1",
            "q": "1",
        },
        allowed_endpoints={"beta", "q"},
    )

    assert result["passed"] is True
    assert result["lhs"] == "beta"
    assert result["op"] == "="
    assert result["rhs"] == "2/3 - 5/(3*q)"
