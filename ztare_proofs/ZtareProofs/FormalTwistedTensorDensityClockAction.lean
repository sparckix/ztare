import Mathlib.Tactic
import Mathlib.Algebra.Group.MinimalAxioms
import ZtareProofs.FormalSemidirectFactorizationOrbit
import ZtareProofs.FormalTwistedSimpleZeroTensorDensityNormalForm

/-!
# Twisted tensor-density action and clock

For a row-indexed residual `K = c X v`, with `v(0)=1`, the corrected finite
action is carried by the normalized unit

`T_phi(v) = (v subst phi) * (phi')^(-3/2)`.

This file packages fixed-origin, tangent substitutions and normalized units
as separate identities.  It proves the identity and composition laws in the
exact `PowerSeries.subst` order, then proves that

`S(v) = integralZero (v^(-2/3))`

intertwines the twisted action with ordinary substitution.  Fractional powers
are the algebraic normalized powers already owned by
`FormalSimpleZeroTensorDensityNormalForm`; no analytic branch is assumed.
-/

namespace ZtareProofs.FormalTwistedTensorDensityClockAction

open PowerSeries
open FormalPowerSeriesLinearODE
open ZtareProofs.FormalSimpleZeroTensorDensityNormalForm

noncomputable section

variable {k : Type*} [Field k] [CharZero k]

/-- A normalized coefficient unit. -/
@[ext]
structure NormalizedUnit where
  series : k⟦X⟧
  constantCoeff_one : constantCoeff series = 1

/-- A fixed-origin tangent formal endpoint. -/
@[ext]
structure TangentEndpoint where
  series : k⟦X⟧
  constantCoeff_zero : constantCoeff series = 0
  linearCoeff_one : coeff 1 series = 1

/-- Fixed-origin endpoints are admissible substitution arguments. -/
theorem TangentEndpoint.hasSubst (endpoint : TangentEndpoint (k := k)) :
    HasSubst endpoint.series :=
  HasSubst.of_constantCoeff_zero' endpoint.constantCoeff_zero

/-- The constant coefficient of a derivative is the linear coefficient. -/
theorem constantCoeff_derivative (series : k⟦X⟧) :
    constantCoeff (d⁄dX k series) = coeff 1 series := by
  rw [← coeff_zero_eq_constantCoeff, coeff_derivative]
  simp

/-- Substitution into a fixed-origin endpoint preserves the outer constant
coefficient. -/
theorem constantCoeff_subst_of_zero
    (inner outer : k⟦X⟧) (hinner : constantCoeff inner = 0) :
    constantCoeff (PowerSeries.subst inner outer) = constantCoeff outer := by
  let scalar := constantCoeff outer
  have houterZero : constantCoeff (outer - C scalar) = 0 := by
    simp [scalar]
  have hzero := PowerSeries.constantCoeff_subst_eq_zero
    hinner (outer - C scalar) houterZero
  have hhas : HasSubst inner :=
    HasSubst.of_constantCoeff_zero' hinner
  rw [PowerSeries.subst_sub hhas] at hzero
  have heq := sub_eq_zero.mp hzero
  simpa [scalar] using heq

/-- The identity tangent endpoint. -/
def TangentEndpoint.identity : TangentEndpoint (k := k) where
  series := X
  constantCoeff_zero := by simp
  linearCoeff_one := by simp

/-- Composition is named by geometry: `outer.after inner` has series
`outer(inner(X)) = subst inner outer`. -/
def TangentEndpoint.after
    (outer inner : TangentEndpoint (k := k)) : TangentEndpoint (k := k) where
  series := PowerSeries.subst inner.series outer.series
  constantCoeff_zero := by
    rw [constantCoeff_subst_of_zero inner.series outer.series
      inner.constantCoeff_zero]
    exact outer.constantCoeff_zero
  linearCoeff_one := by
    have hchain := PowerSeries.derivative_subst k inner.hasSubst
      (f := outer.series)
    have hconstant := congrArg constantCoeff hchain
    rw [map_mul,
      constantCoeff_subst_of_zero inner.series
        (d⁄dX k outer.series) inner.constantCoeff_zero] at hconstant
    simpa [constantCoeff_derivative, outer.linearCoeff_one,
      inner.linearCoeff_one] using hconstant

