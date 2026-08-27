import ZtareProofs.AxiomPackJacobianCriticalPuiseuxAnalyticRealization
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow

/-!
# Analytic-to-formal Julia assembly for the selected critical chart

An eventual polynomial Julia identity for the constructed analytic endpoint
is transported by canonical Taylor algebra.  Exact translation at the input
and output centers then recovers the real formal identity consumed by the
ramified root-factor obstruction.
-/

namespace AxiomPackJacobianCriticalPuiseuxJuliaAssembly

open Filter PowerSeries
open FormalAnalyticTaylorAlgebra
open FormalRamifiedJuliaObstruction
open AxiomPackJacobianCriticalPuiseuxSeries
open AxiomPackJacobianCriticalPuiseuxSelectedGerm
open AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
open AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow
open AxiomPackJacobianCriticalPuiseuxSingleFlow
open AxiomPackJacobianCriticalPuiseuxContinuation
open AxiomPackJacobianCriticalPuiseuxAnalyticRealization

/-- Coefficientwise complexification of a real polynomial. -/
noncomputable def complexifyPolynomial (generator : Polynomial ℝ) :
    Polynomial ℂ :=
  generator.map (algebraMap ℝ ℂ)

theorem complexify_injective : Function.Injective complexify := by
  intro left right heq
  apply PowerSeries.ext
  intro n
  have hcoeff := congrArg (PowerSeries.coeff n) heq
  simpa [complexify] using hcoeff

theorem complexify_aeval
    (series : ℝ⟦X⟧) (generator : Polynomial ℝ) :
    complexify (Polynomial.aeval series generator) =
      Polynomial.aeval (complexify series)
        (complexifyPolynomial generator) := by
  have hcommute :
      (algebraMap ℂ ℂ⟦X⟧).comp (algebraMap ℝ ℂ) =
        (PowerSeries.map (algebraMap ℝ ℂ)).comp
          (algebraMap ℝ ℝ⟦X⟧) := by
    ext value
    simp
  simpa [complexify, complexifyPolynomial] using
    Polynomial.map_aeval_eq_aeval_map hcommute generator series

/-- The selected analytic endpoint with its nonzero output value restored. -/
noncomputable def selectedAnalyticEndpoint
    (continuation : SelectedRegularizedContinuation)
    (outputValue : ℝ) (t : ℂ) : ℂ :=
  (outputValue : ℂ) * continuedTerminalEndpoint continuation t

/-- The selected terminal spatial derivative factor with output scale. -/
noncomputable def selectedAnalyticDerivativeFactor
    (continuation : SelectedRegularizedContinuation)
    (outputValue : ℝ) (t : ℂ) : ℂ :=
  (outputValue : ℂ) *
    continuedTerminalSpatialDerivativeFactor continuation t

theorem selectedAnalyticEndpoint_analyticAt
    (continuation : SelectedRegularizedContinuation)
    (outputValue : ℝ) :
    AnalyticAt ℂ (selectedAnalyticEndpoint continuation outputValue) 0 := by
  exact analyticAt_const.mul
    (continuedTerminalEndpoint_analyticAt continuation)

theorem selectedAnalyticDerivativeFactor_analyticAt
    (continuation : SelectedRegularizedContinuation)
    (outputValue : ℝ) :
    AnalyticAt ℂ
      (selectedAnalyticDerivativeFactor continuation outputValue) 0 := by
  exact analyticAt_const.mul
    (continuedTerminalSpatialDerivativeFactor_analyticAt continuation)

theorem selectedAnalyticEndpoint_taylor
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) :
    taylorPowerSeries (selectedAnalyticEndpoint continuation outputValue) 0 =
      C (outputValue : ℂ) * complexify selectedEndpointT := by
  unfold selectedAnalyticEndpoint
  change taylorPowerSeries
      ((fun _ : ℂ => (outputValue : ℂ)) *
        continuedTerminalEndpoint continuation) 0 = _
  rw [taylorPowerSeries_mul analyticAt_const
      (continuedTerminalEndpoint_analyticAt continuation),
    taylorPowerSeries_const,
    continuedTerminalEndpoint_taylor continuation hterminal]

