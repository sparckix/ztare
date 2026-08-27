import Mathlib.Algebra.Polynomial.Roots
import Mathlib.Tactic
import ZtareProofs.FormalComplexMonodromyFiniteRootEscape

/-!
# Escape from a finite cover of polynomial root sets

A finite-sheet coefficient cover produces only finitely many specialized
polynomials at a fixed return basepoint.  If every visited specialization is
nonzero, their root sets cannot contain an injective endpoint orbit.

This file assumes that the returned sheet and endpoint sequences have already
been constructed.  It contains no analytic-continuation or path-lift claim.
-/

namespace FormalFinitePolynomialCoverOrbitEscape

open Polynomial Set

open FormalComplexMonodromyFiniteRootEscape

/-- An injective endpoint orbit cannot lie in root sets indexed by a finite
family of nonzero polynomials. -/
theorem no_injective_orbit_over_finite_polynomial_cover
    {sheetIndex : Type*} [Finite sheetIndex]
    (polynomial : sheetIndex → ℂ[X])
    (endpoint : ℕ → ℂ)
    (endpoint_injective : Function.Injective endpoint)
    (sheetAt : ℕ → sheetIndex)
    (polynomial_nonzero : ∀ order : ℕ,
      polynomial (sheetAt order) ≠ 0)
    (relation : ∀ order : ℕ,
      (polynomial (sheetAt order)).IsRoot (endpoint order)) :
    False := by
  have hendpointInfinite : (Set.range endpoint).Infinite :=
    Set.infinite_range_of_injective endpoint_injective
  have hrootUnion :
      (⋃ sheet ∈ Set.range sheetAt,
        { value : ℂ | (polynomial sheet).IsRoot value }).Finite :=
    (Set.toFinite (Set.range sheetAt)).biUnion fun sheet hsheet => by
      rcases hsheet with ⟨order, rfl⟩
      exact Polynomial.finite_setOf_isRoot (polynomial_nonzero order)
  have hendpointSubset :
      Set.range endpoint ⊆
        ⋃ sheet ∈ Set.range sheetAt,
          { value : ℂ | (polynomial sheet).IsRoot value } := by
    rintro value ⟨order, rfl⟩
    exact Set.mem_iUnion.2 ⟨sheetAt order,
      Set.mem_iUnion.2 ⟨⟨order, rfl⟩, relation order⟩⟩
  exact hendpointInfinite (hrootUnion.subset hendpointSubset)

/-- A positive-power non-torsion scalar orbit remains injective on every
injectively enumerated infinite return subsequence, so it cannot satisfy a
finite-sheet family of nonzero polynomial relations there. -/
theorem no_nontorsion_scaled_return_subsequence_over_finite_polynomial_cover
    {sheetIndex : Type*} [Finite sheetIndex]
    (polynomial : sheetIndex → ℂ[X])
    (multiplier base : ℂ)
    (multiplier_nonzero : multiplier ≠ 0)
    (base_nonzero : base ≠ 0)
    (no_torsion : ∀ order : ℕ, 0 < order → multiplier ^ order ≠ 1)
    (returnIndex : ℕ → ℕ)
    (returnIndex_injective : Function.Injective returnIndex)
    (sheetAt : ℕ → sheetIndex)
    (polynomial_nonzero : ∀ order : ℕ,
      polynomial (sheetAt order) ≠ 0)
    (relation : ∀ order : ℕ,
      (polynomial (sheetAt order)).IsRoot
        (multiplier ^ (returnIndex order) * base)) :
    False := by
  apply no_injective_orbit_over_finite_polynomial_cover
    polynomial
    (fun order => multiplier ^ (returnIndex order) * base)
    _ sheetAt polynomial_nonzero relation
  exact (scaled_power_orbit_injective multiplier base multiplier_nonzero
    base_nonzero no_torsion).comp returnIndex_injective

end FormalFinitePolynomialCoverOrbitEscape
