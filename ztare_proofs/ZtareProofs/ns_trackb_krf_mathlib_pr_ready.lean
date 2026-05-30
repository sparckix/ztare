/-
Copyright (c) 2026 Mathlib Contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: ZTARE NS Track B
-/
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import Mathlib.MeasureTheory.Function.UnifTight
import Mathlib.MeasureTheory.Function.ConvergenceInMeasure
import Mathlib.MeasureTheory.Measure.Haar.OfBasis
import Mathlib.Analysis.Calculus.BumpFunction.Basic
import Mathlib.Analysis.Calculus.BumpFunction.Normed
import Mathlib.Analysis.Calculus.BumpFunction.FiniteDimension
import Mathlib.Analysis.Calculus.BumpFunction.Convolution
import Mathlib.Analysis.Convolution
import Mathlib.Topology.UniformSpace.Ascoli
import Mathlib.Topology.UniformSpace.Equicontinuity
import Mathlib.Topology.UniformSpace.CompactConvergence
import Mathlib.Topology.MetricSpace.Sequences
import Mathlib.Tactic

/-!
# Kolmogorov–Riesz–Fréchet compactness in `L²(Ω)` for bounded `Ω`

This file states and proves the **Kolmogorov–Riesz–Fréchet (KRF) compactness
theorem** for `L²(Ω)` on a bounded measurable set `Ω ⊆ ℝᵈ`.

## Main statement (Brezis, *Functional Analysis*, Théorème 4.26;
Hanche-Olsen–Holden, *The Kolmogorov–Riesz Compactness Theorem*, 2010,
Theorem 5):

A bounded subset `𝓕 ⊆ L²(Ω)` is precompact iff it is

  (KRF1) `L²`-bounded: `∃ M, ∀ f ∈ 𝓕, ‖f‖₂ ≤ M`;
  (KRF2) uniformly tight: `∀ ε, ∃ R, ∀ f ∈ 𝓕, ∫_{|x|>R} |f|² < ε²`;
  (KRF3) uniformly translation-continuous:
         `∀ ε, ∃ δ, ∀ f ∈ 𝓕, ∀ |h|<δ, ‖τ_h f − f‖₂ < ε`.

For bounded `Ω`, (KRF2) is automatic (extending by zero), so the criterion
reduces to (KRF1) + (KRF3).

## Proof outline

1. **Mollifier rate** (`mollifier_rate_uniform`): under (KRF3), there is a
   uniform-in-`f` mollifier rate `ω : ℝ≥0 → ℝ≥0` with `ω(δ) → 0` such that
   `‖ρ_δ * f − f‖₂ ≤ ω(δ)` for every `f ∈ 𝓕`.

2. **Arzelà–Ascoli on the mollified family** (`arzela_ascoli_mollified_subsequence`):
   for fixed `δ > 0` the mollified family `(ρ_δ * f_n)` is `C¹`-bounded on
   `Ω`, hence equicontinuous + pointwise bounded, hence relatively compact in
   `C(Ω, ℝ)` with the topology of uniform convergence on compact sets. Extract
   a uniformly-convergent subsequence.

3. **Cantor diagonal extraction** (`cantor_diagonal_extraction`): take a
   sequence of mollifier scales `δ_k = 1/k`. For each `k` extract a
   sub-subsequence converging uniformly on `Ω`. Diagonalize.

4. **Composition** (`kolmogorov_riesz_frechet_compactness`): the diagonal
   subsequence is `L²`-Cauchy on `Ω` (uniform convergence on bounded `Ω` plus
   the mollifier rate), hence converges in `L²(Ω)` by completeness.

## Status of this file

This file is structured as a Mathlib upstream PR. It compiles against Mathlib
v4.30.0-rc2. Proofs that depend on classical analytic facts not yet packaged
in Mathlib are flagged with `-- TODO: Mathlib gap` comments naming the
specific missing lemma(s). No NS Track B internal imports are used.

## Missing Mathlib lemmas (consolidated)

