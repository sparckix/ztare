import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate
import ZtareProofs.FormalPolynomialRamifiedTrajectorySheet

/-!
# A centered Abel collision from two Julia identities

Two polynomial Julia identities sharing one hidden meromorphic factor become
two finite/infinity Abel-separation identities on the common uniformizer.
After analytic extension across the puncture and zero normalization of the
four time coordinates, their difference is the centered Abel collision.

The source uniformizer may be ramified.  No inverse of the source coordinate
and no pre-supplied separated-time or Abel equality occurs in the carrier.
-/

namespace FormalAnalyticTwoJuliaAbelCollision

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialFiniteTimeCoordinate
open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialTimeSeparation

/-- Parameterized Julia data convert the derivative of the reciprocal hidden
factor into the finite-source speed times the reciprocal vector field. -/
theorem hasDerivAt_reciprocal_of_parameterized_julia
    (p : ℂ[X]) (degree : ℕ)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree)
    {reciprocal hidden source : ℂ → ℂ}
    {reciprocalDerivative hiddenDerivative sourceDerivative t : ℂ}
    (hreciprocal : HasDerivAt reciprocal reciprocalDerivative t)
    (hreciprocalDerivative :
      reciprocalDerivative = -hiddenDerivative / hidden t ^ 2)
    (hreciprocalValue : reciprocal t = (hidden t)⁻¹)
    (hjulia :
      hiddenDerivative * p.eval (source t) =
        sourceDerivative * p.eval (hidden t))
    (hsourceRegular : p.eval (source t) ≠ 0)
    (hhiddenNonzero : hidden t ≠ 0) :
    HasDerivAt reciprocal
      (finiteTimeIntegrand p (source t) * sourceDerivative *
        reciprocalVectorField p degree (reciprocal t)) t := by
  have hreverse := reverse_eval_inv_mul_pow p hhiddenNonzero
  have hdegreePower : hidden t ^ p.natDegree = hidden t ^ degree := by
    rw [hdegree]
  have hreciprocalCoefficient :
      -p.eval (hidden t) / hidden t ^ 2 =
        reciprocalVectorField p degree (hidden t)⁻¹ := by
    rw [← hreverse]
    simp only [reciprocalVectorField, hdegreePower]
    rw [inv_pow_sub₀ hhiddenNonzero htwo]
    field_simp
  have hratio :
      sourceDerivative * p.eval (hidden t) / p.eval (source t) =
        hiddenDerivative := by
    apply (div_eq_iff hsourceRegular).2
    exact hjulia.symm
  apply hreciprocal.congr_deriv
  rw [hreciprocalDerivative, hreciprocalValue,
    ← hreciprocalCoefficient]
  simp only [finiteTimeIntegrand]
  symm
  rw [mul_assoc]
  calc
    (p.eval (source t))⁻¹ *
          (sourceDerivative * (-p.eval (hidden t) / hidden t ^ 2)) =
        -(sourceDerivative * p.eval (hidden t) /
          p.eval (source t)) / hidden t ^ 2 := by
      field_simp
    _ = -hiddenDerivative / hidden t ^ 2 := by rw [hratio]

