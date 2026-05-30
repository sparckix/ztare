import Mathlib.Tactic
import ZtareProofs.ns_discrete_recurrence_map

namespace ZtareProofs

/-!
`ns_eigenframe_poincare_section` attaches the current NS recurrence story to a
concrete type of return object.

The xhigh cold-shot tightened the bottleneck: the unresolved theorem burden is
not local escape, but the sign of `L(E) - G(E)` on full danger-reset-return
cycles.  This file names those cycles using an eigenframe section rather than
free-floating narrative.
-/

/--
Abstract eigenframe observables at a section hit.

These are the scalars the current branch has actually converged onto:
peak intensity, signed escape coordinate, local production, eigengap, and a
pressure-response proxy.
-/
structure EigenframeState where
  peak : Real
  escape : Real
  chi : Real
  eigengap : Real
  pressureResponse : Real
  hPeakNonneg : 0 ≤ peak

/--
Entry/exit thresholds for a Poincare-style section in the eigenframe variables.

`epsIn` marks danger entry (`escape <= epsIn`) and `epsOut` marks certified
reset exit (`epsOut <= escape`).
-/
structure EigenframeSection where
  epsIn : Real
  epsOut : Real
  hsep : epsIn < epsOut

/--
An abstract eigenframe cycle witness.

This packages the return-map object more honestly than the old branch language:
one enters the danger tube, exits the tube, and later returns to the section.
-/
structure EigenframeCycleWitness where
  entry : EigenframeState
  exit : EigenframeState
  ret : EigenframeState
  dangerGain : Real
  resetLoss : Real
  dwellDanger : Real
  dwellReset : Real
  hDangerNonneg : 0 ≤ dangerGain
  hResetNonneg : 0 ≤ resetLoss
  hDangerTimeNonneg : 0 ≤ dwellDanger
  hResetTimeNonneg : 0 ≤ dwellReset

/--
Cycle map induced by an eigenframe cycle witness.
-/
def eigenframeCycleMap (C : EigenframeCycleWitness) : CycleMap :=
  fun E => E + C.dangerGain - C.resetLoss

/--
The recurrence budget attached to an eigenframe cycle witness.
-/
def eigenframeCycleProfit (C : EigenframeCycleWitness) : Real :=
  C.dangerGain - C.resetLoss

/--
The total cycle time of the witness.
-/
def eigenframeCycleTime (C : EigenframeCycleWitness) : Real :=
  C.dwellDanger + C.dwellReset

/--
The witness-induced cycle map has profit exactly equal to danger gain minus
reset loss.
-/
theorem eigenframe_cycle_profit_identity
    {C : EigenframeCycleWitness} {E : Real} :
    cycleProfit (eigenframeCycleMap C) E = eigenframeCycleProfit C := by
  unfold cycleProfit eigenframeCycleMap eigenframeCycleProfit
  ring

/--
If reset loss exceeds danger gain on a witness, then the induced cycle map is
strictly contractive at that witness scale.
-/
theorem contractive_at_witness_of_loss_dominance
    {C : EigenframeCycleWitness} {E : Real}
    (hloss : C.dangerGain < C.resetLoss) :
    cycleProfit (eigenframeCycleMap C) E < 0 := by
  rw [eigenframe_cycle_profit_identity]
  unfold eigenframeCycleProfit
  linarith

/--
If danger gain exceeds reset loss on a witness, then the induced cycle map is
strictly profitable at that witness scale.
-/
theorem profitable_at_witness_of_gain_dominance
    {C : EigenframeCycleWitness} {E : Real}
    (hgain : C.resetLoss < C.dangerGain) :
    0 < cycleProfit (eigenframeCycleMap C) E := by
  rw [eigenframe_cycle_profit_identity]
  unfold eigenframeCycleProfit
  linarith

/--
Target shape: to close the NS branch, one must show that for sufficiently large
peak intensity, every eigenframe return witness has loss-dominant budget.
-/
def eventualLossDominanceOnSection
    (_S : EigenframeSection) (P : EigenframeState → Prop) : Prop :=
  ∀ C : EigenframeCycleWitness, P C.entry → C.dangerGain ≤ C.resetLoss

/--
This is the exact section-level theorem cage now left by the NS branch.
-/
theorem eigenframe_section_target_shape
    {S : EigenframeSection} {P : EigenframeState → Prop}
    (h : eventualLossDominanceOnSection S P) :
    eventualLossDominanceOnSection S P := by
  exact h

end ZtareProofs