theorem selectedAnalyticDerivativeFactor_taylor
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) :
    taylorPowerSeries
        (selectedAnalyticDerivativeFactor continuation outputValue) 0 =
      C (outputValue : ℂ) *
        complexify (radialLogarithmicDerivativeT * selectedEndpointT) := by
  unfold selectedAnalyticDerivativeFactor
  change taylorPowerSeries
      ((fun _ : ℂ => (outputValue : ℂ)) *
        continuedTerminalSpatialDerivativeFactor continuation) 0 = _
  rw [taylorPowerSeries_mul analyticAt_const
      (continuedTerminalSpatialDerivativeFactor_analyticAt continuation),
    taylorPowerSeries_const,
    continuedTerminalSpatialDerivativeFactor_taylor continuation hterminal]

/-- Eventual analytic Julia equality on the selected terminal chart gives the
exact complex Taylor-series equality without coefficient truncation. -/
theorem selected_terminal_julia_complex_powerSeries
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) (generator : Polynomial ℝ)
    (hJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          (complexifyPolynomial generator)) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t)
            (complexifyPolynomial generator)) :
    Polynomial.aeval
        (C (outputValue : ℂ) * complexify selectedEndpointT)
        (complexifyPolynomial generator) =
      (C (outputValue : ℂ) *
          complexify
            (radialLogarithmicDerivativeT * selectedEndpointT)) *
        Polynomial.aeval (complexify localXT)
          (complexifyPolynomial generator) := by
  have hformal := taylorPowerSeries_polynomial_julia
    analyticLocalX_analyticAt
    (selectedAnalyticEndpoint_analyticAt continuation outputValue)
    (selectedAnalyticDerivativeFactor_analyticAt continuation outputValue)
    (complexifyPolynomial generator) hJulia
  rw [selectedAnalyticEndpoint_taylor continuation hterminal outputValue,
    selectedAnalyticDerivativeFactor_taylor continuation hterminal outputValue,
    analyticLocalX_taylor_named] at hformal
  exact hformal

/-- The complex Taylor identity descends coefficientwise to the corresponding
real polynomial-evaluation identity. -/
theorem selected_terminal_julia_real_aeval
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) (generator : Polynomial ℝ)
    (hJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          (complexifyPolynomial generator)) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t)
            (complexifyPolynomial generator)) :
    Polynomial.aeval (C outputValue * selectedEndpointT) generator =
      (C outputValue *
          (radialLogarithmicDerivativeT * selectedEndpointT)) *
        Polynomial.aeval localXT generator := by
  apply complexify_injective
  have hcomplex := selected_terminal_julia_complex_powerSeries
    continuation hterminal outputValue generator hJulia
  calc
    complexify
          (Polynomial.aeval
            (C outputValue * selectedEndpointT) generator) =
        Polynomial.aeval
          (complexify (C outputValue * selectedEndpointT))
          (complexifyPolynomial generator) :=
      complexify_aeval _ _
    _ = Polynomial.aeval
          (C (outputValue : ℂ) * complexify selectedEndpointT)
          (complexifyPolynomial generator) := by
      simp [complexify]
    _ = (C (outputValue : ℂ) *
          complexify
            (radialLogarithmicDerivativeT * selectedEndpointT)) *
        Polynomial.aeval (complexify localXT)
          (complexifyPolynomial generator) := hcomplex
    _ = complexify
          ((C outputValue *
              (radialLogarithmicDerivativeT * selectedEndpointT)) *
            Polynomial.aeval localXT generator) := by
      have hproductMap :
          complexify
              ((C outputValue *
                  (radialLogarithmicDerivativeT * selectedEndpointT)) *
                Polynomial.aeval localXT generator) =
            (complexify (C outputValue) *
                complexify
                  (radialLogarithmicDerivativeT * selectedEndpointT)) *
              complexify (Polynomial.aeval localXT generator) := by
        unfold complexify
        rw [map_mul, map_mul]
      rw [hproductMap, complexify_C, complexify_aeval]

