import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxAnalyticRealization
import ZtareProofs.FormalCriticalConnectionRationalization
import ZtareProofs.FormalRatFuncLaurentTangentCarrier

/-!
# The critical rational coordinate in the ramified analytic chart

The rational critical parameter and the analytic ramification parameter are
different coordinates.  This file constructs their exact change of
coordinate, proves its tangent is invertible, and installs the resulting
rational differential field inside complex Laurent series.
-/

namespace AxiomPackJacobianCriticalLaurentCoordinate

open Filter Polynomial PowerSeries
open scoped LaurentSeries

open AxiomPackJacobianCriticalPuiseuxAnalyticRealization
open AxiomPackJacobianCriticalPuiseuxUniformization
open FormalAnalyticTaylorAlgebra
open FormalCriticalConnectionRationalization
open FormalRatFuncLaurentTangentCarrier

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

/-- Critical conic parameter on the selected ramified sheet. -/
def sOfT (t : ℂ) : ℂ :=
  3 * t / analyticDiscriminantRoot t

theorem discriminantRoot_zero_ne :
    analyticDiscriminantRoot 0 ≠ 0 := by
  rw [analyticDiscriminantRoot_zero]
  exact mul_ne_zero (by norm_num)
    (Complex.ofReal_ne_zero.mpr
      (ne_of_gt (Real.sqrt_pos.2 (by norm_num))))

theorem sOfT_analyticAt : AnalyticAt ℂ sOfT 0 := by
  unfold sOfT
  exact (analyticAt_const.mul analyticAt_id).div
    analyticDiscriminantRoot_analyticAt discriminantRoot_zero_ne

@[simp]
theorem sOfT_zero : sOfT 0 = 0 := by
  simp [sOfT]

theorem sOfT_hasDerivAt_zero :
    HasDerivAt sOfT (3 / analyticDiscriminantRoot 0) 0 := by
  have hnumerator : HasDerivAt (fun t : ℂ => 3 * t) 3 0 := by
    convert (hasDerivAt_const (0 : ℂ) (3 : ℂ)).mul (hasDerivAt_id 0)
      using 1 <;> simp
  have hdenominator :=
    analyticDiscriminantRoot_analyticAt.differentiableAt.hasDerivAt
  have hquotient := hnumerator.div hdenominator discriminantRoot_zero_ne
  convert hquotient using 1
  simp only [zero_mul, mul_zero, sub_zero]
  field_simp [discriminantRoot_zero_ne]

theorem deriv_sOfT_zero_ne : deriv sOfT 0 ≠ 0 := by
  rw [sOfT_hasDerivAt_zero.deriv]
  exact div_ne_zero (by norm_num) discriminantRoot_zero_ne

/-- Taylor germ of the critical rational coordinate. -/
def sSeries : PS := taylorPowerSeries sOfT 0

@[simp]
theorem sSeries_constantCoeff : sSeries.constantCoeff = 0 := by
  simp [sSeries]

theorem sSeries_coeff_one : sSeries.coeff 1 = deriv sOfT 0 := by
  simp [sSeries, coeff_taylorPowerSeries]

theorem sSeries_coeff_one_ne : sSeries.coeff 1 ≠ 0 := by
  rw [sSeries_coeff_one]
  exact deriv_sOfT_zero_ne

noncomputable instance sSeriesLinearInvertible :
    Invertible (sSeries.coeff 1) :=
  invertibleOfNonzero sSeries_coeff_one_ne

/-- Mobius form of the same coordinate in the continued `q` chart. -/
def mobiusS (q : ℂ) : ℂ := (3 - q) / (q + 1)

theorem mobiusS_qOfT_eq_sOfT
    (t : ℂ)
    (hroot : analyticDiscriminantRoot t ≠ 0)
    (ht : t ^ 2 - 2 ≠ 0)
    (hq : qOfT t + 1 ≠ 0) :
    mobiusS (qOfT t) = sOfT t := by
  unfold mobiusS
  rw [div_eq_iff hq]
  unfold qOfT sOfT
  field_simp [hroot, ht]
  calc
    analyticDiscriminantRoot t *
          (3 * (t ^ 2 - 2) -
            (t * analyticDiscriminantRoot t - 6)) =
        3 * analyticDiscriminantRoot t * t ^ 2 -
          t * analyticDiscriminantRoot t ^ 2 := by ring
    _ = 3 * t *
          (t * analyticDiscriminantRoot t - 6 + (t ^ 2 - 2)) := by
      rw [analyticDiscriminantRoot_square]
      ring

