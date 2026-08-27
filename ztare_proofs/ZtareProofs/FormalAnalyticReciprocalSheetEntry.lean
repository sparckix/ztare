import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticSheetOverlap

/-!
# Entry of an analytic reciprocal germ into a constructed infinity sheet

An incoming reciprocal germ that is analytic, vanishes at its approach
center, and is nonzero on a punctured neighborhood canonically enters the
constructed polynomial infinity sheet.  The transition is the constructed
normal coordinate composed with the incoming reciprocal germ.

This is local chart geometry.  The theorem does not construct the incoming
reciprocal germ from a bare finite continuation and does not classify all
continuation ends.
-/

namespace FormalAnalyticReciprocalSheetEntry

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialRamifiedTrajectorySheet

/-- A germ-level overlap between an incoming reciprocal continuation and a
constructed polynomial infinity sheet. -/
structure AnalyticReciprocalSheetEntry
    {p : ℂ[X]} {degree : ℕ} {infinityTime center : ℂ}
    (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime)
    (incomingReciprocal : ℂ → ℂ) where
  transition : ℂ → ℂ
  transition_analytic : AnalyticAt ℂ transition center
  transition_zero : transition center = 0
  transition_nonzero : ∀ᶠ t in 𝓝[≠] center, transition t ≠ 0
  mapsTo_sheet : ∀ᶠ t in 𝓝[≠] center,
    transition t ∈ constructed.sheet.domain
  reciprocal_compatible : incomingReciprocal =ᶠ[𝓝[≠] center]
    constructed.sheet.reciprocal ∘ transition

/-- The analytic right inverse stored by a constructed sheet is also a local
left inverse of its derivative-one normal coordinate. -/
theorem inverseCoordinate_comp_coordinate
    {p : ℂ[X]} {degree : ℕ} {infinityTime : ℂ}
    (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime) :
    constructed.inverseCoordinate ∘ constructed.coordinate =ᶠ[𝓝 0]
      fun z ↦ z := by
  have hstrict : HasStrictDerivAt constructed.coordinate 1 0 := by
    simpa only [constructed.coordinateDerivative] using
      constructed.coordinateAnalytic.hasStrictDerivAt
  let localInverse := hstrict.localInverse constructed.coordinate 1 0 one_ne_zero
  have hleft : localInverse ∘ constructed.coordinate =ᶠ[𝓝 0]
      fun z ↦ z := by
    simpa only [localInverse, constructed.coordinateZero] using
      hstrict.eventually_left_inverse one_ne_zero
  have hinverseTendsto :
      Tendsto constructed.inverseCoordinate (𝓝 0) (𝓝 0) := by
    have hcontinuous := constructed.inverseAnalytic.continuousAt
    change Tendsto constructed.inverseCoordinate (𝓝 0)
      (𝓝 (constructed.inverseCoordinate 0)) at hcontinuous
    simpa only [constructed.inverseZero] using hcontinuous
  have hleftAtInverse : ∀ᶠ w in 𝓝 0,
      localInverse
          (constructed.coordinate (constructed.inverseCoordinate w)) =
        constructed.inverseCoordinate w := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleft hinverseTendsto
  have hlocalInverseEq : localInverse =ᶠ[𝓝 0]
      constructed.inverseCoordinate := by
    filter_upwards [hleftAtInverse, constructed.coordinate_rightInverse]
      with w hleftW hrightW
    calc
      localInverse w = localInverse
          (constructed.coordinate (constructed.inverseCoordinate w)) :=
        congrArg localInverse hrightW.symm
      _ = constructed.inverseCoordinate w := hleftW
  have hcoordinateTendsto :
      Tendsto constructed.coordinate (𝓝 0) (𝓝 0) := by
    have hcontinuous := constructed.coordinateAnalytic.continuousAt
    change Tendsto constructed.coordinate (𝓝 0)
      (𝓝 (constructed.coordinate 0)) at hcontinuous
    simpa only [constructed.coordinateZero] using hcontinuous
  have hlocalAtCoordinate : ∀ᶠ z in 𝓝 0,
      localInverse (constructed.coordinate z) =
        constructed.inverseCoordinate (constructed.coordinate z) := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hlocalInverseEq hcoordinateTendsto
  filter_upwards [hleft, hlocalAtCoordinate] with z hleftZ hlocalZ
  calc
    constructed.inverseCoordinate (constructed.coordinate z) =
        localInverse (constructed.coordinate z) := hlocalZ.symm
    _ = z := by simpa only [Function.comp_apply] using hleftZ

