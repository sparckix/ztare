#!/usr/bin/env python3
"""name_resolution_probe.py — isolates the inflation-vs-Path-B-false-
negative ambiguity, WITHOUT codex (fast, decisive).

Finding so far: real rows get light=solved, auth=open, axioms=None.
The only difference is govern_edited appends `#print axioms <short>`
(short = target_name.split('.')[-1]). Hypothesis: that line itself
errors (short name unresolvable in the real namespace) ⇒ Path-B FALSE
NEGATIVE, not inflation.

Test directly: open each row's sorried file AS-IS (it has `sorry`,
so the target elaborates with sorryAx) and append `#print axioms`
with (a) the SHORT name, (b) the FULL name. Inspect errors:
  - SHORT errors 'unknown'/'unexpected' but FULL resolves (msgs show
    `sorryAx`)  ⇒ Path-B FN CONFIRMED: govern_edited uses the wrong
    name; 0/23 is a gate artifact, run VOID, NOT inflation.
  - SHORT resolves (msgs show `sorryAx`, no error on print line)
    ⇒ FN hypothesis REJECTED: govern_edited's name is fine; auth=open
    is then about codex's actual proof ⇒ leans genuine/inflation.

Machine-safe with no other local heavy-Lean proc. Run:
  python3 scripts/public/control/name_resolution_probe.py --n 4
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

OUT = "/tmp/rung1/_name_resolution_probe.json"


def _open_with_print(L, body: str, name: str, tag: str, timeout=160):
    tf = Path(f"/tmp/rung1/_nrp_{tag}.lean")
    tf.write_text(body + f"\n#print axioms {name}\n")
    of = L.open_file(str(tf), timeout=timeout)
    tf.unlink(missing_ok=True)
    errs = of.get("errors") or []
    raw = "\n".join(str(m.get("data", "")) for m in
                    (of.get("messages") or []))
    return {
        "ok": of.get("ok"),
        "n_errors": len(errs),
        "err_sample": (str(errs[0])[:200] if errs else ""),
        "print_line_error": bool(re.search(
            r"unknown (constant|identifier)|unexpected|ambiguous",
            (str(errs)[:1500] + raw[:1500]), re.I)),
        "sorryAx_seen": ("sorryax" in raw.lower()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    rows = cr.build_corpus()[: a.n]
    print(f"[nrp] {len(rows)} rows; warming REPL on {cr.SB.name} ...",
          flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    out = []
    for row in rows:
        full = row["target_name"]
        short = full.split(".")[-1]
        body = Path(row["sorried_file"]).read_text(errors="ignore")
        rs = _open_with_print(L, body, short, "short")
        rf = _open_with_print(L, body, full, "full")
        # verdict per row
        if rs["sorryAx_seen"] and not rs["print_line_error"]:
            v = "SHORT-RESOLVES (FN hypothesis rejected for this row)"
        elif (rf["sorryAx_seen"] and not rf["print_line_error"]) and \
             (rs["print_line_error"] or not rs["sorryAx_seen"]):
            v = "PATH-B FN (short fails, full resolves)"
        else:
            v = "INCONCLUSIVE (neither resolved cleanly — other issue)"
        rec = {"id": row["id"], "short": short, "full": full,
               "short_probe": rs, "full_probe": rf, "verdict": v}
        out.append(rec)
        print(f"  {row['id']:34s} short={short!r}\n"
              f"     short: err={rs['n_errors']} "
              f"print_line_error={rs['print_line_error']} "
              f"sorryAx={rs['sorryAx_seen']}\n"
              f"     full : err={rf['n_errors']} "
              f"print_line_error={rf['print_line_error']} "
              f"sorryAx={rf['sorryAx_seen']}\n"
              f"     => {v}", flush=True)
    L.close()
    Path(OUT).write_text(json.dumps(out, indent=1))
    fn = sum(1 for r in out if r["verdict"].startswith("PATH-B FN"))
    ok = sum(1 for r in out if r["verdict"].startswith("SHORT-RESOLVES"))
    print("\n=== NAME-RESOLUTION VERDICT ===")
    print(json.dumps({"n": len(out), "path_b_false_negative": fn,
                       "short_resolves_ok": ok,
                       "detail": OUT}, indent=1))
    if fn and not ok:
        print("PATH-B FALSE NEGATIVE CONFIRMED: govern_edited's "
              "`#print axioms <short>` does not resolve on real "
              "namespaced rows ⇒ 0/23 is a GATE ARTIFACT, the run is "
              "VOID, and it is NOT inflation. govern_edited must use "
              "the resolvable (full/namespace-qualified) name.")
    elif ok and not fn:
        print("FN hypothesis REJECTED: short name resolves; auth=open "
              "is about codex's actual proofs, not the gate.")
    else:
        print("MIXED/INCONCLUSIVE — inspect detail file per row.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
