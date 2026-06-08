#!/usr/bin/env python3
"""Build a matched pre-cutoff FRED companion manifest.

This is a no-call official-data audit. It takes the already frozen
post-cutoff ForecastBench FRED manifest, shifts each scoreable row's
forecast/resolution window back by a fixed number of calendar years, and
computes the historical outcome from official FRED observations.

The fixed-shift rule is deliberately simple and nonadaptive: source series are
selected only from the frozen post-cutoff manifest, and dates are transformed
before any historical observations are inspected.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_POST_MANIFEST = (
    PROGRAM
    / "cutoff_validity_v1/workspace/fred_forecastbench_manifest_2026_06_04/"
    / "fred_forecastbench_manifest_audit.json"
)
DEFAULT_OUT = PROGRAM / "cutoff_validity_v1/workspace/fred_pre_cutoff_companion_2026_06_04"
FRED_BASE = "https://api.stlouisfed.org/fred"


def bootstrap_dotenv() -> None:
    if os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY"):
        return
    if load_dotenv is None:
        return
    env_path = REPO / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: Any) -> date | None:
    if value in (None, "", "N/A"):
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def shift_year(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        # Feb 29 -> Feb 28 in non-leap target years.
        return d.replace(year=d.year - years, day=28)


def relation(date_text: str, cutoff: date) -> str:
    d = parse_date(date_text)
    if d is None:
        return "unknown"
    return "pre_cutoff" if d < cutoff else "post_cutoff"


def request_observations(series_id: str, api_key: str, start: str, end: str, timeout: int) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "sort_order": "asc",
        }
    )
    req = urllib.request.Request(
        f"{FRED_BASE}/series/observations?{params}",
        headers={"User-Agent": "ztare-gp245-fred-precutoff-companion/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status": int(response.status), "json": json.loads(body) if body else {}}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": int(exc.code), "error_body_excerpt": body[:500]}
    except Exception as exc:
        return {"ok": False, "status": None, "error_type": type(exc).__name__, "error": str(exc)[:500]}


def clean_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            value = float(row.get("value"))
        except Exception:
            continue
        out.append({"date": str(row.get("date")), "value": value})
    return out


def observation_on_or_before(rows: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    eligible = [row for row in rows if row["date"] <= target]
    return eligible[-1] if eligible else None


def build_rows(args: argparse.Namespace, api_key: str | None) -> list[dict[str, Any]]:
    post = read_json(args.post_manifest)
    cutoff = date.fromisoformat(args.panel_cutoff)
    rows: list[dict[str, Any]] = []
    for post_row in post.get("rows", []):
        if not isinstance(post_row, dict) or post_row.get("join_status") != "scoreable_verified":
            continue
        series_id = str(post_row.get("series_id"))
        post_due = parse_date(post_row.get("forecast_due_date"))
        post_resolution = parse_date(post_row.get("resolution_date"))
        base = {
            "schema": "gp245-fred-pre-cutoff-companion-row-v1",
            "series_id": series_id,
            "source": "fred",
            "question_template": post_row.get("question"),
            "url": post_row.get("url"),
            "post_forecast_due_date": post_row.get("forecast_due_date"),
            "post_resolution_date": post_row.get("resolution_date"),
            "post_y_known": post_row.get("computed_y_known_increase"),
            "post_contract_id": f"forecastbench_fred_20260412_{series_id}",
            "fixed_date_rule": f"subtract_{args.year_shift}_calendar_year_from_post_due_and_resolution_dates",
            "nonadaptive_source_selection": (
                "series set fixed by scoreable FRED ForecastBench post-cutoff manifest before "
                "historical observations are inspected"
            ),
        }
        if post_due is None or post_resolution is None:
            rows.append({**base, "join_status": "missing_post_due_or_resolution_date"})
            continue
        pre_due = shift_year(post_due, args.year_shift)
        pre_resolution = shift_year(post_resolution, args.year_shift)
        pre_due_text = pre_due.isoformat()
        pre_resolution_text = pre_resolution.isoformat()
        base.update(
            {
                "forecast_due_date": pre_due_text,
                "resolution_date": pre_resolution_text,
                "cutoff_relation": relation(pre_resolution_text, cutoff),
            }
        )
        if not api_key:
            rows.append({**base, "api_ok": False, "join_status": "missing_fred_api_key"})
            continue
        start = date(max(1900, pre_due.year - 1), 1, 1).isoformat()
        response = request_observations(series_id, api_key, start, pre_resolution_text, args.timeout)
        obs = clean_observations(response.get("json") or {}) if response.get("ok") else []
        due_obs = observation_on_or_before(obs, pre_due_text)
        resolution_obs = observation_on_or_before(obs, pre_resolution_text)
        y_known = None
        if due_obs and resolution_obs:
            y_known = 1 if float(resolution_obs["value"]) > float(due_obs["value"]) else 0
        rows.append(
            {
                **base,
                "api_ok": bool(response.get("ok")),
                "http_status": response.get("status"),
                "error_type": response.get("error_type"),
                "error_body_excerpt": response.get("error_body_excerpt"),
                "observations_count": len(obs),
                "due_observation": due_obs,
                "resolution_observation": resolution_obs,
                "computed_y_known_increase": y_known,
                "join_status": (
                    "scoreable_verified"
                    if y_known is not None
                    else "missing_due_or_resolution_observation"
                    if response.get("ok")
                    else "fred_api_failed"
                ),
            }
        )
    return rows


def contract_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in report["rows"]:
        if row.get("join_status") != "scoreable_verified":
            continue
        y_known = row.get("computed_y_known_increase")
        if y_known is None:
            continue
        rows.append(
            {
                "schema": "gp245-fred-pre-cutoff-companion-contract-row-v1",
                "contract_id": f"forecastbench_fred_pre{str(row.get('forecast_due_date')).replace('-', '')}_{row['series_id']}",
                "question": row.get("question_template"),
                "source": "fred",
                "task_type": "forecastbench_official_timeseries_fred_pre_cutoff_companion",
                "horizon": f"forecast_due={row.get('forecast_due_date')};resolution={row.get('resolution_date')}",
                "y_known": int(y_known),
                "post_training_cutoff": row.get("cutoff_relation") == "post_cutoff",
                "external_market_open": "N/A",
                "resolution_source_url": row.get("url"),
                "y_known_provenance": (
                    "official_fred_observation_comparison_fixed_pre_cutoff_companion:"
                    f"due={row.get('forecast_due_date')};resolution={row.get('resolution_date')};"
                    f"source_series={row.get('series_id')};date_rule={row.get('fixed_date_rule')}"
                ),
                "series_id": row.get("series_id"),
                "forecast_due_date": row.get("forecast_due_date"),
                "resolution_date": row.get("resolution_date"),
                "due_observation": row.get("due_observation"),
                "resolution_observation": row.get("resolution_observation"),
                "paired_post_contract_id": row.get("post_contract_id"),
            }
        )
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    api_key = os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY")
    rows = build_rows(args, api_key)
    scoreable = [row for row in rows if row.get("join_status") == "scoreable_verified"]
    contract_ready = contract_rows({"rows": rows})
    status_counts = Counter(str(row.get("join_status")) for row in rows)
    cutoff_counts = Counter(str(row.get("cutoff_relation")) for row in rows)
    y_counts = Counter(str(row.get("computed_y_known_increase")) for row in scoreable)
    all_pre = bool(scoreable) and {row.get("cutoff_relation") for row in scoreable} <= {"pre_cutoff"}
    if scoreable and all_pre and len(scoreable) == len(rows):
        verdict = "pre_cutoff_companion_ready_no_calls"
    elif scoreable and all_pre:
        verdict = "pre_cutoff_companion_partial_no_calls"
    elif scoreable:
        verdict = "pre_cutoff_companion_has_cutoff_or_missingness_issue"
    else:
        verdict = "pre_cutoff_companion_not_scoreable"
    return {
        "schema": "gp245-fred-pre-cutoff-companion-manifest-v1",
        "date": datetime.now(timezone.utc).isoformat(),
        "credential_present_after_dotenv": bool(api_key),
        "post_manifest": str(args.post_manifest.relative_to(REPO)),
        "panel_cutoff": args.panel_cutoff,
        "year_shift": args.year_shift,
        "row_count": len(rows),
        "scoreable_verified_rows": len(scoreable),
        "scoreable_contract_rows": len(contract_ready),
        "join_status_counts": dict(sorted(status_counts.items())),
        "cutoff_relation_counts": dict(sorted(cutoff_counts.items())),
        "scoreable_outcome_counts": dict(sorted(y_counts.items())),
        "verdict": verdict,
        "non_claims": [
            "not a model-call result",
            "not an external human or market baseline",
            "not an original ForecastBench benchmark row because the historical companion dates are researcher-constructed",
            "not a Law 3 pre/post replication until paired model calls are run under a frozen dispatch packet",
        ],
        "next_gate": (
            "If accepted, ingest only after preserving this manifest and then run a paired "
            "pre/post FRED packet over the same series and fixed date rule."
        ),
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# FRED Pre-Cutoff Companion Manifest",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Credential present after dotenv: `{report['credential_present_after_dotenv']}`",
        f"- Post manifest: `{report['post_manifest']}`",
        f"- Year shift: `{report['year_shift']}`",
        f"- Row count: `{report['row_count']}`",
        f"- Scoreable verified rows: `{report['scoreable_verified_rows']}`",
        f"- Scoreable contract rows emitted: `{report['scoreable_contract_rows']}`",
        f"- Join status counts: `{report['join_status_counts']}`",
        f"- Cutoff relation counts: `{report['cutoff_relation_counts']}`",
        f"- Scoreable outcome counts: `{report['scoreable_outcome_counts']}`",
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
            "## Next Gate",
            "",
            report["next_gate"],
            "",
            "## Manifest Rows",
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
    parser.add_argument("--post-manifest", type=Path, default=DEFAULT_POST_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff", default="2025-10-01")
    parser.add_argument("--year-shift", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    report = build(args)
    corpus_rows = contract_rows(report)
    report["scoreable_contract_rows"] = len(corpus_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_pre_cutoff_companion_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "fred_pre_cutoff_companion_manifest.md").write_text(render_md(report), encoding="utf-8")
    with (args.out_dir / "fred_pre_cutoff_companion_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.out_dir / "fred_pre_cutoff_companion_contract_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in corpus_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "row_count",
                    "scoreable_verified_rows",
                    "scoreable_contract_rows",
                    "join_status_counts",
                    "cutoff_relation_counts",
                    "scoreable_outcome_counts",
                    "verdict",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
