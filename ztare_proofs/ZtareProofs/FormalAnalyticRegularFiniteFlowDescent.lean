import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate

/-!
# Descent of regular finite polynomial-flow branches

At regular finite source and endpoint centers, the parameterized Julia
identity makes the two normalized Abel coordinates equal.  The analytic
inverse of the endpoint Abel coordinate then factors the selected branch
through the source germ.  No source-coordinate analyticity of the selected
branch is assumed.
-/

namespace FormalAnalyticRegularFiniteFlowDescent

open Filter Metric Polynomial Set
open scoped Topology

open FormalPolynomialFiniteTimeCoordinate

/-- A finite selected Julia branch on one parameter germ.  Regularity of both
finite centers is explicit; descent through the source coordinate is absent. -/
structure RegularFiniteJuliaBranch where
  generator : ℂ[X]
  parameterCenter : ℂ
  sourceCenter : ℂ
  hiddenCenter : ℂ
  source : ℂ → ℂ
  hidden : ℂ → ℂ
  source_analytic : AnalyticAt ℂ source parameterCenter
  hidden_analytic : AnalyticAt ℂ hidden parameterCenter
  source_center : source parameterCenter = sourceCenter
  hidden_center : hidden parameterCenter = hiddenCenter
  source_regular : generator.eval sourceCenter ≠ 0
  hidden_regular : generator.eval hiddenCenter ≠ 0
  julia :
    (fun t ↦ deriv hidden t * generator.eval (source t)) =ᶠ[
        𝓝 parameterCenter]
      (fun t ↦ deriv source t * generator.eval (hidden t))

/-- Pointwise cancellation of the Julia row after division by the two
regular generator values. -/
theorem abel_parameter_derivatives_equal
    (sourceDerivative hiddenDerivative sourceValue hiddenValue : ℂ)
    (hsourceNonzero : sourceValue ≠ 0)
    (hhiddenNonzero : hiddenValue ≠ 0)
    (hjulia : hiddenDerivative * sourceValue =
      sourceDerivative * hiddenValue) :
    hiddenValue⁻¹ * hiddenDerivative =
      sourceValue⁻¹ * sourceDerivative := by
  rw [inv_mul_eq_div, inv_mul_eq_div]
  exact (div_eq_div_iff hhiddenNonzero hsourceNonzero).2 hjulia

