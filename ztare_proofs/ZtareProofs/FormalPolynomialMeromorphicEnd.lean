import Mathlib.Tactic
import ZtareProofs.FormalMeromorphicSheetEntry

/-!
# Constructed sheet for a meromorphic polynomial-flow end

This file composes unconditional local polynomial infinity-sheet construction
with meromorphic-pole entry.  Its only continuation datum is an already
realized negative-order meromorphic branch in a finite ramified coordinate.
-/

namespace FormalPolynomialMeromorphicEnd

open Filter Polynomial
open scoped Topology

open FormalAnalyticReciprocalSheetEntry
open FormalMeromorphicSheetEntry
open FormalPolynomialRamifiedTrajectorySheet

/-- Every negative-order meromorphic end for an exact degree-at-least-two
polynomial enters a canonically constructed local infinity sheet. -/
theorem polynomial_meromorphic_end_sheet_entry_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ) (infinityTime center : ℂ)
      (branch : ℂ → ℂ),
      p.natDegree = degree →
      2 ≤ degree →
      MeromorphicAt branch center →
      meromorphicOrderAt branch center < 0 →
      ∃ constructed : ConstructedPolynomialInfinitySheet
          p degree infinityTime,
        ∃ reciprocal : ℂ → ℂ,
          branch⁻¹ =ᶠ[𝓝[≠] center] reciprocal ∧
          AnalyticAt ℂ reciprocal center ∧
          reciprocal center = 0 ∧
          Nonempty (AnalyticReciprocalSheetEntry (center := center)
            constructed reciprocal) := by
  intro p degree infinityTime center branch hdegree htwo
    hmeromorphic hnegative
  obtain ⟨constructed⟩ :=
    polynomial_infinity_local_sheet_exists_terminal_certificate
      p degree infinityTime hdegree htwo
  obtain ⟨reciprocal, hreciprocal, hanalytic, hzero, hentry⟩ :=
    meromorphic_pole_enters_constructed_sheet constructed branch
      hmeromorphic hnegative
  exact ⟨constructed, reciprocal, hreciprocal, hanalytic, hzero, hentry⟩

end FormalPolynomialMeromorphicEnd
