import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_contraction_bridge
import ZtareProofs.ns_frequency_sensitive_commutator_collapse

namespace ZtareProofs

/-!
`ns_route1_next_killer_hinges` puts route 1 on the same theorem granularity as
the post-run route-5 branch.

The route-1 branch is no longer one opaque "transport defect" object. Its next
exact hostile-referee payments are:

1. pay the one-step residual budget,
2. extract a strict contraction ratio,
3. show the microstructure/frequency-collapse escape does not win first.
-/

/-- Exact one-step budget inheritance from the pressure-side transport defect. -/
def route1StepBudgetHinge
    (transportDefect commutatorResidual nextStep : Real) : Prop :=
  transportResidualFeedsTowerStep
    transportDefect commutatorResidual nextStep

/-- Exact strict-ratio hinge for the tower step. -/
def route1StrictRatioHinge
    (transportDefect commutatorResidual currentStep nextStep ratio : Real) : Prop :=
  towerContractionFromTransportDefect
    transportDefect commutatorResidual currentStep nextStep ratio

/-- Exact hostile microstructure hinge: route 1 only survives as primary if the
frequency-collapse regime is not already active. -/
def route1NoFrequencyCollapseHinge
    (δ lam amplitude ε : Real) : Prop :=
  ¬ route5PrecedenceAfterFrequencyCollapse δ lam amplitude ε

/-- Exact next killer-hinge surface for route 1. -/
def route1NextKillerHinges
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real) : Prop :=
  route1StepBudgetHinge transportDefect commutatorResidual nextStep ∧
    route1StrictRatioHinge
      transportDefect commutatorResidual currentStep nextStep ratio ∧
    route1NoFrequencyCollapseHinge δ lam amplitude ε

theorem route1_next_killer_surface_projects
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real}
    (h :
      route1NextKillerHinges
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε) :
    route1StepBudgetHinge transportDefect commutatorResidual nextStep ∧
      route1StrictRatioHinge
        transportDefect commutatorResidual currentStep nextStep ratio ∧
      route1NoFrequencyCollapseHinge δ lam amplitude ε := by
  exact h

end ZtareProofs
