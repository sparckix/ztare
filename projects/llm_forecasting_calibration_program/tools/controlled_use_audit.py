#!/usr/bin/env python3
"""Build the evidence map for the GP-245 controlled-use argument.

No model calls and no DB mutation. This audit answers whether the current
evidence supports keeping the existing paper as an integrated validity and
controlled-use paper, or whether the controlled-use material should be split
into a separate paper.
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
    next_check: str,
    evidence_records: list[str],
) -> dict[str, Any]:
    return {
        "mechanism": mechanism,
        "status": status,
        "paper_role": paper_role,
        "evidence": evidence,
        "supported_claim": supported_claim,
        "forbidden_claim": forbidden_claim,
        "next_check": next_check,
        "evidence_records": evidence_records,
    }


def build_report() -> dict[str, Any]:
    rows = [
        row(
            mechanism="measurement_validity_foundation",
            status="include_as_foundation",
            paper_role="validity layer before any controlled-use claim",
            evidence=(
                "Source-currency Stage-B Manifold panel: 80 contracts / 240 calls, "
                "post-minus-pre Brier +0.191098, paired-stratum delta +0.2155, "
                "permutation p=0.0004. Equal-information market controls now include "
                "103 external market rows and 52 equal-information rows."
            ),
            supported_claim=(
                "Controlled use is only interpretable after source-currency, label-time, "
                "and equal-information status are known."
            ),
            forbidden_claim="The source-currency result proves LLMs beat humans or markets.",
            next_check="Keep every positive use claim downstream of validity records.",
            evidence_records=[
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
                "against equal-information market bars; this is the reason raw panels "
                "are insufficient as the paper's comparison unit."
            ),
            forbidden_claim="LLMs are superior to markets under equal information.",
            next_check=(
                "A broad market/human claim requires predeclared or larger source-balanced "
                "equal-information evidence that beats the baseline."
            ),
            evidence_records=[
                "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15/equal_information_replacement_score.md",
                "projects/llm_forecasting_calibration_program/cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_score_2026_06_15/non_polymarket_equal_information_score.md",
            ],
        ),
        row(
            mechanism="source_valid_low_probability_calibration",
            status="include_bounded",
            paper_role="strongest current point-probability use",
            evidence=(
                "Policy-scoreable rerun: the raw mean panel remains worse than the "
                "low-probability adjustment (+0.029598, p=0.0062). Source-currency stress "
                "narrows the rule: it improves "
                "post-cutoff rows by -0.025326 but regresses pre-cutoff/source-visible rows "
                "by +0.035016, p=0.0002."
            ),
            supported_claim=(
                "The low-probability adjustment is a forward-looking calibration view for rows that pass the source-currency check; it improves "
                "scores only on rows that pass source/label-time gates."
            ),
            forbidden_claim="The low-probability adjustment is a universal retrospective correction.",
            next_check="Compare raw, calibrated, pairwise, and market baselines on prospective or newly joined rows that pass the source-currency check.",
            evidence_records=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
        row(
            mechanism="pairwise_ranking_translation",
            status="include_bounded",
            paper_role="ranking use, not standalone probability",
            evidence=(
                "Source-balanced same-source/minimal-pair packet: 24 unique non-tie pairs, "
                "accuracy 0.750, utility +0.583, p=0.0044 vs random and p=0.0002 vs "
                "source control. Translation tests are favorable in one direction but do not "
                "meet the adoption criteria; joined market control remains too small."
            ),
            supported_claim=(
                "LLMs can be more useful as pairwise rankers/tournament comparators than as "
                "direct absolute-probability emitters."
            ),
            forbidden_claim="Translated pairwise probabilities beat markets or replace raw/calibrated probabilities.",
            next_check="Clear same-packet, cross-packet, market-control, and prospective causal-order checks.",
            evidence_records=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/f47_production_readiness_audit_2026_06_05/f47_production_readiness_audit.md",
            ],
        ),
        row(
            mechanism="structured_evidence_fields",
            status="hypothesis_only",
            paper_role="possible interface improvement, not a general result",
            evidence=(
                "N9/N10 smokes sometimes favor typed fields over free prose, but "
                "the placebo-control continuation is negative for the stronger two-stage story."
            ),
            supported_claim=(
                "Structured evidence fields remain a plausible interface for using model output, "
                "but current evidence is underpowered and mixed."
            ),
            forbidden_claim="Prompt staging or structured fields alone are validated forecast improvers.",
            next_check="Run a larger balanced packet that beats same-turn structured-field and two-call prose controls.",
            evidence_records=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
        row(
            mechanism="family_choice_headroom",
            status="diagnostic_headroom_only",
            paper_role="shows conditional family differences, but current selection rules do not recover them",
            evidence=(
                "Family-by-contract interaction is substantial; best-family-in-hindsight review Brier is "
                "0.117454 overall. Current observable policies do not recover it: Hedge over "
                "experts is 0.226481 vs the low-probability adjustment 0.233529, p=0.4671, and source-balanced "
                "selection rules fail source controls."
            ),
            supported_claim=(
                "There is real conditional family-choice headroom, but current cheap selection "
                "features are not strong enough for use."
            ),
            forbidden_claim="The current family-selection rule is a validated forecasting system.",
            next_check="Reopen only with new predeclared features or a real independent reviewer source.",
            evidence_records=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/paper_alignment_v1/workspace/paper_coherence_audit.md",
            ],
        ),
        row(
            mechanism="prompt_intervention_self_repair_controls",
            status="negative_control",
            paper_role="rules out easy prompt-improvement stories",
            evidence=(
                "N2 selective action confirmation fails; N3-N7 self-repair variants overcorrect "
                "or become no-ops; F118 diagnostic-triggered allocation loses to the low-probability adjustment."
            ),
            supported_claim=(
                "Generic reflective prompting, self-repair, and diagnostic-triggered action "
                "do not reliably improve forecast probabilities under current controls."
            ),
            forbidden_claim="More reflective prompting alone unlocks reliable forecasting improvement.",
            next_check=(
                "Test only tool-using, interactive, retrieval-grounded, expert-written, or "
                "heldout-tuned prompt programs with fixed controls."
            ),
            evidence_records=[
                "projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md",
                "projects/llm_forecasting_calibration_program/public/METHODOLOGY.md",
            ],
        ),
    ]
    return {
        "schema": "gp245-controlled-use-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "integrated_paper_supported": True,
            "split_required_now": False,
            "central_claim": (
                "Current equal-information market controls do not support raw LLM panel "
                "superiority, but some model outputs retain limited value after validity, calibration, "
                "ranking, and family/source checks."
            ),
            "main_boundary": (
                "The paper may claim controlled use of selected model outputs; it may not claim "
                "LLM superiority over markets or validated reflective-prompting/self-repair."
            ),
            "split_trigger": (
                "Split later only if new prospective calibration, ranking, or family-choice evidence becomes large enough "
                "to support an independent follow-up paper."
            ),
        },
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    evidence_family_labels = {
        "measurement_validity_foundation": "Measurement validity",
        "equal_information_market_controls": "Equal-information market controls",
        "source_valid_low_probability_calibration": "Low-probability calibration",
        "pairwise_ranking_translation": "Pairwise ranking",
        "structured_evidence_fields": "Structured fields",
        "family_choice_headroom": "Model-family differences",
        "prompt_intervention_self_repair_controls": "Prompt intervention controls",
    }
    status_labels = {
        "include_as_foundation": "Foundation",
        "negative_boundary": "Boundary result",
        "include_bounded": "Bounded result",
        "hypothesis_only": "Hypothesis only",
        "diagnostic_headroom_only": "Diagnostic only",
        "negative_control": "Negative control",
    }

    def family_label(key: str) -> str:
        return evidence_family_labels.get(key, key.replace("_", " ").title())

    def status_label(key: str) -> str:
        return status_labels.get(key, key.replace("_", " "))

    verdict = report["verdict"]
    lines = [
                "# Controlled-Use Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Integrated paper supported: `{verdict['integrated_paper_supported']}`",
        f"- Split required now: `{verdict['split_required_now']}`",
        f"- Central claim: {verdict['central_claim']}",
        f"- Boundary: {verdict['main_boundary']}",
        f"- Split trigger: {verdict['split_trigger']}",
        "",
        "## Evidence Map",
        "",
        "| Evidence family | Status | Paper role | Supported claim | Unsupported claim |",
        "|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| {family} | {status} | {role} | {supported} | {unsupported} |".format(
                family=family_label(item["mechanism"]),
                status=status_label(item["status"]),
                role=item["paper_role"],
                supported=item["supported_claim"],
                unsupported=item["forbidden_claim"],
            )
        )
    lines.extend(["", "## Details", ""])
    for item in report["rows"]:
        lines.extend(
            [
                f"### {family_label(item['mechanism'])}",
                "",
                f"- Status: {status_label(item['status'])}",
                f"- Evidence: {item['evidence']}",
                f"- Supported claim: {item['supported_claim']}",
                f"- Unsupported claim: {item['forbidden_claim']}",
                f"- Next check: {item['next_check']}",
                "- Source records are retained in the JSON sidecar.",
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
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown = render_md(report) + "\n"
    (args.out_dir / "controlled_use_audit.json").write_text(
        payload,
        encoding="utf-8",
    )
    (args.out_dir / "controlled_use_audit.md").write_text(
        markdown,
        encoding="utf-8",
    )
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
