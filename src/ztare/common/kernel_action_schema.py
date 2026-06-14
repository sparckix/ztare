"""Common action-schema contract for kernel primitives.

This is the shared shape for surfaces that propose next work inside or around
autoresearch: failed-branch memory, pattern contracts, primitive retrieval,
structural transfer, and future mutator lanes. The producer may differ, but the
consumer should see the same required fields.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


REQUIRED_KERNEL_ACTION_FIELDS = (
    "target_mapping",
    "nearest_confuser",
    "falsifier",
    "verification_artifact",
)


@dataclass(frozen=True)
class KernelActionSchema:
    schema_version: int = 1
    record_type: str = "kernel_action_schema"
    source_kind: str = "unknown"
    action_family: str = "unknown"
    action_name: str = "unknown"
    source_summary: str = ""
    target_mapping: str = "unset"
    nearest_confuser: str = "unset"
    falsifier: str = "unset"
    verification_artifact: str = "unset"
    action_constraints: list[str] = field(default_factory=list)
    evidence_basis: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def missing_required_fields(action: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_KERNEL_ACTION_FIELDS:
        value = str(action.get(field_name) or "").strip()
        if not value or value == "unset":
            missing.append(field_name)
    return missing


def validate_kernel_action_schema(action: dict[str, Any]) -> tuple[bool, list[str]]:
    if action.get("record_type") not in {
        "kernel_action_schema",
        "structural_transfer_action_schema",
    }:
        return False, ["record_type"]
    missing = missing_required_fields(action)
    return not missing, missing


def render_action_schema_prompt_lines(action: dict[str, Any]) -> list[str]:
    lines = [
        "Action schema required before use:",
        f"target_mapping={action.get('target_mapping')}",
        f"nearest_confuser={action.get('nearest_confuser')}",
        f"falsifier={action.get('falsifier')}",
        f"verification_artifact={action.get('verification_artifact')}",
    ]
    missing = missing_required_fields(action)
    if missing:
        lines.append(f"missing_fields={missing}")
    return lines
