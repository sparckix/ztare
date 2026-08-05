# Moving-backbone induction arithmetic thesis

This proof artifact checks the arithmetic endpoint used after the exact
Jacobian group factorization and complete-face reductions.  Its scope is the
least nonzero positive-contact branch.  It does not encode the pure
contact-zero lower induction or the final global minimax comparison.

```lean
import Mathlib.Tactic

namespace AxiomPackJacobianMovingBackboneInductionArithmetic

def rateGrade (w j : ℤ) : ℤ :=
  2 * (w - j - 5)

theorem rate_grade_bracket_additive (w v j k : ℤ) :
    rateGrade (w + v - 5) (j + k) =
      rateGrade w j + rateGrade v k := by
  unfold rateGrade
  ring

def LiftAdmissible (a b : ℤ) : Prop :=
  1 ≤ a ∨ (a = 0 ∧ 2 ≤ b)

def normalThreeFirstFactor (a b m : ℤ) : ℤ :=
  6 * a + 9 * b + 21 * m - 10

def normalThreeSecondFactor (a b m alpha : ℤ) : ℤ :=
  16 * a * m + 4 * a - 4 * alpha + 18 * b * m +
    37 * m ^ 2 - 29 * m

theorem normal_three_first_factor_positive
    (a b m : ℤ)
    (ha : 0 ≤ a) (hb : 0 ≤ b) (hm : 1 ≤ m)
    (hlift : LiftAdmissible a b) :
    0 < normalThreeFirstFactor a b m := by
  rcases hlift with ha1 | ⟨ha0, hb2⟩
  · unfold normalThreeFirstFactor
    omega
  · subst a
    unfold normalThreeFirstFactor
    omega

theorem normal_three_second_factor_positive
    (a b m alpha : ℤ)
    (ha : 0 ≤ a) (hb : 0 ≤ b) (hm : 1 ≤ m)
    (_halpha0 : 0 ≤ alpha) (halpha2 : alpha ≤ 2)
    (hlift : LiftAdmissible a b) :
    0 < normalThreeSecondFactor a b m alpha := by
  have hm0 : 0 ≤ m := by omega
  have hmm1 : 0 ≤ m * (m - 1) :=
    mul_nonneg hm0 (by omega)
  have hbm : 0 ≤ b * m := mul_nonneg hb hm0
  rcases hlift with ha1 | ⟨ha0, hb2⟩
  · have ham : 1 ≤ a * m := by nlinarith
    unfold normalThreeSecondFactor
    nlinarith
  · subst a
    have hbm2 : 2 ≤ b * m := by nlinarith
    unfold normalThreeSecondFactor
    nlinarith

def exceptionalExit (k : ℕ) : ℚ :=
  -3 / (2 : ℚ) ^ (3 * k + 4)

theorem exceptional_exit_nonzero (k : ℕ) :
    exceptionalExit k ≠ 0 := by
  simp [exceptionalExit]

theorem affine_occurrence_orders_injective
    (n₀ step k ell : ℕ) (hstep : 0 < step)
    (heq : n₀ + step * k = n₀ + step * ell) :
    k = ell := by
  have hmul : step * k = step * ell := Nat.add_left_cancel heq
  exact Nat.eq_of_mul_eq_mul_left hstep hmul

theorem least_index_shift_preserves_order_step
    (n₀ step shift k : ℕ) :
    (shift + n₀ + step * (k + 1)) -
        (shift + n₀ + step * k) = step := by
  simp [Nat.mul_succ]
  omega

theorem terminal_rate_at_least_two :
    (2 : ℚ) ≤ 11 / 2 := by
  norm_num

theorem cancellation_payment_rate_at_least_two :
    (2 : ℚ) ≤ 4 / 2 := by
  norm_num

theorem moving_backbone_induction_arithmetic_terminal_certificate :
    (∀ w v j k : ℤ,
      rateGrade (w + v - 5) (j + k) =
        rateGrade w j + rateGrade v k) ∧
    (∀ a b m : ℤ, 0 ≤ a → 0 ≤ b → 1 ≤ m → LiftAdmissible a b →
      0 < normalThreeFirstFactor a b m) ∧
    (∀ a b m alpha : ℤ,
      0 ≤ a → 0 ≤ b → 1 ≤ m → 0 ≤ alpha → alpha ≤ 2 →
      LiftAdmissible a b →
      0 < normalThreeSecondFactor a b m alpha) ∧
    (∀ k : ℕ, exceptionalExit k ≠ 0) ∧
    (∀ n₀ step k ell : ℕ, 0 < step →
      n₀ + step * k = n₀ + step * ell → k = ell) ∧
    (∀ n₀ step shift k : ℕ,
      (shift + n₀ + step * (k + 1)) -
        (shift + n₀ + step * k) = step) ∧
    (2 : ℚ) ≤ 11 / 2 ∧
    (2 : ℚ) ≤ 4 / 2 := by
  exact ⟨
    rate_grade_bracket_additive,
    normal_three_first_factor_positive,
    normal_three_second_factor_positive,
    exceptional_exit_nonzero,
    affine_occurrence_orders_injective,
    least_index_shift_preserves_order_step,
    terminal_rate_at_least_two,
    cancellation_payment_rate_at_least_two⟩

end AxiomPackJacobianMovingBackboneInductionArithmetic
```
