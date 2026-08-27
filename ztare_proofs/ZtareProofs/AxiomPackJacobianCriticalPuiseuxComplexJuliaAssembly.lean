import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxComplexSingleFlow
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxJuliaAssembly

/-!
# Analytic-to-formal Julia assembly for complex generators

The selected critical analytic endpoint has real Taylor coefficients, but the
polynomial generator need not.  Canonical Taylor algebra transports an
arbitrary complex polynomial Julia identity to the complex formal endpoint,
where the field-polymorphic root-factor obstruction applies.
-/

namespace AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly

open Filter PowerSeries
open FormalAnalyticTaylorAlgebra
open FormalRamifiedJuliaObstruction
open AxiomPackJacobianCriticalPuiseuxAnalyticRealization
open AxiomPackJacobianCriticalPuiseuxComplexSingleFlow
open AxiomPackJacobianCriticalPuiseuxContinuation
open AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
open AxiomPackJacobianCriticalPuiseuxJuliaAssembly
open AxiomPackJacobianCriticalPuiseuxSelectedGerm
open AxiomPackJacobianCriticalPuiseuxSingleFlow
open AxiomPackJacobianCriticalPuiseuxSeries

theorem complexSelectedDisplacement_eq
    (outputValue : ℂ) :
    complexSelectedDisplacement outputValue =
      C outputValue * complexify selectedEndpointT - C outputValue := by
  simp [complexSelectedDisplacement, selectedDisplacement, complexify]
  ring

theorem complexSelectedDerivativeFactor_eq
    (outputValue : ℂ) :
    complexSelectedDerivativeFactor outputValue =
      C outputValue *
        complexify (radialLogarithmicDerivativeT * selectedEndpointT) := by
  simp [complexSelectedDerivativeFactor, selectedDerivativeFactor,
    complexify]

/-- Taylor transport of Julia's identity for an arbitrary complex polynomial
generator. -/
theorem selected_terminal_complex_generator_powerSeries
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) (generator : Polynomial ℂ)
    (hJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          generator) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t) generator) :
    Polynomial.aeval
        (C (outputValue : ℂ) * complexify selectedEndpointT) generator =
      (C (outputValue : ℂ) *
          complexify
            (radialLogarithmicDerivativeT * selectedEndpointT)) *
        Polynomial.aeval (complexify localXT) generator := by
  have hformal := taylorPowerSeries_polynomial_julia
    analyticLocalX_analyticAt
    (selectedAnalyticEndpoint_analyticAt continuation outputValue)
    (selectedAnalyticDerivativeFactor_analyticAt continuation outputValue)
    generator hJulia
  rw [selectedAnalyticEndpoint_taylor continuation hterminal outputValue,
    selectedAnalyticDerivativeFactor_taylor continuation hterminal outputValue,
    analyticLocalX_taylor_named] at hformal
  exact hformal

