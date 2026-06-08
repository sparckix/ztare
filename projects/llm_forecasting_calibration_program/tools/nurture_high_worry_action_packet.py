#!/usr/bin/env python3
"""Build the N3 high-worry action-policy packet.

No model calls. No DB mutation. This packet consumes the prior intervention
amnesia map and selects real-question public contracts whose older v28a
same-contract calls produced high tail-risk diagnostics. The live test is not
"generic action framing"; it is whether action helps on a predeclared
diagnostic-high slice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "nurture_intervention_v1/workspace"
PILOT_ID = "n3_high_worry_action_policy_v1"
DEFAULT_SOURCE_PILOTS = ("v28a_full__v25_external", "v28a_refill__v25_external")
EXCLUDE_PILOTS = ("n1_nurture_intervention_v1", "n2_selective_action_confirmatory_v1")

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
        "tests": "raw Brier baseline on a diagnostic-high slice",
    },
    {
        "arm": "E",
        "condition": "selective_action",
        "instruction": "choose forecast_yes/forecast_no/abstain/reroute_or_judge under predeclared utility on a diagnostic-high row",
        "tests": "whether high-risk diagnostic-triggered action beats raw p and simple abstention",
    },
]

QUALITY_EXCLUDE_PATTERNS = [
    r"\bbitch\b",
    r"\bfuck\b",
    r"\bchad\b",
    r"\bmogged\b",
    r"\bwill manifold think\b",
    r"\bwill an ai agent send me mana\b",
]


def as_tuple_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def placeholders(values: tuple[str, ...]) -> str:
    return ",".join("?" for _ in values)


def quality_flags(question: str) -> list[str]:
    lowered = question.lower()
    flags = []
    for pattern in QUALITY_EXCLUDE_PATTERNS:
        if re.search(pattern, lowered):
            flags.append(pattern)
    if len(question.strip()) < 20:
        flags.append("too_short")
    if question.startswith("Premium clean contract "):
        flags.append("placeholder_question")
    return flags


def selective_action_regime() -> dict[str, Any]:
    return {
        "regime_id": "n3_high_worry_symmetric_with_predeclared_review_v1",
        "forecast_action": {"correct": 1.0, "incorrect": -1.0},
        "abstain_action": {"utility": 0.0},
        "reroute_or_judge_action": {
            "utility_if_correct_after_review": 0.9,
            "utility_if_incorrect_after_review": -1.1,
            "review_cost": 0.1,
            "resolver": (
                "score as unresolved until an independent blind review emits "
                "review_correct in {true,false}; unresolved rows are reported "
                "separately and cannot be counted as wins"
            ),
        },
        "analytic_controls": [
            "raw_baseline_probability",
            "forecast_all_from_baseline_p_ge_0p5",
            "abstain_all_selected_rows",
            "confidence_threshold_abstain_abs_p_minus_0p5_lt_0p20",
            "confident_no_discount_where_p_raw_below_0p10",
        ],
        "decision_rule_required_from_model": ["forecast_yes", "forecast_no", "abstain", "reroute_or_judge"],
        "declared_before_outcomes": True,
    }


def action_control_plan() -> dict[str, Any]:
    return {
        "schema": "gp245-n3-action-control-plan-v1",
        "primary_comparison": "selective_action_vs_baseline_paired_brier",
        "utility_controls": [
            {
                "control_id": "baseline_forecast_all",
                "rule": "Use the baseline arm p_success; forecast YES iff p_success >= 0.5.",
                "utility": "correct=+1, incorrect=-1",
            },
            {
                "control_id": "abstain_all",
                "rule": "Abstain on every selected high-worry row.",
                "utility": "0 for every row",
            },
            {
                "control_id": "confidence_threshold_abstain",
                "rule": "Use baseline p_success; forecast only when abs(p_success - 0.5) >= 0.20, otherwise abstain.",
                "utility": "correct forecast=+1, incorrect forecast=-1, abstain=0",
            },
        ],
        "judge_review_protocol": {
            "when_required": "Only for selective_action rows whose selected_action is reroute_or_judge.",
            "blind_inputs": [
                "contract_id",
                "question",
                "source",
                "baseline p_success hidden unless reviewer is scoring a reroute policy variant",
                "selective_action p_success",
                "action_rationale_short",
            ],
            "required_output_fields": [
                "review_action",
                "review_p_success",
                "review_correct_after_y_known",
                "review_rationale_short",
            ],
            "scoring_rule": (
                "Reroute/judge rows remain unresolved in utility until an independent "
                "blind review row is present; unresolved rows cannot count as wins."
            ),
        },
        "promotion_rule": (
            "N3 promotes only if selective_action beats paired Brier baseline and "
            "mean utility beats both abstain_all and confidence_threshold_abstain."
        ),
    }


def prompt_contract_for(arm: dict[str, str], candidate: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": arm["instruction"],
        "tests": arm["tests"],
        "required_output_fields": ["p_success"],
    }
    if arm["condition"] == "selective_action":
        payload["diagnostic_slice"] = {
            "slice_id": "v28a_tail_insurance_high_risk",
            "selection_rule": "selected before N3 calls by prior v28a tail_insurance_premium only",
            "avg_tail_insurance_premium": candidate["avg_tail"],
            "max_tail_insurance_premium": candidate["max_tail"],
            "families_observed": candidate["families_observed"],
            "source_pilot_ids": candidate["source_pilot_ids"],
            "prior_probabilities_hidden": True,
            "target_outcome_hidden": True,
        }
        payload["utility_regime"] = selective_action_regime()
        payload["required_output_fields"] = [
            "p_success",
            "worry",
            "selected_action",
            "expected_utility",
            "action_rationale_short",
        ]
    return payload


def called_contract_ids(con: sqlite3.Connection, pilot_ids: tuple[str, ...]) -> set[str]:
    if not pilot_ids:
        return set()
    return {
        str(row[0])
        for row in con.execute(
            f"SELECT DISTINCT contract_id FROM pilot_calls WHERE pilot_id IN ({placeholders(pilot_ids)})",
            pilot_ids,
        )
    }


def load_candidates(
    db: Path,
    *,
    source_pilots: tuple[str, ...],
    sources: tuple[str, ...],
    exclude_pilots: tuple[str, ...],
    min_avg_tail: float,
    min_max_tail: float,
    quality_filter: bool,
) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    exclude_contracts = called_contract_ids(con, exclude_pilots)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success, pc.brier,
                   CAST(json_extract(pc.parsed_json, '$.tail_insurance_premium') AS REAL) AS tail,
                   c.question, c.source, c.source_corpus, c.y_known, c.post_training_cutoff,
                   c.resolution_source_url
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id IN ({placeholders(source_pilots)})
              AND c.source IN ({placeholders(sources)})
              AND pc.schema_ok = 1
              AND pc.brier IS NOT NULL
              AND json_extract(pc.parsed_json, '$.tail_insurance_premium') IS NOT NULL
              AND c.y_known IN (0, 1)
              AND c.post_training_cutoff = 1
              AND c.question IS NOT NULL
            """,
            (*source_pilots, *sources),
        )
    ]
    con.close()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row["contract_id"]) in exclude_contracts:
            continue
        grouped[str(row["contract_id"])].append(row)
    candidates: list[dict[str, Any]] = []
    for contract_id, group in grouped.items():
        question = str(group[0]["question"])
        flags = quality_flags(question)
        tails = [float(row["tail"]) for row in group if row.get("tail") is not None]
        if not tails:
            continue
        avg_tail = sum(tails) / len(tails)
        max_tail = max(tails)
        if avg_tail < min_avg_tail and max_tail < min_max_tail:
            continue
        if quality_filter and flags:
            continue
        candidates.append(
            {
                "contract_id": contract_id,
                "question": question,
                "source": group[0]["source"],
                "source_corpus": group[0]["source_corpus"],
                "y_known": int(group[0]["y_known"]),
                "post_training_cutoff": int(group[0]["post_training_cutoff"]),
                "resolution_source_url": group[0]["resolution_source_url"],
                "families_observed": sorted({str(row["family"]) for row in group if row.get("family")}),
                "source_pilot_ids": sorted({str(row["pilot_id"]) for row in group if row.get("pilot_id")}),
                "avg_tail": round(avg_tail, 4),
                "max_tail": round(max_tail, 4),
                "avg_abs_error_prior": round(
                    sum(abs(float(row["p_success"]) - int(row["y_known"])) for row in group) / len(group),
                    4,
                ),
                "quality_flags": flags,
            }
        )
    return sorted(candidates, key=lambda row: (-row["avg_tail"], -row["max_tail"], row["source"], row["contract_id"]))


