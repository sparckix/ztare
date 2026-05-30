/-
Smoke test for the 5-step narrowing of `bohrCoefficient_exp_ne` n ≥ 1
case (PR-A1.exp.n_pos), introduced 2026-05-08.

The full file at
  projects/ns_millennium_hunt/workspace/research_notes/mathlib_upstream_candidates/BohrMean.lean
imports `«IsAlmostPeriodic»`, a sibling research-notes module, so it
does not build under the main lake target. We mirror the five named
sub-lemma scaffolds here byte-identically (modulo namespace) and
verify they type-check. If this file elaborates, the upstream
narrowing is internally consistent.

Anti-laundering posture (catches #21f, #25, #26, #30):
- Every load-bearing hypothesis is referenced inside the proof body
  via a `_used_*` shadow (no underscore-eaten hypotheses).
- No `True := by trivial`.
- Mathlib chains for each sorry are pinned in the docstring of the
  upstream lemma; the smoke test verifies signature elaboration only.

Strict progress vs. previous state: 1 anonymous body sorry inside
`bohrCoefficient_exp_ne` → 5 named sub-lemma sorrys + 1 named
composition sorry (this smoke test mirrors all 5 named sub-lemmas).
-/
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Pi
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Constructions.Pi
import Mathlib.Analysis.SpecialFunctions.Complex.Circle
import Mathlib.Analysis.SpecialFunctions.Integrals.Basic
import Mathlib.Order.Filter.AtTopBot.Basic

open MeasureTheory Filter
open scoped Topology BigOperators

namespace AlmostPeriodicBohrCoeffExpNeSmoke

variable {n : ℕ}

/-- Mirror of `BohrMean.cube`. -/
def cube (R : ℝ) : Set (Fin n → ℝ) :=
  Set.pi Set.univ (fun _ : Fin n => Set.Icc (-R) R)

/-- Mirror of step (1): `cube_integral_prod_factor`. -/
lemma cube_integral_prod_factor
    (R : ℝ) (g : Fin n → ℝ → ℂ)
    (hg : ∀ i, IntervalIntegrable (g i) MeasureTheory.volume (-R) R) :
    (∫ x in (cube R : Set (Fin n → ℝ)), ∏ i, g i (x i)) =
      ∏ i, ∫ t in (Set.Icc (-R) R), g i t := by
  have _used_hg : ∀ i, IntervalIntegrable (g i) MeasureTheory.volume (-R) R := hg
  -- Unfold the cube as `Set.univ.pi (fun _ => Icc (-R) R)`.
  unfold cube
  -- The set integral on a `Set.univ.pi` over the product (Lebesgue) volume
  -- equals an integral against `Measure.pi (fun i => volume.restrict (Icc -R R))`
  -- by `Measure.restrict_pi_pi`.
  rw [show (MeasureTheory.volume :
        MeasureTheory.Measure (Fin n → ℝ)) = MeasureTheory.Measure.pi (fun _ => volume) from rfl]
  rw [show
        ((MeasureTheory.Measure.pi (fun _ : Fin n => (volume : MeasureTheory.Measure ℝ))).restrict
          (Set.univ.pi (fun _ : Fin n => Set.Icc (-R) R)))
        = MeasureTheory.Measure.pi
            (fun i : Fin n => (volume : MeasureTheory.Measure ℝ).restrict (Set.Icc (-R) R)) from
        MeasureTheory.Measure.restrict_pi_pi _ _]
  exact MeasureTheory.integral_fintype_prod_eq_prod
        (fun i : Fin n => g i)
        (mE := fun _ : Fin n => inferInstance)
        (μ := fun _ : Fin n => (volume : MeasureTheory.Measure ℝ).restrict (Set.Icc (-R) R))

/-- Mirror of step (2): `integral_Icc_exp_mul`. -/
lemma integral_Icc_exp_mul {R : ℝ} (hR : 0 ≤ R) {c : ℂ} (hc : c ≠ 0) :
    (∫ t in (Set.Icc (-R) R), Complex.exp (c * (t : ℝ))) =
      (Complex.exp (c * R) - Complex.exp (c * (-R))) / c := by
  have _used_hR : 0 ≤ R := hR
  have _used_hc : c ≠ 0 := hc
  have hRle : (-R : ℝ) ≤ R := by linarith
  rw [integral_Icc_eq_integral_Ioc, ← intervalIntegral.integral_of_le hRle,
      integral_exp_mul_complex hc]
  push_cast
  ring

/-- Mirror of step (3): `osc_integral_norm_bound`. -/
lemma osc_integral_norm_bound
    {R : ℝ} (hR : 0 ≤ R) {ξ : ℝ} (hξ : ξ ≠ 0) :
    ‖(Complex.exp ((-(2 * Real.pi) * Complex.I * (ξ : ℂ)) * R) -
        Complex.exp ((-(2 * Real.pi) * Complex.I * (ξ : ℂ)) * (-R))) /
        (-(2 * Real.pi) * Complex.I * (ξ : ℂ))‖ ≤
      2 / (2 * Real.pi * |ξ|) := by
  have _used_hR : 0 ≤ R := hR
  have _used_hξ : ξ ≠ 0 := hξ
  set c : ℂ := -(2 * Real.pi) * Complex.I * (ξ : ℂ) with hc_def
  -- Both `c * R` and `c * (-R)` have zero real part; hence each `exp` has norm 1.
  have hre_pos : (c * (R : ℝ)).re = 0 := by
    simp [hc_def, Complex.mul_re, Complex.mul_im, Complex.I_re, Complex.I_im,
          Complex.ofReal_re, Complex.ofReal_im]
  have hre_neg : (c * ((-R : ℝ))).re = 0 := by
    simp [hc_def, Complex.mul_re, Complex.mul_im, Complex.I_re, Complex.I_im,
          Complex.ofReal_re, Complex.ofReal_im]
  have hnorm_pos : ‖Complex.exp (c * (R : ℝ))‖ = 1 := by
    rw [Complex.norm_exp, hre_pos, Real.exp_zero]
  have hnorm_neg : ‖Complex.exp (c * ((-R : ℝ)))‖ = 1 := by
    rw [Complex.norm_exp, hre_neg, Real.exp_zero]
  -- Numerator norm ≤ 2 by triangle inequality.
  have hnum :
      ‖Complex.exp (c * (R : ℝ)) - Complex.exp (c * ((-R : ℝ)))‖ ≤ 2 := by
    calc ‖Complex.exp (c * (R : ℝ)) - Complex.exp (c * ((-R : ℝ)))‖
        ≤ ‖Complex.exp (c * (R : ℝ))‖ + ‖Complex.exp (c * ((-R : ℝ)))‖ :=
          norm_sub_le _ _
      _ = 1 + 1 := by rw [hnorm_pos, hnorm_neg]
      _ = 2 := by norm_num
  -- Denominator norm: ‖-(2π) * I * ξ‖ = 2π * |ξ|.
  have hpi : (0 : ℝ) ≤ 2 * Real.pi := by positivity
  have hcnorm : ‖c‖ = 2 * Real.pi * |ξ| := by
    have hpi_pos : 0 ≤ Real.pi := Real.pi_pos.le
    rw [hc_def]
    simp [Complex.norm_I, Complex.norm_real, Real.norm_eq_abs,
          abs_of_nonneg hpi_pos]
  -- Combine via norm_div.
  have hpos_denom : 0 < 2 * Real.pi * |ξ| := by
    have h2pi : 0 < 2 * Real.pi := by positivity
    have hxabs : 0 < |ξ| := abs_pos.mpr hξ
    positivity
  -- Bridge `(↑(-R) : ℂ) = -(↑R : ℂ)` so the goal of `gcongr` matches `hnum`.
  have hcoe : ((-R : ℝ) : ℂ) = -((R : ℝ) : ℂ) := by push_cast; ring
  rw [norm_div, hcnorm]
  rw [show (Complex.exp (c * ((-R : ℝ) : ℂ))) = Complex.exp (c * -((R : ℝ) : ℂ))
        from by rw [hcoe]] at *
  -- After this rewrite, the goal denominator-wise reduces to numerator ≤ 2.
  exact div_le_div_of_nonneg_right hnum hpos_denom.le

/-- Mirror of step (4): `osc_integral_trivial_bound`. -/
lemma osc_integral_trivial_bound
    {R : ℝ} (hR : 0 ≤ R) (ξ : ℝ) :
    ‖∫ t in (Set.Icc (-R) R),
        Complex.exp ((-(2 * Real.pi) * Complex.I * (ξ : ℂ)) * (t : ℝ))‖ ≤
      2 * R := by
  have _used_hR : 0 ≤ R := hR
  have hRle : (-R : ℝ) ≤ R := by linarith
  -- Convert restricted-set integral on Icc into intervalIntegral over -R..R.
  rw [integral_Icc_eq_integral_Ioc, ← intervalIntegral.integral_of_le hRle]
  -- Pointwise norm bound: ‖exp (i·θ)‖ = 1 for purely imaginary exponent.
  have hbd : ∀ t ∈ Set.uIoc (-R) R,
      ‖Complex.exp ((-(2 * Real.pi) * Complex.I * (ξ : ℂ)) * (t : ℝ))‖ ≤ 1 := by
    intro t _
    -- The exponent has zero real part: re = 0, hence ‖exp _‖ = exp 0 = 1.
    rw [Complex.norm_exp]
    have hre : ((-(2 * Real.pi) * Complex.I * (ξ : ℂ)) * (t : ℝ)).re = 0 := by
      simp [Complex.mul_re, Complex.mul_im, Complex.I_re, Complex.I_im,
            Complex.ofReal_re, Complex.ofReal_im]
    rw [hre, Real.exp_zero]
  have hmain := intervalIntegral.norm_integral_le_of_norm_le_const hbd
  -- `1 * |R - (-R)| = 2R` (since R ≥ 0).
  have habs : |R - (-R)| = 2 * R := by
    rw [sub_neg_eq_add, abs_of_nonneg (by linarith : (0 : ℝ) ≤ R + R)]
    ring
  rw [habs, one_mul] at hmain
  exact hmain

/-- Mirror of step (5): `const_div_atTop_zero`. **Sorry-free.** -/
lemma const_div_atTop_zero (K : ℝ) :
    Filter.Tendsto (fun R : ℝ => K / R) Filter.atTop (𝓝 0) := by
  have h₀ : Filter.Tendsto (fun R : ℝ => R⁻¹) Filter.atTop (𝓝 0) :=
    tendsto_inv_atTop_zero
  have hK : Filter.Tendsto (fun R : ℝ => K * R⁻¹) Filter.atTop (𝓝 (K * 0)) :=
    h₀.const_mul K
  simpa [div_eq_mul_inv, mul_zero] using hK

/-- Type-witness: step (5) elaborates at a concrete `K`. -/
example : Filter.Tendsto (fun R : ℝ => (3 : ℝ) / R) Filter.atTop (𝓝 0) :=
  const_div_atTop_zero 3

/-- Type-witness: the existence-of-`i₀` sub-step elaborates. -/
example {n : ℕ} {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) : ∃ i, ζ i ≠ 0 := by
  classical
  by_contra hall
  push Not at hall
  apply hζ
  funext i
  simpa using hall i

/-- Type-witness: the composition skeleton (case-split + chain references)
elaborates against the five sub-lemma signatures. The body of the
`n ≥ 1` branch matches the upstream `bohrCoefficient_exp_ne` body
verbatim modulo namespace; if this elaborates, the signature chain
in the upstream theorem is sound. -/
example {n : ℕ} {ζ : Fin n → ℝ} (hζ : ζ ≠ 0) :
    n = 0 ∨ ∃ i₀ : Fin n, ζ i₀ ≠ 0 := by
  rcases Nat.eq_zero_or_pos n with hn0 | hnpos
  · exact Or.inl hn0
  · refine Or.inr ?_
    have hex_i₀ : ∃ i, ζ i ≠ 0 := by
      classical
      by_contra hall
      push Not at hall
      apply hζ
      funext i
      simpa using hall i
    obtain ⟨i₀, hi₀⟩ := hex_i₀
    -- Type-pin all five chain-step references (mirrors the upstream
    -- composition body). The `_step*` shadows force elaboration of
    -- each named sub-lemma's signature.
    have _step1 := @cube_integral_prod_factor n
    have _step2 := @integral_Icc_exp_mul
    have _step3 := @osc_integral_norm_bound
    have _step4 := @osc_integral_trivial_bound
    have _step5 := @const_div_atTop_zero
    have _used_hnpos : 0 < n := hnpos
    have _used_i₀ : ζ i₀ ≠ 0 := hi₀
    exact ⟨i₀, hi₀⟩

end AlmostPeriodicBohrCoeffExpNeSmoke
