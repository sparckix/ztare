import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalBaseLaurentCoordinate
import ZtareProofs.FormalAutonomousFlowCompositionJulia
import ZtareProofs.FormalCriticalParameterizedTwoJuliaConfinement
import ZtareProofs.FormalTangentSubstitutionInjectivity

/-!
# Exclusion of normalized autonomous two-flow factorizations at the base germ

The exact July source and visible germs are localized at the original
normalization point.  Julia's identities for two normalized autonomous
time-one substitutions then feed the complete critical differential-germ
eliminant.  Confinement forces the inner generator to vanish at the hidden
germ, while injectivity of the two substitutions proves that evaluation is
nonzero.
-/

namespace AxiomPackJacobianCriticalBaseTwoFlowExclusion

open Polynomial PowerSeries
open scoped LaurentSeries

open AxiomPackJacobianCriticalBaseLaurentCoordinate
open FormalAutonomousFlow
open FormalAutonomousFlowCompositionJulia
open FormalCriticalActualGeneratorEliminant
open FormalCriticalConnectionRationalization
open FormalCriticalParameterizedTwoJuliaConfinement
open FormalRatFuncLaurentTangentCarrier
open FormalTangentSubstitutionInjectivity

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

noncomputable local instance criticalBaseLaurentAlgebraInstance :
    Algebra RF LS := criticalBaseLaurentAlgebra

/-- Coefficientwise complexification of a real polynomial. -/
def baseComplexifyPolynomial (generator : ℝ[X]) : ℂ[X] :=
  generator.map (algebraMap ℝ ℂ)

/-- Evaluation commutes with the canonical power-series-to-Laurent map. -/
theorem algebraMap_aeval_binding (generator : ℂ[X]) (series : PS) :
    algebraMap PS LS (Polynomial.aeval series generator) =
      Polynomial.aeval (algebraMap PS LS series) generator := by
  have hcommute :
      (algebraMap ℂ LS).comp (RingHom.id ℂ) =
        (algebraMap PS LS).comp (algebraMap ℂ PS) := by
    apply RingHom.ext
    intro constant
    simpa only [RingHom.comp_apply, RingHom.id_apply] using
      (algebraMap_powerSeries_C constant).symm
  have hmap := Polynomial.map_aeval_eq_aeval_map
    (R := ℂ) (S := PS) (T := ℂ) (U := LS)
    (φ := RingHom.id ℂ) (ψ := algebraMap PS LS)
    hcommute generator series
  simpa only [Polynomial.map_id] using hmap

/-- A coerced polynomial substituted in power series and then localized is
the same polynomial evaluated in the Laurent field. -/
theorem algebraMap_subst_coe_binding
    (generator : ℂ[X]) (series : PS) (hseries : HasSubst series) :
    algebraMap PS LS ((generator : PS).subst series) =
      Polynomial.aeval (algebraMap PS LS series) generator := by
  rw [PowerSeries.subst_coe hseries generator, algebraMap_aeval_binding]

set_option maxHeartbeats 100000 in
-- This bound isolates coefficient-field transport from downstream search.
/- Evaluation of a real generator through the critical rational coefficient
field agrees with evaluation of its complexification. -/
theorem liftRealGenerator_eval_binding
    (generator : ℝ[X]) (value : LS) :
    (liftRealGenerator generator).eval₂ (algebraMap RF LS) value =
      Polynomial.aeval value (baseComplexifyPolynomial generator) := by
  unfold liftRealGenerator baseComplexifyPolynomial
  rw [Polynomial.eval₂_map]
  simp only [Polynomial.aeval_def, Polynomial.eval₂_map]
  congr 1
  apply RingHom.ext
  intro coefficient
  exact base_real_constant_binding coefficient