def select_balanced(candidates: list[dict[str, Any]], *, per_source: int) -> list[dict[str, Any]]:
    by_source_y: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_source_y[(str(row["source"]), int(row["y_known"]))].append(row)
    selected: list[dict[str, Any]] = []
    sources = sorted({str(row["source"]) for row in candidates})
    for source in sources:
        half = per_source // 2
        picked = by_source_y.get((source, 1), [])[:half] + by_source_y.get((source, 0), [])[: per_source - half]
        if len(picked) < per_source:
            seen = {row["contract_id"] for row in picked}
            fallback = [row for row in candidates if row["source"] == source and row["contract_id"] not in seen]
            picked.extend(fallback[: per_source - len(picked)])
        selected.extend(picked[:per_source])
    return selected


def dispatch_rows(contracts: list[dict[str, Any]], *, families: tuple[str, ...], pilot_id: str) -> list[dict[str, Any]]:
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
                        "primitive": "n3_high_worry_action_policy",
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
                        "prompt_contract": prompt_contract_for(arm, contract),
                    }
                )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_jsonl(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N3 High-Worry Action-Policy Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Contracts selected: {report['contracts']}",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Families: `{report['families']}`",
        f"- Source pilots: `{report['source_pilot_ids']}`",
        f"- Excluded pilots: `{report['excluded_pilot_ids']}`",
        f"- Source counts: `{report['contract_counts_by_source']}`",
        f"- y_known counts: `{report['contract_counts_by_y_known']}`",
        f"- Dispatch SHA-256: `{report['dispatch_sha256']}`",
        "",
        "## Why This Is Not N2 Again",
        "",
        "- N2 tested generic action framing on all-comers fresh rows and failed.",
        "- N3 selects rows before calls using prior tail-risk diagnostics from v28a real-question public rows.",
        "- The intervention is diagnostic-triggered action, not another generic prompt-nurture arm.",
        "- The scoring plan compares against raw baseline, abstain-all, confidence-threshold abstention, and confident-NO where applicable.",
        "- Reroute/judge choices are predeclared as unresolved until a blind review record exists.",
        "",
        "## Prior Findings Consumed",
        "",
        "- F25: premium threshold inflation harmed utility as wired.",
        "- F28: premium abstention can help and must be an action-control baseline.",
        "- F30: cross-family judge can help on high-premium cases but is cost-regime dependent.",
        "- F29/F33/F38/F43: generic text/rationale interventions are not enough.",
        "- F47/F62: contrastive/reference-class remain separate probability-generation candidates.",
        "- F89/F108: worry is noisy but diagnostic; do not treat it as direct correction.",
        "- F114: broad selective action failed confirmation.",
        "",
        "## Predeclared Action Controls",
        "",
        "- `baseline_forecast_all`: use baseline p; forecast YES iff p >= 0.5, else forecast NO; correct +1 / incorrect -1.",
        "- `abstain_all`: abstain on every selected row; utility 0.",
        "- `confidence_threshold_abstain`: use baseline p; forecast only when abs(p - 0.5) >= 0.20, otherwise abstain.",
        "- `reroute_or_judge`: unresolved until an independent blind review row exists; unresolved rows cannot count as wins.",
        "",
        "## Selected Contracts",
        "",
        "| contract_id | source | y_known | avg_tail | max_tail | prior_avg_abs_error | question |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in report["selected_contracts"]:
        question = str(row["question"]).replace("|", "/")
        lines.append(
            f"| `{row['contract_id']}` | `{row['source']}` | {row['y_known']} | "
            f"{row['avg_tail']} | {row['max_tail']} | {row['avg_abs_error_prior']} | {question} |"
        )
    lines.extend(
        [
            "",
            "## Kill Criteria",
            "",
            "- Kill broad action policy if `selective_action` fails paired Brier against baseline again.",
            "- Kill utility claim if action utility loses to simple abstention on the same selected rows.",
            "- Scope to family/source only if gains are carried by one family or one source.",
            "- Do not count unresolved reroute/judge choices as wins without independent review labels.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=PILOT_ID)
    parser.add_argument("--source-pilot-ids", default=",".join(DEFAULT_SOURCE_PILOTS))
    parser.add_argument("--exclude-pilot-ids", default=",".join(EXCLUDE_PILOTS))
    parser.add_argument("--sources", default="manifold,polymarket")
    parser.add_argument("--families", default="claude,codex_55,gemini,deepseek")
    parser.add_argument("--contracts-per-source", type=int, default=6)
    parser.add_argument("--min-avg-tail", type=float, default=60.0)
    parser.add_argument("--min-max-tail", type=float, default=80.0)
    parser.add_argument("--no-quality-filter", action="store_true")
    args = parser.parse_args()

    source_pilots = as_tuple_csv(args.source_pilot_ids)
    exclude_pilots = as_tuple_csv(args.exclude_pilot_ids)
    sources = as_tuple_csv(args.sources)
    families = as_tuple_csv(args.families)
    candidates = load_candidates(
        args.db,
        source_pilots=source_pilots,
        sources=sources,
        exclude_pilots=exclude_pilots,
        min_avg_tail=args.min_avg_tail,
        min_max_tail=args.min_max_tail,
        quality_filter=not args.no_quality_filter,
    )
    selected = select_balanced(candidates, per_source=args.contracts_per_source)
    rows = dispatch_rows(selected, families=families, pilot_id=args.pilot_id)
    report = {
        "schema": "gp245-n3-high-worry-action-packet-v1",
        "pilot_id": args.pilot_id,
        "source_pilot_ids": list(source_pilots),
        "excluded_pilot_ids": list(exclude_pilots),
        "sources": list(sources),
        "families": list(families),
        "min_avg_tail": args.min_avg_tail,
        "min_max_tail": args.min_max_tail,
        "quality_filter": not args.no_quality_filter,
        "candidate_contracts": len(candidates),
        "contracts": len(selected),
        "dispatch_rows": len(rows),
        "dispatch_sha256": sha256_jsonl(rows),
        "contract_counts_by_source": dict(Counter(row["source"] for row in selected)),
        "contract_counts_by_y_known": dict(Counter(str(row["y_known"]) for row in selected)),
        "selected_contracts": selected,
        "action_control_plan": action_control_plan(),
        "amnesia_map": "nurture_intervention_v1/workspace/prior_intervention_amnesia_map.md",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "n3_high_worry_action_policy_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "n3_high_worry_action_policy_packet.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    write_jsonl(args.out_dir / "n3_high_worry_action_policy_dispatch_queue.jsonl", rows)
    print(f"wrote {args.out_dir / 'n3_high_worry_action_policy_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
