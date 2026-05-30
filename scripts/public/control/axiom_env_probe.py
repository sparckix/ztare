#!/usr/bin/env python3
"""axiom_env_probe.py — validate the REAL fix design BEFORE touching
the authoritative gate (no guessing on FP-protocol #1).

Root cause: gate appends `#print axioms <n>` to a `module`-headered
file ⇒ "cannot use #print axioms in a module" ⇒ gate returns open for
EVERY row (whole authoritative run void).

Proposed fix: do NOT mutate the file / strip the header. Instead:
  env = open_file(unmutated module file)        # true context, validity
  raw = check("#print axioms <name>", env=env)  # REPL cmd vs that env

Hypothesis: the `module` restriction applies to the command appearing
in module SOURCE, not to a REPL command against an elaborated env ⇒
this returns real axioms with zero semantic change.

This probe DECIDES it on real Lean (machine-safe: one heavy proc):
  A. synthetic MODULE-headered known-good (trivial / Classical):
     env-cmd #print axioms ⇒ MUST be clean, NO module-restriction error
     (the missing real positive control: a module file that closes).
  B. real corpus sorried row (still `sorry`): env-cmd #print axioms
     ⇒ MUST show `sorryAx`, NO module-restriction error, name resolves.
If A clean & B shows sorryAx & neither hits the module error ⇒ design
VALIDATED, implement it. Else ⇒ fall back (separate importing file).

Run: python3 scripts/public/control/axiom_env_probe.py
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

MOD_ERR = re.compile(r"cannot use .#print axioms. in a .module.", re.I)
OUT = "/tmp/rung1/_axiom_env_probe.json"


def main() -> int:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    print(f"[aep] warming REPL on {cr.SB.name} ...", flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    td = Path(tempfile.mkdtemp())
    res = {}

    def env_axioms(env_id, name):
        r = L.check(f"#print axioms {name}", 90, env=env_id)
        raw = r.get("raw", "") or ""
        return {
            "module_restriction_error": bool(MOD_ERR.search(raw)),
            "sorryAx": ("sorryax" in raw.lower()),
            "no_axioms": ("does not depend on any axioms" in raw.lower()),
            "depends_line": bool(re.search(
                r"depends on axioms", raw, re.I)),
            "errors": r.get("errors", [])[:1],
            "raw_head": raw[:240],
        }

    # ---- A. synthetic MODULE-headered known-good (positive control) ----
    for tag, body, nm in [
        ("A_triv_module",
         "module\nimport Mathlib\n\ntheorem _aep_t : True := by "
         "trivial\n", "_aep_t"),
        ("A_classical_module",
         "module\nimport Mathlib\n\ntheorem _aep_c : ∀ p : Prop, "
         "p ∨ ¬ p := by\n  intro p; exact Classical.em p\n", "_aep_c"),
    ]:
        f = td / f"{tag}.lean"
        f.write_text(body)
        of = L.open_file(str(f), 180)
        res[tag] = {
            "open_ok": of.get("ok"),
            "open_errors": [str(e)[:160] for e in
                            (of.get("errors") or [])][:2],
            "env": of.get("env"),
            "axioms_via_env_cmd": (env_axioms(of.get("env"), nm)
                                   if of.get("env") is not None
                                   else "NO_ENV"),
        }
        print(f"  {tag}: open_ok={res[tag]['open_ok']} "
              f"env={res[tag]['env']} -> "
              f"{json.dumps(res[tag]['axioms_via_env_cmd'])[:260]}",
              flush=True)

    # ---- B. real corpus sorried rows (still `sorry`) -------------------
    rows = cr.build_corpus()[:2]
    for row in rows:
        full = row["target_name"]
        short = full.split(".")[-1]
        of = L.open_file(row["sorried_file"], 300)
        env = of.get("env")
        rec = {"id": row["id"], "open_ok": of.get("ok"),
               "open_errors": [str(e)[:160] for e in
                               (of.get("errors") or [])][:2],
               "env": env, "n_sorries": len(of.get("sorries") or [])}
        if env is not None:
            rec["axioms_full"] = env_axioms(env, full)
            rec["axioms_short"] = env_axioms(env, short)
        res[f"B_{row['id']}"] = rec
        print(f"  B_{row['id']}: open_ok={rec['open_ok']} env={env} "
              f"sorries={rec.get('n_sorries')}\n"
              f"     full : {json.dumps(rec.get('axioms_full'))[:240]}\n"
              f"     short: {json.dumps(rec.get('axioms_short'))[:240]}",
              flush=True)
    L.close()
    Path(OUT).write_text(json.dumps(res, indent=1))

    # ---- verdict ----
    a_ok = all(
        isinstance(res.get(t, {}).get("axioms_via_env_cmd"), dict)
        and not res[t]["axioms_via_env_cmd"]["module_restriction_error"]
        and (res[t]["axioms_via_env_cmd"]["no_axioms"]
             or res[t]["axioms_via_env_cmd"]["depends_line"])
        for t in ("A_triv_module", "A_classical_module"))
    b_ok = all(
        isinstance(res[k].get("axioms_full"), dict)
        and not res[k]["axioms_full"]["module_restriction_error"]
        and res[k]["axioms_full"]["sorryAx"]
        for k in res if k.startswith("B_"))
    print("\n=== AXIOM-ENV-PROBE VERDICT ===")
    if a_ok and b_ok:
        print("DESIGN VALIDATED: `check('#print axioms <name>', "
              "env=open_file().env)` works in real MODULE context — "
              "no module-restriction error, clean axioms for known-"
              "good, sorryAx detected for the sorried target. ⇒ "
              "implement: gate opens file UNMUTATED + collects axioms "
              "via env-command (one shared authoritative collector).")
    else:
        print(f"DESIGN NOT VALIDATED (a_ok={a_ok} b_ok={b_ok}) — "
              "inspect detail; fall back to a separate importing-file "
              "axiom query. Detail: " + OUT)
    print("detail:", OUT)
    return 0 if (a_ok and b_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
