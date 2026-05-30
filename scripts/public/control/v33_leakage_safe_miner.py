#!/usr/bin/env python3
"""v33_leakage_safe_miner.py — Tick 2 variance gate + Tick 3 leakage-safe miner.

GPT-5.5-blessed path. Mines deployable solver priors from the re-audited
v22-v29 contrastive ledger (/tmp/v33_reaudited_attempt_ledger.json,
produced by Tick 1 agent).

HARD RULES (GPT-5.5):
  - Predictor features = ONLY preflight: L2_preflight, L1_process,
    L3_preflight_risks, target_kind.
  - FORBIDDEN as predictors: posthoc_kill_reason, source_version,
    row_id prefix, any outcome-derived label.
  - Outcome = success_binary_for_target_kind (top-level SUCCESS/FAIL).
    Kill-reason flavors are NOT outcome variance.

TICK 2 minimum gate (all must pass or STOP — do not mine):
  ≥30 rows, ≥10 audited successes, ≥10 audited failures, ≥3 target_kinds,
  ≥3 L2 ops with BOTH success and failure, ≥2 L1 processes with both,
  0 rows used whose leakage_flags is non-empty.

TICK 3 top-cell requirements: support≥5, real success/failure contrast,
not all-one-family, survives leave-one-family-out.

Reuses v32_meta_pattern_miner contingency + permutation_null. No GNN,
no LLM, no new primitive, no architecture.
"""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from v32_meta_pattern_miner import contingency, permutation_null  # type: ignore

LEDGER = Path("/tmp/v33_reaudited_attempt_ledger.json")
LR = ROOT / "analytics/public/leanmill"

# Multi-ledger union support (GPT-5.5 3-ledger plan): when --ledgers is
# passed, union all given ledger files (dedup by row_id, prefer non-leaked).
def load_and_merge(paths: list[Path]) -> list[dict]:
    seen: dict[str, dict] = {}
    for p in paths:
        if not p.exists():
            continue
        raw = json.load(open(p))
        rows = raw if isinstance(raw, list) else raw.get("ledger", raw.get("rows", []))
        src_tag = p.stem
        for r in rows:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("row_id") or r.get("source") or id(r))
            r = {**r, "_ledger_source": src_tag}
            if rid not in seen:
                seen[rid] = r
            else:
                # prefer the entry WITHOUT leakage flags
                if seen[rid].get("leakage_flags") and not r.get("leakage_flags"):
                    seen[rid] = r
    return list(seen.values())

ALLOWED_PREDICTORS = {"L2_preflight", "L1_process", "L3_preflight_risks", "target_kind"}
FORBIDDEN_PREDICTORS = {"posthoc_kill_reason", "source_version", "row_id", "audited_outcome"}
MIN_SUPPORT = 5


def load_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    raw = json.load(open(LEDGER))
    return raw if isinstance(raw, list) else raw.get("ledger", raw.get("rows", []))


def tick2_variance_gate(rows: list[dict]) -> dict:
    # Exclude leaked rows entirely
    clean = [r for r in rows if not r.get("leakage_flags")]
    n_leaked = len(rows) - len(clean)
    # success/failure must be the top-level binary, not kill flavors
    succ = [r for r in clean if r.get("success_binary_for_target_kind") is True]
    fail = [r for r in clean if r.get("success_binary_for_target_kind") is False]
    tks = {r.get("target_kind") for r in clean if r.get("target_kind") not in (None, "unknown")}

    # L2 ops with BOTH success and failure
    l2_succ = {r.get("L2_preflight") for r in succ if r.get("L2_preflight") not in (None, "unknown")}
    l2_fail = {r.get("L2_preflight") for r in fail if r.get("L2_preflight") not in (None, "unknown")}
    l2_both = l2_succ & l2_fail
    # L1 processes with BOTH
    l1_succ = {r.get("L1_process") for r in succ if r.get("L1_process") not in (None, "unknown")}
    l1_fail = {r.get("L1_process") for r in fail if r.get("L1_process") not in (None, "unknown")}
    l1_both = l1_succ & l1_fail

    checks = {
        "total_clean_rows>=30": len(clean) >= 30,
        "audited_successes>=10": len(succ) >= 10,
        "audited_failures>=10": len(fail) >= 10,
        "target_kinds>=3": len(tks) >= 3,
        "L2_ops_with_both>=3": len(l2_both) >= 3,
        "L1_processes_with_both>=2": len(l1_both) >= 2,
        "zero_leaked_rows_used": True,  # we excluded them; informational below
    }
    passed = all(checks.values())
    return {
        "n_total": len(rows), "n_leaked_excluded": n_leaked, "n_clean": len(clean),
        "n_success": len(succ), "n_failure": len(fail),
        "target_kinds": sorted(tks), "L2_ops_with_both": sorted(l2_both),
        "L1_processes_with_both": sorted(l1_both),
        "checks": checks, "gate_passed": passed,
        "clean_rows": clean,
    }


