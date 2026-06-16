#!/usr/bin/env python3
"""Emit a non-Polymarket equal-information market-baseline export packet.

No network, no model calls, no DB mutation.

The current broad market/human gate needs a source independent of Polymarket.
This packet uses locally resolved Manifold/Kalshi contracts as acquisition
targets and asks for the missing market-history fields needed to materialize a
same-information baseline. It deliberately excludes contracts that already have
Stage-C market-baseline rows, because those rows are not reclassifiable.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
)


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def parse_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def parse_date_from_text(value: Any) -> date | None:
    text = str(value or "")
    match = re.search(r"20\d{2}-\d{2}-\d{2}", text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(0))
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def url_slug(url: str | None) -> str | None:
    if not url:
        return None
    return str(url).rstrip("/").split("/")[-1] or None


def load_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              c.contract_id,
              c.question,
              c.source,
              c.source_corpus,
              c.y_known,
              c.post_training_cutoff,
              c.horizon,
              c.resolution_source_url,
              c.y_known_provenance,
              c.raw_json,
              c.created_at,
              CASE
                WHEN EXISTS (
                  SELECT 1
                  FROM external_baseline_observations ebo
                  WHERE ebo.contract_id = c.contract_id
                ) THEN 1 ELSE 0
              END AS has_any_external_baseline
            FROM contracts c
            WHERE c.source IN ('manifold', 'kalshi')
              AND c.y_known IN (0, 1)
              AND c.post_training_cutoff = 1
            ORDER BY
              CASE WHEN c.source = 'manifold' THEN 0 ELSE 1 END,
              c.source_corpus,
              c.contract_id
            """
        )
    ]
    con.close()
    return rows


def question_length_bucket(question: str | None) -> str:
    n = len(str(question or ""))
    if n < 80:
        return "<80"
    if n < 160:
        return "80-159"
    if n < 280:
        return "160-279"
    return "280+"


def row_status(row: dict[str, Any], *, freeze_days: int) -> tuple[str, dict[str, Any]]:
    raw = parse_json(row.get("raw_json"))
    resolution_date = parse_date_from_text(row.get("horizon")) or parse_date_from_text(
        raw.get("horizon")
    )
    open_dt = parse_datetime(raw.get("external_market_open"))
    if resolution_date is None:
        return "missing_resolution_date", {"raw": raw}
    target_freeze = resolution_date - timedelta(days=freeze_days)
    target_freeze_dt = datetime.combine(target_freeze, datetime.min.time(), tzinfo=timezone.utc)
    if open_dt is None:
        return "missing_market_open", {"raw": raw, "resolution_date": resolution_date}
    if open_dt.astimezone(timezone.utc) > target_freeze_dt:
        return "market_not_open_by_target_freeze", {
            "raw": raw,
            "resolution_date": resolution_date,
            "target_freeze_date": target_freeze,
            "target_freeze_datetime": target_freeze_dt,
            "market_open": open_dt,
        }
    if int(row.get("has_any_external_baseline") or 0):
        return "already_has_external_baseline_excluded", {
            "raw": raw,
            "resolution_date": resolution_date,
            "target_freeze_date": target_freeze,
            "target_freeze_datetime": target_freeze_dt,
            "market_open": open_dt,
        }
    return "eligible_for_export_request", {
        "raw": raw,
        "resolution_date": resolution_date,
        "target_freeze_date": target_freeze,
        "target_freeze_datetime": target_freeze_dt,
        "market_open": open_dt,
    }


