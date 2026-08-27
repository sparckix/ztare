import Mathlib.Analysis.Complex.RemovableSingularity
import Mathlib.Tactic

/-!
# Finite analytic extension of a punctured branch

The governing property is agreement with some analytic germ, rather than the
arbitrary value assigned to a punctured branch at its missing center.
Riemann's removable-singularity theorem supplies such an extension whenever
the branch is holomorphic and locally bounded on the punctured neighborhood.
-/

namespace FormalAnalyticPuncturedExtension

open Filter Set
open scoped Topology

/-- A punctured complex branch has a finite analytic extension at `center` if
it agrees near, but away from, `center` with an analytic germ there. -/
def HasFiniteAnalyticExtension (branch : ℂ → ℂ) (center : ℂ) : Prop :=
  ∃ extension : ℂ → ℂ,
    branch =ᶠ[𝓝[≠] center] extension ∧
      AnalyticAt ℂ extension center

/-- Punctured holomorphy and local boundedness construct a finite analytic
extension by updating the center to the punctured limit. -/
theorem hasFiniteAnalyticExtension_of_bounded
    {branch : ℂ → ℂ} {center : ℂ}
    (hdifferentiable :
      ∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ branch z)
    (hbounded :
      IsBoundedUnder (· ≤ ·) (𝓝[≠] center)
        fun z ↦ ‖branch z - branch center‖) :
    HasFiniteAnalyticExtension branch center := by
  let limitValue := limUnder (𝓝[≠] center) branch
  let extension := Function.update branch center limitValue
  have hlimit : Tendsto branch (𝓝[≠] center) (𝓝 limitValue) := by
    exact Complex.tendsto_limUnder_of_differentiable_on_punctured_nhds_of_bounded_under
      hdifferentiable hbounded
  have hcontinuous : ContinuousAt extension center := by
    exact continuousAt_update_same.mpr hlimit
  have hextensionDifferentiable :
      ∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ extension z := by
    filter_upwards [hdifferentiable, self_mem_nhdsWithin] with z hdiff hz
    have hzc : z ≠ center := by simpa only [mem_compl_iff, mem_singleton_iff]
      using hz
    apply DifferentiableAt.congr_of_eventuallyEq hdiff
    filter_upwards [eventually_ne_nhds hzc] with w hw
    exact Function.update_of_ne hw limitValue branch
  refine ⟨extension, ?_, ?_⟩
  · filter_upwards [self_mem_nhdsWithin] with z hz
    have hzc : z ≠ center := by simpa only [mem_compl_iff, mem_singleton_iff]
      using hz
    exact (Function.update_of_ne hzc limitValue branch).symm
  · exact Complex.analyticAt_of_differentiable_on_punctured_nhds_of_continuousAt
      hextensionDifferentiable hcontinuous

/-- Contrapositive removable-singularity result: a punctured holomorphic
branch with no finite analytic extension cannot be locally bounded. -/
theorem not_bounded_of_no_finite_analytic_extension
    {branch : ℂ → ℂ} {center : ℂ}
    (hdifferentiable :
      ∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ branch z)
    (hnoExtension : ¬HasFiniteAnalyticExtension branch center) :
    ¬IsBoundedUnder (· ≤ ·) (𝓝[≠] center)
      (fun z ↦ ‖branch z - branch center‖) := by
  intro hbounded
  exact hnoExtension
    (hasFiniteAnalyticExtension_of_bounded hdifferentiable hbounded)

/-- Aggregated punctured-extension certificate. -/
theorem punctured_extension_terminal_certificate :
    (∀ (branch : ℂ → ℂ) (center : ℂ),
      (∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ branch z) →
      IsBoundedUnder (· ≤ ·) (𝓝[≠] center)
        (fun z ↦ ‖branch z - branch center‖) →
      HasFiniteAnalyticExtension branch center) ∧
    (∀ (branch : ℂ → ℂ) (center : ℂ),
      (∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ branch z) →
      (¬HasFiniteAnalyticExtension branch center) →
      ¬IsBoundedUnder (· ≤ ·) (𝓝[≠] center)
        (fun z ↦ ‖branch z - branch center‖)) := by
  exact ⟨
    fun branch center ↦
      @hasFiniteAnalyticExtension_of_bounded branch center,
    fun branch center ↦
      @not_bounded_of_no_finite_analytic_extension branch center⟩

end FormalAnalyticPuncturedExtension
