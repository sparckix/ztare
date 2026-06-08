#!/usr/bin/env python3
"""Law 3 Stage-C base-rate repair packet.

No-call audit of the frozen Stage-B cutoff-validity panel. It determines
whether the base-rate limitation can be repaired from local DB fields alone,
and writes the next acquisition/scoring packet.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PANEL = WORKSPACE / "cutoff_stage_b_minimum_panel_contracts.jsonl"
DEFAULT_OUT = WORKSPACE

BASE_RATE_FIELD_NAMES = (
    "base_rate",
    "base_rate_band",
    "market_price",
    "market_price_at_forecast",
    "price_at_forecast",
    "market_consensus",
    "consensus_p_yes",
    "freeze_datetime_value",
    "manifold_probability",
    "probability",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 6) if values else None


def relation_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_relation: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        y = row.get("y_known")
        if y in (0, 1):
            by_relation[str(row.get("cutoff_relation"))].append(int(y))
    return {
        relation: {
            "contracts": len(values),
            "yes_rate": mean([float(v) for v in values]),
            "yes": sum(values),
            "no": len(values) - sum(values),
        }
        for relation, values in sorted(by_relation.items())
    }


def stratum_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        y = row.get("y_known")
        if y in (0, 1):
            groups[(str(row.get("stratum_key")), str(row.get("cutoff_relation")))].append(int(y))
    strata = sorted({key[0] for key in groups})
    out = []
    for stratum in strata:
        pre = groups.get((stratum, "pre_cutoff"), [])
        post = groups.get((stratum, "post_cutoff"), [])
        out.append(
            {
                "stratum_key": stratum,
                "pre_n": len(pre),
                "pre_yes_rate": mean([float(v) for v in pre]),
                "post_n": len(post),
                "post_yes_rate": mean([float(v) for v in post]),
                "post_minus_pre_yes_rate": (
                    round(statistics.mean(post) - statistics.mean(pre), 6)
                    if pre and post
                    else None
                ),
            }
        )
    return out


def db_base_rate_field_audit(db: Path, contract_ids: list[str]) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    placeholders = ",".join("?" for _ in contract_ids)
    found: Counter[str] = Counter()
    raw_key_counter: Counter[str] = Counter()
    missing_contracts = 0
    if not contract_ids:
        return {}
    rows = cur.execute(
        f"SELECT contract_id, raw_json FROM contracts WHERE contract_id IN ({placeholders})",
        contract_ids,
    ).fetchall()
    by_id = {row[0]: parse_json(row[1]) for row in rows}
    for contract_id in contract_ids:
        raw = by_id.get(contract_id)
        if raw is None:
            missing_contracts += 1
            continue
        raw_key_counter.update(raw.keys())
        for field in BASE_RATE_FIELD_NAMES:
            value = raw.get(field)
            if value is not None and value != "unknown":
                found[field] += 1
    con.close()
    return {
        "contracts_checked": len(contract_ids),
        "contracts_missing_from_db": missing_contracts,
        "candidate_base_rate_field_hits": dict(sorted(found.items())),
        "top_raw_json_keys": dict(raw_key_counter.most_common(25)),
    }


def build(db: Path, panel_path: Path) -> dict[str, Any]:
    rows = load_jsonl(panel_path)
    contract_ids = [str(row["contract_id"]) for row in rows]
    base_rate_bands = Counter(str(row.get("base_rate_band")) for row in rows)
    relation = relation_summary(rows)
    pre_rate = relation.get("pre_cutoff", {}).get("yes_rate")
    post_rate = relation.get("post_cutoff", {}).get("yes_rate")
    observed_yes_delta = (
        round(post_rate - pre_rate, 6)
        if isinstance(pre_rate, (int, float)) and isinstance(post_rate, (int, float))
        else None
    )
    db_fields = db_base_rate_field_audit(db, contract_ids)
    local_repair_ready = bool(db_fields.get("candidate_base_rate_field_hits"))
    return {
        "schema": "gp245-cutoff-stage-c-base-rate-repair-packet-v1",
        "panel_path": str(panel_path.relative_to(REPO)),
        "db": str(db),
        "panel_contracts": len(rows),
        "relation_summary": relation,
        "observed_post_minus_pre_yes_rate": observed_yes_delta,
        "base_rate_band_counts": dict(sorted(base_rate_bands.items())),
        "stratum_summary": stratum_summary(rows),
        "db_base_rate_field_audit": db_fields,
        "local_repair_ready": local_repair_ready,
        "verdict": (
            "local_base_rate_repair_ready"
            if local_repair_ready
            else "external_or_historical_base_rate_join_required"
        ),
        "next_packet": {
            "objective": (
                "Join a pre-outcome base-rate proxy for each Stage-B contract, "
                "then rerun the Law 3 post-minus-pre Brier test within base-rate bins."
            ),
            "acceptable_base_rate_sources": [
                "historical Manifold probability at a frozen timestamp",
                "market-implied probability from an official dump with timestamp provenance",
                "pre-registered source-level prior computed without using the row outcome",
            ],
            "unacceptable_repairs": [
                "matching on realized y_known as if it were a prior",
                "adding more unmatched LLM calls",
                "using model self-recognition as a base-rate proxy",
            ],
            "kill_condition": (
                "After base-rate bin matching, post-minus-pre Brier is below 0.02 "
                "or reverses sign."
            ),
            "promotion_condition": (
                "Direction survives within base-rate bins and at least three of "
                "five strata retain post-minus-pre Brier > 0."
            ),
        },
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Cutoff Stage-C Base-Rate Repair Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Panel contracts: {report['panel_contracts']}",
        f"- Verdict: `{report['verdict']}`",
        f"- Local repair ready: `{report['local_repair_ready']}`",
        f"- Observed post-minus-pre YES-rate: `{report['observed_post_minus_pre_yes_rate']}`",
        "",
        "## Relation Summary",
        "",
    ]
    for relation, row in report["relation_summary"].items():
        lines.append(
            f"- `{relation}`: n={row['contracts']}, yes_rate={row['yes_rate']}, "
            f"yes={row['yes']}, no={row['no']}"
        )
    lines.extend(
        [
            "",
            "## Base-Rate Field Audit",
            "",
            f"- `base_rate_band` counts: `{report['base_rate_band_counts']}`",
            f"- Candidate DB field hits: `{report['db_base_rate_field_audit']['candidate_base_rate_field_hits']}`",
            "",
            "## Stratum Outcome Balance",
            "",
        ]
    )
    for row in report["stratum_summary"]:
        lines.append(
            f"- `{row['stratum_key']}`: pre n={row['pre_n']} yes_rate={row['pre_yes_rate']}; "
            f"post n={row['post_n']} yes_rate={row['post_yes_rate']}; "
            f"delta={row['post_minus_pre_yes_rate']}"
        )
    packet = report["next_packet"]
    lines.extend(
        [
            "",
            "## Next Packet",
            "",
            f"- Objective: {packet['objective']}",
            f"- Kill condition: {packet['kill_condition']}",
            f"- Promotion condition: {packet['promotion_condition']}",
            "",
            "Acceptable base-rate sources:",
        ]
    )
    for item in packet["acceptable_base_rate_sources"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Unacceptable repairs:")
    for item in packet["unacceptable_repairs"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args.db, args.panel)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "cutoff_stage_c_base_rate_repair_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "cutoff_stage_c_base_rate_repair_packet.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    print(f"wrote {args.out_dir / 'cutoff_stage_c_base_rate_repair_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
