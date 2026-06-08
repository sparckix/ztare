#!/usr/bin/env python3
"""Audit F100 confident-NO under source-currency/cutoff cohorts.

This no-call audit uses existing scored cutoff-validity receipts. It tests
whether the hand F100 rule still improves Brier on rows whose pre/post cutoff
relation was computed for the Law 3 source-currency panel.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test
from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
)


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "f100_source_currency_audit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f100_source_currency_audit_2026_06_03.md"
DEFAULT_PILOT = "cutoff_stage_b_panel_v1"
DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    match = DATE_RE.search(str(value))
    if not match:
        return None
    y, m, d = map(int, match.groups())
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def source_currency_receipt(row: sqlite3.Row, call_raw: dict[str, Any], contract_raw: dict[str, Any]) -> dict[str, Any]:
    """Return the typed cutoff relation receipt used by this audit.

    Stage-B call receipts include `resolve_date` and `panel_cutoff_date`, but
    older rows do not carry the expanded provenance fields. The shared
    discriminator keeps the computed relation separate from the stored DB flag,
    which is the failure mode this audit is meant to expose.
    """
    resolve_date = first_present(
        call_raw.get("resolve_date"),
        contract_raw.get("resolve_date"),
        contract_raw.get("resolution_date"),
        contract_raw.get("resolution_date_filled"),
        contract_raw.get("resolved_at"),
        contract_raw.get("close_date"),
        contract_raw.get("close_time"),
        parse_iso_date(row["horizon"]),
        parse_iso_date(contract_raw.get("horizon")),
    )
    model_cutoff_date = first_present(
        call_raw.get("panel_cutoff_date"),
        call_raw.get("model_cutoff_date"),
        contract_raw.get("panel_cutoff_date"),
        contract_raw.get("model_cutoff_date"),
    )
    receipt = classify_forecast_source_currency(
        resolve_date=str(resolve_date) if resolve_date else None,
        model_cutoff_date=str(model_cutoff_date) if model_cutoff_date else None,
        stored_post_training_cutoff=row["post_training_cutoff"],
        prefer_computed_cutoff=bool(resolve_date and model_cutoff_date),
    )
    receipt["resolve_date"] = resolve_date
    receipt["model_cutoff_date"] = model_cutoff_date
    return receipt


def load_rows(db: Path, pilot_id: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT pc.contract_id, pc.family, pc.p_success, pc.raw_json AS call_raw_json,
                   c.y_known, c.source AS contract_source, c.source_corpus,
                   c.horizon, c.post_training_cutoff, c.raw_json AS contract_raw_json
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id = ?
              AND pc.schema_ok = 1
              AND pc.p_success IS NOT NULL
              AND c.y_known IN (0, 1)
            """,
            (pilot_id,),
        ).fetchall()
    finally:
        con.close()
    out: list[dict[str, Any]] = []
    for row in rows:
        call_raw = parse_json(row["call_raw_json"])
        contract_raw = parse_json(row["contract_raw_json"])
        p = float(row["p_success"])
        y = int(row["y_known"])
        source_currency = source_currency_receipt(row, call_raw, contract_raw)
        cutoff_relation = source_currency["cutoff_relation"]
        source = call_raw.get("source") or row["contract_source"] or row["source_corpus"] or "unknown"
        adjusted = confident_no(p)
        out.append(
            {
                "contract_id": str(row["contract_id"]),
                "family": str(row["family"]),
                "source": str(source),
                "source_corpus": str(row["source_corpus"] or ""),
                "cutoff_relation": str(cutoff_relation),
                "cutoff_relation_provenance": str(source_currency["provenance"]),
                "stored_cutoff_relation": source_currency.get("stored_cutoff_relation"),
                "computed_cutoff_relation": source_currency.get("computed_cutoff_relation"),
                "cutoff_relation_conflict": bool(source_currency["cutoff_relation_conflict"]),
                "source_currency_receipt": source_currency,
                "p_raw": p,
                "p_f100": adjusted,
                "adjustment_applied": adjusted != p,
                "y": y,
                "raw_brier": brier(p, y),
                "f100_brier": brier(adjusted, y),
            }
        )
    return sorted(out, key=lambda r: (r["cutoff_relation"], r["source"], r["family"], r["contract_id"]))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "raw_brier": None,
            "f100_brier": None,
            "delta_f100_minus_raw": None,
            "adjusted_rows": 0,
            "paired_permutation": None,
        }
    raw = [float(row["raw_brier"]) for row in rows]
    f100 = [float(row["f100_brier"]) for row in rows]
    test = paired_permutation_test(f100, raw, n_perm=5000, seed=42)
    return {
        "n": len(rows),
        "contracts": len({row["contract_id"] for row in rows}),
        "raw_brier": round(statistics.mean(raw), 6),
        "f100_brier": round(statistics.mean(f100), 6),
        "delta_f100_minus_raw": round(statistics.mean(f100) - statistics.mean(raw), 6),
        "adjusted_rows": sum(1 for row in rows if row["adjustment_applied"]),
        "yes_rate": round(statistics.mean(float(row["y"]) for row in rows), 6),
        "mean_raw_p": round(statistics.mean(float(row["p_raw"]) for row in rows), 6),
        "mean_f100_p": round(statistics.mean(float(row["p_f100"]) for row in rows), 6),
        "paired_permutation": test,
    }


