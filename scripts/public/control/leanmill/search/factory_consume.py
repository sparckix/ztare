#!/usr/bin/env python3
"""Consume LeanSearch factory event streams.

This is the pickup side of the file-backed event bus. It reads append-only
factory streams, skips already-consumed event ids via a checkpoint, and emits
follow-on events. The first implemented consumer is Path B governance:
`to_govern.jsonl` -> governed Lean replay -> `closed.jsonl` or
`path_c_residuals.jsonl`.
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

import leansearch_action_smoke as smoke


DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _event_id(rec: dict[str, Any]) -> str:
    key = {
        "event": rec.get("event"),
        "lane": rec.get("lane"),
        "row_id": rec.get("row_id"),
        "row_out": rec.get("row_out"),
        "run_id": rec.get("run_id"),
        "created_at": rec.get("created_at"),
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def _done_ids(path: Path) -> set[str]:
    return {str(r.get("event_id")) for r in _read_jsonl(path) if r.get("event_id")}


def _queue_connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS event_queue (
          event_id TEXT PRIMARY KEY,
          lane TEXT NOT NULL,
          event_type TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'ready',
          priority INTEGER NOT NULL DEFAULT 0,
          source_event_json TEXT NOT NULL,
          claimed_by TEXT,
          claimed_at REAL,
          leased_until REAL,
          attempts INTEGER NOT NULL DEFAULT 0,
          done_at REAL,
          result_json TEXT
        )
        """
    )
    con.commit()
    return con


def _seed_queue(con: sqlite3.Connection, lane: str, events: list[dict[str, Any]], event_type: str) -> int:
    inserted = 0
    for rec in events:
        eid = _event_id(rec)
        cur = con.execute(
            """
            INSERT OR IGNORE INTO event_queue
              (event_id, lane, event_type, status, source_event_json)
            VALUES (?, ?, ?, 'ready', ?)
            """,
            (eid, lane, event_type, json.dumps(rec, sort_keys=True)),
        )
        inserted += int(cur.rowcount == 1)
    con.commit()
    return inserted


def _claim_event(con: sqlite3.Connection, lane: str, event_type: str,
                 worker_id: str, lease_seconds: int) -> tuple[str, dict[str, Any]] | None:
    now = time.time()
    until = now + lease_seconds
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        """
        SELECT event_id, source_event_json
        FROM event_queue
        WHERE lane = ?
          AND event_type = ?
          AND (status = 'ready' OR (status = 'claimed' AND leased_until < ?))
        ORDER BY priority DESC, event_id ASC
        LIMIT 1
        """,
        (lane, event_type, now),
    ).fetchone()
    if row is None:
        con.commit()
        return None
    eid = str(row[0])
    con.execute(
        """
        UPDATE event_queue
        SET status = 'claimed', claimed_by = ?, claimed_at = ?, leased_until = ?,
            attempts = attempts + 1
        WHERE event_id = ?
        """,
        (worker_id, now, until, eid),
    )
    con.commit()
    return eid, json.loads(str(row[1]))


def _finish_event(con: sqlite3.Connection, event_id: str, status: str, result: dict[str, Any]) -> None:
    con.execute(
        """
        UPDATE event_queue
        SET status = ?, done_at = ?, result_json = ?, leased_until = NULL
        WHERE event_id = ?
        """,
        (status, time.time(), json.dumps(result, sort_keys=True), event_id),
    )
    con.commit()


def _candidate_families(rec: dict[str, Any]) -> list[str]:
    families = sorted({
        str(c.get("action_family"))
        for c in rec.get("closed_candidates") or []
        if c.get("action_family")
    })
    return families


def _candidate_names(rec: dict[str, Any]) -> list[str]:
    return sorted({
        str(c.get("candidate"))
        for c in rec.get("closed_candidates") or []
        if c.get("candidate")
    })


def _run_governed_row(args: argparse.Namespace, row_id: str, lane: str, families: list[str],
                      names: list[str], out: Path) -> tuple[dict[str, Any], float, list[str], str]:
    t0 = time.monotonic()
    attempted = list(names)
    mode = args.candidate_mode
    if mode == "first_then_all" and names:
        attempted = [names[0]]
    obj = smoke.run(
        row_id,
        Path(args.corpus),
        Path(args.static_filter),
        out,
        args.timeout,
        args.max_candidates,
        args.max_actions,
        None,
        True,
        [],
        families,
        attempted,
    )
    if mode == "first_then_all" and not obj.get("n_ratified") and len(names) > 1:
        attempted = list(names)
        obj = smoke.run(
            row_id,
            Path(args.corpus),
            Path(args.static_filter),
            out,
            args.timeout,
            args.max_candidates,
            args.max_actions,
            None,
            True,
            [],
            families,
            attempted,
        )
        mode = "first_then_all_fallback_all"
    return obj, round(time.monotonic() - t0, 3), attempted, mode


