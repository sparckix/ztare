import Mathlib.Tactic
import ZtareProofs.ns_nonlocal_frame_transport_gap
import ZtareProofs.ns_eigenvalue_repulsion_or_collapse
import ZtareProofs.ns_mollified_frame_subdyadic_bridge
import ZtareProofs.ns_subdyadic_summability_barrier
import ZtareProofs.ns_intrinsic_frame_mollification_universality
import ZtareProofs.ns_tensor_metric_pressure_l2_bridge

namespace ZtareProofs

/-!
`ns_route5_constructive_frontier` packages the exact live route-5 obligations
after the constructive proof-search iterations and local proof compression.

This is not a closure theorem. It is the current route map in theorem-cage
form, so future local work or future ZTARE reruns attack the same graph:

1. non-local frame gap,
2. eigenvalue repulsion or collapse,
3. mollified-frame sub-dyadic escape,
4. sub-dyadic closure via summability or secondary offset,
5. intrinsic universality barrier,
6. tensor-metric pressure-Hessian absorption / on-graph check.
-/

/--
Unified route-5 frontier target.
-/
def route5ConstructiveFrontierTarget
    (transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real)
    (isIntrinsic : Prop) : Prop :=
    route5NonlocalFrameGapTarget transportDefect umbilicExposure nonlocalityBudget
      pressureCarrier alignmentQuality ∧
    route5EigenvalueRepulsionOrCollapse connectionDefect strainGradient gap floor ∧
    route5MollifiedEscapeHinge γ flatExponent ∧
    route5SubdyadicClosureTarget γ offset ∧
    intrinsicMollificationUniversalityTarget isIntrinsic γ ∧
    tensorMetricCompatibleWithPressureL2 reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset

/--
Projection theorem: the packaged frontier really contains the route-5
sub-dyadic hinge as one of its load-bearing obligations.
-/
theorem route5_frontier_contains_subdyadic_hinge
    {transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real}
    {isIntrinsic : Prop}
    (h :
      route5ConstructiveFrontierTarget transportDefect umbilicExposure
        nonlocalityBudget pressureCarrier alignmentQuality connectionDefect
        strainGradient gap floor γ flatExponent offset reserve pressureL2
        higherFeedback grade C K δ localQuadratic advectedPressure residual
        coerciveBudget pressureBurden isIntrinsic) :
    route5MollifiedEscapeHinge γ flatExponent := by
  exact h.2.2.1

/--
Projection theorem: route 5 now carries the exact closure fork explicitly,
not only the "sub-dyadic sounds better" hinge.
-/
theorem route5_frontier_contains_subdyadic_closure
    {transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real}
    {isIntrinsic : Prop}
    (h :
      route5ConstructiveFrontierTarget transportDefect umbilicExposure
        nonlocalityBudget pressureCarrier alignmentQuality connectionDefect
        strainGradient gap floor γ flatExponent offset reserve pressureL2
        higherFeedback grade C K δ localQuadratic advectedPressure residual
        coerciveBudget pressureBurden isIntrinsic) :
    route5SubdyadicClosureTarget γ offset := by
  exact h.2.2.2.1

/--
Projection theorem: the packaged frontier also contains the tensor-metric
stay-on-graph obligation.
-/
theorem route5_frontier_contains_tensor_metric_check
    {transportDefect umbilicExposure nonlocalityBudget pressureCarrier
      alignmentQuality connectionDefect strainGradient gap floor
      γ flatExponent offset reserve pressureL2 higherFeedback
      grade C K δ localQuadratic advectedPressure residual
      coerciveBudget pressureBurden : Real}
    {isIntrinsic : Prop}
    (h :
      route5ConstructiveFrontierTarget transportDefect umbilicExposure
        nonlocalityBudget pressureCarrier alignmentQuality connectionDefect
        strainGradient gap floor γ flatExponent offset reserve pressureL2
        higherFeedback grade C K δ localQuadratic advectedPressure residual
        coerciveBudget pressureBurden isIntrinsic) :
    tensorMetricCompatibleWithPressureL2 reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset := by
  exact h.2.2.2.2.2

end ZtareProofs
