#!/usr/bin/env python3
"""Advisory proof-source integrity lint for a bundle proofs.json.

Mechanical stopgap for the open apparatus risks R1–R4 (see the GP-233
ledger 'Bundled Path-A residual false-genuine surface' entry):
`bundle_verify`'s COMPILE_OK gate (`rc==0 and not error and not sorry`)
does NOT reject a proof whose source SMUGGLES the goal via an `axiom` /
`opaque` / `sorryAx` / `native_decide` / `@[implemented_by]` term — such
a proof compiles clean and would be credited genuine_novel_closure.

This is ADVISORY ONLY and standalone — it does NOT modify the
adversarially-validated bundle_verify (a forcing-verifier change needs
its own regression+adversary loop). Run it on a proofs.json BEFORE
trusting a bundle's genuine count; any FLAG means the row's "genuine"
status is unverified until the source is explained. Trusted/in-thread-
authored proofs should come back ALL-CLEAN; an untrusted/automated
prover's output is exactly what this exists to screen.

Usage: proof_source_integrity_lint.py --proofs proofs.json [--json]
Exit 0 = all clean ; 1 = at least one FLAG ; 2 = bad input.
"""
import argparse
import json
import re
import sys

# token -> why it is a false-genuine risk for an UNTRUSTED prover
PATTERNS = {
    "axiom": (re.compile(r"(?<![\w.])axiom\s"),
              "R1: declares an axiom — can assume the goal with no proof"),
    "opaque": (re.compile(r"(?<![\w.])opaque\s"),
               "R2: opaque decl shifts trust off the kernel"),
    "sorryAx": (re.compile(r"\bsorryAx\b"),
                "R3: sorryAx term — a sorry that may not emit the warning"),
    "native_decide": (re.compile(r"\bnative_decide\b"),
                      "R2: native_decide trusts compiled code, not the kernel"),
    "implemented_by": (re.compile(r"@\[\s*implemented_by"),
                       "R2: @[implemented_by] swaps in unverified native impl"),
    "extern": (re.compile(r"@\[\s*extern"),
               "R2: @[extern] binds to unverified native code"),
    "admit": (re.compile(r"(?<![\w.])admit(?![\w])"),
              "R3: admit is a sorry synonym"),
    "stop": (re.compile(r"(?<![\w.])stop(?![\w])"),
             "R3: stop leaves the goal open"),
    "sorry": (re.compile(r"(?<![\w.])sorry(?![\w])"),
              "open goal — should already fail COMPILE_OK, flagged for defense"),
}


def lint_source(src: str) -> list[tuple[str, str]]:
    hits = []
    for tok, (pat, why) in PATTERNS.items():
        if pat.search(src):
            hits.append((tok, why))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proofs", required=True,
                    help='bundle proofs.json: {"proofs":{id:src},"gaps":[...]}')
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        pj = json.load(open(a.proofs))
        proofs = pj.get("proofs", {})
    except Exception as e:  # noqa: BLE001
        print(f"bad input: {e}")
        return 2

    report = {}
    flagged = 0
    for rid, src in sorted(proofs.items()):
        hits = lint_source(src or "")
        if hits:
            flagged += 1
            report[rid] = [{"token": t, "why": w} for t, w in hits]

    if a.json:
        print(json.dumps({
            "proofs_checked": len(proofs),
            "flagged": flagged,
            "clean": len(proofs) - flagged,
            "verdict": "ALL-CLEAN" if flagged == 0 else "FLAGS-PRESENT",
            "detail": report,
        }, indent=2))
    else:
        for rid in sorted(proofs):
            if rid in report:
                toks = ", ".join(h["token"] for h in report[rid])
                print(f"FLAG  {rid}: {toks}")
                for h in report[rid]:
                    print(f"        - {h['why']}")
            else:
                print(f"clean {rid}")
        print(f"\n{len(proofs) - flagged}/{len(proofs)} clean ; "
              f"{flagged} flagged ; verdict="
              f"{'ALL-CLEAN' if flagged == 0 else 'FLAGS-PRESENT'}")
        print("ADVISORY ONLY — not wired into bundle_verify; a FLAG means "
              "the row's genuine status is unverified until explained.")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
