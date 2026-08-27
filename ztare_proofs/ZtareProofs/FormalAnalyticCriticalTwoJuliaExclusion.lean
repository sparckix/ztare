import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly
import ZtareProofs.FormalAnalyticProportionalJuliaComposition
import ZtareProofs.FormalAnalyticRamifiedCubicCollision
import ZtareProofs.FormalAnalyticTwoJuliaDerivativeNonvanishing

/-!
# Local critical exclusion for a complete two-Julia carrier

The critical ramified collision first forces equality of the two normalized
complex generators.  Local Julia composition then turns the two factor rows
into Julia's identity for the complete selected endpoint.  The complex
single-flow root-factor theorem excludes that remaining branch.

This theorem consumes a completed local two-Julia carrier.  It does not
construct that carrier from a global maximal continuation.
-/

namespace FormalAnalyticCriticalTwoJuliaExclusion

open Filter Polynomial
open scoped Topology

open AxiomPackJacobianCriticalPuiseuxAnalyticRealization
open AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly
open AxiomPackJacobianCriticalPuiseuxContinuation
open AxiomPackJacobianCriticalPuiseuxJuliaAssembly
open FormalAnalyticProportionalJuliaComposition
open FormalAnalyticRamifiedCubicCollision
open FormalAnalyticTwoJuliaAbelCollision
open FormalAnalyticTwoJuliaDerivativeNonvanishing
open FormalPolynomialFlowAtInfinity
open FormalPolynomialInfinityTimeCoordinate

/-- Every completed local two-Julia carrier on the selected critical chart is
inconsistent. -/
theorem critical_two_julia_carrier_impossible
    (carrier : TwoJuliaAbelCarrier)
    (continuation : SelectedRegularizedContinuation)
    (outputValue : ℝ)
    (degree ramification : ℕ)
    (hcenter : carrier.center = 0)
    (hsource : carrier.source = analyticLocalX)
    (htarget : carrier.target =
      selectedAnalyticEndpoint continuation outputValue)
    (hterminal : continuation.right 3 ≠ 0)
    (houtputValue : outputValue ≠ 0)
    (hfirstMonic : carrier.firstGenerator.IsMonicOfDegree degree)
    (hsecondMonic : carrier.secondGenerator.IsMonicOfDegree degree)
    (hfirstConstant : carrier.firstGenerator.coeff 0 = 0)
    (hsecondConstant : carrier.secondGenerator.coeff 0 = 0)
    (hfirstLinear : carrier.firstGenerator.coeff 1 = 0)
    (hsecondLinear : carrier.secondGenerator.coeff 1 = 0)
    (hdegree : 2 ≤ degree)
    (hbalance : ramification * (degree - 1) = 2)
    (hreciprocalOrder :
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ))
    (hfirstInfinityDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt carrier.firstInfinityTime
        (reciprocalTimeIntegrand carrier.firstGenerator degree z) z)
    (hsecondInfinityDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt carrier.secondInfinityTime
        (reciprocalTimeIntegrand carrier.secondGenerator degree z) z)
    (hsourceLinearJet : deriv carrier.source carrier.center = 0)
    (htargetLinearJet : deriv carrier.target carrier.center = 0)
    (hsourceCubicJet :
      iteratedDeriv 3 carrier.source carrier.center = 0)
    (htargetCubicJet :
      iteratedDeriv 3 carrier.target carrier.center = 0)
    (hderivativeCompatibility :
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        fun t ↦ selectedAnalyticDerivativeFactor continuation outputValue t *
          carrier.sourceDerivative t)
    (hhiddenDerivative :
      ∀ᶠ t in 𝓝[≠] carrier.center,
        carrier.hiddenDerivative t ≠ 0) :
    False := by
  have hgenerators :
      carrier.firstGenerator = carrier.secondGenerator :=
    normalized_generators_equal_of_critical_balance carrier
      degree ramification hfirstMonic hsecondMonic hfirstConstant
      hsecondConstant hfirstLinear hsecondLinear hdegree hbalance
      hreciprocalOrder hfirstInfinityDerivative hsecondInfinityDerivative
      hsourceLinearJet htargetLinearJet hsourceCubicJet htargetCubicJet
  have hspatialAnalytic : AnalyticAt ℂ
      (selectedAnalyticDerivativeFactor continuation outputValue)
      carrier.center := by
    rw [hcenter]
    exact selectedAnalyticDerivativeFactor_analyticAt continuation outputValue
  have hendpointJulia :=
    FormalAnalyticProportionalJuliaComposition.TwoJuliaAbelCarrier.endpoint_julia_nhds_of_generators_eq
      carrier (selectedAnalyticDerivativeFactor continuation outputValue)
      hgenerators hspatialAnalytic hderivativeCompatibility
      hhiddenDerivative
  have hendpointJuliaAtZero :
      (fun t ↦ carrier.firstGenerator.eval (carrier.target t)) =ᶠ[
          𝓝 (0 : ℂ)]
        fun t ↦ selectedAnalyticDerivativeFactor continuation outputValue t *
          carrier.firstGenerator.eval (carrier.source t) := by
    simpa only [hcenter] using hendpointJulia
  have hanalyticJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          carrier.firstGenerator) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t)
            carrier.firstGenerator := by
    rw [← hsource, ← htarget]
    simpa [Polynomial.aeval_def] using hendpointJuliaAtZero
  exact selected_complex_single_flow_analytic_terminal_certificate
    outputValue houtputValue carrier.firstGenerator hfirstMonic.ne_zero
    ⟨continuation, hterminal, hanalyticJulia⟩

