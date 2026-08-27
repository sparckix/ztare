import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialMeromorphicOrder

/-!
# Valuation classification for separated polynomial branch relations

The relation `c * p(Y) = a₀ * q(Y)` has two normalized meromorphic
boundary types. At a finite boundary its visible order is the branch order
times a root-multiplicity difference. At a pole it is the pole order times a
polynomial-degree difference. Both balances are derived from the relation.
-/

namespace FormalSeparatedPolynomialBranchValuation

open Filter Polynomial
open scoped Topology

open FormalPolynomialMeromorphicOrder

/-- A normalized finite branch of a separated polynomial relation. The root
multiplicity balance is deliberately absent. -/
structure FiniteSeparatedRelationCarrier (p q : ℂ[X]) where
  parameterCenter : ℂ
  boundaryCenter : ℂ
  visibleOrder : ℕ
  branchOrder : ℕ
  visible : ℂ → ℂ
  displacement : ℂ → ℂ
  scalar : ℂ
  p_nonzero : p ≠ 0
  q_nonzero : q ≠ 0
  visibleOrder_positive : 0 < visibleOrder
  branchOrder_positive : 0 < branchOrder
  visible_analytic : AnalyticAt ℂ visible parameterCenter
  visible_order :
    meromorphicOrderAt visible parameterCenter =
      ((visibleOrder : ℤ) : WithTop ℤ)
  displacement_analytic : AnalyticAt ℂ displacement parameterCenter
  displacement_zero : displacement parameterCenter = 0
  displacement_order :
    meromorphicOrderAt displacement parameterCenter =
      ((branchOrder : ℤ) : WithTop ℤ)
  relation :
    (fun t ↦ visible t * p.eval (boundaryCenter + displacement t)) =ᶠ[
        𝓝[≠] parameterCenter]
      (fun t ↦ scalar * q.eval (boundaryCenter + displacement t))

/-- A normalized pole branch of a separated polynomial relation. The degree
balance is deliberately absent. -/
structure PoleSeparatedRelationCarrier (p q : ℂ[X]) where
  parameterCenter : ℂ
  visibleOrder : ℕ
  poleOrder : ℕ
  pDegree : ℕ
  qDegree : ℕ
  visible : ℂ → ℂ
  hidden : ℂ → ℂ
  reciprocal : ℂ → ℂ
  scalar : ℂ
  p_nonzero : p ≠ 0
  q_nonzero : q ≠ 0
  visibleOrder_positive : 0 < visibleOrder
  poleOrder_positive : 0 < poleOrder
  p_degree : p.natDegree = pDegree
  q_degree : q.natDegree = qDegree
  visible_analytic : AnalyticAt ℂ visible parameterCenter
  visible_order :
    meromorphicOrderAt visible parameterCenter =
      ((visibleOrder : ℤ) : WithTop ℤ)
  hidden_meromorphic : MeromorphicAt hidden parameterCenter
  hidden_order :
    meromorphicOrderAt hidden parameterCenter =
      ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ)
  reciprocal_analytic : AnalyticAt ℂ reciprocal parameterCenter
  reciprocal_zero : reciprocal parameterCenter = 0
  reciprocal_eq_inverse :
    reciprocal =ᶠ[𝓝[≠] parameterCenter] fun t ↦ (hidden t)⁻¹
  relation :
    (fun t ↦ visible t * p.eval (hidden t)) =ᶠ[
        𝓝[≠] parameterCenter]
      (fun t ↦ scalar * q.eval (hidden t))

private theorem analytic_unit_order_zero
    {unit : ℂ → ℂ} {center : ℂ}
    (hanalytic : AnalyticAt ℂ unit center)
    (hnonzero : unit center ≠ 0) :
    meromorphicOrderAt unit center = 0 := by
  rw [hanalytic.meromorphicOrderAt_eq,
    hanalytic.analyticOrderAt_eq_zero.mpr hnonzero]
  simp

