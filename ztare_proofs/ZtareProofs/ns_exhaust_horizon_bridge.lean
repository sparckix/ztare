import Mathlib.Tactic
import ZtareProofs.ns_eigenframe_poincare_section

namespace ZtareProofs

/-!
`ns_exhaust_horizon_bridge` records the bridge theorem shape after Phase 5CS.

This file is intentionally unimported by `ZtareProofs.lean` and has not been
locally built in this session. Do not count it as verified support until it is
checked under a bounded Lean resource envelope.

The mathematical target is narrow: local centrifugal transversality can become
a recurrence theorem only if it bounds danger dwell/gain and reset exhaust
dominates that bound.
-/

/-- Section-level transversality/exhaust certificate for one eigenframe cycle.

`tubeWidth` is the section width, `escapeSpeed` is the lower bound on outward
transverse speed, `productionRate` is an upper bound on positive production in
the danger tube, and `resetLoss` is the cycle's exhaust loss. -/
def exhaustHorizonBridgeCertificate
    (tubeWidth escapeSpeed productionRate dangerGain resetLoss : Real) : Prop :=
  0 ≤ tubeWidth ∧
    0 < escapeSpeed ∧
    0 ≤ productionRate ∧
    0 ≤ dangerGain ∧
    0 ≤ resetLoss ∧
    dangerGain * escapeSpeed ≤ productionRate * tubeWidth ∧
    productionRate * tubeWidth ≤ resetLoss * escapeSpeed

/-- Exhaust-efficiency condition in Phase 5CW notation.

`resetLoss * escapeSpeed >= productionRate * tubeWidth` is exactly
`Q = L*v/(P*w) >= 1` without dividing by possibly inconvenient factors. -/
def exhaustEfficiencyNonnegative
    (tubeWidth escapeSpeed productionRate resetLoss : Real) : Prop :=
  productionRate * tubeWidth ≤ resetLoss * escapeSpeed

/-- Gain dwell bound in non-divided form. -/
def gainBoundedByDwellCap
    (tubeWidth escapeSpeed productionRate dangerGain : Real) : Prop :=
  dangerGain * escapeSpeed ≤ productionRate * tubeWidth

/-- The efficiency split is equivalent to the bridge certificate once the
nonnegativity side conditions are supplied. -/
theorem exhaust_bridge_certificate_of_efficiency_split
    {tubeWidth escapeSpeed productionRate dangerGain resetLoss : Real}
    (hwidth : 0 ≤ tubeWidth)
    (hspeed : 0 < escapeSpeed)
    (hprod : 0 ≤ productionRate)
    (hdanger : 0 ≤ dangerGain)
    (hloss : 0 ≤ resetLoss)
    (hgain : gainBoundedByDwellCap tubeWidth escapeSpeed productionRate dangerGain)
    (heff : exhaustEfficiencyNonnegative tubeWidth escapeSpeed productionRate resetLoss) :
    exhaustHorizonBridgeCertificate
      tubeWidth escapeSpeed productionRate dangerGain resetLoss := by
  exact ⟨hwidth, hspeed, hprod, hdanger, hloss, hgain, heff⟩

/-- Phase 5CW bridge in one line: if gain is bounded by the dwell cap and
exhaust efficiency is nonnegative, loss dominates danger gain. -/
theorem danger_gain_le_reset_loss_of_exhaust_efficiency
    {tubeWidth escapeSpeed productionRate dangerGain resetLoss : Real}
    (hwidth : 0 ≤ tubeWidth)
    (hspeed : 0 < escapeSpeed)
    (hprod : 0 ≤ productionRate)
    (hdanger : 0 ≤ dangerGain)
    (hloss : 0 ≤ resetLoss)
    (hgain : gainBoundedByDwellCap tubeWidth escapeSpeed productionRate dangerGain)
    (heff : exhaustEfficiencyNonnegative tubeWidth escapeSpeed productionRate resetLoss) :
    dangerGain ≤ resetLoss := by
  unfold gainBoundedByDwellCap at hgain
  unfold exhaustEfficiencyNonnegative at heff
  nlinarith [hgain, heff, hspeed]

/-- The bridge certificate forces loss dominance on the cycle. -/
theorem danger_gain_le_reset_loss_of_exhaust_horizon_bridge
    {tubeWidth escapeSpeed productionRate dangerGain resetLoss : Real}
    (h :
      exhaustHorizonBridgeCertificate
        tubeWidth escapeSpeed productionRate dangerGain resetLoss) :
    dangerGain ≤ resetLoss := by
  rcases h with
    ⟨_hwidth, hspeed, _hprod, _hdanger, _hloss, hgain, hexhaust⟩
  nlinarith [hgain, hexhaust, hspeed]

