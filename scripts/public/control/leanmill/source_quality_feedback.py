#!/usr/bin/env python3
"""Project LeanMill source-bound probe quality by repair family.

This is an allocation signal only. It does not award proof value; it records
whether source-search and source-binding work is converting into useful
governed exits or just producing rejected bindings / clean negatives.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue


DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/source_quality_feedback.json"
TERMINAL = {"done", "failed", "retired", "dead_letter"}
HARD_HOLD_NO_VALUE_SOURCE_ATTEMPTS = 3


def _now() -> int:
    return int(time.time())


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _scoreboard_counts(payload: dict[str, Any]) -> dict[str, int]:
    keys = (
        "ratified_closure_count",
        "exact_gap_candidate_count",
        "valid_falsifier_count",
        "negative_control_fail_count",
        "negative_control_unexpected_pass_count",
    )
    counts = {k: int(payload.get(k) or 0) for k in keys if payload.get(k) is not None}
    result = payload.get("result") or {}
    stdout = str(result.get("stdout_tail") or "") if isinstance(result, dict) else ""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k) is not None:
                    counts[k] = max(int(counts.get(k) or 0), int(obj.get(k) or 0))
            break
    scoreboard = str(payload.get("scoreboard") or "")
    if scoreboard and Path(scoreboard).exists():
        try:
            obj = json.loads(Path(scoreboard).read_text(errors="ignore"))
        except json.JSONDecodeError:
            obj = {}
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k) is not None:
                    counts[k] = max(int(counts.get(k) or 0), int(obj.get(k) or 0))
    return counts


def _family(row: sqlite3.Row, payload: dict[str, Any]) -> str:
    return str(row["family"] or payload.get("family") or "")


def _source_binding_failures(payload: dict[str, Any]) -> list[str]:
    failures = payload.get("source_binding_failures") or []
    out: list[str] = []
    for failure in failures:
        if isinstance(failure, dict):
            msg = str(failure.get("failure") or failure.get("reason") or "")
        else:
            msg = str(failure or "")
        if msg:
            out.append(msg)
    reason = str(payload.get("source_binding_rejection_reason") or "")
    if reason:
        out.append(reason)
    return out


def build(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    since = _now() - max(1, int(args.window_s))
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE updated_at >= ?
          AND status IN ('queued','claimed','running','done','failed','retired','dead_letter')
          AND kind IN ('repair_canary_probe','source_scout_task','source_search_task','llm_proposal_validate','agent_repair_task')
        ORDER BY updated_at ASC
        """,
        (since,),
    ).fetchall()
    per_family: dict[str, Counter] = defaultdict(Counter)
    failure_classes: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        payload = _payload(row)
        family = _family(row, payload)
        if not family:
            continue
        kind = str(row["kind"] or "")
        status = str(row["status"] or "")
        rec = per_family[family]
        if kind == "repair_canary_probe":
            lane = str(payload.get("probe_lane") or "")
            if lane != "source_binding":
                continue
            if status not in TERMINAL:
                rec["source_binding_probe_pending"] += 1
                continue
            pre_execution_retire = bool(
                status == "retired"
                and str(payload.get("exit_kind") or "") == "retired_source_strategy_repair_required"
                and str(payload.get("retired_by") or "") == "leanmill_learning_work_seeder"
                and str(payload.get("retire_reason") or "").startswith("source_quality_feedback_")
            )
            if pre_execution_retire:
                rec["source_binding_probe_retired_before_execution"] += 1
                continue
            rec["source_binding_probe_done"] += 1
            counts = _scoreboard_counts(payload)
            value = (
                int(counts.get("ratified_closure_count") or 0)
                + int(counts.get("exact_gap_candidate_count") or 0)
                + int(counts.get("valid_falsifier_count") or 0)
            )
            rec["source_binding_value_exits"] += value
            rec["source_binding_negative_control_fail"] += int(counts.get("negative_control_fail_count") or 0)
            rec["source_binding_unexpected_negative_pass"] += int(counts.get("negative_control_unexpected_pass_count") or 0)
            if value <= 0 and int(counts.get("negative_control_fail_count") or 0) > 0:
                rec["source_binding_tested_no_positive_signal"] += 1
            continue
        if kind == "source_scout_task":
            if str(payload.get("expected_exit") or row["expected_exit"] or "") == "source_strategy_repair":
                rec["source_strategy_repair_done"] += 1
            ingest_status = str(payload.get("source_binding_ingest_status") or "")
            if ingest_status == "rejected_binding_artifact":
                rec["source_binding_rejected"] += 1
                for failure in _source_binding_failures(payload) or ["rejected_binding_artifact"]:
                    failure_classes[family][failure] += 1
            elif ingest_status == "probe_enqueued":
                rec["source_binding_probe_enqueued"] += 1
            continue
        if kind == "source_search_task":
            exit_kind = str(payload.get("exit_kind") or "")
            if status == "failed" or exit_kind.startswith("source_search_rejected"):
                rec["source_search_failed_or_rejected"] += 1
            ready = int((payload.get("static_summary") or {}).get("canary_ready_total") or 0)
            if ready:
                rec["source_search_canary_ready_total"] += ready
            continue
        if kind == "llm_proposal_validate":
            exit_kind = str(payload.get("exit_kind") or "")
            if exit_kind == "proposal_rejected":
                rec["proposal_rejected"] += 1
            continue
        if kind == "agent_repair_task" and str(payload.get("exit_kind") or "") == "agent_repair_attempt_failed":
            rec["agent_task_failed"] += 1

    families: list[dict[str, Any]] = []
    for family, counts in sorted(per_family.items()):
        probes = int(counts.get("source_binding_probe_done") or 0)
        pending_probes = int(counts.get("source_binding_probe_pending") or 0)
        enqueued_probes = int(counts.get("source_binding_probe_enqueued") or 0)
        value = int(counts.get("source_binding_value_exits") or 0)
        rejected = int(counts.get("source_binding_rejected") or 0)
        no_signal = int(counts.get("source_binding_tested_no_positive_signal") or 0)
        terminal_source_binding_spend = probes
        in_flight_source_binding_spend = pending_probes
        source_binding_spend = probes + pending_probes
        attempted = terminal_source_binding_spend + rejected + int(counts.get("source_search_failed_or_rejected") or 0)
        conversion_rate = round(value / probes, 4) if probes else None
        loss_pressure = (
            rejected * 3
            + no_signal * 2
            + pending_probes
            + int(counts.get("source_search_failed_or_rejected") or 0) * 2
            + int(counts.get("proposal_rejected") or 0)
            + int(counts.get("agent_task_failed") or 0)
            + int(counts.get("source_binding_unexpected_negative_pass") or 0) * 20
        )
        strategy_done = int(counts.get("source_strategy_repair_done") or 0)
        repeated_no_value_spend = bool(value == 0 and terminal_source_binding_spend >= HARD_HOLD_NO_VALUE_SOURCE_ATTEMPTS)
        pending_pressure = bool(value == 0 and in_flight_source_binding_spend >= args.max_inflight_source_binding_before_throttle)
        throttle = bool(
            value == 0
            and (
                (attempted >= args.min_attempts_for_throttle and loss_pressure >= args.throttle_loss_threshold)
                or repeated_no_value_spend
                or pending_pressure
            )
        )
        hard_hold = bool(
            value == 0
            and (
                strategy_done > 0
                or probes >= HARD_HOLD_NO_VALUE_SOURCE_ATTEMPTS
                or attempted >= HARD_HOLD_NO_VALUE_SOURCE_ATTEMPTS
            )
            and (loss_pressure >= args.throttle_loss_threshold or repeated_no_value_spend)
        )
        hold_source_binding = bool(throttle and hard_hold)
        count_record = dict(sorted(counts.items()))
        families.append({
            "family": family,
            "counts": count_record,
            "failure_classes": dict(sorted(failure_classes[family].items(), key=lambda kv: (-kv[1], kv[0]))),
            "source_binding_probe_done": int(counts.get("source_binding_probe_done") or 0),
            "source_binding_probe_pending": pending_probes,
            "source_binding_probe_enqueued": enqueued_probes,
            "source_binding_probe_retired_before_execution": int(counts.get("source_binding_probe_retired_before_execution") or 0),
            "source_binding_spend": source_binding_spend,
            "terminal_source_binding_spend": terminal_source_binding_spend,
            "in_flight_source_binding_spend": in_flight_source_binding_spend,
            "source_binding_value_exits": value,
            "source_binding_negative_control_fail": int(counts.get("source_binding_negative_control_fail") or 0),
            "source_binding_unexpected_negative_pass": int(counts.get("source_binding_unexpected_negative_pass") or 0),
            "source_binding_tested_no_positive_signal": no_signal,
            "source_binding_rejected": rejected,
            "source_search_failed_or_rejected": int(counts.get("source_search_failed_or_rejected") or 0),
            "source_search_canary_ready_total": int(counts.get("source_search_canary_ready_total") or 0),
            "source_strategy_repair_done": strategy_done,
            "proposal_rejected": int(counts.get("proposal_rejected") or 0),
            "agent_task_failed": int(counts.get("agent_task_failed") or 0),
            "source_binding_conversion_rate": conversion_rate,
            "source_loss_pressure": loss_pressure,
            "source_attempts": attempted,
            "hard_hold_no_value_source_attempts": HARD_HOLD_NO_VALUE_SOURCE_ATTEMPTS,
            "max_inflight_source_binding_before_throttle": int(args.max_inflight_source_binding_before_throttle),
            "pending_pressure": pending_pressure,
            "recommended_source_action": (
                "hold_source_binding_until_new_target_evidence"
                if hold_source_binding
                else "repair_source_strategy_before_more_binding" if throttle else "continue_or_watch"
            ),
            "throttle_source_binding": throttle,
            "hold_source_binding": hold_source_binding,
        })
    families.sort(key=lambda r: (-int(r["source_loss_pressure"]), str(r["family"])))
    payload = {
        "schema": "leanmill-source-quality-feedback-v1",
        "generated_at_epoch": _now(),
        "window_s": int(args.window_s),
        "min_attempts_for_throttle": int(args.min_attempts_for_throttle),
        "throttle_loss_threshold": int(args.throttle_loss_threshold),
        "family_count": len(families),
        "families": families,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_source_quality_feedback_") as td:
        db = str(Path(td) / "q.sqlite")
        cx = work_queue.connect(db)
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
            "work_id": "probe1",
            "family": "fam",
            "probe_lane": "source_binding",
            "negative_control_fail_count": 3,
            "ratified_closure_count": 0,
        })
        payload = build(argparse.Namespace(
            queue_db=db,
            out=str(Path(td) / "out.json"),
            window_s=3600,
            min_attempts_for_throttle=1,
            throttle_loss_threshold=1,
            max_inflight_source_binding_before_throttle=3,
        ))
        assert payload["families"][0]["throttle_source_binding"] is True
        assert payload["families"][0]["hold_source_binding"] is False
        for idx in range(2):
            work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
                "work_id": f"probe-extra-{idx}",
                "family": "fam",
                "probe_lane": "source_binding",
                "negative_control_fail_count": 1,
                "ratified_closure_count": 0,
            })
        payload = build(argparse.Namespace(
            queue_db=db,
            out=str(Path(td) / "out_hard.json"),
            window_s=3600,
            min_attempts_for_throttle=1,
            throttle_loss_threshold=1,
            max_inflight_source_binding_before_throttle=3,
        ))
        assert payload["families"][0]["recommended_source_action"] == "hold_source_binding_until_new_target_evidence"
        work_queue.record_terminal_item(cx, kind="source_scout_task", status="done", priority=1, payload={
            "work_id": "strategy1",
            "family": "fam",
            "expected_exit": "source_strategy_repair",
            "exit_kind": "agent_repair_attempt_finished",
        })
        payload = build(argparse.Namespace(
            queue_db=db,
            out=str(Path(td) / "out2.json"),
            window_s=3600,
            min_attempts_for_throttle=1,
            throttle_loss_threshold=1,
            max_inflight_source_binding_before_throttle=3,
        ))
        assert payload["families"][0]["recommended_source_action"] == "hold_source_binding_until_new_target_evidence"
        for idx in range(3):
            work_queue.enqueue(cx, kind="repair_canary_probe", priority=1, payload={
                "work_id": f"pending-source-binding-{idx}",
                "family": "pending_fam",
                "probe_lane": "source_binding",
            })
        payload = build(argparse.Namespace(
            queue_db=db,
            out=str(Path(td) / "out_pending.json"),
            window_s=3600,
            min_attempts_for_throttle=1,
            throttle_loss_threshold=1,
            max_inflight_source_binding_before_throttle=3,
        ))
        pending = next(row for row in payload["families"] if row["family"] == "pending_fam")
        assert pending["source_binding_probe_pending"] == 3
        assert pending["throttle_source_binding"] is True
        assert pending["hold_source_binding"] is False
        assert pending["recommended_source_action"] == "repair_source_strategy_before_more_binding"
        for idx in range(2):
            work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="retired", priority=1, payload={
                "work_id": f"retired-before-execution-{idx}",
                "family": "newly_repaired_family",
                "probe_lane": "source_binding",
                "exit_kind": "retired_source_strategy_repair_required",
                "retired_by": "leanmill_learning_work_seeder",
                "retire_reason": "source_quality_feedback_held_source_binding_until_new_target_evidence",
            })
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=1, payload={
            "work_id": "newly-repaired-one-result",
            "family": "newly_repaired_family",
            "probe_lane": "source_binding",
            "negative_control_fail_count": 1,
            "ratified_closure_count": 0,
        })
        payload = build(argparse.Namespace(
            queue_db=db,
            out=str(Path(td) / "out_retired_before_execution.json"),
            window_s=3600,
            min_attempts_for_throttle=1,
            throttle_loss_threshold=1,
            max_inflight_source_binding_before_throttle=3,
        ))
        repaired = next(row for row in payload["families"] if row["family"] == "newly_repaired_family")
        assert repaired["source_binding_probe_retired_before_execution"] == 2
        assert repaired["terminal_source_binding_spend"] == 1
        assert repaired["hold_source_binding"] is False
        with tempfile.TemporaryDirectory(prefix="leanmill_source_quality_low_loss_") as td2:
            db2 = str(Path(td2) / "q.sqlite")
            cx2 = work_queue.connect(db2)
            for idx in range(3):
                work_queue.record_terminal_item(cx2, kind="repair_canary_probe", status="done", priority=1, payload={
                    "work_id": f"clean-source-binding-{idx}",
                    "family": "clean_no_value_fam",
                    "probe_lane": "source_binding",
                    "ratified_closure_count": 0,
                    "negative_control_fail_count": 0,
                })
            payload2 = build(argparse.Namespace(
                queue_db=db2,
                out=str(Path(td2) / "out.json"),
                window_s=3600,
                min_attempts_for_throttle=3,
                throttle_loss_threshold=99,
                max_inflight_source_binding_before_throttle=3,
            ))
            clean = next(row for row in payload2["families"] if row["family"] == "clean_no_value_fam")
            assert clean["recommended_source_action"] == "hold_source_binding_until_new_target_evidence"
    print("leanmill_source_quality_feedback self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--window-s", type=int, default=6 * 60 * 60)
    ap.add_argument("--min-attempts-for-throttle", type=int, default=3)
    ap.add_argument("--throttle-loss-threshold", type=int, default=6)
    ap.add_argument("--max-inflight-source-binding-before-throttle", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({"family_count": payload["family_count"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
