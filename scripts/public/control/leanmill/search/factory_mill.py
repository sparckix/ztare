#!/usr/bin/env python3
"""Run a LeanSearch factory mill with multiple stations.

90/20 orchestration layer:
  1. Run one or more Path-A lanes to fill durable event streams.
  2. Start N Path-B governance consumers over the SQLite-backed queue.
  3. Leave Path-C residual streams as append-only work for repair mining.

This is intentionally subprocess-based and stdlib-only. SQLite provides the
queue enforcement; JSONL streams provide the audit trail.
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
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def _run(cmd: list[str], timeout_s: float | None = None) -> dict[str, Any]:
    t0 = time.monotonic()
    timed_out = False
    proc = subprocess.Popen(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
    stdout = stdout or ""
    stderr = stderr or ""
    return {
        "cmd": cmd,
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_s": round(time.monotonic() - t0, 3),
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _intake_connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path), timeout=30.0)
    for attempt in range(10):
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=30000")
            break
        except sqlite3.OperationalError:
            if attempt == 9:
                raise
            time.sleep(0.25 * (attempt + 1))
    return con


def _requeue_stale_claims(con: sqlite3.Connection, now: float, stale_after_s: float) -> int:
    if stale_after_s <= 0:
        return 0
    cur = con.execute(
        """
        UPDATE intake_queue
        SET status = 'ready', claimed_by = NULL, claimed_at = NULL
        WHERE status = 'claimed'
          AND claimed_at IS NOT NULL
          AND claimed_at < ?
        """,
        (now - stale_after_s,),
    )
    return int(cur.rowcount or 0)


def _claim_intake(
    con: sqlite3.Connection,
    worker_id: str,
    *,
    lock_lane: bool = True,
    stale_after_s: float = 0.0,
) -> tuple[str, str] | None:
    now = time.time()
    con.execute("BEGIN IMMEDIATE")
    _requeue_stale_claims(con, now, stale_after_s)
    if lock_lane:
        row = con.execute(
            """
            SELECT q.row_id, q.lane_hint
            FROM intake_queue q
            WHERE q.status = 'ready'
              AND NOT EXISTS (
                SELECT 1
                FROM intake_queue active
                WHERE active.status = 'claimed'
                  AND active.lane_hint = q.lane_hint
              )
            ORDER BY q.priority DESC, q.row_id ASC
            LIMIT 1
            """
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT row_id, lane_hint
            FROM intake_queue
            WHERE status = 'ready'
            ORDER BY priority DESC, row_id ASC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        con.commit()
        return None
    row_id = str(row[0])
    lane = str(row[1])
    con.execute(
        """
        UPDATE intake_queue
        SET status = 'claimed', claimed_by = ?, claimed_at = ?
        WHERE row_id = ? AND status = 'ready'
        """,
        (worker_id, now, row_id),
    )
    con.commit()
    return row_id, lane


def _finish_intake(con: sqlite3.Connection, row_id: str, status: str, result_root: Path) -> None:
    con.execute(
        """
        UPDATE intake_queue
        SET status = ?, done_at = ?, result_root = ?
        WHERE row_id = ?
        """,
        (status, time.time(), str(result_root), row_id),
    )
    con.commit()


def _publish_path_a_timeout(root: Path, lane: str, row_id: str | None, result: dict[str, Any]) -> None:
    if not row_id:
        return
    event_dir = root / lane / "events"
    _append_jsonl(event_dir / "path_c_residuals.jsonl", {
        "schema": "leansearch-factory-event-v1",
        "event": "path_c_residual",
        "status": "timeout",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": "",
        "lane": lane,
        "row_id": row_id,
        "row_out": "",
        "cycle_s": result.get("elapsed_s"),
        "lead_s": result.get("elapsed_s"),
        "residual_class": "timeout",
        "error_counts": {"timeout": 1},
        "next_lever": "decompose_or_reduce_search_breadth",
        "sample_tail": "Path-A subprocess wall-clock timeout before row artifact.",
    })


def _effective_intake_limit(args: argparse.Namespace) -> int | None:
    """Global Path-A intake cap.

    Historical footgun: `--limit-per-worker` only limits downstream B workers.
    For from-intake smokes, operator intent is usually a global acquisition cap.
    Preserve explicit `--intake-limit`, otherwise treat `--limit-per-worker` as
    the global cap for Path-A intake too.
    """
    if args.intake_limit is not None:
        return args.intake_limit
    if getattr(args, "from_intake", False) and args.limit_per_worker is not None:
        return args.limit_per_worker
    return None


def _run_path_a(args: argparse.Namespace, lane: str, row_id: str | None = None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(HERE / "leansearch_factory.py"),
        "--lane",
        lane,
        "--root",
        args.root,
        "--corpus",
        args.corpus,
        "--static-filter",
        args.static_filter,
        "--backend",
        args.backend,
        "--timeout",
        str(args.a_timeout),
        "--summary",
        str(Path(args.root) / f"{lane}_path_a_summary.json"),
    ]
    if args.score_candidates:
        cmd.append("--score-candidates")
    if args.require_positive_source_action:
        cmd.append("--require-positive-source-action")
    if row_id:
        cmd.extend(["--row-id", row_id])
    if args.resume:
        cmd.append("--resume")
    timeout_s = float(args.path_a_row_wall_timeout_s or 0.0) or None
    return _run(cmd, timeout_s=timeout_s)


def _run_b_worker(args: argparse.Namespace, lane: str, worker_idx: int) -> subprocess.Popen[str]:
    cmd = [
        sys.executable,
        str(HERE / "leansearch_factory_consume.py"),
        "--root",
        args.root,
        "--lane",
        lane,
        "--corpus",
        args.corpus,
        "--static-filter",
        args.static_filter,
        "--consumer",
        "govern",
        "--timeout",
        str(args.b_timeout),
        "--max-candidates",
        str(args.max_candidates),
        "--max-actions",
        str(args.max_actions),
        "--use-sqlite-queue",
        "--queue-db",
        str(Path(args.root) / "factory_queue.sqlite"),
        "--worker-id",
        f"{lane}:b{worker_idx}",
        "--candidate-mode",
        args.candidate_mode,
    ]
    if args.limit_per_worker is not None:
        cmd.extend(["--limit", str(args.limit_per_worker)])
    return subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _drain(proc: subprocess.Popen[str], cmd_label: str) -> dict[str, Any]:
    out, err = proc.communicate()
    return {
        "cmd": cmd_label,
        "returncode": proc.returncode,
        "stdout_tail": (out or "")[-4000:],
        "stderr_tail": (err or "")[-4000:],
    }


def run_mill(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / "mill_events.jsonl"
    lanes = list(args.lane or ["summability_transport"])
    requested_lanes = list(lanes)
    processed_lanes: list[str] = []
    started = time.monotonic()
    intake_con = _intake_connect(Path(args.intake_db)) if args.from_intake else None
    intake_worker_id = args.worker_id or f"mill:{int(time.time())}"

    path_a_results = []
    workers: list[tuple[str, int, subprocess.Popen[str]]] = []
    if not args.skip_path_a:
        intake_count = 0
        effective_intake_limit = _effective_intake_limit(args)
        while True:
            if intake_con:
                if effective_intake_limit is not None and intake_count >= effective_intake_limit:
                    break
                claimed = _claim_intake(
                    intake_con,
                    intake_worker_id,
                    lock_lane=not args.allow_same_lane_parallel,
                    stale_after_s=float(args.claim_stale_after_s or 0.0),
                )
                if claimed is None:
                    break
                row_id, lane = claimed
                intake_count += 1
            else:
                if not lanes:
                    break
                lane = lanes.pop(0)
                row_id = None
            rec = {"phase": "path_a_start", "lane": lane, "row_id": row_id, "ts": time.time()}
            _append_jsonl(log_path, rec)
            result = _run_path_a(args, lane, row_id)
            result.update({"phase": "path_a_done", "lane": lane, "row_id": row_id, "ts": time.time()})
            _append_jsonl(log_path, result)
            path_a_results.append(result)
            if lane not in processed_lanes:
                processed_lanes.append(lane)
            if result["returncode"] != 0:
                if result.get("timed_out"):
                    _publish_path_a_timeout(root, lane, row_id, result)
                    if intake_con and row_id:
                        _finish_intake(intake_con, row_id, "timeout", root)
                    continue
                if intake_con and row_id:
                    _finish_intake(intake_con, row_id, "failed", root)
                return {
                    "schema": "leansearch-factory-mill-v1",
                    "status": "path_a_failed",
                    "root": str(root),
                    "path_a": path_a_results,
                }
            if intake_con and row_id:
                _finish_intake(intake_con, row_id, "done", root)
            if args.overlap_stations:
                for idx in range(args.b_workers):
                    workers.append((lane, idx, _run_b_worker(args, lane, idx)))
    if args.skip_path_a or not args.overlap_stations:
        for lane in (processed_lanes or requested_lanes):
            for idx in range(args.b_workers):
                workers.append((lane, idx, _run_b_worker(args, lane, idx)))
    b_results = []
    for lane, idx, proc in workers:
        rec = _drain(proc, f"{lane}:b{idx}")
        rec.update({"phase": "path_b_done", "lane": lane, "worker_index": idx, "ts": time.time()})
        _append_jsonl(log_path, rec)
        b_results.append(rec)

    payload = {
        "schema": "leansearch-factory-mill-v1",
        "status": "complete",
        "root": str(root),
        "lanes": processed_lanes or requested_lanes,
        "elapsed_s": round(time.monotonic() - started, 3),
        "path_a": path_a_results,
        "path_b": b_results,
        "queue_db": str(root / "factory_queue.sqlite"),
        "intake_db": args.intake_db if intake_con else "",
        "effective_intake_limit": _effective_intake_limit(args) if intake_con else None,
        "log": str(log_path),
    }
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    assert (HERE / "leansearch_factory.py").exists()
    assert (HERE / "leansearch_factory_consume.py").exists()
    assert _effective_intake_limit(argparse.Namespace(from_intake=True, intake_limit=None, limit_per_worker=4)) == 4
    assert _effective_intake_limit(argparse.Namespace(from_intake=True, intake_limit=2, limit_per_worker=4)) == 2
    assert _effective_intake_limit(argparse.Namespace(from_intake=False, intake_limit=None, limit_per_worker=4)) is None
    with sqlite3.connect(":memory:") as con:
        con.execute(
            """
            CREATE TABLE intake_queue (
              row_id TEXT PRIMARY KEY, lane_hint TEXT, status TEXT, priority INTEGER,
              claimed_by TEXT, claimed_at REAL, done_at REAL, result_root TEXT
            )
            """
        )
        con.execute("INSERT INTO intake_queue (row_id, lane_hint, status, priority) VALUES ('r1', 'bigo_specialization', 'ready', 1)")
        con.execute("INSERT INTO intake_queue (row_id, lane_hint, status, priority) VALUES ('r2', 'bigo_specialization', 'ready', 0)")
        con.execute("INSERT INTO intake_queue (row_id, lane_hint, status, priority) VALUES ('r3', 'geom_iff_direction', 'ready', 0)")
        con.execute(
            "INSERT INTO intake_queue (row_id, lane_hint, status, priority, claimed_by, claimed_at) VALUES ('r4', 'stale_lane', 'claimed', 9, 'dead', ?)",
            (time.time() - 1000,),
        )
        con.commit()
        assert _claim_intake(con, "w", stale_after_s=10) == ("r4", "stale_lane")
        _finish_intake(con, "r4", "done", Path("/tmp/x"))
        assert _claim_intake(con, "w") == ("r1", "bigo_specialization")
        assert _claim_intake(con, "w") == ("r3", "geom_iff_direction")
        assert _claim_intake(con, "w") is None
        _finish_intake(con, "r1", "done", Path("/tmp/x"))
        assert _claim_intake(con, "w") == ("r2", "bigo_specialization")
        _finish_intake(con, "r1", "done", Path("/tmp/x"))
        assert con.execute("SELECT status FROM intake_queue WHERE row_id = 'r1'").fetchone()[0] == "done"
    print("leansearch_factory_mill self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", action="append")
    ap.add_argument("--root", default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--summary")
    ap.add_argument("--skip-path-a", action="store_true")
    ap.add_argument("--overlap-stations", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--from-intake", action="store_true")
    ap.add_argument("--intake-db", default="/tmp/rung1/leansearch_factory_intake.sqlite")
    ap.add_argument("--intake-limit", type=int)
    ap.add_argument("--worker-id", default="")
    ap.add_argument("--corpus", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--static-filter", default="analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json")
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="subprocess")
    ap.add_argument("--score-candidates", action="store_true")
    ap.add_argument("--require-positive-source-action", action="store_true")
    ap.add_argument("--b-workers", type=int, default=2)
    ap.add_argument("--a-timeout", type=int, default=75)
    ap.add_argument(
        "--path-a-row-wall-timeout-s",
        type=float,
        default=0.0,
        help="Hard subprocess wall-clock timeout per Path-A row. 0 disables.",
    )
    ap.add_argument("--b-timeout", type=int, default=160)
    ap.add_argument("--max-candidates", type=int, default=4)
    ap.add_argument("--max-actions", type=int, default=3)
    ap.add_argument("--candidate-mode", choices=["first_then_all", "all"], default="first_then_all")
    ap.add_argument("--limit-per-worker", type=int)
    ap.add_argument(
        "--claim-stale-after-s",
        type=float,
        default=1800.0,
        help="Requeue claimed intake rows older than this many seconds before claiming. Use 0 to disable.",
    )
    ap.add_argument(
        "--allow-same-lane-parallel",
        action="store_true",
        help="Disable intake lane locking. Faster only if per-row output paths are disjoint.",
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(run_mill(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
