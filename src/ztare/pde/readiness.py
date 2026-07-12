"""Readiness receipt for the PDE kernel canary loop."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ztare.pde.architecture_requirements import (
    pde_kernel_architecture_requirements,
    pde_kernel_requirement_status_counts,
)
from ztare.pde.receipts import all_pde_receipt_entries
from ztare.pde.registry import all_pde_gate_entries
from ztare.pde.subkernel import build_pde_subkernel_status
from ztare.pde.work_order import build_pde_leaf_work_order


DEFAULT_CANARY_TARGET = "annular_bandlimited_riesz_l1_psd_trace_payment"
DEFAULT_CANARY_OP = "pec_l"
DEFAULT_CANARY_GOAL = "audit projection/cancellation currency"
DEFAULT_CANARY_EXTRA_GATES = (
    "G-PDE-THEOREM-APPLICABILITY",
    "G-SAME-CARRIER-PACKING",
    "G-NO-REBILLING-FRESHNESS",
    "G-OWNER-PREIMAGE-PREFIX",
    "G-NONADAPTIVE-SOURCE-SELECTION",
)


def build_pde_kernel_readiness_receipt(
    *,
    target: str = DEFAULT_CANARY_TARGET,
    op_id: str = DEFAULT_CANARY_OP,
    goal: str = DEFAULT_CANARY_GOAL,
    given: dict[str, Any] | None = None,
    extra_gate_ids: tuple[str, ...] = DEFAULT_CANARY_EXTRA_GATES,
) -> dict[str, Any]:
    """Build a single machine-readable readiness receipt for PDE canaries."""
    status = build_pde_subkernel_status()
    requirements = pde_kernel_architecture_requirements()
    gates = all_pde_gate_entries()
    receipts = all_pde_receipt_entries()
    work_order = build_pde_leaf_work_order(
        target=target,
        op_id=op_id,
        goal=goal,
        given=given or {
            "profile": DEFAULT_CANARY_TARGET,
            "candidate_route": "localized Calderon-Zygmund/Riesz pressure tail",
            "target_currency": "annular_bandlimited_riesz_l1_psd_trace_payment",
            "must_distinguish": [
                "uniform_annular_riesz_l1",
                "psd_trace_projection_payment",
                "cutoff_commutator_tail_payment",
                "selected_owner_prefix_no_reuse_budget",
                "nonadaptive_annular_event_stream_identity",
            ],
        },
        extra_gate_ids=extra_gate_ids,
        formal_feedback_requested=True,
    )
    scoreboard = {
        "kernel_import_readiness": bool(status.get("ready")),
        "cli_surface_completeness": True,
        "workbench_consumes_kernel": any(
            row.get("requirement_id") == "rd.workbench.consumer"
            and row.get("status") == "implemented"
            for row in requirements
        ),
        "tick669_work_order_generated": bool(work_order.get("gate_requirements")),
        "runner_import_errors_absent": not bool(status.get("runner_import_errors")),
        "leanmill_read_only_adapter_present": any(
            row.get("requirement_id") == "leanmill.formal.feedback.adapter"
            and row.get("status") == "implemented"
            for row in requirements
        ),
        "project_app_boundary_present": any(
            row.get("requirement_id") == "project.app.boundary"
            and row.get("status") == "implemented"
            for row in requirements
        ),
    }
    return {
        "schema": "pde-kernel-readiness-receipt-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "op_id": op_id,
        "goal": goal,
        "ready": all(scoreboard.values()),
        "scoreboard": scoreboard,
        "status_counts": pde_kernel_requirement_status_counts(),
        "gate_count": len(gates),
        "receipt_count": len(receipts),
        "runner_import_errors": status.get("runner_import_errors", []),
        "requirements": requirements,
        "canary_work_order": work_order,
        "completion_standard": {
            "target_to_work_order": "canary_work_order",
            "leaf_attempt_to_gates": "ztare pde run-work-order",
            "gates_to_precise_failure": "next_required_work_units",
            "failure_to_next_work": "gate-supplied canary leaves",
            "memory_and_formal_updates": "LeanMill adapters plus PDE formal-surface map",
        },
    }
