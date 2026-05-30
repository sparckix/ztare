#!/usr/bin/env python3
"""Build 2 (cold-review next-3): corrected pin-delta OOD corpus builder.

Produces a bucketed rung1_corpus.json. The OOD rows are mined from the
version delta (declarations present in vN+1 Mathlib, ABSENT in pinned
vN) — but that name-set diff alone is the WEAK criterion (the SIE
false-escape lesson: "file added later" is insufficient). The STRONG
novelty gate — the actual closer `#check @closer` ERRORS in pinned vN —
is NOT applied here (it needs the sandbox); rows are emitted with
novelty_gate:"pending_check_at_pin" and the gate is ENFORCED at run
time by rung1_kernel_grounded_rerank.closer_absent_at_pin(). No claim
may be made from a pin_delta/escape_route row until that gate passes.

Pure mining only (no sandbox). Closer name is recorded as metadata for
the gate; it is STRIPPED from the emitted `statement` so the scorer
never sees it.

Usage: build_pin_delta_corpus.py --v429-mathlib DIR --v430-mathlib DIR
       --sample N --out rung1_corpus.json [--extra-buckets file.json]
"""
from __future__ import annotations
import argparse, json, random, re
from pathlib import Path

DECL = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)*(?:protected\s+|private\s+|noncomputable\s+)*"
    r"(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_.']*)", re.M)


def names_and_stmts(root: Path):
    """name -> (full statement text up to depth-0 := / by)."""
    out: dict[str, str] = {}
    for f in root.rglob("*.lean"):
        try:
            txt = f.read_text(errors="ignore")
        except Exception:
            continue
        for m in DECL.finditer(txt):
            nm = m.group(2)
            seg = txt[m.start():m.start() + 1400]
            d = i = 0
            cut = None
            while i < len(seg):
                c = seg[i]
                if c in "([{":
                    d += 1
                elif c in ")]}":
                    d -= 1
                elif d == 0 and seg[i:i+2] == ":=":
                    cut = i; break
                elif d == 0 and (seg[i:i+4] in (" by ", "\nby ")):
                    cut = i; break
                i += 1
            stmt = (seg[:cut] if cut is not None else seg).strip()
            if ":" in stmt and 8 <= len(stmt) < 1100 and stmt.count("\n") < 16:
                out.setdefault(nm, stmt)
    return out


def strip_name(stmt: str, rid: str) -> str | None:
    m = re.match(r"^\s*(?:@\[[^\]]*\]\s*)*(?:protected\s+|private\s+|"
                 r"noncomputable\s+)*(theorem|lemma)\s+[A-Za-z_][\w'.]*",
                 stmt)
    if not m:
        return None
    return "theorem " + rid + stmt[m.end():]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v429-mathlib", required=True)
    ap.add_argument("--v430-mathlib", required=True)
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra-buckets",
                    help="json {rows:[...]} of control/public_hammer_open/"
                         "ns_gap rows to merge verbatim")
    a = ap.parse_args()

    v429 = names_and_stmts(Path(a.v429_mathlib))
    v430 = names_and_stmts(Path(a.v430_mathlib))
    added = sorted(set(v430) - set(v429))
    cand = [n for n in added if n.count(".") <= 2 and 6 <= len(n) <= 42
            and not n.startswith(("Lean.", "Mathlib.Tactic", "Aesop"))]
    random.seed(42)
    random.shuffle(cand)

    rows = []
    for i, nm in enumerate(cand[:a.sample], 1):
        rid = f"PD_{i:03d}"
        st = strip_name(v430[nm], rid)
        if not st:
            continue
        rows.append({
            "id": rid, "bucket": "pin_delta", "statement": st,
            "intended_closer": nm,            # metadata ONLY (novelty gate)
            "candidate_pool": [],             # filled by a source layer
            "novelty_gate": "pending_check_at_pin",
        })

    if a.extra_buckets:
        rows += json.load(open(a.extra_buckets)).get("rows", [])

    Path(a.out).write_text(json.dumps({"rows": rows}, indent=1,
                                      ensure_ascii=False))
    by = {}
    for r in rows:
        by[r.get("bucket", "?")] = by.get(r.get("bucket", "?"), 0) + 1
    print(json.dumps({"out": a.out, "added_vN1_minus_vN": len(added),
                      "rows": len(rows), "by_bucket": by,
                      "note": "pin_delta rows are NOT novelty-confirmed; "
                      "rung1 enforces closer-#check-FAILS-in-pinned before "
                      "any claim"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