/-- The two local Abel coordinates agree after composition with the selected
parameter germs. -/
theorem RegularFiniteJuliaBranch.exists_abel_coordinates_equal
    (branch : RegularFiniteJuliaBranch) :
    ∃ (sourceTime hiddenTime : ℂ → ℂ),
      AnalyticAt ℂ sourceTime branch.sourceCenter ∧
      AnalyticAt ℂ hiddenTime branch.hiddenCenter ∧
      sourceTime branch.sourceCenter = 0 ∧
      hiddenTime branch.hiddenCenter = 0 ∧
      deriv hiddenTime branch.hiddenCenter =
        (branch.generator.eval branch.hiddenCenter)⁻¹ ∧
      (hiddenTime ∘ branch.hidden) =ᶠ[𝓝 branch.parameterCenter]
        (sourceTime ∘ branch.source) := by
  obtain ⟨sourceTime, hsourceTimeAnalytic, hsourceTimeZero,
      hsourceTimeDerivative, _hsourceTimeDerivativeCenter,
      _hsourceTimeOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      branch.generator branch.sourceCenter branch.source_regular
  obtain ⟨hiddenTime, hhiddenTimeAnalytic, hhiddenTimeZero,
      hhiddenTimeDerivative, hhiddenTimeDerivativeCenter,
      _hhiddenTimeOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      branch.generator branch.hiddenCenter branch.hidden_regular
  have hsourceTendsto :
      Tendsto branch.source (𝓝 branch.parameterCenter)
        (𝓝 branch.sourceCenter) := by
    have hcontinuous := branch.source_analytic.continuousAt
    change Tendsto branch.source (𝓝 branch.parameterCenter)
      (𝓝 (branch.source branch.parameterCenter)) at hcontinuous
    simpa only [branch.source_center] using hcontinuous
  have hhiddenTendsto :
      Tendsto branch.hidden (𝓝 branch.parameterCenter)
        (𝓝 branch.hiddenCenter) := by
    have hcontinuous := branch.hidden_analytic.continuousAt
    change Tendsto branch.hidden (𝓝 branch.parameterCenter)
      (𝓝 (branch.hidden branch.parameterCenter)) at hcontinuous
    simpa only [branch.hidden_center] using hcontinuous
  have hsourceTimeAt : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt sourceTime
        (finiteTimeIntegrand branch.generator (branch.source t))
        (branch.source t) :=
    hsourceTendsto.eventually hsourceTimeDerivative
  have hhiddenTimeAt : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt hiddenTime
        (finiteTimeIntegrand branch.generator (branch.hidden t))
        (branch.hidden t) :=
    hhiddenTendsto.eventually hhiddenTimeDerivative
  have hsourceHasDeriv : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt branch.source (deriv branch.source t) t := by
    filter_upwards [branch.source_analytic.eventually_analyticAt] with t ht
    exact ht.differentiableAt.hasDerivAt
  have hhiddenHasDeriv : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt branch.hidden (deriv branch.hidden t) t := by
    filter_upwards [branch.hidden_analytic.eventually_analyticAt] with t ht
    exact ht.differentiableAt.hasDerivAt
  let sourceAbel : ℂ → ℂ := sourceTime ∘ branch.source
  let hiddenAbel : ℂ → ℂ := hiddenTime ∘ branch.hidden
  have hsourceAbelAnalytic :
      AnalyticAt ℂ sourceAbel branch.parameterCenter := by
    exact hsourceTimeAnalytic.comp_of_eq branch.source_analytic
      branch.source_center
  have hhiddenAbelAnalytic :
      AnalyticAt ℂ hiddenAbel branch.parameterCenter := by
    exact hhiddenTimeAnalytic.comp_of_eq branch.hidden_analytic
      branch.hidden_center
  have hsourceAbelDerivative : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt sourceAbel
        (finiteTimeIntegrand branch.generator (branch.source t) *
          deriv branch.source t) t := by
    filter_upwards [hsourceTimeAt, hsourceHasDeriv] with t htime hsource
    exact htime.comp t hsource
  have hhiddenAbelDerivative : ∀ᶠ t in 𝓝 branch.parameterCenter,
      HasDerivAt hiddenAbel
        (finiteTimeIntegrand branch.generator (branch.hidden t) *
          deriv branch.hidden t) t := by
    filter_upwards [hhiddenTimeAt, hhiddenHasDeriv] with t htime hhidden
    exact htime.comp t hhidden
  have hsourceEvalAnalytic : AnalyticAt ℂ
      (fun t ↦ branch.generator.eval (branch.source t))
      branch.parameterCenter :=
    branch.source_analytic.aeval_polynomial branch.generator
  have hhiddenEvalAnalytic : AnalyticAt ℂ
      (fun t ↦ branch.generator.eval (branch.hidden t))
      branch.parameterCenter :=
    branch.hidden_analytic.aeval_polynomial branch.generator
  have hsourceEvalNonzero : ∀ᶠ t in 𝓝 branch.parameterCenter,
      branch.generator.eval (branch.source t) ≠ 0 := by
    apply hsourceEvalAnalytic.continuousAt.eventually_ne
    simpa only [branch.source_center] using branch.source_regular
  have hhiddenEvalNonzero : ∀ᶠ t in 𝓝 branch.parameterCenter,
      branch.generator.eval (branch.hidden t) ≠ 0 := by
    apply hhiddenEvalAnalytic.continuousAt.eventually_ne
    simpa only [branch.hidden_center] using branch.hidden_regular
  have hderivativeEq : ∀ᶠ t in 𝓝 branch.parameterCenter,
      deriv hiddenAbel t = deriv sourceAbel t := by
    filter_upwards [hhiddenAbelDerivative, hsourceAbelDerivative,
      branch.julia, hsourceEvalNonzero, hhiddenEvalNonzero] with
      t hhiddenDerivative hsourceDerivative hjulia hsourceNonzero
      hhiddenNonzero
    rw [hhiddenDerivative.deriv, hsourceDerivative.deriv]
    exact abel_parameter_derivatives_equal
      (deriv branch.source t) (deriv branch.hidden t)
      (branch.generator.eval (branch.source t))
      (branch.generator.eval (branch.hidden t))
      hsourceNonzero hhiddenNonzero hjulia
  have hlocal : ∀ᶠ t in 𝓝 branch.parameterCenter,
      AnalyticAt ℂ hiddenAbel t ∧ AnalyticAt ℂ sourceAbel t ∧
        deriv hiddenAbel t = deriv sourceAbel t := by
    filter_upwards [hhiddenAbelAnalytic.eventually_analyticAt,
      hsourceAbelAnalytic.eventually_analyticAt, hderivativeEq] with
      t hhidden hsource hderiv
    exact ⟨hhidden, hsource, hderiv⟩
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp hlocal
  have hhiddenDifferentiable :
      DifferentiableOn ℂ hiddenAbel
        (ball branch.parameterCenter radius) := by
    intro t ht
    exact (hball t ht).1.differentiableAt.differentiableWithinAt
  have hsourceDifferentiable :
      DifferentiableOn ℂ sourceAbel
        (ball branch.parameterCenter radius) := by
    intro t ht
    exact (hball t ht).2.1.differentiableAt.differentiableWithinAt
  have hcenterEq : hiddenAbel branch.parameterCenter =
      sourceAbel branch.parameterCenter := by
    simp only [hiddenAbel, sourceAbel, Function.comp_apply,
      branch.hidden_center, branch.source_center,
      hhiddenTimeZero, hsourceTimeZero]
  have hEqOn : EqOn hiddenAbel sourceAbel
      (ball branch.parameterCenter radius) :=
    isOpen_ball.eqOn_of_deriv_eq
      (convex_ball branch.parameterCenter radius).isPreconnected
      hhiddenDifferentiable hsourceDifferentiable
      (fun t ht ↦ (hball t ht).2.2)
      (mem_ball_self hradius) hcenterEq
  have hballNhd : ball branch.parameterCenter radius ∈
      𝓝 branch.parameterCenter :=
    isOpen_ball.mem_nhds (mem_ball_self hradius)
  have hEventually : hiddenAbel =ᶠ[𝓝 branch.parameterCenter]
      sourceAbel :=
    eventuallyEq_of_mem hballNhd hEqOn
  exact ⟨sourceTime, hiddenTime, hsourceTimeAnalytic,
    hhiddenTimeAnalytic, hsourceTimeZero, hhiddenTimeZero,
    hhiddenTimeDerivativeCenter, hEventually⟩

