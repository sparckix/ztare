#!/usr/bin/env python3
"""Score the narrow Stage-C Manifold market baseline against the Law 3 panel.

This is not a broad human/crowd comparison. The available local baseline is a
pre-outcome market-implied probability, usually seven days before resolution,
for the subset of the cutoff-validity panel where Stage-C joined a probability.
The tool can ingest those rows into the canonical forecast DB and writes a
report comparing the market bar with same-contract LLM panel calls.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_JOIN_REPORT = WORKSPACE / "cutoff_stage_c_base_rate_join_report.json"
DEFAULT_OUT = PROGRAM / "truth_continuation_v1/workspace"
PILOT_ID = "market_baseline_stage_c_v1"
CONDITION = "stage_c_preoutcome_market_probability"
PRIMITIVE = "market_preoutcome_baseline"


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return obj


def probability(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= p <= 1.0:
        return p
    return None


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y not in (0, 1):
        return None
    return (p - int(y)) ** 2


def joined_market_rows(join_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in join_report.get("contract_base_rates", []):
        if not isinstance(row, dict):
            continue
        p = probability(row.get("base_rate_value"))
        if row.get("fetch_status") != "joined" or p is None:
            continue
        rows.append({**row, "base_rate_value": p})
    return rows


def load_contract_outcomes(db: Path, contract_ids: set[str]) -> dict[str, int | None]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in contract_ids)
    rows = con.execute(
        f"SELECT contract_id, y_known FROM contracts WHERE contract_id IN ({placeholders})",
        tuple(contract_ids),
    ).fetchall()
    con.close()
    return {str(cid): int(y) if y in (0, 1) else None for cid, y in rows}


def ensure_pilot_run(con: sqlite3.Connection, source_path: Path, *, dry_run: bool) -> None:
    if con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (PILOT_ID,)).fetchone():
        return
    if dry_run:
        return
    con.execute(
        """
        INSERT INTO pilot_runs
            (pilot_id, pilot_name, primitive, corpus, source_jsonl_path, fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            PILOT_ID,
            "GP-245 Stage-C pre-outcome Manifold market baseline",
            PRIMITIVE,
            "law3_cutoff_stage_c_joined_market_probabilities",
            repo_relative(source_path),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def refresh_pilot_counts(con: sqlite3.Connection) -> None:
    row = con.execute(
        """
        SELECT COUNT(*) AS n_calls, SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (PILOT_ID,),
    ).fetchone()
    con.execute(
        "UPDATE pilot_runs SET n_calls = ?, n_schema_ok = ? WHERE pilot_id = ?",
        (int(row["n_calls"] or 0), int(row["n_schema_ok"] or 0), PILOT_ID),
    )


def ingest_market_rows(rows: list[dict[str, Any]], db: Path, source_path: Path, *, dry_run: bool) -> dict[str, Any]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    ensure_pilot_run(con, source_path, dry_run=dry_run)
    y_by_contract = load_contract_outcomes(db, {str(row["contract_id"]) for row in rows})
    existing = {
        str(row["contract_id"])
        for row in con.execute(
            "SELECT contract_id FROM pilot_calls WHERE pilot_id = ? AND condition = ?",
            (PILOT_ID, CONDITION),
        )
    }
    insert_sql = """
        INSERT INTO pilot_calls
            (pilot_id, contract_id, agent_id, family, condition, primitive,
             primitive_base, phase, role, pair_id, p_success, brier,
             schema_ok, parsed_json, fired_at, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    inserted = 0
    skipped = 0
    for row in rows:
        cid = str(row["contract_id"])
        if cid in existing:
            skipped += 1
            continue
        p = probability(row.get("base_rate_value"))
        y = y_by_contract.get(cid)
        parsed = {
            "baseline_kind": "pre_outcome_market_probability",
            "not_equal_information_human_baseline": True,
            "cutoff_relation": row.get("cutoff_relation"),
            "base_rate_band": row.get("base_rate_band"),
            "base_rate_provenance": row.get("base_rate_provenance"),
            "prior_timestamp": row.get("prior_timestamp"),
            "target_days_before_resolution": row.get("target_days_before_resolution"),
            "selection_method": row.get("selection_method"),
            "source_question_id": row.get("source_question_id"),
            "source_url": row.get("source_url"),
        }
        payload = (
            PILOT_ID,
            cid,
            "manifold_market",
            "manifold_market",
            CONDITION,
            PRIMITIVE,
            "market_baseline",
            "baseline",
            "preoutcome_market_bar",
            cid,
            p,
            brier(p, y),
            1 if p is not None and y in (0, 1) else 0,
            json.dumps(parsed, sort_keys=True),
            datetime.now(timezone.utc).isoformat(),
            json.dumps(row, sort_keys=True),
        )
        if not dry_run:
            con.execute(insert_sql, payload)
        existing.add(cid)
        inserted += 1
    if not dry_run:
        refresh_pilot_counts(con)
        con.commit()
    db_counts = con.execute(
        """
        SELECT COUNT(*) AS n_calls, SUM(CASE WHEN schema_ok THEN 1 ELSE 0 END) AS n_schema_ok
        FROM pilot_calls
        WHERE pilot_id = ?
        """,
        (PILOT_ID,),
    ).fetchone()
    con.close()
    return {
        "pilot_id": PILOT_ID,
        "rows_available": len(rows),
        "inserted": inserted,
        "skipped_existing": skipped,
        "dry_run": dry_run,
        "db_calls": int(db_counts["n_calls"] or 0),
        "db_schema_ok": int(db_counts["n_schema_ok"] or 0),
    }


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def refresh_external_baseline_table(db: Path, *, dry_run: bool) -> dict[str, Any]:
    """Materialize typed external-baseline observations from baseline pilot rows."""
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS external_baseline_observations (
            baseline_id TEXT PRIMARY KEY,
            pilot_id TEXT NOT NULL,
            contract_id TEXT NOT NULL,
            baseline_kind TEXT NOT NULL,
            platform TEXT,
            p_success REAL NOT NULL,
            observed_at TEXT,
            days_before_resolution REAL,
            equal_information_flag INTEGER NOT NULL,
            source_currency_receipt TEXT NOT NULL,
            provenance_url TEXT,
            brier REAL,
            schema_ok INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
        )
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_external_baseline_contract_kind
        ON external_baseline_observations(contract_id, baseline_kind, platform)
        """
    )
    rows = con.execute(
        """
        SELECT pc.*, c.source, c.source_corpus, c.post_training_cutoff, c.y_known
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
          AND pc.condition = ?
          AND pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
        ORDER BY pc.contract_id
        """,
        (PILOT_ID, CONDITION),
    ).fetchall()
    generated_at = datetime.now(timezone.utc).isoformat()
    out_rows = []
    for row in rows:
        parsed = parse_json(row["parsed_json"])
        raw = parse_json(row["raw_json"])
        relation = parsed.get("cutoff_relation") or raw.get("cutoff_relation")
        receipt = {
            "cutoff_relation": relation,
            "stored_post_training_cutoff": row["post_training_cutoff"],
            "source": row["source"],
            "source_corpus": row["source_corpus"],
            "baseline_scope": "narrow_stage_c_preoutcome_market_probability",
            "not_equal_information_human_baseline": bool(parsed.get("not_equal_information_human_baseline")),
        }
        baseline_id = f"{PILOT_ID}:{row['contract_id']}:preoutcome_market"
        out_rows.append(
            (
                baseline_id,
                row["pilot_id"],
                row["contract_id"],
                parsed.get("baseline_kind") or "pre_outcome_market_probability",
                row["family"] or row["agent_id"] or "unknown",
                float(row["p_success"]),
                parsed.get("prior_timestamp"),
                float(parsed["target_days_before_resolution"])
                if parsed.get("target_days_before_resolution") is not None
                else None,
                0 if parsed.get("not_equal_information_human_baseline") else 1,
                json.dumps(receipt, sort_keys=True),
                parsed.get("source_url") or raw.get("source_url"),
                row["brier"],
                int(row["schema_ok"] or 0),
                generated_at,
                json.dumps({"parsed_json": parsed, "raw_json": raw}, sort_keys=True),
            )
        )
    if not dry_run:
        con.execute("DELETE FROM external_baseline_observations WHERE pilot_id = ?", (PILOT_ID,))
        con.executemany(
            """
            INSERT INTO external_baseline_observations (
                baseline_id, pilot_id, contract_id, baseline_kind, platform,
                p_success, observed_at, days_before_resolution,
                equal_information_flag, source_currency_receipt,
                provenance_url, brier, schema_ok, generated_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            out_rows,
        )
        con.execute("DROP VIEW IF EXISTS v_external_market_baselines")
        con.execute(
            """
            CREATE VIEW v_external_market_baselines AS
            SELECT *
            FROM external_baseline_observations
            WHERE baseline_kind = 'pre_outcome_market_probability'
              AND schema_ok = 1
            """
        )
        con.commit()
    count = con.execute(
        "SELECT COUNT(*) FROM external_baseline_observations WHERE pilot_id = ?",
        (PILOT_ID,),
    ).fetchone()[0] if not dry_run else len(out_rows)
    con.close()
    return {
        "table": "external_baseline_observations",
        "view": "v_external_market_baselines",
        "rows_available": len(rows),
        "rows_materialized": int(count),
        "dry_run": dry_run,
    }


def load_llm_calls(db: Path, contract_ids: set[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT contract_id, family, condition, p_success, brier, parsed_json
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
    return rows


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 6) if values else None


def summarize(rows: list[dict[str, Any]], db: Path) -> dict[str, Any]:
    y_by_contract = load_contract_outcomes(db, {str(row["contract_id"]) for row in rows})
    market_by_contract = {
        str(row["contract_id"]): {
            "p": probability(row.get("base_rate_value")),
            "brier": brier(probability(row.get("base_rate_value")), y_by_contract.get(str(row["contract_id"]))),
            "relation": row.get("cutoff_relation"),
            "provenance": row.get("base_rate_provenance"),
        }
        for row in rows
    }
    market_briers = [float(v["brier"]) for v in market_by_contract.values() if v["brier"] is not None]
    llm_calls = load_llm_calls(db, set(market_by_contract))
    family_briers: dict[str, list[float]] = defaultdict(list)
    family_deltas: dict[str, list[float]] = defaultdict(list)
    relation_market_briers: dict[str, list[float]] = defaultdict(list)
    relation_llm_briers: dict[str, list[float]] = defaultdict(list)
    panel_by_contract: dict[str, list[float]] = defaultdict(list)
    for call in llm_calls:
        cid = str(call["contract_id"])
        m = market_by_contract.get(cid)
        if not m or m["brier"] is None:
            continue
        b = float(call["brier"])
        family = str(call["family"])
        family_briers[family].append(b)
        family_deltas[family].append(float(m["brier"]) - b)
        relation = str(m.get("relation") or "unknown")
        relation_llm_briers[relation].append(b)
        panel_by_contract[cid].append(b)
    panel_deltas = []
    for cid, values in panel_by_contract.items():
        m = market_by_contract[cid]
        if m["brier"] is None or not values:
            continue
        panel_deltas.append(float(m["brier"]) - statistics.mean(values))
    for m in market_by_contract.values():
        if m["brier"] is not None:
            relation_market_briers[str(m.get("relation") or "unknown")].append(float(m["brier"]))
    return {
        "schema": "gp245-market-baseline-stage-c-audit-v1",
        "pilot_id": PILOT_ID,
        "baseline_scope": "narrow_stage_c_preoutcome_market_probability_not_equal_information_human_baseline",
        "contracts_joined": len(rows),
        "contracts_scoreable": len(market_briers),
        "llm_calls_on_joined_contracts": len(llm_calls),
        "provenance_counts": dict(Counter(str(row.get("base_rate_provenance")) for row in rows)),
        "relation_counts": dict(Counter(str(row.get("cutoff_relation")) for row in rows)),
        "market_mean_brier": mean(market_briers),
        "llm_family_mean_brier": {family: mean(vals) for family, vals in sorted(family_briers.items())},
        "market_minus_family_mean_brier": {
            family: mean(vals) for family, vals in sorted(family_deltas.items())
        },
        "market_minus_panel_mean_brier": mean(panel_deltas),
        "relation_mean_brier": {
            relation: {
                "market": mean(relation_market_briers.get(relation, [])),
                "llm_calls": mean(relation_llm_briers.get(relation, [])),
                "market_n_contracts": len(relation_market_briers.get(relation, [])),
                "llm_n_calls": len(relation_llm_briers.get(relation, [])),
            }
            for relation in sorted(set(relation_market_briers) | set(relation_llm_briers))
        },
        "interpretation": (
            "Negative market_minus values mean the market baseline has lower Brier than the LLM comparator. "
            "This is a pre-outcome market bar, usually seven days before resolution, and must not be described "
            "as an equal-information human/crowd comparison."
        ),
    }


def render_md(report: dict[str, Any], ingest: dict[str, Any], external_baselines: dict[str, Any]) -> str:
    lines = [
        "# Stage-C Market Baseline Audit",
        "",
        f"- Pilot ID: `{report['pilot_id']}`",
        f"- Scope: `{report['baseline_scope']}`",
        f"- Joined contracts: {report['contracts_joined']}",
        f"- Scoreable contracts: {report['contracts_scoreable']}",
        f"- LLM calls on joined contracts: {report['llm_calls_on_joined_contracts']}",
        f"- DB ingest: `{ingest}`",
        f"- External baseline table refresh: `{external_baselines}`",
        "",
        "## Brier Summary",
        "",
        f"- Market mean Brier: `{report['market_mean_brier']}`",
        f"- LLM family mean Brier: `{report['llm_family_mean_brier']}`",
        f"- Market minus family mean Brier: `{report['market_minus_family_mean_brier']}`",
        f"- Market minus panel mean Brier: `{report['market_minus_panel_mean_brier']}`",
        "",
        "## Relation Breakdown",
        "",
        "```json",
        json.dumps(report["relation_mean_brier"], indent=2, sort_keys=True),
        "```",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--join-report", type=Path, default=DEFAULT_JOIN_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not (args.dry_run or args.commit):
        raise SystemExit("Specify --dry-run or --commit.")
    join_report = load_json(args.join_report)
    rows = joined_market_rows(join_report)
    ingest = ingest_market_rows(rows, args.db, args.join_report, dry_run=not args.commit)
    external_baselines = refresh_external_baseline_table(args.db, dry_run=not args.commit)
    report = summarize(rows, args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "market_baseline_stage_c_report.json").write_text(
        json.dumps(
            {"ingest": ingest, "external_baselines": external_baselines, "report": report},
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "market_baseline_stage_c_report.md").write_text(
        render_md(report, ingest, external_baselines),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"ingest": ingest, "external_baselines": external_baselines, "report": report},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
