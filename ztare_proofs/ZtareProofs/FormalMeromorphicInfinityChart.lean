import Mathlib.Analysis.Meromorphic.Order
import ZtareProofs.FormalAnalyticPuncturedExtension
import Mathlib.Tactic

/-!
# Meromorphic passage to the reciprocal infinity chart

After a selected branch has been shown meromorphic in a declared ramified
coordinate, meromorphic order makes the finite-versus-infinity alternative
exact.  A branch without a finite analytic extension has negative order,
converges to the cobounded filter, and has an analytic reciprocal extension
vanishing at the branch point.
-/

namespace FormalMeromorphicInfinityChart

open Filter Set
open scoped Topology
open FormalAnalyticPuncturedExtension

/-- The reciprocal of a punctured branch extends analytically with value zero
at `center`. -/
def HasAnalyticReciprocalChart (branch : ℂ → ℂ) (center : ℂ) : Prop :=
  ∃ reciprocal : ℂ → ℂ,
    branch⁻¹ =ᶠ[𝓝[≠] center] reciprocal ∧
      AnalyticAt ℂ reciprocal center ∧ reciprocal center = 0

/-- A meromorphic branch of nonnegative order has a finite analytic
extension. -/
theorem hasFiniteAnalyticExtension_of_meromorphicOrderAt_nonneg
    {branch : ℂ → ℂ} {center : ℂ}
    (hmeromorphic : MeromorphicAt branch center)
    (horder : 0 ≤ meromorphicOrderAt branch center) :
    HasFiniteAnalyticExtension branch center := by
  obtain ⟨limitValue, hlimit⟩ :=
    tendsto_nhds_of_meromorphicOrderAt_nonneg hmeromorphic horder
  let extension := Function.update branch center limitValue
  have hmeromorphicExtension : MeromorphicAt extension center := by
    exact hmeromorphic.update center limitValue
  have hcontinuousExtension : ContinuousAt extension center := by
    exact continuousAt_update_same.mpr hlimit
  refine ⟨extension, ?_, hmeromorphicExtension.analyticAt hcontinuousExtension⟩
  filter_upwards [self_mem_nhdsWithin] with z hz
  have hzc : z ≠ center := by simpa only [mem_compl_iff, mem_singleton_iff]
    using hz
  exact (Function.update_of_ne hzc limitValue branch).symm

/-- A meromorphic branch with no finite analytic extension has negative
order and therefore converges to projective infinity. -/
theorem negative_order_and_cobounded_of_no_finite_extension
    {branch : ℂ → ℂ} {center : ℂ}
    (hmeromorphic : MeromorphicAt branch center)
    (hnoExtension : ¬HasFiniteAnalyticExtension branch center) :
    meromorphicOrderAt branch center < 0 ∧
      Tendsto branch (𝓝[≠] center) (Bornology.cobounded ℂ) := by
  have hnegative : meromorphicOrderAt branch center < 0 := by
    by_contra hnot
    have hnonnegative : 0 ≤ meromorphicOrderAt branch center :=
      le_of_not_gt hnot
    exact hnoExtension
      (hasFiniteAnalyticExtension_of_meromorphicOrderAt_nonneg
        hmeromorphic hnonnegative)
  exact ⟨hnegative,
    tendsto_cobounded_of_meromorphicOrderAt_neg hnegative⟩

/-- Negative meromorphic order constructs an analytic reciprocal chart whose
center value is zero. -/
theorem hasAnalyticReciprocalChart_of_negative_order
    {branch : ℂ → ℂ} {center : ℂ}
    (hmeromorphic : MeromorphicAt branch center)
    (hnegative : meromorphicOrderAt branch center < 0) :
    HasAnalyticReciprocalChart branch center := by
  have hinversePositive :
      0 < meromorphicOrderAt branch⁻¹ center := by
    rw [meromorphicOrderAt_inv]
    exact LinearOrderedAddCommGroupWithTop.neg_pos.mpr (Or.inl hnegative)
  have hinverseTends : Tendsto branch⁻¹ (𝓝[≠] center) (𝓝 0) :=
    tendsto_zero_of_meromorphicOrderAt_pos hinversePositive
  let reciprocal := Function.update branch⁻¹ center 0
  have hmeromorphicReciprocal : MeromorphicAt reciprocal center := by
    exact hmeromorphic.inv.update center 0
  have hcontinuousReciprocal : ContinuousAt reciprocal center := by
    exact continuousAt_update_same.mpr hinverseTends
  refine ⟨reciprocal, ?_,
    hmeromorphicReciprocal.analyticAt hcontinuousReciprocal, ?_⟩
  · filter_upwards [self_mem_nhdsWithin] with z hz
    have hzc : z ≠ center := by simpa only [mem_compl_iff, mem_singleton_iff]
      using hz
    exact (Function.update_of_ne hzc 0 branch⁻¹).symm
  · simp [reciprocal]

/-- Aggregated meromorphic infinity-chart certificate.  Meromorphicity is
the remaining caller-owned ramified-branch classification premise. -/
theorem meromorphic_infinity_chart_terminal_certificate :
    ∀ (branch : ℂ → ℂ) (center : ℂ),
      MeromorphicAt branch center →
      (¬HasFiniteAnalyticExtension branch center) →
      meromorphicOrderAt branch center < 0 ∧
      Tendsto branch (𝓝[≠] center) (Bornology.cobounded ℂ) ∧
      HasAnalyticReciprocalChart branch center := by
  intro branch center hmeromorphic hnoExtension
  obtain ⟨hnegative, hcobounded⟩ :=
    negative_order_and_cobounded_of_no_finite_extension
      hmeromorphic hnoExtension
  exact ⟨hnegative, hcobounded,
    hasAnalyticReciprocalChart_of_negative_order
      hmeromorphic hnegative⟩

end FormalMeromorphicInfinityChart
