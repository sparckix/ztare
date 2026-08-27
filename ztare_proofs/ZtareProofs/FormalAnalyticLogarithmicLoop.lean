import Mathlib.MeasureTheory.Integral.CircleIntegral
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic

/-!
# Explicit continuation of a logarithmic scalar connection around a circle

A simple pole contributes its residue times the angular differential.  A
regular summand contributes the derivative of a single-valued primitive and
therefore returns to its initial value after every complete turn.  This file
constructs the resulting scalar-ODE path and derives its endpoint orbit.

The carrier contains no endpoint multiplier equation and no orbit conclusion.
-/

namespace FormalAnalyticLogarithmicLoop

open Complex

/-- Data available before continuing a logarithmic scalar connection around
one circle.  The regular primitive is required only on the circle itself. -/
structure LogarithmicCircleCarrier where
  center : ℂ
  radius : ℝ
  radius_ne_zero : radius ≠ 0
  residue : ℂ
  regularCoefficient : ℂ → ℂ
  regularPrimitive : ℂ → ℂ
  regularPrimitive_derivative :
    ∀ theta : ℝ,
      HasDerivAt regularPrimitive
        (regularCoefficient (circleMap center radius theta))
        (circleMap center radius theta)

/-- The logarithmic coefficient represented by the carrier. -/
noncomputable def LogarithmicCircleCarrier.coefficient
    (carrier : LogarithmicCircleCarrier) (z : ℂ) : ℂ :=
  carrier.residue / (z - carrier.center) + carrier.regularCoefficient z

/-- The exponent obtained by integrating the pole and the regular primitive
along the parameterized circle. -/
noncomputable def LogarithmicCircleCarrier.loopExponent
    (carrier : LogarithmicCircleCarrier) (theta : ℝ) : ℂ :=
  carrier.residue * I * (theta : ℂ) +
    carrier.regularPrimitive
      (circleMap carrier.center carrier.radius theta) -
    carrier.regularPrimitive
      (circleMap carrier.center carrier.radius 0)

/-- Explicit scalar continuation with a prescribed initial value. -/
noncomputable def LogarithmicCircleCarrier.continuedValue
    (carrier : LogarithmicCircleCarrier) (initial : ℂ) (theta : ℝ) : ℂ :=
  initial * exp (carrier.loopExponent theta)

/-- Monodromy multiplier contributed by the logarithmic residue. -/
noncomputable def LogarithmicCircleCarrier.multiplier
    (carrier : LogarithmicCircleCarrier) : ℂ :=
  exp ((2 * Real.pi : ℂ) * I * carrier.residue)

/-- The scalar continuation starts at the prescribed value. -/
@[simp] theorem LogarithmicCircleCarrier.continuedValue_zero
    (carrier : LogarithmicCircleCarrier) (initial : ℂ) :
    carrier.continuedValue initial 0 = initial := by
  simp [continuedValue, loopExponent]

/-- On the circle, multiplication by the circle tangent cancels the simple
pole and leaves the constant angular contribution `residue * I`. -/
theorem LogarithmicCircleCarrier.coefficient_mul_circle_tangent
    (carrier : LogarithmicCircleCarrier) (theta : ℝ) :
    carrier.coefficient
          (circleMap carrier.center carrier.radius theta) *
        (circleMap 0 carrier.radius theta * I) =
      carrier.residue * I +
        carrier.regularCoefficient
            (circleMap carrier.center carrier.radius theta) *
          (circleMap 0 carrier.radius theta * I) := by
  have hcircle : circleMap 0 carrier.radius theta ≠ 0 := by
    simpa [circleMap_zero] using
      mul_ne_zero (Complex.ofReal_ne_zero.mpr carrier.radius_ne_zero)
        (Complex.exp_ne_zero ((theta : ℂ) * I))
  unfold coefficient
  rw [circleMap_sub_center]
  field_simp [hcircle]

/-- The explicit continuation solves the coefficient pulled back along the
circle.  This is the continuation statement consumed by the endpoint law. -/
theorem LogarithmicCircleCarrier.continuedValue_hasDerivAt
    (carrier : LogarithmicCircleCarrier) (initial : ℂ) (theta : ℝ) :
    HasDerivAt (carrier.continuedValue initial)
      (carrier.coefficient
          (circleMap carrier.center carrier.radius theta) *
        (circleMap 0 carrier.radius theta * I) *
        carrier.continuedValue initial theta)
      theta := by
  have hlinear : HasDerivAt
      (fun x : ℝ => carrier.residue * I * (x : ℂ))
      (carrier.residue * I) theta := by
    simpa only [Complex.ofRealCLM_apply, Complex.ofReal_one, mul_one] using
      (Complex.ofRealCLM.hasDerivAt.const_mul (carrier.residue * I))
  have hprimitive : HasDerivAt
      (fun x : ℝ => carrier.regularPrimitive
        (circleMap carrier.center carrier.radius x))
      (carrier.regularCoefficient
          (circleMap carrier.center carrier.radius theta) *
        (circleMap 0 carrier.radius theta * I)) theta := by
    exact (carrier.regularPrimitive_derivative theta).comp theta
      (hasDerivAt_circleMap carrier.center carrier.radius theta)
  have hexponent : HasDerivAt carrier.loopExponent
      (carrier.residue * I +
        carrier.regularCoefficient
            (circleMap carrier.center carrier.radius theta) *
          (circleMap 0 carrier.radius theta * I)) theta := by
    simpa only [loopExponent] using
      (hlinear.add hprimitive).sub_const
        (carrier.regularPrimitive
          (circleMap carrier.center carrier.radius 0))
  have hsolution := (hexponent.cexp.const_mul initial)
  convert hsolution using 1
  rw [carrier.coefficient_mul_circle_tangent theta]
  simp only [continuedValue]
  ring

