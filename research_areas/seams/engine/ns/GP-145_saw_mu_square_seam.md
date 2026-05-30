# GP-145 — SAW Connective Constant μ_sq (Conjecture Refinement Seam)

> **Seam metadata** · `seam_id:` GP-145 · `track:` engine · `status:` run-1 archived 2026-04-24 (partial null, pinned at 56); run- · `last_updated:` 2026-05-08


**Status:** run-1 archived 2026-04-24 (partial null, pinned at 56); run-2 narrow-scope planned (gp145b)
**Owner:** conjecture-refinement substrates
**Depends on:** GP-086 (gate harness), GP-122 (Lean REPL), GP-144 (claim-pipeline discipline), GP-148 (trajectory mining)
**Triggered by:** 2026-04-24 operator ask for first real conjecture-refinement substrate after gp140 continuous-chaotic + gp147 meta-validation
**Visibility:** private (first-mover IP; target is a real open problem)

---

## 1. Problem statement

The connective constant μ_sq of 2D square-lattice self-avoiding walks is known numerically to ≥30 digits (μ_sq ≈ 2.638158530031, Clisby pivot-algorithm simulations). A closed form is **open**. The hexagonal-lattice case was proven by Duminil-Copin & Smirnov (2010): μ_hex = √(2+√2). That result won Fields-Medal-level recognition. The square-lattice case is Fields-Medal-adjacent.

The apparatus's job: given OEIS A001411 enumeration, propose a closed form μ_sq = f(constants ∈ Δ) via PSLQ with bit-budget discipline, passing G2 falsity audit (bit-budget + perturbation + dictionary ablation) before Lean verification.

## 2. Pre-registered priors (set 2026-04-24, before run-1)

| Outcome | Prior | Interpretation |
|---|---|---|
| P_null (correctly reports null) | 65% | No short closed form in Δ₁ at dim ≤ 5 with precision 30 digits |
| P_garbage (proposal fails G2) | 15% | Apparatus over-claims; G2 catches |
| P_positive_long (dim 4-5 passes G2) | 15% | Interesting; Lean verification required |
| P_positive_short (dim ≤3 passes G2) | 5% | Fields-Medal-adjacent signal |

## 3. Simulated panel debate (single-voice, design space narrow)

### Round 1 — opening

**Target Selector (TS):** μ_sq chosen over Hénon λ₁ and Lehmer's constant for three reasons: (a) highest prestige (FM-adjacent), (b) published 30-digit precision fits PSLQ bit budget comfortably for dim ≤ 5, (c) witness exists (hexagonal closed form proves the class admits solutions).

**Prior Assigner (PA):** P_null prior 65% reflects the honest assessment. Hexagonal closed form emerged from a parafermionic observable that doesn't exist on the square lattice. There's no structural reason a short Δ₁ combination produces μ_sq. A short closed form existing would be more surprising than none.

**Gate Integrator (GI):** The G2 PSLQ falsity gate catches false positives. The verifier script parses pslq_claim JSON blocks. Null-result path requires no gate activation — the thesis just argues "no relation found in N runs at precision P implies no relation exists up to [bound]."

**Rubric Designer (RD):** Kepler mode (not Newton). Conjecture refinement is descriptive-fit shaped, not generative-prediction shaped. Four dimensions: Asymptotic Extraction Rigor 35, Rival Closed-Form Skepticism 30, Bit-Budget & Stability Challenge 20, Lean-4 Formal Verification Path 15. Total 100.

**Adversarial Skeptic (AS):** how do we guarantee gp145 fails? (a) Accept the mutator's hand-waved closed form without G2 verification — verifier prevents. (b) Accept a probabilistic null without rigor on the bound — the rubric's "Bit-Budget & Stability Challenge" dimension catches. (c) Run only short precision and declare null — bit-budget compliance requires `precision_bits ≥ dim · log₂(|Δ|) + 20`. All three failure modes are pre-closed.

### Round 2 — response

**PA → AS:** "probabilistic null accepted without bound rigor" is STILL a risk. The judge can score a null-result thesis high if the argument SOUNDS rigorous even if the bound is empirical. This is what we need to watch for in the run.

**GI → AS:** verifier only fires on emitted pslq_claim blocks. A null-result thesis emits no block. Judge scoring is the only gate on null-argument rigor.

