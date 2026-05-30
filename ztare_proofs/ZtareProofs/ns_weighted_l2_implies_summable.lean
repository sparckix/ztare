import Mathlib.Analysis.MeanInequalities
import Mathlib.Data.Real.Basic
import Mathlib.Topology.Instances.Real.Lemmas
import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Algebra.Order.Chebyshev
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Analysis.PSeries
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import ZtareProofs.ns_weighted_l2_kills_dini_cascade

/-!
# Weighted L² implies Summable — full implication (tick470)

**Gowers redescription chain (per operator's blog reference 2026-05-08):**

  Old: "Find a measure that pays r"          (failed — r² vs r dim gap, tick462)
  →   "Prove uniform θ < 1 decay"           (failed — Dini cascade, tick467)
  →   "Show weighted L² with p > 1"          (NEW — works against Dini)

This file completes the third step formally: from
`Σ_n A_n² · (n+1)^p < ∞` (weighted L² with `p > 1`) and `0 ≤ A_n`,
derive `Summable A`.

**Proof.** Discrete Cauchy–Schwarz with weight (tick469): for every `N`,
  `(Σ_{n<N} A_n)² ≤ (Σ_{n<N} A_n² · (n+1)^p) · (Σ_{n<N} 1/(n+1)^p)`
  `≤ C₁ · C₂`
where `C₁ := Σ' A_n² · (n+1)^p` and `C₂ := Σ' 1/(n+1)^p`, both finite
(`p > 1` p-series).  Taking `√`: `Σ_{n<N} A_n ≤ √(C₁ · C₂)` uniformly
in `N`.  Apply Mathlib's `summable_of_sum_range_le` for `ℝ`-valued
nonneg.

## Significance

This Lean theorem rules out **every nonneg Dini cascade** — not just
the harmonic `1/(n+1)` countermodel from tick467, but EVERY non-summable
nonneg sequence satisfying the weighted L² bound.  Strictly stronger
than tick469 (which only ruled out the harmonic at `p=2`).

**Stays in ℝ throughout** — no NNReal/ENNReal detour
(per meta_darwin_proxy GP-230 forecast M3 concern; resolved via
`summable_of_sum_range_le` which lives in
`Mathlib.Topology.Algebra.InfiniteSum.Real`).
-/

namespace ZtareProofs.NSWeightedL2ImpliesSummable

open ZtareProofs.NSWeightedL2KillsDiniCascade
open Finset Real

/--
**Tick470 main theorem: weighted L²-summability implies plain summability.**

For nonneg `A : ℕ → ℝ`, if `Σ_n A_n² · (n+1)^p < ∞` for some integer
`p > 1`, then `Summable A`.

Uses Mathlib named lemmas: `summable_of_sum_range_le` (ℝ),
`Summable.sum_le_tsum`, `sum_mul_sq_le_sq_mul_sq` (Cauchy–Schwarz),
`weighted_p_series_summable` (tick469), `Real.sqrt_le_sqrt`,
`Real.sqrt_sq`, `mul_le_mul`.
-/
theorem weighted_l2_implies_summable
    {A : ℕ → ℝ} (hA_nonneg : ∀ n, 0 ≤ A n)
    {p : ℕ} (hp : 1 < p)
    (hwsum : Summable (fun n => (A n)^2 * ((n : ℝ) + 1)^p)) :
    Summable A := by
  -- C₂ := Σ' 1/(n+1)^p, finite for p > 1.
  have hC₂_summable : Summable (fun n : ℕ => 1 / ((n : ℝ) + 1)^p) :=
    weighted_p_series_summable p hp
  let C₁ : ℝ := ∑' n : ℕ, (A n)^2 * ((n : ℝ) + 1)^p
  let C₂ : ℝ := ∑' n : ℕ, 1 / ((n : ℝ) + 1)^p
  have hC₁_def : C₁ = ∑' n : ℕ, (A n)^2 * ((n : ℝ) + 1)^p := rfl
  have hC₂_def : C₂ = ∑' n : ℕ, 1 / ((n : ℝ) + 1)^p := rfl
  -- C₁, C₂ ≥ 0 since summands nonneg.
  have hsummand1_nonneg : ∀ n : ℕ, 0 ≤ (A n)^2 * ((n : ℝ) + 1)^p := by
    intro n; positivity
  have hsummand2_nonneg : ∀ n : ℕ, 0 ≤ 1 / ((n : ℝ) + 1)^p := by
    intro n; positivity
  have hC₁_nonneg : 0 ≤ C₁ := tsum_nonneg hsummand1_nonneg
  have hC₂_nonneg : 0 ≤ C₂ := tsum_nonneg hsummand2_nonneg
  -- The bound: Σ_{n<N} A_n ≤ √(C₁ · C₂).
  have hbound : ∀ N : ℕ, ∑ n ∈ Finset.range N, A n ≤ Real.sqrt (C₁ * C₂) := by
    intro N
    have hSum_nonneg : 0 ≤ ∑ n ∈ Finset.range N, A n :=
      Finset.sum_nonneg (fun n _ => hA_nonneg n)
    -- Apply tick469's weighted Cauchy-Schwarz with weight w n := (n+1)^p.
    have hCS := weighted_cauchy_schwarz_partial_sum N A
      (fun n => ((n : ℝ) + 1)^p) hA_nonneg (fun n => by positivity)
    -- Bound each Finset partial sum by its tsum (nonneg + summable).
    have hpartial_le_C₁ :
        ∑ n ∈ Finset.range N, (A n)^2 * ((n : ℝ) + 1)^p ≤ C₁ :=
      hwsum.sum_le_tsum (Finset.range N) (fun n _ => hsummand1_nonneg n)
    have hpartial_le_C₂ :
        ∑ n ∈ Finset.range N, 1 / ((n : ℝ) + 1)^p ≤ C₂ :=
      hC₂_summable.sum_le_tsum (Finset.range N) (fun n _ => hsummand2_nonneg n)
    -- Combine: (Σ A_n)² ≤ C₁ · C₂.
    have hsum_sq_le : (∑ n ∈ Finset.range N, A n)^2 ≤ C₁ * C₂ := by
      have hCS_nonneg1 : 0 ≤ ∑ n ∈ Finset.range N, (A n)^2 * ((n : ℝ) + 1)^p :=
        Finset.sum_nonneg (fun n _ => hsummand1_nonneg n)
      calc (∑ n ∈ Finset.range N, A n)^2
          ≤ (∑ n ∈ Finset.range N, (A n)^2 * ((n : ℝ) + 1)^p)
              * (∑ n ∈ Finset.range N, 1 / ((n : ℝ) + 1)^p) := hCS
        _ ≤ C₁ * C₂ := mul_le_mul hpartial_le_C₁ hpartial_le_C₂
              (Finset.sum_nonneg (fun n _ => hsummand2_nonneg n)) hC₁_nonneg
    -- Take √: Σ A_n ≤ √(C₁ · C₂).
    calc ∑ n ∈ Finset.range N, A n
        = Real.sqrt ((∑ n ∈ Finset.range N, A n)^2) :=
          (Real.sqrt_sq hSum_nonneg).symm
      _ ≤ Real.sqrt (C₁ * C₂) := Real.sqrt_le_sqrt hsum_sq_le
  -- Lift bounded partial sums to Summable via Mathlib (in ℝ).
  exact summable_of_sum_range_le hA_nonneg hbound

/-! ## Honest scope guard -/

/-- **Tick470 closes the Gowers replacement chain at the formal level.**

* Tick462 proved the dimensional gap (r² vs r) algebraically.
* Tick467 sharpened the obstruction to the Dini cascade.
* Tick469 proved discrete weighted Cauchy–Schwarz and the harmonic
  countermodel fails weighted L² at `p = 2`.
* **Tick470 (this file)** proves the FULL implication:
  weighted L² at any `p > 1` ⇒ Summable.

This rules out every nonneg Dini cascade under the weighted L²
hypothesis.  The Gowers redescription chain (per operator's blog
reference) is now formally complete at the Lean level.

What remains open:
* Does Navier–Stokes supply weighted L² on per-generation charge
  for some `p > 1`?  This is the new sharpened analytic obligation.
  It is strictly weaker than tick464's uniform `θ < 1` and strictly
  stronger than plain `Σ E_n < ∞`. -/
structure Tick470GowersChainCompleteAtFormalLevel where
  weightedL2ImpliesSummableProvenInLean : Prop
  staysInRealNoNNRealDetour : Prop
  gowersReplacementChainFormallyComplete : Prop
  newOpenContentIsWeightedL2FromNSData : Prop
  metaDarwinAntiLaunderingCatchAddressed : Prop

end ZtareProofs.NSWeightedL2ImpliesSummable
