import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ztare.pde.canary import (  # noqa: E402
    TICK669_PHYSICAL_CANARY_TARGETS,
    build_pde_canary_reingestion_receipt,
    build_pde_failure_memory_rows,
)
from ztare.pde.readiness import build_pde_kernel_readiness_receipt  # noqa: E402
from ztare.pde.gate_runner import run_pde_leaf_work_order_gates  # noqa: E402
from ztare.pde import cli as pde_cli  # noqa: E402


def _gate_bundle() -> dict:
    readiness = build_pde_kernel_readiness_receipt()
    work_order = readiness["canary_work_order"]
    payloads = {
        "G-PDE-ANALYTIC-SUBSTANCE": {
            "analytic_object": "localized pressure tail on an annular carrier",
            "target_estimate": "annular Riesz pressure reserve",
            "quantitative_inequality": "D_r <= C * D_R",
            "norm_or_quantity": "parabolic pressure quantity D_r",
            "scale_or_localization": "fixed annular band with cutoff",
            "derivation_mechanism": "Calderon-Zygmund/Riesz localization",
            "constants_or_exponents": "scale-invariant C",
            "endpoint_or_limit_handling": "endpoint tail asserted",
            "hostile_packet_or_sharpness": "low-high leakage packet",
        },
        "G-PDE-OPERATOR-ADMISSIBILITY": {
            "operator_family": "annular Riesz / Leray projection",
            "kernel_or_multiplier_model": "Calderon-Zygmund kernel",
            "raw_global_CZ_bound": "global CZ bound used as annular payment",
            "post_projection_leakage_unpaid": True,
            "cutoff_commutator_tail_unpaid": True,
            "proxy_carrier_operator_bound": True,
        },
        "G-PDE-PHYSICAL-ACCOUNTING": {
            "physical_system": "Navier-Stokes annular control volume",
            "governing_law_or_balance": "local energy balance with pressure flux",
            "conserved_or_dissipated_quantity": "PSD defect trace payment",
            "quantity_dimensions": {"L": -1, "T": -2},
            "target_dimensions": {"L": -1, "T": -2},
            "candidate_inequality": "Q <= C * R",
            "dimensional_features": {
                "Q": {"L": -1, "T": -2},
                "C": "dimensionless",
                "R": {"L": -1, "T": -2},
            },
            "allowed_endpoints": ["Q", "C", "R"],
            "balance_law_terms": [
                {
                    "name": "localized time derivative",
                    "role": "time derivative",
                    "dimensions": {"L": -1, "T": -2},
                    "payment_status": "paid",
                },
                {
                    "name": "pressure boundary flux",
                    "role": "flux boundary",
                    "dimensions": {"L": -1, "T": -2},
                    "payment_status": "named_only",
                },
                {
                    "name": "viscous dissipation sink",
                    "role": "viscous dissipation sink",
                    "dimensions": {"L": -1, "T": -2},
                    "payment_status": "paid",
                },
                {
                    "name": "positive defect trace sign",
                    "role": "positive sign structure",
                    "dimensions": {"L": -1, "T": -2},
                    "payment_status": "paid",
                },
            ],
            "scale_normalization": "parabolic normalization",
            "flux_or_boundary_terms": "pressure flux named but not paid",
            "localization_region": "fixed annular band",
            "carrier_or_material_volume": "same annular carrier required",
            "source_sink_or_forcing_terms": "viscous sink accounted",
            "sign_or_positivity_structure": "signed pressure cancellation separated from positive trace",
            "operator_or_projection_losses": "projection loss unpaid",
            "cutoff_commutator_or_tail_terms": "cutoff tail unpaid",
            "initial_boundary_data": "local boundary data included",
            "hostile_physical_packet": "low-high pressure packet",
            "operator_loss_ignored": True,
            "cutoff_tail_discarded": True,
        },
        "G-PDE-EQUALITY-PROVENANCE": {
            "equality_target": "PSD trace payment equals projected annular packet payment",
            "left_stream": "PSD defect trace packet",
            "right_stream": "projected tracefree annular packet",
            "provenance_kind": "record_field_projection",
            "constructor_or_theorem": "raw localized pressure CZ/Riesz tail route",
            "generated_fields": ["pressure tail", "projected packet label"],
            "source_binding": "not supplied by raw pressure CZ route",
            "anti_proxy_or_anti_laundering_fields": "not supplied",
            "hostile_packet_or_confuser": "record-field equality laundering packet",
            "proof_boundary": (
                "negative canary: raw pressure estimate does not prove "
                "projected packet payment equality"
            ),
            "field_projection_only": True,
            "derived_equality_without_source_binding": True,
            "proxy_stream_allowed": True,
        },
    }
    return run_pde_leaf_work_order_gates(work_order, payloads, theorem_db={})