| Tag      | Lemma                                                  | Status |
|----------|--------------------------------------------------------|--------|
| MLG-1    | `MeasureTheory.tendsto_translate_eLpNorm_zero`         | ABSENT |
| MLG-2    | `MeasureTheory.eLpNorm_convolution_sub_le` (rate-form) | ABSENT |
| MLG-3    | `MeasureTheory.eLpNorm_convolution_sub_tendsto_zero`   | ABSENT |
| MLG-4    | C¹-bound on `ρ_δ * f` from `‖f‖_{L²}`                  | ABSENT |
| MLG-5    | metrizability of `C(Ω, ℝ)` for σ-compact `Ω`            | partial|

References: Brezis (2011), Th. 4.26; Hanche-Olsen–Holden (2010), Th. 5;
Lieb–Loss (2001), Th. 2.16.
-/

namespace MeasureTheory

open Set Filter Topology Convolution Function

noncomputable section

/-! ## §1. The KRF data bundle -/

/-- The **Kolmogorov–Riesz–Fréchet hypothesis bundle** for a bounded
domain `Ω ⊆ ℝᵈ`.

Concretely a sequence of `L²(Ω, ℝ)` functions satisfying

  (KRF1)  uniform `L²` bound;
  (KRF3)  uniform `L²` translation-continuity in `Ω` (extended by `0`).

(KRF2 — uniform tightness — is automatic on bounded `Ω` and is therefore
NOT a field of this bundle.)

The translation-continuity hypothesis is parameterized by an arbitrary
modulus `ω : ℝ → ℝ` going to `0` at `0`. -/
structure KolmogorovRieszFrechetSeq
    {d : ℕ} (Ω : Set (EuclideanSpace ℝ (Fin d))) (f : ℕ → EuclideanSpace ℝ (Fin d) → ℝ)
    : Prop where
  /-- (KRF1) Uniform `L²`-bound. -/
  l2_bounded :
    ∃ M : ℝ, 0 ≤ M ∧ ∀ n,
      eLpNorm (Ω.indicator (f n)) 2 (volume) ≤ ENNReal.ofReal M
  /-- Each `f n` is strongly measurable. -/
  meas : ∀ n, AEStronglyMeasurable (f n) volume
  /-- The domain `Ω` is bounded (as a subset of Euclidean space). -/
  bounded : Bornology.IsBounded Ω
  /-- `Ω` is measurable. -/
  measΩ : MeasurableSet Ω
  /-- (KRF3) Uniform translation-continuity. For each `ε > 0` there is a
  threshold `δ > 0` such that for every shift `‖h‖ < δ` and every `n`,
  `‖τ_h (1_Ω · f_n) − 1_Ω · f_n‖₂ < ε`. -/
  unif_translation :
    ∀ ε : ℝ, 0 < ε → ∃ δ : ℝ, 0 < δ ∧
      ∀ (h : EuclideanSpace ℝ (Fin d)), ‖h‖ < δ →
        ∀ n,
          eLpNorm
            (fun x => Ω.indicator (f n) (x + h) - Ω.indicator (f n) x) 2 volume
            < ENNReal.ofReal ε

/-! ## §2. The mollifier-rate estimate

The first load-bearing lemma: under (KRF3), the mollified family
`ρ_δ * (1_Ω · f_n)` approximates `1_Ω · f_n` in `L²`, uniformly in `n`,
at a rate going to `0` as `δ → 0`.

The classical proof (Brezis, Lemme 4.21) uses Minkowski's integral
inequality on
  `(ρ_δ * f − f)(x) = ∫ ρ_δ(y) (f(x − y) − f(x)) dy`
and bounds the integrand on the support of `ρ_δ` by the uniform
translation modulus.

Mathlib v4.30.0-rc2 lacks both `tendsto_translate_eLpNorm_zero` (the
per-`f` translation continuity) and `eLpNorm_convolution_sub_le` (the
Minkowski rate-form). We expose the lemma as a structural target and
gate it on these missing pieces. -/

variable {d : ℕ}

/-- **Mollifier rate, uniform-in-family.**

For `(f_n)` satisfying (KRF1) + (KRF3) on a bounded `Ω`, there is a
modulus function `ω` with `ω(δ) → 0` such that the `L²` distance between
`ρ_δ * (1_Ω · f_n)` and `1_Ω · f_n` is bounded by `ω(δ)` uniformly in `n`.

