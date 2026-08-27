import ZtareProofs.FormalPolynomialInfinityRamification

/-!
# Inference from constructed polynomial ramification to a selected branch

The caller retains only the identification of the continued trajectory with
the constructed ramified inverse germ.
-/

namespace FormalPolynomialInfinityRamificationInference

open Filter Polynomial
open scoped Topology
open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialInfinityRamification

/-- The constructed polynomial infinity ramification yields any branch
classification that the caller proves from its exact data. -/
theorem polynomial_infinity_ramification_inference_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ) (ClassifiedBranch : Prop),
      p.natDegree = degree →
      2 ≤ degree →
      ((∃ (timeCoordinate : ℂ → ℂ) (unit : ℂ)
          (coordinate inverseCoordinate : ℂ → ℂ),
          AnalyticAt ℂ timeCoordinate 0 ∧
          timeCoordinate 0 = 0 ∧
          (∀ᶠ z in 𝓝 0,
            HasDerivAt timeCoordinate
              (reciprocalTimeIntegrand p degree z) z) ∧
          analyticOrderAt timeCoordinate 0 = (degree - 1 : ℕ) ∧
          degree - 1 ≠ 0 ∧
          unit ≠ 0 ∧
          AnalyticAt ℂ coordinate 0 ∧
          coordinate 0 = 0 ∧
          deriv coordinate 0 = 1 ∧
          (timeCoordinate =ᶠ[𝓝 0]
            fun z ↦ unit * coordinate z ^ (degree - 1)) ∧
          AnalyticAt ℂ inverseCoordinate 0 ∧
          inverseCoordinate 0 = 0 ∧
          (∀ᶠ w in 𝓝 0,
            coordinate (inverseCoordinate w) = w)) →
        ClassifiedBranch) →
      ClassifiedBranch := by
  intro p degree ClassifiedBranch hdegree htwo hclassify
  exact hclassify
    (polynomial_infinity_ramification_terminal_certificate
      p degree hdegree htwo)

end FormalPolynomialInfinityRamificationInference
