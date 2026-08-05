import Mathlib.Tactic

/-!
Arithmetic carrier for the pure contact-zero polar tensor induction.

The symbolic adapter supplies the split `(A,J)` Lie algebra, the exact
quadratic-field critical residual, the semidirect factorization, and the
source degree dictionary.  This file kernel-checks the universal arithmetic
used after those identities are bound:

* invariance of the Newton weight under the leading polar adjoint;
* the tensor-density monomial recurrence step;
* the uniform four-start resonance bound; and
* strict rate above two on every positive Rees face.

No claim about completeness of the Jacobian adapter is inferred here.
-/

namespace AxiomPackJacobianPolarTensorInductionArithmetic

/-- The leading adjoint step `(nu,e) -> (nu-h,e+d)` preserves `h*e+d*nu`. -/
theorem tensor_newton_invariant (h d e nu : ℤ) :
    h * (e + d) + d * (nu - h) = h * e + d * nu := by
  ring

/-- Applying `rho(x^d)` after `k` preceding steps contributes the next
factor in the tensor-density orbit product. -/
theorem tensor_orbit_factor_step (d e k : ℤ) :
    2 * (e + k * d) - 3 * d - 5 =
      2 * e + (2 * k - 3) * d - 5 := by
  ring

/-- A positive integral resonance can occur only at an adjoint index
`i = 0,1,2,3`.  Since the resonance equation determines `e` at each index,
there are at most four positive resonant starting exponents. -/
theorem tensor_resonance_index_le_three
    (d e i : ℕ)
    (hd : 1 ≤ d)
    (he : 1 ≤ e)
    (hresonance : 2 * e + 2 * i * d = 3 * d + 5) :
    i ≤ 3 := by
  nlinarith

/-- For a fixed actor exponent and adjoint index, the resonant starting
exponent is unique. -/
theorem tensor_resonant_start_unique
    (d e₁ e₂ i : ℕ)
    (h₁ : 2 * e₁ + 2 * i * d = 3 * d + 5)
    (h₂ : 2 * e₂ + 2 * i * d = 3 * d + 5) :
    e₁ = e₂ := by
  omega

/-- The source-degree slope exceeds twice the parameter-order slope by
exactly twice the positive Rees grade. -/
theorem tensor_positive_face_slope_excess
    (d h : ℤ) :
    2 * d - 2 * (d - h) = 2 * h := by
  ring

/-- Every positive polar face has limiting source rate strictly above two. -/
theorem tensor_positive_face_rate_above_two
    (d h : ℚ)
    (hh : 0 < h)
    (hd : h < d) :
    2 < 2 * d / (d - h) := by
  have hdenom : 0 < d - h := sub_pos.mpr hd
  rw [lt_div_iff₀ hdenom]
  nlinarith

/-- Aggregated arithmetic endpoint for the polar tensor induction. -/
theorem polar_tensor_induction_arithmetic_terminal_certificate :
    (∀ h d e nu : ℤ,
      h * (e + d) + d * (nu - h) = h * e + d * nu) ∧
    (∀ d e k : ℤ,
      2 * (e + k * d) - 3 * d - 5 =
        2 * e + (2 * k - 3) * d - 5) ∧
    (∀ d e i : ℕ,
      1 ≤ d → 1 ≤ e →
      2 * e + 2 * i * d = 3 * d + 5 → i ≤ 3) ∧
    (∀ d e₁ e₂ i : ℕ,
      2 * e₁ + 2 * i * d = 3 * d + 5 →
      2 * e₂ + 2 * i * d = 3 * d + 5 → e₁ = e₂) ∧
    (∀ d h : ℤ, 2 * d - 2 * (d - h) = 2 * h) ∧
    (∀ d h : ℚ, 0 < h → h < d → 2 < 2 * d / (d - h)) := by
  exact ⟨tensor_newton_invariant,
    tensor_orbit_factor_step,
    tensor_resonance_index_le_three,
    tensor_resonant_start_unique,
    tensor_positive_face_slope_excess,
    tensor_positive_face_rate_above_two⟩

end AxiomPackJacobianPolarTensorInductionArithmetic
