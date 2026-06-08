#!/usr/bin/env python3
"""Subgoal decomposition + GLOBAL proven-lemma cache — the AlphaProof-distinctive engine.

The fair matrix showed providers land ONE goal short on leak-clean APN rows: the last
goal needs a BESPOKE helper lemma they can't produce in one shot. AlphaProof-Nexus's
distinctive move (arXiv 2605.22763) is exactly this: when stuck, prove the subgoal as a
delegated task and CACHE it globally so it's reused everywhere. Generic best-of-N is NOT
the distinctive part; subgoal-construction + a shared proven-lemma cache is.

Mechanism (grounded in Lean's `extract_goal`):
  1. Attempt the target (few samples). If it closes → done.
  2. Take a leaving goal; insert `extract_goal` at that point and compile → Lean PRINTS the
     stuck goal as a STANDALONE theorem statement (all hypotheses as binders). Parse it.
  3. Look it up in the GLOBAL cache (normalized signature). Hit → reuse the cached lemma.
  4. Miss → prove the standalone lemma (a smaller search; may itself decompose, bounded
     depth). On success, CACHE {signature → statement + proof} globally.
  5. Inject the proven helper lemma(s) into the target context as available premises and
     retry the target → the parent that was one goal short now closes.

The cache is GLOBAL and PERSISTENT (across rows/runs) — APN rows share scaffolding, so a
helper proved for one row accelerates others (the paper's shared-memory speedup).

Modes:  --probe-extract  (de-risk: just step 2 on a seeded partial — does extract_goal
                          yield a parseable standalone lemma?)
        --solve          (full loop on the row)
Run on the VPS. Context = self-contained materialized goal (leak-clean).
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.solver.proof_state import proof_state_signal  # noqa: E402
import provider_registry as reg  # noqa: E402

CACHE_PATH = REPO / "analytics/public/leanmill/proven_lemma_cache.jsonl"
_DECL_LEMMA_RE = re.compile(r"(?ms)^\s*theorem\s+extracted_?\w*\s*.*?:=\s*by\s*sorry")
# extract_goal prints e.g.  `theorem extracted_1 (n : ℕ) ... : <goal> := by\n  sorry`
_EXTRACTED_RE = re.compile(r"(?ms)(theorem\s+[\w.]+[\s\S]*?)\s*:=\s*(?:by\b|sorry\b)")


def _strip(t: str) -> str:
    t = (t or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    return t[3:].lstrip() if t.startswith("by ") or t == "by" else t


def _norm_sig(stmt: str) -> str:
    """Normalize a lemma statement for cache keying (whitespace + extracted-name agnostic)."""
    s = re.sub(r"theorem\s+[\w.]+", "theorem _", stmt)
    return re.sub(r"\s+", " ", s).strip()


def extract_subgoal(rid, goal, partial_proof, lean_root, timeout_s) -> "str | None":
    """Fire `extract_goal` at the stuck point of a partial proof and return the standalone
    lemma statement Lean prints. If the partial uses `sorry` (the structural-progress-then-
    sorry pattern), replace the FIRST sorry with `extract_goal` so it fires exactly where
    the model gave up; otherwise append it. Returns the lemma statement, or None."""
    from solver_lane_worker import _verify_compile  # reuse the canonical compile path
    p = (partial_proof or "").rstrip()
    if re.search(r"\bsorry\b", p):
        body = re.sub(r"\bsorry\b", "extract_goal", p, count=1)
    else:
        body = p + "\n  extract_goal"
    _ok, tail = _verify_compile(rid, goal, body, lean_root, timeout_s)
    m = _EXTRACTED_RE.search(tail or "")
    return m.group(1).strip() if m else None


def gen_partial_with_sorry(provider, goal, timeout_s) -> str:
    """Generate a partial proof that makes STRUCTURAL progress (intro/constructor/cases/
    unfold) and leaves an explicit `sorry` for the hard remaining goal. This reliably
    yields a clean goal state for `extract_goal` — unlike a failed full attempt, which
    tends to error before any well-formed residual."""
    prompt = ("Begin proving this Lean theorem. Make REAL structural progress (unfold "
              "definitions, intro/constructor/obtain/rcases as appropriate) and leave a "
              "single `sorry` for the one hard remaining goal you cannot immediately close. "
              "The body must COMPILE (only the `sorry` open). Reply ONLY the proof body "
              f"after `by`:\n{goal}")
    return _gen(provider, prompt, timeout_s)


def decompose_conjuncts(rid, goal, stmt_def, lean_root, timeout_s) -> list[str]:
    """Unfold the statement def + split top-level ∧ via `repeat' apply And.intro`; read the
    leaf conjunct propositions from the resulting unsolved-goals block. These named
    conjuncts ARE the natural subgoals (cleaner than extract_goal). Returns the goal-prop
    strings (the text after each `⊢`)."""
    from solver_lane_worker import _verify_compile
    from ztare.leanmill.solver.proof_state import extract_unsolved_goals
    body = f"unfold {stmt_def}\n  repeat' apply And.intro"
    _ok, tail = _verify_compile(rid, goal, body, lean_root, timeout_s)
    # `repeat' apply And.intro` leaves ALL leaf goals in ONE block, separated by
    # `case …` markers. Each `⊢ <prop>` line is a SEPARATE conjunct subgoal — split per ⊢.
    conjuncts = []
    for blk in extract_unsolved_goals(tail or ""):
        for m in re.finditer(r"⊢\s*([^\n]+)", blk):
            c = m.group(1).strip()
            if c and c not in conjuncts:
                conjuncts.append(c)
    return conjuncts


def prove_in_context(provider, context_defs, conjunct, lean_root, timeout_s, n) -> "str | None":
    """Best-of-N prove a leaf conjunct as a standalone lemma WITH the statement context
    (the conjunct references context defs). Returns proof body or None."""
    from solver_lane_worker import _verify_compile
    goal = f"{context_defs}\n\ntheorem leaf_h : {conjunct} := by"
    for i in range(n):
        body = _gen(provider, f"Prove this Lean lemma (definitions above are in scope). "
                              f"Reply ONLY the proof body after `by`:\n{goal}", timeout_s)
        if body and _verify_compile("leaf", goal, body, lean_root, timeout_s)[0]:
            return body
    return None


def _retrieve_hints(goal_text: str, k: int = 12) -> list[str]:
    """Top-k Mathlib lemma NAMES semantically near the goal — the premise hints to
    throw at the automation battery. Empty list if retrieval unavailable."""
    try:
        sys.path.insert(0, str(REPO / "src"))
        from ztare.research_director.apn_semantic import apn_semantic_neighbours  # noqa
    except Exception:
        pass
    try:
        from ztare.leanmill.semantic_premise_shelf import mathlib_semantic_neighbours
        hits, *_ = mathlib_semantic_neighbours(goal_text, top_k=k, threshold=0.45)
        return [h.name for h in hits if getattr(h, "name", None)]
    except Exception:
        return []


def prove_in_context_automation(context_defs, conjunct, lean_root, timeout_s, stmt_def=None) -> "str | None":
    """NATIVE-AGENTIC, LLM-FREE leaf prover: throw the verifier's heavy automation +
    decision procedures at the goal, with MANY retrieved premise hints injected — the
    void a human won't explore (nobody hand-tries 12 lemmas in nlinarith), but the
    kernel prunes for free. Returns the first proof body that closes, or None."""
    from solver_lane_worker import _verify_compile
    hints = _retrieve_hints(conjunct, k=12)
    hint_str = ("[" + ", ".join(hints) + "]") if hints else ""
    unfold = f"unfold {stmt_def}\n  " if stmt_def else ""
    # Verifier-cheap battery, cheap→heavy. Each is a complete proof body candidate.
    battery = [
        "decide", "native_decide", "rfl", "trivial",
        "aesop", "simp_all", "omega", "norm_num", "positivity",
        f"simp_all {hint_str}" if hint_str else "simp_all",
        f"aesop (add simp {hint_str})" if hint_str else "aesop",
        f"nlinarith {hint_str}" if hint_str else "nlinarith",
        f"intro _ <;> simp_all {hint_str}" if hint_str else "intro _ <;> simp_all",
        f"constructor <;> simp_all {hint_str}" if hint_str else "constructor <;> simp_all",
        "intros <;> aesop",
        f"first | exact? | aesop | simp_all {hint_str}" if hint_str else "first | exact? | aesop",
    ]
    goal = f"{context_defs}\n\ntheorem leaf_auto : {conjunct} := by"
    for tac in battery:
        body = f"{unfold}{tac}"
        if _verify_compile("leaf_auto", goal, body, lean_root, timeout_s)[0]:
            return f"by {body}"
    return None


def _gen(provider, prompt, timeout_s) -> str:
    try:
        return _strip(reg.invoke(provider, goal_text=prompt, timeout_s=timeout_s).get("proof_text", ""))
    except Exception:
        return ""


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    out = {}
    for l in CACHE_PATH.read_text().splitlines():
        if l.strip():
            try:
                r = json.loads(l); out[r["sig"]] = r
            except Exception:
                pass
    return out


def _cache_put(sig, statement, proof, source):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("a") as f:
        f.write(json.dumps({"sig": sig, "statement": statement, "proof": proof, "source": source}) + "\n")


def prove_statement(provider, statement, lean_root, timeout_s, n=4) -> "str | None":
    """Best-of-N attempt to prove a STANDALONE lemma statement (no decomposition here —
    this is the leaf solver; the parent loop owns decomposition). Returns proof body or None."""
    from solver_lane_worker import _verify_compile
    sig = _norm_sig(statement)
    cache = _load_cache()
    if sig in cache:
        return cache[sig]["proof"]
    goal = statement.rstrip() + " := by"
    for i in range(n):
        body = _gen(provider, f"Prove this Lean lemma. Reply ONLY the proof body after `by`:\n{goal}", timeout_s)
        if not body:
            continue
        ok, _tail = _verify_compile("subgoal", goal, body, lean_root, timeout_s)
        if ok:
            _cache_put(sig, statement, body, "subgoal_solver")
            return body
    return None


def solve(row, provider, lean_root, timeout_s, n=4) -> dict:
    from solver_lane_worker import _verify_compile, _validate_against_contract, _build_solver_action_contract
    rid = row.get("row_id", "anon"); tgt = row.get("target_theorem_name") or ""
    goal = (row.get("goal") or "").strip()
    # 1. direct best-of-N
    best = None
    for i in range(n):
        body = _gen(provider, f"Prove this Lean theorem. Reply ONLY the proof body after `by`:\n{goal}", timeout_s)
        if not body:
            continue
        ok, tail = _verify_compile(rid, goal, body, lean_root, timeout_s)
        if ok:
            return {"row_id": rid, "closed": True, "via": "direct"}
        sig = proof_state_signal(1, tail)
        if best is None or (sig["goals_remaining"] or 99) < (best[2] or 99):
            best = (body, tail, sig["goals_remaining"])
    # 2. extract the stuck subgoal as a standalone lemma. Prefer a purpose-generated
    #    structural-progress-then-`sorry` partial (reliable extract point); fall back to
    #    the best failed direct attempt.
    partial = gen_partial_with_sorry(provider, goal, timeout_s)
    stmt = extract_subgoal(rid, goal, partial, lean_root, timeout_s)
    if not stmt and best is not None:
        stmt = extract_subgoal(rid, goal, best[0], lean_root, timeout_s)
    if not stmt:
        return {"row_id": rid, "closed": False, "via": "extract_failed",
                "best_goals": best[2] if best else None}
    print(f"  [{rid[:20]}] extracted subgoal lemma:\n    {stmt[:160]}", flush=True)
    # 3-4. prove (and cache) the subgoal
    helper_proof = prove_statement(provider, stmt, lean_root, timeout_s, n=n)
    if not helper_proof:
        return {"row_id": rid, "closed": False, "via": "subgoal_unproved", "subgoal": stmt[:200]}
    print(f"  [{rid[:20]}] SUBGOAL PROVED + cached.", flush=True)
    # 5. inject the proven helper as a premise, retry the target
    helper_name = "cached_helper_1"
    helper_decl = re.sub(r"theorem\s+[\w.]+", f"theorem {helper_name}", stmt) + f" := by\n{helper_proof}\n"
    injected_goal = f"{helper_decl}\n\n{goal}"
    for i in range(n):
        body = _gen(provider, f"Prove this Lean theorem; the lemma `{helper_name}` above is available. "
                              f"Reply ONLY the proof body after the final `by`:\n{injected_goal}", timeout_s)
        if not body:
            continue
        ok, tail = _verify_compile(rid, injected_goal, body, lean_root, timeout_s)
        if ok:
            contract = _build_solver_action_contract(row, lean_root)
            v = _validate_against_contract(contract=contract, proof_text=body, enriched_goal=injected_goal,
                    target_name=tgt, lean_root=lean_root, timeout_s=timeout_s, kernel_compile_ok=True,
                    kernel_compile_tail=tail)
            return {"row_id": rid, "closed": True, "via": "subgoal_cache",
                    "mnc": v["receipts"]["matched_negative_control_receipt"]["passed"]}
    return {"row_id": rid, "closed": False, "via": "parent_still_open_after_helper", "subgoal": stmt[:120]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--row", required=True, help="single target name / row substring (ONE row)")
    ap.add_argument("--provider", default="claude_opus")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=400)
    ap.add_argument("--lean-root", default=str(REPO / "ztare_proofs"))
    ap.add_argument("--probe-extract", action="store_true",
                    help="de-risk: only run extract_goal on a one-shot partial and print the lemma")
    ap.add_argument("--decompose", action="store_true",
                    help="decompose the target into conjunct subgoals + best-of-N each leaf in "
                         "context — is the LEAF the wall? (the decisive test)")
    ap.add_argument("--automation", action="store_true",
                    help="NATIVE-AGENTIC (de-anchored): prove leaves with LLM-FREE heavy "
                         "automation + retrieved hints (the void a human won't try), not best-of-N")
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.slice).read_text().splitlines() if l.strip()]
    row = next((r for r in rows if r.get("target_theorem_name") == a.row or a.row in r.get("row_id", "")), None)
    if not row or not (row.get("goal") or "").strip():
        print(f"row {a.row!r} not found / no goal"); return 1
    print(f"[subgoal_cache] row={row.get('row_id')} provider={a.provider} n={a.n} probe={a.probe_extract}")
    if a.probe_extract:
        goal = row["goal"].strip()
        body = _gen(a.provider, f"Prove this Lean theorem. Reply ONLY the proof body after `by`:\n{goal}", a.timeout)
        stmt = extract_subgoal(row.get("row_id", "x"), goal, body, Path(a.lean_root), a.timeout)
        print("extract_goal yielded:\n" + (stmt or "(none — extract_goal did not fire / parse)"))
        return 0
    if a.decompose:
        goal = row["goal"].strip(); rid = row.get("row_id", "x")
        tgt = row.get("target_theorem_name") or ""
        stmt_def = (row.get("materialization", {}).get("seeds") or [tgt])[0]
        context_defs = goal[:goal.rfind(f"theorem {tgt}")].rstrip()
        conj = decompose_conjuncts(rid, goal, stmt_def, Path(a.lean_root), a.timeout)
        print(f"[decompose] {stmt_def} → {len(conj)} leaf conjunct subgoals:")
        for c in conj:
            print(f"    ⊢ {c[:100]}")
        closed = 0
        for i, c in enumerate(conj):
            if getattr(a, "automation", False):
                p = prove_in_context_automation(context_defs, c, Path(a.lean_root), a.timeout, stmt_def=stmt_def)
            else:
                p = prove_in_context(a.provider, context_defs, c, Path(a.lean_root), a.timeout, a.n)
            ok = p is not None
            if ok:
                closed += 1
                S_sig = _norm_sig(f"theorem _ : {c}")
                _cache_put(S_sig, f"theorem leaf : {c}", p, f"{rid}:leaf{i}")
            print(f"  leaf{i}: {'PROVED+cached' if ok else 'unproved'}  ⊢ {c[:60]}", flush=True)
        print(f"\n[decompose] LEAVES CLOSED: {closed}/{len(conj)} "
              f"{'→ harness can assemble; closure achievable' if closed==len(conj) and conj else '→ leaf conjunct(s) are the wall (the RL-solver gap)'}")
        return 0
    t0 = time.time()
    res = solve(row, a.provider, Path(a.lean_root), a.timeout, n=a.n)
    print(f"[subgoal_cache] RESULT: {res}  ({round(time.time()-t0)}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
