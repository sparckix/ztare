#!/usr/bin/env python3
"""Repair visible agentic handoff debt by seeding downstream verification work.

This tool is intentionally narrow: it reads the factory-intelligence
agentic_handoff_contract hard-leak list, reconstructs activation selections for
accepted family-spec patches, and calls the normal learning-work seeder. It
does not grant credit.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import leanmill_work_queue as work_queue
from leanmill_paths import DATA_DIR
from src.ztare.leanmill.contracts import handoff as handoff_contract


DEFAULT_INTELLIGENCE = f"{DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_OUT = f"{DATA_DIR}/agentic_handoff_repair.json"
DEFAULT_SPEC_DIR = "analytics/public/leanmill/repair_families"
DEFAULT_ACTIVATION_DIR = f"{DATA_DIR}/family_birth_activation"
DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json"


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _payload_for_work_id(cx: sqlite3.Connection, work_id: str) -> dict[str, Any]:
    row = cx.execute("SELECT payload_json FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone()
    if row is None:
        return {}
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_family_spec(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _candidate_rows(payload: dict[str, Any], *, mode: str) -> list[str]:
    rows: list[str] = []
    if mode == "family_birth_candidate":
        return rows
    for key in ("c_supply_candidate_rows", "candidate_row_ids", "row_ids"):
        for row_id in payload.get(key) or []:
            if str(row_id):
                rows.append(str(row_id))
    for key in ("c_supply_candidates", "family_birth_candidates"):
        for row in payload.get(key) or []:
            if isinstance(row, dict) and row.get("row_id"):
                rows.append(str(row.get("row_id")))
    return sorted(set(rows))


def _activation_selection(spec_path: Path, payload: dict[str, Any], *, mode: str) -> dict[str, Any]:
    spec = _load_family_spec(spec_path)
    family = str(spec.get("family") or payload.get("family") or spec_path.stem)
    activation_source = "family_birth_candidate" if mode == "family_birth_candidate" else (
        "c_supply_template_backfill" if mode == "c_supply_template_backfill" else "family_spec_positive_repair"
    )
    candidate_rows = set(_candidate_rows(payload, mode=mode))
    positives: set[str] = set()
    negatives: set[str] = set()
    for template in spec.get("templates") or []:
        if not isinstance(template, dict):
            continue
        row_id = str(template.get("row_id") or "")
        if not row_id:
            continue
        if candidate_rows and row_id not in candidate_rows:
            continue
        test_kind = str(template.get("test_kind") or "")
        if test_kind == "positive":
            positives.add(row_id)
        elif test_kind == "negative_control":
            negatives.add(row_id)
    selected = sorted(positives.intersection(negatives))
    return {
        "schema": handoff_contract.REPAIR_SELECTION_SCHEMA,
        "family": family,
        "source_family_spec": str(spec_path),
        "activation_source": activation_source,
        "source_patch_mode": mode,
        "selected_rows": [
            {"row_id": row_id, "matched_families": [family], "activation_source": activation_source}
            for row_id in selected
        ],
        "candidate_row_count": len(candidate_rows),
        "paired_row_count": len(selected),
        "credit_boundary": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        },
    }


def _row_context(payload: dict[str, Any], fallback: str) -> str:
    for key in ("c_supply_row_context", "family_birth_activation_row_context", "row_context"):
        value = str(payload.get(key) or "")
        if value and Path(value).exists():
            return value
    return fallback


def _seed_cmd(args: argparse.Namespace, *, selection: Path, out: Path, out_dir: Path, row_context: str, run_id: str) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/public/control/leanmill/learning_work_seeder.py",
        "--family-spec-selection", str(selection),
        "--family-spec-dir", args.spec_dir,
        "--out", str(out),
        "--out-dir", str(out_dir),
        "--queue-db", args.queue_db,
        "--events", args.events,
        "--run-id", run_id,
        "--max-family-spec-probe-families", "1",
        "--max-probe-families", "0",
        "--max-proposal-jobs", "0",
        "--max-agent-jobs", "0",
        "--max-family-spec-repair-jobs", "0",
        "--max-family-spec-generality-jobs", "0",
        "--max-total-jobs", str(max(1, int(args.max_total_jobs))),
        "--max-enqueued", str(max(0, int(args.max_enqueued))),
        "--max-tests-per-probe", str(max(1, int(args.max_tests_per_probe))),
        "--family-spec-probe-rows-per-work-item", str(max(1, int(args.family_spec_probe_rows_per_work_item))),
    ]
    if row_context:
        cmd.extend(["--row-context", row_context])
    if bool(args.enqueue):
        cmd.append("--enqueue")
    return cmd


def build(args: argparse.Namespace) -> dict[str, Any]:
    intelligence = _read_json(args.intelligence)
    handoff = intelligence.get("agentic_handoff_contract") if isinstance(intelligence, dict) else {}
    hard_leaks = [row for row in (handoff.get("hard_leaks") or []) if isinstance(row, dict)] if isinstance(handoff, dict) else []
    root = Path(args.activation_dir)
    root.mkdir(parents=True, exist_ok=True)
    cx = work_queue.connect(args.queue_db)
    attempts: list[dict[str, Any]] = []
    repaired = 0
    for leak in hard_leaks[: max(0, int(args.max_repairs))]:
        work_id = str(leak.get("work_id") or "")
        mode = str(leak.get("mode") or "")
        family = str(leak.get("family") or "")
        if mode not in {"family_birth_candidate", "family_spec_positive_repair", "c_supply_template_backfill"}:
            attempts.append({"work_id": work_id, "status": "skipped", "reason": "unsupported_mode", "mode": mode})
            continue
        payload = _payload_for_work_id(cx, work_id)
        if not payload:
            attempts.append({"work_id": work_id, "status": "skipped", "reason": "missing_queue_payload", "mode": mode})
            continue
        spec_target = str(payload.get("family_spec_patch_target") or "")
        spec_path = Path(spec_target) if spec_target else Path(args.spec_dir) / f"{_slug(family)}.yaml"
        if not spec_path.exists():
            attempts.append({"work_id": work_id, "status": "skipped", "reason": "missing_family_spec", "mode": mode, "spec_path": str(spec_path)})
            continue
        stamp = f"{int(time.time())}_{_slug(work_id)}"
        selection_path = root / f"handoff_repair_{stamp}.selection.json"
        out_path = root / f"handoff_repair_{stamp}.seed_plan.json"
        out_dir = root / f"queued_work_handoff_repair_{stamp}"
        selection = _activation_selection(spec_path, payload, mode=mode)
        _write_json(selection_path, selection)
        if not selection.get("selected_rows"):
            receipt = {
                "schema": handoff_contract.REPAIR_RECEIPT_SCHEMA,
                "status": "skipped",
                "reason": "no_paired_positive_negative_rows",
                "family": family,
                "work_id": work_id,
                "family_spec_patch_mode": mode,
                "selection": str(selection_path),
                "enqueued": 0,
                "job_count": 0,
                "selected_row_count": 0,
                "candidate_row_count": selection.get("candidate_row_count"),
                "credit_boundary": selection.get("credit_boundary"),
            }
            work_queue.update_status(cx, work_id=work_id, status="done", payload_update={
                handoff_contract.receipt_field_for_mode(mode): receipt,
                "agentic_handoff_repair_receipt": receipt,
            })
            attempts.append({
                "work_id": work_id,
                "status": "blocked",
                "reason": "no_paired_positive_negative_rows",
                "mode": mode,
                "selection": str(selection_path),
                "paired_row_count": selection.get("paired_row_count"),
                "candidate_row_count": selection.get("candidate_row_count"),
            })
            continue
        cmd = _seed_cmd(
            args,
            selection=selection_path,
            out=out_path,
            out_dir=out_dir,
            row_context=_row_context(payload, args.row_context),
            run_id=f"agentic_handoff_repair_{_slug(family)}_{int(time.time())}",
        )
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=max(1, int(args.command_timeout_s)), check=False)
        plan = _read_json(out_path)
        enqueued = int(plan.get("enqueued") or 0) if isinstance(plan, dict) else 0
        if enqueued > 0:
            repaired += enqueued
        attempt = {
            "work_id": work_id,
            "family": family,
            "mode": mode,
            "status": "pass" if proc.returncode == 0 else "fail",
            "returncode": proc.returncode,
            "selection": str(selection_path),
            "seed_plan": str(out_path),
            "job_count": int(plan.get("job_count") or 0) if isinstance(plan, dict) else 0,
            "enqueued": enqueued,
            "skip_counts": plan.get("skip_counts") if isinstance(plan, dict) else {},
            "stdout_tail": (proc.stdout or "")[-1000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
        }
        receipt = {
            "schema": handoff_contract.REPAIR_RECEIPT_SCHEMA,
            "status": "pass" if proc.returncode == 0 else "fail",
            "family": family,
            "work_id": work_id,
            "family_spec_patch_mode": mode,
            "selection": str(selection_path),
            "seed_plan": str(out_path),
            "selected_row_count": len(selection.get("selected_rows") or []),
            "enqueued": enqueued,
            "job_count": attempt["job_count"],
            "skip_counts": attempt["skip_counts"],
            "returncode": proc.returncode,
            "reason": "" if proc.returncode == 0 else "handoff_repair_seed_command_failed",
            "credit_boundary": selection.get("credit_boundary"),
        }
        work_queue.update_status(cx, work_id=work_id, status="done", payload_update={
            handoff_contract.receipt_field_for_mode(mode): receipt,
            "agentic_handoff_repair_receipt": receipt,
        })
        attempts.append(attempt)
        work_queue.append_event(args.events, {
            "event_type": "agentic_handoff_repair_attempt",
            "work_id": work_id,
            "payload": attempt,
            "artifact_paths": [str(selection_path), str(out_path)],
        })
    result = {
        "schema": "leanmill-agentic-handoff-repair-v1",
        "generated_at_epoch": int(time.time()),
        "intelligence": args.intelligence,
        "input_hard_leak_count": len(hard_leaks),
        "attempted_count": len(attempts),
        "enqueued": repaired,
        "attempts": attempts,
        "credit_boundary": "Handoff repair only creates deterministic probe inventory or typed blocked receipts; it grants no proof, benchmark, governance, or C credit.",
    }
    if args.out:
        _write_json(args.out, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intelligence", default=DEFAULT_INTELLIGENCE)
    ap.add_argument("--queue-db", default=f"{DATA_DIR}/leanmill_work_queue.sqlite")
    ap.add_argument("--events", default=f"{DATA_DIR}/leanmill_events.jsonl")
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--activation-dir", default=DEFAULT_ACTIVATION_DIR)
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--max-repairs", type=int, default=4)
    ap.add_argument("--max-total-jobs", type=int, default=16)
    ap.add_argument("--max-enqueued", type=int, default=16)
    ap.add_argument("--max-tests-per-probe", type=int, default=4)
    ap.add_argument("--family-spec-probe-rows-per-work-item", type=int, default=1)
    ap.add_argument("--command-timeout-s", type=int, default=180)
    ap.add_argument("--enqueue", action="store_true")
    args = ap.parse_args()
    result = build(args)
    print(json.dumps({
        "attempted_count": result.get("attempted_count"),
        "enqueued": result.get("enqueued"),
        "input_hard_leak_count": result.get("input_hard_leak_count"),
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
