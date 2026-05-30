import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_proofsearch

namespace ZtareProofs

/-!
`ns_commutator_tower_stepwise_targets` refines route `1` into the next exact
scalar obligations.

The earlier file `ns_commutator_tower_proofsearch` keeps the branch broad on
purpose. This file does the opposite: it compresses the primary route into the
smallest theorem-shaped steps that would actually pay the commutator branch.

Those steps are:

1. a one-step singular-integral kernel bound,
2. extraction of a subcritical tower ratio from radial grade,
3. promotion of that ratio into summability,
4. reduction of the transport residual to the summable tower budget.
-/

/-- One-step Calderon / Coifman-Meyer style kernel estimate. -/
def commutatorKernelStepBound
    (towerStep carrier radialGrade kernelGain multiplierGain : Real) : Prop :=
  0 ≤ kernelGain ∧
    0 ≤ multiplierGain ∧
    towerStep ≤ (kernelGain + multiplierGain) * |carrier| / max radialGrade 1

/--
The older proof-search step obligation and the newer stepwise kernel atom have
the same scalar content. This theorem is a naming adapter, not a proof of the
commutator estimate.
-/
theorem commutatorKernelStepBound_of_singularIntegralCommutatorStep
    {towerStep carrier radialGrade kernelGain multiplierGain : Real}
    (h :
      singularIntegralCommutatorStep
        towerStep radialGrade carrier kernelGain multiplierGain) :
    commutatorKernelStepBound
      towerStep carrier radialGrade kernelGain multiplierGain := by
  exact h

/--
Project the pointwise kernel-step atom from the broader proof-search target.
The analytic estimate is still whatever proves the broader target.
-/
theorem commutatorKernelStepBound_of_commutatorTowerProofSearchTarget
    {tower : Nat → Real} {carrier radialGrade ratio : Real}
    {kernelGain multiplierGain : Nat → Real}
    (h :
      commutatorTowerProofSearchTarget
        tower radialGrade carrier ratio kernelGain multiplierGain)
    (n : Nat) :
    commutatorKernelStepBound
      (tower n) carrier radialGrade (kernelGain n) (multiplierGain n) := by
  exact h.1 n

/--
Radial grade pays the tower only if it forces a strictly subcritical ratio.

This isolates the real scalar hinge: the route does not need a magical closed
form, it needs a ratio extraction with room below one.
-/
def radialGradeExtractsTowerRatio
    (radialGrade kernelGain multiplierGain ratio : Real) : Prop :=
  0 ≤ kernelGain ∧
    0 ≤ multiplierGain ∧
    0 ≤ ratio ∧
    ratio < 1 ∧
    kernelGain + multiplierGain ≤ ratio * max radialGrade 1

/--
Stepwise route-1 package: every level pays the same kind of kernel estimate
and radial grade extracts one globally subcritical ratio.
-/
def commutatorTowerStepwiseTarget
    (tower : Nat → Real) (carrier radialGrade ratio : Real)
    (kernelGain multiplierGain : Nat → Real) : Prop :=
  (∀ n : Nat,
      commutatorKernelStepBound
        (tower n) carrier radialGrade (kernelGain n) (multiplierGain n)) ∧
    (∀ n : Nat,
      radialGradeExtractsTowerRatio
        radialGrade (kernelGain n) (multiplierGain n) ratio)

/--
If the route can actually extract a strict contraction at each step, then the
tower is geometrically summable. The contraction itself is still a separate
obligation; this theorem does not fake it.
-/
theorem geometric_candidate_of_stepwise_ratio_and_contraction
    {tower : Nat → Real} {ratio : Real}
    (hratio : 0 ≤ ratio ∧ ratio < 1)
    (hcontract : ∀ n : Nat, tower (n + 1) ≤ ratio * tower n) :
    commutatorTowerGeometricCandidate tower ratio := by
  refine ⟨hratio.1, hratio.2, ?_⟩
  intro n
  exact hcontract n

/--
What route `1` really needs from the stepwise package:
promotion into the broad proof-search target already used by the packet.
-/
theorem proofsearch_target_of_commutatorTowerStepwiseTarget
    {tower : Nat → Real} {carrier radialGrade ratio : Real}
    {kernelGain multiplierGain : Nat → Real}
    (hstep :
      commutatorTowerStepwiseTarget
        tower carrier radialGrade ratio kernelGain multiplierGain)
    (hcontract : ∀ n : Nat, tower (n + 1) ≤ ratio * tower n) :
    commutatorTowerProofSearchTarget tower radialGrade carrier ratio
      kernelGain multiplierGain := by
  refine ⟨?_, ?_⟩
  · intro n
    rcases hstep.1 n with ⟨hk, hm, hbound⟩
    exact ⟨hk, hm, hbound⟩
  · exact geometric_candidate_of_stepwise_ratio_and_contraction
      ⟨(hstep.2 0).2.2.1, (hstep.2 0).2.2.2.1⟩ hcontract

/--
Paying the stepwise commutator package is enough to choose the commutator
branch in the broad Phase 5CG proof-search target.

This is a conditional branch-payment bridge, not a proof that the stepwise
kernel estimates or contraction hold.
-/
theorem phase5cgBroadProofSearchTarget_of_commutatorTowerStepwiseTarget
    {tower : Nat → Real} {carrier radialGrade ratio : Real}
    {kernelGain multiplierGain : Nat → Real}
    {globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon : Real}
    (hstep :
      commutatorTowerStepwiseTarget
        tower carrier radialGrade ratio kernelGain multiplierGain)
    (hcontract : ∀ n : Nat, tower (n + 1) ≤ ratio * tower n) :
    phase5cgBroadProofSearchTarget tower radialGrade carrier ratio
      kernelGain multiplierGain
      globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon := by
  exact Or.inl
    (proofsearch_target_of_commutatorTowerStepwiseTarget hstep hcontract)

end ZtareProofs