theorem mobiusS_qOfT_eventually :
    (fun t => mobiusS (qOfT t)) =ᶠ[nhds (0 : ℂ)] sOfT := by
  have hroot : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      discriminantRoot_zero_ne
  have ht : ∀ᶠ t in nhds (0 : ℂ), t ^ 2 - 2 ≠ 0 :=
    ((analyticAt_id.pow 2).sub
      (analyticAt_const : AnalyticAt ℂ (fun _ : ℂ => (2 : ℂ)) 0))
        |>.continuousAt.eventually_ne (by norm_num)
  have hq : ∀ᶠ t in nhds (0 : ℂ), qOfT t + 1 ≠ 0 :=
    (qOfT_analyticAt.add analyticAt_const).continuousAt.eventually_ne
      (by simpa only [Pi.add_apply, qOfT_zero] using
        (show (3 : ℂ) + 1 ≠ 0 by norm_num))
  filter_upwards [hroot, ht, hq] with t hrootAt htAt hqAt
  exact mobiusS_qOfT_eq_sOfT t hrootAt htAt hqAt

/-- Complex point formula for the rational source parameterization. -/
def complexXOfS (s : ℂ) : ℂ :=
  6 * (s ^ 2 - 1) / (s ^ 2 + 3)

/-- Complex point formula for the selected radical coordinate. -/
def complexRadicalOfS (s : ℂ) : ℂ :=
  24 * s / (s ^ 2 + 3)

/-- Complex realization of the exact rational logarithmic differential. -/
def complexExplicitRationalDifferential (s : ℂ) : ℂ :=
  896 * s * (s - 3) * (s + 1) * (s ^ 2 - 6 * s - 3) /
    ((s - 1) *
      (199 * s ^ 7 - 1393 * s ^ 6 + 67 * s ^ 5 + 219 * s ^ 4 +
        5973 * s ^ 3 + 10125 * s ^ 2 + 10593 * s + 2889))

/-- Derivative of the Mobius change from the continued `q` coordinate. -/
def mobiusSDerivative (q : ℂ) : ℂ :=
  -4 / (q + 1) ^ 2

theorem mobiusS_hasDerivAt (q : ℂ) (hq : q + 1 ≠ 0) :
    HasDerivAt mobiusS (mobiusSDerivative q) q := by
  have hnumerator : HasDerivAt (fun z : ℂ => 3 - z) (-1) q := by
    convert (hasDerivAt_const q (3 : ℂ)).sub (hasDerivAt_id q)
      using 1 <;> simp
  have hdenominator : HasDerivAt (fun z : ℂ => z + 1) 1 q := by
    convert (hasDerivAt_id q).add_const 1 using 1 <;> simp
  unfold mobiusS mobiusSDerivative
  convert hnumerator.div hdenominator hq using 1
  field_simp [hq]
  ring

/-- The visible critical connection is covariant under the exact Mobius
change of parameter. -/
theorem mobius_connection_identity
    (q : ℂ)
    (hqPlus : q + 1 ≠ 0)
    (hqMinus : q - 1 ≠ 0)
    (hflow : flowDenominator q ≠ 0)
    (hsMinus : mobiusS q - 1 ≠ 0)
    (hpole :
      199 * mobiusS q ^ 7 - 1393 * mobiusS q ^ 6 +
          67 * mobiusS q ^ 5 + 219 * mobiusS q ^ 4 +
          5973 * mobiusS q ^ 3 + 10125 * mobiusS q ^ 2 +
          10593 * mobiusS q + 2889 ≠ 0) :
    mobiusSDerivative q *
        complexExplicitRationalDifferential (mobiusS q) =
      fullLogDerivative q := by
  have hleftDenominator :
      (mobiusS q - 1) *
          (199 * mobiusS q ^ 7 - 1393 * mobiusS q ^ 6 +
            67 * mobiusS q ^ 5 + 219 * mobiusS q ^ 4 +
            5973 * mobiusS q ^ 3 + 10125 * mobiusS q ^ 2 +
            10593 * mobiusS q + 2889) ≠ 0 :=
    mul_ne_zero hsMinus hpole
  have hrightDenominator :
      (q - 1) * flowDenominator q ≠ 0 :=
    mul_ne_zero hqMinus hflow
  have hmobiusExpansion :
      complexExplicitRationalDifferential (mobiusS q) =
        224 * q * (q - 3) * (q + 1) ^ 3 *
            (q ^ 2 - 6 * q - 3) /
          ((q - 1) * flowDenominator q) := by
    unfold complexExplicitRationalDifferential
    rw [div_eq_div_iff hleftDenominator hrightDenominator]
    unfold mobiusS flowDenominator
    field_simp [hqPlus]
    ring
  rw [hmobiusExpansion]
  unfold mobiusSDerivative fullLogDerivative regularizedLogDerivative
    regularizedFlowNumerator flowDenominator
  field_simp [hqPlus, hqMinus, hflow]
  ring

