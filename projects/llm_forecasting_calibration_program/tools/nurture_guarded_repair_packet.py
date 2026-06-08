#!/usr/bin/env python3
"""Build N7 guarded selection-aware repair queues.

N7 is deliberately two-phase:
1. Fire balanced baseline rows.
2. Generate guarded repair rows from those baseline receipts, carrying the
   exact baseline p as the anchor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace"
DEFAULT_SOURCE_PACKET = WORKSPACE / "n3_high_worry_action_policy_packet.json"
PILOT_ID = "n7_guarded_selection_aware_repair_v1"

RUNTIME_BY_FAMILY = {
    "claude": "claude_subscription",
    "codex_55": "codex_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_jsonl(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def numeric_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        p = float(value)
        if 0.0 <= p <= 1.0:
            return p
    return None


def select_balanced_contracts(contracts: list[dict[str, Any]], per_outcome: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for outcome in (1, 0):
        candidates = [row for row in contracts if row.get("y_known") == outcome]
        candidates.sort(key=lambda row: float(row.get("avg_tail") or 0.0), reverse=True)
        selected.extend(candidates[:per_outcome])
    return selected


def baseline_prompt_contract() -> dict[str, Any]:
    return {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": "standard probability forecast only",
        "tests": "baseline anchor for N7 guarded repair",
        "required_output_fields": ["p_success"],
    }


def guarded_repair_contract(contract: dict[str, Any], baseline_anchor_p: float) -> dict[str, Any]:
    return {
        "repair_id": "n7_guarded_selection_aware_probability_repair_v1",
        "baseline_anchor_p": baseline_anchor_p,
        "primary_endpoint": "paired_brier_vs_baseline_anchor",
        "mm_language_mapping": {
            "mm_01": "Admissible-Criteria Rebaselining: do not treat raw-event or market-selected base rates as automatically admissible.",
            "mm_02": "Structural-Semantics Pluralization: emit raw-event and market-selected base rates separately.",
            "mm_03": "Ontological Promotion: guard_decision and revision_delta_vs_anchor are structured carrier fields.",
        },
        "guard_rule": (
            "The baseline anchor is the prior forecast to beat. Revise only if the raw-event and "
            "market-selected reference classes jointly provide a bounded correction. If they conflict, "
            "hold the anchor or cap the revision. Do not let market selection alone move p above 0.5."
        ),
        "diagnostic_slice": {
            "slice_id": "v28a_tail_insurance_high_risk",
            "selection_rule": "selected before N7 by prior tail_insurance_premium only",
            "avg_tail_insurance_premium": contract["avg_tail"],
            "max_tail_insurance_premium": contract["max_tail"],
            "families_observed": contract["families_observed"],
            "source_pilot_ids": contract["source_pilot_ids"],
            "prior_probabilities_hidden": False,
            "target_outcome_hidden": True,
        },
        "promotion_rule": (
            "N7 promotes only if guarded repair improves paired Brier against the exact baseline anchor "
            "on balanced YES/NO rows and does not overcorrect negatives."
        ),
    }


def base_row(contract: dict[str, Any], family: str, pilot_id: str, condition: str) -> dict[str, Any]:
    key = "|".join([pilot_id, contract["contract_id"], family, condition])
    return {
        "dispatch_id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
        "pilot_id": pilot_id,
        "contract_id": contract["contract_id"],
        "family": family,
        "agent_id": family,
        "runtime_route": RUNTIME_BY_FAMILY.get(family, "manual_or_registered_runtime"),
        "condition": condition,
        "primitive": "n7_guarded_selection_aware_repair",
        "question": contract["question"],
        "source": contract["source"],
        "source_corpus": contract["source_corpus"],
        "post_training_cutoff": contract["post_training_cutoff"],
        "resolution_source_url": contract["resolution_source_url"],
        "selection_metadata": {
            "avg_tail_insurance_premium": contract["avg_tail"],
            "max_tail_insurance_premium": contract["max_tail"],
            "families_observed": contract["families_observed"],
            "source_pilot_ids": contract["source_pilot_ids"],
        },
    }


def baseline_rows(contracts: list[dict[str, Any]], families: list[str], pilot_id: str) -> list[dict[str, Any]]:
    rows = []
    for contract in contracts:
        for family in families:
            row = base_row(contract, family, pilot_id, "baseline")
            row["arm"] = "A"
            row["prompt_contract"] = baseline_prompt_contract()
            rows.append(row)
    return rows


def guarded_rows(
    contracts: list[dict[str, Any]],
    families: list[str],
    pilot_id: str,
    baseline_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], float] = {}
    for call in baseline_calls:
        if call.get("pilot_id") != pilot_id or call.get("condition") != "baseline" or not call.get("schema_ok"):
            continue
        p = numeric_probability(call.get("p_success"))
        if p is None:
            parsed = call.get("parsed")
            if isinstance(parsed, dict):
                p = numeric_probability(parsed.get("p_success"))
        if p is not None:
            by_key[(str(call.get("contract_id")), str(call.get("family")))] = p

    rows = []
    for contract in contracts:
        for family in families:
            anchor = by_key.get((contract["contract_id"], family))
            if anchor is None:
                continue
            row = base_row(contract, family, pilot_id, "guarded_selection_aware_probability_repair")
            row["arm"] = "G"
            row["baseline_anchor_p"] = anchor
            row["prompt_contract"] = {
                "include_y_known": False,
                "no_web_tools": True,
                "same_contract_across_arms": True,
                "instruction": (
                    "Use the provided baseline anchor as the prior forecast. Emit raw-event and "
                    "market-selected base rates, apply the guard rule, and revise only if warranted."
                ),
                "tests": "guarded selection-aware repair against exact baseline anchor",
                "required_output_fields": [
                    "baseline_anchor_p",
                    "p_success_before_repair",
                    "raw_event_base_rate",
                    "market_selected_base_rate",
                    "selection_premium",
                    "guard_decision",
                    "p_success",
                    "revision_delta_vs_anchor",
                    "repair_rationale_short",
                ],
                "repair_contract": guarded_repair_contract(contract, anchor),
            }
            rows.append(row)
    return rows


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N7 Guarded Selection-Aware Repair Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Phase: `{report['phase']}`",
        f"- Source packet: `{report['source_packet']}`",
        f"- Contracts: {report['contracts']}",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Families: `{report['families']}`",
        f"- Source counts: `{report['contract_counts_by_source']}`",
        f"- Dispatch SHA-256: `{report['dispatch_sha256']}`",
        "",
        "## Design",
        "",
        "- Phase 1 collects balanced baseline anchors.",
        "- Phase 2 uses only schema-valid phase-1 baselines as explicit anchors.",
        "- Promotion requires paired Brier improvement on balanced YES/NO rows; a tiny smoke is not a claim.",
        "",
        "## Selected Contracts",
        "",
        "| contract_id | source | y_known | avg_tail | max_tail | question |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in report["selected_contracts"]:
        question = str(row["question"]).replace("|", "/")
        lines.append(
            f"| `{row['contract_id']}` | `{row['source']}` | {row['y_known']} | "
            f"{row['avg_tail']} | {row['max_tail']} | {question} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-packet", type=Path, default=DEFAULT_SOURCE_PACKET)
    parser.add_argument("--out-dir", type=Path, default=WORKSPACE)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--families", default="codex_55,gemini,deepseek")
    parser.add_argument("--per-outcome", type=int, default=2)
    parser.add_argument("--phase", choices=["baseline", "guarded"], default="baseline")
    parser.add_argument("--baseline-calls", type=Path)
    args = parser.parse_args()

    source = load_json(args.source_packet)
    contracts = select_balanced_contracts(source.get("selected_contracts") or [], args.per_outcome)
    families = [part.strip() for part in args.families.split(",") if part.strip()]
    if args.phase == "guarded":
        if not args.baseline_calls:
            raise SystemExit("--baseline-calls is required for --phase guarded")
        rows = guarded_rows(contracts, families, args.pilot_id, load_jsonl(args.baseline_calls))
        baseline_queue = args.out_dir / "n7_guarded_selection_aware_repair_baseline_dispatch_queue.jsonl"
        baseline_rows_for_combined = load_jsonl(baseline_queue)
    else:
        rows = baseline_rows(contracts, families, args.pilot_id)
        baseline_rows_for_combined = []

    report = {
        "schema": "gp245-n7-guarded-selection-aware-repair-packet-v1",
        "pilot_id": args.pilot_id,
        "phase": args.phase,
        "source_packet": str(args.source_packet),
        "contracts": len(contracts),
        "dispatch_rows": len(rows),
        "families": families,
        "contract_counts_by_source": dict(Counter(row["source"] for row in contracts)),
        "selected_contracts": contracts,
        "dispatch_sha256": sha256_jsonl(rows),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"n7_guarded_selection_aware_repair_{args.phase}"
    (args.out_dir / f"{stem}_packet.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / f"{stem}_packet.md").write_text(render_md(report), encoding="utf-8")
    write_jsonl(args.out_dir / f"{stem}_dispatch_queue.jsonl", rows)
    if args.phase == "guarded":
        write_jsonl(
            args.out_dir / "n7_guarded_selection_aware_repair_combined_dispatch_queue.jsonl",
            baseline_rows_for_combined + rows,
        )
    print(f"wrote {args.out_dir / f'{stem}_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
