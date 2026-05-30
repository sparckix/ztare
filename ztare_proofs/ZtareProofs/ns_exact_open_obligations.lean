import Mathlib.Tactic
import ZtareProofs.ns_millennium_frontier
import ZtareProofs.ns_route1_killer_theorem_search
import ZtareProofs.ns_route5_next_killer_hinges
import ZtareProofs.ns_route5_postrun_survivor_surface

namespace ZtareProofs

/-!
`ns_exact_open_obligations` is the local "what is still unpaid?" file.

The branch packages and reranking packages now exist. This file names the
current exact obligations that are still theorem-shaped but unproved.

It is intentionally plain: no new mechanism, no new route, only the open
payments.
-/

/-- Exact route-1 theorem-search surface after local compression. -/
def route1OpenObligation
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real) : Prop :=
  route1KillerTheoremSearchFrontier
    transportDefect commutatorResidual currentStep nextStep ratio
    δ lam amplitude ε

/--
Strict-margin route-1 open obligation after v17.13/v17.14.

This is the current scalar-payment surface: route 1 remains conditional on
producing the budget margin certificate, not merely naming subcriticality.
-/
def route1StrictMarginOpenObligation
    (δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio budgetMargin carrier amplitude ε lam : Real) : Prop :=
  route1StrictMarginConstructiveFrontierTarget
    δ penalty K tailDecay margin residualTransition
    stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
    transportDefect localQuadratic advectedPressure commutatorResidual
    budget currentStep nextStep ratio budgetMargin carrier amplitude ε lam

/-- Exact periodic / pulsed metric-reset survivor burden. -/
def route5PeriodicResetOpenObligation
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual : Real) :
    Prop :=
  periodicMetricResetSurvivorTarget
    γ t kappaMax totalStrain logResetCost resetCount globalResidual

/-- Exact micro-local global-leak survivor burden. -/
def route5MicrolocalLeakOpenObligation
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon : Real) : Prop :=
  microlocalDiffusiveAbsorptionSurvivorTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    rawPenalty diffusiveScale smoothingOrder dilutedPenalty
    globalResidual decayBudget horizon

/-- Exact exponential-metric curvature-capacity survivor burden. -/
def route5ExponentialMetricOpenObligation
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricSurvivorTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    hnorm targetCurvature realizedCapacity capacityBudget

/-- Exact post-run route-5 survivor surface after the finished theorem-search run. -/
def route5PostrunSurfaceOpenObligation
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route5PostrunSurvivorSurface
    γ t kappaMax totalStrain logResetCost resetCount globalResidual
    coerciveBudget pressureBurden residual offset lambdaMin
    rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
    hnorm targetCurvature realizedCapacity capacityBudget

/-- The post-run route-5 surface is exactly the three survivor burdens. -/
theorem route5_postrun_surface_projects_to_exact_branches
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      route5PostrunSurfaceOpenObligation
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget) :
    route5PeriodicResetOpenObligation
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
      route5MicrolocalLeakOpenObligation
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon ∨
      route5ExponentialMetricOpenObligation
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

/-- Exact next hostile-referee payment after the post-run route-5 surface. -/
def route5NextKillerOpenObligation
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget : Real) : Prop :=
  route5NextKillerHinges
    γ t kappaMax totalStrain logResetCost resetCount globalResidual
    coerciveBudget pressureBurden residual offset lambdaMin
    rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
    hnorm targetCurvature realizedCapacity capacityBudget
    jumpAlignment resetResidual debtBudget
    localGain tailLeak globalBudget
    finiteIntervalCapacity infiniteTimeFloor driftBudget

/-- Once the post-run route-5 surface is admitted, the next admissible local
work is one of the three exact killer hinges rather than a new vague family. -/
theorem route5_next_work_must_hit_killer_hinge
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget : Real}
    (h :
      route5NextKillerOpenObligation
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget) :
    (route5PeriodicResetOpenObligation
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∧
      periodicResetOrthogonalityHinge jumpAlignment resetResidual debtBudget) ∨
    (route5MicrolocalLeakOpenObligation
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon ∧
      microlocalLeakIntegrabilityHinge localGain tailLeak globalBudget) ∨
    (route5ExponentialMetricOpenObligation
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget ∧
      exponentialCapacityDriftHinge
        finiteIntervalCapacity infiniteTimeFloor driftBudget) := by
  exact h

/--
Exact meta-obligation: decide the ranking only after both branch objects are
stated on the same frontier.
-/
def routeRankingOpenObligation
    (δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  nsMillenniumFrontierTarget
    δ penalty K tailDecay margin residualTransition
    stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
    transportDefect localQuadratic advectedPressure commutatorResidual
    budget currentStep nextStep ratio carrier amplitude ε lam
    γ t kappaMax totalStrain logResetCost resetCount globalResidual
    coerciveBudget pressureBurden residual offset lambdaMin
    rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
    hnorm targetCurvature realizedCapacity capacityBudget

end ZtareProofs
