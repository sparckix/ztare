import Mathlib.Tactic
import ZtareProofs.ns_route5_secondary_offset_bridge
import ZtareProofs.ns_tensor_metric_pressure_absorption

namespace ZtareProofs

/-!
`ns_route5_offset_candidate_families` names the concrete family classes worth
searching on the current geometric fork.

The question is no longer whether route 5 needs an offset. That is already
packaged. The next search object is: what kind of offset could still be on the
current proof graph?

This file keeps the candidate space narrow and honest:

1. pressure-tail style offset,
2. tensor-metric / pressure-absorption style offset,
3. curvature-return offset on the moving-frame side.
-/

/-- A pressure-tail style offset directly neutralizes the positive residual. -/
def pressureTailOffsetFamilyTarget (γ tailOffset : Real) : Prop :=
  secondaryCoerciveOffset γ tailOffset

/--
A tensor-metric candidate counts only if it stays on the current graph: it must
absorb the pressure-Hessian burden and still supply a true residual offset.
-/
def tensorAbsorptionOffsetFamilyTarget
    (γ coerciveBudget pressureBurden residual offset : Real) : Prop :=
  tensorMetricRoute5ClosureTarget coerciveBudget pressureBurden residual offset ∧
    secondaryCoerciveOffset γ offset

/--
A curvature-return candidate offsets the positive residual only if the return
loss is covered by a coercive curvature budget and the remaining scalar offset
is still large enough to close `γ`.
-/
def curvatureReturnOffsetFamilyTarget
    (γ curvatureBudget returnLoss offset : Real) : Prop :=
  0 ≤ curvatureBudget ∧
    0 ≤ returnLoss ∧
    returnLoss ≤ curvatureBudget + offset ∧
    secondaryCoerciveOffset γ offset

/--
The exact local search space for the next route-5 theorem object.
-/
def route5OffsetCandidateFamilyTarget
    (γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
      returnLoss offset : Real) : Prop :=
  pressureTailOffsetFamilyTarget γ tailOffset ∨
    tensorAbsorptionOffsetFamilyTarget
      γ coerciveBudget pressureBurden residual offset ∨
    curvatureReturnOffsetFamilyTarget γ curvatureBudget returnLoss offset

/--
Every honest candidate family still has to cash out as a real secondary offset.
-/
theorem route5_offset_family_implies_real_offset
    {γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
      returnLoss offset : Real}
    (h :
      route5OffsetCandidateFamilyTarget
        γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
        returnLoss offset) :
    secondaryCoerciveOffset γ tailOffset ∨ secondaryCoerciveOffset γ offset := by
  rcases h with htail | htensor | hcurv
  · exact Or.inl htail
  · exact Or.inr htensor.2
  · exact Or.inr hcurv.2.2.2

/--
If none of the candidate families can produce a real offset, the geometric
branch has no live local rescue on the current graph.
-/
theorem no_route5_offset_family_without_real_offset
    {γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
      returnLoss offset : Real}
    (htail :
      ¬ secondaryCoerciveOffset γ tailOffset)
    (hoff :
      ¬ secondaryCoerciveOffset γ offset) :
    ¬ route5OffsetCandidateFamilyTarget
      γ tailOffset coerciveBudget pressureBurden residual curvatureBudget
      returnLoss offset := by
  intro h
  rcases route5_offset_family_implies_real_offset h with hreal | hreal
  · exact htail hreal
  · exact hoff hreal

end ZtareProofs
