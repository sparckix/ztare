import Mathlib.Analysis.Analytic.Binomial
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxContinuation
import ZtareProofs.FormalAnalyticTaylorAlgebra

/-!
# Analytic realization of the selected terminal series

The terminal analytic functions use the principal binomial branch near zero.
Canonical Taylor algebra identifies their coefficient series with the
complexification of the previously constructed real formal endpoint.
-/

namespace AxiomPackJacobianCriticalPuiseuxAnalyticRealization

open Filter Metric Set PowerSeries
open FormalAnalyticTaylorAlgebra
open FormalLocalGerm
open AxiomPackJacobianCriticalPuiseuxSeries
open AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
open AxiomPackJacobianCriticalPuiseuxUniformization
open AxiomPackJacobianCriticalPuiseuxContinuation

/-- Coefficientwise extension from real to complex formal series. -/
noncomputable def complexify (series : ℝ⟦X⟧) : ℂ⟦X⟧ :=
  PowerSeries.map (algebraMap ℝ ℂ) series

@[simp]
theorem complexify_C (value : ℝ) :
    complexify (C value) = C (value : ℂ) := by
  simp [complexify, PowerSeries.map_C]

@[simp]
theorem complexify_X : complexify (X : ℝ⟦X⟧) = X := by
  simp [complexify, PowerSeries.map_X]

/-- The selected analytic branch of `sqrt(24 - 3 t²)` near zero. -/
noncomputable def analyticDiscriminantRoot (t : ℂ) : ℂ :=
  (2 * Real.sqrt 6 : ℂ) *
    (1 - t ^ 2 / 8) ^ (1 / 2 : ℂ)

theorem analyticDiscriminantRoot_analyticAt :
    AnalyticAt ℂ analyticDiscriminantRoot 0 := by
  have houter : AnalyticAt ℂ (fun z : ℂ => (1 + z) ^ (1 / 2 : ℂ)) 0 :=
    Complex.one_add_cpow_hasFPowerSeriesAt_zero.analyticAt
  have hinner : AnalyticAt ℂ (fun t : ℂ => -t ^ 2 / 8) 0 := by
    fun_prop
  have hcomp : AnalyticAt ℂ
      (fun t : ℂ => (1 + (-t ^ 2 / 8)) ^ (1 / 2 : ℂ)) 0 :=
    houter.comp_of_eq' hinner (by norm_num)
  simpa only [analyticDiscriminantRoot, Pi.mul_apply, sub_eq_add_neg,
    neg_div] using
    (analyticAt_const.mul hcomp : AnalyticAt ℂ
      ((fun _ : ℂ => (2 * Real.sqrt 6 : ℂ)) *
        fun t : ℂ => (1 + (-t ^ 2 / 8)) ^ (1 / 2 : ℂ)) 0)

@[simp]
theorem analyticDiscriminantRoot_zero :
    analyticDiscriminantRoot 0 = (2 * Real.sqrt 6 : ℂ) := by
  norm_num [analyticDiscriminantRoot]

theorem analyticDiscriminantRoot_square (t : ℂ) :
    analyticDiscriminantRoot t ^ 2 = 24 - 3 * t ^ 2 := by
  have hbase : ((1 - t ^ 2 / 8) ^ (1 / 2 : ℂ)) ^ (2 : ℕ) =
      1 - t ^ 2 / 8 := by
    simpa using Complex.cpow_nat_inv_pow (1 - t ^ 2 / 8) (by norm_num : (2 : ℕ) ≠ 0)
  have hsqrt : ((Real.sqrt 6 : ℝ) : ℂ) ^ 2 = 6 := by
    norm_cast
    exact Real.sq_sqrt (by norm_num)
  rw [analyticDiscriminantRoot, mul_pow, hbase]
  rw [show (2 * (Real.sqrt 6 : ℂ)) ^ 2 = 24 by
    rw [mul_pow, hsqrt]; norm_num]
  ring

theorem taylor_id_square :
    taylorPowerSeries (fun t : ℂ => t ^ 2) 0 = X ^ 2 := by
  have h := taylorPowerSeries_mul
    (𝕜 := ℂ) (center := (0 : ℂ))
    (f := fun t : ℂ => t) (g := fun t : ℂ => t)
    analyticAt_id analyticAt_id
  simpa only [Pi.mul_apply, pow_two, taylorPowerSeries_id_zero] using h

theorem analyticDiscriminantRoot_taylor_square :
    taylorPowerSeries analyticDiscriminantRoot 0 ^ 2 =
      C (24 : ℂ) - C 3 * X ^ 2 := by
  have hleft := taylorPowerSeries_mul
    analyticDiscriminantRoot_analyticAt analyticDiscriminantRoot_analyticAt
  have hright : AnalyticAt ℂ (fun t : ℂ => 24 - 3 * t ^ 2) 0 := by
    fun_prop
  have heq : (analyticDiscriminantRoot * analyticDiscriminantRoot) =ᶠ[
      nhds (0 : ℂ)] (fun t => 24 - 3 * t ^ 2) := by
    simpa only [Pi.mul_apply, pow_two] using
      (Filter.Eventually.of_forall analyticDiscriminantRoot_square)
  have hseries := taylorPowerSeries_eq_of_eventuallyEq
    (analyticDiscriminantRoot_analyticAt.mul
      analyticDiscriminantRoot_analyticAt) hright heq
  have hrightSeries :
      taylorPowerSeries (fun t : ℂ => 24 - 3 * t ^ 2) 0 =
        C (24 : ℂ) - C 3 * X ^ 2 := by
    have hsquare : AnalyticAt ℂ (fun t : ℂ => t ^ 2) 0 := by
      fun_prop
    have hthree :
        taylorPowerSeries (fun t : ℂ => 3 * t ^ 2) 0 =
          C 3 * X ^ 2 := by
      change taylorPowerSeries
          ((fun _ : ℂ => (3 : ℂ)) * (fun t : ℂ => t ^ 2)) 0 = _
      calc
        taylorPowerSeries
              ((fun _ : ℂ => (3 : ℂ)) * (fun t : ℂ => t ^ 2)) 0 =
            taylorPowerSeries (fun _ : ℂ => (3 : ℂ)) 0 *
              taylorPowerSeries (fun t : ℂ => t ^ 2) 0 :=
          taylorPowerSeries_mul analyticAt_const hsquare
        _ = C 3 * X ^ 2 := by
          rw [taylorPowerSeries_const, taylor_id_square]
    change taylorPowerSeries
        ((fun _ : ℂ => (24 : ℂ)) - (fun t : ℂ => 3 * t ^ 2)) 0 = _
    calc
      taylorPowerSeries
            ((fun _ : ℂ => (24 : ℂ)) - (fun t : ℂ => 3 * t ^ 2)) 0 =
          taylorPowerSeries (fun _ : ℂ => (24 : ℂ)) 0 -
            taylorPowerSeries (fun t : ℂ => 3 * t ^ 2) 0 :=
        taylorPowerSeries_sub analyticAt_const
          (analyticAt_const.mul hsquare)
      _ = C (24 : ℂ) - C 3 * X ^ 2 := by
        rw [taylorPowerSeries_const, hthree]
  simpa only [pow_two] using
    hleft.symm.trans (hseries.trans hrightSeries)

