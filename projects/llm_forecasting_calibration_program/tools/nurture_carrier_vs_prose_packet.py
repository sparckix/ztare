#!/usr/bin/env python3
"""Build the N9 carrier-vs-prose forecasting packet.

No model calls. No DB mutation. This freezes a same-contract dispatch queue
that tests whether typed carrier fields improve Brier, rather than merely
making explanations look better.
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
PILOT_ID = "n9_carrier_vs_prose_v1"

ARMS = [
    {
        "arm": "A",
        "condition": "baseline",
        "instruction": "Emit only a probability for the event resolving YES.",
        "tests": "raw probability baseline",
    },
    {
        "arm": "B",
        "condition": "free_prose_forecast",
        "instruction": (
            "Think in ordinary concise forecasting prose, then emit the final "
            "probability plus short rationale fields."
        ),
        "tests": "whether prose rationale improves p_success",
    },
    {
        "arm": "C",
        "condition": "typed_carrier_forecast",
        "instruction": (
            "Do not write a prose rationale. First fill the typed carrier "
            "fields, then emit p_success."
        ),
        "tests": "whether structured carrier fields improve p_success",
    },
    {
        "arm": "D",
        "condition": "carrier_to_action_execution",
        "instruction": (
            "Do not write a prose rationale. Fill the typed carrier fields, "
            "emit p_success, then choose the utility-maximizing action under "
            "the provided regime."
        ),
        "tests": "whether carrier fields improve costed action selection",
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
        "no_prose_rationale": True,
        "field_order_intent": [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
            "p_success",
        ],
        "source_fact_rule": "Use only the question text, source label, corpus label, and date/horizon clues visible in the prompt.",
        "nearest_confuser_rule": "Name the wrong contract class most likely to pull probability in the wrong direction.",
        "action_program_rule": "State the compact decision procedure that sets p_success from the carrier fields.",
        "deterministic_check_rule": "State the final consistency check before probability emission.",
        "outcome_hidden": True,
        "target_contract_id": contract["contract_id"],
    }


def utility_regime() -> dict[str, Any]:
    return {
        "regime_id": "n9_symmetric_forecast_or_abstain_v1",
        "forecast_action": {"correct": 1.0, "incorrect": -1.0},
        "forecast_yes_action": {"correct_if_yes": 1.0, "incorrect_if_no": -1.0},
        "forecast_no_action": {"correct_if_no": 1.0, "incorrect_if_yes": -1.0},
        "abstain_action": {"utility": 0.0},
        "reroute_or_judge_action": {
            "utility_if_correct_after_review": 0.85,
            "utility_if_incorrect_after_review": -1.15,
            "review_cost": 0.15,
        },
        "allowed_actions": ["forecast", "forecast_yes", "forecast_no", "abstain", "reroute_or_judge"],
        "outcome_hidden": True,
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
    if arm["condition"] == "typed_carrier_forecast":
        payload["carrier_contract"] = carrier_contract_for(contract)
        payload["required_output_fields"] = [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
            "p_success",
        ]
    if arm["condition"] == "carrier_to_action_execution":
        payload["carrier_contract"] = carrier_contract_for(contract)
        payload["utility_regime"] = utility_regime()
        payload["required_output_fields"] = [
            "source_facts",
            "residual_evidence_carrier",
            "nearest_confuser",
            "action_program",
            "deterministic_check",
            "p_success",
            "selected_action",
            "expected_utility",
            "action_rationale_short",
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
                        "primitive": "n9_carrier_vs_prose",
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
    outcome_mix = Counter(int(row["y_known"]) for row in contracts)
    source_mix = Counter(str(row["source"]) for row in contracts)
    condition_mix = Counter(str(row["condition"]) for row in rows)
    return {
        "schema": "gp245-n9-carrier-vs-prose-packet-v1",
        "pilot_id": pilot_id,
        "queue_path": str(queue_path.relative_to(REPO)),
        "queue_sha256": sha256_jsonl(rows),
        "contracts": len(contracts),
        "dispatch_rows": len(rows),
        "families": list(families),
        "sources_requested": list(sources),
        "source_mix": dict(source_mix),
        "outcome_mix_hidden_from_prompt": dict(outcome_mix),
        "condition_mix": dict(condition_mix),
        "arms": ARMS,
        "amnesia_prior_findings": [
            "F19: rationale-only exposure did not systematically rescue Brier.",
            "F22: adversarial framing reduced one worst-case rationale-transfer harm but did not make rationale transfer net-positive.",
            "F38: prompts can increase failure-mode text without moving calibration.",
            "N5-N8: self-repair and diagnostic-triggered allocation are demoted unless Brier/utility controls are beaten.",
        ],
        "promotion_rule": (
            "Promote only if typed_carrier_forecast beats baseline and free_prose_forecast "
            "on paired Brier, and carrier_to_action_execution beats forecast-all, abstain-all, "
            "and confidence-threshold controls on costed utility."
        ),
        "kill_or_scope_rule": (
            "If free_prose_forecast and typed_carrier_forecast both fail to beat baseline, "
            "kill this behavioral carrier intervention surface. If free_prose beats typed_carrier, "
            "scope the carrier law away from closed-model forecasting prompts. If carrier_to_action "
            "does not beat explicit utility controls, do not claim applied value even if Brier moves."
        ),
        "db_contract": (
            "Run with nurture_intervention_dispatch_runner.py, ingest with "
            "nurture_intervention_ingest.py into pilot_calls using this pilot_id, score with "
            "nurture_intervention_score.py. Raw JSONL remains a receipt; DB is canonical."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N9 Carrier-vs-Prose Forecasting Packet",
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
            "## DB Contract",
            "",
            report["db_contract"],
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
    if not contracts:
        raise SystemExit("No eligible contracts selected.")
    rows = dispatch_rows(contracts, families=families, pilot_id=args.pilot_id)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.pilot_id
    queue_path = args.out_dir / f"{stem}_dispatch_queue.jsonl"
    report_json_path = args.out_dir / f"{stem}_packet_report.json"
    report_md_path = args.out_dir / f"{stem}_packet_report.md"
    write_jsonl(queue_path, rows)
    report = report_for(
        pilot_id=args.pilot_id,
        contracts=contracts,
        rows=rows,
        queue_path=queue_path,
        sources=sources,
        families=families,
    )
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md_path.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({"queue": str(queue_path), "report": str(report_md_path), "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
