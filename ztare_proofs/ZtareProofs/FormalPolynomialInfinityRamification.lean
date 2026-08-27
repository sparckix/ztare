import ZtareProofs.FormalAnalyticPowerNormalForm
import ZtareProofs.FormalPolynomialInfinityTimeCoordinate

/-!
# Constructed ramified infinity coordinate for a polynomial flow

This file composes the polynomial reciprocal-time constructor with the
analytic power normal form.  It constructs the finite ramification and its
analytic inverse directly from the polynomial generator.
-/

namespace FormalPolynomialInfinityRamification

open Filter Polynomial
open scoped Topology
open FormalAnalyticPowerNormalForm
open FormalPolynomialInfinityTimeCoordinate

/-- Every complex polynomial of exact degree at least two constructs an
analytic infinity time coordinate, its exact positive order, an exact power
normal form, and an analytic inverse ramification coordinate. -/
theorem polynomial_infinity_ramification_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ),
      p.natDegree = degree →
      2 ≤ degree →
      ∃ (timeCoordinate : ℂ → ℂ) (unit : ℂ)
        (coordinate inverseCoordinate : ℂ → ℂ),
        AnalyticAt ℂ timeCoordinate 0 ∧
        timeCoordinate 0 = 0 ∧
        (∀ᶠ z in 𝓝 0,
          HasDerivAt timeCoordinate
            (reciprocalTimeIntegrand p degree z) z) ∧
        analyticOrderAt timeCoordinate 0 = (degree - 1 : ℕ) ∧
        degree - 1 ≠ 0 ∧
        unit ≠ 0 ∧
        AnalyticAt ℂ coordinate 0 ∧
        coordinate 0 = 0 ∧
        deriv coordinate 0 = 1 ∧
        (timeCoordinate =ᶠ[𝓝 0]
          fun z ↦ unit * coordinate z ^ (degree - 1)) ∧
        AnalyticAt ℂ inverseCoordinate 0 ∧
        inverseCoordinate 0 = 0 ∧
        (∀ᶠ w in 𝓝 0, coordinate (inverseCoordinate w) = w) := by
  intro p degree hdegree htwo
  obtain ⟨timeCoordinate, htimeAnalytic, htimeZero, htimeDerivative,
      htimeOrder, hpositive⟩ :=
    polynomial_infinity_time_coordinate_terminal_certificate
      p degree hdegree htwo
  obtain ⟨unit, coordinate, inverseCoordinate, hunit,
      hcoordinateAnalytic, hcoordinateZero, hcoordinateDerivative,
      hnormal, hinverseAnalytic, hinverseZero, hrightInverse⟩ :=
    analytic_power_normal_form_terminal_certificate
      timeCoordinate 0 (degree - 1) htimeAnalytic htimeOrder hpositive
  exact ⟨timeCoordinate, unit, coordinate, inverseCoordinate,
    htimeAnalytic, htimeZero, htimeDerivative, htimeOrder, hpositive, hunit,
    hcoordinateAnalytic, hcoordinateZero, hcoordinateDerivative, hnormal,
    hinverseAnalytic, hinverseZero, hrightInverse⟩

end FormalPolynomialInfinityRamification
