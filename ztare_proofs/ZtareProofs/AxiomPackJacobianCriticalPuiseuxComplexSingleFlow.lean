import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxAnalyticRealization
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxSingleFlow
import ZtareProofs.FormalRamifiedJuliaObstruction

/-!
# Complex-coefficient single-flow obstruction at the selected critical germ

The root-factor contradiction is characteristic-zero algebra.  This file
applies its field-polymorphic form to the complexification of the named
selected endpoint, excluding arbitrary complex polynomial generators.
-/

namespace AxiomPackJacobianCriticalPuiseuxComplexSingleFlow

open PowerSeries
open AxiomPackJacobianCriticalPuiseuxAnalyticRealization
open AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
open AxiomPackJacobianCriticalPuiseuxSelectedGerm
open AxiomPackJacobianCriticalPuiseuxSingleFlow
open FormalRamifiedJuliaObstruction

/-- Complex selected displacement, normalized at its output center. -/
noncomputable def complexSelectedDisplacement
    (outputValue : ℂ) : ℂ⟦X⟧ :=
  C outputValue *
    complexify (selectedDisplacement 1 selectedEndpointT)

/-- Complex spatial derivative factor of the selected endpoint. -/
noncomputable def complexSelectedDerivativeFactor
    (outputValue : ℂ) : ℂ⟦X⟧ :=
  C outputValue *
    complexify (selectedDerivativeFactor 1 selectedEndpointT)

theorem complexSelectedDisplacement_coeff
    (outputValue : ℂ) (n : ℕ) :
    coeff n (complexSelectedDisplacement outputValue) =
      outputValue *
        ((coeff n (selectedDisplacement 1 selectedEndpointT) : ℝ) : ℂ) := by
  simp [complexSelectedDisplacement, complexify,
    PowerSeries.coeff_C_mul, PowerSeries.coeff_map]

theorem complexSelectedDerivativeFactor_coeff
    (outputValue : ℂ) (n : ℕ) :
    coeff n (complexSelectedDerivativeFactor outputValue) =
      outputValue *
        ((coeff n (selectedDerivativeFactor 1 selectedEndpointT) : ℝ) : ℂ) := by
  simp [complexSelectedDerivativeFactor, complexify,
    PowerSeries.coeff_C_mul, PowerSeries.coeff_map]

theorem complexSelectedDisplacement_order_two
    (outputValue : ℂ) (hOutputValue : outputValue ≠ 0) :
    order (complexSelectedDisplacement outputValue) = (2 : ℕ) := by
  apply (PowerSeries.order_eq_nat).2
  constructor
  · rw [complexSelectedDisplacement_coeff,
      selectedDisplacement_coeff_two 1 selectedEndpointT
        selectedEndpointT_constantCoeff selectedEndpointT_derivative]
    exact mul_ne_zero hOutputValue (by norm_num)
  · intro i hi
    interval_cases i
    · rw [complexSelectedDisplacement_coeff,
        PowerSeries.coeff_zero_eq_constantCoeff,
        selectedDisplacement_constantCoeff 1 selectedEndpointT
          selectedEndpointT_constantCoeff]
      simp
    · rw [complexSelectedDisplacement_coeff,
        selectedDisplacement_coeff_one 1 selectedEndpointT
          selectedEndpointT_derivative]
      simp

theorem complexSelectedDisplacement_coeff_three
    (outputValue : ℂ) :
    coeff 3 (complexSelectedDisplacement outputValue) = 0 := by
  rw [complexSelectedDisplacement_coeff,
    selectedDisplacement_coeff_three 1 selectedEndpointT
      selectedEndpointT_derivative]
  simp

theorem complexSelectedDisplacement_coeff_five_ne_zero
    (outputValue : ℂ) (hOutputValue : outputValue ≠ 0) :
    coeff 5 (complexSelectedDisplacement outputValue) ≠ 0 := by
  rw [complexSelectedDisplacement_coeff,
    selectedDisplacement_coeff_five 1 selectedEndpointT
      selectedEndpointT_constantCoeff selectedEndpointT_derivative]
  apply mul_ne_zero hOutputValue
  norm_num

