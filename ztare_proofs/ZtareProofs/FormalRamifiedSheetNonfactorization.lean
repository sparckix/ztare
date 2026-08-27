import Mathlib.Analysis.Calculus.Deriv.CompMul
import Mathlib.RingTheory.RootsOfUnity.Complex
import Mathlib.Tactic

/-!
# A ramified sheet cannot factor through the unramified base time

For ramification order greater than one, a germ of the form

`w ↦ trajectory (t∞ + unit * w ^ order)`

is invariant under a nontrivial `order`-th root of unity.  Its derivative at
the ramification center is therefore zero.  This rules out interfaces that
simultaneously factor a selected sheet through a single-valued base-time
trajectory and require a nonzero uniformizing derivative.
-/

namespace FormalRamifiedSheetNonfactorization

/-- Every function that factors through an `order`-th power has zero
derivative at the ramification center when `order > 1`.  No regularity of the
outer function is needed. -/
theorem deriv_zero_of_factors_through_nth_power
    (trajectory : ℂ → ℂ) (infinityTime unit : ℂ) (order : ℕ)
    (horder : 2 ≤ order) :
    deriv (fun w : ℂ ↦
      trajectory (infinityTime + unit * w ^ order)) 0 = 0 := by
  let ζ : ℂ := Complex.exp (2 * Real.pi * Complex.I / order)
  let selected : ℂ → ℂ := fun w ↦
    trajectory (infinityTime + unit * w ^ order)
  have horderNe : order ≠ 0 := by omega
  have hprimitive : IsPrimitiveRoot ζ order := by
    simpa only [ζ] using Complex.isPrimitiveRoot_exp order horderNe
  have hζpow : ζ ^ order = 1 := hprimitive.pow_eq_one
  have hζne : ζ ≠ 1 := hprimitive.ne_one (by omega)
  have hinvariant : (fun w : ℂ ↦ selected (ζ * w)) = selected := by
    funext w
    simp only [selected, mul_pow, hζpow, one_mul]
  have hderivative := congrArg (fun f : ℂ → ℂ ↦ deriv f 0) hinvariant
  change deriv (fun w : ℂ ↦ selected (ζ * w)) 0 =
    deriv selected 0 at hderivative
  rw [deriv_comp_mul_left] at hderivative
  simp only [mul_zero, smul_eq_mul] at hderivative
  have hproduct : (ζ - 1) * deriv selected 0 = 0 := by
    linear_combination hderivative
  rcases mul_eq_zero.mp hproduct with hζ | hderivativeZero
  · exact (hζne (sub_eq_zero.mp hζ)).elim
  · simpa only [selected] using hderivativeZero

/-- The derivative-one premise used by an unramified factor-through model is
incompatible with every nontrivial ramification order. -/
theorem derivative_one_factor_through_nth_power_impossible
    (trajectory : ℂ → ℂ) (infinityTime unit : ℂ) (order : ℕ)
    (horder : 2 ≤ order)
    (hderivative : deriv (fun w : ℂ ↦
      trajectory (infinityTime + unit * w ^ order)) 0 = 1) : False := by
  have hzero := deriv_zero_of_factors_through_nth_power
    trajectory infinityTime unit order horder
  exact zero_ne_one (hzero.symm.trans hderivative)

/-- Aggregated incompatibility certificate for formal-coverage audits. -/
theorem ramified_sheet_nonfactorization_terminal_certificate :
    ∀ (trajectory : ℂ → ℂ) (infinityTime unit : ℂ) (order : ℕ),
      2 ≤ order →
      deriv (fun w : ℂ ↦
        trajectory (infinityTime + unit * w ^ order)) 0 = 0 := by
  exact deriv_zero_of_factors_through_nth_power

end FormalRamifiedSheetNonfactorization