/-- Closed derivative formula for the critical rational parameter in the
ramified coordinate. -/
def sOfTDerivativeFormula (t : ℂ) : ℂ :=
  (3 * analyticDiscriminantRoot t -
      3 * t * (-3 * t / analyticDiscriminantRoot t)) /
    analyticDiscriminantRoot t ^ 2

theorem sOfT_deriv_eventually :
    ∀ᶠ t in nhds (0 : ℂ), deriv sOfT t = sOfTDerivativeFormula t := by
  have hsAnalytic := sOfT_analyticAt.eventually_analyticAt
  have hrootAnalytic :=
    analyticDiscriminantRoot_analyticAt.eventually_analyticAt
  have hrootNonzero : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      discriminantRoot_zero_ne
  filter_upwards [hsAnalytic, hrootAnalytic,
      analyticDiscriminantRoot_deriv_eventually, hrootNonzero] with
      t hsAt hrootAt hrootDerivative hroot
  have hformula :=
    ((hasDerivAt_const t (3 : ℂ)).mul (hasDerivAt_id t)).div
      hrootAt.differentiableAt.hasDerivAt hroot
  have hsFormula : HasDerivAt sOfT (sOfTDerivativeFormula t) t := by
    unfold sOfT sOfTDerivativeFormula
    convert hformula using 1 <;>
      simp only [id_eq, one_mul, Nat.cast_ofNat] <;>
      rw [hrootDerivative]
  exact hsFormula.deriv

theorem derivative_coordinate_covariance
    (t : ℂ)
    (hroot : analyticDiscriminantRoot t ≠ 0)
    (ht : t ^ 2 - 2 ≠ 0)
    (hq : qOfT t + 1 ≠ 0) :
    sOfTDerivativeFormula t =
      qOfTDerivativeFormula t * mobiusSDerivative (qOfT t) := by
  unfold sOfTDerivativeFormula qOfTDerivativeFormula
    mobiusSDerivative qOfT
  field_simp [hroot, ht, hq]
  rw [analyticDiscriminantRoot_square]
  ring

theorem deriv_sOfT_coordinate_covariance_eventually :
    ∀ᶠ t in nhds (0 : ℂ),
      deriv sOfT t =
        deriv qOfT t * mobiusSDerivative (qOfT t) := by
  have hroot : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      discriminantRoot_zero_ne
  have ht : ∀ᶠ t in nhds (0 : ℂ), t ^ 2 - 2 ≠ 0 :=
    ((analyticAt_id.pow 2).sub
      (analyticAt_const : AnalyticAt ℂ (fun _ : ℂ => (2 : ℂ)) 0))
        |>.continuousAt.eventually_ne (by norm_num)
  have hq : ∀ᶠ t in nhds (0 : ℂ), qOfT t + 1 ≠ 0 :=
    (qOfT_analyticAt.add analyticAt_const).continuousAt.eventually_ne
      (by simp)
  filter_upwards [sOfT_deriv_eventually, qOfT_deriv_eventually,
      hroot, ht, hq] with t hs hqDerivative hrootAt htAt hqAt
  rw [hs, hqDerivative]
  exact derivative_coordinate_covariance t hrootAt htAt hqAt