theorem complexified_selectedDiscriminantRoot_square :
    complexify selectedDiscriminantRootT ^ 2 =
      C (24 : ℂ) - C 3 * X ^ 2 := by
  have h := congrArg complexify selectedDiscriminantRootT_square
  simpa [complexify, map_pow, map_sub, map_mul,
    PowerSeries.map_C, PowerSeries.map_X] using h

theorem analyticDiscriminantRoot_taylor :
    taylorPowerSeries analyticDiscriminantRoot 0 =
      complexify selectedDiscriminantRootT := by
  apply square_root_eq_of_square_eq
  · rw [analyticDiscriminantRoot_taylor_square,
      complexified_selectedDiscriminantRoot_square]
  · rw [constantCoeff_taylorPowerSeries]
    rw [← coeff_zero_eq_constantCoeff, complexify,
      PowerSeries.coeff_map, coeff_zero_eq_constantCoeff,
      selectedDiscriminantRootT_constantCoeff]
    simp [analyticDiscriminantRoot_zero]

/-! ## Exact analytic connection in the ramified coordinate -/

/-- The analytic local coordinate `x=t²-2`. -/
noncomputable def analyticLocalX (t : ℂ) : ℂ := t ^ 2 - 2

/-- The common connection denominator after `x=t²-2`. -/
noncomputable def analyticConnectionDenominator (t : ℂ) : ℂ :=
  896 * analyticLocalX t ^ 3 * (analyticLocalX t - 4) *
    (analyticLocalX t ^ 2 - 4 * analyticLocalX t - 8)

/-- The radical quotient after its explicit ramification factor is removed. -/
noncomputable def analyticRadicalQuotient (t : ℂ) : ℂ :=
  (analyticLocalX t - 6) *
      (7 * analyticLocalX t ^ 3 - 42 * analyticLocalX t ^ 2 + 624) /
    analyticConnectionDenominator t

/-- The rational part of the selected velocity. -/
noncomputable def analyticRationalVelocity (t : ℂ) : ℂ :=
  (21 * analyticLocalX t ^ 6 - 124 * analyticLocalX t ^ 5 +
      456 * analyticLocalX t ^ 4 - 2048 * analyticLocalX t ^ 3 -
      6768 * analyticLocalX t ^ 2 + 22464 * analyticLocalX t + 44928) /
    analyticConnectionDenominator t

/-- The selected analytic critical velocity in the ramified coordinate. -/
noncomputable def analyticLocalVelocity (t : ℂ) : ℂ :=
  analyticRationalVelocity t +
    analyticRadicalQuotient t * analyticDiscriminantRoot t * t ^ 3

/-- Denominator of the selected radial logarithmic derivative. -/
noncomputable def analyticRadialDenominator (t : ℂ) : ℂ :=
  analyticLocalX t *
    (1 + 2 * analyticLocalX t * analyticLocalVelocity t)

/-- The selected analytic radial logarithmic derivative. -/
noncomputable def analyticRadialLogDerivative (t : ℂ) : ℂ :=
  (analyticRadialDenominator t)⁻¹

/-- Coefficient of the normalized endpoint ODE in the `t` coordinate. -/
noncomputable def analyticEndpointCoefficient (t : ℂ) : ℂ :=
  2 * t * analyticRadialLogDerivative t

/-- Polynomial numerator of the radical quotient. -/
noncomputable def radicalNumeratorPolynomial : Polynomial ℂ :=
  (Polynomial.X - Polynomial.C 6) *
    (Polynomial.C 7 * Polynomial.X ^ 3 -
      Polynomial.C 42 * Polynomial.X ^ 2 + Polynomial.C 624)

/-- Polynomial numerator of the rational velocity. -/
noncomputable def rationalNumeratorPolynomial : Polynomial ℂ :=
  Polynomial.C 21 * Polynomial.X ^ 6 -
    Polynomial.C 124 * Polynomial.X ^ 5 +
    Polynomial.C 456 * Polynomial.X ^ 4 -
    Polynomial.C 2048 * Polynomial.X ^ 3 -
    Polynomial.C 6768 * Polynomial.X ^ 2 +
    Polynomial.C 22464 * Polynomial.X + Polynomial.C 44928

/-- Polynomial connection denominator in the local coordinate. -/
noncomputable def connectionDenominatorPolynomial : Polynomial ℂ :=
  Polynomial.C 896 * Polynomial.X ^ 3 *
    (Polynomial.X - Polynomial.C 4) *
      (Polynomial.X ^ 2 - Polynomial.C 4 * Polynomial.X - Polynomial.C 8)

theorem connectionDenominatorPolynomial_eval (t : ℂ) :
    Polynomial.aeval (analyticLocalX t) connectionDenominatorPolynomial =
      analyticConnectionDenominator t := by
  simp [connectionDenominatorPolynomial, analyticConnectionDenominator]

theorem radicalNumeratorPolynomial_eval (t : ℂ) :
    Polynomial.aeval (analyticLocalX t) radicalNumeratorPolynomial =
      (analyticLocalX t - 6) *
        (7 * analyticLocalX t ^ 3 - 42 * analyticLocalX t ^ 2 + 624) := by
  simp [radicalNumeratorPolynomial]

theorem rationalNumeratorPolynomial_eval (t : ℂ) :
    Polynomial.aeval (analyticLocalX t) rationalNumeratorPolynomial =
      21 * analyticLocalX t ^ 6 - 124 * analyticLocalX t ^ 5 +
        456 * analyticLocalX t ^ 4 - 2048 * analyticLocalX t ^ 3 -
        6768 * analyticLocalX t ^ 2 + 22464 * analyticLocalX t + 44928 := by
  simp [rationalNumeratorPolynomial]

@[simp]
theorem analyticLocalX_zero : analyticLocalX 0 = -2 := by
  norm_num [analyticLocalX]

@[simp]
theorem analyticConnectionDenominator_zero :
    analyticConnectionDenominator 0 = 172032 := by
  norm_num [analyticConnectionDenominator, analyticLocalX]

@[simp]
theorem analyticRadicalQuotient_zero :
    analyticRadicalQuotient 0 = -25 / 1344 := by
  norm_num [analyticRadicalQuotient, analyticConnectionDenominator,
    analyticLocalX]

