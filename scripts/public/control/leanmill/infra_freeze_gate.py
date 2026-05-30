#!/usr/bin/env python3
"""Infra freeze gate for LeanMill 24x7 science mode.

This gate is intentionally operational, not scientific. It answers one question:
is the factory control plane stable enough that operators should stop fixing
adapters and let the mill spend cycles on typed learning-unit exits?
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/leanmill_infra_freeze_gate.json"
TERMINAL = {"done", "failed", "retired", "dead_letter"}
CORE_DEAD_LETTER_KINDS = {
    "repair_canary_probe",
    "proof_probe",
    "source_scout_task",
    "subscription_agent_task",
    "agent_repair_task",
    "llm_proposal_validate",
    "source_search_task",
}
SCORE_KEYS = (
    "ratified_closure_count",
    "exact_gap_candidate_count",
    "valid_falsifier_count",
    "negative_control_fail_count",
    "negative_control_unexpected_pass_count",
)


def _now() -> int:
    return int(time.time())


def _read_json(path: str | Path | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _int(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _scoreboard_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts = {key: _int(payload, key) for key in SCORE_KEYS}
    scoreboard_path = str(payload.get("scoreboard") or "")
    obj = _read_json(scoreboard_path)
    if isinstance(obj, dict):
        for key in SCORE_KEYS:
            counts[key] = max(counts[key], _int(obj, key))
    return counts


def _inferred_exit(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
    counts = _scoreboard_counts(payload)
    if counts["negative_control_unexpected_pass_count"] > 0:
        return "failed_negative_control"
    if counts["ratified_closure_count"] > 0:
        return "ratified_closure"
    if counts["exact_gap_candidate_count"] > 0:
        return "exact_gap_candidate"
    if counts["valid_falsifier_count"] > 0:
        return "valid_falsifier"
    if counts["negative_control_fail_count"] > 0:
        return "tested_no_positive_signal"
    if explicit and explicit != "probe_finished":
        return explicit
    if _int(payload, "completed") > 0:
        return "tested_probe_no_signal"
    return explicit


def _recent_rows(cx: sqlite3.Connection, window_s: int) -> list[sqlite3.Row]:
    since = _now() - max(1, int(window_s))
    return list(cx.execute("SELECT * FROM work_items WHERE updated_at >= ? ORDER BY updated_at DESC", (since,)).fetchall())


def _check_terminal_probe_exits(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] not in {"repair_canary_probe", "proof_probe"} or row["status"] not in TERMINAL:
            continue
        payload = _payload(row)
        inferred = _inferred_exit(payload)
        if inferred in {"", "probe_finished", "probe_finished_no_tests"}:
            failures.append({
                "class": "terminal_probe_without_typed_exit",
                "work_id": row["work_id"],
                "status": row["status"],
                "exit_kind": payload.get("exit_kind"),
                "scoreboard": payload.get("scoreboard"),
            })
    return failures


def _check_negative_controls(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] not in {"repair_canary_probe", "proof_probe"} or row["status"] not in TERMINAL:
            continue
        payload = _payload(row)
        count = _scoreboard_counts(payload)["negative_control_unexpected_pass_count"]
        if count:
            failures.append({
                "class": "unexpected_negative_control_pass",
                "work_id": row["work_id"],
                "count": count,
                "scoreboard": payload.get("scoreboard"),
            })
    return failures


def _check_subscription_artifacts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] not in {"agent_repair_task", "source_scout_task", "subscription_agent_task", "agent_task"}:
            continue
        if row["status"] not in TERMINAL:
            continue
        payload = _payload(row)
        if not bool(payload.get("agent_launched")):
            continue
        if payload.get("output_path") or payload.get("artifact_paths"):
            continue
        failures.append({
            "class": "subscription_agent_terminal_without_artifact",
            "work_id": row["work_id"],
            "status": row["status"],
            "runtime": payload.get("runtime"),
        })
    return failures


def _check_source_binding_ingestability(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] != "source_scout_task" or row["status"] not in TERMINAL:
            continue
        payload = _payload(row)
        if not payload.get("source_search_integration_receipt"):
            continue
        if payload.get("source_binding_ingested_at_epoch"):
            continue
        if payload.get("output_path") or payload.get("artifact_paths"):
            continue
        failures.append({
            "class": "source_binding_terminal_uningestable",
            "work_id": row["work_id"],
            "status": row["status"],
        })
    return failures


def _governance_report_validates(
    report_path: str,
    *,
    family: str,
    row_id: str,
    exit_kind: str,
) -> bool:
    """Verify the agent's claimed governance_report file actually contains a
    matching ratification record. Presence of the field on the WorkItem is not
    sufficient; the report must exist, parse, and carry a matching record."""
    if not report_path:
        return False
    obj = _read_json(report_path)
    if obj is None:
        return False
    records: list[dict[str, Any]] = []
    if isinstance(obj, list):
        records = [x for x in obj if isinstance(x, dict)]
    elif isinstance(obj, dict):
        for key in ("records", "events", "log", "ratifications"):
            vals = obj.get(key)
            if isinstance(vals, list):
                records = [x for x in vals if isinstance(x, dict)]
                break
        if not records:
            records = [obj]
    for rec in records:
        rec_family = str(rec.get("family") or rec.get("repair_family") or rec.get("lane") or "")
        rec_row = str(rec.get("row_id") or rec.get("heldout_row") or rec.get("row") or "")
        if family and rec_family and rec_family != family:
            continue
        if row_id and rec_row and rec_row != row_id:
            continue
        status = str(
            rec.get("status")
            or rec.get("decision")
            or rec.get("event")
            or rec.get("event_type")
            or ""
        )
        ratified = (
            status in {"governance_ratified", "ratified_closure", "ratified", "pass"}
            or rec.get("governance_ratified") is True
        )
        if not ratified:
            continue
        rec_exit = str(rec.get("exit_kind") or rec.get("outcome") or rec.get("expected_outcome") or "")
        if exit_kind and rec_exit and rec_exit not in {exit_kind, exit_kind.replace("_candidate", "")}:
            continue
        return True
    return False


def _check_agent_declared_value_exits(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] not in {"source_scout_task", "subscription_agent_task", "agent_repair_task", "agent_task"}:
            continue
        if row["status"] not in TERMINAL:
            continue
        payload = _payload(row)
        exit_kind = str(payload.get("learning_unit_exit") or payload.get("exit_kind") or "")
        if exit_kind not in {"exact_gap_candidate", "valid_falsifier", "ratified_closure"}:
            continue
        governance_report = str(payload.get("governance_report") or "")
        ratified_epoch = payload.get("governance_ratified_at_epoch")
        family = str(payload.get("family") or "")
        row_id = str(payload.get("row_id") or payload.get("target_row_id") or "")
        # Presence is not enough; the report file must contain a matching
        # ratification record. Epoch alone (without a report path) is not
        # sufficient evidence.
        if governance_report and _governance_report_validates(
            governance_report,
            family=family,
            row_id=row_id,
            exit_kind=exit_kind,
        ):
            continue
        failures.append({
            "class": "agent_declared_value_exit_without_governance",
            "work_id": row["work_id"],
            "kind": row["kind"],
            "exit_kind": exit_kind,
            "governance_report": governance_report,
            "governance_ratified_at_epoch": ratified_epoch,
            "validation": (
                "governance_report_missing_or_unreadable"
                if governance_report and _read_json(governance_report) is None
                else "governance_report_absent_or_no_matching_record"
            ),
        })
    return failures


def _check_dead_letters(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if row["status"] == "dead_letter" and row["kind"] in CORE_DEAD_LETTER_KINDS:
            failures.append({
                "class": "core_lane_dead_letter",
                "work_id": row["work_id"],
                "kind": row["kind"],
            })
    return failures


def _check_stale_running_probes(rows: list[sqlite3.Row], *, running_grace_s: int) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    now = _now()
    for row in rows:
        if row["kind"] not in {"repair_canary_probe", "proof_probe"} or row["status"] != "running":
            continue
        age_s = now - int(row["updated_at"] or now)
        if age_s < int(running_grace_s):
            continue
        payload = _payload(row)
        scoreboard = str(payload.get("scoreboard") or "")
        if scoreboard and Path(scoreboard).exists():
            continue
        failures.append({
            "class": "stale_running_probe_without_scoreboard",
            "work_id": row["work_id"],
            "age_s": age_s,
            "claimed_by": row["claimed_by"],
            "scoreboard": scoreboard,
        })
    return failures


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    work_queue.reclaim_expired(cx)
    rows = _recent_rows(cx, args.window_s)
    failures = [
        *_check_terminal_probe_exits(rows),
        *_check_negative_controls(rows),
        *_check_subscription_artifacts(rows),
        *_check_source_binding_ingestability(rows),
        *_check_agent_declared_value_exits(rows),
        *_check_dead_letters(rows),
        *_check_stale_running_probes(rows, running_grace_s=args.running_grace_s),
    ]
    by_class = Counter(str(item.get("class") or "unknown") for item in failures)
    payload = {
        "schema": "leanmill-infra-freeze-gate-v1",
        "generated_at_epoch": _now(),
        "window_s": int(args.window_s),
        "running_grace_s": int(args.running_grace_s),
        "status": "pass" if not failures else "fail",
        "failure_count": len(failures),
        "failure_classes": dict(sorted(by_class.items())),
        "failures": failures[: int(args.max_failures)],
        "science_mode_rule": "When this gate passes, operator attention should move to proof-science lanes; infra edits require a new failing gate class or explicit operator override.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_infra_freeze_gate_") as td:
        db = str(Path(td) / "q.sqlite")
        cx = work_queue.connect(db)
        wid = work_queue.enqueue(cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe-ok",
            "exit_kind": "probe_finished",
            "completed": 2,
            "negative_control_fail_count": 1,
        })
        work_queue.update_status(cx, work_id=wid, status="done")
        out = build(argparse.Namespace(queue_db=db, out=str(Path(td) / "gate.json"), window_s=3600, running_grace_s=600, max_failures=20))
        assert out["status"] == "pass", out
        bad = work_queue.enqueue(cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe-bad",
            "exit_kind": "probe_finished",
        })
        work_queue.update_status(cx, work_id=bad, status="done")
        out = build(argparse.Namespace(queue_db=db, out=str(Path(td) / "gate2.json"), window_s=3600, running_grace_s=600, max_failures=20))
        assert out["status"] == "fail", out
        assert out["failure_classes"]["terminal_probe_without_typed_exit"] == 1
        stale = work_queue.enqueue(cx, kind="repair_canary_probe", priority=1, payload={
            "work_id": "probe-stale",
            "scoreboard": str(Path(td) / "missing_scoreboard.json"),
        })
        work_queue.update_status(cx, work_id=stale, status="running")
        cx.execute("UPDATE work_items SET updated_at=? WHERE work_id=?", (_now() - 1000, stale))
        cx.commit()
        out = build(argparse.Namespace(queue_db=db, out=str(Path(td) / "gate3.json"), window_s=3600, running_grace_s=600, max_failures=20))
        assert out["failure_classes"]["stale_running_probe_without_scoreboard"] == 1
        agent_value = work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={
            "work_id": "source-agent-bad",
            "exit_kind": "valid_falsifier",
        })
        work_queue.update_status(cx, work_id=agent_value, status="done")
        out = build(argparse.Namespace(queue_db=db, out=str(Path(td) / "gate4.json"), window_s=3600, running_grace_s=600, max_failures=20))
        assert out["failure_classes"]["agent_declared_value_exit_without_governance"] == 1
    print("leanmill_infra_freeze_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--window-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--running-grace-s", type=int, default=10 * 60)
    ap.add_argument("--max-failures", type=int, default=50)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "status": payload["status"],
        "failure_count": payload["failure_count"],
        "failure_classes": payload["failure_classes"],
    }, sort_keys=True))
    return 0 if payload["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