theorem sOfT_sub_one_eventually_ne :
    ∀ᶠ t in nhds (0 : ℂ), sOfT t - 1 ≠ 0 :=
  (sOfT_analyticAt.sub analyticAt_const).continuousAt.eventually_ne
    (by simp)

theorem sOfT_pole_eventually_ne :
    ∀ᶠ t in nhds (0 : ℂ),
      199 * sOfT t ^ 7 - 1393 * sOfT t ^ 6 +
          67 * sOfT t ^ 5 + 219 * sOfT t ^ 4 +
          5973 * sOfT t ^ 3 + 10125 * sOfT t ^ 2 +
          10593 * sOfT t + 2889 ≠ 0 := by
  have hanalytic : AnalyticAt ℂ
      (fun t =>
        199 * sOfT t ^ 7 - 1393 * sOfT t ^ 6 +
          67 * sOfT t ^ 5 + 219 * sOfT t ^ 4 +
          5973 * sOfT t ^ 3 + 10125 * sOfT t ^ 2 +
          10593 * sOfT t + 2889) 0 := by
    fun_prop
  exact hanalytic.continuousAt.eventually_ne (by norm_num [sOfT])

theorem pulledBack_explicit_connection_eventually :
    (fun t => deriv sOfT t *
        complexExplicitRationalDifferential (sOfT t)) =ᶠ[nhds (0 : ℂ)]
      analyticEndpointCoefficient := by
  have hqPlus : ∀ᶠ t in nhds (0 : ℂ), qOfT t + 1 ≠ 0 :=
    (qOfT_analyticAt.add analyticAt_const).continuousAt.eventually_ne
      (by simp)
  filter_upwards [deriv_sOfT_coordinate_covariance_eventually,
      mobiusS_qOfT_eventually, pulledBackLogDerivative_eventually_eq,
      qOfT_eventually_mem_right_disk, hqPlus,
      sOfT_sub_one_eventually_ne, sOfT_pole_eventually_ne] with
      t hderivative hcoordinate hpullback hqDisk hqPlusAt
        hsMinusAt hpoleAt
  have hqMinusAt : qOfT t - 1 ≠ 0 := by
    intro heq
    have hqOne : qOfT t = 1 := sub_eq_zero.mp heq
    rw [hqOne] at hqDisk
    norm_num [Metric.mem_ball, dist_eq_norm, Complex.norm_real] at hqDisk
  have hflowAt : flowDenominator (qOfT t) ≠ 0 :=
    flowDenominator_ne_zero_on_right_disk hqDisk
  have hsMinusMobius : mobiusS (qOfT t) - 1 ≠ 0 := by
    rw [hcoordinate]
    exact hsMinusAt
  have hpoleMobius :
      199 * mobiusS (qOfT t) ^ 7 - 1393 * mobiusS (qOfT t) ^ 6 +
          67 * mobiusS (qOfT t) ^ 5 + 219 * mobiusS (qOfT t) ^ 4 +
          5973 * mobiusS (qOfT t) ^ 3 +
          10125 * mobiusS (qOfT t) ^ 2 +
          10593 * mobiusS (qOfT t) + 2889 ≠ 0 := by
    rw [hcoordinate]
    exact hpoleAt
  have hconnection := mobius_connection_identity (qOfT t) hqPlusAt
    hqMinusAt hflowAt hsMinusMobius hpoleMobius
  calc
    deriv sOfT t * complexExplicitRationalDifferential (sOfT t) =
        (deriv qOfT t * mobiusSDerivative (qOfT t)) *
          complexExplicitRationalDifferential (mobiusS (qOfT t)) := by
      rw [hderivative, hcoordinate]
    _ = deriv qOfT t * fullLogDerivative (qOfT t) := by
      rw [← mul_assoc, hconnection]
    _ = pulledBackLogDerivative t := rfl
    _ = analyticEndpointCoefficient t := hpullback

theorem complexExplicitRationalDifferential_comp_analyticAt :
    AnalyticAt ℂ
      (fun t => complexExplicitRationalDifferential (sOfT t)) 0 := by
  unfold complexExplicitRationalDifferential
  apply AnalyticAt.div
  · fun_prop
  · fun_prop
  · norm_num [sOfT]

