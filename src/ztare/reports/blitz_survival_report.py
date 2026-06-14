"""Read-only survival metrics for autoresearch blitz candidate selection.

The blitz path uses a cheap tournament to pick one mutator candidate before
the normal R1, gate, judge, and champion-selection path runs. This module joins
the existing artifacts from those two phases so operators can see whether the
tournament winner later survived downstream evaluation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError:
        return []
    return rows


def _iteration_number(row: dict[str, Any]) -> int | None:
    raw = row.get("iteration_index", row.get("iteration", row.get("iter")))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _index_by_iteration(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        iteration = _iteration_number(row)
        if iteration is not None:
            out[iteration] = row
    return out


def _selected_candidate_by_iteration(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row.get("record_type") != "candidate" or not row.get("selected_as_winner"):
            continue
        iteration = _iteration_number(row)
        if iteration is not None:
            out[iteration] = row
    return out


def _winner_score_from_blitz_row(row: dict[str, Any]) -> float | None:
    winner_id = row.get("winner_id")
    winner_persona = row.get("winner_persona")
    for score_row in row.get("scores", []) or []:
        if (
            score_row.get("worker_id") == winner_id
            and score_row.get("persona") == winner_persona
        ):
            try:
                return float(score_row.get("score"))
            except (TypeError, ValueError):
                return None
    return None


def _numeric(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify_survival(
    *,
    eval_row: dict[str, Any] | None,
    telemetry_row: dict[str, Any] | None,
) -> str:
    if eval_row is None:
        return "no_downstream_eval"
    score = _numeric(eval_row.get("score"))
    gate_failures = int((telemetry_row or {}).get("gate_failure_count") or 0)
    champion_promoted = bool((telemetry_row or {}).get("champion_promoted"))
    if champion_promoted:
        return "champion_promoted"
    if gate_failures > 0:
        return "evaluated_with_gate_failure"
    if score is not None and score > 0:
        return "evaluated_positive_score"
    return "evaluated_zero_or_missing_score"


@dataclass(frozen=True)
class BlitzSurvivalRow:
    iteration: int
    k: int
    decision_reason: str
    n_after_recombination: int
    n_crossovers: int
    fusion_succeeded: bool
    winner_id: int | None
    winner_persona: str | None
    winner_stage_origin: str | None
    tournament_score: float | None
    selected_candidate_score: float | None
    downstream_eval_present: bool
    eval_score: float | None
    champion_promoted: bool
    gate_failure_count: int
    failed_gate_ids: list[str]
    survival_class: str


def build_blitz_survival_report(workspace_dir: Path | str) -> dict[str, Any]:
    """Join blitz tournament artifacts with downstream evaluation telemetry."""
    workspace = Path(workspace_dir)
    blitz_rows = _read_jsonl(workspace / "parallel_blitz_log.jsonl")
    eval_by_iter = _index_by_iteration(_read_jsonl(workspace / "eval_history.jsonl"))
    telemetry_by_iter = _index_by_iteration(
        [
            row
            for row in _read_jsonl(workspace / "iteration_telemetry.jsonl")
            if row.get("record_type") == "iteration"
        ]
    )
    selected_by_iter = _selected_candidate_by_iteration(_read_jsonl(workspace / "pipeline_log.jsonl"))

    rows: list[BlitzSurvivalRow] = []
    for blitz in blitz_rows:
        iteration = _iteration_number(blitz)
        if iteration is None:
            continue
        eval_row = eval_by_iter.get(iteration)
        telemetry = telemetry_by_iter.get(iteration)
        selected_candidate = selected_by_iter.get(iteration)
        gate_failure_count = int((telemetry or {}).get("gate_failure_count") or 0)
        failed_gate_ids = [
            str(item)
            for item in ((telemetry or {}).get("failed_gate_ids") or [])
        ]
        rows.append(
            BlitzSurvivalRow(
                iteration=iteration,
                k=int(blitz.get("k") or 0),
                decision_reason=str(blitz.get("decision_reason") or ""),
                n_after_recombination=int(blitz.get("n_after_recombination") or 0),
                n_crossovers=int(blitz.get("n_crossovers") or 0),
                fusion_succeeded=bool(blitz.get("fusion_succeeded")),
                winner_id=(
                    int(blitz["winner_id"])
                    if blitz.get("winner_id") is not None
                    else None
                ),
                winner_persona=blitz.get("winner_persona"),
                winner_stage_origin=blitz.get("winner_stage_origin"),
                tournament_score=_winner_score_from_blitz_row(blitz),
                selected_candidate_score=_numeric((selected_candidate or {}).get("score")),
                downstream_eval_present=eval_row is not None,
                eval_score=_numeric((eval_row or {}).get("score")),
                champion_promoted=bool((telemetry or {}).get("champion_promoted")),
                gate_failure_count=gate_failure_count,
                failed_gate_ids=failed_gate_ids,
                survival_class=_classify_survival(eval_row=eval_row, telemetry_row=telemetry),
            )
        )

    rows.sort(key=lambda row: row.iteration)
    total = len(rows)
    downstream = sum(1 for row in rows if row.downstream_eval_present)
    promoted = sum(1 for row in rows if row.champion_promoted)
    gate_clean_positive = sum(
        1
        for row in rows
        if row.downstream_eval_present
        and row.gate_failure_count == 0
        and row.eval_score is not None
        and row.eval_score > 0
    )
    recombination_iters = sum(1 for row in rows if row.n_after_recombination > row.k)
    survival_counts: dict[str, int] = {}
    for row in rows:
        survival_counts[row.survival_class] = survival_counts.get(row.survival_class, 0) + 1

    summary = {
        "workspace_dir": str(workspace),
        "num_blitz_iterations": total,
        "num_downstream_eval_present": downstream,
        "downstream_eval_rate": (downstream / total) if total else None,
        "num_gate_clean_positive": gate_clean_positive,
        "gate_clean_positive_rate": (gate_clean_positive / total) if total else None,
        "num_champion_promoted": promoted,
        "champion_promotion_rate": (promoted / total) if total else None,
        "num_recombination_iterations": recombination_iters,
        "survival_class_counts": dict(sorted(survival_counts.items())),
    }
    return {
        "schema": "ztare-blitz-survival-report-v1",
        "summary": summary,
        "rows": [asdict(row) for row in rows],
    }


def render_blitz_survival_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Blitz Candidate Survival Report",
        "",
        f"- workspace: `{summary.get('workspace_dir', '')}`",
        f"- blitz iterations: `{summary.get('num_blitz_iterations', 0)}`",
        f"- downstream eval rate: `{summary.get('downstream_eval_rate')}`",
        f"- gate-clean positive rate: `{summary.get('gate_clean_positive_rate')}`",
        f"- champion promotion rate: `{summary.get('champion_promotion_rate')}`",
        f"- survival classes: `{summary.get('survival_class_counts', {})}`",
        "",
        "| iter | k | winner | origin | tournament | eval | gates | class |",
        "|---:|---:|---|---|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            "| {iteration} | {k} | {winner_persona} | {winner_stage_origin} | "
            "{tournament_score} | {eval_score} | {gate_failure_count} | {survival_class} |".format(
                **row
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize blitz candidate survival for an autoresearch workspace.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = build_blitz_survival_report(args.workspace)
    payload = json.dumps(report, indent=2 if args.pretty else None, sort_keys=bool(args.pretty)) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_blitz_survival_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
