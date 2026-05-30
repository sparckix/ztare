#!/usr/bin/env python3
"""SQLite persistence for forecaster-skill-calibration program.

Replaces the ad-hoc 88-pilot-files + 12-corpus-files JSONL layer with one
queryable database. JSONL remains the source-of-truth append log; this DB is
the index for cross-pilot, cross-corpus, cross-condition queries.

Schema:
  contracts(contract_id PK, question, source, source_corpus, horizon,
            y_known, post_training_cutoff, task_type, external_market_open,
            resolution_source_url, y_known_provenance, raw_json, created_at)

  pilot_runs(pilot_id PK, pilot_name, primitive, corpus, source_jsonl_path,
             fired_at, n_calls, n_schema_ok)

  pilot_calls(call_id PK AUTOINCREMENT, pilot_id FK, contract_id FK,
              agent_id, family, condition, primitive, p_success, brier,
              schema_ok, parsed_json, fired_at, raw_json)

Usage:
  calibration_db.py init
  calibration_db.py ingest-corpus <path-to-corpus.jsonl>
  calibration_db.py ingest-pilot  <path-to-pilot.jsonl>
  calibration_db.py ingest-all
  calibration_db.py query "<SQL>"
  calibration_db.py stats
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DB_PATH = REPO / "analytics" / "public" / "calibration" / "forecaster_calibration.db"


# ============================== Schema ==============================

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    contract_id           TEXT PRIMARY KEY,
    question              TEXT NOT NULL,
    source                TEXT,
    source_corpus         TEXT,
    horizon               TEXT,
    y_known               INTEGER,
    post_training_cutoff  INTEGER,
    task_type             TEXT,
    external_market_open  TEXT,
    resolution_source_url TEXT,
    y_known_provenance    TEXT,
    raw_json              TEXT,
    created_at            TEXT
);

CREATE TABLE IF NOT EXISTS pilot_runs (
    pilot_id             TEXT PRIMARY KEY,
    pilot_name           TEXT,
    primitive            TEXT,
    corpus               TEXT,
    source_jsonl_path    TEXT,
    fired_at             TEXT,
    n_calls              INTEGER,
    n_schema_ok          INTEGER
);

-- Pre-registrations: bind a hypothesis to a pilot BEFORE it fires.
-- Every entry must be written before the dispatch runs; verdict is filled in
-- after the pilot lands. This codifies §6n.6 / §6n.7 disciplines in the DB.
CREATE TABLE IF NOT EXISTS pre_registrations (
    prereg_id            TEXT PRIMARY KEY,         -- e.g. 'v27a_smoke_internal_2026-05-27'
    pilot_id             TEXT,                     -- expected pilot_id once fired (FK soft, may be NULL pre-fire)
    primitive_base       TEXT NOT NULL,            -- e.g. 'v27a'
    phase                TEXT NOT NULL,            -- 'smoke' or 'full'
    corpus               TEXT NOT NULL,            -- 'internal', 'v25_external', or both
    registered_at        TEXT NOT NULL,            -- ISO timestamp before fire
    hypothesis           TEXT NOT NULL,            -- one-sentence H1
    null_hypothesis      TEXT NOT NULL,            -- one-sentence H0
    expected_direction   TEXT,                     -- 'improves', 'degrades', 'spreads_track_error', etc
    expected_effect_size TEXT,                     -- e.g. 'ρ ≥ 0.3' or 'Δ-Brier ≤ -0.05'
    n_required           INTEGER,                  -- per-family N for full pilot at expected effect size
    n_planned            INTEGER,                  -- N this pilot will run at
    falsifiers           TEXT NOT NULL,            -- bulleted text of what would falsify H1
    pass_gate            TEXT,                     -- conditions for smoke→full promotion
    verdict              TEXT,                     -- 'h1_supported', 'h0_kept', 'inconclusive_underpowered', 'invalid_run', NULL=pending
    verdict_notes        TEXT,                     -- post-fire reasoning
    landed_at            TEXT                      -- ISO timestamp when verdict was recorded
);
CREATE INDEX IF NOT EXISTS idx_prereg_primitive ON pre_registrations(primitive_base);
CREATE INDEX IF NOT EXISTS idx_prereg_verdict   ON pre_registrations(verdict);

CREATE TABLE IF NOT EXISTS pilot_calls (
    call_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    pilot_id       TEXT    NOT NULL,
    contract_id    TEXT    NOT NULL,
    agent_id       TEXT,
    family         TEXT,
    condition      TEXT,
    primitive      TEXT,       -- raw token from filename, e.g. 'v26d_full', 'v6_receiver_forecasts'
    primitive_base TEXT,       -- normalised, e.g. 'v26d', 'v6'
    phase          TEXT,       -- 'full', 'smoke', 'revise_full', NULL
    role           TEXT,       -- NULL for single-agent; 'A'/'B'/'sender'/'receiver' for paired
    pair_id        TEXT,       -- ties together the two rows of a paired-forecast experiment
    p_success      REAL,
    brier          REAL,
    schema_ok      INTEGER,
    parsed_json    TEXT,
    fired_at       TEXT,
    raw_json       TEXT,
    FOREIGN KEY (pilot_id)    REFERENCES pilot_runs(pilot_id),
    FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
);

CREATE INDEX IF NOT EXISTS idx_calls_contract  ON pilot_calls(contract_id);
CREATE INDEX IF NOT EXISTS idx_calls_family    ON pilot_calls(family);
CREATE INDEX IF NOT EXISTS idx_calls_primitive ON pilot_calls(primitive);
CREATE INDEX IF NOT EXISTS idx_calls_pilot     ON pilot_calls(pilot_id);
CREATE INDEX IF NOT EXISTS idx_calls_corpus    ON pilot_calls(pilot_id);
CREATE INDEX IF NOT EXISTS idx_contracts_src   ON contracts(source);
CREATE INDEX IF NOT EXISTS idx_contracts_corpus ON contracts(source_corpus);

-- Per-family per-pilot Brier (only schema-OK + has y_known)
CREATE VIEW IF NOT EXISTS v_family_brier_by_pilot AS
  SELECT pr.pilot_id, pr.pilot_name, pr.primitive, pr.corpus,
         pc.family,
         COUNT(*) AS n,
         AVG(pc.brier) AS mean_brier
  FROM pilot_calls pc
  JOIN pilot_runs  pr ON pr.pilot_id = pc.pilot_id
  WHERE pc.schema_ok = 1
    AND pc.brier IS NOT NULL
    AND pc.family IS NOT NULL
  GROUP BY pr.pilot_id, pc.family;

-- Cross-pilot per-family Brier rollup, keyed on the NORMALISED primitive_base
CREATE VIEW IF NOT EXISTS v_family_brier_by_primitive_corpus AS
  SELECT pc.primitive_base, pr.corpus, pc.family, pc.phase,
         COUNT(DISTINCT pr.pilot_id) AS n_pilots,
         COUNT(*) AS n_calls,
         AVG(pc.brier) AS mean_brier
  FROM pilot_calls pc
  JOIN pilot_runs  pr ON pr.pilot_id = pc.pilot_id
  WHERE pc.schema_ok = 1
    AND pc.brier IS NOT NULL
    AND pc.family IS NOT NULL
    AND pc.primitive_base IS NOT NULL
    AND (pc.phase = 'full' OR pc.phase IS NULL)
  GROUP BY pc.primitive_base, pr.corpus, pc.family, pc.phase;

-- Per-pilot summary (one row per pilot_id)
CREATE VIEW IF NOT EXISTS v_pilot_summary AS
  SELECT pr.pilot_id, pr.pilot_name, pr.primitive, pr.corpus, pr.fired_at,
         COUNT(pc.call_id) AS n_calls,
         SUM(CASE WHEN pc.schema_ok = 1 THEN 1 ELSE 0 END) AS n_schema_ok,
         SUM(CASE WHEN pc.brier IS NOT NULL THEN 1 ELSE 0 END) AS n_with_brier,
         AVG(pc.brier) AS mean_brier,
         COUNT(DISTINCT pc.family) AS n_families,
         COUNT(DISTINCT pc.contract_id) AS n_contracts
  FROM pilot_runs pr
  LEFT JOIN pilot_calls pc ON pc.pilot_id = pr.pilot_id
  GROUP BY pr.pilot_id;

-- Per-contract consensus: agreement / spread across all agents that forecasted it
CREATE VIEW IF NOT EXISTS v_contract_difficulty AS
  SELECT pc.contract_id, c.source_corpus, c.y_known,
         COUNT(*) AS n_calls,
         AVG(pc.p_success) AS mean_p,
         AVG(pc.brier) AS mean_brier,
         MAX(pc.p_success) - MIN(pc.p_success) AS p_range
  FROM pilot_calls pc
  LEFT JOIN contracts c ON c.contract_id = pc.contract_id
  WHERE pc.schema_ok = 1 AND pc.p_success IS NOT NULL
  GROUP BY pc.contract_id;

-- Cross-pilot intervention deltas: for each (primitive_base, corpus, family),
-- the mean Brier alongside the matched baseline Brier for the same corpus+family.
CREATE VIEW IF NOT EXISTS v_intervention_vs_baseline AS
  WITH base AS (
    SELECT pr.corpus, pc.family, AVG(pc.brier) AS baseline_brier, COUNT(*) AS n_base
    FROM pilot_calls pc JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
    WHERE pc.primitive_base = 'baseline' AND pc.phase = 'full'
      AND pc.schema_ok = 1 AND pc.brier IS NOT NULL AND pc.family IS NOT NULL
    GROUP BY pr.corpus, pc.family
  )
  SELECT pc.primitive_base, pc.phase, pr.corpus, pc.family,
         COUNT(*) AS n_v,
         AVG(pc.brier) AS intervention_brier,
         base.baseline_brier,
         base.n_base,
         AVG(pc.brier) - base.baseline_brier AS delta_brier
  FROM pilot_calls pc
  JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
  LEFT JOIN base ON base.corpus = pr.corpus AND base.family = pc.family
  WHERE pc.primitive_base IS NOT NULL
    AND pc.primitive_base != 'baseline'
    AND pc.phase = 'full'
    AND pc.schema_ok = 1 AND pc.brier IS NOT NULL AND pc.family IS NOT NULL
  GROUP BY pc.primitive_base, pc.phase, pr.corpus, pc.family;
"""


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    # FK enforcement off: pilot_calls may reference contracts from corpora we
    # haven't yet ingested (legacy pilots). Orphan calls are surfaced via outer
    # join in queries rather than blocking ingest.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    print(f"Initialised schema at {DB_PATH}")
    conn.close()