/-- Taylor form of covariance of the visible connection. -/
theorem pulledBack_explicit_connection_taylor :
    d⁄dX ℂ sSeries *
        taylorPowerSeries
          (fun t => complexExplicitRationalDifferential (sOfT t)) 0 =
      taylorPowerSeries analyticEndpointCoefficient 0 := by
  have hderivative := sOfT_analyticAt.deriv
  have hleft := hderivative.mul
    complexExplicitRationalDifferential_comp_analyticAt
  have hseries := taylorPowerSeries_eq_of_eventuallyEq hleft
    analyticEndpointCoefficient_analyticAt
    pulledBack_explicit_connection_eventually
  rw [taylorPowerSeries_mul hderivative
      complexExplicitRationalDifferential_comp_analyticAt,
    taylorPowerSeries_deriv, sSeries] at hseries
  exact hseries

/-- Complexified numerator polynomial of the exact rational connection. -/
def complexExplicitNumeratorPolynomial : ℂ[X] :=
  FormalCriticalMonodromyResidueBinding.numeratorPolynomial.map
    (algebraMap ℝ ℂ)

/-- Complexified full denominator polynomial of the exact connection. -/
def complexExplicitDenominatorPolynomial : ℂ[X] :=
  (Polynomial.X - Polynomial.C 1) *
    FormalCriticalMonodromyResidueBinding.polePolynomial.map
      (algebraMap ℝ ℂ)

theorem complexExplicitRationalDifferential_eq_polynomial_div (s : ℂ) :
    complexExplicitRationalDifferential s =
      complexExplicitNumeratorPolynomial.eval s /
        complexExplicitDenominatorPolynomial.eval s := by
  simp [complexExplicitRationalDifferential,
    complexExplicitNumeratorPolynomial,
    complexExplicitDenominatorPolynomial,
    FormalCriticalMonodromyResidueBinding.numeratorPolynomial,
    FormalCriticalMonodromyResidueBinding.polePolynomial]
  ring

theorem taylor_complexExplicitRationalDifferential :
    taylorPowerSeries
        (fun t => complexExplicitRationalDifferential (sOfT t)) 0 =
      Polynomial.aeval sSeries complexExplicitNumeratorPolynomial *
        (Polynomial.aeval sSeries
          complexExplicitDenominatorPolynomial)⁻¹ := by
  have hdivision := taylorPowerSeries_polynomial_div sOfT_analyticAt
    complexExplicitNumeratorPolynomial
    complexExplicitDenominatorPolynomial
    (by
      norm_num [complexExplicitDenominatorPolynomial,
        FormalCriticalMonodromyResidueBinding.polePolynomial, sOfT])
  simpa only [complexExplicitRationalDifferential_eq_polynomial_div,
    sSeries] using hdivision

theorem complexXOfS_sOfT
    (t : ℂ) (hroot : analyticDiscriminantRoot t ≠ 0)
    (hdenominator : sOfT t ^ 2 + 3 ≠ 0) :
    complexXOfS (sOfT t) = analyticLocalX t := by
  unfold complexXOfS sOfT analyticLocalX
  field_simp [hroot, hdenominator]
  rw [analyticDiscriminantRoot_square]
  ring

theorem complexRadicalOfS_sOfT
    (t : ℂ) (hroot : analyticDiscriminantRoot t ≠ 0)
    (hdenominator : sOfT t ^ 2 + 3 ≠ 0) :
    complexRadicalOfS (sOfT t) =
      t * analyticDiscriminantRoot t := by
  unfold complexRadicalOfS sOfT
  field_simp [hroot, hdenominator]
  rw [analyticDiscriminantRoot_square]
  ring

theorem sOfT_sq_add_three_eventually_ne :
    ∀ᶠ t in nhds (0 : ℂ), sOfT t ^ 2 + 3 ≠ 0 :=
  ((sOfT_analyticAt.pow 2).add analyticAt_const).continuousAt.eventually_ne
    (by simp)

theorem complexXOfS_sOfT_eventually :
    (fun t => complexXOfS (sOfT t)) =ᶠ[nhds (0 : ℂ)]
      analyticLocalX := by
  have hroot : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      discriminantRoot_zero_ne
  filter_upwards [hroot, sOfT_sq_add_three_eventually_ne]
      with t hrootAt hdenominator
  exact complexXOfS_sOfT t hrootAt hdenominator

