#!/usr/bin/env python3
"""inspect_open_row.py — same-artifact dual-verdict, isolates whether
the light↔authoritative divergence is VERIFIER LAXITY or CORPUS/hardness.

Discriminator already ruled out H2 (gate is invoked cleanly). Open
question: the old light run got 27/30; the authoritative run gets
0/23 — but corpus AND verifier both changed. This isolates the
VERIFIER variable: run codex ONCE per row (the proven path, verbatim),
then judge the SAME codex-edited file with BOTH criteria:

  light_verdict : the OLD notion — file elaborates ok AND no leftover
                  `sorry`/`admit` near target. (NO #print axioms.)
  auth_verdict  : cr.govern_edited — #print axioms ⊆ STD, no sorryAx,
                  no self-name leak. (the authoritative gate.)

  light=solved & auth=NOT  -> inflation mechanism DEMONSTRATED on the
                              same artifact (the old number was lax).
  both = NOT-solved        -> codex genuinely does not close these rows
                              -> 0/23 is row-hardness, prior 27/30 was a
                              different/easier population (not proven
                              inflation).
  light=NOT & auth=solved  -> (shouldn't happen; auth ⊆ light)

Reuses the proven prover VERBATIM (cr.attempt's codex call) but does
NOT delete the iso dir, so the edited file is inspectable.

Run: python3 scripts/public/control/inspect_open_row.py --n 2
Machine-safe ONLY with no other local heavy-Lean proc (verify first).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

OUT = "/tmp/rung1/_inspect_open_rows.json"


def light_verdict(L, edited_file: str, target_line: int,
                  target_name: str, timeout: int) -> dict:
    """Mimic the OLD light _verify on the SAME edited file: opens it
    (NO #print axioms appended), ok + no errors + no leftover sorry
    near the target ⇒ 'solved'. This is the lax criterion."""
    short = target_name.split(".")[-1]
    try:
        body = Path(edited_file).read_text(errors="ignore")
    except Exception:
        return {"light": "unverified"}
    if re.search(r":=\s*by\s*\n\s*sorry", body) or "admit" in body:
        return {"light": "open(textual sorry/admit)"}
    tf = Path(edited_file + ".light.lean")
    tf.write_text(body)            # NOTE: no `#print axioms`
    of = L.open_file(str(tf), timeout=timeout)
    tf.unlink(missing_ok=True)
    if not of.get("ok"):
        return {"light": "unverified"}
    leftover = [s for s in of.get("sorries", [])
                if s.get("line") and abs(s["line"] - target_line) <= 3]
    if of.get("errors") or leftover:
        return {"light": "open",
                "errs": len(of.get("errors") or []),
                "sorries_near": len(leftover)}
    return {"light": "solved"}     # lax: compiles + no sorry near target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=float, default=400.0)
    a = ap.parse_args()

    import coherent_rung1 as cr
    import codex_proofstate_pilot as _PP
    import codex_proofstate_pilot_fast as _PF
    import tool_router as tr
    from src.ztare.formal.lean_persistent import PersistentLean

    rows = cr.build_corpus()[: a.n]
    print(f"[insp] {len(rows)} rows; warming REPL on {cr.SB.name} ...",
          flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    pool = Path("/tmp/rung1/_insp_pool")
    pool.mkdir(parents=True, exist_ok=True)
    out = []
    for row in rows:
        rid = row["id"]
        print(f"[insp] {rid} : codex (proven path, verbatim) ...",
              flush=True)
        iso = _PF._row_iso(Path(cr.ISO_BASE), pool, rid)
        fn = "mcb_target.lean"
        shutil.copy(row["sorried_file"], iso / fn)
        prompt = _PP.STATE_PROMPT.format(fname=fn) + " " + cr.CHEAP_HINT
        t0 = time.time()
        ok, _m = _PF._codex_hard(prompt, a.model, "workspace-write",
                                 str(iso), int(a.budget),
                                 iso / "lastmsg.txt")
        secs = round(time.time() - t0, 1)
        edited = str(iso / fn)
        rec = {"id": rid, "gold_steps": row.get("gold_n_steps"),
               "codex_ok": ok, "secs": secs}
        if not ok:
            rec["light"] = rec["auth"] = "codex_no_output"
        else:
            lv = light_verdict(L, edited, row["target_line"],
                               row["target_name"], 160)
            av = cr.govern_edited(L, edited, row["target_line"],
                                  row["target_name"], 160)
            rec.update(lv)
            rec["auth"] = av.get("verdict")
            rec["auth_axioms"] = av.get("axioms_deps")
            # save the codex-edited proof block for the operator
            try:
                body = Path(edited).read_text(errors="ignore")
                blk = _PP._target_block(
                    body, row["target_name"].split(".")[-1])
                rec["edited_proof_snippet"] = blk[:900]
            except Exception:
                rec["edited_proof_snippet"] = "(unavailable)"
        # classify the divergence
        lt = str(rec.get("light"))
        at = str(rec.get("auth"))
        if lt == "solved" and at != "closure":
            rec["finding"] = ("INFLATION DEMONSTRATED (same artifact: "
                              "light=solved, auth=" + at + ")")
        elif lt != "solved" and at != "closure":
            rec["finding"] = ("genuine non-closure (both reject) -> "
                              "row-hardness, not proven inflation")
        elif at == "closure":
            rec["finding"] = "actually closes authoritatively"
        else:
            rec["finding"] = "unexpected"
        print(f"  -> light={rec.get('light')} auth={rec.get('auth')} "
              f":: {rec['finding']}", flush=True)
        out.append(rec)
        shutil.rmtree(iso, ignore_errors=True)
    L.close()
    Path(OUT).write_text(json.dumps(out, indent=1))
    infl = sum(1 for r in out if "INFLATION" in str(r.get("finding")))
    hard = sum(1 for r in out if "row-hardness" in str(r.get("finding")))
    print("\n=== INSPECTION SUMMARY ===")
    print(json.dumps({"n": len(out),
                       "inflation_demonstrated": infl,
                       "genuine_non_closure": hard,
                       "detail_file": OUT}, indent=1))
    print("READ: light=solved & auth≠closure on the SAME file ⇒ the old "
          "light number was lax. both reject ⇒ codex just doesn't close "
          "these rows (prior 27/30 = different/easier set).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
