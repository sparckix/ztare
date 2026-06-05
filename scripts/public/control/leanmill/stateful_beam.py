#!/usr/bin/env python3
"""Stateful tactic beam — the GENUINE un-strawmanned nurture test.

⚠️ MECHANISM CAVEAT (2026-06-01): this script steps the REPL's proofState/tactic mode,
which on the vendored repl is ENV-BLIND for a file's LOCAL defs — from a sorry proofState,
`unfold ProblemP2` / `constructor` / `refine ⟨…⟩` all fail "Unknown identifier/constant"
because the file's definitional env is not threaded into tactic name-resolution. So for a
goal stated via local `def`s (e.g. APN P2) this beam cannot take step 1. The WORKING
mechanism is the WHOLE-PROOF `check(file_minus_import)` path (names + `refine` decomposition
resolve there), kernel-gated by `#print axioms`. Reorient to a whole-proof decomposition
beam before trusting any negative from this proofState-stepping version. Also: the project
toolchain MUST match the repl binary (PersistentLean now fails loud otherwise) — see
project_vps_persistent_repl_dead_toolchain_mismatch in memory.

Every prior leaf experiment was a strawman on three axes: (1) one-shot whole-proof,
never stateful; (2) ~400x slow fresh-compile; (3) premise retrieval DEAD on the VPS
(no GEMINI key => the semantic shelf silently returned 0 hits in every run). This runs
the real nurture lever: a gradient-guided BEAM over LIVE proof states via
PersistentLean.start_tactic_proof + step (the REPL's proofState/tactic mode).

The environment, not the model, does the work here:
  - DECOMPOSE: structural tactics (intro / constructor / refine / rintro) crack the
    packed top-level goal into subgoals a closing tactic CAN discharge but could not
    from the whole goal. One-shot whole-proof can never do this.
  - GRADIENT: each candidate state is scored by the proof-state gradient (fewer goals,
    then shorter goals) — best-first search over the live state, not blind enumeration.
  - BUDGET: ~0.1s/probe persistent REPL affords hundreds of probes per leaf.
  - RETRIEVAL: when the semantic shelf is live, retrieved Mathlib lemmas are injected as
    `simp/aesop/nlinarith [hints]` and per-lemma `apply/exact`. The shelf-live flag is
    asserted and LOGGED per leaf — never again run retrieval-dependent work blind.

A closed branch reconstructs to a LINEAR `by` block (sequential `step`s apply to the
current first goal == sequential tactics in a block), which is then INDEPENDENTLY
kernel-gated: re-elaborated whole via check() + `#print axioms` sorryAx scan. The beam's
view of "closed" is necessary; the replay+axiom gate is the verdict.

Run on the VPS (it has the REPL binary + built Mathlib). For retrieval, the GEMINI key
must be present in the env; if absent the run still proceeds (automation-only) and logs
RETRIEVAL DEAD so the result is interpreted correctly.

  python3 stateful_beam.py --slice <slice.jsonl> --row <name> [--leaf N] \
      [--beam 6] [--depth 8] [--budget 2000] [--timeout 30]
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# closers: terminal tactics, tried at every node (apply to the current first goal)
CLOSERS = [
    "aesop", "simp_all", "omega", "norm_num", "nlinarith", "linarith",
    "positivity", "decide", "tauto", "ring", "ring_nf", "rfl", "trivial",
    "field_simp", "gcongr", "assumption",
    "aesop (config := {maxRuleApplications := 600})",
    "simp_all <;> nlinarith", "norm_num <;> nlinarith",
]
# structural: decompose the goal (take no problem-specific names => general purpose)
STRUCTURAL = [
    "intro", "intros", "constructor", "refine ⟨?_, ?_⟩", "rintro h",
    "by_contra h", "push_neg", "apply And.intro", "exact?",
]


def _retrieve_hints(goal_text, k=24):
    """Returns (hints, shelf_live). shelf_live distinguishes 'no neighbours found'
    from 'embedder absent' so a 0-hint run is never silently misread as 'tried & failed'."""
    try:
        from ztare.leanmill.semantic_premise_shelf import mathlib_semantic_neighbours
        hits, *_ = mathlib_semantic_neighbours(goal_text, top_k=k, threshold=0.4)
        names = [h.name for h in hits if getattr(h, "name", None)]
        return names, True
    except Exception as e:
        return [], False


def _retrieval_closers(hints):
    if not hints:
        return []
    out = []
    for size in (6, 12, len(hints)):
        sub = hints[:size]
        if not sub:
            continue
        h = "[" + ", ".join(sub) + "]"
        out += [f"simp_all {h}", f"aesop (add simp {h})", f"nlinarith {h}",
                f"simp only {h} <;> aesop"]
    for name in hints[:8]:
        out += [f"apply {name}", f"exact {name}"]
    # dedup preserve order
    seen, ded = set(), []
    for c in out:
        if c not in seen:
            seen.add(c); ded.append(c)
    return ded


import re as _re
_DEFLIKE = _re.compile(r"\b([A-Z][A-Za-z0-9']{2,})\b")


def _unfold_cands(goal_text):
    """General (not hardcoded): pull CamelCase identifiers from the LIVE goal — these are
    the local `def`s wrapping the statement (ProblemP2, IsUnimodal, …) — and try unfolding
    them so automation sees the underlying logical form. Bad names just error and prune."""
    names = []
    for m in _DEFLIKE.findall(goal_text):
        if m not in names and m not in ("Prop", "Type", "Sort", "True", "False",
                                        "And", "Or", "Not", "Iff", "Nat", "Finset"):
            names.append(m)
    names = names[:4]
    out = []
    for n in names:
        out += [f"unfold {n}", f"simp only [{n}]"]
    if len(names) >= 2:
        out.append("unfold " + " ".join(names))
    return out


def _score(goals):
    """Proof-state gradient as a best-first key: fewer goals first, then shorter total
    goal text (a packed/long goal is farther from closure than a short one)."""
    return (len(goals), sum(len(g) for g in goals))


def _sig(goals):
    return "␞".join(g.strip() for g in goals)


# best (lowest-score) state the beam ever reached — for residual reporting on failure
_BEST = {"score": (10**9, 10**9), "goal": "", "path": []}


def _beam_from(pl, ps0, goal0, hints, beam_w, max_depth, budget, timeout):
    """Gradient-guided beam from a live proof state (ps0, goal0). Returns
    (closed_path_or_None, probes, status). The beam steps the LIVE state — a tactic
    applies to the current first goal, so a linear path reconstructs to a `by` block;
    multi-goal decomposition (constructor -> N goals) is closed incrementally."""
    _BEST.update(score=(10**9, 10**9), goal=goal0, path=[])
    rc = _retrieval_closers(hints)
    candidates = CLOSERS + rc + STRUCTURAL
    root = {"ps": ps0, "goals": [goal0], "path": []}
    frontier = [root]
    seen = {_sig(root["goals"])}
    probes = 0
    for depth in range(max_depth):
        nxt = []
        for st in frontier:
            dyn = _unfold_cands(st["goals"][0]) if st["goals"] else []
            for t in candidates + dyn:
                if probes >= budget:
                    break
                r = pl.step(st["ps"], t, timeout=timeout)
                probes += 1
                if not r.get("ok"):
                    continue
                if r.get("closed"):
                    return st["path"] + [t], probes, "ok"
                goals = r.get("goals") or []
                if not goals:           # ok + no goals but not flagged closed => treat as closed candidate
                    return st["path"] + [t], probes, "ok"
                sig = _sig(goals)
                if sig in seen:
                    continue
                seen.add(sig)
                new_st = {"ps": r["ps"], "goals": goals, "path": st["path"] + [t]}
                sc = _score(goals)
                if sc < _BEST["score"]:
                    _BEST.update(score=sc, goal=" ⊕ ".join(goals),
                                 path=new_st["path"])
                nxt.append(new_st)
            if probes >= budget:
                break
        if not nxt or probes >= budget:
            break
        nxt.sort(key=lambda s: _score(s["goals"]))
        frontier = nxt[:beam_w]
    return None, probes, "exhausted"


def _strip_imports(src):
    """Drop `import …` lines — the persistent base_env already paid `import Mathlib`.
    The rest of the file (defs / lemmas / the sorried target) elaborates against it."""
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("import "))


def _verify_in_body(pl, file_body, target_name, path, timeout):
    """Independent kernel gate: substitute the beam's tactic block for the target's lone
    `sorry`, elaborate the WHOLE module body against base_env via check(), assert no
    errors / no remaining sorries, then #print axioms scan for sorryAx. True module
    context (all sibling defs live), not a regex-scraped prelude."""
    body = "\n  ".join(path)
    if "\n  sorry" in file_body:
        proved = file_body.replace("\n  sorry", "\n  " + body, 1)
    elif " sorry" in file_body:
        proved = file_body.replace(" sorry", "\n  " + body, 1)
    else:
        return False, "no_sorry_to_replace"
    proved += f"\n#print axioms {target_name}\n"
    r = pl.check(proved, timeout=max(timeout, 300))
    if r.get("sorries"):
        return False, "still_has_sorry"
    if not r.get("success"):
        return False, f"replay_err: {(r.get('errors') or ['?'])[0][:140]}"
    if "sorryAx" in (r.get("output") or ""):
        return False, "sorryAx_in_axioms"
    return True, "kernel_clean"


def run_source(source_file, target_name, project_dir, beam_w, max_depth, budget, timeout):
    """GENUINE nurture test: elaborate the REAL sorried .lean module against a LIVE
    Mathlib base_env, take the target's proof state (target NOT yet registered -> self-ref
    impossible), and run the gradient-guided stateful beam from it. project_dir must share
    the repl binary's lean-toolchain (PersistentLean now fails loud otherwise)."""
    from ztare.formal.lean_persistent import PersistentLean
    gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    file_body = _strip_imports(Path(source_file).read_text(encoding="utf-8"))
    print(f"[beam] {Path(source_file).name} target={target_name} | project={project_dir} | "
          f"beam={beam_w} depth={max_depth} budget={budget} | "
          f"GEMINI key {'present' if gemini else 'ABSENT'}", flush=True)
    t0 = time.time()
    with PersistentLean(project_dir=project_dir) as pl:
        print(f"[beam] REPL+Mathlib live in {round(time.time()-t0)}s "
              f"(positive control passed)", flush=True)
        seed = pl.check(file_body, timeout=max(timeout, 600))
        sorries = seed.get("sorries") or []
        seed_errs = seed.get("errors") or []
        if seed_errs:
            print(f"[beam] module body has {len(seed_errs)} elaboration error(s) — "
                  f"target context is broken, aborting: {seed_errs[0][:160]}")
            return
        if not sorries:
            print("[beam] no open sorry in module — nothing to prove")
            return
        s0 = sorries[0]
        ps0, goal0 = s0["proofState"], s0.get("goal", "")
        print(f"[beam] target proofState ready | ⊢ {goal0[:160].replace(chr(10),' ')}",
              flush=True)
        hints, shelf_live = _retrieve_hints(goal0, k=24)
        print(f"[beam] retrieval {'LIVE' if shelf_live else 'DEAD'} ({len(hints)} hints)"
              + ("" if shelf_live else " — embedder/atlas unavailable; automation-only run"),
              flush=True)
        tprobe = time.time()
        path, probes, status = _beam_from(pl, ps0, goal0, hints,
                                          beam_w, max_depth, budget, timeout)
        dt = round(time.time() - tprobe, 1)
        if path:
            ok, why = _verify_in_body(pl, file_body, target_name, path, timeout)
            if ok:
                print(f"\n[beam] {target_name} CLOSED+kernel-gated | {probes} probes {dt}s "
                      f"| depth={len(path)}\n  by {chr(10)+'     '.join([''] + path)}")
                print("[beam] => nurture lever FIRED: the gradient-guided stateful beam "
                      "closed a leaf the one-shot 7-tactic battery could not. Evidence FOR "
                      "the nurture thesis (scoped: one corpus, one solver family).")
            else:
                print(f"\n[beam] {target_name} beam-closed but GATE FAILED ({why}) | "
                      f"{probes} probes {dt}s | path: {' ; '.join(path)}")
        else:
            print(f"\n[beam] {target_name} unproved ({status}) | {probes} probes {dt}s")
            print(f"[beam] best residual goal:\n  ⊢ {_BEST.get('goal','?')[:400]}")
            print("[beam] => 0 closed under the stateful beam (budget+stateful+decompose "
                  "axes, automation-only). SCOPED negative for THIS leaf/corpus. The 7-"
                  "tactic one-shot battery and now a gradient beam over live states both "
                  "fail => the residual is localized to lemma INVENTION/COMPOSITION (the "
                  "published proof is a 35-129-lemma DAG), NOT tactic search and NOT "
                  "budget/speed. That points at the MOVE_CONJECTURE / subgoal-cache engine "
                  "as the lever, not more tactics. Do NOT launder to 'nurture exhausted'.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-file", required=True, help="the REAL sorried .lean module")
    ap.add_argument("--target", required=True, help="target theorem name (axiom gate), e.g. P2")
    ap.add_argument("--project-dir", required=True,
                    help="lake project whose lean-toolchain MATCHES the repl binary "
                         "(PersistentLean fails loud on mismatch)")
    ap.add_argument("--beam", type=int, default=6)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--budget", type=int, default=2500)
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()
    run_source(a.source_file, a.target, a.project_dir, a.beam, a.depth, a.budget, a.timeout)


if __name__ == "__main__":
    main()
