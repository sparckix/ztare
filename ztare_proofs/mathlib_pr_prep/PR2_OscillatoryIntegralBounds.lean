import Mathlib.Analysis.SpecialFunctions.Integrals.Basic

open scoped Real

namespace MathlibPrPrep

/-!
This file is a neutral extraction candidate from the local Bohr/AP support
work.  It deliberately avoids Bohr, Navier-Stokes, and project-specific names.
-/

private lemma norm_exp_mul_I_sub_exp_mul_I_div_le (a b k : ℝ) (hk : k ≠ 0) :
    ‖(Complex.exp ((k : ℂ) * Complex.I * (b : ℂ)) -
          Complex.exp ((k : ℂ) * Complex.I * (a : ℂ))) /
        ((k : ℂ) * Complex.I)‖ ≤
      2 / |k| := by
  have h_exp_norm : ∀ x : ℝ, ‖Complex.exp ((k : ℂ) * Complex.I * (x : ℂ))‖ = 1 := by
    intro x
    rw [show (k : ℂ) * Complex.I * (x : ℂ) = Complex.I * ((k * x : ℝ) : ℂ) by
      rw [Complex.ofReal_mul]
      ring]
    exact Complex.norm_exp_I_mul_ofReal (k * x)
  have h_num :
      ‖Complex.exp ((k : ℂ) * Complex.I * (b : ℂ)) -
          Complex.exp ((k : ℂ) * Complex.I * (a : ℂ))‖ ≤ 2 := by
    calc
      ‖Complex.exp ((k : ℂ) * Complex.I * (b : ℂ)) -
          Complex.exp ((k : ℂ) * Complex.I * (a : ℂ))‖
          ≤ ‖Complex.exp ((k : ℂ) * Complex.I * (b : ℂ))‖ +
              ‖Complex.exp ((k : ℂ) * Complex.I * (a : ℂ))‖ :=
            norm_sub_le _ _
      _ = 2 := by rw [h_exp_norm b, h_exp_norm a]; norm_num
  have h_den : ‖(k : ℂ) * Complex.I‖ = |k| := by
    rw [norm_mul, Complex.norm_I, mul_one, Complex.norm_real, Real.norm_eq_abs]
  have h_abs_pos : 0 < |k| := abs_pos.mpr hk
  rw [norm_div, h_den]
  exact div_le_div_of_nonneg_right h_num h_abs_pos.le

lemma norm_integral_exp_mul_I_le_length (hab : a ≤ b) (k : ℝ) :
    ‖∫ x in a..b, Complex.exp ((k : ℂ) * Complex.I * (x : ℂ))‖ ≤
      b - a := by
  have h :
      ‖∫ x in a..b, Complex.exp ((k : ℂ) * Complex.I * (x : ℂ))‖ ≤
        (1 : ℝ) * |b - a| := by
    apply intervalIntegral.norm_integral_le_of_norm_le_const
    intro x _
    rw [show ‖Complex.exp ((k : ℂ) * Complex.I * (x : ℂ))‖ = 1 by
      rw [show (k : ℂ) * Complex.I * (x : ℂ) = Complex.I * ((k * x : ℝ) : ℂ) by
        rw [Complex.ofReal_mul]
        ring]
      exact Complex.norm_exp_I_mul_ofReal (k * x)]
  simpa [abs_of_nonneg (sub_nonneg.mpr hab)] using h

lemma norm_integral_exp_mul_I_le_two_div (a b k : ℝ) (hk : k ≠ 0) :
    ‖∫ x in a..b, Complex.exp ((k : ℂ) * Complex.I * (x : ℂ))‖ ≤
      2 / |k| := by
  have hkI : (k : ℂ) * Complex.I ≠ 0 := by
    exact mul_ne_zero (Complex.ofReal_ne_zero.mpr hk) Complex.I_ne_zero
  rw [integral_exp_mul_complex (a := a) (b := b) (c := (k : ℂ) * Complex.I) hkI]
  exact norm_exp_mul_I_sub_exp_mul_I_div_le a b k hk

end MathlibPrPrep
