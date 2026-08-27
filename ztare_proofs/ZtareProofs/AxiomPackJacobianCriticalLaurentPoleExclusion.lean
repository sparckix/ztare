import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalLaurentCoordinate
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxJuliaAssembly
import ZtareProofs.FormalCriticalParameterizedTwoJuliaConfinement
import ZtareProofs.FormalLaurentReciprocalJuliaTransport

/-!
# Exclusion of the selected critical Laurent pole branch

The exact critical coordinate carrier and the reciprocal-Julia transport are
assembled here.  Once a selected analytic two-Julia carrier has the July
source and visible Taylor germs, its hidden Laurent pole is forced by the
all-order confinement theorem to be a polynomial equilibrium.  Polynomial
reversal excludes that conclusion.
-/

namespace AxiomPackJacobianCriticalLaurentPoleExclusion

open Polynomial PowerSeries
open scoped LaurentSeries

open AxiomPackJacobianCriticalLaurentCoordinate
open AxiomPackJacobianCriticalPuiseuxAnalyticRealization
open AxiomPackJacobianCriticalPuiseuxJuliaAssembly
open FormalAnalyticTwoJuliaAbelCollision
open FormalCriticalActualGeneratorEliminant
open FormalCriticalParameterizedTwoJuliaConfinement
open FormalLaurentInversePolynomialNonvanishing
open FormalLaurentReciprocalJuliaTransport
open FormalRatFuncLaurentTangentCarrier

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

noncomputable local instance criticalLaurentAlgebraInstance : Algebra RF LS :=
  criticalLaurentAlgebra

/-- Evaluation of a real generator through the critical rational coefficient
field agrees with direct evaluation of its complexification. -/
theorem liftRealGenerator_eval_binding
    (generator : ℝ[X]) (value : LS) :
    (liftRealGenerator generator).eval₂ (algebraMap RF LS) value =
      Polynomial.aeval value (complexifyPolynomial generator) := by
  unfold liftRealGenerator complexifyPolynomial
  rw [Polynomial.eval₂_map]
  simp only [Polynomial.aeval_def, Polynomial.eval₂_map]
  congr 1
  ext coefficient
  exact critical_real_constant_binding coefficient

theorem actualCriticalSourceEvaluation_binding
    (generator : ℝ[X]) :
    algebraMap RF LS (actualCriticalSourceEvaluation generator) =
      Polynomial.aeval (algebraMap RF LS xOfParameter)
        (complexifyPolynomial generator) := by
  unfold actualCriticalSourceEvaluation complexifyPolynomial
  rw [map_eval₂]
  simp only [Polynomial.aeval_def, Polynomial.eval₂_map]
  congr 1
  ext coefficient
  exact critical_real_constant_binding coefficient

