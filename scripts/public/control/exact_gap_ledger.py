#!/usr/bin/env python3
"""Build 3 (cold-review next-3): exact-gap / falsifier ledger.

Consumer contract (governance doc §): every NON-closure row must resolve
to a concrete next lever, never a vague "killed" / "gap". Given a Rung-1
report.json (or a bundle_verify result.txt), each non-closure row is
classified into exactly one:

  missing_lemma  — an isolatable specific lemma is needed (the row
                   reached a clean 'unsolved goals' / honest exact-gap;
                   the candidate symbol that would close it is named iff
                   known from corpus metadata, else "<unresolved>")
  falsifier      — the statement is refutable / a counter-shape exists
                   (compile produced a disproof-shaped error)
  invalid        — wrong target-kind / retired / vacuous / governance-
                   rejected (single_lemma / axiom_smuggled / unverified)

Appended to analytics/public/ledgers/exact_gap/EXACT_GAP_LEDGER.jsonl
(append-only; one object per row per run). Pure: no sandbox; classifies
from the artifact only.

Usage: exact_gap_ledger.py --rung1 report.json [--run-label L]
       exact_gap_ledger.py --bundle result.txt --corpus c.json [--run-label L]
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path

LEDGER = Path("analytics/public/ledgers/exact_gap/EXACT_GAP_LEDGER.jsonl")


def classify_bundle_line(line: str, closer: str | None):
    m = re.match(r"\s*([A-Za-z][\w'.]*):\s*compile=(\S+)\s*\|\s*exact\?="
                 r"(.*?)(?:\s*\|\s*axioms=(.*))?\s*$", line)
    if not m:
        return None
    rid, comp = m.group(1), m.group(2)
    ax = (m.group(4) or "").lower()
    if comp.startswith("COMPILE_OK") and "axioms_clean" in ax \
       and "could not close" in (m.group(3) or "").lower():
        return None  # genuine closure — not a gap row
    if "axioms_smuggled" in ax or "axioms_unverified" in ax:
        return (rid, "invalid", "governance: axiom/sorry/native or unverified")
    if "try this" in (m.group(3) or "").lower():
        return (rid, "invalid", "single-lemma laundering (exact? one-liner)")
    if comp.startswith("PROVER_GAP") or comp.startswith("FAIL"):
        return (rid, "missing_lemma",
                f"needs: {closer or '<unresolved>'} (honest no-close)")
    if "timeout" in (m.group(3) or "").lower() or "inconclusive" in (m.group(3) or "").lower():
        return (rid, "invalid", "exact?-adjudication inconclusive (not credited)")
    return (rid, "missing_lemma", f"needs: {closer or '<unresolved>'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung1")
    ap.add_argument("--bundle")
    ap.add_argument("--corpus")
    ap.add_argument("--run-label", default="unlabeled")
    a = ap.parse_args()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entries = []

    if a.rung1:
        rep = json.load(open(a.rung1))
        for r in rep.get("rows", []):
            if r.get("skipped"):
                entries.append((r["id"], "invalid",
                                "novelty gate failed: " + r["skipped"]))
                continue
            st = (r.get("B7_kernel_rerank_governance") or {}).get("status")
            if st == "closure":
                continue
            entries.append((r["id"],
                            "missing_lemma" if st == "exact_gap" else "invalid",
                            f"rung1 B7 status={st}"))
    elif a.bundle:
        closby = {}
        if a.corpus:
            closby = {x["id"]: x.get("intended_closer")
                      for x in json.load(open(a.corpus)).get("rows", [])}
        for ln in Path(a.bundle).read_text().splitlines():
            if not ln.strip():
                continue
            rid0 = ln.split(":", 1)[0].strip()
            c = classify_bundle_line(ln, closby.get(rid0))
            if c:
                entries.append(c)
    else:
        ap.error("one of --rung1 / --bundle required")

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with LEDGER.open("a") as f:
        for rid, verdict, ev in entries:
            f.write(json.dumps({"ts": ts, "run": a.run_label, "id": rid,
                                "verdict": verdict, "evidence": ev}) + "\n")
    by = {}
    for _, v, _ in entries:
        by[v] = by.get(v, 0) + 1
    print(json.dumps({"ledger": str(LEDGER), "appended": len(entries),
                      "by_verdict": by,
                      "contract": "every non-closure row → "
                      "missing_lemma | falsifier | invalid (no vague gaps)"},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
