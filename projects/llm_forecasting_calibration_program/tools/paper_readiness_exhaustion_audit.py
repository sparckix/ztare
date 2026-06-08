#!/usr/bin/env python3
"""Audit whether the GP-245 forecasting laws are exhausted enough for paper use.

No model calls. No DB mutation.

This report is deliberately claim-boundary oriented: it separates what can be
written now from loved overclaims that current evidence kills or leaves blocked
by acquisition. It consumes existing no-call audits plus DB materialized views.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "law_validation_v1/workspace"

INPUTS = {
    "law_readiness": DEFAULT_OUT / "law_readiness_report.json",
    "science_spine": PROGRAM / "forecaster_skill_calibration_v1/workspace/forecasting_science_spine_audit_2026_06_04.json",
    "max_truth_frontier": PROGRAM / "truth_seeking_v1/workspace/max_truth_frontier_report.json",
    "equal_information": PROGRAM
    / "truth_continuation_v1/workspace/equal_information_baseline_void_2026_06_03/equal_information_baseline_void_report.json",
    "market_blend": PROGRAM
    / "truth_continuation_v1/workspace/market_llm_blend_stage_c_2026_06_03/market_llm_blend_stage_c_report.json",
    "f100_source_currency": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json",
    "f47_prospective": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_prospective_market_freeze_packet_2026_06_04/f47_prospective_market_freeze_score.json",
    "f47_production_readiness": PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_production_readiness_audit_2026_06_05/f47_production_readiness_audit.json",
    "fred_vintage_rescore": PROGRAM
    / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json",
}


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
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


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    try:
        row = cur.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def db_evidence(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    out = {
        "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
        "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
        "policy_scoreable_calls": scalar(cur, "SELECT COUNT(*) FROM v_policy_scoreable_calls"),
        "source_currency_gate_rows": scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows"),
        "source_currency_conflicts": scalar(cur, "SELECT COUNT(*) FROM v_source_currency_gate_conflicts"),
        "policy_scoreable_source_currency_conflicts": scalar(
            cur,
            "SELECT SUM(cutoff_relation_conflict) FROM v_policy_scoreable_calls_source_currency",
        ),
        "external_market_baselines": scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines"),
        "equal_information_market_baselines": scalar(
            cur,
            "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1",
        ),
    }
    con.close()
    return out


def law_by_name(readiness: dict[str, Any], name: str) -> dict[str, Any]:
    for row in readiness.get("laws", []):
        if isinstance(row, dict) and row.get("law") == name:
            return row
    return {}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def verdict_state(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("state") or value.get("verdict")
    return value


def claim_row(
    *,
    claim: str,
    paper_status: str,
    current_evidence: dict[str, Any],
    narrow_writeable_claim: str,
    forbidden_overclaim: str,
    nearest_confuser: str,
    kill_or_completion_condition: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "paper_status": paper_status,
        "current_evidence": current_evidence,
        "narrow_writeable_claim": narrow_writeable_claim,
        "forbidden_overclaim": forbidden_overclaim,
        "nearest_confuser": nearest_confuser,
        "kill_or_completion_condition": kill_or_completion_condition,
        "next_action": next_action,
    }


def build_report(db: Path) -> dict[str, Any]:
    reports = {name: read_json(path) for name, path in INPUTS.items()}
    readiness = reports["law_readiness"]
    science_rows = {
        str(row.get("claim")): row
        for row in (reports["science_spine"].get("rows") or [])
        if isinstance(row, dict)
    }
    dbs = db_evidence(db)
    law1 = law_by_name(readiness, "alignment_modulated_bias_inheritance")
    law2 = law_by_name(readiness, "family_channel_error_surface")
    law3 = law_by_name(readiness, "cutoff_validity")
    f100 = reports["f100_source_currency"]
    equal_info = reports["equal_information"].get("verdict") or {}
    market_blend = reports["market_blend"].get("verdict") or {}
    fred_control = (reports["fred_vintage_rescore"].get("control") or {})
    f47 = reports["f47_prospective"].get("verdict")
    f47_resolution = as_dict(reports["f47_prospective"].get("resolution"))
    f47_exclusions = as_dict(reports["f47_prospective"].get("exclusion_reasons"))
    f47_production = reports["f47_production_readiness"]

    claims = [
        claim_row(
            claim="Law 1: alignment-modulated bias inheritance",
            paper_status="write_as_scoped_negative_or_mechanism_caveat",
            current_evidence={
                "readiness": law1.get("readiness"),
                "score_verdict": (law1.get("current_evidence") or {}).get("score_verdict"),
                "raw_gap_adjusted_mimic_coef": (law1.get("current_evidence") or {}).get(
                    "raw_gap_adjusted_mimic_coef"
                ),
            },
            narrow_writeable_claim=(
                "MIMIC-style inheritance is not currently a promoted causal law; "
                "raw-gap controls explain or scope the observed collapse."
            ),
            forbidden_overclaim="Human-bias labels are a causal carrier law for LLM forecast errors.",
            nearest_confuser="taxonomy/mechanism story mistaken for causal evidence",
            kill_or_completion_condition="Reopen only with raw-gap matched or randomized rows.",
            next_action="Draft as negative/scoping section; no more same-shape anti-bias calls.",
        ),
        claim_row(
            claim="Law 2: elicited error surface",
            paper_status="write_as_diagnostic_ready_policy_demoted",
            current_evidence={
                "readiness": law2.get("readiness"),
                "science_grade": (science_rows.get("Law 2 elicited error surface / worry-tail diagnostic") or {}).get(
                    "science_grade"
                ),
            },
            narrow_writeable_claim=(
                "Auxiliary channels can diagnose fragility, but current frozen policies "
                "do not justify direct Brier/action deployment."
            ),
            forbidden_overclaim="Worry/spread/self-Brier are production probability transforms.",
            nearest_confuser="diagnostic correlation mistaken for actuator",
            kill_or_completion_condition=(
                "Promote only if a frozen allocation/review policy beats raw/F100/sham/source controls."
            ),
            next_action="Write diagnostic law; future allocation packets need an external reviewer/source.",
        ),
        claim_row(
            claim="Law 3: source-currency / cutoff validity",
            paper_status="write_as_candidate_with_explicit_external_baseline_limit",
            current_evidence={
                "readiness": law3.get("readiness"),
                "stage_b_post_minus_pre": (law3.get("current_evidence") or {}).get("stage_b_score_post_minus_pre"),
                "source_currency_gate_rows": dbs["source_currency_gate_rows"],
                "source_currency_conflicts": dbs["source_currency_conflicts"],
                "fred_blinded_control_vintage_delta": (fred_control.get("paired_vintage") or {}).get(
                    "mean_post_minus_pre_brier"
                ),
            },
            narrow_writeable_claim=(
                "Cutoff/source-currency validity matters and survives the main Stage-B "
                "panel, but dataset-source positives require label-time receipts and "
                "market/human comparisons remain source-limited."
            ),
            forbidden_overclaim="A broad LLM forecasting superiority law is proven across equal-information sources.",
            nearest_confuser="source/cutoff leakage mistaken for current forecasting skill",
            kill_or_completion_condition=(
                "Scope if same-information market-only dominates or label-time repair erases the signal."
            ),
            next_action="Acquire remaining Metaculus/export or post-cutoff Polymarket bars; avoid more calls first.",
        ),
        claim_row(
            claim="F100 confident-NO calibration",
            paper_status="write_as_applied_scoped_rule",
            current_evidence={
                "verdict": f100.get("verdict"),
                "overall_delta": f100.get("overall", {}).get("delta_f100_minus_raw"),
                "pre_cutoff_delta": (f100.get("by_cutoff_relation") or {}).get("pre_cutoff", {}).get(
                    "delta_f100_minus_raw"
                ),
                "post_cutoff_delta": (f100.get("by_cutoff_relation") or {}).get("post_cutoff", {}).get(
                    "delta_f100_minus_raw"
                ),
                "source_currency_conflicts": dbs["source_currency_conflicts"],
            },
            narrow_writeable_claim=(
                "F100 is the current forward-looking/source-valid point-probability rule; "
                "it is not a retrospective benchmark correction."
            ),
            forbidden_overclaim="F100 universally improves all cutoff/source strata.",
            nearest_confuser="post-cutoff live calibration mistaken for pre-cutoff retrospective correction",
            kill_or_completion_condition="Kill or narrow further if source-valid live rows regress against raw/market bars.",
            next_action="Compare raw/F100/F47/market on prospective or newly joined source-valid rows.",
        ),
        claim_row(
            claim="F47 contrastive ranking / translated probability",
            paper_status="not_production_ready_wait_for_prospective_resolution",
            current_evidence={
                "production_verdict": f47_production.get("verdict"),
                "production_ready": f47_production.get("production_ready"),
                "failed_production_gates": f47_production.get("failed_gates"),
                "prospective_state": verdict_state(f47),
                "resolution_side_status_counts": f47_resolution.get("side_status_counts"),
                "excluded_unresolved_pairs": f47_exclusions.get("unresolved_pair"),
            },
            narrow_writeable_claim=(
                "F47 is a promising pairwise/ranking phenomenon with prior source-heldout support, "
                "but current production-readiness gates keep it out of absolute-probability deployment."
            ),
            forbidden_overclaim="F47 is a deployed probability layer that beats markets.",
            nearest_confuser="ranking utility mistaken for calibrated absolute probability",
            kill_or_completion_condition=(
                "Promote only if same-packet, cross-packet, market-control, and prospective causal-order gates all pass."
            ),
            next_action="Do not spend more F47 probability calls until frozen prospective markets resolve or equal-information bars are filled.",
        ),
        claim_row(
            claim="Market/human equal-information comparison",
            paper_status="blocked_for_broad_claim_write_as_absence",
            current_evidence={
                "state": equal_info.get("state"),
                "external_market_baselines": dbs["external_market_baselines"],
                "equal_information_market_baselines": dbs["equal_information_market_baselines"],
                "market_blend_state": market_blend.get("state"),
                "market_blend_overall_delta": market_blend.get("overall_loo_minus_market"),
            },
            narrow_writeable_claim=(
                "The current market slice is a useful stress control, but broad same-information "
                "human/market baselines are absent."
            ),
            forbidden_overclaim="LLMs beat humans/markets on same-information forecasting.",
            nearest_confuser="contract count confused with market platform history or LLM call count",
            kill_or_completion_condition=(
                "Broad claim requires matched contract-level bars across at least two independent sources."
            ),
            next_action="Acquire/export equal-information bars before market-comparison model calls.",
        ),
    ]

    not_ready = [
        row["claim"]
        for row in claims
        if row["paper_status"] in {
            "not_production_ready_wait_for_prospective_resolution",
            "blocked_for_broad_claim_write_as_absence",
        }
    ]
    return {
        "schema": "gp245-paper-readiness-exhaustion-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": repo_relative(db),
        "inputs": {name: repo_relative(path) for name, path in INPUTS.items()},
        "db_evidence": dbs,
        "program_verdict": {
            "scoped_paper_ready": True,
            "broad_landmark_claim_ready": False,
            "not_ready_claims": not_ready,
            "next_highest_yield_action": (
                "Write the paper as scoped/diagnostic/applied-candidate claims and acquire "
                "equal-information baseline rows before any broad market/human or production-F47 claim."
            ),
        },
        "claim_boundary_rows": claims,
        "stop_rule": (
            "Do not spend new LLM calls for a claim whose live blocker is source validity, "
            "label-time validity, market/human baseline acquisition, or unresolved prospective outcomes."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    verdict = report["program_verdict"]
    lines = [
        "# GP-245 Paper Readiness / Exhaustion Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- DB: `{report['db']}`",
        f"- Scoped paper ready: `{verdict['scoped_paper_ready']}`",
        f"- Broad landmark claim ready: `{verdict['broad_landmark_claim_ready']}`",
        f"- Stop rule: {report['stop_rule']}",
        "",
        "## Program Verdict",
        "",
        verdict["next_highest_yield_action"],
        "",
        "Broad/not-production-ready claims:",
        "",
        *[f"- {claim}" for claim in verdict["not_ready_claims"]],
        "",
        "## DB Evidence",
        "",
    ]
    for key, value in report["db_evidence"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Claim Boundaries", ""])
    for row in report["claim_boundary_rows"]:
        lines.extend(
            [
                f"### {row['claim']}",
                "",
                f"- Paper status: `{row['paper_status']}`",
                f"- Narrow writeable claim: {row['narrow_writeable_claim']}",
                f"- Forbidden overclaim: {row['forbidden_overclaim']}",
                f"- Nearest confuser: {row['nearest_confuser']}",
                f"- Kill/completion condition: {row['kill_or_completion_condition']}",
                f"- Next action: {row['next_action']}",
                "- Evidence:",
            ]
        )
        for key, value in row["current_evidence"].items():
            lines.append(f"  - `{key}`: `{value}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "paper_readiness_exhaustion_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "paper_readiness_exhaustion_audit.md").write_text(render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "program_verdict": report["program_verdict"],
                "db_evidence": report["db_evidence"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
