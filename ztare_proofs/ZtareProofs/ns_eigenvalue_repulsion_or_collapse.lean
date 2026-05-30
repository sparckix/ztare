import Mathlib.Tactic
import ZtareProofs.ns_nonlocal_frame_transport_gap

namespace ZtareProofs

/-!
`ns_eigenvalue_repulsion_or_collapse` promotes the winning constructive iter-1
route-5 falsifier into the proof cages.

The sharpened hinge is:

* either Navier-Stokes dynamics supply a real eigenvalue-gap repulsion near
  repeated strain eigenvalues, or
* the strain-aligned / covariant moving-frame route collapses because the
  connection defect scales like `∥∇S∥ / δλ`.

This is stronger than the earlier generic "route 5 might fail" story because it
names the single remaining escape hatch precisely: dynamical repulsion away from
degenerate strain loci.
-/

/-- Minimal strain eigenvalue separation along the dangerous set. -/
abbrev EigenvalueGap := Real

/-- Local size of the strain gradient feeding the connection coefficient. -/
abbrev StrainGradientBudget := Real

/-- Covariant connection defect in the moving eigenframe. -/
abbrev EigenframeConnectionDefect := Real

/--
Native route-5 collapse model from the constructive iter:
the moving-frame defect is bounded below by strain-gradient budget divided by
the eigenvalue gap.
-/
def eigenframeDegeneracyDefect
    (connectionDefect strainGradient gap : Real) : Prop :=
  0 ≤ strainGradient ∧ 0 < gap ∧ strainGradient / gap ≤ connectionDefect

/--
Potential route-5 escape hatch: the dynamics keep the eigenvalue gap uniformly
away from zero on the dangerous set.
-/
def dynamicalEigenvalueRepulsion
    (gap floor : Real) : Prop :=
  0 < floor ∧ floor ≤ gap

/--
Exact route-5 hinge after the constructive iter:
either the dynamics provide eigenvalue repulsion, or the degeneracy defect is
strong enough to collapse unconditional route-5 coercivity.
-/
def route5EigenvalueRepulsionOrCollapse
    (connectionDefect strainGradient gap floor : Real) : Prop :=
  dynamicalEigenvalueRepulsion gap floor ∨
    eigenframeDegeneracyDefect connectionDefect strainGradient gap

/--
If there is no positive repulsion floor and the degeneracy defect bound is
paid, then the route-5 branch remains open only by proving repulsion. Without
that, collapse is the active reading.
-/
theorem route5_collapse_without_repulsion
    {connectionDefect strainGradient gap floor : Real}
    (hgap : ¬ dynamicalEigenvalueRepulsion gap floor)
    (hdefect : eigenframeDegeneracyDefect connectionDefect strainGradient gap) :
    route5EigenvalueRepulsionOrCollapse connectionDefect strainGradient gap floor := by
  exact Or.inr hdefect

/--
Conversely, a proved repulsion floor is the exact theorem-shaped object that
would keep the route-5 branch alive after the iter-1 falsifier.
-/
theorem route5_survives_if_repulsion_paid
    {connectionDefect strainGradient gap floor : Real}
    (hrepel : dynamicalEigenvalueRepulsion gap floor) :
    route5EigenvalueRepulsionOrCollapse connectionDefect strainGradient gap floor := by
  exact Or.inl hrepel

end ZtareProofs
