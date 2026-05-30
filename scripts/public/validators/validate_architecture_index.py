#!/usr/bin/env python3
"""Validate analytics/public/index/architecture_index.jsonl SCHEMA.

GAP-A fix (2026-05-15): render_architecture_index.py does HARD key access
(`row['impact_factor_expost']`) and CRASHED on a concurrent session's
malformed META-PATTERN-024 row — silently breaking the discoverability
surface the RD mandate depends on. render only checked path existence,
never schema. This validator is the missing schema gate.

Exit 0 if every row is schema-valid, 1 otherwise. Path-existence is
reported as WARN (the 38 missing-path rows are known separate debt;
schema breakage is the hard failure that crashes render).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INDEX = REPO / "analytics/public/index/architecture_index.jsonl"
REQUIRED = ["id", "path", "kind", "description", "applicability",
            "impact_factor_expost", "last_used", "dependencies"]
KINDS = {"gate", "op", "mining", "primitive", "pattern", "anti-pattern",
         "meta-pattern", "reflexive_primitive", "validator", "orchestrator",
         "script"}


def main() -> int:
    if not INDEX.exists():
        print(f"FATAL: index not found at {INDEX}", file=sys.stderr)
        return 1
    hard: list[str] = []
    warn: list[str] = []
    ids: dict[str, int] = {}
    n = 0
    for ln, raw in enumerate(INDEX.read_text().splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        n += 1
        try:
            r = json.loads(raw)
        except json.JSONDecodeError as e:
            hard.append(f"line {ln}: JSON parse error: {e}")
            continue
        rid = r.get("id", f"<line {ln}>")
        for f in REQUIRED:
            if f not in r:
                hard.append(f"{rid}: missing required key '{f}' "
                            "(this is exactly what crashes render_architecture_index)")
        if "id" in r:
            if rid in ids:
                hard.append(f"{rid}: duplicate id (also line {ids[rid]})")
            else:
                ids[rid] = ln
        if r.get("kind") not in KINDS:
            hard.append(f"{rid}: kind '{r.get('kind')}' not in {sorted(KINDS)}")
        if "impact_factor_expost" in r and not isinstance(
                r["impact_factor_expost"], int):
            hard.append(f"{rid}: impact_factor_expost must be int")
        if "applicability" in r and not isinstance(r["applicability"], list):
            hard.append(f"{rid}: applicability must be a list")
        if "dependencies" in r and not isinstance(r["dependencies"], list):
            hard.append(f"{rid}: dependencies must be a list")
        if "path" in r and not (REPO / r["path"]).exists():
            warn.append(f"{rid}: path missing on disk: {r['path']}")

    print("=== architecture_index.jsonl schema validation ===")
    print(f"rows: {n} | unique ids: {len(ids)} | "
          f"path-missing (known separate debt): {len(warn)}")
    if hard:
        print(f"FAIL — {len(hard)} schema error(s) (these break render):")
        for x in hard:
            print(f"  - {x}")
        return 1
    print("OK — schema valid; render_architecture_index will not crash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