/-- The derivative of a tangent endpoint is a normalized unit. -/
def TangentEndpoint.derivativeUnit
    (endpoint : TangentEndpoint (k := k)) : NormalizedUnit (k := k) where
  series := d⁄dX k endpoint.series
  constantCoeff_one := by
    rw [constantCoeff_derivative]
    exact endpoint.linearCoeff_one

/-- Fractional powers commute with a fixed-origin formal substitution. -/
theorem unitPower_subst
    (endpoint : TangentEndpoint (k := k))
    (unit : NormalizedUnit (k := k)) (exponent : ℚ) :
    unitPower (PowerSeries.subst endpoint.series unit.series) exponent =
      PowerSeries.subst endpoint.series (unitPower unit.series exponent) := by
  rw [unitPower, unitPower]
  rw [PowerSeries.subst_comp_subst_apply
    (unitOffset_hasSubst unit.series unit.constantCoeff_one)
    endpoint.hasSubst]
  congr 1
  rw [PowerSeries.subst_sub endpoint.hasSubst]
  have hone : PowerSeries.subst endpoint.series (1 : k⟦X⟧) = 1 := by
    rw [← PowerSeries.coe_substAlgHom endpoint.hasSubst, map_one]
  rw [hone]

/-- Normalized units are determined by their cubes. -/
theorem normalizedUnit_eq_of_cube_eq
    (left right : k⟦X⟧)
    (hleft : constantCoeff left = 1)
    (hright : constantCoeff right = 1)
    (hcube : left ^ 3 = right ^ 3) :
    left = right := by
  have hproduct :
      (left - right) * (left ^ 2 + left * right + right ^ 2) = 0 := by
    calc
      (left - right) * (left ^ 2 + left * right + right ^ 2) =
          left ^ 3 - right ^ 3 := by ring
      _ = 0 := sub_eq_zero.mpr hcube
  rcases mul_eq_zero.mp hproduct with hdifference | hsum
  · exact sub_eq_zero.mp hdifference
  · have hconstant := congrArg constantCoeff hsum
    simp only [map_add, map_mul, map_pow, map_zero, hleft, hright] at hconstant
    norm_num at hconstant

/-- The normalized `(-2/3)` power respects multiplication. -/
theorem unitPower_neg_two_thirds_mul
    (left right : k⟦X⟧)
    (hleft : constantCoeff left = 1)
    (hright : constantCoeff right = 1) :
    unitPower (left * right) (-2 / 3 : ℚ) =
      unitPower left (-2 / 3 : ℚ) *
        unitPower right (-2 / 3 : ℚ) := by
  have hproductConstant : constantCoeff (left * right) = 1 := by
    simp [hleft, hright]
  let productRoot := unitPower (left * right) (-2 / 3 : ℚ)
  let splitRoot := unitPower left (-2 / 3 : ℚ) *
    unitPower right (-2 / 3 : ℚ)
  have hproductIdentity :=
    unitPower_neg_two_thirds_cube (left * right) hproductConstant
  have hleftIdentity := unitPower_neg_two_thirds_cube left hleft
  have hrightIdentity := unitPower_neg_two_thirds_cube right hright
  have hsplitIdentity : splitRoot ^ 3 * (left * right) ^ 2 = 1 := by
    dsimp only [splitRoot]
    calc
      (unitPower left (-2 / 3 : ℚ) *
            unitPower right (-2 / 3 : ℚ)) ^ 3 *
          (left * right) ^ 2 =
        ((unitPower left (-2 / 3 : ℚ)) ^ 3 * left ^ 2) *
          ((unitPower right (-2 / 3 : ℚ)) ^ 3 * right ^ 2) := by ring
      _ = 1 := by rw [hleftIdentity, hrightIdentity, one_mul]
  have hfactorNonzero : (left * right) ^ 2 ≠ 0 := by
    intro hzero
    have hconstant := congrArg constantCoeff hzero
    simp [hleft, hright] at hconstant
  have hcubes : productRoot ^ 3 = splitRoot ^ 3 := by
    apply mul_right_cancel₀ hfactorNonzero
    exact hproductIdentity.trans hsplitIdentity.symm
  apply normalizedUnit_eq_of_cube_eq productRoot splitRoot
  · exact unitPower_constantCoeff (left * right) hproductConstant _
  · simp [splitRoot, unitPower_constantCoeff left hleft,
      unitPower_constantCoeff right hright]
  · exact hcubes

