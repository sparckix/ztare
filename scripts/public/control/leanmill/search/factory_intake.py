#!/usr/bin/env python3
"""Build the entrance buffer for the LeanSearch factory mill.

The intake buffer is the WIP gate before Path A. It reads a target-site
row-context filter packet, classifies each row into a lane, and inserts
canary-ready rows into a SQLite table with provenance. No Lean is run here.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


DEFAULT_ROW_CONTEXT = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"


def _read_json(path: Path, *, retries: int = 20, stable_delay_s: float = 0.2) -> dict[str, Any]:
    """Read a possibly-live JSON packet after it is stable for one short interval."""
    last_error: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            before = path.stat()
            text = path.read_text(errors="ignore")
            after = path.stat()
            obj = json.loads(text)
            if stable_delay_s > 0:
                time.sleep(stable_delay_s)
            final = path.stat()
            if (
                before.st_size == after.st_size == final.st_size
                and before.st_mtime_ns == after.st_mtime_ns == final.st_mtime_ns
            ):
                return obj
            last_error = RuntimeError("input changed while being read")
        except (FileNotFoundError, json.JSONDecodeError, OSError, RuntimeError) as exc:
            last_error = exc
        if stable_delay_s > 0:
            time.sleep(stable_delay_s)
    raise SystemExit(f"failed to read stable JSON from {path}: {last_error}")


def _connect(path: Path) -> sqlite3.Connection:
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
        CREATE TABLE IF NOT EXISTS intake_queue (
          row_id TEXT PRIMARY KEY,
          lane_hint TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'ready',
          priority INTEGER NOT NULL DEFAULT 0,
          candidate_count INTEGER NOT NULL DEFAULT 0,
          ready_candidate_count INTEGER NOT NULL DEFAULT 0,
          source_json TEXT NOT NULL,
          inserted_at REAL NOT NULL,
          claimed_by TEXT,
          claimed_at REAL,
          done_at REAL,
          result_root TEXT
        )
        """
    )
    con.commit()
    return con


def _lane_hint(row: dict[str, Any]) -> str:
    rid = str(row.get("row_id") or "")
    names = " ".join(str(c.get("name") or "") for c in row.get("row_context_ready_candidates") or [])
    blob = f"{rid} {names}".lower()
    if "summable" in blob or "schlomilch" in blob:
        return "summability_transport"
    if "ennreal" in blob or "tsum" in blob:
        return "ennreal_tsum"
    if "mellin" in blob or "fourier" in blob:
        return "mellin_fourier_transport"
    if "isbigo" in blob or "islittleo" in blob or "tendsto_log" in blob:
        return "bigo_specialization"
    if "tendsto" in blob or "lim_" in blob or "_lim" in blob:
        return "limit_tendsto_transport"
    if "geom_mean" in blob:
        return "geom_iff_direction"
    if "rpow" in blob or "zpow" in blob:
        return "rpow_inequality_transport"
    if "convolution" in blob or "mconv" in blob or "conv_" in blob:
        return "convolution_measure"
    if "inv_sq" in blob or "sum_ioc" in blob or "add_sq_le" in blob:
        return "interval_inv_sq_sum"
    if "inner_le_lp" in blob or "lp_mul_lq" in blob:
        return "abs_transport"
    if "hasconstantspeedonwith" in blob or "lipschitz" in blob:
        return "metric_speed_transport"
    if "oscillation" in blob or "continuouswithinat" in blob or "continuousat" in blob:
        return "continuity_oscillation_transport"
    if "rayleigh" in blob or "eigenvalue" in blob or "eigenvector" in blob or "spectrum" in blob or "possemidef" in blob:
        return "spectral_rayleigh_transport"
    if "islocalextr" in blob or "multipliers" in blob or "linear_dependent" in blob:
        return "local_extrema_transport"
    if "openpartialhomeomorph" in blob:
        return "partial_homeomorph_transport"
    if "areaform" in blob or "orientation" in blob or "kahler" in blob:
        return "orientation_areaform_transport"
    return "unclassified"


def build_intake(args: argparse.Namespace) -> dict[str, Any]:
    obj = _read_json(
        Path(args.row_context_filter),
        retries=args.read_retries,
        stable_delay_s=args.read_stable_delay_s,
    )
    con = _connect(Path(args.queue_db))
    inserted = 0
    skipped = 0
    by_lane: dict[str, int] = {}
    now = time.time()
    for i, row in enumerate(obj.get("rows") or [], start=1):
        ready = int(row.get("row_context_resolved_count") or 0)
        if ready <= 0:
            skipped += 1
            continue
        lane = _lane_hint(row)
        if args.exclude_unclassified and lane == "unclassified":
            skipped += 1
            continue
        priority = 1000 - i + ready
        cur = con.execute(
            """
            INSERT OR IGNORE INTO intake_queue
              (row_id, lane_hint, priority, candidate_count, ready_candidate_count, source_json, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.get("row_id")),
                lane,
                priority,
                int(row.get("candidate_count") or 0),
                ready,
                json.dumps(row, sort_keys=True),
                now,
            ),
        )
        if cur.rowcount == 1:
            inserted += 1
            by_lane[lane] = by_lane.get(lane, 0) + 1
    con.commit()
    payload = {
        "schema": "leansearch-factory-intake-v1",
        "queue_db": args.queue_db,
        "row_context_filter": args.row_context_filter,
        "partial_input": str(args.row_context_filter).endswith(".partial.json"),
        "inserted": inserted,
        "skipped": skipped,
        "by_lane": by_lane,
        "wip_ready_total": con.execute("SELECT COUNT(*) FROM intake_queue WHERE status = 'ready'").fetchone()[0],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    tmp = Path("/tmp/leansearch_factory_intake_self_test.partial.json")
    tmp.write_text(json.dumps({"rows": []}) + "\n")
    assert _read_json(tmp, retries=1, stable_delay_s=0.0) == {"rows": []}
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "NNReal.summable_condensed_iff"}]}) == "summability_transport"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "Real.isLittleO_log_id_atTop"}]}) == "bigo_specialization"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "MeasureTheory.convolution_def"}]}) == "convolution_measure"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "ENNReal.le_tsum"}]}) == "ennreal_tsum"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "ContinuousWithinAt.oscillationWithin_eq_zero"}]}) == "continuity_oscillation_transport"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "Module.End.hasEigenvalue_iff_mem_spectrum"}]}) == "spectral_rayleigh_transport"
    assert _lane_hint({"row_id": "x", "row_context_ready_candidates": [{"name": "Orientation.areaForm_map"}]}) == "orientation_areaform_transport"
    print("leansearch_factory_intake self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-context-filter", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--queue-db", default="/tmp/rung1/leansearch_factory_intake.sqlite")
    ap.add_argument("--out")
    ap.add_argument("--exclude-unclassified", action="store_true")
    ap.add_argument("--read-retries", type=int, default=20)
    ap.add_argument("--read-stable-delay-s", type=float, default=0.2)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(build_intake(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