@[simp]
theorem analyticRationalVelocity_zero :
    analyticRationalVelocity 0 = 5 / 448 := by
  norm_num [analyticRationalVelocity, analyticConnectionDenominator,
    analyticLocalX]

@[simp]
theorem analyticRadialDenominator_zero :
    analyticRadialDenominator 0 = -107 / 56 := by
  norm_num [analyticRadialDenominator, analyticLocalVelocity,
    analyticDiscriminantRoot]

theorem analyticLocalX_analyticAt : AnalyticAt ℂ analyticLocalX 0 := by
  unfold analyticLocalX
  fun_prop

theorem analyticLocalX_taylor :
    taylorPowerSeries analyticLocalX 0 = X ^ 2 - C 2 := by
  change taylorPowerSeries
    ((fun t : ℂ => t ^ 2) - (fun _ : ℂ => (2 : ℂ))) 0 = _
  rw [taylorPowerSeries_sub (analyticAt_id.pow 2) analyticAt_const,
    taylor_id_square, taylorPowerSeries_const]

theorem analyticConnectionDenominator_analyticAt :
    AnalyticAt ℂ analyticConnectionDenominator 0 := by
  rw [← funext connectionDenominatorPolynomial_eval]
  exact analyticLocalX_analyticAt.aeval_polynomial
    connectionDenominatorPolynomial

theorem analyticConnectionDenominator_taylor :
    taylorPowerSeries analyticConnectionDenominator 0 =
      C 896 * (X ^ 2 - C 2) ^ 3 * ((X ^ 2 - C 2) - C 4) *
        ((X ^ 2 - C 2) ^ 2 - C 4 * (X ^ 2 - C 2) - C 8) := by
  rw [← funext connectionDenominatorPolynomial_eval,
    taylorPowerSeries_aeval_polynomial analyticLocalX_analyticAt,
    analyticLocalX_taylor]
  simp [connectionDenominatorPolynomial]

theorem analyticRadicalQuotient_analyticAt :
    AnalyticAt ℂ analyticRadicalQuotient 0 := by
  rw [show analyticRadicalQuotient = fun t =>
      Polynomial.aeval (analyticLocalX t) radicalNumeratorPolynomial /
        analyticConnectionDenominator t by
    funext t
    rw [radicalNumeratorPolynomial_eval]
    rfl]
  exact (analyticLocalX_analyticAt.aeval_polynomial
      radicalNumeratorPolynomial).div
    analyticConnectionDenominator_analyticAt (by norm_num)

theorem analyticRationalVelocity_analyticAt :
    AnalyticAt ℂ analyticRationalVelocity 0 := by
  rw [show analyticRationalVelocity = fun t =>
      Polynomial.aeval (analyticLocalX t) rationalNumeratorPolynomial /
        analyticConnectionDenominator t by
    funext t
    rw [rationalNumeratorPolynomial_eval]
    rfl]
  exact (analyticLocalX_analyticAt.aeval_polynomial
      rationalNumeratorPolynomial).div
    analyticConnectionDenominator_analyticAt (by norm_num)

theorem analyticRadicalQuotient_taylor :
    taylorPowerSeries analyticRadicalQuotient 0 =
      ((X ^ 2 - C 2) - C 6) *
          (C 7 * (X ^ 2 - C 2) ^ 3 -
            C 42 * (X ^ 2 - C 2) ^ 2 + C 624) *
        (C 896 * (X ^ 2 - C 2) ^ 3 * ((X ^ 2 - C 2) - C 4) *
          ((X ^ 2 - C 2) ^ 2 - C 4 * (X ^ 2 - C 2) - C 8))⁻¹ := by
  have hnum : AnalyticAt ℂ
      (fun t => Polynomial.aeval (analyticLocalX t)
        radicalNumeratorPolynomial) 0 :=
    analyticLocalX_analyticAt.aeval_polynomial radicalNumeratorPolynomial
  have hnumTaylor := taylorPowerSeries_aeval_polynomial
    analyticLocalX_analyticAt radicalNumeratorPolynomial
  rw [show analyticRadicalQuotient = fun t =>
      Polynomial.aeval (analyticLocalX t) radicalNumeratorPolynomial *
        (analyticConnectionDenominator t)⁻¹ by
    funext t
    rw [radicalNumeratorPolynomial_eval]
    rfl]
  change taylorPowerSeries
    ((fun t => Polynomial.aeval (analyticLocalX t)
        radicalNumeratorPolynomial) *
      (fun t => (analyticConnectionDenominator t)⁻¹)) 0 = _
  calc
    taylorPowerSeries
          ((fun t => Polynomial.aeval (analyticLocalX t)
              radicalNumeratorPolynomial) *
            (fun t => (analyticConnectionDenominator t)⁻¹)) 0 =
        taylorPowerSeries
            (fun t => Polynomial.aeval (analyticLocalX t)
              radicalNumeratorPolynomial) 0 *
          taylorPowerSeries
            (fun t => (analyticConnectionDenominator t)⁻¹) 0 :=
      taylorPowerSeries_mul hnum
        (analyticConnectionDenominator_analyticAt.inv (by norm_num))
    _ = _ := by
      rw [taylorPowerSeries_inv analyticConnectionDenominator_analyticAt
          (by norm_num),
        hnumTaylor, analyticLocalX_taylor,
        analyticConnectionDenominator_taylor]
      simp [radicalNumeratorPolynomial]

