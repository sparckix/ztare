#!/usr/bin/env python3
"""SQLite WorkItem queue plus append-only JSONL event ledger for LeanMill.

Phase A migration (2026-05-23): canonical home moved here from
``scripts/public/control/leanmill/work_queue.py``. That script keeps a
shim re-export so existing ``import leanmill_work_queue as work_queue``
patterns used by ~14 worker scripts continue to work without modification.

This module is the LeanMill subsystem's durable bus. It must remain
side-effect-free at import time, depend only on stdlib and
``ztare.leanmill.paths``, and never import from ``scripts/`` (per the
boundary rules in ``scripts/README.md``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ztare.leanmill.contracts import handoff as handoff_contract
from ztare.leanmill.paths import DATA_DIR, FACTORY_POLICY

DEFAULT_DB = os.environ.get("LEANMILL_QUEUE_DB", f"{DATA_DIR}/leanmill_work_queue.sqlite")
DEFAULT_EVENTS = os.environ.get("LEANMILL_EVENTS", f"{DATA_DIR}/leanmill_events.jsonl")
STATUSES = {"queued", "claimed", "running", "done", "failed", "retired", "dead_letter"}
PROCESS_STARTED_AT = int(time.time())
FALLBACK_STALE_PROCESS_GRACE_S = 10
FALLBACK_WORKER_HEARTBEAT_STALE_S = 900


def node_id() -> str:
    return os.environ.get("LEANMILL_NODE_ID") or os.uname().nodename


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run_git(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=_repo_root(),
            text=True,
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _tracked_status_receipt() -> dict[str, Any]:
    raw = _run_git(["status", "--porcelain", "--untracked-files=no"])
    lines = [line for line in raw.splitlines() if line.strip()]
    return {
        "tracked_change_count": len(lines),
        "tracked_status_hash": hashlib.sha256(raw.encode()).hexdigest() if raw else "",
    }


def _read_policy(path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    # Delegates to the canonical `policy.read_policy` (was a byte-identical copy — the forgotten-sibling shape,
    # de-duplicated 2026-06-22). Lazy import keeps work_queue ↔ policy cycle-free.
    from ztare.leanmill.policy import read_policy as _rp
    return _rp(path)


def _policy_paths_from_globs(*, glob_key: str, fallback_globs: list[str], files_key: str, fallback_files: list[str]) -> list[Path]:
    root = _repo_root()
    runtime = _read_policy().get("runtime_version")
    runtime = runtime if isinstance(runtime, dict) else {}
    paths: list[Path] = []
    globs = runtime.get(glob_key)
    if not isinstance(globs, list) or not globs:
        globs = fallback_globs
    for pattern in globs:
        paths.extend(sorted(root.glob(str(pattern))))
    files = runtime.get(files_key)
    if not isinstance(files, list) or not files:
        files = fallback_files
    for rel in files:
        p = root / rel
        if p.exists():
            paths.append(p)
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        rp = path.resolve()
        if rp in seen or not rp.is_file():
            continue
        seen.add(rp)
        out.append(path)
    return out


def _watched_source_paths() -> list[Path]:
    return _policy_paths_from_globs(
        glob_key="watch_source_globs",
        fallback_globs=["scripts/public/control/leanmill_*.py"],
        files_key="watch_source_files",
        fallback_files=[
            "scripts/public/control/leanmill/search/repair_family_registry.py",
            FACTORY_POLICY,
            "research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md",
            "research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md",
        ],
    )


def _watched_data_paths() -> list[Path]:
    return _policy_paths_from_globs(
        glob_key="watch_data_globs",
        fallback_globs=["analytics/public/leanmill/repair_families/*.yaml"],
        files_key="watch_data_files",
        fallback_files=[],
    )


def _watched_source_digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    root = _repo_root()
    for path in paths:
        try:
            rel = path.resolve().relative_to(root.resolve())
            data = path.read_bytes()
        except (OSError, ValueError):
            continue
        h.update(str(rel).encode())
        h.update(b"\0")
        h.update(hashlib.sha256(data).hexdigest().encode())
        h.update(b"\0")
    return h.hexdigest()


def runtime_version_settings(policy_path: str | Path = FACTORY_POLICY, *, profile_name: str = "") -> dict[str, int]:
    policy = _read_policy(policy_path)
    values: dict[str, Any] = {}
    runtime = policy.get("runtime_version")
    if isinstance(runtime, dict):
        values.update(runtime)
    if profile_name:
        profile = ((policy.get("profiles") or {}).get(profile_name) or {})
        profile_runtime = profile.get("runtime_version")
        if isinstance(profile_runtime, dict):
            values.update(profile_runtime)
        runner = profile.get("runner")
        if isinstance(runner, dict) and "worker_heartbeat_stale_s" in runner:
            values["worker_heartbeat_stale_s"] = runner["worker_heartbeat_stale_s"]

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(values.get(key) if values.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    return {
        "stale_process_grace_s": max(0, int_value("stale_process_grace_s", FALLBACK_STALE_PROCESS_GRACE_S)),
        "worker_heartbeat_stale_s": max(1, int_value("worker_heartbeat_stale_s", FALLBACK_WORKER_HEARTBEAT_STALE_S)),
    }


def runtime_version_receipt(*, stale_process_grace_s: int | None = None, policy_profile: str = "") -> dict[str, Any]:
    settings = runtime_version_settings(profile_name=policy_profile)
    grace_s = int(stale_process_grace_s if stale_process_grace_s is not None else settings["stale_process_grace_s"])
    paths = _watched_source_paths()
    data_paths = _watched_data_paths()
    mtimes: list[int] = []
    for path in paths:
        try:
            mtimes.append(int(path.stat().st_mtime))
        except OSError:
            pass
    latest_mtime = max(mtimes) if mtimes else 0
    process_started_at = int(os.environ.get("LEANMILL_PROCESS_STARTED_AT") or PROCESS_STARTED_AT)
    status_receipt = _tracked_status_receipt()
    return {
        "schema": "leanmill-runtime-version-receipt-v1",
        "node_id": node_id(),
        "process_started_at": process_started_at,
        "pid": os.getpid(),
        "stale_process_grace_s": grace_s,
        "git_head": _run_git(["rev-parse", "--short=12", "HEAD"]),
        **status_receipt,
        "watched_source_hash": _watched_source_digest(paths),
        "watched_source_file_count": len(paths),
        "watched_source_mtime_max": latest_mtime,
        "watched_data_hash": _watched_source_digest(data_paths),
        "watched_data_file_count": len(data_paths),
        "stale_process_likely": bool(latest_mtime > process_started_at + grace_s),
        "stale_reason": (
            "watched_source_newer_than_worker_process"
            if latest_mtime > process_started_at + grace_s else ""
        ),
    }


def _now() -> int:
    return int(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha_file(path: str) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def connect(db: str) -> sqlite3.Connection:
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(db, timeout=30.0)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA busy_timeout=5000")
    cx.execute(
        """
        CREATE TABLE IF NOT EXISTS work_items (
          work_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          priority INTEGER NOT NULL,
          status TEXT NOT NULL,
          attempts INTEGER NOT NULL,
          max_attempts INTEGER NOT NULL,
          claimed_by TEXT,
          lease_until INTEGER,
          family TEXT,
          station TEXT,
          expected_exit TEXT,
          payload_json TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL
        )
        """
    )
    existing_cols = {row["name"] for row in cx.execute("PRAGMA table_info(work_items)").fetchall()}
    for col in ("family", "station", "expected_exit", "required_capability"):
        if col not in existing_cols:
            cx.execute(f"ALTER TABLE work_items ADD COLUMN {col} TEXT")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_work_pick ON work_items(status, priority DESC, created_at)")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_work_family_kind_status ON work_items(family, kind, status)")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_work_required_capability ON work_items(required_capability) WHERE required_capability IS NOT NULL")
    cx.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_heartbeats (
          worker_id TEXT PRIMARY KEY,
          node_id TEXT,
          last_seen_at INTEGER NOT NULL,
          process_started_at INTEGER NOT NULL,
          pid INTEGER,
          git_head TEXT,
          git_status_tracked TEXT,
          tracked_status_hash TEXT,
          tracked_change_count INTEGER,
          watched_source_hash TEXT,
          watched_source_file_count INTEGER,
          watched_source_mtime_max INTEGER,
          watched_data_hash TEXT,
          watched_data_file_count INTEGER,
          stale_process_likely INTEGER NOT NULL,
          stale_reason TEXT,
          claimed_work_id TEXT,
          worker_kind TEXT,
          payload_json TEXT NOT NULL
        )
        """
    )
    existing_hb_cols = {row["name"] for row in cx.execute("PRAGMA table_info(worker_heartbeats)").fetchall()}
    for col, typ in (
        ("node_id", "TEXT"),
        ("tracked_status_hash", "TEXT"),
        ("tracked_change_count", "INTEGER"),
        ("watched_data_hash", "TEXT"),
        ("watched_data_file_count", "INTEGER"),
    ):
        if col not in existing_hb_cols:
            cx.execute(f"ALTER TABLE worker_heartbeats ADD COLUMN {col} {typ}")
    cx.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact_refs (
          artifact_key TEXT PRIMARY KEY,
          role TEXT NOT NULL,
          path TEXT NOT NULL,
          sha256 TEXT,
          schema_name TEXT,
          producer TEXT,
          run_id TEXT,
          node_id TEXT,
          updated_at INTEGER NOT NULL,
          payload_json TEXT NOT NULL
        )
        """
    )
    cx.execute("CREATE INDEX IF NOT EXISTS idx_artifact_refs_role ON artifact_refs(role, updated_at DESC)")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_artifact_refs_path ON artifact_refs(path)")
    cx.commit()
    return cx


def record_artifact_ref(
    cx: sqlite3.Connection,
    *,
    artifact_key: str,
    role: str,
    path: str | Path,
    payload: dict[str, Any] | None = None,
    producer: str = "",
    schema: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    """Record the authoritative role of a mutable factory artifact path.

    The WorkItem queue remains the durable bus; this table is the read-model
    companion for named artifacts whose file paths are otherwise easy to
    overwrite accidentally. It is node-local authority, not a distributed
    multi-writer file sync mechanism.
    """
    key = str(artifact_key or "").strip()
    if not key:
        raise ValueError("artifact_key is required")
    role_text = str(role or "").strip()
    if not role_text:
        raise ValueError("role is required")
    path_text = str(path)
    file_payload = _read_json_file(path_text)
    payload_obj = dict(file_payload)
    if payload:
        payload_obj.update(payload)
    schema_text = str(schema or payload_obj.get("schema") or "")
    run_id_text = str(run_id or payload_obj.get("run_id") or "")
    rec = {
        "schema": "leanmill-artifact-ref-v1",
        "artifact_key": key,
        "role": role_text,
        "path": path_text,
        "sha256": _sha_file(path_text),
        "schema_name": schema_text,
        "producer": str(producer or ""),
        "run_id": run_id_text,
        "node_id": node_id(),
        "updated_at": _now(),
        "payload": payload_obj,
    }
    cx.execute(
        """
        INSERT INTO artifact_refs
        (artifact_key, role, path, sha256, schema_name, producer, run_id, node_id, updated_at, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(artifact_key) DO UPDATE SET
          role=excluded.role,
          path=excluded.path,
          sha256=excluded.sha256,
          schema_name=excluded.schema_name,
          producer=excluded.producer,
          run_id=excluded.run_id,
          node_id=excluded.node_id,
          updated_at=excluded.updated_at,
          payload_json=excluded.payload_json
        """,
        (
            rec["artifact_key"],
            rec["role"],
            rec["path"],
            rec["sha256"],
            rec["schema_name"],
            rec["producer"],
            rec["run_id"],
            rec["node_id"],
            rec["updated_at"],
            _json(payload_obj),
        ),
    )
    cx.commit()
    return rec


def _artifact_ref_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    obj = dict(row)
    try:
        payload = json.loads(obj.pop("payload_json") or "{}")
    except json.JSONDecodeError:
        payload = {}
    obj["payload"] = payload if isinstance(payload, dict) else {}
    obj["schema"] = "leanmill-artifact-ref-v1"
    return obj


def artifact_ref(cx: sqlite3.Connection, artifact_key: str) -> dict[str, Any] | None:
    row = cx.execute("SELECT * FROM artifact_refs WHERE artifact_key=?", (str(artifact_key),)).fetchone()
    return _artifact_ref_row_to_dict(row) if row else None


def artifact_refs(cx: sqlite3.Connection, *, role: str = "", limit: int = 100) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if role:
        where = "WHERE role=?"
        params.append(role)
    rows = cx.execute(
        f"SELECT * FROM artifact_refs {where} ORDER BY updated_at DESC, artifact_key ASC LIMIT ?",
        [*params, max(1, int(limit))],
    ).fetchall()
    return [_artifact_ref_row_to_dict(row) for row in rows]


def artifact_refs_for_path(cx: sqlite3.Connection, path: str | Path, *, limit: int = 20) -> list[dict[str, Any]]:
    path_text = str(path)
    rows = cx.execute(
        """
        SELECT *
        FROM artifact_refs
        WHERE path=?
        ORDER BY updated_at DESC, artifact_key ASC
        LIMIT ?
        """,
        (path_text, max(1, int(limit))),
    ).fetchall()
    return [_artifact_ref_row_to_dict(row) for row in rows]


def _is_sqlite_busy(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "database is locked" in msg or "database is busy" in msg or "locked" in msg


def _rollback_safely(cx: sqlite3.Connection) -> None:
    try:
        cx.rollback()
    except sqlite3.Error:
        pass


def _sleep_for_sqlite_retry(attempt: int) -> None:
    time.sleep(min(2.0, 0.05 * (2 ** max(0, attempt))))


def append_event(events_path: str, event: dict[str, Any]) -> dict[str, Any]:
    rec = {
        "event_id": event.get("event_id") or str(uuid.uuid4()),
        "timestamp": event.get("timestamp") or _now(),
        "node_id": event.get("node_id") or node_id(),
        **event,
    }
    artifacts = []
    for path in rec.get("artifact_paths") or []:
        artifacts.append({"path": path, "sha256": _sha_file(str(path))})
    if artifacts:
        rec["artifacts"] = artifacts
    p = Path(events_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return rec


def enqueue(cx: sqlite3.Connection, *, kind: str, priority: int, payload: dict[str, Any], max_attempts: int = 3) -> str:
    work_id = str(payload.get("work_id") or uuid.uuid4())
    family = str(payload.get("family") or "")
    station = str(payload.get("station") or "")
    expected_exit = str(payload.get("expected_exit") or payload.get("exit_kind") or "")
    now = _now()
    payload_json = _json(payload)
    for attempt in range(8):
        try:
            cx.execute(
                """
                INSERT OR IGNORE INTO work_items
                (work_id, kind, priority, status, attempts, max_attempts, claimed_by, lease_until, family, station, expected_exit, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, 'queued', 0, ?, NULL, NULL, ?, ?, ?, ?, ?, ?)
                """,
                (work_id, kind, int(priority), int(max_attempts), family, station, expected_exit, payload_json, now, now),
            )
            cx.execute(
                """
                UPDATE work_items
                SET kind=?, priority=?, status='queued', attempts=0, max_attempts=?,
                    claimed_by=NULL, lease_until=NULL, family=?, station=?, expected_exit=?,
                    payload_json=?, updated_at=?
                WHERE work_id=? AND status IN ('failed', 'retired', 'dead_letter')
                """,
                (kind, int(priority), int(max_attempts), family, station, expected_exit, payload_json, now, work_id),
            )
            cx.commit()
            return work_id
        except sqlite3.OperationalError as exc:
            _rollback_safely(cx)
            if not _is_sqlite_busy(exc) or attempt == 7:
                raise
            _sleep_for_sqlite_retry(attempt)
    return work_id


def record_terminal_item(
    cx: sqlite3.Connection,
    *,
    kind: str,
    status: str,
    priority: int,
    payload: dict[str, Any],
    max_attempts: int = 1,
) -> str:
    if status not in {"done", "failed", "retired", "dead_letter"}:
        raise ValueError(f"terminal status required: {status}")
    work_id = str(payload.get("work_id") or uuid.uuid4())
    _apply_terminal_payload_defaults(payload, status=status)
    family = str(payload.get("family") or "")
    station = str(payload.get("station") or "")
    expected_exit = str(payload.get("expected_exit") or payload.get("exit_kind") or "")
    now = _now()
    cx.execute(
        """
        INSERT OR IGNORE INTO work_items
        (work_id, kind, priority, status, attempts, max_attempts, claimed_by, lease_until, family, station, expected_exit, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, NULL, NULL, ?, ?, ?, ?, ?, ?)
        """,
        (work_id, kind, int(priority), status, int(max_attempts), family, station, expected_exit, _json(payload), now, now),
    )
    cx.execute(
        """
        UPDATE work_items
        SET kind=?, priority=?, status=?, attempts=0, max_attempts=?,
            claimed_by=NULL, lease_until=NULL, family=?, station=?, expected_exit=?,
            payload_json=?, updated_at=?
        WHERE work_id=? AND status IN ('failed', 'retired', 'dead_letter')
        """,
        (kind, int(priority), status, int(max_attempts), family, station, expected_exit, _json(payload), now, work_id),
    )
    cx.commit()
    return work_id


def reclaim_expired(cx: sqlite3.Connection, *, events_path: str | None = None) -> int:
    now = _now()
    dead_rows = cx.execute(
        """
        SELECT work_id, kind, claimed_by, attempts, max_attempts, lease_until
        FROM work_items
        WHERE status IN ('claimed', 'running') AND lease_until IS NOT NULL AND lease_until < ? AND attempts >= max_attempts
        """,
        (now,),
    ).fetchall()
    requeue_rows = cx.execute(
        """
        SELECT work_id, kind, claimed_by, attempts, max_attempts, lease_until
        FROM work_items
        WHERE status IN ('claimed', 'running') AND lease_until IS NOT NULL AND lease_until < ? AND attempts < max_attempts
        """,
        (now,),
    ).fetchall()
    cx.execute(
        """
        UPDATE work_items
        SET status='dead_letter', claimed_by=NULL, lease_until=NULL, updated_at=?
        WHERE status IN ('claimed', 'running') AND lease_until IS NOT NULL AND lease_until < ? AND attempts >= max_attempts
        """,
        (now, now),
    )
    cur = cx.execute(
        """
        UPDATE work_items
        SET status='queued', claimed_by=NULL, lease_until=NULL, updated_at=?
        WHERE status IN ('claimed', 'running') AND lease_until IS NOT NULL AND lease_until < ? AND attempts < max_attempts
        """,
        (now, now),
    )
    cx.commit()
    if events_path and (dead_rows or requeue_rows):
        append_event(events_path, {
            "event_type": "expired_leases_reclaimed",
            "payload": {
                "requeued_count": len(requeue_rows),
                "dead_lettered_count": len(dead_rows),
                "requeued": [dict(row) for row in requeue_rows[:20]],
                "dead_lettered": [dict(row) for row in dead_rows[:20]],
            },
        })
    return int(cur.rowcount or 0)


def terminalize_exhausted_queued(cx: sqlite3.Connection, *, events_path: str | None = None, limit: int = 200) -> int:
    """Dead-letter queued rows that have already spent their retry budget."""
    now = _now()
    rows = cx.execute(
        """
        SELECT work_id, kind, attempts, max_attempts, payload_json
        FROM work_items
        WHERE status='queued' AND attempts >= max_attempts
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (max(1, int(limit)),),
    ).fetchall()
    terminalized: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("exit_kind", "queue_attempt_budget_exhausted")
        payload.setdefault("learning_unit_exit", "queue_attempt_budget_exhausted")
        payload.setdefault("dead_letter_reason", "queued_attempts_exhausted_without_terminal_status")
        payload["attempts"] = int(row["attempts"] or 0)
        payload["max_attempts"] = int(row["max_attempts"] or 0)
        cur = cx.execute(
            """
            UPDATE work_items
            SET status='dead_letter', claimed_by=NULL, lease_until=NULL, payload_json=?, updated_at=?
            WHERE work_id=? AND status='queued' AND attempts >= max_attempts
            """,
            (_json(payload), now, row["work_id"]),
        )
        if int(cur.rowcount or 0) == 1:
            terminalized.append({
                "work_id": row["work_id"],
                "kind": row["kind"],
                "attempts": row["attempts"],
                "max_attempts": row["max_attempts"],
            })
    cx.commit()
    if events_path and terminalized:
        append_event(events_path, {
            "event_type": "queued_attempt_budget_exhausted_terminalized",
            "payload": {
                "terminalized_count": len(terminalized),
                "terminalized": terminalized[:40],
            },
        })
    return len(terminalized)


