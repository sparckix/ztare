#!/usr/bin/env python3
"""Build a no-call FRED ForecastBench manifest/readiness audit.

The audit verifies whether ForecastBench FRED rows can be scored mechanically
from official FRED observations using the frozen question bundle and bundled
resolution dates. It does not mutate the DB and does not call any LLM.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_QUESTIONS = WORKSPACE / "fb_2026_04_12_questions.json"
DEFAULT_RESOLUTIONS = WORKSPACE / "fb_2026_04_12_resolutions.json"
DEFAULT_OUT = PROGRAM / "cutoff_validity_v1/workspace/fred_forecastbench_manifest_2026_06_04"
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


def parse_dt(value: Any) -> datetime | None:
    if value in (None, "", "N/A"):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def relation(date_text: Any, cutoff: datetime) -> str:
    dt = parse_dt(date_text)
    if dt is None:
        return "unknown"
    cutoff_cmp = cutoff
    if dt.tzinfo is not None and cutoff_cmp.tzinfo is None:
        cutoff_cmp = cutoff_cmp.replace(tzinfo=dt.tzinfo)
    return "pre_cutoff" if dt < cutoff_cmp else "post_cutoff"


def length_band(question: str) -> str:
    n = len(question)
    if n < 80:
        return "<80"
    if n < 160:
        return "80-159"
    if n < 280:
        return "160-279"
    return "280+"


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
        headers={"User-Agent": "ztare-gp245-fred-forecastbench-manifest/1.0"},
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
    questions = [row for row in read_json(args.questions).get("questions", []) if isinstance(row, dict)]
    res_obj = read_json(args.resolutions)
    forecast_due_date = str(res_obj.get("forecast_due_date") or "")
    res_by_key = {
        (str(row.get("source")), str(row.get("id"))): row
        for row in res_obj.get("resolutions", [])
        if isinstance(row, dict)
    }
    cutoff = datetime.fromisoformat(args.panel_cutoff)
    rows = []
    for q in questions:
        if q.get("source") != "fred":
            continue
        series_id = str(q.get("id"))
        res = res_by_key.get(("fred", series_id), {})
        resolution_date = str(res.get("resolution_date") or "")
        base = {
            "schema": "gp245-fred-forecastbench-manifest-row-v1",
            "series_id": series_id,
            "source": "fred",
            "question": q.get("question"),
            "url": q.get("url"),
            "forecast_due_date": forecast_due_date,
            "resolution_date": resolution_date,
            "cutoff_relation": relation(resolution_date, cutoff),
            "question_length_band": length_band(str(q.get("question") or "")),
            "bundle_resolved": bool(res.get("resolved")),
            "bundle_resolved_to": res.get("resolved_to"),
            "nonadaptive_source_selection": "source fixed by ForecastBench question bundle before this audit",
        }
        if not api_key:
            rows.append({**base, "api_ok": False, "join_status": "missing_fred_api_key"})
            continue
        if not forecast_due_date or not resolution_date:
            rows.append({**base, "api_ok": False, "join_status": "missing_due_or_resolution_date"})
            continue
        start_year = max(1900, int(forecast_due_date[:4]) - 1)
        response = request_observations(series_id, api_key, f"{start_year}-01-01", resolution_date, args.timeout)
        obs = clean_observations(response.get("json") or {}) if response.get("ok") else []
        due_obs = observation_on_or_before(obs, forecast_due_date)
        res_obs = observation_on_or_before(obs, resolution_date)
        computed_y = None
        if due_obs and res_obs:
            computed_y = 1 if float(res_obs["value"]) > float(due_obs["value"]) else 0
        rows.append(
            {
                **base,
                "api_ok": bool(response.get("ok")),
                "http_status": response.get("status"),
                "error_type": response.get("error_type"),
                "error_body_excerpt": response.get("error_body_excerpt"),
                "observations_count": len(obs),
                "due_observation": due_obs,
                "resolution_observation": res_obs,
                "computed_y_known_increase": computed_y,
                "computed_matches_bundle": (
                    computed_y == int(float(res.get("resolved_to")))
                    if computed_y is not None and res.get("resolved_to") is not None
                    else None
                ),
                "join_status": (
                    "scoreable_verified"
                    if computed_y is not None
                    else "missing_due_or_resolution_observation"
                    if response.get("ok")
                    else "fred_api_failed"
                ),
            }
        )
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    api_key = os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY")
    rows = build_rows(args, api_key)
    status_counts = Counter(str(row.get("join_status")) for row in rows)
    relation_counts = Counter(str(row.get("cutoff_relation")) for row in rows)
    scoreable = [row for row in rows if row.get("join_status") == "scoreable_verified"]
    matchable = [row for row in scoreable if row.get("computed_matches_bundle") is True]
    mismatch = [row for row in scoreable if row.get("computed_matches_bundle") is False]
    scoreable_relations = {str(row.get("cutoff_relation")) for row in scoreable}
    if scoreable and not mismatch and scoreable_relations <= {"post_cutoff"}:
        verdict = "fred_rows_scoreable_but_post_cutoff_only"
    elif scoreable and not mismatch:
        verdict = "fred_rows_scoreable_with_mixed_cutoff_relations"
    elif mismatch:
        verdict = "fred_rows_need_resolution_rule_review"
    else:
        verdict = "fred_rows_not_scoreable_from_current_probe"
    return {
        "schema": "gp245-fred-forecastbench-manifest-v1",
        "date": datetime.now(timezone.utc).isoformat(),
        "credential_present_after_dotenv": bool(api_key),
        "questions_path": str(args.questions.relative_to(REPO)),
        "resolutions_path": str(args.resolutions.relative_to(REPO)),
        "panel_cutoff": args.panel_cutoff,
        "row_count": len(rows),
        "scoreable_verified_rows": len(scoreable),
        "computed_bundle_match_rows": len(matchable),
        "computed_bundle_mismatch_rows": len(mismatch),
        "scoreable_cutoff_relation_counts": dict(
            sorted(Counter(str(row.get("cutoff_relation")) for row in scoreable).items())
        ),
        "join_status_counts": dict(sorted(status_counts.items())),
        "cutoff_relation_counts": dict(sorted(relation_counts.items())),
        "verdict": verdict,
        "non_claims": [
            "not a pre/post Law 3 replication because the audited rows are post-cutoff by resolution date",
            "not a human/market equal-information baseline",
            "not a model-call result",
            "not a substitute for the Metaculus target cells",
        ],
        "next_gate": (
            "Use these rows only as post-cutoff official-data supply unless a "
            "separately frozen pre-cutoff official-data side is acquired with the "
            "same due/resolution observation rule."
        ),
        "rows": rows,
    }


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
                "schema": "gp245-fred-forecastbench-contract-row-v1",
                "contract_id": f"forecastbench_fred_20260412_{row['series_id']}",
                "question": row.get("question"),
                "source": "fred",
                "task_type": "forecastbench_official_timeseries_fred",
                "horizon": f"forecast_due={row.get('forecast_due_date')};resolution={row.get('resolution_date')}",
                "y_known": int(y_known),
                "post_training_cutoff": row.get("cutoff_relation") == "post_cutoff",
                "external_market_open": "N/A",
                "resolution_source_url": row.get("url"),
                "y_known_provenance": (
                    "official_fred_observation_comparison:"
                    f"due={row.get('forecast_due_date')};resolution={row.get('resolution_date')}"
                ),
                "series_id": row.get("series_id"),
                "forecast_due_date": row.get("forecast_due_date"),
                "resolution_date": row.get("resolution_date"),
                "due_observation": row.get("due_observation"),
                "resolution_observation": row.get("resolution_observation"),
                "bundle_resolved_to": row.get("bundle_resolved_to"),
                "computed_matches_bundle": row.get("computed_matches_bundle"),
            }
        )
    return rows


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# FRED ForecastBench Manifest Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Credential present after dotenv: `{report['credential_present_after_dotenv']}`",
        f"- Row count: `{report['row_count']}`",
        f"- Scoreable verified rows: `{report['scoreable_verified_rows']}`",
        f"- Bundle-match rows: `{report['computed_bundle_match_rows']}`",
        f"- Bundle-mismatch rows: `{report['computed_bundle_mismatch_rows']}`",
        f"- Scoreable contract rows emitted: `{report.get('scoreable_contract_rows', 'NA')}`",
        f"- Join status counts: `{report['join_status_counts']}`",
        f"- Cutoff relation counts: `{report['cutoff_relation_counts']}`",
        f"- Scoreable cutoff relation counts: `{report['scoreable_cutoff_relation_counts']}`",
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
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff", default="2025-10-01")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    report = build(args)
    corpus_rows = contract_rows(report)
    report["scoreable_contract_rows"] = len(corpus_rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_forecastbench_manifest_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "fred_forecastbench_manifest_audit.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    with (args.out_dir / "fred_forecastbench_manifest_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.out_dir / "fred_forecastbench_contract_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in corpus_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {key: report[key] for key in (
                "row_count",
                "scoreable_verified_rows",
                "computed_bundle_match_rows",
                "computed_bundle_mismatch_rows",
                "join_status_counts",
                "cutoff_relation_counts",
                "verdict",
            )},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
