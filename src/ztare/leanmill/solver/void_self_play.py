"""Void self-play corpus amplifier (expert-iteration accelerant, 2026-07-01) — the buildable lever that makes the
expert-iteration loop viable. (NOTE: "expert iteration" is the proper name — Polu et al. / AlphaProof /
DeepSeek-Prover: generate kernel-verified proofs → train the next prover on them → repeat. NOT the codebase's
constraint-isomorphism "strange loop", which is a different, architecture-self-observation tool.)

WHY. Expert iteration (kernel-verified void-novel proofs → training corpus → a specialized prover leaf) is the
one CAUSAL compounding moat, but it is GATED ON CORPUS SIZE: the export today is ~1e2 pairs, and SFT wants ~1e4+.
Shipping targets one at a time grows it linearly. Self-play grows it super-linearly PER SEED: take a proven
void-novel theorem, generate related conjectures near the current ability frontier, prove them through the
UNCHANGED governed pipeline, and let the existing bank + `export_training_corpus` capture the new closures. This
is STP's conjecturer→prover loop (arxiv 2502.00212) WITHOUT weight-training the conjecturer — the point here is
CORPUS VOLUME in a domain whose data is uniquely ours, not a trained conjecturer.

SCOPE (deliberate). VOID ONLY (non-math + novel formal domains). Self-play on MATH would regenerate a corpus the
big-compute provers already have 100x of, on their metric where our differentiator is invisible; in the void the
data is ours. Raw proving strength is a separate, already-designed path (plug a SOTA prover as a leaf/provider
slot); this module does not touch it.

REUSE, NOT FRANKENSTEIN (the standing anti-sibling rule). Every heavy piece already exists:
  • generalize transform  → `anti_unify.anti_unify` + `schema_conjecture_seed` (LGG of the seed vs a banked sibling)
  • specialize transform  → `conjecture.specialize_generate` / `specialization_substantive` (non-triviality gate)   [deferred]
  • compose transform     → the banked-lemma composition idea (task #70)                                            [deferred]
  • free-vary transform   → an LLM conjecturer prompt over the seed                                                 [deferred]
  • prove each candidate  → the governed pipeline (`solve_family` / `autoformalize`), UNCHANGED — kernel gates all  [driver, deferred]
  • bank + export         → `family_lemma_library` + `export_training_corpus`, already default-on and automatic
This module is a THIN generator/orchestrator over those; it re-rolls none of them.

THEATER TO AVOID (literature-audited; "Library Learning Doesn't" 2410.20274, LEGO-Prover fails 2504.03048).
Growing corpus SIZE without VALUE is worthless — redundant, low-diversity data. Two gates, both reusing existing
machinery, keep amplification honest:
  1. NON-TRIVIAL: drop a candidate the bare native cascade closes instantly (it teaches nothing) — measured by the
     pipeline itself, not re-implemented here (`specialization_substantive` is the existing non-degeneracy check).
  2. DIVERSE: drop a candidate α-equivalent to something already in the corpus (`proof_cache.normalize_statement_equiv`),
     so the exporter's void-novel count rises with DISTINCT theorems, not skins.
A candidate that is false is not waste — it is falsification corpus (the third export stream); it just is not the
prover corpus we are amplifying.

SOUNDNESS. Zero new soundness surface: a candidate is a PROMPT SEED (like `anti_unify`'s), the agent writes the
typed statement + proof, and the unchanged kernel + firewall + anti-laundering gate every closure. A bad seed
yields a no_advance / gap, never a false closure.

STATUS. MVP here = the deterministic GENERALIZE generator (`seed_variants`), offline-testable. Deferred (need the
warm VPS pipeline / LLM keys, and design confirmation): the specialize/compose/free-vary transforms and the
`amplify` driver that routes candidates through `solve_family` and lets the existing export capture them.

  python -m ztare.leanmill.solver.void_self_play --selftest
"""
from __future__ import annotations

from ztare.leanmill.solver.anti_unify import anti_unify, schema_conjecture_seed


def _schema_key(schema: str) -> str:
    """Whitespace-normalized dedup key for a hole-schema (NOT a full statement, so the α-normalizer used for real
    statements does not apply — the schema still carries `?Mi` holes)."""
    return " ".join((schema or "").split())


