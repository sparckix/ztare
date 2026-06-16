#!/usr/bin/env python3
"""Audit the current equal-information market/human baseline void.

This is a no-call, no-network audit. It answers whether the local DB already
contains enough matched market/human baseline evidence to support statements
like "LLM > human/market" or "LLM + market > market".
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_DIR = (
    PROGRAM
    / "truth_continuation_v1/workspace/equal_information_baseline_void_2026_06_03"
)
DEFAULT_CEC = (
    PROGRAM
    / "cutoff_validity_v1/workspace/cutoff_general_source_cec_packet.json"
)
DEFAULT_METACULUS_PROBE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/metaculus_api_access_probe_2026_06_03.md"
)
DEFAULT_METACULUS_REPROBE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/metaculus_api_access_reprobe_2026_06_03.json"
)
DEFAULT_REPLACEMENT_SAMPLE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_sample_2026_06_15/equal_information_replacement_sample.json"
)
DEFAULT_REPLACEMENT_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15/equal_information_replacement_score.json"
)


MARKET_BASELINE_PILOTS = {"market_baseline_stage_c_v1"}
EQUAL_INFORMATION_BASELINE_PILOTS = {
    "equal_information_polymarket_baseline_v1",
    "equal_information_replacement_polymarket_baseline_v1",
}
LLM_STAGE_B_PILOT = "cutoff_stage_b_panel_v1"


def brier(p: float, y: float) -> float:
    return (p - y) ** 2


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_rows(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    source_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              COALESCE(source, '') AS source,
              COALESCE(source_corpus, '') AS source_corpus,
              COUNT(*) AS contracts,
              SUM(y_known IS NOT NULL) AS resolved_contracts,
              SUM(post_training_cutoff = 1) AS post_cutoff_contracts,
              SUM(post_training_cutoff = 0) AS pre_cutoff_contracts
            FROM contracts
            GROUP BY COALESCE(source, ''), COALESCE(source_corpus, '')
            ORDER BY resolved_contracts DESC, contracts DESC
            """
        )
    ]

    pilot_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              pc.pilot_id,
              COALESCE(pr.primitive, pc.primitive, '') AS primitive,
              COUNT(*) AS calls,
              COUNT(DISTINCT pc.contract_id) AS contracts,
              SUM(pc.schema_ok = 1) AS schema_ok,
              AVG(pc.brier) AS mean_brier
            FROM pilot_calls pc
            LEFT JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE c.y_known IS NOT NULL
            GROUP BY pc.pilot_id, COALESCE(pr.primitive, pc.primitive, '')
            ORDER BY calls DESC
            """
        )
    ]

    baseline_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              pc.pilot_id,
              pc.contract_id,
              pc.p_success,
              pc.brier,
              c.y_known,
              c.source,
              c.source_corpus,
              COALESCE(json_extract(pc.parsed_json, '$.cutoff_relation'),
                       json_extract(pc.raw_json, '$.cutoff_relation'),
                       '') AS cutoff_relation,
              COALESCE(json_extract(pc.parsed_json, '$.base_rate_provenance'),
                       json_extract(pc.raw_json, '$.base_rate_provenance'),
                       '') AS provenance
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id IN ('market_baseline_stage_c_v1')
              AND pc.schema_ok = 1
              AND c.y_known IS NOT NULL
            ORDER BY pc.contract_id
            """
        )
    ]

    equal_information_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              ebo.pilot_id,
              ebo.contract_id,
              ebo.p_success,
              ebo.brier,
              c.y_known,
              c.source,
              c.source_corpus,
              COALESCE(json_extract(ebo.source_currency_receipt, '$.cutoff_relation'), '') AS cutoff_relation,
              COALESCE(json_extract(ebo.source_currency_receipt, '$.history_source'), ebo.provenance_url, '') AS provenance
            FROM external_baseline_observations ebo
            JOIN contracts c ON c.contract_id = ebo.contract_id
            WHERE ebo.pilot_id IN (
                'equal_information_polymarket_baseline_v1',
                'equal_information_replacement_polymarket_baseline_v1'
              )
              AND ebo.equal_information_flag = 1
              AND ebo.schema_ok = 1
              AND c.y_known IS NOT NULL
            ORDER BY ebo.contract_id
            """
        )
    ]

    llm_stage_b_rows = [
        dict(row)
        for row in con.execute(
            """
            WITH llm AS (
              SELECT
                pc.contract_id,
                AVG(pc.p_success) AS panel_p,
                AVG(pc.brier) AS family_call_mean_brier,
                COUNT(*) AS calls,
                COALESCE(json_extract(pc.raw_json, '$.cutoff_relation'), '') AS cutoff_relation
              FROM pilot_calls pc
              WHERE pc.pilot_id = ?
                AND pc.schema_ok = 1
              GROUP BY pc.contract_id
            )
            SELECT
              llm.contract_id,
              llm.panel_p,
              llm.family_call_mean_brier,
              llm.calls,
              llm.cutoff_relation,
              c.y_known,
              c.source,
              c.source_corpus
            FROM llm
            JOIN contracts c ON c.contract_id = llm.contract_id
            WHERE c.y_known IS NOT NULL
            ORDER BY llm.contract_id
            """,
            (LLM_STAGE_B_PILOT,),
        )
    ]

    con.close()
    return {
        "source_rows": source_rows,
        "pilot_rows": pilot_rows,
        "baseline_rows": baseline_rows,
        "equal_information_rows": equal_information_rows,
        "llm_stage_b_rows": llm_stage_b_rows,
    }


def summarize_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_contracts": 0}
    by_source = Counter(str(row["source"] or "unknown") for row in rows)
    by_relation = Counter(str(row["cutoff_relation"] or "unknown") for row in rows)
    ys = [float(row["y_known"]) for row in rows]
    briers = [float(row["brier"]) for row in rows]
    return {
        "n_contracts": len({row["contract_id"] for row in rows}),
        "n_rows": len(rows),
        "sources": dict(sorted(by_source.items())),
        "cutoff_relation_counts": dict(sorted(by_relation.items())),
        "outcome_yes": int(sum(ys)),
        "outcome_no": len(ys) - int(sum(ys)),
        "mean_brier": mean(briers),
        "brier_lt_0_01": sum(1 for value in briers if value < 0.01),
        "brier_lt_0_05": sum(1 for value in briers if value < 0.05),
        "provenance_counts": dict(
            Counter(str(row["provenance"] or "unknown") for row in rows).most_common()
        ),
    }


def summarize_llm_stage_b(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_contracts": 0}
    out: dict[str, Any] = {
        "n_contracts": len(rows),
        "n_calls": sum(int(row["calls"]) for row in rows),
        "sources": dict(Counter(str(row["source"] or "unknown") for row in rows).most_common()),
        "cutoff_relation_counts": dict(
            Counter(str(row["cutoff_relation"] or "unknown") for row in rows).most_common()
        ),
        "panel_mean_probability_brier": mean(
            brier(float(row["panel_p"]), float(row["y_known"])) for row in rows
        ),
        "family_call_mean_brier": mean(float(row["family_call_mean_brier"]) for row in rows),
    }
    for relation in ("pre_cutoff", "post_cutoff"):
        rel_rows = [row for row in rows if str(row["cutoff_relation"]) == relation]
        if rel_rows:
            out[relation] = {
                "n_contracts": len(rel_rows),
                "n_calls": sum(int(row["calls"]) for row in rel_rows),
                "panel_mean_probability_brier": mean(
                    brier(float(row["panel_p"]), float(row["y_known"])) for row in rel_rows
                ),
                "family_call_mean_brier": mean(
                    float(row["family_call_mean_brier"]) for row in rel_rows
                ),
            }
    return out


def coverage_matrix(
    baseline_rows: list[dict[str, Any]],
    llm_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_ids = {str(row["contract_id"]) for row in baseline_rows}
    llm_ids = {str(row["contract_id"]) for row in llm_rows}
    overlap_ids = baseline_ids & llm_ids
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"llm_contracts": 0, "baseline_contracts": 0, "overlap": 0})
    for row in llm_rows:
        by_source[str(row["source"] or "unknown")]["llm_contracts"] += 1
    for row in baseline_rows:
        by_source[str(row["source"] or "unknown")]["baseline_contracts"] += 1
    for row in llm_rows:
        if str(row["contract_id"]) in overlap_ids:
            by_source[str(row["source"] or "unknown")]["overlap"] += 1
    return {
        "llm_stage_b_contracts": len(llm_ids),
        "market_baseline_contracts": len(baseline_ids),
        "matched_overlap_contracts": len(overlap_ids),
        "stage_b_without_market_baseline": len(llm_ids - baseline_ids),
        "baseline_without_stage_b_llm": len(baseline_ids - llm_ids),
        "by_source": dict(sorted(by_source.items())),
    }


def source_snapshot(source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, dict[str, int]] = defaultdict(
        lambda: {"contracts": 0, "resolved": 0, "pre_cutoff": 0, "post_cutoff": 0}
    )
    for row in source_rows:
        key = str(row["source"] or "unknown")
        by_source[key]["contracts"] += int(row["contracts"] or 0)
        by_source[key]["resolved"] += int(row["resolved_contracts"] or 0)
        by_source[key]["pre_cutoff"] += int(row["pre_cutoff_contracts"] or 0)
        by_source[key]["post_cutoff"] += int(row["post_cutoff_contracts"] or 0)
    return dict(sorted(by_source.items(), key=lambda item: (-item[1]["resolved"], item[0])))


def verdict(report: dict[str, Any]) -> dict[str, Any]:
    coverage = report["coverage"]
    equal_info = report["equal_information_baselines"]["equal_information_polymarket_baseline_v1"]
    replacement = (report.get("external_target_state") or {}).get("replacement_sample") or {}
    replacement_score = (report.get("external_target_state") or {}).get("replacement_score") or {}
    broad_sources = [
        source
        for source, row in coverage["by_source"].items()
        if int(row.get("baseline_contracts") or 0) > 0
    ]
    stage_c = report["market_baselines"]["market_baseline_stage_c_v1"]
    if replacement_score.get("state") == "market_beats_model_panel_on_replacement_multifamily_slice":
        state = "replacement_multifamily_market_control_market_ahead"
    elif str(replacement_score.get("state") or "").startswith("market_beats_model_on_replacement_"):
        state = "replacement_single_family_market_control_market_ahead"
    elif (
        replacement.get("verdict") == "replacement_sample_ready_for_model_packet"
        and int(equal_info.get("n_contracts") or 0) >= 24
    ):
        state = "replacement_equal_information_baseline_ready_for_model_forecasts"
    elif int(equal_info.get("n_contracts") or 0) > 0 and int(equal_info.get("n_contracts") or 0) < 24:
        state = "partial_equal_information_baseline_underpowered"
    elif broad_sources == ["manifold"] and int(stage_c["n_contracts"]) == 51:
        state = "broad_equal_information_baseline_absent"
    elif coverage["matched_overlap_contracts"] < 100:
        state = "baseline_present_but_underpowered_or_narrow"
    else:
        state = "baseline_surface_ready_for_broad_test"
    return {
        "state": state,
        "promotion_gate": (
            "A broad LLM-vs-human/market or LLM+market claim needs matched "
            "contract-level baseline rows across at least two independent "
            "sources, source-valid/post-cutoff reporting, and heldout or "
            "leave-one-out blend tests against market-only."
        ),
        "current_action": (
            "Do not make an LLM-beats-market claim; the completed four-family "
            "replacement slice loses to market. The next broad-claim gate is an "
            "independent equal-information source, not more calls on this packet."
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = fetch_rows(args.db)
    cec = load_json(args.cec)
    target_summary = ((cec.get("current_state") or {}).get("target_summary") or {})
    metaculus_verdict = (cec.get("verdict") or {}).get("existing_target_next_step")
    replacement_sample = load_json(args.replacement_sample)
    replacement_score = load_json(args.replacement_score) if args.replacement_score.exists() else {}
    market_baselines = {
        "market_baseline_stage_c_v1": summarize_baselines(rows["baseline_rows"])
    }
    equal_information_baselines = {
        "equal_information_polymarket_baseline_v1": summarize_baselines(
            rows["equal_information_rows"]
        )
    }
    report: dict[str, Any] = {
        "schema": "gp245-equal-information-baseline-void-v1",
        "inputs": {
            "db": str(args.db.relative_to(REPO)),
            "cec_packet": str(args.cec.relative_to(REPO)) if args.cec.exists() else None,
            "metaculus_probe": (
                str(args.metaculus_probe.relative_to(REPO))
                if args.metaculus_probe.exists()
                else None
            ),
            "metaculus_reprobe": (
                str(args.metaculus_reprobe.relative_to(REPO))
                if args.metaculus_reprobe.exists()
                else None
            ),
            "replacement_sample": (
                str(args.replacement_sample.relative_to(REPO))
                if args.replacement_sample.exists()
                else None
            ),
            "replacement_score": (
                str(args.replacement_score.relative_to(REPO))
                if args.replacement_score.exists()
                else None
            ),
        },
        "source_snapshot": source_snapshot(rows["source_rows"]),
        "resolved_pilot_top": rows["pilot_rows"][:30],
        "market_baselines": market_baselines,
        "equal_information_baselines": equal_information_baselines,
        "llm_stage_b": summarize_llm_stage_b(rows["llm_stage_b_rows"]),
        "coverage": coverage_matrix(rows["baseline_rows"], rows["llm_stage_b_rows"]),
        "external_target_state": {
            "metaculus_existing_target_next_step": metaculus_verdict,
            "remaining_target_summary": target_summary,
            "metaculus_probe_exists": args.metaculus_probe.exists(),
            "metaculus_reprobe": load_json(args.metaculus_reprobe),
            "replacement_sample": {
                "verdict": replacement_sample.get("verdict"),
                "candidate_rows": replacement_sample.get("candidate_rows"),
                "selected_rows": replacement_sample.get("selected_rows"),
                "selected_counts": replacement_sample.get("selected_counts"),
                "selection_rule": replacement_sample.get("selection_rule"),
                "next_action": replacement_sample.get("next_action"),
                "artifact": (
                    str(args.replacement_sample.relative_to(REPO))
                    if args.replacement_sample.exists()
                    else None
                ),
            },
            "replacement_score": {
                "state": replacement_score.get("state"),
                "summary": replacement_score.get("summary"),
                "artifact": (
                    str(args.replacement_score.relative_to(REPO))
                    if args.replacement_score.exists()
                    else None
                ),
            },
        },
        "interpretation": (
            "The local evidence unit for human/market comparison is the matched "
            "contract. Platform trader count is not a substitute for more "
            "matched outcomes, and repeated LLM family calls are not independent "
            "contract outcomes. The current broad comparison is blocked by "
            "missing baseline rows, not by lack of another prompt condition."
        ),
    }
    report["verdict"] = verdict(report)
    return report


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_baseline_void_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stage_c = report["market_baselines"]["market_baseline_stage_c_v1"]
    equal_info = report["equal_information_baselines"]["equal_information_polymarket_baseline_v1"]
    coverage = report["coverage"]
    llm = report["llm_stage_b"]
    ext = report["external_target_state"]
    replacement = ext["replacement_sample"]
    replacement_score = ext["replacement_score"]
    if replacement_score.get("state"):
        equal_info_status = (
            f"{equal_info['n_contracts']} equal-information market rows ingested; "
            f"replacement score state={replacement_score.get('state')}"
        )
        replacement_next_action = (
            "Completed for the frozen four-family replacement packet; use the "
            "score section below. The next broad-claim gate is an independent "
            "equal-information source."
        )
    else:
        equal_info_status = (
            f"{equal_info['n_contracts']} equal-information market rows ingested; "
            "model forecasts still missing for the replacement packet"
        )
        replacement_next_action = replacement.get("next_action")
    score_summary = replacement_score.get("summary") or {}
    score_lines = []
    if score_summary:
        family_summary = score_summary.get("family_summary") or {}
        score_lines = [
            f"- Model-call rows: `{score_summary.get('row_n')}`",
            f"- Contracts: `{score_summary.get('contract_n')}`",
            f"- Families: `{score_summary.get('families')}`",
            f"- Family Brier summary: `{family_summary}`",
            f"- Mean model-call Brier: `{fmt(score_summary.get('mean_model_brier'))}`",
            f"- Four-family panel Brier: `{fmt(score_summary.get('model_panel_mean_p_brier'))}`",
            f"- Market Brier: `{fmt(score_summary.get('mean_market_brier'))}`",
            f"- Panel-minus-market Brier: `{fmt(score_summary.get('model_panel_mean_p_minus_market_brier'))}`",
            f"- Panel-vs-market paired p: `{fmt((score_summary.get('paired_permutation_model_panel_vs_market') or {}).get('p_value'))}`",
        ]
    else:
        score_lines = ["- Summary: `None`"]
    lines = [
        "# Equal-Information Baseline Void Audit",
        "",
        f"- Verdict: `{report['verdict']['state']}`",
        f"- Stage-B LLM contracts: `{llm['n_contracts']}` over `{llm['n_calls']}` calls",
        f"- Ingested market/human baseline contracts: `{stage_c['n_contracts']}`",
        f"- Partial equal-information Polymarket contracts: `{equal_info['n_contracts']}`",
        f"- Matched Stage-B ∩ baseline contracts: `{coverage['matched_overlap_contracts']}`",
        f"- Baseline sources with matched rows: `{stage_c['sources']}`",
        "",
        "## Current Narrow Market Bar",
        "",
        f"- Pilot: `market_baseline_stage_c_v1`",
        f"- Contracts: `{stage_c['n_contracts']}`",
        f"- Outcome mix: `{stage_c['outcome_yes']}` YES / `{stage_c['outcome_no']}` NO",
        f"- Cutoff relation counts: `{stage_c['cutoff_relation_counts']}`",
        f"- Mean Brier: `{fmt(stage_c['mean_brier'])}`",
        f"- Rows with market Brier < 0.05: `{stage_c['brier_lt_0_05']}`",
        f"- Provenance: `{stage_c['provenance_counts']}`",
        "",
        "## Equal-Information Market Baselines",
        "",
        f"- Pilot: `equal_information_polymarket_baseline_v1`",
        f"- Contracts: `{equal_info['n_contracts']}`",
        f"- Outcome mix: `{equal_info.get('outcome_yes', 0)}` YES / `{equal_info.get('outcome_no', 0)}` NO",
        f"- Cutoff relation counts: `{equal_info.get('cutoff_relation_counts', {})}`",
        f"- Mean Brier: `{fmt(equal_info.get('mean_brier'))}`",
        f"- Provenance: `{equal_info.get('provenance_counts', {})}`",
        f"- Status: `{equal_info_status}`",
        "",
        "## Replacement Equal-Information Sample",
        "",
        f"- Verdict: `{replacement.get('verdict')}`",
        f"- Candidates: `{replacement.get('candidate_rows')}`",
        f"- Selected rows: `{replacement.get('selected_rows')}`",
        f"- Selected counts: `{replacement.get('selected_counts')}`",
        f"- Selection rule: `{replacement.get('selection_rule')}`",
        f"- Artifact: `{replacement.get('artifact')}`",
        f"- Next action: `{replacement_next_action}`",
        "",
        "## Replacement Model-vs-Market Score",
        "",
        f"- State: `{replacement_score.get('state')}`",
        *score_lines,
        f"- Artifact: `{replacement_score.get('artifact')}`",
        "",
        "## Coverage",
        "",
        f"- Stage-B contracts without market/human baseline: `{coverage['stage_b_without_market_baseline']}`",
        f"- By source: `{coverage['by_source']}`",
        "",
        "## External Target State",
        "",
        f"- Metaculus existing-target next step: `{ext['metaculus_existing_target_next_step']}`",
        f"- Remaining target by source: `{(ext['remaining_target_summary'] or {}).get('by_source')}`",
        f"- Metaculus access probe exists: `{ext['metaculus_probe_exists']}`",
        f"- Metaculus reprobe verdict: `{(ext.get('metaculus_reprobe') or {}).get('verdict')}`",
        f"- Metaculus reprobe fields: `{(ext.get('metaculus_reprobe') or {}).get('field_availability')}`",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
        "Promotion gate:",
        report["verdict"]["promotion_gate"],
    ]
    (out_dir / "equal_information_baseline_void_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--cec", type=Path, default=DEFAULT_CEC)
    parser.add_argument("--metaculus-probe", type=Path, default=DEFAULT_METACULUS_PROBE)
    parser.add_argument("--metaculus-reprobe", type=Path, default=DEFAULT_METACULUS_REPROBE)
    parser.add_argument("--replacement-sample", type=Path, default=DEFAULT_REPLACEMENT_SAMPLE)
    parser.add_argument("--replacement-score", type=Path, default=DEFAULT_REPLACEMENT_SCORE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)
    write_report(report, args.out_dir)
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
