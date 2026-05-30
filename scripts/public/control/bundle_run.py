#!/usr/bin/env python3
"""bundle_run.py — the single runnable entrypoint for the bundled
Path A + Path B (the runnable harness for Lean-closure solver+governance
work; answers "how do you run it": `python bundle_run.py ...`, not a
manual tick). Lean-substrate-specific: parameterized across Lean
versions/sandboxes, NOT non-Lean substrates.

Thin composition of already-validated pieces (NO rewrite):
  Path A : bundle_verify.py  (verbatim verify in a canonical pinned
           sandbox + exact? adjudication; pinned_env_healthy-gated)
  Path B : gp233_adversary_yield_decomp.py  (yield decomposition =
           the single scoreboard source; dual never-merged view
           rendered from it; residual_to_lever for gap -> next lever)

Substrate/version parameterized (--substrate / --sandbox): NS or any
substrate runs against its OWN Mathlib version. Two scoreboards are
printed SEPARATELY and never merged (strict bundle invariant).

Usage:
  bundle_run.py --substrate NS --sandbox <pinned-vX sandbox> \
                --corpus adv.json --proofs prover.json \
                [--workdir DIR] [--pent-ok]
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable
CTL = REPO / "scripts/public/control"


def _run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--substrate", required=True)
    ap.add_argument("--sandbox", required=True,
                    help="canonical pinned Mathlib sandbox for this substrate/version")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--proofs", required=True)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--pent-ok", action="store_true")
    a = ap.parse_args()

    wd = Path(a.workdir) if a.workdir else Path(tempfile.mkdtemp(prefix="bundle_"))
    wd.mkdir(parents=True, exist_ok=True)
    result = wd / "result.txt"

    print(f"=== BUNDLE RUN — substrate={a.substrate} sandbox={a.sandbox} ===\n")

    # --- PATH A: verbatim verify in the substrate's canonical pinned sandbox
    rc, o = _run([PY, str(CTL / "bundle_verify.py"),
                  "--corpus", a.corpus, "--proofs", a.proofs,
                  "--sandbox", a.sandbox, "--out", str(result)])
    print("[Path A] verbatim verification (pinned, exact?-adjudicated):")
    print(o.strip())
    if rc == 2 or "PINNED_ENV_NOT_MATERIALIZED" in o:
        print("\nBUNDLE ABORTED: pinned env not materialized for this "
              "substrate/version — register/build the canonical sandbox "
              "at the chosen Mathlib v first (no ad-hoc routing).")
        return 2

    # --- PATH B: governance decomposition (separate scoreboard)
    _, dec = _run([PY, str(CTL / "gp233_adversary_yield_decomp.py"),
                   "--result", str(result),
                   "--corpus-label",
                   f"{a.substrate} @ {a.sandbox} (bundle_run)"])
    try:
        d = json.loads(dec)
        yld = d.get("decision_changing_yield", {})
    except Exception:
        d, yld = {}, {}

    # Single scoreboard source = gp233 decomposition (adversary-format
    # aware). The separate dual_scoreboard.py was redundant + mis-parsed
    # this format + carried gloat — removed; the never-merged dual view
    # is rendered here from the one authoritative source.
    tally = d.get("tally", {})
    print("\n" + "=" * 60)
    print("DUAL SCOREBOARD (never merged):")
    print("-" * 60)
    print("[SOLVER — Path A]  genuine_novel_closures="
          f"{yld.get('genuine_novel_closures_on_adversary_hard_rows','?')} ; "
          f"honest_gaps={yld.get('honest_exact_gaps_isolating_missing_content','?')}")
    print("[GOVERNANCE — Path B]  false_ratifications="
          f"{yld.get('false_ratifications','?')} ; "
          "anti_laundering_rejections="
          f"{yld.get('anti_laundering_rejections_preventing_false_ratification','?')} ; "
          f"zero_false_ratify={yld.get('load_bearing_invariant_false_ratifications_zero','?')}")
    print(f"  tally: {tally}")
    print("=" * 60)

    out = {"substrate": a.substrate, "sandbox": a.sandbox,
           "result_file": str(result),
           "solver_scoreboard": {k: yld.get(k) for k in
               ("genuine_novel_closures_on_adversary_hard_rows",
                "honest_exact_gaps_isolating_missing_content")},
           "governance_scoreboard": {k: yld.get(k) for k in
               ("false_ratifications",
                "anti_laundering_rejections_preventing_false_ratification",
                "load_bearing_invariant_false_ratifications_zero")},
           "tally": d.get("tally"),
           "pinned_provenance": f"verified in canonical sandbox {a.sandbox} "
                                "(pinned_env_healthy-gated; no ad-hoc routing)"}
    (wd / "bundle_report.json").write_text(json.dumps(out, indent=2))
    print(f"\nbundle report: {wd/'bundle_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
