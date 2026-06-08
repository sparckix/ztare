#!/usr/bin/env python3
"""One-command substrate canary — run BEFORE trusting any Lean proof-search result.

Prevents the 2026-06-01 'going blind' failure (a toolchain-mismatched REPL silently
returned an empty env, so every probe errored and we read '0 closed' as a solver verdict).
This spawns the real PersistentLean over a project, runs the full calibration
(toolchain match + positive controls + verifier false-accept guard + sorry-gate guard)
through the SAME code path real probes use, and prints GREEN/RED. Exit code is nonzero
when the substrate is dead, so it can gate experiments and CI.

  python3 verify_substrate.py --project-dir projects/atlas_lean_2026_05_29
  python3 verify_substrate.py --project-dir ztare_proofs          # expected RED (mismatch)

Self-contained: no args beyond the project dir; emits a JSON line too for ledgering.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True,
                    help="lake project whose Mathlib the repl loads (must match repl toolchain)")
    ap.add_argument("--repl-bin", default=None, help="override repl binary path")
    ap.add_argument("--json", action="store_true", help="emit only the JSON report line")
    a = ap.parse_args()

    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import (
        calibrate, toolchain_match, SubstrateDeadError)

    proj = str((REPO / a.project_dir).resolve()
               if not Path(a.project_dir).is_absolute() else Path(a.project_dir))
    repl_bin = a.repl_bin or str(PersistentLean(project_dir=proj).repl_bin)

    # Layer 1 first (deterministic, no spawn) — cheapest catch of the exact RCA.
    m, rtc, ptc = toolchain_match(repl_bin, proj)
    if not a.json:
        print(f"[verify-substrate] layer-1 toolchain: repl={rtc!r} project={ptc!r} "
              f"=> {'MATCH' if m else 'MISMATCH'}", flush=True)

    t0 = time.time()
    try:
        with PersistentLean(project_dir=proj, repl_bin=repl_bin) as pl:
            import_s = time.time() - t0
            rep = calibrate(pl, import_seconds=import_s)
            if a.json:
                print(json.dumps(rep.to_dict()))
            else:
                print(rep.banner())
            sys.exit(0)
    except SubstrateDeadError as e:
        # PersistentLean._spawn may raise before calibrate() (its own positive control),
        # or calibrate() raises with a full report banner.
        if a.json:
            print(json.dumps({"alive": False, "toolchain_match": m,
                              "toolchain_repl": rtc, "toolchain_project": ptc,
                              "error": str(e)}))
        else:
            print(f"[verify-substrate] RED ❌ DEAD — {e}")
        sys.exit(2)
    except RuntimeError as e:
        # _spawn's _assert_prelude_live raises plain RuntimeError on a dead prelude.
        if a.json:
            print(json.dumps({"alive": False, "toolchain_match": m,
                              "toolchain_repl": rtc, "toolchain_project": ptc,
                              "error": str(e)}))
        else:
            print(f"[verify-substrate] RED ❌ DEAD — {str(e)[:300]}")
        sys.exit(2)


if __name__ == "__main__":
    main()