# ============================== Family normalisation ==============================

def family_of(agent_id):
    if not agent_id:
        return None
    a = str(agent_id).lower()
    if "claude" in a: return "claude"
    if "codex_55" in a or "codex_5.5" in a or "gpt-5.5" in a or "gpt5.5" in a: return "codex_55"
    if "codex_54mini" in a or "codex_5.4mini" in a or "5.4-mini" in a or "5.4mini" in a or "gpt-5.4-mini" in a: return "codex_mini"
    # codex_rd_pilot_* without explicit version: treat as codex_55 (the default codex in those pilots)
    if "codex_rd_pilot" in a or a.startswith("codex_") or a.startswith("codex-"): return "codex_55"
    if "gemini" in a: return "gemini"
    if "deepseek" in a: return "deepseek"
    return None


def extract_agent_id(r):
    """Robust agent_id resolution across pilot schemas.

    Newer pilots: r['agent_id']
    v6/v6.1:      r['receiver_agent_id'] (or sender_agent_id; we use receiver)
    v15:          r['agent_id'] + r['codex_model'] (codex_model as fallback)
    v5/v5.1:      no single agent_id (paired). Use agent_B_codex_model or agent_A_v3_id.
    Generic:      r['model'] when nothing else.
    """
    return (
        r.get("agent_id")
        or r.get("receiver_agent_id")
        or r.get("sender_agent_id")
        or r.get("receiver_v3_id")
        or r.get("receiver_codex_model")
        or r.get("agent_B_codex_model")
        or r.get("agent_B")
        or r.get("agent_A_v3_id")
        or r.get("agent_A")
        or r.get("codex_model")
        or r.get("model")
    )


