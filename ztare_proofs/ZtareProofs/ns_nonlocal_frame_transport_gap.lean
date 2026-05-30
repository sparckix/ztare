import Mathlib.Tactic
import ZtareProofs.ns_strain_aligned_connection_bypass

namespace ZtareProofs

/-!
`ns_nonlocal_frame_transport_gap` records the constructive route-5 burden
revealed by the first `ns_proofsearch_constructive` iter: killing the strict
strain-eigenframe is not enough. A pressure-Hessian-aligned or otherwise
non-local moving frame may still evade the local umbilic blowup penalty.

So the live route-5 hinge is no longer generic "geometry helps?" but the
sharper question:

* do non-local frame constructions inherit a comparable transport defect, or
* does route 5 remain open specifically through non-local frame transport?
-/

/-- Scalar proxy for the defect budget carried by a non-local moving frame. -/
abbrev NonlocalFrameTransportDefect := Real

/-- Scalar proxy for how much a frame construction depends on non-local data. -/
abbrev NonlocalityBudget := Real

/-- Scalar proxy for umbilic singularity exposure in a moving frame. -/
abbrev UmbilicExposure := Real

/--
Route-5 rival object: a pressure-Hessian-aligned or otherwise non-local frame
that is not strictly the local strain eigenframe.
-/
def nonlocalFrameCandidate
    (nonlocalityBudget pressureCarrier alignmentQuality : Real) : Prop :=
  0 ≤ nonlocalityBudget ∧ 0 ≤ pressureCarrier ∧ 0 ≤ alignmentQuality

/--
Native route-5 kill target: even the non-local frame pays a transport defect
that is bounded below by umbilic exposure plus a non-locality budget.
-/
def nonlocalFrameInheritsUmbilicPenalty
    (transportDefect umbilicExposure nonlocalityBudget : Real) : Prop :=
  0 ≤ umbilicExposure ∧
    0 ≤ nonlocalityBudget ∧
    umbilicExposure + nonlocalityBudget ≤ transportDefect

/--
Constructive route-5 gap revealed by iter 1: the route only closes if its
native non-local rival frames also inherit a coercive defect.
-/
def route5NonlocalFrameGapTarget
    (transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality : Real) : Prop :=
  nonlocalFrameCandidate nonlocalityBudget pressureCarrier alignmentQuality ∧
    nonlocalFrameInheritsUmbilicPenalty transportDefect umbilicExposure
      nonlocalityBudget

/--
If the non-local frame gap target is paid, then the iter-1 route-coverage gap
is closed honestly: route 5 is no longer open merely by swapping the strict
strain eigenframe for a pressure-Hessian-aligned transport gauge.
-/
theorem route5_gap_closes_only_after_nonlocal_frame_test
    {transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality : Real}
    (h :
      route5NonlocalFrameGapTarget transportDefect umbilicExposure
        nonlocalityBudget pressureCarrier alignmentQuality) :
    nonlocalFrameInheritsUmbilicPenalty transportDefect umbilicExposure
      nonlocalityBudget := by
  exact h.2

end ZtareProofs