set_option maxHeartbeats 100000 in
-- This bound isolates evaluation naturality from downstream search.
theorem actualCriticalSourceEvaluation_binding
    (generator : ℝ[X]) :
    algebraMap RF LS (actualCriticalSourceEvaluation generator) =
      Polynomial.aeval (algebraMap RF LS xOfParameter)
        (baseComplexifyPolynomial generator) := by
  calc
    algebraMap RF LS (actualCriticalSourceEvaluation generator) =
        algebraMap RF LS
          ((liftRealGenerator generator).eval xOfParameter) := by
            simp only [actualCriticalSourceEvaluation, liftRealGenerator,
              Polynomial.eval_map]
    _ = (liftRealGenerator generator).eval₂ (algebraMap RF LS)
          (algebraMap RF LS xOfParameter) := by
            rw [Polynomial.eval₂_at_apply]
    _ = Polynomial.aeval (algebraMap RF LS xOfParameter)
          (baseComplexifyPolynomial generator) :=
            liftRealGenerator_eval_binding generator _

/-- No nonzero series is killed by substitution with the exact tangent
source germ. -/
theorem baseSource_subst_ne_zero (germ : PS) (hgerm : germ ≠ 0) :
    germ.subst baseSource ≠ 0 := by
  intro hzero
  apply hgerm
  apply subst_injective_of_invertible_linear
    baseSource baseSource_constantCoeff
  have hsubstZero : (0 : PS).subst baseSource = 0 := by
    rw [← PowerSeries.coe_substAlgHom
      (HasSubst.of_constantCoeff_zero' baseSource_constantCoeff)]
    exact map_zero _
  exact hzero.trans hsubstZero.symm

/-- Multiplying a mapped derivative row by the inverse coordinate derivative
turns both ordinary derivatives into the coordinate derivation. -/
theorem coordinateDerivation_transport_row
    (coordinate first second : PS) (left right : LS)
    (hrow :
      algebraMap PS LS (d⁄dX ℂ first) * left =
        algebraMap PS LS (d⁄dX ℂ second) * right) :
    coordinateDerivation coordinate (algebraMap PS LS first) * left =
      coordinateDerivation coordinate (algebraMap PS LS second) * right := by
  rw [coordinateDerivation_algebraMap, coordinateDerivation_algebraMap]
  calc
    ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ first)) * left =
        (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (algebraMap PS LS (d⁄dX ℂ first) * left) := by ring
    _ = (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (algebraMap PS LS (d⁄dX ℂ second) * right) := by rw [hrow]
    _ = ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ second)) * right := by ring

/-- Right-oriented version for the outer Julia row. -/
theorem coordinateDerivation_transport_right_row
    (coordinate first second : PS) (left right : LS)
    (hrow :
      left * algebraMap PS LS (d⁄dX ℂ first) =
        algebraMap PS LS (d⁄dX ℂ second) * right) :
    left * coordinateDerivation coordinate (algebraMap PS LS first) =
      coordinateDerivation coordinate (algebraMap PS LS second) * right := by
  rw [coordinateDerivation_algebraMap, coordinateDerivation_algebraMap]
  calc
    left * ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ first)) =
        (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (left * algebraMap PS LS (d⁄dX ℂ first)) := by ring
    _ = (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          (algebraMap PS LS (d⁄dX ℂ second) * right) := by rw [hrow]
    _ = ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ second)) * right := by ring