theorem complexRadicalOfS_sOfT_eventually :
    (fun t => complexRadicalOfS (sOfT t)) =ᶠ[nhds (0 : ℂ)]
      fun t => t * analyticDiscriminantRoot t := by
  have hroot : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      discriminantRoot_zero_ne
  filter_upwards [hroot, sOfT_sq_add_three_eventually_ne]
      with t hrootAt hdenominator
  exact complexRadicalOfS_sOfT t hrootAt hdenominator

/-- Taylor transport through a quotient of two polynomial evaluations. -/
theorem taylorPowerSeries_polynomial_div
    {parameter : ℂ → ℂ} {center : ℂ}
    (hparameter : AnalyticAt ℂ parameter center)
    (numerator denominator : ℂ[X])
    (hdenominator : denominator.eval (parameter center) ≠ 0) :
    taylorPowerSeries
        (fun t => numerator.eval (parameter t) /
          denominator.eval (parameter t)) center =
      Polynomial.aeval (taylorPowerSeries parameter center) numerator *
        (Polynomial.aeval
          (taylorPowerSeries parameter center) denominator)⁻¹ := by
  have hnumerator := hparameter.aeval_polynomial numerator
  have hdenominatorAnalytic := hparameter.aeval_polynomial denominator
  change taylorPowerSeries
      ((fun t => numerator.eval (parameter t)) *
        fun t => (denominator.eval (parameter t))⁻¹) center = _
  rw [taylorPowerSeries_mul hnumerator
    (hdenominatorAnalytic.inv hdenominator)]
  rw [taylorPowerSeries_inv hdenominatorAnalytic hdenominator]
  rw [taylorPowerSeries_aeval_polynomial hparameter,
    taylorPowerSeries_aeval_polynomial hparameter]
  rfl

def complexXNumerator : ℂ[X] := 6 * (Polynomial.X ^ 2 - 1)
def complexXDenominator : ℂ[X] := Polynomial.X ^ 2 + 3

theorem complexXOfS_eq_polynomial_div (s : ℂ) :
    complexXOfS s =
      complexXNumerator.eval s / complexXDenominator.eval s := by
  simp [complexXOfS, complexXNumerator, complexXDenominator]

theorem taylor_complexXOfS_sOfT :
    taylorPowerSeries (fun t => complexXOfS (sOfT t)) 0 =
      Polynomial.aeval sSeries complexXNumerator *
        (Polynomial.aeval sSeries complexXDenominator)⁻¹ := by
  have hdivision := taylorPowerSeries_polynomial_div sOfT_analyticAt
    complexXNumerator complexXDenominator (by simp [complexXDenominator])
  simpa only [complexXOfS_eq_polynomial_div, sSeries] using hdivision

theorem taylor_analyticLocalX_as_s :
    taylorPowerSeries analyticLocalX 0 =
      Polynomial.aeval sSeries complexXNumerator *
        (Polynomial.aeval sSeries complexXDenominator)⁻¹ := by
  rw [← taylor_complexXOfS_sOfT]
  have hleft : AnalyticAt ℂ (fun t => complexXOfS (sOfT t)) 0 := by
    rw [show (fun t => complexXOfS (sOfT t)) =
        fun t => complexXNumerator.eval (sOfT t) /
          complexXDenominator.eval (sOfT t) by
      funext t
      exact complexXOfS_eq_polynomial_div (sOfT t)]
    exact (sOfT_analyticAt.aeval_polynomial complexXNumerator).div
      (sOfT_analyticAt.aeval_polynomial complexXDenominator)
      (by simp [complexXDenominator])
  exact (taylorPowerSeries_eq_of_eventuallyEq
    hleft
    analyticLocalX_analyticAt complexXOfS_sOfT_eventually).symm

/-- Algebra structure selected by the exact critical tangent coordinate. -/
@[reducible]
def criticalLaurentAlgebra : Algebra RF LS :=
  ratFuncLaurentAlgebra sSeries sSeries_constantCoeff

noncomputable local instance criticalLaurentAlgebraInstance : Algebra RF LS :=
  criticalLaurentAlgebra