def normalise_primitive(raw_primitive):
    """Strip _full/_smoke/_revise/forecasts/_receiver_forecasts/_sender_forecasts/_control_forecasts suffixes.

    Examples:
      v26d_full        -> ('v26d', 'full')
      v26b_revise_full -> ('v26b', 'revise_full')
      v10_             -> ('v10', None)
      v6_receiver_forecasts -> ('v6', 'receiver_forecasts')
      v5_forecasts_     -> ('v5', 'forecasts')
      v5_1_forecasts    -> ('v5_1', 'forecasts')
      v22b              -> ('v22b', None)
      baseline          -> ('baseline', None)
    """
    if not raw_primitive:
        return None, None
    p = raw_primitive.rstrip("_")
    # Suffixes (longest first to win on prefix match)
    suffixes = [
        "_revise_full", "_receiver_forecasts", "_sender_forecasts",
        "_control_forecasts", "_independent_concurrent", "_independent",
        "_forecasts", "_revise", "_full", "_smoke",
    ]
    phase = None
    for s in suffixes:
        if p.endswith(s):
            phase = s.lstrip("_")
            p = p[: -len(s)]
            break
    return p.rstrip("_") or None, phase


# ============================== Corpus ingest ==============================

def ingest_corpus(jsonl_path, conn=None):
    if conn is None:
        conn = get_conn()
        own = True
    else:
        own = False
    p = Path(jsonl_path)
    if not p.exists():
        print(f"  MISSING: {p}")
        if own: conn.close()
        return 0
    n = 0
    corpus_name = p.stem
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        cid = r.get("contract_id")
        if not cid:
            continue
        # Some corpora encode source differently
        source = r.get("external_source") or r.get("source") or r.get("source_pool")
        y_known = r.get("y_known")
        if y_known is not None:
            try: y_known = int(y_known)
            except Exception: y_known = None
        post = r.get("post_training_cutoff")
        if post is not None:
            post = int(bool(post))
        # Preserve y_known: if existing row has y_known and new one doesn't,
        # keep the existing y_known + resolution metadata. The canonical corpus
        # for a contract is the one that sourced its resolution.
        existing = conn.execute(
            "SELECT y_known, source_corpus, resolution_source_url, y_known_provenance "
            "FROM contracts WHERE contract_id = ?", (cid,)
        ).fetchone()
        if existing and existing["y_known"] is not None and y_known is None:
            # Keep the resolved row; only refresh question/source/raw_json
            conn.execute(
                """UPDATE contracts SET question = ?, raw_json = ?
                   WHERE contract_id = ?""",
                (r.get("question", ""), json.dumps(r), cid)
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO contracts
                   (contract_id, question, source, source_corpus, horizon, y_known,
                    post_training_cutoff, task_type, external_market_open,
                    resolution_source_url, y_known_provenance, raw_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, r.get("question", ""), source, corpus_name, r.get("horizon"),
                 y_known, post, r.get("task_type"), r.get("external_market_open"),
                 r.get("resolution_source_url"), r.get("y_known_provenance"),
                 json.dumps(r), datetime.now(timezone.utc).isoformat())
            )
        n += 1
    conn.commit()
    print(f"  ingested {n} contracts from {p.name} (corpus={corpus_name})")
    if own: conn.close()
    return n