Reference: Brezis, *Functional Analysis*, Lemme 4.21 + Théorème 4.26
(uniform version).

PROOF SKELETON (Brezis Lemme 4.21):
  Step 1.  `(ρ_δ * f − f)(x) = ∫ ρ_δ(y) (f(x − y) − f(x)) dy`
           (by `convolution_eq` + `ContDiffBump.integral_normed = 1`).
  Step 2.  Minkowski's integral inequality to take the L²(dx) norm
           inside the integral over `y`:
           `‖ρ_δ * f − f‖₂ ≤ ∫ ρ_δ(y) ‖f(· − y) − f‖₂ dy`.
  Step 3.  On `supp ρ_δ ⊆ B(0, δ)`, the integrand is `≤ ω(δ)` by (KRF3).
  Step 4.  `∫ ρ_δ = 1` finishes.

MATHLIB GAPS:
  * MLG-2: `eLpNorm_convolution_sub_le` (Minkowski rate form). -/
theorem mollifier_rate_uniform
    {Ω : Set (EuclideanSpace ℝ (Fin d))} {f : ℕ → EuclideanSpace ℝ (Fin d) → ℝ}
    (D : KolmogorovRieszFrechetSeq Ω f) :
    ∀ ε : ℝ, 0 < ε → ∃ δ : ℝ, 0 < δ ∧
      ∀ (φ : ContDiffBump (0 : EuclideanSpace ℝ (Fin d))),
        φ.rOut < δ →
          ∀ n,
            eLpNorm
              (fun x =>
                (φ.normed (volume) ⋆[ContinuousLinearMap.lsmul ℝ ℝ, volume]
                  (Ω.indicator (f n))) x - Ω.indicator (f n) x)
              2 volume
              < ENNReal.ofReal ε := by
  -- Step 0: extract the modulus-of-translation-continuity.
  intro ε hε
  obtain ⟨δ, hδ_pos, hδ⟩ := D.unif_translation (ε / 2) (by positivity)
  refine ⟨δ, hδ_pos, ?_⟩
  -- TODO: Mathlib gap MLG-2 (`eLpNorm_convolution_sub_le`):
  --   ‖ρ_δ * f − f‖_{L²} ≤ ∫ ρ_δ(y) ‖τ_y f − f‖_{L²} dy.
  --
  -- Once MLG-2 lands, the proof reads:
  --   intro φ hφ_small n
  --   calc eLpNorm (φ.normed * f - f) 2 volume
  --        ≤ ∫ y, φ.normed y * eLpNorm (τ_{-y} f - f) 2 volume   -- MLG-2
  --        ≤ ∫ y, φ.normed y * (ε/2)                              -- hδ on supp(φ)
  --        = ε/2 * ∫ y, φ.normed y                               -- pull const
  --        = ε/2 * 1                                              -- ∫ ρ_δ = 1
  --        < ε                                                    -- arithmetic
  --
  -- The supp(φ) ⊆ ball(0, φ.rOut) ⊆ ball(0, δ) step uses
  -- `ContDiffBump.support_normed_eq` + `hφ_small`.
  intro φ _ n
  -- Axiomatic shim: the inequality holds by Brezis Lemme 4.21 once MLG-2
  -- is in Mathlib. We discharge it with `sorry` and the gap citation.
  sorry

/-! ## §3. The Arzelà–Ascoli step

For fixed `δ > 0`, the mollified family `g_n := ρ_δ * (1_Ω · f_n)` is
smooth, bounded, and `C¹`-bounded uniformly in `n` (the gradient bound
comes from `‖∇ρ_δ‖_∞ · ‖f_n‖_{L²}` after Cauchy–Schwarz). On a
σ-compact set `Ω`, `C¹`-boundedness implies equicontinuity + pointwise
boundedness, and Arzelà–Ascoli supplies a uniformly-convergent
subsequence.

We use `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`
(`Mathlib.Topology.UniformSpace.Ascoli` line 471) as the underlying
extraction primitive. -/

/-- The covering family of compact subsets of `X`. -/
def 𝔖compact (X : Type*) [TopologicalSpace X] : Set (Set X) := {K | IsCompact K}

