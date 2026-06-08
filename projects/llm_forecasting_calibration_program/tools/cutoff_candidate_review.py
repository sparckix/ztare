#!/usr/bin/env python3
"""Review selected Law 3 cutoff candidates before DB ingest.

This is a no-write guardrail. It catches candidate-slate risks that are too
judgmental for the acquisition filter but should be visible before a contract
row is inserted into the master DB.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_REPORT = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_manifold_acquisition_report.json"
DEFAULT_OUT = PROGRAM_ROOT / "cutoff_validity_v1/workspace"

POLITICAL_GENERAL_CUES = (
    "russia",
    "ukraine",
    "china",
    "taiwan",
    "macron",
    "elected",
    "re-elected",
    "military",
    "conflict",
    "approval rating",
    "covid zero",
)
FINANCE_GENERAL_CUES = (
    "usd",
    "price",
    "stock",
    "token",
    "tokens",
    "nft",
    "revenue",
    "bit coin",
    "bitcoin",
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def has_word_or_phrase(text: str, cue: str) -> bool:
    cue_l = cue.lower()
    if cue_l.isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(cue_l)}(?![a-z0-9])", text) is not None
    return cue_l in text


def has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(has_word_or_phrase(text, cue) for cue in cues)


def review_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    q = str(row.get("question") or "").lower()
    topic = str(row.get("topic") or "")
    raw = row.get("raw_manifold") or {}
    groups = raw.get("groupSlugs") or []
    if not groups:
        flags.append("no_group_slugs")
    try:
        if int(raw.get("uniqueBettorCount") or 0) <= 4:
            flags.append("thin_bettor_count")
    except Exception:
        flags.append("invalid_bettor_count")
    try:
        if float(raw.get("volume") or 0.0) <= 250.0:
            flags.append("lowish_volume")
    except Exception:
        flags.append("invalid_volume")
    if topic == "general" and has_any(q, POLITICAL_GENERAL_CUES):
        flags.append("general_bucket_contains_political_cue")
    if topic == "general" and has_any(q, FINANCE_GENERAL_CUES):
        flags.append("general_bucket_contains_finance_cue")
    if "mantic" in q or "manifold" in q or "polymarket" in q:
        flags.append("platform_self_reference")
    if "start right after january" in q:
        flags.append("trivial_calendar")
    return flags


def build_report(report_path: Path) -> dict[str, Any]:
    acquisition = read_json(report_path)
    selected = acquisition.get("selected_candidates") or []
    reviewed = []
    flag_counts: Counter[str] = Counter()
    by_target: Counter[str] = Counter()
    for row in selected:
        flags = review_flags(row)
        flag_counts.update(flags)
        by_target[str(row.get("target_key"))] += 1
        reviewed.append(
            {
                "acquisition_id": row.get("acquisition_id"),
                "contract_id": row.get("contract_id"),
                "target_key": row.get("target_key"),
                "question": row.get("question"),
                "flags": flags,
                "review_status": "manual_review" if flags else "auto_clear",
            }
        )
    manual = [row for row in reviewed if row["flags"]]
    return {
        "schema": "gp245-cutoff-candidate-review-v1",
        "acquisition_report": str(report_path),
        "selected_rows": len(selected),
        "auto_clear_rows": len(selected) - len(manual),
        "manual_review_rows": len(manual),
        "ready_for_unreviewed_db_ingest": len(selected) > 0 and not manual,
        "by_target_key": dict(sorted(by_target.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
        "reviewed_candidates": reviewed,
        "interpretation": (
            "Rows with flags are not rejected automatically. They require a "
            "review decision before DB ingest so Law 3 does not silently inherit "
            "topic, thin-market, or source-platform artifacts."
        ),
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_candidate_review_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Cutoff Candidate Review Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Selected rows: {report['selected_rows']}",
        f"- Auto-clear rows: {report['auto_clear_rows']}",
        f"- Manual-review rows: {report['manual_review_rows']}",
        f"- Ready for unreviewed DB ingest: `{report['ready_for_unreviewed_db_ingest']}`",
        "",
        "## Flag Counts",
        "",
    ]
    if not report["flag_counts"]:
        lines.append("- None.")
    for flag, n in report["flag_counts"].items():
        lines.append(f"- `{flag}`: {n}")
    lines.extend(["", "## Manual Review Rows", ""])
    for row in report["reviewed_candidates"]:
        if not row["flags"]:
            continue
        lines.append(
            f"- `{row['acquisition_id']}` `{row['target_key']}` "
            f"flags={','.join(row['flags'])}: {row['question']}"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    (out_dir / "cutoff_candidate_review_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.report)
    print(json.dumps(report, indent=2, sort_keys=True))
    write_outputs(report, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
