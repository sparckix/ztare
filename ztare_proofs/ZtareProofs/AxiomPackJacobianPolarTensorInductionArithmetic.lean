import Mathlib.Tactic
import Mathlib.Algebra.Polynomial.Derivative
import Mathlib.Algebra.Polynomial.Div
import Mathlib.RingTheory.PowerSeries.Basic
import ZtareProofs.FormalSemidirectFactorizationOrbit

/-!
Arithmetic carrier for the pure contact-zero polar tensor induction.

The symbolic adapter supplies the split `(A,J)` Lie algebra, the exact
quadratic-field critical residual, the semidirect factorization, and the
source degree dictionary.  This file kernel-checks the universal arithmetic
used after those identities are bound:

* invariance of the Newton weight under the leading polar adjoint;
* the tensor-density monomial recurrence step;
* the uniform four-start resonance bound; and
* strict rate above two on every positive Rees face.

No claim about completeness of the Jacobian adapter is inferred here.
-/

namespace AxiomPackJacobianPolarTensorInductionArithmetic

open Polynomial PowerSeries
open _root_.FormalSemidirectFactorizationOrbit

noncomputable section

/-- The leading adjoint step `(nu,e) -> (nu-h,e+d)` preserves `h*e+d*nu`. -/
theorem tensor_newton_invariant (h d e nu : ℤ) :
    h * (e + d) + d * (nu - h) = h * e + d * nu := by
  ring

/-- Applying `rho(x^d)` after `k` preceding steps contributes the next
factor in the tensor-density orbit product. -/
theorem tensor_orbit_factor_step (d e k : ℤ) :
    2 * (e + k * d) - 3 * d - 5 =
      2 * e + (2 * k - 3) * d - 5 := by
  ring

/-- A positive integral resonance can occur only at an adjoint index
`i = 0,1,2,3`.  Since the resonance equation determines `e` at each index,
there are at most four positive resonant starting exponents. -/
theorem tensor_resonance_index_le_three
    (d e i : ℕ)
    (hd : 1 ≤ d)
    (he : 1 ≤ e)
    (hresonance : 2 * e + 2 * i * d = 3 * d + 5) :
    i ≤ 3 := by
  nlinarith

/-- For a fixed actor exponent and adjoint index, the resonant starting
exponent is unique. -/
theorem tensor_resonant_start_unique
    (d e₁ e₂ i : ℕ)
    (h₁ : 2 * e₁ + 2 * i * d = 3 * d + 5)
    (h₂ : 2 * e₂ + 2 * i * d = 3 * d + 5) :
    e₁ = e₂ := by
  omega

/-- The source-degree slope exceeds twice the parameter-order slope by
exactly twice the positive Rees grade. -/
theorem tensor_positive_face_slope_excess
    (d h : ℤ) :
    2 * d - 2 * (d - h) = 2 * h := by
  ring

/-- Every positive polar face has limiting source rate strictly above two. -/
theorem tensor_positive_face_rate_above_two
    (d h : ℚ)
    (hh : 0 < h)
    (hd : h < d) :
    2 < 2 * d / (d - h) := by
  have hdenom : 0 < d - h := sub_pos.mpr hd
  rw [lt_div_iff₀ hdenom]
  nlinarith

/-! ## Lie-coordinate versus group-module counterexample -/

/-- The row-indexed weight-`3/2` tensor action used by the split critical
quotient. -/
def rowIndexedTensorAction (actor module : ℚ[X]) : ℚ[X] :=
  2 * Polynomial.X * actor * Polynomial.derivative module -
    3 * Polynomial.X * Polynomial.derivative actor * module -
      5 * actor * module

/-- For a fixed actor, the row-indexed tensor action is rational-linear in
the module coordinate. -/
def rowIndexedTensorActionLinearMap (actor : ℚ[X]) : Module.End ℚ ℚ[X] where
  toFun := rowIndexedTensorAction actor
  map_add' := by
    intro left right
    simp only [rowIndexedTensorAction, Polynomial.derivative_add]
    ring
  map_smul' := by
    intro scalar module
    simp only [rowIndexedTensorAction, Polynomial.smul_eq_C_mul,
      Polynomial.derivative_mul, Polynomial.derivative_C, zero_mul,
      zero_add, RingHom.id_apply]
    ring

