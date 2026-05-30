#!/usr/bin/env python3
"""
score_pattern_deployment_diversity.py

PATTERN-013 implementation. Reads
`analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl` and computes rolling-window
diversity metrics. Emits monoculture / structural-blind-spot / audit-
share / external-share / eigenquestion-share flags.

Operator catch (2026-05-09): RD was deploying PATTERN-001 ~12/17
dispatches and PATTERN-009 ~0/17, which is exactly why the Lerner-2026
W6 port unfaithfulness (catch C-2026-05-09-59) had to be surfaced by
operator-relayed GPT-5.5 instead of by the RD's own dispatch.

Usage:
  python scripts/public/analytics_shared/score_pattern_deployment_diversity.py
  python scripts/public/analytics_shared/score_pattern_deployment_diversity.py --window 10
  python scripts/public/analytics_shared/score_pattern_deployment_diversity.py --emit-kill-on-monoculture
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


MONOCULTURE_THRESHOLD = 0.50
BLIND_SPOT_THRESHOLD = 0.05
AUDIT_SHARE_LOW = 0.20
AUDIT_SHARE_HIGH = 0.50
EXTERNAL_SHARE_MIN = 0.10
EIGENQUESTION_SHARE_MIN = 0.20


def load_ledger(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def compute_metrics(rows: list[dict], window: int) -> dict:
    cohort = rows[-window:] if len(rows) > window else rows
    n = len(cohort)
    if n == 0:
        return {"n": 0}

    primary_counter = Counter(r.get("primary_pattern", "UNKNOWN") for r in cohort)
    primary_shares = {p: c / n for p, c in primary_counter.items()}
    max_share = max(primary_shares.values()) if primary_shares else 0.0
    max_pattern = max(primary_shares, key=primary_shares.get) if primary_shares else None

    audit_modes = {"audit", "calibrate"}
    audit_share = sum(1 for r in cohort if r.get("audit_or_construct") in audit_modes) / n
    external_share = sum(1 for r in cohort if r.get("external_or_internal") == "external_via_operator") / n
    eigenq_share = sum(1 for r in cohort if r.get("eigenquestion_shape") is True) / n

    return {
        "n": n,
        "window": window,
        "primary_shares": primary_shares,
        "monoculture_flag": max_share > MONOCULTURE_THRESHOLD,
        "monoculture_max_share": round(max_share, 3),
        "monoculture_max_pattern": max_pattern,
        "audit_share": round(audit_share, 3),
        "audit_in_band": AUDIT_SHARE_LOW <= audit_share <= AUDIT_SHARE_HIGH,
        "external_share": round(external_share, 3),
        "external_in_band": external_share >= EXTERNAL_SHARE_MIN,
        "eigenquestion_share": round(eigenq_share, 3),
        "eigenquestion_in_band": eigenq_share >= EIGENQUESTION_SHARE_MIN,
    }


def compute_blind_spots(rows: list[dict], window: int = 20) -> list[str]:
    cohort = rows[-window:] if len(rows) > window else rows
    n = len(cohort)
    if n == 0:
        return []
    counter = Counter(r.get("primary_pattern", "UNKNOWN") for r in cohort)
    canonical = ["PATTERN-001", "PATTERN-002", "PATTERN-003", "PATTERN-004",
                 "PATTERN-005", "PATTERN-006", "PATTERN-007", "PATTERN-008",
                 "PATTERN-009", "PATTERN-010", "PATTERN-011", "PATTERN-012",
                 "PATTERN-013"]
    blind = []
    for p in canonical:
        share = counter.get(p, 0) / n
        if share < BLIND_SPOT_THRESHOLD:
            blind.append((p, round(share, 3)))
    return blind


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--emit-kill-on-monoculture", action="store_true")
    args = parser.parse_args()

    repo = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
    rows = load_ledger(repo / "analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl")
    if not rows:
        print("No pattern-deployment ledger rows yet.")
        return 0

    print(f"Pattern-deployment ledger: {len(rows)} rows")
    metrics = compute_metrics(rows, args.window)
    print(f"\nLast-{args.window} window:")
    print(f"  primary-pattern shares:")
    for p, s in sorted(metrics["primary_shares"].items(), key=lambda kv: -kv[1]):
        print(f"    {p}: {s:.3f}")
    print(f"  monoculture_flag = {metrics['monoculture_flag']} (max {metrics['monoculture_max_share']} on {metrics['monoculture_max_pattern']})")
    print(f"  audit_share = {metrics['audit_share']} (in-band {metrics['audit_in_band']})")
    print(f"  external_share = {metrics['external_share']} (in-band {metrics['external_in_band']})")
    print(f"  eigenquestion_share = {metrics['eigenquestion_share']} (in-band {metrics['eigenquestion_in_band']})")

    blind = compute_blind_spots(rows, window=20)
    if blind:
        print(f"\nStructural blind spots (last-20 share < {BLIND_SPOT_THRESHOLD}):")
        for p, s in blind:
            print(f"  {p}: {s}")

    summary = {
        "computed_at": "2026-05-09",
        "metrics": metrics,
        "blind_spots": blind,
    }
    (repo / "analytics/public/ledgers/pattern_deployment/pattern_deployment_diversity.json").write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written: analytics/public/ledgers/pattern_deployment/pattern_deployment_diversity.json")

    if args.emit_kill_on_monoculture and metrics["monoculture_flag"]:
        print("\nHARD KILL: monoculture flag fired. Block further dispatch until corrective.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
