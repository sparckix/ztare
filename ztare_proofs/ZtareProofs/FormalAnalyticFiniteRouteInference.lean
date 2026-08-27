import ZtareProofs.FormalAnalyticFiniteRoute

/-!
# Inference from finite-route failure to a classified escape

This proposition is intentionally separate from the finite-route leaf so a
formal-coverage DAG does not reuse one governed proposition identity in two
claim roles.
-/

namespace FormalAnalyticFiniteRouteInference

open FormalAnalyticFiniteRoute

/-- If a nonanalytic composition forces a factor out of its finite analytic
chart, any caller-supplied classification of such failures yields the
caller's escape conclusion. -/
theorem finite_or_classified_escape_inference_terminal_certificate :
    ∀ (inner outer : ℂ → ℂ) (x₀ : ℂ) (Escape : Prop),
      (¬AnalyticAt ℂ (outer ∘ inner) x₀) →
      ((¬AnalyticAt ℂ inner x₀ ∨
        ¬AnalyticAt ℂ outer (inner x₀)) → Escape) →
      Escape := by
  intro inner outer x₀ Escape hcomposition hclassify
  exact @escape_of_nonanalytic_composition
    inner outer x₀ Escape hcomposition hclassify

end FormalAnalyticFiniteRouteInference