set_option maxHeartbeats 500000 in
-- This bound detects accidental elaboration across the scalar-tower bridge.
/- The inner autonomous flow supplies the first critical Julia row after
localization at the original normalization point. -/
theorem critical_base_inner_julia
    (inner : ℝ[X]) (innerEndpoint : PS)
    (innerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint) :
    let hiddenPS := PowerSeries.subst baseSource innerEndpoint
    let hidden := algebraMap PS LS hiddenPS
    algebraMap RF LS xDerivativeOfParameter *
        (liftRealGenerator inner).eval₂ (algebraMap RF LS) hidden =
      coordinateDerivation baseTangentCoordinate hidden *
        algebraMap RF LS (actualCriticalSourceEvaluation inner) := by
  let innerGenerator : PS :=
    ((baseComplexifyPolynomial inner : ℂ[X]) : PS)
  let hiddenPS : PS := PowerSeries.subst baseSource innerEndpoint
  let hidden : LS := algebraMap PS LS hiddenPS
  have hsource : HasSubst baseSource :=
    HasSubst.of_constantCoeff_zero' baseSource_constantCoeff
  have hhiddenConstant : hiddenPS.constantCoeff = 0 := by
    exact PowerSeries.constantCoeff_subst_eq_zero baseSource_constantCoeff
      innerEndpoint innerFlow.endpoint_constantCoeff
  have hhidden : HasSubst hiddenPS :=
    HasSubst.of_constantCoeff_zero' hhiddenConstant
  have hinnerRow := parameterized_julia innerGenerator innerEndpoint
    baseSource innerFlow hsource
  have hmappedInnerRow := congrArg (algebraMap PS LS) hinnerRow
  simp only [map_mul] at hmappedInnerRow
  rw [algebraMap_subst_coe_binding
      (baseComplexifyPolynomial inner) hiddenPS hhidden,
    algebraMap_subst_coe_binding
      (baseComplexifyPolynomial inner) baseSource hsource]
    at hmappedInnerRow
  have hsourceDerivative :
      coordinateDerivation baseTangentCoordinate
          (algebraMap PS LS baseSource) =
        algebraMap RF LS xDerivativeOfParameter := by
    rw [← base_source_binding]
    exact base_source_derivative_binding.symm
  have hsourceEvaluation :
      Polynomial.aeval (algebraMap PS LS baseSource)
          (baseComplexifyPolynomial inner) =
        algebraMap RF LS (actualCriticalSourceEvaluation inner) := by
    rw [← base_source_binding]
    exact (actualCriticalSourceEvaluation_binding inner).symm
  have hinnerHiddenEvaluation :
      Polynomial.aeval hidden (baseComplexifyPolynomial inner) =
        (liftRealGenerator inner).eval₂ (algebraMap RF LS) hidden := by
    exact (liftRealGenerator_eval_binding inner hidden).symm
  have htransported := coordinateDerivation_transport_row
    baseTangentCoordinate baseSource hiddenPS
    (Polynomial.aeval hidden (baseComplexifyPolynomial inner))
    (Polynomial.aeval (algebraMap PS LS baseSource)
      (baseComplexifyPolynomial inner)) hmappedInnerRow
  rw [hsourceDerivative, hinnerHiddenEvaluation,
    hsourceEvaluation] at htransported
  exact htransported

