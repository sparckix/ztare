"""leanmill failure triage — the deterministic, cheap layer of "replay + understand what went wrong".

The expensive part of an RCA (read the error, decide whether it's the MATH or the HARNESS) has a hard
deterministic core: a `failed_compile` whose error is a PARSE/ELABORATION error means the probe the move
assembled never parsed — so the move is broken, not the target. A well-formed probe can only fail with a
TACTIC error ("unsolved goals", "tactic failed") or a TIMEOUT. So:

    parse/elab error in a failed_compile  ==>  HARNESS BUG SUSPECT (not math)

Rolled up per move, this is a standing dead-instrument detector: a move whose failures are ~all parse
errors is silently dead (the bug that hid native_hammer's deadness for months — it never had a positive
control, and its failures were never classified). No LLM needed for this layer; it is a SQL scan + a
regex classifier. An LLM "replay" agent is the optional deluxe layer for the residual OTHER bucket.

Usage:
    python -m ztare.leanmill.failure_triage [--db PATH] [--json] [--target NAME] [--since ISO]
"""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import sys
from collections import Counter

# Deterministic error classes. Order matters: first match wins.
_CLASSES = [
    ("parse_elab", re.compile(
        r"unexpected token|unexpected identifier|expected ':'|expected term|expected command|"
        r"Function expected|Expected a fun|unexpected end of input|invalid 'import'|"
        r"unexpected '\)'|unterminated", re.I)),
    ("timeout", re.compile(r"timeout|timed out|deadline", re.I)),
    ("no_proof", re.compile(r"no lemma|no proof|missing goal|did not typecheck|no_advance", re.I)),
    ("tactic_failed", re.compile(
        r"unsolved goals|tactic '?\w+'? failed|simp made no progress|linarith failed|"
        r"aesop|ring failed|no goals|type mismatch|application type mismatch", re.I)),
]
HARNESS_SUSPECT = {"parse_elab"}   # = the probe never parsed; the move/harness is broken, not the math


def classify(notes: str) -> str:
    s = notes or ""
    for name, rx in _CLASSES:
        if rx.search(s):
            return name
    return "other"


def triage(db_path: str, target: str | None = None, since: str | None = None) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    where = ["outcome='failed_compile'"]
    params: list = []
    if target:
        where.append("row_id LIKE ?"); params.append(f"%{target}%")
    if since:
        where.append("attempt_at >= ?"); params.append(since)
    rows = con.execute(
        f"SELECT row_id, move, provider, notes FROM attempts WHERE {' AND '.join(where)}", params
    ).fetchall()
    con.close()
    per_move: dict[str, Counter] = {}
    for r in rows:
        mv = r["move"] or r["provider"] or "?"
        per_move.setdefault(mv, Counter())[classify(r["notes"])] += 1
    report = {}
    for mv, c in per_move.items():
        failed = sum(c.values())
        harness = sum(c[k] for k in HARNESS_SUSPECT)
        pct = round(100 * harness / failed) if failed else 0
        verdict = ("DEAD INSTRUMENT — probe never parses (harness bug, not math)"
                   if failed >= 5 and pct >= 80 else
                   ("harness errors present" if harness else "errors look like real math/tactic failures"))
        report[mv] = {"failed": failed, "harness_suspect": harness, "pct_harness": pct,
                      "by_class": dict(c), "verdict": verdict}
    return dict(sorted(report.items(), key=lambda kv: -kv[1]["failed"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--target", default=None)
    ap.add_argument("--since", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit", nargs="?", const="analytics/public/queries/leanmill_failure_triage.json",
                    default=None, help="write the triage JSON to a path for factory-intelligence surfacing")
    a = ap.parse_args()
    db = a.db
    if not db:
        sys.path.insert(0, "src")
        from ztare.leanmill.solver import solver_core as sc
        db = str(sc.ATTEMPTS_DB)
    rep = triage(db, a.target, a.since)
    if a.emit:
        import os
        os.makedirs(os.path.dirname(a.emit) or ".", exist_ok=True)
        dead = [m for m, d in rep.items() if d["verdict"].startswith("DEAD")]
        with open(a.emit, "w") as fh:
            json.dump({"moves": rep, "dead_instruments": dead}, fh, indent=2)
        print(f"emitted triage -> {a.emit} (dead instruments: {dead or 'none'})")
        if not a.json:
            return 0
    if a.json:
        print(json.dumps(rep, indent=2)); return 0
    print(f"{'move':<18}{'failed':>8}{'harness':>9}{'%':>5}   verdict")
    for mv, d in rep.items():
        print(f"{mv:<18}{d['failed']:>8}{d['harness_suspect']:>9}{d['pct_harness']:>4}%   {d['verdict']}")
    dead = [m for m, d in rep.items() if d["verdict"].startswith("DEAD")]
    if dead:
        print(f"\n⚠ DEAD INSTRUMENTS: {', '.join(dead)} — fix the probe assembly, re-validate with a positive control.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