# ============================== Pilot ingest ==============================

def derive_pilot_id_and_primitive(jsonl_path):
    """Derive a stable pilot_id and primitive from filename.

    Examples:
      pilot_v26d_calls_full.jsonl                       -> v26d_internal_full
      pilot_v26d_calls_full_corpusv25.jsonl             -> v26d_external_full
      pilot_baseline_calls_full.jsonl                   -> baseline_internal_full
      pilot_baseline_calls_full_corpusv25.jsonl         -> baseline_external_full
      pilot_v22d_calls.jsonl                            -> v22d_full
      pilot_v9_1_calls_MERGED.jsonl                     -> v9_1_MERGED
    """
    name = Path(jsonl_path).stem
    # Strip 'pilot_'
    if name.startswith("pilot_"):
        name = name[6:]
    # Strip '_calls'
    name = name.replace("_calls", "")
    # Determine corpus
    corpus = "unknown"
    if "corpusv25" in name or "corpus_v25" in name:
        corpus = "v25_external"
        name = name.replace("_corpusv25", "").replace("_corpus_v25", "")
    elif any(s in jsonl_path for s in ["corpus_v22", "corpus_v21", "_v22.", "v21"]):
        corpus = "internal"
    else:
        corpus = "internal"  # default if no marker
    # `name` after the strips above is e.g. "v26d_full" or "baseline_full" or "v6_receiver_forecasts".
    # Use the full name as `primitive`; normalise_primitive() splits off the phase suffix.
    primitive = name
    pilot_id = f"{name}__{corpus}"
    return pilot_id, primitive, corpus


