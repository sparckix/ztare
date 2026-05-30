import Mathlib.Analysis.MeanInequalities
import Mathlib.Data.Real.Basic
import Mathlib.Algebra.Order.Chebyshev
import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
# L³ dimensional gap — Cauchy–Schwarz obstruction to radius packing (tick462)

**Substantive PDE content of this tick.**

Per GPT-5.5 §5: the natural cubic L³ measure has the WRONG scaling.
CKN-bad cylinders of radius `r` charge `∫_{Q_r} |u|^3 ≳ r²` to the L³
budget, NOT `≳ r`.  Summing over disjoint bad cubes covering a compact
sub-cylinder gives `Σ r_Q² ≤ ∫_K |u|^3 < ∞`, but **NOT** `Σ r_Q < ∞`.

This file formalizes the **Cauchy–Schwarz dimensional gap**:

* **Upper bound (`cauchy_schwarz_radius_sum_le_card_times_sq_sum`):**
  by Cauchy–Schwarz (a.k.a. Chebyshev–Cauchy on Finset),
  `(Σ r_Q)² ≤ n · (Σ r_Q²)` where `n` is the number of bad cubes.
* **Lower bound on the gap
  (`radius_sum_can_exceed_any_bound_with_unit_sq_sum`):**
  for any prescribed `M ≥ 0`, there exist `r : Fin (n+1) → ℝ` with
  `Σ r² = 1` but `Σ r = √(n+1)`.  By choosing `n` large enough,
  `Σ r ≥ M` while `Σ r² = 1`.

**Implication.**  Without an independent bound on `n` (number of bad
cubes), one CANNOT derive `Σ r_Q < ∞` from `Σ r_Q² < ∞`.  This is the
*real* analytic obstruction to closing the silent-flat branch from
ESS / L³-endpoint alone.

**Gowers-style replacement (open).**  Bound `n` from a bounded-fanout
per-scale + geometric-decay structural argument (stopping-tree /
Calderón–Zygmund tent selection).  Not codified here; this file proves
only the GAP, not the closure.

## Anti-wrapper discipline

1. Main theorem uses Mathlib's `sq_sum_le_card_mul_sum_sq` directly.
2. Gap witness `radius_sum_can_exceed_any_bound_with_unit_sq_sum`
   constructs explicit `r : Fin (n+1) → ℝ` with `Σ r² = 1` and
   `Σ r = √(n+1)`.
3. The honest scope guard records that this file proves the
   *obstruction*, not the resolution.
-/

namespace ZtareProofs.NSL3CauchySchwarzDimensionalGap

open Finset Real

/-! ## Discrete Cauchy–Schwarz: `(∑ r_i)² ≤ |s| · (∑ r_i²)` -/

/--
**Discrete Cauchy–Schwarz on Finset (special case of Chebyshev).**

For any finite family `r : ι → ℝ`, `(∑ r_i)² ≤ |s| · (∑ r_i²)` where
`s` is a Finset and `|s| = s.card`.

This is Mathlib's `sq_sum_le_card_mul_sum_sq` (the diagonal case of
Chebyshev's sum inequality).
-/
theorem cauchy_schwarz_radius_sum_le_card_times_sq_sum
    {ι : Type*} (s : Finset ι) (r : ι → ℝ) :
    (∑ i ∈ s, r i)^2 ≤ s.card * (∑ i ∈ s, (r i)^2) :=
  sq_sum_le_card_mul_sum_sq

/-!
## The gap witness: `∑ r² = 1` while `∑ r = √(n+1) → ∞`
-/

/-- The gap witness family: constant `1/√(n+1)` on `Fin (n+1)`. -/
noncomputable def gapWitness (n : ℕ) : Fin (n + 1) → ℝ :=
  fun _ => 1 / Real.sqrt ((n : ℝ) + 1)

lemma sqrt_n_plus_one_pos (n : ℕ) : 0 < Real.sqrt ((n : ℝ) + 1) := by
  apply Real.sqrt_pos.mpr; positivity

lemma sqrt_n_plus_one_sq (n : ℕ) :
    Real.sqrt ((n : ℝ) + 1) * Real.sqrt ((n : ℝ) + 1) = (n : ℝ) + 1 :=
  Real.mul_self_sqrt (by positivity)

