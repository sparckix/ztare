import ZtareProofs.FormalAnalyticRamifiedFiberProductOverlap
import ZtareProofs.FormalPolynomialFiniteInfinityAbelSeparation
import ZtareProofs.FormalPolynomialRegularInfinityFiberProduct

/-!
# Selected regular Julia ends on polynomial fiber products

This file packages the raw global data of a selected regular endpoint branch.
Julia-to-Abel separation constructs target-time compatibility; punctured
fiber-product overlap then derives branch equality and the exact simple pole.
-/

namespace FormalPolynomialRegularJuliaFiberProductEnd

open Filter Polynomial Set
open scoped Topology

open FormalAnalyticRamifiedFiberProductOverlap
open FormalPolynomialFiniteInfinityAbelSeparation
open FormalPolynomialFiniteTimeCoordinate
open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialRegularInfinityFiberProduct

/-- Raw selected branch data over a constructed regular finite-to-infinity
fiber product.  Time compatibility, branch equality, meromorphicity, and pole
order are not fields. -/
structure RegularJuliaFiberProductEndCarrier
    (p : ℂ[X]) (degree : ℕ) (center : ℂ)
    (model : PolynomialRegularInfinityFiberProduct p degree center) where
  sourceDomain : Set ℂ
  uniformDomain : Set ℂ
  uniformAnchor : ℂ
  endpoint : ℂ → ℂ
  endpointDerivative : ℂ → ℂ
  selectedReciprocal : ℂ → ℂ
  source_isOpen : IsOpen sourceDomain
  source_isPreconnected : IsPreconnected sourceDomain
  uniform_isOpen : IsOpen uniformDomain
  uniform_isPreconnected : IsPreconnected uniformDomain
  uniform_anchor_mem : uniformAnchor ∈ uniformDomain
  uniform_punctured_mem : uniformDomain ∈ nhdsWithin (0 : ℂ) {0}ᶜ
  source_projection_maps :
    MapsTo model.fiberProduct.sourceProjection uniformDomain sourceDomain
  finite_time_derivative : ∀ x ∈ sourceDomain,
    HasDerivAt model.finiteTime (finiteTimeIntegrand p x) x
  infinity_time_derivative : ∀ x ∈ sourceDomain,
    HasDerivAt model.infinityTime
      (reciprocalTimeIntegrand p degree (endpoint x)⁻¹)
      (endpoint x)⁻¹
  endpoint_derivative : ∀ x ∈ sourceDomain,
    HasDerivAt endpoint (endpointDerivative x) x
  julia : ∀ x ∈ sourceDomain,
    p.eval (endpoint x) = endpointDerivative x * p.eval x
  source_regular : ∀ x ∈ sourceDomain, p.eval x ≠ 0
  endpoint_nonzero : ∀ x ∈ sourceDomain, endpoint x ≠ 0
  reverse_nonzero : ∀ x ∈ sourceDomain,
    p.reverse.eval (endpoint x)⁻¹ ≠ 0
  selected_definition : EqOn selectedReciprocal
    (fun w ↦ (endpoint (model.fiberProduct.sourceProjection w))⁻¹)
    uniformDomain
  analytic_selected : AnalyticOnNhd ℂ selectedReciprocal uniformDomain
  analytic_lifted :
    AnalyticOnNhd ℂ model.fiberProduct.liftedTarget uniformDomain
  anchor_compatible :
    selectedReciprocal uniformAnchor =
      model.fiberProduct.liftedTarget uniformAnchor
  fiber_time_compatible : EqOn
    (model.infinityTime ∘ model.fiberProduct.liftedTarget)
    (model.finiteTime ∘ model.fiberProduct.sourceProjection)
    uniformDomain
  infinity_time_analytic_at_anchor :
    AnalyticAt ℂ model.infinityTime (selectedReciprocal uniformAnchor)

