#!/usr/bin/env python3
"""Keep LeanMill worker lanes fed with bounded learning-unit WorkItems.

This is a queue shaper, not a proof-value authority. It maintains small
backlog floors for proposal, subscription-agent, and probe lanes by invoking
the existing learning-work seeder with anti-laundering credit boundaries.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import apply_profile_section
from leanmill_paths import FACTORY_POLICY as DEFAULT_FACTORY_POLICY


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/backlog_replenisher_status.json"
DEFAULT_LEARNING_SEED_PLAN = f"{DEFAULT_DATA_DIR}/learning_work_seed_plan.json"
DEFAULT_LEARNING_WORK_SEEDER_SCRIPT = str(Path(__file__).with_name("leanmill_learning_work_seeder.py"))
PROPOSAL_KINDS = {"llm_proposal_validate", "canary_propose", "source_request_propose", "decomposition_propose"}
AGENT_KINDS = {"agent_repair_task", "source_scout_task", "agent_repair", "subscription_agent_task", "agent_task"}
PROBE_KINDS = {"repair_canary_probe"}
REPLENISH_LANES = ("probe_family_spec", "probe_source_shape", "probe", "proposal_agent")


def _display_cmd(cmd: list[str]) -> list[str]:
    if cmd and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return ["<python>", *cmd[1:]]
    return cmd


def _run(cmd: list[str], *, timeout_s: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=max(1, int(timeout_s)))
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": _display_cmd(cmd),
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": _display_cmd(cmd),
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def _read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _normalize_lane_order(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        raw = [str(part).strip() for part in value]
    else:
        raw = []
    order: list[str] = []
    for lane in raw + list(REPLENISH_LANES):
        if lane not in REPLENISH_LANES or lane in order:
            continue
        order.append(lane)
    return order


def _phase_out_path(base: str, index: int, lane: str) -> str:
    p = Path(base)
    suffix = "".join(p.suffixes) or ".json"
    stem = p.name[:-len(suffix)] if p.name.endswith(suffix) else p.stem
    return str(p.with_name(f"{stem}.{index:02d}_{lane}{suffix}"))


def _phase_need_map(lane: str, needs: dict[str, int]) -> dict[str, int]:
    if lane == "proposal_agent":
        return {"proposal": needs.get("proposal", 0), "agent": needs.get("agent", 0)}
    return {lane: needs.get(lane, 0)}


def _seed_command(args: argparse.Namespace, *, run_id: str, out: str, needs: dict[str, int]) -> list[str]:
    overgenerate = max(1, int(args.overgenerate_factor))
    needed_total = sum(max(0, int(v or 0)) for v in needs.values())
    source_probe_need = max(int(needs.get("probe") or 0), int(needs.get("probe_source_shape") or 0))
    cmd = [
        sys.executable,
        args.learning_work_seeder_script,
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--out", out,
        "--run-id", run_id,
        "--enqueue",
        "--terminal-family-cooldown-s", str(args.terminal_family_cooldown_s),
        "--terminal-proposal-family-cooldown-s", str(args.terminal_proposal_family_cooldown_s),
        "--terminal-agent-family-cooldown-s", str(args.terminal_agent_family_cooldown_s),
        "--terminal-probe-signature-cooldown-s", str(args.terminal_probe_signature_cooldown_s),
        "--probe-command-timeout-s", str(args.probe_command_timeout_s),
        "--probe-command-timeout-overhead-s", str(args.probe_command_timeout_overhead_s),
        "--factory-policy", args.factory_policy,
        "--policy-profile", args.policy_profile,
        "--max-total-jobs", str(max(needed_total * overgenerate, 1)),
        "--max-enqueued", str(max(needed_total, 1)),
        "--max-probe-families", str(source_probe_need * overgenerate),
        "--max-family-spec-probe-families", str(int(needs.get("probe_family_spec") or 0) * overgenerate),
        "--max-proposal-jobs", str(int(needs.get("proposal") or 0) * overgenerate),
        "--max-agent-jobs", str(int(needs.get("agent") or 0) * overgenerate),
        "--max-family-spec-repair-jobs", str(int(needs.get("probe_family_spec") or 0) * overgenerate),
        "--max-family-spec-generality-jobs", str(int(needs.get("probe_family_spec") or 0) * max(1, overgenerate // 3)),
        "--agent-runtime", args.agent_runtime,
    ]
    if args.warm_repl_inline:
        cmd.append("--warm-repl-inline")
    if args.govern_winners:
        cmd.append("--govern-winners")
    return cmd


def _combine_seed_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    skip_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    enqueued_jobs: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    for payload in payloads:
        skip_counts.update({str(k): int(v or 0) for k, v in (payload.get("skip_counts") or {}).items()})
        bucket_counts.update({str(k): int(v or 0) for k, v in (payload.get("bucket_counts") or {}).items()})
        enqueued_jobs.extend([j for j in (payload.get("enqueued_jobs") or []) if isinstance(j, dict)])
        jobs.extend([j for j in (payload.get("jobs") or []) if isinstance(j, dict)])
    return {
        "schema": "leanmill-learning-work-seed-plan-aggregate-v1",
        "generated_at_epoch": int(time.time()),
        "phase_count": len(payloads),
        "job_count": sum(int(payload.get("job_count") or 0) for payload in payloads),
        "enqueued": sum(int(payload.get("enqueued") or 0) for payload in payloads),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "skip_counts": dict(sorted(skip_counts.items())),
        "enqueued_jobs": enqueued_jobs,
        "jobs": jobs,
        "anti_laundering_rule": "Seeder emits bounded work only; proof value requires Governance Gate artifacts.",
    }


def _open_counts(cx: Any) -> dict[str, int]:
    stats = work_queue.open_stats(cx)
    by_kind = stats.get("by_kind") or {}
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE status IN ('queued', 'claimed', 'running') AND kind IN ('repair_canary_probe', 'proof_probe')
        """
    ).fetchall()
    by_probe_lane: dict[str, int] = {}
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        lane = str(payload.get("probe_lane") or payload.get("lane") or "legacy")
        by_probe_lane[lane] = by_probe_lane.get(lane, 0) + 1
    return {
        "proposal": sum(int(by_kind.get(k, 0)) for k in PROPOSAL_KINDS),
        "agent": sum(int(by_kind.get(k, 0)) for k in AGENT_KINDS),
        "probe": sum(int(by_kind.get(k, 0)) for k in PROBE_KINDS),
        "probe_family_spec": by_probe_lane.get("family_spec", 0),
        "probe_source_shape": by_probe_lane.get("source_shape", 0),
        "probe_source_binding": by_probe_lane.get("source_binding", 0),
        "probe_legacy": by_probe_lane.get("legacy", 0),
        "total": int(stats.get("total") or 0),
    }


