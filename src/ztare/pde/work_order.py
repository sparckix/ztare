"""PDE leaf-agent work-order schema.

This module is the task boundary between the PDE kernel and worker agents.  A
caller supplies a target plus a GP-219 operation; the builder attaches the
registered gates, expected return fields, and optional formal-feedback lane
without embedding NS/TICK-specific assumptions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from ztare.pde.registry import (
    entries_for_op,
    entry_by_gate_id,
)


@dataclass(frozen=True)
class PDELeafWorkOrder:
    schema: str
    generated_utc: str
    leaf_id: str
    target: str
    op_id: str
    goal: str
    given: dict[str, Any]
    process_requirements: list[dict[str, Any]]
    gate_requirements: list[dict[str, Any]]
    must_return: dict[str, Any]
    formal_feedback_requested: bool
    notes: list[str]


def _stable_leaf_id(target: str, op_id: str) -> str:
    compact = "_".join(
        token for token in "".join(
            ch.lower() if ch.isalnum() else " " for ch in target
        ).split()[:8]
    )
    return f"pde.leaf.{op_id}.{compact or 'target'}"


def _dedupe_gates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        gate_id = str(entry.get("gate_id") or "")
        if not gate_id or gate_id in seen:
            continue
        seen.add(gate_id)
        out.append(entry)
    return out


def build_pde_leaf_work_order(
    *,
    target: str,
    op_id: str,
    goal: str = "",
    given: dict[str, Any] | None = None,
    only_gate_ids: list[str] | tuple[str, ...] = (),
    extra_gate_ids: list[str] | tuple[str, ...] = (),
    formal_feedback_requested: bool = False,
    require_process_contract: bool = False,
    pattern_action_contract_ref: str = "",
    orchestration_contract_ref: str = "",
    pencil_artifact_ref: str = "",
) -> dict[str, Any]:
    """Build an atomic PDE leaf work order from registry-backed gates."""
    gate_entries: list[dict[str, Any]] = []
    missing_only_gates: list[str] = []
    missing_extra_gates: list[str] = []
    if only_gate_ids:
        for gate_id in only_gate_ids:
            entry = entry_by_gate_id(str(gate_id))
            if entry:
                gate_entries.append(entry)
            else:
                missing_only_gates.append(str(gate_id))
    else:
        gate_entries = list(entries_for_op(op_id))
    for gate_id in extra_gate_ids:
        entry = entry_by_gate_id(str(gate_id))
        if entry:
            gate_entries.append(entry)
        else:
            missing_extra_gates.append(str(gate_id))
    gate_entries = _dedupe_gates(gate_entries)
    must_return = {
        "work_unit_type": (
            "estimate_derivation | theorem_applicability | "
            "falsifier_packet | formalization_attempt | smaller_theorem"
        ),
        "orientation_artifact": (
            "required for hard PDE/formal leaves; usually the pencil artifact"
        ),
        "target_inequality_or_statement": "required",
        "proof_steps": "required list",
        "first_failed_line_or_success": "required",
        "hostile_packet_tested": "required unless leaf is purely formal",
        "currency_exchange_used": "required when target currency changes",
        "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM | NEED_FORMALIZATION",
    }
    notes = [
        "gate_requirements are advisory work-order requirements; each gate still owns pass/fail",
        "formal feedback never grants PDE estimate credit",
    ]
    if only_gate_ids:
        notes.append("only_gate_ids supplied; op-default gates were not auto-attached")
    if missing_only_gates:
        notes.append(f"unknown_only_gate_ids={missing_only_gates}")
    if missing_extra_gates:
        notes.append(f"unknown_extra_gate_ids={missing_extra_gates}")
    process_requirements: list[dict[str, Any]] = []
    if require_process_contract:
        process_requirements = [
            {
                "artifact_key": "pattern_action_contract",
                "artifact_ref": str(pattern_action_contract_ref or ""),
                "required": True,
                "acceptance_check": (
                    "pattern action contract maps the residual to pattern chain, "
                    "anti-pattern guards, and required artifact slots"
                ),
            },
            {
                "artifact_key": "orchestration_contract",
                "artifact_ref": str(orchestration_contract_ref or ""),
                "required": True,
                "acceptance_check": (
                    "orchestration/menu contract validates selected residual edge, "
                    "rejected confuser, action program, and required next action"
                ),
            },
            {
                "artifact_key": "pencil_artifact",
                "artifact_ref": str(pencil_artifact_ref or ""),
                "required": True,
                "acceptance_check": (
                    "Gowers-first pencil artifact names eigenquestion, target "
                    "statement or obstruction, kill conditions, and formal surface"
                ),
            },
        ]
        missing_process = [
            item["artifact_key"] for item in process_requirements
            if not item["artifact_ref"]
        ]
        if missing_process:
            notes.append(f"missing_process_contract_refs={missing_process}")
    work_order = PDELeafWorkOrder(
        schema="pde-leaf-work-order-v1",
        generated_utc=datetime.now(timezone.utc).isoformat(),
        leaf_id=_stable_leaf_id(target, op_id),
        target=str(target or ""),
        op_id=str(op_id or ""),
        goal=str(goal or target or ""),
        given=dict(given or {}),
        process_requirements=process_requirements,
        gate_requirements=gate_entries,
        must_return=must_return,
        formal_feedback_requested=bool(formal_feedback_requested),
        notes=notes,
    )
    return asdict(work_order)


def render_pde_leaf_work_order(work_order: dict[str, Any]) -> str:
    """Render a compact PDE leaf work order for packs and dispatch prompts."""
    lines = [
        f"PDE leaf work order: `{work_order.get('leaf_id')}`",
        f"- op: `{work_order.get('op_id')}`",
        f"- target: {work_order.get('target')}",
        f"- goal: {work_order.get('goal')}",
        f"- formal feedback requested: `{work_order.get('formal_feedback_requested')}`",
    ]
    process_requirements = [
        item for item in work_order.get("process_requirements") or []
        if isinstance(item, dict)
    ]
    if process_requirements:
        lines.append("- process requirements:")
        for item in process_requirements:
            ref = item.get("artifact_ref") or "<missing>"
            lines.append(
                f"  - `{item.get('artifact_key')}` required={item.get('required')} "
                f"ref={ref}"
            )
    lines.append("- gates:")
    for gate in work_order.get("gate_requirements") or []:
        if not isinstance(gate, dict):
            continue
        lines.append(
            f"  - `{gate.get('gate_id')}` via `{gate.get('workbench_flag')}` "
            f"tags={list(gate.get('tags') or [])}"
        )
    lines.append("- must return:")
    for key, value in (work_order.get("must_return") or {}).items():
        lines.append(f"  - `{key}`: {value}")
    return "\n".join(lines)