/-- The **mollified-family hypothesis bundle** consumed by Arzelà–Ascoli.

In our application, the mollified family `(ρ_δ * f_n)|_Ω` for fixed `δ`
satisfies all three hypotheses with constants depending only on `δ` and
the uniform `L²`-bound `M` of `(f_n)`. -/
structure MollifiedFamilyHypotheses
    {X : Type*} [TopologicalSpace X] (g : ℕ → X → ℝ) : Prop where
  /-- Each member is continuous. -/
  continuous : ∀ n, Continuous (g n)
  /-- The family is equicontinuous on every compact set. -/
  equicontinuous : ∀ K : Set X, IsCompact K → EquicontinuousOn g K
  /-- The family is pointwise compact (uniform pointwise bound). -/
  pointwiseCompact : ∀ x : X, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, g n x ∈ Q

/-- Helper repackaging the structure into the input shape of
`ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`. -/
theorem MollifiedFamilyHypotheses.toAscoliInputs
    {X : Type*} [TopologicalSpace X] {g : ℕ → X → ℝ}
    (H : MollifiedFamilyHypotheses g) :
    (∀ K ∈ 𝔖compact X, IsCompact K) ∧
    (∀ K ∈ 𝔖compact X, EquicontinuousOn g K) ∧
    (∀ K ∈ 𝔖compact X, ∀ x ∈ K, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, g n x ∈ Q) := by
  refine ⟨?_, ?_, ?_⟩
  · intro K hK; exact hK
  · intro K hK; exact H.equicontinuous K hK
  · intro K _ x _; exact H.pointwiseCompact x

/-- **Arzelà–Ascoli on the mollified family — abstract subsequence form.**

If `(g_n)` satisfies `MollifiedFamilyHypotheses`, then on a σ-compact
metrizable `X` (e.g. `EuclideanSpace ℝ (Fin d)` or any closed bounded
subset thereof), there is a uniformly-on-compacts convergent subsequence.

Reference: Brezis, *Functional Analysis*, Théorème 4.43 (Ascoli);
Hanche-Olsen–Holden (2010), §3.

The proof composes
  * `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`
    (Mathlib `Topology/UniformSpace/Ascoli.lean:471`) — closure compactness
    in `X →ᵤ[𝔖compact X] ℝ`,
  * metrizability of the compact-open topology on `C(X, ℝ)` for σ-compact `X`,
  * `IsCompact.isSeqCompact` (Mathlib `Topology/MetricSpace/Sequences.lean`).

MATHLIB GAP MLG-5: the metrizability of the compact-open topology on
`C(X, ℝ)` for σ-compact `X` is partially packaged (via the Polish-space
machinery) but the named bridge from "closure is compact in
`X →ᵤ[𝔖] ℝ`" to "subsequence converges uniformly on every compact"
is not. We isolate this gap behind a single `sorry`. -/
theorem arzela_ascoli_mollified_subsequence
    {X : Type*} [TopologicalSpace X] [T2Space X] [SigmaCompactSpace X]
    [SecondCountableTopology X]
    {g : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses g) :
    ∃ (φ : ℕ → ℕ) (gInf : X → ℝ),
      StrictMono φ ∧ Continuous gInf ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => g (φ n) x) gInf atTop K := by
  -- Step 1. Repackage hypotheses for `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`.
  obtain ⟨_, _, _⟩ := H.toAscoliInputs
  -- Step 2. Apply the Ascoli closure-compactness theorem to obtain
  -- `IsCompact (closure {g n | n})` in `X →ᵤ[𝔖compact X] ℝ`.
  --
  -- TODO: Mathlib gap MLG-5. The wiring of
  --   * `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`,
  --   * `ContinuousMap.isCompact_iff_seqCompact` (compact-open metrizable),
  --   * `tendstoUniformlyOn_iff_tendsto`
  -- into a single subsequence-extraction lemma is not yet packaged
  -- upstream. Closing it is ~150 LoC of pure Mathlib glue.
  sorry

/-! ## §4. The Cantor diagonal extraction

Standard. Given a chain of nested sub-subsequences `φ_k`, produce a single
diagonal `ψ`. This is provable from `Nat.StrictMono.le_apply` machinery
and is *not* blocked on any deep theorem; we prove it here in full. -/

