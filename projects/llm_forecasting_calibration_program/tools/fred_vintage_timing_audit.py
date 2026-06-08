#!/usr/bin/env python3
"""Audit FRED current-value labels against real-time/vintage observations.

This no-call audit checks whether the 2026-06-04 FRED pair answer key is
stable when values are fetched with FRED real-time parameters. It does not
mutate the DB and does not call any LLM.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_ANSWER = WORKSPACE / "fred_cutoff_pair_packet_2026_06_04/fred_cutoff_pair_answer_key.jsonl"
DEFAULT_OUT = WORKSPACE / "fred_vintage_timing_audit_2026_06_04"
FRED_BASE = "https://api.stlouisfed.org/fred"


def bootstrap_dotenv() -> None:
    if os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY"):
        return
    if load_dotenv is None:
        return
    env_path = REPO / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def parse_date(value: Any) -> date | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def numeric(value: Any) -> float | None:
    if value in (None, "", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def request_observations_asof(
    *,
    series_id: str,
    api_key: str,
    start: str,
    end: str,
    asof: str,
    timeout: int,
) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "realtime_start": asof,
            "realtime_end": asof,
            "sort_order": "asc",
        }
    )
    req = urllib.request.Request(
        f"{FRED_BASE}/series/observations?{params}",
        headers={"User-Agent": "ztare-gp245-fred-vintage-timing-audit/1.0"},
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
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = numeric(row.get("value"))
        if value is None:
            continue
        out.append(
            {
                "date": str(row.get("date")),
                "value": value,
                "realtime_start": row.get("realtime_start"),
                "realtime_end": row.get("realtime_end"),
            }
        )
    return out


def observation_on_or_before(rows: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    eligible = [row for row in rows if str(row.get("date")) <= target]
    return eligible[-1] if eligible else None


def differs(a: float | None, b: float | None, tolerance: float) -> bool | None:
    if a is None or b is None:
        return None
    return abs(a - b) > tolerance


def binary_increase(due: dict[str, Any] | None, res: dict[str, Any] | None) -> int | None:
    due_value = numeric(due.get("value") if due else None)
    res_value = numeric(res.get("value") if res else None)
    if due_value is None or res_value is None:
        return None
    return 1 if res_value > due_value else 0


def audit_row(row: dict[str, Any], *, api_key: str, timeout: int, tolerance: float) -> dict[str, Any]:
    series_id = str(row.get("series_id") or "")
    due_date = parse_date(row.get("forecast_due_date"))
    resolution_date = parse_date(row.get("resolution_date"))
    current_due = row.get("due_observation") if isinstance(row.get("due_observation"), dict) else None
    current_res = row.get("resolution_observation") if isinstance(row.get("resolution_observation"), dict) else None
    current_y = int(row["y_known"]) if row.get("y_known") in (0, 1) else None
    base = {
        "contract_id": row.get("contract_id"),
        "series_id": series_id,
        "cutoff_relation": row.get("cutoff_relation"),
        "forecast_due_date": row.get("forecast_due_date"),
        "resolution_date": row.get("resolution_date"),
        "current_due_observation": current_due,
        "current_resolution_observation": current_res,
        "current_y_known": current_y,
    }
    if not (series_id and due_date and resolution_date):
        return {**base, "join_status": "missing_series_or_dates"}
    start = date(max(1900, due_date.year - 1), 1, 1).isoformat()
    end = resolution_date.isoformat()
    due_resp = request_observations_asof(
        series_id=series_id,
        api_key=api_key,
        start=start,
        end=end,
        asof=due_date.isoformat(),
        timeout=timeout,
    )
    if getattr(audit_row, "_throttle_seconds", 0.0):
        time.sleep(float(getattr(audit_row, "_throttle_seconds")))
    res_resp = request_observations_asof(
        series_id=series_id,
        api_key=api_key,
        start=start,
        end=end,
        asof=resolution_date.isoformat(),
        timeout=timeout,
    )
    due_rows = clean_observations(due_resp.get("json") or {}) if due_resp.get("ok") else []
    res_rows = clean_observations(res_resp.get("json") or {}) if res_resp.get("ok") else []
    due_asof_due = observation_on_or_before(due_rows, due_date.isoformat())
    due_asof_resolution = observation_on_or_before(res_rows, due_date.isoformat())
    res_asof_resolution = observation_on_or_before(res_rows, resolution_date.isoformat())
    y_two_point = binary_increase(due_asof_due, res_asof_resolution)
    y_both_resolution = binary_increase(due_asof_resolution, res_asof_resolution)
    due_value_current = numeric(current_due.get("value") if current_due else None)
    res_value_current = numeric(current_res.get("value") if current_res else None)
    due_value_asof_due = numeric(due_asof_due.get("value") if due_asof_due else None)
    due_value_asof_resolution = numeric(due_asof_resolution.get("value") if due_asof_resolution else None)
    res_value_asof_resolution = numeric(res_asof_resolution.get("value") if res_asof_resolution else None)
    status = "vintage_scoreable"
    if not due_resp.get("ok") or not res_resp.get("ok"):
        status = "fred_api_failed"
    elif due_asof_due is None or due_asof_resolution is None or res_asof_resolution is None:
        status = "missing_vintage_observation"
    return {
        **base,
        "join_status": status,
        "due_http_status": due_resp.get("status"),
        "resolution_http_status": res_resp.get("status"),
        "due_error_type": due_resp.get("error_type"),
        "resolution_error_type": res_resp.get("error_type"),
        "due_asof_due_observation": due_asof_due,
        "due_asof_resolution_observation": due_asof_resolution,
        "resolution_asof_resolution_observation": res_asof_resolution,
        "due_value_changed_asof_due_vs_current": differs(due_value_asof_due, due_value_current, tolerance),
        "due_value_changed_asof_resolution_vs_current": differs(due_value_asof_resolution, due_value_current, tolerance),
        "resolution_value_changed_asof_resolution_vs_current": differs(
            res_value_asof_resolution, res_value_current, tolerance
        ),
        "y_two_point_realtime": y_two_point,
        "y_both_values_asof_resolution": y_both_resolution,
        "y_two_point_differs_from_current": y_two_point != current_y if y_two_point is not None and current_y is not None else None,
        "y_both_resolution_differs_from_current": (
            y_both_resolution != current_y if y_both_resolution is not None and current_y is not None else None
        ),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def count_true(key: str, subset: list[dict[str, Any]]) -> int:
        return sum(1 for row in subset if row.get(key) is True)

    scoreable = [row for row in rows if row.get("join_status") == "vintage_scoreable"]
    by_relation: dict[str, dict[str, Any]] = {}
    for relation, rel_rows_iter in sorted(
        defaultdict(list, {rel: [r for r in rows if str(r.get("cutoff_relation")) == rel] for rel in {str(r.get("cutoff_relation")) for r in rows}}).items()
    ):
        rel_rows = list(rel_rows_iter)
        rel_scoreable = [row for row in rel_rows if row.get("join_status") == "vintage_scoreable"]
        by_relation[relation] = {
            "rows": len(rel_rows),
            "vintage_scoreable": len(rel_scoreable),
            "due_changed_asof_due": count_true("due_value_changed_asof_due_vs_current", rel_scoreable),
            "due_changed_asof_resolution": count_true("due_value_changed_asof_resolution_vs_current", rel_scoreable),
            "resolution_changed_asof_resolution": count_true(
                "resolution_value_changed_asof_resolution_vs_current", rel_scoreable
            ),
            "y_two_point_changed": count_true("y_two_point_differs_from_current", rel_scoreable),
            "y_both_resolution_changed": count_true("y_both_resolution_differs_from_current", rel_scoreable),
        }
    y_changed = count_true("y_two_point_differs_from_current", scoreable)
    if not scoreable:
        verdict = "vintage_timing_not_scoreable"
    elif y_changed:
        verdict = "current_fred_labels_not_vintage_stable"
    elif (
        count_true("due_value_changed_asof_due_vs_current", scoreable)
        or count_true("resolution_value_changed_asof_resolution_vs_current", scoreable)
    ):
        verdict = "labels_stable_but_prompt_values_revision_sensitive"
    else:
        verdict = "labels_and_prompt_values_vintage_stable_on_audit"
    return {
        "rows": len(rows),
        "vintage_scoreable_rows": len(scoreable),
        "join_status_counts": dict(sorted(Counter(str(row.get("join_status")) for row in rows).items())),
        "cutoff_relation_counts": dict(sorted(Counter(str(row.get("cutoff_relation")) for row in rows).items())),
        "due_changed_asof_due": count_true("due_value_changed_asof_due_vs_current", scoreable),
        "due_changed_asof_resolution": count_true("due_value_changed_asof_resolution_vs_current", scoreable),
        "resolution_changed_asof_resolution": count_true("resolution_value_changed_asof_resolution_vs_current", scoreable),
        "y_two_point_changed": y_changed,
        "y_both_resolution_changed": count_true("y_both_resolution_differs_from_current", scoreable),
        "by_relation": by_relation,
        "verdict": verdict,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    api_key = os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY")
    answer_rows = load_jsonl(args.answer_key)
    if args.max_rows:
        answer_rows = answer_rows[: args.max_rows]
    prior_by_contract: dict[str, dict[str, Any]] = {}
    if args.retry_failed_from:
        prior = json.loads(args.retry_failed_from.read_text(encoding="utf-8"))
        prior_by_contract = {
            str(row.get("contract_id")): row
            for row in prior.get("rows", [])
            if isinstance(row, dict) and row.get("join_status") == "vintage_scoreable"
        }
    if not api_key:
        rows = [
            {
                "contract_id": row.get("contract_id"),
                "series_id": row.get("series_id"),
                "cutoff_relation": row.get("cutoff_relation"),
                "join_status": "missing_fred_api_key",
            }
            for row in answer_rows
        ]
    else:
        audit_row._throttle_seconds = float(args.throttle_seconds)  # type: ignore[attr-defined]
        rows = []
        for row in answer_rows:
            prior = prior_by_contract.get(str(row.get("contract_id")))
            if prior:
                rows.append(prior)
                continue
            rows.append(audit_row(row, api_key=api_key, timeout=args.timeout, tolerance=args.tolerance))
            if args.throttle_seconds:
                time.sleep(args.throttle_seconds)
    summary = summarize(rows)
    return {
        "schema": "gp245-fred-vintage-timing-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "answer_key": str(args.answer_key.relative_to(REPO)),
        "credential_present_after_dotenv": bool(api_key),
        "tolerance": args.tolerance,
        "summary": summary,
        "non_claims": [
            "not a model-call result",
            "not a human or market baseline",
            "not an ALFRED bulk-export audit",
            "not proof that unreleased observations were visible to an LLM at forecast time",
        ],
        "next_gate": (
            "If labels change under realtime FRED values, repair the FRED answer key before any "
            "further model calls. If only prompt values change, rerun value-given arms with vintage values."
        ),
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# FRED Vintage Timing Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Answer key: `{report['answer_key']}`",
        f"- Credential present after dotenv: `{report['credential_present_after_dotenv']}`",
        f"- Rows: `{s['rows']}`",
        f"- Vintage-scoreable rows: `{s['vintage_scoreable_rows']}`",
        f"- Verdict: `{s['verdict']}`",
        "",
        "## Summary",
        "",
        f"- Join status counts: `{s['join_status_counts']}`",
        f"- Cutoff relation counts: `{s['cutoff_relation_counts']}`",
        f"- Due value changed as-of due vs current: `{s['due_changed_asof_due']}`",
        f"- Due value changed as-of resolution vs current: `{s['due_changed_asof_resolution']}`",
        f"- Resolution value changed as-of resolution vs current: `{s['resolution_changed_asof_resolution']}`",
        f"- Outcome changed using due-as-of-due and resolution-as-of-resolution: `{s['y_two_point_changed']}`",
        f"- Outcome changed using both values as-of resolution: `{s['y_both_resolution_changed']}`",
        "",
        "## By Cutoff Relation",
        "",
    ]
    for relation, data in s["by_relation"].items():
        lines.extend(
            [
                f"### `{relation}`",
                "",
                f"- Rows: `{data['rows']}`",
                f"- Vintage-scoreable: `{data['vintage_scoreable']}`",
                f"- Due changed as-of due: `{data['due_changed_asof_due']}`",
                f"- Due changed as-of resolution: `{data['due_changed_asof_resolution']}`",
                f"- Resolution changed as-of resolution: `{data['resolution_changed_asof_resolution']}`",
                f"- Outcome changed two-point realtime: `{data['y_two_point_changed']}`",
                f"- Outcome changed both as-of resolution: `{data['y_both_resolution_changed']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Non-Claims",
            "",
            *[f"- {claim}" for claim in report["non_claims"]],
            "",
            "## Next Gate",
            "",
            report["next_gate"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_ANSWER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--retry-failed-from", type=Path)
    parser.add_argument("--throttle-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_vintage_timing_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (args.out_dir / "fred_vintage_timing_audit.md").write_text(render_md(report), encoding="utf-8")
    with (args.out_dir / "fred_vintage_timing_audit_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("schema", "generated_at", "summary")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
