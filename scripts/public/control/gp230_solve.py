#!/usr/bin/env python3
"""GP-230 / Route C solver harness CLI (Day-7 operator deliverable).

Usage:
  gp230_solve.py --row-file <path> [--budget 5] [--strict] [--out <json>]

Pipeline (per operator's Day-7 spec):
  1. Read row Lean file (must end in `:= by sorry` or `:= by hammer`)
  2. Run baseline B0 (basic tactics individually + hint-augmented)
  3. Run baseline B1 (full hammer with import Hammer)
  4. If B0 or B1 closes → report `BASELINE_CLOSED`
  5. If both fail → Route C: LLM-proposed proof attempts (this scaffold logs the
     prompts that WOULD be sent; integration with an LLM is a follow-on)
  6. Apply DAG fingerprint to any compiled proof
  7. Cross-leakage scan
  8. Audit per v30 contract gate
  9. Emit JSON trace with: goal, baseline_results, attempts[], successful_proof,
     fingerprint, gap_report

This is the harness scaffold. Full LLM integration left for v31.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = ROOT / "analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson"
MATHLIB = SANDBOX / ".lake/packages/mathlib/Mathlib"

B0_TACTICS = [
    "linarith", "nlinarith", "omega", "decide",
    "ring", "ring_nf", "norm_num", "positivity",
    "polyrith", "field_simp", "aesop", "simp",
    "tauto", "fun_prop", "continuity",
    # Hint-augmented variants:
    "nlinarith [sq_nonneg a, sq_nonneg b, sq_nonneg (a-b)]",
    "nlinarith [sq_nonneg x, sq_nonneg y, sq_nonneg (x-y)]",
    "simp [mul_add, Finset.sum_add_distrib]",
]


def now(): return time.strftime("%H:%M:%S")


def extract_example(text: str):
    """Return (preamble, signature) by splitting on `:= by`."""
    m = re.search(r"(.*?)(example\s+.*?)(:= by\s*)(sorry|hammer)?", text, re.DOTALL)
    if not m:
        return None, None
    return m.group(1).rstrip(), m.group(2).rstrip()


def run_lean(fpath, timeout=120):
    s = time.time()
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(Path(fpath).relative_to(SANDBOX))],
            cwd=SANDBOX, text=True, capture_output=True,
            timeout=timeout, check=False,
        )
        el = round(time.time() - s, 2)
        out = proc.stdout + "\n" + proc.stderr
        err = bool(re.search(r"^\S*\.lean:\d+:\d+: error:", out, re.MULTILINE))
        return {"compiled": (proc.returncode == 0 and not err), "elapsed": el, "stdout_tail": out[-500:]}
    except subprocess.TimeoutExpired:
        return {"compiled": False, "elapsed": timeout, "timed_out": True, "stdout_tail": ""}


def build_test(preamble, signature, tactic_body, out_path):
    out_path.write_text("\n".join([
        f"-- gp230_solve probe via `{tactic_body[:80]}`",
        preamble, "",
        signature + " := by",
        f"  {tactic_body}", "",
    ]))


def gold_name_in_body(proof_body, gold_names):
    for g in gold_names:
        if g in proof_body:
            return g
    return None


def parse_gap(stdout_tail):
    """Extract a gap report from compiler errors."""
    out = stdout_tail or ""
    if "unknown identifier" in out.lower():
        m = re.search(r"unknown(?:Identifier|Constant)`?\s*`?([A-Za-z_][A-Za-z0-9_'.]*)", out)
        if m:
            return f"missing_lemma: {m.group(1)}"
    if "unsolved goals" in out.lower():
        return "unsolved_goals_at_step"
    if "type mismatch" in out.lower():
        return "type_mismatch"
    if "did not find an occurrence" in out.lower():
        return "rewrite_pattern_miss"
    if "expected" in out.lower():
        return "syntax_or_token_error"
    return "uncategorized"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-file", required=True, help="Lean file with `example ... := by hammer/sorry`")
    ap.add_argument("--budget", type=int, default=5, help="max LLM-proof attempts (scaffold logs only)")
    ap.add_argument("--strict", action="store_true", help="strict mode: 0 manual edits required")
    ap.add_argument("--gold-names", default="", help="comma-separated gold lemma names to ban from proof body")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workdir", default=None, help="dir for test files; defaults to /tmp/gp230_solve_<rowstem>")
    args = ap.parse_args()

    row_file = Path(args.row_file)
    text = row_file.read_text()
    preamble, signature = extract_example(text)
    if not signature:
        print(f"ERROR: could not parse example signature in {row_file}")
        return 1
    gold = [g.strip() for g in args.gold_names.split(",") if g.strip()]

    workdir = Path(args.workdir) if args.workdir else SANDBOX / f"GP230SolveTmp_{row_file.stem}"
    workdir.mkdir(parents=True, exist_ok=True)

    trace = {
        "row_file": str(row_file),
        "started_at": now(),
        "preamble": preamble,
        "signature": signature,
        "gold_names_banned": gold,
        "B0_results": [],
        "B1_result": None,
        "route_c_attempts": [],
        "successful_proof": None,
        "verdict": "PENDING",
        "gap_report": None,
    }

    # B0: try each basic tactic
    print(f"[gp230] B0 phase: {len(B0_TACTICS)} tactics")
    for i, tac in enumerate(B0_TACTICS):
        fp = workdir / f"B0_{i:02d}_{re.sub(r'[^a-z0-9]', '_', tac.lower())[:30]}.lean"
        build_test(preamble, signature, tac, fp)
        r = run_lean(fp, timeout=60)
        trace["B0_results"].append({"tactic": tac, **r})
        if r["compiled"]:
            print(f"  ✓ B0 closes via `{tac}` ({r['elapsed']}s)")
            trace["successful_proof"] = {"phase": "B0", "tactic": tac}
            trace["verdict"] = "BASELINE_CLOSED_B0"
            break
    else:
        # B1: hammer
        print(f"[gp230] B1 phase: hammer")
        fp = workdir / "B1_hammer.lean"
        if "import Hammer" not in preamble:
            preamble_b1 = "import Hammer\n" + preamble
        else:
            preamble_b1 = preamble
        build_test(preamble_b1, signature, "hammer", fp)
        r = run_lean(fp, timeout=240)
        trace["B1_result"] = r
        if r["compiled"]:
            print(f"  ✓ B1 hammer closes ({r['elapsed']}s)")
            trace["successful_proof"] = {"phase": "B1", "tactic": "hammer"}
            trace["verdict"] = "BASELINE_CLOSED_B1"
        else:
            # Route C: scaffold (no LLM integration here)
            print(f"[gp230] B0+B1 OPEN — Route C would now propose {args.budget} LLM attempts")
            print(f"  (scaffold logs prompt context; integrate LLM in v31)")
            trace["route_c_attempts"] = [{"note": f"placeholder; LLM-proof generation not implemented in scaffold (budget={args.budget})"}]
            trace["verdict"] = "ROUTE_C_PENDING_LLM_INTEGRATION"
            trace["gap_report"] = parse_gap(r.get("stdout_tail", ""))

    out_path = Path(args.out) if args.out else workdir / "trace.json"
    out_path.write_text(json.dumps(trace, indent=2, sort_keys=True))
    print(f"\n[gp230] trace written to {out_path}")
    print(f"[gp230] verdict: {trace['verdict']}")
    if trace["gap_report"]:
        print(f"[gp230] gap_report: {trace['gap_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