set_option maxHeartbeats 100000 in
-- This bound detects accidental elaboration across the outer transport.
/- The outer autonomous flow supplies the second critical Julia row whenever
its hidden-source endpoint is the exact visible germ. -/
theorem critical_base_outer_julia
    (outer : ℝ[X]) (hiddenPS outerEndpoint : PS)
    (hhiddenConstant : hiddenPS.constantCoeff = 0)
    (outerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial outer : ℂ[X]) : PS) outerEndpoint)
    (hvisible : PowerSeries.subst hiddenPS outerEndpoint = baseVisible) :
    let hidden := algebraMap PS LS hiddenPS
    let visible := algebraMap PS LS baseVisible
    (liftRealGenerator outer).eval₂ (algebraMap RF LS) visible *
        coordinateDerivation baseTangentCoordinate hidden =
      coordinateDerivation baseTangentCoordinate visible *
        (liftRealGenerator outer).eval₂ (algebraMap RF LS) hidden := by
  let outerGenerator : PS :=
    ((baseComplexifyPolynomial outer : ℂ[X]) : PS)
  let visiblePS : PS := PowerSeries.subst hiddenPS outerEndpoint
  let hidden : LS := algebraMap PS LS hiddenPS
  let visible : LS := algebraMap PS LS baseVisible
  have hhidden : HasSubst hiddenPS :=
    HasSubst.of_constantCoeff_zero' hhiddenConstant
  have hvisibleConstant : visiblePS.constantCoeff = 0 := by
    rw [show visiblePS = baseVisible by exact hvisible]
    simp [baseVisible, baseRegularizedEndpoint_constantCoeff]
  have hvisibleHasSubst : HasSubst visiblePS :=
    HasSubst.of_constantCoeff_zero' hvisibleConstant
  have houterRow := parameterized_julia outerGenerator outerEndpoint
    hiddenPS outerFlow hhidden
  have hmappedOuterRow := congrArg (algebraMap PS LS) houterRow
  simp only [map_mul] at hmappedOuterRow
  rw [algebraMap_subst_coe_binding
      (baseComplexifyPolynomial outer) visiblePS hvisibleHasSubst,
    algebraMap_subst_coe_binding
      (baseComplexifyPolynomial outer) hiddenPS hhidden]
    at hmappedOuterRow
  have hvisibleMap : algebraMap PS LS visiblePS = visible := by
    simpa only [visiblePS, visible] using
      congrArg (algebraMap PS LS) hvisible
  rw [hvisibleMap] at hmappedOuterRow
  have hmappedOuterRow' :
      Polynomial.aeval visible (baseComplexifyPolynomial outer) *
          algebraMap PS LS (d⁄dX ℂ hiddenPS) =
        algebraMap PS LS (d⁄dX ℂ visiblePS) *
          Polynomial.aeval hidden (baseComplexifyPolynomial outer) := by
    rw [mul_comm]
    simpa only [visiblePS, hidden] using hmappedOuterRow
  have htransported := coordinateDerivation_transport_right_row
    baseTangentCoordinate hiddenPS visiblePS
    (Polynomial.aeval visible (baseComplexifyPolynomial outer))
    (Polynomial.aeval hidden (baseComplexifyPolynomial outer))
    hmappedOuterRow'
  rw [show visiblePS = baseVisible by simpa only [visiblePS] using hvisible,
    (liftRealGenerator_eval_binding outer visible).symm,
    (liftRealGenerator_eval_binding outer hidden).symm] at htransported
  exact htransported