private theorem nonzero_constant_order_zero
    (scalar center : ℂ) (hnonzero : scalar ≠ 0) :
    meromorphicOrderAt (fun _ : ℂ ↦ scalar) center = 0 := by
  exact analytic_unit_order_zero analyticAt_const hnonzero

/-- On a nonconstant finite normalized branch, the separated relation itself
forces the scalar coefficient to be nonzero. -/
theorem FiniteSeparatedRelationCarrier.scalar_nonzero
    {p q : ℂ[X]} (carrier : FiniteSeparatedRelationCarrier p q) :
    carrier.scalar ≠ 0 := by
  have hpOrder := meromorphicOrderAt_polynomial_eval_at_finite_center
    p carrier.p_nonzero carrier.boundaryCenter carrier.displacement
    carrier.parameterCenter carrier.branchOrder
    carrier.displacement_analytic carrier.displacement_zero
    carrier.displacement_order
  have hvisibleFinite :
      meromorphicOrderAt carrier.visible carrier.parameterCenter ≠ ⊤ := by
    rw [carrier.visible_order]
    simp
  have hvisibleEventuallyNe :
      ∀ᶠ t in 𝓝[≠] carrier.parameterCenter, carrier.visible t ≠ 0 :=
    (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
      carrier.visible_analytic.meromorphicAt).mp hvisibleFinite
  have hpMeromorphic : MeromorphicAt
      (fun t ↦ p.eval (carrier.boundaryCenter + carrier.displacement t))
      carrier.parameterCenter :=
    (analyticAt_const.add carrier.displacement_analytic).aeval_polynomial p
      |>.meromorphicAt
  have hpFinite : meromorphicOrderAt
      (fun t ↦ p.eval (carrier.boundaryCenter + carrier.displacement t))
      carrier.parameterCenter ≠ ⊤ := by
    rw [hpOrder]
    exact WithTop.coe_ne_top
  have hpEventuallyNe : ∀ᶠ t in 𝓝[≠] carrier.parameterCenter,
      p.eval (carrier.boundaryCenter + carrier.displacement t) ≠ 0 :=
    (meromorphicOrderAt_ne_top_iff_eventually_ne_zero hpMeromorphic).mp
      hpFinite
  intro hscalar
  have hfalse : ∀ᶠ _t in 𝓝[≠] carrier.parameterCenter, False := by
    filter_upwards [carrier.relation, hvisibleEventuallyNe, hpEventuallyNe]
      with t hrelation hvisible hp
    rw [hscalar, zero_mul] at hrelation
    exact (mul_ne_zero hvisible hp) hrelation
  obtain ⟨_t, ht⟩ := Filter.Eventually.exists hfalse
  exact ht

/-- On a pole branch, finite meromorphic substitution order likewise forces
the scalar coefficient to be nonzero. -/
theorem PoleSeparatedRelationCarrier.scalar_nonzero
    {p q : ℂ[X]} (carrier : PoleSeparatedRelationCarrier p q) :
    carrier.scalar ≠ 0 := by
  have hpOrder := meromorphicOrderAt_polynomial_eval_at_pole
    p carrier.p_nonzero carrier.pDegree carrier.p_degree carrier.hidden
    carrier.reciprocal carrier.parameterCenter carrier.poleOrder
    carrier.hidden_meromorphic carrier.hidden_order
    carrier.reciprocal_analytic carrier.reciprocal_zero
    carrier.reciprocal_eq_inverse
  have hvisibleFinite :
      meromorphicOrderAt carrier.visible carrier.parameterCenter ≠ ⊤ := by
    rw [carrier.visible_order]
    simp
  have hvisibleEventuallyNe :
      ∀ᶠ t in 𝓝[≠] carrier.parameterCenter, carrier.visible t ≠ 0 :=
    (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
      carrier.visible_analytic.meromorphicAt).mp hvisibleFinite
  have hpMeromorphic : MeromorphicAt (fun t ↦ p.eval (carrier.hidden t))
      carrier.parameterCenter :=
    meromorphicAt_eval_polynomial carrier.hidden_meromorphic p
  have hpFinite :
      meromorphicOrderAt (fun t ↦ p.eval (carrier.hidden t))
        carrier.parameterCenter ≠ ⊤ := by
    rw [hpOrder]
    exact WithTop.coe_ne_top
  have hpEventuallyNe : ∀ᶠ t in 𝓝[≠] carrier.parameterCenter,
      p.eval (carrier.hidden t) ≠ 0 :=
    (meromorphicOrderAt_ne_top_iff_eventually_ne_zero hpMeromorphic).mp
      hpFinite
  intro hscalar
  have hfalse : ∀ᶠ _t in 𝓝[≠] carrier.parameterCenter, False := by
    filter_upwards [carrier.relation, hvisibleEventuallyNe, hpEventuallyNe]
      with t hrelation hvisible hp
    rw [hscalar, zero_mul] at hrelation
    exact (mul_ne_zero hvisible hp) hrelation
  obtain ⟨_t, ht⟩ := Filter.Eventually.exists hfalse
  exact ht

