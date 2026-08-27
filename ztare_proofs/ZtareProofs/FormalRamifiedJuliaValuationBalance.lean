import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalMeromorphicPoleDerivative
import ZtareProofs.FormalPolynomialMeromorphicOrder

/-!
# Valuation balance for a ramified Julia branch through infinity

The carriers in this file contain analytic/meromorphic branch data and an
eventual pulled-back Julia identity.  They contain no order-balance equation.
Exact derivative and polynomial-substitution orders are supplied by the two
reusable kernels imported above; additivity of meromorphic order then derives
the balance.
-/

namespace FormalRamifiedJuliaValuationBalance

open Filter Polynomial
open scoped Topology
open FormalMeromorphicPoleDerivative
open FormalPolynomialMeromorphicOrder

/-- An inner polynomial endpoint which starts at a finite center and reaches
infinity on a finite ramified meromorphic sheet. -/
structure InnerJuliaPoleCarrier (p : ℂ[X]) where
  degree : ℕ
  center : ℂ
  parameterCenter : ℂ
  baseOrder : ℕ
  poleOrder : ℕ
  sourceDisplacement : ℂ → ℂ
  inner : ℂ → ℂ
  reciprocal : ℂ → ℂ
  polynomial_nonzero : p ≠ 0
  polynomial_degree : p.natDegree = degree
  degree_at_least_two : 2 ≤ degree
  baseOrder_positive : 0 < baseOrder
  poleOrder_positive : 0 < poleOrder
  source_analytic : AnalyticAt ℂ sourceDisplacement parameterCenter
  source_zero : sourceDisplacement parameterCenter = 0
  source_order :
    meromorphicOrderAt sourceDisplacement parameterCenter =
      ((baseOrder : ℤ) : WithTop ℤ)
  inner_meromorphic : MeromorphicAt inner parameterCenter
  inner_order :
    meromorphicOrderAt inner parameterCenter =
      ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ)
  reciprocal_analytic : AnalyticAt ℂ reciprocal parameterCenter
  reciprocal_zero : reciprocal parameterCenter = 0
  reciprocal_eq_inverse :
    reciprocal =ᶠ[𝓝[≠] parameterCenter] (fun t ↦ (inner t)⁻¹)
  julia :
    (fun t ↦ deriv inner t *
      p.eval (center + sourceDisplacement t)) =ᶠ[𝓝[≠] parameterCenter]
      (fun t ↦ deriv sourceDisplacement t * p.eval (inner t))

/-- An outer polynomial endpoint which starts at the same infinity branch and
returns to a finite target center. -/
structure OuterJuliaReturnCarrier (p : ℂ[X]) where
  degree : ℕ
  targetCenter : ℂ
  parameterCenter : ℂ
  endpointOrder : ℕ
  poleOrder : ℕ
  endpointDisplacement : ℂ → ℂ
  inner : ℂ → ℂ
  reciprocal : ℂ → ℂ
  polynomial_nonzero : p ≠ 0
  polynomial_degree : p.natDegree = degree
  degree_at_least_two : 2 ≤ degree
  endpointOrder_positive : 0 < endpointOrder
  poleOrder_positive : 0 < poleOrder
  endpoint_analytic : AnalyticAt ℂ endpointDisplacement parameterCenter
  endpoint_zero : endpointDisplacement parameterCenter = 0
  endpoint_order :
    meromorphicOrderAt endpointDisplacement parameterCenter =
      ((endpointOrder : ℤ) : WithTop ℤ)
  inner_meromorphic : MeromorphicAt inner parameterCenter
  inner_order :
    meromorphicOrderAt inner parameterCenter =
      ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ)
  reciprocal_analytic : AnalyticAt ℂ reciprocal parameterCenter
  reciprocal_zero : reciprocal parameterCenter = 0
  reciprocal_eq_inverse :
    reciprocal =ᶠ[𝓝[≠] parameterCenter] (fun t ↦ (inner t)⁻¹)
  julia :
    (fun t ↦ deriv endpointDisplacement t * p.eval (inner t))
      =ᶠ[𝓝[≠] parameterCenter]
      (fun t ↦ deriv inner t *
        p.eval (targetCenter + endpointDisplacement t))

