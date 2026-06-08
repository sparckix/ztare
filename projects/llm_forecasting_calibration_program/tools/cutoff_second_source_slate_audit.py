#!/usr/bin/env python3
"""Audit non-Manifold second-source slate readiness for Law 3.

No model calls. No DB mutation. Joins the 2026-04-12 question bundle with its
resolution bundle and reports whether Metaculus/Polymarket rows can support a
pre/post cutoff-validity replication.

Law 3 cutoff relation is resolution-date vs model-cutoff date. Freeze
probability is only the pre-outcome base-rate/matching field.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import n_required_for_brier_delta


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_QUESTIONS = WORKSPACE / "fb_2026_04_12_questions.json"
DEFAULT_RESOLUTIONS = WORKSPACE / "fb_2026_04_12_resolutions.json"
DEFAULT_OUT = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_SOURCES = ("metaculus", "polymarket")
DEFAULT_CUTOFF = "2025-10-01"


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_bundle(path: Path, key: str) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = obj.get(key, [])
    if not isinstance(rows, list):
        raise TypeError(f"{path} field {key!r} is not a list")
    return [row for row in rows if isinstance(row, dict)]


def parse_dt(value: Any) -> datetime | None:
    if value in (None, "", "N/A"):
        return None
    text = str(value).strip()
    if not text or text == "N/A":
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def relation(value: Any, cutoff: datetime) -> str:
    dt = parse_dt(value)
    if dt is None:
        return "unknown"
    cutoff_cmp = cutoff
    if dt.tzinfo is not None and cutoff_cmp.tzinfo is None:
        cutoff_cmp = cutoff_cmp.replace(tzinfo=dt.tzinfo)
    if dt < cutoff_cmp:
        return "pre_cutoff"
    return "post_cutoff"


def as_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if out < 0 or out > 1:
        return None
    return out


def probability_band(value: float | None) -> str:
    if value is None:
        return "missing"
    if value < 0.10:
        return "0.00-0.10"
    if value < 0.25:
        return "0.10-0.25"
    if value < 0.50:
        return "0.25-0.50"
    if value < 0.75:
        return "0.50-0.75"
    if value < 0.90:
        return "0.75-0.90"
    return "0.90-1.00"


def length_band(question: str) -> str:
    n = len(question)
    if n < 80:
        return "<80"
    if n < 160:
        return "80-159"
    if n < 280:
        return "160-279"
    return "280+"


def join_rows(
    questions: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    *,
    sources: set[str],
    cutoff: datetime,
) -> list[dict[str, Any]]:
    resolution_by_key = {
        (str(row.get("source")), str(row.get("id"))): row
        for row in resolutions
        if row.get("source") is not None and row.get("id") is not None
    }
    joined = []
    for question in questions:
        source = str(question.get("source") or "")
        if source not in sources:
            continue
        key = (source, str(question.get("id")))
        res = resolution_by_key.get(key, {})
        freeze_value = as_float(question.get("freeze_datetime_value"))
        resolved_flag = bool(res.get("resolved")) if res else False
        resolved_to = as_float(res.get("resolved_to")) if resolved_flag else None
        joined.append(
            {
                "id": str(question.get("id")),
                "source": source,
                "question": str(question.get("question") or ""),
                "url": question.get("url"),
                "freeze_datetime": question.get("freeze_datetime"),
                "freeze_relation": relation(question.get("freeze_datetime"), cutoff),
                "market_open_datetime": question.get("market_info_open_datetime"),
                "market_open_relation": relation(question.get("market_info_open_datetime"), cutoff),
                "market_close_datetime": question.get("market_info_close_datetime"),
                "market_close_relation": relation(question.get("market_info_close_datetime"), cutoff),
                "freeze_datetime_value": freeze_value,
                "freeze_value_band": probability_band(freeze_value),
                "resolution_date": res.get("resolution_date"),
                "resolution_relation": relation(res.get("resolution_date"), cutoff),
                "cutoff_relation": relation(res.get("resolution_date"), cutoff),
                "resolved": resolved_flag,
                "resolved_to": resolved_to,
                "has_resolution_row": bool(res),
                "question_length": len(str(question.get("question") or "")),
                "question_length_band": length_band(str(question.get("question") or "")),
            }
        )
    return joined


def count_by(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        key = " | ".join(str(row.get(field)) for field in fields)
        counts[key] += 1
    return dict(sorted(counts.items()))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    questions = read_bundle(args.questions, "questions")
    resolutions = read_bundle(args.resolutions, "resolutions")
    cutoff = datetime.fromisoformat(args.cutoff)
    sources = {source.strip() for source in args.sources.split(",") if source.strip()}
    joined = join_rows(questions, resolutions, sources=sources, cutoff=cutoff)
    resolved = [row for row in joined if row["resolved"]]
    pre_cutoff = [row for row in resolved if row["cutoff_relation"] == "pre_cutoff"]
    post_cutoff = [row for row in resolved if row["cutoff_relation"] == "post_cutoff"]
    open_pre_candidates = [row for row in joined if row["market_open_relation"] == "pre_cutoff"]
    open_pre_resolved = [row for row in open_pre_candidates if row["resolved"]]
    post_target_counts = Counter(
        (row["source"], row["freeze_value_band"], row["question_length_band"])
        for row in post_cutoff
    )
    ready = bool(pre_cutoff and post_cutoff)
    target_total = sum(post_target_counts.values())
    return {
        "schema": "gp245-law3-second-source-slate-audit-v1",
        "questions_path": repo_relative(args.questions),
        "resolutions_path": repo_relative(args.resolutions),
        "cutoff": args.cutoff,
        "sources": sorted(sources),
        "total_questions_loaded": len(questions),
        "total_resolutions_loaded": len(resolutions),
        "candidate_questions": len(joined),
        "resolution_rows_joined": sum(1 for row in joined if row["has_resolution_row"]),
        "resolved_candidates": len(resolved),
        "pre_cutoff_resolved_by_resolution_date": len(pre_cutoff),
        "post_cutoff_resolved_by_resolution_date": len(post_cutoff),
        "ready_for_pre_post_replication": ready,
        "verdict": "pre_post_ready" if ready else "post_cutoff_slate_only_pre_cutoff_backfill_needed",
        "adjacent_open_date_surface": {
            "candidate_rows_opened_pre_cutoff": len(open_pre_candidates),
            "resolved_rows_opened_pre_cutoff": len(open_pre_resolved),
            "counts_by_source": count_by(open_pre_candidates, ("source",)),
            "resolved_counts_by_source": count_by(open_pre_resolved, ("source",)),
            "interpretation": (
                "Open-date pre-cutoff rows test source-exposure/market-age, not the current Law 3 "
                "resolution-date cutoff relation. Do not substitute this for second-source replication."
            ),
        },
        "counts": {
            "questions_by_source": count_by(joined, ("source",)),
            "resolved_by_source": count_by(resolved, ("source",)),
            "resolved_by_source_cutoff_relation": count_by(resolved, ("source", "cutoff_relation")),
            "resolved_by_source_freeze_relation": count_by(resolved, ("source", "freeze_relation")),
            "resolved_by_source_open_relation": count_by(resolved, ("source", "market_open_relation")),
            "resolved_by_source_resolution_relation": count_by(resolved, ("source", "resolution_relation")),
            "resolved_by_source_freeze_band": count_by(resolved, ("source", "freeze_value_band")),
            "resolved_by_source_question_length_band": count_by(resolved, ("source", "question_length_band")),
        },
        "matched_pre_cutoff_acquisition_targets": [
            {
                "source": source,
                "freeze_value_band": band,
                "question_length_band": length,
                "target_pre_cutoff_rows": count,
            }
            for (source, band, length), count in sorted(post_target_counts.items())
        ],
        "power_note": {
            "target_matched_pre_rows": target_total,
            "n_required_delta_0p13_default_sd_0p20": n_required_for_brier_delta(0.13, sd_brier=0.20),
            "n_required_delta_0p10_default_sd_0p20": n_required_for_brier_delta(0.10, sd_brier=0.20),
            "interpretation": (
                "A 50-row matched pre side is plausibly powered for a Stage-B-sized effect, "
                "but a smaller delta around 0.10 would be underpowered at alpha=0.05/power=0.80."
            ),
        },
        "smallest_next_step": (
            "Acquire or backfill pre-cutoff non-Manifold rows matching the source/freeze-band/length distribution before model calls; "
            "the current fb_2026_04_12 Metaculus/Polymarket slate is useful as the post-cutoff side only."
        ),
        "resolved_manifest": resolved,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Law 3 Second-Source Slate Audit",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Cutoff: `{report['cutoff']}`",
        f"- Sources: `{report['sources']}`",
        f"- Candidate questions: {report['candidate_questions']}",
        f"- Resolution rows joined: {report['resolution_rows_joined']}",
        f"- Resolved candidates: {report['resolved_candidates']}",
        f"- Pre-cutoff resolved by resolution date: {report['pre_cutoff_resolved_by_resolution_date']}",
        f"- Post-cutoff resolved by resolution date: {report['post_cutoff_resolved_by_resolution_date']}",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Counts",
        "",
    ]
    for title, counts in report["counts"].items():
        lines.extend([f"### {title}", "", "```json", json.dumps(counts, indent=2, sort_keys=True), "```", ""])
    lines.extend(
        [
            "## Matched Pre-Cutoff Acquisition Targets",
            "",
            "```json",
            json.dumps(report["matched_pre_cutoff_acquisition_targets"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    lines.extend(
        [
            "## Adjacent Open-Date Surface",
            "",
            "```json",
            json.dumps(report["adjacent_open_date_surface"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    lines.extend(
        [
            "## Power Note",
            "",
            "```json",
            json.dumps(report["power_note"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    lines.extend(
        [
            "## Smallest Next Step",
            "",
            report["smallest_next_step"],
            "",
            "## Resolved Manifest Preview",
            "",
            "| source | id | freeze_p | cutoff_relation | resolved_to | resolution_date | question |",
            "|---|---|---:|---|---:|---|---|",
        ]
    )
    for row in report["resolved_manifest"][:30]:
        question = str(row["question"]).replace("|", "/")[:120]
        lines.append(
            f"| `{row['source']}` | `{row['id']}` | {row['freeze_datetime_value']} | "
            f"`{row['cutoff_relation']}` | {row['resolved_to']} | {row['resolution_date']} | {question} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = "cutoff_second_source_slate_audit_report"
    report_path = args.out_dir / f"{stem}.json"
    md_path = args.out_dir / f"{stem}.md"
    manifest_path = args.out_dir / "cutoff_second_source_resolved_manifest.jsonl"
    target_path = args.out_dir / "cutoff_second_source_pre_cutoff_acquisition_targets.jsonl"
    public_report = {key: value for key, value in report.items() if key != "resolved_manifest"}
    public_report["resolved_manifest_count"] = len(report["resolved_manifest"])
    report_path.write_text(json.dumps(public_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(report), encoding="utf-8")
    manifest_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report["resolved_manifest"]),
        encoding="utf-8",
    )
    target_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report["matched_pre_cutoff_acquisition_targets"]),
        encoding="utf-8",
    )
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
