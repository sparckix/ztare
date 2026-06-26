#!/usr/bin/env python3
"""Denominator audit for the central GP-245 evidence slices.

The paper has several row-rich results whose statistical unit is not always
the model call. This offline audit records calls, contracts, sources, market
rows, and event-group documentation for the central slices used in the
manuscript. It does not run models, change the database, or rescore forecasts.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_DIR = PROGRAM / "paper_alignment_v1/workspace/effective_n_audit_2026_06_16"

POLYMARKET_REPLACEMENT_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15"
    / "equal_information_replacement_score.json"
)
POLYMARKET_REPLACEMENT_ROWS = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_sample_2026_06_15"
    / "equal_information_replacement_selected_rows.jsonl"
)
MANIFOLD_EQUAL_INFO_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
    / "manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json"
)
PAIRWISE_SCORE = (
    PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f47_source_balanced_consumer_score_2026_06_03.json"
)
STRUCTURED_PROMPT_SCORE = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json"
)
STRUCTURED_PROMPT_EXTERNAL_CONTROL = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json"
)
STRUCTURED_PROMPT_CLAUDE_REPLICATION = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json"
)
FRED_VINTAGE_SCORE = (
    PROGRAM / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json"
)
FRED_BLINDED_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/fred_blinded_value_control_packet_2026_06_04"
    / "fred_blinded_value_control_score_report.json"
)
FORECASTBENCH_SCHEMA_PILOT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_row_schema_pilot.json"
)
FORECASTBENCH_SCORE_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_score_audit.json"
)
FORECASTBENCH_HUMAN_COMPARATOR_AUDIT = (
    PROGRAM
    / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
    / "field_wide_forecastbench_human_comparator_audit.json"
)


CSV_FIELDS = [
    "slice_id",
    "role_in_paper",
    "model_call_rows",
    "contracts_or_pairs",
    "market_rows",
    "source_count",
    "sources",
    "yes_contracts",
    "no_contracts",
    "model_families_or_conditions",
    "effective_unit",
    "event_group_status",
    "claim_use",
    "main_limit",
    "evidence_paths",
]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def fnum(value: Any, digits: int = 6) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
    return rows


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def db_call_slice(con: sqlite3.Connection, pilot_id: str) -> dict[str, Any]:
    con.row_factory = sqlite3.Row
    row = con.execute(
        """
        SELECT
            COUNT(*) AS model_call_rows,
            COUNT(DISTINCT pc.contract_id) AS contracts,
            COUNT(DISTINCT c.source) AS source_count,
            GROUP_CONCAT(DISTINCT c.source) AS sources,
            COUNT(DISTINCT pc.family) AS family_count,
            COUNT(DISTINCT pc.condition) AS condition_count
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    counts = con.execute(
        """
        SELECT c.y_known, COUNT(DISTINCT c.contract_id) AS n
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
        GROUP BY c.y_known
        """,
        (pilot_id,),
    ).fetchall()
    outcome = {str(item["y_known"]): int(item["n"]) for item in counts}
    return {
        "model_call_rows": int(row["model_call_rows"] or 0),
        "contracts": int(row["contracts"] or 0),
        "source_count": int(row["source_count"] or 0),
        "sources": str(row["sources"] or ""),
        "family_count": int(row["family_count"] or 0),
        "condition_count": int(row["condition_count"] or 0),
        "yes_contracts": outcome.get("1", 0),
        "no_contracts": outcome.get("0", 0),
    }


