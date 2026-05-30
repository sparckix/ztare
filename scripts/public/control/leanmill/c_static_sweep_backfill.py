#!/usr/bin/env python3
"""Backfill missing governed-static sweep records for C-slice candidates.

This does not run Path C and does not credit proof value. It only completes the
static-control evidence owed before a C-discriminating row can be frozen.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

import leanmill_evaluation_harness_runner as harness
import leanmill_source_materialization as source_materialization
from leanmill_paths import DATA_DIR

DEFAULT_SELECTION = f"{DATA_DIR}/c_supply_batch_cleaned_c_discriminating_slice.json"
DEFAULT_CHECKPOINT_IN = f"{DATA_DIR}/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_CHECKPOINT_OUT = f"{DATA_DIR}/c_supply_batch_static_sweep_checkpoint.jsonl"
DEFAULT_CONTRACT = f"{DATA_DIR}/evaluation_harness_contract.json"
DEFAULT_RUN_ROOT = "/tmp/rung1/leanmill_c_static_sweep_backfill"
DEFAULT_OUT = f"{DATA_DIR}/c_supply_batch_static_sweep_backfill.json"
DEFAULT_SOURCE_SNAPSHOT_DIR = f"{DATA_DIR}/evaluation_harness_sources"
STATIC_ARM_ID = "governed_public_tool_static"


class _Args:
    def __init__(self, per_candidate_timeout_s: int, residual_fallback_family_call_budget: int = 0):
        self.per_candidate_timeout_s = per_candidate_timeout_s
        self.residual_fallback_family_call_budget = residual_fallback_family_call_budget


def _read_json(path: str | Path) -> Any:
    if not str(path):
        return None
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _append_jsonl(path: str | Path, rec: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _selected_rows(selection: dict[str, Any]) -> list[dict[str, Any]]:
    rows = selection.get("selected_rows") or selection.get("rows") or []
    return [dict(row) for row in rows if isinstance(row, dict) and str(row.get("row_id") or "")]


def _iter_context_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [row for row in obj if isinstance(row, dict)]
    if not isinstance(obj, dict):
        return []
    for key in ("rows", "selected_rows", "candidate_rows", "items", "corpus"):
        rows = obj.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _hydrate_rows_from_context(rows: list[dict[str, Any]], row_context_path: str | Path) -> list[dict[str, Any]]:
    context = {
        str(row.get("row_id") or row.get("id") or row.get("target_id") or ""): row
        for row in _iter_context_rows(_read_json(row_context_path))
        if str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
    }
    hydrated: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
        base = dict(context.get(row_id) or {})
        base.update(row)
        if "source" not in base and isinstance((context.get(row_id) or {}).get("source"), dict):
            base["source"] = (context.get(row_id) or {}).get("source")
        hydrated.append(base)
    return hydrated


def _arm(contract: dict[str, Any], arm_id: str) -> dict[str, Any]:
    for arm in contract.get("arms") or []:
        if isinstance(arm, dict) and str(arm.get("arm") or "") == arm_id:
            return arm
    raise SystemExit(f"missing arm in contract: {arm_id}")


def _existing(records: list[dict[str, Any]], arm_id: str) -> set[str]:
    return {
        str(rec.get("row_id") or "")
        for rec in records
        if str(rec.get("arm") or "") == arm_id and str(rec.get("row_id") or "")
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    selection = _read_json(args.selection) or {}
    contract = _read_json(args.contract) or {}
    rows = _hydrate_rows_from_context(_selected_rows(selection), args.row_context)
    materialization = source_materialization.materialize_row_sources(
        rows,
        out_dir=args.source_snapshot_dir,
        mathlib_root=args.mathlib_root,
    )
    arm = _arm(contract, args.arm)
    out_checkpoint = Path(args.out_checkpoint)
    if not out_checkpoint.exists() and Path(args.checkpoint).exists():
        out_checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.checkpoint, out_checkpoint)
    records = _read_jsonl(out_checkpoint)
    done = _existing(records, args.arm)
    owed = [row for row in rows if str(row.get("row_id") or "") not in done]
    ran: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if owed and not args.allow_heavy_lean:
        skipped = [{"row_id": str(row.get("row_id") or ""), "reason": "requires_allow_heavy_lean"} for row in owed]
    else:
        run_root = Path(args.run_root)
        started = time.time()
        for row in owed[: max(0, int(args.limit))]:
            if args.wall_timeout_s and time.time() - started >= args.wall_timeout_s:
                skipped.append({"row_id": str(row.get("row_id") or ""), "reason": "wall_timeout_hit"})
                break
            rec = harness._run_row_arm(
                _Args(per_candidate_timeout_s=int(args.per_candidate_timeout_s)),
                row=row,
                arm=arm,
                specs=[],
                max_calls=int(args.max_tool_calls),
                run_root=run_root,
                wall_timeout_s=int(args.row_wall_timeout_s),
            )
            rec["run_id"] = args.run_id or f"c_static_sweep_{int(started)}"
            rec["static_sweep_backfill_schema"] = "leanmill-c-static-sweep-backfill-record-v1"
            _append_jsonl(out_checkpoint, rec)
            ran.append({"row_id": rec.get("row_id"), "arm": rec.get("arm"), "learning_exit": rec.get("learning_exit"), "attempt_count": rec.get("attempt_count")})
    result = {
        "schema": "leanmill-c-static-sweep-backfill-v1",
        "selection": args.selection,
        "checkpoint_in": args.checkpoint,
        "checkpoint_out": str(out_checkpoint),
        "contract": args.contract,
        "arm": args.arm,
        "selected_count": len(rows),
        "source_materialization": materialization,
        "existing_count": len(done),
        "owed_count": len(owed),
        "ran_count": len(ran),
        "skipped_count": len(skipped),
        "ran": ran,
        "skipped": skipped[:50],
        "status": "complete" if len(ran) == len(owed) or not owed else "incomplete",
        "proof_credit": "none_static_control_only",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_static_sweep_") as td:
        root = Path(td)
        sel = root / "sel.json"
        ck = root / "ck.jsonl"
        out_ck = root / "out.jsonl"
        contract = root / "contract.json"
        src = root / "r1.lean"
        src.write_text("theorem r1 : True := by\n  trivial\n")
        sel.write_text(json.dumps({"selected_rows": [{"row_id": "r1", "source_file": str(src), "target_resolution_status": "pass"}]}) + "\n")
        ck.write_text(json.dumps({"row_id": "r1", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal"}) + "\n")
        contract.write_text(json.dumps({"arms": [{"arm": STATIC_ARM_ID, "uses_governance_gate": True, "uses_residual_memory": False, "route": [{"tool_id": "trivial", "tactic": "trivial", "default_timeout_s": 5}]}]}) + "\n")
        dry = build(argparse.Namespace(selection=str(sel), row_context="", checkpoint=str(ck), out_checkpoint=str(out_ck), contract=str(contract), arm=STATIC_ARM_ID, run_root=str(root / "run"), out=None, run_id="test", allow_heavy_lean=False, limit=10, max_tool_calls=1, per_candidate_timeout_s=5, row_wall_timeout_s=10, wall_timeout_s=30, source_snapshot_dir=str(root / "sources"), mathlib_root=""))
        assert dry["owed_count"] == 1 and dry["ran_count"] == 0 and dry["skipped_count"] == 1, dry
        assert dry["source_materialization"]["counts"]["already_present"] == 1, dry
        assert out_ck.exists(), dry
    print("leanmill_c_static_sweep_backfill self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", default=DEFAULT_SELECTION)
    ap.add_argument("--row-context", default=f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json")
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT_IN)
    ap.add_argument("--out-checkpoint", default=DEFAULT_CHECKPOINT_OUT)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--arm", default=STATIC_ARM_ID)
    ap.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--allow-heavy-lean", action="store_true")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--max-tool-calls", type=int, default=9)
    ap.add_argument("--per-candidate-timeout-s", type=int, default=60)
    ap.add_argument("--row-wall-timeout-s", type=int, default=240)
    ap.add_argument("--wall-timeout-s", type=int, default=900)
    ap.add_argument("--source-snapshot-dir", default=DEFAULT_SOURCE_SNAPSHOT_DIR)
    ap.add_argument("--mathlib-root", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build(args)
    print(json.dumps({"status": result["status"], "owed_count": result["owed_count"], "ran_count": result["ran_count"], "skipped_count": result["skipped_count"], "out_checkpoint": result["checkpoint_out"], "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
