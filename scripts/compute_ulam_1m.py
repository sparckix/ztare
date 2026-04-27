#!/usr/bin/env python3
"""Compute Ulam numbers using direct representation counting.

Counts the number of ways each candidate can be written as a sum of two
distinct earlier Ulam numbers. Accepts if exactly 1 way. Early termination
at ways > 1 for speed. Verified against OEIS A002858 first 30 terms.

Run: nohup python scripts/compute_ulam_1m.py > ulam_1m.log 2>&1 &
Safe to interrupt and resume. Checkpoints every 10K.

Expected times (from benchmarks):
  10K: ~12 seconds
  100K: ~20 minutes
  1M: ~33 hours
"""

import json
import time
from pathlib import Path

TARGET = 1_000_000
CHECKPOINT_EVERY = 10_000
OUTPUT_DIR = Path("projects/gp088_oeis_a002858")
CHECKPOINT_PATH = OUTPUT_DIR / "ulam_checkpoint.json"
FINAL_PATH = OUTPUT_DIR / "ulam_1m.json"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load checkpoint or start fresh
    if CHECKPOINT_PATH.exists():
        data = json.loads(CHECKPOINT_PATH.read_text())
        ulam = data["ulam"]
        candidate = data["next_candidate"]
        print(f"Resumed: {len(ulam):,d} numbers, candidate {candidate:,d}")
    else:
        ulam = [1, 2]
        candidate = 3
        print("Fresh start")

    ulam_set = set(ulam)
    start = time.time()
    n_at_start = len(ulam)

    while len(ulam) < TARGET:
        # Count representations as sum of two DISTINCT earlier Ulam numbers
        ways = 0
        for u in ulam:
            if u >= candidate:
                break
            complement = candidate - u
            if complement != u and complement in ulam_set and complement > u:
                ways += 1
                if ways > 1:
                    break  # early termination — not Ulam

        if ways == 1:
            ulam.append(candidate)
            ulam_set.add(candidate)

            n = len(ulam)
            if n % 1000 == 0:
                elapsed = time.time() - start
                done = n - n_at_start
                rate = done / elapsed if elapsed > 0 else 1
                eta = (TARGET - n) / rate if rate > 0 else 0
                print(
                    f"  {n:>8,d} / {TARGET:,d}  "
                    f"U={candidate:>10,d}  "
                    f"{elapsed:>7.0f}s  "
                    f"ETA {eta:>7.0f}s ({eta/3600:.1f}h)"
                )

            if n % CHECKPOINT_EVERY == 0:
                CHECKPOINT_PATH.write_text(json.dumps({
                    "ulam": ulam,
                    "next_candidate": candidate + 1,
                }))
                print(f"    💾 Checkpoint ({n:,d})")

        candidate += 1

    elapsed = time.time() - start
    print(f"\nDone: {len(ulam):,d} in {elapsed:.1f}s ({elapsed/3600:.1f}h)")
    print(f"U({len(ulam)}) = {ulam[-1]:,d}")

    FINAL_PATH.write_text(json.dumps(ulam))
    print(f"Saved to {FINAL_PATH}")

    # Evidence files
    def write_ev(path, indices, header):
        with open(path, "w") as f:
            f.write(f"# {header}\n# n\tz\n")
            for i in indices:
                f.write(f"{i+1}\t{ulam[i]/(i+1)}\n")

    n_ulam = len(ulam)
    write_ev(OUTPUT_DIR / "evidence_1m_visible.txt",
             range(9999, min(100000, n_ulam)), "visible n=10000..100000")
    write_ev(OUTPUT_DIR / "evidence_1m_holdout.txt",
             range(100000, min(500000, n_ulam)), "holdout n=100001..500000")
    write_ev(OUTPUT_DIR / "evidence_1m_farther.txt",
             range(500000, min(n_ulam, 1000000)), "farther n=500001..1000000")
    print("Evidence files written")

    CHECKPOINT_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