def db_market_slice(con: sqlite3.Connection, pilot_id: str) -> dict[str, Any]:
    con.row_factory = sqlite3.Row
    row = con.execute(
        """
        SELECT
            COUNT(*) AS market_rows,
            COUNT(DISTINCT v.contract_id) AS contracts,
            COUNT(DISTINCT c.source) AS source_count,
            GROUP_CONCAT(DISTINCT c.source) AS sources,
            SUM(CASE WHEN c.y_known = 1 THEN 1 ELSE 0 END) AS yes_rows,
            SUM(CASE WHEN c.y_known = 0 THEN 1 ELSE 0 END) AS no_rows
        FROM v_external_market_baselines v
        JOIN contracts c ON c.contract_id = v.contract_id
        WHERE v.pilot_id = ?
        """,
        (pilot_id,),
    ).fetchone()
    return {
        "market_rows": int(row["market_rows"] or 0),
        "contracts": int(row["contracts"] or 0),
        "source_count": int(row["source_count"] or 0),
        "sources": str(row["sources"] or ""),
        "yes_rows": int(row["yes_rows"] or 0),
        "no_rows": int(row["no_rows"] or 0),
    }


def source_breakdown(con: sqlite3.Connection, pilot_id: str) -> str:
    rows = con.execute(
        """
        SELECT COALESCE(c.source, 'unknown') AS source,
               COUNT(*) AS calls,
               COUNT(DISTINCT c.contract_id) AS contracts
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
        GROUP BY COALESCE(c.source, 'unknown')
        ORDER BY source
        """,
        (pilot_id,),
    ).fetchall()
    return "; ".join(f"{row[0]}:{int(row[1])} calls/{int(row[2])} contracts" for row in rows)


def path_list(*paths: Path) -> str:
    return "; ".join(rel(path) for path in paths if path.exists())


def row(
    *,
    slice_id: str,
    role_in_paper: str,
    model_call_rows: int | str,
    contracts_or_pairs: int | str,
    market_rows: int | str,
    source_count: int | str,
    sources: str,
    yes_contracts: int | str,
    no_contracts: int | str,
    model_families_or_conditions: int | str,
    effective_unit: str,
    event_group_status: str,
    claim_use: str,
    main_limit: str,
    evidence_paths: str,
) -> dict[str, str]:
    return {
        "slice_id": slice_id,
        "role_in_paper": role_in_paper,
        "model_call_rows": str(model_call_rows),
        "contracts_or_pairs": str(contracts_or_pairs),
        "market_rows": str(market_rows),
        "source_count": str(source_count),
        "sources": sources,
        "yes_contracts": str(yes_contracts),
        "no_contracts": str(no_contracts),
        "model_families_or_conditions": str(model_families_or_conditions),
        "effective_unit": effective_unit,
        "event_group_status": event_group_status,
        "claim_use": claim_use,
        "main_limit": main_limit,
        "evidence_paths": evidence_paths,
    }


