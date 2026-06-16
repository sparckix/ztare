#!/usr/bin/env python3
"""Build a source-valid public-corpus structured-metacognition packet.

No model calls. No DB mutation. The output is a deterministic dispatch queue
for testing whether structured metacognition improves forecast probabilities
over bare and placebo prompts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "structured_metacognition_v1/workspace"
PILOT_ID = "structured_metacognition_public_v1"

ARMS = [
    {
        "arm": "A",
        "condition": "bare_forecast",
        "instruction": "Emit only the probability that the event resolves YES.",
        "required_output_fields": ["p_success"],
    },
    {
        "arm": "B",
        "condition": "length_matched_placebo",
        "instruction": (
            "Use concise numbered formatting and then emit the probability that "
            "the event resolves YES. Do not apply a special forecasting method."
        ),
        "required_output_fields": ["format_check", "p_success"],
    },
    {
        "arm": "C",
        "condition": "expert_training_prompt",
        "instruction": (
            "Estimate a base rate, update from the contract wording and source, "
            "state the main uncertainty, then emit the probability that the event resolves YES."
        ),
        "required_output_fields": ["base_rate", "update_reason", "main_uncertainty", "p_success"],
    },
    {
        "arm": "D",
        "condition": "audit_informed_prompt",
        "instruction": (
            "Check source visibility, label vintage, base rate, and overconfidence risk, "
            "then emit the probability that the event resolves YES."
        ),
        "required_output_fields": [
            "source_visibility_check",
            "label_vintage_check",
            "base_rate",
            "overconfidence_check",
            "p_success",
        ],
    },
    {
        "arm": "E",
        "condition": "failure_mode_specific_prompt",
        "instruction": (
            "Name the most likely forecasting error for this contract class, revise only "
            "if that check changes the probability, then emit the probability that the event resolves YES."
        ),
        "required_output_fields": ["likely_error", "revision_reason", "p_success"],
    },
]

RUNTIME_BY_FAMILY = {
    "claude": "claude_subscription",
    "codex_55": "codex_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}


def csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def horizon_fields(row: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in str(row.get("horizon") or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def display_question(row: dict[str, Any]) -> str:
    question = str(row.get("question") or "")
    fields = horizon_fields(row)
    if "{forecast_due_date}" in question and fields.get("forecast_due"):
        question = question.replace("{forecast_due_date}", fields["forecast_due"])
    if "{resolution_date}" in question and fields.get("resolution"):
        question = question.replace("{resolution_date}", fields["resolution"])
    return question


def load_candidates(db: Path, sources: tuple[str, ...]) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT contract_id, question, source, source_corpus, post_training_cutoff,
                   y_known, task_type, resolution_source_url, horizon, raw_json
            FROM contracts
            WHERE y_known IN (0, 1)
              AND post_training_cutoff = 1
              AND source IS NOT NULL
              AND question IS NOT NULL
              AND LENGTH(TRIM(question)) >= 20
            ORDER BY source, contract_id
            """
        )
    ]
    con.close()
    out: list[dict[str, Any]] = []
    source_set = set(sources)
    for row in rows:
        if row.get("source") not in source_set:
            continue
        question = str(row.get("question") or "").strip()
        if question.startswith("Premium clean contract "):
            continue
        out.append(row)
    return out


def select_contracts(candidates: list[dict[str, Any]], *, per_source: int) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_source[str(row["source"])].append(row)

    picked_by_source: dict[str, list[dict[str, Any]]] = {}
    for source in sorted(by_source):
        rows = sorted(by_source[source], key=lambda row: str(row["contract_id"]))
        yes = [row for row in rows if int(row["y_known"]) == 1]
        no = [row for row in rows if int(row["y_known"]) == 0]
        half = per_source // 2
        picked = yes[:half] + no[: per_source - half]
        if len(picked) < per_source:
            seen = {row["contract_id"] for row in picked}
            picked.extend([row for row in rows if row["contract_id"] not in seen][: per_source - len(picked)])
        picked_by_source[source] = picked[:per_source]

    selected: list[dict[str, Any]] = []
    source_order = sorted(picked_by_source)
    for idx in range(per_source):
        for source in source_order:
            rows = picked_by_source[source]
            if idx < len(rows):
                selected.append(rows[idx])
    return selected


