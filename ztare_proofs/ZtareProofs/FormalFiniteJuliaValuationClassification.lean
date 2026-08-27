import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalMeromorphicPoleDerivative
import ZtareProofs.FormalPolynomialMeromorphicOrder

/-!
# Valuation classification of finite polynomial Julia branches

A finite selected branch carries only analytic source/endpoint displacements
and the parameterized Julia identity.  Meromorphic order derives the root-
multiplicity balance.  Positive source and endpoint orders then rule out a
mixed regular/equilibrium pair.
-/

namespace FormalFiniteJuliaValuationClassification

open Filter Polynomial
open scoped Topology

open FormalMeromorphicPoleDerivative
open FormalPolynomialMeromorphicOrder

/-- A finite selected branch for one polynomial generator.  Root
multiplicities and their valuation balance are deliberately absent. -/
structure FiniteJuliaCarrier (p : ℂ[X]) where
  sourceCenter : ℂ
  endpointCenter : ℂ
  parameterCenter : ℂ
  sourceOrder : ℕ
  endpointOrder : ℕ
  sourceDisplacement : ℂ → ℂ
  endpointDisplacement : ℂ → ℂ
  polynomial_nonzero : p ≠ 0
  sourceOrder_positive : 0 < sourceOrder
  endpointOrder_positive : 0 < endpointOrder
  source_analytic : AnalyticAt ℂ sourceDisplacement parameterCenter
  endpoint_analytic : AnalyticAt ℂ endpointDisplacement parameterCenter
  source_zero : sourceDisplacement parameterCenter = 0
  endpoint_zero : endpointDisplacement parameterCenter = 0
  source_order :
    meromorphicOrderAt sourceDisplacement parameterCenter =
      ((sourceOrder : ℤ) : WithTop ℤ)
  endpoint_order :
    meromorphicOrderAt endpointDisplacement parameterCenter =
      ((endpointOrder : ℤ) : WithTop ℤ)
  julia :
    (fun t ↦ deriv endpointDisplacement t *
      p.eval (sourceCenter + sourceDisplacement t)) =ᶠ[
        𝓝[≠] parameterCenter]
      (fun t ↦ deriv sourceDisplacement t *
        p.eval (endpointCenter + endpointDisplacement t))

/-- The finite Julia row derives the complete integer root-multiplicity
balance. -/
theorem FiniteJuliaCarrier.balance
    {p : ℂ[X]} (carrier : FiniteJuliaCarrier p) :
    (carrier.endpointOrder : ℤ) *
        (1 - (p.rootMultiplicity carrier.endpointCenter : ℤ)) =
      (carrier.sourceOrder : ℤ) *
        (1 - (p.rootMultiplicity carrier.sourceCenter : ℤ)) := by
  have hendpointDerivative :=
    meromorphicOrderAt_deriv_of_positive_order
      carrier.endpointDisplacement carrier.parameterCenter
      carrier.endpointOrder carrier.endpoint_analytic.meromorphicAt
      carrier.endpointOrder_positive carrier.endpoint_order
  have hsourceDerivative :=
    meromorphicOrderAt_deriv_of_positive_order
      carrier.sourceDisplacement carrier.parameterCenter
      carrier.sourceOrder carrier.source_analytic.meromorphicAt
      carrier.sourceOrder_positive carrier.source_order
  have hsourceEval :=
    meromorphicOrderAt_polynomial_eval_at_finite_center
      p carrier.polynomial_nonzero carrier.sourceCenter
      carrier.sourceDisplacement carrier.parameterCenter
      carrier.sourceOrder carrier.source_analytic carrier.source_zero
      carrier.source_order
  have hendpointEval :=
    meromorphicOrderAt_polynomial_eval_at_finite_center
      p carrier.polynomial_nonzero carrier.endpointCenter
      carrier.endpointDisplacement carrier.parameterCenter
      carrier.endpointOrder carrier.endpoint_analytic carrier.endpoint_zero
      carrier.endpoint_order
  have hsourceEvalMeromorphic : MeromorphicAt
      (fun t ↦ p.eval
        (carrier.sourceCenter + carrier.sourceDisplacement t))
      carrier.parameterCenter := by
    exact (analyticAt_const.add carrier.source_analytic).aeval_polynomial p
      |>.meromorphicAt
  have hendpointEvalMeromorphic : MeromorphicAt
      (fun t ↦ p.eval
        (carrier.endpointCenter + carrier.endpointDisplacement t))
      carrier.parameterCenter := by
    exact (analyticAt_const.add carrier.endpoint_analytic).aeval_polynomial p
      |>.meromorphicAt
  have horders := meromorphicOrderAt_congr carrier.julia
  change meromorphicOrderAt
      (deriv carrier.endpointDisplacement *
        fun t ↦ p.eval
          (carrier.sourceCenter + carrier.sourceDisplacement t))
        carrier.parameterCenter =
    meromorphicOrderAt
      (deriv carrier.sourceDisplacement *
        fun t ↦ p.eval
          (carrier.endpointCenter + carrier.endpointDisplacement t))
        carrier.parameterCenter at horders
  rw [meromorphicOrderAt_mul carrier.endpoint_analytic.meromorphicAt.deriv
      hsourceEvalMeromorphic,
    meromorphicOrderAt_mul carrier.source_analytic.meromorphicAt.deriv
      hendpointEvalMeromorphic,
    hendpointDerivative, hsourceEval, hsourceDerivative,
    hendpointEval] at horders
  norm_cast at horders
  push_cast at horders
  change ((carrier.endpointOrder : ℤ) - 1) +
      (carrier.sourceOrder : ℤ) *
        (p.rootMultiplicity carrier.sourceCenter : ℤ) =
    ((carrier.sourceOrder : ℤ) - 1) +
      (carrier.endpointOrder : ℤ) *
        (p.rootMultiplicity carrier.endpointCenter : ℤ) at horders
  nlinarith

