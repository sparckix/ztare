import Mathlib.Tactic
import ZtareProofs.ns_parity_transversality_target

namespace ZtareProofs

/-!
`ns_local_delta_sheath_pressure_target` records the Gemini cold-shot correction
to the cone-mass route.

The radial-separation story is false as stated: in a collapsing vortex, the
positive strain contribution to

  `Lambda = |S|^2 - |omega|^2 / 2`

need not live in a distant halo. It can form a same-scale sheath around the
negative vorticity core, so Fourier radial separation cannot prevent
cancellation.

The corrected target is physical-space/local:

* the negative core gives a projected pressure footprint;
* the same-scale positive sheath is annihilated by angular symmetry, or is
  bounded by a strict fraction of the core projection;
* therefore the total projected pressure footprint remains nonzero.

This file proves the algebraic implication once those local estimates are
supplied. It does not prove the estimates from Navier-Stokes.
-/

/-- Projected pressure contribution from the negative vorticity-dominated core. -/
abbrev CorePressureProjection := Real

/-- Projected pressure contribution from the positive strain-dominated sheath. -/
abbrev SheathPressureProjection := Real

/-- Total projected pressure footprint from core plus sheath. -/
noncomputable def totalLocalPressureProjection
    (core sheath : Real) : Real :=
  core + sheath

/--
The positive sheath is harmless if its projected contribution is bounded by a
strict fraction of the core contribution.
-/
def sheathProjectionControlledByCore
    (core sheath fraction : Real) : Prop :=
  |sheath| ≤ fraction * |core|

/--
If the core projection has a floor and the sheath is controlled by a fraction
strictly below one, the total local pressure projection remains bounded away
from zero.
-/
theorem local_pressure_projection_floor_of_core_dominance
    {core sheath fraction coreFloor : Real}
    (hfraction_lt : fraction < 1)
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheathProjectionControlledByCore core sheath fraction) :
    (1 - fraction) * coreFloor ≤ |totalLocalPressureProjection core sheath| := by
  unfold sheathProjectionControlledByCore at hsheath
  unfold totalLocalPressureProjection
  have htri : |core| - |sheath| ≤ |core + sheath| := by
    exact abs_sub_abs_le_abs_add core sheath
  have hfrac : |sheath| ≤ fraction * |core| := hsheath
  have hgap : (1 - fraction) * |core| ≤ |core| - |sheath| := by
    nlinarith
  have hfloor : (1 - fraction) * coreFloor ≤ (1 - fraction) * |core| := by
    have hcoef : 0 ≤ 1 - fraction := by linarith
    exact mul_le_mul_of_nonneg_left hcore hcoef
  exact le_trans hfloor (le_trans hgap htri)

/--
The exact-annihilation special case: if the sheath projection is zero, the total
projection inherits the core floor.
-/
theorem local_pressure_projection_floor_of_sheath_annihilation
    {core sheath coreFloor : Real}
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheath = 0) :
    coreFloor ≤ |totalLocalPressureProjection core sheath| := by
  unfold totalLocalPressureProjection
  rw [hsheath]
  ring_nf
  exact hcore

/--
Route the local core/sheath estimate into the pointwise parity-transversality
target.
-/
theorem parity_transversality_of_local_core_dominance
    {driver : LocalJumpDriver}
    {core sheath fraction coreFloor driverFloor : Real}
    (hfraction_lt : fraction < 1)
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheathProjectionControlledByCore core sheath fraction) :
    parityTransversalityLowerBound
      driver
      (totalLocalPressureProjection core sheath)
      driverFloor
      ((1 - fraction) * coreFloor) := by
  intro _hactive
  exact local_pressure_projection_floor_of_core_dominance
    hfraction_lt hcore hsheath

/--
Exact-annihilation route into pointwise parity transversality.
-/
theorem parity_transversality_of_sheath_annihilation
    {driver : LocalJumpDriver}
    {core sheath coreFloor driverFloor : Real}
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheath = 0) :
    parityTransversalityLowerBound
      driver
      (totalLocalPressureProjection core sheath)
      driverFloor
      coreFloor := by
  intro _hactive
  exact local_pressure_projection_floor_of_sheath_annihilation hcore hsheath

/--
Then an active stealth eigenstate is impossible under the local core/sheath
dominance estimate.
-/
theorem no_active_stealth_eigenstate_of_local_core_dominance
    {driver : LocalJumpDriver}
    {core sheath fraction coreFloor driverFloor : Real}
    (hcoreFloor_pos : 0 < coreFloor)
    (hfraction_lt : fraction < 1)
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheathProjectionControlledByCore core sheath fraction) :
    ¬ activeStealthEigenstate
      driver
      (totalLocalPressureProjection core sheath)
      driverFloor := by
  have hcoef_pos : 0 < 1 - fraction := by linarith
  have hpFloor : 0 < (1 - fraction) * coreFloor :=
    mul_pos hcoef_pos hcoreFloor_pos
  exact no_active_stealth_eigenstate_of_parity_transversality
    hpFloor
    (parity_transversality_of_local_core_dominance
      hfraction_lt hcore hsheath)

/--
If the same-scale positive sheath is exactly annihilated in the projected
principal-value channel, the active stealth eigenstate is impossible as soon as
the core projection has a positive floor.
-/
theorem no_active_stealth_eigenstate_of_sheath_annihilation
    {driver : LocalJumpDriver}
    {core sheath coreFloor driverFloor : Real}
    (hcoreFloor_pos : 0 < coreFloor)
    (hcore : coreFloor ≤ |core|)
    (hsheath : sheath = 0) :
    ¬ activeStealthEigenstate
      driver
      (totalLocalPressureProjection core sheath)
      driverFloor := by
  exact no_active_stealth_eigenstate_of_parity_transversality
    hcoreFloor_pos
    (parity_transversality_of_sheath_annihilation hcore hsheath)

end ZtareProofs
