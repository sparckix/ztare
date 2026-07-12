#!/usr/bin/env python3
"""GP-250 P0' check: run the pre-registered world-model harness (BC-0/1').

Offline and deterministic: sealed synthetic environments, no model calls, no
network. Exits non-zero unless every pre-registered threshold in
`ztare.worldmodel.harness` passes. See
research_areas/seams/substrates/arc/GP-250_arc_agi_3_interactive_program_synthesis_seam.md.

Usage:
    python scripts/public/control/worldmodel_p0_check.py [--json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.worldmodel.harness import run_harness  # noqa: E402


def main() -> int:
    report = run_harness()
    if "--json" in sys.argv[1:]:
        print(json.dumps(report, indent=2))
    else:
        v = report["verdict"]
        print("worldmodel P0' harness")
        for row in report["recovery"]:
            mark = "ok " if (row["recovered"] or (not row["expressible"] and row["status"] == "grammar_ceiling")) else "FAIL"
            print(f"  {mark} {row['env_id']:<28} status={row['status']} committee={row['committee_size']}")
        for row in report["efficiency"]:
            print(f"  eff {row['env_id']:<28} eig={row['eig_median']} random={row['random_median']} ratio={row['ratio']}")
        for row in report["bc1pp"]:
            print(f"  bc1 {row['env_id']:<28} composite={row['eig_median']} random={row['random_median']} ratio={row['ratio']}")
        d = report["degenerate"]
        print(f"  deg {d['env_id']:<28} eig={d['eig_median']} random={d['random_median']}")
        print(f"  verdict: {json.dumps(v)}")
    return 0 if report["verdict"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