/-- The normalized `(-3/2)` power respects multiplication. -/
theorem unitPower_neg_three_halves_mul
    (left right : k⟦X⟧)
    (hleft : constantCoeff left = 1)
    (hright : constantCoeff right = 1) :
    unitPower (left * right) (-3 / 2 : ℚ) =
      unitPower left (-3 / 2 : ℚ) *
        unitPower right (-3 / 2 : ℚ) := by
  have hproductConstant : constantCoeff (left * right) = 1 := by
    simp [hleft, hright]
  let productRoot := unitPower (left * right) (-3 / 2 : ℚ)
  let splitRoot := unitPower left (-3 / 2 : ℚ) *
    unitPower right (-3 / 2 : ℚ)
  have hproductIdentity :=
    unitPower_neg_three_halves_square (left * right) hproductConstant
  have hleftIdentity := unitPower_neg_three_halves_square left hleft
  have hrightIdentity := unitPower_neg_three_halves_square right hright
  have hsplitIdentity : splitRoot ^ 2 * (left * right) ^ 3 = 1 := by
    dsimp only [splitRoot]
    calc
      (unitPower left (-3 / 2 : ℚ) *
            unitPower right (-3 / 2 : ℚ)) ^ 2 *
          (left * right) ^ 3 =
        ((unitPower left (-3 / 2 : ℚ)) ^ 2 * left ^ 3) *
          ((unitPower right (-3 / 2 : ℚ)) ^ 2 * right ^ 3) := by ring
      _ = 1 := by rw [hleftIdentity, hrightIdentity, one_mul]
  have hfactorNonzero : (left * right) ^ 3 ≠ 0 := by
    intro hzero
    have hconstant := congrArg constantCoeff hzero
    simp [hleft, hright] at hconstant
  have hsquares : productRoot ^ 2 = splitRoot ^ 2 := by
    apply mul_right_cancel₀ hfactorNonzero
    exact hproductIdentity.trans hsplitIdentity.symm
  apply normalizedUnit_eq_of_sq_eq productRoot splitRoot
  · exact unitPower_constantCoeff (left * right) hproductConstant _
  · simp [splitRoot, unitPower_constantCoeff left hleft,
      unitPower_constantCoeff right hright]
  · exact hsquares

/-- Applying `(-2/3)` to the normalized `(-3/2)` density factor recovers
the original unit. -/
theorem unitPower_neg_two_thirds_neg_three_halves
    (unit : NormalizedUnit (k := k)) :
    unitPower (unitPower unit.series (-3 / 2 : ℚ)) (-2 / 3 : ℚ) =
      unit.series := by
  let densityRoot := unitPower unit.series (-3 / 2 : ℚ)
  let recovered := unitPower densityRoot (-2 / 3 : ℚ)
  have hdensityConstant : constantCoeff densityRoot = 1 :=
    unitPower_constantCoeff unit.series unit.constantCoeff_one _
  have hrecoveredIdentity :=
    unitPower_neg_two_thirds_cube densityRoot hdensityConstant
  have hdensityIdentity :=
    unitPower_neg_three_halves_square unit.series unit.constantCoeff_one
  have hdensityNonzero : densityRoot ^ 2 ≠ 0 := by
    intro hzero
    have hconstant := congrArg constantCoeff hzero
    simp [hdensityConstant] at hconstant
  have hcubes : recovered ^ 3 = unit.series ^ 3 := by
    apply mul_right_cancel₀ hdensityNonzero
    calc
      recovered ^ 3 * densityRoot ^ 2 = 1 := hrecoveredIdentity
      _ = unit.series ^ 3 * densityRoot ^ 2 := by
        calc
          1 = densityRoot ^ 2 * unit.series ^ 3 := by
            exact hdensityIdentity.symm
          _ = unit.series ^ 3 * densityRoot ^ 2 := by ring
  apply normalizedUnit_eq_of_cube_eq recovered unit.series
  · exact unitPower_constantCoeff densityRoot hdensityConstant _
  · exact unit.constantCoeff_one
  · exact hcubes