/-- A raw regular Julia carrier constructs target-time compatibility with the
fiber-product lift. -/
theorem RegularJuliaFiberProductEndCarrier.time_compatible
    {p : ℂ[X]} {degree : ℕ} {center : ℂ}
    {model : PolynomialRegularInfinityFiberProduct p degree center}
    (carrier : RegularJuliaFiberProductEndCarrier p degree center model)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree) :
    EqOn (model.infinityTime ∘ carrier.selectedReciprocal)
      (model.infinityTime ∘ model.fiberProduct.liftedTarget)
      carrier.uniformDomain := by
  let sourceAnchor :=
    model.fiberProduct.sourceProjection carrier.uniformAnchor
  have hsourceAnchor : sourceAnchor ∈ carrier.sourceDomain :=
    carrier.source_projection_maps carrier.uniform_anchor_mem
  have hseparation := finiteInfinitySeparatedTime_eqOn
    p degree hdegree htwo carrier.source_isOpen
      carrier.source_isPreconnected hsourceAnchor
      carrier.finite_time_derivative carrier.infinity_time_derivative
      carrier.endpoint_derivative carrier.julia carrier.source_regular
      carrier.endpoint_nonzero carrier.reverse_nonzero
  have hselectedAnchor :=
    carrier.selected_definition carrier.uniform_anchor_mem
  have hfiberAnchor :=
    carrier.fiber_time_compatible carrier.uniform_anchor_mem
  simp only [Function.comp_apply] at hfiberAnchor
  have hconstantZero :
      model.infinityTime (carrier.endpoint sourceAnchor)⁻¹ -
          model.finiteTime sourceAnchor = 0 := by
    calc
      model.infinityTime (carrier.endpoint sourceAnchor)⁻¹ -
          model.finiteTime sourceAnchor =
          model.infinityTime
              (carrier.selectedReciprocal carrier.uniformAnchor) -
            model.finiteTime sourceAnchor := by
              rw [hselectedAnchor]
      _ = model.infinityTime
              (model.fiberProduct.liftedTarget carrier.uniformAnchor) -
            model.finiteTime sourceAnchor := by
              rw [carrier.anchor_compatible]
      _ = 0 := sub_eq_zero.mpr hfiberAnchor
  intro w hw
  have hsource := carrier.source_projection_maps hw
  have hseparated := hseparation
    (model.fiberProduct.sourceProjection w) hsource
  rw [hconstantZero] at hseparated
  have hselected := carrier.selected_definition hw
  have hfiber := carrier.fiber_time_compatible hw
  simp only [Function.comp_apply] at hfiber ⊢
  calc
    model.infinityTime (carrier.selectedReciprocal w) =
        model.infinityTime
          (carrier.endpoint (model.fiberProduct.sourceProjection w))⁻¹ := by
      rw [hselected]
    _ = model.finiteTime (model.fiberProduct.sourceProjection w) :=
      sub_eq_zero.mp hseparated
    _ = model.infinityTime (model.fiberProduct.liftedTarget w) :=
      hfiber.symm

/-- The target time is noncritical at the supplied punctured anchor. -/
theorem RegularJuliaFiberProductEndCarrier.target_time_derivative_nonzero
    {p : ℂ[X]} {degree : ℕ} {center : ℂ}
    {model : PolynomialRegularInfinityFiberProduct p degree center}
    (carrier : RegularJuliaFiberProductEndCarrier p degree center model) :
    deriv model.infinityTime
      (carrier.selectedReciprocal carrier.uniformAnchor) ≠ 0 := by
  let sourceAnchor :=
    model.fiberProduct.sourceProjection carrier.uniformAnchor
  have hsourceAnchor : sourceAnchor ∈ carrier.sourceDomain :=
    carrier.source_projection_maps carrier.uniform_anchor_mem
  have hselectedAnchor :=
    carrier.selected_definition carrier.uniform_anchor_mem
  have hderivative := carrier.infinity_time_derivative
    sourceAnchor hsourceAnchor
  have hendpointNonzero := carrier.endpoint_nonzero
    sourceAnchor hsourceAnchor
  have hreverseNonzero := carrier.reverse_nonzero
    sourceAnchor hsourceAnchor
  have hintegrandNonzero :
      reciprocalTimeIntegrand p degree
          (carrier.endpoint sourceAnchor)⁻¹ ≠ 0 := by
    apply mul_ne_zero
    · exact pow_ne_zero _ (inv_ne_zero hendpointNonzero)
    · exact neg_ne_zero.mpr (inv_ne_zero hreverseNonzero)
  rw [hselectedAnchor, hderivative.deriv]
  exact hintegrandNonzero

