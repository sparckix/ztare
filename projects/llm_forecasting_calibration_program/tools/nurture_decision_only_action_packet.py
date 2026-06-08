#!/usr/bin/env python3
"""Build N4 decision-only action-policy packet from the N3 high-tail slate."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace"
DEFAULT_N3_PACKET = WORKSPACE / "n3_high_worry_action_policy_packet.json"
PILOT_ID = "n4_decision_only_action_policy_v1"

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
        "tests": "raw probability and forecast-all utility baseline on the same high-tail slice",
        "required_output_fields": ["p_success"],
    },
    {
        "arm": "D",
        "condition": "selective_action",
        "instruction": (
            "choose one action from forecast_yes, forecast_no, abstain, reroute_or_judge. "
            "Utility is the primary endpoint; p_success is recorded only as the probability used by your decision."
        ),
        "tests": "whether a decision-only policy beats simple utility controls on a diagnostic-high slice",
        "required_output_fields": [
            "p_success",
            "worry",
            "selected_action",
            "expected_utility",
            "action_rationale_short",
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


def action_regime() -> dict[str, Any]:
    return {
        "regime_id": "n4_decision_only_utility_primary_v1",
        "declared_before_outcomes": True,
        "primary_endpoint": "mean_utility_vs_controls",
        "secondary_endpoint": "paired_brier_reported_not_promotional",
        "decision_rule_required_from_model": ["forecast_yes", "forecast_no", "abstain", "reroute_or_judge"],
        "forecast_action": {"correct": 1.0, "incorrect": -1.0},
        "abstain_action": {"utility": 0.0},
        "reroute_or_judge_action": {
            "review_cost": 0.1,
            "utility_if_correct_after_review": 0.9,
            "utility_if_incorrect_after_review": -1.1,
            "resolver": "unresolved until independent blind review row exists; unresolved rows cannot count as wins",
        },
        "analytic_controls": [
            "abstain_all",
            "baseline_forecast_all",
            "confidence_threshold_abstain_abs_p_minus_0p5_lt_0p20",
        ],
        "promotion_rule": (
            "N4 promotes only if selective_action mean utility beats abstain_all, baseline_forecast_all, "
            "and confidence-threshold abstention after unresolved reroute/judge rows are reviewed or excluded "
            "under a predeclared sensitivity analysis."
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
    if arm["condition"] == "selective_action":
        payload["diagnostic_slice"] = {
            "slice_id": "v28a_tail_insurance_high_risk",
            "selection_rule": "selected before N4 calls by prior v28a tail_insurance_premium only",
            "avg_tail_insurance_premium": contract["avg_tail"],
            "max_tail_insurance_premium": contract["max_tail"],
            "families_observed": contract["families_observed"],
            "source_pilot_ids": contract["source_pilot_ids"],
            "prior_probabilities_hidden": True,
            "target_outcome_hidden": True,
        }
        payload["utility_regime"] = action_regime()
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
                        "primitive": "n4_decision_only_action_policy",
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
        "# N4 Decision-Only Action-Policy Packet",
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
        "## Design Repair",
        "",
        "- N3-current mixed probability repair and action policy; all current action probabilities equaled baseline probabilities.",
        "- N4 treats utility as primary and paired Brier as secondary/reporting-only.",
        "- Reroute/judge rows remain unresolved until independent blind review exists.",
        "- Probability-improvement claims require a separate base-rate/reference-class repair arm.",
        "",
        "## Promotion Rule",
        "",
        action_regime()["promotion_rule"],
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
    parser.add_argument("--n3-packet", type=Path, default=DEFAULT_N3_PACKET)
    parser.add_argument("--out-dir", type=Path, default=WORKSPACE)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--families", default="")
    args = parser.parse_args()

    n3 = load_json(args.n3_packet)
    contracts = n3.get("selected_contracts") or []
    families = [part.strip() for part in args.families.split(",") if part.strip()] or list(n3.get("families") or [])
    rows = dispatch_rows(contracts, families, args.pilot_id)
    report = {
        "schema": "gp245-n4-decision-only-action-packet-v1",
        "pilot_id": args.pilot_id,
        "source_packet": str(args.n3_packet),
        "contracts": len(contracts),
        "dispatch_rows": len(rows),
        "families": families,
        "contract_counts_by_source": dict(Counter(row["source"] for row in contracts)),
        "selected_contracts": contracts,
        "action_regime": action_regime(),
        "dispatch_sha256": sha256_jsonl(rows),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "n4_decision_only_action_policy_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "n4_decision_only_action_policy_packet.md").write_text(render_md(report), encoding="utf-8")
    write_jsonl(args.out_dir / "n4_decision_only_action_policy_dispatch_queue.jsonl", rows)
    print(f"wrote {args.out_dir / 'n4_decision_only_action_policy_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