/-- If both inputs vanish at the origin, the tensor action raises the
`X`-adic module order by one. -/
theorem rowIndexedTensorAction_X_pow_succ_dvd
    (actor module : ℚ[X]) (order : ℕ)
    (actorDivisible : Polynomial.X ∣ actor)
    (moduleDivisible : Polynomial.X ^ (order + 1) ∣ module) :
    Polynomial.X ^ (order + 2) ∣
      rowIndexedTensorAction actor module := by
  have derivativeDivisible :
      Polynomial.X ^ order ∣ Polynomial.derivative module := by
    simpa using
      (Polynomial.pow_sub_one_dvd_derivative_of_pow_dvd moduleDivisible)
  have firstCore :
      (Polynomial.X * Polynomial.X) * Polynomial.X ^ order ∣
        (Polynomial.X * actor) * Polynomial.derivative module :=
    mul_dvd_mul (mul_dvd_mul_left Polynomial.X actorDivisible)
      derivativeDivisible
  have firstTerm :
      Polynomial.X ^ (order + 2) ∣
        2 * Polynomial.X * actor * Polynomial.derivative module := by
    have := dvd_mul_of_dvd_right firstCore (2 : ℚ[X])
    convert this using 1 <;> ring
  have secondCore :
      Polynomial.X * Polynomial.X ^ (order + 1) ∣
        Polynomial.X * module :=
    mul_dvd_mul_left Polynomial.X moduleDivisible
  have secondTerm :
      Polynomial.X ^ (order + 2) ∣
        3 * Polynomial.X * Polynomial.derivative actor * module := by
    have := dvd_mul_of_dvd_right secondCore
      (3 * Polynomial.derivative actor)
    convert this using 1 <;> ring
  have thirdCore :
      Polynomial.X * Polynomial.X ^ (order + 1) ∣ actor * module :=
    mul_dvd_mul actorDivisible moduleDivisible
  have thirdTerm :
      Polynomial.X ^ (order + 2) ∣ 5 * actor * module := by
    have := dvd_mul_of_dvd_right thirdCore (5 : ℚ[X])
    convert this using 1 <;> ring
  exact (firstTerm.sub secondTerm).sub thirdTerm

