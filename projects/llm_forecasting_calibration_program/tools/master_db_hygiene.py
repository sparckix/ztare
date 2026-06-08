#!/usr/bin/env python3
"""Read-only hygiene audit for the GP-245 master calibration DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"

KNOWN_NONSTANDARD_CALL_FILES = {
    "novel_bias_smokes_n42_diversified_calls.jsonl": "v28_novel_bias_smokes_n42_diversified",
    "novel_bias_smokes_n30_calls.jsonl": "v28_novel_bias_smokes_n30",
    "freq_inheritance_DI_panel_smoke_n15_calls.jsonl": "f104_freq_inheritance_DI_panel_n15",
    "freq_inheritance_smoke_n15_calls.jsonl": "f104_freq_inheritance_n15",
    "pilot_v28timedecay_calls_full_corpusv25.jsonl": "v28timedecay_full_corpusv25",
    "f105_metacognition_smoke_n15_calls.jsonl": "f105_metacognition_smoke_n15",
    "f105_v5_effort_estimation_calls.jsonl": "f105_v5_effort_claude",
    "f105_v5_multifamily_codex_calls.jsonl": "f105_v5_effort_codex_55",
    "f105_v5_multifamily_gemini_calls.jsonl": "f105_v5_effort_gemini",
    "f105_v5_multifamily_deepseek_calls.jsonl": "f105_v5_effort_deepseek",
    "f105_v6_stepcount_claude_calls.jsonl": "f105_v6_stepcount_claude",
    "f106_ood_inheritance_cheap_n15_calls.jsonl": "f106_ood_inheritance_cheap_n15",
    "f107_corrected_ood_panel_calls.jsonl": "f107_corrected_ood_panel",
    "premium_batch1_calls.jsonl": "premium_batch1",
    "premium_crossfamily_calls.jsonl": "premium_crossfamily",
    "anti_bias_collapse_v1_calls.jsonl": "anti_bias_collapse_v1",
}

FAILED_CALL_SIDECAR_SUFFIX = "_failed_calls.jsonl"

Y_KNOWN_BUCKET_SQL = """
CASE
  WHEN c.y_known IS NOT NULL THEN 'y_known_present'
  WHEN c.source = 'bias_inheritance_ood'
    OR c.source_corpus IN ('f106_ood_inheritance_cheap_n15', 'f107_corrected_ood_panel')
    OR c.task_type IN ('F106_ood_inheritance', 'F107_corrected_ood')
    THEN 'nonbinary_bias_panel'
  WHEN c.source = 'f105_effort_estimation'
    OR c.source_corpus LIKE 'f105_v5_effort_%'
    OR c.source_corpus LIKE 'f105_v6_stepcount_%'
    THEN 'nonbinary_continuous_effort_panel'
  WHEN c.source = 'legacy_orphan_backfill'
    THEN 'legacy_backfill_unresolved'
  ELSE 'scoreable_candidate_missing_y_known'
