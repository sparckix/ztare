#!/usr/bin/env python3
"""Build the N1 forecast-nurture intervention packet.

No model calls. No DB mutation. Selects scoreable contracts from the master DB,
freezes same-contract arms, and emits a dispatch queue plus report.
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

ARMS = [
    {
        "arm": "A",
        "condition": "baseline",
        "instruction": "standard probability forecast only",
        "tests": "raw Brier baseline",
    },
    {
        "arm": "B",
        "condition": "diagnostic_only",
        "instruction": "emit probability plus worry/spread/self-Brier diagnostics, no correction",
        "tests": "whether diagnostics alone move p or only expose risk",
    },
    {
        "arm": "C",
        "condition": "reference_class_numeric",
        "instruction": "use compact outside-view/base-rate context before final probability",
        "tests": "whether explicit reference class improves p",
    },
    {
        "arm": "D",
        "condition": "contrastive_numeric_revision",
        "instruction": "compare against a contrast case and make a mandatory numeric revision",
        "tests": "whether comparative reasoning changes calibration",
    },
    {
        "arm": "E",
        "condition": "selective_action",
        "instruction": "choose forecast/abstain/reroute/judge under predeclared utility",
        "tests": "whether diagnostics improve action instead of p",
    },
]

RUNTIME_BY_FAMILY = {
    "claude": "claude_subscription",
    "codex_55": "codex_subscription",
    "codex_54mini": "codex_subscription",
    "gemini": "gemini_api_or_manual",
    "deepseek": "deepseek_api_or_manual",
}


def as_tuple_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def load_contracts(db: Path, *, sources: tuple[str, ...], per_source: int) -> list[dict[str, Any]]:
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
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        question = str(row.get("question") or "")
        if question.startswith("Premium clean contract "):
            continue
        if len(question.strip()) < 20:
            continue
        if row["source"] in sources:
            by_source[row["source"]].append(row)
    selected: list[dict[str, Any]] = []
    for source in sources:
        candidates = by_source.get(source, [])
        yes = [row for row in candidates if int(row.get("y_known") or 0) == 1]
        no = [row for row in candidates if int(row.get("y_known") or 0) == 0]
        # Deterministic class balance where possible, without hiding the final mix.
        half = per_source // 2
        picked = yes[:half] + no[: per_source - half]
        if len(picked) < per_source:
            seen = {row["contract_id"] for row in picked}
            picked.extend([row for row in candidates if row["contract_id"] not in seen][: per_source - len(picked)])
        selected.extend(picked[:per_source])
    return selected


def reference_class_for(contract: dict[str, Any], all_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    pool = [
        row
        for row in all_contracts
        if row["contract_id"] != contract["contract_id"]
        and row.get("source") == contract.get("source")
        and row.get("y_known") in (0, 1)
        and not str(row.get("question") or "").startswith("Premium clean contract ")
    ]
    yes = sum(1 for row in pool if int(row.get("y_known") or 0) == 1)
    yes_rows = [row for row in pool if int(row.get("y_known") or 0) == 1]
    no_rows = [row for row in pool if int(row.get("y_known") or 0) == 0]
    example_pool = yes_rows[:3] + no_rows[:3]
    if len(example_pool) < 6:
        seen = {row["contract_id"] for row in example_pool}
        example_pool.extend([row for row in pool if row["contract_id"] not in seen][: 6 - len(example_pool)])
    examples = []
    for row in example_pool[:6]:
        examples.append(
            {
                "contract_id": row["contract_id"],
                "question": row["question"],
                "resolved_yes": int(row["y_known"]),
            }
        )
    return {
        "source": contract.get("source"),
        "source_corpus": contract.get("source_corpus"),
        "n": len(pool),
        "yes_rate_excluding_target": round(yes / len(pool), 4) if pool else None,
        "examples_excluding_target": examples,
        "target_outcome_hidden": True,
    }


def contrast_case_for(contract: dict[str, Any], selected_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    same_source = [
        row
        for row in selected_contracts
        if row["contract_id"] != contract["contract_id"]
        and row.get("source") == contract.get("source")
    ]
    opposite = [
        row
        for row in same_source
        if row.get("y_known") in (0, 1) and row.get("y_known") != contract.get("y_known")
    ]
    pool = opposite or same_source or [row for row in selected_contracts if row["contract_id"] != contract["contract_id"]]
    chosen = sorted(pool, key=lambda row: str(row["contract_id"]))[0] if pool else None
    if not chosen:
        return {"available": False, "target_outcome_hidden": True, "contrast_outcome_hidden": True}
    return {
        "available": True,
        "contract_id": chosen["contract_id"],
        "question": chosen["question"],
        "source": chosen.get("source"),
        "source_corpus": chosen.get("source_corpus"),
        "target_outcome_hidden": True,
        "contrast_outcome_hidden": True,
        "selection_rule": "same_source_opposite_outcome_when_available_else_same_source",
    }


def selective_action_regime() -> dict[str, Any]:
    return {
        "regime_id": "n1_symmetric_with_review_cost_v1",
        "forecast_action": {
            "correct": 1.0,
            "incorrect": -1.0,
        },
        "abstain_action": {
            "utility": 0.0,
        },
        "reroute_or_judge_action": {
            "utility_if_correct_after_review": 0.9,
            "utility_if_incorrect_after_review": -1.1,
            "review_cost": 0.1,
        },
        "decision_rule_required_from_model": [
            "forecast",
            "abstain",
            "reroute_or_judge",
        ],
        "declared_before_outcomes": True,
    }


def prompt_contract_for(
    arm: dict[str, str],
    contract: dict[str, Any],
    selected_contracts: list[dict[str, Any]],
    all_contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": arm["instruction"],
        "tests": arm["tests"],
        "required_output_fields": ["p_success"],
    }
    if arm["condition"] == "diagnostic_only":
        payload["required_output_fields"] = [
            "p_success",
            "worry",
            "bid_ask_low",
            "bid_ask_high",
            "self_predicted_brier",
        ]
        payload["correction_allowed"] = False
    elif arm["condition"] == "reference_class_numeric":
        payload["reference_class"] = reference_class_for(contract, all_contracts)
        payload["required_output_fields"] = [
            "p_success_before_reference",
            "reference_class_yes_rate_used",
            "p_success",
            "revision_delta",
        ]
    elif arm["condition"] == "contrastive_numeric_revision":
        payload["contrast_case"] = contrast_case_for(contract, selected_contracts)
        payload["required_output_fields"] = [
            "p_success_initial",
            "contrast_relative_likelihood",
            "p_success",
            "revision_delta",
        ]
    elif arm["condition"] == "selective_action":
        payload["utility_regime"] = selective_action_regime()
        payload["required_output_fields"] = [
            "p_success",
            "worry",
            "selected_action",
            "expected_utility",
            "action_rationale_short",
        ]
    return payload


def dispatch_rows(
    contracts: list[dict[str, Any]],
    *,
    families: tuple[str, ...],
    pilot_id: str,
    all_contracts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for contract in contracts:
        for family in families:
            for arm in ARMS:
                dispatch_id = "|".join([pilot_id, str(contract["contract_id"]), family, arm["condition"]])
                rows.append(
                    {
                        "dispatch_id": hashlib.sha256(dispatch_id.encode("utf-8")).hexdigest()[:16],
                        "pilot_id": pilot_id,
                        "contract_id": contract["contract_id"],
                        "family": family,
                        "agent_id": family,
                        "runtime_route": RUNTIME_BY_FAMILY.get(family, "manual_or_registered_runtime"),
                        "arm": arm["arm"],
                        "condition": arm["condition"],
                        "primitive": "n1_forecast_nurture_intervention",
                        "question": contract["question"],
                        "source": contract["source"],
                        "source_corpus": contract["source_corpus"],
                        "post_training_cutoff": contract["post_training_cutoff"],
                        "resolution_source_url": contract["resolution_source_url"],
                        "prompt_contract": prompt_contract_for(
                            arm,
                            contract,
                            contracts,
                            all_contracts,
                        ),
                    }
                )
    return rows


def smoke_rows(rows: list[dict[str, Any]], *, max_contracts: int, max_families: int) -> list[dict[str, Any]]:
    contract_ids = []
    for row in rows:
        cid = row["contract_id"]
        if cid not in contract_ids:
            contract_ids.append(cid)
        if len(contract_ids) >= max_contracts:
            break
    families = []
    for row in rows:
        family = row["family"]
        if family not in families:
            families.append(family)
        if len(families) >= max_families:
            break
    keep_contracts = set(contract_ids)
    keep_families = set(families)
    return [
        row
        for row in rows
        if row["contract_id"] in keep_contracts and row["family"] in keep_families
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_jsonl(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_report(contracts: list[dict[str, Any]], rows: list[dict[str, Any]], *, families: tuple[str, ...]) -> dict[str, Any]:
    carrier_completeness = {}
    for condition in {row["condition"] for row in rows}:
        condition_rows = [row for row in rows if row["condition"] == condition]
        if condition == "reference_class_numeric":
            ok = [
                row for row in condition_rows
                if (row["prompt_contract"].get("reference_class") or {}).get("yes_rate_excluding_target") is not None
            ]
        elif condition == "contrastive_numeric_revision":
            ok = [
                row for row in condition_rows
                if (row["prompt_contract"].get("contrast_case") or {}).get("available")
            ]
        elif condition == "selective_action":
            ok = [
                row for row in condition_rows
                if (row["prompt_contract"].get("utility_regime") or {}).get("declared_before_outcomes")
            ]
        else:
            ok = condition_rows
        carrier_completeness[condition] = {
            "rows": len(condition_rows),
            "carrier_ok_rows": len(ok),
            "complete": len(ok) == len(condition_rows),
        }
    return {
        "schema": "gp245-n1-forecast-nurture-packet-v1",
        "pilot_id": rows[0]["pilot_id"] if rows else "n1_nurture_intervention_v1",
        "contracts": len(contracts),
        "families": list(families),
        "runtime_routes": {
            family: RUNTIME_BY_FAMILY.get(family, "manual_or_registered_runtime")
            for family in families
        },
        "arms": ARMS,
        "dispatch_rows": len(rows),
        "dispatch_sha256": sha256_jsonl(rows),
        "contract_counts_by_source": dict(Counter(row["source"] for row in contracts)),
        "contract_counts_by_source_corpus": dict(Counter(row["source_corpus"] for row in contracts)),
        "contract_counts_by_y_known": dict(Counter(str(row["y_known"]) for row in contracts)),
        "contract_counts_by_cutoff_relation": dict(Counter(str(row["post_training_cutoff"]) for row in contracts)),
        "carrier_completeness": carrier_completeness,
        "score_plan": {
            "primary": "paired Brier by contract/family comparing each intervention arm to baseline",
            "secondary": "predeclared utility for selective_action",
            "controls": [
                "raw probability baseline",
                "simple uncertainty baseline",
                "source/family/base-rate-band stratification where available",
            ],
            "stats": [
                "paired permutation",
                "bootstrap CI",
                "BH-FDR across arms/families",
                "TOST only for predeclared null claims",
            ],
        },
        "promotion_criteria": [
            "an arm beats baseline raw probability on paired Brier or predeclared utility",
            "the same arm beats simple uncertainty controls",
            "the result is not only one source/family cell",
        ],
        "kill_criteria": [
            "no arm beats baseline under paired tests",
            "best result is source/family concentrated",
            "best result changes rationale text without changing probability or utility",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# N1 Forecast Nurture Intervention Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Contracts: {report['contracts']}",
        f"- Families: `{report['families']}`",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Dispatch SHA-256: `{report['dispatch_sha256']}`",
        f"- Source counts: `{report['contract_counts_by_source']}`",
        f"- y_known counts: `{report['contract_counts_by_y_known']}`",
        f"- Carrier completeness: `{report['carrier_completeness']}`",
        "",
        "## Arms",
        "",
    ]
    for arm in report["arms"]:
        lines.append(f"- `{arm['arm']} / {arm['condition']}`: {arm['tests']}")
    lines.extend(
        [
            "",
            "## Score Plan",
            "",
            f"- Primary: {report['score_plan']['primary']}",
            f"- Secondary: {report['score_plan']['secondary']}",
            f"- Controls: `{report['score_plan']['controls']}`",
            f"- Stats: `{report['score_plan']['stats']}`",
            "",
            "## Kill Criteria",
            "",
        ]
    )
    for item in report["kill_criteria"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default="n1_nurture_intervention_v1")
    parser.add_argument("--sources", default="premium_public_clean,manifold,polymarket")
    parser.add_argument("--families", default="claude,codex_55,gemini,deepseek")
    parser.add_argument("--contracts-per-source", type=int, default=8)
    parser.add_argument("--smoke-contracts", type=int, default=2)
    parser.add_argument("--smoke-families", type=int, default=1)
    args = parser.parse_args()
    sources = as_tuple_csv(args.sources)
    families = as_tuple_csv(args.families)
    contracts = load_contracts(args.db, sources=sources, per_source=args.contracts_per_source)
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    all_contracts = [
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
    rows = dispatch_rows(contracts, families=families, pilot_id=args.pilot_id, all_contracts=all_contracts)
    report = build_report(contracts, rows, families=families)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "n1_nurture_intervention_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "n1_nurture_intervention_packet.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    write_jsonl(args.out_dir / "n1_nurture_intervention_dispatch_queue.jsonl", rows)
    write_jsonl(
        args.out_dir / "n1_nurture_intervention_smoke_queue.jsonl",
        smoke_rows(rows, max_contracts=args.smoke_contracts, max_families=args.smoke_families),
    )
    print(f"wrote {args.out_dir / 'n1_nurture_intervention_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
