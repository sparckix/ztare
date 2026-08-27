import Mathlib.Analysis.Calculus.InverseFunctionTheorem.Analytic
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticLinearODEContinuation
import ZtareProofs.FormalPolynomialEquilibriumTrajectoryRigidity
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate

/-!
# Local holomorphic solutions of controlled polynomial equations

For a holomorphic scalar coefficient and a polynomial state vector field,
the equation

`y' = c(z) * p(y)`

has a holomorphic germ through every finite state.  At a regular state the
construction uses a primitive of `c` and the local inverse of the polynomial
Abel coordinate.  At an equilibrium the solution is constant.  The same
split proves uniqueness of analytic solution germs on overlaps.

No maximal-continuation, path-cover, or infinity-passage statement is made.
-/

namespace FormalAnalyticPolynomialControlledTrajectory

open Filter Metric Polynomial Set
open scoped Topology

open FormalAnalyticLinearODEContinuation
open FormalPolynomialEquilibriumTrajectoryRigidity
open FormalPolynomialFiniteTimeCoordinate

/-- A holomorphic coefficient has a normalized local primitive. -/
theorem exists_normalized_local_primitive
    {coefficient : ℂ → ℂ} {center : ℂ}
    (hcoefficient : AnalyticAt ℂ coefficient center) :
    ∃ primitive : ℂ → ℂ,
      AnalyticAt ℂ primitive center ∧
      primitive center = 0 ∧
      ∀ᶠ z in 𝓝 center,
        HasDerivAt primitive (coefficient z) z := by
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp
      hcoefficient.eventually_analyticAt
  have hdifferentiable :
      DifferentiableOn ℂ coefficient (ball center radius) := by
    intro z hz
    exact (hball z hz).differentiableAt.differentiableWithinAt
  obtain ⟨primitive, hprimitiveCenter, hprimitiveDerivative⟩ :=
    hdifferentiable.isExactOn_ball.with_val_at center 0
  have hballNhd : ball center radius ∈ 𝓝 center :=
    isOpen_ball.mem_nhds (mem_ball_self hradius)
  have hprimitiveAnalytic : AnalyticAt ℂ primitive center := by
    have hprimitiveDifferentiable :
        DifferentiableOn ℂ primitive (ball center radius) := by
      intro z hz
      exact (hprimitiveDerivative z hz).differentiableAt.differentiableWithinAt
    exact hprimitiveDifferentiable.analyticAt hballNhd
  refine ⟨primitive, hprimitiveAnalytic, hprimitiveCenter, ?_⟩
  filter_upwards [hballNhd] with z hz
  exact hprimitiveDerivative z hz

