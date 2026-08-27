import ZtareProofs.AxiomPackJacobianCriticalPuiseuxSelectedGerm
import ZtareProofs.FormalAutonomousFlow
import ZtareProofs.FormalRamifiedJuliaObstruction

/-!
Selected critical Puiseux germ versus one polynomial autonomous generator.

The endpoint ODE constructs the ramified displacement and derivative-factor
jets required by the generic root-multiplicity obstruction.  The remaining
premise is exactly Julia's identity after analytic continuation and
translation to the selected input/output centers.
-/

namespace AxiomPackJacobianCriticalPuiseuxSingleFlow

open PowerSeries
open AxiomPackJacobianCriticalPuiseuxSeries
open AxiomPackJacobianCriticalPuiseuxSelectedGerm
open FormalRamifiedJuliaObstruction

noncomputable def selectedDisplacement
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧) : ℝ⟦X⟧ :=
  C outputValue * (endpoint - 1)

noncomputable def selectedDerivativeFactor
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧) : ℝ⟦X⟧ :=
  C outputValue * radialLogarithmicDerivativeT * endpoint

theorem selectedDisplacement_constantCoeff
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1) :
    constantCoeff (selectedDisplacement outputValue endpoint) = 0 := by
  simp [selectedDisplacement, hEndpointConstant]

theorem selectedDisplacement_coeff_one
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 1 (selectedDisplacement outputValue endpoint) = 0 := by
  rw [selectedDisplacement]
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal,
    selected_endpoint_coeff_one endpoint hODE]

theorem selectedDisplacement_coeff_two
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 2 (selectedDisplacement outputValue endpoint) =
      outputValue * (-56 / 107) := by
  rw [selectedDisplacement]
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal,
    selected_endpoint_coeff_two endpoint hEndpointConstant hODE]

theorem selectedDisplacement_coeff_three
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 3 (selectedDisplacement outputValue endpoint) = 0 := by
  rw [selectedDisplacement]
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal,
    selected_endpoint_coeff_three endpoint hODE]

theorem selectedDisplacement_coeff_five
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 5 (selectedDisplacement outputValue endpoint) =
      outputValue * (1120 / 34347 * Real.sqrt 6) := by
  rw [selectedDisplacement]
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal,
    selected_endpoint_coeff_five endpoint hEndpointConstant hODE]

theorem selectedDisplacement_order_two
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hOutputValue : outputValue ≠ 0)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    order (selectedDisplacement outputValue endpoint) = (2 : ℕ) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · rw [selectedDisplacement_coeff_two outputValue endpoint
      hEndpointConstant hODE]
    exact mul_ne_zero hOutputValue (by norm_num)
  · intro i hi
    interval_cases i
    · rw [PowerSeries.coeff_zero_eq_constantCoeff,
        selectedDisplacement_constantCoeff outputValue endpoint
          hEndpointConstant]
    · exact selectedDisplacement_coeff_one outputValue endpoint hODE

theorem selectedDerivativeFactor_constantCoeff
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    constantCoeff (selectedDerivativeFactor outputValue endpoint) =
      coeff 2 (selectedDisplacement outputValue endpoint) := by
  rw [selectedDerivativeFactor,
    selectedDisplacement_coeff_two outputValue endpoint
      hEndpointConstant hODE]
  simp [hEndpointConstant,
    radial_logarithmic_derivative_constantCoeff]

theorem selectedDerivativeFactor_coeff_one
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 1 (selectedDerivativeFactor outputValue endpoint) = 0 := by
  rw [selectedDerivativeFactor]
  norm_num [PowerSeries.coeff_mul, Finset.antidiagonal,
    radialLogarithmicDerivativeT_coeff_one,
    selected_endpoint_coeff_one endpoint hODE]

