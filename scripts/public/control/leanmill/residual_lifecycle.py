#!/usr/bin/env python3
"""Materialize residual/canary lifecycle states from LeanMill artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = "/tmp/rung1"


STATE_ORDER = {
    "raw_residual": 0,
    "classified_residual": 1,
    "proposed_canary": 2,
    "drained_canary": 3,
    "ratified_closure": 4,
    "exact_gap_candidate": 4,
    "valid_falsifier_candidate": 4,
    "seed_family_hold": 4,
    "family_superseded": 4,
    "retired": 4,
}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"event": "malformed_jsonl", "source_path": str(path)})
    return out


def _json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(errors="ignore"))
    except Exception:
        return {}


def _key(row_id: str, family: str = "") -> str:
    return f"{family or 'unknown'}::{row_id or 'unknown'}"


def _advance(rows: dict[str, dict[str, Any]], key: str, update: dict[str, Any]) -> None:
    cur = rows.setdefault(key, {"key": key, "state": "raw_residual", "events": []})
    state = str(update.get("state") or cur.get("state") or "raw_residual")
    if STATE_ORDER.get(state, 0) >= STATE_ORDER.get(str(cur.get("state") or "raw_residual"), 0):
        cur["state"] = state
    cur.update({k: v for k, v in update.items() if k not in {"event"}})
    cur.setdefault("events", []).append(update)


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    roots = [Path(p) for p in args.root]
    for root in roots:
        residual_paths = list(root.glob("**/events/residual_compiler_residuals.jsonl"))
        residual_paths.extend(root.glob("**/events/path_c_residuals.jsonl"))
        for path in residual_paths:
            for rec in _jsonl(path):
                row_id = str(rec.get("row_id") or "")
                family = str(rec.get("repair_family") or rec.get("lane") or "")
                _advance(rows, _key(row_id, family), {
                    "state": "raw_residual",
                    "row_id": row_id,
                    "repair_family": family,
                    "residual_class": rec.get("residual_class"),
                    "source_path": str(path),
                })
        for path in root.glob("**/*decision*.json"):
            obj = _json(path)
            for rec in obj.get("decisions") or []:
                decision = str(rec.get("decision") or "")
                row_id = str(rec.get("row_id") or "")
                family = str(rec.get("repair_family") or rec.get("lane") or "")
                state = decision if decision in STATE_ORDER else "classified_residual"
                _advance(rows, _key(row_id, family), {
                    "state": state,
                    "row_id": row_id,
                    "repair_family": family,
                    "decision": decision,
                    "next_lever": rec.get("next_lever"),
                    "reason": rec.get("reason"),
                    "source_path": str(path),
                })
        for path in root.glob("**/events/closed.jsonl"):
            for rec in _jsonl(path):
                row_id = str(rec.get("row_id") or "")
                family = str(rec.get("repair_family") or rec.get("lane") or "")
                _advance(rows, _key(row_id, family), {
                    "state": "ratified_closure" if rec.get("event") == "ratified_closure" else "drained_canary",
                    "row_id": row_id,
                    "repair_family": family,
                    "persisted": [
                        c.get("persisted") for c in rec.get("ratified_candidates") or [] if c.get("persisted")
                    ],
                    "source_path": str(path),
                })
        for path in root.glob("**/events/negative_controls.jsonl"):
            for rec in _jsonl(path):
                row_id = str(rec.get("row_id") or "")
                family = str(rec.get("repair_family") or rec.get("lane") or "")
                _advance(rows, _key(row_id, family), {
                    "state": "drained_canary",
                    "row_id": row_id,
                    "repair_family": family,
                    "negative_control_event": rec.get("event"),
                    "source_path": str(path),
                })
    state_counts: dict[str, int] = {}
    for row in rows.values():
        state = str(row.get("state") or "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1
    payload = {
        "schema": "leanmill-residual-lifecycle-v1",
        "roots": [str(p) for p in roots],
        "row_count": len(rows),
        "state_counts": state_counts,
        "rows": sorted(rows.values(), key=lambda r: (str(r.get("state")), str(r.get("key")))),
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(root=["/tmp/no_such_root"], out=None))
    assert payload["row_count"] == 0
    print("leanmill_residual_lifecycle self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=[DEFAULT_ROOT])
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "row_count": payload["row_count"],
        "state_counts": payload["state_counts"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
