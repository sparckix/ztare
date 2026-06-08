#!/usr/bin/env python3
"""Freeze the GP-245 Law 3 Stage-B matched corpus and dispatch slate.

This is a no-call step. It materializes the exact contracts that are eligible
for the cutoff-validity panel after the Stage-B balance gate turns green, then
creates a minimum balanced 40/40 pre/post panel for the constrained 3-family
run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cutoff_candidate_report import build_rows
from cutoff_stage_b_slate import MIN_STAGE_B_POST, MIN_STAGE_B_PRE, matched_keys, stratum_key


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace"
DEFAULT_FAMILIES = ("claude", "codex_54mini", "gemini")
RUNTIME_ROUTES = {
    "claude": "claude_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}
PILOT_ID = "cutoff_stage_b_panel_v1"


def stable_json(row: Any) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_rows(rows: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(stable_json(row).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def load_contract_context(db: Path, contract_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = {
        str(row["contract_id"]): dict(row)
        for row in con.execute(
            f"""
            SELECT contract_id, horizon, raw_json, created_at, external_market_open,
                   resolution_source_url, y_known_provenance
            FROM contracts
            WHERE contract_id IN ({placeholders})
            """,
            sorted(contract_ids),
        )
    }
    con.close()
    return rows


def parse_raw_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def base_rate_band(raw: dict[str, Any]) -> str:
    value = raw.get("probability")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "unknown"
    p = max(0.0, min(1.0, float(value)))
    lo = int(p / 0.2) * 20
    if lo >= 100:
        lo = 80
    return f"{lo / 100:.2f}_{(lo + 20) / 100:.2f}"


def horizon_bucket(resolve_date: str | None, panel_cutoff_date: str) -> str:
    if not resolve_date:
        return "unknown"
    try:
        resolved = datetime.fromisoformat(resolve_date).date()
        cutoff = datetime.fromisoformat(panel_cutoff_date).date()
    except ValueError:
        return "unknown"
    days = abs((resolved - cutoff).days)
    if days <= 90:
        return "0_90d"
    if days <= 365:
        return "91_365d"
    if days <= 1095:
        return "1_3y"
    return "3y_plus"


def enrich_row(row: dict[str, Any], context: dict[str, Any], panel_cutoff_date: str) -> dict[str, Any]:
    raw = parse_raw_json(context.get("raw_json"))
    return {
        "contract_id": row["contract_id"],
        "question": row["question"],
        "source": row["source"],
        "source_corpus": row["source_corpus"],
        "task_type": row["task_type"],
        "topic": row["topic"],
        "question_length_bucket": row["question_length_bucket"],
        "resolve_date": row["resolve_date"],
        "resolve_date_provenance": row["resolve_date_provenance"],
        "panel_cutoff_date": panel_cutoff_date,
        "cutoff_relation": row["cutoff_relation"],
        "cutoff_relation_provenance": row["cutoff_relation_provenance"],
        "stored_cutoff_relation": row["stored_cutoff_relation"],
        "computed_cutoff_relation": row["computed_cutoff_relation"],
        "cutoff_relation_conflict": row["cutoff_relation_conflict"],
        "y_known": row["y_known"],
        "y_known_provenance": context.get("y_known_provenance"),
        "horizon": context.get("horizon"),
        "horizon_bucket": horizon_bucket(row.get("resolve_date"), panel_cutoff_date),
        "base_rate_band": base_rate_band(raw),
        "external_market_open": context.get("external_market_open"),
        "resolution_source_url": context.get("resolution_source_url"),
        "created_at": context.get("created_at"),
        "stratum_key": "/".join(stratum_key(row)),
    }


def select_balanced_minimum(corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key_relation: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in corpus:
        key = (row["source"], row["topic"], row["question_length_bucket"])
        by_key_relation[key][row["cutoff_relation"]].append(row)

    selected: list[dict[str, Any]] = []
    for key in sorted(by_key_relation):
        pre = sorted(by_key_relation[key].get("pre_cutoff", []), key=lambda r: str(r["contract_id"]))
        post = sorted(by_key_relation[key].get("post_cutoff", []), key=lambda r: str(r["contract_id"]))
        if not pre or not post:
            continue
        n = min(len(pre), len(post))
        selected.extend(pre[:n])
        selected.extend(post[:n])
    return sorted(selected, key=lambda r: (r["cutoff_relation"], r["stratum_key"], str(r["contract_id"])))


def build_prompt(contract: dict[str, Any]) -> str:
    return (
        "You are making a tool-free binary forecast. Do not browse, search, or use external tools.\n"
        "Estimate the probability that the event described by the question resolved YES.\n"
        "Return only a JSON object with keys: p_success, confidence, recognition_self_report, "
        "cutoff_relation, source, topic, base_rate_band, source_finding_ids, rationale_short.\n\n"
        f"Question: {contract['question']}\n"
        f"Source: {contract['source']}\n"
        f"Topic: {contract['topic']}\n"
        f"Cutoff relation to echo: {contract['cutoff_relation']}\n"
        f"Base-rate band to echo: {contract['base_rate_band']}\n\n"
        "Definitions: p_success is a number in [0,1]. confidence is your confidence in that "
        "probability, in [0,1]. recognition_self_report is how much you believe you recognize "
        "this exact resolved question or answer from memory, in [0,1]. source_finding_ids must "
        "be [\"F101\"]. Keep rationale_short under 40 words."
    )


def dispatch_rows(panel_contracts: list[dict[str, Any]], families: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contract in sorted(panel_contracts, key=lambda r: str(r["contract_id"])):
        for family in families:
            dispatch_id = f"{PILOT_ID}:{family}:{contract['contract_id']}"
            rows.append(
                {
                    "schema": "gp245-cutoff-stage-b-dispatch-v1",
                    "pilot_id": PILOT_ID,
                    "dispatch_id": dispatch_id,
                    "family": family,
                    "runtime_route": RUNTIME_ROUTES.get(family, "manual"),
                    "contract_id": contract["contract_id"],
                    "condition": "tool_free_cutoff_validity",
                    "primitive": "cutoff_validity_stage_b",
                    "cutoff_relation": contract["cutoff_relation"],
                    "source": contract["source"],
                    "topic": contract["topic"],
                    "base_rate_band": contract["base_rate_band"],
                    "question_length_bucket": contract["question_length_bucket"],
                    "resolve_date": contract["resolve_date"],
                    "panel_cutoff_date": contract["panel_cutoff_date"],
                    "source_finding_ids": ["F101"],
                    "expected_json_keys": [
                        "p_success",
                        "confidence",
                        "recognition_self_report",
                        "cutoff_relation",
                        "source",
                        "topic",
                        "base_rate_band",
                        "source_finding_ids",
                        "rationale_short",
                    ],
                    "prompt": build_prompt(contract),
                }
            )
    return rows


def relation_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(row["cutoff_relation"] for row in rows))


def stratum_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((row["stratum_key"], row["cutoff_relation"]) for row in rows)
    keys = sorted({row["stratum_key"] for row in rows})
    return [
        {
            "stratum_key": key,
            "pre_n": counts.get((key, "pre_cutoff"), 0),
            "post_n": counts.get((key, "post_cutoff"), 0),
        }
        for key in keys
    ]


def build_freeze(
    db: Path,
    panel_cutoff_date: str,
    *,
    prefer_computed_cutoff: bool,
    families: tuple[str, ...],
) -> dict[str, Any]:
    candidate_rows = build_rows(db, panel_cutoff_date, prefer_computed_cutoff=prefer_computed_cutoff)
    eligible = [row for row in candidate_rows if row["eligible_for_matched_audit"]]
    keys = matched_keys(eligible)
    matched = [row for row in eligible if stratum_key(row) in keys]
    context = load_contract_context(db, {str(row["contract_id"]) for row in matched})
    corpus = [
        enrich_row(row, context.get(str(row["contract_id"]), {}), panel_cutoff_date)
        for row in matched
    ]
    corpus = sorted(corpus, key=lambda r: (r["cutoff_relation"], r["stratum_key"], str(r["contract_id"])))
    minimum_panel = select_balanced_minimum(corpus)
    dispatch = dispatch_rows(minimum_panel, families)
    minimum_counts = relation_counts(minimum_panel)
    corpus_counts = relation_counts(corpus)
    ready = (
        corpus_counts.get("pre_cutoff", 0) >= MIN_STAGE_B_PRE
        and corpus_counts.get("post_cutoff", 0) >= MIN_STAGE_B_POST
        and minimum_counts.get("pre_cutoff", 0) >= MIN_STAGE_B_PRE
        and minimum_counts.get("post_cutoff", 0) >= MIN_STAGE_B_POST
        and len(dispatch) == len(minimum_panel) * len(families)
    )
    unknown_base_rate = sum(1 for row in minimum_panel if row["base_rate_band"] == "unknown")
    report = {
        "schema": "gp245-cutoff-stage-b-freeze-v1",
        "db": str(db),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pilot_id": PILOT_ID,
        "panel_cutoff_date": panel_cutoff_date,
        "prefer_computed_cutoff": prefer_computed_cutoff,
        "families": list(families),
        "verdict": "ready_for_constrained_dispatch" if ready else "not_ready_for_dispatch",
        "ready_for_dispatch": ready,
        "full_candidate_corpus": {
            "contracts": len(corpus),
            "counts_by_relation": corpus_counts,
            "strata": stratum_table(corpus),
            "sha256": sha256_rows(corpus),
        },
        "minimum_balanced_panel": {
            "contracts": len(minimum_panel),
            "counts_by_relation": minimum_counts,
            "strata": stratum_table(minimum_panel),
            "sha256": sha256_rows(minimum_panel),
        },
        "dispatch_slate": {
            "rows": len(dispatch),
            "families": list(families),
            "sha256": sha256_rows(dispatch),
        },
        "matching_limitations": {
            "matched_dimensions": ["source", "topic", "question_length_bucket", "computed_cutoff_relation"],
            "not_yet_matched_dimensions": ["base_rate_band"],
            "minimum_panel_unknown_base_rate_contracts": unknown_base_rate,
            "interpretation": (
                "The DB currently lacks reliable base-rate fields for these rows. "
                "This panel freezes the available strict matched corpus and must report "
                "base-rate matching as a limitation unless base-rate metadata is repaired."
            ),
        },
        "kill_switches_before_calls": [
            "Do not dispatch if any prompt includes y_known or resolution outcome.",
            "Do not dispatch with web, retrieval, or browsing tools enabled.",
            "Do not promote Law 3 from this freeze alone; only scored matched calls can validate it.",
        ],
        "artifacts": {
            "full_candidate_corpus_jsonl": "cutoff_stage_b_frozen_corpus.jsonl",
            "minimum_balanced_panel_jsonl": "cutoff_stage_b_minimum_panel_contracts.jsonl",
            "dispatch_slate_jsonl": "cutoff_stage_b_dispatch_slate.jsonl",
        },
    }
    return {
        "report": report,
        "corpus": corpus,
        "minimum_panel": minimum_panel,
        "dispatch": dispatch,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = result["report"]
    (out_dir / "cutoff_stage_b_freeze_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_jsonl(out_dir / "cutoff_stage_b_frozen_corpus.jsonl", result["corpus"])
    write_jsonl(out_dir / "cutoff_stage_b_minimum_panel_contracts.jsonl", result["minimum_panel"])
    write_jsonl(out_dir / "cutoff_stage_b_dispatch_slate.jsonl", result["dispatch"])

    lines = [
        "# Cutoff Stage-B Freeze Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Panel cutoff date: `{report['panel_cutoff_date']}`",
        f"- Families: `{', '.join(report['families'])}`",
        f"- Full candidate corpus: {report['full_candidate_corpus']['counts_by_relation']}",
        f"- Minimum balanced panel: {report['minimum_balanced_panel']['counts_by_relation']}",
        f"- Dispatch rows: {report['dispatch_slate']['rows']}",
        "",
        "## Matched Strata",
        "",
    ]
    for row in report["minimum_balanced_panel"]["strata"]:
        lines.append(f"- `{row['stratum_key']}`: pre={row['pre_n']}, post={row['post_n']}")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            f"- Matched dimensions: `{report['matching_limitations']['matched_dimensions']}`",
            f"- Not yet matched: `{report['matching_limitations']['not_yet_matched_dimensions']}`",
            f"- Unknown base-rate contracts in minimum panel: {report['matching_limitations']['minimum_panel_unknown_base_rate_contracts']}",
            "",
            report["matching_limitations"]["interpretation"],
            "",
            "## Kill Switches Before Calls",
            "",
        ]
    )
    for item in report["kill_switches_before_calls"]:
        lines.append(f"- {item}")
    lines.append("")
    (out_dir / "cutoff_stage_b_freeze_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff-date", default="2025-10-01")
    parser.add_argument("--families", default=",".join(DEFAULT_FAMILIES))
    parser.add_argument("--prefer-computed-cutoff", action="store_true", default=True)
    parser.add_argument("--use-stored-cutoff", action="store_true")
    args = parser.parse_args()
    families = tuple(item.strip() for item in args.families.split(",") if item.strip())
    result = build_freeze(
        args.db,
        args.panel_cutoff_date,
        prefer_computed_cutoff=not args.use_stored_cutoff,
        families=families,
    )
    print(json.dumps(result["report"], indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0 if result["report"]["ready_for_dispatch"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
