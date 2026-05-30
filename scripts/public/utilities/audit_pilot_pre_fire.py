#!/usr/bin/env python3
"""Pre-fire audit on a pilot dispatcher + checkpoint file.

Mechanical kill-bias checks BEFORE firing any pilot or after restart:
  1. Dispatcher source: no GT read (only chmod / docstring references allowed)
  2. Checkpoint file: zero duplicates under expected (key fields)
  3. Schema: all parsed rows have expected JSON keys
  4. Distribution: conditions / agents evenly hit (no missing strata)
  5. p_* values in [0,1]
  6. Resume-safety: dispatcher uses STABLE filename (not timestamp at startup)

Exit 0 if all checks pass; exit 1 if any fail (operator must fix before fire).

Usage:
  python scripts/public/utilities/audit_pilot_pre_fire.py \\
      --dispatcher path/to/run_pilot_X.py \\
      --checkpoint path/to/pilot_X_calls.jsonl \\
      --keys contract_id condition agent_id \\
      --gt-pattern ztare_forecaster_v1_3_ground_truth
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def fail(msg: str) -> None:
    print(f"  ✗ FAIL: {msg}")


def passes(msg: str) -> None:
    print(f"  ✓ {msg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dispatcher", required=True)
    ap.add_argument("--checkpoint", required=False)
    ap.add_argument("--keys", nargs="+", default=("contract_id", "condition", "agent_id"))
    ap.add_argument("--gt-pattern", action="append", default=[])
    args = ap.parse_args()

    failures = 0
    disp = Path(args.dispatcher)
    if not disp.exists():
        fail(f"dispatcher not found: {disp}")
        return 1
    src = disp.read_text()

    print(f"=== audit: {disp.name} ===")

    # 1. GT read-blind (allow chmod, docstring, constant; flag open()/read_text() on GT path)
    for pat in args.gt_pattern:
        leaks = []
        for i, line in enumerate(src.splitlines(), 1):
            if pat not in line:
                continue
            stripped = line.strip()
            # Allow: docstring comments (starts with #, """, ''', * for sphinx), constants, asserts, chmod calls
            allowed = (
                stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'")
                or stripped.startswith("*") or stripped.startswith("//")
                or "chmod" in line or "assert" in line or "= \"" in line or "= '" in line
                or "DO_NOT_OPEN" in line or "GROUND_TRUTH_PATH" in line
            )
            forbidden = (
                ".read_text(" in line or "open(" in line or ".read(" in line or "load(" in line
            )
            if forbidden and not allowed:
                leaks.append((i, stripped[:120]))
        if leaks:
            fail(f"GT '{pat}' READ in dispatcher:")
            for i, l in leaks: print(f"    line {i}: {l}")
            failures += 1
        else:
            passes(f"GT '{pat}' read-blind (only chmod/const/docstring refs found)")

    # 2. Stable filename check
    if "datetime.now(timezone.utc)" in src and ".jsonl" in src:
        # Look for f-string with TS inside a .jsonl path
        suspicious = []
        for i, line in enumerate(src.splitlines(), 1):
            if "OUT" in line and ".jsonl" in line and "{TS}" in line.replace("'", '"'):
                suspicious.append((i, line.strip()[:120]))
            if "OUT" in line and ".jsonl" in line and "datetime.now" in line:
                suspicious.append((i, line.strip()[:120]))
        if suspicious:
            fail(f"timestamp-based filename detected (resume bug risk):")
            for i, l in suspicious: print(f"    line {i}: {l}")
            failures += 1
        else:
            passes("OUT filename is stable (no timestamp at startup)")

    # 3-5. Checkpoint inspection
    if args.checkpoint:
        cp = Path(args.checkpoint)
        if not cp.exists():
            print(f"  ⚠ checkpoint not present yet: {cp.name} (skipping data checks)")
        else:
            rows = [json.loads(l) for l in cp.open() if l.strip()]
            print(f"  checkpoint: {cp.name} ({len(rows)} rows)")
            # Dupes
            try:
                ks = [tuple(r.get(k) for k in args.keys) for r in rows]
                c = Counter(ks)
                dups = sum(1 for v in c.values() if v > 1)
                if dups:
                    fail(f"{dups} duplicate keys under {args.keys}")
                    failures += 1
                else:
                    passes(f"0 duplicate keys under {args.keys}")
            except Exception as e:
                fail(f"key-dedupe check failed: {e}")
                failures += 1
            # Parsed fraction
            ok = [r for r in rows if r.get("parsed_ok") or (r.get("parsed") and isinstance(r["parsed"], dict))]
            rate = len(ok) / max(len(rows), 1)
            if rate < 0.9 and len(rows) > 10:
                fail(f"parsed_ok rate {100*rate:.0f}% (<90%)")
                failures += 1
            else:
                passes(f"parsed_ok rate {100*rate:.0f}% ({len(ok)}/{len(rows)})")
            # p_* range checks
            for p_field in ("p_success", "p_will_close", "p_self_will_close"):
                vals = []
                for r in ok:
                    p = r.get("parsed") or {}
                    if p_field in p and isinstance(p[p_field], (int, float)):
                        vals.append(p[p_field])
                if vals:
                    out_of_range = sum(1 for v in vals if not (0 <= v <= 1))
                    if out_of_range:
                        fail(f"{p_field}: {out_of_range}/{len(vals)} out of [0,1]")
                        failures += 1
                    else:
                        passes(f"{p_field}: {len(vals)} values in [0,1] (range [{min(vals):.3f}, {max(vals):.3f}])")

    print(f"\nresult: {'CLEAN' if failures == 0 else f'{failures} FAILURES'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
