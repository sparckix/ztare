import Mathlib.Tactic
import ZtareProofs.ns_route5_topological_offset_mismatch

namespace ZtareProofs

/-!
`ns_route5_global_offset_sufficiency` promotes the informative content of the
first nontrivial offset-family escape attempt.

After the analytic offset families are killed, the remaining live route-5
rescue is a singular / topological curvature-return mechanism. Iter 3 says that
this is not enough locally: the route only survives if the total global offset
capacity of the singular set is large enough to pay the distributed analytic
debt.
-/

/-- Global measure of the singular set supporting the offset mechanism. -/
abbrev DegeneracySupportMass := Real

/-- Total analytic defect budget that the singular set would need to absorb. -/
abbrev AnalyticResidualDebt := Real

/--
Global sufficiency target for singular / topological route-5 offsets.
The total supported offset capacity must dominate the global analytic debt.
-/
def globalOffsetCapacitySufficiencyTarget
    (supportMass localReturnDensity totalOffsetCapacity analyticDebt : Real) : Prop :=
  0 ≤ supportMass ∧
    0 ≤ localReturnDensity ∧
    totalOffsetCapacity = supportMass * localReturnDensity ∧
    0 ≤ analyticDebt ∧
    analyticDebt ≤ totalOffsetCapacity

/--
Curvature-return can only count as a true route-5 family if it pays both the
local route-5 offset burden and this global sufficiency target.
-/
def curvatureReturnGlobalClosureTarget
    (γ curvatureBudget returnLoss offset
      supportMass localReturnDensity totalOffsetCapacity analyticDebt : Real) : Prop :=
  curvatureReturnOffsetFamilyTarget γ curvatureBudget returnLoss offset ∧
    globalOffsetCapacitySufficiencyTarget
      supportMass localReturnDensity totalOffsetCapacity analyticDebt

/--
Without a global sufficiency bound, local singular return does not close route
5 even if the pointwise offset story looks favorable.
-/
theorem no_curvature_return_closure_without_global_sufficiency
    {γ curvatureBudget returnLoss offset
      supportMass localReturnDensity totalOffsetCapacity analyticDebt : Real}
    (hno :
      ¬ globalOffsetCapacitySufficiencyTarget
        supportMass localReturnDensity totalOffsetCapacity analyticDebt) :
    ¬ curvatureReturnGlobalClosureTarget
      γ curvatureBudget returnLoss offset
      supportMass localReturnDensity totalOffsetCapacity analyticDebt := by
  intro h
  exact hno h.2

/--
If a singular route-5 offset is proposed after the analytic family mismatch,
the next exact hostile-referee question is global sufficiency, not local
holonomy alone.
-/
def route5SingularOffsetNextDiscriminator
    (charge capacity γ curvatureBudget returnLoss offset
      supportMass localReturnDensity totalOffsetCapacity analyticDebt : Real) : Prop :=
  topologicalChargeEllipticMismatch charge capacity ∧
    curvatureReturnGlobalClosureTarget
      γ curvatureBudget returnLoss offset
      supportMass localReturnDensity totalOffsetCapacity analyticDebt

end ZtareProofs
