#!/usr/bin/env python3
"""Build a Law 3 cutoff-validity candidate/repair report from the DB.

This is stricter than cutoff_metadata_audit.py: it does not count generic
date-like fields such as FRED `latest_date` as resolution dates. The output is a
candidate corpus status plus a repair manifest for rows that cannot yet enter a
matched pre/post cutoff audit.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
)


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"

DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
PUBLIC_SOURCES = {
    "manifold",
    "polymarket",
    "metaculus",
    "fred",
    "yfinance",
    "yfinance_etf",
    "kalshi",
    "premium_public_clean",
}

# Strict closeout / resolution date sources. Deliberately excludes fields such
# as FRED `latest_date`, which indicates latest observed data, not final
# question resolution.
STRICT_RESOLVE_DATE_KEYS = (
    "resolve_time",
    "resolution_date",
    "resolution_date_filled",
    "close_time",
    "close_date",
    "resolved_at",
    "resolution_fetched_at",
    "horizon",
)


def load_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def parse_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    match = DATE_RE.search(text)
    if not match:
        return None
    y, m, d = map(int, match.groups())
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def extract_resolve_date(row: dict[str, Any], raw: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in STRICT_RESOLVE_DATE_KEYS:
        parsed = parse_iso_date(raw.get(key))
        if parsed:
            return parsed, f"raw_json.{key}"
    parsed = parse_iso_date(row.get("horizon"))
    if parsed:
        return parsed, "contracts.horizon"
    return None, None


def text_has_any(text: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        token = term.lower()
        if token.isalnum():
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text):
                return True
        elif token in text:
            return True
    return False


def relation_from_row(
    row: dict[str, Any],
    resolve_date: str | None,
    panel_cutoff_date: str | None,
    *,
    prefer_computed_cutoff: bool = False,
) -> tuple[str, str, str | None, str | None, bool]:
    source_currency = classify_forecast_source_currency(
        resolve_date=resolve_date,
        model_cutoff_date=panel_cutoff_date,
        stored_post_training_cutoff=row.get("post_training_cutoff"),
        prefer_computed_cutoff=prefer_computed_cutoff,
    )
    return (
        str(source_currency["cutoff_relation"]),
        str(source_currency["provenance"]),
        source_currency.get("stored_cutoff_relation"),
        source_currency.get("computed_cutoff_relation"),
        bool(source_currency["cutoff_relation_conflict"]),
    )


def topic_bucket(row: dict[str, Any], raw: dict[str, Any]) -> str:
    task = str(row.get("task_type") or raw.get("task_type") or "").lower()
    q = str(row.get("question") or "").lower()
    source = str(row.get("source") or "").lower()
    groups_raw = raw.get("groupSlugs") or raw.get("groups") or []
    if isinstance(groups_raw, str):
        groups = groups_raw.lower()
    elif isinstance(groups_raw, list):
        groups = " ".join(str(item).lower() for item in groups_raw)
    else:
        groups = ""
    if "fred" in source or "macro" in task or text_has_any(q, ("inflation", "unemployment")):
        return "macro"
    if (
        "yfinance" in source
        or text_has_any(groups, ("finance", "economics", "crypto"))
        or text_has_any(q, ("bitcoin", "crypto", "s&p", "stock", "price", "market"))
    ):
        return "finance"
    if (
        "sport" in task
        or text_has_any(groups, ("sport", "sports", "soccer", "football", "nfl", "nba", "mlb"))
        or text_has_any(q, ("football", "soccer", "nfl", "nba", "mlb", "championship", "world cup", "team", "series", "beat"))
    ):
        return "sports"
    if (
        "politic" in task
        or text_has_any(groups, ("politic", "politics", "election", "elections"))
        or text_has_any(q, ("election", "policy", "congress", "biden", "trump", "governor", "mayor"))
    ):
        return "politics"
    return "general"


def question_length_bucket(question: str | None) -> str:
    n = len((question or "").split())
    if n <= 10:
        return "short"
    if n <= 25:
        return "medium"
    return "long"


def build_rows(db: Path, panel_cutoff_date: str | None, *, prefer_computed_cutoff: bool = False) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    for db_row in con.execute("SELECT * FROM contracts"):
        row = dict(db_row)
        source = row.get("source")
        if source not in PUBLIC_SOURCES:
            continue
        raw = load_json(row.get("raw_json"))
        resolve_date, resolve_provenance = extract_resolve_date(row, raw)
        relation, relation_provenance, stored_relation, computed_relation, relation_conflict = relation_from_row(
            row,
            resolve_date,
            panel_cutoff_date,
            prefer_computed_cutoff=prefer_computed_cutoff,
        )
        y_known = row.get("y_known")
        missing: list[str] = []
        if y_known is None:
            missing.append("y_known")
        if not resolve_date:
            missing.append("resolve_date")
        if relation == "unknown":
            missing.append("cutoff_relation")
        rows.append(
            {
                "contract_id": row.get("contract_id"),
                "question": row.get("question"),
                "source": source,
                "source_corpus": row.get("source_corpus"),
                "task_type": row.get("task_type"),
                "y_known": y_known,
                "resolve_date": resolve_date,
                "resolve_date_provenance": resolve_provenance,
                "cutoff_relation": relation,
                "cutoff_relation_provenance": relation_provenance,
                "stored_cutoff_relation": stored_relation,
                "computed_cutoff_relation": computed_relation,
                "cutoff_relation_conflict": relation_conflict,
                "topic": topic_bucket(row, raw),
                "question_length_bucket": question_length_bucket(row.get("question")),
                "eligible_for_matched_audit": not missing,
                "missing_fields": missing,
            }
        )
    con.close()
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row["eligible_for_matched_audit"]]
    repair = [row for row in rows if not row["eligible_for_matched_audit"]]
    relation_counts = Counter(row["cutoff_relation"] for row in eligible)
    stored_relation_counts = Counter(row["stored_cutoff_relation"] for row in rows if row["stored_cutoff_relation"])
    computed_relation_counts = Counter(row["computed_cutoff_relation"] for row in rows if row["computed_cutoff_relation"])
    repair_counts = Counter(field for row in repair for field in row["missing_fields"])
    strata = Counter(
        (row["cutoff_relation"], row["source"], row["topic"], row["question_length_bucket"])
        for row in eligible
    )
    pre_keys = {
        (row["source"], row["topic"], row["question_length_bucket"])
        for row in eligible
        if row["cutoff_relation"] == "pre_cutoff"
    }
    post_keys = {
        (row["source"], row["topic"], row["question_length_bucket"])
        for row in eligible
        if row["cutoff_relation"] == "post_cutoff"
    }
    matched_keys = sorted(pre_keys & post_keys)
    matched_rows = [
        {
            "source": source,
            "topic": topic,
            "question_length_bucket": length,
            "pre_n": strata.get(("pre_cutoff", source, topic, length), 0),
            "post_n": strata.get(("post_cutoff", source, topic, length), 0),
        }
        for source, topic, length in matched_keys
    ]
    pre_n = relation_counts.get("pre_cutoff", 0)
    post_n = relation_counts.get("post_cutoff", 0)
    repair_computed_pre_cutoff = [
        row for row in repair
        if row.get("computed_cutoff_relation") == "pre_cutoff"
    ]
    y_known_missing_resolve_or_relation = [
        row for row in repair
        if row.get("y_known") is not None
        and (
            "resolve_date" in row.get("missing_fields", [])
            or "cutoff_relation" in row.get("missing_fields", [])
        )
    ]
    matched_strata_deficits = [
        {
            **row,
            "pre_needed_to_match_post_or_stage_b": max(min(row["post_n"], 40) - row["pre_n"], 0),
        }
        for row in matched_rows
    ]
    return {
        "total_public_rows": len(rows),
        "eligible_rows": len(eligible),
        "repair_rows": len(repair),
        "eligible_by_relation": dict(relation_counts),
        "stored_relation_counts": dict(stored_relation_counts),
        "computed_relation_counts": dict(computed_relation_counts),
        "cutoff_relation_conflicts": sum(1 for row in rows if row.get("cutoff_relation_conflict")),
        "repair_missing_field_counts": dict(repair_counts),
        "matched_strata": matched_rows,
        "matched_strata_count": len(matched_rows),
        "minimum_stage_b_ready": pre_n >= 40
        and post_n >= 40
        and bool(matched_rows),
        "pre_cutoff_supply_plan": {
            "current_pre_cutoff_eligible": pre_n,
            "current_post_cutoff_eligible": post_n,
            "pre_cutoff_deficit_to_stage_b_minimum": max(40 - pre_n, 0),
            "repair_rows_already_computed_pre_cutoff": len(repair_computed_pre_cutoff),
            "y_known_rows_missing_resolve_or_relation": len(y_known_missing_resolve_or_relation),
            "matched_strata_deficits": matched_strata_deficits,
            "interpretation": (
                "No existing repair row is already computed pre_cutoff. "
                "Law 3 needs intentional historical pre-cutoff corpus supply, "
                "not model calls and not a simple y_known backfill."
            ),
        },
    }


def build_report(db: Path, panel_cutoff_date: str | None, *, prefer_computed_cutoff: bool = False) -> dict[str, Any]:
    rows = build_rows(db, panel_cutoff_date, prefer_computed_cutoff=prefer_computed_cutoff)
    summary = summarize(rows)
    repair = [row for row in rows if not row["eligible_for_matched_audit"]]
    eligible = [row for row in rows if row["eligible_for_matched_audit"]]
    return {
        "schema": "gp245-cutoff-candidate-report-v1",
        "db": str(db),
        "panel_cutoff_date": panel_cutoff_date,
        "prefer_computed_cutoff": prefer_computed_cutoff,
        "summary": summary,
        "verdict": (
            "stage_b_ready"
            if summary["minimum_stage_b_ready"]
            else "not_stage_b_ready_metadata_or_pre_cutoff_supply_missing"
        ),
        "eligible_sample": eligible[:50],
        "repair_manifest": repair[:200],
        "next_actions": [
            "Do not fire cutoff-validity model calls until matched pre/post strata exist.",
            "Resolve or exclude rows missing y_known.",
            "Repair premium_public_clean rows with resolve_date and cutoff_relation before using them.",
            "Use --prefer-computed-cutoff with a concrete model cutoff date to audit stale stored cutoff flags.",
            "Construct intentional pre_cutoff public rows; current eligible surface remains post_cutoff-heavy.",
        ],
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_candidate_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Cutoff Candidate Report", ""]
    lines.append(f"- Verdict: `{result['verdict']}`")
    lines.append(f"- Panel cutoff date: `{result['panel_cutoff_date']}`")
    lines.append(f"- Prefer computed cutoff: `{result['prefer_computed_cutoff']}`")
    lines.append(f"- Public rows: {result['summary']['total_public_rows']}")
    lines.append(f"- Eligible rows: {result['summary']['eligible_rows']}")
    lines.append(f"- Repair rows: {result['summary']['repair_rows']}")
    lines.append(f"- Matched strata: {result['summary']['matched_strata_count']}")
    lines.append(f"- Stored/computed cutoff relation conflicts: {result['summary']['cutoff_relation_conflicts']}")
    lines.append(f"- Stage B ready: `{result['summary']['minimum_stage_b_ready']}`")
    lines.append("")
    lines.append("## Eligible By Relation")
    lines.append("")
    for relation, n in sorted(result["summary"]["eligible_by_relation"].items()):
        lines.append(f"- `{relation}`: {n}")
    lines.append("")
    lines.append("## Stored vs Computed Relation Counts")
    lines.append("")
    lines.append(f"- Stored: `{result['summary']['stored_relation_counts']}`")
    lines.append(f"- Computed: `{result['summary']['computed_relation_counts']}`")
    lines.append("")
    lines.append("## Repair Missing Fields")
    lines.append("")
    if not result["summary"]["repair_missing_field_counts"]:
        lines.append("- None.")
    for field, n in sorted(result["summary"]["repair_missing_field_counts"].items()):
        lines.append(f"- `{field}`: {n}")
    lines.append("")
    lines.append("## Matched Strata")
    lines.append("")
    if not result["summary"]["matched_strata"]:
        lines.append("- None yet.")
    for row in result["summary"]["matched_strata"][:20]:
        lines.append(
            f"- `{row['source']}` / `{row['topic']}` / `{row['question_length_bucket']}`: "
            f"pre={row['pre_n']}, post={row['post_n']}"
        )
    supply = result["summary"].get("pre_cutoff_supply_plan") or {}
    lines.append("")
    lines.append("## Pre-Cutoff Supply Plan")
    lines.append("")
    lines.append(f"- Current pre-cutoff eligible: `{supply.get('current_pre_cutoff_eligible')}`")
    lines.append(f"- Current post-cutoff eligible: `{supply.get('current_post_cutoff_eligible')}`")
    lines.append(f"- Pre-cutoff deficit to Stage B minimum: `{supply.get('pre_cutoff_deficit_to_stage_b_minimum')}`")
    lines.append(f"- Existing repair rows already computed pre-cutoff: `{supply.get('repair_rows_already_computed_pre_cutoff')}`")
    lines.append(f"- y_known rows missing resolve/relation: `{supply.get('y_known_rows_missing_resolve_or_relation')}`")
    lines.append(f"- Interpretation: {supply.get('interpretation')}")
    deficits = supply.get("matched_strata_deficits") or []
    if deficits:
        lines.append("- Matched-strata deficits:")
        for row in deficits[:20]:
            lines.append(
                f"  - `{row['source']}` / `{row['topic']}` / `{row['question_length_bucket']}`: "
                f"pre={row['pre_n']}, post={row['post_n']}, "
                f"needed={row['pre_needed_to_match_post_or_stage_b']}"
            )
    lines.append("")
    lines.append("## Repair Manifest Sample")
    lines.append("")
    for row in result["repair_manifest"][:20]:
        fields = ",".join(row["missing_fields"])
        lines.append(
            f"- `{row['contract_id']}` ({row['source']}, {row['source_corpus']}): "
            f"missing={fields}; question={row['question']}"
        )
    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    for item in result["next_actions"]:
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "cutoff_candidate_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff-date")
    parser.add_argument(
        "--prefer-computed-cutoff",
        action="store_true",
        help="When --panel-cutoff-date is provided, use computed resolve_date-vs-cutoff relation over stored post_training_cutoff.",
    )
    args = parser.parse_args()
    result = build_report(
        args.db,
        args.panel_cutoff_date,
        prefer_computed_cutoff=args.prefer_computed_cutoff,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