/-- At a regular finite state, the Abel inverse constructs a local
holomorphic solution of the controlled polynomial equation. -/
theorem exists_local_solution_of_regular
    (p : ℂ[X]) {coefficient : ℂ → ℂ} {center state : ℂ}
    (hcoefficient : AnalyticAt ℂ coefficient center)
    (hregular : p.eval state ≠ 0) :
    ∃ solution : ℂ → ℂ,
      AnalyticAt ℂ solution center ∧
      solution center = state ∧
      ∀ᶠ z in 𝓝 center,
        HasDerivAt solution
          (coefficient z * p.eval (solution z)) z := by
  obtain ⟨timeCoordinate, htimeAnalytic, htimeZero,
      htimeDerivative, htimeDerivativeCenter, _htimeOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      p state hregular
  obtain ⟨controlTime, hcontrolAnalytic, hcontrolZero,
      hcontrolDerivative⟩ :=
    exists_normalized_local_primitive hcoefficient
  have htimeDerivativeNonzero :
      deriv timeCoordinate state ≠ 0 := by
    rw [htimeDerivativeCenter]
    exact inv_ne_zero hregular
  have hstrict : HasStrictDerivAt timeCoordinate
      (deriv timeCoordinate state) state :=
    htimeAnalytic.hasStrictDerivAt
  let inverseTime := hstrict.localInverse timeCoordinate
    (deriv timeCoordinate state) state htimeDerivativeNonzero
  let solution : ℂ → ℂ := inverseTime ∘ controlTime
  have hinverseAnalytic : AnalyticAt ℂ inverseTime 0 := by
    simpa only [inverseTime, htimeZero] using
      htimeAnalytic.analyticAt_localInverse htimeDerivativeNonzero
  have hinverseZero : inverseTime 0 = state := by
    have hleft :=
      (hstrict.eventually_left_inverse
        htimeDerivativeNonzero).self_of_nhds
    simpa only [inverseTime, htimeZero] using hleft
  have hsolutionAnalytic : AnalyticAt ℂ solution center := by
    exact hinverseAnalytic.comp_of_eq hcontrolAnalytic hcontrolZero
  have hsolutionCenter : solution center = state := by
    simp only [solution, Function.comp_apply, hcontrolZero, hinverseZero]
  have hcontrolTendsto : Tendsto controlTime (𝓝 center) (𝓝 0) := by
    have hcontinuous := hcontrolAnalytic.continuousAt
    change Tendsto controlTime (𝓝 center)
      (𝓝 (controlTime center)) at hcontinuous
    simpa only [hcontrolZero] using hcontinuous
  have hsolutionTendsto : Tendsto solution (𝓝 center) (𝓝 state) := by
    have hcontinuous := hsolutionAnalytic.continuousAt
    change Tendsto solution (𝓝 center)
      (𝓝 (solution center)) at hcontinuous
    simpa only [hsolutionCenter] using hcontinuous
  have hrightInverse :
      (fun w ↦ timeCoordinate (inverseTime w)) =ᶠ[𝓝 0]
        fun w ↦ w := by
    have hright :=
      hstrict.eventually_right_inverse htimeDerivativeNonzero
    rw [htimeZero] at hright
    simpa only [inverseTime] using hright
  have hcompositionIdentity :
      (fun z ↦ timeCoordinate (solution z)) =ᶠ[𝓝 center]
        controlTime := by
    simpa only [solution, Function.comp_apply] using
      EventuallyEq.comp_tendsto hrightInverse hcontrolTendsto
  have htimeAlongSolution : ∀ᶠ z in 𝓝 center,
      HasDerivAt timeCoordinate
        (finiteTimeIntegrand p (solution z)) (solution z) :=
    hsolutionTendsto htimeDerivative
  have hsolutionDerivative : ∀ᶠ z in 𝓝 center,
      HasDerivAt solution (deriv solution z) z := by
    filter_upwards [hsolutionAnalytic.eventually_analyticAt] with z hz
    exact hz.differentiableAt.hasDerivAt
  have hregularAlongSolution : ∀ᶠ z in 𝓝 center,
      p.eval (solution z) ≠ 0 := by
    have hevalAnalytic : AnalyticAt ℂ
        (fun z ↦ p.eval (solution z)) center :=
      hsolutionAnalytic.aeval_polynomial p
    apply hevalAnalytic.continuousAt.eventually_ne
    simpa only [hsolutionCenter] using hregular
  have hcompositionDerivatives :
      (fun z ↦ deriv (fun w ↦ timeCoordinate (solution w)) z) =ᶠ[
        𝓝 center] fun z ↦ deriv controlTime z :=
    hcompositionIdentity.deriv
  refine ⟨solution, hsolutionAnalytic, hsolutionCenter, ?_⟩
  filter_upwards [htimeAlongSolution, hsolutionDerivative,
      hcontrolDerivative, hcompositionDerivatives,
      hregularAlongSolution] with z htime hsolution hcontrol
      hderivativeIdentity hnonzero
  have hcomposed := htime.comp z hsolution
  have hidentityDerivative :
      finiteTimeIntegrand p (solution z) * deriv solution z =
        coefficient z := by
    calc
      finiteTimeIntegrand p (solution z) * deriv solution z =
          deriv (fun w ↦ timeCoordinate (solution w)) z :=
        hcomposed.deriv.symm
      _ = deriv controlTime z := hderivativeIdentity
      _ = coefficient z := hcontrol.deriv
  apply hsolution.congr_deriv
  simp only [finiteTimeIntegrand] at hidentityDerivative
  have hscaled := congrArg
    (fun value ↦ p.eval (solution z) * value) hidentityDerivative
  field_simp [hnonzero] at hscaled
  simpa only [mul_comm] using hscaled

/-- The constant branch solves the equation at an equilibrium state. -/
theorem exists_local_solution_of_equilibrium
    (p : ℂ[X]) {coefficient : ℂ → ℂ} {center state : ℂ}
    (_hcoefficient : AnalyticAt ℂ coefficient center)
    (hequilibrium : p.eval state = 0) :
    ∃ solution : ℂ → ℂ,
      AnalyticAt ℂ solution center ∧
      solution center = state ∧
      ∀ᶠ z in 𝓝 center,
        HasDerivAt solution
          (coefficient z * p.eval (solution z)) z := by
  refine ⟨fun _ ↦ state, analyticAt_const, rfl, ?_⟩
  filter_upwards [] with z
  simpa only [hequilibrium, mul_zero] using
    (hasDerivAt_const z state)

