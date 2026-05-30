#!/usr/bin/env python3
"""escape_route_run.py — discriminating Route C escape-route runner (PL-156).

Runs the wired route_c Layer-2c generator on the 5 screen-CLEAN escape-route rows
(genuinely-new post-v4.29.0 lemmas; statement old-vocab; not
pinned-automatable — per escape_route_screen_results.json), in the same
pinned v4.29.0 sandbox the natural-10 control used (which scored 0/10 in
v32_route_c_replay_results.json).

Per-class verdict: closures on escape-route vs natural. A "closure"
counts ZERO until it survives the v33 anti-laundering organs
(pre-registered in PL-156). Resume-safe; bounded per-row timeout.
"""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic  # noqa: E402

DISPATCH = ROOT / "scripts/public/control/route_c_layer_2c_dispatch.py"
OUT = ROOT / "analytics/public/leanmill/escape_route/escape_route_run_results.json"
PRE = "import Mathlib\nimport Hammer\nopen scoped Nat\nopen Real\n\n"

# Exact statements that PASSED escape_route_screen (typecheck OK under
# v4.29.0, no pinned automation closed them).
ROWS = {
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


BASELINE_MODEL = "gpt-4.1-mini"


def _slug(text: str) -> str:
    out = []
    for ch in str(text):
        out.append(ch if ch.isalnum() else "_")
    return "_".join("".join(out).strip("_").split("_"))[:80]


def _run_tag(model: str, max_rounds: str, tag: str) -> str:
    if tag:
        clean = _slug(tag)
        return clean + ("_" if clean and not clean.endswith("_") else "")
    if model != BASELINE_MODEL or str(max_rounds) != "2":
        return f"{_slug(model)}_r{_slug(max_rounds)}_"
    return ""


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=BASELINE_MODEL)
    ap.add_argument("--max-rounds", default="2")
    ap.add_argument("--tag", default="")  # distinct out files per config
    ap.add_argument("--per-row-timeout-s", type=int, default=900)
    ap.add_argument("--semantic-threshold", type=float, default=0.55)
    ap.add_argument("--no-semantic-premise-shelf", action="store_true")
    ap.add_argument("--results-out", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    tag = _run_tag(a.model, str(a.max_rounds), a.tag)
    results = []
    for rid, stmt in ROWS.items():
        rowf = Path(f"/tmp/er_{rid}.lean")
        write_text_atomic(rowf, PRE + stmt + " := by sorry\n")
        outj = Path(f"/tmp/er_{tag}{rid}.json")
        if a.force or not outj.exists():
            print(f"--- {rid}: dispatch ({a.model}, {a.max_rounds} rounds, compile) ---", flush=True)
            cmd = [
                "python3", str(DISPATCH), "--row", str(rowf),
                "--max-rounds", str(a.max_rounds), "--model", a.model,
                "--compile", "--out", str(outj),
                "--semantic-threshold", str(a.semantic_threshold),
            ]
            if a.no_semantic_premise_shelf:
                cmd.append("--no-semantic-premise-shelf")
            try:
                subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=a.per_row_timeout_s)
            except subprocess.TimeoutExpired:
                results.append({"row_id": rid, "status": f"dispatch_timeout_{a.per_row_timeout_s}s"})
                print(f"  TIMEOUT {a.per_row_timeout_s}s", flush=True); continue
        try:
            r = read_json(outj, default={})
            if not isinstance(r, dict):
                raise ValueError("dispatch_json_not_object")
            # CORRECT raw-dispatch schema (NOT v32-batch keys): the
            # dispatch emits closure_verdict / compiled_any / gap_report;
            # per round: rounds[].candidate.lemma_name. (Bug fixed
            # 2026-05-16 after Be-Meta-Darwin self-catch: prior code read
            # r.get('verdict')/rd.get('lemma') -> always None -> fake 0.)
            cv = r.get("closure_verdict")
            cands = [(rd.get("candidate") or {}).get("lemma_name")
                     for rd in r.get("rounds", [])]
            genuine = cv is not None and len(r.get("rounds", [])) > 0 and any(cands)
            results.append({"row_id": rid, "closure_verdict": cv,
                            "compiled_any": r.get("compiled_any"),
                            "genuine_attempt": genuine,
                            "proposed_lemmas": cands,
                            "dispatch_json": str(outj)})
            print(f"  {rid}: closure_verdict={cv} "
                  f"compiled_any={r.get('compiled_any')} genuine={genuine}", flush=True)
        except Exception as e:
            results.append({"row_id": rid, "status": f"result_read_error:{e}"})

    n_closed = sum(1 for x in results
                   if x.get("closure_verdict") == "CLOSED"
                   or x.get("compiled_any") is True)
    payload = {
        "class": "escape_route",
        "sandbox_mathlib": "v4.29.0",
        "n_rows": len(ROWS),
        "n_closed_raw": n_closed,
        "natural_control": "v32_route_c_replay_results.json (0/10 closed)",
        "note": ("raw closures NOT counted until v33 anti-laundering "
                 "audit (PL-156 pre-registered). 0 raw => pessimism SOUND "
                 "per PL-156 event-2; >=1 raw => v33 audit then per-class verdict"),
        "run_config": {
            "model": a.model,
            "max_rounds": str(a.max_rounds),
            "tag": tag.rstrip("_"),
            "per_row_timeout_s": a.per_row_timeout_s,
            "semantic_premise_shelf": not a.no_semantic_premise_shelf,
            "semantic_threshold": a.semantic_threshold,
            "baseline_preserved": bool(tag),
        },
        "results": results,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Tag the aggregate by config so a stronger-prover run never clobbers
    # the baseline it must be compared against (forward fix 2026-05-16).
    out_path = Path(a.results_out) if a.results_out else (
        OUT.with_name(f"escape_route_run_results_{tag.rstrip('_')}.json")
        if tag else OUT
    )
    write_json_atomic(out_path, payload, sort_keys=False)
    print(f"\n=> escape_route raw closures: {n_closed}/{len(ROWS)} "
          f"(natural control 0/10). {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