def build_request(row: dict[str, Any], meta: dict[str, Any], *, freeze_days: int) -> dict[str, Any]:
    raw = meta["raw"]
    source = str(row["source"])
    resolution_date = meta["resolution_date"]
    target_freeze = meta["target_freeze_date"]
    market_url = row.get("resolution_source_url") or (raw.get("artifact_paths") or [None])[0]
    required_fields = {
        "history_probability": "market-implied YES/probability at or before target_freeze_date_utc 00:00:00 UTC",
        "history_timestamp": "Unix timestamp or ISO timestamp of selected probability",
        "history_source": "API/export/provider/source filename",
        "outcome_mapping": "fields proving that history_probability corresponds to the YES/success outcome",
        "resolved_binary_outcome": "auditable resolved binary outcome matching contracts.y_known",
    }
    if source == "manifold":
        required_fields.update(
            {
                "manifold_contract_id_or_slug": "Manifold contract id or slug used for history lookup",
                "probability_field": "probability/probAfter/probabilityBefore equivalent",
            }
        )
    elif source == "kalshi":
        required_fields.update(
            {
                "kalshi_ticker": "Kalshi market ticker used for history lookup",
                "yes_bid_ask_or_mid": "YES price, midpoint, or documented probability field",
            }
        )
    return {
        "schema": "gp245-non-polymarket-equal-information-export-row-v1",
        "contract_id": row.get("contract_id"),
        "source": source,
        "source_corpus": row.get("source_corpus"),
        "question": row.get("question"),
        "market_url": market_url,
        "market_slug": url_slug(market_url),
        "resolve_date": resolution_date.isoformat(),
        "target_freeze_date_utc": target_freeze.isoformat(),
        "target_freeze_datetime_utc": meta["target_freeze_datetime"].isoformat(),
        "target_freeze_timestamp_rule": (
            "Use the nearest available market probability at or before "
            f"{meta['target_freeze_datetime'].isoformat()}, matching this packet's "
            f"{freeze_days}-day pre-resolution freeze rule."
        ),
        "market_open_datetime": raw.get("external_market_open"),
        "y_known": int(row["y_known"]),
        "y_known_provenance": row.get("y_known_provenance"),
        "post_training_cutoff": int(row["post_training_cutoff"]),
        "question_length_bucket": question_length_bucket(row.get("question")),
        "required_fields": required_fields,
        "eligibility_rule": (
            "Eligible only if history_probability is in [0,1], timestamp is at "
            "or before target freeze, the YES/success mapping is auditable, and "
            "the resolved binary outcome agrees with the canonical DB row."
        ),
        "model_prompt_rule": (
            "Model calls for this packet must not include market prices, history "
            "probabilities, trader counts, or the selected baseline probability."
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = load_rows(args.db)
    statuses: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for row in source_rows:
        status, meta = row_status(row, freeze_days=args.freeze_days_before_resolution)
        statuses[status] += 1
        candidate = {
            "contract_id": row.get("contract_id"),
            "source": row.get("source"),
            "source_corpus": row.get("source_corpus"),
            "question": row.get("question"),
            "y_known": row.get("y_known"),
            "status": status,
            "has_any_external_baseline": bool(row.get("has_any_external_baseline")),
        }
        if "resolution_date" in meta:
            candidate["resolve_date"] = meta["resolution_date"].isoformat()
        if "target_freeze_date" in meta:
            candidate["target_freeze_date_utc"] = meta["target_freeze_date"].isoformat()
        if "target_freeze_datetime" in meta:
            candidate["target_freeze_datetime_utc"] = meta["target_freeze_datetime"].isoformat()
        if "market_open" in meta:
            candidate["market_open_datetime"] = meta["market_open"].isoformat()
        candidates.append(candidate)
        if status == "eligible_for_export_request" and len(requests) < args.target_rows:
            requests.append(build_request(row, meta, freeze_days=args.freeze_days_before_resolution))

    by_source = Counter(str(row["source"]) for row in requests)
    outcome_counts = Counter(str(row["y_known"]) for row in requests)
    verdict_state = (
        "request_packet_ready_for_export_fill"
        if len(requests) >= args.target_rows
        else "insufficient_local_non_polymarket_request_rows"
    )
    return {
        "schema": "gp245-non-polymarket-equal-information-export-packet-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "db": repo_relative(args.db),
            "target_rows": args.target_rows,
            "freeze_days_before_resolution": args.freeze_days_before_resolution,
            "excluded_existing_external_baselines": True,
            "sources": ["manifold", "kalshi"],
        },
        "candidate_status_counts": dict(statuses),
        "candidate_rows": candidates,
        "request_rows": requests,
        "summary": {
            "state": verdict_state,
            "request_rows": len(requests),
            "target_rows": args.target_rows,
            "by_source": dict(by_source),
            "outcome_counts": dict(outcome_counts),
            "acceptance_gate": (
                "The packet becomes an equal-information source only after filled "
                "results provide auditable pre-resolution market probabilities and "
                "resolved binary outcomes for these same contracts."
            ),
            "non_claim": (
                "This manifest is an acquisition request, not evidence that models "
                "beat or lose to the non-Polymarket market source."
            ),
            "next_action": (
                "Fill the request rows with Manifold/Kalshi market-history export data, "
                "then ingest as equal_information_flag=1 only if every row passes "
                "the eligibility rule."
            ),
        },
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "non_polymarket_equal_information_export_packet.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "non_polymarket_equal_information_export_request_rows.jsonl").open(
        "w", encoding="utf-8"
    ) as fh:
        for row in report["request_rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "non_polymarket_equal_information_export_candidate_rows.jsonl").open(
        "w", encoding="utf-8"
    ) as fh:
        for row in report["candidate_rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    summary = report["summary"]
    lines = [
        "# Non-Polymarket Equal-Information Export Packet",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- State: `{summary['state']}`",
        f"- Request rows: `{summary['request_rows']}` / target `{summary['target_rows']}`",
        f"- By source: `{summary['by_source']}`",
        f"- Outcome counts: `{summary['outcome_counts']}`",
        f"- Candidate status counts: `{report['candidate_status_counts']}`",
        f"- Acceptance gate: {summary['acceptance_gate']}",
        f"- Non-claim: {summary['non_claim']}",
        f"- Next action: {summary['next_action']}",
        "",
        "## Required Result Fields",
        "",
        "- `contract_id`",
        "- `history_probability`",
        "- `history_timestamp`",
        "- `history_source`",
        "- `outcome_mapping`",
        "- `resolved_binary_outcome`",
        "- source-specific market identifier fields from each request row",
        "",
        "## Request Rows",
        "",
        "| contract | source | resolve date | freeze date | y | market |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report["request_rows"]:
        lines.append(
            "| {contract_id} | {source} | {resolve_date} | {freeze} | {y} | {url} |".format(
                contract_id=row["contract_id"],
                source=row["source"],
                resolve_date=row["resolve_date"],
                freeze=row["target_freeze_date_utc"],
                y=row["y_known"],
                url=row.get("market_url") or "",
            )
        )
    (out_dir / "non_polymarket_equal_information_export_packet.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--target-rows", type=int, default=24)
    parser.add_argument("--freeze-days-before-resolution", type=int, default=2)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