/-- Every finite state has a local holomorphic controlled-polynomial
trajectory.  The regular/equilibrium split is internal to the proof. -/
theorem exists_local_solution
    (p : ℂ[X]) {coefficient : ℂ → ℂ} {center state : ℂ}
    (hcoefficient : AnalyticAt ℂ coefficient center) :
    ∃ solution : ℂ → ℂ,
      AnalyticAt ℂ solution center ∧
      solution center = state ∧
      ∀ᶠ z in 𝓝 center,
        HasDerivAt solution
          (coefficient z * p.eval (solution z)) z := by
  by_cases hregular : p.eval state ≠ 0
  · exact exists_local_solution_of_regular p hcoefficient hregular
  · exact exists_local_solution_of_equilibrium p hcoefficient
      (not_ne_iff.mp hregular)

/-- An analytic controlled-polynomial trajectory through an equilibrium is
locally constant. -/
theorem eventuallyEq_const_of_equilibrium
    (p : ℂ[X]) {coefficient trajectory : ℂ → ℂ}
    {center state : ℂ}
    (hcoefficient : AnalyticAt ℂ coefficient center)
    (htrajectory : AnalyticAt ℂ trajectory center)
    (htrajectoryCenter : trajectory center = state)
    (htrajectoryODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt trajectory
        (coefficient z * p.eval (trajectory z)) z)
    (hequilibrium : p.eval state = 0) :
    trajectory =ᶠ[𝓝 center] fun _ ↦ state := by
  let quotient : ℂ[X] := equilibriumQuotient p state
  let linearCoefficient : ℂ → ℂ := fun z ↦
    coefficient z * quotient.eval (trajectory z)
  let displacement : ℂ → ℂ := fun z ↦ trajectory z - state
  have hlinearCoefficient : AnalyticAt ℂ linearCoefficient center := by
    have hquotient : AnalyticAt ℂ
        (fun z ↦ quotient.eval (trajectory z)) center :=
      htrajectory.aeval_polynomial quotient
    exact hcoefficient.mul hquotient
  have hdisplacement : AnalyticAt ℂ displacement center :=
    htrajectory.sub analyticAt_const
  have hdisplacementODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt displacement
        (linearCoefficient z * displacement z) z := by
    filter_upwards [htrajectoryODE] with z hODE
    have hfactor := eval_eq_sub_mul_equilibriumQuotient
      p state (trajectory z) hequilibrium
    convert hODE.sub_const state using 1
    simp only [linearCoefficient, displacement, quotient]
    rw [hfactor]
    ring
  have hzeroODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt (fun _ : ℂ ↦ 0)
        (linearCoefficient z * 0) z := by
    filter_upwards [] with z
    simpa using (hasDerivAt_const z (0 : ℂ))
  have hdisplacementCenter : displacement center = 0 := by
    simp [displacement, htrajectoryCenter]
  have hlocalAnalytic : ∀ᶠ z in 𝓝 center,
      AnalyticAt ℂ linearCoefficient z ∧
      AnalyticAt ℂ displacement z :=
    hlinearCoefficient.eventually_analyticAt.and
      hdisplacement.eventually_analyticAt
  have hall : ∀ᶠ z in 𝓝 center,
      (AnalyticAt ℂ linearCoefficient z ∧
        AnalyticAt ℂ displacement z) ∧
      HasDerivAt displacement
        (linearCoefficient z * displacement z) z ∧
      HasDerivAt (fun _ : ℂ ↦ (0 : ℂ))
        (linearCoefficient z * (0 : ℂ)) z :=
    hlocalAnalytic.and (hdisplacementODE.and hzeroODE)
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp hall
  have hcoefficientOn : AnalyticOnNhd ℂ linearCoefficient
      (ball center radius) := fun z hz ↦ (hball z hz).1.1
  have hdisplacementOn : AnalyticOnNhd ℂ displacement
      (ball center radius) := fun z hz ↦ (hball z hz).1.2
  have hzeroOn : AnalyticOnNhd ℂ (fun _ : ℂ ↦ (0 : ℂ))
      (ball center radius) := by
    exact (analyticOnNhd_const :
      AnalyticOnNhd ℂ (fun _ : ℂ ↦ (0 : ℂ)) (ball center radius))
  have heqOn : EqOn displacement (fun _ : ℂ ↦ (0 : ℂ))
      (ball center radius) :=
    solution_eqOn_of_eq_at isOpen_ball
      (convex_ball center radius).isPreconnected
      (mem_ball_self hradius) hcoefficientOn hdisplacementOn hzeroOn
      (fun z hz ↦ (hball z hz).2.1)
      (fun z hz ↦ (hball z hz).2.2)
      hdisplacementCenter
  filter_upwards [isOpen_ball.mem_nhds (mem_ball_self hradius)] with z hz
  have hzero := heqOn hz
  simpa only [displacement, sub_eq_zero] using hzero

