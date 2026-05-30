import Mathlib.Tactic
import ZtareProofs.ns_viscous_exhaust_horizon

namespace ZtareProofs

/-!
`ns_kinematic_compensation` proves the part of the compensation story that is
currently purely kinematic.

For an incompressible local deformation, axial escape cannot be free: if one
principal direction expands while volume is preserved, the transverse area
factor contracts. This is not yet the full Navier-Stokes thickness law, but it
is the algebraic core any such law has to use.
-/

/-- Local volume preservation for an axial/transverse split. -/
def volumePreservingSplit (axial transverseArea : Real) : Prop :=
  axial * transverseArea = 1

/--
If a volume-preserving split has axial expansion greater than one, then the
transverse area factor is strictly less than one.
-/
theorem transverse_area_contracts_of_axial_escape
    {axial transverseArea : Real}
    (hvol : volumePreservingSplit axial transverseArea)
    (haxial : 1 < axial) :
    transverseArea < 1 := by
  unfold volumePreservingSplit at hvol
  by_contra hnot
  have htrans : 1 ≤ transverseArea := le_of_not_gt hnot
  have haxial_nonneg : 0 ≤ axial := by linarith
  have hprod_ge : 1 * 1 ≤ axial * transverseArea := by
    exact mul_le_mul (le_of_lt haxial) htrans (by norm_num) haxial_nonneg
  have hprod_gt : 1 < axial * transverseArea := by
    nlinarith [haxial, htrans]
  nlinarith [hvol, hprod_gt]

/--
Trace-zero strain compensation: if the axial strain rate is positive, the
sum of the two transverse strain rates is negative.
-/
theorem transverse_strain_sum_negative_of_trace_zero_escape
    {lam1 lam2 lam3 : Real}
    (htrace : lam1 + lam2 + lam3 = 0)
    (hescape : 0 < lam3) :
    lam1 + lam2 < 0 := by
  linarith

/--
At least one transverse strain direction must be negative under trace-zero
axial escape.
-/
theorem exists_transverse_compression_of_trace_zero_escape
    {lam1 lam2 lam3 : Real}
    (htrace : lam1 + lam2 + lam3 = 0)
    (hescape : 0 < lam3) :
    lam1 < 0 ∨ lam2 < 0 := by
  have hsum : lam1 + lam2 < 0 :=
    transverse_strain_sum_negative_of_trace_zero_escape htrace hescape
  by_contra hnone
  have h1 : 0 ≤ lam1 := by
    exact le_of_not_gt (fun h => hnone (Or.inl h))
  have h2 : 0 ≤ lam2 := by
    exact le_of_not_gt (fun h => hnone (Or.inr h))
  nlinarith

/--
Kinematic bridge target.

This packages the precise consequence currently proved: incompressibility plus
axial escape forces transverse area contraction. To reach the existing
`incompressibleCompensationTarget`, a future analytic step must upgrade area
contraction into a quantitative thickness/aspect-ratio law across returns.
-/
theorem kinematic_compensation_target_shape
    {axial transverseArea : Real}
    (hvol : volumePreservingSplit axial transverseArea)
    (haxial : 1 < axial) :
    transverseArea < 1 := by
  exact transverse_area_contracts_of_axial_escape hvol haxial

end ZtareProofs
