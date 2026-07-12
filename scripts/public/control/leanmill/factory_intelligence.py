#!/usr/bin/env python3
"""LeanMill action-intelligence read model.

This is the single factory-brain surface for local 24x7 LeanMill operation. It
does not execute Lean, call models, or mutate the scientific registry. It
projects the SQLite WorkItem queue, JSONL event ledger, station contract, and
observability receipt into:

- lead/cycle-time metrics by subprocess and station;
- loss accounting for rejected/held work;
- value-flow counts for typed learning-unit exits;
- a ranked next-action list.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import leanmill_work_queue as work_queue
import leanmill_learning_feedback_contract as learning_feedback
from leanmill_c_supply_credit import (
    probe_verified_pending_static_row as _c_supply_probe_verified_pending_static_row,
    probe_verified_row as _c_supply_probe_verified_row,
    strict_credit_ready_row as _c_supply_credit_ready_row,
)
from src.ztare.leanmill.common import read_json, sha256_file, write_json_atomic, write_text_atomic
from src.ztare.leanmill.contracts import handoff as handoff_contract
from src.ztare.leanmill.policy import c_supply_breadth_policy_from_policy, lane_budget_plan, priority_policy_from_policy
from src.ztare.leanmill.run_observability import (
    DEFAULT_ATTEMPTS_DB as DEFAULT_RUN_OBSERVABILITY_ATTEMPTS_DB,
    DEFAULT_AXIOM_PACKS as DEFAULT_RUN_OBSERVABILITY_AXIOM_PACKS,
    DEFAULT_BANK_ATTEMPTS as DEFAULT_RUN_OBSERVABILITY_BANK_ATTEMPTS,
    DEFAULT_COT_TRACES as DEFAULT_RUN_OBSERVABILITY_COT_TRACES,
    DEFAULT_DECOMPOSITION_CACHE as DEFAULT_RUN_OBSERVABILITY_DECOMPOSITION_CACHE,
    DEFAULT_FAITHFULNESS_STORE as DEFAULT_RUN_OBSERVABILITY_FAITHFULNESS,
    DEFAULT_FORMALIZE_ATTEMPTS as DEFAULT_RUN_OBSERVABILITY_FORMALIZE_ATTEMPTS,
    DEFAULT_NO_GOOD_STORE as DEFAULT_RUN_OBSERVABILITY_NO_GOOD,
    DEFAULT_NOTES_TRACE as DEFAULT_RUN_OBSERVABILITY_NOTES_TRACE,
    DEFAULT_PROOF_CACHE as DEFAULT_RUN_OBSERVABILITY_PROOF_CACHE,
    DEFAULT_VERDICTS as DEFAULT_RUN_OBSERVABILITY_VERDICTS,
)
from src.ztare.leanmill.typed_exit import typed_exit_summary
from leanmill_paths import DATA_DIR as DEFAULT_DATA_DIR
from leanmill_paths import FACTORY_POLICY as DEFAULT_FACTORY_POLICY
from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REPAIR_REGISTRY


DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_MD = f"{DEFAULT_DATA_DIR}/leanmill_factory_intelligence.md"
DEFAULT_OBSERVABILITY = f"{DEFAULT_DATA_DIR}/leanmill_observability.json"
DEFAULT_STATION_HEALTH = f"{DEFAULT_DATA_DIR}/station_health_dashboard.json"
DEFAULT_CONTRACT = f"{DEFAULT_DATA_DIR}/station_action_contract.json"
DEFAULT_SOURCE_SEARCH_INTEGRATIONS = f"{DEFAULT_DATA_DIR}/source_search_integrations"
DEFAULT_FAMILY_SPEC_GATE = f"{DEFAULT_DATA_DIR}/family_spec_gate.json"
DEFAULT_BACKLOG_REPLENISHER = f"{DEFAULT_DATA_DIR}/backlog_replenisher_status.json"
DEFAULT_C_SUPPLY_BATCH_STATUS = f"{DEFAULT_DATA_DIR}/c_supply_batch_status.json"
DEFAULT_C_SUPPLY_EXPOST_CLEANER = f"{DEFAULT_DATA_DIR}/c_supply_batch_expost_cleaner.json"
DEFAULT_C_SUPPLY_CLEAN_SELECTION = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_C_SUPPLY_GROWTH_STATUS = f"{DEFAULT_DATA_DIR}/c_supply_growth_controller.json"
DEFAULT_AGENTIC_PORTFOLIO = f"{DEFAULT_DATA_DIR}/agentic_portfolio_controller.json"
DEFAULT_C_SUPPLY_SOURCE_MATERIALIZATION = f"{DEFAULT_DATA_DIR}/c_supply_source_materialization.json"
DEFAULT_C_SUPPLY_UPSTREAM_RATER = f"{DEFAULT_DATA_DIR}/c_supply_upstream_rater.json"
DEFAULT_TYPED_PROOF_EXITS = f"{DEFAULT_DATA_DIR}/typed_proof_exits.json"
DEFAULT_POPULATION_ELO = f"{DEFAULT_DATA_DIR}/leanmill_population_elo.json"
DEFAULT_HELDOUT_SCOUT = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.json"
DEFAULT_EVALUATION_HARNESS_PREP = f"{DEFAULT_DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_EVALUATION_HARNESS_RUN = f"{DEFAULT_DATA_DIR}/evaluation_harness_run.json"
DEFAULT_EVALUATION_NO_LIFT_REPORT = f"{DEFAULT_DATA_DIR}/evaluation_harness_no_lift_report.json"
DEFAULT_MECHANISM_VS_OVERCLAIM_REPORT = f"{DEFAULT_DATA_DIR}/mechanism_vs_overclaim_report.json"
DEFAULT_COMPETITIVE_INVENTORY = f"{DEFAULT_DATA_DIR}/leanmill_competitive_inventory.json"
DEFAULT_PR_A1_PUBLIC_REVIEW = f"{DEFAULT_DATA_DIR}/pr_a1_public_artifact_review.json"
SUBSCRIPTION_AGENT_KINDS = {
    "agent_repair_task",
    "source_scout_task",
    "subscription_agent_task",
    "agent_task",
    "agent_repair",
}

TERMINAL_STATUSES = {"done", "failed", "retired", "dead_letter"}
OPEN_STATUSES = {"queued", "claimed", "running"}
OPS_EXIT_KINDS = {
    "governance_control_refresh",
    "governance_shape_checked",
    "qualified_source_inventory",
    "residual_source_plan_refreshed",
    "canary_spec_validated",
}
PROOF_VALUE_EXIT_KINDS = set(learning_feedback.PROOF_VALUE_EXIT_KINDS)
TESTED_LEARNING_EXIT_KINDS = set(learning_feedback.TESTED_LEARNING_EXIT_KINDS)
TERMINAL_DECISION_EXIT_KINDS = set(learning_feedback.TERMINAL_DECISION_EXIT_KINDS) | {
    "gm_hold_review",
    "gm_retire_decision",
    "operator_required",
    "retired",
    "retired_no_spend_until_new_evidence",
    "retired_source_strategy_repair_required",
}
INTERMEDIATE_EXIT_KINDS = OPS_EXIT_KINDS | {
    "agent_proposed_exact_gap_candidate",
    "agent_repair_attempt_finished",
    "canary_validation_failed",
    "governance_rejected",
    "proposal_rejected",
    "proposal_validated",
    "probe_failed",
    "qualified_source_candidates",
    "source_binding_compiled",
    "source_search_integrated",
    "source_search_integrated_hold",
}

STATION_KIND_MAP = {
    "source_qualification": {
        "kinds": {
            "station:source_qualification",
            "source_inventory_refresh",
            "source_request_propose",
            "source_search_task",
            "source_scout_task",
        },
        "sla_p95_s": 120,
    },
    "intake_buffer": {
        "kinds": {"station:intake_buffer"},
        "sla_p95_s": 30,
    },
    "proof_execution": {
        "kinds": {"repair_canary_probe", "proof_probe", "station:proof_execution"},
        "sla_p95_s": 300,
    },
    "governance_gate": {
        "kinds": {"governance_refresh", "govern_closure_candidate", "govern_exact_gap", "govern_falsifier", "station:governance_gate"},
        "sla_p95_s": 60,
    },
    "residual_curriculum": {
        "kinds": {
            "station:residual_curriculum",
            "canary_validation_refresh",
            "canary_validate",
            "canary_propose",
            "decomposition_propose",
            "llm_proposal_validate",
            "residual_source_plan_refresh",
        },
        "sla_p95_s": 180,
    },
    "repair_registry": {
        "kinds": {"station:repair_registry", "registry_refresh", "agent_repair_task"},
        "sla_p95_s": 1200,
    },
    "gm_operator": {
        "kinds": {"gm_operator_task"},
        "sla_p95_s": 1800,
    },
}


def _now() -> int:
    return int(time.time())


def _dict_field(obj: Any, key: str) -> dict[str, Any]:
    """Safe nested-dict accessor: `obj[key]` if it is a dict, else `{}`. Replaces the
    `obj.get(k) if isinstance(obj.get(k), dict) else {}` idiom hand-inlined ~78x across the read
    models (the Action-4 dedup). Behavior-identical by construction; locked by the golden-master test
    (`tests/formal/test_factory_intelligence_golden.py`)."""
    if not isinstance(obj, dict):
        return {}
    value = obj.get(key)
    return value if isinstance(value, dict) else {}


def _read_json(path: str | Path | None) -> Any:
    return read_json(path)


def _write_json(path: str | Path, obj: Any) -> None:
    write_json_atomic(path, obj)


def _run_observability_read_model(args: argparse.Namespace) -> dict[str, Any]:
    run_tag = str(getattr(args, "run_observability_tag", "") or "").strip()
    manifest = str(getattr(args, "run_observability_manifest", "") or "").strip()
    if not run_tag and not manifest:
        return {}
    try:
        src = str(REPO / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from ztare.leanmill.run_observability import build_observability_bundle

        return build_observability_bundle(
            run_tag=run_tag,
            attempts_db=getattr(args, "run_observability_attempts_db"),
            manifest_path=manifest or None,
            lean_root=(getattr(args, "run_observability_lean_root", "") or None),
            verdicts_path=getattr(args, "run_observability_verdicts"),
            bank_attempts_path=getattr(args, "run_observability_bank_attempts"),
            formalize_attempts_path=getattr(args, "run_observability_formalize_attempts"),
            notes_trace_path=getattr(args, "run_observability_notes_trace"),
            cot_traces_path=getattr(args, "run_observability_cot_traces"),
            proof_cache_path=getattr(args, "run_observability_proof_cache"),
            no_good_path=getattr(args, "run_observability_no_good"),
            faithfulness_path=getattr(args, "run_observability_faithfulness"),
            decomposition_cache_path=getattr(args, "run_observability_decomposition_cache"),
            staged_index_path=(getattr(args, "run_observability_staged_index", "") or None),
            axiom_packs_path=getattr(args, "run_observability_axiom_packs"),
        )
    except Exception as exc:  # noqa: BLE001 - read model must not block factory intelligence
        return {
            "schema": "leanmill.run_observability_bundle.v1",
            "run_tag": run_tag,
            "error": repr(exc)[:240],
        }


def _read_events(path: str | Path, *, limit: int) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    lines = p.read_text(errors="ignore").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-max(1, int(limit)):]:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def _c_supply_source_file(row: dict[str, Any]) -> str:
    return str(row.get("source_file") or row.get("source_path") or row.get("source") or "").strip()


def _c_supply_source_root(source_file: str) -> str:
    text = str(source_file or "").strip()
    if not text:
        return ""
    parts = [part for part in Path(text).parts if part not in {"", "/"}]
    for marker in (
        "evaluation_harness_sources",
        "mcb_files",
        "queued_learning_work",
        "source_mine",
        "Mathlib",
        "ZtareProofs",
    ):
        if marker in parts:
            return marker
    parent = Path(text).parent
    return str(parent) if str(parent) not in {"", "."} else text
def _c_supply_selection_summary(selection: dict[str, Any], *, source_path: str = "") -> dict[str, Any]:
    if not isinstance(selection, dict):
        return {}
    source_demand = selection.get("source_demand_requests") or []
    selected = selection.get("selected_rows_order") or []
    rows_by_id: dict[str, dict[str, Any]] = {}
    anonymous_rows: list[dict[str, Any]] = []
    for key in ("selected_rows", "rows"):
        vals = selection.get(key) or []
        if not isinstance(vals, list):
            continue
        for row in vals:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
            if row_id:
                rows_by_id.setdefault(row_id, row)
            else:
                anonymous_rows.append(row)
    rows = list(rows_by_id.values()) + anonymous_rows
    unknown_rows = [
        row for row in rows
        if isinstance(row, dict) and "static_result_unknown" in set(row.get("rejection_reasons") or [])
    ]
    eligible_rows = [row for row in rows if isinstance(row, dict) and bool(row.get("eligible"))]
    pending_rows = [row for row in rows if isinstance(row, dict) and bool(row.get("probe_credit_pending"))]
    probe_verified_rows = [row for row in rows if isinstance(row, dict) and _c_supply_probe_verified_row(row)]
    probe_verified_pending_static_rows = [row for row in rows if isinstance(row, dict) and _c_supply_probe_verified_pending_static_row(row)]
    credit_ready_rows = [row for row in rows if isinstance(row, dict) and _c_supply_credit_ready_row(row)]
    static_strict_rows = [
        row for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("static_tools_result"), dict)
        and (
            str(row["static_tools_result"].get("status") or "") == "failed_or_no_positive_signal"
            or (
                str(row["static_tools_result"].get("public_exit") or "") == "tested_no_positive_signal"
                and str(row["static_tools_result"].get("governed_exit") or "") == "tested_no_positive_signal"
            )
        )
        and not row["static_tools_result"].get("missing_static_arms")
    ]
    unknown_family_counts: Counter[str] = Counter()
    unknown_samples: list[dict[str, Any]] = []
    credit_ready_samples: list[dict[str, Any]] = []
    pending_samples: list[dict[str, Any]] = []
    probe_verified_pending_static_samples: list[dict[str, Any]] = []
    credit_ready_family_counts: Counter[str] = Counter()
    credit_ready_source_file_counts: Counter[str] = Counter()
    credit_ready_source_root_counts: Counter[str] = Counter()
    eligible_family_counts: Counter[str] = Counter()
    for row in credit_ready_rows:
        families = [str(f) for f in (row.get("probe_verified_families") or row.get("matched_families") or []) if str(f)]
        credit_ready_family_counts.update(families)
        source_file = _c_supply_source_file(row)
        source_root = _c_supply_source_root(source_file)
        if source_file:
            credit_ready_source_file_counts[source_file] += 1
        if source_root:
            credit_ready_source_root_counts[source_root] += 1
        credit_ready_samples.append({
            "row_id": row.get("row_id"),
            "families": families[:8],
            "c_discriminating_evidence_status": row.get("c_discriminating_evidence_status"),
            "static_tools_result": row.get("static_tools_result"),
            "source_file": row.get("source_file"),
        })
    for row in pending_rows:
        pending_samples.append({
            "row_id": row.get("row_id"),
            "families": [str(f) for f in (row.get("matched_families") or []) if str(f)][:8],
            "c_discriminating_evidence_status": row.get("c_discriminating_evidence_status"),
            "static_tools_result": row.get("static_tools_result"),
            "source_file": row.get("source_file"),
        })
    for row in probe_verified_pending_static_rows:
        families = [str(f) for f in (row.get("probe_verified_families") or row.get("matched_families") or []) if str(f)]
        probe_verified_pending_static_samples.append({
            "row_id": row.get("row_id"),
            "families": families[:8],
            "c_discriminating_evidence_status": row.get("c_discriminating_evidence_status"),
            "static_sweep_required_before_c_credit": row.get("static_sweep_required_before_c_credit"),
            "static_tools_result": row.get("static_tools_result"),
            "source_file": row.get("source_file"),
        })
    for row in eligible_rows:
        families = [str(f) for f in (row.get("matched_families") or row.get("families_with_positive_template") or []) if str(f)]
        eligible_family_counts.update(families)
    for row in unknown_rows:
        families = [str(f) for f in (row.get("matched_families") or []) if str(f)]
        unknown_family_counts.update(families)
        unknown_samples.append({
            "row_id": row.get("row_id"),
            "family_count": len(families),
            "families": families[:8],
            "source_file": row.get("source_file"),
        })
    eligible_order = [str(row.get("row_id")) for row in eligible_rows if row.get("row_id")]
    source_demand_family_count = len({
        str(req.get("family") or "").strip()
        for req in source_demand
        if isinstance(req, dict) and str(req.get("family") or "").strip()
    }) if isinstance(source_demand, list) else 0
    return {
        "schema": "leanmill-c-supply-selection-summary-v1",
        "source_path": source_path,
        "status": selection.get("status"),
        "candidate_pool_count": selection.get("candidate_pool_count"),
        "eligible_count": selection.get("eligible_count"),
        "selected_count": selection.get("selected_count"),
        "credit_ready_count": len(credit_ready_rows) if rows else (selection.get("credit_ready_count") if selection.get("credit_ready_count") is not None else 0),
        "credit_ready_rows": credit_ready_samples[:50],
        "credit_ready_family_counts": dict(sorted(credit_ready_family_counts.items())),
        "credit_ready_unique_family_count": len(credit_ready_family_counts),
        "credit_ready_source_file_counts": dict(sorted(credit_ready_source_file_counts.items())),
        "credit_ready_source_file_count": len(credit_ready_source_file_counts),
        "credit_ready_source_root_counts": dict(sorted(credit_ready_source_root_counts.items())),
        "credit_ready_source_root_count": len(credit_ready_source_root_counts),
        "credit_ready_top_family_row_count": max(credit_ready_family_counts.values() or [0]),
        "probe_pending_count": selection.get("probe_pending_count") if selection.get("probe_pending_count") is not None else len(pending_rows),
        "probe_pending_rows": pending_samples[:50],
        "probe_verified_count": len(probe_verified_rows) if rows else (selection.get("probe_verified_count") if selection.get("probe_verified_count") is not None else 0),
        "probe_verified_pending_static_count": len(probe_verified_pending_static_rows) if rows else (selection.get("probe_verified_pending_static_count") if selection.get("probe_verified_pending_static_count") is not None else 0),
        "probe_verified_pending_static_rows": probe_verified_pending_static_samples[:50],
        "static_strict_no_signal_row_ids": sorted(str(row.get("row_id") or "") for row in static_strict_rows if str(row.get("row_id") or ""))[:200],
        "static_strict_no_signal_row_count": len({str(row.get("row_id") or "") for row in static_strict_rows if str(row.get("row_id") or "")}),
        "eligible_rows_order": eligible_order[:100],
        "eligible_unique_family_count": len(eligible_family_counts),
        "eligible_family_counts": dict(sorted(eligible_family_counts.items())),
        "eligible_rows_truncated": len(eligible_order) > 100,
        "min_rows": selection.get("min_rows"),
        "blockers_by_reason": selection.get("blockers_by_reason") or {},
        "support_counts": selection.get("support_counts") or {},
        "static_conflict_row_count": selection.get("static_conflict_row_count"),
        "static_conflict_policy": selection.get("static_conflict_policy"),
        "source_demand_count": len(source_demand) if isinstance(source_demand, list) else None,
        "source_demand_family_count": source_demand_family_count,
        "source_demand_requests": source_demand[:20] if isinstance(source_demand, list) else [],
        "selected_rows_order": selected[:100] if isinstance(selected, list) else [],
        "selected_rows_truncated": isinstance(selected, list) and len(selected) > 100,
        "static_unknown_row_count": len(unknown_rows),
        "static_unknown_family_counts": dict(sorted(unknown_family_counts.items())),
        "static_unknown_rows": unknown_samples[:50],
    }


def _typed_proof_exit_read_model(payload: dict[str, Any]) -> dict[str, Any]:
    exits = payload.get("exits") if isinstance(payload, dict) else []
    exits = [row for row in exits if isinstance(row, dict)] if isinstance(exits, list) else []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else typed_exit_summary(exits)
    return {
        "schema": "leanmill-typed-proof-exit-read-model-v1",
        "source_schema": payload.get("schema") if isinstance(payload, dict) else None,
        "summary": summary,
        "sample_exits": exits[:25],
        "credit_boundary": summary.get("credit_boundary"),
        "proof_credit": "none_read_model_is_advisory",
    }


def _evaluation_harness_read_model(
    prep: dict[str, Any],
    run_summary: dict[str, Any],
    *,
    prep_path: str,
    run_path: str,
    no_lift_report: dict[str, Any] | None = None,
    no_lift_report_path: str = "",
) -> dict[str, Any]:
    if not prep:
        return {
            "schema": "leanmill-evaluation-harness-read-model-v1",
            "status": "prep_missing",
            "prep_path": prep_path,
            "run_path": run_path,
            "next_action": "run leanmill_benchmark_prep.py before attempting a credited benchmark",
        }
    next_blocker = _dict_field(prep, "next_blocker")
    preflight = _dict_field(prep, "benchmark_preflight")
    materialization = _dict_field(preflight, "source_materialization")
    selected_ready = (
        bool(next_blocker.get("benchmark_can_run_full"))
        and str(preflight.get("selected_target_resolution_status") or "") == "pass"
        and int(preflight.get("selected_target_unresolved_row_count") or 0) == 0
        and int(prep.get("selected_row_count") or 0) > 0
    )
    prep_selected_count = int(prep.get("selected_row_count") or 0)
    credited_run_present = bool(
        run_summary
        and not run_summary.get("preflight_only")
        and int(run_summary.get("record_count") or 0) > 0
    )
    residual_observability = (
        run_summary.get("residual_memory_observability")
        if isinstance(run_summary.get("residual_memory_observability"), dict) else {}
    )
    residual_observability_status = str(residual_observability.get("status") or ("unknown" if credited_run_present else ""))
    masked_family_candidate_record_count = int(residual_observability.get("masked_family_candidate_record_count") or 0)
    run_selected_count = int(run_summary.get("selected_row_count") or 0) if run_summary else 0
    run_completed_row_count = int(run_summary.get("completed_row_count") or run_summary.get("row_count") or 0) if run_summary else 0
    arm_metrics = _dict_field(run_summary, "arm_metrics")
    lift_comparison = (
        arm_metrics.get("benchmark_lift_comparison")
        if isinstance(arm_metrics.get("benchmark_lift_comparison"), dict) else {}
    )
    meets_closure_lift = bool(lift_comparison.get("meets_20pp_closure_lift"))
    meets_efficiency_lift = bool(lift_comparison.get("meets_2x_attempt_efficiency_lift"))
    has_benchmark_lift = bool(meets_closure_lift or meets_efficiency_lift)
    no_lift_report = no_lift_report if isinstance(no_lift_report, dict) else {}
    run_sha256 = sha256_file(run_path)
    no_lift_published = bool(
        no_lift_report
        and str(no_lift_report.get("status") or "") == "published_no_lift_result"
        and str(no_lift_report.get("source_run") or "") == str(run_path)
        and str(no_lift_report.get("source_run_sha256") or "") == str(run_sha256 or "")
    )
    limited_credited_run = bool(
        credited_run_present
        and prep_selected_count > 0
        and run_selected_count > 0
        and run_selected_count < prep_selected_count
    )
    if credited_run_present and masked_family_candidate_record_count > 0:
        status = "credited_run_masked_residual_memory"
    elif credited_run_present and limited_credited_run:
        status = "credited_run_limited_slice"
    elif credited_run_present and residual_observability_status == "unknown":
        status = "credited_run_observability_unknown"
    elif credited_run_present and lift_comparison and not has_benchmark_lift and no_lift_published:
        status = "credited_run_no_lift_published"
    elif credited_run_present and lift_comparison and not has_benchmark_lift:
        status = "credited_run_recorded_no_benchmark_lift"
    elif credited_run_present and lift_comparison and has_benchmark_lift:
        status = "credited_run_recorded_with_benchmark_lift"
    elif credited_run_present:
        status = "credited_run_recorded"
    elif selected_ready:
        status = "ready_for_credited_run"
    else:
        status = "prep_blocked"
    if status == "credited_run_masked_residual_memory":
        next_action = "rerun the evaluation harness with residual family candidates observed before generic tool credit; keep the masked run as a diagnostic, not competitive evidence"
    elif status == "credited_run_limited_slice":
        next_action = "rerun the evaluation harness over the full selected slice with --limit 0 or an explicit full-slice limit"
    elif status == "credited_run_observability_unknown":
        next_action = "refresh the evaluation harness summary with the current runner so residual-memory observability is recorded"
    elif status == "credited_run_recorded_no_benchmark_lift":
        next_action = "publish the benchmark internally as a no-lift result; do not make a competitive planner-lift claim from this natural-Mathlib slice"
    elif status == "credited_run_no_lift_published":
        next_action = "no-lift benchmark receipt is published; prioritize C-discriminating rows where public/static tools fail"
    elif status == "credited_run_recorded_with_benchmark_lift":
        next_action = "publish the benchmark internally with the lift comparison and keep public/static closures outside LeanMill proof credit"
    elif credited_run_present:
        next_action = "credited benchmark has run records with observability checks; summarize internally without treating public-tool closures as LeanMill credit"
    elif selected_ready:
        next_action = "pause proof workers and run leanmill_evaluation_harness_runner.py with --snapshot-repair-families-dir and no skip flags"
    else:
        next_action = "repair prep blockers before running the evaluation harness"
    return {
        "schema": "leanmill-evaluation-harness-read-model-v1",
        "status": status,
        "prep_path": prep_path,
        "run_path": run_path,
        "run_sha256": run_sha256,
        "no_lift_publication": {
            "path": no_lift_report_path,
            "status": no_lift_report.get("status") if no_lift_report else "missing",
            "source_run_sha256": no_lift_report.get("source_run_sha256") if no_lift_report else None,
            "matches_run": no_lift_published,
        },
        "selected_row_count": prep_selected_count,
        "contract_path": prep.get("contract"),
        "row_context_path": prep.get("row_context"),
        "blockers": next_blocker.get("blockers") or [],
        "benchmark_can_run_full": bool(next_blocker.get("benchmark_can_run_full")),
        "selected_target_resolution_status": preflight.get("selected_target_resolution_status"),
        "selected_target_unresolved_row_count": int(preflight.get("selected_target_unresolved_row_count") or 0),
        "full_pool_target_resolution_status": preflight.get("full_pool_target_resolution_status"),
        "full_pool_target_unresolved_row_count": int(preflight.get("full_pool_target_unresolved_row_count") or 0),
        "source_materialization_counts": materialization.get("counts") or {},
        "source_materialization_failure_count": int(materialization.get("failure_count") or 0),
        "family_template_selected_count": int(preflight.get("family_template_selected_count") or 0),
        "selected_template_rows_with_negative_controls": len(preflight.get("selected_template_rows_with_negative_controls") or []),
        "credited_run_present": credited_run_present,
        "run_selected_row_count": run_selected_count,
        "run_completed_row_count": run_completed_row_count,
        "limited_credited_run": limited_credited_run,
        "residual_memory_observability_status": residual_observability_status,
        "masked_family_candidate_record_count": masked_family_candidate_record_count,
        "residual_candidate_order": run_summary.get("residual_candidate_order") if run_summary else None,
        "benchmark_lift_comparison": lift_comparison,
        "has_benchmark_lift": has_benchmark_lift,
        "meets_20pp_closure_lift": meets_closure_lift,
        "meets_2x_attempt_efficiency_lift": meets_efficiency_lift,
        "last_run_summary": {
            "row_count": run_summary.get("row_count") if run_summary else None,
            "selected_row_count": run_summary.get("selected_row_count") if run_summary else None,
            "completed_row_count": run_summary.get("completed_row_count") if run_summary else None,
            "record_count": run_summary.get("record_count") if run_summary else None,
            "preflight_only": run_summary.get("preflight_only") if run_summary else None,
            "residual_memory_observability_status": residual_observability_status,
            "masked_family_candidate_record_count": masked_family_candidate_record_count,
            "residual_candidate_order": run_summary.get("residual_candidate_order") if run_summary else None,
            "benchmark_lift_comparison": lift_comparison,
            "contract_sha256_check_status": (
                (run_summary.get("contract_sha256_check") or {}).get("status")
                if isinstance(run_summary.get("contract_sha256_check"), dict) else None
            ),
            "target_resolution_check_status": (
                (run_summary.get("target_resolution_check") or {}).get("status")
                if isinstance(run_summary.get("target_resolution_check"), dict) else None
            ),
            "repair_families_snapshot_status": (
                (run_summary.get("repair_families_snapshot") or {}).get("status")
                if isinstance(run_summary.get("repair_families_snapshot"), dict) else None
            ),
        } if run_summary else {},
        "next_action": next_action,
        "credit_boundary": "evaluation-readiness only; benchmark claim requires a non-preflight run with complete arm records",
    }


def _same_path(a: str | Path | None, b: str | Path | None) -> bool:
    if not a or not b:
        return False
    pa = Path(a)
    pb = Path(b)
    try:
        return pa.resolve() == pb.resolve()
    except OSError:
        return str(pa) == str(pb)


def _artifact_registry_read_model(
    cx: sqlite3.Connection,
    *,
    expected_canonical_paths: dict[str, str],
) -> dict[str, Any]:
    refs = work_queue.artifact_refs(cx, limit=160)
    by_key = {str(ref.get("artifact_key") or ""): ref for ref in refs if ref.get("artifact_key")}
    missing_canonical_keys: list[str] = []
    path_mismatches: list[dict[str, Any]] = []
    sha_mismatches: list[dict[str, Any]] = []
    role_conflicts: list[dict[str, Any]] = []
    for key, expected_path in expected_canonical_paths.items():
        ref = by_key.get(key)
        if not ref:
            missing_canonical_keys.append(key)
            continue
        if str(ref.get("role") or "") != "canonical":
            role_conflicts.append({
                "artifact_key": key,
                "expected_role": "canonical",
                "observed_role": ref.get("role"),
                "path": ref.get("path"),
            })
        if expected_path and not _same_path(str(ref.get("path") or ""), expected_path):
            path_mismatches.append({
                "artifact_key": key,
                "registered_path": ref.get("path"),
                "expected_path": expected_path,
            })
        current_sha = sha256_file(expected_path) if expected_path else ""
        registered_sha = str(ref.get("sha256") or "")
        if current_sha and registered_sha and current_sha != registered_sha:
            sha_mismatches.append({
                "artifact_key": key,
                "path": expected_path,
                "registered_sha256": registered_sha,
                "current_sha256": current_sha,
            })
        for path_ref in work_queue.artifact_refs_for_path(cx, expected_path, limit=20):
            if str(path_ref.get("role") or "") != "canonical":
                role_conflicts.append({
                    "artifact_key": key,
                    "conflicting_artifact_key": path_ref.get("artifact_key"),
                    "expected_role": "canonical",
                    "observed_role": path_ref.get("role"),
                    "path": path_ref.get("path"),
                })
    return {
        "schema": "leanmill-artifact-registry-read-model-v1",
        "role_contract": {
            "canonical": "single-node authoritative dashboard/read-model artifact",
            "self_correction": "bounded corrective run output; never used as canonical factory state without deterministic promotion",
            "diagnostic": "operator or experimental artifact",
        },
        "authority_model": "VPS/local node SQLite owns mutable factory artifact refs; filesystem sync mirrors artifacts but does not decide role.",
        "ref_count": len(refs),
        "canonical_ref_count": sum(1 for ref in refs if str(ref.get("role") or "") == "canonical"),
        "self_correction_ref_count": sum(1 for ref in refs if str(ref.get("role") or "") == "self_correction"),
        "missing_canonical_keys": missing_canonical_keys,
        "path_mismatches": path_mismatches,
        "sha_mismatches": sha_mismatches,
        "role_conflicts": role_conflicts,
        "recent_refs": refs[:40],
        "status": "needs_attention" if (path_mismatches or sha_mismatches or role_conflicts) else "ok",
    }


def _pr_a1_public_review_receipt(
    report: dict[str, Any] | None,
    *,
    report_path: str,
    target_path: str,
) -> dict[str, Any]:
    report = report if isinstance(report, dict) else {}
    target = str(report.get("target") or "")
    audit = str(report.get("audit") or "")
    target_sha = sha256_file(target) if target else None
    audit_sha = sha256_file(audit) if audit else None
    status = str(report.get("status") or "missing")
    target_matches = bool(
        target
        and _same_path(target, target_path)
        and target_sha
        and str(report.get("target_sha256") or "") == str(target_sha)
    )
    audit_matches = bool(
        audit
        and audit_sha
        and str(report.get("audit_sha256") or "") == str(audit_sha)
    )
    published = bool(status == "governed_public_review_ready" and target_matches and audit_matches)
    return {
        "schema": "leanmill-pr-a1-public-review-receipt-read-model-v1",
        "path": report_path,
        "status": status,
        "target": target,
        "audit": audit,
        "target_sha256": report.get("target_sha256"),
        "current_target_sha256": target_sha,
        "audit_sha256": report.get("audit_sha256"),
        "current_audit_sha256": audit_sha,
        "target_matches_current": target_matches,
        "audit_matches_current": audit_matches,
        "published_for_current_inputs": published,
        "credit_boundary": "review-routing receipt only; no proof credit or final PR correctness claim",
    }


def _competitive_inventory_read_model(
    inventory: dict[str, Any],
    *,
    path: str,
    pr_a1_public_review: dict[str, Any] | None = None,
    pr_a1_public_review_path: str = "",
) -> dict[str, Any]:
    if not inventory:
        return {
            "schema": "leanmill-competitive-inventory-read-model-v1",
            "status": "missing",
            "path": path,
            "next_action": "run leanmill_competitive_inventory.py to materialize the Section 8 Phase 2 artifact inventory",
        }
    summary = _dict_field(inventory, "summary")
    pr = _dict_field(inventory, "pr_a1_candidate")
    ztare = _dict_field(inventory, "ztare_proofs")
    route_c_tasks = _dict_field(inventory, "route_c_gap_tasks")
    route_c_synthesis = _dict_field(inventory, "route_c_hold_synthesis")
    route_c_replay_prep = _dict_field(inventory, "route_c_exact_gap_replay_prep")
    route_c_replay_probe = _dict_field(inventory, "route_c_exact_gap_replay_probe")
    route_c_gap_count = int(summary.get("route_c_gap_report_count") or 0)
    route_c_closed_count = int(summary.get("route_c_compiled_or_closed_count") or 0)
    route_c_gap_task_count = int(summary.get("route_c_gap_task_count") or route_c_tasks.get("task_count") or 0)
    route_c_gap_tasks_enqueued = bool(summary.get("route_c_gap_task_enqueue_requested") or route_c_tasks.get("enqueue_requested"))
    route_c_gap_tasks_all_done = bool(summary.get("route_c_gap_task_all_done") or route_c_tasks.get("all_done"))
    route_c_synthesis_count = int(summary.get("route_c_hold_synthesis_eligible_count") or route_c_synthesis.get("eligible_task_count") or 0)
    route_c_synthesis_all_done = bool(summary.get("route_c_hold_synthesis_all_done") or route_c_synthesis.get("all_done"))
    route_c_synthesis_status_counts = (
        summary.get("route_c_hold_synthesis_status_counts")
        if isinstance(summary.get("route_c_hold_synthesis_status_counts"), dict)
        else (route_c_synthesis.get("queue_status") or {}).get("status_counts")
    )
    route_c_synthesis_status_counts = route_c_synthesis_status_counts if isinstance(route_c_synthesis_status_counts, dict) else {}
    route_c_synthesis_gov_count = int(
        summary.get("route_c_hold_synthesis_governance_followup_count")
        or route_c_synthesis.get("governance_followup_count")
        or 0
    )
    route_c_synthesis_gov_status_counts = (
        summary.get("route_c_hold_synthesis_governance_status_counts")
        if isinstance(summary.get("route_c_hold_synthesis_governance_status_counts"), dict)
        else route_c_synthesis.get("governance_status_counts")
    )
    route_c_synthesis_gov_status_counts = (
        route_c_synthesis_gov_status_counts if isinstance(route_c_synthesis_gov_status_counts, dict) else {}
    )
    route_c_replay_prep_candidate_count = int(
        summary.get("route_c_exact_gap_replay_prep_candidate_count")
        or route_c_replay_prep.get("candidate_count")
        or 0
    )
    route_c_replay_prep_ready_count = int(
        summary.get("route_c_exact_gap_replay_prep_ready_packet_count")
        or route_c_replay_prep.get("ready_packet_count")
        or 0
    )
    route_c_replay_prep_status_counts = (
        summary.get("route_c_exact_gap_replay_prep_status_counts")
        if isinstance(summary.get("route_c_exact_gap_replay_prep_status_counts"), dict)
        else route_c_replay_prep.get("status_counts")
    )
    route_c_replay_prep_status_counts = route_c_replay_prep_status_counts if isinstance(route_c_replay_prep_status_counts, dict) else {}
    route_c_replay_probe_ready_count = int(
        summary.get("route_c_exact_gap_replay_probe_ready_packet_count")
        or route_c_replay_probe.get("ready_packet_count")
        or 0
    )
    route_c_replay_probe_status_counts = (
        summary.get("route_c_exact_gap_replay_probe_status_counts")
        if isinstance(summary.get("route_c_exact_gap_replay_probe_status_counts"), dict)
        else route_c_replay_probe.get("status_counts")
    )
    route_c_replay_probe_status_counts = route_c_replay_probe_status_counts if isinstance(route_c_replay_probe_status_counts, dict) else {}
    pr_status = str(summary.get("pr_a1_status") or pr.get("status") or "")
    pr_a1_path = ((pr.get("static_audit") or {}).get("path") if isinstance(pr.get("static_audit"), dict) else None)
    pr_public_review = _pr_a1_public_review_receipt(
        pr_a1_public_review,
        report_path=pr_a1_public_review_path,
        target_path=str(pr_a1_path or ""),
    )
    pr_public_review_published = bool(pr_public_review.get("published_for_current_inputs"))
    pr_review_ready = pr_status == "compile_pass_l3_advisory_pass"
    pr_l3_review_needed = pr_status == "compile_pass_l3_advisory_review"
    pr_audit_blocked = pr_status in {"compile_failed", "disallowed_axiom_dependency", "l3_confirmed_blocker", "static_open_or_axiom"}
    if pr_status == "static_sorry_free_needs_compile_and_l3_audit":
        status = "pr_a1_compile_l3_audit_ready"
        next_action = "compile PR_A1 and run L3 anti-pattern audit before calling it a PR-ready closure"
    elif pr_l3_review_needed:
        status = "pr_a1_l3_review_needed"
        next_action = "resolve the PR_A1 L3 advisory flags before public artifact review"
    elif pr_audit_blocked:
        status = "pr_a1_audit_blocked"
        next_action = "repair the PR_A1 compile, axiom, or L3 blocker before further promotion"
    elif route_c_replay_probe_ready_count > 0 and int(route_c_replay_probe_status_counts.get("needs_heavy_replay") or 0) > 0:
        status = "route_c_exact_gap_heavy_replay_ready"
        next_action = route_c_replay_probe.get("next_action") or "send Route C exact-gap packets to heavier Lean replay"
    elif route_c_replay_probe_ready_count > 0 and int(route_c_replay_probe_status_counts.get("blocked_existing_tactic_closes") or 0) > 0:
        status = "route_c_exact_gap_probe_disqualified"
        next_action = route_c_replay_probe.get("next_action") or "disqualify cheap-closed exact-gap packets and repair prompt/gate"
    elif route_c_replay_prep_ready_count > 0:
        status = "route_c_exact_gap_replay_probe_ready"
        next_action = route_c_replay_prep.get("next_action") or "run cheap replay probes on Route C exact-gap packets"
    elif (
        route_c_replay_prep_candidate_count > 0
        and route_c_replay_prep_ready_count == 0
        and int(route_c_replay_prep_status_counts.get("blocked_existing_finset_max_mem") or 0) > 0
        and isinstance(route_c_replay_prep.get("prompt_gate_repair_receipt"), dict)
        and str(route_c_replay_prep.get("prompt_gate_repair_receipt", {}).get("status") or "") == "applied"
    ):
        status = "route_c_gap_synthesis_terminal_holds_recorded"
        next_action = "do not replay this Route C batch; future synthesis prompt/gate now blocks the observed duplicate and existing-theorem patterns"
    elif route_c_replay_prep_candidate_count > 0 and int(route_c_replay_prep_status_counts.get("blocked_target_duplicate") or 0) == route_c_replay_prep_candidate_count:
        status = "route_c_exact_gap_duplicate_repair_ready"
        next_action = route_c_replay_prep.get("next_action") or "repair Route C exact-gap synthesis because all candidates duplicate targets"
    elif route_c_synthesis_count > 0 and int(route_c_synthesis_status_counts.get("failed") or 0) > 0:
        status = "route_c_gap_hold_synthesis_retry_ready"
        next_action = route_c_synthesis.get("next_action") or "repair or requeue failed Route C hold-synthesis tasks"
    elif route_c_synthesis_count > 0 and (
        int(route_c_synthesis_status_counts.get("queued") or 0) > 0
        or int(route_c_synthesis_status_counts.get("missing") or 0) > 0
    ):
        status = "route_c_gap_hold_synthesis_execution_ready"
        next_action = route_c_synthesis.get("next_action") or "run proposal workers on Route C hold-synthesis tasks"
    elif route_c_synthesis_count > 0 and route_c_synthesis_gov_count > 0 and int(route_c_synthesis_gov_status_counts.get("failed") or 0) > 0:
        status = "route_c_gap_synthesis_governance_repair_ready"
        next_action = route_c_synthesis.get("next_action") or "repair failed Route C exact-gap governance candidates"
    elif route_c_synthesis_count > 0 and route_c_synthesis_gov_count > 0 and int(route_c_synthesis_gov_status_counts.get("queued") or 0) > 0:
        status = "route_c_gap_synthesis_governance_ready"
        next_action = route_c_synthesis.get("next_action") or "run governance workers on Route C exact-gap candidates"
    elif (
        route_c_synthesis_count > 0
        and route_c_synthesis_all_done
        and route_c_synthesis_gov_count > 0
        and int(route_c_synthesis_gov_status_counts.get("done") or 0) == route_c_synthesis_gov_count
    ):
        status = "route_c_gap_synthesis_replay_ready"
        next_action = route_c_synthesis.get("next_action") or "route governance-checked Route C exact-gap candidates to Lean replay or ratification lane"
    elif route_c_synthesis_count > 0 and route_c_synthesis_all_done:
        status = "route_c_gap_synthesis_terminal_holds_recorded"
        next_action = route_c_synthesis.get("next_action") or "inspect Route C second-pass holds before rerunning"
    elif route_c_gap_task_count > 0 and route_c_gap_tasks_all_done:
        status = "route_c_gap_tasks_terminal_holds_recorded"
        next_action = "synthesize the Route C hold outputs into stronger exact-gap contexts before rerunning proposal tasks"
    elif route_c_gap_task_count > 0 and route_c_gap_tasks_enqueued:
        status = "route_c_gap_task_execution_ready"
        next_action = "run the LLM proposal worker on queued Route C exact-gap/decomposition tasks"
    elif route_c_gap_count > 0 and route_c_closed_count == 0:
        status = "route_c_gap_reports_ready_for_task_extraction"
        next_action = "turn Route C gap reports into missing-lemma tasks and feed them to the proof loop with semantic retrieval"
    elif pr_review_ready and pr_public_review_published:
        status = "pr_a1_public_artifact_review_published"
        next_action = "PR_A1 public-artifact review receipt is published for the current target and audit; wait for governed review feedback before further promotion"
    elif pr_review_ready:
        status = "pr_a1_public_artifact_review_ready"
        next_action = "review PR_A1 as a public artifact candidate; do not treat this audit receipt as proof credit"
    else:
        status = "inventory_recorded"
        next_action = summary.get("next_action") or "inspect competitive inventory"
    return {
        "schema": "leanmill-competitive-inventory-read-model-v1",
        "status": status,
        "path": path,
        "route_c_gap_report_count": route_c_gap_count,
        "route_c_compiled_or_closed_count": route_c_closed_count,
        "route_c_gap_task_count": route_c_gap_task_count,
        "route_c_gap_tasks_enqueued": route_c_gap_tasks_enqueued,
        "route_c_gap_tasks_all_done": route_c_gap_tasks_all_done,
        "route_c_gap_task_status_counts": summary.get("route_c_gap_task_status_counts"),
        "route_c_hold_synthesis_eligible_count": route_c_synthesis_count,
        "route_c_hold_synthesis_all_done": route_c_synthesis_all_done,
        "route_c_hold_synthesis_status_counts": route_c_synthesis_status_counts,
        "route_c_hold_synthesis_proposal_type_counts": summary.get("route_c_hold_synthesis_proposal_type_counts"),
        "route_c_hold_synthesis_governance_followup_count": route_c_synthesis_gov_count,
        "route_c_hold_synthesis_governance_status_counts": route_c_synthesis_gov_status_counts,
        "route_c_exact_gap_replay_prep_candidate_count": route_c_replay_prep_candidate_count,
        "route_c_exact_gap_replay_prep_ready_packet_count": route_c_replay_prep_ready_count,
        "route_c_exact_gap_replay_prep_status_counts": route_c_replay_prep_status_counts,
        "route_c_exact_gap_replay_probe_ready_packet_count": route_c_replay_probe_ready_count,
        "route_c_exact_gap_replay_probe_status_counts": route_c_replay_probe_status_counts,
        "ztare_lean_file_count": int(summary.get("ztare_lean_file_count") or ztare.get("lean_file_count") or 0),
        "ztare_files_with_sorry_or_admit_count": int(
            summary.get("ztare_files_with_sorry_or_admit_count")
            or ztare.get("files_with_sorry_or_admit_count")
            or 0
        ),
        "semantic_retrieval_wiring_status": summary.get("semantic_retrieval_wiring_status"),
        "pr_a1_status": pr_status,
        "pr_a1_compile_status": summary.get("pr_a1_compile_status"),
        "pr_a1_l3_status": summary.get("pr_a1_l3_status"),
        "pr_a1_review_ready": pr_review_ready,
        "pr_a1_public_review_published": pr_public_review_published,
        "pr_a1_public_review": pr_public_review,
        "pr_a1_path": pr_a1_path,
        "next_action": next_action,
        "credit_boundary": inventory.get("credit_boundary") or "inventory only",
    }


def _heavy_lean_process_pressure(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(policy, dict):
        policy = {}
    pattern = r"leansearch_repair_canary_drain|lean_repl|vendor/lean_repl|/bin/repl($| )|lake env .*repl|lake env lean"
    drain_warn_count = int(policy.get("heavy_lean_pressure_drain_warn_count") or 2)
    repl_warn_count = int(policy.get("heavy_lean_pressure_repl_warn_count") or 2)
    external_warn_enabled = bool(policy.get("heavy_lean_pressure_external_warn_enabled", True))
    lines: list[str] = []
    pgrep_error = ""
    try:
        proc = subprocess.run(
            ["pgrep", "-fl", pattern],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )
        if proc.returncode in {0, 1}:
            lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        else:
            pgrep_error = (proc.stderr or proc.stdout or f"pgrep_rc_{proc.returncode}").strip()[:240]
    except (OSError, subprocess.TimeoutExpired) as exc:
        pgrep_error = str(exc)[:240]

    drain: list[str] = []
    repl: list[str] = []
    external: list[str] = []
    other: list[str] = []
    for line in lines:
        low = line.lower()
        if "leansearch_repair_canary_drain.py" in line:
            drain.append(line)
        elif "lean_repl" in low or "/repl" in low or " repl" in low:
            repl.append(line)
        elif "lake env" in low or " lean " in low or low.endswith(" lean"):
            external.append(line)
        else:
            other.append(line)

    repl_group_count = len([line for line in repl if "lake env " in line]) or len(repl)
    risk_classes: list[str] = []
    if len(drain) >= drain_warn_count and repl_group_count >= repl_warn_count:
        risk_classes.append("warm_repl_overprovision_risk")
    if external_warn_enabled and external:
        risk_classes.append("external_lean_contention_risk")
    if len(drain) >= drain_warn_count:
        risk_classes.append("concurrent_drain_processes_observed")

    return {
        "schema": "leanmill-heavy-lean-process-pressure-v1",
        "observed_at_epoch": _now(),
        "pgrep_error": pgrep_error,
        "drain_process_count": len(drain),
        "repl_process_count": len(repl),
        "repl_group_count": repl_group_count,
        "external_lean_process_count": len(external),
        "other_matched_process_count": len(other),
        "risk_classes": risk_classes,
        "thresholds": {
            "heavy_lean_pressure_drain_warn_count": drain_warn_count,
            "heavy_lean_pressure_repl_warn_count": repl_warn_count,
            "heavy_lean_pressure_external_warn_enabled": external_warn_enabled,
        },
        "examples": {
            "drain": [line[:240] for line in drain[:6]],
            "repl": [line[:240] for line in repl[:6]],
            "external_lean": [line[:240] for line in external[:4]],
            "other": [line[:240] for line in other[:4]],
        },
        "interpretation": (
            "If drains and REPLs are both >1, proof cycle time may be dominated by heavy-Lean slot contention "
            "and idle warm REPL pressure rather than by individual proof-row difficulty."
        ),
    }


def _stats(values: list[float]) -> dict[str, Any]:
    vals = sorted(v for v in values if isinstance(v, (int, float)) and math.isfinite(float(v)))
    if not vals:
        return {"n": 0, "mean": None, "p50": None, "p90": None, "p95": None, "max": None}

    def pct(p: float) -> float:
        if len(vals) == 1:
            return round(vals[0], 3)
        rank = (p / 100.0) * (len(vals) - 1)
        lo = int(rank)
        hi = min(lo + 1, len(vals) - 1)
        frac = rank - lo
        return round(vals[lo] + frac * (vals[hi] - vals[lo]), 3)

    return {
        "n": len(vals),
        "mean": round(sum(vals) / len(vals), 3),
        "p50": pct(50),
        "p90": pct(90),
        "p95": pct(95),
        "max": round(max(vals), 3),
    }


def _payload(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        obj = row.get("payload") or {}
        if isinstance(obj, dict):
            return obj
        raw = row.get("payload_json") or "{}"
    else:
        raw = row["payload_json"] or "{}"
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _policy_intelligence(policy: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(policy, dict):
        policy = {}
    obj = policy.get("intelligence") or {}
    if not isinstance(obj, dict):
        obj = {}
    operations = _dict_field(policy, "operations")
    priority_policy = priority_policy_from_policy(policy)
    active_meta_reasoning_loop = (
        operations.get("active_meta_reasoning_loop")
        if isinstance(operations.get("active_meta_reasoning_loop"), dict)
        else {}
    )
    recommendation_priorities_raw = (
        priority_policy.get("recommendations")
        if isinstance(priority_policy.get("recommendations"), dict)
        else {}
    )
    recommendation_priorities: dict[str, int] = {}
    for key, value in recommendation_priorities_raw.items():
        try:
            recommendation_priorities[str(key)] = int(value)
        except (TypeError, ValueError):
            continue

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    def float_value(key: str, fallback: float) -> float:
        try:
            return float(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    return {
        "agent_output_reject_root_cause_min_count": max(1, int_value("agent_output_reject_root_cause_min_count", 3)),
        "agent_output_reject_root_cause_min_rate": max(0.0, float_value("agent_output_reject_root_cause_min_rate", 0.2)),
        "priority_policy": priority_policy,
        "recommendation_priorities": recommendation_priorities,
        "active_meta_reasoning_loop": active_meta_reasoning_loop,
    }


def _recommendation_priority(payload: dict[str, Any], key: str, fallback: int) -> int:
    intelligence_policy = _dict_field(payload, "intelligence_policy")
    priorities = (
        intelligence_policy.get("recommendation_priorities")
        if isinstance(intelligence_policy.get("recommendation_priorities"), dict)
        else {}
    )
    try:
        return int(priorities.get(key) if priorities.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def _station_for_kind(kind: str) -> str:
    for station, spec in STATION_KIND_MAP.items():
        if kind in spec["kinds"]:
            return station
    return "unmapped"


def _queue_rows(cx: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(cx.execute("SELECT * FROM work_items ORDER BY created_at ASC").fetchall())


def _event_index(events: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for event in events:
        work_id = str(event.get("work_id") or "")
        if not work_id:
            continue
        ts = int(event.get("timestamp") or 0)
        if ts <= 0:
            continue
        event_type = str(event.get("event_type") or "")
        rec = out.setdefault(work_id, {})
        if "enqueued" in event_type and "enqueued" not in rec:
            rec["enqueued"] = ts
        if event_type.endswith("_started") and "started" not in rec:
            rec["started"] = ts
        if event_type.endswith(("_done", "_failed", "_rejected")) or event_type in {
            "source_search_integrator_done",
            "source_binding_ingest_rejected",
            "source_binding_probe_enqueued",
        }:
            rec["terminal"] = ts
    return out


def _build_subprocess_metrics(rows: list[sqlite3.Row], events: list[dict[str, Any]], *, trailing_window_s: int) -> dict[str, Any]:
    now = _now()
    event_times = _event_index(events)
    by_kind: dict[str, list[sqlite3.Row]] = defaultdict(list)
    by_station: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        kind = str(row["kind"])
        by_kind[kind].append(row)
        by_station[_station_for_kind(kind)].append(row)

    def summarize(group_rows: list[sqlite3.Row], *, station: str | None = None) -> dict[str, Any]:
        status_counts = Counter(str(row["status"]) for row in group_rows)
        lead: list[float] = []
        cycle: list[float] = []
        wait: list[float] = []
        open_age: list[float] = []
        terminal_recent = 0
        for row in group_rows:
            work_id = str(row["work_id"])
            created = int(row["created_at"])
            updated = int(row["updated_at"])
            status = str(row["status"])
            ev = event_times.get(work_id) or {}
            started = int(ev.get("started") or 0)
            terminal = int(ev.get("terminal") or 0) or (updated if status in TERMINAL_STATUSES else 0)
            if status in TERMINAL_STATUSES:
                lead.append(max(0, updated - created))
                if terminal >= now - trailing_window_s:
                    terminal_recent += 1
                if started:
                    cycle.append(max(0, terminal - started))
                    wait.append(max(0, started - created))
                else:
                    cycle.append(max(0, updated - created))
            elif status in OPEN_STATUSES:
                open_age.append(max(0, now - created))
        sla = None
        breach = False
        if station and station in STATION_KIND_MAP:
            sla = STATION_KIND_MAP[station]["sla_p95_s"]
            p95 = _stats(lead)["p95"]
            breach = bool(p95 is not None and p95 > sla)
        return {
            "count": len(group_rows),
            "status_counts": dict(sorted(status_counts.items())),
            "open_count": sum(status_counts.get(s, 0) for s in OPEN_STATUSES),
            "terminal_recent_count": terminal_recent,
            "terminal_recent_per_hour": round(terminal_recent * 3600.0 / max(1, trailing_window_s), 3),
            "lead_time_to_terminal_s": _stats(lead),
            "active_cycle_time_s": _stats(cycle),
            "wait_before_start_s": _stats(wait),
            "open_age_s": _stats(open_age),
            "sla_p95_s": sla,
            "sla_breached": breach,
        }

    return {
        "by_station": {station: summarize(items, station=station) for station, items in sorted(by_station.items())},
        "by_kind": {kind: summarize(items) for kind, items in sorted(by_kind.items())},
    }


def _phase_timing_read_model() -> dict[str, Any]:
    """Time-to-insight decomposition: WHERE the wall-clock went inside a campaign, per phase
    (formalize / pool / native / verify / govern.mnc / decompose / bank / ...), plus a per-run lead time. Sourced
    from the SHARED phase-timing ledger (`common.telemetry`, emitted by the solver). Pure read; this stays a
    read-model (no Lean, no models, no mutation). Empty shape if the ledger is absent (telemetry off / fresh repo)."""
    try:
        from src.ztare.leanmill.phase_timing import summarize_phase_timings
        return summarize_phase_timings()
    except Exception:  # noqa: BLE001 — surfacing must never break the read model
        return {"phases": {}, "runs": {}, "total_wall_s": 0.0, "total_events": 0}


_EMPTY_CYCLE_TIME = {"schema": "leanmill-campaign-cycle-time-v1", "campaigns": {}, "by_domain": {}, "campaign_count": 0}


def _campaign_cycle_time_read_model() -> dict[str, Any]:
    """Per-campaign TIME-TO-CLOSURE — the factory 'time to insight on closures' metric, segmented by DOMAIN
    (math vs non-math formalization). Joins the solver attempts ledger (sqlite: run_tag / attempt_at / outcome /
    wallclock_s — the closure timing + compute cost) with the phase ledger's `campaign` domain markers. Pure
    read, fail-soft (empty shape if a source is absent); the computation lives in `phase_timing` (single door)."""
    try:
        db = REPO / "analytics" / "public" / "queries" / "solver_lane_attempts.db"
        if not db.exists():
            return dict(_EMPTY_CYCLE_TIME)
        cx = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in cx.execute("PRAGMA table_info(attempts)").fetchall()}
            if not {"run_tag", "attempt_at", "outcome", "wallclock_s"}.issubset(cols):
                return dict(_EMPTY_CYCLE_TIME)
            rows = [dict(zip(("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s"), r))
                    for r in cx.execute(
                        "SELECT run_tag, attempt_at, outcome, ratified, wallclock_s FROM attempts").fetchall()]
        finally:
            cx.close()
        from src.ztare.leanmill.phase_timing import summarize_campaign_cycle_time
        return summarize_campaign_cycle_time(rows)
    except Exception as _e:  # noqa: BLE001 — surfacing must never break the read model
        return {**_EMPTY_CYCLE_TIME, "error": repr(_e)[:160]}


def denotation_rollup(roots: "list[Path] | None" = None) -> dict[str, Any]:
    """DENOTATION-PINNED FRACTION — the repo-level headline behind architecture §4.2b: of the formalizations
    whose built defs the def-denotation REPORTER measured, what fraction is PINNED by a kernel-verified
    external anchor? Verdicts persist ONLY in the per-run `<notes>.autoformalize_result.json` artifacts
    written by `ztare.leanmill.solver.autoformalize_notes.main` (`res["denotation"]` — advisory telemetry,
    never a gate), so this scans those; there is no jsonl store. Artifacts with `denotation: null` (check
    off / non-theory-first run) are EXCLUDED — "reporter never ran" must not be laundered as NOT_APPLICABLE.
    `pinned_fraction` denominator = pinned+underdetermined+refuted (NOT_APPLICABLE has no built defs →
    nothing to pin); None when no applicable rows. Pure read-model: never writes, never gates, no Lean.
    NOTE: the laptop's artifacts are a stale synced snapshot — the authoritative run is on the VPS repo."""
    counts = {"pinned": 0, "underdetermined": 0, "refuted": 0, "not_applicable": 0}
    key = {"PINNED": "pinned", "UNDERDETERMINED": "underdetermined",
           "REFUTED": "refuted", "NOT_APPLICABLE": "not_applicable"}
    prune = {".git", ".lake", ".venv", "node_modules", "__pycache__", "lake-packages", "build"}
    for root in (roots if roots is not None else [REPO]):
        # ponytail: full-repo walk (~seconds, pruned); index the artifacts if this ever gets hot.
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in prune]
            for fn in filenames:
                if not fn.endswith(".autoformalize_result.json"):
                    continue
                try:
                    den = (json.loads((Path(dirpath) / fn).read_text(encoding="utf-8")) or {}).get("denotation")
                except Exception:  # noqa: BLE001 — one unreadable artifact must never break the read model
                    continue
                k = key.get(str((den or {}).get("verdict"))) if isinstance(den, dict) else None
                if k:
                    counts[k] += 1
    applicable = counts["pinned"] + counts["underdetermined"] + counts["refuted"]
    return {**counts,
            "pinned_fraction": (counts["pinned"] / applicable) if applicable else None,
            "n_formalizations": sum(counts.values())}


