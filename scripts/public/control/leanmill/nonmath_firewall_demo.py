#!/usr/bin/env python3
"""Non-math spec-faithfulness FIREWALL — reviewer-runnable demo over the committed domain corpus.

The spine of the non-math wedge: an NL compliance/policy/finance rule is formalized to a decidable Lean
predicate; the firewall ACCEPTS a faithful formalization and REJECTS a laundered one (off-by-one threshold /
comparator flip / dropped clause / boolean-precedence flip / divisibility refactor) — by a KERNEL-decided
instance battery, not an LLM opinion. Deterministic (no LLM), warm-local. Reuses the production primitive
`autoformalize.default_instance_battery` (no fork). Corpus: `nonmath_domain_corpus.json` (16 domains across
compliance / finance / IAM / DeFi / must-search).

  PYTHONPATH=src python scripts/public/control/leanmill/nonmath_firewall_demo.py [--n N]
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
CORPUS = Path(__file__).resolve().parent / "nonmath_domain_corpus.json"
SANDBOX = str(REPO / "ztare_proofs")


def firewall_accepts(prelude: str, predicate: str, battery) -> bool:
    """True = the firewall ACCEPTS (the labelled battery decides to every label under the kernel)."""
    from ztare.leanmill.solver.autoformalize import default_instance_battery
    cases = [(c[0], bool(c[1])) for c in battery]
    return default_instance_battery(prelude, predicate, cases, sandbox=SANDBOX) is True


def main() -> int:
    n = None
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])
    corpus = json.loads(CORPUS.read_text())
    if n:
        corpus = corpus[:n]
    print(f"=== NON-MATH FIREWALL over {len(corpus)} domains (kernel-decided battery, ztare_proofs) ===\n", flush=True)
    admit_faithful = catch_laundered = 0
    rows = []
    for d in corpus:
        fa = firewall_accepts(d["faithful_prelude"], d["predicate"], d["battery"])      # want ACCEPT
        la = firewall_accepts(d["laundered_prelude"], d["predicate"], d["battery"])      # want REJECT
        ok = fa and not la
        admit_faithful += int(fa)
        catch_laundered += int(not la)
        rows.append((d["domain"], d["family"], fa, not la, ok))
        print(f"  {'✅' if ok else '❌'}  {d['domain']:28s} [{d['family']:22s}]  "
              f"faithful={'ACCEPT' if fa else 'REJECT'}  laundered={'CAUGHT' if not la else 'MISSED'}", flush=True)
    nN = len(corpus)
    print(f"\n=== firewall admits faithful {admit_faithful}/{nN}  |  catches laundered {catch_laundered}/{nN} ===")
    clean = (admit_faithful == nN and catch_laundered == nN)
    print("   ✅ SPINE SOUND: every faithful spec admitted, every laundered spec caught — by the kernel, no LLM."
          if clean else "   ⚠️  see rows above (a MISS on laundered is the dangerous direction).")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
