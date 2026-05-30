import Mathlib.Tactic
import ZtareProofs.ns_pressure_pollution_bridge

namespace ZtareProofs

/-!
`ns_calderon_zygmund_stealth_obstruction` records the main red-team correction
to the pressure-pollution route.

Positive pressure-Hessian magnitude is not enough. Calderon-Zygmund kernels
have angular cancellation and projection nulls, so the PDE bridge must be a
nonzero *projected off-axis rotation* bound, not merely a pressure-response
magnitude bound.
-/

/-- A scalar projection of the pressure Hessian onto the off-axis eigenframe-rotation channel. -/
abbrev ProjectedPressureRotation := Real

/--
Projected-footprint bridge.

This is the corrected object: pollution is lower-bounded by the pressure
Hessian's off-axis projection, not by undirected pressure magnitude.
-/
def projectedPressureCreatesPollution
    (Pproj : ProjectedPressureRotation) (pollutedPerJump : PollutionPerJump) (κ : Real) : Prop :=
  κ * |Pproj| ≤ pollutedPerJump

/--
Positive pressure magnitude alone does not force positive pollution.

This is the formal warning against the "pressure response exists, therefore
orientation pollution is positive" overclaim. Without a footprint/projection
bridge, one can have positive pressure response and zero pollution.
-/
theorem positive_pressure_response_does_not_force_pollution_without_bridge :
    ∃ (P : PressureHessianResponse) (pollutedPerJump κ : Real),
      0 < P ∧ 0 < κ ∧ pollutedPerJump = 0 ∧
        ¬ pressureHessianCreatesPollution P pollutedPerJump κ := by
  refine ⟨1, 0, 1, ?_⟩
  constructor
  · norm_num
  constructor
  · norm_num
  constructor
  · rfl
  intro h
  unfold pressureHessianCreatesPollution at h
  norm_num at h

/--
If the off-axis projected pressure rotation is bounded away from zero and its
footprint coefficient is positive, then the per-jump pollution is positive.

This is the corrected lower-bound target for the Calderon-Zygmund pressure
operator: prove a non-null projection, not just nonzero pressure.
-/
theorem positive_pollution_of_projected_pressure_footprint
    {Pproj : ProjectedPressureRotation} {pollutedPerJump κ pFloor : Real}
    (hκ : 0 < κ)
    (hfloor : 0 < pFloor)
    (hnonnull : pFloor ≤ |Pproj|)
    (hbridge : projectedPressureCreatesPollution Pproj pollutedPerJump κ) :
    0 < pollutedPerJump := by
  unfold projectedPressureCreatesPollution at hbridge
  have hprod_floor : 0 < κ * pFloor := mul_pos hκ hfloor
  have hprod_le : κ * pFloor ≤ κ * |Pproj| := by
    exact mul_le_mul_of_nonneg_left hnonnull (le_of_lt hκ)
  exact lt_of_lt_of_le hprod_floor (le_trans hprod_le hbridge)

end ZtareProofs