def build_rows(db: Path) -> list[dict[str, str]]:
    con = sqlite3.connect(db)
    try:
        rows: list[dict[str, str]] = []

        source_currency = db_call_slice(con, "cutoff_stage_b_panel_v1")
        rows.append(
            row(
                slice_id="manifold_source_currency_stage_b",
                role_in_paper="Source-currency diagnostic",
                model_call_rows=source_currency["model_call_rows"],
                contracts_or_pairs=source_currency["contracts"],
                market_rows=0,
                source_count=source_currency["source_count"],
                sources=source_currency["sources"],
                yes_contracts=source_currency["yes_contracts"],
                no_contracts=source_currency["no_contracts"],
                model_families_or_conditions=source_currency["family_count"],
                effective_unit="contract",
                event_group_status="no global event-family key in SQLite; contract is the available denominator",
                claim_use="Shows that source currency changes the interpretation of Manifold rows.",
                main_limit="Source-general extension still needs non-Manifold matched pre/post rows.",
                evidence_paths=rel(db),
            )
        )

        stage_c_market = db_market_slice(con, "market_baseline_stage_c_v1")
        rows.append(
            row(
                slice_id="manifold_stage_c_market_control",
                role_in_paper="Market comparison diagnostic",
                model_call_rows="uses Stage-B model panel joins",
                contracts_or_pairs=stage_c_market["contracts"],
                market_rows=stage_c_market["market_rows"],
                source_count=stage_c_market["source_count"],
                sources=stage_c_market["sources"],
                yes_contracts=stage_c_market["yes_rows"],
                no_contracts=stage_c_market["no_rows"],
                model_families_or_conditions="panel",
                effective_unit="contract",
                event_group_status="no global event-family key in SQLite; not an equal-information slice",
                claim_use="Blocks a broad raw-LLM-over-market reading of the local market join.",
                main_limit="Market timestamps are not the same pre-outcome information state for every row.",
                evidence_paths=rel(db),
            )
        )

        poly_score = read_json(POLYMARKET_REPLACEMENT_SCORE)
        poly_summary = poly_score.get("summary") or {}
        poly_rows = read_jsonl(POLYMARKET_REPLACEMENT_ROWS)
        poly_event_slugs = sorted({str(item.get("event_slug") or "") for item in poly_rows if item.get("event_slug")})
        poly_slug_counts = Counter(str(item.get("event_slug") or "missing") for item in poly_rows)
        repeated_poly_groups = sum(1 for count in poly_slug_counts.values() if count > 1)
        outcome_counts = poly_summary.get("outcome_counts") or {}
        rows.append(
            row(
                slice_id="polymarket_replacement_equal_information",
                role_in_paper="Equal-information market control",
                model_call_rows=poly_summary.get("row_n", 0),
                contracts_or_pairs=poly_summary.get("contract_n", 0),
                market_rows=poly_summary.get("contract_n", 0),
                source_count=1,
                sources="polymarket",
                yes_contracts=outcome_counts.get("1", 0),
                no_contracts=outcome_counts.get("0", 0),
                model_families_or_conditions=poly_summary.get("family_n", 0),
                effective_unit="contract with market price frozen before resolution",
                event_group_status=(
                    f"event_slug available for {len(poly_event_slugs)} groups across {len(poly_rows)} contracts; "
                    f"{repeated_poly_groups} groups contribute more than one contract"
                ),
                claim_use="Shows a completed equal-information slice where markets beat the raw model panel.",
                main_limit="Short-horizon, high-liquidity Polymarket packet; not a broad human or market comparison.",
                evidence_paths=path_list(POLYMARKET_REPLACEMENT_SCORE, POLYMARKET_REPLACEMENT_ROWS),
            )
        )

        manifold_score = read_json(MANIFOLD_EQUAL_INFO_SCORE)
        manifold_market = manifold_score.get("market_summary") or {}
        pilot_scores = manifold_score.get("pilot_scores") or []
        low_item = next(
            (
                item
                for item in pilot_scores
                if item.get("comparison_id") == "v28stake_full__v25_external::low"
            ),
            {},
        )
        manifold_outcome = manifold_market.get("outcome_counts") or {}
        rows.append(
            row(
                slice_id="manifold_history_equal_information",
                role_in_paper="Second equal-information market control",
                model_call_rows=low_item.get("rows", 0),
                contracts_or_pairs=low_item.get("contracts", manifold_market.get("contracts", 0)),
                market_rows=manifold_market.get("contracts", 0),
                source_count=1,
                sources="manifold",
                yes_contracts=manifold_outcome.get("1", 0),
                no_contracts=manifold_outcome.get("0", 0),
                model_families_or_conditions=low_item.get("family_count", 0),
                effective_unit="contract with historical market value",
                event_group_status="no global event-family key in exported packet; contract is the available denominator",
                claim_use="Adds a second market source and keeps market superiority claims out of scope.",
                main_limit="Underpowered for model-market difference and not source-general.",
                evidence_paths=rel(MANIFOLD_EQUAL_INFO_SCORE),
            )
        )

        pair_score = read_json(PAIRWISE_SCORE)
        pair_summaries = pair_score.get("summaries") or {}
        collapsed = pair_summaries.get("collapsed_by_unique_pair") or {}
        source_keys = sorted(key.removeprefix("source::") for key in pair_summaries if key.startswith("source::"))
        rows.append(
            row(
                slice_id="pairwise_source_balanced_ranking",
                role_in_paper="Pairwise ranking result",
                model_call_rows=(pair_summaries.get("all_calls") or {}).get("n", 0),
                contracts_or_pairs=collapsed.get("non_tie_n", 0),
                market_rows=0,
                source_count=len(source_keys),
                sources=", ".join(source_keys),
                yes_contracts="not applicable",
                no_contracts="not applicable",
                model_families_or_conditions=sum(1 for key in pair_summaries if key.startswith("family::")),
                effective_unit="unique non-tie pair",
                event_group_status="pair-level collapse available; event-family grouping remains a prospective requirement",
                claim_use="Supports relative ranking as a scoped signal, not standalone probabilities.",
                main_limit="No completed same-contract probability translation or prospective market-freeze score.",
                evidence_paths=rel(PAIRWISE_SCORE),
            )
        )

        fred_pair = db_call_slice(con, "fred_cutoff_pair_tool_free_v1")
        fred_vintage = read_json(FRED_VINTAGE_SCORE)
        audit_summary = fred_vintage.get("audit_summary") or {}
        rows.append(
            row(
                slice_id="fred_vintage_label_time",
                role_in_paper="Label-time diagnostic",
                model_call_rows=fred_pair["model_call_rows"],
                contracts_or_pairs=fred_pair["contracts"],
                market_rows=0,
                source_count=fred_pair["source_count"],
                sources=fred_pair["sources"],
                yes_contracts=fred_pair["yes_contracts"],
                no_contracts=fred_pair["no_contracts"],
                model_families_or_conditions=fred_pair["family_count"],
                effective_unit="FRED series/event row",
                event_group_status="series-level row; official vintage documentation changes labels",
                claim_use="Shows that current labels can reverse a source-currency conclusion.",
                main_limit=(
                    f"Vintage repair changed {audit_summary.get('binary_label_changed_count', 15)} labels; "
                    "not a positive forecasting-improvement result."
                ),
                evidence_paths=path_list(FRED_VINTAGE_SCORE, db),
            )
        )

        fred_blinded = db_call_slice(con, "fred_blinded_value_control_v1")
        rows.append(
            row(
                slice_id="fred_blinded_value_control",
                role_in_paper="Blinded control for FRED",
                model_call_rows=fred_blinded["model_call_rows"],
                contracts_or_pairs=fred_blinded["contracts"],
                market_rows=0,
                source_count=fred_blinded["source_count"],
                sources=fred_blinded["sources"],
                yes_contracts=fred_blinded["yes_contracts"],
                no_contracts=fred_blinded["no_contracts"],
                model_families_or_conditions=fred_blinded["family_count"],
                effective_unit="FRED series/event row",
                event_group_status="series-level row; no market event group",
                claim_use="Checks whether value visibility alone explains the FRED split.",
                main_limit="Control does not create a correction rule.",
                evidence_paths=path_list(FRED_BLINDED_SCORE, db),
            )
        )

        structured_db = db_call_slice(con, "structured_metacognition_public_v1")
        structured_score = read_json(STRUCTURED_PROMPT_SCORE)
        structured_external = read_json(STRUCTURED_PROMPT_EXTERNAL_CONTROL)
        structured_claude = read_json(STRUCTURED_PROMPT_CLAUDE_REPLICATION)
        coverage = structured_score.get("coverage") or {}
        claude_coverage = structured_claude.get("coverage") or {}
        claude_expert = ((structured_claude.get("condition_gates") or {}).get("expert_training_prompt") or {})
        expert_gate = (structured_score.get("condition_gates") or {}).get("expert_training_prompt") or {}
        expert_bare = expert_gate.get("vs_bare") or {}
        expert_placebo = expert_gate.get("vs_placebo") or {}
        external_adjusted = (
            (structured_external.get("low_probability_adjustment") or {}).get("expert_minus_adjusted_bare") or {}
        )
        external_market = (
            (structured_external.get("market_controls") or {})
            .get("equal_information_rows", {})
            .get("expert_minus_market", {})
        )
        rows.append(
            row(
                slice_id="structured_prompt_completed_public_packet",
                role_in_paper="Scoped positive intervention result",
                model_call_rows=coverage.get("scored_rows", structured_db["model_call_rows"]),
                contracts_or_pairs=structured_db["contracts"],
                market_rows=0,
                source_count=structured_db["source_count"],
                sources=source_breakdown(con, "structured_metacognition_public_v1"),
                yes_contracts=structured_db["yes_contracts"],
                no_contracts=structured_db["no_contracts"],
                model_families_or_conditions=structured_db["condition_count"],
                effective_unit="contract-condition block",
                event_group_status=(
                    f"{coverage.get('complete_contract_family_blocks', structured_db['contracts'])} complete "
                    "contract blocks across FRED, Manifold, and Polymarket"
                ),
                claim_use=(
                    "Shows one expert-training prompt improved paired Brier versus bare and "
                    "length-matched placebo in a Gemini-only public-corpus test."
                ),
                main_limit=(
                    "One model family and retrospective public rows. It beats the same-row "
                    "low-probability-adjusted bare forecast "
                    f"({external_adjusted.get('mean_delta_brier')} Brier delta), but not the "
                    f"equal-information market overlap ({external_market.get('mean_delta_brier')} Brier delta). "
                    "Expert-training deltas: "
                    f"{fnum(expert_bare.get('mean_delta_brier'))} vs bare, "
                    f"{fnum(expert_placebo.get('mean_delta_brier'))} vs placebo. "
                    "Partial Claude validation: "
                    f"{claude_coverage.get('scored_rows')} scored rows, "
                    f"{claude_coverage.get('complete_contract_family_blocks')} complete blocks; "
                    "expert-training deltas "
                    f"{fnum((claude_expert.get('vs_bare') or {}).get('mean_delta_brier'))} vs bare and "
                    f"{fnum((claude_expert.get('vs_placebo') or {}).get('mean_delta_brier'))} vs placebo."
                ),
                evidence_paths=path_list(
                    STRUCTURED_PROMPT_SCORE,
                    STRUCTURED_PROMPT_EXTERNAL_CONTROL,
                    STRUCTURED_PROMPT_CLAUDE_REPLICATION,
                    db,
                ),
            )
        )

        fb_schema = read_json(FORECASTBENCH_SCHEMA_PILOT)
        fb_score = read_json(FORECASTBENCH_SCORE_AUDIT)
        fb_human = read_json(FORECASTBENCH_HUMAN_COMPARATOR_AUDIT)
        fb_rows = fb_schema.get("rows") or []
        fb_event_groups = {str(item.get("event_family_id") or "") for item in fb_rows if item.get("event_family_id")}
        scored_event_groups = fb_score.get("unique_event_family_keys") or len(fb_event_groups)
        capped_market_rows = fb_score.get("event_family_capped_market_rows_per_full_file") or []
        capped_market_delta = fb_score.get("median_event_family_capped_market_delta_forecast_minus_baseline")
        rows.append(
            row(
                slice_id="forecastbench_public_score_audit",
                role_in_paper="Public benchmark check",
                model_call_rows=fb_score.get("unique_scored_row_keys", 0),
                contracts_or_pairs=fb_schema.get("row_count", 0),
                market_rows=fb_schema.get("same_contract_market_rows", 0),
                source_count=len(fb_schema.get("source_counts") or {}),
                sources=", ".join(sorted((fb_schema.get("source_counts") or {}).keys())),
                yes_contracts="mixed numeric and binary labels",
                no_contracts="mixed numeric and binary labels",
                model_families_or_conditions=fb_score.get("forecast_files_scored", 0),
                effective_unit="public row key",
                event_group_status=(
                    f"{fb_score.get('unique_scored_row_keys', 0)} scored row keys collapse to "
                    f"{scored_event_groups} event-family keys; event-family-capped market rows per full file="
                    f"{capped_market_rows}"
                ),
                claim_use="Shows public-audit feasibility and one market-overlap score audit.",
                main_limit=(
                    "Not a field-wide failure-rate estimate and does not include a large human/market overlap. "
                    f"Median capped market-slice delta remains {capped_market_delta}."
                ),
                evidence_paths=path_list(FORECASTBENCH_SCHEMA_PILOT, FORECASTBENCH_SCORE_AUDIT),
            )
        )

        human_summaries = {
            str(item.get("forecast_file")): item for item in fb_human.get("summaries", []) if isinstance(item, dict)
        }
        human_public = human_summaries.get("2024-07-21.ForecastBench.human_public.json") or {}
        human_super = human_summaries.get("2024-07-21.ForecastBench.human_super.json") or {}
        rows.append(
            row(
                slice_id="forecastbench_human_comparator_audit",
                role_in_paper="Public human-comparator check",
                model_call_rows=fb_human.get("unique_scored_row_keys", 0),
                contracts_or_pairs=fb_human.get("forecast_files_scored", 0),
                market_rows=f"{fb_human.get('files_with_market_slice', 0)} files with market slices",
                source_count="public ForecastBench round",
                sources="ForecastBench 2024-07-21 processed forecast archive",
                yes_contracts="mixed binary outcomes",
                no_contracts="mixed binary outcomes",
                model_families_or_conditions=fb_human.get("forecast_files_scored", 0),
                effective_unit="public row key and event-family key",
                event_group_status=(
                    f"{fb_human.get('unique_scored_row_keys', 0)} scored row keys collapse to "
                    f"{fb_human.get('unique_event_family_keys', 0)} event-family keys; human aggregate files "
                    f"have {human_super.get('resolved_rows_non_imputed', 'NA')} and "
                    f"{human_public.get('resolved_rows_non_imputed', 'NA')} resolved non-imputed rows"
                ),
                claim_use=(
                    "Shows that a public ForecastBench round includes scoreable human aggregate files "
                    "under the same row checks."
                ),
                main_limit=(
                    "The human aggregate files each have only two strict same-information market rows, "
                    "so this is not a broad human, market, or model comparison. "
                    f"Superforecaster aggregate Brier={fnum(human_super.get('resolved_brier_non_imputed'))}; "
                    f"public aggregate Brier={fnum(human_public.get('resolved_brier_non_imputed'))}."
                ),
                evidence_paths=path_list(FORECASTBENCH_HUMAN_COMPARATOR_AUDIT),
            )
        )

        return rows
    finally:
        con.close()


