import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Normed.Module.Ball.Pointwise
import Mathlib.Analysis.Normed.Module.Connected
import Mathlib.LinearAlgebra.Complex.FiniteDimensional
import Mathlib.Topology.Separation.Hausdorff
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialInfinityRamification
import ZtareProofs.FormalPolynomialTimeSeparation
import ZtareProofs.FormalSelectedRamifiedInverse

/-!
# Selected ramified sheets for polynomial flows

A ramified trajectory at polynomial infinity is a function on a selected
uniformizing sheet, not a single-valued function of the base-time variable.
The sheet projects to base time by

`w ↦ infinityTime + unit * w ^ order`

and its reciprocal coordinate satisfies the polynomial ODE pulled back along
that projection.  This file proves reciprocal-time separation directly on
the sheet and identifies the normalized sheet germ with the constructed
analytic inverse coordinate.

No existence, continuation, finite-chart overlap, or route-exhaustiveness
claim is made here.
-/

namespace FormalPolynomialRamifiedTrajectorySheet

open Filter Pointwise Polynomial Set
open scoped Topology

open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialInfinityRamification
open FormalPolynomialTimeSeparation
open FormalSelectedRamifiedInverse

/-- Projection from a selected uniformizing sheet to the base-time plane. -/
def ramifiedTimeProjection
    (infinityTime unit : ℂ) (order : ℕ) : ℂ → ℂ :=
  fun w ↦ infinityTime + unit * w ^ order

/-- Derivative of the ramified time projection. -/
def ramifiedTimeProjectionDerivative
    (unit : ℂ) (order : ℕ) : ℂ → ℂ :=
  fun w ↦ unit * (order : ℂ) * w ^ (order - 1)

/-- A nonempty punctured complex ball is preconnected.  The proof realizes it
as the scalar-multiplication image of a radial interval times the unit
sphere. -/
theorem isPreconnected_complex_puncturedBall
    (radius : ℝ) :
    IsPreconnected
      (Metric.ball (0 : ℂ) radius \ {0}) := by
  have hsphere : IsPreconnected (Metric.sphere (0 : ℂ) 1) :=
    isPreconnected_sphere
      (Complex.rank_real_complex ▸ Nat.one_lt_ofNat) 0 1
  have hproduct : IsPreconnected
      (Set.Ioo (0 : ℝ) radius ×ˢ Metric.sphere (0 : ℂ) 1) :=
    isPreconnected_Ioo.prod hsphere
  have hcontinuous : Continuous
      (fun pair : ℝ × ℂ ↦ pair.1 • pair.2) := by
    change Continuous (fun pair : ℝ × ℂ ↦ (pair.1 : ℂ) * pair.2)
    exact (Complex.continuous_ofReal.comp continuous_fst).mul continuous_snd
  have himage := hproduct.image
    (fun pair : ℝ × ℂ ↦ pair.1 • pair.2)
      hcontinuous.continuousOn
  rw [Set.image_prod] at himage
  change IsPreconnected
    (Set.Ioo (0 : ℝ) radius • Metric.sphere (0 : ℂ) 1) at himage
  have hradial := Ioo_smul_sphere_zero
    (E := ℂ) (a := 0) (b := radius) (r := 1)
    (by norm_num) (by norm_num)
  have hradial' :
      Set.Ioo (0 : ℝ) radius • Metric.sphere (0 : ℂ) 1 =
        Metric.ball 0 radius \ {0} := by
    simpa using hradial
  rw [hradial'] at himage
  exact himage

/-- A selected reciprocal trajectory on a punctured ramified sheet.

The record owns its domain, anchor, and reciprocal coordinate.  Its ODE is
the polynomial reciprocal vector field pulled back by the derivative of the
sheet-to-time projection. -/
structure PolynomialRamifiedTrajectorySheet
    (p : ℂ[X]) (degree : ℕ) (timeCoordinate : ℂ → ℂ)
    (infinityTime unit : ℂ) (order : ℕ) where
  domain : Set ℂ
  anchor : ℂ
  reciprocal : ℂ → ℂ
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  punctured_mem : domain ∈ 𝓝[≠] (0 : ℂ)
  analytic_reciprocal : AnalyticAt ℂ reciprocal 0
  reciprocal_zero : reciprocal 0 = 0
  reciprocal_derivative : deriv reciprocal 0 = 1
  time_derivative : ∀ w ∈ domain,
    HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocal w))
      (reciprocal w)
  pulledBack_derivative : ∀ w ∈ domain,
    HasDerivAt reciprocal
      (ramifiedTimeProjectionDerivative unit order w *
        reciprocalVectorField p degree (reciprocal w)) w
  reciprocal_nonzero : ∀ w ∈ domain, reciprocal w ≠ 0
  reverse_nonzero : ∀ w ∈ domain,
    p.reverse.eval (reciprocal w) ≠ 0