/-- Corrected row-indexed tensor-density transport on normalized units. -/
def twistedAction
    (endpoint : TangentEndpoint (k := k))
    (unit : NormalizedUnit (k := k)) : NormalizedUnit (k := k) where
  series := PowerSeries.subst endpoint.series unit.series *
    unitPower (d⁄dX k endpoint.series) (-3 / 2 : ℚ)
  constantCoeff_one := by
    rw [map_mul,
      constantCoeff_subst_of_zero endpoint.series unit.series
        endpoint.constantCoeff_zero]
    rw [unit.constantCoeff_one,
      unitPower_constantCoeff (d⁄dX k endpoint.series)
        endpoint.derivativeUnit.constantCoeff_one]
    exact one_mul 1

/-- The identity endpoint acts trivially. -/
theorem twistedAction_identity (unit : NormalizedUnit (k := k)) :
    twistedAction TangentEndpoint.identity unit = unit := by
  apply NormalizedUnit.ext
  simp only [twistedAction, TangentEndpoint.identity, X_subst,
    PowerSeries.derivative_X]
  have hroot := unitPower_neg_three_halves_square
    (1 : k⟦X⟧) (by simp)
  have hrootOne : unitPower (1 : k⟦X⟧) (-3 / 2 : ℚ) = 1 := by
    apply normalizedUnit_eq_of_sq_eq _ 1
    · exact unitPower_constantCoeff (1 : k⟦X⟧) (by simp) _
    · simp
    · simpa using hroot
  rw [hrootOne, mul_one]

/-- Exact action composition.  `outer.after inner` is
`outer(inner(X))`, so `inner` acts second on units. -/
theorem twistedAction_compose
    (outer inner : TangentEndpoint (k := k))
    (unit : NormalizedUnit (k := k)) :
    twistedAction inner (twistedAction outer unit) =
      twistedAction (outer.after inner) unit := by
  apply NormalizedUnit.ext
  change PowerSeries.subst inner.series
        (PowerSeries.subst outer.series unit.series *
          unitPower (d⁄dX k outer.series) (-3 / 2 : ℚ)) *
      unitPower (d⁄dX k inner.series) (-3 / 2 : ℚ) =
    PowerSeries.subst (PowerSeries.subst inner.series outer.series)
        unit.series *
      unitPower
        (d⁄dX k (PowerSeries.subst inner.series outer.series))
        (-3 / 2 : ℚ)
  rw [PowerSeries.subst_mul inner.hasSubst]
  rw [PowerSeries.subst_comp_subst_apply outer.hasSubst inner.hasSubst]
  have hpowerSubst :=
    unitPower_subst inner outer.derivativeUnit (-3 / 2 : ℚ)
  change unitPower
      (PowerSeries.subst inner.series (d⁄dX k outer.series))
        (-3 / 2 : ℚ) =
    PowerSeries.subst inner.series
      (unitPower (d⁄dX k outer.series) (-3 / 2 : ℚ)) at hpowerSubst
  rw [← hpowerSubst]
  rw [PowerSeries.derivative_subst k inner.hasSubst]
  rw [unitPower_neg_three_halves_mul
    (PowerSeries.subst inner.series (d⁄dX k outer.series))
    (d⁄dX k inner.series)]
  · ring
  · rw [constantCoeff_subst_of_zero inner.series
      (d⁄dX k outer.series) inner.constantCoeff_zero]
    exact outer.derivativeUnit.constantCoeff_one
  · exact inner.derivativeUnit.constantCoeff_one

/-- Normalized density clock. -/
def densityClock (unit : NormalizedUnit (k := k)) : k⟦X⟧ :=
  integralZero (unitPower unit.series (-2 / 3 : ℚ))

@[simp]
theorem densityClock_constantCoeff (unit : NormalizedUnit (k := k)) :
    constantCoeff (densityClock unit) = 0 := by
  exact constantCoeff_integralZero _

@[simp]
theorem derivative_densityClock (unit : NormalizedUnit (k := k)) :
    d⁄dX k (densityClock unit) =
      unitPower unit.series (-2 / 3 : ℚ) := by
  exact derivative_integralZero _

