from ztare.pde.gate_runner import run_pde_gate, run_pde_leaf_work_order_gates
from ztare.pde.work_order import build_pde_leaf_work_order


def _analytic_payload() -> dict:
    return {
        "analytic_object": "localized pressure tail on an annular carrier",
        "target_estimate": "annular Riesz pressure reserve",
        "quantitative_inequality": "D_r <= C * D_R",
        "norm_or_quantity": "parabolic pressure quantity D_r",
        "scale_or_localization": "annulus r < |x| < R with cutoff",
        "derivation_mechanism": "Calderon-Zygmund/Riesz kernel localization",
        "constants_or_exponents": "scale-invariant C",
        "endpoint_or_limit_handling": "endpoint tail handled by annular cutoff",
        "hostile_packet_or_sharpness": "low-high leakage packet",
    }


def _operator_payload() -> dict:
    return {
        "operator_family": "annular Riesz transform",
        "kernel_or_multiplier_model": "Calderon-Zygmund kernel with fixed bandlimit",
        "input_output_norms": "trace variation to projected trace variation",
        "scale_or_bandlimit": "dyadic annular band fixed before payoff",
        "localization_or_cutoff": "same annular cutoff support",
        "carrier_identity": "input and output share carrier",
        "endpoint_handling": "uniform annular kernel L1 endpoint payment",
        "commutator_or_tail_payment": "cutoff commutator tails paid",
        "currency_target": "projected tracefree variation",
        "hostile_packet_or_counterexample": "low-high leakage packet",
    }


def test_run_pde_gate_executes_analytic_substance_by_registry_id() -> None:
    result = run_pde_gate("G-PDE-ANALYTIC-SUBSTANCE", _analytic_payload())

    assert result["schema"] == "pde-gate-run-result-v1"
    assert result["passed"] is True
    assert result["complete"] is True
    assert result["registry_entry"]["gate_id"] == "G-PDE-ANALYTIC-SUBSTANCE"
    assert result["next_required_work_unit"] == {}
    assert result["result"]["classification"] == "analytic_pde_estimate"


def test_run_pde_gate_executes_theorem_applicability_with_supplied_db() -> None:
    theorem_db = {
        "toy_trace_payment": {
            "requires": ["same_carrier", "paid_tail"],
            "does_not_accept": ["raw_cz_substitute"],
            "concludes": {"trace_payment": True},
        }
    }
    result = run_pde_gate(
        "G-PDE-THEOREM-APPLICABILITY",
        {
            "theorem": "toy_trace_payment",
            "available": {
                "same_carrier": True,
                "paid_tail": False,
                "raw_cz_substitute": True,
            },
        },
        theorem_db=theorem_db,
    )

    assert result["passed"] is False
    assert result["complete"] is False
    assert result["missing_fields"] == ["paid_tail"]
    assert result["rejected_substitutes"] == ["raw_cz_substitute"]
    assert result["next_required_work_unit"]["work_unit_type"] == "theorem_applicability"
    assert result["next_required_work_unit"]["action"] == "supply_missing_fields"


def test_run_pde_gate_executes_operator_admissibility_by_registry_id() -> None:
    result = run_pde_gate("G-PDE-OPERATOR-ADMISSIBILITY", _operator_payload())

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["result"]["classification"] == "operator_admissibility_paid"


def test_run_pde_gate_preserves_operator_canary_next_units() -> None:
    result = run_pde_gate(
        "G-PDE-OPERATOR-ADMISSIBILITY",
        {
            "operator_family": "annular Riesz / Leray projection",
            "kernel_or_multiplier_model": "Calderon-Zygmund kernel",
            "raw_global_CZ_bound": "global CZ bound used as annular payment",
        },
    )

    targets = {
        unit["target"]
        for unit in result["next_required_work_units"]
    }

    assert result["passed"] is False
    assert "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier" in targets
    assert "selected_psd_owner_prefix_no_reuse_budget" in targets


def test_run_pde_leaf_work_order_gates_reports_missing_payloads() -> None:
    work_order = build_pde_leaf_work_order(
        target="annular pressure payment",
        op_id="pec_l",
        extra_gate_ids=["G-PDE-THEOREM-APPLICABILITY"],
    )
    bundle = run_pde_leaf_work_order_gates(
        work_order,
        {"G-PDE-ANALYTIC-SUBSTANCE": _analytic_payload()},
        theorem_db={},
    )

    assert bundle["schema"] == "pde-leaf-gate-run-bundle-v1"
    assert bundle["passed"] is False
    assert bundle["summary"]["failed_gate_ids"]
    assert bundle["summary"]["next_required_work_unit_count"] == len(
        bundle["next_required_work_units"]
    )
    assert bundle["missing_payload_gate_ids"]
    assert bundle["next_required_work_units"]
    missing = [
        item for item in bundle["results"]
        if item["error"] == "missing gate payload"
    ]
    assert missing
    assert missing[0]["next_required_work_unit"]["action"] == "supply_gate_payload"


def test_run_pde_leaf_work_order_gates_reports_missing_process_refs() -> None:
    work_order = build_pde_leaf_work_order(
        target="active Carleson budget identity",
        op_id="pec_l",
        require_process_contract=True,
        pattern_action_contract_ref="pattern_action_contract.json",
        orchestration_contract_ref="",
        pencil_artifact_ref="",
    )
    bundle = run_pde_leaf_work_order_gates(
        work_order,
        {"G-PDE-ANALYTIC-SUBSTANCE": _analytic_payload()},
        theorem_db={},
    )

    process_units = [
        item for item in bundle["next_required_work_units"]
        if item.get("gate_id") == "PDE-PROCESS-CONTRACT"
    ]

    assert bundle["passed"] is False
    assert bundle["complete"] is False
    assert bundle["summary"]["process_contract_passed"] is False
    assert bundle["summary"]["missing_process_artifacts"] == [
        "orchestration_contract",
        "pencil_artifact",
    ]
    assert {unit["artifact_key"] for unit in process_units} == {
        "orchestration_contract",
        "pencil_artifact",
    }


def test_run_pde_gate_wraps_single_owner_preimage_receipt_payload() -> None:
    result = run_pde_gate(
        "G-OWNER-PREIMAGE-PREFIX",
        {
            "name": "owner-prefix",
            "owner_map": "ownerOfEvent",
            "pre_payoff_timing": "fixed before payoff",
            "full_output_scale_owner": "output-scale owner atom",
            "pointwise_payment": "eventPay e <= atomCharge (owner e)",
            "finite_atom_budget": "prefix atomCharge <= B",
            "multiplicity_bound": "M",
            "owner_preimage_prefix_inequality": "prefix eventPay N <= M * prefix atomCharge (A N)",
        },
    )

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["result"]["n_complete_receipts"] == 1