/-- The local infinity sheet together with the normal-form data constructed
from its polynomial generator. -/
structure ConstructedPolynomialInfinitySheet
    (p : ℂ[X]) (degree : ℕ) (infinityTime : ℂ) where
  timeCoordinate : ℂ → ℂ
  unit : ℂ
  coordinate : ℂ → ℂ
  inverseCoordinate : ℂ → ℂ
  sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
    infinityTime unit (degree - 1)
  timeAnalytic : AnalyticAt ℂ timeCoordinate 0
  timeZero : timeCoordinate 0 = 0
  timeDerivative : ∀ᶠ z in 𝓝 0,
    HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree z) z
  unit_nonzero : unit ≠ 0
  coordinateAnalytic : AnalyticAt ℂ coordinate 0
  coordinateZero : coordinate 0 = 0
  coordinateDerivative : deriv coordinate 0 = 1
  timeNormalForm : timeCoordinate =ᶠ[𝓝 0]
    fun z ↦ unit * coordinate z ^ (degree - 1)
  inverseAnalytic : AnalyticAt ℂ inverseCoordinate 0
  inverseZero : inverseCoordinate 0 = 0
  coordinate_rightInverse : ∀ᶠ w in 𝓝 0,
    coordinate (inverseCoordinate w) = w
  sheet_reciprocal_eq_inverse : sheet.reciprocal = inverseCoordinate

