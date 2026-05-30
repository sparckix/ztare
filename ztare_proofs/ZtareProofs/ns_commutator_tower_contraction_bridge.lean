import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_stepwise_targets
import ZtareProofs.ns_l2_carrier_transport

namespace ZtareProofs

/-!
`ns_commutator_tower_contraction_bridge` isolates the exact next route-1 hinge
after the stepwise tower split.

The missing move is no longer "prove the whole commutator tower". It is:

1. connect the current transport defect to a one-step tower budget;
2. extract a strict contraction ratio from that budget;
3. feed that contraction into the stepwise tower target.

This file does not prove the contraction. It names it in PDE-facing symbols so
the next search step has a precise target.
-/

/-- One-step residual budget inherited from the live transport defect. -/
def transportResidualFeedsTowerStep
    (transportDefect commutatorResidual towerStep : Real) : Prop :=
  0 ≤ transportDefect ∧
    0 ≤ commutatorResidual ∧
    towerStep ≤ transportDefect + commutatorResidual

/--
The exact unpaid route-1 hinge: the defect-fed tower step must contract by a
strict ratio below one.
-/
def towerContractionFromTransportDefect
    (transportDefect commutatorResidual currentStep nextStep ratio : Real) : Prop :=
  transportResidualFeedsTowerStep transportDefect commutatorResidual nextStep ∧
    0 ≤ ratio ∧ ratio < 1 ∧
    nextStep ≤ ratio * currentStep

/--
PDE-facing route-1 bridge target.

Interpretation:
- the live pressure-side transport defect pays a one-step residual budget,
- that budget induces strict contraction,
- therefore the commutator tower branch can re-enter the stepwise target.
-/
def commutatorTowerContractionBridgeTarget
    (tower : Nat → Real) (carrier radialGrade ratio : Real)
    (kernelGain multiplierGain : Nat → Real)
    (transportDefect commutatorResidual : Nat → Real) : Prop :=
  commutatorTowerStepwiseTarget tower carrier radialGrade ratio
      kernelGain multiplierGain ∧
    (∀ n : Nat,
      towerContractionFromTransportDefect
        (transportDefect n) (commutatorResidual n) (tower n) (tower (n + 1)) ratio)

/--
If the contraction bridge is paid, route `1` is promoted back into the
stepwise proof-search target in exact repo-native form.
-/
theorem proofsearch_target_of_commutatorTowerContractionBridgeTarget
    {tower : Nat → Real} {carrier radialGrade ratio : Real}
    {kernelGain multiplierGain : Nat → Real}
    {transportDefect commutatorResidual : Nat → Real}
    (h :
      commutatorTowerContractionBridgeTarget
        tower carrier radialGrade ratio
        kernelGain multiplierGain
        transportDefect commutatorResidual) :
    commutatorTowerProofSearchTarget tower radialGrade carrier ratio
      kernelGain multiplierGain := by
  rcases h with ⟨hstep, hcontract⟩
  refine proofsearch_target_of_commutatorTowerStepwiseTarget hstep ?_
  intro n
  exact (hcontract n).2.2.2

/--
The PDE-facing contraction bridge pays the commutator branch of the broad
Phase 5CG proof-search target.

This is still conditional: the contraction bridge is the unpaid analytic
object. The theorem only wires that object into the broad branch interface.
-/
theorem phase5cgBroadProofSearchTarget_of_commutatorTowerContractionBridgeTarget
    {tower : Nat → Real} {carrier radialGrade ratio : Real}
    {kernelGain multiplierGain : Nat → Real}
    {transportDefect commutatorResidual : Nat → Real}
    {globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon : Real}
    (h :
      commutatorTowerContractionBridgeTarget
        tower carrier radialGrade ratio
        kernelGain multiplierGain
        transportDefect commutatorResidual) :
    phase5cgBroadProofSearchTarget tower radialGrade carrier ratio
      kernelGain multiplierGain
      globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon := by
  exact Or.inl
    (proofsearch_target_of_commutatorTowerContractionBridgeTarget h)

/--
Minimal tie-back to the current live transport file: if a one-step
`pressureL2TransportDefectObligation` is controlled and its residual is fed
into a strict contraction, then route `1` has the precise bridge object it
needs next.
-/
def route1PDEFacingNextTarget
    (stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      currentStep nextStep ratio : Real) : Prop :=
  pressureL2TransportDefectObligation
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    towerContractionFromTransportDefect
      transportDefect commutatorResidual currentStep nextStep ratio

end ZtareProofs
