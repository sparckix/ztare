#!/usr/bin/env python3
"""Scan the GP-245 paper for claim/readiness drift.

No model calls and no DB writes. This report compares the current law-readiness
JSON against wording in the working paper and flags places where the paper still
uses deployment-policy language after a law has been demoted or scoped down.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
PAPER_ROOT = REPO / "papers/llm-forecast-calibration-cross-corpus"
DEFAULT_READINESS = PROGRAM_ROOT / "law_validation_v1/workspace/law_readiness_report.json"
DEFAULT_OUT = PROGRAM_ROOT / "paper_alignment_v1/workspace"
DEFAULT_PAPERS = (
    PAPER_ROOT / "draft.md",
    PAPER_ROOT / "main.tex",
)


POLICY_PATTERNS = (
    ("deployable_recipe", re.compile(r"\bdeployable recipe\b", re.I)),
    ("deployment_implication", re.compile(r"\bdeployment implication\b", re.I)),
    ("deployment_recipe", re.compile(r"\bdeployment recipe\b", re.I)),
    ("deployed_yaml", re.compile(r"\bdeployed YAML\b", re.I)),
    ("deployable_rule", re.compile(r"\bdeployable rule\b", re.I)),
    ("runtime_calibration_warning", re.compile(r"\bruntime calibration warning\b", re.I)),
    ("conditional_router_deployment", re.compile(r"\bconditional-router deployment\b", re.I)),
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def law_by_name(readiness: dict[str, Any], law_name: str) -> dict[str, Any]:
    for law in readiness.get("laws", []):
        if law.get("law") == law_name:
            return law
    return {}


def line_window(lines: list[str], index: int, radius: int = 1) -> str:
    lo = max(0, index - radius)
    hi = min(len(lines), index + radius + 1)
    return " ".join(line.strip() for line in lines[lo:hi] if line.strip())


def scan_paper(path: Path, law2: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[dict[str, Any]] = []
    law2_demoted = law2.get("readiness") == "diagnostic_ready_policy_demoted"
    for idx, line in enumerate(lines, start=1):
        context = line_window(lines, idx - 1)
        for label, pattern in POLICY_PATTERNS:
            if not pattern.search(line):
                continue
            severity = "info"
            recommendation = "Check that the sentence describes a demoted policy or a hypothesis, not a current deployment claim."
            if law2_demoted:
                severity = "needs_review"
                recommendation = (
                    "Law 2 policy translation is demoted; phrase this as diagnostic, "
                    "hypothesis-generating, or prospective-only."
                )
            findings.append(
                {
                    "file": str(path.relative_to(REPO)),
                    "line": idx,
                    "pattern": label,
                    "severity": severity,
                    "text": line.strip(),
                    "context": context,
                    "recommendation": recommendation,
                }
            )
    return findings


def build_report(readiness_path: Path, paper_paths: tuple[Path, ...]) -> dict[str, Any]:
    readiness = read_json(readiness_path)
    law2 = law_by_name(readiness, "family_channel_error_surface")
    findings: list[dict[str, Any]] = []
    for path in paper_paths:
        findings.extend(scan_paper(path, law2))
    by_severity: dict[str, int] = {}
    for row in findings:
        by_severity[row["severity"]] = by_severity.get(row["severity"], 0) + 1
    return {
        "schema": "gp245-paper-claim-alignment-v1",
        "readiness_report": str(readiness_path),
        "law2_readiness": law2.get("readiness"),
        "law2_status": law2.get("status"),
        "law2_policy_cell_verdict": (law2.get("current_evidence") or {}).get("policy_cell_verdict"),
        "paper_files": [str(path) for path in paper_paths],
        "finding_count": len(findings),
        "by_severity": by_severity,
        "findings": findings,
        "interpretation": (
            "Policy/deployment wording must be scoped when readiness says the "
            "current policy translation is demoted."
        ),
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "paper_claim_alignment_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# GP-245 Paper Claim Alignment Report", ""]
    lines.append(f"- Law 2 readiness: `{result.get('law2_readiness')}`")
    lines.append(f"- Law 2 status: `{result.get('law2_status')}`")
    lines.append(f"- Law 2 policy verdict: `{result.get('law2_policy_cell_verdict')}`")
    lines.append(f"- Finding count: {result['finding_count']}")
    lines.append(f"- By severity: `{result['by_severity']}`")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not result["findings"]:
        lines.append("- None.")
    for row in result["findings"]:
        lines.append(
            f"- `{row['severity']}` `{row['pattern']}` "
            f"[{row['file']}:{row['line']}]: {row['text']}"
        )
        lines.append(f"  Recommendation: {row['recommendation']}")
    lines.append("")
    (out_dir / "paper_claim_alignment_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--paper", type=Path, action="append")
    args = parser.parse_args()
    papers = tuple(args.paper) if args.paper else DEFAULT_PAPERS
    result = build_report(args.readiness, papers)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