/-- Construct the sheet record from inverse-coordinate data valid on one
explicit ball.  The differential equation is derived from the exact
ramified time identity and reciprocal cancellation. -/
noncomputable def PolynomialRamifiedTrajectorySheet.ofLocalInverse
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate inverseCoordinate : ℂ → ℂ}
    {infinityTime unit : ℂ} {order : ℕ} {radius : ℝ}
    (hradius : 0 < radius)
    (hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0)
    (hinverseZero : inverseCoordinate 0 = 0)
    (hinverseDerivative : deriv inverseCoordinate 0 = 1)
    (hinverseAnalyticOn : ∀ w ∈ Metric.ball (0 : ℂ) radius,
      AnalyticAt ℂ inverseCoordinate w)
    (htimeDerivative : ∀ w ∈ Metric.ball (0 : ℂ) radius \ {0},
      HasDerivAt timeCoordinate
        (reciprocalTimeIntegrand p degree (inverseCoordinate w))
        (inverseCoordinate w))
    (htimeIdentity : Set.EqOn
      (fun w ↦ timeCoordinate (inverseCoordinate w))
      (fun w ↦ unit * w ^ order)
      (Metric.ball (0 : ℂ) radius))
    (hinverseNonzero : ∀ w ∈ Metric.ball (0 : ℂ) radius \ {0},
      inverseCoordinate w ≠ 0)
    (hreverseNonzero : ∀ w ∈ Metric.ball (0 : ℂ) radius \ {0},
      p.reverse.eval (inverseCoordinate w) ≠ 0) :
    PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order := by
  let domain := Metric.ball (0 : ℂ) radius \ {0}
  let anchor : ℂ := (radius / 2 : ℝ)
  have hhalfPositive : 0 < radius / 2 := by positivity
  have hhalfLt : radius / 2 < radius := by linarith
  have hanchorBall : anchor ∈ Metric.ball (0 : ℂ) radius := by
    simpa [anchor, Metric.mem_ball, abs_of_pos hradius] using hhalfLt
  have hanchorNonzero : anchor ≠ 0 := by
    change ((radius / 2 : ℝ) : ℂ) ≠ 0
    exact_mod_cast ne_of_gt hhalfPositive
  have hanchor : anchor ∈ domain := ⟨hanchorBall, by simpa⟩
  have hpulledBack : ∀ w ∈ domain,
      HasDerivAt inverseCoordinate
        (ramifiedTimeProjectionDerivative unit order w *
          reciprocalVectorField p degree (inverseCoordinate w)) w := by
    intro w hw
    have hinverseHasDeriv :=
      (hinverseAnalyticOn w hw.1).differentiableAt.hasDerivAt
    have hchain := (htimeDerivative w hw).comp w hinverseHasDeriv
    have hpower : HasDerivAt (fun z : ℂ ↦ unit * z ^ order)
        (ramifiedTimeProjectionDerivative unit order w) w := by
      convert (hasDerivAt_pow order w).const_mul unit using 1
      simp only [ramifiedTimeProjectionDerivative]
      ring
    have hidentityNhd :
        (fun z ↦ timeCoordinate (inverseCoordinate z)) =ᶠ[𝓝 w]
          fun z ↦ unit * z ^ order := by
      filter_upwards [Metric.isOpen_ball.mem_nhds hw.1] with z hz
      exact htimeIdentity hz
    have hcomposition : HasDerivAt
        (fun z ↦ timeCoordinate (inverseCoordinate z))
        (ramifiedTimeProjectionDerivative unit order w) w :=
      hpower.congr_of_eventuallyEq hidentityNhd
    have hcoefficient := hchain.unique hcomposition
    have hcancel := reciprocalTimeIntegrand_mul_reciprocalVectorField
      p degree (hinverseNonzero w hw) (hreverseNonzero w hw)
    apply hinverseHasDeriv.congr_deriv
    calc
      deriv inverseCoordinate w =
          1 * deriv inverseCoordinate w := by ring
      _ = (reciprocalTimeIntegrand p degree (inverseCoordinate w) *
            reciprocalVectorField p degree (inverseCoordinate w)) *
          deriv inverseCoordinate w := by rw [hcancel]
      _ = reciprocalVectorField p degree (inverseCoordinate w) *
          (reciprocalTimeIntegrand p degree (inverseCoordinate w) *
            deriv inverseCoordinate w) := by ring
      _ = reciprocalVectorField p degree (inverseCoordinate w) *
          ramifiedTimeProjectionDerivative unit order w := by
            rw [hcoefficient]
      _ = ramifiedTimeProjectionDerivative unit order w *
          reciprocalVectorField p degree (inverseCoordinate w) := by ring
  exact {
    domain := domain
    anchor := anchor
    reciprocal := inverseCoordinate
    isOpen_domain := Metric.isOpen_ball.sdiff isClosed_singleton
    isPreconnected_domain := isPreconnected_complex_puncturedBall radius
    anchor_mem := hanchor
    punctured_mem := diff_mem_nhdsWithin_compl
      (Metric.ball_mem_nhds (0 : ℂ) hradius) {0}
    analytic_reciprocal := hinverseAnalytic
    reciprocal_zero := hinverseZero
    reciprocal_derivative := hinverseDerivative
    time_derivative := htimeDerivative
    pulledBack_derivative := hpulledBack
    reciprocal_nonzero := hinverseNonzero
    reverse_nonzero := hreverseNonzero
  }