/-- At a regular state, two analytic solution germs with the same initial
value agree. -/
theorem eventuallyEq_of_same_regular_solution
    (p : ℂ[X]) {coefficient left right : ℂ → ℂ}
    {center state : ℂ}
    (hleft : AnalyticAt ℂ left center)
    (hright : AnalyticAt ℂ right center)
    (hleftCenter : left center = state)
    (hrightCenter : right center = state)
    (hleftODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt left (coefficient z * p.eval (left z)) z)
    (hrightODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt right (coefficient z * p.eval (right z)) z)
    (hregular : p.eval state ≠ 0) :
    left =ᶠ[𝓝 center] right := by
  obtain ⟨timeCoordinate, htimeAnalytic, htimeZero,
      htimeDerivative, htimeDerivativeCenter, _htimeOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      p state hregular
  have hleftTendsto : Tendsto left (𝓝 center) (𝓝 state) := by
    have hcontinuous := hleft.continuousAt
    change Tendsto left (𝓝 center) (𝓝 (left center)) at hcontinuous
    simpa only [hleftCenter] using hcontinuous
  have hrightTendsto : Tendsto right (𝓝 center) (𝓝 state) := by
    have hcontinuous := hright.continuousAt
    change Tendsto right (𝓝 center) (𝓝 (right center)) at hcontinuous
    simpa only [hrightCenter] using hcontinuous
  have htimeLeft : ∀ᶠ z in 𝓝 center,
      HasDerivAt timeCoordinate
        (finiteTimeIntegrand p (left z)) (left z) :=
    hleftTendsto htimeDerivative
  have htimeRight : ∀ᶠ z in 𝓝 center,
      HasDerivAt timeCoordinate
        (finiteTimeIntegrand p (right z)) (right z) :=
    hrightTendsto htimeDerivative
  have hleftRegular : ∀ᶠ z in 𝓝 center,
      p.eval (left z) ≠ 0 := by
    apply (hleft.aeval_polynomial p).continuousAt.eventually_ne
    simpa only [hleftCenter] using hregular
  have hrightRegular : ∀ᶠ z in 𝓝 center,
      p.eval (right z) ≠ 0 := by
    apply (hright.aeval_polynomial p).continuousAt.eventually_ne
    simpa only [hrightCenter] using hregular
  let leftTime : ℂ → ℂ := timeCoordinate ∘ left
  let rightTime : ℂ → ℂ := timeCoordinate ∘ right
  have hleftTimeAnalytic : AnalyticAt ℂ leftTime center :=
    htimeAnalytic.comp_of_eq hleft hleftCenter
  have hrightTimeAnalytic : AnalyticAt ℂ rightTime center :=
    htimeAnalytic.comp_of_eq hright hrightCenter
  have htimeDerivatives : ∀ᶠ z in 𝓝 center,
      deriv leftTime z = deriv rightTime z := by
    filter_upwards [htimeLeft, htimeRight, hleftODE, hrightODE,
      hleftRegular, hrightRegular] with z hTL hTR hLODE hRODE
      hLNonzero hRNonzero
    have hL := (hTL.comp z hLODE).deriv
    have hR := (hTR.comp z hRODE).deriv
    simp only [leftTime, rightTime, finiteTimeIntegrand] at hL hR ⊢
    rw [hL, hR]
    field_simp
  have htimeLocal : ∀ᶠ z in 𝓝 center,
      AnalyticAt ℂ leftTime z ∧ AnalyticAt ℂ rightTime z ∧
        deriv leftTime z = deriv rightTime z :=
    hleftTimeAnalytic.eventually_analyticAt.and
      (hrightTimeAnalytic.eventually_analyticAt.and htimeDerivatives)
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp htimeLocal
  have hleftDifferentiable : DifferentiableOn ℂ leftTime
      (ball center radius) := fun z hz ↦
    (hball z hz).1.differentiableAt.differentiableWithinAt
  have hrightDifferentiable : DifferentiableOn ℂ rightTime
      (ball center radius) := fun z hz ↦
    (hball z hz).2.1.differentiableAt.differentiableWithinAt
  have htimeCenter : leftTime center = rightTime center := by
    simp [leftTime, rightTime, hleftCenter, hrightCenter]
  have htimeEqOn : EqOn leftTime rightTime (ball center radius) :=
    isOpen_ball.eqOn_of_deriv_eq
      (convex_ball center radius).isPreconnected
      hleftDifferentiable hrightDifferentiable
      (fun z hz ↦ (hball z hz).2.2)
      (mem_ball_self hradius) htimeCenter
  have htimeEventually : leftTime =ᶠ[𝓝 center] rightTime :=
    eventuallyEq_of_mem
      (isOpen_ball.mem_nhds (mem_ball_self hradius)) htimeEqOn
  have htimeDerivativeNonzero : deriv timeCoordinate state ≠ 0 := by
    rw [htimeDerivativeCenter]
    exact inv_ne_zero hregular
  have hstrict : HasStrictDerivAt timeCoordinate
      (deriv timeCoordinate state) state :=
    htimeAnalytic.hasStrictDerivAt
  let inverseTime := hstrict.localInverse timeCoordinate
    (deriv timeCoordinate state) state htimeDerivativeNonzero
  have hleftInverse :
      (fun z ↦ inverseTime (timeCoordinate (left z))) =ᶠ[𝓝 center]
        left := by
    simpa only [inverseTime, Function.comp_apply] using
      EventuallyEq.comp_tendsto
        (hstrict.eventually_left_inverse htimeDerivativeNonzero)
        hleftTendsto
  have hrightInverse :
      (fun z ↦ inverseTime (timeCoordinate (right z))) =ᶠ[𝓝 center]
        right := by
    simpa only [inverseTime, Function.comp_apply] using
      EventuallyEq.comp_tendsto
        (hstrict.eventually_left_inverse htimeDerivativeNonzero)
        hrightTendsto
  filter_upwards [hleftInverse, hrightInverse, htimeEventually] with
      z hLI hRI htimeEq
  calc
    left z = inverseTime (timeCoordinate (left z)) := hLI.symm
    _ = inverseTime (timeCoordinate (right z)) := by
      exact congrArg inverseTime htimeEq
    _ = right z := hRI

