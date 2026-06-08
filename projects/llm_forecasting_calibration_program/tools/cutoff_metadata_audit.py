#!/usr/bin/env python3
"""No-call cutoff metadata audit for GP-245.

This reports whether the master DB has enough date/cutoff metadata to support a
matched pre/post-cutoff benchmark-validity experiment. It does not mutate the DB.
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


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"

DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
DATE_KEYS = (
    "resolve_time",
    "resolution_date",
    "resolution_date_filled",
    "close_time",
    "close_date",
    "rd_close",
    "fd_close",
    "latest_date",
    "horizon",
)
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
    for key in DATE_KEYS:
        value = raw.get(key)
        parsed = parse_iso_date(value)
        if parsed:
            return parsed, f"raw_json.{key}"
    parsed = parse_iso_date(row.get("horizon"))
    if parsed:
        return parsed, "contracts.horizon"
    return None, None


def audit(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cutoff_counts: Counter[str] = Counter()
    resolved_public: Counter[tuple[str, str, str]] = Counter()
    date_key_counts: Counter[str] = Counter()
    extracted_by_source: Counter[tuple[str, str]] = Counter()
    missing_date_public_resolved: list[dict[str, Any]] = []
    rows_seen = 0
    resolved_rows = 0
    public_resolved_rows = 0
    extracted_date_rows = 0

    for db_row in cur.execute("SELECT * FROM contracts"):
        row = dict(db_row)
        rows_seen += 1
        raw = load_json(row.get("raw_json"))
        cutoff = row.get("post_training_cutoff")
        cutoff_key = "NULL" if cutoff is None else str(int(cutoff))
        cutoff_counts[cutoff_key] += 1
        for key, value in raw.items():
            if parse_iso_date(value):
                date_key_counts[key] += 1

        y_known = row.get("y_known")
        source = row.get("source") or "NULL"
        source_corpus = row.get("source_corpus") or "NULL"
        is_public = source in PUBLIC_SOURCES
        if y_known is not None:
            resolved_rows += 1
        if y_known is not None and is_public:
            public_resolved_rows += 1
            resolved_public[(source, source_corpus, cutoff_key)] += 1

        resolve_date, provenance = extract_resolve_date(row, raw)
        if resolve_date:
            extracted_date_rows += 1
            extracted_by_source[(source, provenance or "unknown")] += 1
        elif y_known is not None and is_public and len(missing_date_public_resolved) < 30:
            missing_date_public_resolved.append(
                {
                    "contract_id": row.get("contract_id"),
                    "source": source,
                    "source_corpus": source_corpus,
                    "question": row.get("question"),
                    "post_training_cutoff": cutoff,
                }
            )

    con.close()
    resolved_public_rows = [
        {
            "source": source,
            "source_corpus": source_corpus,
            "post_training_cutoff": cutoff,
            "resolved_contracts": n,
        }
        for (source, source_corpus, cutoff), n in resolved_public.most_common()
    ]
    return {
        "schema": "gp245-cutoff-metadata-audit-v1",
        "db": str(db),
        "contracts": rows_seen,
        "resolved_contracts": resolved_rows,
        "public_resolved_contracts": public_resolved_rows,
        "post_training_cutoff_counts": dict(sorted(cutoff_counts.items())),
        "date_key_counts": dict(date_key_counts.most_common()),
        "extracted_resolve_date_rows": extracted_date_rows,
        "extracted_resolve_date_by_source": [
            {"source": source, "provenance": provenance, "n": n}
            for (source, provenance), n in extracted_by_source.most_common()
        ],
        "resolved_public_by_source_corpus": resolved_public_rows,
        "missing_date_public_resolved_sample": missing_date_public_resolved,
        "verdict": (
            "metadata_and_pre_cutoff_corpus_required_before_calls"
            if public_resolved_rows and missing_date_public_resolved
            else "review_required"
        ),
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_metadata_audit.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Cutoff Metadata Audit", ""]
    lines.append(f"- Contracts: {result['contracts']}")
    lines.append(f"- Resolved contracts: {result['resolved_contracts']}")
    lines.append(f"- Public resolved contracts: {result['public_resolved_contracts']}")
    lines.append(f"- Extracted resolve-date rows: {result['extracted_resolve_date_rows']}")
    lines.append(f"- Verdict: `{result['verdict']}`")
    lines.append("")
    lines.append("## Post-Training-Cutoff Counts")
    lines.append("")
    for key, n in result["post_training_cutoff_counts"].items():
        lines.append(f"- `{key}`: {n}")
    lines.append("")
    lines.append("## Date-Like Raw JSON Values By Key")
    lines.append("")
    for key, n in list(result["date_key_counts"].items())[:20]:
        lines.append(f"- `{key}`: {n}")
    lines.append("")
    lines.append("## Resolved Public Rows")
    lines.append("")
    for row in result["resolved_public_by_source_corpus"][:20]:
        lines.append(
            f"- `{row['source']}` / `{row['source_corpus']}` / "
            f"post_cutoff=`{row['post_training_cutoff']}`: {row['resolved_contracts']}"
        )
    lines.append("")
    lines.append("## Missing Resolve-Date Sample")
    lines.append("")
    for row in result["missing_date_public_resolved_sample"][:10]:
        lines.append(
            f"- `{row['contract_id']}` ({row['source']}, {row['source_corpus']}): "
            f"{row['question']}"
        )
    lines.append("")
    (out_dir / "cutoff_metadata_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = audit(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