/-- A positive-order finite Julia branch cannot have exactly one regular
center and one equilibrium center. -/
theorem FiniteJuliaCarrier.regular_iff
    {p : ℂ[X]} (carrier : FiniteJuliaCarrier p) :
    p.rootMultiplicity carrier.sourceCenter = 0 ↔
      p.rootMultiplicity carrier.endpointCenter = 0 := by
  have hbalance := carrier.balance
  have hr : (0 : ℤ) < carrier.sourceOrder := by
    exact_mod_cast carrier.sourceOrder_positive
  have hq : (0 : ℤ) < carrier.endpointOrder := by
    exact_mod_cast carrier.endpointOrder_positive
  constructor
  · intro hsourceRegular
    by_contra hendpointRegular
    have hendpointPositive :
        0 < p.rootMultiplicity carrier.endpointCenter :=
      Nat.pos_of_ne_zero hendpointRegular
    have hendpointAtLeastOne :
        (1 : ℤ) ≤ p.rootMultiplicity carrier.endpointCenter := by
      exact_mod_cast hendpointPositive
    rw [hsourceRegular] at hbalance
    norm_num at hbalance
    nlinarith
  · intro hendpointRegular
    by_contra hsourceRegular
    have hsourcePositive :
        0 < p.rootMultiplicity carrier.sourceCenter :=
      Nat.pos_of_ne_zero hsourceRegular
    have hsourceAtLeastOne :
        (1 : ℤ) ≤ p.rootMultiplicity carrier.sourceCenter := by
      exact_mod_cast hsourcePositive
    rw [hendpointRegular] at hbalance
    norm_num at hbalance
    nlinarith

/-- In the regular-to-regular branch, Julia preserves the analytic order. -/
theorem FiniteJuliaCarrier.equal_order_of_source_regular
    {p : ℂ[X]} (carrier : FiniteJuliaCarrier p)
    (hsourceRegular : p.rootMultiplicity carrier.sourceCenter = 0) :
    carrier.endpointOrder = carrier.sourceOrder := by
  have hendpointRegular := carrier.regular_iff.mp hsourceRegular
  have hbalance := carrier.balance
  rw [hsourceRegular, hendpointRegular] at hbalance
  norm_num at hbalance
  exact_mod_cast hbalance

/-- Every finite positive-order Julia branch is either regular at both ends
with equal order, or is an equilibrium transition at both ends. -/
theorem FiniteJuliaCarrier.regular_or_equilibrium
    {p : ℂ[X]} (carrier : FiniteJuliaCarrier p) :
    (p.rootMultiplicity carrier.sourceCenter = 0 ∧
      p.rootMultiplicity carrier.endpointCenter = 0 ∧
      carrier.endpointOrder = carrier.sourceOrder) ∨
    (0 < p.rootMultiplicity carrier.sourceCenter ∧
      0 < p.rootMultiplicity carrier.endpointCenter) := by
  by_cases hsourceRegular :
      p.rootMultiplicity carrier.sourceCenter = 0
  · left
    exact ⟨hsourceRegular, carrier.regular_iff.mp hsourceRegular,
      carrier.equal_order_of_source_regular hsourceRegular⟩
  · right
    have hendpointNotRegular :
        p.rootMultiplicity carrier.endpointCenter ≠ 0 := by
      intro hendpointRegular
      exact hsourceRegular (carrier.regular_iff.mpr hendpointRegular)
    exact ⟨Nat.pos_of_ne_zero hsourceRegular,
      Nat.pos_of_ne_zero hendpointNotRegular⟩

/-- Aggregated finite-Julia valuation classification surface. -/
theorem finite_julia_valuation_classification_terminal_certificate :
    ∀ (p : ℂ[X]) (carrier : FiniteJuliaCarrier p),
      (carrier.endpointOrder : ℤ) *
          (1 - (p.rootMultiplicity carrier.endpointCenter : ℤ)) =
        (carrier.sourceOrder : ℤ) *
          (1 - (p.rootMultiplicity carrier.sourceCenter : ℤ)) ∧
      (p.rootMultiplicity carrier.sourceCenter = 0 ↔
        p.rootMultiplicity carrier.endpointCenter = 0) ∧
      ((p.rootMultiplicity carrier.sourceCenter = 0 ∧
          p.rootMultiplicity carrier.endpointCenter = 0 ∧
          carrier.endpointOrder = carrier.sourceOrder) ∨
        (0 < p.rootMultiplicity carrier.sourceCenter ∧
          0 < p.rootMultiplicity carrier.endpointCenter)) := by
  intro p carrier
  exact ⟨carrier.balance, carrier.regular_iff,
    carrier.regular_or_equilibrium⟩

end FormalFiniteJuliaValuationClassification