/-- **Cantor diagonal subsequence extraction.**

Given a family of strictly monotone indexings `φ k : ℕ → ℕ` such that each
`φ (k+1)` is a subsequence of `φ k` via a strictly monotone extractor
`τ k` (i.e. `φ (k+1) = φ k ∘ τ k`), there is a single strictly monotone
`ψ : ℕ → ℕ` such that for every `k`, `(ψ n)_{n ≥ k}` is a subsequence
of `(φ k m)_m`.

Construction: `ψ n := φ n n` (the diagonal).

Reference: Hanche-Olsen–Holden (2010), proof of Theorem 5; standard
"Cantor's diagonal" trick.

This proof is sorry-free. -/
theorem cantor_diagonal_extraction
    (φ : ℕ → ℕ → ℕ) (h_strict : ∀ k, StrictMono (φ k))
    (τ : ℕ → ℕ → ℕ) (h_tau_strict : ∀ k, StrictMono (τ k))
    (h_nest : ∀ k n, φ (k+1) n = φ k (τ k n)) :
    ∃ ψ : ℕ → ℕ, StrictMono ψ ∧
      ∀ k, ∀ n, k ≤ n → ∃ m, ψ n = φ k m := by
  refine ⟨fun n => φ n n, ?_, ?_⟩
  · -- Strict monotonicity of `n ↦ φ n n`.
    have step : ∀ n, φ n n < φ (n+1) (n+1) := by
      intro n
      have h1 : φ (n+1) (n+1) = φ n (τ n (n+1)) := h_nest n (n+1)
      have h2 : n < τ n (n+1) := by
        have hle : n + 1 ≤ τ n (n+1) := (h_tau_strict n).le_apply
        exact Nat.lt_of_lt_of_le (Nat.lt_succ_self n) hle
      have h3 : φ n n < φ n (τ n (n+1)) := (h_strict n) h2
      simpa [h1] using h3
    intro a b hab
    induction hab with
    | refl => exact step a
    | step _ ih => exact lt_trans ih (step _)
  · -- Subsequence-of-`φ k` condition for `n ≥ k`.
    have nest_iter : ∀ k d n, n = k + d → ∀ m, ∃ m', φ n m = φ k m' := by
      intro k d
      induction d with
      | zero =>
          intro n hn m
          subst hn
          exact ⟨m, rfl⟩
      | succ d ih =>
          intro n hn m
          have hn' : n = (k + d) + 1 := by omega
          have key : φ n m = φ (k + d) (τ (k + d) m) := by
            rw [hn']; exact h_nest (k + d) m
          obtain ⟨m', hm'⟩ := ih (k + d) rfl (τ (k + d) m)
          exact ⟨m', by rw [key, hm']⟩
    intro k n hkn
    obtain ⟨e, he⟩ : ∃ e, n = k + e := ⟨n - k, by omega⟩
    exact nest_iter k e n he n

/-! ## §5. The KRF compactness theorem

We now compose:
  * `mollifier_rate_uniform` (§2);
  * `arzela_ascoli_mollified_subsequence` (§3) applied at scales
    `δ_k = 1/(k+1)`;
  * `cantor_diagonal_extraction` (§4).

The output is an `L²(Ω)`-convergent subsequence of `(f_n)`.

For bounded `Ω`, uniform convergence on `Ω` implies `L²(Ω)` convergence
(the constant function `1` is in `L²(Ω)` because `Ω` has finite measure).
Combined with the mollifier rate going to `0`, the diagonal subsequence
is `L²(Ω)`-Cauchy on `f_n` itself, not just on the mollifications. -/

/-- **Kolmogorov–Riesz–Fréchet compactness, integral form, on a bounded
domain.**

A sequence `(f_n)` in `L²(Ω, ℝ)` satisfying

  (KRF1) `L²`-bounded;
  (KRF3) uniformly translation-continuous;

with `Ω ⊆ ℝᵈ` bounded and measurable, has an `L²(Ω)`-convergent
subsequence.

Reference: Brezis (2011), Théorème 4.26; Hanche-Olsen–Holden (2010),
Theorem 5.

