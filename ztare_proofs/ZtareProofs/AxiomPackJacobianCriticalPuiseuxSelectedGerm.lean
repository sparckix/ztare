import ZtareProofs.AxiomPackJacobianCriticalPuiseuxSeries

/-!
Exact selected Puiseux endpoint germ in the ramified coordinate.

The imported series theorem constructs the selected square-root branch and
forces the endpoint's `t^5` coefficient.  This file pays the inference that
`u=t^2` has a nonzero regular coefficient and no lower odd term: coefficient
comparison in the radial ODE gives the `t`, `t^2`, and `t^3` jets exactly.
-/

namespace AxiomPackJacobianCriticalPuiseuxSelectedGerm

open PowerSeries
open AxiomPackJacobianCriticalPuiseuxSeries

theorem local_ramification_identity :
    localXT = X ^ 2 - C 2 := by
  simp [localXT, localXU, PowerSeries.expand_X, PowerSeries.expand_C]

theorem radial_logarithmic_derivative_constantCoeff :
    constantCoeff radialLogarithmicDerivativeT = -56 / 107 := by
  rw [radialLogarithmicDerivativeT, PowerSeries.constantCoeff_inv,
    radialDenominatorT_constantCoeff]
  norm_num

theorem selected_endpoint_coeff_one
    (endpoint : ℝ⟦X⟧)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 1 endpoint = 0 := by
  have h := congrArg (coeff 0) hODE
  norm_num [PowerSeries.coeff_derivative, coeff_mul,
    Finset.antidiagonal] at h
  exact h

theorem selected_endpoint_coeff_two
    (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 2 endpoint = -56 / 107 := by
  have h := congrArg (coeff 1) hODE
  norm_num [PowerSeries.coeff_derivative, coeff_mul,
    Finset.antidiagonal, hEndpointConstant,
    radial_logarithmic_derivative_constantCoeff] at h
  linarith

theorem selected_endpoint_coeff_two_nonzero
    (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 2 endpoint ≠ 0 := by
  rw [selected_endpoint_coeff_two endpoint hEndpointConstant hODE]
  norm_num

theorem selected_endpoint_coeff_three
    (endpoint : ℝ⟦X⟧)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 3 endpoint = 0 := by
  have hOne := selected_endpoint_coeff_one endpoint hODE
  have h := congrArg (coeff 2) hODE
  norm_num [PowerSeries.coeff_derivative, coeff_mul,
    Finset.antidiagonal, PowerSeries.coeff_X, hOne,
    radialLogarithmicDerivativeT_coeff_one] at h
  linarith

/-- Complete selected-germ endpoint.  In `u=t^2`, the nonzero `t^2` term is
regular, `t` and `t^3` vanish, and the exact nonzero `t^5=u^(5/2)` term is
therefore the first nonintegral term. -/
theorem selected_algebraic_germ_expansion_terminal_certificate :
    localXT = X ^ 2 - C 2 ∧
    (selectedDiscriminantRootT ^ 2 =
        C (24 : ℝ) - C 3 * X ^ 2 ∧
      constantCoeff selectedDiscriminantRootT = 2 * Real.sqrt 6) ∧
    constantCoeff radialLogarithmicDerivativeT = -56 / 107 ∧
    ∀ endpoint : ℝ⟦X⟧,
      constantCoeff endpoint = 1 →
      d⁄dX ℝ endpoint =
        C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint →
      coeff 1 endpoint = 0 ∧
      coeff 2 endpoint = -56 / 107 ∧
      coeff 2 endpoint ≠ 0 ∧
      coeff 3 endpoint = 0 ∧
      coeff 5 endpoint = 1120 / 34347 * Real.sqrt 6 ∧
      coeff 5 endpoint ≠ 0 := by
  refine ⟨local_ramification_identity,
    selectedDiscriminantRootT_selected,
    radial_logarithmic_derivative_constantCoeff, ?_⟩
  intro endpoint hconstant hODE
  exact ⟨selected_endpoint_coeff_one endpoint hODE,
    selected_endpoint_coeff_two endpoint hconstant hODE,
    selected_endpoint_coeff_two_nonzero endpoint hconstant hODE,
    selected_endpoint_coeff_three endpoint hODE,
    selected_endpoint_coeff_five endpoint hconstant hODE,
    selected_endpoint_coeff_five_nonzero endpoint hconstant hODE⟩

end AxiomPackJacobianCriticalPuiseuxSelectedGerm
