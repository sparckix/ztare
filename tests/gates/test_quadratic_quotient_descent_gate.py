from ztare.gates.quadratic_quotient_descent_gate import (
    run_quadratic_quotient_descent_gate,
)


def test_quadratic_quotient_descent_complete_passes():
    result = run_quadratic_quotient_descent_gate({
        "label": "complete_quadratic_descent",
        "source_map_or_equivalence": "Sx = source quotient",
        "quadratic_functional": "selected HH quadratic Q",
        "polarized_bilinear_form": "B_Q(x,k)",
        "source_kernel_definition": "k in ker S",
        "representative_selector": "R(Sx)",
        "selector_fixed_before_payoff": "R fixed before target deficit",
        "kernel_square_zero_or_nonpositive": "Q(k) <= 0 for admissible kernel k",
        "kernel_cross_zero_or_nonpositive": "B_Q(R(Sx),k) <= 0",
        "quotient_descent_or_bound": "Q(x) <= C Q(R(Sx)) <= C MPV(Sx)",
        "not_defined_by_target_deficit": "source-only class",
    })
    assert result["passed"] is True
    assert result["complete"] is True


def test_quadratic_quotient_descent_rejects_energy_only():
    result = run_quadratic_quotient_descent_gate({
        "source_map_or_equivalence": "Sx = source quotient",
        "quadratic_functional": "selected HH quadratic Q",
        "representative_selector": "energy minimizer",
        "energy_minimality_only": "minimizer is E-orthogonal to kernel",
    })
    assert result["passed"] is False
    assert "kernel_square_zero_or_nonpositive" in result["missing_fields"]
    assert "energy_minimality_only" in result["weak_substitutes"]


def test_quadratic_quotient_descent_rejects_kernel_square_confuser():
    result = run_quadratic_quotient_descent_gate({
        "source_map_or_equivalence": "Sx = source quotient",
        "quadratic_functional": "selected HH quadratic Q",
        "polarized_bilinear_form": "B_Q(x,k)",
        "source_kernel_definition": "k in ker S",
        "representative_selector": "R(Sx)",
        "selector_fixed_before_payoff": "R fixed before payoff",
        "kernel_square_zero_or_nonpositive": "claimed Q(k) <= 0",
        "kernel_cross_zero_or_nonpositive": "claimed B <= 0",
        "quotient_descent_or_bound": "claimed descent",
        "not_defined_by_target_deficit": "source-only class",
        "kernel_square_positive": "there exists k in ker S with Q(k)>0",
    })
    assert result["passed"] is False
    assert any(v["type"] == "quadratic_quotient_confuser_present" for v in result["violations"])