def _extract_scoreboard_from_stdout(text: str) -> dict[str, int]:
    obj: Any = None
    try:
        obj = json.loads(text.strip())
    except json.JSONDecodeError:
        for line in reversed(str(text or "").splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            break
    if not isinstance(obj, dict):
        return {}
    return _extract_scoreboard_counts(obj)


def _extract_scoreboard_counts(obj: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for key in (
        "compile_candidate_count",
        "ratified_closure_count",
        "exact_gap_candidate_count",
        "valid_falsifier_count",
        "negative_control_fail_count",
        "negative_control_unexpected_pass_count",
        "negative_control_invalid_fail_count",
    ):
        value = obj.get(key)
        if isinstance(value, int):
            out[key] = value
    return out


def _scoreboard_counts_from_payload(payload: dict[str, Any]) -> dict[str, int]:
    counts = Counter(_extract_scoreboard_counts(payload))
    result = payload.get("result") or {}
    if isinstance(result, dict):
        counts.update(_extract_scoreboard_from_stdout(str(result.get("stdout_tail") or "")))
    scoreboard_path = str(payload.get("scoreboard") or "")
    if scoreboard_path:
        scoreboard_obj = _read_json(scoreboard_path)
        if isinstance(scoreboard_obj, dict):
            counts.update(_extract_scoreboard_counts(scoreboard_obj))
    return dict(counts)


def _tail_text(value: Any, limit: int = 900) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def _probe_failure_evidence_from_payload(payload: dict[str, Any], *, row_id: str = "", limit: int = 2) -> list[dict[str, Any]]:
    root = Path(str(payload.get("root") or ""))
    rows_dir = root / "rows"
    if not rows_dir.exists() or not rows_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(rows_dir.glob("*.json")):
        if len(out) >= limit:
            break
        obj = _read_json(path)
        if not isinstance(obj, dict):
            continue
        obj_row_id = str(obj.get("row_id") or "")
        if row_id and obj_row_id and obj_row_id != row_id:
            continue
        for rec in obj.get("results") or []:
            if len(out) >= limit:
                break
            if not isinstance(rec, dict) or rec.get("closed"):
                continue
            repl_errors = rec.get("repl_errors") if isinstance(rec.get("repl_errors"), list) else []
            out.append({
                "row_id": obj_row_id or row_id or rec.get("row_id"),
                "candidate": rec.get("candidate"),
                "action_family": rec.get("action_family"),
                "driver_path": rec.get("driver_path"),
                "body_tail": _tail_text(rec.get("body") or rec.get("body_tail")),
                "stdout_tail": _tail_text(rec.get("stdout") or rec.get("stdout_tail")),
                "stderr_tail": _tail_text(rec.get("stderr") or rec.get("stderr_tail")),
                "repl_error_tail": _tail_text("\n".join(str(err.get("data") or err) if isinstance(err, dict) else str(err) for err in repl_errors)),
                "error_class": rec.get("error_class"),
            })
    return learning_feedback.compact_failure_evidence(out, limit=limit)


def _infer_learning_exit(payload: dict[str, Any]) -> str:
    merged = dict(payload)
    merged.update(_scoreboard_counts_from_payload(payload))
    exit_kind = learning_feedback.learning_exit_from_counts(merged)
    return "" if exit_kind == "unknown" else exit_kind


def _exit_bucket(exit_kind: str) -> str:
    if not exit_kind:
        return ""
    if exit_kind in PROOF_VALUE_EXIT_KINDS:
        return "proof_value_exit_counts"
    if exit_kind in TESTED_LEARNING_EXIT_KINDS:
        return "tested_learning_exit_counts"
    if exit_kind in TERMINAL_DECISION_EXIT_KINDS:
        return "terminal_decision_counts"
    if exit_kind in INTERMEDIATE_EXIT_KINDS:
        return "intermediate_flow_counts"
    return "uncategorized_terminal_exit_counts"


def _merge_max_counts(dst: Counter, src: dict[str, int]) -> None:
    for key, value in src.items():
        dst[key] = max(int(dst.get(key, 0)), int(value or 0))


def _probe_value_key(*, work_id: str, payload: dict[str, Any]) -> str:
    """Return a stable key for de-duplicating replayed probe value."""
    signature = str(payload.get("probe_signature") or "")
    if signature:
        return f"probe_signature:{signature}"
    return f"work:{work_id}"


def _learning_unit_flow(rows: list[sqlite3.Row], events: list[dict[str, Any]], *, trailing_window_s: int) -> dict[str, Any]:
    now = _now()
    event_counts = Counter(str(e.get("event_type") or "") for e in events if int(e.get("timestamp") or 0) >= now - trailing_window_s)
    source_ready = 0
    source_holds_with_ready = 0
    source_bound = event_counts.get("source_to_canary_binding_enqueued", 0)
    binding_probe = event_counts.get("source_binding_probe_enqueued", 0)
    probe_done = event_counts.get("probe_worker_done", 0)
    scoreboard_by_work: dict[str, Counter] = defaultdict(Counter)
    scoreboard_by_value_key: dict[str, Counter] = defaultdict(Counter)
    for event in events:
        if int(event.get("timestamp") or 0) < now - trailing_window_s:
            continue
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if payload.get("exit_kind") == "qualified_source_candidates":
            static_summary = ((payload.get("result") or {}).get("summary") or {}).get("static_summary") or {}
            source_ready += int(static_summary.get("canary_ready_total") or 0)
        if str(payload.get("exit_kind") or "") == "source_search_integrated_hold":
            source_holds_with_ready += 1
        counts = _scoreboard_counts_from_payload(payload)
        if counts:
            work_id = str(event.get("work_id") or event.get("event_id") or "")
            _merge_max_counts(scoreboard_by_work[work_id], counts)
    terminal_payload_counts = Counter()
    exit_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    unique_exit_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    seen_exit_value_keys: set[tuple[str, str, str]] = set()
    for row in rows:
        if int(row["updated_at"]) < now - trailing_window_s or row["status"] not in TERMINAL_STATUSES:
            continue
        payload = _payload(row)
        work_id = str(row["work_id"])
        exit_kind = str(payload.get("exit_kind") or "")
        if exit_kind:
            terminal_payload_counts[exit_kind] += 1
        learning_exit = _infer_learning_exit(payload)
        if learning_exit:
            bucket = _exit_bucket(learning_exit)
            if bucket:
                exit_buckets[bucket][learning_exit] += 1
                value_key = _probe_value_key(work_id=work_id, payload=payload)
                dedupe_key = (bucket, learning_exit, value_key)
                if dedupe_key not in seen_exit_value_keys:
                    seen_exit_value_keys.add(dedupe_key)
                    unique_exit_buckets[bucket][learning_exit] += 1
        counts = _scoreboard_counts_from_payload(payload)
        if counts:
            _merge_max_counts(scoreboard_by_work[work_id], counts)
            _merge_max_counts(scoreboard_by_value_key[_probe_value_key(work_id=work_id, payload=payload)], counts)
    learning_exit_counts = Counter()
    for bucket in ("proof_value_exit_counts", "tested_learning_exit_counts", "terminal_decision_counts"):
        learning_exit_counts.update(exit_buckets.get(bucket, Counter()))
    recent_scoreboard = Counter()
    for counts in scoreboard_by_work.values():
        recent_scoreboard.update(counts)
    unique_probe_scoreboard = Counter()
    for counts in scoreboard_by_value_key.values():
        unique_probe_scoreboard.update(counts)
    return {
        "window_s": trailing_window_s,
        "source_canary_ready_candidates": source_ready,
        "source_search_holds_with_ready_candidates": source_holds_with_ready,
        "source_to_canary_binding_enqueued": source_bound,
        "source_binding_probe_enqueued": binding_probe,
        "probe_worker_done": probe_done,
        "scoreboard_tail_counts": dict(sorted(recent_scoreboard.items())),
        "unique_probe_signature_scoreboard_counts": dict(sorted(unique_probe_scoreboard.items())),
        "terminal_exit_counts": dict(sorted(terminal_payload_counts.items())),
        "learning_unit_exit_counts": dict(sorted(learning_exit_counts.items())),
        "proof_value_exit_counts": dict(sorted(exit_buckets.get("proof_value_exit_counts", Counter()).items())),
        "unique_proof_value_exit_counts": dict(sorted(unique_exit_buckets.get("proof_value_exit_counts", Counter()).items())),
        "tested_learning_exit_counts": dict(sorted(exit_buckets.get("tested_learning_exit_counts", Counter()).items())),
        "unique_tested_learning_exit_counts": dict(sorted(unique_exit_buckets.get("tested_learning_exit_counts", Counter()).items())),
        "terminal_decision_counts": dict(sorted(exit_buckets.get("terminal_decision_counts", Counter()).items())),
        "unique_terminal_decision_counts": dict(sorted(unique_exit_buckets.get("terminal_decision_counts", Counter()).items())),
        "intermediate_flow_counts": dict(sorted(exit_buckets.get("intermediate_flow_counts", Counter()).items())),
        "uncategorized_terminal_exit_counts": dict(sorted(exit_buckets.get("uncategorized_terminal_exit_counts", Counter()).items())),
        "ops_exit_counts": dict(sorted(Counter({
            k: v
            for k, v in exit_buckets.get("intermediate_flow_counts", Counter()).items()
            if k in OPS_EXIT_KINDS
        }).items())),
        "no_laundering_accounting_note": (
            "proposal/source/agent-note exits are intermediate_flow_counts, not learning_unit_exit_counts; "
            "proof value requires Governance Gate scoreboard evidence; unique_* counts de-duplicate repeated probe signatures"
        ),
    }


def _proof_lane_rca(rows: list[sqlite3.Row], backlog_replenisher: dict[str, Any], factory_policy: dict[str, Any], *, trailing_window_s: int) -> dict[str, Any]:
    now = _now()
    lane_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    lane_open: dict[str, Counter[str]] = defaultdict(Counter)
    signatures: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        payload = _payload(row)
        kind = str(row["kind"])
        lane = str(payload.get("probe_lane") or "")
        if kind not in {"repair_canary_probe", "proof_probe"} and not lane:
            continue
        lane = lane or "unknown"
        status = str(row["status"])
        family = str(row["family"] or payload.get("family") or "")
        row_id = str(payload.get("row_id") or payload.get("target_row_id") or "")
        sig = str(payload.get("probe_signature") or "")
        if not sig:
            sig = f"{family}:{row_id}" if (family or row_id) else str(row["work_id"])
        if status in OPEN_STATUSES:
            lane_open[lane][status] += 1
            signatures[lane].add(sig)
        if int(row["updated_at"]) < now - trailing_window_s:
            continue
        if status in TERMINAL_STATUSES:
            lane_outcomes[lane][_infer_learning_exit(payload) or str(payload.get("exit_kind") or status)] += 1
            signatures[lane].add(sig)
        if len(examples[lane]) < 8:
            examples[lane].append({
                "work_id": str(row["work_id"]),
                "status": status,
                "family": family,
                "row_id": row_id,
                "probe_signature": sig,
                "learning_exit": _infer_learning_exit(payload),
                "updated_at_epoch": int(row["updated_at"]),
            })
    profiles = (factory_policy.get("profiles") or {}) if isinstance(factory_policy, dict) else {}
    runner = ((profiles.get("supervised_24x7") or {}).get("runner") or {}) if isinstance(profiles, dict) else {}
    try:
        family_spec_workers = int(runner.get("family_spec_probe_workers") or 1)
    except (TypeError, ValueError):
        family_spec_workers = 1
    try:
        family_spec_floor = int(runner.get("family_spec_probe_floor") or 2)
    except (TypeError, ValueError):
        family_spec_floor = 2
    candidate_pool = backlog_replenisher.get("candidate_pool") if isinstance(backlog_replenisher, dict) else {}
    if not isinstance(candidate_pool, dict):
        candidate_pool = {}
    generated = int(candidate_pool.get("generated") or candidate_pool.get("candidate_count") or 0)
    enqueued = int(candidate_pool.get("enqueued") or 0)
    blockers: list[str] = []
    family_spec_value = sum(int(lane_outcomes.get("family_spec", Counter()).get(k, 0)) for k in PROOF_VALUE_EXIT_KINDS)
    family_spec_terminal = sum(lane_outcomes.get("family_spec", Counter()).values())
    family_spec_open = sum(lane_open.get("family_spec", Counter()).values())
    family_spec_diversity = len(signatures.get("family_spec", set()))
    source_terminal = sum(lane_outcomes.get("source_binding", Counter()).values())
    source_value = sum(int(lane_outcomes.get("source_binding", Counter()).get(k, 0)) for k in PROOF_VALUE_EXIT_KINDS)
    if generated and enqueued == 0:
        blockers.append("candidate_pool_generated_zero_enqueued")
    if family_spec_diversity < 4 and (family_spec_workers > 1 or family_spec_floor > 2):
        blockers.append("family_spec_candidate_signature_diversity_below_scale_floor")
    if family_spec_open > family_spec_workers:
        blockers.append("family_spec_probe_drain_backlog")
    if source_terminal and source_value == 0:
        blockers.append("source_binding_recent_zero_governed_value")
    if family_spec_terminal and family_spec_value == 0:
        blockers.append("family_spec_recent_zero_governed_value")
    if family_spec_value > 0 and not blockers:
        bottleneck_class = "proof_lane_operational"
    elif "candidate_pool_generated_zero_enqueued" in blockers or "family_spec_candidate_signature_diversity_below_scale_floor" in blockers:
        bottleneck_class = "proof_candidate_supply_blocked"
    elif "family_spec_probe_drain_backlog" in blockers:
        bottleneck_class = "family_spec_probe_drain_limited"
    elif "source_binding_recent_zero_governed_value" in blockers:
        bottleneck_class = "source_binding_zero_value"
    else:
        bottleneck_class = "proof_lane_unproven_current_window"
    return {
        "schema": "leanmill-proof-lane-rca-v1",
        "window_s": trailing_window_s,
        "bottleneck_class": bottleneck_class,
        "blockers": blockers,
        "family_spec_probe_workers_policy": family_spec_workers,
        "family_spec_probe_floor_policy": family_spec_floor,
        "family_spec_candidate_signature_diversity": family_spec_diversity,
        "lane_outcomes": {lane: dict(sorted(counter.items())) for lane, counter in sorted(lane_outcomes.items())},
        "lane_open": {lane: dict(sorted(counter.items())) for lane, counter in sorted(lane_open.items())},
        "candidate_pool": candidate_pool,
        "examples": {lane: vals for lane, vals in sorted(examples.items())},
        "scale_readiness": {
            "safe_to_increase_workers": bottleneck_class in {"proof_lane_operational", "family_spec_probe_drain_limited"} and family_spec_diversity >= 4,
            "requires_candidate_supply_repair": bottleneck_class == "proof_candidate_supply_blocked",
            "requires_source_binding_repair": bottleneck_class == "source_binding_zero_value",
        },
    }


def _integration_loss_summary(integration_dir: str | Path, *, max_files: int) -> dict[str, Any]:
    root = Path(integration_dir)
    if not root.exists():
        return {"receipt_count": 0, "held_receipts": 0, "ready_held_count": 0, "blockers": {}, "recent_ready_holds": []}
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max(1, int(max_files))]
    blockers = Counter()
    ready_holds: list[dict[str, Any]] = []
    held = 0
    for path in files:
        obj = _read_json(path)
        if not isinstance(obj, dict):
            continue
        decision = str(obj.get("integration_decision") or "")
        ready = int(((obj.get("source_search_summary") or {}).get("ready_total")) or 0)
        if decision != "enqueue_source_to_canary_binding":
            held += 1
            for blocker in obj.get("integration_blockers") or ["hold_without_structured_blocker"]:
                blockers[str(blocker)] += 1
            if ready:
                ready_holds.append({
                    "family": obj.get("family"),
                    "ready_total": ready,
                    "blockers": obj.get("integration_blockers") or [],
                    "receipt": str(path),
                    "source_search_work_id": obj.get("source_search_work_id"),
                })
    return {
        "receipt_count": len(files),
        "held_receipts": held,
        "ready_held_count": len(ready_holds),
        "blockers": dict(sorted(blockers.items(), key=lambda kv: (-kv[1], kv[0]))),
        "recent_ready_holds": ready_holds[:8],
    }


def _source_query_gate_failures(events: list[dict[str, Any]], *, trailing_window_s: int) -> dict[str, Any]:
    now = _now()
    failure_classes = Counter()
    records: list[dict[str, Any]] = []
    for event in reversed(events):
        if int(event.get("timestamp") or 0) < now - trailing_window_s:
            continue
        if str(event.get("event_type") or "") != "source_search_task_not_enqueued_query_gate":
            continue
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        for item in payload.get("query_quality") or []:
            if not isinstance(item, dict) or bool(item.get("accepted", True)):
                continue
            for failure in item.get("failures") or ["unknown_query_gate_failure"]:
                failure_classes[str(failure).split(":", 1)[0]] += 1
        records.append({
            "work_id": event.get("work_id"),
            "family": payload.get("family"),
            "accepted_query_count": payload.get("accepted_query_count"),
            "target_row_count": payload.get("target_row_count"),
            "reason": payload.get("reason"),
            "failure_classes": dict(failure_classes),
            "proposal_path": payload.get("proposal_path"),
        })
    return {
        "event_count": len(records),
        "failure_classes": dict(sorted(failure_classes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "recent": records[:8],
    }


def _conversion_diagnostics(
    rows: list[sqlite3.Row],
    events: list[dict[str, Any]],
    observability: dict[str, Any],
    family_promotion_diagnostics: dict[str, Any],
    intelligence_policy: dict[str, Any],
    *,
    trailing_window_s: int,
) -> dict[str, Any]:
    now = _now()
    stage_counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_binding = _dict_field(observability, "source_binding")
    source_query_gate = _source_query_gate_failures(events, trailing_window_s=trailing_window_s)

    for row in rows:
        if int(row["updated_at"]) < now - trailing_window_s:
            continue
        payload = _payload(row)
        kind = str(row["kind"])
        status = str(row["status"])
        work_id = str(row["work_id"])
        family = str(row["family"] or payload.get("family") or "")
        exit_kind = str(payload.get("exit_kind") or payload.get("learning_unit_exit") or status)
        probe_lane = str(payload.get("probe_lane") or "")

        stage = ""
        outcome = exit_kind
        if kind in {"llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"}:
            stage = "proposal_contract"
            if work_id.startswith("agent_output_review:"):
                stage = "agent_output_to_proposal_contract"
            if str(payload.get("reason") or "").startswith("api_runtime_error") or "api_runtime_error" in json.dumps(payload)[:2000]:
                outcome = "api_runtime_error"
            if exit_kind == "codex_cli_fallback_failed":
                outcome = "codex_cli_fallback_failed"
        elif kind == "source_search_task":
            stage = "source_search"
        elif kind == "source_scout_task":
            ingest_status = str(payload.get("source_binding_ingest_status") or "")
            if ingest_status:
                stage = "source_binding_ingest"
                outcome = ingest_status
        elif kind in {"repair_canary_probe", "proof_probe"} or probe_lane:
            stage = f"probe_{probe_lane or 'unknown'}"
            outcome = _infer_learning_exit(payload) or exit_kind
        elif kind == "agent_repair_task":
            stage = "subscription_agent_task"
        elif kind == "gm_operator_task":
            stage = "gm_operator_task"

        if not stage:
            continue
        stage_counts[stage][outcome] += 1
        if len(examples[stage]) < 5 and status in TERMINAL_STATUSES:
            examples[stage].append({
                "work_id": work_id,
                "family": family,
                "status": status,
                "outcome": outcome,
            })

    root_causes: list[dict[str, Any]] = []
    agent_review = stage_counts.get("agent_output_to_proposal_contract", Counter())
    agent_rejects = int(agent_review.get("proposal_rejected", 0))
    agent_review_total = sum(agent_review.values())
    reject_rate = agent_rejects / max(1, agent_review_total)
    min_rejects = int(intelligence_policy.get("agent_output_reject_root_cause_min_count") or 3)
    min_reject_rate = float(intelligence_policy.get("agent_output_reject_root_cause_min_rate") or 0.2)
    if agent_rejects and agent_rejects >= min_rejects and reject_rate >= min_reject_rate:
        root_causes.append({
            "class": "agent_outputs_fail_typed_proposal_contract",
            "count": agent_rejects,
            "interpretation": "subscription agents are producing useful prose or candidate notes, but the proposal boundary rejects the artifact before source/probe work can consume it",
            "next_action": "force agent tasks to emit source-query objects with accepted theorem/declaration shape or route them to GM decomposition instead of source search",
            "reject_rate": round(reject_rate, 3),
        })
    if source_query_gate["event_count"]:
        root_causes.append({
            "class": "source_query_gate_blocks_source_work",
            "count": source_query_gate["event_count"],
            "interpretation": "proposal JSON passed the outer shape but did not contain at least three accepted typed source queries plus target rows",
            "next_action": "repair source-query generation around the observed query-contract failure classes",
            "failure_classes": source_query_gate["failure_classes"],
        })
    rejected_count = int(source_binding.get("rejected_count") or 0)
    if rejected_count:
        root_causes.append({
            "class": "source_binding_artifacts_do_not_match_receipts",
            "count": rejected_count,
            "interpretation": "source binding artifacts name candidates or target rows that the receipt/corpus gate cannot verify",
            "next_action": "bind only allowlisted candidate_names and allowed_binding_target_rows from the integration receipt",
            "failure_classes": source_binding.get("failure_classes") or {},
        })
    source_probe = stage_counts.get("probe_source_binding", Counter())
    source_probe_total = sum(source_probe.values())
    source_probe_value = sum(int(source_probe.get(k, 0)) for k in ("ratified_closure", "exact_gap_candidate", "valid_falsifier"))
    if source_probe_total and source_probe_value == 0:
        root_causes.append({
            "class": "source_bound_probes_have_zero_governed_value",
            "count": source_probe_total,
            "interpretation": "some source candidates reach Proof Execution, but recent bound probes produce no governed closure/gap/falsifier",
            "next_action": "pause source binding for exhausted families until sibling or target evidence changes the candidate shape",
            "outcomes": dict(source_probe),
        })
    promotion = family_promotion_diagnostics
    if promotion.get("validated_family_blocked"):
        root_causes.append({
            "class": "validated_family_path_blocked_by_missing_heldout_receipts",
            "count": len(promotion.get("heldout_blocked_families") or []),
            "interpretation": promotion.get("interpretation"),
            "next_action": "source or construct a truly independent heldout row, then emit a heldout receipt only if the gate can certify independence and governance evidence",
        })
    runner_failures = int((observability.get("runner") or {}).get("command_failure_count") or 0)
    if runner_failures:
        root_causes.append({
            "class": "runner_command_failure_blocks_conversion",
            "count": runner_failures,
            "interpretation": "station command failures can prevent otherwise valid work from entering downstream lanes",
            "next_action": "fix the station command before judging candidate quality",
            "examples": (observability.get("runner") or {}).get("command_failures") or [],
        })
    version_health = _dict_field(observability, "worker_version_health")
    stale_process_count = int(version_health.get("stale_process_count") or 0)
    if stale_process_count:
        root_causes.append({
            "class": "stale_worker_runtime_detected",
            "count": stale_process_count,
            "interpretation": "one or more workers started before the latest watched LeanMill source/spec/family update",
            "next_action": "restart stale worker sessions before trusting new invariants or comparing conversion rates",
            "examples": version_health.get("stale_processes") or [],
        })
    runtime_mismatch_count = int(version_health.get("runtime_mismatch_count") or 0)
    if runtime_mismatch_count:
        root_causes.append({
            "class": "worker_runtime_version_mismatch",
            "count": runtime_mismatch_count,
            "interpretation": "one or more workers report a different watched-source hash or git head than the current control process",
            "next_action": "restart mismatched worker sessions before trusting newly enforced invariants",
            "examples": version_health.get("runtime_mismatches") or [],
        })

    return {
        "schema": "leanmill-conversion-diagnostics-v1",
        "window_s": trailing_window_s,
        "stage_outcome_counts": {
            stage: dict(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))
            for stage, counter in sorted(stage_counts.items())
        },
        "source_query_gate_failures": source_query_gate,
        "source_binding_failure_classes": source_binding.get("failure_classes") or {},
        "examples": dict(examples),
        "non_blocking_signals": {
            "agent_output_reject_count": agent_rejects,
            "agent_output_review_total": agent_review_total,
            "agent_output_reject_rate": round(reject_rate, 3),
            "agent_output_reject_root_cause_threshold": {
                "min_count": min_rejects,
                "min_rate": min_reject_rate,
            },
        },
        "root_causes": root_causes,
        "operator_role_boundary": {
            "gm_is_not_a_proof_oracle": True,
            "gm_advantage": "cross-station diagnosis, prompt/schema repair, scheduler changes, and queue-visible comparator work",
            "proof_value_rule": "GM, API LLM, and subscription-agent outputs all require Proof Execution plus Governance Gate before proof credit",
        },
    }


def _family_promotion_diagnostics(registry: dict[str, Any], heldout_scout: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(registry, dict):
        return {"available": False}
    status_counts = registry.get("status_counts") or {}
    families = registry.get("families") or []
    if isinstance(families, dict):
        family_rows = list(families.values())
    elif isinstance(families, list):
        family_rows = [f for f in families if isinstance(f, dict)]
    else:
        family_rows = []
    heldout_events = int(registry.get("heldout_receipt_events") or 0)
    scout = heldout_scout if isinstance(heldout_scout, dict) else {}
    scout_family_count = int(scout.get("family_count") or 0) if scout else 0
    scout_eligible_family_count = int(scout.get("eligible_family_count") or 0) if scout else 0
    scout_enqueued_gm_tasks = len(scout.get("enqueued_gm_tasks") or []) if scout else 0
    blocked: list[dict[str, Any]] = []
    seed_generalization_needed: list[dict[str, Any]] = []
    for family in family_rows:
        status = str(family.get("status") or "")
        next_required = str(family.get("next_required_evidence") or "")
        rec = {
            "family": family.get("family") or family.get("repair_family") or family.get("name"),
            "status": status,
            "next_required_evidence": next_required,
            "heldout_attempts": family.get("heldout_attempts"),
            "heldout_successes": family.get("heldout_successes"),
            "unique_ratified_rows": family.get("unique_ratified_rows"),
            "ratified_rows": family.get("ratified_rows"),
        }
        if status == "candidate_family" or "heldout" in next_required:
            blocked.append(rec)
        if status == "seed_only" and "heldout" in next_required:
            seed_generalization_needed.append(rec)
    seed_generalization_gap = bool(seed_generalization_needed) and scout_family_count == 0
    return {
        "available": True,
        "status_counts": status_counts,
        "heldout_receipt_events": heldout_events,
        "validated_family_count": int(status_counts.get("validated_family") or 0),
        "validated_family_blocked": heldout_events == 0,
        "heldout_blocked_families": blocked[:12],
        "seed_generalization_needed_count": len(seed_generalization_needed),
        "seed_generalization_needed_families": seed_generalization_needed[:12],
        "heldout_scout": {
            "available": bool(scout),
            "family_count": scout_family_count,
            "eligible_family_count": scout_eligible_family_count,
            "enqueued_gm_tasks": scout_enqueued_gm_tasks,
        },
        "seed_generalization_gap": seed_generalization_gap,
        "interpretation": (
            "validated-family promotion is blocked because no passing heldout-independence receipts are present"
            if heldout_events == 0 else
            "heldout receipts exist; inspect registry status counts for promotion results"
        ),
    }


def _subscription_agent_usage(rows: list[sqlite3.Row], *, trailing_window_s: int) -> dict[str, Any]:
    now = _now()
    v2_usage_created_times: list[int] = []
    for row in rows:
        if str(row["kind"]) not in SUBSCRIPTION_AGENT_KINDS:
            continue
        usage = _payload(row).get("usage_estimate")
        if isinstance(usage, dict) and str(usage.get("schema") or "") == "leanmill-subscription-agent-usage-estimate-v2":
            v2_usage_created_times.append(int(row["created_at"]))
    missing_usage_floor = min(v2_usage_created_times) if v2_usage_created_times else None
    total_prompt_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_wall_time_s = 0
    launched_count = 0
    open_count = 0
    by_runtime: dict[str, Counter[str]] = defaultdict(Counter)
    by_task_kind: dict[str, Counter[str]] = defaultdict(Counter)
    open_by_kind = Counter()
    open_by_worker = Counter()
    open_by_station = Counter()
    warm_session_requested_count = 0
    warm_session_reused_count = 0
    cold_subscription_call_count = 0
    contract_lane_call_count = 0
    examples: list[dict[str, Any]] = []
    open_examples: list[dict[str, Any]] = []
    missing_usage_terminal_count = 0
    missing_usage_examples: list[dict[str, Any]] = []
    for row in rows:
        kind = str(row["kind"])
        if kind not in SUBSCRIPTION_AGENT_KINDS:
            continue
        payload = _payload(row)
        status = str(row["status"])
        if status in OPEN_STATUSES:
            open_count += 1
            open_by_kind[kind] += 1
            worker = str(row["claimed_by"] or payload.get("worker_id") or "unclaimed")
            station = str(row["station"] or payload.get("station") or "unmapped")
            open_by_worker[worker] += 1
            open_by_station[station] += 1
            if len(open_examples) < 8:
                open_examples.append({
                    "work_id": str(row["work_id"]),
                    "kind": kind,
                    "family": str(row["family"] or payload.get("family") or ""),
                    "station": station,
                    "status": status,
                    "claimed_by": worker,
                    "age_s": max(0, now - int(row["created_at"])),
                    "lease_remaining_s": (
                        max(0, int(row["lease_until"]) - now)
                        if row["lease_until"] is not None else None
                    ),
                    "expected_exit": str(row["expected_exit"] or payload.get("expected_exit") or ""),
                })
        if int(row["updated_at"]) < now - trailing_window_s:
            continue
        usage = payload.get("usage_estimate")
        if not isinstance(usage, dict):
            if (
                status in TERMINAL_STATUSES
                and bool(payload.get("agent_launched"))
                and int(row["created_at"]) >= now - trailing_window_s
                and missing_usage_floor is not None
                and int(row["created_at"]) >= missing_usage_floor
            ):
                missing_usage_terminal_count += 1
                if len(missing_usage_examples) < 8:
                    missing_usage_examples.append({
                        "work_id": str(row["work_id"]),
                        "kind": kind,
                        "family": str(row["family"] or payload.get("family") or ""),
                        "status": status,
                        "exit_kind": str(payload.get("exit_kind") or ""),
                        "updated_at_epoch": int(row["updated_at"]),
                    })
            continue
        launched_count += 1
        runtime = str(usage.get("runtime") or payload.get("runtime") or "unknown")
        task_kind = str(usage.get("task_kind") or kind)
        prompt_tokens = int(usage.get("estimated_prompt_tokens") or 0)
        output_tokens = int(usage.get("estimated_output_tokens") or 0)
        item_tokens = int(usage.get("estimated_total_tokens") or (prompt_tokens + output_tokens))
        wall = int(usage.get("wall_time_s") or 0)
        total_prompt_tokens += prompt_tokens
        total_output_tokens += output_tokens
        total_tokens += item_tokens
        total_wall_time_s += wall
        by_runtime[runtime]["tasks"] += 1
        by_runtime[runtime]["estimated_prompt_tokens"] += prompt_tokens
        by_runtime[runtime]["estimated_output_tokens"] += output_tokens
        by_runtime[runtime]["estimated_total_tokens"] += item_tokens
        by_runtime[runtime]["wall_time_s"] += wall
        by_task_kind[task_kind]["tasks"] += 1
        by_task_kind[task_kind]["estimated_total_tokens"] += item_tokens
        by_task_kind[task_kind]["wall_time_s"] += wall
        warm_requested = bool(usage.get("warm_session_requested"))
        warm_reused = bool(usage.get("warm_session_reused"))
        operator_contract_lane = bool(payload.get("operator_contract_lane") or payload.get("family_spec_patch_mode"))
        if warm_requested:
            warm_session_requested_count += 1
        if warm_reused:
            warm_session_reused_count += 1
        if not warm_reused:
            cold_subscription_call_count += 1
        if operator_contract_lane:
            contract_lane_call_count += 1
        if len(examples) < 8:
            examples.append({
                "work_id": str(row["work_id"]),
                "kind": kind,
                "family": str(row["family"] or payload.get("family") or ""),
                "station": str(row["station"] or payload.get("station") or usage.get("station") or ""),
                "status": str(row["status"]),
                "exit_kind": str(payload.get("exit_kind") or ""),
                "runtime": runtime,
                "agent_id": str(usage.get("agent_id") or payload.get("agent_id") or ""),
                "worker_id": str(usage.get("worker_id") or ""),
                "warm_session_requested": warm_requested,
                "warm_session_reused": bool(usage.get("warm_session_reused")),
                "operator_contract_lane": operator_contract_lane,
                "estimated_tokens": item_tokens,
                "wall_time_s": wall,
            })
    return {
        "schema": "leanmill-subscription-agent-usage-window-v2",
        "window_s": trailing_window_s,
        "tracked_kinds": sorted(SUBSCRIPTION_AGENT_KINDS),
        "open_count": open_count,
        "open_by_kind": dict(sorted(open_by_kind.items())),
        "open_by_worker": dict(sorted(open_by_worker.items())),
        "open_by_station": dict(sorted(open_by_station.items())),
        "open_examples": open_examples,
        "launched_count": launched_count,
        "estimated_prompt_tokens": total_prompt_tokens,
        "estimated_output_tokens": total_output_tokens,
        "estimated_total_tokens": total_tokens,
        "wall_time_s": total_wall_time_s,
        "warm_session_requested_count": warm_session_requested_count,
        "warm_session_reused_count": warm_session_reused_count,
        "cold_subscription_call_count": cold_subscription_call_count,
        "contract_lane_call_count": contract_lane_call_count,
        "by_runtime": {runtime: dict(counter) for runtime, counter in sorted(by_runtime.items())},
        "by_task_kind": {kind: dict(counter) for kind, counter in sorted(by_task_kind.items())},
        "recent_examples": examples,
        "missing_usage_terminal_count": missing_usage_terminal_count,
        "missing_usage_examples": missing_usage_examples,
        "missing_usage_floor_created_at_epoch": missing_usage_floor,
        "cost_usd": 0.0,
        "accounting_note": "Subscription-agent usage is estimated from persisted prompt/output characters for all warm-agent lanes, including source scouters. API dollar caps do not apply; missing usage rows are legacy or non-launch artifacts unless they recur after this telemetry contract.",
    }


def _runner_policy(factory_policy: dict[str, Any] | None, profile_name: str) -> dict[str, Any]:
    if not isinstance(factory_policy, dict) or not profile_name:
        return {}
    profile = (factory_policy.get("profiles") or {}).get(profile_name)
    if not isinstance(profile, dict):
        return {}
    runner = profile.get("runner")
    return runner if isinstance(runner, dict) else {}


def _profile_section(factory_policy: dict[str, Any] | None, profile_name: str, section: str) -> dict[str, Any]:
    if not isinstance(factory_policy, dict) or not profile_name:
        return {}
    profile = (factory_policy.get("profiles") or {}).get(profile_name)
    if not isinstance(profile, dict):
        return {}
    obj = profile.get(section)
    return obj if isinstance(obj, dict) else {}


def _execution_mode_for_lane(lane: dict[str, Any], *, source_binding_mode: str) -> str:
    role = str(lane.get("role") or "")
    if role in {"general_subscription_agent"}:
        return "subscription_agent_contract_or_general_generation"
    if role in {"source_subscription_agent"}:
        return "warm_subscription_agent_generation"
    if role == "upstream_source_request_review":
        return "api_llm_review"
    if role == "source_binding_task_integrator":
        if source_binding_mode == "agent":
            return "deterministic_scheduler_to_subscription_agent_binding"
        return "deterministic_source_binding_compiler"
    if role in {"source_retrieval_and_static_filter", "source_scout_release"}:
        return "deterministic_source_inventory"
    if bool(lane.get("heavy_lean")) or "probe" in role:
        return "deterministic_lean_verification"
    return "deterministic_orchestration"


def _execution_mode_for_work(kind: str, payload: dict[str, Any]) -> str:
    if kind in SUBSCRIPTION_AGENT_KINDS:
        if kind == "source_scout_task" and payload.get("source_search_integration_receipt"):
            return "subscription_agent_source_binding_generation"
        if kind == "source_scout_task":
            return "subscription_agent_source_scout_generation"
        if payload.get("family_spec_patch_mode"):
            return "subscription_agent_contract_patch_generation"
        return "subscription_agent_generation"
    if kind in {"llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"}:
        return "api_llm_generation_or_review"
    if kind == "source_search_task":
        return "deterministic_source_retrieval_and_static_filter"
    if kind in {"repair_canary_probe", "proof_probe"} or payload.get("probe_lane"):
        return "deterministic_lean_verification"
    return "deterministic_orchestration"


def _execution_mode_read_model(
    rows: list[sqlite3.Row],
    payload: dict[str, Any],
    *,
    factory_policy: dict[str, Any],
    factory_policy_path: str,
    policy_profile: str,
    trailing_window_s: int,
) -> dict[str, Any]:
    operations = _dict_field(factory_policy, "operations")
    mode_policy = _dict_field(operations, "agentic_execution_mode_policy")
    budget_policy = _dict_field(operations, "agentic_execution_budget_policy")
    budget_minimums = _dict_field(budget_policy, "minimums")
    runner = _runner_policy(factory_policy, policy_profile)
    source_integrator = _profile_section(factory_policy, policy_profile, "source_search_integrator")
    c_supply_controller = _profile_section(factory_policy, policy_profile, "c_supply_growth_controller")
    source_binding_mode = str(source_integrator.get("binding_mode") or "deterministic")
    agent_default_model = str(runner.get("agent_default_codex_model") or "gpt-5.4-mini")
    agent_family_spec_model = str(runner.get("agent_family_spec_patch_codex_model") or "gpt-5.5")
    source_agent_model = str(runner.get("source_agent_codex_model") or agent_default_model)
    llm_model_family = str(runner.get("llm_model_family") or "gpt4.1-mini")
    llm_codex_fallback_model = str(runner.get("llm_codex_cli_fallback_model") or "gpt-5.4-mini")
    upstream_rater_model = str(c_supply_controller.get("upstream_rater_model") or "gpt-5.4-mini")

    def min_int(key: str, fallback: int) -> int:
        try:
            return int(budget_minimums.get(key) if budget_minimums.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    def configured_int(obj: dict[str, Any], key: str, fallback: int = 0) -> int:
        try:
            return int(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    budget_gap_classes: list[str] = []
    budget_checks: list[dict[str, Any]] = []

    def add_budget_check(scope: str, metric: str, configured: int, required: int, *, enabled: bool = True) -> None:
        if not enabled:
            return
        ok = configured >= required
        gap_class = f"{scope}_{metric}_below_policy_floor"
        budget_checks.append({
            "scope": scope,
            "metric": metric,
            "configured": configured,
            "required_minimum": required,
            "ok": ok,
            "gap_class": "" if ok else gap_class,
        })
        if not ok:
            budget_gap_classes.append(gap_class)

    api_llm_enabled = bool(runner.get("allow_paid_llm") or runner.get("allow_llm_codex_cli_fallback"))
    source_agent_enabled = configured_int(runner, "source_agent_workers") > 0 or bool(runner.get("seed_external_source_scouts"))
    source_binding_enabled = source_binding_mode == "agent"
    family_birth_enabled = bool(c_supply_controller.get("family_birth_enabled") or runner.get("family_birth_enabled"))
    controller_agent_enabled = (
        configured_int(c_supply_controller, "agent_worker_processes") > 0
        or configured_int(c_supply_controller, "agent_worker_max_tasks") > 0
        or str(c_supply_controller.get("agent_runtime") or "") in {"codex", "balanced"}
    )
    upstream_rater_enabled = bool(c_supply_controller.get("upstream_rater_run_model")) and str(c_supply_controller.get("upstream_rater_mode") or "off") != "off"
    add_budget_check(
        "api_llm",
        "max_output_tokens",
        configured_int(runner, "llm_max_output_tokens"),
        min_int("api_llm_complex_output_tokens", 2400),
        enabled=api_llm_enabled,
    )
    add_budget_check(
        "api_llm",
        "timeout_s",
        configured_int(runner, "llm_timeout_s"),
        min_int("api_llm_complex_timeout_s", 300),
        enabled=api_llm_enabled,
    )
    add_budget_check(
        "source_subscription_agent",
        "wall_time_s",
        configured_int(runner, "source_agent_max_wall_time_s"),
        min_int("source_subscription_agent_wall_time_s", 1800),
        enabled=source_agent_enabled,
    )
    add_budget_check(
        "source_subscription_agent",
        "iterations",
        configured_int(runner, "source_agent_max_iterations"),
        min_int("source_subscription_agent_iterations", 3),
        enabled=source_agent_enabled,
    )
    add_budget_check(
        "source_binding_agent",
        "wall_time_s",
        configured_int(source_integrator, "agent_max_wall_time_s"),
        min_int("source_binding_agent_wall_time_s", 1800),
        enabled=source_binding_enabled,
    )
    add_budget_check(
        "source_binding_agent",
        "iterations",
        configured_int(source_integrator, "agent_max_iterations"),
        min_int("source_binding_agent_iterations", 3),
        enabled=source_binding_enabled,
    )
    add_budget_check(
        "family_birth_agent",
        "wall_time_s",
        configured_int(c_supply_controller, "family_birth_agent_max_wall_time_s"),
        min_int("family_birth_agent_wall_time_s", 1800),
        enabled=family_birth_enabled,
    )
    add_budget_check(
        "family_birth_agent",
        "iterations",
        configured_int(c_supply_controller, "family_birth_agent_max_iterations"),
        min_int("family_birth_agent_iterations", 3),
        enabled=family_birth_enabled,
    )
    add_budget_check(
        "c_supply_agent_worker",
        "timeout_s",
        configured_int(c_supply_controller, "agent_worker_timeout_s"),
        min_int("c_supply_agent_worker_timeout_s", 1800),
        enabled=controller_agent_enabled,
    )
    add_budget_check(
        "upstream_rater",
        "timeout_s",
        configured_int(c_supply_controller, "upstream_rater_timeout_s"),
        min_int("upstream_rater_timeout_s", 600),
        enabled=upstream_rater_enabled,
    )
    try:
        lane_plan = lane_budget_plan(path=factory_policy_path, profile_name=policy_profile)
    except Exception as exc:  # defensive read model; never block factory intelligence
        lane_plan = {"schema": "leanmill-lane-budget-plan-v1", "error": str(exc), "lanes": []}

    intended_lanes: list[dict[str, Any]] = []
    mode_worker_counts: Counter[str] = Counter()
    for lane in lane_plan.get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        mode = _execution_mode_for_lane(lane, source_binding_mode=source_binding_mode)
        worker_count = int(lane.get("worker_count") or 0)
        role = str(lane.get("role") or "")
        model_contract: dict[str, Any] = {}
        if role == "general_subscription_agent":
            model_contract = {
                "runtime": "codex",
                "default_model": agent_default_model,
                "family_spec_patch_model": agent_family_spec_model,
            }
        elif role == "source_subscription_agent":
            model_contract = {"runtime": "codex", "default_model": source_agent_model}
        elif role == "upstream_source_request_review":
            model_contract = {
                "api_model_family": llm_model_family,
                "subscription_cli_fallback_model": llm_codex_fallback_model,
                "allow_paid_llm": bool(runner.get("allow_paid_llm")),
            }
        elif role == "source_binding_task_integrator" and source_binding_mode == "agent":
            model_contract = {"runtime": str(source_integrator.get("agent_runtime") or "codex"), "claimed_by_source_subscription_agent_model": source_agent_model}
        mode_worker_counts[mode] += worker_count
        intended_lanes.append({
            "lane": lane.get("lane"),
            "role": role,
            "execution_mode": mode,
            "worker_count": worker_count,
            "model_contract": model_contract,
            "claim_kinds": lane.get("claim_kinds") or [],
            "payload_filter": lane.get("payload_filter") or {},
            "heavy_lean": bool(lane.get("heavy_lean")),
            "proof_credit_authority": lane.get("proof_credit_authority"),
        })
    if bool(runner.get("allow_paid_llm")):
        mode_worker_counts["api_llm_generation_or_review"] += 1
        intended_lanes.append({
            "lane": "api_llm_proposal",
            "role": "api_llm_proposal",
            "execution_mode": "api_llm_generation_or_review",
            "worker_count": 1,
            "model_contract": {
                "api_model_family": llm_model_family,
                "subscription_cli_fallback_model": llm_codex_fallback_model,
                "allow_paid_llm": bool(runner.get("allow_paid_llm")),
            },
            "claim_kinds": ["llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"],
            "proof_credit_authority": "governance_gate",
        })
    if bool(c_supply_controller.get("upstream_rater_run_model")) and str(c_supply_controller.get("upstream_rater_mode") or "off") != "off":
        intended_lanes.append({
            "lane": "c_supply_upstream_rater",
            "role": "api_llm_routing_forecast",
            "execution_mode": "api_llm_calibration",
            "worker_count": 1,
            "model_contract": {
                "subscription_cli": "codex",
                "model": upstream_rater_model,
                "mode": str(c_supply_controller.get("upstream_rater_mode") or ""),
                "reasoning_effort": str(c_supply_controller.get("upstream_rater_reasoning_effort") or ""),
            },
            "claim_kinds": [],
            "proof_credit_authority": "governance_gate",
        })
        mode_worker_counts["api_llm_calibration"] += 1

    now = _now()
    open_by_mode: Counter[str] = Counter()
    terminal_recent_by_mode: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for row in rows:
        payload_row = _payload(row)
        mode = _execution_mode_for_work(str(row["kind"]), payload_row)
        status = str(row["status"])
        if status in OPEN_STATUSES:
            open_by_mode[mode] += 1
        if int(row["updated_at"]) >= now - trailing_window_s and status in TERMINAL_STATUSES:
            terminal_recent_by_mode[mode] += 1
        if len(examples) < 12 and (status in OPEN_STATUSES or int(row["updated_at"]) >= now - trailing_window_s):
            usage_row = _dict_field(payload_row, "usage_estimate")
            examples.append({
                "work_id": str(row["work_id"]),
                "kind": str(row["kind"]),
                "status": status,
                "family": str(row["family"] or payload_row.get("family") or ""),
                "execution_mode": mode,
                "expected_exit": str(row["expected_exit"] or payload_row.get("expected_exit") or ""),
                "runtime": str(payload_row.get("runtime") or ""),
                "model": str(usage_row.get("model") or payload_row.get("model") or payload_row.get("model_id") or ""),
                "claimed_by": str(row["claimed_by"] or ""),
            })

    version_health = _dict_field(payload, "worker_version_health")
    active_heartbeats = [h for h in version_health.get("active_heartbeats") or [] if isinstance(h, dict)]
    active_by_mode: Counter[str] = Counter()
    heartbeat_examples: list[dict[str, Any]] = []
    for hb in active_heartbeats:
        worker_id = str(hb.get("worker_id") or "")
        kind = str(hb.get("worker_kind") or "")
        hb_payload = _dict_field(hb, "payload")
        if "source-codex" in worker_id or kind.startswith("agent_repair_runtime"):
            mode = "subscription_agent_worker"
        elif "llm" in worker_id or "proposal" in kind:
            mode = "api_llm_worker"
        elif "probe" in worker_id or "probe" in kind:
            mode = "deterministic_lean_worker"
        elif "source-search" in worker_id or "source-integrator" in worker_id or "24x7" in worker_id or "watchdog" in worker_id:
            mode = "deterministic_control_or_source_worker"
        else:
            mode = "unclassified_worker"
        active_by_mode[mode] += 1
        if len(heartbeat_examples) < 12:
            heartbeat_examples.append({
                "worker_id": worker_id,
                "worker_kind": kind,
                "mode": mode,
                "claimed_work_id": hb.get("claimed_work_id"),
                "heartbeat_age_s": hb.get("heartbeat_age_s"),
                "runtime": hb_payload.get("runtime"),
                "model": hb_payload.get("model") or hb_payload.get("default_model") or hb_payload.get("model_id"),
                "claim_kinds": hb_payload.get("claim_kinds"),
                "claim_patch_modes": hb_payload.get("claim_patch_modes"),
            })

    usage = _dict_field(payload, "subscription_agent_usage")
    launched = int(usage.get("launched_count") or 0)
    warm_reused = int(usage.get("warm_session_reused_count") or 0)
    cold_calls = int(usage.get("cold_subscription_call_count") or 0)
    contract_calls = int(usage.get("contract_lane_call_count") or 0)
    warm_reuse_rate = round(warm_reused / launched, 6) if launched else None
    gap_classes: list[str] = []
    source_workers_declared = int(runner.get("source_agent_workers") or 0)
    if source_workers_declared > 0 and active_by_mode.get("subscription_agent_worker", 0) == 0:
        gap_classes.append("declared_subscription_agent_workers_not_heartbeat_visible")
    if source_binding_mode == "agent" and open_by_mode.get("subscription_agent_source_binding_generation", 0) == 0:
        gap_classes.append("agentic_source_binding_enabled_but_no_open_binding_work")
    if launched and warm_reused == 0 and int(usage.get("warm_session_requested_count") or 0) > 0:
        gap_classes.append("warm_session_requested_but_not_reused_in_window")
    gap_classes.extend(budget_gap_classes)

    return {
        "schema": "leanmill-execution-mode-read-model-v1",
        "policy_profile": policy_profile,
        "policy": mode_policy,
        "budget_policy": budget_policy,
        "source_binding_mode": source_binding_mode,
        "declared_models": {
            "general_subscription_agent": {
                "runtime": "codex",
                "default_model": agent_default_model,
                "family_spec_patch_model": agent_family_spec_model,
            },
            "source_subscription_agent": {"runtime": "codex", "default_model": source_agent_model},
            "api_llm_proposal": {
                "model_family": llm_model_family,
                "codex_cli_fallback_model": llm_codex_fallback_model,
                "allow_paid_llm": bool(runner.get("allow_paid_llm")),
            },
            "c_supply_upstream_rater": {
                "runtime": "codex_subscription_cli",
                "model": upstream_rater_model,
                "mode": str(c_supply_controller.get("upstream_rater_mode") or ""),
                "run_model": bool(c_supply_controller.get("upstream_rater_run_model")),
            },
            "source_search_integrator": {
                "binding_mode": source_binding_mode,
                "agent_runtime": str(source_integrator.get("agent_runtime") or "codex"),
                "effective_agent_model": source_agent_model,
            },
        },
        "intended_lanes": intended_lanes,
        "declared_budgets": {
            "policy_minimums": dict(budget_minimums),
            "checks": budget_checks,
            "budget_gap_classes": budget_gap_classes,
            "budget_gap_action": budget_policy.get("rule") if isinstance(budget_policy, dict) else "",
            "credit_boundary": budget_policy.get("credit_boundary") if isinstance(budget_policy, dict) else "",
        },
        "intended_worker_counts_by_mode": dict(sorted(mode_worker_counts.items())),
        "observed_open_work_by_mode": dict(sorted(open_by_mode.items())),
        "observed_recent_terminal_work_by_mode": dict(sorted(terminal_recent_by_mode.items())),
        "observed_active_workers_by_mode": dict(sorted(active_by_mode.items())),
        "subscription_agent_usage": {
            "launched_count": launched,
            "open_count": int(usage.get("open_count") or 0),
            "warm_session_requested_count": int(usage.get("warm_session_requested_count") or 0),
            "warm_session_reused_count": warm_reused,
            "warm_reuse_rate": warm_reuse_rate,
            "cold_subscription_call_count": cold_calls,
            "contract_lane_call_count": contract_calls,
            "interpretation": (
                "contract lanes intentionally run without warm resume to keep scoped patch state isolated"
                if contract_calls else
                "source/general subscription-agent lanes may reuse warm sessions when runtime supports resume"
            ),
        },
        "recent_work_examples": examples,
        "active_worker_examples": heartbeat_examples,
        "budget_gap_classes": budget_gap_classes,
        "gap_classes": gap_classes,
        "credit_boundary": "Execution mode explains generation/verification architecture only. It does not create proof credit, benchmark lift, governance pass, or C credit-ready status.",
    }


def _learning_feedback_read_model(rows: list[sqlite3.Row], *, trailing_window_s: int) -> dict[str, Any]:
    """Observer read model over probe feedback, patterned after action-impact."""
    now = _now()
    exit_counts: Counter[str] = Counter()
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    recent_feedback: list[dict[str, Any]] = []
    review_required: list[dict[str, Any]] = []
    for row in rows:
        if int(row["updated_at"]) < now - trailing_window_s:
            continue
        if str(row["status"]) not in TERMINAL_STATUSES:
            continue
        payload = _payload(row)
        kind = str(row["kind"])
        lane = str(payload.get("probe_lane") or payload.get("lane") or "")
        if kind not in {"repair_canary_probe", "proof_probe"} and not lane:
            continue
        counts = _scoreboard_counts_from_payload(payload)
        merged = dict(payload)
        merged.update(counts)
        exit_kind = learning_feedback.learning_exit_from_counts(merged)
        if exit_kind == "unknown":
            continue
        family = str(row["family"] or payload.get("family") or "")
        row_id = str(payload.get("row_id") or payload.get("target_row_id") or "")
        shard = payload.get("family_spec_shard") or {}
        if not row_id and isinstance(shard, dict):
            row_id = str(shard.get("row_id") or "")
        if not row_id:
            for outcome in payload.get("row_outcomes") or []:
                if isinstance(outcome, dict) and outcome.get("row_id"):
                    row_id = str(outcome.get("row_id") or "")
                    break
        exit_counts[exit_kind] += 1
        by_family[family or "unknown"][exit_kind] += 1
        if exit_kind in learning_feedback.NONUSEFUL_PROBE_EXITS or learning_feedback.int_count(counts, "negative_control_invalid_fail_count") > 0:
            entry = learning_feedback.feedback_entry(
                source_probe_work_id=str(row["work_id"]),
                row_id=row_id,
                exit_kind=exit_kind,
                negative_control_invalid_fail_count=learning_feedback.int_count(counts, "negative_control_invalid_fail_count"),
                negative_control_fail_count=learning_feedback.int_count(counts, "negative_control_fail_count"),
                negative_control_unexpected_pass_count=learning_feedback.int_count(counts, "negative_control_unexpected_pass_count"),
                scoreboard=str(payload.get("scoreboard") or ""),
                feedback_action="route to typed repair/backfill/triage; do not count as proof value",
                failure_evidence=_probe_failure_evidence_from_payload(payload, row_id=row_id),
            )
            if len(recent_feedback) < 20:
                recent_feedback.append({**entry, "family": family, "lane": lane, "updated_at_epoch": int(row["updated_at"])})
            if exit_kind in {"failed_negative_control", "invalid_negative_control"} and len(review_required) < 20:
                review_required.append({**entry, "family": family, "lane": lane, "updated_at_epoch": int(row["updated_at"])})
    return {
        "schema": "leanmill-learning-feedback-read-model-v1",
        "source_contract_schema": learning_feedback.SCHEMA,
        "window_s": trailing_window_s,
        "feedback_record_count": sum(exit_counts.values()),
        "exit_counts": dict(sorted(exit_counts.items())),
        "by_family": {family: dict(sorted(counts.items())) for family, counts in sorted(by_family.items())},
        "recent_feedback": recent_feedback,
        "review_required_count": len(review_required),
        "review_required": review_required,
        "contract_note": "Feedback records are causal routing inputs only; proof value remains scoreboard/governance-gated.",
    }


def _family_supply_lifecycle_read_model(rows: list[sqlite3.Row], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Project family birth/generalization supply flow from queue and events."""
    tracked_modes = {
        "family_birth_candidate",
        "generalize_family_spec",
        "family_spec_positive_repair",
        "c_supply_template_backfill",
        "repair_quarantine",
    }
    by_mode_status: dict[str, Counter[str]] = {mode: Counter() for mode in tracked_modes}
    family_counts: dict[str, Counter[str]] = {mode: Counter() for mode in tracked_modes}
    recent: list[dict[str, Any]] = []
    accepted_patch_count = 0
    for row in rows:
        payload = _payload(row)
        mode = str(payload.get("family_spec_patch_mode") or "")
        if mode not in tracked_modes:
            continue
        status = str(row["status"])
        family = str(payload.get("family") or payload.get("repair_family") or "unknown")
        by_mode_status[mode][status] += 1
        family_counts[mode][family] += 1
        if status == "done" and str(payload.get("expected_exit") or "") == "family_spec_patch":
            accepted_patch_count += 1
        if len(recent) < 20:
            recent.append({
                "work_id": str(row["work_id"]),
                "status": status,
                "mode": mode,
                "family": family,
                "expected_exit": str(payload.get("expected_exit") or ""),
                "updated_at_epoch": int(row["updated_at"]),
            })
    activation_events = [ev for ev in events if str(ev.get("event_type") or "") in {"family_birth_activated", "family_spec_positive_repair_activated"}]
    activation_status_counts: Counter[str] = Counter()
    activation_seeded_count = 0
    activation_recent: list[dict[str, Any]] = []
    for ev in activation_events:
        ev_payload = _dict_field(ev, "payload")
        status = str(ev_payload.get("status") or "unknown")
        activation_status_counts[status] += 1
        activation_seeded_count += learning_feedback.int_count(ev_payload, "enqueued")
        if len(activation_recent) < 10:
            activation_recent.append({
                "event_type": str(ev.get("event_type") or ""),
                "work_id": str(ev.get("work_id") or ev_payload.get("work_id") or ""),
                "family": str(ev_payload.get("family") or ""),
                "status": status,
                "enqueued": learning_feedback.int_count(ev_payload, "enqueued"),
                "timestamp": int(ev.get("timestamp") or 0),
            })
    birth_done = by_mode_status["family_birth_candidate"].get("done", 0)
    birth_activation_events = [ev for ev in activation_events if str(ev.get("event_type") or "") == "family_birth_activated"]
    possible_birth_activation_leakage = max(0, int(birth_done) - len(birth_activation_events))
    open_birth = by_mode_status["family_birth_candidate"].get("queued", 0) + by_mode_status["family_birth_candidate"].get("running", 0)
    open_generalize = by_mode_status["generalize_family_spec"].get("queued", 0) + by_mode_status["generalize_family_spec"].get("running", 0)
    return {
        "schema": "leanmill-family-supply-lifecycle-read-model-v1",
        "tracked_modes": sorted(tracked_modes),
        "by_mode_status": {mode: dict(sorted(counts.items())) for mode, counts in sorted(by_mode_status.items())},
        "family_counts_by_mode": {mode: dict(counts.most_common(12)) for mode, counts in sorted(family_counts.items())},
        "open_family_birth_count": int(open_birth),
        "open_family_generalize_count": int(open_generalize),
        "accepted_patch_count": int(accepted_patch_count),
        "activation_event_count": len(activation_events),
        "activation_seeded_count": int(activation_seeded_count),
        "activation_status_counts": dict(sorted(activation_status_counts.items())),
        "possible_birth_activation_leakage_count": int(possible_birth_activation_leakage),
        "recent_family_supply_work": recent,
        "recent_activation_events": activation_recent,
        "credit_boundary": "family supply work creates probe supply only; governed family-spec probes decide credit-ready rows",
    }


def _agentic_handoff_contract_read_model(
    rows: list[sqlite3.Row],
    *,
    factory_policy: dict[str, Any],
    trailing_window_s: int,
) -> dict[str, Any]:
    """Central handoff check for agentic-generation outputs.

    This is an observability/read-model contract. It does not enqueue work and
    does not grant credit; it makes missing downstream receipts impossible to
    hide behind terminal agent rows.
    """
    policy = handoff_contract.policy_from_factory_policy(factory_policy)
    skip_keys = policy["terminal_existing_skip_keys"]
    now = _now()
    family_patch_counts: Counter[str] = Counter()
    handoff_status_counts: Counter[str] = Counter()
    source_search_counts: Counter[str] = Counter()
    hard_leaks: list[dict[str, Any]] = []
    blocked_receipts: list[dict[str, Any]] = []
    verified_handoffs: list[dict[str, Any]] = []
    pending_handoffs: list[dict[str, Any]] = []

    for row in rows:
        if str(row["status"]) not in TERMINAL_STATUSES:
            continue
        payload = _payload(row)
        kind = str(row["kind"])
        family = str(row["family"] or payload.get("family") or payload.get("repair_family") or "")
        work_id = str(row["work_id"])
        updated = int(row["updated_at"])
        recent = updated >= now - trailing_window_s
        if kind in SUBSCRIPTION_AGENT_KINDS and str(payload.get("expected_exit") or "") == "family_spec_patch":
            mode = str(payload.get("family_spec_patch_mode") or "")
            patch_receipt = _dict_field(payload, "family_spec_patch_receipt")
            patch_passed = str(patch_receipt.get("status") or "") == "pass" and str(row["status"]) == "done"
            if not patch_passed:
                continue
            family_patch_counts[mode or "unknown"] += 1
            receipt_field = handoff_contract.receipt_field_for_mode(mode, policy)
            if not receipt_field:
                handoff_status_counts["not_required_by_policy"] += 1
                continue
            receipt = payload.get(receipt_field) if isinstance(payload.get(receipt_field), dict) else {}
            base = {
                "work_id": work_id,
                "family": family,
                "mode": mode,
                "receipt_field": receipt_field,
                "updated_at_epoch": updated,
                "recent": recent,
            }
            receipt_class = handoff_contract.classify_family_spec_receipt(receipt, skip_keys=skip_keys)
            class_name = str(receipt_class.get("class") or "unknown")
            handoff_status_counts[class_name] += 1
            if receipt_class.get("hard_leak") and not receipt:
                if len(hard_leaks) < 20:
                    hard_leaks.append({**base, "reason": "accepted_agentic_patch_missing_downstream_handoff_receipt"})
            elif receipt_class.get("verified"):
                if len(verified_handoffs) < 20:
                    verified_handoffs.append({
                        **base,
                        "status": receipt_class.get("status"),
                        "enqueued": receipt_class.get("enqueued"),
                        "job_count": receipt_class.get("job_count"),
                    })
            elif receipt_class.get("blocked"):
                if len(blocked_receipts) < 20:
                    blocked_receipts.append({
                        **base,
                        "status": receipt_class.get("status"),
                        "reason": str(receipt_class.get("reason") or ""),
                        "enqueued": receipt_class.get("enqueued"),
                        "job_count": receipt_class.get("job_count"),
                        "selected_row_count": receipt_class.get("selected_row_count"),
                    })
            else:
                if len(hard_leaks) < 20:
                    hard_leaks.append({
                        **base,
                        "reason": "activation_receipt_has_no_enqueued_or_existing_terminal_work_and_no_blocker",
                        "status": receipt_class.get("status"),
                        "enqueued": receipt_class.get("enqueued"),
                        "job_count": receipt_class.get("job_count"),
                        "selected_row_count": receipt_class.get("selected_row_count"),
                    })
        if kind == "source_search_task" and str(row["status"]) == "done":
            ready_total = handoff_contract.source_search_ready_total(payload, policy["source_search_ready_summary_keys"])
            if ready_total <= 0:
                continue
            integrated = bool(payload.get("source_search_integrated_at_epoch") or payload.get("source_search_integration_receipt"))
            held = str(payload.get("exit_kind") or "") == "source_search_integrated_hold"
            if integrated:
                source_search_counts["integrated"] += 1
            elif held:
                source_search_counts["visible_hold"] += 1
                if len(blocked_receipts) < 20:
                    blocked_receipts.append({
                        "work_id": work_id,
                        "family": family,
                        "mode": "source_search_to_binding",
                        "receipt_field": "exit_kind/source_search_integrated_hold",
                        "status": "hold",
                        "ready_total": ready_total,
                        "updated_at_epoch": updated,
                        "recent": recent,
                    })
            else:
                source_search_counts["pending_integration"] += 1
                if len(pending_handoffs) < 20:
                    pending_handoffs.append({
                        "work_id": work_id,
                        "family": family,
                        "mode": "source_search_to_binding",
                        "reason": "source_search_ready_candidates_waiting_for_integration",
                        "ready_total": ready_total,
                        "updated_at_epoch": updated,
                        "recent": recent,
                    })

    hard_leak_count = sum(v for k, v in handoff_status_counts.items() if k in {"missing_receipt", "zero_handoff_without_blocker"})
    status = "leakage_detected" if hard_leak_count else ("pending_handoff" if pending_handoffs else "pass")
    return {
        "schema": "leanmill-agentic-handoff-contract-read-model-v1",
        "status": status,
        "policy": policy,
        "family_spec_patch_counts_by_mode": dict(sorted(family_patch_counts.items())),
        "handoff_status_counts": dict(sorted(handoff_status_counts.items())),
        "source_search_status_counts": dict(sorted(source_search_counts.items())),
        "hard_leak_count": int(hard_leak_count),
        "blocked_receipt_count": len(blocked_receipts),
        "pending_handoff_count": len(pending_handoffs),
        "verified_handoff_count": len(verified_handoffs),
        "hard_leaks": hard_leaks,
        "blocked_receipts": blocked_receipts,
        "pending_handoffs": pending_handoffs,
        "verified_handoffs": verified_handoffs,
        "next_action": (
            "repair the named lane so terminal agentic outputs write downstream activation/integration receipts"
            if hard_leak_count else
            "drain the integration/probe workers for pending handoffs"
            if pending_handoffs else
            "keep generation lanes active; handoff receipts are visible"
        ),
        "credit_boundary": policy["credit_boundary"],
    }


def _live_queue_c_supply_credit_summary(rows: list[sqlite3.Row]) -> dict[str, Any]:
    credit_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        if str(row["status"]) not in TERMINAL_STATUSES:
            continue
        if str(row["kind"]) != "repair_canary_probe":
            continue
        payload = _payload(row)
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        family = str(row["family"] or payload.get("family") or payload.get("repair_family") or "")
        scoreboard_path = str(payload.get("scoreboard") or "")
        row_outcomes = payload.get("row_outcomes") or []
        if isinstance(row_outcomes, dict):
            row_outcomes = list(row_outcomes.values())
        if not isinstance(row_outcomes, list):
            row_outcomes = []
        neg_fail_count = learning_feedback.int_count(payload, "negative_control_fail_count")
        neg_unexpected_count = learning_feedback.int_count(payload, "negative_control_unexpected_pass_count")
        neg_invalid_count = learning_feedback.int_count(payload, "negative_control_invalid_fail_count")
        if not row_outcomes:
            shard = payload.get("family_spec_shard") or {}
            rid = str(shard.get("row_id") or "") if isinstance(shard, dict) else ""
            row_outcomes = [{
                "row_id": rid,
                "learning_unit_exit": payload.get("learning_unit_exit") or payload.get("exit_kind"),
                "ratified_closure_count": payload.get("ratified_closure_count"),
                "exact_gap_candidate_count": payload.get("exact_gap_candidate_count"),
                "valid_falsifier_count": payload.get("valid_falsifier_count"),
            }]
        for outcome in row_outcomes:
            if not isinstance(outcome, dict):
                continue
            rid = str(outcome.get("row_id") or "")
            if not rid:
                continue
            exit_kind = str(outcome.get("learning_unit_exit") or payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
            proof_value = (
                exit_kind in learning_feedback.PROOF_VALUE_EXIT_KINDS
                or learning_feedback.int_count(outcome, "ratified_closure_count") > 0
                or learning_feedback.int_count(outcome, "exact_gap_candidate_count") > 0
                or learning_feedback.int_count(outcome, "valid_falsifier_count") > 0
            )
            receipt_ok = proof_value and neg_fail_count > 0 and neg_unexpected_count == 0 and neg_invalid_count == 0
            if not receipt_ok:
                continue
            current = credit_rows.setdefault(rid, {
                "row_id": rid,
                "probe_credit_ready": True,
                "probe_verified_families": [],
                "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                "queue_evidence": [],
            })
            families = set(str(f) for f in current.get("probe_verified_families") or [] if str(f))
            if family:
                families.add(family)
            current["probe_verified_families"] = sorted(families)
            current["queue_evidence"].append({
                "work_id": str(row["work_id"]),
                "family": family,
                "exit_kind": exit_kind,
                "scoreboard": scoreboard_path,
                "receipt_ok": True,
                "ratified_closure_count": learning_feedback.int_count(outcome, "ratified_closure_count"),
                "exact_gap_candidate_count": learning_feedback.int_count(outcome, "exact_gap_candidate_count"),
                "valid_falsifier_count": learning_feedback.int_count(outcome, "valid_falsifier_count"),
                "negative_control_fail_count": neg_fail_count,
                "negative_control_unexpected_pass_count": neg_unexpected_count,
                "negative_control_invalid_fail_count": neg_invalid_count,
                "updated_at_epoch": int(row["updated_at"]),
            })
    family_counts: Counter[str] = Counter()
    for item in credit_rows.values():
        family_counts.update(str(f) for f in item.get("probe_verified_families") or [] if str(f))
    return {
        "schema": "leanmill-c-supply-live-queue-credit-summary-v1",
        "source_path": "leanmill_work_queue",
        "status": "ready" if credit_rows else "no_live_queue_credit",
        "credit_ready_count": len(credit_rows),
        "credit_ready_rows": list(credit_rows.values()),
        "credit_ready_family_counts": dict(sorted(family_counts.items())),
        "probe_verified_count": len(credit_rows),
        "selected_count": len(credit_rows),
        "eligible_count": len(credit_rows),
        "blockers_by_reason": {},
    }


def _filter_live_queue_c_supply_credit_summary(summary: dict[str, Any], static_strict_row_ids: set[str]) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    rows = [row for row in (summary.get("credit_ready_rows") or []) if isinstance(row, dict)]
    kept = [row for row in rows if str(row.get("row_id") or "") in static_strict_row_ids]
    blocked_count = max(0, len(rows) - len(kept))
    family_counts: Counter[str] = Counter()
    for row in kept:
        family_counts.update(str(f) for f in (row.get("probe_verified_families") or row.get("families") or []) if str(f))
    out = dict(summary)
    out["status"] = "ready" if kept else "no_static_strict_live_queue_credit"
    out["credit_ready_count"] = len(kept)
    out["credit_ready_rows"] = kept
    out["credit_ready_family_counts"] = dict(sorted(family_counts.items()))
    out["probe_verified_count"] = len(kept)
    out["selected_count"] = len(kept)
    out["eligible_count"] = len(kept)
    blockers = dict(out.get("blockers_by_reason") or {})
    if blocked_count:
        blockers["live_queue_without_static_strict_no_signal"] = blocked_count
    out["blockers_by_reason"] = blockers
    out["static_strict_filter"] = {
        "required": True,
        "eligible_static_row_count": len(static_strict_row_ids),
        "blocked_live_queue_row_count": blocked_count,
        "contract": "family-spec probe receipts count for C-supply only when the row also has strict static no-signal evidence",
    }
    return out



def _target_resolution_read_model(rows: list[sqlite3.Row]) -> dict[str, Any]:
    """Expose probe-target hydration failures before they become false no-signal outcomes."""
    total = 0
    open_missing_target_meta = 0
    terminal_pre_patch_conflicts = 0
    unresolved_reason_counts: Counter[str] = Counter()
    open_unresolved_reason_counts: Counter[str] = Counter()
    terminal_unresolved_reason_counts: Counter[str] = Counter()
    unresolved_samples: list[dict[str, Any]] = []
    open_unresolved_samples: list[dict[str, Any]] = []
    missing_meta_samples: list[dict[str, Any]] = []
    selected_target_count = 0
    for row in rows:
        payload = _payload(row)
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        total += 1
        status = str(row["status"])
        work_id = str(row["work_id"])
        family = str(payload.get("family") or "")
        meta = _dict_field(payload, "probe_corpus_meta")
        selected_targets = _dict_field(meta, "selected_row_targets")
        selected_target_count += len(selected_targets)
        unresolved = meta.get("unresolved_row_reasons") if isinstance(meta.get("unresolved_row_reasons"), list) else []
        for rec in unresolved:
            if not isinstance(rec, dict):
                continue
            reason = str(rec.get("reason") or "unknown")
            unresolved_reason_counts[reason] += 1
            if len(unresolved_samples) < 20:
                unresolved_samples.append({
                    "work_id": work_id,
                    "status": status,
                    "family": family,
                    "row_id": rec.get("row_id"),
                    "reason": reason,
                })
            if status in OPEN_STATUSES:
                open_unresolved_reason_counts[reason] += 1
                if len(open_unresolved_samples) < 20:
                    open_unresolved_samples.append({
                        "work_id": work_id,
                        "status": status,
                        "family": family,
                        "row_id": rec.get("row_id"),
                        "reason": reason,
                    })
            else:
                terminal_unresolved_reason_counts[reason] += 1
        if status in OPEN_STATUSES and not selected_targets:
            open_missing_target_meta += 1
            if len(missing_meta_samples) < 20:
                missing_meta_samples.append({
                    "work_id": work_id,
                    "status": status,
                    "family": family,
                    "selected_row_count": meta.get("selected_row_count"),
                    "selected_row_ids": (meta.get("selected_row_ids") or [])[:8] if isinstance(meta.get("selected_row_ids"), list) else [],
                })
        if str(payload.get("learning_unit_exit") or "") == "target_resolution_conflict_pre_patch":
            terminal_pre_patch_conflicts += 1
        for outcome in payload.get("row_outcomes") or []:
            if isinstance(outcome, dict) and str(outcome.get("learning_unit_exit") or "") == "target_resolution_conflict_pre_patch":
                terminal_pre_patch_conflicts += 1
    risk_classes: list[str] = []
    if open_missing_target_meta:
        risk_classes.append("open_family_spec_probe_missing_target_metadata")
    if open_unresolved_reason_counts:
        risk_classes.append("target_resolution_unresolved_rows_present")
    return {
        "schema": "leanmill-target-resolution-read-model-v1",
        "family_spec_probe_item_count": total,
        "selected_target_metadata_count": selected_target_count,
        "open_missing_target_metadata_count": open_missing_target_meta,
        "terminal_pre_patch_conflict_count": terminal_pre_patch_conflicts,
        "open_unresolved_reason_counts": dict(sorted(open_unresolved_reason_counts.items())),
        "terminal_unresolved_reason_counts": dict(sorted(terminal_unresolved_reason_counts.items())),
        "unresolved_reason_counts": dict(sorted(unresolved_reason_counts.items())),
        "open_unresolved_samples": open_unresolved_samples,
        "unresolved_samples": unresolved_samples,
        "missing_target_metadata_samples": missing_meta_samples,
        "risk_classes": risk_classes,
        "contract_note": "Family-spec probes must bind a concrete theorem target; multi-theorem files without target resolution are supply debt, not no-signal evidence.",
    }


def _c_supply_credit_ready_read_model(
    *,
    c_supply_batch: dict[str, Any],
    c_supply_clean_selection: dict[str, Any],
    c_supply_growth: dict[str, Any],
    factory_policy: dict[str, Any] | None = None,
    live_queue_credit_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Current C-supply learning-unit read model: deduped credit-ready rows."""
    sources: list[tuple[str, dict[str, Any]]] = []
    if isinstance(c_supply_growth, dict):
        seen_growth_selection_keys: set[str] = set()

        def _append_growth_selection(source_name: str, value: Any) -> None:
            if isinstance(value, dict) and value:
                key = f"dict:{source_name}:{id(value)}"
                if key not in seen_growth_selection_keys:
                    sources.append((source_name, _c_supply_selection_summary(value)))
                    seen_growth_selection_keys.add(key)
                return
            path = str(value or "")
            if not path or path in seen_growth_selection_keys:
                return
            obj = _read_json(path) or {}
            if isinstance(obj, dict) and obj:
                sources.append((source_name, _c_supply_selection_summary(obj, source_path=path)))
                seen_growth_selection_keys.add(path)

        if str(c_supply_growth.get("status") or "") == "running":
            _append_growth_selection("growth_controller_running_latest_selection_path", c_supply_growth.get("latest_selection"))
            _append_growth_selection("growth_controller_running_best_selection_path", c_supply_growth.get("best_selection"))
        else:
            _append_growth_selection("growth_controller_final_selection", c_supply_growth.get("final_selection"))
            _append_growth_selection("growth_controller_latest_selection_path", c_supply_growth.get("latest_selection"))
            _append_growth_selection("growth_controller_best_selection_path", c_supply_growth.get("best_selection"))
    if isinstance(c_supply_clean_selection, dict) and c_supply_clean_selection:
        if str(c_supply_clean_selection.get("schema") or "") == "leanmill-c-supply-selection-summary-v1":
            sources.append(("clean_selection", c_supply_clean_selection))
        else:
            sources.append(("clean_selection", _c_supply_selection_summary(c_supply_clean_selection)))
    batch_selection = c_supply_batch.get("selection") if isinstance(c_supply_batch, dict) else {}
    if isinstance(batch_selection, dict) and batch_selection:
        sources.append(("batch_selection", _c_supply_selection_summary(batch_selection)))
    if isinstance(live_queue_credit_summary, dict) and live_queue_credit_summary:
        static_strict_row_ids: set[str] = set()
        for _name, summary in sources:
            static_strict_row_ids.update(str(row_id) for row_id in (summary.get("static_strict_no_signal_row_ids") or []) if str(row_id))
        sources.append(("live_queue", _filter_live_queue_c_supply_credit_summary(live_queue_credit_summary, static_strict_row_ids)))

    target = 20
    if isinstance(c_supply_growth, dict) and c_supply_growth.get("target_credit_ready_rows") is not None:
        try:
            target = int(c_supply_growth.get("target_credit_ready_rows") or target)
        except (TypeError, ValueError):
            pass
    breadth_policy = c_supply_breadth_policy_from_policy(factory_policy)
    target = int(breadth_policy.get("minimum_credit_ready_rows") or breadth_policy.get("target_credit_ready_rows") or target or 20)
    growth_goal = max(target, int(breadth_policy.get("growth_goal_credit_ready_rows") or target))
    continue_after_floor = bool(breadth_policy.get("continue_after_minimum_floor", True))
    effective_target = growth_goal if continue_after_floor else target

    credit_ready_by_row: dict[str, dict[str, Any]] = {}
    probe_verified_pending_static_by_row: dict[str, dict[str, Any]] = {}
    selected_ids: set[str] = set()
    eligible_ids: set[str] = set()
    pending_ids: set[str] = set()
    blockers_by_reason: Counter[str] = Counter()
    source_summaries: list[dict[str, Any]] = []
    source_credit_counts: dict[str, int] = {}

    def _row_key(row: dict[str, Any]) -> str:
        return str(row.get("row_id") or row.get("target_theorem_name") or "")

    def _merge_row(existing: dict[str, Any] | None, row: dict[str, Any], *, source_name: str) -> dict[str, Any]:
        merged = dict(existing or {})
        rid = _row_key(row)
        if not rid:
            return merged
        merged.setdefault("row_id", rid)
        families = set(str(f) for f in (merged.get("families") or []) if str(f))
        families.update(str(f) for f in (row.get("families") or row.get("probe_verified_families") or row.get("matched_families") or []) if str(f))
        merged["families"] = sorted(families)
        sources_seen = set(str(x) for x in (merged.get("sources") or []) if str(x))
        sources_seen.add(source_name)
        merged["sources"] = sorted(sources_seen)
        for key in ("c_discriminating_evidence_status", "static_tools_result", "source_file"):
            if row.get(key) is not None and (merged.get(key) is None or key == "static_tools_result"):
                merged[key] = row.get(key)
        evidence = list(merged.get("queue_evidence") or [])
        seen_evidence = {str(item.get("work_id") or "") for item in evidence if isinstance(item, dict)}
        for item in row.get("queue_evidence") or []:
            if not isinstance(item, dict):
                continue
            wid = str(item.get("work_id") or "")
            if wid and wid not in seen_evidence:
                evidence.append(item)
                seen_evidence.add(wid)
        if evidence:
            merged["queue_evidence"] = evidence[:10]
        return merged

    for name, summary in sources:
        if not isinstance(summary, dict):
            continue
        credit_count = int(summary.get("credit_ready_count") or 0)
        source_credit_counts[name] = credit_count
        selected_ids.update(str(x) for x in (summary.get("selected_rows_order") or []) if str(x))
        eligible_ids.update(str(x) for x in (summary.get("eligible_rows_order") or []) if str(x))
        if not eligible_ids and int(summary.get("eligible_count") or 0) and selected_ids:
            eligible_ids.update(selected_ids)
        for row in summary.get("probe_pending_rows") or []:
            if isinstance(row, dict) and _row_key(row):
                pending_ids.add(_row_key(row))
        for row in summary.get("probe_verified_pending_static_rows") or []:
            if isinstance(row, dict) and _row_key(row):
                rid = _row_key(row)
                probe_verified_pending_static_by_row[rid] = _merge_row(probe_verified_pending_static_by_row.get(rid), row, source_name=name)
        for row in summary.get("credit_ready_rows") or []:
            if isinstance(row, dict) and _row_key(row):
                rid = _row_key(row)
                credit_ready_by_row[rid] = _merge_row(credit_ready_by_row.get(rid), row, source_name=name)
        for reason, count in (summary.get("blockers_by_reason") or {}).items():
            try:
                blockers_by_reason[str(reason)] += int(count or 0)
            except (TypeError, ValueError):
                continue
        source_summaries.append({
            "source": name,
            "source_path": summary.get("source_path") or "",
            "status": summary.get("status"),
            "credit_ready_count": credit_count,
            "credit_ready_unique_family_count": int(summary.get("credit_ready_unique_family_count") or len(summary.get("credit_ready_family_counts") or {})),
            "credit_ready_source_file_count": int(summary.get("credit_ready_source_file_count") or len(summary.get("credit_ready_source_file_counts") or {})),
            "credit_ready_source_root_count": int(summary.get("credit_ready_source_root_count") or len(summary.get("credit_ready_source_root_counts") or {})),
            "eligible_count": int(summary.get("eligible_count") or 0),
            "eligible_unique_family_count": int(summary.get("eligible_unique_family_count") or len(summary.get("eligible_family_counts") or {})),
            "selected_count": int(summary.get("selected_count") or 0),
            "probe_pending_count": int(summary.get("probe_pending_count") or 0),
            "probe_verified_count": int(summary.get("probe_verified_count") or 0),
            "probe_verified_pending_static_count": int(summary.get("probe_verified_pending_static_count") or 0),
            "source_demand_family_count": int(summary.get("source_demand_family_count") or 0),
            "blockers_by_reason": summary.get("blockers_by_reason") or {},
        })

    credit_ready_rows = [credit_ready_by_row[rid] for rid in sorted(credit_ready_by_row)]
    probe_verified_pending_static_rows = [
        probe_verified_pending_static_by_row[rid]
        for rid in sorted(set(probe_verified_pending_static_by_row) - set(credit_ready_by_row))
    ]
    family_counts: Counter[str] = Counter()
    source_file_counts: Counter[str] = Counter()
    source_root_counts: Counter[str] = Counter()
    for row in credit_ready_rows:
        family_counts.update(str(f) for f in (row.get("families") or []) if str(f))
        source_file = _c_supply_source_file(row)
        source_root = _c_supply_source_root(source_file)
        if source_file:
            source_file_counts[source_file] += 1
        if source_root:
            source_root_counts[source_root] += 1
    row_family_evidence_count = sum(family_counts.values())
    unique_family_count = len(family_counts)
    source_file_count = len(source_file_counts)
    source_root_count = len(source_root_counts)
    top_family_row_count = max(family_counts.values() or [0])
    family_target = int(breadth_policy.get("target_credit_ready_family_count") or 1)
    source_file_target = int(breadth_policy.get("target_credit_ready_source_file_count") or 1)
    source_root_target = int(breadth_policy.get("target_credit_ready_source_root_count") or 1)
    max_rows_per_family = int(breadth_policy.get("max_credit_ready_rows_per_family_before_warning") or 1)
    breadth_blockers: list[str] = []
    if len(credit_ready_rows) < target:
        breadth_blockers.append("credit_ready_row_target_not_met")
    if continue_after_floor and len(credit_ready_rows) < growth_goal:
        breadth_blockers.append("growth_goal_row_target_not_met")
    if unique_family_count < family_target:
        breadth_blockers.append("family_breadth_target_not_met")
    if source_file_count < source_file_target:
        breadth_blockers.append("source_file_breadth_target_not_met")
    if source_root_count < source_root_target:
        breadth_blockers.append("source_root_breadth_target_not_met")
    if top_family_row_count > max_rows_per_family:
        breadth_blockers.append("single_family_concentration_warning")
    pending_count = len(pending_ids - set(credit_ready_by_row))
    source_disagreement = len(set(source_credit_counts.values())) > 1 if source_credit_counts else False
    source_count_values = list(source_credit_counts.values())
    source_count_min = min(source_count_values) if source_count_values else 0
    source_count_max = max(source_count_values) if source_count_values else 0
    if len(credit_ready_rows) < target:
        status = "below_minimum_floor"
    elif breadth_blockers:
        status = "minimum_floor_reached_breadth_or_growth_debt"
    else:
        status = "growth_goal_reached" if continue_after_floor else "target_reached"
    if source_disagreement:
        status = f"{status}_source_disagreement"
    return {
        "schema": "leanmill-c-supply-credit-ready-read-model-v2",
        "source": "deduped_union" if sources else "none",
        "source_count": len(sources),
        "source_summaries": source_summaries,
        "source_credit_ready_counts": source_credit_counts,
        "source_disagreement": source_disagreement,
        "source_credit_ready_count_range": {
            "min": source_count_min,
            "max": source_count_max,
            "delta": source_count_max - source_count_min,
        },
        "source_reconciliation": {
            "required": source_disagreement,
            "rule": "When source counts disagree, report the deduped current local union separately from any external or stale read model; do not upgrade a higher source count without rerunning the same target-aware eligibility gate.",
            "credit_boundary": "Reconciliation metadata explains state disagreement only; it does not create C credit, benchmark lift, or proof credit.",
        },
        "c_supply_breadth_policy": breadth_policy,
        "breadth_status": "target_met" if not breadth_blockers else "target_not_met",
        "breadth_blockers": breadth_blockers,
        "breadth_metrics": {
            "credit_ready_unique_family_count": unique_family_count,
            "credit_ready_source_file_count": source_file_count,
            "credit_ready_source_root_count": source_root_count,
            "credit_ready_top_family_row_count": top_family_row_count,
            "family_target": family_target,
            "source_file_target": source_file_target,
            "source_root_target": source_root_target,
            "max_rows_per_family_before_warning": max_rows_per_family,
        },
        "target_credit_ready_rows": target,
        "minimum_credit_ready_rows": target,
        "effective_target_credit_ready_rows": effective_target,
        "growth_goal_credit_ready_rows": growth_goal,
        "continue_after_minimum_floor": continue_after_floor,
        "credit_ready_count": len(credit_ready_rows),
        "credit_ready_unique_row_count": len(credit_ready_rows),
        "credit_ready_row_family_evidence_count": row_family_evidence_count,
        "credit_ready_unique_family_count": unique_family_count,
        "credit_ready_source_file_count": source_file_count,
        "credit_ready_source_root_count": source_root_count,
        "eligible_count": len(eligible_ids) if eligible_ids else max([int(s.get("eligible_count") or 0) for _, s in sources] or [0]),
        "selected_count": len(selected_ids) if selected_ids else max([int(s.get("selected_count") or 0) for _, s in sources] or [0]),
        "probe_pending_count": pending_count,
        "probe_verified_pending_static_count": len(probe_verified_pending_static_rows),
        "remaining_to_target": max(0, target - len(credit_ready_rows)),
        "remaining_to_minimum": max(0, target - len(credit_ready_rows)),
        "remaining_to_effective_target": max(0, effective_target - len(credit_ready_rows)),
        "remaining_to_growth_goal": max(0, growth_goal - len(credit_ready_rows)),
        "credit_ready_rows": credit_ready_rows[:100],
        "probe_verified_pending_static_rows": probe_verified_pending_static_rows[:100],
        "credit_ready_family_counts": dict(sorted(family_counts.items())),
        "credit_ready_source_file_counts": dict(sorted(source_file_counts.items())),
        "credit_ready_source_root_counts": dict(sorted(source_root_counts.items())),
        "blockers_by_reason": dict(sorted(blockers_by_reason.items())),
        "status": status,
        "learning_unit_note": "C-supply credit-ready rows are benchmark-supply learning units, not governed proof-value exits; count is deduped across visible source snapshots. Probe-verified rows with pending static sweep are near-ready inventory, not strict C credit.",
    }


def _latest_c_supply_probe_seed_summary(c_supply_growth: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(c_supply_growth, dict):
        return {}
    summaries: list[dict[str, Any]] = []
    for round_rec in c_supply_growth.get("rounds") or []:
        if not isinstance(round_rec, dict):
            continue
        summary = round_rec.get("probe_seed_summary")
        if isinstance(summary, dict):
            summaries.append(summary)
    return summaries[-1] if summaries else {}


def _latest_c_supply_demand_summary(c_supply_growth: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(c_supply_growth, dict):
        return {}
    summaries: list[dict[str, Any]] = []
    for round_rec in c_supply_growth.get("rounds") or []:
        if not isinstance(round_rec, dict):
            continue
        summary = round_rec.get("demand_corpus")
        if isinstance(summary, dict):
            summaries.append(summary)
    return summaries[-1] if summaries else {}


def _c_supply_yield_policy(factory_policy: dict[str, Any] | None) -> dict[str, Any]:
    operations = _dict_field(factory_policy, "operations")
    obj = _dict_field(operations, "c_supply_yield_decomposition")

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    def float_value(key: str, fallback: float) -> float:
        try:
            return float(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    penalties = _dict_field(obj, "governance_integrity_penalties")
    next_levers = _dict_field(obj, "next_levers")
    return {
        "schema": str(obj.get("schema") or "leanmill-strict-c-yield-decomposition-policy-v1"),
        "source": "factory_policy" if obj else "kernel_default",
        "formula": str(
            obj.get("formula")
            or (
                "strict_c_yield_rate_per_hour = source_inventory_rate_per_hour * "
                "frontier_quality_multiplier * binding_quality_rate * static_no_signal_rate * "
                "probe_conversion_rate * governance_integrity_factor * diversity_retention_factor"
            )
        ),
        "time_basis": str(
            obj.get("time_basis")
            or "Use measured C-supply controller wall time when available; otherwise use the intelligence trailing window."
        ),
        "elo_rule": str(
            obj.get("elo_rule")
            or "Population Elo/P-UCB is routing memory only. It may shape frontier_quality_multiplier after enough resolved attempts, never proof credit."
        ),
        "pca_rule": str(
            obj.get("pca_rule")
            or "Fit predictive/PCA diagnostics only after enough resolved attempt rows exist; before that emit feature vectors and bottleneck terms only."
        ),
        "target_source_inventory_rate_per_hour": max(1.0, float_value("target_source_inventory_rate_per_hour", 20.0)),
        "min_elo_records_for_frontier_multiplier": max(1, int_value("min_elo_records_for_frontier_multiplier", 20)),
        "min_resolved_attempts_for_predictive_model": max(1, int_value("min_resolved_attempts_for_predictive_model", 200)),
        "min_rows_for_pca": max(2, int_value("min_rows_for_pca", 200)),
        "frontier_multiplier_min": max(0.0, float_value("frontier_multiplier_min", 0.5)),
        "frontier_multiplier_max": max(0.01, float_value("frontier_multiplier_max", 1.5)),
        "governance_integrity_penalties": {
            "invalid_negative_control": float(penalties.get("invalid_negative_control", 0.5)),
            "source_disagreement": float(penalties.get("source_disagreement", 0.9)),
            "live_queue_static_filter_leakage": float(penalties.get("live_queue_static_filter_leakage", 0.85)),
        },
        "next_levers": {
            "source_inventory_rate_factor": str(next_levers.get("source_inventory_rate_factor") or "increase outside-source and source-search integration lanes while keeping deterministic credit gates fixed"),
            "frontier_quality_multiplier": str(next_levers.get("frontier_quality_multiplier") or "accumulate resolved executable attempts and route by deterministic Elo/P-UCB once calibrated"),
            "binding_quality_rate": str(next_levers.get("binding_quality_rate") or "improve source-to-target binding and reject source packets that cannot bind to active rows"),
            "static_no_signal_rate": str(next_levers.get("static_no_signal_rate") or "shift sourcing toward families/source roots less likely to duplicate public or governed static positives"),
            "probe_conversion_rate": str(next_levers.get("probe_conversion_rate") or "repair family templates and matched controls that fail to convert strict-static survivors"),
            "governance_integrity_factor": str(next_levers.get("governance_integrity_factor") or "fix invalid controls, static leakage, and source-state disagreement before counting downstream yield"),
            "diversity_retention_factor": str(next_levers.get("diversity_retention_factor") or "increase non-laundered family, source-file, and source-root breadth"),
        },
        "credit_boundary": str(
            obj.get("credit_boundary")
            or "Yield decomposition is a read model and routing diagnostic. It does not create proof credit, benchmark lift, governance pass, or C credit-ready status."
        ),
    }


def _ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        den = float(denominator)
        if den <= 0:
            return None
        return max(0.0, float(numerator) / den)
    except (TypeError, ValueError):
        return None


def _clamped(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _latest_round_command_wall_s(c_supply_growth: dict[str, Any]) -> float:
    rounds = c_supply_growth.get("rounds") if isinstance(c_supply_growth, dict) else []
    if not isinstance(rounds, list) or not rounds:
        return 0.0
    latest = rounds[-1] if isinstance(rounds[-1], dict) else {}
    total = 0.0
    for rec in latest.get("commands") or []:
        if not isinstance(rec, dict):
            continue
        try:
            total += max(0.0, float(rec.get("wall_time_s") or 0.0))
        except (TypeError, ValueError):
            continue
    return total


def _growth_cycle_time_s(c_supply_growth: dict[str, Any], *, trailing_window_s: int) -> tuple[float, str]:
    if isinstance(c_supply_growth, dict):
        try:
            started = float(c_supply_growth.get("started_at_epoch") or 0.0)
            generated = float(c_supply_growth.get("generated_at_epoch") or 0.0)
            if generated > started > 0:
                return max(1.0, generated - started), "c_supply_growth_started_to_generated"
        except (TypeError, ValueError):
            pass
        command_wall = _latest_round_command_wall_s(c_supply_growth)
        if command_wall > 0:
            return max(1.0, command_wall), "latest_growth_round_command_wall_sum"
    return max(1.0, float(trailing_window_s or 1)), "factory_intelligence_trailing_window"


def _max_source_summary_metric(credit_ready_read_model: dict[str, Any], key: str) -> int:
    values: list[int] = []
    for row in credit_ready_read_model.get("source_summaries") or []:
        if not isinstance(row, dict):
            continue
        try:
            values.append(int(row.get(key) or 0))
        except (TypeError, ValueError):
            continue
    return max(values or [0])


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _strict_c_yield_decomposition(
    payload: dict[str, Any],
    *,
    factory_policy: dict[str, Any] | None,
    trailing_window_s: int,
) -> dict[str, Any]:
    """Policy-owned yield decomposition for strict C-supply growth.

    This is a diagnostic funnel, not a fitted model. It creates the feature
    surface needed for later prediction/PCA, but refuses to pretend a model is
    calibrated before there are enough resolved attempts.
    """
    policy = _c_supply_yield_policy(factory_policy)
    credit = _dict_field(payload, "c_supply_credit_ready_read_model")
    growth = _dict_field(payload, "c_supply_growth")
    population = _dict_field(payload, "population_elo")
    upstream = _dict_field(payload, "c_supply_upstream_rater")
    feedback = _dict_field(payload, "learning_feedback_read_model")
    blockers = _dict_field(credit, "blockers_by_reason")
    breadth = _dict_field(credit, "breadth_metrics")
    demand = _latest_c_supply_demand_summary(growth)

    cycle_time_s, cycle_basis = _growth_cycle_time_s(growth, trailing_window_s=trailing_window_s)
    cycle_hours = max(cycle_time_s / 3600.0, 1.0 / 3600.0)
    selected_count = int(credit.get("selected_count") or 0)
    eligible_count = int(credit.get("eligible_count") or 0)
    credit_ready_count = int(credit.get("credit_ready_count") or 0)
    probe_verified_count = max(_max_source_summary_metric(credit, "probe_verified_count"), credit_ready_count)
    probe_pending_count = int(credit.get("probe_pending_count") or 0)
    probe_terminal_nonuseful_count = 0
    for reason, count in blockers.items():
        if str(reason).startswith("family_spec_probe_terminal_nonuseful"):
            try:
                probe_terminal_nonuseful_count += int(count or 0)
            except (TypeError, ValueError):
                continue
    static_positive_count = int(blockers.get("static_tool_positive") or 0)
    static_unknown_count = int(blockers.get("static_result_unknown") or 0)
    static_infra_hold_count = int(blockers.get("static_harness_infra_hold") or 0)
    static_denominator = eligible_count + static_positive_count + static_unknown_count + static_infra_hold_count
    source_inventory_count = max(
        selected_count,
        int(demand.get("total_rows_written") or 0) if isinstance(demand, dict) else 0,
    )
    source_inventory_rate_per_hour = source_inventory_count / cycle_hours
    binding_quality_rate = _ratio(eligible_count, selected_count)
    static_no_signal_rate = _ratio(eligible_count, static_denominator)
    probe_denominator = max(probe_verified_count + probe_pending_count + probe_terminal_nonuseful_count, credit_ready_count)
    probe_conversion_rate = _ratio(credit_ready_count, probe_denominator)

    penalties = policy["governance_integrity_penalties"]
    governance_integrity = 1.0
    penalty_evidence: list[str] = []
    feedback_exits = _dict_field(feedback, "exit_counts")
    if int(feedback_exits.get("invalid_negative_control") or 0) > 0:
        governance_integrity *= float(penalties["invalid_negative_control"])
        penalty_evidence.append("invalid_negative_control")
    if bool(credit.get("source_disagreement")):
        governance_integrity *= float(penalties["source_disagreement"])
        penalty_evidence.append("source_disagreement")
    if int(blockers.get("live_queue_without_static_strict_no_signal") or 0) > 0:
        governance_integrity *= float(penalties["live_queue_static_filter_leakage"])
        penalty_evidence.append("live_queue_static_filter_leakage")
    governance_integrity = _clamped(governance_integrity, 0.0, 1.0)

    family_factor = _ratio(int(breadth.get("credit_ready_unique_family_count") or 0), int(breadth.get("family_target") or 0))
    source_file_factor = _ratio(int(breadth.get("credit_ready_source_file_count") or 0), int(breadth.get("source_file_target") or 0))
    source_root_factor = _ratio(int(breadth.get("credit_ready_source_root_count") or 0), int(breadth.get("source_root_target") or 0))
    diversity_factors = [v for v in (family_factor, source_file_factor, source_root_factor) if v is not None]
    diversity_retention = min([1.0] + diversity_factors) if diversity_factors else None

    pop_record_count = int(population.get("record_count") or 0)
    top_rating = None
    top_contestant = None
    for row in population.get("top_routing_priorities") or []:
        if not isinstance(row, dict):
            continue
        rating = _safe_float(row.get("rating"))
        if rating is not None:
            top_rating = rating
            top_contestant = str(row.get("contestant") or "")
            break
    initial_rating = 1000.0
    operations = _dict_field(factory_policy, "operations")
    pop_policy = _dict_field(operations, "population_elo")
    try:
        initial_rating = float(pop_policy.get("initial_rating") or initial_rating)
    except (TypeError, ValueError):
        pass
    if top_rating is not None and pop_record_count >= int(policy["min_elo_records_for_frontier_multiplier"]):
        expected_vs_initial = 1.0 / (1.0 + 10 ** ((initial_rating - top_rating) / 400.0))
        frontier_quality_multiplier = _clamped(
            2.0 * expected_vs_initial,
            float(policy["frontier_multiplier_min"]),
            float(policy["frontier_multiplier_max"]),
        )
        frontier_quality_confidence = "observed_population_elo"
    else:
        expected_vs_initial = None
        frontier_quality_multiplier = 1.0
        frontier_quality_confidence = "neutral_until_min_elo_records"

    target_source_rate = float(policy["target_source_inventory_rate_per_hour"])
    source_inventory_rate_factor = min(1.0, source_inventory_rate_per_hour / target_source_rate) if target_source_rate > 0 else None
    product_terms = {
        "source_inventory_rate_factor": source_inventory_rate_factor,
        "frontier_quality_multiplier": frontier_quality_multiplier,
        "binding_quality_rate": binding_quality_rate,
        "static_no_signal_rate": static_no_signal_rate,
        "probe_conversion_rate": probe_conversion_rate,
        "governance_integrity_factor": governance_integrity,
        "diversity_retention_factor": diversity_retention,
    }
    product = source_inventory_rate_per_hour
    for key, value in product_terms.items():
        if key == "source_inventory_rate_factor":
            continue
        if value is not None:
            product *= float(value)
    observed_rate_per_hour = credit_ready_count / cycle_hours

    bottleneck_candidates = {
        key: value for key, value in product_terms.items()
        if value is not None and key != "frontier_quality_multiplier"
    }
    if pop_record_count < int(policy["min_elo_records_for_frontier_multiplier"]):
        bottleneck_candidates["frontier_quality_multiplier"] = min(
            1.0,
            pop_record_count / float(policy["min_elo_records_for_frontier_multiplier"]),
        )
    elif frontier_quality_multiplier < 1.0:
        bottleneck_candidates["frontier_quality_multiplier"] = frontier_quality_multiplier
    current_bottleneck = min(bottleneck_candidates, key=lambda key: float(bottleneck_candidates[key])) if bottleneck_candidates else "unknown"
    next_lever = (policy.get("next_levers") or {}).get(current_bottleneck, "inspect yield feature vector and rerun the narrowest failing station")

    resolved_attempts = max(pop_record_count, int(upstream.get("n_brier_scored_now") or 0))
    predictive_status = (
        "ready_for_predictive_fit_and_pca"
        if resolved_attempts >= int(policy["min_resolved_attempts_for_predictive_model"])
        else "insufficient_resolved_attempts"
    )
    pca_status = (
        "ready_for_pca_fit"
        if resolved_attempts >= int(policy["min_rows_for_pca"])
        else "feature_vector_only_not_enough_rows"
    )
    feature_vector = {
        "cycle_time_s": round(cycle_time_s, 3),
        "source_inventory_count": source_inventory_count,
        "source_inventory_rate_per_hour": round(source_inventory_rate_per_hour, 6),
        "population_elo_record_count": pop_record_count,
        "top_population_contestant": top_contestant,
        "top_population_rating": top_rating,
        "frontier_quality_multiplier": round(frontier_quality_multiplier, 6),
        "binding_quality_rate": round(binding_quality_rate, 6) if binding_quality_rate is not None else None,
        "static_no_signal_rate": round(static_no_signal_rate, 6) if static_no_signal_rate is not None else None,
        "probe_conversion_rate": round(probe_conversion_rate, 6) if probe_conversion_rate is not None else None,
        "governance_integrity_factor": round(governance_integrity, 6),
        "family_breadth_factor": round(family_factor, 6) if family_factor is not None else None,
        "source_file_breadth_factor": round(source_file_factor, 6) if source_file_factor is not None else None,
        "source_root_breadth_factor": round(source_root_factor, 6) if source_root_factor is not None else None,
        "diversity_retention_factor": round(diversity_retention, 6) if diversity_retention is not None else None,
    }
    terms = {
        "time": {
            "cycle_time_s": round(cycle_time_s, 3),
            "cycle_time_basis": cycle_basis,
            "cycle_hours": round(cycle_hours, 6),
            "rule": policy["time_basis"],
        },
        "source_inventory": {
            "candidate_count": source_inventory_count,
            "rate_per_hour": round(source_inventory_rate_per_hour, 6),
            "target_rate_per_hour": target_source_rate,
            "rate_factor": round(source_inventory_rate_factor, 6) if source_inventory_rate_factor is not None else None,
            "latest_demand_total_rows_written": demand.get("total_rows_written") if isinstance(demand, dict) else None,
            "latest_demand_source_family_count": demand.get("source_family_count") if isinstance(demand, dict) else None,
        },
        "frontier_quality": {
            "multiplier": round(frontier_quality_multiplier, 6),
            "confidence": frontier_quality_confidence,
            "population_elo_record_count": pop_record_count,
            "min_records_for_multiplier": policy["min_elo_records_for_frontier_multiplier"],
            "top_contestant": top_contestant,
            "top_rating": top_rating,
            "expected_score_vs_initial": round(expected_vs_initial, 6) if expected_vs_initial is not None else None,
            "rule": policy["elo_rule"],
        },
        "binding_quality": {
            "eligible_count": eligible_count,
            "selected_count": selected_count,
            "rate": round(binding_quality_rate, 6) if binding_quality_rate is not None else None,
        },
        "static_no_signal": {
            "eligible_strict_static_survivor_proxy": eligible_count,
            "static_positive_count": static_positive_count,
            "static_unknown_count": static_unknown_count,
            "static_infra_hold_count": static_infra_hold_count,
            "denominator": static_denominator,
            "rate": round(static_no_signal_rate, 6) if static_no_signal_rate is not None else None,
        },
        "probe_conversion": {
            "credit_ready_count": credit_ready_count,
            "probe_verified_count": probe_verified_count,
            "probe_pending_count": probe_pending_count,
            "probe_terminal_nonuseful_count": probe_terminal_nonuseful_count,
            "denominator": probe_denominator,
            "rate": round(probe_conversion_rate, 6) if probe_conversion_rate is not None else None,
        },
        "governance_integrity": {
            "factor": round(governance_integrity, 6),
            "penalty_evidence": penalty_evidence,
            "rule": "penalties are policy-owned diagnostics; strict credit remains governed by existing C-supply gates",
        },
        "diversity_retention": {
            "factor": round(diversity_retention, 6) if diversity_retention is not None else None,
            "family_breadth_factor": round(family_factor, 6) if family_factor is not None else None,
            "source_file_breadth_factor": round(source_file_factor, 6) if source_file_factor is not None else None,
            "source_root_breadth_factor": round(source_root_factor, 6) if source_root_factor is not None else None,
            "aggregation": "minimum_target_coverage",
        },
    }
    return {
        "schema": "leanmill-strict-c-yield-decomposition-v1",
        "policy": policy,
        "formula": policy["formula"],
        "observed_strict_c_rate_per_hour": round(observed_rate_per_hour, 6),
        "modeled_strict_c_rate_per_hour": round(product, 6),
        "terms": terms,
        "feature_vector": feature_vector,
        "current_bottleneck": current_bottleneck,
        "next_lever": next_lever,
        "predictive_model_readiness": {
            "status": predictive_status,
            "resolved_attempt_rows": resolved_attempts,
            "min_resolved_attempts": policy["min_resolved_attempts_for_predictive_model"],
            "pca_status": pca_status,
            "min_rows_for_pca": policy["min_rows_for_pca"],
            "rule": policy["pca_rule"],
        },
        "credit_boundary": policy["credit_boundary"],
    }


def _c_supply_source_materialization_read_model(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    rows = [row for row in (obj.get("rows") or []) if isinstance(row, dict)]
    ready_ids = [
        str(row.get("row_id") or "")
        for row in rows
        if str(row.get("status") or "") == "source_ready" and str(row.get("row_id") or "")
    ]
    materialization = _dict_field(obj, "materialization")
    return {
        "schema": "leanmill-c-supply-source-materialization-read-model-v1",
        "status": obj.get("status"),
        "requested_row_count": int(obj.get("requested_row_count") or 0),
        "unresolved_after_count": int(obj.get("unresolved_after_count") or 0),
        "ready_row_ids": sorted(set(ready_ids)),
        "ready_row_count": len(set(ready_ids)),
        "materialization_counts": materialization.get("counts") or {},
        "credit_boundary": obj.get("credit_boundary"),
        "anti_laundering_guard": obj.get("anti_laundering_guard"),
    }


def _c_supply_source_materialization_satisfies(probe_seed_summary: dict[str, Any], source_materialization: dict[str, Any]) -> bool:
    if not isinstance(probe_seed_summary, dict) or not isinstance(source_materialization, dict):
        return False
    if str(source_materialization.get("status") or "") != "materialized_c_supply_sources":
        return False
    if int(source_materialization.get("unresolved_after_count") or 0) != 0:
        return False
    unresolved_ids = {
        str(item.get("row_id") or "")
        for item in (probe_seed_summary.get("unresolved_rows") or [])
        if isinstance(item, dict)
        and str(item.get("reason") or "") == "missing_source_file"
        and str(item.get("row_id") or "")
    }
    ready_ids = set(str(row_id) for row_id in (source_materialization.get("ready_row_ids") or []) if str(row_id))
    return bool(unresolved_ids) and unresolved_ids.issubset(ready_ids)


def _action_impact_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    flow = payload["learning_unit_flow"]
    losses = payload["loss_accounting"]
    feedback = payload.get("learning_feedback_read_model") or {}
    actions: list[dict[str, Any]] = []
    actions.append({
        "action_id": "leanmill.source_search_to_binding",
        "action_kind": "source_search_integrate",
        "decision_stage": "source_qualification_to_binding",
        "objective_metric": "source_binding_probe_enqueued",
        "expected_effect": "convert canary-ready source inventory into bounded source-to-canary binding tasks",
        "observed_outcome": {
            "source_canary_ready_candidates": flow["source_canary_ready_candidates"],
            "source_search_holds_with_ready_candidates": flow["source_search_holds_with_ready_candidates"],
            "source_to_canary_binding_enqueued": flow["source_to_canary_binding_enqueued"],
            "source_binding_probe_enqueued": flow["source_binding_probe_enqueued"],
        },
        "impact_summary": "binding is the current conversion risk when ready source inventory is held",
        "guardrail_metrics": {
            "source_search_has_no_proof_credit": True,
            "governance_gate_is_only_ratifier": True,
        },
        "requires_human_review": bool(losses["source_search_integrations"].get("ready_held_count", 0) > 0),
    })
    actions.append({
        "action_id": "leanmill.probe_to_governance",
        "action_kind": "probe_and_govern",
        "decision_stage": "proof_execution_to_governance",
        "objective_metric": "ratified_closure_or_exact_gap_or_valid_falsifier",
        "expected_effect": "turn bounded proof probes into governed scientific exits",
        "observed_outcome": {
            "probe_worker_done": flow["probe_worker_done"],
            "scoreboard_tail_counts": flow["scoreboard_tail_counts"],
        },
        "impact_summary": "recent probes are not yet producing governed value exits",
        "guardrail_metrics": {
            "negative_control_unexpected_pass_count": flow["scoreboard_tail_counts"].get("negative_control_unexpected_pass_count", 0),
            "negative_control_invalid_fail_count": flow["scoreboard_tail_counts"].get("negative_control_invalid_fail_count", 0),
            "learning_feedback_review_required_count": feedback.get("review_required_count", 0),
        },
        "requires_human_review": bool(feedback.get("review_required_count", 0)),
    })
    credit_ready = payload.get("c_supply_credit_ready_read_model") or {}
    actions.append({
        "action_id": "leanmill.c_supply_credit_ready_rows",
        "action_kind": "c_supply_growth",
        "decision_stage": "benchmark_supply_to_credit_ready_row",
        "objective_metric": "c_supply_credit_ready_count",
        "expected_effect": "increase strict static-fail, family-probe-verified C-discriminating rows without proof-value laundering",
        "observed_outcome": {
            "credit_ready_count": credit_ready.get("credit_ready_count"),
            "target_credit_ready_rows": credit_ready.get("target_credit_ready_rows"),
            "remaining_to_target": credit_ready.get("remaining_to_target"),
            "source": credit_ready.get("source"),
        },
        "impact_summary": "credit-ready C-supply rows are the current benchmark-supply learning unit",
        "guardrail_metrics": {
            "proof_credit_eligible": False,
            "uses_static_fail_filter": True,
            "uses_family_probe_verification": True,
        },
        "requires_human_review": False,
    })
    return actions


def _agentic_portfolio_read_model(obj: dict[str, Any], *, path: str = "") -> dict[str, Any]:
    if not isinstance(obj, dict) or not obj:
        return {
            "schema": "leanmill-agentic-portfolio-read-model-v1",
            "status": "missing",
            "path": path,
            "next_action": "run leanmill_agentic_portfolio_controller.py from the 24x7 runner after the governance sentinel",
        }
    commands = [row for row in (obj.get("commands") or []) if isinstance(row, dict)]
    decisions = [row for row in (obj.get("decisions") or []) if isinstance(row, dict)]
    command_count = int(obj.get("command_count") or len(commands))
    failed_count = int(obj.get("failed_command_count") or sum(1 for row in commands if int(row.get("returncode") or 0) != 0))
    ran_decisions = [row for row in decisions if row.get("run")]
    preflight_blocked = [
        {
            "lane": row.get("lane"),
            "reason": row.get("reason"),
            "pressure_reason": row.get("pressure_reason"),
            "preflight": row.get("preflight"),
        }
        for row in decisions
        if not row.get("run") and str(row.get("reason") or "").startswith("preflight_")
    ]
    zero_yield: list[dict[str, Any]] = []
    lane_returncodes: dict[str, int] = {}
    for row in commands:
        lane = str(row.get("lane") or "")
        lane_returncodes[lane] = int(row.get("returncode") or 0)
        stdout = str(row.get("stdout_tail") or "")
        parsed: dict[str, Any] = {}
        for line in reversed(stdout.splitlines()):
            if not line.strip().startswith("{"):
                continue
            try:
                maybe = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(maybe, dict):
                parsed = maybe
                break
        if not parsed:
            continue
        enqueued = int(parsed.get("enqueued") or 0)
        job_count = int(parsed.get("job_count") or parsed.get("cluster_count") or 0)
        claimed = parsed.get("claimed")
        if enqueued == 0 and (claimed is False or job_count == 0 or "birth_pressure_row_count" in parsed):
            zero_yield.append({
                "lane": lane,
                "reason": row.get("reason"),
                "parsed_stdout": parsed,
            })
    if command_count == 0 and preflight_blocked:
        status = "all_pressure_lanes_preflight_blocked"
        next_action = "fix the upstream inventory gap named by the preflight receipts before spending agentic generation budget"
    elif command_count == 0:
        status = "no_lane_selected"
        next_action = "inspect portfolio decisions and queue pressure; no generation lane was selected"
    elif failed_count:
        status = "command_failed"
        next_action = "repair failed portfolio lane command before interpreting generation conversion"
    elif len(zero_yield) == command_count:
        status = "all_selected_lanes_zero_yield"
        next_action = "debug each selected generation lane's input pressure and eligibility filters; do not raise concurrency until at least one lane converts to queued work or a typed skip reason explains zero yield"
    elif zero_yield:
        status = "partial_zero_yield"
        next_action = "keep converting productive lanes and debug zero-yield selected lanes before scaling agentic spend"
    else:
        status = "productive_or_skipped"
        next_action = "join selected lane outputs to deterministic static/probe/governance outcomes before changing budget"
    return {
        "schema": "leanmill-agentic-portfolio-read-model-v1",
        "status": status,
        "path": path,
        "source_status": obj.get("status"),
        "policy_profile": obj.get("policy_profile"),
        "run_id": obj.get("run_id"),
        "command_count": command_count,
        "failed_command_count": failed_count,
        "selected_lane_count": len(ran_decisions),
        "selected_lanes": [str(row.get("lane") or "") for row in ran_decisions],
        "skipped_lanes": [
            {"lane": row.get("lane"), "reason": row.get("reason"), "pressure_reason": row.get("pressure_reason"), "preflight": row.get("preflight")}
            for row in decisions
            if not row.get("run")
        ],
        "preflight_blocked_lanes": preflight_blocked,
        "zero_yield_selected_lanes": zero_yield,
        "lane_returncodes": lane_returncodes,
        "credit_boundary": obj.get("credit_boundary") or "agentic_portfolio_dispatch_only_no_credit",
        "next_action": next_action,
    }




def _population_elo_summary(obj: dict[str, Any], *, limit: int = 12) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    ratings = [r for r in obj.get("ratings") or [] if isinstance(r, dict)]
    top = []
    by_scope: Counter[str] = Counter()
    for row in ratings:
        contestant = str(row.get("contestant") or "")
        scope = contestant.split(":", 1)[0] if ":" in contestant else "unknown"
        by_scope[scope] += 1
        if len(top) < limit:
            top.append({
                "contestant": contestant,
                "rating": row.get("rating"),
                "p_ucb_priority": row.get("p_ucb_priority"),
                "games": row.get("games"),
                "wins": row.get("wins"),
                "losses": row.get("losses"),
                "ties": row.get("ties"),
            })
    _record_count = int(obj.get("record_count") or 0)
    return {
        "schema": "leanmill-population-elo-summary-v1",
        "checkpoint": obj.get("checkpoint"),
        "run_id": obj.get("run_id"),
        "record_count": _record_count,
        "row_count": int(obj.get("row_count") or 0),
        "contestant_count": int(obj.get("contestant_count") or 0),
        "event_count": int(obj.get("event_count") or 0),
        "contestant_scope_counts": dict(sorted(by_scope.items())),
        "top_routing_priorities": top,
        # Honest dark-feature flag: population_elo is DARK when no records are produced (e.g. its
        # checkpoint input is empty/absent), so the pane shows "inactive" rather than presenting zeros
        # as a measured-but-empty leaderboard. Consumers gate the frontier-quality signal on this.
        "active": _record_count > 0,
        "active_note": ("observed" if _record_count > 0 else
                        "dark: no population_elo records produced (empty/absent checkpoint input)"),
        "non_laundering_note": obj.get("non_laundering_note") or "routing memory only; proof credit remains governed",
    }



def _upstream_rater_summary(
    obj: dict[str, Any],
    *,
    credit_ready_read_model: dict[str, Any],
    limit: int = 12,
) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    combined = [r for r in obj.get("combined_ranking") or [] if isinstance(r, dict)]
    model_output = _dict_field(obj, "model_output")
    model_ratings = {
        str(row.get("family") or ""): row
        for row in (model_output.get("ratings") or [])
        if isinstance(row, dict) and str(row.get("family") or "")
    }
    credit_counts = credit_ready_read_model.get("credit_ready_family_counts") if isinstance(credit_ready_read_model, dict) else {}
    if not isinstance(credit_counts, dict):
        credit_counts = {}
    joined: list[dict[str, Any]] = []
    briers: list[float] = []
    probs: list[float] = []
    outcomes: list[float] = []
    for rank, row in enumerate(combined, start=1):
        family = str(row.get("family") or "")
        rating = model_ratings.get(family) or {}
        p_useful = rating.get("p_useful_exit")
        p_static = rating.get("p_static_strict_fail")
        p_template = rating.get("p_template_convertible")
        useful_outcome = 1.0 if int(credit_counts.get(family) or 0) > 0 else 0.0
        brier = None
        try:
            p_val = float(p_useful)
            if 0.0 <= p_val <= 1.0:
                brier = round((p_val - useful_outcome) ** 2, 6)
                briers.append(float(brier))
                probs.append(p_val)
                outcomes.append(useful_outcome)
        except (TypeError, ValueError):
            pass
        joined.append({
            "family": family,
            "effective_rank": row.get("effective_rank") or rank,
            "deterministic_rank": row.get("deterministic_rank"),
            "model_rank": row.get("model_rank"),
            "row_count": row.get("row_count"),
            "deterministic_routing_score": row.get("deterministic_routing_score"),
            "p_useful_exit": p_useful,
            "p_static_strict_fail": p_static,
            "p_template_convertible": p_template,
            "useful_exit_observed_now": bool(useful_outcome),
            "credit_ready_count_observed_now": int(credit_counts.get(family) or 0),
            "brier_useful_exit_now": brier,
            "main_risk": rating.get("main_risk"),
        })
    return {
        "schema": "leanmill-c-supply-upstream-rater-summary-v1",
        "mode": obj.get("mode"),
        "model": obj.get("model"),
        "run_model": bool(obj.get("run_model")),
        "candidate_count": int(obj.get("candidate_count") or 0),
        "model_validation": _dict_field(obj, "model_validation"),
        "n_brier_scored_now": len(briers),
        "mean_brier_useful_exit_now": round(sum(briers) / len(briers), 6) if briers else None,
        "calibration_gap_mean_pred_minus_outcome_now": round((sum(probs) / len(probs)) - (sum(outcomes) / len(outcomes)), 6) if probs else None,
        "joined_routing_outcomes": joined[:limit],
        "ordered_families": obj.get("ordered_families")[:limit] if isinstance(obj.get("ordered_families"), list) else [],
        "calibration_join_key": _dict_field(obj, "calibration_join_key"),
        "calibration_note": "Brier is a live upstream-routing calibration signal over observed credit-ready outcomes, not proof credit or governance evidence.",
        "credit_boundary": obj.get("credit_boundary") or "routing_forecast_only_no_proof_credit",
    }

def _recommendations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    losses = payload["loss_accounting"]
    flow = payload["learning_unit_flow"]
    station = payload["subprocess_metrics"]["by_station"]
    queue = payload["queue"]
    obs_bottlenecks = (payload.get("observability") or {}).get("bottlenecks") or []
    promotion = payload.get("family_promotion_diagnostics") or {}
    family_spec_gate = payload.get("family_spec_gate") or {}
    source_probe = (payload.get("conversion_diagnostics") or {}).get("stage_outcome_counts", {}).get("probe_source_binding", {})
    source_probe_total = sum(int(v or 0) for v in source_probe.values()) if isinstance(source_probe, dict) else 0
    source_probe_value = sum(
        int(source_probe.get(k, 0) or 0)
        for k in ("ratified_closure", "exact_gap_candidate", "valid_falsifier")
    ) if isinstance(source_probe, dict) else 0
    open_kind_counts = queue.get("open_kind_counts") or queue.get("by_kind") or {}
    version_health = payload.get("worker_version_health") or {}
    replenisher = payload.get("backlog_replenisher") or {}
    proof_lane = payload.get("proof_lane_rca") or {}
    heavy_lean_pressure = payload.get("heavy_lean_process_pressure") or {}
    pressure_risks = set(heavy_lean_pressure.get("risk_classes") or [])
    learning_feedback_model = _dict_field(payload, "learning_feedback_read_model")
    feedback_exit_counts = _dict_field(learning_feedback_model, "exit_counts")
    upstream_rater = _dict_field(payload, "c_supply_upstream_rater")
    upstream_validation = _dict_field(upstream_rater, "model_validation")
    run_obs = _dict_field(payload, "run_observability")
    run_readout = _dict_field(run_obs, "operator_readout")
    run_status = str(run_readout.get("status") or "")
    if run_readout and run_status in {"blocked", "stuck", "needs_inspection"}:
        recommendations.append({
            "priority": _recommendation_priority(payload, "run_observability_operator_bottleneck", 158),
            "class": "run_observability_operator_bottleneck",
            "why": run_readout.get("why"),
            "next_action": run_readout.get("next_action"),
            "evidence": {
                "run_tag": run_obs.get("run_tag"),
                "status": run_status,
                "primary_bottleneck": run_readout.get("primary_bottleneck"),
                "warnings": run_obs.get("warnings", []),
                "readout": run_readout,
            },
        })
    if upstream_rater and upstream_validation and bool(upstream_rater.get("run_model")) and not upstream_validation.get("ok", True):
        recommendations.append({
            "priority": _recommendation_priority(payload, "upstream_rater_output_invalid", 134),
            "class": "upstream_rater_output_invalid",
            "why": "the upstream GPT routing rater ran but did not emit a valid typed forecast artifact",
            "next_action": "repair the routing-rater prompt/schema before using advisory mode; keep deterministic Elo ordering active",
            "evidence": {
                "mode": upstream_rater.get("mode"),
                "model": upstream_rater.get("model"),
                "candidate_count": upstream_rater.get("candidate_count"),
                "model_validation": upstream_validation,
            },
        })
    if upstream_rater and upstream_rater.get("mean_brier_useful_exit_now") is not None:
        recommendations.append({
            "priority": _recommendation_priority(payload, "upstream_rater_calibration_visible", 93),
            "class": "upstream_rater_calibration_visible",
            "why": "upstream routing predictions are now joinable to observed credit-ready family outcomes",
            "next_action": "keep observe_only until the Brier/calibration trend beats deterministic population Elo on enough joined routing decisions",
            "evidence": {
                "mode": upstream_rater.get("mode"),
                "model": upstream_rater.get("model"),
                "n_brier_scored_now": upstream_rater.get("n_brier_scored_now"),
                "mean_brier_useful_exit_now": upstream_rater.get("mean_brier_useful_exit_now"),
                "calibration_gap_mean_pred_minus_outcome_now": upstream_rater.get("calibration_gap_mean_pred_minus_outcome_now"),
                "joined_routing_outcomes": (upstream_rater.get("joined_routing_outcomes") or [])[:5],
            },
        })
    if int(feedback_exit_counts.get("invalid_negative_control") or 0):
        recommendations.append({
            "priority": _recommendation_priority(payload, "invalid_negative_control_feedback_debt", 142),
            "class": "invalid_negative_control_feedback_debt",
            "why": "recent probes include malformed negative controls, so matched-canary evidence is not reliable until the family templates are repaired",
            "next_action": "route these feedback records into family-template repair/backfill tasks and block value credit until the negative control fails for the family ingredient rather than syntax or elaboration shape",
            "evidence": {
                "exit_counts": feedback_exit_counts,
                "review_required_count": learning_feedback_model.get("review_required_count"),
                "recent_feedback": (learning_feedback_model.get("recent_feedback") or [])[:5],
            },
        })
    if "warm_repl_overprovision_risk" in pressure_risks:
        recommendations.append({
            "priority": _recommendation_priority(payload, "heavy_lean_repl_overprovision_risk", 127),
            "class": "heavy_lean_repl_overprovision_risk",
            "why": "multiple repair-canary drains and Lean REPLs are active while proof execution is serialized by the shared heavy-Lean slot",
            "next_action": "create warm REPLs only while owning the heavy-Lean slot and avoid running benchmark/proof drains concurrently with 24x7 proof workers",
            "evidence": heavy_lean_pressure,
        })
    if "external_lean_contention_risk" in pressure_risks:
        recommendations.append({
            "priority": _recommendation_priority(payload, "external_lean_contention_risk", 96),
            "class": "external_lean_contention_risk",
            "why": "a non-LeanMill Lean/lake process is active while LeanMill proof probes are waiting on heavy Lean work",
            "next_action": "avoid overlapping unrelated lake/Lean jobs with proof-lane drains when measuring cycle time or running a benchmark",
            "evidence": heavy_lean_pressure,
        })
    if proof_lane.get("bottleneck_class") == "proof_candidate_supply_blocked":
        recommendations.append({
            "priority": _recommendation_priority(payload, "proof_candidate_supply_blocked", 135),
            "class": "proof_candidate_supply_blocked",
            "why": "family-spec proof probes cannot be scaled because candidate supply is duplicated, cooldown-blocked, or below diversity floor",
            "next_action": "repair replenisher candidate generation and family-spec row diversity before increasing workers or floors",
            "evidence": proof_lane,
        })
    c_supply = _dict_field(payload, "c_supply_batch")
    c_cleaner = _dict_field(payload, "c_supply_expost_cleaner")
    c_clean_selection = _dict_field(payload, "c_supply_clean_selection")
    c_supply_growth = _dict_field(payload, "c_supply_growth")
    agentic_portfolio = _dict_field(payload, "agentic_portfolio_read_model")
    c_credit_model = _dict_field(payload, "c_supply_credit_ready_read_model")
    population = _dict_field(payload, "population_elo")
    population_top = population.get("top_routing_priorities") if isinstance(population.get("top_routing_priorities"), list) else []
    if population_top and int(population.get("record_count") or 0) > 0:
        recommendations.append({
            "priority": _recommendation_priority(payload, "population_routing_priorities_ready", 91),
            "class": "population_routing_priorities_ready",
            "why": "observed executable outcomes have enough population records to rank arms, families, and candidate tactics for routing",
            "next_action": "feed top population/P-UCB priorities into bounded family, source, and tactic selection; keep governance receipts as the only proof-value authority",
            "evidence": {
                "record_count": population.get("record_count"),
                "row_count": population.get("row_count"),
                "contestant_count": population.get("contestant_count"),
                "contestant_scope_counts": population.get("contestant_scope_counts"),
                "top_routing_priorities": population_top[:8],
                "non_laundering_note": population.get("non_laundering_note"),
            },
        })
    yield_decomp = _dict_field(payload, "strict_c_yield_decomposition")
    if yield_decomp.get("current_bottleneck") and yield_decomp.get("current_bottleneck") != "unknown":
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_yield_bottleneck", 152),
            "class": "c_supply_yield_bottleneck",
            "why": "strict C growth is bottlenecked by the lowest policy-owned yield term rather than by raw closure count alone",
            "next_action": yield_decomp.get("next_lever"),
            "evidence": {
                "formula": yield_decomp.get("formula"),
                "current_bottleneck": yield_decomp.get("current_bottleneck"),
                "observed_strict_c_rate_per_hour": yield_decomp.get("observed_strict_c_rate_per_hour"),
                "modeled_strict_c_rate_per_hour": yield_decomp.get("modeled_strict_c_rate_per_hour"),
                "feature_vector": yield_decomp.get("feature_vector"),
                "predictive_model_readiness": yield_decomp.get("predictive_model_readiness"),
                "credit_boundary": yield_decomp.get("credit_boundary"),
            },
        })
    _ap_status = agentic_portfolio.get("status")
    if _ap_status in {"command_failed", "all_selected_lanes_zero_yield", "partial_zero_yield", "missing", "all_pressure_lanes_preflight_blocked"}:
        # "missing" is a COLD-START / cyclic-read artifact, NOT a yield failure: the portfolio
        # controller runs `post_factory_intelligence` (it CONSUMES this very report), so on a cold
        # start — or any cycle before it has run once — factory reads the prior cycle's absent output.
        # Scoring that as a top-priority failure made it the bogus #1 recommendation. Demote the
        # `missing` case to informational (its fallback priority drops below the genuine-failure recs);
        # a real failure (command_failed / zero_yield / preflight_blocked) keeps the high priority. The
        # `class` string is UNCHANGED — the 24x7_runner self-correction contract keys on it.
        _ap_missing = _ap_status == "missing"
        recommendations.append({
            "priority": _recommendation_priority(
                payload, "agentic_portfolio_zero_yield_or_missing", 110 if _ap_missing else 156),
            "class": "agentic_portfolio_zero_yield_or_missing",
            "why": (
                "the agentic portfolio output is absent this cycle — expected on a cold start or before "
                "the post-factory portfolio controller has produced its first output; informational, not a "
                "yield failure"
                if _ap_missing else
                "the policy-selected agentic generation portfolio did not produce queued downstream work, "
                "failed, or was deterministically blocked before spend, so agentic intent is not yet "
                "converting into verification inventory"),
            "next_action": agentic_portfolio.get("next_action"),
            "evidence": agentic_portfolio,
        })
    exec_modes = _dict_field(payload, "execution_mode_read_model")
    if exec_modes.get("gap_classes"):
        recommendations.append({
            "priority": _recommendation_priority(payload, "execution_mode_observability_gap", 153),
            "class": "execution_mode_observability_gap",
            "why": "the intended agentic/deterministic execution architecture is not fully visible in live workers or recent queue usage",
            "next_action": "inspect execution_mode_read_model, restart missing policy-declared lane subscribers, and verify source/binding generation is flowing through subscription-agent lanes while credit stays deterministic",
            "evidence": {
                "gap_classes": exec_modes.get("gap_classes"),
                "intended_worker_counts_by_mode": exec_modes.get("intended_worker_counts_by_mode"),
                "observed_active_workers_by_mode": exec_modes.get("observed_active_workers_by_mode"),
                "observed_open_work_by_mode": exec_modes.get("observed_open_work_by_mode"),
                "subscription_agent_usage": exec_modes.get("subscription_agent_usage"),
                "credit_boundary": exec_modes.get("credit_boundary"),
            },
        })
    if exec_modes.get("budget_gap_classes"):
        recommendations.append({
            "priority": _recommendation_priority(payload, "execution_budget_underprovisioned", 154),
            "class": "execution_budget_underprovisioned",
            "why": "a policy-declared complex generation lane is below the token, iteration, or timeout floor needed for source/family/binding work",
            "next_action": "raise the live profile budget in leanmill_factory_policy.json or downgrade the task to deterministic/compact review; do not pass one-off token or timeout flags",
            "evidence": {
                "budget_gap_classes": exec_modes.get("budget_gap_classes"),
                "declared_budgets": exec_modes.get("declared_budgets"),
                "declared_models": exec_modes.get("declared_models"),
                "credit_boundary": exec_modes.get("credit_boundary"),
            },
        })
    c_selection = c_clean_selection if c_clean_selection else (_dict_field(c_supply, "selection"))
    c_params = _dict_field(c_supply, "params")
    c_selected = int(c_selection.get("selected_count") or 0)
    c_min = int(c_params.get("min_freeze_rows") or 20)
    target_resolution = _dict_field(payload, "target_resolution_read_model")
    evaluation = _dict_field(payload, "evaluation_harness_read_model")
    if evaluation.get("status") in {
        "credited_run_masked_residual_memory",
        "credited_run_limited_slice",
        "credited_run_observability_unknown",
    }:
        recommendations.append({
            "priority": _recommendation_priority(payload, "evaluation_harness_observability_debt", 147),
            "class": "evaluation_harness_observability_debt",
            "why": "a benchmark run exists, but its scope or candidate routing prevents it from serving as residual-family mechanism evidence",
            "next_action": evaluation.get("next_action"),
            "evidence": evaluation,
        })
    elif evaluation.get("status") == "credited_run_recorded_no_benchmark_lift":
        recommendations.append({
            "priority": _recommendation_priority(payload, "evaluation_harness_no_benchmark_lift", 142),
            "class": "evaluation_harness_no_benchmark_lift",
            "why": "the full credited benchmark recorded clean observability, but residual-memory did not beat the governed public/static baseline on closure rate or attempt efficiency",
            "next_action": evaluation.get("next_action"),
            "evidence": evaluation,
        })
    elif evaluation.get("status") == "credited_run_recorded_with_benchmark_lift":
        recommendations.append({
            "priority": _recommendation_priority(payload, "evaluation_harness_lift_ready_for_internal_publish", 148),
            "class": "evaluation_harness_lift_ready_for_internal_publish",
            "why": "the full credited benchmark recorded a pre-declared lift over the governed public/static baseline",
            "next_action": evaluation.get("next_action"),
            "evidence": evaluation,
        })
    elif evaluation.get("status") == "ready_for_credited_run":
        recommendations.append({
            "priority": _recommendation_priority(payload, "evaluation_harness_ready_for_credited_run", 145),
            "class": "evaluation_harness_ready_for_credited_run",
            "why": "the selected pre-registered benchmark slice has concrete target bindings and the contract can be checked without skip flags",
            "next_action": evaluation.get("next_action"),
            "evidence": evaluation,
        })
    elif evaluation.get("status") == "prep_blocked":
        recommendations.append({
            "priority": _recommendation_priority(payload, "evaluation_harness_prep_blocked", 145),
            "class": "evaluation_harness_prep_blocked",
            "why": "the pre-registered benchmark cannot produce a credited run until prep blockers are resolved",
            "next_action": evaluation.get("next_action"),
            "evidence": evaluation,
        })
    competitive_inventory = _dict_field(payload, "competitive_inventory_read_model")
    if competitive_inventory.get("status") == "pr_a1_compile_l3_audit_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "pr_a1_compile_l3_audit_ready", 144),
            "class": "pr_a1_compile_l3_audit_ready",
            "why": "the PR_A1 candidate is statically sorry-free, but still needs compile and L3 anti-pattern audit before it can become a public artifact candidate",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "pr_a1_l3_review_needed":
        recommendations.append({
            "priority": _recommendation_priority(payload, "pr_a1_l3_review_needed", 144),
            "class": "pr_a1_l3_review_needed",
            "why": "the PR_A1 candidate compiles but the L3 audit recorded advisory flags that need review before public artifact promotion",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "pr_a1_audit_blocked":
        recommendations.append({
            "priority": _recommendation_priority(payload, "pr_a1_audit_blocked", 144),
            "class": "pr_a1_audit_blocked",
            "why": "the PR_A1 audit found a compile, axiom, static, or confirmed L3 blocker",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_reports_ready_for_task_extraction":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_report_task_extraction_ready", 143),
            "class": "route_c_gap_report_task_extraction_ready",
            "why": "Route C produced audit-grade gap reports; the next value is to convert those missing-lemma surfaces into proof-loop tasks",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_task_execution_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_task_execution_ready", 143),
            "class": "route_c_gap_task_execution_ready",
            "why": "Route C gap reports have been converted into queued exact-gap/decomposition proposal tasks with no proof-credit path",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_exact_gap_heavy_replay_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_exact_gap_heavy_replay_ready", 147),
            "class": "route_c_exact_gap_heavy_replay_ready",
            "why": "a Route C exact-gap packet survived duplicate-target and cheap-tactic replay checks; heavier Lean replay is the next discriminator",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_exact_gap_replay_probe_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_exact_gap_replay_probe_ready", 146),
            "class": "route_c_exact_gap_replay_probe_ready",
            "why": "governance-checked Route C exact-gap candidates need duplicate and cheap-replay screening before promotion",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_exact_gap_duplicate_repair_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_exact_gap_duplicate_repair_ready", 145),
            "class": "route_c_exact_gap_duplicate_repair_ready",
            "why": "all Route C exact-gap candidates duplicate target statements, so the synthesis prompt/gate must be tightened before more replay",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_exact_gap_probe_disqualified":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_exact_gap_probe_disqualified", 144),
            "class": "route_c_exact_gap_probe_disqualified",
            "why": "cheap replay closed a purported exact-gap packet, so the packet should be disqualified rather than promoted",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_hold_synthesis_execution_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_hold_synthesis_execution_ready", 143),
            "class": "route_c_gap_hold_synthesis_execution_ready",
            "why": "terminal Route C holds have typed target/error context available and need a bounded second-pass proposal worker run",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_hold_synthesis_retry_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_hold_synthesis_retry_ready", 144),
            "class": "route_c_gap_hold_synthesis_retry_ready",
            "why": "at least one Route C hold-synthesis task failed before producing a proposal, so retry or repair before interpreting the lane",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_synthesis_governance_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_synthesis_governance_ready", 145),
            "class": "route_c_gap_synthesis_governance_ready",
            "why": "Route C hold synthesis produced exact-gap candidates that still require governance checks",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_synthesis_governance_repair_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_synthesis_governance_repair_ready", 145),
            "class": "route_c_gap_synthesis_governance_repair_ready",
            "why": "one or more Route C exact-gap governance checks failed and must be repaired before replay",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_synthesis_replay_ready":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_synthesis_replay_ready", 146),
            "class": "route_c_gap_synthesis_replay_ready",
            "why": "Route C hold synthesis produced governance-checked exact-gap candidates; the next value is Lean replay or ratification, not more prompt churn",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_synthesis_terminal_holds_recorded":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_synthesis_terminal_holds_recorded", 143),
            "class": "route_c_gap_synthesis_terminal_holds_recorded",
            "why": "Route C second-pass synthesis has no replayable exact-gap packets after duplicate and existing-theorem checks",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    elif competitive_inventory.get("status") == "route_c_gap_tasks_terminal_holds_recorded":
        recommendations.append({
            "priority": _recommendation_priority(payload, "route_c_gap_hold_synthesis_ready", 143),
            "class": "route_c_gap_hold_synthesis_ready",
            "why": "the Route C gap-task lane executed, but every proposal terminalized as a hold rather than a governed exact-gap/falsifier followup",
            "next_action": competitive_inventory.get("next_action"),
            "evidence": competitive_inventory,
        })
    if competitive_inventory.get("pr_a1_review_ready") and not competitive_inventory.get("pr_a1_public_review_published"):
        recommendations.append({
            "priority": _recommendation_priority(payload, "pr_a1_public_artifact_review_ready", 142),
            "class": "pr_a1_public_artifact_review_ready",
            "why": "PR_A1 has a compile plus L3 audit receipt, but the receipt only makes it review-ready and does not grant proof credit",
            "next_action": "send PR_A1 through the governed public-artifact review path while continuing mechanizable Route C task extraction",
            "evidence": competitive_inventory,
        })
    if target_resolution and target_resolution.get("risk_classes"):
        recommendations.append({
            "priority": _recommendation_priority(payload, "family_spec_target_resolution_debt", 146),
            "class": "family_spec_target_resolution_debt",
            "why": "family-spec probes have unresolved or missing concrete theorem target bindings; these can create false no-signal outcomes or probe the wrong theorem",
            "next_action": "hydrate every family-spec probe through the target-resolution contract; retry pre-patch conflicts with target-aware probe signatures; refuse unresolved multi-theorem rows",
            "evidence": target_resolution,
        })
    probe_seed_summary = _latest_c_supply_probe_seed_summary(c_supply_growth)
    source_materialization = _dict_field(payload, "c_supply_source_materialization")
    if (
        probe_seed_summary
        and int(probe_seed_summary.get("unresolved_row_count") or 0) > 0
        and int(c_credit_model.get("remaining_to_target") or 0) > 0
        and not _c_supply_source_materialization_satisfies(probe_seed_summary, source_materialization)
    ):
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_probe_source_materialization_debt", 142),
            "class": "c_supply_probe_source_materialization_debt",
            "why": "the C-supply probe seeder could not hydrate some selected family-spec rows into executable Lean source files",
            "next_action": "materialize exact row-id source files for the unresolved C-supply rows or drop them from the owed-probe selection; do not count structural rows as credit-ready until probe receipts exist",
            "evidence": {
                "probe_seed_summary": probe_seed_summary,
                "remaining_to_target": c_credit_model.get("remaining_to_target"),
            },
        })
    live_static_leakage = int((c_credit_model.get("blockers_by_reason") or {}).get("live_queue_without_static_strict_no_signal") or 0)
    if live_static_leakage:
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_live_queue_static_filter_leakage", 140),
            "class": "c_supply_live_queue_static_filter_leakage",
            "why": "some family-spec probe closures came from rows without strict static no-signal evidence, so they are excluded from C-supply credit",
            "next_action": "route C-supply growth through strict static-fail rows only; treat static-solvable probe closures as template/coverage evidence, not C-discriminating credit-ready rows",
            "evidence": {
                "blocked_live_queue_row_count": live_static_leakage,
                "credit_ready_count_after_filter": c_credit_model.get("credit_ready_count"),
                "remaining_to_target": c_credit_model.get("remaining_to_target"),
                "source_summaries": c_credit_model.get("source_summaries"),
            },
        })
    credit_ready = c_credit_model
    if credit_ready and int(credit_ready.get("remaining_to_target") or 0) > 0:
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_credit_ready_row_gap", 141),
            "class": "c_supply_credit_ready_row_gap",
            "why": "the active C-supply learning unit is below the credit-ready threshold required for the C-discriminating benchmark slice",
            "next_action": "increase credit-ready rows through strict static-fail mining, family-template repair, and verified positive/negative family-spec probes; do not count raw candidates or agent patches as credit-ready",
            "evidence": credit_ready,
        })
    breadth_policy = _dict_field(c_credit_model, "c_supply_breadth_policy")
    breadth_blockers = set(str(item) for item in (c_credit_model.get("breadth_blockers") or []) if str(item))
    if "family_breadth_target_not_met" in breadth_blockers or "single_family_concentration_warning" in breadth_blockers:
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_family_breadth_debt", 142),
            "class": "c_supply_family_breadth_debt",
            "why": "strict C-supply is too concentrated by repair family to support a overclaim-grade Path C claim",
            "next_action": "source and probe sibling rows across additional repair families; cap repeated-family interpretation to mechanism evidence until breadth targets are met by governed receipts",
            "evidence": {
                "breadth_metrics": c_credit_model.get("breadth_metrics"),
                "credit_ready_family_counts": c_credit_model.get("credit_ready_family_counts"),
                "breadth_policy": breadth_policy,
                "source_summaries": c_credit_model.get("source_summaries"),
            },
        })
    source_summaries = c_credit_model.get("source_summaries") if isinstance(c_credit_model.get("source_summaries"), list) else []
    max_source_demand_family_count = max(
        [int(summary.get("source_demand_family_count") or 0) for summary in source_summaries if isinstance(summary, dict)]
        or [0]
    )
    upstream_target = int(breadth_policy.get("target_upstream_source_demand_family_count") or 1)
    if (
        "source_file_breadth_target_not_met" in breadth_blockers
        or "source_root_breadth_target_not_met" in breadth_blockers
        or max_source_demand_family_count < upstream_target
    ):
        latest_demand_summary = _latest_c_supply_demand_summary(c_supply_growth)
        demand_corpora_written = int(latest_demand_summary.get("corpora_written_count") or 0) if isinstance(latest_demand_summary, dict) else 0
        demand_missing_source = int(latest_demand_summary.get("missing_source_file_candidate_count") or 0) if isinstance(latest_demand_summary, dict) else 0
        if demand_corpora_written > 0 and demand_missing_source == 0:
            source_next_action = "run bounded static-failure mining on the materialized demand corpora, then rerun C-slice prep; only rows with strict static no-signal and matched negative controls may advance to family-spec probes"
        elif demand_missing_source > 0:
            source_next_action = "materialize executable source files for demanded-family candidates before static mining; keep missing-source rows as source debt, not no-signal C supply"
        else:
            source_next_action = "widen source-demand mining before spending more proof probes on the same aperture: mine demanded families, materialize executable source rows, then let static/probe gates decide credit"
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_supply_source_breadth_debt", 142),
            "class": "c_supply_source_breadth_debt",
            "why": "strict C-supply lacks enough independent downstream source files or upstream source-demand family breadth",
            "next_action": source_next_action,
            "evidence": {
                "breadth_metrics": c_credit_model.get("breadth_metrics"),
                "credit_ready_source_file_counts": c_credit_model.get("credit_ready_source_file_counts"),
                "credit_ready_source_root_counts": c_credit_model.get("credit_ready_source_root_counts"),
                "max_source_demand_family_count": max_source_demand_family_count,
                "upstream_target": upstream_target,
                "latest_demand_summary": latest_demand_summary,
                "breadth_policy": breadth_policy,
                "source_summaries": source_summaries,
            },
        })
    if c_supply and c_selected < c_min:
        candidate_accounting = _dict_field(c_supply, "candidate_accounting")
        blockers = _dict_field(c_selection, "blockers_by_reason")
        template_backfill_pressure = int((blockers or {}).get("no_positive_family_template") or 0)
        candidate_rows = int(candidate_accounting.get("unique_supply_candidate_row_count") or c_cleaner.get("supply_candidate_row_count") or 0)
        c_next_action = (
            "run c_supply_template_backfill on strict static-fail candidates, then rerun bounded static-only mining; freeze only after family-template and negative-control evidence reaches threshold"
            if template_backfill_pressure and candidate_rows
            else "continue bounded static-only mining across family-specific corpora; freeze only after static-fail, family-template, negative-control evidence reaches threshold"
        )
        recommendations.append({
            "priority": _recommendation_priority(payload, "c_discriminating_supply_debt", 139),
            "class": "c_discriminating_supply_debt",
            "why": "C-discriminating benchmark supply has not reached the predeclared freeze threshold, so Path C cannot be tested without starving or laundering it",
            "next_action": c_next_action,
            "evidence": {
                "status": c_supply.get("status"),
                "run_id": c_supply.get("run_id"),
                "selected_count": c_selected,
                "min_freeze_rows": c_min,
                "eligible_count": c_selection.get("eligible_count"),
                "blockers_by_reason": c_selection.get("blockers_by_reason"),
                "source_demand_count": c_selection.get("source_demand_count") if c_selection.get("source_demand_count") is not None else len(c_selection.get("source_demand_requests") or []),
                "freeze": c_supply.get("freeze"),
                "read_model": "cleaned_full_universe" if c_clean_selection else "batch_status",
                "raw_checkpoint_record_count": c_cleaner.get("raw_checkpoint_record_count"),
                "cleaned_checkpoint_record_count": c_cleaner.get("cleaned_checkpoint_record_count"),
                "duplicate_checkpoint_record_count": c_cleaner.get("duplicate_checkpoint_record_count"),
                "raw_corpus_row_count": c_cleaner.get("raw_corpus_row_count"),
                "unique_corpus_row_count": c_cleaner.get("unique_corpus_row_count"),
                "duplicate_corpus_row_count": c_cleaner.get("duplicate_corpus_row_count"),
                "static_conflict_key_count": c_cleaner.get("static_conflict_key_count"),
                "positive_static_row_count": c_cleaner.get("positive_static_row_count"),
                "supply_candidate_row_count": c_cleaner.get("supply_candidate_row_count"),
                "unique_supply_candidate_row_count": candidate_accounting.get("unique_supply_candidate_row_count"),
                "template_backfill_pressure": template_backfill_pressure,
            },
        })
        family_birth_pressure = int((blockers or {}).get("no_positive_family_template") or 0) + int((blockers or {}).get("family_template_not_top_static_match") or 0)
        if family_birth_pressure > 0:
            recommendations.append({
                "priority": _recommendation_priority(payload, "new_family_supply_debt", 137),
                "class": "new_family_supply_debt",
                "why": "strict static-fail rows are blocked because no top-matching family template exists or existing templates attach to the wrong family boundary",
                "next_action": "mine ex-post static failures into governed family-birth candidates; do not grant benchmark credit until a born family has multi-row positive/negative controls and heldout or sibling evidence",
                "evidence": {
                    "selected_count": c_selected,
                    "min_freeze_rows": c_min,
                    "family_birth_pressure": family_birth_pressure,
                    "no_positive_family_template": (blockers or {}).get("no_positive_family_template"),
                    "family_template_not_top_static_match": (blockers or {}).get("family_template_not_top_static_match"),
                    "source_demand_count": c_selection.get("source_demand_count") if c_selection.get("source_demand_count") is not None else len(c_selection.get("source_demand_requests") or []),
                },
            })
    elif proof_lane.get("bottleneck_class") == "family_spec_probe_drain_limited":
        recommendations.append({
            "priority": _recommendation_priority(payload, "family_spec_probe_drain_limited", 118),
            "class": "family_spec_probe_drain_limited",
            "why": "diverse family-spec proof work is queued/running beyond current worker capacity",
            "next_action": "increase family-spec probe workers only while candidate_signature_diversity remains above the restart gate floor",
            "evidence": proof_lane,
        })
    elif proof_lane.get("bottleneck_class") == "source_binding_zero_value":
        recommendations.append({
            "priority": _recommendation_priority(payload, "source_binding_zero_value", 95),
            "class": "source_binding_zero_value",
            "why": "source-bound probes recently consumed proof execution but produced no governed value",
            "next_action": "route source binding to diagnostics/repair; keep family-spec probes as the primary value lane until source-bound templates improve",
            "evidence": proof_lane,
        })
    unmet = replenisher.get("unmet_after_replenish") or {}
    active_unmet = {str(k): int(v or 0) for k, v in unmet.items() if int(v or 0) > 0} if isinstance(unmet, dict) else {}
    candidate_pool = replenisher.get("candidate_pool") if isinstance(replenisher, dict) else {}
    usable_gate = family_spec_gate.get("usable") if isinstance(family_spec_gate, dict) else {}
    quarantine_count = int(family_spec_gate.get("quarantine_failure_count") or 0) if isinstance(family_spec_gate, dict) else 0
    starvation_reason = str((candidate_pool or {}).get("starvation_reason") or "")
    supply_quality = family_spec_gate.get("supply_quality_summary") if isinstance(family_spec_gate, dict) else {}
    supply_gap_counts = (supply_quality or {}).get("gap_counts") if isinstance(supply_quality, dict) else {}
    shallow_count = int((supply_gap_counts or {}).get("shallow_usable_supply") or 0)
    weak_surface_count = int((supply_gap_counts or {}).get("weak_residual_match_surface") or 0)
    probe_ready_general_count = int((supply_quality or {}).get("probe_ready_general_count") or 0) if isinstance(supply_quality, dict) else 0
    overclaim_summary = family_spec_gate.get("overclaim_disqualification_summary") if isinstance(family_spec_gate, dict) else {}
    overclaim_finding_count = int((overclaim_summary or {}).get("finding_count") or 0) if isinstance(overclaim_summary, dict) else 0
    mechanism_overclaim_report = _dict_field(payload, "mechanism_vs_overclaim_report")
    mechanism_overclaim_published = bool(
        mechanism_overclaim_report
        and str(mechanism_overclaim_report.get("status") or "") == "published_mechanism_vs_overclaim_boundary"
        and str(mechanism_overclaim_report.get("source_family_spec_gate_sha256") or "") == str(sha256_file(family_spec_gate.get("source_path") or DEFAULT_FAMILY_SPEC_GATE) or "")
    )
    if overclaim_finding_count > 0 and not mechanism_overclaim_published:
        recommendations.append({
            "priority": _recommendation_priority(payload, "mechanism_vs_overclaim_evidence_debt", 142),
            "class": "mechanism_vs_overclaim_evidence_debt",
            "why": "some family-spec positives are public/gold lemma wrappers; they may be valid mechanism/calibration evidence but must not be summarized as competitive overclaim evidence without prereg arm lift",
            "next_action": "report these rows separately, prioritize C-discriminating rows where public/static tools fail, and require benchmark uplift before making competitive claims",
            "evidence": {
                "overclaim_disqualification_summary": overclaim_summary,
                "gate_path": family_spec_gate.get("source_path") or DEFAULT_FAMILY_SPEC_GATE,
            },
        })
    if shallow_count or weak_surface_count:
        recommendations.append({
            "priority": _recommendation_priority(payload, "family_spec_generality_supply_debt", 138),
            "class": "family_spec_generality_supply_debt",
            "why": "usable family-spec supply exists, but some families remain shallow or weakly abstracted, so replay inventory can outrun reusable residual-family learning",
            "next_action": "generate heldout/sibling template patches for weak families and repair weak residual_match surfaces before raising probe worker count",
            "evidence": {
                "probe_ready_general_count": probe_ready_general_count,
                "class_counts": (supply_quality or {}).get("class_counts") if isinstance(supply_quality, dict) else {},
                "gap_counts": supply_gap_counts or {},
                "weakest_families": (supply_quality or {}).get("weakest_families") if isinstance(supply_quality, dict) else [],
            },
        })
    if quarantine_count > 0 and starvation_reason == "proof_candidate_pool_blocked_by_duplicate_probe_signatures":
        recommendations.append({
            "priority": _recommendation_priority(payload, "family_spec_quarantine_supply_debt", 136),
            "class": "family_spec_quarantine_supply_debt",
            "why": "family-spec refill is blocked by duplicate probe signatures while quarantined templates are reducing usable proof-row supply",
            "next_action": "drain family_spec_patch repair tasks until quarantined templates are fixed or typed-retired, then refill family-spec proof probes",
            "evidence": {
                "quarantine_failure_count": quarantine_count,
                "row_template_count": family_spec_gate.get("row_template_count"),
                "usable_row_template_count": usable_gate.get("row_template_count"),
                "candidate_pool": candidate_pool,
            },
        })
    if active_unmet:
        recommendations.append({
            "priority": _recommendation_priority(payload, "backlog_replenisher_floor_unmet", 128),
            "class": "backlog_replenisher_floor_unmet",
            "why": "the last automated refill finished with one or more policy floors still unsatisfied",
            "next_action": "fix the lane-specific seeding or cooldown cause shown in the replenisher receipt before increasing factory scale",
            "evidence": {
                "unmet_after_replenish": active_unmet,
                "floors": replenisher.get("floors"),
                "after": replenisher.get("after"),
                "candidate_pool": replenisher.get("candidate_pool"),
                "phase_failures": [
                    {
                        "phase": cmd.get("replenish_phase"),
                        "returncode": cmd.get("returncode"),
                        "stderr_tail": cmd.get("stderr_tail"),
                    }
                    for cmd in (replenisher.get("commands") or [])
                    if isinstance(cmd, dict) and int(cmd.get("returncode") or 0) != 0
                ],
            },
        })
    handoff = _dict_field(payload, "agentic_handoff_contract")
    if int(handoff.get("hard_leak_count") or 0) > 0:
        rec_class = str((handoff.get("policy") or {}).get("recommendation_class") or "agentic_handoff_contract_leakage")
        recommendations.append({
            "priority": _recommendation_priority(payload, rec_class, 155),
            "class": rec_class,
            "why": "terminal agentic generation outputs are missing visible downstream activation/integration receipts, so completed agent work can hide verification debt",
            "next_action": handoff.get("next_action"),
            "evidence": {
                "hard_leak_count": handoff.get("hard_leak_count"),
                "handoff_status_counts": handoff.get("handoff_status_counts"),
                "hard_leaks": (handoff.get("hard_leaks") or [])[:5],
                "credit_boundary": handoff.get("credit_boundary"),
            },
        })
    if str(family_spec_gate.get("status") or "") == "fail":
        recommendations.append({
            "priority": _recommendation_priority(payload, "family_spec_gate_failed", 132),
            "class": "family_spec_gate_failed",
            "why": "versioned repair-family specs are invalid, so family-spec proof-probe seeding can starve or skip candidate families",
            "next_action": "fix the family-spec schema/YAML failures before scaling proof probes; do not substitute source-bound work for broken family-spec inventory",
            "evidence": {
                "failure_count": family_spec_gate.get("failure_count"),
                "parse_failure_count": family_spec_gate.get("parse_failure_count"),
                "failures": (family_spec_gate.get("failures") or [])[:5],
            },
        })
    if int(version_health.get("stale_process_count") or 0):
        recommendations.append({
            "priority": _recommendation_priority(payload, "stale_worker_runtime_detected", 130),
            "class": "stale_worker_runtime_detected",
            "why": "workers are reporting processes older than the latest watched LeanMill source/spec/family file",
            "next_action": "restart stale LeanMill daemon sessions so all workers run the current queue, governance, and ingestion contracts",
            "evidence": {
                "stale_process_count": version_health.get("stale_process_count"),
                "stale_processes": (version_health.get("stale_processes") or [])[:5],
            },
        })
    if int(version_health.get("runtime_mismatch_count") or 0):
        recommendations.append({
            "priority": _recommendation_priority(payload, "worker_runtime_version_mismatch", 129),
            "class": "worker_runtime_version_mismatch",
            "why": "some workers report a different watched-source hash or git head than the current control process",
            "next_action": "restart mismatched LeanMill worker sessions before scaling learning-unit exits",
            "evidence": {
                "runtime_mismatch_count": version_health.get("runtime_mismatch_count"),
                "runtime_mismatches": (version_health.get("runtime_mismatches") or [])[:5],
            },
        })
    if promotion.get("seed_generalization_gap"):
        recommendations.append({
            "priority": _recommendation_priority(payload, "closure_to_template_generalization_gap", 140),
            "class": "closure_to_template_generalization_gap",
            "why": "governed seed-only closures need sibling/heldout generalization, but the heldout scout returned zero families",
            "next_action": "run heldout scout with seed families enabled and drain promotion worker into family_spec_patch or heldout_family_spec probes",
            "evidence": {
                "seed_generalization_needed_count": promotion.get("seed_generalization_needed_count"),
                "seed_generalization_needed_families": promotion.get("seed_generalization_needed_families"),
                "heldout_scout": promotion.get("heldout_scout"),
            },
        })
    if promotion.get("validated_family_blocked") and int(open_kind_counts.get("gm_operator_task") or 0) > 0:
        recommendations.append({
            "priority": _recommendation_priority(payload, "heldout_validation_work_ready", 110),
            "class": "heldout_validation_work_ready",
            "why": "candidate families are blocked on heldout evidence and bounded GM heldout-review tasks are queued",
            "next_action": "drain the queued heldout-review tasks into heldout attempt plans, tested retirements, or concrete blockers",
            "evidence": {
                "gm_operator_task_count": int(open_kind_counts.get("gm_operator_task") or 0),
                "heldout_receipt_events": promotion.get("heldout_receipt_events"),
                "validated_family_blocked": promotion.get("validated_family_blocked"),
            },
        })
    if losses["source_search_integrations"].get("ready_held_count", 0):
        priority = (
            _recommendation_priority(payload, "source_binding_conversion_gap_zero_value", 55)
            if source_probe_total and source_probe_value == 0
            else _recommendation_priority(payload, "source_binding_conversion_gap_positive", 100)
        )
        recommendations.append({
            "priority": priority,
            "class": "source_binding_conversion_gap",
            "why": "source-search produced canary-ready candidates but integration held them",
            "next_action": (
                "keep as a secondary repair lane; current source-bound probes have zero governed value, so prioritize heldout/family confirmation first"
                if source_probe_total and source_probe_value == 0 else
                "fix target-row selection and binding eligibility so ready source inventory creates bounded binding work"
            ),
            "evidence": losses["source_search_integrations"]["recent_ready_holds"][:3],
        })
    if queue.get("open_total", 0) == 0 and any((s.get("open_count") or 0) == 0 and (s.get("sla_breached") or False) for s in station.values()):
        recommendations.append({
            "priority": _recommendation_priority(payload, "idle_after_sla_breach", 90),
            "class": "idle_after_sla_breach",
            "why": "queue is drained while prior station lead times breached SLA",
            "next_action": "seed from concrete blocker classes instead of generic floors",
            "evidence": {k: v for k, v in station.items() if v.get("sla_breached")},
        })
    if (payload.get("observability") or {}).get("source_binding", {}).get("rejected_count", 0):
        recommendations.append({
            "priority": _recommendation_priority(payload, "source_binding_rejections", 85),
            "class": "source_binding_rejections",
            "why": "binding artifacts are failing deterministic ingestion",
            "next_action": "tighten binding artifact schema and add repair prompts keyed to rejection classes",
            "evidence": (payload.get("observability") or {}).get("source_binding", {}).get("failure_classes", {}),
        })
    for idx, cause in enumerate((payload.get("conversion_diagnostics") or {}).get("root_causes") or []):
        recommendations.append({
            "priority": max(
                _recommendation_priority(payload, "conversion_root_cause_floor", 60),
                _recommendation_priority(payload, "conversion_root_cause_base", 88) - idx,
            ),
            "class": f"conversion_{cause.get('class')}",
            "why": cause.get("interpretation"),
            "next_action": cause.get("next_action"),
            "evidence": cause,
        })
    if flow["probe_worker_done"] and not any(flow["scoreboard_tail_counts"].get(k, 0) for k in ("ratified_closure_count", "exact_gap_candidate_count", "valid_falsifier_count")):
        recommendations.append({
            "priority": _recommendation_priority(payload, "probe_yield_zero", 75),
            "class": "probe_yield_zero",
            "why": "proof probes completed without governed value exits in the inspected window",
            "next_action": "move from broad probe repetition to family-specific sibling/heldout construction",
            "evidence": flow["scoreboard_tail_counts"],
        })
    compile_candidates = int(flow["scoreboard_tail_counts"].get("compile_candidate_count") or 0)
    ratified = int(flow["scoreboard_tail_counts"].get("ratified_closure_count") or 0)
    if compile_candidates > ratified:
        recommendations.append({
            "priority": _recommendation_priority(payload, "compile_candidate_governance_gap", 92),
            "class": "compile_candidate_governance_gap",
            "why": "proof probes are producing compile-positive candidates that are not becoming governed proof-value exits",
            "next_action": "inspect governance receipts and classify each compile candidate as ratifiable, rejected, timeout, or duplicate before scaling the affected family",
            "evidence": {
                "compile_candidate_count": compile_candidates,
                "ratified_closure_count": ratified,
                "scoreboard_tail_counts": flow["scoreboard_tail_counts"],
                "tested_learning_exit_counts": flow.get("tested_learning_exit_counts", {}),
            },
        })
    for item in obs_bottlenecks:
        recommendations.append({
            "priority": _recommendation_priority(payload, "observability_bottleneck", 50),
            "class": f"observability_{item.get('class')}",
            "why": item.get("evidence"),
            "next_action": item.get("next_action"),
            "evidence": item,
        })
    if not recommendations:
        recommendations.append({
            "priority": _recommendation_priority(payload, "no_immediate_bottleneck_detected", 10),
            "class": "no_immediate_bottleneck_detected",
            "why": "no open queue and no inspected loss class dominated",
            "next_action": "refresh source/residual inventory and seed the next bounded WorkItems",
            "evidence": {},
        })
    return sorted(recommendations, key=lambda r: (-int(r["priority"]), str(r["class"])))


