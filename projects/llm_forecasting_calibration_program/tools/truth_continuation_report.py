#!/usr/bin/env python3
"""GP-245 truth-continuation report.

Read-only synthesis over the local forecasting DB and project artifacts. The
report answers which continuation lanes remain live after the current law
validation work, and whether an already-scoreable human/crowd baseline exists
locally.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "truth_continuation_v1/workspace"

FB_RAW = PROGRAM / "forecaster_skill_calibration_v1/workspace/forecastbench_2026_05_24_raw.json"
FB_RESOLUTIONS = PROGRAM / "forecaster_skill_calibration_v1/workspace/fb_2026_04_12_resolutions.json"
CUTOFF_MANIFOLD_CANDIDATES = (
    PROGRAM / "cutoff_validity_v1/workspace/cutoff_manifold_acquisition_candidates.jsonl"
)
STAGE_C_MANIFOLD_PROBABILITIES = (
    PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_c_manifold_probability_acquisition.jsonl"
)
MARKET_BASELINE_REPORT = PROGRAM / "truth_continuation_v1/workspace/market_baseline_stage_c_report.json"

REPORTS = {
    "premium_channel": PROGRAM / "premium_channel_v1/workspace/premium_channel_report.json",
    "channel_holdout": PROGRAM / "channel_holdout_v1/workspace/channel_holdout_law_report.json",
    "channel_policy_cell": PROGRAM / "channel_policy_cell_v1/workspace/channel_policy_cell_validation.json",
    "cutoff_stage_b": PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_b_score_report.json",
    "anti_bias": PROGRAM / "anti_bias_collapse_v1/workspace/anti_bias_collapse_score.json",
    "router_confirm": PROGRAM / "router_confirmation_v1/workspace/router_confirmation_report.json",
    "router_rederive": PROGRAM / "router_rederivation_v1/workspace/conditional_router_rederivation_report.json",
    "decision_utility": PROGRAM / "decision_utility_v20/workspace/decision_utility_verdict.json",
    "f105": PROGRAM / "llm_effort_estimation/workspace/f105_effort_rescue_db_report.json",
    "cross_domain": PROGRAM / "cross_domain_benchmark_v19/workspace/benchmark_verdict.json",
    "base_rate_join": PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_c_base_rate_join_report.json",
}


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def scalar(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = cur.execute(sql, params).fetchone()
    return row[0] if row else None


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 6) if values else None


def parse_json_object(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def db_audit(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    market_like = [
        {
            "source": row[0],
            "source_corpus": row[1],
            "contracts": row[2],
            "y_known": row[3],
            "raw_json_market_field_rows": row[4],
        }
        for row in cur.execute(
            """
            SELECT source,
                   source_corpus,
                   COUNT(*) AS n,
                   SUM(CASE WHEN y_known IS NOT NULL THEN 1 ELSE 0 END) AS y_known_n,
                   SUM(CASE
                         WHEN raw_json LIKE '%freeze_datetime_value%'
                           OR raw_json LIKE '%market_price%'
                           OR raw_json LIKE '%market_consensus%'
                           OR raw_json LIKE '%manifold_probability%'
                           OR raw_json LIKE '%consensus_p_yes%'
                         THEN 1 ELSE 0 END) AS market_field_n
            FROM contracts
            WHERE lower(COALESCE(source, '')) LIKE '%metaculus%'
               OR lower(COALESCE(source, '')) LIKE '%manifold%'
               OR lower(COALESCE(source, '')) LIKE '%polymarket%'
               OR lower(COALESCE(source_corpus, '')) LIKE '%metaculus%'
               OR lower(COALESCE(source_corpus, '')) LIKE '%manifold%'
               OR lower(COALESCE(source_corpus, '')) LIKE '%polymarket%'
            GROUP BY source, source_corpus
            ORDER BY n DESC
            """
        )
    ]
    out = {
        "contracts": scalar(cur, "SELECT COUNT(*) FROM contracts"),
        "contracts_y_known": scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NOT NULL"),
        "pilot_calls": scalar(cur, "SELECT COUNT(*) FROM pilot_calls"),
        "calls_with_brier": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NOT NULL"),
        "market_like_contract_groups": market_like,
        "scoreable_market_like_contracts": sum(int(r["y_known"] or 0) for r in market_like),
        "market_like_rows_with_probability_fields": sum(
            int(r["raw_json_market_field_rows"] or 0) for r in market_like
        ),
    }
    con.close()
    return out


def forecastbench_audit() -> dict[str, Any]:
    raw = read_json(FB_RAW)
    questions = raw.get("questions", []) if isinstance(raw, dict) else []
    source_counts = Counter(q.get("source") for q in questions if isinstance(q, dict))
    freeze_value_rows = [
        q for q in questions if isinstance(q, dict) and q.get("freeze_datetime_value") is not None
    ]
    market_sources = {"manifold", "metaculus", "polymarket", "infer"}
    market_freeze_rows = [
        q for q in freeze_value_rows if str(q.get("source")).lower() in market_sources
    ]

    resolutions = read_json(FB_RESOLUTIONS)
    resolution_rows = (
        resolutions.get("resolutions", []) if isinstance(resolutions, dict) else []
    )
    question_ids = {str(q.get("id")) for q in questions if isinstance(q, dict) and q.get("id")}
    resolution_ids = {
        str(r.get("id")) for r in resolution_rows if isinstance(r, dict) and r.get("id")
    }
    overlap = question_ids & resolution_ids
    binary_resolutions = {
        str(r.get("id")): r
        for r in resolution_rows
        if isinstance(r, dict)
        and r.get("resolved")
        and r.get("resolved_to") in (0, 1, 0.0, 1.0)
        and r.get("id")
    }
    scoreable_rows = [
        q
        for q in questions
        if isinstance(q, dict)
        and q.get("id") in binary_resolutions
        and q.get("freeze_datetime_value") is not None
    ]
    scoreable_source_counts = Counter(q.get("source") for q in scoreable_rows)
    market_scoreable_rows = [
        q for q in scoreable_rows if str(q.get("source")).lower() in market_sources
    ]

    manifold_rows = read_jsonl(CUTOFF_MANIFOLD_CANDIDATES)
    manifold_probability_rows = 0
    for row in manifold_rows:
        raw_manifold = row.get("raw_manifold") or {}
        if raw_manifold.get("probability") is not None:
            manifold_probability_rows += 1
    stage_c_probability_rows = [
        row
        for row in read_jsonl(STAGE_C_MANIFOLD_PROBABILITIES)
        if row.get("fetch_status") == "joined"
    ]

    return {
        "forecastbench_raw_path": str(FB_RAW.relative_to(REPO)),
        "forecastbench_questions": len(questions),
        "source_counts": dict(sorted(source_counts.items())),
        "freeze_datetime_value_rows": len(freeze_value_rows),
        "market_or_crowd_freeze_rows": len(market_freeze_rows),
        "local_resolution_path": str(FB_RESOLUTIONS.relative_to(REPO)),
        "local_resolution_rows": len(resolution_rows),
        "question_resolution_id_overlap": len(overlap),
        "scoreable_frozen_value_rows": len(scoreable_rows),
        "scoreable_frozen_value_source_counts": dict(sorted(scoreable_source_counts.items())),
        "scoreable_market_or_crowd_rows": len(market_scoreable_rows),
        "cutoff_manifold_candidate_rows": len(manifold_rows),
        "cutoff_manifold_probability_rows": manifold_probability_rows,
        "stage_c_probability_rows": len(stage_c_probability_rows),
        "scoreable_now": bool(market_scoreable_rows),
        "conclusion": (
            "ForecastBench 2026-05-24 has frozen market/crowd values, and the "
            "local 2026-04-12 resolution dump overlaps on dataset rows, but it "
            "does not overlap on market/crowd rows. The Stage-C Manifold repair "
            "now supplies historical probabilities for the cutoff-validity panel, "
            "but that is a narrow Law 3 repair rather than a broad human/crowd "
            "baseline. Locally, there is still no general scoreable human/crowd "
            "comparison without a matching resolution/price source."
        ),
    }


def stage_c_market_baseline_audit(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    market_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT contract_id, p_success, brier, parsed_json
            FROM pilot_calls
            WHERE pilot_id = 'market_baseline_stage_c_v1'
              AND condition = 'stage_c_preoutcome_market_probability'
              AND schema_ok = 1
              AND brier IS NOT NULL
            """
        )
    ]
    contract_ids = [str(row["contract_id"]) for row in market_rows]
    llm_rows: list[dict[str, Any]] = []
    if contract_ids:
        placeholders = ",".join("?" for _ in contract_ids)
        llm_rows = [
            dict(row)
            for row in con.execute(
                f"""
                SELECT contract_id, family, brier
                FROM pilot_calls
                WHERE pilot_id = 'cutoff_stage_b_panel_v1'
                  AND contract_id IN ({placeholders})
                  AND schema_ok = 1
                  AND brier IS NOT NULL
                """,
                tuple(contract_ids),
            )
        ]
    con.close()

    market_briers = [float(row["brier"]) for row in market_rows]
    by_family: dict[str, list[float]] = defaultdict(list)
    panel_by_contract: dict[str, list[float]] = defaultdict(list)
    for row in llm_rows:
        by_family[str(row["family"])].append(float(row["brier"]))
        panel_by_contract[str(row["contract_id"])].append(float(row["brier"]))

    market_by_contract = {str(row["contract_id"]): row for row in market_rows}
    panel_deltas = []
    relation_market: dict[str, list[float]] = defaultdict(list)
    relation_llm: dict[str, list[float]] = defaultdict(list)
    for cid, row in market_by_contract.items():
        parsed = parse_json_object(row.get("parsed_json"))
        relation = str(parsed.get("cutoff_relation") or "unknown")
        relation_market[relation].append(float(row["brier"]))
        if cid in panel_by_contract:
            panel_deltas.append(float(row["brier"]) - statistics.mean(panel_by_contract[cid]))
    for row in llm_rows:
        market = market_by_contract.get(str(row["contract_id"]))
        if not market:
            continue
        parsed = parse_json_object(market.get("parsed_json"))
        relation = str(parsed.get("cutoff_relation") or "unknown")
        relation_llm[relation].append(float(row["brier"]))

    report_file = read_json(MARKET_BASELINE_REPORT) or {}
    return {
        "pilot_id": "market_baseline_stage_c_v1",
        "status": "db_ingested" if market_rows else "absent",
        "baseline_scope": "narrow_stage_c_preoutcome_market_probability_not_equal_information_human_baseline",
        "db_market_rows": len(market_rows),
        "db_llm_comparator_rows": len(llm_rows),
        "market_mean_brier": mean(market_briers),
        "llm_family_mean_brier": {family: mean(vals) for family, vals in sorted(by_family.items())},
        "market_minus_panel_mean_brier": mean(panel_deltas),
        "relation_mean_brier": {
            relation: {
                "market": mean(relation_market.get(relation, [])),
                "llm_calls": mean(relation_llm.get(relation, [])),
                "market_n_contracts": len(relation_market.get(relation, [])),
                "llm_n_calls": len(relation_llm.get(relation, [])),
            }
            for relation in sorted(set(relation_market) | set(relation_llm))
        },
        "report_path": str(MARKET_BASELINE_REPORT.relative_to(REPO)) if MARKET_BASELINE_REPORT.exists() else None,
        "report_file_present": bool(report_file),
        "interpretation": (
            "This is a narrow pre-outcome Manifold market bar, not a broad equal-information "
            "human/crowd baseline. It is useful for Law 3 information-timing interpretation."
        ),
    }


