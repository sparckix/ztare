#!/usr/bin/env python3
"""Build a source-balanced F47 contrastive consumer confirmation packet.

This prepares a future same-source A/B contrastive packet. Dispatch rows do not
contain outcomes; the answer key is written separately for scoring.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_QUEUE = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_dispatch_queue.jsonl"
DEFAULT_KEY = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_answer_key.json"
DEFAULT_REPORT = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_report.md"

SOURCE_TARGETS = {
    "manifold": 8,
    "polymarket": 8,
    "premium_public_clean": 4,
    "corpus_v22": 4,
}


def source_bucket(row: sqlite3.Row) -> str:
    source = str(row["source"] or "")
    if source:
        return source
    return str(row["source_corpus"] or "unknown")


def length_bucket(question: str) -> str:
    n = len(question)
    if n < 90:
        return "short"
    if n < 220:
        return "medium"
    return "long"


def load_contracts(db_path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT contract_id, question, source, source_corpus, y_known,
                   task_type, horizon
            FROM contracts
            WHERE y_known IS NOT NULL
              AND question IS NOT NULL
            """
        ).fetchall()
    finally:
        con.close()
    out: list[dict[str, Any]] = []
    for row in rows:
        question = str(row["question"] or "")
        out.append(
            {
                "contract_id": str(row["contract_id"]),
                "question": question,
                "source": source_bucket(row),
                "source_raw": row["source"],
                "source_corpus": row["source_corpus"],
                "y_known": int(row["y_known"]),
                "task_type": row["task_type"] or "",
                "horizon": row["horizon"] or "",
                "question_len": len(question),
                "question_length_bucket": length_bucket(question),
            }
        )
    return out


def nearest_pairs(rows: list[dict[str, Any]], target_n: int) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    positives = sorted([r for r in rows if r["y_known"] == 1], key=lambda r: (r["question_len"], r["contract_id"]))
    negatives = sorted([r for r in rows if r["y_known"] == 0], key=lambda r: (r["question_len"], r["contract_id"]))
    used_pos: set[str] = set()
    used_neg: set[str] = set()
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

    candidates: list[tuple[int, int, str, dict[str, Any], dict[str, Any]]] = []
    for pos in positives:
        for neg in negatives:
            same_bucket = int(pos["question_length_bucket"] != neg["question_length_bucket"])
            len_gap = abs(pos["question_len"] - neg["question_len"])
            task_gap = int(pos["task_type"] != neg["task_type"])
            candidates.append((same_bucket, task_gap, len_gap, pos["contract_id"], pos, neg))
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    for _, _, _, _, pos, neg in candidates:
        if len(pairs) >= target_n:
            break
        if pos["contract_id"] in used_pos or neg["contract_id"] in used_neg:
            continue
        used_pos.add(pos["contract_id"])
        used_neg.add(neg["contract_id"])
        pairs.append((pos, neg))
    return pairs


def build_packet(contracts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in contracts:
        by_source[row["source"]].append(row)

    dispatch: list[dict[str, Any]] = []
    answer_key: list[dict[str, Any]] = []
    source_reports: dict[str, Any] = {}
    pair_index = 0

    for source, target_n in SOURCE_TARGETS.items():
        pairs = nearest_pairs(by_source.get(source, []), target_n)
        source_reports[source] = {
            "target_pairs": target_n,
            "selected_pairs": len(pairs),
            "available_yes": sum(1 for r in by_source.get(source, []) if r["y_known"] == 1),
            "available_no": sum(1 for r in by_source.get(source, []) if r["y_known"] == 0),
        }
        for local_i, (yes_row, no_row) in enumerate(pairs):
            pair_index += 1
            # Alternate orientation so position is not a label.
            if local_i % 2 == 0:
                a, b = yes_row, no_row
            else:
                a, b = no_row, yes_row
            pair_id = f"f47_consumer_{pair_index:03d}_{source}"
            dispatch.append(
                {
                    "pair_id": pair_id,
                    "source": source,
                    "question_length_bucket_a": a["question_length_bucket"],
                    "question_length_bucket_b": b["question_length_bucket"],
                    "contract_a": {
                        "contract_id": a["contract_id"],
                        "question": a["question"],
                        "task_type": a["task_type"],
                        "horizon": a["horizon"],
                    },
                    "contract_b": {
                        "contract_id": b["contract_id"],
                        "question": b["question"],
                        "task_type": b["task_type"],
                        "horizon": b["horizon"],
                    },
                    "required_output_fields": [
                        "p_success_a",
                        "p_success_b",
                        "predicted_delta",
                        "delta_driver",
                        "rationale_short",
                    ],
                    "scoring_endpoint": "pairwise_choose_higher_probability_utility",
                }
            )
            answer_key.append(
                {
                    "pair_id": pair_id,
                    "source": source,
                    "contract_id_a": a["contract_id"],
                    "contract_id_b": b["contract_id"],
                    "y_a": a["y_known"],
                    "y_b": b["y_known"],
                    "actual_delta": a["y_known"] - b["y_known"],
                }
            )

    report = {
        "packet": "f47_source_balanced_consumer_packet",
        "date": "2026-06-03",
        "dispatch_rows": len(dispatch),
        "unique_pairs": len(dispatch),
        "non_tie_pairs_by_construction": sum(1 for row in answer_key if row["actual_delta"] != 0),
        "source_targets": SOURCE_TARGETS,
        "source_reports": source_reports,
        "orientation_balance": {
            "a_yes": sum(1 for row in answer_key if row["y_a"] == 1),
            "a_no": sum(1 for row in answer_key if row["y_a"] == 0),
        },
        "validity_note": (
            "Dispatch queue omits outcomes. This is a future confirmation packet, "
            "not fresh evidence until model calls are fired and scored."
        ),
    }
    return dispatch, answer_key, report


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def write_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# F47 source-balanced consumer confirmation packet - 2026-06-03",
        "",
        "This is a packet skeleton, not new model evidence. It creates same-source opposite-outcome A/B pairs for a future contrastive consumer confirmation.",
        "",
        f"- Dispatch rows / unique pairs: `{report['dispatch_rows']}`",
        f"- Non-tie pairs by construction: `{report['non_tie_pairs_by_construction']}`",
        f"- Orientation balance: A-YES `{report['orientation_balance']['a_yes']}`, A-NO `{report['orientation_balance']['a_no']}`",
        "",
        "## Source Allocation",
        "",
        "| source | target | selected | available YES | available NO |",
        "|---|---:|---:|---:|---:|",
    ]
    for source, row in report["source_reports"].items():
        lines.append(
            f"| {source} | {row['target_pairs']} | {row['selected_pairs']} | {row['available_yes']} | {row['available_no']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Dispatch queue: `{DEFAULT_QUEUE}`",
            f"- Answer key: `{DEFAULT_KEY}`",
            "",
            "Smallest valid use: fire the same prompt across target families, score pairwise utility on unique pairs, and compare against random, always-A/B, and source/template controls. Do not use this as evidence until calls exist.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    dispatch, answer_key, report = build_packet(load_contracts(args.db))
    write_jsonl(dispatch, args.queue)
    args.answer_key.write_text(json.dumps({"answer_key": answer_key, "report": report}, indent=2, sort_keys=True) + "\n")
    write_report(report, args.report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
