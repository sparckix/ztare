#!/usr/bin/env python3
"""Execute concrete source-search WorkItems for LeanMill.

This worker runs LeanSearch source retrieval and static qualification for
bounded source requests. It emits candidate inventory only; Governance Gate is
still the only proof-credit authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, apply_profile_section
from leanmill_source_query_contract import query_quality


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_ROOT = f"{DEFAULT_DATA_DIR}/source_search_runs"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
SOURCE_SEARCH_BLOCK_ACTIONS = {
    "do_not_spend_until_new_evidence",
    "hold_source_binding_until_new_target_evidence",
}


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


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _allocator_record(path: str | Path | None, family: str) -> dict[str, Any]:
    if not path or not family:
        return {}
    obj = _read_json(Path(path))
    for rec in obj.get("allocations") or []:
        if isinstance(rec, dict) and str(rec.get("family") or "") == family:
            return rec
    return {}


def _query_quality(query: Any, family: str) -> dict[str, Any]:
    return query_quality(query, family)


def _run_root(args: argparse.Namespace, payload: dict[str, Any], work_id: str) -> Path:
    family = _slug(str(payload.get("family") or "unknown_family"))
    nonce = hashlib.sha256(f"{work_id}:{time.time()}".encode()).hexdigest()[:10]
    root = Path(args.root) / f"{family}_{nonce}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def execute_search(args: argparse.Namespace, payload: dict[str, Any], work_id: str) -> dict[str, Any]:
    family = str(payload.get("family") or "unknown_family")
    raw_queries = [q for q in (payload.get("queries") or []) if str(q).strip()]
    quality = [_query_quality(q, family) for q in raw_queries]
    queries = [q["query"] for q in quality if q["accepted"]]
    if not queries:
        root = _run_root(args, payload, work_id)
        summary = root / "summary.json"
        payload_out = {
            "schema": "leanmill-source-search-result-v1",
            "work_id": work_id,
            "family": family,
            "queries": [],
            "raw_queries": raw_queries,
            "query_quality": quality,
            "ok": False,
            "exit_kind": "source_search_rejected_low_quality_queries" if raw_queries else "source_search_rejected",
            "reason": "no_accepted_theorem_shaped_queries" if raw_queries else "missing_queries",
            "credit_boundary": {
                "source_search_has_no_proof_credit": True,
                "proof_credit_authority": "governance_gate",
            },
            "artifact_paths": [str(summary)],
        }
        summary.write_text(json.dumps(payload_out, indent=2, sort_keys=True) + "\n")
        return {
            **payload_out,
        }
    root = _run_root(args, payload, work_id)
    source_packet = root / "source_packet.json"
    source_md = root / "source_packet.md"
    empty_queue = root / "empty_source_queue.json"
    static_filter = root / "static_filter.json"
    static_md = root / "static_filter.md"
    summary = root / "summary.json"
    py = sys.executable
    source_cmd = [
        py,
        "scripts/public/control/leanmill/search/source_adapter.py",
        "--source-queue", str(empty_queue),
        "--out", str(source_packet),
        "--markdown", str(source_md),
        "--limit", str(args.leansearch_limit),
        "--request-sleep", str(args.request_sleep_s),
    ]
    for q in queries[: args.max_queries]:
        source_cmd.extend(["--query", q])
    empty_queue.write_text(json.dumps({"source_discovery_queue": []}, indent=2, sort_keys=True) + "\n")
    if args.fixture:
        source_cmd.extend(["--fixture", args.fixture])
    source_result = _run(source_cmd, timeout_s=args.source_timeout_s)
    static_result: dict[str, Any] = {"skipped": True, "reason": "source_search_failed"}
    if source_result["returncode"] == 0:
        static_result = _run([
            py,
            "scripts/public/control/leanmill/search/candidate_static_filter.py",
            "--packet", str(source_packet),
            "--out", str(static_filter),
            "--markdown", str(static_md),
            "--timeout", str(args.static_timeout_s),
            "--max-candidates-per-row", str(args.max_candidates_per_row),
        ], timeout_s=args.static_wall_timeout_s)
    source_obj = _read_json(source_packet)
    static_obj = _read_json(static_filter)
    ok = source_result["returncode"] == 0 and static_result.get("returncode") == 0
    exit_kind = "qualified_source_candidates" if ok else "source_search_failed"
    payload_out = {
        "schema": "leanmill-source-search-result-v1",
        "work_id": work_id,
        "family": family,
        "queries": queries[: args.max_queries],
        "query_quality": quality,
        "ok": ok,
        "exit_kind": exit_kind,
        "source_summary": {
            "row_count": source_obj.get("row_count"),
            "usable_candidate_total": source_obj.get("usable_candidate_total"),
            "exact_target_excluded_total": source_obj.get("exact_target_excluded_total"),
            "post_target_forbidden_total": source_obj.get("post_target_forbidden_total"),
        },
        "static_summary": {
            "canary_ready_total": static_obj.get("canary_ready_total"),
            "usable_candidate_total": static_obj.get("usable_candidate_total") or static_obj.get("candidate_total"),
        },
        "commands": [source_result, static_result],
        "credit_boundary": {
            "source_search_has_no_proof_credit": True,
            "proof_credit_authority": "governance_gate",
        },
        "artifact_paths": [str(source_packet), str(source_md), str(static_filter), str(static_md), str(summary)],
    }
    summary.write_text(json.dumps(payload_out, indent=2, sort_keys=True) + "\n")
    return payload_out


def work_once(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=["source_search_task"], lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {
        "event_type": "source_search_worker_started",
        "work_id": item["work_id"],
        "payload": item,
    })
    payload = item.get("payload") or {}
    family = str(item.get("family") or payload.get("family") or "")
    allocator_rec = _allocator_record(args.allocator, family)
    allocator_action = str(allocator_rec.get("recommended_action") or "")
    if allocator_action in SOURCE_SEARCH_BLOCK_ACTIONS:
        result = {
            "schema": "leanmill-source-search-result-v1",
            "work_id": item["work_id"],
            "family": family,
            "ok": True,
            "exit_kind": "retired_source_strategy_repair_required",
            "retire_reason": "source_family_allocator_blocks_source_search",
            "allocator_action": allocator_action,
            "credit_boundary": {
                "source_search_has_no_proof_credit": True,
                "proof_credit_authority": "governance_gate",
            },
        }
        work_queue.update_status(cx, work_id=item["work_id"], status="retired", payload_update=result)
        work_queue.append_event(args.events, {
            "event_type": "source_search_worker_retired_allocator_held",
            "work_id": item["work_id"],
            "payload": {
                "family": family,
                "allocator_action": allocator_action,
                "source_binding_conversion_rate": (allocator_rec.get("source_quality") or {}).get("source_binding_conversion_rate"),
            },
        })
        return {"claimed": True, "work_id": item["work_id"], "status": "retired", "ok": True}
    result = execute_search(args, payload, item["work_id"])
    status = "done" if result.get("ok") else "failed"
    work_queue.update_status(cx, work_id=item["work_id"], status=status, payload_update=result)
    work_queue.append_event(args.events, {
        "event_type": f"source_search_worker_{status}",
        "work_id": item["work_id"],
        "payload": {
            "exit_kind": result.get("exit_kind"),
            "family": result.get("family"),
            "source_summary": result.get("source_summary"),
            "static_summary": result.get("static_summary"),
        },
        "artifact_paths": result.get("artifact_paths") or [],
    })
    return {"claimed": True, "work_id": item["work_id"], "status": status, "ok": bool(result.get("ok"))}


def daemon_loop(args: argparse.Namespace) -> dict[str, Any]:
    completed = 0
    last: dict[str, Any] = {}
    while True:
        if args.max_tasks and completed >= args.max_tasks:
            break
        result = work_once(args)
        last = result
        if result.get("claimed"):
            completed += 1
            print(json.dumps({"daemon": args.worker_id, "task_result": result}, sort_keys=True), flush=True)
            continue
        print(json.dumps({"daemon": args.worker_id, "idle": True}, sort_keys=True), flush=True)
        time.sleep(max(1, int(args.idle_sleep_s)))
    return {"daemon": args.worker_id, "completed_tasks": completed, "last_result": last}


def _self_test() -> int:
    import tempfile

    assert _slug("a b/c") == "a_b_c"
    assert not _query_quality("source_to_intake_receipt.exact_target_exclusion_count = 0", "complex_limit_causeq_planner")["accepted"]
    assert _query_quality("Complex.tendsto_re", "complex_limit_causeq_planner")["accepted"]
    with tempfile.TemporaryDirectory(prefix="leanmill_source_search_worker_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        events = str(root / "events.jsonl")
        allocator = root / "allocator.json"
        allocator.write_text(json.dumps({
            "allocations": [{
                "family": "held_fam",
                "recommended_action": "hold_source_binding_until_new_target_evidence",
                "source_quality": {"source_binding_conversion_rate": 0.0},
            }]
        }) + "\n")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="source_search_task", priority=1, payload={
            "work_id": "source_search:held_fam:test",
            "family": "held_fam",
            "queries": ["Complex.tendsto_re"],
        })
        result = work_once(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="test-source-worker",
            lease_s=60,
            allocator=str(allocator),
            root=str(root / "runs"),
            leansearch_limit=1,
            max_queries=1,
            request_sleep_s=0,
            source_timeout_s=1,
            static_timeout_s=1,
            static_wall_timeout_s=1,
            max_candidates_per_row=1,
            fixture="",
        ))
        assert result["status"] == "retired"
    print("leanmill_source_search_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--worker-id", default="source-search-worker-local")
    ap.add_argument("--lease-s", type=int, default=1200)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--leansearch-limit", type=int, default=8)
    ap.add_argument("--max-queries", type=int, default=3)
    ap.add_argument("--request-sleep-s", type=float, default=1.0)
    ap.add_argument("--source-timeout-s", type=int, default=240)
    ap.add_argument("--static-timeout-s", type=int, default=180)
    ap.add_argument("--static-wall-timeout-s", type=int, default=600)
    ap.add_argument("--max-candidates-per-row", type=int, default=6)
    ap.add_argument("--fixture", default="")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-sleep-s", type=int, default=15)
    ap.add_argument("--max-tasks", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    apply_profile_section(args, section="source_search_worker")
    result = daemon_loop(args) if args.daemon else work_once(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