theorem analyticRationalVelocity_taylor :
    taylorPowerSeries analyticRationalVelocity 0 =
      (C 21 * (X ^ 2 - C 2) ^ 6 -
          C 124 * (X ^ 2 - C 2) ^ 5 +
          C 456 * (X ^ 2 - C 2) ^ 4 -
          C 2048 * (X ^ 2 - C 2) ^ 3 -
          C 6768 * (X ^ 2 - C 2) ^ 2 +
          C 22464 * (X ^ 2 - C 2) + C 44928) *
        (C 896 * (X ^ 2 - C 2) ^ 3 * ((X ^ 2 - C 2) - C 4) *
          ((X ^ 2 - C 2) ^ 2 - C 4 * (X ^ 2 - C 2) - C 8))⁻¹ := by
  have hnum : AnalyticAt ℂ
      (fun t => Polynomial.aeval (analyticLocalX t)
        rationalNumeratorPolynomial) 0 :=
    analyticLocalX_analyticAt.aeval_polynomial rationalNumeratorPolynomial
  have hnumTaylor := taylorPowerSeries_aeval_polynomial
    analyticLocalX_analyticAt rationalNumeratorPolynomial
  rw [show analyticRationalVelocity = fun t =>
      Polynomial.aeval (analyticLocalX t) rationalNumeratorPolynomial *
        (analyticConnectionDenominator t)⁻¹ by
    funext t
    rw [rationalNumeratorPolynomial_eval]
    rfl]
  change taylorPowerSeries
    ((fun t => Polynomial.aeval (analyticLocalX t)
        rationalNumeratorPolynomial) *
      (fun t => (analyticConnectionDenominator t)⁻¹)) 0 = _
  calc
    taylorPowerSeries
          ((fun t => Polynomial.aeval (analyticLocalX t)
              rationalNumeratorPolynomial) *
            (fun t => (analyticConnectionDenominator t)⁻¹)) 0 =
        taylorPowerSeries
            (fun t => Polynomial.aeval (analyticLocalX t)
              rationalNumeratorPolynomial) 0 *
          taylorPowerSeries
            (fun t => (analyticConnectionDenominator t)⁻¹) 0 :=
      taylorPowerSeries_mul hnum
        (analyticConnectionDenominator_analyticAt.inv (by norm_num))
    _ = _ := by
      rw [taylorPowerSeries_inv analyticConnectionDenominator_analyticAt
          (by norm_num),
        hnumTaylor, analyticLocalX_taylor,
        analyticConnectionDenominator_taylor]
      simp [rationalNumeratorPolynomial]

theorem analyticRadicalQuotient_taylor_named :
    taylorPowerSeries analyticRadicalQuotient 0 =
      complexify (PowerSeries.expand 2 (by norm_num)
        radicalQuotientU) := by
  have hconnection : constantCoeff connectionDenominatorU ≠ 0 := by
    norm_num [connectionDenominatorU, localXU]
  have hexpandedConnection :
      constantCoeff (PowerSeries.expand 2 (by norm_num)
        connectionDenominatorU) ≠ 0 := by
    rw [PowerSeries.constantCoeff_expand]
    exact hconnection
  rw [analyticRadicalQuotient_taylor]
  unfold radicalQuotientU
  rw [map_mul, map_mul,
    FormalLocalGerm.expand_inv 2 (by norm_num)
      connectionDenominatorU hconnection]
  unfold complexify
  rw [map_mul, map_mul,
    FormalLocalGerm.map_inv (algebraMap ℝ ℂ)
      (PowerSeries.expand 2 (by norm_num) connectionDenominatorU)
      hexpandedConnection]
  simp [connectionDenominatorU, localXU, PowerSeries.map_expand,
    PowerSeries.expand_C]

theorem analyticRationalVelocity_taylor_named :
    taylorPowerSeries analyticRationalVelocity 0 =
      complexify (PowerSeries.expand 2 (by norm_num)
        rationalVelocityU) := by
  have hconnection : constantCoeff connectionDenominatorU ≠ 0 := by
    norm_num [connectionDenominatorU, localXU]
  have hexpandedConnection :
      constantCoeff (PowerSeries.expand 2 (by norm_num)
        connectionDenominatorU) ≠ 0 := by
    rw [PowerSeries.constantCoeff_expand]
    exact hconnection
  rw [analyticRationalVelocity_taylor]
  unfold rationalVelocityU
  rw [map_mul,
    FormalLocalGerm.expand_inv 2 (by norm_num)
      connectionDenominatorU hconnection]
  unfold complexify
  rw [map_mul,
    FormalLocalGerm.map_inv (algebraMap ℝ ℂ)
      (PowerSeries.expand 2 (by norm_num) connectionDenominatorU)
      hexpandedConnection]
  simp [connectionDenominatorU, localXU, PowerSeries.map_expand,
    PowerSeries.expand_C]

theorem analyticLocalX_taylor_named :
    taylorPowerSeries analyticLocalX 0 = complexify localXT := by
  rw [analyticLocalX_taylor]
  simp [localXT, localXU, complexify, PowerSeries.map_expand,
    PowerSeries.expand_C]

theorem analyticLocalVelocity_analyticAt :
    AnalyticAt ℂ analyticLocalVelocity 0 := by
  have hx : AnalyticAt ℂ analyticLocalX 0 := analyticLocalX_analyticAt
  exact analyticRationalVelocity_analyticAt.add
    ((analyticRadicalQuotient_analyticAt.mul
      analyticDiscriminantRoot_analyticAt).mul
      (analyticAt_id.pow 3))

theorem analyticLocalVelocity_taylor :
    taylorPowerSeries analyticLocalVelocity 0 =
      complexify localVelocityT := by
  have hradicalProduct : AnalyticAt ℂ
      (fun t => analyticRadicalQuotient t *
        analyticDiscriminantRoot t * t ^ 3) 0 :=
    (analyticRadicalQuotient_analyticAt.mul
      analyticDiscriminantRoot_analyticAt).mul (analyticAt_id.pow 3)
  have hradicalProductTaylor :
      taylorPowerSeries
          (fun t => analyticRadicalQuotient t *
            analyticDiscriminantRoot t * t ^ 3) 0 =
        (complexify (PowerSeries.expand 2 (by norm_num)
            radicalQuotientU) * complexify selectedDiscriminantRootT) *
          X ^ 3 := by
    have htCube :
        taylorPowerSeries (fun t : ℂ => t ^ 3) 0 = X ^ 3 := by
      rw [taylorPowerSeries_pow
          (f := fun t : ℂ => t) analyticAt_id 3,
        taylorPowerSeries_id_zero]
    change taylorPowerSeries
      ((analyticRadicalQuotient * analyticDiscriminantRoot) *
        (fun t : ℂ => t ^ 3)) 0 = _
    calc
      taylorPowerSeries
            ((analyticRadicalQuotient * analyticDiscriminantRoot) *
              (fun t : ℂ => t ^ 3)) 0 =
          taylorPowerSeries
              (analyticRadicalQuotient * analyticDiscriminantRoot) 0 *
            taylorPowerSeries (fun t : ℂ => t ^ 3) 0 :=
        taylorPowerSeries_mul
          (analyticRadicalQuotient_analyticAt.mul
            analyticDiscriminantRoot_analyticAt) (analyticAt_id.pow 3)
      _ = _ := by
        rw [taylorPowerSeries_mul analyticRadicalQuotient_analyticAt
            analyticDiscriminantRoot_analyticAt,
          htCube,
          analyticRadicalQuotient_taylor_named,
          analyticDiscriminantRoot_taylor]
  unfold analyticLocalVelocity
  change taylorPowerSeries
    (analyticRationalVelocity +
      (fun t => analyticRadicalQuotient t *
        analyticDiscriminantRoot t * t ^ 3)) 0 = _
  rw [taylorPowerSeries_add analyticRationalVelocity_analyticAt
      hradicalProduct,
    analyticRationalVelocity_taylor_named, hradicalProductTaylor]
  simp [localVelocityT, radicalContributionT, complexify,
    PowerSeries.map_expand]

