import Mathlib.Analysis.Calculus.Deriv.Polynomial
import Mathlib.Tactic
import ZtareProofs.FormalCoupledJuliaElimination

/-!
# Differential prolongation of the coupled Julia relation

The two Julia rows and a logarithmic equation first make the hidden endpoint
a root of one polynomial.  Differentiating that root identity along analytic
solution germs yields a second, division-free polynomial relation.  A finite
lift is therefore a common root of the relation and its first differential
prolongation.

No resultant nonvanishing or invariant-factor classification is asserted.
-/

namespace FormalCoupledJuliaDifferentialProlongation

open Filter Polynomial
open scoped Topology

open FormalCoupledJuliaElimination

/-- Scalar value of the zero-th coupled relation along three functions. -/
noncomputable def coupledRelationValue
    (p q : ℂ[X]) (hidden endpoint coefficient : ℂ → ℂ) : ℂ → ℂ :=
  fun x ↦
    q.eval (endpoint x) * p.eval (hidden x) -
      coefficient x * endpoint x * p.eval x * q.eval (hidden x)

/-- First differential prolongation, as a polynomial in the hidden value.
The formula is multiplied by `p(x)`, so no generator value is inverted. -/
noncomputable def hiddenRelationProlongation
    (p q : ℂ[X])
    (x endpoint coefficient coefficientDerivative : ℂ) : ℂ[X] :=
  C (coefficient * endpoint * p.eval x * q.derivative.eval endpoint) * p +
    C (q.eval endpoint) * p.derivative * p -
    C (coefficientDerivative * endpoint * (p.eval x) ^ 2 +
      coefficient ^ 2 * endpoint * (p.eval x) ^ 2 +
      coefficient * endpoint * p.eval x * p.derivative.eval x) * q -
    C (coefficient * endpoint * p.eval x) * q.derivative * p

/-- Evaluation formula for the first prolongation. -/
theorem hiddenRelationProlongation_eval
    (p q : ℂ[X])
    (x hidden endpoint coefficient coefficientDerivative : ℂ) :
    (hiddenRelationProlongation p q x endpoint coefficient
        coefficientDerivative).eval hidden =
      coefficient * endpoint * p.eval x * q.derivative.eval endpoint *
          p.eval hidden +
        q.eval endpoint * p.derivative.eval hidden * p.eval hidden -
        (coefficientDerivative * endpoint * (p.eval x) ^ 2 +
          coefficient ^ 2 * endpoint * (p.eval x) ^ 2 +
          coefficient * endpoint * p.eval x * p.derivative.eval x) *
            q.eval hidden -
        coefficient * endpoint * p.eval x * q.derivative.eval hidden *
          p.eval hidden := by
  simp only [hiddenRelationProlongation, eval_add, eval_sub, eval_mul,
    eval_C, derivative]

/-- Pointwise derivative of the scalar coupled relation. -/
theorem hasDerivAt_coupledRelationValue
    (p q : ℂ[X])
    {hidden endpoint coefficient : ℂ → ℂ} {x : ℂ}
    (hhidden : HasDerivAt hidden (deriv hidden x) x)
    (hendpoint : HasDerivAt endpoint (deriv endpoint x) x)
    (hcoefficient : HasDerivAt coefficient (deriv coefficient x) x) :
    HasDerivAt (coupledRelationValue p q hidden endpoint coefficient)
      (q.derivative.eval (endpoint x) * deriv endpoint x *
          p.eval (hidden x) +
        q.eval (endpoint x) * p.derivative.eval (hidden x) *
          deriv hidden x -
        (deriv coefficient x * endpoint x * p.eval x *
            q.eval (hidden x) +
          coefficient x * deriv endpoint x * p.eval x *
            q.eval (hidden x) +
          coefficient x * endpoint x * p.derivative.eval x *
            q.eval (hidden x) +
          coefficient x * endpoint x * p.eval x *
            q.derivative.eval (hidden x) * deriv hidden x)) x := by
  have hpHidden := (p.hasDerivAt (hidden x)).comp x hhidden
  have hqHidden := (q.hasDerivAt (hidden x)).comp x hhidden
  have hqEndpoint := (q.hasDerivAt (endpoint x)).comp x hendpoint
  have hpId := p.hasDerivAt x
  have hleft := hqEndpoint.mul hpHidden
  have hright := (((hcoefficient.mul hendpoint).mul hpId).mul hqHidden)
  change HasDerivAt
    (fun z ↦
      q.eval (endpoint z) * p.eval (hidden z) -
        coefficient z * endpoint z * p.eval z * q.eval (hidden z)) _ x
  convert hleft.sub hright using 1
  all_goals
    simp only [Function.comp_apply, Pi.mul_apply]
    ring