/-- Aggregated local critical two-flow surface. -/
theorem analytic_critical_two_julia_exclusion_terminal_certificate :
    ∀ (carrier : TwoJuliaAbelCarrier)
      (continuation : SelectedRegularizedContinuation)
      (outputValue : ℝ) (degree ramification : ℕ),
      carrier.center = 0 →
      carrier.source = analyticLocalX →
      carrier.target = selectedAnalyticEndpoint continuation outputValue →
      continuation.right 3 ≠ 0 →
      outputValue ≠ 0 →
      carrier.firstGenerator.IsMonicOfDegree degree →
      carrier.secondGenerator.IsMonicOfDegree degree →
      carrier.firstGenerator.coeff 0 = 0 →
      carrier.secondGenerator.coeff 0 = 0 →
      carrier.firstGenerator.coeff 1 = 0 →
      carrier.secondGenerator.coeff 1 = 0 →
      2 ≤ degree →
      ramification * (degree - 1) = 2 →
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.firstInfinityTime
          (reciprocalTimeIntegrand carrier.firstGenerator degree z) z) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.secondInfinityTime
          (reciprocalTimeIntegrand carrier.secondGenerator degree z) z) →
      deriv carrier.source carrier.center = 0 →
      deriv carrier.target carrier.center = 0 →
      iteratedDeriv 3 carrier.source carrier.center = 0 →
      iteratedDeriv 3 carrier.target carrier.center = 0 →
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        (fun t ↦ selectedAnalyticDerivativeFactor continuation outputValue t *
          carrier.sourceDerivative t) →
      (∀ᶠ t in 𝓝[≠] carrier.center,
        carrier.hiddenDerivative t ≠ 0) →
      False := by
  intro carrier continuation outputValue degree ramification hcenter
    hsource htarget hterminal houtputValue hfirstMonic hsecondMonic
    hfirstConstant hsecondConstant hfirstLinear hsecondLinear hdegree
    hbalance hreciprocalOrder hfirstInfinityDerivative
    hsecondInfinityDerivative hsourceLinearJet htargetLinearJet
    hsourceCubicJet htargetCubicJet hderivativeCompatibility
    hhiddenDerivative
  exact critical_two_julia_carrier_impossible carrier continuation
    outputValue degree ramification hcenter hsource htarget hterminal
    houtputValue hfirstMonic hsecondMonic hfirstConstant hsecondConstant
    hfirstLinear hsecondLinear hdegree hbalance hreciprocalOrder
    hfirstInfinityDerivative hsecondInfinityDerivative hsourceLinearJet
    htargetLinearJet hsourceCubicJet htargetCubicJet
    hderivativeCompatibility hhiddenDerivative

/-- The hidden-derivative premise of the preceding theorem follows from the
positive reciprocal order already present in the critical carrier. -/
theorem analytic_critical_two_julia_intrinsic_exclusion_terminal_certificate :
    ∀ (carrier : TwoJuliaAbelCarrier)
      (continuation : SelectedRegularizedContinuation)
      (outputValue : ℝ) (degree ramification : ℕ),
      carrier.center = 0 →
      carrier.source = analyticLocalX →
      carrier.target = selectedAnalyticEndpoint continuation outputValue →
      continuation.right 3 ≠ 0 →
      outputValue ≠ 0 →
      carrier.firstGenerator.IsMonicOfDegree degree →
      carrier.secondGenerator.IsMonicOfDegree degree →
      carrier.firstGenerator.coeff 0 = 0 →
      carrier.secondGenerator.coeff 0 = 0 →
      carrier.firstGenerator.coeff 1 = 0 →
      carrier.secondGenerator.coeff 1 = 0 →
      2 ≤ degree →
      ramification * (degree - 1) = 2 →
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.firstInfinityTime
          (reciprocalTimeIntegrand carrier.firstGenerator degree z) z) →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt carrier.secondInfinityTime
          (reciprocalTimeIntegrand carrier.secondGenerator degree z) z) →
      deriv carrier.source carrier.center = 0 →
      deriv carrier.target carrier.center = 0 →
      iteratedDeriv 3 carrier.source carrier.center = 0 →
      iteratedDeriv 3 carrier.target carrier.center = 0 →
      carrier.targetDerivative =ᶠ[𝓝[≠] carrier.center]
        (fun t ↦ selectedAnalyticDerivativeFactor continuation outputValue t *
          carrier.sourceDerivative t) →
      False := by
  intro carrier continuation outputValue degree ramification hcenter
    hsource htarget hterminal houtputValue hfirstMonic hsecondMonic
    hfirstConstant hsecondConstant hfirstLinear hsecondLinear hdegree
    hbalance hreciprocalOrder hfirstInfinityDerivative
    hsecondInfinityDerivative hsourceLinearJet htargetLinearJet
    hsourceCubicJet htargetCubicJet hderivativeCompatibility
  have hramification : 0 < ramification := by
    apply Nat.pos_of_ne_zero
    intro hzero
    simp [hzero] at hbalance
  have hhiddenDerivative :=
    FormalAnalyticTwoJuliaDerivativeNonvanishing.TwoJuliaAbelCarrier.hiddenDerivative_eventually_ne_zero_of_reciprocal_order
      carrier ramification hramification hreciprocalOrder
  exact critical_two_julia_carrier_impossible carrier continuation
    outputValue degree ramification hcenter hsource htarget hterminal
    houtputValue hfirstMonic hsecondMonic hfirstConstant hsecondConstant
    hfirstLinear hsecondLinear hdegree hbalance hreciprocalOrder
    hfirstInfinityDerivative hsecondInfinityDerivative hsourceLinearJet
    htargetLinearJet hsourceCubicJet htargetCubicJet
    hderivativeCompatibility hhiddenDerivative

end FormalAnalyticCriticalTwoJuliaExclusion
