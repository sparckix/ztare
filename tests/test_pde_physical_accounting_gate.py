from ztare.pde.gate_runner import run_pde_gate
from ztare.pde.work_order import build_pde_leaf_work_order


def _paid_payload() -> dict:
    dims = {"L": -1, "T": -2}
    return {
        "physical_system": "incompressible Navier-Stokes localized annular control volume",
        "governing_law_or_balance": "local energy balance with pressure flux and viscous dissipation",
        "conserved_or_dissipated_quantity": "localized energy dissipation flux",
        "quantity_dimensions": dims,
        "target_dimensions": dims,
        "candidate_inequality": "Q <= C * R",
        "dimensional_features": {
            "Q": dims,
            "C": "dimensionless",
            "R": dims,
        },
        "allowed_endpoints": ["Q", "C", "R"],
        "balance_law_terms": [
            {
                "name": "localized time derivative",
                "role": "time derivative",
                "dimensions": dims,
                "payment_status": "paid",
            },
            {
                "name": "pressure boundary flux",
                "role": "flux boundary",
                "dimensions": dims,
                "payment_status": "paid",
            },
            {
                "name": "viscous dissipation sink",
                "role": "viscous dissipation sink",
                "dimensions": dims,
                "payment_status": "paid",
            },
            {
                "name": "positive dissipation sign",
                "role": "positive sign structure",
                "dimensions": dims,
                "payment_status": "paid",
            },
        ],
        "pi_group_forcing": {
            "label": "heat_length_forcing",
            "quantity_dim": {"L": 1},
            "subset_dims": {"nu": {"L": 2, "T": -1}, "t": {"T": 1}},
            "expected": "forced",
        },
        "scale_normalization": "parabolic scale invariant normalization",
        "flux_or_boundary_terms": "pressure flux and viscous boundary terms paid by the same annular cutoff",
        "localization_region": "fixed annular region selected before payoff",
        "carrier_or_material_volume": "same annular carrier/control volume as the estimate target",
        "source_sink_or_forcing_terms": "no external forcing; viscous sink accounted",
        "sign_or_positivity_structure": "positive dissipation term separated from signed pressure flux",
        "operator_or_projection_losses": "Leray/Riesz projection losses paid by operator admissibility",
        "cutoff_commutator_or_tail_terms": "cutoff commutator tail paid on the selected stream",
        "initial_boundary_data": "local energy boundary data included in the invoice",
        "hostile_physical_packet": "low-high pressure packet with boundary leakage",
    }


def test_physical_accounting_gate_accepts_paid_physical_invoice() -> None:
    result = run_pde_gate("G-PDE-PHYSICAL-ACCOUNTING", _paid_payload())

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["result"]["classification"] == "physical_accounting_paid"
    assert result["result"]["dimension_mismatch"] is False
    assert result["result"]["candidate_dimension_audit"]["passed"] is True
    assert result["result"]["balance_law_audit"]["passed"] is True
    assert result["result"]["pi_group_audit"]["passed"] is True


def test_physical_accounting_gate_rejects_label_only_unpaid_route() -> None:
    payload = {
        "physical_system": "Navier-Stokes pressure route",
        "governing_law_or_balance": "energy conservation label",
        "conserved_or_dissipated_quantity": "energy",
        "quantity_dimensions": {"L": -1, "T": -2},
        "target_dimensions": {"L": 0, "T": -1},
        "candidate_inequality": "Q <= R",
        "dimensional_features": {
            "Q": {"L": -1, "T": -2},
            "R": {"L": 0, "T": -1},
        },
        "allowed_endpoints": ["Q", "R"],
        "conservation_label_only": True,
        "boundary_terms_discarded": True,
        "operator_loss_ignored": True,
        "soft_physics_loss_only": True,
    }
    result = run_pde_gate("G-PDE-PHYSICAL-ACCOUNTING", payload)

    targets = {
        unit["target"]
        for unit in result["next_required_work_units"]
        if isinstance(unit, dict)
    }

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["result"]["dimension_mismatch"] is True
    assert "conservation_label_only" in result["rejected_substitutes"]
    assert "physical_dimensional_homogeneity" in targets
    assert "physical_balance_flux_boundary_invoice" in targets
    assert "physical_sign_operator_tail_invoice" in targets
    assert result["result"]["candidate_dimension_audit"]["passed"] is False
    assert result["result"]["balance_law_audit"]["passed"] is False


def test_physical_accounting_gate_rejects_unpaid_balance_term() -> None:
    payload = _paid_payload()
    payload["balance_law_terms"][1]["payment_status"] = "named_only"

    result = run_pde_gate("G-PDE-PHYSICAL-ACCOUNTING", payload)

    assert result["passed"] is False
    assert result["result"]["balance_law_audit"]["passed"] is False
    assert any(
        violation["type"] == "balance_law_term_audit_failure"
        for violation in result["result"]["violations"]
    )


def test_physical_accounting_gate_rejects_wrong_pi_group_contract() -> None:
    payload = _paid_payload()
    payload["pi_group_forcing"]["expected"] = "needs_independent_constant"

    result = run_pde_gate("G-PDE-PHYSICAL-ACCOUNTING", payload)

    assert result["passed"] is False
    assert result["result"]["pi_group_audit"]["passed"] is False


def test_pec_l_work_order_includes_physical_accounting_gate() -> None:
    work_order = build_pde_leaf_work_order(
        target="annular pressure payment",
        op_id="pec_l",
    )
    gate_ids = {
        gate["gate_id"]
        for gate in work_order["gate_requirements"]
    }

    assert "G-PDE-PHYSICAL-ACCOUNTING" in gate_ids
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in gate_ids