theorem analyticRadialDenominator_analyticAt :
    AnalyticAt ℂ analyticRadialDenominator 0 := by
  unfold analyticRadialDenominator
  exact analyticLocalX_analyticAt.mul
    (analyticAt_const.add
      ((analyticAt_const.mul analyticLocalX_analyticAt).mul
        analyticLocalVelocity_analyticAt))

theorem analyticRadialDenominator_taylor :
    taylorPowerSeries analyticRadialDenominator 0 =
      complexify radialDenominatorT := by
  have hinner : AnalyticAt ℂ
      (fun t => 1 + 2 * analyticLocalX t * analyticLocalVelocity t) 0 :=
    analyticAt_const.add
      ((analyticAt_const.mul analyticLocalX_analyticAt).mul
        analyticLocalVelocity_analyticAt)
  have htwoX :
      taylorPowerSeries (fun t => 2 * analyticLocalX t) 0 =
        C 2 * complexify localXT := by
    change taylorPowerSeries
      ((fun _ : ℂ => (2 : ℂ)) * analyticLocalX) 0 = _
    rw [taylorPowerSeries_mul analyticAt_const
      analyticLocalX_analyticAt, taylorPowerSeries_const,
      analyticLocalX_taylor_named]
  have hinnerTaylor :
      taylorPowerSeries
          (fun t => 1 + 2 * analyticLocalX t * analyticLocalVelocity t) 0 =
        1 + C 2 * complexify localXT * complexify localVelocityT := by
    have hproductTaylor :
        taylorPowerSeries
            ((fun t => 2 * analyticLocalX t) * analyticLocalVelocity) 0 =
          taylorPowerSeries (fun t => 2 * analyticLocalX t) 0 *
            taylorPowerSeries analyticLocalVelocity 0 :=
      taylorPowerSeries_mul
        (f := fun t => 2 * analyticLocalX t)
        (g := analyticLocalVelocity)
        (analyticAt_const.mul analyticLocalX_analyticAt)
        analyticLocalVelocity_analyticAt
    change taylorPowerSeries
      ((fun _ : ℂ => (1 : ℂ)) +
        ((fun t => 2 * analyticLocalX t) * analyticLocalVelocity)) 0 = _
    calc
      taylorPowerSeries
            ((fun _ : ℂ => (1 : ℂ)) +
              ((fun t => 2 * analyticLocalX t) *
                analyticLocalVelocity)) 0 =
          taylorPowerSeries (fun _ : ℂ => (1 : ℂ)) 0 +
            taylorPowerSeries
              ((fun t => 2 * analyticLocalX t) *
                analyticLocalVelocity) 0 :=
        taylorPowerSeries_add analyticAt_const
          ((analyticAt_const.mul analyticLocalX_analyticAt).mul
            analyticLocalVelocity_analyticAt)
      _ = _ := by
        rw [hproductTaylor,
          taylorPowerSeries_const, htwoX, analyticLocalVelocity_taylor]
        simp
  unfold analyticRadialDenominator
  change taylorPowerSeries
    (analyticLocalX *
      (fun t => 1 + 2 * analyticLocalX t * analyticLocalVelocity t)) 0 = _
  rw [taylorPowerSeries_mul analyticLocalX_analyticAt hinner,
    analyticLocalX_taylor_named, hinnerTaylor]
  simp [radialDenominatorT, complexify]

theorem analyticRadialLogDerivative_analyticAt :
    AnalyticAt ℂ analyticRadialLogDerivative 0 := by
  exact analyticRadialDenominator_analyticAt.inv (by norm_num)

theorem analyticRadialLogDerivative_taylor :
    taylorPowerSeries analyticRadialLogDerivative 0 =
      complexify radialLogarithmicDerivativeT := by
  rw [show analyticRadialLogDerivative =
      fun t => (analyticRadialDenominator t)⁻¹ by rfl,
    taylorPowerSeries_inv analyticRadialDenominator_analyticAt
      (by norm_num), analyticRadialDenominator_taylor]
  unfold radialLogarithmicDerivativeT complexify
  rw [FormalLocalGerm.map_inv (algebraMap ℝ ℂ)
    radialDenominatorT (by
      rw [radialDenominatorT_constantCoeff]
      norm_num)]

theorem analyticEndpointCoefficient_analyticAt :
    AnalyticAt ℂ analyticEndpointCoefficient 0 := by
  unfold analyticEndpointCoefficient
  exact (analyticAt_const.mul analyticAt_id).mul
    analyticRadialLogDerivative_analyticAt

theorem analyticEndpointCoefficient_taylor :
    taylorPowerSeries analyticEndpointCoefficient 0 =
      complexify selectedEndpointCoefficientT := by
  unfold analyticEndpointCoefficient
  have htwoT :
      taylorPowerSeries
          ((fun _ : ℂ => (2 : ℂ)) * (fun t : ℂ => t)) 0 =
        C 2 * X := by
    calc
      taylorPowerSeries
            ((fun _ : ℂ => (2 : ℂ)) * (fun t : ℂ => t)) 0 =
          taylorPowerSeries (fun _ : ℂ => (2 : ℂ)) 0 *
            taylorPowerSeries (fun t : ℂ => t) 0 :=
        taylorPowerSeries_mul
          (f := fun _ : ℂ => (2 : ℂ))
          (g := fun t : ℂ => t) analyticAt_const analyticAt_id
      _ = C 2 * X := by
        rw [taylorPowerSeries_const, taylorPowerSeries_id_zero]
  change taylorPowerSeries
    (((fun _ : ℂ => (2 : ℂ)) * (fun t : ℂ => t)) *
      analyticRadialLogDerivative) 0 = _
  calc
    taylorPowerSeries
          (((fun _ : ℂ => (2 : ℂ)) * (fun t : ℂ => t)) *
            analyticRadialLogDerivative) 0 =
        taylorPowerSeries
            ((fun _ : ℂ => (2 : ℂ)) * (fun t : ℂ => t)) 0 *
          taylorPowerSeries analyticRadialLogDerivative 0 :=
      taylorPowerSeries_mul (analyticAt_const.mul analyticAt_id)
        analyticRadialLogDerivative_analyticAt
    _ = _ := by
      rw [htwoT, analyticRadialLogDerivative_taylor]
      simp [selectedEndpointCoefficientT, complexify]

/-! ## Pullback of the continued uniformizing solution -/

/-- Inverse uniformizing parameter on the selected ramified chart. -/
noncomputable def qOfT (t : ℂ) : ℂ :=
  (t * analyticDiscriminantRoot t - 6) / (t ^ 2 - 2)

