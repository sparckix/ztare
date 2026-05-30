import Mathlib.Tactic
import ZtareProofs.ns_route1_constructive_frontier
import ZtareProofs.ns_route5_postrun_survivor_surface
import ZtareProofs.ns_route_reranking_frontier

namespace ZtareProofs

/-!
`ns_millennium_frontier` is the top-level packaged object for the current local
Navier-Stokes truth-seeking frontier.

It does not claim a proof. It states the current graph explicitly:

1. route 1 has a packaged constructive frontier,
2. route 5 has a packaged post-run survivor surface,
3. a separate reranking object decides when route 5 may outrank route 1.

This keeps future local work from fragmenting into loose subfiles without a
single declared top-level target.
-/

/--
Top-level frontier target: both route packages are stated and the reranking
criterion is available on the same graph.
-/
def nsMillenniumFrontierTarget
    (δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route1ConstructiveFrontierTarget
      δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam ∧
    route5PostrunSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget ∧
    route5LegitimatePrecedenceTarget
      δ lam amplitude ε
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget

/--
Projection theorem: the top-level frontier contains the packaged route-1
constructive frontier.
-/
theorem ns_frontier_contains_route1
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      nsMillenniumFrontierTarget
        δ penalty K tailDecay margin residualTransition
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio carrier amplitude ε lam
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget) :
    route1ConstructiveFrontierTarget
      δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam := by
  exact h.1

/--
Projection theorem: the top-level frontier contains the packaged route-5
post-run survivor surface.
-/
theorem ns_frontier_contains_route5_postrun_surface
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      nsMillenniumFrontierTarget
        δ penalty K tailDecay margin residualTransition
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio carrier amplitude ε lam
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget) :
    route5PostrunSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h.2.1

/--
Projection theorem: the top-level frontier really contains the reranking rule,
not just the two branches in isolation.
-/
theorem ns_frontier_contains_reranking_rule
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      nsMillenniumFrontierTarget
        δ penalty K tailDecay margin residualTransition
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio carrier amplitude ε lam
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget) :
    route5LegitimatePrecedenceTarget
      δ lam amplitude ε
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
      horizon hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h.2.2

end ZtareProofs
