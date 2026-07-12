"""Executable completion audit for the PDE kernel."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ztare.pde.architecture_requirements import pde_kernel_architecture_requirements
from ztare.pde.gate_runner import run_pde_leaf_work_order_gates
from ztare.pde.readiness import build_pde_kernel_readiness_receipt
from ztare.pde.receipts import all_pde_receipt_entries
from ztare.pde.registry import all_pde_gate_entries, entries_for_op
from ztare.pde.subkernel import build_pde_subkernel_status


REQUIRED_ROOT_PDE_VERBS = {
    "status",
    "completion-audit",
    "requirements",
    "readiness",
    "ops",
    "currency",
    "estimates",
    "receipts",
    "gates",
    "run-gate",
    "work-order",
    "run-work-order",
    "context",
    "knowledge",
    "formal-surface",
    "canary-report",
}


@dataclass(frozen=True)
class PDECompletionAuditCheck:
    check_id: str
    passed: bool
    evidence: dict[str, Any]
    failure: str = ""


def _check(check_id: str, passed: bool, evidence: dict[str, Any], failure: str = "") -> dict[str, Any]:
    return asdict(PDECompletionAuditCheck(
        check_id=check_id,
        passed=bool(passed),
        evidence=evidence,
        failure="" if passed else failure,
    ))


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def _contains_text(root: Path, needle: str) -> list[str]:
    offenders: list[str] = []
    for path in _python_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if needle in text:
            offenders.append(str(path))
    return offenders


def _root_pde_verbs(root: Path) -> set[str]:
    cli_file = root / "src" / "ztare" / "cli.py"
    if not cli_file.exists():
        return set()
    text = cli_file.read_text(encoding="utf-8")
    start = text.find("_PDE_VERBS = (")
    if start < 0:
        return set()
    end = text.find(")", start)
    if end < 0:
        return set()
    block = text[start:end]
    verbs: set[str] = set()
    for line in block.splitlines():
        stripped = line.strip().strip(",")
        if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
            verbs.add(stripped[1:-1])
    return verbs


def _bundle_summary_probe() -> dict[str, Any]:
    work_order = {
        "schema": "pde-leaf-work-order-v1",
        "leaf_id": "pde.leaf.audit.equality_provenance",
        "gate_requirements": [
            {
                "gate_id": "G-PDE-EQUALITY-PROVENANCE",
                "runner": (
                    "ztare.gates.pde_equality_provenance_gate:"
                    "run_pde_equality_provenance_gate"
                ),
                "input_shape_hint": "{}",
            }
        ],
    }
    payloads = {
        "G-PDE-EQUALITY-PROVENANCE": {
            "equality_target": "A = B",
            "left_stream": "A",
            "right_stream": "B",
            "provenance_kind": "record_field_projection",
            "constructor_or_theorem": "assumed carrier",
            "generated_fields": ["A", "B"],
            "source_binding": "not supplied",
            "anti_proxy_or_anti_laundering_fields": "not supplied",
            "hostile_packet_or_confuser": "proxy stream packet",
            "proof_boundary": "audit fixture",
            "field_projection_only": True,
        }
    }
    return run_pde_leaf_work_order_gates(work_order, payloads, theorem_db={})


def build_pde_kernel_completion_audit(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return a machine-checkable completion audit for PDE-kernel readiness.

    The audit checks executable surfaces, not mathematical truth. It is the
    kernel-level guard before a project app claims the PDE engine is ready for
    hard leaf work.
    """
    status = build_pde_subkernel_status()
    requirements = pde_kernel_architecture_requirements()
    gates = all_pde_gate_entries()
    receipts = all_pde_receipt_entries()
    receipt_ids = {str(row.get("receipt_id") or "") for row in receipts}
    gate_ids = {str(row.get("gate_id") or "") for row in gates}
    pec_l_gate_ids = {str(row.get("gate_id") or "") for row in entries_for_op("pec_l")}
    readiness = build_pde_kernel_readiness_receipt()
    readiness_gate_ids = {
        str(row.get("gate_id") or "")
        for row in readiness.get("canary_work_order", {}).get("gate_requirements", [])
        if isinstance(row, dict)
    }
    bundle = _bundle_summary_probe()
    summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    checks: list[dict[str, Any]] = []

    checks.append(_check(
        "subkernel_status_ready",
        bool(status.get("ready")),
        {
            "gate_count": status.get("gate_count"),
            "runner_import_errors": status.get("runner_import_errors", []),
        },
        "PDE subkernel status is not ready.",
    ))
    checks.append(_check(
        "all_architecture_requirements_implemented",
        all(row.get("status") == "implemented" for row in requirements),
        {
            "requirement_ids": [row.get("requirement_id") for row in requirements],
            "status_counts": status.get("architecture_requirement_status_counts", {}),
        },
        "At least one architecture requirement is not implemented.",
    ))
    checks.append(_check(
        "receipt_registry_covers_all_gates",
        all(f"gate:{gate_id}" in receipt_ids for gate_id in gate_ids),
        {
            "gate_count": len(gate_ids),
            "receipt_count": len(receipt_ids),
            "missing_gate_receipts": sorted(
                gate_id for gate_id in gate_ids
                if f"gate:{gate_id}" not in receipt_ids
            ),
        },
        "At least one registry gate has no receipt registry entry.",
    ))
    core_pec_l = {
        "G-PDE-ANALYTIC-SUBSTANCE",
        "G-PDE-PHYSICAL-ACCOUNTING",
        "G-PDE-EQUALITY-PROVENANCE",
        "G-PDE-OPERATOR-ADMISSIBILITY",
    }
    checks.append(_check(
        "pec_l_core_pde_gates_present",
        core_pec_l.issubset(pec_l_gate_ids),
        {
            "required": sorted(core_pec_l),
            "actual": sorted(pec_l_gate_ids),
        },
        "pec_l is missing at least one core analytic/physical/equality/operator gate.",
    ))
    checks.append(_check(
        "readiness_canary_requires_core_gates",
        core_pec_l.issubset(readiness_gate_ids),
        {
            "required": sorted(core_pec_l),
            "actual": sorted(readiness_gate_ids),
        },
        "The readiness canary work order is missing a core PDE gate.",
    ))
    summary_keys = {
        "gate_count",
        "passed_gate_ids",
        "failed_gate_ids",
        "incomplete_gate_ids",
        "missing_field_names",
        "rejected_substitutes",
        "next_required_work_unit_count",
    }
    checks.append(_check(
        "gate_bundle_summary_contract",
        summary_keys.issubset(set(summary))
        and summary.get("gate_count") == 1
        and summary.get("next_required_work_unit_count", 0) >= 1,
        {
            "summary": summary,
            "bundle_passed": bundle.get("passed"),
        },
        "Gate bundle summary is missing or not populated.",
    ))
    checks.append(_check(
        "leanmill_adapter_boundary_declared",
        "leanmill_service" in status.get("service_boundaries", {}),
        {
            "service_boundaries": sorted((status.get("service_boundaries") or {}).keys()),
        },
        "LeanMill service boundary is absent from status.",
    ))
    checks.append(_check(
        "project_app_boundary_declared",
        "project_app" in status.get("service_boundaries", {}),
        {
            "service_boundaries": sorted((status.get("service_boundaries") or {}).keys()),
        },
        "Project app boundary is absent from status.",
    ))

    root = Path(repo_root) if repo_root else None
    if root is not None:
        root_verbs = _root_pde_verbs(root)
        checks.append(_check(
            "root_cli_exposes_full_pde_surface",
            REQUIRED_ROOT_PDE_VERBS.issubset(root_verbs),
            {
                "required": sorted(REQUIRED_ROOT_PDE_VERBS),
                "actual": sorted(root_verbs),
                "missing": sorted(REQUIRED_ROOT_PDE_VERBS - root_verbs),
            },
            "Root ztare pde command surface is missing one or more PDE verbs.",
        ))
        leanmill_offenders = _contains_text(root / "src" / "ztare" / "leanmill", "ztare.pde")
        project_app_marker = "ns_" + "millennium_hunt"
        pde_ns_offenders = _contains_text(root / "src" / "ztare" / "pde", project_app_marker)
        checks.append(_check(
            "leanmill_does_not_import_pde_kernel",
            not leanmill_offenders,
            {"offenders": leanmill_offenders},
            "LeanMill imports ztare.pde.",
        ))
        checks.append(_check(
            "pde_kernel_does_not_import_ns_app",
            not pde_ns_offenders,
            {"offenders": pde_ns_offenders},
            "PDE kernel imports NS project app data.",
        ))

    failed = [row for row in checks if not row.get("passed")]
    return {
        "schema": "pde-kernel-completion-audit-v1",
        "passed": not failed,
        "checks": checks,
        "failed_check_ids": [row.get("check_id") for row in failed],
        "status_ready": bool(status.get("ready")),
        "requirement_count": len(requirements),
        "gate_count": len(gates),
        "receipt_count": len(receipts),
        "readiness_ready": bool(readiness.get("ready")),
        "credit_boundary": (
            "completion audit proves kernel surfaces and routing contracts only; "
            "it does not certify any PDE estimate or project theorem"
        ),
    }
