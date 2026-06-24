#!/usr/bin/env python3
"""One-time backfill: bank already-closed `closures/*.lean` proofs into a campaign warm-env file via the
canonical `family_lemma_library.bank_decl_to_env` (the helper-carry fix, 2026-06-24). Use when a run CLOSED
rungs but the (pre-fix) banking dropped them — re-bank from the saved closures so they become exact?/aesop-
citable on the next run, instead of re-deriving. NOT new banking logic — it drives the same canonical door.

  PYTHONPATH=src python scripts/public/control/leanmill/backfill_bank_closures.py <env.lean> <lean_root> <target...>
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.solver.family_lemma_library import bank_decl_to_env  # noqa: E402


def main() -> int:
    env, lean_root, targets = sys.argv[1], sys.argv[2], sys.argv[3:]
    closures = REPO / "ztare_proofs" / ".solver_scratch" / "closures"
    banked = 0
    for tgt in targets:
        f = closures / f"{tgt}.lean"
        if not f.exists():
            print(f"{tgt}: MISSING {f}", flush=True)
            continue
        try:
            r = bank_decl_to_env(env, tgt, f.read_text(encoding="utf-8"), lean_root)
            hb = r.get("helpers_banked") or []
            print(f"{tgt}: banked_as={r.get('banked_as')} reason={r.get('reason')} helpers_carried={len(hb)}", flush=True)
            if r.get("banked_as"):
                banked += 1
        except Exception as e:  # noqa: BLE001
            print(f"{tgt}: ERROR {repr(e)[:200]}", flush=True)
    print(f"BACKFILL DONE — {banked}/{len(targets)} banked", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
