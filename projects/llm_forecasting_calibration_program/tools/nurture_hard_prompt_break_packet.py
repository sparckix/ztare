#!/usr/bin/env python3
"""Build the N10 hard-prompt-break forecasting packet.

No model calls. No DB mutation. This packet tests a stricter hypothesis than
N9: whether forcing a carrier-only first stage, with no final probability
allowed, improves forecasting relative to immediate probability/prose and
single-turn typed carrier generation.
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
DEFAULT_OUT = PROGRAM / "nurture_intervention_v1/workspace"
PILOT_ID = "n10_hard_prompt_break_v1"

ARMS = [
    {
        "arm": "A",
        "condition": "baseline",
        "instruction": "Emit only a probability for the event resolving YES.",
        "tests": "immediate probability baseline",
    },
    {
        "arm": "B",
        "condition": "free_prose_forecast",
        "instruction": "Write a concise ordinary rationale, then emit p_success.",
        "tests": "ordinary solution-prose path",
    },
    {
        "arm": "C",
        "condition": "single_turn_typed_carrier_forecast",
        "instruction": "Fill typed carrier fields and p_success in one JSON object.",
        "tests": "typed schema without a true prompt break",
    },
    {
        "arm": "D",
        "condition": "hard_prompt_break_carrier_then_forecast",
        "instruction": (
            "Stage 1 emits only source facts, residual/evidence carrier, nearest "
            "confuser, action program, and deterministic check. Stage 1 must not "
            "emit p_success. Stage 2 receives the frozen carrier and emits p_success."
        ),
        "tests": "true carrier-only prompt break before probability execution",
    },
    {
        "arm": "E",
        "condition": "two_stage_free_prose_then_forecast",
        "instruction": (
            "Stage 1 emits only ordinary prose rationale and failure modes. "
            "Stage 1 must not emit p_success. Stage 2 receives the frozen prose "
            "and emits p_success."
        ),
        "tests": "two-call placebo control without a typed evidence carrier",
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


def load_contract_candidates(db: Path, sources: tuple[str, ...]) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT contract_id, question, source, source_corpus, post_training_cutoff,
                   y_known, task_type, resolution_source_url, raw_json
            FROM contracts
            WHERE y_known IN (0, 1)
              AND source IS NOT NULL
              AND question IS NOT NULL
            ORDER BY source, post_training_cutoff DESC, contract_id
            """
        )
    ]
    con.close()
    out: list[dict[str, Any]] = []
    for row in rows:
        question = str(row.get("question") or "").strip()
        if row.get("source") not in sources:
            continue
        if len(question) < 30:
            continue
        if question.startswith("Premium clean contract "):
            continue
        out.append(row)
    return out


def select_contracts(candidates: list[dict[str, Any]], *, per_source: int) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_source[str(row["source"])].append(row)
    selected: list[dict[str, Any]] = []
    for source in sorted(by_source):
        source_rows = by_source[source]
        yes_rows = [row for row in source_rows if int(row["y_known"]) == 1]
        no_rows = [row for row in source_rows if int(row["y_known"]) == 0]
        half = per_source // 2
        picked = yes_rows[:half] + no_rows[: per_source - half]
        if len(picked) < per_source:
            seen = {row["contract_id"] for row in picked}
            picked.extend([row for row in source_rows if row["contract_id"] not in seen][: per_source - len(picked)])
        selected.extend(picked[:per_source])
    return selected


def carrier_contract_for(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "hard_prompt_break": True,
        "stage1_forbids_final_probability": True,
        "field_order_intent": [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
        ],
        "source_fact_rule": "Use only the question text, source label, corpus label, and date/horizon clues visible in the prompt.",
        "nearest_confuser_rule": "Name the wrong contract class most likely to pull probability in the wrong direction.",
        "action_program_rule": "State the compact decision procedure that will later set p_success from the carrier fields.",
        "deterministic_check_rule": "State the final consistency check to run before probability emission.",
        "outcome_hidden": True,
        "target_contract_id": contract["contract_id"],
    }


def prompt_contract_for(arm: dict[str, str], contract: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": arm["instruction"],
        "tests": arm["tests"],
        "required_output_fields": ["p_success"],
    }
    if arm["condition"] == "free_prose_forecast":
        payload["required_output_fields"] = ["p_success", "rationale_short", "failure_modes_short"]
    if arm["condition"] == "single_turn_typed_carrier_forecast":
        payload["carrier_contract"] = carrier_contract_for(contract)
        payload["carrier_contract"]["stage1_forbids_final_probability"] = False
        payload["required_output_fields"] = [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
            "p_success",
        ]
    if arm["condition"] == "hard_prompt_break_carrier_then_forecast":
        payload["carrier_contract"] = carrier_contract_for(contract)
        payload["stage_plan"] = [
            {
                "stage": "carrier_only",
                "forbidden_fields": ["p_success", "final_probability", "forecast_probability"],
                "required_output_fields": [
                    "source_facts",
                    "residual_evidence_carrier",
                    "nearest_confuser",
                    "action_program",
                    "deterministic_check",
                ],
            },
            {
                "stage": "execute_frozen_carrier",
                "required_output_fields": ["p_success", "stage2_execution_check"],
            },
        ]
        payload["required_output_fields"] = [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
            "p_success",
            "stage2_execution_check",
        ]
    if arm["condition"] == "two_stage_free_prose_then_forecast":
        payload["stage_plan"] = [
            {
                "stage": "prose_only",
                "forbidden_fields": ["p_success", "final_probability", "forecast_probability"],
                "required_output_fields": ["rationale_short", "failure_modes_short"],
            },
            {
                "stage": "execute_frozen_prose",
                "required_output_fields": ["p_success", "stage2_execution_check"],
            },
        ]
        payload["required_output_fields"] = [
            "rationale_short",
            "failure_modes_short",
            "p_success",
            "stage2_execution_check",
        ]
    return payload


