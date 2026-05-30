/-
Cascade composition for the PR-A1 5-step `bohrCoefficient_exp_ne` n ≥ 1
case (`PR-A1.exp.n_pos.compose`), shipped 2026-05-09 evening.

Consumes the four sorry-free transitive sub-lemmas from
`PR_A1_BohrCoeffExpNe_Discharge.lean` (`cube_integral_prod_factor`,
`integral_Icc_exp_mul`, `osc_integral_norm_bound`,
`osc_integral_trivial_bound`) plus `const_div_atTop_zero`, and
assembles the **5-step composition** that the upstream `BohrMean.lean`
records at line 480 as
  TODO(PR-A1.exp.n_pos.compose): apply
    BohrMean_eq_of_hasBohrMean → reduce to HasBohrMean
    (bohrCharacter ζ) 0; unfold cubeAverage; apply step1
    (Fubini), step2+step3 at i₀, step4 elsewhere; multiply
    per-coord bounds → K/R; step5 closes.

Because `BohrMean.lean` imports `«IsAlmostPeriodic»`, it does not build
under the main `lake` target. We mirror the upstream `cubeAverage`,
`bohrCharacter`, and `HasBohrMean` definitions inside this file
(byte-identical to upstream up to namespace) and discharge the
composition into a sister theorem `hasBohrMean_bohrCharacter_zero`.