PROOF (composition of §§2–4):
  1. Choose `δ_k := 1/(k+1)`.
  2. By `mollifier_rate_uniform`, `‖ρ_{δ_k} * f_n − f_n‖₂ → 0`
     uniformly in `n` as `k → ∞`.
  3. For each fixed `k`, the family `g_n^{(k)} := ρ_{δ_k} * f_n` is
     smooth and `C¹`-bounded uniformly in `n` (gradient bound from
     `‖∇ρ_{δ_k}‖_∞` times the `L²`-bound `M`). So on the bounded set
     `Ω̄`, by `arzela_ascoli_mollified_subsequence`, extract a
     subsequence `g_{φ_k(n)}^{(k)}` that converges uniformly on `Ω̄`.
  4. Inductively nest: `φ_{k+1}` is a sub-subsequence of `φ_k`. By
     `cantor_diagonal_extraction`, there is a diagonal `ψ` with
     `(ψ n)_{n ≥ k}` always a subsequence of `φ_k`.
  5. The diagonal `f_{ψ(n)}` is `L²(Ω)`-Cauchy: for any `ε`, choose `k`
     with `mollifier_rate_uniform δ_k < ε/3`; then for `m, n ≥ k`,
       `‖f_{ψ(m)} − f_{ψ(n)}‖₂`
         ≤ `‖f_{ψ(m)} − ρ_{δ_k} * f_{ψ(m)}‖₂`
         + `‖ρ_{δ_k} * f_{ψ(m)} − ρ_{δ_k} * f_{ψ(n)}‖₂`
         + `‖ρ_{δ_k} * f_{ψ(n)} − f_{ψ(n)}‖₂`
       ≤ ε/3 + ε/3 + ε/3 = ε
     (the middle term controlled by uniform-on-`Ω̄` convergence and the
     fact that `Ω` is bounded so `‖·‖_{L²(Ω)} ≤ √vol(Ω) ‖·‖_∞`).
  6. By `Lp.completeSpace`, the Cauchy subsequence converges in `L²(Ω)`.

MATHLIB GAPS: MLG-2 (Minkowski rate form, in §2),
MLG-4 (`C¹`-bound on `ρ_δ * f`, used implicitly in step 3),
MLG-5 (Ascoli subsequence form, in §3). -/
theorem kolmogorov_riesz_frechet_compactness
    {Ω : Set (EuclideanSpace ℝ (Fin d))} {f : ℕ → EuclideanSpace ℝ (Fin d) → ℝ}
    (D : KolmogorovRieszFrechetSeq Ω f) :
    ∃ (ψ : ℕ → ℕ) (fInf : EuclideanSpace ℝ (Fin d) → ℝ),
      StrictMono ψ ∧ AEStronglyMeasurable fInf volume ∧
      Tendsto
        (fun n => eLpNorm (Ω.indicator (f (ψ n)) - Ω.indicator fInf) 2 volume)
        atTop (𝓝 0) := by
  -- Step 1. Mollifier rate.
  have hRate := mollifier_rate_uniform D
  -- Step 2. Iterated extraction at scales δ_k = 1/(k+1).
  -- For each k, build a sub-subsequence converging uniformly on Ω̄
  -- (closure of Ω, which is compact since Ω is bounded).
  --
  -- TODO: Mathlib composition. The closure of `Ω` in `EuclideanSpace ℝ (Fin d)`
  -- is compact (Heine–Borel, `Bornology.IsBounded` + closed). Apply
  -- `arzela_ascoli_mollified_subsequence` on `closure Ω` for each k.
  --
  -- The hypotheses for `arzela_ascoli_mollified_subsequence` come from:
  --   * smoothness of `ρ_{δ_k} * f_n`: `ContDiff.convolution`
  --   * equicontinuity: `Continuous.uniformContinuous_of_compactSupport`
  --     applied to `∇ ρ_{δ_k}` (compactly supported smooth)
  --   * pointwise compactness: `‖ρ_{δ_k} * f_n‖_∞ ≤ ‖ρ_{δ_k}‖_{L²} ‖f_n‖_{L²}`
  --     by Cauchy–Schwarz; bounded by a constant depending on δ_k and M.
  --
  -- Then the Cantor diagonal gives a single ψ. The L²-Cauchy estimate is
  -- the 3-term triangle inequality in the docstring.
  --
  -- This composition is ~200 LoC of plumbing. We leave it as a single
  -- `sorry` to be filled in once MLG-{2,4,5} land.
  sorry

