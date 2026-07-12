from ztare.pde.currency import (
    missing_pde_exchange_obligations,
    pde_currency_ledger_template,
    pde_exchange_rate_obligations,
)
from ztare.pde.estimates import generate_pde_estimate_skeletons
from ztare.pde.completion_audit import build_pde_kernel_completion_audit
from ztare.pde.ops import pde_execution_template_for_ops, pde_op_by_id
from ztare.pde.receipts import all_pde_receipt_entries


def test_pde_ops_facade_exposes_gp219_execution_template() -> None:
    op = pde_op_by_id("pec_l")
    assert op is not None
    assert op["op_id"] == "pec_l"
    assert "Cancellation" in op["name"]

    template = pde_execution_template_for_ops(["pec_l"])
    assert "estimate_derivation" in template["base_work_unit_templates"]
    assert "pec_l" in template["pde_execution_hints"]


def test_pde_currency_facade_exposes_exchange_obligations() -> None:
    ledger = pde_currency_ledger_template(
        "annular_bandlimited_riesz_l1_psd_trace_payment"
    )
    obligations = pde_exchange_rate_obligations()

    assert ledger["target_currency"] == "annular_bandlimited_riesz_l1_psd_trace_payment"
    assert "psd_defect_trace_to_projected_tracefree_payment" in obligations
    assert missing_pde_exchange_obligations(
        ["signed_to_positive", "reused_to_fresh"],
        available={"signed_to_positive": True},
    ) == ["reused_to_fresh"]


def test_pde_estimate_facade_exposes_projection_tail_skeleton() -> None:
    skeletons = generate_pde_estimate_skeletons(
        target="annular_bandlimited_riesz_l1_psd_trace_payment",
        field="projection",
    )

    assert {skeleton["id"] for skeleton in skeletons} == {"projection_tail_invoice"}
    assert skeletons[0]["hostile_packet"]["name"] == "projection_tail_unpaid_packet"


def test_pde_receipt_registry_includes_work_units_and_gates() -> None:
    receipt_ids = {entry["receipt_id"] for entry in all_pde_receipt_entries()}

    assert "work_unit:estimate_derivation" in receipt_ids
    assert "work_unit:falsifier_packet" in receipt_ids
    assert "gate:G-PDE-HOSTILE-WITNESS" in receipt_ids
    assert "gate:G-PDE-EQUALITY-PROVENANCE" in receipt_ids


def test_pde_completion_audit_checks_kernel_contract() -> None:
    audit = build_pde_kernel_completion_audit(repo_root=".")

    assert audit["schema"] == "pde-kernel-completion-audit-v1"
    assert audit["passed"] is True
    check_ids = {row["check_id"] for row in audit["checks"]}
    assert "receipt_registry_covers_all_gates" in check_ids
    assert "readiness_canary_requires_core_gates" in check_ids
    assert "gate_bundle_summary_contract" in check_ids
    assert "pde_kernel_does_not_import_ns_app" in check_ids