/-- Along one parameterized Julia sheet, the finite/infinity Abel difference
has zero derivative. -/
theorem hasDerivAt_finiteInfinityDifference_zero
    (p : ℂ[X]) (degree : ℕ)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree)
    {finiteTime infinityTime reciprocal hidden source : ℂ → ℂ}
    {reciprocalDerivative hiddenDerivative sourceDerivative t : ℂ}
    (hfiniteTime : HasDerivAt finiteTime
      (finiteTimeIntegrand p (source t)) (source t))
    (hinfinityTime : HasDerivAt infinityTime
      (reciprocalTimeIntegrand p degree (reciprocal t)) (reciprocal t))
    (hsource : HasDerivAt source sourceDerivative t)
    (hreciprocal : HasDerivAt reciprocal reciprocalDerivative t)
    (hreciprocalDerivative :
      reciprocalDerivative = -hiddenDerivative / hidden t ^ 2)
    (hreciprocalValue : reciprocal t = (hidden t)⁻¹)
    (hjulia :
      hiddenDerivative * p.eval (source t) =
        sourceDerivative * p.eval (hidden t))
    (hsourceRegular : p.eval (source t) ≠ 0)
    (hhiddenNonzero : hidden t ≠ 0)
    (hreverseNonzero : p.reverse.eval (reciprocal t) ≠ 0) :
    HasDerivAt
      (fun s ↦ infinityTime (reciprocal s) - finiteTime (source s))
      0 t := by
  have hreciprocalScaled :=
    hasDerivAt_reciprocal_of_parameterized_julia p degree hdegree htwo
      hreciprocal hreciprocalDerivative hreciprocalValue hjulia
      hsourceRegular hhiddenNonzero
  have hreciprocalNonzero : reciprocal t ≠ 0 := by
    rw [hreciprocalValue]
    exact inv_ne_zero hhiddenNonzero
  have hcancel := reciprocalTimeIntegrand_mul_reciprocalVectorField
    p degree hreciprocalNonzero hreverseNonzero
  have hinfinityComp := hinfinityTime.comp t hreciprocalScaled
  have hfiniteComp := hfiniteTime.comp t hsource
  have hinfinityComp' : HasDerivAt
      (fun s ↦ infinityTime (reciprocal s))
      (finiteTimeIntegrand p (source t) * sourceDerivative) t := by
    convert hinfinityComp using 1
    symm
    calc
      reciprocalTimeIntegrand p degree (reciprocal t) *
          (finiteTimeIntegrand p (source t) * sourceDerivative *
            reciprocalVectorField p degree (reciprocal t)) =
        (reciprocalTimeIntegrand p degree (reciprocal t) *
          reciprocalVectorField p degree (reciprocal t)) *
            (finiteTimeIntegrand p (source t) * sourceDerivative) := by ring
      _ = finiteTimeIntegrand p (source t) * sourceDerivative := by
        rw [hcancel, one_mul]
  simpa only [sub_self] using hinfinityComp'.sub hfiniteComp

/-- Two-flow data over one punctured uniformizer sheet.  All equality fields
are differential Julia data or coordinate bindings; the Abel collision is a
conclusion. -/
structure TwoJuliaAbelCarrier where
  firstGenerator : ℂ[X]
  secondGenerator : ℂ[X]
  firstDegree : ℕ
  secondDegree : ℕ
  center : ℂ
  sourceCenter : ℂ
  targetCenter : ℂ
  domain : Set ℂ
  anchor : ℂ
  source : ℂ → ℂ
  target : ℂ → ℂ
  hidden : ℂ → ℂ
  reciprocal : ℂ → ℂ
  sourceDerivative : ℂ → ℂ
  targetDerivative : ℂ → ℂ
  hiddenDerivative : ℂ → ℂ
  reciprocalDerivative : ℂ → ℂ
  firstFiniteTime : ℂ → ℂ
  secondFiniteTime : ℂ → ℂ
  firstInfinityTime : ℂ → ℂ
  secondInfinityTime : ℂ → ℂ
  first_degree : firstGenerator.natDegree = firstDegree
  second_degree : secondGenerator.natDegree = secondDegree
  first_degree_at_least_two : 2 ≤ firstDegree
  second_degree_at_least_two : 2 ≤ secondDegree
  isOpen_domain : IsOpen domain
  isPreconnected_domain : IsPreconnected domain
  anchor_mem : anchor ∈ domain
  punctured_mem : domain ∈ 𝓝[≠] center
  source_analytic : AnalyticAt ℂ source center
  target_analytic : AnalyticAt ℂ target center
  reciprocal_analytic : AnalyticAt ℂ reciprocal center
  source_center : source center = sourceCenter
  target_center : target center = targetCenter
  reciprocal_zero : reciprocal center = 0
  firstFinite_analytic : AnalyticAt ℂ firstFiniteTime sourceCenter
  secondFinite_analytic : AnalyticAt ℂ secondFiniteTime targetCenter
  firstInfinity_analytic : AnalyticAt ℂ firstInfinityTime 0
  secondInfinity_analytic : AnalyticAt ℂ secondInfinityTime 0
  firstFinite_zero : firstFiniteTime sourceCenter = 0
  secondFinite_zero : secondFiniteTime targetCenter = 0
  firstInfinity_zero : firstInfinityTime 0 = 0
  secondInfinity_zero : secondInfinityTime 0 = 0
  firstFinite_derivative : ∀ t ∈ domain,
    HasDerivAt firstFiniteTime
      (finiteTimeIntegrand firstGenerator (source t)) (source t)
  secondFinite_derivative : ∀ t ∈ domain,
    HasDerivAt secondFiniteTime
      (finiteTimeIntegrand secondGenerator (target t)) (target t)
  firstInfinity_derivative : ∀ t ∈ domain,
    HasDerivAt firstInfinityTime
      (reciprocalTimeIntegrand firstGenerator firstDegree (reciprocal t))
      (reciprocal t)
  secondInfinity_derivative : ∀ t ∈ domain,
    HasDerivAt secondInfinityTime
      (reciprocalTimeIntegrand secondGenerator secondDegree (reciprocal t))
      (reciprocal t)
  source_derivative : ∀ t ∈ domain,
    HasDerivAt source (sourceDerivative t) t
  target_derivative : ∀ t ∈ domain,
    HasDerivAt target (targetDerivative t) t
  hidden_derivative : ∀ t ∈ domain,
    HasDerivAt hidden (hiddenDerivative t) t
  reciprocal_derivative : ∀ t ∈ domain,
    HasDerivAt reciprocal (reciprocalDerivative t) t
  reciprocal_derivative_eq : ∀ t ∈ domain,
    reciprocalDerivative t = -hiddenDerivative t / hidden t ^ 2
  reciprocal_eq_inverse : ∀ t ∈ domain,
    reciprocal t = (hidden t)⁻¹
  inner_julia : ∀ t ∈ domain,
    hiddenDerivative t * firstGenerator.eval (source t) =
      sourceDerivative t * firstGenerator.eval (hidden t)
  outer_julia : ∀ t ∈ domain,
    hiddenDerivative t * secondGenerator.eval (target t) =
      targetDerivative t * secondGenerator.eval (hidden t)
  source_regular : ∀ t ∈ domain,
    firstGenerator.eval (source t) ≠ 0
  target_regular : ∀ t ∈ domain,
    secondGenerator.eval (target t) ≠ 0
  hidden_nonzero : ∀ t ∈ domain, hidden t ≠ 0
  first_reverse_nonzero : ∀ t ∈ domain,
    firstGenerator.reverse.eval (reciprocal t) ≠ 0
  second_reverse_nonzero : ∀ t ∈ domain,
    secondGenerator.reverse.eval (reciprocal t) ≠ 0

