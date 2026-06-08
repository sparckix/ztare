#!/usr/bin/env python3
"""Generate GP-245 next-experiment packets.

The packets are deliberately action-shaped: each names prior evidence consumed,
the current local feasibility, the smallest non-duplicative next run, and the
kill condition. No model calls and no DB mutation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "truth_seeking_v1/workspace"


def scalar(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = cur.execute(sql, params).fetchone()
    return row[0] if row else None


def db_snapshot(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    source_cutoff = [
        {
            "source": row[0],
            "source_corpus": row[1],
            "post_training_cutoff": row[2],
            "contracts": row[3],
            "y_known": row[4],
        }
        for row in cur.execute(
            """
            SELECT source, source_corpus, post_training_cutoff,
                   COUNT(*) AS n,
                   SUM(CASE WHEN y_known IS NOT NULL THEN 1 ELSE 0 END) AS y_known_n
            FROM contracts
            GROUP BY source, source_corpus, post_training_cutoff
            ORDER BY y_known_n DESC, n DESC
            """
        )
    ]
    complete_family_sources = [
        {
            "source": row[0] or "",
            "source_corpus": row[1] or "",
            "families": row[2],
            "contracts": row[3],
        }
        for row in cur.execute(
            """
            WITH fams AS (
              SELECT pc.contract_id, COUNT(DISTINCT pc.family) AS nfam
              FROM pilot_calls pc
              JOIN contracts c ON c.contract_id = pc.contract_id
              WHERE pc.brier IS NOT NULL AND pc.schema_ok = 1
              GROUP BY pc.contract_id
            )
            SELECT c.source, c.source_corpus, f.nfam, COUNT(*) AS n
            FROM fams f
            JOIN contracts c ON c.contract_id = f.contract_id
            WHERE f.nfam >= 3
            GROUP BY c.source, c.source_corpus, f.nfam
            ORDER BY n DESC
            """
        )
    ]
    law3_calls = scalar(
        cur,
        "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = 'cutoff_stage_b_panel_v1'",
    )
    anti_bias_calls = scalar(
        cur,
        "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = 'anti_bias_collapse_v1'",
    )
    con.close()
    return {
        "source_cutoff_groups": source_cutoff,
        "complete_family_source_groups": complete_family_sources,
        "law3_stage_b_calls": law3_calls,
        "anti_bias_calls": anti_bias_calls,
    }


def source_currency_feasibility(snapshot: dict[str, Any]) -> dict[str, Any]:
    resolved = [g for g in snapshot["source_cutoff_groups"] if g["y_known"]]
    by_source: dict[str, Counter] = {}
    for group in resolved:
        source = group["source"] or ""
        by_source.setdefault(source, Counter())
        key = "post" if group["post_training_cutoff"] == 1 else "pre" if group["post_training_cutoff"] == 0 else "unknown"
        by_source[source][key] += int(group["y_known"] or 0)
    source_pairs = {
        source: dict(counts)
        for source, counts in sorted(by_source.items())
        if counts.get("pre", 0) and counts.get("post", 0)
    }
    second_source_ready = {
        source: counts
        for source, counts in source_pairs.items()
        if source != "manifold"
    }
    return {
        "resolved_source_cutoff_pairs": source_pairs,
        "second_source_ready_pairs": second_source_ready,
        "local_second_source_ready": bool(second_source_ready),
        "interpretation": (
            "Local resolved pre/post cutoff data currently supports Manifold. "
            "A second-source replication is not locally ready unless another "
            "source gets resolved pre-cutoff rows or a historical dump is joined."
        ),
    }


def router_feasibility(snapshot: dict[str, Any]) -> dict[str, Any]:
    groups = snapshot["complete_family_source_groups"]
    five_family = [g for g in groups if int(g["families"]) >= 5]
    major_sources = [
        g for g in five_family if int(g["contracts"]) >= 30 and g["source"]
    ]
    thin_sources = [
        g for g in five_family if 0 < int(g["contracts"]) < 30 and g["source"]
    ]
    return {
        "five_family_major_sources": major_sources,
        "five_family_thin_sources": thin_sources,
        "source_balanced_existing_sources": [g["source"] for g in major_sources],
        "interpretation": (
            "Existing complete-family rows can support a source-balanced audit "
            "over major local sources, especially Manifold, Polymarket, and "
            "premium_public_clean. Thin sources are too small for robustness."
        ),
    }


def packets(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    law3 = source_currency_feasibility(snapshot)
    router = router_feasibility(snapshot)
    return [
        {
            "id": "GP245-PACKET-N3-HIGH-WORRY-ACTION-CONTROL",
            "rank": 1,
            "lane": "forecast_improvement_control",
            "consumes_prior": [
                "Law 2 diagnostic error-readout is supported but policy translation is demoted",
                "Generic self-distractor / skeptical / rationale-only interventions mostly fail",
                "N2 broad selective action failed confirmation",
                "F117 killed the current router as applied policy, raising the yield of direct action-control testing",
                "N3 high-worry packet is frozen but not DB-scored",
            ],
            "local_feasibility": {
                "requires_new_rows": True,
                "can_prepare_without_calls": False,
                "protocol": "public/METHODOLOGY.md#nurture--intervention-discipline",
                "frozen_queue": "nurture_intervention_v1/workspace/n3_high_worry_action_policy_dispatch_queue.jsonl",
                "expected_rows": 72,
                "db_required": "contracts + pilot_runs + pilot_calls with raw traces",
            },
            "next_artifact": "nurture_intervention_v1/workspace/n3_high_worry_action_policy_v1_score_report.{json,md}",
            "smallest_nonduplicative_run": (
                "Dispatch the frozen 72-row high-worry action-control slate and "
                "score selective_action against paired raw Brier, forecast-all, "
                "abstain-all, confidence-threshold abstention, and blind "
                "judge/reroute review."
            ),
            "kill_condition": (
                "Selective action loses to paired raw baseline or to simple "
                "abstain/threshold controls; unresolved reroute rows cannot count "
                "as wins."
            ),
            "do_not_repeat": [
                "Do not run another standalone worry or rationale prompt.",
                "Do not infer improvement from diagnostic correlation.",
                "Do not count reroute_or_judge as successful without blind review rows.",
            ],
        },
        {
            "id": "GP245-PACKET-L3-BASERATE-REPAIR",
            "rank": 2,
            "lane": "source_currency_law_repair",
            "consumes_prior": [
                "Stage-B 240-call Law 3 panel promoted a source-currency effect",
                "Stage-C missing-band sensitivity survived adversarial assignment",
                "F116 local void miner found 0 resolved pre-cutoff non-Manifold rows against the 50-row target",
            ],
            "local_feasibility": law3,
            "next_artifact": "cutoff_validity_v1/workspace/cutoff_second_source_pre_cutoff_acquisition_targets.jsonl",
            "smallest_nonduplicative_run": (
                "Acquire or backfill the 50 resolved pre-cutoff non-Manifold rows "
                "matching the emitted source/freeze-band/question-length cells; "
                "then freeze a second-source pre/post panel."
            ),
            "kill_condition": (
                "Post-minus-pre Brier gap falls below 0.02 or changes sign after "
                "missing-row completion or second-source replication."
            ),
            "do_not_repeat": [
                "Do not run more unmatched pre/post calls.",
                "Do not spend more local mining cycles unless a new raw source bundle appears.",
                "Do not dispatch model calls on the post-cutoff-only second-source slate.",
            ],
        },
        {
            "id": "GP245-PACKET-ROUTER-NEW-FEATURES-ONLY",
            "rank": 3,
            "lane": "no_poolability_router",
            "consumes_prior": [
                "Registered F107 router failed",
                "Rederived source_sigma router beat baselines on a 34-row holdout but failed source LOO",
                "F117 source-balanced audit killed the current source/sigma router against confident-NO baselines",
            ],
            "local_feasibility": router,
            "next_artifact": "router_rederivation_v1/workspace/new_feature_router_packet.{json,md}",
            "smallest_nonduplicative_run": (
                "Only continue router work if a new feature set is predeclared "
                "beyond source+sigma. Required promotion bar: source-balanced lift "
                "over confident-NO mean/train-best in every major source."
            ),
            "kill_condition": (
                "Any major source loses, or aggregate lift disappears against "
                "confident-NO baselines."
            ),
            "do_not_repeat": [
                "Do not defend the existing hand-router.",
                "Do not rerun source+sigma.",
                "Do not pool all sources and call the result deployable.",
            ],
        },
        {
            "id": "GP245-PACKET-UTILITY-PROSPECTIVE",
            "rank": 4,
            "lane": "decision_utility",
            "consumes_prior": [
                "Retrospective premium-aware thresholding harmed 44/81 cells and helped 2/81",
                "Law 2 survives as diagnostic error readout, not action policy",
            ],
            "local_feasibility": {
                "requires_new_rows": True,
                "can_prepare_without_calls": True,
                "best_carrier": "prospective public rows with declared cost regimes before scoring",
            },
            "next_artifact": "decision_utility_v20/workspace/prospective_utility_packet.{json,md}",
            "smallest_nonduplicative_run": (
                "Prepare a cost-regime packet with route/shrink/abstain actions fixed "
                "before outcomes. Run only after costs map to real false-positive/"
                "false-negative semantics."
            ),
            "kill_condition": (
                "Channel-aware action loses to Brier-blind thresholding or abstention "
                "on the same prospective rows."
            ),
            "do_not_repeat": [
                "Do not reuse the lambda*(1+premium/100) rule as if it were alive.",
                "Do not claim utility from Brier or correlation alone.",
            ],
        },
        {
            "id": "GP245-PACKET-L2-TAIL-RISK-POLICY",
            "rank": 5,
            "lane": "tail_risk_policy_translation",
            "consumes_prior": [
                "Premium-clean n=341: worry-positive 5/5 and beats confidence+sham 4/5",
                "codex_55/worry policy cell demoted by temporal/source stress",
            ],
            "local_feasibility": {
                "diagnostic_ready": True,
                "policy_ready": False,
                "requires_prospective_or_new_holdout": True,
            },
            "next_artifact": "channel_policy_cell_v1/workspace/prospective_tail_policy_packet.{json,md}",
            "smallest_nonduplicative_run": (
                "Freeze one of three actions for high-worry rows: review/reroute, "
                "abstain, or shrink. Compare to raw probabilities and simple "
                "uncertainty thresholds; do not test another generic worry correlation."
            ),
            "kill_condition": "High-worry action fails Brier and utility against simpler controls.",
            "do_not_repeat": [
                "Do not run generic worry-vs-Brier again.",
                "Do not pool worry signs across families without family conditioning.",
            ],
        },
        {
            "id": "GP245-PACKET-L1-RAW-GAP",
            "rank": 6,
            "lane": "carrier_bias_inheritance",
            "consumes_prior": [
                "Anti-bias collapse score scoped/killed the clean MIMIC-collapse claim",
                "Raw starting gap explained the attractive mechanism",
            ],
            "local_feasibility": {
                "existing_anti_bias_calls": snapshot["anti_bias_calls"],
                "requires_new_matched_or_randomized_rows": True,
            },
            "next_artifact": "anti_bias_collapse_v1/workspace/raw_gap_matched_packet.{json,md}",
            "smallest_nonduplicative_run": (
                "Construct pairs where raw frame-gap is matched or randomized before "
                "class labels are revealed; score MIMIC vs inherit-control collapse "
                "only after raw gap is balanced."
            ),
            "kill_condition": "MIMIC still fails label-shuffle and raw-gap controls.",
            "do_not_repeat": [
                "Do not scale the old anti-bias slate without raw-gap control.",
            ],
        },
    ]


def render_md(result: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Next Experiment Packets",
        "",
        "Generated no-call packet queue. Packets are ranked by current truth yield,",
        "not by optimism.",
        "",
    ]
    for packet in result["packets"]:
        lines.extend(
            [
                f"## {packet['rank']}. {packet['id']}",
                "",
                f"- Lane: `{packet['lane']}`",
                f"- Next artifact: `{packet['next_artifact']}`",
                f"- Smallest non-duplicative run: {packet['smallest_nonduplicative_run']}",
                f"- Kill condition: {packet['kill_condition']}",
                "",
                "Consumes prior:",
            ]
        )
        for item in packet["consumes_prior"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Do not repeat:")
        for item in packet["do_not_repeat"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Local feasibility:")
        lines.append("```json")
        lines.append(json.dumps(packet["local_feasibility"], indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def build(db: Path) -> dict[str, Any]:
    snapshot = db_snapshot(db)
    return {
        "schema": "gp245-next-experiment-packets-v1",
        "db": str(db),
        "snapshot": snapshot,
        "packets": packets(snapshot),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = build(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "next_experiment_packets.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "next_experiment_packets.md").write_text(
        render_md(result),
        encoding="utf-8",
    )
    print(f"wrote {args.out_dir / 'next_experiment_packets.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
