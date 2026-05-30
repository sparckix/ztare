import Mathlib.Tactic
import ZtareProofs.ns_frequency_sensitive_commutator_collapse
import ZtareProofs.ns_route5_postrun_survivor_surface

namespace ZtareProofs

/-!
`ns_route_reranking_frontier` packages the live route-ranking rule between the
flat commutator ladder (`route 1`) and the post-run geometric survivor surface
(`route 5`).

This turns the current prose criterion into one theorem-shaped object:

* route 1 must genuinely lose coercive priority on the active regime, and
* route 5 must have paid one of its exact post-run survivor burdens,

before route 5 is allowed to outrank route 1.
-/

/--
Route-5 precedence is only legitimate after a frequency-sensitive collapse of
the isotropic commutator route and payment of the exact post-run route-5
survivor surface.
-/
def route5LegitimatePrecedenceTarget
    (δ lam amplitude ε : Real)
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε ∧
    route5PostrunSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget

/--
If the packaged precedence target is paid, route 5 has outranked route 1 on a
real proof object rather than by rhetoric alone.
-/
theorem route5_precedence_requires_both_sides
    {δ lam amplitude ε : Real}
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      route5LegitimatePrecedenceTarget
        δ lam amplitude ε
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget) :
    route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε ∧
      route5PostrunSurvivorSurface
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
