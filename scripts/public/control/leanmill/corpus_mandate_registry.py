#!/usr/bin/env python3
"""leanmill_corpus_mandate_registry — operator-facing CLI over the typed
corpus_mandate contract.

The kernel API lives in `src/ztare/leanmill/contracts/corpus_mandate.py`. This
script is the operator surface for listing, validating, and propagating the
registry into the seed plan's legacy `active_corpus_paths` field so existing
scout workers consume it transparently.

CLI:
  --list                  Show all mandates + status/lanes/row counts.
  --validate              Run registry validation; nonzero exit on errors.
  --apply-to-seed-plan    Rewrite `active_corpus_paths` in the source-scout
                          seed plan from active mandates with `source_scout`
                          in `lane_eligibility`. Backs up the prior plan.
  --self-test             Run kernel self-test.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Allow ztare imports when invoked as a CLI script.
REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.contracts.corpus_mandate import (  # noqa: E402
    REGISTRY_PATH,
    active_corpus_paths,
    active_mandates,
    mandate_by_id,
    read_registry,
    validate_registry,
)

SEED_PLAN_PATH = (
    REPO
    / "analytics/public/leanmill/dashboard_data/external_source_scout_seed_plan.json"
)


def _list(_args: argparse.Namespace) -> int:
    reg = read_registry()
    print(f"registry: {REGISTRY_PATH}")
    print(f"schema:   {reg.get('schema')}")
    print(f"mandates: {len(reg.get('mandates', []))}")
    print()
    for m in reg.get("mandates", []):
        lanes = ",".join(m.get("lane_eligibility") or [])
        credit = ",".join(m.get("credit_lanes_allowed") or [])
        print(
            f"  [{m.get('status'):>18}] {m.get('mandate_id'):<32} "
            f"rows={m.get('row_count'):>4}  lanes=[{lanes}]  credit=[{credit}]"
        )
        print(f"    corpus_path: {m.get('corpus_path')}")
    return 0


def _validate(_args: argparse.Namespace) -> int:
    reg = read_registry()
    errors = validate_registry(reg)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    print(f"OK: registry valid, mandates={len(reg.get('mandates', []))}")
    return 0


def _apply_to_seed_plan(args: argparse.Namespace) -> int:
    """Rewrite the seed plan's active_corpus_paths from the registry.

    Workers reading the seed plan field continue working transparently;
    the registry becomes the source of truth for which corpora are routed
    to the source-scout lane.
    """
    reg = read_registry()
    errors = validate_registry(reg)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1
    src_scout = active_mandates("source_scout")
    paths = [m["corpus_path"] for m in src_scout]
    if not SEED_PLAN_PATH.exists():
        print(f"ERROR: seed plan missing at {SEED_PLAN_PATH}")
        return 1
    seed = json.loads(SEED_PLAN_PATH.read_text())
    prior_paths = list(seed.get("active_corpus_paths") or [])

    if paths == prior_paths and not args.force:
        print(f"NO-OP: active_corpus_paths already matches registry")
        return 0

    if args.dry_run:
        print("DRY RUN — would set active_corpus_paths to:")
        for p in paths:
            print(f"  {p}")
        print("would archive prior to active_corpus_paths_previous:")
        for p in prior_paths:
            print(f"  {p}")
        return 0

    # Backup.
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = SEED_PLAN_PATH.with_suffix(f".backup-{stamp}.json")
    backup.write_text(json.dumps(seed, indent=2))

    seed["active_corpus_paths"] = paths
    seed["active_corpus_paths_previous"] = prior_paths
    seed["active_corpus_mandate_ids"] = [m["mandate_id"] for m in src_scout]
    seed["mandate_registry_path"] = str(
        REGISTRY_PATH.relative_to(REPO) if REGISTRY_PATH.is_relative_to(REPO) else REGISTRY_PATH
    )
    seed["mandate_registry_applied_at"] = stamp
    SEED_PLAN_PATH.write_text(json.dumps(seed, indent=2))

    print(f"OK: applied registry to {SEED_PLAN_PATH.name}")
    print(f"  active_corpus_paths now: {paths}")
    print(f"  active mandate_ids:      {[m['mandate_id'] for m in src_scout]}")
    print(f"  backup written:          {backup.name}")
    return 0


def _self_test(_args: argparse.Namespace) -> int:
    # Re-exec the kernel self-test for parity with the leanmill convention.
    from ztare.leanmill.contracts.corpus_mandate import _self_test as kernel_self_test

    return kernel_self_test()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--apply-to-seed-plan", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test(args)
    if args.list:
        return _list(args)
    if args.validate:
        return _validate(args)
    if args.apply_to_seed_plan:
        return _apply_to_seed_plan(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
