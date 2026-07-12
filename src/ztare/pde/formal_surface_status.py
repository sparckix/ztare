"""Formal-surface status inventory for PDE leaf agents.

This module tracks where a PDE analytic primitive sits on the formalization
ladder. It is an inventory and routing aid, not proof credit: LeanMill remains
the owner of citable proof material and kernel verification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


FORMAL_SURFACE_STATUSES = {
    "absent",
    "informal_only",
    "lean_statement_only",
    "lean_proof_complete",
    "external_citation",
    "numerical_certificate",
}


@dataclass(frozen=True)
class PDEFormalSurfaceRecord:
    schema: str
    primitive_id: str
    title: str
    status: str
    source_profile: str
    evidence_complete: bool
    missing_evidence: list[str]
    statement: str
    lean_decl: str
    lean_file: str
    proof_artifact: str
    citation: str
    certificate_artifact: str
    validator: str
    dependencies: list[str]
    gaps: list[str]
    notes: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def _compile_success(record: dict[str, Any]) -> bool:
    compile_result = record.get("compile_result")
    if isinstance(compile_result, dict) and compile_result.get("success") is True:
        return True
    axiom_audit = record.get("axiom_audit")
    if isinstance(axiom_audit, dict) and axiom_audit.get("success") is True:
        return True
    return False


def _missing_evidence(record: dict[str, Any], status: str) -> list[str]:
    missing: list[str] = []
    if not _text(record.get("primitive_id")):
        missing.append("primitive_id")
    if status not in FORMAL_SURFACE_STATUSES:
        missing.append("recognized_status")
        return missing
    if status == "lean_statement_only":
        if not (_text(record.get("statement")) or _text(record.get("lean_decl"))):
            missing.append("statement_or_lean_decl")
        if not _text(record.get("lean_file")):
            missing.append("lean_file")
    elif status == "lean_proof_complete":
        if not _text(record.get("lean_decl")):
            missing.append("lean_decl")
        if not _text(record.get("lean_file")):
            missing.append("lean_file")
        if not (_text(record.get("proof_artifact")) or _compile_success(record)):
            missing.append("proof_artifact_or_compile_success")
    elif status == "external_citation":
        if not _text(record.get("citation")):
            missing.append("citation")
    elif status == "numerical_certificate":
        if not _text(record.get("certificate_artifact")):
            missing.append("certificate_artifact")
        if not _text(record.get("validator")):
            missing.append("validator")
    return missing


def normalize_pde_formal_surface_record(
    record: dict[str, Any],
    *,
    default_source_profile: str = "unknown",
) -> dict[str, Any]:
    """Normalize one PDE formal-surface status row."""
    status = _text(record.get("status")) or "informal_only"
    missing = _missing_evidence(record, status)
    normalized = PDEFormalSurfaceRecord(
        schema="pde-formal-surface-record-v1",
        primitive_id=_text(record.get("primitive_id")),
        title=_text(record.get("title")) or _text(record.get("primitive_id")),
        status=status,
        source_profile=_text(record.get("source_profile")) or default_source_profile,
        evidence_complete=not missing,
        missing_evidence=missing,
        statement=_text(record.get("statement")),
        lean_decl=_text(record.get("lean_decl")),
        lean_file=_text(record.get("lean_file")),
        proof_artifact=_text(record.get("proof_artifact")),
        citation=_text(record.get("citation")),
        certificate_artifact=_text(record.get("certificate_artifact")),
        validator=_text(record.get("validator")),
        dependencies=_string_list(record.get("dependencies")),
        gaps=_string_list(record.get("gaps")),
        notes=_text(record.get("notes")),
    )
    return asdict(normalized)


def build_pde_formal_surface_map(
    records: list[dict[str, Any]],
    *,
    target: str = "",
    required_primitives: list[str] | tuple[str, ...] = (),
    source_profile: str = "unknown",
) -> dict[str, Any]:
    """Build a formal-surface inventory map for a PDE target."""
    normalized = [
        normalize_pde_formal_surface_record(
            record,
            default_source_profile=source_profile,
        )
        for record in records
        if isinstance(record, dict)
    ]
    by_id = {
        str(record.get("primitive_id")): record
        for record in normalized
        if record.get("primitive_id")
    }
    required = [str(item) for item in required_primitives if str(item).strip()]
    missing_required = [item for item in required if item not in by_id]
    status_counts: dict[str, int] = {}
    incomplete_records: list[str] = []
    for record in normalized:
        status = str(record.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if not record.get("evidence_complete"):
            incomplete_records.append(str(record.get("primitive_id") or "?"))
    next_actions: list[str] = []
    for primitive_id in missing_required:
        next_actions.append(f"add formal-surface row for `{primitive_id}`")
    for record in normalized:
        if record.get("evidence_complete"):
            continue
        primitive_id = str(record.get("primitive_id") or "?")
        missing = ", ".join(str(item) for item in record.get("missing_evidence") or [])
        next_actions.append(f"complete `{primitive_id}` evidence: {missing}")
    return {
        "schema": "pde-formal-surface-map-v1",
        "target": str(target or ""),
        "source_profile": str(source_profile or "unknown"),
        "records": normalized,
        "required_primitives": required,
        "missing_required_primitives": missing_required,
        "status_counts": dict(sorted(status_counts.items())),
        "incomplete_records": incomplete_records,
        "next_required_actions": next_actions,
        "credit_boundary": (
            "inventory_only_no_proof_credit; LeanMill/kernel checks certify "
            "formal proof reuse, PDE gates certify estimate obligations"
        ),
    }


def render_pde_formal_surface_map(surface_map: dict[str, Any]) -> str:
    """Render a compact formal-surface map for workbench markdown."""
    if not surface_map:
        return "- (not requested)"
    lines = [
        f"- Schema: `{surface_map.get('schema')}`",
        f"- Status counts: `{surface_map.get('status_counts', {})}`",
        f"- Missing required: `{surface_map.get('missing_required_primitives', [])}`",
        f"- Credit boundary: {surface_map.get('credit_boundary')}",
    ]
    records = surface_map.get("records") or []
    if records:
        lines.append("- Surface rows:")
        for record in records[:12]:
            missing = record.get("missing_evidence") or []
            suffix = f"; missing={missing}" if missing else ""
            lines.append(
                f"  - `{record.get('primitive_id')}` "
                f"status=`{record.get('status')}` complete="
                f"`{record.get('evidence_complete')}`{suffix}"
            )
    actions = surface_map.get("next_required_actions") or []
    if actions:
        lines.append("- Next required actions:")
        for action in actions[:8]:
            lines.append(f"  - {action}")
    return "\n".join(lines)
