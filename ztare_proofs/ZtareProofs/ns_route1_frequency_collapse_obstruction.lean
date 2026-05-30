import Mathlib.Tactic
import ZtareProofs.ns_route1_constructive_frontier
import ZtareProofs.ns_route1_killer_theorem_search

namespace ZtareProofs

/-!
`ns_route1_frequency_collapse_obstruction` records the cheapest visible
route-1 obstruction theorem: once the frequency-sensitive collapse regime is
actually paid, route 1 is no longer admissible as the primary constructive
branch.
-/

/-- Canonical route-1 obstruction target: the frequency-sensitive collapse
regime is genuinely active. -/
def route1FrequencyCollapseObstructionTarget
    (δ lam amplitude ε : Real) : Prop :=
  route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε

/-- If the frequency-sensitive collapse regime is active, the exact route-1
killer-theorem surface is impossible. -/
theorem route1_killer_surface_obstructed_of_frequency_collapse
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real}
    (hcollapse : route1FrequencyCollapseObstructionTarget δ lam amplitude ε) :
    ¬ route1KillerTheoremSearchFrontier
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε := by
  intro h
  exact h.2.2 hcollapse

/-- Stronger branch-level phrasing: if the collapse regime is active, the
packaged route-1 constructive frontier is no longer admissible. -/
theorem route1_constructive_frontier_obstructed_of_frequency_collapse
    {δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam : Real}
    (hcollapse : route1FrequencyCollapseObstructionTarget δ lam amplitude ε) :
    ¬ route1ConstructiveFrontierTarget
      δ penalty K tailDecay margin residualTransition
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio carrier amplitude ε lam := by
  intro h
  exact h.2.2 hcollapse

end ZtareProofs
