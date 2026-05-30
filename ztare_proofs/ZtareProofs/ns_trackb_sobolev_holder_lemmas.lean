/-
# NS Track B — Sobolev embedding `H¹(ℝ³) ↪ L⁶(ℝ³)` and Hölder
# interpolation `L² ∩ L⁶ ↪ L³` Mathlib bridges

This file closes the two **Mathlib-infrastructure gaps** identified by
`ns_trackb_ess_l3_endpoint.lean` (the brute-force ESS attempt):

1. `sorry_sobolev_embedding_H1_into_L6_R3` — Gagliardo-Nirenberg-
   Sobolev `H¹(ℝ³) ↪ L⁶(ℝ³)`.

2. `sorry_holder_L2_L6_to_L3` — Hölder interpolation
   `‖u‖_{L³} ≤ ‖u‖_{L²}^{1/2} · ‖u‖_{L⁶}^{1/2}`.

These are STANDARD analysis results. Mathlib supplies:

* `MeasureTheory.eLpNorm_le_eLpNorm_fderiv_of_eq` — the general
  Gagliardo-Nirenberg-Sobolev inequality (for compactly-supported
  `C¹` functions on a finite-dimensional normed space). Specialize
  to `E = EuclideanSpace ℝ (Fin 3)`, `p = 2`, `p' = 6`, using the
  identity `1/6 = 1/2 - 1/3`.

* `MeasureTheory.eLpNorm_le_eLpNorm_mul_eLpNorm_of_nnnorm` —
  the abstract Hölder bilinear inequality with a `HolderTriple`
  type-class. Specialize to `HolderTriple 2 6 (3/2)` to obtain
  `‖u·u‖_{3/2} ≤ ‖u‖_{2} · ‖u‖_{6}`, i.e.
  `‖u‖_{L³}^{2} ≤ ‖u‖_{L²} · ‖u‖_{L⁶}`, then take square roots.

The composition gives the **borderline Galerkin bound**

  `‖u‖_{L³}^{2} ≤ C · ‖u‖_{L²} · ‖∇u‖_{L²}`

which is exactly the time-integrated `L³_x` bound that the Galerkin
construction's `M_kin` (kinetic) and `M_ens` (enstrophy) provide.

**Honest scope.** This file closes voids (1) and (2) of the
brute-force ESS attempt. Voids (3), (4), (5) — the pointwise-in-`t`
`L³_x` bound, weak-`L²` lower semicontinuity at exponent 3, and the
uniform-in-`n` `L³_x` bound on Galerkin truncations — remain
**Clay-equivalent** at the borderline scaling-critical exponent and
are NOT closed here.

## Architecture

* `H1_into_L6_R3`           — Sobolev `H¹(ℝ³) ↪ L⁶(ℝ³)`
* `holder_L2_L6_to_L3`      — Hölder `L² ∩ L⁶ ↪ L³`
* `sobolev_holder_L3_bound` — composition (Galerkin borderline bound)

## References

* Gagliardo-Nirenberg-Sobolev: Mathlib4 file
  `Mathlib/Analysis/FunctionalSpaces/SobolevInequality.lean`,
  theorem `eLpNorm_le_eLpNorm_fderiv_of_eq`.

* Hölder bilinear: Mathlib4 file
  `Mathlib/MeasureTheory/Function/LpSeminorm/CompareExp.lean`,
  theorem `eLpNorm_le_eLpNorm_mul_eLpNorm_of_nnnorm` and
  `Mathlib/Data/ENNReal/Holder.lean`'s `HolderTriple` class.
-/

import Mathlib.Analysis.FunctionalSpaces.SobolevInequality
import Mathlib.MeasureTheory.Function.LpSeminorm.CompareExp
import Mathlib.Data.ENNReal.Holder
import Mathlib.Analysis.InnerProductSpace.EuclideanDist
import Mathlib.Tactic

open MeasureTheory Module
open scoped ENNReal NNReal

namespace ZtareProofs.NS.SobolevHolder

noncomputable section

/-- Shorthand for `EuclideanSpace ℝ (Fin 3)`, the codomain/domain of
3D Navier-Stokes. -/
abbrev E3 : Type := EuclideanSpace ℝ (Fin 3)