def test_pde_canary_reingestion_emits_physical_scoreboard_memory_and_surface_rows() -> None:
    readiness = build_pde_kernel_readiness_receipt()
    bundle = _gate_bundle()

    receipt = build_pde_canary_reingestion_receipt(
        readiness_receipt=readiness,
        gate_run_bundle=bundle,
        physical_receipt={"artifact": "tick669_physical_canary_kill_chain_receipt.json"},
    )

    assert receipt["schema"] == "pde-canary-reingestion-receipt-v1"
    assert receipt["kernel_loop_ready"] is True
    assert receipt["scoreboard"]["tick669_gates_run"] is True
    assert receipt["gate_run_summary"]["next_required_work_unit_count"] == len(
        bundle["next_required_work_units"]
    )
    assert "G-PDE-EQUALITY-PROVENANCE" in receipt["gate_run_summary"]["failed_gate_ids"]
    assert receipt["scoreboard"]["next_work_units_emitted"] is True
    assert receipt["scoreboard"]["failure_memory_updated"] is True
    assert receipt["scoreboard"]["formal_surface_row_updated"] is True
    assert receipt["canary_math_verdict"]["verdict"] == "NEED_THEOREM"
    assert receipt["canary_math_verdict"]["equality_provenance_passed"] is False
    assert receipt["failure_memory_rows"][0]["leanmill_policy"].startswith("project_pde_memory_only")
    assert receipt["physical_accounting_work_orders"]
    assert receipt["equality_provenance_work_orders"]
    assert set(receipt["formal_surface_map"]["required_primitives"]) == set(
        TICK669_PHYSICAL_CANARY_TARGETS
    )
    assert receipt["formal_surface_map"]["missing_required_primitives"] == []


def test_pde_canary_reingestion_respects_nested_resolved_targets() -> None:
    readiness = build_pde_kernel_readiness_receipt()
    bundle = _gate_bundle()

    receipt = build_pde_canary_reingestion_receipt(
        readiness_receipt=readiness,
        gate_run_bundle=bundle,
        physical_receipt={
            "current_compression": {
                "paid_physical_targets": [
                    "selected_psd_owner_prefix_no_reuse_budget",
                    "nonadaptive_annular_event_stream_identity",
                ],
                "upstream_explicit_targets": [
                    "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier"
                ],
            }
        },
    )

    assert receipt["kernel_loop_ready"] is True
    assert receipt["physical_accounting"]["required_canary_targets"] == [
        "psd_trace_to_projected_tracefree_payment",
        "cutoff_commutator_tail_payment_on_same_stream",
    ]
    assert set(receipt["physical_accounting"]["resolved_canary_targets"]) == {
        "selected_psd_owner_prefix_no_reuse_budget",
        "nonadaptive_annular_event_stream_identity",
        "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier",
    }
    assert {
        unit["target"] for unit in receipt["next_leaf_work_orders"]
    }.issuperset(set(receipt["physical_accounting"]["required_canary_targets"]))


def test_pde_failure_memory_rows_are_project_physics_keyed() -> None:
    rows = build_pde_failure_memory_rows(
        target="annular_bandlimited_riesz_l1_psd_trace_payment",
        gate_run_bundle=_gate_bundle(),
    )

    by_gate = {row["source_gate_id"]: row for row in rows}

    assert "G-PDE-PHYSICAL-ACCOUNTING" in by_gate
    assert "G-PDE-EQUALITY-PROVENANCE" in by_gate
    assert "G-PDE-OPERATOR-ADMISSIBILITY" in by_gate
    assert by_gate["G-PDE-EQUALITY-PROVENANCE"]["failure_class"] == "equality_provenance_unpaid"
    assert "field_projection_only" in by_gate["G-PDE-EQUALITY-PROVENANCE"]["rejected_substitutes"]
    assert by_gate["G-PDE-OPERATOR-ADMISSIBILITY"]["failure_class"] == "operator_admissibility_unpaid"
    assert "raw_global_CZ_bound" in by_gate["G-PDE-OPERATOR-ADMISSIBILITY"]["rejected_substitutes"]
    assert (
        "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier"
        in by_gate["G-PDE-OPERATOR-ADMISSIBILITY"]["next_targets"]
    )


def test_pde_cli_canary_report_json(capsys) -> None:
    readiness = build_pde_kernel_readiness_receipt()
    bundle = _gate_bundle()
    with tempfile.NamedTemporaryFile("w", suffix=".json") as readiness_file, tempfile.NamedTemporaryFile(
        "w", suffix=".json"
    ) as bundle_file:
        json.dump(readiness, readiness_file)
        json.dump(bundle, bundle_file)
        readiness_file.flush()
        bundle_file.flush()

        assert (
            pde_cli.main(
                [
                    "canary-report",
                    "--readiness-json",
                    readiness_file.name,
                    "--gate-run-json",
                    bundle_file.name,
                    "--json",
                ]
            )
            == 0
        )

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pde-canary-reingestion-receipt-v1"
    assert payload["kernel_loop_ready"] is True