def seed_variants(seed_stmt: str, seed_name: str, banked: "list[dict]",
                  *, max_variants: int = 8) -> "list[dict]":
    """Generalize-transform generator: pair a PROVEN seed theorem against each banked sibling and emit the
    least-general-generalization as a targeted conjecture seed (the agent fills the holes, the kernel gates it).
    This is `anti_unify.mine_cert_pairs` re-aimed — seeded on ONE new theorem vs the bank, for corpus growth,
    rather than all-pairs advisory mining. Deduped by schema, ranked tightest-first (fewest holes, then lowest
    coverage), capped. `banked` = [{"name":str, "text":str}, ...] proven statements.

    Returns [{transform, seed_name, sibling, n_vars, coverage, conjecture_seed}], ready to route through the
    governed pipeline as MOVE_CONJECTURE / consolidation targets. Empty when nothing generalizes (never raises)."""
    out: "list[dict]" = []
    seen: "set[str]" = set()
    for b in banked or []:
        name, text = (b.get("name") or ""), (b.get("text") or "")
        if not text.strip() or name == seed_name:
            continue
        au = anti_unify(seed_stmt, text)
        if not au:
            continue
        key = _schema_key(au["schema"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"transform": "generalize", "seed_name": seed_name, "sibling": name,
                    "n_vars": au["n_vars"], "coverage": au["coverage"],
                    "conjecture_seed": schema_conjecture_seed(au, seed_name, name)})
    out.sort(key=lambda d: (d["n_vars"], d["coverage"]))
    return out[:max_variants]


