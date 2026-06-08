#!/usr/bin/env python3
"""Build a manual provenance packet for Polymarket Law 3 candidates.

No DB mutation. This is the review surface between public-CLOB acquisition and
any contract-row ingest: it preserves the event-family cap receipts, exposes
the structured Gamma source gap, and records exactly what a reviewer must clear.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_MANIFEST = WORKSPACE / "cutoff_polymarket_event_family_cap_selected.jsonl"
DEFAULT_OUT = WORKSPACE


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (REPO / path).resolve()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def parse_jsonish_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def resolution_text(raw_market: dict[str, Any]) -> str:
    texts: list[str] = []
    for value in (raw_market.get("resolutionSource"), raw_market.get("description")):
        if isinstance(value, str) and value.strip():
            texts.append(" ".join(value.split()))
    for event in raw_market.get("events") or []:
        if not isinstance(event, dict):
            continue
        for value in (event.get("resolutionSource"), event.get("description")):
            if isinstance(value, str) and value.strip():
                normalized = " ".join(value.split())
                if normalized not in texts:
                    texts.append(normalized)
    return "\n\n".join(texts)


def final_yes_probability(row: dict[str, Any]) -> float | None:
    raw_market = row.get("raw_market") or {}
    prices = parse_jsonish_list(raw_market.get("outcomePrices"))
    outcomes = parse_jsonish_list(raw_market.get("outcomes")) or row.get("outcomes") or []
    if not prices or not outcomes:
        return None
    for outcome, price in zip(outcomes, prices, strict=False):
        if str(outcome).strip().lower() == "yes":
            try:
                return float(price)
            except Exception:
                return None
    return None


def row_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    raw_market = row.get("raw_market") or {}
    text = resolution_text(raw_market)
    yes_prob = final_yes_probability(row)
    if not str(raw_market.get("resolutionSource") or "").strip():
        flags.append("gamma_resolution_source_field_blank")
    if not text:
        flags.append("missing_resolution_criteria_text")
    if yes_prob is None:
        flags.append("missing_final_yes_outcome_price")
    elif row.get("y_known") not in (0, 1):
        flags.append("invalid_y_known")
    elif int(row["y_known"]) != int(round(yes_prob)):
        flags.append("y_known_disagrees_with_final_outcome_price")
    if str(raw_market.get("umaResolutionStatus") or "").lower() != "resolved":
        flags.append("uma_not_resolved")
    if row.get("history_status") != "history_nearest_at_or_before_target":
        flags.append("unexpected_history_status")
    if row.get("cutoff_relation") != "pre_cutoff":
        flags.append("not_pre_cutoff")
    if not row.get("url"):
        flags.append("missing_polymarket_url")
    return flags


def review_row(row: dict[str, Any], event_counts: Counter[str]) -> dict[str, Any]:
    raw_market = row.get("raw_market") or {}
    event_slug = str(row.get("event_slug") or row.get("slug") or "")
    final_yes = final_yes_probability(row)
    flags = row_flags(row)
    if event_counts[event_slug] > 1:
        flags.append("sibling_event_family_duplicate")
    return {
        "schema": "gp245-polymarket-manual-provenance-row-v1",
        "contract_id": row.get("contract_id"),
        "external_id": row.get("external_id"),
        "question": row.get("question"),
        "polymarket_url": row.get("url"),
        "event_slug": event_slug,
        "event_title": row.get("event_title"),
        "resolution_date": row.get("resolution_date"),
        "closed_time": row.get("closed_time"),
        "freeze_datetime": row.get("freeze_datetime"),
        "freeze_datetime_value": row.get("freeze_datetime_value"),
        "freeze_value_band": row.get("freeze_value_band"),
        "freeze_history_timestamp": row.get("freeze_history_timestamp"),
        "history_status": row.get("history_status"),
        "y_known": row.get("y_known"),
        "final_yes_probability": final_yes,
        "outcome_prices_raw": raw_market.get("outcomePrices"),
        "outcomes_raw": raw_market.get("outcomes"),
        "uma_resolution_status": raw_market.get("umaResolutionStatus"),
        "uma_end_date": raw_market.get("umaEndDate"),
        "gamma_resolution_source_field": raw_market.get("resolutionSource"),
        "resolution_criteria_text": resolution_text(raw_market),
        "source_currency_receipt": row.get("source_currency_receipt"),
        "flags": sorted(set(flags)),
        "manual_decision_required": True,
        "manual_decision_template": {
            "accept_for_db_ingest": None,
            "reviewer": "",
            "reviewed_at": "",
            "resolution_source_url": "",
            "resolution_source_note": "",
            "y_known_confirmed": None,
            "reject_reason": "",
        },
    }


def build_packet(manifest: Path) -> dict[str, Any]:
    rows = read_jsonl(manifest)
    event_counts = Counter(str(row.get("event_slug") or row.get("slug") or "") for row in rows)
    reviewed = [review_row(row, event_counts) for row in rows]
    flag_counts: Counter[str] = Counter(flag for row in reviewed for flag in row["flags"])
    by_cell = Counter(
        f"{row.get('freeze_value_band')} | {row.get('question_length_band')}"
        for row in rows
    )
    final_agree = sum(
        1
        for row in reviewed
        if row["final_yes_probability"] is not None
        and row["y_known"] in (0, 1)
        and int(row["y_known"]) == int(round(float(row["final_yes_probability"])))
    )
    return {
        "schema": "gp245-polymarket-manual-provenance-packet-v1",
        "manifest": repo_rel(manifest),
        "candidate_rows": len(rows),
        "unique_event_families": len(event_counts),
        "selected_by_cell": dict(sorted(by_cell.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
        "rows_with_final_outcome_price_matching_y_known": final_agree,
        "manual_review_rows": len(reviewed),
        "ready_for_db_ingest": False,
        "review_rule": (
            "A row can be accepted only after a human reviewer fills the manual "
            "decision template with an acceptable resolution source URL or note, "
            "confirms y_known, and leaves no unresolved critical provenance issue."
        ),
        "reviewed_candidates": reviewed,
    }


def render_md(packet: dict[str, Any]) -> str:
    lines = [
        "# Polymarket Manual Provenance Packet",
        "",
        f"- Schema: `{packet['schema']}`",
        f"- Candidate rows: {packet['candidate_rows']}",
        f"- Unique event families: {packet['unique_event_families']}",
        f"- Manual-review rows: {packet['manual_review_rows']}",
        f"- Final outcome price agrees with `y_known`: {packet['rows_with_final_outcome_price_matching_y_known']}",
        f"- Ready for DB ingest: `{packet['ready_for_db_ingest']}`",
        "",
        "## Cell Coverage",
        "",
        "```json",
        json.dumps(packet["selected_by_cell"], indent=2, sort_keys=True),
        "```",
        "",
        "## Flag Counts",
        "",
        "```json",
        json.dumps(packet["flag_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Review Rule",
        "",
        packet["review_rule"],
        "",
        "## Rows",
        "",
    ]
    for row in packet["reviewed_candidates"]:
        text = row["resolution_criteria_text"].replace("\n", " ")
        if len(text) > 420:
            text = text[:417].rstrip() + "..."
        lines.extend(
            [
                f"### {row['contract_id']}",
                "",
                f"- Question: {row['question']}",
                f"- URL: {row['polymarket_url']}",
                f"- Event: `{row['event_slug']}`",
                f"- Resolution date: `{row['resolution_date']}`",
                f"- Freeze: `{row['freeze_datetime']}` price `{row['freeze_datetime_value']}`",
                f"- Outcome: `y_known={row['y_known']}` final_yes_probability=`{row['final_yes_probability']}`",
                f"- UMA: `{row['uma_resolution_status']}` at `{row['uma_end_date']}`",
                f"- Flags: `{','.join(row['flags'])}`",
                f"- Resolution text: {text}",
                "- Manual decision: `accept_for_db_ingest=` `reviewer=` `reviewed_at=` `resolution_source_url=` `y_known_confirmed=`",
                "",
            ]
        )
    return "\n".join(lines)


def write_outputs(packet: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_polymarket_manual_provenance_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "cutoff_polymarket_manual_provenance_packet.md").write_text(
        render_md(packet),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    packet = build_packet(resolve_path(args.manifest))
    print(json.dumps(packet, indent=2, sort_keys=True))
    write_outputs(packet, resolve_path(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
