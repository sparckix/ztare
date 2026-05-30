import Mathlib.Tactic
import ZtareProofs.ns_local_delta_sheath_pressure_target

namespace ZtareProofs

/-!
`ns_angular_moment_pressure_target` incorporates the GPT-5.5 cold shot.

The pressure projection is not controlled by radial mass, core size, halo size,
or verbal parity. It sees a signed `l = 2` angular moment of

  `Lambda = |S|^2 - |omega|^2 / 2`

against the projected Riesz kernel. Active torque alone is not enough: an
annular, strain-dominated sheath with the right angular lobe can cancel the
core projection while leaving the first jet, and therefore the local torque, at
the core unchanged.

This file records the corrected target:

* core projected angular moment has a floor;
* sheath/error angular moment is a strict fraction of the core;
* then stealth is impossible.
-/

/-- Signed `l=2` angular moment of the negative core against the projected Riesz kernel. -/
abbrev CoreAngularMoment := Real

/-- Signed `l=2` angular moment of the same-scale sheath and exterior error. -/
abbrev SheathErrorAngularMoment := Real

/-- Total signed angular moment visible to the pressure projection. -/
noncomputable def totalAngularMoment
    (coreMoment sheathErrorMoment : Real) : Real :=
  coreMoment + sheathErrorMoment

/--
Angular-moment dominance condition.

This is the smallest decisive condition identified by the GPT-5.5 cold shot.
It is not automatic from active torque; it is the PDE estimate to prove or
falsify.
-/
def angularMomentDominance
    (coreMoment sheathErrorMoment epsilon : Real) : Prop :=
  |sheathErrorMoment| ≤ (1 - epsilon) * |coreMoment|

/--
If the core angular moment has a floor and sheath/error is a strict fraction,
the total angular moment remains nonzero with an `epsilon` margin.
-/
theorem angular_moment_floor_of_dominance
    {coreMoment sheathErrorMoment epsilon coreFloor : Real}
    (heps_pos : 0 < epsilon)
    (_heps_le_one : epsilon ≤ 1)
    (hcore : coreFloor ≤ |coreMoment|)
    (hdominance : angularMomentDominance coreMoment sheathErrorMoment epsilon) :
    epsilon * coreFloor ≤ |totalAngularMoment coreMoment sheathErrorMoment| := by
  unfold angularMomentDominance at hdominance
  unfold totalAngularMoment
  have htri : |coreMoment| - |sheathErrorMoment| ≤ |coreMoment + sheathErrorMoment| := by
    exact abs_sub_abs_le_abs_add coreMoment sheathErrorMoment
  have hgap : epsilon * |coreMoment| ≤ |coreMoment| - |sheathErrorMoment| := by
    have hnonneg : 0 ≤ 1 - epsilon := by linarith
    nlinarith
  have hfloor : epsilon * coreFloor ≤ epsilon * |coreMoment| := by
    exact mul_le_mul_of_nonneg_left hcore (le_of_lt heps_pos)
  exact le_trans hfloor (le_trans hgap htri)

/--
Angular-moment dominance routes into pointwise parity transversality.
-/
theorem parity_transversality_of_angular_moment_dominance
    {driver : LocalJumpDriver}
    {coreMoment sheathErrorMoment epsilon coreFloor driverFloor : Real}
    (heps_pos : 0 < epsilon)
    (heps_le_one : epsilon ≤ 1)
    (hcore : coreFloor ≤ |coreMoment|)
    (hdominance : angularMomentDominance coreMoment sheathErrorMoment epsilon) :
    parityTransversalityLowerBound
      driver
      (totalAngularMoment coreMoment sheathErrorMoment)
      driverFloor
      (epsilon * coreFloor) := by
  intro _hactive
  exact angular_moment_floor_of_dominance heps_pos heps_le_one hcore hdominance

/--
Under angular-moment dominance and a positive core floor, an active stealth
eigenstate is impossible.
-/
theorem no_active_stealth_eigenstate_of_angular_moment_dominance
    {driver : LocalJumpDriver}
    {coreMoment sheathErrorMoment epsilon coreFloor driverFloor : Real}
    (heps_pos : 0 < epsilon)
    (heps_le_one : epsilon ≤ 1)
    (hcoreFloor_pos : 0 < coreFloor)
    (hcore : coreFloor ≤ |coreMoment|)
    (hdominance : angularMomentDominance coreMoment sheathErrorMoment epsilon) :
    ¬ activeStealthEigenstate
      driver
      (totalAngularMoment coreMoment sheathErrorMoment)
      driverFloor := by
  have hpFloor : 0 < epsilon * coreFloor := mul_pos heps_pos hcoreFloor_pos
  exact no_active_stealth_eigenstate_of_parity_transversality
    hpFloor
    (parity_transversality_of_angular_moment_dominance
      heps_pos heps_le_one hcore hdominance)

/--
Countermechanism slot:
if a sheath/error contribution exactly cancels the core angular moment, the
pressure projection can vanish despite a nonzero core moment.

This formalizes why active torque alone is insufficient: one can keep the local
driver fixed while tuning a same-scale annular contribution to the opposite
Riesz angular lobe.
-/
theorem stealth_possible_by_exact_angular_moment_cancellation
    {coreMoment sheathErrorMoment : Real}
    (hcancel : sheathErrorMoment = -coreMoment) :
    totalAngularMoment coreMoment sheathErrorMoment = 0 := by
  unfold totalAngularMoment
  linarith

/--
Exact same-scale sheath cancellation is incompatible with a positive-core
angular-dominance certificate.

This is the positive condition that defeats the No-Go mechanism: the strict
fractional sheath bound must be proved before the route receipt or angular
floor is chosen.
-/
theorem exact_sheath_cancellation_incompatible_with_positive_core_dominance
    {coreMoment sheathErrorMoment epsilon coreFloor : Real}
    (heps_pos : 0 < epsilon)
    (hcoreFloor : coreFloor ≤ |coreMoment|)
    (hcoreFloor_pos : 0 < coreFloor)
    (hcancel : sheathErrorMoment = -coreMoment)
    (hdominance : angularMomentDominance coreMoment sheathErrorMoment epsilon) :
    False := by
  unfold angularMomentDominance at hdominance
  have hsheath_abs : |sheathErrorMoment| = |coreMoment| := by
    rw [hcancel, abs_neg]
  have hcore_abs_pos : 0 < |coreMoment| := lt_of_lt_of_le hcoreFloor_pos hcoreFloor
  rw [hsheath_abs] at hdominance
  nlinarith

end ZtareProofs