theorem critical_parameter_binding :
    algebraMap RF LS parameter = algebraMap PS LS sSeries := by
  change ratFuncToLaurent sSeries sSeries_constantCoeff parameter = _
  exact ratFuncToLaurent_X sSeries sSeries_constantCoeff

theorem critical_real_constant_binding (constant : ℝ) :
    algebraMap RF LS (RatFunc.C constant) =
      algebraMap ℂ LS (constant : ℂ) := by
  change ratFuncToLaurent sSeries sSeries_constantCoeff
      (RatFunc.C constant) = _
  rw [← RatFunc.algebraMap_C, ratFuncToLaurent_algebraMap]
  simp [realPolynomialToLaurent]

/-- The canonical power-series inverse maps to the field inverse whenever
its constant coefficient is nonzero. -/
theorem algebraMap_powerSeries_inv
    (series : PS) (hconstant : series.constantCoeff ≠ 0) :
    algebraMap PS LS series⁻¹ = (algebraMap PS LS series)⁻¹ := by
  have hseries : series ≠ 0 := by
    intro hzero
    apply hconstant
    rw [hzero]
    simp
  have hmapped : algebraMap PS LS series ≠ 0 := by
    simpa only [map_zero] using
      (FaithfulSMul.algebraMap_injective PS LS).ne hseries
  apply (eq_inv_iff_mul_eq_one₀ hmapped).2
  rw [← map_mul, PowerSeries.inv_mul_cancel series hconstant, map_one]

/-- The rational connection and its analytic Taylor pullback define the
same Laurent element. -/
theorem critical_connection_binding :
    algebraMap RF LS explicitRationalDifferential =
      algebraMap PS LS
        (taylorPowerSeries
          (fun t => complexExplicitRationalDifferential (sOfT t)) 0) := by
  rw [taylor_complexExplicitRationalDifferential]
  have hdenominator :
      (Polynomial.aeval sSeries
        complexExplicitDenominatorPolynomial).constantCoeff ≠ 0 := by
    norm_num [complexExplicitDenominatorPolynomial,
      FormalCriticalMonodromyResidueBinding.polePolynomial,
      sSeries_constantCoeff]
  rw [map_mul, algebraMap_powerSeries_inv _ hdenominator]
  change ratFuncToLaurent sSeries sSeries_constantCoeff
      explicitRationalDifferential = _
  unfold explicitRationalDifferential numeratorRationalFunction
    poleRationalFunction parameter
  rw [map_div₀, map_mul, map_sub, map_one,
    ratFuncToLaurent_algebraMap, ratFuncToLaurent_algebraMap,
    ratFuncToLaurent_X, realPolynomialToLaurent_apply,
    realPolynomialToLaurent_apply]
  simp [complexExplicitNumeratorPolynomial,
    complexExplicitDenominatorPolynomial, div_eq_mul_inv]

theorem critical_source_binding :
    algebraMap RF LS xOfParameter =
      algebraMap PS LS (taylorPowerSeries analyticLocalX 0) := by
  rw [taylor_analyticLocalX_as_s]
  have hdenominator :
      (Polynomial.aeval sSeries complexXDenominator).constantCoeff ≠ 0 := by
    simp [complexXDenominator]
  rw [map_mul, algebraMap_powerSeries_inv _ hdenominator]
  unfold xOfParameter parameter complexXNumerator complexXDenominator
  rw [map_div₀]
  simp [critical_parameter_binding]

theorem rationalDerivative_xOfParameter :
    FormalRationalFunctionDerivationLocalOrder.rationalDerivative
        xOfParameter =
      xDerivativeOfParameter := by
  let numerator : ℝ[X] := 6 * (Polynomial.X ^ 2 - 1)
  let denominator : ℝ[X] := Polynomial.X ^ 2 + 3
  have hrepresentation :
      xOfParameter =
        algebraMap ℝ[X] RF numerator /
          algebraMap ℝ[X] RF denominator := by
    simp [xOfParameter, parameter, numerator, denominator]
  rw [hrepresentation,
    FormalRationalFunctionDerivationLocalOrder.rationalDerivative_div]
  unfold FormalRationalFunctionDerivationLocalOrder.quotientDerivative
    numerator denominator xDerivativeOfParameter parameter
  simp only [map_sub, map_mul, map_pow, map_add, map_one, map_ofNat,
    RatFunc.algebraMap_X, Polynomial.derivative_sub,
    Polynomial.derivative_mul, Polynomial.derivative_pow,
    Polynomial.derivative_X, Polynomial.derivative_one,
    Polynomial.derivative_ofNat, zero_mul, add_zero, sub_zero]
  field_simp [parameter_sq_add_three_ne_zero]
  ring

