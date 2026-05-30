import Mathlib.Data.Real.Basic

/-!
# Stealth-growth tradeoff cage

Phase 5BJ changed the NS proof target.

The strongest surviving statement is not:

* pressure stealth is empty;
* first-order transversality always ejects the flow;
* viscosity automatically destroys tangency.

The data now supports a different theorem shape:

* a pressure-stealth tube may exist and may persist for a finite window;
* the relevant question is whether it can also carry positive global enstrophy
  growth;
* if the signed enstrophy budget is non-positive during the stealth dwell,
  the state is camouflage, not a blowup engine.

This file records the scalar proof spine. The PDE obligation is to prove the
budget inequality from Navier-Stokes structure, not to expand a full Taylor jet.
-/

namespace ZtareProofs.NS

/-- Abstract state of a trajectory segment inside a pressure-stealth tube. -/
structure StealthGrowthState where
  pressureResidual : ℝ
  residualDotNorm : ℝ
  torque : ℝ
  enstrophyInitial : ℝ
  enstrophyFinal : ℝ
  signedProduction : ℝ
  viscousDissipation : ℝ
  dwellTime : ℝ

/-- The trajectory segment is inside the operational pressure-stealth tube. -/
def inPressureStealthTube (s : StealthGrowthState) (eps derivBound torqueFloor : ℝ) : Prop :=
  |s.pressureResidual| < eps ∧ s.residualDotNorm < derivBound ∧ torqueFloor < s.torque

/-- The signed global enstrophy budget is production minus viscous dissipation. -/
def netEnstrophyBudget (s : StealthGrowthState) : ℝ :=
  s.signedProduction - s.viscousDissipation

/-- The stealth state is growth-sterile: its global enstrophy budget is non-positive. -/
def stealthGrowthSterile (s : StealthGrowthState) : Prop :=
  netEnstrophyBudget s ≤ 0

/-- A segment is growth-bearing if total enstrophy increases over the dwell. -/
def growthBearingSegment (s : StealthGrowthState) : Prop :=
  s.enstrophyInitial < s.enstrophyFinal

/--
Budget consistency: if the integrated net enstrophy budget is non-positive over
the segment, final enstrophy cannot exceed initial enstrophy.

This is the scalar identity that a PDE proof must instantiate with the
Navier-Stokes enstrophy balance.
-/
def enstrophyBudgetConsistent (s : StealthGrowthState) : Prop :=
  netEnstrophyBudget s ≤ 0 → s.enstrophyFinal ≤ s.enstrophyInitial

/--
Stealth plus a non-positive global enstrophy budget cannot be a growth-bearing
singularity segment.
-/
theorem not_growth_bearing_of_stealth_sterile
    (s : StealthGrowthState)
    (hbudget : enstrophyBudgetConsistent s)
    (hsterile : stealthGrowthSterile s) :
    ¬ growthBearingSegment s := by
  intro hgrow
  exact not_lt_of_ge (hbudget hsterile) hgrow

/--
The corrected post-5BJ closure target.

If every pressure-stealth tube segment satisfying active torque is
growth-sterile, then no such segment can be the growth-bearing part of a blowup
cascade. The pressure-stealth camouflage may exist; it just cannot fund growth.
-/
theorem no_blowup_engine_inside_sterile_stealth_tube
    (s : StealthGrowthState)
    (eps derivBound torqueFloor : ℝ)
    (_htube : inPressureStealthTube s eps derivBound torqueFloor)
    (hbudget : enstrophyBudgetConsistent s)
    (hsterile : stealthGrowthSterile s) :
    ¬ growthBearingSegment s := by
  exact not_growth_bearing_of_stealth_sterile s hbudget hsterile

/--
Positive local-production pockets are not sufficient for growth if the signed
global budget is non-positive. This names the 5BJ lesson: local profitable
pockets can coexist with a globally draining enstrophy budget.
-/
theorem local_pockets_do_not_override_signed_budget
    (s : StealthGrowthState)
    (positiveLocalPockets : ℝ)
    (_hlocal : 0 < positiveLocalPockets)
    (hbudget : enstrophyBudgetConsistent s)
    (hsterile : stealthGrowthSterile s) :
    ¬ growthBearingSegment s := by
  exact not_growth_bearing_of_stealth_sterile s hbudget hsterile

end ZtareProofs.NS
