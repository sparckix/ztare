#!/usr/bin/env python3
"""Whole-proof decomposition beam — the LIVE-substrate re-measurement of "automation 0/3".

The proofState/tactic stepping mode is env-blind for a file's local defs, so the earlier
"stateful beam" could not even take step 1. The WORKING mechanism is whole-proof `check`:
names + `refine` decomposition resolve. This script, per APN row:

  1. CALIBRATES the substrate first (substrate_liveness.calibrate) — refuses to emit any
     number without a green stamp, so a dead REPL can never again read as "0 closed".
  2. Builds an env E once from the file's defs/lemmas (target theorem removed); every
     candidate is then checked against E via check(env=E) — fast (no full-file re-elab).
  3. DECOMPOSES the target: `refine ⟨?_,…⟩ <;> sorry` at the max arity that elaborates,
     reading each top-level component's statement from the returned sorries.
  4. For each component, runs an automation battery (decide/native_decide/norm_num/omega/
     simp_all/aesop, with and without local-def unfold hints), KERNEL-GATED by #print axioms
     (closed iff 0 errors, 0 sorries, and no sorryAx).

Reports per-row component-closure counts and the aggregate fraction across all rows —
the real number that replaces the void "0/3". Run on the VPS over the matched live pair.

  python3 decomposition_beam.py --slice <slice.jsonl> \
      --project-dir projects/atlas_lean_2026_05_29 [--row P2] [--budget 40]
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

IDENT = re.compile(r"\b([A-Za-z_][A-Za-z0-9_']*)\b")
NO_HINT_CLOSERS = ["decide", "native_decide", "rfl", "trivial", "omega", "norm_num",
                   "positivity", "simp_all", "aesop", "tauto"]


def _strip_imports(src):
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("import "))


def _local_defs(body):
    """Names introduced by the file (def/abbrev/lemma/theorem/structure/inductive)."""
    names = set()
    for m in re.finditer(r"(?m)^\s*(?:noncomputable\s+)?(?:def|abbrev|lemma|theorem|structure|inductive)\s+([A-Za-z_][A-Za-z0-9_'.]*)", body):
        names.add(m.group(1).split(".")[0])
    return names


def _target_type(body, target):
    """Extract T from `theorem <target> : T :=` (T may be a def name or an inline prop)."""
    m = re.search(rf"(?s)\btheorem\s+{re.escape(target)}\b\s*:\s*(.+?)\s*:=", body)
    return m.group(1).strip() if m else None


def _body_without_target(body, target):
    """Drop the target theorem (assumed last) so the rest forms a clean env."""
    m = re.search(rf"(?m)^\s*theorem\s+{re.escape(target)}\b", body)
    return body[:m.start()].rstrip() if m else body


def _candidates(hints, budget):
    cands = list(NO_HINT_CLOSERS)
    cands += [f"intros; {c}" for c in
              ["decide", "norm_num", "omega", "simp_all", "aesop", "positivity", "tauto"]]
    if hints:
        H = "[" + ", ".join(sorted(hints)[:10]) + "]"
        cands += [f"intros; simp_all {H}", f"simp_all {H}",
                  f"intros; aesop (add simp {H})", f"intros; norm_num {H}",
                  f"unfold {' '.join(sorted(hints)[:10])}; intros; simp_all",
                  f"intros; simp only {H} <;> norm_num",
                  f"intros; simp_all {H} <;> omega",
                  f"intros; simp_all {H} <;> nlinarith"]
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out[:budget]


def _hints_for(pl, env, comp_expr, local_defs):
    """Local defs referenced directly in the component, plus a 1-level #print expansion if
    the component is a single local def name."""
    toks = {t for t in IDENT.findall(comp_expr) if t in local_defs}
    head = comp_expr.strip()
    if head in local_defs:
        r = pl.check(f"#print {head}", timeout=60, env=env)
        for t in IDENT.findall(r.get("output") or ""):
            if t in local_defs:
                toks.add(t)
    toks.discard("Prop"); toks.discard("Type")
    return toks


_AXIOM_ALLOWLIST = {"propext", "Classical.choice", "Quot.sound"}
_AXIOM_LINE = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


def _kernel_closed(pl, env, comp_expr, cand, idx):
    """Kernel-clean closure gate. Guards against false positives on BOTH axes:
      - no remaining sorries / no elaboration errors (the proof actually elaborated);
      - #print axioms ⊆ {propext, Classical.choice, Quot.sound} — rejects sorryAx AND any
        other smuggled axiom (a proof that closes via `axiom`/native_decide-trust is not a
        genuine kernel proof). If the axioms line is absent we fail closed."""
    name = f"_zdb_{idx}"
    code = f"theorem {name} : {comp_expr} := by {cand}\n#print axioms {name}\n"
    r = pl.check(code, timeout=120, env=env)
    if not r.get("success") or (r.get("sorries") or []):
        return False
    out = r.get("output") or ""
    if "sorryAx" in out:
        return False
    if "does not depend on any axioms" in out:
        return True  # cleanest possible: empty axiom set
    m = _AXIOM_LINE.search(out)
    if not m:
        return False  # no axioms line surfaced → cannot certify; fail closed
    axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
    return axioms.issubset(_AXIOM_ALLOWLIST)


def _decompose(pl, env, T):
    """Return the list of top-level component statements (max-arity refine split)."""
    for n in range(6, 1, -1):
        anon = "⟨" + ", ".join(["?_"] * n) + "⟩"
        r = pl.check(f"theorem _zdb_probe : {T} := by refine {anon} <;> sorry",
                     timeout=120, env=env)
        if not (r.get("errors") or []):
            comps = []
            for s in (r.get("sorries") or []):
                g = (s.get("goal") or "")
                # goal field can be `case refine_1\n⊢ <prop>` — take the prop after last ⊢
                g = g.split("⊢")[-1].strip() if "⊢" in g else g.strip()
                if g:
                    comps.append(g)
            if comps:
                return comps
    return [T]


def _router_candidates(comp, hints, budget):
    """Vocabulary-driven candidate plan (obligation_router) — the A/B arm that tests
    whether typing the obligation + MM-3 reframes adds lift over the plain battery."""
    try:
        from ztare.leanmill.solver import obligation_router as orr
        ob, plan = orr.candidate_plan(comp, hints)
        return ob, plan[:budget]
    except Exception as e:
        return None, []


def run_row(pl, row, budget, use_router=False):
    src = _strip_imports(Path(row["source_file"]).read_text(encoding="utf-8"))
    target = row["target_theorem_name"]
    T = _target_type(src, target)
    if not T:
        print(f"  [{target}] could not parse target type — skip"); return (target, 0, 0, [])
    defs_body = _body_without_target(src, target)
    seed = pl.check(defs_body, timeout=600)
    if seed.get("errors"):
        print(f"  [{target}] env build has {len(seed['errors'])} errors — skip: "
              f"{seed['errors'][0][:120]}"); return (target, 0, 0, [])
    env = seed.get("env")
    local_defs = _local_defs(defs_body)
    comps = _decompose(pl, env, T)
    closed, detail = 0, []
    for i, comp in enumerate(comps):
        hints = _hints_for(pl, env, comp, local_defs)
        # A/B: plain battery vs vocabulary-driven router plan (same env, same gate)
        won_bat = None
        for j, cand in enumerate(_candidates(hints, budget)):
            if _kernel_closed(pl, env, comp, cand, f"b{i}_{j}"):
                won_bat = cand; break
        ob, plan = _router_candidates(comp, hints, budget)
        won_rt = None
        for j, cand in enumerate(plan):
            if _kernel_closed(pl, env, comp, cand, f"r{i}_{j}"):
                won_rt = cand; break
        obtag = f"{ob.obligation}/{ob.op_id}" if ob else "?"
        if won_bat or won_rt:
            closed += 1
            arm = ("both" if won_bat and won_rt else "battery-only" if won_bat
                   else "ROUTER-ONLY")
            detail.append((comp[:44], f"CLOSED[{arm}]", (won_rt or won_bat)[:40], obtag))
        else:
            detail.append((comp[:44], "open", "", obtag))
    print(f"  [{target}] components {closed}/{len(comps)}:")
    for c, st, w, obtag in detail:
        print(f"      [{obtag:16}] {st:18} ⊢ {c}" + (f"   by {w}" if w else ""))
    return (target, closed, len(comps), detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--row", default=None, help="only this target (e.g. P2); default all")
    ap.add_argument("--budget", type=int, default=40, help="max candidate bodies per component")
    a = ap.parse_args()
    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import calibrate

    proj = str((REPO / a.project_dir).resolve()
               if not Path(a.project_dir).is_absolute() else Path(a.project_dir))
    rows = [json.loads(l) for l in Path(a.slice).read_text().splitlines() if l.strip()]
    if a.row:
        rows = [r for r in rows if r.get("target_theorem_name") == a.row]
    with PersistentLean(project_dir=proj) as pl:
        rep = calibrate(pl)   # FAIL-CLOSED: no admissible negative without a green stamp
        print(rep.banner())
        print(f"[decomp-beam] {len(rows)} row(s), budget={a.budget}/component\n", flush=True)
        tot_c, tot_n, results = 0, 0, []
        t0 = time.time()
        for row in rows:
            target, c, n, _ = run_row(pl, row, a.budget)
            tot_c += c; tot_n += n; results.append((target, c, n))
        print(f"\n[decomp-beam] AGGREGATE: {tot_c}/{tot_n} components closed kernel-clean "
              f"across {len(rows)} rows ({round(time.time()-t0)}s)")
        print("[decomp-beam] per-row: " + ", ".join(f"{t}={c}/{n}" for t, c, n in results))
        frac = (tot_c / tot_n) if tot_n else 0.0
        print(f"[decomp-beam] closed fraction = {frac:.2f} "
              f"(forecast 0.30). Residual components localize where invention/MOVE_CONJECTURE "
              f"is the lever; SCOPED to this corpus, calibrated substrate.")


if __name__ == "__main__":
    main()
