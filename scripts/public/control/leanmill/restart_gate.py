#!/usr/bin/env python3
"""Fail-fast restart gate for local LeanMill factory."""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR, FACTORY_POLICY
from leanmill_watchdog import DEFAULT_POLICY_PROFILE, DEFAULT_SHUTDOWN_MARKER


DEFAULT_OUT = f"{DATA_DIR}/leanmill_restart_gate.json"


def _now() -> int:
    return int(time.time())


def _policy_ops(path: str | Path) -> dict[str, Any]:
    policy = read_policy(path)
    ops = policy.get("operations") if isinstance(policy, dict) else {}
    return ops if isinstance(ops, dict) else {}


def _runner_settings(path: str | Path, profile: str) -> dict[str, Any]:
    policy = read_policy(path)
    profile_obj = ((policy.get("profiles") or {}).get(profile) or {}) if isinstance(policy, dict) else {}
    runner = profile_obj.get("runner") if isinstance(profile_obj, dict) else {}
    return runner if isinstance(runner, dict) else {}


def _int(obj: Any, fallback: int) -> int:
    try:
        return int(obj)
    except (TypeError, ValueError):
        return fallback


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _candidate_supply(cx: sqlite3.Connection, *, window_s: int) -> dict[str, Any]:
    cutoff = _now() - max(1, int(window_s))
    try:
        rows = cx.execute(
            """
            SELECT *
            FROM work_items
            WHERE kind IN ('repair_canary_probe', 'proof_probe')
              AND updated_at >= ?
            ORDER BY updated_at DESC
            """,
            (cutoff,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    signatures: set[str] = set()
    lanes = Counter()
    by_status = Counter()
    examples: list[dict[str, Any]] = []
    for row in rows:
        payload = _payload(row)
        lane = str(payload.get("probe_lane") or "")
        if lane != "family_spec":
            continue
        sig = str(payload.get("probe_signature") or "")
        if not sig:
            family = str(payload.get("family") or row["family"] or "")
            row_id = str(payload.get("row_id") or payload.get("target_row_id") or "")
            sig = f"{family}:{row_id}" if family or row_id else str(row["work_id"])
        signatures.add(sig)
        lanes[lane] += 1
        by_status[str(row["status"])] += 1
        if len(examples) < 8:
            examples.append({
                "work_id": row["work_id"],
                "status": row["status"],
                "family": str(payload.get("family") or row["family"] or ""),
                "row_id": str(payload.get("row_id") or payload.get("target_row_id") or ""),
                "probe_signature": sig,
            })
    return {
        "window_s": window_s,
        "family_spec_probe_count": sum(lanes.values()),
        "candidate_signature_diversity": len(signatures),
        "status_counts": dict(sorted(by_status.items())),
        "examples": examples,
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    ops = _policy_ops(args.factory_policy)
    runner = _runner_settings(args.factory_policy, args.policy_profile)
    policy_min_diversity = _int(ops.get("restart_min_candidate_signature_diversity"), 4)
    policy_window_s = _int(ops.get("restart_candidate_supply_window_s"), 1800)
    min_arg = _int(args.min_candidate_signature_diversity, 0)
    window_arg = _int(args.candidate_supply_window_s, 0)
    min_diversity = min_arg if min_arg > 0 else policy_min_diversity
    window_s = window_arg if window_arg > 0 else policy_window_s
    requested_workers = _int(runner.get("family_spec_probe_workers"), 1)
    requested_floor = _int(runner.get("family_spec_probe_floor"), 2)
    scale_requested = requested_workers > 1 or requested_floor > 2 or args.policy_profile == "supervised_24x7"
    shutdown_marker = Path(args.shutdown_marker)
    cx = work_queue.connect(args.queue_db)
    supply = _candidate_supply(cx, window_s=window_s)
    blockers: list[str] = []
    if shutdown_marker.exists() and not args.force_clear_shutdown_marker:
        blockers.append("shutdown_marker_requires_explicit_force_clear")
    if scale_requested and int(supply["candidate_signature_diversity"]) < min_diversity:
        blockers.append("candidate_signature_diversity_below_scale_floor")
    verdict = "pass" if not blockers else "fail"
    payload = {
        "schema": "leanmill-restart-gate-v1",
        "generated_at_epoch": _now(),
        "status": verdict,
        "blockers": blockers,
        "policy_profile": args.policy_profile,
        "shutdown_marker": str(shutdown_marker),
        "shutdown_marker_present": shutdown_marker.exists(),
        "force_clear_shutdown_marker": bool(args.force_clear_shutdown_marker),
        "scale_requested": scale_requested,
        "requested_family_spec_probe_workers": requested_workers,
        "requested_family_spec_probe_floor": requested_floor,
        "min_candidate_signature_diversity": min_diversity,
        "candidate_supply": supply,
        "restart_allowed": verdict == "pass",
        "next_action": (
            "restart may proceed" if verdict == "pass" else
            "keep factory stopped; replenish diverse family-spec candidate supply or choose low-burn profile before restart"
        ),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if verdict != "pass" and not args.report_only:
        raise SystemExit("leanmill restart gate failed: " + json.dumps({
            "blockers": blockers,
            "candidate_supply": supply,
            "policy_profile": args.policy_profile,
            "shutdown_marker_present": shutdown_marker.exists(),
        }, sort_keys=True))
    return payload


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_restart_gate_") as td:
        root = Path(td)
        policy = root / "policy.json"
        policy.write_text(json.dumps({
            "operations": {"restart_min_candidate_signature_diversity": 2, "restart_candidate_supply_window_s": 3600},
            "profiles": {"supervised_24x7": {"runner": {"family_spec_probe_workers": 2, "family_spec_probe_floor": 8}}},
        }))
        db = str(root / "q.sqlite")
        cx = work_queue.connect(db)
        for idx in range(2):
            work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
                "work_id": f"probe:{idx}",
                "probe_lane": "family_spec",
                "probe_signature": f"sig:{idx}",
            })
        marker = root / "shutdown.json"
        marker.write_text("{}")
        blocked = evaluate(argparse.Namespace(
            queue_db=db,
            factory_policy=str(policy),
            policy_profile="supervised_24x7",
            shutdown_marker=str(marker),
            force_clear_shutdown_marker=False,
            min_candidate_signature_diversity=0,
            candidate_supply_window_s=0,
            out=str(root / "blocked.json"),
            report_only=True,
        ))
        assert blocked["status"] == "fail" and blocked["shutdown_marker_present"]
        passed = evaluate(argparse.Namespace(
            queue_db=db,
            factory_policy=str(policy),
            policy_profile="supervised_24x7",
            shutdown_marker=str(marker),
            force_clear_shutdown_marker=True,
            min_candidate_signature_diversity=0,
            candidate_supply_window_s=0,
            out=str(root / "passed.json"),
            report_only=False,
        ))
        assert passed["status"] == "pass", passed
    print("leanmill_restart_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default=DEFAULT_POLICY_PROFILE)
    ap.add_argument("--shutdown-marker", default=str(DEFAULT_SHUTDOWN_MARKER))
    ap.add_argument("--force-clear-shutdown-marker", action="store_true")
    ap.add_argument("--min-candidate-signature-diversity", type=int, default=0)
    ap.add_argument("--candidate-supply-window-s", type=int, default=0)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(evaluate(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
