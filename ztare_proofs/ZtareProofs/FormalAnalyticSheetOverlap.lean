import Mathlib.Analysis.Analytic.IsolatedZeros
import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Analysis.Complex.CauchyIntegral
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialRamifiedTrajectorySheet

/-!
# Analytic uniqueness on a finite-to-ramified-sheet overlap

The local inverse theorem and the analytic identity theorem separate overlap
uniqueness from overlap existence.  Two analytic branches on one connected
chart are equal when they meet at a noncritical point of a common analytic
coordinate and have the same coordinate value throughout the chart.

The polynomial specialization applies this kernel to a selected finite
reciprocal continuation and a ramified infinity sheet.  Its overlap record
owns coordinate compatibility, but does not assume equality of the two
reciprocal branches.

No maximal-continuation, overlap-existence, or route-exhaustiveness statement
is made here.
-/

namespace FormalAnalyticSheetOverlap

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialRamifiedTrajectorySheet

/-- A connected overlap on which two analytic branches have one common
noncritical analytic coordinate. -/
structure AnalyticCoordinateOverlap
    (coordinate left right : ℂ → ℂ) where
  domain : Set ℂ
  anchor : ℂ
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  analytic_left : AnalyticOnNhd ℂ left domain
  analytic_right : AnalyticOnNhd ℂ right domain
  anchor_compatible : left anchor = right anchor
  coordinate_analytic : AnalyticAt ℂ coordinate (left anchor)
  coordinate_derivative_nonzero : deriv coordinate (left anchor) ≠ 0
  coordinate_compatible :
    EqOn (coordinate ∘ left) (coordinate ∘ right) domain

/-- Local inverse uniqueness at the anchor, followed by the analytic identity
theorem, identifies the two branches on the whole connected overlap. -/
theorem AnalyticCoordinateOverlap.eqOn
    {coordinate left right : ℂ → ℂ}
    (overlap : AnalyticCoordinateOverlap coordinate left right) :
    EqOn left right overlap.domain := by
  have hstrict : HasStrictDerivAt coordinate
      (deriv coordinate (left overlap.anchor)) (left overlap.anchor) := by
    simpa using overlap.coordinate_analytic.hasStrictDerivAt
  let localInverse := hstrict.localInverse coordinate
    (deriv coordinate (left overlap.anchor)) (left overlap.anchor)
    overlap.coordinate_derivative_nonzero
  have hleftInverse :
      localInverse ∘ coordinate =ᶠ[𝓝 (left overlap.anchor)]
        fun z ↦ z := by
    simpa only [localInverse] using
      hstrict.eventually_left_inverse
        overlap.coordinate_derivative_nonzero
  have hleftTendsto :
      Tendsto left (𝓝 overlap.anchor) (𝓝 (left overlap.anchor)) :=
    (overlap.analytic_left overlap.anchor overlap.anchor_mem).continuousAt
  have hrightTendsto :
      Tendsto right (𝓝 overlap.anchor) (𝓝 (left overlap.anchor)) := by
    have hcontinuous :=
      (overlap.analytic_right overlap.anchor overlap.anchor_mem).continuousAt
    simpa only [overlap.anchor_compatible] using hcontinuous
  have hleftLocal : ∀ᶠ z in 𝓝 overlap.anchor,
      localInverse (coordinate (left z)) = left z := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleftInverse hleftTendsto
  have hrightLocal : ∀ᶠ z in 𝓝 overlap.anchor,
      localInverse (coordinate (right z)) = right z := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleftInverse hrightTendsto
  have hcoordinateLocal : ∀ᶠ z in 𝓝 overlap.anchor,
      coordinate (left z) = coordinate (right z) := by
    filter_upwards [overlap.isOpen_domain.mem_nhds overlap.anchor_mem]
      with z hz
    exact overlap.coordinate_compatible hz
  have hnear : left =ᶠ[𝓝 overlap.anchor] right := by
    filter_upwards [hleftLocal, hrightLocal, hcoordinateLocal]
      with z hleftZ hrightZ hcoordinateZ
    calc
      left z = localInverse (coordinate (left z)) := hleftZ.symm
      _ = localInverse (coordinate (right z)) :=
        congrArg localInverse hcoordinateZ
      _ = right z := hrightZ
  exact overlap.analytic_left.eqOn_of_preconnected_of_eventuallyEq
    overlap.analytic_right overlap.isPreconnected_domain
    overlap.anchor_mem hnear

/-- A selected finite reciprocal continuation represented on one connected
chart of a polynomial ramified infinity sheet.