END
"""


def scalar(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return cur.execute(sql, params).fetchone()[0]


def derive_conventional_pilot_id(path: Path) -> str | None:
    name = path.stem
    if not name.startswith("pilot_") or "_calls" not in name:
        return None
    name = name[6:].replace("_calls", "")
    corpus = "v25_external" if ("corpusv25" in name or "corpus_v25" in name) else "internal"
    name = name.replace("_corpusv25", "").replace("_corpus_v25", "")
    return f"{name}__{corpus}"


def looks_like_call_ledger(path: Path) -> tuple[bool, int]:
    rows = 0
    signal = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return False, 0
    for line in lines[:50]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        rows += 1
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        has_id = bool(row.get("contract_id") or row.get("task_id") or row.get("pair_id"))
        has_agent = bool(
            row.get("agent_id")
            or row.get("receiver_agent_id")
            or row.get("sender_agent_id")
            or row.get("agent_A")
            or row.get("agent_B")
            or row.get("model")
        )
        has_probability = (
            isinstance(parsed.get("p_success"), (int, float))
            or isinstance(row.get("p_success"), (int, float))
            or isinstance(row.get("p_B_independent_concurrent"), (int, float))
        )
        if has_id and (has_agent or has_probability):
            signal += 1
    if rows == 0:
        return False, 0
    return signal >= max(1, rows // 2), len(lines)


def jsonl_db_sync(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(PROGRAM_ROOT.glob("**/workspace/*.jsonl")):
        is_calls, line_count = looks_like_call_ledger(path)
        if not is_calls:
            continue
        if path.name.endswith(FAILED_CALL_SIDECAR_SUFFIX):
            out.append(
                {
                    "path": str(path.relative_to(REPO)),
                    "lines": line_count,
                    "expected_pilot_id": None,
                    "db_rows_by_pilot_id": 0,
                    "db_pilot_runs_by_source_path": 0,
                    "status": "failure_sidecar_not_claim_store",
                }
            )
            continue
        expected = KNOWN_NONSTANDARD_CALL_FILES.get(path.name) or derive_conventional_pilot_id(path)
        db_rows = 0
        db_source_rows = 0
        if expected:
            db_rows = scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = ?", (expected,))
        db_source_rows = scalar(
            cur,
            "SELECT COUNT(*) FROM pilot_runs WHERE source_jsonl_path LIKE ?",
            (f"%{path.name}",),
        )
        status = "in_db" if (db_rows or db_source_rows) else "not_seen_in_db"
        out.append(
            {
                "path": str(path.relative_to(REPO)),
                "lines": line_count,
                "expected_pilot_id": expected,
                "db_rows_by_pilot_id": db_rows,
                "db_pilot_runs_by_source_path": db_source_rows,
                "status": status,
            }
        )
    return out


def audit(db: Path) -> dict[str, Any]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    tables = {
        name: scalar(cur, f"SELECT COUNT(*) FROM {name}")
        for name in ("contracts", "pilot_runs", "pilot_calls")
    }
    y_known = {
        "contracts_total": tables["contracts"],
        "contracts_y_known": scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NOT NULL"),
        "contracts_missing_y_known": scalar(cur, "SELECT COUNT(*) FROM contracts WHERE y_known IS NULL"),
    }
    corpus_class = [
        {
            "corpus_class": row[0],
            "contracts": row[1],
            "y_known": row[2],
            "missing_y_known": row[3],
        }
        for row in cur.execute(
            """
            SELECT cc.corpus_class,
                   COUNT(*) AS n,
                   SUM(CASE WHEN c.y_known IS NOT NULL THEN 1 ELSE 0 END) AS y_known,
                   SUM(CASE WHEN c.y_known IS NULL THEN 1 ELSE 0 END) AS missing_y_known
            FROM contracts c
            JOIN v_corpus_class cc ON cc.contract_id = c.contract_id
            GROUP BY cc.corpus_class
            ORDER BY n DESC
            """
        )
    ]
    source_corpus = [
        {
            "source_corpus": row[0],
            "contracts": row[1],
            "y_known": row[2],
            "missing_y_known": row[3],
        }
        for row in cur.execute(
            """
            SELECT COALESCE(source_corpus, '') AS source_corpus,
                   COUNT(*) AS n,
                   SUM(CASE WHEN y_known IS NOT NULL THEN 1 ELSE 0 END) AS y_known,
                   SUM(CASE WHEN y_known IS NULL THEN 1 ELSE 0 END) AS missing_y_known
            FROM contracts
            GROUP BY COALESCE(source_corpus, '')
            ORDER BY missing_y_known DESC, n DESC
            LIMIT 25
            """
        )
    ]
    y_known_buckets = [
        {
            "bucket": row[0],
            "corpus_class": row[1],
            "contracts": row[2],
            "y_known": row[3],
            "missing_y_known": row[4],
        }
        for row in cur.execute(
            f"""
            SELECT {Y_KNOWN_BUCKET_SQL} AS bucket,
                   cc.corpus_class,
                   COUNT(*) AS n,
                   SUM(CASE WHEN c.y_known IS NOT NULL THEN 1 ELSE 0 END) AS y_known,
                   SUM(CASE WHEN c.y_known IS NULL THEN 1 ELSE 0 END) AS missing_y_known
            FROM contracts c
            JOIN v_corpus_class cc ON cc.contract_id = c.contract_id
            GROUP BY bucket, cc.corpus_class
            ORDER BY missing_y_known DESC, n DESC
            """
        )
    ]
    scoreable_source_gaps = [
        {
            "source_corpus": row[0],
            "source": row[1],
            "task_type": row[2],
            "contracts": row[3],
            "missing_y_known": row[4],
        }
        for row in cur.execute(
            f"""
            SELECT COALESCE(c.source_corpus, '') AS source_corpus,
                   COALESCE(c.source, '') AS source,
                   COALESCE(c.task_type, '') AS task_type,
                   COUNT(*) AS n,
                   SUM(CASE WHEN c.y_known IS NULL THEN 1 ELSE 0 END) AS missing_y_known
            FROM contracts c
            WHERE {Y_KNOWN_BUCKET_SQL} = 'scoreable_candidate_missing_y_known'
            GROUP BY COALESCE(c.source_corpus, ''), COALESCE(c.source, ''), COALESCE(c.task_type, '')
            ORDER BY missing_y_known DESC, n DESC
            LIMIT 25
            """
        )
    ]
    calls = {
        "calls_total": tables["pilot_calls"],
        "schema_ok": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE schema_ok = 1"),
        "schema_bad_or_null": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE schema_ok IS NULL OR schema_ok != 1"),
        "with_brier": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NOT NULL"),
        "missing_brier": scalar(cur, "SELECT COUNT(*) FROM pilot_calls WHERE brier IS NULL"),
        "orphan_contract_calls": scalar(
            cur,
            """
            SELECT COUNT(*)
            FROM pilot_calls pc
            LEFT JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE c.contract_id IS NULL
            """,
        ),
        "orphan_pilot_calls": scalar(
            cur,
            """
            SELECT COUNT(*)
            FROM pilot_calls pc
            LEFT JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
            WHERE pr.pilot_id IS NULL
            """,
        ),
    }
    pilot_coverage = [
        {
            "pilot_id": row[0],
            "n_calls": row[1],
            "schema_ok": row[2],
            "with_brier": row[3],
        }
        for row in cur.execute(
            """
            SELECT pilot_id,
                   COUNT(*) AS n_calls,
                   SUM(CASE WHEN schema_ok = 1 THEN 1 ELSE 0 END) AS schema_ok,
                   SUM(CASE WHEN brier IS NOT NULL THEN 1 ELSE 0 END) AS with_brier
            FROM pilot_calls
            GROUP BY pilot_id
            HAVING with_brier < n_calls
            ORDER BY (n_calls - with_brier) DESC, n_calls DESC
            LIMIT 25
            """
        )
    ]
    orphan_contract_by_pilot = [
        {"pilot_id": row[0], "orphan_calls": row[1]}
        for row in cur.execute(
            """
            SELECT pc.pilot_id, COUNT(*) AS orphan_calls
            FROM pilot_calls pc
            LEFT JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE c.contract_id IS NULL
            GROUP BY pc.pilot_id
            ORDER BY orphan_calls DESC
            LIMIT 25
            """
        )
    ]
    family_counts = {
        str(row[0] or "NULL"): int(row[1])
        for row in cur.execute(
            """
            SELECT family, COUNT(*)
            FROM pilot_calls
            GROUP BY family
            ORDER BY COUNT(*) DESC
            """
        )
    }
    family_alias_issues = {
        "codex_mini_rows": family_counts.get("codex_mini", 0),
        "null_family_rows": family_counts.get("NULL", 0),
    }
    suspicious_primitive_base = [
        {"primitive_base": row[0], "calls": row[1]}
        for row in cur.execute(
            """
            SELECT primitive_base, COUNT(*)
            FROM pilot_calls
            WHERE LENGTH(COALESCE(primitive_base, '')) = 1
            GROUP BY primitive_base
            ORDER BY COUNT(*) DESC
            """
        )
    ]
    sync_rows = jsonl_db_sync(cur)
    con.close()

    external_y = next((r["y_known"] for r in corpus_class if r["corpus_class"] == "external"), 0) or 0
    internal_y = next((r["y_known"] for r in corpus_class if r["corpus_class"] == "internal"), 0) or 0
    parity_gap = max(0, external_y - internal_y)
    scoreable_missing = sum(
        row["missing_y_known"]
        for row in y_known_buckets
        if row["bucket"] == "scoreable_candidate_missing_y_known"
    )
    nonbinary_missing = sum(
        row["missing_y_known"]
        for row in y_known_buckets
        if row["bucket"] == "nonbinary_bias_panel"
    )
    legacy_missing = sum(
        row["missing_y_known"]
        for row in y_known_buckets
        if row["bucket"] == "legacy_backfill_unresolved"
    )

    return {
        "schema": "gp245-master-db-hygiene-v1",
        "db": str(db),
        "tables": tables,
        "y_known": y_known,
        "y_known_outcome_buckets": y_known_buckets,
        "y_known_debt": {
            "scoreable_candidate_missing_y_known": scoreable_missing,
            "nonbinary_bias_panel_missing_y_known": nonbinary_missing,
            "legacy_backfill_unresolved_missing_y_known": legacy_missing,
        },
        "corpus_class": corpus_class,
        "source_corpus_top_missing": source_corpus,
        "scoreable_source_corpus_top_missing_y_known": scoreable_source_gaps,
        "pilot_calls": calls,
        "pilot_coverage_top_missing_brier": pilot_coverage,
        "orphan_contract_calls_by_pilot": orphan_contract_by_pilot,
        "family_counts": family_counts,
        "family_alias_issues": family_alias_issues,
        "suspicious_primitive_base": suspicious_primitive_base,
        "jsonl_db_sync": {
            "call_ledgers_scanned": len(sync_rows),
            "not_seen_in_db": [row for row in sync_rows if row["status"] == "not_seen_in_db"][:50],
            "not_seen_count": sum(1 for row in sync_rows if row["status"] == "not_seen_in_db"),
            "failure_sidecars": [
                row for row in sync_rows if row["status"] == "failure_sidecar_not_claim_store"
            ],
            "failure_sidecar_count": sum(
                1 for row in sync_rows if row["status"] == "failure_sidecar_not_claim_store"
            ),
        },
        "internal_external_y_known_parity_gap": parity_gap,
    "next_actions": [
        "Resolve scoreable_candidate_missing_y_known rows; do not treat nonbinary bias or continuous-effort panels as binary y_known debt.",
            "Unify source/source_corpus aliases before deriving cross-corpus claims.",
            "Ingest sidecar experiment JSONL into pilot_runs/pilot_calls before using it in policy claims.",
            "Treat project files as receipts; treat DB views as the claim substrate.",
        ],
    }


def write_report(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "master_db_hygiene_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Master DB Hygiene Report",
        "",
        f"- Contracts: {result['tables']['contracts']}",
        f"- Pilot runs: {result['tables']['pilot_runs']}",
        f"- Pilot calls: {result['tables']['pilot_calls']}",
        f"- Contracts with `y_known`: {result['y_known']['contracts_y_known']}",
        f"- Contracts missing `y_known`: {result['y_known']['contracts_missing_y_known']}",
        f"- Scoreable candidate rows missing `y_known`: {result['y_known_debt']['scoreable_candidate_missing_y_known']}",
        f"- Non-binary bias-panel rows missing `y_known`: {result['y_known_debt']['nonbinary_bias_panel_missing_y_known']}",
        f"- Legacy backfill rows missing `y_known`: {result['y_known_debt']['legacy_backfill_unresolved_missing_y_known']}",
        f"- Internal/external `y_known` parity gap: {result['internal_external_y_known_parity_gap']}",
        "",
        "## Corpus Class Coverage",
        "",
    ]
    for row in result["corpus_class"]:
        lines.append(
            f"- `{row['corpus_class']}`: contracts={row['contracts']}, "
            f"y_known={row['y_known']}, missing={row['missing_y_known']}"
        )
    lines.extend(["", "## Top Source-Corpus Gaps", ""])
    for row in result["source_corpus_top_missing"][:12]:
        lines.append(
            f"- `{row['source_corpus']}`: contracts={row['contracts']}, "
            f"y_known={row['y_known']}, missing={row['missing_y_known']}"
        )
    lines.extend(["", "## Scoreable Candidate `y_known` Gaps", ""])
    for row in result["scoreable_source_corpus_top_missing_y_known"][:12]:
        lines.append(
            f"- `{row['source_corpus']}` / `{row['source']}` / `{row['task_type']}`: "
            f"contracts={row['contracts']}, missing={row['missing_y_known']}"
        )
    lines.extend(["", "## Outcome Buckets", ""])
    for row in result["y_known_outcome_buckets"]:
        lines.append(
            f"- `{row['bucket']}` / `{row['corpus_class']}`: contracts={row['contracts']}, "
            f"y_known={row['y_known']}, missing={row['missing_y_known']}"
        )
    lines.extend(["", "## Pilot-Call Coverage", ""])
    for key, value in result["pilot_calls"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Schema Drift", ""])
    lines.append(f"- `codex_mini` alias rows: {result['family_alias_issues']['codex_mini_rows']}")
    lines.append(f"- null family rows: {result['family_alias_issues']['null_family_rows']}")
    if result["suspicious_primitive_base"]:
        lines.append("- one-character `primitive_base` values:")
        for row in result["suspicious_primitive_base"][:10]:
            lines.append(f"  - `{row['primitive_base']}`: {row['calls']}")
    if result["orphan_contract_calls_by_pilot"]:
        lines.append("- top orphan-contract pilots:")
        for row in result["orphan_contract_calls_by_pilot"][:10]:
            lines.append(f"  - `{row['pilot_id']}`: {row['orphan_calls']}")
    lines.extend(["", "## JSONL to DB Sync", ""])
    sync = result["jsonl_db_sync"]
    lines.append(f"- Call ledgers scanned: {sync['call_ledgers_scanned']}")
    lines.append(f"- Not seen in DB: {sync['not_seen_count']}")
    lines.append(f"- Failure sidecars not treated as claim stores: {sync.get('failure_sidecar_count', 0)}")
    for row in sync["not_seen_in_db"][:12]:
        lines.append(
            f"- `{row['path']}`: lines={row['lines']}, "
            f"expected_pilot_id={row['expected_pilot_id']}"
        )
    lines.append("")
    (out_dir / "master_db_hygiene_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = audit(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_report(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
