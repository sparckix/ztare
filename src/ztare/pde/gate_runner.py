"""Uniform runner for PDE registry-backed gates."""
from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from typing import Any

from ztare.pde.registry import entry_by_gate_id


@dataclass(frozen=True)
class PDEGateRunResult:
    schema: str
    gate_id: str
    runner: str
    passed: bool
    complete: bool
    registry_entry: dict[str, Any]
    input_shape_hint: str
    result: dict[str, Any]
    missing_fields: list[str]
    rejected_substitutes: list[str]
    violations: list[dict[str, Any]]
    provenance: list[dict[str, Any]]
    next_required_work_unit: dict[str, Any]
    next_required_work_units: list[dict[str, Any]]
    error: str


def _import_runner(runner: str):
    module_name, sep, func_name = runner.partition(":")
    if not sep or not module_name or not func_name:
        raise ValueError(f"invalid runner spec: {runner!r}")
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value in (None, ""):
        return []
    return [value]


def _work_unit_type(entry: dict[str, Any]) -> str:
    tags = {str(tag) for tag in _as_list(entry.get("tags"))}
    if "theorem_match" in tags or "profile_match" in tags:
        return "theorem_applicability"
    if "hostile_packet" in tags or "failure_witness" in tags:
        return "falsifier_packet"
    if "validated_numerics" in tags or "certificate" in tags:
        return "numerical_certificate"
    if "formal" in tags:
        return "formalization_attempt"
    if "same_carrier" in tags or "source_selection" in tags or "no_rebilling" in tags:
        return "positive_constructor_attempt"
    return "estimate_derivation"


def _provenance_for(entry: dict[str, Any], runner: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "pde_gate_registry_entry",
            "gate_id": entry.get("gate_id", ""),
            "workbench_flag": entry.get("workbench_flag", ""),
            "renderer_section": entry.get("renderer_section", ""),
            "requires_ops": list(entry.get("requires_ops") or []),
            "tags": list(entry.get("tags") or []),
        },
        {
            "kind": "pde_gate_runner",
            "runner": runner,
        },
    ]


def _next_required_work_unit(
    *,
    gate_id: str,
    entry: dict[str, Any],
    passed: bool,
    complete: bool,
    missing_fields: list[str],
    rejected_substitutes: list[str],
    error: str,
) -> dict[str, Any]:
    if passed and complete and not error:
        return {}
    action = "repair_gate_payload"
    if error == "missing gate payload":
        action = "supply_gate_payload"
    elif missing_fields:
        action = "supply_missing_fields"
    elif rejected_substitutes:
        action = "replace_rejected_substitutes"
    elif error:
        action = "repair_runner_or_payload"
    return {
        "schema": "pde-next-required-work-unit-v1",
        "gate_id": gate_id,
        "work_unit_type": _work_unit_type(entry),
        "action": action,
        "workbench_flag": entry.get("workbench_flag", ""),
        "input_shape_hint": entry.get("input_shape_hint", ""),
        "missing_fields": missing_fields,
        "rejected_substitutes": rejected_substitutes,
        "error": error,
        "must_return": {
            "target_inequality_or_statement": "required",
            "proof_steps": "required list",
            "first_failed_line_or_success": "required",
            "hostile_packet_tested": "required unless inapplicable",
            "currency_exchange_used": "required when target currency changes",
            "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM | NEED_FORMALIZATION",
        },
    }