/-- Every regular finite selected Julia branch is an analytic function of the
source coordinate germ. -/
theorem RegularFiniteJuliaBranch.exists_analytic_source_descent
    (branch : RegularFiniteJuliaBranch) :
    ∃ finiteEndpoint : ℂ → ℂ,
      AnalyticAt ℂ finiteEndpoint branch.sourceCenter ∧
      finiteEndpoint branch.sourceCenter = branch.hiddenCenter ∧
      branch.hidden =ᶠ[𝓝 branch.parameterCenter]
        finiteEndpoint ∘ branch.source := by
  obtain ⟨sourceTime, hiddenTime, hsourceTimeAnalytic,
      hhiddenTimeAnalytic, hsourceTimeZero, hhiddenTimeZero,
      hhiddenTimeDerivativeCenter, htimeEq⟩ :=
    branch.exists_abel_coordinates_equal
  have hhiddenTimeDerivativeNonzero :
      deriv hiddenTime branch.hiddenCenter ≠ 0 := by
    rw [hhiddenTimeDerivativeCenter]
    exact inv_ne_zero branch.hidden_regular
  have hstrict : HasStrictDerivAt hiddenTime
      (deriv hiddenTime branch.hiddenCenter) branch.hiddenCenter :=
    hhiddenTimeAnalytic.hasStrictDerivAt
  let inverseTime := hstrict.localInverse hiddenTime
    (deriv hiddenTime branch.hiddenCenter) branch.hiddenCenter
    hhiddenTimeDerivativeNonzero
  have hinverseAnalytic : AnalyticAt ℂ inverseTime 0 := by
    simpa only [inverseTime, hhiddenTimeZero] using
      hhiddenTimeAnalytic.analyticAt_localInverse
        hhiddenTimeDerivativeNonzero
  have hinverseZero : inverseTime 0 = branch.hiddenCenter := by
    have hleft :=
      (hstrict.eventually_left_inverse
        hhiddenTimeDerivativeNonzero).self_of_nhds
    simpa only [inverseTime, hhiddenTimeZero] using hleft
  have hleftInverse : inverseTime ∘ hiddenTime =ᶠ[
      𝓝 branch.hiddenCenter] fun z ↦ z := by
    simpa only [inverseTime] using
      hstrict.eventually_left_inverse hhiddenTimeDerivativeNonzero
  let finiteEndpoint : ℂ → ℂ := inverseTime ∘ sourceTime
  have hfiniteAnalytic :
      AnalyticAt ℂ finiteEndpoint branch.sourceCenter := by
    exact hinverseAnalytic.comp_of_eq hsourceTimeAnalytic hsourceTimeZero
  have hfiniteCenter : finiteEndpoint branch.sourceCenter =
      branch.hiddenCenter := by
    simp only [finiteEndpoint, Function.comp_apply, hsourceTimeZero,
      hinverseZero]
  have hhiddenTendsto :
      Tendsto branch.hidden (𝓝 branch.parameterCenter)
        (𝓝 branch.hiddenCenter) := by
    have hcontinuous := branch.hidden_analytic.continuousAt
    change Tendsto branch.hidden (𝓝 branch.parameterCenter)
      (𝓝 (branch.hidden branch.parameterCenter)) at hcontinuous
    simpa only [branch.hidden_center] using hcontinuous
  have hleftAtHidden :
      (fun t ↦ inverseTime (hiddenTime (branch.hidden t))) =ᶠ[
        𝓝 branch.parameterCenter] branch.hidden := by
    simpa only [Function.comp_apply] using
      EventuallyEq.comp_tendsto hleftInverse hhiddenTendsto
  have hdescent : branch.hidden =ᶠ[𝓝 branch.parameterCenter]
      finiteEndpoint ∘ branch.source := by
    filter_upwards [hleftAtHidden, htimeEq] with t hleft htime
    calc
      branch.hidden t = inverseTime (hiddenTime (branch.hidden t)) :=
        hleft.symm
      _ = inverseTime (sourceTime (branch.source t)) :=
        congrArg inverseTime htime
      _ = (finiteEndpoint ∘ branch.source) t := rfl
  exact ⟨finiteEndpoint, hfiniteAnalytic, hfiniteCenter, hdescent⟩

/-- Aggregated regular finite-route descent surface. -/
theorem analytic_regular_finite_flow_descent_terminal_certificate :
    ∀ branch : RegularFiniteJuliaBranch,
      ∃ finiteEndpoint : ℂ → ℂ,
        AnalyticAt ℂ finiteEndpoint branch.sourceCenter ∧
        finiteEndpoint branch.sourceCenter = branch.hiddenCenter ∧
        branch.hidden =ᶠ[𝓝 branch.parameterCenter]
          finiteEndpoint ∘ branch.source := by
  intro branch
  exact branch.exists_analytic_source_descent

end FormalAnalyticRegularFiniteFlowDescent