@[simp]
theorem qOfT_zero : qOfT 0 = 3 := by
  norm_num [qOfT, analyticDiscriminantRoot]

theorem qOfT_analyticAt : AnalyticAt ℂ qOfT 0 := by
  unfold qOfT
  exact ((analyticAt_id.mul analyticDiscriminantRoot_analyticAt).sub
      analyticAt_const).div
    ((analyticAt_id.pow 2).sub analyticAt_const) (by norm_num)

theorem analyticDiscriminantRoot_deriv_eventually :
    ∀ᶠ t in nhds (0 : ℂ),
      deriv analyticDiscriminantRoot t =
        -3 * t / analyticDiscriminantRoot t := by
  have hrootAnalytic :=
    analyticDiscriminantRoot_analyticAt.eventually_analyticAt
  have hrootNonzero : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      (by
        rw [analyticDiscriminantRoot_zero]
        exact mul_ne_zero (by norm_num)
          (Complex.ofReal_ne_zero.mpr
            (ne_of_gt (Real.sqrt_pos.2 (by norm_num)))))
  filter_upwards [hrootAnalytic, hrootNonzero] with t ht hn
  have hroot := ht.differentiableAt.hasDerivAt
  have hleft := hroot.pow 2
  have hright : HasDerivAt (fun z : ℂ => 24 - 3 * z ^ 2) (-6 * t) t := by
    convert (hasDerivAt_const t (24 : ℂ)).sub
      ((hasDerivAt_const t (3 : ℂ)).mul
        ((hasDerivAt_id t).pow 2)) using 1 <;>
      simp only [id_eq] <;>
      ring
  have hright' : HasDerivAt
      (fun z => analyticDiscriminantRoot z ^ 2) (-6 * t) t :=
    hright.congr_of_eventuallyEq
      (Filter.Eventually.of_forall analyticDiscriminantRoot_square)
  have hderivative := hleft.unique hright'
  rw [hroot.deriv]
  field_simp [hn]
  linear_combination (1 / 2 : ℂ) * hderivative

/-- Closed derivative formula for the inverse uniformizing parameter. -/
noncomputable def qOfTDerivativeFormula (t : ℂ) : ℂ :=
  ((analyticDiscriminantRoot t +
        t * (-3 * t / analyticDiscriminantRoot t)) * (t ^ 2 - 2) -
      (t * analyticDiscriminantRoot t - 6) * (2 * t)) /
    (t ^ 2 - 2) ^ 2

theorem qOfT_deriv_eventually :
    ∀ᶠ t in nhds (0 : ℂ),
      deriv qOfT t = qOfTDerivativeFormula t := by
  have hqAnalytic := qOfT_analyticAt.eventually_analyticAt
  have hrootAnalytic :=
    analyticDiscriminantRoot_analyticAt.eventually_analyticAt
  have hdenominatorAnalytic :
      AnalyticAt ℂ (fun t : ℂ => t ^ 2 - 2) 0 :=
    (analyticAt_id.pow 2).sub analyticAt_const
  have hdenominator : ∀ᶠ t in nhds (0 : ℂ), t ^ 2 - 2 ≠ 0 :=
    hdenominatorAnalytic.continuousAt.eventually_ne (by norm_num)
  filter_upwards [hqAnalytic, hrootAnalytic,
      analyticDiscriminantRoot_deriv_eventually, hdenominator] with
      t hqt hroot hrootDeriv hden
  have hrootAt := hroot.differentiableAt.hasDerivAt
  have hqFormula :=
    (((hasDerivAt_id t).mul hrootAt).sub_const 6).div
      (((hasDerivAt_id t).pow 2).sub_const 2) hden
  have hqAt : HasDerivAt qOfT (qOfTDerivativeFormula t) t := by
    unfold qOfT qOfTDerivativeFormula
    convert hqFormula using 1 <;>
      simp only [id_eq, Pi.pow_apply, Pi.mul_apply, one_mul,
        Nat.cast_ofNat] <;>
      rw [hrootDeriv] <;>
      norm_num
  exact hqAt.deriv

theorem qOfT_eventually_mem_right_disk :
    ∀ᶠ t in nhds (0 : ℂ), qOfT t ∈ ball (11 / 4) (1 / 3) := by
  have hthree : (3 : ℂ) ∈ ball (11 / 4) (1 / 3) :=
    selected_disk_chain_overlaps.2.2.2
  have hqmem : qOfT 0 ∈ ball (11 / 4) (1 / 3) := by
    simpa using hthree
  exact qOfT_analyticAt.continuousAt.tendsto
    (isOpen_ball.mem_nhds hqmem)

theorem uniformizing_log_derivative_identity
    (t : ℂ)
    (hroot : analyticDiscriminantRoot t ≠ 0)
    (htdenominator : t ^ 2 - 2 ≠ 0)
    (hqsub : qOfT t - 1 ≠ 0)
    (hflow : flowDenominator (qOfT t) ≠ 0)
    (hconnection : analyticConnectionDenominator t ≠ 0)
    (hradial : analyticRadialDenominator t ≠ 0) :
    qOfTDerivativeFormula t *
        ((qOfT t - 1)⁻¹ + regularizedLogDerivative (qOfT t)) =
      analyticEndpointCoefficient t := by
  unfold regularizedLogDerivative analyticEndpointCoefficient
    analyticRadialLogDerivative
  field_simp [hqsub, hflow, hradial]
  unfold qOfTDerivativeFormula qOfT regularizedFlowNumerator
    flowDenominator analyticRadialDenominator analyticLocalVelocity
    analyticRationalVelocity analyticRadicalQuotient analyticLocalX
  field_simp [hroot, htdenominator, hconnection]
  have hr2 := analyticDiscriminantRoot_square t
  have hr3 : analyticDiscriminantRoot t ^ 3 =
      analyticDiscriminantRoot t * (24 - 3 * t ^ 2) := by
    calc
      analyticDiscriminantRoot t ^ 3 =
          analyticDiscriminantRoot t * analyticDiscriminantRoot t ^ 2 := by
        ring
      _ = _ := by rw [hr2]
  have hr4 : analyticDiscriminantRoot t ^ 4 =
      (24 - 3 * t ^ 2) ^ 2 := by
    calc
      analyticDiscriminantRoot t ^ 4 =
          (analyticDiscriminantRoot t ^ 2) ^ 2 := by ring
      _ = _ := by rw [hr2]
  have hr5 : analyticDiscriminantRoot t ^ 5 =
      analyticDiscriminantRoot t * (24 - 3 * t ^ 2) ^ 2 := by
    calc
      analyticDiscriminantRoot t ^ 5 =
          analyticDiscriminantRoot t *
            (analyticDiscriminantRoot t ^ 2) ^ 2 := by ring
      _ = _ := by rw [hr2]
  have hr6 : analyticDiscriminantRoot t ^ 6 =
      (24 - 3 * t ^ 2) ^ 3 := by
    calc
      analyticDiscriminantRoot t ^ 6 =
          (analyticDiscriminantRoot t ^ 2) ^ 3 := by ring
      _ = _ := by rw [hr2]
  have hr7 : analyticDiscriminantRoot t ^ 7 =
      analyticDiscriminantRoot t * (24 - 3 * t ^ 2) ^ 3 := by
    calc
      analyticDiscriminantRoot t ^ 7 =
          analyticDiscriminantRoot t *
            (analyticDiscriminantRoot t ^ 2) ^ 3 := by ring
      _ = _ := by rw [hr2]
  have hr8 : analyticDiscriminantRoot t ^ 8 =
      (24 - 3 * t ^ 2) ^ 4 := by
    calc
      analyticDiscriminantRoot t ^ 8 =
          (analyticDiscriminantRoot t ^ 2) ^ 4 := by ring
      _ = _ := by rw [hr2]
  have hr9 : analyticDiscriminantRoot t ^ 9 =
      analyticDiscriminantRoot t * (24 - 3 * t ^ 2) ^ 4 := by
    calc
      analyticDiscriminantRoot t ^ 9 =
          analyticDiscriminantRoot t *
            (analyticDiscriminantRoot t ^ 2) ^ 4 := by ring
      _ = _ := by rw [hr2]
  unfold analyticConnectionDenominator analyticLocalX
  set_option maxRecDepth 100000 in
    ring_nf
  simp only [hr9, hr8, hr7, hr6, hr5, hr4, hr3, hr2]
  set_option maxRecDepth 100000 in
    ring