def _normalize_result(
    *,
    gate_id: str,
    runner: str,
    result: dict[str, Any],
    entry: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    entry = dict(entry or {})
    verdict = str(result.get("verdict") or "")
    if "passed" in result:
        passed = bool(result.get("passed"))
    elif verdict:
        passed = verdict == "MATCH"
    else:
        passed = not error
    missing_fields = [str(x) for x in _as_list(result.get("missing_fields"))]
    rejected = [str(x) for x in _as_list(result.get("rejected_substitutes"))]
    violations = [
        item for item in _as_list(result.get("violations"))
        if isinstance(item, dict)
    ]
    if "complete" in result:
        complete = bool(result.get("complete"))
    elif verdict:
        complete = not missing_fields
    else:
        complete = passed
    if error:
        passed = False
        complete = False
    next_unit = _next_required_work_unit(
        gate_id=gate_id,
        entry=entry,
        passed=passed,
        complete=complete,
        missing_fields=missing_fields,
        rejected_substitutes=rejected,
        error=error,
    )
    gate_units = [
        item for item in _as_list(result.get("next_required_work_units"))
        if isinstance(item, dict)
    ]
    if next_unit and not gate_units:
        gate_units = [next_unit]
    return asdict(PDEGateRunResult(
        schema="pde-gate-run-result-v1",
        gate_id=gate_id,
        runner=runner,
        passed=passed,
        complete=complete,
        registry_entry=entry,
        input_shape_hint=str(entry.get("input_shape_hint") or ""),
        result=result,
        missing_fields=missing_fields,
        rejected_substitutes=rejected,
        violations=violations,
        provenance=_provenance_for(entry, runner) if entry else [],
        next_required_work_unit=next_unit,
        next_required_work_units=gate_units,
        error=error,
    ))


def run_pde_gate(
    gate_id: str,
    payload: dict[str, Any],
    *,
    theorem_db: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one PDE gate by registry id and return a normalized result envelope."""
    entry = entry_by_gate_id(gate_id)
    if not entry:
        return _normalize_result(
            gate_id=gate_id,
            runner="",
            result={},
            entry={},
            error=f"unknown PDE gate id: {gate_id}",
        )
    runner = str(entry.get("runner") or "")
    try:
        if gate_id == "G-PDE-THEOREM-APPLICABILITY":
            if theorem_db is None:
                return _normalize_result(
                    gate_id=gate_id,
                    runner=runner,
                    result={},
                    entry=entry,
                    error="theorem_db is required for theorem applicability",
                )
            from ztare.research_director.theorem_applicability_db import (
                match_theorem_applicability,
            )

            result = match_theorem_applicability(
                str(payload.get("theorem") or payload.get("theorem_id") or ""),
                payload.get("available") if isinstance(payload.get("available"), dict) else {},
                theorem_db,
            )
        elif gate_id == "G-OWNER-PREIMAGE-PREFIX":
            func = _import_runner(runner)
            if "owner_preimage_receipts" in payload:
                rubric_data = payload
            else:
                rubric_data = {"owner_preimage_receipts": [payload]}
            result = func(rubric_data, expect_receipt=True)
        else:
            func = _import_runner(runner)
            result = func(payload)
        if not isinstance(result, dict):
            return _normalize_result(
                gate_id=gate_id,
                runner=runner,
                result={"raw_result": result},
                entry=entry,
                error=f"gate runner returned {type(result).__name__}, expected dict",
            )
        return _normalize_result(
            gate_id=gate_id,
            runner=runner,
            result=result,
            entry=entry,
        )
    except Exception as exc:  # pragma: no cover - defensive envelope
        return _normalize_result(
            gate_id=gate_id,
            runner=runner,
            result={},
            entry=entry,
            error=f"{type(exc).__name__}: {exc}",
        )


def run_pde_leaf_work_order_gates(
    work_order: dict[str, Any],
    payloads_by_gate_id: dict[str, dict[str, Any]],
    *,
    theorem_db: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all gate payloads supplied for a PDE leaf work order."""
    process_units: list[dict[str, Any]] = []
    process_missing: list[str] = []
    for item in work_order.get("process_requirements") or []:
        if not isinstance(item, dict) or not item.get("required"):
            continue
        artifact_key = str(item.get("artifact_key") or "")
        artifact_ref = str(item.get("artifact_ref") or "")
        if artifact_key and not artifact_ref:
            process_missing.append(artifact_key)
            process_units.append({
                "schema": "pde-next-required-work-unit-v1",
                "gate_id": "PDE-PROCESS-CONTRACT",
                "work_unit_type": "process_contract_artifact",
                "action": "supply_process_artifact_ref",
                "artifact_key": artifact_key,
                "acceptance_check": str(item.get("acceptance_check") or ""),
                "must_return": {
                    "orientation_artifact": "required",
                    "pattern_action_contract": "required when hard PDE leaf",
                    "orchestration_contract": "required when hard PDE leaf",
                    "verdict": "CLOSE | FAIL | SHRINK | NEED_THEOREM",
                },
            })
    results = []
    for gate in work_order.get("gate_requirements") or []:
        if not isinstance(gate, dict):
            continue
        gate_id = str(gate.get("gate_id") or "")
        payload = payloads_by_gate_id.get(gate_id)
        if payload is None:
            results.append(_normalize_result(
                gate_id=gate_id,
                runner=str(gate.get("runner") or ""),
                result={},
                entry=gate,
                error="missing gate payload",
            ))
            continue
        results.append(run_pde_gate(gate_id, payload, theorem_db=theorem_db))
    next_units: list[dict[str, Any]] = []
    next_units.extend(process_units)
    for item in results:
        item_units: list[dict[str, Any]] = []
        for unit in _as_list(item.get("next_required_work_units")):
            if isinstance(unit, dict) and unit:
                item_units.append(unit)
                next_units.append(unit)
        fallback = item.get("next_required_work_unit")
        if (
            not item_units
            and isinstance(fallback, dict)
            and fallback
            and fallback not in next_units
        ):
            next_units.append(fallback)
    failed = [item for item in results if not item.get("passed")]
    incomplete = [item for item in results if not item.get("complete")]
    rejected: list[str] = []
    missing_fields: list[str] = []
    for item in results:
        for field in _as_list(item.get("missing_fields")):
            text = str(field)
            if text and text not in missing_fields:
                missing_fields.append(text)
        for substitute in _as_list(item.get("rejected_substitutes")):
            text = str(substitute)
            if text and text not in rejected:
                rejected.append(text)
    return {
        "schema": "pde-leaf-gate-run-bundle-v1",
        "leaf_id": work_order.get("leaf_id", ""),
        "passed": (
            all(item["passed"] for item in results) if results else False
        ) and not process_missing,
        "complete": (
            all(item["complete"] for item in results) if results else False
        ) and not process_missing,
        "summary": {
            "process_contract_passed": not process_missing,
            "missing_process_artifacts": process_missing,
            "gate_count": len(results),
            "passed_gate_ids": [
                item["gate_id"] for item in results if item.get("passed")
            ],
            "failed_gate_ids": [item["gate_id"] for item in failed],
            "incomplete_gate_ids": [item["gate_id"] for item in incomplete],
            "missing_field_names": missing_fields,
            "rejected_substitutes": rejected,
            "next_required_work_unit_count": len(next_units),
        },
        "missing_payload_gate_ids": [
            item["gate_id"] for item in results
            if item.get("error") == "missing gate payload"
        ],
        "next_required_work_units": next_units,
        "results": results,
    }