/-- Julia derives the inner pole balance; it is not a carrier field. -/
theorem InnerJuliaPoleCarrier.balance
    {p : ℂ[X]} (carrier : InnerJuliaPoleCarrier p) :
    (carrier.poleOrder : ℤ) * ((carrier.degree : ℤ) - 1) =
      (carrier.baseOrder : ℤ) *
        (1 - (p.rootMultiplicity carrier.center : ℤ)) := by
  have hinnerDerivative := meromorphicOrderAt_deriv_of_pole
    carrier.inner carrier.parameterCenter carrier.poleOrder
    carrier.inner_meromorphic carrier.poleOrder_positive carrier.inner_order
  have hsourceDerivative := meromorphicOrderAt_deriv_of_positive_order
    carrier.sourceDisplacement carrier.parameterCenter carrier.baseOrder
    carrier.source_analytic.meromorphicAt carrier.baseOrder_positive
    carrier.source_order
  have hsourceEval :=
    meromorphicOrderAt_polynomial_eval_at_finite_center
      p carrier.polynomial_nonzero carrier.center
      carrier.sourceDisplacement carrier.parameterCenter carrier.baseOrder
      carrier.source_analytic carrier.source_zero carrier.source_order
  have hinnerEval := meromorphicOrderAt_polynomial_eval_at_pole
    p carrier.polynomial_nonzero carrier.degree carrier.polynomial_degree
    carrier.inner carrier.reciprocal carrier.parameterCenter
    carrier.poleOrder carrier.inner_meromorphic carrier.inner_order
    carrier.reciprocal_analytic carrier.reciprocal_zero
    carrier.reciprocal_eq_inverse
  have hsourceEvalMeromorphic : MeromorphicAt
      (fun t ↦ p.eval (carrier.center + carrier.sourceDisplacement t))
      carrier.parameterCenter := by
    exact (analyticAt_const.add carrier.source_analytic).aeval_polynomial p
      |>.meromorphicAt
  have hinnerEvalMeromorphic :
      MeromorphicAt (fun t ↦ p.eval (carrier.inner t))
        carrier.parameterCenter :=
    meromorphicAt_eval_polynomial carrier.inner_meromorphic p
  have horders := meromorphicOrderAt_congr carrier.julia
  change meromorphicOrderAt
      (deriv carrier.inner *
        fun t ↦ p.eval (carrier.center + carrier.sourceDisplacement t))
        carrier.parameterCenter =
    meromorphicOrderAt
      (deriv carrier.sourceDisplacement *
        fun t ↦ p.eval (carrier.inner t)) carrier.parameterCenter at horders
  rw [meromorphicOrderAt_mul carrier.inner_meromorphic.deriv
      hsourceEvalMeromorphic,
    meromorphicOrderAt_mul carrier.source_analytic.meromorphicAt.deriv
      hinnerEvalMeromorphic,
    hinnerDerivative, hsourceEval, hsourceDerivative, hinnerEval] at horders
  norm_cast at horders
  push_cast at horders
  change (-(carrier.poleOrder : ℤ) - 1) +
      (carrier.baseOrder : ℤ) *
        (p.rootMultiplicity carrier.center : ℤ) =
    ((carrier.baseOrder : ℤ) - 1) +
      (-(carrier.poleOrder : ℤ)) * (carrier.degree : ℤ) at horders
  nlinarith