theorem selectedDerivativeFactor_coeff_three
    (outputValue : ℝ) (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 3 (selectedDerivativeFactor outputValue endpoint) =
      (5 / 2 : ℝ) *
        coeff 5 (selectedDisplacement outputValue endpoint) := by
  have hRhs :
      coeff 4
          (C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) =
        2 * coeff 3 (radialLogarithmicDerivativeT * endpoint) := by
    calc
      coeff 4
          (C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) =
          coeff 4
            (C (2 : ℝ) *
              (X ^ 1 * (radialLogarithmicDerivativeT * endpoint))) := by
            congr 1
            ring
      _ = 2 * coeff 4
          (X ^ 1 * (radialLogarithmicDerivativeT * endpoint)) := by
            rw [PowerSeries.coeff_C_mul]
      _ = 2 * coeff 3
          (radialLogarithmicDerivativeT * endpoint) := by
            simpa using congrArg (fun value : ℝ => 2 * value)
              (PowerSeries.coeff_X_pow_mul
                (radialLogarithmicDerivativeT * endpoint) 1 3)
  have hCoefficient := congrArg (coeff 4) hODE
  have hProduct :
      coeff 3 (radialLogarithmicDerivativeT * endpoint) =
        (5 / 2 : ℝ) * coeff 5 endpoint := by
    rw [PowerSeries.coeff_derivative, hRhs] at hCoefficient
    norm_num at hCoefficient
    linarith
  calc
    coeff 3 (selectedDerivativeFactor outputValue endpoint) =
        outputValue *
          coeff 3 (radialLogarithmicDerivativeT * endpoint) := by
      rw [selectedDerivativeFactor]
      simpa [mul_assoc] using
        PowerSeries.coeff_C_mul 3
          (radialLogarithmicDerivativeT * endpoint) outputValue
    _ = outputValue * ((5 / 2 : ℝ) * coeff 5 endpoint) := by
      rw [hProduct]
    _ = (5 / 2 : ℝ) *
        coeff 5 (selectedDisplacement outputValue endpoint) := by
      rw [selectedDisplacement_coeff_five outputValue endpoint
        hEndpointConstant hODE,
        selected_endpoint_coeff_five endpoint hEndpointConstant hODE]
      ring

/-- The selected ramified endpoint cannot obey the locally transported Julia
identity for any nonzero polynomial generator. -/
theorem selected_endpoint_polynomial_local_julia_impossible
    (endpoint : ℝ⟦X⟧) (outputValue : ℝ)
    (hOutputValue : outputValue ≠ 0)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint)
    (generator : Polynomial ℝ) (hGenerator : generator ≠ 0)
    (hLocalJulia :
      (((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
          (selectedDisplacement outputValue endpoint)) =
        selectedDerivativeFactor outputValue endpoint *
          (((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
            (X ^ 2))) :
    False := by
  apply polynomial_julia_root_factor_obstruction
    generator hGenerator (-2) outputValue
    (selectedDisplacement outputValue endpoint)
    (selectedDerivativeFactor outputValue endpoint)
  · exact selectedDisplacement_order_two outputValue endpoint
      hOutputValue hEndpointConstant hODE
  · exact selectedDisplacement_coeff_three outputValue endpoint hODE
  · rw [selectedDisplacement_coeff_five outputValue endpoint
      hEndpointConstant hODE]
    exact mul_ne_zero hOutputValue
      (mul_ne_zero (by norm_num) (Real.sqrt_ne_zero'.mpr (by norm_num)))
  · exact selectedDerivativeFactor_constantCoeff outputValue endpoint
      hEndpointConstant hODE
  · exact selectedDerivativeFactor_coeff_one outputValue endpoint hODE
  · exact selectedDerivativeFactor_coeff_three outputValue endpoint
      hEndpointConstant hODE
  · exact hLocalJulia

/-- Aggregated formal endpoint for the single-flow root-factor mechanism. -/
theorem selected_single_polynomial_flow_obstruction_terminal_certificate :
    ∀ (endpoint : ℝ⟦X⟧) (outputValue : ℝ),
      outputValue ≠ 0 →
      constantCoeff endpoint = 1 →
      d⁄dX ℝ endpoint =
        C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint →
      ∀ generator : Polynomial ℝ,
        generator ≠ 0 →
        (((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
            (selectedDisplacement outputValue endpoint)) =
          selectedDerivativeFactor outputValue endpoint *
            (((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
              (X ^ 2)) →
        False := by
  intro endpoint outputValue hOutput hConstant hODE generator hGenerator
    hJulia
  exact selected_endpoint_polynomial_local_julia_impossible
    endpoint outputValue hOutput hConstant hODE generator hGenerator hJulia

end AxiomPackJacobianCriticalPuiseuxSingleFlow
