import Mathlib.RingTheory.PowerSeries.Derivative
import Mathlib.RingTheory.PowerSeries.Exp
import Mathlib.RingTheory.PowerSeries.Substitution

/-!
# Normalized scalar linear ODEs in formal power series

The missing constructor is the zero-constant formal antiderivative.  Composing
the exponential series with that antiderivative constructs the normalized
solution of `E' = A E`.
-/

namespace FormalPowerSeriesLinearODE

open PowerSeries

variable {k : Type*} [Field k] [CharZero k]

/-- Formal antiderivative with zero constant coefficient. -/
noncomputable def integralZero (series : k⟦X⟧) : k⟦X⟧ :=
  PowerSeries.mk fun n =>
    if n = 0 then 0 else (n : k)⁻¹ * coeff (n - 1) series

omit [CharZero k] in
@[simp]
theorem coeff_integralZero (series : k⟦X⟧) (n : ℕ) :
    coeff n (integralZero series) =
      if n = 0 then 0 else (n : k)⁻¹ * coeff (n - 1) series := by
  simp [integralZero]

omit [CharZero k] in
@[simp]
theorem constantCoeff_integralZero (series : k⟦X⟧) :
    constantCoeff (integralZero series) = 0 := by
  rw [← coeff_zero_eq_constantCoeff]
  simp

@[simp]
theorem derivative_integralZero (series : k⟦X⟧) :
    d⁄dX k (integralZero series) = series := by
  ext n
  rw [coeff_derivative, coeff_integralZero]
  have hsucc : (n + 1 : k) ≠ 0 := by
    exact_mod_cast Nat.succ_ne_zero n
  simp only [Nat.succ_ne_zero, if_false, Nat.add_sub_cancel]
  field_simp
  simp [Nat.cast_add, Nat.cast_one, mul_comm]

omit [CharZero k] in
theorem integralZero_hasSubst (series : k⟦X⟧) :
    HasSubst (integralZero series) :=
  HasSubst.of_constantCoeff_zero' (constantCoeff_integralZero series)

/-- The normalized solution `exp(∫₀ A)`. -/
noncomputable def normalizedEndpoint (coefficient : k⟦X⟧) : k⟦X⟧ :=
  (PowerSeries.exp k).subst (integralZero coefficient)

@[simp]
theorem normalizedEndpoint_constantCoeff (coefficient : k⟦X⟧) :
    constantCoeff (normalizedEndpoint coefficient) = 1 := by
  rw [normalizedEndpoint]
  change MvPowerSeries.constantCoeff
      ((PowerSeries.exp k).subst (integralZero coefficient)) = 1
  rw [PowerSeries.constantCoeff_subst
    (integralZero_hasSubst coefficient)]
  rw [finsum_eq_single _ 0 (fun d hd => by
    have hzero :
        MvPowerSeries.constantCoeff (integralZero coefficient) = 0 := by
      rw [← PowerSeries.constantCoeff_eq]
      exact constantCoeff_integralZero coefficient
    simp [hzero, hd])]
  simp

/-- The constructed endpoint solves the complete formal ODE. -/
theorem normalizedEndpoint_derivative (coefficient : k⟦X⟧) :
    d⁄dX k (normalizedEndpoint coefficient) =
      coefficient * normalizedEndpoint coefficient := by
  rw [normalizedEndpoint,
    PowerSeries.derivative_subst k (integralZero_hasSubst coefficient),
    PowerSeries.derivative_exp,
    derivative_integralZero]
  ring

/-- A scalar formal linear ODE has at most one solution with a supplied
constant coefficient.  The induction divides only by positive integers, so
the characteristic-zero assumption is explicit. -/
theorem linear_ode_solution_unique
    {coefficient left right : k⟦X⟧}
    (hconstant : constantCoeff left = constantCoeff right)
    (hleft : d⁄dX k left = coefficient * left)
    (hright : d⁄dX k right = coefficient * right) :
    left = right := by
  apply PowerSeries.ext
  intro n
  induction n using Nat.strong_induction_on with
  | h n inductionHypothesis =>
      cases n with
      | zero =>
          simpa [coeff_zero_eq_constantCoeff] using hconstant
      | succ n =>
          have hproduct :
              coeff n (coefficient * left) =
                coeff n (coefficient * right) := by
            rw [PowerSeries.coeff_mul, PowerSeries.coeff_mul]
            apply Finset.sum_congr rfl
            intro pair hpair
            congr 1
            apply inductionHypothesis pair.2
            have hpairsum := Finset.mem_antidiagonal.mp hpair
            omega
          have hleftCoeff := congrArg (coeff n) hleft
          have hrightCoeff := congrArg (coeff n) hright
          rw [coeff_derivative] at hleftCoeff hrightCoeff
          have hcast : ((n + 1 : ℕ) : k) ≠ 0 := by
            exact_mod_cast Nat.succ_ne_zero n
          apply mul_right_cancel₀ hcast
          simpa [Nat.cast_add, Nat.cast_one] using
            hleftCoeff.trans (hproduct.trans hrightCoeff.symm)

/-- Aggregated constructor certificate for normalized scalar formal ODEs. -/
theorem normalized_formal_linear_ode_terminal_certificate :
    ∀ coefficient : k⟦X⟧,
      constantCoeff (normalizedEndpoint coefficient) = 1 ∧
      d⁄dX k (normalizedEndpoint coefficient) =
        coefficient * normalizedEndpoint coefficient := by
  intro coefficient
  exact ⟨normalizedEndpoint_constantCoeff coefficient,
    normalizedEndpoint_derivative coefficient⟩

end FormalPowerSeriesLinearODE