theorem shifted_output_substitution_eq_aeval
    (generator : Polynomial ℝ) (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hconstant : constantCoeff endpoint = 1) :
    ((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
        (selectedDisplacement outputValue endpoint) =
      Polynomial.aeval (C outputValue * endpoint) generator := by
  have hzero :
      constantCoeff (selectedDisplacement outputValue endpoint) = 0 :=
    selectedDisplacement_constantCoeff outputValue endpoint hconstant
  rw [PowerSeries.subst_coe
    (PowerSeries.HasSubst.of_constantCoeff_zero' hzero)]
  unfold shiftedPolynomial selectedDisplacement
  rw [Polynomial.aeval_comp]
  simp only [map_add, Polynomial.aeval_X, Polynomial.aeval_C]
  apply congrArg (fun value : ℝ⟦X⟧ =>
    Polynomial.aeval value generator)
  simp
  ring

theorem shifted_input_substitution_eq_aeval
    (generator : Polynomial ℝ) :
    ((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
        (X ^ 2) =
      Polynomial.aeval localXT generator := by
  rw [PowerSeries.subst_coe
    (PowerSeries.HasSubst.X_pow (by norm_num : (2 : ℕ) ≠ 0))]
  unfold shiftedPolynomial
  rw [Polynomial.aeval_comp]
  simp only [map_add, Polynomial.aeval_X, Polynomial.aeval_C]
  rw [local_ramification_identity]
  apply congrArg (fun value : ℝ⟦X⟧ =>
    Polynomial.aeval value generator)
  simp
  ring

/-- The analytic Julia equality on the constructed terminal chart yields the
exact shifted real formal identity consumed by the selected obstruction. -/
theorem selected_terminal_julia_shifted_powerSeries
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) (generator : Polynomial ℝ)
    (hJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          (complexifyPolynomial generator)) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t)
            (complexifyPolynomial generator)) :
    (((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
        (selectedDisplacement outputValue selectedEndpointT)) =
      selectedDerivativeFactor outputValue selectedEndpointT *
        (((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
          (X ^ 2)) := by
  have hreal := selected_terminal_julia_real_aeval
    continuation hterminal outputValue generator hJulia
  rw [shifted_output_substitution_eq_aeval generator outputValue
      selectedEndpointT selectedEndpointT_constantCoeff,
    shifted_input_substitution_eq_aeval generator]
  rw [selectedDerivativeFactor]
  simpa [mul_assoc] using hreal

/-- A nonzero polynomial generator cannot supply an analytic Julia identity
on any constructed selected terminal continuation. -/
theorem selected_single_flow_analytic_obstruction_terminal_certificate :
    ∀ (outputValue : ℝ), outputValue ≠ 0 →
      ∀ generator : Polynomial ℝ, generator ≠ 0 →
        (∃ continuation : SelectedRegularizedContinuation,
          continuation.right 3 ≠ 0 ∧
          (fun t => Polynomial.aeval
              (selectedAnalyticEndpoint continuation outputValue t)
              (complexifyPolynomial generator)) =ᶠ[nhds (0 : ℂ)]
            fun t =>
              selectedAnalyticDerivativeFactor continuation outputValue t *
                Polynomial.aeval (analyticLocalX t)
                  (complexifyPolynomial generator)) →
        False := by
  intro outputValue hOutputValue generator hGenerator hrealization
  obtain ⟨continuation, hterminal, hJulia⟩ := hrealization
  have hformal := selected_terminal_julia_shifted_powerSeries
    continuation hterminal outputValue generator hJulia
  exact selected_constructed_endpoint_polynomial_julia_impossible
    outputValue hOutputValue generator hGenerator hformal

end AxiomPackJacobianCriticalPuiseuxJuliaAssembly
