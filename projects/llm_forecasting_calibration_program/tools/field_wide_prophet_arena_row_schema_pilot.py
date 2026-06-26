#!/usr/bin/env python3
"""Audit public Prophet Arena sample rows against the GP-245 row schema.

This is a small source-access pilot. It fetches the public sample releases from
the ai-prophet dataset repository, checks which row-validity fields are present,
and records the missing fields that block a conclusion-change test.

No model calls and no database mutation.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"

BASE_RAW = "https://raw.githubusercontent.com/ai-prophet/ai-prophet-datasets/main/datasets"
DATASETS = [
    "sample-economics",
    "sample-entertainment",
    "sample-sports",
    "sample-resolved",
]
RELEASE = "v1.0.0"
PUBLIC_REPO_TREES = [
    {
        "repository": "ai-prophet/ai-prophet-datasets",
        "branch": "main",
        "role": "public task dataset registry",
    },
    {
        "repository": "ai-prophet/ai-prophet",
        "branch": "main",
        "role": "forecast/evaluation package",
    },
    {
        "repository": "ai-prophet/mini-prophet",
        "branch": "main",
        "role": "forecast/evaluation package",
    },
    {
        "repository": "ai-prophet/example-api",
        "branch": "main",
        "role": "example endpoint package",
    },
    {
        "repository": "ai-prophet/pm_ranking",
        "branch": "master",
        "role": "prediction-market ranking research package",
    },
]

TRACE_PATH_RE = re.compile(
    r"forecast|submission|score|leader|result|prediction|trace|eval|run|model|answer",
    re.IGNORECASE,
)
TRACE_DATA_SUFFIXES = (
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".tsv",
    ".db",
    ".sqlite",
    ".pt",
    ".npy",
    ".npz",
    ".ipynb",
)
CODE_OR_DOC_PREFIXES = (
    ".github/",
    "docs/",
    "examples/",
    "packages/",
    "sdk/",
    "src/",
    "test/",
    "tests/",
)

ROW_FIELDS = [
    "dataset_id",
    "task_id",
    "category",
    "source",
    "predict_by",
    "resolved_at",
    "resolved_value",
    "outcome_count",
    "has_context",
    "has_metadata_close_time",
    "has_model_forecast_probability",
    "has_same_time_market_baseline",
    "event_family_proxy",
]


def fetch_text(url: str, *, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "gp245-row-schema-pilot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> dict[str, Any]:
    obj = json.loads(fetch_text(url))
    return obj if isinstance(obj, dict) else {}


def fetch_json_any(url: str) -> Any:
    return json.loads(fetch_text(url))


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {lineno}: {exc}") from exc
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    return str(value)


def row_record(dataset_id: str, row: dict[str, Any]) -> dict[str, str]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    source_meta = metadata.get("source") if isinstance(metadata.get("source"), dict) else {}
    resolved = row.get("resolved_outcome") if isinstance(row.get("resolved_outcome"), dict) else {}
    source = as_text(row.get("source") or source_meta.get("event_ticker"))
    return {
        "dataset_id": dataset_id,
        "task_id": as_text(row.get("task_id")),
        "category": as_text(metadata.get("category") or source_meta.get("category")),
        "source": source,
        "predict_by": as_text(row.get("predict_by")),
        "resolved_at": as_text(resolved.get("resolved_at")),
        "resolved_value": as_text(resolved.get("value")),
        "outcome_count": str(len(row.get("outcomes") or [])),
        "has_context": str(bool(row.get("context"))).lower(),
        "has_metadata_close_time": str(bool(source_meta.get("close_time"))).lower(),
        "has_model_forecast_probability": "false",
        "has_same_time_market_baseline": "false",
        "event_family_proxy": source,
    }


def count(rows: list[dict[str, str]], key: str) -> int:
    return sum(1 for row in rows if row.get(key))


def true_count(rows: list[dict[str, str]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) == "true")


def build_field_coverage(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    n = len(rows)
    specs = [
        (
            "row_id",
            "task_id",
            count(rows, "task_id"),
            "present",
            "Stable task identifier is present in all fetched rows.",
        ),
        (
            "question_or_market_id",
            "source/event_ticker",
            count(rows, "source"),
            "present",
            "Kalshi-style source/event ticker is present and can be used as a market/question identifier.",
        ),
        (
            "forecast_timestamp",
            "predict_by",
            count(rows, "predict_by"),
            "partial",
            "The sample rows expose a prediction deadline, not the timestamp of a submitted model forecast.",
        ),
        (
            "model_cutoff_or_retrieval_window",
            "",
            0,
            "missing",
            "No submitted model traces or input-bundle timestamps are included in the sample task release.",
        ),
        (
            "resolution_timestamp",
            "resolved_outcome.resolved_at",
            count(rows, "resolved_at"),
            "partial",
            "Resolution timestamps are present for the resolved sample rows only.",
        ),
        (
            "outcome_label",
            "resolved_outcome.value",
            count(rows, "resolved_value"),
            "partial",
            "Outcome labels are present for the resolved sample rows only.",
        ),
        (
            "label_vintage",
            "",
            0,
            "missing_or_not_applicable",
            "The fetched samples are market/sports/election style rows; no official-data vintage is documented.",
        ),
        (
            "same_contract_baseline_type",
            "",
            0,
            "missing",
            "No same-time market, human, or crowd baseline probability is included in the task release.",
        ),
        (
            "baseline_timestamp",
            "",
            0,
            "missing",
            "No comparator probability timestamp is included in the fetched task rows.",
        ),
        (
            "event_family_id",
            "source/event_ticker",
            count(rows, "event_family_proxy"),
            "proxy_only",
            "The event ticker can de-duplicate exact markets; sibling-event grouping still needs a separate rule.",
        ),
        (
            "score_before_validity_filter",
            "",
            0,
            "missing",
            "The task rows do not include submitted forecast probabilities or benchmark scores.",
        ),
        (
            "score_after_validity_filter",
            "",
            0,
            "missing",
            "A before/after conclusion-change test is blocked until model forecasts or scores are available.",
        ),
    ]
    return [
        {
            "schema_field": field,
            "source_field": source_field,
            "rows_present": str(rows_present),
            "rows_total": str(n),
            "coverage": f"{rows_present}/{n}" if n else "0/0",
            "status": status,
            "note": note,
        }
        for field, source_field, rows_present, status, note in specs
    ]


def compact_paths(paths: list[str], *, limit: int = 12) -> str:
    if not paths:
        return ""
    shown = paths[:limit]
    suffix = f";...(+{len(paths) - limit})" if len(paths) > limit else ""
    return ";".join(shown) + suffix


def is_trace_artifact_path(path: str) -> bool:
    lowered = path.lower()
    if not lowered.endswith(TRACE_DATA_SUFFIXES):
        return False
    if lowered.startswith(CODE_OR_DOC_PREFIXES):
        return False
    return bool(TRACE_PATH_RE.search(path))


def build_public_trace_surface() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in PUBLIC_REPO_TREES:
        repo = spec["repository"]
        branch = spec["branch"]
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        try:
            tree = fetch_json_any(url)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            rows.append(
                {
                    "repository": repo,
                    "branch": branch,
                    "role": spec["role"],
                    "tree_paths": "0",
                    "trace_candidate_paths": "0",
                    "public_trace_artifact_paths": "0",
                    "candidate_sample": "",
                    "artifact_sample": "",
                    "surface_verdict": f"fetch_failed: {exc}",
                }
            )
            continue

        if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
            message = tree.get("message") if isinstance(tree, dict) else "unexpected response"
            rows.append(
                {
                    "repository": repo,
                    "branch": branch,
                    "role": spec["role"],
                    "tree_paths": "0",
                    "trace_candidate_paths": "0",
                    "public_trace_artifact_paths": "0",
                    "candidate_sample": "",
                    "artifact_sample": "",
                    "surface_verdict": f"fetch_failed: {message}",
                }
            )
            continue

        paths = [
            str(item.get("path"))
            for item in tree["tree"]
            if isinstance(item, dict) and item.get("type") == "blob" and item.get("path")
        ]
        candidates = sorted(path for path in paths if TRACE_PATH_RE.search(path))
        artifacts = sorted(path for path in candidates if is_trace_artifact_path(path))
        if repo == "ai-prophet/ai-prophet-datasets":
            verdict = "task_rows_only_no_public_submission_archive"
        elif repo in {"ai-prophet/ai-prophet", "ai-prophet/mini-prophet", "ai-prophet/example-api"}:
            verdict = "forecast_evaluation_code_no_committed_submission_archive"
        else:
            verdict = "related_research_artifacts_not_prophet_arena_submission_archive"
        rows.append(
            {
                "repository": repo,
                "branch": branch,
                "role": spec["role"],
                "tree_paths": str(len(paths)),
                "trace_candidate_paths": str(len(candidates)),
                "public_trace_artifact_paths": str(len(artifacts)),
                "candidate_sample": compact_paths(candidates),
                "artifact_sample": compact_paths(artifacts),
                "surface_verdict": verdict,
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        values = []
        for col in columns:
            values.append(str(row.get(col, "")).replace("\n", " ").replace("|", r"\|"))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep, *body])


def build_markdown(
    report: dict[str, Any],
    coverage_rows: list[dict[str, str]],
    trace_surface_rows: list[dict[str, str]],
) -> str:
    summary = report["summary"]
    dataset_rows = report["datasets"]
    return "\n".join(
        [
            "# GP-245 Prophet Arena Row-Schema Pilot",
            "",
            f"Generated: `{report['generated_at']}`",
            "",
            "Purpose: check whether the public Prophet Arena / AI Prophet sample datasets expose the row-level fields needed by the GP-245 field-wide validity audit.",
            "",
            "## Summary",
            "",
            f"- datasets checked: `{summary['datasets_checked']}`",
            f"- fetched task rows: `{summary['task_rows']}`",
            f"- rows with prediction deadline (`predict_by`): `{summary['rows_with_predict_by']}`",
            f"- rows with resolved outcome: `{summary['resolved_rows']}`",
            f"- rows with submitted model forecast probabilities: `{summary['rows_with_model_forecast_probability']}`",
            f"- rows with same-time market/human baseline probabilities: `{summary['rows_with_same_time_baseline']}`",
            f"- public repositories checked for forecast traces: `{summary['public_repositories_checked']}`",
            f"- public Prophet Arena submission/leaderboard trace archives found: `{summary['public_prophet_arena_trace_archives_found']}`",
            f"- row-access verdict: `{summary['row_access_verdict']}`",
            f"- trace-surface verdict: `{summary['trace_surface_verdict']}`",
            "",
            "Interpretation: Prophet Arena now has public task-row access for the audit route, including task ids, market/source ids, prediction deadlines, contexts, outcomes, and resolved labels for the resolved sample. The public repositories checked here include task data and forecast/evaluation code, but not a committed Prophet Arena submission, leaderboard, or per-model trace archive. The fetched public surface therefore cannot yet support a conclusion-change test.",
            "",
            "## Dataset Releases",
            "",
            markdown_table(dataset_rows, ["dataset_id", "release", "task_rows", "resolved_rows", "categories", "tasks_url"]),
            "",
            "## GP-245 Row-Schema Coverage",
            "",
            markdown_table(coverage_rows, ["schema_field", "source_field", "coverage", "status", "note"]),
            "",
            "## Public Trace Surface",
            "",
            markdown_table(
                trace_surface_rows,
                [
                    "repository",
                    "role",
                    "tree_paths",
                    "trace_candidate_paths",
                    "public_trace_artifact_paths",
                    "surface_verdict",
                ],
            ),
            "",
            "## Next Action",
            "",
            "Use Prophet Arena as a public source-access route, but do not count it as a second scored benchmark family until submitted forecast traces, leaderboard files, or score files are acquired. The decisive next check is whether public submissions expose forecast timestamps/probabilities and whether same-time market baselines can be reconstructed for the same tasks.",
            "",
        ]
    )


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_report() -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    all_rows: list[dict[str, str]] = []
    dataset_summaries: list[dict[str, str]] = []
    errors: list[str] = []

    for dataset_id in DATASETS:
        release_url = f"{BASE_RAW}/{dataset_id}/releases/{RELEASE}/release.json"
        tasks_url = f"{BASE_RAW}/{dataset_id}/releases/{RELEASE}/tasks.jsonl"
        try:
            release_meta = fetch_json(release_url)
            task_objs = parse_jsonl(fetch_text(tasks_url))
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{dataset_id}: {exc}")
            continue
        records = [row_record(dataset_id, row) for row in task_objs]
        all_rows.extend(records)
        categories = sorted({record["category"] for record in records if record["category"]})
        dataset_summaries.append(
            {
                "dataset_id": dataset_id,
                "release": as_text(release_meta.get("version") or RELEASE),
                "task_rows": str(len(records)),
                "resolved_rows": str(count(records, "resolved_value")),
                "categories": ";".join(categories),
                "tasks_url": tasks_url,
            }
        )

    coverage_rows = build_field_coverage(all_rows)
    trace_surface_rows = build_public_trace_surface()
    prophet_trace_archives = sum(
        int(row["public_trace_artifact_paths"])
        for row in trace_surface_rows
        if row["repository"] in {"ai-prophet/ai-prophet-datasets", "ai-prophet/ai-prophet", "ai-prophet/mini-prophet"}
    )
    summary = {
        "datasets_checked": len(dataset_summaries),
        "task_rows": len(all_rows),
        "rows_with_predict_by": count(all_rows, "predict_by"),
        "resolved_rows": count(all_rows, "resolved_value"),
        "rows_with_context": true_count(all_rows, "has_context"),
        "rows_with_metadata_close_time": true_count(all_rows, "has_metadata_close_time"),
        "rows_with_model_forecast_probability": true_count(all_rows, "has_model_forecast_probability"),
        "rows_with_same_time_baseline": true_count(all_rows, "has_same_time_market_baseline"),
        "public_repositories_checked": len(trace_surface_rows),
        "public_prophet_arena_trace_archives_found": prophet_trace_archives,
        "trace_surface_verdict": (
            "public_task_rows_and_code_available_no_prophet_arena_submission_archive_found"
            if trace_surface_rows and prophet_trace_archives == 0
            else "public_trace_archives_need_manual_review"
        ),
        "row_access_verdict": (
            "public_task_rows_accessible_but_no_submitted_forecast_or_baseline_rows"
            if all_rows and not errors
            else "fetch_incomplete"
        ),
        "errors": errors,
    }
    report = {
        "schema": "gp245-prophet-arena-row-schema-pilot-v1",
        "generated_at": generated_at,
        "source": {
            "repository": "https://github.com/ai-prophet/ai-prophet-datasets",
            "base_raw_url": BASE_RAW,
            "release": RELEASE,
        "datasets": DATASETS,
        },
        "summary": summary,
        "datasets": dataset_summaries,
        "field_coverage": coverage_rows,
        "public_trace_surface": trace_surface_rows,
    }
    return report, coverage_rows, all_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report, coverage_rows, all_rows = build_report()
    trace_surface_rows = report["public_trace_surface"]

    json_path = args.out_dir / "field_wide_prophet_arena_row_schema_pilot.json"
    csv_path = args.out_dir / "field_wide_prophet_arena_row_schema_pilot.csv"
    rows_path = args.out_dir / "field_wide_prophet_arena_sample_rows.csv"
    trace_path = args.out_dir / "field_wide_prophet_arena_public_trace_surface.csv"
    md_path = args.out_dir / "field_wide_prophet_arena_row_schema_pilot.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, coverage_rows, list(coverage_rows[0].keys()) if coverage_rows else [])
    write_csv(rows_path, all_rows, ROW_FIELDS)
    write_csv(trace_path, trace_surface_rows, list(trace_surface_rows[0].keys()) if trace_surface_rows else [])
    md_path.write_text(build_markdown(report, coverage_rows, trace_surface_rows), encoding="utf-8")

    status = "pass" if report["summary"]["task_rows"] else "fail"
    print(
        json.dumps(
            {
                "status": status,
                "outputs": [str(json_path), str(csv_path), str(rows_path), str(trace_path), str(md_path)],
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