/-- Every nontrivial analytic reciprocal germ approaching zero canonically
enters the constructed sheet through the normal-coordinate transition. -/
noncomputable def AnalyticReciprocalSheetEntry.ofAnalyticGerm
    {p : ℂ[X]} {degree : ℕ} {infinityTime center : ℂ}
    (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime)
    (incomingReciprocal : ℂ → ℂ)
    (hincomingAnalytic : AnalyticAt ℂ incomingReciprocal center)
    (hincomingZero : incomingReciprocal center = 0)
    (hincomingNonzero : ∀ᶠ t in 𝓝[≠] center,
      incomingReciprocal t ≠ 0) :
    AnalyticReciprocalSheetEntry (center := center)
      constructed incomingReciprocal := by
  let transition : ℂ → ℂ :=
    constructed.coordinate ∘ incomingReciprocal
  have hincomingTendsto :
      Tendsto incomingReciprocal (𝓝 center) (𝓝 0) := by
    have hcontinuous := hincomingAnalytic.continuousAt
    change Tendsto incomingReciprocal (𝓝 center)
      (𝓝 (incomingReciprocal center)) at hcontinuous
    simpa only [hincomingZero] using hcontinuous
  have htransitionAnalytic : AnalyticAt ℂ transition center := by
    exact constructed.coordinateAnalytic.comp_of_eq
      hincomingAnalytic hincomingZero
  have htransitionZero : transition center = 0 := by
    simp only [transition, Function.comp_apply, hincomingZero,
      constructed.coordinateZero]
  have hleftIncoming : ∀ᶠ t in 𝓝 center,
      constructed.inverseCoordinate (constructed.coordinate
        (incomingReciprocal t)) = incomingReciprocal t := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto
        (inverseCoordinate_comp_coordinate constructed)
        hincomingTendsto
  have hcompatible : incomingReciprocal =ᶠ[𝓝 center]
      constructed.sheet.reciprocal ∘ transition := by
    filter_upwards [hleftIncoming] with t ht
    simp only [transition, Function.comp_apply,
      constructed.sheet_reciprocal_eq_inverse]
    exact ht.symm
  have hcompatiblePunctured : incomingReciprocal =ᶠ[𝓝[≠] center]
      constructed.sheet.reciprocal ∘ transition :=
    hcompatible.filter_mono nhdsWithin_le_nhds
  have htransitionNonzero : ∀ᶠ t in 𝓝[≠] center,
      transition t ≠ 0 := by
    filter_upwards [hcompatiblePunctured, hincomingNonzero]
      with t hcompat hnonzero htransitionZeroAt
    apply hnonzero
    rw [hcompat, Function.comp_apply, htransitionZeroAt,
      constructed.sheet_reciprocal_eq_inverse,
      constructed.inverseZero]
  have htransitionTendsto : Tendsto transition (𝓝 center) (𝓝 0) := by
    have hcontinuous := htransitionAnalytic.continuousAt
    change Tendsto transition (𝓝 center) (𝓝 (transition center)) at hcontinuous
    simpa only [htransitionZero] using hcontinuous
  have htransitionTendstoPunctured :
      Tendsto transition (𝓝[≠] center) (𝓝[≠] 0) := by
    rw [tendsto_nhdsWithin_iff]
    exact ⟨htransitionTendsto.mono_left nhdsWithin_le_nhds,
      htransitionNonzero⟩
  have hmapsToSheet : ∀ᶠ t in 𝓝[≠] center,
      transition t ∈ constructed.sheet.domain :=
    htransitionTendstoPunctured constructed.sheet.punctured_mem
  exact {
    transition := transition
    transition_analytic := htransitionAnalytic
    transition_zero := htransitionZero
    transition_nonzero := htransitionNonzero
    mapsTo_sheet := hmapsToSheet
    reciprocal_compatible := hcompatiblePunctured
  }

/-- Aggregated reusable certificate for analytic reciprocal entry into a
constructed polynomial infinity sheet. -/
theorem analytic_reciprocal_sheet_entry_terminal_certificate :
    ∀ {p : ℂ[X]} {degree : ℕ} {infinityTime center : ℂ}
      (constructed : ConstructedPolynomialInfinitySheet p degree infinityTime)
      (incomingReciprocal : ℂ → ℂ),
      AnalyticAt ℂ incomingReciprocal center →
      incomingReciprocal center = 0 →
      (∀ᶠ t in 𝓝[≠] center, incomingReciprocal t ≠ 0) →
      Nonempty (AnalyticReciprocalSheetEntry (center := center)
        constructed incomingReciprocal) := by
  intro p degree infinityTime center constructed incomingReciprocal
    hanalytic hzero hnonzero
  exact ⟨AnalyticReciprocalSheetEntry.ofAnalyticGerm constructed
    incomingReciprocal hanalytic hzero hnonzero⟩

end FormalAnalyticReciprocalSheetEntry
