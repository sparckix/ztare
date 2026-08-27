import ZtareProofs.FormalPowerSeriesLinearODE
import ZtareProofs.FormalSimpleZeroTensorDensityNormalForm

/-!
# Twisted simple-zero tensor-density normal form

The row-indexed tensor residual `K = X C` does not carry the untwisted
weight-`3/2` action of `C`.  For the corrected action

`T_phi(K)(X) = X / phi(X) * K(phi(X)) / phi'(X)^(3/2)`,

the linear representative `c X` is sent to `c X / phi'^(3/2)`.  This file
constructs `phi' = v^(-2/3)` for every normalized unit `v`, proves the exact
fractional-power identity, and then normalizes every simple-zero formal
residual.  It does not assert that the iterative logarithm of `phi` is a
polynomial vector field.
-/

namespace ZtareProofs.FormalTwistedSimpleZeroTensorDensityNormalForm

open PowerSeries
open ZtareProofs.FormalSimpleZeroTensorDensityNormalForm
open FormalPowerSeriesLinearODE

noncomputable section

variable {k : Type*} [Field k] [CharZero k]

/-- Canonical tangent coordinate for the row-indexed density twist. -/
noncomputable def twistedOrbitCoordinate (v : k⟦X⟧) : k⟦X⟧ :=
  integralZero (unitPower v (-2 / 3 : ℚ))

@[simp]
theorem twistedOrbitCoordinate_constantCoeff (v : k⟦X⟧) :
    constantCoeff (twistedOrbitCoordinate v) = 0 := by
  exact constantCoeff_integralZero _

@[simp]
theorem derivative_twistedOrbitCoordinate (v : k⟦X⟧) :
    d⁄dX k (twistedOrbitCoordinate v) =
      unitPower v (-2 / 3 : ℚ) := by
  exact derivative_integralZero _

theorem twistedOrbitCoordinate_linearCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    coeff 1 (twistedOrbitCoordinate v) = 1 := by
  have hderivative := congrArg (coeff 0)
    (derivative_twistedOrbitCoordinate v)
  rw [coeff_derivative] at hderivative
  simpa [unitPower_constantCoeff v hv] using hderivative

/-- The normalized `(-3/2)` derivative factor in the twisted finite action. -/
noncomputable def twistedDensityTransport (v : k⟦X⟧) : k⟦X⟧ :=
  unitPower (d⁄dX k (twistedOrbitCoordinate v)) (-3 / 2 : ℚ)

theorem twistedDensityTransport_constantCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    constantCoeff (twistedDensityTransport v) = 1 := by
  rw [twistedDensityTransport, derivative_twistedOrbitCoordinate]
  apply unitPower_constantCoeff
  exact unitPower_constantCoeff v hv _

/-- Exact corrected finite-action identity on normalized units. -/
theorem twistedDensityTransport_eq (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    twistedDensityTransport v = v := by
  let unitRoot := unitPower v (-2 / 3 : ℚ)
  let inverseDensityRoot := unitPower unitRoot (-3 / 2 : ℚ)
  have hunitRootConstant : constantCoeff unitRoot = 1 :=
    unitPower_constantCoeff v hv _
  have hinverseRoot :
      inverseDensityRoot ^ 2 * unitRoot ^ 3 = 1 :=
    unitPower_neg_three_halves_square unitRoot hunitRootConstant
  have hsourceRoot : unitRoot ^ 3 * v ^ 2 = 1 :=
    unitPower_neg_two_thirds_cube v hv
  have hunitRootNonzero : unitRoot ^ 3 ≠ 0 := by
    intro hzero
    have hconstant := congrArg constantCoeff hzero
    simp [hunitRootConstant] at hconstant
  have hsquares : inverseDensityRoot ^ 2 = v ^ 2 := by
    apply mul_right_cancel₀ hunitRootNonzero
    calc
      inverseDensityRoot ^ 2 * unitRoot ^ 3 = 1 := hinverseRoot
      _ = v ^ 2 * unitRoot ^ 3 := by
        rw [mul_comm]
        exact hsourceRoot.symm
  have hinverseConstant : constantCoeff inverseDensityRoot = 1 :=
    unitPower_constantCoeff unitRoot hunitRootConstant _
  have hinverseEq : inverseDensityRoot = v :=
    normalizedUnit_eq_of_sq_eq inverseDensityRoot v
      hinverseConstant hv hsquares
  rw [twistedDensityTransport, derivative_twistedOrbitCoordinate]
  exact hinverseEq

/-- Branch-free exact check of the corrected orbit equation. -/
theorem twisted_squaredDensityOrbit (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    (X * v) ^ 2 * (d⁄dX k (twistedOrbitCoordinate v)) ^ 3 = X ^ 2 := by
  rw [derivative_twistedOrbitCoordinate]
  have hroot := unitPower_neg_two_thirds_cube v hv
  calc
    (X * v) ^ 2 * (unitPower v (-2 / 3 : ℚ)) ^ 3 =
        X ^ 2 * ((unitPower v (-2 / 3 : ℚ)) ^ 3 * v ^ 2) := by
      ring
    _ = X ^ 2 := by rw [hroot, mul_one]

/-- Every simple-zero row-indexed density lies in the corrected twisted
orbit of its linear monomial. -/
theorem twistedSimpleZero_densityOrbit (residual : k⟦X⟧)
    (hconstant : constantCoeff residual = 0)
    (hlinear : coeff 1 residual ≠ 0) :
    residual =
      C (coeff 1 residual) * X *
        unitPower
          (d⁄dX k (twistedOrbitCoordinate (simpleZeroUnit residual)))
          (-3 / 2 : ℚ) := by
  have hunit := simpleZeroUnit_constantCoeff residual hlinear
  have htransport := twistedDensityTransport_eq
    (simpleZeroUnit residual) hunit
  rw [twistedDensityTransport] at htransport
  calc
    residual = C (coeff 1 residual) *
        (X * simpleZeroUnit residual) :=
      (simpleZero_factorization residual hconstant hlinear).symm
    _ = C (coeff 1 residual) * X *
        unitPower
          (d⁄dX k (twistedOrbitCoordinate (simpleZeroUnit residual)))
          (-3 / 2 : ℚ) := by
      rw [htransport]
      ring

/-- All-order corrected critical-quotient orbit certificate. -/
theorem twisted_simple_zero_density_orbit_terminal_certificate :
    ∀ residual : k⟦X⟧,
      constantCoeff residual = 0 →
      coeff 1 residual ≠ 0 →
      constantCoeff (simpleZeroUnit residual) = 1 ∧
      constantCoeff (twistedOrbitCoordinate (simpleZeroUnit residual)) = 0 ∧
      coeff 1 (twistedOrbitCoordinate (simpleZeroUnit residual)) = 1 ∧
      residual =
        C (coeff 1 residual) * X *
          unitPower
            (d⁄dX k
              (twistedOrbitCoordinate (simpleZeroUnit residual)))
            (-3 / 2 : ℚ) := by
  intro residual hconstant hlinear
  have hunit := simpleZeroUnit_constantCoeff residual hlinear
  exact ⟨hunit, twistedOrbitCoordinate_constantCoeff _,
    twistedOrbitCoordinate_linearCoeff _ hunit,
    twistedSimpleZero_densityOrbit residual hconstant hlinear⟩

end

end ZtareProofs.FormalTwistedSimpleZeroTensorDensityNormalForm