/-! ## §6. A.e. corollary via convergence in measure

Conversion from `L²` convergence to a.e. convergence along a further
sub-subsequence, using PRESENT Mathlib lemmas:
  * `MeasureTheory.tendstoInMeasure_of_tendsto_eLpNorm`
    (`Mathlib/MeasureTheory/Function/ConvergenceInMeasure.lean:463`)
  * `MeasureTheory.TendstoInMeasure.exists_seq_tendsto_ae`
    (`Mathlib/MeasureTheory/Function/ConvergenceInMeasure.lean:277`)

This step is sorry-free given `kolmogorov_riesz_frechet_compactness`. -/

/-- **KRF compactness, a.e. corollary.**

The subsequence produced by `kolmogorov_riesz_frechet_compactness`
admits a further sub-subsequence converging a.e. on `Ω`. -/
theorem kolmogorov_riesz_frechet_compactness_ae
    {Ω : Set (EuclideanSpace ℝ (Fin d))} {f : ℕ → EuclideanSpace ℝ (Fin d) → ℝ}
    (D : KolmogorovRieszFrechetSeq Ω f) :
    ∃ (ψ : ℕ → ℕ) (fInf : EuclideanSpace ℝ (Fin d) → ℝ),
      StrictMono ψ ∧
      ∀ᵐ x ∂(volume.restrict Ω),
        Tendsto (fun n => f (ψ n) x) atTop (𝓝 (fInf x)) := by
  -- Apply the integral-form KRF.
  obtain ⟨ψ, fInf, hψ_mono, hfInf_meas, hConv⟩ := kolmogorov_riesz_frechet_compactness D
  -- Convert L²-convergence to convergence in measure.
  have hMeas : ∀ n, AEStronglyMeasurable (Ω.indicator (f (ψ n))) volume := by
    intro n; exact (D.meas (ψ n)).indicator D.measΩ
  have hfInfInd : AEStronglyMeasurable (Ω.indicator fInf) volume :=
    hfInf_meas.indicator D.measΩ
  -- `tendstoInMeasure_of_tendsto_eLpNorm`:
  have hTM : TendstoInMeasure volume
      (fun n => Ω.indicator (f (ψ n))) atTop (Ω.indicator fInf) := by
    exact tendstoInMeasure_of_tendsto_eLpNorm
      (p := (2 : ENNReal)) (by norm_num) hMeas hfInfInd hConv
  -- Extract a.e.-convergent further sub-subsequence.
  obtain ⟨ns, hns_mono, hns_ae⟩ := hTM.exists_seq_tendsto_ae
  -- Compose subsequences.
  refine ⟨ψ ∘ ns, fInf, hψ_mono.comp hns_mono, ?_⟩
  -- Restrict the a.e. statement from `volume` to `volume.restrict Ω`.
  -- TODO: Mathlib gap (minor): on `Ω`, indicator `Ω.indicator g x = g x`,
  -- so a.e. convergence of indicators on the full space implies a.e.
  -- convergence of `f (ψ (ns n)) x → f∞ x` on `Ω`.
  --
  -- This uses `Set.indicator_of_mem` + `ae_restrict_iff'`. About 10 LoC.
  -- Sketch:
  --   filter_upwards [(ae_restrict_iff' D.measΩ).mpr (hns_ae.mono ?_)] with x hx
  --   intro x hx; rw [Set.indicator_of_mem hx, Set.indicator_of_mem hx] at hx
  --   exact hx
  rw [ae_restrict_iff' D.measΩ]
  filter_upwards [hns_ae] with x hx hxΩ
  simpa [Set.indicator_of_mem hxΩ] using hx

/-! ## §7. Translation-continuity is automatic on `MemLp 2`

A standard companion lemma. For any `f ∈ L²(volume)` on `ℝᵈ`,
`f` is automatically translation-continuous in `L²`.

PROOF (Lieb–Loss Th. 2.16): density of `C_c(ℝᵈ)` in `L²` plus uniform
continuity of `C_c` functions.

MATHLIB GAP MLG-1: The named lemma
`MeasureTheory.tendsto_translate_eLpNorm_zero` does not exist in
v4.30.0-rc2. The building blocks (`Lp.continuous_compact_dense`,
`Continuous.uniformContinuous_of_compactSupport`,
`Measure.IsAddHaarMeasure`) are all PRESENT. -/

/-- **`L²` translation continuity for `MemLp 2` functions.**

Reference: Lieb–Loss, *Analysis*, Theorem 2.16. -/
theorem tendsto_translate_eLpNorm_zero
    {f : EuclideanSpace ℝ (Fin d) → ℝ} (_hf : MemLp f 2 volume) :
    Tendsto (fun h : EuclideanSpace ℝ (Fin d) =>
      eLpNorm (fun x => f (x + h) - f x) 2 volume) (𝓝 0) (𝓝 0) := by
  -- TODO: Mathlib gap MLG-1.
  -- 3-step proof:
  --   (a) approximate f by g ∈ C_c(ℝᵈ) within ε in L²
  --       (`MemLp.exists_hasCompactSupport_eLpNorm_sub_le`).
  --   (b) g is uniformly continuous (compact support + continuity).
  --   (c) Triangle inequality:
  --       ‖τ_h f − f‖₂ ≤ ‖τ_h f − τ_h g‖₂ + ‖τ_h g − g‖₂ + ‖g − f‖₂.
  --       The first term equals ‖f − g‖₂ (Haar invariance). The second
  --       goes to 0 by uniform continuity. The third is < ε.
  -- ~150 LoC; closable today. We mark it as a Mathlib-PR target.
  sorry

/-! ## §8. Sorry / Mathlib-gap inventory

| Tag    | Theorem                                         | Type     | LoC  |
|--------|-------------------------------------------------|----------|------|
| MLG-1  | `tendsto_translate_eLpNorm_zero`                 | gap      | ~150 |
| MLG-2  | `mollifier_rate_uniform` (Minkowski rate form)  | gap      | ~300 |
| MLG-4  | C¹-bound used in §5 composition                 | gap      | ~50  |
| MLG-5  | `arzela_ascoli_mollified_subsequence`           | gap      | ~150 |
| GLUE-A | §5 composition (steps 2–6)                      | plumbing | ~200 |
| GLUE-B | §6 indicator-on-restrict                         | closed   | done |

Total `sorry` count: **4** (one per ABSENT-Mathlib gap MLG-1, MLG-2, MLG-5
plus GLUE-A; MLG-4 is implicit inside GLUE-A and not a
separate sorry).

Three are ABSENT-Mathlib-lemma gaps (MLG-1, MLG-2, MLG-5), one is a
load-bearing analytic step packageable from existing infrastructure
(MLG-4), and the remaining pure plumbing sorry is GLUE-A. GLUE-B was
closed on 2026-05-27 by rewriting the a.e. convergence statement through
`ae_restrict_iff'` and `Set.indicator_of_mem`.

Cantor diagonal extraction (§4) is fully proved.
The §6 `tendstoInMeasure_of_tendsto_eLpNorm` invocation is correctly
wired; the previous indicator-on-restrict block is closed.

## Estimated effort to land in Mathlib upstream

- MLG-1 (`tendsto_translate_eLpNorm_zero`):     ~ 1 PR, 1–2 weeks.
- MLG-2 (Minkowski convolution rate form):     ~ 1 PR, 2–4 weeks.
- MLG-4 (C¹-bound on smoothed):                ~ 1 PR, 1 week.
- MLG-5 (Ascoli subsequence form):             ~ 1 PR, 2 weeks.
- This file (composition + KRF master):         ~ 1 PR, 1 week (after above land).

Total: ~ 5 PRs, 8–10 author-weeks in calendar terms (parallelizable to
~6 author-weeks). After KRF lands, the Aubin–Lions stub in NS Track B
discharges with a single Ehrling-interpolation PR (additional ~ 4 weeks).
-/

end

end MeasureTheory
