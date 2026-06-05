"""Closure ledger — measure the validated agentic-leaf solver's real yield on a subset.

Best-of-N across the agentic-capable providers (codex + claude on subscription; deepseek/
gemini are API-only and cannot edit files + run lake, so they are not agentic leaves here).
Substrate is calibrated ONCE up front (fail-loud); each closure is independently kernel-gated
(axioms ⊆ allowlist, no sorryAx). Produces an honest ledger: which components close, by which
provider, and which are genuine frontier. Run on the VPS over the matched live pair.

  python3 closure_ledger.py [--timeout 250]
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO))
ATLAS = "projects/atlas_lean_2026_05_29"
APN = "projects/gp_spectral_apn_seed_2026_05_28/candidates/hilbert_functions_2_sorried.lean"
LAKE = str(Path.home() / ".elan/bin/lake")

# (name, goal, decompose). Lesson (2026-06-02): decompose=True for ALL — P1_d2 read as a
# "wall" under decompose=False + 250s, but closes kernel-clean with decompose + a fair budget
# (it needed to enumerate 4 degree-2 divisors). An under-budgeted "open" is NOT a capability
# verdict; the ledger now flags near-budget opens as budget_suspect and must re-test first.
SUBSET = [
    ("P1_d0", "pureOSequence GammaP1 0 = 1", True),
    ("P1_d2", "pureOSequence GammaP1 2 = 4", True),
    ("P2_unimodal", "ProblemP2Type1Unimodal", True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=500)  # 250 under-budgeted the harder leaves
    ap.add_argument("--providers", default="codex,claude")
    a = ap.parse_args()
    from ztare.leanmill.solver.agentic_leaf import solve_robust
    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import calibrate, SubstrateDeadError
    from ztare.common.apparatus_certificate import Certificate, Verdict

    src = (REPO / APN).read_text(encoding="utf-8")
    defs = src[:re.search(r"(?m)^\s*theorem\s+P2\b", src).start()]
    providers = tuple(a.providers.split(","))

    # CALIBRATE SUBSTRATE ONCE (fail-loud) — a closure ledger off a dead substrate is void.
    try:
        with PersistentLean(project_dir=str(REPO / ATLAS)) as pl:
            print("[ledger] " + calibrate(pl).banner(), flush=True)
    except (SubstrateDeadError, RuntimeError) as e:
        print(f"[ledger] ABORT — substrate not live: {str(e)[:160]}"); sys.exit(2)

    ledger, t0 = [], time.time()
    for name, goal, decomp in SUBSET:
        ts = time.time()
        r = solve_robust(goal, defs=defs, project_dir=str(REPO / ATLAS), repo=str(REPO / ATLAS),
                         lake_bin=LAKE, providers=providers, attempts_per_provider=1,
                         target="leaf", timeout=a.timeout, decompose=decomp)
        bo = r.calibration.get("best_of", {})
        secs = round(time.time() - ts)
        # an open that consumed ~a full provider-budget likely TIMED OUT (budget-bound), so it
        # is NOT a capability verdict — flag it so it is re-tested with more budget, not called
        # a wall (P1_d2 looked like a wall at 250s and closes kernel-clean with a fair budget).
        budget_suspect = (not r.closed) and (not r.inadmissible) and secs >= a.timeout
        # APPARATUS CERTIFICATE per component: substrate calibrate already certified
        # live+sound (else we aborted above); adequacy = the run was NOT budget-suspect (a
        # budget-bound open is under-powered, not a wall). So an open is a genuine
        # ADMISSIBLE_NEGATIVE (frontier) only if certified; otherwise INADMISSIBLE (re-test).
        cert = Certificate(live=True, sound=True, adequate=(not budget_suspect and not r.inadmissible),
                           adequate_why=("budget-suspect" if budget_suspect else
                                         "provider/substrate uncertified" if r.inadmissible else "ok"))
        verdict = cert.verdict(r.closed)
        row = {"component": name, "goal": goal, "closed": r.closed, "verdict": verdict.value,
               "winner": bo.get("winner"), "attempts": bo.get("attempts_tried"),
               "decomposed": r.decomposed, "reason": r.reason, "inadmissible": r.inadmissible,
               "seconds": secs, "budget_suspect": budget_suspect}
        ledger.append(row)
        tag = {Verdict.POSITIVE: "CLOSED by " + str(bo.get("winner")),
               Verdict.ADMISSIBLE_NEGATIVE: "open (ADMISSIBLE NEGATIVE — genuine frontier)",
               Verdict.INADMISSIBLE: "open (INADMISSIBLE — apparatus under-powered/uncertified; "
                                     "re-test, NOT a wall)"}[verdict]
        print(f"[ledger] {name}: {tag} ({secs}s, {row['attempts']} attempts) "
              f"{('— '+r.reason) if not r.closed else ''}", flush=True)

    closed = sum(1 for r in ledger if r["closed"])
    suspect = sum(1 for r in ledger if r["verdict"] == Verdict.INADMISSIBLE.value)
    frontier = sum(1 for r in ledger if r["verdict"] == Verdict.ADMISSIBLE_NEGATIVE.value)
    out = {"providers": list(providers), "n": len(SUBSET), "closed": closed,
           "admissible_frontier": frontier, "inadmissible": suspect, "timeout_s": a.timeout,
           "elapsed_s": round(time.time() - t0), "ledger": ledger}
    p = REPO / "analytics/public/queries/classification/closure_ledger_subset.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\n[ledger] verdicts (apparatus-certified): CLOSED={closed}, "
          f"ADMISSIBLE-NEGATIVE(genuine frontier)={frontier}, "
          f"INADMISSIBLE(apparatus under-powered → re-test, NOT walls)={suspect} "
          f"of {len(SUBSET)} (best-of-{len(providers)}: {providers}; timeout={a.timeout}s). "
          f"Only ADMISSIBLE-NEGATIVEs are real science 'no's. wrote {p}")


if __name__ == "__main__":
    main()