/-- The finite separated relation forces the exact integer multiplicity
balance. -/
theorem FiniteSeparatedRelationCarrier.integer_balance
    {p q : ℂ[X]} (carrier : FiniteSeparatedRelationCarrier p q) :
    (carrier.visibleOrder : ℤ) +
        (carrier.branchOrder : ℤ) *
          (p.rootMultiplicity carrier.boundaryCenter : ℤ) =
      (carrier.branchOrder : ℤ) *
        (q.rootMultiplicity carrier.boundaryCenter : ℤ) := by
  have hpOrder := meromorphicOrderAt_polynomial_eval_at_finite_center
    p carrier.p_nonzero carrier.boundaryCenter carrier.displacement
    carrier.parameterCenter carrier.branchOrder
    carrier.displacement_analytic carrier.displacement_zero
    carrier.displacement_order
  have hqOrder := meromorphicOrderAt_polynomial_eval_at_finite_center
    q carrier.q_nonzero carrier.boundaryCenter carrier.displacement
    carrier.parameterCenter carrier.branchOrder
    carrier.displacement_analytic carrier.displacement_zero
    carrier.displacement_order
  have hscalarOrder := nonzero_constant_order_zero carrier.scalar
    carrier.parameterCenter carrier.scalar_nonzero
  have hpMeromorphic : MeromorphicAt
      (fun t ↦ p.eval (carrier.boundaryCenter + carrier.displacement t))
      carrier.parameterCenter :=
    (analyticAt_const.add carrier.displacement_analytic).aeval_polynomial p
      |>.meromorphicAt
  have hqMeromorphic : MeromorphicAt
      (fun t ↦ q.eval (carrier.boundaryCenter + carrier.displacement t))
      carrier.parameterCenter :=
    (analyticAt_const.add carrier.displacement_analytic).aeval_polynomial q
      |>.meromorphicAt
  have horders := meromorphicOrderAt_congr carrier.relation
  change meromorphicOrderAt
      (carrier.visible * fun t ↦ p.eval
        (carrier.boundaryCenter + carrier.displacement t))
        carrier.parameterCenter =
    meromorphicOrderAt
      ((fun _ : ℂ ↦ carrier.scalar) *
        fun t ↦ q.eval
          (carrier.boundaryCenter + carrier.displacement t))
        carrier.parameterCenter at horders
  rw [meromorphicOrderAt_mul
      carrier.visible_analytic.meromorphicAt hpMeromorphic,
    meromorphicOrderAt_mul (MeromorphicAt.const carrier.scalar _)
      hqMeromorphic,
    carrier.visible_order, hpOrder, hscalarOrder, hqOrder]
    at horders
  norm_cast at horders
  have hnatural : carrier.visibleOrder + carrier.branchOrder *
        p.rootMultiplicity carrier.boundaryCenter =
      carrier.branchOrder * q.rootMultiplicity carrier.boundaryCenter := by
    omega
  exact_mod_cast hnatural