set_option maxHeartbeats 500000 in
-- This bound keeps the power-series injectivity argument local.
/- The inner generator remains nonzero after its endpoint and the exact
source germ are composed. -/
theorem critical_base_inner_hidden_aeval_ne_zero
    (inner : ℝ[X]) (hinner : inner ≠ 0) (innerEndpoint : PS)
    (innerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint) :
    Polynomial.aeval (PowerSeries.subst baseSource innerEndpoint)
      (baseComplexifyPolynomial inner) ≠ 0 := by
  let hiddenPS : PS := PowerSeries.subst baseSource innerEndpoint
  have hsource : HasSubst baseSource :=
    HasSubst.of_constantCoeff_zero' baseSource_constantCoeff
  have hhiddenConstant : hiddenPS.constantCoeff = 0 := by
    exact PowerSeries.constantCoeff_subst_eq_zero baseSource_constantCoeff
      innerEndpoint innerFlow.endpoint_constantCoeff
  have hcomplexInner : baseComplexifyPolynomial inner ≠ 0 := by
    exact (Polynomial.map_ne_zero_iff Complex.ofReal_injective).2 hinner
  have hendpointDerivativeConstant :
      (d⁄dX ℂ innerEndpoint).constantCoeff = 1 := by
    rw [← PowerSeries.coeff_zero_eq_constantCoeff_apply,
      PowerSeries.coeff_derivative]
    norm_num [innerFlow.endpoint_coeff_one]
  have hsubstitutedDerivativeConstant :
      PowerSeries.constantCoeff (PowerSeries.subst baseSource
        (d⁄dX ℂ innerEndpoint)) = 1 := by
    let c := (d⁄dX ℂ innerEndpoint).constantCoeff
    have htailConstant :
        ((d⁄dX ℂ innerEndpoint) - PowerSeries.C c).constantCoeff = 0 := by
      simp [c]
    have htailAfterSubstitution := PowerSeries.constantCoeff_subst_eq_zero
      baseSource_constantCoeff
      ((d⁄dX ℂ innerEndpoint) - PowerSeries.C c) htailConstant
    rw [PowerSeries.subst_sub hsource] at htailAfterSubstitution
    have heq := sub_eq_zero.mp htailAfterSubstitution
    have heqConstant :
        MvPowerSeries.constantCoeff
            (PowerSeries.subst baseSource (d⁄dX ℂ innerEndpoint)) =
          MvPowerSeries.constantCoeff
            (PowerSeries.subst baseSource (PowerSeries.C c)) := by
      rw [← MvPowerSeries.coeff_zero_eq_constantCoeff_apply,
        ← MvPowerSeries.coeff_zero_eq_constantCoeff_apply]
      exact heq
    rw [PowerSeries.constantCoeff_eq]
    calc
      MvPowerSeries.constantCoeff
          (PowerSeries.subst baseSource (d⁄dX ℂ innerEndpoint)) =
        MvPowerSeries.constantCoeff
          (PowerSeries.subst baseSource (PowerSeries.C c)) := heqConstant
      _ = 1 := by
        have hc : c = 1 := by
          simpa only [c] using hendpointDerivativeConstant
        rw [hc, PowerSeries.subst_C]
        rfl
  have hchain := PowerSeries.derivative_subst ℂ hsource
    (f := innerEndpoint)
  have hchainCoefficient := congrArg (PowerSeries.coeff 0) hchain
  have hhiddenLinear : hiddenPS.coeff 1 = -3 := by
    simpa [hiddenPS, PowerSeries.coeff_derivative,
      PowerSeries.coeff_mul, Finset.antidiagonal,
      hsubstitutedDerivativeConstant, baseSource_coeff_one]
      using hchainCoefficient
  have hhiddenLinearNe : hiddenPS.coeff 1 ≠ 0 := by
    rw [hhiddenLinear]
    norm_num
  letI : Invertible (hiddenPS.coeff 1) :=
    invertibleOfNonzero hhiddenLinearNe
  exact polynomial_aeval_ne_zero_of_invertible_linear hiddenPS
    hhiddenConstant (baseComplexifyPolynomial inner) hcomplexInner

set_option maxHeartbeats 100000 in
-- This bound isolates Laurent localization from substitution injectivity.
/- The inner generator cannot vanish in the Laurent field at the hidden
endpoint produced by its normalized time-one substitution. -/
theorem critical_base_inner_hidden_evaluation_ne_zero
    (inner : ℝ[X]) (hinner : inner ≠ 0) (innerEndpoint : PS)
    (innerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint) :
    let hidden := algebraMap PS LS
      (PowerSeries.subst baseSource innerEndpoint)
    (liftRealGenerator inner).eval₂ (algebraMap RF LS) hidden ≠ 0 := by
  let hiddenPS : PS := PowerSeries.subst baseSource innerEndpoint
  let hidden : LS := algebraMap PS LS hiddenPS
  have hhiddenEvaluationPS :
      Polynomial.aeval hiddenPS (baseComplexifyPolynomial inner) ≠ 0 := by
    exact critical_base_inner_hidden_aeval_ne_zero inner hinner
      innerEndpoint innerFlow
  have hhiddenEvaluationLS :
      Polynomial.aeval hidden (baseComplexifyPolynomial inner) ≠ 0 := by
    rw [← algebraMap_aeval_binding]
    simpa only [map_zero] using
      (FaithfulSMul.algebraMap_injective PS LS).ne hhiddenEvaluationPS
  change (liftRealGenerator inner).eval₂ (algebraMap RF LS) hidden ≠ 0
  rw [liftRealGenerator_eval_binding]
  exact hhiddenEvaluationLS

