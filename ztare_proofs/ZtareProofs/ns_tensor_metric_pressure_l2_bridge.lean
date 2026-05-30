import Mathlib.Tactic
import ZtareProofs.ns_tensor_metric_pressure_absorption

namespace ZtareProofs

/-!
`ns_tensor_metric_pressure_l2_bridge` prevents the iter-4 tensor-metric route
from floating free of the existing pressure-side obligations.

If a non-sectional tensor metric is real, it should cash out through the same
pressure-Hessian transport objects already named elsewhere in the proof spine,
not via a separate rhetorical universe.
-/

/--
Compatibility target: a tensor-metric pressure absorption claim is only on the
same proof graph if it is backed by a pressure-Hessian transport bridge.
-/
def tensorMetricCompatibleWithPressureL2
    (reserve pressureL2 higherFeedback grade C K δ
      transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset : Real) : Prop :=
  pressureHessianL2TransportBridgeTarget reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual ∧
    tensorMetricRoute5ClosureTarget coerciveBudget pressureBurden residual offset

/--
If the tensor-metric route does not hook into the pressure-Hessian transport
bridge, then it has not reduced proof cost on the current graph; it has merely
renamed the operator burden.
-/
theorem tensor_metric_needs_pressure_l2_bridge
    {reserve pressureL2 higherFeedback grade C K δ
      transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset : Real}
    (hno :
      ¬ pressureHessianL2TransportBridgeTarget reserve pressureL2 higherFeedback
        grade C K δ transportDefect localQuadratic advectedPressure residual) :
    ¬ tensorMetricCompatibleWithPressureL2 reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset := by
  intro h
  exact hno h.1

/--
Conversely, if both the pressure-side bridge and the tensor-metric closure
target are paid, then the tensor-metric route is at least speaking the same
mathematical language as the rest of route 5.
-/
theorem tensor_metric_is_on_graph_if_pressure_bridge_paid
    {reserve pressureL2 higherFeedback grade C K δ
      transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset : Real}
    (hpressure :
      pressureHessianL2TransportBridgeTarget reserve pressureL2 higherFeedback
        grade C K δ transportDefect localQuadratic advectedPressure residual)
    (htensor :
      tensorMetricRoute5ClosureTarget coerciveBudget pressureBurden residual offset) :
    tensorMetricCompatibleWithPressureL2 reserve pressureL2 higherFeedback
      grade C K δ transportDefect localQuadratic advectedPressure residual
      coerciveBudget pressureBurden offset := by
  exact And.intro hpressure htensor

end ZtareProofs