/-- Taking the `(-2/3)` clock derivative of a transported density produces
the ordinary chain-rule factor. -/
theorem unitPower_twistedAction
    (endpoint : TangentEndpoint (k := k))
    (unit : NormalizedUnit (k := k)) :
    unitPower (twistedAction endpoint unit).series (-2 / 3 : ℚ) =
      PowerSeries.subst endpoint.series
          (unitPower unit.series (-2 / 3 : ℚ)) *
        d⁄dX k endpoint.series := by
  change unitPower
      (PowerSeries.subst endpoint.series unit.series *
        unitPower (d⁄dX k endpoint.series) (-3 / 2 : ℚ))
      (-2 / 3 : ℚ) = _
  rw [unitPower_neg_two_thirds_mul]
  · rw [unitPower_subst endpoint unit]
    have hrecover := unitPower_neg_two_thirds_neg_three_halves
      endpoint.derivativeUnit
    change unitPower
        (unitPower (d⁄dX k endpoint.series) (-3 / 2 : ℚ))
          (-2 / 3 : ℚ) = d⁄dX k endpoint.series at hrecover
    rw [hrecover]
  · rw [constantCoeff_subst_of_zero endpoint.series unit.series
      endpoint.constantCoeff_zero]
    exact unit.constantCoeff_one
  · exact unitPower_constantCoeff _
      endpoint.derivativeUnit.constantCoeff_one _

/-- Equal derivatives and equal constants determine a formal series. -/
theorem eq_of_derivative_eq_of_constantCoeff_eq
    (left right : k⟦X⟧)
    (hderivative : d⁄dX k left = d⁄dX k right)
    (hconstant : constantCoeff left = constantCoeff right) :
    left = right := by
  apply PowerSeries.ext
  intro n
  cases n with
  | zero =>
      simpa only [coeff_zero_eq_constantCoeff] using hconstant
  | succ n =>
      have hcoefficient := congrArg (coeff n) hderivative
      simp only [coeff_derivative] at hcoefficient
      have hcast : (((n + 1 : ℕ) : k)) ≠ 0 := by
        exact_mod_cast Nat.succ_ne_zero n
      apply mul_right_cancel₀ hcast
      simpa [Nat.cast_add, Nat.cast_one, mul_comm] using hcoefficient

/-- Exact normalized clock equivariance in the declared substitution
orientation. -/
theorem densityClock_twistedAction
    (endpoint : TangentEndpoint (k := k))
    (unit : NormalizedUnit (k := k)) :
    densityClock (twistedAction endpoint unit) =
      PowerSeries.subst endpoint.series (densityClock unit) := by
  apply eq_of_derivative_eq_of_constantCoeff_eq
  · rw [derivative_densityClock, unitPower_twistedAction]
    rw [PowerSeries.derivative_subst k endpoint.hasSubst]
    rw [derivative_densityClock]
  · rw [densityClock_constantCoeff]
    exact (PowerSeries.constantCoeff_subst_eq_zero
      endpoint.constantCoeff_zero (densityClock unit)
      (densityClock_constantCoeff unit)).symm

/-- A quadratic and a cubic tangent endpoint do not commute. -/
theorem tangent_quadratic_cubic_not_commute :
    PowerSeries.subst ((X : k⟦X⟧) + X ^ 3)
        ((X : k⟦X⟧) + X ^ 2) ≠
      PowerSeries.subst ((X : k⟦X⟧) + X ^ 2)
        ((X : k⟦X⟧) + X ^ 3) := by
  have hcubic : HasSubst ((X : k⟦X⟧) + X ^ 3) :=
    HasSubst.of_constantCoeff_zero' (by simp)
  have hquadratic : HasSubst ((X : k⟦X⟧) + X ^ 2) :=
    HasSubst.of_constantCoeff_zero' (by simp)
  intro hequal
  rw [PowerSeries.subst_add hcubic, PowerSeries.subst_X hcubic,
    PowerSeries.subst_pow hcubic,
    PowerSeries.subst_add hquadratic,
    PowerSeries.subst_X hquadratic,
    PowerSeries.subst_pow hquadratic] at hequal
  simp only [PowerSeries.subst_X hcubic,
    PowerSeries.subst_X hquadratic] at hequal
  ring_nf at hequal
  have htwo : (2 : k⟦X⟧) = C (2 : k) := by
    exact (map_natCast (C : k →+* k⟦X⟧) 2).symm
  have hthree : (3 : k⟦X⟧) = C (3 : k) := by
    exact (map_natCast (C : k →+* k⟦X⟧) 3).symm
  rw [htwo, hthree] at hequal
  have hcoefficient := congrArg (coeff 4) hequal
  norm_num [PowerSeries.coeff_X_pow, PowerSeries.coeff_mul_C]
    at hcoefficient

