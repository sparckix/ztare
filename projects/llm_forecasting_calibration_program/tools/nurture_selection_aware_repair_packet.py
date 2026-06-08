#!/usr/bin/env python3
"""Build N6 selection-aware probability-repair packet from the N3/N4 slate."""
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
PILOT_ID = "n6_selection_aware_probability_repair_v1"

RUNTIME_BY_FAMILY = {
    "claude": "claude_subscription",
    "codex_55": "codex_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}

ARMS = [
    {
        "arm": "A",
        "condition": "baseline",
        "instruction": "standard probability forecast only",
        "tests": "raw probability baseline on the high-tail slice",
        "required_output_fields": ["p_success"],
    },
    {
        "arm": "S",
        "condition": "selection_aware_probability_repair",
        "instruction": (
            "First give your unaided probability. Then explicitly separate at least two reference classes: "
            "the raw event class and the market-selected named-candidate class. Choose the reference class "
            "that should govern the final probability, then revise only if warranted."
        ),
        "tests": (
            "whether reference-class pluralization avoids the N5 failure mode where raw event base rates "
            "overcorrected high-tail market-selected contracts"
        ),
        "required_output_fields": [
            "p_success_before_repair",
            "raw_event_base_rate",
            "market_selected_base_rate",
            "chosen_reference_class",
            "chosen_base_rate",
            "p_success",
            "revision_delta",
            "repair_rationale_short",
        ],
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_jsonl(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def selection_aware_repair_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "repair_id": "n6_selection_aware_reference_class_probability_repair_v1",
        "primary_endpoint": "paired_brier_vs_baseline",
        "secondary_endpoints": [
            "raw_event_base_rate",
            "market_selected_base_rate",
            "chosen_reference_class",
            "revision_direction_and_magnitude",
        ],
        "mm_language_mapping": {
            "mm_01": (
                "Admissible-Criteria Rebaselining: raw participant/event base rate is not automatically "
                "admissible once a prediction market has selected and named the candidate."
            ),
            "mm_02": (
                "Structural-Semantics Pluralization: split base rate into raw event class and "
                "market-selected named-candidate class before revising."
            ),
            "mm_03": (
                "Ontological Promotion: selection-aware reference class is a first-class carrier field, "
                "not prose hidden inside rationale."
            ),
        },
        "base_rate_instruction": (
            "Use only general knowledge. Do not browse. Do not use hidden outcome information. "
            "Emit numeric probabilities in [0,1] for both requested reference classes."
        ),
        "diagnostic_slice": {
            "slice_id": "v28a_tail_insurance_high_risk",
            "selection_rule": "selected before N6 calls by prior v28a tail_insurance_premium only",
            "avg_tail_insurance_premium": contract["avg_tail"],
            "max_tail_insurance_premium": contract["max_tail"],
            "families_observed": contract["families_observed"],
            "source_pilot_ids": contract["source_pilot_ids"],
            "prior_probabilities_hidden": True,
            "target_outcome_hidden": True,
        },
        "promotion_rule": (
            "N6 promotes only if selection_aware_probability_repair improves paired Brier against "
            "baseline and avoids systematic downward overcorrection on market-selected high-tail positives."
        ),
    }


def prompt_contract(arm: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": arm["instruction"],
        "tests": arm["tests"],
        "required_output_fields": arm["required_output_fields"],
    }
    if arm["condition"] == "selection_aware_probability_repair":
        payload["repair_contract"] = selection_aware_repair_contract(contract)
    return payload


def dispatch_rows(contracts: list[dict[str, Any]], families: list[str], pilot_id: str) -> list[dict[str, Any]]:
    rows = []
    for contract in contracts:
        for family in families:
            for arm in ARMS:
                key = "|".join([pilot_id, contract["contract_id"], family, arm["condition"]])
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
                        "primitive": "n6_selection_aware_probability_repair",
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
                        "prompt_contract": prompt_contract(arm, contract),
                    }
                )
    return rows


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N6 Selection-Aware Probability-Repair Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Source packet: `{report['source_packet']}`",
        f"- Contracts: {report['contracts']}",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Families: `{report['families']}`",
        f"- Source counts: `{report['contract_counts_by_source']}`",
        f"- Dispatch SHA-256: `{report['dispatch_sha256']}`",
        "",
        "## Why This Exists",
        "",
        "- N3/N4 action-policy smokes failed first utility checks.",
        "- N5 naive probability repair worsened paired Brier on the first two rows by using low raw-event base rates.",
        "- N6 asks whether the failure is base-rate repair itself or the wrong reference-class semantics.",
        "",
        "## Meta-Language Carrier",
        "",
        "- `mm_01`: rebaseline admissibility; raw event base rate is not automatically admissible.",
        "- `mm_02`: pluralize base-rate semantics into raw event and market-selected candidate classes.",
        "- `mm_03`: promote the selection-aware reference class into required structured fields.",
        "",
        "## Promotion Rule",
        "",
        selection_aware_repair_contract(report["selected_contracts"][0])["promotion_rule"]
        if report["selected_contracts"]
        else "",
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
    parser.add_argument("--families", default="")
    args = parser.parse_args()

    source = load_json(args.source_packet)
    contracts = source.get("selected_contracts") or []
    families = [part.strip() for part in args.families.split(",") if part.strip()] or list(source.get("families") or [])
    rows = dispatch_rows(contracts, families, args.pilot_id)
    report = {
        "schema": "gp245-n6-selection-aware-probability-repair-packet-v1",
        "pilot_id": args.pilot_id,
        "source_packet": str(args.source_packet),
        "contracts": len(contracts),
        "dispatch_rows": len(rows),
        "families": families,
        "contract_counts_by_source": dict(Counter(row["source"] for row in contracts)),
        "selected_contracts": contracts,
        "dispatch_sha256": sha256_jsonl(rows),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "n6_selection_aware_probability_repair_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "n6_selection_aware_probability_repair_packet.md").write_text(render_md(report), encoding="utf-8")
    write_jsonl(args.out_dir / "n6_selection_aware_probability_repair_dispatch_queue.jsonl", rows)
    print(f"wrote {args.out_dir / 'n6_selection_aware_probability_repair_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