def get_brier(parsed, y_known):
    if y_known is None: return None
    if parsed is None: return None
    if "p_success" in parsed and isinstance(parsed["p_success"], (int, float)):
        return (parsed["p_success"] - y_known) ** 2
    # v26a paired: p_success_a + p_success_b — score against contract_id default mapping
    if "p_success_a" in parsed and isinstance(parsed["p_success_a"], (int, float)):
        return (parsed["p_success_a"] - y_known) ** 2
    return None


def ingest_pilot(jsonl_path, conn=None):
    if conn is None:
        conn = get_conn()
        own = True
    else:
        own = False
    p = Path(jsonl_path)
    if not p.exists():
        print(f"  MISSING: {p}")
        if own: conn.close()
        return 0
    pilot_id, primitive, corpus = derive_pilot_id_and_primitive(str(p))
    # Idempotent ingest: delete any prior rows for this pilot_id before re-inserting.
    # Prevents duplicate accumulation when ingest-pilot runs more than once for the same file.
    conn.execute("DELETE FROM pilot_calls WHERE pilot_id = ?", (pilot_id,))
    conn.execute("DELETE FROM pilot_runs  WHERE pilot_id = ?", (pilot_id,))
    rows = list(p.read_text().splitlines())
    n_calls = 0
    n_ok = 0
    for line in rows:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        cid = r.get("contract_id") or r.get("task_id") or r.get("pair_id")
        if not cid:
            continue
        agent_id = extract_agent_id(r)
        family = family_of(agent_id)
        condition = r.get("condition") or r.get("sub_condition") or r.get("row_kind") or r.get("stage")
        parsed = r.get("parsed") or {}
        schema = r.get("schema_audit", {}) or {}
        # Newer pilots set schema_audit.schema_ok; older ones set parsed_ok.
        schema_ok_flag = schema.get("schema_ok") if isinstance(schema, dict) else None
        if schema_ok_flag is None:
            schema_ok_flag = r.get("parsed_ok")
        schema_ok = 1 if schema_ok_flag else 0
        p_success = parsed.get("p_success") if isinstance(parsed.get("p_success"), (int, float)) else None
        # Lookup y_known from contracts table to compute brier
        cur = conn.execute("SELECT y_known FROM contracts WHERE contract_id = ?", (cid,))
        row = cur.fetchone()
        y_known = row["y_known"] if row else None
        brier = get_brier(parsed, y_known)
        n_calls += 1
        if schema_ok: n_ok += 1
        primitive_base, phase = normalise_primitive(primitive)
        fired_at = r.get("fired_at") or r.get("started_at") or r.get("pilot_run_ts") or r.get("ts")

        # Paired-forecast detection: emit one row per agent.
        rows_to_emit = []
        if r.get("receiver_agent_id") and not r.get("agent_id"):
            # v6 family (sender + receiver). Use pair_id = contract_id + ts.
            pair_id = f"{cid}__{fired_at or ''}"
            recv_agent = r.get("receiver_agent_id") or r.get("model")
            send_agent = r.get("sender_agent_id")
            recv_p = parsed.get("p_success") if isinstance(parsed.get("p_success"), (int, float)) else None
            rows_to_emit.append({
                "agent_id": recv_agent, "family": family_of(recv_agent), "role": "receiver",
                "pair_id": pair_id, "p_success": recv_p,
                "brier": get_brier({"p_success": recv_p}, y_known) if recv_p is not None else None,
            })
            if send_agent:
                rows_to_emit.append({
                    "agent_id": send_agent, "family": family_of(send_agent), "role": "sender",
                    "pair_id": pair_id, "p_success": None,
                    "brier": None,
                })
        elif r.get("agent_A") and r.get("agent_B"):
            # v5 family. agent_A is the shown forecaster, agent_B is the independent / influenced agent.
            pair_id = r.get("pair_id") or f"{cid}__{fired_at or ''}"
            a_agent = r.get("agent_A_v3_id") or r.get("agent_A")
            b_agent = r.get("agent_B_codex_model") or r.get("agent_B")
            p_a = r.get("p_A_shown") if isinstance(r.get("p_A_shown"), (int, float)) else None
            p_b = (r.get("p_B_independent_concurrent")
                   or r.get("p_B_independent_v3_stale"))
            if not isinstance(p_b, (int, float)): p_b = None
            rows_to_emit.append({
                "agent_id": a_agent, "family": family_of(a_agent), "role": "A",
                "pair_id": pair_id, "p_success": p_a,
                "brier": get_brier({"p_success": p_a}, y_known) if p_a is not None else None,
            })
            rows_to_emit.append({
                "agent_id": b_agent, "family": family_of(b_agent), "role": "B",
                "pair_id": pair_id, "p_success": p_b,
                "brier": get_brier({"p_success": p_b}, y_known) if p_b is not None else None,
            })
        else:
            rows_to_emit.append({
                "agent_id": agent_id, "family": family, "role": None,
                "pair_id": None, "p_success": p_success, "brier": brier,
            })

        for er in rows_to_emit:
            conn.execute(
                """INSERT INTO pilot_calls
                   (pilot_id, contract_id, agent_id, family, condition, primitive,
                    primitive_base, phase, role, pair_id, p_success, brier,
                    schema_ok, parsed_json, fired_at, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pilot_id, cid, er["agent_id"], er["family"], condition, primitive,
                 primitive_base, phase, er["role"], er["pair_id"], er["p_success"],
                 er["brier"], schema_ok, json.dumps(parsed), fired_at, line)
            )
    conn.execute(
        """INSERT OR REPLACE INTO pilot_runs
           (pilot_id, pilot_name, primitive, corpus, source_jsonl_path,
            fired_at, n_calls, n_schema_ok)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (pilot_id, p.stem, primitive, corpus, str(p),
         datetime.now(timezone.utc).isoformat(), n_calls, n_ok)
    )
    conn.commit()
    print(f"  ingested {n_calls} calls ({n_ok} schema-ok) from {p.name} -> {pilot_id}")
    if own: conn.close()
    return n_calls


