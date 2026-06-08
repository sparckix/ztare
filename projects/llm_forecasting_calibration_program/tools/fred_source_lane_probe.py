#!/usr/bin/env python3
"""Probe whether FRED can support a separate source-valid forecasting lane.

This is not a Metaculus replacement and does not mutate the DB. It verifies
whether the local FRED credential can retrieve dated observations for existing
FRED contracts already present in the calibration DB, so the program can decide
whether a separate frozen dataset-source replication is feasible.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "cutoff_validity_v1/workspace/fred_source_lane_probe_2026_06_04"
FRED_BASE = "https://api.stlouisfed.org/fred"


def bootstrap_dotenv() -> None:
    if os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY"):
        return
    if load_dotenv is None:
        return
    env_path = REPO / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def parse_dt(value: Any) -> datetime | None:
    if value in (None, "", "N/A"):
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def date_text(value: datetime | None) -> str | None:
    return value.date().isoformat() if value else None


def series_id_from_row(contract_id: str, raw: dict[str, Any]) -> str:
    artifact_paths = raw.get("artifact_paths")
    if isinstance(artifact_paths, list):
        for item in artifact_paths:
            parsed = urllib.parse.urlparse(str(item))
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[-2] == "series" and parts[-1]:
                return parts[-1]
    return contract_id.replace("forecastbench_fred_", "").replace("fb_external_fred_", "")


def read_contracts(db: Path, limit: int) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = []
        for row in con.execute(
            """
            SELECT contract_id, question, horizon, y_known, post_training_cutoff,
                   raw_json
            FROM contracts
            WHERE source = 'fred'
            ORDER BY contract_id
            LIMIT ?
            """,
            (limit,),
        ):
            raw: dict[str, Any] = {}
            try:
                raw = json.loads(row["raw_json"] or "{}")
            except Exception:
                raw = {}
            series_id = series_id_from_row(str(row["contract_id"] or ""), raw)
            freeze_dt = parse_dt(raw.get("external_freeze_datetime"))
            rows.append(
                {
                    "contract_id": row["contract_id"],
                    "series_id": series_id,
                    "question": row["question"],
                    "horizon": row["horizon"],
                    "y_known_present": row["y_known"] is not None,
                    "post_training_cutoff": row["post_training_cutoff"],
                    "freeze_datetime": raw.get("external_freeze_datetime"),
                    "freeze_date": date_text(freeze_dt),
                    "artifact_paths": raw.get("artifact_paths") or [],
                }
            )
        return rows
    finally:
        con.close()


def request_json(path: str, params: dict[str, str], timeout: int) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{FRED_BASE}/{path}?{query}",
        headers={"User-Agent": "ztare-gp245-fred-source-lane-probe/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {
                "ok": True,
                "status": int(response.status),
                "json": json.loads(body) if body else {},
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": int(exc.code),
            "error_body_excerpt": body[:500],
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }


def usable_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("value")
        if value in (None, "", "."):
            continue
        try:
            float(value)
        except Exception:
            continue
        out.append({"date": row.get("date"), "value_present": True})
    return out


def probe_contract(row: dict[str, Any], api_key: str, timeout: int) -> dict[str, Any]:
    freeze_dt = parse_dt(row.get("freeze_datetime"))
    start = "2026-03-01"
    end = datetime.now(timezone.utc).date().isoformat()
    if freeze_dt is not None:
        start = f"{max(1900, freeze_dt.year - 1):04d}-01-01"
    response = request_json(
        "series/observations",
        {
            "series_id": str(row["series_id"]),
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "sort_order": "asc",
        },
        timeout,
    )
    observations = usable_observations(response.get("json") or {}) if response.get("ok") else []
    freeze_date = row.get("freeze_date")
    before_or_at_freeze = [
        obs for obs in observations if freeze_date and str(obs.get("date")) <= str(freeze_date)
    ]
    after_freeze = [
        obs for obs in observations if freeze_date and str(obs.get("date")) > str(freeze_date)
    ]
    return {
        **row,
        "api_ok": bool(response.get("ok")),
        "http_status": response.get("status"),
        "error_type": response.get("error_type"),
        "error_body_excerpt": response.get("error_body_excerpt"),
        "observations_count": len(observations),
        "has_observation_on_or_before_freeze": bool(before_or_at_freeze),
        "has_observation_after_freeze": bool(after_freeze),
        "latest_observation_date": observations[-1]["date"] if observations else None,
        "first_observation_date": observations[0]["date"] if observations else None,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    api_key = os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY")
    contracts = read_contracts(args.db, args.limit)
    if not api_key:
        rows = [{**row, "api_ok": False, "error_type": "missing_fred_api_key"} for row in contracts]
    else:
        rows = [probe_contract(row, api_key, args.timeout) for row in contracts]
    api_ok = sum(1 for row in rows if row.get("api_ok"))
    before = sum(1 for row in rows if row.get("has_observation_on_or_before_freeze"))
    after = sum(1 for row in rows if row.get("has_observation_after_freeze"))
    if api_ok and before and after:
        verdict = "fred_api_can_support_dataset_source_lane_probe_sample"
    elif api_ok:
        verdict = "fred_api_reachable_but_sample_incomplete_for_frozen_lane"
    elif api_key:
        verdict = "fred_api_key_present_but_probe_failed"
    else:
        verdict = "missing_fred_api_key_after_dotenv"
    return {
        "schema": "gp245-fred-source-lane-probe-v1",
        "date": datetime.now(timezone.utc).isoformat(),
        "credential_present_after_dotenv": bool(api_key),
        "db_contracts_sampled": len(contracts),
        "api_ok_rows": api_ok,
        "rows_with_observation_on_or_before_freeze": before,
        "rows_with_observation_after_freeze": after,
        "verdict": verdict,
        "non_claims": [
            "not a Metaculus target-cell substitute",
            "not a human/market equal-information baseline",
            "not a model-call result",
            "not evidence that FRED rows are already source-balanced or powered",
        ],
        "next_design_gate": (
            "Open a separate FRED/yfinance dataset-source lane only with a frozen "
            "manifest, external y_known receipts, strict resolve dates, and matched "
            "pre/post source/topic/length/horizon cells."
        ),
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# FRED Source-Lane Probe",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Credential present after dotenv: `{report['credential_present_after_dotenv']}`",
        f"- DB contracts sampled: `{report['db_contracts_sampled']}`",
        f"- API-ok rows: `{report['api_ok_rows']}`",
        f"- Rows with observation on/before freeze: `{report['rows_with_observation_on_or_before_freeze']}`",
        f"- Rows with observation after freeze: `{report['rows_with_observation_after_freeze']}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Non-Claims",
        "",
    ]
    for item in report["non_claims"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next Design Gate",
            "",
            report["next_design_gate"],
            "",
            "## Row Probe Summary",
            "",
            "```json",
            json.dumps(report["rows"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_source_lane_probe.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "fred_source_lane_probe.md").write_text(render_md(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "credential_present_after_dotenv",
        "db_contracts_sampled",
        "api_ok_rows",
        "rows_with_observation_on_or_before_freeze",
        "rows_with_observation_after_freeze",
        "verdict",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
