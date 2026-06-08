#!/usr/bin/env python3
"""Build an outcome-balanced blinded FRED control packet.

The previous FRED cutoff panel exposed the cutoff relation and withheld the
due-date observed value. This packet attacks both confounds on an
outcome-balanced subset: no prompt asks the model to echo pre/post cutoff, and
one arm gives the due-date observation value.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_ANSWER = WORKSPACE / "fred_cutoff_pair_packet_2026_06_04/fred_cutoff_pair_answer_key.jsonl"
DEFAULT_OUT = WORKSPACE / "fred_blinded_value_control_packet_2026_06_04"
DEFAULT_PILOT_ID = "fred_blinded_value_control_v1"
FAMILIES = {
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
    "claude": "claude_subscription",
    "codex_54mini": "codex_subscription",
}
CONDITIONS = {
    "blinded_prior_no_cutoff_label",
    "blinded_value_given_no_cutoff_label",
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


def by_series(answer_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in answer_rows:
        out[str(row["series_id"])][str(row["cutoff_relation"])] = row
    return dict(out)


def balanced_series(series_rows: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    buckets: dict[tuple[int, int], list[str]] = defaultdict(list)
    for series_id, rels in series_rows.items():
        if "pre_cutoff" not in rels or "post_cutoff" not in rels:
            continue
        key = (int(rels["pre_cutoff"]["y_known"]), int(rels["post_cutoff"]["y_known"]))
        buckets[key].append(series_id)
    for values in buckets.values():
        values.sort()
    selected = []
    selected.extend(buckets[(1, 1)][:10])
    selected.extend(buckets[(1, 0)][:2])
    selected.extend(buckets[(0, 1)][:2])
    selected.extend(buckets[(0, 0)][:10])
    return sorted(selected)


def prompt(row: dict[str, Any], condition: str) -> str:
    base = (
        "You are making a tool-free binary forecast. Do not browse, search, or use external tools.\n"
        "Estimate the probability that the event described by the question resolved YES.\n"
        "Return only a JSON object with keys: p_success, confidence, recognition_self_report, "
        "source, topic, base_rate_band, source_finding_ids, rationale_short.\n\n"
        f"Question: {row['question']}\n"
        "Source: fred\n"
        "Topic: economics\n"
    )
    if condition == "blinded_value_given_no_cutoff_label":
        due = row.get("due_observation") or {}
        base += (
            f"Due-date observed value available at forecast time: {due.get('value')} "
            f"on observation date {due.get('date')}.\n"
        )
    base += (
        "\nDefinitions: p_success is a number in [0,1]. confidence is your confidence in that probability, "
        "in [0,1]. recognition_self_report is how much you believe you recognize this exact resolved "
        "question or answer from memory, in [0,1]. source_finding_ids must be [\"FRED_BLIND_VALUE_V1\"]. "
        "Keep rationale_short under 40 words. Do not include any cutoff-relation field."
    )
    return base


def dispatch_row(
    row: dict[str, Any],
    *,
    pilot_id: str,
    family: str,
    condition: str,
) -> dict[str, Any]:
    return {
        "schema": "gp245-fred-blinded-value-control-dispatch-v1",
        "pilot_id": pilot_id,
        "dispatch_id": f"{pilot_id}:{condition}:{family}:{row['contract_id']}",
        "contract_id": row["contract_id"],
        "paired_contract_id": row.get("paired_contract_id"),
        "family": family,
        "runtime_route": FAMILIES[family],
        "condition": condition,
        "primitive": "cutoff_validity_fred_blinded_value_control",
        "cutoff_relation": row["cutoff_relation"],
        "require_cutoff_echo": False,
        "source": "fred",
        "topic": "economics",
        "base_rate_band": "unknown",
        "question_length_bucket": "long" if len(str(row["question"])) >= 180 else "medium",
        "resolve_date": row.get("resolution_date"),
        "panel_cutoff_date": "2025-10-01",
        "source_finding_ids": ["FRED_BLIND_VALUE_V1"],
        "expected_json_keys": [
            "p_success",
            "confidence",
            "recognition_self_report",
            "source",
            "topic",
            "base_rate_band",
            "source_finding_ids",
            "rationale_short",
        ],
        "prompt": prompt(row, condition),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    answer_rows = load_jsonl(args.answer_key)
    series_rows = by_series(answer_rows)
    selected = balanced_series(series_rows)
    families = args.family or ["gemini", "deepseek"]
    conditions = args.condition or sorted(CONDITIONS)
    invalid_families = sorted(set(families) - set(FAMILIES))
    invalid_conditions = sorted(set(conditions) - CONDITIONS)
    if invalid_families:
        raise SystemExit(f"unknown families: {', '.join(invalid_families)}")
    if invalid_conditions:
        raise SystemExit(f"unknown conditions: {', '.join(invalid_conditions)}")
    queue = []
    selected_answers = []
    combo_counts: Counter[str] = Counter()
    relation_outcomes: Counter[str] = Counter()
    for series_id in selected:
        rels = series_rows[series_id]
        combo_counts[f"{rels['pre_cutoff']['y_known']}{rels['post_cutoff']['y_known']}"] += 1
        for relation in ("pre_cutoff", "post_cutoff"):
            row = rels[relation]
            selected_answers.append(row)
            relation_outcomes[f"{relation}|y={row['y_known']}"] += 1
            for condition in conditions:
                for family in families:
                    queue.append(dispatch_row(row, pilot_id=args.pilot_id, family=family, condition=condition))
    return {
        "schema": "gp245-fred-blinded-value-control-packet-v1",
        "pilot_id": args.pilot_id,
        "source_answer_key": str(args.answer_key.relative_to(REPO)),
        "selected_series": selected,
        "selected_series_count": len(selected),
        "contract_rows": len(selected_answers),
        "dispatch_rows": len(queue),
        "families": families,
        "conditions": conditions,
        "pair_outcome_combo_counts": dict(sorted(combo_counts.items())),
        "relation_outcome_counts": dict(sorted(relation_outcomes.items())),
        "selection_rule": (
            "outcome-balanced diagnostic subset: all 10 (pre=1,post=1), all 2 "
            "(pre=1,post=0), first 2 sorted (pre=0,post=1), first 10 sorted "
            "(pre=0,post=0); yields 12 YES/12 NO in both pre and post marginals"
        ),
        "non_claims": [
            "not a prospective natural-distribution estimate because outcomes are used to balance the diagnostic subset",
            "not an equal-information market or human baseline",
            "not a vintage-proof FRED/ALFRED audit",
        ],
        "queue": queue,
        "answer_key": selected_answers,
    }


def render_md(packet: dict[str, Any]) -> str:
    lines = [
        "# FRED Blinded Value Control Packet",
        "",
        f"- Pilot ID: `{packet['pilot_id']}`",
        f"- Selected series: `{packet['selected_series_count']}`",
        f"- Contract rows: `{packet['contract_rows']}`",
        f"- Dispatch rows: `{packet['dispatch_rows']}`",
        f"- Families: `{packet['families']}`",
        f"- Conditions: `{packet['conditions']}`",
        f"- Pair outcome combos: `{packet['pair_outcome_combo_counts']}`",
        f"- Relation outcome counts: `{packet['relation_outcome_counts']}`",
        f"- Selection rule: {packet['selection_rule']}",
        "",
        "## Non-Claims",
        "",
    ]
    lines.extend(f"- {item}" for item in packet["non_claims"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_ANSWER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--family", action="append")
    parser.add_argument("--condition", action="append")
    args = parser.parse_args()
    packet = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "fred_blinded_value_control_packet.json").write_text(
        json.dumps({k: v for k, v in packet.items() if k not in {"queue", "answer_key"}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "fred_blinded_value_control_packet.md").write_text(render_md(packet), encoding="utf-8")
    with (args.out_dir / "fred_blinded_value_control_dispatch_queue.jsonl").open("w", encoding="utf-8") as fh:
        for row in packet["queue"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.out_dir / "fred_blinded_value_control_answer_key.jsonl").open("w", encoding="utf-8") as fh:
        for row in packet["answer_key"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {k: packet[k] for k in ("pilot_id", "selected_series_count", "contract_rows", "dispatch_rows", "pair_outcome_combo_counts", "relation_outcome_counts")},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