def amplify(corpus_preamble: str, candidates: "list[dict]", *, solve_fn=None,
            corpus_keys: "set[str] | None" = None, trivial_fn=None,
            max_candidates: int = 16, **solve_kw) -> dict:
    """THE driver: route self-generated CONCRETE candidate conjectures through the UNCHANGED governed
    prove+bank+measure pipeline (`solver_core.solve_family`), after the two VALUE gates. solve_family already
    proves each sibling, banks every closure, and counts BANKED reuse (the compounding signal) with a built-in
    `compound=True/False` A/B — so amplify adds ONLY: (1) the DIVERSE gate (drop a candidate α-equivalent to the
    corpus or to an earlier candidate — `proof_cache.normalize_statement_equiv`, so the corpus grows by DISTINCT
    theorems not skins), (2) the optional NON-TRIVIAL gate (`trivial_fn(decl)->bool` drops what the native cascade
    closes instantly — teaches nothing; a compute probe, injected, default skip), and (3) the corpus-growth report.

    Candidate GENERATION is upstream and unchanged (`seed_variants` = generalize schemas → an instantiation step;
    `conjecture.specialize_generate` = concrete specializations); this DRIVES and MEASURES, it does not generate.
    `candidates`: [{"name": <decl name>, "decl": <`theorem … := by sorry` block>}, ...]. `solve_fn` is injected so
    the driver is offline-testable with a stub; the live default lazy-imports `solve_family` (heavy). `solve_kw`
    (e.g. `compound=`, `provider=`, `substrate=`) pass through. Returns the growth report; run it once with
    `compound=True` and once `compound=False` and compare `closure_rate`/`banked_reuse_total` — that A/B is the
    'does self-play banking accelerate closure' measurement (the point of the module; corpus size without value is
    the audited theater). Zero new soundness surface: every closure is kernel + firewall + anti-laundering gated."""
    from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
    from ztare.leanmill.lean_source import signature_before_proof
    seen: "set[str]" = set(corpus_keys or ())
    kept: "list[dict]" = []
    dropped = {"duplicate": 0, "trivial": 0}
    for c in candidates or []:
        name, decl = (c.get("name") or ""), (c.get("decl") or "")
        if not decl.strip() or not name:
            continue
        key = normalize_statement_equiv(signature_before_proof(decl) or decl)
        if key in seen:                                   # DIVERSE gate
            dropped["duplicate"] += 1
            continue
        if trivial_fn is not None and trivial_fn(decl):   # NON-TRIVIAL gate (injected compute probe)
            dropped["trivial"] += 1
            continue
        seen.add(key)
        kept.append({"name": name, "decl": decl})
        if len(kept) >= max_candidates:
            break
    report = {"generated": len(candidates or []), "kept": len(kept), "dropped": dropped,
              "closed": 0, "closure_rate": 0.0, "banked_reuse_total": 0, "distinct_added": [], "family": None}
    if not kept:
        return report
    if solve_fn is None:
        from ztare.leanmill.solver.solver_core import solve_family as solve_fn  # heavy — lazy, live only
    fam = solve_fn(corpus_preamble, kept, **solve_kw)
    report["family"] = fam
    report["closed"] = fam.get("closed", 0)
    report["closure_rate"] = fam.get("closure_rate", 0.0)
    report["banked_reuse_total"] = sum((s.get("banked_helper_refs_in_proof") or 0) for s in fam.get("siblings", []))
    report["distinct_added"] = [s.get("name") for s in fam.get("siblings", []) if s.get("closed")]
    return report


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    seed = "theorem shamir_recon_deg2 (P : F[X]) (h : P.degree < 2) : unique_on P s := by simp"
    banked = [
        {"name": "shamir_recon_deg3", "text": "theorem shamir_recon_deg3 (P : F[X]) (h : P.degree < 3) : unique_on P s := by simp"},
        {"name": "unrelated_group",   "text": "theorem unrelated_group (G : Type) [Group G] (g : G) : g * g⁻¹ = 1 := by simp"},
        {"name": "shamir_recon_deg2", "text": seed},  # the seed itself — must be skipped
    ]
    v = seed_variants(seed, "shamir_recon_deg2", banked)
    ok("generalizes the seed vs a degree-sibling (one hole on the degree bound)",
       len(v) == 1 and v[0]["sibling"] == "shamir_recon_deg3" and v[0]["n_vars"] == 1)
    ok("emits a targeted conjecture seed the agent can fill",
       v and "STRICTLY more general" in v[0]["conjecture_seed"] and "?M1" in v[0]["conjecture_seed"])
    ok("skips the seed itself and the non-generalizable sibling (no frankenstein pairing)",
       all(x["sibling"] != "shamir_recon_deg2" and x["sibling"] != "unrelated_group" for x in v))
    ok("empty bank ⇒ no variants, never raises", seed_variants(seed, "s", []) == [])
    # cap + dedup: many identical siblings collapse to one schema, and the cap holds
    dup_bank = [{"name": f"dup{i}", "text": banked[0]["text"]} for i in range(5)]
    vd = seed_variants(seed, "shamir_recon_deg2", dup_bank, max_variants=3)
    ok("dedup by schema (5 identical siblings ⇒ 1 variant)", len(vd) == 1)

    # --- amplify driver (offline; stub solve_fn so no compute / no heavy import) ---
    cand = [
        {"name": "c_deg4", "decl": "theorem c_deg4 (P : F[X]) (h : P.degree < 4) : unique_on P s := by sorry"},
        {"name": "c_deg4_dup", "decl": "theorem c_deg4_dup (P : F[X]) (h : P.degree < 4) : unique_on P s := by sorry"},  # α-dup of c_deg4
        {"name": "c_deg5", "decl": "theorem c_deg5 (P : F[X]) (h : P.degree < 5) : unique_on P s := by sorry"},
        {"name": "c_triv", "decl": "theorem c_triv (P : F[X]) : True := by sorry"},  # dropped by trivial_fn
    ]
    seen_fam = {}

    def _stub_solve(preamble, siblings, **kw):  # mimic solve_family's report shape
        seen_fam["siblings"] = [s["name"] for s in siblings]
        sibs = [{"name": s["name"], "closed": True, "banked_helper_refs_in_proof": (1 if i else 0)}
                for i, s in enumerate(siblings)]
        return {"closed": len(siblings), "closure_rate": 1.0, "siblings": sibs}

    rep = amplify("-- corpus", cand, solve_fn=_stub_solve,
                  trivial_fn=lambda d: ": True" in d)
    ok("DIVERSE gate drops the α-equivalent duplicate", rep["dropped"]["duplicate"] == 1)
    ok("NON-TRIVIAL gate drops the trivial candidate", rep["dropped"]["trivial"] == 1)
    ok("keeps only the 2 distinct non-trivial candidates", rep["kept"] == 2
       and seen_fam.get("siblings") == ["c_deg4", "c_deg5"])
    ok("aggregates banked reuse from the family report", rep["banked_reuse_total"] == 1)
    ok("reports the distinct closed theorems added to the corpus", rep["distinct_added"] == ["c_deg4", "c_deg5"])
    ok("empty candidates ⇒ nothing routed, never raises",
       amplify("-- c", [], solve_fn=_stub_solve)["kept"] == 0)
    ok("corpus_keys pre-seed suppresses a candidate already in the corpus",
       amplify("-- c", [cand[0]], solve_fn=_stub_solve,
               corpus_keys={__import__("ztare.leanmill.solver.proof_cache", fromlist=["normalize_statement_equiv"])
                            .normalize_statement_equiv("theorem c_deg4 (P : F[X]) (h : P.degree < 4) : unique_on P s")}
               )["kept"] == 0)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
