#!/usr/bin/env python3
"""LeanMill safe 24x7 control-plane runner.

This runner does not launch heavy Lean proof execution. It keeps the factory
control plane live: refreshes deterministic state, enqueues station work orders,
drains safe deterministic registry-refresh work, and writes an operating receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import apply_profile_section, multi_node_routing_plan, priority_value, read_policy
from leanmill_paths import DATA_DIR as DEFAULT_DATA_DIR
from leanmill_paths import FACTORY_POLICY as DEFAULT_FACTORY_POLICY
from leanmill_paths import REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY


DEFAULT_STATUS = f"{DEFAULT_DATA_DIR}/leanmill_24x7_status.json"
DEFAULT_SCHEDULER_PLAN = f"{DEFAULT_DATA_DIR}/station_scheduler_plan.json"
DEFAULT_STATION_HEALTH = f"{DEFAULT_DATA_DIR}/station_health_dashboard.json"
DEFAULT_OBSERVABILITY = f"{DEFAULT_DATA_DIR}/leanmill_observability.json"
DEFAULT_OBSERVABILITY_MD = f"{DEFAULT_DATA_DIR}/leanmill_observability.md"
DEFAULT_FACTORY_INTELLIGENCE = f"{DEFAULT_DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_FACTORY_INTELLIGENCE_MD = f"{DEFAULT_DATA_DIR}/leanmill_factory_intelligence.md"
DEFAULT_POPULATION_ELO = f"{DEFAULT_DATA_DIR}/leanmill_population_elo.json"
DEFAULT_POPULATION_ELO_MD = f"{DEFAULT_DATA_DIR}/leanmill_population_elo.md"
DEFAULT_LEARNING_SEED_PLAN = f"{DEFAULT_DATA_DIR}/learning_work_seed_plan.json"
DEFAULT_SELF_CORRECTION_PLAN = f"{DEFAULT_DATA_DIR}/self_correction_work_seed_plan.json"
DEFAULT_SELF_CORRECTION_ACTION_IMPACT = f"{DEFAULT_DATA_DIR}/self_correction_action_impact.jsonl"
DEFAULT_FAMILY_BIRTH_PLAN = f"{DEFAULT_DATA_DIR}/family_birth_candidates.json"
DEFAULT_FAMILY_BIRTH_PLAN_MD = f"{DEFAULT_DATA_DIR}/family_birth_candidates.md"
DEFAULT_C_SUPPLY_BATCH_STATUS = f"{DEFAULT_DATA_DIR}/c_supply_batch_status.json"
DEFAULT_C_SUPPLY_BATCH_MD = f"{DEFAULT_DATA_DIR}/c_supply_batch_status.md"
DEFAULT_C_SUPPLY_BATCH_SELECTION = f"{DEFAULT_DATA_DIR}/c_supply_batch_c_discriminating_slice.json"
DEFAULT_C_SUPPLY_BATCH_CHECKPOINT = f"{DEFAULT_DATA_DIR}/c_supply_batch_checkpoint.jsonl"
DEFAULT_C_SUPPLY_BATCH_ROW_CONTEXT = f"{DEFAULT_DATA_DIR}/c_supply_batch_row_context.json"
DEFAULT_C_SUPPLY_EXPOST_CLEANER = f"{DEFAULT_DATA_DIR}/c_supply_batch_expost_cleaner.json"
DEFAULT_C_SUPPLY_CLEAN_CHECKPOINT = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_C_SUPPLY_CLEAN_ROW_CONTEXT = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_row_context.json"
DEFAULT_C_SUPPLY_CLEAN_SELECTION = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_C_SUPPLY_CLEAN_SELECTION_MD = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.md"
DEFAULT_C_SUPPLY_CLEAN_SELECTED_ROW_CONTEXT = f"{DEFAULT_DATA_DIR}/c_supply_batch_cleaned_c_discriminating_row_context.json"
DEFAULT_C_SUPPLY_GROWTH_STATUS = f"{DEFAULT_DATA_DIR}/c_supply_growth_controller.json"
DEFAULT_C_SUPPLY_GROWTH_WORK_DIR = "/tmp/rung1/leanmill_c_supply_growth_controller"
DEFAULT_C_SUPPLY_CONVERSION_PRIORITIZER = f"{DEFAULT_DATA_DIR}/c_supply_conversion_prioritizer.json"
DEFAULT_AGENTIC_PORTFOLIO_STATUS = f"{DEFAULT_DATA_DIR}/agentic_portfolio_controller.json"
DEFAULT_EXTERNAL_SOURCE_SCOUT_SEED_PLAN = f"{DEFAULT_DATA_DIR}/external_source_scout_seed_plan.json"
DEFAULT_BACKLOG_REPLENISHER_STATUS = f"{DEFAULT_DATA_DIR}/backlog_replenisher_status.json"
DEFAULT_DEAD_LETTER_TRIAGE_STATUS = f"{DEFAULT_DATA_DIR}/dead_letter_triage_status.json"
DEFAULT_RETRYABLE_FAILURE_RECOVERY_STATUS = f"{DEFAULT_DATA_DIR}/retryable_failure_recovery.json"
DEFAULT_RECOVER_PRUNED_SOURCE_REQUESTS_STATUS = f"{DEFAULT_DATA_DIR}/recover_pruned_source_requests_status.json"
DEFAULT_RECOVER_REJECTED_BINDINGS_STATUS = f"{DEFAULT_DATA_DIR}/recover_rejected_source_bindings_status.json"
DEFAULT_EXTERNAL_SOURCE_SEARCH_RECOVERY_STATUS = f"{DEFAULT_DATA_DIR}/external_source_search_recovery.json"
DEFAULT_EXPAND100_SOURCE_DIR = "/tmp/rung1/mcb_expand100/files"
DEFAULT_EXPAND100_CORPUS = f"{DEFAULT_DATA_DIR}/mcb_expand100_active_corpus.json"
DEFAULT_RECOVER_PRUNED_LOOKBACK_S = 6 * 60 * 60
DEFAULT_AGENT_OUTPUT_INGESTION_STATUS = f"{DEFAULT_DATA_DIR}/agent_output_ingestion_status.json"
DEFAULT_SOURCE_BINDING_INGESTION_STATUS = f"{DEFAULT_DATA_DIR}/source_binding_ingestion_status.json"
DEFAULT_SOURCE_FAMILY_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
DEFAULT_SOURCE_PLAN = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.json"
DEFAULT_SOURCE_PLAN_MD = f"{DEFAULT_DATA_DIR}/residual_family_source_plan.md"
DEFAULT_CANARY_PACKETS = f"{DEFAULT_DATA_DIR}/residual_family_canary_packets.json"
DEFAULT_SOURCE_SEARCH_INTEGRATIONS = f"{DEFAULT_DATA_DIR}/source_search_integrations"
DEFAULT_HELDOUT_SCOUT = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.json"
DEFAULT_HELDOUT_SCOUT_MD = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.md"
DEFAULT_HELDOUT_PROMOTION = f"{DEFAULT_DATA_DIR}/heldout_promotion_worker.json"
DEFAULT_HELDOUT_PROMOTION_MD = f"{DEFAULT_DATA_DIR}/heldout_promotion_worker.md"
DEFAULT_ANDON_CORD = f"{DEFAULT_DATA_DIR}/leanmill_andon_cord.json"
DEFAULT_POST_PROBE_TRIAGE_STATUS = f"{DEFAULT_DATA_DIR}/post_probe_triage_status.json"
DEFAULT_GOVERNANCE_SENTINEL = f"{DEFAULT_DATA_DIR}/leanmill_governance_sentinel_suite_latest.json"
DEFAULT_LANE_EXECUTION_ORDER = [
    "source_review",
    "source_scout",
    "source_search",
    "source_search_integrator",
    "source_binding_probe",
    "agent_repair",
    "generic_probe",
]
KNOWN_LANE_EXECUTION_STATIONS = set(DEFAULT_LANE_EXECUTION_ORDER)


def _population_elo_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/public/control/leanmill/population_elo.py",
        "--checkpoint", args.population_elo_checkpoint,
        "--run-id", args.population_elo_run_id,
        "--policy", args.factory_policy,
        "--out", args.population_elo_out,
        "--md", args.population_elo_md,
    ]


def _apply_policy_profile(args: argparse.Namespace) -> None:
    receipt = apply_profile_section(args, section="runner")
    setattr(args, "_policy_profile_applied", receipt)


def _profile_runner_int(args: argparse.Namespace, key: str, fallback: int) -> int:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return int(fallback)
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {})
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    if not isinstance(runner, dict):
        return int(fallback)
    try:
        return int(runner.get(key) if runner.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def _profile_runner_bool(args: argparse.Namespace, key: str, fallback: bool) -> bool:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return bool(fallback)
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {})
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    if not isinstance(runner, dict):
        return bool(fallback)
    value = runner.get(key)
    if value is None:
        return bool(fallback)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _profile_runner_list(args: argparse.Namespace, key: str, fallback: list[str]) -> list[str]:
    profile_name = str(getattr(args, "policy_profile", "") or "")
    if not profile_name:
        return list(fallback)
    policy = read_policy(getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY))
    profile = ((policy.get("profiles") or {}).get(profile_name) or {})
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    if not isinstance(runner, dict):
        return list(fallback)
    value = runner.get(key)
    if value is None:
        return list(fallback)
    if isinstance(value, str):
        values = _csv_values(value)
    elif isinstance(value, list):
        values = [str(v).strip() for v in value if str(v).strip()]
    else:
        return list(fallback)
    return values or list(fallback)


def _lane_execution_order(args: argparse.Namespace) -> tuple[list[str], list[str], list[str]]:
    requested = _profile_runner_list(args, "lane_execution_order", DEFAULT_LANE_EXECUTION_ORDER)
    order: list[str] = []
    unknown: list[str] = []
    for lane in requested:
        if lane not in KNOWN_LANE_EXECUTION_STATIONS:
            unknown.append(lane)
            continue
        if lane not in order:
            order.append(lane)
    appended_defaults: list[str] = []
    for lane in DEFAULT_LANE_EXECUTION_ORDER:
        if lane not in order:
            order.append(lane)
            appended_defaults.append(lane)
    return order, unknown, appended_defaults


def _source_review_worker_passes(args: argparse.Namespace) -> int:
    return max(0, _profile_runner_int(args, "source_review_worker_passes", 0))


def _source_agent_workers(args: argparse.Namespace) -> int:
    return max(0, _profile_runner_int(args, "source_agent_workers", 0))


def _source_binding_probe_worker_passes(args: argparse.Namespace) -> int:
    return max(0, _profile_runner_int(args, "source_binding_probe_worker_passes", 0))


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


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


def _run(cmd: list[str], *, timeout_s: int) -> dict[str, Any]:
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        stdout, stderr = proc.communicate(timeout=max(1, int(timeout_s)))
    except subprocess.TimeoutExpired:
        if proc is not None:
            _kill_process_group(proc)
            stdout, stderr = proc.communicate()
        else:
            stdout, stderr = "", ""
        return {
            "cmd": _display_cmd(cmd),
            "returncode": 124,
            "timed_out": True,
            "timeout_s": int(timeout_s),
            "stdout_tail": (stdout or "")[-2000:],
            "stderr_tail": (stderr or "")[-2000:],
            "timeout_kill": "process_group",
        }
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "timed_out": False,
        "timeout_s": int(timeout_s),
        "stdout_tail": (stdout or "")[-2000:],
        "stderr_tail": (stderr or "")[-2000:],
    }


def _run_phase(args: argparse.Namespace, *, phase: str, cmd: list[str], timeout_s: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    started = int(time.time())
    _write_progress_status(args, stage=f"phase:{phase}:started", extra={
        "phase": phase,
        "phase_started_at_epoch": started,
        "timeout_s": int(timeout_s),
        "cmd": _display_cmd(cmd),
        **(extra or {}),
    })
    result = _run(cmd, timeout_s=timeout_s)
    _write_progress_status(args, stage=f"phase:{phase}:finished", extra={
        "phase": phase,
        "phase_started_at_epoch": started,
        "phase_elapsed_s": max(0, int(time.time()) - started),
        "returncode": result.get("returncode"),
        "timed_out": bool(result.get("timed_out")),
        **(extra or {}),
    })
    return result


def _run_andon_cord(args: argparse.Namespace) -> dict[str, Any]:
    if not _profile_runner_bool(args, "run_andon_cord", True):
        return {
            "cmd": ["<python>", "scripts/public/control/leanmill/andon_cord.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "policy_disabled",
        }
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/andon_cord.py",
        "--intelligence", args.factory_intelligence_out,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", args.andon_cord,
        "--min-source-bound-probes", str(_profile_runner_int(args, "andon_min_source_bound_probes", 5)),
        "--min-source-flow", str(_profile_runner_int(args, "andon_min_source_flow", 20)),
        "--min-governed-value", str(_profile_runner_int(args, "andon_min_governed_value", 1)),
        "--min-probe-open", str(_profile_runner_int(args, "andon_min_probe_open", 1)),
        "--min-gm-open", str(_profile_runner_int(args, "andon_min_gm_open", 1)),
        "--apply",
    ]
    return _run(cmd, timeout_s=args.command_timeout_s)


def _run_c_supply_conversion_prioritizer(args: argparse.Namespace) -> dict[str, Any]:
    out_path = getattr(args, "c_supply_conversion_prioritizer_status", DEFAULT_C_SUPPLY_CONVERSION_PRIORITIZER)
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/c_supply_conversion_prioritizer.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--intelligence", args.factory_intelligence_out,
        "--factory-policy", args.factory_policy,
        "--out", out_path,
    ]
    return _run(cmd, timeout_s=args.command_timeout_s)


def _run_agentic_portfolio_controller(args: argparse.Namespace, *, phase: str = "post_factory_intelligence") -> dict[str, Any]:
    out_path = getattr(args, "agentic_portfolio_status", DEFAULT_AGENTIC_PORTFOLIO_STATUS)
    if not _profile_runner_bool(args, "run_agentic_portfolio", False):
        return {
            "cmd": ["<python>", "scripts/public/control/leanmill/agentic_portfolio_controller.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "policy_disabled",
            "portfolio_phase": phase,
            "out": out_path,
        }
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/agentic_portfolio_controller.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--factory-intelligence", args.factory_intelligence_out,
        "--c-supply-growth", args.c_supply_growth_status,
        "--selection", args.c_supply_clean_selection,
        "--checkpoint", args.c_supply_clean_checkpoint,
        "--row-context", args.c_supply_clean_row_context,
        "--spec-dir", args.family_spec_dir,
        "--source-search-integrations", args.source_search_integrations,
        "--source-binding-ingest-out", args.source_binding_ingestion_status,
        "--agent-output-ingest-out", args.agent_output_ingestion_status,
        "--andon-cord", args.andon_cord,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--worker-id", f"{args.worker_id}-agentic-portfolio",
        "--out", out_path,
        "--command-timeout-s", str(max(1, int(args.command_timeout_s))),
        "--run-id", f"{args.worker_id}_{phase}_{int(time.time())}",
    ]
    result = _run(cmd, timeout_s=args.command_timeout_s)
    result["portfolio_phase"] = phase
    return result



def _csv_values(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def _artifact_slug(value: str, *, max_chars: int = 80) -> str:
    raw = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "artifact"
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]
    suffix = f"_{digest}"
    if len(raw) + len(suffix) <= max_chars:
        return f"{raw}{suffix}"
    return f"{raw[:max(1, max_chars - len(suffix))].rstrip('_')}{suffix}"


def _self_correction_run_id(rec_class: str, *, ordinal: int) -> str:
    return f"self_correct_{_artifact_slug(rec_class, max_chars=64)}_{time.time_ns()}_{int(ordinal)}"


def _default_self_correction_path(base_path: str, *, rec_class: str, ordinal: int, label: str, suffix: str = ".json", run_id: str = "") -> str:
    base = Path(base_path)
    stem = _artifact_slug(run_id or f"{rec_class}_{int(time.time())}_{int(ordinal)}", max_chars=96)
    return str(base.with_name(f"self_correction_{stem}_{label}{base.suffix or suffix}"))


def _json_from_stdout_tail(text: str) -> dict[str, Any]:
    for line in reversed(str(text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    try:
        obj = json.loads(str(text or "{}").strip() or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_progress_status(args: argparse.Namespace, *, stage: str, extra: dict[str, Any] | None = None) -> None:
    status = {
        "schema": "leanmill-24x7-progress-status-v1",
        "generated_at_epoch": int(time.time()),
        "stage": stage,
        "worker_id": getattr(args, "worker_id", ""),
        "policy_profile": getattr(args, "policy_profile", ""),
        "runner_pid": os.getpid(),
        "final_status_pending": True,
    }
    portfolio_ref = getattr(args, "agentic_portfolio_status", DEFAULT_AGENTIC_PORTFOLIO_STATUS)
    portfolio = _read_json(portfolio_ref)
    if portfolio:
        status["agentic_portfolio_snapshot"] = {
            "path": portfolio_ref,
            "status": portfolio.get("status"),
            "run_id": portfolio.get("run_id"),
            "command_count": portfolio.get("command_count"),
            "failed_command_count": portfolio.get("failed_command_count"),
            "selected_lanes": [
                str(row.get("lane") or "")
                for row in (portfolio.get("decisions") or [])
                if isinstance(row, dict) and row.get("run")
            ],
        }
    growth_ref = getattr(args, "c_supply_growth_status", DEFAULT_C_SUPPLY_GROWTH_STATUS)
    growth = _read_json(growth_ref)
    if growth:
        latest_metrics = growth.get("latest_metrics") if isinstance(growth.get("latest_metrics"), dict) else {}
        status["c_supply_growth_snapshot"] = {
            "path": growth_ref,
            "status": growth.get("status"),
            "current_stage": growth.get("current_stage"),
            "effective_target_credit_ready_rows": growth.get("effective_target_credit_ready_rows"),
            "credit_ready_count": latest_metrics.get("credit_ready_count"),
            "source_demand_family_count": latest_metrics.get("source_demand_family_count"),
            "probe_seedable_count": latest_metrics.get("probe_seedable_count"),
        }
    if extra:
        status.update(extra)
    p = Path(args.status_out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


def _enqueue_registry_refresh(args: argparse.Namespace) -> str:
    cx = work_queue.connect(args.queue_db)
    if _has_open_kind_work(cx, "registry_refresh"):
        return ""
    work_id = f"registry_refresh:{int(time.time())}"
    work_queue.enqueue(
        cx,
        kind="registry_refresh",
        priority=_queue_priority(args, "registry_refresh", 100),
        payload={"work_id": work_id, "reason": "24x7_control_refresh"},
        max_attempts=2,
    )
    work_queue.append_event(args.events, {
        "event_type": "work_enqueued",
        "work_id": work_id,
        "payload": {"kind": "registry_refresh", "source": "leanmill_24x7_runner"},
    })
    return work_id


def _enqueue_refresh(args: argparse.Namespace, *, kind: str, priority: int, reason: str) -> str:
    cx = work_queue.connect(args.queue_db)
    if _has_open_kind_work(cx, kind):
        return ""
    work_id = f"{kind}:{int(time.time())}"
    work_queue.enqueue(
        cx,
        kind=kind,
        priority=priority,
        payload={"work_id": work_id, "reason": reason},
        max_attempts=2,
    )
    work_queue.append_event(args.events, {
        "event_type": "work_enqueued",
        "work_id": work_id,
        "payload": {"kind": kind, "source": "leanmill_24x7_runner"},
    })
    return work_id


def _has_open_kind_work(cx: Any, kind: str) -> bool:
    row = cx.execute(
        """
        SELECT 1
        FROM work_items
        WHERE kind=? AND status IN ('queued', 'claimed', 'running')
        LIMIT 1
        """,
        (kind,),
    ).fetchone()
    return row is not None


def _has_recent_terminal_kind_work(cx: Any, kind: str, *, cooldown_s: int) -> bool:
    if cooldown_s <= 0:
        return False
    row = cx.execute(
        """
        SELECT 1
        FROM work_items
        WHERE kind=? AND status IN ('done', 'failed', 'retired', 'dead_letter') AND updated_at >= ?
        LIMIT 1
        """,
        (kind, int(time.time()) - int(cooldown_s)),
    ).fetchone()
    return row is not None


def _enqueue_source_plan_refresh(args: argparse.Namespace) -> str:
    cx = work_queue.connect(args.queue_db)
    kind = "residual_source_plan_refresh"
    if _has_open_kind_work(cx, kind) or _has_recent_terminal_kind_work(cx, kind, cooldown_s=args.source_plan_refresh_interval_s):
        return ""
    work_id = f"{kind}:{int(time.time())}"
    work_queue.enqueue(
        cx,
        kind=kind,
        priority=_queue_priority(args, "residual_source_plan_refresh", 90),
        payload={
            "work_id": work_id,
            "station": "residual_curriculum",
            "expected_exit": "fresh_residual_family_source_plan",
            "reason": "24x7_residual_source_plan_refresh",
        },
        max_attempts=2,
    )
    work_queue.append_event(args.events, {
        "event_type": "work_enqueued",
        "work_id": work_id,
        "payload": {"kind": kind, "source": "leanmill_24x7_runner"},
    })
    return work_id


def _queue_stats(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    return work_queue.stats(cx)


def _queue_open_stats(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    return work_queue.open_stats(cx)


def _external_source_scout_open_stats(args: argparse.Namespace) -> dict[str, int]:
    cx = work_queue.connect(args.queue_db)
    rows = cx.execute(
        """
        SELECT status, COUNT(*) n
        FROM work_items
        WHERE kind='source_scout_task'
          AND status IN ('queued', 'claimed', 'running')
          AND payload_json LIKE '%subscription_public_external%'
        GROUP BY status
        """
    ).fetchall()
    by_status = {str(row["status"]): int(row["n"]) for row in rows}
    total = sum(by_status.values())
    return {
        "queued": by_status.get("queued", 0),
        "claimed": by_status.get("claimed", 0),
        "running": by_status.get("running", 0),
        "total": total,
    }


def _policy_self_correction_actions(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, str):
        if not raw.strip():
            return {}
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for rec_class, action in raw.items():
        if isinstance(action, dict):
            out[str(rec_class)] = action
        elif isinstance(action, list):
            out[str(rec_class)] = {"actions": [a for a in action if isinstance(a, dict)]}
    return out


def _intelligence_recommendation_classes(path: str) -> list[str]:
    report = _read_json(path)
    classes: list[str] = []
    for item in report.get("recommendations") or []:
        if not isinstance(item, dict):
            continue
        rec_class = str(item.get("class") or "")
        if rec_class and rec_class not in classes:
            classes.append(rec_class)
    return classes


def _int_value(obj: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(obj.get(key) if obj.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return fallback


def _append_jsonl(path: str, row: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _self_correction_measurement(args: argparse.Namespace, *, label: str) -> dict[str, Any]:
    report = _read_json(args.factory_intelligence_out)
    open_queue = _queue_open_stats(args)
    flow = report.get("learning_unit_flow") if isinstance(report.get("learning_unit_flow"), dict) else {}
    proof_lane = report.get("proof_lane_rca") if isinstance(report.get("proof_lane_rca"), dict) else {}
    family_gate = report.get("family_spec_gate") if isinstance(report.get("family_spec_gate"), dict) else {}
    supply_quality = family_gate.get("supply_quality_summary") if isinstance(family_gate.get("supply_quality_summary"), dict) else {}
    scoreboard = flow.get("scoreboard_tail_counts") if isinstance(flow.get("scoreboard_tail_counts"), dict) else {}
    return {
        "schema": "leanmill-self-correction-measurement-v1",
        "label": label,
        "measured_at_epoch": int(time.time()),
        "factory_intelligence_ref": args.factory_intelligence_out,
        "queue_open_total": int(open_queue.get("total") or 0),
        "open_kind_counts": open_queue.get("by_kind") or {},
        "open_status_counts": open_queue.get("by_status") or {},
        "top_recommendations": [
            str(r.get("class") or "")
            for r in (report.get("recommendations") or [])[:8]
            if isinstance(r, dict)
        ],
        "verdict_status": str((report.get("verdict") or {}).get("status") or ""),
        "governed_value_tail_count": int((report.get("verdict") or {}).get("governed_value_tail_count") or 0),
        "unique_proof_value_exit_counts": flow.get("unique_proof_value_exit_counts") or {},
        "unique_tested_learning_exit_counts": flow.get("unique_tested_learning_exit_counts") or {},
        "scoreboard_tail_counts": {
            "ratified_closure_count": int(scoreboard.get("ratified_closure_count") or 0),
            "compile_candidate_count": int(scoreboard.get("compile_candidate_count") or 0),
            "exact_gap_candidate_count": int(scoreboard.get("exact_gap_candidate_count") or 0),
            "negative_control_unexpected_pass_count": int(scoreboard.get("negative_control_unexpected_pass_count") or 0),
            "negative_control_fail_count": int(scoreboard.get("negative_control_fail_count") or 0),
        },
        "proof_lane": {
            "bottleneck_class": proof_lane.get("bottleneck_class"),
            "blockers": proof_lane.get("blockers") or [],
            "family_spec_candidate_signature_diversity": proof_lane.get("family_spec_candidate_signature_diversity"),
            "lane_open": proof_lane.get("lane_open") or {},
            "lane_outcomes": proof_lane.get("lane_outcomes") or {},
            "scale_readiness": proof_lane.get("scale_readiness") or {},
        },
        "family_spec_supply_quality": {
            "family_count": supply_quality.get("family_count"),
            "class_counts": supply_quality.get("class_counts") or {},
            "gap_counts": supply_quality.get("gap_counts") or {},
            "median_generality_score": supply_quality.get("median_generality_score"),
            "weakest_families": (supply_quality.get("weakest_families") or [])[:8],
        },
    }


def _plan_summary(path: str) -> dict[str, Any]:
    obj = _read_json(path)
    if not obj:
        return {"available": False, "path": path}
    if obj.get("schema") == "leanmill-c-supply-batch-v1":
        selection = obj.get("selection") if isinstance(obj.get("selection"), dict) else {}
        freeze = obj.get("freeze") if isinstance(obj.get("freeze"), dict) else None
        freeze_creditable = bool(freeze) and str(freeze.get("status") or "frozen") == "frozen" and int(freeze.get("row_count") or 0) >= int(selection.get("selected_count") or 0) > 0
        return {
            "available": True,
            "path": path,
            "schema": obj.get("schema"),
            "status": obj.get("status"),
            "run_id": obj.get("run_id"),
            "corpus_count": int(obj.get("corpus_count") or 0),
            "selected_count": int(selection.get("selected_count") or 0),
            "eligible_count": int(selection.get("eligible_count") or 0),
            "freeze": freeze if freeze_creditable else None,
            "freeze_creditable": freeze_creditable,
            "proof_credit_granted": 0,
        }
    return {
        "available": True,
        "path": path,
        "job_count": int(obj.get("job_count") or 0),
        "bucket_counts": obj.get("bucket_counts") or {},
        "enqueued": int(obj.get("enqueued") or 0),
        "skip_counts": obj.get("skip_counts") or {},
        "anti_laundering_rule": obj.get("anti_laundering_rule"),
    }


def _self_correction_outcome(result: dict[str, Any], plan: dict[str, Any]) -> str:
    if int(result.get("returncode") or 0) != 0:
        return "dispatch_failed"
    if plan.get("schema") == "leanmill-c-supply-batch-v1":
        if plan.get("freeze"):
            return "c_discriminating_slice_frozen"
        if int(plan.get("selected_count") or 0) > 0:
            return "c_supply_candidates_mined_not_frozen"
        return "c_supply_no_candidates"
    if int(plan.get("enqueued") or 0) > 0:
        return "corrective_work_enqueued"
    skips = plan.get("skip_counts") if isinstance(plan.get("skip_counts"), dict) else {}
    if any(int(skips.get(k) or 0) for k in ("open_same_replenish_group", "recent_terminal_same_replenish_group", "open_same_probe_signature", "recent_terminal_same_probe_signature")):
        return "corrective_work_already_open_or_recent"
    if int(plan.get("job_count") or 0) == 0:
        return "no_correction_candidates"
    return "correction_plan_generated_no_enqueue"


def _queue_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_counts = before.get("open_kind_counts") if isinstance(before.get("open_kind_counts"), dict) else {}
    after_counts = after.get("open_kind_counts") if isinstance(after.get("open_kind_counts"), dict) else {}
    keys = sorted(set(before_counts) | set(after_counts))
    return {
        "queue_open_total_delta": int(after.get("queue_open_total") or 0) - int(before.get("queue_open_total") or 0),
        "open_kind_count_delta": {k: int(after_counts.get(k) or 0) - int(before_counts.get(k) or 0) for k in keys},
    }


def _append_self_correction_action_impact(
    args: argparse.Namespace,
    *,
    dispatch: dict[str, Any],
    result: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    contract = dispatch.get("action_contract") if isinstance(dispatch.get("action_contract"), dict) else {}
    plan = _plan_summary(str(dispatch.get("plan_out") or ""))
    outcome = _self_correction_outcome(result, plan)
    row = {
        "schema": "leanmill-self-correction-action-impact-v1",
        "action_id": str(contract.get("action_id") or f"self_correct:unknown:{int(time.time())}"),
        "action_ref": str(dispatch.get("plan_out") or ""),
        "actor": "leanmill_24x7_runner",
        "actor_role": "control_runner",
        "action_kind": "route_intelligence_recommendation",
        "decision_stage": "post_factory_intelligence",
        "objective_metric": str(dispatch.get("recommendation_class") or contract.get("objective_metric") or ""),
        "baseline_action": contract.get("baseline_action") or "record_recommendation_only",
        "counterfactual_action": contract.get("counterfactual_action") or "enqueue_bounded_corrective_work",
        "expected_effect": contract.get("expected_effect"),
        "observed_outcome": outcome,
        "impact_summary": (
            "bounded correction enqueued" if outcome == "corrective_work_enqueued" else
            "equivalent corrective work already open or recently completed" if outcome == "corrective_work_already_open_or_recent" else
            outcome
        ),
        "old_state": before,
        "new_state": after,
        "artifact_refs": [args.factory_intelligence_out, str(dispatch.get("plan_out") or "")],
        "evaluator_role": "deterministic_runner_receipt",
        "independence_boundary": "no proof credit; proof value still requires Proof Execution plus Governance Gate",
        "decision_changed_bool": outcome in {"corrective_work_enqueued", "corrective_work_already_open_or_recent"},
        "optimization_scope": "system",
        "status": "measured",
        "attribution_confidence": "low",
        "guardrail_metrics": {
            "proof_credit_granted": 0.0,
            "returncode": float(int(result.get("returncode") or 0)),
            "negative_control_unexpected_pass_count_before": float(((before.get("scoreboard_tail_counts") or {}).get("negative_control_unexpected_pass_count") or 0)),
            "negative_control_unexpected_pass_count_after": float(((after.get("scoreboard_tail_counts") or {}).get("negative_control_unexpected_pass_count") or 0)),
        },
        "measurement_ref": args.factory_intelligence_out,
        "metadata": {
            "plan_summary": plan,
            "queue_delta": _queue_delta(before, after),
            "result_returncode": result.get("returncode"),
            "self_correction_tool": dispatch.get("tool"),
            "delayed_metrics_to_check": [
                "family_spec_supply_quality.gap_counts",
                "family_spec_supply_quality.median_generality_score",
                "unique_proof_value_exit_counts",
                "scoreboard_tail_counts.negative_control_unexpected_pass_count",
            ],
        },
        "notes": "Immediate dispatch measurement only; delayed supply/proof effects are evaluated by later intelligence snapshots.",
    }
    _append_jsonl(args.self_correction_action_impact_ledger, row)
    work_queue.append_event(args.events, {
        "event_type": "leanmill_self_correction_action_impact",
        "work_id": row["action_id"],
        "payload": {
            "objective_metric": row["objective_metric"],
            "observed_outcome": row["observed_outcome"],
            "decision_changed_bool": row["decision_changed_bool"],
            "proof_credit_granted": 0,
        },
        "artifact_paths": [args.self_correction_action_impact_ledger, row["action_ref"]],
    })
    return row


def _append_multi_node_routing_args(cmd: list[str], args: argparse.Namespace) -> list[str]:
    routing = multi_node_routing_plan(path=args.factory_policy, profile_name=args.policy_profile)
    if routing.get("enabled"):
        cmd.extend(["--node-id", str(routing.get("node_id") or "")])
        cmd.extend(["--routing-nodes", str(routing.get("routing_nodes_arg") or "")])
    return cmd


def _learning_seed_self_correction_cmd(
    args: argparse.Namespace,
    *,
    rec_class: str,
    action: dict[str, Any],
    ordinal: int,
) -> list[str]:
    py = sys.executable
    run_id = _self_correction_run_id(rec_class, ordinal=ordinal)
    max_total = max(0, _int_value(action, "max_total_jobs", _int_value(action, "max_enqueued", 4)))
    max_enqueued = max(0, _int_value(action, "max_enqueued", max_total))
    out_path = str(action.get("out") or _default_self_correction_path(
        args.self_correction_seed_plan,
        rec_class=rec_class,
        ordinal=ordinal,
        label="seed_plan",
        run_id=run_id,
    ))
    if ordinal:
        stem = Path(out_path)
        out_path = str(stem.with_name(f"{stem.stem}.{ordinal}{stem.suffix or '.json'}"))
    cmd = [
        py,
        "scripts/public/control/leanmill/learning_work_seeder.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out_path,
        "--run-id", run_id,
        "--agent-runtime", str(action.get("agent_runtime") or args.agent_default_runtime),
        "--agent-max-wall-time-s", str(_int_value(action, "agent_max_wall_time_s", args.agent_max_wall_time_s)),
        "--agent-max-iterations", str(_int_value(action, "agent_max_iterations", args.agent_max_iterations)),
        "--max-total-jobs", str(max_total),
        "--max-enqueued", str(max_enqueued),
        "--max-probe-families", str(_int_value(action, "max_probe_families", 0)),
        "--max-family-spec-probe-families", str(_int_value(action, "max_family_spec_probe_families", 0)),
        "--max-family-spec-repair-jobs", str(_int_value(action, "max_family_spec_repair_jobs", 0)),
        "--max-family-spec-generality-jobs", str(_int_value(action, "max_family_spec_generality_jobs", 0)),
        "--max-proposal-jobs", str(_int_value(action, "max_proposal_jobs", 0)),
        "--max-agent-jobs", str(_int_value(action, "max_agent_jobs", 0)),
        "--terminal-family-cooldown-s", str(_int_value(action, "terminal_family_cooldown_s", 0)),
        "--terminal-proposal-family-cooldown-s", str(_int_value(action, "terminal_proposal_family_cooldown_s", args.learning_terminal_proposal_family_cooldown_s)),
        "--terminal-agent-family-cooldown-s", str(_int_value(action, "terminal_agent_family_cooldown_s", args.learning_terminal_agent_family_cooldown_s)),
        "--terminal-probe-signature-cooldown-s", str(_int_value(action, "terminal_probe_signature_cooldown_s", 0)),
        "--probe-command-timeout-s", str(args.probe_command_timeout_s),
        "--probe-command-timeout-overhead-s", str(args.probe_command_timeout_overhead_s),
        "--factory-policy", args.factory_policy,
        "--enqueue",
    ]
    seeder_policy_profile = str(action.get("seeder_policy_profile") or args.policy_profile or "")
    if seeder_policy_profile:
        cmd.extend(["--policy-profile", seeder_policy_profile])
    if bool(action.get("warm_repl_inline", False)) and args.allow_heavy_lean:
        cmd.append("--warm-repl-inline")
    if bool(action.get("govern_winners", False)) and args.allow_heavy_lean:
        cmd.append("--govern-winners")
    _append_multi_node_routing_args(cmd, args)
    return cmd




def _c_supply_batch_self_correction_cmd(
    args: argparse.Namespace,
    *,
    rec_class: str,
    action: dict[str, Any],
    ordinal: int,
) -> list[str]:
    py = sys.executable
    run_id = _self_correction_run_id(rec_class, ordinal=ordinal)
    if action.get("out"):
        out_path = str(action.get("out"))
    else:
        out_path = _default_self_correction_path(
            args.c_supply_batch_status,
            rec_class=rec_class,
            ordinal=ordinal,
            label="c_supply_batch",
            run_id=run_id,
        )
    if action.get("md"):
        md_path = str(action.get("md"))
    else:
        md_path = _default_self_correction_path(
            args.c_supply_batch_md,
            rec_class=rec_class,
            ordinal=ordinal,
            label="c_supply_batch",
            suffix=".md",
            run_id=run_id,
        )
    if ordinal:
        stem = Path(out_path)
        out_path = str(stem.with_name(f"{stem.stem}.{ordinal}{stem.suffix or '.json'}"))
        md_stem = Path(md_path)
        md_path = str(md_stem.with_name(f"{md_stem.stem}.{ordinal}{md_stem.suffix or '.md'}"))
    cmd = [
        py,
        "scripts/public/control/leanmill/c_supply_batch.py",
        "--factory-policy", args.factory_policy,
        "--out", out_path,
        "--md", md_path,
        "--run-id", run_id,
    ]
    budget_profile = str(action.get("budget_profile") or "")
    if budget_profile:
        cmd.extend(["--budget-profile", budget_profile])
    numeric_flags = {
        "max_corpora": "--max-corpora",
        "corpus_offset": "--corpus-offset",
        "max_new_rows_per_corpus": "--max-new-rows-per-corpus",
        "limit_per_corpus": "--limit-per-corpus",
        "min_signature_hits": "--min-signature-hits",
        "min_freeze_rows": "--min-freeze-rows",
        "max_tool_calls": "--max-tool-calls",
        "per_candidate_timeout_s": "--per-candidate-timeout-s",
        "wall_timeout_s": "--wall-timeout-s",
    }
    for key, flag in numeric_flags.items():
        if key in action:
            cmd.extend([flag, str(_int_value(action, key, 0))])
    if bool(action.get("source_demand_only", False)):
        cmd.append("--source-demand-only")
        cmd.extend(["--source-demand-selection", getattr(args, "c_supply_clean_selection", args.c_supply_batch_selection)])
    for pattern in action.get("corpus_globs") or []:
        cmd.extend(["--corpus-glob", str(pattern)])
    if bool(action.get("freeze_under_min_for_pilot", False)):
        cmd.append("--freeze-under-min-for-pilot")
    if bool(action.get("no_run", False)):
        cmd.append("--no-run")
    return cmd


def _c_supply_template_backfill_self_correction_cmd(
    args: argparse.Namespace,
    *,
    rec_class: str,
    action: dict[str, Any],
    ordinal: int,
) -> list[str]:
    py = sys.executable
    run_id = _self_correction_run_id(rec_class, ordinal=ordinal)
    out_path = str(action.get("out") or _default_self_correction_path(
        args.self_correction_seed_plan,
        rec_class=rec_class,
        ordinal=ordinal,
        label="template_backfill_plan",
        run_id=run_id,
    ))
    if ordinal:
        stem = Path(out_path)
        out_path = str(stem.with_name(f"{stem.stem}.{ordinal}{stem.suffix or '.json'}"))
    cmd = [
        py,
        "scripts/public/control/leanmill/c_supply_template_backfill.py",
        "--selection", args.c_supply_clean_selection,
        "--checkpoint", args.c_supply_clean_checkpoint,
        "--row-context", args.c_supply_clean_row_context,
        "--spec-dir", args.family_spec_dir,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out_path,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--run-id", run_id,
        "--max-jobs", str(_int_value(action, "max_jobs", _int_value(action, "max_enqueued", 4))),
        "--rows-per-family", str(_int_value(action, "rows_per_family", 2)),
        "--agent-runtime", str(action.get("agent_runtime") or args.agent_default_runtime),
        "--agent-max-wall-time-s", str(_int_value(action, "agent_max_wall_time_s", args.agent_max_wall_time_s)),
        "--agent-max-attempts", str(_int_value(action, "agent_max_attempts", 2)),
        "--agent-max-iterations", str(_int_value(action, "agent_max_iterations", args.agent_max_iterations)),
        "--max-enqueued", str(_int_value(action, "max_enqueued", _int_value(action, "max_jobs", 4))),
        "--cooldown-s", str(_int_value(action, "cooldown_s", 3600)),
        "--enqueue",
    ]
    if bool(action.get("include_all_candidate_families", True)):
        cmd.append("--include-all-candidate-families")
    else:
        cmd.append("--no-include-all-candidate-families")
    if bool(action.get("retry_existing", False)):
        cmd.append("--retry-existing")
    return cmd


def _c_supply_growth_controller_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/c_supply_growth_controller.py",
        "--selection", args.c_supply_clean_selection,
        "--checkpoint", args.c_supply_clean_checkpoint,
        "--row-context", args.c_supply_clean_row_context,
        "--spec-dir", args.family_spec_dir,
        "--registry", args.registry,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--work-dir", args.c_supply_growth_work_dir,
        "--out", args.c_supply_growth_status,
        "--worker-id", f"{args.worker_id}-c-supply-growth",
    ]
    if args.allow_heavy_lean:
        cmd.append("--allow-heavy-lean")
    return cmd


def _family_birth_miner_self_correction_cmd(
    args: argparse.Namespace,
    *,
    rec_class: str,
    action: dict[str, Any],
    ordinal: int,
) -> list[str]:
    py = sys.executable
    run_id = _self_correction_run_id(rec_class, ordinal=ordinal)
    out_path = str(action.get("out") or _default_self_correction_path(
        args.family_birth_plan,
        rec_class=rec_class,
        ordinal=ordinal,
        label="family_birth",
        run_id=run_id,
    ))
    md_path = str(action.get("md") or _default_self_correction_path(
        args.family_birth_plan_md,
        rec_class=rec_class,
        ordinal=ordinal,
        label="family_birth",
        suffix=".md",
        run_id=run_id,
    ))
    if ordinal:
        out_stem = Path(out_path)
        md_stem = Path(md_path)
        out_path = str(out_stem.with_name(f"{out_stem.stem}.{ordinal}{out_stem.suffix or '.json'}"))
        md_path = str(md_stem.with_name(f"{md_stem.stem}.{ordinal}{md_stem.suffix or '.md'}"))
    cmd = [
        py,
        "scripts/public/control/leanmill/family_birth_miner.py",
        "--selection", args.c_supply_batch_selection,
        "--checkpoint", args.c_supply_batch_checkpoint,
        "--row-context", args.c_supply_batch_row_context,
        "--spec-dir", args.family_spec_dir,
        "--out", out_path,
        "--md", md_path,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--run-id", run_id,
        "--existing-family-confidence-floor", str(float(action.get("existing_family_confidence_floor", 0.75))),
        "--existing-family-hit-floor", str(_int_value(action, "existing_family_hit_floor", 3)),
        "--min-rows", str(_int_value(action, "min_rows", 3)),
        "--min-shared-tokens", str(_int_value(action, "min_shared_tokens", 2)),
        "--max-clusters", str(_int_value(action, "max_clusters", 20)),
        "--max-enqueued", str(_int_value(action, "max_enqueued", 0)),
        "--agent-runtime", str(action.get("agent_runtime") or args.agent_default_runtime),
        "--agent-max-wall-time-s", str(_int_value(action, "agent_max_wall_time_s", args.agent_max_wall_time_s)),
        "--agent-max-iterations", str(_int_value(action, "agent_max_iterations", args.agent_max_iterations)),
    ]
    if bool(action.get("include_covered_static_failures", False)):
        cmd.append("--include-covered-static-failures")
    else:
        cmd.append("--no-include-covered-static-failures")
    if bool(action.get("exclude_existing_family_tokens", True)):
        cmd.append("--exclude-existing-family-tokens")
    else:
        cmd.append("--no-exclude-existing-family-tokens")
    if bool(action.get("enqueue", False)):
        cmd.append("--enqueue")
    return cmd


def _agentic_handoff_repair_self_correction_cmd(
    args: argparse.Namespace,
    *,
    rec_class: str,
    action: dict[str, Any],
    ordinal: int,
) -> list[str]:
    run_id = _self_correction_run_id(rec_class, ordinal=ordinal)
    out_path = str(action.get("out") or _default_self_correction_path(
        args.self_correction_seed_plan,
        rec_class=rec_class,
        ordinal=ordinal,
        label="handoff_repair",
        run_id=run_id,
    ))
    if ordinal:
        stem = Path(out_path)
        out_path = str(stem.with_name(f"{stem.stem}.{ordinal}{stem.suffix or '.json'}"))
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/agentic_handoff_repair.py",
        "--intelligence", args.factory_intelligence_out,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--spec-dir", args.family_spec_dir,
        "--row-context", args.c_supply_clean_row_context,
        "--out", out_path,
        "--max-repairs", str(_int_value(action, "max_repairs", 4)),
        "--max-total-jobs", str(_int_value(action, "max_total_jobs", 16)),
        "--max-enqueued", str(_int_value(action, "max_enqueued", 16)),
        "--max-tests-per-probe", str(_int_value(action, "max_tests_per_probe", 4)),
        "--family-spec-probe-rows-per-work-item", str(_int_value(action, "family_spec_probe_rows_per_work_item", 1)),
        "--command-timeout-s", str(_int_value(action, "command_timeout_s", args.command_timeout_s)),
    ]
    if bool(action.get("enqueue", True)):
        cmd.append("--enqueue")
    return cmd


def _run_intelligence_self_correction(
    args: argparse.Namespace,
    commands: list[dict[str, Any]],
    *,
    phase: str = "post_factory_intelligence",
    early_only: bool = False,
    max_actions_override: int | None = None,
) -> dict[str, Any]:
    if not bool(getattr(args, "self_correct_from_intelligence", False)):
        return {"enabled": False, "reason": "disabled"}
    actions_by_class = _policy_self_correction_actions(getattr(args, "self_correction_actions", {}))
    if not actions_by_class:
        return {"enabled": True, "matched": [], "dispatched": [], "skipped": ["no_policy_actions"]}
    rec_classes = _intelligence_recommendation_classes(args.factory_intelligence_out)
    before_measurement = _self_correction_measurement(args, label=f"before_{phase}_self_correction_dispatch")
    dispatched: list[dict[str, Any]] = []
    measured_impacts: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    max_actions_raw = max_actions_override if max_actions_override is not None else getattr(args, "self_correction_max_actions_per_cycle", 0)
    max_actions = max(0, int(max_actions_raw or 0))
    for rec_class in rec_classes:
        if max_actions and len(dispatched) >= max_actions:
            break
        action_spec = actions_by_class.get(rec_class)
        if not action_spec:
            continue
        actions = action_spec.get("actions") if isinstance(action_spec.get("actions"), list) else [action_spec]
        for action in [a for a in actions if isinstance(a, dict)]:
            if max_actions and len(dispatched) >= max_actions:
                break
            tool = str(action.get("tool") or "learning_work_seeder")
            if early_only and not bool(action.get("early_dispatch", False)):
                skipped.append({"recommendation_class": rec_class, "reason": "not_marked_for_early_dispatch", "tool": tool})
                continue
            if not bool(action.get("enabled", True)):
                skipped.append({"recommendation_class": rec_class, "reason": "action_disabled", "tool": tool})
                continue
            if tool not in {"learning_work_seeder", "c_supply_batch", "c_supply_template_backfill", "family_birth_miner", "agentic_handoff_repair"}:
                skipped.append({"recommendation_class": rec_class, "reason": "unsupported_tool", "tool": tool})
                continue
            if tool == "c_supply_batch":
                cmd = _c_supply_batch_self_correction_cmd(args, rec_class=rec_class, action=action, ordinal=len(dispatched))
            elif tool == "c_supply_template_backfill":
                cmd = _c_supply_template_backfill_self_correction_cmd(args, rec_class=rec_class, action=action, ordinal=len(dispatched))
            elif tool == "family_birth_miner":
                cmd = _family_birth_miner_self_correction_cmd(args, rec_class=rec_class, action=action, ordinal=len(dispatched))
            elif tool == "agentic_handoff_repair":
                cmd = _agentic_handoff_repair_self_correction_cmd(args, rec_class=rec_class, action=action, ordinal=len(dispatched))
            else:
                cmd = _learning_seed_self_correction_cmd(args, rec_class=rec_class, action=action, ordinal=len(dispatched))
            plan_out = next((cmd[i + 1] for i, part in enumerate(cmd[:-1]) if part == "--out"), "")
            counterfactual = (
                "mine_and_freeze_bounded_c_discriminating_supply"
                if tool == "c_supply_batch"
                else "backfill_family_spec_templates_from_strict_c_supply_candidates"
                if tool == "c_supply_template_backfill"
                else "mine_unmatched_static_failures_into_family_birth_candidates"
                if tool == "family_birth_miner"
                else "repair_agentic_handoff_debt"
                if tool == "agentic_handoff_repair"
                else "enqueue_bounded_corrective_work"
            )
            action_contract = {
                "schema": "leanmill-self-correction-action-contract-v1",
                "action_id": f"self_correct:{rec_class}:{int(time.time())}:{len(dispatched)}",
                "actor": "leanmill_24x7_runner",
                "actor_role": "control_runner",
                "action_kind": "route_intelligence_recommendation",
                "decision_stage": phase,
                "objective_metric": rec_class,
                "baseline_action": "record_recommendation_only",
                "counterfactual_action": counterfactual,
                "expected_effect": str(action.get("expected_effect") or "reduce the typed bottleneck without granting proof credit"),
                "artifact_refs": [args.factory_intelligence_out, plan_out],
                "optimization_scope": "system",
                "attribution_confidence": "low",
                "status": "planned",
                "measurement_ref": args.factory_intelligence_out,
                "guardrail_metrics": {
                    "max_total_jobs": float(_int_value(action, "max_total_jobs", _int_value(action, "max_enqueued", 4))),
                    "max_enqueued": float(_int_value(action, "max_enqueued", _int_value(action, "max_total_jobs", 4))),
                    "max_corpora": float(_int_value(action, "max_corpora", 0)),
                    "source_demand_only": 1.0 if bool(action.get("source_demand_only", False)) else 0.0,
                    "family_birth_enqueue": 1.0 if bool(action.get("enqueue", False)) else 0.0,
                    "min_freeze_rows": float(_int_value(action, "min_freeze_rows", 0)),
                    "proof_credit_granted": 0.0,
                    "seeder_profile_override_enabled": 1.0 if str(action.get("seeder_policy_profile") or "") else 0.0,
                },
                "notes": "Corrective work must earn value through the existing proof execution and governance gates.",
            }
            _write_progress_status(args, stage=f"self_correction:{phase}:{rec_class}:{tool}", extra={
                "phase": phase,
                "recommendation_class": rec_class,
                "tool": tool,
                "plan_out": plan_out,
                "early_only": early_only,
            })
            result = _run(cmd, timeout_s=args.command_timeout_s)
            result["self_correction"] = {
                "recommendation_class": rec_class,
                "tool": tool,
                "phase": phase,
                "action_contract": action_contract,
            }
            commands.append(result)
            dispatch = {
                "recommendation_class": rec_class,
                "tool": tool,
                "phase": phase,
                "returncode": result.get("returncode"),
                "plan_out": plan_out,
                "action_contract": action_contract,
            }
            after_measurement = _self_correction_measurement(args, label=f"after_{phase}_self_correction_dispatch")
            impact = _append_self_correction_action_impact(
                args,
                dispatch=dispatch,
                result=result,
                before=before_measurement,
                after=after_measurement,
            )
            dispatch["action_impact_ref"] = args.self_correction_action_impact_ledger
            dispatch["observed_outcome"] = impact.get("observed_outcome")
            dispatch["decision_changed_bool"] = impact.get("decision_changed_bool")
            dispatched.append(dispatch)
            measured_impacts.append({
                "action_id": impact.get("action_id"),
                "objective_metric": impact.get("objective_metric"),
                "observed_outcome": impact.get("observed_outcome"),
                "decision_changed_bool": impact.get("decision_changed_bool"),
                "plan_out": plan_out,
            })
    receipt = {
        "enabled": True,
        "phase": phase,
        "early_only": early_only,
        "recommendation_classes": rec_classes,
        "matched": [c for c in rec_classes if c in actions_by_class],
        "dispatched": dispatched,
        "measured_impacts": measured_impacts,
        "action_impact_ledger": args.self_correction_action_impact_ledger,
        "skipped": skipped,
    }
    return receipt


def cycle(args: argparse.Namespace) -> dict[str, Any]:
    cycle_started_at = int(time.time())
    py = sys.executable
    commands: list[dict[str, Any]] = []
    cx0 = work_queue.connect(args.queue_db)
    work_queue.record_worker_heartbeat(
        cx0,
        worker_id=args.worker_id,
        worker_kind="control_runner",
        policy_profile=args.policy_profile,
        payload={"policy_profile": args.policy_profile},
    )
    andon = _read_json(args.andon_cord)
    andon_active = bool(andon.get("active"))
    andon_containment = andon.get("containment") or {}
    effective_probe_signature_cooldown_s = int(args.replenisher_terminal_probe_signature_cooldown_s)
    effective_learning_probe_signature_cooldown_s = 6 * 60 * 60
    effective_learning_family_cooldown_s = (
        0
        if andon_active and bool(andon_containment.get("reset_proof_value_family_cooldown_s"))
        else 3600
    )
    effective_replenisher_family_cooldown_s = (
        0
        if andon_active and bool(andon_containment.get("reset_proof_value_family_cooldown_s"))
        else int(args.replenisher_terminal_family_cooldown_s)
    )
    pause_external_source_scouts = andon_active and bool(andon_containment.get("pause_external_source_scouts"))
    pause_source_binding_ingest = andon_active and bool(andon_containment.get("pause_source_binding_ingest"))
    pause_source_binding_probes = andon_active and bool(andon_containment.get("pause_source_binding_probes"))
    _write_progress_status(args, stage="cycle_started", extra={
        "heavy_lean_allowed": bool(args.allow_heavy_lean),
        "paid_llm_enabled": bool(args.allow_paid_llm),
        "subscription_agent_launch_enabled": bool(args.allow_agent_launch),
        "andon_active": andon_active,
        "andon_containment": andon_containment,
    })

    preflight_self_correction = {"enabled": False, "reason": "policy_disabled"}
    if _profile_runner_bool(args, "run_preflight_self_correction_from_last_intelligence", False):
        preflight_self_correction = _run_intelligence_self_correction(
            args,
            commands,
            phase="preflight_last_intelligence",
            early_only=True,
            max_actions_override=_profile_runner_int(args, "self_correction_preflight_max_actions_per_cycle", 1),
        )
    _write_progress_status(args, stage="preflight_complete", extra={
        "preflight_self_correction": preflight_self_correction,
    })

    # Ensure queue schema exists.
    cx0.close()

    governance_sentinel = {"enabled": False, "status": "disabled", "path": args.governance_sentinel_out}
    if args.run_governance_sentinel:
        sentinel_result = _run([
            py,
            "scripts/public/control/leanmill/governance_sentinel_suite.py",
            "--out", args.governance_sentinel_out,
        ], timeout_s=args.command_timeout_s)
        commands.append(sentinel_result)
        sentinel_payload = _read_json(args.governance_sentinel_out)
        if not sentinel_payload:
            sentinel_payload = _json_from_stdout_tail(str(sentinel_result.get("stdout_tail") or ""))
        governance_sentinel = {
            "enabled": True,
            "path": args.governance_sentinel_out,
            "returncode": sentinel_result.get("returncode"),
            "status": str(sentinel_payload.get("status") or "unknown"),
            "liveness": sentinel_payload.get("liveness") or {},
            "case_count": int(sentinel_payload.get("case_count") or 0),
        }
    governance_sentinel_ok = not args.run_governance_sentinel or governance_sentinel.get("status") == "pass"

    pre_growth_agentic_portfolio = {
        "cmd": ["<python>", "scripts/public/control/leanmill/agentic_portfolio_controller.py"],
        "returncode": 0,
        "skipped": True,
        "reason": "policy_disabled_or_not_started",
        "portfolio_phase": "pre_growth_last_intelligence",
    }
    _write_progress_status(args, stage="phase:agentic_portfolio_pre_growth:started")
    if _profile_runner_bool(args, "run_preflight_agentic_portfolio_from_last_intelligence", False) and governance_sentinel_ok:
        pre_growth_agentic_portfolio = _run_agentic_portfolio_controller(args, phase="pre_growth_last_intelligence")
    elif _profile_runner_bool(args, "run_preflight_agentic_portfolio_from_last_intelligence", False):
        pre_growth_agentic_portfolio = {
            "cmd": ["<python>", "scripts/public/control/leanmill/agentic_portfolio_controller.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "portfolio_phase": "pre_growth_last_intelligence",
            "governance_sentinel": governance_sentinel,
        }
    _write_progress_status(args, stage="phase:agentic_portfolio_pre_growth:finished", extra={
        "returncode": pre_growth_agentic_portfolio.get("returncode"),
        "timed_out": bool(pre_growth_agentic_portfolio.get("timed_out")),
    })
    commands.append(pre_growth_agentic_portfolio)

    if args.expand_corpus_from_files:
        _write_progress_status(args, stage="phase:expand_corpus_from_files:started")
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/corpus_expansion_from_files.py",
            "--source-dir", args.expand_corpus_source_dir,
            "--out", args.expand_corpus_out,
        ], timeout_s=args.command_timeout_s))
        _write_progress_status(args, stage="phase:expand_corpus_from_files:finished")

    enqueued_refresh = ""
    if args.refresh_first:
        _write_progress_status(args, stage="phase:refresh_first:started")
        enqueued_refresh = _enqueue_registry_refresh(args)
        enqueued_source_refresh = _enqueue_refresh(args, kind="source_inventory_refresh", priority=_queue_priority(args, "source_inventory_refresh", 80), reason="24x7_source_inventory_refresh")
        enqueued_canary_refresh = _enqueue_refresh(args, kind="canary_validation_refresh", priority=_queue_priority(args, "canary_validation_refresh", 70), reason="24x7_canary_shape_refresh")
        enqueued_governance_refresh = _enqueue_refresh(args, kind="governance_refresh", priority=_queue_priority(args, "governance_refresh", 60), reason="24x7_governance_control_refresh")
        enqueued_source_plan_refresh = _enqueue_source_plan_refresh(args)
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/registry_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", args.worker_id,
            "--registry", args.registry,
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/source_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-source",
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/canary_validator_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-canary",
            "--registry", args.registry,
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/governance_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-governance",
            "--registry", args.registry,
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/source_plan_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-source-plan",
            "--source-plan", args.source_plan,
            "--source-plan-md", args.source_plan_md,
            "--canary-packets", args.canary_packets,
            "--contract", args.contract,
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/source_search_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-source-search",
        ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/source_search_integrator.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-source-search-integrator",
            "--out-dir", args.source_search_integrations,
            "--agent-runtime", args.agent_default_runtime,
        ], timeout_s=args.command_timeout_s))
        _write_progress_status(args, stage="phase:refresh_first:finished")

    commands.append(_run([
        py,
        "scripts/public/control/leanmill/station_scheduler.py",
        "--contract", args.contract,
        "--out", args.scheduler_plan,
        "--enqueue",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--limit", str(args.enqueue_limit),
    ], timeout_s=args.command_timeout_s))

    if args.seed_learning_work and governance_sentinel_ok:
        seed_cmd = [
            py,
            "scripts/public/control/leanmill/learning_work_seeder.py",
            "--out", args.learning_seed_plan,
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--max-total-jobs", str(args.learning_max_total_jobs),
            "--max-probe-families", str(args.learning_max_probe_families),
            "--max-family-spec-probe-families", str(args.learning_max_family_spec_probe_families),
            "--max-proposal-jobs", str(args.learning_max_proposal_jobs),
            "--max-agent-jobs", str(args.learning_max_agent_jobs),
            "--agent-runtime", args.agent_default_runtime,
            "--terminal-family-cooldown-s", str(effective_learning_family_cooldown_s),
            "--terminal-proposal-family-cooldown-s", str(args.learning_terminal_proposal_family_cooldown_s),
            "--terminal-agent-family-cooldown-s", str(args.learning_terminal_agent_family_cooldown_s),
            "--terminal-probe-signature-cooldown-s", str(effective_learning_probe_signature_cooldown_s),
            "--probe-command-timeout-s", str(args.probe_command_timeout_s),
            "--probe-command-timeout-overhead-s", str(args.probe_command_timeout_overhead_s),
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--enqueue",
        ]
        _append_multi_node_routing_args(seed_cmd, args)
        if args.allow_heavy_lean:
            seed_cmd.append("--warm-repl-inline")
            seed_cmd.append("--govern-winners")
        commands.append(_run(seed_cmd, timeout_s=args.command_timeout_s))
    elif args.seed_learning_work:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/learning_work_seeder.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        })

    external_source_scout_open = _external_source_scout_open_stats(args)
    external_source_scout_target = 0 if pause_external_source_scouts else max(0, int(args.external_source_scout_floor))
    external_source_scout_needed = max(0, external_source_scout_target - int(external_source_scout_open.get("total", 0)))
    if args.seed_external_source_scouts and external_source_scout_needed > 0 and not pause_external_source_scouts and governance_sentinel_ok:
        max_external_scout_enqueued = max(
            0,
            min(int(args.external_source_scout_max_enqueued), external_source_scout_needed),
        )
        external_scout_cmd = [
            py,
            "scripts/public/control/leanmill/external_source_scout_seeder.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.external_source_scout_seed_plan,
            "--run-id", f"cycle_{int(time.time())}",
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--max-enqueued", str(max_external_scout_enqueued),
            "--enqueue",
        ]
        commands.append(_run(external_scout_cmd, timeout_s=args.command_timeout_s))
    elif args.seed_external_source_scouts:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/external_source_scout_seeder.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass" if not governance_sentinel_ok else ("andon_pause_external_source_scouts" if pause_external_source_scouts else "external_source_scout_floor_satisfied"),
            "external_source_scout_open": external_source_scout_open,
            "external_source_scout_floor": external_source_scout_target,
            "andon_active": andon_active,
        })

    if args.scout_heldouts and governance_sentinel_ok:
        scout_cmd = [
            py,
            "scripts/public/control/leanmill/heldout_independence_scout.py",
            "--registry", args.registry,
            "--out", args.heldout_scout,
            "--md", args.heldout_scout_md,
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--max-candidates-per-family", str(args.heldout_scout_max_candidates_per_family),
            "--max-enqueued-tasks", str(args.heldout_scout_max_enqueued_tasks),
            "--run-id", f"cycle_{int(time.time())}",
            "--enqueue-gm-tasks",
        ]
        if args.heldout_scout_include_seed_families:
            scout_cmd.append("--include-seed-families")
        commands.append(_run(scout_cmd, timeout_s=args.command_timeout_s))
    elif args.scout_heldouts:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/heldout_independence_scout.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        })

    if args.promote_heldouts and governance_sentinel_ok:
        promotion_cmd = [
            py,
            "scripts/public/control/leanmill/heldout_promotion_worker.py",
            "--scout", args.heldout_scout,
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.heldout_promotion,
            "--md", args.heldout_promotion_md,
            "--run-id", f"cycle_{int(time.time())}",
            "--agent-runtime", args.agent_default_runtime,
            "--agent-max-wall-time-s", str(args.agent_max_wall_time_s),
            "--agent-max-iterations", str(args.agent_max_iterations),
            "--max-enqueued", str(args.heldout_promotion_max_enqueued),
        ]
        if args.allow_heavy_lean:
            promotion_cmd.append("--govern-winners")
        commands.append(_run(promotion_cmd, timeout_s=args.command_timeout_s))
    elif args.promote_heldouts:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/heldout_promotion_worker.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        })

    if andon_active and bool(andon_containment.get("auto_drain_gm_operator")):
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/gm_operator_lane.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", f"{DEFAULT_DATA_DIR}/gm_operator_auto_drain.json",
            "--worker-id", f"{args.worker_id}-gm-auto",
            "--max-tasks", str(int(andon_containment.get("max_gm_auto_drain_tasks") or 4)),
            "--auto",
        ], timeout_s=args.command_timeout_s))

    if args.ingest_agent_outputs:
        if args.recover_external_source_search:
            commands.append(_run([
                py,
                "scripts/public/control/leanmill/external_source_search_recovery.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--out", args.external_source_search_recovery_status,
                "--limit", str(args.recover_external_source_search_limit),
            ], timeout_s=args.command_timeout_s))
        if args.recover_rejected_source_bindings:
            recover_bindings_result = _run([
                py,
                "scripts/public/control/leanmill/source_search_integrator.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--out-dir", args.source_search_integrations,
                "--recover-rejected-bindings",
                "--max-recover", str(args.recover_rejected_bindings_limit),
                "--recovery-status-out", args.recover_rejected_bindings_status,
            ], timeout_s=args.command_timeout_s)
            commands.append(recover_bindings_result)
            recover_bindings_payload = _read_json(args.recover_rejected_bindings_status)
            if not recover_bindings_payload:
                recover_bindings_payload = _json_from_stdout_tail(str(recover_bindings_result.get("stdout_tail") or ""))
            if not recover_bindings_payload:
                recover_bindings_payload = {"parse_error": True, "stdout_tail": recover_bindings_result.get("stdout_tail")}
                Path(args.recover_rejected_bindings_status).parent.mkdir(parents=True, exist_ok=True)
                Path(args.recover_rejected_bindings_status).write_text(json.dumps(recover_bindings_payload, indent=2, sort_keys=True) + "\n")
        if pause_source_binding_ingest:
            commands.append({
                "cmd": ["<python>", "scripts/public/control/leanmill/source_binding_ingester.py"],
                "returncode": 0,
                "skipped": True,
                "reason": "andon_pause_source_binding_ingest",
                "andon_active": andon_active,
                "andon_containment": andon_containment,
            })
        else:
            commands.append(_run([
                py,
                "scripts/public/control/leanmill/source_binding_ingester.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--out", args.source_binding_ingestion_status,
                "--allocator", args.source_family_allocator,
                "--max-ingest", str(args.source_binding_max_ingest),
                "--factory-policy", args.factory_policy,
            ], timeout_s=args.command_timeout_s))
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/agent_output_ingester.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.agent_output_ingestion_status,
            "--max-ingest", str(args.agent_output_max_ingest),
        ], timeout_s=args.command_timeout_s))

    if args.triage_dead_letters:
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/dead_letter_triage.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.dead_letter_triage_status,
            "--limit", str(args.dead_letter_triage_limit),
            "--max-requeues", str(args.dead_letter_triage_max_requeues),
            "--max-attempts", str(args.dead_letter_triage_max_attempts),
            "--enqueue",
        ], timeout_s=args.command_timeout_s))

    if args.recover_retryable_failures:
        retryable_since = int(args.recover_retryable_since_epoch)
        if retryable_since <= 0:
            retryable_since = int(time.time()) - int(args.recover_retryable_lookback_s)
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/retryable_failure_recovery.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.retryable_failure_recovery_status,
            "--since-epoch", str(retryable_since),
            "--limit", str(args.retryable_failure_recovery_limit),
            "--max-requeues", str(args.retryable_failure_recovery_max_requeues),
            "--max-attempts", str(args.retryable_failure_recovery_max_attempts),
            "--enqueue",
        ], timeout_s=args.command_timeout_s))

    if args.triage_post_probes:
        commands.append(_run([
            py,
            "scripts/public/control/leanmill/post_probe_triage.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.post_probe_triage_status,
            "--agent-runtime", args.agent_default_runtime,
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--limit", str(args.post_probe_triage_limit),
            "--max-enqueued", str(args.post_probe_triage_max_enqueued),
            "--enqueue",
            "--mark",
        ], timeout_s=args.command_timeout_s))

    if args.recover_pruned_source_requests:
        recover_since = int(args.recover_pruned_since_epoch)
        if recover_since <= 0:
            recover_since = int(time.time()) - int(args.recover_pruned_lookback_s)
        recover_result = _run([
            py,
            "scripts/public/control/leanmill/recover_pruned_source_requests.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--since-epoch", str(recover_since),
            "--limit", str(args.recover_pruned_limit),
            "--priority", str(args.recover_pruned_priority),
        ], timeout_s=args.command_timeout_s)
        commands.append(recover_result)
        recover_payload = _json_from_stdout_tail(str(recover_result.get("stdout_tail") or ""))
        if not recover_payload:
            recover_payload = {"parse_error": True, "stdout_tail": recover_result.get("stdout_tail")}
        Path(args.recover_pruned_source_requests_status).parent.mkdir(parents=True, exist_ok=True)
        Path(args.recover_pruned_source_requests_status).write_text(json.dumps(recover_payload, indent=2, sort_keys=True) + "\n")

    if args.replenish_backlog and governance_sentinel_ok:
        replenish_cmd = [
            py,
            "scripts/public/control/leanmill/backlog_replenisher.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", args.backlog_replenisher_status,
            "--learning-seed-plan", args.learning_seed_plan,
            "--proposal-floor", str(args.proposal_floor),
            "--agent-floor", str(args.agent_floor),
            "--probe-floor", str(args.probe_floor),
            "--family-spec-probe-floor", str(args.family_spec_probe_floor),
            "--source-shape-probe-floor", str(args.source_shape_probe_floor),
            "--agent-runtime", args.agent_default_runtime,
            "--terminal-family-cooldown-s", str(effective_replenisher_family_cooldown_s),
            "--terminal-proposal-family-cooldown-s", str(args.replenisher_terminal_proposal_family_cooldown_s),
            "--terminal-agent-family-cooldown-s", str(args.replenisher_terminal_agent_family_cooldown_s),
            "--terminal-probe-signature-cooldown-s", str(effective_probe_signature_cooldown_s),
            "--probe-command-timeout-s", str(args.probe_command_timeout_s),
            "--probe-command-timeout-overhead-s", str(args.probe_command_timeout_overhead_s),
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--command-timeout-s", str(args.command_timeout_s),
        ]
        if args.allow_heavy_lean:
            replenish_cmd.extend(["--allow-probe-seed", "--warm-repl-inline", "--govern-winners"])
        commands.append(_run(replenish_cmd, timeout_s=args.command_timeout_s))
    elif args.replenish_backlog:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/backlog_replenisher.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        })

    registry_worker_runs = 0
    for _ in range(max(0, args.registry_worker_passes)):
        result = _run([
            py,
            "scripts/public/control/leanmill/registry_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", args.worker_id,
            "--registry", args.registry,
        ], timeout_s=args.command_timeout_s)
        commands.append(result)
        registry_worker_runs += 1
        payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
        if not payload.get("claimed"):
            break

    for _ in range(max(0, args.llm_worker_passes)):
        cmd = [
            py,
            "scripts/public/control/leanmill/llm_proposal_worker.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-llm-proposal",
            "--max-total-cost-usd", str(args.llm_max_total_cost_usd),
            "--model-family", args.llm_model_family,
            "--session-id", args.llm_session_id,
        ]
        if args.allow_paid_llm:
            cmd.append("--allow-paid-llm")
        if args.allow_llm_codex_cli_fallback:
            cmd.extend([
                "--allow-codex-cli-fallback",
                "--codex-cli-fallback-model", args.llm_codex_cli_fallback_model,
                "--codex-cli-fallback-timeout-s", str(args.llm_codex_cli_fallback_timeout_s),
            ])
        result = _run(cmd, timeout_s=args.command_timeout_s)
        commands.append(result)
        payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
        if not payload.get("claimed"):
            break

    heavy_lean_launched = False
    source_binding_probe_runs = 0
    source_binding_probe_passes = _source_binding_probe_worker_passes(args)
    lane_order, unknown_lanes, default_appended_lanes = _lane_execution_order(args)
    lane_execution = {
        "order": lane_order,
        "unknown": unknown_lanes,
        "default_appended": default_appended_lanes,
        "enabled": _profile_runner_bool(args, "runner_drain_lanes", True),
        "rule": "Lane order is profile policy. Missing known lanes are appended disabled-by-count; unknown names are reported and ignored.",
    }

    def _run_source_review_lane(*, suffix: str = "") -> None:
        worker_suffix = f"-source-review{suffix}" if suffix else "-source-review"
        for _ in range(_source_review_worker_passes(args)):
            result = _run([
                py,
                "scripts/public/control/leanmill/source_review_worker.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}{worker_suffix}",
                "--factory-policy", args.factory_policy,
                "--policy-profile", args.policy_profile,
            ], timeout_s=args.command_timeout_s)
            commands.append(result)
            payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
            if not payload.get("claimed"):
                break

    def _run_agent_repair_lane() -> None:
        for _ in range(max(0, args.agent_worker_passes)):
            cmd = [
                py,
                "scripts/public/control/leanmill/agent_repair_worker.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}-agent-repair",
                "--claim-kind", "agent_repair_task",
                "--default-runtime", args.agent_default_runtime,
                "--default-codex-model", args.agent_default_codex_model,
                "--family-spec-patch-codex-model", args.agent_family_spec_patch_codex_model,
                "--max-wall-time-s", str(args.agent_max_wall_time_s),
                "--max-iterations", str(args.agent_max_iterations),
            ]
            agent_claim_modes = _csv_values(getattr(args, "agent_worker_claim_patch_modes", ""))
            for mode in agent_claim_modes:
                cmd.extend(["--claim-patch-mode", mode])
            if "c_supply_template_backfill" in set(agent_claim_modes):
                cmd.extend(["--claim-payload-eq", f"c_supply_selection={args.c_supply_clean_selection}"])
            if args.allow_agent_launch:
                cmd.append("--allow-agent-launch")
            result = _run(cmd, timeout_s=max(args.command_timeout_s, args.agent_max_wall_time_s + 60))
            commands.append(result)
            payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
            if not payload.get("claimed"):
                break

    def _run_source_scout_lane() -> None:
        for _ in range(_source_agent_workers(args)):
            result = _run([
                py,
                "scripts/public/control/leanmill/source_scout_worker.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}-source-scout",
                "--factory-policy", args.factory_policy,
                "--policy-profile", args.policy_profile,
            ], timeout_s=args.command_timeout_s)
            commands.append(result)
            payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
            if not payload.get("claimed"):
                break

        if args.ingest_agent_outputs and _source_agent_workers(args) > 0:
            commands.append(_run([
                py,
                "scripts/public/control/leanmill/agent_output_ingester.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--out", args.agent_output_ingestion_status,
                "--max-ingest", str(args.agent_output_max_ingest),
                "--factory-policy", args.factory_policy,
            ], timeout_s=args.command_timeout_s))
            _run_source_review_lane(suffix="-post-source")

    def _run_source_search_lane() -> None:
        for _ in range(max(0, args.source_search_worker_passes)):
            result = _run([
                py,
                "scripts/public/control/leanmill/source_search_worker.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}-source-search",
            ], timeout_s=args.command_timeout_s)
            commands.append(result)
            payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
            if not payload.get("claimed"):
                break

    def _run_source_search_integrator_lane() -> None:
        for _ in range(max(0, args.source_search_integrator_passes)):
            result = _run([
                py,
                "scripts/public/control/leanmill/source_search_integrator.py",
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}-source-search-integrator",
                "--out-dir", args.source_search_integrations,
                "--agent-runtime", args.agent_default_runtime,
            ], timeout_s=args.command_timeout_s)
            commands.append(result)
            payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
            if not payload.get("claimed"):
                break

    def _run_source_binding_probe_lane() -> None:
        nonlocal heavy_lean_launched, source_binding_probe_runs
        if args.allow_heavy_lean and source_binding_probe_passes > 0 and not pause_source_binding_probes:
            for _ in range(source_binding_probe_passes):
                result = _run([
                    py,
                    "scripts/public/control/leanmill/source_binding_probe_worker.py",
                    "--queue-db", args.queue_db,
                    "--events", args.events,
                    "--worker-id", f"{args.worker_id}-source-binding-probe",
                    "--factory-policy", args.factory_policy,
                    "--policy-profile", args.policy_profile,
                ], timeout_s=args.command_timeout_s)
                commands.append(result)
                payload = _json_from_stdout_tail(str(result.get("stdout_tail") or ""))
                if payload.get("claimed"):
                    source_binding_probe_runs += 1
                heavy_lean_launched = heavy_lean_launched or bool(payload.get("heavy_lean_launched"))
                if not payload.get("claimed"):
                    break
        elif source_binding_probe_passes > 0:
            commands.append({
                "cmd": ["<python>", "scripts/public/control/leanmill/source_binding_probe_worker.py"],
                "returncode": 0,
                "skipped": True,
                "reason": "andon_pause_source_binding_probes" if pause_source_binding_probes else "heavy_lean_disabled",
                "source_binding_probe_worker_passes": source_binding_probe_passes,
                "andon_active": andon_active,
            })

    def _run_generic_probe_lane() -> None:
        nonlocal heavy_lean_launched
        if args.allow_heavy_lean and args.runner_probe_worker_passes > 0:
            probe_cmd = [
                py,
                "scripts/public/control/leanmill/probe_worker.py",
                "--factory-policy", args.factory_policy,
                "--policy-profile", args.policy_profile,
                "--queue-db", args.queue_db,
                "--events", args.events,
                "--worker-id", f"{args.worker_id}-probe",
                "--allow-heavy-lean",
            ]
            probe_result = _run(probe_cmd, timeout_s=args.command_timeout_s)
            commands.append(probe_result)
            probe_payload = _json_from_stdout_tail(str(probe_result.get("stdout_tail") or ""))
            heavy_lean_launched = heavy_lean_launched or bool(probe_payload.get("heavy_lean_launched"))
        else:
            commands.append({
                "cmd": ["<python>", "scripts/public/control/leanmill/probe_worker.py"],
                "returncode": 0,
                "skipped": True,
                "reason": "runner-local probe worker disabled; queued probes remain available to authorized probe daemons",
            })

    lane_dispatch = {
        "source_review": _run_source_review_lane,
        "source_scout": _run_source_scout_lane,
        "source_search": _run_source_search_lane,
        "source_search_integrator": _run_source_search_integrator_lane,
        "source_binding_probe": _run_source_binding_probe_lane,
        "agent_repair": _run_agent_repair_lane,
        "generic_probe": _run_generic_probe_lane,
    }
    if lane_execution["enabled"]:
        for lane in lane_order:
            _write_progress_status(args, stage=f"lane:{lane}", extra={
                "lane_execution": lane_execution,
                "command_count_before_lane": len(commands),
                "source_binding_probe_worker_passes": source_binding_probe_passes,
                "pause_source_binding_probes": pause_source_binding_probes,
                "andon_active": andon_active,
            })
            lane_dispatch[lane]()
    else:
        commands.append({
            "cmd": ["<python>", "scripts/public/control/leanmill/24x7_runner.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "policy_runner_drain_lanes_disabled_watchdog_owns_dedicated_lanes",
            "lane_execution": lane_execution,
        })

    commands.append(_run([
        py,
        "scripts/public/control/leanmill/station_health_dashboard.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--contract", args.contract,
        "--out", args.station_health,
    ], timeout_s=args.command_timeout_s))

    commands.append(_run_phase(args, phase="c_supply_expost_cleaner", cmd=[
        py,
        "scripts/public/control/leanmill/c_supply_expost_cleaner.py",
        "--out", args.c_supply_expost_cleaner,
        "--out-checkpoint", args.c_supply_clean_checkpoint,
        "--out-row-context", args.c_supply_clean_row_context,
    ], timeout_s=args.command_timeout_s))
    commands.append(_run_phase(args, phase="c_discriminating_slice_prep", cmd=[
        py,
        "scripts/public/control/leanmill/c_discriminating_slice_prep.py",
        "--checkpoint", args.c_supply_clean_checkpoint,
        "--row-context", args.c_supply_clean_row_context,
        "--spec-dir", args.family_spec_dir,
        "--registry", args.registry,
        "--out", args.c_supply_clean_selection,
        "--md", args.c_supply_clean_selection_md,
        "--row-context-out", args.c_supply_clean_selected_row_context,
        "--min-rows", str(max(1, int(args.c_supply_clean_min_rows))),
        "--limit", str(max(1, int(args.c_supply_clean_limit))),
        "--allow-not-ready",
    ], timeout_s=args.command_timeout_s))

    c_supply_growth = {"enabled": False, "reason": "disabled"}
    if args.grow_c_supply and governance_sentinel_ok:
        c_supply_growth = _run_phase(
            args,
            phase="c_supply_growth_controller",
            cmd=_c_supply_growth_controller_cmd(args),
            timeout_s=max(args.command_timeout_s, args.c_supply_growth_timeout_s),
        )
        commands.append(c_supply_growth)
    elif args.grow_c_supply:
        c_supply_growth = {
            "cmd": ["<python>", "scripts/public/control/leanmill/c_supply_growth_controller.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        }
        commands.append(c_supply_growth)

    c_supply_conversion_prioritizer = {
        "cmd": ["<python>", "scripts/public/control/leanmill/c_supply_conversion_prioritizer.py"],
        "returncode": 0,
        "skipped": True,
        "reason": "not_run_until_factory_intelligence_refresh",
    }
    agentic_portfolio = {
        "cmd": ["<python>", "scripts/public/control/leanmill/agentic_portfolio_controller.py"],
        "returncode": 0,
        "skipped": True,
        "reason": "not_run_until_factory_intelligence_refresh",
        "portfolio_phase": "post_factory_intelligence",
    }
    population_elo = _run_phase(args, phase="population_elo", cmd=_population_elo_cmd(args), timeout_s=args.command_timeout_s)
    commands.append(population_elo)

    stats = _queue_stats(args)
    open_queue = _queue_open_stats(args)
    vh_cx = work_queue.connect(args.queue_db)
    version_health = work_queue.worker_version_health(vh_cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=args.policy_profile)
    vh_cx.close()
    status = {
        "schema": "leanmill-24x7-control-status-v1",
        "generated_at_epoch": int(time.time()),
        "stage": "pre_intelligence_refresh",
        "final_status_pending": True,
        "cycle_started_at_epoch": cycle_started_at,
        "cycle_elapsed_s": max(0, int(time.time()) - cycle_started_at),
        "heavy_lean_allowed": bool(args.allow_heavy_lean),
        "heavy_lean_launched": heavy_lean_launched,
        "paid_llm_enabled": bool(args.allow_paid_llm),
        "llm_max_total_cost_usd": args.llm_max_total_cost_usd,
        "subscription_agent_launch_enabled": bool(args.allow_agent_launch),
        "policy_profile": getattr(args, "_policy_profile_applied", None),
        "governance_sentinel": governance_sentinel,
        "governance_sentinel_ok": governance_sentinel_ok,
        "andon": {
            "active": andon_active,
            "severity": andon.get("severity"),
            "defect_count": andon.get("defect_count"),
            "containment": andon_containment,
            "effective_probe_signature_cooldown_s": effective_probe_signature_cooldown_s,
            "effective_learning_family_cooldown_s": effective_learning_family_cooldown_s,
            "effective_replenisher_family_cooldown_s": effective_replenisher_family_cooldown_s,
            "pause_external_source_scouts": pause_external_source_scouts,
            "pause_source_binding_ingest": pause_source_binding_ingest,
            "pause_source_binding_probes": pause_source_binding_probes,
        },
        "enqueued_registry_refresh": enqueued_refresh,
        "enqueued_source_inventory_refresh": enqueued_source_refresh if args.refresh_first else "",
        "enqueued_canary_validation_refresh": enqueued_canary_refresh if args.refresh_first else "",
        "enqueued_governance_refresh": enqueued_governance_refresh if args.refresh_first else "",
        "enqueued_source_plan_refresh": enqueued_source_plan_refresh if args.refresh_first else "",
        "registry_worker_passes": registry_worker_runs,
        "station_health": args.station_health,
        "observability": args.observability_out,
        "observability_md": args.observability_md,
        "factory_intelligence": args.factory_intelligence_out,
        "factory_intelligence_md": args.factory_intelligence_md,
        "population_elo": args.population_elo_out,
        "population_elo_md": args.population_elo_md,
        "population_elo_checkpoint": args.population_elo_checkpoint,
        "population_elo_run_id": args.population_elo_run_id,
        "population_elo_refresh": population_elo,
        "expand_corpus_from_files": args.expand_corpus_out if args.expand_corpus_from_files else "",
        "source_plan": args.source_plan,
        "canary_packets": args.canary_packets,
        "source_search_integrations": args.source_search_integrations,
        "heldout_scout": args.heldout_scout,
        "heldout_scout_md": args.heldout_scout_md,
        "heldout_promotion": args.heldout_promotion,
        "heldout_promotion_md": args.heldout_promotion_md,
        "learning_seed_plan": args.learning_seed_plan,
        "preflight_self_correction": preflight_self_correction,
        "self_correction_seed_plan": args.self_correction_seed_plan,
        "self_correction_action_impact_ledger": args.self_correction_action_impact_ledger,
        "c_supply_batch_status": args.c_supply_batch_status,
        "c_supply_expost_cleaner": getattr(args, "c_supply_expost_cleaner", DEFAULT_C_SUPPLY_EXPOST_CLEANER),
        "c_supply_clean_checkpoint": getattr(args, "c_supply_clean_checkpoint", DEFAULT_C_SUPPLY_CLEAN_CHECKPOINT),
        "c_supply_clean_row_context": getattr(args, "c_supply_clean_row_context", DEFAULT_C_SUPPLY_CLEAN_ROW_CONTEXT),
        "c_supply_clean_selection": getattr(args, "c_supply_clean_selection", DEFAULT_C_SUPPLY_CLEAN_SELECTION),
        "c_supply_clean_selection_md": getattr(args, "c_supply_clean_selection_md", DEFAULT_C_SUPPLY_CLEAN_SELECTION_MD),
        "c_supply_clean_selected_row_context": getattr(args, "c_supply_clean_selected_row_context", DEFAULT_C_SUPPLY_CLEAN_SELECTED_ROW_CONTEXT),
        "c_supply_growth_status": getattr(args, "c_supply_growth_status", DEFAULT_C_SUPPLY_GROWTH_STATUS),
        "c_supply_growth_work_dir": getattr(args, "c_supply_growth_work_dir", DEFAULT_C_SUPPLY_GROWTH_WORK_DIR),
        "c_supply_growth": c_supply_growth,
        "c_supply_conversion_prioritizer_status": getattr(args, "c_supply_conversion_prioritizer_status", DEFAULT_C_SUPPLY_CONVERSION_PRIORITIZER),
        "c_supply_conversion_prioritizer": c_supply_conversion_prioritizer,
        "agentic_portfolio_status": getattr(args, "agentic_portfolio_status", DEFAULT_AGENTIC_PORTFOLIO_STATUS),
        "pre_growth_agentic_portfolio": pre_growth_agentic_portfolio,
        "agentic_portfolio": agentic_portfolio,
        "c_supply_batch_md": args.c_supply_batch_md,
        "external_source_scout_seed_plan": args.external_source_scout_seed_plan,
        "backlog_replenisher_status": args.backlog_replenisher_status,
        "dead_letter_triage_status": args.dead_letter_triage_status,
        "post_probe_triage_status": args.post_probe_triage_status,
        "recover_pruned_source_requests_status": args.recover_pruned_source_requests_status,
        "recover_rejected_bindings_status": args.recover_rejected_bindings_status,
        "external_source_search_recovery_status": args.external_source_search_recovery_status,
        "agent_output_ingestion_status": args.agent_output_ingestion_status,
        "source_binding_ingestion_status": args.source_binding_ingestion_status,
        "lane_floors": {
            "proposal": args.proposal_floor if args.replenish_backlog else 0,
            "agent": args.agent_floor if args.replenish_backlog else 0,
            "probe": args.probe_floor if args.replenish_backlog and args.allow_heavy_lean else 0,
            "external_source_scout": external_source_scout_target if args.seed_external_source_scouts else 0,
        },
        "lane_execution": lane_execution,
        "source_binding_probe_worker_passes": source_binding_probe_passes,
        "source_binding_probe_runs": source_binding_probe_runs,
        "external_source_scout_open": external_source_scout_open,
        "external_source_scout_needed": external_source_scout_needed if args.seed_external_source_scouts else 0,
        "queue": stats,
        "open_queue": open_queue,
        "worker_version_health": version_health,
        "commands": commands,
        "next_operator_actions": _next_operator_actions(open_queue),
    }
    Path(args.status_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.status_out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    commands.append(_run_phase(args, phase="observability", cmd=[
        py,
        "scripts/public/control/leanmill/observability.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", args.observability_out,
        "--md", args.observability_md,
        "--runner-status", args.status_out,
    ], timeout_s=args.command_timeout_s))
    commands.append(_run_phase(args, phase="factory_intelligence", cmd=[
        py,
        "scripts/public/control/leanmill/factory_intelligence.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", args.factory_intelligence_out,
        "--md", args.factory_intelligence_md,
        "--observability", args.observability_out,
        "--station-health", args.station_health,
        "--contract", args.contract,
        "--repair-registry", args.registry,
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--source-search-integrations", args.source_search_integrations,
        "--c-supply-batch-status", args.c_supply_batch_status,
        "--c-supply-expost-cleaner", getattr(args, "c_supply_expost_cleaner", DEFAULT_C_SUPPLY_EXPOST_CLEANER),
        "--c-supply-clean-selection", getattr(args, "c_supply_clean_selection", DEFAULT_C_SUPPLY_CLEAN_SELECTION),
        "--agentic-portfolio", getattr(args, "agentic_portfolio_status", DEFAULT_AGENTIC_PORTFOLIO_STATUS),
        "--population-elo", args.population_elo_out,
    ], timeout_s=args.command_timeout_s))
    _write_progress_status(args, stage="phase:c_supply_conversion_prioritizer:started")
    c_supply_conversion_prioritizer = _run_c_supply_conversion_prioritizer(args)
    _write_progress_status(args, stage="phase:c_supply_conversion_prioritizer:finished", extra={
        "returncode": c_supply_conversion_prioritizer.get("returncode"),
        "timed_out": bool(c_supply_conversion_prioritizer.get("timed_out")),
    })
    commands.append(c_supply_conversion_prioritizer)
    status["c_supply_conversion_prioritizer"] = c_supply_conversion_prioritizer
    _write_progress_status(args, stage="phase:andon_cord:started")
    andon_refresh = _run_andon_cord(args)
    _write_progress_status(args, stage="phase:andon_cord:finished", extra={
        "returncode": andon_refresh.get("returncode"),
        "timed_out": bool(andon_refresh.get("timed_out")),
    })
    commands.append(andon_refresh)
    status["andon_refresh"] = andon_refresh
    _write_progress_status(args, stage="phase:agentic_portfolio:started")
    if governance_sentinel_ok:
        agentic_portfolio = _run_agentic_portfolio_controller(args, phase="post_factory_intelligence")
    else:
        agentic_portfolio = {
            "cmd": ["<python>", "scripts/public/control/leanmill/agentic_portfolio_controller.py"],
            "returncode": 0,
            "skipped": True,
            "reason": "governance_sentinel_not_pass",
            "governance_sentinel": governance_sentinel,
        }
    _write_progress_status(args, stage="phase:agentic_portfolio:finished", extra={
        "returncode": agentic_portfolio.get("returncode"),
        "timed_out": bool(agentic_portfolio.get("timed_out")),
    })
    commands.append(agentic_portfolio)
    status["agentic_portfolio"] = agentic_portfolio
    self_correction = _run_intelligence_self_correction(args, commands, phase="post_factory_intelligence")
    stats = _queue_stats(args)
    open_queue = _queue_open_stats(args)
    status["queue"] = stats
    status["open_queue"] = open_queue
    status["self_correction"] = self_correction
    status["stage"] = "cycle_finished"
    status["final_status_pending"] = False
    status["cycle_elapsed_s"] = max(0, int(time.time()) - cycle_started_at)
    Path(args.status_out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    work_queue.append_event(args.events, {
        "event_type": "leanmill_24x7_cycle_finished",
        "payload": {
            "status_out": args.status_out,
            "queue": stats,
            "open_queue": open_queue,
            "heavy_lean_allowed": bool(args.allow_heavy_lean),
            "heavy_lean_launched": heavy_lean_launched,
            "paid_llm_enabled": bool(args.allow_paid_llm),
            "subscription_agent_launch_enabled": bool(args.allow_agent_launch),
            "stale_worker_process_count": version_health.get("stale_process_count"),
            "runtime_mismatch_count": version_health.get("runtime_mismatch_count"),
        },
        "artifact_paths": [
            args.status_out,
            args.governance_sentinel_out,
            args.scheduler_plan,
            args.station_health,
            args.observability_out,
            args.observability_md,
            args.factory_intelligence_out,
            args.factory_intelligence_md,
            args.population_elo_out,
            args.population_elo_md,
            args.source_plan,
            args.canary_packets,
            args.source_search_integrations,
            args.external_source_scout_seed_plan,
            args.external_source_search_recovery_status,
            args.heldout_scout,
            args.heldout_scout_md,
            args.heldout_promotion,
            args.heldout_promotion_md,
            args.andon_cord,
            args.learning_seed_plan,
            args.self_correction_seed_plan,
            args.self_correction_action_impact_ledger,
            args.c_supply_batch_status,
            args.c_supply_batch_md,
            getattr(args, "c_supply_conversion_prioritizer_status", DEFAULT_C_SUPPLY_CONVERSION_PRIORITIZER),
            args.backlog_replenisher_status,
            args.dead_letter_triage_status,
            args.retryable_failure_recovery_status,
            args.recover_pruned_source_requests_status,
            args.recover_rejected_bindings_status,
            args.agent_output_ingestion_status,
            args.source_binding_ingestion_status,
        ],
    })
    return status


def _next_operator_actions(stats: dict[str, Any]) -> list[str]:
    by_kind = stats.get("by_kind") or {}
    actions: list[str] = []
    if by_kind.get("station:residual_curriculum"):
        actions.append("compile queued Residual Compiler packets; this may require bounded Lean")
    if by_kind.get("station:source_qualification"):
        actions.append("advance source qualification buffer when Lean slot is free")
    if by_kind.get("station:repair_registry"):
        actions.append("source sibling or heldout evidence for queued repair-family promotion target")
    if (stats.get("by_status") or {}).get("dead_letter"):
        actions.append("inspect dead-lettered WorkItems before retrying")
    if not actions:
        actions.append("no queued station work detected; refresh source/residual inventory")
    return actions


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "q.sqlite")
        events = str(Path(td) / "events.jsonl")
        status = str(Path(td) / "status.json")
        plan = str(Path(td) / "plan.json")
        contract = str(Path(td) / "contract.json")
        Path(contract).write_text(json.dumps({"work_orders": []}) + "\n")
        result = cycle(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="self-test-worker",
            registry=DEFAULT_REGISTRY,
            family_spec_dir=str(Path(td) / "repair_families"),
            contract=contract,
            scheduler_plan=plan,
            station_health=str(Path(td) / "health.json"),
            observability_out=str(Path(td) / "observability.json"),
            observability_md=str(Path(td) / "observability.md"),
            factory_intelligence_out=str(Path(td) / "factory_intelligence.json"),
            factory_intelligence_md=str(Path(td) / "factory_intelligence.md"),
            population_elo_out=str(Path(td) / "population_elo.json"),
            population_elo_md=str(Path(td) / "population_elo.md"),
            population_elo_checkpoint=str(Path(td) / "c_supply_clean_checkpoint.jsonl"),
            population_elo_run_id="",
            status_out=status,
            governance_sentinel_out=str(Path(td) / "governance_sentinel.json"),
            run_governance_sentinel=True,
            expand_corpus_from_files=True,
            expand_corpus_source_dir=str(Path(td) / "missing_expand_files"),
            expand_corpus_out=str(Path(td) / "expand_corpus.json"),
            source_plan=str(Path(td) / "source_plan.json"),
            source_plan_md=str(Path(td) / "source_plan.md"),
            canary_packets=str(Path(td) / "canary_packets.json"),
            source_search_integrations=str(Path(td) / "source_search_integrations"),
            heldout_scout=str(Path(td) / "heldout_scout.json"),
            heldout_scout_md=str(Path(td) / "heldout_scout.md"),
            heldout_promotion=str(Path(td) / "heldout_promotion.json"),
            heldout_promotion_md=str(Path(td) / "heldout_promotion.md"),
            source_plan_refresh_interval_s=900,
            refresh_first=False,
            enqueue_limit=0,
            registry_worker_passes=0,
            llm_worker_passes=1,
            agent_worker_passes=1,
            source_search_worker_passes=1,
            source_search_integrator_passes=1,
            seed_learning_work=True,
            scout_heldouts=True,
            promote_heldouts=True,
            replenish_backlog=True,
            ingest_agent_outputs=True,
            learning_seed_plan=str(Path(td) / "learning_seed.json"),
            self_correction_seed_plan=str(Path(td) / "self_correction_seed.json"),
            self_correction_action_impact_ledger=str(Path(td) / "self_correction_action_impact.jsonl"),
            c_supply_batch_status=str(Path(td) / "c_supply_batch_status.json"),
            c_supply_batch_md=str(Path(td) / "c_supply_batch_status.md"),
            c_supply_batch_selection=str(Path(td) / "c_supply_selection.json"),
            c_supply_batch_checkpoint=str(Path(td) / "c_supply_checkpoint.jsonl"),
            c_supply_batch_row_context=str(Path(td) / "c_supply_rows.json"),
            c_supply_expost_cleaner=str(Path(td) / "c_supply_cleaner.json"),
            c_supply_clean_checkpoint=str(Path(td) / "c_supply_clean_checkpoint.jsonl"),
            c_supply_clean_row_context=str(Path(td) / "c_supply_clean_rows.json"),
            c_supply_clean_selection=str(Path(td) / "c_supply_clean_selection.json"),
            c_supply_clean_selection_md=str(Path(td) / "c_supply_clean_selection.md"),
            c_supply_clean_selected_row_context=str(Path(td) / "c_supply_clean_selected_rows.json"),
            c_supply_clean_min_rows=20,
            c_supply_clean_limit=30,
            c_supply_growth_status=str(Path(td) / "c_supply_growth.json"),
            c_supply_growth_work_dir=str(Path(td) / "c_supply_growth"),
            c_supply_conversion_prioritizer_status=str(Path(td) / "c_supply_conversion_prioritizer.json"),
            agentic_portfolio_status=str(Path(td) / "agentic_portfolio.json"),
            grow_c_supply=False,
            c_supply_growth_timeout_s=60,
            backlog_replenisher_status=str(Path(td) / "replenisher.json"),
            dead_letter_triage_status=str(Path(td) / "dead_letter_triage.json"),
            retryable_failure_recovery_status=str(Path(td) / "retryable_failure_recovery.json"),
            external_source_search_recovery_status=str(Path(td) / "external_source_recovery.json"),
            recover_pruned_source_requests_status=str(Path(td) / "recover_pruned.json"),
            recover_rejected_bindings_status=str(Path(td) / "recover_rejected_bindings.json"),
            triage_dead_letters=True,
            dead_letter_triage_limit=10,
            dead_letter_triage_max_requeues=1,
            dead_letter_triage_max_attempts=2,
            recover_retryable_failures=True,
            recover_retryable_since_epoch=0,
            recover_retryable_lookback_s=6 * 60 * 60,
            retryable_failure_recovery_limit=10,
            retryable_failure_recovery_max_requeues=1,
            retryable_failure_recovery_max_attempts=1,
            triage_post_probes=True,
            post_probe_triage_status=str(Path(td) / "post_probe_triage.json"),
            post_probe_triage_limit=10,
            post_probe_triage_max_enqueued=5,
            recover_external_source_search=True,
            recover_external_source_search_limit=10,
            recover_pruned_source_requests=True,
            recover_pruned_since_epoch=0,
            recover_pruned_lookback_s=DEFAULT_RECOVER_PRUNED_LOOKBACK_S,
            recover_pruned_limit=10,
            recover_pruned_priority=94,
            recover_rejected_source_bindings=True,
            recover_rejected_bindings_limit=10,
            agent_output_ingestion_status=str(Path(td) / "agent_ingest.json"),
            source_binding_ingestion_status=str(Path(td) / "source_binding_ingest.json"),
            source_family_allocator=str(Path(td) / "source_family_allocator.json"),
            andon_cord=str(Path(td) / "andon.json"),
            agent_output_max_ingest=1,
            source_binding_max_ingest=1,
            learning_max_total_jobs=4,
            external_source_scout_seed_plan=str(Path(td) / "external_source_scout.json"),
            seed_external_source_scouts=True,
            external_source_scout_runtimes="codex",
            external_source_scout_max_families=1,
            external_source_scout_tasks_per_family=1,
            external_source_scout_floor=1,
            external_source_scout_max_enqueued=1,
            learning_max_probe_families=1,
            learning_max_family_spec_probe_families=1,
            learning_max_proposal_jobs=1,
            learning_max_agent_jobs=0,
            self_correct_from_intelligence=True,
            self_correction_actions={},
            self_correction_max_actions_per_cycle=2,
            learning_terminal_proposal_family_cooldown_s=900,
            learning_terminal_agent_family_cooldown_s=900,
            heldout_scout_max_candidates_per_family=2,
            heldout_scout_max_enqueued_tasks=1,
            heldout_scout_include_seed_families=True,
            heldout_promotion_max_enqueued=1,
            proposal_floor=1,
            agent_floor=0,
            probe_floor=0,
            family_spec_probe_floor=0,
            source_shape_probe_floor=0,
            probe_command_timeout_s=1200,
            probe_command_timeout_overhead_s=180,
            replenisher_terminal_family_cooldown_s=900,
            replenisher_terminal_proposal_family_cooldown_s=900,
            replenisher_terminal_agent_family_cooldown_s=900,
            replenisher_terminal_probe_signature_cooldown_s=21600,
            allow_paid_llm=False,
            llm_max_total_cost_usd=0.0,
            llm_model_family="gpt4.1-mini",
            llm_session_id="self-test",
            allow_llm_codex_cli_fallback=False,
            llm_codex_cli_fallback_model="gpt-5.4-mini",
            llm_codex_cli_fallback_timeout_s=240,
            allow_agent_launch=False,
            agent_default_runtime="codex",
            agent_worker_claim_patch_modes="",
            agent_default_codex_model="gpt-5.4-mini",
            agent_family_spec_patch_codex_model="gpt-5.5",
            agent_max_wall_time_s=1200,
            agent_max_iterations=3,
            allow_heavy_lean=False,
            runner_probe_worker_passes=0,
            command_timeout_s=30,
            factory_policy=str(Path(td) / "policy.json"),
            policy_profile="",
            worker_heartbeat_stale_s=0,
        ))
        assert result["heavy_lean_launched"] is False
        assert result["governance_sentinel_ok"] is True
        assert result["lane_execution"]["order"][:5] == [
            "source_review",
            "source_scout",
            "source_search",
            "source_search_integrator",
            "source_binding_probe",
        ]
        assert Path(status).exists()
        assert json.loads(Path(status).read_text())["schema"] == "leanmill-24x7-control-status-v1"
        progress_status = str(Path(td) / "progress_status.json")
        _write_progress_status(
            argparse.Namespace(status_out=progress_status, worker_id="progress-worker", policy_profile="p"),
            stage="lane:source_scout",
            extra={"lane_execution": {"order": ["source_scout"]}},
        )
        progress_obj = json.loads(Path(progress_status).read_text())
        assert progress_obj["schema"] == "leanmill-24x7-progress-status-v1"
        assert progress_obj["stage"] == "lane:source_scout"
        lane_policy = Path(td) / "lane_policy.json"
        lane_policy.write_text(json.dumps({
            "profiles": {
                "p": {
                    "runner": {
                        "lane_execution_order": ["source_binding_probe", "bogus_lane", "agent_repair"]
                    }
                }
            }
        }) + "\n")
        lane_order, unknown_lanes, appended_lanes = _lane_execution_order(argparse.Namespace(
            factory_policy=str(lane_policy),
            policy_profile="p",
        ))
        assert lane_order[:2] == ["source_binding_probe", "agent_repair"]
        assert unknown_lanes == ["bogus_lane"]
        assert "source_review" in appended_lanes
        cmd = _learning_seed_self_correction_cmd(
            argparse.Namespace(
                queue_db=db,
                events=events,
                self_correction_seed_plan=str(Path(td) / "self_correction_direct.json"),
                self_correction_action_impact_ledger=str(Path(td) / "self_correction_action_impact_direct.jsonl"),
                c_supply_batch_status=str(Path(td) / "c_supply_direct.json"),
                c_supply_batch_md=str(Path(td) / "c_supply_direct.md"),
                agent_default_runtime="codex",
                agent_max_wall_time_s=1200,
                agent_max_iterations=3,
                learning_terminal_proposal_family_cooldown_s=900,
                learning_terminal_agent_family_cooldown_s=900,
                probe_command_timeout_s=1200,
                probe_command_timeout_overhead_s=180,
                factory_policy=str(Path(td) / "policy.json"),
                policy_profile="supervised_24x7",
                allow_heavy_lean=False,
            ),
            rec_class="source_binding_conversion_gap",
            action={
                "max_total_jobs": 2,
                "max_enqueued": 2,
                "max_family_spec_repair_jobs": 0,
                "max_family_spec_generality_jobs": 0,
                "max_agent_jobs": 2,
            },
            ordinal=0,
        )
        assert cmd[cmd.index("--policy-profile") + 1] == "supervised_24x7"
        assert cmd[cmd.index("--max-family-spec-generality-jobs") + 1] == "0"
        assert cmd[cmd.index("--max-family-spec-repair-jobs") + 1] == "0"
        assert cmd[cmd.index("--max-agent-jobs") + 1] == "2"
        c_cmd = _c_supply_batch_self_correction_cmd(
            argparse.Namespace(
                factory_policy=str(Path(td) / "policy.json"),
                c_supply_batch_status=str(Path(td) / "c_supply_direct.json"),
                c_supply_batch_md=str(Path(td) / "c_supply_direct.md"),
            ),
            rec_class="c_discriminating_supply_debt",
            action={"max_corpora": 2, "max_new_rows_per_corpus": 3, "min_freeze_rows": 20, "no_run": True},
            ordinal=0,
        )
        assert "scripts/public/control/leanmill/c_supply_batch.py" in c_cmd
        assert c_cmd[c_cmd.index("--out") + 1] != str(Path(td) / "c_supply_direct.json")
        assert c_cmd[c_cmd.index("--md") + 1] != str(Path(td) / "c_supply_direct.md")
        assert Path(c_cmd[c_cmd.index("--out") + 1]).name.startswith("self_correction_")
        assert "c_supply_batch" in Path(c_cmd[c_cmd.index("--out") + 1]).name
        run_id_arg = c_cmd[c_cmd.index("--run-id") + 1]
        assert run_id_arg.startswith("self_correct_c_discriminating_supply_debt"), run_id_arg
        c_cmd_repeat = _c_supply_batch_self_correction_cmd(
            argparse.Namespace(
                factory_policy=str(Path(td) / "policy.json"),
                c_supply_batch_status=str(Path(td) / "c_supply_direct.json"),
                c_supply_batch_md=str(Path(td) / "c_supply_direct.md"),
            ),
            rec_class="c_discriminating_supply_debt",
            action={"no_run": True},
            ordinal=0,
        )
        assert c_cmd_repeat[c_cmd_repeat.index("--out") + 1] != c_cmd[c_cmd.index("--out") + 1]
        assert c_cmd[c_cmd.index("--max-corpora") + 1] == "2"
        assert "--corpus-offset" not in c_cmd
        assert c_cmd[c_cmd.index("--max-new-rows-per-corpus") + 1] == "3"
        assert "--no-run" in c_cmd
        c_profile_cmd = _c_supply_batch_self_correction_cmd(
            argparse.Namespace(
                factory_policy=str(Path(td) / "policy.json"),
                c_supply_batch_status=str(Path(td) / "c_supply_profile.json"),
                c_supply_batch_md=str(Path(td) / "c_supply_profile.md"),
                c_supply_batch_selection=str(Path(td) / "c_supply_selection.json"),
            ),
            rec_class="c_discriminating_supply_debt",
            action={"budget_profile": "source_demand_mining", "source_demand_only": True},
            ordinal=0,
        )
        assert "--budget-profile" in c_profile_cmd
        assert "--max-corpora" not in c_profile_cmd
        assert c_profile_cmd[c_profile_cmd.index("--out") + 1] != str(Path(td) / "c_supply_profile.json")
        growth_cmd = _c_supply_growth_controller_cmd(argparse.Namespace(
            c_supply_clean_selection="selection.json",
            c_supply_clean_checkpoint="checkpoint.jsonl",
            c_supply_clean_row_context="rows.json",
            family_spec_dir="families",
            registry="registry.json",
            queue_db="queue.sqlite",
            events="events.jsonl",
            factory_policy=str(Path(td) / "policy.json"),
            policy_profile="supervised_24x7",
            c_supply_growth_work_dir=str(Path(td) / "growth"),
            c_supply_growth_status=str(Path(td) / "growth.json"),
            worker_id="runner-test",
            allow_heavy_lean=True,
        ))
        assert "--allow-heavy-lean" in growth_cmd, growth_cmd
        routing_policy = Path(td) / "routing_policy.json"
        routing_policy.write_text(json.dumps({"operations": {"multi_node_control_plane": {"routing": {"default_weighted_nodes": ["local-mac:1", "vps-hetzner-49-13-160-58:2"]}}}}) + "\n")
        old_node = __import__("os").environ.get("LEANMILL_NODE_ID")
        try:
            __import__("os").environ["LEANMILL_NODE_ID"] = "local-mac"
            routed_seed = _learning_seed_self_correction_cmd(
                argparse.Namespace(
                    factory_policy=str(routing_policy), policy_profile="supervised_24x7", queue_db=str(Path(td) / "q.sqlite"), events=events,
                    self_correction_seed_plan=str(Path(td) / "seed.json"), agent_default_runtime="codex", agent_max_wall_time_s=10,
                    agent_max_iterations=1, learning_terminal_proposal_family_cooldown_s=0, learning_terminal_agent_family_cooldown_s=0,
                    probe_command_timeout_s=10, probe_command_timeout_overhead_s=1, allow_heavy_lean=False,
                ),
                rec_class="route_test", action={"max_enqueued": 1}, ordinal=0,
            )
            assert "--routing-nodes" in routed_seed and "local-mac:1,vps-hetzner-49-13-160-58:2" in routed_seed, routed_seed
        finally:
            if old_node is None:
                __import__("os").environ.pop("LEANMILL_NODE_ID", None)
            else:
                __import__("os").environ["LEANMILL_NODE_ID"] = old_node
        action_impact_ledger = str(Path(td) / "self_correction_action_impact_unit.jsonl")
        plan_out = str(Path(td) / "self_correction_plan_unit.json")
        Path(plan_out).write_text(json.dumps({
            "job_count": 1,
            "bucket_counts": {"family_spec_generalize": 1},
            "enqueued": 1,
            "skip_counts": {},
            "anti_laundering_rule": "proof value requires governance",
        }) + "\n")
        impact = _append_self_correction_action_impact(
            argparse.Namespace(
                factory_intelligence_out=str(Path(td) / "factory_intelligence.json"),
                self_correction_action_impact_ledger=action_impact_ledger,
                events=events,
            ),
            dispatch={
                "recommendation_class": "family_spec_generality_supply_debt",
                "tool": "learning_work_seeder",
                "plan_out": plan_out,
                "action_contract": {
                    "action_id": "self_correct:test",
                    "baseline_action": "record_recommendation_only",
                    "counterfactual_action": "enqueue_bounded_corrective_work",
                    "expected_effect": "test",
                },
            },
            result={"returncode": 0},
            before={"queue_open_total": 0, "open_kind_counts": {}, "scoreboard_tail_counts": {"negative_control_unexpected_pass_count": 0}},
            after={"queue_open_total": 1, "open_kind_counts": {"agent_repair_task": 1}, "scoreboard_tail_counts": {"negative_control_unexpected_pass_count": 0}},
        )
        assert impact["status"] == "measured"
        assert impact["observed_outcome"] == "corrective_work_enqueued"
        assert impact["guardrail_metrics"]["proof_credit_granted"] == 0.0
        ledger_row = json.loads(Path(action_impact_ledger).read_text().splitlines()[-1])
        assert ledger_row["action_id"] == "self_correct:test"
    print("leanmill_24x7_runner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="leanmill-24x7-local")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--family-spec-dir", default="analytics/public/leanmill/repair_families")
    ap.add_argument("--contract", default=f"{DEFAULT_DATA_DIR}/station_action_contract.json")
    ap.add_argument("--scheduler-plan", default=DEFAULT_SCHEDULER_PLAN)
    ap.add_argument("--station-health", default=DEFAULT_STATION_HEALTH)
    ap.add_argument("--observability-out", default=DEFAULT_OBSERVABILITY)
    ap.add_argument("--observability-md", default=DEFAULT_OBSERVABILITY_MD)
    ap.add_argument("--factory-intelligence-out", default=DEFAULT_FACTORY_INTELLIGENCE)
    ap.add_argument("--factory-intelligence-md", default=DEFAULT_FACTORY_INTELLIGENCE_MD)
    ap.add_argument("--population-elo-out", default=DEFAULT_POPULATION_ELO)
    ap.add_argument("--population-elo-md", default=DEFAULT_POPULATION_ELO_MD)
    ap.add_argument("--population-elo-checkpoint", default=DEFAULT_C_SUPPLY_CLEAN_CHECKPOINT)
    ap.add_argument("--population-elo-run-id", default="")
    ap.add_argument("--status-out", default=DEFAULT_STATUS)
    ap.add_argument("--governance-sentinel-out", default=DEFAULT_GOVERNANCE_SENTINEL)
    ap.add_argument("--run-governance-sentinel", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--expand-corpus-from-files", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--expand-corpus-source-dir", default=DEFAULT_EXPAND100_SOURCE_DIR)
    ap.add_argument("--expand-corpus-out", default=DEFAULT_EXPAND100_CORPUS)
    ap.add_argument("--source-plan", default=DEFAULT_SOURCE_PLAN)
    ap.add_argument("--source-plan-md", default=DEFAULT_SOURCE_PLAN_MD)
    ap.add_argument("--canary-packets", default=DEFAULT_CANARY_PACKETS)
    ap.add_argument("--source-search-integrations", default=DEFAULT_SOURCE_SEARCH_INTEGRATIONS)
    ap.add_argument("--heldout-scout", default=DEFAULT_HELDOUT_SCOUT)
    ap.add_argument("--heldout-scout-md", default=DEFAULT_HELDOUT_SCOUT_MD)
    ap.add_argument("--heldout-promotion", default=DEFAULT_HELDOUT_PROMOTION)
    ap.add_argument("--heldout-promotion-md", default=DEFAULT_HELDOUT_PROMOTION_MD)
    ap.add_argument("--source-plan-refresh-interval-s", type=int, default=900)
    ap.add_argument("--learning-seed-plan", default=DEFAULT_LEARNING_SEED_PLAN)
    ap.add_argument("--self-correction-seed-plan", default=DEFAULT_SELF_CORRECTION_PLAN)
    ap.add_argument("--self-correction-action-impact-ledger", default=DEFAULT_SELF_CORRECTION_ACTION_IMPACT)
    ap.add_argument("--family-birth-plan", default=DEFAULT_FAMILY_BIRTH_PLAN)
    ap.add_argument("--family-birth-plan-md", default=DEFAULT_FAMILY_BIRTH_PLAN_MD)
    ap.add_argument("--c-supply-batch-status", default=DEFAULT_C_SUPPLY_BATCH_STATUS)
    ap.add_argument("--c-supply-batch-md", default=DEFAULT_C_SUPPLY_BATCH_MD)
    ap.add_argument("--c-supply-batch-selection", default=DEFAULT_C_SUPPLY_BATCH_SELECTION)
    ap.add_argument("--c-supply-batch-checkpoint", default=DEFAULT_C_SUPPLY_BATCH_CHECKPOINT)
    ap.add_argument("--c-supply-batch-row-context", default=DEFAULT_C_SUPPLY_BATCH_ROW_CONTEXT)
    ap.add_argument("--c-supply-expost-cleaner", default=DEFAULT_C_SUPPLY_EXPOST_CLEANER)
    ap.add_argument("--c-supply-clean-checkpoint", default=DEFAULT_C_SUPPLY_CLEAN_CHECKPOINT)
    ap.add_argument("--c-supply-clean-row-context", default=DEFAULT_C_SUPPLY_CLEAN_ROW_CONTEXT)
    ap.add_argument("--c-supply-clean-selection", default=DEFAULT_C_SUPPLY_CLEAN_SELECTION)
    ap.add_argument("--c-supply-clean-selection-md", default=DEFAULT_C_SUPPLY_CLEAN_SELECTION_MD)
    ap.add_argument("--c-supply-clean-selected-row-context", default=DEFAULT_C_SUPPLY_CLEAN_SELECTED_ROW_CONTEXT)
    ap.add_argument("--c-supply-clean-min-rows", type=int, default=20)
    ap.add_argument("--c-supply-clean-limit", type=int, default=30)
    ap.add_argument("--c-supply-growth-status", default=DEFAULT_C_SUPPLY_GROWTH_STATUS)
    ap.add_argument("--c-supply-growth-work-dir", default=DEFAULT_C_SUPPLY_GROWTH_WORK_DIR)
    ap.add_argument("--agentic-portfolio-status", default=DEFAULT_AGENTIC_PORTFOLIO_STATUS)
    ap.add_argument("--grow-c-supply", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--c-supply-growth-timeout-s", type=int, default=1800)
    ap.add_argument("--backlog-replenisher-status", default=DEFAULT_BACKLOG_REPLENISHER_STATUS)
    ap.add_argument("--dead-letter-triage-status", default=DEFAULT_DEAD_LETTER_TRIAGE_STATUS)
    ap.add_argument("--retryable-failure-recovery-status", default=DEFAULT_RETRYABLE_FAILURE_RECOVERY_STATUS)
    ap.add_argument("--recover-pruned-source-requests-status", default=DEFAULT_RECOVER_PRUNED_SOURCE_REQUESTS_STATUS)
    ap.add_argument("--recover-rejected-bindings-status", default=DEFAULT_RECOVER_REJECTED_BINDINGS_STATUS)
    ap.add_argument("--agent-output-ingestion-status", default=DEFAULT_AGENT_OUTPUT_INGESTION_STATUS)
    ap.add_argument("--source-binding-ingestion-status", default=DEFAULT_SOURCE_BINDING_INGESTION_STATUS)
    ap.add_argument("--source-family-allocator", default=DEFAULT_SOURCE_FAMILY_ALLOCATOR)
    ap.add_argument("--andon-cord", default=DEFAULT_ANDON_CORD)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="", help="Optional named profile from the factory policy artifact.")
    ap.add_argument("--refresh-first", action="store_true")
    ap.add_argument("--enqueue-limit", type=int, default=10)
    ap.add_argument("--registry-worker-passes", type=int, default=3)
    ap.add_argument("--llm-worker-passes", type=int, default=1)
    ap.add_argument("--agent-worker-passes", type=int, default=1)
    ap.add_argument("--source-search-worker-passes", type=int, default=1)
    ap.add_argument("--source-search-integrator-passes", type=int, default=1)
    ap.add_argument("--seed-learning-work", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--scout-heldouts", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--promote-heldouts", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--replenish-backlog", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--ingest-agent-outputs", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--triage-dead-letters", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--dead-letter-triage-limit", type=int, default=20)
    ap.add_argument("--dead-letter-triage-max-requeues", type=int, default=1)
    ap.add_argument("--dead-letter-triage-max-attempts", type=int, default=2)
    ap.add_argument("--recover-retryable-failures", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--recover-retryable-since-epoch", type=int, default=0)
    ap.add_argument("--recover-retryable-lookback-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--retryable-failure-recovery-limit", type=int, default=50)
    ap.add_argument("--retryable-failure-recovery-max-requeues", type=int, default=1)
    ap.add_argument("--retryable-failure-recovery-max-attempts", type=int, default=1)
    ap.add_argument("--triage-post-probes", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--post-probe-triage-status", default=DEFAULT_POST_PROBE_TRIAGE_STATUS)
    ap.add_argument("--post-probe-triage-limit", type=int, default=100)
    ap.add_argument("--post-probe-triage-max-enqueued", type=int, default=20)
    ap.add_argument("--recover-external-source-search", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--external-source-search-recovery-status", default=DEFAULT_EXTERNAL_SOURCE_SEARCH_RECOVERY_STATUS)
    ap.add_argument("--recover-external-source-search-limit", type=int, default=50)
    ap.add_argument("--recover-pruned-source-requests", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--recover-pruned-since-epoch", type=int, default=0)
    ap.add_argument("--recover-pruned-lookback-s", type=int, default=DEFAULT_RECOVER_PRUNED_LOOKBACK_S)
    ap.add_argument("--recover-pruned-limit", type=int, default=20)
    ap.add_argument("--recover-pruned-priority", type=int, default=94)
    ap.add_argument("--recover-rejected-source-bindings", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--recover-rejected-bindings-limit", type=int, default=20)
    ap.add_argument("--agent-output-max-ingest", type=int, default=4)
    ap.add_argument("--source-binding-max-ingest", type=int, default=4)
    ap.add_argument("--seed-external-source-scouts", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--external-source-scout-seed-plan", default=DEFAULT_EXTERNAL_SOURCE_SCOUT_SEED_PLAN)
    ap.add_argument("--external-source-scout-runtimes", default="codex,claude")
    ap.add_argument("--external-source-scout-max-families", type=int, default=8)
    ap.add_argument("--external-source-scout-tasks-per-family", type=int, default=2)
    ap.add_argument("--external-source-scout-floor", type=int, default=24)
    ap.add_argument("--external-source-scout-max-enqueued", type=int, default=12)
    ap.add_argument("--learning-max-total-jobs", type=int, default=12)
    ap.add_argument("--learning-max-probe-families", type=int, default=4)
    ap.add_argument("--learning-max-family-spec-probe-families", type=int, default=4)
    ap.add_argument("--learning-max-proposal-jobs", type=int, default=4)
    ap.add_argument("--learning-max-agent-jobs", type=int, default=1)
    ap.add_argument("--learning-terminal-proposal-family-cooldown-s", type=int, default=900)
    ap.add_argument("--learning-terminal-agent-family-cooldown-s", type=int, default=900)
    ap.add_argument("--self-correct-from-intelligence", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--self-correction-actions", default={})
    ap.add_argument("--self-correction-max-actions-per-cycle", type=int, default=0)
    ap.add_argument("--heldout-scout-max-candidates-per-family", type=int, default=8)
    ap.add_argument("--heldout-scout-max-enqueued-tasks", type=int, default=4)
    ap.add_argument("--heldout-scout-include-seed-families", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--heldout-promotion-max-enqueued", type=int, default=4)
    ap.add_argument("--proposal-floor", type=int, default=3)
    ap.add_argument("--agent-floor", type=int, default=3)
    ap.add_argument("--probe-floor", type=int, default=2)
    ap.add_argument("--family-spec-probe-floor", type=int, default=1)
    ap.add_argument("--source-shape-probe-floor", type=int, default=1)
    ap.add_argument("--probe-command-timeout-s", type=int, default=900)
    ap.add_argument("--probe-command-timeout-overhead-s", type=int, default=120)
    ap.add_argument("--replenisher-terminal-family-cooldown-s", type=int, default=3600)
    ap.add_argument("--replenisher-terminal-proposal-family-cooldown-s", type=int, default=900)
    ap.add_argument("--replenisher-terminal-agent-family-cooldown-s", type=int, default=900)
    ap.add_argument("--replenisher-terminal-probe-signature-cooldown-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--allow-paid-llm", action="store_true")
    ap.add_argument("--llm-max-total-cost-usd", type=float, default=0.0)
    ap.add_argument("--llm-model-family", default="gpt4.1-mini")
    ap.add_argument("--llm-session-id", default="leanmill_24x7")
    ap.add_argument("--allow-llm-codex-cli-fallback", action="store_true")
    ap.add_argument("--llm-codex-cli-fallback-model", default="gpt-5.4-mini")
    ap.add_argument("--llm-codex-cli-fallback-timeout-s", type=int, default=240)
    ap.add_argument("--allow-agent-launch", action="store_true")
    ap.add_argument("--agent-default-runtime", choices=["codex", "claude"], default="codex")
    ap.add_argument("--agent-worker-claim-patch-modes", default="")
    ap.add_argument("--agent-default-codex-model", default="gpt-5.4-mini")
    ap.add_argument("--agent-family-spec-patch-codex-model", default="gpt-5.5")
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--allow-heavy-lean", action="store_true")
    ap.add_argument("--runner-probe-worker-passes", type=int, default=0)
    ap.add_argument("--command-timeout-s", type=int, default=1800)
    ap.add_argument("--worker-heartbeat-stale-s", type=int, default=0)
    ap.add_argument("--sleep-s", type=int, default=60)
    ap.add_argument("--cycles", type=int, default=0, help="Number of cycles to run; 0 means run until stopped.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    _apply_policy_profile(args)
    if int(args.recover_pruned_priority) == 94:
        args.recover_pruned_priority = _queue_priority(args, "recover_pruned_source_requests", 94)

    last: dict[str, Any] = {}
    idx = 0
    while True:
        last = cycle(args)
        idx += 1
        if args.cycles > 0 and idx >= args.cycles:
            break
        time.sleep(max(1, args.sleep_s))
    print(json.dumps({
        "status_out": args.status_out,
        "queue": last.get("queue"),
        "next_operator_actions": last.get("next_operator_actions"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