def reclaim_worker_claims(cx: sqlite3.Connection, *, worker_id: str) -> int:
    """Requeue nonterminal rows still leased by a restarting worker id.

    This is intentionally scoped to one worker id. It lets a daemon restart pick
    up its own abandoned in-flight row without touching work owned by a different
    live worker or waiting for the full lease window. Preserves attempts: the
    worker incremented attempts on claim, and the row was abandoned before
    completion, so the attempt counts as spent.
    """
    cur = cx.execute(
        """
        UPDATE work_items
        SET status='queued',
            claimed_by=NULL,
            lease_until=NULL,
            updated_at=?
        WHERE status IN ('claimed', 'running') AND claimed_by=?
        """,
        (_now(), worker_id),
    )
    cx.commit()
    return int(cur.rowcount or 0)


def reclaim_all_open_claims(cx: sqlite3.Connection, *, events_path: str | None = None, reason: str = "factory_shutdown") -> int:
    """Requeue all claimed/running rows during an intentional full-factory stop."""
    rows = cx.execute(
        """
        SELECT work_id, kind, claimed_by, attempts, max_attempts, lease_until
        FROM work_items
        WHERE status IN ('claimed', 'running')
        ORDER BY updated_at ASC
        """
    ).fetchall()
    cur = cx.execute(
        """
        UPDATE work_items
        SET status='queued',
            attempts=CASE WHEN attempts > 0 THEN attempts - 1 ELSE attempts END,
            claimed_by=NULL,
            lease_until=NULL,
            updated_at=?
        WHERE status IN ('claimed', 'running')
        """,
        (_now(),),
    )
    cx.commit()
    count = int(cur.rowcount or 0)
    if events_path and count:
        append_event(events_path, {
            "event_type": "open_claims_reclaimed",
            "payload": {
                "reason": reason,
                "reclaimed_count": count,
                "reclaimed": [dict(row) for row in rows[:40]],
            },
        })
    return count