instance : MeasurableSpace E3 := borel _
instance : BorelSpace E3 := ⟨rfl⟩

/-! ## §1.  Sobolev `H¹(ℝ³) ↪ L⁶(ℝ³)` -/

/-- The Mathlib constant produced by the GNS specialization at
`p = 2`, `p' = 6`, `n = 3`. Kept as `ℝ≥0` and named for downstream
use. -/
def C_sobolev_H1_L6 (μ : Measure E3) [μ.IsAddHaarMeasure] : ℝ≥0 :=
  SNormLESNormFDerivOfEqConst (F := ℝ) μ 2

/-- **Gagliardo-Nirenberg-Sobolev**, specialized to `H¹(ℝ³) ↪ L⁶(ℝ³)`.

If `u : EuclideanSpace ℝ (Fin 3) → ℝ` is `C¹` and compactly supported,
then

  `‖u‖_{L⁶(ℝ³)} ≤ C · ‖∇u‖_{L²(ℝ³)}`

with constant `C := SNormLESNormFDerivOfEqConst F μ 2`.

This is the direct specialization of `eLpNorm_le_eLpNorm_fderiv_of_eq`
to `E = EuclideanSpace ℝ (Fin 3)`, `F = ℝ`, `p = 2`, `p' = 6`, using
the arithmetic identity `(6 : ℝ)⁻¹ = (2 : ℝ)⁻¹ - (3 : ℝ)⁻¹`. -/
theorem H1_into_L6_R3
    (μ : Measure E3) [μ.IsAddHaarMeasure]
    {u : E3 → ℝ} (hu : ContDiff ℝ 1 u) (h2u : HasCompactSupport u) :
    eLpNorm u 6 μ
      ≤ (C_sobolev_H1_L6 μ : ℝ≥0∞) * eLpNorm (fderiv ℝ u) 2 μ := by
  have hp : (1 : ℝ≥0) ≤ 2 := by norm_num
  have hn : 0 < finrank ℝ E3 := by
    -- `finrank ℝ (EuclideanSpace ℝ (Fin 3)) = 3`
    simp [E3, finrank_euclideanSpace, Fintype.card_fin]
  have hfinrank : (finrank ℝ E3 : ℝ) = 3 := by
    simp [E3, finrank_euclideanSpace, Fintype.card_fin]
  have hp' : ((6 : ℝ≥0) : ℝ)⁻¹ = ((2 : ℝ≥0) : ℝ)⁻¹ - (finrank ℝ E3 : ℝ)⁻¹ := by
    rw [hfinrank]; push_cast; ring
  have h := MeasureTheory.eLpNorm_le_eLpNorm_fderiv_of_eq
    (E := E3) (F := ℝ) (μ := μ) (u := u) (p := (2 : ℝ≥0)) (p' := (6 : ℝ≥0))
    hu h2u hp hn hp'
  simpa [C_sobolev_H1_L6] using h

/-! ## §2.  Hölder interpolation `‖u‖_{L³} ≤ ‖u‖_{L²}^{1/2} · ‖u‖_{L⁶}^{1/2}` -/

/-- The `HolderTriple 2 6 (3/2)` instance: `1/2 + 1/6 = 2/3 = 1/(3/2)`.

This is the load-bearing arithmetic enabling the bilinear Hölder
inequality at exponents `(2, 6, 3/2)`. -/
instance hoelderTriple_2_6 :
    ENNReal.HolderTriple (2 : ℝ≥0∞) 6 (3 / 2) where
  inv_add_inv_eq_inv := by
    -- `(2 : ℝ≥0∞)⁻¹ + (6 : ℝ≥0∞)⁻¹ = (3 / 2 : ℝ≥0∞)⁻¹`. Lift to
    -- `ℝ≥0` (all values are nonzero finite) and do the arithmetic.
    have h : ((2 : ℝ≥0∞)⁻¹ + (6 : ℝ≥0∞)⁻¹).toReal
        = ((3 / 2 : ℝ≥0∞)⁻¹).toReal := by
      simp [ENNReal.toReal_inv, ENNReal.toReal_add, ENNReal.toReal_div]
      norm_num
    have h_ne_top₁ : (2 : ℝ≥0∞)⁻¹ + (6 : ℝ≥0∞)⁻¹ ≠ ∞ := by
      simp [ENNReal.add_eq_top]
    have h_ne_top₂ : (3 / 2 : ℝ≥0∞)⁻¹ ≠ ∞ := by
      simp [ENNReal.inv_eq_top, ENNReal.div_eq_zero_iff]
    exact (ENNReal.toReal_eq_toReal_iff' h_ne_top₁ h_ne_top₂).mp h

/-- **Bilinear Hölder at exponents `(2, 6, 3/2)`** for a scalar
function `u : E3 → ℝ`.

This applies `eLpNorm_le_eLpNorm_mul_eLpNorm_of_nnnorm` to the
bilinear map `(a, b) ↦ a * b` (with `‖a*b‖₊ ≤ 1 * ‖a‖₊ * ‖b‖₊`) and
`f = g = u`, yielding

  `eLpNorm (u·u) (3/2) μ ≤ eLpNorm u 2 μ · eLpNorm u 6 μ`. -/
private lemma holder_self_square_L3_half_aux
    (μ : Measure E3) {u : E3 → ℝ} (hu : AEStronglyMeasurable u μ) :
    eLpNorm (fun x => u x * u x) (3 / 2 : ℝ≥0∞) μ
      ≤ eLpNorm u 2 μ * eLpNorm u 6 μ := by
  have h := MeasureTheory.eLpNorm_le_eLpNorm_mul_eLpNorm_of_nnnorm
    (μ := μ) (p := (2 : ℝ≥0∞)) (q := 6) (r := (3 / 2 : ℝ≥0∞))
    (f := u) (g := u)
    hu hu (b := fun a b : ℝ => a * b) (c := 1)
    (by
      refine Filter.Eventually.of_forall (fun x => ?_)
      simp [nnnorm_mul])
  simpa using h

/-! Below: the squared form of the Hölder interpolation. The square
form drops out directly from `holder_self_square_L3_half_aux` once
we record the identity `eLpNorm (u·u) (3/2) = (eLpNorm u 3)^2`. The
1/2-power form follows by taking `ENNReal.rpow` of both sides. -/

/-- `eLpNorm (u·u) (3/2) μ = (eLpNorm u 3 μ)^2`.

Both sides equal `(∫ ‖u(x)‖ₑ^3 dμ)^{2/3}`. -/
theorem eLpNorm_self_mul_three_halves_eq_sq_eLpNorm_three
    (μ : Measure E3) {u : E3 → ℝ} :
    eLpNorm (fun x => u x * u x) (3 / 2 : ℝ≥0∞) μ
      = (eLpNorm u 3 μ) ^ 2 := by
  have h32_ne_zero : ((3 : ℝ≥0∞) / 2) ≠ 0 := by
    simp [ENNReal.div_eq_zero_iff]
  have h32_ne_top : ((3 : ℝ≥0∞) / 2) ≠ ∞ := by
    simp [ENNReal.div_eq_top]
  have h3_ne_zero : (3 : ℝ≥0∞) ≠ 0 := by norm_num
  have h3_ne_top : (3 : ℝ≥0∞) ≠ ∞ := by simp
  have h32_toReal : ((3 : ℝ≥0∞) / 2).toReal = 3 / 2 := by
    rw [ENNReal.toReal_div]; norm_num
  have h3_toReal : (3 : ℝ≥0∞).toReal = 3 := by norm_num
  -- Rewrite both sides via the integral formula.
  rw [MeasureTheory.eLpNorm_eq_lintegral_rpow_enorm_toReal h32_ne_zero h32_ne_top,
      MeasureTheory.eLpNorm_eq_lintegral_rpow_enorm_toReal h3_ne_zero h3_ne_top,
      h32_toReal, h3_toReal]
  -- LHS: (∫ ‖u·u‖ₑ^(3/2))^(2/3). Pointwise ‖u·u‖ₑ^(3/2) = ‖u‖ₑ^3.
  have h_pointwise : ∀ x, (‖u x * u x‖ₑ : ℝ≥0∞) ^ ((3 : ℝ) / 2)
      = ‖u x‖ₑ ^ (3 : ℝ) := by
    intro x
    rw [enorm_mul, ENNReal.mul_rpow_of_nonneg _ _ (by norm_num : (0 : ℝ) ≤ 3 / 2)]
    rw [← ENNReal.rpow_add_of_nonneg (3 / 2 : ℝ) (3 / 2 : ℝ)
        (by norm_num) (by norm_num)]
    congr 1
    norm_num
  simp_rw [h_pointwise]
  -- Now goal: (∫ ‖u‖ₑ^3)^(1/(3/2)) = ((∫ ‖u‖ₑ^3)^(1/3))^2 (^2 is npow).
  -- Convert RHS npow to rpow then collapse via rpow_mul.
  set I := ∫⁻ x, ‖u x‖ₑ ^ (3 : ℝ) ∂μ
  have hRHS : (I ^ ((1 : ℝ) / 3)) ^ 2 = I ^ ((2 : ℝ) * (1 / 3)) := by
    rw [show (I ^ ((1 : ℝ) / 3)) ^ 2 = (I ^ ((1 : ℝ) / 3)) ^ ((2 : ℕ) : ℝ) from
      (ENNReal.rpow_natCast _ 2).symm]
    rw [← ENNReal.rpow_mul]
    congr 1
    push_cast; ring
  rw [hRHS]
  congr 1
  norm_num


theorem holder_L2_L6_to_L3_squared
    (μ : Measure E3) {u : E3 → ℝ} (hu : AEStronglyMeasurable u μ) :
    (eLpNorm u 3 μ) ^ 2
      ≤ eLpNorm u 2 μ * eLpNorm u 6 μ := by
  rw [← eLpNorm_self_mul_three_halves_eq_sq_eLpNorm_three μ]
  exact holder_self_square_L3_half_aux μ hu

/-- Square-root form of `holder_L2_L6_to_L3_squared`:

  `‖u‖_{L³} ≤ ‖u‖_{L²}^{1/2} · ‖u‖_{L⁶}^{1/2}`.

Equivalent to `holder_L2_L6_to_L3_squared` modulo monotonicity of
`ENNReal.rpow` at exponent `1/2`. -/
theorem holder_L2_L6_to_L3
    (μ : Measure E3) {u : E3 → ℝ} (hu : AEStronglyMeasurable u μ) :
    eLpNorm u 3 μ
      ≤ (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
        * (eLpNorm u 6 μ) ^ ((1 : ℝ) / 2) := by
  have hsq := holder_L2_L6_to_L3_squared μ hu
  -- Take square roots of both sides via `ENNReal.rpow_le_rpow` at exponent 1/2.
  have hroot :
      ((eLpNorm u 3 μ) ^ 2) ^ ((1 : ℝ) / 2)
        ≤ (eLpNorm u 2 μ * eLpNorm u 6 μ) ^ ((1 : ℝ) / 2) := by
    exact ENNReal.rpow_le_rpow hsq (by norm_num)
  -- LHS simplifies to `eLpNorm u 3 μ` (a ≥ 0 in `ℝ≥0∞`).
  have hLHS : ((eLpNorm u 3 μ) ^ 2) ^ ((1 : ℝ) / 2)
      = eLpNorm u 3 μ := by
    rw [show ((eLpNorm u 3 μ) ^ 2) = (eLpNorm u 3 μ) ^ (2 : ℝ) from by
        rw [← ENNReal.rpow_natCast]; norm_num,
        ← ENNReal.rpow_mul]
    norm_num
  -- RHS distributes the 1/2-power over the product.
  have hRHS : (eLpNorm u 2 μ * eLpNorm u 6 μ) ^ ((1 : ℝ) / 2)
      = (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
          * (eLpNorm u 6 μ) ^ ((1 : ℝ) / 2) := by
    exact ENNReal.mul_rpow_of_nonneg _ _ (by norm_num : (0 : ℝ) ≤ 1 / 2)
  rw [hLHS, hRHS] at hroot
  exact hroot

/-! ## §3.  Composition: the Galerkin borderline bound

  `‖u‖_{L³} ≤ C^{1/2} · ‖u‖_{L²}^{1/2} · ‖∇u‖_{L²}^{1/2}`,

with `C := C_sobolev_H1_L6 μ`. This is the time-integrated `L³_x`
bound that drops out of `M_kin` (`L²_x` energy bound) and `M_ens`
(`L²_x` enstrophy = `H¹_x` bound) for the Galerkin construction. -/

/-- **Sobolev + Hölder composed.**

For `u : E3 → ℝ` continuously differentiable with compact support,

  `‖u‖_{L³} ≤ C^{1/2} · ‖u‖_{L²}^{1/2} · ‖∇u‖_{L²}^{1/2}`,

where `C := C_sobolev_H1_L6 μ` is the Mathlib Sobolev constant.

This is the Galerkin borderline bound: with kinetic-energy bound
`M_kin ≥ ‖u‖_{L²}^2` and enstrophy bound
`M_ens ≥ ∫ ‖∇u‖_{L²}^2 dt`, one obtains a TIME-INTEGRATED `L³_x`
bound on `u`. The pointwise-in-`t` essential-supremum bound (the L³
endpoint of ESS) is NOT recoverable from this inequality alone — it
requires Clay-equivalent input. -/
theorem sobolev_holder_L3_bound
    (μ : Measure E3) [μ.IsAddHaarMeasure]
    {u : E3 → ℝ} (hu : ContDiff ℝ 1 u) (h2u : HasCompactSupport u) :
    eLpNorm u 3 μ
      ≤ ((C_sobolev_H1_L6 μ : ℝ≥0∞)) ^ ((1 : ℝ) / 2)
        * (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
        * (eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2) := by
  have hu_meas : AEStronglyMeasurable u μ := hu.continuous.aestronglyMeasurable
  have hHolder := holder_L2_L6_to_L3 μ hu_meas
  have hSobolev := H1_into_L6_R3 μ hu h2u
  -- raise Sobolev inequality to the 1/2 power
  have hSobolev_root :
      (eLpNorm u 6 μ) ^ ((1 : ℝ) / 2)
        ≤ ((C_sobolev_H1_L6 μ : ℝ≥0∞) * eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2) :=
    ENNReal.rpow_le_rpow hSobolev (by norm_num)
  -- distribute the 1/2-power over the product
  have hRHS_split :
      ((C_sobolev_H1_L6 μ : ℝ≥0∞) * eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2)
        = ((C_sobolev_H1_L6 μ : ℝ≥0∞)) ^ ((1 : ℝ) / 2)
            * (eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2) :=
    ENNReal.mul_rpow_of_nonneg _ _ (by norm_num : (0 : ℝ) ≤ 1 / 2)
  rw [hRHS_split] at hSobolev_root
  -- chain Hölder ≤ ⋯ ≤ Sobolev
  calc eLpNorm u 3 μ
      ≤ (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
          * (eLpNorm u 6 μ) ^ ((1 : ℝ) / 2) := hHolder
    _ ≤ (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
          * (((C_sobolev_H1_L6 μ : ℝ≥0∞)) ^ ((1 : ℝ) / 2)
              * (eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2)) := by
        gcongr
    _ = ((C_sobolev_H1_L6 μ : ℝ≥0∞)) ^ ((1 : ℝ) / 2)
          * (eLpNorm u 2 μ) ^ ((1 : ℝ) / 2)
          * (eLpNorm (fderiv ℝ u) 2 μ) ^ ((1 : ℝ) / 2) := by ring

/-! ## §4.  Wire-in for `ns_trackb_ess_l3_endpoint.lean`

The brute-force ESS attempt
`attempted_ess_l3_bound_for_leray_hopf` ships five `sorry`s. This
file's `sobolev_holder_L3_bound` discharges TWO of them:

* `sorry_sobolev_embedding_H1_into_L6_R3` (void 1) — closed by
  `H1_into_L6_R3` above.

* `sorry_holder_L2_L6_to_L3` (void 2) — closed by
  `holder_L2_L6_to_L3` above.

The remaining three voids — `sorry_pointwise_in_time_L3_bound_for_uInf`,
`sorry_weak_lower_semicontinuity_of_L3_under_galerkin_limit`, and
`sorry_uniform_in_n_L3_bound_for_galerkin_truncations` — sit at the
borderline scaling-critical exponent and remain Clay-equivalent. They
are NOT closed here.

Downstream consumers (the Galerkin existence file and the ESS
endpoint file) can `import` this file and call
`sobolev_holder_L3_bound` to obtain the time-integrated `L³_x` bound
from `M_kin` and `M_ens`. -/

end

end ZtareProofs.NS.SobolevHolder