def tick3_mine(clean: list[dict]) -> dict:
    # Build (L2_preflight x L1_process x target_kind) -> success/fail
    rows = []
    for r in clean:
        if r.get("success_binary_for_target_kind") not in (True, False):
            continue
        rows.append({
            "L2_preflight": r.get("L2_preflight", "unknown"),
            "L1_process": r.get("L1_process", "unknown"),
            "target_kind": r.get("target_kind", "unknown"),
            "outcome": "SUCCESS" if r["success_binary_for_target_kind"] else "FAIL",
            # family for leave-one-family-out = source_version (NOT a predictor, only resample axis)
            "namespace": r.get("source_version", "?"),
        })
    if len(rows) < MIN_SUPPORT:
        return {"verdict": "insufficient_rows_post_filter", "n": len(rows)}

    cells, grand, cv = contingency(rows, ("L2_preflight", "L1_process", "target_kind"))
    if not cells:
        return {"verdict": "no_cell_meets_min_support", "grand": grand}
    top = cells[0]
    perm_p = permutation_null(rows, ("L2_preflight", "L1_process", "target_kind"), top["chi2"], n_perm=1000)

    # leave-one-family-out (family = source_version)
    fams = sorted({r["namespace"] for r in rows if r["namespace"] != "?"})
    preserved = 0
    for f in fams:
        sub = [r for r in rows if r["namespace"] != f]
        cs, _, _ = contingency(sub, ("L2_preflight", "L1_process", "target_kind"))
        if cs:
            t = (tuple(cs[0]["cell"]), cs[0]["outcome"])
            if t == (tuple(top["cell"]), top["outcome"]):
                preserved += 1
    n_fam = len(fams)

    # not-all-one-family check
    top_rows = [r for r in rows
                if r["L2_preflight"] == top["cell"][0]
                and r["L1_process"] == top["cell"][1]
                and r["target_kind"] == top["cell"][2]]
    fam_spread = len({r["namespace"] for r in top_rows})

    if perm_p >= 0.05:
        verdict = "no_pattern_in_corpus"
        rat = f"permutation null p={perm_p:.3f} ≥ 0.05 — top cell not beyond shuffle noise"
    elif top["support"] < MIN_SUPPORT:
        verdict = "no_pattern_in_corpus"
        rat = f"top cell support {top['support']} < {MIN_SUPPORT}"
    elif fam_spread < 2:
        verdict = "label_quality_binding"
        rat = f"top cell all from one source family (spread={fam_spread}) — not generalizable"
    elif n_fam >= 2 and preserved < max(1, n_fam - 1):
        verdict = "label_quality_binding"
        rat = f"top cell unstable: preserved {preserved}/{n_fam} leave-one-family-out"
    else:
        verdict = "solver_prior_found"
        rat = (f"preflight-only cell stable {preserved}/{n_fam}, perm_p={perm_p:.3f}, "
               f"lift={top['lift']}, fam_spread={fam_spread} — DEPLOYABLE prior candidate")

    return {
        "verdict": verdict, "rationale": rat,
        "top_cell": top, "perm_p": round(perm_p, 4),
        "resample_family_stability": f"{preserved}/{n_fam}",
        "top_cell_family_spread": fam_spread,
        "cramers_v": cv,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledgers", nargs="+", default=None,
                    help="union multiple ledger JSON paths (dedup by row_id, prefer non-leaked)")
    ap.add_argument("--tag", default="v22v29", help="output tag")
    args = ap.parse_args()

    if args.ledgers:
        rows = load_and_merge([Path(p) for p in args.ledgers])
        print(f"# v33 leakage-safe miner — MERGED {len(args.ledgers)} ledgers (tag={args.tag})")
    else:
        rows = load_ledger()
        print(f"# v33 leakage-safe miner")
    if not rows:
        print(f"No ledger rows found — re-audit agent must complete first.")
        return 1
    print(f"Ledger rows (post-merge dedup): {len(rows)}\n")

    gate = tick2_variance_gate(rows)
    print("=== TICK 2: variance gate (honest STOP if not met) ===")
    print(f"clean={gate['n_clean']} (leaked-excluded={gate['n_leaked_excluded']}) "
          f"success={gate['n_success']} failure={gate['n_failure']}")
    print(f"target_kinds={gate['target_kinds']}")
    print(f"L2_ops_with_both={gate['L2_ops_with_both']}")
    print(f"L1_processes_with_both={gate['L1_processes_with_both']}")
    for k, v in gate["checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"GATE: {'PASSED — proceed to Tick 3' if gate['gate_passed'] else 'NOT MET — STOP, do not mine'}")

    result = {"tick2_gate": {k: v for k, v in gate.items() if k != "clean_rows"}}
    if gate["gate_passed"]:
        mine = tick3_mine(gate["clean_rows"])
        print(f"\n=== TICK 3: leakage-safe contingency miner ===")
        print(f"VERDICT: {mine['verdict']} — {mine.get('rationale','')}")
        if mine.get("top_cell"):
            t = mine["top_cell"]
            print(f"TOP CELL: (L2={t['cell'][0]}, L1={t['cell'][1]}, target={t['cell'][2]} "
                  f"→ {t['outcome']}) support={t['support']} lift={t['lift']} "
                  f"perm_p={mine['perm_p']} fam_stability={mine['resample_family_stability']}")
        result["tick3_miner"] = mine
    else:
        result["tick3_miner"] = {"verdict": "NOT_RUN_gate_not_met",
                                 "rationale": "Tick 2 variance gate not met; per GPT-5.5 STOP — do not mine an under-powered/leaky corpus"}

    outp = LR / f"v33_leakage_safe_miner_results_{args.tag}.json"
    Path(outp).write_text(json.dumps(result, indent=2, default=str))
    print(f"\nwrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
