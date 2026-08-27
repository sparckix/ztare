import Mathlib.RingTheory.PowerSeries.Binomial
import Mathlib.RingTheory.PowerSeries.Derivative
import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic

/-!
# Formal normal form for a simple-zero tensor density

For a normalized unit `v`, the fractional unit `u = v^(-2/3)` is defined
by binomial substitution.  The diagonal Euler equation

`w + 3 X w' = u`

has the coefficientwise solution `w_n = u_n / (1 + 3n)`.  The tangent
coordinate `phi = X w^3` then satisfies the complete squared density-orbit
identity

`(X v)^2 * (phi')^3 = phi^2`.

The squared equation is the algebraic form of the weight-`3/2` action and
does not choose an analytic square-root branch.
-/

namespace ZtareProofs.FormalSimpleZeroTensorDensityNormalForm

open PowerSeries

noncomputable section

variable {k : Type*} [Field k] [CharZero k]

omit [CharZero k] in
/-- The zero-constant substitution used to evaluate a binomial series at a
normalized unit. -/
theorem unitOffset_hasSubst (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    HasSubst (v - 1) := by
  apply HasSubst.of_constantCoeff_zero'
  simp [hv]

/-- Formal fractional power of a unit normalized by `v(0)=1`. -/
noncomputable def unitPower (v : k⟦X⟧) (exponent : ℚ) : k⟦X⟧ :=
  (PowerSeries.binomialSeries k exponent).subst (v - 1)

theorem unitPower_add (v : k⟦X⟧)
    (hv : constantCoeff v = 1) (a b : ℚ) :
    unitPower v (a + b) = unitPower v a * unitPower v b := by
  rw [unitPower, PowerSeries.binomialSeries_add]
  exact PowerSeries.subst_mul (unitOffset_hasSubst v hv) _ _

@[simp]
theorem unitPower_zero (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    unitPower v 0 = 1 := by
  rw [unitPower, show PowerSeries.binomialSeries k (0 : ℚ) =
      (1 : k⟦X⟧) from PowerSeries.binomialSeries_zero]
  rw [← PowerSeries.coe_substAlgHom (unitOffset_hasSubst v hv), map_one]

theorem unitPower_nat (v : k⟦X⟧)
    (hv : constantCoeff v = 1) (n : ℕ) :
    unitPower v (n : ℚ) = v ^ n := by
  rw [unitPower, show PowerSeries.binomialSeries k (n : ℚ) =
      (1 + X : k⟦X⟧) ^ n from PowerSeries.binomialSeries_nat n]
  rw [PowerSeries.subst_pow (unitOffset_hasSubst v hv)]
  congr 1
  rw [PowerSeries.subst_add (unitOffset_hasSubst v hv)]
  have hone : PowerSeries.subst (R := k) (v - 1) (1 : k⟦X⟧) = 1 := by
    rw [← PowerSeries.coe_substAlgHom (unitOffset_hasSubst v hv), map_one]
  rw [hone, PowerSeries.subst_X (unitOffset_hasSubst v hv)]
  ring

/-- The canonical `(-2/3)` unit power has the exact cubed inverse-square
identity, with no truncation. -/
theorem unitPower_neg_two_thirds_cube (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    (unitPower v (-2 / 3 : ℚ)) ^ 3 * v ^ 2 = 1 := by
  have hdouble := unitPower_add v hv (-2 / 3 : ℚ) (-2 / 3 : ℚ)
  have htriple := unitPower_add v hv (-4 / 3 : ℚ) (-2 / 3 : ℚ)
  have hminusTwo :
      (unitPower v (-2 / 3 : ℚ)) ^ 3 = unitPower v (-2 : ℚ) := by
    calc
      (unitPower v (-2 / 3 : ℚ)) ^ 3 =
          (unitPower v (-2 / 3 : ℚ) * unitPower v (-2 / 3 : ℚ)) *
            unitPower v (-2 / 3 : ℚ) := by ring
      _ = unitPower v (-4 / 3 : ℚ) * unitPower v (-2 / 3 : ℚ) := by
        rw [← hdouble]
        norm_num
      _ = unitPower v (-2 : ℚ) := by
        rw [← htriple]
        norm_num
  rw [hminusTwo, ← unitPower_nat v hv 2]
  rw [← unitPower_add v hv]
  norm_num [unitPower_zero v hv]

/-- The canonical `(-3/2)` unit power is the normalized inverse square root
of the cube. -/
theorem unitPower_neg_three_halves_square (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    (unitPower v (-3 / 2 : ℚ)) ^ 2 * v ^ 3 = 1 := by
  have hdouble := unitPower_add v hv (-3 / 2 : ℚ) (-3 / 2 : ℚ)
  have hminusThree :
      (unitPower v (-3 / 2 : ℚ)) ^ 2 = unitPower v (-3 : ℚ) := by
    calc
      (unitPower v (-3 / 2 : ℚ)) ^ 2 =
          unitPower v (-3 / 2 : ℚ) *
            unitPower v (-3 / 2 : ℚ) := by ring
      _ = unitPower v (-3 : ℚ) := by
        rw [← hdouble]
        norm_num
  rw [hminusThree, ← unitPower_nat v hv 3]
  rw [← unitPower_add v hv]
  norm_num [unitPower_zero v hv]

/-- The diagonal Euler operator occurring in the weight-`3/2` orbit
equation. -/
def weightedEuler (series : k⟦X⟧) : k⟦X⟧ :=
  series + (3 : k) • (X * d⁄dX k series)

/-- Coefficientwise inverse of `weightedEuler` in characteristic zero. -/
noncomputable def solveWeightedEuler (right : k⟦X⟧) : k⟦X⟧ :=
  PowerSeries.mk fun n =>
    coeff n right / ((1 + 3 * n : ℕ) : k)

omit [CharZero k] in
theorem coeff_weightedEuler (series : k⟦X⟧) (n : ℕ) :
    coeff n (weightedEuler series) =
      ((1 + 3 * n : ℕ) : k) * coeff n series := by
  cases n with
  | zero =>
      simp [weightedEuler]
  | succ n =>
      simp only [weightedEuler, map_add, coeff_smul,
        coeff_succ_X_mul, coeff_derivative]
      push_cast
      ring

@[simp]
theorem weightedEuler_solve (right : k⟦X⟧) :
    weightedEuler (solveWeightedEuler right) = right := by
  ext n
  rw [coeff_weightedEuler]
  simp only [solveWeightedEuler, coeff_mk]
  have hdenominator : ((1 + 3 * n : ℕ) : k) ≠ 0 := by
    exact_mod_cast (by omega : (1 + 3 * n : ℕ) ≠ 0)
  field_simp

theorem solveWeightedEuler_unique
    (right left : k⟦X⟧)
    (hleft : weightedEuler left = right) :
    left = solveWeightedEuler right := by
  apply PowerSeries.ext
  intro n
  have hcoefficient := congrArg (coeff n) hleft
  rw [coeff_weightedEuler] at hcoefficient
  rw [solveWeightedEuler, coeff_mk]
  have hdenominator : ((1 + 3 * n : ℕ) : k) ≠ 0 := by
    exact_mod_cast (by omega : (1 + 3 * n : ℕ) ≠ 0)
  apply (eq_div_iff hdenominator).2
  simpa only [mul_comm] using hcoefficient

/-- Unit solving the tensor-density Euler equation. -/
noncomputable def orbitUnit (v : k⟦X⟧) : k⟦X⟧ :=
  solveWeightedEuler (unitPower v (-2 / 3 : ℚ))

/-- Tangent coordinate which normalizes the simple-zero density. -/
noncomputable def orbitCoordinate (v : k⟦X⟧) : k⟦X⟧ :=
  X * orbitUnit v ^ 3

theorem unitPower_constantCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) (exponent : ℚ) :
    constantCoeff (unitPower v exponent) = 1 := by
  rw [unitPower]
  have hoffset : constantCoeff (v - 1) = 0 := by simp [hv]
  change MvPowerSeries.constantCoeff
      ((PowerSeries.binomialSeries k exponent).subst (v - 1)) = 1
  rw [PowerSeries.constantCoeff_subst
    (unitOffset_hasSubst v hv)]
  rw [finsum_eq_single _ 0 (fun d hd => by
    have hzero :
        MvPowerSeries.constantCoeff (v - 1) = 0 := by
      rw [← PowerSeries.constantCoeff_eq]
      exact hoffset
    simp [hzero, hd])]
  simp

@[simp]
theorem orbitUnit_constantCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    constantCoeff (orbitUnit v) = 1 := by
  rw [← coeff_zero_eq_constantCoeff]
  simp [orbitUnit, solveWeightedEuler,
    unitPower_constantCoeff v hv]

theorem orbitCoordinate_constantCoeff (v : k⟦X⟧) :
    constantCoeff (orbitCoordinate v) = 0 := by
  simp [orbitCoordinate]

theorem orbitCoordinate_linearCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    coeff 1 (orbitCoordinate v) = 1 := by
  rw [orbitCoordinate, coeff_succ_X_mul]
  rw [coeff_zero_eq_constantCoeff, map_pow,
    orbitUnit_constantCoeff v hv]
  simp

theorem derivative_orbitCoordinate (v : k⟦X⟧) :
    d⁄dX k (orbitCoordinate v) =
      orbitUnit v ^ 2 * weightedEuler (orbitUnit v) := by
  rw [orbitCoordinate, (PowerSeries.derivative k).leibniz,
    PowerSeries.derivative_X, PowerSeries.derivative_pow]
  simp only [weightedEuler, Nat.cast_ofNat, Nat.add_one_sub_one,
    smul_eq_mul, mul_one, Algebra.smul_def]
  rw [show (algebraMap k k⟦X⟧) (3 : k) = (3 : k⟦X⟧) by
    exact map_natCast (algebraMap k k⟦X⟧) 3]
  ring

theorem orbitCoordinate_derivative_constantCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    constantCoeff (d⁄dX k (orbitCoordinate v)) = 1 := by
  rw [← coeff_zero_eq_constantCoeff, coeff_derivative]
  simp [orbitCoordinate_linearCoeff v hv]

/-- Complete algebraic density-orbit identity.  Both sides retain every
coefficient; the square avoids selecting a fractional analytic branch. -/
theorem simpleZero_squaredDensityOrbit (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    (X * v) ^ 2 * (d⁄dX k (orbitCoordinate v)) ^ 3 =
      orbitCoordinate v ^ 2 := by
  have heuler :
      weightedEuler (orbitUnit v) = unitPower v (-2 / 3 : ℚ) := by
    exact weightedEuler_solve _
  rw [derivative_orbitCoordinate, heuler]
  have hroot := unitPower_neg_two_thirds_cube v hv
  rw [orbitCoordinate]
  calc
    (X * v) ^ 2 *
          (orbitUnit v ^ 2 * unitPower v (-2 / 3 : ℚ)) ^ 3 =
        X ^ 2 * orbitUnit v ^ 6 *
          ((unitPower v (-2 / 3 : ℚ)) ^ 3 * v ^ 2) := by ring
    _ = X ^ 2 * orbitUnit v ^ 6 := by rw [hroot, mul_one]
    _ = (X * orbitUnit v ^ 3) ^ 2 := by ring

/-- A normalized unit is determined by its square in characteristic zero. -/
theorem normalizedUnit_eq_of_sq_eq
    (left right : k⟦X⟧)
    (hleft : constantCoeff left = 1)
    (hright : constantCoeff right = 1)
    (hsquare : left ^ 2 = right ^ 2) :
    left = right := by
  have hproduct : (left - right) * (left + right) = 0 := by
    calc
      (left - right) * (left + right) = left ^ 2 - right ^ 2 := by ring
      _ = 0 := sub_eq_zero.mpr hsquare
  rcases mul_eq_zero.mp hproduct with hdifference | hsum
  · exact sub_eq_zero.mp hdifference
  · have hconstant := congrArg constantCoeff hsum
    simp only [map_add, map_zero, hleft, hright] at hconstant
    norm_num at hconstant

/-- The selected weight-`3/2` density transport in the tangent coordinate. -/
noncomputable def densityTransport (v : k⟦X⟧) : k⟦X⟧ :=
  orbitUnit v ^ 3 *
    unitPower (d⁄dX k (orbitCoordinate v)) (-3 / 2 : ℚ)

theorem densityTransport_constantCoeff (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    constantCoeff (densityTransport v) = 1 := by
  simp [densityTransport, orbitUnit_constantCoeff v hv,
    unitPower_constantCoeff _
      (orbitCoordinate_derivative_constantCoeff v hv)]

/-- The square-free formal tensor-density orbit equation. -/
theorem simpleZero_densityTransport (v : k⟦X⟧)
    (hv : constantCoeff v = 1) :
    densityTransport v = v := by
  let derivativeCoordinate := d⁄dX k (orbitCoordinate v)
  let inverseDensityRoot := unitPower derivativeCoordinate (-3 / 2 : ℚ)
  have hderivativeConstant : constantCoeff derivativeCoordinate = 1 :=
    orbitCoordinate_derivative_constantCoeff v hv
  have hinverseRoot :
      inverseDensityRoot ^ 2 * derivativeCoordinate ^ 3 = 1 :=
    unitPower_neg_three_halves_square derivativeCoordinate
      hderivativeConstant
  have hderivative :
      derivativeCoordinate = orbitUnit v ^ 2 *
        unitPower v (-2 / 3 : ℚ) := by
    dsimp [derivativeCoordinate]
    rw [derivative_orbitCoordinate]
    rw [show weightedEuler (orbitUnit v) =
        unitPower v (-2 / 3 : ℚ) from weightedEuler_solve _]
  have hsourceRoot := unitPower_neg_two_thirds_cube v hv
  have hsourceRootNonzero :
      (unitPower v (-2 / 3 : ℚ)) ^ 3 ≠ 0 := by
    intro hzero
    have hconstant := congrArg constantCoeff hzero
    simp [unitPower_constantCoeff v hv] at hconstant
  have hsquares : densityTransport v ^ 2 = v ^ 2 := by
    have hcancel :
        (inverseDensityRoot ^ 2 * orbitUnit v ^ 6) *
            (unitPower v (-2 / 3 : ℚ)) ^ 3 =
          v ^ 2 * (unitPower v (-2 / 3 : ℚ)) ^ 3 := by
      calc
        (inverseDensityRoot ^ 2 * orbitUnit v ^ 6) *
              (unitPower v (-2 / 3 : ℚ)) ^ 3 =
            inverseDensityRoot ^ 2 * derivativeCoordinate ^ 3 := by
          rw [hderivative]
          ring
        _ = 1 := hinverseRoot
        _ = v ^ 2 * (unitPower v (-2 / 3 : ℚ)) ^ 3 := by
          rw [mul_comm]
          exact hsourceRoot.symm
    have hunitSquare :
        inverseDensityRoot ^ 2 * orbitUnit v ^ 6 = v ^ 2 := by
      exact mul_right_cancel₀ hsourceRootNonzero hcancel
    rw [densityTransport]
    change (orbitUnit v ^ 3 * inverseDensityRoot) ^ 2 = v ^ 2
    calc
      (orbitUnit v ^ 3 * inverseDensityRoot) ^ 2 =
          inverseDensityRoot ^ 2 * orbitUnit v ^ 6 := by ring
      _ = v ^ 2 := hunitSquare
  exact normalizedUnit_eq_of_sq_eq (densityTransport v) v
    (densityTransport_constantCoeff v hv) hv hsquares

/-- Unit obtained after removing and normalizing the simple zero of a
formal density. -/
noncomputable def simpleZeroUnit (residual : k⟦X⟧) : k⟦X⟧ :=
  C (coeff 1 residual)⁻¹ *
    PowerSeries.mk fun n => coeff (n + 1) residual

omit [CharZero k] in
theorem simpleZeroUnit_constantCoeff (residual : k⟦X⟧)
    (hlinear : coeff 1 residual ≠ 0) :
    constantCoeff (simpleZeroUnit residual) = 1 := by
  simp [simpleZeroUnit, hlinear]

omit [CharZero k] in
theorem simpleZero_factorization (residual : k⟦X⟧)
    (hconstant : constantCoeff residual = 0)
    (hlinear : coeff 1 residual ≠ 0) :
    C (coeff 1 residual) * (X * simpleZeroUnit residual) = residual := by
  have hsplit := PowerSeries.eq_X_mul_shift_add_const residual
  rw [hconstant, map_zero, add_zero] at hsplit
  rw [simpleZeroUnit]
  calc
    C (coeff 1 residual) *
          (X * (C (coeff 1 residual)⁻¹ *
            PowerSeries.mk fun n => coeff (n + 1) residual)) =
        (C (coeff 1 residual) * C (coeff 1 residual)⁻¹) *
          (X * PowerSeries.mk fun n => coeff (n + 1) residual) := by
      ring
    _ = X * PowerSeries.mk fun n => coeff (n + 1) residual := by
      rw [← map_mul, mul_inv_cancel₀ hlinear, map_one, one_mul]
    _ = residual := hsplit.symm

/-- Every formal density with a simple zero lies in the tangent formal
diffeomorphism orbit of its linear monomial. -/
theorem simpleZero_densityOrbit (residual : k⟦X⟧)
    (hconstant : constantCoeff residual = 0)
    (hlinear : coeff 1 residual ≠ 0) :
    residual =
      C (coeff 1 residual) * orbitCoordinate (simpleZeroUnit residual) *
        unitPower
          (d⁄dX k (orbitCoordinate (simpleZeroUnit residual)))
          (-3 / 2 : ℚ) := by
  have hunit := simpleZeroUnit_constantCoeff residual hlinear
  have htransport := simpleZero_densityTransport
    (simpleZeroUnit residual) hunit
  calc
    residual = C (coeff 1 residual) *
        (X * simpleZeroUnit residual) :=
      (simpleZero_factorization residual hconstant hlinear).symm
    _ = C (coeff 1 residual) *
        (X * densityTransport (simpleZeroUnit residual)) := by
      rw [htransport]
    _ = C (coeff 1 residual) *
        orbitCoordinate (simpleZeroUnit residual) *
        unitPower
          (d⁄dX k (orbitCoordinate (simpleZeroUnit residual)))
          (-3 / 2 : ℚ) := by
      rw [densityTransport, orbitCoordinate]
      ring

/-- Fully normalized transitivity certificate for simple-zero formal
weight-`3/2` densities. -/
theorem simple_zero_density_orbit_transitivity_terminal_certificate :
    ∀ residual : k⟦X⟧,
      constantCoeff residual = 0 →
      coeff 1 residual ≠ 0 →
      constantCoeff (simpleZeroUnit residual) = 1 ∧
      constantCoeff (orbitCoordinate (simpleZeroUnit residual)) = 0 ∧
      coeff 1 (orbitCoordinate (simpleZeroUnit residual)) = 1 ∧
      residual =
        C (coeff 1 residual) *
          orbitCoordinate (simpleZeroUnit residual) *
          unitPower
            (d⁄dX k (orbitCoordinate (simpleZeroUnit residual)))
            (-3 / 2 : ℚ) := by
  intro residual hconstant hlinear
  have hunit := simpleZeroUnit_constantCoeff residual hlinear
  exact ⟨hunit,
    orbitCoordinate_constantCoeff _,
    orbitCoordinate_linearCoeff _ hunit,
    simpleZero_densityOrbit residual hconstant hlinear⟩

/-- Constructor certificate for the all-order simple-zero normal form. -/
theorem simple_zero_tensor_density_normal_form_terminal_certificate :
    ∀ v : k⟦X⟧, constantCoeff v = 1 →
      constantCoeff (orbitUnit v) = 1 ∧
      weightedEuler (orbitUnit v) = unitPower v (-2 / 3 : ℚ) ∧
      constantCoeff (orbitCoordinate v) = 0 ∧
      coeff 1 (orbitCoordinate v) = 1 ∧
      (X * v) ^ 2 * (d⁄dX k (orbitCoordinate v)) ^ 3 =
        orbitCoordinate v ^ 2 ∧
      densityTransport v = v := by
  intro v hv
  exact ⟨orbitUnit_constantCoeff v hv, weightedEuler_solve _,
    orbitCoordinate_constantCoeff v,
    orbitCoordinate_linearCoeff v hv,
    simpleZero_squaredDensityOrbit v hv,
    simpleZero_densityTransport v hv⟩

end

end ZtareProofs.FormalSimpleZeroTensorDensityNormalForm