/-- The pointwise first prolongation is the source-generator multiple of
the derivative of the zero-th relation after the inner Julia and visible
logarithmic equations are substituted. -/
theorem prolongation_eval_eq_source_mul_relationDerivative
    (p q : ℂ[X])
    (x hidden endpoint coefficient coefficientDerivative
      hiddenDerivative endpointDerivative relationDerivative : ℂ)
    (innerJulia :
      p.eval hidden = hiddenDerivative * p.eval x)
    (endpointLogarithmicEquation :
      endpointDerivative = coefficient * endpoint)
    (relationDerivativeFormula :
      relationDerivative =
        q.derivative.eval endpoint * endpointDerivative * p.eval hidden +
          q.eval endpoint * p.derivative.eval hidden * hiddenDerivative -
          (coefficientDerivative * endpoint * p.eval x * q.eval hidden +
            coefficient * endpointDerivative * p.eval x * q.eval hidden +
            coefficient * endpoint * p.derivative.eval x * q.eval hidden +
            coefficient * endpoint * p.eval x *
              q.derivative.eval hidden * hiddenDerivative)) :
    (hiddenRelationProlongation p q x endpoint coefficient
        coefficientDerivative).eval hidden =
      p.eval x * relationDerivative := by
  rw [hiddenRelationProlongation_eval, relationDerivativeFormula,
    endpointLogarithmicEquation, innerJulia]
  ring

