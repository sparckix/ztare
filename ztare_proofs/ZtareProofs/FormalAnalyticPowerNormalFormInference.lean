import ZtareProofs.FormalAnalyticPowerNormalForm

/-!
# Inference from analytic power normal form to a selected ramified branch

This proposition owns the coverage edge from the constructed analytic power
coordinate to a caller-supplied identification with its selected polynomial
flow branch.
-/

namespace FormalAnalyticPowerNormalFormInference

open Filter
open scoped Topology
open FormalAnalyticPowerNormalForm

/-- A positive finite-order analytic time coordinate supplies its constructed
ramified inverse; any caller-supplied identification of that inverse with the
selected branch yields the declared branch-classification proposition. -/
theorem analytic_power_normal_form_inference_terminal_certificate :
    ∀ (timeCoordinate : ℂ → ℂ) (center : ℂ) (order : ℕ)
      (ClassifiedBranch : Prop),
      AnalyticAt ℂ timeCoordinate center →
      analyticOrderAt timeCoordinate center = order →
      order ≠ 0 →
      ((∃ (unit : ℂ) (coordinate inverseCoordinate : ℂ → ℂ),
          unit ≠ 0 ∧
          AnalyticAt ℂ coordinate center ∧
          coordinate center = 0 ∧
          deriv coordinate center = 1 ∧
          (timeCoordinate =ᶠ[𝓝 center]
            fun z ↦ unit * coordinate z ^ order) ∧
          AnalyticAt ℂ inverseCoordinate 0 ∧
          inverseCoordinate 0 = center ∧
          (∀ᶠ w in 𝓝 0, coordinate (inverseCoordinate w) = w)) →
        ClassifiedBranch) →
      ClassifiedBranch := by
  intro timeCoordinate center order ClassifiedBranch hanalytic horder
    hpositive hclassify
  exact hclassify
    (analytic_power_normal_form_terminal_certificate
      timeCoordinate center order hanalytic horder hpositive)

end FormalAnalyticPowerNormalFormInference
