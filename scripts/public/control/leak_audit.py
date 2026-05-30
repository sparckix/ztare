#!/usr/bin/env python3
"""leak_audit.py — validity audit of prior "solved"/certified proofs.

Cold-review #5/#6: `#print axioms` does NOT catch corpus leakage —
a proof under bare `import Mathlib` may close by `exact <the target
theorem itself>` or by a lemma unavailable at the target's original
declaration point, and the kernel axiom gate reports it clean. Prior
closure/`genuine` verdicts measured that way are validity-SUSPECT
until rechecked.

What this CAN compute on our (synthetic, NOT module-extracted) prior
corpora — honest proxies, reported as such:
  - governance verdict via the persistent REPL (kernel #print axioms +
    single-lemma `exact?` probe). `single_lemma` => the "target" is a
    renamed existing Mathlib lemma => benchmark-INVALID (leakage class).
  - self-reference: proof body mentions its OWN target name => direct
    `exact target` style leakage.
  - axiom_smuggled / unverified => not a clean closure.
Contamination rate = (single_lemma + self_ref + axiom_smuggled +
unverified) / audited. >5% => prior closure metric is contaminated.

Caveat (stated, not hidden): true LeanDojo-style module-context replay
(only pre-target declarations visible) requires a dependency-DAG
extracted benchmark we do not yet have; that is the durable fix. This
audit bounds the risk with what the existing artifacts allow.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--glob", default="/tmp/adv_corpus/proofs_*.json")
    ap.add_argument("--out", default="/tmp/rung1/leak_audit.json")
    a = ap.parse_args()

    sb = Path(a.sandbox).expanduser().resolve()
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r1", str(Path(__file__).with_name("rung1_kernel_grounded_rerank.py")))
    r1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r1)

    items: list[tuple[str, str, str]] = []
    for f in sorted(glob.glob(a.glob)):
        try:
            proofs = json.load(open(f)).get("proofs", {})
        except Exception:
            continue
        for tid, proof in proofs.items():
            if isinstance(proof, str) and proof.strip():
                items.append((f, tid, proof.strip()))

    audited, rows = [], []
    by = {"closure": 0, "single_lemma": 0, "axiom_smuggled": 0,
          "unverified": 0, "self_ref": 0}
    for src, tid, proof in items:
        stmt = proof.split(":= by")[0].rstrip()
        body = proof.split(":= by", 1)[1] if ":= by" in proof else ""
        # self-reference: proof body invokes its OWN target name
        self_ref = bool(re.search(rf"\b{re.escape(tid)}\b", body))
        verdict = r1.governance(sb, stmt, proof, 120)
        contaminated = (self_ref or verdict in
                        ("single_lemma", "axiom_smuggled", "unverified"))
        if self_ref:
            by["self_ref"] += 1
        by[verdict] = by.get(verdict, 0) + 1
        rows.append({"src": Path(src).name, "id": tid,
                     "governance": verdict, "self_ref": self_ref,
                     "contaminated": contaminated})
        audited.append(contaminated)
        print(json.dumps({"id": tid, "gov": verdict,
                          "self_ref": self_ref,
                          "contaminated": contaminated}))

    n = len(audited)
    c = sum(audited)
    rate = (c / n) if n else 0.0
    summary = {
        "audited": n, "contaminated": c,
        "contamination_rate": round(rate, 3),
        "by": by,
        "verdict": ("CONTAMINATED (>5%) — prior closure metric "
                    "validity-suspect; needs module-context rebench"
                    if rate > 0.05 else
                    "within 5% — prior closures provisionally OK on "
                    "the computable proxies (true module-context "
                    "audit still owed)"),
        "caveat": ("proxy audit on synthetic non-module-extracted "
                   "corpora; single_lemma/self_ref/smuggled are sound "
                   "leakage signals but cannot detect future-lemma "
                   "use without dependency-DAG extraction"),
    }
    out = {"summary": summary, "rows": rows}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("\n" + json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
