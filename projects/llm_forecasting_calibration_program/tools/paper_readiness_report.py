#!/usr/bin/env python3
"""Check whether the GP-245 paper text matches current law readiness.

No model calls and no DB writes. This is stricter than
paper_claim_alignment_report.py: it checks that the draft surfaces the current
top-law maturity, companion-law scope, and known non-promotions.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
PAPER_ROOT = REPO / "papers/llm-forecast-calibration-cross-corpus"
DEFAULT_READINESS = PROGRAM_ROOT / "law_validation_v1/workspace/law_readiness_report.json"
DEFAULT_PUBLIC_SUMMARY = PROGRAM_ROOT / "public/CLAIM_SUMMARY.md"
DEFAULT_OUT = PROGRAM_ROOT / "paper_alignment_v1/workspace"
DEFAULT_PAPERS = (
    PAPER_ROOT / "main.tex",
)


@dataclass(frozen=True)
class MarkerRule:
    rule_id: str
    label: str
    required_terms: tuple[str, ...]
    scope_terms: tuple[str, ...]
    severity: str
    recommendation: str


@dataclass(frozen=True)
class SurfaceRule:
    rule_id: str
    label: str
    required_groups: tuple[tuple[str, ...], ...]
    stale_terms: tuple[str, ...]
    severity: str
    recommendation: str
    trigger_terms: tuple[str, ...] = ()


RULES = (
    MarkerRule(
        rule_id="law1_negative_scope",
        label="Law 1 anti-bias-collapse status",
        required_terms=("anti-bias", "anti_bias", "mimic", "collapse"),
        scope_terms=("negative", "scop", "raw-gap", "label-shuffle", "not promote", "not a confirmed"),
        severity="needs_review",
        recommendation=(
            "If the paper mentions MIMIC/anti-bias collapse, it should say the "
            "180-call smoke scoped down the clean mechanism because raw-gap "
            "controls explain/reverse the class effect."
        ),
    ),
    MarkerRule(
        rule_id="law2_diagnostic_not_policy",
        label="Law 2 diagnostic-only status",
        required_terms=("worry", "premium", "channel", "auxiliary"),
        scope_terms=("diagnostic", "error-readout", "policy", "demot", "not a", "future work"),
        severity="needs_review",
        recommendation=(
            "Law 2 should be written as diagnostic error-readout unless a "
            "prospective Brier-policy cell is validated."
        ),
    ),
    MarkerRule(
        rule_id="law3_cutoff_stage_b_scored_scope",
        label="Law 3 cutoff-validity status",
        required_terms=("cutoff", "halawi", "pre-cutoff", "post-cutoff"),
        scope_terms=("matched", "stage", "panel", "240", "base-rate", "limitation", "candidate"),
        severity="needs_review",
        recommendation=(
            "Cutoff-validity should be written from the completed constrained "
            "Stage-B panel plus Stage-C partial base-rate repair, while keeping "
            "the unjoined-row and second-source limitations explicit."
        ),
    ),
    MarkerRule(
        rule_id="router_source_fragility_scope",
        label="No-poolability/router companion status",
        required_terms=("router", "routing", "mean", "median", "no-pool", "poolability"),
        scope_terms=("source", "leave-one-out", "fragile", "failed", "not deploy", "research target"),
        severity="info",
        recommendation=(
            "Router/no-poolability should remain a companion claim until source "
            "leave-one-out survives."
        ),
    ),
    MarkerRule(
        rule_id="reasoning_probability_decoupling_scope",
        label="Reasoning-probability decoupling companion",
        required_terms=("rationale", "reasoning", "cot", "probability", "calibration"),
        scope_terms=("decoupl", "near-zero", "revision", "intervention", "numeric"),
        severity="info",
        recommendation=(
            "If rationale content is discussed, distinguish rationale quality "
            "from probability calibration and name the intervention needed."
        ),
    ),
)


SURFACE_RULES = (
    SurfaceRule(
        rule_id="law1_anti_bias_collapse_scoping_surface",
        label="Law 1 anti-bias-collapse scoping surface",
        required_groups=(
            ("kill_or_scope_raw_gap_explains_collapse", "180-call", "anti-bias-collapse"),
            ("0.5387", "class-label shuffle", "label-shuffle"),
            ("-0.076587", "raw-gap-adjusted", "raw-gap adjustment"),
            ("0.0025", "raw-gap-adjusted"),
            ("anti_bias_raw_gap_match_audit", "matched audit", "matched raw-gap"),
            ("-0.072750", "-0.077561"),
            ("16 with-replacement", "16 with replacement"),
            ("15 no-replacement", "15 no replacement"),
        ),
        stale_terms=(),
        severity="needs_review",
        recommendation=(
            "The paper should preserve the Law 1 demotion: the 180-call "
            "anti-bias-collapse smoke keeps MIMIC as a taxonomy, but the clean "
            "prompt-actuation mechanism fails the label-shuffle check and "
            "reverses after raw-gap adjustment. It should also preserve the "
            "matched-audit caveat: existing rows have poor support overlap and "
            "strict within-family matching flips the effect negative."
        ),
    ),
    SurfaceRule(
        rule_id="stage_c_market_baseline_surface",
        label="Stage-C market baseline surface",
        required_groups=(
            ("0.099673", "pre-outcome market", "market bar", "narrow market"),
            ("0.097218", "leave-one-out", "market+LLM", "blend"),
            ("0.794", "-0.002455", "fails promotion", "paired delta"),
            ("post-cutoff subset selects market-only", "post-cutoff prefers market-only", "post-cutoff-negative"),
            ("17 yes / 34 no", "32 of 51", "effective-n", "effective-$n"),
            ("follow-up void audit", "broad_equal_information_baseline_absent", "51 contracts have an ingested market/human baseline"),
            ("80 contracts / 240 calls", "80 contracts"),
            ("29 Stage-B contracts", "29"),
        ),
        stale_terms=(),
        severity="missing_surface",
        recommendation=(
            "The paper should mention the DB-ingested Stage-C Manifold market "
            "baseline and the scoped market+LLM blend audit, or explicitly say "
            "why either is omitted. It is the current external bar for Law 3, "
            "but the paired test fails promotion, the post-cutoff subset "
            "selects market-only, and it is not a broad human/crowd baseline. "
            "The baseline-void audit should also be preserved: the only joined "
            "bar is 51 Manifold contracts against an 80-contract Stage-B panel."
        ),
    ),
    SurfaceRule(
        rule_id="stage_c_base_rate_repair_surface",
        label="Stage-C base-rate repair and missing-band sensitivity",
        required_groups=(
            ("0.255418", "+0.255418", "base-rate-band", "base-rate band"),
            ("0.127901", "+0.127901", "missing-band", "missing band"),
        ),
        stale_terms=("reliable base-rate fields are absent",),
        severity="needs_review",
        recommendation=(
            "Replace the old 'base-rate fields are absent' limitation with the "
            "current Stage-C partial base-rate repair: 51/80 joined, 27 paired "
            "base-rate-band cells positive, missing-band sensitivity still positive."
        ),
    ),
    SurfaceRule(
        rule_id="n10_latent_carrier_surface",
        label="N10 hard-prompt-break latent-carrier continuation",
        required_groups=(
            ("0.103278", "two-step carrier", "hard prompt break", "hard-prompt-break"),
            ("0.098425", "same-turn carrier", "typed carrier"),
            ("0.149921", "placebo-control", "two-call prose"),
            ("0.107254", "two-call prose", "placebo"),
            ("unproven", "not a validated law", "not confirmed", "not support"),
        ),
        stale_terms=(),
        severity="needs_review",
        recommendation=(
            "If the paper invokes the behavioral latent-carrier/token-bottleneck "
            "bridge, it should include the N9/N10 continuation and keep it scoped "
            "as directional smoke evidence, not a validated law."
        ),
        trigger_terms=("latent-carrier", "korchinski", "structured carrier"),
    ),
    SurfaceRule(
        rule_id="expert_advice_router_surface",
        label="Expert-advice router demotion surface",
        required_groups=(
            ("0.226481", "expert-advice", "hedge"),
            ("0.233529", "confident-NO mean-panel", "confident-no mean-panel"),
            ("0.4671", "-0.0070", "fails promotion"),
            ("0.117454", "oracle-expert", "oracle expert"),
            ("regresses on Manifold", "source-balanced", "balanced Manifold/Polymarket"),
        ),
        stale_terms=(),
        severity="needs_review",
        recommendation=(
            "If the paper discusses no-poolability or routing, it should include "
            "the expert-advice continuation: oracle family-choice headroom is "
            "large, but Hedge-style observable expert weighting fails promotion "
            "against confident-NO mean-panel and source controls."
        ),
        trigger_terms=("no-poolability", "routing", "router", "family-choice"),
    ),
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def find_lines(path: Path, terms: tuple[str, ...], max_hits: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    hits: list[dict[str, Any]] = []
    lower_terms = tuple(term.lower() for term in terms)
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        low = line.lower()
        if any(term in low for term in lower_terms):
            hits.append(
                {
                    "file": str(path.relative_to(REPO)),
                    "line": idx,
                    "text": line.strip(),
                }
            )
        if len(hits) >= max_hits:
            break
    return hits


def law_by_name(readiness: dict[str, Any], law_name: str) -> dict[str, Any]:
    for law in readiness.get("laws", []):
        if law.get("law") == law_name:
            return law
    return {}


def readiness_summary(readiness: dict[str, Any]) -> dict[str, Any]:
    laws = {
        law.get("law"): {
            "readiness": law.get("readiness"),
            "status": law.get("status"),
            "bottleneck": law.get("bottleneck"),
            "next_step": law.get("next_step"),
        }
        for law in readiness.get("laws", [])
    }
    return {
        "ready_for_landmark_claim": (readiness.get("paper_status") or {}).get("ready_for_landmark_claim"),
        "hard_blockers": (readiness.get("paper_status") or {}).get("hard_blockers") or [],
        "laws": laws,
    }


def scan_rule(rule: MarkerRule, paper_paths: tuple[Path, ...]) -> dict[str, Any]:
    combined = normalize("\n".join(read_text(path) for path in paper_paths))
    mentions_subject = has_any(combined, rule.required_terms)
    has_scope = has_any(combined, rule.scope_terms)
    finding = None
    if mentions_subject and not has_scope:
        finding = {
            "rule_id": rule.rule_id,
            "label": rule.label,
            "severity": rule.severity,
            "problem": "subject_mentioned_without_current_scope_marker",
            "recommendation": rule.recommendation,
            "evidence_hits": [
                hit
                for path in paper_paths
                for hit in find_lines(path, rule.required_terms, max_hits=3)
            ][:6],
        }
    if not mentions_subject and rule.severity == "needs_review":
        finding = {
            "rule_id": rule.rule_id,
            "label": rule.label,
            "severity": "missing_surface",
            "problem": "current_law_surface_not_found_in_paper",
            "recommendation": rule.recommendation,
            "evidence_hits": [],
        }
    return {
        "rule_id": rule.rule_id,
        "label": rule.label,
        "mentions_subject": mentions_subject,
        "has_scope_marker": has_scope,
        "finding": finding,
    }


def scan_surface_rule(rule: SurfaceRule, paper_paths: tuple[Path, ...]) -> dict[str, Any]:
    combined = normalize("\n".join(read_text(path) for path in paper_paths))
    triggered = True if not rule.trigger_terms else has_any(combined, rule.trigger_terms)
    group_hits = [has_any(combined, group) for group in rule.required_groups]
    stale_hits = [term for term in rule.stale_terms if term.lower() in combined]
    finding = None
    if triggered and (not all(group_hits) or stale_hits):
        missing_groups = [
            group for group, hit in zip(rule.required_groups, group_hits) if not hit
        ]
        finding = {
            "rule_id": rule.rule_id,
            "label": rule.label,
            "severity": rule.severity,
            "problem": (
                "stale_surface_terms_present"
                if stale_hits
                else "current_empirical_surface_not_found_in_paper"
            ),
            "recommendation": rule.recommendation,
            "missing_required_groups": missing_groups,
            "stale_terms": stale_hits,
            "evidence_hits": [
                hit
                for path in paper_paths
                for hit in find_lines(
                    path,
                    rule.trigger_terms or tuple(term for group in rule.required_groups for term in group),
                    max_hits=3,
                )
            ][:6],
        }
    return {
        "rule_id": rule.rule_id,
        "label": rule.label,
        "triggered": triggered,
        "required_group_hits": group_hits,
        "stale_terms_present": stale_hits,
        "finding": finding,
    }


def hidden_scan_summary(path: Path) -> dict[str, Any]:
    text = read_text(path)
    low = normalize(text)
    candidates = {
        "no_poolability_metric_non_equivalence": "no-poolability" in low or "metric non-equivalence" in low,
        "reasoning_probability_decoupling": "reasoning-to-probability" in low or "decoupling" in low,
        "f105_effort_sibling": "f105" in low and "sibling" in low,
        "confident_no_fragment": "confident-no" in low or "confident no" in low,
        "horizon_source_fragment": "horizon/source" in low or "horizon" in low,
        "sealed_independence_exposure_herding_fragment": "sealed-independence" in low or "exposure-herding" in low,
        "contrastive_comparative_elicitation_fragment": "contrastive comparative" in low or "contrastive elicitation" in low,
        "selective_action_arbitration_fragment": "selective-action" in low or "arbitration" in low,
    }
    return {
        "path": str(path.relative_to(REPO)) if path.exists() else str(path),
        "exists": path.exists(),
        "candidates_named": candidates,
        "verdict_marker_present": "no hidden law currently outranks" in low,
    }


def build_report(
    readiness_path: Path,
    hidden_scan_path: Path,
    paper_paths: tuple[Path, ...],
) -> dict[str, Any]:
    readiness = read_json(readiness_path)
    rule_results = [scan_rule(rule, paper_paths) for rule in RULES]
    surface_results = [scan_surface_rule(rule, paper_paths) for rule in SURFACE_RULES]
    findings = [row["finding"] for row in rule_results if row["finding"]]
    findings.extend(row["finding"] for row in surface_results if row["finding"])
    by_severity: dict[str, int] = {}
    for row in findings:
        by_severity[row["severity"]] = by_severity.get(row["severity"], 0) + 1
    law1 = law_by_name(readiness, "alignment_modulated_bias_inheritance")
    law2 = law_by_name(readiness, "family_channel_error_surface")
    law3 = law_by_name(readiness, "cutoff_validity")
    top_law_blockers = [
        {
            "law": law.get("law"),
            "readiness": law.get("readiness"),
            "status": law.get("status"),
            "bottleneck": law.get("bottleneck"),
            "next_step": law.get("next_step"),
        }
        for law in (law1, law2, law3)
        if law and law.get("readiness") == "not_paper_ready"
    ]
    hidden_summary = hidden_scan_summary(hidden_scan_path)
    missing_hidden_scan = [
        key for key, present in hidden_summary["candidates_named"].items() if not present
    ]
    if missing_hidden_scan:
        findings.append(
            {
                "rule_id": "hidden_law_scan_incomplete",
                "label": "Hidden-law scan candidate coverage",
                "severity": "info",
                "problem": "hidden_scan_missing_candidate_markers",
                "recommendation": "Check whether the hidden-law frontier scan intentionally excludes these candidates.",
                "missing_candidates": missing_hidden_scan,
                "evidence_hits": [],
            }
        )
        by_severity["info"] = by_severity.get("info", 0) + 1
    return {
        "schema": "gp245-paper-readiness-v1",
        "readiness_report": str(readiness_path.relative_to(REPO)) if readiness_path.exists() else str(readiness_path),
        "paper_files": [str(path.relative_to(REPO)) for path in paper_paths],
        "readiness_summary": readiness_summary(readiness),
        "top_law_blockers": top_law_blockers,
        "hidden_law_scan": hidden_summary,
        "rule_results": rule_results,
        "surface_results": surface_results,
        "finding_count": len(findings),
        "by_severity": by_severity,
        "findings": findings,
        "ready_to_represent_as_landmark_paper": (
            not top_law_blockers
            and by_severity.get("needs_review", 0) == 0
            and by_severity.get("missing_surface", 0) == 0
        ),
        "interpretation": (
            "A clean report means the draft is scoped to current evidence. It "
            "does not mean the laws themselves are validated."
        ),
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "paper_readiness_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# GP-245 Paper Readiness Report", ""]
    lines.append(f"- Ready to represent as landmark paper: `{result['ready_to_represent_as_landmark_paper']}`")
    lines.append(f"- Finding count: `{result['finding_count']}`")
    lines.append(f"- By severity: `{result['by_severity']}`")
    lines.append("")
    lines.append("## Top-Law Blockers")
    lines.append("")
    if not result["top_law_blockers"]:
        lines.append("- None.")
    for row in result["top_law_blockers"]:
        lines.append(
            f"- `{row['law']}`: readiness=`{row['readiness']}`, "
            f"status=`{row['status']}`, bottleneck=`{row['bottleneck']}`"
        )
        lines.append(f"  Next step: {row['next_step']}")
    lines.append("")
    lines.append("## Hidden-Law Scan")
    lines.append("")
    hidden = result["hidden_law_scan"]
    lines.append(f"- Source: `{hidden['path']}`")
    lines.append(f"- Verdict marker present: `{hidden['verdict_marker_present']}`")
    for key, value in hidden["candidates_named"].items():
        lines.append(f"- `{key}` named: `{value}`")
    lines.append("")
    lines.append("## Rule Results")
    lines.append("")
    for row in result["rule_results"]:
        lines.append(
            f"- `{row['rule_id']}`: mentions_subject=`{row['mentions_subject']}`, "
            f"has_scope_marker=`{row['has_scope_marker']}`"
        )
    lines.append("")
    lines.append("## Current Empirical Surfaces")
    lines.append("")
    for row in result["surface_results"]:
        lines.append(
            f"- `{row['rule_id']}`: triggered=`{row['triggered']}`, "
            f"required_group_hits=`{row['required_group_hits']}`, "
            f"stale_terms_present=`{row['stale_terms_present']}`"
        )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not result["findings"]:
        lines.append("- None.")
    for row in result["findings"]:
        lines.append(f"- `{row['severity']}` `{row['rule_id']}`: {row['problem']}")
        lines.append(f"  Recommendation: {row['recommendation']}")
        for hit in row.get("evidence_hits", [])[:3]:
            lines.append(f"  Evidence: `{hit['file']}:{hit['line']}` {hit['text']}")
    lines.append("")
    (out_dir / "paper_readiness_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--hidden-scan", type=Path, default=DEFAULT_PUBLIC_SUMMARY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--paper", type=Path, action="append")
    args = parser.parse_args()
    papers = tuple(args.paper) if args.paper else DEFAULT_PAPERS
    result = build_report(args.readiness, args.hidden_scan, papers)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
