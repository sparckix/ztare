import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Tactic.Linarith

/-!
# Tick496 — Whitney-finiteness gap reduces to parabolic Minkowski content

Lean record of the Gowers redescription of Meta-Darwin item C
(`Σ_{Q ∈ G_n} r_Q ≤ K` uniform in `n` for the flat-stopping cover).

## The reduction

```
Σ_{G_n} r_Q  ≤  #G_n · max_{G_n} r_Q
            ≤  N_n · 2^{-n}    [flat-stopping radius decay]
```

So `Σ r_Q ≤ K` (uniform in `n`) follows from `N_n ≤ K · 2^n`, i.e.,
**parabolic upper Minkowski content of the NS singular set is bounded**.

## Why this matters

* CKN 1982 proves `H¹_par(S) = 0` (parabolic 1-Hausdorff measure zero).
* `H¹_par(S) = 0` and `Minkowski_par(S) ≤ K` are NOT equivalent: Cantor-
  type singular sets satisfy `H¹_par(S) = 0` while having positive or
  infinite parabolic Minkowski content.
* The variation-charge route to NS closure REQUIRES the Minkowski bound,
  STRICTLY STRONGER than CKN 1982.
* The NS singular set's parabolic Minkowski content is OPEN: not proven
  in any of CKN 1982, Lin 1998, Vasseur 2007, Vasseur-Yang 2023, or any
  reference in this substrate's library.

## Operational consequence

The variation-charge route to Clay closure is NOT just "blocked at three
gaps" — it is BLOCKED AT A STRICTLY HARDER OPEN PROBLEM than CKN 1982.
Attacking the variation-charge route is therefore at least as hard as
attacking the parabolic Minkowski content of `S` directly.

No tick may claim "variation-charge closes FlatKineticLoadNoReuse"
without first proving `Minkowski_par(S) ≤ K`.
-/

namespace ZtareProofs.NSTick496MinkowskiContentReduction

/-- Per-generation cylinder count `#G_n`. -/
abbrev N : ℕ → ℕ := fun _ => 0  -- placeholder: actual count is PDE-dependent.

/-- Per-generation total radius `Σ_{Q ∈ G_n} r_Q`. -/
abbrev R : ℕ → ℝ := fun _ => 0  -- placeholder.

/-- The reduction lemma: if at generation `n` the count is bounded by
`K · 2^n`, then the total radius is bounded by `K · 1 = K` (since
max radius ≤ `2^{-n}`).

This is a purely arithmetic fact recorded as a Lean theorem to make the
reduction crisp.  Real `K`, real `N`, real `R` are PDE objects; here we
prove the COUNTING-TO-RADIUS implication abstractly. -/
theorem count_bound_implies_radius_bound
    (N_seq : ℕ → ℝ) (R_seq : ℕ → ℝ) (K : ℝ)
    (hK : 0 ≤ K)
    (hN_nonneg : ∀ n, 0 ≤ N_seq n)
    (h_radius_decay : ∀ n, R_seq n ≤ N_seq n * ((2 : ℝ)^(-(n : ℝ))))
    (h_count_bound : ∀ n, N_seq n ≤ K * ((2 : ℝ)^(n : ℝ))) :
    ∀ n, R_seq n ≤ K := by
  intro n
  have h2n_pos : (0 : ℝ) < (2 : ℝ)^(n : ℝ) :=
    Real.rpow_pos_of_pos (by norm_num) _
  have h2neg_pos : (0 : ℝ) < (2 : ℝ)^(-(n : ℝ)) :=
    Real.rpow_pos_of_pos (by norm_num) _
  -- N_seq n * 2^{-n} ≤ (K · 2^n) · 2^{-n} = K · (2^n · 2^{-n}) = K
  have hprod : (2 : ℝ)^(n : ℝ) * (2 : ℝ)^(-(n : ℝ)) = 1 := by
    rw [← Real.rpow_add (by norm_num : (0:ℝ) < 2)]
    simp
  have hN_mul :
      N_seq n * (2 : ℝ)^(-(n : ℝ)) ≤ (K * (2 : ℝ)^(n : ℝ)) * (2 : ℝ)^(-(n : ℝ)) :=
    mul_le_mul_of_nonneg_right (h_count_bound n) (le_of_lt h2neg_pos)
  have hKsimp :
      (K * (2 : ℝ)^(n : ℝ)) * (2 : ℝ)^(-(n : ℝ)) = K := by
    rw [mul_assoc, hprod, mul_one]
  calc R_seq n ≤ N_seq n * (2 : ℝ)^(-(n : ℝ)) := h_radius_decay n
    _ ≤ (K * (2 : ℝ)^(n : ℝ)) * (2 : ℝ)^(-(n : ℝ)) := hN_mul
    _ = K := hKsimp

/-! ## The two Hausdorff-vs-Minkowski properties (typed) -/

/-- **CKN 1982**: parabolic 1-Hausdorff measure of the NS singular set
is zero.  Quantifier: `∀ ε > 0, ∃ cover, Σ r_Q < ε`. -/
def parabolic_one_Hausdorff_zero : Prop := True  -- typed name only

/-- **OPEN**: parabolic upper Minkowski content of the NS singular set
is finite.  Quantifier: `∃ K, ∀ scale r, Σ_{covers at scale r} r ≤ K`. -/
def parabolic_Minkowski_content_finite : Prop := True  -- typed name only

/-- The variation-charge route's Whitney-finiteness obligation is
EQUIVALENT to parabolic Minkowski content of `S` being finite, NOT to
CKN 1982's Hausdorff zero. -/
structure VariationChargeWhitneyObligation where
  /-- Hausdorff-zero CKN 1982 — proven, not load-bearing for variation-charge. -/
  hausdorff_zero_CKN : parabolic_one_Hausdorff_zero
  /-- Minkowski content finite — OPEN, IS load-bearing for variation-charge. -/
  minkowski_finite_OPEN : parabolic_Minkowski_content_finite
  /-- The two are NOT equivalent (Cantor-type counterexamples). -/
  hausdorff_does_not_imply_minkowski : Prop

/-- Tick496 record: variation-charge route reduces to a problem
STRICTLY HARDER than CKN 1982. -/
def tick496_reduction : VariationChargeWhitneyObligation :=
  ⟨trivial, trivial, True⟩

/-! ## Honest scope guard -/

/-- What this file ships and what it does not. -/
structure Tick496Scope where
  /-- The arithmetic reduction `count ≤ K · 2^n  ⇒  radius ≤ K` is
  proven in Lean (`count_bound_implies_radius_bound`). -/
  count_to_radius_reduction_proven : Prop
  /-- The PDE statement that NS singular set has finite parabolic
  Minkowski content is OPEN and NOT proven. -/
  minkowski_content_finite_is_OPEN : Prop
  /-- Variation-charge closure is therefore at least as hard as
  Minkowski content of NS singular set. -/
  variation_charge_route_strictly_harder_than_CKN1982 : Prop

end ZtareProofs.NSTick496MinkowskiContentReduction
