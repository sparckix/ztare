#!/usr/bin/env python3
"""Convert finished proof probes into the next bounded LeanMill work item.

A zero-score probe is still information, but it must not become a dead end.
This worker inspects terminal probe WorkItems and emits exactly one follow-up:

- family_spec no-signal -> bounded Codex repair/exact-gap agent task
- source_shape no-signal -> bounded exact-gap/decomposition proposal task
- unsafe negative-control pass -> operator-required safety task

The original probe row is marked as triaged, so repeated runner cycles do not
create duplicate work.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import leanmill_work_queue as work_queue
import leanmill_learning_feedback_contract as learning_feedback
import leanmill_operator_contracts as operator_contracts
import leanmill_family_specs as family_specs
from leanmill_factory_config import apply_profile_section, priority_value
from src.ztare.leanmill.contracts import handoff as handoff_contract

DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/post_probe_triage_status.json"
DEFAULT_FAMILY_SPEC_DIR = "analytics/public/leanmill/repair_families"
DEFAULT_C_SUPPLY_CHECKPOINT = "analytics/public/leanmill/dashboard_data/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_C_SUPPLY_ROW_CONTEXT = "analytics/public/leanmill/dashboard_data/c_supply_batch_cleaned_row_context.json"
DEFAULT_C_SUPPLY_SELECTION = "analytics/public/leanmill/dashboard_data/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_FAMILY_SPEC_ACTIVATION_DIR = "analytics/public/leanmill/dashboard_data/family_spec_activation_reconciliation"
FAMILY_SPEC_POSITIVE_REPAIR_MODE = "family_spec_positive_repair"

_LEAN_DECL_RE = re.compile(
    r"(?m)^\s*(?:@[^\n]*\n\s*)*(?:(?:public|private|protected|noncomputable)\s+)*(?:theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)"
)


def _now() -> int:
    return int(time.time())


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", ":"} else "_" for ch in value).strip("_") or "item"


def _family_spec_positive_repair_handoff_field(args: argparse.Namespace) -> str:
    factory_policy = _read_json(getattr(args, "factory_policy", "")) or {}
    policy = handoff_contract.policy_from_factory_policy(factory_policy if isinstance(factory_policy, dict) else {})
    return handoff_contract.receipt_field_for_mode(FAMILY_SPEC_POSITIVE_REPAIR_MODE, policy)


def _handoff_credit_boundary() -> dict[str, Any]:
    return {
        "source_credit_eligible": False,
        "clean_solver_credit_eligible": False,
        "proof_credit_authority": "governance_gate",
        "worker_can_self_ratify": False,
    }


def _blocked_positive_repair_handoff_receipt(
    *,
    work_id: str,
    family: str,
    reason: str,
    candidate_rows: list[str] | None = None,
    selected_rows: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": handoff_contract.REPAIR_RECEIPT_SCHEMA,
        "status": "skipped",
        "reason": reason,
        "source_work_id": work_id,
        "work_id": work_id,
        "family": family,
        "family_spec_patch_mode": FAMILY_SPEC_POSITIVE_REPAIR_MODE,
        "candidate_rows": sorted(set(candidate_rows or [])),
        "selected_rows": sorted(set(selected_rows or [])),
        "selected_row_count": len(set(selected_rows or [])),
        "enqueued": 0,
        "job_count": 0,
        "credit_boundary": _handoff_credit_boundary(),
    }



def _work_exists(cx: Any, work_id: str) -> bool:
    row = cx.execute("SELECT 1 FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone()
    return row is not None


def _rebalance_open_regovernance_priorities(cx: Any, priority: int) -> int:
    target = int(priority)
    if target <= 0:
        return 0
    cur = cx.execute(
        """
        UPDATE work_items
        SET priority=?, updated_at=?
        WHERE kind='repair_canary_probe'
          AND status='queued'
          AND work_id LIKE 'post_probe_regovern:%'
          AND priority < ?
        """,
        (target, _now(), target),
    )
    cx.commit()
    return int(cur.rowcount or 0)

def _int_count(obj: dict[str, Any], key: str) -> int:
    return learning_feedback.int_count(obj, key)


def _exit_kind(payload: dict[str, Any]) -> str:
    return learning_feedback.learning_exit_from_counts(payload)


def _scoreboard(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}

def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not path or not p.exists() or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("rows", "results", "row_results", "qualified_rows", "corpus"):
        vals = obj.get(key)
        if isinstance(vals, list):
            rows.extend(x for x in vals if isinstance(x, dict))
    return rows


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _target_theorem_name_from_source(source_file: str, row_id: str) -> str:
    path = Path(source_file)
    if source_file and path.exists() and path.is_file():
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            text = ""
        matches = list(_LEAN_DECL_RE.finditer(text))
        if matches:
            declared: list[tuple[str, str]] = []
            for idx, match in enumerate(matches):
                name = str(match.group(1) or "")
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                declared.append((name, text[match.end():end]))
            sorry_names = [name for name, body in declared if re.search(r"(?<![A-Za-z0-9_'])sorry(?![A-Za-z0-9_'])", body)]
            candidates = sorry_names or [name for name, _ in declared]
            if len(candidates) == 1:
                return candidates[0]
            row_matches = [name for name in candidates if name and (name in row_id or name.split(".")[-1] in row_id)]
            if row_matches:
                return sorted(row_matches, key=lambda x: (-len(x), x))[0]
    parts = str(row_id or "").split("_", 2)
    return parts[2] if len(parts) == 3 and parts[2] else str(row_id or "")


def _probe_row_context(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in (payload.get("corpus"), DEFAULT_C_SUPPLY_ROW_CONTEXT):
        for row in _iter_rows(_read_json(str(path or ""))):
            row_id = _row_id(row)
            if row_id and row_id not in rows:
                rows[row_id] = row
    return rows


def _probe_row_ids(payload: dict[str, Any], scoreboard: dict[str, Any]) -> list[str]:
    out: list[str] = []
    shard = payload.get("family_spec_shard")
    if isinstance(shard, dict):
        if str(shard.get("row_id") or ""):
            out.append(str(shard.get("row_id") or ""))
        raw = shard.get("row_ids") or []
        if isinstance(raw, str):
            out.append(raw)
        elif isinstance(raw, list):
            out.extend(str(x) for x in raw if str(x or ""))
    for rec in scoreboard.get("row_outcomes") or payload.get("row_outcomes") or []:
        if isinstance(rec, dict) and str(rec.get("row_id") or ""):
            out.append(str(rec.get("row_id") or ""))
    return sorted(set(out))


def _c_supply_candidate_rows_from_probe(payload: dict[str, Any], scoreboard: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_id = _probe_row_context(payload)
    out: list[dict[str, Any]] = []
    for row_id in _probe_row_ids(payload, scoreboard):
        row = rows_by_id.get(row_id) or {}
        source_file = str(row.get("source_file") or row.get("sorried_file") or "")
        target_name = str(row.get("target_theorem_name") or "")
        if not target_name:
            target_name = _target_theorem_name_from_source(source_file, row_id)
        out.append({
            "row_id": row_id,
            "source_file": source_file,
            "target_theorem_name": target_name,
            "matched_features": [str(payload.get("family") or "")],
            "template_design_rows": [],
            "static_exit": "tested_no_positive_signal",
        })
    return out


def _governance_summary(root: str) -> dict[str, Any]:
    base = Path(root)
    out = {
        "closed_candidate_count": 0,
        "missing_governance_count": 0,
        "ratified_count": 0,
        "governance_reason_counts": {},
        "examples": [],
    }
    rows = sorted((base / "rows").glob("*.json")) if root else []
    for path in rows:
        try:
            obj = json.loads(path.read_text(errors="ignore"))
        except json.JSONDecodeError:
            continue
        for rec in obj.get("results") or []:
            if not isinstance(rec, dict) or not rec.get("closed"):
                continue
            out["closed_candidate_count"] += 1
            governance = rec.get("governance")
            if not isinstance(governance, dict) or not governance:
                out["missing_governance_count"] += 1
                reason = "missing_governance"
            else:
                reason = str(governance.get("reason") or governance.get("verdict") or "governance_unknown")
                if governance.get("verdict") == "closure":
                    out["ratified_count"] += 1
            out["governance_reason_counts"][reason] = int(out["governance_reason_counts"].get(reason, 0)) + 1
            if len(out["examples"]) < 5:
                out["examples"].append({
                    "row_result_path": str(path),
                    "candidate": rec.get("candidate"),
                    "action_family": rec.get("action_family"),
                    "governance": governance if isinstance(governance, dict) else None,
                })
    return out



NO_POSITIVE_OUTCOMES = {
    "exact_gap_candidate",
    "valid_falsifier_candidate",
    "tested_hold",
    "retired",
    "repair_attempt",
}


def _compact_row_context(payload: dict[str, Any]) -> dict[str, Any]:
    exit_contract = payload.get("exit_contract")
    if not isinstance(exit_contract, dict):
        exit_contract = {}
    return {
        "packet": payload.get("packet"),
        "root": payload.get("root"),
        "scoreboard": payload.get("scoreboard"),
        "static_filter": payload.get("static_filter"),
        "credit_boundary": payload.get("credit_boundary") or exit_contract.get("credit_boundary"),
        "expected_exit": payload.get("expected_exit") or exit_contract.get("expected_exit"),
        "negative_control": payload.get("negative_control") or exit_contract.get("negative_control"),
    }


def _scoreboard_counts(scoreboard: dict[str, Any]) -> dict[str, int]:
    keys = (
        "ratified_closure_count",
        "exact_gap_candidate_count",
        "valid_falsifier_count",
        "negative_control_fail_count",
        "negative_control_unexpected_pass_count",
        "negative_control_invalid_fail_count",
        "compile_candidate_count",
        "completed",
    )
    return {key: _int_count(scoreboard, key) for key in keys}


def _tail(value: Any, limit: int = 900) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def _probe_failure_evidence(payload: dict[str, Any], scoreboard: dict[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
    """Compact failed-candidate evidence for the next repair worker.

    Aggregate counts tell the factory that a row did not convert; they do not
    tell the next worker what to repair. The evidence kept here is deliberately
    bounded and non-credit-bearing: candidate id, action family, error class,
    and Lean/REPL tails from row artifacts under the probe root.
    """
    root = Path(str(payload.get("root") or ""))
    if not root:
        return []
    row_ids = set(_probe_row_ids(payload, scoreboard))
    out: list[dict[str, Any]] = []
    for path in sorted((root / "rows").glob("*.json")):
        if len(out) >= limit:
            break
        obj = _read_json(str(path))
        row_id = str(obj.get("row_id") or "")
        if row_ids and row_id and row_id not in row_ids:
            continue
        for rec in obj.get("results") or []:
            if len(out) >= limit:
                break
            if not isinstance(rec, dict) or rec.get("closed"):
                continue
            repl_errors = rec.get("repl_errors") if isinstance(rec.get("repl_errors"), list) else []
            out.append({
                "row_id": row_id or rec.get("row_id"),
                "candidate": rec.get("candidate"),
                "action_family": rec.get("action_family"),
                "error_class": rec.get("error_class"),
                "driver_path": rec.get("driver_path"),
                "body_tail": _tail(rec.get("body"), 500),
                "stdout_tail": _tail(rec.get("stdout_tail"), 900),
                "stderr_tail": _tail(rec.get("stderr_tail"), 500),
                "repl_error_tail": _tail((repl_errors[0] or {}).get("data") if repl_errors else "", 900),
            })
    return out


def _no_positive_learning_contract(
    row: sqlite3.Row,
    payload: dict[str, Any],
    scoreboard: dict[str, Any],
    *,
    exit_kind: str,
    probe_lane: str,
    outcome_class: str,
    followup_kind: str,
    reason: str,
) -> dict[str, Any]:
    if outcome_class not in NO_POSITIVE_OUTCOMES:
        raise ValueError(f"invalid no-positive outcome_class: {outcome_class}")
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    exit_contract = payload.get("exit_contract")
    if not isinstance(exit_contract, dict):
        exit_contract = {}
    replay_bits = [
        family,
        str(probe_lane),
        str(payload.get("packet") or ""),
        str(payload.get("static_filter") or ""),
        str(exit_contract.get("positive_target") or exit_contract.get("target") or ""),
        str(exit_contract.get("negative_control") or payload.get("negative_control") or ""),
    ]
    return {
        "schema": "leanmill-no-positive-learning-contract-v1",
        "generated_at_epoch": _now(),
        "source_probe_work_id": probe_work_id,
        "family": family,
        "probe_lane": probe_lane,
        "source_exit_kind": exit_kind,
        "outcome_class": outcome_class,
        "followup_kind": followup_kind,
        "reason": reason,
        "credit_boundary": "no proof credit; routing/anti-replay evidence only until a future governed artifact is ratified",
        "required_resolution": [
            "repair_attempt",
            "exact_gap_candidate",
            "valid_falsifier_candidate",
            "tested_hold",
            "retired",
        ],
        "anti_template_candidate": {
            "schema": "leanmill-anti-template-candidate-v1",
            "forbidden_replay_signature": "|".join(replay_bits),
            "failed_route": {
                "family": family,
                "probe_lane": probe_lane,
                "exit_kind": exit_kind,
                "scoreboard_counts": _scoreboard_counts({**scoreboard, **payload}),
                "failure_evidence": _probe_failure_evidence(payload, scoreboard),
            },
            "do_not_repeat_without": [
                "new_family_template",
                "new_source_binding",
                "new_negative_control",
                "new_static_failure_evidence",
                "explicit_regression_lane",
            ],
            "not_a_negative_result_for": [
                "the family in general",
                "the target theorem in general",
                "Path C in general",
            ],
        },
        "row_context": _compact_row_context(payload),
    }

def _regovernance_payload(row: sqlite3.Row, payload: dict[str, Any], scoreboard: dict[str, Any], governance_summary: dict[str, Any]) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    root = str(payload.get("root") or "")
    retry_root = f"{root}_regovern_{int(row['updated_at'])}" if root else f"/tmp/rung1/leanmill_24x7_learning/regovern_{_slug(probe_work_id)}"
    return {
        "work_id": f"post_probe_regovern:{_slug(probe_work_id)}",
        "family": family,
        "probe_lane": str(payload.get("probe_lane") or "family_spec"),
        "governance_required": True,
        "govern_winners": True,
        "no_cache": True,
        "warm_repl_inline": bool(payload.get("warm_repl_inline")),
        "packet": payload.get("packet"),
        "root": retry_root,
        "corpus": payload.get("corpus"),
        "static_filter": payload.get("static_filter"),
        "scoreboard": f"{retry_root}/scoreboard.json",
        "limit": payload.get("limit"),
        "max_candidates": payload.get("max_candidates", 1),
        "max_actions": payload.get("max_actions", 1),
        "timeout": payload.get("timeout"),
        "test_wall_timeout": payload.get("test_wall_timeout"),
        "command_timeout_s": payload.get("command_timeout_s"),
        "backend": payload.get("backend"),
        "cache_dir": payload.get("cache_dir"),
        "lean_slot_lock": payload.get("lean_slot_lock"),
        "parent_probe_work_id": probe_work_id,
        "parent_scoreboard": payload.get("scoreboard"),
        "rescue_reason": "compile_candidate_missing_governance",
        "governance_summary": governance_summary,
        "credit_boundary": payload.get("credit_boundary"),
        "exit_contract": payload.get("exit_contract"),
        "expected_exit": "ratified_closure_or_typed_governance_rejection",
    }


def _needs_governance_audit_residual(governance_summary: dict[str, Any]) -> bool:
    if int(governance_summary.get("closed_candidate_count") or 0) <= 0:
        return False
    if int(governance_summary.get("ratified_count") or 0) > 0:
        return False
    if int(governance_summary.get("missing_governance_count") or 0) > 0:
        return False
    reasons = {str(k): int(v or 0) for k, v in (governance_summary.get("governance_reason_counts") or {}).items()}
    return any(k not in {"", "closure"} and v > 0 for k, v in reasons.items())


def _governance_audit_payload(row: sqlite3.Row, payload: dict[str, Any], scoreboard: dict[str, Any], *, runtime: str, governance_summary: dict[str, Any]) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    root = str(payload.get("root") or "")
    work_id = f"post_probe_governance_audit:{_slug(probe_work_id)}"
    task = (
        "A compile-positive family-spec probe was refused by governance. Do not treat this as a template "
        "no-signal case and do not claim proof value. Diagnose the governance audit refusal and emit one "
        "bounded artifact: governance_audit_residual, operator_required, retired, exact_gap_candidate, or valid_falsifier. "
        "If the verifier is correct, explain the typed rejection/residual. If the verifier is broken, propose the "
        "minimal code fix plus self-test; do not edit scoreboards, registries, research logs, or governance receipts."
    )
    return {
        "work_id": work_id,
        "runtime": runtime,
        "agent_id": f"leanmill_{runtime}_governance_audit_residual",
        "station": "governance_gate",
        "family": family,
        "task": task,
        "expected_exit": "governance_audit_residual",
        "allowed_paths": [
            "scripts/public/control/authoritative_axioms.py",
            "scripts/public/control/leanmill/search/repair_canary_drain.py",
            "scripts/public/control/leanmill/post_probe_triage.py",
            "/tmp/rung1",
        ],
        "requires_negative_control": False,
        "proof_affecting": False,
        "max_iterations": 3,
        "max_wall_time_s": 1200,
        "context": {
            "probe_work_id": probe_work_id,
            "probe_lane": payload.get("probe_lane"),
            "packet": payload.get("packet"),
            "scoreboard": payload.get("scoreboard"),
            "root": root,
            "scoreboard_summary": scoreboard,
            "governance_summary": governance_summary,
            "exit_contract": payload.get("exit_contract"),
            "credit_boundary": "no proof credit unless a future probe receives governance verdict closure",
        },
    }


def _family_spec_negative_control_repair_payload(
    row: sqlite3.Row,
    payload: dict[str, Any],
    scoreboard: dict[str, Any],
    *,
    runtime: str,
    no_positive_learning_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    shard = payload.get("family_spec_shard") or {}
    row_ids: list[str] = []
    if isinstance(shard, dict):
        if str(shard.get("row_id") or ""):
            row_ids.append(str(shard.get("row_id") or ""))
        raw_rows = shard.get("row_ids") or []
        if isinstance(raw_rows, str):
            row_ids.append(raw_rows)
        elif isinstance(raw_rows, list):
            row_ids.extend(str(x) for x in raw_rows if str(x or ""))
    row_id = str(payload.get("row_id") or payload.get("target_row_id") or "")
    if row_id:
        row_ids.append(row_id)
    row_ids = sorted(set(row_ids))
    target_path = f"{DEFAULT_FAMILY_SPEC_DIR}/{family}.yaml"
    work_id = f"post_probe_family_spec_negative_control_repair:{_slug(probe_work_id)}"
    task = (
        "A family-spec probe produced invalid negative-control failures. This is a family-spec template bug, "
        "not a theorem result and not proof credit. Edit only the target repair-family YAML. Repair or retire the "
        "negative_control templates for the listed rows so their failure tests the family-specific ingredient rather "
        "than Lean syntax, notation, missing names, bad binders, or malformed elaboration shape. Preserve paired "
        "positive+negative rows; do not weaken credit boundaries; do not edit scoreboards, registries, research logs, "
        "or governance receipts. If no safe YAML repair is possible, emit terminal JSON with exit_kind operator_required "
        "or retired plus attempted_routes and blocked_edge. "
        f"Target YAML: {target_path}. Rows: {json.dumps(row_ids)}. Scoreboard summary: {json.dumps(scoreboard, sort_keys=True)}"
    )
    return {
        "work_id": work_id,
        "runtime": runtime,
        "agent_id": f"leanmill_{runtime}_family_spec_negative_control_repair",
        "station": "repair_registry",
        "family": family,
        "task": task,
        "expected_exit": "family_spec_patch",
        "allowed_paths": [target_path, "/tmp/rung1"],
        "requires_negative_control": False,
        "proof_affecting": False,
        "max_iterations": 3,
        "max_wall_time_s": 1200,
        "family_spec_patch_target": target_path,
        "family_spec_patch_mode": "repair_invalid_negative_control",
        "invalid_negative_control_probe_work_id": probe_work_id,
        "invalid_negative_control_scoreboard": scoreboard,
        "invalid_negative_control_row_ids": row_ids,
        "post_probe_no_positive_learning_contract": no_positive_learning_contract,
        "replenish_group": f"family_spec_negative_control_repair:{family}",
    }


def _agent_repair_payload(
    row: sqlite3.Row,
    payload: dict[str, Any],
    scoreboard: dict[str, Any],
    *,
    runtime: str,
    no_positive_learning_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    packet = str(payload.get("packet") or "")
    score_path = str(payload.get("scoreboard") or "")
    root = str(payload.get("root") or "")
    target_path = f"{DEFAULT_FAMILY_SPEC_DIR}/{family}.yaml"
    candidate_rows = _c_supply_candidate_rows_from_probe(payload, scoreboard)
    candidate_row_ids = [str(r.get("row_id") or "") for r in candidate_rows if str(r.get("row_id") or "")]
    source_demand = {
        "family": family,
        "recommended_action": "repair_existing_family_spec_positive_templates",
        "source_query_intent": "post_probe_family_spec_positive_repair",
        "recent_probe_feedback": [{
            "source_probe_work_id": probe_work_id,
            "exit_kind": _exit_kind({**scoreboard, **payload}),
            "scoreboard_counts": _scoreboard_counts({**scoreboard, **payload}),
            "packet": packet,
            "scoreboard": score_path,
            "root": root,
            "row_outcomes": scoreboard.get("row_outcomes") or payload.get("row_outcomes") or [],
            "failure_evidence": _probe_failure_evidence(payload, scoreboard),
            "no_positive_learning_contract": no_positive_learning_contract,
        }],
    }
    contract_id = f"leanmill-family-spec-positive-repair:{family}:{_slug(probe_work_id)}"
    operator_contract = operator_contracts.c_supply_template_backfill_contract(
        family=family,
        candidate_rows=candidate_rows,
        target_path=target_path,
        source_demand=source_demand,
        contract_id=contract_id,
    )
    task = (
        "Patch the target LeanMill repair-family YAML only. A family-spec proof probe had matched negative "
        "controls but zero positive compile candidates, so repair the existing positive templates into concrete "
        "family-specific Lean action bodies, or retire/operator_required with attempted_routes and blocked_edge. "
        "Do not update scoreboards, registries, research logs, governance receipts, or Python. Preserve or strengthen "
        "matched negative controls for every row you touch. Follow the compact operator_contract exactly; it is the "
        "program counter and evidence contract for this task. Treat recent_probe_feedback as causal feedback: do not "
        "replay the same non-useful positive route without a concrete repair. "
        f"Target YAML: {target_path}. Probe packet: {packet}. Candidate rows: {json.dumps(candidate_rows, sort_keys=True)}"
    )
    work_id = f"post_probe_family_spec_positive_repair:{_slug(probe_work_id)}"
    return {
        "work_id": work_id,
        "runtime": runtime,
        "agent_id": f"leanmill_{runtime}_family_spec_positive_repair",
        "station": "repair_registry",
        "family": family,
        "task": task,
        "operator_contract": operator_contract,
        "expected_exit": "family_spec_patch",
        "allowed_paths": [target_path, "/tmp/rung1"],
        "allowed_read_paths": [target_path, "/tmp/rung1"],
        "allowed_write_paths": [target_path],
        "negative_control": "Every repaired positive template must retain a matched negative_control template for the same row that fails when the family-specific bridge/direction/source ingredient is removed or reversed.",
        "requires_negative_control": True,
        "proof_affecting": False,
        "max_iterations": 3,
        "max_wall_time_s": 1200,
        "max_family_spec_feedback_retries": 1,
        "family_spec_patch_target": target_path,
        "family_spec_patch_mode": "family_spec_positive_repair",
        "c_supply_selection": DEFAULT_C_SUPPLY_SELECTION,
        "c_supply_checkpoint": DEFAULT_C_SUPPLY_CHECKPOINT,
        "c_supply_row_context": DEFAULT_C_SUPPLY_ROW_CONTEXT,
        "c_supply_spec_dir": DEFAULT_FAMILY_SPEC_DIR,
        "c_supply_candidate_rows": candidate_row_ids,
        "c_supply_candidates": candidate_rows,
        "c_supply_source_demand": source_demand,
        "recent_probe_feedback": source_demand["recent_probe_feedback"],
        "replenish_group": f"family_spec_positive_repair:{family}",
        "context": {
            "probe_work_id": probe_work_id,
            "probe_lane": payload.get("probe_lane"),
            "packet": packet,
            "scoreboard": score_path,
            "root": root,
            "scoreboard_summary": scoreboard,
            "governance_summary": _governance_summary(root),
            "exit_contract": payload.get("exit_contract"),
            "no_positive_learning_contract": no_positive_learning_contract,
        },
    }


def _gap_proposal_payload(
    row: sqlite3.Row,
    payload: dict[str, Any],
    scoreboard: dict[str, Any],
    *,
    no_positive_learning_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    work_id = f"post_probe_gap_triage:{_slug(probe_work_id)}"
    return {
        "work_id": work_id,
        "station": "residual_curriculum",
        "family": family,
        "proposal_type": "exact_gap",
        "expected_outcome": "exact_gap",
        "credit_type": "none",
        "force_credit_type": "none",
        "allowed_proposal_types": ["exact_gap", "falsifier", "decomposition"],
        "context": {
            "probe_work_id": probe_work_id,
            "probe_lane": payload.get("probe_lane"),
            "packet": payload.get("packet"),
            "scoreboard": payload.get("scoreboard"),
            "root": payload.get("root"),
            "scoreboard_summary": scoreboard,
            "exit_contract": payload.get("exit_contract"),
            "no_positive_learning_contract": no_positive_learning_contract,
            "instruction": (
                "The probe produced no closure. Produce a precise exact_gap/falsifier/decomposition proposal "
                "that names the missing theorem/interface, the next executable check, and the retire condition. "
                "Do not ask for more generic source binding."
            ),
        },
    }


def _safety_payload(row: sqlite3.Row, payload: dict[str, Any], scoreboard: dict[str, Any]) -> dict[str, Any]:
    family = str(row["family"] or payload.get("family") or "unknown_family")
    probe_work_id = str(row["work_id"])
    return {
        "work_id": f"post_probe_safety:{_slug(probe_work_id)}",
        "station": "governance_gate",
        "family": family,
        "expected_exit": "operator_required",
        "exit_kind": "operator_required",
        "reason": "negative_control_unexpected_pass_blocks_credit",
        "probe_work_id": probe_work_id,
        "scoreboard_summary": scoreboard,
    }



def _clean_positive_repair_rows(
    *,
    spec_dir: str,
    family: str,
    candidate_row_ids: list[str],
    target_context_paths: list[str | Path] | None = None,
) -> list[str]:
    wanted = {str(row_id) for row_id in candidate_row_ids if str(row_id)}
    if not family or not wanted:
        return []
    target_names_by_row = family_specs.target_names_by_row_from_context_paths(target_context_paths or [])
    specs = family_specs.usable_specs(
        family_specs.load_specs(spec_dir),
        target_names_by_row=target_names_by_row,
    )
    for spec in specs:
        if str(spec.get("family") or "") != family:
            continue
        groups: dict[str, set[str]] = {}
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if row_id in wanted:
                groups.setdefault(row_id, set()).add(str(template.get("test_kind") or ""))
        return sorted(row_id for row_id, kinds in groups.items() if {"positive", "negative_control"}.issubset(kinds))
    return []


def _positive_repair_activation_reconciliation(args: argparse.Namespace, cx: Any, *, remaining_budget: int) -> dict[str, Any]:
    if remaining_budget <= 0:
        return {"inspected": 0, "activated": 0, "skipped": [], "records": []}
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind='agent_repair_task'
          AND status IN ('failed', 'done')
          AND expected_exit='family_spec_patch'
          AND updated_at >= ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (max(0, int(args.since_epoch)), max(1, int(args.limit))),
    ).fetchall()
    root = Path(DEFAULT_FAMILY_SPEC_ACTIVATION_DIR)
    root.mkdir(parents=True, exist_ok=True)
    inspected = 0
    activated = 0
    skipped: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for row in rows:
        payload = _payload(row)
        if str(payload.get("family_spec_patch_mode") or "") != FAMILY_SPEC_POSITIVE_REPAIR_MODE:
            continue
        inspected += 1
        canonical_field = _family_spec_positive_repair_handoff_field(args)
        canonical_receipt = payload.get(canonical_field) if isinstance(payload.get(canonical_field), dict) else None
        reconciliation_receipt = (
            payload.get("family_spec_positive_repair_activation_reconciliation")
            if isinstance(payload.get("family_spec_positive_repair_activation_reconciliation"), dict)
            else None
        )
        if canonical_receipt:
            skipped.append({"work_id": row["work_id"], "reason": "already_activated_or_reconciled"})
            continue
        if reconciliation_receipt:
            if args.mark:
                work_queue.update_status(
                    cx,
                    work_id=str(row["work_id"]),
                    status=str(row["status"]),
                    payload_update={canonical_field: reconciliation_receipt},
                )
            skipped.append({"work_id": row["work_id"], "reason": "legacy_reconciliation_receipt_promoted_to_canonical"})
            continue
        family = str(row["family"] or payload.get("family") or "")
        candidate_row_ids = [str(x) for x in (payload.get("c_supply_candidate_rows") or []) if str(x)]
        if not candidate_row_ids:
            for cand in payload.get("c_supply_candidates") or []:
                if isinstance(cand, dict) and cand.get("row_id"):
                    candidate_row_ids.append(str(cand.get("row_id")))
        clean_rows = _clean_positive_repair_rows(
            spec_dir=DEFAULT_FAMILY_SPEC_DIR,
            family=family,
            candidate_row_ids=sorted(set(candidate_row_ids)),
            target_context_paths=[DEFAULT_C_SUPPLY_ROW_CONTEXT],
        )
        if not clean_rows:
            receipt = _blocked_positive_repair_handoff_receipt(
                work_id=str(row["work_id"]),
                family=family,
                reason="current_spec_has_no_clean_candidate_pair",
                candidate_rows=sorted(set(candidate_row_ids)),
            )
            if args.mark:
                work_queue.update_status(
                    cx,
                    work_id=str(row["work_id"]),
                    status=str(row["status"]),
                    payload_update={
                        canonical_field: receipt,
                        "family_spec_positive_repair_activation_reconciliation": receipt,
                    },
                )
            records.append(receipt)
            skipped.append({"work_id": row["work_id"], "reason": "current_spec_has_no_clean_candidate_pair", "family": family, "candidate_rows": sorted(set(candidate_row_ids))})
            continue
        if activated >= remaining_budget:
            skipped.append({"work_id": row["work_id"], "reason": "activation_budget_exhausted"})
            continue
        stamp = f"{_now()}_{_slug(str(row['work_id']))}"
        selection_path = root / f"{stamp}.selection.json"
        out_path = root / f"{stamp}.seed_plan.json"
        out_dir = root / f"queued_work_{stamp}"
        selection = {
            "schema": "leanmill-family-spec-positive-repair-activation-reconciliation-selection-v1",
            "source_work_id": str(row["work_id"]),
            "selected_rows": [
                {"row_id": row_id, "matched_families": [family], "activation_source": "family_spec_positive_repair_reconciliation"}
                for row_id in clean_rows
            ],
            "credit_boundary": _handoff_credit_boundary(),
        }
        selection_path.write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n")
        cmd = [
            sys.executable,
            "scripts/public/control/leanmill/learning_work_seeder.py",
            "--family-spec-selection", str(selection_path),
            "--family-spec-dir", DEFAULT_FAMILY_SPEC_DIR,
            "--row-context", DEFAULT_C_SUPPLY_ROW_CONTEXT,
            "--out", str(out_path),
            "--out-dir", str(out_dir),
            "--queue-db", str(args.queue_db),
            "--events", str(args.events),
            "--run-id", f"family_spec_positive_repair_reconcile_{_now()}",
            "--max-family-spec-probe-families", "1",
            "--max-probe-families", "0",
            "--max-proposal-jobs", "0",
            "--max-agent-jobs", "0",
            "--max-family-spec-repair-jobs", "0",
            "--max-family-spec-generality-jobs", "0",
            "--max-total-jobs", "16",
            "--max-enqueued", "16",
            "--max-tests-per-probe", "4",
            "--family-spec-probe-rows-per-work-item", "1",
            "--enqueue",
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180, check=False)
        plan = _read_json(out_path) or {}
        receipt = {
            "schema": handoff_contract.REPAIR_RECEIPT_SCHEMA,
            "status": "pass" if proc.returncode == 0 else "fail",
            "source_work_id": str(row["work_id"]),
            "work_id": str(row["work_id"]),
            "family": family,
            "family_spec_patch_mode": FAMILY_SPEC_POSITIVE_REPAIR_MODE,
            "selected_rows": clean_rows,
            "selected_row_count": len(clean_rows),
            "selection": str(selection_path),
            "seed_plan": str(out_path),
            "enqueued": int(plan.get("enqueued") or 0) if isinstance(plan, dict) else 0,
            "job_count": int(plan.get("job_count") or 0) if isinstance(plan, dict) else 0,
            "skip_counts": plan.get("skip_counts") if isinstance(plan, dict) else {},
            "returncode": proc.returncode,
            "reason": "" if proc.returncode == 0 else "family_spec_positive_repair_activation_seed_failed",
            "stdout_tail": (proc.stdout or "")[-1000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
            "credit_boundary": selection["credit_boundary"],
        }
        records.append(receipt)
        work_queue.append_event(args.events, {
            "event_type": "family_spec_positive_repair_activation_reconciled",
            "work_id": str(row["work_id"]),
            "payload": receipt,
            "artifact_paths": [str(selection_path), str(out_path)],
        })
        if args.mark and proc.returncode == 0:
            work_queue.update_status(
                cx,
                work_id=str(row["work_id"]),
                status=str(row["status"]),
                payload_update={
                    canonical_field: receipt,
                    "family_spec_positive_repair_activation_reconciliation": receipt,
                },
            )
        if proc.returncode == 0 and int(receipt.get("enqueued") or 0) > 0:
            activated += int(receipt.get("enqueued") or 0)
    return {"inspected": inspected, "activated": activated, "skipped": skipped[:20], "records": records[:20]}


def triage(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    regovernance_reprioritized = (
        _rebalance_open_regovernance_priorities(cx, int(args.regovernance_priority))
        if bool(getattr(args, "rebalance_open_regovernance_priorities", True))
        else 0
    )
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind IN ('repair_canary_probe', 'proof_probe')
          AND status IN ('done', 'failed')
          AND updated_at >= ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (max(0, int(args.since_epoch)), max(1, int(args.limit))),
    ).fetchall()
    inspected = 0
    enqueued: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    no_positive_contract_count = 0
    no_positive_backfilled_count = 0
    no_positive_outcome_counts: dict[str, int] = {}
    marked = 0
    for row in rows:
        payload = _payload(row)
        lane = str(payload.get("probe_lane") or "legacy")
        score_path = str(payload.get("scoreboard") or "")
        scoreboard = _scoreboard(score_path)
        merged = {**scoreboard, **payload}
        exit_kind = _exit_kind(merged)
        governance_summary: dict[str, Any] = {}
        if payload.get("post_probe_triaged_at_epoch"):
            if exit_kind == "invalid_negative_control" and lane == "family_spec":
                repair_work_id = f"post_probe_family_spec_negative_control_repair:{_slug(str(row['work_id']))}"
                if not _work_exists(cx, repair_work_id):
                    no_positive_contract = _no_positive_learning_contract(
                        row, payload, scoreboard,
                        exit_kind=exit_kind, probe_lane=lane, outcome_class="repair_attempt",
                        followup_kind="agent_repair_task", reason="expost_family_spec_probe_invalid_negative_control",
                    )
                    followup = _family_spec_negative_control_repair_payload(
                        row, payload, scoreboard, runtime=args.agent_runtime,
                        no_positive_learning_contract=no_positive_contract,
                    )
                    followup_record = {
                        "work_id": followup["work_id"],
                        "kind": "agent_repair_task",
                        "source_probe_work_id": row["work_id"],
                        "exit_kind": exit_kind,
                        "probe_lane": lane,
                        "backfill": "invalid_negative_control",
                    }
                    if args.enqueue:
                        work_id = work_queue.enqueue(
                            cx, kind="agent_repair_task", priority=int(args.agent_priority) + 20,
                            payload=followup, max_attempts=1,
                        )
                        work_queue.append_event(args.events, {
                            "event_type": "post_probe_triage_enqueued",
                            "work_id": work_id,
                            "payload": {
                                "source_probe_work_id": row["work_id"],
                                "kind": "agent_repair_task",
                                "exit_kind": exit_kind,
                                "probe_lane": lane,
                                "backfill": "invalid_negative_control",
                            },
                        })
                        enqueued.append(followup_record)
                    if args.mark:
                        work_queue.update_status(
                            cx,
                            work_id=str(row["work_id"]),
                            status=str(row["status"]),
                            payload_update={
                                "post_probe_no_positive_learning_contract": no_positive_contract,
                                "post_probe_invalid_negative_control_backfilled_at_epoch": _now(),
                                "post_probe_triage_followups": [followup_record],
                            },
                        )
                    no_positive_backfilled_count += 1
                    no_positive_outcome_counts["repair_attempt"] = int(no_positive_outcome_counts.get("repair_attempt", 0)) + 1
            if (
                isinstance(payload.get("post_probe_no_positive_learning_contract"), dict)
                and exit_kind in {"tested_no_positive_signal", "tested_probe_no_signal", "probe_failed"}
                and lane == "family_spec"
            ):
                followup = _agent_repair_payload(
                    row, payload, scoreboard, runtime=args.agent_runtime,
                    no_positive_learning_contract=payload.get("post_probe_no_positive_learning_contract"),
                )
                if not _work_exists(cx, str(followup.get("work_id") or "")):
                    followup_record = {
                        "work_id": followup["work_id"],
                        "kind": "agent_repair_task",
                        "source_probe_work_id": row["work_id"],
                        "exit_kind": exit_kind,
                        "probe_lane": lane,
                        "backfill": "family_spec_positive_repair",
                    }
                    if args.enqueue:
                        work_id = work_queue.enqueue(
                            cx, kind="agent_repair_task", priority=int(args.agent_priority),
                            payload=followup, max_attempts=2,
                        )
                        work_queue.append_event(args.events, {
                            "event_type": "post_probe_triage_enqueued",
                            "work_id": work_id,
                            "payload": {
                                "source_probe_work_id": row["work_id"],
                                "kind": "agent_repair_task",
                                "exit_kind": exit_kind,
                                "probe_lane": lane,
                                "backfill": "family_spec_positive_repair",
                            },
                        })
                        enqueued.append(followup_record)
                    if args.mark:
                        existing_followups = payload.get("post_probe_triage_followups") if isinstance(payload.get("post_probe_triage_followups"), list) else []
                        work_queue.update_status(
                            cx,
                            work_id=str(row["work_id"]),
                            status=str(row["status"]),
                            payload_update={
                                "post_probe_positive_repair_backfilled_at_epoch": _now(),
                                "post_probe_triage_followups": [*existing_followups, followup_record],
                            },
                        )
                        legacy_work_id = f"post_probe_agent_repair:{_slug(str(row['work_id']))}"
                        legacy = cx.execute("SELECT status FROM work_items WHERE work_id=?", (legacy_work_id,)).fetchone()
                        if legacy and str(legacy["status"] or "") == "queued":
                            work_queue.update_status(
                                cx,
                                work_id=legacy_work_id,
                                status="retired",
                                payload_update={
                                    "retired_by": "post_probe_positive_repair_backfill",
                                    "retired_reason": "superseded_by_structured_family_spec_positive_repair",
                                    "replacement_work_id": followup["work_id"],
                                },
                            )
                    no_positive_backfilled_count += 1
                    no_positive_outcome_counts["repair_attempt"] = int(no_positive_outcome_counts.get("repair_attempt", 0)) + 1
            if (
                not isinstance(payload.get("post_probe_no_positive_learning_contract"), dict)
                and exit_kind in {"tested_no_positive_signal", "tested_probe_no_signal", "probe_failed"}
            ):
                if lane == "family_spec":
                    outcome_class, followup_kind, reason = "repair_attempt", "already_triaged", "expost_family_spec_probe_no_positive_signal"
                elif lane == "source_binding" and not args.triage_source_binding:
                    outcome_class, followup_kind, reason = "tested_hold", "already_triaged", "expost_source_binding_triage_paused_zero_governed_value"
                else:
                    outcome_class, followup_kind, reason = "exact_gap_candidate", "already_triaged", "expost_probe_no_positive_requires_gap_falsifier_or_decomposition"
                contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class=outcome_class,
                    followup_kind=followup_kind, reason=reason,
                )
                if args.mark:
                    work_queue.update_status(
                        cx,
                        work_id=str(row["work_id"]),
                        status=str(row["status"]),
                        payload_update={"post_probe_no_positive_learning_contract": contract},
                    )
                no_positive_backfilled_count += 1
                no_positive_outcome_counts[outcome_class] = int(no_positive_outcome_counts.get(outcome_class, 0)) + 1
            if exit_kind != "compile_candidate_needs_governance":
                continue
            governance_summary = _governance_summary(str(payload.get("root") or ""))
            regovern_work_id = f"post_probe_regovern:{_slug(str(row['work_id']))}"
            if int(governance_summary.get("missing_governance_count") or 0) <= 0 or _work_exists(cx, regovern_work_id):
                continue
        if args.regovernance_only:
            if exit_kind != "compile_candidate_needs_governance":
                continue
            if not governance_summary:
                governance_summary = _governance_summary(str(payload.get("root") or ""))
            regovern_work_id = f"post_probe_regovern:{_slug(str(row['work_id']))}"
            if int(governance_summary.get("missing_governance_count") or 0) <= 0 or _work_exists(cx, regovern_work_id):
                continue
        inspected += 1
        followup: dict[str, Any] | None = None
        kind = ""
        priority = 0
        max_attempts = 1
        no_positive_contract: dict[str, Any] | None = None
        if exit_kind == "failed_negative_control":
            kind = "gm_operator_task"
            priority = int(args.safety_priority)
            followup = _safety_payload(row, payload, scoreboard)
        elif exit_kind == "invalid_negative_control":
            if lane == "family_spec":
                kind = "agent_repair_task"
                priority = int(args.agent_priority) + 20
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="repair_attempt",
                    followup_kind=kind, reason="family_spec_probe_invalid_negative_control",
                )
                followup = _family_spec_negative_control_repair_payload(
                    row, payload, scoreboard, runtime=args.agent_runtime,
                    no_positive_learning_contract=no_positive_contract,
                )
            else:
                kind = "gm_operator_task"
                priority = int(args.safety_priority)
                followup = _safety_payload(row, payload, scoreboard)
        elif exit_kind == "compile_candidate_needs_governance":
            if not governance_summary:
                governance_summary = _governance_summary(str(payload.get("root") or ""))
            if int(governance_summary.get("missing_governance_count") or 0) > 0:
                kind = "repair_canary_probe"
                priority = int(args.regovernance_priority)
                followup = _regovernance_payload(row, payload, scoreboard, governance_summary)
            elif _needs_governance_audit_residual(governance_summary):
                kind = "agent_repair_task"
                priority = int(args.governance_audit_priority)
                followup = _governance_audit_payload(row, payload, scoreboard, runtime=args.agent_runtime, governance_summary=governance_summary)
            elif lane == "family_spec":
                kind = "agent_repair_task"
                priority = int(args.agent_priority)
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="repair_attempt",
                    followup_kind=kind, reason="compile_candidate_governance_audit_then_repair",
                )
                followup = _agent_repair_payload(row, payload, scoreboard, runtime=args.agent_runtime, no_positive_learning_contract=no_positive_contract)
                max_attempts = 2
            elif lane == "source_binding" and not args.triage_source_binding:
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="tested_hold",
                    followup_kind="held", reason="source_binding_triage_paused_zero_governed_value",
                )
                held.append({"work_id": row["work_id"], "reason": "source_binding_triage_paused_zero_governed_value", "exit_kind": exit_kind, "probe_lane": lane, "no_positive_learning_contract": no_positive_contract})
            else:
                kind = "decomposition_propose"
                priority = int(args.gap_priority)
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="exact_gap_candidate",
                    followup_kind=kind, reason="compile_candidate_requires_gap_or_falsifier_triage",
                )
                followup = _gap_proposal_payload(row, payload, scoreboard, no_positive_learning_contract=no_positive_contract)
        elif exit_kind in {"tested_no_positive_signal", "tested_probe_no_signal", "probe_failed"}:
            if lane == "family_spec":
                kind = "agent_repair_task"
                priority = int(args.agent_priority)
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="repair_attempt",
                    followup_kind=kind, reason="family_spec_probe_no_positive_signal",
                )
                followup = _agent_repair_payload(row, payload, scoreboard, runtime=args.agent_runtime, no_positive_learning_contract=no_positive_contract)
                max_attempts = 2
            elif lane == "source_binding" and not args.triage_source_binding:
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="tested_hold",
                    followup_kind="held", reason="source_binding_triage_paused_zero_governed_value",
                )
                held.append({"work_id": row["work_id"], "reason": "source_binding_triage_paused_zero_governed_value", "exit_kind": exit_kind, "probe_lane": lane, "no_positive_learning_contract": no_positive_contract})
            else:
                kind = "decomposition_propose"
                priority = int(args.gap_priority)
                no_positive_contract = _no_positive_learning_contract(
                    row, payload, scoreboard,
                    exit_kind=exit_kind, probe_lane=lane, outcome_class="exact_gap_candidate",
                    followup_kind=kind, reason="probe_no_positive_requires_gap_falsifier_or_decomposition",
                )
                followup = _gap_proposal_payload(row, payload, scoreboard, no_positive_learning_contract=no_positive_contract)
        elif exit_kind in {"ratified_closure", "exact_gap_candidate", "valid_falsifier"}:
            held.append({"work_id": row["work_id"], "reason": "already_useful_exit", "exit_kind": exit_kind})
        else:
            held.append({"work_id": row["work_id"], "reason": "no_triage_rule", "exit_kind": exit_kind, "probe_lane": lane})
        if followup and kind:
            if len(enqueued) >= max(0, int(args.max_enqueued)):
                held.append({
                    "work_id": row["work_id"],
                    "reason": "post_probe_triage_max_enqueued_reached",
                    "exit_kind": exit_kind,
                    "probe_lane": lane,
                })
                continue
            if args.enqueue:
                work_id = work_queue.enqueue(cx, kind=kind, priority=priority, payload=followup, max_attempts=max_attempts)
                work_queue.append_event(args.events, {
                    "event_type": "post_probe_triage_enqueued",
                    "work_id": work_id,
                    "payload": {
                        "source_probe_work_id": row["work_id"],
                        "kind": kind,
                        "exit_kind": exit_kind,
                        "probe_lane": lane,
                    },
                })
            enqueued.append({"work_id": followup["work_id"], "kind": kind, "source_probe_work_id": row["work_id"], "exit_kind": exit_kind, "probe_lane": lane})
        if no_positive_contract:
            no_positive_contract_count += 1
            outcome = str(no_positive_contract.get("outcome_class") or "unknown")
            no_positive_outcome_counts[outcome] = int(no_positive_outcome_counts.get(outcome, 0)) + 1
        if args.mark:
            mark_update = {
                "post_probe_no_positive_learning_contract": no_positive_contract,
            }
            if not followup or args.enqueue:
                mark_update.update({
                    "post_probe_triaged_at_epoch": _now(),
                    "post_probe_triage_exit_kind": exit_kind,
                    "post_probe_triage_followups": enqueued[-1:] if followup else [],
                })
            work_queue.update_status(
                cx,
                work_id=str(row["work_id"]),
                status=str(row["status"]),
                payload_update=mark_update,
            )
            marked += 1
    activation_reconciliation = _positive_repair_activation_reconciliation(
        args,
        cx,
        remaining_budget=max(0, int(args.max_enqueued) - len(enqueued)),
    )
    out = {
        "schema": "leanmill-post-probe-triage-v1",
        "generated_at_epoch": _now(),
        "inspected": inspected,
        "enqueued_count": len(enqueued),
        "marked_count": marked,
        "held_count": len(held),
        "regovernance_reprioritized_count": regovernance_reprioritized,
        "no_positive_learning_contract_count": no_positive_contract_count,
        "no_positive_backfilled_count": no_positive_backfilled_count,
        "no_positive_outcome_counts": no_positive_outcome_counts,
        "positive_repair_activation_reconciliation": activation_reconciliation,
        "enqueued": enqueued,
        "held": held[:20],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def _self_test() -> int:
    import tempfile

    assert _exit_kind({"negative_control_unexpected_pass_count": 1}) == "failed_negative_control"
    assert _exit_kind({"negative_control_invalid_fail_count": 1, "ratified_closure_count": 1}) == "invalid_negative_control"
    assert _exit_kind({"ratified_closure_count": 1}) == "ratified_closure"
    assert _exit_kind({"compile_candidate_count": 1, "negative_control_fail_count": 1}) == "compile_candidate_needs_governance"
    assert _exit_kind({"negative_control_fail_count": 1}) == "tested_no_positive_signal"
    assert _slug("a/b c") == "a_b_c"
    assert _needs_governance_audit_residual({
        "closed_candidate_count": 1,
        "ratified_count": 0,
        "missing_governance_count": 0,
        "governance_reason_counts": {"injected_audit_errors": 1},
    })
    assert not _needs_governance_audit_residual({
        "closed_candidate_count": 1,
        "ratified_count": 1,
        "missing_governance_count": 0,
        "governance_reason_counts": {"axioms_subset_STD": 1},
    })
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "q.sqlite")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=10, payload={"work_id": "post_probe_regovern:probe:a", "family": "fam"})
        work_queue.enqueue(cx, kind="repair_canary_probe", priority=20, payload={"work_id": "probe:fresh", "family": "fam"})
        assert _rebalance_open_regovernance_priorities(cx, 99) == 1
        row = cx.execute("SELECT priority FROM work_items WHERE work_id='post_probe_regovern:probe:a'").fetchone()
        assert int(row["priority"]) == 99
        events = str(Path(td) / "events.jsonl")
        status = str(Path(td) / "status.json")
        work_queue.record_terminal_item(
            cx,
            kind="repair_canary_probe",
            status="done",
            priority=10,
            payload={
                "work_id": "probe:invalid-negative",
                "family": "fam",
                "probe_lane": "family_spec",
                "negative_control_invalid_fail_count": 1,
                "family_spec_shard": {"row_id": "r-invalid"},
                "packet": "packet.json",
                "scoreboard": "scoreboard.json",
                "exit_contract": {"negative_control": "bad neg"},
            },
        )
        invalid_out = triage(argparse.Namespace(
            queue_db=db, events=events, out=status, since_epoch=0, limit=20, max_enqueued=20,
            agent_runtime="codex", agent_priority=145, gap_priority=135, regovernance_priority=240,
            governance_audit_priority=320, rebalance_open_regovernance_priorities=False,
            triage_source_binding=False, regovernance_only=False,
            enqueue=True, mark=True,
        ))
        assert invalid_out["enqueued_count"] == 1, invalid_out
        invalid_task = cx.execute("SELECT payload_json FROM work_items WHERE work_id LIKE 'post_probe_family_spec_negative_control_repair:%'").fetchone()
        invalid_payload = json.loads(invalid_task["payload_json"])
        assert invalid_payload["expected_exit"] == "family_spec_patch", invalid_payload
        assert invalid_payload["family_spec_patch_mode"] == "repair_invalid_negative_control", invalid_payload
        assert invalid_payload["family_spec_patch_target"].endswith("repair_families/fam.yaml"), invalid_payload
        invalid_parent = cx.execute("SELECT payload_json FROM work_items WHERE work_id='probe:invalid-negative'").fetchone()
        invalid_parent_payload = json.loads(invalid_parent["payload_json"])
        assert invalid_parent_payload["post_probe_triage_exit_kind"] == "invalid_negative_control", invalid_parent_payload

        work_queue.record_terminal_item(
            cx,
            kind="repair_canary_probe",
            status="done",
            priority=10,
            payload={
                "work_id": "probe:old-invalid-negative",
                "family": "fam_old",
                "probe_lane": "family_spec",
                "negative_control_invalid_fail_count": 1,
                "family_spec_shard": {"row_id": "r-old-invalid"},
                "post_probe_triaged_at_epoch": 1,
            },
        )
        old_invalid_out = triage(argparse.Namespace(
            queue_db=db, events=events, out=status, since_epoch=0, limit=20, max_enqueued=20,
            agent_runtime="codex", agent_priority=145, gap_priority=135, regovernance_priority=240,
            governance_audit_priority=320, rebalance_open_regovernance_priorities=False,
            triage_source_binding=False, regovernance_only=False,
            enqueue=True, mark=True,
        ))
        assert old_invalid_out["no_positive_backfilled_count"] == 1, old_invalid_out
        old_invalid_task = cx.execute(
            "SELECT payload_json FROM work_items WHERE work_id='post_probe_family_spec_negative_control_repair:probe:old-invalid-negative'"
        ).fetchone()
        old_invalid_payload = json.loads(old_invalid_task["payload_json"])
        assert old_invalid_payload["family_spec_patch_mode"] == "repair_invalid_negative_control", old_invalid_payload

        work_queue.record_terminal_item(
            cx,
            kind="repair_canary_probe",
            status="done",
            priority=10,
            payload={
                "work_id": "probe:no-positive",
                "family": "fam",
                "probe_lane": "family_spec",
                "negative_control_fail_count": 1,
                "packet": "packet.json",
                "exit_contract": {"negative_control": "neg"},
            },
        )
        out = triage(argparse.Namespace(
            queue_db=db, events=events, out=status, since_epoch=0, limit=20, max_enqueued=20,
            agent_runtime="codex", agent_priority=145, gap_priority=135, regovernance_priority=240,
            governance_audit_priority=320, rebalance_open_regovernance_priorities=False,
            triage_source_binding=False, regovernance_only=False,
            enqueue=True, mark=True,
        ))
        assert out["no_positive_learning_contract_count"] == 1
        assert out["no_positive_outcome_counts"]["repair_attempt"] == 1
        task = cx.execute("SELECT payload_json, max_attempts FROM work_items WHERE work_id='post_probe_family_spec_positive_repair:probe:no-positive'").fetchone()
        task_payload = json.loads(task["payload_json"])
        assert task["max_attempts"] == 2
        assert task_payload["expected_exit"] == "family_spec_patch"
        assert task_payload["family_spec_patch_mode"] == "family_spec_positive_repair"
        assert task_payload["allowed_write_paths"] == [task_payload["family_spec_patch_target"]]
        assert task_payload["operator_contract"]["accepted_residual_class"] == "c_supply_template_backfill"
        contract = task_payload["context"]["no_positive_learning_contract"]
        assert contract["schema"] == "leanmill-no-positive-learning-contract-v1"
        assert contract["anti_template_candidate"]["schema"] == "leanmill-anti-template-candidate-v1"
        parent = cx.execute("SELECT payload_json FROM work_items WHERE work_id='probe:no-positive'").fetchone()
        parent_payload = json.loads(parent["payload_json"])
        assert parent_payload["post_probe_no_positive_learning_contract"]["outcome_class"] == "repair_attempt"
        work_queue.record_terminal_item(
            cx,
            kind="repair_canary_probe",
            status="done",
            priority=10,
            payload={
                "work_id": "probe:old-no-positive",
                "family": "fam",
                "probe_lane": "source_binding",
                "negative_control_fail_count": 1,
                "post_probe_triaged_at_epoch": 1,
            },
        )
        out2 = triage(argparse.Namespace(
            queue_db=db, events=events, out=status, since_epoch=0, limit=20, max_enqueued=20,
            agent_runtime="codex", agent_priority=145, gap_priority=135, regovernance_priority=240,
            governance_audit_priority=320, rebalance_open_regovernance_priorities=False,
            triage_source_binding=False, regovernance_only=False,
            enqueue=False, mark=True,
        ))
        assert out2["no_positive_backfilled_count"] == 1
        old = cx.execute("SELECT payload_json FROM work_items WHERE work_id='probe:old-no-positive'").fetchone()
        old_payload = json.loads(old["payload_json"])
        assert old_payload["post_probe_no_positive_learning_contract"]["outcome_class"] == "tested_hold"
    print("leanmill_post_probe_triage self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--since-epoch", type=int, default=0)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--max-enqueued", type=int, default=20)
    ap.add_argument("--agent-runtime", choices=["codex", "claude"], default="codex")
    ap.add_argument("--agent-priority", type=int, default=145)
    ap.add_argument("--gap-priority", type=int, default=135)
    ap.add_argument("--regovernance-priority", type=int, default=240)
    ap.add_argument("--governance-audit-priority", type=int, default=320)
    ap.add_argument("--safety-priority", type=int, default=1000)
    ap.add_argument("--rebalance-open-regovernance-priorities", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--factory-policy", default="analytics/public/leanmill/dashboard_data/leanmill_factory_policy.json")
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--triage-source-binding", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--regovernance-only", action="store_true", help="Only enqueue deterministic re-governance rescues for compile-positive probes missing governance receipts.")
    ap.add_argument("--enqueue", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--mark", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="post_probe_triage")
    if int(args.safety_priority) == 1000:
        args.safety_priority = priority_value(
            path=args.factory_policy,
            namespace="work_queue",
            key="post_probe_safety_review",
            fallback=1000,
        )
    print(json.dumps(triage(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