/-- Every complex polynomial of exact degree at least two constructs a local
ramified infinity sheet.  The statement remains local: it does not identify
the sheet with an analytic continuation arriving from a finite trajectory. -/
theorem polynomial_infinity_local_sheet_exists_terminal_certificate
    (p : ℂ[X]) (degree : ℕ) (infinityTime : ℂ)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree) :
    Nonempty (ConstructedPolynomialInfinitySheet p degree infinityTime) := by
  obtain ⟨timeCoordinate, unit, coordinate, inverseCoordinate,
      htimeAnalytic, htimeZero, htimeDerivative, _htimeOrder, hpositive,
      hunit, hcoordinateAnalytic, hcoordinateZero, hcoordinateDerivative,
      hnormal, hinverseAnalytic, hinverseZero, hrightInverse⟩ :=
    polynomial_infinity_ramification_terminal_certificate
      p degree hdegree htwo
  have hinverseTendsto : Tendsto inverseCoordinate (𝓝 0) (𝓝 0) := by
    have hcontinuous := hinverseAnalytic.continuousAt
    change Tendsto inverseCoordinate (𝓝 0)
      (𝓝 (inverseCoordinate 0)) at hcontinuous
    simpa only [hinverseZero] using hcontinuous
  have htimeAtInverse : ∀ᶠ w in 𝓝 0,
      HasDerivAt timeCoordinate
        (reciprocalTimeIntegrand p degree (inverseCoordinate w))
        (inverseCoordinate w) :=
    hinverseTendsto htimeDerivative
  have hnormalAtInverse : ∀ᶠ w in 𝓝 0,
      timeCoordinate (inverseCoordinate w) =
        unit * coordinate (inverseCoordinate w) ^ (degree - 1) := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hnormal hinverseTendsto
  have htimeIdentity : ∀ᶠ w in 𝓝 0,
      timeCoordinate (inverseCoordinate w) =
        unit * w ^ (degree - 1) := by
    filter_upwards [hnormalAtInverse, hrightInverse] with w hnormalW hrightW
    simpa only [hrightW] using hnormalW
  have hinverseNonzero : ∀ᶠ w in 𝓝 0,
      w ≠ 0 → inverseCoordinate w ≠ 0 := by
    filter_upwards [hrightInverse] with w hrightW hw
    intro hinverseW
    apply hw
    calc
      w = coordinate (inverseCoordinate w) := hrightW.symm
      _ = coordinate 0 := by rw [hinverseW]
      _ = 0 := hcoordinateZero
  have hp : p ≠ 0 := by
    intro hpzero
    simp [hpzero] at hdegree
    omega
  have hreverseZero : p.reverse.eval 0 ≠ 0 := by
    have hleading : p.leadingCoeff ≠ 0 := leadingCoeff_ne_zero.mpr hp
    simpa only [← Polynomial.coeff_zero_eq_eval_zero,
      Polynomial.coeff_zero_reverse] using hleading
  have hreverseAnalytic :
      AnalyticAt ℂ (fun w ↦ p.reverse.eval (inverseCoordinate w)) 0 := by
    have hevalAnalytic :
        AnalyticAt ℂ (fun z : ℂ ↦ p.reverse.eval z) 0 :=
      (AnalyticOnNhd.eval_polynomial p.reverse) 0 (by simp)
    exact hevalAnalytic.comp_of_eq hinverseAnalytic hinverseZero
  have hreverseAtInverse : ∀ᶠ w in 𝓝 0,
      p.reverse.eval (inverseCoordinate w) ≠ 0 := by
    apply hreverseAnalytic.continuousAt.eventually_ne
    simpa only [hinverseZero] using hreverseZero
  have hinverseDerivative : deriv inverseCoordinate 0 = 1 := by
    have hcoordinateHasDeriv : HasDerivAt coordinate 1 0 := by
      simpa only [hcoordinateDerivative] using
        hcoordinateAnalytic.differentiableAt.hasDerivAt
    have hinverseHasDeriv : HasDerivAt inverseCoordinate
        (deriv inverseCoordinate 0) 0 :=
      hinverseAnalytic.differentiableAt.hasDerivAt
    have hcoordinateAtInverse : HasDerivAt coordinate 1
        (inverseCoordinate 0) := by
      simpa only [hinverseZero] using hcoordinateHasDeriv
    have hcomposition :=
      (hcoordinateAtInverse.comp 0 hinverseHasDeriv).deriv
    have hrightFunctions :
        (coordinate ∘ inverseCoordinate) =ᶠ[𝓝 0] fun w ↦ w := by
      simpa only [Function.comp_apply] using hrightInverse
    calc
      deriv inverseCoordinate 0 = 1 * deriv inverseCoordinate 0 := by ring
      _ = deriv (coordinate ∘ inverseCoordinate) 0 := hcomposition.symm
      _ = deriv (fun w : ℂ ↦ w) 0 := hrightFunctions.deriv_eq
      _ = 1 := by simp
  let good : Set ℂ := {w |
    AnalyticAt ℂ inverseCoordinate w ∧
    HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (inverseCoordinate w))
      (inverseCoordinate w) ∧
    timeCoordinate (inverseCoordinate w) =
      unit * w ^ (degree - 1) ∧
    (w ≠ 0 → inverseCoordinate w ≠ 0) ∧
    p.reverse.eval (inverseCoordinate w) ≠ 0}
  have hgood : good ∈ 𝓝 (0 : ℂ) := by
    filter_upwards [hinverseAnalytic.eventually_analyticAt,
      htimeAtInverse, htimeIdentity, hinverseNonzero,
      hreverseAtInverse] with w ha ht hi hn hr
    exact ⟨ha, ht, hi, hn, hr⟩
  obtain ⟨radius, hradius, hball⟩ := Metric.mem_nhds_iff.mp hgood
  let sheet := PolynomialRamifiedTrajectorySheet.ofLocalInverse
    p degree (infinityTime := infinityTime) hradius hinverseAnalytic
    hinverseZero hinverseDerivative
    (fun w hw ↦ (hball hw).1)
    (fun w hw ↦ (hball hw.1).2.1)
    (fun w hw ↦ (hball hw).2.2.1)
    (fun w hw ↦ (hball hw.1).2.2.2.1 hw.2)
    (fun w hw ↦ (hball hw.1).2.2.2.2)
  exact ⟨{
    timeCoordinate := timeCoordinate
    unit := unit
    coordinate := coordinate
    inverseCoordinate := inverseCoordinate
    sheet := sheet
    timeAnalytic := htimeAnalytic
    timeZero := htimeZero
    timeDerivative := htimeDerivative
    unit_nonzero := hunit
    coordinateAnalytic := hcoordinateAnalytic
    coordinateZero := hcoordinateZero
    coordinateDerivative := hcoordinateDerivative
    timeNormalForm := hnormal
    inverseAnalytic := hinverseAnalytic
    inverseZero := hinverseZero
    coordinate_rightInverse := hrightInverse
    sheet_reciprocal_eq_inverse := rfl
  }⟩