private theorem TwoJuliaAbelCarrier.separated_eq_zero
    (carrier : TwoJuliaAbelCarrier)
    (generator : ℂ[X]) (degree : ℕ)
    (finiteTime infinityTime base baseDerivative : ℂ → ℂ)
    (baseCenter : ℂ)
    (hdegree : generator.natDegree = degree)
    (htwo : 2 ≤ degree)
    (hbaseAnalytic : AnalyticAt ℂ base carrier.center)
    (hbaseCenter : base carrier.center = baseCenter)
    (hfiniteAnalytic : AnalyticAt ℂ finiteTime baseCenter)
    (hinfinityAnalytic : AnalyticAt ℂ infinityTime 0)
    (hfiniteZero : finiteTime baseCenter = 0)
    (hinfinityZero : infinityTime 0 = 0)
    (hfiniteDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt finiteTime (finiteTimeIntegrand generator (base t))
        (base t))
    (hinfinityDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt infinityTime
        (reciprocalTimeIntegrand generator degree (carrier.reciprocal t))
        (carrier.reciprocal t))
    (hbaseDerivative : ∀ t ∈ carrier.domain,
      HasDerivAt base (baseDerivative t) t)
    (hjulia : ∀ t ∈ carrier.domain,
      carrier.hiddenDerivative t * generator.eval (base t) =
        baseDerivative t * generator.eval (carrier.hidden t))
    (hbaseRegular : ∀ t ∈ carrier.domain,
      generator.eval (base t) ≠ 0)
    (hreverseNonzero : ∀ t ∈ carrier.domain,
      generator.reverse.eval (carrier.reciprocal t) ≠ 0) :
    (fun t ↦ infinityTime (carrier.reciprocal t) - finiteTime (base t))
      =ᶠ[𝓝 carrier.center] fun _ ↦ 0 := by
  let separated : ℂ → ℂ :=
    fun t ↦ infinityTime (carrier.reciprocal t) - finiteTime (base t)
  have hderivative : ∀ t ∈ carrier.domain,
      HasDerivAt separated 0 t := by
    intro t ht
    exact hasDerivAt_finiteInfinityDifference_zero generator degree
      hdegree htwo (hfiniteDerivative t ht) (hinfinityDerivative t ht)
      (hbaseDerivative t ht) (carrier.reciprocal_derivative t ht)
      (carrier.reciprocal_derivative_eq t ht)
      (carrier.reciprocal_eq_inverse t ht) (hjulia t ht)
      (hbaseRegular t ht) (carrier.hidden_nonzero t ht)
      (hreverseNonzero t ht)
  have hdifferentiable : DifferentiableOn ℂ separated carrier.domain := by
    intro t ht
    exact (hderivative t ht).differentiableAt.differentiableWithinAt
  have hderivZero : carrier.domain.EqOn (deriv separated) 0 := by
    intro t ht
    exact (hderivative t ht).deriv
  have hconstantOn : ∀ t ∈ carrier.domain,
      separated t = separated carrier.anchor := by
    intro t ht
    exact carrier.isOpen_domain.is_const_of_deriv_eq_zero
      carrier.isPreconnected_domain hdifferentiable hderivZero
      ht carrier.anchor_mem
  have hpuncturedConstant :
      separated =ᶠ[𝓝[≠] carrier.center]
        fun _ ↦ separated carrier.anchor := by
    filter_upwards [carrier.punctured_mem] with t ht
    exact hconstantOn t ht
  have hfiniteCompAnalytic :
      AnalyticAt ℂ (finiteTime ∘ base) carrier.center :=
    hfiniteAnalytic.comp_of_eq hbaseAnalytic hbaseCenter
  have hinfinityCompAnalytic :
      AnalyticAt ℂ (infinityTime ∘ carrier.reciprocal) carrier.center :=
    hinfinityAnalytic.comp_of_eq carrier.reciprocal_analytic
      carrier.reciprocal_zero
  have hseparatedAnalytic : AnalyticAt ℂ separated carrier.center := by
    simpa only [separated, Function.comp_apply] using
      hinfinityCompAnalytic.sub hfiniteCompAnalytic
  have hfullConstant :
      separated =ᶠ[𝓝 carrier.center]
        fun _ ↦ separated carrier.anchor := by
    exact (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
      hseparatedAnalytic.continuousAt continuousAt_const).mp
      hpuncturedConstant
  have hconstantZero : separated carrier.anchor = 0 := by
    have hcenterValue := hfullConstant.self_of_nhds
    simpa [separated, carrier.reciprocal_zero, hbaseCenter,
      hinfinityZero, hfiniteZero] using hcenterValue.symm
  simpa only [hconstantZero] using hfullConstant

