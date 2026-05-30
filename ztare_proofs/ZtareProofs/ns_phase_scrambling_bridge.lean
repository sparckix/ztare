import Mathlib.Tactic
import ZtareProofs.ns_marginal_tax_rate
import ZtareProofs.ns_time_rate_pincer

namespace ZtareProofs

/-!
`ns_phase_scrambling_bridge` formalizes the Munger inversion exposed by
Phase 5AD.

The previous route treated frame tumbling as an anti-blowup mechanism because
it disrupts profitable alignment. Phase 5AD forces the inverse possibility:
the same tumbling may preserve peak intensity by phase-scrambling the
vorticity/strain relation before a stationary viscous sheet can form.

So the theorem object is no longer "orientation escape occurs". It is the fork:

* if rapid frame tumbling necessarily creates a compensating Eulerian shear tax,
  the exhaust route survives;
* if phase-scrambled returns keep `L / G <= 1` along unbounded intensity, the
  fractal rival remains live at the scalar-budget level.
-/

/--
Abstract phase-scrambled gain.

`Gscramble E` is the realized danger-cycle gain when the state does not stay in
the perfectly aligned frame, but also does not immediately burn its intensity.
-/
abbrev phaseScrambledGain := cycleGain

/--
Abstract tumbling shear tax.

`Tau E` is the dissipation lower bound generated specifically by rapid
vorticity-strain frame tumbling. Proving a positive, eventually dominant `Tau`
from Navier-Stokes structure is the new bridge.
-/
abbrev tumblingShearTax := cycleLoss

/--
Phase scrambling retains a fixed fraction of the aligned gain envelope.

This is the tax-evasion side of the inversion: if `retention` is not small,
orientation noise is not merely a brake.
-/
def phaseScrambleGainRetention
    (G0 Gscramble : cycleGain) (retention EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → retention * G0 E ≤ Gscramble E

/--
Tumbling-induced shear tax lower-bounds reset loss.
-/
def resetLossLowerBoundedByTumblingTax
    (L : cycleLoss) (Tau : tumblingShearTax) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Tau E ≤ L E

/--
The decisive regularity-side margin after Phase 5AD:
the shear tax created by phase scrambling itself beats the phase-scrambled gain.
-/
def tumblingTaxBeatsPhaseScrambledGain
    (Gscramble : phaseScrambledGain) (Tau : tumblingShearTax) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Gscramble E < Tau E

/--
Phase-scrambling bridge:
if tumbling creates a shear tax that beats the scrambled gain, and reset loss
includes that tax, then the recurrence map is contractive.
-/
theorem contractive_recurrence_of_tumbling_shear_tax
    {Gscramble L : cycleGain} {Tau : tumblingShearTax} {EStar : Real}
    (hbeat : tumblingTaxBeatsPhaseScrambledGain Gscramble Tau EStar)
    (hloss : resetLossLowerBoundedByTumblingTax L Tau EStar) :
    contractiveAbove (recurrenceFromGainLoss Gscramble L) EStar := by
  apply contractive_of_exhaustHorizon
  intro E hE
  exact lt_of_lt_of_le (hbeat hE) (hloss hE)

/--
Equivalent marginal-tax form of the same bridge.
-/
theorem tax_dominance_of_tumbling_shear_tax
    {Gscramble L : cycleGain} {Tau : tumblingShearTax} {EStar : Real}
    (hGpos : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < Gscramble E)
    (hbeat : tumblingTaxBeatsPhaseScrambledGain Gscramble Tau EStar)
    (hloss : resetLossLowerBoundedByTumblingTax L Tau EStar) :
    eventualTaxDominance Gscramble L EStar := by
  intro E hE
  unfold marginalTaxRate
  have hGL : Gscramble E < L E := lt_of_lt_of_le (hbeat hE) (hloss hE)
  exact (one_lt_div (hGpos hE)).2 hGL

/--
Direct loss-dominance statement from the tumbling bridge.
-/
theorem loss_gt_gain_of_tumbling_shear_tax
    {Gscramble L : cycleGain} {Tau : tumblingShearTax} {EStar E : Real}
    (hE : EStar ≤ E)
    (hbeat : tumblingTaxBeatsPhaseScrambledGain Gscramble Tau EStar)
    (hloss : resetLossLowerBoundedByTumblingTax L Tau EStar) :
    Gscramble E < L E := by
  exact lt_of_lt_of_le (hbeat hE) (hloss hE)

/--
Tax-evasion witness:
an unbounded sequence where reset loss never outpaces phase-scrambled gain.

This is not a blowup proof. It is the exact scalar condition under which the
fractal rival remains live after the phase-scrambling inversion.
-/
def phaseScrambleTaxEvasionSubsequence
    (Gscramble L : cycleGain) (Es : Nat → Real) : Prop :=
  nonDominantSubsequence Gscramble L Es

/--
If phase-scrambled tax evasion survives, loss does not dominate gain along the
unbounded sequence.
-/
theorem loss_not_dominant_on_phase_scramble_tax_evasion
    {Gscramble L : cycleGain} {Es : Nat → Real}
    (hsub : phaseScrambleTaxEvasionSubsequence Gscramble L Es)
    (hG : ∀ n : Nat, 0 < Gscramble (Es n)) :
    ∀ n : Nat, L (Es n) ≤ Gscramble (Es n) := by
  exact gain_not_outpaced_along_nonDominantSubsequence hsub hG

/--
The sharpened Phase 5AD fork.

This is the "hidden in plain sight" object: phase noise is either a tax source
or a tax-evasion channel. The next PDE work must decide which side Navier-
Stokes enforces.
-/
def phaseScramblingFork
    (Gscramble L : cycleGain) (Tau : tumblingShearTax) (EStar : Real)
    (Es : Nat → Real) : Prop :=
  (tumblingTaxBeatsPhaseScrambledGain Gscramble Tau EStar ∧
    resetLossLowerBoundedByTumblingTax L Tau EStar) ∨
  phaseScrambleTaxEvasionSubsequence Gscramble L Es

/--
Target-shape theorem for the phase-scrambling fork.
-/
theorem phase_scrambling_fork_target_shape
    {Gscramble L : cycleGain} {Tau : tumblingShearTax} {EStar : Real}
    {Es : Nat → Real}
    (h : phaseScramblingFork Gscramble L Tau EStar Es) :
    phaseScramblingFork Gscramble L Tau EStar Es := by
  exact h

end ZtareProofs
