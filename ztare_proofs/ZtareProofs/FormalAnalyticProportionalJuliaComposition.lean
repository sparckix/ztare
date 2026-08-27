import Mathlib.Analysis.Analytic.IsolatedZeros
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticTwoJuliaAbelCollision

/-!
# Local Julia composition on the proportional generator branch

Two parameterized Julia identities on one ramified sheet can be glued when
their generators agree.  Cancellation uses only the hidden derivative on the
punctured sheet; the ramified source derivative is never divided out.  An
analytic identity theorem then fills the center.
-/

namespace FormalAnalyticProportionalJuliaComposition

open Filter Polynomial
open scoped Topology
open FormalAnalyticTwoJuliaAbelCollision

/-- Pointwise algebra behind proportional Julia composition. -/
theorem parameterized_same_generator_julia
    (generator : ℂ[X])
    (source target hidden sourceDerivative targetDerivative
      hiddenDerivative spatialDerivative : ℂ)
    (hinner :
      hiddenDerivative * generator.eval source =
        sourceDerivative * generator.eval hidden)
    (houter :
      hiddenDerivative * generator.eval target =
        targetDerivative * generator.eval hidden)
    (hderivativeCompatibility :
      targetDerivative = spatialDerivative * sourceDerivative)
    (hhiddenDerivative : hiddenDerivative ≠ 0) :
    generator.eval target = spatialDerivative * generator.eval source := by
  apply mul_left_cancel₀ hhiddenDerivative
  calc
    hiddenDerivative * generator.eval target =
        targetDerivative * generator.eval hidden := houter
    _ = (spatialDerivative * sourceDerivative) *
        generator.eval hidden := by rw [hderivativeCompatibility]
    _ = spatialDerivative *
        (sourceDerivative * generator.eval hidden) := by ring
    _ = spatialDerivative *
        (hiddenDerivative * generator.eval source) := by rw [hinner]
    _ = hiddenDerivative *
        (spatialDerivative * generator.eval source) := by ring

/-- Equal generators and parameter-derivative compatibility produce Julia's
identity for the complete endpoint on the punctured uniformizer germ. -/
theorem TwoJuliaAbelCarrier.endpoint_julia_nhdsNE_of_generators_eq
    (carrier : TwoJuliaAbelCarrier)
    (spatialDerivative : ℂ → ℂ)
    (hgenerators : carrier.firstGenerator = carrier.secondGenerator)
    (hderivativeCompatibility :
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        fun t ↦ spatialDerivative t * carrier.sourceDerivative t)
    (hhiddenDerivative :
      ∀ᶠ t in 𝓝[≠] carrier.center, carrier.hiddenDerivative t ≠ 0) :
    (fun t ↦ carrier.firstGenerator.eval (carrier.target t)) =ᶠ[
        𝓝[≠] carrier.center]
      fun t ↦ spatialDerivative t *
        carrier.firstGenerator.eval (carrier.source t) := by
  filter_upwards [carrier.punctured_mem, hderivativeCompatibility,
      hhiddenDerivative] with t ht hcompat hhidden
  have houter := carrier.outer_julia t ht
  rw [← hgenerators] at houter
  exact parameterized_same_generator_julia carrier.firstGenerator
    (carrier.source t) (carrier.target t) (carrier.hidden t)
    (carrier.sourceDerivative t) (carrier.targetDerivative t)
    (carrier.hiddenDerivative t) (spatialDerivative t)
    (carrier.inner_julia t ht) houter hcompat hhidden

/-- Analyticity extends the punctured endpoint Julia identity across the
uniformizer center. -/
theorem TwoJuliaAbelCarrier.endpoint_julia_nhds_of_generators_eq
    (carrier : TwoJuliaAbelCarrier)
    (spatialDerivative : ℂ → ℂ)
    (hgenerators : carrier.firstGenerator = carrier.secondGenerator)
    (hspatialDerivative :
      AnalyticAt ℂ spatialDerivative carrier.center)
    (hderivativeCompatibility :
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        fun t ↦ spatialDerivative t * carrier.sourceDerivative t)
    (hhiddenDerivative :
      ∀ᶠ t in 𝓝[≠] carrier.center, carrier.hiddenDerivative t ≠ 0) :
    (fun t ↦ carrier.firstGenerator.eval (carrier.target t)) =ᶠ[
        𝓝 carrier.center]
      fun t ↦ spatialDerivative t *
        carrier.firstGenerator.eval (carrier.source t) := by
  have hleft : AnalyticAt ℂ
      (fun t ↦ carrier.firstGenerator.eval (carrier.target t))
      carrier.center :=
    carrier.target_analytic.aeval_polynomial carrier.firstGenerator
  have hright : AnalyticAt ℂ
      (fun t ↦ spatialDerivative t *
        carrier.firstGenerator.eval (carrier.source t)) carrier.center :=
    hspatialDerivative.mul
      (carrier.source_analytic.aeval_polynomial carrier.firstGenerator)
  apply (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
    hleft.continuousAt hright.continuousAt).mp
  exact TwoJuliaAbelCarrier.endpoint_julia_nhdsNE_of_generators_eq
    carrier spatialDerivative hgenerators hderivativeCompatibility
    hhiddenDerivative

/-- Aggregated local proportional-branch surface. -/
theorem analytic_proportional_julia_composition_terminal_certificate :
    ∀ (carrier : TwoJuliaAbelCarrier)
      (spatialDerivative : ℂ → ℂ),
      carrier.firstGenerator = carrier.secondGenerator →
      AnalyticAt ℂ spatialDerivative carrier.center →
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        (fun t ↦ spatialDerivative t * carrier.sourceDerivative t) →
      (∀ᶠ t in 𝓝[≠] carrier.center,
        carrier.hiddenDerivative t ≠ 0) →
      (fun t ↦ carrier.firstGenerator.eval (carrier.target t)) =ᶠ[
          𝓝 carrier.center]
        fun t ↦ spatialDerivative t *
          carrier.firstGenerator.eval (carrier.source t) := by
  intro carrier spatialDerivative hgenerators hspatialDerivative
    hderivativeCompatibility hhiddenDerivative
  exact TwoJuliaAbelCarrier.endpoint_julia_nhds_of_generators_eq
    carrier spatialDerivative hgenerators hspatialDerivative
    hderivativeCompatibility hhiddenDerivative

end FormalAnalyticProportionalJuliaComposition
