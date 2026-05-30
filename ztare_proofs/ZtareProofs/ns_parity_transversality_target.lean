import Mathlib.Tactic
import ZtareProofs.ns_self_generated_pressure_transversality

namespace ZtareProofs

/-!
`ns_parity_transversality_target` is the "stealth eigenstate" target after the
4D/GR analogy is stripped down to a Navier-Stokes statement.

The useful content is not that one field is verbally "odd" and the other is
"even".  Parity language only points to a quantitative target:

* an active local jump driver must have nonzero projection onto its
  self-generated pressure footprint;
* otherwise the rival has a self-consistent stealth eigenstate.

This file encodes that target and the contradiction it yields. It does not prove
the tensor-geometry estimate from Navier-Stokes.
-/

/-- A pointwise projected pressure-footprint value for a candidate stealth state. -/
abbrev PointwisePressureProjection := Real

/--
Candidate self-consistent stealth eigenstate:
the local jump driver is active, but the projected pressure footprint is zero.
-/
def activeStealthEigenstate
    (driver : LocalJumpDriver)
    (Pproj : PointwisePressureProjection)
    (driverFloor : Real) : Prop :=
  driverFloor ≤ |driver| ∧ Pproj = 0

/--
Quantitative parity/transversality lower bound.

This is the actual PDE theorem target suggested by the odd/even discussion:
active jump geometries have a pressure-footprint projection bounded away from
zero. Without this quantitative bound, parity language alone proves nothing.
-/
def parityTransversalityLowerBound
    (driver : LocalJumpDriver)
    (Pproj : PointwisePressureProjection)
    (driverFloor pFloor : Real) : Prop :=
  driverFloor ≤ |driver| → pFloor ≤ |Pproj|

/--
An active stealth eigenstate is impossible under a positive quantitative
parity/transversality lower bound.
-/
theorem no_active_stealth_eigenstate_of_parity_transversality
    {driver : LocalJumpDriver}
    {Pproj : PointwisePressureProjection}
    {driverFloor pFloor : Real}
    (hpFloor : 0 < pFloor)
    (htrans :
      parityTransversalityLowerBound driver Pproj driverFloor pFloor) :
    ¬ activeStealthEigenstate driver Pproj driverFloor := by
  intro hstealth
  rcases hstealth with ⟨hactive, hzero⟩
  unfold parityTransversalityLowerBound at htrans
  have hnonzero : pFloor ≤ |Pproj| := htrans hactive
  rw [hzero] at hnonzero
  simp at hnonzero
  linarith

/--
Sequence-level parity/transversality target.

The Zeno rival may hit isolated Calderon-Zygmund nulls. The real target is that
active jump drivers cannot remain null-locked on average across the jump prefix.
-/
def parityNoNullLockLowerBound
    (driver : LocalJumpDriver)
    (Pseq : ProjectedPressureSequence)
    (N : Nat)
    (driverFloor pFloor : Real) : Prop :=
  selfGeneratedPressureTransversality driver Pseq N driverFloor pFloor

/--
Parity/no-null-lock lower bound routes into positive total pollution.
-/
theorem positive_total_pollution_of_parity_no_null_lock
    {driver : LocalJumpDriver}
    {Pseq : ProjectedPressureSequence}
    {N : Nat}
    {totalPollution κ driverFloor pFloor : Real}
    (hN : 0 < (N : Real))
    (hκ : 0 < κ)
    (hpFloor : 0 < pFloor)
    (hactive : driverFloor ≤ |driver|)
    (hparity :
      parityNoNullLockLowerBound driver Pseq N driverFloor pFloor)
    (hbridge : sequenceProjectedPressureCreatesPollution Pseq N totalPollution κ) :
    0 < totalPollution := by
  exact positive_total_pollution_of_self_generated_transversality
    hN hκ hpFloor hactive hparity hbridge

/--
Parity/no-null-lock lower bound routes into the clean-relay contradiction.
-/
theorem clean_relay_contradiction_of_parity_no_null_lock
    {driver : LocalJumpDriver}
    {Pseq : ProjectedPressureSequence}
    {N : Nat}
    {Vclean Vtotal totalPollution cleanupRate elapsedTime : Real}
    {κ driverFloor pFloor : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount :
      cleanVolumeAccounting
        Vclean
        Vtotal
        ((N : Real) * totalPollution)
        (cleanupRate * elapsedTime))
    (hN : 0 < (N : Real))
    (hκ : 0 < κ)
    (hpFloor : 0 < pFloor)
    (hactive : driverFloor ≤ |driver|)
    (hparity :
      parityNoNullLockLowerBound driver Pseq N driverFloor pFloor)
    (hbridge : sequenceProjectedPressureCreatesPollution Pseq N totalPollution κ)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / totalPollution < (N : Real)) :
    False := by
  exact clean_relay_contradiction_of_self_generated_transversality
    hVclean_nonneg haccount hN hκ hpFloor hactive hparity hbridge hcount

end ZtareProofs
