import Mathlib.Tactic
import ZtareProofs.ns_route1_next_killer_hinges

namespace ZtareProofs

/-!
`ns_route1_killer_theorem_search` is the theorem-search surface for the exact
next route-1 payments.

Useful local work is no longer "improve route 1 somehow." It is one of:

1. prove the one-step budget inheritance cleanly,
2. prove the strict contraction ratio,
3. or kill route 1 by exhibiting the frequency-collapse regime first.
-/

/-- Theorem target for the one-step budget inheritance. -/
def route1StepBudgetTheoremCandidate
    (transportDefect commutatorResidual nextStep : Real) : Prop :=
  route1StepBudgetHinge
    transportDefect commutatorResidual nextStep

/-- Theorem target for the strict contraction ratio. -/
def route1StrictRatioTheoremCandidate
    (transportDefect commutatorResidual currentStep nextStep ratio : Real) : Prop :=
  route1StrictRatioHinge
    transportDefect commutatorResidual currentStep nextStep ratio

/-- Theorem target for excluding the frequency-collapse escape. -/
def route1NoFrequencyCollapseTheoremCandidate
    (δ lam amplitude ε : Real) : Prop :=
  route1NoFrequencyCollapseHinge
    δ lam amplitude ε

/-- Exact theorem-search surface for route 1 after local compression. -/
def route1KillerTheoremSearchFrontier
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real) : Prop :=
  route1StepBudgetTheoremCandidate
      transportDefect commutatorResidual nextStep ∧
    route1StrictRatioTheoremCandidate
      transportDefect commutatorResidual currentStep nextStep ratio ∧
    route1NoFrequencyCollapseTheoremCandidate
      δ lam amplitude ε

theorem route1_killer_frontier_is_exact
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real}
    (h :
      route1KillerTheoremSearchFrontier
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε) :
    route1StepBudgetTheoremCandidate
        transportDefect commutatorResidual nextStep ∧
      route1StrictRatioTheoremCandidate
        transportDefect commutatorResidual currentStep nextStep ratio ∧
      route1NoFrequencyCollapseTheoremCandidate
        δ lam amplitude ε := by
  exact h

end ZtareProofs
