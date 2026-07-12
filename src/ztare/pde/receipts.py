"""Receipt registry for the PDE subkernel.

This registry is declarative glue: it maps work-unit receipt types and gate
receipt payloads to their required fields and stable gate ids. It is not a
mathematical validator; the individual gates still own validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ztare.pde.registry import all_pde_gate_entries
from ztare.research_director.pde_estimate_craft_ops import (
    BASE_WORK_UNIT_TEMPLATES,
)


@dataclass(frozen=True)
class PDEReceiptRegistryEntry:
    receipt_id: str
    kind: str
    required_fields: tuple[str, ...]
    gate_id: str = ""
    workbench_flag: str = ""
    runner: str = ""
    renderer_section: str = ""
    input_shape_hint: str = ""
    dependency_edges: tuple[str, ...] = ()
    credit_boundary: str = "schema_only"


def pde_work_unit_receipt_entries() -> list[dict[str, Any]]:
    """Return receipt schemas for PDE work units."""
    entries: list[dict[str, Any]] = []
    for unit_type, template in BASE_WORK_UNIT_TEMPLATES.items():
        entries.append(asdict(PDEReceiptRegistryEntry(
            receipt_id=f"work_unit:{unit_type}",
            kind="work_unit",
            required_fields=tuple(template.required_fields),
            input_shape_hint=template.prompt,
            credit_boundary=(
                "shape_only; pde_work_unit_gate checks presence, not theorem truth"
            ),
        )))
    return entries


def pde_gate_receipt_entries() -> list[dict[str, Any]]:
    """Return receipt schemas derived from registry-backed gates."""
    entries: list[dict[str, Any]] = []
    for gate in all_pde_gate_entries():
        gate_id = str(gate.get("gate_id") or "")
        entries.append(asdict(PDEReceiptRegistryEntry(
            receipt_id=f"gate:{gate_id}",
            kind="gate_payload",
            required_fields=(),
            gate_id=gate_id,
            workbench_flag=str(gate.get("workbench_flag") or ""),
            runner=str(gate.get("runner") or ""),
            renderer_section=str(gate.get("renderer_section") or ""),
            input_shape_hint=str(gate.get("input_shape_hint") or ""),
            dependency_edges=tuple(str(op) for op in gate.get("requires_ops") or ()),
            credit_boundary="gate_runner_decides_pass_fail",
        )))
    return entries


def all_pde_receipt_entries() -> list[dict[str, Any]]:
    """Return work-unit and gate receipt registry entries."""
    return pde_work_unit_receipt_entries() + pde_gate_receipt_entries()
