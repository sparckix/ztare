import ZtareProofs.AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxSingleFlow

/-!
# Constructed selected endpoint versus one polynomial flow

This specialization removes the endpoint and ODE premises from the general
ramified root-factor theorem.  The only remaining premise is the exact Julia
power-series identity for the named selected endpoint.
-/

namespace AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow

open PowerSeries
open AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
open AxiomPackJacobianCriticalPuiseuxSingleFlow
open FormalRamifiedJuliaObstruction

/-- The named selected endpoint excludes every nonzero polynomial generator
once its locally transported Julia identity is supplied. -/
theorem selected_constructed_endpoint_polynomial_julia_impossible
    (outputValue : ℝ) (hOutputValue : outputValue ≠ 0)
    (generator : Polynomial ℝ) (hGenerator : generator ≠ 0)
    (hLocalJulia :
      (((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
          (selectedDisplacement outputValue selectedEndpointT)) =
        selectedDerivativeFactor outputValue selectedEndpointT *
          (((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
            (X ^ 2))) :
    False := by
  exact selected_endpoint_polynomial_local_julia_impossible
    selectedEndpointT outputValue hOutputValue
      selectedEndpointT_constantCoeff selectedEndpointT_derivative
      generator hGenerator hLocalJulia

/-- Aggregated constructed-endpoint single-flow obstruction. -/
theorem selected_constructed_single_flow_terminal_certificate :
    ∀ (outputValue : ℝ), outputValue ≠ 0 →
      ∀ generator : Polynomial ℝ, generator ≠ 0 →
        (((shiftedPolynomial generator outputValue : Polynomial ℝ) : ℝ⟦X⟧).subst
            (selectedDisplacement outputValue selectedEndpointT)) =
          selectedDerivativeFactor outputValue selectedEndpointT *
            (((shiftedPolynomial generator (-2) : Polynomial ℝ) : ℝ⟦X⟧).subst
              (X ^ 2)) →
          False := by
  intro outputValue hOutputValue generator hGenerator hJulia
  exact selected_constructed_endpoint_polynomial_julia_impossible
    outputValue hOutputValue generator hGenerator hJulia

end AxiomPackJacobianCriticalPuiseuxConstructedSingleFlow