/-- The two independently derived centered separations subtract to the Abel
collision identity on the common uniformizer germ. -/
theorem TwoJuliaAbelCarrier.centered_abel_collision
    (carrier : TwoJuliaAbelCarrier) :
    (fun t ↦
      carrier.secondInfinityTime (carrier.reciprocal t) -
        carrier.firstInfinityTime (carrier.reciprocal t))
      =ᶠ[𝓝 carrier.center]
    (fun t ↦
      carrier.secondFiniteTime (carrier.target t) -
        carrier.firstFiniteTime (carrier.source t)) := by
  have hfirst := carrier.separated_eq_zero
    carrier.firstGenerator carrier.firstDegree
    carrier.firstFiniteTime carrier.firstInfinityTime
    carrier.source carrier.sourceDerivative carrier.sourceCenter
    carrier.first_degree carrier.first_degree_at_least_two
    carrier.source_analytic carrier.source_center
    carrier.firstFinite_analytic carrier.firstInfinity_analytic
    carrier.firstFinite_zero carrier.firstInfinity_zero
    carrier.firstFinite_derivative carrier.firstInfinity_derivative
    carrier.source_derivative carrier.inner_julia carrier.source_regular
    carrier.first_reverse_nonzero
  have hsecond := carrier.separated_eq_zero
    carrier.secondGenerator carrier.secondDegree
    carrier.secondFiniteTime carrier.secondInfinityTime
    carrier.target carrier.targetDerivative carrier.targetCenter
    carrier.second_degree carrier.second_degree_at_least_two
    carrier.target_analytic carrier.target_center
    carrier.secondFinite_analytic carrier.secondInfinity_analytic
    carrier.secondFinite_zero carrier.secondInfinity_zero
    carrier.secondFinite_derivative carrier.secondInfinity_derivative
    carrier.target_derivative carrier.outer_julia carrier.target_regular
    carrier.second_reverse_nonzero
  filter_upwards [hfirst, hsecond] with t hfirstT hsecondT
  linear_combination hsecondT - hfirstT

/-- Aggregated reusable two-Julia Abel-collision surface. -/
theorem analytic_two_julia_abel_collision_terminal_certificate :
    ∀ carrier : TwoJuliaAbelCarrier,
      (fun t ↦
        carrier.secondInfinityTime (carrier.reciprocal t) -
          carrier.firstInfinityTime (carrier.reciprocal t))
        =ᶠ[𝓝 carrier.center]
      (fun t ↦
        carrier.secondFiniteTime (carrier.target t) -
          carrier.firstFiniteTime (carrier.source t)) := by
  intro carrier
  exact carrier.centered_abel_collision

end FormalAnalyticTwoJuliaAbelCollision
