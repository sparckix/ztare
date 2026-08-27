import Mathlib.RingTheory.Algebraic.Basic
import Mathlib.Tactic

/-!
# Algebraic eliminant for a tensor-density polynomial-flow orbit

Squaring a weight-`3/2` orbit identity and substituting Julia's identity
removes the derivative of the time-one endpoint.  The resulting polynomial
relation makes that endpoint algebraic as soon as its separated polynomial
is nonzero.

The second half gives a reusable nondegeneracy criterion.  If the coefficient
of one constant-field polynomial does not descend to the intermediate base
field, it cannot cancel a base-field scalar times another constant-field
polynomial identically.

This file owns the algebraic elimination.  Extension of a selected place and
the resulting local Puiseux chart are separate function-field facts.
-/

namespace FormalTensorDensityJuliaEliminant

open Polynomial

noncomputable section

/-- Polynomial obtained after eliminating the endpoint derivative from the
squared density action with Julia's identity. -/
def densityJuliaEliminant {E : Type*} [Field E]
    (criticalSquare sourceSquare sourceGeneratorValue : E)
    (generator residual : E[X]) : E[X] :=
  C criticalSquare * (X ^ 2 * generator ^ 3) -
    C (sourceSquare * sourceGeneratorValue ^ 3) * residual ^ 2

/-- The squared density identity and Julia identity make the endpoint a root
of the derivative-free eliminant. -/
theorem aeval_densityJuliaEliminant_eq_zero
    {E H : Type*} [Field E] [Field H] [Algebra E H]
    (criticalSquare sourceSquare sourceGeneratorValue : E)
    (generator residual : E[X]) (endpoint endpointDerivative : H)
    (horbit :
      algebraMap E H criticalSquare * endpoint ^ 2 *
          endpointDerivative ^ 3 =
        algebraMap E H sourceSquare *
          Polynomial.aeval endpoint residual ^ 2)
    (hjulia :
      Polynomial.aeval endpoint generator =
        endpointDerivative * algebraMap E H sourceGeneratorValue) :
    Polynomial.aeval endpoint
        (densityJuliaEliminant criticalSquare sourceSquare
          sourceGeneratorValue generator residual) = 0 := by
  rw [densityJuliaEliminant]
  simp only [map_sub, map_mul, aeval_C, aeval_X, map_pow]
  rw [hjulia]
  apply sub_eq_zero.mpr
  calc
    algebraMap E H criticalSquare *
          (endpoint ^ 2 *
            (endpointDerivative *
              algebraMap E H sourceGeneratorValue) ^ 3) =
        (algebraMap E H criticalSquare * endpoint ^ 2 *
            endpointDerivative ^ 3) *
          algebraMap E H sourceGeneratorValue ^ 3 := by ring
    _ = (algebraMap E H sourceSquare *
            Polynomial.aeval endpoint residual ^ 2) *
          algebraMap E H sourceGeneratorValue ^ 3 := by rw [horbit]
    _ = algebraMap E H sourceSquare *
          algebraMap E H sourceGeneratorValue ^ 3 *
        Polynomial.aeval endpoint residual ^ 2 := by ring

/-- A nonzero derivative-free eliminant makes the endpoint algebraic over
its coefficient field. -/
theorem endpoint_isAlgebraic_of_densityJuliaEliminant_ne_zero
    {E H : Type*} [Field E] [Field H] [Algebra E H]
    (criticalSquare sourceSquare sourceGeneratorValue : E)
    (generator residual : E[X]) (endpoint endpointDerivative : H)
    (horbit :
      algebraMap E H criticalSquare * endpoint ^ 2 *
          endpointDerivative ^ 3 =
        algebraMap E H sourceSquare *
          Polynomial.aeval endpoint residual ^ 2)
    (hjulia :
      Polynomial.aeval endpoint generator =
        endpointDerivative * algebraMap E H sourceGeneratorValue)
    (hnonzero :
      densityJuliaEliminant criticalSquare sourceSquare
        sourceGeneratorValue generator residual ≠ 0) :
    IsAlgebraic E endpoint := by
  exact ⟨densityJuliaEliminant criticalSquare sourceSquare
      sourceGeneratorValue generator residual,
    hnonzero,
    aeval_densityJuliaEliminant_eq_zero criticalSquare sourceSquare
      sourceGeneratorValue generator residual endpoint endpointDerivative
      horbit hjulia⟩

