#!/usr/bin/env python3
"""LeanSearch repair factory.

Runs named repair lanes through the checkpointed action batcher and
publishes append-only event streams:
  - closed.jsonl: Path-B-ratified closures
  - to_govern.jsonl: compile closures awaiting Path-B governance
  - path_c_residuals.jsonl: every non-closure with residual_class + next_lever

The factory is intentionally local-file based. It is a streaming/event-bus
shape without infrastructure: every completed row appends one event before
the next row starts, so downstream consumers can tail the streams.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leansearch_action_batch as batch


DEFAULT_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_ROOT = "/tmp/rung1/leansearch_factory"


LANES: dict[str, dict[str, Any]] = {
    "abs_transport": {
        "families": ["local_abs_sum_transport_convert"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 1,
        "description": "Finite-sum abs-to-nonnegative transport via local Real sibling.",
    },
    "summability_transport": {
        "families": [
            "summability_nnreal_power2",
            "summability_real_nonneg_power2",
            "ennreal_tsum_condensation_shape",
        ],
        "rows": [
            "MCB_015_summable_condensed_iff",
            "MCB_016_summable_condensed_iff_of_nonneg",
            "MCB_017_summable_condensed_iff_of_eventu",
            "MCB_018_summable_condensed_iff",
            "MCB_019_summable_condensed_iff_of_nonneg",
        ],
        "max_candidates": 4,
        "max_actions": 2,
        "description": "Power-of-two condensation via Schlomilch sibling transport.",
    },
    "bigo_specialization": {
        "families": ["apply_easy"],
        "rows": ["MCB_012_isBigO_rpow_top_log_smul", "MCB_013_isBigO_rpow_zero_log_smul"],
        "max_candidates": 3,
        "max_actions": 3,
        "description": "BigO source specialization diagnostic lane.",
    },
    "geom_iff_direction": {
        "families": ["constructor_apply_easy", "apply_easy"],
        "rows": ["MCB_025_geom_mean_eq_arith_mean_weighted", "MCB_026_geom_mean_eq_arith_mean_weighted"],
        "max_candidates": 3,
        "max_actions": 3,
        "description": "Geom-mean iff direction planning diagnostic lane.",
    },
    "convolution_measure": {
        "families": ["convolution_source_shape", "apply_easy"],
        "rows": [
            "MCB_003_convolution_mono_right_of_nonneg",
            "MCB_004_convolution_congr",
            "MCB_006_integral_convolution",
        ],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Measure convolution source-shape diagnostic lane.",
    },
    "ennreal_tsum": {
        "families": ["apply_easy"],
        "rows": ["MCB_017_le_tsum_condensed"],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "ENNReal tsum/source-specialization diagnostic lane.",
    },
    "interval_inv_sq_sum": {
        "families": ["apply_easy"],
        "rows": ["MCB_022_sum_Ioo_inv_sq_le"],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Interval inverse-square sum diagnostic lane.",
    },
    "limit_tendsto_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Limit/Tendsto source-specialization diagnostic lane.",
    },
    "mellin_fourier_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Mellin/Fourier transform source-shape diagnostic lane.",
    },
    "rpow_inequality_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Power-inequality source-specialization diagnostic lane.",
    },
    "metric_speed_transport": {
        "families": ["constructor_apply_easy", "apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 4,
        "description": "Metric speed/Lipschitz iff diagnostic lane.",
    },
    "continuity_oscillation_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Oscillation/continuity source-specialization diagnostic lane.",
    },
    "spectral_rayleigh_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Spectral/Rayleigh quotient diagnostic lane.",
    },
    "local_extrema_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Local extrema/multiplier theorem diagnostic lane.",
    },
    "partial_homeomorph_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Open partial homeomorphism diagnostic lane.",
    },
    "orientation_areaform_transport": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 4,
        "max_actions": 3,
        "description": "Orientation/area-form diagnostic lane.",
    },
    "unclassified": {
        "families": ["apply_easy"],
        "rows": [],
        "max_candidates": 3,
        "max_actions": 2,
        "description": "Generic source-action probe for target-context-ready rows with no specialized lane yet.",
    },
}


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _lane_args(args: argparse.Namespace, lane: str, spec: dict[str, Any], run_id: str, started: float, offset: int) -> argparse.Namespace:
    root = Path(args.root)
    out_dir = root / lane / f"shard_{args.shard_index}_of_{args.shard_count}" / "rows"
    event_dir = root / lane / "events"
    telemetry_path = Path(args.telemetry) if args.telemetry else root / "iteration_telemetry.jsonl"
    row_ids = list(args.row_id or spec.get("rows") or [])
    return argparse.Namespace(
        row_id=row_ids,
        corpus=args.corpus,
        static_filter=args.static_filter,
        out_dir=str(out_dir),
        checkpoint=str(out_dir.parent / "checkpoint.jsonl"),
        summary=str(out_dir.parent / "summary.json"),
        lane=lane,
        event_dir=str(event_dir),
        factory_telemetry_path=str(telemetry_path),
        factory_run_id=run_id,
        factory_started_monotonic=started,
        factory_iteration_offset=offset,
        timeout=args.timeout,
        max_candidates=int(args.max_candidates or spec.get("max_candidates") or 4),
        max_actions=int(args.max_actions or spec.get("max_actions") or 1),
        action_family=list(args.action_family or spec.get("families") or []),
        candidate_name=[],
        backend=args.backend,
        score_candidates=args.score_candidates,
        require_positive_source_action=args.require_positive_source_action,
        govern_winners=args.govern_winners,
        save_dir="",
        resume=args.resume,
        limit=args.limit,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
    )


def _write_manifest(root: Path, lane: str, spec: dict[str, Any], bargs: argparse.Namespace, result: dict[str, Any]) -> None:
    event_dir = root / lane / "events"
    manifest = {
        "schema": "leansearch-factory-manifest-v1",
        "lane": lane,
        "description": spec.get("description"),
        "families": bargs.action_family,
        "rows": bargs.row_id or "filter_ready_rows",
        "shard_index": bargs.shard_index,
        "shard_count": bargs.shard_count,
        "summary": bargs.summary,
        "checkpoint": bargs.checkpoint,
        "events": {
            "closed": str(event_dir / "closed.jsonl"),
            "to_govern": str(event_dir / "to_govern.jsonl"),
            "path_c_residuals": str(event_dir / "path_c_residuals.jsonl"),
        },
        "result": result,
    }
    path = root / lane / f"manifest_shard_{bargs.shard_index}_of_{bargs.shard_count}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _summarize(root: Path, lane: str) -> dict[str, Any]:
    event_dir = root / lane / "events"
    closed = _read_jsonl(event_dir / "closed.jsonl")
    to_govern = _read_jsonl(event_dir / "to_govern.jsonl")
    residuals = _read_jsonl(event_dir / "path_c_residuals.jsonl")
    by_residual: dict[str, int] = {}
    cycle_values: list[float] = []
    lead_values: list[float] = []
    for rec in residuals:
        key = str(rec.get("residual_class") or "unknown")
        by_residual[key] = by_residual.get(key, 0) + 1
    for rec in closed + to_govern + residuals:
        if rec.get("cycle_s") is not None:
            cycle_values.append(float(rec.get("cycle_s") or 0.0))
        if rec.get("lead_s") is not None:
            lead_values.append(float(rec.get("lead_s") or 0.0))
    total_cycle_s = sum(cycle_values)
    max_lead_s = max(lead_values) if lead_values else 0.0
    return {
        "lane": lane,
        "closed": len(closed),
        "to_govern": len(to_govern),
        "path_c_residuals": len(residuals),
        "total_events": len(closed) + len(to_govern) + len(residuals),
        "cycle_time_seconds_total": round(total_cycle_s, 3),
        "cycle_time_seconds_mean": round(total_cycle_s / len(cycle_values), 3) if cycle_values else None,
        "lead_time_seconds_max": round(max_lead_s, 3),
        "throughput_events_per_hour": round((len(cycle_values) / max_lead_s) * 3600, 3) if max_lead_s > 0 else None,
        "by_residual_class": by_residual,
        "event_dir": str(event_dir),
    }


def run_factory(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or str(int(time.time()))
    started = time.monotonic()
    telemetry_path = Path(args.telemetry) if args.telemetry else root / "iteration_telemetry.jsonl"
    _append_jsonl(telemetry_path, {
        "record_type": "run_start",
        "schema": "leansearch-factory-telemetry-v1",
        "run_id": run_id,
        "project": "gp225_leansearch_repair_factory",
        "timestamp_utc": _now_iso(),
        "root": str(root),
        "rubric": "ratified_closure_or_compile_closure_or_path_c_residual",
        "iteration_budget": args.limit,
        "mutator_model": "deterministic_lean_action_templates",
        "judge_model": "path_b_governance" if args.govern_winners else "none",
    })
    lanes = list(args.lane or [])
    if args.all_lanes:
        lanes = sorted(LANES)
    if not lanes:
        lanes = ["summability_transport"]
    summaries = []
    offset = 0
    for lane in lanes:
        if lane not in LANES:
            raise SystemExit(f"unknown lane {lane}; choices={sorted(LANES)}")
        spec = LANES[lane]
        bargs = _lane_args(args, lane, spec, run_id, started, offset)
        result = batch.run_batch(bargs)
        _write_manifest(root, lane, spec, bargs, result)
        summaries.append(_summarize(root, lane))
        offset += len(result.get("rows") or [])
    final_score = sum(s.get("closed", 0) + s.get("to_govern", 0) for s in summaries)
    _append_jsonl(telemetry_path, {
        "record_type": "run_end",
        "schema": "leansearch-factory-telemetry-v1",
        "run_id": run_id,
        "timestamp_utc": _now_iso(),
        "final_iteration": max(0, offset - 1),
        "final_score": final_score,
        "run_exit_reason": "completed",
    })
    payload = {
        "schema": "leansearch-factory-run-v1",
        "run_id": run_id,
        "root": str(root),
        "telemetry": str(telemetry_path),
        "summaries": summaries,
    }
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    assert "summability_transport" in LANES
    assert "mellin_fourier_transport" in LANES
    assert "spectral_rayleigh_transport" in LANES
    assert "unclassified" in LANES
    assert "path_c_residuals" in _summarize(Path("/tmp/nonexistent_factory_self_test"), "x")
    print("leansearch_factory self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", action="append", choices=sorted(LANES))
    ap.add_argument("--all-lanes", action="store_true")
    ap.add_argument("--row-id", action="append", default=[])
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", default=DEFAULT_FILTER)
    ap.add_argument("--summary")
    ap.add_argument("--telemetry")
    ap.add_argument("--run-id")
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--max-candidates", type=int)
    ap.add_argument("--max-actions", type=int)
    ap.add_argument("--action-family", action="append", default=[])
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="subprocess")
    ap.add_argument("--score-candidates", action="store_true")
    ap.add_argument("--require-positive-source-action", action="store_true")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = run_factory(args)
    print(json.dumps(obj, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
