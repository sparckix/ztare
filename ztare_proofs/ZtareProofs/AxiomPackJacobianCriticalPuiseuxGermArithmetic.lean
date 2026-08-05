import Mathlib.Tactic

/-!
Algebraic leading-scale carrier for the selected critical Puiseux germ.

The theorem records the exact discriminant factorization and the simple-zero
scale of the radical coefficient at `x = -2`.  Choosing a square-root branch,
constructing the local series, and integrating to the endpoint `u^(5/2)` term
remain outside this arithmetic carrier.
-/

namespace AxiomPackJacobianCriticalPuiseuxGermArithmetic

def discriminant (x : ℚ) : ℚ :=
  36 + 12 * x - 3 * x ^ 2

def radicalNumerator (x : ℚ) : ℚ :=
  (x - 6) * (x + 2) * (7 * x ^ 3 - 42 * x ^ 2 + 624)

def radicalDenominator (x : ℚ) : ℚ :=
  896 * x ^ 3 * (x - 4) * (x ^ 2 - 4 * x - 8)

def radicalSimpleZeroScale : ℚ :=
  ((-2 : ℚ) - 6) *
      (7 * (-2 : ℚ) ^ 3 - 42 * (-2 : ℚ) ^ 2 + 624) /
    radicalDenominator (-2)

theorem discriminant_factorization (x : ℚ) :
    discriminant x = (x + 2) * (-3 * (x - 6)) := by
  unfold discriminant
  ring

theorem discriminant_linear_scale_at_branch :
    -3 * ((-2 : ℚ) - 6) = 24 := by
  norm_num

theorem radical_numerator_simple_zero (x : ℚ) :
    radicalNumerator x =
      (x + 2) * ((x - 6) * (7 * x ^ 3 - 42 * x ^ 2 + 624)) := by
  unfold radicalNumerator
  ring

theorem radical_denominator_at_branch_nonzero :
    radicalDenominator (-2) ≠ 0 := by
  norm_num [radicalDenominator]

theorem radical_simple_zero_scale_exact :
    radicalSimpleZeroScale = -25 / 1344 := by
  norm_num [radicalSimpleZeroScale, radicalDenominator]

theorem radical_simple_zero_scale_nonzero :
    radicalSimpleZeroScale ≠ 0 := by
  norm_num [radicalSimpleZeroScale, radicalDenominator]

/-- Aggregated arithmetic endpoint for the leading selected-branch scales. -/
theorem critical_branch_leading_scales_terminal_certificate :
    (∀ x : ℚ, discriminant x = (x + 2) * (-3 * (x - 6))) ∧
    -3 * ((-2 : ℚ) - 6) = 24 ∧
    (∀ x : ℚ, radicalNumerator x =
      (x + 2) * ((x - 6) * (7 * x ^ 3 - 42 * x ^ 2 + 624))) ∧
    radicalDenominator (-2) ≠ 0 ∧
    radicalSimpleZeroScale = -25 / 1344 ∧
    radicalSimpleZeroScale ≠ 0 := by
  exact ⟨discriminant_factorization,
    discriminant_linear_scale_at_branch,
    radical_numerator_simple_zero,
    radical_denominator_at_branch_nonzero,
    radical_simple_zero_scale_exact,
    radical_simple_zero_scale_nonzero⟩

end AxiomPackJacobianCriticalPuiseuxGermArithmetic
