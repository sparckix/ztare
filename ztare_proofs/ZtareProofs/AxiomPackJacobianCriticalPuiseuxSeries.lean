import ZtareProofs.AxiomPackJacobianCriticalPuiseuxGermArithmetic
import ZtareProofs.FormalLocalGerm

/-!
Formal selected-branch series passage for the critical Puiseux terminal.

The ramified parameter is `u = t^2` and the original coordinate is
`x = u - 2`.  The square-root branch is constructed in
`ZtareProofs.FormalLocalGerm`; this file propagates its first odd jet through
the exact algebraic connection, radial inverse, and normalized endpoint ODE.
-/

namespace AxiomPackJacobianCriticalPuiseuxSeries

open PowerSeries
open FormalLocalGerm

private theorem two_ne_zero : (2 : ℕ) ≠ 0 := by norm_num

/-- The selected formal branch of `sqrt(24-3*t^2)`. -/
noncomputable def selectedDiscriminantRootT : ℝ⟦X⟧ :=
  selectedQuadraticRoot (2 * Real.sqrt 6) (-1 / 8)

theorem selectedDiscriminantRootT_constantCoeff :
    constantCoeff selectedDiscriminantRootT = 2 * Real.sqrt 6 := by
  exact selectedQuadraticRoot_constantCoeff _ _

theorem selectedDiscriminantRootT_square :
    selectedDiscriminantRootT ^ 2 = C (24 : ℝ) - C 3 * X ^ 2 := by
  have hsqrt : (Real.sqrt (6 : ℝ)) ^ 2 = 6 :=
    Real.sq_sqrt (by norm_num)
  rw [selectedDiscriminantRootT,
    selectedQuadraticRoot_square]
  rw [show (2 * Real.sqrt 6) ^ 2 = (24 : ℝ) by nlinarith]
  have hscale : C (24 : ℝ) * C (-1 / 8 : ℝ) = -C 3 := by
    rw [← map_mul, ← map_neg]
    norm_num
  calc
    C (24 : ℝ) * (1 + C (-1 / 8 : ℝ) * X ^ 2) =
        C 24 + (C 24 * C (-1 / 8 : ℝ)) * X ^ 2 := by ring
    _ = C 24 - C 3 * X ^ 2 := by rw [hscale]; ring

theorem selectedDiscriminantRootT_selected :
    selectedDiscriminantRootT ^ 2 = C (24 : ℝ) - C 3 * X ^ 2 ∧
      constantCoeff selectedDiscriminantRootT = 2 * Real.sqrt 6 := by
  exact ⟨selectedDiscriminantRootT_square,
    selectedDiscriminantRootT_constantCoeff⟩

/-- The local `x` coordinate as a series in `u`. -/
noncomputable def localXU : ℝ⟦X⟧ := X - C 2

/-- The exact common denominator of the critical normal-two connection after
the substitution `x=u-2`. -/
noncomputable def connectionDenominatorU : ℝ⟦X⟧ :=
  C 896 * localXU ^ 3 * (localXU - C 4) *
    (localXU ^ 2 - C 4 * localXU - C 8)

/-- The radical quotient after removing its explicit simple factor `u`. -/
noncomputable def radicalQuotientU : ℝ⟦X⟧ :=
  (localXU - C 6) *
      (C 7 * localXU ^ 3 - C 42 * localXU ^ 2 + C 624) *
    connectionDenominatorU⁻¹

/-- Rational part of the critical normal-two connection. -/
noncomputable def rationalVelocityU : ℝ⟦X⟧ :=
  (C 21 * localXU ^ 6 - C 124 * localXU ^ 5 +
      C 456 * localXU ^ 4 - C 2048 * localXU ^ 3 -
      C 6768 * localXU ^ 2 + C 22464 * localXU + C 44928) *
    connectionDenominatorU⁻¹

/-- The selected radical contribution in `t`: the removed `u`, the radical
factor `t`, and the selected square root combine to the explicit `t^3`. -/
noncomputable def radicalContributionT : ℝ⟦X⟧ :=
  (PowerSeries.expand 2 two_ne_zero radicalQuotientU *
      selectedDiscriminantRootT) * X ^ 3

