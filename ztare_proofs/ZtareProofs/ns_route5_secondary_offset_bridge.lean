import Mathlib.Tactic
import ZtareProofs.ns_route5_constructive_frontier

namespace ZtareProofs

/-!
`ns_route5_secondary_offset_bridge` isolates the exact next discriminator on
the geometric branch.

After the constructive iterations and local compression, route 5 no longer
lives or dies on "does geometry help?" It lives or dies on a narrower fork:

* if the sub-dyadic exponent stays positive, is there a real secondary
  coercive offset that closes it?
* if not, the route collapses back below route 1.
-/

/--
Exact route-5 next discriminator: the branch must carry both the constructive
sub-dyadic hinge and an explicit closure object for the positive residual.
-/
def route5SecondaryOffsetDiscriminatorTarget
    (transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real)
    (isIntrinsic : Prop) : Prop :=
  route5ConstructiveFrontierTarget transportDefect umbilicExposure
      nonlocalityBudget pressureCarrier alignmentQuality connectionDefect
      strainGradient gap floor γ flatExponent offset reserve pressureL2
      higherFeedback grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden isIntrinsic ∧
    route5SubdyadicClosureTarget γ offset

/--
If the geometric branch is still carrying a positive residual exponent and no
secondary coercive offset is available, the route-5 closure target fails.
-/
theorem route5_positive_residual_needs_offset
    {γ offset : Real}
    (hγpos : 0 < γ)
    (hno : ¬ secondaryCoerciveOffset γ offset) :
    ¬ route5SubdyadicClosureTarget γ offset := by
  intro h
  rcases h with hsum | hoff
  · exact (positive_subdyadic_not_summable hγpos) hsum
  · exact hno hoff

/--
Route 5 only survives a positive sub-dyadic residual if the secondary offset
branch is actually paid.
-/
theorem route5_secondary_offset_or_collapse
    {transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real}
    {isIntrinsic : Prop}
    (h :
      route5SecondaryOffsetDiscriminatorTarget transportDefect umbilicExposure
        nonlocalityBudget pressureCarrier alignmentQuality connectionDefect
        strainGradient gap floor γ flatExponent offset reserve pressureL2
        higherFeedback grade C K δ localQuadratic advectedPressure residual
        coerciveBudget pressureBurden isIntrinsic)
    (hγpos : 0 < γ) :
    secondaryCoerciveOffset γ offset := by
  rcases h with ⟨_, hclosure⟩
  rcases hclosure with hsum | hoff
  · exact False.elim ((positive_subdyadic_not_summable hγpos) hsum)
  · exact hoff

end ZtareProofs
