#!/usr/bin/env python3
"""Shared strict C-supply credit classification helpers."""
from __future__ import annotations

from typing import Any

STATIC_ARMS = ("public_tool_static", "governed_public_tool_static")
STRICT_C_PROBE_VERIFIED_STATUS = "c_discriminating_probe_verified"
PENDING_STATIC_C_PROBE_VERIFIED_STATUS = "c_discriminating_probe_verified_pending_static_sweep"
MATHLIB_EXISTING_DECL_MATERIALIZATION = "mathlib_existing_decl_snapshot"


def static_sweep_owed_row(row: dict[str, Any]) -> bool:
    if row.get("static_sweep_required_before_c_credit"):
        return True
    static = row.get("static_tools_result") if isinstance(row.get("static_tools_result"), dict) else {}
    if str(static.get("status") or "") == "unknown_not_run":
        return True
    missing = static.get("missing_static_arms")
    if isinstance(missing, list):
        return bool(missing)
    present = static.get("present_arms")
    if isinstance(present, list):
        # An EMPTY present_arms means the sweep recorded zero arms -> the
        # required static arms are absent -> sweep is OWED. (The old
        # `and present` short-circuit treated [] as "not owed", which could
        # grant strict-C credit to a row with no static arms.)
        return not set(STATIC_ARMS).issubset({str(x) for x in present})
    return False


def existing_mathlib_target_row(row: dict[str, Any]) -> bool:
    if row.get("existing_mathlib_target"):
        return True
    if str(row.get("strict_c_credit_disqualified_reason") or "") == "existing_mathlib_target_snapshot":
        return True
    materialization = row.get("source_materialization") if isinstance(row.get("source_materialization"), dict) else {}
    return bool(
        materialization.get("existing_mathlib_target")
        or str(materialization.get("materialization_source") or "") == MATHLIB_EXISTING_DECL_MATERIALIZATION
        or str(materialization.get("strict_c_credit_disqualified_reason") or "") == "existing_mathlib_target_snapshot"
    )


def strict_credit_disqualified_row(row: dict[str, Any]) -> bool:
    return existing_mathlib_target_row(row)


def strict_credit_ready_row(row: dict[str, Any]) -> bool:
    status = str(row.get("c_discriminating_evidence_status") or "")
    return bool(
        row.get("probe_credit_ready")
        and status == STRICT_C_PROBE_VERIFIED_STATUS
        and not row.get("static_sweep_required_before_c_credit")
        and not static_sweep_owed_row(row)
        and not strict_credit_disqualified_row(row)
    )


def probe_verified_row(row: dict[str, Any]) -> bool:
    status = str(row.get("c_discriminating_evidence_status") or "")
    return bool(
        not strict_credit_disqualified_row(row)
        and (row.get("probe_credit_ready") or status in {STRICT_C_PROBE_VERIFIED_STATUS, PENDING_STATIC_C_PROBE_VERIFIED_STATUS})
    )


def probe_verified_pending_static_row(row: dict[str, Any]) -> bool:
    status = str(row.get("c_discriminating_evidence_status") or "")
    return bool(
        probe_verified_row(row)
        and not strict_credit_disqualified_row(row)
        and not strict_credit_ready_row(row)
        and (
            status == PENDING_STATIC_C_PROBE_VERIFIED_STATUS
            or row.get("static_sweep_required_before_c_credit")
            or static_sweep_owed_row(row)
        )
    )