set_option maxHeartbeats 100000 in
-- The terminal theorem only composes the preceding bounded certificates.
/- The exact July base germ cannot factor through two nonzero normalized
autonomous polynomial time-one substitutions. -/
theorem critical_base_two_flow_impossible
    (inner outer : ℝ[X])
    (hinner : inner ≠ 0) (houter : outer ≠ 0)
    (hinnerConstant : inner.coeff 0 = 0)
    (hinnerLinear : inner.coeff 1 = 0)
    (houterConstant : outer.coeff 0 = 0)
    (houterLinear : outer.coeff 1 = 0)
    (innerEndpoint outerEndpoint : PS)
    (innerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint)
    (outerFlow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial outer : ℂ[X]) : PS) outerEndpoint)
    (hcomposition :
      PowerSeries.subst baseSource
          (PowerSeries.subst innerEndpoint outerEndpoint) =
        baseVisible) :
    False := by
  let hiddenPS : PS := PowerSeries.subst baseSource innerEndpoint
  let hidden : LS := algebraMap PS LS hiddenPS
  let visible : LS := algebraMap PS LS baseVisible
  let dE := coordinateDerivation baseTangentCoordinate
  have hsource : HasSubst baseSource :=
    HasSubst.of_constantCoeff_zero' baseSource_constantCoeff
  have hhiddenConstant : hiddenPS.constantCoeff = 0 := by
    exact PowerSeries.constantCoeff_subst_eq_zero baseSource_constantCoeff
      innerEndpoint innerFlow.endpoint_constantCoeff
  have hvisiblePS : PowerSeries.subst hiddenPS outerEndpoint = baseVisible :=
    (composition_subst innerEndpoint outerEndpoint baseSource
      innerFlow.hasSubst hsource).symm.trans hcomposition
  have hinnerJulia := critical_base_inner_julia inner innerEndpoint innerFlow
  have houterJulia := critical_base_outer_julia outer hiddenPS outerEndpoint
    hhiddenConstant outerFlow hvisiblePS
  have hcoefficientDerivation : ∀ coefficient : RF,
      algebraMap RF LS
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap RF LS coefficient) := by
    intro coefficient
    simpa only [dE] using
      (base_coefficient_derivative_binding coefficient)
  have hvisibleODE :
      dE visible =
        algebraMap RF LS explicitRationalDifferential * visible := by
    simpa only [dE, visible] using baseVisible_critical_ode
  have hvisibleNonzero : visible ≠ 0 := baseVisible_ne_zero
  have hzeros := parameterized_two_julia_force_common_generator_zeros
    inner outer hinner houter hinnerConstant hinnerLinear houterConstant
    houterLinear dE visible hidden hcoefficientDerivation hvisibleODE
    hinnerJulia houterJulia hvisibleNonzero
  apply critical_base_inner_hidden_evaluation_ne_zero
    inner hinner innerEndpoint innerFlow
  exact hzeros.1

/-- Aggregated all-degree two-flow exclusion certificate. -/
theorem critical_base_two_flow_exclusion_terminal_certificate :
    ∀ (inner outer : ℝ[X]),
      inner ≠ 0 → outer ≠ 0 →
      inner.coeff 0 = 0 → inner.coeff 1 = 0 →
      outer.coeff 0 = 0 → outer.coeff 1 = 0 →
      ∀ (innerEndpoint outerEndpoint : PS),
        AutonomousSubstitutionTimeOne
          ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint →
        AutonomousSubstitutionTimeOne
          ((baseComplexifyPolynomial outer : ℂ[X]) : PS) outerEndpoint →
        PowerSeries.subst baseSource
            (PowerSeries.subst innerEndpoint outerEndpoint) =
          baseVisible →
        False := by
  intro inner outer hinner houter hinnerConstant hinnerLinear
    houterConstant houterLinear innerEndpoint outerEndpoint innerFlow
    outerFlow hcomposition
  exact critical_base_two_flow_impossible inner outer hinner houter
    hinnerConstant hinnerLinear houterConstant houterLinear innerEndpoint
    outerEndpoint innerFlow outerFlow hcomposition

end

end AxiomPackJacobianCriticalBaseTwoFlowExclusion