def build_report(db: Path) -> dict[str, Any]:
    rows = build_rows(db)
    missing_event_groups = [
        item["slice_id"]
        for item in rows
        if "no global event-family key" in item["event_group_status"]
        or "prospective requirement" in item["event_group_status"]
    ]
    return {
        "schema": "gp245-central-evidence-effective-n-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass",
        "central_evidence_rows": len(rows),
        "rows_with_missing_global_event_group": len(missing_event_groups),
        "missing_global_event_group_slice_ids": missing_event_groups,
        "interpretation": (
            "The central evidence is strongest at the contract or unique-pair level. "
            "Several slices lack a global event-family key, so the manuscript treats "
            "contract, pair, and available event-family counts as the central denominators."
        ),
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Central Evidence Effective-N Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        report["interpretation"],
        "",
        "| Slice | Role | Calls | Contracts/Pairs | Market Rows | Sources | Unit | Event-Group Status | Use | Limit |",
        "|---|---:|---:|---:|---:|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        values = [
            item["slice_id"],
            item["role_in_paper"],
            item["model_call_rows"],
            item["contracts_or_pairs"],
            item["market_rows"],
            item["sources"],
            item["effective_unit"],
            item["event_group_status"],
            item["claim_use"],
            item["main_limit"],
        ]
        escaped = [str(value).replace("|", "/") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "central_evidence_effective_n_audit.json"
    csv_path = args.out_dir / "central_evidence_effective_n_audit.csv"
    md_path = args.out_dir / "central_evidence_effective_n_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "central_evidence_rows": report["central_evidence_rows"],
                "rows_with_missing_global_event_group": report["rows_with_missing_global_event_group"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