/-- Every adjoint depth gains one spatial power when actor and module both
start in the origin ideal. -/
theorem rowIndexedTensorAction_iterate_X_pow_succ_dvd
    (actor module : ℚ[X])
    (actorDivisible : Polynomial.X ∣ actor)
    (moduleDivisible : Polynomial.X ∣ module) :
    ∀ depth,
      Polynomial.X ^ (depth + 1) ∣
        (fun value => rowIndexedTensorAction actor value)^[depth] module := by
  intro depth
  induction depth with
  | zero => simpa using moduleDivisible
  | succ depth inductionHypothesis =>
      rw [Function.iterate_succ_apply']
      exact rowIndexedTensorAction_X_pow_succ_dvd actor
        ((fun value => rowIndexedTensorAction actor value)^[depth] module)
        depth actorDivisible inductionHypothesis

/-- Spatial coefficients below the gained action depth vanish. -/
theorem coeff_rowIndexedTensorAction_iterate_eq_zero
    (actor module : ℚ[X])
    (actorDivisible : Polynomial.X ∣ actor)
    (moduleDivisible : Polynomial.X ∣ module)
    (depth spatialDegree : ℕ)
    (below : spatialDegree < depth + 1) :
    ((fun value => rowIndexedTensorAction actor value)^[depth] module).coeff
        spatialDegree = 0 := by
  exact Polynomial.X_pow_dvd_iff.mp
    (rowIndexedTensorAction_iterate_X_pow_succ_dvd actor module
      actorDivisible moduleDivisible depth)
    spatialDegree below

/-- The spatial formal series obtained by flattening the locally finite
target-left action-depth coefficients. -/
def targetLeftTensorDuhamelTransfer
    (actor module : ℚ[X]) : ℚ⟦X⟧ :=
  PowerSeries.mk fun spatialDegree =>
    ∑ depth ∈ Finset.range (spatialDegree + 1),
      (targetLeftSemidirectExponentialCoefficient
          (rowIndexedTensorActionLinearMap actor) module depth).coeff
        spatialDegree

/-- Every omitted action depth has zero coefficient in the corresponding
lower spatial degree. -/
theorem coeff_targetLeftSemidirectExponential_eq_zero
    (actor module : ℚ[X])
    (actorDivisible : Polynomial.X ∣ actor)
    (moduleDivisible : Polynomial.X ∣ module)
    (depth spatialDegree : ℕ)
    (below : spatialDegree < depth + 1) :
    (targetLeftSemidirectExponentialCoefficient
        (rowIndexedTensorActionLinearMap actor) module depth).coeff
      spatialDegree = 0 := by
  rw [targetLeftSemidirectExponentialCoefficient_eq]
  simp only [rowIndexedTensorActionLinearMap,
    LinearMap.coe_mk, AddHom.coe_mk]
  rw [Polynomial.coeff_smul]
  rw [coeff_rowIndexedTensorAction_iterate_eq_zero actor module
    actorDivisible moduleDivisible depth spatialDegree below]
  simp

/-- Any depth cutoff beyond the requested spatial degree computes the same
coefficient.  Thus the flattened transfer is not a finite-window surrogate. -/
theorem coeff_targetLeftTensorDuhamelTransfer_eq_sum_range
    (actor module : ℚ[X])
    (actorDivisible : Polynomial.X ∣ actor)
    (moduleDivisible : Polynomial.X ∣ module)
    (spatialDegree cutoff : ℕ)
    (cutoffBeyond : spatialDegree + 1 ≤ cutoff) :
    PowerSeries.coeff spatialDegree
        (targetLeftTensorDuhamelTransfer actor module) =
      ∑ depth ∈ Finset.range cutoff,
        (targetLeftSemidirectExponentialCoefficient
            (rowIndexedTensorActionLinearMap actor) module depth).coeff
          spatialDegree := by
  rw [targetLeftTensorDuhamelTransfer, PowerSeries.coeff_mk]
  apply Finset.sum_subset (Finset.range_mono cutoffBeyond)
  intro depth depthBelowCutoff depthNotBelowSpatial
  apply coeff_targetLeftSemidirectExponential_eq_zero actor module
    actorDivisible moduleDivisible
  have spatialBelowDepth : spatialDegree < depth := by
    have notDepthBelow : ¬ depth < spatialDegree + 1 := by
      simpa using depthNotBelowSpatial
    omega
  omega

/-- Kernel endpoint for the exact July action and its locally finite
target-left Duhamel flattening. -/
theorem tensor_action_spatial_flattening_terminal_certificate :
    (∀ (actor module : ℚ[X]),
      Polynomial.X ∣ actor → Polynomial.X ∣ module →
      ∀ depth,
        Polynomial.X ^ (depth + 1) ∣
          (fun value => rowIndexedTensorAction actor value)^[depth] module) ∧
    (∀ (actor module : ℚ[X]),
      Polynomial.X ∣ actor → Polynomial.X ∣ module →
      ∀ spatialDegree cutoff,
        spatialDegree + 1 ≤ cutoff →
        PowerSeries.coeff spatialDegree
            (targetLeftTensorDuhamelTransfer actor module) =
          ∑ depth ∈ Finset.range cutoff,
            (targetLeftSemidirectExponentialCoefficient
                (rowIndexedTensorActionLinearMap actor) module depth).coeff
              spatialDegree) := by
  exact ⟨rowIndexedTensorAction_iterate_X_pow_succ_dvd,
    coeff_targetLeftTensorDuhamelTransfer_eq_sum_range⟩

/-- The `k`-th explicit iterate produced from the finite polynomial Lie pair
`A=X`, `J=X^5`. -/
def tensorExponentialCounterexampleIterate (k : ℕ) : ℚ[X] :=
  Polynomial.C ((2 ^ k * k.factorial : ℕ) : ℚ) *
    Polynomial.X ^ (5 + k)

/-- The explicit iterate starts at the polynomial module coordinate `X^5`. -/
@[simp]
theorem tensorExponentialCounterexampleIterate_zero :
    tensorExponentialCounterexampleIterate 0 = (X : ℚ[X]) ^ 5 := by
  simp [tensorExponentialCounterexampleIterate]

/-- One application of the actual tensor action advances the explicit
iterate.  In particular, the new spatial degree is different at every
depth. -/
theorem rowIndexedTensorAction_counterexampleIterate (k : ℕ) :
    rowIndexedTensorAction Polynomial.X
        (tensorExponentialCounterexampleIterate k) =
      tensorExponentialCounterexampleIterate (k + 1) := by
  simp only [rowIndexedTensorAction,
    tensorExponentialCounterexampleIterate]
  rw [Polynomial.derivative_mul, Polynomial.derivative_C,
    zero_mul, zero_add, Polynomial.derivative_pow]
  simp only [Polynomial.derivative_X, mul_one]
  rw [show 5 + k - 1 = 4 + k by omega, pow_add,
    Nat.factorial_succ]
  push_cast
  ring_nf
  have hscalar :
      -((k.factorial : ℚ) * 2 ^ k * 8) +
          (k.factorial : ℚ) * 2 ^ k * (5 + k) * 2 =
        (k.factorial : ℚ) * k * 2 ^ k * 2 +
          (k.factorial : ℚ) * 2 ^ k * 2 := by
    ring
  have hconstant := congrArg (Polynomial.C : ℚ → ℚ[X]) hscalar
  simp only [map_neg, map_add, map_mul, map_natCast] at hconstant ⊢
  have hCtwo : Polynomial.C (2 : ℚ) = (2 : ℚ[X]) :=
    Polynomial.C_eq_natCast 2
  have hCfive : Polynomial.C (5 : ℚ) = (5 : ℚ[X]) :=
    Polynomial.C_eq_natCast 5
  have hCeight : Polynomial.C (8 : ℚ) = (8 : ℚ[X]) :=
    Polynomial.C_eq_natCast 8
  rw [hCtwo, hCfive, hCeight] at hconstant
  rw [hCtwo, hCfive]
  linear_combination
    (Polynomial.X ^ 6 * Polynomial.X ^ k) * hconstant

/-- The coefficient contributed at exponential depth `k` is the iterate
coefficient divided by `(k+1)!`. -/
def tensorExponentialTransferCoefficient (k : ℕ) : ℚ :=
  ((2 ^ k * k.factorial : ℕ) : ℚ) / (k + 1).factorial

/-- Closed form of the semidirect exponential transfer coefficient. -/
theorem tensorExponentialTransferCoefficient_eq (k : ℕ) :
    tensorExponentialTransferCoefficient k =
      (2 : ℚ) ^ k / (k + 1) := by
  rw [tensorExponentialTransferCoefficient, Nat.factorial_succ]
  push_cast
  have hk : (k.factorial : ℚ) ≠ 0 := by positivity
  field_simp

/-- Every depth of the semidirect exponential transfer survives. -/
theorem tensorExponentialTransferCoefficient_ne_zero (k : ℕ) :
    tensorExponentialTransferCoefficient k ≠ 0 := by
  rw [tensorExponentialTransferCoefficient_eq]
  positivity

/-- The additive group-module coordinate obtained by exponentiating the
finite Lie pair `A=X`, `J=X^5`. -/
def tensorExponentialModuleCounterexample : ℚ⟦X⟧ :=
  PowerSeries.mk fun degree =>
    if 5 ≤ degree then
      (2 : ℚ) ^ (degree - 5) / ((degree - 4 : ℕ) : ℚ)
    else 0

/-- Its coefficient in degree `5+k` is exactly the depth-`k` semidirect
transfer coefficient. -/
theorem coeff_tensorExponentialModuleCounterexample (k : ℕ) :
    coeff (5 + k) tensorExponentialModuleCounterexample =
      tensorExponentialTransferCoefficient k := by
  have hfive : 5 + k - 5 = k := by omega
  have hfour : 5 + k - 4 = k + 1 := by omega
  rw [tensorExponentialModuleCounterexample, PowerSeries.coeff_mk]
  rw [if_pos (by omega)]
  rw [hfive, hfour, tensorExponentialTransferCoefficient_eq]
  push_cast
  rfl

/-- A polynomial Lie pair can therefore exponentiate to a nonpolynomial
group-module coordinate. -/
theorem tensorExponentialModuleCounterexample_not_polynomial :
    ¬ ∃ modulePolynomial : ℚ[X],
      (modulePolynomial : ℚ⟦X⟧) =
        tensorExponentialModuleCounterexample := by
  rintro ⟨modulePolynomial, hmodule⟩
  let k := modulePolynomial.natDegree + 1
  have hdegree : modulePolynomial.natDegree < 5 + k := by
    dsimp [k]
    omega
  have hpolynomialZero :
      coeff (5 + k) (modulePolynomial : ℚ⟦X⟧) = 0 := by
    simpa using Polynomial.coeff_eq_zero_of_natDegree_lt hdegree
  have hseriesNonzero :
      coeff (5 + k) tensorExponentialModuleCounterexample ≠ 0 := by
    rw [coeff_tensorExponentialModuleCounterexample]
    exact tensorExponentialTransferCoefficient_ne_zero k
  apply hseriesNonzero
  rw [← hmodule]
  exact hpolynomialZero

/-- Target-left cancellation multiplies depth `k` by `(-1)^k`; it cannot
make any transfer coefficient vanish. -/
theorem targetLeftTransferCoefficient_ne_zero (k : ℕ) :
    (-1 : ℚ) ^ k * tensorExponentialTransferCoefficient k ≠ 0 := by
  exact mul_ne_zero (pow_ne_zero _ (by norm_num))
    (tensorExponentialTransferCoefficient_ne_zero k)

/-- Kernel certificate separating finite polynomial Lie coordinates from
the generally infinite semidirect group-module coordinate. -/
theorem tensor_lie_group_module_distinction_terminal_certificate :
    tensorExponentialCounterexampleIterate 0 = (X : ℚ[X]) ^ 5 ∧
    (∀ k, rowIndexedTensorAction Polynomial.X
      (tensorExponentialCounterexampleIterate k) =
        tensorExponentialCounterexampleIterate (k + 1)) ∧
    (∀ k, coeff (5 + k) tensorExponentialModuleCounterexample =
      tensorExponentialTransferCoefficient k) ∧
    (∀ k, tensorExponentialTransferCoefficient k ≠ 0) ∧
    (¬ ∃ modulePolynomial : ℚ[X],
      (modulePolynomial : ℚ⟦X⟧) = tensorExponentialModuleCounterexample) ∧
    (∀ k, (-1 : ℚ) ^ k *
      tensorExponentialTransferCoefficient k ≠ 0) := by
  exact ⟨tensorExponentialCounterexampleIterate_zero,
    rowIndexedTensorAction_counterexampleIterate,
    coeff_tensorExponentialModuleCounterexample,
    tensorExponentialTransferCoefficient_ne_zero,
    tensorExponentialModuleCounterexample_not_polynomial,
    targetLeftTransferCoefficient_ne_zero⟩

/-- Aggregated arithmetic endpoint for the polar tensor induction. -/
theorem polar_tensor_induction_arithmetic_terminal_certificate :
    (∀ h d e nu : ℤ,
      h * (e + d) + d * (nu - h) = h * e + d * nu) ∧
    (∀ d e k : ℤ,
      2 * (e + k * d) - 3 * d - 5 =
        2 * e + (2 * k - 3) * d - 5) ∧
    (∀ d e i : ℕ,
      1 ≤ d → 1 ≤ e →
      2 * e + 2 * i * d = 3 * d + 5 → i ≤ 3) ∧
    (∀ d e₁ e₂ i : ℕ,
      2 * e₁ + 2 * i * d = 3 * d + 5 →
      2 * e₂ + 2 * i * d = 3 * d + 5 → e₁ = e₂) ∧
    (∀ d h : ℤ, 2 * d - 2 * (d - h) = 2 * h) ∧
    (∀ d h : ℚ, 0 < h → h < d → 2 < 2 * d / (d - h)) := by
  exact ⟨tensor_newton_invariant,
    tensor_orbit_factor_step,
    tensor_resonance_index_le_three,
    tensor_resonant_start_unique,
    tensor_positive_face_slope_excess,
    tensor_positive_face_rate_above_two⟩

end

end AxiomPackJacobianPolarTensorInductionArithmetic