/-- A selected two-Julia carrier with the exact July source and visible germs
cannot have a nonfinite hidden endpoint. -/
theorem selected_critical_laurent_pole_impossible
    (inner outer : ℝ[X])
    (hinner : inner ≠ 0) (houter : outer ≠ 0)
    (hinnerConstant : inner.coeff 0 = 0)
    (hinnerLinear : inner.coeff 1 = 0)
    (houterConstant : outer.coeff 0 = 0)
    (houterLinear : outer.coeff 1 = 0)
    (carrier : TwoJuliaAbelCarrier)
    (hfirstGenerator :
      carrier.firstGenerator = complexifyPolynomial inner)
    (hsecondGenerator :
      carrier.secondGenerator = complexifyPolynomial outer)
    (hsource :
      taylorPowerSeries carrier.source carrier.center =
        taylorPowerSeries analyticLocalX 0)
    (htarget :
      taylorPowerSeries carrier.target carrier.center =
        complexify selectedEndpointT)
    (hreciprocal :
      taylorPowerSeries carrier.reciprocal carrier.center ≠ 0) :
    False := by
  let reciprocal : PS :=
    taylorPowerSeries carrier.reciprocal carrier.center
  let source : PS := taylorPowerSeries carrier.source carrier.center
  let target : PS := taylorPowerSeries carrier.target carrier.center
  let visible : LS := algebraMap PS LS target
  let hidden : LS := (algebraMap PS LS reciprocal)⁻¹
  let dE : Derivation ℤ LS LS := coordinateDerivation sSeries
  obtain ⟨hinnerRow, houterRow⟩ :=
    carrier.laurent_julia_rows sSeries hreciprocal
  dsimp only at hinnerRow houterRow
  have hsourceLaurent :
      algebraMap PS LS source = algebraMap RF LS xOfParameter := by
    rw [show source = taylorPowerSeries analyticLocalX 0 by
      exact hsource]
    exact critical_source_binding.symm
  have htargetLaurent :
      algebraMap PS LS target =
        algebraMap PS LS (complexify selectedEndpointT) := by
    rw [show target = complexify selectedEndpointT by exact htarget]
  have hinnerEvaluationSource :
      Polynomial.aeval (algebraMap PS LS source)
          carrier.firstGenerator =
        algebraMap RF LS (actualCriticalSourceEvaluation inner) := by
    rw [hfirstGenerator, hsourceLaurent,
      actualCriticalSourceEvaluation_binding]
  have hinnerEvaluationHidden :
      Polynomial.aeval hidden carrier.firstGenerator =
        (liftRealGenerator inner).eval₂ (algebraMap RF LS) hidden := by
    rw [hfirstGenerator, liftRealGenerator_eval_binding]
  have houterEvaluationVisible :
      Polynomial.aeval (algebraMap PS LS target)
          carrier.secondGenerator =
        (liftRealGenerator outer).eval₂
          (algebraMap RF LS) visible := by
    rw [hsecondGenerator, liftRealGenerator_eval_binding]
  have houterEvaluationHidden :
      Polynomial.aeval hidden carrier.secondGenerator =
        (liftRealGenerator outer).eval₂ (algebraMap RF LS) hidden := by
    rw [hsecondGenerator, liftRealGenerator_eval_binding]
  have hsourceDerivative :
      dE (algebraMap PS LS source) =
        algebraMap RF LS xDerivativeOfParameter := by
    rw [hsourceLaurent]
    exact critical_source_derivative_binding.symm
  have htargetDerivative :
      dE (algebraMap PS LS target) =
        algebraMap RF LS explicitRationalDifferential *
          algebraMap PS LS target := by
    rw [htargetLaurent]
    exact critical_selected_visible_ode
  have hinnerJulia :
      algebraMap RF LS xDerivativeOfParameter *
          (liftRealGenerator inner).eval₂
            (algebraMap RF LS) hidden =
        dE hidden *
          algebraMap RF LS (actualCriticalSourceEvaluation inner) := by
    rw [← hsourceDerivative, ← hinnerEvaluationHidden,
      ← hinnerEvaluationSource]
    exact hinnerRow.symm
  have houterJulia :
      (liftRealGenerator outer).eval₂
            (algebraMap RF LS) visible * dE hidden =
        dE visible *
          (liftRealGenerator outer).eval₂
            (algebraMap RF LS) hidden := by
    rw [← houterEvaluationVisible, ← houterEvaluationHidden]
    simpa only [visible, dE] using houterRow
  have hcoefficientDerivation : ∀ coefficient : RF,
      algebraMap RF LS
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap RF LS coefficient) := by
    intro coefficient
    change algebraMap RF LS
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
          coefficient) = _
    exact critical_coefficient_derivative_binding coefficient
  have hvisibleODE :
      dE visible =
        algebraMap RF LS explicitRationalDifferential * visible := by
    simpa only [visible] using htargetDerivative
  have hvisibleNonzero : visible ≠ 0 := by
    rw [show visible = algebraMap PS LS (complexify selectedEndpointT) by
      exact htargetLaurent]
    exact critical_selected_visible_ne_zero
  have hzeros := parameterized_two_julia_force_common_generator_zeros
    inner outer hinner houter hinnerConstant hinnerLinear houterConstant
    houterLinear dE visible hidden hcoefficientDerivation hvisibleODE
    hinnerJulia houterJulia hvisibleNonzero
  have hcomplexInner : complexifyPolynomial inner ≠ 0 := by
    exact (Polynomial.map_ne_zero_iff Complex.ofReal_injective).2 hinner
  have hreciprocalConstant : reciprocal.constantCoeff = 0 := by
    simp [reciprocal, carrier.reciprocal_zero]
  have hpoleNonzero := polynomial_aeval_inverse_ne_zero reciprocal
    hreciprocal hreciprocalConstant (complexifyPolynomial inner)
    hcomplexInner
  apply hpoleNonzero
  rw [← liftRealGenerator_eval_binding]
  exact hzeros.1

/-- Aggregated selected-branch certificate. -/
theorem critical_laurent_pole_exclusion_terminal_certificate :
    ∀ (inner outer : ℝ[X]),
      inner ≠ 0 → outer ≠ 0 →
      inner.coeff 0 = 0 → inner.coeff 1 = 0 →
      outer.coeff 0 = 0 → outer.coeff 1 = 0 →
      ∀ carrier : TwoJuliaAbelCarrier,
        carrier.firstGenerator = complexifyPolynomial inner →
        carrier.secondGenerator = complexifyPolynomial outer →
        taylorPowerSeries carrier.source carrier.center =
          taylorPowerSeries analyticLocalX 0 →
        taylorPowerSeries carrier.target carrier.center =
          complexify selectedEndpointT →
        taylorPowerSeries carrier.reciprocal carrier.center ≠ 0 →
        False := by
  intro inner outer hinner houter hinnerConstant hinnerLinear
    houterConstant houterLinear carrier hfirstGenerator hsecondGenerator
    hsource htarget hreciprocal
  exact selected_critical_laurent_pole_impossible inner outer hinner houter
    hinnerConstant hinnerLinear houterConstant houterLinear carrier
    hfirstGenerator hsecondGenerator hsource htarget hreciprocal

end

end AxiomPackJacobianCriticalLaurentPoleExclusion
