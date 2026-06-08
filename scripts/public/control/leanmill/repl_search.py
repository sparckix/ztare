#!/usr/bin/env python3
"""Persistent-REPL nurture test — was the hard-leaf failure a BUDGET/SPEED strawman?

Every prior leaf experiment used ~40s fresh `lake env lean` per attempt and ran ~5
candidates. The repo has `lean_persistent.PersistentLean` — the canonical leanprover
REPL as a long-lived process, `import Mathlib` paid ONCE, then ~0.1s per probe. That is
~400× faster, so it affords HUNDREDS of candidate probes per leaf instead of five. This
runs that budget: a large automation × retrieved-hint candidate pool against a leaf, via
the persistent REPL. If a hard leaf closes under proper budget, "talent-bound" was a
strawman (too few, too slow, stateless attempts), not an insight ceiling.

NOT the full stateful tactic-beam (PersistentLean exposes whole-cmd probes, not the
REPL's incremental proofState mode — that is the next, deeper nurture build). This is the
cheapest genuine nurture test the built infra allows. Run on the VPS.
"""
from __future__ import annotations
import argparse, json, itertools, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))


def _retrieve_hints(goal_text, k=24):
    try:
        from ztare.leanmill.semantic_premise_shelf import mathlib_semantic_neighbours
        hits, *_ = mathlib_semantic_neighbours(goal_text, top_k=k, threshold=0.4)
        return [h.name for h in hits if getattr(h, "name", None)]
    except Exception:
        return []


def _candidate_bodies(stmt_def, hints):
    """A LARGE pool of LLM-FREE candidate proof bodies: the automation battery crossed
    with retrieved-hint subsets. Cheap to enumerate; the persistent REPL prunes."""
    unfold = f"unfold {stmt_def}; " if stmt_def else ""
    base = ["decide", "native_decide", "rfl", "trivial", "aesop", "simp_all", "omega",
            "norm_num", "positivity", "tauto", "constructor <;> aesop",
            "intro _ <;> aesop", "intros <;> simp_all", "constructor <;> simp_all",
            "refine ⟨?_, ?_⟩ <;> aesop", "aesop (config := {maxRuleApplications := 400})"]
    cands = [unfold + t for t in base]
    # hint-injected automation: try several hint subset sizes (the void a human won't hand-try)
    for size in (4, 8, 16, len(hints)):
        sub = hints[:size]
        if not sub:
            continue
        h = "[" + ", ".join(sub) + "]"
        cands += [unfold + f"simp_all {h}", unfold + f"aesop (add simp {h})",
                  unfold + f"nlinarith {h}", unfold + f"simp only {h} <;> aesop"]
    # dedup, preserve order
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def run(slice_path, row_name, only_leaf, timeout_s):
    import subgoal_cache as S
    from ztare.formal.lean_persistent import PersistentLean
    rows = [json.loads(l) for l in Path(slice_path).read_text().splitlines() if l.strip()]
    row = next((r for r in rows if r.get("target_theorem_name") == row_name or row_name in r.get("row_id", "")), None)
    goal = (row.get("goal") or "").strip(); tgt = row.get("target_theorem_name")
    stmt_def = (row.get("materialization", {}).get("seeds") or [tgt])[0]
    context_defs = goal[:goal.rfind(f"theorem {tgt}")].rstrip()
    conj = S.decompose_conjuncts(row.get("row_id", "x"), goal, stmt_def, REPO / "ztare_proofs", 400)
    if only_leaf is not None:
        conj = [c for i, c in enumerate(conj) if i == only_leaf]
    print(f"[repl_search] {tgt}: {len(conj)} leaf(s); persistent REPL warming (import Mathlib once)…", flush=True)
    t0 = time.time()
    closed = 0
    with PersistentLean(project_dir=str(REPO / "ztare_proofs")) as pl:
        print(f"[repl_search] REPL ready in {round(time.time()-t0)}s", flush=True)
        for i, c in enumerate(conj):
            hints = _retrieve_hints(c, k=24)
            cands = _candidate_bodies(None, hints)   # conj is already the unfolded prop
            probes = 0; got = None; tprobe = time.time()
            for body in cands:
                code = f"{context_defs}\n\ntheorem leaf_repl : {c} := by\n  {body}\n"
                r = pl.check(code, timeout=timeout_s)
                probes += 1
                errs = r.get("errors") or []
                sorries = r.get("sorries") or []
                if r.get("success") and not errs and not sorries:
                    got = body; break
            dt = round(time.time() - tprobe, 1)
            if got:
                closed += 1
                print(f"  leaf{i} CLOSED via REPL after {probes} probes ({dt}s): {got[:70]}", flush=True)
            else:
                print(f"  leaf{i} unproved after {probes} probes ({dt}s): ⊢ {c[:60]}", flush=True)
    print(f"\n[repl_search] LEAVES CLOSED (persistent-REPL budget): {closed}/{len(conj)} "
          f"{'→ talent-bound was a BUDGET/SPEED strawman' if closed else '→ even proper-budget automation fails; next = stateful tactic beam, not a talent verdict yet'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True); ap.add_argument("--row", required=True)
    ap.add_argument("--leaf", type=int, default=None, help="only this leaf index (0-based)")
    ap.add_argument("--timeout", type=int, default=30)
    a = ap.parse_args()
    run(a.slice, a.row, a.leaf, a.timeout)


if __name__ == "__main__":
    main()