def reclaim_terminated_worker_claims(
    cx: sqlite3.Connection,
    *,
    version_health: dict[str, Any],
    events_path: str | None = None,
    reason: str = "terminated_worker_claim_reclaim",
    max_rows: int = 50,
) -> int:
    """Requeue nonterminal claims whose recorded worker process is dead.

    This is the watchdog/deploy-restart companion to ``reclaim_expired``. Lease
    expiry protects ordinary crashes, but a supervised tmux restart can leave a
    max-attempt row in ``running`` until it dead-letters. We only reclaim rows
    whose current ``claimed_by`` still matches a terminated heartbeat record and
    whose ``claimed_work_id`` matches the row, then refund the claim attempt
    because the owning process was intentionally removed by the control plane.
    """
    terminated = version_health.get("terminated_heartbeats")
    if not isinstance(terminated, list):
        return 0
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for rec in terminated:
        if not isinstance(rec, dict):
            continue
        worker_id = str(rec.get("worker_id") or "")
        work_id = str(rec.get("claimed_work_id") or "")
        if not worker_id or not work_id:
            continue
        key = (worker_id, work_id)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(key)
        if len(candidates) >= max(1, int(max_rows)):
            break
    if not candidates:
        return 0

    now = _now()
    reclaimed: list[dict[str, Any]] = []
    for worker_id, work_id in candidates:
        row = cx.execute(
            """
            SELECT work_id, kind, status, claimed_by, attempts, max_attempts, lease_until
            FROM work_items
            WHERE work_id=? AND claimed_by=? AND status IN ('claimed', 'running')
            """,
            (work_id, worker_id),
        ).fetchone()
        if row is None:
            continue
        cur = cx.execute(
            """
            UPDATE work_items
            SET status='queued',
                attempts=CASE WHEN attempts > 0 THEN attempts - 1 ELSE attempts END,
                claimed_by=NULL,
                lease_until=NULL,
                updated_at=?
            WHERE work_id=? AND claimed_by=? AND status IN ('claimed', 'running')
            """,
            (now, work_id, worker_id),
        )
        if int(cur.rowcount or 0) == 1:
            reclaimed.append(dict(row))
    cx.commit()
    if events_path and reclaimed:
        append_event(events_path, {
            "event_type": "terminated_worker_claims_reclaimed",
            "payload": {
                "reason": reason,
                "reclaimed_count": len(reclaimed),
                "reclaimed": reclaimed[:40],
            },
        })
    return len(reclaimed)