/-! ## Governing groups and the additive density action -/

/-- Endpoint multiplication follows composition as seen by a right action:
`inner * outer` has series `outer(inner(X))`. -/
def TangentEndpoint.multiply
    (inner outer : TangentEndpoint (k := k)) : TangentEndpoint (k := k) :=
  outer.after inner

/-- The compositional inverse of a tangent endpoint. -/
noncomputable def TangentEndpoint.compositionalInverse
    (endpoint : TangentEndpoint (k := k)) : TangentEndpoint (k := k) := by
  letI : Invertible (coeff 1 endpoint.series) :=
    invertibleOfNonzero (by simpa [endpoint.linearCoeff_one])
  exact {
    series := endpoint.series.substInv
    constantCoeff_zero := PowerSeries.constantCoeff_substInv endpoint.series
    linearCoeff_one := by
      rw [PowerSeries.coeff_one_substInv, invOf_eq_inv,
        endpoint.linearCoeff_one, inv_one]
  }

noncomputable instance : One (TangentEndpoint (k := k)) :=
  ⟨TangentEndpoint.identity⟩

noncomputable instance : Mul (TangentEndpoint (k := k)) :=
  ⟨TangentEndpoint.multiply⟩

noncomputable instance : Inv (TangentEndpoint (k := k)) :=
  ⟨TangentEndpoint.compositionalInverse⟩

theorem TangentEndpoint.multiply_assoc
    (first second third : TangentEndpoint (k := k)) :
    (first * second) * third = first * (second * third) := by
  apply TangentEndpoint.ext
  exact (PowerSeries.subst_comp_subst_apply
    second.hasSubst first.hasSubst third.series).symm

theorem TangentEndpoint.one_multiply
    (endpoint : TangentEndpoint (k := k)) :
    1 * endpoint = endpoint := by
  apply TangentEndpoint.ext
  exact PowerSeries.X_subst endpoint.series

theorem TangentEndpoint.inverse_multiply
    (endpoint : TangentEndpoint (k := k)) :
    endpoint⁻¹ * endpoint = 1 := by
  apply TangentEndpoint.ext
  letI : Invertible (coeff 1 endpoint.series) :=
    invertibleOfNonzero (by simpa [endpoint.linearCoeff_one])
  exact PowerSeries.subst_substInv_right
    endpoint.series endpoint.constantCoeff_zero

noncomputable instance : Group (TangentEndpoint (k := k)) :=
  Group.ofLeftAxioms TangentEndpoint.multiply_assoc
    TangentEndpoint.one_multiply TangentEndpoint.inverse_multiply

@[simp]
theorem TangentEndpoint.multiply_series
    (inner outer : TangentEndpoint (k := k)) :
    (inner * outer).series =
      PowerSeries.subst inner.series outer.series :=
  rfl

/-- Linear tensor-density transport before restricting to the normalized
unit slice.  This is the additive normal group action in the semidirect
factorization. -/
def densityAction
    (endpoint : TangentEndpoint (k := k)) (density : k⟦X⟧) : k⟦X⟧ :=
  PowerSeries.subst endpoint.series density *
    unitPower (d⁄dX k endpoint.series) (-3 / 2 : ℚ)

