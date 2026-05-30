#!/usr/bin/env python3
"""Prepare a C-discriminating LeanMill benchmark slice.

A C-discriminating row is one where static/public tools have already failed or
not produced a positive signal, repair-family memory is available, and matched
negative controls exist. This script is intentionally a gate: if the pool has no
such rows, it reports the supply gap instead of letting an aggregate benchmark be
misread as a Path-C test.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from ztare.leanmill.contracts import source_family_match
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
    from ztare.leanmill.contracts import source_family_match

import leanmill_family_specs as family_specs
import leanmill_family_spec_probe_signature as probe_signatures
import leanmill_source_materialization as source_materialization
from leanmill_c_supply_credit import existing_mathlib_target_row
from leanmill_factory_config import FACTORY_POLICY
from leanmill_paths import DATA_DIR, REPAIR_FAMILY_REGISTRY

DEFAULT_CHECKPOINT = f"{DATA_DIR}/evaluation_harness_run.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/evaluation_harness_row_context_selected.json"
DEFAULT_PREP = f"{DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_c_discriminating_slice.json"
DEFAULT_MD = f"{DATA_DIR}/evaluation_harness_c_discriminating_slice.md"
DEFAULT_ROW_CONTEXT_OUT = f"{DATA_DIR}/evaluation_harness_c_discriminating_row_context.json"
DEFAULT_QUEUE_DB = f"{DATA_DIR}/leanmill_work_queue.sqlite"
DEFAULT_SOURCE_SNAPSHOT_DIR = f"{DATA_DIR}/evaluation_harness_sources"
POSITIVE_EXITS = {
    "raw_closure_candidate",
    "governed_tool_tactic_closure_candidate",
    "ratified_closure",
    "exact_gap",
    "valid_falsifier",
}
STRICT_NO_SIGNAL_EXITS = {
    "tested_no_positive_signal",
}
INFRA_HOLD_EXITS = {
    "harness_candidate_build_failure",
    "harness_no_candidates",
    "target_kind_audit_failure",
    "wall_timeout_hit",
}
STATIC_ARMS = ("public_tool_static", "governed_public_tool_static")
C_ARM = "governed_adaptive_residual_curriculum"
USEFUL_PROBE_EXITS = {"ratified_closure", "exact_gap_candidate", "valid_falsifier"}
NO_SIGNAL_PROBE_EXITS = {"tested_no_positive_signal", "tested_probe_no_signal", "probe_finished_no_tests"}
BAD_PROBE_EXITS = {"probe_failed", "failed_negative_control", "probe_worker_exception"}


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("rows", "results", "row_results", "qualified_rows", "items", "corpus"):
        vals = obj.get(key)
        if isinstance(vals, list):
            rows.extend(x for x in vals if isinstance(x, dict))
    for value in obj.values():
        if isinstance(value, dict) and _row_id(value):
            rows.append(value)
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = _row_id(row)
        if rid:
            dedup.setdefault(rid, row)
    return list(dedup.values())


def _template_index(
    spec_dir: str | Path,
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    positives: dict[str, set[str]] = defaultdict(set)
    negatives: dict[str, set[str]] = defaultdict(set)
    for spec in family_specs.usable_specs(family_specs.load_specs(spec_dir), target_names_by_row=target_names_by_row):
        family = str(spec.get("family") or "")
        if not family:
            continue
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if not row_id:
                continue
            kind = str(template.get("test_kind") or "")
            if kind == "positive":
                positives[row_id].add(family)
            elif kind == "negative_control":
                negatives[row_id].add(family)
    return positives, negatives


def _registry_statuses(path: str | Path) -> dict[str, str]:
    obj = _read_json(path) or {}
    return {
        str(row.get("family") or ""): str(row.get("status") or "")
        for row in obj.get("families") or []
        if isinstance(row, dict) and str(row.get("family") or "")
    }


def _positive(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in POSITIVE_EXITS


def _strict_no_signal(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in STRICT_NO_SIGNAL_EXITS


def _infra_hold(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in INFRA_HOLD_EXITS


def _record_rank(rec: dict[str, Any]) -> tuple[int, int, int, int]:
    # Safety rule: if any static run found a public-tool positive for a row,
    # that row is tool-solvable and must not enter a C-discriminating slice.
    positive_rank = 3 if _positive(rec) else 0
    strict_rank = 2 if _strict_no_signal(rec) else 0
    infra_rank = 1 if _infra_hold(rec) else 0
    attempts = int(rec.get("attempt_count") or 0)
    has_family_match = 1 if rec.get("family_matches") else 0
    return (positive_rank, strict_rank, infra_rank, has_family_match, attempts)


def _by_row_arm(records: list[dict[str, Any]], run_id: str = "") -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    conflicts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for rec in records:
        if run_id and str(rec.get("run_id") or "") != run_id:
            continue
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "")
        if not row_id or not arm:
            continue
        existing = out[row_id].get(arm)
        if existing is not None and str(existing.get("learning_exit") or "") != str(rec.get("learning_exit") or ""):
            conflicts[row_id][arm] += 1
        if existing is None or _record_rank(rec) > _record_rank(existing):
            out[row_id][arm] = rec
    return out


def _static_result(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    public = arms.get("public_tool_static")
    governed = arms.get("governed_public_tool_static")
    present = [arm for arm in STATIC_ARMS if arm in arms]
    positive = any(_positive(arms.get(arm)) for arm in STATIC_ARMS)
    infra_hold = any(_infra_hold(arms.get(arm)) for arm in STATIC_ARMS)
    missing_static_arms = [arm for arm in STATIC_ARMS if arm not in arms]
    strict_no_signal = bool(present) and all(_strict_no_signal(arms.get(arm)) for arm in present)
    if not present:
        status = "unknown_not_run"
    elif positive:
        status = "positive"
    elif infra_hold:
        status = "infra_hold"
    elif strict_no_signal:
        status = "failed_or_no_positive_signal"
    else:
        status = "ambiguous_non_positive"
    return {
        "status": status,
        "public_exit": public.get("learning_exit") if public else None,
        "governed_exit": governed.get("learning_exit") if governed else None,
        "present_arms": present,
        "missing_static_arms": missing_static_arms,
        "full_static_sweep_complete": not missing_static_arms,
        "strict_no_signal_required": True,
        "attempt_count": sum(int((arms.get(arm) or {}).get("attempt_count") or 0) for arm in STATIC_ARMS),
    }



def _probe_status(exit_kind: str) -> str:
    if exit_kind in USEFUL_PROBE_EXITS:
        return "probe_useful_positive"
    if exit_kind in NO_SIGNAL_PROBE_EXITS:
        return "probe_no_positive_signal"
    if exit_kind == "compile_candidate_needs_governance":
        return "probe_compile_candidate_needs_governance"
    if exit_kind in BAD_PROBE_EXITS:
        return f"probe_bad_{exit_kind}"
    if exit_kind:
        return "probe_other_terminal_exit"
    return "probe_terminal_missing_exit"


def _probe_rank(status: str) -> int:
    if status == "probe_useful_positive":
        return 40
    if status == "probe_compile_candidate_needs_governance":
        return 30
    if status == "probe_no_positive_signal":
        return 20
    if status.startswith("probe_bad_"):
        return 10
    return 0


def _family_spec_row_probe_signature(family: str, row_id: str, templates: list[dict[str, Any]]) -> str:
    body_by_template_id = {
        str(template.get("id") or ""): family_specs._template_body(template)
        for template in templates
        if isinstance(template, dict)
    }
    return probe_signatures.family_spec_row_probe_signature(
        family=family,
        row_id=row_id,
        templates=templates,
        body_by_template_id=body_by_template_id,
    )


def _current_family_spec_row_signatures(
    spec_dir: str | Path,
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for spec in family_specs.usable_specs(family_specs.load_specs(str(spec_dir)), target_names_by_row=target_names_by_row):
        family = str(spec.get("family") or "")
        if not family:
            continue
        by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if row_id:
                by_row[row_id].append(template)
        for row_id, templates in by_row.items():
            if any(str(t.get("test_kind") or "") == "positive" for t in templates):
                out[(family, row_id)] = _family_spec_row_probe_signature(family, row_id, templates)
    return out


def _payload_row_signature(payload: dict[str, Any], row_id: str) -> str:
    fps = payload.get("family_spec_template_fingerprints") or {}
    if isinstance(fps, dict) and str(fps.get(row_id) or ""):
        return str(fps.get(row_id) or "")
    return str(payload.get("probe_signature") or "")


def _probe_results_by_pair(queue_db: str | Path, *, current_row_signatures: dict[tuple[str, str], str] | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    if not queue_db:
        return {}
    p = Path(queue_db)
    if not p.exists() or not p.is_file():
        return {}
    try:
        cx = sqlite3.connect(str(p))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT work_id, status, payload_json, updated_at
            FROM work_items
            WHERE kind='repair_canary_probe' AND status IN ('done','failed','retired','dead_letter')
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("probe_lane") or "") != "family_spec":
            continue
        if str(row["status"] or "") in {"retired", "dead_letter"} and not (payload.get("row_outcomes") or payload.get("learning_unit_exit") or payload.get("exit_kind")):
            continue
        family = str(payload.get("family") or "")
        if not family:
            continue
        row_payloads: list[dict[str, Any]] = []
        row_outcomes = payload.get("row_outcomes") or []
        if isinstance(row_outcomes, dict):
            row_outcomes = list(row_outcomes.values())
        if isinstance(row_outcomes, list) and row_outcomes:
            row_payloads = [x for x in row_outcomes if isinstance(x, dict)]
        else:
            shard = payload.get("family_spec_shard") or {}
            row_id = str(shard.get("row_id") or "") if isinstance(shard, dict) else ""
            if row_id:
                row_payloads = [{
                    "row_id": row_id,
                    "learning_unit_exit": str(payload.get("learning_unit_exit") or payload.get("exit_kind") or ""),
                    "ratified_closure_count": payload.get("ratified_closure_count"),
                    "exact_gap_candidate_count": payload.get("exact_gap_candidate_count"),
                    "valid_falsifier_count": payload.get("valid_falsifier_count"),
                    "negative_control_fail_count": payload.get("negative_control_fail_count"),
                    "negative_control_unexpected_pass_count": payload.get("negative_control_unexpected_pass_count"),
                    "compile_candidate_count": payload.get("compile_candidate_count"),
                }]
        for outcome in row_payloads:
            row_id = str(outcome.get("row_id") or "")
            if not row_id:
                continue
            exit_kind = str(outcome.get("learning_unit_exit") or payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
            status = _probe_status(exit_kind)
            evidence = {
                "family": family,
                "row_id": row_id,
                "work_id": row["work_id"],
                "queue_status": row["status"],
                "updated_at": int(row["updated_at"] or 0),
                "learning_unit_exit": exit_kind,
                "probe_status": status,
                "scoreboard": payload.get("scoreboard"),
                "ratified_closure_count": outcome.get("ratified_closure_count"),
                "exact_gap_candidate_count": outcome.get("exact_gap_candidate_count"),
                "valid_falsifier_count": outcome.get("valid_falsifier_count"),
                "negative_control_fail_count": outcome.get("negative_control_fail_count"),
                "negative_control_unexpected_pass_count": outcome.get("negative_control_unexpected_pass_count"),
                "compile_candidate_count": outcome.get("compile_candidate_count"),
            }
            key = (family, row_id)
            expected_signature = (current_row_signatures or {}).get(key, "")
            observed_signature = _payload_row_signature(payload, row_id)
            if expected_signature and observed_signature and observed_signature != expected_signature:
                continue
            evidence["family_spec_template_fingerprint"] = observed_signature or None
            key = (family, row_id)
            old = out.get(key)
            if old is None or (_probe_rank(status), evidence["updated_at"]) > (_probe_rank(str(old.get("probe_status") or "")), int(old.get("updated_at") or 0)):
                out[key] = evidence
    return out


def _static_conflict_rows(records: list[dict[str, Any]], run_id: str = "") -> list[dict[str, Any]]:
    exits_by_row_arm: dict[tuple[str, str], set[str]] = defaultdict(set)
    for rec in records:
        if run_id and str(rec.get("run_id") or "") != run_id:
            continue
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "")
        if row_id and arm in STATIC_ARMS:
            exits_by_row_arm[(row_id, arm)].add(str(rec.get("learning_exit") or ""))
    out = []
    for (row_id, arm), exits in exits_by_row_arm.items():
        if len(exits) > 1:
            out.append({"row_id": row_id, "arm": arm, "learning_exits": sorted(exits)})
    return sorted(out, key=lambda r: (str(r["row_id"]), str(r["arm"])))


def _best_family_match(rec: dict[str, Any] | None, policy: source_family_match.SourceFamilyMatchPolicy) -> str:
    match = source_family_match.best_match((rec or {}).get("family_matches") or [], policy)
    return str((match or {}).get("family") or "")


def _read_factory_policy(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path)
    return obj if isinstance(obj, dict) else {}

def _target_resolution_ok(row: dict[str, Any]) -> bool:
    status = str(row.get("target_resolution_status") or "")
    return status == "pass"


def build(args: argparse.Namespace) -> dict[str, Any]:
    match_policy = source_family_match.policy_from_factory_policy(
        _read_factory_policy(getattr(args, "factory_policy", FACTORY_POLICY)),
        profile=str(getattr(args, "policy_profile", "") or ""),
    )
    rows_obj = _read_json(args.row_context) or {}
    rows = _iter_rows(rows_obj)
    materialization = source_materialization.materialize_row_sources(
        rows,
        out_dir=getattr(args, "source_snapshot_dir", DEFAULT_SOURCE_SNAPSHOT_DIR),
        mathlib_root=getattr(args, "mathlib_root", ""),
    )
    by_id = {_row_id(row): row for row in rows if _row_id(row)}
    prep = _read_json(args.prep) or {}
    order = [str(x) for x in prep.get("selected_rows_order") or [] if str(x)]
    if order:
        seen_order = set()
        filtered_order = []
        for row_id in order:
            if row_id in by_id and row_id not in seen_order:
                filtered_order.append(row_id)
                seen_order.add(row_id)
        missing_from_prep = sorted(row_id for row_id in by_id if row_id not in seen_order)
        order = filtered_order + missing_from_prep
    else:
        missing_from_prep = []
        order = sorted(by_id)
    target_names_by_row = family_specs.target_names_by_row_from_context_paths([args.row_context])
    positives, negatives = _template_index(args.spec_dir, target_names_by_row=target_names_by_row)
    registry_status = _registry_statuses(args.registry)
    records = _read_jsonl(args.checkpoint)
    records_by_row = _by_row_arm(records, run_id=args.run_id)
    static_conflict_rows = _static_conflict_rows(records, run_id=args.run_id)
    current_probe_signatures = _current_family_spec_row_signatures(args.spec_dir, target_names_by_row=target_names_by_row)
    probe_by_pair = _probe_results_by_pair(getattr(args, "queue_db", ""), current_row_signatures=current_probe_signatures)

    candidates: list[dict[str, Any]] = []
    support_counts = Counter()
    blockers_by_reason = Counter()
    family_supply: dict[str, dict[str, Any]] = {}
    for row_id in order:
        row = by_id.get(row_id, {"row_id": row_id})
        static = _static_result(records_by_row.get(row_id, {}))
        families_pos_raw = sorted(positives.get(row_id) or [])
        families_neg_raw = sorted(negatives.get(row_id) or [])
        best_static_family = _best_family_match((records_by_row.get(row_id, {}) or {}).get("public_tool_static"), match_policy)
        families_rejected_by_static_match: list[str] = []
        if best_static_family:
            families_pos = [fam for fam in families_pos_raw if fam == best_static_family]
            families_neg = [fam for fam in families_neg_raw if fam == best_static_family]
            families_rejected_by_static_match = sorted(set(families_pos_raw).union(families_neg_raw).difference({best_static_family}))
        else:
            families_pos = families_pos_raw
            families_neg = families_neg_raw
        matched_families = sorted(set(families_pos).intersection(families_neg))
        probe_evidence_by_family = {
            fam: probe_by_pair[(fam, row_id)]
            for fam in matched_families
            if (fam, row_id) in probe_by_pair
        }
        probe_verified_families = sorted(
            fam for fam, evidence in probe_evidence_by_family.items()
            if evidence.get("probe_status") == "probe_useful_positive"
        )
        probe_pending_families = sorted(fam for fam in matched_families if fam not in probe_evidence_by_family)
        probe_terminal_nonuseful_families = sorted(
            fam for fam, evidence in probe_evidence_by_family.items()
            if evidence.get("probe_status") != "probe_useful_positive"
        )
        target_ok = _target_resolution_ok(row)
        existing_mathlib_target = existing_mathlib_target_row(row)
        structural_eligible = (
            static["status"] == "failed_or_no_positive_signal"
            and bool(matched_families)
            and target_ok
            and not existing_mathlib_target
        )
        probe_terminal_block = bool(structural_eligible and not probe_verified_families and not probe_pending_families and probe_terminal_nonuseful_families)
        eligible = bool(structural_eligible and not probe_terminal_block)
        reasons = []
        if static["status"] == "positive":
            reasons.append("static_tool_positive")
        elif static["status"] == "unknown_not_run":
            reasons.append("static_result_unknown")
        elif static["status"] == "infra_hold":
            reasons.append("static_harness_infra_hold")
        elif static["status"] == "ambiguous_non_positive":
            reasons.append("static_ambiguous_non_positive")
        if not families_pos:
            reasons.append("no_positive_family_template")
        if families_pos and not matched_families:
            reasons.append("missing_matched_negative_control")
        if best_static_family and not matched_families and set(families_pos_raw).union(families_neg_raw):
            reasons.append("family_template_not_top_static_match")
        if not target_ok:
            reasons.append("target_not_executable")
        if existing_mathlib_target:
            reasons.append("existing_mathlib_target_snapshot")
        if probe_terminal_block:
            statuses = sorted({str(evidence.get("probe_status") or "") for evidence in probe_evidence_by_family.values()})
            reasons.append("family_spec_probe_terminal_nonuseful:" + ",".join(statuses))
        if not reasons:
            reasons.append("eligible")
        for reason in reasons:
            support_counts[reason] += 1
            if reason != "eligible":
                blockers_by_reason[reason] += 1
        for family in sorted(set(families_pos).union(families_neg)):
            rec = family_supply.setdefault(family, {
                "family": family,
                "status": registry_status.get(family, "unknown"),
                "positive_template_rows_seen": 0,
                "matched_negative_rows_seen": 0,
                "static_positive_rows": [],
                "static_fail_rows": [],
                "missing_negative_rows": [],
                "target_not_executable_rows": [],
            })
            if family in families_pos:
                rec["positive_template_rows_seen"] += 1
            if family in matched_families:
                rec["matched_negative_rows_seen"] += 1
            if family in matched_families and static["status"] == "positive":
                rec["static_positive_rows"].append(row_id)
            if family in matched_families and static["status"] == "failed_or_no_positive_signal" and target_ok and not existing_mathlib_target:
                rec["static_fail_rows"].append(row_id)
            if family in families_pos and family not in families_neg:
                rec["missing_negative_rows"].append(row_id)
            if family in families_pos and not target_ok:
                rec["target_not_executable_rows"].append(row_id)
        static_credit_pending = bool([arm for arm in STATIC_ARMS if arm not in static.get("present_arms", [])])
        probe_credit_ready = bool(eligible and probe_verified_families)
        probe_credit_pending = bool(eligible and not probe_verified_families and probe_pending_families)
        evidence_status = (
            "c_discriminating_probe_verified_pending_static_sweep" if probe_credit_ready and static_credit_pending else
            "c_discriminating_probe_verified" if probe_credit_ready else
            "c_discriminating_structural_candidate_pending_static_sweep_and_probe" if eligible and static_credit_pending else
            "c_discriminating_structural_candidate_pending_probe" if probe_credit_pending else
            "blocked_family_spec_probe_terminal_nonuseful" if probe_terminal_block else (
            "disqualified_existing_mathlib_target" if existing_mathlib_target else
            "unverified_static_sweep_required" if static["status"] == "unknown_not_run" else
            "disqualified_static_positive" if static["status"] == "positive" else
            "blocked_static_infra_hold" if static["status"] == "infra_hold" else
            "blocked_static_ambiguous_non_positive" if static["status"] == "ambiguous_non_positive" else
            "blocked_missing_family_or_target_evidence"
        ))
        candidates.append({
            "row_id": row_id,
            "eligible": eligible,
            "c_discriminating_evidence_status": evidence_status,
            "static_sweep_required_before_c_credit": bool(static_credit_pending or static["status"] == "unknown_not_run"),
            "family_spec_probe_required_before_c_credit": bool(probe_credit_pending),
            "probe_credit_ready": probe_credit_ready,
            "probe_credit_pending": probe_credit_pending,
            "probe_verified_families": probe_verified_families,
            "probe_pending_families": probe_pending_families,
            "probe_terminal_nonuseful_families": probe_terminal_nonuseful_families,
            "family_spec_probe_evidence": {fam: probe_evidence_by_family[fam] for fam in sorted(probe_evidence_by_family)},
            "static_tools_result": static,
            "family_available": bool(families_pos),
            "families_with_positive_template": families_pos,
            "families_with_negative_control": families_neg,
            "matched_families": matched_families,
            "best_static_family_match": best_static_family,
            "families_rejected_by_static_match": families_rejected_by_static_match,
            "family_statuses": {fam: registry_status.get(fam, "unknown") for fam in matched_families},
            "target_resolution_ok": target_ok,
            "target_theorem_name": row.get("target_theorem_name"),
            "source_file": row.get("source_file") or row.get("sorried_file"),
            "existing_mathlib_target": existing_mathlib_target,
            "strict_c_credit_disqualified_reason": "existing_mathlib_target_snapshot" if existing_mathlib_target else "",
            "source_materialization": row.get("source_materialization") if isinstance(row.get("source_materialization"), dict) else {},
            "rejection_reasons": [] if eligible else reasons,
        })

    eligible_rows = [row for row in candidates if row["eligible"]]
    selected = eligible_rows[: max(0, int(args.limit))]
    selected_ids = [row["row_id"] for row in selected]
    credit_ready_rows = [
        row for row in eligible_rows
        if row.get("c_discriminating_evidence_status") == "c_discriminating_probe_verified"
    ]
    probe_verified_rows = [row for row in eligible_rows if row.get("probe_credit_ready")]
    probe_pending_rows = [row for row in eligible_rows if row.get("probe_credit_pending")]
    source_demand_requests = []
    for rec in family_supply.values():
        static_fail_count = len(rec["static_fail_rows"])
        missing = max(0, int(args.min_rows_per_family) - static_fail_count)
        action = None
        if missing and rec["matched_negative_rows_seen"]:
            action = "source_similar_static_fail_rows"
        elif rec["missing_negative_rows"]:
            action = "create_matched_negative_controls_before_c_slice"
        elif rec["target_not_executable_rows"]:
            action = "repair_target_materialization_before_c_slice"
        if not action:
            continue
        source_demand_requests.append({
            "family": rec["family"],
            "status": rec["status"],
            "recommended_action": action,
            "needed_static_fail_rows": missing,
            "existing_static_fail_rows": rec["static_fail_rows"][:10],
            "static_positive_design_rows": rec["static_positive_rows"][:10],
            "missing_negative_rows": rec["missing_negative_rows"][:10],
            "target_not_executable_rows": rec["target_not_executable_rows"][:10],
            "source_query_intent": "Find sibling or heldout target rows with the same repair-family shape, executable local source, matched negative-control design, and no static-public-tool positive signal.",
        })
    source_demand_requests.sort(key=lambda item: (
        item["recommended_action"] != "source_similar_static_fail_rows",
        -int(item.get("needed_static_fail_rows") or 0),
        str(item.get("family") or ""),
    ))
    if len(credit_ready_rows) >= int(args.min_rows):
        status = "ready"
    elif selected:
        status = "blocked_pending_probe_or_static_sweep"
    else:
        status = "blocked_insufficient_c_discriminating_rows"
    selected_context_rows = [by_id[row_id] for row_id in selected_ids if row_id in by_id]
    if args.row_context_out:
        Path(args.row_context_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.row_context_out).write_text(json.dumps({
            "schema": "leanmill-c-discriminating-row-context-v1",
            "source_row_context": args.row_context,
            "selection_file": args.out,
            "rows": selected_context_rows,
        }, indent=2, sort_keys=True) + "\n")
    result = {
        "schema": "leanmill-c-discriminating-slice-v1",
        "status": status,
        "checkpoint": args.checkpoint,
        "run_id": args.run_id,
        "row_context": args.row_context,
        "row_context_out": args.row_context_out,
        "source_materialization": materialization,
        "spec_dir": args.spec_dir,
        "registry": args.registry,
        "min_rows": int(args.min_rows),
        "limit": int(args.limit),
        "candidate_pool_count": len(candidates),
        "prep_missing_row_count": len(missing_from_prep),
        "prep_missing_rows_sample": missing_from_prep[:50],
        "eligible_count": len(eligible_rows),
        "selected_count": len(selected),
        "credit_ready_count": len(credit_ready_rows),
        "probe_verified_count": len(probe_verified_rows),
        "probe_pending_count": len(probe_pending_rows),
        "probe_terminal_nonuseful_count": sum(1 for row in candidates if row.get("c_discriminating_evidence_status") == "blocked_family_spec_probe_terminal_nonuseful"),
        "static_conflict_row_count": len(static_conflict_rows),
        "static_conflict_rows": static_conflict_rows[:50],
        "static_conflict_policy": "public-tool positive dominates conflicting static no-signal records for C-slice safety",
        "source_family_match_policy": match_policy.as_receipt(),
        "selected_rows_order": selected_ids,
        "support_counts": dict(sorted(support_counts.items())),
        "blockers_by_reason": dict(sorted(blockers_by_reason.items())),
        "source_demand_requests": source_demand_requests,
        "rows": candidates,
        "selected_rows": selected,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(args.md, result)
    if status != "ready" and not args.allow_not_ready:
        raise SystemExit("C-discriminating slice prep failed: " + json.dumps({
            "eligible_count": len(eligible_rows),
            "min_rows": int(args.min_rows),
            "blockers_by_reason": dict(blockers_by_reason),
        }, sort_keys=True))
    return result


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill C-Discriminating Slice Prep",
        "",
        f"- status: `{result['status']}`",
        f"- eligible rows: `{result['eligible_count']}`",
        f"- selected rows: `{result['selected_count']}`",
        f"- credit-ready rows: `{result.get('credit_ready_count', 0)}`",
        f"- probe-pending rows: `{result.get('probe_pending_count', 0)}`",
        f"- min rows: `{result['min_rows']}`",
        f"- blockers: `{result['blockers_by_reason']}`",
        "",
        "## Selected Rows",
        "",
        "| row | static | evidence | matched families | target |",
        "|---|---|---|---|---|",
    ]
    for row in result["selected_rows"]:
        lines.append("| " + " | ".join([
            str(row["row_id"]),
            str(row["static_tools_result"]["status"]),
            str(row.get("c_discriminating_evidence_status") or ""),
            ",".join(row["matched_families"]),
            str(row.get("target_theorem_name") or ""),
        ]) + " |")
    lines.extend(["", "## Top Rejection Reasons", ""])
    for reason, count in result["blockers_by_reason"].items():
        lines.append(f"- `{reason}`: `{count}`")
    lines.extend(["", "## Source Demand Requests", ""])
    for req in result.get("source_demand_requests", [])[:20]:
        lines.append(
            f"- `{req['family']}` action=`{req['recommended_action']}` needed_static_fail_rows=`{req['needed_static_fail_rows']}` design_rows=`{req['static_positive_design_rows']}`"
        )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_slice_") as td:
        root = Path(td)
        src = root / "r1.lean"
        src.write_text("theorem r1 : True := by\n  trivial\n")
        rows = root / "rows.json"
        rows.write_text(json.dumps({"rows": [{"row_id": "r1", "source_file": str(src), "target_resolution_status": "pass"}]}) + "\n")
        prep = root / "prep.json"
        prep.write_text(json.dumps({"selected_rows_order": ["r1"]}) + "\n")
        ck = root / "run.jsonl"
        for arm in STATIC_ARMS:
            ck.write_text((ck.read_text() if ck.exists() else "") + json.dumps({"run_id": "x", "row_id": "r1", "arm": arm, "learning_exit": "tested_no_positive_signal", "attempt_count": 3}) + "\n")
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "fam.yaml").write_text("""
family: fam
status: candidate_family
templates:
  - id: pos
    row_id: r1
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: r1
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        reg = root / "registry.json"
        reg.write_text(json.dumps({"families": [{"family": "fam", "status": "candidate_family"}]}) + "\n")
        result = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=str(root / "selected_rows.json"),
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert result["status"] == "blocked_pending_probe_or_static_sweep", result
        assert result["eligible_count"] == 1, result
        assert result["probe_pending_count"] == 1, result
        assert result["selected_rows_order"] == ["r1"], result
        assert Path(result["row_context_out"]).exists(), result

        qdb = root / "queue.sqlite"
        qcx = sqlite3.connect(str(qdb))
        qcx.execute("CREATE TABLE work_items (work_id TEXT, kind TEXT, status TEXT, payload_json TEXT, updated_at INTEGER)")
        qcx.execute(
            "INSERT INTO work_items VALUES (?,?,?,?,?)",
            (
                "probe-useful",
                "repair_canary_probe",
                "done",
                json.dumps({
                    "family": "fam",
                    "probe_lane": "family_spec",
                    "family_spec_shard": {"row_id": "r1"},
                    "learning_unit_exit": "ratified_closure",
                    "ratified_closure_count": 1,
                    "negative_control_fail_count": 1,
                }),
                1,
            ),
        )
        qcx.commit()
        verified = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=False,
            queue_db=str(qdb),
        ))
        assert verified["status"] == "ready", verified
        assert verified["credit_ready_count"] == 1, verified
        assert verified["selected_rows"][0]["c_discriminating_evidence_status"] == "c_discriminating_probe_verified", verified

        current_sig = _current_family_spec_row_signatures(spec_dir)[("fam", "r1")]
        qcx.execute("UPDATE work_items SET payload_json=? WHERE work_id='probe-useful'", (json.dumps({
            "family": "fam",
            "probe_lane": "family_spec",
            "family_spec_shard": {"row_id": "r1"},
            "family_spec_template_fingerprints": {"r1": "stale"},
            "learning_unit_exit": "ratified_closure",
            "ratified_closure_count": 1,
            "negative_control_fail_count": 1,
        }),))
        qcx.commit()
        stale_probe = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
            queue_db=str(qdb),
        ))
        assert stale_probe["probe_pending_count"] == 1 and stale_probe["credit_ready_count"] == 0, stale_probe

        qcx.execute("UPDATE work_items SET payload_json=? WHERE work_id='probe-useful'", (json.dumps({
            "family": "fam",
            "probe_lane": "family_spec",
            "family_spec_shard": {"row_id": "r1"},
            "family_spec_template_fingerprints": {"r1": current_sig},
            "learning_unit_exit": "ratified_closure",
            "ratified_closure_count": 1,
            "negative_control_fail_count": 1,
        }),))
        qcx.commit()
        current_probe = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=False,
            queue_db=str(qdb),
        ))
        assert current_probe["credit_ready_count"] == 1, current_probe

        mathlib_root = root / "Mathlib"
        mathlib_file = mathlib_root / "Analysis" / "Existing.lean"
        mathlib_file.parent.mkdir(parents=True, exist_ok=True)
        mathlib_file.write_text("import Mathlib\n\ntheorem existing_target : True := by\n  trivial\n")
        mathlib_rows = root / "mathlib_rows.json"
        mathlib_rows.write_text(json.dumps({"rows": [{
            "row_id": "MCB_999_existing_target",
            "goal": "theorem existing_target : True := by\n  trivial",
            "source": {"mathlib_name": "existing_target", "file": "Analysis/Existing.lean"},
        }]}) + "\n")
        mathlib_prep = root / "mathlib_prep.json"
        mathlib_prep.write_text(json.dumps({"selected_rows_order": ["MCB_999_existing_target"]}) + "\n")
        mathlib_ck = root / "mathlib_run.jsonl"
        for arm in STATIC_ARMS:
            mathlib_ck.write_text((mathlib_ck.read_text() if mathlib_ck.exists() else "") + json.dumps({"run_id": "x", "row_id": "MCB_999_existing_target", "arm": arm, "learning_exit": "tested_no_positive_signal", "attempt_count": 3}) + "\n")
        (spec_dir / "fam_existing_mathlib.yaml").write_text("""
family: fam_existing_mathlib
status: candidate_family
templates:
  - id: pos
    row_id: MCB_999_existing_target
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: MCB_999_existing_target
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        qcx.execute("DELETE FROM work_items")
        qcx.execute(
            "INSERT INTO work_items VALUES (?,?,?,?,?)",
            (
                "probe-existing-mathlib",
                "repair_canary_probe",
                "done",
                json.dumps({
                    "family": "fam_existing_mathlib",
                    "probe_lane": "family_spec",
                    "family_spec_shard": {"row_id": "MCB_999_existing_target"},
                    "learning_unit_exit": "ratified_closure",
                    "ratified_closure_count": 1,
                    "negative_control_fail_count": 1,
                }),
                3,
            ),
        )
        qcx.commit()
        existing_mathlib = build(argparse.Namespace(
            checkpoint=str(mathlib_ck),
            run_id="x",
            row_context=str(mathlib_rows),
            prep=str(mathlib_prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
            queue_db=str(qdb),
            source_snapshot_dir=str(root / "mathlib_snapshots"),
            mathlib_root=str(mathlib_root),
        ))
        assert existing_mathlib["credit_ready_count"] == 0, existing_mathlib
        assert existing_mathlib["blockers_by_reason"].get("existing_mathlib_target_snapshot") == 1, existing_mathlib
        assert existing_mathlib["rows"][0]["existing_mathlib_target"] is True, existing_mathlib
        assert existing_mathlib["rows"][0]["c_discriminating_evidence_status"] == "disqualified_existing_mathlib_target", existing_mathlib

        qcx.execute("DELETE FROM work_items")
        qcx.execute(
            "INSERT INTO work_items VALUES (?,?,?,?,?)",
            (
                "probe-useful",
                "repair_canary_probe",
                "done",
                json.dumps({
                    "family": "fam",
                    "probe_lane": "family_spec",
                    "family_spec_shard": {"row_id": "r1"},
                    "learning_unit_exit": "tested_no_positive_signal",
                    "negative_control_fail_count": 1,
                }),
                4,
            ),
        )
        qcx.commit()
        no_probe_value = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
            queue_db=str(qdb),
        ))
        assert no_probe_value["eligible_count"] == 0, no_probe_value
        assert no_probe_value["probe_terminal_nonuseful_count"] == 1, no_probe_value

        qcx.execute("DELETE FROM work_items")
        qcx.execute(
            "INSERT INTO work_items VALUES (?,?,?,?,?)",
            (
                "probe-retired-no-evidence",
                "repair_canary_probe",
                "retired",
                json.dumps({
                    "family": "fam",
                    "probe_lane": "family_spec",
                    "family_spec_shard": {"row_id": "r1"},
                    "retired_by": "selftest",
                }),
                2,
            ),
        )
        qcx.commit()
        retired_ignored = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
            queue_db=str(qdb),
        ))
        assert retired_ignored["eligible_count"] == 1, retired_ignored
        assert retired_ignored["probe_pending_count"] == 1, retired_ignored

        rows_no_status = root / "rows_no_status.json"
        rows_no_status.write_text(json.dumps({"rows": [{"row_id": "r1", "source_file": str(src)}]}) + "\n")
        no_status_result = build(argparse.Namespace(
            checkpoint=str(ck),
            run_id="x",
            row_context=str(rows_no_status),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert no_status_result["eligible_count"] == 1, no_status_result
        assert no_status_result["source_materialization"]["counts"]["already_present"] == 1, no_status_result

        public_only_ck = root / "public_only_run.jsonl"
        public_only_ck.write_text(json.dumps({"run_id": "x", "row_id": "r1", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal", "attempt_count": 3}) + "\n")
        public_only = build(argparse.Namespace(
            checkpoint=str(public_only_ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert public_only["eligible_count"] == 1, public_only
        assert public_only["selected_rows"][0]["static_sweep_required_before_c_credit"], public_only
        assert public_only["selected_rows"][0]["static_tools_result"]["missing_static_arms"] == ["governed_public_tool_static"], public_only

        bad_ck = root / "bad_run.jsonl"
        bad_ck.write_text("".join(
            json.dumps({"run_id": "x", "row_id": "r1", "arm": arm, "learning_exit": "harness_candidate_build_failure", "attempt_count": 1}) + "\n"
            for arm in STATIC_ARMS
        ))
        blocked = build(argparse.Namespace(
            checkpoint=str(bad_ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert blocked["status"] == "blocked_insufficient_c_discriminating_rows", blocked
        assert blocked["eligible_count"] == 0, blocked
        assert blocked["blockers_by_reason"].get("static_harness_infra_hold") == 1, blocked

        src2 = root / "r2.lean"
        src2.write_text("theorem r2 : True := by\n  trivial\n")
        rows2 = root / "rows2.json"
        rows2.write_text(json.dumps({"rows": [
            {"row_id": "r1", "source_file": str(src), "target_resolution_status": "pass"},
            {"row_id": "r2", "source_file": str(src2), "target_resolution_status": "pass"},
        ]}) + "\n")
        prep_stale = root / "prep_stale.json"
        prep_stale.write_text(json.dumps({"selected_rows_order": ["r1"]}) + "\n")
        ck2 = root / "run2.jsonl"
        for rid in ("r1", "r2"):
            for arm in STATIC_ARMS:
                ck2.write_text((ck2.read_text() if ck2.exists() else "") + json.dumps({"run_id": "x", "row_id": rid, "arm": arm, "learning_exit": "tested_no_positive_signal", "attempt_count": 3}) + "\n")
        (spec_dir / "fam2.yaml").write_text("""
family: fam2
status: seed_only
templates:
  - id: pos
    row_id: r2
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: r2
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        stale_order_result = build(argparse.Namespace(
            checkpoint=str(ck2),
            run_id="x",
            row_context=str(rows2),
            prep=str(prep_stale),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert "r2" in stale_order_result["selected_rows_order"], stale_order_result
        assert stale_order_result["prep_missing_row_count"] == 1, stale_order_result

        routed_ck = root / "routed_run.jsonl"
        routed_ck.write_text(json.dumps({
            "run_id": "x",
            "row_id": "r1",
            "arm": "public_tool_static",
            "learning_exit": "tested_no_positive_signal",
            "attempt_count": 3,
            "family_matches": [
                {"family": "better_fam", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.95, "hit_count": 3},
                {"family": "fam", "status": "candidate_family", "has_negative_controls": True, "confidence": 0.5, "hit_count": 2},
            ],
        }) + "\n")
        routed = build(argparse.Namespace(
            checkpoint=str(routed_ck),
            run_id="x",
            row_context=str(rows),
            prep=str(prep),
            spec_dir=str(spec_dir),
            registry=str(reg),
            out=None,
            md=None,
            row_context_out=None,
            min_rows=1,
            limit=20,
            min_rows_per_family=1,
            allow_not_ready=True,
        ))
        assert routed["eligible_count"] == 0, routed
        assert routed["blockers_by_reason"].get("family_template_not_top_static_match") == 1, routed
    print("leanmill_c_discriminating_slice_prep self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--registry", default=REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--row-context-out", default=DEFAULT_ROW_CONTEXT_OUT)
    ap.add_argument("--queue-db", default=DEFAULT_QUEUE_DB)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--source-snapshot-dir", default=DEFAULT_SOURCE_SNAPSHOT_DIR)
    ap.add_argument("--mathlib-root", default="")
    ap.add_argument("--min-rows", type=int, default=20)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--min-rows-per-family", type=int, default=3)
    ap.add_argument("--allow-not-ready", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "row_context_out": args.row_context_out,
        "status": result["status"],
        "eligible_count": result["eligible_count"],
        "selected_count": result["selected_count"],
        "credit_ready_count": result.get("credit_ready_count", 0),
        "probe_pending_count": result.get("probe_pending_count", 0),
        "probe_terminal_nonuseful_count": result.get("probe_terminal_nonuseful_count", 0),
        "blockers_by_reason": result["blockers_by_reason"],
        "source_demand_count": len(result.get("source_demand_requests") or []),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
