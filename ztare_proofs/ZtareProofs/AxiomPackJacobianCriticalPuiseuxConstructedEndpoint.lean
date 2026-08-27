import ZtareProofs.AxiomPackJacobianCriticalPuiseuxSelectedGerm
import ZtareProofs.FormalPowerSeriesLinearODE

/-!
# Constructed selected critical endpoint

The prior series certificates characterized every normalized solution of the
selected ramified ODE.  Here the general formal linear-ODE kernel constructs
that normalized solution and specializes all required jets to the named
endpoint.
-/

namespace AxiomPackJacobianCriticalPuiseuxConstructedEndpoint

open PowerSeries
open AxiomPackJacobianCriticalPuiseuxSeries
open AxiomPackJacobianCriticalPuiseuxSelectedGerm
open FormalPowerSeriesLinearODE

noncomputable def selectedEndpointCoefficientT : ℝ⟦X⟧ :=
  C (2 : ℝ) * X * radialLogarithmicDerivativeT

/-- The selected normalized endpoint constructed as `exp(∫₀ 2tL(t))`. -/
noncomputable def selectedEndpointT : ℝ⟦X⟧ :=
  normalizedEndpoint selectedEndpointCoefficientT

theorem selectedEndpointT_constantCoeff :
    constantCoeff selectedEndpointT = 1 := by
  exact normalizedEndpoint_constantCoeff selectedEndpointCoefficientT

theorem selectedEndpointT_derivative :
    d⁄dX ℝ selectedEndpointT =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * selectedEndpointT := by
  rw [selectedEndpointT, normalizedEndpoint_derivative]
  rfl

theorem selectedEndpointT_jets :
    coeff 1 selectedEndpointT = 0 ∧
    coeff 2 selectedEndpointT = -56 / 107 ∧
    coeff 2 selectedEndpointT ≠ 0 ∧
    coeff 3 selectedEndpointT = 0 ∧
    coeff 5 selectedEndpointT = 1120 / 34347 * Real.sqrt 6 ∧
    coeff 5 selectedEndpointT ≠ 0 := by
  exact selected_algebraic_germ_expansion_terminal_certificate.2.2.2
    selectedEndpointT selectedEndpointT_constantCoeff
      selectedEndpointT_derivative

/-- Aggregated constructed selected-germ certificate. -/
theorem selected_constructed_endpoint_terminal_certificate :
    localXT = X ^ 2 - C 2 ∧
    constantCoeff selectedEndpointT = 1 ∧
    d⁄dX ℝ selectedEndpointT =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * selectedEndpointT ∧
    coeff 1 selectedEndpointT = 0 ∧
    coeff 2 selectedEndpointT = -56 / 107 ∧
    coeff 2 selectedEndpointT ≠ 0 ∧
    coeff 3 selectedEndpointT = 0 ∧
    coeff 5 selectedEndpointT = 1120 / 34347 * Real.sqrt 6 ∧
    coeff 5 selectedEndpointT ≠ 0 := by
  rcases selectedEndpointT_jets with
    ⟨h1, h2, h2ne, h3, h5, h5ne⟩
  exact ⟨local_ramification_identity, selectedEndpointT_constantCoeff,
    selectedEndpointT_derivative, h1, h2, h2ne, h3, h5, h5ne⟩

end AxiomPackJacobianCriticalPuiseuxConstructedEndpoint