The record deliberately contains projected-time compatibility and one anchor
match, not equality of reciprocal branches.  Constructing this record from a
bare selected continuation is the separate global continuation obligation. -/
structure PolynomialFiniteToRamifiedSheetOverlap
    (p : ℂ[X]) (degree : ℕ) (timeCoordinate : ℂ → ℂ)
    (infinityTime unit : ℂ) (order : ℕ)
    (sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order) where
  domain : Set ℂ
  anchor : ℂ
  finiteReciprocal : ℂ → ℂ
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  mapsTo_sheet : MapsTo id domain sheet.domain
  analytic_finite : AnalyticOnNhd ℂ finiteReciprocal domain
  anchor_compatible :
    finiteReciprocal anchor = sheet.reciprocal anchor
  time_analytic_at_anchor :
    AnalyticAt ℂ timeCoordinate (sheet.reciprocal anchor)
  time_compatible : EqOn
    (timeCoordinate ∘ finiteReciprocal)
    (timeCoordinate ∘ sheet.reciprocal)
    domain

/-- The sheet reciprocal coordinate is analytic throughout every open subset
of its punctured sheet domain. -/
theorem sheet_reciprocal_analyticOnNhd
    {p : ℂ[X]} {degree : ℕ} {timeCoordinate : ℂ → ℂ}
    {infinityTime unit : ℂ} {order : ℕ}
    (sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order) :
    AnalyticOnNhd ℂ sheet.reciprocal sheet.domain := by
  apply DifferentiableOn.analyticOnNhd _ sheet.isOpen_domain
  intro w hw
  exact (sheet.pulledBack_derivative w hw).differentiableAt.differentiableWithinAt

/-- Projected-time compatibility on a supplied connected overlap forces the
incoming finite reciprocal branch to equal the selected sheet branch. -/
theorem PolynomialFiniteToRamifiedSheetOverlap.eqOn
    {p : ℂ[X]} {degree : ℕ} {timeCoordinate : ℂ → ℂ}
    {infinityTime unit : ℂ} {order : ℕ}
    {sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
      infinityTime unit order}
    (overlap : PolynomialFiniteToRamifiedSheetOverlap p degree
      timeCoordinate infinityTime unit order sheet) :
    EqOn overlap.finiteReciprocal sheet.reciprocal overlap.domain := by
  have hsheetAnalytic :
      AnalyticOnNhd ℂ sheet.reciprocal overlap.domain :=
    (sheet_reciprocal_analyticOnNhd sheet).mono overlap.mapsTo_sheet
  have htimeDerivative :=
    sheet.time_derivative overlap.anchor
      (overlap.mapsTo_sheet overlap.anchor_mem)
  have hreciprocalNonzero :=
    sheet.reciprocal_nonzero overlap.anchor
      (overlap.mapsTo_sheet overlap.anchor_mem)
  have hreverseNonzero :=
    sheet.reverse_nonzero overlap.anchor
      (overlap.mapsTo_sheet overlap.anchor_mem)
  have hintegrandNonzero :
      reciprocalTimeIntegrand p degree (sheet.reciprocal overlap.anchor) ≠ 0 := by
    apply mul_ne_zero
    · exact pow_ne_zero _ hreciprocalNonzero
    · exact neg_ne_zero.mpr (inv_ne_zero hreverseNonzero)
  have htimeDerivativeNonzero :
      deriv timeCoordinate (overlap.finiteReciprocal overlap.anchor) ≠ 0 := by
    rw [overlap.anchor_compatible]
    rw [htimeDerivative.deriv]
    exact hintegrandNonzero
  let core : AnalyticCoordinateOverlap timeCoordinate
      overlap.finiteReciprocal sheet.reciprocal := {
    domain := overlap.domain
    anchor := overlap.anchor
    isOpen_domain := overlap.isOpen_domain
    isPreconnected_domain := overlap.isPreconnected_domain
    anchor_mem := overlap.anchor_mem
    analytic_left := overlap.analytic_finite
    analytic_right := hsheetAnalytic
    anchor_compatible := overlap.anchor_compatible
    coordinate_analytic := by
      simpa only [overlap.anchor_compatible] using
        overlap.time_analytic_at_anchor
    coordinate_derivative_nonzero := htimeDerivativeNonzero
    coordinate_compatible := overlap.time_compatible
  }
  exact core.eqOn

/-- Reusable terminal surface: every supplied finite-to-sheet overlap has a
unique reciprocal branch.  The quantified record is evidence of overlap
existence; this theorem does not construct it. -/
theorem polynomial_finite_to_ramified_sheet_overlap_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ) (timeCoordinate : ℂ → ℂ)
      (infinityTime unit : ℂ) (order : ℕ)
      (sheet : PolynomialRamifiedTrajectorySheet p degree timeCoordinate
        infinityTime unit order)
      (overlap : PolynomialFiniteToRamifiedSheetOverlap p degree
        timeCoordinate infinityTime unit order sheet),
      EqOn overlap.finiteReciprocal sheet.reciprocal overlap.domain := by
  intro p degree timeCoordinate infinityTime unit order sheet overlap
  exact overlap.eqOn

end FormalAnalyticSheetOverlap