def record_worker_heartbeat(
    cx: sqlite3.Connection,
    *,
    worker_id: str,
    claimed_work_id: str = "",
    worker_kind: str = "",
    payload: dict[str, Any] | None = None,
    stale_process_grace_s: int | None = None,
    policy_profile: str = "",
) -> dict[str, Any]:
    receipt = runtime_version_receipt(stale_process_grace_s=stale_process_grace_s, policy_profile=policy_profile)
    now = _now()
    rec_payload = {
        "runtime_version": receipt,
        **(payload or {}),
    }
    cx.execute(
        """
        INSERT INTO worker_heartbeats
        (worker_id, node_id, last_seen_at, process_started_at, pid, git_head, git_status_tracked,
         tracked_status_hash, tracked_change_count,
         watched_source_hash, watched_source_file_count, watched_source_mtime_max,
         watched_data_hash, watched_data_file_count,
         stale_process_likely, stale_reason, claimed_work_id, worker_kind, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(worker_id) DO UPDATE SET
          node_id=excluded.node_id,
          last_seen_at=excluded.last_seen_at,
          process_started_at=excluded.process_started_at,
          pid=excluded.pid,
          git_head=excluded.git_head,
          git_status_tracked=excluded.git_status_tracked,
          tracked_status_hash=excluded.tracked_status_hash,
          tracked_change_count=excluded.tracked_change_count,
          watched_source_hash=excluded.watched_source_hash,
          watched_source_file_count=excluded.watched_source_file_count,
          watched_source_mtime_max=excluded.watched_source_mtime_max,
          watched_data_hash=excluded.watched_data_hash,
          watched_data_file_count=excluded.watched_data_file_count,
          stale_process_likely=excluded.stale_process_likely,
          stale_reason=excluded.stale_reason,
          claimed_work_id=excluded.claimed_work_id,
          worker_kind=excluded.worker_kind,
          payload_json=excluded.payload_json
        """,
        (
            worker_id,
            str(receipt.get("node_id") or node_id()),
            now,
            int(receipt.get("process_started_at") or 0),
            int(receipt.get("pid") or 0),
            str(receipt.get("git_head") or ""),
            "",
            str(receipt.get("tracked_status_hash") or ""),
            int(receipt.get("tracked_change_count") or 0),
            str(receipt.get("watched_source_hash") or ""),
            int(receipt.get("watched_source_file_count") or 0),
            int(receipt.get("watched_source_mtime_max") or 0),
            str(receipt.get("watched_data_hash") or ""),
            int(receipt.get("watched_data_file_count") or 0),
            int(bool(receipt.get("stale_process_likely"))),
            str(receipt.get("stale_reason") or ""),
            claimed_work_id,
            worker_kind,
            _json(rec_payload),
        ),
    )
    cx.commit()
    return rec_payload


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_command(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        proc = subprocess.run(["ps", "-p", str(pid), "-o", "command="], text=True, capture_output=True, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _pid_identity_matches_worker(command: str, *, worker_id: str) -> bool:
    """Reject stale heartbeats when the OS has reused a recorded PID.

    The runtime gate uses PID liveness as a cheap heartbeat sanity check. That
    is not enough across restarts: a new worker can reuse an old PID while the
    DB row still names the previous worker. When the command line carries an
    explicit --worker-id, treat mismatch as a terminated stale heartbeat.
    """
    if not command or not worker_id:
        return True
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for idx, part in enumerate(parts):
        if part == "--worker-id" and idx + 1 < len(parts):
            return parts[idx + 1] == worker_id
        if part.startswith("--worker-id="):
            return part.split("=", 1)[1] == worker_id
    return True


def worker_version_health(cx: sqlite3.Connection, *, stale_after_s: int | None = None, policy_profile: str = "") -> dict[str, Any]:
    now = _now()
    settings = runtime_version_settings(profile_name=policy_profile)
    heartbeat_stale_s = int(stale_after_s if stale_after_s is not None and stale_after_s > 0 else settings["worker_heartbeat_stale_s"])
    try:
        rows = cx.execute(
            """
            SELECT *
            FROM worker_heartbeats
            ORDER BY last_seen_at DESC, worker_id ASC
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return {"schema": "leanmill-worker-version-health-v1", "available": False}
    active: list[dict[str, Any]] = []
    terminated_heartbeats: list[dict[str, Any]] = []
    stale_processes: list[dict[str, Any]] = []
    stale_heartbeats: list[dict[str, Any]] = []
    runtime_mismatches: list[dict[str, Any]] = []
    git_heads: dict[str, int] = {}
    hashes: dict[str, int] = {}
    data_hashes: dict[str, int] = {}
    data_mismatches: list[dict[str, Any]] = []
    current_runtime = runtime_version_receipt(policy_profile=policy_profile)
    current_hash = str(current_runtime.get("watched_source_hash") or "")
    current_data_hash = str(current_runtime.get("watched_data_hash") or "")
    current_git_head = str(current_runtime.get("git_head") or "")
    for row in rows:
        age_s = max(0, now - int(row["last_seen_at"]))
        pid = int(row["pid"] or 0)
        process_alive = _pid_is_alive(pid)
        process_command = _pid_command(pid) if process_alive else ""
        process_identity_match = _pid_identity_matches_worker(process_command, worker_id=str(row["worker_id"] or ""))
        try:
            heartbeat_payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            heartbeat_payload = {}
        rec = {
            "worker_id": row["worker_id"],
            "node_id": row["node_id"] or "",
            "last_seen_at": int(row["last_seen_at"]),
            "heartbeat_age_s": age_s,
            "process_started_at": int(row["process_started_at"]),
            "pid": row["pid"],
            "process_alive": process_alive,
            "process_identity_match": process_identity_match,
            "process_command_tail": process_command[-240:],
            "git_head": row["git_head"],
            "tracked_status_hash": row["tracked_status_hash"],
            "tracked_change_count": int(row["tracked_change_count"] or 0),
            "watched_source_hash": row["watched_source_hash"],
            "watched_source_mtime_max": int(row["watched_source_mtime_max"] or 0),
            "watched_data_hash": row["watched_data_hash"],
            "watched_data_file_count": int(row["watched_data_file_count"] or 0),
            "stale_process_likely": bool(row["stale_process_likely"]),
            "stale_reason": row["stale_reason"],
            "claimed_work_id": row["claimed_work_id"],
            "worker_kind": row["worker_kind"],
            "payload": heartbeat_payload if isinstance(heartbeat_payload, dict) else {},
        }
        if not rec["process_alive"]:
            terminated_heartbeats.append({**rec, "terminated_reason": "pid_not_alive"})
            continue
        if not rec["process_identity_match"]:
            terminated_heartbeats.append({**rec, "terminated_reason": "pid_identity_mismatch"})
            continue
        active.append(rec)
        git_heads[str(row["git_head"] or "unknown")] = git_heads.get(str(row["git_head"] or "unknown"), 0) + 1
        hashes[str(row["watched_source_hash"] or "unknown")] = hashes.get(str(row["watched_source_hash"] or "unknown"), 0) + 1
        data_hashes[str(row["watched_data_hash"] or "unknown")] = data_hashes.get(str(row["watched_data_hash"] or "unknown"), 0) + 1
        if rec["stale_process_likely"]:
            stale_processes.append(rec)
        if (
            (current_hash and rec["watched_source_hash"] and rec["watched_source_hash"] != current_hash)
            or (current_git_head and rec["git_head"] and rec["git_head"] != current_git_head)
        ):
            runtime_mismatches.append(rec)
        if current_data_hash and rec["watched_data_hash"] and rec["watched_data_hash"] != current_data_hash:
            data_mismatches.append(rec)
        if age_s > heartbeat_stale_s:
            stale_heartbeats.append(rec)
    return {
        "schema": "leanmill-worker-version-health-v1",
        "available": True,
        "generated_at_epoch": now,
        "worker_heartbeat_stale_s": heartbeat_stale_s,
        "worker_count": len(active),
        "terminated_heartbeat_count": len(terminated_heartbeats),
        "git_heads": git_heads,
        "watched_source_hashes": hashes,
        "watched_data_hashes": data_hashes,
        "stale_process_count": len(stale_processes),
        "stale_heartbeat_count": len(stale_heartbeats),
        "runtime_mismatch_count": len(runtime_mismatches),
        "data_mismatch_count": len(data_mismatches),
        "stale_processes": stale_processes[:20],
        "stale_heartbeats": stale_heartbeats[:20],
        "runtime_mismatches": runtime_mismatches[:20],
        "data_mismatches": data_mismatches[:20],
        "terminated_heartbeats": terminated_heartbeats[:20],
        "active_heartbeats": active[:80],
        "current_runtime": current_runtime,
    }


def _record_claim_ready_heartbeat(
    cx: sqlite3.Connection,
    *,
    worker_id: str,
    worker_kind: str,
    payload: dict[str, Any] | None = None,
) -> bool:
    rec = record_worker_heartbeat(cx, worker_id=worker_id, worker_kind=worker_kind, payload=payload or {})
    runtime = rec.get("runtime_version") if isinstance(rec.get("runtime_version"), dict) else {}
    return not bool(runtime.get("stale_process_likely"))


def claim(
    cx: sqlite3.Connection,
    *,
    worker_id: str,
    kinds: list[str],
    lease_s: int,
    capabilities: list[str] | None = None,
) -> dict[str, Any] | None:
    """Claim the highest-priority queued item this worker can serve.

    `capabilities`: if provided, only items whose `required_capability` is NULL
    (lane-agnostic) or matches one of these capabilities are eligible. This is
    the cross-node routing primitive — laptop and VPS workers claim from the
    same queue but each only acts on items their node can serve. Items left
    behind by one node are picked up by the other.

    If `capabilities` is None (default), no capability filter — existing
    callers keep working unchanged.
    """
    reclaim_expired(cx)
    terminalize_exhausted_queued(cx)
    if not _record_claim_ready_heartbeat(cx, worker_id=worker_id, worker_kind="claim_waiting",
                                          payload={"claim_kinds": kinds, "capabilities": capabilities}):
        return None
    now = _now()
    where_kind = ""
    params: list[Any] = []
    if kinds:
        where_kind = "AND kind IN (%s)" % ",".join("?" for _ in kinds)
        params.extend(kinds)
    where_cap = ""
    if capabilities is not None:
        # NULL required_capability means "any node may serve this item"
        where_cap = (
            " AND (required_capability IS NULL OR required_capability IN (%s))"
            % ",".join("?" for _ in capabilities)
        )
        params.extend(capabilities)
    row = cx.execute(
        f"""
        SELECT * FROM work_items
        WHERE status='queued' AND attempts < max_attempts {where_kind} {where_cap}
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        """,
        params,
    ).fetchone()
    if row is None:
        return None
    cur = cx.execute(
        """
        UPDATE work_items
        SET status='claimed', attempts=attempts+1, claimed_by=?, lease_until=?, updated_at=?
        WHERE work_id=? AND status='queued'
        """,
        (worker_id, now + int(lease_s), now, row["work_id"]),
    )
    if cur.rowcount != 1:
        cx.rollback()
        return None
    cx.commit()
    row = cx.execute("SELECT * FROM work_items WHERE work_id=?", (row["work_id"],)).fetchone()
    if row:
        record_worker_heartbeat(cx, worker_id=worker_id, claimed_work_id=str(row["work_id"]), worker_kind=str(row["kind"]))
    return row_to_dict(row) if row else None


def claim_matching(
    cx: sqlite3.Connection,
    *,
    worker_id: str,
    kinds: list[str],
    lease_s: int,
    predicate: Callable[[dict[str, Any]], bool],
    scan_limit: int = 100,
) -> dict[str, Any] | None:
    """Claim the highest-priority queued item accepted by ``predicate``.

    This keeps lane affinity inside the queue claim boundary. Workers should not
    claim a high-priority item and then reject it locally; that would create
    false contention and hide the lane from the right worker until lease expiry.
    """
    reclaim_expired(cx)
    terminalize_exhausted_queued(cx)
    if not _record_claim_ready_heartbeat(cx, worker_id=worker_id, worker_kind="claim_matching_waiting", payload={"claim_kinds": kinds}):
        return None
    now = _now()
    where_kind = ""
    params: list[Any] = []
    if kinds:
        where_kind = "AND kind IN (%s)" % ",".join("?" for _ in kinds)
        params.extend(kinds)
    rows = cx.execute(
        f"""
        SELECT * FROM work_items
        WHERE status='queued' AND attempts < max_attempts {where_kind}
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
        """,
        [*params, max(1, int(scan_limit))],
    ).fetchall()
    for row in rows:
        item = row_to_dict(row)
        if not predicate(item):
            continue
        cur = cx.execute(
            """
            UPDATE work_items
            SET status='claimed', attempts=attempts+1, claimed_by=?, lease_until=?, updated_at=?
            WHERE work_id=? AND status='queued' AND attempts < max_attempts
            """,
            (worker_id, now + int(lease_s), now, item["work_id"]),
        )
        cx.commit()
        if int(cur.rowcount or 0) != 1:
            continue
        claimed = cx.execute("SELECT * FROM work_items WHERE work_id=?", (item["work_id"],)).fetchone()
        if claimed:
            record_worker_heartbeat(cx, worker_id=worker_id, claimed_work_id=str(claimed["work_id"]), worker_kind=str(claimed["kind"]))
        return row_to_dict(claimed) if claimed else None
    return None


def claim_specific(
    cx: sqlite3.Connection,
    *,
    work_id: str,
    worker_id: str,
    lease_s: int,
) -> bool:
    """Atomically lease ONE specific work item by id. Returns True iff THIS worker now owns it.

    The compare-and-set lease primitive for partitioning a known, finite work-list across nodes
    (vs `claim`, which pulls the next-by-priority item). A node wins iff the item is `queued`, or
    already held by this same worker (idempotent re-claim within a run). If another node holds an
    unexpired lease, this returns False and the caller skips it — its result converges via the
    fact-log merge (state_convergence). Expired leases are reclaimed first, so a dead node's items
    become claimable again."""
    reclaim_expired(cx)
    now = _now()
    cur = cx.execute(
        """
        UPDATE work_items
        SET status='claimed',
            attempts=attempts + CASE WHEN status='queued' THEN 1 ELSE 0 END,
            claimed_by=?, lease_until=?, updated_at=?
        WHERE work_id=?
          AND (
              (status='queued' AND attempts < max_attempts)
              OR (status='claimed' AND claimed_by=?)
          )
        """,
        (worker_id, now + int(lease_s), now, work_id, worker_id),
    )
    cx.commit()
    if int(cur.rowcount or 0) == 1:
        record_worker_heartbeat(cx, worker_id=worker_id, claimed_work_id=work_id, worker_kind="campaign_lemma")
        return True
    return False


def finish_specific(
    cx: sqlite3.Connection,
    *,
    work_id: str,
    worker_id: str,
    done: bool,
) -> bool:
    """Release a claimed item: `done=True` → terminal `done`; `done=False` → back to `queued`
    (so another node — possibly with a larger proven shelf — can retry it). The lease is cleared
    either way. An expired or foreign lease cannot be finalized by this worker;
    expiration recovery remains the queue's separate state transition."""
    reclaim_expired(cx)
    now = _now()
    status = "done" if done else "queued"
    cur = cx.execute(
        """
        UPDATE work_items
        SET status=?, claimed_by=NULL, lease_until=NULL, updated_at=?
        WHERE work_id=? AND status='claimed' AND claimed_by=?
        """,
        (status, now, work_id, worker_id),
    )
    cx.commit()
    return int(cur.rowcount or 0) == 1


def _apply_terminal_payload_defaults(payload: dict[str, Any], *, status: str) -> None:
    if status != "dead_letter":
        return
    payload.setdefault("exit_kind", "dead_letter_unclassified")
    payload.setdefault("ops_exit_kind", "dead_letter_unclassified")
    payload.setdefault("dead_letter_reason", "terminal_status_without_specific_reason")


def update_status(cx: sqlite3.Connection, *, work_id: str, status: str, payload_update: dict[str, Any] | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")
    row = cx.execute("SELECT kind, payload_json FROM work_items WHERE work_id=?", (work_id,)).fetchone()
    payload = json.loads(row["payload_json"]) if row else {}
    if payload_update:
        payload.update(payload_update)
    if row:
        payload.setdefault("work_id", work_id)
        handoff_contract.ensure_terminal_handoff_receipt(
            kind=str(row["kind"]),
            status=status,
            payload=payload,
            policy=handoff_contract.policy_from_factory_policy(_read_policy()),
        )
    _apply_terminal_payload_defaults(payload, status=status)
    family = str(payload.get("family") or "")
    station = str(payload.get("station") or "")
    expected_exit = str(payload.get("expected_exit") or payload.get("exit_kind") or "")
    terminal = status in {"done", "failed", "retired", "dead_letter"}
    cx.execute(
        """
        UPDATE work_items
        SET status=?, family=?, station=?, expected_exit=?, payload_json=?, updated_at=?,
            claimed_by=CASE WHEN ? THEN NULL ELSE claimed_by END,
            lease_until=CASE WHEN ? THEN NULL ELSE lease_until END
        WHERE work_id=?
        """,
        (status, family, station, expected_exit, _json(payload), _now(), int(terminal), int(terminal), work_id),
    )
    cx.commit()


def requeue_with_payload_update(cx: sqlite3.Connection, *, work_id: str, payload_update: dict[str, Any] | None = None) -> None:
    row = cx.execute("SELECT payload_json FROM work_items WHERE work_id=?", (work_id,)).fetchone()
    payload = json.loads(row["payload_json"]) if row else {}
    if payload_update:
        payload.update(payload_update)
    family = str(payload.get("family") or "")
    station = str(payload.get("station") or "")
    expected_exit = str(payload.get("expected_exit") or payload.get("exit_kind") or "")
    cx.execute(
        """
        UPDATE work_items
        SET status='queued', family=?, station=?, expected_exit=?, payload_json=?, updated_at=?,
            claimed_by=NULL, lease_until=NULL
        WHERE work_id=?
        """,
        (family, station, expected_exit, _json(payload), _now(), work_id),
    )
    cx.commit()


def heartbeat(
    cx: sqlite3.Connection,
    *,
    work_id: str,
    worker_id: str,
    lease_s: int,
    payload_update: dict[str, Any] | None = None,
) -> bool:
    now = _now()
    row = cx.execute(
        """
        SELECT payload_json FROM work_items
        WHERE work_id=? AND claimed_by=? AND status IN ('claimed', 'running')
        """,
        (work_id, worker_id),
    ).fetchone()
    if row is None:
        return False
    payload = json.loads(row["payload_json"] or "{}")
    if payload_update:
        payload.update(payload_update)
    cur = cx.execute(
        """
        UPDATE work_items
        SET lease_until=?, payload_json=?, updated_at=?
        WHERE work_id=? AND claimed_by=? AND status IN ('claimed', 'running')
          AND lease_until IS NOT NULL AND lease_until >= ?
        """,
        (now + int(lease_s), _json(payload), now, work_id, worker_id, now),
    )
    cx.commit()
    if int(cur.rowcount or 0) != 1:
        return False
    record_worker_heartbeat(
        cx,
        worker_id=worker_id,
        claimed_work_id=work_id,
        worker_kind="leased_work",
    )
    return True


class QueueLeaseBusy(RuntimeError):
    """A live worker already owns the requested mutable work identity."""


class QueueLeaseLost(RuntimeError):
    """The worker could no longer renew or release its queue lease."""


class QueueLease:
    """Reusable single-owner lease over one mutable work identity.

    The queue row is authoritative.  Callers provide the identity and payload;
    immutable receipts remain caller-owned.  The lease renews in a daemon thread
    so a long provider call cannot silently outlive ownership, and an optional
    ``on_change`` callback may refresh a derived status view.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        work_id: str,
        worker_id: str | None = None,
        kind: str = "leased_work",
        worker_kind: str = "leased_work",
        payload: Mapping[str, Any] | None = None,
        max_attempts: int = 1_000_000_000,
        lease_s: int = 900,
        heartbeat_s: float | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.db_path = str(db_path)
        self.work_id = str(work_id)
        if not self.work_id.strip():
            raise ValueError("queue lease requires work_id")
        self.worker_id = worker_id or (
            f"queue-lease:{node_id()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"
        )
        self.kind = str(kind or "leased_work")
        self.worker_kind = str(worker_kind or self.kind)
        self.payload = dict(payload or {})
        self.max_attempts = max(1, int(max_attempts))
        self.lease_s = max(1, int(lease_s))
        self.heartbeat_s = max(
            0.05,
            float(
                heartbeat_s
                if heartbeat_s is not None
                else min(60, max(5, self.lease_s / 3))
            ),
        )
        self._on_change = on_change
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._renew_lock = threading.Lock()
        self._acquired = False
        self._lost = False
        self._last_error = ""

    @property
    def lost(self) -> bool:
        return self._lost

    def __enter__(self) -> "QueueLease":
        cx = connect(self.db_path)
        try:
            enqueue(
                cx,
                kind=self.kind,
                priority=0,
                max_attempts=self.max_attempts,
                payload={**self.payload, "work_id": self.work_id},
            )
            if not claim_specific(
                cx,
                work_id=self.work_id,
                worker_id=self.worker_id,
                lease_s=self.lease_s,
            ):
                row = cx.execute(
                    "SELECT claimed_by, lease_until FROM work_items WHERE work_id=?",
                    (self.work_id,),
                ).fetchone()
                owner = str(row["claimed_by"] or "") if row else ""
                until = int(row["lease_until"] or 0) if row else 0
                raise QueueLeaseBusy(
                    "queue work is currently owned by another worker"
                    + (f" ({owner} until {until})" if owner else "")
                )
            self._acquired = True
        finally:
            cx.close()
        self._emit_change()
        self._thread = threading.Thread(
            target=self._renew_loop,
            name=f"queue-lease-{self.work_id[-8:]}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, _exc: Any, _traceback: Any) -> bool:
        try:
            self.release()
        except QueueLeaseLost:
            if exc_type is None:
                raise
        return False

    def update(self, payload_update: Mapping[str, Any]) -> None:
        if not self._acquired:
            raise QueueLeaseLost("queue lease was never acquired")
        self.payload.update(dict(payload_update))
        self.renew()

    def renew(self) -> None:
        with self._renew_lock:
            if not self._acquired:
                raise QueueLeaseLost("queue lease was never acquired")
            cx = connect(self.db_path)
            try:
                renewed = heartbeat(
                    cx,
                    work_id=self.work_id,
                    worker_id=self.worker_id,
                    lease_s=self.lease_s,
                    payload_update=dict(self.payload),
                )
            finally:
                cx.close()
            if not renewed:
                self._lost = True
                raise QueueLeaseLost("queue lease ownership was lost")
            self._emit_change()

    def _renew_loop(self) -> None:
        while not self._stop.wait(self.heartbeat_s):
            try:
                self.renew()
            except QueueLeaseLost as exc:
                self._last_error = str(exc)
                return
            except Exception as exc:  # transient coordinator errors are retried
                self._last_error = str(exc)

    def release(self) -> None:
        if not self._acquired:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=6.0)
        with self._renew_lock:
            cx = connect(self.db_path)
            try:
                released = finish_specific(
                    cx,
                    work_id=self.work_id,
                    worker_id=self.worker_id,
                    done=False,
                )
            finally:
                cx.close()
            self._acquired = False
        self._emit_change()
        if not released:
            self._lost = True
        if self._lost:
            detail = f": {self._last_error}" if self._last_error else ""
            raise QueueLeaseLost("queue lease was lost before release" + detail)

    def _emit_change(self) -> None:
        if self._on_change is None:
            return
        try:
            self._on_change()
        except Exception:
            # A derived view must never decide queue ownership.
            return


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    obj = dict(row)
    obj["payload"] = json.loads(obj.pop("payload_json") or "{}")
    return obj


def list_items(cx: sqlite3.Connection, *, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if status:
        where = "WHERE status=?"
        params.append(status)
    rows = cx.execute(
        f"SELECT * FROM work_items {where} ORDER BY priority DESC, created_at ASC LIMIT ?",
        [*params, int(limit)],
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def stats(cx: sqlite3.Connection) -> dict[str, Any]:
    reclaim_expired(cx)
    rows = cx.execute("SELECT status, kind, COUNT(*) n FROM work_items GROUP BY status, kind").fetchall()
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + int(row["n"])
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + int(row["n"])
    return {"by_status": by_status, "by_kind": by_kind, "total": sum(by_status.values())}


def _work_lane(kind: str, payload: dict[str, Any]) -> str:
    if kind == "repair_canary_probe":
        lane = str(payload.get("probe_lane") or payload.get("lane") or "legacy")
        return f"probe:{lane}"
    if kind in {"agent_repair_task", "subscription_agent_task", "agent_task", "agent_repair"}:
        mode = str(payload.get("family_spec_patch_mode") or payload.get("expected_exit") or "general")
        return f"agent:{mode}"
    if kind == "source_scout_task":
        return "source_scout"
    return kind


def open_stats(cx: sqlite3.Connection) -> dict[str, Any]:
    reclaim_expired(cx)
    rows = cx.execute(
        """
        SELECT status, kind, payload_json, COUNT(*) n
        FROM work_items
        WHERE status IN ('queued', 'claimed', 'running')
        GROUP BY status, kind, payload_json
        """
    ).fetchall()
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for row in rows:
        n = int(row["n"])
        by_status[row["status"]] = by_status.get(row["status"], 0) + n
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + n
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        lane = _work_lane(str(row["kind"] or ""), payload)
        by_lane[lane] = by_lane.get(lane, 0) + n
    return {"by_status": by_status, "by_kind": by_kind, "by_lane": by_lane, "total": sum(by_status.values())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    enq = sub.add_parser("enqueue")
    enq.add_argument("--kind", required=True)
    enq.add_argument("--priority", type=int, default=1)
    enq.add_argument("--payload-json", default="{}")
    enq.add_argument("--max-attempts", type=int, default=3)
    term = sub.add_parser("record-terminal")
    term.add_argument("--kind", required=True)
    term.add_argument("--status", required=True)
    term.add_argument("--priority", type=int, default=1)
    term.add_argument("--payload-json", default="{}")
    term.add_argument("--max-attempts", type=int, default=1)
    cl = sub.add_parser("claim")
    cl.add_argument("--worker-id", required=True)
    cl.add_argument("--kind", action="append", default=[])
    cl.add_argument("--lease-s", type=int, default=600)
    hb = sub.add_parser("heartbeat")
    hb.add_argument("--work-id", required=True)
    hb.add_argument("--worker-id", required=True)
    hb.add_argument("--lease-s", type=int, default=600)
    hb.add_argument("--payload-json", default="{}")
    wh = sub.add_parser("worker-heartbeat")
    wh.add_argument("--worker-id", required=True)
    wh.add_argument("--claimed-work-id", default="")
    wh.add_argument("--worker-kind", default="")
    wh.add_argument("--payload-json", default="{}")
    wvh = sub.add_parser("worker-version-health")
    wvh.add_argument("--stale-after-s", type=int, default=0)
    wvh.add_argument("--policy-profile", default="")
    rtw = sub.add_parser("reclaim-terminated-workers")
    rtw.add_argument("--stale-after-s", type=int, default=0)
    rtw.add_argument("--policy-profile", default="")
    rw = sub.add_parser("reclaim-worker")
    rw.add_argument("--worker-id", required=True)
    st = sub.add_parser("status")
    st.add_argument("--work-id", required=True)
    st.add_argument("--status", required=True)
    st.add_argument("--payload-json", default="{}")
    ev = sub.add_parser("event")
    ev.add_argument("--event-type", required=True)
    ev.add_argument("--work-id", default="")
    ev.add_argument("--payload-json", default="{}")
    ev.add_argument("--artifact-path", action="append", default=[])
    ar = sub.add_parser("artifact-record")
    ar.add_argument("--artifact-key", required=True)
    ar.add_argument("--role", required=True)
    ar.add_argument("--path", required=True)
    ar.add_argument("--producer", default="")
    ar.add_argument("--schema-name", default="")
    ar.add_argument("--run-id", default="")
    ar.add_argument("--payload-json", default="{}")
    ag = sub.add_parser("artifact-get")
    ag.add_argument("--artifact-key", required=True)
    al = sub.add_parser("artifact-list")
    al.add_argument("--role", default="")
    al.add_argument("--limit", type=int, default=100)
    ls = sub.add_parser("list")
    ls.add_argument("--status", default="")
    ls.add_argument("--limit", type=int, default=50)
    sub.add_parser("stats")
    sub.add_parser("self-test")
    args = ap.parse_args()

    cx = connect(args.db)
    if args.cmd == "init":
        print(json.dumps({"db": args.db, "events": args.events, "status": "ready"}, sort_keys=True))
    elif args.cmd == "enqueue":
        payload = json.loads(args.payload_json)
        work_id = enqueue(cx, kind=args.kind, priority=args.priority, payload=payload, max_attempts=args.max_attempts)
        append_event(args.events, {"event_type": "work_enqueued", "work_id": work_id, "payload": payload})
        print(json.dumps({"work_id": work_id}, sort_keys=True))
    elif args.cmd == "record-terminal":
        payload = json.loads(args.payload_json)
        work_id = record_terminal_item(
            cx,
            kind=args.kind,
            status=args.status,
            priority=args.priority,
            payload=payload,
            max_attempts=args.max_attempts,
        )
        append_event(args.events, {"event_type": f"work_{args.status}", "work_id": work_id, "payload": payload})
        print(json.dumps({"work_id": work_id, "status": args.status}, sort_keys=True))
    elif args.cmd == "claim":
        reclaim_expired(cx, events_path=args.events)
        item = claim(cx, worker_id=args.worker_id, kinds=args.kind, lease_s=args.lease_s)
        if item:
            append_event(args.events, {"event_type": "work_claimed", "work_id": item["work_id"], "worker_id": args.worker_id})
        print(json.dumps(item or {}, sort_keys=True))
    elif args.cmd == "heartbeat":
        ok = heartbeat(
            cx,
            work_id=args.work_id,
            worker_id=args.worker_id,
            lease_s=args.lease_s,
            payload_update=json.loads(args.payload_json),
        )
        if ok:
            append_event(args.events, {
                "event_type": "work_heartbeat",
                "work_id": args.work_id,
                "worker_id": args.worker_id,
                "payload": json.loads(args.payload_json),
            })
        print(json.dumps({"work_id": args.work_id, "heartbeat": ok}, sort_keys=True))
    elif args.cmd == "worker-heartbeat":
        rec = record_worker_heartbeat(
            cx,
            worker_id=args.worker_id,
            claimed_work_id=args.claimed_work_id,
            worker_kind=args.worker_kind,
            payload=json.loads(args.payload_json),
        )
        append_event(args.events, {
            "event_type": "worker_runtime_heartbeat",
            "worker_id": args.worker_id,
            "work_id": args.claimed_work_id,
            "payload": rec,
        })
        print(json.dumps({"worker_id": args.worker_id, "runtime_version": rec.get("runtime_version")}, sort_keys=True))
    elif args.cmd == "worker-version-health":
        print(json.dumps(worker_version_health(cx, stale_after_s=args.stale_after_s, policy_profile=args.policy_profile), indent=2, sort_keys=True))
    elif args.cmd == "reclaim-terminated-workers":
        health = worker_version_health(cx, stale_after_s=args.stale_after_s, policy_profile=args.policy_profile)
        count = reclaim_terminated_worker_claims(cx, version_health=health, events_path=args.events, reason="cli_reclaim_terminated_workers")
        print(json.dumps({"reclaimed_count": count}, sort_keys=True))
    elif args.cmd == "reclaim-worker":
        count = reclaim_worker_claims(cx, worker_id=args.worker_id)
        if count:
            append_event(args.events, {
                "event_type": "worker_claims_reclaimed",
                "worker_id": args.worker_id,
                "payload": {"reclaimed_count": count},
            })
        print(json.dumps({"worker_id": args.worker_id, "reclaimed_count": count}, sort_keys=True))
    elif args.cmd == "status":
        update_status(cx, work_id=args.work_id, status=args.status, payload_update=json.loads(args.payload_json))
        append_event(args.events, {"event_type": f"work_{args.status}", "work_id": args.work_id, "payload": json.loads(args.payload_json)})
        print(json.dumps({"work_id": args.work_id, "status": args.status}, sort_keys=True))
    elif args.cmd == "event":
        rec = append_event(args.events, {
            "event_type": args.event_type,
            "work_id": args.work_id,
            "payload": json.loads(args.payload_json),
            "artifact_paths": args.artifact_path,
        })
        print(json.dumps({"event_id": rec["event_id"]}, sort_keys=True))
    elif args.cmd == "artifact-record":
        rec = record_artifact_ref(
            cx,
            artifact_key=args.artifact_key,
            role=args.role,
            path=args.path,
            payload=json.loads(args.payload_json),
            producer=args.producer,
            schema=args.schema_name,
            run_id=args.run_id,
        )
        append_event(args.events, {
            "event_type": "artifact_ref_recorded",
            "work_id": args.artifact_key,
            "payload": {
                "artifact_key": rec["artifact_key"],
                "role": rec["role"],
                "path": rec["path"],
                "sha256": rec["sha256"],
                "schema_name": rec["schema_name"],
                "run_id": rec["run_id"],
            },
            "artifact_paths": [args.path],
        })
        print(json.dumps(rec, indent=2, sort_keys=True))
    elif args.cmd == "artifact-get":
        print(json.dumps(artifact_ref(cx, args.artifact_key) or {}, indent=2, sort_keys=True))
    elif args.cmd == "artifact-list":
        print(json.dumps({"artifact_refs": artifact_refs(cx, role=args.role, limit=args.limit)}, indent=2, sort_keys=True))
    elif args.cmd == "list":
        reclaim_expired(cx, events_path=args.events)
        print(json.dumps({"items": list_items(cx, status=args.status, limit=args.limit)}, indent=2, sort_keys=True))
    elif args.cmd == "stats":
        reclaim_expired(cx, events_path=args.events)
        print(json.dumps(stats(cx), sort_keys=True))
    elif args.cmd == "self-test":
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "q.sqlite")
            evp = str(Path(td) / "events.jsonl")
            tcx = connect(db)
            wid = enqueue(tcx, kind="k", priority=1, payload={"x": 1})
            terminal_wid = record_terminal_item(
                tcx,
                kind="terminal",
                status="done",
                priority=2,
                payload={"work_id": "terminal-ok", "exit_kind": "ready"},
            )
            terminal = tcx.execute("SELECT status FROM work_items WHERE work_id=?", (terminal_wid,)).fetchone()
            assert terminal and terminal["status"] == "done"
            artifact_path = Path(td) / "canonical.json"
            artifact_path.write_text(json.dumps({"schema": "self-test-artifact-v1", "run_id": "artifact-run"}) + "\n")
            ref = record_artifact_ref(
                tcx,
                artifact_key="self_test.canonical",
                role="canonical",
                path=artifact_path,
                producer="self_test",
            )
            assert ref["schema_name"] == "self-test-artifact-v1", ref
            assert ref["run_id"] == "artifact-run", ref
            assert artifact_ref(tcx, "self_test.canonical")["sha256"] == ref["sha256"]
            assert artifact_refs(tcx, role="canonical", limit=10)
            assert artifact_refs_for_path(tcx, artifact_path)[0]["artifact_key"] == "self_test.canonical"
            stale_wid = enqueue(tcx, kind="stale", priority=5, payload={"x": "stale"})
            original_runtime_version_receipt = globals()["runtime_version_receipt"]
            def _stale_runtime_version_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
                rec = original_runtime_version_receipt(*args, **kwargs)
                rec = dict(rec)
                rec["stale_process_likely"] = True
                rec["stale_reason"] = "self_test_stale_worker"
                return rec
            globals()["runtime_version_receipt"] = _stale_runtime_version_receipt
            try:
                assert claim(tcx, worker_id="stale-worker", kinds=["stale"], lease_s=1) is None
            finally:
                globals()["runtime_version_receipt"] = original_runtime_version_receipt
            stale_row = tcx.execute("SELECT status, attempts FROM work_items WHERE work_id=?", (stale_wid,)).fetchone()
            assert stale_row and stale_row["status"] == "queued" and stale_row["attempts"] == 0
            item = claim(tcx, worker_id="w", kinds=["k"], lease_s=1)
            assert item and item["work_id"] == wid
            health = worker_version_health(tcx, stale_after_s=0)
            assert health["worker_count"] >= 1
            assert health["stale_process_count"] >= 0
            original_runtime_version_receipt = globals()["runtime_version_receipt"]
            def _drifted_data_runtime_version_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
                rec = original_runtime_version_receipt(*args, **kwargs)
                rec = dict(rec)
                rec["watched_data_hash"] = "self-test-drifted-data-hash"
                return rec
            globals()["runtime_version_receipt"] = _drifted_data_runtime_version_receipt
            try:
                data_health = worker_version_health(tcx, stale_after_s=0)
            finally:
                globals()["runtime_version_receipt"] = original_runtime_version_receipt
            assert data_health["data_mismatch_count"] >= 1, data_health
            assert _pid_identity_matches_worker("python worker.py --worker-id current", worker_id="current")
            assert not _pid_identity_matches_worker("python worker.py --worker-id current", worker_id="previous")
            assert _pid_identity_matches_worker("python worker.py --daemon", worker_id="watchdog")
            assert heartbeat(tcx, work_id=wid, worker_id="w", lease_s=1)
            heartbeat_expired = enqueue(
                tcx,
                kind="heartbeat-expired",
                priority=1,
                payload={"work_id": "heartbeat-expired"},
                max_attempts=2,
            )
            assert claim(tcx, worker_id="heartbeat-worker", kinds=["heartbeat-expired"], lease_s=1)
            tcx.execute(
                "UPDATE work_items SET lease_until=? WHERE work_id=?",
                (_now() - 1, heartbeat_expired),
            )
            tcx.commit()
            assert not heartbeat(
                tcx,
                work_id=heartbeat_expired,
                worker_id="heartbeat-worker",
                lease_s=1,
            )
            update_status(tcx, work_id=wid, status="done")
            wid_a = enqueue(tcx, kind="probe", priority=10, payload={"work_id": "a", "lane": "source"})
            wid_b = enqueue(tcx, kind="probe", priority=9, payload={"work_id": "b", "lane": "family"})
            probe_family = enqueue(tcx, kind="repair_canary_probe", priority=8, payload={"work_id": "pf", "probe_lane": "family_spec"})
            agent_birth = enqueue(tcx, kind="agent_repair_task", priority=7, payload={"work_id": "ab", "family_spec_patch_mode": "family_birth_candidate"})
            accepted_patch = enqueue(tcx, kind="agent_repair_task", priority=7, payload={
                "work_id": "accepted-patch",
                "expected_exit": "family_spec_patch",
                "family": "self_test_family",
                "family_spec_patch_mode": "family_spec_positive_repair",
                "family_spec_patch_receipt": {"status": "pass"},
            })
            open_before_lane_claim = open_stats(tcx)
            assert open_before_lane_claim["by_lane"].get("probe:family_spec") == 1, open_before_lane_claim
            assert open_before_lane_claim["by_lane"].get("agent:family_birth_candidate") == 1, open_before_lane_claim
            update_status(tcx, work_id=probe_family, status="retired")
            update_status(tcx, work_id=agent_birth, status="retired")
            update_status(tcx, work_id=accepted_patch, status="done")
            accepted_row = tcx.execute("SELECT payload_json FROM work_items WHERE work_id=?", (accepted_patch,)).fetchone()
            accepted_payload = json.loads(accepted_row["payload_json"])
            assert accepted_payload["family_spec_positive_repair_activation"]["status"] == "skipped"
            assert accepted_payload["agentic_handoff_boundary_receipt"]["reason"] == "terminal_agentic_patch_missing_downstream_handoff_at_queue_boundary"
            matched = claim_matching(
                tcx,
                worker_id="lane-worker",
                kinds=["probe"],
                lease_s=1,
                predicate=lambda obj: obj.get("payload", {}).get("lane") == "family",
            )
            assert matched and matched["work_id"] == wid_b
            still_queued = tcx.execute("SELECT status FROM work_items WHERE work_id=?", (wid_a,)).fetchone()
            assert still_queued and still_queued["status"] == "queued"
            requeued = reclaim_worker_claims(tcx, worker_id="lane-worker")
            assert requeued == 1
            # 2026-05-23 behavior change: reclaim_worker_claims no longer
            # decrements attempts. The first claim consumed an attempt; the
            # row was abandoned without a terminal status; that attempt counts.
            # Previously the attempt was refunded, which let crashed workers
            # bypass max_attempts under tight crash loops.
            row = tcx.execute("SELECT status, claimed_by, attempts FROM work_items WHERE work_id=?", (wid_b,)).fetchone()
            assert row and row["status"] == "queued" and row["claimed_by"] is None and row["attempts"] == 1
            matched_again = claim_matching(
                tcx,
                worker_id="lane-worker-2",
                kinds=["probe"],
                lease_s=1,
                predicate=lambda obj: obj.get("payload", {}).get("lane") == "family",
            )
            assert matched_again and matched_again["work_id"] == wid_b
            assert reclaim_all_open_claims(tcx, events_path=evp, reason="self_test") == 1
            # reclaim_all_open_claims is the intentional-factory-stop path and
            # still refunds an attempt (deliberate-stop semantics; no crash).
            # So attempts goes from 2 (after the second claim) back to 1.
            row = tcx.execute("SELECT status, claimed_by, attempts FROM work_items WHERE work_id=?", (wid_b,)).fetchone()
            assert row and row["status"] == "queued" and row["claimed_by"] is None and row["attempts"] == 1
            dead_claim = claim_matching(
                tcx,
                worker_id="dead-worker",
                kinds=["probe"],
                lease_s=3600,
                predicate=lambda obj: obj["work_id"] == wid_b,
            )
            assert dead_claim and dead_claim["work_id"] == wid_b
            reclaimed_dead = reclaim_terminated_worker_claims(
                tcx,
                version_health={"terminated_heartbeats": [{"worker_id": "dead-worker", "claimed_work_id": wid_b}]},
                events_path=evp,
                reason="self_test",
            )
            assert reclaimed_dead == 1
            row = tcx.execute("SELECT status, claimed_by, attempts FROM work_items WHERE work_id=?", (wid_b,)).fetchone()
            assert row and row["status"] == "queued" and row["claimed_by"] is None and row["attempts"] == 1
            exhausted = enqueue(tcx, kind="exhausted", priority=1, payload={"work_id": "exhausted"}, max_attempts=1)
            claim(tcx, worker_id="exhausted-worker", kinds=["exhausted"], lease_s=1)
            reclaim_worker_claims(tcx, worker_id="exhausted-worker")
            assert terminalize_exhausted_queued(tcx, events_path=evp) == 1
            exhausted_row = tcx.execute("SELECT status, payload_json FROM work_items WHERE work_id=?", (exhausted,)).fetchone()
            assert exhausted_row and exhausted_row["status"] == "dead_letter"
            assert json.loads(exhausted_row["payload_json"])["exit_kind"] == "queue_attempt_budget_exhausted"

            wid_exp = enqueue(tcx, kind="lease", priority=1, payload={"work_id": "expired"}, max_attempts=2)
            expired = claim(tcx, worker_id="expired-worker", kinds=["lease"], lease_s=1)
            assert expired and expired["work_id"] == wid_exp
            tcx.execute("UPDATE work_items SET lease_until=? WHERE work_id=?", (_now() - 1, wid_exp))
            tcx.commit()
            expired_events = str(Path(td) / "expired_events.jsonl")
            assert reclaim_expired(tcx, events_path=expired_events) == 1
            expired_row = tcx.execute("SELECT status, claimed_by, attempts FROM work_items WHERE work_id=?", (wid_exp,)).fetchone()
            assert expired_row and expired_row["status"] == "queued" and expired_row["claimed_by"] is None
            assert Path(expired_events).read_text()
            append_event(evp, {"event_type": "ok", "work_id": wid})
            assert Path(evp).exists()
        print("leanmill_work_queue self-test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