# ============================== ingest-all ==============================

def ingest_all():
    """Find all corpus_*.jsonl and pilot_*.jsonl in projects/ and ingest."""
    conn = get_conn()
    # First wipe existing pilot_calls (idempotent re-ingest); contracts use INSERT OR REPLACE so safe
    conn.execute("DELETE FROM pilot_calls")
    conn.execute("DELETE FROM pilot_runs")
    conn.commit()

    # Corpora
    corpus_paths = sorted(REPO.glob("projects/**/workspace/corpus_*.jsonl"))
    print(f"\n=== Ingesting {len(corpus_paths)} corpus files ===")
    total_contracts = 0
    for p in corpus_paths:
        total_contracts += ingest_corpus(str(p), conn=conn)

    # Pilots
    pilot_paths = sorted(REPO.glob("projects/**/workspace/pilot_*.jsonl"))
    print(f"\n=== Ingesting {len(pilot_paths)} pilot files ===")
    total_calls = 0
    for p in pilot_paths:
        try:
            total_calls += ingest_pilot(str(p), conn=conn)
        except Exception as e:
            print(f"  ERROR ingesting {p.name}: {e!r}")

    print(f"\n=== Summary ===")
    print(f"Contracts: {total_contracts}")
    print(f"Pilot calls: {total_calls}")
    conn.close()


