import Mathlib.Analysis.Analytic.Composition
import Mathlib.Tactic

/-!
# Finite analytic routes in a two-map composition

This file isolates the general analytic part of a finite-versus-infinity
argument.  If both selected factor germs are analytic in their finite charts,
their composition is analytic.  Consequently a nonanalytic composition makes
at least one finite-chart factor fail.

Identifying that failure with a reciprocal projective-infinity chart is a
separate maximal-continuation theorem and is not assumed here under a renamed
predicate.
-/

namespace FormalAnalyticFiniteRoute

/-- Composition preserves analyticity when the inner endpoint and the outer
germ at that endpoint both remain in finite analytic charts. -/
theorem analyticAt_comp_of_finite_factor_germs
    {inner outer : ℂ → ℂ} {x₀ : ℂ}
    (hinner : AnalyticAt ℂ inner x₀)
    (houter : AnalyticAt ℂ outer (inner x₀)) :
    AnalyticAt ℂ (outer ∘ inner) x₀ :=
  houter.comp hinner

/-- Contrapositive finite-route theorem: a nonanalytic composition forces at
least one selected factor germ out of its finite analytic chart. -/
theorem nonanalytic_comp_forces_nonanalytic_factor
    {inner outer : ℂ → ℂ} {x₀ : ℂ}
    (hcomposition : ¬AnalyticAt ℂ (outer ∘ inner) x₀) :
    ¬AnalyticAt ℂ inner x₀ ∨ ¬AnalyticAt ℂ outer (inner x₀) := by
  by_contra hfinite
  push Not at hfinite
  exact hcomposition
    (analyticAt_comp_of_finite_factor_germs hfinite.1 hfinite.2)

/-- Inference boundary for a caller-owned escape classification.  The caller
must prove that failure of either finite factor germ implies its declared
escape proposition; this theorem supplies only the analytic contraposition. -/
theorem escape_of_nonanalytic_composition
    {inner outer : ℂ → ℂ} {x₀ : ℂ} {Escape : Prop}
    (hcomposition : ¬AnalyticAt ℂ (outer ∘ inner) x₀)
    (hclassify :
      (¬AnalyticAt ℂ inner x₀ ∨ ¬AnalyticAt ℂ outer (inner x₀)) →
        Escape) :
    Escape :=
  hclassify (nonanalytic_comp_forces_nonanalytic_factor hcomposition)

/-- Aggregated finite-route certificate for formal-coverage adapters. -/
theorem finite_analytic_route_terminal_certificate :
    (∀ (inner outer : ℂ → ℂ) (x₀ : ℂ),
      AnalyticAt ℂ inner x₀ →
      AnalyticAt ℂ outer (inner x₀) →
      AnalyticAt ℂ (outer ∘ inner) x₀) ∧
    (∀ (inner outer : ℂ → ℂ) (x₀ : ℂ),
      (¬AnalyticAt ℂ (outer ∘ inner) x₀) →
      ¬AnalyticAt ℂ inner x₀ ∨ ¬AnalyticAt ℂ outer (inner x₀)) ∧
    (∀ (inner outer : ℂ → ℂ) (x₀ : ℂ) (Escape : Prop),
      (¬AnalyticAt ℂ (outer ∘ inner) x₀) →
      ((¬AnalyticAt ℂ inner x₀ ∨
        ¬AnalyticAt ℂ outer (inner x₀)) → Escape) →
      Escape) := by
  exact ⟨
    fun inner outer x₀ ↦
      @analyticAt_comp_of_finite_factor_germs inner outer x₀,
    fun inner outer x₀ ↦
      @nonanalytic_comp_forces_nonanalytic_factor inner outer x₀,
    fun inner outer x₀ Escape ↦
      @escape_of_nonanalytic_composition inner outer x₀ Escape⟩

end FormalAnalyticFiniteRoute