def report_summary() -> dict[str, Any]:
    loaded = {name: read_json(path) or {} for name, path in REPORTS.items()}
    premium = loaded["premium_channel"]
    premium_standard = premium.get("cross_family_standard") or {}
    policy = loaded["channel_policy_cell"]
    cutoff = loaded["cutoff_stage_b"]
    base_rate_join = loaded["base_rate_join"]
    base_rate_effect = (base_rate_join.get("repaired_effect") or {}).get("base_rate_matched") or {}
    anti = loaded["anti_bias"]
    router = loaded["router_rederive"]
    decision = loaded["decision_utility"]
    f105 = loaded["f105"]
    cross = loaded["cross_domain"]
    utility_tally = decision.get("overall_lift_tally") or {}
    rank_instability = (cross.get("cross_domain_analysis") or {}).get("pairwise_rank_instability") or []

    return {
        "law2_tail_risk": {
            "status": "diagnostic_supported_policy_demoted",
            "rows": premium.get("rows"),
            "worry_positive_families": premium_standard.get("worry_positive_families"),
            "worry_beats_confidence_and_sham_families": premium_standard.get(
                "worry_beats_confidence_and_sham_families"
            ),
            "policy_verdict": policy.get("verdict"),
            "plain_english": (
                "Second-channel worry/tail-risk is a warning-light for error "
                "risk, not a confirmed automatic Brier correction."
            ),
        },
        "law3_source_currency": {
            "status": (
                "promote_cutoff_validity_law_partial_base_rate_repair"
                if base_rate_effect.get("paired_cells")
                else cutoff.get("verdict") or "check_cutoff_stage_b_report"
            ),
            "calls": (cutoff.get("call_coverage") or {}).get("calls_in_db"),
            "post_minus_pre_brier": (cutoff.get("aggregate_delta") or {}).get("post_minus_pre"),
            "paired_stratum_delta": (cutoff.get("paired_stratum_delta") or {}).get("post_minus_pre"),
            "paired_stratum_p": (
                (cutoff.get("paired_stratum_delta") or {}).get("paired_permutation") or {}
            ).get("p_value"),
            "base_rate_joined_contracts": (base_rate_join.get("coverage") or {}).get("joined_contracts"),
            "base_rate_missing_contracts": (base_rate_join.get("coverage") or {}).get("missing_contracts"),
            "base_rate_matched_paired_cells": base_rate_effect.get("paired_cells"),
            "base_rate_matched_post_minus_pre_brier": base_rate_effect.get("post_minus_pre_brier"),
            "next_falsifier": (
                "Missing-row completion or second-source panel removes the "
                "post-minus-pre Brier gap."
            ),
        },
        "law1_carrier_bias": {
            "status": anti.get("verdict") or "check_anti_bias_report",
            "mimic_mean_collapse": ((anti.get("class_summary") or {}).get("MIMIC") or {}).get(
                "mean_collapse"
            ),
            "raw_gap_adjusted_mimic_coef": (
                anti.get("raw_gap_adjusted_control") or {}
            ).get("coef_mimic_after_raw_gap_and_family"),
            "next_falsifier": "Matched/randomized raw-gap panel still fails to show MIMIC-specific collapse.",
        },
        "router": {
            "status": router.get("verdict") or "check_router_rederivation_report",
            "next_falsifier": "Source-balanced router again fails Manifold/Polymarket leave-one-out.",
        },
        "decision_utility": {
            "status": "premium_thresholding_negative_on_retrospective_utility"
            if decision.get("headline_verdict")
            else "check_decision_utility_report",
            "utility_cells": utility_tally.get("n_cells"),
            "positive_lift_cells": utility_tally.get("n_positive_lift"),
            "negative_lift_cells": utility_tally.get("n_negative_lift"),
            "zero_lift_cells": utility_tally.get("n_zero_lift"),
            "mean_lift": utility_tally.get("mean_lift"),
            "next_falsifier": "Prospective utility regimes show channel-aware action loses to simpler abstain/threshold rules.",
        },
        "f105_effort": {
            "status": (
                (f105.get("sibling_paper_status") or {}).get("verdict")
                if isinstance(f105.get("sibling_paper_status"), dict)
                else None
            )
            or f105.get("status")
            or f105.get("verdict")
            or "check_f105_report",
            "rows": f105.get("rows") or f105.get("n_rows"),
            "next_falsifier": "Hidden objective-effort tasks erase the self-calibration signal.",
        },
        "cross_domain_benchmark": {
            "status": "pilot_rank_instability_seen_b_c_unscoreable",
            "rank_instability_pairs": len(rank_instability),
            "next_falsifier": "Rank instability disappears after B/C are scoreable and domains are balanced.",
        },
    }


