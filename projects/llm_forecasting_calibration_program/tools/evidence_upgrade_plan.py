#!/usr/bin/env python3
"""Generate a clean evidence-upgrade plan for GP-245.

The plan is paper-facing support, not a lab queue. It separates:

1. the safest path to a broader measurement claim,
2. the live positive-intervention test, and
3. the baseline acquisition needed for any market/human additivity claim.

No network calls, model calls, or database mutation.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/evidence_upgrade_plan_2026_06_17"

CLAIM_MATRIX = PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json"
FOLLOWUP_MATRIX = (
    PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16/decisive_continuation_matrix.json"
)
STRUCTURED_SCORE = PROGRAM / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json"
STRUCTURED_EXTERNAL = (
    PROGRAM / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json"
)
STRUCTURED_CLAUDE = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json"
)
FORECASTBENCH_SCORE = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_forecastbench_score_audit.json"
)
FORECASTBENCH_HUMAN = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_human_comparator_audit.json"
)
PREDICTIONMARKETBENCH_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_predictionmarketbench_row_schema_pilot.json"
)
POLYBENCH_SOURCE = (
    PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16/field_wide_polybench_source_pilot.json"
)
PROPHET_ARENA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_prophet_arena_row_schema_pilot.json"
)

CSV_FIELDS = [
    "rank",
    "track",
    "current_state",
    "minimum_next_action",
    "what_it_could_change",
    "what_would_strengthen",
    "what_would_rule_out",
    "why_not_more_model_calls_first",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    row = cur.execute(sql).fetchone()
    return row[0] if row else None


def nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def fnum(value: Any, digits: int = 6) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def forecastbench_human_summary(report: dict[str, Any], filename: str) -> dict[str, Any]:
    for item in report.get("summaries", []) or []:
        if isinstance(item, dict) and item.get("forecast_file") == filename:
            return item
    return {}


def db_counts(db: Path) -> dict[str, int]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        return {
            "external_market_rows": int(scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines") or 0),
            "equal_information_rows": int(
                scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1") or 0
            ),
            "structured_rows": int(
                scalar(
                    cur,
                    "SELECT COUNT(*) FROM pilot_calls "
                    "WHERE pilot_id='structured_metacognition_public_v1' AND schema_ok=1",
                )
                or 0
            ),
            "structured_contracts": int(
                scalar(
                    cur,
                    "SELECT COUNT(DISTINCT contract_id) FROM pilot_calls "
                    "WHERE pilot_id='structured_metacognition_public_v1' AND schema_ok=1",
                )
                or 0
            ),
        }
    finally:
        con.close()


def status_label(value: Any) -> str:
    text = str(value or "").strip()
    labels = {
        "not_promoted_or_not_ready": "incomplete and not yet supportive",
        "passes_primary_pairwise_gate_pending_source_and_external_controls": (
            "expert-training passed the bare/placebo public-corpus comparison; external controls still pending"
        ),
        "pass": "passed",
        "fail": "failed",
    }
    return labels.get(text, text.replace("_", " ") if text else "unknown")


def row(
    rank: int,
    track: str,
    current_state: str,
    minimum_next_action: str,
    what_it_could_change: str,
    what_would_strengthen: str,
    what_would_rule_out: str,
    why_not_more_model_calls_first: str,
) -> dict[str, str]:
    return {
        "rank": str(rank),
        "track": track,
        "current_state": current_state,
        "minimum_next_action": minimum_next_action,
        "what_it_could_change": what_it_could_change,
        "what_would_strengthen": what_would_strengthen,
        "what_would_rule_out": what_would_rule_out,
        "why_not_more_model_calls_first": why_not_more_model_calls_first,
    }


def build_report(db: Path) -> dict[str, Any]:
    counts = db_counts(db)
    claim_matrix = read_json(CLAIM_MATRIX)
    followups = read_json(FOLLOWUP_MATRIX)
    structured = read_json(STRUCTURED_SCORE)
    structured_external = read_json(STRUCTURED_EXTERNAL)
    structured_claude = read_json(STRUCTURED_CLAUDE)
    forecastbench = read_json(FORECASTBENCH_SCORE)
    forecastbench_human = read_json(FORECASTBENCH_HUMAN)
    predictionmarketbench = read_json(PREDICTIONMARKETBENCH_PILOT)
    polybench = read_json(POLYBENCH_SOURCE)
    prophet_arena = read_json(PROPHET_ARENA_PILOT)
    human_super = forecastbench_human_summary(forecastbench_human, "2024-07-21.ForecastBench.human_super.json")
    human_public = forecastbench_human_summary(forecastbench_human, "2024-07-21.ForecastBench.human_public.json")

    structured_status = status_label(
        structured.get("primary_verdict") or structured.get("verdict") or structured.get("status")
    )
    if structured_external.get("verdict") == "beats_adjusted_bare_market_not_beaten":
        structured_status = (
            "expert-training passed bare/placebo and same-row calibrated-bare checks; "
            "current market overlap has lower market Brier"
        )
    claude_coverage = structured_claude.get("coverage") or {}
    claude_status = (
        f"partial Claude validation has {claude_coverage.get('scored_rows', 'NA')}/"
        f"{claude_coverage.get('planned_rows', 'NA')} rows and "
        f"{claude_coverage.get('complete_contract_family_blocks', 'NA')} complete blocks; "
        "expert-training is not replicated "
        f"(bare delta {fnum(nested(structured_claude, 'condition_gates', 'expert_training_prompt', 'vs_bare', 'mean_delta_brier'))}, "
        f"placebo delta {fnum(nested(structured_claude, 'condition_gates', 'expert_training_prompt', 'vs_placebo', 'mean_delta_brier'))})"
    )
    rows = [
        row(
            1,
            "Broaden the measurement result across public benchmarks",
            (
                f"ForecastBench is already scored over {forecastbench.get('forecast_files_scored', 0)} files and "
                f"{forecastbench.get('unique_scored_row_keys', 0)} resolved row keys "
                f"({forecastbench.get('unique_event_family_keys', 'NA')} event-family keys); "
                "the same-information market-slice result is unchanged by event-family capping; "
                f"the 2024 human-comparator round scores {forecastbench_human.get('forecast_files_scored', 0)} "
                f"files over {forecastbench_human.get('unique_scored_row_keys', 0)} row keys and "
                f"{forecastbench_human.get('unique_event_family_keys', 'NA')} event-family keys, with "
                f"human-super/public aggregate Briers {fnum(human_super.get('resolved_brier_non_imputed'))}/"
                f"{fnum(human_public.get('resolved_brier_non_imputed'))}; "
                "strict market overlap for those human aggregate files is two rows each; "
                f"Prophet Arena sample releases expose {nested(prophet_arena, 'summary', 'task_rows') or 0} "
                f"public task rows and {nested(prophet_arena, 'summary', 'resolved_rows') or 0} resolved rows, "
                "but no submitted model forecast probabilities or same-time baseline probabilities in the fetched samples; "
                f"the public trace-surface check inspected {nested(prophet_arena, 'summary', 'public_repositories_checked') or 0} "
                "AI Prophet repositories and found no public Prophet Arena submission or leaderboard trace archive; "
                f"PredictionMarketBench has {predictionmarketbench.get('market_baseline_rows', 0)} replay market rows "
                f"but no stored model forecast rows; PolyBench source/schema access is recorded, but the database was "
                f"not available through the noninteractive path."
            ),
            (
                "Obtain one more public benchmark family with stored model or agent forecasts, row timestamps, "
                "and resolved outcomes, or acquire Prophet Arena submitted-forecast/leaderboard traces; then repeat "
                "the row-level validity and same-time baseline audit."
            ),
            (
                "Would turn the manuscript from a scoped measurement paper into a broader claim about the row-level "
                "audit requirements for LLM forecasting benchmarks."
            ),
            (
                "At least two additional benchmark families show missing row-level documentation or conclusion "
                "changes after source-currency, label-time, same-time baseline, or event grouping checks."
            ),
            "Additional public benchmark families have complete documentation and unchanged conclusions after audit.",
            (
                "More calls on the existing corpus cannot answer whether public benchmarks share the same validity "
                "problem; this path needs rows and timestamps, not new prompts."
            ),
        ),
        row(
            2,
            "Acquire a larger same-information market or human packet",
            (
                f"The database has {counts['external_market_rows']} external market rows, including "
                f"{counts['equal_information_rows']} same-information rows. Current completed slices have lower market Brier "
                "or are inconclusive."
            ),
            (
                "Acquire a predeclared, source-balanced packet with same-contract market or human baselines sampled "
                "under the same pre-outcome information rule."
            ),
            (
                "Would decide whether model-derived forecasts add useful information beyond a matched market or "
                "human baseline."
            ),
            (
                "A model-derived forecast or predeclared model-plus-baseline blend beats the matched baseline by the "
                "stated Brier margin with source-stratified survival."
            ),
            (
                "The matched market or human baseline remains better, or any apparent gain disappears under source "
                "and event-group checks."
            ),
            (
                "Without matched baselines, extra model calls cannot establish an additive forecast claim; they only "
                "increase the model-only side of the comparison."
            ),
        ),
        row(
            3,
            "Validate the public structured-prompting result",
            (
                f"{counts['structured_rows']}/600 target rows are usable across "
                f"{counts['structured_contracts']} contracts; current score status is {structured_status}; "
                f"{claude_status}."
            ),
            (
                "Complete or explicitly stand down the Claude validation under the same checks, and acquire "
                "larger same-time market or human overlap before spending on another prompt family."
            ),
            (
                "Would decide whether the positive public-corpus prompt result remains a scoped one-family "
                "finding or supports a broader intervention claim."
            ),
            (
                "A predeclared structured-prompt arm beats bare, placebo, same-row calibrated-bare forecasts, "
                "and a larger same-time market or human baseline without source or family regression."
            ),
            (
                "The structured-prompt result fails model-family replication or the market/human overlap continues "
                "to dominate."
            ),
            (
                "The 600-call comparison and same-row calibrated-bare check are already resolved, and the "
                "partial Claude run is not supportive; the open questions are market/human additivity and "
                "whether a completed second-family run changes the boundary."
            ),
        ),
    ]
    return {
        "schema": "gp245-evidence-upgrade-plan-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass",
        "central_claim": claim_matrix.get("central_claim"),
        "source_files": {
            "claim_matrix": rel(CLAIM_MATRIX),
            "followup_matrix": rel(FOLLOWUP_MATRIX),
            "structured_score": rel(STRUCTURED_SCORE),
            "structured_claude": rel(STRUCTURED_CLAUDE),
            "forecastbench_score": rel(FORECASTBENCH_SCORE),
            "forecastbench_human": rel(FORECASTBENCH_HUMAN),
            "prophet_arena_pilot": rel(PROPHET_ARENA_PILOT),
            "predictionmarketbench_pilot": rel(PREDICTIONMARKETBENCH_PILOT),
            "polybench_source": rel(POLYBENCH_SOURCE),
        },
        "followup_rows_seen": len(followups.get("rows") or []),
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Evidence Upgrade Plan",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        str(report.get("central_claim") or ""),
        "",
        "| Rank | Track | Current state | Minimum next action | What it could change |",
        "|---:|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| {rank} | {track} | {current_state} | {minimum_next_action} | {what_it_could_change} |".format(
                **item
            )
        )
    lines.extend(["", "## Decision Details", ""])
    for item in report["rows"]:
        lines.extend(
            [
                f"### {item['rank']}. {item['track']}",
                "",
                f"- Current state: {item['current_state']}",
                f"- Minimum next action: {item['minimum_next_action']}",
                f"- What it could change: {item['what_it_could_change']}",
                f"- What would strengthen it: {item['what_would_strengthen']}",
                f"- What would rule it out: {item['what_would_rule_out']}",
                f"- Why more model calls are not first: {item['why_not_more_model_calls_first']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Source Files",
            "",
        ]
    )
    for label, path in report["source_files"].items():
        lines.append(f"- {label}: `{path}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "evidence_upgrade_plan.json"
    csv_path = args.out_dir / "evidence_upgrade_plan.csv"
    md_path = args.out_dir / "evidence_upgrade_plan.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(render_md(report) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "rows": len(report["rows"]),
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