### Round 3 — convergence

Design locked: kepler rubric, 4 dimensions, G2 verifier post-hoc, null-result protocol explicit in evidence. Risk accepted: judge may score unrigorous null arguments high on prose alone.

## 4. Run-1 results (2026-04-24, iter 1-11, archived)

Trajectory: **8 → 42 → 35 → 28 → 34 → 28 → 43 → 52 → 38 → 25 → 56**.

Champion (iter 11, score 56) converged on a **probabilistic non-existence argument**:

> "If PSLQ at p ≥ T bits with κ₂ ≤ 10¹² deterministically recovers any existing relation (Bailey-Ferguson 1992 Thm 2), and six archived runs all satisfy this, then P_miss ≤ 2⁻³⁸⁴. Therefore no Δ₁-based dim ≤ 5 H ≤ 10⁸ closed form exists."

**Verdict:** *P_null direction (correct per 65% prior) but pinned at 56 by premise-rigor ceiling.* Every iter's weakest-link was the same class: **unverified κ̂ bound / Ferguson-Bailey overreach / run-independence unproven**. Identical ceiling class to gp140's pre-Chebyshev 78-ceiling.

**What we learned:**
1. Apparatus defaults to P_null discipline when the conjecture is unfriendly to the dictionary (no hand-waved false positive).
2. Null-result arguments have the same ceiling class as positive-result arguments: "the bound is empirical, not proven." Judge correctly flags this.
3. Analog to gp140: the ceiling breaks when the mutator converts empirical-bound → provable-bound. For gp140 that was Chebyshev basis-change. For gp145, the analog is **narrowing scope to where κ̂ bound is provable by construction** (dim ≤ 2 over small dictionary).
4. Verifier + G2 gate both held discipline: never triggered because no pslq_claim block was emitted (correct — no closed form proposed).

## 5. Run-2 plan: gp145b narrow-scope null argument

**Target:** dim ≤ 2 over dictionary Δ₀_small = {1, π, √2, √3, ln 2} (|Δ₀_small|=5). At this scope, κ̂ is provably bounded by a closed-form lemma (elementary condition-number arithmetic on 5-constant Gram matrix); no empirical measurement needed. The null-result argument becomes a rigorous theorem:

> "For any (c₁, c₂) ∈ Z² with |c_i| ≤ H in the span of Δ₀_small, either c₁k₁ + c₂k₂ = 0 (trivial) or |c₁k₁ + c₂k₂| ≥ 2^{-B(H,|Δ₀_small|)} for a bound B. Our PSLQ runs rule out all such at the declared precision. Therefore no dim ≤ 2, Δ₀_small-based closed form for μ_sq exists at height H ≤ 10⁸."

**Expected outcome:** P_null holds, score breaks past 70 because the κ̂ bound becomes provable. If it does, we publish the narrow null as a preliminary finding and extend scope iteratively. If it doesn't, the ceiling isn't κ̂ — it's something else we haven't identified.

**gp145b is a fresh project** (separate directory, separate rubric, separate mining records). Run-1 results stay archived at gp145.

## 6. Convergence points (design locked)

- Run-1: archived as partial P_null at score 56, ceiling on premise-rigor.
- Run-2: gp145b, dim ≤ 2 over Δ₀_small, provable κ̂ bound by construction.
- G2 falsity audit remains the gate for any positive closed-form claim.
- Null-result protocol remains: thesis may emit no pslq_claim block and still pass if the null argument is rigorous.

## 7. What this seam is NOT

- Not a kernel-integration seam (that's GP-143 for continuous-chaotic).
- Not a new gate spec (that's GP-144).
- Not a mining-infrastructure seam (that's GP-148).
- IS: the design record for the first conjecture-refinement substrate, its pre-registration, its run-1 archival, and the run-2 narrow-scope plan.

## 8. What counts as "new science" from this seam

Even if gp145b produces a rigorous dim ≤ 2 null:

- It is **a preliminary scientific finding** worth a methodology paper (the GP-148-auditable null protocol applied to a real open problem).
- It is NOT a solution to μ_sq — it rules out one specific region of the search space.
- To extend to a full new-science claim (closed form found OR rigorous all-dim closed-form non-existence), all four GP-144 gates + GP-146 self-validation + Lean 4 compilation + external review must apply.
