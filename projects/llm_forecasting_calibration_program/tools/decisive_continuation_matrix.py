#!/usr/bin/env python3
"""Generate the GP-245 decisive-continuation matrix.

No network, no model calls, no database mutation. The matrix ranks the next
experiments or acquisitions by the manuscript claim they could change, and
records the minimum next step plus the results that would strengthen or rule
out the claim.
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
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/decisive_continuation_2026_06_16"

CLAIM_GAP = PROGRAM / "paper_alignment_v1/workspace/claim_gap_matrix_2026_06_16/claim_gap_matrix.json"
PILOT_QUEUE = PROGRAM / "forecaster_skill_calibration_v1/workspace/pilot_queue.md"
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

STATUS_LABELS = {
    "not_promoted_or_not_ready": "incomplete and not yet supportive",
    "passes_primary_pairwise_gate_pending_source_and_external_controls": (
        "expert-training passed the bare/placebo public-corpus comparison; external controls still pending"
    ),
    "pass": "passed",
    "fail": "failed",
}


COLUMNS = [
    "rank",
    "continuation",
    "claim_impact",
    "current_state",
    "minimum_next_step",
    "result_that_would_strengthen",
    "result_that_would_rule_out",
    "manuscript_effect",
    "evidence_sources",
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
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


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


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    row = cur.execute(sql).fetchone()
    return row[0] if row else None


def db_summary(db: Path) -> dict[str, int]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        return {
            "external_market_rows": int(scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines") or 0),
            "equal_information_rows": int(
                scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1") or 0
            ),
            "source_currency_rows": int(scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows") or 0),
            "label_time_rows": int(scalar(cur, "SELECT COUNT(*) FROM dataset_label_time_gate_rows") or 0),
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


def fmt_sources(*paths: Path) -> str:
    return "; ".join(rel(path) for path in paths if path.exists())


def human_status(value: Any) -> str:
    text = str(value or "").strip()
    return STATUS_LABELS.get(text, text.replace("_", " ") if text else "unknown")


def row(
    rank: int,
    continuation: str,
    claim_impact: str,
    current_state: str,
    minimum_next_step: str,
    result_that_would_strengthen: str,
    result_that_would_rule_out: str,
    manuscript_effect: str,
    evidence_sources: str,
) -> dict[str, str]:
    return {
        "rank": str(rank),
        "continuation": continuation,
        "claim_impact": claim_impact,
        "current_state": current_state,
        "minimum_next_step": minimum_next_step,
        "result_that_would_strengthen": result_that_would_strengthen,
        "result_that_would_rule_out": result_that_would_rule_out,
        "manuscript_effect": manuscript_effect,
        "evidence_sources": evidence_sources,
    }


def build_report(db: Path) -> dict[str, Any]:
    counts = db_summary(db)
    claim_gap = read_json(CLAIM_GAP)
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

    structured_status = human_status(
        structured.get("primary_verdict") or structured.get("verdict") or structured.get("status")
    )
    if structured_external.get("verdict") == "beats_adjusted_bare_market_not_beaten":
        structured_status = (
            "expert-training passed bare/placebo and same-row calibrated-bare checks; "
            "current market overlap has lower market Brier"
        )
    claude_coverage = structured_claude.get("coverage") or {}
    claude_gates = structured_claude.get("condition_gates") or {}
    claude_expert = claude_gates.get("expert_training_prompt") or {}
    claude_audit = claude_gates.get("audit_informed_prompt") or {}
    claude_status = (
        f"Partial Claude validation has {claude_coverage.get('scored_rows', 'NA')}/"
        f"{claude_coverage.get('planned_rows', 'NA')} rows and "
        f"{claude_coverage.get('complete_contract_family_blocks', 'NA')} complete blocks; "
        "expert-training versus bare delta="
        f"{fnum(nested(claude_expert, 'vs_bare', 'mean_delta_brier'))}, versus placebo delta="
        f"{fnum(nested(claude_expert, 'vs_placebo', 'mean_delta_brier'))}; "
        "audit-informed is directionally favorable on mean but does not clear sign-test or source checks"
    )
    rows = [
        row(
            1,
            "Public benchmark validity extension",
            "Could turn the scoped row-validity result into a field-level measurement claim.",
            (
                f"ForecastBench score audit has {forecastbench.get('forecast_files_scored', 0)} files and "
                f"{forecastbench.get('unique_scored_row_keys', 0)} unique resolved row keys; "
                f"the 2024 human-comparator round has {forecastbench_human.get('forecast_files_scored', 0)} files, "
                f"{forecastbench_human.get('unique_scored_row_keys', 0)} row keys, "
                f"{forecastbench_human.get('unique_event_family_keys', 'NA')} event-family keys, and "
                f"human-super/public aggregate Briers {fnum(human_super.get('resolved_brier_non_imputed'))}/"
                f"{fnum(human_public.get('resolved_brier_non_imputed'))}, but only two strict market-overlap "
                "rows per human aggregate file; "
                f"Prophet Arena public samples expose {nested(prophet_arena, 'summary', 'task_rows') or 0} "
                f"task rows and {nested(prophet_arena, 'summary', 'resolved_rows') or 0} resolved rows, "
                "but no submitted forecast or same-time baseline probabilities; "
                f"its public trace-surface check inspected {nested(prophet_arena, 'summary', 'public_repositories_checked') or 0} "
                "AI Prophet repositories and found no public Prophet Arena submission or leaderboard trace archive; "
                f"PredictionMarketBench has {predictionmarketbench.get('market_baseline_rows', 0)} replay "
                f"market rows but {predictionmarketbench.get('stored_model_forecast_rows', 0)} stored model rows; "
                f"PolyBench database_ready={polybench.get('database_ready')}."
            ),
            "Acquire at least one more public benchmark family with stored model or agent forecasts and row-level timestamps, or acquire Prophet Arena submitted-forecast/leaderboard traces.",
            "Two or more additional public benchmark families show missing row-level validity fields or conclusion changes after repair.",
            "Additional public benchmark families have complete row documentation and no conclusion changes.",
            "Would support a broader measurement paper without requiring LLMs to beat markets.",
            fmt_sources(
                CLAIM_GAP,
                FORECASTBENCH_SCORE,
                FORECASTBENCH_HUMAN,
                PROPHET_ARENA_PILOT,
                PREDICTIONMARKETBENCH_PILOT,
                POLYBENCH_SOURCE,
            ),
        ),
        row(
            2,
            "Larger equal-information market or human packet",
            "Could change the current market-boundary result or confirm that markets remain the stronger baseline.",
            (
                f"Current database has {counts['external_market_rows']} external market rows and "
                f"{counts['equal_information_rows']} equal-information rows; current completed slices have lower market Brier "
                "or are inconclusive."
            ),
            "Acquire a predeclared, source-balanced packet with same-contract market or human baselines sampled under the same pre-outcome rule.",
            "A model-derived forecast or predeclared model+baseline blend beats the matched baseline by the stated Brier margin with source-stratified survival.",
            "The matched baseline remains better or any apparent gain disappears under source/event-family checks.",
            "Would determine whether the paper can claim additivity beyond market or human baselines.",
            fmt_sources(CLAIM_GAP),
        ),
        row(
            3,
            "Structured-prompting validation",
            "Could decide whether the completed positive prompt result stays scoped or generalizes.",
            (
                f"{counts['structured_rows']}/600 target rows are usable across "
                f"{counts['structured_contracts']} contracts; current score status is {structured_status}. "
                f"{claude_status}."
            ),
            "Complete or explicitly stand down the Claude validation under the same checks, and acquire larger same-time market or human overlap before spending on another prompt family.",
            "A predeclared structured-prompt arm beats bare, placebo, same-row calibrated-bare forecasts, and a larger same-time market or human baseline without source or family regression.",
            "The result fails model-family replication or the market/human overlap continues to dominate.",
            "Would determine whether the manuscript can move beyond a scoped one-family intervention result.",
            fmt_sources(PILOT_QUEUE, STRUCTURED_SCORE, STRUCTURED_EXTERNAL, STRUCTURED_CLAUDE, CLAIM_GAP),
        ),
        row(
            4,
            "Prospective pairwise ranking market-freeze score",
            "Could move pairwise ranking from supported ranking evidence toward a probability or blend claim.",
            "A prospective Polymarket packet exists with frozen market bars, but unresolved outcomes prevent scoring.",
            "Preserve the frozen packet, complete hidden-market model calls if still needed, and score after market resolution.",
            "Predeclared pairwise-derived probabilities or a model+market blend beat raw, calibrated, and market-only controls without source/event-family regression.",
            "Pairwise-derived probabilities lose to raw, calibrated, or market-only controls, or the result remains underpowered.",
            "Would decide whether pairwise ranking remains a ranking-only result or becomes a stronger controlled-use result.",
            fmt_sources(CLAIM_GAP, PILOT_QUEUE),
        ),
        row(
            5,
            "Non-Manifold source-currency replication",
            "Could generalize the source-currency result beyond the main Manifold panel.",
            (
                f"Current validity support includes {counts['source_currency_rows']} source-currency rows and "
                f"{counts['label_time_rows']} label-time rows; FRED current-label positives weaken after vintage repair."
            ),
            "Acquire a non-Manifold matched pre/post panel with admissible label vintage and pre-outcome baselines where available.",
            "Post-cutoff rows remain harder after label-time repair, base-rate checks, and source/event-family stratification.",
            "Effect vanishes or flips after label-time repair or source/base-rate matching.",
            "Would change the source-currency claim from source-supported to source-general.",
            fmt_sources(CLAIM_GAP),
        ),
        row(
            6,
            "Open-weight public replication",
            "Could establish provider-independent generality for the current scoped claims.",
            "The current scored calls use proprietary APIs or CLIs; open-weight replication has not been run.",
            "Repeat the public-corpus validity, market-control, low-probability calibration, and pairwise-ranking checks on open-weight models.",
            "The scoped claims reproduce or the model-family differences are precisely bounded.",
            "The claims depend on proprietary providers and do not transfer to open-weight models.",
            "Would change the generality boundary, not the current provider-snapshot evidence.",
            fmt_sources(CLAIM_GAP),
        ),
        row(
            7,
            "Public substitute for the private low-overlap corpus",
            "Could move low-overlap elicitation diagnostics from secondary evidence to externally checkable results.",
            "Low-overlap findings are private and confounded with novelty, source, topic, length, and horizon.",
            "Release a sanitized corpus or build a public niche-domain substitute with the same design axes.",
            "Key elicitation diagnostics replicate after the novelty/source/topic/horizon split is broken.",
            "Diagnostics disappear or are explained by source, length, topic, or horizon.",
            "Would affect the secondary diagnostics and external reproducibility, not the main market-boundary result.",
            fmt_sources(CLAIM_GAP),
        ),
    ]
    return {
        "schema": "gp245-decisive-continuation-matrix-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass",
        "claim_gap_central_claim": claim_gap.get("central_claim"),
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Follow-up Priority Matrix",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['status']}`",
        f"- Central claim: {report.get('claim_gap_central_claim')}",
        "",
        "| Rank | Follow-up | Claim impact | Minimum next step | What would rule it out |",
        "|---:|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| {rank} | {continuation} | {claim_impact} | {minimum_next_step} | {result_that_would_rule_out} |".format(
                **item
            )
        )
    lines.extend(["", "## Details", ""])
    for item in report["rows"]:
        lines.extend(
            [
                f"### {item['rank']}. {item['continuation']}",
                "",
                f"- Claim impact: {item['claim_impact']}",
                f"- Current state: {item['current_state']}",
                f"- Minimum next step: {item['minimum_next_step']}",
                f"- What would strengthen it: {item['result_that_would_strengthen']}",
                f"- What would rule it out: {item['result_that_would_rule_out']}",
                f"- Manuscript effect: {item['manuscript_effect']}",
                f"- Evidence sources: {item['evidence_sources']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "decisive_continuation_matrix.json"
    csv_path = args.out_dir / "decisive_continuation_matrix.csv"
    md_path = args.out_dir / "decisive_continuation_matrix.md"

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
