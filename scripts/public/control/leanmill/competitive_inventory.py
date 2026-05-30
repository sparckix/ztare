#!/usr/bin/env python3
"""Inventory LeanMill artifacts for competitive-readiness Phase 2.

This is a read-only classifier. It does not grant proof credit and does not
run Lean by default; it turns existing Route C and ZtareProofs artifacts into a
single inspectable report so the next action is based on concrete inventory.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from leanmill_paths import DATA_DIR


DEFAULT_ESCAPE_ROUTE = "analytics/public/leanmill/escape_route/escape_route_run_results.json"
DEFAULT_ROUTE_C_REPLAY = "analytics/public/leanmill/results/v32_route_c_replay_results.json"
DEFAULT_ZTARE_PROOFS = "ztare_proofs/ZtareProofs"
DEFAULT_PR_A1 = "ztare_proofs/ZtareProofs/PR_A1_BohrCoeffExpNe_Discharge.lean"
DEFAULT_PR_A1_AUDIT = f"{DATA_DIR}/pr_a1_compile_l3_audit.json"
DEFAULT_ROUTE_C_GAP_TASKS = f"{DATA_DIR}/route_c_gap_tasks.json"
DEFAULT_ROUTE_C_HOLD_SYNTHESIS = f"{DATA_DIR}/route_c_gap_hold_synthesis.json"
DEFAULT_ROUTE_C_EXACT_GAP_REPLAY_PREP = f"{DATA_DIR}/route_c_exact_gap_replay_prep.json"
DEFAULT_ROUTE_C_EXACT_GAP_REPLAY_PROBE = f"{DATA_DIR}/route_c_exact_gap_replay_probe.json"
DEFAULT_OUT = f"{DATA_DIR}/leanmill_competitive_inventory.json"
DEFAULT_MD = f"{DATA_DIR}/leanmill_competitive_inventory.md"
DEFAULT_PROOF_LOOP_PATHS = [
    "scripts/public/control/route_c_layer_2c_dispatch.py",
    "scripts/public/lean/auto_prover_harness.py",
    "scripts/public/control/leanmill/llm_proposal_worker.py",
]

DECL_RE = re.compile(r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*(?:theorem|lemma)\s+([^\s:]+)", re.MULTILINE)
SORRY_RE = re.compile(r"\bsorry\b")
ADMIT_RE = re.compile(r"\badmit\b")
AXIOM_RE = re.compile(r"^\s*axiom\s+", re.MULTILINE)
PRINT_AXIOMS_RE = re.compile(r"^\s*#print\s+axioms\s+(.+)$", re.MULTILINE)


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _lean_static_counts(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "path": str(p),
            "exists": False,
            "sorry_count": 0,
            "admit_count": 0,
            "axiom_decl_count": 0,
            "decl_count": 0,
            "print_axioms_count": 0,
        }
    text = p.read_text(errors="ignore")
    decls = DECL_RE.findall(text)
    print_axioms = [m.group(1).strip() for m in PRINT_AXIOMS_RE.finditer(text)]
    return {
        "path": str(p),
        "exists": True,
        "line_count": text.count("\n") + 1,
        "sorry_count": len(SORRY_RE.findall(text)),
        "admit_count": len(ADMIT_RE.findall(text)),
        "axiom_decl_count": len(AXIOM_RE.findall(text)),
        "decl_count": len(decls),
        "decls": decls[:50],
        "print_axioms_count": len(print_axioms),
        "print_axioms_targets": print_axioms[:20],
    }


def _route_c_inventory(path: str | Path, *, label: str) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {"path": str(path), "label": label, "status": "missing_or_unreadable"}
    results = obj.get("results") if isinstance(obj.get("results"), list) else []
    verdicts = Counter(str(row.get("closure_verdict") or row.get("verdict") or row.get("status") or "unknown") for row in results if isinstance(row, dict))
    gap_rows: list[dict[str, Any]] = []
    closure_rows: list[dict[str, Any]] = []
    proposed_lemma_counter: Counter[str] = Counter()
    for row in results:
        if not isinstance(row, dict):
            continue
        verdict = str(row.get("closure_verdict") or row.get("verdict") or "")
        row_id = str(row.get("row_id") or "")
        proposed = [str(x) for x in (row.get("proposed_lemmas") or []) if str(x)]
        for lemma in proposed:
            proposed_lemma_counter[lemma] += 1
        if "GAP" in verdict or "OPEN" in verdict:
            gap_rows.append({
                "row_id": row_id,
                "theorem": row.get("theorem"),
                "verdict": verdict,
                "compiled_any": bool(row.get("compiled_any")),
                "proposed_lemmas": proposed[:8],
                "operation_type": row.get("operation_type"),
            })
        if bool(row.get("compiled_any")) or "CLOSED" in verdict:
            closure_rows.append({
                "row_id": row_id,
                "theorem": row.get("theorem"),
                "verdict": verdict,
                "compiled_any": bool(row.get("compiled_any")),
            })
    return {
        "path": str(path),
        "label": label,
        "status": "ok",
        "row_count": len(results),
        "verdict_counts": dict(sorted(verdicts.items())),
        "compiled_or_closed_count": len(closure_rows),
        "gap_report_count": len(gap_rows),
        "gap_rows": gap_rows[:50],
        "closure_rows": closure_rows[:20],
        "top_proposed_lemmas": proposed_lemma_counter.most_common(20),
        "metadata": {
            key: obj.get(key)
            for key in ("class", "model", "methodology", "generated_at", "note", "natural_control")
            if key in obj
        },
    }


def _ztare_proofs_inventory(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    lean_files = sorted(root_path.rglob("*.lean")) if root_path.exists() else []
    sorry_files: list[dict[str, Any]] = []
    decl_total = 0
    prefix_counts: Counter[str] = Counter()
    for path in lean_files:
        rel = path.relative_to(root_path).as_posix()
        prefix = rel.split("/", 1)[0] if "/" in rel else rel.split("_", 1)[0]
        prefix_counts[prefix] += 1
        counts = _lean_static_counts(path)
        decl_total += int(counts.get("decl_count") or 0)
        if int(counts.get("sorry_count") or 0) or int(counts.get("admit_count") or 0):
            sorry_files.append({
                "path": str(path),
                "relative_path": rel,
                "sorry_count": counts.get("sorry_count"),
                "admit_count": counts.get("admit_count"),
                "decl_count": counts.get("decl_count"),
            })
    return {
        "path": str(root_path),
        "exists": root_path.exists(),
        "lean_file_count": len(lean_files),
        "decl_count": decl_total,
        "files_with_sorry_or_admit_count": len(sorry_files),
        "open_sorry_or_admit_count": sum(int(item.get("sorry_count") or 0) + int(item.get("admit_count") or 0) for item in sorry_files),
        "prefix_counts": dict(prefix_counts.most_common(40)),
        "sample_open_files": sorry_files[:40],
    }


def _pr_a1_status(static_audit: dict[str, Any], compile_l3_audit: dict[str, Any] | None) -> tuple[str, str]:
    if not static_audit.get("exists"):
        return "missing", "restore or generate the PR_A1 candidate before audit"
    if (
        int(static_audit.get("sorry_count") or 0)
        or int(static_audit.get("admit_count") or 0)
        or int(static_audit.get("axiom_decl_count") or 0)
    ):
        return "static_open_or_axiom", "repair static blockers before compile/audit"
    if not compile_l3_audit:
        return (
            "static_sorry_free_needs_compile_and_l3_audit",
            "run lake/Lean compile plus L3 anti-pattern audit before treating this as a public artifact candidate",
        )
    audit_status = str(compile_l3_audit.get("status") or "")
    if audit_status == "compile_pass_l3_advisory_pass":
        return (
            "compile_pass_l3_advisory_pass",
            "treat as public artifact review candidate only; proof credit still requires governed review",
        )
    if audit_status == "compile_pass_l3_advisory_review":
        return (
            "compile_pass_l3_advisory_review",
            "resolve the L3 advisory flags before public artifact review",
        )
    if audit_status in {"compile_failed", "disallowed_axiom_dependency", "l3_confirmed_blocker", "static_open_or_axiom"}:
        return audit_status, "repair the compile, axiom, or L3 blocker before further PR_A1 promotion"
    return audit_status or "compile_l3_audit_unreadable", "inspect the PR_A1 audit receipt"


def _semantic_retrieval_wiring(paths: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in paths:
        p = Path(item)
        text = p.read_text(errors="ignore") if p.exists() else ""
        rows.append({
            "path": str(p),
            "exists": p.exists(),
            "imports_semantic_premise_shelf": "semantic_premise_shelf" in text,
            "builds_semantic_shelf": "build_semantic_premise_shelf" in text,
            "renders_semantic_shelf": "render_semantic_premise_shelf" in text,
            "has_disable_flag": "no-semantic-premise-shelf" in text or "LEANMILL_DISABLE_SEMANTIC_PREMISE_SHELF" in text,
        })
    status = "pass" if rows and all(
        row["exists"] and row["imports_semantic_premise_shelf"] and row["builds_semantic_shelf"] and row["renders_semantic_shelf"]
        for row in rows
    ) else "gap"
    return {
        "schema": "leanmill-semantic-retrieval-wiring-inventory-v1",
        "status": status,
        "proof_loop_count": len(rows),
        "wired_count": sum(
            1 for row in rows
            if row["exists"] and row["imports_semantic_premise_shelf"] and row["builds_semantic_shelf"] and row["renders_semantic_shelf"]
        ),
        "paths": rows,
        "credit_boundary": "retrieval context only; no proof credit without Lean replay and governance",
    }


def _route_c_gap_task_summary(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {
            "path": str(path),
            "status": "missing",
            "task_count": 0,
            "enqueue_requested": False,
            "enqueued_now_count": 0,
        }
    tasks = obj.get("tasks") if isinstance(obj.get("tasks"), list) else []
    enqueue_receipts = obj.get("enqueue_receipts") if isinstance(obj.get("enqueue_receipts"), list) else []
    queue_status = obj.get("queue_status") if isinstance(obj.get("queue_status"), dict) else {}
    return {
        "path": str(path),
        "status": "ok" if tasks else "empty",
        "task_count": int(obj.get("task_count") or len(tasks)),
        "enqueue_requested": bool(obj.get("enqueue_requested")),
        "enqueued_now_count": int(obj.get("enqueued_now_count") or 0),
        "enqueue_receipt_count": len(enqueue_receipts),
        "queue_status": queue_status,
        "all_done": bool(queue_status.get("all_done")),
        "sample_tasks": tasks[:20],
        "next_action": obj.get("next_action"),
        "credit_boundary": obj.get("credit_boundary"),
    }


def _route_c_hold_synthesis_summary(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {
            "path": str(path),
            "status": "missing",
            "eligible_task_count": 0,
            "governance_followup_count": 0,
        }
    result_summary = obj.get("result_summary") if isinstance(obj.get("result_summary"), dict) else {}
    queue_status = obj.get("queue_status") if isinstance(obj.get("queue_status"), dict) else {}
    return {
        "path": str(path),
        "status": "ok" if int(obj.get("eligible_task_count") or 0) > 0 else "empty",
        "eligible_task_count": int(obj.get("eligible_task_count") or 0),
        "skipped_count": int(obj.get("skipped_count") or 0),
        "skipped_reason_counts": obj.get("skipped_reason_counts") if isinstance(obj.get("skipped_reason_counts"), dict) else {},
        "enqueue_requested": bool(obj.get("enqueue_requested")),
        "enqueued_now_count": int(obj.get("enqueued_now_count") or 0),
        "queue_status": queue_status,
        "all_done": bool(queue_status.get("all_done")),
        "result_proposal_type_counts": result_summary.get("proposal_type_counts") if isinstance(result_summary.get("proposal_type_counts"), dict) else {},
        "result_expected_outcome_counts": result_summary.get("expected_outcome_counts") if isinstance(result_summary.get("expected_outcome_counts"), dict) else {},
        "governance_followup_count": int(result_summary.get("governance_followup_count") or 0),
        "governance_status_counts": result_summary.get("governance_status_counts") if isinstance(result_summary.get("governance_status_counts"), dict) else {},
        "next_action": obj.get("next_action"),
        "credit_boundary": obj.get("credit_boundary"),
        "meta_reasoning_contract": obj.get("meta_reasoning_contract") if isinstance(obj.get("meta_reasoning_contract"), dict) else {},
    }


def _route_c_exact_gap_replay_prep_summary(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {"path": str(path), "status": "missing", "candidate_count": 0, "ready_packet_count": 0}
    return {
        "path": str(path),
        "status": "ok" if int(obj.get("candidate_count") or 0) > 0 else "empty",
        "candidate_count": int(obj.get("candidate_count") or 0),
        "status_counts": obj.get("status_counts") if isinstance(obj.get("status_counts"), dict) else {},
        "ready_packet_count": int(obj.get("ready_packet_count") or 0),
        "blocked_target_duplicate_count": int(obj.get("blocked_target_duplicate_count") or 0),
        "prompt_gate_repair_receipt": obj.get("prompt_gate_repair_receipt") if isinstance(obj.get("prompt_gate_repair_receipt"), dict) else {},
        "next_action": obj.get("next_action"),
        "credit_boundary": obj.get("credit_boundary"),
    }


def _route_c_exact_gap_replay_probe_summary(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path)
    if not isinstance(obj, dict):
        return {"path": str(path), "status": "missing", "ready_packet_count": 0}
    return {
        "path": str(path),
        "status": "ok" if int(obj.get("ready_packet_count") or 0) > 0 else "empty",
        "ready_packet_count": int(obj.get("ready_packet_count") or 0),
        "row_count": int(obj.get("row_count") or 0),
        "status_counts": obj.get("status_counts") if isinstance(obj.get("status_counts"), dict) else {},
        "next_action": obj.get("next_action"),
        "credit_boundary": obj.get("credit_boundary"),
        "meta_reasoning_receipt": obj.get("meta_reasoning_receipt") if isinstance(obj.get("meta_reasoning_receipt"), dict) else {},
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    pr_a1 = _lean_static_counts(args.pr_a1)
    pr_a1_audit = _read_json(args.pr_a1_audit)
    pr_a1_status, pr_a1_next_action = _pr_a1_status(
        pr_a1,
        pr_a1_audit if isinstance(pr_a1_audit, dict) else None,
    )
    route_c = [
        _route_c_inventory(args.escape_route, label="escape_route"),
        _route_c_inventory(args.route_c_replay, label="v32_route_c_replay"),
    ]
    ztare = _ztare_proofs_inventory(args.ztare_proofs)
    semantic_wiring = _semantic_retrieval_wiring(DEFAULT_PROOF_LOOP_PATHS)
    route_c_gap_tasks = _route_c_gap_task_summary(args.route_c_gap_tasks)
    route_c_hold_synthesis = _route_c_hold_synthesis_summary(args.route_c_hold_synthesis)
    route_c_replay_prep = _route_c_exact_gap_replay_prep_summary(args.route_c_exact_gap_replay_prep)
    route_c_replay_probe = _route_c_exact_gap_replay_probe_summary(args.route_c_exact_gap_replay_probe)
    route_c_gap_report_count = sum(int(item.get("gap_report_count") or 0) for item in route_c if isinstance(item, dict))
    route_c_closed_count = sum(int(item.get("compiled_or_closed_count") or 0) for item in route_c if isinstance(item, dict))
    return {
        "schema": "leanmill-competitive-inventory-v1",
        "generated_at_epoch": int(time.time()),
        "section_8_phase": "phase_2_existing_artifact_inventory",
        "credit_boundary": "inventory only; proof credit requires compile, leak-tight audit, matched negative controls, and governance receipts",
        "route_c": route_c,
        "route_c_gap_tasks": route_c_gap_tasks,
        "route_c_hold_synthesis": route_c_hold_synthesis,
        "route_c_exact_gap_replay_prep": route_c_replay_prep,
        "route_c_exact_gap_replay_probe": route_c_replay_probe,
        "ztare_proofs": ztare,
        "semantic_retrieval_wiring": semantic_wiring,
        "pr_a1_candidate": {
            "status": pr_a1_status,
            "static_audit": pr_a1,
            "compile_l3_audit": pr_a1_audit if isinstance(pr_a1_audit, dict) else None,
            "next_action": pr_a1_next_action,
        },
        "summary": {
            "route_c_gap_report_count": route_c_gap_report_count,
            "route_c_compiled_or_closed_count": route_c_closed_count,
            "route_c_gap_task_count": route_c_gap_tasks.get("task_count"),
            "route_c_gap_task_enqueue_requested": route_c_gap_tasks.get("enqueue_requested"),
            "route_c_gap_task_enqueued_now_count": route_c_gap_tasks.get("enqueued_now_count"),
            "route_c_gap_task_all_done": route_c_gap_tasks.get("all_done"),
            "route_c_gap_task_status_counts": (route_c_gap_tasks.get("queue_status") or {}).get("status_counts"),
            "route_c_hold_synthesis_eligible_count": route_c_hold_synthesis.get("eligible_task_count"),
            "route_c_hold_synthesis_all_done": route_c_hold_synthesis.get("all_done"),
            "route_c_hold_synthesis_status_counts": (route_c_hold_synthesis.get("queue_status") or {}).get("status_counts"),
            "route_c_hold_synthesis_proposal_type_counts": route_c_hold_synthesis.get("result_proposal_type_counts"),
            "route_c_hold_synthesis_governance_followup_count": route_c_hold_synthesis.get("governance_followup_count"),
            "route_c_hold_synthesis_governance_status_counts": route_c_hold_synthesis.get("governance_status_counts"),
            "route_c_exact_gap_replay_prep_candidate_count": route_c_replay_prep.get("candidate_count"),
            "route_c_exact_gap_replay_prep_ready_packet_count": route_c_replay_prep.get("ready_packet_count"),
            "route_c_exact_gap_replay_prep_status_counts": route_c_replay_prep.get("status_counts"),
            "route_c_exact_gap_replay_probe_ready_packet_count": route_c_replay_probe.get("ready_packet_count"),
            "route_c_exact_gap_replay_probe_status_counts": route_c_replay_probe.get("status_counts"),
            "ztare_lean_file_count": ztare.get("lean_file_count"),
            "ztare_files_with_sorry_or_admit_count": ztare.get("files_with_sorry_or_admit_count"),
            "semantic_retrieval_wiring_status": semantic_wiring.get("status"),
            "pr_a1_status": pr_a1_status,
            "pr_a1_compile_status": (
                ((pr_a1_audit or {}).get("compile") or {}).get("ok")
                if isinstance(pr_a1_audit, dict) and isinstance((pr_a1_audit or {}).get("compile"), dict)
                else None
            ),
            "pr_a1_l3_status": (
                ((pr_a1_audit or {}).get("l3_audit") or {}).get("status")
                if isinstance(pr_a1_audit, dict) and isinstance((pr_a1_audit or {}).get("l3_audit"), dict)
                else None
            ),
            "next_action": (
                route_c_replay_probe.get("next_action")
                if int(route_c_replay_probe.get("ready_packet_count") or 0) > 0
                else
                route_c_replay_prep.get("next_action")
                if int(route_c_replay_prep.get("candidate_count") or 0) > 0
                else
                route_c_hold_synthesis.get("next_action")
                if int(route_c_hold_synthesis.get("eligible_task_count") or 0) > 0
                and bool(route_c_hold_synthesis.get("all_done"))
                and int(route_c_hold_synthesis.get("governance_followup_count") or 0) > 0
                else
                route_c_hold_synthesis.get("next_action")
                if int(route_c_hold_synthesis.get("eligible_task_count") or 0) > 0
                and not bool(route_c_hold_synthesis.get("all_done"))
                else
                "run leanmill_llm_proposal_worker on Route C gap tasks"
                if int(route_c_gap_tasks.get("task_count") or 0) > 0 and bool(route_c_gap_tasks.get("enqueue_requested")) and not bool(route_c_gap_tasks.get("all_done"))
                else
                "synthesize Route C hold outputs into stronger exact-gap contexts"
                if int(route_c_gap_tasks.get("task_count") or 0) > 0 and bool(route_c_gap_tasks.get("all_done"))
                else
                "turn Route C gap reports into missing-lemma tasks"
                if pr_a1_status == "compile_pass_l3_advisory_pass" and route_c_gap_report_count > 0
                else pr_a1_next_action
            ),
        },
    }


def write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    pr = payload.get("pr_a1_candidate") if isinstance(payload.get("pr_a1_candidate"), dict) else {}
    lines = [
        "# LeanMill Competitive Inventory",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- phase: `{payload.get('section_8_phase')}`",
        f"- credit_boundary: {payload.get('credit_boundary')}",
        "",
        "## Summary",
        "",
        f"- route_c_gap_report_count: `{summary.get('route_c_gap_report_count')}`",
        f"- route_c_compiled_or_closed_count: `{summary.get('route_c_compiled_or_closed_count')}`",
        f"- route_c_gap_task_count: `{summary.get('route_c_gap_task_count')}`",
        f"- route_c_gap_task_enqueue_requested: `{summary.get('route_c_gap_task_enqueue_requested')}`",
        f"- route_c_gap_task_all_done: `{summary.get('route_c_gap_task_all_done')}`",
        f"- route_c_gap_task_status_counts: `{summary.get('route_c_gap_task_status_counts')}`",
        f"- route_c_hold_synthesis_eligible_count: `{summary.get('route_c_hold_synthesis_eligible_count')}`",
        f"- route_c_hold_synthesis_all_done: `{summary.get('route_c_hold_synthesis_all_done')}`",
        f"- route_c_hold_synthesis_status_counts: `{summary.get('route_c_hold_synthesis_status_counts')}`",
        f"- route_c_hold_synthesis_proposal_type_counts: `{summary.get('route_c_hold_synthesis_proposal_type_counts')}`",
        f"- route_c_hold_synthesis_governance_followup_count: `{summary.get('route_c_hold_synthesis_governance_followup_count')}`",
        f"- route_c_hold_synthesis_governance_status_counts: `{summary.get('route_c_hold_synthesis_governance_status_counts')}`",
        f"- route_c_exact_gap_replay_prep_candidate_count: `{summary.get('route_c_exact_gap_replay_prep_candidate_count')}`",
        f"- route_c_exact_gap_replay_prep_ready_packet_count: `{summary.get('route_c_exact_gap_replay_prep_ready_packet_count')}`",
        f"- route_c_exact_gap_replay_prep_status_counts: `{summary.get('route_c_exact_gap_replay_prep_status_counts')}`",
        f"- route_c_exact_gap_replay_probe_ready_packet_count: `{summary.get('route_c_exact_gap_replay_probe_ready_packet_count')}`",
        f"- route_c_exact_gap_replay_probe_status_counts: `{summary.get('route_c_exact_gap_replay_probe_status_counts')}`",
        f"- ztare_lean_file_count: `{summary.get('ztare_lean_file_count')}`",
        f"- ztare_files_with_sorry_or_admit_count: `{summary.get('ztare_files_with_sorry_or_admit_count')}`",
        f"- semantic_retrieval_wiring_status: `{summary.get('semantic_retrieval_wiring_status')}`",
        f"- pr_a1_status: `{summary.get('pr_a1_status')}`",
        f"- pr_a1_compile_status: `{summary.get('pr_a1_compile_status')}`",
        f"- pr_a1_l3_status: `{summary.get('pr_a1_l3_status')}`",
        f"- next_action: {summary.get('next_action')}",
        "",
        "## Route C",
        "",
    ]
    for item in payload.get("route_c") or []:
        lines.append(
            f"- `{item.get('label')}`: rows=`{item.get('row_count')}`, "
            f"gap_reports=`{item.get('gap_report_count')}`, "
            f"compiled_or_closed=`{item.get('compiled_or_closed_count')}`"
        )
    tasks = payload.get("route_c_gap_tasks") if isinstance(payload.get("route_c_gap_tasks"), dict) else {}
    lines.extend([
        "",
        "## Route C Gap Tasks",
        "",
        f"- status: `{tasks.get('status')}`",
        f"- task_count: `{tasks.get('task_count')}`",
        f"- enqueue_requested: `{tasks.get('enqueue_requested')}`",
        f"- enqueued_now_count: `{tasks.get('enqueued_now_count')}`",
        f"- all_done: `{tasks.get('all_done')}`",
        f"- queue_status: `{(tasks.get('queue_status') or {}).get('status_counts')}`",
        f"- next_action: {tasks.get('next_action')}",
    ])
    synthesis = payload.get("route_c_hold_synthesis") if isinstance(payload.get("route_c_hold_synthesis"), dict) else {}
    lines.extend([
        "",
        "## Route C Hold Synthesis",
        "",
        f"- status: `{synthesis.get('status')}`",
        f"- eligible_task_count: `{synthesis.get('eligible_task_count')}`",
        f"- skipped_count: `{synthesis.get('skipped_count')}`",
        f"- queue_status: `{(synthesis.get('queue_status') or {}).get('status_counts')}`",
        f"- result_proposal_type_counts: `{synthesis.get('result_proposal_type_counts')}`",
        f"- governance_followup_count: `{synthesis.get('governance_followup_count')}`",
        f"- governance_status_counts: `{synthesis.get('governance_status_counts')}`",
        f"- next_action: {synthesis.get('next_action')}",
    ])
    replay_prep = payload.get("route_c_exact_gap_replay_prep") if isinstance(payload.get("route_c_exact_gap_replay_prep"), dict) else {}
    replay_probe = payload.get("route_c_exact_gap_replay_probe") if isinstance(payload.get("route_c_exact_gap_replay_probe"), dict) else {}
    replay_next_action = (
        replay_probe.get("next_action")
        if int(replay_probe.get("ready_packet_count") or 0) > 0
        else replay_prep.get("next_action")
    )
    lines.extend([
        "",
        "## Route C Exact Gap Replay",
        "",
        f"- prep_candidate_count: `{replay_prep.get('candidate_count')}`",
        f"- prep_ready_packet_count: `{replay_prep.get('ready_packet_count')}`",
        f"- prep_status_counts: `{replay_prep.get('status_counts')}`",
        f"- prep_prompt_gate_repair_receipt: `{replay_prep.get('prompt_gate_repair_receipt', {})}`",
        f"- probe_ready_packet_count: `{replay_probe.get('ready_packet_count')}`",
        f"- probe_status_counts: `{replay_probe.get('status_counts')}`",
        f"- probe_meta_reasoning_receipt: `{replay_probe.get('meta_reasoning_receipt', {})}`",
        f"- next_action: {replay_next_action}",
    ])
    semantic = payload.get("semantic_retrieval_wiring") if isinstance(payload.get("semantic_retrieval_wiring"), dict) else {}
    lines.extend([
        "",
        "## Semantic Retrieval Wiring",
        "",
        f"- status: `{semantic.get('status')}`",
        f"- wired_count: `{semantic.get('wired_count')}` / `{semantic.get('proof_loop_count')}`",
        f"- credit_boundary: {semantic.get('credit_boundary')}",
    ])
    lines.extend([
        "",
        "## PR A1 Candidate",
        "",
        f"- status: `{pr.get('status')}`",
        f"- path: `{(pr.get('static_audit') or {}).get('path')}`",
        f"- sorry_count: `{(pr.get('static_audit') or {}).get('sorry_count')}`",
        f"- admit_count: `{(pr.get('static_audit') or {}).get('admit_count')}`",
        f"- axiom_decl_count: `{(pr.get('static_audit') or {}).get('axiom_decl_count')}`",
        f"- print_axioms_count: `{(pr.get('static_audit') or {}).get('print_axioms_count')}`",
        f"- compile_l3_status: `{(pr.get('compile_l3_audit') or {}).get('status')}`",
        f"- next_action: {pr.get('next_action')}",
    ])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_competitive_inventory_") as td:
        root = Path(td)
        proofs = root / "ZtareProofs"
        proofs.mkdir()
        pr = proofs / "PR_A1_BohrCoeffExpNe_Discharge.lean"
        pr.write_text("theorem ok : True := by\n  trivial\n#print axioms ok\n", encoding="utf-8")
        open_file = proofs / "open_demo.lean"
        open_file.write_text("theorem open_demo : True := by\n  sorry\n", encoding="utf-8")
        escape = root / "escape.json"
        escape.write_text(json.dumps({
            "results": [{"row_id": "r1", "closure_verdict": "OPEN_GAP_REPORT", "compiled_any": False, "proposed_lemmas": ["missing_x"]}]
        }), encoding="utf-8")
        replay = root / "replay.json"
        replay.write_text(json.dumps({
            "results": [{"row_id": "r2", "verdict": "CLOSED", "compiled_any": True}]
        }), encoding="utf-8")
        out = root / "out.json"
        md = root / "out.md"
        payload = build(argparse.Namespace(
            escape_route=str(escape),
            route_c_replay=str(replay),
            ztare_proofs=str(proofs),
            pr_a1=str(pr),
            pr_a1_audit=str(root / "missing_audit.json"),
            route_c_gap_tasks=str(root / "missing_tasks.json"),
            route_c_hold_synthesis=str(root / "missing_synthesis.json"),
            route_c_exact_gap_replay_prep=str(root / "missing_replay_prep.json"),
            route_c_exact_gap_replay_probe=str(root / "missing_replay_probe.json"),
            out=str(out),
            md=str(md),
        ))
        assert payload["summary"]["route_c_gap_report_count"] == 1, payload
        assert payload["summary"]["route_c_compiled_or_closed_count"] == 1, payload
        assert payload["summary"]["ztare_lean_file_count"] == 2, payload
        assert payload["summary"]["semantic_retrieval_wiring_status"] in {"pass", "gap"}, payload
        assert payload["summary"]["pr_a1_status"] == "static_sorry_free_needs_compile_and_l3_audit", payload
        write_markdown(md, payload)
        assert "route_c_gap_report_count" in md.read_text(encoding="utf-8")
    print("leanmill_competitive_inventory self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escape-route", default=DEFAULT_ESCAPE_ROUTE)
    ap.add_argument("--route-c-replay", default=DEFAULT_ROUTE_C_REPLAY)
    ap.add_argument("--ztare-proofs", default=DEFAULT_ZTARE_PROOFS)
    ap.add_argument("--pr-a1", default=DEFAULT_PR_A1)
    ap.add_argument("--pr-a1-audit", default=DEFAULT_PR_A1_AUDIT)
    ap.add_argument("--route-c-gap-tasks", default=DEFAULT_ROUTE_C_GAP_TASKS)
    ap.add_argument("--route-c-hold-synthesis", default=DEFAULT_ROUTE_C_HOLD_SYNTHESIS)
    ap.add_argument("--route-c-exact-gap-replay-prep", default=DEFAULT_ROUTE_C_EXACT_GAP_REPLAY_PREP)
    ap.add_argument("--route-c-exact-gap-replay-probe", default=DEFAULT_ROUTE_C_EXACT_GAP_REPLAY_PROBE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.md, payload)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "route_c_gap_report_count": payload["summary"]["route_c_gap_report_count"],
        "route_c_compiled_or_closed_count": payload["summary"]["route_c_compiled_or_closed_count"],
        "ztare_lean_file_count": payload["summary"]["ztare_lean_file_count"],
        "semantic_retrieval_wiring_status": payload["summary"]["semantic_retrieval_wiring_status"],
        "pr_a1_status": payload["summary"]["pr_a1_status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