theorem densityAction_identity (density : k⟦X⟧) :
    densityAction (1 : TangentEndpoint (k := k)) density = density := by
  change PowerSeries.subst X density *
      unitPower (d⁄dX k X) (-3 / 2 : ℚ) = density
  have hroot := unitPower_neg_three_halves_square
    (1 : k⟦X⟧) (by simp)
  have hrootOne : unitPower (1 : k⟦X⟧) (-3 / 2 : ℚ) = 1 := by
    apply normalizedUnit_eq_of_sq_eq _ 1
    · exact unitPower_constantCoeff (1 : k⟦X⟧) (by simp) _
    · simp
    · simpa using hroot
  simp [hrootOne]

/-- Composition of the linear density transport in the endpoint-group
orientation. -/
theorem densityAction_compose
    (outer inner : TangentEndpoint (k := k)) (density : k⟦X⟧) :
    densityAction inner (densityAction outer density) =
      densityAction (inner * outer) density := by
  change PowerSeries.subst inner.series
        (PowerSeries.subst outer.series density *
          unitPower (d⁄dX k outer.series) (-3 / 2 : ℚ)) *
      unitPower (d⁄dX k inner.series) (-3 / 2 : ℚ) =
    PowerSeries.subst (PowerSeries.subst inner.series outer.series)
        density *
      unitPower
        (d⁄dX k (PowerSeries.subst inner.series outer.series))
        (-3 / 2 : ℚ)
  rw [PowerSeries.subst_mul inner.hasSubst]
  rw [PowerSeries.subst_comp_subst_apply outer.hasSubst inner.hasSubst]
  have hpowerSubst :=
    unitPower_subst inner outer.derivativeUnit (-3 / 2 : ℚ)
  change unitPower
      (PowerSeries.subst inner.series (d⁄dX k outer.series))
        (-3 / 2 : ℚ) =
    PowerSeries.subst inner.series
      (unitPower (d⁄dX k outer.series) (-3 / 2 : ℚ)) at hpowerSubst
  rw [← hpowerSubst]
  rw [PowerSeries.derivative_subst k inner.hasSubst]
  rw [unitPower_neg_three_halves_mul
    (PowerSeries.subst inner.series (d⁄dX k outer.series))
    (d⁄dX k inner.series)]
  · ring
  · rw [constantCoeff_subst_of_zero inner.series
      (d⁄dX k outer.series) inner.constantCoeff_zero]
    exact outer.derivativeUnit.constantCoeff_one
  · exact inner.derivativeUnit.constantCoeff_one

theorem densityAction_add
    (endpoint : TangentEndpoint (k := k)) (left right : k⟦X⟧) :
    densityAction endpoint (left + right) =
      densityAction endpoint left + densityAction endpoint right := by
  rw [densityAction, PowerSeries.subst_add endpoint.hasSubst]
  simp only [densityAction]
  ring

/-- Each tangent endpoint acts by an additive automorphism of all formal
tensor densities. -/
noncomputable def densityAddEquiv
    (endpoint : TangentEndpoint (k := k)) : k⟦X⟧ ≃+ k⟦X⟧ where
  toFun := densityAction endpoint
  invFun := densityAction endpoint⁻¹
  left_inv density := by
    rw [densityAction_compose]
    rw [inv_mul_cancel endpoint]
    exact densityAction_identity density
  right_inv density := by
    rw [densityAction_compose]
    rw [mul_inv_cancel endpoint]
    exact densityAction_identity density
  map_add' := densityAction_add endpoint

/-- The exact density action as a homomorphism into additive automorphisms. -/
noncomputable def densityAddAction :
    TangentEndpoint (k := k) →* AddAut k⟦X⟧ where
  toFun := densityAddEquiv
  map_one' := by
    apply DFunLike.ext _ _
    intro density
    exact densityAction_identity density
  map_mul' inner outer := by
    apply DFunLike.ext _ _
    intro density
    exact (densityAction_compose outer inner density).symm

/-- The same action in the multiplicative wrapper required by Mathlib's
semidirect-product constructor.  Multiplication in the wrapper is addition
of tensor densities. -/
noncomputable def densityMulAction :
    TangentEndpoint (k := k) →*
      MulAut (Multiplicative k⟦X⟧) :=
  (MulAutMultiplicative k⟦X⟧).symm.toMonoidHom.comp densityAddAction

@[simp]
theorem densityMulAction_apply
    (endpoint : TangentEndpoint (k := k)) (density : k⟦X⟧) :
    ((densityMulAction endpoint (Multiplicative.ofAdd density)).toAdd) =
      densityAction endpoint density :=
  rfl