/-- Analytic controlled-polynomial solution germs with the same finite
initial state agree locally. -/
theorem eventuallyEq_of_same_solution
    (p : ℂ[X]) {coefficient left right : ℂ → ℂ}
    {center state : ℂ}
    (hcoefficient : AnalyticAt ℂ coefficient center)
    (hleft : AnalyticAt ℂ left center)
    (hright : AnalyticAt ℂ right center)
    (hleftCenter : left center = state)
    (hrightCenter : right center = state)
    (hleftODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt left (coefficient z * p.eval (left z)) z)
    (hrightODE : ∀ᶠ z in 𝓝 center,
      HasDerivAt right (coefficient z * p.eval (right z)) z) :
    left =ᶠ[𝓝 center] right := by
  by_cases hregular : p.eval state ≠ 0
  · exact eventuallyEq_of_same_regular_solution p hleft hright
      hleftCenter hrightCenter hleftODE hrightODE hregular
  · have hequilibrium : p.eval state = 0 := not_ne_iff.mp hregular
    exact (eventuallyEq_const_of_equilibrium p hcoefficient hleft
      hleftCenter hleftODE hequilibrium).trans
      (eventuallyEq_const_of_equilibrium p hcoefficient hright
        hrightCenter hrightODE hequilibrium).symm

/-- Aggregated finite-state holomorphic continuation surface. -/
theorem analytic_polynomial_controlled_trajectory_terminal_certificate :
    (∀ (p : ℂ[X]) (coefficient : ℂ → ℂ) (center state : ℂ),
      AnalyticAt ℂ coefficient center →
      ∃ solution : ℂ → ℂ,
        AnalyticAt ℂ solution center ∧
        solution center = state ∧
        ∀ᶠ z in 𝓝 center,
          HasDerivAt solution
            (coefficient z * p.eval (solution z)) z) ∧
    (∀ (p : ℂ[X]) (coefficient left right : ℂ → ℂ)
      (center state : ℂ),
      AnalyticAt ℂ coefficient center →
      AnalyticAt ℂ left center →
      AnalyticAt ℂ right center →
      left center = state →
      right center = state →
      (∀ᶠ z in 𝓝 center,
        HasDerivAt left (coefficient z * p.eval (left z)) z) →
      (∀ᶠ z in 𝓝 center,
        HasDerivAt right (coefficient z * p.eval (right z)) z) →
      left =ᶠ[𝓝 center] right) := by
  constructor
  · intro p coefficient center state hcoefficient
    exact exists_local_solution p hcoefficient
  · intro p coefficient left right center state hcoefficient hleft
      hright hleftCenter hrightCenter hleftODE hrightODE
    exact eventuallyEq_of_same_solution p hcoefficient hleft hright
      hleftCenter hrightCenter hleftODE hrightODE

end FormalAnalyticPolynomialControlledTrajectory
