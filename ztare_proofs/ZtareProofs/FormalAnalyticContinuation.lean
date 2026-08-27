import Mathlib.Analysis.Analytic.IsolatedZeros
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.Basic

/-!
# Analytic identity transport through continuation charts

This file isolates the analytic mechanism needed when an identity starts in
one local coordinate and ends in another, possibly ramified, coordinate.
Each chart carries the represented input, endpoint, and spatial derivative
factor.  An edge supplies their eventual compatibility after a local change
of coordinate.  The analytic identity theorem then propagates a polynomial
Julia residual across the edge, and an inductive chain propagates it to the
terminal chart.

The interface does not assert that a particular branch admits a chain.  That
realization remains the responsibility of the caller.
-/

namespace FormalAnalyticContinuation

open scoped Topology
open Filter Polynomial Set

/-- One connected analytic chart for an input coordinate, an endpoint, and
its spatial derivative factor. -/
structure IdentityChart where
  domain : Set ℂ
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  center : ℂ
  center_mem : center ∈ domain
  base : ℂ → ℂ
  endpoint : ℂ → ℂ
  derivativeFactor : ℂ → ℂ
  analytic_base : AnalyticOnNhd ℂ base domain
  analytic_endpoint : AnalyticOnNhd ℂ endpoint domain
  analytic_derivativeFactor : AnalyticOnNhd ℂ derivativeFactor domain

/-- The Julia residual represented in one chart. -/
noncomputable def juliaResidual
    (generator : ℂ[X]) (chart : IdentityChart) : ℂ → ℂ :=
  fun z =>
    aeval (chart.endpoint z) generator -
      chart.derivativeFactor z * aeval (chart.base z) generator

theorem juliaResidual_analyticOnNhd
    (generator : ℂ[X]) (chart : IdentityChart) :
    AnalyticOnNhd ℂ (juliaResidual generator chart) chart.domain := by
  exact (chart.analytic_endpoint.aeval_polynomial generator).sub
    (chart.analytic_derivativeFactor.mul
      (chart.analytic_base.aeval_polynomial generator))

/-- A local continuation edge.  `transition` expresses the left-chart
coordinate as a function of the right-chart coordinate.  Compatibility is
required for the three represented functions, never for the Julia residual
itself. -/
structure IdentityEdge (left right : IdentityChart) where
  point : ℂ
  point_mem_right : point ∈ right.domain
  transition : ℂ → ℂ
  analytic_transition : AnalyticAt ℂ transition point
  transition_mem_left :
    ∀ᶠ z in 𝓝 point, transition z ∈ left.domain
  base_compatible :
    right.base =ᶠ[𝓝 point] left.base ∘ transition
  endpoint_compatible :
    right.endpoint =ᶠ[𝓝 point] left.endpoint ∘ transition
  derivativeFactor_compatible :
    right.derivativeFactor =ᶠ[𝓝 point]
      left.derivativeFactor ∘ transition

theorem IdentityEdge.juliaResidual_eventuallyEq
    {left right : IdentityChart} (edge : IdentityEdge left right)
    (generator : ℂ[X]) :
    juliaResidual generator right =ᶠ[𝓝 edge.point]
      juliaResidual generator left ∘ edge.transition := by
  filter_upwards [edge.base_compatible, edge.endpoint_compatible,
    edge.derivativeFactor_compatible] with z hbase hendpoint hfactor
  simp only [juliaResidual, Function.comp_apply]
  rw [hbase, hendpoint, hfactor]
  simp only [Function.comp_apply]

/-- One continuation edge propagates a polynomial Julia identity by the
analytic identity theorem. -/
theorem IdentityEdge.propagate_julia
    {left right : IdentityChart} (edge : IdentityEdge left right)
    (generator : ℂ[X])
    (hleft : EqOn (juliaResidual generator left) 0 left.domain) :
    EqOn (juliaResidual generator right) 0 right.domain := by
  have hnear : juliaResidual generator right =ᶠ[𝓝 edge.point] 0 := by
    filter_upwards [edge.juliaResidual_eventuallyEq generator,
      edge.transition_mem_left] with z hcompat hmem
    rw [hcompat]
    exact hleft hmem
  exact (juliaResidual_analyticOnNhd generator right).eqOn_of_preconnected_of_eventuallyEq
    analyticOnNhd_const right.isPreconnected_domain edge.point_mem_right hnear

