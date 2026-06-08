#!/usr/bin/env python3
"""Build the external-bar acquisition manifest for F47 production validation.

No model calls. No network. No DB mutation.

F47 translated probabilities cannot be promoted as a production point-forecast
policy until they are compared against external market/human bars. The existing
DB overlap is too small, so this tool materializes the exact missing rows and
the source-specific acquisition path.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_SOURCE_KEY = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_answer_key.json"
DEFAULT_TOURNAMENT_KEY = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_answer_key.json"
DEFAULT_OUT_JSON = WORKSPACE / "f47_external_bar_manifest_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_external_bar_manifest_2026_06_03.md"
DEFAULT_MANIFOLD_INPUT = WORKSPACE / "f47_external_bar_manifold_missing_2026_06_03.jsonl"
DEFAULT_POLYMARKET_INPUT = WORKSPACE / "f47_external_bar_polymarket_missing_2026_06_03.jsonl"
MARKET_PILOT = "market_baseline_stage_c_v1"


def load_key_contracts(path: Path, packet: str) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in data.get("answer_key", []):
        if not isinstance(row, dict):
            continue
        for side in ("a", "b"):
            cid = str(row[f"contract_id_{side}"])
            slot = out.setdefault(
                cid,
                {
                    "contract_id": cid,
                    "source": str(row.get("source") or ""),
                    "packets": set(),
                    "pair_ids": [],
                    "y_known": int(row[f"y_{side}"]),
                },
            )
            slot["packets"].add(packet)
            slot["pair_ids"].append(str(row.get("pair_id") or ""))
    return out


def merge_contracts(*items: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        for cid, row in item.items():
            slot = merged.setdefault(
                cid,
                {
                    "contract_id": cid,
                    "source": row["source"],
                    "packets": set(),
                    "pair_ids": [],
                    "y_known": row["y_known"],
                },
            )
            if slot["source"] != row["source"]:
                raise SystemExit(f"source mismatch for {cid}")
            if int(slot["y_known"]) != int(row["y_known"]):
                raise SystemExit(f"outcome mismatch for {cid}")
            slot["packets"].update(row["packets"])
            slot["pair_ids"].extend(row["pair_ids"])
    return merged


def parse_resolve_date(horizon: Any) -> str | None:
    text = str(horizon or "")
    if text.startswith("resolved-"):
        return text.removeprefix("resolved-")
    return None


def load_contract_metadata(db: Path, contract_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = con.execute(
        f"""
        SELECT contract_id, question, source, source_corpus, horizon,
               external_market_open, resolution_source_url, y_known, raw_json
        FROM contracts
        WHERE contract_id IN ({placeholders})
        """,
        tuple(sorted(contract_ids)),
    ).fetchall()
    con.close()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw: dict[str, Any] = {}
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except json.JSONDecodeError:
            raw = {}
        source_url = row["resolution_source_url"] or raw.get("polymarket_url")
        if not source_url:
            artifacts = raw.get("artifact_paths")
            if isinstance(artifacts, list) and artifacts:
                source_url = artifacts[0]
        out[str(row["contract_id"])] = {
            "contract_id": str(row["contract_id"]),
            "question": row["question"],
            "source": row["source"],
            "source_corpus": row["source_corpus"],
            "horizon": row["horizon"],
            "resolve_date": parse_resolve_date(row["horizon"]),
            "external_market_open": row["external_market_open"],
            "source_url": source_url,
            "y_known": row["y_known"],
            "raw": raw,
        }
    return out


def load_existing_market(db: Path) -> dict[str, dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT contract_id, p_success, brier, raw_json
        FROM pilot_calls
        WHERE pilot_id = ?
          AND schema_ok = 1
        """,
        (MARKET_PILOT,),
    ).fetchall()
    con.close()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw: dict[str, Any] = {}
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except json.JSONDecodeError:
            raw = {}
        out[str(row["contract_id"])] = {
            "p_success": row["p_success"],
            "brier": row["brier"],
            "raw": raw,
        }
    return out


