import Mathlib.Tactic

namespace ZtareProofs

/-!
`ns_quadrupole_identity` isolates the exact algebraic layer of the Phase 5CG
`l = 2` route.

This file does not prove the tensor calculus of Navier-Stokes. It records the
precise theorem targets identified by the representation-theory panel:

1. the trace part annihilates symmetric traceless strain;
2. instantaneous stretching density factors through the deviatoric quadrupole;
3. the immediate norm bound follows from that identity.

Anything beyond this is a PDE bridge, not exact algebra.
-/

/-- Pointwise stretching density, e.g. `ω · S ω`. -/
abbrev StretchDensity := Real

/-- Scalar placeholder for the isotropic trace contribution. -/
abbrev TraceContribution := Real

/-- Scalar placeholder for the deviatoric quadrupole contraction. -/
abbrev QuadrupoleContraction := Real

/-- Norm of the deviatoric quadrupole carrier. -/
abbrev QuadrupoleNorm := Real

/-- Norm of the traceless strain carrier. -/
abbrev StrainNorm := Real

/-- The isotropic trace component contributes nothing against traceless strain. -/
def tracePartAnnihilatesTracelessStrain
    (traceContribution : TraceContribution) : Prop :=
  traceContribution = 0

/--
Exact instantaneous quadrupole identity.

This is the narrow algebraic closure:
the stretching density equals the deviatoric quadrupole contraction.
-/
def strainContractionEqQuadrupoleContraction
    (stretchDensity quadrupoleContraction : Real) : Prop :=
  stretchDensity = quadrupoleContraction

/-- Immediate norm inequality associated with the exact quadrupole identity. -/
def strainContractionLeQuadrupoleNormMulStrainNorm
    (stretchDensity quadrupoleNorm strainNorm : Real) : Prop :=
  |stretchDensity| ≤ quadrupoleNorm * strainNorm

/--
If the exact quadrupole identity is paid and the quadrupole contraction is
itself bounded by the product norm, then the stretching density inherits the
same bound.
-/
theorem strain_contraction_le_quadrupole_norm_mul_strain_norm_of_identity
    {stretchDensity quadrupoleContraction quadrupoleNorm strainNorm : Real}
    (hid : strainContractionEqQuadrupoleContraction stretchDensity quadrupoleContraction)
    (hbound : |quadrupoleContraction| ≤ quadrupoleNorm * strainNorm) :
    strainContractionLeQuadrupoleNormMulStrainNorm stretchDensity quadrupoleNorm strainNorm := by
  unfold strainContractionEqQuadrupoleContraction at hid
  unfold strainContractionLeQuadrupoleNormMulStrainNorm
  simpa [hid] using hbound

end ZtareProofs
