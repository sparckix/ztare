import Mathlib.Tactic
import ZtareProofs.ns_pressure_pollution_bridge

namespace ZtareProofs

/-!
`ns_landfill_dilemma` handles the strongest red-team response to topological
gridlock.

The rival may concede that each jump creates pressure-Hessian pollution, but
claim that all pollution can be aimed into an already-dirty orientation
neighborhood: a "landfill" strategy. Then clean volume need not shrink every
cycle; instead pollution density grows in one place.

The inversion is that a landfill is still finite-capacity. If it has finite
orientation volume and finite admissible debt density, unbounded jumps in a
finite window overflow it. The rival must therefore choose:

* spread pollution across `SO(3)` and exhaust clean real estate; or
* concentrate pollution in a landfill and exceed local debt capacity.

This file proves only that accounting dilemma. The PDE obligations are the
finite density-capacity bound and the pressure-Hessian footprint bound.
-/

/-- Volume of a deliberately reused dirty orientation neighborhood. -/
abbrev LandfillVolume := Real

/-- Maximum unresolved debt density the landfill can absorb without paying tax. -/
abbrev LandfillDebtDensityCap := Real

/--
Landfill absorption predicate.

The landfill strategy is viable only if total injected pollution can be held in
the chosen dirty orientation volume, plus whatever cleanup occurred.
-/
def landfillCanAbsorb
    (jumpCount pollutedPerJump : Real)
    (Vlandfill : LandfillVolume)
    (densityCap : LandfillDebtDensityCap)
    (cleaned : CleanedOrientationVolume) : Prop :=
  jumpCount * pollutedPerJump ≤ densityCap * Vlandfill + cleaned

/--
If jump count exceeds finite landfill capacity measured in pollution units, the
landfill strategy overflows.
-/
theorem not_landfillCanAbsorb_of_jumpCount_gt
    {jumpCount pollutedPerJump Vlandfill densityCap cleaned : Real}
    (hpollute : 0 < pollutedPerJump)
    (hcount :
      (densityCap * Vlandfill + cleaned) / pollutedPerJump < jumpCount) :
    ¬ landfillCanAbsorb jumpCount pollutedPerJump Vlandfill densityCap cleaned := by
  intro habsorb
  unfold landfillCanAbsorb at habsorb
  have hoverflow :
      densityCap * Vlandfill + cleaned < jumpCount * pollutedPerJump := by
    calc
      densityCap * Vlandfill + cleaned
          = ((densityCap * Vlandfill + cleaned) / pollutedPerJump) *
              pollutedPerJump := by field_simp [hpollute.ne']
      _ < jumpCount * pollutedPerJump := by
        exact mul_lt_mul_of_pos_right hcount hpollute
  linarith

/--
Pressure-Hessian version of landfill overflow.

If pressure response gives a positive per-jump footprint, then sufficiently many
reused-frame jumps cannot be hidden in a finite dirty quadrant.
-/
theorem not_landfillCanAbsorb_of_pressure_hessian_footprint
    {jumpCount pollutedPerJump Vlandfill densityCap cleaned : Real}
    {P : PressureHessianResponse} {κ : Real}
    (hκ : 0 < κ)
    (hP : 0 < P)
    (hbridge : pressureHessianCreatesPollution P pollutedPerJump κ)
    (hcount :
      (densityCap * Vlandfill + cleaned) / pollutedPerJump < jumpCount) :
    ¬ landfillCanAbsorb jumpCount pollutedPerJump Vlandfill densityCap cleaned := by
  have hpollute : 0 < pollutedPerJump :=
    positive_pollution_per_jump_of_pressure_hessian hκ hP hbridge
  exact not_landfillCanAbsorb_of_jumpCount_gt hpollute hcount

/--
The no-free-landfill dilemma in disjunctive form.

For a finite jump prefix, either unresolved pollution exceeds clean orientation
capacity, or, if the rival tries to aim it into a landfill, that landfill
overflows its density capacity.
-/
theorem no_free_landfill_dilemma
    {Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {Vlandfill densityCap cleaned : Real}
    (hpollute : 0 < pollutedPerJump)
    (hcleanCapacity :
      Vtotal <
        unresolvedPollution jumpCount pollutedPerJump cleanupRate elapsedTime ∨
      (densityCap * Vlandfill + cleaned) / pollutedPerJump < jumpCount) :
    orientationCapacityExceeded
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime) ∨
      ¬ landfillCanAbsorb jumpCount pollutedPerJump Vlandfill densityCap cleaned := by
  rcases hcleanCapacity with hspread | hlandfill
  · exact Or.inl (orientation_capacity_exceeded_of_unresolvedPollution hspread)
  · exact Or.inr (not_landfillCanAbsorb_of_jumpCount_gt hpollute hlandfill)

end ZtareProofs
