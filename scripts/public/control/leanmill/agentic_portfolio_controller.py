#!/usr/bin/env python3
"""Policy-owned agentic generation portfolio for LeanMill.

This controller does not create proof or C credit. It decides which existing
agentic generation lanes should get the next bounded spend, then lets the
ordinary deterministic static/probe/governance lanes decide what survives.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from leanmill_factory_config import FACTORY_POLICY, read_policy
from leanmill_paths import DATA_DIR
import leanmill_work_queue as work_queue


DEFAULT_OUT = f"{DATA_DIR}/agentic_portfolio_controller.json"
DEFAULT_FACTORY_INTELLIGENCE = f"{DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_C_SUPPLY_GROWTH = f"{DATA_DIR}/c_supply_growth_controller.json"
DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json"
DEFAULT_SOURCE_SEARCH_INTEGRATIONS = f"{DATA_DIR}/source_search_integrations"
DEFAULT_SOURCE_BINDING_INGEST = f"{DATA_DIR}/source_binding_ingestion_status.json"
DEFAULT_AGENT_OUTPUT_INGEST = f"{DATA_DIR}/agent_output_ingestion_status.json"
DEFAULT_ANDON = f"{DATA_DIR}/leanmill_andon_cord.json"
DEFAULT_SPEC_DIR = "analytics/public/leanmill/repair_families"
SOURCE_SEARCH_INTEGRATOR_RETRY_VERSION = "family_spec_seed_rows_v1"


DEFAULT_POLICY: dict[str, Any] = {
    "enabled": False,
    "max_actions_per_cycle": 2,
    "command_timeout_s": 900,
    "preflight_enabled": True,
    "preflight_timeout_s": 120,
    "lane_order": [
        "source_request_generation",
        "source_to_target_binding",
        "template_family_generation",
        "family_birth_generation",
        "proof_proposal_generation",
    ],
    "lanes": {
        "source_request_generation": {"enabled": True, "open_floor": 4, "max_enqueued": 1},
        "source_to_target_binding": {"enabled": True, "max_runs": 1, "max_ingest": 1},
        "template_family_generation": {"enabled": True, "max_enqueued": 1, "max_jobs": 1, "rows_per_family": 2},
        "family_birth_generation": {"enabled": True, "max_enqueued": 1, "min_pressure_rows": 1},
        "proof_proposal_generation": {"enabled": True, "open_floor": 8, "max_total_jobs": 1, "max_proposal_jobs": 1},
    },
}


def _read_json(path: str | Path) -> Any:
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


def _int(obj: dict[str, Any], key: str, fallback: int = 0) -> int:
    try:
        return int(obj.get(key) if obj.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return fallback


def _tail(text: str, limit: int = 3000) -> str:
    return text if len(text) <= limit else text[-limit:]


def _run(cmd: list[str], *, timeout_s: int, dry_run: bool = False) -> dict[str, Any]:
    rec: dict[str, Any] = {"cmd": cmd, "timeout_s": timeout_s, "dry_run": dry_run}
    if dry_run:
        rec.update({"returncode": 0, "stdout_tail": "", "stderr_tail": ""})
        return rec
    started = time.time()
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=max(1, int(timeout_s)))
        rec.update({
            "returncode": proc.returncode,
            "wall_time_s": round(time.time() - started, 3),
            "stdout_tail": _tail(proc.stdout or ""),
            "stderr_tail": _tail(proc.stderr or ""),
        })
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        rec.update({
            "returncode": 124,
            "wall_time_s": round(time.time() - started, 3),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": True,
        })
    return rec


def _profile_policy(args: argparse.Namespace) -> dict[str, Any]:
    policy = read_policy(args.factory_policy)
    profile = ((policy.get("profiles") or {}).get(args.policy_profile) or {}) if args.policy_profile else {}
    raw = profile.get("agentic_portfolio_controller") if isinstance(profile, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    merged = dict(DEFAULT_POLICY)
    for key, value in raw.items():
        if key == "lanes" and isinstance(value, dict):
            lanes = {k: dict(v) for k, v in DEFAULT_POLICY["lanes"].items()}
            for lane, lane_policy in value.items():
                base = dict(lanes.get(lane, {}))
                if isinstance(lane_policy, dict):
                    base.update(lane_policy)
                lanes[lane] = base
            merged["lanes"] = lanes
        else:
            merged[key] = value
    return merged


def _open_queue(args: argparse.Namespace) -> dict[str, Any]:
    try:
        cx = work_queue.connect(args.queue_db)
        return work_queue.open_stats(cx)
    except Exception as exc:
        return {"error": str(exc), "by_status": {}, "by_kind": {}, "by_lane": {}, "total": 0}


def _claimable_source_search_integration_count(args: argparse.Namespace) -> int:
    try:
        cx = work_queue.connect(args.queue_db)
        row = cx.execute(
            """
            SELECT COUNT(*) AS n
            FROM work_items
            WHERE kind='source_search_task'
              AND (
                (status='done' AND json_extract(payload_json, '$.source_search_integrated_at_epoch') IS NULL)
                OR (
                  status='done'
                  AND json_extract(payload_json, '$.exit_kind')='source_search_integrated_hold'
                  AND COALESCE(json_extract(payload_json, '$.source_search_integration_retry_version'), '') != ?
                )
              )
            """,
            (SOURCE_SEARCH_INTEGRATOR_RETRY_VERSION,),
        ).fetchone()
        cx.close()
        return int(row["n"] if row is not None else 0)
    except Exception:
        return 0


def _growth_metrics(growth: dict[str, Any]) -> dict[str, Any]:
    for key in ("latest_metrics", "final_metrics", "best_metrics"):
        val = growth.get(key)
        if isinstance(val, dict):
            return val
    return {}


def _path_from_growth(growth: dict[str, Any], key: str, fallback: str) -> str:
    val = str(growth.get(key) or "")
    return val if val and Path(val).exists() else fallback


def _recommendation_classes(factory: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for rec in factory.get("recommendations") or []:
        if isinstance(rec, dict) and str(rec.get("class") or ""):
            out.add(str(rec.get("class") or ""))
    return out


def _action_impact(factory: dict[str, Any], action_id: str) -> dict[str, Any]:
    for row in factory.get("action_impact_records") or []:
        if isinstance(row, dict) and str(row.get("action_id") or "") == action_id:
            outcome = row.get("observed_outcome")
            return outcome if isinstance(outcome, dict) else {}
    return {}


def _proposal_open_count(open_queue: dict[str, Any]) -> int:
    by_kind = open_queue.get("by_kind") if isinstance(open_queue.get("by_kind"), dict) else {}
    return sum(int(by_kind.get(kind) or 0) for kind in ("llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"))


def _andon_pauses(args: argparse.Namespace) -> dict[str, bool]:
    obj = _read_json(args.andon_cord)
    if not isinstance(obj, dict) or not obj.get("andon_active"):
        return {"source_scout": False, "source_binding": False}
    containment = obj.get("containment") if isinstance(obj.get("containment"), dict) else {}
    return {
        "source_scout": bool(containment.get("pause_external_source_scouts")),
        "source_binding": bool(containment.get("pause_source_binding_ingest") or containment.get("pause_source_binding_probes")),
    }


def _build_lane_command(
    args: argparse.Namespace,
    *,
    lane: str,
    lane_policy: dict[str, Any],
    growth: dict[str, Any],
    artifact_dir: Path,
    run_id: str,
) -> list[str]:
    py = sys.executable
    selection = _path_from_growth(growth, "latest_selection", args.selection)
    checkpoint = _path_from_growth(growth, "latest_checkpoint", args.checkpoint)
    row_context = _path_from_growth(growth, "latest_row_context", args.row_context)
    if lane == "source_request_generation":
        return [
            py,
            "scripts/public/control/leanmill/external_source_scout_seeder.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", str(artifact_dir / "source_scout_seed.json"),
            "--run-id", f"{run_id}_source",
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--max-enqueued", str(max(0, _int(lane_policy, "max_enqueued", 1))),
            "--enqueue",
        ]
    if lane == "source_to_target_binding":
        return [
            py,
            "scripts/public/control/leanmill/source_search_integrator.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--worker-id", f"{args.worker_id}-agentic-portfolio-source-binding",
            "--out-dir", args.source_search_integrations,
            "--agent-runtime", str(lane_policy.get("agent_runtime") or "codex"),
        ]
    if lane == "template_family_generation":
        return [
            py,
            "scripts/public/control/leanmill/c_supply_template_backfill.py",
            "--selection", selection,
            "--checkpoint", checkpoint,
            "--row-context", row_context,
            "--spec-dir", args.spec_dir,
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", str(artifact_dir / "template_backfill.json"),
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--run-id", f"{run_id}_template",
            "--max-jobs", str(max(0, _int(lane_policy, "max_jobs", 1))),
            "--rows-per-family", str(max(1, _int(lane_policy, "rows_per_family", 2))),
            "--agent-runtime", str(lane_policy.get("agent_runtime") or "codex"),
            "--agent-max-wall-time-s", str(max(1, _int(lane_policy, "agent_max_wall_time_s", 1800))),
            "--agent-max-iterations", str(max(1, _int(lane_policy, "agent_max_iterations", 3))),
            "--max-enqueued", str(max(0, _int(lane_policy, "max_enqueued", 1))),
            "--cooldown-s", str(max(0, _int(lane_policy, "cooldown_s", 0))),
            "--enqueue",
        ]
    if lane == "family_birth_generation":
        cmd = [
            py,
            "scripts/public/control/leanmill/family_birth_miner.py",
            "--selection", selection,
            "--checkpoint", checkpoint,
            "--row-context", row_context,
            "--spec-dir", args.spec_dir,
            "--out", str(artifact_dir / "family_birth.json"),
            "--md", str(artifact_dir / "family_birth.md"),
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--run-id", f"{run_id}_family_birth",
            "--max-enqueued", str(max(0, _int(lane_policy, "max_enqueued", 1))),
            "--max-clusters", str(max(0, _int(lane_policy, "max_clusters", 20))),
            "--min-rows", str(max(1, _int(lane_policy, "min_rows", 3))),
            "--min-shared-tokens", str(max(1, _int(lane_policy, "min_shared_tokens", 1))),
            "--agent-runtime", str(lane_policy.get("agent_runtime") or "codex"),
            "--agent-max-wall-time-s", str(max(1, _int(lane_policy, "agent_max_wall_time_s", 1800))),
            "--agent-max-iterations", str(max(1, _int(lane_policy, "agent_max_iterations", 3))),
            "--enqueue",
        ]
        if bool(lane_policy.get("include_covered_static_failures", False)):
            cmd.append("--include-covered-static-failures")
        else:
            cmd.append("--no-include-covered-static-failures")
        if bool(lane_policy.get("exclude_existing_family_tokens", True)):
            cmd.append("--exclude-existing-family-tokens")
        return cmd
    if lane == "proof_proposal_generation":
        return [
            py,
            "scripts/public/control/leanmill/learning_work_seeder.py",
            "--queue-db", args.queue_db,
            "--events", args.events,
            "--out", str(artifact_dir / "proof_proposal_seed.json"),
            "--run-id", f"{run_id}_proof_proposal",
            "--agent-runtime", str(lane_policy.get("agent_runtime") or "codex"),
            "--max-total-jobs", str(max(0, _int(lane_policy, "max_total_jobs", 1))),
            "--max-probe-families", "0",
            "--max-family-spec-probe-families", "0",
            "--max-family-spec-repair-jobs", "0",
            "--max-family-spec-generality-jobs", "0",
            "--max-proposal-jobs", str(max(0, _int(lane_policy, "max_proposal_jobs", 1))),
            "--max-agent-jobs", str(max(0, _int(lane_policy, "max_agent_jobs", 0))),
            "--max-enqueued", str(max(0, _int(lane_policy, "max_enqueued", _int(lane_policy, "max_total_jobs", 1)))),
            "--factory-policy", args.factory_policy,
            "--policy-profile", args.policy_profile,
            "--enqueue",
        ]
    raise ValueError(f"unknown lane: {lane}")


def _with_preflight_output(cmd: list[str], *, out_path: Path, md_path: Path | None = None) -> list[str]:
    out = list(cmd)
    if "--enqueue" in out:
        out.remove("--enqueue")
    if "--max-enqueued" in out:
        idx = out.index("--max-enqueued")
        if idx + 1 < len(out):
            out[idx + 1] = "0"
    if "--out" in out:
        idx = out.index("--out")
        if idx + 1 < len(out):
            out[idx + 1] = str(out_path)
    if md_path is not None and "--md" in out:
        idx = out.index("--md")
        if idx + 1 < len(out):
            out[idx + 1] = str(md_path)
    return out


def _lane_preflight(
    args: argparse.Namespace,
    *,
    lane: str,
    lane_policy: dict[str, Any],
    policy: dict[str, Any],
    growth: dict[str, Any],
    artifact_dir: Path,
    run_id: str,
) -> tuple[bool, dict[str, Any]]:
    if not bool(policy.get("preflight_enabled", True)) or lane not in {"template_family_generation", "family_birth_generation"}:
        return True, {"status": "not_required"}
    if bool(args.dry_run):
        return True, {"status": "skipped_dry_run"}
    out_path = artifact_dir / f"{lane}_preflight.json"
    md_path = artifact_dir / f"{lane}_preflight.md" if lane == "family_birth_generation" else None
    cmd = _with_preflight_output(
        _build_lane_command(args, lane=lane, lane_policy=lane_policy, growth=growth, artifact_dir=artifact_dir, run_id=f"{run_id}_preflight"),
        out_path=out_path,
        md_path=md_path,
    )
    rec = _run(cmd, timeout_s=max(1, _int(policy, "preflight_timeout_s", 120)), dry_run=False)
    preflight: dict[str, Any] = {
        "status": "ran",
        "lane": lane,
        "cmd": rec.get("cmd"),
        "returncode": rec.get("returncode"),
        "wall_time_s": rec.get("wall_time_s"),
        "stdout_tail": rec.get("stdout_tail"),
        "stderr_tail": rec.get("stderr_tail"),
        "out": str(out_path),
    }
    if int(rec.get("returncode") or 0) != 0:
        preflight["admitted"] = False
        preflight["reason"] = "preflight_command_failed"
        return False, preflight
    payload = _read_json(out_path)
    if not isinstance(payload, dict):
        preflight["admitted"] = False
        preflight["reason"] = "preflight_output_missing_or_invalid"
        return False, preflight
    if lane == "template_family_generation":
        job_count = _int(payload, "job_count", 0)
        preflight.update({
            "job_count": job_count,
            "candidate_family_count": _int(payload, "candidate_family_count", 0),
            "strict_static_fail_row_count": _int(payload, "strict_static_fail_row_count", 0),
            "static_outcome_row_count": _int(payload, "static_outcome_row_count", 0),
            "candidate_counts_by_family": payload.get("candidate_counts_by_family") or {},
        })
        if job_count <= 0:
            preflight["admitted"] = False
            preflight["reason"] = "preflight_no_template_jobs"
            return False, preflight
        preflight["admitted"] = True
        preflight["reason"] = "preflight_template_jobs_available"
        return True, preflight
    if lane == "family_birth_generation":
        cluster_count = _int(payload, "cluster_count", 0)
        preflight.update({
            "cluster_count": cluster_count,
            "candidate_static_fail_row_count": _int(payload, "candidate_static_fail_row_count", 0),
            "birth_pressure_row_count": _int(payload, "birth_pressure_row_count", 0),
            "thresholds": payload.get("thresholds") or {},
        })
        if cluster_count <= 0:
            preflight["admitted"] = False
            preflight["reason"] = "preflight_no_family_birth_clusters"
            return False, preflight
        preflight["admitted"] = True
        preflight["reason"] = "preflight_family_birth_clusters_available"
        return True, preflight
    return True, preflight


def _should_run_lane(
    *,
    lane: str,
    lane_policy: dict[str, Any],
    metrics: dict[str, Any],
    factory: dict[str, Any],
    open_queue: dict[str, Any],
    pauses: dict[str, bool],
    claimable_source_integrations: int,
) -> tuple[bool, str]:
    blockers = metrics.get("blockers_by_reason") if isinstance(metrics.get("blockers_by_reason"), dict) else {}
    recs = _recommendation_classes(factory)
    by_lane = open_queue.get("by_lane") if isinstance(open_queue.get("by_lane"), dict) else {}
    by_kind = open_queue.get("by_kind") if isinstance(open_queue.get("by_kind"), dict) else {}
    credit_ready = _int(metrics, "credit_ready_count", 0)
    source_demand_families = _int(metrics, "source_demand_family_count", 0)
    if lane == "source_request_generation":
        if pauses.get("source_scout"):
            return False, "andon_pause_source_scout"
        open_floor = max(0, _int(lane_policy, "open_floor", 4))
        if int(by_lane.get("source_scout") or 0) >= open_floor:
            return False, "source_scout_open_floor_satisfied"
        if credit_ready <= 0 or source_demand_families < max(1, _int(lane_policy, "target_source_demand_families", 8)):
            return True, "strict_c_or_source_family_gap"
        return False, "source_request_generation_not_current_bottleneck"
    if lane == "source_to_target_binding":
        if pauses.get("source_binding"):
            return False, "andon_pause_source_binding"
        if int(claimable_source_integrations) > 0:
            return True, "claimable_source_search_integration_ready"
        if int(by_kind.get("source_search_task") or 0) > 0:
            return False, "source_search_tasks_open_wait_for_search_worker"
        impact = _action_impact(factory, "leanmill.source_search_to_binding")
        if _int(impact, "source_search_holds_with_ready_candidates", 0) > 0:
            return False, "source_search_ready_holds_blocked_not_claimable"
        return False, "no_source_search_binding_pressure"
    if lane == "template_family_generation":
        if _int(blockers, "no_positive_family_template", 0) > 0 or _int(metrics, "probe_seedable_count", 0) > 0:
            return True, "template_or_probe_seedable_gap"
        return False, "no_template_generation_pressure"
    if lane == "family_birth_generation":
        pressure = _int(blockers, "no_positive_family_template", 0)
        if pressure >= max(1, _int(lane_policy, "min_pressure_rows", 1)):
            return True, "no_positive_family_template_pressure"
        return False, "family_birth_pressure_below_policy_floor"
    if lane == "proof_proposal_generation":
        if _proposal_open_count(open_queue) >= max(0, _int(lane_policy, "open_floor", 8)):
            return False, "proposal_open_floor_satisfied"
        if "proof_candidate_supply_blocked" in recs or "route_c_gap_task_execution_ready" in recs:
            return True, "proof_candidate_supply_or_route_c_gap_pressure"
        return False, "proof_proposal_generation_not_current_bottleneck"
    return False, "unknown_lane"


def build(args: argparse.Namespace) -> dict[str, Any]:
    policy = _profile_policy(args)
    factory = _read_json(args.factory_intelligence) or {}
    growth = _read_json(args.c_supply_growth) or {}
    metrics = _growth_metrics(growth if isinstance(growth, dict) else {})
    open_queue = _open_queue(args)
    pauses = _andon_pauses(args)
    claimable_source_integrations = _claimable_source_search_integration_count(args)
    run_id = str(args.run_id or f"agentic_portfolio_{int(time.time())}")
    artifact_dir = Path(args.out).with_suffix("")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    commands: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    if not bool(policy.get("enabled", False)):
        result = {
            "schema": "leanmill-agentic-portfolio-controller-v1",
            "status": "skipped",
            "reason": "disabled_by_policy",
            "policy_profile": args.policy_profile,
            "credit_boundary": "no_credit_generation_routing_only",
            "policy": policy,
        }
        if args.out:
            _write_json(args.out, result)
        return result

    max_actions = max(0, _int(policy, "max_actions_per_cycle", 2))
    lanes = policy.get("lanes") if isinstance(policy.get("lanes"), dict) else {}
    lane_order = [str(x) for x in (policy.get("lane_order") or DEFAULT_POLICY["lane_order"]) if str(x)]
    for lane in lane_order:
        lane_policy = lanes.get(lane) if isinstance(lanes.get(lane), dict) else {}
        if not bool(lane_policy.get("enabled", True)):
            decisions.append({"lane": lane, "run": False, "reason": "lane_disabled"})
            continue
        should_run, reason = _should_run_lane(
            lane=lane,
            lane_policy=lane_policy,
            metrics=metrics,
            factory=factory if isinstance(factory, dict) else {},
            open_queue=open_queue,
            pauses=pauses,
            claimable_source_integrations=claimable_source_integrations,
        )
        if not should_run:
            decisions.append({"lane": lane, "run": False, "reason": reason})
            continue
        if max_actions and len(commands) >= max_actions:
            decisions.append({"lane": lane, "run": False, "reason": "max_actions_per_cycle_reached"})
            continue
        admitted, preflight = _lane_preflight(
            args,
            lane=lane,
            lane_policy=lane_policy,
            policy=policy,
            growth=growth if isinstance(growth, dict) else {},
            artifact_dir=artifact_dir,
            run_id=run_id,
        )
        if not admitted:
            decisions.append({"lane": lane, "run": False, "reason": str(preflight.get("reason") or "preflight_blocked"), "pressure_reason": reason, "preflight": preflight})
            continue
        cmd = _build_lane_command(args, lane=lane, lane_policy=lane_policy, growth=growth if isinstance(growth, dict) else {}, artifact_dir=artifact_dir, run_id=run_id)
        rec = _run(cmd, timeout_s=max(1, _int(policy, "command_timeout_s", args.command_timeout_s)), dry_run=bool(args.dry_run))
        rec["lane"] = lane
        rec["reason"] = reason
        rec["preflight"] = preflight
        commands.append(rec)
        decisions.append({"lane": lane, "run": True, "reason": reason, "returncode": rec.get("returncode")})

    result = {
        "schema": "leanmill-agentic-portfolio-controller-v1",
        "generated_at_epoch": int(time.time()),
        "status": "ran",
        "policy_profile": args.policy_profile,
        "run_id": run_id,
        "credit_boundary": "Agentic portfolio dispatch creates generation work only; deterministic static/probe/governance gates decide all proof, benchmark, governance, and C credit.",
        "policy": policy,
        "metrics": metrics,
        "open_queue": open_queue,
        "claimable_source_search_integration_count": claimable_source_integrations,
        "andon_pauses": pauses,
        "decisions": decisions,
        "commands": commands,
        "command_count": len(commands),
        "failed_command_count": sum(1 for c in commands if int(c.get("returncode") or 0) != 0),
    }
    if args.out:
        _write_json(args.out, result)
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_agentic_portfolio_") as td:
        root = Path(td)
        policy = root / "policy.json"
        policy.write_text(json.dumps({
            "profiles": {
                "unit": {
                    "agentic_portfolio_controller": {
                        "enabled": True,
                        "max_actions_per_cycle": 3,
                        "command_timeout_s": 1,
                        "lanes": {
                            "source_request_generation": {"enabled": True, "open_floor": 1, "max_enqueued": 1},
                            "template_family_generation": {"enabled": True, "max_enqueued": 1},
                            "proof_proposal_generation": {"enabled": True, "open_floor": 1, "max_total_jobs": 1},
                        },
                    }
                }
            }
        }) + "\n")
        growth = root / "growth.json"
        growth.write_text(json.dumps({
            "latest_metrics": {
                "credit_ready_count": 0,
                "source_demand_family_count": 0,
                "probe_seedable_count": 1,
                "blockers_by_reason": {"no_positive_family_template": 4},
            }
        }) + "\n")
        factory = root / "fi.json"
        factory.write_text(json.dumps({
            "recommendations": [{"class": "proof_candidate_supply_blocked"}],
            "action_impact_records": [{"action_id": "leanmill.source_search_to_binding", "observed_outcome": {"source_search_holds_with_ready_candidates": 2}}],
        }) + "\n")
        q = root / "q.sqlite"
        cx = work_queue.connect(q)
        wid = work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "family": "fam",
            "ok": True,
            "work_id": "source_search:fam:unit",
        })
        work_queue.update_status(cx, work_id=wid, status="done", payload_update={"ok": True})
        cx.close()
        result = build(argparse.Namespace(
            queue_db=str(q),
            events=str(root / "events.jsonl"),
            factory_intelligence=str(factory),
            c_supply_growth=str(growth),
            selection=str(root / "sel.json"),
            checkpoint=str(root / "ck.jsonl"),
            row_context=str(root / "rows.json"),
            spec_dir=str(root / "specs"),
            source_search_integrations=str(root / "integrations"),
            source_binding_ingest_out=str(root / "binding.json"),
            agent_output_ingest_out=str(root / "agent_ingest.json"),
            andon_cord=str(root / "missing_andon.json"),
            factory_policy=str(policy),
            policy_profile="unit",
            worker_id="w",
            out=str(root / "out.json"),
            command_timeout_s=1,
            run_id="unit",
            dry_run=True,
        ))
        ran = [d["lane"] for d in result["decisions"] if d.get("run")]
        assert "source_request_generation" in ran, result
        assert "template_family_generation" in ran, result
        assert result["command_count"] == 3, result
        assert result["credit_boundary"].startswith("Agentic portfolio dispatch"), result
    print("leanmill_agentic_portfolio_controller self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=f"{DATA_DIR}/leanmill_work_queue.sqlite")
    ap.add_argument("--events", default=f"{DATA_DIR}/leanmill_events.jsonl")
    ap.add_argument("--factory-intelligence", default=DEFAULT_FACTORY_INTELLIGENCE)
    ap.add_argument("--c-supply-growth", default=DEFAULT_C_SUPPLY_GROWTH)
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--source-search-integrations", default=DEFAULT_SOURCE_SEARCH_INTEGRATIONS)
    ap.add_argument("--source-binding-ingest-out", default=DEFAULT_SOURCE_BINDING_INGEST)
    ap.add_argument("--agent-output-ingest-out", default=DEFAULT_AGENT_OUTPUT_INGEST)
    ap.add_argument("--andon-cord", default=DEFAULT_ANDON)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--worker-id", default="leanmill-agentic-portfolio")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--command-timeout-s", type=int, default=900)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({
        "status": result.get("status"),
        "command_count": result.get("command_count", 0),
        "decisions": result.get("decisions", [])[:8],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
