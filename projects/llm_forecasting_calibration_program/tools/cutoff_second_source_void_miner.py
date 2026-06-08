#!/usr/bin/env python3
"""Mine local files/DB for Law 3 second-source pre-cutoff supply.

No model calls. No DB mutation.

The target is narrow: resolved non-Manifold rows whose *resolution date* is
before the model cutoff, matched to the Metaculus/Polymarket post-cutoff slate.
Market-open date and freeze probability are useful metadata, but neither is the
Law 3 cutoff relation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_TARGETS = DEFAULT_OUT / "cutoff_second_source_pre_cutoff_acquisition_targets.jsonl"
DEFAULT_CUTOFF = "2025-10-01"
QUESTION_BUNDLE = WORKSPACE / "fb_2026_04_12_questions.json"
RESOLUTION_BUNDLE = WORKSPACE / "fb_2026_04_12_resolutions.json"
RAW_BUNDLE = WORKSPACE / "forecastbench_2026_05_24_raw.json"
EXTERNAL_CORPUS = WORKSPACE / "external_forecastbench_corpus_16.jsonl"
TARGET_SOURCES = {"metaculus", "polymarket"}


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


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
    return "pre_cutoff" if dt < cutoff_cmp else "post_cutoff"


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


def count_by(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        counts[" | ".join(str(row.get(field)) for field in fields)] += 1
    return dict(sorted(counts.items()))


def load_targets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = read_jsonl(path)
    return [row for row in rows if row.get("source") in TARGET_SOURCES]


def join_forecastbench(cutoff: datetime) -> list[dict[str, Any]]:
    questions = read_json(QUESTION_BUNDLE).get("questions", [])
    resolutions = read_json(RESOLUTION_BUNDLE).get("resolutions", [])
    res_by_key = {
        (str(row.get("source")), str(row.get("id"))): row
        for row in resolutions
        if row.get("source") is not None and row.get("id") is not None
    }
    rows = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        source = str(q.get("source") or "")
        if source not in TARGET_SOURCES:
            continue
        res = res_by_key.get((source, str(q.get("id"))), {})
        resolved = bool(res.get("resolved")) if res else False
        freeze_p = as_float(q.get("freeze_datetime_value"))
        rows.append(
            {
                "source": source,
                "id": str(q.get("id")),
                "question": str(q.get("question") or ""),
                "resolved": resolved,
                "resolved_to": as_float(res.get("resolved_to")) if resolved else None,
                "resolution_date": res.get("resolution_date"),
                "resolution_relation": relation(res.get("resolution_date"), cutoff),
                "market_open_relation": relation(q.get("market_info_open_datetime"), cutoff),
                "freeze_relation": relation(q.get("freeze_datetime"), cutoff),
                "freeze_value_band": probability_band(freeze_p),
                "question_length_band": length_band(str(q.get("question") or "")),
            }
        )
    return rows


def summarize_question_bundle(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": repo_relative(path)}
    obj = read_json(path)
    questions = [row for row in obj.get("questions", []) if isinstance(row, dict)]
    by_source = Counter(str(row.get("source") or "") for row in questions)
    target_rows = [row for row in questions if str(row.get("source") or "") in TARGET_SOURCES]
    return {
        "exists": True,
        "path": repo_relative(path),
        "questions": len(questions),
        "target_source_questions": len(target_rows),
        "by_source": dict(sorted(by_source.items())),
        "has_resolution_bundle": False,
        "interpretation": "Question bundle only; cannot supply resolved pre-cutoff rows without a resolution bundle.",
    }


def summarize_external_corpus(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": repo_relative(path)}
    rows = read_jsonl(path)
    by_source = Counter(str(row.get("external_source") or row.get("source") or "") for row in rows)
    target_rows = [
        row for row in rows
        if str(row.get("external_source") or row.get("source") or "") in TARGET_SOURCES
    ]
    return {
        "exists": True,
        "path": repo_relative(path),
        "rows": len(rows),
        "target_source_rows": len(target_rows),
        "by_source": dict(sorted(by_source.items())),
        "interpretation": "External corpus rows here do not provide resolved Metaculus/Polymarket pre-cutoff supply.",
    }


def summarize_db(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows = [
        {
            "source": row[0] or "",
            "contracts": row[1],
            "resolved": row[2],
            "resolved_pre_flag": row[3],
            "resolved_post_flag": row[4],
            "any_pre_flag": row[5],
            "any_post_flag": row[6],
        }
        for row in cur.execute(
            """
            SELECT source,
                   COUNT(*) AS contracts,
                   SUM(CASE WHEN y_known IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                   SUM(CASE WHEN y_known IS NOT NULL AND post_training_cutoff = 0 THEN 1 ELSE 0 END) AS resolved_pre_flag,
                   SUM(CASE WHEN y_known IS NOT NULL AND post_training_cutoff = 1 THEN 1 ELSE 0 END) AS resolved_post_flag,
                   SUM(CASE WHEN post_training_cutoff = 0 THEN 1 ELSE 0 END) AS any_pre_flag,
                   SUM(CASE WHEN post_training_cutoff = 1 THEN 1 ELSE 0 END) AS any_post_flag
            FROM contracts
            WHERE source IN ('metaculus', 'polymarket', 'kalshi')
            GROUP BY source
            ORDER BY source
            """
        )
    ]
    pre_cell_counts: Counter[tuple[str, str, str]] = Counter()
    for source, question, raw_json in cur.execute(
        """
        SELECT source, question, raw_json
        FROM contracts
        WHERE source IN ('metaculus', 'polymarket', 'kalshi')
          AND y_known IS NOT NULL
          AND post_training_cutoff = 0
        """
    ):
        try:
            raw = json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            raw = {}
        freeze_p = as_float(raw.get("freeze_datetime_value"))
        pre_cell_counts[
            (
                str(source or ""),
                probability_band(freeze_p),
                length_band(str(question or "")),
            )
        ] += 1
    con.close()
    return {
        "path": repo_relative(db),
        "source_rows": rows,
        "resolved_pre_flag_total": sum(int(row["resolved_pre_flag"] or 0) for row in rows),
        "resolved_pre_cell_counts": {
            " | ".join(key): value for key, value in sorted(pre_cell_counts.items())
        },
        "interpretation": (
            "The DB may contain reviewed pre-cutoff acquisition rows not present "
            "in the original ForecastBench join; target deficits must subtract "
            "these DB-cell counts before declaring an acquisition void."
        ),
    }


def repo_file_hits(max_hits: int = 80) -> list[str]:
    needles = ("metaculus", "polymarket", "forecastbench", "prediction_market")
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__"}
    hits: list[str] = []
    roots = [
        PROGRAM,
        REPO / "analytics/public/forecast_pool",
        REPO / "scripts/public/control/forecast",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(hits) >= max_hits:
                break
            if any(part in skip_dirs for part in path.parts):
                continue
            if not path.is_file():
                continue
            lower = path.name.lower()
            if any(needle in lower for needle in needles):
                hits.append(repo_relative(path))
    return sorted(hits)


def build(args: argparse.Namespace) -> dict[str, Any]:
    cutoff = datetime.fromisoformat(args.cutoff)
    targets = load_targets(args.targets)
    joined = join_forecastbench(cutoff)
    resolved = [row for row in joined if row["resolved"]]
    pre = [row for row in resolved if row["resolution_relation"] == "pre_cutoff"]
    post = [row for row in resolved if row["resolution_relation"] == "post_cutoff"]
    open_pre_resolved = [
        row for row in resolved
        if row["market_open_relation"] == "pre_cutoff"
    ]
    target_cell_counts = Counter(
        (row.get("source"), row.get("freeze_value_band"), row.get("question_length_band"))
        for row in targets
    )
    local_satisfied_cells = Counter(
        (row.get("source"), row.get("freeze_value_band"), row.get("question_length_band"))
        for row in pre
    )
    db_summary = summarize_db(args.db)
    db_satisfied_cells: Counter[tuple[str, str, str]] = Counter()
    for key, value in db_summary["resolved_pre_cell_counts"].items():
        parts = tuple(key.split(" | "))
        if len(parts) == 3:
            db_satisfied_cells[parts] += int(value)
    satisfied_cells = local_satisfied_cells + db_satisfied_cells
    deficits = []
    for target in targets:
        key = (target.get("source"), target.get("freeze_value_band"), target.get("question_length_band"))
        need = int(target.get("target_pre_cutoff_rows") or 0)
        have = int(satisfied_cells.get(key, 0))
        deficits.append(
            {
                **target,
                "local_pre_cutoff_rows": int(local_satisfied_cells.get(key, 0)),
                "db_pre_cutoff_rows": int(db_satisfied_cells.get(key, 0)),
                "available_pre_cutoff_rows": have,
                "deficit": max(0, need - have),
            }
        )
    total_deficit = sum(row["deficit"] for row in deficits)
    return {
        "schema": "gp245-law3-second-source-void-miner-v1",
        "cutoff": args.cutoff,
        "target_manifest": repo_relative(args.targets),
        "target_cells": len(targets),
        "target_pre_cutoff_rows": sum(int(row.get("target_pre_cutoff_rows") or 0) for row in targets),
        "target_cell_key_count": len(target_cell_counts),
        "local_joined_forecastbench": {
            "questions_path": repo_relative(QUESTION_BUNDLE),
            "resolutions_path": repo_relative(RESOLUTION_BUNDLE),
            "candidate_rows": len(joined),
            "resolved_rows": len(resolved),
            "resolved_pre_cutoff_by_resolution_date": len(pre),
            "resolved_post_cutoff_by_resolution_date": len(post),
            "resolved_opened_pre_cutoff": len(open_pre_resolved),
            "counts": {
                "resolved_by_source": count_by(resolved, ("source",)),
                "resolved_by_source_resolution_relation": count_by(resolved, ("source", "resolution_relation")),
                "resolved_by_source_open_relation": count_by(resolved, ("source", "market_open_relation")),
            },
        },
        "target_deficits": deficits,
        "target_deficit_total": total_deficit,
        "other_local_surfaces": {
            "forecastbench_2026_05_24_raw": summarize_question_bundle(RAW_BUNDLE),
            "external_forecastbench_corpus_16": summarize_external_corpus(EXTERNAL_CORPUS),
            "db_contracts": db_summary,
            "repo_file_hits": repo_file_hits(),
        },
        "verdict": (
            "local_void_confirmed_external_acquisition_required"
            if total_deficit else "local_pre_cutoff_supply_ready"
        ),
        "killed_or_scoped_options": [
            "Do not use market-open date as the Law 3 cutoff relation.",
            "Do not spend model calls on a post-cutoff-only second-source slate.",
            "Do not treat more Manifold missing-band repair as the top Law 3 falsifier.",
        ],
        "next_best_action": (
            f"Acquire or backfill {total_deficit} remaining resolved pre-cutoff "
            "non-Manifold rows matching the emitted source/freeze-band/"
            "question-length cells; then freeze a second-source pre/post panel "
            "before any model calls."
        ),
        "required_row_fields": [
            "source",
            "source_id",
            "question",
            "url",
            "resolution_date",
            "resolved_to",
            "freeze_datetime",
            "freeze_datetime_value",
            "market_info_open_datetime",
            "market_info_close_datetime",
            "resolution_criteria",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    local = report["local_joined_forecastbench"]
    db = report["other_local_surfaces"]["db_contracts"]
    lines = [
        "# Law 3 Second-Source Void Miner",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Cutoff: `{report['cutoff']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Target cells: `{report['target_cells']}`",
        f"- Target pre-cutoff rows: `{report['target_pre_cutoff_rows']}`",
        f"- Local target deficit: `{report['target_deficit_total']}`",
        "",
        "## Core Local Slate",
        "",
        f"- Candidate Metaculus/Polymarket rows: `{local['candidate_rows']}`",
        f"- Resolved rows: `{local['resolved_rows']}`",
        f"- Resolved pre-cutoff by resolution date: `{local['resolved_pre_cutoff_by_resolution_date']}`",
        f"- Resolved post-cutoff by resolution date: `{local['resolved_post_cutoff_by_resolution_date']}`",
        f"- Resolved rows opened pre-cutoff: `{local['resolved_opened_pre_cutoff']}`",
        "",
        "Counts:",
        "",
        "```json",
        json.dumps(local["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "Interpretation: opened-before-cutoff rows are source-exposure or market-age evidence, not a Law 3 resolution-date replication.",
        "",
        "## DB Check",
        "",
        f"- DB: `{db['path']}`",
        f"- Resolved pre-cutoff non-Manifold rows by stored flag: `{db['resolved_pre_flag_total']}`",
        "",
        "```json",
        json.dumps(db["source_rows"], indent=2, sort_keys=True),
        "```",
        "",
        "## Other Local Surfaces",
        "",
        "```json",
        json.dumps(
            {
                "forecastbench_2026_05_24_raw": report["other_local_surfaces"]["forecastbench_2026_05_24_raw"],
                "external_forecastbench_corpus_16": report["other_local_surfaces"]["external_forecastbench_corpus_16"],
                "repo_file_hits": report["other_local_surfaces"]["repo_file_hits"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Target Deficits",
        "",
        "| source | freeze band | length band | target | local join pre | DB pre | available pre | deficit |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["target_deficits"]:
        lines.append(
            f"| `{row['source']}` | `{row['freeze_value_band']}` | `{row['question_length_band']}` | "
            f"{row['target_pre_cutoff_rows']} | {row['local_pre_cutoff_rows']} | "
            f"{row['db_pre_cutoff_rows']} | {row['available_pre_cutoff_rows']} | {row['deficit']} |"
        )
    lines.extend(
        [
            "",
            "## Killed / Scoped Options",
            "",
        ]
    )
    for item in report["killed_or_scoped_options"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Best Action", "", report["next_best_action"], ""])
    lines.extend(["Required row fields:", ""])
    for field in report["required_row_fields"]:
        lines.append(f"- `{field}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "cutoff_second_source_void_miner_report.json"
    md_path = args.out_dir / "cutoff_second_source_void_miner_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(report), encoding="utf-8")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
