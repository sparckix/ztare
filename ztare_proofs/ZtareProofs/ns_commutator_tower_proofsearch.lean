import Mathlib.Tactic
import ZtareProofs.ns_2028_hindsight_obligations

namespace ZtareProofs

/-!
`ns_commutator_tower_proofsearch` isolates the broad proof-search frontier
opened after the Phase 5CG pressure-`l = 2` compression.

The point is not to assume the iterated commutator tower is the only route.
The point is to name the ranked proof-search obligations in one place so the
apparatus can search over them without collapsing back into generic prose.

Primary route:
- iterated Calderon commutator tower under active radial grade

Competing / successor routes:
- global pressure-tail bootstrap
- continuation handoff
- small/large regime split

This file contains theorem-shaped targets only. It does not claim any of them
are proved.
-/

/-- Fractional Leibniz / Kato-Ponce style gain attached to one commutation step. -/
abbrev FractionalLeibnizGain := Real

/-- Coifman-Meyer multiplier control on the angular commutator return. -/
abbrev CoifmanMeyerMultiplierBound := Real

/-- Summable ratio candidate for the iterated commutator tower. -/
abbrev CommutatorTowerRatio := Real

/--
One step of the commutator tower is controlled by a singular-integral
commutator estimate, not merely by generic Sobolev embedding.
-/
def singularIntegralCommutatorStep
    (towerStep radialGrade carrier katoPonceGain multiplierBound : Real) : Prop :=
  0 ≤ katoPonceGain ∧
    0 ≤ multiplierBound ∧
    towerStep ≤ (katoPonceGain + multiplierBound) * |carrier| / max radialGrade 1

/--
The iterated tower is summable if each level contracts by a ratio strictly
below one after radial-grade renormalization.
-/
def commutatorTowerGeometricCandidate
    (tower : Nat → Real) (ratio : Real) : Prop :=
  0 ≤ ratio ∧ ratio < 1 ∧ ∀ n : Nat, tower (n + 1) ≤ ratio * tower n

/--
Primary proof-search target: derive a summable commutator tower from
singular-integral commutator structure plus active radial grade.
-/
def commutatorTowerProofSearchTarget
    (tower : Nat → Real) (radialGrade carrier ratio : Real)
    (katoPonceGain multiplierBound : Nat → Real) : Prop :=
  (∀ n : Nat,
      singularIntegralCommutatorStep
        (tower n) radialGrade carrier (katoPonceGain n) (multiplierBound n)) ∧
    commutatorTowerGeometricCandidate tower ratio

/--
Broad packet target: any one of the live obligations may be the cheapest real
promotion step, so the proof-search packet should stay open to all of them.
-/
def phase5cgBroadProofSearchTarget
    (tower : Nat → Real) (radialGrade carrier ratio : Real)
    (katoPonceGain multiplierBound : Nat → Real)
    (globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon : Real) : Prop :=
  commutatorTowerProofSearchTarget tower radialGrade carrier ratio
    katoPonceGain multiplierBound ∨
  globalPressureTailBootstrap globalTail radialGrade energyBudget Ktail ε ∨
  uniformContinuationObligation lifetime reciprocalScale c ∨
  smallLargeSplitObligation initialIntensity threshold activationHorizon

/--
If the broad proof-search target is solved along any branch, then the current
local transport-defect route has been meaningfully promoted beyond its present
local-only status.
-/
theorem local_route_promoted_of_phase5cgBroadProofSearchTarget
    {tower : Nat → Real} {radialGrade carrier ratio : Real}
    {katoPonceGain multiplierBound : Nat → Real}
    {globalTail energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon : Real}
    (h :
      phase5cgBroadProofSearchTarget tower radialGrade carrier ratio
        katoPonceGain multiplierBound
        globalTail energyBudget Ktail ε
        lifetime reciprocalScale c
        initialIntensity threshold activationHorizon) :
    commutatorTowerProofSearchTarget tower radialGrade carrier ratio
        katoPonceGain multiplierBound ∨
      globalPressureTailBootstrap globalTail radialGrade energyBudget Ktail ε ∨
      uniformContinuationObligation lifetime reciprocalScale c ∨
      smallLargeSplitObligation initialIntensity threshold activationHorizon := by
  exact h

end ZtareProofs
