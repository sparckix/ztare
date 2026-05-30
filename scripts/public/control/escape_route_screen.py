#!/usr/bin/env python3
"""escape_route_screen.py — deterministic v4.29.0 rigor gate for the
escape-route ablation (operator-authorized, post-Meta-Darwin).

For each candidate (a genuinely-new post-v4.29.0 Mathlib lemma whose
statement is old-vocab-expressible):
  1. TYPECHECK under pinned v4.29.0 ( `:= by sorry` ) -> confirms the
     statement uses only v4.29.0 vocabulary (no newer defs).
  2. AUTOMATION-SCREEN: try exact? / nlinarith / simp_all / aesop /
     positivity. If ANY closes it from pinned Mathlib, it is
     false-escape (relocated classic or automation-trivial) -> DROP.
A candidate is a CLEAN escape-route row iff typecheck OK AND no
automation closes it. No paid LLM here — this is the gate BEFORE the
gpt-4.1-mini generator run.

Same sandbox as the generator (v28A_carleson_baseline/carleson, pinned
Mathlib v4.29.0) so screen and run share one pinned env.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SANDBOX = REPO / "analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson"
OUT = REPO / "analytics/public/leanmill/escape_route/escape_route_screen_results.json"

PREAMBLE = "import Mathlib\nopen scoped Nat\nopen Real\n\n"

# Exact statements transcribed from mathlib4 master (files provably added
# after v4.29.0): SumIntegralExpDecay.lean (4) + Pentagonal.lean
# (old-vocab restatement of the genuinely-new pentagonal_strictMonoOn).
CANDIDATES = {
 "ER_SIE1_intervalIntegral_pow_exp":
   "example {k : ℕ} {M c : ℝ} (hM : 0 ≤ M) (hc : 0 < c) : "
   "(∫ x in (0:ℝ)..M, x ^ k * Real.exp (-(c * x))) ≤ (Nat.factorial k : ℝ) / c ^ (k + 1)",
 "ER_SIE2_sum_Ico_pow_exp":
   "example {k M : ℕ} {c : ℝ} (hc : 0 < c) : "
   "(∑ i ∈ Finset.Ico 0 M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1)",
 "ER_SIE3_sum_Iic_pow_exp":
   "example {k M : ℕ} {c : ℝ} (hc : 0 < c) : "
   "(∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1)",
 "ER_SIE4_sum_Iic_pow_twopow":
   "example {k M : ℕ} {c : ℝ} (hc : 0 < c) : "
   "(∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * (2:ℝ) ^ (-(c * i))) ≤ (2:ℝ) ^ c * (Nat.factorial k:ℝ) / (Real.log 2 * c) ^ (k+1)",
 "ER_PENT_strictMonoOn":
   "example : StrictMonoOn (fun k : ℤ => k * (3 * k - 1) / 2) (Set.Ici (0:ℤ))",
}
TACTICS = ["exact?", "nlinarith", "simp_all", "aesop", "positivity",
           "norm_num", "decide"]


def _compile(src: str, timeout: int = 120) -> tuple[bool, str]:
    import tempfile, os
    fd, p = tempfile.mkstemp(suffix=".lean", dir=str(SANDBOX))
    try:
        os.write(fd, src.encode()); os.close(fd)
        r = subprocess.run(["lake", "env", "lean", os.path.basename(p)],
                            cwd=str(SANDBOX), capture_output=True,
                            text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and "error:" not in out
        return ok, out[-400:]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    finally:
        try: os.unlink(p)
        except Exception: pass


def main() -> int:
    results = {}
    for name, stmt in CANDIDATES.items():
        rec = {"typecheck": None, "automation_closed_by": None,
               "clean_escape_route": False}
        tc_ok, tc_tail = _compile(PREAMBLE + stmt + " := by sorry")
        rec["typecheck"] = tc_ok
        if not tc_ok:
            rec["note"] = "statement does NOT typecheck under v4.29.0 " \
                          "(needs newer vocab) — not a clean old-vocab row"
            rec["tail"] = tc_tail
            results[name] = rec
            print(f"{name}: typecheck=FAIL (drop)"); continue
        closer = None
        for t in TACTICS:
            ok, _ = _compile(PREAMBLE + stmt + f" := by {t}")
            if ok:
                closer = t; break
        rec["automation_closed_by"] = closer
        rec["clean_escape_route"] = closer is None
        results[name] = rec
        print(f"{name}: typecheck=OK automation={'CLOSED by '+closer if closer else 'none -> CLEAN escape-route'}")
    clean = [k for k, v in results.items() if v["clean_escape_route"]]
    payload = {"sandbox_mathlib": "v4.29.0",
               "n_candidates": len(CANDIDATES),
               "n_clean_escape_route": len(clean),
               "clean_rows": clean, "detail": results,
               "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n=> {len(clean)}/{len(CANDIDATES)} clean escape-route rows: {clean}")
    print(f"=> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
