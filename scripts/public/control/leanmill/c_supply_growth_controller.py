#!/usr/bin/env python3
"""Closed-loop controller for strict C-discriminating supply growth.

This controller mechanizes the loop that should not require GM hand-work:
strict slice prep -> family-template backfill -> governed static controls ->
family-spec probes -> strict slice prep. It grants no proof credit itself.
Only the existing slice-prep gate can mark rows credit-ready.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from ztare.leanmill.contracts import source_family_match
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
    from ztare.leanmill.contracts import source_family_match

from leanmill_factory_config import (
    FACTORY_POLICY,
    apply_profile_section,
    c_supply_breadth_policy_from_policy,
    multi_node_routing_plan,
    read_policy,
)
from leanmill_source_routing import (
    promote_recent_ratified_seed_records,
    recent_ratified_seed_families,
    source_growth_routing_policy,
)
from leanmill_c_supply_credit import (
    probe_verified_pending_static_row as _probe_verified_pending_static_row,
    probe_verified_row as _probe_verified_row,
    static_sweep_owed_row as _static_sweep_owed_row,
    strict_credit_ready_row as _credit_ready_row,
)
from leanmill_paths import DATA_DIR, REPAIR_FAMILY_REGISTRY

DEFAULT_OUT = f"{DATA_DIR}/c_supply_growth_controller.json"
DEFAULT_WORK_DIR = "/tmp/rung1/leanmill_c_supply_growth_controller"
DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json"
DEFAULT_SPEC_DIR = "analytics/public/leanmill/repair_families"
DEFAULT_CONTRACT = f"{DATA_DIR}/evaluation_harness_contract.json"
DEFAULT_UPSTREAM_RATER = f"{DATA_DIR}/c_supply_upstream_rater.json"
DEFAULT_EXTERNAL_SOURCE_SCOUT_PLAN = f"{DATA_DIR}/external_source_scout_seed_plan.json"
LEGACY_STRUCTURAL_SUPPLY_STATUSES = {"c_discriminating_supply_verified"}
DEFAULT_SELECTION_SCORE_FIELDS = [
    {"metric": "credit_ready_count", "direction": "desc"},
    {"metric": "credit_ready_unique_family_count", "direction": "desc"},
    {"metric": "credit_ready_source_file_count", "direction": "desc"},
    {"metric": "probe_verified_pending_static_count", "direction": "desc"},
    {"metric": "probe_seedable_count", "direction": "desc"},
    {"metric": "source_demand_family_count", "direction": "desc"},
    {"metric": "eligible_unique_family_count", "direction": "desc"},
    {"metric": "eligible_count", "direction": "desc"},
    {"metric": "static_sweep_owed_count", "direction": "asc"},
    {"metric": "probe_terminal_nonuseful_count", "direction": "asc"},
]


def _read_json(path: str | Path) -> Any:
    if not str(path):
        return None
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _kill_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        try:
            proc.kill()
        except ProcessLookupError:
            return


def _run(cmd: list[str], *, timeout_s: int, dry_run: bool = False) -> dict[str, Any]:
    rec = {"cmd": cmd, "timeout_s": timeout_s, "dry_run": dry_run}
    if dry_run:
        rec.update({"returncode": 0, "stdout_tail": "", "stderr_tail": ""})
        return rec
    started = time.time()
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        stdout, stderr = proc.communicate(timeout=max(1, int(timeout_s)))
        rec.update({
            "returncode": proc.returncode,
            "wall_time_s": round(time.time() - started, 3),
            "stdout_tail": _tail(stdout or ""),
            "stderr_tail": _tail(stderr or ""),
        })
    except subprocess.TimeoutExpired:
        if proc is not None:
            _kill_process_group(proc)
            stdout, stderr = proc.communicate()
        else:
            stdout, stderr = "", ""
        rec.update({
            "returncode": 124,
            "wall_time_s": round(time.time() - started, 3),
            "stdout_tail": _tail(stdout or ""),
            "stderr_tail": _tail(stderr or ""),
            "timed_out": True,
            "timeout_kill": "process_group",
        })
    return rec


def _command_applied(rec: dict[str, Any]) -> bool:
    return int(rec.get("returncode") or 0) == 0 and not bool(rec.get("dry_run"))


def _checkpoint_has_records(path: str | Path) -> bool:
    p = Path(path)
    return p.exists() and p.is_file() and p.stat().st_size > 0


def _run_parallel(cmds: list[list[str]], *, timeout_s: int, parallelism: int, dry_run: bool = False) -> list[dict[str, Any]]:
    if not cmds:
        return []
    if dry_run or parallelism <= 1:
        return [_run(cmd, timeout_s=timeout_s, dry_run=dry_run) for cmd in cmds]
    results: list[dict[str, Any]] = []
    width = max(1, int(parallelism))
    for start_idx in range(0, len(cmds), width):
        batch = cmds[start_idx:start_idx + width]
        procs: list[tuple[list[str], float, subprocess.Popen[str]]] = []
        for cmd in batch:
            started = time.time()
            proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            procs.append((cmd, started, proc))
        for cmd, started, proc in procs:
            rec = {"cmd": cmd, "timeout_s": timeout_s, "dry_run": False}
            remaining = max(1, int(timeout_s) - int(time.time() - started))
            try:
                stdout, stderr = proc.communicate(timeout=remaining)
                rec.update({
                    "returncode": proc.returncode,
                    "wall_time_s": round(time.time() - started, 3),
                    "stdout_tail": _tail(stdout or ""),
                    "stderr_tail": _tail(stderr or ""),
                })
            except subprocess.TimeoutExpired:
                _kill_process_group(proc)
                stdout, stderr = proc.communicate()
                rec.update({
                    "returncode": 124,
                    "wall_time_s": round(time.time() - started, 3),
                    "stdout_tail": _tail(stdout or ""),
                    "stderr_tail": _tail(stderr or ""),
                    "timed_out": True,
                    "timeout_kill": "process_group",
                })
            results.append(rec)
    return results


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key in ("rows", "results", "row_results", "qualified_rows", "corpus", "items"):
        vals = obj.get(key)
        if isinstance(vals, list):
            rows.extend(x for x in vals if isinstance(x, dict))
    return rows


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _static_executable_row_ids(checkpoint: str | Path) -> set[str]:
    bad_exits = {"harness_candidate_build_failure", "target_not_executable"}
    out: set[str] = set()
    for rec in _read_jsonl(checkpoint):
        row_id = str(rec.get("row_id") or "")
        if not row_id or str(rec.get("arm") or "") not in {"public_tool_static", "governed_public_tool_static"}:
            continue
        if str(rec.get("learning_exit") or "") in bad_exits:
            continue
        if int(rec.get("build_failure_count") or 0) > 0:
            continue
        out.add(row_id)
    return out


def _stamp_static_executability(row_context: str | Path, checkpoint: str | Path, out: str | Path) -> str:
    obj = _read_json(row_context) or {}
    executable = _static_executable_row_ids(checkpoint)
    changed = 0
    rows = []
    for row in _iter_rows(obj):
        rec = dict(row)
        row_id = _row_id(rec)
        if row_id in executable and not rec.get("target_resolution_status"):
            rec["target_resolution_status"] = "pass"
            rec["target_resolution_source"] = "static_tool_candidate_built_without_build_failure"
            changed += 1
        rows.append(rec)
    stamped = dict(obj) if isinstance(obj, dict) else {}
    stamped["schema"] = "leanmill-c-supply-growth-static-executable-row-context-v1"
    stamped["source_row_context"] = str(row_context)
    stamped["checkpoint"] = str(checkpoint)
    stamped["static_executable_stamp_count"] = changed
    stamped["rows"] = rows
    _write_json(out, stamped)
    return str(out)


def _merge_row_context(base: str | Path, extra_paths: list[str], out: str | Path) -> str:
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in _iter_rows(_read_json(base) or {}):
        row_id = _row_id(row)
        if row_id:
            rec = dict(row)
            rec["row_id"] = row_id
            rows_by_id[row_id] = rec
    for path in extra_paths:
        for row in _iter_rows(_read_json(path) or {}):
            row_id = _row_id(row)
            if row_id and row_id not in rows_by_id:
                rec = dict(row)
                rec["row_id"] = row_id
                rows_by_id[row_id] = rec
    merged = {
        "schema": "leanmill-c-supply-growth-merged-row-context-v1",
        "base_row_context": str(base),
        "extra_row_contexts": extra_paths,
        "row_count": len(rows_by_id),
        "rows": sorted(rows_by_id.values(), key=lambda row: str(row.get("row_id") or "")),
    }
    _write_json(out, merged)
    return str(out)


def _int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _effective_target_credit_ready_rows(breadth_policy: dict[str, Any], requested_target: int) -> int:
    target = max(int(requested_target), _metric_int(breadth_policy, "target_credit_ready_rows"))
    if bool(breadth_policy.get("continue_after_minimum_floor")):
        target = max(target, _metric_int(breadth_policy, "growth_goal_credit_ready_rows"))
    return max(1, target)


def _row_families(row: dict[str, Any], *, credit_ready_only: bool = False) -> list[str]:
    keys = (
        ("probe_verified_families", "families")
        if credit_ready_only
        else (
            "probe_verified_families",
            "matched_families",
            "families_with_positive_template",
            "families",
        )
    )
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        value = row.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            family = str(item or "").strip()
            if family and family not in seen:
                out.append(family)
                seen.add(family)
    return out


def _source_file(row: dict[str, Any]) -> str:
    return str(row.get("source_file") or row.get("source_path") or row.get("source") or "").strip()


def _source_root(source_file: str) -> str:
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
def _selection_metrics(path: str | Path) -> dict[str, Any]:
    obj = _read_json(path) or {}
    selected = [r for r in (obj.get("selected_rows") or []) if isinstance(r, dict)]
    probe_owed_rows = [r for r in selected if _probe_owed_row(r)]
    probe_seedable_rows = [r for r in probe_owed_rows if not _static_sweep_owed_row(r)]
    probe_verified_rows = [r for r in selected if _probe_verified_row(r)]
    probe_verified_pending_static_rows = [r for r in selected if _probe_verified_pending_static_row(r)]
    raw_credit_ready_rows = [r for r in selected if _credit_ready_row(r)]
    credit_ready_by_id: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(raw_credit_ready_rows):
        row_id = _row_id(row) or f"__row_index_{idx}"
        credit_ready_by_id.setdefault(row_id, row)
    credit_ready_rows = list(credit_ready_by_id.values())
    credit_ready_count_source = "selected_rows" if selected else "selection_summary"
    credit_ready_count = len(credit_ready_rows) if selected else _int(obj, "credit_ready_count")
    credit_ready_family_counts: Counter[str] = Counter()
    eligible_family_counts: Counter[str] = Counter()
    credit_ready_source_files: set[str] = set()
    credit_ready_source_roots: set[str] = set()
    source_demand_families = {
        str(req.get("family") or "").strip()
        for req in (obj.get("source_demand_requests") or [])
        if isinstance(req, dict) and str(req.get("family") or "").strip()
    }
    for row in credit_ready_rows:
        credit_ready_family_counts.update(_row_families(row, credit_ready_only=True))
        source_file = _source_file(row)
        if source_file:
            credit_ready_source_files.add(source_file)
            root = _source_root(source_file)
            if root:
                credit_ready_source_roots.add(root)
    for row in selected:
        if row.get("eligible"):
            eligible_family_counts.update(_row_families(row))
    legacy_supply_rows = [
        r for r in selected
        if str(r.get("c_discriminating_evidence_status") or "") in LEGACY_STRUCTURAL_SUPPLY_STATUSES
    ]
    top_credit_ready_family_count = max(credit_ready_family_counts.values() or [0])
    return {
        "path": str(path),
        "status": obj.get("status"),
        "credit_ready_count": credit_ready_count,
        "credit_ready_count_source": credit_ready_count_source,
        "credit_ready_unique_family_count": len(credit_ready_family_counts),
        "credit_ready_source_file_count": len(credit_ready_source_files),
        "credit_ready_source_root_count": len(credit_ready_source_roots),
        "credit_ready_top_family_row_count": top_credit_ready_family_count,
        "credit_ready_family_counts": dict(sorted(credit_ready_family_counts.items())),
        "eligible_count": _int(obj, "eligible_count"),
        "eligible_unique_family_count": len(eligible_family_counts),
        "selected_count": _int(obj, "selected_count"),
        "probe_pending_count": _int(obj, "probe_pending_count"),
        "probe_verified_count": len(probe_verified_rows) if selected else _int(obj, "probe_verified_count"),
        "probe_verified_pending_static_count": len(probe_verified_pending_static_rows) if selected else _int(obj, "probe_verified_pending_static_count"),
        "probe_terminal_nonuseful_count": _int(obj, "probe_terminal_nonuseful_count"),
        "blockers_by_reason": obj.get("blockers_by_reason") or {},
        "source_demand_family_count": len(source_demand_families),
        "static_sweep_owed_count": sum(1 for r in selected if _static_sweep_owed_row(r)),
        "probe_owed_count": len(probe_owed_rows),
        "probe_seedable_count": len(probe_seedable_rows),
        "legacy_structural_supply_probe_owed_count": len(legacy_supply_rows),
    }


def _selection_score_policy(args: argparse.Namespace) -> dict[str, Any]:
    policy = read_policy(getattr(args, "factory_policy", FACTORY_POLICY))
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("c_supply_selection_score") if isinstance(operations.get("c_supply_selection_score"), dict) else {}
    raw_fields = obj.get("fields") if isinstance(obj.get("fields"), list) else []
    fields: list[dict[str, str]] = []
    for raw in raw_fields:
        if not isinstance(raw, dict):
            continue
        metric = str(raw.get("metric") or "").strip()
        direction = str(raw.get("direction") or "desc").strip().lower()
        if not metric or direction not in {"asc", "desc"}:
            continue
        fields.append({"metric": metric, "direction": direction})
    if not fields:
        fields = [dict(field) for field in DEFAULT_SELECTION_SCORE_FIELDS]
    return {
        "schema": str(obj.get("schema") or "leanmill-c-supply-selection-score-v1"),
        "source": "factory_policy" if raw_fields else "controller_default",
        "ordering_rule": str(obj.get("ordering_rule") or "Compare fields in order; desc means higher is preferred, asc means lower is preferred."),
        "credit_boundary": str(obj.get("credit_boundary") or "Selection score chooses routing state only; it grants no proof or benchmark credit."),
        "fields": fields,
    }


def _controller_operating_policy(args: argparse.Namespace) -> dict[str, Any]:
    """Expose live generation/routing knobs as a non-credit receipt."""
    return {
        "schema": "leanmill-c-supply-growth-operating-policy-v1",
        "source": "factory_policy.profile.c_supply_growth_controller",
        "credit_boundary": (
            "Controller operating policy only routes generation/static spend. "
            "Strict C credit still requires deterministic static/probe/governance receipts."
        ),
        "upstream_rater": {
            "mode": str(getattr(args, "upstream_rater_mode", "off")),
            "run_model": bool(getattr(args, "upstream_rater_run_model", False)),
            "model": str(getattr(args, "upstream_rater_model", "")),
            "reasoning_effort": str(getattr(args, "upstream_rater_reasoning_effort", "")),
            "timeout_s": int(getattr(args, "upstream_rater_timeout_s", 0) or 0),
            "max_candidates": int(getattr(args, "upstream_rater_max_candidates", 0) or 0),
            "rationale": (
                "Agentic ranking is allowed to order upstream family-corpus spend when "
                "its JSON validates. Invalid output falls back to deterministic order, "
                "and the rater never grants proof, benchmark, governance, or C credit."
            ),
        },
        "source_static_mining": {
            "source_parallel_families": int(getattr(args, "source_parallel_families", 1) or 1),
            "source_rows_per_family": int(getattr(args, "source_rows_per_family", 0) or 0),
            "source_min_signature_hits": int(getattr(args, "source_min_signature_hits", 0) or 0),
            "source_template_min_hit_count": int(getattr(args, "source_template_min_hit_count", 0) or 0),
            "source_family_match_policy": source_family_match.policy_from_mapping(vars(args)).as_receipt(),
            "static_max_tool_calls": int(getattr(args, "static_max_tool_calls", 0) or 0),
            "static_per_candidate_timeout_s": int(getattr(args, "static_per_candidate_timeout_s", 0) or 0),
            "static_row_wall_timeout_s": int(getattr(args, "static_row_wall_timeout_s", 0) or 0),
            "static_wall_timeout_s": int(getattr(args, "static_wall_timeout_s", 0) or 0),
            "rationale": (
                "Source-static mining is deterministic verification of generated source inventory. "
                "Timeouts and breadth limits belong in policy so failed conversion can be "
                "diagnosed as budget, quality, template, or probe debt instead of launch drift."
            ),
        },
    }


def _metric_int(metrics: dict[str, Any], key: str) -> int:
    try:
        return int(metrics.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _selection_score(metrics: dict[str, Any], policy: dict[str, Any]) -> tuple[int, ...]:
    score: list[int] = []
    fields = policy.get("fields") if isinstance(policy.get("fields"), list) else []
    for field in fields:
        if not isinstance(field, dict):
            continue
        value = _metric_int(metrics, str(field.get("metric") or ""))
        score.append(value if str(field.get("direction") or "desc") == "desc" else -value)
    return tuple(score)


def _target_readiness_decision(
    metrics: dict[str, Any],
    breadth_policy: dict[str, Any],
    *,
    target_credit_ready_rows: int,
) -> dict[str, Any]:
    target_rows = _effective_target_credit_ready_rows(breadth_policy, target_credit_ready_rows)
    checks = {
        "credit_ready_rows": {
            "actual": _metric_int(metrics, "credit_ready_count"),
            "target": target_rows,
        },
        "credit_ready_families": {
            "actual": _metric_int(metrics, "credit_ready_unique_family_count"),
            "target": _metric_int(breadth_policy, "target_credit_ready_family_count"),
        },
        "credit_ready_source_files": {
            "actual": _metric_int(metrics, "credit_ready_source_file_count"),
            "target": _metric_int(breadth_policy, "target_credit_ready_source_file_count"),
        },
        "credit_ready_source_roots": {
            "actual": _metric_int(metrics, "credit_ready_source_root_count"),
            "target": _metric_int(breadth_policy, "target_credit_ready_source_root_count"),
        },
    }
    missing = [
        key for key, check in checks.items()
        if int(check.get("actual") or 0) < int(check.get("target") or 0)
    ]
    return {
        "schema": "leanmill-c-supply-target-readiness-v1",
        "ready": not missing,
        "missing": missing,
        "checks": checks,
        "credit_boundary": "Target readiness is a controller stop rule only; existing gates decide C credit.",
    }


def _source_growth_decision(
    metrics: dict[str, Any],
    breadth_policy: dict[str, Any],
    *,
    target_credit_ready_rows: int,
) -> dict[str, Any]:
    readiness = _target_readiness_decision(
        metrics,
        breadth_policy,
        target_credit_ready_rows=target_credit_ready_rows,
    )
    blockers = metrics.get("blockers_by_reason") if isinstance(metrics.get("blockers_by_reason"), dict) else {}
    reasons = list(readiness["missing"])
    if _metric_int(metrics, "source_demand_family_count") < _metric_int(breadth_policy, "target_upstream_source_demand_family_count"):
        reasons.append("upstream_source_demand_families")
    if _metric_int(blockers, "no_positive_family_template") > 0:
        reasons.append("no_positive_family_template_pressure")
    mode = str(breadth_policy.get("source_growth_trigger_mode") or "breadth_or_count_gap")
    if mode == "off":
        needed = False
    elif mode == "when_unblocked":
        needed = bool(reasons) and _metric_int(metrics, "static_sweep_owed_count") == 0 and _metric_int(metrics, "probe_owed_count") == 0
    elif mode == "always":
        needed = _metric_int(metrics, "credit_ready_count") < _effective_target_credit_ready_rows(breadth_policy, target_credit_ready_rows)
    else:
        needed = bool(reasons)
    return {
        "schema": "leanmill-c-supply-source-growth-decision-v1",
        "needed": needed,
        "mode": mode,
        "reasons": sorted(set(reasons)),
        "rule": str(breadth_policy.get("source_growth_trigger_rule") or ""),
        "target_readiness": readiness,
        "credit_boundary": "Source growth is routing only; it grants no C, proof, benchmark, or governance credit.",
    }


def _open_work_count(queue_db: str | Path, *, kinds: set[str]) -> int:
    if not kinds:
        return 0
    p = Path(queue_db)
    if not p.exists():
        return 0
    placeholders = ",".join("?" for _ in kinds)
    try:
        cx = sqlite3.connect(str(p))
        row = cx.execute(
            f"SELECT COUNT(*) FROM work_items WHERE kind IN ({placeholders}) AND status IN ('queued','running')",
            tuple(sorted(kinds)),
        ).fetchone()
        return int(row[0] if row else 0)
    except sqlite3.Error:
        return 0
    finally:
        try:
            cx.close()
        except Exception:
            pass


def _external_source_scout_cmd(args: argparse.Namespace, *, out: str, max_enqueued: int, run_id: str) -> list[str]:
    scout_policy = _external_source_scout_policy(args)
    return [
        sys.executable,
        "scripts/public/control/leanmill/external_source_scout_seeder.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out,
        "--run-id", run_id,
        "--runtimes", str(scout_policy["external_source_scout_runtimes"]),
        "--max-families", str(max(1, int(scout_policy["external_source_scout_max_families"]))),
        "--tasks-per-family", str(max(1, int(scout_policy["external_source_scout_tasks_per_family"]))),
        "--max-enqueued", str(max(0, int(max_enqueued))),
        "--agent-max-wall-time-s", str(max(1, int(getattr(args, "agent_max_wall_time_s", 1200)))),
        "--agent-max-iterations", str(max(1, int(getattr(args, "agent_max_iterations", 3)))),
        "--factory-policy", args.factory_policy,
        "--enqueue",
    ]


def _c_supply_profile_runner_policy(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return {}
    policy = read_policy(getattr(args, "factory_policy", FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if isinstance(policy.get("profiles"), dict) else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    return runner if isinstance(runner, dict) else {}


def _external_source_scout_policy(args: argparse.Namespace) -> dict[str, Any]:
    runner = _c_supply_profile_runner_policy(args)

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(runner.get(key) if runner.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    return {
        "schema": "leanmill-external-source-scout-routing-policy-v1",
        "source": "factory_policy.profile.runner" if runner else "controller_default",
        "seed_external_source_scouts": bool(runner.get("seed_external_source_scouts", True)),
        "external_source_scout_floor": max(0, int_value("external_source_scout_floor", 4)),
        "external_source_scout_max_enqueued": max(0, int_value("external_source_scout_max_enqueued", 4)),
        "external_source_scout_max_families": max(0, int_value("external_source_scout_max_families", 4)),
        "external_source_scout_runtimes": str(runner.get("external_source_scout_runtimes") or "codex"),
        "external_source_scout_tasks_per_family": max(1, int_value("external_source_scout_tasks_per_family", 1)),
        "credit_boundary": "Policy routes outside source scouts only; scouts emit source_request inventory and never grant credit.",
    }


def _c_supply_controller_policy(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return {}
    policy = read_policy(getattr(args, "factory_policy", FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if isinstance(policy.get("profiles"), dict) else {}
    section = profile.get("c_supply_growth_controller") if isinstance(profile, dict) else {}
    return section if isinstance(section, dict) else {}


def _previous_running_state(args: argparse.Namespace) -> dict[str, Any]:
    policy = _c_supply_controller_policy(args)
    if "resume_previous_running_state" not in policy:
        return {"resumed": False, "reason": "missing_policy_key_resume_previous_running_state"}
    if not bool(policy.get("resume_previous_running_state")):
        return {"resumed": False, "reason": "disabled_by_policy"}
    out_path = Path(str(getattr(args, "out", "") or ""))
    if not out_path.exists() or not out_path.is_file():
        return {"resumed": False, "reason": "missing_previous_receipt"}
    previous = _read_json(out_path) or {}
    if not isinstance(previous, dict) or previous.get("schema") != "leanmill-c-supply-growth-controller-v1":
        return _recent_stage_local_resume_state(args, policy=policy, fallback_reason="invalid_previous_receipt")
    if str(previous.get("status") or "") != "running":
        return _recent_stage_local_resume_state(args, policy=policy, fallback_reason="previous_not_running")
    try:
        max_age_s = int(policy.get("resume_previous_running_state_max_age_s") or 86400)
    except (TypeError, ValueError):
        max_age_s = 86400
    generated = int(previous.get("generated_at_epoch") or 0)
    if generated and max_age_s > 0 and int(time.time()) - generated > max_age_s:
        return _recent_stage_local_resume_state(
            args,
            policy=policy,
            fallback_reason="previous_receipt_too_old",
            fallback_extra={"generated_at_epoch": generated, "max_age_s": max_age_s},
        )
    selection = str(previous.get("latest_selection") or "")
    checkpoint = str(previous.get("latest_checkpoint") or "")
    row_context = str(previous.get("latest_row_context") or "")
    stage_resume = _stage_local_resume_state(previous)
    if stage_resume.get("resumed"):
        checkpoint = str(stage_resume.get("latest_checkpoint") or checkpoint)
        row_context = str(stage_resume.get("latest_row_context") or row_context)
    best_selection = str(previous.get("best_selection") or "")
    best_checkpoint = str(previous.get("best_checkpoint") or "")
    best_row_context = str(previous.get("best_row_context") or "")
    required = {"latest_selection": selection, "latest_checkpoint": checkpoint}
    missing = [key for key, path in required.items() if not path or not Path(path).exists()]
    if missing:
        return _recent_stage_local_resume_state(
            args,
            policy=policy,
            fallback_reason="missing_previous_artifact",
            fallback_extra={"missing": missing},
        )
    if row_context and not Path(row_context).exists():
        row_context = str(getattr(args, "row_context", "") or "")
    if best_selection and not Path(best_selection).exists():
        best_selection = ""
    if best_checkpoint and not Path(best_checkpoint).exists():
        best_checkpoint = ""
    if best_row_context and not Path(best_row_context).exists():
        best_row_context = ""
    return {
        "resumed": True,
        "source_receipt": str(out_path),
        "generated_at_epoch": generated,
        "previous_stage": previous.get("current_stage"),
        "stage_local_resume": stage_resume,
        "latest_selection": selection,
        "latest_checkpoint": checkpoint,
        "latest_row_context": row_context,
        "best_selection": best_selection,
        "best_checkpoint": best_checkpoint,
        "best_row_context": best_row_context,
        "credit_boundary": "Resume preserves controller routing state only; strict C credit still comes from slice/static/probe receipts.",
    }


def _stage_local_resume_state(previous: dict[str, Any]) -> dict[str, Any]:
    """Recover stage-local controller artifacts not yet promoted to latest_*.

    A restart can intentionally stop the controller after a source-candidate
    governed-static checkpoint is written but before post-source slice prep
    publishes that checkpoint as `latest_checkpoint`. The checkpoint is
    deterministic routing state and should be reused rather than discarded.
    """
    work_dir = Path(str(previous.get("work_invocation_dir") or ""))
    if not work_dir.exists() or not work_dir.is_dir():
        return {"resumed": False, "reason": "missing_work_invocation_dir"}
    candidates = sorted(
        work_dir.glob("round_*.source_candidates.static_checkpoint.jsonl"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    checkpoint = ""
    for path in candidates:
        if _checkpoint_has_records(path):
            checkpoint = str(path)
            break
    if not checkpoint:
        return {"resumed": False, "reason": "no_stage_checkpoint_with_records"}
    row_context = ""
    for pattern in (
        "round_*.source_static_candidates.selection.json",
        "round_*.source_augmented_executable.rows.json",
        "round_*.source_augmented.rows.json",
        "round_*.post_template.rows.json",
        "round_*.post_static.rows.json",
    ):
        matches = sorted(
            work_dir.glob(pattern),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
        if matches:
            row_context = str(matches[0])
            break
    return {
        "resumed": True,
        "reason": "stage_local_source_candidate_static_checkpoint",
        "latest_checkpoint": checkpoint,
        "latest_row_context": row_context,
        "credit_boundary": "Stage-local resume preserves deterministic routing state only; strict C credit still comes from slice/static/probe receipts.",
    }


def _recent_stage_local_resume_state(
    args: argparse.Namespace,
    *,
    policy: dict[str, Any],
    fallback_reason: str,
    fallback_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        max_age_s = int(policy.get("resume_previous_running_state_max_age_s") or 86400)
    except (TypeError, ValueError):
        max_age_s = 86400
    now = time.time()
    work_dir = Path(str(getattr(args, "work_dir", "") or ""))
    candidates: list[Path] = []
    if work_dir.exists() and work_dir.is_dir():
        candidates = sorted(
            work_dir.glob("run_*/round_*.source_candidates.static_checkpoint.jsonl"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
    for checkpoint in candidates:
        try:
            age_s = max(0, int(now - checkpoint.stat().st_mtime))
        except OSError:
            continue
        if max_age_s > 0 and age_s > max_age_s:
            continue
        if not _checkpoint_has_records(checkpoint):
            continue
        stage_state = _stage_local_resume_state({"work_invocation_dir": str(checkpoint.parent)})
        if not stage_state.get("resumed"):
            continue
        selection = str(getattr(args, "selection", "") or "")
        if not selection or not Path(selection).exists():
            continue
        return {
            "resumed": True,
            "source_receipt": str(getattr(args, "out", "") or ""),
            "generated_at_epoch": 0,
            "previous_stage": "",
            "stage_local_resume": {
                **stage_state,
                "source": "recent_work_dir_scan",
                "checkpoint_age_s": age_s,
            },
            "latest_selection": selection,
            "latest_checkpoint": str(stage_state.get("latest_checkpoint") or checkpoint),
            "latest_row_context": str(stage_state.get("latest_row_context") or getattr(args, "row_context", "") or ""),
            "best_selection": "",
            "best_checkpoint": "",
            "best_row_context": "",
            "fallback_reason": fallback_reason,
            **(fallback_extra or {}),
            "credit_boundary": "Resume preserves controller routing state only; strict C credit still comes from slice/static/probe receipts.",
        }
    return {
        "resumed": False,
        "reason": fallback_reason,
        **(fallback_extra or {}),
        "recent_stage_local_resume": {"resumed": False, "reason": "no_recent_stage_checkpoint_with_records"},
    }


def _probe_owed_row(row: dict[str, Any]) -> bool:
    status = str(row.get("c_discriminating_evidence_status") or "")
    return bool(
        status.endswith("pending_probe")
        or "pending_static_sweep_and_probe" in status
        or status in LEGACY_STRUCTURAL_SUPPLY_STATUSES
        or row.get("family_spec_probe_required_before_c_credit")
    )



def _probe_owed_selection(selection: str | Path, out: str | Path) -> tuple[str, int]:
    obj = _read_json(selection) or {}
    rows = [r for r in (obj.get("selected_rows") or obj.get("rows") or []) if isinstance(r, dict)]
    owed_rows = [r for r in rows if _probe_owed_row(r) and not _static_sweep_owed_row(r)]
    if not owed_rows:
        return str(selection), 0
    owed_ids = {str(r.get("row_id") or r.get("id") or r.get("target_id") or "") for r in owed_rows}
    owed_ids.discard("")
    filtered = dict(obj)
    filtered["selected_rows"] = owed_rows
    if "rows" in filtered:
        filtered["rows"] = [
            r for r in (filtered.get("rows") or [])
            if isinstance(r, dict) and str(r.get("row_id") or r.get("id") or r.get("target_id") or "") in owed_ids
        ]
    if "selected_rows_order" in filtered:
        filtered["selected_rows_order"] = [row_id for row_id in (filtered.get("selected_rows_order") or []) if str(row_id) in owed_ids]
    filtered["selected_count"] = len(owed_rows)
    filtered["probe_pending_count"] = len(owed_rows)
    filtered["parent_selection"] = str(selection)
    filtered["selection_filter"] = "probe_owed_rows_only"
    _write_json(out, filtered)
    return str(out), len(owed_rows)

def _parse_stdout_json(rec: dict[str, Any]) -> dict[str, Any]:
    text = str(rec.get("stdout_tail") or "")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        return obj if isinstance(obj, dict) else {}
    return {}


def _no_enqueue_cmd(cmd: list[str], *, out: str | None = None, md: str | None = None) -> list[str]:
    """Run the same station as a deterministic preview before spending agents."""
    preview = list(cmd)
    if "--enqueue" in preview:
        preview.remove("--enqueue")
    if "--max-enqueued" in preview:
        idx = preview.index("--max-enqueued")
        if idx + 1 < len(preview):
            preview[idx + 1] = "0"
    if out and "--out" in preview:
        idx = preview.index("--out")
        if idx + 1 < len(preview):
            preview[idx + 1] = out
    if md and "--md" in preview:
        idx = preview.index("--md")
        if idx + 1 < len(preview):
            preview[idx + 1] = md
    return preview


def _probe_seed_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    jobs = [job for job in (report.get("jobs") or []) if isinstance(job, dict)] if isinstance(report, dict) else []
    unresolved_reason_counts: dict[str, int] = {}
    missing_rows: list[dict[str, Any]] = []
    selected_row_count = 0
    target_row_count = 0
    for job in jobs:
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        meta = payload.get("probe_corpus_meta") if isinstance(payload.get("probe_corpus_meta"), dict) else {}
        selected_row_count += int(meta.get("selected_row_count") or 0)
        target_row_count += int(meta.get("target_row_count") or 0)
        for item in meta.get("unresolved_row_reasons") or []:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason") or "unknown")
            unresolved_reason_counts[reason] = unresolved_reason_counts.get(reason, 0) + 1
            if len(missing_rows) < 30:
                missing_rows.append({
                    "row_id": item.get("row_id"),
                    "reason": reason,
                    "family": payload.get("family"),
                    "work_id": job.get("work_id"),
                })
    return {
        "schema": "leanmill-c-supply-probe-seed-summary-v1",
        "generated_job_count": int(report.get("generated_job_count") or 0) if isinstance(report, dict) else 0,
        "job_count": int(report.get("job_count") or 0) if isinstance(report, dict) else 0,
        "enqueued": int(report.get("enqueued") or 0) if isinstance(report, dict) else 0,
        "selected_row_count": selected_row_count,
        "target_row_count": target_row_count,
        "unresolved_row_count": sum(unresolved_reason_counts.values()),
        "unresolved_reason_counts": dict(sorted(unresolved_reason_counts.items())),
        "unresolved_rows": missing_rows,
        "credit_boundary": "probe seed diagnostics only; no benchmark or proof credit",
    }


def _prep_cmd(args: argparse.Namespace, *, checkpoint: str, out: str, md: str, row_context_out: str, row_context: str | None = None) -> list[str]:
    return [
        sys.executable,
        "scripts/public/control/leanmill/c_discriminating_slice_prep.py",
        "--checkpoint", checkpoint,
        "--row-context", row_context or args.row_context,
        "--spec-dir", args.spec_dir,
        "--registry", args.registry,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--out", out,
        "--md", md,
        "--row-context-out", row_context_out,
        "--min-rows", str(getattr(args, "effective_target_credit_ready_rows", args.target_credit_ready_rows)),
        "--limit", str(args.slice_limit),
        "--allow-not-ready",
    ]


def _template_backfill_cmd(args: argparse.Namespace, *, selection: str, checkpoint: str, out: str, row_context: str | None = None) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/c_supply_template_backfill.py",
        "--selection", selection,
        "--checkpoint", checkpoint,
        "--row-context", row_context or args.row_context,
        "--spec-dir", args.spec_dir,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--run-id", f"c_supply_growth_template_{int(time.time())}",
        "--max-jobs", str(args.template_max_jobs),
        "--rows-per-family", str(args.template_rows_per_family),
        "--agent-runtime", args.agent_runtime,
        "--agent-max-wall-time-s", str(args.agent_max_wall_time_s),
        "--agent-max-attempts", str(args.agent_max_attempts),
        "--agent-max-iterations", str(args.agent_max_iterations),
        "--max-enqueued", str(args.template_max_enqueued),
        "--cooldown-s", str(args.template_cooldown_s),
        "--enqueue",
    ]
    if args.retry_existing_template_jobs:
        cmd.append("--retry-existing")
    return cmd


def _agent_worker_cmd(args: argparse.Namespace, *, selection: str, ordinal: int = 0, patch_mode: str = "c_supply_template_backfill") -> list[str]:
    mode_slug = str(patch_mode or "family_spec_patch").replace("_", "-")
    worker_suffix = mode_slug if int(ordinal) <= 0 else f"{mode_slug}-{int(ordinal)}"
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/agent_repair_worker.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--worker-id", f"{args.worker_id}-{worker_suffix}",
        "--claim-kind", "agent_repair_task",
        "--claim-patch-mode", str(patch_mode),
        "--default-runtime", args.agent_runtime if args.agent_runtime in {"codex", "claude"} else "codex",
        "--default-codex-model", args.default_codex_model,
        "--max-wall-time-s", str(args.agent_max_wall_time_s),
        "--max-iterations", str(args.agent_max_iterations),
        "--daemon",
        "--max-tasks", str(args.agent_worker_max_tasks),
        "--max-idle-s", str(args.agent_worker_max_idle_s),
        "--idle-sleep-s", "5",
        "--allow-agent-launch",
    ]
    if str(patch_mode) == "c_supply_template_backfill":
        cmd.extend(["--claim-payload-eq", f"c_supply_selection={selection}"])
    return cmd


def _static_sweep_cmd(args: argparse.Namespace, *, selection: str, checkpoint: str, out_checkpoint: str, out: str, row_context: str = "") -> list[str]:
    return [
        sys.executable,
        "scripts/public/control/leanmill/c_static_sweep_backfill.py",
        "--selection", selection,
        "--row-context", row_context or args.row_context,
        "--checkpoint", checkpoint,
        "--out-checkpoint", out_checkpoint,
        "--contract", args.contract,
        "--run-root", str(Path(out).parent / "static_sweep"),
        "--out", out,
        "--run-id", f"c_supply_growth_static_{int(time.time())}",
        "--limit", str(args.static_sweep_limit),
        "--max-tool-calls", str(args.static_max_tool_calls),
        "--per-candidate-timeout-s", str(args.static_per_candidate_timeout_s),
        "--row-wall-timeout-s", str(args.static_row_wall_timeout_s),
        "--wall-timeout-s", str(args.static_wall_timeout_s),
        "--allow-heavy-lean",
    ]


def _demand_corpus_cmd(args: argparse.Namespace, *, selection: str, checkpoint: str, out_dir: str, out: str, md: str, row_context: str | None = None) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/c_supply_demand_corpus_builder.py",
        "--selection", selection,
        "--spec-dir", args.spec_dir,
        "--row-context", row_context or args.row_context,
        "--out-dir", out_dir,
        "--checkpoint", checkpoint,
        "--queue-db", args.queue_db,
        "--out", out,
        "--md", md,
        "--run-id", f"c_supply_growth_demand_{int(time.time())}",
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--rows-per-family", str(max(1, int(args.source_rows_per_family))),
        "--min-signature-hits", str(max(1, int(getattr(args, "source_min_signature_hits", 2)))),
        "--source-snapshot-dir", str(getattr(args, "source_snapshot_dir", f"{DATA_DIR}/evaluation_harness_sources")),
        "--mathlib-root", str(getattr(args, "source_mathlib_root", "")),
    ]
    if bool(getattr(args, "source_materialize_missing_files", False)):
        cmd.append("--materialize-missing-source-files")
    for source_corpus in (getattr(args, "source_corpora", []) or []):
        if str(source_corpus):
            cmd.extend(["--source-corpus", str(source_corpus)])
    return cmd


def _family_birth_cmd(args: argparse.Namespace, *, selection: str, checkpoint: str, row_context: str, out: str, md: str) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/family_birth_miner.py",
        "--selection", selection,
        "--checkpoint", checkpoint,
        "--row-context", row_context,
        "--spec-dir", args.spec_dir,
        "--out", out,
        "--md", md,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--run-id", f"c_supply_growth_family_birth_{int(time.time())}",
        "--existing-family-confidence-floor", str(float(getattr(args, "family_birth_existing_family_confidence_floor", 0.75))),
        "--existing-family-hit-floor", str(max(1, int(getattr(args, "family_birth_existing_family_hit_floor", 3)))),
        "--min-rows", str(max(1, int(getattr(args, "family_birth_min_rows", 3)))),
        "--min-shared-tokens", str(max(1, int(getattr(args, "family_birth_min_shared_tokens", 1)))),
        "--max-clusters", str(max(0, int(getattr(args, "family_birth_max_clusters", 20)))),
        "--max-enqueued", str(max(0, int(getattr(args, "family_birth_max_enqueued", 0)))),
        "--cooldown-s", str(max(0, int(getattr(args, "family_birth_cooldown_s", 86400)))),
        "--agent-runtime", str(getattr(args, "family_birth_agent_runtime", args.agent_runtime)),
        "--agent-max-wall-time-s", str(max(1, int(getattr(args, "family_birth_agent_max_wall_time_s", args.agent_max_wall_time_s)))),
        "--agent-max-iterations", str(max(1, int(getattr(args, "family_birth_agent_max_iterations", args.agent_max_iterations)))),
    ]
    if bool(getattr(args, "family_birth_include_covered_static_failures", False)):
        cmd.append("--include-covered-static-failures")
    else:
        cmd.append("--no-include-covered-static-failures")
    if bool(getattr(args, "family_birth_exclude_existing_family_tokens", True)):
        cmd.append("--exclude-existing-family-tokens")
    else:
        cmd.append("--no-exclude-existing-family-tokens")
    if bool(getattr(args, "family_birth_enqueue", False)):
        cmd.append("--enqueue")
    return cmd


def _upstream_rater_cmd(args: argparse.Namespace, *, selection: str, demand_corpus: str, out: str, packet_out: str, prompt_out: str, codex_out: str) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/c_supply_upstream_rater.py",
        "--selection", selection,
        "--demand-corpus", demand_corpus,
        "--population-elo", getattr(args, "population_elo", f"{DATA_DIR}/leanmill_population_elo.json"),
        "--mode", str(getattr(args, "upstream_rater_mode", "observe_only")),
        "--model", str(getattr(args, "upstream_rater_model", "gpt-5.4-mini")),
        "--reasoning-effort", str(getattr(args, "upstream_rater_reasoning_effort", "low")),
        "--timeout-s", str(max(30, int(getattr(args, "upstream_rater_timeout_s", 300)))),
        "--max-candidates", str(max(1, int(getattr(args, "upstream_rater_max_candidates", 24)))),
        "--out", out,
        "--packet-out", packet_out,
        "--prompt-out", prompt_out,
        "--codex-out", codex_out,
    ]
    if bool(getattr(args, "upstream_rater_run_model", False)):
        cmd.append("--run-model")
    return cmd


def _source_growth_routing_policy(args: argparse.Namespace) -> dict[str, Any]:
    return source_growth_routing_policy(getattr(args, "factory_policy", FACTORY_POLICY))


def _recent_ratified_seed_families(queue_db: str, *, window_s: int, now: int | None = None) -> set[str]:
    return recent_ratified_seed_families(queue_db, window_s=window_s, now=now)


def _promote_recent_ratified_seed_corpora(
    corpora: list[dict[str, Any]],
    *,
    policy: dict[str, Any],
    recent_families: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    return promote_recent_ratified_seed_records(
        corpora,
        policy=policy,
        recent_families=recent_families,
        eligible_status_key="status",
        eligible_status_value="written",
    )


def _order_corpora_with_rater(corpora: list[dict[str, Any]], rater_obj: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    if mode != "advisory" or not isinstance(rater_obj, dict):
        return corpora
    validation = rater_obj.get("model_validation") if isinstance(rater_obj.get("model_validation"), dict) else {}
    if not validation.get("ok"):
        return corpora
    rank = {str(family): idx for idx, family in enumerate(rater_obj.get("ordered_families") or []) if str(family)}
    if not rank:
        return corpora
    return sorted(corpora, key=lambda corpus: (rank.get(str(corpus.get("family") or ""), 10000), str(corpus.get("family") or "")))


def _static_failure_miner_cmd(args: argparse.Namespace, *, row_context: str, checkpoint: str, out: str, md: str, run_root: str, family: str) -> list[str]:
    return [
        sys.executable,
        "scripts/public/control/leanmill/static_failure_miner.py",
        "--row-context", row_context,
        "--spec-dir", args.spec_dir,
        "--checkpoint", checkpoint,
        "--out", out,
        "--md", md,
        "--run-id", f"c_supply_growth_source_{family}_{int(time.time())}",
        "--run-root", run_root,
        "--limit", str(max(1, int(args.source_rows_per_family))),
        "--max-new-rows", str(max(1, min(int(args.static_sweep_limit), int(args.source_rows_per_family)))),
        "--max-tool-calls", str(args.static_max_tool_calls),
        "--per-candidate-timeout-s", str(args.static_per_candidate_timeout_s),
        "--wall-timeout-s", str(args.static_wall_timeout_s),
        "--min-signature-hits", str(max(1, int(getattr(args, "source_min_signature_hits", 2)))),
        "--skip-any-checkpoint-row",
    ]


def _source_static_candidate_rows_from_reports(
    report_paths: list[tuple[str, str]],
    row_context: str | Path,
    *,
    match_policy: source_family_match.SourceFamilyMatchPolicy | None = None,
    min_hit_count: int = 2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    match_policy = match_policy or source_family_match.SourceFamilyMatchPolicy(min_hit_count=max(1, int(min_hit_count)))
    rows_by_id = {
        _row_id(row): dict(row)
        for row in _iter_rows(_read_json(row_context) or {})
        if _row_id(row)
    }
    rows_by_candidate: dict[str, dict[str, Any]] = {}
    mined_family_counts: Counter[str] = Counter()
    matched_family_counts: Counter[str] = Counter()
    weak_match_count = 0
    rejected_match_counts: Counter[str] = Counter()
    report_summaries: list[dict[str, Any]] = []
    for mined_family, report_path in report_paths:
        obj = _read_json(report_path) or {}
        if not isinstance(obj, dict):
            continue
        report_summaries.append({
            "family": mined_family,
            "path": str(report_path),
            "supply_candidate_count": obj.get("supply_candidate_count"),
            "counts": obj.get("counts") or {},
        })
        for cand in obj.get("candidates") or []:
            if not isinstance(cand, dict):
                continue
            if not cand.get("supply_candidate"):
                continue
            if str(cand.get("static_failure_class") or "") != "strict_no_signal":
                continue
            row_id = str(cand.get("row_id") or "")
            if not row_id:
                continue
            summary = source_family_match.rejection_summary(cand.get("family_matches") or [], match_policy)
            for reason, count in (summary.get("counts") or {}).items():
                if reason != "eligible":
                    rejected_match_counts[str(reason)] += int(count)
            strong_matches = source_family_match.eligible_matches(cand.get("family_matches") or [], match_policy)
            if not strong_matches:
                weak_match_count += 1
                continue
            row = dict(rows_by_id.get(row_id) or {})
            row["row_id"] = row_id
            source_file = str(cand.get("source_file") or row.get("source_file") or row.get("sorried_file") or "")
            if source_file:
                row["source_file"] = source_file
            row["source_static_candidate"] = {
                "mined_family": mined_family,
                "static_result": cand.get("static_result"),
                "static_failure_class": cand.get("static_failure_class"),
                "family_matches": strong_matches,
                "report_path": str(report_path),
                "min_hit_count": match_policy.min_hit_count,
                "source_family_match_policy": match_policy.as_receipt(),
                "credit_boundary": "source static candidate only; governed static, family templates, probes, and slice prep decide C credit",
            }
            if row_id not in rows_by_candidate:
                rows_by_candidate[row_id] = row
                mined_family_counts[mined_family] += 1
                for match in strong_matches:
                    if str(match.get("family") or ""):
                        matched_family_counts[str(match.get("family") or "")] += 1
    rows = sorted(rows_by_candidate.values(), key=lambda row: str(row.get("row_id") or ""))
    summary = {
        "schema": "leanmill-source-static-candidate-summary-v1",
        "candidate_count": len(rows),
        "candidate_counts_by_mined_family": dict(sorted(mined_family_counts.items())),
        "candidate_counts_by_matched_family": dict(sorted(matched_family_counts.items())),
        "min_hit_count": match_policy.min_hit_count,
        "source_family_match_policy": match_policy.as_receipt(),
        "weak_match_candidate_count": weak_match_count,
        "rejected_match_counts": dict(sorted(rejected_match_counts.items())),
        "reports": report_summaries,
        "credit_boundary": "public source mining candidates only; no C credit until governed static, matched templates, and probe receipts pass",
    }
    return rows, summary


def _write_source_static_candidate_selection(rows: list[dict[str, Any]], *, parent_selection: str, out: str | Path) -> str:
    obj = {
        "schema": "leanmill-source-static-candidates-selection-v1",
        "status": "source_static_candidates_pending_governed_static",
        "parent_selection": str(parent_selection),
        "selected_count": len(rows),
        "selected_rows_order": [str(row.get("row_id") or "") for row in rows if str(row.get("row_id") or "")],
        "selected_rows": rows,
        "rows": rows,
        "credit_boundary": "temporary controller selection for governed static completion only; no proof, benchmark, or C credit",
    }
    _write_json(out, obj)
    return str(out)


def _probe_seed_cmd(args: argparse.Namespace, *, selection: str, out: str, row_context: str = "") -> list[str]:
    max_tests_per_probe = int(args.max_tests_per_probe or 0)
    if max_tests_per_probe <= 0:
        max_tests_per_probe = max(1, int(args.probe_rows_per_work_item)) * 2
    routing = multi_node_routing_plan(path=args.factory_policy, profile_name=args.policy_profile)
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/learning_work_seeder.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out,
        "--run-id", f"c_supply_growth_probe_{int(time.time())}",
        "--factory-policy", args.factory_policy,
        "--policy-profile", "",
        "--family-spec-selection", selection,
        "--row-context", row_context or args.row_context,
        "--max-total-jobs", str(args.probe_seed_max_jobs),
        "--max-probe-families", "0",
        "--max-family-spec-probe-families", str(args.probe_seed_max_families),
        "--family-spec-probe-rows-per-work-item", str(args.probe_rows_per_work_item),
        "--max-tests-per-probe", str(max_tests_per_probe),
        "--max-family-spec-repair-jobs", "0",
        "--max-family-spec-generality-jobs", "0",
        "--max-proposal-jobs", "0",
        "--max-agent-jobs", "0",
        "--max-enqueued", str(args.probe_seed_max_enqueued),
        "--terminal-family-cooldown-s", "0",
        "--terminal-probe-signature-cooldown-s", "0",
        "--probe-command-timeout-s", str(args.probe_command_timeout_s),
        "--probe-command-timeout-overhead-s", str(args.probe_command_timeout_overhead_s),
        "--warm-repl-inline",
        "--govern-winners",
    ]
    if int(getattr(args, "probe_seed_max_enqueued", 0) or 0) > 0:
        cmd.append("--enqueue")
    if routing.get("enabled"):
        cmd.extend(["--node-id", str(routing.get("node_id") or "")])
        cmd.extend(["--routing-nodes", str(routing.get("routing_nodes_arg") or "")])
    return cmd


def _probe_worker_cmd(args: argparse.Namespace, *, selection: str) -> list[str]:
    return [
        sys.executable,
        "scripts/public/control/leanmill/probe_worker.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--worker-id", f"{args.worker_id}-probe",
        "--probe-lane", "family_spec",
        "--family-spec-selection", selection,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--claim-scan-limit", str(args.probe_claim_scan_limit),
        "--daemon",
        "--max-tasks", str(args.probe_worker_max_tasks),
        "--max-idle-ticks", "1",
        "--idle-sleep-s", "2",
        "--allow-heavy-lean",
    ]


def run_controller(args: argparse.Namespace) -> dict[str, Any]:
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    invocation_dir = work_dir / f"run_{time.time_ns()}"
    invocation_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.checkpoint
    current_selection = args.selection
    current_row_context = args.row_context
    resume_previous_state = _previous_running_state(args)
    if resume_previous_state.get("resumed"):
        checkpoint = str(resume_previous_state.get("latest_checkpoint") or checkpoint)
        current_selection = str(resume_previous_state.get("latest_selection") or current_selection)
        current_row_context = str(resume_previous_state.get("latest_row_context") or current_row_context)
    commands: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    previous_score = None
    score_policy = _selection_score_policy(args)
    breadth_policy = c_supply_breadth_policy_from_policy(read_policy(getattr(args, "factory_policy", FACTORY_POLICY)))
    effective_target_credit_ready_rows = _effective_target_credit_ready_rows(breadth_policy, args.target_credit_ready_rows)
    args.effective_target_credit_ready_rows = effective_target_credit_ready_rows
    best_selection = current_selection
    best_row_context = current_row_context
    best_checkpoint = checkpoint
    if resume_previous_state.get("resumed"):
        best_selection = str(resume_previous_state.get("best_selection") or best_selection)
        best_row_context = str(resume_previous_state.get("best_row_context") or best_row_context)
        best_checkpoint = str(resume_previous_state.get("best_checkpoint") or best_checkpoint)
    best_metrics = _selection_metrics(current_selection)
    if resume_previous_state.get("resumed") and best_selection != current_selection:
        candidate_best_metrics = _selection_metrics(best_selection)
        if _selection_score(candidate_best_metrics, score_policy) >= _selection_score(best_metrics, score_policy):
            best_metrics = candidate_best_metrics
        else:
            best_selection = current_selection
            best_row_context = current_row_context
            best_checkpoint = checkpoint
    best_score = _selection_score(best_metrics, score_policy)
    stop_reason = "max_rounds_exhausted"
    active_round_rec: dict[str, Any] | None = None

    def _progress_payload(*, stage: str, status: str = "running", stop: str | None = None) -> dict[str, Any]:
        latest_metrics = _selection_metrics(current_selection)
        report_metrics = best_metrics if best_metrics else latest_metrics
        visible_rounds = list(rounds)
        if isinstance(active_round_rec, dict) and active_round_rec not in visible_rounds:
            visible_rounds.append(active_round_rec)
        readiness = _target_readiness_decision(
            report_metrics,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        )
        return {
            "schema": "leanmill-c-supply-growth-controller-v1",
            "generated_at_epoch": int(time.time()),
            "status": status,
            "current_stage": stage,
            "stop_reason": stop or stop_reason,
            "proof_credit": "none_controller_only_existing_gates_decide",
            "target_credit_ready_rows": args.target_credit_ready_rows,
            "effective_target_credit_ready_rows": effective_target_credit_ready_rows,
            "work_invocation_dir": str(invocation_dir),
            "initial_checkpoint": args.checkpoint,
            "resume_previous_state": resume_previous_state,
            "latest_checkpoint": checkpoint,
            "latest_selection": current_selection,
            "latest_row_context": current_row_context,
            "latest_metrics": latest_metrics,
            "best_checkpoint": best_checkpoint,
            "best_selection": best_selection,
            "best_row_context": best_row_context,
            "best_metrics": best_metrics,
            "target_readiness": readiness,
            "source_growth_decision": _source_growth_decision(
                report_metrics,
                breadth_policy,
                target_credit_ready_rows=effective_target_credit_ready_rows,
            ),
            "policy_profile_application": getattr(
                args,
                "_policy_profile_c_supply_growth_controller_applied",
                {"name": "", "key_count": 0, "keys": []},
            ),
            "external_source_scout_policy": _external_source_scout_policy(args),
            "selection_score_policy": score_policy,
            "c_supply_breadth_policy": breadth_policy,
            "best_selection_rule": score_policy["ordering_rule"],
            "rounds": visible_rounds,
            "command_count": len(commands),
            "failed_command_count": sum(1 for c in commands if int(c.get("returncode") or 0) != 0),
            "commands": commands[-40:],
            "progress_note": "running controller receipt; final_selection is emitted only when the controller reaches a terminal state",
        }

    def _write_progress(stage: str, *, status: str = "running", stop: str | None = None) -> None:
        if args.out:
            _write_json(args.out, _progress_payload(stage=stage, status=status, stop=stop))

    def _consider_best(selection: str, row_context: str, checkpoint_path: str, metrics: dict[str, Any]) -> None:
        nonlocal best_selection, best_row_context, best_checkpoint, best_metrics, best_score
        score = _selection_score(metrics, score_policy)
        if score > best_score:
            best_selection = selection
            best_row_context = row_context
            best_checkpoint = checkpoint_path
            best_metrics = metrics
            best_score = score

    _write_progress("initialized")
    for round_idx in range(max(1, int(args.max_rounds))):
        prefix = invocation_dir / f"round_{round_idx:02d}"
        prep_out = str(prefix.with_suffix(".selection.json"))
        prep_md = str(prefix.with_suffix(".selection.md"))
        prep_rows = str(prefix.with_suffix(".rows.json"))
        _write_progress(f"round_{round_idx:02d}:slice_prep_started")
        rec = _run(_prep_cmd(args, checkpoint=checkpoint, out=prep_out, md=prep_md, row_context_out=prep_rows, row_context=current_row_context), timeout_s=args.command_timeout_s, dry_run=args.dry_run)
        commands.append(rec)
        if rec.get("returncode") != 0:
            stop_reason = "slice_prep_failed"
            current_selection = prep_out
            _write_progress(f"round_{round_idx:02d}:slice_prep_failed", status="blocked", stop=stop_reason)
            break
        fresh_selection = prep_out if _command_applied(rec) else current_selection
        fresh_before = _selection_metrics(fresh_selection)
        _consider_best(fresh_selection, current_row_context, checkpoint, fresh_before)
        if _selection_score(fresh_before, score_policy) >= best_score:
            current_selection = fresh_selection
            before = fresh_before
        else:
            current_selection = best_selection
            before = best_metrics
        round_rec: dict[str, Any] = {"round": round_idx, "before": before, "commands": []}
        active_round_rec = round_rec
        enqueued_templates = 0
        _write_progress(f"round_{round_idx:02d}:slice_prep_finished")

        def _refresh_selection(stage_key: str, suffix: str) -> dict[str, Any]:
            nonlocal current_selection
            _write_progress(f"round_{round_idx:02d}:{stage_key}_refresh_started")
            out = str(prefix.with_suffix(f"{suffix}.selection.json"))
            rows = str(prefix.with_suffix(f"{suffix}.rows.json"))
            rec_refresh = _run(
                _prep_cmd(
                    args,
                    checkpoint=checkpoint,
                    out=out,
                    md=str(prefix.with_suffix(f"{suffix}.selection.md")),
                    row_context_out=rows,
                    row_context=current_row_context,
                ),
                timeout_s=args.command_timeout_s,
                dry_run=args.dry_run,
            )
            commands.append(rec_refresh)
            if _command_applied(rec_refresh):
                current_selection = out
            metrics = _selection_metrics(current_selection)
            _consider_best(current_selection, current_row_context, checkpoint, metrics)
            round_rec[stage_key] = metrics
            _write_progress(f"round_{round_idx:02d}:{stage_key}_refresh_finished")
            return metrics

        def _run_static_stage(stage_label: str, checkpoint_suffix: str, out_suffix: str) -> None:
            nonlocal checkpoint
            if int(getattr(args, "static_sweep_limit", 0) or 0) <= 0:
                round_rec["commands"].append({
                    "stage": stage_label,
                    "skipped": True,
                    "reason": "static_sweep_limit_zero",
                    "checkpoint_preserved": checkpoint,
                })
                return
            new_checkpoint = str(prefix.with_suffix(checkpoint_suffix))
            _write_progress(f"round_{round_idx:02d}:{stage_label}_started")
            static = _run(
                _static_sweep_cmd(
                    args,
                    selection=current_selection,
                    row_context=current_row_context,
                    checkpoint=checkpoint,
                    out_checkpoint=new_checkpoint,
                    out=str(prefix.with_suffix(out_suffix)),
                ),
                timeout_s=args.static_wall_timeout_s + 60,
                dry_run=args.dry_run,
            )
            commands.append(static)
            adopt_partial = bool(static.get("timed_out") and static.get("timeout_kill") == "process_group" and _checkpoint_has_records(new_checkpoint))
            command_rec = {"stage": stage_label, **static}
            if adopt_partial:
                command_rec["partial_checkpoint_adopted"] = True
                command_rec["partial_checkpoint"] = new_checkpoint
            round_rec["commands"].append(command_rec)
            if _command_applied(static) or adopt_partial:
                checkpoint = new_checkpoint
            _write_progress(f"round_{round_idx:02d}:{stage_label}_finished")

        def _run_template_stage(stage_label: str, plan_suffix: str, stage_key: str, prep_suffix: str) -> dict[str, Any]:
            nonlocal enqueued_templates
            template_plan = str(prefix.with_suffix(plan_suffix))
            template_preview_path = str(prefix.with_suffix(plan_suffix.replace(".json", ".preview.json")))
            _write_progress(f"round_{round_idx:02d}:{stage_label}_started")
            templ_cmd = _template_backfill_cmd(
                args,
                selection=current_selection,
                checkpoint=checkpoint,
                out=template_plan,
                row_context=current_row_context,
            )
            templ_preview = _run(
                _no_enqueue_cmd(templ_cmd, out=template_preview_path),
                timeout_s=args.command_timeout_s,
                dry_run=args.dry_run,
            )
            commands.append(templ_preview)
            round_rec["commands"].append({"stage": f"{stage_label}_preflight", **templ_preview})
            templ_preview_obj = _read_json(template_preview_path) if _command_applied(templ_preview) else _parse_stdout_json(templ_preview)
            if not isinstance(templ_preview_obj, dict):
                templ_preview_obj = {}
            round_rec[f"{stage_label}_preflight"] = {
                "path": template_preview_path,
                "job_count": templ_preview_obj.get("job_count"),
                "candidate_family_count": templ_preview_obj.get("candidate_family_count"),
                "strict_static_fail_row_count": templ_preview_obj.get("strict_static_fail_row_count"),
                "static_outcome_row_count": templ_preview_obj.get("static_outcome_row_count"),
                "reason": "preflight_template_jobs_available" if int(templ_preview_obj.get("job_count") or 0) > 0 else "preflight_no_template_jobs",
                "credit_boundary": "deterministic no-enqueue preview only; no proof, C, benchmark, or governance credit",
            }
            if int(templ_preview_obj.get("job_count") or 0) <= 0:
                _write_progress(f"round_{round_idx:02d}:{stage_label}_finished")
                return _refresh_selection(stage_key, prep_suffix)
            templ = _run(
                templ_cmd,
                timeout_s=args.command_timeout_s,
                dry_run=args.dry_run,
            )
            commands.append(templ)
            round_rec["commands"].append({"stage": stage_label, **templ})
            templ_obj = _parse_stdout_json(templ)
            stage_enqueued = int(templ_obj.get("enqueued") or 0)
            enqueued_templates += stage_enqueued
            if stage_enqueued and args.allow_agent_launch:
                worker_processes = max(1, int(getattr(args, "agent_worker_processes", 1)))
                agent_cmds = [
                    _agent_worker_cmd(args, selection=current_selection, ordinal=idx)
                    for idx in range(worker_processes)
                ]
                agent_results = _run_parallel(
                    agent_cmds,
                    timeout_s=args.agent_worker_timeout_s,
                    parallelism=worker_processes,
                    dry_run=args.dry_run,
                )
                commands.extend(agent_results)
                round_rec["commands"].append({
                    "stage": f"{stage_label}_workers",
                    "worker_processes": worker_processes,
                    "results": agent_results,
                })
            _write_progress(f"round_{round_idx:02d}:{stage_label}_finished")
            return _refresh_selection(stage_key, prep_suffix)

        before_readiness = _target_readiness_decision(
            before,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        )
        round_rec["target_readiness_before"] = before_readiness
        if before_readiness["ready"]:
            stop_reason = "target_reached"
            rounds.append(round_rec)
            break

        if args.allow_heavy_lean and before["static_sweep_owed_count"] > 0:
            _run_static_stage("static_sweep", ".static_checkpoint.jsonl", ".static_sweep.json")

        after_static = _refresh_selection("after_static", ".post_static")
        after_static = _run_template_stage("template_backfill_enqueue", ".template_backfill.json", "after_template", ".post_template")

        if (
            bool(getattr(args, "family_birth_enabled", False))
            and after_static["credit_ready_count"] < effective_target_credit_ready_rows
            and int((after_static.get("blockers_by_reason") or {}).get("no_positive_family_template") or 0) >= int(getattr(args, "family_birth_min_pressure_rows", 1))
        ):
            family_birth_out = str(prefix.with_suffix(".family_birth.json"))
            family_birth_md = str(prefix.with_suffix(".family_birth.md"))
            family_birth_preview_out = str(prefix.with_suffix(".family_birth.preview.json"))
            family_birth_preview_md = str(prefix.with_suffix(".family_birth.preview.md"))
            _write_progress(f"round_{round_idx:02d}:family_birth_started")
            family_birth_cmd = _family_birth_cmd(
                args,
                selection=current_selection,
                checkpoint=checkpoint,
                row_context=current_row_context,
                out=family_birth_out,
                md=family_birth_md,
            )
            family_birth_preview = _run(
                _no_enqueue_cmd(family_birth_cmd, out=family_birth_preview_out, md=family_birth_preview_md),
                timeout_s=args.command_timeout_s,
                dry_run=args.dry_run,
            )
            commands.append(family_birth_preview)
            round_rec["commands"].append({"stage": "family_birth_preflight", **family_birth_preview})
            family_birth_preview_obj = (_read_json(family_birth_preview_out) or {}) if _command_applied(family_birth_preview) else _parse_stdout_json(family_birth_preview)
            if not isinstance(family_birth_preview_obj, dict):
                family_birth_preview_obj = {}
            round_rec["family_birth"] = {
                "path": family_birth_preview_out,
                "dry_run": family_birth_preview_obj.get("dry_run"),
                "candidate_static_fail_row_count": family_birth_preview_obj.get("candidate_static_fail_row_count"),
                "birth_pressure_row_count": family_birth_preview_obj.get("birth_pressure_row_count"),
                "cluster_count": family_birth_preview_obj.get("cluster_count"),
                "enqueued": 0,
                "preflight_reason": "preflight_family_birth_clusters_available" if int(family_birth_preview_obj.get("cluster_count") or 0) > 0 else "preflight_no_family_birth_clusters",
                "credit_boundary": family_birth_preview_obj.get("credit_boundary") or "deterministic no-enqueue preview only; no proof, C, benchmark, or governance credit",
            }
            family_birth_obj = family_birth_preview_obj
            if int(family_birth_preview_obj.get("cluster_count") or 0) > 0:
                family_birth = _run(
                    family_birth_cmd,
                    timeout_s=args.command_timeout_s,
                    dry_run=args.dry_run,
                )
                commands.append(family_birth)
                family_birth_obj = (_read_json(family_birth_out) or {}) if _command_applied(family_birth) else _parse_stdout_json(family_birth)
                if not isinstance(family_birth_obj, dict):
                    family_birth_obj = {}
                round_rec["family_birth"].update({
                    "path": family_birth_out,
                    "dry_run": family_birth_obj.get("dry_run"),
                    "candidate_static_fail_row_count": family_birth_obj.get("candidate_static_fail_row_count"),
                    "birth_pressure_row_count": family_birth_obj.get("birth_pressure_row_count"),
                    "cluster_count": family_birth_obj.get("cluster_count"),
                    "enqueued": family_birth_obj.get("enqueued"),
                    "credit_boundary": family_birth_obj.get("credit_boundary"),
                })
                round_rec["commands"].append({"stage": "family_birth_miner", **family_birth})
            if args.allow_agent_launch and int(family_birth_obj.get("enqueued") or 0) > 0:
                birth_worker_processes = max(1, min(int(family_birth_obj.get("enqueued") or 0), int(args.agent_worker_processes)))
                birth_agent_results = _run_parallel(
                    [
                        _agent_worker_cmd(args, selection=current_selection, ordinal=idx, patch_mode="family_birth_candidate")
                        for idx in range(birth_worker_processes)
                    ],
                    timeout_s=args.agent_worker_timeout_s,
                    parallelism=birth_worker_processes,
                    dry_run=args.dry_run,
                )
                commands.extend(birth_agent_results)
                round_rec["commands"].append({
                    "stage": "family_birth_workers",
                    "worker_processes": birth_worker_processes,
                    "results": birth_agent_results,
                })
            _write_progress(f"round_{round_idx:02d}:family_birth_finished")

        source_growth = _source_growth_decision(
            after_static,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        )
        round_rec["source_growth_decision"] = source_growth
        controller_policy = _c_supply_controller_policy(args)
        source_growth_allowed = bool(controller_policy.get("allow_source_growth", getattr(args, "allow_heavy_lean", False)))
        source_static_mining_allowed = bool(controller_policy.get("allow_source_static_mining", source_growth_allowed))
        round_rec["source_growth_execution_policy"] = {
            "allow_source_growth": source_growth_allowed,
            "allow_source_static_mining": source_static_mining_allowed,
            "allow_heavy_lean": bool(getattr(args, "allow_heavy_lean", False)),
            "source": "factory_policy.profile.c_supply_growth_controller" if controller_policy else "controller_default",
            "rule": (
                "Agentic/source upstream inventory is decoupled from heavy Lean. "
                "Heavy Lean still gates governed static/probe credit paths."
            ),
        }
        if source_growth["needed"] and source_growth_allowed:
            external_scout_policy = _external_source_scout_policy(args)
            round_rec["external_source_scout_policy"] = external_scout_policy
            if bool(external_scout_policy["seed_external_source_scouts"]):
                open_external_source_scouts = _open_work_count(args.queue_db, kinds={"source_scout_task"})
                external_source_target = max(0, int(external_scout_policy["external_source_scout_floor"]))
                external_source_needed = max(0, external_source_target - open_external_source_scouts)
                external_source_max_enqueued = min(
                    max(0, int(external_scout_policy["external_source_scout_max_enqueued"])),
                    external_source_needed,
                )
                external_source_out = str(prefix.with_suffix(".external_source_scout_seed.json"))
                if external_source_max_enqueued > 0:
                    _write_progress(f"round_{round_idx:02d}:external_source_scout_seed_started")
                    external_source = _run(
                        _external_source_scout_cmd(
                            args,
                            out=external_source_out,
                            max_enqueued=external_source_max_enqueued,
                            run_id=f"c_supply_source_growth_{int(time.time())}",
                        ),
                        timeout_s=args.command_timeout_s,
                        dry_run=args.dry_run,
                    )
                    commands.append(external_source)
                    round_rec["commands"].append({"stage": "external_source_scout_seed", **external_source})
                    external_source_obj = (_read_json(external_source_out) or {}) if _command_applied(external_source) else {}
                    round_rec["external_source_scout_seed"] = {
                        "path": external_source_out,
                        "open_before": open_external_source_scouts,
                        "floor": external_source_target,
                        "max_enqueued": external_source_max_enqueued,
                        "job_count": external_source_obj.get("job_count"),
                        "enqueued": external_source_obj.get("enqueued"),
                        "skipped_existing": external_source_obj.get("skipped_existing"),
                        "anti_laundering_rule": external_source_obj.get("anti_laundering_rule"),
                        "credit_boundary": "outside source scouts emit source_request inventory only; no proof, C, benchmark, or governance credit",
                    }
                    _write_progress(f"round_{round_idx:02d}:external_source_scout_seed_finished")
                else:
                    round_rec["external_source_scout_seed"] = {
                        "skipped": True,
                        "reason": "external_source_scout_floor_satisfied",
                        "open_before": open_external_source_scouts,
                        "floor": external_source_target,
                        "credit_boundary": "outside source scouts emit source_request inventory only; no proof, C, benchmark, or governance credit",
                    }
            demand_out_dir = str(prefix.with_suffix(".demand_corpora"))
            demand_out = str(prefix.with_suffix(".demand_corpus.json"))
            _write_progress(f"round_{round_idx:02d}:demand_corpus_started")
            demand = _run(
                _demand_corpus_cmd(
                    args,
                    selection=current_selection,
                    checkpoint=checkpoint,
                    out_dir=demand_out_dir,
                    out=demand_out,
                    md=str(prefix.with_suffix(".demand_corpus.md")),
                    row_context=current_row_context,
                ),
                timeout_s=args.command_timeout_s,
                dry_run=args.dry_run,
            )
            commands.append(demand)
            round_rec["commands"].append({"stage": "demand_corpus_builder", **demand})
            demand_obj = (_read_json(demand_out) or {}) if _command_applied(demand) else {}
            if isinstance(demand_obj, dict) and demand_obj:
                round_rec["demand_corpus"] = {
                    "path": demand_out,
                    "source_family_count": demand_obj.get("source_family_count"),
                    "corpora_written_count": demand_obj.get("corpora_written_count"),
                    "total_rows_written": demand_obj.get("total_rows_written"),
                    "missing_source_file_candidate_count": demand_obj.get("missing_source_file_candidate_count"),
                    "missing_source_file_candidate_counts_by_family": demand_obj.get("missing_source_file_candidate_counts_by_family"),
                    "source_materialization": demand_obj.get("source_materialization"),
                    "source_file_filter": demand_obj.get("source_file_filter"),
                    "target_aware_family_template_filter": demand_obj.get("target_aware_family_template_filter"),
                }
            _write_progress(f"round_{round_idx:02d}:demand_corpus_finished")
            source_mine_commands = []
            corpora_for_routing = [c for c in (demand_obj.get("corpora") or []) if isinstance(c, dict)]
            rater_obj: dict[str, Any] = {}
            if str(getattr(args, "upstream_rater_mode", "off")) != "off" and int(demand_obj.get("corpora_written_count") or 0) > 0:
                rater_out = str(prefix.with_suffix(".upstream_rater.json"))
                _write_progress(f"round_{round_idx:02d}:upstream_rater_started")
                rater = _run(
                    _upstream_rater_cmd(
                        args,
                        selection=current_selection,
                        demand_corpus=demand_out,
                        out=rater_out,
                        packet_out=str(prefix.with_suffix(".upstream_rater_packet.json")),
                        prompt_out=str(prefix.with_suffix(".upstream_rater_prompt.txt")),
                        codex_out=str(prefix.with_suffix(".upstream_rater_codex.json")),
                    ),
                    timeout_s=max(30, int(getattr(args, "upstream_rater_timeout_s", 300))) + 30,
                    dry_run=args.dry_run,
                )
                commands.append(rater)
                round_rec["commands"].append({"stage": "upstream_rater", **rater})
                rater_obj = _read_json(rater_out) or {}
                if isinstance(rater_obj, dict) and rater_obj:
                    _write_json(DEFAULT_UPSTREAM_RATER, rater_obj)
                round_rec["upstream_rater"] = {
                    "path": rater_out,
                    "mode": getattr(args, "upstream_rater_mode", "off"),
                    "candidate_count": rater_obj.get("candidate_count"),
                    "model_validation": rater_obj.get("model_validation"),
                    "ordered_families": (rater_obj.get("ordered_families") or [])[:8],
                }
                corpora_for_routing = _order_corpora_with_rater(corpora_for_routing, rater_obj, mode=str(getattr(args, "upstream_rater_mode", "observe_only")))
                _write_progress(f"round_{round_idx:02d}:upstream_rater_finished")
            if corpora_for_routing:
                routing_policy = _source_growth_routing_policy(args)
                recent_families = _recent_ratified_seed_families(
                    str(getattr(args, "queue_db", "")),
                    window_s=int(routing_policy.get("recent_ratified_seed_window_s") or 0),
                )
                corpora_for_routing, promoted_families = _promote_recent_ratified_seed_corpora(
                    corpora_for_routing,
                    policy=routing_policy,
                    recent_families=recent_families,
                )
                round_rec["source_growth_routing_policy"] = {
                    **routing_policy,
                    "recent_ratified_seed_family_count": len(recent_families),
                    "recent_ratified_seed_families_sample": sorted(recent_families)[:12],
                    "promoted_families": promoted_families,
                    "upstream_rater_mode": str(getattr(args, "upstream_rater_mode", "off")),
                    "upstream_rater_applied": bool(rater_obj),
                }
            corpus_paths = [str(corpus.get("path") or "") for corpus in corpora_for_routing if isinstance(corpus, dict) and str(corpus.get("status") or "") == "written" and corpus.get("path")]
            if corpus_paths:
                current_row_context = _merge_row_context(current_row_context, corpus_paths, prefix.with_suffix(".source_augmented.rows.json"))
            source_jobs: list[tuple[str, list[str]]] = []
            if source_static_mining_allowed and int(args.static_sweep_limit) > 0:
                written_corpora_for_mining = [
                    corpus for corpus in corpora_for_routing
                    if isinstance(corpus, dict)
                    and str(corpus.get("status") or "") == "written"
                    and corpus.get("path")
                ]
                for corpus in written_corpora_for_mining[: max(1, int(args.probe_seed_max_families))]:
                    family = str(corpus.get("family") or "family")
                    source_jobs.append((family, _static_failure_miner_cmd(
                        args,
                        row_context=str(corpus.get("path")),
                        checkpoint=checkpoint,
                        out=str(prefix.with_suffix(f".source_mine_{family}.json")),
                        md=str(prefix.with_suffix(f".source_mine_{family}.md")),
                        run_root=str(Path(args.work_dir) / "source_mine" / family),
                        family=family,
                    )))
            elif corpus_paths:
                round_rec["source_static_failure_mining"] = {
                    "skipped": True,
                    "reason": "source_static_mining_disabled_by_policy" if not source_static_mining_allowed else "static_sweep_limit_zero",
                    "corpus_count": len(corpus_paths),
                }
            if source_jobs:
                _write_progress(f"round_{round_idx:02d}:source_static_failure_mining_started")
            source_results = _run_parallel(
                [cmd for _family, cmd in source_jobs],
                timeout_s=args.static_wall_timeout_s + 60,
                parallelism=max(1, int(args.source_parallel_families)),
                dry_run=args.dry_run,
            )
            if source_jobs:
                _write_progress(f"round_{round_idx:02d}:source_static_failure_mining_finished")
            source_report_paths: list[tuple[str, str]] = []
            for (family, _cmd), mine in zip(source_jobs, source_results):
                commands.append(mine)
                source_mine_commands.append({"family": family, **mine})
                out_path = ""
                for idx, part in enumerate(_cmd):
                    if part == "--out" and idx + 1 < len(_cmd):
                        out_path = str(_cmd[idx + 1])
                        break
                if out_path:
                    source_report_paths.append((family, out_path))
            if source_mine_commands:
                round_rec["commands"].append({"stage": "source_static_failure_mining", "commands": source_mine_commands})
                source_candidate_rows, source_candidate_summary = _source_static_candidate_rows_from_reports(
                    source_report_paths,
                    current_row_context,
                    match_policy=source_family_match.policy_from_mapping(vars(args)),
                    min_hit_count=max(2, int(getattr(args, "source_template_min_hit_count", 2))),
                )
                source_candidate_selection = ""
                if source_candidate_rows:
                    source_candidate_selection = _write_source_static_candidate_selection(
                        source_candidate_rows,
                        parent_selection=current_selection,
                        out=prefix.with_suffix(".source_static_candidates.selection.json"),
                    )
                source_candidate_summary["selection_path"] = source_candidate_selection
                round_rec["source_static_failure_mining"] = source_candidate_summary
                if source_candidate_rows and args.allow_heavy_lean and int(args.static_sweep_limit) > 0:
                    source_candidate_checkpoint = str(prefix.with_suffix(".source_candidates.static_checkpoint.jsonl"))
                    _write_progress(f"round_{round_idx:02d}:source_candidate_governed_static_started")
                    source_candidate_static = _run(
                        _static_sweep_cmd(
                            args,
                            selection=source_candidate_selection,
                            checkpoint=checkpoint,
                            out_checkpoint=source_candidate_checkpoint,
                            out=str(prefix.with_suffix(".source_candidates.static_sweep.json")),
                            row_context=source_candidate_selection,
                        ),
                        timeout_s=args.static_wall_timeout_s + 60,
                        dry_run=args.dry_run,
                    )
                    commands.append(source_candidate_static)
                    source_candidate_static_obj = (_read_json(str(prefix.with_suffix(".source_candidates.static_sweep.json"))) or {}) if _command_applied(source_candidate_static) else {}
                    round_rec["commands"].append({"stage": "source_candidate_governed_static", **source_candidate_static})
                    round_rec["source_candidate_governed_static"] = {
                        "checkpoint_out": source_candidate_checkpoint,
                        "selection": source_candidate_selection,
                        "candidate_count": len(source_candidate_rows),
                        "status": source_candidate_static_obj.get("status"),
                        "owed_count": source_candidate_static_obj.get("owed_count"),
                        "ran_count": source_candidate_static_obj.get("ran_count"),
                        "skipped_count": source_candidate_static_obj.get("skipped_count"),
                        "proof_credit": source_candidate_static_obj.get("proof_credit"),
                    }
                    adopt_partial_source_candidate = bool(
                        source_candidate_static.get("timed_out")
                        and source_candidate_static.get("timeout_kill") == "process_group"
                        and _checkpoint_has_records(source_candidate_checkpoint)
                    )
                    if adopt_partial_source_candidate:
                        round_rec["source_candidate_governed_static"]["partial_checkpoint_adopted"] = True
                    if _command_applied(source_candidate_static) or adopt_partial_source_candidate:
                        checkpoint = source_candidate_checkpoint
                    _write_progress(f"round_{round_idx:02d}:source_candidate_governed_static_finished")
                current_row_context = _stamp_static_executability(current_row_context, checkpoint, prefix.with_suffix(".source_augmented_executable.rows.json"))
                post_source_out = str(prefix.with_suffix(".post_source.selection.json"))
                post_source_rows = str(prefix.with_suffix(".post_source.rows.json"))
                _write_progress(f"round_{round_idx:02d}:post_source_slice_prep_started")
                rec_source = _run(_prep_cmd(args, checkpoint=checkpoint, out=post_source_out, md=str(prefix.with_suffix(".post_source.selection.md")), row_context_out=post_source_rows, row_context=current_row_context), timeout_s=args.command_timeout_s, dry_run=args.dry_run)
                commands.append(rec_source)
                if rec_source.get("returncode") == 0:
                    current_selection = post_source_out
                    after_static = _selection_metrics(current_selection)
                    _consider_best(current_selection, current_row_context, checkpoint, after_static)
                    round_rec["after_source"] = after_static
                    if args.allow_heavy_lean and after_static["static_sweep_owed_count"] > 0:
                        _run_static_stage(
                            "source_static_sweep",
                            ".post_source.static_checkpoint.jsonl",
                            ".post_source.static_sweep.json",
                        )
                        after_static = _refresh_selection("after_source_static", ".post_source_static")
                    if (
                        after_static["credit_ready_count"] < effective_target_credit_ready_rows
                        and (
                            after_static["probe_owed_count"] > 0
                            or int((after_static.get("blockers_by_reason") or {}).get("no_positive_family_template") or 0) > 0
                        )
                    ):
                        after_static = _run_template_stage(
                            "source_template_backfill_enqueue",
                            ".post_source.template_backfill.json",
                            "after_source_template",
                            ".post_source_template",
                        )
                _write_progress(f"round_{round_idx:02d}:post_source_slice_prep_finished")
        elif source_growth["needed"]:
            round_rec["source_growth_skipped"] = {
                "reason": "source_growth_disabled_by_policy",
                "credit_boundary": "skipping source growth creates no credit; policy should enable agentic upstream when C/source/family breadth is short",
            }

        if args.allow_heavy_lean and int(after_static.get("probe_seedable_count", after_static["probe_owed_count"]) or 0) > 0:
            if args.dry_run:
                probe_selection, probe_owed_count = current_selection, int(after_static.get("probe_seedable_count", after_static["probe_owed_count"]) or 0)
            else:
                probe_selection, probe_owed_count = _probe_owed_selection(current_selection, prefix.with_suffix(".probe_owed.selection.json"))
            round_rec["probe_owed_selection"] = {"path": probe_selection, "row_count": probe_owed_count}
            _write_progress(f"round_{round_idx:02d}:probe_seed_started")
            seed = _run(_probe_seed_cmd(args, selection=probe_selection, out=str(prefix.with_suffix(".probe_seed.json")), row_context=current_row_context), timeout_s=args.command_timeout_s, dry_run=args.dry_run)
            commands.append(seed)
            round_rec["commands"].append({"stage": "probe_seed", **seed})
            seed_obj = _parse_stdout_json(seed)
            seed_report = _read_json(str(seed_obj.get("out") or "")) or {}
            round_rec["probe_seed_summary"] = _probe_seed_report_summary(seed_report if isinstance(seed_report, dict) else {})
            _write_progress(f"round_{round_idx:02d}:probe_seed_finished")
            if int(seed_obj.get("enqueued") or 0) > 0:
                _write_progress(f"round_{round_idx:02d}:probe_worker_started")
                probe = _run(_probe_worker_cmd(args, selection=probe_selection), timeout_s=args.probe_worker_timeout_s, dry_run=args.dry_run)
                commands.append(probe)
                round_rec["commands"].append({"stage": "probe_worker", **probe})
                _write_progress(f"round_{round_idx:02d}:probe_worker_finished")

        final_out = str(prefix.with_suffix(".final.selection.json"))
        final_rows = str(prefix.with_suffix(".final.rows.json"))
        _write_progress(f"round_{round_idx:02d}:final_slice_prep_started")
        rec4 = _run(_prep_cmd(args, checkpoint=checkpoint, out=final_out, md=str(prefix.with_suffix(".final.selection.md")), row_context_out=final_rows, row_context=current_row_context), timeout_s=args.command_timeout_s, dry_run=args.dry_run)
        commands.append(rec4)
        if _command_applied(rec4):
            current_selection = final_out
        final = _selection_metrics(current_selection)
        _consider_best(current_selection, current_row_context, checkpoint, final)
        round_rec["after"] = final
        rounds.append(round_rec)
        score = _selection_score(final, score_policy)
        final_readiness = _target_readiness_decision(
            final,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        )
        round_rec["target_readiness_after"] = final_readiness
        _write_progress(f"round_{round_idx:02d}:final_slice_prep_finished")
        if final_readiness["ready"]:
            stop_reason = "target_reached"
            break
        if previous_score is not None and score <= previous_score and enqueued_templates == 0 and final["probe_owed_count"] == 0 and final["static_sweep_owed_count"] == 0:
            stop_reason = "no_progress_stop_rule"
            break
        previous_score = score

    final_metrics = best_metrics
    latest_metrics = _selection_metrics(current_selection)
    result = {
        "schema": "leanmill-c-supply-growth-controller-v1",
        "generated_at_epoch": int(time.time()),
        "status": "ready" if _target_readiness_decision(
            final_metrics,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        )["ready"] else "blocked",
        "stop_reason": stop_reason,
        "proof_credit": "none_controller_only_existing_gates_decide",
        "target_credit_ready_rows": args.target_credit_ready_rows,
        "effective_target_credit_ready_rows": effective_target_credit_ready_rows,
        "work_invocation_dir": str(invocation_dir),
        "initial_checkpoint": args.checkpoint,
        "resume_previous_state": resume_previous_state,
        "final_checkpoint": best_checkpoint,
        "final_selection": best_selection,
        "final_row_context": best_row_context,
        "final_metrics": final_metrics,
        "target_readiness": _target_readiness_decision(
            final_metrics,
            breadth_policy,
            target_credit_ready_rows=effective_target_credit_ready_rows,
        ),
        "policy_profile_application": getattr(
            args,
            "_policy_profile_c_supply_growth_controller_applied",
            {"name": "", "key_count": 0, "keys": []},
        ),
        "external_source_scout_policy": _external_source_scout_policy(args),
        "selection_score_policy": score_policy,
        "controller_operating_policy": _controller_operating_policy(args),
        "c_supply_breadth_policy": breadth_policy,
        "latest_checkpoint": checkpoint,
        "latest_selection": current_selection,
        "latest_row_context": current_row_context,
        "latest_metrics": latest_metrics,
        "best_selection_rule": score_policy["ordering_rule"],
        "rounds": rounds,
        "command_count": len(commands),
        "failed_command_count": sum(1 for c in commands if int(c.get("returncode") or 0) != 0),
        "commands": commands[-40:],
    }
    if args.out:
        _write_json(args.out, result)
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_growth_") as td:
        ns = argparse.Namespace(
            work_dir=td,
            checkpoint="ck.jsonl",
            selection="sel.json",
            row_context="rows.json",
            spec_dir="specs",
            registry="registry.json",
            contract="contract.json",
            queue_db="q.sqlite",
            events="events.jsonl",
            factory_policy=str(Path(td) / "policy.json"),
            policy_profile="",
            target_credit_ready_rows=20,
            slice_limit=30,
            command_timeout_s=1,
            template_max_jobs=2,
            template_rows_per_family=2,
            agent_runtime="codex",
            agent_max_wall_time_s=1200,
            agent_max_attempts=2,
            agent_max_iterations=3,
            template_max_enqueued=2,
            template_cooldown_s=0,
            retry_existing_template_jobs=False,
            worker_id="w",
            default_codex_model="gpt-5.4-mini",
            agent_worker_max_tasks=2,
            agent_worker_max_idle_s=5,
            agent_worker_processes=2,
            allow_agent_launch=True,
            agent_worker_timeout_s=10,
            allow_heavy_lean=True,
            static_sweep_limit=3,
            source_rows_per_family=4,
            source_parallel_families=2,
            static_max_tool_calls=9,
            static_per_candidate_timeout_s=60,
            static_row_wall_timeout_s=240,
            static_wall_timeout_s=600,
            probe_seed_max_jobs=8,
            probe_seed_max_families=8,
            probe_seed_max_enqueued=8,
            probe_rows_per_work_item=4,
            max_tests_per_probe=8,
            probe_command_timeout_s=900,
            probe_command_timeout_overhead_s=120,
            probe_claim_scan_limit=300,
            probe_worker_max_tasks=8,
            probe_worker_timeout_s=900,
            dry_run=True,
            max_rounds=1,
            out=str(Path(td) / "out.json"),
            source_min_signature_hits=2,
            source_template_min_hit_count=2,
            source_materialize_missing_files=True,
            source_snapshot_dir=str(Path(td) / "source_snapshots"),
            source_mathlib_root="",
            population_elo=str(Path(td) / "population_elo.json"),
            upstream_rater_mode="observe_only",
            upstream_rater_model="gpt-5.4-mini",
            upstream_rater_run_model=False,
            upstream_rater_timeout_s=30,
            upstream_rater_reasoning_effort="low",
            upstream_rater_max_candidates=12,
            source_corpora=[],
            family_birth_enabled=True,
            family_birth_min_pressure_rows=1,
            family_birth_enqueue=False,
            family_birth_max_enqueued=0,
            family_birth_max_clusters=20,
            family_birth_cooldown_s=86400,
            family_birth_min_rows=3,
            family_birth_min_shared_tokens=1,
            family_birth_existing_family_confidence_floor=0.75,
            family_birth_existing_family_hit_floor=3,
            family_birth_include_covered_static_failures=False,
            family_birth_exclude_existing_family_tokens=True,
            family_birth_agent_runtime="codex",
            family_birth_agent_max_wall_time_s=1200,
            family_birth_agent_max_iterations=3,
        )
        src = Path(__file__).read_text()
        assert src.index('_run_static_stage("static_sweep"') < src.index('_run_template_stage("template_backfill_enqueue"')
        assert src.index('"source_static_sweep"') < src.index('"source_template_backfill_enqueue"')
        repo = Path(__file__).resolve().parents[4]
        sync_manifest = repo / "deploy/vps_sync_files.txt"
        if sync_manifest.exists():
            assert "scripts/public/control/leanmill/c_supply_credit.py" in sync_manifest.read_text(), "shared C credit helper must be shipped to VPS"
        spawn_child = Path(td) / "spawn_child.py"
        child_pid_file = Path(td) / "child.pid"
        spawn_child.write_text(
            "import subprocess, sys, time\n"
            "p = subprocess.Popen(['sleep', '30'])\n"
            "open(sys.argv[1], 'w').write(str(p.pid))\n"
            "time.sleep(30)\n"
        )
        timeout_rec = _run([sys.executable, str(spawn_child), str(child_pid_file)], timeout_s=1)
        assert timeout_rec["returncode"] == 124 and timeout_rec.get("timeout_kill") == "process_group", timeout_rec
        time.sleep(0.2)
        child_pid = child_pid_file.read_text().strip()
        ps_child = subprocess.run(["ps", "-p", child_pid, "-o", "stat="], text=True, capture_output=True)
        assert ps_child.returncode != 0 or "Z" in ps_child.stdout, {"pid": child_pid, "ps": ps_child.stdout}
        legacy_selection = Path(td) / "legacy_selection.json"
        legacy_selection.write_text(json.dumps({
            "status": "ready",
            "selected_rows": [{
                "row_id": "legacy",
                "c_discriminating_evidence_status": "c_discriminating_supply_verified",
                "static_tools_result": {"status": "failed_or_no_positive_signal", "present_arms": ["public_tool_static"]},
            }],
        }) + "\n")
        legacy_metrics = _selection_metrics(legacy_selection)
        assert legacy_metrics["static_sweep_owed_count"] == 1, legacy_metrics
        assert legacy_metrics["probe_owed_count"] == 1 and legacy_metrics["probe_seedable_count"] == 0, legacy_metrics
        ns.source_corpora = ["fresh.json"]
        demand_cmd = _demand_corpus_cmd(ns, selection="sel.json", checkpoint="ck.jsonl", out_dir="out", out="demand.json", md="demand.md")
        assert demand_cmd.count("--source-corpus") == 1 and "fresh.json" in demand_cmd, demand_cmd
        assert "--materialize-missing-source-files" in demand_cmd and "--source-snapshot-dir" in demand_cmd, demand_cmd
        source_rows = Path(td) / "source_rows.json"
        source_rows.write_text(json.dumps({"rows": [{"row_id": "r-src", "source_file": str(Path(td) / "r-src.lean"), "target_resolution_status": "pass"}]}) + "\n")
        source_report = Path(td) / "source_mine.json"
        source_report.write_text(json.dumps({
            "supply_candidate_count": 1,
            "counts": {"static_fail_family_matched_with_negative_controls": 1},
            "candidates": [{
                "row_id": "r-src",
                "source_file": str(Path(td) / "r-src.lean"),
                "static_result": "tested_no_positive_signal",
                "static_failure_class": "strict_no_signal",
                "supply_candidate": True,
                "family_matches": [{"family": "fam", "status": "candidate_family", "confidence": 0.8, "hit_count": 2, "has_negative_controls": True}],
            }],
        }) + "\n")
        candidate_rows, candidate_summary = _source_static_candidate_rows_from_reports([("mined_fam", str(source_report))], source_rows)
        assert len(candidate_rows) == 1 and candidate_rows[0]["row_id"] == "r-src", candidate_rows
        assert candidate_summary["candidate_count"] == 1 and candidate_summary["candidate_counts_by_matched_family"]["fam"] == 1, candidate_summary
        candidate_selection = _write_source_static_candidate_selection(candidate_rows, parent_selection="sel.json", out=Path(td) / "source_candidate_selection.json")
        candidate_selection_obj = _read_json(candidate_selection)
        assert candidate_selection_obj["selected_count"] == 1 and candidate_selection_obj["credit_boundary"], candidate_selection_obj
        birth_cmd = _family_birth_cmd(ns, selection="sel.json", checkpoint="ck.jsonl", row_context="rows.json", out="birth.json", md="birth.md")
        assert "scripts/public/control/leanmill/family_birth_miner.py" in birth_cmd and "--no-include-covered-static-failures" in birth_cmd, birth_cmd
        birth_worker_cmd = _agent_worker_cmd(ns, selection="sel.json", patch_mode="family_birth_candidate")
        assert "family_birth_candidate" in birth_worker_cmd and not any(str(x).startswith("c_supply_selection=") for x in birth_worker_cmd), birth_worker_cmd
        Path(ns.factory_policy).write_text(json.dumps({
            "operations": {
                "c_supply_breadth_policy": {
                    "target_credit_ready_rows": 20,
                    "target_credit_ready_family_count": 8,
                    "target_credit_ready_source_file_count": 10,
                    "target_credit_ready_source_root_count": 3,
                },
                "c_supply_source_growth_routing": {
                    "recent_ratified_seed_promotion_enabled": True,
                    "recent_ratified_seed_window_s": 3600,
                    "recent_ratified_seed_max_promoted_families": 1,
                },
                "multi_node_control_plane": {
                    "routing": {"default_weighted_nodes": ["local-mac:1", "vps-hetzner-49-13-160-58:2"]},
                },
            },
            "profiles": {
                "unit": {
                    "runner": {
                        "seed_external_source_scouts": True,
                        "external_source_scout_floor": 7,
                        "external_source_scout_max_enqueued": 5,
                        "external_source_scout_max_families": 6,
                        "external_source_scout_runtimes": "codex",
                        "external_source_scout_tasks_per_family": 1,
                    },
                    "c_supply_growth_controller": {
                        "resume_previous_running_state": True,
                        "resume_previous_running_state_max_age_s": 86400,
                        "upstream_rater_mode": "advisory",
                        "upstream_rater_run_model": True,
                        "upstream_rater_timeout_s": 600,
                        "static_per_candidate_timeout_s": 240,
                    },
                },
            },
        }) + "\n")
        ns.policy_profile = "unit"
        applied_ns = argparse.Namespace(**vars(ns))
        apply_profile_section(applied_ns, section="c_supply_growth_controller")
        assert applied_ns.upstream_rater_mode == "advisory" and applied_ns.upstream_rater_run_model is True, applied_ns
        assert applied_ns.static_per_candidate_timeout_s == 240, applied_ns
        receipt = _controller_operating_policy(applied_ns)
        assert receipt["upstream_rater"]["run_model"] is True and receipt["upstream_rater"]["mode"] == "advisory", receipt
        assert receipt["source_static_mining"]["static_per_candidate_timeout_s"] == 240, receipt
        routing_policy = _source_growth_routing_policy(applied_ns)
        assert routing_policy["recent_ratified_seed_promotion_enabled"] is True, routing_policy
        recent_queue_db = str(Path(td) / "recent_seed_queue.sqlite")
        cx = sqlite3.connect(recent_queue_db)
        cx.execute(
            """
            CREATE TABLE work_items (
                work_id TEXT PRIMARY KEY, kind TEXT, status TEXT, family TEXT,
                updated_at INTEGER, payload_json TEXT
            )
            """
        )
        cx.execute(
            "INSERT INTO work_items VALUES (?, ?, ?, ?, ?, ?)",
            ("probe:fam_new:r1", "repair_canary_probe", "done", "fam_new", int(time.time()), json.dumps({"exit_kind": "ratified_closure"})),
        )
        cx.commit()
        assert "fam_new" in _recent_ratified_seed_families(recent_queue_db, window_s=3600)
        ordered, promoted = _promote_recent_ratified_seed_corpora(
            [
                {"family": "older", "status": "written", "path": "older.json"},
                {"family": "fam_new", "status": "written", "path": "fam_new.json"},
            ],
            policy=routing_policy,
            recent_families={"fam_new"},
        )
        assert promoted == ["fam_new"] and ordered[0]["family"] == "fam_new", (promoted, ordered)
        off_ns = argparse.Namespace(**vars(applied_ns))
        off_ns.upstream_rater_mode = "off"
        off_policy = _source_growth_routing_policy(off_ns)
        off_ordered, off_promoted = _promote_recent_ratified_seed_corpora(
            [
                {"family": "older", "status": "written", "path": "older.json"},
                {"family": "fam_new", "status": "written", "path": "fam_new.json"},
            ],
            policy=off_policy,
            recent_families=_recent_ratified_seed_families(recent_queue_db, window_s=3600),
        )
        assert off_promoted == ["fam_new"] and off_ordered[0]["family"] == "fam_new", (off_promoted, off_ordered)
        old_node = __import__("os").environ.get("LEANMILL_NODE_ID")
        try:
            __import__("os").environ["LEANMILL_NODE_ID"] = "local-mac"
            routed_probe_cmd = _probe_seed_cmd(ns, selection="sel.json", out="seed.json")
            assert "--routing-nodes" in routed_probe_cmd and "local-mac:1,vps-hetzner-49-13-160-58:2" in routed_probe_cmd, routed_probe_cmd
            no_enqueue_probe_cmd = _probe_seed_cmd(argparse.Namespace(**{**vars(ns), "probe_seed_max_enqueued": 0}), selection="sel.json", out="seed.json")
            assert "--enqueue" not in no_enqueue_probe_cmd, no_enqueue_probe_cmd
        finally:
            if old_node is None:
                __import__("os").environ.pop("LEANMILL_NODE_ID", None)
            else:
                __import__("os").environ["LEANMILL_NODE_ID"] = old_node
        scout_policy = _external_source_scout_policy(ns)
        assert scout_policy["source"] == "factory_policy.profile.runner", scout_policy
        assert scout_policy["external_source_scout_floor"] == 7, scout_policy
        scout_cmd = _external_source_scout_cmd(ns, out="external_source.json", max_enqueued=3, run_id="unit")
        assert "scripts/public/control/leanmill/external_source_scout_seeder.py" in scout_cmd, scout_cmd
        assert "--enqueue" in scout_cmd and "external_source.json" in scout_cmd, scout_cmd
        assert scout_cmd[scout_cmd.index("--max-enqueued") + 1] == "3", scout_cmd
        assert scout_cmd[scout_cmd.index("--max-families") + 1] == "6", scout_cmd
        result = run_controller(ns)
        assert result["schema"] == "leanmill-c-supply-growth-controller-v1", result
        assert result["proof_credit"] == "none_controller_only_existing_gates_decide", result
        metric_order = [field["metric"] for field in result["selection_score_policy"]["fields"]]
        assert metric_order[:3] == ["credit_ready_count", "credit_ready_unique_family_count", "credit_ready_source_file_count"], result
        assert metric_order.index("probe_verified_pending_static_count") < metric_order.index("probe_seedable_count"), result
        assert "probe_seedable_count" in metric_order, result
        assert result["c_supply_breadth_policy"]["target_credit_ready_family_count"] == 8, result
        source_growth_decision = _source_growth_decision(
            {
                "credit_ready_count": 15,
                "credit_ready_unique_family_count": 8,
                "credit_ready_source_file_count": 2,
                "credit_ready_source_root_count": 1,
                "source_demand_family_count": 6,
                "static_sweep_owed_count": 10,
                "probe_owed_count": 10,
                "blockers_by_reason": {},
            },
            result["c_supply_breadth_policy"],
            target_credit_ready_rows=20,
        )
        assert source_growth_decision["needed"], source_growth_decision
        assert "credit_ready_rows" in source_growth_decision["reasons"], source_growth_decision
        assert "credit_ready_source_files" in source_growth_decision["reasons"], source_growth_decision
        growth_goal_readiness = _target_readiness_decision(
            {
                "credit_ready_count": 20,
                "credit_ready_unique_family_count": 8,
                "credit_ready_source_file_count": 10,
                "credit_ready_source_root_count": 3,
            },
            {
                "target_credit_ready_rows": 20,
                "growth_goal_credit_ready_rows": 50,
                "continue_after_minimum_floor": True,
                "target_credit_ready_family_count": 8,
                "target_credit_ready_source_file_count": 10,
                "target_credit_ready_source_root_count": 3,
            },
            target_credit_ready_rows=20,
        )
        assert growth_goal_readiness["checks"]["credit_ready_rows"]["target"] == 50, growth_goal_readiness
        assert "credit_ready_rows" in growth_goal_readiness["missing"], growth_goal_readiness
        floor_only_readiness = _target_readiness_decision(
            {
                "credit_ready_count": 20,
                "credit_ready_unique_family_count": 8,
                "credit_ready_source_file_count": 10,
                "credit_ready_source_root_count": 3,
            },
            {
                "target_credit_ready_rows": 20,
                "growth_goal_credit_ready_rows": 50,
                "continue_after_minimum_floor": False,
                "target_credit_ready_family_count": 8,
                "target_credit_ready_source_file_count": 10,
                "target_credit_ready_source_root_count": 3,
            },
            target_credit_ready_rows=20,
        )
        assert floor_only_readiness["ready"], floor_only_readiness
        blocked_legacy_source_growth = _source_growth_decision(
            {
                "credit_ready_count": 15,
                "credit_ready_unique_family_count": 8,
                "credit_ready_source_file_count": 2,
                "credit_ready_source_root_count": 1,
                "source_demand_family_count": 6,
                "static_sweep_owed_count": 10,
                "probe_owed_count": 10,
                "blockers_by_reason": {},
            },
            {**result["c_supply_breadth_policy"], "source_growth_trigger_mode": "when_unblocked"},
            target_credit_ready_rows=20,
        )
        assert not blocked_legacy_source_growth["needed"], blocked_legacy_source_growth
        assert not _target_readiness_decision(
            {
                "credit_ready_count": 20,
                "credit_ready_unique_family_count": 8,
                "credit_ready_source_file_count": 2,
                "credit_ready_source_root_count": 1,
            },
            result["c_supply_breadth_policy"],
            target_credit_ready_rows=20,
        )["ready"]
        assert Path(ns.out).exists(), result
        seed_summary = _probe_seed_report_summary({
            "generated_job_count": 1,
            "job_count": 1,
            "enqueued": 1,
            "jobs": [{
                "work_id": "probe1",
                "payload": {
                    "family": "fam",
                    "probe_corpus_meta": {
                        "target_row_count": 3,
                        "selected_row_count": 1,
                        "unresolved_row_reasons": [
                            {"row_id": "r2", "reason": "missing_source_file"},
                            {"row_id": "r3", "reason": "missing_source_file"},
                        ],
                    },
                },
            }],
        })
        assert seed_summary["unresolved_row_count"] == 2, seed_summary
        assert seed_summary["unresolved_reason_counts"]["missing_source_file"] == 2, seed_summary
        stale_work = Path(td) / "stale_dry_run"
        stale_work.mkdir()
        real_selection = Path(td) / "real_selection.json"
        real_selection.write_text(json.dumps({
            "status": "ready",
            "credit_ready_count": 1,
            "eligible_count": 2,
            "selected_count": 2,
            "selected_rows": [],
        }) + "\n")
        (stale_work / "round_00.selection.json").write_text(json.dumps({
            "status": "ready",
            "credit_ready_count": 99,
            "eligible_count": 99,
            "selected_count": 99,
            "selected_rows": [],
        }) + "\n")
        dry_result = run_controller(argparse.Namespace(**{
            **vars(ns),
            "work_dir": str(stale_work),
            "selection": str(real_selection),
            "dry_run": True,
            "allow_heavy_lean": False,
            "out": "",
        }))
        assert dry_result["rounds"][0]["before"]["path"] == str(real_selection), dry_result
        assert dry_result["final_metrics"]["credit_ready_count"] == 1, dry_result

        row_level_ready_selection = Path(td) / "row_level_ready_selection.json"
        row_level_ready_selection.write_text(json.dumps({
            "status": "blocked",
            "credit_ready_count": 0,
            "eligible_count": 5,
            "selected_count": 5,
            "selected_rows": [
                {
                    "row_id": "ready-a",
                    "probe_credit_ready": True,
                    "probe_verified_families": ["family_a"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                    "source_file": "Mathlib/Data/A.lean",
                },
                {
                    "row_id": "ready-b",
                    "probe_credit_ready": True,
                    "probe_verified_families": ["family_b"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                    "source_file": "evaluation_harness_sources/b.lean",
                },
                {
                    "row_id": "ready-a",
                    "probe_credit_ready": True,
                    "probe_verified_families": ["family_a"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                    "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
                    "source_file": "Mathlib/Data/A.lean",
                },
                {
                    "row_id": "near-ready-pending-static",
                    "probe_credit_ready": True,
                    "probe_verified_families": ["family_pending"],
                    "c_discriminating_evidence_status": "c_discriminating_probe_verified_pending_static_sweep",
                    "static_sweep_required_before_c_credit": True,
                    "static_tools_result": {"status": "unknown_not_run"},
                    "source_file": "source_mine/pending.lean",
                },
                {
                    "row_id": "not-ready",
                    "probe_credit_ready": False,
                    "probe_verified_families": ["family_c"],
                    "source_file": "queued_learning_work/c.lean",
                },
            ],
        }) + "\n")
        row_level_metrics = _selection_metrics(row_level_ready_selection)
        assert row_level_metrics["credit_ready_count"] == 2, row_level_metrics
        assert row_level_metrics["credit_ready_count_source"] == "selected_rows", row_level_metrics
        assert row_level_metrics["credit_ready_unique_family_count"] == 2, row_level_metrics
        assert row_level_metrics["credit_ready_source_file_count"] == 2, row_level_metrics
        assert row_level_metrics["credit_ready_source_root_count"] == 2, row_level_metrics
        assert row_level_metrics["probe_verified_count"] == 4, row_level_metrics
        assert row_level_metrics["probe_verified_pending_static_count"] == 1, row_level_metrics

        resume_selection = Path(td) / "resume_selection.json"
        resume_checkpoint = Path(td) / "resume_checkpoint.jsonl"
        resume_rows = Path(td) / "resume_rows.json"
        resume_selection.write_text(json.dumps({
            "status": "blocked_pending_probe_or_static_sweep",
            "credit_ready_count": 0,
            "eligible_count": 1,
            "selected_count": 1,
            "selected_rows": [{
                "row_id": "resume-row",
                "eligible": True,
                "probe_credit_ready": True,
                "probe_verified_families": ["resume_family"],
                "c_discriminating_evidence_status": "c_discriminating_probe_verified",
                "static_tools_result": {"public_exit": "tested_no_positive_signal", "governed_exit": "tested_no_positive_signal"},
            }],
        }) + "\n")
        resume_checkpoint.write_text(json.dumps({"row_id": "resume-row", "arm": "governed_public_tool_static", "learning_exit": "tested_no_positive_signal"}) + "\n")
        resume_rows.write_text(json.dumps({"rows": [{"row_id": "resume-row"}]}) + "\n")
        resume_status = Path(td) / "resume_status.json"
        resume_status.write_text(json.dumps({
            "schema": "leanmill-c-supply-growth-controller-v1",
            "status": "running",
            "generated_at_epoch": int(time.time()),
            "current_stage": "round_00:post_static_refresh_finished",
            "latest_selection": str(resume_selection),
            "latest_checkpoint": str(resume_checkpoint),
            "latest_row_context": str(resume_rows),
            "best_selection": str(resume_selection),
            "best_checkpoint": str(resume_checkpoint),
            "best_row_context": str(resume_rows),
        }) + "\n")
        resume_result = run_controller(argparse.Namespace(**{
            **vars(ns),
            "selection": str(real_selection),
            "checkpoint": str(Path(td) / "base_checkpoint.jsonl"),
            "row_context": str(Path(td) / "base_rows.json"),
            "out": str(resume_status),
            "dry_run": True,
            "allow_heavy_lean": False,
            "max_rounds": 1,
        }))
        assert resume_result["resume_previous_state"]["resumed"] is True, resume_result
        assert resume_result["rounds"][0]["before"]["path"] == str(resume_selection), resume_result
        assert resume_result["initial_checkpoint"] != resume_result["latest_checkpoint"], resume_result

        stage_dir = Path(td) / "run_stage_resume"
        stage_dir.mkdir()
        stage_checkpoint = stage_dir / "round_00.source_candidates.static_checkpoint.jsonl"
        stage_rows = stage_dir / "round_00.source_augmented.rows.json"
        stage_candidate_rows = stage_dir / "round_00.source_static_candidates.selection.json"
        stage_checkpoint.write_text(json.dumps({"row_id": "stage-row", "arm": "governed_public_tool_static", "learning_exit": "tested_no_positive_signal"}) + "\n")
        stage_rows.write_text(json.dumps({"rows": [{"row_id": "stage-row"}]}) + "\n")
        stage_candidate_rows.write_text(json.dumps({"rows": [{"row_id": "stage-row", "source_static_candidate": {"mined_family": "stage_family"}}]}) + "\n")
        stage_status = Path(td) / "stage_resume_status.json"
        stage_status.write_text(json.dumps({
            "schema": "leanmill-c-supply-growth-controller-v1",
            "status": "running",
            "generated_at_epoch": int(time.time()),
            "current_stage": "round_00:source_candidate_governed_static_started",
            "work_invocation_dir": str(stage_dir),
            "latest_selection": str(resume_selection),
            "latest_checkpoint": str(resume_checkpoint),
            "latest_row_context": str(resume_rows),
        }) + "\n")
        stage_state = _previous_running_state(argparse.Namespace(**{**vars(ns), "out": str(stage_status)}))
        assert stage_state["resumed"] is True, stage_state
        assert stage_state["stage_local_resume"]["resumed"] is True, stage_state
        assert stage_state["latest_checkpoint"] == str(stage_checkpoint), stage_state
        assert stage_state["latest_row_context"] == str(stage_candidate_rows), stage_state
        stage_status.write_text(json.dumps({
            "schema": "leanmill-c-supply-growth-controller-v1",
            "status": "stopped",
            "generated_at_epoch": int(time.time()),
        }) + "\n")
        recent_stage_state = _previous_running_state(argparse.Namespace(**{
            **vars(ns),
            "out": str(stage_status),
            "work_dir": str(Path(td)),
            "selection": str(resume_selection),
        }))
        assert recent_stage_state["resumed"] is True, recent_stage_state
        assert recent_stage_state["fallback_reason"] == "previous_not_running", recent_stage_state
        assert recent_stage_state["latest_checkpoint"] == str(stage_checkpoint), recent_stage_state

        old_run = globals()["_run"]
        old_metrics = globals()["_selection_metrics"]
        try:
            def fake_run_regression(cmd, *, timeout_s, dry_run=False):
                out = ""
                for idx, part in enumerate(cmd):
                    if part == "--out" and idx + 1 < len(cmd):
                        out = cmd[idx + 1]
                if out:
                    Path(out).parent.mkdir(parents=True, exist_ok=True)
                    Path(out).write_text("{}\n")
                return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}
            def fake_metrics_regression(path):
                text = str(path)
                if text == "seed_selection.json":
                    return {"path": text, "status": "ready", "credit_ready_count": 0, "eligible_count": 5, "selected_count": 5, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 5, "probe_owed_count": 5}
                return {"path": text, "status": "blocked", "credit_ready_count": 0, "eligible_count": 0, "selected_count": 0, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0}
            globals()["_run"] = fake_run_regression
            globals()["_selection_metrics"] = fake_metrics_regression
            regression_result = run_controller(argparse.Namespace(**{**vars(ns), "selection": "seed_selection.json", "out": "", "dry_run": False, "allow_heavy_lean": False, "max_rounds": 1}))
            assert regression_result["rounds"][0]["before"]["path"] == "seed_selection.json", regression_result
            assert regression_result["final_metrics"]["eligible_count"] == 5, regression_result
        finally:
            globals()["_run"] = old_run
            globals()["_selection_metrics"] = old_metrics

        old_run = globals()["_run"]
        old_metrics = globals()["_selection_metrics"]
        try:
            def fake_run_seedable(cmd, *, timeout_s, dry_run=False):
                out = ""
                for idx, part in enumerate(cmd):
                    if part == "--out" and idx + 1 < len(cmd):
                        out = cmd[idx + 1]
                if out:
                    Path(out).parent.mkdir(parents=True, exist_ok=True)
                    Path(out).write_text("{}\n")
                return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}
            def fake_metrics_seedable(path):
                text = str(path)
                if text == "seed_selection.json":
                    return {"path": text, "status": "ready", "credit_ready_count": 0, "eligible_count": 21, "selected_count": 21, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 21, "probe_owed_count": 21, "probe_seedable_count": 0}
                if "selection" in text:
                    return {"path": text, "status": "blocked", "credit_ready_count": 0, "eligible_count": 10, "selected_count": 10, "probe_pending_count": 10, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 9, "probe_owed_count": 10, "probe_seedable_count": 1}
                return {"path": text, "status": "blocked", "credit_ready_count": 0, "eligible_count": 0, "selected_count": 0, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0, "probe_seedable_count": 0}
            globals()["_run"] = fake_run_seedable
            globals()["_selection_metrics"] = fake_metrics_seedable
            seedable_result = run_controller(argparse.Namespace(**{**vars(ns), "selection": "seed_selection.json", "out": "", "dry_run": False, "allow_heavy_lean": True, "static_sweep_limit": 0, "max_rounds": 1}))
            assert seedable_result["rounds"][0]["before"]["probe_seedable_count"] == 1, seedable_result
            assert "round_00.selection" in seedable_result["rounds"][0]["before"]["path"], seedable_result
            assert any(c.get("stage") == "static_sweep" and c.get("skipped") for c in seedable_result["rounds"][0]["commands"]), seedable_result
        finally:
            globals()["_run"] = old_run
            globals()["_selection_metrics"] = old_metrics

        old_run = globals()["_run"]
        old_metrics = globals()["_selection_metrics"]
        try:
            seen_prep_checkpoints: list[str] = []

            def fake_run_partial_static(cmd, *, timeout_s, dry_run=False):
                if "scripts/public/control/leanmill/c_discriminating_slice_prep.py" in cmd:
                    if "--checkpoint" in cmd:
                        seen_prep_checkpoints.append(str(cmd[cmd.index("--checkpoint") + 1]))
                    if "--out" in cmd:
                        Path(cmd[cmd.index("--out") + 1]).parent.mkdir(parents=True, exist_ok=True)
                        Path(cmd[cmd.index("--out") + 1]).write_text("{}\n")
                    return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}
                if "scripts/public/control/leanmill/c_static_sweep_backfill.py" in cmd:
                    out_checkpoint = str(cmd[cmd.index("--out-checkpoint") + 1])
                    Path(out_checkpoint).parent.mkdir(parents=True, exist_ok=True)
                    Path(out_checkpoint).write_text(json.dumps({
                        "row_id": "partial-row",
                        "arm": "governed_public_tool_static",
                        "learning_exit": "tested_no_positive_signal",
                        "status": "done",
                    }) + "\n")
                    return {
                        "cmd": cmd,
                        "returncode": 124,
                        "timed_out": True,
                        "timeout_kill": "process_group",
                        "stdout_tail": "",
                        "stderr_tail": "",
                    }
                if "--out" in cmd:
                    Path(cmd[cmd.index("--out") + 1]).parent.mkdir(parents=True, exist_ok=True)
                    Path(cmd[cmd.index("--out") + 1]).write_text("{}\n")
                return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}

            def fake_metrics_partial_static(path):
                text = str(path)
                if "post_static" in text or "post_template" in text:
                    return {
                        "path": text,
                        "status": "ready",
                        "credit_ready_count": 50,
                        "credit_ready_unique_family_count": 8,
                        "credit_ready_source_file_count": 10,
                        "credit_ready_source_root_count": 3,
                        "eligible_count": 50,
                        "selected_count": 50,
                        "probe_pending_count": 0,
                        "probe_terminal_nonuseful_count": 0,
                        "blockers_by_reason": {},
                        "static_sweep_owed_count": 0,
                        "probe_owed_count": 0,
                        "probe_seedable_count": 0,
                    }
                return {
                    "path": text,
                    "status": "blocked",
                    "credit_ready_count": 0,
                    "eligible_count": 1,
                    "selected_count": 1,
                    "probe_pending_count": 0,
                    "probe_terminal_nonuseful_count": 0,
                    "blockers_by_reason": {},
                    "static_sweep_owed_count": 1,
                    "probe_owed_count": 0,
                    "probe_seedable_count": 0,
                }

            globals()["_run"] = fake_run_partial_static
            globals()["_selection_metrics"] = fake_metrics_partial_static
            partial_static_result = run_controller(argparse.Namespace(**{**vars(ns), "selection": "seed_selection.json", "out": "", "dry_run": False, "allow_heavy_lean": True, "max_rounds": 1}))
            assert any(str(path).endswith(".static_checkpoint.jsonl") for path in seen_prep_checkpoints[1:]), seen_prep_checkpoints
            static_command = next(c for c in partial_static_result["rounds"][0]["commands"] if c.get("stage") == "static_sweep")
            assert static_command.get("partial_checkpoint_adopted") is True, static_command
        finally:
            globals()["_run"] = old_run
            globals()["_selection_metrics"] = old_metrics

        old_run = globals()["_run"]
        old_metrics = globals()["_selection_metrics"]
        try:
            progress_out = Path(td) / "progress_status.json"
            seen_progress_stages: list[str] = []

            def fake_run_progress(cmd, *, timeout_s, dry_run=False):
                current_status = _read_json(progress_out) or {}
                if isinstance(current_status, dict) and current_status.get("current_stage"):
                    seen_progress_stages.append(str(current_status.get("current_stage")))
                out = ""
                for idx, part in enumerate(cmd):
                    if part == "--out" and idx + 1 < len(cmd):
                        out = cmd[idx + 1]
                if out:
                    Path(out).parent.mkdir(parents=True, exist_ok=True)
                    Path(out).write_text("{}\n")
                return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}

            def fake_metrics_progress(path):
                text = str(path)
                if "final" in text:
                    return {"path": text, "status": "blocked", "credit_ready_count": 2, "eligible_count": 4, "selected_count": 4, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0, "probe_seedable_count": 0}
                return {"path": text, "status": "blocked", "credit_ready_count": 1, "eligible_count": 3, "selected_count": 3, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0, "probe_seedable_count": 0}

            globals()["_run"] = fake_run_progress
            globals()["_selection_metrics"] = fake_metrics_progress
            progress_result = run_controller(argparse.Namespace(**{**vars(ns), "selection": "seed_selection.json", "out": str(progress_out), "dry_run": False, "allow_heavy_lean": False, "max_rounds": 1}))
            assert "round_00:slice_prep_started" in seen_progress_stages, seen_progress_stages
            assert "round_00:template_backfill_enqueue_started" in seen_progress_stages, seen_progress_stages
            assert progress_result["latest_metrics"]["credit_ready_count"] == 2, progress_result
            assert progress_result["final_selection"], progress_result
        finally:
            globals()["_run"] = old_run
            globals()["_selection_metrics"] = old_metrics

        old_run = globals()["_run"]
        old_metrics = globals()["_selection_metrics"]
        try:
            def fake_run(cmd, *, timeout_s, dry_run=False):
                out = ""
                for idx, part in enumerate(cmd):
                    if part == "--out" and idx + 1 < len(cmd):
                        out = cmd[idx + 1]
                if out:
                    Path(out).parent.mkdir(parents=True, exist_ok=True)
                    Path(out).write_text("{}\n")
                return {"cmd": cmd, "returncode": 0, "stdout_tail": "{}", "stderr_tail": ""}
            def fake_metrics(path):
                text = str(path)
                if "post_static" in text:
                    return {"path": text, "status": "blocked", "credit_ready_count": 2, "eligible_count": 6, "selected_count": 6, "probe_pending_count": 4, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0}
                if "final" in text:
                    return {"path": text, "status": "blocked", "credit_ready_count": 0, "eligible_count": 0, "selected_count": 0, "probe_pending_count": 0, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0}
                return {"path": text, "status": "blocked", "credit_ready_count": 1, "eligible_count": 3, "selected_count": 3, "probe_pending_count": 1, "probe_terminal_nonuseful_count": 0, "blockers_by_reason": {}, "static_sweep_owed_count": 0, "probe_owed_count": 0}
            globals()["_run"] = fake_run
            globals()["_selection_metrics"] = fake_metrics
            result2 = run_controller(argparse.Namespace(**{**vars(ns), "out": "", "max_rounds": 1}))
            assert result2["final_metrics"]["credit_ready_count"] == 2, result2
            assert "post_static" in result2["final_selection"], result2
            assert "final" in result2["latest_selection"], result2
        finally:
            globals()["_run"] = old_run
            globals()["_selection_metrics"] = old_metrics
    print("leanmill_c_supply_growth_controller self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--registry", default=REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--queue-db", default=f"{DATA_DIR}/leanmill_work_queue.sqlite")
    ap.add_argument("--events", default=f"{DATA_DIR}/leanmill_work_queue_events.jsonl")
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--target-credit-ready-rows", type=int, default=20)
    ap.add_argument("--slice-limit", type=int, default=30)
    ap.add_argument("--max-rounds", type=int, default=1)
    ap.add_argument("--command-timeout-s", type=int, default=900)
    ap.add_argument("--template-max-jobs", type=int, default=8)
    ap.add_argument("--template-rows-per-family", type=int, default=2)
    ap.add_argument("--template-max-enqueued", type=int, default=8)
    ap.add_argument("--template-cooldown-s", type=int, default=3600)
    ap.add_argument("--retry-existing-template-jobs", action="store_true")
    ap.add_argument("--allow-agent-launch", action="store_true")
    ap.add_argument("--agent-runtime", choices=["balanced", "codex", "claude"], default="balanced")
    ap.add_argument("--default-codex-model", default="gpt-5.4-mini")
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--agent-max-attempts", type=int, default=2)
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-worker-max-tasks", type=int, default=4)
    ap.add_argument("--agent-worker-max-idle-s", type=int, default=20)
    ap.add_argument("--agent-worker-processes", type=int, default=1)
    ap.add_argument("--agent-worker-timeout-s", type=int, default=1800)
    ap.add_argument("--allow-heavy-lean", action="store_true")
    ap.add_argument("--static-sweep-limit", type=int, default=8)
    ap.add_argument("--source-rows-per-family", type=int, default=4)
    ap.add_argument("--source-parallel-families", type=int, default=1)
    ap.add_argument("--source-min-signature-hits", type=int, default=2)
    ap.add_argument("--source-template-min-hit-count", type=int, default=2)
    ap.add_argument("--source-materialize-missing-files", action="store_true")
    ap.add_argument("--source-snapshot-dir", default=f"{DATA_DIR}/evaluation_harness_sources")
    ap.add_argument("--source-mathlib-root", default="")
    ap.add_argument("--static-max-tool-calls", type=int, default=9)
    ap.add_argument("--static-per-candidate-timeout-s", type=int, default=60)
    ap.add_argument("--static-row-wall-timeout-s", type=int, default=240)
    ap.add_argument("--static-wall-timeout-s", type=int, default=900)
    ap.add_argument("--probe-seed-max-jobs", type=int, default=12)
    ap.add_argument("--probe-seed-max-families", type=int, default=8)
    ap.add_argument("--probe-seed-max-enqueued", type=int, default=8)
    ap.add_argument("--probe-rows-per-work-item", type=int, default=4)
    ap.add_argument("--max-tests-per-probe", type=int, default=0)
    ap.add_argument("--probe-command-timeout-s", type=int, default=900)
    ap.add_argument("--probe-command-timeout-overhead-s", type=int, default=120)
    ap.add_argument("--probe-claim-scan-limit", type=int, default=5000)
    ap.add_argument("--probe-worker-max-tasks", type=int, default=8)
    ap.add_argument("--probe-worker-timeout-s", type=int, default=1800)
    ap.add_argument("--worker-id", default="leanmill-c-supply-growth")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    args.source_min_signature_hits = max(1, int(args.source_min_signature_hits))
    args.source_template_min_hit_count = max(2, int(args.source_template_min_hit_count))
    args.population_elo = f"{DATA_DIR}/leanmill_population_elo.json"
    args.upstream_rater_mode = "observe_only"
    args.upstream_rater_model = "gpt-5.4-mini"
    args.upstream_rater_run_model = False
    args.upstream_rater_timeout_s = 300
    args.upstream_rater_reasoning_effort = "low"
    args.upstream_rater_max_candidates = 24
    args.source_corpora = []
    args.source_materialize_missing_files = bool(args.source_materialize_missing_files)
    args.source_snapshot_dir = str(args.source_snapshot_dir)
    args.source_mathlib_root = str(args.source_mathlib_root)
    args.family_birth_enabled = True
    args.family_birth_min_pressure_rows = 1
    args.family_birth_enqueue = False
    args.family_birth_max_enqueued = 0
    args.family_birth_max_clusters = 20
    args.family_birth_cooldown_s = 86400
    args.family_birth_min_rows = 3
    args.family_birth_min_shared_tokens = 1
    args.family_birth_existing_family_confidence_floor = 0.75
    args.family_birth_existing_family_hit_floor = 3
    args.family_birth_include_covered_static_failures = False
    args.family_birth_exclude_existing_family_tokens = True
    args.family_birth_agent_runtime = "codex"
    args.family_birth_agent_max_wall_time_s = args.agent_max_wall_time_s
    args.family_birth_agent_max_iterations = args.agent_max_iterations
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="c_supply_growth_controller")
    result = run_controller(args)
    print(json.dumps({
        "status": result["status"],
        "stop_reason": result["stop_reason"],
        "credit_ready_count": result["final_metrics"].get("credit_ready_count"),
        "target_readiness_missing": result.get("target_readiness", {}).get("missing"),
        "eligible_count": result["final_metrics"].get("eligible_count"),
        "final_selection": result["final_selection"],
        "out": args.out,
    }, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