/-- Analytic germs carrying the two Julia rows and the visible logarithmic
equation make the hidden branch a common root of the zero-th relation and
its first differential prolongation. -/
theorem coupled_relation_and_first_prolongation
    (p q : ℂ[X])
    {hidden endpoint coefficient : ℂ → ℂ} {center : ℂ}
    (hhidden : AnalyticAt ℂ hidden center)
    (hendpoint : AnalyticAt ℂ endpoint center)
    (hcoefficient : AnalyticAt ℂ coefficient center)
    (innerJulia : ∀ᶠ x in 𝓝 center,
      p.eval (hidden x) = deriv hidden x * p.eval x)
    (outerJulia : ∀ᶠ x in 𝓝 center,
      q.eval (endpoint x) * deriv hidden x =
        deriv endpoint x * q.eval (hidden x))
    (endpointLogarithmicEquation : ∀ᶠ x in 𝓝 center,
      deriv endpoint x = coefficient x * endpoint x) :
    ((fun x ↦
      (hiddenRelationPolynomial p q x (endpoint x) (coefficient x)).eval
        (hidden x)) =ᶠ[𝓝 center] fun _ ↦ (0 : ℂ)) ∧
    ((fun x ↦
      (hiddenRelationProlongation p q x (endpoint x) (coefficient x)
        (deriv coefficient x)).eval (hidden x)) =ᶠ[𝓝 center]
      fun _ ↦ (0 : ℂ)) := by
  have hzeroRelation :
      (coupledRelationValue p q hidden endpoint coefficient) =ᶠ[
        𝓝 center] fun _ ↦ 0 := by
    filter_upwards [innerJulia, outerJulia,
      endpointLogarithmicEquation] with x hinner houter hendpointEquation
    have hroot := hiddenRelationPolynomial_eval_eq_zero p q x
      (hidden x) (endpoint x) (coefficient x) (deriv hidden x)
      (deriv endpoint x) hinner houter hendpointEquation
    simpa only [coupledRelationValue, hiddenRelationPolynomial,
      eval_sub, eval_mul, eval_C] using hroot
  have hzeroRelationDerivative :
      (fun x ↦ deriv
        (coupledRelationValue p q hidden endpoint coefficient) x) =ᶠ[
          𝓝 center] fun _ ↦ 0 := by
    simpa using hzeroRelation.deriv
  have hhiddenDerivative : ∀ᶠ x in 𝓝 center,
      HasDerivAt hidden (deriv hidden x) x := by
    filter_upwards [hhidden.eventually_analyticAt] with x hx
    exact hx.differentiableAt.hasDerivAt
  have hendpointDerivative : ∀ᶠ x in 𝓝 center,
      HasDerivAt endpoint (deriv endpoint x) x := by
    filter_upwards [hendpoint.eventually_analyticAt] with x hx
    exact hx.differentiableAt.hasDerivAt
  have hcoefficientDerivative : ∀ᶠ x in 𝓝 center,
      HasDerivAt coefficient (deriv coefficient x) x := by
    filter_upwards [hcoefficient.eventually_analyticAt] with x hx
    exact hx.differentiableAt.hasDerivAt
  constructor
  · filter_upwards [hzeroRelation] with x hx
    simpa only [coupledRelationValue, hiddenRelationPolynomial,
      eval_sub, eval_mul, eval_C] using hx
  · filter_upwards [innerJulia, endpointLogarithmicEquation,
      hzeroRelationDerivative, hhiddenDerivative, hendpointDerivative,
      hcoefficientDerivative] with x hinner hendpointEquation hderivZero
      hhiddenAt hendpointAt hcoefficientAt
    have hrelationDerivative := hasDerivAt_coupledRelationValue p q
      hhiddenAt hendpointAt hcoefficientAt
    have hrelationFormula :
        deriv (coupledRelationValue p q hidden endpoint coefficient) x =
          q.derivative.eval (endpoint x) * deriv endpoint x *
              p.eval (hidden x) +
            q.eval (endpoint x) * p.derivative.eval (hidden x) *
              deriv hidden x -
            (deriv coefficient x * endpoint x * p.eval x *
                q.eval (hidden x) +
              coefficient x * deriv endpoint x * p.eval x *
                q.eval (hidden x) +
              coefficient x * endpoint x * p.derivative.eval x *
                q.eval (hidden x) +
              coefficient x * endpoint x * p.eval x *
                q.derivative.eval (hidden x) * deriv hidden x) :=
      hrelationDerivative.deriv
    have hprolongation :=
      prolongation_eval_eq_source_mul_relationDerivative p q x
        (hidden x) (endpoint x) (coefficient x) (deriv coefficient x)
        (deriv hidden x) (deriv endpoint x)
        (deriv (coupledRelationValue p q hidden endpoint coefficient) x)
        hinner hendpointEquation hrelationFormula
    rw [hprolongation, hderivZero, mul_zero]

/-- Aggregated differential-elimination surface. -/
theorem coupled_julia_differential_prolongation_terminal_certificate :
    ∀ (p q : ℂ[X])
      (hidden endpoint coefficient : ℂ → ℂ) (center : ℂ),
      AnalyticAt ℂ hidden center →
      AnalyticAt ℂ endpoint center →
      AnalyticAt ℂ coefficient center →
      (∀ᶠ x in 𝓝 center,
        p.eval (hidden x) = deriv hidden x * p.eval x) →
      (∀ᶠ x in 𝓝 center,
        q.eval (endpoint x) * deriv hidden x =
          deriv endpoint x * q.eval (hidden x)) →
      (∀ᶠ x in 𝓝 center,
        deriv endpoint x = coefficient x * endpoint x) →
      ((fun x ↦
        (hiddenRelationPolynomial p q x (endpoint x) (coefficient x)).eval
          (hidden x)) =ᶠ[𝓝 center] fun _ ↦ (0 : ℂ)) ∧
      ((fun x ↦
        (hiddenRelationProlongation p q x (endpoint x) (coefficient x)
          (deriv coefficient x)).eval (hidden x)) =ᶠ[𝓝 center]
        fun _ ↦ (0 : ℂ)) := by
  intro p q hidden endpoint coefficient center hhidden hendpoint
    hcoefficient hinner houter hendpointEquation
  exact coupled_relation_and_first_prolongation p q hhidden hendpoint
    hcoefficient hinner houter hendpointEquation

end FormalCoupledJuliaDifferentialProlongation
