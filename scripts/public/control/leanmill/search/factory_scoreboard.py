#!/usr/bin/env python3
"""Aggregate P0 analytics for a LeanSearch factory run.

Reads factory event streams and consumer checkpoints from a root directory and
emits a compact solver/governance/curriculum scoreboard. This is intentionally
stdlib-only and conservative: unknown metrics are reported as null/0 rather
than inferred from prose.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


STREAMS = ("closed", "to_govern", "path_c_residuals")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    rank = (p / 100.0) * (len(vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(vals) - 1)
    frac = rank - lo
    return round(vals[lo] + frac * (vals[hi] - vals[lo]), 3)


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 3) if values else None,
        "p50": _percentile(values, 50),
        "p90": _percentile(values, 90),
        "max": round(max(values), 3) if values else None,
    }


def _event_dir(root: Path, lane: str) -> Path:
    return root / lane / "events"


def _lanes(root: Path) -> list[str]:
    out: list[str] = []
    for p in sorted(root.iterdir()) if root.exists() else []:
        if p.is_dir() and (p / "events").is_dir():
            out.append(p.name)
    return out


def _stream_rows(root: Path, lane: str, stream: str) -> list[dict[str, Any]]:
    return _read_jsonl(_event_dir(root, lane) / f"{stream}.jsonl")


def _consumer_rows(root: Path, lane: str) -> list[dict[str, Any]]:
    return _read_jsonl(root / lane / "consumers" / "path_b_governance.jsonl")


def _summarize_lane(root: Path, lane: str) -> dict[str, Any]:
    closed = _stream_rows(root, lane, "closed")
    to_govern = _stream_rows(root, lane, "to_govern")
    residuals = _stream_rows(root, lane, "path_c_residuals")
    consumer = _consumer_rows(root, lane)
    a_cycles = [float(r.get("cycle_s") or 0.0) for r in to_govern + residuals if r.get("cycle_s") is not None]
    b_cycles = [float(r.get("cycle_s") or 0.0) for r in consumer if r.get("cycle_s") is not None]
    residual_classes: dict[str, int] = {}
    for rec in residuals:
        key = str(rec.get("residual_class") or "unknown")
        residual_classes[key] = residual_classes.get(key, 0) + 1
    ratified_candidates = sum(len(r.get("ratified_candidates") or []) for r in closed)
    candidate_sources = sum(len(r.get("closed_candidates") or []) for r in to_govern)
    attempted = sum(len(r.get("candidate_names_attempted") or []) for r in consumer)
    return {
        "lane": lane,
        "solver": {
            "ratified_proof_closure": len(closed),
            "exact_gap": 0,
            "valid_falsifier": 0,
            "consequence_exposure": 0,
            "invalid_or_retired": sum(1 for r in consumer if r.get("status") in {"residualized", "skipped"}),
        },
        "governance": {
            "false_ratifications_caught": 0,
            "wrong_target_kind_avoided": 0,
            "axiom_sorry_native_smuggling_blocked": 0,
            "source_order_debt": 0,
            "leakage_exclusions": 0,
            "governance_residualized": sum(1 for r in consumer if r.get("status") == "residualized"),
        },
        "curriculum": {
            "candidate_sources": candidate_sources,
            "canary_ready_rows": len(to_govern) + len(residuals),
            "ratified_candidates": ratified_candidates,
            "negative_controls": 0,
            "repair_trajectories": len(closed) + len(residuals),
            "first_failure_policy_labels": residual_classes,
            "path_c_residuals": len(residuals),
        },
        "flow": {
            "to_govern_events": len(to_govern),
            "closed_events": len(closed),
            "path_c_residual_events": len(residuals),
            "a_cycle_s": _stats(a_cycles),
            "b_cycle_s": _stats(b_cycles),
            "b_candidate_names_attempted": attempted,
        },
    }


def build_scoreboard(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    lanes = args.lane or _lanes(root)
    lane_rows = [_summarize_lane(root, lane) for lane in lanes]
    total = {
        "solver": {
            "ratified_proof_closure": sum(r["solver"]["ratified_proof_closure"] for r in lane_rows),
            "exact_gap": sum(r["solver"]["exact_gap"] for r in lane_rows),
            "valid_falsifier": sum(r["solver"]["valid_falsifier"] for r in lane_rows),
            "consequence_exposure": sum(r["solver"]["consequence_exposure"] for r in lane_rows),
            "invalid_or_retired": sum(r["solver"]["invalid_or_retired"] for r in lane_rows),
        },
        "governance": {
            "false_ratifications_caught": sum(r["governance"]["false_ratifications_caught"] for r in lane_rows),
            "wrong_target_kind_avoided": sum(r["governance"]["wrong_target_kind_avoided"] for r in lane_rows),
            "axiom_sorry_native_smuggling_blocked": sum(r["governance"]["axiom_sorry_native_smuggling_blocked"] for r in lane_rows),
            "source_order_debt": sum(r["governance"]["source_order_debt"] for r in lane_rows),
            "leakage_exclusions": sum(r["governance"]["leakage_exclusions"] for r in lane_rows),
            "governance_residualized": sum(r["governance"]["governance_residualized"] for r in lane_rows),
        },
        "curriculum": {
            "candidate_sources": sum(r["curriculum"]["candidate_sources"] for r in lane_rows),
            "canary_ready_rows": sum(r["curriculum"]["canary_ready_rows"] for r in lane_rows),
            "ratified_candidates": sum(r["curriculum"]["ratified_candidates"] for r in lane_rows),
            "negative_controls": sum(r["curriculum"]["negative_controls"] for r in lane_rows),
            "repair_trajectories": sum(r["curriculum"]["repair_trajectories"] for r in lane_rows),
            "path_c_residuals": sum(r["curriculum"]["path_c_residuals"] for r in lane_rows),
        },
    }
    payload = {
        "schema": "leansearch-factory-scoreboard-v1",
        "root": str(root),
        "lanes": lanes,
        "totals": total,
        "by_lane": lane_rows,
        "notes": {
            "exact_gap_valid_falsifier_consequence_exposure": "not yet emitted by current factory event schema",
            "negative_controls": "not yet emitted by current factory event schema",
            "governance_smuggling_metrics": "reported only when Path-B consumer emits explicit block reasons",
        },
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    assert _stats([1.0, 3.0])["mean"] == 2.0
    print("leansearch_factory_scoreboard self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=False, default="/tmp/rung1/leansearch_factory_mill")
    ap.add_argument("--lane", action="append")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build_scoreboard(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