/-- The carrier constructs a punctured fiber-product overlap, so equality and
the exact selected simple pole follow from the governed overlap kernel. -/
theorem RegularJuliaFiberProductEndCarrier.selected_end_certificate
    {p : ℂ[X]} {degree : ℕ} {center : ℂ}
    {model : PolynomialRegularInfinityFiberProduct p degree center}
    (carrier : RegularJuliaFiberProductEndCarrier p degree center model)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree) :
    EqOn carrier.selectedReciprocal model.fiberProduct.liftedTarget
        carrier.uniformDomain ∧
      MeromorphicAt (carrier.selectedReciprocal⁻¹) 0 ∧
      meromorphicOrderAt (carrier.selectedReciprocal⁻¹) 0 =
        ((-1 : ℤ) : WithTop ℤ) := by
  let overlap : PuncturedRamifiedFiberProductOverlap
      model.infinityTime model.finiteTime 0 center (degree - 1) 1
      model.fiberProduct := {
    domain := carrier.uniformDomain
    anchor := carrier.uniformAnchor
    selectedTarget := carrier.selectedReciprocal
    isOpen_domain := carrier.uniform_isOpen
    isPreconnected_domain := carrier.uniform_isPreconnected
    anchor_mem := carrier.uniform_anchor_mem
    punctured_mem := carrier.uniform_punctured_mem
    analytic_selected := carrier.analytic_selected
    analytic_lifted := carrier.analytic_lifted
    anchor_compatible := carrier.anchor_compatible
    target_time_analytic_at_anchor :=
      carrier.infinity_time_analytic_at_anchor
    target_time_derivative_nonzero :=
      carrier.target_time_derivative_nonzero
    time_compatible := carrier.time_compatible hdegree htwo
  }
  have hequality :
      EqOn carrier.selectedReciprocal model.fiberProduct.liftedTarget
        carrier.uniformDomain := by
    simpa only [overlap] using overlap.eqOn
  have hcertificate :
      MeromorphicAt (carrier.selectedReciprocal⁻¹) 0 ∧
        meromorphicOrderAt (carrier.selectedReciprocal⁻¹) 0 =
          ((-1 : ℤ) : WithTop ℤ) := by
    simpa only [overlap, sub_zero] using
      overlap.selected_inverse_certificate
  exact ⟨hequality, hcertificate⟩

/-- Aggregated typed inference from a selected regular Julia carrier to
fiber-product branch equality and a simple pole. -/
theorem polynomial_regular_julia_fiber_product_end_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ) (center : ℂ)
      (model : PolynomialRegularInfinityFiberProduct p degree center)
      (carrier : RegularJuliaFiberProductEndCarrier p degree center model),
      p.natDegree = degree →
      2 ≤ degree →
      EqOn carrier.selectedReciprocal model.fiberProduct.liftedTarget
          carrier.uniformDomain ∧
        MeromorphicAt (carrier.selectedReciprocal⁻¹) 0 ∧
        meromorphicOrderAt (carrier.selectedReciprocal⁻¹) 0 =
          ((-1 : ℤ) : WithTop ℤ) := by
  intro p degree center model carrier hdegree htwo
  exact carrier.selected_end_certificate hdegree htwo

end FormalPolynomialRegularJuliaFiberProductEnd