def split_summary(rows: list[dict[str, Any]], key: str, *, min_n: int = 1) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "unknown")].append(row)
    return {
        group: summarize(group_rows)
        for group, group_rows in sorted(groups.items())
        if len(group_rows) >= min_n
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_rows(args.db, args.pilot_id)
    tail_rows = [row for row in rows if row["p_raw"] < 0.10]
    by_relation_source: dict[str, dict[str, Any]] = {}
    for relation in sorted({row["cutoff_relation"] for row in rows}):
        relation_rows = [row for row in rows if row["cutoff_relation"] == relation]
        by_relation_source[relation] = split_summary(relation_rows, "source")
    verdict = "f100_survives_source_currency_smoke"
    major_relation_failures = []
    for relation, summary in split_summary(rows, "cutoff_relation").items():
        if summary["n"] >= args.major_min_n and summary["delta_f100_minus_raw"] is not None:
            if summary["delta_f100_minus_raw"] > 0:
                major_relation_failures.append(relation)
    if major_relation_failures:
        verdict = "f100_regresses_in_major_cutoff_relation"
    elif not tail_rows:
        verdict = "no_confident_no_tail_rows"
    return {
        "schema": "gp245-f100-source-currency-audit-v1",
        "db": str(args.db),
        "pilot_id": args.pilot_id,
        "rows": len(rows),
        "contracts": len({row["contract_id"] for row in rows}),
        "families": sorted({row["family"] for row in rows}),
        "source_counts": dict(Counter(row["source"] for row in rows)),
        "cutoff_relation_counts": dict(Counter(row["cutoff_relation"] for row in rows)),
        "cutoff_relation_provenance_counts": dict(Counter(row["cutoff_relation_provenance"] for row in rows)),
        "stored_cutoff_relation_counts": dict(Counter(str(row["stored_cutoff_relation"] or "missing") for row in rows)),
        "computed_cutoff_relation_counts": dict(Counter(str(row["computed_cutoff_relation"] or "missing") for row in rows)),
        "cutoff_relation_conflicts": sum(1 for row in rows if row["cutoff_relation_conflict"]),
        "overall": summarize(rows),
        "tail_only": summarize(tail_rows),
        "by_cutoff_relation": split_summary(rows, "cutoff_relation"),
        "tail_by_cutoff_relation": split_summary(tail_rows, "cutoff_relation"),
        "by_source": split_summary(rows, "source"),
        "tail_by_source": split_summary(tail_rows, "source"),
        "by_family": split_summary(rows, "family"),
        "tail_by_family": split_summary(tail_rows, "family"),
        "by_cutoff_relation_source": by_relation_source,
        "major_relation_failures": major_relation_failures,
        "verdict": verdict,
        "interpretation": (
            "F100 is evaluated here on the Law 3 cutoff-validity panel. "
            "Cutoff relation is computed through the shared source-currency discriminator, with stored "
            "DB flags kept as separate receipts. This is a source-currency stress test, not a replacement "
            "for the original F100 public-domain audit."
        ),
    }


def fmt(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def score_table(title: str, rows: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", "", "| cell | n | adjusted | raw Brier | F100 Brier | delta | p |", "|---|---:|---:|---:|---:|---:|---:|"]
    for cell, row in sorted(rows.items()):
        p = None
        if isinstance(row.get("paired_permutation"), dict):
            p = row["paired_permutation"].get("p_value")
        lines.append(
            f"| `{cell}` | `{row.get('n')}` | `{row.get('adjusted_rows')}` | "
            f"`{fmt(row.get('raw_brier'))}` | `{fmt(row.get('f100_brier'))}` | "
            f"`{fmt(row.get('delta_f100_minus_raw'))}` | `{fmt(p)}` |"
        )
    lines.append("")
    return lines


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# F100 Source-Currency Audit (2026-06-03)",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot: `{report['pilot_id']}`",
        f"- Rows: `{report['rows']}` over `{report['contracts']}` contracts.",
        f"- Families: `{', '.join(report['families'])}`",
        f"- Source counts: `{report['source_counts']}`",
        f"- Cutoff relation counts: `{report['cutoff_relation_counts']}`",
        f"- Cutoff relation provenance counts: `{report['cutoff_relation_provenance_counts']}`",
        f"- Stored cutoff relation counts: `{report['stored_cutoff_relation_counts']}`",
        f"- Computed cutoff relation counts: `{report['computed_cutoff_relation_counts']}`",
        f"- Cutoff relation conflicts: `{report['cutoff_relation_conflicts']}`",
        f"- Verdict: `{report['verdict']}`",
        "",
        "## Overall",
        "",
        f"- All rows: `{report['overall']}`",
        f"- Tail-only (`p_raw < 0.10`): `{report['tail_only']}`",
        "",
    ]
    lines.extend(score_table("By Cutoff Relation", report["by_cutoff_relation"]))
    lines.extend(score_table("Tail By Cutoff Relation", report["tail_by_cutoff_relation"]))
    lines.extend(score_table("By Source", report["by_source"]))
    lines.extend(score_table("Tail By Source", report["tail_by_source"]))
    lines.extend(score_table("By Family", report["by_family"]))
    lines.extend(score_table("Tail By Family", report["tail_by_family"]))
    lines.extend(["## Interpretation", "", report["interpretation"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--major-min-n", type=int, default=30)
    args = parser.parse_args()
    report = build(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("rows", "contracts", "verdict", "overall", "tail_only")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