/-- Full logarithmic derivative before removing the simple zero at `q=1`. -/
noncomputable def fullLogDerivative (q : ℂ) : ℂ :=
  (q - 1)⁻¹ + regularizedLogDerivative q

/-- Pullback of the continued logarithmic derivative to the ramified chart. -/
noncomputable def pulledBackLogDerivative (t : ℂ) : ℂ :=
  deriv qOfT t * fullLogDerivative (qOfT t)

theorem pulledBackLogDerivative_eventually_eq :
    pulledBackLogDerivative =ᶠ[nhds (0 : ℂ)]
      analyticEndpointCoefficient := by
  have hrootNonzero : ∀ᶠ t in nhds (0 : ℂ),
      analyticDiscriminantRoot t ≠ 0 :=
    analyticDiscriminantRoot_analyticAt.continuousAt.eventually_ne
      (by
        rw [analyticDiscriminantRoot_zero]
        exact mul_ne_zero (by norm_num)
          (Complex.ofReal_ne_zero.mpr
            (ne_of_gt (Real.sqrt_pos.2 (by norm_num)))))
  have htDenominator : ∀ᶠ t in nhds (0 : ℂ), t ^ 2 - 2 ≠ 0 :=
    ((analyticAt_id.pow 2).sub
      (analyticAt_const : AnalyticAt ℂ (fun _ : ℂ => (2 : ℂ)) 0))
        |>.continuousAt.eventually_ne (by norm_num)
  have hconnection : ∀ᶠ t in nhds (0 : ℂ),
      analyticConnectionDenominator t ≠ 0 :=
    analyticConnectionDenominator_analyticAt.continuousAt.eventually_ne
      (by norm_num)
  have hradial : ∀ᶠ t in nhds (0 : ℂ),
      analyticRadialDenominator t ≠ 0 :=
    analyticRadialDenominator_analyticAt.continuousAt.eventually_ne
      (by norm_num)
  filter_upwards [qOfT_deriv_eventually,
      qOfT_eventually_mem_right_disk, hrootNonzero, htDenominator,
      hconnection, hradial] with t hderiv hqmem hroot htden hconnection hradial
  have hq_ne_one : qOfT t ≠ 1 := by
    intro heq
    rw [heq] at hqmem
    norm_num [mem_ball, dist_eq_norm, Complex.norm_real] at hqmem
  have hqsub : qOfT t - 1 ≠ 0 := sub_ne_zero.mpr hq_ne_one
  have hflow : flowDenominator (qOfT t) ≠ 0 :=
    flowDenominator_ne_zero_on_right_disk hqmem
  unfold pulledBackLogDerivative fullLogDerivative
  rw [hderiv]
  exact uniformizing_log_derivative_identity t hroot htden hqsub
    hflow hconnection hradial

/-- Terminal endpoint obtained from the three-disk continuation, normalized
to value one at the ramification point. -/
noncomputable def continuedTerminalEndpoint
    (continuation : SelectedRegularizedContinuation) (t : ℂ) : ℂ :=
  ((qOfT t - 1) * continuation.right (qOfT t)) /
    (2 * continuation.right 3)

theorem continuedTerminalEndpoint_analyticAt
    (continuation : SelectedRegularizedContinuation) :
    AnalyticAt ℂ (continuedTerminalEndpoint continuation) 0 := by
  have hrightAtThree : AnalyticAt ℂ continuation.right 3 :=
    continuation.analytic_right 3 selected_disk_chain_overlaps.2.2.2
  have hcomp : AnalyticAt ℂ (fun t => continuation.right (qOfT t)) 0 :=
    hrightAtThree.comp_of_eq' qOfT_analyticAt qOfT_zero
  unfold continuedTerminalEndpoint
  exact ((qOfT_analyticAt.sub analyticAt_const).mul hcomp).div_const

theorem continuedTerminalEndpoint_zero
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0) :
    continuedTerminalEndpoint continuation 0 = 1 := by
  simp only [continuedTerminalEndpoint, qOfT_zero]
  field_simp
  ring_nf

theorem continuedTerminalEndpoint_ode
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0) :
    deriv (continuedTerminalEndpoint continuation) =ᶠ[nhds (0 : ℂ)]
      fun t => pulledBackLogDerivative t *
        continuedTerminalEndpoint continuation t := by
  have hqAnalytic := qOfT_analyticAt.eventually_analyticAt
  filter_upwards [qOfT_eventually_mem_right_disk, hqAnalytic] with t ht hqt
  have hright := continuation.right_ode (qOfT t) ht
  have hq_ne_one : qOfT t ≠ 1 := by
    intro heq
    rw [heq] at ht
    norm_num [mem_ball, dist_eq_norm, Complex.norm_real] at ht
  have hq_sub_one : qOfT t - 1 ≠ 0 := sub_ne_zero.mpr hq_ne_one
  have hqDeriv : HasDerivAt qOfT (deriv qOfT t) t :=
    hqt.differentiableAt.hasDerivAt
  have hcomp := hright.comp t hqDeriv
  have hnumerator : HasDerivAt
      (fun z => (qOfT z - 1) * continuation.right (qOfT z))
      (deriv qOfT t * continuation.right (qOfT t) +
        (qOfT t - 1) *
          (regularizedLogDerivative (qOfT t) *
            continuation.right (qOfT t) * deriv qOfT t)) t := by
    convert (hqDeriv.sub_const 1).mul hcomp using 1 <;> ring
  have hendpoint := hnumerator.div_const
    (2 * continuation.right 3)
  change deriv
      (fun x => (qOfT x - 1) * continuation.right (qOfT x) /
        (2 * continuation.right 3)) t = _
  rw [hendpoint.deriv]
  unfold pulledBackLogDerivative fullLogDerivative
    continuedTerminalEndpoint
  field_simp [hq_ne_one, hq_sub_one, hterminal]