/-- Connecting the bridge certificate to the existing eigenframe cycle map:
if the certificate applies to the cycle's gain and loss, cycle profit is
nonpositive. -/
theorem nonpositive_cycle_profit_of_exhaust_horizon_bridge
    {C : EigenframeCycleWitness}
    {tubeWidth escapeSpeed productionRate E : Real}
    (h :
      exhaustHorizonBridgeCertificate
        tubeWidth escapeSpeed productionRate C.dangerGain C.resetLoss) :
    cycleProfit (eigenframeCycleMap C) E ≤ 0 := by
  have hdom :
      C.dangerGain ≤ C.resetLoss :=
    danger_gain_le_reset_loss_of_exhaust_horizon_bridge h
  rw [eigenframe_cycle_profit_identity]
  unfold eigenframeCycleProfit
  linarith

/-- Profitable recurrence is exactly the obstruction to the exhaust bridge on a
cycle witness. -/
def profitableEigenframeReturn (C : EigenframeCycleWitness) : Prop :=
  C.resetLoss < C.dangerGain

/-- A profitable return cannot satisfy the exhaust-horizon bridge certificate. -/
theorem no_exhaust_bridge_of_profitable_return
    {C : EigenframeCycleWitness}
    {tubeWidth escapeSpeed productionRate : Real}
    (hprof : profitableEigenframeReturn C) :
    ¬ exhaustHorizonBridgeCertificate
        tubeWidth escapeSpeed productionRate C.dangerGain C.resetLoss := by
  intro hbridge
  have hdom :
      C.dangerGain ≤ C.resetLoss :=
    danger_gain_le_reset_loss_of_exhaust_horizon_bridge hbridge
  unfold profitableEigenframeReturn at hprof
  linarith

/-- Cycle margin in the Phase 5CU notation: reset/exhaust loss minus danger
gain.  The theorem hinge is the eventual sign of this quantity. -/
def eigenframeCycleMargin (C : EigenframeCycleWitness) : Real :=
  C.resetLoss - C.dangerGain

/-- Nonnegative cycle margin is the same as nonpositive cycle profit. -/
theorem nonpositive_profit_of_nonnegative_cycle_margin
    {C : EigenframeCycleWitness} {E : Real}
    (hmargin : 0 ≤ eigenframeCycleMargin C) :
    cycleProfit (eigenframeCycleMap C) E ≤ 0 := by
  rw [eigenframe_cycle_profit_identity]
  unfold eigenframeCycleProfit eigenframeCycleMargin at *
  linarith

/-- A ladder reaches arbitrarily high entry intensity. -/
def unboundedEntryPeak (C : Nat → EigenframeCycleWitness) : Prop :=
  ∀ B : Real, ∃ n : Nat, B ≤ (C n).entry.peak

/-- Eventual exhaust horizon on a ladder: above `EStar`, every return has
loss-dominant budget. -/
def exhaustHorizonOnLadder
    (C : Nat → EigenframeCycleWitness) (EStar : Real) : Prop :=
  ∀ n : Nat, EStar ≤ (C n).entry.peak → (C n).dangerGain ≤ (C n).resetLoss

/-- Uniformly profitable ladder with a positive margin schedule.  This names
the blowup-side recurrence obligation before any return-time summability
condition is added. -/
def profitableReturnLadder
    (C : Nat → EigenframeCycleWitness) (eta : Nat → Real) : Prop :=
  ∀ n : Nat, 0 < eta n ∧ (C n).resetLoss + eta n ≤ (C n).dangerGain

/-- Exhaust horizon on an unbounded ladder rules out a uniformly profitable
return ladder.  This is the abstract bridge obstruction; Navier-Stokes still
has to supply the exhaust horizon premise. -/
theorem no_profitable_ladder_under_exhaust_horizon
    {C : Nat → EigenframeCycleWitness} {eta : Nat → Real}
    (hexhaust : ∃ EStar : Real, exhaustHorizonOnLadder C EStar)
    (hunbounded : unboundedEntryPeak C) :
    ¬ profitableReturnLadder C eta := by
  intro hprof
  rcases hexhaust with ⟨EStar, hEStar⟩
  rcases hunbounded EStar with ⟨n, hn⟩
  have hdom : (C n).dangerGain ≤ (C n).resetLoss := hEStar n hn
  have hpos : 0 < eta n := (hprof n).1
  have hprofit : (C n).resetLoss + eta n ≤ (C n).dangerGain := (hprof n).2
  linarith

end ZtareProofs