# ============================== query / stats ==============================

def run_query(sql):
    conn = get_conn()
    cur = conn.execute(sql)
    rows = cur.fetchall()
    if not rows:
        print("(no rows)")
        return
    cols = rows[0].keys()
    print(" | ".join(cols))
    print("-" * 80)
    for r in rows:
        print(" | ".join(str(r[c]) for c in cols))
    print(f"\n({len(rows)} rows)")
    conn.close()


def stats():
    conn = get_conn()
    print("=== Database stats ===")
    for table in ["contracts", "pilot_runs", "pilot_calls"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n}")
    print("\n=== Contracts by corpus ===")
    for r in conn.execute("SELECT source_corpus, COUNT(*) AS n FROM contracts GROUP BY source_corpus ORDER BY n DESC"):
        print(f"  {r['source_corpus']:<30} {r['n']}")
    print("\n=== Contracts by source ===")
    for r in conn.execute("SELECT source, COUNT(*) AS n FROM contracts WHERE source IS NOT NULL GROUP BY source ORDER BY n DESC LIMIT 20"):
        print(f"  {r['source']:<30} {r['n']}")
    print("\n=== Contracts with y_known by corpus ===")
    for r in conn.execute("SELECT source_corpus, COUNT(*) AS n FROM contracts WHERE y_known IS NOT NULL GROUP BY source_corpus ORDER BY n DESC"):
        print(f"  {r['source_corpus']:<30} {r['n']}")
    print("\n=== Pilot calls by primitive ===")
    for r in conn.execute("SELECT primitive, COUNT(*) AS n FROM pilot_calls GROUP BY primitive ORDER BY n DESC LIMIT 20"):
        print(f"  {r['primitive']:<30} {r['n']}")
    print("\n=== Pilot calls by family ===")
    for r in conn.execute("SELECT family, COUNT(*) AS n FROM pilot_calls WHERE family IS NOT NULL GROUP BY family ORDER BY n DESC"):
        print(f"  {r['family']:<30} {r['n']}")
    print("\n=== Pilot calls per pilot (top 15) ===")
    for r in conn.execute("SELECT pilot_id, COUNT(*) AS n, SUM(schema_ok) AS ok FROM pilot_calls GROUP BY pilot_id ORDER BY n DESC LIMIT 15"):
        print(f"  {r['pilot_id']:<50} n={r['n']} ok={r['ok']}")
    conn.close()


# ============================== CLI ==============================