def dispatch_rows(contracts: list[dict[str, Any]], *, families: tuple[str, ...], pilot_id: str) -> list[dict[str, Any]]:
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
                        "primitive": "n10_hard_prompt_break",
                        "question": contract["question"],
                        "source": contract["source"],
                        "source_corpus": contract["source_corpus"],
                        "post_training_cutoff": contract["post_training_cutoff"],
                        "resolution_source_url": contract["resolution_source_url"],
                        "prompt_contract": prompt_contract_for(arm, contract),
                    }
                )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def sha256_jsonl(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows).encode("utf-8")
    ).hexdigest()


def report_for(
    *,
    pilot_id: str,
    contracts: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    queue_path: Path,
    sources: tuple[str, ...],
    families: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "gp245-n10-hard-prompt-break-packet-v1",
        "pilot_id": pilot_id,
        "queue_path": str(queue_path.relative_to(REPO)),
        "queue_sha256": sha256_jsonl(rows),
        "contracts": len(contracts),
        "dispatch_rows": len(rows),
        "families": list(families),
        "sources_requested": list(sources),
        "source_mix": dict(Counter(str(row["source"]) for row in contracts)),
        "outcome_mix_hidden_from_prompt": dict(Counter(int(row["y_known"]) for row in contracts)),
        "condition_mix": dict(Counter(str(row["condition"]) for row in rows)),
        "arms": ARMS,
        "amnesia_prior_findings": [
            "F19/F22: ordinary rationale transfer does not systematically improve Brier.",
            "N9: single-turn typed carrier weakly beat free prose but did not establish applied action value.",
            "docs/public_claim_register: typed contracts transfer source-bound intent in artifact-only consumer tasks.",
        ],
        "non_duplication_claim": (
            "N10 is not another N9 replicate. N9 emitted carrier and p_success in the same completion; "
            "N10's D arm forbids p_success in Stage 1 and freezes the carrier before execution."
        ),
        "promotion_rule": (
            "Promote only if hard_prompt_break_carrier_then_forecast beats baseline, free_prose_forecast, "
            "single_turn_typed_carrier_forecast, and two_stage_free_prose_then_forecast on paired Brier. "
            "Treat a win over prose alone as insufficient."
        ),
        "kill_or_scope_rule": (
            "If the true prompt-break arm fails to beat the single-turn typed carrier arm, scope the "
            "token-bottleneck analogy away from closed-model forecasting prompts. If both typed arms lose "
            "to baseline, demote this as an intervention and retain only the artifact-transfer claim."
        ),
        "literature_anchor": {
            "paper": "Korchinski, Favero, Wyart 2026, Learn from your own latents and not from tokens",
            "use": "Mechanistic analogy only: the paper is about training objectives/sample complexity, while N10 tests prompt-time behavioral decomposition.",
        },
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N10 Hard-Prompt-Break Forecasting Packet",
        "",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Contracts: {report['contracts']}",
        f"- Families: `{report['families']}`",
        f"- Queue: `{report['queue_path']}`",
        f"- Queue SHA256: `{report['queue_sha256']}`",
        f"- Source mix: `{report['source_mix']}`",
        f"- Outcome mix hidden from prompt: `{report['outcome_mix_hidden_from_prompt']}`",
        "",
        "## Arms",
        "",
    ]
    for arm in report["arms"]:
        lines.append(f"- `{arm['condition']}`: {arm['tests']}")
    lines.extend(
        [
            "",
            "## Non-Duplication",
            "",
            report["non_duplication_claim"],
            "",
            "## Prior Findings Consumed",
            "",
        ]
    )
    for finding in report["amnesia_prior_findings"]:
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            report["promotion_rule"],
            "",
            "## Kill / Scope Rule",
            "",
            report["kill_or_scope_rule"],
            "",
            "## Literature Anchor",
            "",
            f"- {report['literature_anchor']['paper']}",
            f"- {report['literature_anchor']['use']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--sources", default="manifold,polymarket")
    parser.add_argument("--families", default="codex_55")
    parser.add_argument("--per-source", type=int, default=2)
    args = parser.parse_args()

    sources = csv_tuple(args.sources)
    families = csv_tuple(args.families)
    candidates = load_contract_candidates(args.db, sources)
    contracts = select_contracts(candidates, per_source=args.per_source)
    rows = dispatch_rows(contracts, families=families, pilot_id=args.pilot_id)
    queue_path = args.out_dir / f"{args.pilot_id}_dispatch_queue.jsonl"
    report_path = args.out_dir / f"{args.pilot_id}_packet_report.md"
    report_json_path = args.out_dir / f"{args.pilot_id}_packet_report.json"
    write_jsonl(queue_path, rows)
    report = report_for(
        pilot_id=args.pilot_id,
        contracts=contracts,
        rows=rows,
        queue_path=queue_path,
        sources=sources,
        families=families,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_md(report), encoding="utf-8")
    print(f"wrote {queue_path}")
    print(f"wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
