# Paper 5 Epistemic Ledger
## The Principles of Epistemic Verification: How Judgment Decomposes, and What Does Not

**Purpose:** Token-Optimized Self-Model for agents making targeted edits to paper5.
Maps Claims, Dependencies, and Epistemic Invariants for a ~45-page document with
tightly interlocked taxonomy (10 operations, 7 principles, 3 tiers, 3 residuals).
Read this before editing any section of paper5/main.tex or paper5/draft.md.

**Last verified:** 2026-04-26. Structural audit against draft.md line count + section headers.

---

## 1. Core Thesis (The Root Node)

Epistemic verification — the practice incumbent vocabulary calls "judgment," "senior
review," "the expert eye" — decomposes into ten named stateless operations and three
residual commitments that resist decomposition because they are non-deterministic AND
stateful. The boundary between the two is the treatise's load-bearing and testable claim.

**Falsification conditions (stated in §1.4):**
- Refuted if an independent operator finds the operations are not separable (performing op 4 requires op 8 implicitly)
- Refuted if the pathologies of §1.3 turn out not to recur across systems (artifacts of one architecture)

---

## 2. Structural Skeleton (Section Map)

### Front Matter (lines 14-40)
Four scope commitments + corpus caveat + Taylor analogy framing + agency disambiguation.

### Introduction (lines 44-66)
Taylor analogy: 4 reasons craftsmen resisted decomposition. Same structure for epistemic verification.

### Chapter 1: The Decomposition (lines 70-150)
- §1.1 What is being decomposed (distinct from generation, decision-making, analysis)
- §1.2 Ten Operations (table)
- §1.3 Ten Pathologies + P11 Grammar Semantic Leak
- §1.4 Provenance: abductively proposed from one corpus

### Chapter 2: Principles (lines 154-334)
Seven principles = one commitment (make inspection structural) rendered at seven failure surfaces.

| Principle | What it prevents |
|-----------|-----------------|
| P-I Separation | Adversarial gradient through shared substrate |
| P-II Statelessness | Slow-poison drift attack |
| P-III Typed Deterministic | Non-reproducible verification |
| P-IV Cheap Repetition | Fatigue/rubber-stamp |
| P-V Pre-registration | Ex-post rationalization |
| P-VI Holdout Surfaces | Candidate authoring own test |
| P-VII Asymptotic Standards | Closed optimization surface (Goodhart) |

§2.8 Standing Reservation (library is Goodhart target)
§2.9 Static Grammar as Falsification Guarantee
§2.10 Epistemological Ledger (3 tiers: registration → closure → promotion)

### Chapter 2½: Empirical Validation (lines 336-412) — ADDED 2026-04-24/25

**§2½.1 The Corpus** (lines 342-348)
1,825 iterations, 84 projects, enriched with active_constraints, diff_delta_bytes, run_session_id, charter_hash, rubric_hash. GP-148 Stage 1 extractor + Stage 1.5 enrichment.

**§2½.2 Two Causal Categories** (lines 350-360)
Structural blockers (lift < 1, presence kills scores) vs ceiling-breakers (lift > 1, appear at high scores as residual critiques). Anti-pattern catalog Part 1 (blockers, cross-judge-validated) vs Part 2 (ceiling-breakers, judge-family-specific). 48% three-way LLM agreement on Part 2 labels.

**§2½.3 Persistence Profile** (lines 372-378)
Champions need ~28 iters / ~10 critique classes. Persistence + cycling, not single-shot insight.

**§2½.4 Self-Correcting Audit Coda** (lines 384-392)
Framer spec v1.0 → v2.0 evolution: apparatus designed primitive, audited it, refuted its own audit's Student-t claim. Jacobian-patch-cycle anti-pattern documented (RH-11).

**§2½.5 From Verification to Discovery: Three Adversarial Gates** (lines 396-412) — ADDED 2026-04-25, UPDATED 2026-04-26

Three pre-registered synthetic tests:
1. GP-159 Retrieval-Trap: non-standard constants, anti-retrieval gate. o3=90, claude-sonnet=90.
2. GP-160 Asymptotic Wall: extrapolation gate, polynomial trap. o3=90, claude-sonnet=82.
3. GP-161 MDL Anti-Goodhart: K=10 oscillatory truth, parsimony resistance. o3=90, claude-opus=81.

**Cross-mutator replication paragraph** (added 2026-04-26): all three pass across OpenAI o3 and Anthropic claude, confirming result is structural.

**Scope paragraph** (updated 2026-04-26): "Telescope works; planet pending." Raw capability to enable discovery validated. Discovery itself requires unknown-GT success (GP-163d in flight).

### Chapter 3: The Residual (lines 414-478)
Three operations that have NOT decomposed:
- §3.1 Eigenquestion SELECTION (Peircean abduction)
- §3.2 Recognizing when to reframe (vs basin search) — NOTE: GP-164 ANALOGY seam (2026-04-26) proposes a partial mechanization of this via cross-domain structural fingerprinting. If implemented and validated, §3.2 boundary narrows.
- §3.3 Social dynamics of live pressure-testing
- §3.4 Shape: residual = non-deterministic AND stateful

### Conclusion (lines 480-558)
Five empirical anchors + named extensions.

**2026-04-26 update needed:** The five empirical anchors (Planck/Weibull, H-COMPUTE-01, H-GRAMMAR-01, KWW, Saturation/Langevin) predate the Discovery Engine triad. The triad is now in Chapter 2½ but NOT in the Conclusion's anchor list. Options: (a) add a sixth anchor, (b) reference the triad from the Conclusion with a forward pointer. Current state: the Conclusion does not mention the triad.

