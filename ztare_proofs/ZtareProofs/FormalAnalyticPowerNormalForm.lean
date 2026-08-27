import Mathlib.Analysis.Analytic.Order
import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Analysis.SpecialFunctions.Complex.Analytic
import Mathlib.Tactic

/-!
# Analytic power normal form and ramified inverse coordinate

A complex analytic germ of finite positive order is a nonzero constant times
an exact power of an analytic coordinate with derivative one.  The proof
constructs the root of the analytic unit using complex `cpow` at the
normalized value one, and then constructs the inverse coordinate by the
analytic inverse-function theorem.
-/

namespace FormalAnalyticPowerNormalForm

open Filter
open scoped Topology

/-- A finite positive-order complex analytic germ admits an exact power
normal form in an analytic coordinate tangent to the identity. -/
theorem exists_analytic_power_coordinate
    {timeCoordinate : ℂ → ℂ} {center : ℂ} {order : ℕ}
    (hanalytic : AnalyticAt ℂ timeCoordinate center)
    (horder : analyticOrderAt timeCoordinate center = order)
    (hpositive : order ≠ 0) :
    ∃ (unit : ℂ) (coordinate : ℂ → ℂ),
      unit ≠ 0 ∧
      AnalyticAt ℂ coordinate center ∧
      coordinate center = 0 ∧
      deriv coordinate center = 1 ∧
      timeCoordinate =ᶠ[𝓝 center]
        fun z ↦ unit * coordinate z ^ order := by
  obtain ⟨g, hganalytic, hgcenter, hfactor⟩ :=
    hanalytic.analyticOrderAt_eq_natCast.mp horder
  let normalizedUnit : ℂ → ℂ := fun z ↦ g z / g center
  have hnormalizedAnalytic :
      AnalyticAt ℂ normalizedUnit center := by
    exact hganalytic.div analyticAt_const hgcenter
  have hnormalizedCenter : normalizedUnit center = 1 := by
    simp [normalizedUnit, hgcenter]
  let rootUnit : ℂ → ℂ := fun z ↦
    normalizedUnit z ^ ((order : ℂ)⁻¹)
  have hrootAnalytic : AnalyticAt ℂ rootUnit center := by
    exact hnormalizedAnalytic.cpow analyticAt_const
      (by simpa [hnormalizedCenter] using Complex.one_mem_slitPlane)
  have hrootCenter : rootUnit center = 1 := by
    simp [rootUnit, hnormalizedCenter]
  have hrootPower : ∀ z, rootUnit z ^ order = normalizedUnit z := by
    intro z
    exact Complex.cpow_nat_inv_pow (normalizedUnit z) hpositive
  let coordinate : ℂ → ℂ := fun z ↦ (z - center) * rootUnit z
  have hcoordinateAnalytic : AnalyticAt ℂ coordinate center := by
    exact (analyticAt_id.sub analyticAt_const).mul hrootAnalytic
  have hcoordinateCenter : coordinate center = 0 := by
    simp [coordinate]
  have hcoordinateDerivative : deriv coordinate center = 1 := by
    have hleft : HasDerivAt (fun z : ℂ ↦ z - center) 1 center :=
      (hasDerivAt_id center).sub_const center
    have hproduct := hleft.mul hrootAnalytic.differentiableAt.hasDerivAt
    have hcoordinateHasDeriv : HasDerivAt coordinate 1 center := by
      simpa [coordinate, hrootCenter] using hproduct
    exact hcoordinateHasDeriv.deriv
  refine ⟨g center, coordinate, hgcenter, hcoordinateAnalytic,
    hcoordinateCenter, hcoordinateDerivative, ?_⟩
  filter_upwards [hfactor] with z hz
  rw [hz]
  simp only [smul_eq_mul]
  rw [show coordinate z = (z - center) * rootUnit z by rfl, mul_pow,
    hrootPower]
  rw [show normalizedUnit z = g z / g center by rfl]
  field_simp

/-- The power coordinate has an analytic local inverse at zero.  This is the
finite-ramification inversion mechanism used by reciprocal infinity charts. -/
theorem analytic_power_normal_form_terminal_certificate :
    ∀ (timeCoordinate : ℂ → ℂ) (center : ℂ) (order : ℕ),
      AnalyticAt ℂ timeCoordinate center →
      analyticOrderAt timeCoordinate center = order →
      order ≠ 0 →
      ∃ (unit : ℂ) (coordinate inverseCoordinate : ℂ → ℂ),
        unit ≠ 0 ∧
        AnalyticAt ℂ coordinate center ∧
        coordinate center = 0 ∧
        deriv coordinate center = 1 ∧
        (timeCoordinate =ᶠ[𝓝 center]
          fun z ↦ unit * coordinate z ^ order) ∧
        AnalyticAt ℂ inverseCoordinate 0 ∧
        inverseCoordinate 0 = center ∧
        (∀ᶠ w in 𝓝 0, coordinate (inverseCoordinate w) = w) := by
  intro timeCoordinate center order hanalytic horder hpositive
  obtain ⟨unit, coordinate, hunit, hcoordinateAnalytic,
      hcoordinateCenter, hcoordinateDerivative, hnormal⟩ :=
    exists_analytic_power_coordinate hanalytic horder hpositive
  have hderivativeNonzero : deriv coordinate center ≠ 0 := by
    simpa [hcoordinateDerivative]
  have hstrict :
      HasStrictDerivAt coordinate (deriv coordinate center) center :=
    hcoordinateAnalytic.hasStrictDerivAt
  let inverseCoordinate :=
    hstrict.localInverse
      coordinate (deriv coordinate center) center hderivativeNonzero
  have hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0 := by
    simpa [inverseCoordinate, hcoordinateCenter] using
      hcoordinateAnalytic.analyticAt_localInverse hderivativeNonzero
  have hinverseCenter : inverseCoordinate 0 = center := by
    have himage :=
      (hstrict.eventually_left_inverse hderivativeNonzero).self_of_nhds
    simpa [inverseCoordinate, hcoordinateCenter] using himage
  have hrightInverse :
      ∀ᶠ w in 𝓝 0, coordinate (inverseCoordinate w) = w := by
    simpa [inverseCoordinate, hcoordinateCenter] using
      hstrict.eventually_right_inverse hderivativeNonzero
  exact ⟨unit, coordinate, inverseCoordinate, hunit,
    hcoordinateAnalytic, hcoordinateCenter, hcoordinateDerivative, hnormal,
    hinverseAnalytic, hinverseCenter, hrightInverse⟩

end FormalAnalyticPowerNormalForm
