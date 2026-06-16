#!/usr/bin/env python3
"""Emit provenance-limited local evidence for the GP-245 field-wide audit.

This script does not download external benchmark rows and does not re-score a
published benchmark. It extracts the locally recorded Halawi date-distribution
summary from docs/public_claim_register.md and writes a small companion file
that states exactly what the local evidence can and cannot support.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
CLAIM_REGISTER = REPO / "docs/public_claim_register.md"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"

CSV_COLUMNS = [
    "benchmark_id",
    "evidence_status",
    "local_source",
    "line_number",
    "raw_rows_available_locally",
    "reported_binary_resolved_n",
    "reported_resolve_year_counts",
    "reported_current_generation_rows_passing",
    "score_reanalysis_available",
    "interpretation",
    "limitation",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def parse_halawi_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    target_line = None
    line_no = None
    for idx, line in enumerate(lines, start=1):
        if "F101" in line and "Halawi 2024 dataset" in line:
            target_line = line
            line_no = idx
            break
    if target_line is None or line_no is None:
        raise RuntimeError(f"Could not find Halawi local summary in {path}")

    n_match = re.search(r"N=(\d+)\s+binary-resolved", target_line)
    counts_match = re.search(
        r"resolve-year histogram\s+2021:(\d+)\s*/\s*2022:(\d+)\s*/\s*2023:(\d+)\s*/\s*2024:(\d+)\s*/\s*2025\+:\*\*(\d+)\*\*",
        target_line,
    )
    if n_match is None or counts_match is None:
        raise RuntimeError("Halawi local summary is present but the expected counts were not parsed")

    year_counts = {
        "2021": int(counts_match.group(1)),
        "2022": int(counts_match.group(2)),
        "2023": int(counts_match.group(3)),
        "2024": int(counts_match.group(4)),
        "2025_plus": int(counts_match.group(5)),
    }
    return {
        "benchmark_id": "halawi_2024_binary_resolved",
        "evidence_status": "date-distribution summary only",
        "local_source": rel(path),
        "line_number": line_no,
        "raw_rows_available_locally": False,
        "reported_binary_resolved_n": int(n_match.group(1)),
        "reported_sources": ["Polymarket", "Metaculus", "Manifold", "GJOpen", "CSET"],
        "reported_resolve_year_counts": year_counts,
        "reported_current_generation_rows_passing": year_counts["2025_plus"],
        "score_reanalysis_available": False,
        "interpretation": (
            "The local summary supports a corpus-validity warning for 2025+ model replications: "
            "the recorded binary-resolved date histogram has no 2025-or-later resolutions."
        ),
        "limitation": (
            "The raw benchmark rows are not present locally, so this is not a row-level external audit "
            "and does not recompute any published score before and after filtering."
        ),
    }


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    row = {
        key: (
            json.dumps(summary[key], sort_keys=True)
            if isinstance(summary.get(key), (dict, list))
            else summary.get(key)
        )
        for key in CSV_COLUMNS
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def build_markdown(summary: dict[str, Any], generated_at: str) -> str:
    counts = summary["reported_resolve_year_counts"]
    counts_text = ", ".join(f"{year}: {count}" for year, count in counts.items())
    return "\n".join(
        [
            "# GP-245 Field-Wide Validity Local Evidence Summary",
            "",
            f"Generated: `{generated_at}`",
            "",
            "## Halawi 2024 Binary-Resolved Dataset",
            "",
            f"- Local source: `{summary['local_source']}:{summary['line_number']}`",
            f"- Evidence status: {summary['evidence_status']}",
            f"- Reported binary-resolved rows: `{summary['reported_binary_resolved_n']}`",
            f"- Reported resolution-year counts: {counts_text}",
            f"- Rows passing a 2025+ resolution-date screen in the local summary: `{summary['reported_current_generation_rows_passing']}`",
            f"- Interpretation: {summary['interpretation']}",
            f"- Limitation: {summary['limitation']}",
            "",
            "This file is a provenance-limited summary. It supports mentioning the Halawi dataset as a motivating date-distribution warning, not as completed field-wide evidence.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim-register", type=Path, default=CLAIM_REGISTER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary = parse_halawi_summary(args.claim_register)
    payload = {
        "schema": "gp245-field-wide-validity-local-evidence-v1",
        "generated_at": generated_at,
        "summaries": [summary],
    }

    json_path = args.out_dir / "field_wide_validity_local_evidence_summary.json"
    csv_path = args.out_dir / "field_wide_validity_local_evidence_summary.csv"
    md_path = args.out_dir / "field_wide_validity_local_evidence_summary.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, summary)
    md_path.write_text(build_markdown(summary, generated_at), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