/-- The inherited coefficient derivation is exactly the normalized tangent
Laurent derivation. -/
theorem critical_coefficient_derivative_binding (coefficient : RF) :
    algebraMap RF LS
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
          coefficient) =
      coordinateDerivation sSeries (algebraMap RF LS coefficient) := by
  change ratFuncToLaurent sSeries sSeries_constantCoeff
      (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
        coefficient) = _
  exact ratFuncToLaurent_derivative sSeries sSeries_constantCoeff coefficient

theorem critical_source_derivative_binding :
    algebraMap RF LS xDerivativeOfParameter =
      coordinateDerivation sSeries (algebraMap RF LS xOfParameter) := by
  rw [← rationalDerivative_xOfParameter]
  exact critical_coefficient_derivative_binding xOfParameter

/-- Any visible Taylor germ satisfying the endpoint ODE in the ramified
coordinate satisfies the rational connection ODE after normalization to the
critical parameter. -/
theorem critical_visible_ode_of_t_derivative
    (visible : PS)
    (hvisible :
      d⁄dX ℂ visible =
        taylorPowerSeries analyticEndpointCoefficient 0 * visible) :
    coordinateDerivation sSeries (algebraMap PS LS visible) =
      algebraMap RF LS explicitRationalDifferential *
        algebraMap PS LS visible := by
  rw [coordinateDerivation_algebraMap, hvisible, map_mul,
    critical_connection_binding]
  have hcovariance := congrArg (algebraMap PS LS)
    pulledBack_explicit_connection_taylor
  rw [map_mul] at hcovariance
  rw [← hcovariance]
  field_simp [coordinateDerivative_ne_zero sSeries]

/-- The analytically continued terminal endpoint is a visible solution of
the exact rational critical connection in the Laurent chart. -/
theorem critical_selected_visible_ode :
    coordinateDerivation sSeries
        (algebraMap PS LS
          (complexify selectedEndpointT)) =
      algebraMap RF LS explicitRationalDifferential *
        algebraMap PS LS (complexify selectedEndpointT) := by
  apply critical_visible_ode_of_t_derivative
  rw [analyticEndpointCoefficient_taylor]
  exact complexify_selectedEndpointT_derivative

theorem critical_selected_visible_ne_zero :
    algebraMap PS LS (complexify selectedEndpointT) ≠ 0 := by
  have hpower : complexify selectedEndpointT ≠ 0 := by
    intro hzero
    have hconstant := congrArg PowerSeries.constantCoeff hzero
    rw [← coeff_zero_eq_constantCoeff, complexify,
      PowerSeries.coeff_map, coeff_zero_eq_constantCoeff,
      selectedEndpointT_constantCoeff] at hconstant
    simp at hconstant
  simpa only [map_zero] using
    (FaithfulSMul.algebraMap_injective PS LS).ne hpower

/-- Exact critical-coordinate and visible-connection certificate. -/
theorem critical_laurent_coordinate_source_terminal_certificate :
    sSeries.constantCoeff = 0 ∧ sSeries.coeff 1 ≠ 0 ∧
      algebraMap RF LS parameter = algebraMap PS LS sSeries ∧
      algebraMap RF LS xOfParameter =
        algebraMap PS LS (taylorPowerSeries analyticLocalX 0) ∧
      algebraMap RF LS explicitRationalDifferential =
        algebraMap PS LS
          (taylorPowerSeries
            (fun t => complexExplicitRationalDifferential (sOfT t)) 0) ∧
      ∀ coefficient : RF,
        algebraMap RF LS
            (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
              coefficient) =
          coordinateDerivation sSeries (algebraMap RF LS coefficient) := by
  exact ⟨sSeries_constantCoeff, sSeries_coeff_one_ne,
    critical_parameter_binding, critical_source_binding,
    critical_connection_binding,
    critical_coefficient_derivative_binding⟩

end

end AxiomPackJacobianCriticalLaurentCoordinate