/-- A separated polynomial with a coefficient outside the intermediate base
field cannot vanish identically.  No hypothesis on the second polynomial is
needed. -/
theorem separatedPolynomial_ne_zero_of_not_mem_base
    {k F E : Type*} [Field k] [Field F] [Field E]
    [Algebra k F] [Algebra k E] [Algebra F E]
    [IsScalarTower k F E]
    (outside : E) (baseScalar : F) (left right : k[X])
    (hleft : left ≠ 0)
    (houtside : ¬ ∃ value : F, algebraMap F E value = outside) :
    C outside * left.map (algebraMap k E) -
        C (algebraMap F E baseScalar) *
          right.map (algebraMap k E) ≠ 0 := by
  intro hzero
  have houtsideZero : outside ≠ 0 := by
    intro hz
    apply houtside
    exact ⟨0, by simp [hz]⟩
  have hleading : left.leadingCoeff ≠ 0 :=
    leadingCoeff_ne_zero.mpr hleft
  have hcoefficient := congrArg
    (fun polynomial : E[X] => polynomial.coeff left.natDegree) hzero
  simp only [coeff_sub, coeff_C_mul, coeff_map] at hcoefficient
  have hscalar :
      outside * algebraMap k E left.leadingCoeff =
        algebraMap F E baseScalar *
          algebraMap k E (right.coeff left.natDegree) := by
    simpa [coeff_natDegree] using sub_eq_zero.mp hcoefficient
  apply houtside
  refine ⟨baseScalar * algebraMap k F
      (right.coeff left.natDegree / left.leadingCoeff), ?_⟩
  rw [map_mul, ← IsScalarTower.algebraMap_apply k F E]
  have hmapDiv :
      algebraMap k E
          (right.coeff left.natDegree / left.leadingCoeff) =
        algebraMap k E (right.coeff left.natDegree) /
          algebraMap k E left.leadingCoeff := by
    exact map_div₀ (algebraMap k E)
      (right.coeff left.natDegree) left.leadingCoeff
  rw [hmapDiv]
  calc
    algebraMap F E baseScalar *
          (algebraMap k E (right.coeff left.natDegree) /
            algebraMap k E left.leadingCoeff) =
        (algebraMap F E baseScalar *
            algebraMap k E (right.coeff left.natDegree)) /
          algebraMap k E left.leadingCoeff := by ring
    _ = (outside * algebraMap k E left.leadingCoeff) /
          algebraMap k E left.leadingCoeff := by rw [hscalar]
    _ = outside := by
      exact mul_div_cancel_right₀ outside
        ((_root_.map_ne_zero (algebraMap k E)).2 hleading)

/-- Aggregated algebraic-elimination certificate. -/
theorem tensor_density_julia_eliminant_terminal_certificate :
    (∀ {E H : Type*} [Field E] [Field H] [Algebra E H]
      (criticalSquare sourceSquare sourceGeneratorValue : E)
      (generator residual : E[X]) (endpoint endpointDerivative : H),
      algebraMap E H criticalSquare * endpoint ^ 2 *
            endpointDerivative ^ 3 =
          algebraMap E H sourceSquare *
            Polynomial.aeval endpoint residual ^ 2 →
      Polynomial.aeval endpoint generator =
          endpointDerivative * algebraMap E H sourceGeneratorValue →
      densityJuliaEliminant criticalSquare sourceSquare
          sourceGeneratorValue generator residual ≠ 0 →
      IsAlgebraic E endpoint) ∧
    (∀ {k F E : Type*} [Field k] [Field F] [Field E]
      [Algebra k F] [Algebra k E] [Algebra F E]
      [IsScalarTower k F E]
      (outside : E) (baseScalar : F) (left right : k[X]),
      left ≠ 0 →
      (¬ ∃ value : F, algebraMap F E value = outside) →
      C outside * left.map (algebraMap k E) -
          C (algebraMap F E baseScalar) *
            right.map (algebraMap k E) ≠ 0) := by
  constructor
  · intro E H _ _ _ criticalSquare sourceSquare sourceGeneratorValue
      generator residual endpoint endpointDerivative horbit hjulia
      hnonzero
    exact endpoint_isAlgebraic_of_densityJuliaEliminant_ne_zero
      criticalSquare sourceSquare sourceGeneratorValue generator residual
      endpoint endpointDerivative horbit hjulia hnonzero
  · intro k F E _ _ _ _ _ _ _ outside baseScalar left right hleft
      houtside
    exact separatedPolynomial_ne_zero_of_not_mem_base
      outside baseScalar left right hleft houtside

end

end FormalTensorDensityJuliaEliminant