def _verdict(payload: dict[str, Any]) -> dict[str, Any]:
    version_health = payload.get("worker_version_health") or {}
    if int(version_health.get("stale_process_count") or 0) or int(version_health.get("runtime_mismatch_count") or 0):
        return {
            "status": "runtime_version_drift_requires_restart",
            "summary": "At least one worker process is stale or reports a different watched-source runtime version.",
            "governed_value_tail_count": 0,
            "governed_value_accounting": "blocked_until_worker_restart",
            "source_flow_tail_count": 0,
            "open_probe_work_count": 0,
            "open_source_work_count": 0,
            "no_laundering_guard": {
                "source_inventory_has_no_proof_credit": True,
                "agent_outputs_have_no_proof_credit": True,
                "governance_gate_is_only_ratifier": True,
            },
        }
    flow = payload["learning_unit_flow"]
    unique_value_exits = flow.get("unique_proof_value_exit_counts") or {}
    governed_value = sum(int(unique_value_exits.get(k, 0) or 0) for k in ("ratified_closure", "exact_gap_candidate", "valid_falsifier"))
    source_flow = flow["source_canary_ready_candidates"] + flow["source_to_canary_binding_enqueued"] + flow["source_binding_probe_enqueued"]
    open_kinds = payload.get("queue", {}).get("open_kind_counts") or {}
    open_probes = int(open_kinds.get("repair_canary_probe") or 0)
    open_source = int(open_kinds.get("source_search_task") or 0) + int(open_kinds.get("source_scout_task") or 0)
    if governed_value > 0:
        if open_probes > 0 and open_source == 0:
            status = "proof_lane_value_scaling_lean_slot_bound"
            sentence = "Governed value exits appeared and the open queue is proof-lane focused; current rate is bounded by Lean probe drain time."
        else:
            status = "learning_unit_value_scaling"
            sentence = "Governed value exits appeared in the inspected window."
    elif source_flow > 0:
        status = "operational_learning_flow_scaling_not_yet_value_scaling"
        sentence = "The factory is scaling source/proposal flow, but governed proof-value exits have not appeared in the inspected window."
    elif open_probes > 0 and open_source == 0:
        status = "proof_lane_running_no_new_value_yet"
        sentence = "The queue is proof-lane focused, but the inspected window has not yet produced a governed proof-value exit."
    else:
        status = "not_scaling_current_window"
        sentence = "The inspected window does not show new source-flow or governed proof-value scaling."
    return {
        "status": status,
        "summary": sentence,
        "governed_value_tail_count": governed_value,
        "governed_value_accounting": "unique_proof_value_exit_counts",
        "source_flow_tail_count": source_flow,
        "open_probe_work_count": open_probes,
        "open_source_work_count": open_source,
        "no_laundering_guard": {
            "source_inventory_has_no_proof_credit": True,
            "agent_outputs_have_no_proof_credit": True,
            "governance_gate_is_only_ratifier": True,
        },
    }