/-- At a finite boundary, the outer polynomial has strictly larger root
multiplicity, and the visible order is their exact positive difference. -/
theorem FiniteSeparatedRelationCarrier.natural_balance_and_boundary_root
    {p q : ℂ[X]} (carrier : FiniteSeparatedRelationCarrier p q) :
    carrier.scalar ≠ 0 ∧
      carrier.visibleOrder = carrier.branchOrder *
        (q.rootMultiplicity carrier.boundaryCenter -
          p.rootMultiplicity carrier.boundaryCenter) ∧
      p.rootMultiplicity carrier.boundaryCenter <
        q.rootMultiplicity carrier.boundaryCenter ∧
      q.IsRoot carrier.boundaryCenter := by
  have hbalance := carrier.integer_balance
  have he : (0 : ℤ) < carrier.visibleOrder := by
    exact_mod_cast carrier.visibleOrder_positive
  have hr : (0 : ℤ) < carrier.branchOrder := by
    exact_mod_cast carrier.branchOrder_positive
  have hstrict : p.rootMultiplicity carrier.boundaryCenter <
      q.rootMultiplicity carrier.boundaryCenter := by
    by_contra hnot
    have hle : q.rootMultiplicity carrier.boundaryCenter ≤
        p.rootMultiplicity carrier.boundaryCenter := Nat.le_of_not_gt hnot
    have hleCast :
        (q.rootMultiplicity carrier.boundaryCenter : ℤ) ≤
          (p.rootMultiplicity carrier.boundaryCenter : ℤ) := by
      exact_mod_cast hle
    nlinarith
  have hnatural : carrier.visibleOrder = carrier.branchOrder *
      (q.rootMultiplicity carrier.boundaryCenter -
        p.rootMultiplicity carrier.boundaryCenter) := by
    have hcast : (carrier.visibleOrder : ℤ) =
        ((carrier.branchOrder *
          (q.rootMultiplicity carrier.boundaryCenter -
            p.rootMultiplicity carrier.boundaryCenter) : ℕ) : ℤ) := by
      rw [Nat.cast_mul, Nat.cast_sub hstrict.le]
      nlinarith
    exact_mod_cast hcast
  have hqPositive : 0 < q.rootMultiplicity carrier.boundaryCenter :=
    lt_of_le_of_lt (Nat.zero_le _) hstrict
  exact ⟨carrier.scalar_nonzero, hnatural, hstrict,
    (rootMultiplicity_pos carrier.q_nonzero).mp hqPositive⟩

/-- The pole separated relation forces the exact integer degree balance. -/
theorem PoleSeparatedRelationCarrier.integer_balance
    {p q : ℂ[X]} (carrier : PoleSeparatedRelationCarrier p q) :
    (carrier.visibleOrder : ℤ) =
      (carrier.poleOrder : ℤ) *
        ((carrier.pDegree : ℤ) - (carrier.qDegree : ℤ)) := by
  have hpOrder := meromorphicOrderAt_polynomial_eval_at_pole
    p carrier.p_nonzero carrier.pDegree carrier.p_degree carrier.hidden
    carrier.reciprocal carrier.parameterCenter carrier.poleOrder
    carrier.hidden_meromorphic carrier.hidden_order
    carrier.reciprocal_analytic carrier.reciprocal_zero
    carrier.reciprocal_eq_inverse
  have hqOrder := meromorphicOrderAt_polynomial_eval_at_pole
    q carrier.q_nonzero carrier.qDegree carrier.q_degree carrier.hidden
    carrier.reciprocal carrier.parameterCenter carrier.poleOrder
    carrier.hidden_meromorphic carrier.hidden_order
    carrier.reciprocal_analytic carrier.reciprocal_zero
    carrier.reciprocal_eq_inverse
  have hscalarOrder := nonzero_constant_order_zero carrier.scalar
    carrier.parameterCenter carrier.scalar_nonzero
  have hpMeromorphic : MeromorphicAt (fun t ↦ p.eval (carrier.hidden t))
      carrier.parameterCenter :=
    meromorphicAt_eval_polynomial carrier.hidden_meromorphic p
  have hqMeromorphic : MeromorphicAt (fun t ↦ q.eval (carrier.hidden t))
      carrier.parameterCenter :=
    meromorphicAt_eval_polynomial carrier.hidden_meromorphic q
  have horders := meromorphicOrderAt_congr carrier.relation
  change meromorphicOrderAt
      (carrier.visible * fun t ↦ p.eval (carrier.hidden t))
        carrier.parameterCenter =
    meromorphicOrderAt
      ((fun _ : ℂ ↦ carrier.scalar) *
        fun t ↦ q.eval (carrier.hidden t)) carrier.parameterCenter at horders
  rw [meromorphicOrderAt_mul
      carrier.visible_analytic.meromorphicAt hpMeromorphic,
    meromorphicOrderAt_mul (MeromorphicAt.const carrier.scalar _)
      hqMeromorphic,
    carrier.visible_order, hpOrder, hscalarOrder, hqOrder]
    at horders
  norm_cast at horders
  nlinarith