/-- Positivity forces the finite source center to be regular and converts the
integer balance to a natural ramification equation. -/
theorem InnerJuliaPoleCarrier.regular_and_natural_balance
    {p : ℂ[X]} (carrier : InnerJuliaPoleCarrier p) :
    p.rootMultiplicity carrier.center = 0 ∧
      carrier.poleOrder * (carrier.degree - 1) = carrier.baseOrder := by
  have hbalance := carrier.balance
  have hr : (0 : ℤ) < carrier.poleOrder := by
    exact_mod_cast carrier.poleOrder_positive
  have hd : (1 : ℤ) < carrier.degree := by
    have hdNat : 1 < carrier.degree := by
      exact lt_of_lt_of_le (by norm_num) carrier.degree_at_least_two
    exact_mod_cast hdNat
  have hq : (0 : ℤ) < carrier.baseOrder := by
    exact_mod_cast carrier.baseOrder_positive
  have hm : (p.rootMultiplicity carrier.center : ℤ) = 0 := by
    nlinarith
  have hmNat : p.rootMultiplicity carrier.center = 0 := by
    exact_mod_cast hm
  constructor
  · exact hmNat
  · rw [hmNat] at hbalance
    norm_num at hbalance
    have hdOne : 1 ≤ carrier.degree := by omega
    have hcast :
        ((carrier.poleOrder * (carrier.degree - 1) : ℕ) : ℤ) =
          (carrier.baseOrder : ℤ) := by
      rw [Nat.cast_mul, Nat.cast_sub hdOne]
      norm_num
      exact hbalance
    exact_mod_cast hcast

/-- Julia derives the outer return balance; it is not a carrier field. -/
theorem OuterJuliaReturnCarrier.balance
    {p : ℂ[X]} (carrier : OuterJuliaReturnCarrier p) :
    (carrier.endpointOrder : ℤ) *
        (1 - (p.rootMultiplicity carrier.targetCenter : ℤ)) =
      (carrier.poleOrder : ℤ) * ((carrier.degree : ℤ) - 1) := by
  have hinnerDerivative := meromorphicOrderAt_deriv_of_pole
    carrier.inner carrier.parameterCenter carrier.poleOrder
    carrier.inner_meromorphic carrier.poleOrder_positive carrier.inner_order
  have hendpointDerivative := meromorphicOrderAt_deriv_of_positive_order
    carrier.endpointDisplacement carrier.parameterCenter carrier.endpointOrder
    carrier.endpoint_analytic.meromorphicAt carrier.endpointOrder_positive
    carrier.endpoint_order
  have hendpointEval :=
    meromorphicOrderAt_polynomial_eval_at_finite_center
      p carrier.polynomial_nonzero carrier.targetCenter
      carrier.endpointDisplacement carrier.parameterCenter
      carrier.endpointOrder carrier.endpoint_analytic carrier.endpoint_zero
      carrier.endpoint_order
  have hinnerEval := meromorphicOrderAt_polynomial_eval_at_pole
    p carrier.polynomial_nonzero carrier.degree carrier.polynomial_degree
    carrier.inner carrier.reciprocal carrier.parameterCenter
    carrier.poleOrder carrier.inner_meromorphic carrier.inner_order
    carrier.reciprocal_analytic carrier.reciprocal_zero
    carrier.reciprocal_eq_inverse
  have hendpointEvalMeromorphic : MeromorphicAt
      (fun t ↦ p.eval
        (carrier.targetCenter + carrier.endpointDisplacement t))
      carrier.parameterCenter := by
    exact (analyticAt_const.add carrier.endpoint_analytic).aeval_polynomial p
      |>.meromorphicAt
  have hinnerEvalMeromorphic :
      MeromorphicAt (fun t ↦ p.eval (carrier.inner t))
        carrier.parameterCenter :=
    meromorphicAt_eval_polynomial carrier.inner_meromorphic p
  have horders := meromorphicOrderAt_congr carrier.julia
  change meromorphicOrderAt
      (deriv carrier.endpointDisplacement *
        fun t ↦ p.eval (carrier.inner t)) carrier.parameterCenter =
    meromorphicOrderAt
      (deriv carrier.inner *
        fun t ↦ p.eval
          (carrier.targetCenter + carrier.endpointDisplacement t))
        carrier.parameterCenter at horders
  rw [meromorphicOrderAt_mul carrier.endpoint_analytic.meromorphicAt.deriv
      hinnerEvalMeromorphic,
    meromorphicOrderAt_mul carrier.inner_meromorphic.deriv
      hendpointEvalMeromorphic,
    hendpointDerivative, hinnerEval, hinnerDerivative, hendpointEval] at horders
  norm_cast at horders
  push_cast at horders
  change ((carrier.endpointOrder : ℤ) - 1) +
      (-(carrier.poleOrder : ℤ)) * (carrier.degree : ℤ) =
    (-(carrier.poleOrder : ℤ) - 1) +
      (carrier.endpointOrder : ℤ) *
        (p.rootMultiplicity carrier.targetCenter : ℤ) at horders
  nlinarith

