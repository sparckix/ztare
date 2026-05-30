#!/usr/bin/env python3
"""Validate analytics/public/forecast_pool/contracts/*.json SCHEMA (GAP-D).

GAP-D (2026-05-15): `forecast_pool.py daemon-once` does
`require_fields(contract, REQUIRED_CONTRACT_FIELDS)` and raises SystemExit
on the FIRST malformed contract — so one bad contract from a concurrent
session aborts the entire GP-230 market re-derivation (observed:
`gp225_v2001_fresh_clean_topology_replay` missing 13 fields blocked the
whole daemon). Same unguarded-artifact class as GAP-A (architecture
index) — a derive-pipeline with no schema gate in front of it.

This validator is that gate. It reuses `forecast_pool.REQUIRED_CONTRACT_FIELDS`
by import (single source of truth — anti-drift; do NOT re-hardcode the
list). Exit 1 if any contract is malformed, naming each offender + its
missing fields, so the daemon never has to discover this fatally.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACTS = REPO / "analytics/public/forecast_pool/contracts"
FP = REPO / "scripts/public/control/forecast/pool.py"
LAYERS = {"micro", "meso", "macro"}


def _required_fields() -> set[str]:
    """Import the canonical set from forecast_pool (no __main__ run)."""
    spec = importlib.util.spec_from_file_location("fp_schema", FP)
    m = importlib.util.module_from_spec(spec)
    sys.modules["fp_schema"] = m
    spec.loader.exec_module(m)  # type: ignore[attr-defined]
    return set(m.REQUIRED_CONTRACT_FIELDS)


def main() -> int:
    if not CONTRACTS.exists():
        print(f"FATAL: contracts dir not found at {CONTRACTS}", file=sys.stderr)
        return 1
    try:
        required = _required_fields()
    except Exception as e:
        print(f"FATAL: could not import REQUIRED_CONTRACT_FIELDS: {e}",
              file=sys.stderr)
        return 1

    hard: list[str] = []
    ids: dict[str, str] = {}
    n = 0
    for cf in sorted(CONTRACTS.glob("*.json")):
        n += 1
        try:
            d = json.loads(cf.read_text(errors="ignore"))
        except json.JSONDecodeError as e:
            hard.append(f"{cf.name}: JSON parse error: {e}")
            continue
        missing = sorted(f for f in required if f not in d or d[f] in (None, ""))
        if missing:
            hard.append(f"{cf.name}: missing required fields "
                        f"{missing} (this is what aborts daemon-once)")
        cid = d.get("contract_id")
        if cid:
            if cid in ids:
                hard.append(f"{cf.name}: duplicate contract_id '{cid}' "
                            f"(also {ids[cid]})")
            else:
                ids[cid] = cf.name
        lyr = str(d.get("layer", "")).lower()
        if lyr and lyr not in LAYERS:
            hard.append(f"{cf.name}: layer '{d.get('layer')}' not in "
                        f"{sorted(LAYERS)}")

    print("=== forecast_pool/contracts/*.json schema validation (GAP-D) ===")
    print(f"contracts: {n} | unique contract_ids: {len(ids)} | "
          f"required fields (from forecast_pool): {len(required)}")
    if hard:
        print(f"FAIL — {len(hard)} malformed (these abort daemon-once / "
              f"block GP-230 market re-derive):")
        for x in hard:
            print(f"  - {x}")
        return 1
    print("OK — all contracts schema-valid; daemon-once will not abort.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