def acquisition_path(source: str, meta: dict[str, Any], has_market: bool) -> str:
    if has_market:
        return "already_joined"
    if source == "manifold":
        if meta.get("source_url") and meta.get("resolve_date"):
            return "manifold_public_probability_acquire"
        return "manifold_missing_url_or_resolve_date"
    if source == "polymarket":
        raw = meta.get("raw") or {}
        if raw.get("freeze_datetime_value") is not None:
            return "polymarket_freeze_value_present_not_ingested_as_market_bar"
        if meta.get("source_url"):
            return "polymarket_historical_price_acquire"
        return "polymarket_missing_url"
    return "no_market_bar_expected_for_source"


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    source_contracts = load_key_contracts(args.source_key, "source_balanced")
    tournament_contracts = load_key_contracts(args.tournament_key, "translation_tournament")
    contracts = merge_contracts(source_contracts, tournament_contracts)
    meta = load_contract_metadata(args.db, set(contracts))
    existing_market = load_existing_market(args.db)
    rows: list[dict[str, Any]] = []
    for cid, row in sorted(contracts.items()):
        m = meta.get(cid, {})
        has_market = cid in existing_market
        source = str(row["source"])
        path = acquisition_path(source, m, has_market)
        packets = sorted(row["packets"])
        rows.append(
            {
                "schema": "f47-external-bar-manifest-row-v1",
                "contract_id": cid,
                "question": m.get("question"),
                "source": source,
                "source_corpus": m.get("source_corpus"),
                "packets": packets,
                "pair_ids": sorted(set(row["pair_ids"])),
                "y_known": int(row["y_known"]),
                "resolve_date": m.get("resolve_date"),
                "horizon": m.get("horizon"),
                "source_url": m.get("source_url"),
                "external_market_open": m.get("external_market_open"),
                "has_existing_market_bar": has_market,
                "existing_market_p": (existing_market.get(cid) or {}).get("p_success"),
                "acquisition_path": path,
            }
        )
    manifold_rows = [
        {
            "contract_id": row["contract_id"],
            "question": row["question"],
            "source": "manifold",
            "source_url": row["source_url"],
            "resolve_date": row["resolve_date"],
            "cutoff_relation": "f47_external_bar",
            "source_question_id": row["contract_id"],
            "packets": row["packets"],
        }
        for row in rows
        if row["acquisition_path"] == "manifold_public_probability_acquire"
    ]
    polymarket_rows = [
        {
            "contract_id": row["contract_id"],
            "question": row["question"],
            "source": "polymarket",
            "source_url": row["source_url"],
            "resolve_date": row["resolve_date"],
            "cutoff_relation": "f47_external_bar",
            "source_question_id": row["contract_id"],
            "packets": row["packets"],
        }
        for row in rows
        if row["acquisition_path"] in {"polymarket_historical_price_acquire", "polymarket_freeze_value_present_not_ingested_as_market_bar"}
    ]
    report = {
        "schema": "f47-external-bar-manifest-v1",
        "date": "2026-06-03",
        "market_pilot": MARKET_PILOT,
        "unique_contracts": len(rows),
        "source_counts": dict(sorted(Counter(row["source"] for row in rows).items())),
        "packet_counts": dict(sorted(Counter("+".join(row["packets"]) for row in rows).items())),
        "existing_market_overlap": sum(1 for row in rows if row["has_existing_market_bar"]),
        "existing_market_overlap_by_source": dict(
            sorted(Counter(row["source"] for row in rows if row["has_existing_market_bar"]).items())
        ),
        "acquisition_path_counts": dict(sorted(Counter(row["acquisition_path"] for row in rows).items())),
        "manifold_acquisition_rows": len(manifold_rows),
        "polymarket_acquisition_rows": len(polymarket_rows),
        "verdict": (
            "f47_external_bar_missing_broad_baseline"
            if sum(1 for row in rows if row["has_existing_market_bar"]) < 20
            else "f47_external_bar_overlap_ready"
        ),
        "interpretation": (
            "F47 production validation is not blocked by more model calls. It is blocked by "
            "external-bar acquisition: current DB overlap is too small to answer whether "
            "translated F47 beats market/human bars or adds to them."
        ),
        "rows": rows,
    }
    return report, manifold_rows, polymarket_rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# F47 External-Bar Manifest",
        "",
        report["interpretation"],
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Unique F47 contracts: `{report['unique_contracts']}`",
        f"- Existing market overlap: `{report['existing_market_overlap']}`",
        f"- Source counts: `{report['source_counts']}`",
        f"- Acquisition path counts: `{report['acquisition_path_counts']}`",
        f"- Manifold acquisition rows: `{report['manifold_acquisition_rows']}`",
        f"- Polymarket acquisition rows: `{report['polymarket_acquisition_rows']}`",
        "",
        "## Missing External Bars",
        "",
        "| source | acquisition path | count |",
        "|---|---|---:|",
    ]
    counts = Counter((row["source"], row["acquisition_path"]) for row in report["rows"])
    for (source, path), count in sorted(counts.items()):
        lines.append(f"| {source} | `{path}` | {count} |")
    lines.extend(
        [
            "",
            "Smallest valid next step: acquire the Manifold public probability rows and the Polymarket historical-price rows, ingest them as a scoped F47 external-bar pilot, then compare translated F47 against raw, F100, market-alone, and market+F47 blends. Do not spend more F47 model calls before this join unless the packet is explicitly prospective.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-key", type=Path, default=DEFAULT_SOURCE_KEY)
    parser.add_argument("--tournament-key", type=Path, default=DEFAULT_TOURNAMENT_KEY)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--manifold-input", type=Path, default=DEFAULT_MANIFOLD_INPUT)
    parser.add_argument("--polymarket-input", type=Path, default=DEFAULT_POLYMARKET_INPUT)
    args = parser.parse_args()
    report, manifold_rows, polymarket_rows = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    write_jsonl(args.manifold_input, manifold_rows)
    write_jsonl(args.polymarket_input, polymarket_rows)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "unique_contracts": report["unique_contracts"],
                "existing_market_overlap": report["existing_market_overlap"],
                "acquisition_path_counts": report["acquisition_path_counts"],
                "manifold_input": str(args.manifold_input.relative_to(REPO)),
                "polymarket_input": str(args.polymarket_input.relative_to(REPO)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