def prompt_contract(arm: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "source_valid_primary_endpoint": True,
        "instruction": arm["instruction"],
        "required_output_fields": arm["required_output_fields"],
        "scoring": {
            "primary": "paired_brier",
            "compare_to": [
                "bare_forecast",
                "length_matched_placebo",
                "confident_no_adjustment_when_defined",
                "equal_information_market_when_available",
            ],
        },
        "contract_metadata_visible": {
            "contract_id": contract["contract_id"],
            "source": contract["source"],
            "source_corpus": contract.get("source_corpus"),
            "task_type": contract.get("task_type"),
            "horizon": contract.get("horizon"),
        },
    }


def dispatch_rows(
    contracts: list[dict[str, Any]], *, families: tuple[str, ...], pilot_id: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contract in contracts:
        for family in families:
            for arm in ARMS:
                key = "|".join([pilot_id, str(contract["contract_id"]), family, arm["condition"]])
                rows.append(
                    {
                        "dispatch_id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                        "pilot_id": pilot_id,
                        "contract_id": contract["contract_id"],
                        "family": family,
                        "agent_id": family,
                        "runtime_route": RUNTIME_BY_FAMILY.get(family, "manual_or_registered_runtime"),
                        "arm": arm["arm"],
                        "condition": arm["condition"],
                        "question": display_question(contract),
                        "source": contract["source"],
                        "source_corpus": contract.get("source_corpus"),
                        "post_training_cutoff": contract.get("post_training_cutoff"),
                        "include_y_known": False,
                        "prompt_contract": prompt_contract(arm, contract),
                    }
                )
    return rows


def report(
    *, selected: list[dict[str, Any]], rows: list[dict[str, Any]], families: tuple[str, ...], sources: tuple[str, ...]
) -> dict[str, Any]:
    source_counts = Counter(str(row["source"]) for row in selected)
    outcome_counts = Counter(str(int(row["y_known"])) for row in selected)
    arm_counts = Counter(str(row["condition"]) for row in rows)
    return {
        "schema": "structured-metacognition-public-packet-v1",
        "pilot_id": PILOT_ID,
        "status": "dispatch_queue_prepared",
        "sources_requested": list(sources),
        "families": list(families),
        "contracts": len(selected),
        "dispatch_rows": len(rows),
        "source_counts": dict(source_counts),
        "outcome_counts": dict(outcome_counts),
        "arm_counts": dict(arm_counts),
        "primary_endpoint": "paired Brier improvement over bare forecast and length-matched placebo on the same source-valid contracts",
        "promotion_rule": [
            "beats bare forecast and placebo on paired Brier",
            "survives source-stratified reporting",
            "does not regress badly on any major source",
            "beats or complements confident-NO on eligible rows",
        ],
        "stop_rule": [
            "only beats bare prompt but not placebo",
            "improves one source while regressing another",
            "loses to confident-NO on the same rows",
            "gain disappears after label-time repair",
        ],
    }


def render_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Structured Metacognition Public-Corpus Dispatch Packet",
        "",
        f"- Pilot ID: `{summary['pilot_id']}`",
        f"- Status: `{summary['status']}`",
        f"- Contracts: `{summary['contracts']}`",
        f"- Dispatch rows: `{summary['dispatch_rows']}`",
        f"- Families: `{', '.join(summary['families'])}`",
        f"- Primary endpoint: {summary['primary_endpoint']}",
        "",
        "Source counts:",
        "```json",
        json.dumps(summary["source_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "Outcome counts:",
        "```json",
        json.dumps(summary["outcome_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "Promotion rule:",
    ]
    for item in summary["promotion_rule"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Stop rule:")
    for item in summary["stop_rule"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sources", default="manifold,polymarket,fred")
    parser.add_argument("--per-source", type=int, default=40)
    parser.add_argument("--families", default="gemini")
    parser.add_argument("--pilot-id", default=PILOT_ID)
    args = parser.parse_args()

    sources = csv_tuple(args.sources)
    families = csv_tuple(args.families)
    candidates = load_candidates(args.db, sources)
    selected = select_contracts(candidates, per_source=args.per_source)
    rows = dispatch_rows(selected, families=families, pilot_id=args.pilot_id)
    summary = report(selected=selected, rows=rows, families=families, sources=sources)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    queue_path = args.out_dir / f"{args.pilot_id}_dispatch_queue.jsonl"
    json_path = args.out_dir / f"{args.pilot_id}_packet.json"
    md_path = args.out_dir / f"{args.pilot_id}_packet.md"
    queue_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(summary), encoding="utf-8")
    print(json.dumps({"queue": str(queue_path), "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
