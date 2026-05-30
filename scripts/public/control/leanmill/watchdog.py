#!/usr/bin/env python3
"""Local LeanMill daemon watchdog.

This is a control-plane supervisor for the local tmux-based mill. It restarts
missing bounded daemons, refreshes factory intelligence, runs safety gates, and
writes a receipt. It does not create proof credit or mutate scientific
scoreboards.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import lane_budget_plan
from leanmill_paths import DATA_DIR as LEANMILL_DATA_DIR
from leanmill_paths import FACTORY_POLICY


DATA_DIR = Path(LEANMILL_DATA_DIR)
DEFAULT_OUT = DATA_DIR / "leanmill_watchdog_status.json"
DEFAULT_EVENTS = work_queue.DEFAULT_EVENTS
DEFAULT_SHUTDOWN_MARKER = DATA_DIR / "leanmill_shutdown_requested.json"
DEFAULT_POLICY_PROFILE = "supervised_24x7_low_burn"


def _python() -> str:
    return "./venv/bin/python" if Path("./venv/bin/python").exists() else sys.executable


def _profile_settings(policy_profile: str) -> dict[str, Any]:
    try:
        obj = json.loads(Path(FACTORY_POLICY).read_text(errors="ignore"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    profile = ((obj.get("profiles") or {}).get(policy_profile) or {})
    runner = profile.get("runner") or {}
    return runner if isinstance(runner, dict) else {}


def _heavy_lean_slot_count(settings: dict[str, Any]) -> int:
    node_id = os.environ.get("LEANMILL_NODE_ID", "")
    configured = settings.get("heavy_lean_slot_count")
    per_node = settings.get("heavy_lean_slot_count_by_node")
    if isinstance(per_node, dict) and node_id:
        configured = per_node.get(node_id, configured)
    try:
        return max(1, int(configured or 1))
    except (TypeError, ValueError):
        return 1


def _heavy_lean_lock_arg(worker_index: int, slot_count: int) -> str:
    slot = ((max(1, worker_index) - 1) % max(1, slot_count)) + 1
    if slot == 1:
        return "/tmp/rung1/leanmill_heavy_lean.lock"
    return f"/tmp/rung1/leanmill_heavy_lean_{slot}.lock"


def _agent_claim_patch_mode_args(settings: dict[str, Any]) -> str:
    raw = settings.get("agent_worker_claim_patch_modes", "")
    if isinstance(raw, str):
        modes = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, list):
        modes = [str(part).strip() for part in raw if str(part).strip()]
    else:
        modes = []
    return "".join(f" --claim-patch-mode {shlex.quote(mode)}" for mode in modes)


def _control_runner_session_name(policy_profile: str) -> str:
    if policy_profile == "supervised_24x7":
        return "leanmill_24x7_full"
    if policy_profile == "supervised_24x7_low_burn":
        return "leanmill_24x7_low_burn"
    safe = "".join(ch if ch.isalnum() else "_" for ch in policy_profile).strip("_") or "custom"
    return f"leanmill_24x7_{safe[:48]}"


def _session_env_prefix() -> str:
    """Preserve path/queue policy when watchdog spawns tmux workers."""
    keys = [
        "LEANMILL_DATA_DIR",
        "LEANMILL_REPAIR_FAMILY_SPEC_DIR",
        "LEANMILL_FACTORY_POLICY",
        "LEANMILL_SCRATCH_ROOT",
        "LEANMILL_QUEUE_DB",
        "LEANMILL_EVENTS",
        "LEANMILL_NODE_ID",
    ]
    pairs = []
    for key in keys:
        val = os.environ.get(key)
        if val:
            pairs.append(f"{key}={shlex.quote(val)}")
    return "env " + " ".join(pairs) + " " if pairs else ""


def _lane_budget(plan: dict[str, Any], role: str, fallback: int) -> dict[str, Any]:
    for lane in plan.get("lanes") or []:
        if isinstance(lane, dict) and str(lane.get("role") or "") == role:
            return lane
    return {"role": role, "worker_count": fallback}


def _sessions(policy_profile: str = DEFAULT_POLICY_PROFILE) -> list[dict[str, str]]:
    py = _python()
    env_prefix = _session_env_prefix()
    settings = _profile_settings(policy_profile)
    lane_plan = lane_budget_plan(path=FACTORY_POLICY, profile_name=policy_profile, node_id=os.environ.get("LEANMILL_NODE_ID", ""))
    llm_cap = float(settings.get("llm_max_total_cost_usd", 10.0))
    llm_idle_s = 10 if policy_profile == "supervised_24x7" else 15
    repair_lane = _lane_budget(lane_plan, "general_subscription_agent", 1)
    source_lane = _lane_budget(lane_plan, "source_subscription_agent", 1)
    source_review_lane = _lane_budget(lane_plan, "upstream_source_request_review", 0)
    source_search_lane = _lane_budget(lane_plan, "source_retrieval_and_static_filter", 0)
    source_integrator_lane = _lane_budget(lane_plan, "source_binding_task_integrator", 0)
    source_binding_probe_lane = _lane_budget(lane_plan, "source_bound_canary_probe", 0)
    family_probe_lane = _lane_budget(lane_plan, "family_spec_probe", 1)
    non_family_probe_lane = _lane_budget(lane_plan, "non_family_probe", 1)
    repair_workers = max(1, int(repair_lane.get("worker_count") or 1))
    agent_claim_patch_modes = "".join(f" --claim-patch-mode {shlex.quote(str(mode))}" for mode in (repair_lane.get("claim_patch_modes") or []))
    if not agent_claim_patch_modes:
        agent_claim_patch_modes = _agent_claim_patch_mode_args(settings)
    source_workers = max(0, int(source_lane.get("worker_count") or 0))
    source_review_workers = max(0, int(source_review_lane.get("worker_count") or 0))
    source_search_workers = max(0, int(source_search_lane.get("worker_count") or 0))
    source_integrator_workers = max(0, int(source_integrator_lane.get("worker_count") or 0))
    source_binding_probe_workers = max(0, int(source_binding_probe_lane.get("worker_count") or 0))
    family_spec_probe_workers = max(1, int(family_probe_lane.get("worker_count") or 1))
    non_family_probe_workers = max(0, int(non_family_probe_lane.get("worker_count") or 0))
    agent_default_model = str(settings.get("agent_default_codex_model") or "gpt-5.4-mini")
    agent_family_spec_patch_model = str(settings.get("agent_family_spec_patch_codex_model") or "gpt-5.5")
    repair_agent_max_wall_time_s = max(1, int(repair_lane.get("max_wall_time_s") or settings.get("agent_max_wall_time_s") or 1200))
    repair_agent_max_iterations = max(1, int(repair_lane.get("max_iterations") or settings.get("agent_max_iterations") or 3))
    heavy_lean_slot_count = max(1, int(
        family_probe_lane.get("heavy_lean_slot_count")
        or non_family_probe_lane.get("heavy_lean_slot_count")
        or source_binding_probe_lane.get("heavy_lean_slot_count")
        or _heavy_lean_slot_count(settings)
    ))
    sessions = [
        {
            "name": _control_runner_session_name(policy_profile),
            "role": "control_runner",
            "worker_id": "leanmill-24x7-local",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/24x7_runner.py "
                f"--factory-policy {FACTORY_POLICY} --policy-profile {policy_profile}"
            ),
        },
        {
            "name": "leanmill_llm30",
            "role": "api_llm_proposal",
            "worker_id": "leanmill-llm-proposal-daemon",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/llm_proposal_worker.py "
                f"--daemon --allow-paid-llm --max-total-cost-usd {llm_cap:g} --allow-codex-cli-fallback "
                f"--worker-id leanmill-llm-proposal-daemon --session-id leanmill_24x7 --idle-sleep-s {llm_idle_s}"
            ),
        },
    ]
    if bool(settings.get("external_source_scout_release_daemon", settings.get("seed_external_source_scouts", False))):
        sessions.append({
            "name": "leanmill_source_release_daemon",
            "role": "source_scout_release",
            "worker_id": "leanmill-source-release-daemon",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/external_source_scout_release_daemon.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-release-daemon "
                f"--idle-sleep-s {int(settings.get('external_source_scout_release_idle_s') or 60)}"
            ),
        })
    for idx in range(1, repair_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        worker_id = f"leanmill-warm-codex-agent-{idx}"
        required_fragments = []
        for mode in (repair_lane.get("claim_patch_modes") or []):
            mode_s = str(mode).strip()
            if mode_s:
                required_fragments.append(f"--claim-patch-mode {mode_s}")
        if not required_fragments:
            for mode in str(settings.get("agent_worker_claim_patch_modes", "")).split(","):
                mode_s = mode.strip()
                if mode_s:
                    required_fragments.append(f"--claim-patch-mode {mode_s}")
        sessions.append({
            "name": f"leanmill_warm_codex_agent{suffix}",
            "role": "general_subscription_agent",
            "worker_id": worker_id,
            "required_process_fragments": required_fragments,
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/agent_repair_worker.py "
                f"--daemon --allow-agent-launch --default-runtime codex --default-codex-model {shlex.quote(agent_default_model)} "
                f"--family-spec-patch-codex-model {shlex.quote(agent_family_spec_patch_model)} "
                f"--worker-id {worker_id} --claim-kind agent_repair_task "
                "--claim-kind subscription_agent_task --claim-kind agent_task --claim-kind agent_repair "
                f"--max-wall-time-s {repair_agent_max_wall_time_s} --max-iterations {repair_agent_max_iterations} "
                f"--idle-sleep-s 15{agent_claim_patch_modes}"
            ),
        })
    for idx in range(1, source_workers + 1):
        sessions.append({
            "name": f"leanmill_source_codex_{idx}",
            "role": "source_subscription_agent",
            "worker_id": f"leanmill-source-codex-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/source_scout_worker.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-codex-{idx} --idle-sleep-s 10"
            ),
        })
    for idx in range(1, source_review_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        sessions.append({
            "name": f"leanmill_source_review_daemon{suffix}",
            "role": "upstream_source_request_review",
            "worker_id": f"leanmill-source-review-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/source_review_worker.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-review-{idx} --idle-sleep-s 10"
            ),
        })
    for idx in range(1, source_search_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        sessions.append({
            "name": f"leanmill_source_search_daemon{suffix}",
            "role": "source_retrieval_and_static_filter",
            "worker_id": f"leanmill-source-search-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/source_search_worker.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-search-{idx} --idle-sleep-s 15"
            ),
        })
    for idx in range(1, source_integrator_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        sessions.append({
            "name": f"leanmill_source_integrator_daemon{suffix}",
            "role": "source_binding_task_integrator",
            "worker_id": f"leanmill-source-integrator-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/source_search_integrator.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-integrator-{idx} "
                "--idle-sleep-s 15"
            ),
        })
    for idx in range(1, source_binding_probe_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        sessions.append({
            "name": f"leanmill_source_binding_probe_daemon{suffix}",
            "role": "source_bound_canary_probe",
            "worker_id": f"leanmill-source-binding-probe-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/source_binding_probe_worker.py "
                f"--daemon --factory-policy {FACTORY_POLICY} --policy-profile {policy_profile} "
                f"--worker-id leanmill-source-binding-probe-{idx} --idle-sleep-s 10"
            ),
        })
    for idx in range(1, family_spec_probe_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        lock_arg = _heavy_lean_lock_arg(idx, heavy_lean_slot_count)
        sessions.append({
            "name": f"leanmill_probe_family_spec_daemon{suffix}",
            "role": "family_spec_probe",
            "worker_id": f"probe-family-spec-worker-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/probe_worker.py "
                f"--daemon --worker-id probe-family-spec-worker-{idx} --allow-heavy-lean --warm-repl-inline "
                f"--govern-winners --probe-lane family_spec --lean-slot-lock {lock_arg} --idle-sleep-s 5"
            ),
        })
    for idx in range(1, non_family_probe_workers + 1):
        suffix = "" if idx == 1 else f"_{idx}"
        lock_arg = _heavy_lean_lock_arg(family_spec_probe_workers + idx, heavy_lean_slot_count)
        sessions.append({
            "name": f"leanmill_probe_daemon{suffix}",
            "role": "non_family_probe",
            "worker_id": f"probe-non-family-worker-{idx}",
            "cmd": (
                f"{env_prefix}{py} scripts/public/control/leanmill/probe_worker.py "
                f"--daemon --worker-id probe-non-family-worker-{idx} --allow-heavy-lean --warm-repl-inline "
                f"--govern-winners --exclude-probe-lane family_spec --lean-slot-lock {lock_arg} --idle-sleep-s 15"
            ),
        })

    # ── Solver lane (Lane A) drain session ──────────────────────────────────
    # Wraps `ztare leanmill solver solve` in a bash poll loop. Each cycle:
    # detect node capabilities → claim solver-eligible rows (bounded by
    # --limit) → invoke via router (provider + fallbacks per policy) →
    # write unratified_closure_candidates + typed exits → governance ratifies.
    # Enable: policy.operations.solver_lane.enabled = true AND
    #         policy.operations.solver_lane.watchdog_session = true.
    try:
        policy_obj = json.loads(Path(FACTORY_POLICY).read_text())
        solver_cfg = (policy_obj.get("operations", {}) or {}).get("solver_lane", {}) or {}
    except Exception:
        solver_cfg = {}
    if bool(solver_cfg.get("enabled")) and bool(solver_cfg.get("watchdog_session")):
        provider = str(solver_cfg.get("provider") or "claude_opus")
        per_cycle_limit = int(solver_cfg.get("watchdog_per_cycle_limit", 3))
        cycle_sleep_s = int(solver_cfg.get("watchdog_cycle_sleep_s", 600))
        sessions.append({
            "name": "leanmill_solver_lane_drain",
            "role": "solver_lane_drain",
            "worker_id": "leanmill-solver-lane-drain",
            "cmd": (
                f"{env_prefix}bash -c 'cd ~/figs_activist_loop && "
                f"set -a; source .env 2>/dev/null; set +a; "
                f"while true; do "
                f"PYTHONPATH=src ./venv/bin/python -m ztare.cli leanmill solver solve "
                f"--provider {shlex.quote(provider)} --limit {per_cycle_limit} "
                f">> /tmp/leanmill_solver_lane_drain.log 2>&1; "
                f"sleep {cycle_sleep_s}; "
                f"done'"
            ),
        })

    return sessions


def _run(cmd: list[str], *, timeout_s: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def _tmux_has_session(name: str) -> bool:
    proc = subprocess.run(["tmux", "has-session", "-t", name], text=True, capture_output=True)
    return proc.returncode == 0


def _start_session(session: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"name": session["name"], "role": session["role"], "action": "would_start", "cmd": session["cmd"]}
    result = _run(["tmux", "new-session", "-d", "-s", session["name"], session["cmd"]], timeout_s=30)
    return {
        "name": session["name"],
        "role": session["role"],
        "action": "started" if result["returncode"] == 0 else "start_failed",
        "cmd": session["cmd"],
        "result": result,
    }


def _kill_session(name: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"returncode": 0, "dry_run": True}
    return _run(["tmux", "kill-session", "-t", name], timeout_s=30)


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _worker_has_running_claim(cx, worker_id: str) -> bool:
    if not worker_id:
        return False
    row = cx.execute(
        "select 1 from work_items where status = ? and claimed_by = ? limit 1",
        ("running", worker_id),
    ).fetchone()
    return row is not None


def _process_cmdline_for_worker(worker_id: str) -> str:
    if not worker_id:
        return ""
    proc = subprocess.run(["pgrep", "-af", worker_id], text=True, capture_output=True)
    if proc.returncode != 0:
        return ""
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    script_lines = [line for line in lines if "leanmill_" in line]
    return script_lines[0] if script_lines else (lines[0] if lines else "")


def _missing_required_process_fragments(session: dict[str, Any]) -> list[str]:
    worker_id = str(session.get("worker_id") or "")
    required = [str(part) for part in (session.get("required_process_fragments") or []) if str(part)]
    if not worker_id or not required:
        return []
    cmdline = _process_cmdline_for_worker(worker_id)
    if not cmdline:
        return []
    return [fragment for fragment in required if fragment not in cmdline]


def _stale_worker_reasons(version_health: dict[str, Any]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for entry in version_health.get("stale_processes") or []:
        if not isinstance(entry, dict):
            continue
        worker_id = str(entry.get("worker_id") or "")
        if not worker_id:
            continue
        reasons[worker_id] = str(entry.get("stale_reason") or "runtime_version_drift")
    return reasons


def _refresh_intelligence(args: argparse.Namespace) -> dict[str, Any]:
    py = _python()
    return _run([
        py,
        "scripts/public/control/leanmill/factory_intelligence.py",
        "--out", str(DATA_DIR / "leanmill_factory_intelligence.json"),
        "--md", str(DATA_DIR / "leanmill_factory_intelligence.md"),
        "--factory-policy", str(FACTORY_POLICY),
        "--policy-profile", str(args.policy_profile),
    ], timeout_s=args.command_timeout_s)


def _refresh_andon(args: argparse.Namespace) -> dict[str, Any]:
    py = _python()
    return _run([
        py,
        "scripts/public/control/leanmill/andon_cord.py",
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", str(DATA_DIR / "leanmill_andon_cord.json"),
        "--apply",
    ], timeout_s=args.command_timeout_s)


def _gate_results(args: argparse.Namespace) -> dict[str, Any]:
    py = _python()
    freeze = _run([py, "scripts/public/control/leanmill/infra_freeze_gate.py", "--window-s", str(args.freeze_window_s)], timeout_s=args.command_timeout_s)
    coverage: dict[str, Any] = {"skipped": True}
    if args.run_coverage_gate:
        coverage = _run([py, "scripts/public/control/leanmill/vnext_coverage_gate.py", "--run-self-tests"], timeout_s=args.coverage_timeout_s)
    return {"infra_freeze": freeze, "coverage": coverage}


def cycle(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    work_queue.record_worker_heartbeat(
        cx,
        worker_id=f"watchdog:{str(args.policy_profile)}",
        worker_kind="watchdog",
        policy_profile=str(args.policy_profile),
        payload={"policy_profile": str(args.policy_profile)},
    )
    shutdown_marker = Path(args.shutdown_marker)
    if shutdown_marker.exists() and not args.ignore_shutdown_marker:
        expired_reclaimed = work_queue.reclaim_expired(cx, events_path=args.events)
        queue_stats = work_queue.stats(cx)
        open_stats = work_queue.open_stats(cx)
        version_health = work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=str(args.policy_profile))
        marker = _read_json(shutdown_marker)
        status = {
            "schema": "leanmill-watchdog-status-v1",
            "generated_at_epoch": int(time.time()),
            "dry_run": bool(args.dry_run),
            "shutdown_marker_present": True,
            "shutdown_marker": str(shutdown_marker),
            "shutdown_request": marker,
            "actions": [],
            "restart_count": 0,
            "failed_restart_count": 0,
            "queue": queue_stats,
            "open_queue": open_stats,
            "lane_budget_plan": lane_budget_plan(path=FACTORY_POLICY, profile_name=str(args.policy_profile), node_id=os.environ.get("LEANMILL_NODE_ID", "")),
            "worker_version_health": version_health,
            "expired_lease_reclaimed_count": expired_reclaimed,
            "factory_verdict": "shutdown_requested",
            "top_recommendation": {"class": "factory_shutdown_requested", "next_action": "clear shutdown marker before restart"},
            "learning_unit_flow": {},
            "gates": {"infra_freeze": {"skipped": True}, "coverage": {"skipped": True}},
            "intelligence_refresh": {"skipped": True},
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        work_queue.append_event(args.events, {
            "event_type": "leanmill_watchdog_shutdown_marker_seen",
            "payload": {
                "shutdown_marker": str(shutdown_marker),
                "dry_run": bool(args.dry_run),
                "expired_lease_reclaimed_count": expired_reclaimed,
            },
            "artifact_paths": [str(args.out), str(shutdown_marker)],
        })
        return status

    pre_version_health = work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=str(args.policy_profile))
    stale_worker_reasons = _stale_worker_reasons(pre_version_health)
    actions: list[dict[str, Any]] = []
    for session in _sessions(str(args.policy_profile)):
        if _tmux_has_session(session["name"]):
            missing_fragments = _missing_required_process_fragments(session)
            worker_id = str(session.get("worker_id") or "")
            stale_reason = stale_worker_reasons.get(worker_id, "")
            if missing_fragments or stale_reason:
                if _worker_has_running_claim(cx, worker_id):
                    actions.append({
                        "name": session["name"],
                        "role": session["role"],
                        "worker_id": worker_id,
                        "action": "restart_deferred_running_claim",
                        "missing_required_process_fragments": missing_fragments,
                        "stale_reason": stale_reason,
                    })
                else:
                    kill_result = _kill_session(session["name"], dry_run=args.dry_run)
                    start_result = _start_session(session, dry_run=args.dry_run)
                    if start_result.get("action") == "started":
                        if missing_fragments and stale_reason:
                            action = "restarted_for_command_and_runtime_drift"
                        elif missing_fragments:
                            action = "restarted_for_command_drift"
                        else:
                            action = "restarted_for_runtime_drift"
                    else:
                        action = str(start_result.get("action"))
                    start_result.update({
                        "action": action,
                        "worker_id": worker_id,
                        "missing_required_process_fragments": missing_fragments,
                        "stale_reason": stale_reason,
                        "kill_result": kill_result,
                    })
                    actions.append(start_result)
            else:
                actions.append({"name": session["name"], "role": session["role"], "worker_id": worker_id, "action": "alive"})
        else:
            actions.append(_start_session(session, dry_run=args.dry_run))

    intelligence_refresh = _refresh_intelligence(args)
    andon_refresh = _refresh_andon(args)
    gates = _gate_results(args)
    expired_reclaimed = work_queue.reclaim_expired(cx, events_path=args.events)
    version_health = work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=str(args.policy_profile))
    terminated_claims_reclaimed = 0
    if not args.dry_run:
        terminated_claims_reclaimed = work_queue.reclaim_terminated_worker_claims(
            cx,
            version_health=version_health,
            events_path=args.events,
            reason="watchdog_terminated_worker_claim_reclaim",
        )
        if terminated_claims_reclaimed:
            version_health = work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=str(args.policy_profile))
    queue_stats = work_queue.stats(cx)
    open_stats = work_queue.open_stats(cx)
    intelligence = _read_json(DATA_DIR / "leanmill_factory_intelligence.json")
    andon = _read_json(DATA_DIR / "leanmill_andon_cord.json")
    runner = _read_json(DATA_DIR / "leanmill_24x7_status.json")
    status = {
        "schema": "leanmill-watchdog-status-v1",
        "generated_at_epoch": int(time.time()),
        "dry_run": bool(args.dry_run),
        "policy_profile": str(args.policy_profile),
        "actions": actions,
        "restart_count": sum(1 for a in actions if a.get("action") in {"started", "would_start", "restarted_for_command_drift", "restarted_for_runtime_drift", "restarted_for_command_and_runtime_drift"}),
        "failed_restart_count": sum(1 for a in actions if a.get("action") == "start_failed"),
        "queue": queue_stats,
        "open_queue": open_stats,
        "lane_budget_plan": lane_budget_plan(path=FACTORY_POLICY, profile_name=str(args.policy_profile), node_id=os.environ.get("LEANMILL_NODE_ID", "")),
        "worker_version_health": version_health,
        "expired_lease_reclaimed_count": expired_reclaimed,
        "terminated_worker_claim_reclaimed_count": terminated_claims_reclaimed,
        "factory_verdict": intelligence.get("verdict"),
        "top_recommendation": (intelligence.get("recommendations") or [{}])[0],
        "andon_cord": andon,
        "learning_unit_flow": intelligence.get("learning_unit_flow"),
        "runner_external_source_scout_open": runner.get("external_source_scout_open"),
        "runner_external_source_scout_needed": runner.get("external_source_scout_needed"),
        "gates": gates,
        "intelligence_refresh": intelligence_refresh,
        "andon_refresh": andon_refresh,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    work_queue.append_event(args.events, {
        "event_type": "leanmill_watchdog_cycle_finished",
        "payload": {
            "restart_count": status["restart_count"],
            "failed_restart_count": status["failed_restart_count"],
            "open_queue_total": open_stats.get("total"),
            "stale_worker_process_count": version_health.get("stale_process_count"),
            "runtime_mismatch_count": version_health.get("runtime_mismatch_count"),
            "terminated_worker_claim_reclaimed_count": terminated_claims_reclaimed,
            "factory_status": (status.get("factory_verdict") or {}).get("status"),
            "andon_active": bool((status.get("andon_cord") or {}).get("active")),
            "dry_run": bool(args.dry_run),
        },
        "artifact_paths": [str(args.out)],
    })
    return status


def daemon(args: argparse.Namespace) -> dict[str, Any]:
    last: dict[str, Any] = {}
    ticks = 0
    while True:
        last = cycle(args)
        ticks += 1
        if last.get("shutdown_marker_present"):
            break
        if args.max_ticks and ticks >= args.max_ticks:
            break
        time.sleep(max(5, int(args.interval_s)))
    return {"ticks": ticks, "last": last}


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_watchdog_") as td:
        out = Path(td) / "watchdog.json"
        result = cycle(argparse.Namespace(
            dry_run=True,
            out=str(out),
            queue_db=str(Path(td) / "q.sqlite"),
            events=str(Path(td) / "events.jsonl"),
            shutdown_marker=str(Path(td) / "shutdown.json"),
            ignore_shutdown_marker=False,
            command_timeout_s=30,
            coverage_timeout_s=120,
            freeze_window_s=60,
            run_coverage_gate=False,
            policy_profile=DEFAULT_POLICY_PROFILE,
            worker_heartbeat_stale_s=0,
            clear_shutdown_marker=False,
            force_clear_shutdown_marker=False,
        ))
        assert out.exists()
        assert result["schema"] == "leanmill-watchdog-status-v1"
        assert result["lane_budget_plan"]["schema"] == "leanmill-lane-budget-plan-v1"
        assert result["lane_budget_plan"]["queue_model"] == "single_durable_queue_with_policy_lane_budgets"
        assert len(result["actions"]) == len(_sessions(DEFAULT_POLICY_PROFILE))
        assert all(a.get("action") in {"alive", "would_start"} for a in result["actions"])
        assert result["failed_restart_count"] == 0
        assert "terminated_worker_claim_reclaimed_count" in result
        supervised_sessions = _sessions("supervised_24x7")
        assert any(session.get("role") == "source_scout_release" for session in supervised_sessions)
        warm_sessions = [session for session in supervised_sessions if session.get("role") == "general_subscription_agent"]
        assert warm_sessions
        assert all("--claim-patch-mode family_spec_positive_repair" in session.get("cmd", "") for session in warm_sessions)
        assert all("--claim-patch-mode family_spec_positive_repair" in session.get("required_process_fragments", []) for session in warm_sessions)
        old_node = os.environ.get("LEANMILL_NODE_ID")
        try:
            os.environ["LEANMILL_NODE_ID"] = "vps-hetzner-49-13-160-58"
            assert _heavy_lean_slot_count({"heavy_lean_slot_count_by_node": {"vps-hetzner-49-13-160-58": 2}}) == 2
            assert _heavy_lean_lock_arg(1, 2) == "/tmp/rung1/leanmill_heavy_lean.lock"
            assert _heavy_lean_lock_arg(2, 2) == "/tmp/rung1/leanmill_heavy_lean_2.lock"
            assert _heavy_lean_lock_arg(3, 2) == "/tmp/rung1/leanmill_heavy_lean.lock"
        finally:
            if old_node is None:
                os.environ.pop("LEANMILL_NODE_ID", None)
            else:
                os.environ["LEANMILL_NODE_ID"] = old_node
    print("leanmill_watchdog self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--interval-s", type=int, default=300)
    ap.add_argument("--max-ticks", type=int, default=0)
    ap.add_argument("--command-timeout-s", type=int, default=180)
    ap.add_argument("--coverage-timeout-s", type=int, default=600)
    ap.add_argument("--freeze-window-s", type=int, default=21600)
    ap.add_argument("--worker-heartbeat-stale-s", type=int, default=0)
    ap.add_argument("--run-coverage-gate", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--shutdown-marker", default=str(DEFAULT_SHUTDOWN_MARKER))
    ap.add_argument("--policy-profile", default=DEFAULT_POLICY_PROFILE)
    ap.add_argument("--ignore-shutdown-marker", action="store_true")
    ap.add_argument("--clear-shutdown-marker", action="store_true")
    ap.add_argument("--force-clear-shutdown-marker", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.clear_shutdown_marker:
        if not args.force_clear_shutdown_marker:
            raise SystemExit("refusing to clear LeanMill shutdown marker without --force-clear-shutdown-marker")
        p = Path(args.shutdown_marker)
        if p.exists():
            p.unlink()
    if args.self_test:
        return _self_test()
    result = daemon(args) if args.daemon else cycle(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
