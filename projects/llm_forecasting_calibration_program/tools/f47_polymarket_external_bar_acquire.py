#!/usr/bin/env python3
"""Acquire F47 Polymarket external bars from DB freezes or public CLOB history.

No model calls. No DB mutation.

The F47 external-bar manifest contains two Polymarket cases:
- reviewed Polymarket rows already carrying a DB raw_json.freeze_datetime_value,
- ForecastBench Polymarket rows whose public Gamma/CLOB history must be fetched.

For short-horizon markets, a day-before-resolution bar often predates market
creation, so this tool defaults to one hour before the Gamma close/end time.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
TOOL_DIR = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from cutoff_polymarket_pre_cutoff_acquire import (  # noqa: E402
    CLOB_BASE,
    GAMMA_BASE,
    as_number,
    as_probability,
    parse_dt,
    parse_json_array,
    probability_band,
    read_json_url,
    read_jsonl,
    yes_index,
)
from cutoff_polymarket_post_price_probe import final_yes_outcome  # noqa: E402


WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_INPUT = WORKSPACE / "f47_external_bar_polymarket_missing_2026_06_03.jsonl"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_DIR = WORKSPACE / "f47_external_bar_polymarket_acquisition_2026_06_03"


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def slug_from_url(url: Any) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    parsed = urllib.parse.urlparse(text)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return ""
    return parts[-1]


def gamma_market_by_slug(slug: str) -> tuple[dict[str, Any] | None, str]:
    if not slug:
        return None, "missing_slug"
    direct = f"{GAMMA_BASE}/markets/slug/{urllib.parse.quote(slug)}"
    try:
        data = read_json_url(direct)
        if isinstance(data, dict) and str(data.get("slug") or "") == slug:
            return data, "gamma_market_slug_direct"
    except Exception:
        pass
    params = urllib.parse.urlencode({"slug": slug, "limit": "5"})
    try:
        data = read_json_url(f"{GAMMA_BASE}/markets?{params}")
    except Exception as exc:
        return None, f"gamma_fetch_failed:{type(exc).__name__}"
    if not isinstance(data, list) or not data:
        return None, "gamma_no_market"
    for row in data:
        if isinstance(row, dict) and str(row.get("slug") or "") == slug:
            return row, "gamma_slug_exact"
    for row in data:
        if isinstance(row, dict):
            return row, "gamma_first_result_slug_mismatch"
    return None, "gamma_no_object_market"


def history_price_at_any_fidelity(
    token_id: str,
    target: datetime,
    *,
    fidelities: list[int],
) -> tuple[float | None, int | None, str, int | None]:
    target_ts = int(target.timestamp())
    saw_empty = False
    failures: list[str] = []
    for fidelity in fidelities:
        params = urllib.parse.urlencode(
            {
                "market": token_id,
                "interval": "max",
                "fidelity": str(fidelity),
            }
        )
        try:
            obj = read_json_url(f"{CLOB_BASE}/prices-history?{params}")
        except Exception as exc:
            failures.append(f"fidelity_{fidelity}:{type(exc).__name__}")
            continue
        history = obj.get("history", []) if isinstance(obj, dict) else []
        if not history:
            saw_empty = True
            continue
        eligible = [
            item
            for item in history
            if isinstance(item, dict)
            and isinstance(item.get("t"), int)
            and item.get("t") <= target_ts
            and as_probability(item.get("p")) is not None
        ]
        if not eligible:
            failures.append(f"fidelity_{fidelity}:no_history_before_target")
            continue
        item = max(eligible, key=lambda row: int(row["t"]))
        return (
            float(item["p"]),
            int(item["t"]),
            "history_nearest_at_or_before_target",
            fidelity,
        )
    if failures:
        return None, None, ";".join(failures), None
    if saw_empty:
        return None, None, "history_empty", None
    return None, None, "history_unavailable", None


def load_contract_meta(db: Path, ids: set[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in ids)
    rows = con.execute(
        f"""
        SELECT contract_id, question, y_known, raw_json, resolution_source_url
        FROM contracts
        WHERE contract_id IN ({placeholders})
        """,
        tuple(sorted(ids)),
    ).fetchall()
    con.close()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw: dict[str, Any] = {}
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except json.JSONDecodeError:
            raw = {}
        out[str(row["contract_id"])] = {
            "contract_id": str(row["contract_id"]),
            "question": row["question"],
            "y_known": int(row["y_known"]) if row["y_known"] in (0, 1) else None,
            "raw": raw,
            "resolution_source_url": row["resolution_source_url"],
        }
    return out


def stored_freeze_row(row: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any] | None:
    raw = meta.get("raw") or {}
    p = as_probability(raw.get("freeze_datetime_value"))
    if p is None:
        return None
    y = meta.get("y_known")
    return {
        "schema": "f47-polymarket-external-bar-row-v1",
        "contract_id": row.get("contract_id"),
        "question": row.get("question") or meta.get("question"),
        "source": "polymarket",
        "source_url": row.get("source_url") or meta.get("resolution_source_url") or raw.get("polymarket_url"),
        "y_known": y,
        "join_status": "joined",
        "bar_source": "db_raw_json_freeze_datetime_value",
        "market_p": p,
        "freeze_datetime": raw.get("freeze_datetime"),
        "freeze_datetime_value": p,
        "freeze_value_band": probability_band(p),
        "history_status": raw.get("history_status"),
        "freeze_history_timestamp": raw.get("freeze_history_timestamp"),
        "gamma_final_yes_matches_y_known": None,
        "packets": row.get("packets") or [],
    }


def fetched_bar_row(
    row: dict[str, Any],
    meta: dict[str, Any],
    *,
    freeze_hours_before_resolution: float,
    history_fidelities: list[int],
) -> dict[str, Any]:
    url = row.get("source_url") or meta.get("resolution_source_url")
    slug = slug_from_url(url)
    market, gamma_status = gamma_market_by_slug(slug)
    base = {
        "schema": "f47-polymarket-external-bar-row-v1",
        "contract_id": row.get("contract_id"),
        "question": row.get("question") or meta.get("question"),
        "source": "polymarket",
        "source_url": url,
        "slug": slug,
        "y_known": meta.get("y_known"),
        "gamma_status": gamma_status,
        "packets": row.get("packets") or [],
    }
    if market is None:
        return {**base, "join_status": gamma_status}
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    token_ids = parse_json_array(market.get("clobTokenIds"))
    if idx is None or idx >= len(token_ids):
        return {**base, "join_status": "missing_yes_token", "outcomes": outcomes}
    target_base = parse_dt(market.get("closedTime") or market.get("umaEndDate") or market.get("endDate"))
    if target_base is None:
        target_base = parse_dt(row.get("resolve_date"))
    if target_base is None:
        return {**base, "join_status": "missing_resolution_datetime", "outcomes": outcomes}
    freeze_dt = target_base - timedelta(hours=freeze_hours_before_resolution)
    p_yes, history_ts, history_status, history_fidelity = history_price_at_any_fidelity(
        str(token_ids[idx]),
        freeze_dt,
        fidelities=history_fidelities,
    )
    final_yes = final_yes_outcome(market, idx)
    return {
        **base,
        "join_status": "joined" if p_yes is not None else history_status,
        "bar_source": "polymarket_gamma_clob_history",
        "outcomes": outcomes,
        "yes_token_id": str(token_ids[idx]),
        "market_p": p_yes,
        "freeze_datetime": freeze_dt.isoformat(),
        "freeze_hours_before_resolution": freeze_hours_before_resolution,
        "freeze_datetime_value": p_yes,
        "freeze_history_timestamp": history_ts,
        "freeze_value_band": probability_band(p_yes),
        "history_status": history_status,
        "history_fidelity_minutes": history_fidelity,
        "gamma_market_id": market.get("id"),
        "gamma_question": market.get("question"),
        "gamma_slug": market.get("slug"),
        "gamma_closed_time": market.get("closedTime"),
        "gamma_end_date": market.get("endDate"),
        "gamma_volume_num": as_number(market.get("volumeNum")),
        "gamma_final_yes": final_yes,
        "gamma_final_yes_matches_y_known": (
            final_yes == int(meta["y_known"])
            if final_yes is not None and meta.get("y_known") in (0, 1)
            else None
        ),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.input)
    meta = load_contract_meta(args.db, {str(row.get("contract_id")) for row in rows})
    history_fidelities = [
        int(item)
        for item in str(args.history_fidelities).split(",")
        if item.strip()
    ]
    acquired: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if i and args.sleep_ms:
            time.sleep(args.sleep_ms / 1000)
        m = meta.get(str(row.get("contract_id"))) or {}
        stored = stored_freeze_row(row, m)
        if stored is not None:
            acquired.append(stored)
            continue
        acquired.append(
            fetched_bar_row(
                row,
                m,
                freeze_hours_before_resolution=args.freeze_hours_before_resolution,
                history_fidelities=history_fidelities,
            )
        )
    joined = [row for row in acquired if row.get("join_status") == "joined" and row.get("market_p") is not None]
    return {
        "schema": "f47-polymarket-external-bar-acquisition-v1",
        "input": repo_rel(args.input),
        "freeze_hours_before_resolution": args.freeze_hours_before_resolution,
        "history_fidelities": history_fidelities,
        "rows_considered": len(rows),
        "joined_rows": len(joined),
        "join_status_counts": dict(Counter(str(row.get("join_status")) for row in acquired)),
        "bar_source_counts": dict(Counter(str(row.get("bar_source")) for row in joined)),
        "history_status_counts": dict(Counter(str(row.get("history_status")) for row in acquired if row.get("history_status"))),
        "freeze_value_band_counts": dict(Counter(str(row.get("freeze_value_band")) for row in joined)),
        "final_yes_match_counts": dict(Counter(str(row.get("gamma_final_yes_matches_y_known")) for row in acquired)),
        "interpretation": (
            "F47 Polymarket external bars are available for all considered rows."
            if len(joined) == len(rows) and rows
            else "F47 Polymarket external-bar acquisition remains incomplete."
        ),
        "rows": acquired,
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "f47_polymarket_external_bar_acquisition.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "f47_polymarket_external_bar_acquisition_rows.jsonl").open("w", encoding="utf-8") as f:
        for row in report["rows"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# F47 Polymarket External-Bar Acquisition",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Rows considered: `{report['rows_considered']}`",
        f"- Joined rows: `{report['joined_rows']}`",
        f"- Join status counts: `{report['join_status_counts']}`",
        f"- Bar source counts: `{report['bar_source_counts']}`",
        f"- History status counts: `{report['history_status_counts']}`",
        f"- Freeze value bands: `{report['freeze_value_band_counts']}`",
        f"- Final YES match counts: `{report['final_yes_match_counts']}`",
        "",
        report["interpretation"],
        "",
    ]
    (out_dir / "f47_polymarket_external_bar_acquisition.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--freeze-hours-before-resolution", type=float, default=1.0)
    parser.add_argument("--history-fidelities", default="1440,60,15,5,1")
    parser.add_argument("--sleep-ms", type=int, default=100)
    args = parser.parse_args()
    report = build(args)
    write_outputs(report, args.out_dir)
    print(
        json.dumps(
            {
                "rows_considered": report["rows_considered"],
                "joined_rows": report["joined_rows"],
                "join_status_counts": report["join_status_counts"],
                "bar_source_counts": report["bar_source_counts"],
                "history_status_counts": report["history_status_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