/-- Exact derivative of the sheet-to-time projection. -/
theorem hasDerivAt_ramifiedTimeProjection
    (infinityTime unit w : ℂ) (order : ℕ) :
    HasDerivAt (ramifiedTimeProjection infinityTime unit order)
      (ramifiedTimeProjectionDerivative unit order w) w := by
  convert
    ((hasDerivAt_pow order w).const_mul unit).const_add infinityTime using 1
  simp only [ramifiedTimeProjectionDerivative]
  ring

/-- Along a valid selected sheet, the reciprocal time coordinate advances at
the derivative of the sheet's time projection. -/
theorem hasDerivAt_timeCoordinate_comp_sheet
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate reciprocal : ℂ → ℂ}
    {unit w : ℂ} {order : ℕ}
    (htime : HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocal w)) (reciprocal w))
    (hsheet : HasDerivAt reciprocal
      (ramifiedTimeProjectionDerivative unit order w *
        reciprocalVectorField p degree (reciprocal w)) w)
    (hnonzero : reciprocal w ≠ 0)
    (hreverse : p.reverse.eval (reciprocal w) ≠ 0) :
    HasDerivAt (timeCoordinate ∘ reciprocal)
      (ramifiedTimeProjectionDerivative unit order w) w := by
  have hcancel := reciprocalTimeIntegrand_mul_reciprocalVectorField
    p degree hnonzero hreverse
  have hcoefficient :
      reciprocalTimeIntegrand p degree (reciprocal w) *
          (ramifiedTimeProjectionDerivative unit order w *
            reciprocalVectorField p degree (reciprocal w)) =
        ramifiedTimeProjectionDerivative unit order w := by
    calc
      reciprocalTimeIntegrand p degree (reciprocal w) *
          (ramifiedTimeProjectionDerivative unit order w *
            reciprocalVectorField p degree (reciprocal w)) =
        ramifiedTimeProjectionDerivative unit order w *
          (reciprocalTimeIntegrand p degree (reciprocal w) *
            reciprocalVectorField p degree (reciprocal w)) := by ring
      _ = ramifiedTimeProjectionDerivative unit order w := by
        rw [hcancel, mul_one]
  convert htime.comp w hsheet using 1
  exact hcoefficient.symm

