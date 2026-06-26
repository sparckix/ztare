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

ALIGNMENT_REQUIREMENTS = (
    {
        "name": "abstract_claim_boundary",
        "zone": "tex_abstract",
        "required": (
            "We define the forecast row as the unit of evidence",
            "The strict market comparisons remain small, so we use them to bound claims",
            "Gemini-specific candidate, not a general prompting method",
            "companion benchmark design",
        ),
    },
    {
        "name": "front_contributions_include_benchmark",
        "zone": "tex_front_before_positioning",
        "required": (
            "The paper makes five contributions",
            "companion benchmark design",
            "These results are not claims that LLMs are superior to markets or humans",
            "The current usable results are a selected calibration rule for eligible rows and pairwise ranking balanced by source",
            "model-specific intervention candidate and a replication target",
            "Additional structured outputs and differences across model families are design evidence",
        ),
    },
    {
        "name": "front_benchmark_boundary",
        "zone": "tex_front_before_positioning",
        "required": (
            "Benchmark design implication",
            r"Table~\ref{tab:benchmark-blueprint}",
            "which claim a packet can test before outcomes are scored",
            "not a current claim about a measured failure rate across the field",
            "rather than collapsed into one leaderboard",
        ),
    },
    {
        "name": "limits_preserve_scope",
        "zone": "tex_limits",
        "required": (
            "It does not show that LLMs beat humans",
            "Gemini-specific candidate",
            "replication on open models and public questions is required",
        ),
    },
    {
        "name": "conclusion_matches_front_claim",
        "zone": "tex_conclusion",
        "required": (
            "scored probabilities do not become forecasting evidence",
            "applied claim is limited but nontrivial",
            "companion benchmark design",
            "useful during research, not only after publication",
        ),
    },
    {
        "name": "reproducibility_supports_claims",
        "zone": "tex_reproducibility",
        "required": (
            "Forecast row validity benchmark blueprint",
            "Numeric claim trace",
            "Raw low-overlap questions",
        ),
    },
    {
        "name": "draft_front_matches_tex",
        "zone": "draft_front_before_positioning",
        "required": (
            "The paper makes five contributions",
            "companion benchmark design",
            "The current usable results are a selected calibration rule for eligible rows and pairwise ranking balanced by source",
            "model-specific intervention candidate and a replication target",
            "Additional structured outputs and differences across model families are design evidence",
            "which claim a packet can test before outcomes are scored",
            "not a current claim about a measured failure rate across the field",
        ),
    },
)


def reader_status(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return (
        value.replace("diagnostic_ready_policy_demoted", "diagnostic_only_policy_not_supported")
        .replace("diagnostic_promoted_policy_translation_demoted", "diagnostic_supported_policy_not_supported")
        .replace("demote_policy_cell_temporal_split_failed", "policy_cell_temporal_split_failed")
        .replace("demoted", "not_supported")
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


def between(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return ""
    tail = text.split(start, 1)[1]
    if end is None or end not in tail:
        return tail
    return tail.split(end, 1)[0]


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def build_zones(paper_paths: tuple[Path, ...]) -> dict[str, str]:
    zones: dict[str, str] = {}
    for path in paper_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "main.tex":
            zones["tex_abstract"] = between(text, r"\begin{abstract}", r"\end{abstract}")
            zones["tex_front_before_positioning"] = text.split(r"\paragraph{Positioning.}", 1)[0]
            zones["tex_limits"] = between(
                text,
                r"\section{What this paper does not establish}",
                r"\paragraph{Effective denominators.}",
            )
            zones["tex_conclusion"] = between(text, r"\section{Conclusion}", r"\section{Reproducibility}")
            zones["tex_reproducibility"] = between(text, r"\section{Reproducibility}", r"\bibliographystyle")
        elif path.name == "draft.md":
            zones["draft_front_before_positioning"] = text.split("#### Positioning.", 1)[0]
    return zones


def build_alignment_checks(paper_paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    zones = build_zones(paper_paths)
    checks: list[dict[str, Any]] = []
    for requirement in ALIGNMENT_REQUIREMENTS:
        zone_name = str(requirement["zone"])
        text = compact_ws(zones.get(zone_name, ""))
        missing = [phrase for phrase in requirement["required"] if phrase not in text]
        checks.append(
            {
                "name": requirement["name"],
                "zone": zone_name,
                "status": "pass" if not missing else "fail",
                "missing": missing,
            }
        )
    return checks


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
    alignment_checks = build_alignment_checks(paper_paths)
    failed_alignment = [row for row in alignment_checks if row["status"] != "pass"]
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
        "alignment_status": "pass" if not failed_alignment else "fail",
        "alignment_checks": alignment_checks,
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
    lines.append(f"- Channel-diagnostic readiness: `{reader_status(result.get('law2_readiness'))}`")
    lines.append(f"- Channel-diagnostic status: `{reader_status(result.get('law2_status'))}`")
    lines.append(f"- Channel-policy verdict: `{reader_status(result.get('law2_policy_cell_verdict'))}`")
    lines.append(f"- Endpoint alignment: `{result.get('alignment_status')}`")
    lines.append(f"- Finding count: {result['finding_count']}")
    lines.append(f"- By severity: `{result['by_severity']}`")
    lines.append("")
    lines.append("## Endpoint Alignment")
    lines.append("")
    lines.append("| Check | Zone | Status | Missing |")
    lines.append("|---|---|---|---|")
    for row in result["alignment_checks"]:
        missing = "; ".join(row["missing"]) if row["missing"] else ""
        lines.append(f"| {row['name']} | {row['zone']} | {row['status']} | {missing} |")
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
