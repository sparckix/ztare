import Mathlib.Tactic
import ZtareProofs.ns_calderon_zygmund_stealth_obstruction

open scoped BigOperators

namespace ZtareProofs

/-!
`ns_ergodic_no_null_lock` replaces the false pointwise CZ lower bound with the
correct sequence-level object.

A Calderon-Zygmund pressure kernel has angular nulls, so a single handoff can
land in a blind spot. The viable theorem target is no-null-lock: an infinite or
long finite Zeno relay cannot keep every local `-Omega^2` jump axis synchronized
with the global CZ null set. Formally, this is an average lower bound on the
absolute projected pressure-rotation channel over a jump prefix.
-/

/-- Projected pressure-rotation value on the `n`-th jump. -/
abbrev ProjectedPressureSequence := Nat → ProjectedPressureRotation

/-- Sum of absolute projected pressure rotations over a finite jump prefix. -/
noncomputable def projectedPressureAbsSum
    (P : ProjectedPressureSequence) (N : Nat) : Real :=
  (Finset.range N).sum (fun n => |P n|)

/--
No-null-lock lower bound over a finite prefix.

This is the sequence-level replacement for pointwise non-nullness: the average
absolute projection is at least `pFloor`, expressed without division.
-/
def noNullLockAverageLowerBound
    (P : ProjectedPressureSequence) (N : Nat) (pFloor : Real) : Prop :=
  (N : Real) * pFloor ≤ projectedPressureAbsSum P N

/--
Sequence footprint bridge.

The total polluted orientation volume is lower-bounded by the accumulated
projected pressure-rotation footprint over the jump prefix.
-/
def sequenceProjectedPressureCreatesPollution
    (P : ProjectedPressureSequence) (N : Nat)
    (totalPollution : PollutionPerJump) (κ : Real) : Prop :=
  κ * projectedPressureAbsSum P N ≤ totalPollution

/--
No-null-lock plus a positive footprint coefficient implies positive total
pollution over the jump prefix.

This permits isolated CZ blind-spot jumps. What is forbidden is perfect
phase-locking to the null set across the whole accelerating relay.
-/
theorem positive_total_pollution_of_no_null_lock
    {P : ProjectedPressureSequence} {N : Nat}
    {totalPollution κ pFloor : Real}
    (hN : 0 < (N : Real))
    (hκ : 0 < κ)
    (hfloor : 0 < pFloor)
    (hnonlock : noNullLockAverageLowerBound P N pFloor)
    (hbridge : sequenceProjectedPressureCreatesPollution P N totalPollution κ) :
    0 < totalPollution := by
  unfold noNullLockAverageLowerBound at hnonlock
  unfold sequenceProjectedPressureCreatesPollution at hbridge
  have hprefix_pos : 0 < (N : Real) * pFloor := mul_pos hN hfloor
  have hsum_pos : 0 < projectedPressureAbsSum P N :=
    lt_of_lt_of_le hprefix_pos hnonlock
  have hprod_pos : 0 < κ * projectedPressureAbsSum P N :=
    mul_pos hκ hsum_pos
  exact lt_of_lt_of_le hprod_pos hbridge

/--
Average-footprint route into the existing Zeno threshold.

If the no-null-lock sequence creates a positive total footprint, and the jump
count exceeds capacity measured against that footprint, clean relay is
impossible.
-/
theorem clean_relay_contradiction_of_no_null_lock_sequence
    {P : ProjectedPressureSequence} {N : Nat}
    {Vclean Vtotal totalPollution cleanupRate elapsedTime : Real}
    {κ pFloor : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount :
      cleanVolumeAccounting
        Vclean
        Vtotal
        ((N : Real) * totalPollution)
        (cleanupRate * elapsedTime))
    (hN : 0 < (N : Real))
    (hκ : 0 < κ)
    (hfloor : 0 < pFloor)
    (hnonlock : noNullLockAverageLowerBound P N pFloor)
    (hbridge : sequenceProjectedPressureCreatesPollution P N totalPollution κ)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / totalPollution < (N : Real)) :
    False := by
  have hpollute : 0 < totalPollution :=
    positive_total_pollution_of_no_null_lock hN hκ hfloor hnonlock hbridge
  exact clean_relay_contradiction_of_jumpCount_threshold
    (Vclean := Vclean)
    (Vtotal := Vtotal)
    (jumpCount := (N : Real))
    (pollutedPerJump := totalPollution)
    (cleanupRate := cleanupRate)
    (elapsedTime := elapsedTime)
    hVclean_nonneg haccount hpollute hcount

end ZtareProofs