/-- Reciprocal-time separation on a selected ramified sheet extends through
the sheet center and forces the exact power identity. -/
theorem timeCoordinate_comp_sheet_eq_power
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate : ℂ → ℂ} {infinityTime unit : ℂ} {order : ℕ}
    (sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order)
    (hpositive : order ≠ 0)
    (htimeAnalytic : AnalyticAt ℂ timeCoordinate 0)
    (htimeZero : timeCoordinate 0 = 0) :
    ∀ᶠ w in 𝓝 0,
      timeCoordinate (sheet.reciprocal w) = unit * w ^ order := by
  let projection := ramifiedTimeProjection infinityTime unit order
  let separated : ℂ → ℂ :=
    fun w ↦ timeCoordinate (sheet.reciprocal w) - projection w
  have hderivative : ∀ w ∈ sheet.domain,
      HasDerivAt separated 0 w := by
    intro w hw
    have htimeSheet := hasDerivAt_timeCoordinate_comp_sheet p degree
      (sheet.time_derivative w hw) (sheet.pulledBack_derivative w hw)
      (sheet.reciprocal_nonzero w hw) (sheet.reverse_nonzero w hw)
    have hprojection :=
      hasDerivAt_ramifiedTimeProjection infinityTime unit w order
    simpa only [separated, projection, Function.comp_apply, sub_self] using
      htimeSheet.sub hprojection
  have hdifferentiable : DifferentiableOn ℂ separated sheet.domain := by
    intro w hw
    exact (hderivative w hw).differentiableAt.differentiableWithinAt
  have hderivZero : sheet.domain.EqOn (deriv separated) 0 := by
    intro w hw
    exact (hderivative w hw).deriv
  have hconstantOn : ∀ w ∈ sheet.domain,
      separated w = separated sheet.anchor := by
    intro w hw
    exact sheet.isOpen_domain.is_const_of_deriv_eq_zero
      sheet.isPreconnected_domain hdifferentiable hderivZero
      hw sheet.anchor_mem
  have hpuncturedConstant :
      separated =ᶠ[𝓝[≠] 0] fun _ ↦ separated sheet.anchor := by
    filter_upwards [sheet.punctured_mem] with w hw
    exact hconstantOn w hw
  have htimeSheetAnalytic :
      AnalyticAt ℂ (timeCoordinate ∘ sheet.reciprocal) 0 :=
    htimeAnalytic.comp_of_eq sheet.analytic_reciprocal
      sheet.reciprocal_zero
  have hprojectionAnalytic : AnalyticAt ℂ projection 0 := by
    change AnalyticAt ℂ
      (fun w : ℂ ↦ infinityTime + unit * w ^ order) 0
    fun_prop
  have hseparatedAnalytic : AnalyticAt ℂ separated 0 := by
    simpa only [separated, Function.comp_apply] using
      htimeSheetAnalytic.sub hprojectionAnalytic
  have hfullConstant :
      separated =ᶠ[𝓝 0] fun _ ↦ separated sheet.anchor := by
    exact (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
      hseparatedAnalytic.continuousAt continuousAt_const).mp
      hpuncturedConstant
  have hconstant : separated sheet.anchor = -infinityTime := by
    have hcenter := hfullConstant.self_of_nhds
    simpa [separated, projection, ramifiedTimeProjection,
      sheet.reciprocal_zero, htimeZero, hpositive] using hcenter.symm
  filter_upwards [hfullConstant] with w hw
  rw [hconstant] at hw
  dsimp only [separated, projection, ramifiedTimeProjection] at hw
  linear_combination hw

/-- The normalized selected sheet germ equals the constructed local inverse
of the ramified time coordinate.  This is a uniqueness theorem for supplied
sheet data, not a construction of the sheet. -/
theorem polynomial_ramified_trajectory_sheet_terminal_certificate
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate coordinate inverseCoordinate : ℂ → ℂ}
    {infinityTime unit : ℂ} {order : ℕ}
    (sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order)
    (hpositive : order ≠ 0)
    (hunit : unit ≠ 0)
    (htimeAnalytic : AnalyticAt ℂ timeCoordinate 0)
    (htimeZero : timeCoordinate 0 = 0)
    (hcoordinateAnalytic : AnalyticAt ℂ coordinate 0)
    (hcoordinateZero : coordinate 0 = 0)
    (hcoordinateDerivative : deriv coordinate 0 = 1)
    (hnormal : timeCoordinate =ᶠ[𝓝 0]
      fun z ↦ unit * coordinate z ^ order)
    (hinverseAnalytic : AnalyticAt ℂ inverseCoordinate 0)
    (hinverseZero : inverseCoordinate 0 = 0)
    (hrightInverse : ∀ᶠ w in 𝓝 0,
      coordinate (inverseCoordinate w) = w) :
    sheet.reciprocal =ᶠ[𝓝 0] inverseCoordinate := by
  have htimeSheet := timeCoordinate_comp_sheet_eq_power p degree sheet
    hpositive htimeAnalytic htimeZero
  have hpower := coordinate_power_eq_of_timeCoordinate_eq hunit
    sheet.analytic_reciprocal sheet.reciprocal_zero hnormal htimeSheet
  exact selected_eq_inverseCoordinate hcoordinateAnalytic hcoordinateZero
    hcoordinateDerivative sheet.analytic_reciprocal sheet.reciprocal_zero
    sheet.reciprocal_derivative hinverseAnalytic hinverseZero hrightInverse
    hpositive hpower

end FormalPolynomialRamifiedTrajectorySheet