def consume_govern(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    lane = args.lane
    event_dir = root / lane / "events"
    checkpoint = Path(args.checkpoint) if args.checkpoint else root / lane / "consumers" / "path_b_governance.jsonl"
    done = _done_ids(checkpoint)
    events = _read_jsonl(event_dir / "to_govern.jsonl")
    queue_db = Path(args.queue_db) if args.queue_db else root / "factory_queue.sqlite"
    queue_con = _queue_connect(queue_db) if args.use_sqlite_queue else None
    queued_inserted = _seed_queue(queue_con, lane, events, "to_govern") if queue_con else 0
    worker_id = args.worker_id or f"{os.uname().nodename}:{os.getpid()}"
    consumed = 0
    ratified = 0
    residualized = 0
    seq_events: list[tuple[str, dict[str, Any]]] = []
    if not queue_con:
        for idx, rec in enumerate(events):
            if args.worker_count > 1 and idx % args.worker_count != args.worker_index:
                continue
            seq_events.append((_event_id(rec), rec))

    while True:
        if queue_con:
            claimed = _claim_event(queue_con, lane, "to_govern", worker_id, args.lease_seconds)
            if claimed is None:
                break
            eid, rec = claimed
        else:
            if not seq_events:
                break
            eid, rec = seq_events.pop(0)
        if eid in done:
            continue
        families = _candidate_families(rec)
        names = _candidate_names(rec)
        row_id = str(rec.get("row_id") or "")
        if not row_id or not families or not names:
            _append_jsonl(checkpoint, {
                "event_id": eid,
                "status": "skipped",
                "reason": "missing_row_action_family_or_candidate_name",
                "source_event": rec,
                "created_at": _now_iso(),
            })
            if queue_con:
                _finish_event(queue_con, eid, "skipped", {"reason": "missing_row_action_family_or_candidate_name"})
            continue
        t0 = time.monotonic()
        out = root / lane / "path_b_governed" / f"{row_id}.json"
        obj, cycle_s, attempted_names, candidate_mode_used = _run_governed_row(
            args, row_id, lane, families, names, out
        )
        base = {
            "schema": "leansearch-factory-event-v1",
            "created_at": _now_iso(),
            "run_id": rec.get("run_id"),
            "consumer": "path_b_governance",
            "source_event_id": eid,
            "lane": lane,
            "row_id": row_id,
            "row_out": str(out),
            "cycle_s": cycle_s,
            "candidate_mode": candidate_mode_used,
            "candidate_names_attempted": attempted_names,
        }
        if obj.get("n_ratified"):
            ratified += 1
            _append_jsonl(event_dir / "closed.jsonl", {
                **base,
                "event": "ratified_closure",
                "ratified_candidates": obj.get("ratified_candidates", []),
            })
            status = "ratified"
            queue_status = "done"
        else:
            residualized += 1
            _append_jsonl(event_dir / "path_c_residuals.jsonl", {
                **base,
                "event": "path_c_residual",
                "residual_class": "governance_failed",
                "next_lever": "inspect_path_b_failure_or_repair_candidate",
                "error_counts": {},
                "sample_tail": "",
            })
            status = "residualized"
            queue_status = "residualized"
        result_rec = {
            "status": status,
            "row_id": row_id,
            "families": families,
            "candidate_names": names,
            "candidate_names_attempted": attempted_names,
            "candidate_mode": candidate_mode_used,
            "out": str(out),
            "cycle_s": cycle_s,
            "created_at": _now_iso(),
        }
        _append_jsonl(checkpoint, {
            "event_id": eid,
            **result_rec,
        })
        if queue_con:
            _finish_event(queue_con, eid, queue_status, result_rec)
        consumed += 1
        if args.limit is not None and consumed >= args.limit:
            break
    return {
        "schema": "leansearch-factory-consumer-summary-v1",
        "consumer": "path_b_governance",
        "root": str(root),
        "lane": lane,
        "events_seen": len(events),
        "worker_index": args.worker_index,
        "worker_count": args.worker_count,
        "worker_id": worker_id,
        "queue_db": str(queue_db) if queue_con else "",
        "queued_inserted": queued_inserted,
        "consumed": consumed,
        "ratified": ratified,
        "residualized": residualized,
        "checkpoint": str(checkpoint),
    }


def _self_test() -> int:
    rec = {"event": "x", "lane": "l", "row_id": "r", "closed_candidates": [{"action_family": "a"}]}
    assert _event_id(rec) == _event_id(dict(rec))
    assert _candidate_families(rec) == ["a"]
    assert _candidate_names({"closed_candidates": [{"candidate": "C.z"}, {"candidate": "C.z"}]}) == ["C.z"]
    with sqlite3.connect(":memory:") as con:
        con.execute(
            """
            CREATE TABLE event_queue (
              event_id TEXT PRIMARY KEY, lane TEXT, event_type TEXT, status TEXT,
              priority INTEGER DEFAULT 0, source_event_json TEXT, claimed_by TEXT,
              claimed_at REAL, leased_until REAL, attempts INTEGER DEFAULT 0,
              done_at REAL, result_json TEXT
            )
            """
        )
        _seed_queue(con, "l", [rec], "to_govern")
        assert _claim_event(con, "l", "to_govern", "w1", 60) is not None
        assert _claim_event(con, "l", "to_govern", "w2", 60) is None
    print("leansearch_factory_consume self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=False, default="/tmp/rung1/leansearch_factory")
    ap.add_argument("--lane", required=False, default="summability_transport")
    ap.add_argument("--consumer", choices=["govern"], default="govern")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", default=DEFAULT_FILTER)
    ap.add_argument("--checkpoint")
    ap.add_argument("--timeout", type=int, default=160)
    ap.add_argument("--max-candidates", type=int, default=4)
    ap.add_argument("--max-actions", type=int, default=2)
    ap.add_argument("--worker-index", type=int, default=0)
    ap.add_argument("--worker-count", type=int, default=1)
    ap.add_argument("--candidate-mode", choices=["first_then_all", "all"], default="first_then_all")
    ap.add_argument("--use-sqlite-queue", action="store_true")
    ap.add_argument("--queue-db")
    ap.add_argument("--worker-id", default="")
    ap.add_argument("--lease-seconds", type=int, default=900)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(consume_govern(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
