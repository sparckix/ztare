import Mathlib.Tactic
import ZtareProofs.FormalCriticalHolonomyLoop
import ZtareProofs.FormalSingleValuedEigenrowMonodromy

/-!
# Binding a single-valued critical cross row to the loop obstruction

Two single-valued coefficient functions satisfying the specialized
cross-weight row on the exact critical circle have a quotient solving the
weighted logarithmic loop equation.  Circle periodicity supplies the return
identity, so positive-power non-torsion gives a contradiction.

This is the one-sheet analytic adapter.  It does not construct a finite
algebraic cover or realize an abstract coefficient-field derivation as a
pointwise complex derivative.
-/

namespace FormalCriticalCrossWeightLoopBinding

open Complex

open FormalAnalyticLogarithmicLoop
open FormalCriticalHolonomyLoop
open FormalSingleValuedEigenrowMonodromy

/-- A positive critical cross-weight row cannot be carried by two
single-valued coefficient functions on a compatible critical circle. -/
theorem no_single_valued_critical_cross_weight_row
    (realization : CriticalLoopRealization)
    (weight : ℕ) (weight_positive : 0 < weight)
    (first second firstDerivative secondDerivative : ℂ → ℂ)
    (first_hasDerivAt : ∀ theta : ℝ,
      HasDerivAt first
        (firstDerivative
          (circleMap realization.carrier.center
            realization.carrier.radius theta))
        (circleMap realization.carrier.center
          realization.carrier.radius theta))
    (second_hasDerivAt : ∀ theta : ℝ,
      HasDerivAt second
        (secondDerivative
          (circleMap realization.carrier.center
            realization.carrier.radius theta))
        (circleMap realization.carrier.center
          realization.carrier.radius theta))
    (cross_weight_row : ∀ theta : ℝ,
      let z := circleMap realization.carrier.center
        realization.carrier.radius theta
      second z * firstDerivative z - first z * secondDerivative z =
        (weight : ℂ) * criticalCoefficient z * first z * second z)
    (first_initial_nonzero :
      first (circleMap realization.carrier.center
        realization.carrier.radius 0) ≠ 0)
    (second_nonzero : ∀ theta : ℝ,
      second (circleMap realization.carrier.center
        realization.carrier.radius theta) ≠ 0) :
    False := by
  let solution : ℝ → ℂ := fun theta =>
    first (circleMap realization.carrier.center
        realization.carrier.radius theta) /
      second (circleMap realization.carrier.center
        realization.carrier.radius theta)
  have solution_ode : ∀ theta : ℝ,
      HasDerivAt solution
        ((weight : ℂ) *
          realization.carrier.coefficient
            (circleMap realization.carrier.center
              realization.carrier.radius theta) *
          (circleMap 0 realization.carrier.radius theta * I) *
          solution theta)
        theta := by
    intro theta
    let z := circleMap realization.carrier.center
      realization.carrier.radius theta
    let tangent := circleMap 0 realization.carrier.radius theta * I
    have hcircle : HasDerivAt
        (circleMap realization.carrier.center realization.carrier.radius)
        tangent theta := by
      simpa [tangent] using
        hasDerivAt_circleMap realization.carrier.center
          realization.carrier.radius theta
    have hfirst : HasDerivAt
        (fun angle => first
          (circleMap realization.carrier.center
            realization.carrier.radius angle))
        (firstDerivative z * tangent) theta := by
      exact (first_hasDerivAt theta).comp theta hcircle
    have hsecond : HasDerivAt
        (fun angle => second
          (circleMap realization.carrier.center
            realization.carrier.radius angle))
        (secondDerivative z * tangent) theta := by
      exact (second_hasDerivAt theta).comp theta hcircle
    have hquotient := hfirst.div hsecond (second_nonzero theta)
    have hrow := cross_weight_row theta
    dsimp only at hrow
    rw [← realization.coefficient_on_circle theta] at hrow
    have hderivative :
        (firstDerivative z * tangent * second z -
              first z * (secondDerivative z * tangent)) /
            second z ^ 2 =
          (weight : ℂ) * realization.carrier.coefficient z * tangent *
            (first z / second z) := by
      calc
        (firstDerivative z * tangent * second z -
                first z * (secondDerivative z * tangent)) /
              second z ^ 2 =
            tangent *
                (second z * firstDerivative z -
                  first z * secondDerivative z) /
              second z ^ 2 := by ring
        _ = tangent *
                ((weight : ℂ) * realization.carrier.coefficient z *
                  first z * second z) /
              second z ^ 2 := by rw [hrow]
        _ = (weight : ℂ) * realization.carrier.coefficient z * tangent *
              (first z / second z) := by
          field_simp [second_nonzero theta]
    change HasDerivAt
      (fun angle =>
        first (circleMap realization.carrier.center
            realization.carrier.radius angle) /
          second (circleMap realization.carrier.center
            realization.carrier.radius angle))
      _ theta
    convert hquotient using 1
    simpa only [z, tangent] using hderivative.symm
  have solution_initial_nonzero : solution 0 ≠ 0 := by
    exact div_ne_zero first_initial_nonzero (second_nonzero 0)
  have solution_return :
      solution (((1 : ℕ) : ℝ) * (2 * Real.pi)) = solution 0 := by
    dsimp only [solution]
    rw [realization.carrier.circle_nat_turns 1]
  exact no_single_valued_positive_weight_solution
    realization.carrier weight 1 weight_positive (by norm_num)
    solution solution_ode solution_initial_nonzero solution_return
    realization.multiplier_non_torsion

end FormalCriticalCrossWeightLoopBinding