theorem complexSelectedDerivativeFactor_constantCoeff
    (outputValue : ℂ) :
    constantCoeff (complexSelectedDerivativeFactor outputValue) =
      coeff 2 (complexSelectedDisplacement outputValue) := by
  rw [← PowerSeries.coeff_zero_eq_constantCoeff,
    complexSelectedDerivativeFactor_coeff,
    complexSelectedDisplacement_coeff]
  have hreal :
      coeff 0 (selectedDerivativeFactor 1 selectedEndpointT) =
        coeff 2 (selectedDisplacement 1 selectedEndpointT) := by
    simpa only [PowerSeries.coeff_zero_eq_constantCoeff] using
      selectedDerivativeFactor_constantCoeff 1 selectedEndpointT
        selectedEndpointT_constantCoeff selectedEndpointT_derivative
  rw [hreal]

theorem complexSelectedDerivativeFactor_coeff_one
    (outputValue : ℂ) :
    coeff 1 (complexSelectedDerivativeFactor outputValue) = 0 := by
  rw [complexSelectedDerivativeFactor_coeff,
    selectedDerivativeFactor_coeff_one 1 selectedEndpointT
      selectedEndpointT_derivative]
  simp

theorem complexSelectedDerivativeFactor_coeff_three
    (outputValue : ℂ) :
    coeff 3 (complexSelectedDerivativeFactor outputValue) =
      (5 / 2 : ℂ) * coeff 5
        (complexSelectedDisplacement outputValue) := by
  rw [complexSelectedDerivativeFactor_coeff,
    complexSelectedDisplacement_coeff,
    selectedDerivativeFactor_coeff_three 1 selectedEndpointT
      selectedEndpointT_constantCoeff selectedEndpointT_derivative]
  push_cast
  ring

/-- No nonzero complex polynomial generator satisfies Julia's formal identity
for the selected critical endpoint. -/
theorem selected_complex_polynomial_local_julia_impossible
    (outputValue : ℂ) (hOutputValue : outputValue ≠ 0)
    (generator : Polynomial ℂ) (hGenerator : generator ≠ 0)
    (hLocalJulia :
      (((shiftedPolynomial generator outputValue : Polynomial ℂ) : ℂ⟦X⟧).subst
          (complexSelectedDisplacement outputValue)) =
        complexSelectedDerivativeFactor outputValue *
          (((shiftedPolynomial generator (-2) : Polynomial ℂ) : ℂ⟦X⟧).subst
            (X ^ 2))) :
    False := by
  apply polynomial_julia_root_factor_obstruction
    generator hGenerator (-2) outputValue
    (complexSelectedDisplacement outputValue)
    (complexSelectedDerivativeFactor outputValue)
  · exact complexSelectedDisplacement_order_two outputValue hOutputValue
  · exact complexSelectedDisplacement_coeff_three outputValue
  · exact complexSelectedDisplacement_coeff_five_ne_zero
      outputValue hOutputValue
  · exact complexSelectedDerivativeFactor_constantCoeff outputValue
  · exact complexSelectedDerivativeFactor_coeff_one outputValue
  · exact complexSelectedDerivativeFactor_coeff_three outputValue
  · exact hLocalJulia

/-- Aggregated complex-coefficient critical single-flow surface. -/
theorem selected_complex_single_flow_terminal_certificate :
    ∀ (outputValue : ℂ), outputValue ≠ 0 →
      ∀ generator : Polynomial ℂ, generator ≠ 0 →
        (((shiftedPolynomial generator outputValue : Polynomial ℂ) : ℂ⟦X⟧).subst
            (complexSelectedDisplacement outputValue)) =
          complexSelectedDerivativeFactor outputValue *
            (((shiftedPolynomial generator (-2) : Polynomial ℂ) : ℂ⟦X⟧).subst
              (X ^ 2)) →
        False := by
  intro outputValue hOutputValue generator hGenerator hJulia
  exact selected_complex_polynomial_local_julia_impossible outputValue
    hOutputValue generator hGenerator hJulia

end AxiomPackJacobianCriticalPuiseuxComplexSingleFlow
