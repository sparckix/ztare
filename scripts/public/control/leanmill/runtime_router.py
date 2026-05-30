#!/usr/bin/env python3
"""Policy and queue-health based runtime routing for LeanMill agents.

This is deliberately a control-plane primitive: it chooses which subscription
agent runtime should own a new model-mediated task. Proof credit and scientific
outcomes remain governed elsewhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY, read_policy

VALID_RUNTIMES = ("codex", "claude")
BALANCED_SENTINELS = {"", "auto", "balanced", "policy"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _runtime_policy(policy: dict[str, Any], profile_name: str = "") -> dict[str, Any]:
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    base = operations.get("agent_runtime_routing") or operations.get("model_runtime_routing") or {}
    out = dict(base) if isinstance(base, dict) else {}
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if profile_name else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    override = runner.get("agent_runtime_routing") if isinstance(runner, dict) else None
    if isinstance(override, dict):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(out.get(key), dict):
                merged = dict(out[key])
                merged.update(value)
                out[key] = merged
            else:
                out[key] = value
    return out


def _parse_runtime_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        vals = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        vals = [str(part).strip() for part in value if str(part).strip()]
    else:
        vals = []
    cleaned = [val for val in vals if val in VALID_RUNTIMES]
    return cleaned or list(fallback)


def _payload_runtime(payload_json: str) -> str:
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        return ""
    runtime = str(payload.get("runtime") or "")
    return runtime if runtime in VALID_RUNTIMES else ""


def _worker_runtime(payload_json: str, worker_id: str = "") -> str:
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    runtime = str(payload.get("runtime") or payload.get("default_runtime") or "")
    if runtime in VALID_RUNTIMES:
        return runtime
    text = (str(worker_id) + " " + json.dumps(payload, sort_keys=True)).lower()
    for candidate in VALID_RUNTIMES:
        if candidate in text:
            return candidate
    return ""


def _payload_auth_unavailable(payload_json: str) -> bool:
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        return False
    runtime_health = payload.get("runtime_health") if isinstance(payload.get("runtime_health"), dict) else {}
    exit_kind = str(payload.get("exit_kind") or "")
    reason = str(payload.get("reason") or payload.get("last_failure_reason") or "")
    text = " ".join([exit_kind, reason, json.dumps(runtime_health, sort_keys=True)]).lower()
    return "runtime_auth_unavailable" in text or "token_invalidated" in text or "refresh_token_reused" in text


def runtime_recovery_epochs(events_path: str | Path = work_queue.DEFAULT_EVENTS) -> dict[str, int]:
    epochs = {runtime: 0 for runtime in VALID_RUNTIMES}
    p = Path(events_path)
    if not p.exists():
        return epochs
    for line in p.read_text(errors="ignore").splitlines()[-5000:]:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(rec.get("event_type") or "") not in {"subscription_runtime_health_recovered", "agent_runtime_health_recovered"}:
            continue
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        runtime = str(payload.get("runtime") or rec.get("runtime") or "")
        if runtime not in epochs:
            continue
        epoch = _int(payload.get("recovered_at_epoch") or rec.get("created_at") or rec.get("timestamp") or rec.get("epoch"), 0)
        if epoch <= 0:
            epoch = _int(payload.get("at_epoch"), 0)
        epochs[runtime] = max(epochs[runtime], epoch)
    return epochs


def queue_runtime_stats(queue_db: str | Path, *, window_s: int, recovery_epochs: dict[str, int] | None = None) -> dict[str, dict[str, int]]:
    stats = {
        runtime: {
            "open": 0,
            "recent_terminal": 0,
            "recent_done": 0,
            "recent_failed": 0,
            "recent_auth_unavailable": 0,
            "fresh_heartbeats": 0,
            "stale_heartbeats": 0,
        }
        for runtime in VALID_RUNTIMES
    }
    p = Path(queue_db)
    if not p.exists():
        return stats
    threshold = int(time.time()) - max(0, int(window_s))
    recovery_epochs = recovery_epochs or {}
    try:
        cx = sqlite3.connect(str(p))
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            """
            SELECT status, updated_at, payload_json
            FROM work_items
            WHERE kind IN ('agent_repair_task','source_scout_task','agent_repair','subscription_agent_task','agent_task')
            """
        ).fetchall()
    except sqlite3.Error:
        return stats
    now = int(time.time())
    for row in rows:
        runtime = _payload_runtime(str(row["payload_json"] or ""))
        if runtime not in stats:
            continue
        status = str(row["status"] or "")
        updated_at = _int(row["updated_at"], 0)
        if status in {"queued", "claimed", "running"}:
            stats[runtime]["open"] += 1
        if updated_at >= threshold and status in {"done", "failed", "retired", "dead_letter"}:
            stats[runtime]["recent_terminal"] += 1
            if status == "done":
                stats[runtime]["recent_done"] += 1
            if status == "failed":
                stats[runtime]["recent_failed"] += 1
            if _payload_auth_unavailable(str(row["payload_json"] or "")) and updated_at >= _int(recovery_epochs.get(runtime), 0):
                stats[runtime]["recent_auth_unavailable"] += 1
    try:
        hb_rows = cx.execute("""
            SELECT worker_id, worker_kind, last_seen_at, payload_json
            FROM worker_heartbeats
        """).fetchall()
    except sqlite3.Error:
        hb_rows = []
    stale_after_s = max(60, int(window_s))
    for hb in hb_rows:
        runtime = _worker_runtime(str(hb["payload_json"] or ""), str(hb["worker_id"] or ""))
        if runtime not in stats:
            continue
        last_seen = _int(hb["last_seen_at"], 0)
        if last_seen and now - last_seen <= stale_after_s:
            stats[runtime]["fresh_heartbeats"] += 1
        else:
            stats[runtime]["stale_heartbeats"] += 1
    return stats


def select_runtime(
    *,
    requested_runtime: str,
    queue_db: str | Path = work_queue.DEFAULT_DB,
    policy_path: str | Path = FACTORY_POLICY,
    policy_profile: str = "",
    route_key: str = "",
    planned_counts: dict[str, int] | None = None,
    events_path: str | Path = work_queue.DEFAULT_EVENTS,
) -> dict[str, Any]:
    requested = str(requested_runtime or "").strip()
    if requested in VALID_RUNTIMES:
        return {
            "schema": "leanmill-agent-runtime-routing-receipt-v1",
            "mode": "forced",
            "requested_runtime": requested,
            "selected_runtime": requested,
            "reason": "explicit_runtime_requested",
        }
    if requested not in BALANCED_SENTINELS:
        requested = "balanced"
    policy = read_policy(policy_path)
    routing = _runtime_policy(policy, policy_profile)
    candidates = _parse_runtime_list(routing.get("candidate_runtimes"), list(VALID_RUNTIMES))
    weights_raw = routing.get("weights") if isinstance(routing.get("weights"), dict) else {}
    weights = {runtime: max(1, _int(weights_raw.get(runtime), 1)) for runtime in VALID_RUNTIMES}
    window_s = _int(routing.get("health_window_s"), 1800)
    auth_threshold = _int(routing.get("auth_unavailable_block_threshold"), 1)
    recovery_epochs = runtime_recovery_epochs(events_path)
    stats = queue_runtime_stats(queue_db, window_s=window_s, recovery_epochs=recovery_epochs)
    disabled = set(_parse_runtime_list(routing.get("disabled_runtimes"), []))
    env_disabled = _parse_runtime_list(os.environ.get("LEANMILL_AGENT_RUNTIME_DISABLED", ""), [])
    disabled.update(env_disabled)
    runtime_overrides = routing.get("runtimes") if isinstance(routing.get("runtimes"), dict) else {}
    for runtime, cfg in runtime_overrides.items():
        if runtime in VALID_RUNTIMES and isinstance(cfg, dict) and cfg.get("enabled") is False:
            disabled.add(runtime)
    planned = {runtime: _int((planned_counts or {}).get(runtime), 0) for runtime in VALID_RUNTIMES}
    available = []
    unavailable_reasons: dict[str, str] = {}
    for runtime in candidates:
        if runtime in disabled:
            unavailable_reasons[runtime] = "disabled_by_policy_or_env"
            continue
        if auth_threshold >= 0 and stats[runtime]["recent_auth_unavailable"] >= auth_threshold:
            unavailable_reasons[runtime] = "recent_runtime_auth_unavailable"
            continue
        require_fresh = bool(routing.get("require_fresh_worker_heartbeat", False))
        if require_fresh and stats[runtime]["fresh_heartbeats"] <= 0:
            unavailable_reasons[runtime] = "no_fresh_worker_heartbeat"
            continue
        available.append(runtime)
    if not available:
        fallback = str(routing.get("fallback_runtime") or "")
        fallback_order: list[str] = []
        if fallback in VALID_RUNTIMES:
            fallback_order.append(fallback)
        fallback_order.extend(runtime for runtime in candidates if runtime not in fallback_order)
        fallback_order.append("codex")
        selected = next((runtime for runtime in fallback_order if runtime in VALID_RUNTIMES and runtime not in disabled), "codex")
        mode = "fallback_no_healthy_runtime"
    else:
        def score(runtime: str) -> tuple[float, int, str]:
            heartbeat_discount = min(stats[runtime]["fresh_heartbeats"], weights[runtime])
            load = stats[runtime]["open"] + planned[runtime] - (0.25 * heartbeat_discount)
            normalized = load / float(weights[runtime])
            tie = int(hashlib.sha256(f"{route_key}:{runtime}".encode()).hexdigest()[:8], 16)
            return (normalized, tie, runtime)
        selected = min(available, key=score)
        mode = "weighted_least_loaded_healthy"
    return {
        "schema": "leanmill-agent-runtime-routing-receipt-v1",
        "mode": mode,
        "requested_runtime": requested or "balanced",
        "selected_runtime": selected,
        "candidate_runtimes": candidates,
        "available_runtimes": available,
        "unavailable_reasons": unavailable_reasons,
        "weights": weights,
        "planned_counts": planned,
        "queue_window_s": window_s,
        "queue_runtime_stats": stats,
        "runtime_recovery_epochs": recovery_epochs,
        "route_key": route_key,
        "policy_path": str(policy_path),
        "policy_profile": policy_profile,
    }


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_runtime_router_") as td:
        root = Path(td)
        policy = root / "policy.json"
        policy.write_text(json.dumps({
            "operations": {
                "agent_runtime_routing": {
                    "candidate_runtimes": ["codex", "claude"],
                    "weights": {"codex": 1, "claude": 1},
                    "auth_unavailable_block_threshold": 1,
                    "health_window_s": 3600,
                }
            }
        }) + "\n")
        db = root / "q.sqlite"
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="agent_repair_task", priority=1, payload={"runtime": "codex", "work_id": "c1"})
        work_queue.record_worker_heartbeat(cx, worker_id="leanmill-codex-worker", worker_kind="agent_repair", payload={"runtime": "codex"})
        r = select_runtime(requested_runtime="balanced", queue_db=db, policy_path=policy, route_key="x")
        assert r["selected_runtime"] == "claude", r
        work_queue.update_status(cx, work_id="c1", status="failed", payload_update={"runtime": "codex", "exit_kind": "runtime_auth_unavailable"})
        r2 = select_runtime(requested_runtime="balanced", queue_db=db, policy_path=policy, route_key="x")
        assert r2["selected_runtime"] == "claude", r2
        events = root / "events.jsonl"
        now = int(time.time())
        events.write_text(json.dumps({"event_type": "subscription_runtime_health_recovered", "payload": {"runtime": "codex", "recovered_at_epoch": now + 1}}) + "\n")
        r3 = select_runtime(requested_runtime="balanced", queue_db=db, policy_path=policy, route_key="x", events_path=events)
        assert r3["selected_runtime"] in {"codex", "claude"}, r3
        assert r3["queue_runtime_stats"]["codex"]["recent_auth_unavailable"] == 0, r3
        forced = select_runtime(requested_runtime="codex", queue_db=db, policy_path=policy, route_key="x")
        assert forced["selected_runtime"] == "codex" and forced["mode"] == "forced", forced
        codex_only_policy = root / "codex_only_policy.json"
        codex_only_policy.write_text(json.dumps({
            "operations": {
                "agent_runtime_routing": {
                    "candidate_runtimes": ["codex"],
                    "fallback_runtime": "claude",
                    "disabled_runtimes": ["claude"],
                    "auth_unavailable_block_threshold": 0,
                }
            }
        }) + "\n")
        codex_only = select_runtime(requested_runtime="balanced", queue_db=db, policy_path=codex_only_policy, route_key="x")
        assert codex_only["selected_runtime"] == "codex", codex_only
        assert codex_only["unavailable_reasons"].get("claude") != "disabled_by_policy_or_env", codex_only
    print("leanmill_runtime_router self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requested-runtime", default="balanced")
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--route-key", default="")
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(select_runtime(
        requested_runtime=args.requested_runtime,
        queue_db=args.queue_db,
        policy_path=args.factory_policy,
        policy_profile=args.policy_profile,
        route_key=args.route_key,
        events_path=args.events,
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