/-- A finite coordinate-aware continuation from `first` to `last`. -/
inductive IdentityContinuation : IdentityChart → IdentityChart → Type
  | refl (chart : IdentityChart) : IdentityContinuation chart chart
  | step {first middle last : IdentityChart}
      (edge : IdentityEdge first middle)
      (tail : IdentityContinuation middle last) :
      IdentityContinuation first last

/-- Polynomial Julia identities propagate through every edge of a finite
continuation chain. -/
theorem IdentityContinuation.propagate_julia
    {first last : IdentityChart}
    (continuation : IdentityContinuation first last)
    (generator : ℂ[X])
    (hfirst : EqOn (juliaResidual generator first) 0 first.domain) :
    EqOn (juliaResidual generator last) 0 last.domain := by
  induction continuation with
  | refl => exact hfirst
  | step edge tail ih =>
      exact ih (edge.propagate_julia generator hfirst)

/-- Terminal point form of analytic Julia transport. -/
theorem IdentityContinuation.terminal_julia_identity
    {first last : IdentityChart}
    (continuation : IdentityContinuation first last)
    (generator : ℂ[X])
    (hfirst : EqOn (juliaResidual generator first) 0 first.domain) :
    aeval (last.endpoint last.center) generator =
      last.derivativeFactor last.center *
        aeval (last.base last.center) generator := by
  have hterminal := continuation.propagate_julia generator hfirst
  have hzero := hterminal last.center_mem
  exact sub_eq_zero.mp (by simpa [juliaResidual] using hzero)

/-- Entire identity chart used to stress continuation through a noninjective
terminal coordinate. -/
noncomputable def identityChart : IdentityChart where
  domain := Set.univ
  isOpen_domain := isOpen_univ
  isPreconnected_domain := isPreconnected_univ
  center := 0
  center_mem := Set.mem_univ 0
  base := fun z => z
  endpoint := fun z => z
  derivativeFactor := fun _ => 1
  analytic_base := analyticOnNhd_id
  analytic_endpoint := analyticOnNhd_id
  analytic_derivativeFactor := analyticOnNhd_const

/-- The same represented identity in the ramified coordinate `z ↦ z² - 2`. -/
noncomputable def ramifiedIdentityChart : IdentityChart where
  domain := Set.univ
  isOpen_domain := isOpen_univ
  isPreconnected_domain := isPreconnected_univ
  center := 0
  center_mem := Set.mem_univ 0
  base := fun z => z ^ 2 - 2
  endpoint := fun z => z ^ 2 - 2
  derivativeFactor := fun _ => 1
  analytic_base := (analyticOnNhd_id.pow 2).sub analyticOnNhd_const
  analytic_endpoint := (analyticOnNhd_id.pow 2).sub analyticOnNhd_const
  analytic_derivativeFactor := analyticOnNhd_const

noncomputable def ramifiedIdentityEdge :
    IdentityEdge identityChart ramifiedIdentityChart where
  point := 0
  point_mem_right := Set.mem_univ 0
  transition := fun z => z ^ 2 - 2
  analytic_transition := (analyticAt_id.pow 2).sub analyticAt_const
  transition_mem_left := Filter.Eventually.of_forall fun _ => Set.mem_univ _
  base_compatible := Filter.Eventually.of_forall fun _ => rfl
  endpoint_compatible := Filter.Eventually.of_forall fun _ => rfl
  derivativeFactor_compatible := Filter.Eventually.of_forall fun _ => rfl

/-- Stress fixture: the transport theorem accepts a square-root uniformizing
coordinate without treating it as the original planar coordinate. -/
theorem ramified_coordinate_transport_fixture (generator : ℂ[X]) :
    EqOn (juliaResidual generator ramifiedIdentityChart) 0 Set.univ := by
  let continuation :
      IdentityContinuation identityChart ramifiedIdentityChart :=
    .step ramifiedIdentityEdge (.refl ramifiedIdentityChart)
  apply continuation.propagate_julia generator
  intro z _hz
  simp [juliaResidual, identityChart]

/-- Aggregated formal endpoint for coordinate-aware analytic identity
transport. -/
theorem analytic_continuation_julia_terminal_certificate :
    ∀ {first last : IdentityChart}
      (_continuation : IdentityContinuation first last)
      (generator : ℂ[X]),
      EqOn (juliaResidual generator first) 0 first.domain →
      EqOn (juliaResidual generator last) 0 last.domain := by
  intro first last continuation generator hfirst
  exact continuation.propagate_julia generator hfirst

end FormalAnalyticContinuation
