import Mathlib.Analysis.Complex.Basic
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Tactic

/-!
# Exact disk nonvanishing from shifted coefficient dominance

This is a finite Rouché-style criterion with no root approximation.  A
shifted polynomial is nonzero throughout a disk when its constant coefficient
strictly dominates the norm bound for its positive-degree tail.
-/

namespace FormalPolynomialDiskNonvanishing

open scoped BigOperators

/-- A degree-bounded polynomial value in a coordinate shifted to the disk
center.  `degree` counts the positive-degree tail terms. -/
noncomputable def shiftedPolynomialValue
    (coefficient : ℕ → ℂ) (degree : ℕ) (shift : ℂ) : ℂ :=
  coefficient 0 +
    ∑ i ∈ Finset.range degree,
      coefficient (i + 1) * shift ^ (i + 1)

/-- Strict constant-term dominance certifies nonvanishing on the open disk. -/
theorem shiftedPolynomialValue_ne_zero_of_norm_lt
    (coefficient : ℕ → ℂ) (degree : ℕ) (radius : ℝ) (shift : ℂ)
    (hshift : ‖shift‖ < radius)
    (hdominates :
      (∑ i ∈ Finset.range degree,
        ‖coefficient (i + 1)‖ * radius ^ (i + 1)) <
          ‖coefficient 0‖) :
    shiftedPolynomialValue coefficient degree shift ≠ 0 := by
  intro hzero
  have hconstant :
      coefficient 0 =
        -(∑ i ∈ Finset.range degree,
          coefficient (i + 1) * shift ^ (i + 1)) := by
    simpa [shiftedPolynomialValue, add_eq_zero_iff_eq_neg] using hzero
  have hnormTail :
      ‖∑ i ∈ Finset.range degree,
          coefficient (i + 1) * shift ^ (i + 1)‖ ≤
        ∑ i ∈ Finset.range degree,
          ‖coefficient (i + 1) * shift ^ (i + 1)‖ :=
    norm_sum_le _ _
  have hterm : ∀ i ∈ Finset.range degree,
      ‖coefficient (i + 1) * shift ^ (i + 1)‖ ≤
        ‖coefficient (i + 1)‖ * radius ^ (i + 1) := by
    intro i _hi
    rw [norm_mul, norm_pow]
    apply mul_le_mul_of_nonneg_left
    · exact pow_le_pow_left₀ (norm_nonneg shift) (le_of_lt hshift) _
    · exact norm_nonneg _
  have htailBound :
      (∑ i ∈ Finset.range degree,
        ‖coefficient (i + 1) * shift ^ (i + 1)‖) ≤
      ∑ i ∈ Finset.range degree,
        ‖coefficient (i + 1)‖ * radius ^ (i + 1) := by
    exact Finset.sum_le_sum hterm
  have hnormConstant :
      ‖coefficient 0‖ =
        ‖∑ i ∈ Finset.range degree,
          coefficient (i + 1) * shift ^ (i + 1)‖ := by
    rw [hconstant, norm_neg]
  linarith

/-- Aggregated exact disk certificate. -/
theorem polynomial_disk_nonvanishing_terminal_certificate :
    ∀ (coefficient : ℕ → ℂ) (degree : ℕ) (radius : ℝ) (shift : ℂ),
      ‖shift‖ < radius →
      (∑ i ∈ Finset.range degree,
        ‖coefficient (i + 1)‖ * radius ^ (i + 1)) <
          ‖coefficient 0‖ →
      shiftedPolynomialValue coefficient degree shift ≠ 0 := by
  intro coefficient degree radius shift hshift hdominates
  exact shiftedPolynomialValue_ne_zero_of_norm_lt
    coefficient degree radius shift hshift hdominates

end FormalPolynomialDiskNonvanishing
