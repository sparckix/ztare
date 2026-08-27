import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Analysis.Normed.Field.Lemmas
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticReciprocalSheetEntry
import ZtareProofs.FormalMeromorphicInfinityChart

/-!
# Meromorphic pole entry into a polynomial infinity sheet

A negative-order meromorphic branch has an analytic reciprocal germ that
vanishes, but is nonzero, on a punctured neighborhood.  The canonical normal
coordinate of any constructed polynomial infinity sheet therefore produces a
germ-level overlap with that reciprocal branch.

Finite ramification or meromorphicity of an arbitrary selected continuation
is not proved here.
-/

namespace FormalMeromorphicSheetEntry

open Filter Polynomial Set
open scoped Topology

open FormalAnalyticReciprocalSheetEntry
open FormalMeromorphicInfinityChart
open FormalPolynomialRamifiedTrajectorySheet

/-- A negative-order meromorphic branch enters every supplied constructed
polynomial infinity sheet through its analytic reciprocal chart. -/
theorem meromorphic_pole_enters_constructed_sheet
    {p : ℂ[X]} {degree : ℕ} {infinityTime center : ℂ}
    (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime)
    (branch : ℂ → ℂ)
    (hmeromorphic : MeromorphicAt branch center)
    (hnegative : meromorphicOrderAt branch center < 0) :
    ∃ reciprocal : ℂ → ℂ,
      branch⁻¹ =ᶠ[𝓝[≠] center] reciprocal ∧
      AnalyticAt ℂ reciprocal center ∧
      reciprocal center = 0 ∧
      Nonempty (AnalyticReciprocalSheetEntry (center := center)
        constructed reciprocal) := by
  obtain ⟨reciprocal, hreciprocal, hanalytic, hzero⟩ :=
    hasAnalyticReciprocalChart_of_negative_order hmeromorphic hnegative
  have hcobounded :
      Tendsto branch (𝓝[≠] center) (Bornology.cobounded ℂ) :=
    tendsto_cobounded_of_meromorphicOrderAt_neg hnegative
  have hnorm : ∀ᶠ z in 𝓝[≠] center, 1 ≤ ‖branch z‖ :=
    hcobounded (eventually_cobounded_le_norm 1)
  have hbranchNonzero : ∀ᶠ z in 𝓝[≠] center, branch z ≠ 0 := by
    filter_upwards [hnorm] with z hz hbranchZero
    rw [hbranchZero, norm_zero] at hz
    norm_num at hz
  have hreciprocalNonzero : ∀ᶠ z in 𝓝[≠] center,
      reciprocal z ≠ 0 := by
    filter_upwards [hreciprocal, hbranchNonzero]
      with z hreciprocalZ hbranchZ
    rw [← hreciprocalZ]
    exact inv_ne_zero hbranchZ
  exact ⟨reciprocal, hreciprocal, hanalytic, hzero,
    ⟨AnalyticReciprocalSheetEntry.ofAnalyticGerm constructed reciprocal
      hanalytic hzero hreciprocalNonzero⟩⟩

/-- Aggregated terminal surface for the meromorphic-pole-to-sheet entry
mechanism. -/
theorem meromorphic_sheet_entry_terminal_certificate :
    ∀ {p : ℂ[X]} {degree : ℕ} {infinityTime center : ℂ}
      (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime)
      (branch : ℂ → ℂ),
      MeromorphicAt branch center →
      meromorphicOrderAt branch center < 0 →
      ∃ reciprocal : ℂ → ℂ,
        branch⁻¹ =ᶠ[𝓝[≠] center] reciprocal ∧
        AnalyticAt ℂ reciprocal center ∧
        reciprocal center = 0 ∧
        Nonempty (AnalyticReciprocalSheetEntry (center := center)
          constructed reciprocal) := by
  intro p degree infinityTime center constructed branch
    hmeromorphic hnegative
  exact meromorphic_pole_enters_constructed_sheet constructed branch
    hmeromorphic hnegative

end FormalMeromorphicSheetEntry
