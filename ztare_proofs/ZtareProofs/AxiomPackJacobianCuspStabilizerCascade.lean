import Mathlib

/-!
Arithmetic certificate for the generic-amplitude cusp-stabilizer cascade in
the normalized Jacobian contact campaign.

The mathematical BCH calculation gives, at logarithmic order `k + 1`, a
Hamiltonian coefficient polynomial in the normal amplitude `μ`.  Its linear
coefficient is

`(-1)^k / (k + 1)! * ad_C^k(B)`.

Restriction to the cusp turns `ad_C^k(B)` into the nonzero scalar recurrence
encoded below.  The final theorem records the algebraic consequence used by
the pencil argument: arbitrary terms divisible by `μ²` cannot erase that
linear coefficient over the rational function field.

This file certifies that arithmetic spine.  The identification with the BCH
coefficient and the Hamiltonian restriction is carried by the exact symbolic
artifact; no formal-power-series contact group is constructed here.
-/

namespace AxiomPackJacobianCuspStabilizerCascade

open Polynomial

noncomputable section

/-- The scalar multiplying `r^(6+k)` in `(ad_C)^k B` on the normalized cusp. -/
def restrictedIterate : ℕ → ℚ
  | 0 => -1 / 4
  | k + 1 => 18 * (k + 6) * restrictedIterate k

theorem restrictedIterate_ne_zero (k : ℕ) :
    restrictedIterate k ≠ 0 := by
  induction k with
  | zero =>
      norm_num [restrictedIterate]
  | succ k ih =>
      simp only [restrictedIterate]
      exact mul_ne_zero
        (mul_ne_zero (by norm_num) (by positivity))
        ih

/-- The linear-in-amplitude BCH scalar at logarithmic order `k + 1`. -/
def linearBchScalar (k : ℕ) : ℚ :=
  (-1) ^ k * restrictedIterate k / (k + 1).factorial

theorem linearBchScalar_ne_zero (k : ℕ) :
    linearBchScalar k ≠ 0 := by
  apply div_ne_zero
  · exact mul_ne_zero (pow_ne_zero _ (by norm_num))
      (restrictedIterate_ne_zero k)
  · exact_mod_cast Nat.factorial_ne_zero (k + 1)

/-- A generic amplitude coefficient with the certified linear term and an
arbitrary nonlinear tail. -/
def amplitudeCoefficient (k : ℕ) (nonlinear : Polynomial ℚ) :
    Polynomial ℚ :=
  C (linearBchScalar k) * X + X ^ 2 * nonlinear

theorem amplitudeCoefficient_coeff_one
    (k : ℕ) (nonlinear : Polynomial ℚ) :
    (amplitudeCoefficient k nonlinear).coeff 1 =
      linearBchScalar k := by
  simp [amplitudeCoefficient, coeff_X_pow_mul']

theorem amplitudeCoefficient_ne_zero
    (k : ℕ) (nonlinear : Polynomial ℚ) :
    amplitudeCoefficient k nonlinear ≠ 0 := by
  intro hzero
  have hcoeff := congrArg (fun p : Polynomial ℚ => p.coeff 1) hzero
  change (amplitudeCoefficient k nonlinear).coeff 1 =
    (0 : Polynomial ℚ).coeff 1 at hcoeff
  rw [amplitudeCoefficient_coeff_one] at hcoeff
  simp only [coeff_zero] at hcoeff
  exact linearBchScalar_ne_zero k hcoeff

/-- Terminal arithmetic certificate for every order of the generic-amplitude
cascade. -/
theorem generic_amplitude_cascade_arithmetic_terminal_certificate :
    (∀ k : ℕ, restrictedIterate k ≠ 0) ∧
      (∀ k : ℕ, linearBchScalar k ≠ 0) ∧
      (∀ (k : ℕ) (nonlinear : Polynomial ℚ),
        amplitudeCoefficient k nonlinear ≠ 0) := by
  exact ⟨restrictedIterate_ne_zero, linearBchScalar_ne_zero,
    amplitudeCoefficient_ne_zero⟩

end

end AxiomPackJacobianCuspStabilizerCascade
