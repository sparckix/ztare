import Mathlib.Analysis.Meromorphic.Order
import ZtareProofs.FormalAnalyticRamifiedFiberProduct
import ZtareProofs.FormalAnalyticSheetOverlap

/-!
# Punctured overlap with an analytic ramified fiber product

A selected branch and a constructed fiber-product lift that share one
noncritical target-time coordinate on a connected punctured overlap must
coincide there.  Punctured-germ congruence then transfers the constructed
meromorphic inverse and its exact order to the selected branch.
-/

namespace FormalAnalyticRamifiedFiberProductOverlap

open Filter Set
open scoped Topology

open FormalAnalyticRamifiedFiberProduct
open FormalAnalyticSheetOverlap

/-- Raw selected overlap data.  Equality and meromorphicity are deliberately
absent: they are conclusions of the kernel below. -/
structure PuncturedRamifiedFiberProductOverlap
    (targetTime sourceTime : ℂ → ℂ)
    (targetCenter sourceCenter : ℂ)
    (targetOrder sourceOrder : ℕ)
    (fiberProduct : AnalyticRamifiedFiberProduct targetTime sourceTime
      targetCenter sourceCenter targetOrder sourceOrder) where
  domain : Set ℂ
  anchor : ℂ
  selectedTarget : ℂ → ℂ
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  punctured_mem : domain ∈ nhdsWithin (0 : ℂ) {0}ᶜ
  analytic_selected : AnalyticOnNhd ℂ selectedTarget domain
  analytic_lifted : AnalyticOnNhd ℂ fiberProduct.liftedTarget domain
  anchor_compatible :
    selectedTarget anchor = fiberProduct.liftedTarget anchor
  target_time_analytic_at_anchor :
    AnalyticAt ℂ targetTime (selectedTarget anchor)
  target_time_derivative_nonzero :
    deriv targetTime (selectedTarget anchor) ≠ 0
  time_compatible :
    EqOn (targetTime ∘ selectedTarget)
      (targetTime ∘ fiberProduct.liftedTarget) domain

/-- Target-time compatibility at one noncritical anchor identifies the
selected and constructed branches throughout the connected overlap. -/
theorem PuncturedRamifiedFiberProductOverlap.eqOn
    {targetTime sourceTime : ℂ → ℂ}
    {targetCenter sourceCenter : ℂ}
    {targetOrder sourceOrder : ℕ}
    {fiberProduct : AnalyticRamifiedFiberProduct targetTime sourceTime
      targetCenter sourceCenter targetOrder sourceOrder}
    (overlap : PuncturedRamifiedFiberProductOverlap
      targetTime sourceTime targetCenter sourceCenter
      targetOrder sourceOrder fiberProduct) :
    EqOn overlap.selectedTarget fiberProduct.liftedTarget
      overlap.domain := by
  let core : AnalyticCoordinateOverlap targetTime
      overlap.selectedTarget fiberProduct.liftedTarget := {
    domain := overlap.domain
    anchor := overlap.anchor
    isOpen_domain := overlap.isOpen_domain
    isPreconnected_domain := overlap.isPreconnected_domain
    anchor_mem := overlap.anchor_mem
    analytic_left := overlap.analytic_selected
    analytic_right := overlap.analytic_lifted
    anchor_compatible := overlap.anchor_compatible
    coordinate_analytic := overlap.target_time_analytic_at_anchor
    coordinate_derivative_nonzero :=
      overlap.target_time_derivative_nonzero
    coordinate_compatible := overlap.time_compatible
  }
  exact core.eqOn

/-- Equality on a punctured neighborhood transfers the fiber product's
meromorphic inverse displacement and its exact negative order to the selected
branch. -/
theorem PuncturedRamifiedFiberProductOverlap.selected_inverse_certificate
    {targetTime sourceTime : ℂ → ℂ}
    {targetCenter sourceCenter : ℂ}
    {targetOrder sourceOrder : ℕ}
    {fiberProduct : AnalyticRamifiedFiberProduct targetTime sourceTime
      targetCenter sourceCenter targetOrder sourceOrder}
    (overlap : PuncturedRamifiedFiberProductOverlap
      targetTime sourceTime targetCenter sourceCenter
      targetOrder sourceOrder fiberProduct) :
    MeromorphicAt
        ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) 0 ∧
      meromorphicOrderAt
          ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) 0 =
        ((-(sourceOrder : ℤ) : ℤ) : WithTop ℤ) := by
  have hselectedLifted : overlap.selectedTarget =ᶠ[nhdsWithin (0 : ℂ) {0}ᶜ]
      fiberProduct.liftedTarget := by
    filter_upwards [overlap.punctured_mem] with w hw
    exact overlap.eqOn hw
  have hinverseEq :
      ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) =ᶠ[nhdsWithin (0 : ℂ) {0}ᶜ]
        ((fun w ↦ fiberProduct.liftedTarget w - targetCenter)⁻¹) := by
    filter_upwards [hselectedLifted] with w hw
    change (overlap.selectedTarget w - targetCenter)⁻¹ =
      (fiberProduct.liftedTarget w - targetCenter)⁻¹
    rw [hw]
  constructor
  · exact fiberProduct.inverse_displacement_meromorphic.congr
      hinverseEq.symm
  · calc
      meromorphicOrderAt
          ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) 0 =
          meromorphicOrderAt
            ((fun w ↦ fiberProduct.liftedTarget w - targetCenter)⁻¹) 0 :=
        meromorphicOrderAt_congr hinverseEq
      _ = ((-(sourceOrder : ℤ) : ℤ) : WithTop ℤ) :=
        fiberProduct.inverse_displacement_order

/-- Aggregated punctured-overlap uniqueness and exact-pole transfer
certificate. -/
theorem analytic_ramified_fiber_product_overlap_terminal_certificate :
    ∀ (targetTime sourceTime : ℂ → ℂ)
      (targetCenter sourceCenter : ℂ)
      (targetOrder sourceOrder : ℕ)
      (fiberProduct : AnalyticRamifiedFiberProduct targetTime sourceTime
        targetCenter sourceCenter targetOrder sourceOrder)
      (overlap : PuncturedRamifiedFiberProductOverlap
        targetTime sourceTime targetCenter sourceCenter
        targetOrder sourceOrder fiberProduct),
      EqOn overlap.selectedTarget fiberProduct.liftedTarget
          overlap.domain ∧
        MeromorphicAt
          ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) 0 ∧
        meromorphicOrderAt
            ((fun w ↦ overlap.selectedTarget w - targetCenter)⁻¹) 0 =
          ((-(sourceOrder : ℤ) : ℤ) : WithTop ℤ) := by
  intro targetTime sourceTime targetCenter sourceCenter
    targetOrder sourceOrder fiberProduct overlap
  exact ⟨overlap.eqOn, overlap.selected_inverse_certificate⟩

end FormalAnalyticRamifiedFiberProductOverlap
