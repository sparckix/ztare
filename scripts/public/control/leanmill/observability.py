#!/usr/bin/env python3
"""Central LeanMill observability report over queue, events, and artifacts."""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_paths import FACTORY_POLICY as DEFAULT_FACTORY_POLICY


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/leanmill_observability.json"
DEFAULT_MD = f"{DEFAULT_DATA_DIR}/leanmill_observability.md"
DEFAULT_RUNNER_STATUS = f"{DEFAULT_DATA_DIR}/leanmill_24x7_status.json"


def _now() -> int:
    return int(time.time())


def _read_json(path: str | Path | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _observability_policy(path: str | Path | None) -> dict[str, Any]:
    policy = _read_json(path)
    if not isinstance(policy, dict):
        policy = {}
    obj = policy.get("observability") or {}
    if not isinstance(obj, dict):
        obj = {}

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    return {
        "dead_letter_root_cause_window_s": max(1, int_value("dead_letter_root_cause_window_s", 3600)),
        "runner_status_stale_after_s": max(1, int_value("runner_status_stale_after_s", 6 * 60 * 60)),
    }


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


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


def _int_count(obj: dict[str, Any], key: str) -> int:
    try:
        return int(obj.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


def _queue_rows(cx: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(cx.execute("SELECT * FROM work_items ORDER BY updated_at DESC").fetchall())


def _status_counts(rows: list[sqlite3.Row]) -> dict[str, int]:
    counts = Counter(str(row["status"]) for row in rows)
    return dict(sorted(counts.items()))


def _kind_status_counts(rows: list[sqlite3.Row]) -> dict[str, dict[str, int]]:
    nested: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        nested[str(row["kind"])][str(row["status"])] += 1
    return {kind: dict(sorted(counter.items())) for kind, counter in sorted(nested.items())}


def _recent_terminal_failures(rows: list[sqlite3.Row], *, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["status"] not in {"failed", "dead_letter", "retired"}:
            continue
        payload = _payload(row)
        reasons = []
        for key in (
            "exit_kind",
            "reason",
            "failure_class",
            "source_binding_ingest_status",
            "source_binding_failures",
            "source_search_integration_skipped_reason",
            "llm_proposal_status",
        ):
            value = payload.get(key)
            if value not in (None, "", []):
                reasons.append({key: value})
        quality = [
            q for q in payload.get("query_quality") or []
            if isinstance(q, dict) and not bool(q.get("accepted", True))
        ]
        if quality:
            reasons.append({"query_quality_failures": quality[:3]})
        out.append({
            "work_id": row["work_id"],
            "kind": row["kind"],
            "family": row["family"] or payload.get("family") or "",
            "status": row["status"],
            "updated_at": row["updated_at"],
            "reasons": reasons[:6],
        })
        if len(out) >= limit:
            break
    return out


def _source_search_summary(rows: list[sqlite3.Row]) -> dict[str, Any]:
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    low_quality: dict[str, int] = defaultdict(int)
    qualified_ready: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["kind"] != "source_search_task":
            continue
        payload = _payload(row)
        family = str(row["family"] or payload.get("family") or "unknown_family")
        status = str(row["status"])
        exit_kind = str(payload.get("exit_kind") or status)
        by_family[family][exit_kind] += 1
        if exit_kind == "source_search_rejected_low_quality_queries":
            low_quality[family] += 1
        static_summary = payload.get("static_summary") or {}
        ready = int(static_summary.get("canary_ready_total") or 0)
        if ready:
            qualified_ready[family] += ready
    return {
        "by_family_exit": {fam: dict(counter) for fam, counter in sorted(by_family.items())},
        "low_quality_rejects_by_family": dict(sorted(low_quality.items(), key=lambda kv: (-kv[1], kv[0]))),
        "canary_ready_total_by_family": dict(sorted(qualified_ready.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _binding_summary(rows: list[sqlite3.Row]) -> dict[str, Any]:
    rejected: list[dict[str, Any]] = []
    resolved_rejections: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    failures_by_class = Counter()
    for row in rows:
        if row["kind"] != "source_scout_task":
            continue
        payload = _payload(row)
        status = str(payload.get("source_binding_ingest_status") or "")
        if not status:
            continue
        family = str(row["family"] or payload.get("family") or "")
        if status == "rejected_binding_artifact":
            resolution_status = str(payload.get("source_binding_recovery_status") or "")
            if payload.get("source_binding_deterministic_recovery_at_epoch") or payload.get("source_binding_unrecoverable_at_epoch"):
                resolved_rejections.append({
                    "work_id": row["work_id"],
                    "family": family,
                    "resolution_status": resolution_status or "deterministic_recovery_attempted",
                })
                continue
            failures = [str(x) for x in payload.get("source_binding_failures") or []]
            for failure in failures:
                failures_by_class[failure.split(":", 1)[0]] += 1
            rejected.append({
                "work_id": row["work_id"],
                "family": family,
                "failures": failures,
                "artifact_path": payload.get("source_binding_artifact_path"),
            })
        elif status in {"probe_enqueued", "probe_already_present"}:
            probes.append({
                "work_id": row["work_id"],
                "family": family,
                "status": status,
                "probe_work_id": payload.get("source_binding_probe_work_id"),
            })
    return {
        "rejected_count": len(rejected),
        "resolved_rejection_count": len(resolved_rejections),
        "probe_bridge_count": len(probes),
        "failure_classes": dict(sorted(failures_by_class.items(), key=lambda kv: (-kv[1], kv[0]))),
        "recent_rejections": rejected[:10],
        "recent_resolved_rejections": resolved_rejections[:10],
        "recent_probe_bridges": probes[:10],
    }


def _event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(event.get("event_type") or "") for event in events)
    costs: list[dict[str, Any]] = []
    fallback_events = 0
    useful_exits = Counter()
    for event in events:
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        model = payload.get("model") or {}
        if isinstance(model, dict) and model.get("actual_cost_usd") is not None:
            costs.append({
                "work_id": event.get("work_id"),
                "model_id": model.get("model_id"),
                "actual_cost_usd": model.get("actual_cost_usd"),
                "estimated_cost_usd": model.get("estimated_cost_usd"),
            })
        if payload.get("codex_cli_fallback_used") or payload.get("codex_cli_fallback_attempted"):
            fallback_events += 1
        for token in ("ratified_closure_count", "exact_gap_candidate_count", "valid_falsifier_count", "negative_control_unexpected_pass_count"):
            if _int_count(payload, token) > 0:
                useful_exits[token] += _int_count(payload, token)
                continue
            result = payload.get("result") or {}
            stdout_obj = _json_from_stdout_tail(str(result.get("stdout_tail") or "")) if isinstance(result, dict) else {}
            if _int_count(stdout_obj, token) > 0:
                useful_exits[token] += _int_count(stdout_obj, token)
    return {
        "tail_event_counts": dict(sorted(counts.items())),
        "llm_cost_events": costs[-20:],
        "llm_cost_tail_total_usd": round(sum(float(c.get("actual_cost_usd") or 0.0) for c in costs), 6),
        "codex_cli_fallback_events": fallback_events,
        "probe_scoreboard_event_mentions": dict(useful_exits),
    }


def _runner_summary(path: str | Path | None, *, stale_after_s: int) -> dict[str, Any]:
    status = _read_json(path)
    if not isinstance(status, dict):
        return {"status_path": str(path or ""), "available": False, "command_failures": [], "worker_negative_exits": []}
    failures: list[dict[str, Any]] = []
    worker_negative_exits: list[dict[str, Any]] = []
    for rec in status.get("commands") or []:
        if not isinstance(rec, dict):
            continue
        if rec.get("skipped"):
            continue
        rc = rec.get("returncode")
        if rc in (None, 0):
            continue
        cmd = rec.get("cmd") or []
        if isinstance(cmd, list):
            cmd_label = " ".join(str(part) for part in cmd[:4])
        else:
            cmd_label = str(cmd)
        stdout_obj = _json_from_stdout_tail(str(rec.get("stdout_tail") or ""))
        if (
            isinstance(stdout_obj, dict)
            and stdout_obj.get("claimed") is True
            and stdout_obj.get("work_id")
            and stdout_obj.get("status") in {"failed", "retired", "dead_letter"}
        ):
            worker_negative_exits.append({
                "cmd": cmd_label,
                "returncode": rc,
                "work_id": stdout_obj.get("work_id"),
                "status": stdout_obj.get("status"),
                "ok": stdout_obj.get("ok"),
            })
            continue
        failures.append({
            "cmd": cmd_label,
            "returncode": rc,
            "stdout_tail": str(rec.get("stdout_tail") or "")[-600:],
            "stderr_tail": str(rec.get("stderr_tail") or "")[-600:],
        })
    generated_at = int(status.get("generated_at_epoch") or 0)
    age_s = _now() - generated_at if generated_at > 0 else None
    stale = age_s is not None and age_s > max(1, int(stale_after_s))
    if stale:
        return {
            "status_path": str(path or ""),
            "available": True,
            "generated_at_epoch": generated_at,
            "age_s": age_s,
            "stale": True,
            "stale_after_s": max(1, int(stale_after_s)),
            "command_count": len(status.get("commands") or []),
            "command_failure_count": 0,
            "command_failures": [],
            "stale_command_failure_count": len(failures),
            "stale_command_failures": failures[:10],
            "worker_negative_exit_count": 0,
            "worker_negative_exits": [],
            "stale_worker_negative_exit_count": len(worker_negative_exits),
            "stale_worker_negative_exits": worker_negative_exits[:10],
            "note": "Runner status is stale, so command failures are retained as history but not treated as current bottlenecks.",
        }
    return {
        "status_path": str(path or ""),
        "available": True,
        "generated_at_epoch": generated_at,
        "age_s": age_s,
        "stale": False,
        "stale_after_s": max(1, int(stale_after_s)),
        "command_count": len(status.get("commands") or []),
        "command_failure_count": len(failures),
        "command_failures": failures[:10],
        "worker_negative_exit_count": len(worker_negative_exits),
        "worker_negative_exits": worker_negative_exits[:10],
    }


def _bottlenecks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    runner = payload.get("runner") or {}
    version_health = payload.get("worker_version_health") or {}
    if int(version_health.get("stale_process_count") or 0):
        out.append({
            "class": "stale_worker_runtime",
            "severity": "high",
            "evidence": {
                "stale_process_count": version_health.get("stale_process_count"),
                "stale_processes": (version_health.get("stale_processes") or [])[:5],
            },
            "next_action": "restart stale worker sessions before relying on new mill invariants",
        })
    if int(version_health.get("runtime_mismatch_count") or 0):
        out.append({
            "class": "worker_runtime_version_mismatch",
            "severity": "high",
            "evidence": {
                "runtime_mismatch_count": version_health.get("runtime_mismatch_count"),
                "runtime_mismatches": (version_health.get("runtime_mismatches") or [])[:5],
            },
            "next_action": "restart mismatched worker sessions so all workers share the current watched-source contract",
        })
    if runner.get("command_failure_count"):
        out.append({
            "class": "runner_command_failure",
            "severity": "high",
            "evidence": runner["command_failures"][:3],
            "next_action": "fix the failing station command before treating the queue as healthy",
        })
    recent_dead_letters = int(payload["queue"].get("recent_dead_letter_count") or 0)
    if recent_dead_letters:
        out.append({
            "class": "dead_letter",
            "severity": "high",
            "evidence": f"{recent_dead_letters} recently dead-lettered WorkItems",
            "next_action": "inspect dead-lettered WorkItems before retrying",
        })
    binding = payload["source_binding"]
    if binding["rejected_count"]:
        out.append({
            "class": "source_binding_rejection",
            "severity": "high",
            "evidence": binding["failure_classes"],
            "next_action": "feed rejection classes into scout/binding prompts and fix allowed target/candidate alignment",
        })
    low_quality = payload["source_search"]["low_quality_rejects_by_family"]
    if low_quality:
        top = next(iter(low_quality.items()))
        out.append({
            "class": "low_quality_source_queries",
            "severity": "medium",
            "evidence": {top[0]: top[1]},
            "next_action": "tighten scout context or retire families whose queries keep failing theorem-shape gates",
        })
    open_total = payload["queue"]["open_total"]
    if open_total == 0 and (binding["rejected_count"] or low_quality):
        out.append({
            "class": "drained_but_lossy",
            "severity": "medium",
            "evidence": "open queue is empty while recent terminal failures remain",
            "next_action": "reseed from failure classes, not from generic lane floors",
        })
    return out


def _write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LeanMill Observability",
        "",
        f"- generated_at_epoch: `{payload['generated_at_epoch']}`",
        f"- open_total: `{payload['queue']['open_total']}`",
        f"- queue_status: `{payload['queue']['status_counts']}`",
        f"- runner_command_failure_count: `{payload['runner'].get('command_failure_count', 0)}`",
        f"- runner_status_stale: `{payload['runner'].get('stale', False)}`",
        f"- stale_runner_command_failure_count: `{payload['runner'].get('stale_command_failure_count', 0)}`",
        f"- worker_negative_exit_count: `{payload['runner'].get('worker_negative_exit_count', 0)}`",
        f"- stale_worker_process_count: `{payload.get('worker_version_health', {}).get('stale_process_count', 0)}`",
        f"- runtime_mismatch_count: `{payload.get('worker_version_health', {}).get('runtime_mismatch_count', 0)}`",
        f"- llm_cost_tail_total_usd: `{payload['events']['llm_cost_tail_total_usd']}`",
        f"- codex_cli_fallback_events: `{payload['events']['codex_cli_fallback_events']}`",
        "",
        "## Bottlenecks",
        "",
    ]
    if payload["bottlenecks"]:
        for item in payload["bottlenecks"]:
            lines.append(f"- `{item['severity']}` `{item['class']}`: {item['evidence']} -> {item['next_action']}")
    else:
        lines.append("- none detected in the inspected window")
    lines.extend(["", "## Recent Terminal Failures", ""])
    for item in payload["recent_terminal_failures"][:10]:
        lines.append(f"- `{item['status']}` `{item['kind']}` `{item['family']}` `{item['work_id']}` reasons={item['reasons']}")
    lines.extend(["", "## Source Binding Rejections", ""])
    for item in payload["source_binding"]["recent_rejections"][:10]:
        lines.append(f"- `{item['family']}` `{item['work_id']}` failures={item['failures']}")
    lines.extend(["", "## Worker Version Health", ""])
    version_health = payload.get("worker_version_health") or {}
    lines.append(f"- worker_count: `{version_health.get('worker_count')}`")
    lines.append(f"- stale_process_count: `{version_health.get('stale_process_count')}`")
    lines.append(f"- stale_heartbeat_count: `{version_health.get('stale_heartbeat_count')}`")
    lines.append(f"- runtime_mismatch_count: `{version_health.get('runtime_mismatch_count')}`")
    lines.append(f"- git_heads: `{version_health.get('git_heads', {})}`")
    for rec in (version_health.get("stale_processes") or [])[:10]:
        lines.append(
            f"- stale `{rec.get('worker_id')}` age={rec.get('heartbeat_age_s')}s "
            f"work={rec.get('claimed_work_id')}"
        )
    p.write_text("\n".join(lines) + "\n")


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    rows = _queue_rows(cx)
    now = _now()
    obs_policy = _observability_policy(args.factory_policy)
    dead_letter_window_s = int(obs_policy["dead_letter_root_cause_window_s"])
    open_total = sum(1 for row in rows if row["status"] in {"queued", "claimed", "running"})
    recent_dead_letter_count = sum(
        1 for row in rows
        if row["status"] == "dead_letter" and int(row["updated_at"]) >= now - dead_letter_window_s
    )
    events = _read_events(args.events, limit=args.event_tail)
    payload = {
        "schema": "leanmill-observability-v1",
        "generated_at_epoch": now,
        "event_tail": int(args.event_tail),
        "observability_policy": obs_policy,
        "queue": {
            "total": len(rows),
            "open_total": open_total,
            "status_counts": _status_counts(rows),
            "kind_status_counts": _kind_status_counts(rows),
            "recent_dead_letter_count": recent_dead_letter_count,
        },
        "source_search": _source_search_summary(rows),
        "source_binding": _binding_summary(rows),
        "events": _event_summary(events),
        "runner": _runner_summary(args.runner_status, stale_after_s=int(obs_policy.get("runner_status_stale_after_s") or 6 * 60 * 60)),
        "worker_version_health": work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s),
        "recent_terminal_failures": _recent_terminal_failures(rows, limit=args.failure_limit),
    }
    payload["bottlenecks"] = _bottlenecks(payload)
    if args.out:
        _write_json(args.out, payload)
    if args.md:
        _write_markdown(args.md, payload)
    if args.events and args.out:
        work_queue.append_event(args.events, {
            "event_type": "leanmill_observability_report",
            "payload": {
                "bottleneck_count": len(payload["bottlenecks"]),
                "open_total": open_total,
                "source_binding_rejected_count": payload["source_binding"]["rejected_count"],
                "stale_worker_process_count": payload["worker_version_health"]["stale_process_count"],
                "runtime_mismatch_count": payload["worker_version_health"]["runtime_mismatch_count"],
            },
            "artifact_paths": [args.out, args.md] if args.md else [args.out],
        })
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_observability_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        cx = work_queue.connect(db)
        wid = work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": "s1",
            "family": "fam",
            "exit_kind": "source_search_rejected_low_quality_queries",
            "query_quality": [{"accepted": False, "failures": ["not_theorem_shaped"], "query": "find source"}],
        })
        work_queue.update_status(cx, work_id=wid, status="failed")
        bwid = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "b1",
            "family": "fam",
            "source_binding_ingest_status": "rejected_binding_artifact",
            "source_binding_failures": ["candidate_not_in_source_receipt:A"],
        })
        work_queue.update_status(cx, work_id=bwid, status="done")
        status = root / "status.json"
        status.write_text(json.dumps({
            "commands": [{
                "cmd": ["python", "scripts/public/control/failing_station.py"],
                "returncode": 1,
                "stderr_tail": "boom",
            }]
        }) + "\n")
        payload = build(argparse.Namespace(
            queue_db=db,
            events=events,
            runner_status=str(status),
            factory_policy=str(root / "missing_policy.json"),
            out=str(root / "obs.json"),
            md=str(root / "obs.md"),
            event_tail=100,
            failure_limit=10,
            worker_heartbeat_stale_s=0,
        ))
        assert payload["schema"] == "leanmill-observability-v1"
        assert payload["source_binding"]["rejected_count"] == 1
        assert payload["runner"]["command_failure_count"] == 1
        assert payload["bottlenecks"]
        status.write_text(json.dumps({
            "commands": [{
                "cmd": ["python", "scripts/public/control/worker.py"],
                "returncode": 1,
                "stdout_tail": json.dumps({"claimed": True, "status": "failed", "work_id": "w"}),
            }]
        }) + "\n")
        worker_payload = build(argparse.Namespace(
            queue_db=db,
            events=events,
            runner_status=str(status),
            factory_policy=str(root / "missing_policy.json"),
            out="",
            md="",
            event_tail=100,
            failure_limit=10,
            worker_heartbeat_stale_s=0,
        ))
        assert worker_payload["runner"]["command_failure_count"] == 0
        assert worker_payload["runner"]["worker_negative_exit_count"] == 1
    print("leanmill_observability self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--runner-status", default=DEFAULT_RUNNER_STATUS)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--event-tail", type=int, default=5000)
    ap.add_argument("--failure-limit", type=int, default=30)
    ap.add_argument("--worker-heartbeat-stale-s", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "open_total": payload["queue"]["open_total"],
        "bottleneck_count": len(payload["bottlenecks"]),
        "runner_command_failure_count": payload["runner"].get("command_failure_count", 0),
        "source_binding_rejected_count": payload["source_binding"]["rejected_count"],
        "stale_worker_process_count": payload["worker_version_health"]["stale_process_count"],
        "runtime_mismatch_count": payload["worker_version_health"]["runtime_mismatch_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