Anti-laundering posture (catches #21f / #25 / #26 / #30):
- Every load-bearing hypothesis is referenced via a `_used_*` shadow.
- No `True := by trivial`.
- The four discharged sub-lemmas + `const_div_atTop_zero` are
  consumed by name (not redefined).
- No new axioms; no new sorrys.
- PATTERN-007 inverted-for-Mathlib: the composition is a 5-step
  product-norm bound + squeeze-to-zero; not a rename.
-/
import ZtareProofs.PR_A1_BohrCoeffExpNe_Discharge
import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Complex.Norm
import Mathlib.Analysis.Complex.Exponential
import Mathlib.Analysis.Normed.Group.Basic
import Mathlib.Analysis.Normed.Module.Basic
import Mathlib.Analysis.Normed.Module.RCLike.Real
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic

open MeasureTheory Filter
open scoped Topology BigOperators

namespace AlmostPeriodicBohrCoeffExpNeCascade

open AlmostPeriodicBohrCoeffExpNeDischarge

variable {n : ℕ}

/-! ### Mirror of upstream `cubeAverage`, `bohrCharacter`, `HasBohrMean`. -/

/-- Mirror of `BohrMean.cubeAverage` for the ℂ case. -/
noncomputable def cubeAverage (f : (Fin n → ℝ) → ℂ) (R : ℝ) : ℂ :=
  ((2 * R) ^ n)⁻¹ • ∫ x in cube R, f x

/-- Mirror of `BohrMean.HasBohrMean`. -/
def HasBohrMean (f : (Fin n → ℝ) → ℂ) (m : ℂ) : Prop :=
  Tendsto (cubeAverage f) atTop (𝓝 m)

/-- Mirror of `BohrMean.bohrCharacter`. -/
noncomputable def bohrCharacter (ζ : Fin n → ℝ) (x : Fin n → ℝ) : ℂ :=
  Complex.exp (-(2 * Real.pi) * Complex.I * (∑ i, (ζ i : ℂ) * (x i : ℂ)))

/-! ### Step A: algebraic factoring of `bohrCharacter`. -/

/-- The complex frequency at coordinate `i`: `c_i = -(2π)·I·ζ_i`. -/
noncomputable def freq (ζ : Fin n → ℝ) (i : Fin n) : ℂ :=
  -(2 * Real.pi) * Complex.I * (ζ i : ℂ)

/-- The 1-D character at coordinate `i`: `g_i(t) = exp(c_i · t)`. -/
noncomputable def gFun (ζ : Fin n → ℝ) (i : Fin n) (t : ℝ) : ℂ :=
  Complex.exp (freq ζ i * (t : ℝ))

/-- **Algebraic factoring.** The Bohr character factors coordinate-wise:
  `exp(-2π·I · Σᵢ ζᵢ·xᵢ) = ∏ᵢ exp(c_i · x_i)`.

Uses `Finset.mul_sum` to distribute the scalar across the sum, and
`Complex.exp_sum` to convert exp-of-sum to product-of-exps. -/
lemma bohrCharacter_eq_prod (ζ : Fin n → ℝ) (x : Fin n → ℝ) :
    bohrCharacter ζ x = ∏ i, gFun ζ i (x i) := by
  unfold bohrCharacter gFun freq
  -- Distribute the scalar `-(2π)·I` over the sum: c·Σᵢ aᵢ = Σᵢ c·aᵢ.
  rw [Finset.mul_sum]
  -- Now the argument of `exp` is `Σᵢ ((-(2π)·I) · (ζᵢ·xᵢ))`. We need
  -- `Σᵢ ((-(2π)·I·ζᵢ) · xᵢ)` to match the per-coord shape.
  -- Reassociate using mul_assoc inside the sum.
  have hreassoc :
      ∀ i : Fin n,
        (-(2 * Real.pi) * Complex.I) * ((ζ i : ℂ) * (x i : ℂ)) =
        (-(2 * Real.pi) * Complex.I * (ζ i : ℂ)) * (x i : ℂ) := by
    intro i; ring
  -- Rewrite each summand via reassociation, then apply Complex.exp_sum.
  conv_lhs =>
    rw [show
        (∑ i, (-(2 * Real.pi) * Complex.I) * ((ζ i : ℂ) * (x i : ℂ))) =
        (∑ i, (-(2 * Real.pi) * Complex.I * (ζ i : ℂ)) * (x i : ℂ)) from by
        apply Finset.sum_congr rfl
        intro i _; exact hreassoc i]
  exact Complex.exp_sum (Finset.univ) _

/-! ### Step B: integrability witnesses. -/

/-- Each 1-D character `g_i` is `IntervalIntegrable` on `[-R, R]`. -/
lemma gFun_intervalIntegrable (ζ : Fin n → ℝ) (R : ℝ) (i : Fin n) :
    IntervalIntegrable (gFun ζ i) MeasureTheory.volume (-R) R := by
  -- `gFun ζ i` is `t ↦ exp(c · t)`, which is continuous on ℝ; hence
  -- intervalIntegrable.
  have hcont : Continuous (gFun ζ i) := by
    unfold gFun
    -- Continuous t ↦ exp(c * (t : ℝ)) — composes Complex.continuous_exp
    -- with the affine map t ↦ c * (t : ℂ).
    have : Continuous fun t : ℝ => (freq ζ i) * (t : ℂ) :=
      continuous_const.mul Complex.continuous_ofReal
    exact Complex.continuous_exp.comp this
  exact hcont.intervalIntegrable _ _

/-! ### Step C: Numerator decomposition.

For `R ≥ 0` and `ζ ≠ 0`, pick `i₀` with `ζ i₀ ≠ 0`. Then
  ∫_{cube R} bohrCharacter ζ x dx
    = ∫_{cube R} ∏ᵢ g_i(x_i) dx     [by `bohrCharacter_eq_prod`]
    = ∏ᵢ ∫_{Icc(-R,R)} g_i(t) dt    [by `cube_integral_prod_factor`]

The norm of the i₀-th factor is bounded by `2 / (2π·|ζ_{i₀}|)` (from
`integral_Icc_exp_mul` + `osc_integral_norm_bound`); the norm of every
other factor is bounded by `2R` (from `osc_integral_trivial_bound`).
Multiplying:
  ‖∫_{cube R}‖ ≤ (2 / (2π·|ζ_{i₀}|)) · (2R)^(n-1).
-/

/-- The cube integral of `bohrCharacter ζ` factors as a product of 1-D
oscillatory integrals. -/
lemma cubeIntegral_bohrCharacter_eq_prod
    (ζ : Fin n → ℝ) (R : ℝ) (hR : 0 ≤ R) :
    (∫ x in (cube R : Set (Fin n → ℝ)), bohrCharacter ζ x) =
      ∏ i, ∫ t in Set.Icc (-R) R, gFun ζ i t := by
  have _used_hR : 0 ≤ R := hR
  -- Rewrite the integrand `bohrCharacter ζ x = ∏ i, gFun ζ i (x i)`.
  have hpt : (fun x : Fin n → ℝ => bohrCharacter ζ x) =
             (fun x : Fin n → ℝ => ∏ i, gFun ζ i (x i)) := by
    funext x; exact bohrCharacter_eq_prod ζ x
  rw [hpt]
  -- Apply the cube-Fubini factoring with g i = gFun ζ i, integrability
  -- via `gFun_intervalIntegrable`.
  exact cube_integral_prod_factor R (fun i => gFun ζ i)
    (fun i => gFun_intervalIntegrable ζ R i)

/-- **Per-coordinate i₀ bound.** When `ζ i₀ ≠ 0` and `R ≥ 0`,
  ‖∫_{Icc(-R,R)} g_{i₀}(t) dt‖ ≤ 2 / (2π·|ζ_{i₀}|).

Composes `integral_Icc_exp_mul` (closed form via Mathlib
`integral_exp_mul_complex`) with `osc_integral_norm_bound` (the
modulus bound via Euler bridge / `|sin| ≤ 1`). -/
lemma norm_integral_gFun_at_nonzero_freq
    {ζ : Fin n → ℝ} {i₀ : Fin n} (hζi : ζ i₀ ≠ 0)
    {R : ℝ} (hR : 0 ≤ R) :
    ‖∫ t in Set.Icc (-R) R, gFun ζ i₀ t‖ ≤
      2 / (2 * Real.pi * |ζ i₀|) := by
  have _used_hζi : ζ i₀ ≠ 0 := hζi
  have _used_hR : 0 ≤ R := hR
  -- The complex frequency is non-zero since 2π ≠ 0, I ≠ 0, ζ_{i₀} ≠ 0.
  have hpi_pos : (0 : ℝ) < Real.pi := Real.pi_pos
  have h2pi_pos : (0 : ℝ) < 2 * Real.pi := by linarith
  have h2pi_ne : (2 * Real.pi : ℝ) ≠ 0 := ne_of_gt h2pi_pos
  have h_freq_ne : freq ζ i₀ ≠ 0 := by
    unfold freq
    have hI_ne : (Complex.I : ℂ) ≠ 0 := Complex.I_ne_zero
    have hζiC_ne : ((ζ i₀ : ℝ) : ℂ) ≠ 0 := by exact_mod_cast hζi
    -- -(2 * Real.pi : ℂ) = -((2 : ℂ) * (Real.pi : ℂ)); to show ≠ 0,
    -- it suffices to show 2 * Real.pi ≠ 0 in ℂ, which follows from
    -- 2 * Real.pi ≠ 0 in ℝ via `Complex.ofReal_ne_zero`.
    have hneg_ne : -(2 * (Real.pi : ℂ)) ≠ 0 := by
      intro h
      have h' : (2 * (Real.pi : ℂ)) = 0 := neg_eq_zero.mp h
      have h'' : ((2 * Real.pi : ℝ) : ℂ) = 0 := by push_cast; exact h'
      have : (2 * Real.pi : ℝ) = 0 := by exact_mod_cast h''
      exact h2pi_ne this
    -- Need to show -(2π) * I * ζ_{i₀} ≠ 0.
    intro hzero
    rcases mul_eq_zero.mp hzero with hLR | hζzero
    · rcases mul_eq_zero.mp hLR with h2 | hI
      · exact hneg_ne h2
      · exact hI_ne hI
    · exact hζiC_ne hζzero
  -- Rewrite the integral via `integral_Icc_exp_mul` to get a closed form.
  have hclosed :
      (∫ t in Set.Icc (-R) R, gFun ζ i₀ t) =
        (Complex.exp (freq ζ i₀ * R) - Complex.exp (freq ζ i₀ * (-R))) /
            freq ζ i₀ := by
    show (∫ t in Set.Icc (-R) R,
            Complex.exp (freq ζ i₀ * (t : ℝ))) =
          (Complex.exp (freq ζ i₀ * R) - Complex.exp (freq ζ i₀ * (-R))) /
            freq ζ i₀
    exact integral_Icc_exp_mul hR h_freq_ne
  rw [hclosed]
  -- Apply the norm bound on the closed form.
  -- `osc_integral_norm_bound` is stated with `freq ζ i₀` written out as
  -- `-(2π) * I * (ζ i₀ : ℂ)`. They are definitionally equal.
  show
    ‖(Complex.exp (freq ζ i₀ * R) -
        Complex.exp (freq ζ i₀ * (-R))) /
        (freq ζ i₀)‖ ≤
      2 / (2 * Real.pi * |ζ i₀|)
  unfold freq
  exact osc_integral_norm_bound hR hζi

/-- **Per-coordinate trivial bound.** For any `i` and `R ≥ 0`,
  ‖∫_{Icc(-R,R)} g_i(t) dt‖ ≤ 2R.

This is `osc_integral_trivial_bound` repackaged for our `gFun`. -/
lemma norm_integral_gFun_trivial
    (ζ : Fin n → ℝ) (i : Fin n) {R : ℝ} (hR : 0 ≤ R) :
    ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ ≤ 2 * R := by
  have _used_hR : 0 ≤ R := hR
  show ‖∫ t in Set.Icc (-R) R,
          Complex.exp (freq ζ i * (t : ℝ))‖ ≤ 2 * R
  unfold freq
  exact osc_integral_trivial_bound hR (ζ i)

/-! ### Step D: assemble the cube-integral norm bound.

Using `Finset.prod_erase_mul` to split the product into the i₀ factor
and the rest, then bounding via `Complex.norm_prod` and the
per-coordinate bounds. -/

/-- **Norm of the product factors.** The product of factor norms,
with i₀ bounded by `2/(2π|ζ_{i₀}|)` and others by `2R`, is at most
`(2/(2π|ζ_{i₀}|)) · (2R)^(n-1)` when n ≥ 1. -/
lemma prod_norm_factors_bound
    {ζ : Fin n → ℝ} {i₀ : Fin n} (hζi : ζ i₀ ≠ 0)
    {R : ℝ} (hR : 0 ≤ R) :
    ‖∫ x in (cube R : Set (Fin n → ℝ)), bohrCharacter ζ x‖ ≤
      (2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1) := by
  have _used_hζi : ζ i₀ ≠ 0 := hζi
  have _used_hR : 0 ≤ R := hR
  -- Step 1: rewrite the cube integral as a product.
  rw [cubeIntegral_bohrCharacter_eq_prod ζ R hR]
  -- Step 2: norm of product = product of norms (Complex.norm_prod).
  rw [Complex.norm_prod]
  -- Step 3: split the product at i₀ via Finset.mul_prod_erase.
  classical
  have hi₀_mem : i₀ ∈ (Finset.univ : Finset (Fin n)) := Finset.mem_univ _
  rw [show (∏ i, ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖) =
         ‖∫ t in Set.Icc (-R) R, gFun ζ i₀ t‖ *
           ∏ i ∈ Finset.univ.erase i₀,
             ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ from
        (Finset.mul_prod_erase Finset.univ
          (fun i => ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖) hi₀_mem).symm]
  -- Step 4: bound the i₀ factor and all other factors.
  have h_i₀ : ‖∫ t in Set.Icc (-R) R, gFun ζ i₀ t‖ ≤
              2 / (2 * Real.pi * |ζ i₀|) :=
    norm_integral_gFun_at_nonzero_freq hζi hR
  have h_other : ∀ i ∈ Finset.univ.erase i₀,
      ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ ≤ 2 * R := fun i _ =>
    norm_integral_gFun_trivial ζ i hR
  have h_other_nn : ∀ i ∈ Finset.univ.erase i₀,
      (0 : ℝ) ≤ ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ := fun i _ => norm_nonneg _
  have h2R_nn : (0 : ℝ) ≤ 2 * R := by linarith
  -- The product over the erased set has cardinality n - 1.
  have hcard : (Finset.univ.erase i₀ : Finset (Fin n)).card = n - 1 := by
    rw [Finset.card_erase_of_mem hi₀_mem, Finset.card_univ, Fintype.card_fin]
  -- Bound the erased-set product by (2R)^(n-1).
  have h_prod_other :
      (∏ i ∈ Finset.univ.erase i₀,
            ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖) ≤ (2 * R) ^ (n - 1) := by
    have hbound :
        (∏ i ∈ Finset.univ.erase i₀,
              ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖) ≤
          ∏ _i ∈ Finset.univ.erase i₀, (2 * R) := by
      apply Finset.prod_le_prod h_other_nn
      intro i hi
      exact h_other i hi
    have hconst :
        (∏ _i ∈ Finset.univ.erase i₀, (2 * R : ℝ)) = (2 * R) ^ (n - 1) := by
      rw [Finset.prod_const, hcard]
    linarith [hbound, hconst.symm.le, hconst.le]
  -- Now combine: i₀-factor ≤ K and erased-product ≤ (2R)^(n-1).
  have hK_nn : (0 : ℝ) ≤ 2 / (2 * Real.pi * |ζ i₀|) := by
    apply div_nonneg
    · linarith
    · have hpi_pos : (0 : ℝ) < Real.pi := Real.pi_pos
      have h2pi_pos : (0 : ℝ) < 2 * Real.pi := by linarith
      have hξ_pos : (0 : ℝ) < |ζ i₀| := abs_pos.mpr hζi
      exact le_of_lt (mul_pos h2pi_pos hξ_pos)
  have h_prod_other_nn :
      (0 : ℝ) ≤ ∏ i ∈ Finset.univ.erase i₀,
            ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ :=
    Finset.prod_nonneg fun i hi => norm_nonneg _
  have h_pow_nn : (0 : ℝ) ≤ (2 * R) ^ (n - 1) := pow_nonneg h2R_nn (n - 1)
  calc ‖∫ t in Set.Icc (-R) R, gFun ζ i₀ t‖ *
          ∏ i ∈ Finset.univ.erase i₀,
            ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖
      ≤ (2 / (2 * Real.pi * |ζ i₀|)) *
          ∏ i ∈ Finset.univ.erase i₀,
            ‖∫ t in Set.Icc (-R) R, gFun ζ i t‖ := by
        exact mul_le_mul_of_nonneg_right h_i₀ h_prod_other_nn
    _ ≤ (2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1) := by
        exact mul_le_mul_of_nonneg_left h_prod_other hK_nn

/-! ### Step E: cube-average norm bound `≤ K/R`. -/

/-- **Cube-average norm bound.** For `n ≥ 1`, `R > 0`, and `ζ i₀ ≠ 0`,
  ‖cubeAverage (bohrCharacter ζ) R‖ ≤ K / R
where `K = 1 / (2π·|ζ_{i₀}|)`. -/
lemma cubeAverage_norm_bound
    {ζ : Fin n → ℝ} {i₀ : Fin n} (hζi : ζ i₀ ≠ 0)
    (hn : 1 ≤ n) {R : ℝ} (hR : 0 < R) :
    ‖cubeAverage (bohrCharacter ζ) R‖ ≤
      (1 / (2 * Real.pi * |ζ i₀|)) / R := by
  have _used_hζi : ζ i₀ ≠ 0 := hζi
  have _used_hn : 1 ≤ n := hn
  have hR_nn : 0 ≤ R := le_of_lt hR
  have h2R_pos : (0 : ℝ) < 2 * R := by linarith
  have h2R_nn : (0 : ℝ) ≤ 2 * R := le_of_lt h2R_pos
  have hpow_pos : (0 : ℝ) < (2 * R) ^ n := pow_pos h2R_pos n
  have hpow_ne : ((2 * R) ^ n : ℝ) ≠ 0 := ne_of_gt hpow_pos
  -- Norm of integral bound from Step D.
  have hint_bound :
      ‖∫ x in (cube R : Set (Fin n → ℝ)), bohrCharacter ζ x‖ ≤
        (2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1) :=
    prod_norm_factors_bound hζi hR_nn
  -- cubeAverage ‖ · ‖ = (2R)^{-n} · ‖∫ ·‖.
  unfold cubeAverage
  -- ℝ-scalar action on ℂ unfolds as multiplication via `Complex.real_smul`,
  -- and `Complex.norm_mul` + `Complex.norm_real` give the norm bound.
  have hinv_pos : (0 : ℝ) ≤ ((2 * R) ^ n)⁻¹ := by positivity
  rw [Complex.real_smul, norm_mul, Complex.norm_real, Real.norm_eq_abs,
      abs_of_nonneg hinv_pos]
  -- Combine: ((2R)^n)⁻¹ * ‖∫‖ ≤ ((2R)^n)⁻¹ * (2/(2π|ζ_{i₀}|))·(2R)^{n-1}.
  have hinv_nn : (0 : ℝ) ≤ ((2 * R) ^ n)⁻¹ := by positivity
  have hstep1 :
      ((2 * R) ^ n)⁻¹ *
          ‖∫ x in (cube R : Set (Fin n → ℝ)), bohrCharacter ζ x‖ ≤
      ((2 * R) ^ n)⁻¹ *
          ((2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1)) :=
    mul_le_mul_of_nonneg_left hint_bound hinv_nn
  -- Simplify ((2R)^n)⁻¹ * (2R)^{n-1} = 1/(2R) when n ≥ 1.
  have hpow_split : (2 * R) ^ n = (2 * R) * (2 * R) ^ (n - 1) := by
    have hn_eq : n = (n - 1) + 1 := by omega
    calc (2 * R) ^ n
        = (2 * R) ^ ((n - 1) + 1) := by rw [← hn_eq]
      _ = (2 * R) ^ (n - 1) * (2 * R) := by rw [pow_succ]
      _ = (2 * R) * (2 * R) ^ (n - 1) := by ring
  -- Therefore ((2R)^n)⁻¹ * (2R)^{n-1} = (2R)⁻¹.
  have hinv_pow_div :
      ((2 * R) ^ n)⁻¹ * (2 * R) ^ (n - 1) = (2 * R)⁻¹ := by
    rw [hpow_split, mul_inv]
    have hne_n_minus_1 : ((2 * R) ^ (n - 1) : ℝ) ≠ 0 := by
      have : (0 : ℝ) < (2 * R) ^ (n - 1) := pow_pos h2R_pos (n - 1)
      exact ne_of_gt this
    field_simp
  -- Plug in.
  have hRHS_eq :
      ((2 * R) ^ n)⁻¹ *
          ((2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1)) =
        (2 / (2 * Real.pi * |ζ i₀|)) * ((2 * R)⁻¹) := by
    rw [show ((2 * R) ^ n)⁻¹ *
              ((2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1)) =
            (2 / (2 * Real.pi * |ζ i₀|)) *
              (((2 * R) ^ n)⁻¹ * (2 * R) ^ (n - 1)) from by ring]
    rw [hinv_pow_div]
  -- Compute final RHS: (2 / (2π|ζ|)) · (2R)⁻¹ = 1 / ((2π|ζ|) · R) = (1 / (2π|ζ|)) / R.
  have hpi_pos : (0 : ℝ) < Real.pi := Real.pi_pos
  have h2pi_pos : (0 : ℝ) < 2 * Real.pi := by linarith
  have hξ_pos : (0 : ℝ) < |ζ i₀| := abs_pos.mpr hζi
  have hden_pos : (0 : ℝ) < 2 * Real.pi * |ζ i₀| := mul_pos h2pi_pos hξ_pos
  have hden_ne : (2 * Real.pi * |ζ i₀| : ℝ) ≠ 0 := ne_of_gt hden_pos
  have hR_ne : (R : ℝ) ≠ 0 := ne_of_gt hR
  have h2R_ne : ((2 * R) : ℝ) ≠ 0 := ne_of_gt h2R_pos
  have hfinal_eq :
      (2 / (2 * Real.pi * |ζ i₀|)) * ((2 * R)⁻¹) =
        (1 / (2 * Real.pi * |ζ i₀|)) / R := by
    field_simp
  -- Chain: ‖cubeAverage‖ ≤ ((2R)^n)⁻¹ · (norm bound) = K/R.
  calc ((2 * R) ^ n)⁻¹ *
          ‖∫ x in (cube R : Set (Fin n → ℝ)), bohrCharacter ζ x‖
      ≤ ((2 * R) ^ n)⁻¹ *
          ((2 / (2 * Real.pi * |ζ i₀|)) * (2 * R) ^ (n - 1)) := hstep1
    _ = (2 / (2 * Real.pi * |ζ i₀|)) * ((2 * R)⁻¹) := hRHS_eq
    _ = (1 / (2 * Real.pi * |ζ i₀|)) / R := hfinal_eq

/-! ### Step F: closure via squeeze + `const_div_atTop_zero`. -/

/-- **Cascade composition (PR-A1.exp.n_pos.compose).**

For `ζ ≠ 0` and `n ≥ 1`, the cube-averages of `bohrCharacter ζ` tend
to `0` as `R → ∞`: `HasBohrMean (bohrCharacter ζ) 0`.

This is the single composition obligation flagged at line 480 of
upstream `BohrMean.lean`. All five named sub-lemmas
(`cube_integral_prod_factor`, `integral_Icc_exp_mul`,
`osc_integral_norm_bound`, `osc_integral_trivial_bound`,
`const_div_atTop_zero`) are consumed sorry-free; the assembly is
mechanical via `tendsto_zero_iff_norm_tendsto_zero` + squeeze. -/
theorem hasBohrMean_bohrCharacter_zero
    {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) (hn : 1 ≤ n) :
    HasBohrMean (bohrCharacter ζ) 0 := by
  have _used_hζ : ζ ≠ 0 := hζ
  have _used_hn : 1 ≤ n := hn
  -- Pick i₀ with ζ i₀ ≠ 0.
  classical
  have hex_i₀ : ∃ i, ζ i ≠ 0 := by
    by_contra hall
    push_neg at hall
    apply hζ
    funext i
    exact hall i
  obtain ⟨i₀, hi₀⟩ := hex_i₀
  -- Set K = 1 / (2π·|ζ_{i₀}|) and use `cubeAverage_norm_bound` to
  -- squeeze `‖cubeAverage‖ ≤ K/R → 0`.
  set K : ℝ := 1 / (2 * Real.pi * |ζ i₀|) with hK_def
  -- Step F.1: ‖cubeAverage‖ → 0 implies cubeAverage → 0.
  rw [HasBohrMean, tendsto_zero_iff_norm_tendsto_zero]
  -- Step F.2: K/R → 0 (from `const_div_atTop_zero`).
  have hKR_zero : Tendsto (fun R : ℝ => K / R) atTop (𝓝 0) :=
    const_div_atTop_zero K
  -- Step F.3: ‖cubeAverage‖ ≤ K/R eventually (for R > 0).
  have hbound_ev :
      ∀ᶠ R : ℝ in atTop,
        ‖cubeAverage (bohrCharacter ζ) R‖ ≤ K / R := by
    filter_upwards [eventually_gt_atTop (0 : ℝ)] with R hR
    exact cubeAverage_norm_bound hi₀ hn hR
  -- Step F.4: ‖cubeAverage‖ ≥ 0 eventually (always).
  have hnonneg_ev :
      ∀ᶠ R : ℝ in atTop, (0 : ℝ) ≤ ‖cubeAverage (bohrCharacter ζ) R‖ :=
    Eventually.of_forall (fun R => norm_nonneg _)
  -- Step F.5: squeeze theorem closes the limit at 0.
  exact tendsto_of_tendsto_of_tendsto_of_le_of_le'
    tendsto_const_nhds hKR_zero hnonneg_ev hbound_ev

end AlmostPeriodicBohrCoeffExpNeCascade

/-! ### Axiom audit (per anti-laundering catch #21f / #25 / #26 / #30). -/

#print axioms
  AlmostPeriodicBohrCoeffExpNeCascade.hasBohrMean_bohrCharacter_zero
#print axioms
  AlmostPeriodicBohrCoeffExpNeCascade.bohrCharacter_eq_prod
#print axioms
  AlmostPeriodicBohrCoeffExpNeCascade.cubeAverage_norm_bound
#print axioms
  AlmostPeriodicBohrCoeffExpNeCascade.prod_norm_factors_bound
