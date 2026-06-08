#!/usr/bin/env python3
"""Build the N2 selective-action confirmatory packet.

No model calls. No DB mutation. Excludes contracts already called in the N1
adaptive slice, then freezes fresh baseline/selective-action rows.
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
N1_PILOT_ID = "n1_nurture_intervention_v1"
N2_PILOT_ID = "n2_selective_action_confirmatory_v1"

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
        "tests": "raw Brier baseline",
    },
    {
        "arm": "E",
        "condition": "selective_action",
        "instruction": "choose forecast/abstain/reroute/judge under predeclared utility",
        "tests": "confirm whether action framing improves Brier or utility on fresh rows",
    },
]


def as_tuple_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def selective_action_regime() -> dict[str, Any]:
    return {
        "regime_id": "n2_symmetric_with_predeclared_review_resolution_v1",
        "forecast_action": {"correct": 1.0, "incorrect": -1.0},
        "abstain_action": {"utility": 0.0},
        "reroute_or_judge_action": {
            "utility_if_correct_after_review": 0.9,
            "utility_if_incorrect_after_review": -1.1,
            "review_cost": 0.1,
            "resolver": "score as unresolved until independent review labels the reroute/judge decision correct/incorrect",
        },
        "decision_rule_required_from_model": ["forecast", "abstain", "reroute_or_judge"],
        "declared_before_outcomes": True,
    }


def prompt_contract_for(arm: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "include_y_known": False,
        "no_web_tools": True,
        "same_contract_across_arms": True,
        "instruction": arm["instruction"],
        "tests": arm["tests"],
        "required_output_fields": ["p_success"],
    }
    if arm["condition"] == "selective_action":
        payload["utility_regime"] = selective_action_regime()
        payload["required_output_fields"] = [
            "p_success",
            "worry",
            "selected_action",
            "expected_utility",
            "action_rationale_short",
        ]
    return payload


def called_contract_ids(con: sqlite3.Connection, pilot_id: str) -> set[str]:
    return {
        str(row[0])
        for row in con.execute(
            "SELECT DISTINCT contract_id FROM pilot_calls WHERE pilot_id = ?",
            (pilot_id,),
        )
    }


def load_contracts(db: Path, *, sources: tuple[str, ...], per_source: int, exclude_contracts: set[str]) -> list[dict[str, Any]]:
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
        if row["contract_id"] in exclude_contracts:
            continue
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
        half = per_source // 2
        picked = yes[:half] + no[: per_source - half]
        if len(picked) < per_source:
            seen = {row["contract_id"] for row in picked}
            picked.extend([row for row in candidates if row["contract_id"] not in seen][: per_source - len(picked)])
        selected.extend(picked[:per_source])
    return selected


def dispatch_rows(contracts: list[dict[str, Any]], *, families: tuple[str, ...], pilot_id: str) -> list[dict[str, Any]]:
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
                        "prompt_contract": prompt_contract_for(arm),
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
        "# N2 Selective-Action Confirmatory Packet",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Contracts: {report['contracts']}",
        f"- Dispatch rows: {report['dispatch_rows']}",
        f"- Families: `{report['families']}`",
        f"- Source counts: `{report['contract_counts_by_source']}`",
        f"- y_known counts: `{report['contract_counts_by_y_known']}`",
        f"- Dispatch SHA-256: `{report['dispatch_sha256']}`",
        "",
        "## Arms",
        "",
    ]
    for arm in ARMS:
        lines.append(f"- `{arm['condition']}`: {arm['tests']}")
    lines.extend(
        [
            "",
            "## Confirmatory Rule",
            "",
            "- This packet excludes contracts already called in N1.",
            "- The N1 p-value is descriptive/adaptive; N2 is the confirmation surface.",
            "- Promote only if selective action beats baseline on paired Brier and does not collapse under family/source split.",
            "- Score reroute/judge only after an independent review result is available.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=N2_PILOT_ID)
    parser.add_argument("--exclude-pilot-id", default=N1_PILOT_ID)
    parser.add_argument("--sources", default="manifold,polymarket")
    parser.add_argument("--families", default="claude,codex_55,gemini,deepseek")
    parser.add_argument("--contracts-per-source", type=int, default=6)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    exclude = called_contract_ids(con, args.exclude_pilot_id)
    con.close()
    contracts = load_contracts(
        args.db,
        sources=as_tuple_csv(args.sources),
        per_source=args.contracts_per_source,
        exclude_contracts=exclude,
    )
    families = as_tuple_csv(args.families)
    rows = dispatch_rows(contracts, families=families, pilot_id=args.pilot_id)
    report = {
        "schema": "gp245-n2-selective-action-confirmatory-packet-v1",
        "pilot_id": args.pilot_id,
        "excluded_pilot_id": args.exclude_pilot_id,
        "excluded_contracts": len(exclude),
        "contracts": len(contracts),
        "families": list(families),
        "arms": ARMS,
        "dispatch_rows": len(rows),
        "dispatch_sha256": sha256_jsonl(rows),
        "contract_counts_by_source": dict(Counter(row["source"] for row in contracts)),
        "contract_counts_by_y_known": dict(Counter(str(row["y_known"]) for row in contracts)),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "n2_selective_action_confirmatory_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "n2_selective_action_confirmatory_packet.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    write_jsonl(args.out_dir / "n2_selective_action_confirmatory_dispatch_queue.jsonl", rows)
    print(f"wrote {args.out_dir / 'n2_selective_action_confirmatory_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
