import ZtareProofs.FormalMeromorphicInfinityChart

/-!
# Inference from a meromorphic puncture to a classified reciprocal escape

This theorem owns the coverage edge joining the meromorphic reciprocal-chart
kernel to a caller-supplied identification of that chart with its normalized
projective time coordinate.
-/

namespace FormalMeromorphicInfinityChartInference

open FormalAnalyticPuncturedExtension
open FormalMeromorphicInfinityChart

/-- Meromorphicity and failure of finite analytic extension construct the
reciprocal chart; any caller-supplied identification of that chart yields the
declared escape proposition. -/
theorem meromorphic_reciprocal_escape_inference_terminal_certificate :
    ∀ (branch : ℂ → ℂ) (center : ℂ) (Escape : Prop),
      MeromorphicAt branch center →
      (¬HasFiniteAnalyticExtension branch center) →
      (HasAnalyticReciprocalChart branch center → Escape) →
      Escape := by
  intro branch center Escape hmeromorphic hnoExtension hclassify
  exact hclassify
    (meromorphic_infinity_chart_terminal_certificate
      branch center hmeromorphic hnoExtension).2.2

end FormalMeromorphicInfinityChartInference