def prereg_add(prereg_id, primitive_base, phase, corpus, hypothesis,
               null_hypothesis, falsifiers, expected_direction=None,
               expected_effect_size=None, n_required=None, n_planned=None,
               pass_gate=None, target_rho=None):
    """Register a hypothesis BEFORE firing. If target_rho is provided, n_required
    is computed automatically (α=0.05 two-tailed, 80% power, Spearman) and any
    manually-passed n_required is overridden (with a warning)."""
    if target_rho is not None:
        if str(REPO / "src") not in sys.path:
            sys.path.insert(0, str(REPO / "src"))
        from ztare.experiment_stats import n_required_for_rho
        auto_n = n_required_for_rho(target_rho)
        if n_required is not None and n_required != auto_n:
            print(f"WARNING: manual n_required={n_required} overridden by computed {auto_n} for ρ={target_rho}")
        n_required = auto_n
    conn = get_conn()
    conn.execute("""INSERT OR REPLACE INTO pre_registrations
        (prereg_id, primitive_base, phase, corpus, registered_at,
         hypothesis, null_hypothesis, expected_direction, expected_effect_size,
         n_required, n_planned, falsifiers, pass_gate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (prereg_id, primitive_base, phase, corpus,
         datetime.now(timezone.utc).isoformat(),
         hypothesis, null_hypothesis, expected_direction, expected_effect_size,
         n_required, n_planned, falsifiers, pass_gate))
    conn.commit(); conn.close()
    print(f"registered: {prereg_id}  (n_required={n_required})")


def prereg_resolve(prereg_id, verdict, notes, pilot_id=None):
    conn = get_conn()
    conn.execute("""UPDATE pre_registrations
        SET verdict = ?, verdict_notes = ?, pilot_id = ?, landed_at = ?
        WHERE prereg_id = ?""",
        (verdict, notes, pilot_id, datetime.now(timezone.utc).isoformat(), prereg_id))
    conn.commit(); conn.close()
    print(f"resolved: {prereg_id} → {verdict}")


def prereg_list():
    conn = get_conn()
    rows = conn.execute("""SELECT prereg_id, primitive_base, phase, corpus,
        n_planned, verdict, registered_at FROM pre_registrations
        ORDER BY registered_at DESC""").fetchall()
    if not rows: print("(no pre-registrations)"); return
    for r in rows:
        v = r["verdict"] or "PENDING"
        print(f"  [{v:<28}] {r['prereg_id']}  ({r['primitive_base']}/{r['phase']}/{r['corpus']}  N_planned={r['n_planned']})")
    conn.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    p_ic = sub.add_parser("ingest-corpus"); p_ic.add_argument("path")
    p_ip = sub.add_parser("ingest-pilot"); p_ip.add_argument("path")
    sub.add_parser("ingest-all")
    p_q = sub.add_parser("query"); p_q.add_argument("sql")
    sub.add_parser("stats")
    p_pa = sub.add_parser("prereg-add")
    p_pa.add_argument("--id", required=True)
    p_pa.add_argument("--primitive", required=True)
    p_pa.add_argument("--phase", required=True, choices=["smoke", "full"])
    p_pa.add_argument("--corpus", required=True)
    p_pa.add_argument("--hypothesis", required=True)
    p_pa.add_argument("--null", required=True)
    p_pa.add_argument("--falsifiers", required=True)
    p_pa.add_argument("--direction"); p_pa.add_argument("--effect-size")
    p_pa.add_argument("--n-required", type=int); p_pa.add_argument("--n-planned", type=int)
    p_pa.add_argument("--target-rho", type=float,
                      help="if provided, n_required auto-computed for this ρ (α=0.05, 80% power, Spearman)")
    p_pa.add_argument("--pass-gate")
    p_pr = sub.add_parser("prereg-resolve")
    p_pr.add_argument("--id", required=True)
    p_pr.add_argument("--verdict", required=True,
                      choices=["h1_supported", "h0_kept", "inconclusive_underpowered", "invalid_run"])
    p_pr.add_argument("--notes", required=True)
    p_pr.add_argument("--pilot-id")
    sub.add_parser("prereg-list")

    args = ap.parse_args()
    if args.cmd == "init":
        init_db()
    elif args.cmd == "ingest-corpus":
        init_db(); ingest_corpus(args.path)
    elif args.cmd == "ingest-pilot":
        init_db(); ingest_pilot(args.path)
    elif args.cmd == "ingest-all":
        init_db(); ingest_all()
    elif args.cmd == "query":
        run_query(args.sql)
    elif args.cmd == "stats":
        stats()
    elif args.cmd == "prereg-add":
        init_db()
        prereg_add(args.id, args.primitive, args.phase, args.corpus,
                   args.hypothesis, args.null, args.falsifiers,
                   expected_direction=args.direction,
                   expected_effect_size=args.effect_size,
                   n_required=args.n_required, n_planned=args.n_planned,
                   pass_gate=args.pass_gate, target_rho=args.target_rho)
    elif args.cmd == "prereg-resolve":
        prereg_resolve(args.id, args.verdict, args.notes, args.pilot_id)
    elif args.cmd == "prereg-list":
        prereg_list()


if __name__ == "__main__":
    main()