theorem continuedTerminalEndpoint_selected_ode
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0) :
    deriv (continuedTerminalEndpoint continuation) =ᶠ[nhds (0 : ℂ)]
      fun t => analyticEndpointCoefficient t *
        continuedTerminalEndpoint continuation t := by
  filter_upwards [continuedTerminalEndpoint_ode continuation hterminal,
      pulledBackLogDerivative_eventually_eq] with t hODE hcoefficient
  rw [hODE, hcoefficient]

theorem complexify_selectedEndpointT_derivative :
    d⁄dX ℂ (complexify selectedEndpointT) =
      complexify selectedEndpointCoefficientT *
        complexify selectedEndpointT := by
  unfold complexify
  rw [← FormalLocalGerm.map_derivative,
    selectedEndpointT_derivative]
  simp [selectedEndpointCoefficientT]

theorem normalizedEndpoint_complexify_selected :
    FormalPowerSeriesLinearODE.normalizedEndpoint
        (complexify selectedEndpointCoefficientT) =
      complexify selectedEndpointT := by
  apply FormalPowerSeriesLinearODE.linear_ode_solution_unique
  · rw [FormalPowerSeriesLinearODE.normalizedEndpoint_constantCoeff]
    rw [← coeff_zero_eq_constantCoeff, complexify,
      PowerSeries.coeff_map, coeff_zero_eq_constantCoeff,
      selectedEndpointT_constantCoeff]
    simp
  · exact FormalPowerSeriesLinearODE.normalizedEndpoint_derivative _
  · exact complexify_selectedEndpointT_derivative

theorem continuedTerminalEndpoint_taylor
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0) :
    taylorPowerSeries (continuedTerminalEndpoint continuation) 0 =
      complexify selectedEndpointT := by
  have htaylor := taylorPowerSeries_eq_normalizedEndpoint
    analyticEndpointCoefficient_analyticAt
    (continuedTerminalEndpoint_analyticAt continuation)
    (continuedTerminalEndpoint_zero continuation hterminal)
    (continuedTerminalEndpoint_selected_ode continuation hterminal)
  rw [analyticEndpointCoefficient_taylor] at htaylor
  exact htaylor.trans normalizedEndpoint_complexify_selected

/-- Spatial derivative factor in the terminal ramified chart. -/
noncomputable def continuedTerminalSpatialDerivativeFactor
    (continuation : SelectedRegularizedContinuation) (t : ℂ) : ℂ :=
  analyticRadialLogDerivative t *
    continuedTerminalEndpoint continuation t

theorem continuedTerminalSpatialDerivativeFactor_analyticAt
    (continuation : SelectedRegularizedContinuation) :
    AnalyticAt ℂ
      (continuedTerminalSpatialDerivativeFactor continuation) 0 := by
  exact analyticRadialLogDerivative_analyticAt.mul
    (continuedTerminalEndpoint_analyticAt continuation)

theorem continuedTerminalSpatialDerivativeFactor_taylor
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0) :
    taylorPowerSeries
        (continuedTerminalSpatialDerivativeFactor continuation) 0 =
      complexify (radialLogarithmicDerivativeT * selectedEndpointT) := by
  unfold continuedTerminalSpatialDerivativeFactor
  change taylorPowerSeries
    (analyticRadialLogDerivative *
      continuedTerminalEndpoint continuation) 0 = _
  rw [taylorPowerSeries_mul analyticRadialLogDerivative_analyticAt
      (continuedTerminalEndpoint_analyticAt continuation),
    analyticRadialLogDerivative_taylor,
    continuedTerminalEndpoint_taylor continuation hterminal]
  simp [complexify]

/-- Constructed analytic realization of the selected terminal endpoint. -/
theorem exists_selected_analytic_terminal_realization :
    ∃ continuation : SelectedRegularizedContinuation,
      continuation.right 3 ≠ 0 ∧
      AnalyticAt ℂ (continuedTerminalEndpoint continuation) 0 ∧
      continuedTerminalEndpoint continuation 0 = 1 ∧
      taylorPowerSeries (continuedTerminalEndpoint continuation) 0 =
        complexify selectedEndpointT := by
  obtain ⟨continuation, hterminal⟩ :=
    exists_selectedRegularizedContinuation
  exact ⟨continuation, hterminal,
    continuedTerminalEndpoint_analyticAt continuation,
    continuedTerminalEndpoint_zero continuation hterminal,
    continuedTerminalEndpoint_taylor continuation hterminal⟩

/-- Selected-chart realization with the base coordinate, endpoint, and Julia
spatial derivative factor all bound to their named formal series. -/
theorem selected_chart_realization_terminal_certificate :
    ∃ continuation : SelectedRegularizedContinuation,
      continuation.right 3 ≠ 0 ∧
      AnalyticAt ℂ (continuedTerminalEndpoint continuation) 0 ∧
      AnalyticAt ℂ
        (continuedTerminalSpatialDerivativeFactor continuation) 0 ∧
      taylorPowerSeries analyticLocalX 0 = complexify localXT ∧
      taylorPowerSeries (continuedTerminalEndpoint continuation) 0 =
        complexify selectedEndpointT ∧
      taylorPowerSeries
          (continuedTerminalSpatialDerivativeFactor continuation) 0 =
        complexify
          (radialLogarithmicDerivativeT * selectedEndpointT) := by
  obtain ⟨continuation, hterminal⟩ :=
    exists_selectedRegularizedContinuation
  exact ⟨continuation, hterminal,
    continuedTerminalEndpoint_analyticAt continuation,
    continuedTerminalSpatialDerivativeFactor_analyticAt continuation,
    analyticLocalX_taylor_named,
    continuedTerminalEndpoint_taylor continuation hterminal,
    continuedTerminalSpatialDerivativeFactor_taylor continuation hterminal⟩

end AxiomPackJacobianCriticalPuiseuxAnalyticRealization
