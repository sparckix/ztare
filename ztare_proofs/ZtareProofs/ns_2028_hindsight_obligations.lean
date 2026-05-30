import Mathlib.Tactic
import ZtareProofs.ns_l2_carrier_transport

namespace ZtareProofs

/-!
`ns_2028_hindsight_obligations` records the "already visible today" missed
objects that would have to be paid if the pressure-`l = 2` route eventually
closed.

These are not new mechanism guesses. They are the natural unpaid objects
already exposed by the current theorem cages, backtests, and replay summaries:

1. the pressure-side object is still local / principal-part facing and needs a
   nonlocal tail bootstrap;
2. the Calderon residual is recorded once, but a successful closure would need
   iterated commutator control rather than a one-shot estimate;
3. the recurrence spine is cycle-local and still needs a uniform continuation
   handoff;
4. the branch still lacks a clean regime split between small-data closure and
   driver-floor activation.

This file names those obligations without pretending they are already theorems.
-/

/-- Nonlocal pressure-tail discrepancy relative to the local pressure carrier. -/
abbrev GlobalPressureTail := Real

/-- Iterated commutator magnitude at level `n`. -/
abbrev CommutatorTowerTerm := Nat → Real

/-- Maximal-interval continuation lifetime lower bound. -/
abbrev UniformContinuationScale := Real

/-- Threshold separating small-data closure from driver-floor activation. -/
abbrev SmallLargeSplitThreshold := Real

/--
The local `l = 2` pressure carrier must eventually be bootstrapped against the
genuinely nonlocal pressure tail on driver-floor support.
-/
def globalPressureTailBootstrap
    (globalTail radialGrade energyBudget K ε : Real) : Prop :=
  0 < ε ∧ globalTail ≤ K * radialPowerWeight radialGrade ε * energyBudget

/--
The first Calderon residual is unlikely to be the whole story; a true closure
would need the entire iterated commutator tower to remain summably suppressed.
-/
def commutatorTowerSummable
    (tower : Nat → Real) (radialGrade carrier : Real) (K : Nat → Real) (δ : Nat → Real) : Prop :=
  ∀ n : Nat, 0 < δ n ∧ tower n ≤ K n * radialPowerWeight radialGrade (δ n) * |carrier|

/--
The cycle-local recurrence / exhaust control must feed a continuation bound
that does not degenerate with initial intensity.
-/
def uniformContinuationObligation
    (lifetime reciprocalScale c : Real) : Prop :=
  0 < c ∧ lifetime ≥ c * reciprocalScale

/--
The branch likely needs an explicit regime split: either standard small-data
closure applies, or the driver-floor mechanism activates within a controlled
time horizon.
-/
def smallLargeSplitObligation
    (initialIntensity threshold activationHorizon : Real) : Prop :=
  0 < threshold ∧
    ((initialIntensity ≤ threshold) ∨ (initialIntensity > threshold ∧ 0 ≤ activationHorizon))

/--
Bundle of hindsight obligations that are already visible from the current
spine. If this branch ever closes, some version of these objects is likely to
have been paid explicitly rather than left implicit.
-/
def ns2028HindsightBundle
    (globalTail radialGrade energyBudget Ktail ε
      lifetime reciprocalScale c
      initialIntensity threshold activationHorizon carrier : Real)
    (tower : Nat → Real) (Ktower : Nat → Real) (δtower : Nat → Real) : Prop :=
  globalPressureTailBootstrap globalTail radialGrade energyBudget Ktail ε ∧
    commutatorTowerSummable tower radialGrade carrier Ktower δtower ∧
    uniformContinuationObligation lifetime reciprocalScale c ∧
    smallLargeSplitObligation initialIntensity threshold activationHorizon

/--
The current pressure-`l = 2` transport-defect route is still local unless it
is eventually extended by the hindsight bundle above.
-/
theorem local_transport_route_still_needs_hindsight_bundle
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      globalTail energyBudget Ktail ε
      lifetime reciprocalScale c initialIntensity threshold activationHorizon
      carrier : Real}
    {tower : Nat → Real} {Ktower : Nat → Real} {δtower : Nat → Real}
    (htransport :
      pressureL2TransportDefectObligation stretch pressureL2 vorticitySq radialGrade Λ0 C0
        decayProfile transportDefect localQuadratic advectedPressure commutatorResidual)
    (hhindsight :
      ns2028HindsightBundle globalTail radialGrade energyBudget Ktail ε
        lifetime reciprocalScale c initialIntensity threshold activationHorizon
        carrier tower Ktower δtower) :
    l2CarrierTransportInequality
        transportDefect
        (C0 * localQuadratic)
        (C0 * advectedPressure)
        commutatorResidual ∧
      ns2028HindsightBundle globalTail radialGrade energyBudget Ktail ε
        lifetime reciprocalScale c initialIntensity threshold activationHorizon
        carrier tower Ktower δtower := by
  rcases transport_defect_control_of_pressureL2TransportObligation htransport with ⟨hineq, _⟩
  exact ⟨hineq, hhindsight⟩

end ZtareProofs
