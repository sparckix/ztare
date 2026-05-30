#!/usr/bin/env python3
"""GM/operator WorkItem lane for audited LeanMill supervisor work.

This lane is for the in-thread GM/operator, not for proof ratification. It
lets the supervisor claim bounded tasks from the same queue, write receipts,
and compare downstream conversion against API LLM and subscription-agent work.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_ALLOCATOR = f"{DEFAULT_DATA_DIR}/source_family_allocator.json"
DEFAULT_OUT_DIR = f"{DEFAULT_DATA_DIR}/gm_operator_outputs"
DEFAULT_SEED_STATUS = f"{DEFAULT_DATA_DIR}/gm_operator_seed_status.json"
VALID_EXITS = {
    "gm_source_strategy_review",
    "gm_hold_review",
    "gm_sibling_or_heldout_review",
    "gm_retire_decision",
    "gm_operator_required",
}
ACTION_EXIT = {
    "hold_source_binding_until_new_target_evidence": "gm_hold_review",
    "repair_source_strategy_before_more_binding": "gm_source_strategy_review",
    "seek_heldout_validation": "gm_sibling_or_heldout_review",
    "seek_sibling_or_hold": "gm_sibling_or_heldout_review",
    "seek_first_useful_exit_or_retire": "gm_sibling_or_heldout_review",
}


def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _priority_base(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="formula_bases",
        key=key,
        fallback=fallback,
    )


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "gm"


def _open_same_family_exists(cx: Any, *, family: str) -> bool:
    row = cx.execute(
        """
        SELECT 1
        FROM work_items
        WHERE kind='gm_operator_task'
          AND family=?
          AND status IN ('queued','claimed','running')
        LIMIT 1
        """,
        (family,),
    ).fetchone()
    return row is not None


def seed(args: argparse.Namespace) -> dict[str, Any]:
    allocator = _read(args.allocator)
    cx = work_queue.connect(args.queue_db)
    enqueued: list[dict[str, Any]] = []
    skipped_open = 0
    run_id = args.run_id or str(int(time.time()))
    for rec in allocator.get("allocations") or []:
        if len(enqueued) >= max(0, args.max_tasks):
            break
        family = str(rec.get("family") or "")
        action = str(rec.get("recommended_action") or "")
        expected_exit = ACTION_EXIT.get(action)
        if not family or not expected_exit:
            continue
        if _open_same_family_exists(cx, family=family):
            skipped_open += 1
            continue
        work_id = f"gm:{family}:{_slug(expected_exit)}:{run_id}"
        task = {
            "work_id": work_id,
            "family": family,
            "station": "gm_operator",
            "expected_exit": expected_exit,
            "recommended_action": action,
            "allocator_record": rec,
            "task": (
                "GM/operator review. Produce a bounded learning-unit decision: "
                "new target-evidence route, sibling/heldout plan, source-binding hold, or tested retirement. "
                "Do not claim proof value or update scoreboards."
            ),
            "credit_type": "none",
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
            "allowed_artifact_root": args.output_dir,
        }
        work_queue.enqueue(
            cx,
            kind="gm_operator_task",
            priority=int(_priority_base(args, "gm_operator_lane", 180) + float(rec.get("yield_score") or 0.0)),
            payload=task,
            max_attempts=1,
        )
        work_queue.append_event(args.events, {
            "event_type": "gm_operator_task_enqueued",
            "work_id": work_id,
            "payload": {"family": family, "expected_exit": expected_exit, "recommended_action": action},
        })
        enqueued.append({"work_id": work_id, "family": family, "expected_exit": expected_exit, "recommended_action": action})
    payload = {
        "schema": "leanmill-gm-operator-seed-status-v1",
        "generated_at_epoch": int(time.time()),
        "allocator": args.allocator,
        "enqueued": len(enqueued),
        "skipped_open": skipped_open,
        "enqueued_tasks": enqueued,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def claim(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    item = work_queue.claim(cx, worker_id=args.worker_id, kinds=["gm_operator_task"], lease_s=args.lease_s)
    if not item:
        return {"claimed": False}
    work_queue.update_status(cx, work_id=item["work_id"], status="running")
    work_queue.append_event(args.events, {
        "event_type": "gm_operator_task_claimed",
        "work_id": item["work_id"],
        "worker_id": args.worker_id,
        "payload": {"family": item.get("family"), "expected_exit": item.get("expected_exit")},
    })
    return {"claimed": True, "work_id": item["work_id"], "payload": item.get("payload")}


def complete(args: argparse.Namespace) -> dict[str, Any]:
    if args.exit_kind not in VALID_EXITS:
        raise SystemExit(f"invalid --exit-kind {args.exit_kind!r}")
    cx = work_queue.connect(args.queue_db)
    row = cx.execute("SELECT * FROM work_items WHERE work_id=?", (args.work_id,)).fetchone()
    if row is None:
        raise SystemExit(f"unknown work_id {args.work_id}")
    payload = json.loads(row["payload_json"] or "{}")
    return complete_payload(
        argparse.Namespace(
            queue_db=args.queue_db,
            events=args.events,
            output_dir=args.output_dir,
        ),
        work_id=args.work_id,
        payload=payload,
        family=row["family"] or payload.get("family") or "",
        exit_kind=args.exit_kind,
        summary=args.summary,
        decision=args.decision,
    )


def complete_payload(
    args: argparse.Namespace,
    *,
    work_id: str,
    payload: dict[str, Any],
    family: str,
    exit_kind: str,
    summary: str,
    decision: str,
) -> dict[str, Any]:
    if exit_kind not in VALID_EXITS:
        raise SystemExit(f"invalid exit_kind {exit_kind!r}")
    cx = work_queue.connect(args.queue_db)
    output = {
        "schema": "leanmill-gm-operator-output-v1",
        "work_id": work_id,
        "family": family,
        "exit_kind": exit_kind,
        "summary": summary,
        "decision": decision,
        "credit_type": "none",
        "proof_credit_authority": "governance_gate",
        "worker_can_self_ratify": False,
        "created_at_epoch": int(time.time()),
    }
    out_path = Path(args.output_dir) / f"{_slug(work_id)}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    update = {
        "exit_kind": exit_kind,
        "gm_operator_output_path": str(out_path),
        "artifact_paths": [str(out_path)],
        "credit_type": "none",
        "proof_credit_authority": "governance_gate",
        "worker_can_self_ratify": False,
    }
    work_queue.update_status(cx, work_id=work_id, status="done", payload_update=update)
    work_queue.append_event(args.events, {
        "event_type": "gm_operator_task_done",
        "work_id": work_id,
        "payload": update,
        "artifact_paths": [str(out_path)],
    })
    return {"ok": True, "work_id": work_id, "output_path": str(out_path), "exit_kind": exit_kind}


def _auto_review(payload: dict[str, Any]) -> tuple[str, str, str]:
    expected = str(payload.get("expected_exit") or "")
    action = str(payload.get("recommended_action") or "")
    candidate = payload.get("heldout_candidate") or {}
    precheck = candidate.get("independence_precheck") if isinstance(candidate, dict) else {}
    if expected == "gm_sibling_or_heldout_review" and all(
        bool((precheck or {}).get(key))
        for key in ("not_same_row", "not_same_source_file", "not_same_target_alias", "not_used_in_template_design")
    ):
        row_id = str(candidate.get("row_id") or "")
        return (
            "gm_sibling_or_heldout_review",
            f"approved bounded heldout attempt planning for {row_id}; proof value still requires probe, matched negative control, and Governance Gate receipt",
            "approve_bounded_heldout_attempt_plan",
        )
    if expected == "gm_hold_review" or action == "hold_source_binding_until_new_target_evidence":
        return (
            "gm_hold_review",
            "hold direct source binding until new target evidence or family-spec evidence changes the candidate shape",
            "hold_source_binding",
        )
    if expected == "gm_source_strategy_review" or action == "repair_source_strategy_before_more_binding":
        return (
            "gm_source_strategy_review",
            "route to source-strategy repair before more source-binding probes",
            "repair_source_strategy_before_more_binding",
        )
    if expected in VALID_EXITS:
        return (
            expected,
            "recorded bounded GM review; downstream workers and Governance Gate retain proof authority",
            "continue_with_bounded_worker_path",
        )
    return (
        "gm_operator_required",
        "could not deterministically classify GM task",
        "operator_required",
    )


def auto(args: argparse.Namespace) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for _ in range(max(0, args.max_tasks)):
        claimed = claim(args)
        if not claimed.get("claimed"):
            break
        payload = claimed.get("payload") or {}
        exit_kind, summary, decision = _auto_review(payload)
        done = complete_payload(
            args,
            work_id=str(claimed["work_id"]),
            payload=payload,
            family=str(payload.get("family") or ""),
            exit_kind=exit_kind,
            summary=summary,
            decision=decision,
        )
        actions.append(done)
    result = {
        "schema": "leanmill-gm-operator-auto-drain-v1",
        "generated_at_epoch": int(time.time()),
        "completed": len(actions),
        "actions": actions,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_gm_operator_lane_") as td:
        allocator = Path(td) / "allocator.json"
        allocator.write_text(json.dumps({
            "allocations": [
                {"family": "fam", "recommended_action": "hold_source_binding_until_new_target_evidence", "yield_score": 7}
            ]
        }) + "\n")
        db = str(Path(td) / "q.sqlite")
        events = str(Path(td) / "events.jsonl")
        out = str(Path(td) / "seed.json")
        payload = seed(argparse.Namespace(
            allocator=str(allocator),
            queue_db=db,
            events=events,
            output_dir=str(Path(td) / "out"),
            max_tasks=1,
            run_id="r",
            out=out,
        ))
        assert payload["enqueued"] == 1
        claimed = claim(argparse.Namespace(queue_db=db, events=events, worker_id="gm", lease_s=30))
        assert claimed["claimed"] is True
        done = complete(argparse.Namespace(
            queue_db=db,
            events=events,
            work_id=claimed["work_id"],
            exit_kind="gm_hold_review",
            summary="hold until new target evidence",
            decision="hold_source_binding",
            output_dir=str(Path(td) / "out"),
        ))
        assert done["ok"] is True
        payload = seed(argparse.Namespace(
            allocator=str(allocator),
            queue_db=db,
            events=events,
            output_dir=str(Path(td) / "out"),
            max_tasks=1,
            run_id="r2",
            out=out,
        ))
        assert payload["enqueued"] == 1
        auto_done = auto(argparse.Namespace(
            queue_db=db,
            events=events,
            worker_id="gm-auto",
            lease_s=30,
            output_dir=str(Path(td) / "out"),
            max_tasks=1,
            out=str(Path(td) / "auto.json"),
        ))
        assert auto_done["completed"] == 1
    print("leanmill_gm_operator_lane self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--allocator", default=DEFAULT_ALLOCATOR)
    ap.add_argument("--output-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--out", default=DEFAULT_SEED_STATUS)
    ap.add_argument("--worker-id", default="gm-operator")
    ap.add_argument("--lease-s", type=int, default=3600)
    ap.add_argument("--max-tasks", type=int, default=3)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--work-id", default="")
    ap.add_argument("--exit-kind", default="")
    ap.add_argument("--summary", default="")
    ap.add_argument("--decision", default="")
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    sub = ap.add_mutually_exclusive_group()
    sub.add_argument("--seed", action="store_true")
    sub.add_argument("--claim", action="store_true")
    sub.add_argument("--complete", action="store_true")
    sub.add_argument("--auto", action="store_true")
    sub.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.claim:
        print(json.dumps(claim(args), indent=2, sort_keys=True))
        return 0
    if args.complete:
        print(json.dumps(complete(args), indent=2, sort_keys=True))
        return 0
    if args.auto:
        print(json.dumps(auto(args), indent=2, sort_keys=True))
        return 0
    payload = seed(args)
    print(json.dumps({"enqueued": payload["enqueued"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
