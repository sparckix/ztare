#!/usr/bin/env python3
"""Summarize how the GP-245 paper compresses the historical findings ledger.

The paper cannot include every pilot. This tool reads the local findings
ledger plus the current pilot queue and emits a reader-facing count summary:
what became central evidence, what became diagnostics, what became limits, and
what was excluded as sibling work.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_LEDGER = WORKSPACE / "findings_completeness_ledger.md"
DEFAULT_RESEARCH_LOG = WORKSPACE / "research_log.md"
DEFAULT_QUEUE = WORKSPACE / "pilot_queue.md"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/experiment_coverage_2026_06_16"
STRUCTURED_SCORE = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json"
)
STRUCTURED_EXTERNAL = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json"
)

CATEGORY_BY_ROW = {
    # Central GP-245 claims or explicit quantitative boundaries.
    "F99": "central_validity_control_or_calibration",
    "F100": "central_validity_control_or_calibration",
    "F101": "central_validity_control_or_calibration",
    # Diagnostics retained in the main text or appendix.
    "F8": "secondary_diagnostic",
    "F10": "secondary_diagnostic",
    "F36": "secondary_diagnostic",
    "F40": "secondary_diagnostic",
    "F54": "secondary_diagnostic",
    "F56": "secondary_diagnostic",
    "F58": "secondary_diagnostic",
    "F60": "secondary_diagnostic",
    "F61": "secondary_diagnostic",
    "F62": "secondary_diagnostic",
    "F71": "secondary_diagnostic",
    "F72": "secondary_diagnostic",
    "F73": "secondary_diagnostic",
    "F74": "secondary_diagnostic",
    "F75": "secondary_diagnostic",
    "F84": "secondary_diagnostic",
    "F86": "secondary_diagnostic",
    "F89": "secondary_diagnostic",
    "F102": "secondary_diagnostic",
    # Retractions, superseded pilots, and underpowered rows used as limits.
    "F42": "claim_boundary_or_retraction",
    "F44": "claim_boundary_or_retraction",
    "F47": "claim_boundary_or_retraction",
    "F48": "claim_boundary_or_retraction",
    "F49": "claim_boundary_or_retraction",
    "F95": "claim_boundary_or_retraction",
    "F97": "claim_boundary_or_retraction",
    # Sibling tasks excluded from GP-245's forecasting-row validity argument.
    "F12": "sibling_or_workflow_excluded",
    "F13": "sibling_or_workflow_excluded",
    "F14": "sibling_or_workflow_excluded",
    "F15": "sibling_or_workflow_excluded",
    "F69": "sibling_or_workflow_excluded",
    "F70": "sibling_or_workflow_excluded",
    "F103": "sibling_or_workflow_excluded",
    # Execution repair rather than a scientific claim.
    "F96": "execution_or_persistence_only",
}

CATEGORY_LABELS = {
    "central_validity_control_or_calibration": "Central validity/control/calibration evidence",
    "secondary_diagnostic": "Secondary diagnostics retained in the paper",
    "claim_boundary_or_retraction": "Retractions, supersessions, or underpowered boundaries",
    "sibling_or_workflow_excluded": "Sibling workflow or non-forecasting findings excluded from GP-245",
    "execution_or_persistence_only": "Execution or persistence rows with no paper claim",
}

CATEGORY_NOTES = {
    "central_validity_control_or_calibration": (
        "Used for the main validity, market-boundary, and low-probability calibration story."
    ),
    "secondary_diagnostic": (
        "Kept as channel, prompt-stability, or family/source diagnostics rather than broad claims."
    ),
    "claim_boundary_or_retraction": (
        "Preserved as scope control: these rows explain why broader or older claims are not made."
    ),
    "sibling_or_workflow_excluded": (
        "Excluded because they ask a different question from forecast-row validity."
    ),
    "execution_or_persistence_only": (
        "Recorded for reproducibility, not used as evidence for a scientific claim."
    ),
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def parse_ledger(path: Path) -> list[dict[str, str]]:
    rows = []
    pattern = re.compile(r"^\|\s*(F\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        row_id, headline, verdict, state = match.groups()
        category = CATEGORY_BY_ROW.get(row_id, "unclassified")
        rows.append(
            {
                "internal_row_id": row_id,
                "headline": headline.strip(),
                "verdict": verdict.strip(),
                "state": state.strip(),
                "category": category,
            }
        )
    unknown = sorted(row["internal_row_id"] for row in rows if row["category"] == "unclassified")
    if unknown:
        raise RuntimeError(f"Unclassified findings ledger rows: {', '.join(unknown)}")
    return rows


def parse_research_log(path: Path) -> dict[str, Any]:
    """Count unique numbered findings in the full living research log.

    The curated completeness ledger is the paper-facing subset. The research
    log is larger and includes historical, workflow, deprecated, and later
    continuation rows. Count unique row numbers without exposing the row labels
    in the public markdown output.
    """
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    numbers: set[int] = set()
    for pattern in [
        re.compile(r"^## F(\d+)\b", re.MULTILINE),
        re.compile(r"^\|\s*F(\d+)\s*\|", re.MULTILINE),
    ]:
        for match in pattern.finditer(text):
            numbers.add(int(match.group(1)))
    return {
        "source": rel(path),
        "unique_rows_detected": len(numbers),
        "highest_numbered_row": max(numbers) if numbers else 0,
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def structured_status_label(status: Any) -> str:
    text = str(status or "").strip()
    labels = {
        "passes_primary_pairwise_gate_pending_source_and_external_controls": (
            "expert-training passed the bare/placebo public-corpus comparison; external controls still pending"
        ),
        "not_promoted_or_not_ready": "incomplete and not yet supportive",
    }
    return labels.get(text, text.replace("_", " ") if text else "unknown")


def parse_queue(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    rows_match = re.search(r"(\d+)\s*/\s*(\d+)\s+(?:target rows|usable rows|minimum-useful)", text)
    verdict_match = re.search(r"Current score report remains `([^`]+)`", text)
    plain_verdict_match = re.search(r"Current score report remains ([^.]+)\.", text)
    status = "unknown"
    if verdict_match:
        raw_status = verdict_match.group(1)
        status = "not supported yet" if raw_status == "not_promoted_or_not_ready" else raw_status.replace("_", " ")
    elif plain_verdict_match:
        status = plain_verdict_match.group(1).strip()

    score = read_json(STRUCTURED_SCORE)
    coverage = score.get("coverage") or {}
    scored_rows = coverage.get("scored_rows")
    planned_rows = coverage.get("planned_rows")
    if scored_rows is not None and planned_rows is not None:
        rows_text = f"{scored_rows}/{planned_rows}"
    else:
        rows_text = f"{rows_match.group(1)}/{rows_match.group(2)}" if rows_match else "unknown"
    score_status = structured_status_label(
        score.get("primary_verdict") or score.get("verdict") or score.get("status")
    )
    external = read_json(STRUCTURED_EXTERNAL)
    if external.get("verdict") == "beats_adjusted_bare_market_not_beaten":
        score_status = (
            "expert-training passed bare/placebo and same-row calibrated-bare checks; "
            "market and family checks remain open"
        )
    if score_status != "unknown":
        status = score_status

    return {
        "source": rel(path),
        "score_source": rel(STRUCTURED_SCORE),
        "current_intervention_rows": rows_text,
        "current_intervention_status": status,
    }


def summarize(
    rows: list[dict[str, str]],
    research_log: dict[str, Any],
    queue: dict[str, str],
    generated_at: str,
) -> dict[str, Any]:
    counts = Counter(row["category"] for row in rows)
    category_rows = []
    for category, label in CATEGORY_LABELS.items():
        category_rows.append(
            {
                "category": category,
                "label": label,
                "count": counts.get(category, 0),
                "paper_role": CATEGORY_NOTES[category],
            }
        )
    return {
        "schema": "gp245-experiment-coverage-summary-v1",
        "generated_at": generated_at,
        "ledger_source": rel(DEFAULT_LEDGER),
        "ledger_rows": len(rows),
        "research_log": {
            **research_log,
            "curated_ledger_rows": len(rows),
            "rows_outside_curated_ledger": max(0, int(research_log.get("unique_rows_detected", 0)) - len(rows)),
        },
        "category_rows": category_rows,
        "current_queue": queue,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = ["category", "label", "count", "paper_role"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Experiment Coverage Summary",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        f"Findings ledger rows classified: `{summary['ledger_rows']}`",
        f"Findings ledger source: `{summary['ledger_source']}`",
        f"Unique rows detected in full research log: `{summary['research_log']['unique_rows_detected']}`",
        f"Highest numbered row detected in full research log: `{summary['research_log']['highest_numbered_row']}`",
        f"Rows outside the curated paper ledger: `{summary['research_log']['rows_outside_curated_ledger']}`",
        f"Research log source: `{summary['research_log']['source']}`",
        "",
        "| Paper role | Count | Meaning |",
        "|---|---:|---|",
    ]
    for row in summary["category_rows"]:
        lines.append(f"| {row['label']} | {row['count']} | {row['paper_role']} |")
    queue = summary["current_queue"]
    lines.extend(
        [
            "",
            "## Current Intervention Queue",
            "",
            f"- Queue source: `{queue['source']}`",
            f"- Score source: `{queue['score_source']}`",
            f"- Structured-intervention rows scored: `{queue['current_intervention_rows']}`",
            f"- Current score status: {queue['current_intervention_status']}",
            "",
            "This summary is a coverage check, not a new empirical result. Its purpose is to show that omitted pilots were classified by paper role before the manuscript compressed them.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--research-log", type=Path, default=DEFAULT_RESEARCH_LOG)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = parse_ledger(args.ledger)
    research_log = parse_research_log(args.research_log)
    queue = parse_queue(args.queue)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary = summarize(rows, research_log, queue, generated_at)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "experiment_coverage_summary.json"
    csv_path = args.out_dir / "experiment_coverage_summary.csv"
    md_path = args.out_dir / "experiment_coverage_summary.md"

    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, summary["category_rows"])
    md_path.write_text(build_markdown(summary), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "ledger_rows": summary["ledger_rows"],
                "research_log_unique_rows": summary["research_log"]["unique_rows_detected"],
                "research_log_highest_numbered_row": summary["research_log"]["highest_numbered_row"],
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