### Formalization Sketch (lines 562-708)
Typed signatures, grammar ceiling function, theory/practice split, apparatus-domain scoping, inspection principle, formal bridge.

### Instrumentation Roadmap (lines 710-750)
Four metrics: automation ratio, cost per validated finding, N threshold, cross-operator replication.

---

## 3. The Ten Operations and Pathologies

(Unchanged from previous version — see tables above.)

---

## 4. Load-Bearing Claims and Evidence Dependencies

### Grammar Ceiling Hypothesis (GCH)
**Claim:** Score ceiling is grammar + substrate; compute beyond primitive exhaustion = zero marginal lift.
**DEPENDS_ON:** H-COMPUTE-01 (32 iters, zero lift) AND H-GRAMMAR-01 (1 primitive, Planck recovered). Both pre-registered.
**Status:** Confirmed (INS-050).

### Discovery Engine Triad (NEW 2026-04-25/26)
**Claim:** Apparatus has raw capability to enable discovery (avoids retrieval, extrapolation breakdown, MDL Goodharting).
**DEPENDS_ON:** GP-159 (anti-retrieval gate clean, non-standard constants), GP-160 (asymptotic wall passes, polynomial trap avoided), GP-161 (K=10 accepted, parsimony not forced).
**Cross-replication:** o3 + claude-opus/sonnet. Condition (a) satisfied.
**DOES NOT CLAIM:** Discovery on unknown-GT substrate. Pending GP-163d.
**Status:** Confirmed / scoped / cross-family (INS-054).

### KWW Second Chain
**Claim:** Evidential ceiling (98/100) is correct epistemology, not shortfall.
**Status:** Confirmed (INS-046).

### Residual (Chapter 3)
**Claim:** Three operations are non-deterministic AND stateful.
**DEPENDS_ON:** Peirce (1878); 2026-04-14 identifiability catch as live instance.
**NOTE:** GP-164 ANALOGY seam proposes partial mechanization of §3.2 (reframe recognition) via cross-domain structural fingerprinting. If validated, the residual boundary narrows. This is noted as future work, not a current claim.

### Self-Correcting Audit (NEW 2026-04-25)
**Claim:** Apparatus can audit its own designs and refute its own audit's claims.
**DEPENDS_ON:** Framer spec v1.0 → v2.0 evolution; Student-t claim constructed iter 4, refuted iter 7.
**Status:** Documented (RH-10 in anti-pattern catalog).

### ZTARE-on-ZTARE Postmortem (NEW 2026-04-25)
**Claim:** Spec audits without integration smoke tests systematically miss code bugs.
**DEPENDS_ON:** 4 meta-projects (gp152, gp153, gp140, gp156); 7/12 iters failed on code not concept.
**Status:** Confirmed (INS-052). Mandatory protocol: smoke test FIRST, then inverted spec audit.

---

## 5. Lexical and Epistemic Invariants

1. **NEVER say the operations were "observed."** "Abductively proposed." (Front Matter §4)
2. **Residual boundary is empirical, not proven.** "As of 2026, one system, one operator."
3. **Grammar Ceiling = grammar is binding, not compute.** H-COMPUTE-01 is the control.
4. **Pathology confidence tiers are not interchangeable.** Upgrades require new independent domain.
5. **No quantitative claims on cost, throughput, or automation ratio.**
6. **Corpus caveat is non-negotiable.** 2026-04-08 to 2026-04-15 corridor disclosed.
7. **"Agency" has two distinct meanings.** Jensen-Meckling (structural) vs Bandura/Ryan (psychological).
8. **KWW 98/100 is correct epistemology, not a shortfall.**
9. **The treatise is "version zero."** No finality claims.
10. **Paper 5 and Paper 4 are a pair.** Operations (P5) and structure (P4).
11. **Tone:** No em-dashes. No "it wasn't X; it was Y." Direct affirmative framing. Peircean precision.
12. **Discovery Engine claim is SCOPED.** "Telescope works; planet pending." Do not upgrade to "discovery proven" without unknown-GT success.
13. **Cross-mutator replication is structural, not model-specific.** The claim is about the apparatus + gates, not about o3 or claude.

---

## 6. Structural Flow Check (2026-04-26)

The document flows as:
```
Front Matter (scope) → Introduction (Taylor analogy)
→ Ch1 (decomposition: 10 ops + 10 pathologies)
→ Ch2 (7 principles + grammar + ledger)
→ Ch2½ (empirical: mining → self-correcting audit → discovery triad)
→ Ch3 (residual: 3 non-decomposed ops)
→ Conclusion (anchors + extensions)
→ Formalization (typed signatures + grammar ceiling + inspection principle)
→ Instrumentation (4 metrics)
```

**Flow concern:** Chapter 2½ has grown substantially (mining + audit coda + triad + cross-mutator). It now carries more empirical weight than Chapter 2 (principles). This is structurally correct (the principles NEED empirical validation) but the length ratio should be monitored. If Chapter 2½ exceeds ~8 pages, consider splitting into "Chapter 2½A: Corpus Mining" and "Chapter 2½B: Discovery Validation."

**Missing from Conclusion:** The Discovery Engine triad is in Chapter 2½ but not in the Conclusion's five empirical anchors. The Conclusion should either add a sixth anchor or reference the triad with a forward pointer. Current state: silent.

---

*Created: 2026-04-19. Last updated: 2026-04-26 (Discovery Engine triad + cross-mutator replication + GP-164 ANALOGY note + structural flow check + new invariants 12-13).*