/-- The exact selected critical velocity series in `t`. -/
noncomputable def localVelocityT : ℝ⟦X⟧ :=
  PowerSeries.expand 2 two_ne_zero rationalVelocityU +
    radicalContributionT

/-- The local `x=t^2-2` coordinate. -/
noncomputable def localXT : ℝ⟦X⟧ :=
  PowerSeries.expand 2 two_ne_zero localXU

/-- Denominator of the radial logarithmic derivative
`1/(x*(1+2*x*V))`. -/
noncomputable def radialDenominatorT : ℝ⟦X⟧ :=
  localXT * (1 + C 2 * localXT * localVelocityT)

/-- The selected radial logarithmic derivative. -/
noncomputable def radialLogarithmicDerivativeT : ℝ⟦X⟧ :=
  radialDenominatorT⁻¹

theorem radicalQuotientU_constantCoeff :
    constantCoeff radicalQuotientU = -25 / 1344 := by
  norm_num [radicalQuotientU, connectionDenominatorU, localXU]

theorem rationalVelocityU_constantCoeff :
    constantCoeff rationalVelocityU = 5 / 448 := by
  norm_num [rationalVelocityU, connectionDenominatorU, localXU]

theorem radicalContributionT_constantCoeff :
    constantCoeff radicalContributionT = 0 := by
  simp [radicalContributionT]

