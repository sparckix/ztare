from src.ztare.gates.persistence_budget_exponent_gate import (
    run_persistence_budget_exponent_gate,
)


def test_rejects_l2_persistence_budget_in_3d_without_thickness():
    result = run_persistence_budget_exponent_gate(
        dimension=3,
        persistence_exponent=2,
        same_carrier_receipt=True,
    )
    assert result["passed"] is False
    assert result["violations"][0]["kind"] == "subcritical_persistence_exponent"


def test_accepts_super_dimension_same_carrier_budget():
    result = run_persistence_budget_exponent_gate(
        dimension=3,
        persistence_exponent=4,
        same_carrier_receipt=True,
    )
    assert result["passed"] is True


def test_accepts_subcritical_with_thickness_receipt():
    result = run_persistence_budget_exponent_gate(
        dimension=3,
        persistence_exponent=2,
        thickness_or_reach_receipt=True,
        same_carrier_receipt=True,
    )
    assert result["passed"] is True


def test_requires_same_carrier_even_when_exponent_is_large():
    result = run_persistence_budget_exponent_gate(
        dimension=3,
        persistence_exponent=4,
    )
    assert result["passed"] is False
    assert result["violations"][0]["kind"] == "same_carrier_receipt_missing"
