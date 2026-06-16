#!/usr/bin/env python3
"""Build the evidence map for the GP-245 harnessing thesis.

No model calls and no DB mutation. This audit answers whether the current
evidence supports recasting the existing paper around constrained extraction of
LLM forecast signal, or whether the harnessing material should be split into a
separate paper.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def row(
    *,
    mechanism: str,
    status: str,
    paper_role: str,
    evidence: str,
    supported_claim: str,
    forbidden_claim: str,
    next_gate: str,
    receipts: list[str],
) -> dict[str, Any]:
    return {
        "mechanism": mechanism,
        "status": status,
        "paper_role": paper_role,
        "evidence": evidence,
        "supported_claim": supported_claim,
        "forbidden_claim": forbidden_claim,
        "next_gate": next_gate,
        "receipts": receipts,
    }


def build_report() -> dict[str, Any]:
    rows = [
        row(
            mechanism="measurement_validity_foundation",
            status="include_as_foundation",
            paper_role="gating layer before any harnessing claim",
            evidence=(
                "Source-currency Stage-B Manifold panel: 80 contracts / 240 calls, "
                "post-minus-pre Brier +0.191098, paired-stratum delta +0.2155, "
                "permutation p=0.0004. Equal-information market controls now include "
                "103 external market rows and 52 equal-information rows."
            ),
            supported_claim=(
                "Harnessing is only interpretable after source-currency, label-time, "
                "and equal-information receipts are known."
            ),
            forbidden_claim="The source-currency result proves LLMs beat humans or markets.",
            next_gate="Keep all positive harnessing claims downstream of validity receipts.",
            receipts=[
                "papers/llm-forecast-calibration-cross-corpus/main.tex",
                "projects/llm_forecasting_calibration_program/law_validation_v1/workspace/paper_readiness_exhaustion_audit.md",
            ],
        ),
        row(
            mechanism="equal_information_market_controls",
            status="negative_boundary",
            paper_role="shows raw panels are not enough",
            evidence=(
                "Polymarket replacement: four-family panel Brier 0.267758 vs market "
                "0.072964, paired p=0.0068. Manifold second source: five-family "
                "low-stake panel 0.198723 vs market 0.160977, paired p=0.5431."
            ),
            supported_claim=(
                "Raw or lightly pooled LLM panels underperform or remain inconclusive "
                "against equal-information market bars; the paper should treat this as "
                "the reason a harness is needed."
            ),
            forbidden_claim="LLMs are superior to markets under equal information.",
            next_gate=(
                "A broad market/human claim requires predeclared or larger source-balanced "
                "equal-information evidence that beats the baseline."
            ),
            receipts=[
                "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15/equal_information_replacement_score.md",
                "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_score_2026_06_15/non_polymarket_equal_information_score.md",
            ],
        ),
        row(
            mechanism="f100_source_valid_calibration",
            status="include_bounded",
            paper_role="strongest current point-probability harness",
            evidence=(
                "Policy-scoreable rerun: raw mean-panel remains worse than confident-NO "
                "(+0.029598, p=0.0062). Source-currency stress narrows F100: improves "
                "post-cutoff rows by -0.025326 but regresses pre-cutoff/source-visible rows "
                "by +0.035016, p=0.0002."
            ),
            supported_claim=(
                "F100 is a source-valid, forward-looking calibration view; it extracts "
                "usable signal only on rows that pass source/label-time gates."
            ),
            forbidden_claim="F100 is a universal retrospective correction.",
            next_gate="Compare raw/F100/F47/market on prospective or newly joined source-valid rows.",
            receipts=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
        row(
            mechanism="f47_pairwise_ranking_translation",
            status="include_bounded",
            paper_role="ranking harness, not production probability",
            evidence=(
                "Source-balanced same-source/minimal-pair packet: 24 unique non-tie pairs, "
                "accuracy 0.750, utility +0.583, p=0.0044 vs random and p=0.0002 vs "
                "source control. Translation tests are favorable in one direction but fail "
                "production gates; joined market control remains too small."
            ),
            supported_claim=(
                "LLMs can be more useful as pairwise rankers/tournament comparators than as "
                "direct absolute-probability emitters."
            ),
            forbidden_claim="F47 translated probabilities beat markets or should replace F100/raw in production.",
            next_gate="Clear same-packet, cross-packet, market-control, and prospective causal-order checks.",
            receipts=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/f47_production_readiness_audit_2026_06_05/f47_production_readiness_audit.md",
            ],
        ),
        row(
            mechanism="structured_evidence_carriers",
            status="hypothesis_only",
            paper_role="possible interface improvement, not a law",
            evidence=(
                "N9/N10 smokes sometimes favor typed carrier fields over free prose, but "
                "the placebo-control continuation is negative for the stronger hard-break story."
            ),
            supported_claim=(
                "Structured carrier fields remain a plausible interface for extracting signal "
                "from model outputs, but current evidence is underpowered and mixed."
            ),
            forbidden_claim="Prompt hard-breaks or carrier-only stages are validated forecast improvers.",
            next_gate="Run a larger balanced packet that beats same-turn carrier and two-call prose controls.",
            receipts=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
        row(
            mechanism="family_routing_headroom",
            status="diagnostic_headroom_only",
            paper_role="shows signal exists but current routers do not recover it",
            evidence=(
                "Family-by-contract interaction is substantial; oracle-family review Brier is "
                "0.117454 overall. Current observable policies do not recover it: Hedge over "
                "experts is 0.226481 vs confident-NO 0.233529, p=0.4671, and source-balanced "
                "routers fail source controls."
            ),
            supported_claim=(
                "There is real conditional family-choice headroom, but current cheap routing "
                "features are not deployable."
            ),
            forbidden_claim="The current router is a production harness.",
            next_gate="Reopen only with new predeclared features or a real independent reviewer source.",
            receipts=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/paper_coherence_audit.md",
            ],
        ),
        row(
            mechanism="nurture_self_repair_controls",
            status="negative_control",
            paper_role="demotes easy harnessing stories",
            evidence=(
                "N2 selective action confirmation fails; N3-N7 self-repair variants overcorrect "
                "or become no-ops; F118 diagnostic-triggered allocation loses to confident-NO."
            ),
            supported_claim=(
                "Simple prompt nurture, generic self-repair, and diagnostic-triggered action "
                "do not reliably unlock forecast signal under current controls."
            ),
            forbidden_claim="More reflective prompting alone unlocks reliable forecasting improvement.",
            next_gate=(
                "Test only tool-using, interactive, retrieval-grounded, expert-written, or "
                "heldout-tuned prompt programs with fixed controls."
            ),
            receipts=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
    ]
    return {
        "schema": "gp245-harnessing-thesis-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "integrated_paper_supported": True,
            "split_required_now": False,
            "central_claim": (
                "Raw LLM forecasts do not beat equal-information market bars in the current "
                "evidence, but LLM forecast signal can be harnessed under validity, calibration, "
                "ranking, and routing constraints."
            ),
            "main_boundary": (
                "The paper may claim constrained extraction of usable signal; it may not claim "
                "LLM superiority over markets or validated prompt-nurture/self-repair."
            ),
            "split_trigger": (
                "Split later only if new prospective F47/F100/router evidence becomes large enough "
                "to support an independent mechanisms paper."
            ),
        },
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    lines = [
        "# GP-245 Harnessing Thesis Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Integrated paper supported: `{verdict['integrated_paper_supported']}`",
        f"- Split required now: `{verdict['split_required_now']}`",
        f"- Central claim: {verdict['central_claim']}",
        f"- Boundary: {verdict['main_boundary']}",
        f"- Split trigger: {verdict['split_trigger']}",
        "",
        "## Mechanism Map",
        "",
        "| mechanism | status | paper role | supported claim | forbidden claim |",
        "|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| {mechanism} | `{status}` | {role} | {supported} | {forbidden} |".format(
                mechanism=item["mechanism"],
                status=item["status"],
                role=item["paper_role"],
                supported=item["supported_claim"],
                forbidden=item["forbidden_claim"],
            )
        )
    lines.extend(["", "## Details", ""])
    for item in report["rows"]:
        lines.extend(
            [
                f"### {item['mechanism']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Evidence: {item['evidence']}",
                f"- Supported claim: {item['supported_claim']}",
                f"- Forbidden claim: {item['forbidden_claim']}",
                f"- Next gate: {item['next_gate']}",
                "- Receipts:",
                *[f"  - `{receipt}`" for receipt in item["receipts"]],
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "harnessing_thesis_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "harnessing_thesis_audit.md").write_text(
        render_md(report) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
