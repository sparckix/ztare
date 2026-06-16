#!/usr/bin/env python3
"""Audit independent equal-information market/human source coverage.

No network, no model calls, no DB mutation. This audit answers the paper gate:
does the local evidence contain an equal-information market/human baseline from
at least two independent sources, or only the Polymarket replacement slice?
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = (
    PROGRAM
    / "truth_continuation_v1/workspace/independent_equal_information_source_audit_2026_06_15"
)
DEFAULT_METACULUS_REPROBE = (
    PROGRAM / "cutoff_validity_v1/workspace/metaculus_api_access_reprobe_2026_06_03.json"
)
DEFAULT_CEC = PROGRAM / "cutoff_validity_v1/workspace/cutoff_general_source_cec_packet.json"
DEFAULT_NON_POLY_PACKET = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/non_polymarket_equal_information_export_packet.json"
)
DEFAULT_NON_POLY_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15/manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json"
)


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
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def fetch_db(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    baseline_rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              COALESCE(c.source, '') AS source,
              COALESCE(c.source_corpus, '') AS source_corpus,
              COALESCE(ebo.platform, '') AS platform,
              ebo.pilot_id,
              ebo.baseline_kind,
              ebo.equal_information_flag,
              COUNT(*) AS rows,
              COUNT(DISTINCT ebo.contract_id) AS contracts,
              AVG(ebo.brier) AS mean_brier
            FROM external_baseline_observations ebo
            JOIN contracts c ON c.contract_id = ebo.contract_id
            WHERE ebo.schema_ok = 1
              AND c.y_known IS NOT NULL
            GROUP BY
              COALESCE(c.source, ''),
              COALESCE(c.source_corpus, ''),
              COALESCE(ebo.platform, ''),
              ebo.pilot_id,
              ebo.baseline_kind,
              ebo.equal_information_flag
            ORDER BY rows DESC
            """
        )
    ]
    contract_sources = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              COALESCE(source, '') AS source,
              COALESCE(source_corpus, '') AS source_corpus,
              COUNT(*) AS contracts,
              SUM(y_known IS NOT NULL) AS resolved,
              SUM(post_training_cutoff = 1) AS post_cutoff,
              SUM(post_training_cutoff = 0) AS pre_cutoff
            FROM contracts
            GROUP BY COALESCE(source, ''), COALESCE(source_corpus, '')
            ORDER BY resolved DESC, contracts DESC
            """
        )
    ]
    con.close()
    return {"baseline_rows": baseline_rows, "contract_sources": contract_sources}


def metaculus_summary(reprobe: dict[str, Any]) -> dict[str, Any]:
    field_availability = reprobe.get("field_availability") or {}
    detail_attempts = reprobe.get("detail_attempts") or []
    statuses = Counter(str(row.get("status")) for row in detail_attempts if isinstance(row, dict))
    ok_details = [row for row in detail_attempts if isinstance(row, dict) and row.get("ok")]
    return {
        "credential_present": bool(reprobe.get("credential_present")),
        "verdict": reprobe.get("verdict")
        or (
            "authenticated_but_required_fields_not_available_in_probe"
            if reprobe.get("credential_present")
            else "credential_missing_or_unproven"
        ),
        "field_availability": field_availability,
        "detail_status_counts": dict(statuses),
        "ok_detail_attempts": len(ok_details),
        "data_download_statuses": [
            attempt.get("status")
            for attempt in ((reprobe.get("data_download_probe") or {}).get("attempts") or [])
            if isinstance(attempt, dict)
        ],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    db_rows = fetch_db(args.db)
    metaculus = metaculus_summary(read_json(args.metaculus_reprobe))
    cec = read_json(args.cec)
    non_poly_packet = read_json(args.non_poly_packet)
    non_poly_summary = non_poly_packet.get("summary") or non_poly_packet
    non_poly_score = read_json(args.non_poly_score)
    non_poly_score_verdict = non_poly_score.get("verdict") or {}
    non_poly_selected = non_poly_score.get("selected_candidate") or {}
    baseline_rows = db_rows["baseline_rows"]
    equal_info_rows = [row for row in baseline_rows if int(row["equal_information_flag"] or 0) == 1]
    equal_info_sources = sorted({str(row["source"]) for row in equal_info_rows if row.get("source")})
    equal_info_contracts = sum(int(row["contracts"] or 0) for row in equal_info_rows)
    by_source = {}
    for row in baseline_rows:
        source = str(row.get("source") or "unknown")
        bucket = by_source.setdefault(source, {"contracts": 0, "equal_information_contracts": 0, "rows": []})
        bucket["contracts"] += int(row["contracts"] or 0)
        if int(row["equal_information_flag"] or 0) == 1:
            bucket["equal_information_contracts"] += int(row["contracts"] or 0)
        bucket["rows"].append(row)

    candidate_sources = [
        {
            "source": "polymarket",
            "status": "current_equal_information_source",
            "local_evidence": "Polymarket equal-information rows include the completed replacement slice.",
            "reason_not_second_source": "It is the already-used source; more Polymarket rows improve power but do not satisfy independent-source breadth.",
            "next_action": "Use for Polymarket-only negative control; do not use alone for broad human/market claim.",
            "kill_or_completion": "Independent-source gate remains open until a non-Polymarket source has matched equal-information rows.",
        },
        {
            "source": "metaculus",
            "status": "best_independent_source_but_access_blocked",
            "local_evidence": (
                "Credential present and post detail endpoint can authenticate, but sampled payloads lack non-null resolved Yes/No values and dated aggregate history; data download was rate-limited."
            ),
            "reason_not_second_source": "No local rows can yet supply both outcome and pre-resolution aggregate/history at the frozen time.",
            "next_action": "Obtain bot-benchmarking/data-download access or licensed export with resolved binary outcomes and timestamped aggregate history.",
            "kill_or_completion": "Complete if export gives >=24 matched equal-information rows; kill this path if export lacks outcome or dated aggregate/history fields.",
        },
        {
            "source": "manifold",
            "status": "current_equal_information_source_plus_old_stress_rows",
            "local_evidence": (
                "24 equal-information Manifold history rows are now DB-ingested under equal_information_manifold_history_baseline_v1. "
                "The older 51 Stage-C Manifold rows remain stress controls with equal_information_flag=0."
            ),
            "reason_not_second_source": "This source now satisfies the independent-source gate, but the joined model-vs-market score is post-hoc and not a broad LLM-superiority result.",
            "next_action": "Report the Manifold join as second-source comparison evidence; use a prospective or larger source-balanced join before any broad superiority claim.",
            "kill_or_completion": "Second-source acquisition is complete; broad claim remains scoped unless market/human bars are beaten under a predeclared, sufficiently powered comparison.",
        },
        {
            "source": "kalshi",
            "status": "local_contracts_too_small_no_baseline_rows",
            "local_evidence": "The DB has two resolved Kalshi contracts and no external_baseline_observations rows.",
            "reason_not_second_source": "No matched historical market baseline exists locally.",
            "next_action": "Use only if historical probability/orderbook receipts can be acquired at frozen pre-resolution timestamps.",
            "kill_or_completion": "Complete only with a sufficiently large, matched, timestamped Kalshi market packet.",
        },
        {
            "source": "fred_yfinance",
            "status": "official_data_not_market_or_human_baseline",
            "local_evidence": "FRED/yfinance rows support label-time and source-currency stress tests, not human/market forecasts.",
            "reason_not_second_source": "Official observed values are outcome data, not market/human baseline probabilities.",
            "next_action": "Keep as label-time validity evidence; do not count toward equal-information market/human breadth.",
            "kill_or_completion": "Never counts for the market/human gate unless paired with an independent human/market forecast source.",
        },
    ]

    independent_source_gate = len(equal_info_sources) >= 2
    broad_ready = bool(non_poly_score_verdict.get("broad_market_human_claim_ready"))
    if independent_source_gate and not broad_ready:
        state = "second_source_acquired_broad_claim_not_supported"
        current_evidence = (
            "Polymarket and Manifold now both have equal-information market baseline rows in the DB; "
            "the Manifold joined score is market-ahead/inconclusive and does not support LLM superiority."
        )
        next_action = (
            "Write the paper as a two-source market-baseline comparison with a negative or inconclusive "
            "LLM-vs-market boundary; use a prospective or larger source-balanced packet before any broader claim."
        )
        kill_boundary = (
            "If source-balanced joined evidence keeps market baselines ahead or remains underpowered, the paper "
            "must stay a measurement-validity contribution, not an LLM-beats-market paper."
        )
    elif independent_source_gate:
        state = "independent_source_gate_satisfied"
        current_evidence = "At least two equal-information market/human sources are present in the DB."
        next_action = "Check source-balanced power, predeclaration, and market-vs-model direction before broadening claims."
        kill_boundary = "Do not make a broad claim unless the source-balanced comparison beats market/human baselines."
    else:
        state = "independent_source_missing"
        current_evidence = "Only Polymarket currently has equal-information market baseline rows in the DB."
        next_action = (
            "Obtain a non-Polymarket packet with auditable timestamped history probabilities, or obtain "
            "Metaculus/Kalshi export data with the same resolved-outcome and pre-resolution probability fields."
        )
        kill_boundary = (
            "If no independent source can provide both a pre-resolution probability and an auditable resolved binary outcome, "
            "the paper must remain a source-validity contribution with a Polymarket-only negative market control."
        )
    return {
        "schema": "gp245-independent-equal-information-source-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "db": repo_relative(args.db),
            "metaculus_reprobe": repo_relative(args.metaculus_reprobe),
            "cec": repo_relative(args.cec),
            "non_polymarket_request_packet": repo_relative(args.non_poly_packet),
            "non_polymarket_score": repo_relative(args.non_poly_score),
        },
        "db_external_baselines": baseline_rows,
        "db_contract_sources_top": db_rows["contract_sources"][:25],
        "equal_information_summary": {
            "sources": equal_info_sources,
            "source_count": len(equal_info_sources),
            "contracts": equal_info_contracts,
            "rows": sum(int(row["rows"] or 0) for row in equal_info_rows),
            "by_source": by_source,
        },
        "metaculus_probe_summary": metaculus,
        "non_polymarket_request_packet": {
            "path": repo_relative(args.non_poly_packet),
            "state": non_poly_summary.get("state"),
            "request_rows": non_poly_summary.get("request_rows"),
            "target_rows": non_poly_summary.get("target_rows"),
            "by_source": non_poly_summary.get("by_source"),
            "outcome_counts": non_poly_summary.get("outcome_counts"),
            "acceptance_gate": non_poly_summary.get("acceptance_gate"),
            "non_claim": non_poly_summary.get("non_claim"),
            "next_action": non_poly_summary.get("next_action"),
        },
        "non_polymarket_score": {
            "path": repo_relative(args.non_poly_score),
            "state": non_poly_score_verdict.get("state"),
            "second_source_gate_satisfied": non_poly_score_verdict.get("second_source_gate_satisfied"),
            "broad_market_human_claim_ready": non_poly_score_verdict.get("broad_market_human_claim_ready"),
            "selected_pilot_id": non_poly_selected.get("pilot_id"),
            "selected_comparison_id": non_poly_selected.get("comparison_id"),
            "selected_condition": non_poly_selected.get("condition"),
            "selected_contracts": non_poly_selected.get("contracts"),
            "selected_families": non_poly_selected.get("families"),
            "market_brier": non_poly_selected.get("market_brier"),
            "model_panel_brier": non_poly_selected.get("model_panel_brier"),
            "panel_minus_market": non_poly_selected.get("panel_minus_market"),
            "paired": non_poly_selected.get("paired"),
            "interpretation": non_poly_score_verdict.get("interpretation"),
        },
        "cec_next_step": (cec.get("verdict") or {}).get("existing_target_next_step"),
        "candidate_sources": candidate_sources,
        "verdict": {
            "broad_market_human_claim_ready": broad_ready,
            "independent_source_gate_satisfied": independent_source_gate,
            "state": state,
            "current_evidence": current_evidence,
            "next_action": next_action,
            "kill_boundary": kill_boundary,
        },
    }


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_md(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    summary = report["equal_information_summary"]
    lines = [
        "# Independent Equal-Information Source Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- State: `{verdict['state']}`",
        f"- Broad market/human claim ready: `{verdict['broad_market_human_claim_ready']}`",
        f"- Equal-information sources: `{summary['sources']}`",
        f"- Equal-information contracts: `{summary['contracts']}`",
        f"- Current evidence: {verdict['current_evidence']}",
        f"- Next action: {verdict['next_action']}",
        f"- Kill boundary: {verdict['kill_boundary']}",
        "",
        "## DB External Baselines",
        "",
        "| source | corpus | platform | pilot | equal info | contracts | mean Brier |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in report["db_external_baselines"]:
        lines.append(
            "| {source} | {corpus} | {platform} | {pilot} | {eq} | {contracts} | {brier} |".format(
                source=row.get("source") or "unknown",
                corpus=row.get("source_corpus") or "",
                platform=row.get("platform") or "",
                pilot=row.get("pilot_id") or "",
                eq=row.get("equal_information_flag"),
                contracts=row.get("contracts"),
                brier=fmt(row.get("mean_brier")),
            )
        )
    lines.extend(
        [
            "",
            "## Candidate Source Status",
            "",
            "| source | status | why not enough now | next action |",
            "|---|---|---|---|",
        ]
    )
    for row in report["candidate_sources"]:
        lines.append(
            "| {source} | `{status}` | {reason} | {next_action} |".format(
                source=row["source"],
                status=row["status"],
                reason=row["reason_not_second_source"],
                next_action=row["next_action"],
            )
        )
    metaculus = report["metaculus_probe_summary"]
    packet = report["non_polymarket_request_packet"]
    score = report["non_polymarket_score"]
    lines.extend(
        [
            "",
            "## Metaculus Access Probe",
            "",
            f"- Credential present: `{metaculus['credential_present']}`",
            f"- Verdict: `{metaculus['verdict']}`",
            f"- Field availability: `{metaculus['field_availability']}`",
            f"- Detail status counts: `{metaculus['detail_status_counts']}`",
            f"- Data-download statuses: `{metaculus['data_download_statuses']}`",
            "",
            "## Non-Polymarket Request Packet",
            "",
            f"- Path: `{packet['path']}`",
            f"- State: `{packet['state']}`",
            f"- Request rows: `{packet['request_rows']}` / target `{packet['target_rows']}`",
            f"- By source: `{packet['by_source']}`",
            f"- Outcome counts: `{packet['outcome_counts']}`",
            f"- Acceptance gate: {packet['acceptance_gate']}",
            f"- Non-claim: {packet['non_claim']}",
            f"- Next action: {packet['next_action']}",
            "",
            "## Non-Polymarket Score",
            "",
            f"- Path: `{score['path']}`",
            f"- State: `{score['state']}`",
            f"- Second-source gate satisfied: `{score['second_source_gate_satisfied']}`",
            f"- Broad market/human claim ready: `{score['broad_market_human_claim_ready']}`",
            f"- Selected pilot: `{score['selected_pilot_id']}`",
            f"- Selected comparison: `{score['selected_comparison_id']}`",
            f"- Selected condition: `{score['selected_condition']}`",
            f"- Selected contracts: `{score['selected_contracts']}`",
            f"- Selected families: `{score['selected_families']}`",
            f"- Market Brier: `{fmt(score['market_brier'])}`",
            f"- Model panel Brier: `{fmt(score['model_panel_brier'])}`",
            f"- Panel-minus-market Brier: `{fmt(score['panel_minus_market'])}`",
            f"- Paired test: `{score['paired']}`",
            f"- Interpretation: {score['interpretation']}",
            "",
            "## Interpretation",
            "",
            "The broad comparison needs independent matched evidence units. More LLM calls on the existing Polymarket packet cannot create an independent source. The Manifold fill supplies a second source, but its joined score is market-ahead and inconclusive, so the paper should report a bounded two-source market comparison rather than an LLM superiority claim.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--metaculus-reprobe", type=Path, default=DEFAULT_METACULUS_REPROBE)
    parser.add_argument("--cec", type=Path, default=DEFAULT_CEC)
    parser.add_argument("--non-poly-packet", type=Path, default=DEFAULT_NON_POLY_PACKET)
    parser.add_argument("--non-poly-score", type=Path, default=DEFAULT_NON_POLY_SCORE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "independent_equal_information_source_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "independent_equal_information_source_audit.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
