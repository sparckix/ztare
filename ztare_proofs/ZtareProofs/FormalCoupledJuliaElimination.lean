import Mathlib.Algebra.Polynomial.Eval.Defs
import Mathlib.Tactic

/-!
# Division-free elimination of a hidden endpoint from two Julia rows

A composition of two autonomous time-one maps supplies one Julia identity
for the inner factor and one for the outer factor.  Multiplying them eliminates
the hidden derivative without assuming that either polynomial generator is
nonzero at the selected points.  If the visible endpoint also solves a scalar
logarithmic differential equation, the hidden value is a root of one explicit
polynomial.
-/

namespace FormalCoupledJuliaElimination

open Polynomial

universe u

/-- Polynomial relation in the hidden endpoint. -/
noncomputable def hiddenRelationPolynomial
    {𝕜 : Type u} [CommRing 𝕜]
    (p q : 𝕜[X]) (x endpoint coefficient : 𝕜) : 𝕜[X] :=
  C (q.eval endpoint) * p -
    C (coefficient * endpoint * p.eval x) * q

/-- The two Julia rows eliminate the hidden derivative without division. -/
theorem coupled_julia_identity
    {𝕜 : Type u} [CommRing 𝕜]
    (p q : 𝕜[X])
    (x hidden endpoint hiddenDerivative endpointDerivative : 𝕜)
    (innerJulia :
      p.eval hidden = hiddenDerivative * p.eval x)
    (outerJulia :
      q.eval endpoint * hiddenDerivative =
        endpointDerivative * q.eval hidden) :
    p.eval hidden * q.eval endpoint =
      endpointDerivative * p.eval x * q.eval hidden := by
  calc
    p.eval hidden * q.eval endpoint =
        (hiddenDerivative * p.eval x) * q.eval endpoint := by
      rw [innerJulia]
    _ = (q.eval endpoint * hiddenDerivative) * p.eval x := by ring
    _ = (endpointDerivative * q.eval hidden) * p.eval x := by
      rw [outerJulia]
    _ = endpointDerivative * p.eval x * q.eval hidden := by ring

/-- A logarithmic endpoint equation turns the coupled Julia identity into
root membership in the explicit hidden relation polynomial. -/
theorem hiddenRelationPolynomial_eval_eq_zero
    {𝕜 : Type u} [CommRing 𝕜]
    (p q : 𝕜[X])
    (x hidden endpoint coefficient hiddenDerivative endpointDerivative : 𝕜)
    (innerJulia :
      p.eval hidden = hiddenDerivative * p.eval x)
    (outerJulia :
      q.eval endpoint * hiddenDerivative =
        endpointDerivative * q.eval hidden)
    (endpointLogarithmicEquation :
      endpointDerivative = coefficient * endpoint) :
    (hiddenRelationPolynomial p q x endpoint coefficient).eval hidden = 0 := by
  have heliminated := coupled_julia_identity p q x hidden endpoint
    hiddenDerivative endpointDerivative innerJulia outerJulia
  rw [endpointLogarithmicEquation] at heliminated
  simp only [hiddenRelationPolynomial, eval_sub, eval_mul, eval_C]
  calc
    q.eval endpoint * p.eval hidden -
          coefficient * endpoint * p.eval x * q.eval hidden =
        p.eval hidden * q.eval endpoint -
          coefficient * endpoint * p.eval x * q.eval hidden := by ring
    _ = 0 := by rw [heliminated]; ring

/-- Aggregated general-purpose terminal certificate. -/
theorem coupled_julia_elimination_terminal_certificate :
    ∀ {𝕜 : Type u} [CommRing 𝕜]
      (p q : 𝕜[X])
      (x hidden endpoint coefficient hiddenDerivative endpointDerivative : 𝕜),
      p.eval hidden = hiddenDerivative * p.eval x →
      q.eval endpoint * hiddenDerivative =
        endpointDerivative * q.eval hidden →
      endpointDerivative = coefficient * endpoint →
      p.eval hidden * q.eval endpoint =
        endpointDerivative * p.eval x * q.eval hidden ∧
      (hiddenRelationPolynomial p q x endpoint coefficient).eval hidden = 0 := by
  intro 𝕜 _ p q x hidden endpoint coefficient hiddenDerivative
    endpointDerivative innerJulia outerJulia endpointEquation
  exact ⟨coupled_julia_identity p q x hidden endpoint hiddenDerivative
      endpointDerivative innerJulia outerJulia,
    hiddenRelationPolynomial_eval_eq_zero p q x hidden endpoint coefficient
      hiddenDerivative endpointDerivative innerJulia outerJulia
      endpointEquation⟩

end FormalCoupledJuliaElimination
