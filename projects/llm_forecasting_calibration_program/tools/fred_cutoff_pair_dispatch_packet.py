#!/usr/bin/env python3
"""Build a frozen paired FRED pre/post cutoff dispatch packet."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PRE = WORKSPACE / "fred_pre_cutoff_companion_2026_06_04/fred_pre_cutoff_companion_contract_rows.jsonl"
DEFAULT_POST = WORKSPACE / "fred_forecastbench_manifest_2026_06_04/fred_forecastbench_contract_rows.jsonl"
DEFAULT_OUT = WORKSPACE / "fred_cutoff_pair_packet_2026_06_04"
DEFAULT_PILOT_ID = "fred_cutoff_pair_tool_free_v1"
FAMILIES = {
    "claude": "claude_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def concrete_question(row: dict[str, Any]) -> str:
    question = str(row.get("question") or "")
    return (
        question.replace("{forecast_due_date}", str(row.get("forecast_due_date")))
        .replace("{resolution_date}", str(row.get("resolution_date")))
        .strip()
    )


def length_bucket(question: str) -> str:
    n = len(question)
    if n < 80:
        return "short"
    if n < 180:
        return "medium"
    return "long"


def prompt(row: dict[str, Any], cutoff_relation: str) -> str:
    q = concrete_question(row)
    return (
        "You are making a tool-free binary forecast. Do not browse, search, or use external tools.\n"
        "Estimate the probability that the event described by the question resolved YES.\n"
        "Return only a JSON object with keys: p_success, confidence, recognition_self_report, "
        "cutoff_relation, source, topic, base_rate_band, source_finding_ids, rationale_short.\n\n"
        f"Question: {q}\n"
        "Source: fred\n"
        "Topic: economics\n"
        f"Cutoff relation to echo: {cutoff_relation}\n"
        "Base-rate band to echo: unknown\n\n"
        "Definitions: p_success is a number in [0,1]. confidence is your confidence in that probability, "
        "in [0,1]. recognition_self_report is how much you believe you recognize this exact resolved "
        "question or answer from memory, in [0,1]. source_finding_ids must be [\"FRED_PAIR_V1\"]. "
        "Keep rationale_short under 40 words."
    )


def dispatch_row(row: dict[str, Any], *, pilot_id: str, family: str, cutoff_relation: str) -> dict[str, Any]:
    q = concrete_question(row)
    return {
        "schema": "gp245-fred-cutoff-pair-dispatch-v1",
        "pilot_id": pilot_id,
        "dispatch_id": f"{pilot_id}:{family}:{row['contract_id']}",
        "contract_id": row["contract_id"],
        "paired_contract_id": row.get("paired_post_contract_id") or row.get("paired_pre_contract_id"),
        "family": family,
        "runtime_route": FAMILIES[family],
        "condition": "tool_free_fred_cutoff_pair",
        "primitive": "cutoff_validity_fred_pair",
        "cutoff_relation": cutoff_relation,
        "source": "fred",
        "topic": "economics",
        "base_rate_band": "unknown",
        "question_length_bucket": length_bucket(q),
        "resolve_date": row.get("resolution_date"),
        "panel_cutoff_date": "2025-10-01",
        "source_finding_ids": ["FRED_PAIR_V1"],
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
        "prompt": prompt(row, cutoff_relation),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    pre_rows = load_jsonl(args.pre_contracts)
    post_rows = load_jsonl(args.post_contracts)
    pre_by_series = {str(row.get("series_id")): row for row in pre_rows}
    post_by_series = {str(row.get("series_id")): row for row in post_rows}
    series_ids = sorted(set(pre_by_series) & set(post_by_series))
    if args.max_pairs >= 0:
        series_ids = series_ids[: args.max_pairs]
    families = args.family or list(FAMILIES)
    invalid = sorted(set(families) - set(FAMILIES))
    if invalid:
        raise SystemExit(f"unknown families: {', '.join(invalid)}")
    queue: list[dict[str, Any]] = []
    answer_rows: list[dict[str, Any]] = []
    for series_id in series_ids:
        pre = pre_by_series[series_id]
        post = post_by_series[series_id]
        pre["paired_post_contract_id"] = post["contract_id"]
        post["paired_pre_contract_id"] = pre["contract_id"]
        for source_row, cutoff_relation in ((pre, "pre_cutoff"), (post, "post_cutoff")):
            answer_rows.append(
                {
                    "contract_id": source_row["contract_id"],
                    "paired_contract_id": source_row.get("paired_post_contract_id")
                    or source_row.get("paired_pre_contract_id"),
                    "series_id": source_row.get("series_id"),
                    "cutoff_relation": cutoff_relation,
                    "question": concrete_question(source_row),
                    "y_known": int(source_row["y_known"]),
                    "forecast_due_date": source_row.get("forecast_due_date"),
                    "resolution_date": source_row.get("resolution_date"),
                    "due_observation": source_row.get("due_observation"),
                    "resolution_observation": source_row.get("resolution_observation"),
                    "y_known_provenance": source_row.get("y_known_provenance"),
                }
            )
            for family in families:
                queue.append(dispatch_row(source_row, pilot_id=args.pilot_id, family=family, cutoff_relation=cutoff_relation))
    by_relation = Counter(row["cutoff_relation"] for row in answer_rows)
    by_outcome = Counter(str(row["y_known"]) for row in answer_rows)
    return {
        "schema": "gp245-fred-cutoff-pair-packet-v1",
        "pilot_id": args.pilot_id,
        "pre_contracts": str(args.pre_contracts.relative_to(REPO)),
        "post_contracts": str(args.post_contracts.relative_to(REPO)),
        "paired_series": len(series_ids),
        "contract_rows": len(answer_rows),
        "dispatch_rows": len(queue),
        "families": families,
        "relation_counts": dict(sorted(by_relation.items())),
        "outcome_counts": dict(sorted(by_outcome.items())),
        "nonadaptive_rule": "intersection of verified post ForecastBench FRED rows and fixed one-year pre companions; sorted series order",
        "queue": queue,
        "answer_key": answer_rows,
    }


def render_md(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# FRED Cutoff Pair Dispatch Packet",
            "",
            f"- Pilot ID: `{packet['pilot_id']}`",
            f"- Paired series: `{packet['paired_series']}`",
            f"- Contract rows: `{packet['contract_rows']}`",
            f"- Dispatch rows: `{packet['dispatch_rows']}`",
            f"- Families: `{packet['families']}`",
            f"- Relation counts: `{packet['relation_counts']}`",
            f"- Outcome counts: `{packet['outcome_counts']}`",
            f"- Nonadaptive rule: {packet['nonadaptive_rule']}",
            "",
            "This packet freezes the paired official-data slate before model calls. It is not outcome evidence until dispatch receipts are scored.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-contracts", type=Path, default=DEFAULT_PRE)
    parser.add_argument("--post-contracts", type=Path, default=DEFAULT_POST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--family", action="append")
    parser.add_argument("--max-pairs", type=int, default=-1)
    args = parser.parse_args()
    packet = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_cutoff_pair_packet.json").write_text(
        json.dumps({k: v for k, v in packet.items() if k not in {"queue", "answer_key"}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "fred_cutoff_pair_packet.md").write_text(render_md(packet), encoding="utf-8")
    with (args.out_dir / "fred_cutoff_pair_dispatch_queue.jsonl").open("w", encoding="utf-8") as fh:
        for row in packet["queue"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.out_dir / "fred_cutoff_pair_answer_key.jsonl").open("w", encoding="utf-8") as fh:
        for row in packet["answer_key"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {k: packet[k] for k in ("pilot_id", "paired_series", "contract_rows", "dispatch_rows", "relation_counts", "outcome_counts")},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