def _station_placeholders(cx: Any) -> list[dict[str, Any]]:
    rows = cx.execute(
        """
        SELECT work_id, kind, payload_json
        FROM work_items
        WHERE status='queued' AND kind LIKE 'station:%'
        ORDER BY priority DESC, created_at ASC
        LIMIT 20
        """
    ).fetchall()
    out = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        order = payload.get("station_order") or {}
        out.append({
            "work_id": row["work_id"],
            "kind": row["kind"],
            "station": order.get("station"),
            "action": order.get("action"),
            "requires_operator_fill": (order.get("execution") or {}).get("requires_operator_fill") or [],
        })
    return out


def _retire_placeholder(cx: Any, *, events: str, rec: dict[str, Any], replacement: str) -> None:
    work_queue.update_status(
        cx,
        work_id=str(rec["work_id"]),
        status="retired",
        payload_update={
            "exit_kind": "replaced_by_executable_learning_work",
            "replacement": replacement,
            "retired_by": "leanmill_backlog_replenisher",
        },
    )
    work_queue.append_event(events, {
        "event_type": "station_placeholder_retired",
        "work_id": rec["work_id"],
        "payload": {"station": rec.get("station"), "replacement": replacement},
    })


def replenish(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    before = _open_counts(cx)
    need_proposal = max(0, args.proposal_floor - before["proposal"])
    need_agent = max(0, args.agent_floor - before["agent"])
    need_probe = max(0, args.probe_floor - before["probe"]) if args.allow_probe_seed else 0
    need_family_spec_probe = max(0, args.family_spec_probe_floor - before["probe_family_spec"]) if args.allow_probe_seed else 0
    need_source_shape_probe = max(0, args.source_shape_probe_floor - before["probe_source_shape"]) if args.allow_probe_seed else 0
    commands: list[dict[str, Any]] = []
    enqueued = 0
    enqueued_jobs: list[dict[str, Any]] = []
    skipped = {
        "proposal": before["proposal"] >= args.proposal_floor,
        "agent": before["agent"] >= args.agent_floor,
        "probe": (not args.allow_probe_seed) or before["probe"] >= args.probe_floor,
        "probe_family_spec": (not args.allow_probe_seed) or before["probe_family_spec"] >= args.family_spec_probe_floor,
        "probe_source_shape": (not args.allow_probe_seed) or before["probe_source_shape"] >= args.source_shape_probe_floor,
    }
    if need_proposal or need_agent or need_probe or need_family_spec_probe or need_source_shape_probe:
        run_id = args.run_id or str(int(time.time()))
        needs = {
            "proposal": need_proposal,
            "agent": need_agent,
            "probe": need_probe,
            "probe_family_spec": need_family_spec_probe,
            "probe_source_shape": need_source_shape_probe,
        }
        phase_payloads: list[dict[str, Any]] = []
        for index, lane in enumerate(_normalize_lane_order(args.replenish_lane_order), start=1):
            phase_needs = {k: v for k, v in _phase_need_map(lane, needs).items() if int(v or 0) > 0}
            if not phase_needs:
                continue
            phase_out = _phase_out_path(args.learning_seed_plan, index, lane)
            cmd = _seed_command(args, run_id=f"{run_id}_{lane}", out=phase_out, needs=phase_needs)
            result = _run(cmd, timeout_s=args.command_timeout_s)
            result["replenish_phase"] = {"lane": lane, "needs": phase_needs, "out": phase_out}
            commands.append(result)
            parsed = _read_json(phase_out)
            phase_payloads.append(parsed)
            enqueued += int(parsed.get("enqueued") or 0)
            enqueued_jobs.extend([j for j in (parsed.get("enqueued_jobs") or []) if isinstance(j, dict)])
        aggregate = _combine_seed_payloads(phase_payloads)
        Path(args.learning_seed_plan).parent.mkdir(parents=True, exist_ok=True)
        Path(args.learning_seed_plan).write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
    placeholders = _station_placeholders(cx)
    retired_placeholders = 0
    if args.retire_replaced_station_placeholders and enqueued:
        kinds = {str(job.get("kind") or "") for job in enqueued_jobs}
        for rec in placeholders:
            station = str(rec.get("station") or "")
            has_replacement = (
                (station == "residual_curriculum" and bool(kinds & {"repair_canary_probe", "source_request_propose", "decomposition_propose", "llm_proposal_validate"}))
                or (station == "repair_registry" and bool(kinds & {"agent_repair_task", "source_scout_task"}))
                or (station == "source_qualification" and "source_scout_task" in kinds)
            )
            if has_replacement:
                _retire_placeholder(cx, events=args.events, rec=rec, replacement=args.learning_seed_plan)
                retired_placeholders += 1
    after = _open_counts(cx)
    learning_seed_payload = _read_json(args.learning_seed_plan)
    seed_skip_counts = learning_seed_payload.get("skip_counts") or {}
    if not isinstance(seed_skip_counts, dict):
        seed_skip_counts = {}
    unmet = {
        "proposal": max(0, args.proposal_floor - after["proposal"]),
        "agent": max(0, args.agent_floor - after["agent"]),
        "probe": max(0, (args.probe_floor if args.allow_probe_seed else 0) - after["probe"]),
        "probe_family_spec": max(0, (args.family_spec_probe_floor if args.allow_probe_seed else 0) - after["probe_family_spec"]),
        "probe_source_shape": max(0, (args.source_shape_probe_floor if args.allow_probe_seed else 0) - after["probe_source_shape"]),
    }
    duplicate_blockers = {
        key: int(seed_skip_counts.get(key) or 0)
        for key in (
            "recent_terminal_same_probe_signature",
            "open_same_probe_signature",
            "recent_terminal_same_replenish_group",
            "open_same_replenish_group",
            "recent_terminal_same_family_kind",
            "open_same_family_kind",
        )
    }
    starvation_reason = ""
    if any(unmet.values()):
        if duplicate_blockers.get("recent_terminal_same_probe_signature") or duplicate_blockers.get("open_same_probe_signature"):
            starvation_reason = "proof_candidate_pool_blocked_by_duplicate_probe_signatures"
        elif duplicate_blockers.get("recent_terminal_same_replenish_group") or duplicate_blockers.get("open_same_replenish_group"):
            starvation_reason = "candidate_pool_blocked_by_open_or_recent_replenish_groups"
        elif duplicate_blockers.get("recent_terminal_same_family_kind") or duplicate_blockers.get("open_same_family_kind"):
            starvation_reason = "candidate_pool_blocked_by_family_kind_cooldown"
        elif commands:
            starvation_reason = "seeder_returned_no_eligible_candidates"
    payload = {
        "schema": "leanmill-backlog-replenisher-status-v1",
        "generated_at_epoch": int(time.time()),
        "before": before,
        "after": after,
        "floors": {
            "proposal": args.proposal_floor,
            "agent": args.agent_floor,
            "probe": args.probe_floor if args.allow_probe_seed else 0,
            "probe_family_spec": args.family_spec_probe_floor if args.allow_probe_seed else 0,
            "probe_source_shape": args.source_shape_probe_floor if args.allow_probe_seed else 0,
        },
        "needed": {
            "proposal": need_proposal,
            "agent": need_agent,
            "probe": need_probe,
            "probe_family_spec": need_family_spec_probe,
            "probe_source_shape": need_source_shape_probe,
        },
        "unmet_after_replenish": unmet,
        "candidate_pool": {
            "overgenerate_factor": int(args.overgenerate_factor),
            "replenish_lane_order": _normalize_lane_order(args.replenish_lane_order),
            "seed_job_count": int(learning_seed_payload.get("job_count") or 0),
            "seed_skip_counts": seed_skip_counts,
            "duplicate_blockers": duplicate_blockers,
            "starvation_reason": starvation_reason,
        },
        "enqueued": enqueued,
        "enqueued_jobs": enqueued_jobs,
        "skipped": skipped,
        "retired_station_placeholders": retired_placeholders,
        "commands": commands,
        "anti_laundering_rule": "Replenisher emits work only; Governance Gate remains the only proof-credit authority.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    work_queue.append_event(args.events, {
        "event_type": "leanmill_backlog_replenished",
        "payload": {
            "before": before,
            "after": after,
            "floors": payload["floors"],
            "enqueued": enqueued,
            "unmet_after_replenish": unmet,
            "starvation_reason": starvation_reason,
            "retired_station_placeholders": retired_placeholders,
        },
        "artifact_paths": [args.out, args.learning_seed_plan],
    })
    return payload


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "q.sqlite")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="source_request_propose", priority=1, payload={"work_id": "p"})
        counts = _open_counts(cx)
        assert counts["proposal"] == 1
        args = argparse.Namespace(
            queue_db=db,
            events=str(Path(td) / "events.jsonl"),
            learning_seed_plan=str(Path(td) / "seed.json"),
            learning_work_seeder_script=DEFAULT_LEARNING_WORK_SEEDER_SCRIPT,
            run_id="selftest",
            proposal_floor=1,
            agent_floor=0,
            probe_floor=0,
            family_spec_probe_floor=0,
            source_shape_probe_floor=0,
            allow_probe_seed=True,
            replenish_lane_order=["probe_family_spec", "proposal_agent"],
            overgenerate_factor=7,
            out=str(Path(td) / "status.json"),
            retire_replaced_station_placeholders=True,
            factory_policy=str(Path(td) / "policy.json"),
            policy_profile="",
            agent_runtime="codex",
            max_family_spec_repair_jobs=0,
            max_family_spec_generality_jobs=0,
            terminal_family_cooldown_s=3600,
            terminal_proposal_family_cooldown_s=900,
            terminal_agent_family_cooldown_s=900,
            terminal_probe_signature_cooldown_s=21600,
            probe_command_timeout_s=900,
            probe_command_timeout_overhead_s=120,
            warm_repl_inline=False,
            govern_winners=False,
            command_timeout_s=1,
        )
        Path(args.learning_seed_plan).write_text(json.dumps({
            "job_count": 0,
            "skip_counts": {"recent_terminal_same_probe_signature": 2},
        }) + "\n")
        before = {"proposal": 0, "agent": 0, "probe": 0, "probe_family_spec": 0, "probe_source_shape": 0, "total": 0}
        # Exercise the receipt-shaping logic without launching the seeder.
        seed = _read_json(args.learning_seed_plan)
        assert seed["skip_counts"]["recent_terminal_same_probe_signature"] == 2
        assert _normalize_lane_order(["probe_family_spec", "proposal_agent"])[:2] == ["probe_family_spec", "proposal_agent"]
        cmd = _seed_command(
            args,
            run_id="phase",
            out=str(Path(td) / "phase.json"),
            needs={"probe_family_spec": 2},
        )
        assert "--max-family-spec-probe-families" in cmd
        assert cmd[cmd.index("--max-enqueued") + 1] == "2"
        assert cmd[cmd.index("--max-proposal-jobs") + 1] == "0"
        assert cmd[cmd.index("--max-agent-jobs") + 1] == "0"
        assert cmd[cmd.index("--max-family-spec-repair-jobs") + 1] == "14"
        assert cmd[cmd.index("--max-family-spec-generality-jobs") + 1] == "4"
    print("leanmill_backlog_replenisher self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--learning-seed-plan", default=DEFAULT_LEARNING_SEED_PLAN)
    ap.add_argument("--learning-work-seeder-script", default=DEFAULT_LEARNING_WORK_SEEDER_SCRIPT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--proposal-floor", type=int, default=3)
    ap.add_argument("--agent-floor", type=int, default=3)
    ap.add_argument("--probe-floor", type=int, default=2)
    ap.add_argument("--family-spec-probe-floor", type=int, default=1)
    ap.add_argument("--source-shape-probe-floor", type=int, default=1)
    ap.add_argument("--allow-probe-seed", action="store_true")
    ap.add_argument("--agent-runtime", choices=["codex", "claude"], default="codex")
    ap.add_argument("--terminal-family-cooldown-s", type=int, default=3600)
    ap.add_argument("--terminal-proposal-family-cooldown-s", type=int, default=900)
    ap.add_argument("--terminal-agent-family-cooldown-s", type=int, default=900)
    ap.add_argument("--terminal-probe-signature-cooldown-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--overgenerate-factor", type=int, default=3)
    ap.add_argument("--replenish-lane-order", default="probe_family_spec,probe_source_shape,probe,proposal_agent")
    ap.add_argument("--probe-command-timeout-s", type=int, default=900)
    ap.add_argument("--probe-command-timeout-overhead-s", type=int, default=120)
    ap.add_argument("--warm-repl-inline", action="store_true")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--retire-replaced-station-placeholders", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--command-timeout-s", type=int, default=180)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="backlog_replenisher")
    payload = replenish(args)
    print(json.dumps({
        "before": payload["before"],
        "after": payload["after"],
        "enqueued": payload["enqueued"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
