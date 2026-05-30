import Mathlib.Tactic
import ZtareProofs.ns_topological_gridlock

namespace ZtareProofs

/-!
`ns_zeno_gridlock_threshold` is the queuing-theory compression of the
topological-gridlock route.

The Zeno rival requires unboundedly many clean orientation handoffs in a finite
time window. This file proves the algebraic part of why that is incompatible
with finite orientation capacity once two PDE obligations are supplied:

1. every large handoff pollutes at least `pollutedPerJump > 0` orientation
   volume;
2. cleanup over the finite window is bounded by `cleanupRate * elapsedTime`.

It does not prove either PDE obligation. It proves that once they are available,
the clean-relay story has a finite jump-count threshold.
-/

/--
Jump-count threshold for capacity exhaustion.

If the number of relay jumps exceeds the finite capacity plus cleaned volume,
measured in units of pollution-per-jump, then unresolved pollution exceeds the
orientation capacity.
-/
theorem unresolved_pollution_exceeds_capacity_of_jumpCount_gt
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    (hpollute : 0 < pollutedPerJump)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / pollutedPerJump < jumpCount) :
    Vtotal <
      unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime := by
  unfold unresolvedPollution
  have hmul :
      Vtotal + cleanupRate * elapsedTime < jumpCount * pollutedPerJump := by
    calc
      Vtotal + cleanupRate * elapsedTime
          = ((Vtotal + cleanupRate * elapsedTime) / pollutedPerJump) *
              pollutedPerJump := by field_simp [hpollute.ne']
      _ < jumpCount * pollutedPerJump := by
        exact mul_lt_mul_of_pos_right hcount hpollute
  linarith

/--
Capacity-exceedance version of the same threshold.
-/
theorem orientation_capacity_exceeded_of_jumpCount_gt
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    (hpollute : 0 < pollutedPerJump)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / pollutedPerJump < jumpCount) :
    orientationCapacityExceeded
      Vtotal
      (jumpCount * pollutedPerJump)
      (cleanupRate * elapsedTime) := by
  exact orientation_capacity_exceeded_of_unresolvedPollution
    (unresolved_pollution_exceeds_capacity_of_jumpCount_gt hpollute hcount)

/--
Finite-capacity contradiction from a jump-count threshold.

This is the clean "infinite clean relays in finite time" pincer in finite form:
once the handoff count crosses the threshold, nonnegative clean orientation
volume contradicts the clean-volume accounting.
-/
theorem clean_relay_contradiction_of_jumpCount_threshold
    {Vclean Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount :
      cleanVolumeAccounting
        Vclean
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime))
    (hpollute : 0 < pollutedPerJump)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / pollutedPerJump < jumpCount) :
    False := by
  have hcapacity :
      Vtotal <
        unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime :=
    unresolved_pollution_exceeds_capacity_of_jumpCount_gt hpollute hcount
  exact clean_relay_contradiction_of_unresolved_pollution
    hVclean_nonneg haccount hcapacity

end ZtareProofs
