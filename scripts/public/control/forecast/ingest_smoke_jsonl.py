"""Ingest forecast-smoke JSONL ledgers into forecaster_calibration.db.

Closes the 5-file ingest gap surfaced by the 2026-05-29 DB migration audit
(`projects/.../forecaster_skill_calibration_v1/workspace/db_migration_audit_2026_05_29.md`).

The 5 jsonls deliberately break the `pilot_*_calls` filename convention because
they're labelled by smoke_id rather than pilot version. This script maps each
known filename → pilot_id, parses each row into the pilot_calls schema, and
upserts (no-duplicate via (pilot_id, contract_id, agent_id, primitive)).

Reads (5 files):
  novel_bias_smokes_n42_diversified_calls.jsonl → pilot_id v28_novel_bias_smokes_n42_diversified
  novel_bias_smokes_n30_calls.jsonl             → pilot_id v28_novel_bias_smokes_n30
  freq_inheritance_DI_panel_smoke_n15_calls.jsonl → pilot_id f104_freq_inheritance_DI_panel_n15
  freq_inheritance_smoke_n15_calls.jsonl        → pilot_id f104_freq_inheritance_n15
  pilot_v28timedecay_calls_full_corpusv25.jsonl → pilot_id v28timedecay_full_corpusv25

CLI:
  python3 scripts/public/control/forecast/ingest_smoke_jsonl.py --dry-run
  python3 scripts/public/control/forecast/ingest_smoke_jsonl.py --commit
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
WS = REPO / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"

FILE_TO_PILOT = {
    "novel_bias_smokes_n42_diversified_calls.jsonl": "v28_novel_bias_smokes_n42_diversified",
    "novel_bias_smokes_n30_calls.jsonl":             "v28_novel_bias_smokes_n30",
    "freq_inheritance_DI_panel_smoke_n15_calls.jsonl": "f104_freq_inheritance_DI_panel_n15",
    "freq_inheritance_smoke_n15_calls.jsonl":        "f104_freq_inheritance_n15",
    "pilot_v28timedecay_calls_full_corpusv25.jsonl": "v28timedecay_full_corpusv25",
}


def agent_to_family(agent: str) -> str:
    """Map agent_id → family stripping the version suffix."""
    if agent.startswith("claude"):    return "claude"
    if "codex_55" in agent:           return "codex_55"
    if "codex_54mini" in agent:       return "codex_54mini"
    if "codex_5large" in agent:       return "codex_5large"
    if agent.startswith("deepseek"):  return "deepseek"
    if agent.startswith("gemini"):    return "gemini"
    return agent


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y is None: return None
    return (p - y) ** 2


def ingest_file(con: sqlite3.Connection, path: Path, pilot_id: str,
                *, dry_run: bool) -> dict:
    if not path.exists():
        return {"file": path.name, "ok": False, "error": "not found"}
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    # y_known map (contracts table)
    y_map = dict(con.execute("SELECT contract_id, y_known FROM contracts"))
    # already-ingested (pilot_id, contract_id, agent_id, primitive) keys
    existing = set()
    for r in con.execute(
        "SELECT contract_id, agent_id, primitive FROM pilot_calls WHERE pilot_id = ?",
        (pilot_id,),
    ):
        existing.add(r)
    inserted = skipped = 0
    insert_sql = """
        INSERT INTO pilot_calls
            (pilot_id, contract_id, agent_id, family, condition, primitive,
             primitive_base, phase, role, pair_id, p_success, brier,
             schema_ok, parsed_json, fired_at, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    for r in rows:
        cid = r.get("contract_id")
        agent = r.get("agent_id")
        prim = r.get("smoke_id") or r.get("primitive")
        if not (cid and agent and prim): skipped += 1; continue
        if (cid, agent, prim) in existing:
            skipped += 1; continue
        parsed = r.get("parsed") if isinstance(r.get("parsed"), dict) else None
        p = (parsed or {}).get("p_success") if parsed else None
        try:
            p = float(p) if p is not None else None
        except (TypeError, ValueError):
            p = None
        y = y_map.get(cid)
        b = brier(p, y)
        schema_ok = 1 if r.get("schema_ok") else 0
        row = (
            pilot_id, cid, agent, agent_to_family(agent), None,
            prim, prim.split("_")[0] if prim else None, None, None, None,
            p, b, schema_ok,
            json.dumps(parsed) if parsed else None,
            r.get("fired_at"),
            json.dumps(r),
        )
        if not dry_run:
            con.execute(insert_sql, row)
        inserted += 1
    return {
        "file": path.name, "pilot_id": pilot_id, "rows_in_file": len(rows),
        "inserted": inserted, "skipped_already_in_db_or_invalid": skipped,
        "ok": True,
    }


def ensure_pilot_run(con: sqlite3.Connection, pilot_id: str, *, dry_run: bool,
                     source_jsonl: str | None = None) -> None:
    have = con.execute("SELECT 1 FROM pilot_runs WHERE pilot_id = ?", (pilot_id,)).fetchone()
    if have or dry_run: return
    con.execute(
        "INSERT INTO pilot_runs (pilot_id, pilot_name, source_jsonl_path, fired_at) VALUES (?,?,?,datetime('now'))",
        (pilot_id, f"smoke ingest 2026-05-29: {pilot_id}", source_jsonl),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.commit):
        print("specify --dry-run or --commit", file=sys.stderr); return 2
    dry = not args.commit
    con = sqlite3.connect(str(DB))
    results = []
    for fname, pilot_id in FILE_TO_PILOT.items():
        ensure_pilot_run(con, pilot_id, dry_run=dry)
        results.append(ingest_file(con, WS / fname, pilot_id, dry_run=dry))
    if not dry:
        con.commit()
    con.close()
    total = sum(r.get("inserted", 0) for r in results)
    print(json.dumps(results, indent=2))
    print(f"\n{'DRY-RUN: ' if dry else ''}total rows to insert: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