/-- Positivity forces the finite target center to be regular and converts the
integer balance to a natural ramification equation. -/
theorem OuterJuliaReturnCarrier.regular_and_natural_balance
    {p : ℂ[X]} (carrier : OuterJuliaReturnCarrier p) :
    p.rootMultiplicity carrier.targetCenter = 0 ∧
      carrier.poleOrder * (carrier.degree - 1) = carrier.endpointOrder := by
  have hbalance := carrier.balance
  have hr : (0 : ℤ) < carrier.poleOrder := by
    exact_mod_cast carrier.poleOrder_positive
  have hd : (1 : ℤ) < carrier.degree := by
    have hdNat : 1 < carrier.degree := by
      exact lt_of_lt_of_le (by norm_num) carrier.degree_at_least_two
    exact_mod_cast hdNat
  have hl : (0 : ℤ) < carrier.endpointOrder := by
    exact_mod_cast carrier.endpointOrder_positive
  have hn : (p.rootMultiplicity carrier.targetCenter : ℤ) = 0 := by
    nlinarith
  have hnNat : p.rootMultiplicity carrier.targetCenter = 0 := by
    exact_mod_cast hn
  constructor
  · exact hnNat
  · rw [hnNat] at hbalance
    norm_num at hbalance
    have hdOne : 1 ≤ carrier.degree := by omega
    have hcast :
        ((carrier.poleOrder * (carrier.degree - 1) : ℕ) : ℤ) =
          (carrier.endpointOrder : ℤ) := by
      rw [Nat.cast_mul, Nat.cast_sub hdOne]
      norm_num
      exact hbalance.symm
    exact_mod_cast hcast

/-- Equal base and endpoint orders on one positive pole sheet force equal
generator degrees.  The critical specialization uses order two on both
sides. -/
theorem equal_degree_of_common_ramified_order
    {poleOrder innerDegree outerDegree commonOrder : ℕ}
    (hpole : 0 < poleOrder)
    (hinnerDegree : 2 ≤ innerDegree)
    (houterDegree : 2 ≤ outerDegree)
    (hinner : poleOrder * (innerDegree - 1) = commonOrder)
    (houter : poleOrder * (outerDegree - 1) = commonOrder) :
    innerDegree = outerDegree := by
  have hmul : poleOrder * (innerDegree - 1) =
      poleOrder * (outerDegree - 1) := hinner.trans houter.symm
  have hsub : innerDegree - 1 = outerDegree - 1 :=
    Nat.mul_left_cancel hpole hmul
  omega

/-- Aggregated ramified Julia valuation-balance surface. -/
theorem ramified_julia_valuation_balance_terminal_certificate :
    (∀ (p : ℂ[X]) (carrier : InnerJuliaPoleCarrier p),
      p.rootMultiplicity carrier.center = 0 ∧
        carrier.poleOrder * (carrier.degree - 1) = carrier.baseOrder) ∧
    (∀ (p : ℂ[X]) (carrier : OuterJuliaReturnCarrier p),
      p.rootMultiplicity carrier.targetCenter = 0 ∧
        carrier.poleOrder * (carrier.degree - 1) =
          carrier.endpointOrder) ∧
    (∀ poleOrder innerDegree outerDegree commonOrder : ℕ,
      0 < poleOrder → 2 ≤ innerDegree → 2 ≤ outerDegree →
      poleOrder * (innerDegree - 1) = commonOrder →
      poleOrder * (outerDegree - 1) = commonOrder →
      innerDegree = outerDegree) := by
  refine ⟨?_, ?_, ?_⟩
  · intro p carrier
    exact carrier.regular_and_natural_balance
  · intro p carrier
    exact carrier.regular_and_natural_balance
  · intro poleOrder innerDegree outerDegree commonOrder hpole hinnerDegree
      houterDegree hinner houter
    exact equal_degree_of_common_ramified_order hpole hinnerDegree
      houterDegree hinner houter

end FormalRamifiedJuliaValuationBalance