def _write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    meta_loop = (
        payload.get("intelligence_policy", {}).get("active_meta_reasoning_loop", {})
        if isinstance(payload.get("intelligence_policy"), dict)
        else {}
    )
    lines = [
        "# LeanMill Factory Intelligence",
        "",
        f"- generated_at_epoch: `{payload['generated_at_epoch']}`",
        f"- verdict: `{payload['verdict']['status']}`",
        f"- verdict_summary: {payload['verdict']['summary']}",
        f"- queue_open_total: `{payload['queue']['open_total']}`",
        f"- inspected_window_s: `{payload['learning_unit_flow']['window_s']}`",
        "",
    ]
    if meta_loop:
        lines.extend([
            "## Active Meta-Reasoning",
            "",
            f"- schema: `{meta_loop.get('schema')}`",
            f"- rule: {meta_loop.get('rule')}",
            f"- credit_boundary: {meta_loop.get('credit_boundary')}",
            f"- gaming_guard: {meta_loop.get('gaming_guard')}",
            "",
        ])
    cct = payload.get("campaign_cycle_time") or {}
    if isinstance(cct, dict) and cct.get("campaigns"):
        lines.extend(["## Campaign Cycle-Time (time to closure)", ""])
        for dom in sorted(cct.get("by_domain") or {}):
            d = (cct["by_domain"])[dom]
            lines.append(f"- domain `{dom}`: avg time-to-closure `{d.get('avg_time_to_closure_s')}s` "
                         f"over `{d.get('closures')}` closure(s) across `{d.get('campaigns')}` campaign(s)")
        lines.extend([
            "",
            "| campaign | domain | closures | first TTC (s) | mean TTC (s) | p95 TTC (s) | first cost-to-close (s) | span (s) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for rt in sorted(cct["campaigns"]):
            c = cct["campaigns"][rt]
            ttc = c.get("time_to_closure_s") or {}
            ctc = c.get("cost_to_closure_s") or {}
            lines.append(f"| `{rt}` | {c.get('domain')} | {c.get('closures')} | {ttc.get('first')} | "
                         f"{ttc.get('mean')} | {ttc.get('p95')} | {ctc.get('first')} | {c.get('span_s')} |")
        lines.append("")
    lines.extend([
        "## Learning-Unit Flow",
        "",
        f"- source_canary_ready_candidates: `{payload['learning_unit_flow']['source_canary_ready_candidates']}`",
        f"- source_search_holds_with_ready_candidates: `{payload['learning_unit_flow']['source_search_holds_with_ready_candidates']}`",
        f"- source_to_canary_binding_enqueued: `{payload['learning_unit_flow']['source_to_canary_binding_enqueued']}`",
        f"- source_binding_probe_enqueued: `{payload['learning_unit_flow']['source_binding_probe_enqueued']}`",
        f"- probe_worker_done: `{payload['learning_unit_flow']['probe_worker_done']}`",
        f"- scoreboard_tail_counts: `{payload['learning_unit_flow']['scoreboard_tail_counts']}`",
        f"- unique_probe_signature_scoreboard_counts: `{payload['learning_unit_flow'].get('unique_probe_signature_scoreboard_counts', {})}`",
        f"- learning_unit_exit_counts: `{payload['learning_unit_flow'].get('learning_unit_exit_counts', {})}`",
        f"- proof_value_exit_counts: `{payload['learning_unit_flow'].get('proof_value_exit_counts', {})}`",
        f"- unique_proof_value_exit_counts: `{payload['learning_unit_flow'].get('unique_proof_value_exit_counts', {})}`",
        f"- tested_learning_exit_counts: `{payload['learning_unit_flow'].get('tested_learning_exit_counts', {})}`",
        f"- unique_tested_learning_exit_counts: `{payload['learning_unit_flow'].get('unique_tested_learning_exit_counts', {})}`",
        f"- terminal_decision_counts: `{payload['learning_unit_flow'].get('terminal_decision_counts', {})}`",
        f"- unique_terminal_decision_counts: `{payload['learning_unit_flow'].get('unique_terminal_decision_counts', {})}`",
        f"- intermediate_flow_counts: `{payload['learning_unit_flow'].get('intermediate_flow_counts', {})}`",
        f"- ops_exit_counts: `{payload['learning_unit_flow'].get('ops_exit_counts', {})}`",
        f"- no_laundering_accounting_note: {payload['learning_unit_flow'].get('no_laundering_accounting_note')}",
        "",
        "## Learning Feedback",
        "",
        f"- feedback_record_count: `{payload.get('learning_feedback_read_model', {}).get('feedback_record_count')}`",
        f"- feedback_exit_counts: `{payload.get('learning_feedback_read_model', {}).get('exit_counts', {})}`",
        f"- feedback_review_required_count: `{payload.get('learning_feedback_read_model', {}).get('review_required_count')}`",
        f"- feedback_contract_note: {payload.get('learning_feedback_read_model', {}).get('contract_note')}",
        "",
        "## Run Observability",
        "",
        f"- run_tag: `{payload.get('run_observability', {}).get('run_tag', '')}`",
        f"- operator_status: `{payload.get('run_observability', {}).get('operator_readout', {}).get('status', '')}`",
        f"- primary_bottleneck: `{payload.get('run_observability', {}).get('operator_readout', {}).get('primary_bottleneck', '')}`",
        f"- next_action: {payload.get('run_observability', {}).get('operator_readout', {}).get('next_action', '')}",
        f"- warnings: `{payload.get('run_observability', {}).get('warnings', [])}`",
        f"- axiom_packs: `{payload.get('run_observability', {}).get('axiom_packs', {})}`",
        "",
        "## Proof-Lane RCA",
        "",
        f"- bottleneck_class: `{payload.get('proof_lane_rca', {}).get('bottleneck_class')}`",
        f"- blockers: `{payload.get('proof_lane_rca', {}).get('blockers', [])}`",
        f"- family_spec_candidate_signature_diversity: `{payload.get('proof_lane_rca', {}).get('family_spec_candidate_signature_diversity')}`",
        f"- lane_outcomes: `{payload.get('proof_lane_rca', {}).get('lane_outcomes', {})}`",
        f"- lane_open: `{payload.get('proof_lane_rca', {}).get('lane_open', {})}`",
        f"- scale_readiness: `{payload.get('proof_lane_rca', {}).get('scale_readiness', {})}`",
        "",
        "## Heavy Lean Process Pressure",
        "",
        f"- risk_classes: `{payload.get('heavy_lean_process_pressure', {}).get('risk_classes', [])}`",
        f"- drain_process_count: `{payload.get('heavy_lean_process_pressure', {}).get('drain_process_count')}`",
        f"- repl_process_count: `{payload.get('heavy_lean_process_pressure', {}).get('repl_process_count')}`",
        f"- repl_group_count: `{payload.get('heavy_lean_process_pressure', {}).get('repl_group_count')}`",
        f"- external_lean_process_count: `{payload.get('heavy_lean_process_pressure', {}).get('external_lean_process_count')}`",
        "",
        "## Conversion Diagnostics",
        "",
        f"- stage_outcome_counts: `{payload.get('conversion_diagnostics', {}).get('stage_outcome_counts', {})}`",
        f"- source_query_gate_failures: `{payload.get('conversion_diagnostics', {}).get('source_query_gate_failures', {}).get('failure_classes', {})}`",
        f"- source_binding_failure_classes: `{payload.get('conversion_diagnostics', {}).get('source_binding_failure_classes', {})}`",
        "",
        "## C-Discriminating Supply",
        "",
        f"- status: `{payload.get('c_supply_batch', {}).get('status')}`",
        f"- selection: `{payload.get('c_supply_batch', {}).get('selection', {})}`",
        f"- freeze: `{payload.get('c_supply_batch', {}).get('freeze')}`",
        f"- credit_ready_read_model: `{payload.get('c_supply_credit_ready_read_model', {})}`",
        f"- growth_probe_seed_summary: `{_latest_c_supply_probe_seed_summary(payload.get('c_supply_growth', {}) if isinstance(payload.get('c_supply_growth'), dict) else {})}`",
        f"- source_materialization: `{payload.get('c_supply_source_materialization', {})}`",
        f"- target_resolution_read_model: `{payload.get('target_resolution_read_model', {})}`",
        "",
        "## Evaluation Harness",
        "",
        f"- status: `{payload.get('evaluation_harness_read_model', {}).get('status')}`",
        f"- selected_row_count: `{payload.get('evaluation_harness_read_model', {}).get('selected_row_count')}`",
        f"- run_selected_row_count: `{payload.get('evaluation_harness_read_model', {}).get('run_selected_row_count')}`",
        f"- run_completed_row_count: `{payload.get('evaluation_harness_read_model', {}).get('run_completed_row_count')}`",
        f"- residual_memory_observability: `{payload.get('evaluation_harness_read_model', {}).get('residual_memory_observability_status')}`",
        f"- masked_family_candidate_record_count: `{payload.get('evaluation_harness_read_model', {}).get('masked_family_candidate_record_count')}`",
        f"- benchmark_lift: `{payload.get('evaluation_harness_read_model', {}).get('has_benchmark_lift')}`",
        f"- benchmark_lift_comparison: `{payload.get('evaluation_harness_read_model', {}).get('benchmark_lift_comparison', {})}`",
        f"- no_lift_publication: `{payload.get('evaluation_harness_read_model', {}).get('no_lift_publication', {})}`",
        f"- benchmark_can_run_full: `{payload.get('evaluation_harness_read_model', {}).get('benchmark_can_run_full')}`",
        f"- selected_target_resolution: `{payload.get('evaluation_harness_read_model', {}).get('selected_target_resolution_status')}`",
        f"- full_pool_target_unresolved_row_count: `{payload.get('evaluation_harness_read_model', {}).get('full_pool_target_unresolved_row_count')}`",
        f"- source_materialization_counts: `{payload.get('evaluation_harness_read_model', {}).get('source_materialization_counts', {})}`",
        f"- next_action: {payload.get('evaluation_harness_read_model', {}).get('next_action')}",
        "",
        "## Competitive Inventory",
        "",
        f"- status: `{payload.get('competitive_inventory_read_model', {}).get('status')}`",
        f"- route_c_gap_report_count: `{payload.get('competitive_inventory_read_model', {}).get('route_c_gap_report_count')}`",
        f"- route_c_compiled_or_closed_count: `{payload.get('competitive_inventory_read_model', {}).get('route_c_compiled_or_closed_count')}`",
        f"- route_c_gap_task_count: `{payload.get('competitive_inventory_read_model', {}).get('route_c_gap_task_count')}`",
        f"- route_c_gap_tasks_enqueued: `{payload.get('competitive_inventory_read_model', {}).get('route_c_gap_tasks_enqueued')}`",
        f"- ztare_lean_file_count: `{payload.get('competitive_inventory_read_model', {}).get('ztare_lean_file_count')}`",
        f"- ztare_files_with_sorry_or_admit_count: `{payload.get('competitive_inventory_read_model', {}).get('ztare_files_with_sorry_or_admit_count')}`",
        f"- semantic_retrieval_wiring_status: `{payload.get('competitive_inventory_read_model', {}).get('semantic_retrieval_wiring_status')}`",
        f"- pr_a1_status: `{payload.get('competitive_inventory_read_model', {}).get('pr_a1_status')}`",
        f"- pr_a1_public_review: `{payload.get('competitive_inventory_read_model', {}).get('pr_a1_public_review', {})}`",
        f"- next_action: {payload.get('competitive_inventory_read_model', {}).get('next_action')}",
    ])
    for cause in (payload.get("conversion_diagnostics") or {}).get("root_causes") or []:
        lines.append(f"- `{cause.get('class')}` count={cause.get('count')}: {cause.get('next_action')}")
    usage = payload.get("subscription_agent_usage") or {}
    exec_modes = _dict_field(payload, "execution_mode_read_model")
    if exec_modes:
        lines.extend([
            "",
            "## Execution Modes",
            "",
            f"- policy_profile: `{exec_modes.get('policy_profile')}` source_binding_mode: `{exec_modes.get('source_binding_mode')}`",
            f"- declared_models: `{exec_modes.get('declared_models', {})}`",
            f"- declared_budgets: `{exec_modes.get('declared_budgets', {})}`",
            f"- intended_worker_counts_by_mode: `{exec_modes.get('intended_worker_counts_by_mode', {})}`",
            f"- observed_active_workers_by_mode: `{exec_modes.get('observed_active_workers_by_mode', {})}`",
            f"- observed_open_work_by_mode: `{exec_modes.get('observed_open_work_by_mode', {})}`",
            f"- subscription_agent_usage: `{exec_modes.get('subscription_agent_usage', {})}`",
            f"- budget_gap_classes: `{exec_modes.get('budget_gap_classes', [])}`",
            f"- gap_classes: `{exec_modes.get('gap_classes', [])}`",
            f"- credit_boundary: `{exec_modes.get('credit_boundary')}`",
        ])
    handoff = _dict_field(payload, "agentic_handoff_contract")
    if handoff:
        lines.extend([
            "",
            "## Agentic Handoff Contract",
            "",
            f"- status: `{handoff.get('status')}`",
            f"- hard_leak_count: `{handoff.get('hard_leak_count')}`",
            f"- pending_handoff_count: `{handoff.get('pending_handoff_count')}`",
            f"- verified_handoff_count: `{handoff.get('verified_handoff_count')}`",
            f"- handoff_status_counts: `{handoff.get('handoff_status_counts', {})}`",
            f"- source_search_status_counts: `{handoff.get('source_search_status_counts', {})}`",
            f"- next_action: {handoff.get('next_action')}",
            f"- credit_boundary: `{handoff.get('credit_boundary')}`",
        ])
    lines.extend([
        "",
        "## Subscription Agent Usage",
        "",
        f"- open_count: `{usage.get('open_count')}`",
        f"- open_by_kind: `{usage.get('open_by_kind', {})}`",
        f"- open_by_worker: `{usage.get('open_by_worker', {})}`",
        f"- launched_count: `{usage.get('launched_count')}`",
        f"- estimated_total_tokens: `{usage.get('estimated_total_tokens')}`",
        f"- wall_time_s: `{usage.get('wall_time_s')}`",
        f"- by_runtime: `{usage.get('by_runtime', {})}`",
        f"- by_task_kind: `{usage.get('by_task_kind', {})}`",
        f"- missing_usage_terminal_count: `{usage.get('missing_usage_terminal_count')}`",
        f"- accounting_note: {usage.get('accounting_note')}",
    ])
    lines.extend([
        "",
        "## Family Promotion",
        "",
        f"- status_counts: `{payload.get('family_promotion_diagnostics', {}).get('status_counts', {})}`",
        f"- heldout_receipt_events: `{payload.get('family_promotion_diagnostics', {}).get('heldout_receipt_events')}`",
        f"- validated_family_blocked: `{payload.get('family_promotion_diagnostics', {}).get('validated_family_blocked')}`",
        f"- seed_generalization_gap: `{payload.get('family_promotion_diagnostics', {}).get('seed_generalization_gap')}`",
        f"- seed_generalization_needed_count: `{payload.get('family_promotion_diagnostics', {}).get('seed_generalization_needed_count')}`",
        f"- heldout_scout: `{payload.get('family_promotion_diagnostics', {}).get('heldout_scout', {})}`",
        f"- interpretation: {payload.get('family_promotion_diagnostics', {}).get('interpretation')}",
        "",
    ])
    _msy = payload.get("move_space_yield", {})
    _msy_h = _msy.get("headline", {}) if isinstance(_msy, dict) else {}
    if _msy_h:
        lines.extend([
            "## Move-Space Yield (are we using the move space we built?)",
            "",
            f"- native+warm attempt-share: `{_msy_h.get('native_warm_attempt_share')}`  "
            f"(closers: `{_msy_h.get('closers')}`, only_warm_closes: `{_msy_h.get('only_warm_closes')}`)",
            f"- dormant moves (never reached): `{_msy_h.get('dormant_moves')}`",
            f"- reached moves: `{_msy_h.get('reached_moves')}`",
        ])
        for _mv, _m in sorted((_msy.get("by_move") or {}).items(),
                              key=lambda x: -x[1].get("attempts", 0)):
            lines.append(
                f"  - `{_mv}`: attempts={_m.get('attempts')} ratified={_m.get('ratified_closes')} "
                f"close_rate={_m.get('close_rate')} non_close_success={_m.get('non_close_success')} "
                f"mean_s={_m.get('mean_wallclock_s')}")
        lines.append("")
    lines.extend([
        "## Top Actions",
        "",
    ])
    for rec in payload["recommendations"][:8]:
        lines.append(f"- P{rec['priority']} `{rec['class']}`: {rec['next_action']}")
    lines.extend(["", "## Station Lead/Cycle Times", ""])
    for station, data in payload["subprocess_metrics"]["by_station"].items():
        lead = data["lead_time_to_terminal_s"]
        cycle = data["active_cycle_time_s"]
        lines.append(
            f"- `{station}` open={data['open_count']} recent_terminal={data['terminal_recent_count']} "
            f"lead_p95={lead['p95']}s cycle_p95={cycle['p95']}s sla={data['sla_p95_s']}s breach={data['sla_breached']}"
        )
    lines.extend([
        "",
        "## Worker Version Health",
        "",
        f"- stale_process_count: `{payload.get('worker_version_health', {}).get('stale_process_count')}`",
        f"- stale_heartbeat_count: `{payload.get('worker_version_health', {}).get('stale_heartbeat_count')}`",
        f"- runtime_mismatch_count: `{payload.get('worker_version_health', {}).get('runtime_mismatch_count')}`",
        f"- git_heads: `{payload.get('worker_version_health', {}).get('git_heads', {})}`",
        f"- watched_source_hashes: `{payload.get('worker_version_health', {}).get('watched_source_hashes', {})}`",
    ])
    for rec in (payload.get("worker_version_health", {}).get("stale_processes") or [])[:8]:
        lines.append(
            f"- stale `{rec.get('worker_id')}` age={rec.get('heartbeat_age_s')}s "
            f"started={rec.get('process_started_at')} source_mtime={rec.get('watched_source_mtime_max')} "
            f"work={rec.get('claimed_work_id')}"
        )
    lines.extend(["", "## Loss Accounting", ""])
    integration = payload["loss_accounting"]["source_search_integrations"]
    lines.append(f"- source_search_ready_holds: `{integration.get('ready_held_count')}` blockers=`{integration.get('blockers')}`")
    binding = (payload.get("observability") or {}).get("source_binding") or {}
    lines.append(f"- source_binding_rejections: `{binding.get('rejected_count', 0)}` classes=`{binding.get('failure_classes', {})}`")
    spec_gate = payload.get("family_spec_gate") or {}
    lines.append(
        f"- family_spec_gate: status=`{spec_gate.get('status')}` "
        f"failures=`{spec_gate.get('failure_count')}` parse_failures=`{spec_gate.get('parse_failure_count')}`"
    )
    sq = spec_gate.get("supply_quality_summary") or {}
    lines.append(
        f"- family_spec_supply_quality: classes=`{sq.get('class_counts', {})}` "
        f"gaps=`{sq.get('gap_counts', {})}` median_score=`{sq.get('median_generality_score')}`"
    )
    overclaim = spec_gate.get("overclaim_disqualification_summary") or {}
    lines.append(
        f"- mechanism_vs_overclaim: disqualified_positive_templates=`{overclaim.get('finding_count', 0)}` "
        f"families=`{overclaim.get('family_count', 0)}` note=`{overclaim.get('interpretation', '')}`"
    )
    mechanism_overclaim_report = payload.get("mechanism_vs_overclaim_report") or {}
    lines.append(
        f"- mechanism_vs_overclaim_report: status=`{mechanism_overclaim_report.get('status')}` "
        f"gate_sha=`{mechanism_overclaim_report.get('source_family_spec_gate_sha256')}`"
    )
    replenisher = payload.get("backlog_replenisher") or {}
    lines.append(
        f"- backlog_replenisher_unmet: `{replenisher.get('unmet_after_replenish', {})}` "
        f"starvation_reason=`{(replenisher.get('candidate_pool') or {}).get('starvation_reason')}`"
    )
    c_clean = _dict_field(payload, "c_supply_clean_selection")
    c_cleaner = _dict_field(payload, "c_supply_expost_cleaner")
    population = _dict_field(payload, "population_elo")
    upstream_rater = _dict_field(payload, "c_supply_upstream_rater")
    if upstream_rater:
        lines.extend([
            "",
            "## Upstream Routing Rater",
            "",
            f"- mode: `{upstream_rater.get('mode')}` model: `{upstream_rater.get('model')}` candidates: `{upstream_rater.get('candidate_count')}` validation: `{upstream_rater.get('model_validation', {})}`",
            f"- brier_scored_now: `{upstream_rater.get('n_brier_scored_now')}` mean_brier_useful_exit_now: `{upstream_rater.get('mean_brier_useful_exit_now')}` calibration_gap: `{upstream_rater.get('calibration_gap_mean_pred_minus_outcome_now')}`",
            f"- joined_routing_outcomes: `{upstream_rater.get('joined_routing_outcomes', [])[:5]}`",
            f"- calibration_note: `{upstream_rater.get('calibration_note')}`",
        ])
    if population:
        lines.extend([
            "",
            "## Population Routing",
            "",
            f"- records: `{population.get('record_count')}` rows: `{population.get('row_count')}` contestants: `{population.get('contestant_count')}` events: `{population.get('event_count')}`",
            f"- contestant_scope_counts: `{population.get('contestant_scope_counts', {})}`",
            f"- top_routing_priorities: `{population.get('top_routing_priorities', [])[:5]}`",
            f"- non_laundering_note: `{population.get('non_laundering_note')}`",
        ])
    yield_decomp = _dict_field(payload, "strict_c_yield_decomposition")
    if yield_decomp:
        readiness = _dict_field(yield_decomp, "predictive_model_readiness")
        lines.extend([
            "",
            "## Strict C Yield",
            "",
            f"- formula: `{yield_decomp.get('formula')}`",
            f"- observed_strict_c_rate_per_hour: `{yield_decomp.get('observed_strict_c_rate_per_hour')}` modeled_strict_c_rate_per_hour: `{yield_decomp.get('modeled_strict_c_rate_per_hour')}`",
            f"- current_bottleneck: `{yield_decomp.get('current_bottleneck')}`",
            f"- next_lever: {yield_decomp.get('next_lever')}",
            f"- feature_vector: `{yield_decomp.get('feature_vector', {})}`",
            f"- predictive_model_readiness: `{readiness}`",
            f"- credit_boundary: `{yield_decomp.get('credit_boundary')}`",
        ])
    if c_clean or c_cleaner:
        lines.extend([
            "",
            "## C-Supply Clean Read Model",
            "",
            f"- selected_count: `{c_clean.get('selected_count')}` eligible_count: `{c_clean.get('eligible_count')}` status: `{c_clean.get('status')}`",
            f"- blockers_by_reason: `{c_clean.get('blockers_by_reason', {})}`",
            f"- raw_checkpoint_records: `{c_cleaner.get('raw_checkpoint_record_count')}` cleaned_checkpoint_records: `{c_cleaner.get('cleaned_checkpoint_record_count')}` duplicate_checkpoint_records: `{c_cleaner.get('duplicate_checkpoint_record_count')}`",
            f"- raw_corpus_rows: `{c_cleaner.get('raw_corpus_row_count')}` unique_corpus_rows: `{c_cleaner.get('unique_corpus_row_count')}` duplicate_corpus_rows: `{c_cleaner.get('duplicate_corpus_row_count')}`",
            f"- static_conflict_keys: `{c_cleaner.get('static_conflict_key_count')}` positive_static_rows: `{c_cleaner.get('positive_static_row_count')}` supply_candidate_rows: `{c_cleaner.get('supply_candidate_row_count')}`",
            f"- static_unknown_row_count: `{c_clean.get('static_unknown_row_count')}` static_unknown_family_counts: `{c_clean.get('static_unknown_family_counts', {})}`",
        ])
    typed = _dict_field(payload, "typed_proof_exit_read_model")
    typed_summary = _dict_field(typed, "summary")
    if typed_summary.get("exit_count"):
        lines.extend([
            "",
            "## Typed Proof Exits",
            "",
            f"- exit_count: `{typed_summary.get('exit_count')}`",
            f"- source_kind_counts: `{typed_summary.get('source_kind_counts', {})}`",
            f"- typed_exit_kind_counts: `{typed_summary.get('typed_exit_kind_counts', {})}`",
            f"- residual_class_counts: `{typed_summary.get('residual_class_counts', {})}`",
            f"- proof_compiler_contract: `{typed_summary.get('proof_compiler_contract', {})}`",
            f"- credit_boundary: `{typed_summary.get('credit_boundary')}`",
        ])
    write_text_atomic(path, "\n".join(lines) + "\n")


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = _queue_rows(cx)
    events = _read_events(args.events, limit=args.event_tail)
    observability = _read_json(args.observability)
    station_health = _read_json(args.station_health)
    contract = _read_json(args.contract)
    registry = _read_json(args.repair_registry)
    heldout_scout = _read_json(args.heldout_scout)
    family_spec_gate = _read_json(args.family_spec_gate)
    backlog_replenisher = _read_json(args.backlog_replenisher)
    c_supply_batch = _read_json(args.c_supply_batch_status)
    c_supply_expost_cleaner = _read_json(args.c_supply_expost_cleaner)
    c_supply_growth = _read_json(args.c_supply_growth_status)
    agentic_portfolio_raw = _read_json(args.agentic_portfolio)
    c_supply_source_materialization_raw = _read_json(args.c_supply_source_materialization)
    c_supply_upstream_rater_raw = _read_json(args.c_supply_upstream_rater)
    typed_proof_exits_raw = _read_json(args.typed_proof_exits)
    population_elo_raw = _read_json(args.population_elo)
    evaluation_harness_prep_raw = _read_json(args.evaluation_harness_prep)
    evaluation_harness_run_raw = _read_json(args.evaluation_harness_run)
    evaluation_no_lift_report_raw = _read_json(args.evaluation_no_lift_report)
    mechanism_vs_overclaim_report_raw = _read_json(args.mechanism_vs_overclaim_report)
    competitive_inventory_raw = _read_json(args.competitive_inventory)
    pr_a1_public_review_raw = _read_json(args.pr_a1_public_review)
    c_supply_clean_selection_raw = _read_json(args.c_supply_clean_selection)
    c_supply_clean_selection = _c_supply_selection_summary(
        c_supply_clean_selection_raw if isinstance(c_supply_clean_selection_raw, dict) else {},
        source_path=args.c_supply_clean_selection,
    )
    factory_policy = _read_json(args.factory_policy)
    intelligence_policy = _policy_intelligence(factory_policy if isinstance(factory_policy, dict) else {})
    queue_stats = work_queue.stats(cx)
    open_stats = work_queue.open_stats(cx)
    artifact_registry = _artifact_registry_read_model(
        cx,
        expected_canonical_paths={
            "c_supply_batch_status": args.c_supply_batch_status,
            "c_supply_batch_selection": DEFAULT_C_SUPPLY_BATCH_STATUS.replace("c_supply_batch_status.json", "c_supply_batch_c_discriminating_slice.json"),
            "factory_intelligence": args.out,
        },
    )
    queue = {
        "total": queue_stats.get("total", 0),
        "open_total": open_stats.get("total", 0),
        "status_counts": queue_stats.get("by_status") or {},
        "kind_counts": queue_stats.get("by_kind") or {},
        "open_status_counts": open_stats.get("by_status") or {},
        "open_kind_counts": open_stats.get("by_kind") or {},
    }
    payload: dict[str, Any] = {
        "schema": "leanmill-factory-intelligence-v1",
        "generated_at_epoch": _now(),
        "source_protocols": {
            "inspired_by": [
                "cognitive-firm OperatingUnit dashboard",
                "cognitive-firm ActionImpactRecordView",
                "OpenTelemetry-style projection boundary",
            ],
            "canonical_truth": "LeanMill SQLite WorkItem queue plus append-only event ledger plus artifact_refs role registry",
        },
        "artifact_registry": artifact_registry,
        "queue": queue,
        "station_contract_kpis": (contract or {}).get("kpis", {}),
        "current_bottleneck": (contract or {}).get("current_bottleneck"),
        "contract_recommended_next_action": (contract or {}).get("recommended_next_action"),
        "intelligence_policy": intelligence_policy,
        "subprocess_metrics": _build_subprocess_metrics(rows, events, trailing_window_s=args.window_s),
        "phase_timing": _phase_timing_read_model(),
        "campaign_cycle_time": _campaign_cycle_time_read_model(),
        "denotation_rollup": denotation_rollup(),
        "learning_unit_flow": _learning_unit_flow(rows, events, trailing_window_s=args.window_s),
        "learning_feedback_read_model": _learning_feedback_read_model(rows, trailing_window_s=args.window_s),
        "target_resolution_read_model": _target_resolution_read_model(rows),
        "subscription_agent_usage": _subscription_agent_usage(rows, trailing_window_s=args.window_s),
        "heavy_lean_process_pressure": _heavy_lean_process_pressure(intelligence_policy),
        "worker_version_health": work_queue.worker_version_health(
            cx,
            stale_after_s=args.worker_heartbeat_stale_s,
            policy_profile=args.policy_profile,
        ),
        "loss_accounting": {
            "source_search_integrations": _integration_loss_summary(args.source_search_integrations, max_files=args.integration_receipt_limit),
        },
        "observability": observability if isinstance(observability, dict) else {},
        "station_health": station_health if isinstance(station_health, dict) else {},
        "family_spec_gate": family_spec_gate if isinstance(family_spec_gate, dict) else {},
        "mechanism_vs_overclaim_report": mechanism_vs_overclaim_report_raw if isinstance(mechanism_vs_overclaim_report_raw, dict) else {},
        "pr_a1_public_review_report": pr_a1_public_review_raw if isinstance(pr_a1_public_review_raw, dict) else {},
        "backlog_replenisher": backlog_replenisher if isinstance(backlog_replenisher, dict) else {},
        "c_supply_batch": c_supply_batch if isinstance(c_supply_batch, dict) else {},
        "c_supply_expost_cleaner": c_supply_expost_cleaner if isinstance(c_supply_expost_cleaner, dict) else {},
        "c_supply_clean_selection": c_supply_clean_selection if isinstance(c_supply_clean_selection, dict) else {},
        "c_supply_growth": c_supply_growth if isinstance(c_supply_growth, dict) else {},
        "agentic_portfolio_read_model": _agentic_portfolio_read_model(
            agentic_portfolio_raw if isinstance(agentic_portfolio_raw, dict) else {},
            path=args.agentic_portfolio,
        ),
        "c_supply_source_materialization": _c_supply_source_materialization_read_model(
            c_supply_source_materialization_raw if isinstance(c_supply_source_materialization_raw, dict) else {}
        ),
        "typed_proof_exit_read_model": _typed_proof_exit_read_model(
            typed_proof_exits_raw if isinstance(typed_proof_exits_raw, dict) else {}
        ),
        "evaluation_harness_read_model": _evaluation_harness_read_model(
            evaluation_harness_prep_raw if isinstance(evaluation_harness_prep_raw, dict) else {},
            evaluation_harness_run_raw if isinstance(evaluation_harness_run_raw, dict) else {},
            prep_path=args.evaluation_harness_prep,
            run_path=args.evaluation_harness_run,
            no_lift_report=evaluation_no_lift_report_raw if isinstance(evaluation_no_lift_report_raw, dict) else {},
            no_lift_report_path=args.evaluation_no_lift_report,
        ),
        "competitive_inventory_read_model": _competitive_inventory_read_model(
            competitive_inventory_raw if isinstance(competitive_inventory_raw, dict) else {},
            path=args.competitive_inventory,
            pr_a1_public_review=pr_a1_public_review_raw if isinstance(pr_a1_public_review_raw, dict) else {},
            pr_a1_public_review_path=args.pr_a1_public_review,
        ),
        "c_supply_credit_ready_read_model": _c_supply_credit_ready_read_model(
            c_supply_batch=c_supply_batch if isinstance(c_supply_batch, dict) else {},
            c_supply_clean_selection=c_supply_clean_selection if isinstance(c_supply_clean_selection, dict) else {},
            c_supply_growth=c_supply_growth if isinstance(c_supply_growth, dict) else {},
            factory_policy=factory_policy if isinstance(factory_policy, dict) else {},
            live_queue_credit_summary=_live_queue_c_supply_credit_summary(rows),
        ),
        "family_supply_lifecycle": _family_supply_lifecycle_read_model(rows, events),
        "population_elo": _population_elo_summary(population_elo_raw if isinstance(population_elo_raw, dict) else {}),
        "family_promotion_diagnostics": _family_promotion_diagnostics(
            registry if isinstance(registry, dict) else {},
            heldout_scout if isinstance(heldout_scout, dict) else {},
        ),
    }
    payload["agentic_handoff_contract"] = _agentic_handoff_contract_read_model(
        rows,
        factory_policy=factory_policy if isinstance(factory_policy, dict) else {},
        trailing_window_s=args.window_s,
    )
    payload["c_supply_upstream_rater"] = _upstream_rater_summary(
        c_supply_upstream_rater_raw if isinstance(c_supply_upstream_rater_raw, dict) else {},
        credit_ready_read_model=payload["c_supply_credit_ready_read_model"],
    )
    payload["strict_c_yield_decomposition"] = _strict_c_yield_decomposition(
        payload,
        factory_policy=factory_policy if isinstance(factory_policy, dict) else {},
        trailing_window_s=args.window_s,
    )
    payload["execution_mode_read_model"] = _execution_mode_read_model(
        rows,
        payload,
        factory_policy=factory_policy if isinstance(factory_policy, dict) else {},
        factory_policy_path=args.factory_policy,
        policy_profile=args.policy_profile,
        trailing_window_s=args.window_s,
    )
    payload["proof_lane_rca"] = _proof_lane_rca(
        rows,
        payload["backlog_replenisher"],
        factory_policy if isinstance(factory_policy, dict) else {},
        trailing_window_s=args.window_s,
    )
    run_observability = _run_observability_read_model(args)
    if run_observability:
        payload["run_observability"] = run_observability
    payload["conversion_diagnostics"] = _conversion_diagnostics(
        rows,
        events,
        payload["observability"],
        payload["family_promotion_diagnostics"],
        intelligence_policy,
        trailing_window_s=args.window_s,
    )
    payload["action_impact_records"] = _action_impact_records(payload)
    payload["recommendations"] = _recommendations(payload)
    # Move-space reachability + yield (2026-06-06): surfaces the starvation finding (native+warm dominate
    # the attempts, the strategist/decomposition/falsify tail is dormant) + per-move ratified yield from the
    # enriched attempts DB — answers "are we actually using the move space we built?" without raw-DB joins.
    # Fail-soft: a DB-read error must never break the intelligence report.
    try:
        _src = str(REPO / "src")   # solver/__init__ uses bare `ztare` imports → need src on the path
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from ztare.leanmill.solver.move_calibration import move_yield_report as _move_yield_report
        payload["move_space_yield"] = _move_yield_report(
            REPO / "analytics" / "public" / "queries" / "solver_lane_attempts.db")
    except Exception as _myr_err:  # noqa: BLE001
        payload["move_space_yield"] = {"error": repr(_myr_err)[:160]}
    payload["verdict"] = _verdict(payload)
    if args.out:
        _write_json(args.out, payload)
    if args.md:
        _write_markdown(args.md, payload)
    if args.events and args.out:
        work_queue.append_event(args.events, {
            "event_type": "leanmill_factory_intelligence_report",
            "payload": {
                "verdict": payload["verdict"]["status"],
                "top_recommendation": payload["recommendations"][0] if payload["recommendations"] else {},
                "source_ready_holds": payload["loss_accounting"]["source_search_integrations"].get("ready_held_count", 0),
                "stale_worker_process_count": payload.get("worker_version_health", {}).get("stale_process_count"),
                "runtime_mismatch_count": payload.get("worker_version_health", {}).get("runtime_mismatch_count"),
            },
            "artifact_paths": [args.out, args.md] if args.md else [args.out],
        })
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_factory_intelligence_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        cx = work_queue.connect(db)
        wid = work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": "source_search:fam:w1",
            "family": "fam",
            "exit_kind": "qualified_source_candidates",
        })
        work_queue.append_event(events, {"event_type": "source_search_worker_started", "work_id": wid, "timestamp": _now() - 10})
        work_queue.update_status(cx, work_id=wid, status="done", payload_update={"exit_kind": "qualified_source_candidates"})
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
            "work_id": "probe:fam:invalid-negative",
            "family": "fam",
            "probe_lane": "family_spec",
            "scoreboard": "",
            "negative_control_invalid_fail_count": 1,
            "row_outcomes": [{"row_id": "r-bad", "learning_unit_exit": "invalid_negative_control", "negative_control_invalid_fail_count": 1}],
        })
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
            "work_id": "probe:fam:static-positive-leak",
            "family": "fam",
            "probe_lane": "family_spec",
            "scoreboard": "",
            "negative_control_fail_count": 1,
            "negative_control_unexpected_pass_count": 0,
            "negative_control_invalid_fail_count": 0,
            "row_outcomes": [{"row_id": "c-static-positive", "learning_unit_exit": "ratified_closure", "ratified_closure_count": 1}],
        })
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe:fam:missing-target-meta",
            "family": "fam",
            "probe_lane": "family_spec",
            "probe_corpus_meta": {
                "selected_row_count": 1,
                "selected_row_ids": ["MCB_123_missing"],
                "unresolved_row_reasons": [{"row_id": "MCB_123_missing", "reason": "target_theorem_not_resolved"}],
            },
        })
        work_queue.record_terminal_item(cx, kind="agent_repair_task", status="done", priority=1, payload={
            "work_id": "family_birth_candidate:born:f1",
            "family": "born",
            "expected_exit": "family_spec_patch",
            "family_spec_patch_mode": "family_birth_candidate",
            "exit_kind": "family_spec_patch",
            "family_spec_patch_receipt": {"schema": "test", "status": "pass"},
            "family_birth_activation": {"schema": "test", "status": "pass", "enqueued": 1, "job_count": 1},
        })
        work_queue.append_event(events, {"event_type": "family_birth_activated", "work_id": "family_birth_candidate:born:f1", "timestamp": _now(), "payload": {"family": "born", "status": "pass", "enqueued": 1}})
        work_queue.enqueue(cx, kind="agent_repair_task", priority=1, payload={
            "work_id": "family_spec_generalize:fam:g1",
            "family": "fam",
            "expected_exit": "family_spec_patch",
            "family_spec_patch_mode": "generalize_family_spec",
        })
        work_queue.record_terminal_item(cx, kind="agent_repair_task", status="done", priority=1, payload={
            "work_id": "agent:fam:w1",
            "family": "fam",
            "station": "repair_registry",
            "expected_exit": "exact_gap_candidate",
            "exit_kind": "agent_repair_attempt_finished",
            "agent_launched": True,
            "usage_estimate": {
                "schema": "leanmill-subscription-agent-usage-estimate-v2",
                "runtime": "codex",
                "task_kind": "agent_repair_task",
                "worker_id": "warm-codex-test",
                "agent_id": "leanmill_codex_test",
                "estimated_prompt_tokens": 10,
                "estimated_output_tokens": 20,
                "estimated_total_tokens": 30,
                "wall_time_s": 2,
                "warm_session_reused": True,
                "subscription_mode": True,
                "api_llm_call": False,
                "cost_usd": 0,
            },
        })
        open_agent = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "source_scout:fam:w1",
            "family": "fam",
            "station": "source_qualification",
            "expected_exit": "source_request",
        })
        work_queue.update_status(cx, work_id=open_agent, status="running")
        integration_dir = root / "integrations"
        integration_dir.mkdir()
        (integration_dir / "hold.json").write_text(json.dumps({
            "family": "fam",
            "integration_decision": "hold_low_quality_or_no_enough_sources",
            "integration_blockers": ["no_allowed_active_binding_target_rows"],
            "source_search_summary": {"ready_total": 3},
        }) + "\n")
        growth_path = root / "c_supply_growth.json"
        growth_path.write_text(json.dumps({
            "schema": "leanmill-c-supply-growth-controller-v1",
            "target_credit_ready_rows": 20,
            "final_selection": {
                "status": "ready",
                "credit_ready_count": 1,
                "eligible_count": 1,
                "selected_count": 1,
                "selected_rows_order": ["c-ready-1"],
                "rows": [{
                    "row_id": "c-ready-1",
                    "eligible": True,
                    "probe_credit_ready": True,
                    "probe_verified_families": ["fam"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                }],
            },
            "rounds": [{
                "probe_seed_summary": {
                    "schema": "leanmill-c-supply-probe-seed-summary-v1",
                    "generated_job_count": 1,
                    "job_count": 1,
                    "enqueued": 1,
                    "selected_row_count": 1,
                    "target_row_count": 3,
                    "unresolved_row_count": 2,
                    "unresolved_reason_counts": {"missing_source_file": 2},
                    "unresolved_rows": [{"row_id": "r-missing", "reason": "missing_source_file", "family": "fam"}],
                },
            }],
        }) + "\n")
        clean_selection_path = root / "clean_selection.json"
        clean_selection_path.write_text(json.dumps({
            "status": "ready",
            "credit_ready_count": 2,
            "eligible_count": 2,
            "selected_count": 2,
            "selected_rows_order": ["c-ready-1", "c-ready-2"],
            "rows": [
                {
                    "row_id": "c-ready-1",
                    "eligible": True,
                    "probe_credit_ready": True,
                    "probe_verified_families": ["fam"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                },
                {
                    "row_id": "c-ready-2",
                    "eligible": True,
                    "probe_credit_ready": True,
                    "probe_verified_families": ["fam2"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                },
            ],
        }) + "\n")
        population_path = root / "population_elo.json"
        population_path.write_text(json.dumps({
            "schema": "leanmill-population-elo-v1",
            "checkpoint": "ck.jsonl",
            "record_count": 2,
            "row_count": 1,
            "contestant_count": 2,
            "event_count": 1,
            "non_laundering_note": "routing memory only",
            "ratings": [
                {"contestant": "family:fam", "rating": 1012.0, "p_ucb_priority": 1050.0, "games": 1, "wins": 1, "losses": 0, "ties": 0},
                {"contestant": "arm:static", "rating": 988.0, "p_ucb_priority": 1000.0, "games": 1, "wins": 0, "losses": 1, "ties": 0},
            ],
        }) + "\n")
        upstream_path = root / "upstream_rater.json"
        upstream_path.write_text(json.dumps({
            "schema": "leanmill-c-supply-upstream-routing-rater-v1",
            "mode": "observe_only",
            "model": "gpt-5.4-mini",
            "run_model": True,
            "candidate_count": 1,
            "model_validation": {"ok": True, "errors": [], "rating_count": 1},
            "model_output": {
                "schema": "leanmill-upstream-routing-rater-output-v1",
                "ratings": [{"family": "fam", "p_useful_exit": 0.75, "p_static_strict_fail": 0.8, "p_template_convertible": 0.6, "spend_rank": 1, "main_risk": "sample"}],
            },
            "combined_ranking": [{"family": "fam", "effective_rank": 1, "deterministic_rank": 1, "model_rank": 1, "row_count": 3, "deterministic_routing_score": 30.0}],
            "ordered_families": ["fam"],
            "credit_boundary": "routing_forecast_only_no_proof_credit",
        }) + "\n")
        typed_exits_path = root / "typed_proof_exits.json"
        typed_exits_path.write_text(json.dumps({
            "schema": "leanmill-typed-proof-exit-artifact-v1",
            "summary": {"exit_count": 1, "typed_exit_kind_counts": {"gap_report": 1}, "credit_boundary": "advisory"},
            "exits": [{"attempt_id": "er1", "source_kind": "route_c_layer_2c", "typed_exit_kind": "gap_report", "residual_class": "theorem_or_pde_gap"}],
        }) + "\n")
        eval_prep_path = root / "evaluation_harness_prep.json"
        eval_prep_path.write_text(json.dumps({
            "schema": "leanmill-evaluation-harness-prep-v1",
            "selected_row_count": 4,
            "contract": "contract.json",
            "row_context": "rows.json",
            "next_blocker": {"benchmark_can_run_full": True, "blockers": []},
            "benchmark_preflight": {
                "family_template_selected_count": 4,
                "selected_template_rows_with_negative_controls": ["r1", "r2", "r3", "r4"],
                "selected_target_resolution_status": "pass",
                "selected_target_unresolved_row_count": 0,
                "full_pool_target_resolution_status": "fail",
                "full_pool_target_unresolved_row_count": 9,
                "source_materialization": {"counts": {"materialized": 4, "skip": 9}, "failure_count": 0},
            },
        }) + "\n")
        competitive_inventory_path = root / "competitive_inventory.json"
        competitive_inventory_path.write_text(json.dumps({
            "schema": "leanmill-competitive-inventory-v1",
            "credit_boundary": "inventory only",
            "summary": {
                "route_c_gap_report_count": 2,
                "route_c_compiled_or_closed_count": 0,
                "ztare_lean_file_count": 7,
                "ztare_files_with_sorry_or_admit_count": 3,
                "pr_a1_status": "static_sorry_free_needs_compile_and_l3_audit",
            },
            "pr_a1_candidate": {
                "status": "static_sorry_free_needs_compile_and_l3_audit",
                "static_audit": {"path": "PR_A1.lean"},
            },
        }) + "\n")
        family_gate_path = root / "family_spec_gate.json"
        family_gate_path.write_text(json.dumps({
            "schema": "leanmill-family-spec-gate-v1",
            "status": "pass",
            "failure_count": 0,
            "quarantine_failure_count": 0,
            "usable": {"row_template_count": 4},
            "supply_quality_summary": {"class_counts": {"probe_ready_general": 1}, "gap_counts": {}, "median_generality_score": 70},
            "overclaim_disqualification_summary": {
                "schema": "leanmill-overclaim-disqualification-summary-v1",
                "finding_count": 1,
                "family_count": 1,
                "by_family": {"fam": 1},
                "interpretation": "mechanism evidence only until benchmark uplift",
            },
        }) + "\n")
        policy_path = root / "policy.json"
        policy_path.write_text(json.dumps({
            "operations": {
                "priority_policy": {
                    "schema": "leanmill-priority-policy-v1",
                    "ordering_rule": "Higher integer priority wins. Durable queue workers claim queued rows by priority DESC, then created_at ASC.",
                    "rationale": "self-test override proves recommendations read named policy priority values",
                    "recommendations": {
                        "evaluation_harness_ready_for_credited_run": 1999,
                    },
                },
            },
        }) + "\n")
        out = root / "intel.json"
        base_args = argparse.Namespace(
            queue_db=db,
            events=events,
            out=str(out),
            md=str(root / "intel.md"),
            observability=str(root / "missing_obs.json"),
            station_health=str(root / "missing_health.json"),
            contract=str(root / "missing_contract.json"),
            repair_registry=str(root / "missing_registry.json"),
            family_spec_gate=str(family_gate_path),
            backlog_replenisher=str(root / "missing_backlog_replenisher.json"),
            c_supply_batch_status=str(root / "missing_c_supply_batch.json"),
            c_supply_expost_cleaner=str(root / "missing_c_supply_expost_cleaner.json"),
            c_supply_clean_selection=str(clean_selection_path),
            c_supply_growth_status=str(growth_path),
            agentic_portfolio=str(root / "missing_agentic_portfolio.json"),
            c_supply_source_materialization=str(root / "missing_c_supply_source_materialization.json"),
            c_supply_upstream_rater=str(upstream_path),
            typed_proof_exits=str(typed_exits_path),
            evaluation_harness_prep=str(eval_prep_path),
            evaluation_harness_run=str(root / "missing_eval_run.json"),
            evaluation_no_lift_report=str(root / "missing_no_lift_report.json"),
            mechanism_vs_overclaim_report=str(root / "missing_mechanism_vs_overclaim.json"),
            pr_a1_public_review=str(root / "missing_pr_a1_public_review.json"),
            competitive_inventory=str(competitive_inventory_path),
            population_elo=str(root / "population_elo.json"),
            heldout_scout=str(root / "missing_heldout_scout.json"),
            factory_policy=str(policy_path),
            policy_profile="",
            source_search_integrations=str(integration_dir),
            event_tail=100,
            window_s=3600,
            integration_receipt_limit=20,
            worker_heartbeat_stale_s=0,
        )
        payload = build(base_args)
        assert payload["schema"] == "leanmill-factory-intelligence-v1"
        assert payload["loss_accounting"]["source_search_integrations"]["ready_held_count"] == 1
        assert payload["subscription_agent_usage"]["launched_count"] == 1
        assert payload["subscription_agent_usage"]["estimated_total_tokens"] == 30
        assert payload["subscription_agent_usage"]["open_count"] == 2
        assert any(rec["class"] == "source_binding_conversion_gap" for rec in payload["recommendations"])
        assert payload["c_supply_credit_ready_read_model"]["credit_ready_count"] == 2
        assert payload["c_supply_credit_ready_read_model"]["credit_ready_unique_row_count"] == 2
        assert payload["c_supply_credit_ready_read_model"]["credit_ready_row_family_evidence_count"] >= 2
        assert payload["c_supply_credit_ready_read_model"]["remaining_to_target"] == 18
        assert payload["c_supply_credit_ready_read_model"]["source_disagreement"] is True
        assert sorted(r["row_id"] for r in payload["c_supply_credit_ready_read_model"]["credit_ready_rows"]) == ["c-ready-1", "c-ready-2"]
        running_latest_selection_path = root / "running_latest_selection.json"
        running_latest_selection_path.write_text(json.dumps({
            "status": "blocked",
            "credit_ready_count": 0,
            "eligible_count": 1,
            "selected_count": 1,
            "selected_rows_order": ["running-ready"],
            "selected_rows": [{
                "row_id": "running-ready",
                "eligible": True,
                "probe_credit_ready": True,
                "probe_verified_families": ["fam-running"],
                "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
            }],
        }) + "\n")
        stale_final_selection_path = root / "stale_final_selection.json"
        stale_final_selection_path.write_text(json.dumps({
            "status": "ready",
            "credit_ready_count": 1,
            "eligible_count": 1,
            "selected_count": 1,
            "selected_rows_order": ["stale-ready"],
            "rows": [{"row_id": "stale-ready", "eligible": True, "probe_credit_ready": True, "probe_verified_families": ["fam-stale"]}],
        }) + "\n")
        running_growth_model = _c_supply_credit_ready_read_model(
            c_supply_batch={},
            c_supply_clean_selection={},
            c_supply_growth={
                "status": "running",
                "latest_selection": str(running_latest_selection_path),
                "best_selection": str(running_latest_selection_path),
                "final_selection": str(stale_final_selection_path),
            },
            factory_policy={
                "operations": {
                    "c_supply_breadth_policy": {
                        "minimum_credit_ready_rows": 20,
                        "growth_goal_credit_ready_rows": 50,
                        "continue_after_minimum_floor": True,
                    },
                },
            },
        )
        assert [r["row_id"] for r in running_growth_model["credit_ready_rows"]] == ["running-ready"], running_growth_model
        assert running_growth_model["source_summaries"][0]["source"] == "growth_controller_running_latest_selection_path", running_growth_model
        assert running_growth_model["effective_target_credit_ready_rows"] == 50, running_growth_model
        assert running_growth_model["remaining_to_effective_target"] == 49, running_growth_model
        pending_static_selection_path = root / "pending_static_selection.json"
        pending_static_selection_path.write_text(json.dumps({
            "status": "blocked",
            "credit_ready_count": 99,
            "eligible_count": 1,
            "selected_count": 1,
            "selected_rows_order": ["pending-static"],
            "selected_rows": [{
                "row_id": "pending-static",
                "eligible": True,
                "probe_credit_ready": True,
                "probe_verified_families": ["fam-pending"],
                "c_discriminating_evidence_status": "c_discriminating_probe_verified_pending_static_sweep",
                "static_sweep_required_before_c_credit": True,
                "static_tools_result": {"status": "unknown_not_run"},
            }],
        }) + "\n")
        pending_static_model = _c_supply_credit_ready_read_model(
            c_supply_batch={},
            c_supply_clean_selection={},
            c_supply_growth={
                "status": "running",
                "latest_selection": str(pending_static_selection_path),
                "best_selection": str(pending_static_selection_path),
            },
            factory_policy={
                "operations": {
                    "c_supply_breadth_policy": {
                        "minimum_credit_ready_rows": 20,
                        "growth_goal_credit_ready_rows": 50,
                        "continue_after_minimum_floor": True,
                    },
                },
            },
        )
        assert pending_static_model["credit_ready_count"] == 0, pending_static_model
        assert pending_static_model["probe_verified_pending_static_count"] == 1, pending_static_model
        assert [r["row_id"] for r in pending_static_model["probe_verified_pending_static_rows"]] == ["pending-static"], pending_static_model
        live_summary = next(s for s in payload["c_supply_credit_ready_read_model"]["source_summaries"] if s["source"] == "live_queue")
        assert live_summary["blockers_by_reason"].get("live_queue_without_static_strict_no_signal") == 1, live_summary
        assert any(rec["class"] == "c_supply_live_queue_static_filter_leakage" for rec in payload["recommendations"])
        assert any(rec["class"] == "c_supply_credit_ready_row_gap" for rec in payload["recommendations"])
        assert any(rec["class"] == "c_supply_probe_source_materialization_debt" for rec in payload["recommendations"])
        source_materialization_path = root / "c_supply_source_materialization.json"
        source_materialization_path.write_text(json.dumps({
            "schema": "leanmill-c-supply-source-materialization-v1",
            "status": "materialized_c_supply_sources",
            "requested_row_count": 1,
            "unresolved_after_count": 0,
            "credit_boundary": "source materialization only; no proof, benchmark, source, or C-supply credit",
            "anti_laundering_guard": "Rows remain probe-owed until independent probe receipts and governance checks pass.",
            "materialization": {"counts": {"materialized": 1}},
            "rows": [{"row_id": "r-missing", "status": "source_ready", "source_file": "r_missing.lean"}],
        }) + "\n")
        payload_source_ready = build(argparse.Namespace(**{
            **vars(base_args),
            "out": str(root / "intel_source_ready.json"),
            "md": str(root / "intel_source_ready.md"),
            "c_supply_source_materialization": str(source_materialization_path),
        }))
        assert not any(rec["class"] == "c_supply_probe_source_materialization_debt" for rec in payload_source_ready["recommendations"])
        assert payload["learning_feedback_read_model"]["exit_counts"]["invalid_negative_control"] == 1
        assert payload["learning_feedback_read_model"]["review_required_count"] == 1
        assert any(rec["class"] == "invalid_negative_control_feedback_debt" for rec in payload["recommendations"])
        assert payload["typed_proof_exit_read_model"]["summary"]["exit_count"] == 1
        assert payload["evaluation_harness_read_model"]["status"] == "ready_for_credited_run"
        assert payload["evaluation_harness_read_model"]["selected_target_resolution_status"] == "pass"
        assert any(rec["class"] == "evaluation_harness_ready_for_credited_run" for rec in payload["recommendations"])
        assert payload["competitive_inventory_read_model"]["status"] == "pr_a1_compile_l3_audit_ready"
        assert any(rec["class"] == "pr_a1_compile_l3_audit_ready" for rec in payload["recommendations"])
        pr_ready_target = root / "PR_A1_ready.lean"
        pr_ready_audit = root / "pr_a1_audit_ready.json"
        pr_ready_review = root / "pr_a1_public_review.json"
        pr_ready_target.write_text("lemma t : True := by trivial\n")
        pr_ready_audit.write_text(json.dumps({"status": "compile_pass_l3_advisory_pass"}) + "\n")
        pr_ready_review.write_text(json.dumps({
            "status": "governed_public_review_ready",
            "target": str(pr_ready_target),
            "target_sha256": sha256_file(pr_ready_target),
            "audit": str(pr_ready_audit),
            "audit_sha256": sha256_file(pr_ready_audit),
        }) + "\n")
        pr_review_model = _competitive_inventory_read_model(
            {
                "schema": "leanmill-competitive-inventory-v1",
                "summary": {
                    "pr_a1_status": "compile_pass_l3_advisory_pass",
                },
                "pr_a1_candidate": {
                    "status": "compile_pass_l3_advisory_pass",
                    "static_audit": {"path": str(pr_ready_target)},
                },
            },
            path=str(root / "competitive_inventory_ready.json"),
            pr_a1_public_review=json.loads(pr_ready_review.read_text()),
            pr_a1_public_review_path=str(pr_ready_review),
        )
        assert pr_review_model["status"] == "pr_a1_public_artifact_review_published", pr_review_model
        pr_review_payload = dict(payload)
        pr_review_payload["competitive_inventory_read_model"] = pr_review_model
        assert not any(rec["class"] == "pr_a1_public_artifact_review_ready" for rec in _recommendations(pr_review_payload))
        masked_eval = _evaluation_harness_read_model(
            json.loads(eval_prep_path.read_text()),
            {
                "preflight_only": False,
                "record_count": 16,
                "selected_row_count": 4,
                "completed_row_count": 4,
                "residual_candidate_order": "tool_first",
                "residual_memory_observability": {
                    "status": "fail",
                    "masked_family_candidate_record_count": 2,
                },
            },
            prep_path=str(eval_prep_path),
            run_path=str(root / "masked_eval_run.json"),
        )
        assert masked_eval["status"] == "credited_run_masked_residual_memory", masked_eval
        debt_payload = dict(payload)
        debt_payload["evaluation_harness_read_model"] = masked_eval
        assert any(rec["class"] == "evaluation_harness_observability_debt" for rec in _recommendations(debt_payload))
        limited_eval = _evaluation_harness_read_model(
            json.loads(eval_prep_path.read_text()),
            {
                "preflight_only": False,
                "record_count": 8,
                "selected_row_count": 2,
                "completed_row_count": 2,
                "residual_candidate_order": "family_first",
                "residual_memory_observability": {
                    "status": "pass",
                    "masked_family_candidate_record_count": 0,
                },
            },
            prep_path=str(eval_prep_path),
            run_path=str(root / "limited_eval_run.json"),
        )
        assert limited_eval["status"] == "credited_run_limited_slice", limited_eval
        no_lift_eval = _evaluation_harness_read_model(
            json.loads(eval_prep_path.read_text()),
            {
                "preflight_only": False,
                "record_count": 16,
                "selected_row_count": 4,
                "completed_row_count": 4,
                "residual_candidate_order": "family_first",
                "residual_memory_observability": {
                    "status": "pass",
                    "masked_family_candidate_record_count": 0,
                },
                "arm_metrics": {
                    "benchmark_lift_comparison": {
                        "meets_20pp_closure_lift": False,
                        "meets_2x_attempt_efficiency_lift": False,
                    },
                },
            },
            prep_path=str(eval_prep_path),
            run_path=str(root / "no_lift_eval_run.json"),
        )
        assert no_lift_eval["status"] == "credited_run_recorded_no_benchmark_lift", no_lift_eval
        assert payload["intelligence_policy"]["priority_policy"]["schema"] == "leanmill-priority-policy-v1"
        eval_rec = next(rec for rec in payload["recommendations"] if rec["class"] == "evaluation_harness_ready_for_credited_run")
        assert eval_rec["priority"] == 1999
        assert payload["target_resolution_read_model"]["open_missing_target_metadata_count"] == 1
        assert payload["target_resolution_read_model"]["unresolved_reason_counts"]["target_theorem_not_resolved"] == 1
        assert any(rec["class"] == "family_spec_target_resolution_debt" for rec in payload["recommendations"])
        assert "target_resolution_conflict_seen" not in payload["target_resolution_read_model"]["risk_classes"]
        assert payload["action_impact_records"][1]["guardrail_metrics"]["negative_control_invalid_fail_count"] == 1
        assert payload["family_supply_lifecycle"]["open_family_generalize_count"] == 1
        assert payload["family_supply_lifecycle"]["activation_seeded_count"] == 1
        assert payload["family_supply_lifecycle"]["possible_birth_activation_leakage_count"] == 0
        assert payload["agentic_handoff_contract"]["schema"] == "leanmill-agentic-handoff-contract-read-model-v1"
        assert payload["agentic_handoff_contract"]["status"] == "pass"
        assert payload["agentic_handoff_contract"]["hard_leak_count"] == 0
        assert payload["agentic_handoff_contract"]["verified_handoff_count"] == 1
        assert payload["population_elo"]["record_count"] == 2
        assert payload["population_elo"]["top_routing_priorities"][0]["contestant"] == "family:fam"
        assert payload["c_supply_upstream_rater"]["mean_brier_useful_exit_now"] == 0.0625
        assert payload["c_supply_upstream_rater"]["joined_routing_outcomes"][0]["useful_exit_observed_now"] is True
        assert payload["strict_c_yield_decomposition"]["schema"] == "leanmill-strict-c-yield-decomposition-v1"
        assert payload["strict_c_yield_decomposition"]["terms"]["time"]["cycle_time_basis"] in {
            "c_supply_growth_started_to_generated",
            "latest_growth_round_command_wall_sum",
            "factory_intelligence_trailing_window",
        }
        assert payload["strict_c_yield_decomposition"]["predictive_model_readiness"]["status"] == "insufficient_resolved_attempts"
        assert any(rec["class"] == "c_supply_yield_bottleneck" for rec in payload["recommendations"])
        assert payload["execution_mode_read_model"]["schema"] == "leanmill-execution-mode-read-model-v1"
        assert payload["execution_mode_read_model"]["observed_open_work_by_mode"]["subscription_agent_source_scout_generation"] >= 1
        assert payload["execution_mode_read_model"]["subscription_agent_usage"]["warm_session_reused_count"] == 1
        assert payload["execution_mode_read_model"]["declared_models"]["general_subscription_agent"]["default_model"]
        assert any(rec["class"] == "upstream_rater_calibration_visible" for rec in payload["recommendations"])
        assert any(rec["class"] == "population_routing_priorities_ready" for rec in payload["recommendations"])
        assert any(rec["class"] == "mechanism_vs_overclaim_evidence_debt" for rec in payload["recommendations"])
        assert "mechanism_vs_overclaim" in (root / "intel.md").read_text(errors="ignore")
        assert payload["heavy_lean_process_pressure"]["schema"] == "leanmill-heavy-lean-process-pressure-v1"
        assert out.exists()
    print("leanmill_factory_intelligence self-test PASS")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--observability", default=DEFAULT_OBSERVABILITY)
    ap.add_argument("--station-health", default=DEFAULT_STATION_HEALTH)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--repair-registry", default=DEFAULT_REPAIR_REGISTRY)
    ap.add_argument("--family-spec-gate", default=DEFAULT_FAMILY_SPEC_GATE)
    ap.add_argument("--backlog-replenisher", default=DEFAULT_BACKLOG_REPLENISHER)
    ap.add_argument("--c-supply-batch-status", default=DEFAULT_C_SUPPLY_BATCH_STATUS)
    ap.add_argument("--c-supply-expost-cleaner", default=DEFAULT_C_SUPPLY_EXPOST_CLEANER)
    ap.add_argument("--c-supply-clean-selection", default=DEFAULT_C_SUPPLY_CLEAN_SELECTION)
    ap.add_argument("--c-supply-growth-status", default=DEFAULT_C_SUPPLY_GROWTH_STATUS)
    ap.add_argument("--agentic-portfolio", default=DEFAULT_AGENTIC_PORTFOLIO)
    ap.add_argument("--c-supply-source-materialization", default=DEFAULT_C_SUPPLY_SOURCE_MATERIALIZATION)
    ap.add_argument("--c-supply-upstream-rater", default=DEFAULT_C_SUPPLY_UPSTREAM_RATER)
    ap.add_argument("--typed-proof-exits", default=DEFAULT_TYPED_PROOF_EXITS)
    ap.add_argument("--evaluation-harness-prep", default=DEFAULT_EVALUATION_HARNESS_PREP)
    ap.add_argument("--evaluation-harness-run", default=DEFAULT_EVALUATION_HARNESS_RUN)
    ap.add_argument("--evaluation-no-lift-report", default=DEFAULT_EVALUATION_NO_LIFT_REPORT)
    ap.add_argument("--mechanism-vs-overclaim-report", default=DEFAULT_MECHANISM_VS_OVERCLAIM_REPORT)
    ap.add_argument("--pr-a1-public-review", default=DEFAULT_PR_A1_PUBLIC_REVIEW)
    ap.add_argument("--competitive-inventory", default=DEFAULT_COMPETITIVE_INVENTORY)
    ap.add_argument("--population-elo", default=DEFAULT_POPULATION_ELO)
    ap.add_argument("--heldout-scout", default=DEFAULT_HELDOUT_SCOUT)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--source-search-integrations", default=DEFAULT_SOURCE_SEARCH_INTEGRATIONS)
    ap.add_argument("--event-tail", type=int, default=10000)
    ap.add_argument("--window-s", type=int, default=3600)
    ap.add_argument("--integration-receipt-limit", type=int, default=200)
    ap.add_argument("--worker-heartbeat-stale-s", type=int, default=0)
    ap.add_argument("--run-observability-tag", default="",
                    help="optional LeanMill run_tag to join into this factory read model")
    ap.add_argument("--run-observability-manifest", default="",
                    help="optional .solver_scratch/<run_tag>/run_manifest.json path")
    ap.add_argument("--run-observability-lean-root", default="")
    ap.add_argument("--run-observability-attempts-db", default=str(DEFAULT_RUN_OBSERVABILITY_ATTEMPTS_DB))
    ap.add_argument("--run-observability-verdicts", default=str(DEFAULT_RUN_OBSERVABILITY_VERDICTS))
    ap.add_argument("--run-observability-bank-attempts", default=str(DEFAULT_RUN_OBSERVABILITY_BANK_ATTEMPTS))
    ap.add_argument("--run-observability-formalize-attempts", default=str(DEFAULT_RUN_OBSERVABILITY_FORMALIZE_ATTEMPTS))
    ap.add_argument("--run-observability-notes-trace", default=str(DEFAULT_RUN_OBSERVABILITY_NOTES_TRACE))
    ap.add_argument("--run-observability-cot-traces", default=str(DEFAULT_RUN_OBSERVABILITY_COT_TRACES))
    ap.add_argument("--run-observability-proof-cache", default=str(DEFAULT_RUN_OBSERVABILITY_PROOF_CACHE))
    ap.add_argument("--run-observability-no-good", default=str(DEFAULT_RUN_OBSERVABILITY_NO_GOOD))
    ap.add_argument("--run-observability-faithfulness", default=str(DEFAULT_RUN_OBSERVABILITY_FAITHFULNESS))
    ap.add_argument("--run-observability-decomposition-cache", default=str(DEFAULT_RUN_OBSERVABILITY_DECOMPOSITION_CACHE))
    ap.add_argument("--run-observability-staged-index", default="")
    ap.add_argument("--run-observability-axiom-packs", default=str(DEFAULT_RUN_OBSERVABILITY_AXIOM_PACKS))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--denotation-rollup", action="store_true",
                    help="print the repo-level def-denotation verdict rollup as JSON and exit (pure read)")
    return ap


def main() -> int:
    args = _build_arg_parser().parse_args()
    if args.self_test:
        return _self_test()
    if args.denotation_rollup:
        print(json.dumps(denotation_rollup(), indent=2, sort_keys=True))
        return 0
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "verdict": payload["verdict"]["status"],
        "top_recommendation": payload["recommendations"][0]["class"] if payload["recommendations"] else "",
        "queue_open_total": payload["queue"]["open_total"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