/-- A natural number of turns returns the circle and its regular primitive to
the starting point. -/
theorem LogarithmicCircleCarrier.circle_nat_turns
    (carrier : LogarithmicCircleCarrier) (turns : ℕ) :
    circleMap carrier.center carrier.radius
        ((turns : ℝ) * (2 * Real.pi)) =
      circleMap carrier.center carrier.radius 0 := by
  exact (periodic_circleMap carrier.center carrier.radius).nat_mul_eq turns

/-- Exact endpoint after any natural number of turns. -/
theorem LogarithmicCircleCarrier.continuedValue_nat_turns
    (carrier : LogarithmicCircleCarrier) (initial : ℂ) (turns : ℕ) :
    carrier.continuedValue initial ((turns : ℝ) * (2 * Real.pi)) =
      initial * carrier.multiplier ^ turns := by
  rw [continuedValue, loopExponent, carrier.circle_nat_turns turns]
  simp only [multiplier]
  congr 1
  rw [← Complex.exp_nat_mul]
  congr 1
  push_cast
  ring

/-- A non-torsion nonzero multiplier has pairwise distinct natural powers. -/
theorem powers_injective_of_positive_pow_ne_one
    (multiplier : ℂ) (hmultiplier : multiplier ≠ 0)
    (hnontorsion : ∀ N : ℕ, 0 < N → multiplier ^ N ≠ 1) :
    Function.Injective (fun N : ℕ => multiplier ^ N) := by
  intro m n hmn
  change multiplier ^ m = multiplier ^ n at hmn
  have hlt_impossible : ∀ {a b : ℕ}, a < b →
      multiplier ^ a = multiplier ^ b → False := by
    intro a b hab hpowers
    have hsplit : multiplier ^ a * multiplier ^ (b - a) =
        multiplier ^ a := by
      calc
        multiplier ^ a * multiplier ^ (b - a) =
            multiplier ^ (a + (b - a)) := (pow_add _ _ _).symm
        _ = multiplier ^ b := by
          rw [Nat.add_sub_of_le (Nat.le_of_lt hab)]
        _ = multiplier ^ a := hpowers.symm
    have hpow : multiplier ^ (b - a) = 1 := by
      exact mul_left_cancel₀ (pow_ne_zero a hmultiplier)
        (by simpa using hsplit)
    exact hnontorsion (b - a) (Nat.sub_pos_of_lt hab) hpow
  rcases Nat.lt_trichotomy m n with hlt | heq | hgt
  · exact (hlt_impossible hlt hmn).elim
  · exact heq
  · exact (hlt_impossible hgt hmn.symm).elim

/-- Under positive-power non-torsion, the constructed continuation endpoints
form an infinite orbit. -/
theorem LogarithmicCircleCarrier.endpoint_orbit_injective
    (carrier : LogarithmicCircleCarrier) (initial : ℂ)
    (hinitial : initial ≠ 0)
    (hnontorsion : ∀ N : ℕ, 0 < N → carrier.multiplier ^ N ≠ 1) :
    Function.Injective
      (fun N : ℕ =>
        carrier.continuedValue initial ((N : ℝ) * (2 * Real.pi))) := by
  intro m n hmn
  change carrier.continuedValue initial ((m : ℝ) * (2 * Real.pi)) =
    carrier.continuedValue initial ((n : ℝ) * (2 * Real.pi)) at hmn
  rw [carrier.continuedValue_nat_turns initial m,
    carrier.continuedValue_nat_turns initial n] at hmn
  have hpowers : carrier.multiplier ^ m = carrier.multiplier ^ n :=
    mul_left_cancel₀ hinitial hmn
  exact powers_injective_of_positive_pow_ne_one carrier.multiplier
    (Complex.exp_ne_zero _) hnontorsion hpowers

/-- Aggregated general-purpose continuation certificate. -/
theorem analytic_logarithmic_loop_terminal_certificate :
    ∀ (carrier : LogarithmicCircleCarrier) (initial : ℂ),
      initial ≠ 0 →
      (∀ N : ℕ, 0 < N → carrier.multiplier ^ N ≠ 1) →
      (∀ theta : ℝ,
        HasDerivAt (carrier.continuedValue initial)
          (carrier.coefficient
              (circleMap carrier.center carrier.radius theta) *
            (circleMap 0 carrier.radius theta * I) *
            carrier.continuedValue initial theta)
          theta) ∧
      (∀ N : ℕ,
        carrier.continuedValue initial ((N : ℝ) * (2 * Real.pi)) =
          initial * carrier.multiplier ^ N) ∧
      Function.Injective
        (fun N : ℕ =>
          carrier.continuedValue initial ((N : ℝ) * (2 * Real.pi))) := by
  intro carrier initial hinitial hnontorsion
  exact ⟨carrier.continuedValue_hasDerivAt initial,
    carrier.continuedValue_nat_turns initial,
    carrier.endpoint_orbit_injective initial hinitial hnontorsion⟩

end FormalAnalyticLogarithmicLoop
