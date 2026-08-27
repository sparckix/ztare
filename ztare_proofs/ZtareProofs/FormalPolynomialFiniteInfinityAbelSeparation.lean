import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate
import ZtareProofs.FormalPolynomialTimeSeparation

/-!
# Abel separation from Julia's identity

Julia's identity for a polynomial-flow endpoint is the pullback invariance of
the Abel differential.  In reciprocal output coordinates this makes the
difference between the infinity time and finite time locally constant.
-/

namespace FormalPolynomialFiniteInfinityAbelSeparation

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialFiniteTimeCoordinate
open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialTimeSeparation

/-- Endpoint differentiation, Julia's identity, and polynomial reversal give
the exact derivative of the reciprocal endpoint branch. -/
theorem hasDerivAt_reciprocalEndpoint_of_julia
    (p : ℂ[X]) (degree : ℕ)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree)
    {endpoint : ℂ → ℂ} {x endpointDerivative : ℂ}
    (hendpoint : HasDerivAt endpoint endpointDerivative x)
    (hjulia :
      p.eval (endpoint x) = endpointDerivative * p.eval x)
    (hsourceRegular : p.eval x ≠ 0)
    (hendpointNonzero : endpoint x ≠ 0) :
    HasDerivAt (fun y ↦ (endpoint y)⁻¹)
      (reciprocalVectorField p degree (endpoint x)⁻¹ *
        finiteTimeIntegrand p x) x := by
  have hreverse := reverse_eval_inv_mul_pow p hendpointNonzero
  have hdegreePower : endpoint x ^ p.natDegree =
      endpoint x ^ degree := by rw [hdegree]
  have hreciprocalCoefficient :
      -p.eval (endpoint x) / endpoint x ^ 2 =
        reciprocalVectorField p degree (endpoint x)⁻¹ := by
    rw [← hreverse]
    simp only [reciprocalVectorField, hdegreePower]
    rw [inv_pow_sub₀ hendpointNonzero htwo]
    field_simp
  have hendpointDerivative :
      endpointDerivative = p.eval (endpoint x) / p.eval x := by
    exact (eq_div_iff hsourceRegular).2 hjulia.symm
  have hcoefficient :
      -endpointDerivative / endpoint x ^ 2 =
        reciprocalVectorField p degree (endpoint x)⁻¹ *
          finiteTimeIntegrand p x := by
    rw [hendpointDerivative, ← hreciprocalCoefficient]
    simp only [finiteTimeIntegrand]
    ring
  convert hendpoint.inv hendpointNonzero using 1
  exact hcoefficient.symm