def continuation_lanes(crowd: dict[str, Any], market: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = [
        {
            "rank": 1,
            "lane": "source_currency_law_repair",
            "action": "Base-rate repair or add a second source for Law 3.",
            "why": "Strongest positive evidence and clearest practical implication.",
            "kill_condition": "Matched source/base-rate panel removes the cutoff gap.",
        },
        {
            "rank": 2,
            "lane": "broad_market_human_baseline_completion",
            "action": (
                "Keep the narrow Stage-C market bar as a scoped baseline, but acquire/join "
                "broad equal-information market or crowd rows before making LLM-vs-human claims."
            ),
            "why": (
                "Stage-C market baseline is DB-ingested, but ForecastBench broad market/crowd "
                "overlap remains zero locally."
            ),
            "kill_condition": "LLM advantage disappears under same-question, same-time market/human baselines.",
        },
        {
            "rank": 3,
            "lane": "source_balanced_router",
            "action": "Rebuild router validation with source-balanced splits.",
            "why": "There is contract-level headroom, but current routers fail robustness.",
            "kill_condition": "Router fails source leave-one-out again.",
        },
        {
            "rank": 4,
            "lane": "prospective_decision_utility",
            "action": "Declare utility regimes first, then test route/shrink/abstain.",
            "why": "Tail-risk diagnostics matter only if they change decisions beneficially.",
            "kill_condition": "Channel-aware action harms utility versus simpler rules.",
        },
        {
            "rank": 5,
            "lane": "law2_tail_risk_policy_reopen_only_if_prospective",
            "action": "Keep tail-risk as diagnostic; reopen policy only with prospective rows.",
            "why": "The diagnostic survived; the broad Brier policy did not.",
            "kill_condition": "Frozen prospective shrink/reroute rule fails Brier and utility.",
        },
        {
            "rank": 6,
            "lane": "law1_raw_gap_deconfounded",
            "action": "Only reopen carrier/bias law with matched or randomized raw gaps.",
            "why": "The first clean mechanism was scoped by raw-gap confounding.",
            "kill_condition": "MIMIC does not survive raw-gap controls.",
        },
        {
            "rank": 7,
            "lane": "f105_effort_hidden_test",
            "action": "Run hidden objective effort tasks as sibling paper work.",
            "why": "Promising but not GP-245 binary Brier evidence.",
            "kill_condition": "Self-calibrated effort estimates fail hidden objective outcomes.",
        },
        {
            "rank": 8,
            "lane": "cross_domain_benchmark_repair",
            "action": "Repair B/C scoreability and preserve IDs/outcomes.",
            "why": "Useful benchmark infrastructure, but lower immediate scientific yield.",
            "kill_condition": "Family/domain rank instability vanishes under balanced N.",
        },
    ]
    if crowd.get("scoreable_now"):
        lanes.insert(
            1,
            {
                "rank": 2,
                "lane": "already_scoreable_crowd_comparison",
                "action": "Score LLM predictions against the matched local crowd baseline.",
                "why": "Would directly answer human/crowd comparison without new collection.",
                "kill_condition": "LLM route fails same-question/same-time Brier or utility.",
            },
        )
        for idx, lane in enumerate(lanes, start=1):
            lane["rank"] = idx
    return lanes


def render_md(result: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Truth Continuation Report",
        "",
        "Read-only local report. No model calls and no DB mutation.",
        "",
        "## Crowd / Human Baseline Audit",
        "",
    ]
    crowd = result["crowd_baseline_audit"]
    market = result["stage_c_market_baseline_audit"]
    lines.extend(
        [
            f"- ForecastBench raw questions: {crowd['forecastbench_questions']}",
            f"- Rows with frozen values: {crowd['freeze_datetime_value_rows']}",
            f"- Market/crowd-source frozen rows: {crowd['market_or_crowd_freeze_rows']}",
            f"- Local resolution rows checked: {crowd['local_resolution_rows']}",
            f"- Question/resolution ID overlap: {crowd['question_resolution_id_overlap']}",
            f"- Scoreable frozen-value rows: {crowd['scoreable_frozen_value_rows']}",
            f"- Scoreable market/crowd rows: {crowd['scoreable_market_or_crowd_rows']}",
            f"- Cutoff Manifold resolved candidate rows: {crowd['cutoff_manifold_candidate_rows']}",
            f"- Cutoff Manifold rows with historical probability: {crowd['cutoff_manifold_probability_rows']}",
            f"- Stage-C Manifold probability rows: {crowd['stage_c_probability_rows']}",
            "",
            f"**Conclusion:** {crowd['conclusion']}",
            "",
            "## Stage-C Market Baseline Audit",
            "",
            f"- Status: `{market['status']}`",
            f"- Scope: `{market['baseline_scope']}`",
            f"- DB market rows: {market['db_market_rows']}",
            f"- DB LLM comparator rows: {market['db_llm_comparator_rows']}",
            f"- Market mean Brier: `{market['market_mean_brier']}`",
            f"- LLM family mean Brier: `{market['llm_family_mean_brier']}`",
            f"- Market minus panel mean Brier: `{market['market_minus_panel_mean_brier']}`",
            f"- Report: `{market['report_path']}`",
            "",
            "Relation breakdown:",
            "",
            "```json",
            json.dumps(market["relation_mean_brier"], indent=2, sort_keys=True),
            "```",
            "",
            f"**Interpretation:** {market['interpretation']}",
            "",
            "## Current Law State",
            "",
        ]
    )
    for name, summary in result["law_and_lane_summary"].items():
        lines.append(f"### {name}")
        for key, value in summary.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    lines.extend(["## Continuation Lanes", ""])
    for lane in result["continuation_lanes"]:
        lines.extend(
            [
                f"### {lane['rank']}. {lane['lane']}",
                f"- Action: {lane['action']}",
                f"- Why: {lane['why']}",
                f"- Kill condition: {lane['kill_condition']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Simple Practical Claim",
            "",
            "The strongest user-facing claim is not broad LLM superiority over",
            "humans/crowds. It is that LLM forecasts need a validity layer:",
            "source-currency checks, family/source routing, second-channel",
            "diagnostics, and prospective utility tests before deployment.",
            "",
            "Tail-risk/worry is currently best described as a warning light for",
            "forecast fragility, not an autopilot that fixes probabilities.",
            "",
        ]
    )
    return "\n".join(lines)


def build(db: Path) -> dict[str, Any]:
    crowd = forecastbench_audit()
    market = stage_c_market_baseline_audit(db)
    return {
        "db": db_audit(db),
        "crowd_baseline_audit": crowd,
        "stage_c_market_baseline_audit": market,
        "law_and_lane_summary": report_summary(),
        "continuation_lanes": continuation_lanes(crowd, market),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    result = build(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "truth_continuation_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "truth_continuation_report.md").write_text(
        render_md(result),
        encoding="utf-8",
    )
    print(f"wrote {args.out_dir / 'truth_continuation_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
