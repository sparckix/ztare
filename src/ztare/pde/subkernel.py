"""Readiness diagnostics for the PDE subkernel."""
from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from typing import Any

from ztare.pde.ops import all_pde_ops
from ztare.pde.receipts import all_pde_receipt_entries
from ztare.pde.registry import all_pde_gate_entries
from ztare.pde.architecture_requirements import (
    pde_kernel_architecture_requirements,
    pde_kernel_requirement_status_counts,
)


@dataclass(frozen=True)
class PDERunnerCheck:
    gate_id: str
    runner: str
    importable: bool
    error: str = ""


@dataclass(frozen=True)
class PDESubkernelStatus:
    schema: str
    ready: bool
    gate_count: int
    gates_by_op: dict[str, list[str]]
    runner_checks: list[dict[str, Any]]
    runner_import_errors: list[dict[str, Any]]
    canonical_modules: dict[str, str]
    service_boundaries: dict[str, list[str]]
    architecture_requirements: list[dict[str, Any]]
    architecture_requirement_status_counts: dict[str, int]
    capabilities: list[str]
    notes: list[str]


def _runner_importable(gate_id: str, runner: str) -> dict[str, Any]:
    module_name, sep, func_name = runner.partition(":")
    if not sep or not module_name or not func_name:
        return asdict(PDERunnerCheck(
            gate_id=gate_id,
            runner=runner,
            importable=False,
            error="runner spec must be module:function",
        ))
    try:
        module = importlib.import_module(module_name)
        getattr(module, func_name)
    except Exception as exc:  # noqa: BLE001 - readiness report should not raise
        return asdict(PDERunnerCheck(
            gate_id=gate_id,
            runner=runner,
            importable=False,
            error=f"{type(exc).__name__}: {exc}",
        ))
    return asdict(PDERunnerCheck(gate_id=gate_id, runner=runner, importable=True))


def build_pde_subkernel_status() -> dict[str, Any]:
    """Return a compact status report for the reusable PDE subkernel."""
    entries = all_pde_gate_entries()
    ops = all_pde_ops()
    receipts = all_pde_receipt_entries()
    gates_by_op: dict[str, list[str]] = {}
    for entry in entries:
        gate_id = str(entry.get("gate_id") or "")
        for op_id in entry.get("requires_ops") or ():
            gates_by_op.setdefault(str(op_id), []).append(gate_id)
    runner_checks = [
        _runner_importable(str(entry.get("gate_id") or ""), str(entry.get("runner") or ""))
        for entry in entries
    ]
    runner_errors = [
        check for check in runner_checks
        if not check.get("importable")
    ]
    status = PDESubkernelStatus(
        schema="pde-subkernel-status-v1",
        ready=bool(entries) and not runner_errors,
        gate_count=len(entries),
        gates_by_op={key: sorted(value) for key, value in sorted(gates_by_op.items())},
        runner_checks=runner_checks,
        runner_import_errors=runner_errors,
        canonical_modules={
            "registry": "ztare.pde.registry",
            "ops": "ztare.pde.ops",
            "currency": "ztare.pde.currency",
            "estimates": "ztare.pde.estimates",
            "receipts": "ztare.pde.receipts",
            "work_order": "ztare.pde.work_order",
            "gate_runner": "ztare.pde.gate_runner",
            "engine": "ztare.pde.engine",
            "formal_feedback": "ztare.pde.formal_feedback",
            "formal_surface_status": "ztare.pde.formal_surface_status",
            "applicability_cards": "ztare.pde.applicability_cards",
            "knowledge_service": "ztare.pde.knowledge_service",
            "completion_audit": "ztare.pde.completion_audit",
        },
        service_boundaries={
            "pde_subkernel": [
                "GP-219 PDE operation cards",
                "proof-currency ledger facade",
                "estimate skeleton facade",
                "receipt registry",
                "gate registry",
                "leaf work orders",
                "gate execution envelopes",
                "applicability cards",
                "formal-surface inventory",
            ],
            "leanmill_service": [
                "semantic premise shelf",
                "proof cache",
                "typed exits",
                "repair and attempt memory",
            ],
            "project_app": [
                "theorem profiles",
                "hostile packets",
                "source-specific receipts",
                "formal-surface rows",
            ],
            "rd_workbench": [
                "pack assembly",
                "markdown rendering",
                "legacy workbench flags",
                "project run orchestration",
            ],
        },
        architecture_requirements=pde_kernel_architecture_requirements(),
        architecture_requirement_status_counts=pde_kernel_requirement_status_counts(),
        capabilities=[
            f"expose {len(ops)} GP-219 PDE operation cards and execution templates",
            f"expose {len(receipts)} PDE receipt schemas for work units and gate payloads",
            "expose proof-currency ledger and exchange-rate obligations",
            "generate estimate skeletons through the stable PDE-kernel facade",
            "build registry-backed PDE leaf work orders",
            "execute gates by stable gate id",
            "execute all supplied gate payloads for a leaf work order",
            "adapt LeanMill formal-feedback services without merging theorem banks",
            "track formal-surface status without granting proof credit",
            "rank theorem-profile applicability cards with field-level missing/rejected data",
            "assemble LeanMill proof-cache/no-good/premise-shelf context without duplicating those stores",
            "run one executable PDE-kernel completion audit over registry, receipts, canary, summary, and boundaries",
        ],
        notes=[
            "The RD workbench is a consumer of this subkernel.",
            "LeanMill owns citable theorem/proof reuse and failure-memory services.",
            "Project apps own NS/TICK-specific theorem profiles and receipts.",
        ],
    )
    return asdict(status)