/-- On a connected regular overlap, Julia forces the difference between the
infinity time of the reciprocal endpoint and the finite Abel time to be
constant. -/
theorem finiteInfinitySeparatedTime_eqOn
    (p : ℂ[X]) (degree : ℕ)
    {domain : Set ℂ}
    {finiteTime infinityTime endpoint endpointDerivative : ℂ → ℂ}
    {anchor : ℂ}
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree)
    (hopen : IsOpen domain)
    (hpreconnected : IsPreconnected domain)
    (hanchor : anchor ∈ domain)
    (hfiniteTime : ∀ x ∈ domain,
      HasDerivAt finiteTime (finiteTimeIntegrand p x) x)
    (hinfinityTime : ∀ x ∈ domain,
      HasDerivAt infinityTime
        (reciprocalTimeIntegrand p degree (endpoint x)⁻¹)
        (endpoint x)⁻¹)
    (hendpoint : ∀ x ∈ domain,
      HasDerivAt endpoint (endpointDerivative x) x)
    (hjulia : ∀ x ∈ domain,
      p.eval (endpoint x) = endpointDerivative x * p.eval x)
    (hsourceRegular : ∀ x ∈ domain, p.eval x ≠ 0)
    (hendpointNonzero : ∀ x ∈ domain, endpoint x ≠ 0)
    (hreverseNonzero : ∀ x ∈ domain,
      p.reverse.eval (endpoint x)⁻¹ ≠ 0) :
    ∀ x ∈ domain,
      infinityTime (endpoint x)⁻¹ - finiteTime x =
        infinityTime (endpoint anchor)⁻¹ - finiteTime anchor := by
  let separated : ℂ → ℂ :=
    fun x ↦ infinityTime (endpoint x)⁻¹ - finiteTime x
  have hreciprocal : ∀ x ∈ domain,
      HasDerivAt (fun y ↦ (endpoint y)⁻¹)
        (reciprocalVectorField p degree (endpoint x)⁻¹ *
          finiteTimeIntegrand p x) x := by
    intro x hx
    exact hasDerivAt_reciprocalEndpoint_of_julia p degree hdegree htwo
      (hendpoint x hx) (hjulia x hx) (hsourceRegular x hx)
      (hendpointNonzero x hx)
  have hderivative : ∀ x ∈ domain,
      HasDerivAt separated 0 x := by
    intro x hx
    have htarget := (hinfinityTime x hx).comp x (hreciprocal x hx)
    have hcancel := reciprocalTimeIntegrand_mul_reciprocalVectorField
      p degree (inv_ne_zero (hendpointNonzero x hx))
      (hreverseNonzero x hx)
    have htarget' : HasDerivAt
        (fun y ↦ infinityTime (endpoint y)⁻¹)
        (finiteTimeIntegrand p x) x := by
      convert htarget using 1
      symm
      calc
        reciprocalTimeIntegrand p degree (endpoint x)⁻¹ *
              (reciprocalVectorField p degree (endpoint x)⁻¹ *
                finiteTimeIntegrand p x) =
            (reciprocalTimeIntegrand p degree (endpoint x)⁻¹ *
              reciprocalVectorField p degree (endpoint x)⁻¹) *
                finiteTimeIntegrand p x := by ring
        _ = finiteTimeIntegrand p x := by rw [hcancel, one_mul]
    simpa only [separated, sub_self] using
      htarget'.sub (hfiniteTime x hx)
  have hdifferentiable : DifferentiableOn ℂ separated domain := by
    intro x hx
    exact (hderivative x hx).differentiableAt.differentiableWithinAt
  have hderivZero : domain.EqOn (deriv separated) 0 := by
    intro x hx
    exact (hderivative x hx).deriv
  intro x hx
  exact hopen.is_const_of_deriv_eq_zero hpreconnected
    hdifferentiable hderivZero hx hanchor

/-- Aggregated Abel-separation certificate.  Target-time compatibility is a
conclusion of Julia and the two coordinate derivatives. -/
theorem polynomial_finite_infinity_abel_separation_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ)
      (domain : Set ℂ)
      (finiteTime infinityTime endpoint endpointDerivative : ℂ → ℂ)
      (anchor : ℂ),
      p.natDegree = degree →
      2 ≤ degree →
      IsOpen domain →
      IsPreconnected domain →
      anchor ∈ domain →
      (∀ x ∈ domain,
        HasDerivAt finiteTime (finiteTimeIntegrand p x) x) →
      (∀ x ∈ domain,
        HasDerivAt infinityTime
          (reciprocalTimeIntegrand p degree (endpoint x)⁻¹)
          (endpoint x)⁻¹) →
      (∀ x ∈ domain,
        HasDerivAt endpoint (endpointDerivative x) x) →
      (∀ x ∈ domain,
        p.eval (endpoint x) = endpointDerivative x * p.eval x) →
      (∀ x ∈ domain, p.eval x ≠ 0) →
      (∀ x ∈ domain, endpoint x ≠ 0) →
      (∀ x ∈ domain, p.reverse.eval (endpoint x)⁻¹ ≠ 0) →
      ∀ x ∈ domain,
        infinityTime (endpoint x)⁻¹ - finiteTime x =
          infinityTime (endpoint anchor)⁻¹ - finiteTime anchor := by
  intro p degree domain finiteTime infinityTime endpoint
    endpointDerivative anchor hdegree htwo hopen hpreconnected hanchor
    hfiniteTime hinfinityTime hendpoint hjulia hsourceRegular
    hendpointNonzero hreverseNonzero
  exact finiteInfinitySeparatedTime_eqOn p degree hdegree htwo
    hopen hpreconnected hanchor hfiniteTime hinfinityTime hendpoint hjulia
    hsourceRegular hendpointNonzero hreverseNonzero

end FormalPolynomialFiniteInfinityAbelSeparation
