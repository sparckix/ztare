import Mathlib.Tactic
import ZtareProofs.ns_phase_scrambling_bridge

namespace ZtareProofs

/-!
`ns_topological_gridlock` names the refined object after Phase 5AG.

Phase 5AE falsified the visible single-jump transaction-fee thesis. Phase 5AG
partially recovered the regularity route by showing that re-entry targets can
already carry Eulerian debt. The resulting theorem object is a memory/occupancy
map, not a single-vortex or single-jump estimate.
-/

/-- Abstract orientation/eigenframe cell identifier. -/
abbrev OrientationCell := Nat

/-- Debt carried by an orientation neighborhood before the next landing. -/
abbrev FrameDebt := Real

/-- A phase-scrambled handoff/re-entry event. -/
structure RelayJump where
  entryPeak : Real
  landingPeak : Real
  source : OrientationCell
  target : OrientationCell
  jumpTime : Real
  targetDebt : FrameDebt
  hEntryNonneg : 0 ≤ entryPeak
  hLandingNonneg : 0 ≤ landingPeak
  hTimeNonneg : 0 ≤ jumpTime

/-- The jump re-enters an orientation neighborhood already used by the relay. -/
def reentryJump (J : RelayJump) : Prop :=
  J.source = J.target

/-- The target frame is dirty above a threshold. -/
def dirtyTarget (debtThreshold : Real) (J : RelayJump) : Prop :=
  debtThreshold ≤ J.targetDebt

/--
Dirty re-entry density along a finite prefix of a relay sequence.

Kept abstract as a scalar so the proof cage does not depend on a particular
finite-count implementation.
-/
abbrev DirtyReentryDensity := Real

/-- Abstract clean volume remaining in orientation/eigenframe phase space. -/
abbrev CleanOrientationVolume := Real

/-- Total available orientation phase-space volume, e.g. the finite volume of `SO(3)`. -/
abbrev OrientationVolume := Real

/-- Volume of orientation phase space polluted by unresolved relay debris. -/
abbrev PollutedOrientationVolume := Real

/-- Volume scrubbed by viscous relaxation over the elapsed interval. -/
abbrev CleanedOrientationVolume := Real

/-- Observable non-leader component-halo debt proxy from a finite strobe. -/
abbrev ComponentHaloDebt := Real

/--
Component-halo lower-bound bridge.

This is the formal slot opened by Phase 5AH: if the observed non-leader halo
debt lower-bounds orientation-space pollution, then the finite component audit
can feed the clean-volume accounting object. The PDE/geometry work is proving
this bridge, not asserting it from a finite trace.
-/
def componentHaloLowerBoundsPollution
    (Halo : ComponentHaloDebt)
    (Vpolluted : PollutedOrientationVolume) : Prop :=
  Halo ≤ Vpolluted

/--
Clean-volume accounting bound.

This is the balance-sheet version of topological gridlock: clean orientation
real estate is at most total finite orientation volume minus unresolved
pollution plus whatever viscous relaxation has actually cleaned.
-/
def cleanVolumeAccounting
    (Vclean : CleanOrientationVolume)
    (Vtotal : OrientationVolume)
    (Vpolluted : PollutedOrientationVolume)
    (Vcleaned : CleanedOrientationVolume) : Prop :=
  Vclean ≤ Vtotal - Vpolluted + Vcleaned

/--
The orientation market is oversubscribed: unresolved pollution exceeds total
orientation supply plus cleanup.
-/
def orientationCapacityExceeded
    (Vtotal : OrientationVolume)
    (Vpolluted : PollutedOrientationVolume)
    (Vcleaned : CleanedOrientationVolume) : Prop :=
  Vtotal + Vcleaned < Vpolluted

/--
If unresolved polluted orientation volume exceeds total orientation supply plus
cleanup, any accounting upper bound forces clean volume negative. Since clean
volume is physically nonnegative, this is the contradiction that kills an
indefinite clean-relay story under the supplied premises.
-/
theorem clean_volume_negative_of_capacity_exceeded
    {Vclean : CleanOrientationVolume}
    {Vtotal : OrientationVolume}
    {Vpolluted : PollutedOrientationVolume}
    {Vcleaned : CleanedOrientationVolume}
    (haccount : cleanVolumeAccounting Vclean Vtotal Vpolluted Vcleaned)
    (hexceed : orientationCapacityExceeded Vtotal Vpolluted Vcleaned) :
    Vclean < 0 := by
  unfold cleanVolumeAccounting at haccount
  unfold orientationCapacityExceeded at hexceed
  linarith

/--
Clean relay impossible under nonnegative clean volume once capacity is exceeded.
-/
theorem no_nonnegative_clean_volume_of_capacity_exceeded
    {Vclean : CleanOrientationVolume}
    {Vtotal : OrientationVolume}
    {Vpolluted : PollutedOrientationVolume}
    {Vcleaned : CleanedOrientationVolume}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount : cleanVolumeAccounting Vclean Vtotal Vpolluted Vcleaned)
    (hexceed : orientationCapacityExceeded Vtotal Vpolluted Vcleaned) :
    False := by
  have hneg : Vclean < 0 :=
    clean_volume_negative_of_capacity_exceeded haccount hexceed
  linarith

/--
Linear pollution/cleanup surrogate.