/-- At a pole boundary, the first polynomial has strictly larger degree, and
the visible order is the exact natural degree difference. -/
theorem PoleSeparatedRelationCarrier.natural_balance_and_degree_drop
    {p q : ℂ[X]} (carrier : PoleSeparatedRelationCarrier p q) :
    carrier.scalar ≠ 0 ∧
      carrier.visibleOrder = carrier.poleOrder *
        (carrier.pDegree - carrier.qDegree) ∧
      carrier.qDegree < carrier.pDegree := by
  have hbalance := carrier.integer_balance
  have he : (0 : ℤ) < carrier.visibleOrder := by
    exact_mod_cast carrier.visibleOrder_positive
  have hr : (0 : ℤ) < carrier.poleOrder := by
    exact_mod_cast carrier.poleOrder_positive
  have hstrict : carrier.qDegree < carrier.pDegree := by
    by_contra hnot
    have hle : carrier.pDegree ≤ carrier.qDegree := Nat.le_of_not_gt hnot
    have hleCast : (carrier.pDegree : ℤ) ≤ carrier.qDegree := by
      exact_mod_cast hle
    nlinarith
  have hnatural : carrier.visibleOrder = carrier.poleOrder *
      (carrier.pDegree - carrier.qDegree) := by
    have hcast : (carrier.visibleOrder : ℤ) =
        ((carrier.poleOrder *
          (carrier.pDegree - carrier.qDegree) : ℕ) : ℤ) := by
      rw [Nat.cast_mul, Nat.cast_sub hstrict.le]
      exact hbalance
    exact_mod_cast hcast
  exact ⟨carrier.scalar_nonzero, hnatural, hstrict⟩

/-- Aggregated finite/pole valuation classification surface. -/
theorem separated_polynomial_branch_valuation_terminal_certificate :
    (∀ (p q : ℂ[X]) (carrier : FiniteSeparatedRelationCarrier p q),
      carrier.scalar ≠ 0 ∧
        carrier.visibleOrder = carrier.branchOrder *
          (q.rootMultiplicity carrier.boundaryCenter -
            p.rootMultiplicity carrier.boundaryCenter) ∧
        p.rootMultiplicity carrier.boundaryCenter <
          q.rootMultiplicity carrier.boundaryCenter ∧
        q.IsRoot carrier.boundaryCenter) ∧
    (∀ (p q : ℂ[X]) (carrier : PoleSeparatedRelationCarrier p q),
      carrier.scalar ≠ 0 ∧
        carrier.visibleOrder = carrier.poleOrder *
          (carrier.pDegree - carrier.qDegree) ∧
        carrier.qDegree < carrier.pDegree) := by
  constructor
  · intro p q carrier
    exact carrier.natural_balance_and_boundary_root
  · intro p q carrier
    exact carrier.natural_balance_and_degree_drop

end FormalSeparatedPolynomialBranchValuation
