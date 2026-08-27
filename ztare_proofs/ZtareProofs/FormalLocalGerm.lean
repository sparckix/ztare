import Mathlib.RingTheory.PowerSeries.Binomial
import Mathlib.RingTheory.PowerSeries.Derivative
import Mathlib.RingTheory.PowerSeries.Expand
import Mathlib.RingTheory.PowerSeries.Inverse
import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.Tactic

/-!
Constructed formal local germs used by AxiomPack adapters.

The definitions in this file use Mathlib's power-series identity.  In
particular, a selected square-root branch includes its constant coefficient;
the polynomial equation alone does not identify a branch.
-/

namespace FormalLocalGerm

open PowerSeries

section GeneralAlgebra

variable {k : Type*} [Field k]

/-- A selected square-root series is unique once its square and nonzero
constant branch are fixed. -/
theorem square_root_eq_of_square_eq
    {left right : k⟦X⟧}
    (hsquare : left ^ 2 = right ^ 2)
    (hconstantSum :
      constantCoeff left + constantCoeff right ≠ 0) :
    left = right := by
  have hfactor : (left - right) * (left + right) = 0 := by
    calc
      (left - right) * (left + right) = left ^ 2 - right ^ 2 := by ring
      _ = 0 := by rw [hsquare]; ring
  have hsum : left + right ≠ 0 := by
    intro hzero
    have := congrArg constantCoeff hzero
    simp only [map_add, map_zero] at this
    exact hconstantSum this
  have hdifference : left - right = 0 :=
    (mul_eq_zero.mp hfactor).resolve_right hsum
  exact sub_eq_zero.mp hdifference

/-- Expansion `X ↦ X^p` preserves inversion when the original constant
coefficient is nonzero. -/
theorem expand_inv (p : ℕ) (hp : p ≠ 0) (series : k⟦X⟧)
    (hconstant : constantCoeff series ≠ 0) :
    PowerSeries.expand p hp series⁻¹ =
      (PowerSeries.expand p hp series)⁻¹ := by
  have hexpandedConstant :
      constantCoeff (PowerSeries.expand p hp series) ≠ 0 := by
    rw [PowerSeries.constantCoeff_expand]
    exact hconstant
  apply (PowerSeries.eq_inv_iff_mul_eq_one hexpandedConstant).mpr
  rw [← map_mul]
  simp [PowerSeries.inv_mul_cancel series hconstant]

/-- Coefficient maps between fields preserve the power-series inverse of a
series with nonzero constant coefficient. -/
theorem map_inv
    {K : Type*} [Field K] (hom : k →+* K) (series : k⟦X⟧)
    (hconstant : constantCoeff series ≠ 0) :
    PowerSeries.map hom series⁻¹ = (PowerSeries.map hom series)⁻¹ := by
  have hmappedConstant :
      constantCoeff (PowerSeries.map hom series) ≠ 0 := by
    rw [← coeff_zero_eq_constantCoeff, PowerSeries.coeff_map]
    simpa using (hom.injective.ne_iff).mpr hconstant
  apply (PowerSeries.eq_inv_iff_mul_eq_one hmappedConstant).mpr
  rw [← map_mul]
  simp [PowerSeries.inv_mul_cancel series hconstant]

/-- Coefficient extension commutes with the formal power-series derivative. -/
theorem map_derivative
    {K : Type*} [Field K] (hom : k →+* K) (series : k⟦X⟧) :
    PowerSeries.map hom (d⁄dX k series) =
      d⁄dX K (PowerSeries.map hom series) := by
  ext n
  simp [PowerSeries.coeff_derivative, PowerSeries.coeff_map]

end GeneralAlgebra

/-- The selected quadratic square-root branch
`root * (1 + ratio*X^2)^(1/2)`, constructed from Mathlib's binomial
series.  The parameter `root` records the branch identity. -/
noncomputable def selectedQuadraticRoot (root ratio : ℝ) : ℝ⟦X⟧ :=
  C root *
  PowerSeries.expand 2 (by norm_num)
    (PowerSeries.rescale ratio
      (binomialSeries ℝ (1 / 2 : ℝ)))

