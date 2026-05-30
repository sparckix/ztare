#!/usr/bin/env python3
"""known_possible_run.py — solver-0 corpus fix (PL-367).

The escape-route corpus tested only genuinely-OPEN hard analysis lemmas
(0/5 closed across two prover tiers). The reframe explicitly allowed
"rows where closure is KNOWN POSSIBLE". This runs the SAME route_c
residual-to-lever loop on v30_benchmark rows that carry a `gold_proof_body`
(closure proven to exist) and are non-trivial multi-step compositions —
to isolate "can the loop close when closure EXISTS" from "can it close
open math".

The loop is fed GOAL ONLY (route_c semantic-masking); gold_proof_body is
NEVER shown to it — no leakage. Any compile still passes v33 downstream
(blunt-nlinarith ≠ loop composition). Reuses the v30 curated corpus
(no re-transcription) + the route_c dispatch (no new detectors).
"""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DISPATCH = ROOT / "scripts/public/control/route_c_layer_2c_dispatch.py"
BENCH = ROOT / "analytics/public/leanmill/results/v30_benchmark_27_rows.json"
OUT = ROOT / "analytics/public/leanmill/results/known_possible_run_results_gpt41.json"
PICK = ["v30_A01_three_pow_ge_quad", "v30_A02_sq_plus_one_le_cube",
        "v30_A04_quartic_dominates", "v30_A06_two_pow_ge_cube",
        "v30_B01_carleson_style_thirtytwo"]


def main() -> int:
    d = json.load(open(BENCH))
    rows = d if isinstance(d, list) else d.get("rows") or list(d.values())[0]
    by_id = {r["row_id"]: r for r in rows}
    results = []
    for rid in PICK:
        r = by_id.get(rid)
        if not r:
            results.append({"row_id": rid, "status": "missing_in_benchmark"}); continue
        goal = r["goal_statement"].strip()
        rowf = Path(f"/tmp/kp_{rid}.lean")
        rowf.write_text(f"import Mathlib\n\nexample {goal} := by sorry\n")
        outj = Path(f"/tmp/kp_gpt41_{rid}.json")
        if not outj.exists():
            print(f"--- {rid}: dispatch (gpt-4.1, 3 rounds, compile) goal={goal[:60]} ---", flush=True)
            try:
                subprocess.run(["python3", str(DISPATCH), "--row", str(rowf),
                                "--max-rounds", "3", "--model", "gpt-4.1",
                                "--compile", "--out", str(outj)],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=900)
            except subprocess.TimeoutExpired:
                results.append({"row_id": rid, "status": "timeout_900s"}); continue
        try:
            j = json.load(open(outj))
            results.append({"row_id": rid,
                            "closure_verdict": j.get("closure_verdict"),
                            "compiled_any": j.get("compiled_any"),
                            "category_bucket": r.get("category_bucket"),
                            "gold_exists": True})
            print(f"  {rid}: {j.get('closure_verdict')} compiled_any={j.get('compiled_any')}", flush=True)
        except Exception as e:
            results.append({"row_id": rid, "status": f"read_error:{e}"})
    n_compiled = sum(1 for x in results if x.get("compiled_any") is True
                     or x.get("closure_verdict") == "CLOSED")
    OUT.write_text(json.dumps({
        "corpus": "v30 known-possible non-trivial (gold proof exists; goal-only to loop)",
        "n_rows": len(PICK), "n_compiled_raw": n_compiled,
        "note": ("raw compile NOT a closure until v33 anti-laundering pass "
                 "(blunt nlinarith != loop composition) — PL-367 pre-registered. "
                 "Closure-exists by construction (gold_proof_body), so 0 here "
                 "means a loop-composition deficit, not open-math hardness."),
        "results": results,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2) + "\n")
    print(f"\n=> known-possible raw compiles: {n_compiled}/{len(PICK)} (v33 audit pending). {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