/-- The abstract target-left semidirect equation now yields the exact
twisted normalized-density orbit and its clock equation. -/
theorem targetLeft_factorization_forces_twisted_clock
    (residual sourceModule : NormalizedUnit (k := k))
    (targetActor sourceActor : TangentEndpoint (k := k))
    (factorization :
      (SemidirectProduct.inl
          (Multiplicative.ofAdd residual.series) :
        Multiplicative k⟦X⟧ ⋊[densityMulAction] TangentEndpoint) =
        SemidirectProduct.inr targetActor *
          (⟨Multiplicative.ofAdd sourceModule.series, sourceActor⟩ :
            Multiplicative k⟦X⟧ ⋊[densityMulAction]
              TangentEndpoint)) :
    targetActor = sourceActor⁻¹ ∧
      residual = twistedAction sourceActor⁻¹ sourceModule ∧
      densityClock residual =
        PowerSeries.subst sourceActor⁻¹.series
          (densityClock sourceModule) := by
  have projected :=
    _root_.FormalSemidirectFactorizationOrbit.targetLeft_factorization_forces_inverse_orbit
        densityMulAction
        (Multiplicative.ofAdd residual.series)
        (Multiplicative.ofAdd sourceModule.series)
        targetActor sourceActor factorization
  have horbitSeries : residual.series =
      (twistedAction sourceActor⁻¹ sourceModule).series := by
    have hseries := congrArg Multiplicative.toAdd projected.2
    simpa [densityMulAction_apply, densityAction, twistedAction] using hseries
  have horbit : residual = twistedAction sourceActor⁻¹ sourceModule := by
    apply NormalizedUnit.ext
    exact horbitSeries
  exact ⟨projected.1, horbit, by
    rw [horbit]
    exact densityClock_twistedAction sourceActor⁻¹ sourceModule⟩

/-- The v118 action bridge: the semidirect equation itself supplies the
inverse actor, density orbit, and clock transport. -/
theorem additive_density_semidirect_terminal_certificate :
    ∀ (residual sourceModule : NormalizedUnit (k := k))
      (targetActor sourceActor : TangentEndpoint (k := k)),
      (SemidirectProduct.inl
          (Multiplicative.ofAdd residual.series) :
        Multiplicative k⟦X⟧ ⋊[densityMulAction] TangentEndpoint) =
        SemidirectProduct.inr targetActor *
          (⟨Multiplicative.ofAdd sourceModule.series, sourceActor⟩ :
            Multiplicative k⟦X⟧ ⋊[densityMulAction]
              TangentEndpoint) →
      targetActor = sourceActor⁻¹ ∧
        residual = twistedAction sourceActor⁻¹ sourceModule ∧
        densityClock residual =
          PowerSeries.subst sourceActor⁻¹.series
            (densityClock sourceModule) :=
  targetLeft_factorization_forces_twisted_clock

/-- Aggregated twisted-action and clock certificate. -/
theorem twisted_tensor_density_clock_action_terminal_certificate :
    (∀ unit : NormalizedUnit (k := k),
      twistedAction TangentEndpoint.identity unit = unit) ∧
    (∀ (outer inner : TangentEndpoint (k := k))
        (unit : NormalizedUnit (k := k)),
      twistedAction inner (twistedAction outer unit) =
        twistedAction (outer.after inner) unit) ∧
    (∀ (endpoint : TangentEndpoint (k := k))
        (unit : NormalizedUnit (k := k)),
      densityClock (twistedAction endpoint unit) =
        PowerSeries.subst endpoint.series (densityClock unit)) ∧
    PowerSeries.subst ((X : k⟦X⟧) + X ^ 3)
        ((X : k⟦X⟧) + X ^ 2) ≠
      PowerSeries.subst ((X : k⟦X⟧) + X ^ 2)
        ((X : k⟦X⟧) + X ^ 3) := by
  exact ⟨twistedAction_identity, twistedAction_compose,
    densityClock_twistedAction, tangent_quadratic_cubic_not_commute⟩

end

end ZtareProofs.FormalTwistedTensorDensityClockAction