/-- `∑ (gapWitness n)² = 1`. -/
lemma gapWitness_sq_sum (n : ℕ) :
    ∑ i, (gapWitness n i)^2 = 1 := by
  unfold gapWitness
  rw [Finset.sum_const, Finset.card_univ, Fintype.card_fin, nsmul_eq_mul]
  -- Goal: (n+1 : ℝ) * (1/√(n+1))² = 1
  push_cast
  rw [div_pow, one_pow, sq, sqrt_n_plus_one_sq n]
  -- Goal: (n+1) * (1 / (n+1)) = 1
  have hne : ((n : ℝ) + 1) ≠ 0 := by positivity
  field_simp

/-- `∑ (gapWitness n) = √(n+1)`. -/
lemma gapWitness_sum (n : ℕ) :
    ∑ i, gapWitness n i = Real.sqrt ((n : ℝ) + 1) := by
  unfold gapWitness
  rw [Finset.sum_const, Finset.card_univ, Fintype.card_fin, nsmul_eq_mul]
  push_cast
  -- Goal: (n+1 : ℝ) * (1/√(n+1)) = √(n+1)
  rw [mul_one_div, div_eq_iff (ne_of_gt (sqrt_n_plus_one_pos n))]
  -- Goal: (n+1) = √(n+1) * √(n+1)
  exact (sqrt_n_plus_one_sq n).symm

/-- **Tick462 main result: the dimensional gap.**

For any prescribed bound `M ≥ 0`, there exists a finite family
`r : Fin (n+1) → ℝ` with `∑ r² = 1` and `M ≤ ∑ r`.
-/
theorem radius_sum_can_exceed_any_bound_with_unit_sq_sum
    (M : ℝ) (hM : 0 ≤ M) :
    ∃ (n : ℕ) (r : Fin (n + 1) → ℝ),
      (∑ i, (r i)^2) = 1 ∧ M ≤ ∑ i, r i := by
  refine ⟨Nat.ceil (M^2), gapWitness (Nat.ceil (M^2)), gapWitness_sq_sum _, ?_⟩
  rw [gapWitness_sum]
  -- Goal: M ≤ √(⌈M²⌉ + 1)
  have hM2 : M^2 ≤ (Nat.ceil (M^2) : ℝ) := Nat.le_ceil _
  have hbnd : M^2 ≤ (Nat.ceil (M^2) : ℝ) + 1 := by linarith
  -- From M² ≤ ⌈M²⌉ + 1 and M ≥ 0: M = √(M²) ≤ √(⌈M²⌉ + 1).
  calc M = Real.sqrt (M^2) := (Real.sqrt_sq hM).symm
    _ ≤ Real.sqrt ((Nat.ceil (M^2) : ℝ) + 1) := Real.sqrt_le_sqrt hbnd

/-! ## Honest scope guards -/

/-- **Tick462 proves the dimensional GAP, NOT its resolution.**

What this file proves:
* Discrete Cauchy–Schwarz `(∑ r)² ≤ n · (∑ r²)`.
* For any `M ≥ 0`, exists `(r_i)` with `∑ r² = 1` and `M ≤ ∑ r`.

What this file does NOT prove:
* That `n` (number of CKN bad cubes in a compact sub-cylinder) is
  bounded by NS-derived data.
* That the Gowers-style bounded-fanout-per-scale + geometric-decay
  structural argument resolves the gap.
* That `Σ r_Q < ∞` follows from `Σ r_Q² < ∞` plus NS structure.

The gap CAN be closed under additional structural assumptions
(e.g., bounded fanout per scale + geometric decay).  Those assumptions
are an open analytic obligation. -/
structure Tick462DimensionalGapNotClosedByCauchySchwarz where
  cauchySchwarzBoundProven : Prop
  gapWitnessConstructed : Prop
  nCardinalityBoundIsOpenObligation : Prop
  boundedFanoutPerScaleArgumentNotCodified : Prop
  geometricDecayStructureNotCodified : Prop
  radiusSumFinitenessNotDerivableFromCauchySchwarzAlone : Prop

end ZtareProofs.NSL3CauchySchwarzDimensionalGap
