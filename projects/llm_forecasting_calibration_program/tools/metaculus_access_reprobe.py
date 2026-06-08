#!/usr/bin/env python3
"""Bounded Metaculus API access reprobe for Law 3 acquisition.

This script checks whether the current local credentials expose the two fields
needed for the Metaculus second-source slice: resolved Yes/No values and
pre-resolution aggregate/community prediction history. It intentionally records
only HTTP status and field availability, never the token.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is in repo requirements
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_OUT_JSON = WORKSPACE / "metaculus_api_access_reprobe_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "metaculus_api_access_reprobe_2026_06_03.md"
BASE = "https://www.metaculus.com"


def bootstrap_dotenv() -> None:
    if os.environ.get("METACULUS_API_KEY"):
        return
    if load_dotenv is None:
        return
    candidate = REPO / ".env"
    if candidate.exists():
        load_dotenv(candidate, override=False)


def request_json(path: str, headers: dict[str, str], *, timeout: int = 30) -> dict[str, Any]:
    url = BASE + path
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {
                "ok": True,
                "status": int(response.status),
                "url_path": path,
                "json": json.loads(body) if body else None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": int(exc.code),
            "url_path": path,
            "error_body_excerpt": body[:500],
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "url_path": path,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }


def list_posts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("results", "posts"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def first_question(post: dict[str, Any]) -> dict[str, Any]:
    direct = post.get("question")
    if isinstance(direct, dict):
        return direct
    for key in ("questions", "group_of_questions"):
        value = post.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    return item
        if isinstance(value, dict):
            nested = value.get("questions")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        return item
    return {}


def aggregate_availability(question: dict[str, Any]) -> dict[str, Any]:
    aggregations = question.get("aggregations")
    latest_available = False
    history_available = False
    aggregation_keys: list[str] = []
    if isinstance(aggregations, dict):
        aggregation_keys = sorted(str(k) for k in aggregations.keys())
        for value in aggregations.values():
            if not isinstance(value, dict):
                continue
            latest_available = latest_available or value.get("latest") is not None
            history_available = history_available or value.get("history") is not None
    return {
        "aggregation_keys": aggregation_keys,
        "any_latest_available": latest_available,
        "any_history_available": history_available,
    }


def post_summary(post: dict[str, Any]) -> dict[str, Any]:
    question = first_question(post)
    return {
        "post_id": post.get("id"),
        "post_title": post.get("title"),
        "post_published_at": post.get("published_at") or post.get("publishedAt"),
        "question_id": question.get("id"),
        "question_type": question.get("type"),
        "question_status": question.get("status"),
        "resolution_field_present": "resolution" in question,
        "resolution_value_is_non_null": question.get("resolution") is not None,
        "actual_resolve_time": question.get("actual_resolve_time") or question.get("actualResolveTime"),
        **aggregate_availability(question),
    }


def data_download_probe(headers: dict[str, str]) -> dict[str, Any]:
    probes = [
        "/api/data/download/",
        "/api/data/download/?format=csv",
        "/api/data/download/?include_comments=false",
    ]
    return {"attempts": [request_json(path, headers) for path in probes]}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    token = os.environ.get("METACULUS_API_KEY")
    if not token:
        return {
            "schema": "metaculus-api-access-reprobe-v1",
            "date": datetime.now(timezone.utc).isoformat(),
            "credential_present": False,
            "verdict": "missing_metaculus_api_key_after_dotenv",
        }
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
        "User-Agent": "ztare-gp245-metaculus-access-reprobe/1.0",
    }
    paths = [
        "/api/posts/?limit=5",
        "/api/posts/?limit=5&order_by=published_at",
        "/api/posts/?limit=5&forecast_type=binary&statuses=resolved",
    ]
    feed_attempts = [request_json(path, headers, timeout=args.timeout) for path in paths]
    post_summaries: list[dict[str, Any]] = []
    detail_attempts: list[dict[str, Any]] = []
    for attempt in feed_attempts:
        if not attempt.get("ok"):
            continue
        for post in list_posts(attempt.get("json"))[: args.max_details]:
            summary = post_summary(post)
            post_summaries.append(summary)
            post_id = summary.get("post_id")
            if post_id is not None:
                detail = request_json(f"/api/posts/{urllib.parse.quote(str(post_id))}/", headers, timeout=args.timeout)
                detail_attempts.append(
                    {
                        "post_id": post_id,
                        "status": detail.get("status"),
                        "ok": detail.get("ok"),
                        "summary": post_summary(detail.get("json") or {}) if detail.get("ok") else None,
                        "error_body_excerpt": detail.get("error_body_excerpt"),
                        "error_type": detail.get("error_type"),
                    }
                )
    download = data_download_probe(headers)
    all_summaries = post_summaries + [
        item["summary"] for item in detail_attempts if isinstance(item.get("summary"), dict)
    ]
    has_resolution = any(item.get("resolution_value_is_non_null") for item in all_summaries)
    has_history = any(item.get("any_history_available") for item in all_summaries)
    download_ok = any(item.get("ok") for item in download["attempts"])
    if has_resolution and has_history:
        verdict = "metaculus_api_fields_available_for_law3_probe_sample"
    elif download_ok:
        verdict = "data_download_endpoint_available_needs_export_parse"
    else:
        verdict = "authenticated_but_required_fields_not_available_in_probe"
    return {
        "schema": "metaculus-api-access-reprobe-v1",
        "date": datetime.now(timezone.utc).isoformat(),
        "credential_present": True,
        "auth_header_shape": "Authorization: Token <redacted>",
        "official_docs_checked": [
            "https://www.metaculus.com/api/",
            "https://www.metaculus.com/notebooks/42554/changes-to-the-metaculus-api/",
        ],
        "feed_attempts": [
            {
                "url_path": item.get("url_path"),
                "ok": item.get("ok"),
                "status": item.get("status"),
                "error_body_excerpt": item.get("error_body_excerpt"),
                "error_type": item.get("error_type"),
            }
            for item in feed_attempts
        ],
        "post_summaries": post_summaries,
        "detail_attempts": detail_attempts,
        "data_download_probe": download,
        "field_availability": {
            "any_non_null_resolution_in_probe": has_resolution,
            "any_aggregate_history_in_probe": has_history,
            "data_download_any_ok": download_ok,
        },
        "verdict": verdict,
        "interpretation": (
            "A negative verdict here means the current credential did not expose "
            "the exact fields needed by the Law 3 Metaculus target in this bounded "
            "probe. It does not test a licensed export file or website-mediated "
            "manual download."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Metaculus API Access Reprobe",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Credential present after dotenv: `{report.get('credential_present')}`",
        f"- Verdict: `{report.get('verdict')}`",
        f"- Auth header shape: `{report.get('auth_header_shape', 'NA')}`",
        "",
        "## Field Availability",
        "",
        "```json",
        json.dumps(report.get("field_availability", {}), indent=2, sort_keys=True),
        "```",
        "",
        "## Feed Attempts",
        "",
        "```json",
        json.dumps(report.get("feed_attempts", []), indent=2, sort_keys=True),
        "```",
        "",
        "## Interpretation",
        "",
        str(report.get("interpretation", "")),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-details", type=int, default=3)
    args = parser.parse_args()
    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps(
        {
            "credential_present": report.get("credential_present"),
            "field_availability": report.get("field_availability"),
            "verdict": report.get("verdict"),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
