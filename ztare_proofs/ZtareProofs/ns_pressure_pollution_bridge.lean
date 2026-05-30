import Mathlib.Tactic
import ZtareProofs.ns_zeno_gridlock_threshold

namespace ZtareProofs

/-!
`ns_pressure_pollution_bridge` names the "flash wash" inversion.

The clean-relay rival says the elliptic pressure field might instantly clear a
dirty local frame. The inversion is that elliptic redistribution is not erasure:
if the Pressure Hessian is the channel that moves the debt, then it must leave
an orientation/eigenframe footprint counted by the gridlock ledger.

This file does not derive the Pressure Hessian estimate from Navier-Stokes. It
turns that estimate into the exact scalar obligations consumed by
`ns_topological_gridlock` and `ns_zeno_gridlock_threshold`.
-/

/-- Scalar size of the pressure-Hessian response during a handoff. -/
abbrev PressureHessianResponse := Real

/-- Per-jump orientation/eigenframe real estate polluted by the response. -/
abbrev PollutionPerJump := Real

/--
Pressure-Hessian footprint bridge.

`κ * P <= pollutedPerJump` says that a pressure-Hessian response of size `P`
cannot be a zero-footprint cleanup event: at least this much orientation volume
is marked dirty by the redistribution. Proving this from the pressure Poisson
equation and eigenframe perturbation theory is the PDE work.
-/
def pressureHessianCreatesPollution
    (P : PressureHessianResponse) (pollutedPerJump : PollutionPerJump) (κ : Real) : Prop :=
  κ * P ≤ pollutedPerJump

/--
If the pressure-Hessian response is strictly positive and the footprint
coefficient is strictly positive, the per-jump pollution is nonzero.

This closes the "needle jump" loophole at the scalar level once the PDE supplies
the pressure-footprint bridge.
-/
theorem positive_pollution_per_jump_of_pressure_hessian
    {P : PressureHessianResponse} {pollutedPerJump : PollutionPerJump} {κ : Real}
    (hκ : 0 < κ)
    (hP : 0 < P)
    (hbridge : pressureHessianCreatesPollution P pollutedPerJump κ) :
    0 < pollutedPerJump := by
  unfold pressureHessianCreatesPollution at hbridge
  have hprod : 0 < κ * P := mul_pos hκ hP
  exact lt_of_lt_of_le hprod hbridge

/--
Pressure-Hessian route to finite-capacity gridlock.

If pressure response creates a nonzero polluted footprint per jump, then the
finite-capacity threshold theorem applies. In other words: using pressure as the
flash-wash channel consumes orientation capacity instead of bypassing it.
-/
theorem clean_relay_contradiction_of_pressure_hessian_footprint
    {Vclean Vtotal jumpCount pollutedPerJump cleanupRate elapsedTime : Real}
    {P : PressureHessianResponse} {κ : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (haccount :
      cleanVolumeAccounting
        Vclean
        Vtotal
        (jumpCount * pollutedPerJump)
        (cleanupRate * elapsedTime))
    (hκ : 0 < κ)
    (hP : 0 < P)
    (hbridge : pressureHessianCreatesPollution P pollutedPerJump κ)
    (hcount :
      (Vtotal + cleanupRate * elapsedTime) / pollutedPerJump < jumpCount) :
    False := by
  have hpollute : 0 < pollutedPerJump :=
    positive_pollution_per_jump_of_pressure_hessian hκ hP hbridge
  exact clean_relay_contradiction_of_jumpCount_threshold
    hVclean_nonneg haccount hpollute hcount

/--
Debt-export form of the same inversion.

If local debt is "washed" through a pressure-Hessian channel and that pressure
response lower-bounds component-halo debt, then the existing component-halo
gridlock theorem applies. This is the algebraic statement that pressure can
move debt into the halo ledger, but not erase it.
-/
theorem clean_relay_contradiction_of_pressure_exported_halo_debt
    {Vclean Vtotal Vpolluted Vcleaned : Real}
    {P Halo : Real}
    (hVclean_nonneg : 0 ≤ Vclean)
    (hpressure_to_halo : P ≤ Halo)
    (hhalo_pollution : componentHaloLowerBoundsPollution Halo Vpolluted)
    (haccount : cleanVolumeAccounting Vclean Vtotal Vpolluted Vcleaned)
    (hpressure_exceeds : Vtotal + Vcleaned < P) :
    False := by
  have hhalo_exceeds : Vtotal + Vcleaned < Halo := by
    linarith
  exact clean_relay_contradiction_of_component_halo_debt
    hVclean_nonneg hhalo_pollution haccount hhalo_exceeds

end ZtareProofs