`jumpCount * pollutedPerJump` is the gross dirty real estate created by relay
jumps. `cleanupRate * elapsedTime` is the maximum scrubbed volume in the same
window. This deliberately keeps the PDE work explicit: one must prove the lower
bound per jump and the upper bound on cleanup from Navier-Stokes.
-/
noncomputable def unresolvedPollution
    (jumpCount pollutedPerJump cleanupRate elapsedTime : Real) : Real :=
  jumpCount * pollutedPerJump - cleanupRate * elapsedTime

/--
Capacity-exceedance criterion in the linear surrogate.
-/
theorem orientation_capacity_exceeded_of_unresolvedPollution
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    (h :
      Vtotal <
        unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime) :
    orientationCapacityExceeded
      Vtotal
      (jumpCount * pollutedPerJump)
      (cleanupRate * elapsedTime) := by
  unfold orientationCapacityExceeded unresolvedPollution at *
  linarith

/--
Zeno-style clean-relay contradiction in balance-sheet form.

If an accelerating relay produces more unresolved orientation pollution than
finite orientation phase space can hold, clean frame supply is exhausted before
the putative clean relay can continue.
-/
theorem clean_relay_contradiction_of_unresolved_pollution
    {Vclean Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount :
      cleanVolumeAccounting
        Vclean
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime))
    (hcapacity :
      Vtotal <
        unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime) :
    False := by
  have hexceed :
      orientationCapacityExceeded
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime) :=
    orientation_capacity_exceeded_of_unresolvedPollution hcapacity
  exact no_nonnegative_clean_volume_of_capacity_exceeded
    hVclean_nonneg haccount hexceed

/--
Component-halo route to orientation capacity exhaustion.

If measured/derived component-halo debt already exceeds finite orientation
capacity after cleanup, and if that halo lower-bounds polluted orientation
volume, then an indefinite clean relay is impossible.
-/
theorem clean_relay_contradiction_of_component_halo_debt
    {Vclean Vtotal Vpolluted Vcleaned : Real}
    {Halo : ComponentHaloDebt}
    (hVclean_nonneg : 0 ≤ Vclean)
    (hhalo_pollution : componentHaloLowerBoundsPollution Halo Vpolluted)
    (haccount : cleanVolumeAccounting Vclean Vtotal Vpolluted Vcleaned)
    (hhalo_exceeds : Vtotal + Vcleaned < Halo) :
    False := by
  unfold componentHaloLowerBoundsPollution at hhalo_pollution
  have hexceed : orientationCapacityExceeded Vtotal Vpolluted Vcleaned := by
    unfold orientationCapacityExceeded
    linarith [hhalo_pollution, hhalo_exceeds]
  exact no_nonnegative_clean_volume_of_capacity_exceeded
    hVclean_nonneg haccount hexceed

/--
Gridlock premise:
above some intensity, the relay's reused target frames carry enough residual
debt to dominate the phase-scrambled gain.
-/
def gridlockDebtBeatsRelayGain
    (Grelay : phaseScrambledGain) (DebtTax : cycleLoss) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → Grelay E < DebtTax E

/-- Reset loss includes the debt tax paid on dirty re-entry. -/
def resetLossIncludesGridlockDebt
    (L : cycleLoss) (DebtTax : cycleLoss) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → DebtTax E ≤ L E

/--
Topological gridlock route:
if reused-frame debt beats relay gain and reset loss includes that debt, the
phase-scrambled recurrence is contractive.
-/
theorem contractive_recurrence_of_topological_gridlock
    {Grelay L DebtTax : cycleGain} {EStar : Real}
    (hdebt : gridlockDebtBeatsRelayGain Grelay DebtTax EStar)
    (hinclude : resetLossIncludesGridlockDebt L DebtTax EStar) :
    contractiveAbove (recurrenceFromGainLoss Grelay L) EStar := by
  apply contractive_of_exhaustHorizon
  intro E hE
  exact lt_of_lt_of_le (hdebt hE) (hinclude hE)

/--
Clean-relay subsequence:
an unbounded sequence where loss still does not dominate relay gain.

This is the exact loophole left open by the clean `t=1.95` target in Phase 5AG.
-/
def cleanRelaySubsequence
    (Grelay L : cycleGain) (Es : Nat → Real) : Prop :=
  nonDominantSubsequence Grelay L Es

/--
If a clean relay subsequence survives, then the scalar budget does not establish
gridlock along that subsequence.
-/
theorem loss_not_dominant_on_cleanRelaySubsequence
    {Grelay L : cycleGain} {Es : Nat → Real}
    (hsub : cleanRelaySubsequence Grelay L Es)
    (hG : ∀ n : Nat, 0 < Grelay (Es n)) :
    ∀ n : Nat, L (Es n) ≤ Grelay (Es n) := by
  exact gain_not_outpaced_along_nonDominantSubsequence hsub hG

/--
The final fork after Phase 5AG:
either dirty re-entry debt eventually dominates relay gain, or an unbounded
clean-relay subsequence remains live.
-/
def topologicalGridlockFork
    (Grelay L DebtTax : cycleGain) (EStar : Real) (Es : Nat → Real) : Prop :=
  (gridlockDebtBeatsRelayGain Grelay DebtTax EStar ∧
    resetLossIncludesGridlockDebt L DebtTax EStar) ∨
  cleanRelaySubsequence Grelay L Es

theorem topological_gridlock_fork_target_shape
    {Grelay L DebtTax : cycleGain} {EStar : Real} {Es : Nat → Real}
    (h : topologicalGridlockFork Grelay L DebtTax EStar Es) :
    topologicalGridlockFork Grelay L DebtTax EStar Es := by
  exact h

end ZtareProofs
