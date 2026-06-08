#!/usr/bin/env python3
"""Program-level science spine audit for LLM forecasting.

No model calls. No DB mutation.

The goal is broader than asking whether one packet improved Brier. This audit
asks whether each live claim is doing genuine forecasting science:

1. source-valid measurement,
2. explicit external or sham control,
3. cross-source/family stress,
4. an actuator that can change forecasts/actions,
5. a residual-to-lever next test that could kill or promote it.

It intentionally separates model-only progress from production progress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_READINESS = PROGRAM / "law_validation_v1/workspace/law_readiness_report.json"
DEFAULT_OUT_JSON = WORKSPACE / "forecasting_science_spine_audit_2026_06_04.json"
DEFAULT_OUT_MD = WORKSPACE / "forecasting_science_spine_audit_2026_06_04.md"


INPUTS = {
    "law_readiness": DEFAULT_READINESS,
    "f47_cross_packet": WORKSPACE / "f47_cross_packet_transfer_audit_2026_06_03.json",
    "f47_external_bar": WORKSPACE / "f47_external_bar_score_2026_06_03.json",
    "f47_external_manifest": WORKSPACE / "f47_external_bar_manifest_2026_06_03.json",
    "f100_source_currency": WORKSPACE / "f100_source_currency_audit_2026_06_03.json",
    "market_blend": PROGRAM / "truth_continuation_v1/workspace/market_llm_blend_stage_c_2026_06_03/market_llm_blend_stage_c_audit.json",
    "expert_advice": WORKSPACE / "expert_advice_router_audit_2026_06_03.json",
    "fred_vintage_bulk_repair": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_repair_2026_06_04/fred_vintage_bulk_repair.json",
    "fred_vintage_bulk_rescore": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def yesno(value: bool) -> str:
    return "yes" if value else "no"


def grade(criteria: dict[str, bool]) -> str:
    positive = sum(1 for v in criteria.values() if v)
    if criteria.get("deployable_actuator") and criteria.get("source_validity") and criteria.get("external_control"):
        return "applied_candidate"
    if positive >= 4:
        return "science_progress"
    if positive >= 2:
        return "diagnostic_or_scoped"
    return "weak_or_killed"


def row(
    *,
    claim: str,
    current_status: str,
    actuator: str,
    criteria: dict[str, bool],
    evidence: str,
    residual: str,
    next_lever: str,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "current_status": current_status,
        "actuator": actuator,
        "criteria": criteria,
        "science_grade": grade(criteria),
        "evidence": evidence,
        "residual": residual,
        "next_lever": next_lever,
    }


def build_report() -> dict[str, Any]:
    data = {name: read_json(path) for name, path in INPUTS.items()}
    raw_laws = (data["law_readiness"].get("laws") or {}) if data["law_readiness"] else {}
    if isinstance(raw_laws, list):
        laws = {str(item.get("law") or item.get("id") or item.get("name")): item for item in raw_laws if isinstance(item, dict)}
    elif isinstance(raw_laws, dict):
        laws = raw_laws
    else:
        laws = {}
    f47_cross = data["f47_cross_packet"]
    f47_bar = data["f47_external_bar"]
    f47_manifest = data["f47_external_manifest"]
    f100 = data["f100_source_currency"]
    market = data["market_blend"]
    expert = data["expert_advice"]
    fred_repair = data["fred_vintage_bulk_repair"]
    fred_rescore = data["fred_vintage_bulk_rescore"]
    fred_summary = fred_repair.get("summary") or {}
    fred_pair = fred_rescore.get("pair") or {}
    fred_control = fred_rescore.get("control") or {}

    f47_joined = int(f47_bar.get("n_joined") or 0)
    f47_market_delta = (
        (f47_bar.get("comparisons") or {})
        .get("translated_vs_market", {})
        .get("delta_candidate_minus_baseline")
    )
    f47_promoted_direction = (
        (f47_cross.get("transfers") or {})
        .get("source_balanced_to_translation_tournament", {})
        .get("promotable")
        is True
    )

    rows = [
        row(
            claim="Law 3 source-currency / cutoff validity",
            current_status=(laws.get("cutoff_validity") or {}).get("readiness", "unknown"),
            actuator="evaluation hygiene: separate prediction from retrieval/source visibility",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": True,
                "deployable_actuator": True,
                "kill_test_live": True,
            },
            evidence=(
                "Stage-B cutoff delta survived partial base-rate repair. FRED added a "
                "negative second-source stress: complete vintage repair found "
                f"{fred_summary.get('y_two_point_changed', 'unknown')}/"
                f"{fred_summary.get('rows', 'unknown')} label flips and erased the "
                "blinded-control current-label penalty."
            ),
            residual=(
                "Law 3 now has two distinct residuals: Manifold-heavy market/human "
                "baseline coverage, and label-time validity for dataset-source rows."
            ),
            next_lever=(
                "Acquire remaining Metaculus/export or reachable Polymarket bars for "
                "market/human comparison; use FRED only after ALFRED/bulk-export "
                "confirmation or another official source with frozen real-time labels."
            ),
        ),
        row(
            claim="Law 2 elicited error surface / worry-tail diagnostic",
            current_status=(laws.get("family_channel_error_surface") or {}).get("readiness", "unknown"),
            actuator="triage/review signal only, not automatic probability repair",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": True,
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence="Worry/error survives as diagnostic; channel-only and policy-translation audits demote broad correction.",
            residual="No frozen policy has converted diagnostic worry/channel signal into Brier or utility improvement over F100/raw controls.",
            next_lever="Only test review allocation when reviewer adds new information: market/web/human/heldout family with fixed cost and sham trigger.",
        ),
        row(
            claim="F100 confident-NO post-processing",
            current_status="live applied point-probability rule, source-valid only",
            actuator="external post-processing of low probabilities",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": True,
                "deployable_actuator": True,
                "kill_test_live": True,
            },
            evidence="Improves low-p post-cutoff/source-valid tails; source-currency audit shows it regresses pre-cutoff/source-visible rows.",
            residual=(
                f"Source-currency conflict: {f100.get('verdict', 'unknown')}. "
                "FRED bulk repair further excludes current-label dataset rows as "
                "policy-calibration evidence."
            ),
            next_lever=(
                "Keep raw and F100 views separate; apply only to live/source-valid "
                "rows with time-valid labels/baselines; test against market/human "
                "bars before replacing the hand rule."
            ),
        ),
        row(
            claim="F47 contrastive ranking and translated probability layer",
            current_status="ranking promoted; translation experimental; production closed",
            actuator="pairwise/tournament elicitation and graph-derived translation",
            criteria={
                "source_validity": True,
                "external_control": f47_joined >= 20 and (f47_market_delta or 0) <= 0,
                "cross_source_or_family": bool(f47_promoted_direction),
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence=(
                "One cross-packet direction beats F100; joined external-bar slice is "
                f"n={f47_joined} and market-minus-F47 control blocks deployment."
            ),
            residual=(
                "External-bar deficit: "
                f"{f47_manifest.get('acquisition_path_counts', {})}; translated-vs-market delta={f47_market_delta}."
            ),
            next_lever="Acquire 16 Polymarket historical-price rows or run prospective market/human-frozen packet; do not spend more unjoined F47 model calls.",
        ),
        row(
            claim="Prompt-nurture self-repair / action framing",
            current_status="demoted / mostly negative",
            actuator="same-model prose/action prompt intervention",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": False,
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence="N3-N10, router, allocation, hard-break and action-frame controls mostly fail or reduce to diagnostics.",
            residual="Model prose often changes without probability improvement; extra-call and carrier controls explain prior positive-looking effects.",
            next_lever="Stop broad self-repair scaling; only run prompt packets when they beat F100/raw plus sham/source controls.",
        ),
        row(
            claim="Expert advice / no-poolability family routing",
            current_status="headroom diagnostic, router not deployed",
            actuator="online expert weighting or family selection",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": True,
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence=(
                "Oracle family is far better, but Hedge/source-stratified expert advice "
                f"does not promote: {expert.get('verdict', 'unknown')}."
            ),
            residual="Observable features do not recover family-choice headroom without source regressions.",
            next_lever="Revisit only with more complete-five source-balanced panels or an external reviewer/market expert.",
        ),
        row(
            claim="Market/human additivity",
            current_status="not established",
            actuator="LLM+market blend or escalation policy",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": False,
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence=(
                "Stage-C Manifold blend is narrow and tiny gains are non-significant; "
                f"scope={market.get('scope', 'unknown')}."
            ),
            residual="External bar is sparse and Manifold-only; F47 joined slice also favors market-alone.",
            next_lever="Treat market/human baseline completion as a first-class acquisition problem, not a side analysis.",
        ),
        row(
            claim="Dataset-source official-data lane",
            current_status="apparatus/source-validity stress, not positive forecasting law",
            actuator="label-time repair before scoring or policy use",
            criteria={
                "source_validity": True,
                "external_control": False,
                "cross_source_or_family": True,
                "deployable_actuator": True,
                "kill_test_live": True,
            },
            evidence=(
                "FRED bulk repair reached "
                f"{fred_summary.get('vintage_scoreable_rows', 0)}/{fred_summary.get('rows', 0)} "
                "scoreable rows; pair-panel vintage mean Brier is "
                f"{fred_pair.get('vintage_mean_brier')} and blinded-control vintage "
                f"post-minus-pre is {(fred_control.get('paired_vintage') or {}).get('mean_post_minus_pre_brier')}."
            ),
            residual=(
                "Current-label official-data rows can be wrong even when the source "
                "API is official; no market/human equal-information baseline exists "
                "for FRED."
            ),
            next_lever=(
                "Promote a reusable label-time gate: any dataset-source benchmark row "
                "needs vintage/as-of labels before it can support source-currency or "
                "calibration-policy claims."
            ),
        ),
        row(
            claim="Law 1 anti-bias inheritance / MIMIC collapse",
            current_status=(laws.get("alignment_modulated_bias_inheritance") or {}).get("readiness", "unknown"),
            actuator="paper scoping / negative mechanism boundary",
            criteria={
                "source_validity": True,
                "external_control": True,
                "cross_source_or_family": False,
                "deployable_actuator": False,
                "kill_test_live": True,
            },
            evidence="Raw-gap and label-shuffle controls demote the broad causal carrier story.",
            residual="If a positive mechanism is desired, current rows lack support overlap for strict raw-gap confirmation.",
            next_lever="Write as negative/scoping unless a new raw-gap-matched packet is worth the cost.",
        ),
    ]

    belief_tests = [
        {
            "belief": "Forecasting progress comes from calibrated systems, not prompt introspection alone.",
            "currently_supported": True,
            "reason": "F100 and source-validity gates are stronger than self-repair/action prompts.",
        },
        {
            "belief": "Model-only Brier wins are insufficient until compared with market/human bars.",
            "currently_supported": True,
            "reason": "F47 beats F100 in one transfer direction but loses to market on the tiny joined slice.",
        },
        {
            "belief": "Diagnostic channels can be valuable without being deployable correction policies.",
            "currently_supported": True,
            "reason": "Worry/channel surfaces survive as error readouts while channel-only policy translation fails.",
        },
        {
            "belief": "Broad laws require source/family/horizon stress and explicit kill tests.",
            "currently_supported": True,
            "reason": "The strongest claims are scoped by source-currency, F100 source conflict, and market-bar deficits.",
        },
        {
            "belief": "Dataset-source rows need label-time validation before they count as forecasting evidence.",
            "currently_supported": True,
            "reason": "Complete FRED vintage repair changed 15/98 binary labels and erased the blinded-control current-label penalty.",
        },
    ]

    return {
        "schema": "forecasting-science-spine-audit-v1",
        "date": "2026-06-04",
        "inputs": {name: str(path.relative_to(REPO)) for name, path in INPUTS.items()},
        "belief_tests": belief_tests,
        "rows": rows,
        "program_verdict": "genuine_science_if_external_controls_drive_next_spend",
        "program_residual": (
            "The program is producing broad science when it kills prompt folklore and "
            "moves toward source-valid calibration, external baselines, and allocation. "
            "It regresses when it spends calls on unjoined model-only packets."
        ),
        "next_levers": [
            "Acquire external bars before further F47 production claims.",
            "Keep F100 live only on forward-looking/source-valid rows.",
            "Require label-time/vintage receipts before using dataset-source rows for law or policy evidence.",
            "Write Law 2 as diagnostic, not policy.",
            "Use prompt-nurture packets only as controlled construct probes unless they beat F100/raw/sham/source bars.",
            "Make market/human baseline completion a top acquisition lane.",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Forecasting Science Spine Audit",
        "",
        report["program_residual"],
        "",
        f"- Program verdict: `{report['program_verdict']}`",
        "",
        "## Beliefs Required",
        "",
        "| belief | supported now | reason |",
        "|---|---|---|",
    ]
    for item in report["belief_tests"]:
        lines.append(f"| {item['belief']} | {yesno(bool(item['currently_supported']))} | {item['reason']} |")
    lines.extend(
        [
            "",
            "## Claim Spine",
            "",
            "| claim | grade | status | actuator | residual | next lever |",
            "|---|---|---|---|---|---|",
        ]
    )
    for r in report["rows"]:
        lines.append(
            "| {claim} | `{grade}` | {status} | {actuator} | {residual} | {lever} |".format(
                claim=r["claim"],
                grade=r["science_grade"],
                status=r["current_status"],
                actuator=r["actuator"],
                residual=r["residual"],
                lever=r["next_lever"],
            )
        )
    lines.extend(["", "## Next Levers", ""])
    for lever in report["next_levers"]:
        lines.append(f"- {lever}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_report()
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "program_verdict": report["program_verdict"],
                "grades": {row["claim"]: row["science_grade"] for row in report["rows"]},
                "next_levers": report["next_levers"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
