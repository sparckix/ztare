import ZtareProofs.FormalAnalyticPuncturedExtension

/-!
# Inference from a nonremovable punctured branch to a classified escape

This theorem owns the DAG edge joining removable-singularity unboundedness to
a caller-supplied projective escape classification.
-/

namespace FormalAnalyticPuncturedEscapeInference

open Filter
open scoped Topology
open FormalAnalyticPuncturedExtension

/-- A punctured holomorphic branch with no finite analytic extension is
unbounded; any classification of that unboundedness therefore yields the
declared escape proposition. -/
theorem punctured_unbounded_escape_inference_terminal_certificate :
    ∀ (branch : ℂ → ℂ) (center : ℂ) (Escape : Prop),
      (∀ᶠ z in 𝓝[≠] center, DifferentiableAt ℂ branch z) →
      (¬HasFiniteAnalyticExtension branch center) →
      ((¬IsBoundedUnder (· ≤ ·) (𝓝[≠] center)
        (fun z ↦ ‖branch z - branch center‖)) → Escape) →
      Escape := by
  intro branch center Escape hdifferentiable hnoExtension hclassify
  exact hclassify
    (not_bounded_of_no_finite_analytic_extension
      hdifferentiable hnoExtension)

end FormalAnalyticPuncturedEscapeInference