theorem half_binomial_square :
    (binomialSeries ℝ (1 / 2 : ℝ)) ^ 2 =
      (1 + X : ℝ⟦X⟧) := by
  calc
    (binomialSeries ℝ (1 / 2 : ℝ)) ^ 2 =
        binomialSeries ℝ (1 / 2 : ℝ) *
          binomialSeries ℝ (1 / 2 : ℝ) := by ring
    _ = binomialSeries ℝ ((1 / 2 : ℝ) + 1 / 2) := by
      rw [binomialSeries_add]
    _ = binomialSeries ℝ (1 : ℝ) := by norm_num
    _ = (1 + X : ℝ⟦X⟧) := by
      simpa using (binomialSeries_nat (A := ℝ) (R := ℝ) 1)

theorem selectedQuadraticRoot_square (root ratio : ℝ) :
    selectedQuadraticRoot root ratio ^ 2 =
      C (root ^ 2) * (1 + C ratio * X ^ 2) := by
  have hrescale := congrArg (PowerSeries.rescale ratio)
    half_binomial_square
  have hexpand := congrArg (PowerSeries.expand 2 (by norm_num)) hrescale
  simp only [map_pow, map_add, map_one, rescale_X, map_mul,
    expand_C, expand_X] at hexpand
  rw [selectedQuadraticRoot, mul_pow, hexpand, ← map_pow]

theorem selectedQuadraticRoot_constantCoeff (root ratio : ℝ) :
    constantCoeff (selectedQuadraticRoot root ratio) = root := by
  rw [selectedQuadraticRoot, map_mul, constantCoeff_C]
  rw [constantCoeff_expand]
  rw [← coeff_zero_eq_constantCoeff, coeff_rescale]
  simp

section InverseJet

variable {k : Type*} [Field k]

/-- If the linear coefficient of a series vanishes, so does the linear
coefficient of its inverse. -/
theorem coeff_one_inv_of_coeff_one_eq_zero (f : k⟦X⟧)
    (hlinear : coeff 1 f = 0) : coeff 1 f⁻¹ = 0 := by
  by_cases hconstant : constantCoeff f = 0
  · rw [PowerSeries.inv_eq_zero.mpr hconstant]
    simp
  · rw [coeff_inv]
    norm_num [Finset.antidiagonal, hlinear, hconstant]

/-- The first possible odd cubic coefficient of an inverse.  Quadratic even
data may be arbitrary; it cannot enter before the inverse has a linear term. -/
theorem coeff_three_inv_of_first_odd_cubic (f : k⟦X⟧)
    (hlinear : coeff 1 f = 0) :
    coeff 3 f⁻¹ =
      -(constantCoeff f)⁻¹ *
        (coeff 3 f * (constantCoeff f)⁻¹) := by
  by_cases hconstant : constantCoeff f = 0
  · rw [PowerSeries.inv_eq_zero.mpr hconstant, hconstant]
    simp
  · rw [coeff_inv]
    norm_num [Finset.antidiagonal, hlinear, hconstant,
      coeff_one_inv_of_coeff_one_eq_zero f hlinear]

end InverseJet

section RamifiedEndpointJet

/-- The first odd endpoint coefficient forced by the ramified radial ODE.
Even coefficients of the logarithmic derivative remain arbitrary. -/
theorem endpoint_coeff_five_of_first_odd_cubic
    (logarithmicDerivative endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hLogarithmicLinear : coeff 1 logarithmicDerivative = 0)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * logarithmicDerivative * endpoint) :
    coeff 5 endpoint = (2 / 5 : ℝ) * coeff 3 logarithmicDerivative := by
  have hEndpointLinear := congrArg (coeff 0) hODE
  norm_num [coeff_derivative, coeff_mul, coeff_X,
    Finset.antidiagonal] at hEndpointLinear
  have hEndpointCubic := congrArg (coeff 2) hODE
  norm_num [coeff_derivative, coeff_mul, coeff_X,
    Finset.antidiagonal,
    hEndpointLinear, hLogarithmicLinear] at hEndpointCubic
  have hEndpointQuintic := congrArg (coeff 4) hODE
  norm_num [coeff_derivative, coeff_mul, coeff_X,
    Finset.antidiagonal,
    hEndpointConstant, hEndpointLinear, hEndpointCubic,
    hLogarithmicLinear] at hEndpointQuintic
  linarith

end RamifiedEndpointJet

end FormalLocalGerm
