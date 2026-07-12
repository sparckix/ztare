"""PDE estimate-craft operation facade.

The GP-219 vocabulary remains authored in the legacy research-director module.
This facade is the kernel import path for callers that need operation cards,
portable receipt fields, or execution templates without depending on the RD
workbench package boundary.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ztare.research_director import pde_estimate_craft_ops as _legacy


def all_pde_ops() -> list[dict[str, Any]]:
    """Return every GP-219 PDE operation as plain JSON-ready dictionaries."""
    return [asdict(op) for op in _legacy.VOCABULARY_GP219]


def pde_op_by_id(op_id: str) -> dict[str, Any] | None:
    """Return one GP-219 PDE operation by id."""
    op = _legacy.get(op_id)
    return asdict(op) if op else None


def deployable_pde_ops() -> list[dict[str, Any]]:
    """Return operations that already have a deterministic gate."""
    return [asdict(op) for op in _legacy.deployable_gates()]


def portable_receipt_pde_ops() -> list[dict[str, Any]]:
    """Return operations treated as portable receipt-schema candidates."""
    return [asdict(op) for op in _legacy.portable_receipt_candidates()]


def pde_execution_template_for_ops(op_ids: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Return work-unit templates and execution hints for a set of op ids."""
    return _legacy.execution_template_for_ops([str(op_id) for op_id in op_ids])


def render_pde_ops_summary() -> str:
    """Render the one-screen GP-219 summary from the canonical vocabulary."""
    return _legacy.render_vocabulary_summary()