theorem radicalContributionT_coeff_one :
    coeff 1 radicalContributionT = 0 := by
  simp [radicalContributionT, coeff_mul_X_pow']

theorem radicalContributionT_coeff_three :
    coeff 3 radicalContributionT = -25 / 672 * Real.sqrt 6 := by
  rw [radicalContributionT]
  have hshift :
      coeff 3 ((PowerSeries.expand 2 two_ne_zero radicalQuotientU *
          selectedDiscriminantRootT) * X ^ 3) =
        constantCoeff (PowerSeries.expand 2 two_ne_zero radicalQuotientU *
          selectedDiscriminantRootT) := by
    simpa [← coeff_zero_eq_constantCoeff] using
      (coeff_mul_X_pow
        (PowerSeries.expand 2 two_ne_zero radicalQuotientU *
          selectedDiscriminantRootT) 3 0)
  rw [hshift]
  simp [radicalQuotientU_constantCoeff,
    selectedDiscriminantRootT_constantCoeff]
  ring

theorem localVelocityT_constantCoeff :
    constantCoeff localVelocityT = 5 / 448 := by
  simp [localVelocityT, rationalVelocityU_constantCoeff,
    radicalContributionT_constantCoeff]

theorem localVelocityT_coeff_one : coeff 1 localVelocityT = 0 := by
  rw [localVelocityT, map_add]
  rw [PowerSeries.coeff_expand_of_not_dvd 2 two_ne_zero
    rationalVelocityU (by norm_num)]
  simp [radicalContributionT_coeff_one]

theorem localVelocityT_coeff_three :
    coeff 3 localVelocityT = -25 / 672 * Real.sqrt 6 := by
  rw [localVelocityT, map_add]
  rw [PowerSeries.coeff_expand_of_not_dvd 2 two_ne_zero
    rationalVelocityU (by norm_num)]
  simp [radicalContributionT_coeff_three]

theorem localXT_coefficients :
    constantCoeff localXT = -2 ∧ coeff 1 localXT = 0 ∧
      coeff 2 localXT = 1 ∧ coeff 3 localXT = 0 := by
  constructor
  · simp [localXT, localXU]
  constructor
  · rw [localXT]
    exact PowerSeries.coeff_expand_of_not_dvd 2 two_ne_zero
      localXU (by norm_num)
  constructor
  · rw [localXT]
    simpa [localXU] using
      PowerSeries.coeff_expand_mul 2 two_ne_zero localXU 1
  · rw [localXT]
    exact PowerSeries.coeff_expand_of_not_dvd 2 two_ne_zero
      localXU (by norm_num)

theorem radialDenominatorT_constantCoeff :
    constantCoeff radialDenominatorT = -107 / 56 := by
  rcases localXT_coefficients with ⟨hx0, _hx1, _hx2, _hx3⟩
  norm_num [radialDenominatorT, hx0, localVelocityT_constantCoeff]

theorem radialDenominatorT_coeff_one :
    coeff 1 radialDenominatorT = 0 := by
  rcases localXT_coefficients with ⟨hx0, hx1, _hx2, _hx3⟩
  norm_num [radialDenominatorT, coeff_mul, Finset.antidiagonal,
    hx0, hx1, localVelocityT_constantCoeff, localVelocityT_coeff_one]

theorem radialDenominatorT_coeff_three :
    coeff 3 radialDenominatorT = -25 / 84 * Real.sqrt 6 := by
  rcases localXT_coefficients with ⟨hx0, hx1, hx2, hx3⟩
  norm_num [radialDenominatorT, coeff_mul, Finset.antidiagonal,
    hx0, hx1, hx2, hx3, localVelocityT_constantCoeff,
    localVelocityT_coeff_one, localVelocityT_coeff_three]
  ring

theorem radialLogarithmicDerivativeT_coeff_one :
    coeff 1 radialLogarithmicDerivativeT = 0 := by
  exact coeff_one_inv_of_coeff_one_eq_zero radialDenominatorT
    radialDenominatorT_coeff_one

theorem radialLogarithmicDerivativeT_coeff_three :
    coeff 3 radialLogarithmicDerivativeT =
      2800 / 34347 * Real.sqrt 6 := by
  rw [radialLogarithmicDerivativeT,
    coeff_three_inv_of_first_odd_cubic radialDenominatorT
      radialDenominatorT_coeff_one,
    radialDenominatorT_constantCoeff,
    radialDenominatorT_coeff_three]
  ring

/-- Every normalized solution of the selected radial endpoint ODE has the
declared first odd ramified coefficient. -/
theorem selected_endpoint_coeff_five
    (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 5 endpoint = 1120 / 34347 * Real.sqrt 6 := by
  rw [endpoint_coeff_five_of_first_odd_cubic
    radialLogarithmicDerivativeT endpoint hEndpointConstant
    radialLogarithmicDerivativeT_coeff_one hODE,
    radialLogarithmicDerivativeT_coeff_three]
  ring

theorem selected_endpoint_coeff_five_nonzero
    (endpoint : ℝ⟦X⟧)
    (hEndpointConstant : constantCoeff endpoint = 1)
    (hODE : d⁄dX ℝ endpoint =
      C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint) :
    coeff 5 endpoint ≠ 0 := by
  rw [selected_endpoint_coeff_five endpoint hEndpointConstant hODE]
  have hsqrt : 0 < Real.sqrt (6 : ℝ) := Real.sqrt_pos.2 (by norm_num)
  positivity

/-- Complete selected-series leaf: a constructed branch, exact connection and
radial odd jets, and the normalized endpoint coefficient forced by the ODE. -/
theorem selected_algebraic_germ_series_passage :
    (selectedDiscriminantRootT ^ 2 =
        C (24 : ℝ) - C 3 * X ^ 2 ∧
      constantCoeff selectedDiscriminantRootT = 2 * Real.sqrt 6) ∧
    constantCoeff radicalQuotientU = -25 / 1344 ∧
    constantCoeff localVelocityT = 5 / 448 ∧
    coeff 3 localVelocityT = -25 / 672 * Real.sqrt 6 ∧
    coeff 3 radialLogarithmicDerivativeT =
      2800 / 34347 * Real.sqrt 6 ∧
    ∀ endpoint : ℝ⟦X⟧,
      constantCoeff endpoint = 1 →
      d⁄dX ℝ endpoint =
        C (2 : ℝ) * X * radialLogarithmicDerivativeT * endpoint →
      coeff 5 endpoint = 1120 / 34347 * Real.sqrt 6 ∧
        coeff 5 endpoint ≠ 0 := by
  refine ⟨selectedDiscriminantRootT_selected,
    radicalQuotientU_constantCoeff,
    localVelocityT_constantCoeff,
    localVelocityT_coeff_three,
    radialLogarithmicDerivativeT_coeff_three, ?_⟩
  intro endpoint hconstant hODE
  exact ⟨selected_endpoint_coeff_five endpoint hconstant hODE,
    selected_endpoint_coeff_five_nonzero endpoint hconstant hODE⟩

end AxiomPackJacobianCriticalPuiseuxSeries
