import Mathlib.Tactic
import ZtareProofs.ns_pressure_hessian_l2_bridge
import ZtareProofs.ns_subdyadic_summability_barrier

namespace ZtareProofs

/-!
`ns_tensor_metric_pressure_absorption` records the exact unpaid term exposed by
iter 4 on the constructive route-5 substrate.

The proposed escape was a non-sectional tensor metric, meant to avoid the
eigenframe gap singularity by refusing to diagonalize. That category jump is
only legitimate if it pays the operator-level pressure-Hessian burden rather
than renaming it.

So the live tensor-metric hinge is:

* does the pressure Hessian get absorbed into the Riccati / tensor-metric
  coercive term, or
* does route 5 merely swap one unpaid operator for another?
-/

/-- Scalar proxy for the Riccati-side coercive budget of a tensor metric route. -/
abbrev TensorMetricCoerciveBudget := Real

/-- Scalar proxy for the pressure-Hessian commutator burden in that route. -/
abbrev PressureHessianAbsorptionBurden := Real

/-- Scalar proxy for the net residual after attempting tensor-metric absorption. -/
abbrev TensorMetricResidual := Real

/--
The tensor-metric route pays its operator burden only if the pressure-Hessian
commutator is absorbed into the coercive budget up to a controlled residual.
-/
def tensorMetricPressureAbsorptionTarget
    (coerciveBudget pressureBurden residual : Real) : Prop :=
  0 ≤ coerciveBudget ∧
    0 ≤ pressureBurden ∧
    pressureBurden ≤ coerciveBudget + residual

/--
If the residual is still positive, the tensor-metric route inherits the same
closure burden as the mollified-frame route: it still needs summability or a
secondary offset.
-/
def tensorMetricResidualClosureTarget
    (residual offset : Real) : Prop :=
  route5SubdyadicClosureTarget residual offset

/--
Exact iter-4 hinge: a non-sectional tensor metric is a real route-5 advance
only if it both absorbs the pressure-Hessian burden and closes the remaining
residual budget.
-/
def tensorMetricRoute5ClosureTarget
    (coerciveBudget pressureBurden residual offset : Real) : Prop :=
  tensorMetricPressureAbsorptionTarget coerciveBudget pressureBurden residual ∧
    tensorMetricResidualClosureTarget residual offset

/--
Without pressure-Hessian absorption, the tensor-metric route has not earned the
right to retire the earlier route-5 hinges.
-/
theorem tensor_metric_route_not_closed_without_absorption
    {coerciveBudget pressureBurden residual offset : Real}
    (hno : ¬ tensorMetricPressureAbsorptionTarget coerciveBudget pressureBurden residual) :
    ¬ tensorMetricRoute5ClosureTarget coerciveBudget pressureBurden residual offset := by
  intro h
  exact hno h.1

end ZtareProofs
