#!/usr/bin/env python3
"""remediate_catch_ledger.py — integrity-PRESERVING remediation of
analytics/public/ledgers/catch/catch_ledger.jsonl.

Principle (SOX §1220 independence — see catch_ledger_schema.md):
a catch that never had an independent concurring agent / valid
`ratified_at` was NEVER validly ratified. The honest remediation is to
DEMOTE it (status -> pending), NOT to back-fill a fabricated concurring
agent / timestamp. Fabrication would launder the very independence
assertion the ledger exists to protect. This script therefore makes the
TALLY honest; it deliberately does NOT chase a green validator (genuinely
malformed historical rows stay flagged — that is the truthful state).

Deterministic rules (no judgement, no fabrication):
  R1 independence-blocked  -> status=pending, concurring_agent=pending
       (missing/null concurring_agent OR ratified_at, OR
        author_agent == concurring_agent)
  R2 duplicate catch_id    -> keep the most-complete row; the other(s)
       become status=retired + superseded_by=<canonical id> (tombstone,
       never deleted — append-only spirit preserved)
  R3 status not in enum    -> status=pending (unknown != ratified)
Each mutated row gets a `remediation` provenance note (audit trail —
silent mutation of an audit ledger is itself bad practice).

Reversibility: file is git-tracked; --apply writes in place; default is
dry-run (prints the would-be diff + honest new tally).

Usage:
  python3 scripts/public/control/remediate_catch_ledger.py            # dry-run
  python3 scripts/public/control/remediate_catch_ledger.py --apply
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
NOTE = f"demoted {date.today().isoformat()} by remediate_catch_ledger.py (integrity-preserving; not re-ratified — needs independent concurrer)"

REQUIRED = ["catch_id", "title", "author_agent", "concurring_agent",
            "workpaper_paths", "load_bearing", "category", "fix_artifact",
            "ratified_at", "status"]
VALID_STATUS = {"pending", "ratified", "retired"}


def _completeness(r: dict) -> int:
    return sum(1 for f in REQUIRED if r.get(f) not in (None, "", []))


def _independence_blocked(r: dict) -> bool:
    ca = r.get("concurring_agent")
    ra = r.get("ratified_at")
    if ca in (None, "") or ra in (None, ""):
        return True
    if r.get("author_agent") and r.get("author_agent") == ca:
        return True
    return False


def remediate(rows: list[dict]) -> tuple[list[dict], Counter]:
    acts: Counter = Counter()
    # R2: duplicate ids — pick canonical = most complete (first wins ties)
    by_id: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by_id.setdefault(r.get("catch_id", f"<noid-{i}>"), []).append(i)
    tombstone: dict[int, str] = {}
    for cid, idxs in by_id.items():
        if len(idxs) < 2:
            continue
        canon = max(idxs, key=lambda j: _completeness(rows[j]))
        for j in idxs:
            if j != canon:
                tombstone[j] = cid
    out = []
    for i, r in enumerate(rows):
        r = dict(r)
        if i in tombstone:
            r["status"] = "retired"
            r["superseded_by"] = tombstone[i]
            r["remediation"] = f"duplicate-id tombstone -> {tombstone[i]}; {NOTE}"
            acts["R2_duplicate_retired"] += 1
        elif _independence_blocked(r):
            r["status"] = "pending"
            if r.get("concurring_agent") in (None, ""):
                r["concurring_agent"] = "pending"
            r["remediation"] = f"independence-blocked; {NOTE}"
            acts["R1_independence_demoted"] += 1
        elif r.get("status") not in VALID_STATUS:
            r["remediation"] = f"status '{r.get('status')}' invalid -> pending; {NOTE}"
            r["status"] = "pending"
            acts["R3_bad_status_demoted"] += 1
        else:
            acts["unchanged"] += 1
        out.append(r)
    return out, acts


def tally(rows: list[dict]) -> dict:
    c = Counter(r.get("status") for r in rows)
    honest_ratified = sum(
        1 for r in rows
        if r.get("status") == "ratified"
        and not _independence_blocked(r)
        and r.get("load_bearing") is True
    )
    return {"by_status": dict(c), "honest_load_bearing_ratified": honest_ratified}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    before = tally(rows)
    new, acts = remediate(rows)
    after = tally(new)
    print("=== catch_ledger remediation (integrity-preserving) ===")
    print(f"  rows: {len(rows)}")
    print(f"  actions: {dict(acts)}")
    print(f"  BEFORE status: {before['by_status']} | "
          f"cited-but-suspect decision-critical ratified: {before['honest_load_bearing_ratified']}")
    print(f"  AFTER  status: {after['by_status']} | "
          f"HONEST decision-critical ratified: {after['honest_load_bearing_ratified']}")
    print("  (genuinely-malformed historical rows remain flagged by the "
          "validator — that is the truthful state; green-by-fabrication "
          "would be laundering)")
    if a.apply:
        LEDGER.write_text("".join(json.dumps(r) + "\n" for r in new))
        print(f"  APPLIED -> {LEDGER.relative_to(REPO)} (git-tracked; reversible)")
    else:
        print("  DRY-RUN (no write). Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
