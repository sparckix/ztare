import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticLogarithmicLoop

/-!
# Single-valued scalar eigenrows versus non-torsion monodromy

The existing logarithmic-circle carrier can be scaled by a positive natural
weight.  Any pulled-back scalar solution of that weighted connection agrees
with the carrier's explicit continuation.  Consequently a nonzero solution
cannot return to its initial value after a positive number of turns when the
base multiplier has no positive torsion power.

The file assumes the scalar eigenrow has already been specialized and pulled
back to the circle.  It does not construct that upstream binding.
-/

namespace FormalSingleValuedEigenrowMonodromy

open Complex

open FormalAnalyticLogarithmicLoop

/-- Natural scaling of the existing logarithmic-circle connection. -/
noncomputable def natScaleCarrier
    (carrier : LogarithmicCircleCarrier) (weight : ℕ) :
    LogarithmicCircleCarrier where
  center := carrier.center
  radius := carrier.radius
  radius_ne_zero := carrier.radius_ne_zero
  residue := (weight : ℂ) * carrier.residue
  regularCoefficient := fun z =>
    (weight : ℂ) * carrier.regularCoefficient z
  regularPrimitive := fun z =>
    (weight : ℂ) * carrier.regularPrimitive z
  regularPrimitive_derivative := fun theta => by
    simpa using
      (carrier.regularPrimitive_derivative theta).const_mul (weight : ℂ)

/-- Scaling the carrier scales its logarithmic coefficient pointwise. -/
theorem natScaleCarrier_coefficient
    (carrier : LogarithmicCircleCarrier) (weight : ℕ) (z : ℂ) :
    (natScaleCarrier carrier weight).coefficient z =
      (weight : ℂ) * carrier.coefficient z := by
  simp only [natScaleCarrier, LogarithmicCircleCarrier.coefficient]
  ring

/-- The multiplier of the scaled carrier is the corresponding natural
power of the original multiplier. -/
theorem natScaleCarrier_multiplier
    (carrier : LogarithmicCircleCarrier) (weight : ℕ) :
    (natScaleCarrier carrier weight).multiplier =
      carrier.multiplier ^ weight := by
  rw [LogarithmicCircleCarrier.multiplier,
    LogarithmicCircleCarrier.multiplier]
  simp only [natScaleCarrier]
  rw [← Complex.exp_nat_mul]
  congr 1
  ring

/-- A nonzero solution of a positive-weight logarithmic eigenrow cannot be
single-valued after a positive number of turns when the base multiplier is
non-torsion. -/
theorem no_single_valued_positive_weight_solution
    (carrier : LogarithmicCircleCarrier)
    (weight turns : ℕ)
    (weight_positive : 0 < weight)
    (turns_positive : 0 < turns)
    (solution : ℝ → ℂ)
    (solution_ode : ∀ theta : ℝ,
      HasDerivAt solution
        ((weight : ℂ) *
          carrier.coefficient
            (circleMap carrier.center carrier.radius theta) *
          (circleMap 0 carrier.radius theta * I) *
          solution theta)
        theta)
    (initial_nonzero : solution 0 ≠ 0)
    (single_valued_return :
      solution ((turns : ℝ) * (2 * Real.pi)) = solution 0)
    (multiplier_non_torsion : ∀ order : ℕ, 0 < order →
      carrier.multiplier ^ order ≠ 1) :
    False := by
  let scaled := natScaleCarrier carrier weight
  let explicit := scaled.continuedValue (solution 0)
  have explicit_ode : ∀ theta : ℝ,
      HasDerivAt explicit
        ((weight : ℂ) *
          carrier.coefficient
            (circleMap carrier.center carrier.radius theta) *
          (circleMap 0 carrier.radius theta * I) *
          explicit theta)
        theta := by
    intro theta
    have h := scaled.continuedValue_hasDerivAt (solution 0) theta
    have hcoefficient :
        scaled.coefficient
            (circleMap scaled.center scaled.radius theta) =
          (weight : ℂ) *
            carrier.coefficient
              (circleMap carrier.center carrier.radius theta) := by
      simpa [scaled, natScaleCarrier] using
        natScaleCarrier_coefficient carrier weight
          (circleMap carrier.center carrier.radius theta)
    rw [hcoefficient] at h
    simpa [explicit, scaled, natScaleCarrier] using h
  have explicit_nonzero : ∀ theta : ℝ, explicit theta ≠ 0 := by
    intro theta
    exact mul_ne_zero initial_nonzero (Complex.exp_ne_zero _)
  let ratio : ℝ → ℂ := fun theta => solution theta / explicit theta
  have ratio_hasDerivAt : ∀ theta : ℝ, HasDerivAt ratio 0 theta := by
    intro theta
    have hquotient := (solution_ode theta).div (explicit_ode theta)
      (explicit_nonzero theta)
    change HasDerivAt (fun x => solution x / explicit x) 0 theta
    convert hquotient using 1
    ring
  have ratio_differentiable : Differentiable ℝ ratio :=
    fun theta => (ratio_hasDerivAt theta).differentiableAt
  have ratio_deriv_zero : ∀ theta : ℝ, deriv ratio theta = 0 :=
    fun theta => (ratio_hasDerivAt theta).deriv
  let endpointTime : ℝ := (turns : ℝ) * (2 * Real.pi)
  have ratio_constant : ratio endpointTime = ratio 0 :=
    is_const_of_deriv_eq_zero ratio_differentiable ratio_deriv_zero _ _
  have explicit_zero : explicit 0 = solution 0 := by
    simp [explicit]
  have ratio_zero : ratio 0 = 1 := by
    simp [ratio, explicit_zero, initial_nonzero]
  have ratio_endpoint : ratio endpointTime = 1 := by
    rw [ratio_constant, ratio_zero]
  have solution_eq_explicit : solution endpointTime = explicit endpointTime := by
    apply (div_eq_one_iff_eq (explicit_nonzero endpointTime)).mp
    exact ratio_endpoint
  have explicit_endpoint :
      explicit endpointTime =
        solution 0 * carrier.multiplier ^ (weight * turns) := by
    change scaled.continuedValue (solution 0)
        ((turns : ℝ) * (2 * Real.pi)) = _
    rw [scaled.continuedValue_nat_turns, natScaleCarrier_multiplier]
    rw [← pow_mul]
  have fixed_power : carrier.multiplier ^ (weight * turns) = 1 := by
    apply mul_left_cancel₀ initial_nonzero
    calc
      solution 0 * carrier.multiplier ^ (weight * turns) =
          explicit endpointTime := explicit_endpoint.symm
      _ = solution endpointTime := solution_eq_explicit.symm
      _ = solution 0 := single_valued_return
      _ = solution 0 * 1 := by simp
  exact multiplier_non_torsion (weight * turns)
    (Nat.mul_pos weight_positive turns_positive) fixed_power

end FormalSingleValuedEigenrowMonodromy