theorem complex_shifted_output_substitution_eq_aeval
    (generator : Polynomial ℂ) (outputValue : ℂ)
    (hOutputValue : outputValue ≠ 0) :
    ((shiftedPolynomial generator outputValue : Polynomial ℂ) : ℂ⟦X⟧).subst
        (complexSelectedDisplacement outputValue) =
      Polynomial.aeval
        (C outputValue * complexify selectedEndpointT) generator := by
  have horder := complexSelectedDisplacement_order_two
    outputValue hOutputValue
  have hzero :
      constantCoeff (complexSelectedDisplacement outputValue) = 0 := by
    rw [← coeff_zero_eq_constantCoeff]
    exact PowerSeries.coeff_of_lt_order 0
      (φ := complexSelectedDisplacement outputValue) (by simpa [horder])
  rw [PowerSeries.subst_coe
    (PowerSeries.HasSubst.of_constantCoeff_zero' hzero)]
  unfold shiftedPolynomial
  rw [Polynomial.aeval_comp]
  simp only [map_add, Polynomial.aeval_X, Polynomial.aeval_C]
  apply congrArg (fun value : ℂ⟦X⟧ =>
    Polynomial.aeval value generator)
  rw [complexSelectedDisplacement_eq]
  simp [PowerSeries.algebraMap_apply]

theorem complex_shifted_input_substitution_eq_aeval
    (generator : Polynomial ℂ) :
    ((shiftedPolynomial generator (-2 : ℂ) : Polynomial ℂ) : ℂ⟦X⟧).subst
        (X ^ 2) =
      Polynomial.aeval (complexify localXT) generator := by
  rw [PowerSeries.subst_coe
    (PowerSeries.HasSubst.X_pow (by norm_num : (2 : ℕ) ≠ 0))]
  unfold shiftedPolynomial
  rw [Polynomial.aeval_comp]
  simp only [map_add, Polynomial.aeval_X, Polynomial.aeval_C]
  apply congrArg (fun value : ℂ⟦X⟧ =>
    Polynomial.aeval value generator)
  have hcomplex := congrArg complexify local_ramification_identity
  simpa [complexify, PowerSeries.algebraMap_apply] using hcomplex.symm

/-- The analytic Julia identity gives the exact shifted complex formal
identity consumed by the critical root-factor obstruction. -/
theorem selected_terminal_complex_julia_shifted_powerSeries
    (continuation : SelectedRegularizedContinuation)
    (hterminal : continuation.right 3 ≠ 0)
    (outputValue : ℝ) (hOutputValue : outputValue ≠ 0)
    (generator : Polynomial ℂ)
    (hJulia :
      (fun t => Polynomial.aeval
          (selectedAnalyticEndpoint continuation outputValue t)
          generator) =ᶠ[nhds (0 : ℂ)]
        fun t => selectedAnalyticDerivativeFactor continuation outputValue t *
          Polynomial.aeval (analyticLocalX t) generator) :
    (((shiftedPolynomial generator (outputValue : ℂ) : Polynomial ℂ) :
          ℂ⟦X⟧).subst
        (complexSelectedDisplacement (outputValue : ℂ))) =
      complexSelectedDerivativeFactor (outputValue : ℂ) *
        (((shiftedPolynomial generator (-2 : ℂ) : Polynomial ℂ) :
            ℂ⟦X⟧).subst (X ^ 2)) := by
  rw [complex_shifted_output_substitution_eq_aeval generator
      (outputValue : ℂ) (by exact_mod_cast hOutputValue),
    complex_shifted_input_substitution_eq_aeval generator,
    complexSelectedDerivativeFactor_eq]
  exact selected_terminal_complex_generator_powerSeries
    continuation hterminal outputValue generator hJulia

/-- A nonzero complex polynomial generator cannot supply Julia's identity on
the constructed selected analytic endpoint. -/
theorem selected_complex_single_flow_analytic_terminal_certificate :
    ∀ (outputValue : ℝ), outputValue ≠ 0 →
      ∀ generator : Polynomial ℂ, generator ≠ 0 →
        (∃ continuation : SelectedRegularizedContinuation,
          continuation.right 3 ≠ 0 ∧
          (fun t => Polynomial.aeval
              (selectedAnalyticEndpoint continuation outputValue t)
              generator) =ᶠ[nhds (0 : ℂ)]
            fun t =>
              selectedAnalyticDerivativeFactor continuation outputValue t *
                Polynomial.aeval (analyticLocalX t) generator) →
        False := by
  intro outputValue hOutputValue generator hGenerator hrealization
  obtain ⟨continuation, hterminal, hJulia⟩ := hrealization
  have hformal := selected_terminal_complex_julia_shifted_powerSeries
    continuation hterminal outputValue hOutputValue generator hJulia
  exact selected_complex_polynomial_local_julia_impossible
    (outputValue : ℂ) (by exact_mod_cast hOutputValue)
    generator hGenerator hformal

end AxiomPackJacobianCriticalPuiseuxComplexJuliaAssembly
